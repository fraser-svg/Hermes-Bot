#!/usr/bin/env python3
"""Slot-fill ULTIMATE_TEMPLATE.html deterministically from a candidate record.

Fills every data and derived slot directly from the prospect JSON. Every slot
that requires human-written copy (hero_subhead, service titles/descriptions,
FAQ answers, review attribution names) is replaced with a visible sentinel
and an HTML comment instruction marker. A Claude Code session (the
`template-site-builder` skill) then reads the intermediate file and replaces
each sentinel with voice-matched copy following COPY.md formulas.

Usage:
    # Fill one prospect, write to output/_filled/<slug>.html
    python3 fill_template.py <slug>

    # Fill every qualified prospect
    python3 fill_template.py --all-qualified

    # Dry-run: print filled HTML to stdout (no file written)
    python3 fill_template.py <slug> --dry-run

Reads:
    templates/ULTIMATE_TEMPLATE.html
    _workspace/nowebsite/candidates.json
    _workspace/nowebsite/{slug}_qualified.json (optional — used for persona fallback)
    .claude/skills/template-site-builder/references/vertical-defaults.json

Writes:
    output/_filled/<slug>.html
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Reuse accent + hero photo logic from core/generate.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import hero_images  # type: ignore  # noqa: E402
from core.generate import auto_select_accent  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "ULTIMATE_TEMPLATE.html"
WORKSPACE = BASE_DIR / "_workspace" / "nowebsite"
FILLED_DIR = BASE_DIR / "output" / "_filled"
DEFAULTS_PATH = (
    BASE_DIR
    / ".claude"
    / "skills"
    / "template-site-builder"
    / "references"
    / "vertical-defaults.json"
)

GENERIC_DEFAULT = {
    "credential_human": "Fully insured",
    "credential_marker": "Fully insured",
    "credential_subtext": "Insured trader",
    "response_window": "Same week",
    "service_radius_hint": "{city} and surrounding areas",
    "persona": "cold",
}

logger = logging.getLogger("fill_template")

COPY_SLOTS: tuple[str, ...] = (
    "hero_subhead",
    "service_1_title",
    "service_1_description",
    "service_2_title",
    "service_2_description",
    "service_3_title",
    "service_3_description",
    "service_4_title",
    "service_4_description",
    "service_5_title",
    "service_5_description",
    "service_6_title",
    "service_6_description",
    "faq_1_answer",
    "faq_2_answer",
    "faq_3_answer",
    "faq_4_answer",
    "faq_5_answer",
    "review_1_name",
    "review_2_name",
    "review_3_name",
)


@dataclass(frozen=True)
class VerticalDefaults:
    credential_human: str
    credential_marker: str
    credential_subtext: str
    response_window: str
    service_radius_hint: str
    persona: str


@dataclass
class FillContext:
    """All computed values needed to render ULTIMATE_TEMPLATE.html."""

    slug: str
    candidate: dict[str, Any]
    defaults: VerticalDefaults
    accent: str
    hero_image_url: str
    service_radius: str
    review_quotes: list[str] = field(default_factory=list)


def load_defaults(category: str) -> VerticalDefaults:
    try:
        raw = json.loads(DEFAULTS_PATH.read_text())
    except FileNotFoundError:
        raw = {}
    entry = raw.get(category.lower()) or GENERIC_DEFAULT
    return VerticalDefaults(
        credential_human=entry.get("credential_human", GENERIC_DEFAULT["credential_human"]),
        credential_marker=entry.get("credential_marker", GENERIC_DEFAULT["credential_marker"]),
        credential_subtext=entry.get("credential_subtext", GENERIC_DEFAULT["credential_subtext"]),
        response_window=entry.get("response_window", GENERIC_DEFAULT["response_window"]),
        service_radius_hint=entry.get("service_radius_hint", GENERIC_DEFAULT["service_radius_hint"]),
        persona=entry.get("persona", GENERIC_DEFAULT["persona"]),
    )


def phone_tel(phone: str) -> str:
    """Best-effort E.164 for UK phones."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return ""
    if phone.lstrip().startswith("+"):
        return f"+{digits}"
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    if digits.startswith("0"):
        return f"+44{digits[1:]}"
    return f"+{digits}"


def category_article(category: str) -> str:
    c = (category or "").strip().lower()
    if not c:
        return "a"
    return "an" if c[0] in "aeiou" else "a"


def truncate_review(text: str, max_words: int = 30) -> str:
    """Truncate a review to ≤max_words, ending on a sentence boundary where possible.

    COPY.md §5 forbids paraphrasing — only truncation is allowed. We prefer
    cutting at a `.` / `!` / `?` boundary; fall back to word-count truncation
    and drop the trailing fragment.
    """
    text = (text or "").strip().replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    # Prefer sentence boundary inside truncated window.
    last_stop = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if last_stop >= 40:  # only use a boundary if we keep enough content
        return truncated[: last_stop + 1]
    # Otherwise trim trailing punctuation and add ellipsis marker.
    return truncated.rstrip(",;:- ") + "…"


