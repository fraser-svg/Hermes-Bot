#!/usr/bin/env python3
"""Deploy HTML sites to Cloudflare Pages via wrangler CLI.

Takes built HTML from output/, deploys each to Cloudflare Pages,
returns live preview URLs ready for outreach.

Usage:
    python3 deploy.py                          # deploy all un-deployed sites
    python3 deploy.py output/some-business.html  # deploy one site
    python3 deploy.py --list                   # list all deployed sites
    python3 deploy.py --status                 # check deploy status

Requires: npx wrangler login (OAuth — no API token needed)
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DEPLOY_LOG = BASE_DIR / "deploys.json"

CF_ACCOUNT_ID = "6736c2090f18a33741b887e93406a852"


def load_deploy_log() -> list[dict]:
    if DEPLOY_LOG.exists():
        return json.loads(DEPLOY_LOG.read_text())
    return []


def save_deploy_log(deploys: list[dict]) -> None:
    DEPLOY_LOG.parent.mkdir(exist_ok=True)
    DEPLOY_LOG.write_text(json.dumps(deploys, indent=2))


def make_project_name(name_slug: str) -> str:
    short_hash = hashlib.sha256(name_slug.encode()).hexdigest()[:6]
    return f"h-{name_slug}-{short_hash}"[:58].strip("-")


def wrangler_cmd(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a wrangler command via npx."""
    cmd = ["npx", "wrangler"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_project(project_name: str) -> None:
    """Create Cloudflare Pages project if it doesn't exist."""
    result = wrangler_cmd([
        "pages", "project", "create", project_name,
        "--production-branch", "main",
    ])
    if result.returncode != 0:
        # Project already exists — that's fine
        if "already being used" in result.stderr or "already exists" in result.stderr:
            return
        # Some other error
        if result.returncode != 0 and "already" not in result.stderr.lower():
            raise RuntimeError(f"Failed to create project {project_name}: {result.stderr}")


def deploy_one(html_path: Path, deploys: list[dict]) -> dict:
    """Deploy a single HTML file to Cloudflare Pages. Returns deploy record."""
    html_path = html_path.resolve()
    slug = html_path.stem

    # Check if already deployed (same file content)
    file_hash = hashlib.sha256(html_path.read_bytes()).hexdigest()[:16]
    for d in deploys:
        if d.get("slug") == slug and d.get("file_hash") == file_hash:
            print(f"  Already deployed (unchanged): {d['url']}")
            return d

    project_name = make_project_name(slug)

    # Ensure project exists
    print(f"  Ensuring project: {project_name}")
    ensure_project(project_name)

    # Create temp directory with index.html for wrangler deploy
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / "index.html"
        copy2(html_path, dest)

        print(f"  Deploying to Cloudflare Pages...")
        result = wrangler_cmd([
            "pages", "deploy", tmpdir,
            "--project-name", project_name,
            "--branch", "main",
        ], timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"Deploy failed: {result.stderr}")

    # Parse URL from wrangler output
    output = result.stdout + result.stderr
    url = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("https://") and ".pages.dev" in line:
            url = line
            break

    if not url:
        # Construct URL from project name
        url = f"https://{project_name}.pages.dev"

    record = {
        "slug": slug,
        "project_name": project_name,
        "url": url,
        "html_file": str(html_path.relative_to(BASE_DIR)),
        "file_hash": file_hash,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "status": "preview",
        "provider": "cloudflare",
    }

    # Update or append to deploy log
    updated = False
    for i, d in enumerate(deploys):
        if d.get("slug") == slug:
            deploys[i] = record
            updated = True
            break
    if not updated:
        deploys.append(record)

    print(f"  LIVE: {url}")
    return record


def deploy_all() -> list[dict]:
    """Deploy all HTML files in output/ that haven't been deployed yet."""
    html_files = sorted(OUTPUT_DIR.glob("*.html"))
    if not html_files:
        print("No HTML files in output/")
        return []

    deploys = load_deploy_log()
    results = []

    for html_path in html_files:
        print(f"\n[{html_path.name}]")
        try:
            record = deploy_one(html_path, deploys)
            results.append(record)
        except RuntimeError as e:
            print(f"  Error: {e}")

    save_deploy_log(deploys)
    return results


def list_deploys() -> None:
    deploys = load_deploy_log()
    if not deploys:
        print("No deploys yet.")
        return

    print(f"\n{'=' * 60}")
    print(f"  DEPLOYED SITES ({len(deploys)})")
    print(f"{'=' * 60}\n")

    for d in deploys:
        status = d.get("status", "?").upper()
        provider = d.get("provider", "netlify")
        print(f"  [{status}] {d['slug']} ({provider})")
        print(f"    URL: {d['url']}")
        print(f"    File: {d['html_file']}")
        print(f"    Deployed: {d['deployed_at'][:16]}")
        print()


def main() -> int:
    args = sys.argv[1:]

    if "--list" in args or "--status" in args:
        list_deploys()
        return 0

    print("=" * 60)
    print("  HERMES DEPLOY (Cloudflare Pages)")
    print("=" * 60)

    # Verify wrangler auth
    result = wrangler_cmd(["whoami"])
    if "not authenticated" in (result.stdout + result.stderr).lower():
        print("Not authenticated. Run: npx wrangler login")
        return 1

    if args and not args[0].startswith("--"):
        # Deploy specific file
        html_path = Path(args[0])
        if not html_path.exists():
            html_path = OUTPUT_DIR / args[0]
        if not html_path.exists():
            print(f"File not found: {args[0]}")
            return 1

        deploys = load_deploy_log()
        deploy_one(html_path, deploys)
        save_deploy_log(deploys)
    else:
        deploy_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
