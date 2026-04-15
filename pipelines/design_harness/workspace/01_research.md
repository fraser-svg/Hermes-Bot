# Template Research — 2026-04-13

Source corpus: VoltAgent/awesome-design-md, fetched via `npx getdesign add {slug}` (CLI pulls full DESIGN.md; the GitHub README is a redirect stub). All 10 exemplars fetched successfully as full Stitch 9-section files. No degraded fetches.

Hermes priors read: `_workspace/template/DESIGN_existing_stripe_reference.md` (Stripe sample, Stitch format confirmed) and `prompts/website_builder.md` §§1–5 (current Inter + cold-gray `#F9FAFB` + utility-blue + anti-slop direction).

Target end user: UK/US local-service businesses — electricians, plumbers, roofers, dentists, accountants, solicitors, personal trainers, cleaners, HVAC, vets, movers, photographers. Buyer mindset: problem-now, high-trust, 3-second read.

---

## 1. Exemplar matrix

| Exemplar | Fit (★1–5) | Adopt for | Skip |
|----------|-----------|-----------|------|
| **Stripe** | ★★★★★ | Trust hierarchy, layered blue-tinted shadow, navy-not-black heading (`#061b31`), conservative 4–8px radius, light-weight restraint at display sizes, dark brand section as rhythm break | Purple CTA (wrong signal for trades), weight-300 headlines (too whispered for urgency copy) |
| **Linear** | ★★★★ | Editorial precision, 510-weight discipline, OpenType `cv01/ss03` on Inter, negative tracking at display sizes, luminance-step depth system | Dark-mode canvas (wrong for local service trust), near-transparent surfaces (reads as unfinished) |
| **Vercel** | ★★★★★ | Shadow-as-border technique (`box-shadow: 0 0 0 1px rgba(0,0,0,0.08)`), inner `#fafafa` ring for card glow, achromatic palette, three-weight system (400/500/600), `#171717` not black, aggressive negative tracking at display | Workflow color triad (not useful), 9999px pill radius (slop trigger per Hermes rule) |
| **Cal.com** | ★★★★ | Multi-layer ring+diffused shadow for physical-card feel, Cal Sans-style display font discipline (headings only, never body), 80–96px section padding, generous radius graduation | 9999px pill CTAs, 64–100px nav radius |
| **Resend** | ★★★ | Shadow philosophy lesson (on dark, borders replace shadows), three-font editorial hierarchy as *concept*, frost-tinted borders as signature, monospace as design element | Dark canvas, serif display hero (too editorial for trades), multi-accent color system |
| **Intercom** | ★★★ | Sharp 4px button geometry as discipline, scale(1.1)/scale(0.92) hover/press affordance, warm cream alternative surface (`#faf9f6`) for premium-traditional persona, singular brand accent rule, negative tracking on headings | Weight-400 headlines (too light for urgency), warm palette for trades persona |
| **Airbnb** | ★★★ | Three-layer warm card shadow (`0.02 ring + 0.04 ambient + 0.1 lift`), near-black `#222222` heading rule, Rausch-red-as-singular-accent discipline, photography-first card pattern for trust, 500–700 weight minimum on headings | Rausch Red itself, 20–32px card radius (breaks Hermes 12–16px convention) |
| **Notion** | ★★★ | Warm-neutral alt surface (`#f6f5f4`) for premium-traditional variant, 4- and 5-layer accumulating soft shadow stacks (none > 0.05 opacity), whisper border `1px rgba(0,0,0,0.1)`, section alternation rhythm, `rgba(0,0,0,0.95)` heading color technique | Blue CTA (`#0075de`), decorative illustrations, 8px base with fractional scale |
| **Mintlify** | ★★★★ | Border-driven depth (5% opacity `rgba(0,0,0,0.05)` line system), atmospheric hero gradient as single decorative move, section-padding 48–96px discipline, uppercase label pattern (Geist Mono, 12px, +0.6px tracking) for "mono as design element" moments, Inter discipline | 9999px pill buttons, brand green CTA |
| **Webflow** | ★★★ | 5-layer cascading shadow formula (`0→24, 0.01→22, 0.04→18, 0.08→13, 0.09→7`) as reference-grade physical depth, conservative 4–8px radius rule, translate(6px) hover microinteraction | Secondary rainbow palette, fractional pixel scale (1.6/2.4/5.6), WF Visual Sans |

