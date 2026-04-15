# Glasgow Retarget Prospecting — Final Report

**Date:** 2026-04-13
**Scope:** Glasgow, UK — 12 ICP whitelist categories
**Goal:** Find local businesses running Meta ads with no Meta pixel on site (Cohort C candidates — the retargeting-leak pitch has teeth when the advertiser is already paying Meta but losing the bounce).

## TL;DR

- 164 whitelist businesses crawled across 12 categories.
- 123 had no Meta pixel on site (75%).
- 118 unique after dedupe — each one checked against the Meta Ad Library with strict Page-name matching.
- **9 confirmed hits.** Of those, **6 are ICP-compliant local businesses**; 3 are national chains (auto-reject per ICP §Gate 2).

## Funnel

| Stage | Count |
|---|---|
| Whitelist businesses crawled (Google Maps) | 164 |
| &nbsp;&nbsp;→ already had Meta pixel (rejected) | 41 |
| &nbsp;&nbsp;→ missing Meta pixel | 123 |
| Unique candidates after dedupe | 118 |
| Checked in Meta Ad Library (strict Page-name filter) | 118 |
| Running active Meta ads (hits) | 9 |
| &nbsp;&nbsp;→ national chains (ICP reject) | 3 |
| &nbsp;&nbsp;→ **ICP-compliant local businesses** | **6** |

## Per-category breakdown

| Category | Crawled | No pixel | Meta-ad hits |
|---|---|---|---|
| dentist | 11 | 7 | 0 |
| optician | 12 | 11 | 3 (all chains) |
| cosmetic clinic | 15 | 5 | 1 |
| aesthetic clinic | 13 | 6 | 0 |
| veterinary clinic | 15 | 7 | 0 |
| solicitor | 12 | 11 | 0 |
| accountant | 12 | 12 | 0 |
| financial advisor | 15 | 12 | 1 |
| mortgage broker | 15 | 10 | 0 |
| architect | 15 | 12 | 0 |
| interior designer | 15 | 12 | 0 |
| wedding venue | 14 | 13 | 4 |
| **Total** | **164** | **118** | **9** |

## Qualified leads (ICP-compliant, local)

| # | Business | Category | Active ads | Rating | Reviews | Phone | Website |
|---|---|---|---|---|---|---|---|
| 1 | **Elanic** | cosmetic clinic | 2 | 4.4 | 361 | 0141 332 5106 | elanic.co.uk |
| 2 | **Spectrum Wealth Group** | financial advisor | 1 | 5.0 | 17 | 0141 732 1237 | spectrumwealthgroup.com |
| 3 | **Citation Weddings & Events** | wedding venue | 2 | 4.1 | 995 | 0141 559 6799 | citation-glasgow.com |
| 4 | **Arta** | wedding venue | 1 | 4.2 | 1035 | 0141 552 2101 | arta.co.uk |
| 5 | **WestEnd Venue** | wedding venue | 1 | 4.6 | 29 | — | westendvenue.co.uk |
| 6 | **The Exchange** | wedding venue | 2 | 4.6 | 8 | 0141 225 6654 | theexchangeglasgow.co.uk |

### Rejected — national chains (ICP §Gate 2)

| Business | Category | Active ads | Reason |
|---|---|---|---|
| Optical Express | optician | 23 | >5 UK locations, national chain |
| IOLLA | optician | 11 | national DTC brand, HQ-run marketing |
| Ace & Tate | optician | 29 | national DTC brand, HQ-run marketing |

## Methodology

### Phase 1 — Source
Google Maps text-search crawl per (category, "Glasgow") across the 12 ICP whitelist categories. Raw results written to `prospects/{category}-glasgow-no-pixel.json`. The `-no-pixel` suffix is a target, not a filter — each row carries a `pixel_audit` block recording what was actually found.

### Phase 2 — Pixel audit
Rendered (post-JavaScript) pixel audit via Playwright — `audit_pixels_v2`. Records `facebook_pixel`, `google_ads_remarketing`, `google_analytics`, `google_tag_manager`, TikTok, LinkedIn Insight. We only passed rows where `pixel_audit.facebook_pixel is False` into Phase 3.

### Phase 3 — Meta Ad Library verification
Strict Page-name match against the public Meta Ad Library search UI. Each candidate name is queried, each returned ad card is split on `Library ID: <digits>` markers, and the card-tail is inspected for a line matching the business name tokens followed by "Sponsored" within the next two lines. This rejects two classes of false positive:

1. **Keyword noise.** Meta's `search_type=keyword_unordered` matches ads whose body text happens to contain the query string. A naive "~X results" regex would have counted "Glasgow Mortgage Company" → 11 ads and "A&A Accountants Glasgow" → 50,000 ads (both false — the latter is keyword collisions across unrelated advertisers).
2. **Chain-brand dilution.** Strict Page-name matching means "Glasgow Mortgage Company" ads only count if the advertiser's Page name is literally "Glasgow Mortgage Company", not "MortgageGym plc".

A first pass using the batch scraper's naive regex returned **42 hits**. The strict-mode pass returned **9**. The difference is the false-positive rate of the naive parser (~79%).

### Phase 4 — ICP filter
Applied `.claude/skills/retarget-prospector/references/icp.md` Gate 2 (category whitelist + chain blacklist). Three of the 9 hits are national chains with centralised HQ marketing — not addressable by a Glasgow local-service pitch — so the final addressable shortlist is 6.

## Next steps

For each of the 6 qualified leads, the retargeting leak is provable:
- Google Ads status unknown (not yet gated by Phase 5). Worth running `check_google_ads_transparency.py` before outreach — if confirmed running, the pitch becomes "you're already paying Google for the click, let us recover the bounce on Meta" (Cohort C per ICP).
- Elanic + Spectrum Wealth Group are the highest-signal: good reviews, active Meta ads, considered-purchase verticals.
- Wedding venues (Citation, Arta, WestEnd, The Exchange) are all healthy review counts — high-LTV single-purchase, textbook retargeting targets.

## Artifacts

- `prospects/{category}-glasgow-no-pixel.json` — raw crawl output per category (12 files, 164 rows)
- `prospects/glasgow_meta_ads_no_pixel.json` — 9 Meta-ad hits with `meta_has_ads=true` and `pixel_audit.facebook_pixel=false` (strict Page-name verified)
- `scripts/glasgow_meta_ads_no_pixel.py` — driver script (throwaway, reuses `_page_name_matches` from `check_meta_ad_library.py`)
- `output/glasgow_final_report.md` — this file
