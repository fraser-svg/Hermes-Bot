"""Verify Meta Ad Library activity for every Glasgow no-pixel candidate.

Runs naive and strict parsers in a single scrape pass per candidate, writes
timestamped output files that refuse to clobber existing data. Protects
prospects/glasgow_meta_ads_no_pixel.json (prior round-2 whitelist-strict hits) —
never touches it.
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
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "ad-verification" / "scripts"))

from check_meta_ad_library import _page_name_matches  # noqa: E402

PROTECTED = ROOT / "prospects" / "glasgow_meta_ads_no_pixel.json"


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
            pa = row.get("pixel_audit") or {}
            if pa.get("facebook_pixel") is not False:
                continue
            out.append(row)
    return out


def verify_batch_dual(candidates: list[dict], country: str = "GB") -> list[dict]:
    """Scrape Meta Ad Library once per candidate and emit both a naive
    results-banner count and a strict Page-name-matched count."""
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
            locale="en-GB",
        )
        page = ctx.new_page()
        cookies_dismissed = False

        for i, cand in enumerate(candidates, 1):
            name = (cand.get("business_name") or "").strip()
            url = (
                f"https://www.facebook.com/ads/library/"
                f"?active_status=active&ad_type=all&country={country}"
                f"&q={quote(name)}&search_type=keyword_unordered"
            )
            print(f"[{i}/{len(candidates)}] {name}", file=sys.stderr, flush=True)

            naive_count = 0
            strict_count = 0
            error: str | None = None
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)
                if not cookies_dismissed:
                    for label in [
                        "Allow all cookies",
                        "Decline optional cookies",
                        "Only allow essential cookies",
                    ]:
                        try:
                            btn = page.get_by_role("button", name=label)
                            if btn.count() > 0:
                                btn.first.click(timeout=2000)
                                page.wait_for_timeout(1500)
                                cookies_dismissed = True
                                break
                        except Exception:
                            pass

                body_text = page.inner_text("body", timeout=5000)
                low = body_text.lower()

                if "no ads match" in low or "no results" in low:
                    naive_count = 0
                    strict_count = 0
                else:
                    m = re.search(r"~?\s*([\d,]+)\s+result", low)
                    naive_count = int(m.group(1).replace(",", "")) if m else 0

                    segments = re.split(r"Library ID:\s*\d+", body_text)
                    for seg in segments[1:]:
                        tail = seg[-600:]
                        if _page_name_matches(tail, name):
                            strict_count += 1
                    if naive_count == 0 and strict_count > 0:
                        naive_count = len(segments) - 1
            except Exception as e:
                error = f"{type(e).__name__}: {e}"

            enriched = dict(cand)
            enriched.update(
                {
                    "naive_count": naive_count,
                    "strict_count": strict_count,
                    "meta_has_ads_naive": naive_count > 0 if error is None else None,
                    "meta_has_ads_strict": strict_count > 0 if error is None else None,
                    "meta_url": url,
                    "meta_error": error,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            out.append(enriched)
            time.sleep(0.5)
        browser.close()
    return out


def main() -> int:
    protected_sha_before = PROTECTED.read_bytes() if PROTECTED.exists() else None

    slug = timestamp_slug()
    full_path = ROOT / "prospects" / f"glasgow_meta_verification_{slug}.full.json"
    naive_hits_path = ROOT / "prospects" / f"glasgow_meta_verification_{slug}.naive_hits.json"
    strict_hits_path = ROOT / "prospects" / f"glasgow_meta_verification_{slug}.strict_hits.json"
    latest_path = ROOT / "prospects" / "glasgow_meta_verification_latest.full.json"

    ensure_no_clobber([full_path, naive_hits_path, strict_hits_path])

    candidates = load_candidates()
    print(f"loaded {len(candidates)} unique no-pixel candidates", file=sys.stderr)

    verified = verify_batch_dual(candidates, country="GB")

    # Protect the prior file.
    if protected_sha_before is not None:
        assert PROTECTED.read_bytes() == protected_sha_before, (
            f"PROTECTED FILE WAS MODIFIED DURING RUN: {PROTECTED}"
        )

    for row in verified:
        if row.get("meta_has_ads_strict") is True:
            assert (row.get("pixel_audit") or {}).get("facebook_pixel") is False

    naive_hits = [r for r in verified if r.get("meta_has_ads_naive") is True]
    strict_hits = [r for r in verified if r.get("meta_has_ads_strict") is True]

    full_path.write_text(json.dumps(verified, indent=2, ensure_ascii=False))
    naive_hits_path.write_text(json.dumps(naive_hits, indent=2, ensure_ascii=False))
    strict_hits_path.write_text(json.dumps(strict_hits, indent=2, ensure_ascii=False))
    latest_path.write_text(json.dumps(verified, indent=2, ensure_ascii=False))

    per_cat_total: Counter[str] = Counter()
    per_cat_naive: Counter[str] = Counter()
    per_cat_strict: Counter[str] = Counter()
    for row in verified:
        cat = row.get("business_category", "?")
        per_cat_total[cat] += 1
        if row.get("meta_has_ads_naive"):
            per_cat_naive[cat] += 1
        if row.get("meta_has_ads_strict"):
            per_cat_strict[cat] += 1

    print()
    print(f"{'category':<22} {'total':>7} {'naive':>7} {'strict':>7}")
    print("-" * 46)
    for cat in sorted(per_cat_total):
        print(f"{cat:<22} {per_cat_total[cat]:>7} {per_cat_naive[cat]:>7} {per_cat_strict[cat]:>7}")
    print("-" * 46)
    print(
        f"{'TOTAL':<22} {sum(per_cat_total.values()):>7} "
        f"{sum(per_cat_naive.values()):>7} {sum(per_cat_strict.values()):>7}"
    )
    print()
    print(f"full:        {full_path.relative_to(ROOT)}  ({len(verified)} rows)")
    print(f"naive hits:  {naive_hits_path.relative_to(ROOT)}  ({len(naive_hits)} rows)")
    print(f"strict hits: {strict_hits_path.relative_to(ROOT)}  ({len(strict_hits)} rows)")
    print(f"latest:      {latest_path.relative_to(ROOT)}")

    naive_names = {r["business_name"] for r in naive_hits}
    strict_names = {r["business_name"] for r in strict_hits}
    missing = strict_names - naive_names
    if missing:
        print(f"\n[warn] {len(missing)} strict hits not in naive set: {sorted(missing)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
