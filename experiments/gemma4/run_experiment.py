"""Gemma 4 LOCAL experiment via Ollama.

Builds 3 websites with Gemma 4 running locally (free, no API cost).
Uses the same design system prompt as generate.py.
"""

import json
import sys
import time
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from generate import load_system_prompt, extract_html, audit_readability, auto_select_accent

EXPERIMENT_DIR = Path(__file__).resolve().parent
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma4"

TEST_BUSINESSES = [
    {
        "business_name": "Spark Brothers Electrical",
        "business_category": "electrician",
        "city": "Edinburgh",
        "phone_number": "0131 444 5566",
        "address": "22 Leith Walk, Edinburgh EH6 5AA",
        "services_offered": ["Rewiring", "Fuse board upgrades", "EV charger installation",
                             "Emergency callouts", "Lighting design", "PAT testing"],
        "google_reviews": [
            {"rating": 5, "text": "Rewired our entire flat in Stockbridge. Clean work, on time, fair price."},
            {"rating": 5, "text": "Installed an EV charger on our driveway. Done in half a day."},
            {"rating": 4, "text": "Fixed a tricky fault in our fuse board. Honest about what needed replacing."}
        ],
        "rating": 4.9, "review_count": 41
    },
    {
        "business_name": "Caledonia Family Dental",
        "business_category": "dentist",
        "city": "Glasgow",
        "phone_number": "0141 332 8899",
        "address": "45 Sauchiehall Street, Glasgow G2 3AT",
        "services_offered": ["Check-ups & cleaning", "Fillings & crowns", "Teeth whitening",
                             "Invisalign", "Emergency dental care", "Children's dentistry"],
        "google_reviews": [
            {"rating": 5, "text": "Dr. Murray is brilliant with nervous patients. First dentist my daughter hasn't cried at."},
            {"rating": 5, "text": "Had an emergency appointment within 2 hours of calling. Abscess sorted, pain gone."},
            {"rating": 4, "text": "Whitening results were excellent. Reception staff are always friendly."}
        ],
        "rating": 4.8, "review_count": 127
    },
    {
        "business_name": "Morrison & Co Solicitors",
        "business_category": "lawyer",
        "city": "Aberdeen",
        "phone_number": "01224 600 700",
        "address": "8 Union Street, Aberdeen AB10 1BD",
        "services_offered": ["Conveyancing", "Family law", "Wills & probate",
                             "Employment law", "Personal injury", "Commercial property"],
        "google_reviews": [
            {"rating": 5, "text": "Handled our house purchase in 4 weeks flat. Other solicitors quoted 8-12 weeks."},
            {"rating": 5, "text": "Claire Morrison handled my divorce with real compassion. Made a horrible process bearable."},
            {"rating": 5, "text": "Drew up our wills and power of attorney. Explained everything in plain English."}
        ],
        "rating": 4.9, "review_count": 63
    }
]


