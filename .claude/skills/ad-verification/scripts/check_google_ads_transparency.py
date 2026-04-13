#!/usr/bin/env python3
"""Check Google Ads Transparency Center for a domain.

Usage:
    python3 check_google_ads_transparency.py example.com [--region GB]

Outputs JSON to stdout:
    {"has_google_ads": bool|null, "ad_count": int, "sample_headlines": [...], "error": str|null}

Exit codes:
    0 = success (even if no ads found)
    1 = error (selector failure, network, etc.)
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def check(domain: str, region: str = "GB") -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "has_google_ads": None,
            "ad_count": 0,
            "sample_headlines": [],
            "error": "playwright_not_installed",
        }

    url = f"https://adstransparency.google.com/?region={region}&domain={domain}"
    headlines: list[str] = []
    ad_count = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # GATC renders ad cards in a creative-preview component.
            cards = page.locator("creative-preview").all()
            ad_count = len(cards)
            for card in cards[:5]:
                try:
                    text = card.inner_text(timeout=2000)
                    first_line = text.strip().split("\n")[0] if text else ""
                    if first_line:
                        headlines.append(first_line[:120])
                except Exception:
                    continue

            browser.close()
    except Exception as e:
        return {
            "has_google_ads": None,
            "ad_count": 0,
            "sample_headlines": [],
            "error": f"scrape_failed: {type(e).__name__}: {e}",
        }

    return {
        "has_google_ads": ad_count > 0,
        "ad_count": ad_count,
        "sample_headlines": headlines,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("domain")
    parser.add_argument("--region", default="GB")
    args = parser.parse_args()

    result = check(args.domain, args.region)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    sys.exit(main())
