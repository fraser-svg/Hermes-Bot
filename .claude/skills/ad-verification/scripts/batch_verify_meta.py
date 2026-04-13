#!/usr/bin/env python3
"""Batch-verify Meta Ad Library activity for a list of businesses.

Reuses a single chromium browser across all candidates for speed.

Usage:
    python3 batch_verify_meta.py candidates.json --output verified.json [--country GB]

Input JSON: list of {"slug": "...", "business_name": "...", ...}
Output JSON: same list with added fields:
    {"meta_has_ads": bool|null, "meta_ad_count": int, "meta_url": str, "meta_error": str|null}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote


def verify_batch(candidates: list[dict[str, Any]], country: str = "GB") -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    out: list[dict[str, Any]] = []
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
        cookies_dismissed = False

        for i, cand in enumerate(candidates, 1):
            name = cand.get("business_name") or cand.get("name") or ""
            slug = cand.get("slug") or name
            if not name:
                cand["meta_has_ads"] = None
                cand["meta_ad_count"] = 0
                cand["meta_error"] = "no_name"
                cand["meta_url"] = ""
                out.append(cand)
                continue

            q = quote(name)
            url = (
                f"https://www.facebook.com/ads/library/"
                f"?active_status=active&ad_type=all&country={country}"
                f"&q={q}&search_type=keyword_unordered"
            )

            print(f"[{i}/{len(candidates)}] {name}", file=sys.stderr, flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)

                if not cookies_dismissed:
                    for label in ["Allow all cookies", "Decline optional cookies", "Only allow essential cookies"]:
                        try:
                            btn = page.get_by_role("button", name=label)
                            if btn.count() > 0:
                                btn.first.click(timeout=2000)
                                page.wait_for_timeout(1500)
                                cookies_dismissed = True
                                break
                        except Exception:
                            pass

                body = page.inner_text("body", timeout=5000).lower()

                if "no ads match" in body or "no results" in body:
                    ad_count = 0
                else:
                    m = re.search(r"~?\s*([\d,]+)\s+result", body)
                    ad_count = int(m.group(1).replace(",", "")) if m else 0

                cand["meta_has_ads"] = ad_count > 0
                cand["meta_ad_count"] = ad_count
                cand["meta_error"] = None
                cand["meta_url"] = url
            except Exception as e:
                cand["meta_has_ads"] = None
                cand["meta_ad_count"] = 0
                cand["meta_error"] = f"{type(e).__name__}: {e}"
                cand["meta_url"] = url

            out.append(cand)
            time.sleep(0.5)

        browser.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--country", default="GB")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    if isinstance(data, dict) and "results" in data:
        candidates = data["results"]
    elif isinstance(data, list):
        candidates = data
    else:
        print("input must be list or dict with 'results' key", file=sys.stderr)
        return 1

    verified = verify_batch(candidates, args.country)

    Path(args.output).write_text(json.dumps(verified, indent=2, ensure_ascii=False))
    confirmed = sum(1 for c in verified if c.get("meta_has_ads"))
    unknown = sum(1 for c in verified if c.get("meta_has_ads") is None)
    print(
        f"\nverified {len(verified)}: {confirmed} running ads, "
        f"{len(verified) - confirmed - unknown} no ads, {unknown} unknown",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