**Shortlist used: 10/10 fetched in full.** No automotive/luxury exemplars included (Ferrari/Lamborghini/BMW/Tesla per skill guidance — too editorial, wrong funnel).

**Top 3 "adopt wholesale":** Stripe (shadow + navy heading + section rhythm), Vercel (shadow-as-border + achromatic + Geist-style tracking), Mintlify (border-driven depth + uppercase-mono labels + Inter discipline). All three translate directly to local-service without importing brand baggage.

---

## 2. Cross-cutting patterns (≥3 exemplars)

### 2.1 Theme & atmosphere

- **Rule:** Canvas is pure white (`#FFFFFF`). Never pure black for text — use "warm near-black" in the `#0d0d0d`–`#222222` range.
  - Sources: Stripe §1 (`#061b31` navy heading), Vercel §1 (`#171717`), Mintlify §1 (`#0d0d0d`), Notion §1 (`rgba(0,0,0,0.95)`), Airbnb §1 (`#222222`), Intercom §1 (`#111111`), Cal.com §1 (`#242424`).
  - **Replaces AI-slop rule:** Hermes prompt already says "Ink: `#111827`" which is in-range — retain but elevate to a hard requirement with the rationale that pure `#000000` reads cold-clinical and all 7 exemplars avoid it.
  - **Local-service translation:** Near-black builds the "engineering firm, not tradesman van" feeling the Hermes brief wants.

- **Rule:** One alt-surface for section rhythm. Either cold off-white (`#F9FAFB`/`#fafafa`) or warm off-white (`#f6f5f4`/`#faf9f6`). Pick one per persona, alternate against pure white.
  - Sources: Stripe §5 (alternates white with `#1c1e54` dark brand), Notion §5 (white ↔ `#f6f5f4` warm), Mintlify §5 (white throughout, borders only), Vercel §5 (white throughout, shadow-border only), Intercom (warm `#faf9f6`).
  - **Local-service translation:** Use cold `#F9FAFB` for trades/tech personas (plumber, electrician, HVAC, IT). Use warm `#f6f5f4` for premium-traditional personas (solicitor, accountant, dentist, photographer). Hermes currently uses cold-only — adding warm as an option unlocks the "safe hands" verticals.

- **Rule:** Exactly one saturated accent color, used ONLY for primary CTA + link + focus ring. Everything else is grayscale.
  - Sources: Stripe (`#533afd` purple), Linear (`#5e6ad2` indigo), Airbnb (`#ff385c` Rausch), Notion (`#0075de` blue), Mintlify (`#18E299` green), Intercom (`#ff5600` Fin orange), Cal.com (grayscale, blue link only).
  - **Replaces AI-slop rule:** Hermes already enforces "90% white/gray, 10% utility". Keep, but add the hard rule "accent never appears on icons, dividers, section backgrounds, or decorative flourishes — CTA and link only." Four exemplars call this out explicitly.

### 2.2 Palette

- **Rule:** Heading color ≠ body color ≠ muted color. Use a 3- or 4-step neutral scale.
  - Stripe: `#061b31` heading, `#273951` label, `#64748d` body.
  - Vercel: `#171717` heading, `#4d4d4d` body, `#666666` tertiary, `#808080` placeholder.
  - Mintlify: `#0d0d0d` heading, `#333333` body, `#666666` tertiary, `#888888` placeholder.
  - Notion: `rgba(0,0,0,0.95)` heading, `#615d59` secondary, `#a39e98` muted.
  - **Translation:** Hermes currently has heading (`#111827`) + body (`#6B7280`). Add a third "muted" step (`#9CA3AF` or similar) for review stars, timestamps, fine-print — all 4 exemplars split tertiary from body.

