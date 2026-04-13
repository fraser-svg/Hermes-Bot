#!/usr/bin/env python3
"""Composer hallucination guard.

Validates that any ad headline or company-name claim in a composed outreach
email actually exists verbatim in the candidate's verified ad creatives. If
the composer invented a quote, the lead is rejected for auto-send and routed
to manual review.

Usage:
    python3 validate_composer_output.py outreach.json --output validated.json

Input shape (per record):
    {
        "slug": "...",
        "business_name": "...",
        "email": {"subject": "...", "body": "..."},
        "meta_creatives": [{"page_name": "...", "headline": "...", "raw_excerpt": "..."}, ...],
        ...
    }

Adds fields:
    {
        "composer_validation": {
            "passed": bool,
            "checks": {
                "quoted_headline_grounded": bool,
                "page_name_referenced": bool,
                "no_generic_claims": bool,
                "footer_complete": bool,
            },
            "errors": [str, ...],
            "auto_send_eligible": bool,
        }
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_FOOTER_TOKENS = [
    "Company No",
    "Reply STOP",
    "legitimate interest",
]

GENERIC_HALLUCINATION_PHRASES = [
    "your competitors are",
    "limited spots",
    "acting fast",
    "we guarantee",
    "3x your",
    "double your",
]


def extract_quoted_strings(body: str) -> list[str]:
    """Find quoted strings in the email body — likely candidates for ad-headline claims."""
    quotes: list[str] = []
    # Standard quotes
    quotes.extend(re.findall(r'"([^"]{6,160})"', body))
    quotes.extend(re.findall(r"'([^']{6,160})'", body))
    # Smart quotes
    quotes.extend(re.findall(r'\u201c([^\u201d]{6,160})\u201d', body))
    quotes.extend(re.findall(r"\u2018([^\u2019]{6,160})\u2019", body))
    return quotes


def normalize_quote(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def find_in_creatives(quote: str, creatives: list[dict]) -> bool:
    """Return True if the quote appears verbatim in any creative's headline or raw_excerpt."""
    needle = normalize_quote(quote)
    if len(needle) < 6:
        return False
    for cr in creatives or []:
        for field in ("headline", "raw_excerpt", "body", "page_name"):
            hay = normalize_quote(cr.get(field, "") or "")
            if needle in hay:
                return True
    return False


def validate_one(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = (record.get("email") or {}).get("body", "")
    subject = (record.get("email") or {}).get("subject", "")
    creatives = record.get("meta_creatives") or []
    business_name = record.get("business_name", "")

    # Check 1: every quoted string must exist verbatim in some creative
    quotes = extract_quoted_strings(body) + extract_quoted_strings(subject)
    grounded = True
    for q in quotes:
        # Skip the business name itself — it's allowed to be quoted
        if normalize_quote(q) in normalize_quote(business_name):
            continue
        if not find_in_creatives(q, creatives):
            grounded = False
            errors.append(f"ungrounded_quote: '{q[:80]}' not found in any verified ad creative")

    # Check 2: page_name referenced (composer should know which Page is theirs)
    page_referenced = False
    for cr in creatives:
        pn = (cr.get("page_name") or "").lower()
        if pn and pn in body.lower():
            page_referenced = True
            break
    # Not strictly required but flagged
    if not page_referenced and creatives:
        errors.append("no_page_name_in_body (warning, not blocking)")

    # Check 3: no generic hallucination phrases
    no_generic = True
    body_low = body.lower()
    for phrase in GENERIC_HALLUCINATION_PHRASES:
        if phrase in body_low:
            no_generic = False
            errors.append(f"generic_phrase_found: '{phrase}'")

    # Check 4: footer completeness
    footer_complete = True
    for token in REQUIRED_FOOTER_TOKENS:
        if token not in body:
            footer_complete = False
            errors.append(f"footer_missing_token: '{token}'")

    # Strict gate: must be grounded + no generic + footer complete
    passed = grounded and no_generic and footer_complete

    record["composer_validation"] = {
        "passed": passed,
        "checks": {
            "quoted_headline_grounded": grounded,
            "page_name_referenced": page_referenced,
            "no_generic_claims": no_generic,
            "footer_complete": footer_complete,
        },
        "errors": errors,
        "auto_send_eligible": passed,
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text())
    records = raw if isinstance(raw, list) else [raw]

    validated = [validate_one(r) for r in records]
    Path(args.output).write_text(json.dumps(validated, indent=2, ensure_ascii=False))

    passed = sum(1 for r in validated if r.get("composer_validation", {}).get("passed"))
    print(f"validated {len(validated)}: {passed} passed, {len(validated) - passed} blocked", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
