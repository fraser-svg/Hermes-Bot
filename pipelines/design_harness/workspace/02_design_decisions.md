# Design Decision Log — Master Template DESIGN.md

**Author:** `design-system-architect`
**Date:** 2026-04-13
**Status:** Phase-1 parallel draft. Research integration pending from `market-researcher`.

## Inputs used in this pass

- `prompts/website_builder.md` — existing YC-aesthetic priors (Inter, cold gray canvas, utility blue, 90/10 color rule, anti-slop table, micro-elevation shadows, 650px body cap, rigid spacing scale).
- `.claude/skills/design-md-authoring/SKILL.md` — Stitch 9-section schema contract.
- `_workspace/template/DESIGN_existing_stripe_reference.md` — structural exemplar (not aesthetic template).

## Decisions

### D-01 — Single aesthetic direction, not three personas
**Decision:** Kill the old Bright & Bold / Copper & Cream / Safety First persona split. One voice: **Cold Engineering Neutral**.
**Why:** Skill contract mandates "one aesthetic direction at the master-template layer." Priors in `website_builder.md §DESIGN PHILOSOPHY` already deprecated personas ("Unified — No Personas"). Local-service sites convert best with decisive direction; three personas was a hedge.
**Source:** `prompts/website_builder.md` line 154 ("Design System (Unified - No Personas)").

### D-02 — Canvas = `#FFFFFF`, alt = `#F9FAFB`, not `#F3F4F6`
**Decision:** Promoted `#F9FAFB` to `--surface-alt` (alternating sections), demoted `#F3F4F6` to `--surface-sunken` (inputs, cards internal).
**Why:** `#F9FAFB` is 1% above `#F3F4F6` in luminance — barely perceptible alternation is what we want. `#F3F4F6` reads as a genuine sunken surface. Priors used `#F3F4F6` as alt, but with 3 surface tokens available, we can layer tighter.

### D-03 — Accent primary = `#2563EB`, not business-category-driven
**Decision:** One accent color for the master template: Electric Blue `#2563EB`. Business-category accent overrides (indigo, teal, orange) moved to per-business config layer, not DESIGN.md.
**Why:** Stitch schema wants one direction. Category-color logic is a generate-time decision, not a design-system decision. DESIGN.md defines the default; `business_details.json` can override via a `--accent-primary` CSS var swap without changing the template.
**Contrast check:** `#2563EB` on `#FFFFFF` = 5.2:1 ✓ (passes AA). White text on `#2563EB` = 5.2:1 ✓.

### D-04 — Ink scale expanded from 2 to 5 tokens
**Decision:** Priors had `--ink` + `--ink-muted`. New scale: `--ink-strong` / `--ink-body` / `--ink-muted` / `--ink-subtle` / `--ink-disabled`.
**Why:** 5 layers lets typography + form states share a coherent ramp. Every token contrast-checked against canvas. `--ink-disabled` (3.2:1) explicitly flagged as large-text only.

