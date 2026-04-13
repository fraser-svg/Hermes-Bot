# Smoke Test Results — Retarget Prospector

Manual verification of detector output against live sites. Run before any
production prospecting campaign. Spot-check at least 3 randomly sampled
entries from `prospects/*-no-pixel.json` and record the results below.

## How to smoke test

For each sampled entry:

1. Open the business `website` in a browser with DevTools → Network.
2. Filter `facebook.com/tr` → should match if `facebook_pixel: true`.
3. Filter `googleads.g.doubleclick.net` or `googletagmanager.com` → match if `google_ads_remarketing: true`.
4. Filter `snap.licdn.com` → match if `linkedin_insight: true`.
5. Open `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=GB&q={business_name}&search_type=keyword_unordered` → compare with reported `has_meta_ads`.
6. Record discrepancies. Any mismatch means re-run `validation/eval_detectors.py` and identify which detector lied.

## Template

```
### YYYY-MM-DD — {category}-{city} run

| slug | site | reported | observed | match | note |
|------|------|----------|----------|-------|------|
| ... | ... | fb_pixel:false, meta_ads:true | fb_pixel:false confirmed, meta_ads:true (3 live) | ✓ | ok |
```

## Log

<!-- append run results below this line -->
