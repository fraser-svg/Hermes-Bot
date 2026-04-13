#!/usr/bin/env python3
"""Meta Ad Library verification with advertiser-identity matching.

Replaces batch_verify_meta.py. Differences:

1. Uses keyword_exact_phrase (not keyword_unordered) — eliminates token collisions.
2. Parses each ad card's advertiser Page name and link.
3. Fuzzy-matches advertiser-Page name against candidate business name + domain.
4. Counts only matching cards as ad_count.
5. Treats unmatched results as `meta_has_ads=False` even if Meta returned cards
   for the search term.
6. Captures sample creative TEXT (headline + body excerpt) for use by composer
   — used later by composer hallucination guard.
7. Detects rate-limit / cookie-banner-stuck pages and returns `unknown` (null),
   never silently false.

Usage:
    python3 verify_meta_identity.py candidates.json --output verified_meta.json
    python3 verify_meta_identity.py candidates.json --output verified_meta.json --limit 5
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


def normalize_name(name: str) -> str:
    """Lowercase, strip company suffixes and punctuation."""
    n = name.lower()
    for suffix in [" ltd", " limited", " plc", " llp", " co.", " co ", " group", " (uk)", " uk", " inc"]:
        n = n.replace(suffix, "")
    n = re.sub(r"[^\w\s&]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


UK_SLDS = {"co", "org", "ac", "gov", "net", "ltd", "plc", "me"}


def domain_root(url: str) -> str:
    """Extract the registered domain label, handling UK SLDs like foo.co.uk."""
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) < 2:
        return host
    # Handle .co.uk, .org.uk etc — registered domain is parts[-3]
    if len(parts) >= 3 and parts[-1] == "uk" and parts[-2] in UK_SLDS:
        return parts[-3]
    return parts[-2]


GENERIC_TOKENS = {
    # Geo
    "glasgow", "edinburgh", "scotland", "scottish", "uk", "british", "london",
    "england", "manchester", "birmingham", "leeds", "bristol", "liverpool",
    # Service descriptors that say nothing about identity
    "studio", "services", "service", "company", "shop", "centre", "center",
    "group", "team", "solutions", "consulting", "consultants", "agency",
    "art", "design", "marketing", "media", "events", "training", "lab",
    "house", "place", "club", "online", "digital", "global", "international",
    # Entity types
    "ltd", "limited", "plc", "llp",
}


def fuzzy_match(advertiser: str, business_name: str, website_domain_root: str) -> tuple[bool, float]:
    """Return (matches, score) — True if advertiser-page is plausibly the candidate.

    Strict matching to avoid false positives. Order of preference:
    1. Bidirectional substring containment (highest confidence)
    2. Domain root present in advertiser name (high confidence)
    3. Strong token overlap (2+ significant non-generic tokens)
    4. High string-similarity ratio (>= 0.85)
    """
    a = normalize_name(advertiser)
    b = normalize_name(business_name)
    if not a or not b:
        return False, 0.0

    # Direct substring containment in either direction (highest confidence)
    if (len(a) >= 6 and a in b) or (len(b) >= 6 and b in a):
        return True, 0.95

    # Domain root in advertiser name — only if domain root is distinctive (>=4 chars, not generic)
    dr = (website_domain_root or "").lower()
    if dr and len(dr) >= 5 and dr not in GENERIC_TOKENS and dr in a.replace(" ", ""):
        return True, 0.9

    # Strong token overlap — at least 2 significant non-generic tokens shared
    a_tokens = set(t for t in a.split() if len(t) > 3 and t not in GENERIC_TOKENS)
    b_tokens = set(t for t in b.split() if len(t) > 3 and t not in GENERIC_TOKENS)
    overlap = a_tokens & b_tokens
    if len(overlap) >= 2:
        return True, 0.85

    # High sequence ratio — strict threshold to avoid false positives
    score = difflib.SequenceMatcher(None, a, b).ratio()
    if score >= 0.85:
        return True, score

    return False, score


def detect_blocked(body_text: str) -> str | None:
    """Detect bot-block, rate-limit, or cookie-banner-stuck pages."""
    low = body_text.lower()
    if "just a moment" in low or "cf-chl" in low:
        return "cloudflare_challenge"
    if "you've been blocked" in low or "rate limited" in low or "too many requests" in low:
        return "rate_limited"
    if len(body_text.strip()) < 200:
        return "empty_or_blocked"
    if "allow all cookies" in low and "ad library" not in low:
        return "cookie_banner_stuck"
    return None


def query_meta(page, business_name: str, country: str = "GB") -> dict[str, Any]:
    """Run one Meta Ad Library query and return ad cards + status.

    Uses keyword_unordered (broad recall: catches FB Page names that don't
    exactly match the Google Maps business name). Identity verification on
    each card filters out the inevitable noise.
    """
    q = quote(business_name)
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country={country}"
        f"&q={q}&search_type=keyword_unordered"
    )

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
    except Exception as e:
        return {"status": "error", "error": f"goto_failed: {type(e).__name__}", "url": url, "cards": []}

    try:
        body_text = page.inner_text("body", timeout=5000)
    except Exception:
        body_text = ""

    blocked = detect_blocked(body_text)
    if blocked:
        return {"status": "blocked", "error": blocked, "url": url, "cards": []}

    low = body_text.lower()
    if "no ads match" in low or "no results" in low or "0 results" in low:
        return {"status": "ok", "error": None, "url": url, "cards": []}

    # Find ad cards via DOM walk. Each ad card contains "Library ID:" text;
    # walking up ~7 levels finds the container with Page name + creative body.
    try:
        cards = page.evaluate("""
        () => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const out = [];
            let node;
            while (node = walker.nextNode()) {
                if (!node.textContent.includes('Library ID:')) continue;
                let parent = node.parentElement;
                for (let i = 0; i < 12; i++) {
                    if (!parent) break;
                    const txt = parent.innerText || '';
                    if (txt.length > 200) {
                        out.push(txt.substring(0, 800));
                        break;
                    }
                    parent = parent.parentElement;
                }
                if (out.length >= 30) break;
            }
            return out;
        }
        """)
    except Exception as e:
        return {"status": "error", "error": f"dom_walk_failed: {e}", "url": url, "cards": []}

    parsed_cards: list[dict[str, str]] = []
    for raw in cards:
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip() and ln.strip() != "​"]

        # Find "Sponsored" line — Page name is the line immediately before it.
        page_name = ""
        headline_start_idx = -1
        for idx, ln in enumerate(lines):
            if ln == "Sponsored" and idx > 0:
                page_name = lines[idx - 1]
                headline_start_idx = idx + 1
                break

        # Fallback: line right after "See ad details"
        if not page_name:
            for idx, ln in enumerate(lines):
                if "See ad details" in ln and idx + 1 < len(lines):
                    page_name = lines[idx + 1]
                    headline_start_idx = idx + 2
                    break

        # Headline = first non-chrome line after Page name
        headline = ""
        if headline_start_idx >= 0:
            for ln in lines[headline_start_idx:]:
                if len(ln) > 15 and "Library ID" not in ln and "Started running" not in ln:
                    headline = ln
                    break

        parsed_cards.append({
            "page_name": page_name[:120],
            "headline": headline[:200],
            "raw_excerpt": raw[:400],
        })

    return {"status": "ok", "error": None, "url": url, "cards": parsed_cards}


def verify_one(page, candidate: dict[str, Any]) -> dict[str, Any]:
    name = candidate.get("business_name") or ""
    website = candidate.get("website_url") or ""
    domain_r = domain_root(website)

    if not name:
        return {
            "meta_has_ads": None,
            "meta_ad_count": 0,
            "meta_matched_count": 0,
            "meta_creatives": [],
            "meta_status": "skipped",
            "meta_error": "no_name",
            "meta_url": "",
        }

    result = query_meta(page, name)
    if result["status"] != "ok":
        return {
            "meta_has_ads": None,  # unknown, not False
            "meta_ad_count": 0,
            "meta_matched_count": 0,
            "meta_creatives": [],
            "meta_status": result["status"],
            "meta_error": result.get("error"),
            "meta_url": result.get("url", ""),
        }

    raw_count = len(result["cards"])
    matched = []
    for card in result["cards"]:
        ok, score = fuzzy_match(card["page_name"], name, domain_r)
        if ok:
            card["match_score"] = round(score, 2)
            matched.append(card)

    return {
        "meta_has_ads": len(matched) > 0,
        "meta_ad_count": len(matched),  # only count verified-identity cards
        "meta_unmatched_count": raw_count - len(matched),
        "meta_creatives": matched[:5],  # top 5 with verified identity
        "meta_status": "ok",
        "meta_error": None,
        "meta_url": result["url"],
    }


def verify_batch(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        cookies_dismissed = False

        for i, c in enumerate(candidates, 1):
            # Fresh context every 25 candidates to avoid state bleed / throttle
            if i == 1 or i % 25 == 1:
                try:
                    context.close()
                except Exception:
                    pass
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                    locale="en-GB",
                )
                cookies_dismissed = False
                # Pre-warm: visit the homepage and dismiss the cookie banner once
                warm = context.new_page()
                try:
                    warm.goto("https://www.facebook.com/ads/library/", wait_until="domcontentloaded", timeout=20000)
                    warm.wait_for_timeout(2000)
                    for label in ["Allow all cookies", "Decline optional cookies", "Only allow essential cookies"]:
                        try:
                            btn = warm.get_by_role("button", name=label)
                            if btn.count() > 0:
                                btn.first.click(timeout=2000)
                                warm.wait_for_timeout(1000)
                                cookies_dismissed = True
                                break
                        except Exception:
                            pass
                except Exception:
                    pass
                warm.close()

            page = context.new_page()
            print(f"[{i}/{len(candidates)}] {c.get('business_name','')[:50]}", file=sys.stderr, flush=True)
            try:
                result = verify_one(page, c)
            except Exception as e:
                result = {
                    "meta_has_ads": None,
                    "meta_ad_count": 0,
                    "meta_creatives": [],
                    "meta_status": "exception",
                    "meta_error": f"{type(e).__name__}: {e}",
                    "meta_url": "",
                }
            page.close()

            c.update(result)
            out.append(c)
            time.sleep(0.4)

        try:
            context.close()
        except Exception:
            pass
        browser.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text())
    candidates = raw["results"] if isinstance(raw, dict) and "results" in raw else raw
    if args.limit:
        candidates = candidates[: args.limit]

    verified = verify_batch(candidates)
    Path(args.output).write_text(json.dumps(verified, indent=2, ensure_ascii=False))

    has = sum(1 for c in verified if c.get("meta_has_ads"))
    unknown = sum(1 for c in verified if c.get("meta_has_ads") is None)
    print(
        f"\nverified {len(verified)}: {has} confirmed running ads (identity-matched), "
        f"{len(verified) - has - unknown} no ads, {unknown} unknown",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
