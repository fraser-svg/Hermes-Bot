# Hermes Bot - Project Instructions

## Communication Mode

Caveman ultra always on. No exceptions. Drop articles, filler, pleasantries, hedging. Fragments OK. Technical terms exact. Code blocks unchanged. Errors quoted exact. Resume normal voice only for: security warnings, irreversible action confirmations.

## What This Project Does

Hermes builds high-converting, single-page websites for local service businesses (electricians, plumbers, roofers, cleaners, etc). It uses Gemini via OpenRouter to generate production-ready HTML from a structured design system.

## Website Generation - ALWAYS USE THIS SYSTEM

When asked to build, create, generate, or make a website:

1. **NEVER hand-write HTML/CSS.** Always use `generate.py` which calls Gemini with the full design system prompt.
2. **NEVER skip the design system.** The prompt at `prompts/website_builder.md` contains the entire design methodology: personas, golden rules, readability checks, stock photos, typography, color rhythm. It is the result of extensive research into what makes real premium service sites convert. Do not bypass it.
3. **NEVER use the old `main.py` or `website_generator.py`.** Those are legacy. `generate.py` is the current system.

### How to Build a Website

```bash
python3 generate.py
```

That's it. The script:
- Reads business data from `references/business_details.json`
- Loads the design system prompt from `prompts/website_builder.md`
- Auto-selects a design persona (Bright & Bold / Copper & Cream / Safety First)
- Calls Gemini via OpenRouter
- Outputs a complete single-file HTML website with real Unsplash photos
- Runs 15 validation checks + 6-point readability audit
- Writes output to `output/{slug}.html` and `index.html`

### Before Building

Update `references/business_details.json` with the client's info. Required fields:

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

The design prompt (`prompts/website_builder.md`) enforces:

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

## File Structure

```
generate.py              - Main build script (USE THIS)
prompts/website_builder.md - Gemini system prompt (design system)
references/business_details.json - Client data input
output/                  - Generated websites
index.html               - Latest build preview
build_report.json        - Latest build validation report
LOCAL_SERVICE_WEBSITE_BLUEPRINT.md - Reference documentation

main.py                  - LEGACY, do not use
website_generator.py     - LEGACY, do not use
```

## Deployment

Sites deploy to **Cloudflare Pages** (free, unlimited bandwidth). Auth via `npx wrangler login` (OAuth, no API token).

```bash
python3 deploy.py                          # deploy all un-deployed sites
python3 deploy.py output/some-business.html  # deploy one site
python3 deploy.py --list                   # list all deployed sites
```

Sites go live at `h-{slug}-{hash}.pages.dev`. Deploy log: `prospects/deploys.json`.

## API Keys

Stored in `.env`. Uses `openrouter` key to call Gemini via OpenRouter.
Model: `google/gemini-2.5-pro` (update to `google/gemini-3.1-pro` when available).

## Rules

- Every website must pass 15/15 validation AND 0 readability warnings before delivery
- Never deliver a site with unreadable text
- Never use placeholder gray boxes instead of real photos
- Never hand-code websites outside the generate.py pipeline
- If a client needs something the system can't handle, update the prompt - don't work around it
