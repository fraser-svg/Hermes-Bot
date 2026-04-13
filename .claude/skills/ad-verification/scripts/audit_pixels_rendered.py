#!/usr/bin/env python3
"""Pixel auditor that renders JavaScript before scanning.

Fixes the false-negative problem of static-HTML regex auditing: pixels loaded
via Google Tag Manager (GTM) or other client-side injection are invisible to
static scans but ARE present after JS execution.

Two-source detection per candidate:
1. Network requests during page load (most reliable — pixel = network call)
2. Final rendered DOM HTML (catches inline pixels and confirms #1)

Usage:
    python3 audit_pixels_rendered.py candidates.json --output audited.json

Adds these fields to each candidate:
    pixels_rendered: {
        facebook_pixel: bool,
        facebook_pixel_id: str|null,
        google_ads_remarketing: bool,
        google_ads_id: str|null,
        google_analytics: bool,
        google_tag_manager: bool,
        gtm_id: str|null,
        linkedin_insight: bool,
        tiktok_pixel: bool,
        any_retargeting: bool,
        evidence: list[str],
        status: "ok"|"timeout"|"error",
        error: str|null,
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

PIXEL_PATTERNS = {
    "facebook_pixel": [
        r"connect\.facebook\.net.*fbevents\.js",
        r"facebook\.com/tr\?",
        r"fbevents\.js",
    ],
    "google_ads_remarketing": [
        r"googleads\.g\.doubleclick\.net",
        r"google\.com/ads/ga-audiences",
        r"googleadservices\.com/pagead/conversion",
        r"google\.com/pagead/1p-conversion",
    ],
    "google_analytics": [
        r"google-analytics\.com/(g/collect|collect|analytics\.js)",
        r"googletagmanager\.com/gtag/js",
        r"analytics\.google\.com",
    ],
    "google_tag_manager": [
        r"googletagmanager\.com/gtm\.js",
        r"googletagmanager\.com/ns\.html",
    ],
    "linkedin_insight": [
        r"snap\.licdn\.com",
        r"px\.ads\.linkedin\.com",
        r"_linkedin_partner_id",
    ],
    "tiktok_pixel": [
        r"analytics\.tiktok\.com",
        r"ttq\.load",
    ],
}

ID_EXTRACTORS = {
    "facebook_pixel_id": [
        r"facebook\.com/tr\?id=(\d+)",
        r"fbq\s*\(\s*['\"]init['\"]\s*,\s*['\"](\d+)['\"]",
    ],
    "google_ads_id": [
        r"id=(AW-\d+)",
        r"AW-(\d+)",
        r"google_conversion_id\s*=\s*['\"]?(\d+)",
    ],
    "gtm_id": [
        r"id=(GTM-[A-Z0-9]+)",
        r"GTM-([A-Z0-9]+)",
    ],
}


def classify_url(url: str) -> list[str]:
    """Return list of pixel classifications matching this URL."""
    out = []
    for name, patterns in PIXEL_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, url, re.IGNORECASE):
                out.append(name)
                break
    return out


def extract_id(text: str, key: str) -> str | None:
    for pat in ID_EXTRACTORS.get(key, []):
        m = re.search(pat, text)
        if m:
            return m.group(1) if "(" in pat else m.group(0)
    return None


def audit_one(page, url: str, timeout_ms: int = 25000) -> dict[str, Any]:
    """Visit URL, capture network requests + rendered HTML, classify pixels."""
    seen: set[str] = set()
    request_urls: list[str] = []

    def on_request(req):
        request_urls.append(req.url)
        for cls in classify_url(req.url):
            seen.add(cls)

    page.on("request", on_request)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # Allow time for GTM/async scripts to fire after DOMContentLoaded
        page.wait_for_timeout(3500)
        html = page.content()
    except Exception as e:
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)[:200]}",
            "facebook_pixel": False,
            "facebook_pixel_id": None,
            "google_ads_remarketing": False,
            "google_ads_id": None,
            "google_analytics": False,
            "google_tag_manager": False,
            "gtm_id": None,
            "linkedin_insight": False,
            "tiktok_pixel": False,
            "any_retargeting": False,
            "evidence": [],
        }
    finally:
        page.remove_listener("request", on_request)

    # Also scan rendered HTML (catches inline pixels)
    for name, patterns in PIXEL_PATTERNS.items():
        if name in seen:
            continue
        for pat in patterns:
            if re.search(pat, html, re.IGNORECASE):
                seen.add(name)
                break

    # Extract IDs from network URLs and HTML
    all_text = " ".join(request_urls) + " " + html
    fb_id = extract_id(all_text, "facebook_pixel_id") if "facebook_pixel" in seen else None
    gads_id = extract_id(all_text, "google_ads_id") if "google_ads_remarketing" in seen else None
    gtm_id = extract_id(all_text, "gtm_id") if "google_tag_manager" in seen else None

    # Build evidence list (top 3 matching request URLs per category)
    evidence = []
    for name in seen:
        for u in request_urls:
            if classify_url(u) and name in classify_url(u):
                evidence.append(f"{name}: {u[:120]}")
                break

    return {
        "status": "ok",
        "error": None,
        "facebook_pixel": "facebook_pixel" in seen,
        "facebook_pixel_id": fb_id,
        "google_ads_remarketing": "google_ads_remarketing" in seen,
        "google_ads_id": gads_id,
        "google_analytics": "google_analytics" in seen,
        "google_tag_manager": "google_tag_manager" in seen,
        "gtm_id": gtm_id,
        "linkedin_insight": "linkedin_insight" in seen,
        "tiktok_pixel": "tiktok_pixel" in seen,
        "any_retargeting": any(
            seen & {"facebook_pixel", "google_ads_remarketing", "linkedin_insight", "tiktok_pixel"}
            for _ in [1]
        ),
        "evidence": evidence[:8],
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
        )

        for i, c in enumerate(candidates, 1):
            url = c.get("website_url") or ""
            name = c.get("business_name", "")
            if not url:
                c["pixels_rendered"] = {"status": "skipped", "error": "no_url"}
                out.append(c)
                continue

            print(f"[{i}/{len(candidates)}] {name[:50]}", file=sys.stderr, flush=True)

            page = context.new_page()
            try:
                result = audit_one(page, url)
            except Exception as e:
                result = {"status": "error", "error": f"{type(e).__name__}: {e}"}
            finally:
                page.close()

            c["pixels_rendered"] = result
            out.append(c)
            time.sleep(0.3)

        browser.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    candidates = data["results"] if isinstance(data, dict) and "results" in data else data

    audited = audit_batch(candidates)
    Path(args.output).write_text(json.dumps(audited, indent=2, ensure_ascii=False))

    ok = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("status") == "ok")
    has_fb = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("facebook_pixel"))
    has_gads = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("google_ads_remarketing"))
    print(
        f"\naudited {len(audited)}: {ok} ok, FB Pixel present: {has_fb}, "
        f"Google Ads remarketing present: {has_gads}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
