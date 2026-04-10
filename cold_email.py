#!/usr/bin/env python3
"""Cold email engine — SMTP rotation, multi-step sequences, deliverability protection.

Sends cold outreach via direct SMTP (Google Workspace / any provider).
Rotates across multiple inboxes with per-account daily limits.
Manages 3-step follow-up sequences with configurable delays.
Tracks everything in JSON files. No external dependencies.

Usage:
    python3 cold_email.py --send <slug>         # send step 1 for one prospect
    python3 cold_email.py --drip                # send all due follow-ups
    python3 cold_email.py --status              # show pipeline health
    python3 cold_email.py --generate <slug>     # generate sequence emails for prospect
    python3 cold_email.py --generate-all        # generate sequences for all deployed prospects
    python3 cold_email.py --test <email>        # send test email to verify SMTP

Requires: config/smtp_accounts.json with at least one SMTP account configured.
"""

import json
import os
import random
import re
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
PROSPECTS_DIR = BASE_DIR / "prospects"

SMTP_ACCOUNTS_FILE = CONFIG_DIR / "smtp_accounts.json"
SEQUENCES_FILE = CONFIG_DIR / "sequences.json"
SEND_LOG_FILE = PROSPECTS_DIR / "send_log.json"
SUPPRESSED_FILE = PROSPECTS_DIR / "suppressed.json"
OUTREACH_LOG = PROSPECTS_DIR / "outreach.json"
DEPLOY_LOG = PROSPECTS_DIR / "deploys.json"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Daily send limit per inbox (conservative for deliverability)
DEFAULT_DAILY_LIMIT = 30

# Sequence delays in days (step 1 = immediate, step 2 = +3 days, step 3 = +7 days)
DEFAULT_DELAYS = [0, 3, 7]

