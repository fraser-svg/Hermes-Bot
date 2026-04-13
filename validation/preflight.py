#!/usr/bin/env python3
"""Preflight health checks for retarget-prospector.

Fails loud if any production dependency is broken BEFORE the pipeline runs:
    1. META_AD_LIBRARY_TOKEN present, API reachable
    2. LINKEDIN_COOKIE present, not expired (auth probe)
    3. Google Ads Transparency scraper selector still matches
    4. Playwright Chromium installed
    5. OPENROUTER_API_KEY present, cheap probe passes

Exit non-zero on any failure so the orchestrator can abort.

Usage:
    python3 validation/preflight.py
    python3 validation/preflight.py --skip linkedin,openrouter
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from prospect_no_pixel import load_env  # noqa: E402


Result = tuple[bool, str]


def _env(key: str) -> str:
    env = load_env()
    return os.environ.get(key) or env.get(key, "")


def check_meta_token() -> Result:
    """Probe Meta ad verification. Prefer API (token), fall back to scraper.

    Scraper path requires no credentials but is slower and IP-rate-limited.
    The check_meta_ad_library.py script returns `has_meta_ads=None` on
    scraper failure (selector drift, cookie banner change) — that counts as
    a preflight failure because the retarget pipeline would silently treat
    those as "no ads" without this gate.
    """
    token = _env("META_AD_LIBRARY_TOKEN")
    if token:
        url = (
            "https://graph.facebook.com/v21.0/ads_archive"
            "?search_terms=Monzo&ad_reached_countries=%5B%27GB%27%5D"
            "&ad_active_status=active&fields=id&limit=1"
            f"&access_token={token}"
        )
        try:
            with urlopen(Request(url), timeout=15) as resp:
                body = json.loads(resp.read().decode())
            if "data" not in body:
                return False, f"meta api shape unexpected: {list(body)[:3]}"
            return True, f"meta api ok (returned {len(body.get('data', []))} results)"
        except HTTPError as e:
            return False, f"meta api http {e.code}: {e.read()[:200]!r}"
        except URLError as e:
            return False, f"meta api network: {e}"

    # No token — try scraper against a known active UK advertiser.
    scripts_dir = BASE_DIR / ".claude/skills/ad-verification/scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from check_meta_ad_library import check as _scrape
    except ImportError as e:
        return False, f"no META_AD_LIBRARY_TOKEN AND scraper import failed: {e}"
    try:
        result = _scrape("Monzo", country="GB")
    except Exception as e:
        return False, f"no token; scraper exception: {type(e).__name__}: {str(e)[:160]}"
    if result.get("error"):
        return False, f"no token; scraper error: {result['error']}"
    if result.get("has_meta_ads") is None:
        return False, "no token; scraper returned unknown for Monzo — selector likely broken"
    return True, (
        f"meta scraper ok (Monzo has_meta_ads={result.get('has_meta_ads')}, "
        f"ad_count={result.get('ad_count')}) — no API token, using public UI scrape"
    )


def check_linkedin_cookie() -> Result:
    cookie = _env("LINKEDIN_COOKIE")
    if not cookie:
        return False, "LINKEDIN_COOKIE missing — LinkedIn checks will silently return unknown"
    if "li_at=" not in cookie:
        return False, "LINKEDIN_COOKIE present but no li_at token — likely malformed"
    # Probe a public LinkedIn endpoint with the cookie; login redirect means expired.
    req = Request(
        "https://www.linkedin.com/feed/",
        headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urlopen(req, timeout=15) as resp:
            final = resp.geturl()
            if "login" in final or "authwall" in final:
                return False, f"LinkedIn cookie expired — redirected to {final}"
            return True, "linkedin cookie live"
    except HTTPError as e:
        if e.code in (401, 403, 999):
            return False, f"linkedin http {e.code} — cookie likely expired"
        return False, f"linkedin http {e.code}"
    except URLError as e:
        return False, f"linkedin network: {e}"


def check_gatc_selector() -> Result:
    """Run the scraper against a known advertiser; selector must still match."""
    script = BASE_DIR / ".claude/skills/ad-verification/scripts/check_google_ads_transparency.py"
    if not script.exists():
        return False, f"scraper script missing: {script}"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "stripe.com", "--region", "GB"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, "gatc scraper timed out after 120s"
    if proc.returncode != 0:
        return False, f"gatc exit {proc.returncode}: {proc.stderr[:200]}"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, f"gatc stdout not json: {proc.stdout[:200]}"
    if data.get("has_google_ads") is None:
        return False, f"gatc returned unknown for known advertiser — selector likely broken: {data.get('error')}"
    return True, f"gatc ok (stripe.com has_google_ads={data.get('has_google_ads')}, ad_count={data.get('ad_count')})"


def check_playwright_chromium() -> Result:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "playwright not installed (pip install playwright)"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True, "playwright chromium launches"
    except Exception as e:
        msg = str(e)[:200]
        return False, f"chromium launch failed: {msg} (try: npx playwright install chromium)"


def check_openrouter() -> Result:
    key = _env("OPENROUTER_API_KEY") or _env("openrouter")
    if not key:
        return False, "OPENROUTER_API_KEY (or 'openrouter') missing"
    req = Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
        if "data" not in body:
            return False, "openrouter api shape unexpected"
        return True, f"openrouter ok ({len(body.get('data', []))} models listed)"
    except HTTPError as e:
        return False, f"openrouter http {e.code}"
    except URLError as e:
        return False, f"openrouter network: {e}"


CHECKS: dict[str, Callable[[], Result]] = {
    "meta": check_meta_token,
    "linkedin": check_linkedin_cookie,
    "gatc": check_gatc_selector,
    "playwright": check_playwright_chromium,
    "openrouter": check_openrouter,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", default="", help="comma-separated checks to skip")
    parser.add_argument("--only", default="", help="comma-separated checks to run exclusively")
    args = parser.parse_args()

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    failures: list[str] = []
    for name, fn in CHECKS.items():
        if only and name not in only:
            continue
        if name in skip:
            print(f"[skip] {name}")
            continue
        try:
            ok, msg = fn()
        except Exception as e:  # defensive — any check raising is a failure
            ok, msg = False, f"unexpected exception: {e}"
        marker = "[ ok ]" if ok else "[FAIL]"
        print(f"{marker} {name}: {msg}")
        if not ok:
            failures.append(name)

    print()
    if failures:
        print(f"PREFLIGHT FAILED — {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("PREFLIGHT OK — retarget-prospector cleared for launch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
