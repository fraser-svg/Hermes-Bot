#!/usr/bin/env python3
"""Enrich prospects with email addresses and formatted mobile numbers.

Sources for emails (waterfall — tries each until found):
  1. Business website (if they have one) — scrape mailto: and email patterns
  2. Facebook page — search and extract public email
  3. Yell.com listing — scrape contact details
  4. Google search "[business name] [city] email" — extract from snippets

Mobiles: formats existing phone numbers for WhatsApp/SMS.

Usage:
    python3 enrich.py                     # enrich all outreach queue
    python3 enrich.py --prospect-file prospects/plumber-dunfermline.json
    python3 enrich.py --status            # show enrichment coverage

Requires GOOGLE_MAPS_API in .env (for Places lookup if needed)
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
PROSPECTS_DIR = BASE_DIR / "prospects"
OUTREACH_LOG = PROSPECTS_DIR / "outreach.json"

# Email regex — catches most valid emails in HTML/text
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

# Ignore these email patterns (generic, not the business)
JUNK_EMAILS = {
    "example.com", "email.com", "youremail.com", "yourcompany.com",
    "sentry.io", "wixpress.com", "googleapis.com", "w3.org",
    "schema.org", "gravatar.com", "wordpress.org", "jquery.com",
    "google.com", "facebook.com", "twitter.com", "instagram.com",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


def load_json(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def fetch_html(url: str, timeout: int = 12) -> str:
    """Fetch page HTML. Returns empty string on failure."""
    try:
        req = Request(url, headers=HEADERS, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return ""
            return resp.read(500_000).decode("utf-8", errors="ignore")
    except (HTTPError, URLError, Exception):
        return ""


def extract_emails(html: str) -> list[str]:
    """Pull email addresses from HTML, filter junk."""
    if not html:
        return []

    raw = EMAIL_RE.findall(html)
    seen: set[str] = set()
    results: list[str] = []

    for email in raw:
        email = email.lower().strip(".")
        domain = email.split("@")[1] if "@" in email else ""

        if domain in JUNK_EMAILS:
            continue
        if email.endswith(".png") or email.endswith(".jpg"):
            continue
        if len(email) > 60:
            continue
        if email not in seen:
            seen.add(email)
            results.append(email)

    return results


# ---------------------------------------------------------------------------
# Email source 1: Business website
# ---------------------------------------------------------------------------

def emails_from_website(website_url: str) -> list[str]:
    """Scrape email from business website homepage + /contact page."""
    if not website_url:
        return []

    emails: list[str] = []
    html = fetch_html(website_url)
    emails.extend(extract_emails(html))

    # Try /contact and /about pages
    parsed = urlparse(website_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in ["/contact", "/contact-us", "/about", "/about-us"]:
        page_html = fetch_html(f"{base}{path}")
        emails.extend(extract_emails(page_html))

    return list(dict.fromkeys(emails))  # dedupe, preserve order


# ---------------------------------------------------------------------------
# Email source 2: Yell.com
# ---------------------------------------------------------------------------

def emails_from_yell(business_name: str, city: str) -> list[str]:
    """Search Yell.com for business listing and extract email."""
    query = quote(f"{business_name} {city}")
    url = f"https://www.yell.com/ucs/UcsSearchAction.do?keywords={query}&location={quote(city)}"

    html = fetch_html(url)
    if not html:
        return []

    # Look for email in results
    return extract_emails(html)


# ---------------------------------------------------------------------------
# Email source 3: Google search snippets
# ---------------------------------------------------------------------------

def emails_from_google_search(business_name: str, city: str) -> list[str]:
    """Search Google for "[business] [city] email contact" and extract emails from snippets.

    Uses Google's HTML search page — no API key needed.
    Rate-limited: use sparingly.
    """
    query = quote(f"{business_name} {city} email contact")
    url = f"https://www.google.com/search?q={query}&num=5&hl=en"

    html = fetch_html(url)
    if not html:
        return []

    return extract_emails(html)


# ---------------------------------------------------------------------------
# Phone number formatting
# ---------------------------------------------------------------------------

def format_uk_mobile(phone: str) -> dict:
    """Format UK phone number for WhatsApp/SMS.

    Returns dict with:
      - raw: original
      - e164: +44 format (for APIs)
      - is_mobile: bool
      - whatsapp_link: wa.me link
    """
    if not phone:
        return {"raw": "", "e164": "", "is_mobile": False, "whatsapp_link": ""}

    # Strip spaces, dashes, parens
    digits = re.sub(r"[^\d+]", "", phone)

    # Convert to E.164
    if digits.startswith("0"):
        e164 = "+44" + digits[1:]
    elif digits.startswith("44"):
        e164 = "+" + digits
    elif digits.startswith("+44"):
        e164 = digits
    else:
        e164 = digits  # unknown format, keep as-is

    # UK mobile numbers start with 07 (or +447)
    is_mobile = (
        digits.startswith("07")
        or digits.startswith("447")
        or digits.startswith("+447")
    )

    # WhatsApp link (strip the +)
    wa_number = e164.lstrip("+")
    whatsapp_link = f"https://wa.me/{wa_number}" if is_mobile else ""

    return {
        "raw": phone,
        "e164": e164,
        "is_mobile": is_mobile,
        "whatsapp_link": whatsapp_link,
    }


# ---------------------------------------------------------------------------
# Enrichment pipeline
# ---------------------------------------------------------------------------

def enrich_one(record: dict) -> dict:
    """Enrich a single prospect/outreach record with email + formatted mobile."""
    name = record.get("business_name", "")
    city = record.get("city", "")
    phone = record.get("phone", "") or record.get("phone_number", "")
    website = record.get("website_url", "")

    print(f"  [{name}]")

    # --- Email waterfall ---
    emails: list[str] = []
    source = ""

    if not record.get("contact_email"):
        # Source 1: Website
        if website:
            print(f"    Checking website: {website}")
            emails = emails_from_website(website)
            if emails:
                source = "website"

        # Source 2: Yell.com
        if not emails and name and city:
            print(f"    Checking Yell.com...")
            emails = emails_from_yell(name, city)
            if emails:
                source = "yell"

        # Source 3: Google search (use sparingly)
        if not emails and name and city:
            print(f"    Checking Google search...")
            emails = emails_from_google_search(name, city)
            if emails:
                source = "google_search"

        if emails:
            record["contact_email"] = emails[0]
            record["email_source"] = source
            record["all_emails_found"] = emails[:5]
            print(f"    FOUND: {emails[0]} (via {source})")
        else:
            print(f"    No email found")
    else:
        print(f"    Email exists: {record['contact_email']}")

    # --- Mobile formatting ---
    if phone:
        mobile_info = format_uk_mobile(phone)
        record["mobile"] = mobile_info
        if mobile_info["is_mobile"]:
            print(f"    Mobile: {mobile_info['e164']} (WhatsApp ready)")
        else:
            print(f"    Landline: {mobile_info['e164']} (SMS/WhatsApp not available)")
    else:
        record["mobile"] = format_uk_mobile("")
        print(f"    No phone number")

    return record


def enrich_outreach_queue() -> None:
    """Enrich all records in outreach.json."""
    outreach = load_json(OUTREACH_LOG)
    if not outreach:
        print("No outreach records. Run outreach.py first.")
        return

    print(f"\nEnriching {len(outreach)} outreach records...\n")

    for record in outreach:
        # Pull city from prospect data if missing
        if not record.get("city"):
            from outreach import find_prospect_data
            prospect = find_prospect_data(record.get("slug", ""))
            if prospect:
                record["city"] = prospect.get("city", "")
                record["website_url"] = prospect.get("website_url", "")

        enrich_one(record)
        print()

    save_json(OUTREACH_LOG, outreach)
    print(f"Updated: {OUTREACH_LOG}")


def enrich_prospect_file(path: Path) -> None:
    """Enrich all records in a prospect JSON file."""
    data = load_json(path)
    if not data:
        print(f"No records in {path}")
        return

    print(f"\nEnriching {len(data)} prospects from {path.name}...\n")

    for record in data:
        enrich_one(record)
        print()

    save_json(path, data)
    print(f"Updated: {path}")


def show_status() -> None:
    """Show enrichment coverage across outreach queue."""
    outreach = load_json(OUTREACH_LOG)
    if not outreach:
        print("No outreach records.")
        return

    has_email = sum(1 for o in outreach if o.get("contact_email"))
    has_mobile = sum(1 for o in outreach if o.get("mobile", {}).get("is_mobile"))
    has_phone = sum(1 for o in outreach if o.get("mobile", {}).get("e164"))
    total = len(outreach)

    print(f"\n{'=' * 60}")
    print(f"  ENRICHMENT STATUS ({total} prospects)")
    print(f"{'=' * 60}\n")
    print(f"  Email found:     {has_email}/{total}")
    print(f"  Mobile (WhatsApp): {has_mobile}/{total}")
    print(f"  Any phone:       {has_phone}/{total}")
    print()

    for o in outreach:
        email = o.get("contact_email") or "NO EMAIL"
        mobile = o.get("mobile", {})
        phone_status = "MOBILE" if mobile.get("is_mobile") else ("LANDLINE" if mobile.get("e164") else "NO PHONE")
        print(f"  {o.get('business_name', '?')}")
        print(f"    Email: {email}")
        print(f"    Phone: {mobile.get('e164', '?')} ({phone_status})")
        if mobile.get("whatsapp_link"):
            print(f"    WhatsApp: {mobile['whatsapp_link']}")
        print()


def main() -> int:
    args = sys.argv[1:]

    print("=" * 60)
    print("  HERMES ENRICHMENT")
    print("=" * 60)

    if "--status" in args:
        show_status()
        return 0

    if "--prospect-file" in args:
        idx = args.index("--prospect-file")
        if idx + 1 >= len(args):
            print("Usage: python3 enrich.py --prospect-file <path>")
            return 1
        path = Path(args[idx + 1])
        if not path.exists():
            path = PROSPECTS_DIR / args[idx + 1]
        if not path.exists():
            print(f"File not found: {args[idx + 1]}")
            return 1
        enrich_prospect_file(path)
        return 0

    enrich_outreach_queue()
    return 0


if __name__ == "__main__":
    sys.exit(main())
