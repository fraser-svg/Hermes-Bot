#!/usr/bin/env python3
"""Deploy HTML sites to Netlify as preview URLs.

Takes built HTML from output/, deploys each to Netlify,
returns live preview URLs ready for outreach.

Usage:
    python3 deploy.py                          # deploy all un-deployed sites
    python3 deploy.py output/some-business.html  # deploy one site
    python3 deploy.py --list                   # list all deployed sites
    python3 deploy.py --status                 # check deploy status

Requires NETLIFY_AUTH_TOKEN in .env
"""

import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DEPLOY_LOG = BASE_DIR / "prospects" / "deploys.json"

NETLIFY_API = "https://api.netlify.com/api/v1"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def get_netlify_token() -> str:
    token = (
        os.environ.get("NETLIFY_AUTH_TOKEN")
        or load_env().get("NETLIFY_AUTH_TOKEN")
    )
    if not token:
        raise RuntimeError("No NETLIFY_AUTH_TOKEN in .env")
    return token


def load_deploy_log() -> list[dict]:
    if DEPLOY_LOG.exists():
        return json.loads(DEPLOY_LOG.read_text())
    return []


def save_deploy_log(deploys: list[dict]) -> None:
    DEPLOY_LOG.parent.mkdir(exist_ok=True)
    DEPLOY_LOG.write_text(json.dumps(deploys, indent=2))


def netlify_request(
    method: str,
    path: str,
    token: str,
    data: bytes | None = None,
    content_type: str = "application/json",
    retries: int = 3,
) -> dict:
    import time
    url = f"{NETLIFY_API}{path}"

    for attempt in range(retries):
        req = Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type,
            },
            method=method,
        )
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429 and attempt < retries - 1:
                wait = (attempt + 1) * 15
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Netlify API {e.code}: {body}") from e
    raise RuntimeError("Netlify API: max retries exceeded")


def make_subdomain(name_slug: str) -> str:
    short_hash = hashlib.sha256(name_slug.encode()).hexdigest()[:6]
    return f"h-{name_slug}-{short_hash}"[:60].strip("-")


def create_site(token: str, name_slug: str) -> dict:
    """Create a new Netlify site, or return existing one if subdomain taken."""
    subdomain = make_subdomain(name_slug)
    payload = json.dumps({"name": subdomain}).encode("utf-8")
    try:
        return netlify_request("POST", "/sites", token, data=payload)
    except RuntimeError as e:
        if "422" in str(e) and "unique" in str(e).lower():
            print(f"  Site exists, fetching: {subdomain}")
            return netlify_request("GET", f"/sites/{subdomain}.netlify.app", token)
        raise


def make_zip(html_path: Path) -> bytes:
    """Create a zip archive with index.html for Netlify deploy."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_path.read_text(encoding="utf-8"))
    return buf.getvalue()


def deploy_site(token: str, site_id: str, zip_data: bytes) -> dict:
    """Deploy a zip to an existing Netlify site."""
    return netlify_request(
        "POST",
        f"/sites/{site_id}/deploys",
        token,
        data=zip_data,
        content_type="application/zip",
    )


def deploy_one(html_path: Path, token: str, deploys: list[dict]) -> dict:
    """Deploy a single HTML file to Netlify. Returns deploy record."""
    html_path = html_path.resolve()
    slug = html_path.stem  # e.g. "edinburgh-sparks-electrical"

    # Check if already deployed (same file content)
    file_hash = hashlib.sha256(html_path.read_bytes()).hexdigest()[:16]
    for d in deploys:
        if d.get("slug") == slug and d.get("file_hash") == file_hash:
            print(f"  Already deployed (unchanged): {d['url']}")
            return d

    # Check if site exists from previous deploy
    existing = next((d for d in deploys if d.get("slug") == slug), None)

    if existing:
        site_id = existing["site_id"]
        print(f"  Re-deploying to existing site: {existing['url']}")
    else:
        print(f"  Creating new Netlify site: {slug}")
        site = create_site(token, slug)
        site_id = site["id"]

    # Deploy
    zip_data = make_zip(html_path)
    deploy_result = deploy_site(token, site_id, zip_data)

    ssl_url = deploy_result.get("ssl_url") or deploy_result.get("url", "")
    deploy_url = deploy_result.get("deploy_ssl_url") or ssl_url

    record = {
        "slug": slug,
        "site_id": site_id,
        "deploy_id": deploy_result.get("id", ""),
        "url": ssl_url,
        "deploy_url": deploy_url,
        "html_file": str(html_path.relative_to(BASE_DIR)),
        "file_hash": file_hash,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "status": "preview",  # preview | live | paused
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

    print(f"  LIVE: {ssl_url}")
    return record


def deploy_all(token: str) -> list[dict]:
    """Deploy all HTML files in output/ that haven't been deployed yet."""
    import time

    html_files = sorted(OUTPUT_DIR.glob("*.html"))
    if not html_files:
        print("No HTML files in output/")
        return []

    deploys = load_deploy_log()
    results = []

    for i, html_path in enumerate(html_files):
        print(f"\n[{html_path.name}]")
        try:
            record = deploy_one(html_path, token, deploys)
            results.append(record)
        except RuntimeError as e:
            if "429" in str(e):
                print("  Rate limited. Waiting 10s...")
                time.sleep(10)
                try:
                    record = deploy_one(html_path, token, deploys)
                    results.append(record)
                except RuntimeError as e2:
                    print(f"  Still failing: {e2}")
            else:
                print(f"  Error: {e}")

        # Brief pause between deploys to avoid rate limits
        if i < len(html_files) - 1:
            time.sleep(3)

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
        print(f"  [{status}] {d['slug']}")
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
    print("  HERMES DEPLOY")
    print("=" * 60)

    token = get_netlify_token()

    if args and not args[0].startswith("--"):
        # Deploy specific file
        html_path = Path(args[0])
        if not html_path.exists():
            html_path = OUTPUT_DIR / args[0]
        if not html_path.exists():
            print(f"File not found: {args[0]}")
            return 1

        deploys = load_deploy_log()
        deploy_one(html_path, token, deploys)
        save_deploy_log(deploys)
    else:
        # Deploy all
        deploy_all(token)

    return 0


if __name__ == "__main__":
    sys.exit(main())
