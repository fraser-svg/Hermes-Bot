#!/usr/bin/env python3
"""Emit outreach CSV for no-website prospects.

Merges:
    - _workspace/nowebsite/candidates.json (all discovered candidates)
    - _workspace/nowebsite/{slug}_qualified.json (qualifier agent verdicts)
    - _workspace/nowebsite/{slug}_built.json (build + deploy results)
    - prospects/deploys.json (canonical Cloudflare URL source)

Emits output/nowebsite_outreach.csv with:
    business_name, city, address, phone_number, phone_e164, email,
    email_source, website_url, slug, rating, review_count, cohort,
    deployed_at

Dedupes on slug; if the CSV exists, the new rows replace same-slug rows.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "_workspace" / "nowebsite"
OUTPUT_DIR = BASE_DIR / "output"
DEPLOY_LOG = BASE_DIR / "prospects" / "deploys.json"
DEFAULT_CSV = OUTPUT_DIR / "nowebsite_outreach.csv"

COLUMNS: tuple[str, ...] = (
    "business_name",
    "city",
    "address",
    "phone_number",
    "phone_e164",
    "email",
    "email_source",
    "website_url",
    "current_website_url",
    "slug",
    "rating",
    "review_count",
    "cohort",
    "deployed_at",
)

logger = logging.getLogger("nowebsite.csv")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        logger.warning("invalid JSON in %s: %s", path, e)
        return None


def to_e164(phone: str, default_country: str = "44") -> str:
    """Best-effort E.164 for UK phones. Non-UK numbers pass through cleaned."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return ""
    if phone.strip().startswith("+"):
        return f"+{digits}"
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    if digits.startswith("0"):
        return f"+{default_country}{digits[1:]}"
    return f"+{digits}"


def load_deploy_map() -> dict[str, dict[str, Any]]:
    data = load_json(DEPLOY_LOG)
    if not isinstance(data, list):
        return {}
    return {d.get("slug", ""): d for d in data if d.get("slug")}


def collect_rows(workspace: Path, deploys: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    candidates = load_json(workspace / "candidates.json") or []
    rows: list[dict[str, str]] = []

    for cand in candidates:
        slug = cand.get("slug", "")
        if not slug:
            continue

        qualified = load_json(workspace / f"{slug}_qualified.json") or {}
        if qualified.get("verdict") != "qualified":
            continue

        built = load_json(workspace / f"{slug}_built.json") or {}
        deploy_record = deploys.get(slug, {})
        deploy_info = built.get("deploy", {}) if built else {}
        website_url = deploy_info.get("url") or deploy_record.get("url", "")
        deployed_at = built.get("deployed_at") or deploy_record.get("deployed_at", "")

        phone = cand.get("phone_number", "") or ""
        row = {
            "business_name": cand.get("business_name", ""),
            "city": cand.get("city", ""),
            "address": cand.get("address", ""),
            "phone_number": phone,
            "phone_e164": to_e164(phone),
            "email": cand.get("email", ""),
            "email_source": cand.get("email_source", "not_found" if not cand.get("email") else "manual"),
            "website_url": website_url,
            "current_website_url": cand.get("website_url", "") or "",
            "slug": slug,
            "rating": str(cand.get("rating", "")),
            "review_count": str(cand.get("review_count", "")),
            "cohort": qualified.get("cohort", ""),
            "deployed_at": deployed_at,
        }
        rows.append(row)

    return rows


def merge_with_existing(rows: list[dict[str, str]], csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        return rows
    existing: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            existing.append({col: raw.get(col, "") for col in COLUMNS})

    by_slug = {r["slug"]: r for r in existing if r.get("slug")}
    for r in rows:
        by_slug[r["slug"]] = r
    return list(by_slug.values())


def write_csv(rows: list[dict[str, str]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarize(rows: list[dict[str, str]]) -> dict[str, int]:
    cohort_counts: dict[str, int] = {}
    for r in rows:
        cohort_counts[r["cohort"]] = cohort_counts.get(r["cohort"], 0) + 1
    with_url = sum(1 for r in rows if r["website_url"])
    return {
        "total": len(rows),
        "with_live_url": with_url,
        **{f"cohort_{k or 'unknown'}": v for k, v in cohort_counts.items()},
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit no-website outreach CSV")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=WORKSPACE,
        help="Workspace directory with candidates.json and per-slug JSONs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CSV,
        help="Destination CSV path.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    deploys = load_deploy_map()
    new_rows = collect_rows(args.workspace, deploys)
    merged = merge_with_existing(new_rows, args.output)
    write_csv(merged, args.output)
    stats = summarize(merged)
    logger.info("wrote %s (%s)", args.output, stats)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
