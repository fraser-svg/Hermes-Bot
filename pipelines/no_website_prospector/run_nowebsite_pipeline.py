#!/usr/bin/env python3
"""No-website prospecting pipeline.

Discovers UK local-service businesses without a website via Google Places,
probes website health for any that list a URL (broken/placeholder detection),
writes a candidates JSON file for the no-website-qualifier agent, and
optionally builds + deploys a site per qualified prospect.

Usage:
    # Discovery only (stop before qualify/build/deploy):
    python3 -m pipelines.no_website_prospector.run_nowebsite_pipeline \\
        --cities "Edinburgh,Glasgow,Stirling" \\
        --categories "electrician,plumber" \\
        --limit 20 \\
        --discover-only

    # Full pipeline (build + deploy each qualified prospect):
    python3 -m pipelines.no_website_prospector.run_nowebsite_pipeline \\
        --cities "Stirling" --categories "electrician" --limit 10

    # Build + deploy for already-qualified prospects (skips discovery):
    python3 -m pipelines.no_website_prospector.run_nowebsite_pipeline --build-qualified

The qualifier step itself is expected to be driven by the orchestrator skill
invoking the `no-website-qualifier` agent on each candidate; this script emits
the data the agent needs (candidates.json) and consumes the agent's output
(`_workspace/nowebsite/{slug}_qualified.json`).

Environment:
    GOOGLE_API_KEY / GOOGLE_MAPS_API — Google Places (New) API key.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Reuse prospector primitives.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import prospect  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "_workspace" / "nowebsite"
OUTPUT_DIR = BASE_DIR / "output"
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
DEPLOY_LOG = BASE_DIR / "prospects" / "deploys.json"

PLACEHOLDER_SIGNALS: tuple[str, ...] = (
    "coming soon",
    "under construction",
    "just another wordpress site",
    "site not published",
    "welcome to wordpress",
    "default web site page",
    "this domain is for sale",
    "parked domain",
)

UK_POSTCODE_RE = re.compile(
    r"\b[A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2}\b", re.IGNORECASE
)

logger = logging.getLogger("nowebsite")


@dataclass(frozen=True)
class WebsiteHealth:
    status: str  # "no_site" | "broken" | "placeholder" | "ok" | "needs_check"
    http_status: int | None
    title: str
    checked_at: str


@dataclass
class Candidate:
    slug: str
    business_name: str
    business_category: str
    city: str
    address: str
    phone_number: str
    website_url: str
    rating: float
    review_count: int
    business_status: str
    google_maps_url: str
    services_offered: list[str]
    google_reviews: list[dict[str, Any]]
    website_health: dict[str, Any] | None = None


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:60] or "business"


def is_uk_address(address: str) -> bool:
    if not address:
        return False
    if UK_POSTCODE_RE.search(address):
        return True
    lowered = address.lower()
    tokens = (
        "united kingdom",
        ", uk",
        " uk",
        "england",
        "scotland",
        "wales",
        "northern ireland",
    )
    return any(tok in lowered for tok in tokens)


def probe_website(url: str, timeout: float = 10.0) -> WebsiteHealth:
    """Classify a URL as no_site / broken / placeholder / ok / needs_check."""
    now = datetime.now(timezone.utc).isoformat()
    if not url or url.lower() in {"n/a", "none", "null"}:
        return WebsiteHealth("no_site", None, "", now)

    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    if not parsed.netloc:
        return WebsiteHealth("broken", None, "", now)

    try:
        req = Request(
            parsed.geturl(),
            headers={"User-Agent": "Mozilla/5.0 (HermesBot/1.0 health-probe)"},
        )
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read(4096).decode("utf-8", errors="ignore").lower()
    except HTTPError as e:
        return WebsiteHealth("broken", e.code, "", now)
    except (URLError, socket.timeout, ConnectionError, OSError) as e:
        logger.debug("probe error for %s: %s", url, e)
        return WebsiteHealth("broken", None, "", now)

    title = ""
    match = re.search(r"<title[^>]*>(.*?)</title>", body, re.DOTALL)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()

    if status >= 400:
        return WebsiteHealth("broken", status, title, now)

    haystack = f"{title} {body[:2048]}"
    for signal in PLACEHOLDER_SIGNALS:
        if signal in haystack:
            return WebsiteHealth("placeholder", status, title, now)
    if not title:
        return WebsiteHealth("placeholder", status, "", now)

    return WebsiteHealth("ok", status, title, now)


def place_to_candidate(place: dict[str, Any], category: str, city: str) -> Candidate:
    """Adapt a Google Places result into our Candidate dataclass."""
    details = prospect.place_to_business_details(place, category, city)
    name = details["business_name"]
    slug = slugify(f"{city}-{name}")
    return Candidate(
        slug=slug,
        business_name=name,
        business_category=details["business_category"],
        city=details["city"],
        address=details.get("address", ""),
        phone_number=details.get("phone_number", ""),
        website_url=place.get("websiteUri", "") or "",
        rating=float(details.get("rating") or 0.0),
        review_count=int(details.get("review_count") or 0),
        business_status=place.get("businessStatus", "OPERATIONAL"),
        google_maps_url=details.get("google_maps_url", ""),
        services_offered=details.get("services_offered", []),
        google_reviews=details.get("google_reviews", []),
    )


def discover(cities: list[str], categories: list[str], limit: int) -> list[Candidate]:
    """Search Google Places across the city × category grid. Drop duplicates."""
    api_key = prospect.get_google_key()
    seen: set[str] = set()
    out: list[Candidate] = []

    for city in cities:
        for category in categories:
            logger.info("discover: %s × %s", city, category)
            try:
                places = prospect.search_places(category, city, api_key, limit)
            except RuntimeError as e:
                logger.error("Places API failure for %s/%s: %s", city, category, e)
                continue

            for place in places:
                if place.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue
                cand = place_to_candidate(place, category, city)
                if cand.slug in seen:
                    continue
                seen.add(cand.slug)
                out.append(cand)

    return out


def enrich_health(candidates: list[Candidate]) -> None:
    """Probe each candidate's website in-place."""
    for cand in candidates:
        health = probe_website(cand.website_url)
        cand.website_health = asdict(health)
        logger.info(
            "health: %-48s %-12s %s",
            cand.business_name[:48],
            health.status,
            cand.website_url or "(none)",
        )


