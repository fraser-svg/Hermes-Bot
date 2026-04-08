#!/usr/bin/env python3
"""Hermes poor-website prospector v2.

Adds weighted rubric, evidence capture, and confidence scoring.

Usage:
  python3 prospect_poor_websites_v2.py "electrician" "Edinburgh" --top 1
  python3 prospect_poor_websites_v2.py "electrician" "Edinburgh" --company "Lumen" --top 1
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from prospect import BASE_DIR, PROSPECTS_DIR, get_google_key, search_places


@dataclass
class PageFetch:
    final_url: str
    html: str
    status: str
    content_type: str
    http_status: int


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


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


def get_firecrawl_key() -> str:
    env = load_env()
    return (
        os.environ.get("FIRECRAWL_API_KEY")
        or env.get("FIRECRAWL_API_KEY")
        or ""
    )


def fetch_page_raw(url: str, timeout: int = 15) -> PageFetch:
    url = normalize_url(url)
    if not url:
        return PageFetch("", "", "missing_url", "", 0)

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HermesAuditV2/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            html = resp.read(700_000).decode("utf-8", errors="ignore") if "html" in ctype else ""
            return PageFetch(resp.geturl(), html, "ok" if "html" in ctype else "non_html", ctype, resp.status)
    except HTTPError as e:
        return PageFetch(url, "", f"http_{e.code}", "", e.code)
    except URLError:
        return PageFetch(url, "", "network_error", "", 0)
    except Exception:
        return PageFetch(url, "", "fetch_error", "", 0)


def fetch_page_firecrawl(url: str, api_key: str, timeout: int = 25) -> PageFetch:
    """Use Firecrawl /v1/scrape. Returns synthetic HTML from markdown + metadata.
    Falls back to raw fetch if Firecrawl fails.
    """
    target = normalize_url(url)
    if not target:
        return PageFetch("", "", "missing_url", "", 0)

    payload = json.dumps({
        "url": target,
        "formats": ["markdown", "html"],
        "onlyMainContent": False,
        "waitFor": 1500
    }).encode("utf-8")

    req = Request(
        "https://api.firecrawl.dev/v1/scrape",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            success = body.get("success", False)
            if not success:
                return PageFetch(target, "", "firecrawl_unsuccessful", "", resp.status)

            data = body.get("data", {})
            fc_html = data.get("html", "") or ""
            fc_md = data.get("markdown", "") or ""
            title = (data.get("metadata", {}) or {}).get("title", "")

            # synthesize HTML when only markdown available
            if not fc_html and fc_md:
                safe_md = fc_md.replace("<", " ").replace(">", " ")
                fc_html = f"<html><head><title>{title}</title></head><body>{safe_md}</body></html>"

            if not fc_html:
                return PageFetch(target, "", "firecrawl_empty", "", resp.status)

            final_url = data.get("metadata", {}).get("sourceURL") or target
            return PageFetch(final_url, fc_html, "ok", "text/html+firecrawl", resp.status)
    except HTTPError as e:
        return PageFetch(target, "", f"firecrawl_http_{e.code}", "", e.code)
    except URLError:
        return PageFetch(target, "", "firecrawl_network_error", "", 0)
    except Exception:
        return PageFetch(target, "", "firecrawl_fetch_error", "", 0)


def fetch_page(url: str, timeout: int = 15) -> PageFetch:
    key = get_firecrawl_key()
    if key:
        fc = fetch_page_firecrawl(url, key, timeout=max(timeout, 25))
        if fc.status == "ok":
            return fc
    return fetch_page_raw(url, timeout=timeout)


def strip_html(html: str) -> str:
    if not html:
        return ""
    s = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def contains_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def first_match(text: str, patterns: list[str]) -> str:
    t = text.lower()
    for p in patterns:
        if p in t:
            return p
    return ""


def audit_v2(url: str, page: PageFetch) -> dict:
    # Weighted rubric (100 total)
    # Technical 20, Mobile UX 20, Conversion 25, Trust 20, Visual Modernity 15

    if page.status != "ok":
        return {
            "quality_score": 20,
            "bucket": "poor",
            "confidence": 0.9,
            "rubric": [
                {
                    "id": "site_reachable",
                    "pillar": "technical",
                    "weight": 20,
                    "passed": False,
                    "evidence": f"fetch_status={page.status}",
                }
            ],
            "issues": [f"site_unreachable:{page.status}"],
            "wins": [],
            "signals": {"fetch_status": page.status, "final_url": page.final_url},
        }

    html = page.html
    low = html.lower()
    text = strip_html(html)
    text_low = text.lower()

    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    title = (title_match.group(1).strip() if title_match else "")

    # cheap signals
    script_chars = sum(len(m.group(0)) for m in re.finditer(r"<script[\s\S]*?</script>", html, flags=re.I))
    js_ratio = script_chars / max(1, len(html))

    has_viewport = bool(re.search(r"name=[\"']viewport[\"']", low))
    has_media_query = "@media" in low
    has_h1 = bool(re.search(r"<h1\b", low))
    has_tel = "tel:" in low
    has_contact_form = bool(re.search(r"<form\b", low))
    has_address = bool(re.search(r"\b\d{1,4}\s+\w+\s+(st|street|rd|road|ave|avenue|dr|drive|lane|ln|way)\b", text_low))

    cta_terms = ["call now", "get quote", "request quote", "book now", "contact us", "schedule", "free quote", "get estimate"]
    trust_terms = ["reviews", "testimonials", "licensed", "insured", "since", "years", "guarantee", "accredited", "google reviews"]
    location_terms = ["edinburgh", "scotland", "uk"]

    cta_any = contains_any(text_low, cta_terms) or contains_any(low, ["btn", "button"])
    trust_any = contains_any(text_low, trust_terms)
    location_any = contains_any(text_low, location_terms) or contains_any((title or "").lower(), location_terms)

    nav_links = 0
    nav_match = re.search(r"<nav\b[\s\S]*?</nav>", low)
    if nav_match:
        nav_links = len(re.findall(r"<a\b", nav_match.group(0)))

    legacy_font = "<font" in low
    obsolete_tags = "<marquee" in low or "<blink" in low
    table_layout_smell = "cellpadding" in low or "cellspacing" in low

    # Rubric checks
    rubric = []

    def add_check(cid: str, pillar: str, weight: int, passed: bool, evidence: str):
        rubric.append({
            "id": cid,
            "pillar": pillar,
            "weight": weight,
            "passed": passed,
            "evidence": evidence,
        })

    # Technical (20)
    add_check("https", "technical", 5, page.final_url.lower().startswith("https://"), f"final_url={page.final_url}")
    add_check("html_title", "technical", 5, len(title) >= 8, f"title={title[:80]}")
    add_check("h1_present", "technical", 5, has_h1, "found <h1>" if has_h1 else "no <h1> found")
    add_check("non_empty_content", "technical", 5, len(text) >= 700, f"visible_text_chars={len(text)}")

    # Mobile UX (20)
    add_check("viewport", "mobile_ux", 10, has_viewport, "viewport meta found" if has_viewport else "missing viewport")
    add_check("responsive_hint", "mobile_ux", 5, has_media_query, "@media found" if has_media_query else "no @media found")
    add_check("nav_depth", "mobile_ux", 5, nav_links <= 7 if nav_links else True, f"nav_links={nav_links}")

    # Conversion (25)
    add_check("cta_presence", "conversion", 10, cta_any, f"cta_term={first_match(text_low, cta_terms) or 'none'}")
    add_check("contact_path", "conversion", 8, has_tel or has_contact_form, f"has_tel={has_tel}, has_form={has_contact_form}")
    add_check("value_prop_clarity", "conversion", 7, len(title) >= 18 and location_any, f"title={title[:80]}, location_signal={location_any}")

    # Trust (20)
    add_check("trust_signals", "trust", 10, trust_any, f"trust_term={first_match(text_low, trust_terms) or 'none'}")
    add_check("address_or_location", "trust", 5, has_address or location_any, f"has_address={has_address}, location_signal={location_any}")
    add_check("contact_identity", "trust", 5, has_tel, f"has_tel={has_tel}")

    # Visual modernity (15)
    add_check("no_legacy_font", "visual_modernity", 5, not legacy_font, "legacy <font> present" if legacy_font else "no <font> tags")
    add_check("no_obsolete_tags", "visual_modernity", 5, not obsolete_tags, "obsolete tags found" if obsolete_tags else "no marquee/blink")
    add_check("no_table_layout_smell", "visual_modernity", 5, not table_layout_smell, "table-layout attributes found" if table_layout_smell else "no table-layout attributes")

    passed_weight = sum(c["weight"] for c in rubric if c["passed"])
    score = int(round(passed_weight))

    if score <= 60:
        bucket = "poor"
    elif score <= 75:
        bucket = "average"
    else:
        bucket = "good"

    issues = [c["id"] for c in rubric if not c["passed"]]
    wins = [c["id"] for c in rubric if c["passed"]]

    # Confidence model
    confidence = 0.55
    confidence += 0.15 if len(text) >= 700 else -0.1
    confidence += 0.1 if has_h1 else 0.0
    confidence += 0.1 if len(title) >= 8 else -0.05
    confidence += 0.05 if has_viewport else 0.0
    if js_ratio > 0.35:
        confidence -= 0.2  # likely JS-heavy; static parse less reliable
    confidence = round(clamp(confidence, 0.1, 0.95), 2)

    return {
        "quality_score": score,
        "bucket": bucket,
        "confidence": confidence,
        "rubric": rubric,
        "issues": issues,
        "wins": wins,
        "signals": {
            "fetch_status": page.status,
            "http_status": page.http_status,
            "content_type": page.content_type,
            "final_url": page.final_url,
            "firecrawl_used": "firecrawl" in page.content_type,
            "visible_text_chars": len(text),
            "js_ratio": round(js_ratio, 3),
            "nav_links": nav_links,
            "title": title[:120],
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

    page = fetch_page(website)
    audit = audit_v2(website, page)

    opportunity = round((rating or 0) * (review_count or 0), 1)

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
        "opportunity_score": opportunity,
        "website_audit_v2": audit,
        "_source": "google_maps_poor_website_audit_v2",
    }


def run(category: str, location: str, limit: int, top: int, company_filter: str) -> list[dict]:
    api_key = get_google_key()
    places = search_places(category, location, api_key, limit)

    rows = []
    filter_low = company_filter.lower().strip() if company_filter else ""

    for p in places:
        if p.get("businessStatus", "") == "CLOSED_PERMANENTLY":
            continue
        website = p.get("websiteUri", "")
        if not website:
            continue

        name = p.get("displayName", {}).get("text", "")
        if filter_low and filter_low not in name.lower():
            continue

        rows.append(place_to_record(p, category, location))

    def rank_key(r: dict):
        a = r.get("website_audit_v2", {})
        return (
            0 if a.get("bucket") == "poor" else 1,
            a.get("quality_score", 100),
            -r.get("opportunity_score", 0),
        )

    rows.sort(key=rank_key)
    if top > 0:
        rows = rows[:top]
    return rows


def save(results: list[dict], category: str, location: str) -> Path:
    PROSPECTS_DIR.mkdir(exist_ok=True)
    slug = f"{category.lower()}-{location.lower().replace(' ', '-')}-poor-websites-v2"
    out = PROSPECTS_DIR / f"{slug}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("category")
    parser.add_argument("location")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--company", default="", help="Filter by business name contains")
    args = parser.parse_args()

    print("=" * 60)
    print("HERMES POOR-WEBSITE PROSPECTOR v2")
    print(f"Category: {args.category} | Location: {args.location}")
    if args.company:
        print(f"Company filter: {args.company}")
    print("=" * 60)

    try:
        results = run(args.category, args.location, args.limit, args.top, args.company)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    if not results:
        print("No matching website-bearing businesses found.")
        return 0

    out = save(results, args.category, args.location)
    print(f"Saved: {out}")
    print()

    for i, r in enumerate(results, 1):
        a = r["website_audit_v2"]
        print(f"[{i}] {r['business_name']} | q={a['quality_score']} ({a['bucket']}) | conf={a['confidence']} | opp={r['opportunity_score']}")
        print(f"    site: {r['website_url']}")
        print(f"    key issues: {', '.join(a['issues'][:5]) if a['issues'] else 'none'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
