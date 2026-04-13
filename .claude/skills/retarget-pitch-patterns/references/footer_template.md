# Email Footer Template — UK PECR + Companies Act + GDPR Art 14 Compliant

Append to every cold email. Override `cold_email.UNSUBSCRIBE_FOOTER` with this.

```
—
{sender_first_name} {sender_last_name}
{company_legal_name} | Company No. {company_number}
{registered_office_address}

You're receiving this because we found {business_name} listed publicly
on Google Maps as a {category} in {city}, and we offer marketing services
relevant to your business. We use legitimate interest as our lawful basis
under UK GDPR Art 6(1)(f).

Reply STOP and I'll remove you from all future contact within 24 hours.
Reply DELETE and I'll erase your record entirely.
Privacy notice: {privacy_url}
```

## Required substitutions (composer must fill all)

- `{sender_first_name}`, `{sender_last_name}` — match the body signature
- `{company_legal_name}` — exact Companies House name
- `{company_number}` — UK Companies House number (8 digits)
- `{registered_office_address}` — full address as filed
- `{business_name}`, `{category}`, `{city}` — pulled from candidate record
- `{privacy_url}` — URL to a hosted privacy notice covering source, purpose, retention, rights

## Why each line exists

| Line | Required by |
|---|---|
| Sender name + match to signature | Gmail spam policy, ICO sender-identity rules |
| Company legal name + number + address | UK Companies Act 2006 s.84 (business correspondence disclosure) |
| Source statement | GDPR Art 14(2)(f) — must state where data was obtained |
| Lawful basis statement | GDPR Art 14(1)(c) |
| STOP opt-out | PECR Reg 22(3)(b) |
| DELETE / erasure path | GDPR Art 17 (right to erasure) |
| Privacy notice link | GDPR Art 14(2) full notice |

## What MUST exist alongside

1. **A hosted privacy notice** at `{privacy_url}` covering: data source (Google Maps public listings + business websites), purposes (B2B outbound), retention (90 days unless reply), data controller, contact for SAR/erasure, right to lodge complaint with ICO.

2. **A documented Legitimate Interest Assessment (LIA)** at `compliance/lia_retargeting.md` — see template in `compliance/` directory.

3. **An IMAP STOP parser** that reads the sender mailbox daily, detects STOP/UNSUBSCRIBE/REMOVE/OPT OUT replies, and writes addresses + domains to `prospects/suppressed.json`.

4. **An NDR bounce parser** in the same IMAP reader that detects Mailer-Daemon NDRs and suppresses bounced addresses.

Without ALL FOUR of the above, the auto-send pipeline must remain disabled.
