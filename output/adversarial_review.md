# Adversarial Review — Retarget Prospector Pipeline

**Date:** 2026-04-13
**Reviewers:** 4 parallel adversarial agents (pixel detection, ad signal, legal/compliance, business logic)
**Verdict:** ❌ **Pipeline cannot deliver user's stated goal as-is. Needs fundamental redesign before scaling.**

---

## TL;DR

The user asked for "500 top-quality leads running ads on Meta AND Google but missing pixels for either." The current pipeline:

1. Filters with **OR not AND** — 91% of the "56 qualified" leads are off-spec.
2. Already has **at least one confirmed false positive** in Tier 1A (Glasgow Smile Clinic — pixel IS installed, regex got it right, the merge script then mis-tiered it).
3. Includes **national chains** (Optical Express, Timpson, Ace & Tate, IOLLA) that are not pitchable.
4. **Cannot legally auto-send** to most of the list (sole traders → PECR breach, no Art 14 notice, no LIA).
5. **Scaling math is infeasible** — 500 dual-platform-leak leads at current ~4% yield requires processing ~12,500 candidates, ≈ saturating the discoverable Scottish local-services market.
6. The cold email pipeline will likely **suspend the sender's Gmail account** within ~100 sends due to bounce rate + scraped-list reputation hit.

---

## Critical Issues (must fix before any send)

### Detection logic

1. **Glasgow Smile Clinic merge bug** — `pixel_audit.facebook_pixel=True` but lead is in `tier1_dual_platform` (the missing-FB-pixel tier). The qualifier reads pixel state correctly but the post-merge tier-assignment script ignores the `facebook_pixel` boolean. **Every "missing-X" tier needs an explicit cross-check against the booleans, not the `missing` array.**

2. **`any_retargeting` aggregate masks per-platform leaks.** v1 and v2 both compute a single OR-aggregate, but pitches are per-platform. Composer says "you're missing your FB Pixel" using the aggregate — claim doesn't match the actual leak.

3. **Homepage-only scan is structurally wrong.** Service businesses (dentists, opticians, plumbers) put pixels on `/book`, `/quote`, `/contact` — not the homepage. Multiple agents flagged this independently.

4. **Consent-mode (UK GDPR) blocks pixel firing in headless browser.** OneTrust / Cookiebot / Iubenda / Quantcast / Didomi all gate ad pixels until consent. Headless Chromium without consent click → tags never fire → false negative. **Glasgow is in the UK, this is the worst-case region.**

5. **Server-side tagging is invisible to all detectors.** Meta CAPI, Stape, sGTM, GA4 Measurement Protocol — sophisticated shops would look "missing pixel" while having state-of-the-art tracking.

6. **Google Maps website field garbage.** Many SMB Google listings point at `facebook.com/foo`, Linktree, Yell, or a directory. The pipeline scans those for pixels — meaningless.

7. **v1 regex false positives.**
   - `r"AW-\d+"` matches blog content ("Our AW-2024 campaign…")
   - `r"google_tag_data"` matches GA boilerplate, not remarketing
   - `r"conversion.js"` matches any file named conversion.js
   - `"hotjar.com" in low` matches `<a href="blog.hotjar.com">` in testimonials
   - `"segment.com" in low` matches the word "segment" in marketing copy

8. **v2 firecrawl conflates conversion ↔ remarketing.** `googleads.g.doubleclick.net` and `google_conversion_id` are conversion-tracking signals. The actual remarketing audience collector is `google.com/ads/ga-audiences`. Current regex says "remarketing present" when only conversion tracking exists.

### Ad-verification logic

9. **`keyword_unordered` Meta search guarantees collisions.** "Access Lock Co" returned 400 ads — implausible for a 184-review solo locksmith. The query matches any active GB ad containing "access" AND "lock" in any order. Needs `search_type=keyword_exact_phrase` + advertiser-name verification.

