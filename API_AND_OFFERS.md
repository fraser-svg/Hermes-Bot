# APIs & Offers — Filtered for Reality

---

## PART 1: API MAP

### Already Have (in .env)

| API | Key | Powers |
|-----|-----|--------|
| Google Places API (New) | `GOOGLE_MAPS_API` | All prospecting — find businesses, reviews, ratings, website/no-website |
| OpenRouter (Gemini) | `openrouter` | Website generation, content writing, email drafting |
| Firecrawl | `FIRECRAWL_API_KEY` | JS-rendered page fetching for site audits |
| Netlify | `NETLIFY_AUTH_TOKEN` | Preview hosting + deploy |
| SendGrid | `SENDGRID_API_KEY` | Outreach emails + welcome emails |
| Stripe | `STRIPE_SECRET_KEY` | Payment + subscription management |

### Free APIs — Just Need to Register

| API | Cost | Register At | Powers Which Vectors |
|-----|------|-------------|---------------------|
| **Google PageSpeed Insights** | Free (no key needed, or use existing Google key) | Uses existing key | 2.4 Slow sites — Core Web Vitals with hard numbers |
| **Companies House** | Free (600 req/5min) | developer.company-information.service.gov.uk | 8.2 New businesses, 8.7 ownership changes, 7.4 company number check |
| **Meta Ad Library** | Free (needs Meta developer account) | developers.facebook.com | 3.1 Confirm businesses actively spending on ads |
| **Google Trends (pytrends)** | Free (no key) | pip install pytrends | 8.1 Seasonal peaks — time outreach to demand surges |

### Paid APIs — Only If Justified by ROI

| API | Cost | Powers | Verdict |
|-----|------|--------|---------|
| **SerpAPI** | $50/mo (5000 searches) | 4.1 Search ranking checks | WORTH IT — "you're not ranking" is a killer proof point |
| **WhoisXML** | $25/mo | 2.9 Domain expiry detection | SKIP — low volume signal, not worth the cost |
| **Adzuna** | Free tier available | 8.3 Hiring/growth signals | MAYBE — free tier, low effort to add |
| **CallRail / WhatConverts** | $45+/mo | 3.4 Call tracking as a service | SKIP for prospecting. Offer as upsell service, don't use for detection. |

### No API Needed — Already Fetching HTML

These are just pattern-match additions to existing page fetch. Zero new cost.

| Check | How | Add To |
|-------|-----|--------|
| SSL/HTTPS | Check URL scheme after redirect | prospect_poor_websites_v2.py |
| Privacy policy | Scan for "/privacy", "privacy policy" links | prospect_poor_websites_v2.py |
| Cookie consent | Scan for CookieBot, OneTrust, cookieyes, etc. | prospect_poor_websites_v2.py |
| Schema markup | Scan for `application/ld+json` | prospect_poor_websites_v2.py |
| Email capture | Scan for `<input type="email">`, Mailchimp embeds | prospect_no_pixel.py |
| Booking system | Scan for Calendly, Acuity, SimplyBook, Booksy | prospect_no_pixel.py |
| Copyright year | Regex for ©20XX or &copy; | prospect_poor_websites_v2.py |
| Free tier builder | Check URL for wixsite.com, wordpress.com, weebly.com | prospect_poor_websites_v2.py |
| Contact form exists | Already in v2 rubric | — |

### API Summary: What to Actually Get

**Immediate (free, register today):**
1. Companies House API key
2. Meta Ad Library access token
3. (PageSpeed already works with existing Google key)

**When revenue justifies it:**
4. SerpAPI ($50/mo) — adds search ranking proof

**That's it. Four APIs cover 80% of all vectors.**

---

## PART 2: OFFERS

### Offer 1: "Your New Website" — £29/mo

**For:** Businesses with no website at all.
**Trigger vectors:** 1.1

**What they get:**
- Professional single-page website (built before they even know we exist)
- Mobile responsive, fast, real photos
- Hosted on our infrastructure
- Their Google reviews displayed
- Contact form that forwards to their email/phone
- Basic local SEO (title tags, meta description, schema markup)

**What we do:**
- generate.py builds it. Netlify hosts it. SendGrid sends welcome email. Done.

**Why it works:**
- Zero effort from prospect. They see their name on a real site.
- £29/mo is impulse purchase territory. Less than a takeaway.

---

### Offer 2: "Website Upgrade" — £79/mo

**For:** Businesses with terrible existing websites.
**Trigger vectors:** 2.1-2.8

**What they get:**
- Everything in Offer 1
- Side-by-side comparison: their current site vs. our build
- PageSpeed score comparison (theirs: 23, ours: 95)
- Mobile screenshot comparison

**What we do:**
- Same as Offer 1, plus auto-generate comparison report.

**Why it works:**
- Visual proof. Can't argue with a screenshot of their broken mobile layout next to our clean one.

---

### Offer 3: "Stop Leaking Money" — £149/mo

**For:** Businesses spending on ads but missing tracking/retargeting.
**Trigger vectors:** 3.1-3.6

**What they get:**
- Everything in Offer 1 or 2
- Facebook Pixel installed and configured
- Google Analytics 4 setup
- Google Tag Manager installed
- Conversion tracking on contact form
- Monthly report: visitors, calls, form submissions

**What we do:**
- Build site with all tracking baked in from day one (add to generate.py template).
- Monthly automated report via GA4 API.

**Why it works:**
- "You spent £X on ads last month. 97% of visitors left and you have no way to reach them again. We fix that."

---

### Offer 4: "Get Found Locally" — £199/mo

