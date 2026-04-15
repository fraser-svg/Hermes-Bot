# Glasgow Round 1 — Naive Meta Ad Library Scraper (false-positive baseline)

**Date:** 2026-04-13
**Status:** SUPERSEDED by round 2 (`glasgow_final_report.md`). Kept as a reference for false-positive analysis.

## Why this exists

First pass used `batch_verify_meta.verify_batch()`, which parses the Meta Ad Library results page with a naive regex:

```python
m = re.search(r"~?\s*([\d,]+)\s+result", body)
ad_count = int(m.group(1).replace(",", "")) if m else 0
```

That regex captures Meta's "~X results" banner for **any** keyword — it counts ads whose body text contains the query string, not ads run by the business itself. No Page-name filtering. It's the parser `check_meta_ad_library.py` explicitly rewrote away after the Wikipedia false-positive incident (CLAUDE.md change log, 2026-04-13).

Result: 42 "hits" from 118 candidates — **79% of them were false positives** per round 2 verification.

## Funnel (round 1, naive parser)

| category | candidates | "hits" |
|---|---|---|
| dentist | 7 | 1 |
| optician | 11 | 5 |
| cosmetic clinic | 5 | 3 |
| aesthetic clinic | 6 | 1 |
| veterinary clinic | 7 | 0 |
| solicitor | 11 | 3 |
| accountant | 12 | 3 |
| financial advisor | 12 | 3 |
| mortgage broker | 10 | 6 |
| architect | 12 | 0 |
| interior designer | 12 | 5 |
| wedding venue | 13 | 12 |
| **Total** | **118** | **42** |

## Raw "hits" list (naive parser)

Counts are Meta's "results" banner — **not** verified ads run by the named business. Use for calibration only.

| Business | Category | Naive count | Website |
|---|---|---|---|
| G1 Dental | dentist | 350 | g1dental.com |
| O'Callaghan Opticians | optician | 110 | ocallaghanopticians.com |
| Eyes Optical Optometrists | optician | 51 | eyesopticiansglasgow.co.uk |
| Optical Express | optician | 72 | opticalexpress.co.uk |
| IOLLA | optician | 44 | iolla.com |
| Ace & Tate | optician | 700 | aceandtate.com |
| Clinica Medica | cosmetic clinic | 76 | clinicamedica.co.uk |
| BBL Aesthetic Clinic | cosmetic clinic | 77 | beautebroderie.wixsite.com/semipermanentmakeup |
| Elanic | cosmetic clinic | 6 | elanic.co.uk |
| Sculpt Aesthetics Clinic | aesthetic clinic | 67 | sculptaestheticsclinic.co.uk |
| McVey & Murricane | solicitor | 1 | mmilegal.com |
| mccarthy law | solicitor | 3 | mccarthylaw.co.uk |
| McIntosh & McCann Family & Civil Solicitors | solicitor | 3 | mcintoshmccann.com |
| LPA Accountancy | accountant | 3 | lpa-accountancy.co.uk |
| A&A Accountants Glasgow | accountant | 50000 | aaaccounting.co.uk |
| The Kelvin Partnership | accountant | 2800 | thekelvinpartnership.com |
| The McKnight Financial Group | financial advisor | 2400 | tmfg.co.uk |
| Spectrum Wealth Group | financial advisor | 2 | spectrumwealthgroup.com |
| Prosperity Financial Solutions | financial advisor | 8 | prosperityfinancial.co.uk |
| Mortgage Advice Brokerage Ltd | mortgage broker | 2 | mortgageadvicebrokerage.co.uk |
| Bricks and Mortar Mortgages | mortgage broker | 10 | bricksandmortarmortgages.co.uk |
| Independent Mortgage Store | mortgage broker | 42 | independent-mortgage-store.co.uk |
| West End Mortgages | mortgage broker | 110 | westendmortgages.co.uk |
| The Glasgow Mortgage Company Ltd | mortgage broker | 11 | glasgowmortgagecompany.co.uk |
| Specialist Mortgages | mortgage broker | 57 | specialistmortgages.uk.com |
| Anne Interiors | interior designer | 2 | anneinteriors.com |
| Arch Interiors | interior designer | 20 | arch-interiors.co.uk |
| Interior Renovation Designs ltd | interior designer | 1 | interiorrenovationdesigns.com |
| Homes & Interiors | interior designer | 4500 | homesandinteriors.co.uk |
| Studio LBI | interior designer | 1 | studiolbi.com |
| The Engine Works | wedding venue | 45000 | theengine.works |
| Citation Weddings & Events | wedding venue | 190 | citation-glasgow.com |
| 200 SVS Conference & Events | wedding venue | 10 | 200svs.com |
| House for an Art Lover | wedding venue | 25000 | houseforanartlover.co.uk |
| Box Hub | wedding venue | 490 | boxhub.uk |
| Merchants House of Glasgow | wedding venue | 33 | merchantshouse.org.uk |
| Òran Mór | wedding venue | 50 | oran-mor.co.uk |
| Arta | wedding venue | 170 | arta.co.uk |
| WestEnd Venue | wedding venue | 1200 | westendvenue.co.uk |
| Bridge Gardens | wedding venue | 330 | boxhub.uk |
| The Exchange | wedding venue | 50000 | theexchangeglasgow.co.uk |
| Cottiers | wedding venue | 15 | cottiers.com |

## Round 1 vs Round 2 comparison

Of the 42 round-1 hits, only **9 survived** strict Page-name verification in round 2:

| Business | R1 naive | R2 strict | Note |
|---|---|---|---|
| Optical Express | 72 | 23 | chain, reject |
| IOLLA | 44 | 11 | chain, reject |
| Ace & Tate | 700 | 29 | chain, reject |
| Elanic | 6 | 2 | **qualified** |
| Spectrum Wealth Group | 2 | 1 | **qualified** |
| Citation Weddings & Events | 190 | 2 | **qualified** |
| Arta | 170 | 1 | **qualified** |
| WestEnd Venue | 1200 | 1 | **qualified** |
| The Exchange | 50000 | 2 | **qualified** |
| *(33 others)* | — | 0 | false positive, dropped |

Notable false positives killed by strict mode:

- **A&A Accountants Glasgow** → 50,000 → 0. Query matches unrelated ads mentioning "Glasgow" or "accountants" across Meta's entire GB inventory.
- **The Engine Works** → 45,000 → 0. Keyword collision with the noun phrase "engine works".
- **Homes & Interiors** → 4,500 → 0. Magazine-title keyword collision.
- **The Kelvin Partnership** → 2,800 → 0. Pattern of long-tail brand names getting matched against generic ad copy.

Across the 33 killed false positives, median naive count was ~100 with long tail up to 50k — all driven by ad body-text keyword matching, zero actually run by the named business.

## Lesson

Naive "X results" regex has no place in retargeting qualification. Always use the Page-name split-by-`Library ID` filter from `check_meta_ad_library.py:53` when targeting small local businesses whose names contain common words (Glasgow, Mortgage, Venue, Exchange, Interiors, etc.).

The `batch_verify_meta.py` scraper should be patched or deprecated before any future city run — otherwise every outreach queue built on top of it is 80% noise.
