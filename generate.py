"""Hermes Website Generator — Gemini 3.1 Pro via OpenRouter.

Reads business_details.json, sends to Gemini with the website builder prompt,
outputs a production-ready single-file HTML website.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
PROMPT_PATH = BASE_DIR / "prompts" / "website_builder.md"
OUTPUT_PATH = BASE_DIR / "output"
REPORT_PATH = BASE_DIR / "build_report.json"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_PRODUCTION = "google/gemini-3.1-pro-preview"
MODEL_DRAFT = "google/gemini-2.5-flash"
MAX_TOKENS_PRO = 32000
MAX_TOKENS_DRAFT = 16000

# Mode selection: --pro forces Pro, --draft forces Flash, default is smart (Flash-first)
if "--pro" in sys.argv:
    MODE = "production"
elif "--draft" in sys.argv:
    MODE = "draft"
else:
    MODE = "smart"

SMART_THRESHOLD = 8.0  # Minimum score to accept Flash output (out of 10)
SMART_REQUIRE_READABILITY = True  # Flash must also pass readability


def load_env() -> dict[str, str]:
    """Load .env file into dict. No dependency needed."""
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


def get_api_key() -> str:
    """Get OpenRouter API key from env."""
    key = os.environ.get("OPENROUTER_API_KEY") or load_env().get("openrouter")
    if not key:
        raise RuntimeError("No OpenRouter API key found. Set OPENROUTER_API_KEY or add 'openrouter' to .env")
    return key


def load_business_details() -> dict:
    """Load and validate business details JSON."""
    if not DETAILS_PATH.exists():
        raise FileNotFoundError(f"Business details not found at {DETAILS_PATH}")
    data = json.loads(DETAILS_PATH.read_text())
    required = ["business_name", "phone_number", "city"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return data


def load_system_prompt() -> str:
    """Load the website builder system prompt."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text()


def auto_select_accent(details: dict) -> str:
    """Auto-select accent color based on business category (YC startup palette)."""
    category = details.get("business_category", "").lower()

    accent_map = {
        # Trades
        "electrician": "#2563EB",
        "plumber": "#2563EB",
        "roofer": "#111827",
        "hvac": "#0891B2",
        "builder": "#111827",
        "carpenter": "#111827",
        "painter": "#111827",
        "tiler": "#111827",
        "plasterer": "#111827",
        "glazier": "#0891B2",
        "locksmith": "#111827",
        "cleaner": "#4F46E5",
        "landscaper": "#059669",
        "pest control": "#059669",
        "mover": "#2563EB",
        # Professional
        "lawyer": "#4F46E5",
        "solicitor": "#4F46E5",
        "accountant": "#4F46E5",
        "financial advisor": "#4F46E5",
        "architect": "#111827",
        "surveyor": "#111827",
        "estate agent": "#4F46E5",
        "insurance broker": "#111827",
        # Health
        "dentist": "#0891B2",
        "physiotherapist": "#0891B2",
        "chiropractor": "#0891B2",
        "optician": "#0891B2",
        "vet": "#059669",
        "veterinarian": "#059669",
        # Personal / Creative
        "photographer": "#111827",
        "personal trainer": "#EA580C",
        "beauty salon": "#111827",
        "hairdresser": "#111827",
        "barber": "#111827",
        "dog groomer": "#059669",
        # Food / Events
        "caterer": "#111827",
        "florist": "#111827",
        "restaurant": "#111827",
        # Auto
        "mechanic": "#DC2626",
        "car wash": "#2563EB",
        # Tech
        "it support": "#2563EB",
        "web designer": "#4F46E5",
        "marketing agency": "#4F46E5",
    }
    return accent_map.get(category, "#2563EB")


