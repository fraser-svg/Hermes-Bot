# Purchase → Deploy Pipeline

Zero friction. Prospect clicks, pays, site goes live. No human required.

---

## Full Flow

```
Prospect receives email
        ↓
Sees their site (preview.netlify.app)
        ↓
Clicks "Get this site — £29/month" button
        ↓
Stripe Checkout (pre-filled with their business name)
        ↓
Pays
        ↓
Stripe fires webhook
        ↓
Hermes receives trigger
        ↓
Hermes:
  - Promotes preview → production deploy
  - Attaches custom domain (or assigns subdomain)
  - Enables contact form
  - Sends welcome email with live URL + next steps
        ↓
Site live within 2 minutes of payment
```

---

## Stack

| Component | Tool | Cost |
|-----------|------|------|
| Payments + subscriptions | Stripe | 1.5% + 20p per txn |
| Preview hosting | Netlify (free tier) | £0 |
| Production hosting | Netlify Pro or Vercel | ~£15/month flat (covers all clients) |
| Domain (optional) | Namecheap API or Cloudflare | ~£8/year per domain |
| Webhook bridge | Make.com or direct VPS endpoint | £0–£9/month |
| Email delivery | SendGrid (already configured) | £0 for low volume |

Margin at £29/month per client: healthy from client 2 onward.

---

## Stripe Setup

### Step 1 — Create Product

In Stripe dashboard:
- Product: "Local Business Website"
- Price: £29/month recurring
- Also create: £49 and £99 tiers for upsell

### Step 2 — Payment Link

Create Stripe Payment Link:
- Attach to £29/month product
- Enable: collect name, email, phone
- Add custom field: "Business name" (pre-fill via URL param)
- Success URL: `youragency.com/welcome?session={CHECKOUT_SESSION_ID}`

Pre-fill link for each prospect:
```
https://buy.stripe.com/yourlink?prefilled_custom_fields[business_name]=[Business Name]
```

Hermes generates this per-lead. Drops into email template automatically.

### Step 3 — Webhook

Stripe → your VPS endpoint:
```
POST https://yourvps.com/webhooks/stripe
```

Events to listen for:
- `checkout.session.completed` → trigger deploy
- `invoice.payment_failed` → notify + pause site
- `customer.subscription.deleted` → take site down

---

## Webhook Receiver (on VPS)

Simple Python Flask endpoint. Hermes can create this as a skill.

```python
# webhook_receiver.py
from flask import Flask, request
import stripe
import subprocess

app = Flask(__name__)
stripe.api_key = "sk_live_..."
webhook_secret = "whsec_..."

@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        business_name = session['custom_fields'][0]['text']['value']
        customer_email = session['customer_details']['email']
        
        # Trigger Hermes via Telegram or direct call
        notify_hermes(f"PAYMENT_CONFIRMED|{business_name}|{customer_email}")
    
    if event['type'] == 'customer.subscription.deleted':
        customer_email = event['data']['object']['customer']
        notify_hermes(f"SUBSCRIPTION_CANCELLED|{customer_email}")
    
    return '', 200

def notify_hermes(message):
    # Send message to Hermes via Telegram bot API
    import requests
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": HERMES_CHAT_ID, "text": f"🔔 TRIGGER: {message}"}
    )
```

Or simpler: use **Make.com** (Integromat):
```
Stripe trigger → Make scenario → Telegram message to Hermes
```
No code. 5 minutes to set up. £9/month.

---

## Hermes Deploy Skill

When Hermes receives `PAYMENT_CONFIRMED|[business name]|[email]`:

```
1. Look up business name in leads_database
2. Find preview Netlify site URL
3. Call Netlify API → promote to production
4. If custom domain available → attach via Netlify API
5. Enable contact form (Netlify Forms or Formspree)
6. Update built_sites collection: status → live
7. Update leads_database: status → converted
8. Send welcome email via SendGrid
9. Log to conversion_log
```

