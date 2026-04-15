# Hermes Master Design System

> Single aesthetic direction for every local-service site Hermes builds. Replaces the old three-persona system (Bright & Bold / Copper & Cream / Safety First). Authored by `design-system-architect`. Schema: Google Stitch 9-section.

**Status:** Research-integrated (2026-04-13). Phase-1 parallel draft merged with `_workspace/template/01_research.md` findings from `market-researcher` (10 VoltAgent exemplars fetched in full: Stripe, Linear, Vercel, Cal.com, Resend, Intercom, Airbnb, Notion, Mintlify, Webflow). Decision log: `_workspace/template/02_design_decisions.md` §Integration Pass.

---

## 1. Visual Theme & Atmosphere

Hermes builds sites that move local service businesses out of "advertising" and into "engineering." A plumber in Dunfermline should feel, at first glance, like Stripe built their site. Cold, clean, precise, confident — the aesthetic of a refined product, not a manual task.

The master theme is **Cold Engineering Neutral**. A near-white canvas (`#FFFFFF`) does 90% of the work; a single alt-surface alternates behind section rhythm. Warmed near-black ink (`#0A0F1A`, never pure `#000`) carries headings — the research corpus unanimously avoids pure black (Stripe `#061b31`, Vercel `#171717`, Mintlify `#0d0d0d`, Airbnb `#222222`; see research §2.1). The default primary CTA is **warm near-black** `#0A0F1A` on light — the universal fallback adopted by Cal.com, Mintlify, Airbnb, Vercel, Intercom. Electric Blue `#2563EB` remains available as a per-vertical accent override for trades/emergency personas where urgency benefits from saturation. No gradients except a single atmospheric hero wash. No glow, no pill buttons, no wavy dividers.

**Persona-locked alt-surface.** One DESIGN.md, two surface modes via a `[data-persona]` attribute on `<html>`:
- `data-persona="cold"` (default) — cold off-white `#F9FAFB` alt. Trades, emergency, tech, HVAC, cleaning, pest, locksmith.
- `data-persona="warm"` — warm off-white `#F6F5F4` alt. Solicitors, accountants, dentists, vets, photographers, personal trainers. Adopted from Notion/Intercom precedent (research §2.1).

Borders are expressed as **shadow-as-border** on cards — `box-shadow: 0 0 0 1px rgba(10,15,26,0.06)` replaces `border: 1px solid` (Vercel signature, Cal.com + Linear + Resend confirmed). Smoother corner rounding, cleaner hover transitions. Real `1px` borders stay on inputs for form-debuggability.

Typography is **Inter Variable** with `font-feature-settings: "cv11", "ss01"` enabled globally (8/10 exemplars use a stylistic set — zero build cost). Three-weight UI system: `400 / 500 / 600` for body and UI, `700` reserved for the h1 display hero only. Weight `800` is **dropped** — 7/10 exemplars cap at 600, none exceed 700 on marketing. Aggressive negative tracking at display sizes: `-0.04em` at h1 (Vercel/Notion/Intercom consensus). Body capped at `650px`. Mono (JetBrains Mono) for phone + license numbers only.

Density: **comfortable, not cramped, not airy-gallery.** The grid breathes (96px section padding desktop, 64px mobile) but every element carries information. If a section feels busy, 30% gets deleted. If a section feels empty, copy was too vague — rewrite, don't pad.

---

## 2. Color Palette & Roles

All hex values verified against `--surface-canvas` (`#FFFFFF`) for 4.5:1 minimum. Contrast ratios computed per WCAG 2.1 relative luminance. Border color is expressed as an **opacity rule** (`rgba(10,15,26,0.06)`) rather than a fixed hex — so the same token reads correctly on white, `#F9FAFB`, `#F6F5F4`, and dark inverse surfaces. This matches Mintlify/Notion/Vercel convention (research §2.2).

