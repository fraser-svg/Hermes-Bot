#!/usr/bin/env python3
"""Aggregate all Scotland no-pixel JSONs into a single candidates file.

Dedups on (domain, phone_e164). Applies tier filter:
    Tier 1: rating >= 4.0 AND reviews >= 30
    Tier 2: rating >= 4.5 AND reviews 15-29
    else: dropped

Output: _workspace/retarget_scotland/scotland_candidates.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
PROSPECTS = BASE / "prospects"
OUT_DIR = BASE / "_workspace" / "retarget_scotland"
OUT = OUT_DIR / "scotland_candidates.json"


def domain_of(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def phone_e164(raw: str) -> str:
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    if digits.startswith("44"):
        return "+" + digits
    if digits.startswith("0"):
        return "+44" + digits[1:]
    return "+" + digits


def tier_for(rating: float, reviews: int) -> str | None:
    if rating is None or reviews is None:
        return None
    if rating >= 4.0 and reviews >= 30:
        return "tier1"
    if rating >= 4.5 and 15 <= reviews < 30:
        return "tier2"
    return None


def slugify_source(path: Path) -> str:
    return path.stem.replace("-no-pixel", "")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(PROSPECTS.glob("*-no-pixel.json"))
    print(f"found {len(files)} no-pixel files", file=sys.stderr)

    seen: dict[tuple[str, str], dict] = {}
    stats = {"total_rows": 0, "dropped_tier": 0, "dedup_collapsed": 0, "written": 0}

    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            continue
        src = slugify_source(f)
        category, _, city = src.partition("-")
        for row in data:
            stats["total_rows"] += 1
            rating = row.get("rating") or 0.0
            reviews = row.get("review_count") or 0
            tier = tier_for(rating, reviews)
            if not tier:
                stats["dropped_tier"] += 1
                continue
            website = row.get("website_url") or ""
            phone = row.get("phone_number") or ""
            dom = domain_of(website)
            e164 = phone_e164(phone)
            key = (dom or f.name, e164 or row.get("business_name", ""))
            if key in seen:
                stats["dedup_collapsed"] += 1
                continue
            pix = row.get("pixels_v2") or row.get("pixel_audit") or {}
            slug = f"{category}-{city}-" + re.sub(r"[^a-z0-9]+", "-", (row.get("business_name") or "").lower()).strip("-")
            seen[key] = {
                "slug": slug,
                "business_name": row.get("business_name"),
                "business_category": row.get("business_category") or category,
                "city": row.get("city") or city,
                "address": row.get("address"),
                "phone_number": phone,
                "phone_e164": e164,
                "website_url": website,
                "domain": dom,
                "google_maps_url": row.get("google_maps_url"),
                "rating": rating,
                "review_count": reviews,
                "tier": tier,
                "fetch_status": row.get("fetch_status"),
                "pixels_v2": {
                    "facebook_pixel": pix.get("facebook_pixel"),
                    "google_ads_remarketing": pix.get("google_ads_remarketing"),
                    "google_ads_conversion": pix.get("google_ads_conversion"),
                    "google_analytics": pix.get("google_analytics"),
                    "google_tag_manager": pix.get("google_tag_manager"),
                    "linkedin_insight": pix.get("linkedin_insight"),
                    "tiktok_pixel": pix.get("tiktok_pixel"),
                },
                "_source_file": f.name,
            }

    stats["written"] = len(seen)
    OUT.write_text(json.dumps(list(seen.values()), indent=2))
    print(json.dumps(stats, indent=2), file=sys.stderr)
    print(f"wrote {OUT} ({stats['written']} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