def write_candidates(candidates: list[Candidate], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            **asdict(c),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        for c in candidates
    ]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("wrote %d candidates → %s", len(candidates), path)


def candidate_to_business_details(cand: Candidate) -> dict[str, Any]:
    """Map Candidate → references/business_details.json shape for generate.py."""
    return {
        "business_name": cand.business_name,
        "business_category": cand.business_category,
        "city": cand.city,
        "address": cand.address,
        "phone_number": cand.phone_number,
        "services_offered": cand.services_offered,
        "google_reviews": cand.google_reviews,
        "rating": cand.rating,
        "review_count": cand.review_count,
        "google_maps_url": cand.google_maps_url,
        "_source": "no_website_prospector",
    }


def load_qualified(slug: str) -> dict[str, Any] | None:
    path = WORKSPACE / f"{slug}_qualified.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("invalid JSON in %s", path)
        return None


def run_subprocess(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(BASE_DIR),
        check=False,
    )


def build_one(cand: Candidate) -> dict[str, Any]:
    """Write business_details.json for `cand` and run generate.py."""
    details = candidate_to_business_details(cand)
    # Back up existing details file if present, restore after.
    backup: bytes | None = None
    if DETAILS_PATH.exists():
        backup = DETAILS_PATH.read_bytes()

    try:
        DETAILS_PATH.write_text(json.dumps(details, indent=2, ensure_ascii=False))
        result = run_subprocess(
            [sys.executable, "generate.py"],
            timeout=600,
        )
        if result.returncode != 0:
            return {
                "status": "failed",
                "stderr": result.stderr[-2000:],
                "stdout": result.stdout[-2000:],
            }
        # generate.py writes output/{slug}.html. Locate it via the build report.
        report_path = BASE_DIR / "build_report.json"
        html_path: Path | None = None
        if report_path.exists():
            try:
                report = json.loads(report_path.read_text())
                html_rel = report.get("output_file") or report.get("output")
                if html_rel:
                    candidate_path = BASE_DIR / html_rel
                    if candidate_path.exists():
                        html_path = candidate_path
            except json.JSONDecodeError:
                pass
        if html_path is None:
            # Fallback: pick newest file in output/ matching candidate slug.
            matches = sorted(
                OUTPUT_DIR.glob(f"*{slugify(cand.business_name)}*.html"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            html_path = matches[0] if matches else None

        return {
            "status": "ok" if html_path else "missing_output",
            "html_file": str(html_path.relative_to(BASE_DIR)) if html_path else "",
        }
    finally:
        if backup is not None:
            DETAILS_PATH.write_bytes(backup)


def deploy_one(html_rel: str) -> dict[str, Any]:
    result = run_subprocess(
        [sys.executable, "deploy.py", html_rel],
        timeout=300,
    )
    if result.returncode != 0:
        return {
            "status": "failed",
            "stderr": result.stderr[-2000:],
            "url": "",
        }
    url = ""
    if DEPLOY_LOG.exists():
        try:
            deploys = json.loads(DEPLOY_LOG.read_text())
            slug = Path(html_rel).stem
            for d in deploys:
                if d.get("slug") == slug:
                    url = d.get("url", "")
                    break
        except json.JSONDecodeError:
            pass
    return {"status": "ok" if url else "missing_url", "url": url}


def build_and_deploy(candidates: list[Candidate]) -> list[dict[str, Any]]:
    """Run build + deploy on each qualified candidate. Write per-slug records."""
    records: list[dict[str, Any]] = []
    for cand in candidates:
        qualified = load_qualified(cand.slug)
        if not qualified or qualified.get("verdict") != "qualified":
            logger.info("skip %s (verdict=%s)", cand.slug, qualified and qualified.get("verdict"))
            continue

        logger.info("build: %s", cand.slug)
        build_result = build_one(cand)
        record: dict[str, Any] = {
            "slug": cand.slug,
            "business_name": cand.business_name,
            "cohort": qualified.get("cohort", ""),
            "build": build_result,
            "built_at": datetime.now(timezone.utc).isoformat(),
        }
        if build_result.get("status") == "ok":
            logger.info("deploy: %s", cand.slug)
            deploy_result = deploy_one(build_result["html_file"])
            record["deploy"] = deploy_result
            record["deployed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            record["deploy"] = {"status": "skipped", "url": ""}

        out_path = WORKSPACE / f"{cand.slug}_built.json"
        out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        records.append(record)

    return records


def load_candidates(path: Path) -> list[Candidate]:
    raw = json.loads(path.read_text())
    out: list[Candidate] = []
    for item in raw:
        item.pop("discovered_at", None)
        out.append(Candidate(**item))
    return out


def parse_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="No-website prospecting pipeline")
    parser.add_argument("--cities", type=str, default="")
    parser.add_argument("--categories", type=str, default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument(
        "--build-qualified",
        action="store_true",
        help="Skip discovery; build+deploy candidates whose _qualified.json verdict is 'qualified'.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    candidates_path = WORKSPACE / "candidates.json"

    if args.build_qualified:
        if not candidates_path.exists():
            logger.error("candidates.json missing at %s", candidates_path)
            return 2
        candidates = load_candidates(candidates_path)
    else:
        cities = parse_list(args.cities)
        categories = parse_list(args.categories)
        if not cities or not categories:
            logger.error("--cities and --categories required for discovery")
            return 2
        candidates = discover(cities, categories, args.limit)
        # Only keep records without a live "ok" website; others will be rejected anyway.
        enrich_health(candidates)
        no_ok = [c for c in candidates if (c.website_health or {}).get("status") != "ok"]
        dropped = len(candidates) - len(no_ok)
        logger.info("kept %d candidates (dropped %d with live sites)", len(no_ok), dropped)
        candidates = no_ok
        write_candidates(candidates, candidates_path)

    if args.discover_only:
        logger.info("discover-only mode: stopping before build/deploy")
        return 0

    records = build_and_deploy(candidates)
    summary = {
        "total_candidates": len(candidates),
        "built": sum(1 for r in records if r["build"].get("status") == "ok"),
        "deployed": sum(1 for r in records if r.get("deploy", {}).get("status") == "ok"),
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = WORKSPACE / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    logger.info("summary: %s", summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
