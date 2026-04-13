#!/usr/bin/env python3
"""Pixel auditor v2 — multi-page, consent-aware, identity-honest.

Fixes from v1:
1. **Multi-page scan.** Visits homepage + /contact + /book + /quote + /get-quote
   + top 3 internal links. Pixel is "present" if found on ANY scanned page.
2. **Consent-mode click.** Auto-dismisses OneTrust, Cookiebot, Iubenda,
   Quantcast, Didomi, Sourcepoint, and generic CMP banners before scanning,
   so GDPR-gated GTM containers actually fire their tags.
3. **Network + DOM scan.** Captures both network requests and post-JS
   rendered DOM. Two independent signals.
4. **Strict pixel-vs-conversion separation.** Distinguishes
   `google_ads_remarketing` (audience builder) from `google_ads_conversion`
   (conversion tracking only).
5. **Tri-state outputs.** Errors → status=error, blocked → status=blocked,
   never silently `False`. The qualifier must treat non-`ok` status as
   `unknown`, not `missing`.
6. **Bot-block detection.** Cloudflare, DataDome challenge pages are caught
   and surfaced as `blocked`, not silently scanned for nothing.

Usage:
    python3 audit_pixels_v2.py candidates.json --output audited.json [--limit 5]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

# Network-request signatures
NETWORK_PATTERNS = {
    "facebook_pixel": [
        r"connect\.facebook\.net/[a-z_]+/fbevents\.js",
        r"facebook\.com/tr[/?]",
    ],
    "google_ads_remarketing": [
        r"google\.com/ads/ga-audiences",
        r"googleads\.g\.doubleclick\.net/pagead/viewthroughconversion",
    ],
    "google_ads_conversion": [
        r"googleadservices\.com/pagead/conversion",
        r"google\.com/pagead/1p-conversion",
    ],
    "google_analytics": [
        r"google-analytics\.com/(g/collect|collect|analytics\.js)",
        r"googletagmanager\.com/gtag/js",
    ],
    "google_tag_manager": [
        r"googletagmanager\.com/gtm\.js",
        r"googletagmanager\.com/ns\.html",
    ],
    "linkedin_insight": [
        r"snap\.licdn\.com",
        r"px\.ads\.linkedin\.com",
    ],
    "tiktok_pixel": [
        r"analytics\.tiktok\.com",
        r"business-api\.tiktok\.com",
    ],
}

# DOM/HTML signatures (post-JS execution)
DOM_PATTERNS = {
    "facebook_pixel": [
        r"fbq\s*\(\s*['\"]init['\"]",
        r"window\.fbq",
        r"_fbq",
    ],
    "google_ads_remarketing": [
        r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]AW-\d+['\"]",
        r"google_conversion_id",
    ],
}

CONSENT_BUTTON_TEXTS = [
    # Common CMP "accept" labels
    "Allow all", "Accept all", "Accept All", "Accept all cookies",
    "Allow All Cookies", "Allow Cookies", "I accept", "Agree", "I agree",
    "Got it", "OK", "Continue", "Allow", "Yes, I accept",
    "Accept and continue", "Accept recommended", "Accept and close",
]

CONVERSION_PAGE_PATHS = [
    "/contact", "/contact-us", "/book", "/booking", "/book-now",
    "/quote", "/get-quote", "/get-a-quote", "/request-quote",
    "/appointment", "/services",
]


def normalize_url(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def url_root(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def detect_blocked(html: str, body_text: str) -> str | None:
    low = (body_text or "").lower()[:2000]
    if "just a moment" in low and "cloudflare" in low:
        return "cloudflare_challenge"
    if "captcha" in low and len(body_text) < 1000:
        return "captcha_required"
    if "access denied" in low and len(body_text) < 1000:
        return "access_denied"
    if len((html or "").strip()) < 500:
        return "empty_response"
    return None


def classify_url_match(url: str, patterns: dict[str, list[str]]) -> set[str]:
    found = set()
    for name, pats in patterns.items():
        for pat in pats:
            if re.search(pat, url, re.IGNORECASE):
                found.add(name)
                break
    return found


def scan_page(page, url: str, timeout_ms: int = 25000) -> dict[str, Any]:
    """Visit url, accept cookies, capture network + DOM."""
    seen: set[str] = set()
    request_urls: list[str] = []

    def on_request(req):
        request_urls.append(req.url)
        for x in classify_url_match(req.url, NETWORK_PATTERNS):
            seen.add(x)

    page.on("request", on_request)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2500)

        # Try to dismiss consent banner — multiple strategies
        for label in CONSENT_BUTTON_TEXTS:
            try:
                btn = page.get_by_role("button", name=label, exact=False)
                if btn.count() > 0:
                    btn.first.click(timeout=1500)
                    page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        # Wait for any deferred scripts to fire
        page.wait_for_timeout(3000)

        html = page.content()
        try:
            body = page.inner_text("body", timeout=3000)
        except Exception:
            body = ""
    except Exception as e:
        page.remove_listener("request", on_request)
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)[:160]}",
            "found": set(),
        }

    page.remove_listener("request", on_request)

    blocked = detect_blocked(html, body)
    if blocked:
        return {"status": "blocked", "error": blocked, "found": set()}

    # Also scan rendered HTML for inline pixel patterns
    for name, pats in DOM_PATTERNS.items():
        for pat in pats:
            if re.search(pat, html, re.IGNORECASE):
                seen.add(name)
                break

    return {"status": "ok", "error": None, "found": seen, "html_len": len(html)}


def discover_internal_paths(page, base_url: str) -> list[str]:
    """Find internal links matching conversion-page patterns."""
    try:
        links = page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a[href]'));
            return anchors.map(a => a.getAttribute('href')).filter(Boolean);
        }
        """)
    except Exception:
        return []

    base_root = url_root(base_url)
    found_paths = set()
    for href in links:
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        # Resolve to absolute
        if href.startswith("/"):
            full = base_root + href
            path = href
        elif href.startswith("http"):
            if not href.startswith(base_root):
                continue
            path = urlparse(href).path
            full = href
        else:
            continue
        path_low = path.lower().rstrip("/")
        for needle in CONVERSION_PAGE_PATHS:
            if path_low == needle or path_low.endswith(needle):
                found_paths.add(full)
                break
    return sorted(found_paths)[:5]  # max 5 extra pages


