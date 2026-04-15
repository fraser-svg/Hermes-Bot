#!/usr/bin/env python3
"""Hermes pixel prospector — find businesses running ads but missing tracking pixels.

Searches Google Maps for businesses with websites, fetches each site,
checks for Facebook Pixel, Google Ads remarketing, TikTok pixel, and
tag managers. Businesses spending on ads but missing retargeting = high
value leads leaking conversions.

Usage:
    python3 prospect_no_pixel.py "electrician" "Edinburgh"
    python3 prospect_no_pixel.py "plumber" "Glasgow" --limit 20 --top 5
    python3 prospect_no_pixel.py "dentist" "London" --company "Smile"
    python3 prospect_no_pixel.py "electrician" "Edinburgh" --meta-ads

Requires GOOGLE_MAPS_API in .env
Optional: META_AD_LIBRARY_TOKEN in .env for Meta Ad Library lookups
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from core.prospect import BASE_DIR, PROSPECTS_DIR, get_google_key, search_places


# ---------------------------------------------------------------------------
# Page fetching (reuse pattern from prospect_poor_websites_v2)
# ---------------------------------------------------------------------------

@dataclass
class PageFetch:
    final_url: str
    html: str
    status: str
    http_status: int


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


def fetch_page(url: str, timeout: int = 15) -> PageFetch:
    url = normalize_url(url)
    if not url:
        return PageFetch("", "", "missing_url", 0)

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HermesPixelAudit/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return PageFetch(resp.geturl(), "", "non_html", resp.status)
            html = resp.read(800_000).decode("utf-8", errors="ignore")
            return PageFetch(resp.geturl(), html, "ok", resp.status)
    except HTTPError as e:
        return PageFetch(url, "", f"http_{e.code}", e.code)
    except URLError:
        return PageFetch(url, "", "network_error", 0)
    except Exception:
        return PageFetch(url, "", "fetch_error", 0)


# ---------------------------------------------------------------------------
# Pixel / tracking detection
# ---------------------------------------------------------------------------

@dataclass
class PixelAudit:
    facebook_pixel: bool = False
    facebook_pixel_id: str = ""
    google_ads_remarketing: bool = False
    google_ads_id: str = ""
    google_analytics: bool = False
    google_tag_manager: bool = False
    tiktok_pixel: bool = False
    linkedin_insight: bool = False
    hotjar: bool = False
    any_tag_manager: bool = False
    any_retargeting: bool = False
    tracking_score: int = 0  # 0-100, higher = more tracking
    missing: list[str] = field(default_factory=list)
    found: list[str] = field(default_factory=list)


def audit_pixels(html: str) -> PixelAudit:
    """Scan HTML for tracking pixels and tag managers."""
    if not html:
        return PixelAudit(missing=["all — page not fetched"], tracking_score=0)

    audit = PixelAudit()
    low = html.lower()

    # --- Facebook Pixel ---
    if "fbq(" in low or "connect.facebook.net" in low or "fbevents.js" in low:
        audit.facebook_pixel = True
        audit.found.append("facebook_pixel")
        # Extract pixel ID
        m = re.search(r"fbq\s*\(\s*['\"]init['\"],\s*['\"](\d+)['\"]", html)
        if m:
            audit.facebook_pixel_id = m.group(1)
    else:
        audit.missing.append("facebook_pixel")

    # --- Google Ads remarketing ---
    gads_patterns = [
        r"googleads\.g\.doubleclick\.net",
        r"gtag\s*\(\s*['\"]config['\"],\s*['\"]AW-(\d+)['\"]",
        r"google_tag_data",
        r"conversion\.js",
        r"AW-\d+",
    ]
    for pat in gads_patterns:
        m = re.search(pat, html, re.I)
        if m:
            audit.google_ads_remarketing = True
            if m.lastindex and m.lastindex >= 1:
                audit.google_ads_id = f"AW-{m.group(1)}"
            break
    if audit.google_ads_remarketing:
        audit.found.append("google_ads_remarketing")
    else:
        audit.missing.append("google_ads_remarketing")

    # --- Google Analytics ---
    ga_patterns = [
        r"google-analytics\.com/analytics\.js",
        r"googletagmanager\.com/gtag/js",
        r"gtag\s*\(\s*['\"]config['\"],\s*['\"]G-",
        r"gtag\s*\(\s*['\"]config['\"],\s*['\"]UA-",
        r"google-analytics\.com/ga\.js",
    ]
    for pat in ga_patterns:
        if re.search(pat, html, re.I):
            audit.google_analytics = True
            audit.found.append("google_analytics")
            break
    if not audit.google_analytics:
        audit.missing.append("google_analytics")

    # --- Google Tag Manager ---
    if "googletagmanager.com/gtm.js" in low or "googletagmanager.com/ns.html" in low:
        audit.google_tag_manager = True
        audit.any_tag_manager = True
        audit.found.append("google_tag_manager")
    else:
        audit.missing.append("google_tag_manager")

    # --- TikTok Pixel ---
    if "analytics.tiktok.com" in low or "ttq.load" in low:
        audit.tiktok_pixel = True
        audit.found.append("tiktok_pixel")
    else:
        audit.missing.append("tiktok_pixel")

    # --- LinkedIn Insight Tag ---
    if "snap.licdn.com" in low or "linkedin.com/px" in low or "_linkedin_partner_id" in low:
        audit.linkedin_insight = True
        audit.found.append("linkedin_insight")
    else:
        audit.missing.append("linkedin_insight")

    # --- Hotjar ---
    if "hotjar.com" in low or "static.hotjar.com" in low:
        audit.hotjar = True
        audit.found.append("hotjar")

    # --- Any tag manager at all ---
    if not audit.any_tag_manager:
        alt_tms = ["segment.com", "segment.io", "cdn.mxpnl.com", "matomo", "plausible.io"]
        for tm in alt_tms:
            if tm in low:
                audit.any_tag_manager = True
                break

    # --- Retargeting verdict ---
    audit.any_retargeting = (
        audit.facebook_pixel
        or audit.google_ads_remarketing
        or audit.tiktok_pixel
        or audit.linkedin_insight
    )

    # --- Tracking score (0-100) ---
    score = 0
    if audit.facebook_pixel:
        score += 25
    if audit.google_ads_remarketing:
        score += 25
    if audit.google_analytics:
        score += 15
    if audit.google_tag_manager:
        score += 15
    if audit.tiktok_pixel:
        score += 10
    if audit.linkedin_insight:
        score += 5
    if audit.hotjar:
        score += 5
    audit.tracking_score = min(score, 100)

    return audit


# ---------------------------------------------------------------------------
# Meta Ad Library lookup (optional)
# ---------------------------------------------------------------------------

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


def get_meta_token() -> str:
    env = load_env()
    import os
    return os.environ.get("META_AD_LIBRARY_TOKEN") or env.get("META_AD_LIBRARY_TOKEN") or ""


def check_meta_ads_scrape(business_name: str, country: str = "GB") -> dict:
    """Scrape the public Meta Ad Library web UI — no API token, no identity
    verification required. Slower than the API and IP-rate-limited, but does
    not require a Meta dev account. Use as default when META_AD_LIBRARY_TOKEN
    is absent."""
    import sys as _sys
    scripts_dir = BASE_DIR / ".claude/skills/ad-verification/scripts"
    _sys.path.insert(0, str(scripts_dir))
    try:
        from check_meta_ad_library import check as _scraper_check
    except ImportError as e:
        return {"active_ads": -1, "is_advertiser": None, "note": f"scraper_import_failed: {e}"}

    result = _scraper_check(business_name, country=country)
    if result.get("error"):
        return {"active_ads": -1, "is_advertiser": None, "note": result["error"]}
    ad_count = int(result.get("ad_count") or 0)
    has_ads = result.get("has_meta_ads")
    return {
        "active_ads": ad_count,
        "is_advertiser": has_ads if has_ads is not None else (ad_count > 0),
        "ad_samples": [
            {
                "page_name": "",
                "body_preview": (cr.get("headline") or cr.get("body") or "")[:120],
            }
            for cr in (result.get("sample_creatives") or [])[:3]
        ],
        "note": "scraped_public_ui",
    }


def check_meta_ads(business_name: str, country: str = "GB") -> dict:
    """Check Meta Ad Library for active ads by this business.

    Returns dict with 'active_ads' count and 'is_advertiser' bool.
    Prefers the official API if META_AD_LIBRARY_TOKEN is set; otherwise
    falls back to scraping the public Ad Library web UI via Playwright.
    """
    token = get_meta_token()
    if not token:
        return check_meta_ads_scrape(business_name, country=country)

    search_term = quote(business_name)
    url = (
        f"https://graph.facebook.com/v21.0/ads_archive"
        f"?search_terms={search_term}"
        f"&ad_reached_countries=['{country}']"
        f"&ad_active_status=active"
        f"&fields=id,ad_creative_bodies,page_name"
        f"&limit=5"
        f"&access_token={token}"
    )

    req = Request(url, headers={"Accept": "application/json"}, method="GET")

    try:
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            ads = body.get("data", [])
            return {
                "active_ads": len(ads),
                "is_advertiser": len(ads) > 0,
                "ad_samples": [
                    {
                        "page_name": ad.get("page_name", ""),
                        "body_preview": (ad.get("ad_creative_bodies", [""])[0] or "")[:120],
                    }
                    for ad in ads[:3]
                ],
            }
    except HTTPError as e:
        return {"active_ads": -1, "is_advertiser": None, "note": f"meta_api_error_{e.code}"}
    except Exception:
        return {"active_ads": -1, "is_advertiser": None, "note": "meta_api_fetch_error"}


# ---------------------------------------------------------------------------
# Prospect assembly
# ---------------------------------------------------------------------------

def place_to_record(
    place: dict,
    category: str,
    city: str,
    check_meta: bool = False,
) -> dict | None:
    """Build prospect record for a business with a website."""
    name = place.get("displayName", {}).get("text", "Unknown Business")
    website = place.get("websiteUri", "")
    if not website:
        return None  # no website = different prospecting vector

    rating = place.get("rating", 0)
    review_count = place.get("userRatingCount", 0)
    maps_url = place.get("googleMapsUri", "")
    phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber", "")
    address = place.get("formattedAddress", city)

    print(f"  Scanning: {name} — {website}")
    page = fetch_page(website)
    pixel_audit = audit_pixels(page.html)

    record: dict = {
        "business_name": name,
        "business_category": category.lower(),
        "city": city,
        "address": address,
        "phone_number": phone,
        "website_url": website,
        "google_maps_url": maps_url,
        "rating": rating,
        "review_count": review_count,
        "pixel_audit": {
            "tracking_score": pixel_audit.tracking_score,
            "any_retargeting": pixel_audit.any_retargeting,
            "facebook_pixel": pixel_audit.facebook_pixel,
            "facebook_pixel_id": pixel_audit.facebook_pixel_id,
            "google_ads_remarketing": pixel_audit.google_ads_remarketing,
            "google_ads_id": pixel_audit.google_ads_id,
            "google_analytics": pixel_audit.google_analytics,
            "google_tag_manager": pixel_audit.google_tag_manager,
            "tiktok_pixel": pixel_audit.tiktok_pixel,
            "linkedin_insight": pixel_audit.linkedin_insight,
            "hotjar": pixel_audit.hotjar,
            "any_tag_manager": pixel_audit.any_tag_manager,
            "missing": pixel_audit.missing,
            "found": pixel_audit.found,
        },
        "fetch_status": page.status,
        "_source": "google_maps_pixel_audit",
    }

    if check_meta:
        record["meta_ads"] = check_meta_ads(name)

    # Opportunity = high reviews + low tracking = leaking money
    reputation_score = min((rating or 0) * (review_count or 0), 500)
    leak_score = 100 - pixel_audit.tracking_score  # higher = more leaking
    record["opportunity_score"] = round(reputation_score * (leak_score / 100), 1)

    return record


def _rendered_pixel_override(rows: list[dict]) -> list[dict]:
    """Re-scan every record with audit_pixels_v2 (rendered browser) and
    overwrite the static `pixel_audit` / `fetch_status` fields. Static regex
    misses GTM-injected pixels — see validation/eval_detectors.py for ground-
    truth eval proving static recall = 0.0 on Stripe/HubSpot/Shopify. Anything
    the rendered scan cannot classify (blocked, error, timeout) leaves
    `pixel_audit_status != 'ok'` so downstream qualifier treats it as unknown
    rather than 'no pixel'."""
    import sys as _sys
    _sys.path.insert(0, str(BASE_DIR / ".claude/skills/ad-verification/scripts"))
    from audit_pixels_v2 import audit_batch as _v2_batch

    print(f"\nRendered pixel audit ({len(rows)} sites, multi-page + consent-aware)...\n")
    audited = _v2_batch(list(rows))
    for r in audited:
        v2 = r.get("pixels_v2") or {}
        status = v2.get("status", "error")
        r["pixel_audit_status"] = status
        if status != "ok":
            # Do not overwrite static audit with partial/blocked data — leave
            # record's pixel_audit intact but flag so qualifier treats as gap
            r["pixel_audit"]["audit_gap"] = v2.get("error") or status
            continue
        r["pixel_audit"].update({
            "facebook_pixel": v2.get("facebook_pixel", False),
            "google_ads_remarketing": v2.get("google_ads_remarketing", False),
            "google_ads_conversion": v2.get("google_ads_conversion", False),
            "google_analytics": v2.get("google_analytics", False),
            "google_tag_manager": v2.get("google_tag_manager", False),
            "linkedin_insight": v2.get("linkedin_insight", False),
            "tiktok_pixel": v2.get("tiktok_pixel", False),
            "any_retargeting": v2.get("any_retargeting", False),
            "pages_scanned": v2.get("pages_scanned", []),
            "source": "playwright_v2",
        })
    return audited


def run(
    category: str,
    location: str,
    limit: int,
    top: int,
    company_filter: str,
    check_meta: bool,
    rendered: bool = True,
) -> list[dict]:
    api_key = get_google_key()
    places = search_places(category, location, api_key, limit)

    print(f"\nFound {len(places)} businesses. Scanning pixels...\n")

    rows: list[dict] = []
    filter_low = company_filter.lower().strip() if company_filter else ""

    for p in places:
        if p.get("businessStatus", "") == "CLOSED_PERMANENTLY":
            continue
        if not p.get("websiteUri"):
            continue

        name = p.get("displayName", {}).get("text", "")
        if filter_low and filter_low not in name.lower():
            continue

        record = place_to_record(p, category, location, check_meta=check_meta)
        if record:
            rows.append(record)

    if rendered:
        rows = _rendered_pixel_override(rows)

    # Sort: no retargeting first, then by opportunity score (highest first)
    rows.sort(key=lambda r: (
        r["pixel_audit"]["any_retargeting"],  # False (no retargeting) sorts first
        -r["opportunity_score"],
    ))

    if top > 0:
        rows = rows[:top]
    return rows


def save(results: list[dict], category: str, location: str) -> Path:
    PROSPECTS_DIR.mkdir(exist_ok=True)
    slug = f"{category.lower()}-{location.lower().replace(' ', '-')}-no-pixel"
    out = PROSPECTS_DIR / f"{slug}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_results(results: list[dict]) -> None:
    no_retarget = [r for r in results if not r["pixel_audit"]["any_retargeting"]]
    has_retarget = [r for r in results if r["pixel_audit"]["any_retargeting"]]

    print(f"\n{'=' * 60}")
    print(f"  NO RETARGETING PIXEL ({len(no_retarget)} leads) — LEAKING MONEY")
    print(f"{'=' * 60}\n")

    for i, r in enumerate(no_retarget, 1):
        pa = r["pixel_audit"]
        stars = f"{r['rating']}/5" if r['rating'] else "no rating"
        reviews = f"{r['review_count']} reviews" if r['review_count'] else "no reviews"
        print(f"  [{i}] {r['business_name']}")
        print(f"      {stars} | {reviews} | opp={r['opportunity_score']}")
        print(f"      site: {r['website_url']}")
        print(f"      tracking: {pa['tracking_score']}/100")
        print(f"      found: {', '.join(pa['found']) or 'nothing'}")
        print(f"      missing: {', '.join(pa['missing'][:5])}")
        if r.get("meta_ads", {}).get("is_advertiser"):
            print(f"      META ADS: ACTIVE — spending money but no pixel!")
        print()

    if has_retarget:
        print(f"  --- Has retargeting ({len(has_retarget)}): lower priority ---")
        for r in has_retarget[:3]:
            pa = r["pixel_audit"]
            print(f"  {r['business_name']} | tracking={pa['tracking_score']}/100 | {', '.join(pa['found'])}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find businesses with websites but missing tracking pixels."
    )
    parser.add_argument("category", help="Business category (electrician, plumber, etc.)")
    parser.add_argument("location", help="City or area to search")
    parser.add_argument("--limit", type=int, default=20, help="Max Google Maps results")
    parser.add_argument("--top", type=int, default=20, help="Show top N results")
    parser.add_argument("--company", default="", help="Filter by business name contains")
    parser.add_argument("--meta-ads", action="store_true", help="Check Meta Ad Library (needs META_AD_LIBRARY_TOKEN)")
    parser.add_argument("--static-only", action="store_true", help="Skip rendered pixel audit — USE ONLY FOR DEBUGGING. Static regex misses GTM-injected pixels and produces false-positive leaks.")
    args = parser.parse_args()

    print("=" * 60)
    print("  HERMES PIXEL PROSPECTOR")
    print(f"  Finding {args.category}s in {args.location} missing tracking pixels")
    print("=" * 60)

    try:
        results = run(
            args.category,
            args.location,
            args.limit,
            args.top,
            args.company,
            check_meta=args.meta_ads,
            rendered=not args.static_only,
        )
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    if not results:
        print("No businesses with websites found in this search.")
        return 0

    out = save(results, args.category, args.location)
    print(f"\nSaved {len(results)} results to {out}")

    print_results(results)

    no_retarget = sum(1 for r in results if not r["pixel_audit"]["any_retargeting"])
    print(f"\nSUMMARY: {no_retarget}/{len(results)} businesses have NO retargeting pixel.")
    if no_retarget:
        print("These businesses are paying for ads/traffic and losing ~97% of visitors forever.")
        print("Pitch: website + pixel setup + retargeting management = £299-499/mo tier.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