def service_radius(city: str, hint_template: str) -> str:
    return hint_template.format(city=city or "your area")


def service_icon_digit(index: int) -> str:
    """Service cards use plain digits 1–6; the template's CSS themes them."""
    return str(index + 1)


def hero_image_for(category: str) -> str:
    photos = hero_images.resolve(category or "")
    return photos.hero


def sentinel(slot: str, instruction: str) -> str:
    """Build a visible sentinel + HTML comment for a copy slot.

    Sentinel format (intentionally ugly so a missing replacement is obvious):
        <!-- COPY_TODO:<slot>|<instruction> -->[[WRITE_<slot>]]
    """
    return f"<!-- COPY_TODO:{slot}|{instruction} -->[[WRITE_{slot}]]"


def build_copy_instructions(ctx: FillContext) -> dict[str, str]:
    """Return {slot: single-line instruction} for every COPY_SLOT."""
    cat = ctx.candidate.get("business_category", "service").lower()
    city = ctx.candidate.get("city", "")
    persona = ctx.defaults.persona
    credential_marker = ctx.defaults.credential_marker

    out: dict[str, str] = {}
    out["hero_subhead"] = (
        f"COPY.md §3 subhead ≤25 words, persona={persona}, one of patterns "
        f"S-A/S-B/S-C/S-D. Must include credential ({credential_marker}) "
        f"AND rating/review count. City={city}."
    )
    services = ctx.candidate.get("services_offered") or []
    for i in range(6):
        svc = services[i] if i < len(services) else f"{cat} services"
        out[f"service_{i+1}_title"] = (
            f"COPY.md §6 service title ≤4 words, sentence case, source='{svc}'."
        )
        out[f"service_{i+1}_description"] = (
            f"COPY.md §6 description ≤15 words, formula "
            f"'outcome_verb deliverable. specific_qualifier_or_proof.' "
            f"source='{svc}'. No banned vocab."
        )
    out["faq_1_answer"] = (
        f"COPY.md §7 Q1 (cost range, ≤40 words): give a real {cat} price band, "
        f"what's included, what isn't. No ranges under £40."
    )
    out["faq_2_answer"] = (
        f"COPY.md §7 Q2 (insured/accredited, ≤25 words): "
        f"'Yes. {credential_marker}. Certificate available on request.'"
    )
    out["faq_3_answer"] = (
        f"COPY.md §7 Q3 (how quickly, ≤30 words): geographic radius "
        f"({ctx.service_radius}) + response time ({ctx.defaults.response_window}) "
        f"+ booking channel (phone)."
    )
    out["faq_4_answer"] = (
        f"COPY.md §7 Q4 (fixed vs estimate, ≤25 words): state one pricing model, "
        f"explain when a visit is needed. Never both."
    )
    out["faq_5_answer"] = (
        f"COPY.md §7 Q5 (after-job guarantee, ≤40 words): workmanship guarantee "
        f"period + what it covers + how to claim. Name the period."
    )
    for i, name_slot in enumerate(("review_1_name", "review_2_name", "review_3_name")):
        out[name_slot] = (
            f"COPY.md §5 attribution: first name only + city/neighborhood. "
            f"Source review text: '{ctx.review_quotes[i] if i < len(ctx.review_quotes) else ''}'"
        )
    return out


def compute_fill_values(ctx: FillContext) -> dict[str, str]:
    c = ctx.candidate
    cat = c.get("business_category", "service").lower()
    phone = c.get("phone_number", "") or ""
    reviews = c.get("google_reviews") or []

    # Build review quotes (truncated)
    quotes: list[str] = []
    for r in reviews[:3]:
        text = r.get("text", "") if isinstance(r, dict) else ""
        if text:
            quotes.append(truncate_review(text))
    while len(quotes) < 3:
        quotes.append("")
    ctx.review_quotes = quotes

    values: dict[str, str] = {
        # business.*
        "business.name": c.get("business_name", ""),
        "business.category": cat,
        "business.city": c.get("city", ""),
        "business.address": c.get("address", ""),
        "business.phone": phone,
        "business.phone_tel": phone_tel(phone),
        "business.rating": f"{c.get('rating', 0):.1f}".rstrip("0").rstrip("."),
        "business.review_count": str(c.get("review_count", 0)),
        # derived
        "category_article": category_article(cat),
        "year": str(datetime.now().year),
        "years_short": "Local",  # absent from prospect data; placeholder label
        "response_window": ctx.defaults.response_window,
        "service_radius": ctx.service_radius,
        "credential_human": ctx.defaults.credential_human,
        "credential_marker": ctx.defaults.credential_marker,
        "credential_subtext": ctx.defaults.credential_subtext,
        "hero_image_url": ctx.hero_image_url,
        "logo_html": c.get("business_name", ""),
        # reviews
        "review_1_quote": quotes[0],
        "review_2_quote": quotes[1],
        "review_3_quote": quotes[2],
    }
    # Service icons are integers 1–6 rendered by template CSS.
    for i in range(6):
        values[f"service_{i+1}_icon"] = service_icon_digit(i)
    return values


