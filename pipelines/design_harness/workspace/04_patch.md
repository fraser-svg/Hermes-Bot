# Patch Log — prompts/website_builder.md

**Author:** `template-engineer`
**Date:** 2026-04-13
**Type:** Additive insertion (no deletions, no in-place rewrites).

## Inputs

- `DESIGN.md` (Cold Engineering Neutral, `[data-persona]` toggle, warm near-black primary CTA)
- `COPY.md` (10-section framework, banned vocabulary, slot map)
- `templates/ULTIMATE_TEMPLATE.html` (reference single-file HTML)
- `references/business_details.json` (slot schema)
- `_workspace/template/03_copy_decisions.md` (slot validation log)
- `.claude/skills/template-synthesis/SKILL.md` (patching convention)

## Insertion point

Original file was 676 lines. Patch inserts a single `## AUTHORITATIVE REFERENCES (READ FIRST — OVERRIDES EVERYTHING BELOW)` block between the existing Role section and the existing `## DESIGN PHILOSOPHY` section.

**Exact anchor (pre-patch):**

```
Line  7: You build websites for any local business … give them trust and a clear next step in 3 seconds.
Line  8: (blank)
Line  9: ---
Line 10: (blank)
Line 11: ## DESIGN PHILOSOPHY: YC STARTUP AESTHETIC FOR LOCAL BUSINESS (READ FIRST)
```

Patch inserted between line 10 (the blank after `---`) and line 11 (`## DESIGN PHILOSOPHY …`). The existing `## DESIGN PHILOSOPHY` block is NOT touched — it remains in place as a fallback. The old three-persona aesthetic (Bright & Bold / Copper & Cream / Safety First) is explicitly overridden by the new block, which names the override so the model doesn't need to reconcile ambiguity.

## Inserted block (full text)

See `prompts/website_builder.md` lines 11–136 (approx) after patch: `## AUTHORITATIVE REFERENCES (READ FIRST — OVERRIDES EVERYTHING BELOW)`. The block contains:

1. Pointer to `DESIGN.md`, `COPY.md`, `templates/ULTIMATE_TEMPLATE.html`.
2. Explicit override statement: "On conflict: DESIGN.md + COPY.md + ULTIMATE_TEMPLATE.html win."
3. Explicit retirement of the three-persona system in favor of single Cold Engineering Neutral direction with `[data-persona]` toggle.
4. Inlined DESIGN.md essentials — palette tokens, typography rules, component specs (buttons / cards / dividers / nav / icons), layout scale, depth rules, gradient rules, AI-slop kill list.
5. Inlined COPY.md essentials — voice split, headline formulas (max 14 words), CTA rules (near-black, sentence case, `Call {{business.phone}}` default), trust block patterns, review rules (verbatim, 30 words, never paraphrase), service card rules, FAQ rules, banned vocabulary (full / context / phrase), slot map + fallback rules.
6. Pointer to `templates/ULTIMATE_TEMPLATE.html` as skeleton.
7. Note that existing 15-point validation + readability audit below still runs unchanged.

## What was NOT touched

- Role section (lines 1–9).
- `## DESIGN PHILOSOPHY: YC STARTUP AESTHETIC FOR LOCAL BUSINESS` block and every rule after it. Old 800-weight h1 rule, old three-persona accent color matrix, old stock photo rules, etc. — all still present. New block explicitly overrides the contradicted items (weight cap, persona system, near-black primary CTA, wavy dividers, pill buttons).
- 15-point validation checklist.
- Readability audit.
- Unsplash photo conventions.

## Rollback instructions

1. Open `prompts/website_builder.md`.
2. Find the line `## AUTHORITATIVE REFERENCES (READ FIRST — OVERRIDES EVERYTHING BELOW)`.
3. Delete everything from that line through (and including) the terminating `---` directly before the original `## DESIGN PHILOSOPHY: YC STARTUP AESTHETIC FOR LOCAL BUSINESS (READ FIRST)` line.
4. Verify the file now jumps from the Role section's closing `---` straight to `## DESIGN PHILOSOPHY …`.
5. Run `python3 generate.py` on `references/business_details.json` (Spartan Electrical) — must still pass 15/15 validation + 0 readability warnings (the exact pre-patch behaviour).

Alternative (git): `git checkout HEAD -- prompts/website_builder.md` if no other edits to that file are pending.

## Slot map validation

Cross-checked against `_workspace/template/03_copy_decisions.md §Slot validation log` and `references/business_details.json`:

