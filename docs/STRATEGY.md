# UPDATED STRATEGY: BUILD FIRST, PITCH NEVER

## Old Way Dead

Old way: find problem, tell business about problem, hope they pay you to fix problem.

New way: find problem, fix problem, show business the fix, they pay you to keep it.

This change everything. Not incremental improvement. Fundamental shift in power dynamic.

---

## WHY THIS HIT DIFFERENT (Behavioural Psych)

**Reciprocity on steroids.** Cialdini say give first. Old version: give audit. New version: give the actual thing. Audit = information. Built website = tangible asset. Brain process tangible gift completely different to information gift. Obligation 10x stronger when you hold something real.

**Endowment effect.** Kahneman: people value thing more once they feel they own it. You show them "their" new website. Their name on it. Their services. Their photos. Brain already think "mine." Taking it away now feel like loss. Loss aversion kick in. They pay to not lose what they already mentally own.

**Status quo bias works FOR you now.** Normally status quo bias enemy. Business owner think "what I have is fine." But when you show them new site next to old site, new site BECOME the reference point. Old site now feel broken by comparison. You shifted the anchor.

**Zero cognitive load to say yes.** Sutherland: best marketing remove friction, not add persuasion. Old way: prospect must imagine what you could build. Imagination = effort. Effort = friction. New way: nothing to imagine. It there. Decision go from "should I hire someone to maybe build something" to "do I want this thing that already exist." Completely different question. Massively easier yes.

**Demonstration over claim.** Aristotle (actual one): proof by example strongest form of persuasion. Every agency on earth SAY they build good websites. You SHOW the website. Claim eliminated. Proof delivered. Conversation skip past trust building entirely.

---

## UPDATED HUNT FLOW

### Step 1: Identify (Automated)
`python3 prospect.py "category" "city"`

Searches Google Maps. Filters for no website. Ranks by review count and rating. Worst digital presence = hottest lead.

### Step 2: Build (Automated)
`python3 run.py "category" "city" --top 10`

Agent pulls from prospect's Google Maps data (name, address, phone, reviews, rating). Builds full website via Gemini 3.1 Pro using the YC startup design system. 15-point validation. Readability audit. Real Unsplash photos. Their name, their services, their actual Google reviews embedded.

Time per prospect: minutes. Cost per prospect: ~$0.15-0.42. This ratio what make model work.

### Step 3: Show (Personal - STAY HUMAN)

Cold outreach with the thing attached. Not "we can help." The message:

"Built you a new website. Here it is: [link]. No catch. Took me [X] minutes. Yours look like it costing you customers. This one would not. Want me to put it live?"

**Channel options:**
- Direct mail with QR code to their new site (nuclear option)
- Video message (Loom) showing their current site next to your build
- Personal email with screenshot + link

The BUILD automated. The REACH OUT stay personal.

### Step 4: Close

They seen the site. They want it. Conversation now about WHAT ELSE you can do.

"Site goes live this week. I handle hosting, updates, and your Google profile optimisation for X/month. Want ads running too? That Y/month and I handle everything."

---

## WHAT AGENT BUILDS PER PROSPECT

| Asset | Source | Tool |
|---|---|---|
| Website | GBP data, reviews | `generate.py` via Gemini 3.1 Pro |
| Prospect list | Google Maps | `prospect.py` via Places API |
| Batch builds | Prospect list | `run.py` (finds + builds in one shot) |

---

## VOLUME MATH

Old agency: pitch 50, close 3. Hours per pitch.
Our model: agent build 50 sites in a day. Send 50 personalised outreaches. Close 5-10.

50 sites at $0.15 each = $7.50 total build cost.
5 closes at 99/month = 495/month recurring.
ROI in month 1: 6,500%.

---

## KEY RISK AND FIX

**Risk:** Prospect take free site and ghost.

**Fix 1:** Site hosted on YOUR infrastructure. You control it.

**Fix 2:** Site is real and works but not connected to their domain. Not indexed. No analytics. The "turning it on" = the service.

**Fix 3:** Frame honest. "Built this because your current presence is losing you money. Wanted to show you what different looks like rather than just telling you."