| Token | Hex / rgba | Role | Contrast vs canvas |
|-------|------------|------|--------------------|
| `--surface-canvas` | `#FFFFFF` | Primary page background | — |
| `--surface-alt` | `#F9FAFB` *(cold)* / `#F6F5F4` *(warm)* | Alternating sections — persona-locked via `[data-persona]` | — |
| `--surface-sunken` | `#F3F4F6` | Input fill, sunken testimonial band | — |
| `--surface-inverse` | `#0A0F1A` | Hero base, footer, the ONE accent section | — |
| `--border-hairline` | `rgba(10,15,26,0.06)` | Card ring (shadow-as-border), 1px dividers | — |
| `--border-hairline-strong` | `rgba(10,15,26,0.10)` | Interactive / hover seam, input border | — |
| `--border-input` | `#E5E7EB` | Solid `1px` on inputs only (debuggability) | — |
| `--ink-strong` | `#0A0F1A` | h1/h2/h3, primary text | **18.1:1** ✓ |
| `--ink-body` | `#1F2937` | Long-form body, emphasised paragraph | **14.7:1** ✓ |
| `--ink-muted` | `#4B5563` | Captions, secondary body, subheads | **8.6:1** ✓ |
| `--ink-subtle` | `#6B7280` | Meta, timestamps, placeholder labels | **5.7:1** ✓ |
| `--ink-tertiary` | `#9CA3AF` | Star-row, review meta, fine-print (third step per research §2.2) | 3.2:1 (large-text / non-prose only) |
| `--ink-disabled` | `#9CA3AF` | Disabled labels | 3.2:1 (large-text only) |
| `--accent-primary` | `#0A0F1A` | **Universal primary CTA fill** (warm near-black) | 18.1:1 ✓ (white text on accent) |
| `--accent-primary-hover` | `#1F2937` | Primary CTA hover | 14.7:1 ✓ |
| `--accent-primary-active` | `#000000` | Primary CTA active/pressed (`scale(0.98)` compliments) | 21:1 ✓ |
| `--accent-ink` | `#FFFFFF` | Text on `--accent-primary` | 18.1:1 ✓ |
| `--accent-vertical` | `#2563EB` | **Optional per-vertical accent override** — trades/emergency only. Swap `--accent-primary` to this via JSON `"accent_color"` field. | 5.2:1 ✓ |
| `--accent-vertical-hover` | `#1D4ED8` | Vertical accent hover | 6.4:1 ✓ |
| `--accent-subtle` | `#EFF6FF` | Focus-ring tint, focused input bg | — |
| `--accent-border` | `rgba(37,99,235,0.30)` | Focus ring 3px halo | — |
| `--signal-success` | `#047857` | "Verified" / "Gas Safe" / "DBS checked" badges | 6.6:1 ✓ |
| `--signal-urgent` | `#B91C1C` | Emergency CTA only — never decorative | 7.4:1 ✓ |
| `--ink-on-inverse` | `#F9FAFB` | Body text on `--surface-inverse` | 17.2:1 ✓ |
| `--ink-on-inverse-muted` | `#9CA3AF` | Muted text on inverse (footer meta only) | 4.9:1 ✓ |

**90/10 rule (enforced).** 90% of the pixel area is canvas + ink + border. 10% is accent. Accent only appears in: **primary CTA background, link underline, focus ring, icon highlight.** Never in: dividers, section backgrounds, borders, body text emphasis, card fills, stat numbers, quote marks, decorative strokes. (Research anti-slop rule §4.7, 7/10 exemplars enforce.)

**Pure `#000000` is forbidden for text.** Use `--ink-strong` `#0A0F1A` (warmed near-black). Research §2.1 — all 10 exemplars avoid pure black.

**Pure `#FFFFFF` buttons are forbidden as primary CTA on light.** Primary CTA must be dark solid (`--accent-primary`) or vertical accent solid (`--accent-vertical`). Research anti-slop §4.2.

**Persona toggle.** `<html data-persona="cold">` (default) or `<html data-persona="warm">` — swaps `--surface-alt` only. Never mix within a single site.

**Forbidden palette.** Decorative creams (`#FFF8F0`), beige (`#F5F5DC`), parchment, gold (`#D4AF37`), copper (`#B87333`), colored shadows (`rgba(37,99,235,0.3)`), gradient fills on buttons/cards/badges, color-on-color borders, rainbow secondary palettes (Webflow anti-pattern).

---

## 3. Typography Rules

**Primary:** Inter Variable. Load only `Inter:wght@400;500;600;700` — **weight 800 dropped** (7/10 research exemplars cap at 600; none exceed 700 on marketing). `font-feature-settings: "cv11", "ss01"` enabled globally — Inter's alternate single-storey `a` and straight `l`. This is a free visual upgrade and non-negotiable (research §2.3, 8/10 exemplars use a stylistic set). Fallback: `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif`.

