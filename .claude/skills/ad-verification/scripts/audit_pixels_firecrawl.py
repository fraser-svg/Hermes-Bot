#!/usr/bin/env python3
"""Pixel auditor using Firecrawl REST API for JS-rendered HTML.

Why Firecrawl: pixels loaded via Google Tag Manager or other client-side
injection are invisible to static-HTML regex. Firecrawl renders the page in
a real browser, returning the post-JS-execution DOM that contains those
dynamically-injected script tags.

Each scrape costs 1 credit. Check budget with:
    curl -H "Authorization: Bearer $FIRECRAWL_API_KEY" \\
         https://api.firecrawl.dev/v1/team/credit-usage

Usage:
    python3 audit_pixels_firecrawl.py candidates.json --output audited.json
    python3 audit_pixels_firecrawl.py candidates.json --output audited.json --concurrency 10
    python3 audit_pixels_firecrawl.py candidates.json --output audited.json --limit 5  # dry test

Adds these fields to each candidate under `pixels_rendered`:
    {
        facebook_pixel: bool,
        facebook_pixel_id: str|null,
        google_ads_remarketing: bool,
        google_ads_id: str|null,
        google_ads_conversion: bool,        # conversion tracking only (≠ remarketing)
        google_analytics: bool,
        google_tag_manager: bool,
        gtm_id: str|null,
        linkedin_insight: bool,
        tiktok_pixel: bool,
        any_retargeting: bool,
        evidence: list[str],                # patterns matched in rendered HTML
        status: "ok"|"error"|"skipped",
        error: str|null,
        source: "firecrawl",
    }
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"

# Pattern → fragment list. A pixel is "present" if any fragment is found in
# the rendered HTML (case-insensitive).
PIXEL_PATTERNS: dict[str, list[str]] = {
    "facebook_pixel": [
        r"connect\.facebook\.net/[a-z_]+/fbevents\.js",
        r"facebook\.com/tr\?",
        r"fbevents\.js",
        r"fbq\s*\(\s*['\"]init['\"]",
    ],
    "google_ads_remarketing": [
        # The remarketing tag specifically (AW- config) is the qualifier for retargeting.
        r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]AW-\d+['\"]",
        r"google_conversion_id",
        r"googleads\.g\.doubleclick\.net",
        r"google\.com/ads/ga-audiences",
    ],
    "google_ads_conversion": [
        # Conversion tracking only — not retargeting. Tracked separately so we
        # don't conflate one with the other.
        r"googleadservices\.com/pagead/conversion",
        r"google\.com/pagead/1p-conversion",
    ],
    "google_analytics": [
        r"google-analytics\.com/(g/collect|collect|analytics\.js|ga\.js)",
        r"googletagmanager\.com/gtag/js",
        r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"](G-|UA-)",
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

ID_PATTERNS: dict[str, list[str]] = {
    "facebook_pixel_id": [
        r"fbq\s*\(\s*['\"]init['\"]\s*,\s*['\"](\d+)['\"]",
        r"facebook\.com/tr\?id=(\d+)",
    ],
    "google_ads_id": [
        r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"](AW-\d+)['\"]",
        r"AW-(\d{8,})",  # at least 8 digits to avoid noise
    ],
    "gtm_id": [
        r"googletagmanager\.com/gtm\.js\?id=(GTM-[A-Z0-9]+)",
        r"GTM-([A-Z0-9]{6,})",
    ],
}


def load_api_key() -> str:
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    if key:
        return key
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        # Fall back: walk up from cwd until .env found
        cwd = Path.cwd()
        for p in [cwd, *cwd.parents]:
            if (p / ".env").exists():
                env_path = p / ".env"
                break
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("FIRECRAWL_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("FIRECRAWL_API_KEY not found in env or .env")


def firecrawl_scrape(url: str, api_key: str, timeout: int = 60) -> dict[str, Any]:
    """Call Firecrawl /v1/scrape. Returns rendered HTML or raises."""
    payload = json.dumps(
        {
            "url": url,
            "formats": ["rawHtml"],
            "waitFor": 3500,
            "onlyMainContent": False,
            "timeout": (timeout - 5) * 1000,
            "blockAds": False,  # we WANT to see the ad/tracking scripts
        }
    ).encode()
    req = urllib.request.Request(
        FIRECRAWL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"http_{e.code}: {body}") from None
    except Exception as e:
        raise RuntimeError(f"{type(e).__name__}: {e}") from None

    if not data.get("success"):
        raise RuntimeError(f"firecrawl_failed: {data.get('error', 'unknown')[:200]}")

    return data["data"]


def extract_id(html: str, key: str) -> str | None:
    for pat in ID_PATTERNS.get(key, []):
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            captured = m.group(1)
            # For google_ads_id, ensure the AW- prefix
            if key == "google_ads_id" and not captured.startswith("AW-"):
                captured = f"AW-{captured}"
            if key == "gtm_id" and not captured.startswith("GTM-"):
                captured = f"GTM-{captured}"
            return captured
    return None


def scan_html(html: str) -> dict[str, Any]:
    """Scan rendered HTML for pixel signatures. Returns the pixels_rendered shape."""
    if not html:
        return _empty_result(status="error", error="empty_html")

    found: dict[str, bool] = {}
    evidence: list[str] = []

    for name, patterns in PIXEL_PATTERNS.items():
        present = False
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                present = True
                evidence.append(f"{name}: {m.group(0)[:100]}")
                break
        found[name] = present

    fb_id = extract_id(html, "facebook_pixel_id") if found["facebook_pixel"] else None
    gads_id = extract_id(html, "google_ads_id") if found["google_ads_remarketing"] else None
    gtm_id = extract_id(html, "gtm_id") if found["google_tag_manager"] else None

    return {
        "status": "ok",
        "error": None,
        "facebook_pixel": found["facebook_pixel"],
        "facebook_pixel_id": fb_id,
        "google_ads_remarketing": found["google_ads_remarketing"],
        "google_ads_id": gads_id,
        "google_ads_conversion": found["google_ads_conversion"],
        "google_analytics": found["google_analytics"],
        "google_tag_manager": found["google_tag_manager"],
        "gtm_id": gtm_id,
        "linkedin_insight": found["linkedin_insight"],
        "tiktok_pixel": found["tiktok_pixel"],
        "any_retargeting": (
            found["facebook_pixel"]
            or found["google_ads_remarketing"]
            or found["linkedin_insight"]
            or found["tiktok_pixel"]
        ),
        "evidence": evidence[:8],
        "source": "firecrawl",
    }


def _empty_result(status: str, error: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "error": error,
        "facebook_pixel": False,
        "facebook_pixel_id": None,
        "google_ads_remarketing": False,
        "google_ads_id": None,
        "google_ads_conversion": False,
        "google_analytics": False,
        "google_tag_manager": False,
        "gtm_id": None,
        "linkedin_insight": False,
        "tiktok_pixel": False,
        "any_retargeting": False,
        "evidence": [],
        "source": "firecrawl",
    }


def audit_one(candidate: dict[str, Any], api_key: str) -> dict[str, Any]:
    url = candidate.get("website_url") or ""
    if not url:
        candidate["pixels_rendered"] = _empty_result("skipped", "no_url")
        return candidate

    try:
        data = firecrawl_scrape(url, api_key)
        html = data.get("rawHtml") or data.get("html") or ""
        candidate["pixels_rendered"] = scan_html(html)
    except RuntimeError as e:
        candidate["pixels_rendered"] = _empty_result("error", str(e)[:200])

    return candidate


def audit_batch(
    candidates: list[dict[str, Any]],
    api_key: str,
    concurrency: int = 8,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = [None] * len(candidates)  # type: ignore
    done = 0
    total = len(candidates)

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {
            ex.submit(audit_one, dict(c), api_key): i
            for i, c in enumerate(candidates)
        }
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = candidates[i]
                results[i]["pixels_rendered"] = _empty_result("error", f"task_failed: {e}")
            done += 1
            name = (results[i].get("business_name") or "")[:50]
            status = results[i].get("pixels_rendered", {}).get("status", "?")
            print(f"[{done}/{total}] {status:5} {name}", file=sys.stderr, flush=True)

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="audit only first N (for testing)")
    args = parser.parse_args()

    api_key = load_api_key()

    raw = json.loads(Path(args.input).read_text())
    candidates = raw["results"] if isinstance(raw, dict) and "results" in raw else raw
    if args.limit:
        candidates = candidates[: args.limit]

    print(
        f"auditing {len(candidates)} candidates via Firecrawl, concurrency={args.concurrency}",
        file=sys.stderr,
    )
    start = time.time()
    audited = audit_batch(candidates, api_key, args.concurrency)
    elapsed = time.time() - start

    Path(args.output).write_text(json.dumps(audited, indent=2, ensure_ascii=False))

    ok = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("status") == "ok")
    err = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("status") == "error")
    has_fb = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("facebook_pixel"))
    has_gads = sum(1 for c in audited if (c.get("pixels_rendered") or {}).get("google_ads_remarketing"))
    print(
        f"\ndone in {elapsed:.1f}s — {ok} ok, {err} errors. "
        f"FB Pixel detected: {has_fb}. Google Ads remarketing detected: {has_gads}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
