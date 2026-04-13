#!/usr/bin/env python3
"""Check LinkedIn company page Ads tab for active ads.

Usage:
    python3 check_linkedin_ads.py https://linkedin.com/company/foo

Outputs JSON to stdout:
    {"has_linkedin_ads": bool|null, "ad_count": int, "sample_creatives": [...], "error": str|null}

LinkedIn requires auth for the Ads tab. Without LINKEDIN_COOKIE in env,
returns has_linkedin_ads=null with error='auth_required'.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def check(linkedin_url: str) -> dict[str, Any]:
    cookie = os.environ.get("LINKEDIN_COOKIE")
    if not cookie:
        return {
            "has_linkedin_ads": None,
            "ad_count": 0,
            "sample_creatives": [],
            "error": "auth_required",
        }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "has_linkedin_ads": None,
            "ad_count": 0,
            "sample_creatives": [],
            "error": "playwright_not_installed",
        }

    ads_url = linkedin_url.rstrip("/") + "/posts/?feedView=ads"
    creatives: list[dict[str, str]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_cookies(
                [
                    {
                        "name": "li_at",
                        "value": cookie,
                        "domain": ".linkedin.com",
                        "path": "/",
                    }
                ]
            )
            page = context.new_page()
            page.goto(ads_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)

            cards = page.locator('div[data-id*="urn:li:activity"]').all()
            for card in cards[:5]:
                try:
                    text = card.inner_text(timeout=2000)
                    if text:
                        creatives.append(
                            {"headline": text.strip().split("\n")[0][:120], "body": text[:300]}
                        )
                except Exception:
                    continue

            browser.close()
    except Exception as e:
        return {
            "has_linkedin_ads": None,
            "ad_count": 0,
            "sample_creatives": [],
            "error": f"scrape_failed: {type(e).__name__}: {e}",
        }

    return {
        "has_linkedin_ads": len(creatives) > 0,
        "ad_count": len(creatives),
        "sample_creatives": creatives,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("linkedin_url")
    args = parser.parse_args()
    result = check(args.linkedin_url)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    sys.exit(main())
