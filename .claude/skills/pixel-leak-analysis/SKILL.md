---
name: pixel-leak-analysis
description: Maps active ad platforms to required retargeting pixels and computes leak severity. Use this skill whenever you need to determine whether a missing pixel actually wastes ad spend, quantify a retargeting leak, or pick the highest-value leak to pitch.
---

# Pixel Leak Analysis

A "leak" exists only when an ad platform is **active** AND its corresponding retargeting pixel is **missing**. Missing pixels for platforms with no ads = no leak.

## Platform → Required Pixel

| Ad platform | Required for retargeting | Detection key (from pixel-auditor) |
|-------------|--------------------------|-------------------------------------|
| Meta (Facebook/Instagram) | Facebook Pixel | `facebook_pixel` |
| Google Ads (Search, Display, YouTube) | Google Ads remarketing tag (`AW-XXX`) | `google_ads_remarketing` |
| LinkedIn Ads | LinkedIn Insight Tag | `linkedin_insight` |
| TikTok Ads | TikTok Pixel | `tiktok_pixel` |
| Reddit Ads | Reddit Pixel | (not currently audited — note as gap) |

## Leak Severity

```
leak_surface = active_platforms ∩ missing_pixels

severity = "critical"   if "meta" in leak_surface (highest ROAS impact)
         = "high"       if "google" in leak_surface
         = "medium"     if "linkedin" in leak_surface
         = "low"        if only "tiktok" in leak_surface
```

Multi-platform leaks compound — pitch as "you're losing X% of clicks across N platforms".

## Quantification Frames (for outreach copy)

Use these **only**, do not invent numbers. Cite source if asked.

| Frame | Use when |
|-------|----------|
| "97% of first-time visitors leave without converting" (Baymard / industry) | Generic CTR loss |
| "Retargeted users are 70% more likely to convert" (Criteo) | Persuading on retargeting value |
| "Without a pixel, your audience starts from zero every campaign" | Cold start framing |
| "FB Pixel data takes 90 days of traffic to mature — every day you wait costs you data, not just clicks" | Urgency framing |

## Edge Cases

- **GTM present, no individual pixels:** Could mean pixels are loaded server-side OR truly missing. Mark as `data_quality_uncertain`. Composer should soften pitch ("It looks like you may be running pixels via GTM — happy to take a look").
- **GA4 present, no Google Ads tag:** Conversion data exists but cannot be used for retargeting. Pitch angle: "you have the data, you're just not using it".
- **Pixel ID present but stale (last load >180 days):** out of scope for v1.

## Anti-Patterns

- Do not pitch retargeting to a business with **no confirmed ads**. They have no audience to retarget.
- Do not pitch FB Pixel install to a Meta-only ads spender who already has it (qualifier should reject — defense in depth).
- Do not quantify with made-up percentages. Stick to the frames above.