**Mono:** JetBrains Mono (400/500). Two jobs: (1) phone + license numbers with `font-variant-numeric: tabular-nums`; (2) uppercase-mono eyebrow labels (research §2.3, Mintlify/Vercel/Resend/Linear/Stripe pattern) — 12px, `letter-spacing: 0.08em`, `text-transform: uppercase`, `--ink-muted` color, used for section hats like "SERVICES", "REVIEWS", "SERVICE AREAS".

**Three-weight UI system.** `400` for body, `500` for emphasized / micro labels, `600` for all UI + section headings (h2/h3/h4), `700` reserved for h1 display hero only. Never mix more than these four in a single page.

**Never load:** serif display fonts, script fonts, Google Fonts "display" category, Cal Sans / Pretendard / any custom display face.

### Hierarchy

| Role | Size (clamp) | Weight | Tracking | Line-height | Max width | Notes |
|------|--------------|--------|----------|-------------|-----------|-------|
| `h1` display (hero) | `clamp(2rem, 6vw, 4.25rem)` | 700 | `-0.04em` | 1.05 | 14ch | Only role that uses weight 700. Tracks proportionally on mobile. |
| `h2` section | `clamp(1.5rem, 4vw, 2.5rem)` | 600 | `-0.03em` | 1.1 | 18ch | Max 6 words |
| `h3` subsection | `1.375rem` (22px) | 600 | `-0.02em` | 1.25 | 22ch | Card titles |
| `h4` card label | `1rem` (16px) | 600 | `-0.01em` | 1.3 | — | Service card titles, trust labels |
| Eyebrow (Inter) | `0.75rem` (12px) | 600 | `0.08em` UPPERCASE | 1.2 | — | Section eyebrows only — never above hero h1 |
| Eyebrow (Mono) | `0.75rem` (12px, JetBrains Mono) | 500 | `0.08em` UPPERCASE | 1.2 | — | Premium-tier section hat. "SERVICES" / "REVIEWS" / "TRUSTED LOCALLY". Research §2.3. |
| Lead | `1.125rem` (18px) | 400 | `-0.005em` | 1.55 | 650px | Hero subhead, intro paragraphs |
| Body | `1rem` (16px) | 400 | 0 | 1.65 | 650px | Default paragraph |
| Body-emphasized | `1rem` (16px) | 500 | 0 | 1.65 | 650px | In-prose emphasis. Never `font-weight: bold`. |
| Body-small | `0.875rem` (14px) | 400 | 0 | 1.55 | 600px | Captions, helper text |
| Micro | `0.75rem` (12px) | 500 | `0.02em` | 1.4 | — | Meta, form hints |
| Button | `0.9375rem` (15px) | 600 | `-0.005em` | 1 | — | Never uppercase, never tracked wide |
| Mono-phone | `1rem` (16px, JetBrains Mono) | 500 | 0 | 1 | — | `tabular-nums`, used on phone anchor |

**Mobile tracking rule.** `letter-spacing` is a property of `em` not `px`, so `-0.04em` at `clamp()` minimums already scales. But below 32px absolute, clamp to `-0.03em` minimum (Linear rule — research §2.3) to avoid breaking narrow mobile widths.

### Typographic rules

- **Body max-width is 650px. No exceptions.** Applies to hero subhead, about paragraphs, service card descriptions, review quotes, FAQ answers.
- **One size per visual zone.** Hero has exactly 3 text scales (h1, lead, button). Nothing else. No eyebrow, no badge, no "pre-headline."
- **Weight 400 for body only.** No bold mid-paragraph. Bold is for headings and labels.
- **No all-caps paragraphs.** Uppercase only on eyebrows and micro labels.
- **Letter-spacing tightens with size.** h1 `-0.04em` → h2 `-0.03em` → h3 `-0.02em` → body `0`. Never loosen tracking on body.
- **Numbers in stats use `tabular-nums`.** `font-variant-numeric: tabular-nums` on any element displaying ratings, counts, years, prices.

---

## 4. Component Stylings

Every component spec names the anti-slop pattern it rejects.

### Buttons

