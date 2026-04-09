#!/usr/bin/env python3
"""Send outreach emails via SendGrid with preview URLs and Stripe payment links.

Generates personalized emails per prospect, queues for approval,
sends via SendGrid on confirmation.

Usage:
    python3 outreach.py                        # process all deployed + unsent
    python3 outreach.py --preview              # generate emails, don't send
    python3 outreach.py --send slug-name       # send one approved email
    python3 outreach.py --status               # show outreach pipeline status

Requires in .env: SENDGRID_API_KEY, STRIPE_PUBLISHABLE_KEY, openrouter
Optional: SENDER_EMAIL, SENDER_NAME
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
PROSPECTS_DIR = BASE_DIR / "prospects"
DEPLOY_LOG = PROSPECTS_DIR / "deploys.json"
OUTREACH_LOG = PROSPECTS_DIR / "outreach.json"
OUTPUT_DIR = BASE_DIR / "output"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"

# Default sender — override in .env
DEFAULT_SENDER_EMAIL = "hello@hermes.agency"
DEFAULT_SENDER_NAME = "Hermes"


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
# Find prospect data for a deployed site
# ---------------------------------------------------------------------------

def find_prospect_data(slug: str) -> dict | None:
    """Search prospect JSON files for matching business by slug."""
    for json_file in PROSPECTS_DIR.glob("*.json"):
        if json_file.name in ("deploys.json", "outreach.json"):
            continue
        try:
            data = json.loads(json_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, list):
            continue

        for prospect in data:
            name = prospect.get("business_name", "")
            prospect_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            if prospect_slug == slug:
                return prospect

    return None


# ---------------------------------------------------------------------------
# Email generation via Gemini
# ---------------------------------------------------------------------------

def generate_email(prospect: dict, preview_url: str, payment_url: str) -> dict:
    """Generate personalized outreach email via Gemini."""
    api_key = get_key("openrouter")
    if not api_key:
        raise RuntimeError("No openrouter key in .env")

    name = prospect.get("business_name", "Business Owner")
    category = prospect.get("business_category", "service")
    city = prospect.get("city", "")
    rating = prospect.get("rating", 0)
    review_count = prospect.get("review_count", 0)
    phone = prospect.get("phone_number", "")

    prompt = f"""Write a short cold outreach email for a local {category} business.

BUSINESS: {name}
LOCATION: {city}
RATING: {rating}/5 ({review_count} reviews on Google)
THEIR PREVIEW SITE: {preview_url}

RULES:
- We already BUILT them a free website. It's live at the preview URL above.
- Subject line: short, curiosity-driven, their business name included
- Opening: acknowledge their Google reputation (be specific with their rating/reviews)
- Core message: "I built you a new website. Here it is." Link to preview URL.
- Short paragraph about what the site includes (mobile-friendly, their real reviews displayed, contact form)
- CTA: "If you want this live as your actual website, it's {payment_url}" — one click, £29/month, cancel anytime
- Sign off as a real person (first name only)
- TONE: direct, warm, not salesy. Like a neighbour who happens to build websites.
- LENGTH: 120-180 words max. Short paragraphs. No walls of text.
- NO buzzwords, NO "leverage", NO "synergy", NO "cutting-edge"
- NO attachments mentioned, NO "I noticed your business doesn't have..."

Return ONLY a JSON object:
{{"subject": "...", "body_text": "...", "body_html": "..."}}

