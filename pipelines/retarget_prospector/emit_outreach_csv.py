#!/usr/bin/env python3
"""Emit final outreach CSV for Scotland retarget campaign.

Merges:
    - scotland_candidates_gatc_meta.json (all candidates with GATC + Meta verdicts)
    - scotland_candidates_fullaudit.json (prospect subset with GBP + extended audit)

Emits output/scotland_outreach.csv with:
    is_prospect, tier, priority, ad-spend signals, pixel gaps, GBP grade, call-tracking,
    phone type, form tracking, top-3 fixes, pitch angle.

Also prints grade distribution summary for prospects.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
WS = BASE / "_workspace" / "retarget_scotland"
OUT_DIR = BASE / "output"

COLUMNS = [
    "slug", "business_name", "business_category", "city", "address",
    "phone_number", "phone_e164", "phone_type", "website_url", "domain",
    "rating", "review_count", "tier",
    "is_spending_money", "spending_evidence",
    "gatc_has_ads", "gatc_ad_count", "gatc_url", "gatc_checked_at",
    "meta_has_ads", "meta_ad_count", "meta_url", "meta_checked_at",
    "has_meta_pixel", "has_google_ads_remarketing", "has_google_ads_conversion",
    "has_gtm", "has_ga4", "has_tiktok_pixel",
    "is_prospect", "cohort", "priority",
    "call_tracking_provider", "call_tracking_evidence",
    "form_ga4_event", "form_gtm_tag", "form_google_ads_conv", "form_tel_link",
    "gbp_overall_grade", "gbp_overall_score",
    "gbp_completeness_score", "gbp_visuals_score", "gbp_reviews_score",
    "gbp_categories_attributes_score", "gbp_technical_score",
    "gbp_top_fix_1", "gbp_top_fix_2", "gbp_top_fix_3",
    "gbp_overrides_applied", "gbp_notes",
    "pitch_angle",
]


def is_true(v) -> bool:
    return v is True


def compute_is_prospect(row: dict) -> bool:
    spending = is_true(row.get("gatc_has_ads")) or is_true(row.get("meta_has_ads"))
    if not spending:
        # fallback: existing google_ads_conversion / google_ads_remarketing tags imply past spend
        pix = row.get("pixels_v2") or {}
        spending = bool(pix.get("google_ads_conversion") or pix.get("google_ads_remarketing"))
    pix = row.get("pixels_v2") or {}
    no_meta = not bool(pix.get("facebook_pixel"))
    return spending and no_meta


def compute_cohort(row: dict) -> str:
    """A: active google ads, has meta pixel dormant but not firing visibly → skipped here (we require no_meta).
    B: greenfield — running ads, no pixels at all.
    C: active ads + infra gap (has some tags but missing meta pixel).
    """
    pix = row.get("pixels_v2") or {}
    has_any_tag = any(pix.get(k) for k in ("google_analytics", "google_tag_manager", "google_ads_conversion", "google_ads_remarketing"))
    if is_true(row.get("meta_has_ads")) and not has_any_tag:
        return "B"  # greenfield, actively running meta
    if is_true(row.get("gatc_has_ads")) and has_any_tag:
        return "C"  # spending + infra gap
    if is_true(row.get("gatc_has_ads")) or is_true(row.get("meta_has_ads")):
        return "B"
    return ""


def compute_priority(row: dict) -> int:
    score = 0
    if is_true(row.get("gatc_has_ads")):
        score += 50 + min(row.get("gatc_ad_count") or 0, 20)
    if is_true(row.get("meta_has_ads")):
        score += 30 + min(row.get("meta_ad_count") or 0, 20)
    grade = row.get("gbp_overall_grade") or ""
    grade_bonus = {"A+": 25, "A": 22, "B": 18, "C": 12, "D": 6, "F": 0}.get(grade, 0)
    score += grade_bonus
    if row.get("tier") == "tier1":
        score += 10
    if row.get("call_tracking_provider"):
        score += 5
    return score


def compute_pitch_angle(row: dict) -> str:
    gatc = is_true(row.get("gatc_has_ads"))
    meta = is_true(row.get("meta_has_ads"))
    pix = row.get("pixels_v2") or {}
    if gatc and not pix.get("facebook_pixel"):
        return "You're spending on Google Ads but not retargeting Meta traffic — ~70% of clicks never convert first visit"
    if meta and not pix.get("facebook_pixel"):
        return "You're running Meta ads but the pixel isn't firing on your site — you're losing the retargeting pool"
    if pix.get("google_ads_remarketing") and not pix.get("facebook_pixel"):
        return "Google retargeting tag is live, Meta pixel isn't — cross-channel retargeting gap"
    return "Tracking gap: spending on ads without full conversion + retargeting pixel coverage"


def row_to_csv(row: dict) -> dict:
    pix = row.get("pixels_v2") or {}
    is_prospect = compute_is_prospect(row)
    cohort = compute_cohort(row) if is_prospect else ""
    spending = is_true(row.get("gatc_has_ads")) or is_true(row.get("meta_has_ads")) or bool(pix.get("google_ads_conversion") or pix.get("google_ads_remarketing"))
    evidence_parts = []
    if is_true(row.get("gatc_has_ads")):
        evidence_parts.append(f"gatc:{row.get('gatc_ad_count') or 0}")
    if is_true(row.get("meta_has_ads")):
        evidence_parts.append(f"meta:{row.get('meta_ad_count') or 0}")
    if pix.get("google_ads_conversion"):
        evidence_parts.append("gac_conv_tag")
    if pix.get("google_ads_remarketing"):
        evidence_parts.append("gac_remarketing_tag")
    ft = row.get("form_tracking") or {}
    out = {
        "slug": row.get("slug", ""),
        "business_name": row.get("business_name", ""),
        "business_category": row.get("business_category", ""),
        "city": row.get("city", ""),
        "address": row.get("address", ""),
        "phone_number": row.get("phone_number", ""),
        "phone_e164": row.get("phone_e164", ""),
        "phone_type": row.get("phone_type", ""),
        "website_url": row.get("website_url", ""),
        "domain": row.get("domain", ""),
        "rating": row.get("rating", ""),
        "review_count": row.get("review_count", ""),
        "tier": row.get("tier", ""),
        "is_spending_money": spending,
        "spending_evidence": ";".join(evidence_parts),
        "gatc_has_ads": row.get("gatc_has_ads"),
        "gatc_ad_count": row.get("gatc_ad_count", ""),
        "gatc_url": row.get("gatc_url", ""),
        "gatc_checked_at": row.get("gatc_checked_at", ""),
        "meta_has_ads": row.get("meta_has_ads"),
        "meta_ad_count": row.get("meta_ad_count", ""),
        "meta_url": row.get("meta_url", ""),
        "meta_checked_at": row.get("meta_checked_at", ""),
        "has_meta_pixel": bool(pix.get("facebook_pixel")),
        "has_google_ads_remarketing": bool(pix.get("google_ads_remarketing")),
        "has_google_ads_conversion": bool(pix.get("google_ads_conversion")),
        "has_gtm": bool(pix.get("google_tag_manager")),
        "has_ga4": bool(pix.get("google_analytics")),
        "has_tiktok_pixel": bool(pix.get("tiktok_pixel")),
        "is_prospect": is_prospect,
        "cohort": cohort,
        "priority": compute_priority(row) if is_prospect else 0,
        "call_tracking_provider": row.get("call_tracking_provider") or "",
        "call_tracking_evidence": row.get("call_tracking_evidence") or "",
        "form_ga4_event": ft.get("ga4_event"),
        "form_gtm_tag": ft.get("gtm_tag"),
        "form_google_ads_conv": ft.get("google_ads_conv"),
        "form_tel_link": ft.get("tel_link"),
        "gbp_overall_grade": row.get("gbp_overall_grade", ""),
        "gbp_overall_score": row.get("gbp_overall_score", ""),
        "gbp_completeness_score": row.get("gbp_completeness_score", ""),
        "gbp_visuals_score": row.get("gbp_visuals_score", ""),
        "gbp_reviews_score": row.get("gbp_reviews_score", ""),
        "gbp_categories_attributes_score": row.get("gbp_categories_attributes_score", ""),
        "gbp_technical_score": row.get("gbp_technical_score", ""),
        "gbp_top_fix_1": row.get("gbp_top_fix_1", ""),
        "gbp_top_fix_2": row.get("gbp_top_fix_2", ""),
        "gbp_top_fix_3": row.get("gbp_top_fix_3", ""),
        "gbp_overrides_applied": ";".join(row.get("gbp_overrides_applied") or []),
        "gbp_notes": ";".join(row.get("gbp_notes") or []),
        "pitch_angle": compute_pitch_angle(row) if is_prospect else "",
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(WS / "scotland_candidates_gatc_meta.json"))
    ap.add_argument("--prospects", default=str(WS / "scotland_candidates_fullaudit.json"))
    ap.add_argument("--output", default=str(OUT_DIR / "scotland_outreach.csv"))
    args = ap.parse_args()

    cands = json.loads(Path(args.candidates).read_text())
    prospects = {}
    pp = Path(args.prospects)
    if pp.exists():
        for p in json.loads(pp.read_text()):
            prospects[p.get("slug")] = p

    merged = []
    for c in cands:
        slug = c.get("slug")
        if slug in prospects:
            c = {**c, **prospects[slug]}
        merged.append(c)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in merged:
            w.writerow(row_to_csv(row))

    grade_dist = {}
    prospect_count = 0
    for row in merged:
        if compute_is_prospect(row):
            prospect_count += 1
            g = row.get("gbp_overall_grade", "?") or "ungraded"
            grade_dist[g] = grade_dist.get(g, 0) + 1
    print(f"wrote {args.output}  rows={len(merged)}  prospects={prospect_count}", file=sys.stderr)
    print(f"prospect grade distribution: {grade_dist}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