**For:** Businesses invisible in local search despite having reviews/reputation.
**Trigger vectors:** 4.1-4.5, 5.1-5.5

**What they get:**
- Everything in Offer 1 or 2
- Google Business Profile optimization (photos, description, categories, hours)
- Local schema markup on website
- Review response templates (AI-generated, human-approved)
- Directory submissions (Yell, Checkatrade, Thomson Local — top 5 relevant)
- Monthly local ranking report

**What we do:**
- GBP optimization guide auto-generated per business.
- Review response drafts via Gemini.
- Directory submission is manual initially, automate later.

**Why it works:**
- "Your competitor has 3.8 stars and 200 reviews. You have 4.9 stars and 8 reviews. They show up first. We fix the gap."

---

### Offer 5: "Full Digital Presence" — £299/mo

**For:** Businesses with multiple gaps across website, tracking, SEO, reviews.
**Trigger vectors:** Compound audit showing 3+ gaps.

**What they get:**
- Everything in Offers 1-4 combined
- Complete digital audit report (the compound play)
- Priority support
- Quarterly site refresh

**What we do:**
- Run full audit pipeline across all vectors. Bundle everything.
- This is where the compound audit becomes the sales tool itself.

**Why it works:**
- The audit shows them 5-6 problems. Each one is a line item they understand. Bundled price feels like a deal vs. fixing each separately.

---

## PART 3: BRUTAL SELF-REVIEW

Now kill the stupid.

### Vectors to CUT from the list

| Vector | Why It's Stupid |
|--------|----------------|
| **4.6 Missing from Apple Maps** | Trivial signal. No business owner cares. No actionable offer. CUT. |
| **6.3 No link-in-bio** | Instagram scraping is fragile, legally grey, and the signal is weak. CUT. |
| **6.5 Good content, no funnel** | Requires subjective judgement AI can't reliably make. CUT. |
| **8.4 New housing developments** | Planning portal data is fragmented across 300+ UK councils. No standard API. Massive effort, tiny signal. CUT. |
| **8.5 Storm/weather event** | Reactive, not systematic. Hard to automate into consistent pipeline. Fun idea, bad execution. CUT. |
| **9.1 Competitor just upgraded site** | Requires tracking historical state of every site. Wayback Machine API is slow and unreliable. CUT. |
| **10.1 Revenue growing, site static** | Most local tradespeople are sole traders or micro-entities. Companies House accounts show NOTHING useful for them. No P&L. No revenue. CUT. |
| **10.3 Recently funded/got grant** | Local electricians don't get VC funding. This is startup-brain leaking into trades-world. CUT. |

### Offers That Need Honesty

| Issue | Reality |
|-------|---------|
| **Offer 4 "directory submissions"** | Submitting to Checkatrade/TrustATrader requires business owner cooperation (verification, identity). We can't do this fully autonomously. Be honest: we PREPARE the submissions, they click confirm. |
| **Offer 4 "GBP optimization"** | We can't access their GBP. We generate a guide + templates. They implement or give us access. |
| **Offer 3 "monthly report"** | Requires GA4 API access to their property. Either we own the GA4 property (better) or they grant access. Build this into onboarding. |
| **Compliance vector (7.1-7.6)** | Using fear of GDPR fines as a sales tactic might work but could also make prospects defensive. Lead with "we handle this for you" not "you're breaking the law." Reframe: compliance is included, not the pitch. |

### Pricing Honesty

| Offer | Price | Realistic? |
|-------|-------|------------|
| £29/mo | Yes | Covers hosting costs from client 3 onward. Impulse buy. |
| £79/mo | Yes | Still cheap. Easy upsell from £29 when they see comparison. |
| £149/mo | Stretch | Only worth it if we actually deliver tracking + reports. Need GA4 automation built. |
| £199/mo | Stretch | GBP + directories + reviews = significant ongoing work. Needs clear scope boundaries. |
| £299/mo | Risky | Only sell this if compound audit is genuinely automated. Otherwise we're selling manual work at scale prices. |

### Architecture Honesty

| Claim | Reality |
|-------|---------|
| "50 vectors" | After cuts: ~35. After filtering to what's actually buildable with current + 3 new APIs: ~20. Still plenty. |
| "Fully autonomous" | Prospecting and building = autonomous. Outreach still needs human approval gate. GBP/directory work needs client cooperation. Be honest about the boundary. |
| "Compound audit" | Currently would need to run 3-4 separate scripts and manually combine. Need one unified `audit.py` that runs everything and outputs single report. |

### What Actually Matters

The 80/20 of this entire system:

1. **Google Places API** — finds leads (already have)
2. **Page fetch + HTML scan** — scores them on 15+ dimensions (mostly built)
3. **Gemini via OpenRouter** — builds the demo site (already have)
4. **Netlify** — hosts the preview (have key, not wired)
5. **SendGrid** — sends the outreach (have key, not wired)
6. **Stripe** — takes the money (have key, not wired)

Everything else is enrichment. Nice to have. Not blocking revenue.

**The bottleneck is not more prospecting vectors. The bottleneck is: nothing is deployed, no outreach is being sent, and no money is coming in.**

Build the deploy + outreach + payment pipeline FIRST. Add more prospecting sophistication AFTER the first paying customer.

---

## REVISED API SHOPPING LIST

### Get Now (free, 10 minutes each)

1. **Companies House API key** — new business detection
2. **Meta Ad Library token** — confirm ad spend (enriches pixel prospector)

### Get When Revenue > £500/mo

3. **SerpAPI** ($50/mo) — search ranking proof

### Don't Bother

Everything else. The HTML we already fetch + Google Places API we already have covers 80% of useful signals.
