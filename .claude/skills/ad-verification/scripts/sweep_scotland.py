#!/usr/bin/env python3
"""End-to-end Scotland sweep — discovery → ad verification → pixel audit →
   compliance enrichment → email discovery → tiered report.

Pipeline:
1. For each (city, category) pair, run prospect_no_pixel.py to discover
   businesses with websites and 5+ reviews
2. Dedupe across categories/cities (by business_name + phone)
3. Run audit_pixels_v2.py to multi-page pixel-audit each survivor
4. Run verify_meta_identity.py to identity-verify Meta ad activity
5. Run batch_verify_gatc.py for Google Ads activity
6. Run lookup_companies_house.py for entity type + chain filter
7. Run discover_emails.py for email enrichment
8. Apply final qualification rules and emit tiered report

Usage:
    python3 sweep_scotland.py --cities glasgow,edinburgh --categories electrician,plumber --limit 10
    python3 sweep_scotland.py --resume   # skip phases whose output files exist
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS = BASE_DIR / ".claude" / "skills" / "ad-verification" / "scripts"
WORKSPACE = BASE_DIR / "_workspace" / "retarget_scotland"
OUTPUT = BASE_DIR / "output"

DEFAULT_CITIES = [
    "Glasgow", "Edinburgh", "Aberdeen", "Dundee", "Stirling",
    "Inverness", "Perth", "Paisley", "Falkirk", "Ayr",
    "Dunfermline", "Kilmarnock", "Greenock", "Hamilton", "Kirkcaldy",
    "East Kilbride", "Livingston", "Cumbernauld", "Motherwell", "Dumfries",
]

DEFAULT_CATEGORIES = [
    # Trades (high paid-ad volume)
    "electrician", "plumber", "roofer", "hvac", "locksmith",
    "cleaner", "painter", "landscaper", "garage",
    # Health & retail (high LTV → dual-platform spend common)
    "dentist", "optician", "chiropractor", "physiotherapist",
    "kitchen showroom", "bathroom showroom", "furniture shop",
    "solar installer", "double glazing",
    # Beauty / personal services
    "hair salon", "barber", "tattoo studio", "personal trainer",
    # B2B services
    "accountant", "marketing agency", "it support",
]


def run_cmd(cmd: list[str], desc: str) -> int:
    print(f"\n{'='*60}\n{desc}\n{'='*60}\n  $ {' '.join(cmd)}", flush=True)
    start = time.time()
    rc = subprocess.call(cmd)
    elapsed = time.time() - start
    print(f"  → exit {rc} in {elapsed:.1f}s")
    return rc


def phase_1_discovery(cities: list[str], categories: list[str], limit: int) -> Path:
    """Run prospect_no_pixel.py across all city × category pairs and merge."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    candidates_path = WORKSPACE / "candidates.json"

    if candidates_path.exists():
        print(f"phase 1: candidates.json exists, skipping discovery")
        return candidates_path

    all_records: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for city in cities:
        for category in categories:
            print(f"\n--- {category} / {city} ---")
            try:
                subprocess.call(
                    ["python3", str(BASE_DIR / "prospect_no_pixel.py"), category, city, "--limit", str(limit)],
                    cwd=str(BASE_DIR),
                    timeout=600,
                )
            except subprocess.TimeoutExpired:
                print(f"  timeout on {category}/{city}, skipping")
                continue
            # Read the produced file
            slug = f"{category.lower().replace(' ', '-')}-{city.lower().replace(' ', '-')}-no-pixel.json"
            f = BASE_DIR / "prospects" / slug
            if not f.exists():
                continue
            try:
                data = json.loads(f.read_text())
            except Exception:
                continue
            for c in data:
                key = (c.get("business_name", "").lower().strip(), c.get("phone_number", ""))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                c["category"] = category
                c["sweep_city"] = city
                all_records.append(c)

    # Filter: must have website + 5+ reviews
    filtered = [c for c in all_records if c.get("website_url") and (c.get("review_count") or 0) >= 5]
    candidates_path.write_text(json.dumps(filtered, indent=2))
    print(f"\nphase 1 done: {len(all_records)} raw → {len(filtered)} filtered")
    return candidates_path


