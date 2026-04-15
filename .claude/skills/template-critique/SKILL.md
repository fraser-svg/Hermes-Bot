---
name: template-critique
description: QA rubric and smoke-test harness for the Hermes master template. Use when template-critic is validating DESIGN.md schema conformance, running the AI-slop checklist, smoke-testing the patched core/generate.py pipeline on 3 synthetic businesses (trades, professional services, personal services), or scoring generalization. Produces the ship/fix/rebuild verdict.
---

# Template Critique

Produces `_workspace/template/05_critique.json` with `ship_verdict` ∈ {`ship`, `fix_then_ship`, `rebuild`}.

## Why default-to-guilty

A master template touches every future Hermes site. A missed slop regression gets baked into hundreds of builds. Critic defaults to `fix_then_ship`; the team must prove ship-readiness.

## Verification passes (all required)

### Pass 1: DESIGN.md schema conformance

Check all 9 Stitch sections present in order:
1. Visual Theme & Atmosphere
2. Color Palette & Roles
3. Typography Rules
4. Component Stylings
5. Layout Principles
6. Depth & Elevation
7. Do's and Don'ts
8. Responsive Behavior
9. Agent Prompt Guide

Missing or out-of-order section → `rebuild` verdict, route back to architect.

### Pass 2: COPY.md structural check

Sections 1–10 present per `copy-md-framework` skill. Slot map matches `core/references/business_details.json` field names exactly (no invented fields). Banned vocabulary section present and non-trivial.

### Pass 3: AI-slop rubric

Scan `DESIGN.md`, `COPY.md`, `core/templates/ULTIMATE_TEMPLATE.html` against the slop checklist in existing `core/prompts/website_builder.md`:

- Wavy/curvy SVG dividers → fail
- Pill buttons (100px radius) → fail
- 3D or cartoonish icons → fail
- Warm cream/beige backgrounds → fail
- Gradient glows on CTAs → fail
- "Revolutionizing" / "seamless" / "cutting-edge" etc. in COPY.md outside the banned list → fail
- Hero text without text-shadow on image background → fail
- Body text wider than 650px → fail

Every finding records: severity (high/med/low), location (file + section), rule violated, suggested fix.

### Pass 4: Smoke test (end-to-end)

Run `python3 -m core.generate` three times, each with a different synthetic `core/references/business_details.json`:

| Sample | Category | Required fields |
|--------|----------|----------------|
| `trades_sample` | electrician | Dunfermline, 10+ years, 4.9 ★, 80+ reviews |
| `professional_sample` | accountant | Edinburgh, 15 years, 5.0 ★, 40+ reviews |
| `personal_sample` | personal trainer | Glasgow, 5 years, 4.8 ★, 60+ reviews |

Each must:
- Score 15/15 on `build_report.json` validation
- Score 0 readability warnings
- Produce a standalone-renderable `output/{slug}.html`

Any failure on any sample → critic reports exact failure text, engineer fixes, re-test.

Cache the three synthetic businesses in `.claude/skills/template-critique/samples/` so tests are reproducible.

### Pass 5: Generalization score (0–10)

Rate how well the template adapts across verticals:
- 10: all three samples look distinctive to their vertical, feel like different businesses
- 7: all three pass validation but feel like the same template
- 4: one sample is noticeably weaker than the others
- 0: template over-fits to one vertical

## Verdict rules

- `ship` — Pass 1–4 all green, generalization ≥ 7
- `fix_then_ship` — Pass 1–4 green, generalization 5–6, OR Pass 3 has only low-severity findings
- `rebuild` — Pass 1 fail, OR Pass 2 fail, OR Pass 4 fails on ≥2 samples, OR Pass 3 has high-severity findings

## Output schema (`05_critique.json`)

```json
{
  "ship_verdict": "ship | fix_then_ship | rebuild",
  "timestamp": "...",
  "schema_check": {
    "design_md": { "passed": true, "missing_sections": [] },
    "copy_md": { "passed": true, "missing_sections": [] }
  },
  "slop_findings": [
    { "severity": "high", "location": "DESIGN.md §4 Buttons", "rule": "pill radius 100px", "fix": "use 6–8px radius" }
  ],
  "smoke_test": {
    "trades_sample": { "validation": "15/15", "readability_warnings": 0, "html_path": "..." },
    "professional_sample": { ... },
    "personal_sample": { ... }
  },
  "generalization_score": 8,
  "notes": "..."
}
```

## Fix-loop protocol

- `fix_then_ship` → message `template-engineer` with the findings list, wait for re-notification, re-run full critique. Max 2 iterations.
- `rebuild` → message `design-system-architect` (schema/high-severity slop) with rationale. Max 1 rebuild.
- After max iterations, escalate to orchestrator; do not silently ship.

## Failure recovery

- `core/generate.py` error unrelated to template (infra/API) → retry once, if persistent escalate to orchestrator as infra issue, don't mask as slop.
- Screenshot tool unavailable → fall back to static HTML/CSS review, mark "no visual verification" in `notes`.
