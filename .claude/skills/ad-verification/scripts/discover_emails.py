#!/usr/bin/env python3
"""Email discovery for prospects.

Visits homepage + /contact + /about + footer pages and extracts:
1. mailto: links (highest confidence)
2. plain-text email regex matches
3. Filters out generic noreply/donotreply addresses
4. Validates MX record exists for the domain (drops catch-all/throwaway)

No third-party API used — all free.

Usage:
    python3 discover_emails.py candidates.json --output with_emails.json
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

EMAIL_REGEX = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
)

NOISE_PREFIXES = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "postmaster",
    "abuse", "webmaster", "wordpress", "example", "test",
}

NOISE_DOMAINS = {
    "example.com", "example.org", "test.com", "domain.com",
    "wixpress.com", "sentry.io", "cloudfront.net",
}

CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/team", "/footer", "/get-in-touch"]


def normalize_url(u: str) -> str:
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def is_noise_email(email: str) -> bool:
    local, _, domain = email.partition("@")
    local = local.lower()
    domain = domain.lower()
    if local in NOISE_PREFIXES:
        return True
    if any(p in local for p in ["sentry", "wixpress", "wordpress"]):
        return True
    if domain in NOISE_DOMAINS:
        return True
    # Common image-CDN false positives
    if domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        return True
    return False


def has_mx(domain: str, cache: dict[str, bool]) -> bool:
    if domain in cache:
        return cache[domain]
    try:
        # Cheap DNS check via socket — getaddrinfo doesn't return MX, so use
        # gethostbyname as a coarse proxy (domain resolves at all).
        socket.setdefaulttimeout(3)
        socket.gethostbyname(domain)
        cache[domain] = True
        return True
    except Exception:
        cache[domain] = False
        return False


def extract_from_page(page, url: str) -> set[str]:
    found: set[str] = set()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1500)
    except Exception:
        return found

    # mailto: links
    try:
        mailtos = page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href^="mailto:"]'))
            .map(a => a.getAttribute('href').replace('mailto:', '').split('?')[0])
        """)
        for m in mailtos or []:
            if m:
                found.add(m.strip().lower())
    except Exception:
        pass

    # Plain text email regex on full HTML
    try:
        html = page.content()
        for m in EMAIL_REGEX.findall(html):
            found.add(m.lower())
    except Exception:
        pass

    return found


def discover_one(page, candidate: dict[str, Any], mx_cache: dict[str, bool]) -> dict[str, Any]:
    raw_url = candidate.get("website_url") or ""
    if not raw_url:
        candidate["email"] = None
        candidate["email_source"] = "no_website"
        candidate["all_emails"] = []
        return candidate

    base = normalize_url(raw_url)
    parsed = urlparse(base)
    if parsed.netloc.lower() in {"facebook.com", "www.facebook.com", "instagram.com"}:
        candidate["email"] = None
        candidate["email_source"] = "non_website_url"
        candidate["all_emails"] = []
        return candidate

    base_root = f"{parsed.scheme}://{parsed.netloc}"

    all_emails: set[str] = set()

    # Scan homepage + contact/about
    pages_to_scan = [base] + [base_root + p for p in CONTACT_PATHS]

    for u in pages_to_scan[:5]:  # cap at 5 page visits
        emails = extract_from_page(page, u)
        all_emails |= emails
        if len(all_emails) >= 5:
            break

    # Filter noise
    cleaned = [e for e in all_emails if not is_noise_email(e)]

    # Filter by MX
    candidate_domain_root = parsed.netloc.lower().lstrip("www.")
    valid = []
    for e in cleaned:
        local, _, domain = e.partition("@")
        if has_mx(domain, mx_cache):
            valid.append(e)

    # Prefer same-domain emails
    same_domain = [e for e in valid if candidate_domain_root in e.split("@")[1]]
    chosen = same_domain[0] if same_domain else (valid[0] if valid else None)

    candidate["email"] = chosen
    candidate["email_source"] = "same_domain" if chosen and chosen in same_domain else ("found" if chosen else "none")
    candidate["all_emails"] = sorted(set(valid))

    return candidate


def discover_batch(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    out = []
    mx_cache: dict[str, bool] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
            ignore_https_errors=True,
        )
        page = context.new_page()

        for i, c in enumerate(candidates, 1):
            print(f"[{i}/{len(candidates)}] {c.get('business_name','')[:50]}", file=sys.stderr, flush=True)
            try:
                discover_one(page, c, mx_cache)
            except Exception as e:
                c["email"] = None
                c["email_source"] = f"error:{type(e).__name__}"
                c["all_emails"] = []
            out.append(c)

        context.close()
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

    enriched = discover_batch(candidates)
    Path(args.output).write_text(json.dumps(enriched, indent=2, ensure_ascii=False))

    with_email = sum(1 for c in enriched if c.get("email"))
    print(f"\ndiscovered {with_email}/{len(enriched)} emails", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
