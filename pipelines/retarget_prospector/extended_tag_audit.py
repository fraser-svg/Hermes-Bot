#!/usr/bin/env python3
"""Detect call-tracking provider, phone type, and form tracking on prospect sites.

Reuses existing pixels_v2 audit. Adds:
    - call_tracking_provider: str | None
    - call_tracking_evidence: str
    - phone_type: "mobile"|"geographic"|"nongeographic"|"unknown"
    - form_tracking: {"ga4_event": bool, "gtm_tag": bool, "google_ads_conv": bool}

Input:  _workspace/retarget_scotland/scotland_prospects_gbp_graded.json
Output: _workspace/retarget_scotland/scotland_candidates_fullaudit.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
REFS = BASE / "references" / "call_tracking_prefixes.json"


def load_providers() -> dict:
    return json.loads(REFS.read_text())


def fetch(url: str, timeout: int = 12) -> str:
    if "://" not in url:
        url = "https://" + url
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; HermesAudit/1.0)"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read(500_000).decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, ConnectionError, UnicodeDecodeError):
        return ""
    except Exception:
        return ""


def detect_call_tracking(html: str, providers: dict) -> tuple[str | None, str]:
    lower = html.lower()
    for name, spec in providers["providers"].items():
        for host in spec.get("script_hosts", []):
            if host in lower:
                return name, f"script_host:{host}"
    # generic swap patterns
    if "dynamic number insertion" in lower or re.search(r"data-(callrail|responsetap|infinity)-", lower):
        return "unknown_dni", "dni_attribute_present"
    return None, ""


def detect_phone_type(phone: str, providers: dict) -> str:
    if not phone:
        return "unknown"
    p = re.sub(r"\s", "", phone)
    for pre in providers["uk_mobile_prefixes"]:
        if p.startswith(pre):
            return "mobile"
    for pre in providers["uk_nongeographic_prefixes"]:
        if p.startswith(pre):
            return "nongeographic"
    for pre in providers["uk_geographic_prefixes"]:
        if p.startswith(pre):
            return "geographic"
    return "unknown"


def detect_form_tracking(html: str) -> dict:
    lower = html.lower()
    return {
        "ga4_event": bool(re.search(r"gtag\([^)]*'event'[^)]*form", lower) or "form_submit" in lower),
        "gtm_tag": "googletagmanager.com/gtm.js" in lower or "dataLayer.push" in html,
        "google_ads_conv": bool(re.search(r"aw-\d+/[\w-]+", lower)) or "conversion_id" in lower,
        "tel_link": bool(re.search(r"href=[\"']tel:", lower)),
    }


def audit_row(row: dict, providers: dict) -> dict:
    url = row.get("website_url") or ""
    html = fetch(url) if url else ""
    provider, evidence = detect_call_tracking(html, providers)
    row["call_tracking_provider"] = provider
    row["call_tracking_evidence"] = evidence
    row["phone_type"] = detect_phone_type(row.get("phone_number") or row.get("phone_e164") or "", providers)
    row["form_tracking"] = detect_form_tracking(html)
    row["extended_audit_checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="_workspace/retarget_scotland/scotland_prospects_gbp_graded.json")
    ap.add_argument("--output", default="_workspace/retarget_scotland/scotland_candidates_fullaudit.json")
    args = ap.parse_args()

    providers = load_providers()
    rows = json.loads(Path(args.input).read_text())
    for i, row in enumerate(rows, 1):
        audit_row(row, providers)
        if i % 25 == 0:
            print(f"[{i}/{len(rows)}]", file=sys.stderr)
    Path(args.output).write_text(json.dumps(rows, indent=2))
    print(f"wrote {args.output}  n={len(rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