def phase_2_compliance(candidates_path: Path) -> Path:
    """Companies House + chain filter — runs FIRST because it cuts the most candidates cheaply."""
    out = WORKSPACE / "ch_enriched.json"
    if out.exists():
        return out
    run_cmd(
        ["python3", str(SCRIPTS / "lookup_companies_house.py"), str(candidates_path), "--output", str(out)],
        "Phase 2: Companies House + chain filter",
    )
    return out


def phase_3_pixel_audit(input_path: Path) -> Path:
    """Multi-page pixel scan with consent click — only on auto_send_eligible candidates."""
    eligible_path = WORKSPACE / "eligible_for_audit.json"
    data = json.loads(input_path.read_text())
    eligible = [c for c in data if c.get("auto_send_eligible")]
    print(f"phase 3: {len(eligible)} of {len(data)} candidates auto_send_eligible (Ltd/LLP/PLC, non-chain, non-regulated)")
    eligible_path.write_text(json.dumps(eligible, indent=2))

    out = WORKSPACE / "pixels_audited.json"
    if out.exists():
        return out
    run_cmd(
        ["python3", str(SCRIPTS / "audit_pixels_v2.py"), str(eligible_path), "--output", str(out)],
        "Phase 3: Multi-page pixel audit",
    )
    return out


def phase_4_meta(input_path: Path) -> Path:
    """Meta Ad Library identity-verified ad detection."""
    out = WORKSPACE / "meta_verified.json"
    if out.exists():
        return out
    run_cmd(
        ["python3", str(SCRIPTS / "verify_meta_identity.py"), str(input_path), "--output", str(out)],
        "Phase 4: Meta Ad Library identity verification",
    )
    return out


def phase_5_gatc(input_path: Path) -> Path:
    """Google Ads Transparency Center."""
    out = WORKSPACE / "gatc_verified.json"
    if out.exists():
        return out
    run_cmd(
        ["python3", str(SCRIPTS / "batch_verify_gatc.py"), str(input_path), "--output", str(out)],
        "Phase 5: GATC verification",
    )
    return out


def phase_6_emails(input_path: Path) -> Path:
    """Email discovery."""
    out = WORKSPACE / "with_emails.json"
    if out.exists():
        return out
    run_cmd(
        ["python3", str(SCRIPTS / "discover_emails.py"), str(input_path), "--output", str(out)],
        "Phase 6: Email discovery",
    )
    return out


