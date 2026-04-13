---
name: hermes-design-harness
description: Orchestrates a 4-agent team that builds high-design Hermes websites for local service businesses. Use when the user asks to build, generate, create, make, improve, refine, redesign, iterate, rebuild, or upgrade a website, landing page, or site for a local service business (electrician, plumber, roofer, HVAC, cleaner, etc). Also triggers on "make the site look better", "fix the design", "improve quality", "re-run design", "apply feedback", or any follow-up request referencing a previously built Hermes site. Coordinates aesthetic-director → site-builder → design-critic → surgical-fixer with an iterative quality loop.
---

# Hermes Design Harness

Orchestrates the 4-agent pipeline that turns `references/business_details.json` into a high-design, ship-ready website.

## Execution mode
**Agent team** (default). Use `TeamCreate` with all four members, drive with `TaskCreate`, let members self-coordinate via `SendMessage`. All `Agent` calls use `model: "opus"`.

## Team
| Agent | Role | Output |
|-------|------|--------|
| `aesthetic-director` | Design brief from biz data + frontend-design taste | `_workspace/01_aesthetic_brief.md` |
| `site-builder` | Runs `generate.py` with brief injected | `output/{slug}.html`, `_workspace/02_build_report.json` |
| `design-critic` | Screenshot QA + AI-slop hunt | `_workspace/03_critique.json` |
| `surgical-fixer` | Minimal HTML/CSS edits | modified HTML, `_workspace/04_fixes.md` |

## Phase 0: Context check
Before running the pipeline, inspect `_workspace/`:
- **Missing** → initial run, execute all phases.
- **Exists + user asks for fresh build** → move `_workspace/` to `_workspace_prev/`, initial run.
- **Exists + user asks to iterate/fix/improve** → partial re-run. Read existing artifacts, route only the affected agents.
- **Exists + user provides targeted feedback** → skip to `surgical-fixer` with feedback appended to `03_critique.json`.

## Phase 1: Brief (aesthetic-director)
Create the aesthetic brief. Wait for `01_aesthetic_brief.md`.

## Phase 2: Build (site-builder)
Inject brief into `prompts/website_builder.md`, run `generate.py`, capture output + build report. Target 15/15 validation + 0 readability warnings. One regeneration on failure, then escalate.

## Phase 3: Critique (design-critic)
Screenshot desktop + mobile. Score on 4 axes. Produce `03_critique.json` with `ship_verdict`.

## Phase 4: Fix loop
- `ship` → done, report to user.
- `fix_then_ship` → `surgical-fixer` applies edits → back to Phase 3. Max 3 iterations.
- `rebuild` → back to Phase 1 with critic's brief feedback. Max 2 rebuilds.

## Phase 5: Report
Summarize to user: final scores, iterations used, path to HTML, readiness verdict. Ask:
> "Ready to deploy, or anything to refine?"

If deploy requested: run `python3 deploy.py output/{slug}.html`.

## Data flow
- File-based for artifacts (`_workspace/`, `output/`).
- SendMessage for agent handoffs + iteration loops.
- TaskCreate for dependency tracking (each phase = one task).

## Error handling
- `generate.py` fails → site-builder retries once with error context → escalate to orchestrator if still failing.
- Screenshot tool fails → design-critic falls back to `review.py` → if both fail, critique from raw HTML only, flag "no visual verification" in report.
- Fix loop exceeds 3 iterations → stop, report remaining issues, ask user whether to ship-as-is or rebuild.

## Test scenario (normal)
Input: `Spartan Electrical` in business_details.json.
Expected: brief → HTML built → critique finds 2-4 issues → fixer resolves → ship verdict → final HTML at `output/spartan-electrical.html` scoring ≥8 on all 4 axes.

## Test scenario (error)
Input: business_details.json missing `services_offered`.
Expected: aesthetic-director flags missing field, halts pipeline, reports to user before generation starts. No wasted Gemini tokens.

## Follow-up triggers
This skill MUST re-trigger on: "make it better", "fix the design", "redo", "try another direction", "the hero feels weak", "apply this feedback", "rebuild for {business}". On re-trigger, run Phase 0 context check first.