def audit_one(context, candidate: dict[str, Any]) -> dict[str, Any]:
    raw_url = candidate.get("website_url") or ""
    if not raw_url:
        return _empty("skipped", "no_url")

    base_url = normalize_url(raw_url)

    # Skip non-website URLs (FB pages, directory listings)
    host = urlparse(base_url).netloc.lower()
    if any(blocked_host in host for blocked_host in [
        "facebook.com", "instagram.com", "linktr.ee", "yell.com", "yelp.com",
        "google.com/maps", "thomsonlocal", "192.com",
    ]):
        return _empty("skipped", f"non_website_url:{host}")

    page = context.new_page()
    aggregate_found: set[str] = set()
    pages_scanned: list[str] = []
    errors: list[str] = []

    # Scan homepage
    home = scan_page(page, base_url)
    if home["status"] == "ok":
        aggregate_found |= home["found"]
        pages_scanned.append(base_url)

        # Find conversion pages and scan top 3
        try:
            conv = discover_internal_paths(page, base_url)
        except Exception:
            conv = []

        for cp in conv[:3]:
            if cp in pages_scanned:
                continue
            sub = scan_page(page, cp, timeout_ms=20000)
            if sub["status"] == "ok":
                aggregate_found |= sub["found"]
                pages_scanned.append(cp)
            else:
                errors.append(f"{cp}: {sub.get('error','?')}")
            # If we already found everything we care about, stop early
            if {"facebook_pixel", "google_ads_remarketing"}.issubset(aggregate_found):
                break
    else:
        errors.append(f"home: {home.get('error','?')}")

    page.close()

    if not pages_scanned:
        return {
            "status": "error" if home["status"] == "error" else home["status"],
            "error": home.get("error"),
            "facebook_pixel": False,
            "google_ads_remarketing": False,
            "google_ads_conversion": False,
            "google_analytics": False,
            "google_tag_manager": False,
            "linkedin_insight": False,
            "tiktok_pixel": False,
            "any_retargeting": False,
            "pages_scanned": [],
            "errors": errors,
            "source": "playwright_v2",
        }

    return {
        "status": "ok",
        "error": None,
        "facebook_pixel": "facebook_pixel" in aggregate_found,
        "google_ads_remarketing": "google_ads_remarketing" in aggregate_found,
        "google_ads_conversion": "google_ads_conversion" in aggregate_found,
        "google_analytics": "google_analytics" in aggregate_found,
        "google_tag_manager": "google_tag_manager" in aggregate_found,
        "linkedin_insight": "linkedin_insight" in aggregate_found,
        "tiktok_pixel": "tiktok_pixel" in aggregate_found,
        "any_retargeting": bool(
            aggregate_found
            & {"facebook_pixel", "google_ads_remarketing", "linkedin_insight", "tiktok_pixel"}
        ),
        "pages_scanned": pages_scanned,
        "errors": errors,
        "source": "playwright_v2",
    }


def _empty(status: str, error: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "error": error,
        "facebook_pixel": False,
        "google_ads_remarketing": False,
        "google_ads_conversion": False,
        "google_analytics": False,
        "google_tag_manager": False,
        "linkedin_insight": False,
        "tiktok_pixel": False,
        "any_retargeting": False,
        "pages_scanned": [],
        "errors": [],
        "source": "playwright_v2",
    }


def audit_batch(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
            locale="en-GB",
        )

        for i, c in enumerate(candidates, 1):
            print(f"[{i}/{len(candidates)}] {c.get('business_name','')[:50]}", file=sys.stderr, flush=True)
            try:
                result = audit_one(context, c)
            except Exception as e:
                result = _empty("exception", f"{type(e).__name__}: {e}")
            c["pixels_v2"] = result
            out.append(c)

        context.close()
        browser.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text())
    candidates = raw["results"] if isinstance(raw, dict) and "results" in raw else raw
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"auditing {len(candidates)} candidates with multi-page consent-aware scan", file=sys.stderr)
    start = time.time()
    audited = audit_batch(candidates)
    elapsed = time.time() - start

    Path(args.output).write_text(json.dumps(audited, indent=2, ensure_ascii=False))

    ok = sum(1 for c in audited if (c.get("pixels_v2") or {}).get("status") == "ok")
    has_fb = sum(1 for c in audited if (c.get("pixels_v2") or {}).get("facebook_pixel"))
    has_gads = sum(1 for c in audited if (c.get("pixels_v2") or {}).get("google_ads_remarketing"))
    print(
        f"\ndone in {elapsed:.1f}s — {ok} ok, FB Pixel: {has_fb}, Google Ads remarketing: {has_gads}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
