---
name: retarget-pitch-patterns
description: Cold outreach templates for offering retargeting setup + ad-management to UK businesses with confirmed paid ad spend. Use whenever composing email, WhatsApp, or LinkedIn DM pitches for a retargeting offer. Covers UK PECR/GDPR-compliant tone, soft observational framing, outcome-led CTAs, and the per-leak pitch angles. Always reference observed ad evidence (verified, not invented) and never disparage incumbent suppliers.
---

# Retarget Pitch Patterns

The pitch sells **ad management as a retainer** (£1.5–5k/mo recurring), not pixel install (a £200 commodity). Lead with outcome, use the missing pixel as **proof of opportunity**, never as the offer.

## Universal Rules

- **Subject ≤ 50 chars.** Curiosity + specificity, no alarmism. No "leaks", "losing leads", "broken", "fix".
- **Observational framing only.** "Noticed something" beats "you're broken".
- **Quote ad evidence verbatim or not at all.** Composer hallucination guard rejects un-grounded quotes.
- **Never disparage incumbents.** No "your current setup is flying blind". Defamation/trade-libel risk.
- **One CTA.** Either "5-min reply audit" OR "15-min call". Never both.
- **No links in first email.** Triggers spam filters AND PECR scrutiny.
- **No statistics without source.** Drop "97% of visitors leave" entirely or cite Baymard inline.
- **No fake urgency.** No "limited spots", "acting fast", "before competitors".
- **Reframe value.** Pixel install = 30 min. Audience architecture + creative iteration + spend optimization = ongoing work.

## PECR Compliance (UK)

- **Limited companies / LLPs / PLCs only.** Sole traders are individual subscribers under PECR — composer must reject `entity_type != "ltd"`.
- **Footer must include:** sender legal name + company number + registered office + clear opt-out + Art 14 source notice. See `references/footer_template.md`.
- **Honor STOP immediately.** No drip after any STOP/UNSUBSCRIBE/REMOVE reply or any reply at all to step 1.

## Templates by Pitch Angle

### `fb_pixel_leak` (Meta ads + no FB Pixel)

**Subject:** `{first_word} ad — quick observation`

**Body:**
```
Hi {first_name},

Saw your "{ad_headline}" ad in {city} — caught my eye because the
landing page doesn't have a Facebook Pixel installed yet.

Without it, the audience you're paying to reach is one-and-done —
no warm-audience retargeting, no lookalikes, and Meta's optimizer
can't learn from real conversions on your site.

I help UK service businesses turn existing Meta ad spend into 2–3x
ROAS by setting up the pixel, building proper audience layers, and
running creative iteration that compounds. Most clients see the
shift within the first 30 days of data maturity.

Worth a 15-min call to look at your setup? Reply "audit" and I'll
send a short loom with three things I'd change.

{sender_first_name}
```

### `gads_remarketing_leak` (Google Ads + no remarketing tag)

**Subject:** `Quick observation on {business_name}'s Google Ads`

**Body:**
```
Hi {first_name},

Noticed {business_name} is running Google Ads but the site doesn't
have the Google Ads remarketing tag set up. Means the audience you're
paying for can't be re-reached on Display, YouTube, or search
remarketing campaigns.

I help UK service businesses turn one-shot Google Ads spend into a
warm-audience funnel — usually 25–40% of new conversions come from
remarketing once it's wired up properly.

Open to a quick chat about your current setup? Reply "tag" and I'll
send a short loom showing what's missing and what I'd build.

{sender_first_name}
```

### `linkedin_insight_leak` (LinkedIn Ads + no Insight Tag)

**Subject:** `LinkedIn Ads observation for {business_name}`

**Body:**
```
Hi {first_name},

Saw {business_name} is running LinkedIn ads but the website doesn't
have the LinkedIn Insight Tag installed. For B2B that breaks the
matched-audience and conversion-tracking parts of the campaign —
you can't see which companies visit, can't build account-based
audiences, can't run conversion campaigns properly.

Happy to send a 5-min loom on what to add and how I'd structure
matched audiences for your stack. Reply "insight" if useful.

{sender_first_name}
```

### `multi_platform_leak` (Both Meta and Google leaks)

**Subject:** `Quick note on {business_name}'s ad setup`

Open with the most recognizable verified ad creative. List the two opportunities in plain prose (not bullets). Single CTA. Same outcome framing.

## WhatsApp Format (DRAFT ONLY — never auto-send)

≤160 chars, no links, no formatting:

```
Hi {first_name} — Fraser here, noticed {business_name}'s
{ad_platform} ads. Their landing page is missing the
{pixel_name} setup which limits retargeting. Worth a quick chat?
```

## LinkedIn DM (DRAFT ONLY — manual send via Sales Nav)

≤300 chars:

```
{first_name} — saw {business_name} is running {ad_platform} ads.
Noticed the site doesn't have the {pixel_name} installed yet,
which limits warm-audience retargeting. Happy to send a 5-min
loom on what to add. Worth 15 min?
```

## Anti-patterns (never do)

- ❌ "Hope this finds you well" — instant delete
- ❌ "Your competitors are doing this" — fake urgency
- ❌ Quoting a stat without a source
- ❌ Quoting an ad headline that wasn't verified in `_ads.json`
- ❌ Calling the recipient's setup "broken", "leaking", "flying blind"
- ❌ Promising specific lift numbers ("3x your conversions in 30 days")
- ❌ Mentioning their existing agency by name
- ❌ Attaching PDFs / case studies in cold outreach

## More

Concrete proven samples: `references/example_emails.md`
Footer template (PECR/Companies Act compliant): `references/footer_template.md`