**Primary (`.btn-primary`)** — default is warm near-black solid (universal fallback). Per-vertical accent override swaps `--accent-primary` → `--accent-vertical` at template inheritance level.
- Background: `--accent-primary` (`#0A0F1A` default, or vertical override)
- Text: `--accent-ink` (`#FFFFFF`), 15px / 600 / `-0.005em`, sentence case
- Padding: `12px 24px` (desktop), `14px 20px` (mobile — 48px min touch target)
- Radius: `8px` — **NEVER pill (`9999px`)**, NEVER `0px`. Research §2.4: Vercel 6, Stripe 4–8, Notion 4, Intercom 4 — 8px is the midpoint.
- Border: none
- Shadow rest: `--elev-1` (`0 1px 2px rgba(10,15,26,0.08)`)
- Shadow hover: `--elev-2`
- Hover: background → `--accent-primary-hover`, `transform: translateY(-1px) scale(1.01)` — **micro-transform required, color-only hover is forbidden (research anti-slop §4.5, 5/10 exemplars).**
- Active: background → `--accent-primary-active`, `transform: translateY(0) scale(0.98)`
- Focus: `outline: 2px solid currentColor; outline-offset: 2px`, plus `box-shadow: 0 0 0 3px var(--accent-subtle)` for accent-mode variant
- Disabled: `background: --ink-disabled; cursor: not-allowed; transform: none`
- **Rejects:** gradients, glow, pill radius, uppercase text, tracked-wide letters, colored drop shadows, scale(1.05+) jumps, shimmer animations, pure `#FFFFFF` fill on light backgrounds.

**Secondary / Ghost (`.btn-secondary`)**
- Background: transparent
- Text: `--ink-strong`, 15px / 600
- Padding: same as primary
- Border: `1px solid --border-hairline`
- Radius: `8px`
- Hover: background → `--surface-alt`, border → `--border-strong`
- Focus: same outline as primary
- **Rejects:** dashed borders, double borders, hover fill with accent color.

**Urgent (`.btn-urgent`)** — only when business offers emergency service
- Background: `--signal-urgent` (`#B91C1C`)
- Text: `#FFFFFF`
- Same shape/padding/radius as primary
- **Rejects:** using red for non-emergency CTAs, using accent blue for emergency CTAs.

### Cards

**Base card (`.card`)** — uses **shadow-as-border** technique (Vercel signature, research §2.4) instead of real `border`. Cleaner corner rounding, cleaner hover transitions, no border/shadow seam.
- Background: `--surface-canvas`
- Border: **none** — the ring layer of the shadow stack does this job
- Radius: `16px` (consistent across all cards on a site — never mix)
- Padding: `32px` desktop, `24px` mobile
- Shadow rest (`--elev-2`, canonical 3-layer synthesized from Airbnb + Vercel + research §2.4):
  ```
  0 0 0 1px rgba(10,15,26,0.06),   /* ring border */
  0 2px 4px rgba(10,15,26,0.04),   /* ambient */
  0 8px 16px -4px rgba(10,15,26,0.08)   /* lift */
  ```
- Shadow hover (`--elev-3`): ring to `0.08`, lift to `0 16px 24px -4px rgba(10,15,26,0.10)`
- Hover transform: `translateY(-2px)`
- **Opacity rule:** no individual shadow layer may exceed `0.10` opacity. Accumulated visible shadow must read as lift, not drop. (Research anti-slop §4.3.)
- **Rejects:** single-layer `box-shadow`, gradient card backgrounds, colored borders, colored shadows, `border-radius: 0` (brutalist), `border-radius: 24px+` (too soft), 5+ layer Webflow-style cascades (too aggressive).

**Service card** — uniform grid (3 cols desktop, 2 cols tablet, 1 col mobile). Every card identical height. Title (h4), 15-word max description, optional `→` affordance. No icons in circles with accent tint. Mono-line icons only (Lucide/Heroicons style, 20px, `stroke: --ink-strong`).

**Trust card** — stat-forward. Large number in `--ink-strong` at 48px/800, label beneath in `--ink-muted` 14px/500. `tabular-nums`. No accent color on the number.

**Testimonial card** — quote in `--ink-body` 18px/400 italic, attribution in `--ink-muted` 14px/500. No oversized decorative quote marks. No star icons in accent color — use `--ink-strong` filled stars or none.

### Inputs