body_html should be simple HTML email - no complex templates. Just styled text with a clear CTA button.
The CTA button should link to: {payment_url}
"""

    payload = json.dumps({
        "model": "openai/gpt-4.1-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000,
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

    content = result["choices"][0]["message"]["content"]

    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        raise RuntimeError(f"AI didn't return JSON: {content[:200]}")

    return json.loads(json_match.group(0))


# ---------------------------------------------------------------------------
# Stripe payment link generation
# ---------------------------------------------------------------------------

def create_payment_link(business_name: str) -> str:
    """Create a Stripe payment link for this prospect.

    Returns the payment link URL.
    """
    stripe_key = get_key("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise RuntimeError("No STRIPE_SECRET_KEY in .env")

    # First, find or create the product + price
    price_id = get_or_create_price(stripe_key)

    # Create payment link — keep it simple, no custom fields
    from urllib.parse import urlencode
    params = urlencode({
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
    }).encode("utf-8")

    result = stripe_request("POST", "/v1/payment_links", stripe_key, params)
    return result.get("url", "")


def get_or_create_price(stripe_key: str) -> str:
    """Find existing £29/mo price or create one."""
    # Search for existing product named "Local Business Website"
    result = stripe_request(
        "GET",
        "/v1/products?active=true&limit=10",
        stripe_key,
    )

    product_id = ""
    for product in result.get("data", []):
        if "local business website" in product.get("name", "").lower():
            product_id = product["id"]
            break

    if not product_id:
        # Create product
        from urllib.parse import urlencode
        params = urlencode({
            "name": "Local Business Website",
            "description": "Professional website with hosting, mobile design, and contact form. Cancel anytime.",
        }).encode("utf-8")
        product = stripe_request("POST", "/v1/products", stripe_key, params)
        product_id = product["id"]
        print(f"  Created Stripe product: {product_id}")

    # Find existing price
    result = stripe_request(
        "GET",
        f"/v1/prices?product={product_id}&active=true&limit=5",
        stripe_key,
    )

    for price in result.get("data", []):
        if (
            price.get("unit_amount") == 2900
            and price.get("currency") == "gbp"
            and price.get("recurring", {}).get("interval") == "month"
        ):
            return price["id"]

    # Create price: £29/month
    from urllib.parse import urlencode
    params = urlencode({
        "product": product_id,
        "unit_amount": "2900",
        "currency": "gbp",
        "recurring[interval]": "month",
    }).encode("utf-8")
    price = stripe_request("POST", "/v1/prices", stripe_key, params)
    print(f"  Created Stripe price: £29/mo ({price['id']})")
    return price["id"]


def stripe_request(
    method: str,
    path: str,
    key: str,
    data: bytes | None = None,
) -> dict:
    url = f"https://api.stripe.com{path}"
    req = Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method,
    )
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"Stripe API {e.code}: {body}") from e


# ---------------------------------------------------------------------------
# SendGrid email sending
# ---------------------------------------------------------------------------

def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str,
) -> bool:
    """Send email via SendGrid. Returns True on success."""
    sg_key = get_key("SENDGRID_API_KEY")
    if not sg_key:
        raise RuntimeError("No SENDGRID_API_KEY in .env")

    env = load_env()
    sender_email = env.get("SENDER_EMAIL", DEFAULT_SENDER_EMAIL)
    sender_name = env.get("SENDER_NAME", DEFAULT_SENDER_NAME)

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
        SENDGRID_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {sg_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201, 202)
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"  SendGrid error {e.code}: {body}")
        return False


# ---------------------------------------------------------------------------
# WhatsApp message generation
# ---------------------------------------------------------------------------

def generate_whatsapp(prospect: dict, preview_url: str, payment_url: str) -> str:
    """Generate short WhatsApp message via Gemini. Returns plain text."""
    api_key = get_key("openrouter")
    if not api_key:
        raise RuntimeError("No openrouter key in .env")

    env = load_env()
    sender_name = env.get("SENDER_NAME", "Alex")

    name = prospect.get("business_name", "your business")
    category = prospect.get("business_category", "service")
    city = prospect.get("city", "")
    rating = prospect.get("rating", 0)
    review_count = prospect.get("review_count", 0)

    prompt = f"""Write a short WhatsApp message to a local {category} business owner.

BUSINESS: {name}
LOCATION: {city}
RATING: {rating}/5 ({review_count} Google reviews)
THEIR NEW SITE: {preview_url}
PAYMENT LINK: {payment_url}
YOUR NAME: {sender_name}

RULES:
- We already BUILT them a free website. It's live at the preview URL.
- This is a WhatsApp message, NOT an email. Keep it conversational.
- MAX 4-5 short lines. Like texting a mate who runs a business.
- First line: quick intro + why you're messaging
- Middle: link to their site with one line about what it is
- Last line: simple CTA. "Want it live? {payment_url}" or similar
- Mention their rating/reviews as social proof (they earned it)
- NO formal greeting (no "Dear", no "I hope this finds you well")
- NO bullet points, NO HTML, NO formatting
- NO buzzwords. Talk like a real person.
- Sign off with: {sender_name}

