---
name: whatsapp-outreach
description: Format and constraints for WhatsApp cold outreach to local service businesses. Use whenever drafting WhatsApp messages for prospects, deciding whether WhatsApp is appropriate for a given business, or formatting WhatsApp queue entries.
---

# WhatsApp Outreach

WhatsApp converts higher than email for trades but burns trust faster if abused. Stricter rules than email.

## When WhatsApp Is Appropriate

**Use WhatsApp if all true:**
- Prospect record has `phone_number` formattable as E.164
- Business category in receptive list (below)
- Phone is a mobile, not a landline (best-effort: numbers starting with `+447` UK, `+1{2-9}xx` US mobile prefixes, etc.)
- Business is in a region where WhatsApp is the dominant business messaging app

**Receptive categories (high WhatsApp usage):**
- Electrician, plumber, roofer, HVAC, locksmith, pest control
- Cleaner, painter, mover, landscaper, handyman
- Salon, barber, mobile mechanic, MOT garage
- Personal trainer, photographer, event vendor

**Non-receptive (skip WhatsApp, use email/LinkedIn):**
- B2B SaaS, enterprise services, professional services (law, accounting)
- Healthcare practitioners (regulated)
- Anything where the buyer is corporate procurement

**Region heuristic:**
- UK, Ireland, India, Brazil, Spain, Italy, MENA, most of LATAM → high WhatsApp adoption
- US, Canada, Australia, Northern Europe → mixed, prefer email
- Default to email if region unknown

## Format Rules

- **First message ≤ 160 chars.** Hard limit.
- **No links in first message.** Triggers WhatsApp spam flags. Save link for reply.
- **No formatting.** No bold, italics, emojis. Plain text only.
- **No image/PDF attachment.**
- **Identify yourself in first 5 words.** They have no idea who you are.
- **One question, one CTA.** Not both.

## Template

```
Hi {first_name} — Fraser here, saw your {city}
{category} {ad_platform} ad. Noticed your site's
missing the {pixel_name} pixel which makes
retargeting impossible. Worth a quick chat?
```

Replace placeholders. Keep under 160 chars after substitution.

## Anti-Patterns

- ❌ "Hi! Hope you're well 😊" — instant block
- ❌ "Check out our website: https://..." — link in first message
- ❌ "We help businesses like yours grow 3x faster" — generic, salesy
- ❌ Voice notes — never in cold outreach
- ❌ Multiple messages in a row before reply — appears desperate

## v1 Constraint

**Do not auto-send WhatsApp in v1.** Hermes Bot has no WhatsApp send infrastructure. Compose the message into `_workspace/retarget/whatsapp_queue.md` for manual send via the user's phone.

Queue file format:
```markdown
## {slug}
**Phone:** +447712345678
**Business:** {business_name}
**Message:** {one-line text}
**Context:** {leak_summary}
**Send link:** https://wa.me/447712345678?text={url-encoded}
---
```

The `wa.me` link lets the user tap and send from their phone in one motion.

## Compliance

- UK PECR / GDPR: B2B WhatsApp to a business mobile number for a relevant service offer is generally permitted, but include opt-out path in any reply ("reply STOP and I won't message again").
- Never message the same number twice without a reply.
- Honor STOP / OPT OUT / UNSUBSCRIBE — append to `prospects/whatsapp_suppressed.json`.
