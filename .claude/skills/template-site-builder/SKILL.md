---
name: template-site-builder
description: Build per-business websites from core/templates/ULTIMATE_TEMPLATE.html for Hermes no-website prospects WITHOUT calling OpenRouter or Gemini. Runs Python slot-fill (data + derived slots), then you — Claude Code — author the 21 voice-matched copy slots in-session using COPY.md formulas and the frontend-design:frontend-design skill for polish, then validates, deploys to Cloudflare Pages, and refreshes output/nowebsite_outreach.csv. Use WHENEVER the user asks to build/generate sites from the template, fill the template for a slug, build sites for no-website or poor-website prospects, replace a prospect's broken/placeholder site, or says "use the template", "use Claude Code not Gemini", "template-fill build", "build using frontend-design", "build more sites from the template", "build the next N prospects", "rebuild {slug} from template", "fill slots for {slug}". Covers all three qualified cohorts (A_greenfield, B_broken, C_placeholder) — the built site is the outreach deliverable for all of them. Does NOT fire for ultimate-template-builder (that rebuilds the master template itself).
---

# Template Site-Builder

Build websites for Hermes no-website / poor-website prospects using the master `core/templates/ULTIMATE_TEMPLATE.html` + COPY.md voice + the `frontend-design:frontend-design` skill, with no Gemini/OpenRouter calls. Every LLM-authored byte is written in this Claude Code session.

## Inputs expected

- `_workspace/nowebsite/candidates.json` — discovery output from the `no-website-prospector` pipeline.
- `_workspace/nowebsite/{slug}_qualified.json` — one per qualified slug, `verdict == "qualified"` and `cohort ∈ {A_greenfield, B_broken, C_placeholder}`.
- `core/templates/ULTIMATE_TEMPLATE.html`, `DESIGN.md`, `COPY.md` — treat as read-only references.

If the workspace does not exist, stop and suggest running `no-website-prospector` first.

## Workflow

### Phase 0 — Context

1. Check `output/_filled/` and `output/` for any prior artifacts.
2. Read the user's scope request. Defaults when unspecified:
   - `--top 1` + `--cohort A_greenfield` for smoke test / single prospect.
   - Otherwise ask AskUserQuestion to pick cohort(s) + count.
3. If user says "redo {slug}", jump straight to Phase 1 for that slug (skip queue sort).

### Phase 1 — Deterministic slot-fill

For each target slug, run:

```bash
python3 -m core.fill_template <slug>
```

Output: `output/_filled/<slug>.html` with every data + derived slot populated, and every copy slot replaced with a sentinel of the form:

```html
<!-- COPY_TODO:hero_subhead|…formula + constraints… -->[[WRITE_hero_subhead]]
```

If `core/fill_template.py` exits non-zero, the slug is missing from `candidates.json` — surface the error, skip the slug.

### Phase 2 — Author the copy slots (this is why this skill exists)

1. Read the filled HTML, the prospect's record from `candidates.json`, and `references/copy-instructions.md`.
2. Invoke the `frontend-design:frontend-design` skill once to ground yourself in the design system's voice constraints — do not have it rewrite HTML wholesale; use it to sanity-check your phrasing and CSS micro-adjustments only.
3. For each `[[WRITE_<slot>]]` sentinel, use the Edit tool to replace the **entire** `<!-- COPY_TODO:... --><![[WRITE_<slot>]]` pair (both the comment and the sentinel) with the authored copy.
4. Once every sentinel is gone, save the file to `output/<slug>.html` and delete the intermediate `output/_filled/<slug>.html`.

Constraints — enforced by `core/validate_filled_html.py`:
- ≤25 words on `hero_subhead`, ≤15 words on each `service_*_description`, ≤4 words on each `service_*_title`.
- FAQ answers within per-question budgets (see `copy-instructions.md`).
- No banned vocab (COPY.md §9 — `core/validate_filled_html.py` scans the stripped body text).
- No exclamation marks outside the review quotes already baked in.
- Persona matches what `core/fill_template.py` set on `<html data-persona="...">` — do not override it.

### Phase 3 — Validate

```bash
python3 -m core.validate_filled_html output/<slug>.html
```

On failure:
1. Read the printed reasons.
2. Fix in place with Edit — never regenerate the file. Typical failures: residual sentinel (one slot missed), banned word slipped in, service_description over 15 words.
3. Re-validate. Loop max twice. If still failing after two fixes, leave the HTML in `output/` but mark the slug skipped when summarizing.

### Phase 4 — Deploy

```bash
python3 -m core.deploy output/<slug>.html
```

`core/deploy.py` is idempotent (file-hash dedup). After deploy, the live URL is in `prospects/deploys.json`.

### Phase 5 — Refresh CSV

```bash
python3 -m pipelines.no_website_prospector.emit_nowebsite_outreach
```

Writes/updates `output/nowebsite_outreach.csv` (columns include `business_name, city, address, phone_number, phone_e164, email, email_source, website_url, current_website_url, cohort, slug, rating, review_count, deployed_at`). Dedups on `slug`.

### Phase 6 — Summarize

One message to the user:
- N qualified in queue, M filled, V validated-pass, D deployed, C CSV rows.
- Path to CSV.
- Any skipped slugs and the reason in one line each.
- Prompt for feedback: "Anything to adjust on copy or template before the next batch?"

## Why this skill orchestrates you (not a subprocess)

The copy slots are the core value — they need the voice, specificity, and
COPY.md formula compliance that only a reasoning LLM can produce. Running
them through an autonomous Python script would either hallucinate or need
an external API call. Instead this skill keeps the heavy reasoning where it
already is (this session) and spends Python on everything deterministic:
slot-fill, validation, deploy, CSV emit.

## Follow-ups

- "Build 5 more" → Phase 0 re-derives the top-5 unbuilt queue, skip build reports that already exist in `output/`.
- "Rebuild {slug}" → force re-fill + re-validate + re-deploy (core/deploy.py will re-hash).
- "Tighten the voice for {slug}" → skip Phase 1, Edit the existing `output/<slug>.html`, re-validate, re-deploy.

## References

- `references/slot-map.md` — which slots are filled by whom, and how.
- `references/copy-instructions.md` — voice + formula + examples for each copy slot.
- `references/vertical-defaults.json` — credential / persona / response defaults per vertical.
- `evals/evals.json` — smoke test prospects spanning cohorts A/B/C.

## Test scenarios

**Normal (A_greenfield):** user says "build a site for `stirling-burt-heating` using the template" → Phase 1 fills the template → you author 21 copy slots inline → validator exits 0 → core/deploy.py returns a pages.dev URL → CSV row appended.

**B_broken cohort:** user says "build a replacement for `aberdeen-kelgas-uk-limited`" (existing URL is HTTP dead). Pipeline runs identically; CSV carries both the old URL (`current_website_url`) and the new pages.dev URL (`website_url`) so outreach copy can reference the upgrade.

**Partial rerun:** user says "the FAQs felt generic for stirling-burt-heating, rewrite them" → skip Phase 1; open `output/stirling-burt-heating.html`; Edit only the five FAQ answers; re-validate; re-deploy.
