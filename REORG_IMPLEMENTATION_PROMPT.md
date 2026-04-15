# Hermes Bot Reorg — Implementation Prompt

Paste this into a fresh Claude Code session at `/Users/foxy/Hermes Bot`.

---

Execute the folder reorganization plan at `/Users/foxy/.claude/plans/optimized-seeking-metcalfe.md`. Read it first in full.

## Context (short)

Project has 4 pipelines (Ultimate Template Builder, Hermes Design Harness, Retarget Prospector, No-Website Prospector) currently sprawled across the repo root with ~50 loose Python files. Goal: `core/` for shared infra, `pipelines/<name>/` for each pipeline, `docs/` for strategy md, `legacy/` for quarantined files.

## Decisions already confirmed by user

1. **Legacy quarantine** — `git mv` unused files (`main.py`, `hermes.py`, `run.py`, `pipeline.py`, `mission_control.py`, `content_gen.py`, `enrich.py`, `generate_hybrid.py`, `webhook_server.py`, `prospect.py`, `v1-frozen/`, `experiments/`, `compliance/`) into `legacy/`. Do NOT delete.
2. **`_workspace/`** — move `_workspace/template/` → `pipelines/template_builder/workspace/`, add `_workspace/` to `.gitignore`, leave other artifacts on disk untouched (do not `git rm`).
3. **Import style** — package modules. Add `__init__.py` to `core/` and each `pipelines/<name>/`. Scripts invoked as `python -m core.generate`, `python -m pipelines.no_website_prospector.run_nowebsite_pipeline`, etc.

## Execution order (follow exactly)

1. `git status` — confirm clean-ish working tree. Existing uncommitted changes from the previous session are OK; just note them.
2. Create empty target dirs: `core/`, `pipelines/{template_builder,design_harness,retarget_prospector,no_website_prospector}/`, `docs/`, `legacy/`.
3. `git mv` shared infra → `core/`: `generate.py`, `deploy.py`, `review.py`, `fill_template.py`, `validate_filled_html.py`, `hero_images.py`, `prompts/`, `templates/`, `references/`.
4. `git mv` pipeline files per the plan's Target Layout section.
5. Split `prospects/`:
   - `*-no-pixel.json` → `pipelines/retarget_prospector/data/`
   - nowebsite JSONs (grep for cohort A/B/C or `nowebsite`) → `pipelines/no_website_prospector/data/`
   - `prospects/deploys.json` → `core/deploys.json`
   - Ambiguous leftovers → `legacy/prospects_uncategorized/`
6. Split `output/`:
   - `scotland_retarget_*`, `glasgow_*`, `*_retarget_*` → `pipelines/retarget_prospector/output/`
   - `*-filled.html`, `nowebsite_outreach.csv`, `_filled/` → `pipelines/no_website_prospector/output/`
   - Everything else from per-business builds → `pipelines/design_harness/output/`
7. Quarantine legacy list (decision #1) → `legacy/`.
8. Add `__init__.py` (empty) to `core/` and each `pipelines/<name>/`.
9. Patch `core/fill_template.py` — change `from generate import auto_select_accent` → `from core.generate import auto_select_accent`.
10. Patch `.claude/` skills + agents + `prompts/hermes_system_prompt.md` path references. File list is in the plan under "Skill + agent markdown references". Use `Edit` per file, not global sed. Replace `generate.py` → `core/generate.py`, `deploy.py` → `core/deploy.py`, `run_nowebsite_pipeline.py` → `pipelines/no_website_prospector/run_nowebsite_pipeline.py`, `prospect_no_pixel.py` → `pipelines/retarget_prospector/prospect_no_pixel.py`, `fill_template.py` → `core/fill_template.py`. Update any `python3 <file>.py` → `python3 -m core.<module>` / `python3 -m pipelines.<pkg>.<module>`.
11. Patch `CLAUDE.md` — "How to Build a Website" block (`python3 generate.py` → `python3 -m core.generate`) and any path refs in 변경 이력 tables. Preserve all narrative and caveman voice.
12. Patch `.gitignore` — add `_workspace/`, `__pycache__/`, `output/*.html`, `build_report.json`, `review_report.json`.
13. Patch `.claude/skills/ad-verification/scripts/sweep_scotland.py` path references.
14. Commit in logical groups (one commit per group, conventional commits format):
    - `refactor: create core/ + pipelines/ layout`
    - `refactor: move retarget prospector files`
    - `refactor: move no-website prospector files`
    - `refactor: quarantine legacy`
    - `docs: update skill + CLAUDE.md path references`
15. Run verification (next section). If any step fails, fix before continuing.

## Verification

Run after commits, in order. Fix failures before declaring done.

1. `python -m core.generate` with existing `core/references/business_details.json` — builds a site, writes `output/` + `index.html`, 15/15 validation score.
2. `python -m pipelines.retarget_prospector.prospect_no_pixel --static-only --limit 1` — runs end-to-end on one prospect without ImportError.
3. `python -m core.deploy --list` — reads deploy log without error.
4. `git grep -n "python3 generate.py\|run_nowebsite_pipeline.py\|prospect_no_pixel.py" -- ':!legacy' ':!docs' ':!REORG_IMPLEMENTATION_PROMPT.md'` — zero results.
5. `git log --follow core/generate.py` — history preserved through `git mv`.
6. `git grep -l "^from generate\|^import generate" -- ':!legacy'` — zero results (no bare `generate` imports outside legacy).

## Rules

- Use `git mv`, never `mv` + `git add`, so history follows.
- One logical commit group at a time. Do not bundle everything into one commit.
- Do NOT touch `v1-frozen/` contents — just move the folder wholesale into `legacy/`.
- Do NOT rewrite any Python beyond the one import fix in `core/fill_template.py` unless verification reveals a second broken import.
- If `prospects/` contains files matching neither pattern, put them in `legacy/prospects_uncategorized/` — do not guess.
- Caveman voice for any user-facing status updates, normal voice for commit messages and code.
- Read `CLAUDE.md` before touching it so you don't lose the 하네스 history tables.

## Red flags — stop and ask user if you hit these

- Any script imports a module that's not in the plan's known-imports list (plan found only `fill_template` → `generate`).
- `prospects/` or `output/` contains files you can't classify into retarget vs no-website vs design-harness.
- Verification step 1 (core.generate smoke test) fails — do not proceed to more commits.
- Any `.claude/skill` references a path that doesn't exist in the new layout.

Plan file: `/Users/foxy/.claude/plans/optimized-seeking-metcalfe.md`. Re-read it whenever unclear.
