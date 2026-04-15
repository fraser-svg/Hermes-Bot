# Legitimate Interest Assessment — Retargeting Outbound Campaign

**Data Controller:** {your company legal name + Companies House number}
**Date of assessment:** 2026-04-13
**Reviewer:** {your name, role}
**Next review:** 2026-10-13 (6 months)

This document satisfies the ICO requirement to perform and record a Legitimate Interest Assessment (LIA) before relying on UK GDPR Art 6(1)(f) as the lawful basis for direct B2B marketing outreach.

---

## Part 1 — Purpose Test (is the interest legitimate?)

**Stated purpose:** Send personalised cold outbound (email + drafted WhatsApp/LinkedIn DM) to UK limited companies that have publicly-discoverable signals of running paid digital ads but lack the corresponding retargeting pixel infrastructure, in order to offer ad management consulting services.

**Is the purpose legitimate?** Yes. Direct B2B marketing of relevant services to a corporate audience is a recognised legitimate interest under ICO's Direct Marketing Code. Recital 47 of UK GDPR explicitly recognises direct marketing as a legitimate interest.

**Is the purpose necessary for the interest?** Yes. There is no comparable opt-in audience available; the prospects must be discovered via public signals.

---

## Part 2 — Necessity Test (is processing necessary?)

**Could we achieve the same result with less data?** The minimum data set required is: business name, website URL, contact name, contact email, public ad-platform activity, public pixel-presence audit. We do not collect or process: payment data, employee records, special-category data, or anything beyond what is needed to personalise the relevance of the outreach.

**Are we processing only what is needed?** Yes — see `_workspace/retarget/candidates.json` schema for the exact fields stored.

**Is the processing proportionate?** Yes — single outreach attempt + 2 follow-ups maximum, capped at 90-day retention if no reply.

---

## Part 3 — Balancing Test (does our interest override the recipient's rights?)

### Reasonable expectations

- **Limited companies (Ltd / LLP / PLC):** A business actively running paid ads in the public Meta Ad Library and Google Ads Transparency Center can reasonably expect to be approached by service providers offering relevant marketing services. **Reasonable expectation: yes.**
- **Sole traders / partnerships / individuals:** Treated as individual subscribers under PECR Reg 22 — they require prior consent or soft opt-in. **EXCLUDED from this LIA.** The pipeline must filter out non-corporate entities via Companies House lookup before sending.

### Likely impact on the recipient

- Recipient receives one cold email with clear opt-out (STOP) and erasure (DELETE) options, plus a privacy notice link.
- Total messages without reply: maximum 3 over 14 days, then suppression.
- No special-category data processed.
- Suppression is honoured immediately and persistently across runs and categories.
- **Likely impact: low.**

### Safeguards

1. Limited companies only (Companies House verification gate).
2. National chain blocklist (chains have agency relationships and are not the target).
3. Regulated-profession blocklist (solicitors, doctors, financial advisers, charities).
4. PECR-compliant footer with sender legal name, company number, registered office, opt-out, erasure path, privacy notice link.
5. IMAP STOP-reply parser running daily.
6. NDR bounce parser running daily.
7. SPF/DKIM/DMARC alignment verified before any send.
8. Per-run send cap (max 20 sends per execution).
9. Hard suppression list at both address and domain level.
10. 90-day retention policy on `_workspace/retarget/` and `prospects/`.
11. SAR/erasure command available: `python3 cold_email.py --erase {email}`.

### Conclusion

The legitimate interest in identifying and contacting limited companies with relevant marketing infrastructure gaps is not overridden by the rights and freedoms of those companies, **provided all safeguards above are operational at the time of sending**. The pipeline must perform a pre-flight check that all 11 safeguards are in place; if any are missing, sending must be disabled.

---

## Compliance Gates (must pass before any auto-send run)

- [ ] Companies House lookup integrated and tested
- [ ] Chain blocklist applied
- [ ] Regulated-profession blocklist applied
- [ ] Footer template populated with sender details
- [ ] Privacy notice live at the URL referenced in footer
- [ ] IMAP STOP parser running and tested
- [ ] NDR bounce parser running and tested
- [ ] SPF/DKIM/DMARC alignment verified for sending domain
- [ ] Per-run send cap = 20 enforced in orchestrator
- [ ] Suppression list checked at both address and domain level
- [ ] 90-day retention cron configured
- [ ] Erasure command tested

If any box is unchecked, **AUTO-SEND IS DISABLED**.

---

## Review schedule

This LIA must be reviewed every 6 months OR after any change to:
- The data sources used
- The personalisation methods
- The send volume
- The recipient categories

Last review: 2026-04-13
Next review: 2026-10-13