Return ONLY the message text. No JSON. No quotes. Just the message."""

    payload = json.dumps({
        "model": "openai/gpt-4.1-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 300,
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

    return result["choices"][0]["message"]["content"].strip().strip('"')


def make_whatsapp_link(phone_e164: str, message: str) -> str:
    """Build a wa.me click-to-send link with pre-filled message."""
    from urllib.parse import quote as url_quote
    number = phone_e164.lstrip("+")
    return f"https://wa.me/{number}?text={url_quote(message)}"


def show_whatsapp_queue() -> None:
    """Show all WhatsApp-ready outreach with click-to-send links."""
    outreach = load_json(OUTREACH_LOG)
    if not outreach:
        print("No outreach records.")
        return

    wa_ready = [o for o in outreach if o.get("whatsapp_message") and o.get("whatsapp_link")]

    if not wa_ready:
        print("No WhatsApp messages generated yet.")
        print("Run: python3 outreach.py --preview  (generates for all queued)")
        return

    print(f"\n{'=' * 60}")
    print(f"  WHATSAPP OUTREACH ({len(wa_ready)} ready)")
    print(f"{'=' * 60}\n")

    for o in wa_ready:
        status = o.get("whatsapp_status", "pending")
        print(f"  [{status.upper()}] {o['business_name']}")
        print(f"  Phone: {o.get('mobile', {}).get('e164', o.get('phone', '?'))}")
        print(f"  Preview: {o['preview_url']}")
        print()
        print(f"  --- MESSAGE ---")
        for line in o["whatsapp_message"].split("\n"):
            print(f"  {line}")
        print(f"  --- END ---")
        print()
        print(f"  CLICK TO SEND: {o['whatsapp_link']}")
        print()
        print(f"  {'─' * 50}")
        print()


# ---------------------------------------------------------------------------
# Pipeline: generate outreach for all deployed sites
# ---------------------------------------------------------------------------

def process_all(preview_only: bool = False) -> None:
    deploys = load_json(DEPLOY_LOG)
    outreach = load_json(OUTREACH_LOG)

    if not deploys:
        print("No deployed sites. Run deploy.py first.")
        return

    sent_slugs = {o["slug"] for o in outreach if o.get("status") in ("sent", "approved", "queued")}
    pending = [d for d in deploys if d["slug"] not in sent_slugs and d.get("status") == "preview"]

    if not pending:
        print("All deployed sites already have outreach queued or sent.")
        return

    print(f"\nGenerating outreach for {len(pending)} sites...\n")

    for deploy in pending:
        slug = deploy["slug"]
        url = deploy["url"]
        print(f"[{slug}]")

        # Find prospect data
        prospect = find_prospect_data(slug)
        if not prospect:
            print("  WARNING: No prospect data found. Skipping.")
            continue

        # Check if we have contact email (we often won't from Google Maps)
        # For now, generate the email anyway — we'll find email during outreach prep
        contact_email = prospect.get("email", "")

        # Create Stripe payment link
        print("  Creating payment link...")
        try:
            payment_url = create_payment_link(prospect.get("business_name", slug))
        except Exception as e:
            print(f"  Stripe error: {e}")
            payment_url = "[PAYMENT_LINK_PENDING]"

        # Generate email
        print("  Generating email...")
        try:
            email = generate_email(prospect, url, payment_url)
        except Exception as e:
            print(f"  Email gen error: {e}")
            continue

        # Generate WhatsApp message
        phone = prospect.get("phone_number", "")
        whatsapp_msg = ""
        whatsapp_link = ""
        if phone:
            from enrich import format_uk_mobile
            mobile_info = format_uk_mobile(phone)
            if mobile_info["is_mobile"]:
                print("  Generating WhatsApp message...")
                try:
                    whatsapp_msg = generate_whatsapp(prospect, url, payment_url)
                    whatsapp_link = make_whatsapp_link(mobile_info["e164"], whatsapp_msg)
                except Exception as e:
                    print(f"  WhatsApp gen error: {e}")
            else:
                mobile_info = format_uk_mobile("")
        else:
            mobile_info = format_uk_mobile("")

        record = {
            "slug": slug,
            "business_name": prospect.get("business_name", slug),
            "preview_url": url,
            "payment_url": payment_url,
            "contact_email": contact_email,
            "phone": phone,
            "mobile": mobile_info,
            "subject": email.get("subject", ""),
            "body_text": email.get("body_text", ""),
            "body_html": email.get("body_html", ""),
            "whatsapp_message": whatsapp_msg,
            "whatsapp_link": whatsapp_link,
            "whatsapp_status": "pending" if whatsapp_msg else "no_mobile",
            "status": "queued",  # queued | approved | sent | failed
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sent_at": None,
        }

        outreach.append(record)

        print(f"  Subject: {record['subject']}")
        print(f"  Preview: {url}")
        print(f"  Payment: {payment_url}")
        if contact_email:
            print(f"  Email: {contact_email}")
        else:
            print(f"  EMAIL NEEDED: find contact email for {record['business_name']}")
        if whatsapp_link:
            print(f"  WhatsApp: READY (click to send)")
        print()

    save_json(OUTREACH_LOG, outreach)
    print(f"Outreach log saved: {OUTREACH_LOG}")

    if preview_only:
        print("\n[PREVIEW MODE] No emails sent. Review outreach.json then run:")
        print("  python3 outreach.py --send <slug>")


def approve_and_send(slug: str) -> bool:
    """Approve and send outreach for a specific prospect."""
    outreach = load_json(OUTREACH_LOG)

    record = next((o for o in outreach if o["slug"] == slug), None)
    if not record:
        print(f"No outreach found for: {slug}")
        return False

    if not record.get("contact_email"):
        print(f"No contact email for {record['business_name']}.")
        print(f"Add email to outreach.json then retry.")
        return False

    if record["status"] == "sent":
        print(f"Already sent to {record['contact_email']}")
        return False

    print(f"Sending to: {record['contact_email']}")
    print(f"Subject: {record['subject']}")
    print(f"Preview: {record['preview_url']}")

    success = send_email(
        record["contact_email"],
        record["subject"],
        record["body_text"],
        record["body_html"],
    )

    if success:
        record["status"] = "sent"
        record["sent_at"] = datetime.now(timezone.utc).isoformat()
        print("  SENT")
    else:
        record["status"] = "failed"
        print("  FAILED")

    save_json(OUTREACH_LOG, outreach)
    return success


def show_status() -> None:
    outreach = load_json(OUTREACH_LOG)
    if not outreach:
        print("No outreach records.")
        return

    print(f"\n{'=' * 60}")
    print(f"  OUTREACH PIPELINE ({len(outreach)} prospects)")
    print(f"{'=' * 60}\n")

    by_status: dict[str, list] = {}
    for o in outreach:
        status = o.get("status", "?")
        by_status.setdefault(status, []).append(o)

    for status in ["sent", "approved", "queued", "failed"]:
        items = by_status.get(status, [])
        if not items:
            continue
        print(f"  {status.upper()} ({len(items)}):")
        for o in items:
            email = o.get("contact_email") or "NO EMAIL"
            print(f"    {o['business_name']} | {email} | {o['preview_url']}")
        print()

    wa_ready = [o for o in outreach if o.get("whatsapp_link")]
    if wa_ready:
        print(f"  WHATSAPP READY ({len(wa_ready)}):")
        for o in wa_ready:
            wa_status = o.get("whatsapp_status", "pending")
            print(f"    [{wa_status.upper()}] {o['business_name']} | {o.get('mobile', {}).get('e164', '?')}")
        print()
        print(f"  View messages + click-to-send links:")
        print(f"    python3 outreach.py --whatsapp")
        print()

    needs_email = [o for o in outreach if not o.get("contact_email")]
    if needs_email:
        print(f"  NEED EMAIL ({len(needs_email)}):")
        for o in needs_email:
            print(f"    {o['business_name']} | phone: {o.get('phone', '?')}")


def main() -> int:
    args = sys.argv[1:]

    print("=" * 60)
    print("  HERMES OUTREACH")
    print("=" * 60)

    if "--status" in args:
        show_status()
        return 0

    if "--whatsapp" in args:
        show_whatsapp_queue()
        return 0

    if "--send" in args:
        idx = args.index("--send")
        if idx + 1 >= len(args):
            print("Usage: python3 outreach.py --send <slug>")
            return 1
        slug = args[idx + 1]
        return 0 if approve_and_send(slug) else 1

    preview_only = "--preview" in args
    process_all(preview_only=preview_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
