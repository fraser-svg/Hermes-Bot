---
name: ultimate-template-builder
description: Orchestrates the 5-agent team (market-researcher, design-system-architect, conversion-copywriter, template-engineer, template-critic) that builds and maintains the master DESIGN.md + COPY.md + core/templates/ULTIMATE_TEMPLATE.html for Hermes. Use whenever the user asks to build, create, author, redesign, improve, iterate, update, patch, refine, rebuild, or audit the master template, design system, copy framework, DESIGN.md, COPY.md, preview catalog, or core/prompts/website_builder.md's design layer. Also triggers on "make the template better", "add a trust section to the template", "redo the palette", "tighten the hero copy framework", or any follow-up referencing previous template work. DO NOT use for per-business website builds — those route to hermes-design-harness.
---

# Ultimate Template Builder

Orchestrates the template-creation pipeline that produces Hermes's master design system, copy framework, and reference HTML. Output feeds `core/prompts/website_builder.md` so every per-business build via `hermes-design-harness` inherits the template.

## When this skill is wrong

If the user says "build me a website for {business}" or references a specific client in `core/references/business_details.json`, route to `hermes-design-harness` instead. This skill is exclusively for the reusable master template, not per-business sites.

## Execution mode

**Agent team** (default). `TeamCreate` with the 5 members, drive with `TaskCreate`, let members self-coordinate via `SendMessage`. All `Agent`/team calls use `model: "opus"`.

## Team

| Agent | Role | Output |
|-------|------|--------|
| `market-researcher` | Mine VoltAgent/awesome-design-md exemplars, extract cross-cutting patterns | `_workspace/template/01_research.md` |
| `design-system-architect` | Author `DESIGN.md` (Stitch 9-section schema) + preview HTML | `DESIGN.md`, `preview.html`, `preview-dark.html`, `_workspace/template/02_design_decisions.md` |
| `conversion-copywriter` | Author `COPY.md` modular framework | `COPY.md`, `_workspace/template/03_copy_decisions.md` |
| `template-engineer` | Synthesize into reference HTML + patch builder prompt | `core/templates/ULTIMATE_TEMPLATE.html`, patched `core/prompts/website_builder.md`, `_workspace/template/04_patch.md` |
| `template-critic` | Schema check, slop audit, 3-business smoke test | `_workspace/template/05_critique.json` |

## Phase 0: Context check

Inspect `_workspace/template/`:
- **Missing** → initial run, execute all phases.
- **Exists + user asks for fresh build** → archive `_workspace/template/` to `_workspace/template_prev/`, run initial.
- **Exists + user asks to iterate** → partial re-run. Read artifacts, route only affected agents (e.g., "tighten hero copy" → copywriter + engineer + critic; skip researcher + architect).
- **Exists + user provides targeted feedback on one component** → skip straight to `template-engineer` with feedback appended, then critic.

Why: re-running research/architecture on every feedback burns tokens and risks drift. Scope the loop to the smallest set that can answer the feedback.

## Phase 1: Parallel kickoff

Spawn `market-researcher` and `design-system-architect` in parallel via `TaskCreate` with no dependency between them. Architect drafts from existing `core/prompts/website_builder.md` priors; researcher pulls exemplars from https://github.com/VoltAgent/awesome-design-md.

Wait for both.

## Phase 2: Architect integrates research

`design-system-architect` reads `_workspace/template/01_research.md` and finalizes `DESIGN.md` + `preview.html` + `preview-dark.html`. Decision log recorded in `02_design_decisions.md`.

## Phase 3: Copywriter

`conversion-copywriter` reads `DESIGN.md` (tone) + research (trust patterns) + `core/references/business_details.json` (slot schema), authors `COPY.md`.

## Phase 4: Synthesis

`template-engineer` composes `core/templates/ULTIMATE_TEMPLATE.html` from the two source files and patches `core/prompts/website_builder.md` additively (not a rewrite). Records diff + rollback in `04_patch.md`.

## Phase 5: Critique + fix loop

`template-critic` verdicts:
- `ship` → done, go to Phase 6
- `fix_then_ship` → route fix list to `template-engineer`, re-critique. Max 2 iterations.
- `rebuild` → schema failure, route back to `design-system-architect` with rationale. Max 1 rebuild.

Critic's smoke test must pass 15/15 + 0 readability warnings on 3 synthetic businesses (trades, professional services, personal services).

## Phase 6: Report

Summarize to user: final verdict, iterations used, files created, smoke test scores, any deferred issues. Ask:
> "Want this merged into the live builder prompt, or iterate further?"

## Data flow

- **File-based** for all artifacts (`_workspace/template/`, project-root `DESIGN.md`/`COPY.md`, `templates/`).
- **SendMessage** for handoffs and fix-loop messages.
- **TaskCreate** for dependency tracking (one task per phase).

## Error handling

- Research step fails → retry once with narrower target → proceed with architect's priors, flag "limited research".
- `core/generate.py` smoke test fails → engineer patches placeholder logic → one retry → escalate.
- Fix loop exceeds 2 iterations → stop, report unresolved findings, ask user for direction.

## Follow-up triggers

This skill MUST re-trigger on: "update DESIGN.md", "improve the template", "redo the palette", "tighten hero copy framework", "rebuild the master template", "apply this feedback to the template", "fix the design system", "refine COPY.md". On re-trigger, run Phase 0 first.

## Test scenario (normal)

Input: "build me the ultimate local service template".
Expected: Phase 1 parallel → architect finalizes DESIGN.md → copywriter produces COPY.md → engineer patches prompt → critic smoke-tests trades/pro/personal samples → all 15/15 + 0 warnings → ship verdict → report.

## Test scenario (iterate)

Input: "the hero copy formulas feel generic, tighten them" (existing `_workspace/template/` present).
Expected: Phase 0 detects partial re-run → route only `conversion-copywriter` → engineer patches → critic runs smoke test → verdict → report. No research or architecture re-run.
