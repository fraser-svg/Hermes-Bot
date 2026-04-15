# Copy Decision Log — Master Template COPY.md

**Author:** `conversion-copywriter`
**Date:** 2026-04-13
**Status:** Phase-3 authoring complete. Calibrated against `DESIGN.md` (post-integration pass) and `_workspace/template/01_research.md`.

## Inputs

- `DESIGN.md` §1 (Cold Engineering Neutral theme, `[data-persona]` warm/cold toggle)
- `DESIGN.md` §2 (palette — primary CTA is warm near-black `#0A0F1A`, NOT blue; vertical blue is optional override)
- `DESIGN.md` §3 (typography — h1 14ch, mono eyebrow 12px JetBrains Mono, 650px body cap)
- `DESIGN.md` §4 (component specs — `.btn-primary`, `.btn-urgent`, `.card`, `.badge-trust`, `.badge-signal-success`, testimonial card)
- `DESIGN.md` §7 (do/don't — no eyebrow above hero h1, no exclamation tone, no uppercase button labels)
- `DESIGN.md` §9 (agent prompt guide)
- `_workspace/template/01_research.md` §3 (trust signals inventory), §6 (open copywriter questions: eyebrow bank, 2-word CTA matrix, metric ribbon, review truncation, voice split, accreditation whitelist)
- `_workspace/template/02_design_decisions.md` I-02 (CTA is near-black), I-03 (persona toggle), I-09 (mono eyebrow adopted), I-11 (one hero gradient)
- `references/business_details.json` (slot schema — Spartan Electrical, Edinburgh, 5★, 173 reviews)
- `.claude/skills/copy-md-framework/SKILL.md` (10-section schema contract)

## Decisions

### C-01 — Two voice modes locked to DESIGN.md `[data-persona]`
**Decision:** Voice splits into **Cold** (trades/emergency/tech) and **Warm** (professional/personal). Both share the specificity rules but differ in cadence and verb palette.
**Why:** Research §6 Q5 — "Warm vs cold voice calibration" open question. Cold voice matches the `data-persona="cold"` alt-surface `#F9FAFB`, warm matches `data-persona="warm"` `#F6F5F4` (Notion/Intercom precedent). Avoids sounding clinical in a solicitor's office and avoids sounding mushy in an emergency plumber's hero.
**Source:** `DESIGN.md §1`, research §2.1 + §6 Q5.

### C-02 — Primary CTA default is `Call {{business.phone}}`, not "Get quote"
**Decision:** The phone number IS the primary CTA label. `Get quote` / `Book visit` / `See pricing` are explicit alternatives, each with a named condition-of-use.
**Why:** Research §3 trust signals — click-to-call is the #1 conversion action for local service. DESIGN.md §2 ships the primary button as warm near-black `#0A0F1A`, which pairs correctly with a phone-as-CTA (doesn't compete with urgency-red for attention). Also gives the generator a safe fallback when the client has no online booking system.
**Source:** Research §3, `DESIGN.md §2` I-02, `DESIGN.md §4` button spec.

### C-03 — CTA is 2 words max (unless it's a phone number)
**Decision:** All non-phone CTAs capped at 2 words. Phone CTAs are `Call {{phone}}` format (technically 3+ tokens, but treated as a single unit).
**Why:** Research §3 CTA observations — Stripe `Start now`, Vercel `Start Deploying`, Cal.com `Get started`, Mintlify `Get Started`, Notion `Try it`, Linear `Sign up`. All 2-word, verb-led, imperative.
**Source:** Research §3 + §6 Q2.

### C-04 — 9-item full-ban vocabulary list, 8-item context-ban list, 15-item phrase-ban list
**Decision:** Three-tier ban system. Full ban (auto-strip), context ban (allowed only if backed by concrete proof), phrase ban (AI-slop sentence patterns).
**Why:** Skill contract §9 mandates the banned vocabulary list. Research §3 CTA patterns show winning copy is verb-led and specific; the banned list is the literal inverse (`revolutionizing` / `unleash` / `seamless` / `robust` / `cutting-edge` / `solutions`). Context-ban tier exists because words like `quality` and `experienced` aren't inherently bad — they're bad when unsupported. Phrase ban catches the AI-slop sentence-level constructions that any word-level filter misses (`"Welcome to…"`, `"Look no further."`, `"We pride ourselves on…"`).
**Source:** Skill contract, `.claude/skills/copy-md-framework/SKILL.md` §banned vocabulary, research §4 anti-slop rules.

### C-05 — 3 headline formulas × 3 categories = 9 hero variants
**Decision:** Trades / Professional / Personal. Each category has T-1/T-2/T-3 (or P-/S-) formulas. All three follow Problem → Outcome → Proof.
**Why:** Skill contract output checklist mandates "3 headline formulas per category." Three-variant rotation lets `generate.py` A/B headlines without re-prompting. Categories map cleanly onto the `DESIGN.md §1` persona split (trades → cold, professional + personal → warm, but personal services can flex cold when emergency-adjacent like vets/emergency dental).
**Source:** Skill contract output checklist, research §3 trust patterns.

### C-06 — 14-word h1 cap (matches DESIGN.md h1 `max-width: 14ch`)
**Decision:** Every hero headline formula produces ≤14 words. Validated on worked examples.
**Why:** `DESIGN.md §3` sets h1 `max-width: 14ch` — a 14-word English sentence fits in 2 lines at that width on desktop and 3 lines on mobile. Any longer and the typography breaks or the copy ships as an h2.
**Source:** `DESIGN.md §3` hierarchy table.

### C-07 — Review truncation only, never paraphrase
**Decision:** `google_reviews[].text` is quoted verbatim. Truncation permitted from the end of a sentence. Mid-quote elision with `[…]` permitted. **No paraphrasing** — compliance risk.
**Why:** Research §6 Q4 explicitly flags this. Paraphrasing a Google review creates a copy that the reviewer didn't write, which exposes the business to misrepresentation claims and kills the trust signal. Better to use a different review than paraphrase one.
**Source:** Research §6 Q4.

### C-08 — Accreditation whitelist per vertical (14 verticals)
**Decision:** COPY.md §5 ships a named whitelist of allowed badges per vertical. Never render a badge outside the whitelist for that category.
**Why:** Research §6 Q6 — trust logos can't be fabricated. A dentist site with a `Gas Safe` badge is a lawsuit. The whitelist constrains the generator to badges that exist for the business's actual regulator.
**Source:** Research §6 Q6.

### C-09 — Trust ribbon separator is `·` (middle dot), never `|`
**Decision:** `{{review_count}} reviews · {{rating}}★ · {years} · {credential}`.
**Why:** Research §6 Q3. Middle dot is the typographic convention (Stripe, Linear, Vercel metric rows). Pipe character reads as a code artifact and breaks on mobile wrap.
**Source:** Research §6 Q3 + §3 metric cluster pattern.

### C-10 — Mono eyebrow bank: 15 labels (exceeds skill minimum)
**Decision:** 15-entry eyebrow bank covering services/reviews/areas/trust/accreditation/process/pricing/FAQ/contact/emergency/credentials/trading-history/geography.
**Why:** Research §6 Q1 asked for "10–15 entry bank." Shipped 15. Every label is ≤3 words, uppercase-safe, and maps to a real section type.
**Source:** Research §6 Q1, `DESIGN.md §3` mono eyebrow type role + `.eyebrow-mono` utility in `DESIGN.md §9`.

### C-11 — 15-word cap on service card descriptions
**Decision:** Every service card description is ≤15 words. Validated on all 8 Spartan services.
**Why:** `DESIGN.md §4` service card spec mandates uniform card height and 650px body cap. 15-word descriptions fit in 2 lines at card width (~300px) without breaking the grid. Also forces the copywriter to pick a single outcome per service instead of listing features.
**Source:** `DESIGN.md §4` service card spec.

### C-12 — Slot map is authoritative, derived slots are explicit
**Decision:** §10 Slot Map names every JSON field plus 5 derived slots (`service_radius`, `response_window`, `trading_since`, `year`, `credential_marker`). Derived slots are computed by `template-engineer`, not by the JSON.
**Why:** Skill slot convention says "do not invent fields." A strict field-only rule would force every formula to avoid useful transformations (postcode radius from city, years-trading from years_experience). Marking derivations explicit makes the contract clear to `template-engineer` and still forbids free-form invention.
**Source:** `.claude/skills/copy-md-framework/SKILL.md` slot conventions.

### C-13 — Fallback behavior for optional fields
**Decision:** Every optional slot has a named fallback (drop section, drop card, drop subhead item) rather than rendering empty strings or placeholder text.
**Why:** A partial render (`"Serving Edinburgh since ."`) is worse than a smaller render. Fallbacks are the only safe way to handle the long tail of businesses that don't fill every JSON field.
**Source:** Skill failure recovery section.

### C-14 — `Emergency? Call {{phone}}` urgent CTA uses `--signal-urgent`, not `--accent-primary`
**Decision:** The emergency CTA copy is distinct (prefixed with "Emergency?") and only rendered for 24/7 emergency verticals. Uses `.btn-urgent` red, not the default near-black primary.
**Why:** `DESIGN.md §4` ships `.btn-urgent` as `--signal-urgent #B91C1C`, "never decorative." Reserving the red CTA for real emergency copy prevents color-as-decoration slop and makes the red read as signal.
**Source:** `DESIGN.md §4` `.btn-urgent` spec.

## Slot validation log (against business_details.json)

Validated against `references/business_details.json` (Spartan Electrical):

| Slot | Field | Present? | Notes |
|------|-------|----------|-------|
| `business.name` | `business_name` | ✓ "Spartan Electrical" | |
| `business.category` | `business_category` | ✓ "electrician" | |
| `business.city` | `city` | ✓ "Edinburgh" | |
| `business.address` | `address` | ✓ "22 Stafford St…" | |
| `business.phone` | `phone_number` | ✓ "0131 202 2711" | Needs `tel:` sanitization to `+441312022711` |
| `business.services[]` | `services_offered[]` | ✓ 8 services | Meets ≥3 requirement |
| `business.reviews[]` | `google_reviews[]` | ✓ 5 reviews | Meets ≥1 requirement; Izabela review used as §5 worked example |
| `business.rating` | `rating` | ✓ 5 | |
| `business.review_count` | `review_count` | ✓ 173 | |
| `business.years` | `years_experience` | ✗ **MISSING** | Fallback: drop "Trading since" card; drop S-C numbers line years item |
| `business.license` | `license_number` | ✗ **MISSING** | Fallback: drop accreditation badge; show vertical-default credential (NICEIC) only if template-engineer confirms from external validation |
| `business.maps_url` | `google_maps_url` | ✓ present | |
| `business.email` | `email` | ✗ **MISSING** | Fallback: omit footer email line |

**Critical finding:** `years_experience` and `license_number` are absent from the current Spartan JSON. Fallbacks in §10 handle this cleanly. `template-engineer` should add these fields to the JSON schema as optional — not required — and `market-researcher` / enrichment pipeline should populate them when available.

**Assumed-credential caution:** The COPY.md trust block examples reference "NICEIC" for Spartan and "Gas Safe" for plumbers. These assumptions come from vertical defaults, not from the JSON. `template-engineer` must NOT render an accreditation badge unless `license_number` is present AND matches a whitelist entry for that vertical (C-08). Otherwise it's fabricated trust.

## Schema conformance check

- [x] §1 Voice & Tone
- [x] §2 Headline Formulas (Hero) — 3 variants × 3 categories = 9 total
- [x] §3 Subheadline Patterns — 4 patterns (S-A through S-D)
- [x] §4 CTA Vocabulary — default + 7 alternatives + urgent + secondary + 9-item ban table
- [x] §5 Trust Block Patterns — ribbon, metric cluster, accreditation row, review card, priority order
- [x] §6 Service Block Copy — card template, formula, 8 worked fills for Spartan, eyebrow, h2 formulas
- [x] §7 FAQ Templates — 4 universal + 2 trades + 2 professional/medical + banned patterns + rules
- [x] §8 Microcopy — forms, badges, footer, 15-item eyebrow bank, nav
- [x] §9 Banned Vocabulary — 34-word full ban, 8-word context ban, 15-phrase ban
- [x] §10 Slot Map — 13 JSON slots + 5 derived slots + fallback rules + 8-item validation checklist

## Output checklist (per skill)

- [x] All 10 sections present
- [x] 3 headline formulas per category (trades, professional, personal)
- [x] Slot map matches `business_details.json` field names exactly
- [x] Banned vocabulary list included
- [x] Every formula has a worked example fill
- [x] `_workspace/template/03_copy_decisions.md` logs banned-word sources and formula rationale

## Follow-ups for downstream agents

**`template-engineer`:**
- COPY.md §10 is authoritative for every placeholder. Do not invent slots.
- Derived slots (`service_radius`, `response_window`, `trading_since`, `credential_marker`) require template-side logic — build a city→postcode map and a vertical→response-window map.
- Primary CTA default is `Call {{business.phone}}` rendered as `<a href="tel:+44...">` with the display string as text. Mono-phone type role on the label.
- Persona toggle (`<html data-persona="cold|warm">`) drives both `DESIGN.md §1` alt-surface AND COPY.md §1 voice mode. Map vertical → persona:
  - `cold`: electrician, plumber, roofer, HVAC, gas engineer, locksmith, pest, cleaner, painter, landscaper, handyman, IT, emergency
  - `warm`: solicitor, accountant, IFA, mortgage broker, architect, surveyor, dentist, vet, GP, physio, chiropractor, optician, personal trainer, therapist, tutor, photographer
- Validate every rendered page against the 8-item checklist in §10.
- `.btn-urgent` is only rendered when `business_details.json` has an emergency flag or the category is in the emergency whitelist. Never decorative.

**`template-critic`:**
- COPY.md §9 banned vocabulary + §9 banned phrase list are the auto-reject criteria for generated copy.
- Review-quote verbatim rule (C-07): any generated quote that doesn't match the source `google_reviews[].text` (allowing only truncation/elision) fails critique.
- Hero h1 ≤14 words, subhead ≤25 words, service description ≤15 words — word-count checks.
- Trust ribbon separator must be `·`, not `|` or `-`.
- No exclamation marks outside review quotations.

**`market-researcher`:**
- Current Spartan JSON lacks `years_experience` and `license_number`. These are high-value proof fields. If the enrichment pipeline can extract them from Companies House, NICEIC public register, or Checkatrade, ship them.
- Accreditation whitelist per vertical (§5) is the scope of safe badges. Additions welcome if researcher finds new category-specific regulators (e.g. RICS for surveyors, ARB for architects).
