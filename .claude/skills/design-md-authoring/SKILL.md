---
name: design-md-authoring
description: Authoring guide for the master Hermes DESIGN.md following the Google Stitch 9-section schema (Visual Theme, Palette, Typography, Components, Layout, Depth, Do/Don't, Responsive, Agent Prompt Guide). Use when design-system-architect is writing, editing, or validating DESIGN.md, or generating preview.html / preview-dark.html visual catalogs. Enforces schema conformance, token naming, and anti-slop guardrails.
---

# DESIGN.md Authoring

Produces `DESIGN.md` at project root, plus `preview.html` + `preview-dark.html` visual catalogs.

## Why Stitch schema

Google Stitch's DESIGN.md format (https://stitch.withgoogle.com/docs/design-md/overview/) is the closest thing to a standard: plain markdown, 9 fixed sections, LLM-parseable. AI agents read it natively without tooling. Every exemplar in the VoltAgent library uses it, so our template compares directly.

## The 9 sections (required, in order)

| # | Section | What it captures |
|---|---------|-----------------|
| 1 | Visual Theme & Atmosphere | Mood, density, design philosophy (2–4 paragraphs max) |
| 2 | Color Palette & Roles | Semantic name + hex + functional role (table) |
| 3 | Typography Rules | Font families + full hierarchy table (h1–h6, body, caption, mono) |
| 4 | Component Stylings | Buttons, cards, inputs, navigation, links, badges — with states |
| 5 | Layout Principles | Spacing scale, grid, breakpoints, whitespace philosophy |
| 6 | Depth & Elevation | Shadow system, surface hierarchy |
| 7 | Do's and Don'ts | Design guardrails + explicit anti-patterns |
| 8 | Responsive Behavior | Breakpoints, touch targets, collapsing strategy |
| 9 | Agent Prompt Guide | Quick color reference + ready-to-use prompt snippets |

A missing section = fail. Leave "Deliberately minimal — {rationale}" if a section has no meaningful content rather than omitting it.

## Authoring principles

- **Tokens > prose.** Name every value. `--accent-primary: #2563EB` beats "use a confident blue."
- **Semantic names.** `--surface-canvas`, `--surface-alt`, `--ink-strong`, `--ink-muted`, `--accent-primary`. Not `--blue-500`.
- **One aesthetic direction.** Local-service sites need decisive direction. Don't ship three personas at the master-template layer — that was the old `core/prompts/website_builder.md` approach. The master template is one voice; per-business tweaks happen later.
- **Anti-slop explicit.** Every component spec names the AI-slop pattern it rejects.
- **4.5:1 contrast minimum** on all text/background pairs. Cite the ratio in the palette table.
- **Max body width 650px.** Readability rule from existing Hermes prompt.

## Section-level templates

### §2 Palette (example row format)

| Token | Hex | Role | Contrast vs canvas |
|-------|-----|------|--------------------|
| `--surface-canvas` | `#FFFFFF` | Primary page background | — |
| `--surface-alt` | `#F9FAFB` | Alternating section bg | — |
| `--ink-strong` | `#0A0F1A` | Headings, primary text | 17.4:1 ✓ |
| `--ink-muted` | `#4B5563` | Body text, captions | 7.8:1 ✓ |
| `--accent-primary` | `#2563EB` | Primary CTA only | 4.6:1 ✓ |
| `--accent-ink` | `#FFFFFF` | Text on accent | — |

### §3 Typography (example)

- **Family:** Inter Variable (100–900), `-apple-system` fallback.
- **Mono:** JetBrains Mono (for phone number, license numbers).

| Role | Size | Weight | Tracking | Line-height |
|------|------|--------|----------|-------------|
| h1 (hero) | 64px (clamp 40–72px) | 800 | -0.04em | 1.05 |
| h2 | 44px | 700 | -0.03em | 1.1 |
| h3 | 28px | 600 | -0.02em | 1.2 |
| body | 17px | 400 | 0 | 1.6 |
| caption | 13px | 500 | 0.02em | 1.4 |

### §7 Do's and Don'ts

Use paired rows. Left = AI-slop anti-pattern. Right = our rule.

## Preview catalogs

`preview.html` must render standalone in a browser (no network). Include:
- Color swatches with hex + token name
- Type scale with live rendered text
- Button states (rest, hover, active, focus, disabled)
- Card variants (service card, trust card, testimonial)
- Form controls
- Typography sample paragraph

`preview-dark.html` = mirror with dark surfaces. Use CSS variables so both files share structure.

## Parallel draft mode

When orchestrator spawns architect in parallel with researcher, start from existing `core/prompts/website_builder.md` priors (the current Inter + cold gray + utility blue direction). Record "drafted without research, awaiting integration" in `02_design_decisions.md`. On researcher handoff, merge and log every change with source citation.

## Failure recovery

- Research missing → proceed with priors, flag in decision log.
- Cannot achieve 4.5:1 contrast with chosen accent → pick a darker shade, document the swap.
- Schema section has no content → write "Deliberately minimal — {why}" rather than omitting.

## Output checklist

- [ ] All 9 sections present in order
- [ ] Every token named + cited
- [ ] Every color pair passes 4.5:1
- [ ] `preview.html` renders standalone
- [ ] `preview-dark.html` renders standalone
- [ ] `_workspace/template/02_design_decisions.md` logs rationale + research citations
