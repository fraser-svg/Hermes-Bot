# Outreach Strategy — Show Don't Tell

## Core Concept

Don't pitch. Don't promise. **Deliver first, ask second.**

Build their site before contacting them. Email arrives with live URL + screenshot. They click. They see their own business, professionally presented. That's the hook.

Most cold outreach: "We could build you a website..."
This outreach: "We built you a website. Here it is."

Conversion logic: prospect has already experienced the product before saying a word.

---

## Full Flow

```
Detect lead
     ↓
Scrape public data (name, reviews, phone, category, location, photos)
     ↓
Generate site content via Gemini (structured JSON)
     ↓
Build site from template
     ↓
Deploy to live preview URL
(e.g. preview.yourdomain.com/business-name)
     ↓
Screenshot site (full-page + mobile view)
     ↓
Generate personalised email with:
  - Screenshot embedded
  - Live URL
  - Their reviews shown on the site
  - Their actual business name, phone, location
     ↓
Queue for manual approval
     ↓
Send on approval
```

---

## Preview URL Strategy

Option A — Subdomain per lead
```
edinburgh-sparks-electrical.preview.youragency.com
```
Clean. Looks real. Easy to set up with Netlify + wildcard DNS.

Option B — Path-based
```
youragency.com/preview/edinburgh-sparks-electrical
```
Simpler. Same Netlify deploy.

Option C — Netlify deploy preview (easiest to automate)
```
https://edinburgh-sparks-electrical.netlify.app
```
Free. Instant. Each site gets unique URL. No custom domain needed for preview phase.

**Use Option C for Phase 1.** Zero config, instant deploy, free.

---

## Email Structure

Subject line options (test these):
- `[Business Name] — we built your website`
- `Your website is ready, [First Name]`
- `We made something for [Business Name]`
- `[First Name] — took us 20 minutes, took a look?`

No subject line with "free" or "offer" — triggers spam filters.

---

## Email Body (Template)

```
Hi [First Name],

We noticed [Business Name] has [X] Google reviews but no website.

So we built one.

[SCREENSHOT IMAGE — full width, linked to live URL]

→ See it live: [preview URL]

Built using your actual reviews, your phone number, and your location.
Took us about 20 minutes.

If you want to keep it live and make it yours:
£[price]/month — that's it. No setup fee. Cancel anytime.

Includes:
- Hosting
- Monthly updates
- Contact form
- Google-ready (shows up in local search)

Reply "yes" and we'll transfer it to you this week.
Reply "not interested" and we'll take it down — no hard feelings.

[Your name]
[Agency name]
```

---

## Screenshot Automation

Hermes takes screenshot via headless browser after deploy:

Tools available:
- `playwright` or `puppeteer` — full-page screenshot
- Capture: desktop (1280px) + mobile (375px)
- Save as `preview-desktop.jpg` + `preview-mobile.jpg`
- Embed desktop screenshot in email body
- Link screenshot → live URL

Mobile screenshot used as secondary image or shown as inset.

---

## What Goes on the Preview Site

Pull from public data only:
- Business name (Google)
- Category / services (Google category + reviews text mining)
- Phone number (Google listing)
- Location / area served (Google listing)
- Review count + avg rating (Google)
- 2–3 review quotes (public Google reviews)
- Google Maps embed (their pin)

Generate via Gemini:
- Hero headline ("Edinburgh's trusted electricians")
- Services section (inferred from category + reviews)
- CTA copy
- Meta description
- LocalBusiness schema

Never invent: phone, address, opening hours, pricing. Pull real or leave blank.

---

## Personalisation Levels

| Level | What's personalised | Conversion impact |
|-------|--------------------|--------------------|
| Basic | Name + phone + location | Low |
| Medium | + real reviews quoted on site | Medium |
| High | + their Google photos used, services inferred from reviews | High |
| Max | + video loom of you showing them their site | Very high |

Phase 1: aim for Medium minimum. High where data available.

**Loom video** (optional manual add): 60-second screen recording walking through their site. Massively increases reply rate. Reserve for highest-scored leads.

---

## Follow-Up Sequence

Day 0 — Send email with site
Day 3 — "Just checking you saw this" (2 lines, reattach screenshot)
Day 7 — "Taking the site down Friday unless I hear from you"

3 touches max. Then mark as no-response, log, move on.

Scarcity on day 7 is real — actually take it down if no response. Keeps you honest, creates genuine urgency.

---

## Rejection Handling

Common responses:

**"Not interested"**
→ Log objection. Ask why (one reply). Thank them. Remove preview.

**"How much?"**
→ Already in email. Resend pricing section. Ask if they want to proceed.

**"Can you add X?"**
→ Yes — log as upsell signal. Add to brief. Rebuild + resend.

**"I already have a website"**
→ Check it. If it's bad: "We know — we looked. Here's what we built instead."
If it's decent: log, mark disqualified, move on.

**No response**
→ Follow-up sequence above. After day 7: mark cold, archive lead.

---

## Hermes Instruction (Paste to Update Outreach Agent)

```
Outreach strategy update:

Before any outreach:
1. Build preview site for each qualified lead
2. Deploy to Netlify (get live URL)
3. Take full-page screenshot (desktop + mobile)
4. Generate personalised email using template in OUTREACH_STRATEGY.md
5. Embed screenshot in email body, linked to live URL
6. Queue for manual approval — do not send automatically

Email subject: "[Business Name] — we built your website"

Follow-up sequence:
- Day 3: short follow-up
- Day 7: scarcity close ("taking it down Friday")
- After day 7: mark cold, archive

Log all outcomes in outreach_log with:
- Lead name
- Preview URL
- Email sent date
- Response type
- Follow-up dates
- Final status
```

---

## Phase 1 Metrics to Track

- Build rate (sites built per hour)
- Email open rate (use tracking pixel or SendGrid open events)
- Reply rate (total replies / sent)
- Positive reply rate (interested / sent)
- Conversion rate (paying / sent)
- Avg days to convert

Target Phase 1 benchmark:
- Reply rate: 15–30% (personalised outreach with live site is high)
- Conversion: 1 in 20 minimum to validate model

---

*Strategy: show first, ask second. Build before pitching. Let the product do the selling.*
