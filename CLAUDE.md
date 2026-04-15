# Hermes Bot - Project Instructions

## 하네스: Hermes Website Design Pipeline

**목표:** Build high-design local-service websites via 4-agent team (aesthetic-director → site-builder → design-critic → surgical-fixer).

**트리거:** Any request to build/create/generate/improve/fix/redesign a Hermes website → use `hermes-design-harness` skill. Simple questions can answer directly.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-13 | 초기 구성 | 전체 | Improve website quality via frontend-design skill integration |

## 하네스: Ultimate Local Service Template

**목표:** Maintain a master `DESIGN.md` + `COPY.md` + `templates/ULTIMATE_TEMPLATE.html` via a 5-agent team (web-design experts + copywriters). Output feeds `prompts/website_builder.md` so every per-business Hermes build inherits the template.

**트리거:** Requests to build/redesign/improve/iterate the master template, design system, copy framework, `DESIGN.md`, `COPY.md`, or preview catalog → use `ultimate-template-builder` skill. Follow-ups: "tighten hero copy", "redo the palette", "update the template", "rebuild master template". Per-business builds still route to `hermes-design-harness`, not here.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-13 | 초기 구성 | agents/market-researcher, design-system-architect, conversion-copywriter, template-engineer, template-critic; skills/ultimate-template-builder, design-md-research, design-md-authoring, copy-md-framework, template-synthesis, template-critique; templates/ (planned output: DESIGN.md, COPY.md, preview.html, preview-dark.html, templates/ULTIMATE_TEMPLATE.html) | Adopt Google Stitch DESIGN.md standard (per VoltAgent/awesome-design-md, 66 curated exemplars) + companion COPY.md for dedicated copywriting layer. Produces reusable master template feeding hermes-design-harness. |

## 하네스: No-Website Prospector

**목표:** Find UK local-service businesses without a website (or with broken/placeholder websites), auto-generate a professional site via the Hermes pipeline, deploy to Cloudflare Pages, and append each prospect to an outreach CSV with name, location, phone, email, and live site URL.

**트리거:** Any request to find/qualify/build/outreach businesses with no website → use `no-website-prospector` skill. Follow-ups: "more no-website leads", "rerun no-website", "redo outreach for {slug}", "build site for {business}", "find companies with no website". Distinct from retarget-prospector (which requires active paid ads).

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-14 | 초기 구성 | agents/no-website-qualifier; skills/no-website-prospector (+ references/qualification-gates.md); run_nowebsite_pipeline.py, emit_nowebsite_outreach.py | Extend harness to cover no-website cohort. Reuses prospect.py (Places filter), generate.py (build), deploy.py (Cloudflare), hermes-design-harness (per-site quality loop). New gates lower floors vs retarget (rating ≥3.8, reviews ≥10, phone required) since no-website businesses rarely invest in digital reputation. Cohorts A_greenfield > B_broken > C_placeholder by priority. |
| 2026-04-14 | build step swap → Claude-Code template fill | skills/template-site-builder (+ references/slot-map.md, copy-instructions.md, vertical-defaults.json, evals/evals.json); fill_template.py, validate_filled_html.py; emit_nowebsite_outreach.py (+current_website_url, +cohort columns) | OpenRouter 402 blocked generate.py (Gemini). New template-site-builder skill orchestrates fill_template.py (data+derived slots) then Claude Code itself authors 21 copy slots via COPY.md + frontend-design skill, validates, deploys, CSVs. Zero OpenRouter spend. Smoke test: stirling-burt-heating live at h-stirling-burt-heating-1c0f57.pages.dev, validator 15/15. All 3 cohorts (A_greenfield/B_broken/C_placeholder) are in scope — the built site is the outreach deliverable for all of them. |

## 하네스: Retarget Prospector

**목표:** Find local businesses actively running paid ads (Meta/Google/LinkedIn) but missing retargeting pixels, qualify by leak severity, and auto-send personalized cold outreach.