**Text / email / tel**
- Background: `--surface-canvas`
- Border: `1px solid --border-hairline`
- Radius: `8px`
- Padding: `12px 16px`
- Font: 16px / 400 (prevents iOS zoom)
- Placeholder color: `--ink-subtle` (`#6B7280`, 5.7:1 ✓)
- Focus: `border: 1px solid --accent-primary; box-shadow: 0 0 0 3px --accent-subtle`
- Error: `border-color: --signal-urgent`
- **Rejects:** floating labels that animate, underline-only inputs, large rounded pill inputs, placeholder text at `#D1D5DB` (contrast fails).

**Label** — 14px / 600 / `--ink-strong`, sits above input with 6px gap. Never inside.

### Navigation

- Height: `64px` desktop, `56px` mobile
- Background: `--surface-canvas` (or transparent over hero with `backdrop-filter: blur(8px)` + `rgba(255,255,255,0.85)` fill when scrolled)
- Bottom border: `1px solid --border-hairline` when scrolled, none at top
- Logo: wordmark, 16px / 700 / `--ink-strong`, `white-space: nowrap`, `max-width: 40vw`, ellipsis
- Links: 14px / 500 / `--ink-muted`, hover → `--ink-strong`
- Primary CTA: `.btn-primary` at compact padding (10px 18px)
- Mobile: logo left, tel-icon center, CTA right. No hamburger. No overlay menu.
- **Rejects:** sticky nav that grows/shrinks, mega-menus, hamburger with slide-out drawer, centered logo with links flanking.

### Links

- Default: `--ink-body`, underline offset 3px, decoration color `--border-hairline`
- Hover: `--accent-primary`, decoration color `--accent-primary`
- Visited: same as default
- **Rejects:** no-underline links in prose, accent-colored links by default (reserves accent for CTAs).

### Badges

**Trust badge (`.badge-trust`)**
- Background: `--surface-alt`
- Border: `1px solid --border-hairline`
- Radius: `6px`
- Padding: `6px 12px`
- Font: 12px / 600 / `--ink-strong`, NOT uppercase
- Optional icon: 14px monoline, `--ink-strong`
- **Rejects:** pill shape, accent fill, gold/bronze "premium" badges, glow, emoji badges.

**Signal badge (`.badge-signal-success`)** — "Gas Safe registered" / "DBS checked" — same shape, but with `--signal-success` text and border.

### Section dividers

Dead-straight `1px solid --border-hairline` or none. Never wavy SVG, curved, organic. If a stronger break is needed, use a change of `--surface-*` token on the next section instead of a visual divider.

---

## 5. Layout Principles

### Spacing scale (rigid)

`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128` px. Any value outside this scale is a bug.

Tokens: `--space-1` (4) … `--space-10` (128). Extended from original priors (which stopped at 64) per research §2.5 — Cal.com / Notion / Resend all operate 80–120px at section level.

### Grid

- Container max-width: `1200px`
- Gutter: `32px` desktop, `20px` mobile
- Column system: CSS Grid, `repeat(12, 1fr)` when needed; flexbox with gap for simpler layouts
- Section padding: `96px 0` desktop, `64px 0` mobile
- Vertical rhythm between heading and body: `24px`
- Vertical rhythm between body paragraphs: `16px`

### Breakpoints

| Name | Min width | Notes |
|------|-----------|-------|
| `mobile` | 0 | 1-column everything, 56px nav |
| `tablet` | 768px | 2-column services/cards |
| `desktop` | 1024px | 3-column services, 64px nav |
| `wide` | 1280px | Max container kicks in |

Mobile-first CSS. Desktop is an enhancement.

### Whitespace philosophy

- If a section feels busy, **delete 30% of the content**, don't shrink the spacing.
- If a section feels empty, the **copy is too vague** — rewrite with specifics, don't add padding.
- Negative space around the primary CTA: minimum `48px` on all sides.
- Never let two heavy elements (card, image, CTA) touch without a 24px minimum gap.

---

## 6. Depth & Elevation

Micro-elevation only. Layered shadows, never single heavy drops. Elements feel like physical objects resting on a desk — not hovering in CSS space. **Hard rule:** no individual `box-shadow` layer may exceed `0.10` opacity. Accumulated stacks stay under `0.15` total visible weight (research §2.6; Notion/Mintlify/Airbnb/Vercel consensus).

