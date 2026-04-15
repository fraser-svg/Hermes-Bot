"""Verify Google Ads Transparency Center activity for every Glasgow no-pixel candidate.

Parallel to glasgow_meta_ads_no_pixel.py. Reuses one browser, refuses to clobber
existing output, preserves all rows (hits + non-hits). Protects prior outputs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent

PROTECTED = [
    ROOT / "prospects" / "glasgow_meta_ads_no_pixel.json",
]


def git_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "nogit"


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M") + "_" + git_hash()


def ensure_no_clobber(paths: list[Path]) -> None:
    existing = [p for p in paths if p.exists()]
    if existing:
        print("refusing to clobber existing files:", file=sys.stderr)
        for p in existing:
            print(f"  {p}", file=sys.stderr)
        raise SystemExit(2)


def extract_domain(url: str | None) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    host = re.sub(r"^www\.", "", host)
    return host


def load_candidates() -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    files = sorted((ROOT / "prospects").glob("*-glasgow-no-pixel.json"))
    print(f"found {len(files)} source crawl files", file=sys.stderr)
    for path in files:
        rows = json.loads(path.read_text())
        for row in rows:
            name = (row.get("business_name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    return out


def verify_batch_google(candidates: list[dict], region: str = "GB") -> list[dict]:
    from playwright.sync_api import sync_playwright

    out: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        for i, cand in enumerate(candidates, 1):
            name = cand.get("business_name", "")
            domain = extract_domain(cand.get("website_url"))
            print(f"[{i}/{len(candidates)}] {name}  ({domain})", file=sys.stderr, flush=True)

            ad_count = 0
            headlines: list[str] = []
            error: str | None = None
            url = ""

            if not domain:
                error = "no_domain"
            else:
                url = f"https://adstransparency.google.com/?region={region}&domain={domain}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
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
                except Exception as e:
                    error = f"{type(e).__name__}: {e}"

            enriched = dict(cand)
            enriched.update(
                {
                    "gatc_domain": domain,
                    "gatc_url": url,
                    "gatc_ad_count": ad_count,
                    "gatc_sample_headlines": headlines,
                    "gatc_has_ads": (ad_count > 0) if error is None else None,
                    "gatc_error": error,
                    "gatc_checked_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            out.append(enriched)
            time.sleep(0.3)
        browser.close()
    return out


def main() -> int:
    protected_bytes = {p: p.read_bytes() for p in PROTECTED if p.exists()}

    slug = timestamp_slug()
    full_path = ROOT / "prospects" / f"glasgow_google_ads_verification_{slug}.full.json"
    hits_path = ROOT / "prospects" / f"glasgow_google_ads_verification_{slug}.leak_hits.json"
    latest_path = ROOT / "prospects" / "glasgow_google_ads_verification_latest.full.json"

    ensure_no_clobber([full_path, hits_path])

    candidates = load_candidates()
    print(f"loaded {len(candidates)} unique candidates", file=sys.stderr)

    verified = verify_batch_google(candidates, region="GB")

    for p, pre in protected_bytes.items():
        assert p.read_bytes() == pre, f"PROTECTED FILE WAS MODIFIED DURING RUN: {p}"

    # Google Ads leak = running GATC ads AND no google_ads_remarketing tag on site.
    leak_hits = [
        r
        for r in verified
        if r.get("gatc_has_ads") is True
        and (r.get("pixel_audit") or {}).get("google_ads_remarketing") is False
    ]

    for r in leak_hits:
        assert r["gatc_has_ads"] is True
        assert (r.get("pixel_audit") or {}).get("google_ads_remarketing") is False

    full_path.write_text(json.dumps(verified, indent=2, ensure_ascii=False))
    hits_path.write_text(json.dumps(leak_hits, indent=2, ensure_ascii=False))
    latest_path.write_text(json.dumps(verified, indent=2, ensure_ascii=False))

    per_cat_total: Counter[str] = Counter()
    per_cat_running: Counter[str] = Counter()
    per_cat_leak: Counter[str] = Counter()
    for row in verified:
        cat = row.get("business_category", "?")
        per_cat_total[cat] += 1
        if row.get("gatc_has_ads"):
            per_cat_running[cat] += 1
        if row in leak_hits:
            per_cat_leak[cat] += 1

    print()
    print(f"{'category':<22} {'total':>7} {'gAds':>7} {'leak':>7}")
    print("-" * 46)
    for cat in sorted(per_cat_total):
        print(
            f"{cat:<22} {per_cat_total[cat]:>7} "
            f"{per_cat_running[cat]:>7} {per_cat_leak[cat]:>7}"
        )
    print("-" * 46)
    print(
        f"{'TOTAL':<22} {sum(per_cat_total.values()):>7} "
        f"{sum(per_cat_running.values()):>7} {sum(per_cat_leak.values()):>7}"
    )
    print()
    print(f"full:      {full_path.relative_to(ROOT)}  ({len(verified)} rows)")
    print(f"leak hits: {hits_path.relative_to(ROOT)}  ({len(leak_hits)} rows)")
    print(f"latest:    {latest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