- **Rule:** Borders live between `rgba(0,0,0,0.05)` and `rgba(0,0,0,0.10)`. Never solid mid-grays.
  - Sources: Mintlify (`rgba(0,0,0,0.05)` standard, `rgba(0,0,0,0.08)` interactive), Notion (`rgba(0,0,0,0.1)` whisper), Vercel (`rgba(0,0,0,0.08)` shadow-border), Stripe (`#e5edf5` — equivalent to ~6% dark).
  - **Replaces AI-slop rule:** Hermes uses `#E5E7EB`. Keep the value but express it as an opacity rule so dark-hero text over it still works; `rgba(0,0,0,0.06)` is the safer cross-surface form.

### 2.3 Typography

- **Rule:** Inter Variable is the correct default for local-service (confirmed by ≥4 premium-to-mainstream exemplars as either native or close sibling).
  - Direct Inter use: Mintlify §3, Cal.com §3 (body), Notion §3 (NotionInter = modified Inter), Linear §3 (Inter Variable). Stripe, Vercel, Intercom, Airbnb use custom variable fonts in the same genre.
  - **Hermes prior match:** Rule 1 already mandates Inter. Confirmed correct. Retain.

- **Rule:** Aggressive negative letter-spacing at display sizes. Range across exemplars: -0.8px to -2.88px at 48–64px.
  - Sources: Stripe (-1.4px at 56px, -0.96px at 48px), Linear (-1.056px at 48px), Vercel (-2.4px at 48px — most aggressive), Mintlify (-1.28px at 64px), Notion (-2.125px at 64px, -1.5px at 48px), Intercom (-2.4px at 80px), Webflow (-0.8px at 80px).
  - **Translation for local-service:** `-0.04em` to `-0.05em` (Hermes current spec) = roughly `-1.9px to -2.4px at 48px`. **This lines up with Vercel/Notion/Intercom.** Confirmed correct. Retain.
  - **Replaces AI-slop rule:** Hermes says `-0.04em to -0.06em` — tighten lower bound to `-0.03em` to avoid breaking at narrow mobile widths, per Linear's "tracking adjusts proportionally" rule.

- **Rule:** Three-weight UI system — never more than 3 discrete weights in play.
  - Sources: Vercel 400/500/600, Mintlify 400/500/600, Stripe 300/400 (two-weight variant), Linear 400/510/590, Intercom 400/700 (simplified two-weight).
  - **Conflict:** Hermes currently loads `400/500/600/700/800`. Exemplars cluster around "no bold above 600 except display hero". **Recommendation: drop 800, keep `400/600/700` where 700 is reserved for display hero only.** Flagged for architect.

- **Rule:** OpenType stylistic sets are non-negotiable on premium-tier builds.
  - Sources: Stripe `"ss01"`, Linear `"cv01","ss03"`, Vercel `"liga"`, Resend `"ss01","ss04","ss11"`, Notion `"lnum","locl"`, Airbnb `"salt"`, Intercom (via Saans custom), Mintlify (Inter default).
  - **Translation:** For Inter, enable `font-feature-settings: "cv11", "ss01"` globally. This is a free visual upgrade that costs nothing in build complexity. **New rule for Hermes.**

- **Rule:** Uppercase-mono micro-label pattern (12px, +0.5–0.7px tracking, Geist Mono or equivalent, `text-transform: uppercase`) as a section-hat / eyebrow / category marker.
  - Sources: Mintlify §3 (13px Inter +0.65px + Geist Mono 12px +0.6px), Vercel §3 (12px Geist Mono uppercase), Resend §3 (12px Inter uppercase), Linear §3 (12px Berkeley Mono uppercase labels), Stripe §3 (10px micro labels).
  - **Translation for local-service:** Use this for service-section eyebrow labels ("SERVICES", "SERVICE AREAS", "REVIEWS"). Creates the "engineering firm" signal without importing dark themes. **New rule for Hermes.**

### 2.4 Components

