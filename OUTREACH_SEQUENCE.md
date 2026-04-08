# Outreach Sequence

Two emails. First one gets a reply. Second one sells.

---

## EMAIL 1

**Subject:** still open?

```
hey, was looking for a [category] in [city] and couldn't find you guys online

you still taking on work?

[first name]
```

No links. No pitch. No attachments. Looks like a potential customer.

---

## EMAIL 2 (sent after they reply)

Wait 10-30 minutes after their reply. Then send.

**Subject:** re: still open?

```
oh nice, glad you're still going

Honestly wasn't sure, couldn't find you anywhere online so just assumed you'd shut down or something

Had a nosy at your online stuff while i was at it

- no website. anyone searching [category] in [city] can't find you. looks like you're closed to them, they just call whoever shows up first

- not on google maps for "[category] [city]". checked this morning, [competitor] and [competitor 2] are both there. you're not

- google profile's a bit bare. no photos and none of the reviews have been replied to. google pushes those ones down

- no way for anyone to reach you after hours. if someone needs a [category] at 9pm and you don't pick up they just ring the next one

most of that's pretty quick to sort

i already had a go at the first one

[SCREENSHOT]

[preview URL]

used your actual reviews and your number and that

if you want it it's yours, 50 quid a month, i sort the hosting and keep it updated. you can grab it here: [stripe link]

or if you want a proper chat about the rest of it grab 15 mins here and i'll walk you through it: [calendly link]

either way no worries

[first name]
```

---

## FOLLOW-UPS

No reply to Email 1 after 4 days:

```
just checking this got through?

[first name]
```

No reply to Email 2 after 3 days:

```
did you get a chance to look at the site?

[first name]
```

Day 7, still nothing:

```
going to take the preview down friday, just let me know either way

[first name]
```

After day 7 silence: mark cold, archive, move on.

---

## EDGE CASE REPLIES

"no we closed down"
```
ah sorry to hear that, all the best

[first name]
```

"who is this?"
```
just a guy who builds websites for local businesses. was genuinely 
looking for a [category] in [city] and couldn't find you

[first name]
```

"how much?"
```
29 a month for the website, hosted and maintained

i actually already built a demo for you, want to see it?

[first name]
```

"interested but not sure"
-> send Email 2 if not already sent, then follow up in 2 days

---

## TONE RULES

Write like you're texting a builder from your phone.

- lowercase everything except names
- "i" not "I"
- contractions always (i'm, you're, it's, they'll, that's)
- short lines, one thought each
- incomplete sentences fine
- british casual ("had a nosy", "29 quid", "you guys", "and that", "no worries")
- sign off with first name only, nothing else

never use:
- capital I
- em dashes
- emojis
- exclamation marks
- "I hope this finds you well"
- "I wanted to reach out"
- "please don't hesitate"
- "best regards" or "kind regards"
- any word that sounds like marketing

---

## REPLY DETECTION

Hermes monitors for replies via SendGrid Inbound Parse or Gmail API.

On reply to Email 1:
1. Match sender to lead in outreach_log
2. Filter out-of-office (keywords: "away", "holiday", "automated")
3. If genuine reply: wait 10-30 min, send Email 2
4. Log reply content + timestamp

---

## PERSONALISATION VARIABLES

| Variable | Source |
|----------|--------|
| `[first name]` | your name (Fraser or whatever you set) |
| `[category]` | Google listing category |
| `[city]` | lead location |
| `[competitor]` | top Maps result for "[category] [city]" |
| `[competitor 2]` | second Maps result |
| `[preview URL]` | Netlify deploy URL |
| `[SCREENSHOT]` | Playwright screenshot of built site |
| `[stripe link]` | pre-filled Stripe payment link |
| `[calendly link]` | booking link |

If lead's first name unavailable: skip greeting, start with "hey,"

---

## AUDIT CHECKS (Hermes runs before Email 2)

| Check | Method | Include if |
|-------|--------|-----------|
| Website | DNS + HTTP check | dead, missing, or blank |
| Google Maps ranking | search "[category] [city]" | not in top 5 |
| Google profile photos | Places API | < 3 photos |
| Review reply rate | Places API | < 50% replied |
| Directory listings | web search (Checkatrade, Yell, TrustATrader) | not found |
| After-hours contact | site check | no form, no chat |

Pick 3-4 worst. Don't list everything. Lead with whatever costs them money today.

---

## HERMES INSTRUCTION

```
outreach uses two-touch sequence.

email 1: looks like a potential customer asking if they're still open.
short. no links. no pitch.

wait for reply. monitor via SendGrid Inbound Parse.

on reply: wait 10-30 min, then send email 2.

email 2: mirror their reply, list 3-4 audit findings (worst first), 
show the built site with screenshot + preview URL, 
give two options: pay link (stripe) or book a call (calendly).

follow up on day 4 if no reply to email 1.
follow up on day 3 and day 7 if no reply to email 2.
after day 7: mark cold, archive.

tone: casual, lowercase, british, no emojis, no em dashes, 
no exclamation marks, no marketing language. 
reads like texting a builder from your phone.

log everything in outreach_log:
email_1_sent, email_1_reply, email_2_sent, 
cta_clicked (pay/call/none), outcome
```

---

## CALL PREP (when someone books via Calendly)

Hermes sends to Telegram 30 min before the call:

```
CALL BRIEF: [business name]
[date] [time]

contact: [name] / [phone] / [email]

situation:
- [X] google reviews, avg [rating]
- competitors outranking them: [names]
- est. monthly searches "[category] [city]": [X]

issues:
1. [issue]
2. [issue]
3. [issue]

demo site: [preview URL]

packages:
starter 29/month: website, hosting, updates
growth 99/month: + google profile optimisation, review management
full 299/month: + content, ads, monthly reporting

opener: "did you get a chance to look at the site?"
close: "most people start with the site and add on from there"
```
