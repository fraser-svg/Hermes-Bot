---
name: ad-verification
description: Verify whether a business actively runs paid ads on Meta, Google Ads, or LinkedIn. Use this skill whenever you need to confirm ad spend signals before pitching, qualify a lead by ad activity, check Meta Ad Library, scrape Google Ads Transparency Center, or check LinkedIn company ads tab. Required for retarget-prospector pipeline.
---

# Ad Verification

Three independent ad sources. Every result must cite evidence. Unknown beats fabricated.

## Sources

### 1. Meta Ad Library (API)

Official, free, no scraping. Use existing wrapper:
```python
import sys
sys.path.insert(0, '/Users/foxy/Hermes Bot')
from prospect_no_pixel import check_meta_ads
result = check_meta_ads(business_name, country='GB')
```

Returns `{has_ads, ad_count, sample_creatives, error}`. Requires `META_AD_LIBRARY_TOKEN` in `.env`. Without token → `result['error'] = 'no_token'`, mark `has_meta_ads: unknown`.

**Recency filter:** Only count ads with `delivery_dates.start` within last 90 days.

### 2. Google Ads Transparency Center (Playwright scrape)

No official API. URL pattern:
```
https://adstransparency.google.com/?region=GB&domain={domain}
```

Run bundled script:
```bash
python3 .claude/skills/ad-verification/scripts/check_google_ads_transparency.py "{domain}"
```

Returns JSON to stdout: `{has_google_ads, ad_count, sample_headlines, error}`. Non-zero exit → mark `unknown`.

### 3. LinkedIn Ads tab (Playwright scrape)

URL pattern: `{company_url}/posts/?feedView=ads`

Run bundled script:
```bash
python3 .claude/skills/ad-verification/scripts/check_linkedin_ads.py "{linkedin_url}"
```

Returns JSON: `{has_linkedin_ads, ad_count, sample_creatives, error}`. Requires logged-in cookie or returns `error: 'auth_required'` → mark `unknown`.

## 출력 정규화

각 source 결과를 다음 shape으로 통합:
```json
{
  "platform": "meta|google|linkedin",
  "has_ads": true|false|null,
  "ad_count": 3,
  "creatives": [
    {"headline": "...", "body": "...", "first_seen": "2026-03-15", "evidence": "url"}
  ],
  "error": null
}
```

`has_ads: null` 은 `unknown` 의미. `false` 와 구분 필수.

## Confidence 계산

**핵심 원칙:** `unknown` (has_ads == null) 은 "확인된 부재"가 아니라 **감사 공백** 이다. `false` 와 같은 가중치로 취급하지 마라. 스크래퍼 실패, 쿠키 만료, 셀렉터 드리프트가 모두 이 범주에 들어가며, 이 상태를 "광고 없음"으로 collapse 하면 lead intersection 계산이 손상된다.

```
confirmed_platforms = {p : p.has_ads == true}    # 진짜 true, non-stale
denied_platforms    = {p : p.has_ads == false}   # 스크래퍼가 확신 있게 false 를 반환
unknown_platforms   = {p : p.has_ads == null}    # error, auth_required, selector_failed, timeout 모두 여기

if len(confirmed_platforms) == 0:
    verdict = "rejected_no_confirmed_ads"   # unknown 만으로는 절대 qualified 불가
    confidence = 0.0
elif len(confirmed_platforms) >= 2:
    confidence = 0.9
elif len(confirmed_platforms) == 1 and len(unknown_platforms) == 0:
    confidence = 0.8
elif len(confirmed_platforms) == 1:
    confidence = 0.6      # 확인 1 + 미상 존재 → 증거 부족
```

결과 payload 에는 반드시 `confirmed_platforms`, `denied_platforms`, `unknown_platforms` 세 리스트를 분리 기록한다. qualifier 는 `confirmed_platforms` 만을 `active_platforms` 로 간주한다. `unknown_platforms` 는 `audit_gaps` 필드로 전달되어 보고서에 표시된다.

## 사용 시 주의

- **Cache 결과** 24시간. 같은 도메인을 반복 조회 시 `_workspace/retarget/_cache/` 에서 먼저 읽음.
- **Rate limit 준수.** Meta API: 200/hour. GATC scrape: 1 req/3s. LinkedIn: 1 req/5s, 세션당 50 max.
- **403/429 → wait 60s, retry once, then mark unknown.** Never burn through.
- **사람 검증 sample.** 매 실행마다 무작위 1개 lead 의 ad evidence URL을 보고서에 포함하여 사용자가 직접 확인 가능하게.
