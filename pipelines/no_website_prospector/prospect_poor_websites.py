#!/usr/bin/env python3
"""Find Google Maps businesses WITH websites and flag poor website quality.

Uses existing prospect.py Google Places pipeline functions (no duplicate API stack).

Usage:
  python3 prospect_poor_websites.py "electrician" "Edinburgh" --limit 20 --top 10
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.prospect import BASE_DIR, PROSPECTS_DIR, get_google_key, search_places


def fetch_html(url: str, timeout: int = 12) -> tuple[str, str]:
    if not url:
        return "", "missing_url"

    # Normalize scheme
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HermesAudit/1.0; +https://example.com)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return "", "non_html"
            html = resp.read(450_000).decode("utf-8", errors="ignore")
            return html, "ok"
    except HTTPError as e:
        return "", f"http_{e.code}"
    except URLError:
        return "", "network_error"
    except Exception:
        return "", "fetch_error"


def has_any(text: str, patterns: list[str]) -> bool:
    t = text.lower()
    return any(p in t for p in patterns)


def audit_html(url: str, html: str, fetch_status: str) -> dict:
    score = 100
    issues: list[str] = []
    wins: list[str] = []

    if fetch_status != "ok":
        return {
            "quality_score": 30,
            "bucket": "poor",
            "issues": [f"site_unreachable:{fetch_status}"],
            "wins": [],
            "signals": {
                "fetch_status": fetch_status,
                "https": url.lower().startswith("https://"),
            },
        }

    low = html.lower()

    # Technical / structure
    has_viewport = "name=\"viewport\"" in low or "name='viewport'" in low
    has_h1 = bool(re.search(r"<h1\b", low))
    nav_links = 0
    nav_match = re.search(r"<nav\b[\s\S]*?</nav>", low)
    if nav_match:
        nav_links = len(re.findall(r"<a\b", nav_match.group(0)))

    if not has_viewport:
        score -= 18
        issues.append("missing_viewport_meta")
    else:
        wins.append("mobile_viewport_present")

    if not has_h1:
        score -= 10
        issues.append("missing_h1")
    else:
        wins.append("has_h1")

    if nav_links > 7:
        score -= 8
        issues.append(f"overloaded_navigation:{nav_links}_links")
    elif nav_links > 0:
        wins.append(f"navigation_depth_ok:{nav_links}_links")

    # Visual age / outdated patterns
    if "<font" in low:
        score -= 15
        issues.append("legacy_font_tags")
    if "<marquee" in low or "<blink" in low:
        score -= 25
        issues.append("obsolete_animation_tags")
    if "table" in low and has_any(low, ["layout", "cellpadding", "cellspacing"]):
        score -= 8
        issues.append("possible_table_based_layout")

    # Conversion signals
    cta_terms = [
        "call now", "book now", "get quote", "request quote", "free quote",
        "contact us", "contact", "get estimate", "request callback", "schedule",
    ]
    has_cta = has_any(low, cta_terms)
    if not has_cta:
        score -= 14
        issues.append("weak_or_missing_cta")
    else:
        wins.append("cta_detected")

    # Trust signals
    trust_terms = [
        "testimonial", "reviews", "google reviews", "licensed", "insured",
        "guarantee", "years experience", "since ", "case study",
    ]
    has_trust = has_any(low, trust_terms)
    if not has_trust:
        score -= 10
        issues.append("weak_trust_signals")
    else:
        wins.append("trust_signals_detected")

    # Efficiency / clarity heuristic
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title_text = (title_match.group(1).strip() if title_match else "")
    if not title_text or len(title_text) < 8:
        score -= 6
        issues.append("weak_title_value_prop")
    else:
        wins.append("title_present")

    # Safety bounds
    score = max(0, min(100, score))
    if score <= 60:
        bucket = "poor"
    elif score <= 75:
        bucket = "average"
    else:
        bucket = "good"

    return {
        "quality_score": score,
        "bucket": bucket,
        "issues": issues,
        "wins": wins,
        "signals": {
            "fetch_status": fetch_status,
            "https": url.lower().startswith("https://"),
            "has_viewport": has_viewport,
            "has_h1": has_h1,
            "nav_links": nav_links,
            "has_cta": has_cta,
            "has_trust": has_trust,
            "title": title_text[:120],
        },
    }


def place_to_record(place: dict, category: str, city: str) -> dict:
    name = place.get("displayName", {}).get("text", "Unknown Business")
    website = place.get("websiteUri", "")
    rating = place.get("rating", 0)
    review_count = place.get("userRatingCount", 0)
    maps_url = place.get("googleMapsUri", "")
    phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber", "")
    address = place.get("formattedAddress", city)

    html, fetch_status = fetch_html(website)
    audit = audit_html(website, html, fetch_status)

    opp_score = round((rating or 0) * (review_count or 0), 1)

    return {
        "business_name": name,
        "business_category": category.lower(),
        "city": city,
        "address": address,
        "phone_number": phone,
        "website_url": website,
        "google_maps_url": maps_url,
        "rating": rating,
        "review_count": review_count,
        "opportunity_score": opp_score,
        "website_audit": audit,
        "_source": "google_maps_poor_website_audit",
    }


def run(category: str, location: str, limit: int, top: int) -> list[dict]:
    api_key = get_google_key()
    places = search_places(category, location, api_key, limit)

    candidates = []
    for place in places:
        status = place.get("businessStatus", "")
        if status == "CLOSED_PERMANENTLY":
            continue
        website = place.get("websiteUri", "")
        if not website:
            continue
        candidates.append(place_to_record(place, category, location))

    # Rank: poor websites first, then biggest opportunity by reviews*rating
    def rank_key(x: dict):
        audit = x.get("website_audit", {})
        return (
            0 if audit.get("bucket") == "poor" else 1,
            audit.get("quality_score", 100),
            -(x.get("opportunity_score", 0)),
        )

    candidates.sort(key=rank_key)
    if top > 0:
        candidates = candidates[:top]

    return candidates


def save(results: list[dict], category: str, location: str) -> Path:
    PROSPECTS_DIR.mkdir(exist_ok=True)
    slug = f"{category.lower()}-{location.lower().replace(' ', '-')}-poor-websites"
    out = PROSPECTS_DIR / f"{slug}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("category")
    parser.add_argument("location")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    print("=" * 56)
    print("HERMES POOR-WEBSITE PROSPECTOR")
    print(f"Category: {args.category} | Location: {args.location}")
    print("=" * 56)

    try:
        results = run(args.category, args.location, args.limit, args.top)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    if not results:
        print("No website-bearing businesses found in this query window.")
        return 0

    out = save(results, args.category, args.location)

    poor = [r for r in results if r["website_audit"].get("bucket") == "poor"]
    avg = [r for r in results if r["website_audit"].get("bucket") == "average"]
    good = [r for r in results if r["website_audit"].get("bucket") == "good"]

    print(f"Saved: {out}")
    print(f"Total audited: {len(results)} | poor: {len(poor)} | average: {len(avg)} | good: {len(good)}")
    print()
    print("Top opportunities:")
    for i, r in enumerate(results[:10], 1):
        a = r["website_audit"]
        print(
            f"[{i}] {r['business_name']} | q={a.get('quality_score')} ({a.get('bucket')}) "
            f"| opp={r.get('opportunity_score')} | reviews={r.get('review_count')}"
        )
        if a.get("issues"):
            print(f"    issues: {', '.join(a['issues'][:3])}")
        print(f"    {r.get('website_url')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
