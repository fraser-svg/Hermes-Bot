"""Batch-driver: crawl every Scotland city × whitelisted category.

Iterates the city list from
`.claude/skills/retarget-prospector/references/scotland_cities.md`, running
`crawl_city.py` for each (city, category) pair. Tier-ordered so the largest
pools return first.

Idempotent: skips pairs whose output file was modified in the last
`--stale-days` days (default 14), unless `--force` is set.

Usage:
    python3 scripts/crawl_scotland.py --tier 1 --dry-run
    python3 scripts/crawl_scotland.py --tier 1
    python3 scripts/crawl_scotland.py                 # all tiers
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
CRAWL_CITY: Final[Path] = ROOT / "scripts" / "crawl_city.py"


@dataclass(frozen=True)
class CityEntry:
    slug: str
    tier: int


# Source: .claude/skills/retarget-prospector/references/scotland_cities.md
SCOTLAND_CITIES: Final[tuple[CityEntry, ...]] = (
    # Tier 1 — major cities
    CityEntry("glasgow", 1),
    CityEntry("edinburgh", 1),
    CityEntry("aberdeen", 1),
    CityEntry("dundee", 1),
    # Tier 2 — mid-sized
    CityEntry("paisley", 2),
    CityEntry("east-kilbride", 2),
    CityEntry("livingston", 2),
    CityEntry("hamilton", 2),
    CityEntry("cumbernauld", 2),
    CityEntry("kirkcaldy", 2),
    CityEntry("dunfermline", 2),
    CityEntry("ayr", 2),
    CityEntry("perth", 2),
    CityEntry("inverness", 2),
    CityEntry("kilmarnock", 2),
    CityEntry("greenock", 2),
    CityEntry("coatbridge", 2),
    CityEntry("glenrothes", 2),
    CityEntry("airdrie", 2),
    CityEntry("stirling", 2),
    CityEntry("falkirk", 2),
    # Tier 3 — smaller towns
    CityEntry("st-andrews", 3),
    CityEntry("dumfries", 3),
    CityEntry("motherwell", 3),
    CityEntry("wishaw", 3),
    CityEntry("bearsden", 3),
    CityEntry("bishopbriggs", 3),
    CityEntry("newton-mearns", 3),
    CityEntry("clydebank", 3),
    CityEntry("renfrew", 3),
    CityEntry("rutherglen", 3),
    CityEntry("cambuslang", 3),
    CityEntry("elgin", 3),
    CityEntry("oban", 3),
    CityEntry("fort-william", 3),
)

# Priority categories for Tier 1 runs (highest Google-Ads-spender density).
PRIORITY_CATEGORIES: Final[tuple[str, ...]] = (
    "dentist",
    "aesthetic clinic",
    "cosmetic clinic",
    "solicitor",
    "accountant",
    "financial advisor",
    "mortgage broker",
    "optician",
    "vet",
    "architect",
    "interior designer",
    "wedding venue",
    "private school",
    "driving school",
)

# Smaller category set for Tier 2/3 to keep pool-vs-cost sane.
COMPACT_CATEGORIES: Final[tuple[str, ...]] = (
    "dentist",
    "aesthetic clinic",
    "solicitor",
    "accountant",
    "mortgage broker",
)


def output_path(category: str, city: str) -> Path:
    slug = f"{category.lower()}-{city.lower()}-no-pixel"
    return ROOT / "prospects" / f"{slug}.json"


def is_fresh(path: Path, stale_days: int) -> bool:
    if not path.exists():
        return False
    age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    return age < stale_days * 86400


def pair_list(
    tier_filter: int | None,
    cities: tuple[CityEntry, ...] = SCOTLAND_CITIES,
) -> list[tuple[CityEntry, str]]:
    out: list[tuple[CityEntry, str]] = []
    for city in cities:
        if tier_filter is not None and city.tier != tier_filter:
            continue
        cats = PRIORITY_CATEGORIES if city.tier == 1 else COMPACT_CATEGORIES
        for cat in cats:
            out.append((city, cat))
    return out


def run_one(city_slug: str, category: str, limit: int, force: bool) -> int:
    cmd = [
        sys.executable,
        str(CRAWL_CITY),
        "--city",
        city_slug,
        "--category",
        category,
        "--limit",
        str(limit),
    ]
    if force:
        cmd.append("--force")
    print(f"$ {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Batch crawler: iterates Scotland cities × categories per the "
            "retarget-prospector ICP whitelist."
        )
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        help="Only run this tier (1 = major cities, 2 = mid, 3 = smaller).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max Google Maps results per (city, category) pair.",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=14,
        help="Skip pairs whose output is newer than this many days.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore staleness check, re-crawl every pair.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate the pairs that would run without calling crawl_city.",
    )
    parser.add_argument(
        "--sleep-between",
        type=float,
        default=2.0,
        help="Seconds to sleep between pair runs (rate-limit courtesy).",
    )
    args = parser.parse_args()

    pairs = pair_list(args.tier)
    pairs.sort(key=lambda p: (p[0].tier, p[0].slug, p[1]))

    print(
        f"planning {len(pairs)} (city, category) pairs "
        f"across {len({p[0].slug for p in pairs})} cities"
    )

    skipped = 0
    ran = 0
    failed: list[tuple[str, str, int]] = []

    for entry, category in pairs:
        out = output_path(category, entry.slug)
        if not args.force and is_fresh(out, args.stale_days):
            skipped += 1
            print(
                f"[skip fresh <{args.stale_days}d] tier{entry.tier} "
                f"{entry.slug} / {category}"
            )
            continue

        print(f"[run ] tier{entry.tier} {entry.slug} / {category}")
        if args.dry_run:
            ran += 1
            continue

        rc = run_one(entry.slug, category, args.limit, args.force)
        if rc == 0:
            ran += 1
        else:
            failed.append((entry.slug, category, rc))
            print(
                f"[fail] tier{entry.tier} {entry.slug} / {category} rc={rc}",
                file=sys.stderr,
            )
        time.sleep(args.sleep_between)

    print()
    print(f"summary: ran={ran}  skipped_fresh={skipped}  failed={len(failed)}")
    if failed:
        print("failed pairs:")
        for slug, cat, rc in failed:
            print(f"  {slug} / {cat}  rc={rc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
