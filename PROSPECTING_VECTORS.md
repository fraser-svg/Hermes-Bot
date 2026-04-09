# Prospecting Vectors — The Definitive List

Every automated signal Hermes can detect to find businesses that need help.
Grouped by what the signal proves. Ordered by value within each group.

Status key: BUILT | READY (can build now) | NEEDS_API | RESEARCH

---

## 1. NO ONLINE PRESENCE (£29-99/mo tier)

These businesses are invisible online. Easiest pitch: "You don't exist on the internet."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 1.1 | **No website** | Google Maps listing, no websiteUri | Google Places API | **BUILT** (`prospect.py`) |
| 1.2 | **No Google Business Profile** | Business exists (Companies House) but no GBP listing | Companies House API + Google Places cross-ref | READY |
| 1.3 | **GBP claimed but empty** | Has GBP but missing: photos, hours, description, categories | Google Places API (check field completeness) | READY |
| 1.4 | **No social media** | No Facebook page, no Instagram, no LinkedIn | Facebook Graph API + scrape | READY |
| 1.5 | **Not on any directory** | Missing from Checkatrade, Yell, TrustATrader, Rated People | Scrape directory searches | READY |

---

## 2. BAD WEBSITE (£99-199/mo tier)

They have a website but it's hurting them. Pitch: "Your site is losing you customers."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 2.1 | **Poor website quality** | Fails rubric: no CTA, no mobile, no trust signals, legacy code | HTML audit (fetch + parse) | **BUILT** (`prospect_poor_websites_v2.py`) |
| 2.2 | **Not mobile responsive** | No viewport meta, no media queries, fixed-width layout | HTML audit | **BUILT** (part of v2 rubric) |
| 2.3 | **No SSL/HTTPS** | Site loads on HTTP, no redirect to HTTPS. Chrome shows "Not Secure" | URL fetch, check scheme | READY |
| 2.4 | **Painfully slow** | Core Web Vitals failing. LCP > 4s, CLS > 0.25 | Google PageSpeed Insights API (free) | READY |
| 2.5 | **Built on free tier** | Wix free (wixsite.com subdomain), WordPress.com free, Weebly free, GoDaddy builder | URL/HTML pattern match | READY |
| 2.6 | **Ancient/abandoned site** | Copyright year 3+ years old, outdated design patterns, dead links | HTML scrape (©2019, broken hrefs) | READY |
| 2.7 | **Broken website** | HTTP 4xx/5xx, domain expired, DNS failure, SSL cert expired | URL fetch status codes | READY |
| 2.8 | **No sitemap or robots.txt** | Search engines can't crawl properly | Fetch /sitemap.xml and /robots.txt | READY |
| 2.9 | **Domain expiring soon** | WHOIS shows expiry within 90 days — business may not renew | WHOIS API (WhoisXML, Nominet) | NEEDS_API |

---

## 3. LEAKING MONEY (£299-499/mo tier)

They spend on marketing but the funnel is broken. Pitch: "You're paying for traffic and throwing it away."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 3.1 | **No tracking pixels** | Running ads but no FB Pixel, no Google remarketing tag | HTML scan for pixel signatures | **BUILT** (`prospect_no_pixel.py`) |
| 3.2 | **Running Google Ads, bad landing page** | Ads point to homepage instead of dedicated landing page. No conversion tracking. | Google Ads Transparency Center + site audit | READY |
| 3.3 | **No email capture** | No newsletter signup, no lead magnet, no contact form | HTML scan for `<form>`, `<input type="email">`, Mailchimp/ConvertKit embeds | READY |
| 3.4 | **No call tracking** | Phone number is just text, not a tracked number | HTML scan for `tel:` links, absence of CallRail/WhatConverts | READY |
| 3.5 | **No conversion tracking** | No Google Ads conversion tag, no Meta CAPI, no thank-you page redirect | HTML scan + form action analysis | READY |
| 3.6 | **No booking system** | Service business with no online booking, just "call us" | HTML scan for Calendly, Acuity, SimplyBook, Booksy, etc. | READY |

---

## 4. SEO GAPS (£199-399/mo tier)

They exist online but nobody finds them. Pitch: "Your competitors show up. You don't."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 4.1 | **Not ranking for "[category] [city]"** | Competitors appear in search, they don't | SerpAPI or scrape Google results | NEEDS_API |
| 4.2 | **No local schema markup** | Missing LocalBusiness structured data — Google can't parse them | HTML scan for `application/ld+json`, microdata | READY |
| 4.3 | **Inconsistent NAP** | Name/Address/Phone different across Google, Yell, Checkatrade, Facebook | Cross-reference multiple directory listings | READY |
| 4.4 | **No reviews strategy** | Great service (high rating) but low review count vs. competitors | Google Places API — compare review_count in category+city | READY |
| 4.5 | **Unanswered reviews** | Has reviews but owner never responds — looks like nobody's home | Google Places API review data (check for owner responses) | READY |
| 4.6 | **Missing from Apple Maps** | Android users find them, iPhone users don't | Apple Maps lookup | RESEARCH |
| 4.7 | **No backlinks/citations** | Not listed on local directories, trade associations, chamber of commerce | Scrape directory searches | READY |

