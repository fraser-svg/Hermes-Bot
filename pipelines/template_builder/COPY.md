# Hermes Master Copy Framework

> Single copy direction for every local-service site Hermes builds. Companion to `DESIGN.md` — together they form the master brief injected into `prompts/website_builder.md` on every `generate.py` run. Authored by `conversion-copywriter`. Schema: 10 sections, slot-keyed to `references/business_details.json`.

**Status:** Research-integrated (2026-04-13). Calibrated against `DESIGN.md` Cold Engineering Neutral theme. Research source: `_workspace/template/01_research.md` §3 trust signals + §6 copywriter questions. Decision log: `_workspace/template/03_copy_decisions.md`.

---

## 1. Voice & Tone

Hermes copy sounds like an **engineering firm**, not an advertising brochure. Specific beats clever. Numbers beat adjectives. Place names beat "local area." Direct verbs beat passive voice.

The visual system (`DESIGN.md §1`) does the heavy lifting on "looks premium." Copy's job is to sound **precise** — the kind of precision that signals competence to a homeowner who just found a burst pipe at 10pm. No swagger, no apology, no filler.

**Two voice modes, persona-locked to the surface token** (`DESIGN.md §1` `[data-persona]`):

### Cold voice — trades/emergency/tech verticals
Used with `<html data-persona="cold">`. Electrician, plumber, HVAC, roofer, cleaner, locksmith, pest control, IT, emergency.

- **Cadence:** Short declarative sentences. Often fragments. Period-heavy.
- **Verbs:** arrive, fix, diagnose, replace, test, certify, fit, rewire.
- **Proof verbs:** certified, registered, tested, insured, documented.
- **Example:** "Edinburgh's NICEIC-registered electrician. Fault diagnosed and repaired in 90 minutes, or the callout is free."
- **Never:** reassuring adjectives ("friendly," "caring," "trusted"), emotional appeals, exclamation marks.

### Warm voice — professional/personal verticals
Used with `<html data-persona="warm">`. Solicitor, accountant, dentist, vet, photographer, personal trainer, therapist.

- **Cadence:** Full sentences. Measured. One pause per idea.
- **Verbs:** advise, review, plan, assess, support, document, represent.
- **Proof verbs:** qualified, regulated, insured, accredited, published.
- **Example:** "Independent legal advice for Fife families since 2009. Fixed-fee consultations, SRA-regulated, no obligation."
- **Never:** urgency language ("act now," "don't wait"), corporate jargon ("solutions," "leverage"), first-person plural as a crutch ("we pride ourselves").

**Shared rules (both voices):**

- Every sentence earns its place. If it survives deletion, keep it. Otherwise cut.
- **Second person beats third.** "You get a fixed price before we start." not "Customers receive transparent pricing."
- **Specific geographies.** "EH3 postcodes" not "local area." "Dunfermline and West Fife" not "Fife."
- **Specific timeframes.** "90 minutes" not "fast." "Same week" not "promptly." "Tuesday and Thursday slots" not "flexible scheduling."
- **Specific numbers.** "173 Google reviews" not "loved by our customers." "12 years" not "established."
- **No throat-clearing intros.** "Welcome to…" is banned. "Looking for a…" is banned. Start with the problem or the proof.
- **No compound adjective stacks.** "Reliable, trustworthy, professional service" is slop. Pick one proof and demonstrate it.
- **Contractions allowed.** "We'll" / "you'll" / "won't" — matches how a human tradesman actually speaks.

---

## 2. Headline Formulas (Hero)

Every hero headline follows **Problem → Outcome → Proof.** The h1 carries the outcome-promise; the subheadline (§3) delivers the proof; the CTA (§4) closes the action. Max 14 words in h1 (fits the `DESIGN.md §3` h1 `max-width: 14ch` at display sizes).

Three variants per category so the builder can rotate and A/B.

### Trades category
**Verticals:** electrician, plumber, roofer, HVAC, gas engineer, locksmith, pest, cleaner, painter, landscaper, handyman.

#### Formula T-1 — Geo + proof + urgency
```
{{business.city}}'s {proof_marker} {{business.category}}.
{outcome_promise} in {timeframe}, or {guarantee}.
```
**Fill:**
> Edinburgh's NICEIC-registered electrician.
> Fault diagnosed and repaired in 90 minutes, or the callout is free.