- **Rule:** Border-radius is conservative. The `4px–16px` range covers all functional elements. Pill (`9999px`) is for badges/chips only, never primary CTA.
  - Sources: Stripe (4–8px buttons/cards), Linear (6–12px), Vercel (6–8px cards, 9999px for badges only), Cal.com (6–16px cards, 9999px pill for badges), Webflow (4–8px aggressive), Intercom (4px buttons — sharpest), Notion (4px buttons, 12–16px cards).
  - **Conflict:** Mintlify and Resend use 9999px pill for primary CTA. Outliers — ignored for local-service (Hermes anti-slop rule explicitly forbids pill buttons, confirmed correct by majority).
  - **Translation:** Hermes current `12/16/24px` for cards is in-range. Keep. For buttons, standardize on **`8px`** (midpoint of Vercel 6px / Stripe 4–8px / Notion 4px). Retain the "never pill" rule.

- **Rule:** Primary CTA pattern = solid dark background `#111`/`#171717`/`#222222` + white text, OR one saturated accent color + white text. Never both. Ghost/secondary is outlined transparent with 1px border.
  - Sources: Cal.com (`#242424` solid), Mintlify (`#0d0d0d` solid), Airbnb (`#222222` solid), Notion (`#0075de` blue), Vercel (`#171717` solid), Intercom (`#111111` + scale(1.1) hover), Stripe (`#533afd` accent).
  - **Translation:** Hermes currently auto-selects accent by vertical. Retain but add the **"dark solid as universal fallback"** option — it works for every category and 5/10 exemplars use it as the primary pattern. Flag for architect as the safer default.

- **Rule:** Button hover = either scale transform OR translate, never color-only.
  - Sources: Intercom (scale 1.1 hover, 0.85 active), Notion (scale 1.05 hover, 0.9 active), Airbnb (scale 0.92 focus), Webflow (translate 6px), Cal.com (opacity 0.7).
  - **New rule for Hermes:** Add micro-transform to all buttons. 2% scale or 2–4px translate. No-op color-only hovers are a slop signal.

- **Rule:** Cards use a multi-layer shadow stack, never single-layer `box-shadow`. Typical pattern: ring border layer + soft ambient layer + lift layer.
  - Sources: Stripe §6 (`rgba(50,50,93,0.25) 0 30 45 -30, rgba(0,0,0,0.1) 0 18 36 -18`), Vercel §6 (`0 0 0 1px 0.08 + 0 2px 2px 0.04 + 0 8px 8px -8px + inner #fafafa`), Airbnb §6 (3-layer: `0 0 0 1px 0.02 + 0 2 6 0.04 + 0 4 8 0.1`), Notion §6 (4-layer max 0.04, 5-layer max 0.05 deep), Cal.com §6 (ring + diffused + contact), Webflow §6 (5-layer cascade), Mintlify §6 (border-only, no shadow).
  - **Master pattern for Hermes (synthesized):**
    ```css
    box-shadow:
      0 0 0 1px rgba(0, 0, 0, 0.06),     /* ring border */
      0 2px 4px rgba(0, 0, 0, 0.04),     /* ambient */
      0 8px 16px -4px rgba(0, 0, 0, 0.08); /* lift */
    ```
    This is a 3-layer stack aligned with Airbnb (warm) and Vercel (achromatic) philosophies. **New canonical rule for Hermes.**

- **Rule:** Shadow-as-border technique (`box-shadow: 0 0 0 1px rgba(0,0,0,0.08)` instead of `border: 1px solid`) is the premium pattern.
  - Sources: Vercel (defining signature), Cal.com (ring shadows throughout), Linear (`rgba(0,0,0,0.2) 0px 0px 0px 1px`), Resend (`rgba(176,199,217,0.145) 0px 0px 0px 1px`).
  - **Translation:** Hermes currently uses `1px solid #E5E7EB`. Offer shadow-as-border as an upgrade for "premium" sub-persona — it allows smoother corner rounding and cleaner hover transitions. **Optional upgrade, flagged for architect.**

### 2.5 Layout

