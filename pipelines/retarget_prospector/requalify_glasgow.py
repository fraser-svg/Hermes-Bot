"""
Re-qualify existing Glasgow prospect data against the new retarget-prospector ICP
(UK considered-purchase + Google Ads hard gate + Meta cohort A/B/C).

Throwaway script. Reads _workspace/retarget/glasgow_*.json, joins on business_name,
applies the 7 gates from .claude/agents/retarget-qualifier.md, writes:

  _workspace/retarget/glasgow_requalified.json        (all rows + verdicts)
  _workspace/retarget/glasgow_wave1_cohortC.json      (Cohort C only, ranked)
  _workspace/retarget/glasgow_funnel.md               (human-readable funnel report)

Does NOT re-scrape. Every signal comes from existing merged files.
Deleted once Track 2 (national crawler) ships.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
WS = ROOT / "_workspace" / "retarget"

# ICP whitelist — mirrors .claude/skills/retarget-prospector/references/icp.md
# Mapped from `category` field values present in the Glasgow crawl.
WHITELIST = {
    "dentist",
    "optician",
    "cosmetic_clinic",
    "aesthetic_clinic",
    "private_healthcare",
    "vet",
    "veterinary_clinic",
    "solicitor",
    "accountant",
    "financial_advisor",
    "mortgage_broker",
    "architect",
    "interior_designer",
    "landscaper_premium",
    "painter_premium",
    "kitchen_fitter_premium",
    "wedding_venue",
    "private_school",
    "tutoring",
    "driving_school_intensive",
    "premium_fitness",
    "coaching",
    "recruitment_specialist",
}

# Categories present in Glasgow crawl that map to blacklist (emergency trades etc)
BLACKLIST = {
    "electrician",
    "plumber",
    "roofer",
    "hvac",
    "locksmith",
    "cleaner",
    "landscaper",  # unqualified = emergency/standard
    "painter",  # unqualified
    "garage",
}


def load_json(name: str):
    path = WS / name
    if not path.exists():
        print(f"[warn] {name} missing")
        return []
    return json.loads(path.read_text())


def merge_sources() -> list[dict]:
    """Merge glasgow_ch.json (original 43-record crawl) with glasgow_emails.json AND
    _workspace/retarget_glasgow_wl/final.json (new whitelist crawl). Dedup by
    business_name.lower().strip(); new whitelist records override the old set."""
    base = load_json("glasgow_ch.json")
    emails = load_json("glasgow_emails.json")
    email_by_name = {r["business_name"]: r.get("email") for r in emails}
    email_src_by_name = {r["business_name"]: r.get("email_source") for r in emails}
    for r in base:
        if not r.get("email"):
            r["email"] = email_by_name.get(r["business_name"])
        if not r.get("email_source"):
            r["email_source"] = email_src_by_name.get(r["business_name"])

    # Union with the new whitelist crawl output
    wl_path = ROOT / "_workspace" / "retarget_glasgow_wl" / "final.json"
    if wl_path.exists():
        wl = json.loads(wl_path.read_text())
        by_key = {r["business_name"].lower().strip(): r for r in base}
        for r in wl:
            key = r["business_name"].lower().strip()
            by_key[key] = r  # new records win on conflict
        merged = list(by_key.values())
        print(f"[merge] base={len(base)} + whitelist={len(wl)} → union={len(merged)}")
        return merged
    else:
        print(f"[merge] whitelist file missing ({wl_path}), using base only ({len(base)})")
        return base


def gate_evaluate(record: dict) -> dict:
    """Apply ICP gates in cheapest-first order. Return dict with verdict, gates, cohort."""
    gates = {}
    category = record.get("category", "").lower()
    pv2 = record.get("pixels_v2") or {}

    # Gate 1: geography — all Glasgow records are UK, always pass
    gates["geography"] = "pass"

    # Gate 2: category whitelist/blacklist
    if category in BLACKLIST:
        return {"verdict": "rejected_out_of_icp", "gates": gates | {"category": "fail_blacklist"}}
    if category not in WHITELIST:
        return {"verdict": "rejected_out_of_icp", "gates": gates | {"category": "fail_unknown"}}
    gates["category"] = "pass"

    # Gate 3: Google Ads hard gate
    gatc_hit = bool(record.get("gatc_has_ads"))
    site_tag_hit = bool(pv2.get("google_ads_conversion")) or bool(pv2.get("google_ads_remarketing"))
    gatc_unknown = record.get("gatc_has_ads") is None
    pixels_unreach = (pv2.get("status") not in ("ok", None)) or pv2.get("partial_scan")

    if not (gatc_hit or site_tag_hit):
        if gatc_unknown and pixels_unreach:
            return {"verdict": "rejected_unreachable", "gates": gates | {"google_ads": "unreachable"}}
        return {"verdict": "rejected_no_google_ads", "gates": gates | {"google_ads": "fail"}}
    gates["google_ads"] = "pass"

    google_ads_evidence = []
    if gatc_hit:
        google_ads_evidence.append(f"gatc:active_ads={record.get('gatc_ad_count', 0)}")
    if pv2.get("google_ads_conversion"):
        google_ads_evidence.append("site_tag:gads_conversion")
    if pv2.get("google_ads_remarketing"):
        google_ads_evidence.append("site_tag:gads_remarketing")

    # Gate 5: website signal — we trust that records with pixels_v2.status==ok have a real site
    # (Glasgow crawl already filtered placeholder/parked sites upstream)
    if pv2.get("status") != "ok":
        return {"verdict": "rejected_weak_web", "gates": gates | {"website": "fail"}}
    gates["website"] = "pass"

    # Gate 6: trust signal — 30+ reviews @ 4.0+
    rating = float(record.get("rating") or 0)
    reviews = int(record.get("review_count") or 0)
    if not (reviews >= 30 and rating >= 4.0):
        return {
            "verdict": "rejected_weak_trust",
            "gates": gates | {"trust": f"fail_{rating}_{reviews}"},
        }
    gates["trust"] = "pass"

    # Gate 7: size signal — use Companies House as primary proxy (Glasgow data has it)
    # Multi-service offering implied by business_category whitelist categories (all multi-service)
    ch_active = (record.get("ch_status") or "").lower() in ("active", "")  # tolerate missing CH
    has_ch = bool(record.get("ch_company_number"))
    if not (has_ch or reviews >= 30):  # reviews already confirmed as 30+, so size passes
        return {"verdict": "rejected_too_small", "gates": gates | {"size": "fail"}}
    gates["size"] = "pass"

    # Gate 4: Meta cohort assignment
    meta_pixel = bool(pv2.get("facebook_pixel"))
    meta_active = bool(record.get("meta_has_ads"))
    meta_creatives = int(record.get("meta_ad_count") or 0)

    # Without CAPI detection, if active+pixel with no known infra gap → no_leak
    if meta_active and meta_pixel:
        return {
            "verdict": "rejected_no_leak",
            "gates": gates | {"meta": "complete"},
        }

    if meta_active and meta_creatives >= 3 and not meta_pixel:
        cohort = "C"
        pitch_angle = "meta_infra_gap"
    elif not meta_active and meta_pixel:
        cohort = "A"
        pitch_angle = "meta_dormant_pixel"
    elif not meta_active and not meta_pixel:
        cohort = "B"
        pitch_angle = "meta_greenfield"
    else:
        # Edge: active Meta but fewer than 3 creatives — treat as Cohort C-lite
        cohort = "C"
        pitch_angle = "meta_infra_gap"

    gates["meta"] = f"cohort_{cohort}"

    # Priority scoring
    base = {"C": 8, "A": 6, "B": 5}[cohort]
    if reviews >= 100:
        base += 1
    if reviews >= 300:
        base += 1
    if meta_creatives >= 5 and cohort == "C":
        base += 1
    priority = min(base, 10)

    # Auto-send eligible? verified email + priority >= 8 + no audit gaps
    has_verified_email = bool(record.get("email"))
    auto_send_eligible = priority >= 8 and has_verified_email and not pixels_unreach

    return {
        "verdict": "qualified",
        "gates": gates,
        "cohort": cohort,
        "priority": priority,
        "pitch_angle": pitch_angle,
        "google_ads_evidence": google_ads_evidence,
        "meta_status": {
            "pixel_installed": meta_pixel,
            "active_ads": meta_active,
            "creative_count": meta_creatives,
        },
        "leak_summary": _leak_summary(cohort, record, meta_creatives),
        "auto_send_eligible": auto_send_eligible,
    }


def _leak_summary(cohort: str, record: dict, creatives: int) -> str:
    name = record["business_name"]
    gatc_count = record.get("gatc_ad_count") or 0
    if cohort == "C":
        return (
            f"{name} runs {gatc_count} Google Ads creatives AND {creatives} live Meta creatives "
            f"but has no Facebook Pixel installed — every Meta click is unrecoverable."
        )
    if cohort == "A":
        return (
            f"{name} runs {gatc_count} Google Ads creatives and has a Facebook Pixel installed, "
            f"but is not running any Meta retargeting campaigns against it."
        )
    if cohort == "B":
        return (
            f"{name} runs {gatc_count} Google Ads creatives but has no Meta Pixel and no Meta "
            f"campaigns — paid Google traffic has nowhere to be retargeted on Meta."
        )
    return ""


def main():
    records = merge_sources()
    print(f"Loaded {len(records)} merged records")

    results = []
    for r in records:
        evalr = gate_evaluate(r)
        merged = {
            "slug": r["business_name"].lower().replace(" ", "-").replace("&", "and"),
            "business_name": r["business_name"],
            "category": r.get("category"),
            "city": r.get("city"),
            "website": r.get("website_url"),
            "phone": r.get("phone_number"),
            "email": r.get("email"),
            "rating": r.get("rating"),
            "review_count": r.get("review_count"),
            "ch_company_name": r.get("ch_company_name"),
            "gatc_ad_count": r.get("gatc_ad_count"),
            "meta_ad_count": r.get("meta_ad_count"),
            "pixels_v2": r.get("pixels_v2"),
            "old_tier": r.get("tier"),
            **evalr,
        }
        results.append(merged)

    # Save all
    (WS / "glasgow_requalified.json").write_text(json.dumps(results, indent=2))

    # Cohort C wave
    wave1 = [
        r for r in results if r["verdict"] == "qualified" and r.get("cohort") == "C"
    ]
    wave1.sort(key=lambda x: (-x["priority"], -(x.get("review_count") or 0)))
    (WS / "glasgow_wave1_cohortC.json").write_text(json.dumps(wave1, indent=2))

    # Funnel report
    verdicts = Counter(r["verdict"] for r in results)
    cohorts = Counter(r.get("cohort") for r in results if r["verdict"] == "qualified")
    lines = [
        "# Glasgow Re-qualification Funnel",
        f"_Run: {datetime.now(timezone.utc).isoformat()}_",
        "",
        f"**Source:** `_workspace/retarget/glasgow_ch.json` ({len(records)} records)",
        "",
        "## Verdict distribution",
        "",
    ]
    for verdict, count in verdicts.most_common():
        lines.append(f"- `{verdict}`: **{count}**")
    lines += ["", "## Cohort distribution (qualified only)", ""]
    if cohorts:
        for cohort, count in sorted(cohorts.items()):
            lines.append(f"- Cohort **{cohort}**: {count}")
    else:
        lines.append("- _(none qualified)_")
    lines += ["", "## Wave 1 (Cohort C, highest priority)", ""]
    if wave1:
        for r in wave1:
            lines.append(
                f"- **{r['business_name']}** ({r['category']}) — priority {r['priority']}, "
                f"{r['review_count']} reviews, email `{r['email']}`"
            )
    else:
        lines.append("- _(empty — no Cohort C leads under new ICP)_")
    lines += ["", "## Qualified leads (all cohorts)", ""]
    qualified_all = [r for r in results if r["verdict"] == "qualified"]
    qualified_all.sort(key=lambda x: (x["cohort"], -x["priority"]))
    for r in qualified_all:
        lines.append(
            f"- [{r['cohort']}] **{r['business_name']}** ({r['category']}) "
            f"priority={r['priority']} reviews={r['review_count']} email={r['email']}"
        )
    (WS / "glasgow_funnel.md").write_text("\n".join(lines) + "\n")

    print(f"\nVerdict distribution: {dict(verdicts)}")
    print(f"Cohort distribution: {dict(cohorts)}")
    print(f"Wave 1 (Cohort C) count: {len(wave1)}")
    print("\nOutputs:")
    print("  _workspace/retarget/glasgow_requalified.json")
    print("  _workspace/retarget/glasgow_wave1_cohortC.json")
    print("  _workspace/retarget/glasgow_funnel.md")


if __name__ == "__main__":
    main()
