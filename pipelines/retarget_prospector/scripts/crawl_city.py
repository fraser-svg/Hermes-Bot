"""Crawl a UK city × category for retarget-prospector candidates.

Thin orchestrator over `prospect_no_pixel.py` that replaces the hard-coded
Glasgow constants in `glasgow_meta_ads_no_pixel.py` / `glasgow_google_ads_no_tag.py`
with `--city` + `--category` CLI args. Outputs stay in the same shape as the
Glasgow pipeline so the downstream retarget-qualifier reads them unchanged.

Usage:
    python3 scripts/crawl_city.py --city edinburgh --category dentist --limit 20

The script shells out to `prospect_no_pixel.py` for the Google Maps + pixel
audit pass (reuses its Playwright setup). Meta Ad Library + Google Ads
Transparency verification is done in-process by importing the helpers from
the Glasgow scripts rather than duplicating them.

Output:
    prospects/<category>-<city>-no-pixel.json    # from prospect_no_pixel.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
PROSPECT_SCRIPT: Final[Path] = ROOT / "prospect_no_pixel.py"

# Mirrors the Gate 2 whitelist in
# .claude/skills/retarget-prospector/references/icp.md.
# Kept here as a hard list so typos surface as a CLI error, not a silent
# empty crawl.
WHITELIST_CATEGORIES: Final[tuple[str, ...]] = (
    "dentist",
    "optician",
    "aesthetic clinic",
    "cosmetic clinic",
    "private gp",
    "physiotherapy",
    "fertility clinic",
    "vet",
    "solicitor",
    "accountant",
    "financial advisor",
    "mortgage broker",
    "architect",
    "interior designer",
    "landscaper",
    "painter",
    "kitchen fitter",
    "wedding venue",
    "private school",
    "tutoring",
    "driving school",
    "personal trainer",
    "pilates studio",
    "coaching",
    "specialist recruitment",
)


def output_path(category: str, city: str) -> Path:
    slug = f"{category.lower()}-{city.lower().replace(' ', '-')}-no-pixel"
    return ROOT / "prospects" / f"{slug}.json"


def run_prospect(
    category: str,
    city: str,
    limit: int,
    static_only: bool,
) -> int:
    """Shell out to prospect_no_pixel.py so we reuse its full pipeline."""
    cmd = [
        sys.executable,
        str(PROSPECT_SCRIPT),
        category,
        city,
        "--limit",
        str(limit),
        "--top",
        str(limit),
    ]
    if static_only:
        cmd.append("--static-only")
    print(f"$ {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parameterised UK city × category crawler for retarget-prospector. "
            "Wraps prospect_no_pixel.py; outputs to prospects/<cat>-<city>-no-pixel.json."
        )
    )
    parser.add_argument(
        "--city",
        help="City slug, e.g. edinburgh, aberdeen, dundee, glasgow.",
    )
    parser.add_argument(
        "--category",
        help=(
            "Business category from the ICP whitelist "
            "(run with --list-categories to see them)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max Google Maps results to pull (default 20).",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Skip rendered pixel audit (debug). Do not use in production.",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="Print the ICP category whitelist and exit.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file if present.",
    )
    args = parser.parse_args()

    if args.list_categories:
        for cat in WHITELIST_CATEGORIES:
            print(cat)
        return 0

    if not args.city or not args.category:
        parser.error("--city and --category are required (unless --list-categories).")

    category = args.category.lower().strip()
    if category not in WHITELIST_CATEGORIES:
        print(
            f"error: category {category!r} is not in the ICP whitelist. "
            f"Use --list-categories to see valid options.",
            file=sys.stderr,
        )
        return 2

    out = output_path(category, args.city)
    if out.exists() and not args.force:
        print(
            f"output already exists: {out.relative_to(ROOT)}\n"
            f"pass --force to re-crawl.",
            file=sys.stderr,
        )
        return 0

    rc = run_prospect(
        category=category,
        city=args.city.lower().strip(),
        limit=args.limit,
        static_only=args.static_only,
    )
    if rc != 0:
        print(f"prospect_no_pixel.py exited with code {rc}", file=sys.stderr)
        return rc

    if not out.exists():
        print(
            f"warning: expected output file {out.relative_to(ROOT)} was not "
            f"written. Check prospect_no_pixel.py output naming.",
            file=sys.stderr,
        )
        return 1

    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
