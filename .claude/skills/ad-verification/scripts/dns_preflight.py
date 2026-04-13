#!/usr/bin/env python3
"""SPF / DKIM / DMARC pre-flight check for sender domains.

Gmail/Yahoo 2024 bulk-sender rules require all three to be aligned. Without
them, cold sends will be junked or block the account. This script verifies
DNS records exist and look valid before any send is permitted.

Usage:
    python3 dns_preflight.py --domain example.com [--dkim-selector google]
    python3 dns_preflight.py --check-all  # check every account in config/smtp_accounts.json

Exit code:
    0 = all checks pass
    1 = at least one check failed (auto-send must remain disabled)
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[3]
SMTP_CONFIG = BASE_DIR / "config" / "smtp_accounts.json"


def dig_txt(name: str) -> list[str]:
    """Run dig +short TXT and return list of trimmed strings."""
    try:
        result = subprocess.run(
            ["dig", "+short", "TXT", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:
        return [f"__error__:{e}"]
    out = []
    for line in result.stdout.splitlines():
        line = line.strip().strip('"')
        if line:
            out.append(line)
    return out


def check_spf(domain: str) -> tuple[bool, str]:
    records = dig_txt(domain)
    spf_records = [r for r in records if r.startswith("v=spf1")]
    if not spf_records:
        return False, f"no SPF record on {domain}"
    if len(spf_records) > 1:
        return False, f"multiple SPF records on {domain} (RFC 7208 violation)"
    record = spf_records[0]
    if "_spf.google.com" not in record and "include:" not in record:
        return False, f"SPF doesn't include any sender authorization: {record[:80]}"
    return True, record[:120]


def check_dkim(domain: str, selector: str = "google") -> tuple[bool, str]:
    name = f"{selector}._domainkey.{domain}"
    records = dig_txt(name)
    dkim = [r for r in records if "v=DKIM1" in r or "p=" in r]
    if not dkim:
        return False, f"no DKIM record at {name}"
    if "p=" not in dkim[0]:
        return False, f"DKIM record missing public key at {name}"
    return True, f"selector={selector}, record present"


def check_dmarc(domain: str) -> tuple[bool, str]:
    records = dig_txt(f"_dmarc.{domain}")
    dmarc = [r for r in records if r.startswith("v=DMARC1")]
    if not dmarc:
        return False, f"no DMARC record at _dmarc.{domain}"
    record = dmarc[0]
    if "p=none" in record:
        return False, "DMARC policy is p=none — Gmail/Yahoo 2024 rules require p=quarantine or p=reject"
    if "p=quarantine" not in record and "p=reject" not in record:
        return False, f"DMARC policy unclear: {record[:100]}"
    return True, record[:120]


def check_domain(domain: str, dkim_selector: str = "google") -> dict[str, Any]:
    spf_ok, spf_msg = check_spf(domain)
    dkim_ok, dkim_msg = check_dkim(domain, dkim_selector)
    dmarc_ok, dmarc_msg = check_dmarc(domain)
    return {
        "domain": domain,
        "spf": {"pass": spf_ok, "detail": spf_msg},
        "dkim": {"pass": dkim_ok, "detail": dkim_msg},
        "dmarc": {"pass": dmarc_ok, "detail": dmarc_msg},
        "all_pass": spf_ok and dkim_ok and dmarc_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", help="check a single domain")
    parser.add_argument("--dkim-selector", default="google")
    parser.add_argument("--check-all", action="store_true", help="check all SMTP accounts in config")
    args = parser.parse_args()

    domains: list[tuple[str, str]] = []

    if args.domain:
        domains.append((args.domain, args.dkim_selector))

    if args.check_all:
        if not SMTP_CONFIG.exists():
            print(f"error: {SMTP_CONFIG} not found", file=sys.stderr)
            return 1
        accounts = json.loads(SMTP_CONFIG.read_text())
        for acc in accounts:
            email = acc.get("email", "")
            if "@" in email:
                d = email.split("@", 1)[1]
                selector = acc.get("dkim_selector", "google")
                domains.append((d, selector))

    if not domains:
        print("provide --domain or --check-all", file=sys.stderr)
        return 1

    all_pass = True
    for domain, selector in domains:
        result = check_domain(domain, selector)
        status = "PASS" if result["all_pass"] else "FAIL"
        print(f"\n{'='*60}\n{status} — {domain}\n{'='*60}")
        for key in ("spf", "dkim", "dmarc"):
            r = result[key]
            mark = "✓" if r["pass"] else "✗"
            print(f"  {mark} {key.upper():6} {r['detail']}")
        if not result["all_pass"]:
            all_pass = False

    if not all_pass:
        print("\n❌ AT LEAST ONE DNS CHECK FAILED — auto-send must remain disabled", file=sys.stderr)
        return 1

    print("\n✅ all DNS checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