def build_user_message(details: dict, fix_hints: list[str] | None = None) -> str:
    """Format business details into the user message for Gemini."""
    # Auto-select accent color if not specified
    if "accent_color" not in details:
        details = {**details, "accent_color": auto_select_accent(details)}

    msg = (
        "Build a complete website for this business. "
        "Use the YC startup aesthetic. Follow ALL 7 design rules and the anti-slop checklist. "
        "Return ONLY the HTML document, no explanations.\n\n"
        f"```json\n{json.dumps(details, indent=2)}\n```"
    )

    if fix_hints:
        msg += "\n\nCRITICAL: A previous attempt failed these checks. You MUST fix them:\n"
        for hint in fix_hints:
            msg += f"- {hint}\n"

    return msg


def call_gemini(system_prompt: str, user_message: str, api_key: str, model: str | None = None, max_tokens: int | None = None) -> str:
    """Call Gemini via OpenRouter and return the HTML response."""
    use_model = model or MODEL
    use_max_tokens = max_tokens or (MAX_TOKENS_PRO if use_model == MODEL_PRODUCTION else MAX_TOKENS_DRAFT)
    payload = json.dumps({
        "model": use_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": use_max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://hermes-bot.local",
            "X-Title": "Hermes Website Builder",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No response body"
        raise RuntimeError(f"OpenRouter API error {e.code}: {error_body}") from e

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"No response from model. Full response: {json.dumps(body)}")

    return choices[0]["message"]["content"]


def extract_html(response: str) -> str:
    """Extract HTML from response, stripping any markdown fences."""
    # If response is wrapped in code fences, extract inner content
    fence_match = re.search(r"```(?:html)?\s*\n(.*?)```", response, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # If it starts with <!DOCTYPE or <html, use as-is
    stripped = response.strip()
    if stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
        return stripped

    # Last resort: return everything
    return stripped


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    def channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    l1 = relative_luminance(*hex_to_rgb(hex1))
    l2 = relative_luminance(*hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def audit_readability(html: str) -> list[str]:
    """Audit HTML for common readability/contrast issues. Returns list of warnings."""
    warnings: list[str] = []
    html_lower = html.lower()

    # Check 1: Hero text-shadow for readability on photo backgrounds
    has_hero_bg_image = "background-image" in html_lower and "unsplash" in html_lower
    has_text_shadow_hero = "text-shadow" in html_lower
    if has_hero_bg_image and not has_text_shadow_hero:
        warnings.append(
            "HERO: No text-shadow found. White text on photo backgrounds needs "
            "text-shadow for readability (e.g. text-shadow: 0 2px 8px rgba(0,0,0,0.5))"
        )

    # Check 2: Hero overlay darkness
    if has_hero_bg_image:
        # Look for rgba overlay with sufficient darkness
        overlay_match = re.findall(r"rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*([\d.]+)\s*\)", html)
        overlay_opacities = [float(m) for m in overlay_match]
        max_opacity = max(overlay_opacities) if overlay_opacities else 0
        if max_opacity < 0.5:
            warnings.append(
                f"HERO: Darkest overlay opacity is {max_opacity}. Needs at least 0.5 "
                "for white text readability on photos. Recommend 0.6-0.75."
            )

    # Check 3: White text on gold/yellow (the #1 contrast fail)
    gold_patterns = re.findall(
        r"(background[^;]*#FF[DdEe]\w{3}[^;]*;[^}]*color\s*:\s*(?:#[Ff]{3,6}|white|rgba\(255))",
        html, re.DOTALL
    )
    if gold_patterns:
        warnings.append(
            "CONTRAST FAIL: White/light text found on gold/yellow background. "
            "Gold backgrounds need dark text (#1A202C or similar)."
        )

    # Check 4: Low-opacity white TEXT (not backgrounds)
    # Match "color:" specifically (not background-color) followed by rgba white
    low_opacity_text = re.findall(
        r"(?<!background-)color\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*([\d.]+)\s*\)",
        html
    )
    for opacity_str in low_opacity_text:
        opacity = float(opacity_str)
        if opacity < 0.65:
            warnings.append(
                f"LOW CONTRAST: White text color at opacity {opacity}. "
                "Minimum readable opacity for white text is 0.7. "
                "Body text should be 0.85+."
            )
            break

    # Check 5: Detect actual white-text-on-gold-background patterns in CSS rules
    # Look for gold/yellow background with white/light color in same rule block
    white_on_gold = re.findall(
        r"background(?:-color)?\s*:\s*[^;]*#FF[Dd][0-9A-Fa-f]{3}[^}]*?"
        r"(?:^|\s)color\s*:\s*(?:#[Ff]{3,6}|white|#[Ff][Ff][Ff])",
        html, re.DOTALL | re.MULTILINE
    )
    if white_on_gold:
        warnings.append(
            "CONTRAST FAIL: White text on gold/yellow background detected. "
            "Gold backgrounds need dark text (#1A202C or similar)."
        )

    # Check 6: Form placeholder contrast
    if "<input" in html_lower or "<textarea" in html_lower:
        if "placeholder" in html_lower and "::placeholder" not in html_lower:
            warnings.append(
                "FORMS: No ::placeholder CSS rule found. Browser default placeholder "
                "color may be too light. Add ::placeholder { color: #9CA3AF; } minimum."
            )

    return warnings


def estimate_cost(model: str, input_chars: int, output_chars: int) -> float:
    """Rough cost estimate from character counts (~4 chars per token)."""
    input_tokens = input_chars // 4
    output_tokens = output_chars // 4
    rates: dict[str, tuple[float, float]] = {
        MODEL_PRODUCTION: (2.00, 10.00),
        MODEL_DRAFT: (0.075, 0.30),
    }
    inp_rate, out_rate = rates.get(model, (2.00, 10.00))
    return (input_tokens * inp_rate + output_tokens * out_rate) / 1_000_000


def validate_html(html: str, details: dict) -> tuple[float, dict, list[str]]:
    """Validate HTML and return (score, checks, readability_warnings)."""
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
    return score, checks, readability_warnings


def build_report(
    details: dict, html: str, model: str, html_file: Path,
    score: float, checks: dict, readability_warnings: list[str],
    cost_usd: float, mode_label: str, escalated: bool = False,
    draft_cost: float = 0.0,
) -> dict:
    """Build the report dict."""
    accent = details.get("accent_color") or auto_select_accent(details)
    total_cost = cost_usd + draft_cost
    report = {
        "success": True,
        "business": details["business_name"],
        "category": details.get("business_category", "general"),
        "accent": accent,
        "city": details["city"],
        "model": model,
        "output_file": str(html_file),
        "index_file": str(BASE_DIR / "index.html"),
        "validation": {
            "score": f"{score}/10",
            "passed": sum(checks.values()),
            "total": len(checks),
            "checks": checks,
        },
        "readability": {
            "pass": len(readability_warnings) == 0,
            "warnings": readability_warnings,
        },
        "html_size_kb": round(len(html.encode("utf-8")) / 1024, 1),
        "cost": {
            "mode": mode_label,
            "estimated_usd": round(total_cost, 4),
            "escalated": escalated,
        },
    }
    if escalated:
        report["cost"]["draft_cost_usd"] = round(draft_cost, 4)
        report["cost"]["pro_cost_usd"] = round(cost_usd, 4)
    return report


def call_and_validate(
    system_prompt: str, user_message: str, api_key: str, model: str,
    details: dict, label: str,
) -> tuple[str, float, float, dict, list[str]]:
    """Call model, extract HTML, validate. Returns (html, score, cost, checks, warnings)."""
    input_chars = len(system_prompt) + len(user_message)
    print(f"  Calling {model}...")
    raw_response = call_gemini(system_prompt, user_message, api_key, model=model)
    html = extract_html(raw_response)
    cost_usd = estimate_cost(model, input_chars, len(raw_response))
    score, checks, warnings = validate_html(html, details)
    print(f"  {label}: {score}/10 | ${cost_usd:.4f} | readability={'PASS' if not warnings else f'{len(warnings)} warnings'}")
    return html, score, cost_usd, checks, warnings


def generate_website() -> dict:
    """Main generation pipeline. Returns build report."""
    details = load_business_details()
    system_prompt = load_system_prompt()
    api_key = get_api_key()
    user_message = build_user_message(details)
    accent = details.get("accent_color") or auto_select_accent(details)

    print(f"Generating website for: {details['business_name']}")
    print(f"Category: {details.get('business_category', 'general')} | Accent: {accent} | City: {details['city']}")

    OUTPUT_PATH.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", details["business_name"].lower()).strip("-")
    html_file = OUTPUT_PATH / f"{slug}.html"

    escalated = False
    draft_cost = 0.0

    if MODE == "smart":
        # Smart mode: try Flash first, escalate to Pro only if quality insufficient
        pro_cost_est = estimate_cost(MODEL_PRODUCTION, len(system_prompt) + len(user_message), 20000 * 4)
        print(f"Mode: SMART (Flash first, Pro fallback) | Pro would cost ~${pro_cost_est:.4f}")

        html, score, cost_usd, checks, warnings = call_and_validate(
            system_prompt, user_message, api_key, MODEL_DRAFT, details, "Flash",
        )

        needs_escalation = score < SMART_THRESHOLD or (SMART_REQUIRE_READABILITY and warnings)

        if needs_escalation:
            failed = [k for k, v in checks.items() if not v]
            reason = f"score {score}/10" if score < SMART_THRESHOLD else f"{len(warnings)} readability warnings"
            print(f"  Flash insufficient ({reason}). Failed: {', '.join(failed)}")
            print(f"  Escalating to Pro with fix hints...")

            draft_cost = cost_usd
            escalated = True

            # Build fix hints from failures so Pro knows what to fix
            fix_hints = [k.replace("_", " ") for k, v in checks.items() if not v]
            fix_hints.extend(warnings)
            escalation_message = build_user_message(details, fix_hints=fix_hints)

            html, score, cost_usd, checks, warnings = call_and_validate(
                system_prompt, escalation_message, api_key, MODEL_PRODUCTION, details, "Pro",
            )
            model_used = MODEL_PRODUCTION
            total = cost_usd + draft_cost
            print(f"  Escalated. Total cost: ${total:.4f} (Flash ${draft_cost:.4f} + Pro ${cost_usd:.4f})")
        else:
            model_used = MODEL_DRAFT
            saved = pro_cost_est - cost_usd
            print(f"  Flash passed! Saved ${saved:.4f} vs Pro")

        mode_label = "smart"
    else:
        model_used = MODEL_PRODUCTION if MODE == "production" else MODEL_DRAFT
        mode_label = MODE
        est = "~$0.02" if MODE == "draft" else "~$0.60"
        print(f"Mode: {mode_label.upper()} | Est cost: {est} | Model: {model_used}")

        html, score, cost_usd, checks, warnings = call_and_validate(
            system_prompt, user_message, api_key, model_used, details, mode_label.title(),
        )

    # Write output
    html_file.write_text(html)
    (BASE_DIR / "index.html").write_text(html)

    report = build_report(
        details, html, model_used, html_file,
        score, checks, warnings, cost_usd, mode_label,
        escalated=escalated, draft_cost=draft_cost,
    )

    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nBuild complete: {score}/10 validation score")
    print(f"Output: {html_file}")

    if warnings:
        print(f"\n⚠ READABILITY WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("Readability audit: PASS")
    print(f"Size: {report['html_size_kb']}KB")

    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"Missing: {', '.join(failed)}")

    return report


if __name__ == "__main__":
    try:
        result = generate_website()
        print(json.dumps(result, indent=2))
    except Exception as e:
        error = {"success": False, "error": str(e)}
        REPORT_PATH.write_text(json.dumps(error, indent=2))
        print(json.dumps(error, indent=2))
        raise SystemExit(1)