**트리거:** Any request to find/qualify/outreach businesses with ad leaks, missing pixels, or retargeting opportunities → use `retarget-prospector` skill. Includes follow-ups: "more leads", "rerun retarget", "redo outreach for {slug}". Simple questions answer directly.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-13 | 초기 구성 | agents/ad-intel-scout, pixel-auditor, retarget-qualifier, outreach-composer; skills/retarget-prospector, ad-verification, pixel-leak-analysis, retarget-pitch-patterns, whatsapp-outreach | Build retarget-leak prospecting + outreach pipeline wrapping prospect_no_pixel.py and cold_email.py |
| 2026-04-13 | validation harness + gates | validation/ground_truth.json, validation/preflight.py, validation/eval_detectors.py, validation/smoke_test_results.md; skills/ad-verification (confidence calc: unknown ≠ false); agents/retarget-qualifier (scoring only counts confirmed_platforms, audit_gaps blocks auto-send); skills/retarget-prospector (Phase 0a preflight, Phase 4b mandatory composer grounding gate, dry-run default); agents/outreach-composer (grounding enforcement note) | Pre-production validation: kill silent scraper failures, block false positives from unknown collapse, enforce composer hallucination guard, make dry-run the default |
| 2026-04-13 | swap static pixel audit → rendered playwright v2 | prospect_no_pixel.py (_rendered_pixel_override, --static-only flag); validation/eval_detectors.py (audit_pixels_v2 integration with shared browser context cache) | Eval caught static regex recall = 0.00 on known retargeters (Stripe/HubSpot/Shopify) because GTM-injected pixels are invisible to urllib. Rendered v2 achieves 100% recall + 100% precision on ground truth. Production path now runs rendered audit by default; static only via --static-only debug flag. |
| 2026-04-13 | Meta Ad Library token-free scraper path | prospect_no_pixel.py (check_meta_ads → check_meta_ads_scrape fallback when no token); validation/preflight.py (scraper probe against Monzo); .claude/skills/ad-verification/scripts/check_meta_ad_library.py (DOM-free body-text parser, strict page-name filter requiring Page name + "Sponsored" line); validation/eval_detectors.py (playwright sync context teardown between detector groups) | User cannot wait 2 days for Meta ID verification. Swapped in public Meta Ad Library scraper that needs no token. Discovered stale div[role="article"] selector (Meta DOM changed), rewrote card parser to split body text on "Library ID:" markers. Discovered keyword-search false positives (Wikipedia keyword = ads mentioning Wikipedia, not Wikipedia's own ads) — added strict page-name filter requiring the business name appear as a Page-name line followed by "Sponsored". Also discovered Wikipedia genuinely runs Meta ads (Wikimedia Foundation), relabelled ground truth. Final meta_library detector: precision 1.00, recall 1.00, FP rate 0.00 on 5 labelled entries (Monzo, Wikipedia true; example.com, python.org, gnu.org false). |
| 2026-04-13 | ICP rewrite: Google-Ads-required + Meta cohort segmentation | skills/retarget-prospector/references/icp.md (new — 7 hard gates: geo/category/google_ads/website/trust/size/meta_cohort with whitelist/blacklist + verdict map); skills/retarget-prospector/SKILL.md (ICP summary block, Phase 1 whitelist precheck + UK city enforcement, Phase 4 qualifier reads icp.md and emits cohort A/B/C); agents/retarget-qualifier.md (description rewrite, gate-ordered scoring algorithm, cohort assignment replacing leak_surface scoring, new verdict enum, expanded `_qualified.json` schema with `cohort` + `icp_gates` + `meta_status` + `google_ads_evidence`); agents/ad-intel-scout.md (added `meta_creative_count` requirement, GATC-or-site-tag fallback note for Gate 3) | Pivot from "any platform leak" to "UK Google-Ads spenders with Meta retargeting gap" — considered-purchase verticals only (dentists/clinics/solicitors/accountants/etc), Google Ads is the hard gate (GATC OR site Conversion Tag), Meta status segments into Cohort A (dormant pixel) / B (greenfield) / C (active ads + infra gap, highest priority). Trust + size + website are hard rejects, not bonuses. Order of evaluation: cheap rejects first (geo→category→google_ads→web→trust→size), cohort assignment last. |

## Communication Mode

Caveman ultra always on. No exceptions. Drop articles, filler, pleasantries, hedging. Fragments OK. Technical terms exact. Code blocks unchanged. Errors quoted exact. Resume normal voice only for: security warnings, irreversible action confirmations.

## What This Project Does

Hermes builds high-converting, single-page websites for local service businesses (electricians, plumbers, roofers, cleaners, etc). It uses Gemini via OpenRouter to generate production-ready HTML from a structured design system.

## Website Generation - ALWAYS USE THIS SYSTEM

When asked to build, create, generate, or make a website:

1. **NEVER hand-write HTML/CSS.** Always use `core/generate.py` which calls Gemini with the full design system prompt.
2. **NEVER skip the design system.** The prompt at `core/prompts/website_builder.md` contains the entire design methodology: personas, golden rules, readability checks, stock photos, typography, color rhythm. It is the result of extensive research into what makes real premium service sites convert. Do not bypass it.
3. **NEVER use the old `main.py` or `website_generator.py`.** Those are legacy (now under `legacy/`). `core/generate.py` is the current system.

### How to Build a Website

```bash
python3 -m core.generate
```

That's it. The script:
- Reads business data from `core/references/business_details.json`
- Loads the design system prompt from `core/prompts/website_builder.md`
- Auto-selects a design persona (Bright & Bold / Copper & Cream / Safety First)
- Calls Gemini via OpenRouter
- Outputs a complete single-file HTML website with real Unsplash photos
- Runs 15 validation checks + 6-point readability audit
- Writes output to `output/{slug}.html` and `index.html`

### Before Building

Update `core/references/business_details.json` with the client's info. Required fields:

```json
{
  "business_name": "Required",
  "business_category": "Required (electrician, plumber, roofer, hvac, cleaner, painter, locksmith, mover, pest control, landscaper)",
  "city": "Required",
  "phone_number": "Required",
  "services_offered": ["At least 3 services"],
  "google_reviews": [{"rating": 5, "text": "Real review text"}],
  "rating": 4.8,
  "review_count": 50
}
```

Optional fields: `address`, `years_experience`, `license_number`, `persona` (override auto-selection), `style_mix` (override default Mix & Match).

### After Building

- Check the validation score (target: 15/15)
- Check readability warnings (target: 0 warnings)
- Open `index.html` in a browser to preview
- If readability fails, DO NOT ship. Fix the issues first.

## Design System Overview

The design prompt (`core/prompts/website_builder.md`) enforces:

- **3 personas:** Bright & Bold (modern), Copper & Cream (premium traditional), Safety First (corporate clean)
- **Dark photo hero** with gradient overlay + bold white text (like Benjamin Franklin Plumbing, Genz-Ryan, Smock HVAC)
- **Light canvas body** with alternating section backgrounds
- **One bold accent section** breaking the light rhythm
- **Dark footer** anchoring the bottom
- **Real Unsplash stock photos** (no placeholders)
- **SVG section dividers** (waves/angles between hero and content)
- **60-30-10 color rule**, **4.5:1 contrast minimum**, **650px max text width**
- **text-shadow on all white-on-image text** for readability
- **Mandatory readability audit** as final build step

## Website Review

After building, run the AI-powered critical reviewer:

```bash
python3 -m core.review pipelines/design_harness/output/some-business.html  # review specific file
python3 -m core.review                                                      # review latest (index.html)
python3 -m core.review --cheap                                              # use Gemini Flash (cheaper)
```

Grades 4 dimensions (1-10): Design, UX, Content, Flow. Uses Playwright CLI for desktop + mobile screenshots, sends to Claude Sonnet via OpenRouter for vision-based review. Returns actionable fixes for anything scoring below 7. Report saves to `review_report.json`.

First run: requires `npx playwright install chromium` (auto-prompted).

## File Structure

```
core/generate.py                 - Main build script (USE THIS)
core/review.py                   - AI-powered critical website reviewer
core/deploy.py                   - Cloudflare Pages deploy
core/fill_template.py            - Template slot fill (no-website pipeline)
core/prompts/website_builder.md  - Gemini system prompt (design system)
core/references/business_details.json - Client data input
core/templates/ULTIMATE_TEMPLATE.html  - Master template
pipelines/design_harness/output/ - Per-business Gemini builds
pipelines/no_website_prospector/output/ - Template-filled builds
pipelines/retarget_prospector/output/ - Retarget reports
index.html                       - Latest build preview
build_report.json                - Latest build validation report
review_report.json               - Latest review grade card

legacy/                          - Quarantined (main.py, hermes.py, v1-frozen/, etc)
```

## Deployment

Sites deploy to **Cloudflare Pages** (free, unlimited bandwidth). Auth via `npx wrangler login` (OAuth, no API token).

```bash
python3 -m core.deploy                                                 # deploy all un-deployed sites
python3 -m core.deploy pipelines/design_harness/output/some-business.html  # deploy one site
python3 -m core.deploy --list                                          # list all deployed sites
```

Sites go live at `h-{slug}-{hash}.pages.dev`. Deploy log: `core/deploys.json`.

## API Keys

Stored in `.env`. Uses `openrouter` key to call Gemini via OpenRouter.
Model: `google/gemini-2.5-pro` (update to `google/gemini-3.1-pro` when available).

## Rules

- Every website must pass 15/15 validation AND 0 readability warnings before delivery
- Never deliver a site with unreadable text
- Never use placeholder gray boxes instead of real photos
- Never hand-code websites outside the core/generate.py pipeline
- If a client needs something the system can't handle, update the prompt - don't work around it
