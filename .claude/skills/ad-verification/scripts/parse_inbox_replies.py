#!/usr/bin/env python3
"""IMAP poller that suppresses STOP replies and NDR bounces.

Run daily via cron. For each configured SMTP account:
1. Connect via IMAP, scan INBOX for messages from the last 48h
2. Detect STOP/UNSUBSCRIBE/REMOVE/OPT OUT keywords in plaintext body
3. Detect NDR/bounce messages (Mailer-Daemon, postmaster, "delivery failure")
4. Add affected addresses to `prospects/suppressed.json`
5. Suppress at both address and domain level
6. Mark messages as read so they're not re-processed

Required env / config:
- `config/imap_accounts.json` — list of {email, password, imap_host, imap_port}
  (mirrors smtp_accounts.json shape)

Usage:
    python3 parse_inbox_replies.py
    python3 parse_inbox_replies.py --erase user@example.com   # GDPR erasure command
    python3 parse_inbox_replies.py --dry-run
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import getaddresses
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[3]
SUPPRESSED_PATH = BASE_DIR / "prospects" / "suppressed.json"
IMAP_CONFIG_PATH = BASE_DIR / "config" / "imap_accounts.json"

STOP_KEYWORDS = re.compile(
    r"\b(stop|unsubscribe|remove me|opt out|opt-out|delete me|do not (email|contact)|"
    r"please remove|take me off)\b",
    re.IGNORECASE,
)

DELETE_KEYWORDS = re.compile(r"\b(delete|erase|gdpr|right to be forgotten)\b", re.IGNORECASE)

NDR_HEADERS = {"mailer-daemon", "postmaster"}

NDR_BODY_PATTERNS = [
    r"could not be delivered",
    r"delivery (status|has failed)",
    r"recipient address rejected",
    r"undeliverable",
    r"mailbox unavailable",
    r"user unknown",
    r"no such user",
    r"550 ",
    r"553 ",
]


def load_suppressed() -> set[str]:
    if not SUPPRESSED_PATH.exists():
        return set()
    try:
        data = json.loads(SUPPRESSED_PATH.read_text())
        if isinstance(data, list):
            return {x.lower() for x in data}
        if isinstance(data, dict):
            return {x.lower() for x in data.keys()}
    except Exception:
        pass
    return set()


def save_suppressed(suppressed: set[str], reasons: dict[str, str]) -> None:
    SUPPRESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if SUPPRESSED_PATH.exists():
        try:
            data = json.loads(SUPPRESSED_PATH.read_text())
            if isinstance(data, dict):
                existing = data
            elif isinstance(data, list):
                existing = {x: "legacy" for x in data}
        except Exception:
            pass
    for addr in suppressed:
        existing[addr] = reasons.get(addr, "unknown")
    SUPPRESSED_PATH.write_text(json.dumps(existing, indent=2))


def load_imap_accounts() -> list[dict[str, Any]]:
    if not IMAP_CONFIG_PATH.exists():
        print(f"warning: {IMAP_CONFIG_PATH} not found — copy from smtp_accounts.json with imap_host/imap_port", file=sys.stderr)
        return []
    return json.loads(IMAP_CONFIG_PATH.read_text())


def decode_field(s: str | None) -> str:
    if not s:
        return ""
    try:
        parts = decode_header(s)
        out = ""
        for p, enc in parts:
            if isinstance(p, bytes):
                out += p.decode(enc or "utf-8", errors="replace")
            else:
                out += p
        return out
    except Exception:
        return str(s)


def extract_email(addr_field: str) -> str:
    """Pull the bare email from a 'Name <foo@bar.com>' string."""
    addrs = getaddresses([addr_field or ""])
    if addrs and addrs[0][1]:
        return addrs[0][1].lower()
    return ""


def get_body(msg) -> str:
    """Extract plaintext body from an email.Message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    return (payload or b"").decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    continue
        return ""
    try:
        return (msg.get_payload(decode=True) or b"").decode(msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


def detect_ndr(msg, body: str) -> tuple[bool, list[str]]:
    """Return (is_ndr, list_of_bounced_addresses)."""
    sender = extract_email(decode_field(msg.get("From", "")))
    sender_local = sender.split("@")[0]
    is_ndr = sender_local in NDR_HEADERS or any(re.search(p, body, re.IGNORECASE) for p in NDR_BODY_PATTERNS)
    if not is_ndr:
        return False, []
    # Find bounced addresses in the body — typically appear as "to: foo@bar.com" or in the original message section
    addrs = re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", body)
    # Drop obvious chrome
    bounced = []
    for a in addrs:
        a = a.lower()
        if a == sender or a.startswith(("postmaster@", "mailer-daemon@", "noreply@")):
            continue
        bounced.append(a)
    return True, list(set(bounced))


def detect_stop(body: str) -> bool:
    return bool(STOP_KEYWORDS.search(body or ""))


def process_account(account: dict[str, Any], dry_run: bool = False) -> dict[str, str]:
    """Scan one IMAP account and return {address: reason} for new suppressions."""
    new_suppress: dict[str, str] = {}
    host = account.get("imap_host", "imap.gmail.com")
    port = account.get("imap_port", 993)
    user = account["email"]
    pw = account["password"]

    try:
        M = imaplib.IMAP4_SSL(host, port)
        M.login(user, pw)
        M.select("INBOX")

        # Search messages from the last 48h
        since = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%d-%b-%Y")
        typ, data = M.search(None, f'(SINCE "{since}")')
        if typ != "OK":
            return {}

        ids = data[0].split()
        for msg_id in ids:
            typ, msg_data = M.fetch(msg_id, "(RFC822)")
            if typ != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            body = get_body(msg)
            sender = extract_email(decode_field(msg.get("From", "")))

            # NDR detection
            is_ndr, bounced = detect_ndr(msg, body)
            if is_ndr:
                for b in bounced:
                    new_suppress[b] = "hard_bounce_ndr"
                    domain = b.split("@")[1]
                    new_suppress[f"@{domain}"] = "hard_bounce_ndr_domain"
                continue

            # STOP detection on direct replies
            if sender and detect_stop(body):
                new_suppress[sender] = "stop_reply"
                domain = sender.split("@")[1]
                new_suppress[f"@{domain}"] = "stop_reply_domain"

        if not dry_run:
            M.close()
        M.logout()
    except Exception as e:
        print(f"imap_error {user}: {e}", file=sys.stderr)
        return {}

    return new_suppress


def erase_address(email_addr: str) -> int:
    """GDPR erasure — remove one address from all candidate stores."""
    needle = email_addr.lower()
    affected = 0
    for path in [
        BASE_DIR / "_workspace" / "retarget",
        BASE_DIR / "prospects",
    ]:
        if not path.exists():
            continue
        for f in path.rglob("*.json"):
            try:
                data = json.loads(f.read_text())
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            before = len(data)
            data = [c for c in data if (c.get("email") or "").lower() != needle]
            if len(data) < before:
                f.write_text(json.dumps(data, indent=2))
                affected += before - len(data)
    return affected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--erase", help="GDPR erasure: remove one address from all stores")
    args = parser.parse_args()

    if args.erase:
        n = erase_address(args.erase)
        print(f"erased {n} records matching {args.erase}")
        return 0

    accounts = load_imap_accounts()
    if not accounts:
        print("no imap accounts configured", file=sys.stderr)
        return 1

    all_new: dict[str, str] = {}
    for acc in accounts:
        result = process_account(acc, dry_run=args.dry_run)
        all_new.update(result)
        print(f"{acc['email']}: {len(result)} new suppressions", file=sys.stderr)

    if all_new and not args.dry_run:
        save_suppressed(set(all_new.keys()), all_new)
    print(f"total new suppressions: {len(all_new)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