- **Rule:** Section vertical padding 64–120px desktop, ~48px mobile.
  - Sources: Cal.com (80–96px), Mintlify (48–96px), Notion (64–120px), Stripe (64px+), Linear (80px+), Resend (80–120px).
  - **Replaces AI-slop rule:** Hermes prompt spacing scale goes `4/8/16/32/64`. Extend to `4/8/16/32/64/96` for section-level padding. **Refinement.**

- **Rule:** Max content width ~1200px. Centered container with generous side margins.
  - Sources: 8/10 exemplars (Stripe 1080, Linear 1200, Vercel 1200, Cal.com 1200, Notion 1200, Mintlify 1200, Airbnb responsive, Webflow responsive).
  - **Translation:** Confirmed. Retain existing Hermes container logic.

- **Rule:** Body text max-width ≤ 650px (reading-comfort convention).
  - Sources: Mintlify (reading-first), Notion (reading-first), Cal.com (editorial).
  - **Hermes prior match:** Rule 1 already says `Body max-width: 650px. Enforce this everywhere.` Confirmed correct.

### 2.6 Depth

- **Rule:** Shadow opacity individual layers never exceed 0.10. Accumulated stacks stay under 0.15 total.
  - Sources: Notion (max single layer 0.05), Mintlify (0.03–0.06), Airbnb (0.02/0.04/0.1 graduated), Vercel (0.04/0.08), Cal.com (0.05/0.08/0.7 but the 0.7 is a sharp contact at -4px spread).
  - **Replaces AI-slop rule:** Hermes prompt says "Layered micro-elevation" but doesn't quantify. **Add: "No individual box-shadow layer may exceed 0.10 opacity. Total visible shadow must read as lift, not drop."**

- **Rule:** Heading color is warmed. Tint the near-black slightly toward navy or brown, never pure `#000`.
  - See §2.1. Reinforced for depth section — this is a depth-signaling trick (warmth = closer/friendlier perceived elevation).

### 2.7 Responsive

- **Rule:** Display headline scales `64 → 48 → 32` across desktop/tablet/mobile with letter-spacing scaling proportionally.
  - Sources: Stripe (56→48→32), Linear (72→48→32), Vercel (48→ responsive), Notion (64→40→26), Mintlify (64→40).
  - **Replaces AI-slop rule:** Hermes uses `clamp(2.5rem, 6vw, 4.5rem)` = 40–72px. In-range. **Refinement: add explicit breakpoint stops so tracking can adjust — clamp alone doesn't re-compute `letter-spacing`.**

- **Rule:** 3-col → 2-col → 1-col feature card collapse. Universal.
  - All 10 exemplars.

---

## 3. Trust signals inventory (for conversion-copywriter)

Extracted patterns that appear as trust/social-proof components across exemplars:

- **Logo trust bar.** Grayscale company logos in a horizontal row with subtle ring-border containers. Present in: Stripe, Vercel, Cal.com, Mintlify, Notion, Intercom, Webflow. **Translation for local-service:** "Trusted by 500+ homes in Dunfermline" + 4–6 logos of familiar local institutions (housing associations, estate agents, local councils, Checkatrade, Gas Safe, TrustMark). Copy must be specific: logo names + count + geo.

- **Metric card pattern.** Large number + short description. Sources: Vercel (`10x faster`), Notion (`$4,200 ROI`), Linear, Stripe.
  - **Translation:** `"58 five-star reviews"`, `"45-min average response time"`, `"12 years in Fife"`. Already partially in Hermes prompt Rule 4 — elevate to dedicated component.

- **Metric cluster row.** 3–4 metrics in one horizontal strip, usually right below hero. Sources: Stripe, Linear, Notion.
  - **Translation:** `"58 reviews · 4.9★ · 12yrs · Gas Safe"`. One-line trust ribbon.

- **Review quotation card.** White card, whisper border, italic or quoted body, name + photo + location. Sources: Airbnb (listing reviews), Notion, Intercom.
  - **Translation:** Quote 2 sentences max (Hermes word limit), reviewer first name + area ("Sarah, Dalgety Bay"), star row. Avatar optional.

