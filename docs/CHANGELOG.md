# CHANGELOG

## 2026-04-08 16:49
- Added `prospect_poor_websites_v2.py` for expanded Google Maps prospecting on businesses with websites.
- Implemented weighted rubric scoring (Technical 20, Mobile UX 20, Conversion 25, Trust 20, Visual Modernity 15).
- Added per-check evidence output, confidence score, and structured JSON export to `prospects/*-poor-websites-v2.json`.
- Added `--company` filter for single-company testing.
- Validated test run: `python3 prospect_poor_websites_v2.py "electrician" "Edinburgh" --limit 20 --top 1`.

## 2026-04-08 16:56
- Updated `prospect_poor_websites_v2.py` to support Firecrawl extraction via `FIRECRAWL_API_KEY` (env or .env).
- Added automatic fallback to raw HTML fetch when Firecrawl key missing/fails.
- Added `signals.firecrawl_used` flag in audit output for traceability.

## 2026-04-08 17:12
- Added strategy document `STRATEGY_BUILD_FIRST_PITCH_NEVER.md` capturing Build-First operating model and Phase-1 execution rules.

## 2026-04-08 17:18
- Added `mission_control.py` localhost dashboard with lifecycle phases, KPI progress, broken/in-progress/not-started status, and JSON API endpoint `/api/status`.
- Added CLI mode `--print-status` for terminal snapshots.
- Started dashboard server on `http://127.0.0.1:8787`.

## 2026-04-08 17:20
- Mission Control: added `/vision` page showing strategy vision, built code components, lifecycle phase statuses, and current broken items.
- Main dashboard now links to Vision + Build Reality page.

## 2026-04-08 17:24
- Mission Control `/vision`: added visual architecture map with health-colored built nodes (healthy/warning/broken) and shadowed unbuilt nodes.
- Map includes lifecycle flow + component flow with current live metrics and quality-gate status.

## 2026-04-08 17:26
- Redesigned Mission Control pages with Tailwind CSS (CDN) and unified top navigation across Dashboard and Vision pages.
- Kept architecture map and phase/status rendering intact under new UI shell.

## 2026-04-08 17:31
- Rebuilt Mission Control UI shell using HeroUI (React via esm.sh) for both Dashboard and Vision pages.
- Added shared HeroUI navigation (Dashboard / Vision / JSON) and componentized cards/chips layout.
- Kept backend metrics and architecture-map logic unchanged; rendered through HeroUI frontend layer.
