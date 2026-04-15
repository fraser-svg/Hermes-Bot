#!/usr/bin/env python3
"""Deterministic GBP grading from Places API Details JSON.

Rubric (renormalised to exclude Posts, Q&A, owner-response-rate, photo taxonomy):
    Completeness          23.5%
    Visuals               17.6%
    Reviews               35.3%
    Categories/Attributes 17.6%
    Technical              5.9%

Input:  _workspace/retarget_scotland/scotland_prospects_gbp_details.json
Output: _workspace/retarget_scotland/scotland_prospects_gbp_graded.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

WEIGHTS = {
    "completeness": 0.235,
    "visuals": 0.176,
    "reviews": 0.353,
    "categories_attributes": 0.176,
    "technical": 0.059,
}

# Service category whitelist — primary-type strings we consider "exact match".
CATEGORY_WHITELIST = {
    "accountant": {"accounting", "accountant", "tax_consultant", "tax_preparation_service"},
    "solicitor": {"lawyer", "law_firm", "legal_services"},
    "dentist": {"dentist", "dental_clinic"},
    "optician": {"optician", "eye_care_center"},
    "physio": {"physiotherapist"},
    "vet": {"veterinary_care"},
    "electrician": {"electrician"},
    "plumber": {"plumber"},
    "roofer": {"roofing_contractor"},
}


def _score_reviews_volume(n: int) -> float:
    if n <= 5:
        return 2
    if n <= 15:
        return 4
    if n <= 30:
        return 6
    if n <= 75:
        return 7
    if n <= 150:
        return 8
    if n <= 300:
        return 9
    return 10


def _score_reviews_rating(r: float) -> float:
    if r is None or r < 3.0:
        return 2
    if r < 3.5:
        return 4
    if r < 4.0:
        return 6
    if r < 4.3:
        return 7
    if r < 4.6:
        return 8
    if r < 4.8:
        return 9
    return 10


def _score_reviews_recency(reviews: list[dict]) -> float:
    """Plan spec: 0 in 6+mo → 2; 1-2 in last 3mo → 5; 3+ in last 3mo → 8."""
    if not reviews:
        return 2
    now = time.time()
    ts_3mo = now - 90 * 86400
    ts_6mo = now - 180 * 86400
    count_3mo = 0
    latest = 0.0
    for rv in reviews:
        pt = rv.get("publishTime")
        if not pt:
            continue
        try:
            t = time.mktime(time.strptime(pt.replace("Z", "+0000")[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            continue
        latest = max(latest, t)
        if t >= ts_3mo:
            count_3mo += 1
    if latest < ts_6mo:
        return 2
    if count_3mo >= 3:
        return 8
    if count_3mo >= 1:
        return 5
    return 4


def score_completeness(d: dict) -> tuple[float, dict]:
    pts = 0.0
    gaps = []
    dn = d.get("displayName")
    if dn and (dn.get("text") if isinstance(dn, dict) else dn):
        pts += 1
    else:
        gaps.append("displayName")
    if d.get("primaryType"):
        pts += 1
    else:
        gaps.append("primaryType")
    if len(d.get("types") or []) >= 3:
        pts += 1
    else:
        gaps.append("secondary_types")
    if d.get("formattedAddress"):
        pts += 1
    else:
        gaps.append("address")
    if d.get("nationalPhoneNumber"):
        pts += 1
    elif d.get("internationalPhoneNumber"):
        pts += 0.5
        gaps.append("national_phone")
    else:
        gaps.append("phone")
    if d.get("websiteUri"):
        pts += 1
    else:
        gaps.append("website")
    hrs = d.get("regularOpeningHours") or {}
    if hrs.get("weekdayDescriptions"):
        pts += 1
    else:
        gaps.append("hours")
    es = d.get("editorialSummary")
    if es:
        text = es.get("text") if isinstance(es, dict) else es
        if text and len(text) > 120:
            pts += 1
        else:
            pts += 0.5
            gaps.append("editorialSummary_thin")
    else:
        gaps.append("editorialSummary")
    if any(d.get(k) for k in ("paymentOptions", "parkingOptions", "accessibilityOptions", "amenities")):
        pts += 1
    else:
        gaps.append("attributes_empty")
    if d.get("businessStatus") == "OPERATIONAL":
        pts += 1
    else:
        gaps.append(f"status_{d.get('businessStatus')}")
    return pts, {"gaps": gaps}


def score_visuals(d: dict) -> tuple[float, dict]:
    photos = d.get("photos") or []
    n = len(photos)
    if n == 0:
        s = 0.0
    elif n <= 2:
        s = 3.0
    elif n <= 5:
        s = 6.0
    elif n <= 9:
        s = 8.0
    else:
        s = 10.0
    return s, {"photo_count_api": n, "note": "photo_count_api_capped_at_10"}


def score_reviews(d: dict) -> tuple[float, dict]:
    n = d.get("userRatingCount") or 0
    r = d.get("rating")
    reviews = d.get("reviews") or []
    sv = _score_reviews_volume(n)
    sr = _score_reviews_rating(r)
    srecency = _score_reviews_recency(reviews)
    overall = (sv + sr + srecency) / 3.0
    return overall, {
        "volume": sv, "rating": sr, "recency": srecency,
        "count": n, "avg_rating": r, "sampled_reviews": len(reviews),
    }


def _whitelist_for(category: str) -> set[str]:
    return CATEGORY_WHITELIST.get((category or "").lower(), set())


def score_categories(d: dict, expected_category: str) -> tuple[float, dict]:
    primary = (d.get("primaryType") or "").lower()
    types = [t.lower() for t in (d.get("types") or [])]
    wl = _whitelist_for(expected_category)
    if wl and primary in wl:
        primary_score = 10.0
    elif wl and any(t in wl for t in types):
        primary_score = 5.0
    elif wl:
        primary_score = 2.0
    else:
        primary_score = 7.0  # unknown expected category — neutral
    secondary_count = max(0, len(types) - 1)
    if secondary_count == 0:
        sec = 0.0
    elif secondary_count <= 2:
        sec = 5.0
    else:
        sec = 10.0
    attr_groups = sum(1 for k in ("paymentOptions", "parkingOptions", "accessibilityOptions", "amenities") if d.get(k))
    if attr_groups == 0:
        attrs = 0.0
    elif attr_groups <= 2:
        attrs = 5.0
    else:
        attrs = 10.0
    overall = primary_score * 0.4 + sec * 0.3 + attrs * 0.3
    return overall, {"primary": primary_score, "secondary": sec, "attrs": attrs, "primary_type": primary}


def score_technical(d: dict, row: dict) -> tuple[float, dict]:
    pts = 0.0
    parts = {}
    if d.get("businessStatus") == "OPERATIONAL":
        pts += 4
        parts["operational"] = True
    if row.get("fetch_status") == "ok":
        pts += 3
        parts["website_ok"] = True
    src_addr = (row.get("address") or "").lower()
    gbp_addr = (d.get("formattedAddress") or "").lower()
    if src_addr and gbp_addr:
        sim = SequenceMatcher(None, src_addr, gbp_addr).ratio()
        parts["nap_similarity"] = round(sim, 2)
        if sim >= 0.8:
            pts += 3
    return pts, parts


def letter(score: float) -> str:
    if score >= 9.0:
        return "A+"
    if score >= 8.0:
        return "A"
    if score >= 7.0:
        return "B"
    if score >= 6.0:
        return "C"
    if score >= 5.0:
        return "D"
    return "F"


def top_fixes(cat_meta: dict, comp_meta: dict, rev_meta: dict, tech_meta: dict, d: dict) -> list[str]:
    fixes = []
    gaps = comp_meta.get("gaps", [])
    if "editorialSummary" in gaps or "editorialSummary_thin" in gaps:
        fixes.append("Write a 600-750 char GBP business description covering services, unique value, and location")
    photo_n = cat_meta.get("primary") is not None  # unused sentinel
    photos = len(d.get("photos") or [])
    if photos < 6:
        fixes.append(f"Upload {max(6-photos,1)}+ photos: exterior, 2 interior, team, and 2 service shots")
    if "secondary_types" in gaps:
        fixes.append("Add 2-4 secondary GBP categories aligned with your primary service")
    if "hours" in gaps:
        fixes.append("Publish complete weekly hours including bank holidays")
    if "attributes_empty" in gaps:
        fixes.append("Fill service-option attributes (payment, parking, accessibility, amenities)")
    count = rev_meta.get("count") or 0
    if count < 16:
        fixes.append("Run a review campaign — target 20+ Google reviews in next 90 days")
    if rev_meta.get("recency", 10) <= 4:
        fixes.append("Request reviews from last 10 customers this week")
    if (rev_meta.get("avg_rating") or 5) < 4.3:
        fixes.append("Respond to the lowest-rated reviews and address systemic issues flagged")
    if tech_meta.get("nap_similarity", 1.0) < 0.8:
        fixes.append("Align address on GBP, website footer, and top 5 citations")
    return fixes[:3] or ["No critical gaps detected — focus on post cadence and Q&A"]


def grade_row(row: dict) -> dict:
    d = row.get("gbp_details") or {}
    if not d:
        return {
            "gbp_overall_grade": "F",
            "gbp_overall_score": 0.0,
            "gbp_notes": [row.get("gbp_details_error", "no_details")],
            "gbp_checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    c_score, c_meta = score_completeness(d)
    v_score, v_meta = score_visuals(d)
    r_score, r_meta = score_reviews(d)
    cat_score, cat_meta = score_categories(d, row.get("business_category", ""))
    t_score, t_meta = score_technical(d, row)

    raw = (
        c_score * WEIGHTS["completeness"]
        + v_score * WEIGHTS["visuals"]
        + r_score * WEIGHTS["reviews"]
        + cat_score * WEIGHTS["categories_attributes"]
        + t_score * WEIGHTS["technical"]
    )

    overrides = []
    if d.get("businessStatus") != "OPERATIONAL":
        raw = min(raw, 3.0)  # cap at F
        overrides.append("not_operational")
    if (d.get("userRatingCount") or 0) == 0:
        raw = min(raw, 5.5)  # cap at D
        overrides.append("zero_reviews")
    if cat_meta.get("primary", 0) <= 2:
        raw = min(raw, 6.5)  # cap at C
        overrides.append("primary_category_mismatch")

    notes = ["photo_count_api_capped_at_10"]
    notes.append("dropped_from_grade: Posts, QA, owner_response, photo_taxonomy, services_list")

    fixes = top_fixes(cat_meta, c_meta, r_meta, t_meta, d)

    return {
        "gbp_overall_score": round(raw, 2),
        "gbp_overall_grade": letter(raw),
        "gbp_completeness_score": round(c_score, 2),
        "gbp_visuals_score": round(v_score, 2),
        "gbp_reviews_score": round(r_score, 2),
        "gbp_categories_attributes_score": round(cat_score, 2),
        "gbp_technical_score": round(t_score, 2),
        "gbp_top_fix_1": fixes[0] if len(fixes) >= 1 else "",
        "gbp_top_fix_2": fixes[1] if len(fixes) >= 2 else "",
        "gbp_top_fix_3": fixes[2] if len(fixes) >= 3 else "",
        "gbp_overrides_applied": overrides,
        "gbp_notes": notes,
        "gbp_sub_meta": {
            "completeness": c_meta,
            "visuals": v_meta,
            "reviews": r_meta,
            "categories": cat_meta,
            "technical": t_meta,
        },
        "gbp_checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="_workspace/retarget_scotland/scotland_prospects_gbp_details.json")
    ap.add_argument("--output", default="_workspace/retarget_scotland/scotland_prospects_gbp_graded.json")
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    rows = json.loads(inp.read_text())
    for row in rows:
        row.update(grade_row(row))
    out.write_text(json.dumps(rows, indent=2))

    dist = {}
    for r in rows:
        g = r.get("gbp_overall_grade", "?")
        dist[g] = dist.get(g, 0) + 1
    print(f"wrote {out}  n={len(rows)}", file=sys.stderr)
    print(f"grade distribution: {dist}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