def call_ollama(system_prompt: str, user_message: str) -> tuple[str, float]:
    """Call Gemma 4 via local Ollama. Returns (response, duration_sec)."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 32000,
        }
    }).encode("utf-8")

    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    start = time.time()
    try:
        with urlopen(req, timeout=600) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"Ollama error {e.code}: {error_body}") from e

    duration = time.time() - start
    return body.get("message", {}).get("content", ""), duration


def validate_html(html: str, details: dict) -> dict:
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
    rw = audit_readability(html)
    checks["readability_pass"] = len(rw) == 0
    passed = sum(checks.values())
    return {"score": f"{passed}/{len(checks)}", "passed": passed, "total": len(checks),
            "checks": checks, "readability_warnings": rw}


def check_slop(html: str, city: str) -> dict:
    return {
        "gradient_buttons": bool(re.search(r"gradient.*btn|btn.*gradient", html, re.I)),
        "pill_buttons": bool(re.search(r"border-radius:\s*100px|border-radius:\s*999", html)),
        "wavy_svg": bool(re.search(r"clip-path.*polygon|wave.*svg", html, re.I)),
        "uses_inter": "inter" in html.lower() and "fonts.googleapis" in html.lower(),
        "cold_palette": "#FFFFFF" in html or "#F9FAFB" in html or "#F3F4F6" in html,
        "layered_shadow": "0 1px 3px" in html,
        "city_in_content": city.lower() in html.lower(),
    }


def run():
    system_prompt = load_system_prompt()

    print("=" * 70)
    print("  GEMMA 4 LOCAL EXPERIMENT (Ollama)")
    print(f"  Model: {OLLAMA_MODEL}")
    print("  Building 3 websites, 0 API cost")
    print("=" * 70)

    results = []
    for i, biz in enumerate(TEST_BUSINESSES):
        name = biz["business_name"]
        accent = auto_select_accent(biz)
        biz_msg = {**biz, "accent_color": accent}

        user_message = (
            "Build a complete website for this business. "
            "Use the YC startup aesthetic. Follow ALL 7 design rules and the anti-slop checklist. "
            "Return ONLY the HTML document, no explanations.\n\n"
            f"```json\n{json.dumps(biz_msg, indent=2)}\n```"
        )

        print(f"\n[{i+1}/3] {name} ({biz['business_category']}, {biz['city']})")
        print(f"  Accent: {accent}")
        print(f"  Calling Ollama ({OLLAMA_MODEL})...")

        try:
            raw, duration = call_ollama(system_prompt, user_message)
            html = extract_html(raw)

            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            output_path = EXPERIMENT_DIR / f"{slug}-gemma4-local.html"
            output_path.write_text(html)

            val = validate_html(html, biz)
            slop = check_slop(html, biz["city"])
            size_kb = round(len(html.encode("utf-8")) / 1024, 1)

            result = {
                "business": name, "category": biz["business_category"], "city": biz["city"],
                "model": OLLAMA_MODEL, "local": True, "cost": "$0.00",
                "duration_sec": round(duration, 1), "size_kb": size_kb,
                "validation": val["score"], "passed": val["passed"], "total": val["total"],
                "readability_warnings": val["readability_warnings"],
                "slop_checks": slop, "output_file": str(output_path),
            }

            print(f"  Done in {duration:.1f}s | {size_kb}KB | {val['score']} validation")
            rw_count = len(val["readability_warnings"])
            print(f"  Readability: {'PASS' if rw_count == 0 else f'{rw_count} warnings'}")

            slop_bad = [k for k in ("gradient_buttons", "pill_buttons", "wavy_svg") if slop.get(k)]
            slop_good = [k for k in ("uses_inter", "cold_palette", "layered_shadow", "city_in_content") if slop.get(k)]
            if slop_bad:
                print(f"  SLOP: {', '.join(slop_bad)}")
            print(f"  YC signals: {', '.join(slop_good) or 'none detected'}")

        except Exception as e:
            result = {"business": name, "model": OLLAMA_MODEL, "error": str(e)}
            print(f"  FAILED: {e}")

        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    for r in results:
        if "error" in r:
            print(f"\n  FAIL: {r['business']} - {r['error'][:100]}")
        else:
            print(f"\n  {r['business']} ({r['category']})")
            print(f"    {r['validation']} | {r['size_kb']}KB | {r['duration_sec']}s | {r['cost']}")
            s = r["slop_checks"]
            checks = f"Inter:{'Y' if s['uses_inter'] else 'N'} Cold:{'Y' if s['cold_palette'] else 'N'} Shadow:{'Y' if s['layered_shadow'] else 'N'} City:{'Y' if s['city_in_content'] else 'N'}"
            print(f"    {checks}")
            print(f"    {r['output_file']}")

    # Save
    (EXPERIMENT_DIR / "results.json").write_text(json.dumps(results, indent=2))
    print(f"\n  Results saved: {EXPERIMENT_DIR / 'results.json'}")


if __name__ == "__main__":
    run()