#### Formula T-2 — Outcome-first
```
{outcome_in_plain_language}.
{proof_marker} {{business.category}} serving {{business.city}} and {service_radius}.
```
**Fill:**
> Power back on before the kids get home.
> Fully insured electrician serving Edinburgh and EH postcodes, 173 five-star reviews.

#### Formula T-3 — Problem-named
```
{specific_problem} in {{business.city}}? {first_action_verb}.
{{business.rating}}★ from {{business.review_count}} reviews. {licence_or_guarantee}.
```
**Fill:**
> Fuse board tripping in Edinburgh? Call us before it trips again.
> 5★ from 173 reviews. NICEIC Approved Contractor.

### Professional services category
**Verticals:** solicitor, accountant, IFA, mortgage broker, architect, surveyor, notary, tax advisor, bookkeeper.

#### Formula P-1 — Credentials + audience + since
```
{credential} {{business.category}} for {target_audience}.
Serving {{business.city}} since {{business.years}}.
```
**Fill:**
> SRA-regulated family solicitor for Fife homeowners.
> Serving Edinburgh since 2009.

#### Formula P-2 — Outcome + proof + scope
```
{outcome_in_client_language}. {credential_marker} {{business.category}}, {{business.city}}.
{specific_proof_number} {reviews_or_clients}.
```
**Fill:**
> Keep more of your profit, legally. ICAEW-chartered accountant, Edinburgh.
> 173 owner-managed businesses, 5★ reviewed.

#### Formula P-3 — Category-specific problem
```
{specific_pain_point}? {direct_outcome}.
{{business.city}} {{business.category}}, {trust_marker}, {availability_marker}.
```
**Fill:**
> Self-assessment deadline tomorrow? Filed and paid today.
> Edinburgh accountant, ICAEW-chartered, same-day appointments this week.

### Personal services category
**Verticals:** dentist, vet, GP, physio, chiropractor, optician, personal trainer, therapist, tutor, photographer.

#### Formula S-1 — Emotional outcome + practical proof
```
{emotional_outcome_in_patient_language}.
{practical_credential} {{business.category}} in {{business.city}}, {availability_marker}.
```
**Fill:**
> Walk out smiling, not wincing.
> GDC-registered dentist in Edinburgh, same-week appointments for new patients.

#### Formula S-2 — Credential + target audience + reassurance
```
{credential} {{business.category}} for {specific_audience}.
{{business.rating}}★ from {{business.review_count}} {{business.city}} families.
```
**Fill:**
> RCVS-registered vet for anxious dogs and nervous owners.
> 5★ from 173 Edinburgh families.

#### Formula S-3 — Outcome in client language
```
{first_person_plain_outcome}.
{{business.category}} in {{business.city}}, {since_or_count_proof}.
```
**Fill:**
> Run your first 5k without your knees protesting.
> Personal trainer in Edinburgh, 173 clients trained since 2013.

**Headline banned patterns:**
- "Welcome to {{business.name}}" — zero information density.
- "Your trusted {{business.category}}" — unsupported trust claim.
- "Quality {{business.category}} services" — category + filler word.
- "Looking for a {{business.category}}?" — question the visitor already answered.
- Any headline >14 words or >2 lines on desktop.

---

## 3. Subheadline Patterns

The subheadline is the **proof layer** under the headline-outcome. Always second-person. Always specific. Uses the `Lead` type role (`DESIGN.md §3` — 18px/400, 650px max).

### Pattern S-A — Proof triple
```
{credential} · {geographic_scope} · {availability_or_guarantee}.
```
**Fill:** `NICEIC Approved · Edinburgh and EH postcodes · Emergency callouts 7 days.`

### Pattern S-B — What you get
```
You get {concrete_deliverable_1}, {concrete_deliverable_2}, and {guarantee_or_proof}.
```
**Fill:** `You get a fixed quote before we start, a fully certified install, and a six-year workmanship guarantee.`

### Pattern S-C — Numbers line
```
{{business.review_count}} {{business.rating}}★ reviews. {years_marker}. {credential_marker}.
```
**Fill:** `173 five-star reviews. Trading in Edinburgh since 2013. NICEIC Approved Contractor.`

