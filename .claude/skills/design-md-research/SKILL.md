---
name: design-md-research
description: Methodology for mining the VoltAgent/awesome-design-md library (66 DESIGN.md exemplars from Stripe, Linear, Vercel, Airbnb, Cal.com, Intercom, Resend, etc.) to extract cross-cutting design patterns for local-service business websites. Use when the market-researcher agent is gathering exemplar tokens, layout rhythms, trust patterns, or anti-slop rules for the Hermes master template. Covers which exemplars to pick, how to extract, how to cite, how to handle conflicts.
---

# Design MD Research

Turns the VoltAgent DESIGN.md library into `_workspace/template/01_research.md` — a research brief that feeds `design-system-architect` and `conversion-copywriter`.

## Why this methodology exists

Random site surveys drift into cherry-picking. The VoltAgent library gives a fixed, curated corpus where every entry already uses the Stitch 9-section schema, so cross-cutting patterns are comparable. Pulling from a shared schema beats freestyling.

Source: https://github.com/VoltAgent/awesome-design-md — 66 curated DESIGN.md files. Raw files at `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/{site}/DESIGN.md` (check repo layout first).

## Exemplar shortlist (local-service fit)

Pick 8–12. Start from this shortlist; add or subtract with justification:

| Exemplar | Why for local service |
|----------|----------------------|
| **Stripe** | Trust hierarchy, premium neutral palette, proof density |
| **Linear** | Editorial density, precise type, zero-slop discipline |
| **Vercel** | Pure monochrome confidence, Geist engineering feel |
| **Cal.com** | Developer-oriented but warm; FAQ + booking conventions transfer well |
| **Resend** | Minimal dark accents + monospace — translates to "we're a refined product" |
| **Intercom** | Friendly-but-professional palette, conversational tone cues for copywriter |
| **Airbnb** | Photography-driven trust, rounded UI warmth (only when the business is personal-service tier) |
| **Notion** | Soft surfaces + serif headings (for premium traditional positioning) |
| **Mintlify** | Reading-optimized green-accent — informs professional services copy |
| **Webflow** | Blue-accented marketing polish, hero patterns |

Do not pull from: automotive (Ferrari, Lamborghini, BMW) — too editorial for service funnels. Flag them as "reference only, do not inherit".

## Extraction rules

1. **Only cross-cutting patterns.** If a token appears in ≥3 exemplars, it's cross-cutting. Single-site patterns belong in the "reference only" annex.
2. **Cite every claim.** Every extracted pattern names the exemplars it came from and the Stitch section (Palette / Typography / Components / etc.).
3. **Translate, don't transplant.** Stripe's gradient-weight-300 headline doesn't transplant onto an electrician site — translate the *intent* (confidence, proof, restraint) into terms that fit a local service funnel.
4. **Pair with anti-slop.** Every pattern includes the AI-slop rule it replaces (reference `core/prompts/website_builder.md`'s existing slop table).

## Output structure (`_workspace/template/01_research.md`)

```markdown
# Template Research — {date}

## 1. Exemplar matrix
| Exemplar | Local-service fit | Use for |
|----------|------------------|---------|
| Stripe | ★★★★★ | trust hierarchy, palette |
| ... |

## 2. Cross-cutting patterns

### Theme & atmosphere
- **Pattern:** {rule}. Sources: Stripe §1, Linear §1, Vercel §1. Replaces AI-slop: {rule}.
- ...

### Palette
...
### Typography
...
### Components
...
### Layout
...
### Depth
...
### Responsive
...

## 3. Trust signals inventory
- {pattern}, sources, copy implications for copywriter
- ...

## 4. Anti-slop additions beyond current prompt
- ...

## 5. Open questions for architect
- ...

## 6. Open questions for copywriter
- ...
```

## Failure recovery

- Raw.githubusercontent fails → try `gh api repos/VoltAgent/awesome-design-md/contents/{path}` → if still failing, proceed with offline priors from the README collection list and flag "limited fetch, patterns inferred from site descriptions only" in the header.
- Conflicting patterns between exemplars → record both with pros/cons. Do not pre-resolve; architect decides.

## Example extraction

Input: Stripe DESIGN.md §2 says `--surface-canvas: #FFFFFF`, Linear says `#FCFCFC`, Vercel says `#FFFFFF`.
Output: `Canvas = pure white (#FFFFFF). Sources: Stripe §2, Vercel §2. Linear uses #FCFCFC (off-white) for reduced eye strain — flag as alt for premium tier.`