---

## 5. REPUTATION GAPS (£149-299/mo tier)

Their online reputation is hurting them or underutilized. Pitch: "People are checking you online before calling. Here's what they see."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 5.1 | **Negative reviews unanswered** | 1-2 star reviews with no owner response — looks terrible | Google Places API | READY |
| 5.2 | **Rating declining** | Was 4.8, now 4.2. Trend visible in review dates. | Google Places API (review timestamps) | READY |
| 5.3 | **High rating, zero visibility** | 4.9 stars but only 5 reviews. Invisible vs. competitor with 4.5 and 200 reviews. | Google Places API | READY |
| 5.4 | **No Trustpilot/Checkatrade presence** | Reviews only on Google. Missing from platforms where prospects actively search for trades. | Scrape Trustpilot + Checkatrade for business name | READY |
| 5.5 | **Competitor with worse service ranks higher** | They have 4.9★ but competitor with 3.8★ outranks them because of better digital presence | Google Places API + search ranking comparison | READY |
| 5.6 | **Reviews mention website negatively** | "Couldn't find their website", "had to call because site was confusing" | NLP scan of review text | READY |

---

## 6. SOCIAL MEDIA GAPS (£99-299/mo tier)

Social exists but it's dead or counterproductive. Pitch: "Your last post was 8 months ago. That looks worse than no page at all."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 6.1 | **Dormant social accounts** | Facebook/Instagram last post 6+ months ago | Facebook Graph API / scrape | READY |
| 6.2 | **Active socials, dead website** | Posting on Instagram regularly but website is garbage or nonexistent | Cross-reference social activity vs. site quality | READY |
| 6.3 | **No link-in-bio** | Instagram active but bio has no website link, no Linktree, nothing | Scrape Instagram bio | RESEARCH |
| 6.4 | **Facebook page, no website linked** | Facebook business page exists but website field empty | Facebook Graph API | READY |
| 6.5 | **Good content, no funnel** | Posts get engagement but no clear path to conversion | Social scrape + site audit combined | RESEARCH |

---

## 7. COMPLIANCE GAPS (£199-499/mo tier)

They're technically breaking the law. Pitch: "You're required by law to have X. You don't. Here's the fix."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 7.1 | **No privacy policy** | GDPR requires it if collecting any data (contact form, analytics, cookies) | HTML scan for /privacy, "privacy policy" links | READY |
| 7.2 | **No cookie consent** | Using analytics/pixels without cookie banner — PECR/GDPR violation in UK | HTML scan for cookie consent scripts (CookieBot, OneTrust, etc.) | READY |
| 7.3 | **No ICO registration** | Business holds customer data but not registered with ICO (legally required) | ICO register lookup (ico.org.uk) | READY |
| 7.4 | **Missing company registration number** | UK LTDs must display company number on website | Companies House cross-ref + HTML scan | READY |
| 7.5 | **No accessibility** | Fails basic WCAG — no alt text, poor contrast, no keyboard nav. Legal risk. | HTML audit (alt attrs, contrast ratios, ARIA) | READY |
| 7.6 | **Missing VAT number** | VAT-registered businesses must display VAT number on site | Companies House + HTML scan | READY |

---

## 8. TIMING / EVENT SIGNALS (any tier — but with urgency)

External events create urgency. Pitch: "This is happening NOW. You need to be visible."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 8.1 | **Seasonal peak approaching** | Roofers before winter, HVAC before summer, landscapers before spring | Google Trends API (pytrends) + calendar | READY |
| 8.2 | **New business just registered** | Companies House filing in last 90 days. Fresh business, no digital presence yet. | Companies House API (free, 600 req/5min) | READY |
| 8.3 | **Hiring = growing** | Job posts on Indeed/Reed = business expanding, likely needs better digital presence | Adzuna API (free tier) or Reed API | NEEDS_API |
| 8.4 | **New housing developments nearby** | All trades needed in area — plumbers, electricians, builders | Planning portal / council data | RESEARCH |
| 8.5 | **Storm/weather event** | Heavy weather = roofers, tree surgeons, drainage businesses get surge demand | Met Office API + category mapping | RESEARCH |
| 8.6 | **Competitor just closed** | Google Maps shows competitor "permanently closed" — their customers need somewhere to go | Google Places API (businessStatus filter) | READY |
| 8.7 | **Recently changed ownership** | Companies House officer changes — new owner likely wants fresh start | Companies House API (officer appointments) | READY |