### Pattern S-D — Scope + exclusion
```
{what_we_do}. {what_we_dont_do}. {how_you_book}.
```
**Fill:** `Domestic electrical work across Edinburgh. No commercial contracts, no subcontractors. Book by phone or text.`

**Subheadline rules:**
- 25 words max. Count them.
- One idea per sentence. Full stops are free.
- No "we pride ourselves" / "we specialise in" / "we are passionate about."
- Numbers in digits (`173`, not `one hundred and seventy-three`).

---

## 4. CTA Vocabulary

Primary CTA is **near-black `#0A0F1A` solid** (`DESIGN.md §2` — warm near-black, NOT blue). The vertical override `#2563EB` ships only when JSON sets `accent_color`. Copy stays the same in either case.

### Default primary CTA
```
Call {{business.phone}}
```
The phone number IS the CTA label. Research §3 trust signals — click-to-call is the #1 conversion action for local service. Use `tel:` link. Mono-phone type role (`DESIGN.md §3`).

### Primary CTA alternatives (pick ONE per page)

| Label | When to use | Category fit |
|-------|-------------|--------------|
| `Call {{business.phone}}` | Default. Always works. | All |
| `Get quote` | When phone isn't primary channel | Trades, professional |
| `Book visit` | When business uses online booking | Personal services, dentist, vet |
| `Check availability` | When scheduling is constrained | Personal services, photographer |
| `See pricing` | When business publishes rates | Accountant, solicitor (fixed-fee) |
| `Free consult` | When first meeting is free + legal/medical | Solicitor, IFA, therapist |
| `Request callback` | When phone staffing is part-time | Sole trader, evening-only |

### Urgent CTA (emergency verticals only)
```
Emergency? Call {{business.phone}}
```
Uses `--signal-urgent` `#B91C1C` background (`DESIGN.md §4` `.btn-urgent`). **Only** for 24/7 emergency services. Never decorative.

### Secondary CTA
```
See services  →
See reviews  →
```
Ghost style — `DESIGN.md §4` `.btn-secondary`. Right-arrow affordance. Sentence case. Never "Learn more."

### CTA banned vocabulary

| Banned | Why | Use instead |
|--------|-----|-------------|
| "Get started" | No outcome named, ambiguous | `Call {{business.phone}}` or `Get quote` |
| "Learn more" | No commitment, no outcome | `See services` or `See pricing` |
| "Contact us" | No channel specified | `Call {{business.phone}}` |
| "Click here" | Not copy, describes mechanism | Action verb tied to outcome |
| "Submit" | Form-survivor, cold | `Send request` or `Request callback` |
| "Read more" | Lazy, no promise | `See {specific_thing}` |
| "Sign up" | SaaS language, wrong signal | `Book visit` or `Request callback` |
| "Discover" | Marketing-speak | `See` or direct verb |
| "Enquire" | Distanced, passive | `Get quote` or `Call {{business.phone}}` |

### CTA rules
- **Sentence case.** Never ALL CAPS, never Title Case. (`DESIGN.md §4` button spec.)
- **2 words max** for non-phone CTAs. (Research §3 CTA observations — Stripe/Vercel/Cal.com/Notion/Linear all 2-word.)
- **One primary CTA per screen.** Repeat the same label in hero, nav, and footer. Never vary.
- **Tel-link mandatory** on any `Call` CTA: `<a href="tel:+44...">Call 0131 202 2711</a>`.
- **Never two CTAs at equal weight.** Primary is solid dark, secondary is ghost. No "two big buttons side by side."

---

## 5. Trust Block Patterns

Trust is **proof density**. The visual system gives you the cards; copy fills them with specifics. Research §3 trust signals inventory drives this module.

### Trust ribbon (hero-adjacent, 1 line)
**Formula:**
```
{{business.review_count}} reviews · {{business.rating}}★ · {{business.years}} · {credential}
```
**Fill:**
> 173 reviews · 5★ · Trading since 2013 · NICEIC Approved

**Rules:**
- Separator is `·` (middle dot, U+00B7). Never `|`, never em-dash, never `/`.
- 4 items max. 3 is fine. 2 is fine. Never 5+.
- On mobile, wrap to 2 lines — never shrink below 14px.
- Every item must be a number, a name, or a credential. No adjectives.
- Drop the years item if `years_experience` absent. Drop the credential item if `license_number` absent. Never invent.

