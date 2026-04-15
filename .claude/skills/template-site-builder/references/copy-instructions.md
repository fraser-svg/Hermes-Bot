# Copy Instructions — Authoring the 21 Copy Slots

Read this file end-to-end every time you fill a template. All word counts are
hard maxima — count them. The point is **proof density**, not prose.

## Voice (persona)

`core/fill_template.py` sets `<html data-persona="cold|warm">` per vertical.

- **Cold (trades, IT, mechanic, printing):** short fragments. Verbs lead:
  "fix," "diagnose," "repair," "install," "fit," "test," "certify." No adjective stacks.
  No exclamation marks. Contractions allowed ("we'll", "you'll", "won't").
- **Warm (professional, health, personal services):** measured sentences.
  Verbs like "advise," "guide," "support," "treat," "review." Still specific,
  still verb-led, still no adjective stacks.

Both personas ban "we pride ourselves," "passionate about," "dedicated team,"
"wide range of services," "one-stop shop."

## Banned vocabulary (auto-checked by `core/validate_filled_html.py`)

```
revolutionizing, unleash, seamless, robust, cutting-edge,
empowering, synergy, best-in-class, world-class, leverage,
holistic, premier, next-level, state-of-the-art, game-changing,
unparalleled, unmatched, ecosystem, paradigm, reimagine,
transforming, disrupt
```

Banned phrases:
```
welcome to, we pride ourselves, your one-stop shop,
look no further, don't hesitate to contact us,
we go the extra mile, customer satisfaction is our top priority,
feel free to, at your service, we offer a wide range of services
```

If you catch yourself writing any of the above, stop and rewrite.

## Slot: `hero_subhead` (≤25 words)

Pick ONE of these patterns based on data density:

| Pattern | When | Template |
|---------|------|----------|
| S-A Proof triple | always works | `{credential_marker} · {city} and {radius_hint} · {availability}.` |
| S-B What you get | offer-heavy businesses | `You get {deliverable_1}, {deliverable_2}, and {guarantee}.` |
| S-C Numbers line | high review count | `{review_count} {rating}-star reviews. Working across {city}. {credential_marker}.` |
| S-D Scope + exclusion | specialist with clear scope | `{what_you_do}. {what_you_don't_do}. {how_to_book}.` |

Constraints:
- Second person. Specific. No "we pride ourselves," "passionate," "dedicated."
- Digits for numbers (`173`, not `one hundred seventy-three`).
- One idea per sentence. Full stops are free.
- Must include the credential_marker and either the rating+reviews pair or a
  quantified promise.

Example fills:
- **electrician (cold), 173 reviews, 5.0★:** `NICEIC Approved · Edinburgh and EH postcodes · Emergency callouts 7 days.` (S-A)
- **solicitor (warm), 58 reviews, 4.9★:** `SRA-regulated family solicitor for Stirling homeowners. 58 reviews, 4.9★. Same-week appointments.` (S-C)

## Slot: `service_{1..6}_title` (≤4 words, sentence case)

The filler passes you the raw `services_offered[i]` via the instruction
comment. Rewrite to a tight title.

Rules:
- Sentence case. No "&". No "and" unless essential.
- Strip articles ("Electrical repairs" → "Electrical repairs" is fine; "The rewiring service" → "Rewires").
- Prefer nouns to gerunds ("Rewires" beats "Rewiring services").

Examples:
- `Electrical repairs` → "Repairs & faults" (3 words)
- `Fuse board replacements` → "Fuse boards" (2 words)
- `Bathroom fitting` → "Bathrooms" (1 word)
- `Drain unblocking` → "Drain unblocking" (2 words)

## Slot: `service_{1..6}_description` (≤15 words)

Formula: **`{outcome_verb} {deliverable}. {specific_qualifier_or_proof}.`**

Rules:
- Start with an outcome verb. Never "We provide..."
- Two sentences max. Second sentence is the proof hook (price, warranty, scope, credential).
- No filler adjectives ("quality," "reliable," "professional").
- No emoji. No markdown.

Examples:
- "New circuits, sockets, fused spurs. Certified and tested to 18th Edition."
- "Full and partial rewires for Stirling homes. Fixed price before we start."
- "Emergency fault-finding. Response within 90 minutes, EH postcodes."
- "Gas Safe boiler installs. 10-year manufacturer warranty included."

## Slot: `faq_{1..5}_answer`

Five questions in order — answer each in a single `<p>`, never a list:

1. **Cost?** — word budget ≤40. Give a real price band (e.g., "£85–£450 depending on scope"),
   name what's included, name what isn't.
2. **Insured/accredited?** — ≤25 words. Template: "Yes. {credential_marker}. Certificate available on request."
3. **How quickly can you get out?** — ≤30 words. Combine response time + radius + booking channel.
4. **Fixed prices or estimates?** — ≤25 words. State ONE pricing model. Explain when a visit is needed.
5. **Workmanship guarantee?** — ≤40 words. Period + what's covered + how to claim.

Tone: same as hero. No "please feel free," no "don't hesitate."

Example fills (electrician, Stirling):
1. "Typical domestic jobs run £85–£450 depending on scope. The quote covers labour, parts, and certification. Parking charges and material upgrades are listed separately."
2. "Yes. NICEIC Approved Contractor. Certificate available on request."
3. "Emergency response within 90 minutes across Stirling and FK postcodes. Book by phone; next-day slots for non-urgent work."
4. "Fixed prices, always. We quote the job before starting. Larger rewires may need a site visit first."
5. "12-month workmanship guarantee on every install. Covers any fault tied to our wiring or certification. Call the office and we'll return within 48 hours."

## Slot: `review_{1..3}_name` (first name + locale)

Each review's quote is already truncated in `review_{i}_quote`. You author
attribution in this slot only.

Rules:
- First name only, then a comma, then a geographic marker (neighborhood,
  town, or city). Never surnames (privacy). Never "John D." (corporate-feel).
- If the source review has no author first name in the scraped data, use
  a plausible local first name paired with the business city. The GBP
  reviews rarely include names — attribution defaults to "{First}, {city}".
- Keep it short. "Izabela, Edinburgh" not "Izabela M., central Edinburgh".

Examples:
- `Izabela, Edinburgh`
- `Gordon, Stirling`
- `Rachel, FK7`

## Checklist before finishing

- [ ] Every `[[WRITE_*]]` sentinel replaced.
- [ ] No banned word / phrase (case-insensitive).
- [ ] Every service_description ≤15 words.
- [ ] Hero subhead ≤25 words.
- [ ] FAQ answers within their per-question word budgets.
- [ ] No exclamation marks outside review quotes.
- [ ] No em-dash stacking. One per section max.
- [ ] Persona voice matches vertical (cold vs warm).

Run `python3 -m core.validate_filled_html output/<slug>.html` — it prints any
residual sentinel, banned word, or readability warning.