10. **Result-count regex grabs page chrome.** `~50000 results` and `~8400 results` are Meta UI elements ("X results in this category"), not per-query counts. This is the root of the 50000/8400 garbage tier. Fix: count `[role="article"]` ad cards in the result region directly.

11. **No advertiser-identity check on matched creatives.** Meta exposes Page name per ad card; GATC exposes verified advertiser name. Neither is read. **Root cause of all chain false positives** (Optical Express, Timpson, IOLLA → matched by name but advertiser-Page isn't the local Glasgow store).

12. **GATC alt-selector counts navigation chrome.** When `creative-preview` returns zero, the fallback `[role='listitem']` matches the GATC sidebar/nav menu items. Returns inflated counts for domains with literally zero ads.

13. **Cookie banner blocks first-candidate Meta query.** `cookies_dismissed` flag set after first successful click — but the first candidate may time out before banner is even visible, returning count=0. **Every batch's first lead is at risk.**

14. **Single shared browser context leaks state.** Cached graphql, throttled responses, accepted-then-revoked cookies. After Meta or GATC starts shadow-throttling (~50–100 requests in), all subsequent results silently degrade to 0 — pipeline never knows.

15. **`active_status=active` is point-in-time.** Businesses pause/restart ads weekly. A scrape on Sunday morning misses Monday-Friday advertisers. Treat as Bernoulli sample, not ground truth.

### Compliance / legal / sender reputation

16. **Sole-trader PECR breach.** UK law treats sole traders and partnerships as individual subscribers — needs prior consent or soft opt-in. Pipeline doesn't distinguish from limited companies. **Every electrician, plumber, hairdresser in the current list is potentially a sole trader.** ICO fines up to £500k.

17. **No GDPR Art 14 notice ever sent.** When you process personal data not obtained from the data subject, you must notify them within 30 days about source, purpose, retention, rights. Pipeline has no Art 14 mechanism.

18. **No Legitimate Interest Assessment (LIA) documented.** ICO requires a written balancing test before relying on Art 6(1)(f). Sole traders almost certainly fail balancing.

19. **STOP replies are not parsed.** `cold_email.py` writes "reply STOP" in the footer but no IMAP reader detects STOP and adds to suppression. **Unsubscribes are silently dropped.** Direct PECR Reg 22 violation. The drip sequence keeps firing on opted-out recipients.

20. **Hard bounces only suppressed in-band.** SMTP recipient-refused triggers suppression, but async NDR bounces (the majority of bounces) hit the inbox and are never parsed. Next run re-mails them. Gmail spam-rate threshold breached fast.

21. **No SPF/DKIM/DMARC alignment check.** Sending as `fraser@vanity.co.uk` via `smtp.gmail.com` requires Workspace + DNS records. If not aligned, Gmail's 2024 bulk-sender rules junk every email.

22. **Predicted Gmail account suspension within ~100 sends.** Cold list + ~5–15% bounce rate + zero reply rate + no warm-up + no rotation = abuse heuristics trip fast. The user's primary inbox is at risk.

23. **No physical postal address in footer.** CAN-SPAM (US recipients) requires it. UK Companies Act requires Ltd businesses to disclose company name + number + registered office in commercial emails.

24. **Solicitors are in the current target list.** McIntosh & McCann Family & Civil Solicitors. Sending them an alarmist "you're losing leads" pitch is the maximum legal-literacy attack surface. Trivial letter-before-action could cost £2k–£10k to settle.

25. **Composer can hallucinate ad headlines.** Outreach-composer.md says "never invent ad creatives" but there's no programmatic check that the quoted headline literally appears in `_ads.json`. LLMs under instruction pressure will fabricate.

26. **WhatsApp wa.me queue functionally enables bulk cold DMs.** Skill claims "drafts only" but the tap-to-send link makes 50 cold messages a 60-second user action. Direct WhatsApp TOS violation → permanent number ban.

27. **Plain-text SMTP credentials in `config/smtp_accounts.json`.** If repo is ever pushed to a remote, GDPR Art 32 security failure + 72h breach notification.

### Business logic / claims

28. **AND vs OR semantics mismatch.** User said "Meta AND Google + missing pixel for EITHER". Pipeline filters as `(meta_leak OR gads_leak)`. **91% of the report does not match the user's stated criterion.** Only Tier 1A (5 leads) attempts the AND, and one of those is a confirmed false positive.

29. **National chains pollute Tier 1B.** Optical Express (951 reviews, 72 ads), IOLLA, Ace & Tate, Timpson — corporate HQ ads, not Glasgow-store. Pitching the local branch manager retargeting setup is nonsensical.

30. **Tier 2 (1–4 ads) is economically dead.** Meta custom audiences need ~100 unique 30-day visitors to serve. Boosted-post advertisers don't have that traffic. Retargeting math is negative — pitch promises something math can't deliver.

31. **No quality filter beyond reviews ≥5.** No revenue, ad spend, in-house team detection, agency-managed flag, domain age. "Top quality" undefined.

32. **No contact email extraction.** Output has phone numbers only. Default outbound channel is email. Without emails, "56 leads" is really "56 phone-only contacts" with ~10% the conversion rate.

33. **Pitch sells the commodity.** Pixel install is a 20-minute job. Real value is campaign management, audience architecture, creative iteration. Lead with outcome (£/mo retainer), use leak as proof point.

34. **Scaling math infeasible.** 500 strict dual-platform-leak leads at 4% yield → 12,500 candidates → saturating Scottish local services. **The user's literal goal cannot be met with current architecture.**

---

## Strategic Recommendation

The pipeline needs structural change before any production run. Two paths:

### Path A — Relax the spec (recommended, achievable in days)

Tell the user: "500 strict dual-platform leads from Scotland is mathematically infeasible. I can deliver 500 single-platform-leak leads filtered to high-quality independent businesses." Then:

1. Fix the merge-script tier bug (1 hour)
2. Switch Meta query to `keyword_exact_phrase` + advertiser-Page name verification (4 hours)
3. Multi-page pixel scan (homepage + /contact + /book + /quote) via Firecrawl with consent-mode click (4 hours)
4. Add Companies House lookup → drop sole traders (2 hours)
5. Add chain filter → drop businesses with >3 locations / national brand (2 hours)
6. Add email discovery (Hunter/Clearout API or scrape /contact + /about) (3 hours)
7. Reframe pitch from "pixel leak" to "ad management" (1 hour copy work)
8. Add IMAP STOP-reply parser + NDR bounce parser (4 hours)
9. SPF/DKIM/DMARC pre-flight check (1 hour)
10. Run wider sweep (~25 cats × 20 cities × 30 results = 15k candidates → ~1,500 qualified after filters → 500 top-tier survivable)

### Path B — Keep strict spec, pivot data source (1–2 weeks)

1. Replace ad-library scraping with **BuiltWith** or **SEMrush API** (paid but accurate at scale and gives spend estimates)
2. Filter to "Meta + Google ads with estimated monthly spend ≥ £2k AND missing pixels"
3. Accept the deliverable will be 50–150 genuinely dual-platform-leak independent Scottish businesses, not 500
4. Rebuild outreach as a high-touch, manually-approved pipeline (not auto-send)

### Do not do

- ❌ Run the current pipeline at 500-lead scale
- ❌ Auto-send any cold email until items #16, #19, #20, #21, #22, #24, #25 are fixed
- ❌ Use the current Tier 1A list for outreach without re-verification (1/5 confirmed false)
- ❌ Pitch national chains (Optical Express, Timpson, etc.) at all

---

## Next Step

Recommend going back to the user with the two paths and getting an explicit decision. The current pipeline is a **prospecting research artifact**, not a production outreach system.
