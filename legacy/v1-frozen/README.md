# Hermes Bot

Autonomous agent that finds local service businesses without websites (via Google Maps), builds them premium websites (via Gemini 3.1 Pro), and manages outreach.

## Quick Start

```bash
# Chat mode
python3 hermes.py

# Find businesses without websites
python3 prospect.py "electrician" "Edinburgh"

# Build a website
python3 generate.py

# Find + build in one shot
python3 prospect.py "electrician" "Edinburgh" --build-first
```

## Setup

Add to `.env`:
```
openrouter=your_openrouter_key
GOOGLE_MAPS_API=your_google_maps_key
```

Enable "Places API (New)" in Google Cloud Console.

## Stack

- **GPT 4.1 Mini** (via OpenRouter) - chat brain, command routing
- **Gemini 3.1 Pro Preview** (via OpenRouter) - website generation
- **Google Maps Places API** - business prospecting
- **Unsplash** - stock photography

## Files

| File | Purpose |
|------|---------|
| `hermes.py` | Chat agent |
| `generate.py` | Website builder (Gemini 3.1 Pro) |
| `prospect.py` | Google Maps prospector |
| `prompts/website_builder.md` | Design system (500+ lines) |
| `prompts/hermes_system_prompt.md` | GPT instructions |
| `MASTER_INIT_BRIEF.md` | Full init brief for Hermes |

## Business Model

- Entry: 29-99/month
- Upsell: 300-800/month within 6 months
- Vector: businesses with Google reviews but no website