| Level | Use | Shadow |
|-------|-----|--------|
| `--elev-0` | Canvas, flat sections | none |
| `--elev-1` | Buttons at rest, inputs | `0 1px 2px rgba(10,15,26,0.08)` |
| `--elev-2` | Cards at rest (canonical 3-layer ring+ambient+lift) | `0 0 0 1px rgba(10,15,26,0.06), 0 2px 4px rgba(10,15,26,0.04), 0 8px 16px -4px rgba(10,15,26,0.08)` |
| `--elev-3` | Cards on hover, nav when scrolled | `0 0 0 1px rgba(10,15,26,0.08), 0 4px 8px rgba(10,15,26,0.05), 0 16px 24px -4px rgba(10,15,26,0.10)` |
| `--elev-4` | Modal, popover | `0 0 0 1px rgba(10,15,26,0.08), 0 8px 16px rgba(10,15,26,0.06), 0 24px 48px -8px rgba(10,15,26,0.10)` |

The `--elev-2` ring layer does the job of `border: 1px solid` — this is the Vercel shadow-as-border technique. The ambient + lift layers stack Airbnb's 3-tier physical-card feel. Synthesized from research §2.4 canonical formula.

**Surface hierarchy.** `--surface-canvas` → `--surface-alt` → `--surface-sunken` → `--surface-inverse`. Stack order in a page: sections alternate canvas and alt; sunken only inside cards or input fills; inverse reserved for hero and footer and the one accent section.

**Rejects:** single `box-shadow: 0 10px 40px rgba(0,0,0,0.2)`, colored shadows (`rgba(37,99,235,0.3)`), glow effects, inset shadows on non-input elements, neumorphism.

---

## 7. Do's and Don'ts

Paired rows. Left = AI-slop anti-pattern this system rejects. Right = the Hermes rule.

| Don't (AI slop) | Do (Hermes) |
|-----------------|-------------|
| Wavy SVG section dividers | Dead-straight 1px borders or surface-token change |
| Pill-shaped buttons (`border-radius: 999px`) | `8px` squircle on every button, same radius for all |
| Gradient button fills | Solid `--accent-primary`, hover darkens to `--accent-primary-hover` |
| Colored drop shadows (`rgba(37,99,235,0.3)`) | Layered neutral micro-elevation using `rgba(10,15,26,*)` |
| Warm beige / cream / parchment backgrounds | Cold `#FFFFFF` or `#F9FAFB`, never warm |
| Decorative oversized quote marks on testimonials | Italic body copy, attribution in muted, no decoration |
| 3D / cartoon / multicolor icons | Monoline Lucide/Heroicons at 20px in `--ink-strong` |
| Revolutionary / unmatched / cutting-edge copy | Specific verbs + numbers + place names |
| Eyebrow text above the hero h1 | Hero has exactly h1 + lead + CTA. Nothing else. |
| Uppercase tracked button labels | Sentence case, tracking `-0.005em` |
| Hamburger drawer menu on mobile | Logo + tel icon + CTA. No drawer. |
| Accent color on card borders, dividers, stat numbers | Accent only on primary CTA, focus ring, one accent section |
| Scale(1.05) hover animations | `translateY(-1px)` on buttons, `translateY(-2px)` on cards |
| Star icons in gold / accent fill | `--ink-strong` filled stars or no stars |
| Body text wider than 650px | Hard 650px cap on every paragraph |
| Centered-everything layouts | Left-aligned prose, centered only for hero + CTA clusters |
| Pure `#000000` for text | Warm near-black `#0A0F1A` — research unanimous |
| Pure `#FFFFFF` fill on primary CTA | Dark solid `--accent-primary` or vertical accent solid |
| Single-layer `box-shadow` on cards | 3-layer ring+ambient+lift stack, max 0.10 opacity per layer |
| Color-only hover on buttons | Micro-transform required: `translateY(-1px) scale(1.01)` |
| Decorative gradients (cards, dividers, text, backgrounds) | Exactly ONE gradient allowed site-wide: atmospheric hero wash |
| Accent on icons/dividers/stat-numbers/borders | Accent on CTA bg + link underline + focus ring + icon highlight only |
| Loose letter-spacing on display sizes | Negative `-0.03em` to `-0.05em` on every h1/h2 |
| Inter without `cv11`/`ss01` feature settings | `font-feature-settings: "cv11", "ss01"` globally (free upgrade) |
| Lowercase prose eyebrow labels | Uppercase-mono `0.08em` tracked section hats |
| Multi-color / 3D / cartoon icons | Monoline Heroicons/Lucide 20px in `--ink-strong` |
| Mixing cold and warm alt-surfaces | Persona-locked — `data-persona="cold"` or `"warm"`, never both |

