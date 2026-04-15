# Glasgow Retargeting Leak Report

**Date:** 2026-04-13
**Scope:** All 21 categories crawled in Glasgow, UK.
**Method:** For each business we verified (a) active paid-ad spend (Meta Ad Library page-name match + Google Ads Transparency Center) and (b) the presence of the matching retargeting pixel on the live website. A "leak" is ads running + pixel missing.

## Summary

| Pipeline | Candidates scanned | Running ads | Leak (no pixel) |
|---|---|---|---|
| Meta (strict Page-name match) | 206 | 9 | **9** |
| Google Ads (Transparency Center) | 249 | 26 | **16** |

Total unique businesses with a confirmed retargeting leak: **24** (1 business — Ace & Tate — appears on both lists).

---

## List 1 — Running Google Ads, no Google Ads remarketing tag (16)

| # | Business | Category | Ads | Rating | Reviews | Phone | Website |
|---|---|---|---|---|---|---|---|
| 1 | Luxe Skin Aesthetic Clinic by Dr Q | aesthetic clinic | 4 | 4.7 | 61 | 0141 573 1473 | luxeskin.co.uk |
| 2 | Glasgow Cleaning Specialists | cleaner | 2 | 4.8 | 116 | 07543 203536 | glasgowcleaningspecialists.co.uk |
| 3 | Sparkle Sparkle | cleaner | 4 | 3.6 | 231 | 07523 689180 | sparklesparkle.co.uk |
| 4 | The Home Maid | cleaner | 4 | 4.8 | 21 | 0141 374 2833 | thehomemaid.co.uk |
| 5 | Urban Carpet Cleaning | cleaner | 4 | 5.0 | 188 | 07914 152037 | urbancleaningcompany.co.uk |
| 6 | Dentistry @ Jordanhill | dentist | 4 | 4.9 | 449 | 0141 334 2550 | dentistryatjordanhill.co.uk |
| 7 | Jorges Landscaping and Gardening Services | landscaper | 4 | 4.9 | 98 | 07596 032247 | jorgeslandscapeandgardeningservices.co.uk |
| 8 | Caledonian Lock & Safe | locksmith | 4 | 4.6 | 107 | 0141 846 1817 | caledonianlock-safe.co.uk |
| 9 | Ace & Tate *(chain)* | optician | 4 | 4.7 | 54 | 0141 846 0681 | aceandtate.com |
| 10 | JSL Plumbing | plumber | 4 | 4.9 | 66 | 0141 406 1658 | jsl-glasgow.com |
| 11 | J. Shearer Roofing Ltd | roofer | 4 | 4.9 | 134 | 0141 638 6613 | jshearer-roofing.co.uk |
| 12 | Ross Clark Roofing Glasgow | roofer | 4 | 5.0 | 10 | 0141 374 0655 | rossclarkroofingayr.co.uk |
| 13 | Strathclyde Domestic Roofing | roofer | 3 | 5.0 | 79 | 0141 255 2448 | strathclydedomesticroofing.co.uk |
| 14 | Queens Crescent Veterinary Clinic | veterinary clinic | 1 | 4.4 | 131 | 0141 332 1934 | qcvc.co.uk |
| 15 | The Veterinary Centre | veterinary clinic | 1 | 4.7 | 320 | 0141 339 1228 | vetcentre.co.uk |
| 16 | Box Hub | wedding venue | 4 | 4.8 | 98 | 0141 266 0664 | boxhub.uk |

---

## List 2 — Running Meta ads, no Meta pixel (9)

| # | Business | Category | Ads | Rating | Reviews | Phone | Website |
|---|---|---|---|---|---|---|---|
| 1 | Elanic | cosmetic clinic | 2 | 4.4 | 361 | 0141 332 5106 | elanic.co.uk |
| 2 | Spectrum Wealth Group | financial advisor | 1 | 5.0 | 17 | 0141 732 1237 | spectrumwealthgroup.com |
| 3 | Ace & Tate *(chain)* | optician | 29 | 4.7 | 54 | 0141 846 0681 | aceandtate.com |
| 4 | IOLLA *(chain)* | optician | 11 | 4.9 | 358 | — | iolla.com |
| 5 | Optical Express *(chain)* | optician | 23 | 4.8 | 951 | 0141 732 7196 | opticalexpress.co.uk |
| 6 | Arta | wedding venue | 1 | 4.2 | 1035 | 0141 552 2101 | arta.co.uk |
| 7 | Citation Weddings & Events | wedding venue | 2 | 4.1 | 995 | 0141 559 6799 | citation-glasgow.com |
| 8 | The Exchange | wedding venue | 2 | 4.6 | 8 | 0141 225 6654 | theexchangeglasgow.co.uk |
| 9 | WestEnd Venue | wedding venue | 1 | 4.6 | 29 | — | westendvenue.co.uk |

---

## Cross-reference

**Ace & Tate** appears on both lists — they are running ads on *both* platforms and missing *both* retargeting pixels. Highest-priority target if in-ICP (note: national chain — ICP Gate 2 reject).

No other business overlaps between the two lists.

## Data sources

- `prospects/glasgow_google_ads_verification_latest.full.json` — 249 rows with GATC ad counts.
- `prospects/glasgow_meta_verification_latest.full.json` — 206 rows with naive + strict Meta ad counts.
- `prospects/*-glasgow-no-pixel.json` — 21 source crawl files, pixel audit included.

## Methodology notes

- **Meta verification** uses the `Library ID` card-split + page-name match parser (`check_meta_ad_library.py:_page_name_matches`). The naive `"~X results"` regex produced 73 hits against the same candidate set; 64 were keyword-match false positives (e.g. A&A Accountants → 50,000, The Engine Works → 45,000) and are excluded from List 2.
- **Google Ads verification** uses the public Google Ads Transparency Center, matching ads by website domain (not business name), so no keyword-noise class exists.
- **Pixel audit** is a rendered (post-JavaScript) Playwright scan — catches GTM-injected pixels that static HTML scraping would miss.