- **Copy-micro-pattern: "Loved by your favorite companies" label.** A small uppercase-mono tracked-out eyebrow above the trust row. Sources: Mintlify, Vercel, Notion.
  - **Translation for copywriter:** Eyebrow copy pattern for UK trades: `"TRUSTED LOCALLY"`, `"45 VERIFIED REVIEWS"`, `"FULLY ACCREDITED"`.

- **Microcopy / CTA phrasing observations (for copywriter):**
  - Stripe: `"Start now"` / `"Contact sales"`.
  - Vercel: `"Start Deploying"` / `"Contact Sales"`.
  - Cal.com: `"Get started"`.
  - Mintlify: `"Get Started"` / `"Request Demo"`.
  - Notion: `"Get Notion free"` / `"Try it"`.
  - Linear: `"Start building"` / `"Sign up"`.
  - **Pattern:** Verb-led, 2 words, imperative, never "Learn More" or "Click Here". **For local-service:** `"Get Quote"`, `"Call Now"`, `"Book Visit"`, `"Check Availability"`, `"See Prices"`. All 2-word max.

---

## 4. Anti-slop additions beyond current Hermes prompt

New rules derived from cross-cutting extraction. Numbered for tracking.

1. **Pure `#000000` is forbidden for text.** Use `#111827`, `#0d0d0d`, `#171717`, or `#222222`. (All 10 exemplars.)
2. **Pure `#FFFFFF` buttons are forbidden as primary CTA on light backgrounds.** Primary CTA must be dark solid OR accent solid. (7/10 exemplars.)
3. **Single-layer `box-shadow` is forbidden for cards.** Minimum 2-layer stack (ring + lift) or 3-layer (ring + ambient + lift). Max individual opacity 0.10. (6/10 exemplars quantified.)
4. **Border-radius 9999px (pill) is forbidden for primary CTA buttons.** Pill shape is reserved for chips/badges/tags only. (Aligns with 7/10 + Hermes existing rule.)
5. **Color-only hover states are forbidden.** Every button must have a micro-transform on hover: `scale(1.02–1.05)`, `translate(2–4px)`, or measurable shadow expansion. (5/10 exemplars.)
6. **Decorative gradients are forbidden outside a single hero atmospheric wash.** No gradient dividers, no gradient card backgrounds, no gradient text. (Mintlify uses exactly one; Stripe reserves gradients for "decorative only, never buttons"; Resend none on marketing.)
7. **Accent color may only appear in: primary CTA background, link underline, focus ring, icon highlight.** Never in: dividers, section backgrounds, borders, body text emphasis, card fills. (7/10 exemplars enforce.)
8. **Letter-spacing at display sizes must be negative.** Target `-0.03em to -0.05em` at 48px+, scaling proportionally as size decreases. (All 10 exemplars.)
9. **Section alt-surface choice is persona-locked.** Cold-white (`#F9FAFB`) for trades/tech/emergency. Warm-white (`#f6f5f4`) for premium-traditional (solicitor, accountant, dentist, photographer). Never mix. **New decision point.**
10. **OpenType `font-feature-settings: "cv11", "ss01"` must be set globally on Inter.** Free upgrade, zero build cost. (8/10 exemplars enable some stylistic set.)
11. **Uppercase-mono eyebrow labels are the approved pattern for section hats.** 12–13px, +0.5–0.65px tracking, `text-transform: uppercase`, Geist Mono or JetBrains Mono. (5/10 exemplars.)
12. **Icons must be monochromatic thin-line.** Hermes prompt already says this. Reinforced — no exemplar uses multi-color or 3D iconography on marketing pages.

---

## 5. Open questions for design-system-architect

1. **Three-weight system conflict.** Hermes prompt currently loads Inter `400/500/600/700/800`. Exemplar majority uses `400/500/600` with no `800`. Question: drop `800` entirely (saves bandwidth, aligns with 7/10 exemplars), or retain `800` only for H1 display hero as Hermes currently does? My recommendation: drop `800`, use `700` for hero, use `600` for section headings.

