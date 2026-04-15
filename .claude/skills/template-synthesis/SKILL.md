---
name: template-synthesis
description: Guide for composing DESIGN.md + COPY.md into core/templates/ULTIMATE_TEMPLATE.html (reference single-file HTML with placeholder slots) and safely patching core/prompts/website_builder.md so core/generate.py inherits the master template on every per-business build. Use when template-engineer is synthesizing, patching, or rolling back template changes. Enforces additive patching, slot conventions, and no-regression rules.
---

# Template Synthesis

Takes `DESIGN.md` + `COPY.md` and produces two deliverables: `core/templates/ULTIMATE_TEMPLATE.html` (a working reference) and a patched `core/prompts/website_builder.md` (so every future `core/generate.py` run inherits both).

## Why additive patching

`core/prompts/website_builder.md` is already battle-tested — 15/15 validation + 0 readability rules are tuned against its exact structure. A full rewrite would risk regression. Instead, we append an "Authoritative References" block that points at the new `DESIGN.md` + `COPY.md` and instructs the prompt to defer to them on conflict. Existing rules stay as fallback.

Record every patch in `_workspace/template/04_patch.md` with exact insertion points and rollback instructions so `core/generate.py` can always be reverted.

## ULTIMATE_TEMPLATE.html requirements

- **Standalone.** Opens in a browser with no build step, no network fetches (except Google Fonts + Unsplash stock photos, matching `core/generate.py` conventions).
- **Every value ties to DESIGN.md.** Inline CSS variables at `:root` mirror the DESIGN.md token names (`--surface-canvas`, `--ink-strong`, etc.). No magic numbers.
- **Slots use `{{business.field_name}}`.** Matching `COPY.md` §10 slot map exactly.
- **Complete page.** Not a component library — a full single-page site with hero, services, trust band, FAQ, footer. What a real `core/generate.py` output looks like, just with slots.

## Section coverage

| Section | DESIGN.md source | COPY.md source |
|---------|-----------------|----------------|
| Hero | §1 theme + §3 type | §2 headline formula |
| Trust band | §4 components (cards) | §5 trust patterns |
| Services grid | §4 cards + §5 layout | §6 service copy |
| Testimonials | §4 cards | `{{business.reviews[]}}` |
| FAQ | §4 components | §7 FAQ templates |
| Footer | §4 footer | §8 microcopy |

## Patching core/prompts/website_builder.md

Append this block near the top (after the existing role description, before "DESIGN PHILOSOPHY"):

```markdown
## AUTHORITATIVE REFERENCES (READ FIRST)

Two master files live at project root and override anything below on conflict:

1. **DESIGN.md** — master design system (Google Stitch 9-section schema). Palette, typography, components, layout, depth, responsive rules. Load as context at build time.
2. **COPY.md** — master copy framework. Headline formulas, CTA vocabulary, trust patterns, FAQ templates, banned AI-slop vocabulary. Load as context at build time.

When DESIGN.md or COPY.md disagrees with a rule later in this prompt, DESIGN.md/COPY.md wins. Treat the rest of this prompt as fallback for anything those files don't cover.
```

Record in `04_patch.md`:
- Insertion point (line number + surrounding context)
- Full inserted text
- Rollback: delete lines N–M

## Slot convention enforcement

Before writing any `{{business.x}}` placeholder, confirm `x` exists in `core/references/business_details.json`. If not, stop and message the orchestrator — do not invent fields.

## No-regression rule

After patching `core/prompts/website_builder.md`, the critic will run `core/generate.py` on 3 synthetic businesses. All three must still score 15/15 validation + 0 readability warnings. If any fail, revert the patch and try a narrower insertion — do not ship a regression.

## Failure recovery

- Patch breaks `core/generate.py` → read `04_patch.md`, revert, retry with narrower insertion. Second failure → escalate.
- Slot name missing from `business_details.json` → halt, ask orchestrator. Never guess.
- `ULTIMATE_TEMPLATE.html` won't render standalone → trace to which DESIGN.md token is missing, add it to architect's backlog, use a fallback value in HTML and flag it.

## Output checklist

- [ ] `core/templates/ULTIMATE_TEMPLATE.html` renders standalone
- [ ] Every CSS value maps to a DESIGN.md token
- [ ] Every `{{business.*}}` slot maps to a `business_details.json` field
- [ ] `core/prompts/website_builder.md` patched additively (no deletions)
- [ ] `_workspace/template/04_patch.md` has insertion point + rollback
- [ ] Team notified (`SendMessage` to critic) with paths