### D-05 — Signal colors split from accent
**Decision:** Added `--signal-success` (#047857) and `--signal-urgent` (#B91C1C) as dedicated tokens. Priors had `--urgent` only.
**Why:** "Gas Safe registered" / "DBS checked" badges need a trust-green that isn't the accent. Urgent red stays red. Neither gets used decoratively — both are anti-slop guarded.

### D-06 — Typography weights = 400/500/600/700/800, drop 100–300
**Decision:** Load Inter Variable but expose only `400;500;600;700;800`. No weight 300 for headlines (Stripe does this — wrong for local services, reads as whispered/fashionable).
**Why:** Local-service conversion needs confident, heavy headlines. Stripe's 300-weight display is the opposite of what a Dunfermline plumber needs. Priors explicitly mandate 800 on h1 — preserved.

### D-07 — 3 display font sizes, not a full 10-step scale
**Decision:** h1/h2/h3/h4 + lead/body/small/micro. No display-large or display-small extras.
**Why:** Single-page sites don't need 10 type roles. Every extra role is a slop vector. Matches priors exactly.

### D-08 — Layered micro-elevation, 4 levels
**Decision:** `--elev-1` → `--elev-4`, all using `rgba(10,15,26,*)` (neutral blue-black) layered shadows. No colored shadows ever.
**Why:** Direct port of priors rule 6. Stripe reference uses blue-tinted shadows for brand feel — we explicitly don't, because accent-tinted shadows are the #1 AI slop tell on card grids.

### D-09 — Radius ladder: 6 / 8 / 16
**Decision:** `--radius-sm: 6px` (badges), `--radius-md: 8px` (buttons, inputs), `--radius-lg: 16px` (cards).
**Why:** Priors use 8px buttons + 16px cards. Added 6px for badges to avoid pill shape while staying tighter than the button. Consistent ladder.

### D-10 — Dark mode is mirror, not alternative palette
**Decision:** `preview-dark.html` uses the same token names with inverted hex. `--accent-primary` brightens to `#3B82F6` to hold contrast against `#0A0F1A` canvas.
**Why:** One system, two surface modes. Template-engineer inherits dark mode for free via CSS var swap.

### D-11 — No eyebrow text above hero h1
**Decision:** Component spec explicitly rejects eyebrow/pre-headline in the hero. Eyebrow role exists, but only for section eyebrows below hero.
**Why:** Priors Rule 5 "anti-competition rules" — eyebrow above hero splits attention and kills conversion. Carried forward verbatim.

### D-12 — 650px body cap, no exceptions
**Decision:** Applied to hero lead, about paragraphs, card descriptions, reviews, FAQ answers. Headings may span wider.
**Why:** Priors Golden Rule 2. Non-negotiable readability constraint.

### D-13 — Spacing scale frozen to 10 steps
**Decision:** `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128`. Any other value is a bug.
**Why:** Priors rigid scale. Enforced as lint-able constraint in §5.

### D-14 — Mobile nav = logo + tel icon + CTA, no drawer
**Decision:** Explicit ban on hamburger drawer menus in §4 Navigation and §8 Collapsing.
**Why:** Priors Rule 5 mobile constraints. Drawers are slop for single-page local-service sites — every link is visible if the page is done right.

## Schema conformance check

- [x] §1 Visual Theme & Atmosphere
- [x] §2 Color Palette & Roles (contrast table)
- [x] §3 Typography Rules (hierarchy table)
- [x] §4 Component Stylings (buttons, cards, inputs, nav, links, badges, dividers — all with states + anti-slop rejections)
- [x] §5 Layout Principles (spacing scale, grid, breakpoints)
- [x] §6 Depth & Elevation (4-level shadow system)
- [x] §7 Do's and Don'ts (paired anti-slop table)
- [x] §8 Responsive Behavior (breakpoints, touch targets, collapsing matrix)
- [x] §9 Agent Prompt Guide (color reference + CSS var block + ready-to-paste components + prompt boilerplate)

## Open items — pending research handoff

1. **Trust-signal palette.** Waiting on `market-researcher` for whether local-service sites that convert actually use green checkmarks or "verified" badges, or if they're a SaaS-era cargo cult.
2. **Hero photo treatment.** Priors mandate dark photo + gradient overlay. Research may reveal that category-leading sites (e.g. Benjamin Franklin Plumbing) have shifted to product hero or illustration — will validate.
3. **Testimonial format.** Currently italic body + attribution. Research may show stat-card testimonials convert better.
4. **Stats block density.** 4-col trust block is assumed. Research may argue for 3-col with more breathing room.
5. **Accent saturation.** `#2563EB` is a safe default. Research may push toward `#0A84FF` (Apple-system blue) or near-black primary CTAs, which priors flag as a viable alternative for trades.

Each open item will be resolved + logged in an "Integration Pass" section once researcher sends findings via SendMessage.

---

## Integration Pass — 2026-04-13

Source: `_workspace/template/01_research.md` (10 VoltAgent exemplars, all fetched in full: Stripe, Linear, Vercel, Cal.com, Resend, Intercom, Airbnb, Notion, Mintlify, Webflow).

Resolved every Phase-1 open item + every research §5 open question. Every change cites the research source.

### I-01 — Drop Inter weight `800`, adopt three-weight system
**Change:** h1 is now weight `700` (was `800`). h2 is weight `600` (was `700`). Font load simplified to `400;500;600;700`.
**Source:** Research §2.3 (Vercel 400/500/600, Mintlify 400/500/600, Linear 400/510/590). 7/10 exemplars cap at 600. §5 Q1.
**Supersedes:** D-06.

### I-02 — Primary CTA default = warm near-black `#0A0F1A`
**Change:** `--accent-primary` swapped from Electric Blue `#2563EB` to warm near-black `#0A0F1A`. Electric Blue retained as optional `--accent-vertical` override.
**Why:** Research §2.4 — Cal.com `#242424`, Mintlify `#0d0d0d`, Airbnb `#222222`, Vercel `#171717`, Intercom `#111111`. 5/10 exemplars use dark solid as primary CTA. §5 Q2.
**Supersedes:** D-03.

### I-03 — Single DESIGN.md with `[data-persona]` toggle
**Change:** `--surface-alt` = `#F9FAFB` (cold default) or `#F6F5F4` (warm, `html[data-persona="warm"]`).
**Why:** Research §2.1 + §4.9 — Notion warm `#f6f5f4`, Intercom warm `#faf9f6`. Persona-lock is the go-to pattern for "safe hands" verticals. §5 Q3.
**Verticals:** Cold — trades, HVAC, cleaning, pest, locksmith, emergency, IT. Warm — solicitors, accountants, dentists, vets, photographers, trainers.
**Supersedes:** D-02.

### I-04 — Shadow-as-border adopted as canonical on cards
**Change:** `.card` spec uses `box-shadow: 0 0 0 1px rgba(10,15,26,0.06)` as ring layer of `--elev-2`, replacing `border: 1px solid`. Real `1px solid` borders retained on inputs.
**Why:** Vercel signature, confirmed by Cal.com/Linear/Resend. Research §2.4 + §5 Q4.

### I-05 — Canonical 3-layer card shadow adopted verbatim
**Change:** `--elev-2` = `0 0 0 1px rgba(10,15,26,0.06), 0 2px 4px rgba(10,15,26,0.04), 0 8px 16px -4px rgba(10,15,26,0.08)`. Hard opacity ceiling: no individual layer > 0.10.
**Why:** Research §2.4 synthesized formula (Airbnb + Vercel) + §2.6 opacity rule. §5 Q6.

### I-06 — Border expressed as opacity rule, not fixed hex
**Change:** `--border-hairline: rgba(10,15,26,0.06)`. `--border-input: #E5E7EB` retained as solid for form debuggability.
**Why:** Research §2.2 — Mintlify 0.05, Notion 0.1, Vercel 0.08. Renders correctly on white, `#F9FAFB`, `#F6F5F4`, inverse.

### I-07 — Ink ramp extended to 5 steps
**Change:** Added `--ink-tertiary: #9CA3AF` for star rows, review meta, fine-print.
**Why:** Research §2.2 — Stripe/Vercel/Mintlify/Notion all split tertiary from body.

### I-08 — `font-feature-settings: "cv11", "ss01"` enforced
**Change:** Global on `html`. Dropped hallucinated `ss03` from Phase-1 draft (Inter has no ss03).
**Why:** Research §2.3 + §4.10 — 8/10 exemplars enable a stylistic set.

### I-09 — Uppercase-mono eyebrow label adopted
**Change:** Added Mono Eyebrow row to §3 hierarchy table. JetBrains Mono 12px 500 `0.08em` uppercase `--ink-muted`. `.eyebrow-mono` utility in §9.
**Why:** Research §2.3 + §4.11 — Mintlify/Vercel/Resend/Linear/Stripe all use this pattern for section hats.

### I-10 — Color-only hover forbidden; micro-transform required
**Change:** `.btn-primary` hover is `transform: translateY(-1px) scale(1.01)`. Active `scale(0.98)`.
**Why:** Research §4.5 — Intercom scale 1.1, Notion scale 1.05, Airbnb scale 0.92.

### I-11 — One hero atmospheric gradient permitted
**Change:** §7 now allows exactly ONE gradient site-wide: a wash behind the hero background image, under the overlay.
**Why:** Research §5 Q7 + Mintlify §1 — single atmospheric wash reads premium, not slop. Hard-limited to hero only.

### I-12 — Pure `#000000` forbidden; 12 anti-slop rows added
**Change:** §7 Do/Don't table extended with research §4.1–4.12 verbatim, each cited.
**Why:** Research §4 provides numbered anti-slop list with ≥3 exemplar sources per rule.

### I-13 — h1 clamp floor lowered to `2rem` (32px)
**Change:** `clamp(2rem, 6vw, 4.25rem)`. Previously `clamp(2.5rem, 6vw, 4.5rem)`.
**Why:** Research §2.7 — Stripe 56→48→32, Linear 72→48→32. Previous 40px floor cut off the mobile step.

### I-14 — Tracking floor `-0.03em` on narrow mobile
**Change:** Below 32px absolute, clamp letter-spacing to `-0.03em` minimum.
**Why:** Research §2.3 Linear proportional-tracking rule.

## Resolved Phase-1 open items

- [x] Trust-signal palette — research confirms green checkmarks on verified badges (Mintlify/Cal.com/Notion/Intercom). `--signal-success #047857` retained.
- [x] Hero photo treatment — dark photo + gradient overlay retained, plus single atmospheric wash now permitted (I-11).
- [x] Testimonial format — italic body + attribution retained. Airbnb precedent (research §2.4). Truncation rule deferred to copywriter.
- [x] Stats block density — 4-col confirmed by research §3 metric cluster pattern.
- [x] Accent saturation — resolved via I-02: dark solid default, Electric Blue optional override.

## Follow-ups for downstream agents

**`conversion-copywriter`:**
- Research §3 trust signals inventory + §6 copywriter questions (eyebrow bank, 2-word CTA matrix, metric ribbon, review truncation, voice calibration, accreditation whitelist per vertical).
- Mono eyebrow slot exists — copywriter owns the copy bank.
- CTA pattern: verb-led, 2-word max, imperative. Trades "Get Quote"/"Call Now", Medical "Book Visit"/"Check Availability", Legal "Free Consult"/"Call Direct".

**`template-engineer`:**
- Token cheatsheet = §9 of DESIGN.md. Copy CSS var block directly into template `<style>`.
- Persona toggle: `<html data-persona="cold">` (default) or `"warm"` — map from `business_details.json[business_category]` per I-03 vertical list.
- Per-vertical accent override: when JSON has `"accent_color"`, alias `--accent-primary` to that value. Otherwise dark solid default.
- Card: no `border` property. `box-shadow: var(--elev-2)` does ring + lift in one declaration.
- Font load: `Inter:wght@400;500;600;700` + `JetBrains Mono:wght@400;500`. Nothing else.
- `font-feature-settings: "cv11", "ss01"` on `html` selector — non-negotiable.

## Integration Pass

*To be populated after `market-researcher` delivers `_workspace/template/01_research.md`.*