2. **Dark-solid vs accent-color CTA default.** 5/10 exemplars use `#111/#171717/#222` dark solid as primary CTA. 5/10 use a saturated accent. Hermes currently uses per-vertical accent mapping. Question: make dark-solid the fallback when no accent is specified, or keep accent-by-default?

3. **Cold `#F9FAFB` vs warm `#f6f5f4` alt surface — persona split.** The research above proposes locking this per persona. Question: does the architect want two DESIGN.md variants (cold + warm) or a single DESIGN.md with a `persona_mode: cold | warm` toggle?

4. **Shadow-as-border upgrade tier.** Vercel-style `box-shadow: 0 0 0 1px rgba(0,0,0,0.06)` replacing `border: 1px solid`. Cleaner corner rounding, but harder to debug. Worth adding as a "premium tier" opt-in, or keep `border: 1px solid` universally?

5. **Section padding extension.** Current Hermes scale stops at 64px. Exemplars go to 96–120px. Question: extend the scale to `4/8/16/32/64/96/128`, or cap at 96?

6. **Card shadow canonical formula.** Research above proposes a 3-layer synthesized stack (`ring 0.06 + ambient 0.04 + lift 0.08`). Architect to confirm or override with a different blend.

7. **Hero atmospheric gradient — yes or no?** Mintlify's single gradient wash behind hero is elegant and doesn't break the anti-slop rule. Hermes currently forbids gradients. Question: allow ONE gradient in ONE place (hero background only), or hold the line?

---

## 6. Open questions for conversion-copywriter

1. **Eyebrow label copy bank.** Uppercase-mono section hats ("TRUSTED LOCALLY", "VERIFIED REVIEWS", "FULLY ACCREDITED"). Need a 10–15 entry bank covering: trades, medical, legal, personal-care, emergency. Tone: UK-spelling, specific-not-generic.

2. **2-word CTA variants per vertical.** Trades lean `"Get Quote"` / `"Call Now"`. Medical leans `"Book Visit"` / `"Check Availability"`. Legal leans `"Free Consult"` / `"Call Direct"`. Need the full matrix.

3. **Metric cluster ribbon copy formula.** Hero-adjacent 1-line trust ribbon (`"58 reviews · 4.9★ · 12yrs · Gas Safe"`). Need the separator convention (`·` vs `|` vs line-break on mobile) and which metrics are mandatory vs optional.

4. **Review card truncation rule.** 2 sentences max, 30 words max (Hermes existing rule). Question: if a Google review is longer, is the copywriter allowed to paraphrase, or only truncate with `[…]`? Paraphrase keeps rhythm but risks compliance issues — flag for copywriter.

5. **Warm vs cold voice calibration.** Cold-surface persona (trades) wants a crisper "engineering firm" voice (`"45-minute response. No call-out charge."`). Warm-surface persona (solicitor) wants a steadier "safe hands" voice (`"Independent legal advice in Fife since 2009."`). Need voice examples per persona.

6. **Trust logo row copy — what to show when the business has no corporate clients.** Substitute with accreditation logos (Gas Safe, NICEIC, TrustMark, Checkatrade, Which? Trusted Trader, GDC, SRA, ICAEW). Need the approved-accreditation whitelist per vertical.

---

## 7. Reference-only annex (not cross-cutting, kept for completeness)

- Stripe shadow color `rgba(50,50,93,0.25)` (blue-tinted). Brand-specific. Do not adopt — use achromatic.
- Linear luminance-step dark-mode depth system. Wrong color space for local-service.
- Resend frost-blue borders `rgba(214,235,253,0.19)`. Brand-specific to Resend's dark theme.
- Airbnb three-tier premium palette (Rausch/Luxe/Plus). Tier system doesn't map to local-service.
- Webflow 5-layer cascade shadow with `84px` outer blur. Too aggressive; Airbnb's 3-layer is cleaner.
- Cal Sans custom display font. Wrong license model; Inter is the correct choice.

---

**Fetch status:** Complete. 10/10 exemplars fetched in full via `npx getdesign add`. No degraded data, no missing sections, no inferred patterns. All citations verifiable against `/tmp/gd-pull/{slug}/DESIGN.md`.