### Metric cluster row (4-col trust block)
Research §3 metric cluster pattern — one stat per card, 4 cards across. Uses `DESIGN.md §4` Trust card component.

**Card template:**
```
{big_number}
{short_label_4_words_max}
```

**Category fills:**

| Vertical | Card 1 | Card 2 | Card 3 | Card 4 |
|----------|--------|--------|--------|--------|
| Electrician | `173` five-star reviews | `90min` average response | `12yrs` trading in Edinburgh | `NICEIC` approved contractor |
| Plumber | `173` five-star reviews | `60min` emergency response | `Fixed` price before we start | `Gas Safe` registered |
| Dentist | `173` patient reviews | `Same week` appointments | `12yrs` in practice | `GDC` registered |
| Solicitor | `173` client reviews | `Fixed fee` initial consult | `Since 2009` in Fife | `SRA` regulated |
| Accountant | `173` five-star reviews | `48hr` turnaround | `Since 2013` | `ICAEW` chartered |

**Rules:**
- Big number uses `tabular-nums` (`DESIGN.md §3`). 48px weight 600 `--ink-strong`. **Never** accent color.
- Never 5 cards, never 3 cards on desktop. 4 is the pattern. Tablet collapses 4→2 per `DESIGN.md §8`.
- Numbers must be real. If `review_count < 20`, drop the reviews card and use a different proof. Never inflate.

### Accreditation badge row
When `business.license_number` or vertical implies accreditations, show 4–6 **grayscale** logos in a ring-shadow bar. Research §3 logo trust bar pattern.

