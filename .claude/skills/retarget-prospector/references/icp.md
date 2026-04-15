# ICP — Retarget Prospector

Authoritative target definition. Every prospect must pass **all** gates below or be rejected with a specific `rejected_*` verdict.

## Statement

> Considered-purchase local service businesses in the UK, currently spending on Google Ads, with missing or underused Meta remarketing infrastructure.

The thesis: these businesses already pay Google for clicks (proven intent + budget), but the absence of Meta retargeting infrastructure means cold website visitors leak away unrecovered. The pitch is "you already buy the click, let us recover the bounce."

## Gate 1 — Geography

- **Required:** UK based. Country code `GB`.
- Crawled **city-by-city**. Phase 1 input is a single UK city (London, Manchester, Edinburgh, Birmingham, Leeds, Glasgow, Bristol, etc.). Never run Phase 1 against "UK" as a whole.
- Reject any business whose primary listing is outside GB — verify via Google Maps address country, phone country code, or registered address.

## Gate 2 — Category (whitelist + blacklist)

**Whitelist (considered-purchase, high-LTV).** Phase 1 may only run with one of these categories:

- Dentists, opticians
- Cosmetic / aesthetic clinics
- Private healthcare (private GPs, physiotherapy, fertility, etc.)
- Vets
- Solicitors — **private client work only** (family, wills, conveyancing, immigration, personal injury). Reject pure-corporate firms.
- Accountants
- Financial advisors, mortgage brokers
- Architects, interior designers
- Premium landscapers, painters, kitchen fitters (premium = bespoke / design-led, not emergency call-out)
- Wedding venues and premium wedding suppliers
- Private schools, tutoring
- Driving schools — **intensive courses only**, not pay-as-you-go
- Premium fitness (boutique studios, PT, pilates, climbing — not budget gyms)
- Coaching / consulting practices
- Specialist recruitment

**Blacklist (auto-reject):**

- Emergency-response trades (24/7 plumbers, locksmiths, boiler repair, towing, tree emergency). Their funnel is single-call-conversion — retargeting adds nothing.
- Restaurants, cafes, bars
- Convenience retail (corner shops, off-licences, newsagents)
- National chains and franchises (anything with >5 UK locations under one brand)
- NHS / council / charity-only providers (no ad budget, no commercial intent)

If the category is ambiguous, reject. Do not stretch the whitelist.

## Gate 3 — Required digital signal: Active Google Ads

**This is the hard gate.** Reject if neither of the two signals below is confirmed.

Signal must come from one of:

1. **Google Ads Transparency Center** — business or domain appears with at least one ad active in the last 90 days. Verified by `check_google_ads_transparency.py`.
2. **Google Ads Conversion Tag** detected on the live site — `gtag/js?id=AW-...`, `googleadservices.com/pagead/conversion`, `googleads.g.doubleclick.net`, or a Google Ads conversion linker fired from GTM. Verified by the rendered pixel auditor (`audit_pixels_v2`).

Either signal alone is sufficient. Both are stronger.

`unknown` ≠ `true`. If both probes return `unknown` (scraper failure or partial scan), the verdict is `rejected_unreachable`. Never assume.

## Gate 4 — Meta status (segmentation, not rejection)

Meta status does **not** reject — it segments. Every qualified prospect lands in exactly one cohort. Composer uses the cohort to pick the pitch angle.

| Cohort | Meta pixel | Meta ads active | Pitch angle |
|--------|-----------|-----------------|-------------|
| **A** | installed | none | `meta_dormant_pixel` — "you have the pixel, you're not using it for ads" |
| **B** | missing | none | `meta_greenfield` — "your Google traffic has nowhere to be retargeted" |
| **C** | missing OR misconfigured | active (3+ creatives) | `meta_infra_gap` — "you're already spending on Meta, but the pixel/CAPI is incomplete" |

Cohort C is highest priority — they have demonstrated willingness to spend on Meta and the gap is the most painful.

A prospect that has **active Meta ads AND a fully working pixel** is `rejected_no_leak` — there is nothing to sell them.

## Gate 5 — Website signal

Reject if any of the following:

- No real website (Facebook page only, Linktree, Google site builder, Wix one-pager with placeholder copy).
- Single-page site — must have **multiple service pages** (services, about, contact at minimum).
- No contact mechanism (no phone, no form, no email).
- Unrecognisable platform — accept WordPress, Webflow, Squarespace, Shopify, Wix (multi-page only), custom. Reject obviously dead/parked/under-construction sites.
- **Stale**: not updated within the last 12 months. Check copyright year in footer, latest blog post date, or last-modified header.

## Gate 6 — Trust signal

At least **one** of:

- 30+ Google reviews with average rating ≥ 4.0
- Trustpilot equivalent (30+ reviews, ≥4.0)
- Clear professional accreditation visible on the site (GDC for dentists, SRA for solicitors, ICAEW/ACCA for accountants, ARB/RIBA for architects, FCA for financial advisors, RCVS for vets, etc.)

## Gate 7 — Size signal

At least **one** of:

- 2+ team members visible on a "team" / "about" page
- Companies House data showing >1 employee or trading >2 years
- LinkedIn company page with 5+ employees
- Multiple service offerings priced/described separately (proxy for established operation)

Sole operators with no team page, no Companies House record, no LinkedIn presence, and a single-service site are rejected — they are unlikely to have budget for managed retargeting.

## Verdict mapping

| Failed gate | Verdict |
|-------------|---------|
| Gate 1 (geography) | `rejected_out_of_geo` |
| Gate 2 (category) | `rejected_out_of_icp` |
| Gate 3 (no Google Ads) | `rejected_no_google_ads` |
| Gate 3 (probes unknown) | `rejected_unreachable` |
| Gate 4 (Meta complete, no leak) | `rejected_no_leak` |
| Gate 5 (website) | `rejected_weak_web` |
| Gate 6 (trust) | `rejected_weak_trust` |
| Gate 7 (size) | `rejected_too_small` |
| All gates pass | `qualified` + cohort A/B/C |

Order of evaluation: 1 → 2 → 3 → 5 → 6 → 7 → 4. Run cheap rejects first; cohort assignment is last because it requires the full Meta audit.
