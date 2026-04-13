#!/usr/bin/env python3
"""Batch-verify Google Ads Transparency Center activity for a list of businesses.

Reuses a single chromium browser across all candidates for speed.

Usage:
    python3 batch_verify_gatc.py candidates.json --output verified_gatc.json [--region GB]

Input JSON: list of {"slug": "...", "business_name": "...", "website_url": "...", ...}
Output JSON: same list with added fields:
    {"gatc_has_ads": bool|null, "gatc_ad_count": int, "gatc_url": str, "gatc_error": str|null}
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def domain_of(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def verify_batch(candidates: list[dict[str, Any]], region: str = "GB") -> list[dict[str, Any]]:
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

        for i, cand in enumerate(candidates, 1):
            domain = domain_of(cand.get("website_url") or "")
            name = cand.get("business_name", "")
            if not domain:
                cand["gatc_has_ads"] = None
                cand["gatc_ad_count"] = 0
                cand["gatc_error"] = "no_domain"
                cand["gatc_url"] = ""
                out.append(cand)
                continue

            url = f"https://adstransparency.google.com/?region={region}&domain={domain}"
            print(f"[{i}/{len(candidates)}] {name} ({domain})", file=sys.stderr, flush=True)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)

                body_text = ""
                try:
                    body_text = page.inner_text("body", timeout=5000)
                except Exception:
                    pass

                low = body_text.lower()
                ad_count = 0

                if "no results" in low or "couldn't find" in low or "no ads" in low:
                    ad_count = 0
                else:
                    cards = page.locator("creative-preview").all()
                    ad_count = len(cards)
                    if ad_count == 0:
                        # try alt selectors
                        alts = page.locator("[role='listitem']").all()
                        ad_count = len(alts) if len(alts) < 1000 else 0

                cand["gatc_has_ads"] = ad_count > 0
                cand["gatc_ad_count"] = ad_count
                cand["gatc_error"] = None
                cand["gatc_url"] = url
            except Exception as e:
                cand["gatc_has_ads"] = None
                cand["gatc_ad_count"] = 0
                cand["gatc_error"] = f"{type(e).__name__}: {e}"
                cand["gatc_url"] = url

            out.append(cand)
            time.sleep(0.4)

        browser.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--region", default="GB")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    candidates = data["results"] if isinstance(data, dict) and "results" in data else data

    verified = verify_batch(candidates, args.region)
    Path(args.output).write_text(json.dumps(verified, indent=2, ensure_ascii=False))

    confirmed = sum(1 for c in verified if c.get("gatc_has_ads"))
    unknown = sum(1 for c in verified if c.get("gatc_has_ads") is None)
    print(
        f"\nGATC verified {len(verified)}: {confirmed} running ads, "
        f"{len(verified) - confirmed - unknown} no ads, {unknown} unknown",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
