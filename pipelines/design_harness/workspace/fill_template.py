"""Fill ULTIMATE_TEMPLATE.html placeholders from business_details.json."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "ULTIMATE_TEMPLATE.html"
DATA = ROOT / "references" / "business_details.json"
OUT = ROOT / "output" / "fife-current-electrical-filled.html"

# Import shared industry-photo resolver from project root.
sys.path.insert(0, str(ROOT))
import hero_images  # noqa: E402

CATEGORY_CREDENTIAL = {
    "electrician": ("Fully certified", "NICEIC-registered · £5M public liability"),
    "plumber": ("Gas-safe registered", "Fully insured · £5M public liability"),
    "roofer": ("Vetted & approved", "£10M insurance · 10-year workmanship guarantee"),
    "hvac": ("F-gas certified", "Gas-safe & F-gas registered · fully insured"),
    "accountant": ("ICAS chartered", "Chartered accountants · ICAEW/ICAS regulated"),
    "lawyer": ("SRA regulated", "Solicitors Regulation Authority · £3M PI cover"),
    "dentist": ("GDC registered", "General Dental Council · full indemnity cover"),
}

SERVICE_ICONS = ["→", "✓", "⚡", "◆", "●", "★", "◎", "◇"]


def phone_tel(phone: str) -> str:
    digits = phone.replace(" ", "").replace("-", "")
    return "+44" + digits[1:] if digits.startswith("0") else digits


def build_slots(d: dict) -> dict[str, str]:
    reviews = d.get("google_reviews", [])
    services = d.get("services_offered", [])
    category = d.get("business_category", "").lower()

    credential_human, credential_subtext = CATEGORY_CREDENTIAL.get(
        category, ("Fully insured", "£5M public liability · workmanship guaranteed"),
    )
    credential_marker = d.get("license_number", "Fully insured")

    years = d.get("years_experience")
    years_short = f"{years}+" if isinstance(years, int) and years >= 3 else "Local"

    photos = hero_images.resolve(category)
    hero_image = photos.hero
    about_image = photos.about

    logo_url = (d.get("logo_url") or "").strip()
    business_name_escaped = d["business_name"].replace('"', "&quot;")
    if logo_url:
        logo_html = (
            f'<img src="{logo_url}" alt="{business_name_escaped} logo" '
            'loading="eager" decoding="async">'
        )
    else:
        logo_html = d["business_name"]

    article = "an" if category and category[0].lower() in "aeiou" else "a"

    slots: dict[str, str] = {
        "business.name": d["business_name"],
        "business.category": category,
        "category_article": article,
        "business.city": d["city"],
        "business.address": d.get("address", ""),
        "business.phone": d["phone_number"],
        "business.phone_tel": phone_tel(d["phone_number"]),
        "business.rating": str(d.get("rating", "")),
        "business.review_count": str(d.get("review_count", "")),
        "credential_marker": credential_marker,
        "credential_human": credential_human,
        "credential_subtext": credential_subtext,
        "years_short": years_short,
        "response_window": "60 min",
        "service_radius": "KY + FK postcodes",
        "hero_subhead": (
            f"Same-day callouts across {d['city']}. Fixed-price quotes, "
            f"work certificated on completion, and {d.get('rating','')}★ from "
            f"{d.get('review_count','')} local reviews."
        ),
        "hero_image_url": hero_image,
        "about_image_url": about_image,
        "logo_html": logo_html,
        "logo_url": logo_url,
        "year": str(datetime.now().year),
    }

    service_blurbs = [
        "Fixed-price quote before we start. Certificated on completion.",
        "Same-day diagnosis where possible. No hourly surprises.",
        "Tidy work, clear invoice, full warranty.",
        "Detailed report within 24 hours of the inspection.",
        "Approved products only. Workmanship guaranteed.",
        "Callouts answered within 60 minutes during working hours.",
    ]
    for i, svc in enumerate(services[:6], 1):
        slots[f"service_{i}_title"] = svc
        slots[f"service_{i}_description"] = service_blurbs[(i - 1) % len(service_blurbs)]
        slots[f"service_{i}_icon"] = SERVICE_ICONS[(i - 1) % len(SERVICE_ICONS)]
    for i in range(len(services) + 1, 7):
        slots[f"service_{i}_title"] = ""
        slots[f"service_{i}_description"] = ""
        slots[f"service_{i}_icon"] = ""

    for i, r in enumerate(reviews[:3], 1):
        slots[f"review_{i}_name"] = "Verified Google review"
        slots[f"review_{i}_quote"] = r["text"]

    slots["faq_1_answer"] = (
        f"Yes. We cover {d['city']} and all surrounding KY and FK postcodes. "
        "Emergency callouts typically within 60 minutes during working hours."
    )
    slots["faq_2_answer"] = (
        "Every job is quoted before we start. No hourly surprises. "
        "Emergency callouts have a fixed callout fee plus parts at cost — you approve before work begins."
    )
    slots["faq_3_answer"] = (
        f"All installations and remedial work are certificated. We are {credential_human.lower()}, "
        f"fully insured (£5M public liability), and every domestic job ships with an "
        "Electrical Installation Certificate or Minor Works Certificate."
    )
    slots["faq_4_answer"] = (
        "Most faults are diagnosed and fixed in a single visit. Rewires typically take 3–5 days "
        "depending on property size. EICR reports are emailed within 24 hours of the inspection."
    )
    slots["faq_5_answer"] = (
        "Call or fill in the form below. We respond to every enquiry within 60 minutes, "
        "book a time that suits you, and confirm the price before any tools come out of the van."
    )
    return slots


def fill(template: str, slots: dict[str, str]) -> str:
    for k, v in slots.items():
        template = template.replace("{{" + k + "}}", v)
    return template


def main() -> None:
    data = json.loads(DATA.read_text())
    slots = build_slots(data)
    template = TEMPLATE.read_text()
    filled = fill(template, slots)
    OUT.write_text(filled)
    remaining = [s for s in filled.split("{{")[1:] if "}}" in s]
    print(f"Wrote {OUT.relative_to(ROOT)}")
    if remaining:
        print(f"Warning: {len(remaining)} unfilled placeholders remain")
        for r in remaining[:5]:
            print(f"  {{{{ {r.split('}}')[0]} }}}}")
    else:
        print("All placeholders filled.")


if __name__ == "__main__":
    main()