Netlify API calls:
```bash
# Promote deploy to production
curl -X POST "https://api.netlify.com/api/v1/sites/{site_id}/deploys/{deploy_id}/restore" \
  -H "Authorization: Bearer {NETLIFY_TOKEN}"

# Add custom domain
curl -X POST "https://api.netlify.com/api/v1/sites/{site_id}/domain_aliases" \
  -H "Authorization: Bearer {NETLIFY_TOKEN}" \
  -d '{"domain": "businessname.youragency.com"}'
```

---

## Domain Strategy

### Option A — Agency subdomain (recommended for Phase 1)
```
edinburgh-sparks-electrical.youragency.com
```
- Zero extra cost
- Instant (DNS wildcard already set)
- Client doesn't need to do anything
- Looks professional

### Option B — Client's own domain (upsell)
```
edinburghsparks.co.uk
```
- Register via Namecheap API (~£8/year)
- Point to Netlify via DNS
- Add as upsell: "Get your own domain — £8/year"
- Client gives us domain or we register it for them

**Phase 1: use Option A. Offer Option B as upgrade.**

Wildcard DNS setup (one-time):
```
*.youragency.com → Netlify load balancer IP
```

---

## Welcome Email (Auto-sent on Payment)

```
Subject: Your website is live, [First Name] 🎉

Hi [First Name],

Your site is live:
→ [live URL]

Here's what's included:
✓ Mobile-friendly design
✓ Your reviews displayed
✓ Contact form (replies go to [their email])
✓ Google-ready (local search optimised)

What happens next:
- We'll check in monthly with a short report
- Reply to this email anytime for changes
- Want your own domain? Reply "domain" and we'll sort it

Your subscription: £29/month — cancel anytime, no questions.

[Your name]
[Agency]
```

---

## Subscription Management

| Event | Hermes Action |
|-------|--------------|
| Payment success | Deploy + send welcome email |
| Payment failed | Email client, retry 3x, then pause site + notify |
| Subscription cancelled | Take site down, send offboarding email, log |
| Upgrade (£49/£99) | Unlock features, log upsell in conversion_log |

Pausing = redirect to "This site is temporarily unavailable" page.
Taking down = delete deploy, keep data in case they return.

---

## Email CTA Button (in outreach email)

Hermes generates this per lead:

```html
<a href="https://buy.stripe.com/yourlink?prefilled_custom_fields[business_name]=Edinburgh+Sparks+Electrical"
   style="background:#000;color:#fff;padding:14px 28px;border-radius:6px;
          text-decoration:none;font-weight:bold;display:inline-block;">
  Get this site — £29/month →
</a>
```

One click → Stripe → paid → live. No calls. No back-and-forth.

---

## Hermes Instruction (Paste to Update Agent)

```
Purchase + deploy pipeline active.

When lead moves to outreach stage:
1. Generate Stripe payment link with business name pre-filled
2. Embed in outreach email as primary CTA button
3. Text: "Get this site — £[price]/month →"

When PAYMENT_CONFIRMED trigger received:
1. Look up lead in leads_database by business name
2. Promote Netlify preview → production
3. Assign subdomain: [slug].youragency.com
4. Enable contact form
5. Send welcome email via SendGrid template
6. Update built_sites: status = live
7. Update leads_database: status = converted
8. Log to conversion_log with: date, amount, business name, live URL

When SUBSCRIPTION_CANCELLED received:
1. Pause site (redirect to maintenance page)
2. Send offboarding email
3. Update records

All of this runs without human input after initial payment confirmation.
```

---

## Phase 1 Setup Checklist

- [ ] Stripe account created + bank connected
- [ ] Product + Payment Link created (£29/month)
- [ ] Stripe webhook endpoint live on VPS (or Make.com scenario)
- [ ] Netlify API token stored in Hermes memory
- [ ] Wildcard DNS set (`*.youragency.com → Netlify`)
- [ ] SendGrid welcome email template created
- [ ] Hermes deploy skill created + tested on dummy lead
- [ ] End-to-end test: fake payment → confirm site goes live

---

*Prospect clicks. Pays. Site live in 2 minutes. Nobody wakes up.*