UNSUBSCRIBE_FOOTER = "\n\n---\nDon't want to hear from me? Reply STOP and I'll remove you immediately."


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def load_json(path: Path) -> list | dict:
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_json(path: Path, data: list | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def get_key(name: str) -> str:
    return os.environ.get(name) or load_env().get(name) or ""


# ---------------------------------------------------------------------------
# SMTP account management
# ---------------------------------------------------------------------------

def load_accounts() -> list[dict]:
    """Load SMTP accounts from config.

    Expected format in config/smtp_accounts.json:
    [
        {
            "email": "fraser@fraserwebdesign.co.uk",
            "password": "app-password-here",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "daily_limit": 30,
            "display_name": "Fraser",
            "active": true
        }
    ]
    """
    accounts = load_json(SMTP_ACCOUNTS_FILE)
    if not accounts:
        print(f"No SMTP accounts configured. Create {SMTP_ACCOUNTS_FILE}")
        print("See config/smtp_accounts.example.json for format.")
        sys.exit(1)
    return [a for a in accounts if a.get("active", True)]


def get_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def count_sends_today(email: str, send_log: list[dict]) -> int:
    """Count how many emails this account sent today."""
    today = get_today()
    return sum(
        1 for entry in send_log
        if entry.get("from_email") == email
        and entry.get("sent_at", "").startswith(today)
        and entry.get("status") == "sent"
    )


def pick_account(send_log: list[dict]) -> dict | None:
    """Pick the account with the most remaining capacity today.

    Returns None if all accounts are at their daily limit.
    """
    accounts = load_accounts()
    today = get_today()

    candidates = []
    for account in accounts:
        limit = account.get("daily_limit", DEFAULT_DAILY_LIMIT)
        sent = count_sends_today(account["email"], send_log)
        remaining = limit - sent
        if remaining > 0:
            candidates.append((account, remaining))

    if not candidates:
        return None

    # Weighted random — accounts with more remaining capacity are more likely
    # This avoids predictable round-robin patterns
    total = sum(r for _, r in candidates)
    pick = random.randint(1, total)
    cumulative = 0
    for account, remaining in candidates:
        cumulative += remaining
        if pick <= cumulative:
            return account

    return candidates[0][0]


# ---------------------------------------------------------------------------
# Suppression list (unsubscribes + bounces)
# ---------------------------------------------------------------------------

def load_suppressed() -> set[str]:
    data = load_json(SUPPRESSED_FILE)
    if isinstance(data, list):
        return {entry.get("email", "").lower() for entry in data if entry.get("email")}
    return set()


def add_suppressed(email: str, reason: str) -> None:
    data = load_json(SUPPRESSED_FILE)
    if not isinstance(data, list):
        data = []

    # Don't add duplicates
    existing = {entry.get("email", "").lower() for entry in data}
    if email.lower() in existing:
        return

    data.append({
        "email": email.lower(),
        "reason": reason,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    save_json(SUPPRESSED_FILE, data)


def is_suppressed(email: str) -> bool:
    return email.lower() in load_suppressed()


# ---------------------------------------------------------------------------
# SMTP sending
# ---------------------------------------------------------------------------

def send_smtp(
    account: dict,
    to_email: str,
    subject: str,
    body_text: str,
) -> tuple[bool, str]:
    """Send plain text email via SMTP. Returns (success, error_message)."""
    msg = MIMEMultipart("alternative")
    display_name = account.get("display_name", "Fraser")
    msg["From"] = f"{display_name} <{account['email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = account["email"]

    # Plain text only — better deliverability for cold email
    msg.attach(MIMEText(body_text + UNSUBSCRIBE_FOOTER, "plain", "utf-8"))

    host = account.get("smtp_host", "smtp.gmail.com")
    port = account.get("smtp_port", 587)

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(account["email"], account["password"])
            server.send_message(msg)
        return True, ""
    except smtplib.SMTPRecipientsRefused as e:
        # Hard bounce — suppress this address
        add_suppressed(to_email, f"hard_bounce: {e}")
        return False, f"hard_bounce: {e}"
    except smtplib.SMTPResponseException as e:
        code = e.smtp_code
        error_msg = e.smtp_error.decode("utf-8", errors="replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
        # 5xx = permanent failure, suppress
        if 500 <= code < 600:
            add_suppressed(to_email, f"smtp_{code}: {error_msg}")
        return False, f"smtp_{code}: {error_msg}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Sequence email generation
# ---------------------------------------------------------------------------

def generate_sequence(prospect: dict, preview_url: str, payment_url: str) -> list[dict]:
    """Generate 3-step email sequence via AI."""
    api_key = get_key("openrouter")
    if not api_key:
        raise RuntimeError("No openrouter key in .env")

    name = prospect.get("business_name", "Business Owner")
    category = prospect.get("business_category", "service")
    city = prospect.get("city", "")
    rating = prospect.get("rating", 0)
    review_count = prospect.get("review_count", 0)

    prompt = f"""Write a 3-email cold outreach sequence for a local {category} business.

BUSINESS: {name}
LOCATION: {city}
RATING: {rating}/5 ({review_count} reviews on Google)
THEIR NEW SITE: {preview_url}
PAYMENT LINK: {payment_url}

SEQUENCE:

EMAIL 1 (Day 0) — "I built you a website"
- Subject: short, curiosity-driven, their business name
- Open with their Google reputation (specific rating + review count)
- Core: "I built you a new website. Here it is." + preview link
- What the site includes (mobile-friendly, real reviews, contact form)
- CTA: payment link, £29/month, cancel anytime
- Sign off: Fraser

EMAIL 2 (Day 3) — Follow-up bump
- Subject: "re: " + email 1 subject (same thread feel)
- Short — 3-4 sentences max
- New angle: mention one specific thing about their site (e.g. "the reviews section turned out well")
- Soft CTA: "worth a look if you haven't yet"
- Sign off: Fraser

EMAIL 3 (Day 7) — Breakup / scarcity
- Subject: new thread, "quick question about {name}"
- Frame: "I built this for you specifically, but if you're not interested I'll reassign the design"
- Not aggressive — just honest that you'll move on
- Final CTA: payment link
- Sign off: Fraser

RULES:
- PLAIN TEXT ONLY. No HTML. No formatting. Just text like a real person typing.
- Each email: 80-150 words. Short paragraphs. Like texting, not copywriting.
- TONE: direct, warm, like a local freelancer. Not salesy.
- NO buzzwords. NO "leverage", "synergy", "cutting-edge", "bespoke", "tailored".
- NO "I noticed your business doesn't have..." — we never mention their current site.
- NO images, no attachments.
- Every email must stand alone (reader might not have seen previous ones).

Return ONLY a JSON array of 3 objects:
[
  {{"step": 1, "subject": "...", "body": "..."}},
  {{"step": 2, "subject": "...", "body": "..."}},
  {{"step": 3, "subject": "...", "body": "..."}}
]"""

    payload = json.dumps({
        "model": "openai/gpt-4.1-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000,
    }).encode("utf-8")

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if "error" in result:
        raise RuntimeError(f"OpenRouter error: {result['error']}")

    content = result["choices"][0]["message"]["content"]

    # Extract JSON array from response
    json_match = re.search(r"\[[\s\S]*\]", content)
    if not json_match:
        raise RuntimeError(f"AI didn't return JSON array: {content[:200]}")

    return json.loads(json_match.group(0))


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def send_cold_email(slug: str, step: int = 1) -> bool:
    """Send a specific sequence step to a prospect."""
    outreach = load_json(OUTREACH_LOG)
    record = next((o for o in outreach if o["slug"] == slug), None)
    if not record:
        print(f"No outreach record for: {slug}")
        return False

    to_email = record.get("contact_email", "")
    if not to_email:
        print(f"No contact email for {record['business_name']}. Run enrichment first.")
        return False

    if is_suppressed(to_email):
        print(f"SUPPRESSED: {to_email} — skipping")
        return False

    # Load sequence for this prospect
    sequences = load_json(SEQUENCES_FILE)
    prospect_seq = next((s for s in sequences if s["slug"] == slug), None)
    if not prospect_seq:
        print(f"No sequence generated for {slug}. Run: python3 cold_email.py --generate {slug}")
        return False

    steps = prospect_seq.get("steps", [])
    step_data = next((s for s in steps if s["step"] == step), None)
    if not step_data:
        print(f"No step {step} in sequence for {slug}")
        return False

    # Check send log — already sent this step?
    send_log = load_json(SEND_LOG_FILE)
    if not isinstance(send_log, list):
        send_log = []

    already_sent = any(
        e["slug"] == slug and e["step"] == step and e["status"] == "sent"
        for e in send_log
    )
    if already_sent:
        print(f"Step {step} already sent to {record['business_name']}")
        return False

    # Pick sending account
    account = pick_account(send_log)
    if not account:
        print("All SMTP accounts at daily limit. Try again tomorrow.")
        return False

    from_email = account["email"]
    subject = step_data["subject"]
    body = step_data["body"]

    print(f"  [{from_email}] → {to_email}")
    print(f"  Subject: {subject}")
    print(f"  Step: {step}/3")

    ok, error = send_smtp(account, to_email, subject, body)

    entry = {
        "slug": slug,
        "business_name": record["business_name"],
        "to_email": to_email,
        "from_email": from_email,
        "subject": subject,
        "step": step,
        "status": "sent" if ok else "failed",
        "error": error if not ok else "",
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    send_log.append(entry)
    save_json(SEND_LOG_FILE, send_log)

    if ok:
        print(f"  SENT")
    else:
        print(f"  FAILED: {error}")

    return ok


def run_drip() -> None:
    """Check send_log and send any due follow-ups."""
    send_log = load_json(SEND_LOG_FILE)
    if not isinstance(send_log, list):
        send_log = []

    sequences = load_json(SEQUENCES_FILE)
    if not sequences:
        print("No sequences generated. Run --generate-all first.")
        return

    now = datetime.now(timezone.utc)
    delays = DEFAULT_DELAYS
    sent_count = 0
    skipped_count = 0

    print(f"\n{'=' * 60}")
    print(f"  DRIP CHECK — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'=' * 60}\n")

    for seq in sequences:
        slug = seq["slug"]
        steps = seq.get("steps", [])

        # Find what steps have been sent
        sent_steps = [
            e for e in send_log
            if e["slug"] == slug and e["status"] == "sent"
        ]
        sent_step_nums = {e["step"] for e in sent_steps}

        if not sent_step_nums:
            # Step 1 never sent — skip (use --send for initial sends)
            continue

        # Anchor all delays to step 1 send time (deterministic regardless of retries)
        step1_entry = next(
            (e for e in sent_steps if e["step"] == 1),
            None,
        )
        if not step1_entry:
            continue

        max_sent = max(sent_step_nums)
        if max_sent >= len(steps):
            # All steps sent
            continue

        next_step = max_sent + 1
        step1_sent_at = datetime.fromisoformat(step1_entry["sent_at"])

        # Absolute delay from step 1
        delay_days = delays[next_step - 1] if next_step - 1 < len(delays) else delays[-1]
        due_at = step1_sent_at + timedelta(days=delay_days)

        if now >= due_at:
            print(f"  DUE: {seq.get('business_name', slug)} — step {next_step}")
            ok = send_cold_email(slug, step=next_step)
            if ok:
                sent_count += 1
            else:
                skipped_count += 1
        else:
            remaining = due_at - now
            hours_left = remaining.total_seconds() / 3600
            print(f"  WAITING: {seq.get('business_name', slug)} — step {next_step} due in {hours_left:.0f}h")

    print(f"\n  Sent: {sent_count} | Skipped: {skipped_count}")


def generate_for_prospect(slug: str) -> bool:
    """Generate 3-step sequence for a specific prospect."""
    outreach = load_json(OUTREACH_LOG)
    deploys = load_json(DEPLOY_LOG)

    record = next((o for o in outreach if o["slug"] == slug), None)
    if not record:
        print(f"No outreach record for: {slug}")
        return False

    preview_url = record.get("preview_url", "")
    payment_url = record.get("payment_url", "")

    # Find prospect data for richer generation
    from outreach import find_prospect_data
    prospect = find_prospect_data(slug) or {
        "business_name": record.get("business_name", slug),
        "business_category": "service",
        "city": "",
        "rating": 0,
        "review_count": 0,
    }

    print(f"  Generating 3-step sequence for {record['business_name']}...")

    try:
        steps = generate_sequence(prospect, preview_url, payment_url)
    except Exception as e:
        print(f"  Generation failed: {e}")
        return False

    # Save to sequences file
    sequences = load_json(SEQUENCES_FILE)
    if not isinstance(sequences, list):
        sequences = []

    # Remove existing sequence for this slug
    sequences = [s for s in sequences if s.get("slug") != slug]

    sequences.append({
        "slug": slug,
        "business_name": record.get("business_name", slug),
        "preview_url": preview_url,
        "payment_url": payment_url,
        "steps": steps,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })

    save_json(SEQUENCES_FILE, sequences)

    for step in steps:
        print(f"  Step {step['step']}: {step['subject']}")

    return True


def generate_all() -> None:
    """Generate sequences for all prospects with outreach records."""
    outreach = load_json(OUTREACH_LOG)
    if not outreach:
        print("No outreach records. Run outreach.py first.")
        return

    print(f"\nGenerating sequences for {len(outreach)} prospects...\n")

    for record in outreach:
        slug = record["slug"]
        print(f"[{slug}]")
        generate_for_prospect(slug)
        print()


def show_status() -> None:
    """Show cold email pipeline health."""
    accounts = load_json(SMTP_ACCOUNTS_FILE)
    send_log = load_json(SEND_LOG_FILE)
    if not isinstance(send_log, list):
        send_log = []
    sequences = load_json(SEQUENCES_FILE)
    if not isinstance(sequences, list):
        sequences = []
    suppressed = load_suppressed()

    print(f"\n{'=' * 60}")
    print(f"  COLD EMAIL STATUS")
    print(f"{'=' * 60}\n")

    # Account health
    print(f"  SMTP ACCOUNTS ({len(accounts)} configured):")
    for account in accounts:
        email = account["email"]
        active = account.get("active", True)
        limit = account.get("daily_limit", DEFAULT_DAILY_LIMIT)
        sent = count_sends_today(email, send_log)
        status = "ACTIVE" if active else "PAUSED"
        print(f"    [{status}] {email}: {sent}/{limit} today")

    # Capacity
    total_capacity = sum(a.get("daily_limit", DEFAULT_DAILY_LIMIT) for a in accounts if a.get("active", True))
    total_sent = sum(count_sends_today(a["email"], send_log) for a in accounts)
    print(f"\n  Daily capacity: {total_sent}/{total_capacity}")

    # Sequences
    print(f"\n  SEQUENCES ({len(sequences)} generated):")
    for seq in sequences:
        slug = seq["slug"]
        name = seq.get("business_name", slug)
        steps_sent = [
            e for e in send_log
            if e["slug"] == slug and e["status"] == "sent"
        ]
        step_nums = sorted({e["step"] for e in steps_sent})
        total_steps = len(seq.get("steps", []))
        progress = f"{len(step_nums)}/{total_steps}"
        print(f"    {name}: {progress} steps sent {step_nums or '(none)'}")

    # Send log summary
    total_all_time = len([e for e in send_log if e["status"] == "sent"])
    total_failed = len([e for e in send_log if e["status"] == "failed"])
    total_bounced = len([e for e in send_log if "bounce" in e.get("error", "")])
    print(f"\n  TOTALS:")
    print(f"    Sent (all time): {total_all_time}")
    print(f"    Failed: {total_failed}")
    print(f"    Bounced: {total_bounced}")
    print(f"    Suppressed: {len(suppressed)}")

    # Bounce rate
    if total_all_time > 0:
        bounce_rate = total_bounced / total_all_time * 100
        print(f"    Bounce rate: {bounce_rate:.1f}%", end="")
        if bounce_rate > 3:
            print(" ⚠ HIGH — check email quality")
        else:
            print(" OK")


def send_test(to_email: str) -> None:
    """Send a test email to verify SMTP is working."""
    send_log = load_json(SEND_LOG_FILE)
    if not isinstance(send_log, list):
        send_log = []

    account = pick_account(send_log)
    if not account:
        print("No SMTP accounts available.")
        return

    print(f"  Sending test from {account['email']} to {to_email}...")

    ok, error = send_smtp(
        account,
        to_email,
        "[TEST] Cold email system — SMTP verification",
        "This is a test email from the Hermes cold email engine.\n\nIf you received this, SMTP is working correctly.",
    )

    if ok:
        print(f"  SENT — check {to_email}")
    else:
        print(f"  FAILED: {error}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]

    print("=" * 60)
    print("  HERMES COLD EMAIL ENGINE")
    print("=" * 60)

    if "--test" in args:
        idx = args.index("--test")
        if idx + 1 >= len(args):
            print("Usage: python3 cold_email.py --test <email>")
            return 1
        send_test(args[idx + 1])
        return 0

    if "--generate" in args:
        idx = args.index("--generate")
        if idx + 1 >= len(args):
            print("Usage: python3 cold_email.py --generate <slug>")
            return 1
        return 0 if generate_for_prospect(args[idx + 1]) else 1

    if "--generate-all" in args:
        generate_all()
        return 0

    if "--send" in args:
        idx = args.index("--send")
        if idx + 1 >= len(args):
            print("Usage: python3 cold_email.py --send <slug>")
            return 1
        slug = args[idx + 1]
        step = 1
        if "--step" in args:
            step_idx = args.index("--step")
            if step_idx + 1 >= len(args):
                print("Usage: python3 cold_email.py --send <slug> --step <1|2|3>")
                return 1
            try:
                step = int(args[step_idx + 1])
            except ValueError:
                print(f"Invalid step: {args[step_idx + 1]}. Use 1, 2, or 3.")
                return 1
        return 0 if send_cold_email(slug, step=step) else 1

    if "--drip" in args:
        run_drip()
        return 0

    if "--status" in args:
        show_status()
        return 0

    if "--suppress" in args:
        idx = args.index("--suppress")
        if idx + 1 >= len(args):
            print("Usage: python3 cold_email.py --suppress <email>")
            return 1
        add_suppressed(args[idx + 1], "manual")
        print(f"Suppressed: {args[idx + 1]}")
        return 0

    # Default: show status
    show_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
