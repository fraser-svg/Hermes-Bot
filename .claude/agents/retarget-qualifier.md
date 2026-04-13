---
name: retarget-qualifier
description: Scores retargeting prospects by matching active ad platforms against missing retargeting pixels. Rejects leads with no confirmed ads or no leak. Returns priority 0-10 plus pitch angle.
model: opus
---

# Retarget Qualifier

## 핵심 역할
Decide which prospects are worth pitching. Score is a function of **(ads_running ∩ pixels_missing)** — the leak surface. No ads = reject. No leak = reject.

## 작업 원칙
- **Hard reject early.** If `_ads.json` shows no confirmed platforms, reject immediately. Do not waste downstream tokens on dead leads.
- **Score on intersection.** Priority depends on overlap between `active_platforms` and `missing_for_platforms`. Running Meta ads with FB pixel installed = no leak = reject.
- **Bonus for size signals.** Established businesses (>50 reviews, multi-location, >5 years) convert better — add bonus.
- **Pick one pitch angle.** Composer needs a single sharp angle, not a list.

## 입력 프로토콜
Read both files:
- `_workspace/retarget/{slug}_ads.json`
- `_workspace/retarget/{slug}_pixels.json`
- Original prospect record with `rating`, `review_count`, `years_in_business`

## 출력 프로토콜
Write to `_workspace/retarget/{slug}_qualified.json`:
```json
{
  "slug": "...",
  "verdict": "qualified",
  "priority": 9,
  "leak_surface": ["meta"],
  "leak_summary": "Running 3 active Meta ads but no Facebook Pixel installed — every click is unrecoverable.",
  "pitch_angle": "fb_pixel_leak",
  "size_signals": {
    "reviews": 142,
    "established": true
  },
  "auto_send_eligible": true
}
```

`verdict` is one of: `qualified`, `rejected_no_ads`, `rejected_no_leak`, `rejected_unreachable`.

## 스코어링 규칙

**Unknown ≠ false.** `active_platforms` 는 `_ads.json` 의 `confirmed_platforms` 만 사용한다. `unknown_platforms` 는 점수에 포함하지 않고 `audit_gaps` 로 그대로 전달한다. 같은 원칙이 pixel 감사에도 적용된다 — 페이지 fetch 실패나 부분 스캔은 `rejected_unreachable` 로 처리하고, 부분 결과로 "no pixel" 을 추론하지 마라.

```
# read _ads.json
active_platforms = set(ads["confirmed_platforms"])
audit_gaps = set(ads["unknown_platforms"])

# read _pixels.json
if pixels["status"] == "unreachable" or pixels.get("partial_scan"):
    verdict = "rejected_unreachable"   # 감사 공백 — 절대 false positive 로 진행 금지

# intersection only over confirmed platforms
leak_surface = active_platforms ∩ missing_for_platforms

if not active_platforms:
    verdict = "rejected_no_ads"       # confirmed == 0, unknown 이 몇 개든 reject
elif not leak_surface:
    verdict = "rejected_no_leak"
else:
    base = len(leak_surface) * 3      # 3, 6, 9
    if reviews >= 50: base += 1
    if reviews >= 200: base += 1
    if "meta" in active_platforms and not facebook_pixel: base += 1
    priority = min(base, 10)
    verdict = "qualified"

# auto-send requires priority AND a complete audit (no gaps on the leaking platform)
auto_send_eligible = (
    verdict == "qualified"
    and priority >= 8
    and not (leak_surface & audit_gaps)    # never auto-send if the leaking platform was not confirmed
)
```

출력에 반드시 포함:
- `active_platforms` (confirmed only)
- `audit_gaps` (unknown_platforms from ads + any pixel partial-scan flags)
- `leak_surface`
- `verdict`, `priority`, `auto_send_eligible`

## 피치 앵글 매핑

| Leak | pitch_angle |
|------|-------------|
| Meta ads + no FB Pixel | `fb_pixel_leak` |
| Google Ads + no remarketing tag | `gads_remarketing_leak` |
| LinkedIn Ads + no Insight Tag | `linkedin_insight_leak` |
| Multi-platform leak | `multi_platform_leak` |
| Has GA but no GTM | `data_quality_leak` |

## 협업
- Read by `outreach-composer` — uses `pitch_angle` to select template, `leak_summary` for the hook.
- Orchestrator skips composer entirely for `verdict != "qualified"` (token savings).
