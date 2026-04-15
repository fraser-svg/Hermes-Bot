"""Hybrid Generator - 2 Stage Pipeline.

Stage 1: Local Ollama (FREE) or cheap API generates all website copy
Stage 2: Gemini 3.1 Pro (PAID) does HTML/CSS design with pre-written content

Cost: ~$0.15/site instead of ~$0.42/site (65% savings)

Usage:
    python3 generate_hybrid.py              # auto (Ollama if available, else cheap API)
    python3 generate_hybrid.py --local-only # force local Ollama
    python3 generate_hybrid.py --compare    # build with both hybrid and full pipeline, compare
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
CONTENT_PATH = BASE_DIR / "references" / "generated_content.json"
DESIGN_PROMPT_PATH = BASE_DIR / "prompts" / "design_only.md"
REPORT_PATH = BASE_DIR / "build_report.json"
OUTPUT_PATH = BASE_DIR / "output"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_MODEL = "google/gemini-3.1-pro-preview"

# Import shared functions
from generate import (
    load_env, get_api_key, extract_html, audit_readability, auto_select_accent,
)
from content_gen import generate_content, ollama_available


def load_business_details() -> dict:
    if not DETAILS_PATH.exists():
        raise FileNotFoundError(f"No business details at {DETAILS_PATH}")
    data = json.loads(DETAILS_PATH.read_text())
    required = ["business_name", "phone_number", "city"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return data


def build_design_message(details: dict, content: dict) -> str:
    """Build the user message for Stage 2 (design only)."""
    accent = details.get("accent_color") or auto_select_accent(details)

    # Stock photo URLs by category
    photo_map = {
        "electrician": ("photo-1621905251189-08b45d6a269e", "photo-1504328345606-18bbc8c9d7d1"),
        "plumber": ("photo-1585704032915-c3400ca199e7", "photo-1581578731548-c64695cc6952"),
        "dentist": ("photo-1629909613654-28e377c37b09", "photo-1612349317150-e413f6a5b16d"),
        "lawyer": ("photo-1589829545856-d10d557cf95f", "photo-1556157382-97eda2d62296"),
        "solicitor": ("photo-1589829545856-d10d557cf95f", "photo-1556157382-97eda2d62296"),
        "barber": ("photo-1560066984-138dadb4c035", "photo-1522337360788-8b13dee7a37e"),
        "roofer": ("photo-1504307651254-35680f356dfd", "photo-1574359411659-15573a27fd0c"),
        "vet": ("photo-1548199973-03cce0bbc87b", "photo-1587300003388-59208cc962cb"),
        "mechanic": ("photo-1487754180451-c456f719a1fc", "photo-1619642751034-765dfdf7c58e"),
        "photographer": ("photo-1452587925148-ce544e77e70d", "photo-1554048612-b6a482bc67e5"),
    }
    category = details.get("business_category", "").lower()
    hero_id, about_id = photo_map.get(category, ("photo-1497366216548-37526070297c", "photo-1556157382-97eda2d62296"))

    # Combine business details + generated content into one payload for Gemini
    design_data = {
        "business_name": details["business_name"],
        "business_category": details.get("business_category", "service"),
        "city": details["city"],
        "phone_number": details["phone_number"],
        "address": details.get("address", details["city"]),
        "accent_color": accent,
        "hero_image_url": f"https://images.unsplash.com/{hero_id}?w=1600&h=1000&fit=crop&auto=format&q=80",
        "about_image_url": f"https://images.unsplash.com/{about_id}?w=600&h=400&fit=crop&auto=format&q=80",
        "content": content,
    }

    return (
        "Build a complete single-file HTML website using the pre-written content below. "
        "Do NOT rewrite the copy. Use it exactly as provided. Your job is ONLY layout and styling. "
        "Return ONLY the HTML document, no explanations.\n\n"
        f"```json\n{json.dumps(design_data, indent=2)}\n```"
    )


def call_gemini_design(design_prompt: str, user_message: str, api_key: str) -> str:
    """Call Gemini with the slim design-only prompt."""
    payload = json.dumps({
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": design_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 32000,
        "temperature": 0.3,
    }).encode("utf-8")

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://hermes-bot.local",
            "X-Title": "Hermes Hybrid Builder",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"Gemini API error {e.code}: {error_body}") from e

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"No response: {json.dumps(body)}")
    return choices[0]["message"]["content"]


def generate_hybrid() -> dict:
    """Two-stage pipeline: local content gen + API design."""
    details = load_business_details()
    api_key = get_api_key()
    accent = details.get("accent_color") or auto_select_accent(details)

    print(f"Generating website for: {details['business_name']}")
    print(f"Category: {details.get('business_category', 'general')}")
    print(f"Accent: {accent}")
    print(f"City: {details['city']}")
    print()

    # STAGE 1: Content generation (free or cheap)
    print("STAGE 1: Content Generation")
    content = generate_content(details)
    CONTENT_PATH.write_text(json.dumps(content, indent=2))
    gen_info = content.get("_generation", {})
    print(f"  Model: {gen_info.get('model', '?')}")
    print(f"  Local: {gen_info.get('local', '?')}")
    print(f"  Cost: {gen_info.get('cost', '?')}")
    print(f"  Time: {gen_info.get('duration_sec', '?')}s")
    print()

    # STAGE 2: HTML/CSS design (paid, but slim prompt)
    print("STAGE 2: HTML/CSS Design")
    print(f"  Model: {GEMINI_MODEL}")

    design_prompt = DESIGN_PROMPT_PATH.read_text()
    user_message = build_design_message(details, content)

    # Estimate cost savings
    prompt_tokens = len(design_prompt.encode()) // 4 + len(user_message.encode()) // 4
    full_prompt_tokens = 45000  # what the full pipeline uses
    print(f"  Prompt tokens: ~{prompt_tokens:,} (full pipeline: ~{full_prompt_tokens:,})")
    print(f"  Savings: ~{(1 - prompt_tokens/full_prompt_tokens) * 100:.0f}% fewer input tokens")
    print(f"  Calling Gemini...")

    start = time.time()
    raw = call_gemini_design(design_prompt, user_message, api_key)
    duration = time.time() - start
    html = extract_html(raw)
    print(f"  Done in {duration:.1f}s")

    # Write output
    OUTPUT_PATH.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", details["business_name"].lower()).strip("-")
    html_file = OUTPUT_PATH / f"{slug}.html"
    html_file.write_text(html)
    (BASE_DIR / "index.html").write_text(html)

    # Validate
    checks = {
        "has_tel_link": "tel:" in html,
        "has_contact_form": "<form" in html.lower(),
        "has_schema_markup": "application/ld+json" in html,
        "has_meta_description": 'name="description"' in html.lower(),
        "has_responsive_viewport": 'name="viewport"' in html.lower(),
        "has_sticky_nav": "sticky" in html.lower() or "fixed" in html.lower(),
        "has_reviews_section": "review" in html.lower(),
        "has_services_section": "service" in html.lower(),
        "phone_in_html": details["phone_number"] in html,
        "business_name_in_html": details["business_name"] in html,
        "has_google_fonts": "fonts.googleapis.com" in html,
        "has_max_width_constraint": "max-width" in html and "650" in html,
        "has_unsplash_images": "images.unsplash.com" in html,
        "has_hero_photo_bg": "background-image" in html and "unsplash" in html,
    }
    readability_warnings = audit_readability(html)
    checks["readability_pass"] = len(readability_warnings) == 0

    passed = sum(checks.values())
    total = len(checks)
    score = round(passed / total * 10, 1)

    # Estimate total cost
    output_tokens = len(html.encode()) // 4
    stage2_cost = (prompt_tokens * 2.0 + output_tokens * 12.0) / 1_000_000
    stage1_cost = 0.0 if gen_info.get("local") else 0.002
    total_cost = stage1_cost + stage2_cost

    report = {
        "success": True,
        "pipeline": "hybrid",
        "business": details["business_name"],
        "category": details.get("business_category", "general"),
        "accent": accent,
        "city": details["city"],
        "stage1": {
            "model": gen_info.get("model", "?"),
            "local": gen_info.get("local", False),
            "cost": gen_info.get("cost", "?"),
            "duration_sec": gen_info.get("duration_sec", 0),
        },
        "stage2": {
            "model": GEMINI_MODEL,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "cost": f"${stage2_cost:.4f}",
            "duration_sec": round(duration, 1),
        },
        "total_cost": f"${total_cost:.4f}",
        "output_file": str(html_file),
        "index_file": str(BASE_DIR / "index.html"),
        "validation": {
            "score": f"{score}/10",
            "passed": passed,
            "total": total,
            "checks": checks,
        },
        "readability": {
            "pass": len(readability_warnings) == 0,
            "warnings": readability_warnings,
        },
        "html_size_kb": round(len(html.encode("utf-8")) / 1024, 1),
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2))

    print(f"\nBuild complete: {score}/10 validation score")
    print(f"Output: {html_file}")
    print(f"Size: {report['html_size_kb']}KB")

    if readability_warnings:
        print(f"\nREADABILITY WARNINGS ({len(readability_warnings)}):")
        for w in readability_warnings:
            print(f"  - {w}")
    else:
        print("Readability audit: PASS")

    print(f"\nCOST BREAKDOWN:")
    print(f"  Stage 1 (content): {gen_info.get('cost', '?')}")
    print(f"  Stage 2 (design):  ${stage2_cost:.4f}")
    print(f"  TOTAL:             ${total_cost:.4f}")
    print(f"  vs full pipeline:  ~$0.4200")
    print(f"  SAVED:             ~{(1 - total_cost/0.42) * 100:.0f}%")

    return report


if __name__ == "__main__":
    try:
        result = generate_hybrid()
        print(json.dumps(result, indent=2))
    except Exception as e:
        error = {"success": False, "error": str(e)}
        REPORT_PATH.write_text(json.dumps(error, indent=2))
        print(json.dumps(error, indent=2))
        raise SystemExit(1)