---

## 9. COMPETITIVE INTELLIGENCE (any tier)

Not about their weakness — about their competitor's strength. Pitch: "[Competitor] just did X. Your customers see it."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 9.1 | **Competitor just upgraded their site** | Competitor in same category+city recently launched modern site | Periodic site audit comparison (Wayback Machine API or re-crawl) | RESEARCH |
| 9.2 | **Competitor running ads, they're not** | Google/Meta ad transparency shows competitor spending | Google Ads Transparency + Meta Ad Library | READY |
| 9.3 | **Competitor has 10x reviews** | Same category, same city, one business has 200 reviews and they have 12 | Google Places API comparison | READY |
| 9.4 | **Market has weak digital presence overall** | Entire category+city has poor websites — first mover advantage for whoever upgrades | Aggregate audit of top 10 in category+city | READY |
| 9.5 | **Competitor ranking for their brand name** | Someone else's ad shows up when you Google their business name | Search query check | NEEDS_API |

---

## 10. FINANCIAL / GROWTH SIGNALS (£299+ tier)

Business is doing well financially but digital presence doesn't match. Pitch: "Your business grew. Your website didn't."

| # | Vector | Signal | Data Source | Status |
|---|--------|--------|-------------|--------|
| 10.1 | **Revenue growing, site static** | Companies House accounts show growth but website hasn't changed | Companies House API + Wayback Machine | RESEARCH |
| 10.2 | **Multiple locations, one bad site** | Business has expanded (multiple GBP listings) but one generic website | Google Places API (same brand, multiple locations) | READY |
| 10.3 | **Recently funded / got grant** | Government grant recipients list, startup loans | UK gov grant databases (public) | RESEARCH |
| 10.4 | **High-value services, cheap presence** | Premium pricing (evident from reviews/descriptions) but amateur website | Review text NLP + site quality audit | READY |

---

## PRIORITY RANKING — What to Build Next

Based on: data availability, automation ease, conversion likelihood, revenue per close.

| Priority | Vector | Why |
|----------|--------|-----|
| **P0** | 1.1 No website | **BUILT** |
| **P0** | 2.1 Poor website | **BUILT** |
| **P0** | 3.1 No tracking pixels | **BUILT** |
| **P1** | 8.2 New business registered | Companies House API is free, 90-day-old businesses = blank slate, high intent |
| **P1** | 2.4 Slow site (Core Web Vitals) | PageSpeed API is free, concrete proof, easy demo |
| **P1** | 7.1-7.4 Compliance gaps | Legal fear = urgency. GDPR/ICO non-compliance is provable and scary. |
| **P2** | 4.1 Not ranking for category+city | Proves invisibility with hard data. Needs SerpAPI or similar. |
| **P2** | 5.1 Negative reviews unanswered | Already have review data from Google Places. Just need analysis layer. |
| **P2** | 3.2-3.6 Funnel leaks (forms, booking, email) | Already fetching HTML. Just add more pattern checks. |
| **P2** | 8.1 Seasonal peak approaching | Google Trends is free. Time-pressure = urgency. |
| **P3** | 9.2-9.3 Competitor intelligence | Powerful but needs comparison framework |
| **P3** | 6.1 Dormant socials | Strong signal but social scraping is fragile |
| **P3** | 2.9 Domain expiring | WHOIS APIs cost money, but high-intent signal |

---

## THE COMPOUND PLAY

Single vectors find leads. Stacked vectors close deals.

Best stack per prospect:
1. **Detect** — any vector above triggers initial interest
2. **Enrich** — run ALL applicable audits on that one business
3. **Score** — composite score across all dimensions
4. **Bundle** — generate pitch showing ALL their gaps, not just one

Example output for one prospect:
```
Edinburgh Sparks Electrical
├── Website: POOR (42/100) — no mobile, no CTA, copyright 2019
├── Tracking: ZERO — no FB pixel, no GA, no GTM
├── SEO: NOT RANKING for "electrician edinburgh"
├── Reviews: 4.8★ but only 8 reviews (competitor has 156)
├── Compliance: NO privacy policy, NO cookie consent
├── Social: Facebook page dormant since March 2025
└── Opportunity score: 94/100 — HIGH VALUE LEAD
```

That's not a cold email. That's an audit they'd pay £500 for. We give it away free with a built website attached.

---

*50 vectors. 3 built. 30+ buildable with existing data sources. The rest need one new API key each.*