def phase_7_qualify_and_report(meta_path: Path, gatc_path: Path, emails_path: Path) -> Path:
    """Merge all signals, apply qualification rules, emit tiered report."""
    meta = json.loads(meta_path.read_text())
    gatc = {(c.get("business_name", "").lower(), c.get("phone_number", "")): c for c in json.loads(gatc_path.read_text())}
    emails = {(c.get("business_name", "").lower(), c.get("phone_number", "")): c for c in json.loads(emails_path.read_text())}

    merged = []
    for c in meta:
        key = (c.get("business_name", "").lower(), c.get("phone_number", ""))
        g = gatc.get(key, {})
        e = emails.get(key, {})
        c["gatc_has_ads"] = g.get("gatc_has_ads")
        c["gatc_ad_count"] = g.get("gatc_ad_count", 0)
        c["email"] = e.get("email")
        c["email_source"] = e.get("email_source")
        merged.append(c)

    # Qualification:
    # - must be auto_send_eligible (Ltd/LLP/PLC, non-chain, non-regulated)
    # - must have email
    # - must have at least one confirmed leak
    qualified = []
    for c in merged:
        if not c.get("auto_send_eligible"):
            continue
        if not c.get("email"):
            continue
        pv = c.get("pixels_v2") or {}
        if pv.get("status") != "ok":
            continue
        meta_leak = c.get("meta_has_ads") and not pv.get("facebook_pixel")
        gads_leak = c.get("gatc_has_ads") and not pv.get("google_ads_remarketing")
        if not (meta_leak or gads_leak):
            continue
        c["leaks"] = {"meta": bool(meta_leak), "gads": bool(gads_leak)}

        # Tier
        if meta_leak and gads_leak:
            c["tier"] = "tier1a_dual_platform_dual_leak"
        elif meta_leak:
            c["tier"] = "tier1b_meta_leak"
        elif gads_leak:
            c["tier"] = "tier1c_gads_leak"
        qualified.append(c)

    qualified.sort(key=lambda c: (
        0 if c["tier"] == "tier1a_dual_platform_dual_leak" else (1 if c["tier"] == "tier1b_meta_leak" else 2),
        -((c.get("meta_ad_count") or 0) + (c.get("gatc_ad_count") or 0) * 5),
        -(c.get("review_count") or 0),
    ))

    # Write JSON + Markdown report
    OUTPUT.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT / "scotland_retarget_qualified.json"
    md_path = OUTPUT / "scotland_retarget_report.md"
    json_path.write_text(json.dumps(qualified, indent=2))

    from collections import Counter
    tiers = Counter(c["tier"] for c in qualified)
    cats = Counter(c.get("category") for c in qualified)
    cities = Counter(c.get("sweep_city") for c in qualified)

    L = ["# Scotland Retarget Prospects — Final Qualified List\n"]
    L.append(f"**Total qualified leads:** {len(qualified)}\n")
    L.append("**Qualification gates applied:**")
    L.append("1. Active UK Ltd / LLP / PLC (Companies House verified)")
    L.append("2. Not a national chain (blocklist)")
    L.append("3. Not a regulated profession (solicitor/doctor/IFA/charity)")
    L.append("4. Has discoverable contact email")
    L.append("5. Multi-page pixel scan with consent-click (post-JS rendered DOM)")
    L.append("6. Identity-matched Meta Ad Library activity (advertiser Page name verification)")
    L.append("7. At least one confirmed leak: Meta ads + no FB Pixel, OR Google Ads + no remarketing tag\n")
    L.append("## Tiers\n")
    for tier, n in tiers.most_common():
        L.append(f"- **{tier}**: {n}")
    L.append("\n## Top categories\n")
    for cat, n in cats.most_common(10):
        L.append(f"- {cat}: {n}")
    L.append("\n## Top cities\n")
    for city, n in cities.most_common(10):
        L.append(f"- {city}: {n}")

    L.append("\n---\n## Lead Table\n")
    L.append("| # | Business | Category | City | Reviews | Meta Ads | Google Ads | Email | Phone | Tier |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(qualified, 1):
        L.append(
            f"| {i} | **{c.get('business_name','')}** | {c.get('category','')} | {c.get('sweep_city','')} | "
            f"{c.get('rating','')}★ ({c.get('review_count',0)}) | "
            f"{c.get('meta_ad_count') if c.get('meta_has_ads') else '—'} | "
            f"{c.get('gatc_ad_count') if c.get('gatc_has_ads') else '—'} | "
            f"{c.get('email','')} | {c.get('phone_number','')} | {c.get('tier','').replace('tier','T')} |"
        )

    md_path.write_text("\n".join(L))
    print(f"\n✅ wrote {md_path}")
    print(f"✅ wrote {json_path}")
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities", default="", help="comma-separated city list (default: 20 Scottish cities)")
    parser.add_argument("--categories", default="", help="comma-separated category list (default: 25 high-yield)")
    parser.add_argument("--limit", type=int, default=15, help="results per category-city query")
    parser.add_argument("--resume", action="store_true", help="skip phases whose output exists")
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()] or DEFAULT_CITIES
    categories = [c.strip() for c in args.categories.split(",") if c.strip()] or DEFAULT_CATEGORIES

    print(f"\nSWEEP CONFIG\n  cities ({len(cities)}): {cities}\n  categories ({len(categories)}): {categories}\n  limit per query: {args.limit}")
    print(f"  workspace: {WORKSPACE}")
    print(f"  expected discovery queries: {len(cities) * len(categories)}")

    candidates = phase_1_discovery(cities, categories, args.limit)
    ch = phase_2_compliance(candidates)
    pixels = phase_3_pixel_audit(ch)
    meta = phase_4_meta(pixels)
    gatc = phase_5_gatc(pixels)
    emails = phase_6_emails(pixels)
    phase_7_qualify_and_report(meta, gatc, emails)

    return 0


if __name__ == "__main__":
    sys.exit(main())
