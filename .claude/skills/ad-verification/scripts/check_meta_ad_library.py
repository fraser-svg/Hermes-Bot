#!/usr/bin/env python3
"""Scrape the public Meta Ad Library web UI for active ads from a business.

No API token required — scrapes facebook.com/ads/library/ directly.

Usage:
    python3 check_meta_ad_library.py "Bright Spark Electricians" --country GB

Output JSON to stdout:
    {"has_meta_ads": bool|null, "ad_count": int, "sample_creatives": [...], "error": str|null, "url": str}
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.parse import quote


def _normalize_name(s: str) -> str:
    """Strip punctuation, collapse whitespace, lowercase for fuzzy matching."""
    import re as _re
    return _re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def _page_name_matches(card_text: str, business_name: str) -> bool:
    """Meta ad cards render the Page name as its own line immediately
    followed by "Sponsored". Return True only when a line in the card
    (a) matches the business name as all tokens AND (b) is followed by
    "Sponsored" within the next two lines. This rejects keyword hits
    in ad body copy while accepting real page-scoped matches."""
    if not card_text or not business_name:
        return False
    target_tokens = _normalize_name(business_name).split()
    if not target_tokens:
        return False
    lines = [ln.strip() for ln in card_text.split("\n") if ln.strip() and ln.strip() != "\u200b"]
    for i, line in enumerate(lines):
        norm_tokens = _normalize_name(line).split()
        if not norm_tokens:
            continue
        if not all(tok in norm_tokens for tok in target_tokens):
            continue
        # Require "Sponsored" as the next meaningful line to confirm this
        # is a Page-name slot, not a keyword match in body copy.
        for j in range(i + 1, min(i + 3, len(lines))):
            if lines[j].lower().startswith("sponsored"):
                return True
    return False


def check(business_name: str, country: str = "GB", strict_page_name: bool = True) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "has_meta_ads": None,
            "ad_count": 0,
            "sample_creatives": [],
            "error": "playwright_not_installed",
            "url": "",
        }

    q = quote(business_name)
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country={country}"
        f"&q={q}&search_type=keyword_unordered"
    )
    creatives: list[dict[str, str]] = []
    ad_count = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                locale="en-GB",
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)

            # Dismiss cookie banner if present.
            for label in ["Allow all cookies", "Decline optional cookies", "Only allow essential cookies"]:
                try:
                    btn = page.get_by_role("button", name=label)
                    if btn.count() > 0:
                        btn.first.click(timeout=2000)
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    pass

            # Read the result count text — Meta shows "~X results" or "No ads match".
            body_text = ""
            try:
                body_text = page.inner_text("body", timeout=5000)
            except Exception:
                pass

            low = body_text.lower()
            if "no ads match" in low or "no results" in low:
                ad_count = 0
            else:
                import re
                # Parse each ad card from the flat body text. Meta's DOM
                # role="article" selector no longer matches as of 2026-04
                # so we split on "Library ID: <digits>" markers — each one
                # terminates one ad card's text block. segments[0] is the
                # page chrome; segments[1..N] each correspond to one ad.
                segments = re.split(r"Library ID:\s*\d+", body_text)
                total_cards = max(0, len(segments) - 1)
                matched_cards = 0
                for seg in segments[1:]:
                    # Inspect only the tail (card body region just above
                    # the Library ID line). Page name sits near the end.
                    tail = seg[-600:]
                    if strict_page_name and not _page_name_matches(tail, business_name):
                        continue
                    matched_cards += 1
                    if len(creatives) < 5:
                        lines = [ln.strip() for ln in tail.split("\n") if ln.strip()]
                        page_name_guess = ""
                        for ln in reversed(lines):
                            if len(ln) < 80 and "Started running" not in ln and "Sponsored" not in ln:
                                page_name_guess = ln
                                break
                        headline = next(
                            (ln for ln in lines if len(ln) > 10 and "Started running" not in ln and "Sponsored" not in ln),
                            page_name_guess or (lines[0] if lines else ""),
                        )
                        creatives.append(
                            {
                                "page_name": page_name_guess[:120],
                                "headline": headline[:160],
                                "body": tail[:400],
                            }
                        )

                if strict_page_name:
                    # Keyword search matches ad body text, so queries like
                    # "Wikipedia" return ads from unrelated advertisers
                    # mentioning Wikipedia. Strict mode requires the
                    # business name tokens to appear in the card's Page
                    # name region before counting.
                    ad_count = matched_cards
                else:
                    m = re.search(r"~?\s*([\d,]+)\s+result", low)
                    if m:
                        ad_count = int(m.group(1).replace(",", ""))
                    elif total_cards:
                        ad_count = total_cards

            browser.close()
    except Exception as e:
        return {
            "has_meta_ads": None,
            "ad_count": 0,
            "sample_creatives": [],
            "error": f"scrape_failed: {type(e).__name__}: {e}",
            "url": url,
        }

    return {
        "has_meta_ads": ad_count > 0,
        "ad_count": ad_count,
        "sample_creatives": creatives,
        "error": None,
        "url": url,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("business_name")
    parser.add_argument("--country", default="GB")
    args = parser.parse_args()
    result = check(args.business_name, args.country)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    sys.exit(main())