**Approved accreditation whitelist per vertical** (never show a badge the business can't prove):

| Vertical | Allowed badges |
|----------|----------------|
| Electrician | NICEIC, NAPIT, ELECSA, Part P, TrustMark, Checkatrade, Which? Trusted Trader |
| Plumber / Gas | Gas Safe, WRAS, CIPHE, TrustMark, Checkatrade |
| Roofer | NFRC, CompetentRoofer, TrustMark, Checkatrade |
| HVAC | REFCOM, F-Gas, Gas Safe, TrustMark |
| Locksmith | MLA, DBS checked, TrustMark |
| Dentist | GDC, CQC, BDA |
| Vet | RCVS, BVA |
| GP / medical | GMC, CQC |
| Solicitor | SRA, Law Society, Legal 500 |
| Accountant | ICAEW, ACCA, CIOT, AAT |
| IFA | FCA, CII, CISI |
| Surveyor | RICS |
| Architect | ARB, RIBA |

**Eyebrow label over the row:**
> FULLY ACCREDITED

Use mono-eyebrow type role (`DESIGN.md §3`, `.eyebrow-mono` utility).

### Review quotation card
Research §3 review quotation pattern. Real reviews from `business.reviews[]` — never fabricate.

**Card template:**
```
"{quote_30_words_max}."
— {reviewer_first_name}, {neighborhood_or_town}
```

**Fill from Izabela's Spartan review:**
> "Carlos arrived on time, installation was prompt, and my kitchen was left spotless. Even cleaned my gas hob — an unexpected, much-appreciated extra."
> — Izabela, Edinburgh

**Truncation rule:**
- 30 words max. Cut from the **end** of a sentence, never mid-sentence.
- Use `[…]` only if removing material from the **middle** to preserve meaning.
- **Paraphrasing is forbidden** — compliance risk. Truncate only. If no 30-word excerpt works, use a different review.
- Star row is **filled `--ink-strong` stars or no stars**. Never gold, never accent blue (`DESIGN.md §4` testimonial card spec).
- Attribution: first name + geographic marker (neighborhood > town > city). Never "John D." (corporate-feel). Never full surname (privacy).

### Trust block copy — priority order
When space is tight, drop from the bottom up:
1. Phone primary (never dropped)
2. Rating + review count
3. Licence / accreditation
4. Service radius
5. Years in business
6. Review quotation card

---

## 6. Service Block Copy

Uses `DESIGN.md §4` Service card — uniform grid, 3-col desktop → 2-col tablet → 1-col mobile. Every card identical height.

### Service card template
```
{service_name_max_4_words}
{outcome_in_15_words_max}
See service →
```

**Rules:**
- Title is `h4` (`DESIGN.md §3` — 16px/600). Max 4 words. Sentence case.
- Description is `0.9375rem` / `--ink-muted`. **15 words max.** Count them.
- No bullet lists inside cards. If a service needs bullets, it's a full section, not a card.
- Optional `→` affordance, never a button inside a card.
- Icon (if used) is monoline Heroicon/Lucide at 20px `--ink-strong`. Never in an accent-tinted circle.

### Service description formula
```
{outcome_verb} {deliverable}. {specific_qualifier_or_proof}.
```

**Fills for Spartan Electrical `services_offered`:**

| Service | Card title | Description (15 words max) |
|---------|-----------|----------------------------|
| Domestic electrical installations | Installations | New circuits, sockets, and fused spurs. Certified and tested to 18th Edition. |
| Rewiring and upgrades | Rewires | Full and partial rewires for Edinburgh homes. Fixed price before we start. |
| Fuse board replacements | Fuse boards | Modern consumer units fitted same day. RCD protection on every circuit. |
| Lighting design and installation | Lighting | Ceiling, wall, and garden lighting. Designed once, rewired never. |
| Electrical inspections and testing | EICR testing | Electrical Installation Condition Reports for landlords, buyers, and selling surveys. |
| Emergency call-outs | Emergencies | Fault-finding and repairs, Edinburgh and EH postcodes. Response within 90 minutes. |
| EV charger installation | EV chargers | 7kW and 22kW home chargers. OZEV-approved, wired direct to your consumer unit. |
| Smart home systems | Smart systems | Hive, Nest, and smart lighting configured and wired. No apps left abandoned. |

### Service section eyebrow
```
SERVICES
```
Mono eyebrow, single word, above the section h2. Research §3 + `DESIGN.md §3` mono eyebrow row.

### Service section h2 formulas
```
What we fix in {{business.city}}.
```
or
```
{{business.category}} work, done once.
```
or
```
Every job, certified and signed off.
```

Pick one. No eyebrow-copy + headline-copy saying the same thing.

---

## 7. FAQ Templates

FAQs are **objection handlers**, not filler. Six questions max. Every question is a real thing a homeowner Googles at 9pm. Uses two-column layout or single accordion (template-engineer decides).

### Universal questions (always ask)

1. **"How much does a {{business.category}} cost in {{business.city}}?"**
   Answer pattern: give a real price range, name what's included, name what isn't. 40 words max.

2. **"Are you insured and {credential_for_vertical}?"**
   Answer: "Yes. [Proof noun + number]. Certificate available on request." 25 words max.

3. **"How quickly can you get to {{business.city}}?"**
   Answer: geographic radius + response time + booking channel. 30 words max.

4. **"Do you give fixed prices or estimates?"**
   Answer: state the pricing model. Never both. 25 words max.

### Trades-specific questions

5. **"What happens if something goes wrong after you've left?"**
   Answer: workmanship guarantee period + what it covers + how to claim. 40 words max.

6. **"Do I need to be home during the work?"**
   Answer: yes/no + why + what you need to prepare. 30 words max.

### Professional/medical questions

5. **"Is the first consultation free?"**
   Answer: yes/no + duration + what's covered. 25 words max.

6. **"How do I know you're regulated?"**
   Answer: regulator name + membership number + how to verify. 30 words max.

### FAQ banned answer patterns
- "It depends." — always give the range.
- "Contact us for a quote." — answer first, CTA second.
- "We pride ourselves on…" — delete on sight.
- Any answer >50 words.
- Questions without a question mark.

### FAQ copy rules
- Questions in **second person** ("How much does it cost?") not third ("How much do your services cost?").
- Answers start with a **direct statement**, not a restatement of the question.
- End every answer with a specific fact or next action, not filler.

---

## 8. Microcopy

### Form labels and helpers

| Element | Copy |
|---------|------|
| Name label | `Your name` |
| Email label | `Email` |
| Phone label | `Phone` |
| Message label | `What do you need?` |
| Placeholder (message) | `e.g. Fuse board keeps tripping in the kitchen` |
| Submit button | `Send request` |
| Privacy microcopy | `We only use your details to reply to this request.` |
| Error — missing field | `We need this to get back to you.` |
| Error — bad email | `This email address looks off — check it?` |
| Success message | `Got it. We'll reply within {{response_window}}.` |

### Badge labels (sentence case, never shouty)

| Context | Copy |
|---------|------|
| Verified credential | `Gas Safe registered` / `NICEIC approved` / `SRA regulated` |
| Insurance | `£5m public liability` (real number only) |
| Response guarantee | `90-minute callout` |
| Trading record | `Trading since 2013` |

Uses `DESIGN.md §4` `.badge-trust` for neutral, `.badge-signal-success` for verified.

### Footer copy block

```
{{business.name}}
{{business.address}}
{{business.phone}}  ·  {{business.email}}

Edinburgh-based. {{business.category}} work across {service_radius}.
{{business.license}} · {trading_since}

© {year} {{business.name}}. All rights reserved.
```

**Rules:**
- Phone as `tel:` link, monospace (`DESIGN.md §3` mono-phone role).
- No "Powered by…" / "Designed by…" / "Crafted with ♥" — all banned.
- Address is plain text, not a button.
- No social icons unless the business actively posts (ghost accounts kill trust).

### Uppercase-mono eyebrow label bank

Research §6 Q1 — 15 entry bank. Use sparingly. One eyebrow per section, never above the hero h1 (`DESIGN.md §7`).

| Label | Use for section |
|-------|-----------------|
| `SERVICES` | Service grid |
| `REVIEWS` | Testimonial row |
| `SERVICE AREAS` | Geographic scope |
| `TRUSTED LOCALLY` | Trust ribbon / logo row |
| `FULLY ACCREDITED` | Badge row |
| `VERIFIED REVIEWS` | Review section when Google reviews |
| `HOW WE WORK` | Process steps section |
| `WHAT YOU GET` | Deliverables block |
| `PRICING` | Fixed-fee table |
| `FAQ` | Question block |
| `GET IN TOUCH` | Contact block |
| `ON CALL` | Emergency-only eyebrow |
| `CERTIFIED` | Credential row |
| `SINCE 2013` | Years-trading marker (only if real) |
| `{{business.city}} BASED` | Geo marker |

All 12px JetBrains Mono, `0.08em` tracked, `--ink-muted`, uppercase (`DESIGN.md §3` mono eyebrow row).

### Nav microcopy

| Element | Copy |
|---------|------|
| Logo wordmark | `{{business.name}}` |
| Nav link 1 | `Services` |
| Nav link 2 | `Reviews` |
| Nav link 3 | `Areas` |
| Nav link 4 | `Contact` |
| Nav tel-icon aria-label | `Call {{business.phone}}` |
| Nav primary CTA | `Call {{business.phone}}` (compact) |

---

## 9. Banned Vocabulary

**Full ban — never use these words.** Auto-strip in post-generate validation.

```
revolutionizing, unleash, seamless, robust, cutting-edge, solutions,
empowering, synergy, best-in-class, world-class, leverage, holistic,
premier, next-level, state-of-the-art, bespoke, tailored, game-changing,
unparalleled, unmatched, passionate, dedicated, committed, driven,
ecosystem, paradigm, journey, craft, crafted, elevate, reimagine,
transforming, innovative, innovation, disrupt
```

**Context ban — allowed only with concrete support.**

| Word | Only allowed if |
|------|-----------------|
| `quality` | Paired with a measurable ("18th Edition certified") — otherwise delete |
| `professional` | Paired with a credential ("SRA-regulated professional") — otherwise implied, delete |
| `trusted` | Paired with a number ("173 five-star reviews") — otherwise unsupported, delete |
| `reliable` | Paired with a guarantee ("60-minute response or free") — otherwise filler |
| `experienced` | Paired with a year count ("12 years in Edinburgh") — otherwise delete |
| `friendly` | Never in hero or h2. Only allowed in a review quotation. |
| `local` | Must be paired with a place name ("local to EH3 and EH4") |
| `affordable` | Must be paired with a real price ("from £85") |

**Phrase ban — the AI-slop sentence patterns.**

- "Welcome to {{business.name}}"
- "At {{business.name}}, we pride ourselves on…"
- "Your one-stop shop for…"
- "We specialise in…" (implied — show, don't declare)
- "Looking for a {{business.category}}?"
- "Look no further."
- "Get in touch today!"
- "Don't hesitate to contact us."
- "We go the extra mile."
- "Customer satisfaction is our top priority."
- "With years of experience…" (how many? name it)
- "Our team of experts…" (how many? which experts?)
- "We offer a wide range of services"
- "Feel free to…"
- Exclamation marks in body copy. (Allowed only in a review quotation.)
- Em-dashes as a stylistic tic. One per section max.

**Why the bans matter.** Research §3 CTA observations — every exemplar (Stripe, Linear, Vercel, Mintlify, Notion, Cal.com) uses verb-led specific copy. The banned list is the direct inverse of what wins. If the generator produces any banned word, `template-critic` blocks the build.

---

## 10. Slot Map

Every `{{business.*}}` placeholder in this file maps to exactly one `references/business_details.json` field. No invented slots.

| Placeholder | Source JSON field | Required? | Fallback if missing |
|-------------|-------------------|-----------|---------------------|
| `{{business.name}}` | `business_name` | required | — |
| `{{business.category}}` | `business_category` | required | — |
| `{{business.city}}` | `city` | required | — |
| `{{business.address}}` | `address` | optional | Omit footer address line |
| `{{business.phone}}` | `phone_number` | required | — |
| `{{business.email}}` | `email` | optional | Omit from footer; use phone only |
| `{{business.services[]}}` | `services_offered[]` | required (≥3) | Block build |
| `{{business.reviews[]}}` | `google_reviews[]` | required (≥1) | Block testimonial section; keep trust ribbon |
| `{{business.rating}}` | `rating` | required | Block trust ribbon; use reviews card only |
| `{{business.review_count}}` | `review_count` | required | Block trust ribbon rating item |
| `{{business.years}}` | `years_experience` | optional | Drop "years trading" card; drop S-C numbers line years item; drop "Since {year}" eyebrow |
| `{{business.license}}` | `license_number` | optional | Drop accreditation badge; drop credential subhead item |
| `{{business.maps_url}}` | `google_maps_url` | optional | Omit "see on map" link |

### Derived slots (computed by template-engineer, not JSON fields)

| Placeholder | Computed from | Rule |
|-------------|---------------|------|
| `{{service_radius}}` | `city` + vertical defaults | e.g. "Edinburgh and EH postcodes" — template-engineer maintains a city→postcode map |
| `{{response_window}}` | vertical default | Trades 90min, professional same day, personal services same week |
| `{{trading_since}}` | `years_experience` minus current year | Only rendered if `years_experience` present |
| `{{year}}` | current year | Footer copyright |
| `{{credential_marker}}` | `business_category` + `license_number` presence | Pulls from vertical whitelist (§5 accreditation whitelist) |

### Slot rules

- **Never invent a slot that doesn't map to a JSON field or a computed derivation.** If a headline formula needs a field that doesn't exist, the formula is wrong — rewrite it.
- **Never interpolate a missing optional slot.** Use the fallback. Better to drop a whole section than to render `"Serving Edinburgh since ."`.
- **Reviews are quoted, never paraphrased.** The `{{business.reviews[].text}}` field passes through truncation logic in §5, never rewording.
- **Phone is always `tel:`** — the slot renders both a display string (`0131 202 2711`) and a sanitized href (`tel:+441312022711`).

### Validation checklist (run before deploy)

- [ ] Every `{{business.*}}` in the rendered HTML resolves to a real value (no empty interpolations).
- [ ] No banned vocabulary present (§9 full-ban list — auto-strip).
- [ ] Every CTA is ≤2 words OR starts with `Call`.
- [ ] Every review is ≤30 words and matches the source `google_reviews[].text`.
- [ ] Hero h1 is ≤14 words.
- [ ] Every subheadline is ≤25 words.
- [ ] Every service description is ≤15 words.
- [ ] No exclamation marks outside review quotations.

---

*Calibrated against `DESIGN.md` Cold Engineering Neutral (2026-04-13). Research source: `_workspace/template/01_research.md`. Decision log: `_workspace/template/03_copy_decisions.md`.*
