#!/usr/bin/env python3
"""Stripe webhook receiver — handles payment events.

On payment success: updates deploy status to "live", sends welcome email.
On subscription cancel: updates status to "paused".

Usage:
    python3 webhook_server.py                  # start on port 8788
    python3 webhook_server.py --port 9000      # custom port

For local testing:
    stripe listen --forward-to localhost:8788/webhooks/stripe

For production: deploy to VPS and point Stripe webhook to:
    https://yourvps.com/webhooks/stripe

Requires in .env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, SENDGRID_API_KEY
"""

import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
PROSPECTS_DIR = BASE_DIR / "prospects"
DEPLOY_LOG = PROSPECTS_DIR / "deploys.json"
OUTREACH_LOG = PROSPECTS_DIR / "outreach.json"
CONVERSION_LOG = PROSPECTS_DIR / "conversions.json"


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


def load_json(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Stripe signature verification
# ---------------------------------------------------------------------------

def verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify Stripe webhook signature."""
    if not sig_header or not secret:
        return False

    # Parse signature header
    elements = dict(
        item.split("=", 1)
        for item in sig_header.split(",")
        if "=" in item
    )

    timestamp = elements.get("t", "")
    signature = elements.get("v1", "")

    if not timestamp or not signature:
        return False

    # Check timestamp tolerance (5 minutes)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_payment_success(session: dict) -> None:
    """Handle checkout.session.completed — mark site as live, send welcome email."""
    customer_email = session.get("customer_details", {}).get("email", "")
    customer_name = session.get("customer_details", {}).get("name", "")
    amount = session.get("amount_total", 0)

    # Extract business name from custom fields
    business_name = ""
    for field in session.get("custom_fields", []):
        if field.get("key") == "business_name":
            business_name = field.get("text", {}).get("value", "")
            break

    print(f"\n  PAYMENT CONFIRMED: {business_name or customer_email}")
    print(f"  Amount: £{amount / 100:.2f}")
    print(f"  Email: {customer_email}")

    # Find matching deploy and update status
    deploys = load_json(DEPLOY_LOG)
    matched_deploy = None

    if business_name:
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", business_name.lower()).strip("-")
        for d in deploys:
            if d.get("slug") == slug or slug in d.get("slug", ""):
                d["status"] = "live"
                matched_deploy = d
                break

    if not matched_deploy:
        # Try matching by any available info
        for d in deploys:
            if d.get("status") == "preview":
                d["status"] = "live"
                matched_deploy = d
                print(f"  WARNING: Fuzzy matched to {d['slug']}. Verify manually.")
                break

    save_json(DEPLOY_LOG, deploys)

    # Update outreach log
    outreach = load_json(OUTREACH_LOG)
    for o in outreach:
        if matched_deploy and o.get("slug") == matched_deploy.get("slug"):
            o["status"] = "converted"
            break
    save_json(OUTREACH_LOG, outreach)

    # Log conversion
    conversions = load_json(CONVERSION_LOG)
    conversions.append({
        "business_name": business_name,
        "customer_email": customer_email,
        "customer_name": customer_name,
        "amount_pence": amount,
        "currency": session.get("currency", "gbp"),
        "stripe_session_id": session.get("id", ""),
        "deploy_slug": matched_deploy.get("slug", "") if matched_deploy else "",
        "live_url": matched_deploy.get("url", "") if matched_deploy else "",
        "converted_at": datetime.now(timezone.utc).isoformat(),
    })
    save_json(CONVERSION_LOG, conversions)

    # Send welcome email
    if customer_email and matched_deploy:
        send_welcome_email(
            customer_email,
            customer_name or business_name,
            matched_deploy.get("url", ""),
        )

    print(f"  Site status: LIVE")
    print(f"  Conversion logged.")


def handle_subscription_cancelled(subscription: dict) -> None:
    """Handle customer.subscription.deleted — pause the site."""
    customer_id = subscription.get("customer", "")
    print(f"\n  SUBSCRIPTION CANCELLED: {customer_id}")

    # Find and pause the site
    deploys = load_json(DEPLOY_LOG)
    for d in deploys:
        if d.get("status") == "live":
            # TODO: match by customer ID stored at conversion time
            # For now, log the event for manual handling
            pass
    save_json(DEPLOY_LOG, deploys)

    print(f"  Logged for manual review. Match customer to site and pause.")


def send_welcome_email(to_email: str, name: str, live_url: str) -> None:
    """Send welcome email via SendGrid."""
    sg_key = get_key("SENDGRID_API_KEY")
    if not sg_key:
        print("  No SendGrid key — skipping welcome email.")
        return

    env = load_env()
    sender_email = env.get("SENDER_EMAIL", "hello@hermes.agency")
    sender_name = env.get("SENDER_NAME", "Hermes")

    subject = f"Your website is live, {name.split()[0] if name else 'there'}"

    body_text = f"""Hi {name.split()[0] if name else 'there'},

Your site is live: {live_url}

What's included:
- Mobile-friendly design
- Your Google reviews displayed
- Contact form (replies go to your email)
- Google-ready (local search optimised)

What happens next:
- We check in monthly with a short report
- Reply to this email anytime for changes
- Want your own domain? Reply "domain" and we'll sort it

Your subscription: £29/month — cancel anytime, no questions.

{sender_name}"""

    body_html = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<p>Hi {name.split()[0] if name else 'there'},</p>

<p>Your site is live:<br>
<a href="{live_url}" style="color: #2563eb; font-weight: bold; font-size: 18px;">{live_url}</a></p>

<p><strong>What's included:</strong></p>
<ul>
<li>Mobile-friendly design</li>
<li>Your Google reviews displayed</li>
<li>Contact form (replies go to your email)</li>
<li>Google-ready (local search optimised)</li>
</ul>

<p><strong>What happens next:</strong></p>
<ul>
<li>We check in monthly with a short report</li>
<li>Reply to this email anytime for changes</li>
<li>Want your own domain? Reply "domain" and we'll sort it</li>
</ul>

<p style="color: #6b7280; font-size: 14px;">Your subscription: £29/month — cancel anytime, no questions.</p>

<p>{sender_name}</p>
</div>"""

    payload = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": sender_email, "name": sender_name},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": body_text},
            {"type": "text/html", "value": body_html},
        ],
    }).encode("utf-8")

    req = Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {sg_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            print(f"  Welcome email sent to {to_email}")
    except HTTPError as e:
        print(f"  Welcome email failed: {e.code}")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhooks/stripe":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)
        sig_header = self.headers.get("Stripe-Signature", "")

        # Verify signature
        webhook_secret = get_key("STRIPE_WEBHOOK_SECRET")
        if webhook_secret and not verify_stripe_signature(payload, sig_header, webhook_secret):
            print("  REJECTED: invalid signature")
            self.send_response(401)
            self.end_headers()
            return

        try:
            event = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        event_type = event.get("type", "")
        print(f"\n[WEBHOOK] {event_type}")

        if event_type == "checkout.session.completed":
            handle_payment_success(event.get("data", {}).get("object", {}))
        elif event_type == "customer.subscription.deleted":
            handle_subscription_cancelled(event.get("data", {}).get("object", {}))
        else:
            print(f"  Unhandled event: {event_type}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"received": true}')

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hermes Webhook Server")

    def log_message(self, format, *args):
        # Quieter logging
        print(f"  [{self.log_date_time_string()}] {format % args}")


def main() -> int:
    port = 8788
    args = sys.argv[1:]
    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 < len(args):
            port = int(args[idx + 1])

    # Verify keys exist
    missing = []
    if not get_key("STRIPE_SECRET_KEY"):
        missing.append("STRIPE_SECRET_KEY")
    if not get_key("STRIPE_WEBHOOK_SECRET"):
        missing.append("STRIPE_WEBHOOK_SECRET")
    if not get_key("SENDGRID_API_KEY"):
        missing.append("SENDGRID_API_KEY")

    if missing:
        print(f"WARNING: Missing keys: {', '.join(missing)}")
        print("Server will start but some features won't work.\n")

    print("=" * 60)
    print("  HERMES WEBHOOK SERVER")
    print(f"  Listening on http://127.0.0.1:{port}")
    print(f"  Endpoint: http://127.0.0.1:{port}/webhooks/stripe")
    print("=" * 60)
    print()
    print("For local testing with Stripe CLI:")
    print(f"  stripe listen --forward-to localhost:{port}/webhooks/stripe")
    print()

    server = HTTPServer(("127.0.0.1", port), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
