# Qualification Gates — No-Website Cohort

## Gate Order (cheap-reject-first)

| # | Gate | Pass | Fail verdict |
|---|------|------|--------------|
| 1 | Geography (UK) | `city` ∈ UK OR address contains UK postcode/region | `rejected_geo` |
| 2 | Category whitelist | `business_category` ∈ considered-purchase list | `rejected_category` |
| 3 | Operating status | `business_status != CLOSED_PERMANENTLY` | `rejected_closed` |
| 4 | Website health | `no_site` / `broken` / `placeholder` | `rejected_has_site` (if `ok`) or `needs_check` (if unknown) |
| 5 | Rating | `rating >= 3.8` | `rejected_rating` or `rejected_no_rating` (if 0/missing) |
| 6 | Review count | `review_count >= 10` | `rejected_low_reviews` |
| 7 | Phone present | `phone_number` non-empty | `rejected_no_phone` |

## Website Health Probe Rules

Probe order: HEAD → GET (if HEAD 405).

| Observation | health status |
|-------------|--------------|
| URL empty / null / "n/a" | `no_site` |
| HTTP status ≥ 400 OR timeout (>10s) OR DNS failure | `broken` |
| HTTP 200 + `<title>` empty OR contains "Coming Soon" / "Under Construction" / "Just another WordPress site" / "Site not published" (Wix default) | `placeholder` |
| HTTP 200 + non-placeholder title | `ok` |
| Probe not attempted (e.g. network unavailable) | `needs_check` |

**Critical rule:** `needs_check` never auto-qualifies. Operator must re-run with network available, or treat as rejected.

## Placeholder Signals

Case-insensitive substring match on the HTML's `<title>` + first 2KB of body text:

- "coming soon"
- "under construction"
- "just another wordpress site"
- "site not published"
- "welcome to wordpress"
- "default web site page"
- "this domain is for sale"
- "parked domain"

## Category Whitelist

Considered-purchase local services where a built site moves revenue:

**Trades:** electrician, plumber, roofer, hvac, cleaner, painter, locksmith, mover, pest control, landscaper, builder, carpenter, tiler, plasterer, glazier, garage door

**Professional services:** lawyer, solicitor, accountant, dentist, physiotherapist, chiropractor, optician, vet, veterinarian, tutor, driving instructor, photographer, personal trainer, beauty salon, hairdresser, barber, dog groomer, caterer, florist, mechanic, tailor, estate agent, architect, surveyor, financial advisor, insurance broker, it support, web designer, marketing agency, printing

Categories outside this list → `rejected_category`.

## Cohort Assignment (qualified only)

| website_health | cohort | priority |
|----------------|--------|----------|
| `no_site` | `A_greenfield` | 1 (highest — zero competition for the domain) |
| `broken` | `B_broken` | 2 (urgent — existing business, dead site) |
| `placeholder` | `C_placeholder` | 3 (warm — business aware, but not serious) |

## Rationale

- Lower rating floor (3.8 vs retarget's 4.0) because no-website businesses rarely invest in reputation management; we still want legitimate operators.
- Lower review floor (10 vs retarget's 30) because no-website businesses naturally accumulate fewer digital reviews.
- Phone required (unlike retarget which accepts email-only) because outreach channel for no-website cohort leans heavily on SMS/WhatsApp/call.