| Slot used in ULTIMATE_TEMPLATE.html | JSON field | Present in Spartan JSON? | Fallback |
|---|---|---|---|
| `{{business.name}}` | `business_name` | ✓ | required |
| `{{business.category}}` | `business_category` | ✓ | required |
| `{{business.city}}` | `city` | ✓ | required |
| `{{business.address}}` | `address` | ✓ | omit footer address line |
| `{{business.phone}}` | `phone_number` | ✓ | required — display string |
| `{{business.phone_tel}}` | derived from `phone_number` | computed | strip non-digits, prefix `+44` |
| `{{business.rating}}` | `rating` | ✓ | required |
| `{{business.review_count}}` | `review_count` | ✓ | required |
| `{{business.services_offered[]}}` | `services_offered[]` | ✓ (8) | required ≥3 |
| `{{business.reviews[]}}` | `google_reviews[]` | ✓ (5) | required ≥1 |
| `{{service_radius}}` | derived (city → postcode) | computed | vertical-default |
| `{{response_window}}` | derived (vertical default) | computed | 90min trades, same day professional, same week personal |
| `{{credential_marker}}` | derived (vertical + license whitelist) | computed | drop if no license AND no vertical default |
| `{{credential_short}}` | derived (credential acronym) | computed | drop if no license |
| `{{year}}` | current year | computed | — |
| (not used) `business.email` | `email` | ✗ missing | omit footer email line — NOT used in template |
| (not used) `business.years` | `years_experience` | ✗ missing | drop "trading since" card — NOT used in template |
| (not used) `business.license` | `license_number` | ✗ missing | drop accreditation badge — `credential_marker` derivation handles |

No invented fields. All slots map to either a real JSON field or an explicitly-documented derived slot.

## No-regression note

The patch is purely additive and sits ABOVE the existing rules. The existing prompt's 15-point validation, readability audit, Unsplash conventions, and Spartan-specific worked examples are all still in place. Where the new block and the old block disagree (h1 weight, persona system, primary CTA color, wavy dividers), the new block explicitly claims precedence via the "OVERRIDES EVERYTHING BELOW" header and the inline "… is now forbidden" annotations. Smoke test (template-critic, Phase 5) will validate against 3 synthetic businesses before ship.

If the smoke test regresses any of the 3 businesses, rollback per instructions above and retry with a narrower insertion (e.g. inline only the top 3 kill-list items instead of the full block).

## Fix pass — 2026-04-13 (post critic `fix_then_ship`)

**Finding (critic 05_critique.json):** All smoke builds failed `has_contact_form` validation because template intentionally shipped form-less (tel-CTA primacy). COPY.md §8 form-label bank had nowhere to render.

**Fix:** Option 1 (critic's preferred) — added a minimal contact form section to `templates/ULTIMATE_TEMPLATE.html` between the dark accent tel-CTA and the FAQ, plus a `### Contact form` requirement block inside the builder prompt overrides.

Changes:
- `templates/ULTIMATE_TEMPLATE.html`: +CSS rules for `.contact-form`, `.contact-form__grid`, `.form-card`, `.form-row`, `.form-field`, `.form-privacy`. +`<section class="contact-form" id="request">` markup with fields `Your name`, `Phone`, `Email`, `What do you need?` plus `Send request` submit + privacy microcopy. Copy matches COPY.md §8 verbatim. Form sits on `--surface-alt`. Inputs use `--border-input` solid 1px (DESIGN.md §4 input exemption for form debuggability), focus ring `0 0 0 3px var(--accent-subtle)`. Form card uses `--elev-2` shadow-as-border stack. Submit is full-width `.btn-primary` near-black. Tel-CTA accent section remains the primary close; form is secondary path. Total template: 524 → 599 lines.
- `prompts/website_builder.md`: inserted `### Contact form (secondary path — required for has_contact_form validation)` block inside AUTHORITATIVE REFERENCES, just before `### Reference HTML`. Names required labels, placement (after accent section, before FAQ), voice-specific h2 options, references the `#request` anchor in ULTIMATE_TEMPLATE.html.

Rollback for the fix pass: delete the `<section class="contact-form" id="request">…</section>` block and the `/* contact form (secondary path …) */` CSS block in the template; delete the `### Contact form` block in the builder prompt. Base patch rollback (above) is unaffected.

Low-severity flags from critic deferred this pass: latent contradicted lines in legacy DESIGN PHILOSOPHY block (weight-800 / 3-persona matrix), and hero radial-gradient blue opacity borderline vs §7 glow rule. Both acceptable as-is per override precedence.

## Fix pass 2 — 2026-04-13 (generate.py call_claude_cli shim)

**Finding (critic):** `call_claude_cli()` in `generate.py:162` passed the combined ~50KB prompt as a single argv argument. Smoke test trades sample hung for full 600s subprocess timeout. Zero output.

**Root cause:** `claude -p <PROMPT>` with a giant argv hit ARG_MAX / stdin ambiguity. `claude -p` is designed to take prompts via stdin when piped.

**Fix applied to `/Users/foxy/Hermes Bot/generate.py:162`:**
- Pipe user message via `input=user_message` (stdin), not argv.
- Pass full builder prompt via `--system-prompt` flag (keeps stdin small).
- Add `--output-format text` for clean plain-text response (default, but explicit for stability).
- Do NOT use `--bare` — it disables OAuth/keychain auth and requires `ANTHROPIC_API_KEY`, which breaks session auth.

**Verification (before re-running critic smoke test):**
- ~2KB synthetic prompt → 9.1s round trip, clean HTML output, rc=0.
- Full 64KB real builder prompt + minimal user message → 8.5s round trip, clean output, rc=0.
- Prior failure mode (600s hang) confirmed fixed.

**Rollback for this pass:** revert the `call_claude_cli` function in `generate.py` to the argv form. Git: `git checkout HEAD -- generate.py`.