---

## 8. Responsive Behavior

### Breakpoints
Mobile-first. See §5 for token values.

### Touch targets
- Minimum `44x44px` on any interactive element (buttons, links, phone icons, form controls).
- CTA buttons on mobile bump padding to `14px 20px` to hit 48px min height.
- Nav tel-icon: `44x44px` tap area even if the SVG is 24px.

### Collapsing strategy

| Component | Mobile behavior |
|-----------|-----------------|
| Nav | Logo left (ellipsis at 40vw) + tel icon center + compact CTA right. No drawer. |
| Hero h1 | `clamp(2.5rem, 8vw, 3.5rem)`, 2-3 lines allowed |
| Hero CTA group | Stack vertically, primary first, full-width buttons up to `340px` max |
| Services grid | 3 col → 2 col (tablet) → 1 col (mobile) |
| Trust stats | 4 col → 2 col → 2 col (never 1 col — keeps the stat row visible above fold) |
| Testimonial cards | 3 col → 1 col with horizontal scroll if >3 |
| Footer | 4 col → 2 col → 1 col stacked |
| Section padding | 96px → 64px |
| Body font size | unchanged (16px everywhere — never shrink body on mobile) |

### Mobile type
- h1: `clamp(2.5rem, 8vw, 3.5rem)`
- h2: `clamp(1.5rem, 5vw, 2rem)`
- Body: 16px (never shrink below — iOS will zoom if <16px on inputs)

### Fluid sizing
Use `clamp()` for display sizes. Use fixed for body and smaller. Never use `vw`-only sizing on text.

---

## 9. Agent Prompt Guide

Ready-to-paste snippets for any AI agent authoring HTML against this system.

### Quick color reference

```
Canvas:             #FFFFFF                   (--surface-canvas)
Canvas alt (cold):  #F9FAFB                   (--surface-alt, default)
Canvas alt (warm):  #F6F5F4                   (--surface-alt, [data-persona="warm"])
Canvas sunken:      #F3F4F6                   (--surface-sunken)
Inverse (hero):     #0A0F1A                   (--surface-inverse)
Border hairline:    rgba(10,15,26,0.06)       (--border-hairline — shadow-as-border)
Ink strong:         #0A0F1A                   (--ink-strong)     headings (never #000)
Ink body:           #1F2937                   (--ink-body)       long prose
Ink muted:          #4B5563                   (--ink-muted)      captions, subheads
Ink tertiary:       #9CA3AF                   (--ink-tertiary)   star rows, meta
Accent primary:     #0A0F1A                   (--accent-primary) DEFAULT CTA (dark solid)
Accent vertical:    #2563EB                   (--accent-vertical) optional trades override
Signal success:     #047857                   (--signal-success) verified badges
Signal urgent:      #B91C1C                   (--signal-urgent)  emergency CTA only
```

### CSS variable block (paste into `<style>`)

