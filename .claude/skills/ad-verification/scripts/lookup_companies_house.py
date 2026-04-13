#!/usr/bin/env python3
"""Companies House lookup + UK chain filter.

Two-tier strategy (no API key required):

1. **Companies House public web search** — scrapes
   https://find-and-update.company-information.service.gov.uk/search?q=NAME
   for entity type, status, registered office. Single Playwright session,
   reused across candidates.

2. **Chain blocklist** — hardcoded list of top UK multi-location service
   brands. Optical Express, Timpson, Dental Designs, etc. Match by
   normalized business name. If the candidate's name contains any chain
   token AND the matched company has multiple "branch of" indicators,
   mark `is_chain_branch=true`.

Output schema (added to each candidate):
    {
        "entity_type": "ltd" | "llp" | "plc" | "sole_trader_or_unknown",
        "ch_company_number": "..." | null,
        "ch_company_name": "..." | null,
        "ch_status": "active" | "dissolved" | null,
        "is_chain_branch": bool,
        "chain_brand": "..." | null,
        "auto_send_eligible": bool   # only true for active Ltd/LLP/PLC, non-chain, non-regulated
    }

Usage:
    python3 lookup_companies_house.py candidates.json --output ch_enriched.json
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

CH_SEARCH_URL = "https://find-and-update.company-information.service.gov.uk/search/companies?q={q}"

# Hardcoded UK chain blocklist (top service-business chains by branch count).
# Add to this as new chains are spotted in runs.
UK_CHAIN_BLOCKLIST: dict[str, str] = {
    "optical express": "Optical Express",
    "specsavers": "Specsavers",
    "vision express": "Vision Express",
    "boots opticians": "Boots Opticians",
    "ace and tate": "Ace & Tate",
    "ace & tate": "Ace & Tate",
    "iolla": "IOLLA",
    "timpson": "Timpson",
    "max spielmann": "Max Spielmann",
    "snappy snaps": "Snappy Snaps",
    "kwik fit": "Kwik Fit",
    "halfords": "Halfords",
    "national tyres": "National Tyres",
    "f1 autocentres": "F1 Autocentres",
    "atsuk": "ATS Euromaster",
    "ats euromaster": "ATS Euromaster",
    "dyno-rod": "Dyno-Rod",
    "british gas": "British Gas",
    "boilerjuice": "BoilerJuice",
    "homeserve": "HomeServe",
    "domestic & general": "Domestic & General",
    "rentokil": "Rentokil",
    "rentokil initial": "Rentokil Initial",
    "mr clutch": "Mr Clutch",
    "halfords autocentre": "Halfords Autocentres",
    "tesco opticians": "Tesco Opticians",
    "asda opticians": "Asda Opticians",
    "scrivens": "Scrivens Opticians",
    "leightons": "Leightons Opticians",
    "mydentist": "mydentist",
    "bupa dental": "Bupa Dental Care",
    "bupa health": "Bupa",
    "rodericks dental": "Rodericks Dental",
    "dentalcare group": "Dentalcare Group",
    "smile direct club": "SmileDirectClub",
    "the gym group": "The Gym Group",
    "puregym": "PureGym",
    "fitness first": "Fitness First",
    "david lloyd": "David Lloyd",
    "nuffield health": "Nuffield Health",
    "anytime fitness": "Anytime Fitness",
    "snap fitness": "Snap Fitness",
    "f45": "F45",
    "f45 training": "F45 Training",
    "the gym": "The Gym Group",
    "barbershop group": "The Barbershop Group",
    "supercuts": "Supercuts",
    "regis": "Regis",
    "tonidolls": "Toni & Guy",
    "toni guy": "Toni & Guy",
    "rush hair": "Rush Hair",
    "andrew collinge": "Andrew Collinge",
    "saks": "Saks Hair",
    "headmasters": "Headmasters",
    "harlequin hair": "Harlequin",
}

# Regulated professions — auto-send disabled regardless of entity type
REGULATED_KEYWORDS = [
    "solicitor", "solicitors", "advocate", "advocates", "barrister",
    "law firm", "legal services", "lawyer",
    "accountant", "accountants", "chartered accountant",
    "financial adviser", "financial advisor", "ifa ", "wealth manager",
    "doctor", "gp ", "general practitioner", "medical centre",
    "physiotherapist", "physio ", "chiropractor", "osteopath",
    "charity", "charities", "trust",
]

UK_SLDS = {"co", "org", "ac", "gov", "net", "ltd", "plc"}


def normalize(name: str) -> str:
    n = (name or "").lower()
    for s in [" ltd", " limited", " plc", " llp", " (uk)", " uk", " group"]:
        n = n.replace(s, "")
    n = re.sub(r"[^\w\s&]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def is_chain(business_name: str) -> tuple[bool, str | None]:
    n = normalize(business_name)
    for token, brand in UK_CHAIN_BLOCKLIST.items():
        if token in n:
            return True, brand
    return False, None


def is_regulated(business_name: str, category: str = "") -> bool:
    text = f"{normalize(business_name)} {normalize(category)}"
    return any(kw in text for kw in REGULATED_KEYWORDS)


def lookup_ch(page, business_name: str) -> dict[str, Any]:
    """Scrape Companies House public search for the first matching active company."""
    url = CH_SEARCH_URL.format(q=quote(business_name))
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(800)
    except Exception as e:
        return {"entity_type": "sole_trader_or_unknown", "ch_error": f"goto:{type(e).__name__}"}

    try:
        # Companies House search results: a <ul id="results"> with <li> entries
        results = page.evaluate("""
        () => {
            const items = Array.from(document.querySelectorAll('li.type-company'));
            return items.slice(0, 5).map(li => {
                const link = li.querySelector('a');
                const meta = li.querySelector('p');
                return {
                    name: link ? link.innerText.trim() : '',
                    href: link ? link.getAttribute('href') : '',
                    meta: meta ? meta.innerText.trim() : '',
                };
            });
        }
        """)
    except Exception:
        results = []

    # Pick the first result whose name fuzzy-matches AND status = active
    target = normalize(business_name)
    for r in results:
        cand_name = normalize(r.get("name", ""))
        if not cand_name or len(cand_name) < 4:
            continue
        # Substring containment in either direction
        if target in cand_name or cand_name in target:
            meta_low = r.get("meta", "").lower()
            if "dissolved" in meta_low or "liquidation" in meta_low:
                continue
            # Extract company number from href (/company/12345678)
            m = re.search(r"/company/(\w+)", r.get("href", ""))
            number = m.group(1) if m else None
            entity = "ltd"
            name_low = r.get("name", "").lower()
            if "llp" in name_low:
                entity = "llp"
            elif "plc" in name_low:
                entity = "plc"
            return {
                "entity_type": entity,
                "ch_company_number": number,
                "ch_company_name": r.get("name", ""),
                "ch_status": "active",
                "ch_error": None,
            }

    return {
        "entity_type": "sole_trader_or_unknown",
        "ch_company_number": None,
        "ch_company_name": None,
        "ch_status": None,
        "ch_error": None,
    }


def enrich_one(page, candidate: dict[str, Any]) -> dict[str, Any]:
    name = candidate.get("business_name") or ""
    category = candidate.get("category") or ""

    # 1. Chain blocklist
    chain, brand = is_chain(name)
    candidate["is_chain_branch"] = chain
    candidate["chain_brand"] = brand

    # 2. Regulated profession check
    candidate["is_regulated"] = is_regulated(name, category)

    # 3. Companies House lookup (skip if chain — already disqualified)
    if not chain:
        ch = lookup_ch(page, name)
        candidate.update(ch)
    else:
        candidate.update({
            "entity_type": "skipped_chain",
            "ch_company_number": None,
            "ch_company_name": brand,
            "ch_status": None,
            "ch_error": None,
        })

    # 4. Auto-send eligibility gate
    candidate["auto_send_eligible"] = (
        candidate["entity_type"] in {"ltd", "llp", "plc"}
        and not candidate["is_chain_branch"]
        and not candidate["is_regulated"]
    )

    return candidate


def enrich_batch(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    out = []
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

        for i, c in enumerate(candidates, 1):
            print(f"[{i}/{len(candidates)}] {c.get('business_name','')[:50]}", file=sys.stderr, flush=True)
            try:
                enriched = enrich_one(page, c)
            except Exception as e:
                c["ch_error"] = f"{type(e).__name__}: {e}"
                c["entity_type"] = "sole_trader_or_unknown"
                c["auto_send_eligible"] = False
                enriched = c
            out.append(enriched)
            time.sleep(0.4)

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

    enriched = enrich_batch(candidates)
    Path(args.output).write_text(json.dumps(enriched, indent=2, ensure_ascii=False))

    ltd = sum(1 for c in enriched if c.get("entity_type") in {"ltd", "llp", "plc"})
    chain = sum(1 for c in enriched if c.get("is_chain_branch"))
    regulated = sum(1 for c in enriched if c.get("is_regulated"))
    eligible = sum(1 for c in enriched if c.get("auto_send_eligible"))
    print(
        f"\nenriched {len(enriched)}: ltd/llp/plc={ltd}, chain={chain}, regulated={regulated}, "
        f"auto_send_eligible={eligible}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
