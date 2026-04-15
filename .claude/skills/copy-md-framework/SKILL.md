---
name: copy-md-framework
description: Authoring guide for COPY.md — the Hermes modular copy framework keyed to business_details.json slots. Use when conversion-copywriter is writing or editing COPY.md: hero headline formulas, trust block patterns, CTA variants, service block copy, FAQ templates, microcopy, category-aware slots (trades vs professional vs personal services). Enforces specificity, bans AI-slop vocabulary, and mirrors DESIGN.md section structure for pipeline parity.
---

# COPY.md Framework

Produces `COPY.md` at project root — a companion to `DESIGN.md` that the user explicitly requested to bring copywriting expertise onto the template team. Not part of the Stitch spec.

## Why COPY.md exists

`DESIGN.md` captures visual tokens. `COPY.md` captures copy tokens: headline formulas, proof patterns, CTA vocabulary, FAQ templates. Together they form the master brief that `core/prompts/website_builder.md` injects into every `core/generate.py` run.

Without this layer, copy falls back to AI-slop defaults ("Revolutionizing home services with cutting-edge solutions"). With it, every hero headline is a specific, measurable promise.

## Section schema (mirrors DESIGN.md for parity)

```markdown
# COPY.md

## 1. Voice & Tone
## 2. Headline Formulas (Hero)
## 3. Subheadline Patterns
## 4. CTA Vocabulary
## 5. Trust Block Patterns
## 6. Service Block Copy
## 7. FAQ Templates
## 8. Microcopy (forms, badges, labels, footer)
## 9. Banned Vocabulary
## 10. Slot Map (copy placeholder → business_details.json field)
```

## Slot conventions

Every formula uses `{{business.field_name}}` matching `core/references/business_details.json` exactly. Do not invent fields. Current schema:

| Slot | Source field |
|------|--------------|
| `{{business.name}}` | `business_name` |
| `{{business.city}}` | `city` |
| `{{business.phone}}` | `phone_number` |
| `{{business.category}}` | `business_category` |
| `{{business.years}}` | `years_experience` (optional) |
| `{{business.rating}}` | `rating` |
| `{{business.review_count}}` | `review_count` |
| `{{business.services[]}}` | `services_offered[]` |
| `{{business.license}}` | `license_number` (optional) |
| `{{business.reviews[]}}` | `google_reviews[]` |

Never add a slot without first confirming the source field exists.

## Headline formula principles

**Problem → outcome → proof.** Every hero headline anchors to a visitor problem, promises a concrete outcome, backs it with proof.

### Formula: Emergency/urgency (trades)
```
{{business.city}}'s [licensed/certified] {{business.category}}.
{outcome_promise} in {timeframe} or {guarantee}.
```

Example fill:
```
Dunfermline's licensed electrician.
Power back on in 60 minutes or the callout is free.
```

### Formula: Expertise/trust (professional services)
```
{proof_anchor} {{business.category}} for {target_audience_specific}.
Serving {{business.city}} since {{business.years}} years.
```

### Formula: Outcome (personal services)
```
{outcome_in_visitor_language}.
{{business.category}} in {{business.city}}, {proof_short}.
```

Include 3 variants per category so the builder can rotate.

## CTA vocabulary (banned phrases + approved)

| Banned | Why | Use instead |
|--------|-----|-------------|
| "Get started" | Generic, no outcome | "Book today", "Call {{business.phone}}" |
| "Learn more" | No commitment | "See pricing", "Check availability" |
| "Contact us" | No channel | "Call {{business.phone}}", "Book online" |
| "Click here" | Not copy | Use action verb tied to outcome |

## Trust block patterns

Trust is proof density. Mandatory modules in priority order:
1. **Phone primary** — large, click-to-call, tied to `{{business.phone}}`
2. **Rating + review count** — `{{business.rating}} ★ ({{business.review_count}} reviews)`
3. **Licence/certification** — `{{business.license}}` when present, skip when null
4. **Service radius** — geographic proof
5. **Years in business** — `{{business.years}}+ years` when ≥5
6. **Real testimonials** — `{{business.reviews[]}}` quoted, not paraphrased

## Banned vocabulary (the AI-slop list)

Full ban: `revolutionizing`, `unleash`, `seamless`, `robust`, `cutting-edge`, `solutions`, `empowering`, `synergy`, `best-in-class`, `world-class`, `leverage`, `holistic`, `premier`, `next-level`, `state-of-the-art`.

Context ban: `quality` (replace with measurable), `professional` (implied, redundant), `trusted` (show proof instead).

## Failure recovery

- `DESIGN.md` not yet written → draft voice-neutral formulas, flag for tone lock-in once design lands.
- Slot field missing from `business_details.json` → do not invent; request schema extension via orchestrator.

## Output checklist

- [ ] All 10 sections present
- [ ] 3 headline formulas per category (trades, professional, personal)
- [ ] Slot map matches `business_details.json` field names exactly
- [ ] Banned vocabulary list included
- [ ] Every formula has a worked example fill
- [ ] `_workspace/template/03_copy_decisions.md` logs banned-word sources and formula rationale