def inject_head_meta(html: str, ctx: FillContext) -> str:
    """Add <meta name='description'> + LocalBusiness JSON-LD before </head>."""
    c = ctx.candidate
    desc = (
        f"{c.get('business_category', 'service').title()} in {c.get('city', '')}. "
        f"{c.get('rating', '')}★ from {c.get('review_count', 0)} reviews. "
        f"{ctx.defaults.credential_marker}. "
        f"Call {c.get('phone_number', '')}."
    )
    meta_tag = f'<meta name="description" content="{_attr_escape(desc)}">'

    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": c.get("business_name", ""),
        "image": ctx.hero_image_url,
        "telephone": c.get("phone_number", ""),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": c.get("address", ""),
            "addressLocality": c.get("city", ""),
            "addressCountry": "GB",
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": c.get("rating", 0),
            "reviewCount": c.get("review_count", 0),
        },
    }
    schema_tag = (
        '<script type="application/ld+json">'
        + json.dumps(schema, ensure_ascii=False)
        + "</script>"
    )
    inject = f"  {meta_tag}\n  {schema_tag}\n"
    return html.replace("</head>", inject + "</head>", 1)


def set_persona(html: str, persona: str) -> str:
    return re.sub(
        r'<html([^>]*?)data-persona="[^"]*"', rf'<html\1data-persona="{persona}"', html
    )


def _attr_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def replace_data_slots(html: str, values: dict[str, str]) -> str:
    for slot, value in values.items():
        html = html.replace("{{" + slot + "}}", value)
    return html


def replace_copy_slots_with_sentinels(html: str, instructions: dict[str, str]) -> str:
    for slot, instr in instructions.items():
        html = html.replace("{{" + slot + "}}", sentinel(slot, instr))
    return html


def fill(slug: str) -> str:
    """Produce intermediate filled HTML for `slug`. Returns the HTML string."""
    candidates = json.loads((WORKSPACE / "candidates.json").read_text())
    candidate = next((c for c in candidates if c.get("slug") == slug), None)
    if candidate is None:
        raise KeyError(f"slug {slug!r} not in _workspace/nowebsite/candidates.json")

    cat = candidate.get("business_category", "service")
    defaults = load_defaults(cat)
    ctx = FillContext(
        slug=slug,
        candidate=candidate,
        defaults=defaults,
        accent=auto_select_accent(candidate),
        hero_image_url=hero_image_for(cat),
        service_radius=service_radius(candidate.get("city", ""), defaults.service_radius_hint),
    )

    values = compute_fill_values(ctx)
    instructions = build_copy_instructions(ctx)

    html = TEMPLATE_PATH.read_text()
    html = replace_data_slots(html, values)
    html = replace_copy_slots_with_sentinels(html, instructions)
    html = set_persona(html, ctx.defaults.persona)
    html = inject_head_meta(html, ctx)

    # Sanity check: no orphan {{...}} slots remain.
    orphans = re.findall(r"\{\{[a-zA-Z0-9_.]+\}\}", html)
    if orphans:
        raise RuntimeError(f"unfilled slots: {sorted(set(orphans))}")

    return html


def list_qualified(cohort_filter: set[str] | None = None) -> list[str]:
    qualified: list[tuple[float, str]] = []
    for qpath in WORKSPACE.glob("*_qualified.json"):
        q = json.loads(qpath.read_text())
        if q.get("verdict") != "qualified":
            continue
        if cohort_filter and q.get("cohort") not in cohort_filter:
            continue
        ev = q.get("evidence", {})
        score = float(ev.get("rating") or 0) * float(ev.get("review_count") or 0)
        qualified.append((score, q["slug"]))
    qualified.sort(reverse=True)
    return [s for _, s in qualified]


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("slug", nargs="?", help="Prospect slug to fill")
    p.add_argument("--all-qualified", action="store_true", help="Fill every qualified prospect")
    p.add_argument(
        "--cohort",
        default="",
        help="Comma-separated cohort filter (e.g., 'A_greenfield,B_broken')",
    )
    p.add_argument("--dry-run", action="store_true", help="Print HTML to stdout instead of writing file")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.all_qualified:
        cohort_filter = {c.strip() for c in args.cohort.split(",") if c.strip()} or None
        slugs = list_qualified(cohort_filter)
        if not slugs:
            logger.error("no qualified prospects found")
            return 2
    elif args.slug:
        slugs = [args.slug]
    else:
        logger.error("provide a slug or --all-qualified")
        return 2

    FILLED_DIR.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        try:
            html = fill(slug)
        except (KeyError, RuntimeError) as e:
            logger.error("%s: %s", slug, e)
            continue
        if args.dry_run:
            sys.stdout.write(html)
            continue
        out_path = FILLED_DIR / f"{slug}.html"
        out_path.write_text(html)
        logger.info("wrote %s (%d bytes)", out_path, len(html))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
