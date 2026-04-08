"""Stage 1: Local Content Generation via Ollama (FREE).

Generates all website copy from business details using a local model.
Outputs a structured JSON that Stage 2 (generate.py) feeds to Gemini
for HTML/CSS design only.

This handles:
- Hero headline and subhead
- Service descriptions
- About section copy
- Differentiators/trust badges
- Additional reviews (if < 3 provided)
- Area/neighborhood names
- Meta description
- CTA text

Usage:
    python3 content_gen.py                    # generate content for current business
    python3 content_gen.py --model gemma4     # specify model
"""

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
CONTENT_PATH = BASE_DIR / "references" / "generated_content.json"

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma4"

CONTENT_PROMPT = """\
You are a direct, no-nonsense copywriter for local service businesses. \
You write like a confident tradesperson, not a marketing agency. \
Short sentences. Specific facts. No jargon. No buzzwords.

BANNED WORDS: revolutionary, unmatched, cutting-edge, state-of-the-art, \
synergy, leverage, experience the best, comprehensive solutions, \
pride ourselves, committed to excellence, your trusted partner.

Given this business data, generate ALL the website copy as a JSON object. \
Every piece of text must be specific to THIS business in THIS city. \
If you could swap the business name and the copy still works, it's too generic. Rewrite it.

Return ONLY valid JSON. No explanation. No markdown fences.
"""

CONTENT_SCHEMA = """\
Return this exact JSON structure:
{
  "hero_headline": "Short, punchy. Include city name and service. Max 8 words.",
  "hero_subhead": "1-2 sentences. State facts: years, rating, response time. Max 25 words.",
  "services": [
    {
      "name": "Service Name",
      "description": "What happens when they hire you for this. 1-2 sentences. Specific."
    }
  ],
  "about_heading": "Why Choose [Business Name]",
  "about_text": "2-3 sentences. Who they are, how long, what they stand for. Human voice.",
  "differentiators": [
    "Specific verifiable claim (e.g. 'NICEIC registered since 2015')",
    "Another fact (e.g. 'Same-day emergency response')",
    "Another fact (e.g. 'Fixed pricing, no hidden fees')",
    "Another fact (e.g. 'All work guaranteed for 12 months')"
  ],
  "reviews": [
    {
      "rating": 5,
      "text": "Realistic review mentioning specific work done. 1-2 sentences.",
      "author": "First Name L., Neighborhood"
    }
  ],
  "area_names": ["Neighborhood1", "Neighborhood2", "at least 8 areas near the city"],
  "meta_description": "Under 160 chars. [Business] provides [service] in [city]. [fact]. Call [phone].",
  "cta_primary": "Short action text for main button (e.g. 'Get a free quote')",
  "cta_secondary": "Short text for secondary button (e.g. 'Call now')",
  "stats": {
    "jobs_completed": "Estimated number (review_count * 15-25)",
    "years_experience": "Number or 'X+'",
    "satisfaction": "100%",
    "response_time": "Estimated (e.g. 'Under 2 hours')"
  }
}
"""


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def call_ollama(model: str, system_prompt: str, user_message: str) -> str:
    """Call local Ollama model. Returns response text."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 4000,  # Content is small, not a full HTML page
        }
    }).encode("utf-8")

    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, Exception) as e:
        raise RuntimeError(f"Ollama error: {e}") from e

    return body.get("message", {}).get("content", "")


def call_openrouter_cheap(user_message: str) -> str:
    """Fallback: call a cheap model via OpenRouter if Ollama unavailable."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or load_env().get("openrouter")
    if not api_key:
        raise RuntimeError("No OpenRouter key and Ollama unavailable")

    payload = json.dumps({
        "model": "google/gemma-4-26b-a4b-it",  # $0.13/M input - dirt cheap
        "messages": [
            {"role": "system", "content": CONTENT_PROMPT + "\n\n" + CONTENT_SCHEMA},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 4000,
        "temperature": 0.4,
    }).encode("utf-8")

    req = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://hermes-bot.local",
            "X-Title": "Hermes Content Gen",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"OpenRouter error: {error_body}") from e

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError("No response from cheap model")
    return choices[0]["message"]["content"]


