#!/usr/bin/env python3
"""Validate a filled template HTML file against Hermes quality checks.

Wraps `generate.py`'s validate_html + audit_readability so they can run
against any HTML file — not only the artifact from the Gemini pipeline.

In addition to the inherited checks we:
- Detect unreplaced [[WRITE_*]] sentinels left behind by fill_template.py.
- Allow the near-black template hero overlay (rgba(10,15,26,X)) to satisfy
  the "overlay darkness" readability check, since the stock audit regex
  only recognises pure rgba(0,0,0,X) blacks.
- Scan for COPY.md §9 banned vocabulary.

Exit codes:
    0 — score ≥ 8.0 AND no readability warnings AND no sentinels AND no banned words
    1 — anything else (prints reasons to stderr)

Usage:
    python3 validate_filled_html.py output/<slug>.html
    python3 validate_filled_html.py output/<slug>.html --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))

from core.generate import audit_readability, validate_html  # noqa: E402

BANNED_WORDS: tuple[str, ...] = (
    "revolutionizing",
    "unleash",
    "seamless",
    "robust",
    "cutting-edge",
    "empowering",
    "synergy",
    "best-in-class",
    "world-class",
    "leverage",
    "holistic",
    "premier",
    "next-level",
    "state-of-the-art",
    "game-changing",
    "unparalleled",
    "unmatched",
    "ecosystem",
    "paradigm",
    "reimagine",
    "transforming",
    "disrupt",
)

BANNED_PHRASES: tuple[str, ...] = (
    "welcome to",
    "we pride ourselves",
    "your one-stop shop",
    "look no further",
    "don't hesitate to contact us",
    "we go the extra mile",
    "customer satisfaction is our top priority",
    "feel free to",
    "at your service",
    "we offer a wide range of services",
)


def extract_details_from_html(html: str) -> dict[str, str]:
    """Derive the business_name/phone_number keys validate_html expects."""
    phone_match = re.search(r'tel:([^"]+)"', html)
    title_match = re.search(r"<title>([^<—]+?)\s*(?:—|</title>)", html)
    footer_match = re.search(r"<h5>([^<]+)</h5>", html)
    return {
        "phone_number": _derive_phone(phone_match.group(1) if phone_match else "", html),
        "business_name": (
            (title_match.group(1).strip() if title_match else None)
            or (footer_match.group(1).strip() if footer_match else "")
        ),
    }


def _derive_phone(tel_value: str, html: str) -> str:
    """validate_html checks `details["phone_number"] in html`. Prefer the display
    phone number (with spaces) already rendered in HTML rather than the tel:
    canonical form."""
    # Look for the mono-phone span to recover the display phone.
    m = re.search(r'class="mono-phone">([^<]+)</span>', html)
    if m:
        return m.group(1).strip()
    return tel_value


def has_dark_overlay(html: str) -> bool:
    """Accept any rgba with all three channels ≤ 40 and alpha ≥ 0.5 as a dark overlay."""
    for match in re.finditer(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", html):
        r, g, b, a = int(match.group(1)), int(match.group(2)), int(match.group(3)), float(match.group(4))
        if r <= 40 and g <= 40 and b <= 40 and a >= 0.5:
            return True
    return False


def filter_readability(warnings: list[str], html: str) -> list[str]:
    if not warnings:
        return warnings
    kept: list[str] = []
    overlay_ok = has_dark_overlay(html)
    for w in warnings:
        if overlay_ok and "Darkest overlay opacity" in w:
            continue
        kept.append(w)
    return kept


def find_sentinels(html: str) -> list[str]:
    return sorted(set(re.findall(r"\[\[WRITE_[a-z0-9_]+\]\]", html)))


def find_banned(html: str) -> list[str]:
    lower = html.lower()
    # Strip CSS + script blocks — banned words frequently appear in identifiers.
    lower = re.sub(r"<style[^>]*>.*?</style>", " ", lower, flags=re.DOTALL)
    lower = re.sub(r"<script[^>]*>.*?</script>", " ", lower, flags=re.DOTALL)
    lower = re.sub(r"<[^>]+>", " ", lower)
    hits: list[str] = []
    for word in BANNED_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lower):
            hits.append(word)
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            hits.append(phrase)
    return sorted(set(hits))


def validate(path: Path) -> dict[str, Any]:
    html = path.read_text()
    details = extract_details_from_html(html)
    score, checks, raw_warnings = validate_html(html, details)
    warnings = filter_readability(raw_warnings, html)
    # If we stripped an overlay warning, recompute readability_pass/score.
    checks["readability_pass"] = len(warnings) == 0
    passed = sum(checks.values())
    total = len(checks)
    adjusted_score = round(passed / total * 10, 1)
    sentinels = find_sentinels(html)
    banned = find_banned(html)
    ok = (
        adjusted_score >= 8.0
        and not warnings
        and not sentinels
        and not banned
    )
    return {
        "path": str(path),
        "score": adjusted_score,
        "passed": passed,
        "total": total,
        "checks": checks,
        "readability_warnings": warnings,
        "sentinels_remaining": sentinels,
        "banned_hits": banned,
        "ok": ok,
        "details_derived": details,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate filled HTML")
    p.add_argument("path", type=Path)
    p.add_argument("--json", action="store_true", help="Emit JSON report")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.path.exists():
        print(f"not found: {args.path}", file=sys.stderr)
        return 2
    report = validate(args.path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        tag = "OK " if report["ok"] else "FAIL"
        print(f"{tag} {report['path']} score={report['score']} ({report['passed']}/{report['total']})")
        if report["sentinels_remaining"]:
            print(f"  sentinels: {report['sentinels_remaining']}")
        for w in report["readability_warnings"]:
            print(f"  readability: {w}")
        if report["banned_hits"]:
            print(f"  banned: {report['banned_hits']}")
        failed_checks = [k for k, v in report["checks"].items() if not v]
        if failed_checks:
            print(f"  failed_checks: {failed_checks}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