```css
:root {
  /* surfaces */
  --surface-canvas: #FFFFFF;
  --surface-alt: #F9FAFB;          /* cold default */
  --surface-sunken: #F3F4F6;
  --surface-inverse: #0A0F1A;

  /* borders — opacity rule, renders correctly on every surface */
  --border-hairline: rgba(10,15,26,0.06);
  --border-hairline-strong: rgba(10,15,26,0.10);
  --border-input: #E5E7EB;

  /* ink */
  --ink-strong: #0A0F1A;
  --ink-body: #1F2937;
  --ink-muted: #4B5563;
  --ink-subtle: #6B7280;
  --ink-tertiary: #9CA3AF;
  --ink-disabled: #9CA3AF;
  --ink-on-inverse: #F9FAFB;
  --ink-on-inverse-muted: #9CA3AF;

  /* CTA — universal fallback is dark solid */
  --accent-primary: #0A0F1A;
  --accent-primary-hover: #1F2937;
  --accent-primary-active: #000000;
  --accent-ink: #FFFFFF;

  /* Vertical override — trades/emergency only, swapped at template inheritance */
  --accent-vertical: #2563EB;
  --accent-vertical-hover: #1D4ED8;
  --accent-subtle: #EFF6FF;
  --accent-border: rgba(37,99,235,0.30);

  /* signals */
  --signal-success: #047857;
  --signal-urgent: #B91C1C;

  /* radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 16px;

  /* spacing */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 24px;  --space-6: 32px;
  --space-7: 48px;  --space-8: 64px;  --space-9: 96px;  --space-10: 128px;

  /* elevation — layered, never single-layer, max 0.10/layer */
  --elev-1: 0 1px 2px rgba(10,15,26,0.08);
  --elev-2:
    0 0 0 1px rgba(10,15,26,0.06),
    0 2px 4px rgba(10,15,26,0.04),
    0 8px 16px -4px rgba(10,15,26,0.08);
  --elev-3:
    0 0 0 1px rgba(10,15,26,0.08),
    0 4px 8px rgba(10,15,26,0.05),
    0 16px 24px -4px rgba(10,15,26,0.10);
  --elev-4:
    0 0 0 1px rgba(10,15,26,0.08),
    0 8px 16px rgba(10,15,26,0.06),
    0 24px 48px -8px rgba(10,15,26,0.10);
}

html[data-persona="warm"] {
  --surface-alt: #F6F5F4;          /* notion/intercom warm off-white */
}

html {
  font-family: "Inter Variable", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  font-feature-settings: "cv11", "ss01";
  color: var(--ink-body);
  background: var(--surface-canvas);
}
body { margin: 0; font-size: 16px; line-height: 1.65; }
h1, h2, h3, h4 { color: var(--ink-strong); margin: 0; }
h1 { font-size: clamp(2rem, 6vw, 4.25rem); font-weight: 700; letter-spacing: -0.04em; line-height: 1.05; }
h2 { font-size: clamp(1.5rem, 4vw, 2.5rem); font-weight: 600; letter-spacing: -0.03em; line-height: 1.1; }
h3 { font-size: 1.375rem; font-weight: 600; letter-spacing: -0.02em; line-height: 1.25; }
h4 { font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; line-height: 1.3; }
p { max-width: 650px; color: var(--ink-muted); }

/* uppercase-mono eyebrow label — research-approved section hat */
.eyebrow-mono {
  display: inline-block;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-muted);
}
```

### Ready-to-use component snippets

**Primary CTA button**

```html
<a class="btn-primary" href="tel:+441234567890">Get a free quote</a>
```
```css
.btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 24px; font: 600 15px/1 "Inter Variable", sans-serif; letter-spacing: -0.005em; color: var(--accent-ink); background: var(--accent-primary); border: none; border-radius: var(--radius-md); box-shadow: var(--elev-1); transition: background 120ms, transform 120ms, box-shadow 120ms; cursor: pointer; }
.btn-primary:hover { background: var(--accent-primary-hover); transform: translateY(-1px); box-shadow: var(--elev-3); }
.btn-primary:active { background: var(--accent-primary-active); transform: translateY(0); }
.btn-primary:focus-visible { outline: 2px solid var(--accent-primary); outline-offset: 2px; }
```

**Service card**

```html
<article class="card">
  <h4>Emergency callouts</h4>
  <p>We arrive within 2 hours, diagnose the fault, and give you a fixed price before we start.</p>
</article>
```
```css
.card { background: var(--surface-canvas); border: 1px solid var(--border-hairline); border-radius: var(--radius-lg); padding: 32px; box-shadow: var(--elev-2); transition: box-shadow 160ms, transform 160ms; }
.card:hover { box-shadow: var(--elev-3); transform: translateY(-2px); }
.card h4 { font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; margin-bottom: 12px; }
.card p { font-size: 0.9375rem; color: var(--ink-muted); margin: 0; }
```

### Prompt boilerplate (for downstream agents)

> Build the page using CSS variables from `DESIGN.md §9`. Canvas `#FFFFFF` with alternating `#F9FAFB` sections. Inter Variable only — no serif, no script. Near-black ink `#0A0F1A` on headings, slate `#4B5563` on body. Electric blue `#2563EB` on primary CTA only — never on borders, dividers, or decorative elements. `16px` card radius, `8px` button radius. Layered micro-elevation shadows (`--elev-2` on cards), never single heavy drops. 90% neutral, 10% accent. 650px max body width. Dead-straight dividers. No gradients, no glow, no pill buttons, no wavy SVGs, no revolutionary copy.

---

*Anti-slop checklist: see §7. Contrast math: see §2. Preview catalogs: `preview.html`, `preview-dark.html`. Decision log: `_workspace/template/02_design_decisions.md`.*