def extract_json(text: str) -> dict:
    """Extract JSON from model response."""
    import re
    # Try code fence first
    fence = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    # Try raw JSON
    brace_start = text.find("{")
    brace_end = text.rfind("}") + 1
    if brace_start >= 0 and brace_end > brace_start:
        return json.loads(text[brace_start:brace_end])
    raise ValueError(f"No JSON found in response: {text[:200]}")


def ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        req = Request("http://localhost:11434/api/tags", method="GET")
        with urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def generate_content(details: dict, model: str = DEFAULT_MODEL) -> dict:
    """Generate all website copy from business details."""
    user_message = (
        f"Generate website copy for this business:\n\n"
        f"```json\n{json.dumps(details, indent=2)}\n```\n\n"
        f"Return the JSON structure described. Every piece of text must be specific to "
        f"{details['business_name']} in {details['city']}. Include the city name in headlines. "
        f"Generate {max(3 - len(details.get('google_reviews', [])), 0)} additional realistic reviews "
        f"if fewer than 3 are provided. "
        f"Generate at least 8 area/neighborhood names near {details['city']}."
    )

    system = CONTENT_PROMPT + "\n\n" + CONTENT_SCHEMA

    use_local = ollama_available()
    raw = None

    if use_local:
        print(f"  Content gen: Ollama ({model}) [FREE]")
        start = time.time()
        try:
            raw = call_ollama(model, system, user_message)
            duration = time.time() - start
            cost = "$0.00"
        except Exception as e:
            print(f"  Local model failed ({e}), falling back to cheap API...")
            use_local = False

    if not use_local or raw is None:
        print("  Content gen: OpenRouter (gemma-4-26b) [~$0.002]")
        start = time.time()
        raw = call_openrouter_cheap(system + "\n\n" + user_message)
        duration = time.time() - start
        cost = "~$0.002"

    try:
        content = extract_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  WARNING: Failed to parse content JSON: {e}")
        print(f"  Raw response (first 500 chars): {raw[:500]}")
        # Return minimal fallback so generate.py can still work
        content = {
            "hero_headline": f"{details.get('business_category', 'Service').title()} in {details['city']}",
            "hero_subhead": f"{details.get('rating', 4.8)}-star rated. Call {details.get('phone_number', '')}.",
            "services": [{"name": s, "description": ""} for s in details.get("services_offered", [])],
            "about_heading": f"Why choose {details['business_name']}",
            "about_text": f"Local {details.get('business_category', 'service')} business in {details['city']}.",
            "differentiators": ["Licensed & insured", "Local business", "Competitive pricing", "Free quotes"],
            "reviews": details.get("google_reviews", []),
            "area_names": [details["city"]],
            "meta_description": f"{details['business_name']} - {details.get('business_category', '')} in {details['city']}.",
            "cta_primary": "Get a free quote",
            "cta_secondary": "Call now",
            "stats": {"jobs_completed": "100+", "years_experience": "10+", "satisfaction": "100%", "response_time": "Same day"},
            "_fallback": True,
        }

    content["_generation"] = {
        "model": model if use_local else "google/gemma-4-26b-a4b-it",
        "local": use_local,
        "cost": cost,
        "duration_sec": round(duration, 1),
    }

    return content


def main():
    model = DEFAULT_MODEL
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--model" and i + 1 < len(sys.argv) - 1:
            model = sys.argv[i + 2]

    if not DETAILS_PATH.exists():
        print("No business_details.json found.")
        sys.exit(1)

    details = json.loads(DETAILS_PATH.read_text())
    print(f"Generating content for: {details['business_name']}")

    content = generate_content(details, model)
    CONTENT_PATH.write_text(json.dumps(content, indent=2))

    print(f"  Saved to: {CONTENT_PATH}")
    print(f"  Cost: {content['_generation']['cost']}")
    print(f"  Time: {content['_generation']['duration_sec']}s")
    print(f"  Fallback: {content.get('_fallback', False)}")

    # Preview
    print(f"\n  Headline: {content.get('hero_headline', '?')}")
    print(f"  Subhead: {content.get('hero_subhead', '?')}")
    print(f"  Services: {len(content.get('services', []))}")
    print(f"  Reviews: {len(content.get('reviews', []))}")
    print(f"  Areas: {len(content.get('area_names', []))}")


if __name__ == "__main__":
    main()
