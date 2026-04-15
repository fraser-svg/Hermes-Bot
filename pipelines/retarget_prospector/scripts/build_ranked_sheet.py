"""Build a ranked CSV of qualified retarget-prospector candidates.

Joins the city × category `prospects/<cat>-<city>-no-pixel.json` crawl outputs
with any `*_qualified.json` verdict files emitted by the retarget-qualifier
agent. Drops anything not `qualified`. Sorts by (cohort priority, score desc).

Cohort priority mirrors the ICP Gate 4 pitch value:
    C (active Meta + infra gap) > A (dormant pixel) > B (greenfield)

Output:
    output/ranked_prospects_<YYYYMMDD>.csv

CSV-only by design. No Google Sheets push.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Iterable

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
PROSPECTS_DIR: Final[Path] = ROOT / "prospects"
OUTPUT_DIR: Final[Path] = ROOT / "output"

COHORT_PRIORITY: Final[dict[str, int]] = {"C": 0, "A": 1, "B": 2}

CSV_COLUMNS: Final[tuple[str, ...]] = (
    "cohort",
    "score",
    "city",
    "category",
    "business_name",
    "domain",
    "contact_name",
    "contact_title",
    "linkedin",
    "email",
    "meta_status",
    "google_ads_evidence",
    "verdict",
    "phone",
    "website",
    "rating",
    "review_count",
)


@dataclass(frozen=True)
class Row:
    cohort: str
    score: float
    city: str
    category: str
    business_name: str
    domain: str
    contact_name: str
    contact_title: str
    linkedin: str
    email: str
    meta_status: str
    google_ads_evidence: str
    verdict: str
    phone: str
    website: str
    rating: float | None
    review_count: int | None

    def as_dict(self) -> dict[str, Any]:
        return {col: getattr(self, col) for col in CSV_COLUMNS}


def _domain(url: str | None) -> str:
    if not url:
        return ""
    s = url.lower().split("://", 1)[-1]
    s = s.split("/", 1)[0]
    return s.removeprefix("www.")


def _extract_contact(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return (name, title, linkedin, email) from an enriched row if present."""
    contact = row.get("contact") or {}
    return (
        str(contact.get("name") or ""),
        str(contact.get("title") or ""),
        str(contact.get("linkedin") or ""),
        str(contact.get("email") or ""),
    )


def _meta_status(row: dict[str, Any]) -> str:
    # Prefer qualifier output; fall back to inferring from pixel + ad counts.
    status = row.get("meta_status")
    if status:
        return str(status)
    pa = row.get("pixel_audit") or {}
    has_pixel = bool(pa.get("facebook_pixel"))
    strict_count = int(row.get("strict_count") or 0)
    if has_pixel and strict_count == 0:
        return "pixel_installed_no_ads"
    if not has_pixel and strict_count == 0:
        return "no_pixel_no_ads"
    if not has_pixel and strict_count > 0:
        return "ads_running_no_pixel"
    return "pixel_and_ads_active"


def _google_ads_evidence(row: dict[str, Any]) -> str:
    evidence = row.get("google_ads_evidence")
    if evidence:
        return str(evidence)
    if (row.get("pixel_audit") or {}).get("google_ads_remarketing"):
        return "site_conversion_tag"
    if row.get("google_ads_transparency_hits"):
        return "transparency_center"
    return ""


def _to_row(src: dict[str, Any]) -> Row | None:
    verdict = str(src.get("verdict") or "").lower()
    if verdict and verdict != "qualified":
        return None

    cohort = str(src.get("cohort") or "").upper()
    if cohort not in COHORT_PRIORITY:
        # Unqualified if cohort missing — skip; upstream bug, not our job to guess.
        return None

    name, title, linkedin, email = _extract_contact(src)

    rating_raw = src.get("rating")
    reviews_raw = src.get("review_count")
    try:
        rating = float(rating_raw) if rating_raw is not None else None
    except (TypeError, ValueError):
        rating = None
    try:
        review_count = int(reviews_raw) if reviews_raw is not None else None
    except (TypeError, ValueError):
        review_count = None

    return Row(
        cohort=cohort,
        score=float(src.get("score") or src.get("opportunity_score") or 0.0),
        city=str(src.get("city") or ""),
        category=str(src.get("business_category") or ""),
        business_name=str(src.get("business_name") or ""),
        domain=_domain(src.get("website_url")),
        contact_name=name,
        contact_title=title,
        linkedin=linkedin,
        email=email,
        meta_status=_meta_status(src),
        google_ads_evidence=_google_ads_evidence(src),
        verdict=verdict or "qualified",
        phone=str(src.get("phone_number") or ""),
        website=str(src.get("website_url") or ""),
        rating=rating,
        review_count=review_count,
    )


def _discover_sources(explicit: Iterable[Path] | None) -> list[Path]:
    if explicit:
        return [p for p in explicit if p.exists()]
    patterns = ("*_qualified.json", "*-no-pixel.json")
    found: list[Path] = []
    for pat in patterns:
        found.extend(sorted(PROSPECTS_DIR.glob(pat)))
    # Also include anything the retarget-prospector SKILL dumped under output/.
    found.extend(sorted(OUTPUT_DIR.glob("*_qualified.json")))
    return found


def load_rows(sources: Iterable[Path]) -> list[Row]:
    seen_keys: set[tuple[str, str]] = set()
    rows: list[Row] = []
    for src in sources:
        try:
            data = json.loads(src.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warn: could not read {src}: {exc}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            row = _to_row(item)
            if row is None:
                continue
            key = (row.business_name.lower(), row.city.lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append(row)
    return rows


def sort_rows(rows: list[Row]) -> list[Row]:
    return sorted(
        rows,
        key=lambda r: (COHORT_PRIORITY.get(r.cohort, 99), -r.score, r.city, r.business_name),
    )


def write_csv(rows: list[Row], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Join qualified retarget-prospector rows into a single ranked CSV. "
            "No Google Sheets push — open the CSV in Sheets manually."
        )
    )
    parser.add_argument(
        "--source",
        action="append",
        type=Path,
        help=(
            "Explicit source JSON file(s). Pass multiple --source flags. "
            "If omitted, discovers prospects/*.json + output/*_qualified.json."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path. Defaults to output/ranked_prospects_<YYYYMMDD>.csv.",
    )
    args = parser.parse_args()

    sources = _discover_sources(args.source)
    if not sources:
        print("no source JSON files found; nothing to rank.", file=sys.stderr)
        return 1

    rows = sort_rows(load_rows(sources))
    if not rows:
        print(
            "loaded zero qualified rows. Check that qualifier has run and "
            "rows carry cohort ∈ {A,B,C}.",
            file=sys.stderr,
        )
        return 1

    out = args.out or (
        OUTPUT_DIR
        / f"ranked_prospects_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    )
    write_csv(rows, out)

    by_cohort = {"A": 0, "B": 0, "C": 0}
    for r in rows:
        by_cohort[r.cohort] = by_cohort.get(r.cohort, 0) + 1
    print(
        f"wrote {len(rows)} rows to {out.relative_to(ROOT)}  "
        f"(C={by_cohort.get('C', 0)}  A={by_cohort.get('A', 0)}  "
        f"B={by_cohort.get('B', 0)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
