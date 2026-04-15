---
name: retarget-prospector
description: Find local businesses actively running paid ads (Meta, Google, LinkedIn) but missing retargeting pixels, qualify by leak severity, and auto-send personalized cold outreach. Use when the user asks to find retargeting prospects, ad-leak leads, businesses without pixels, missing pixel outreach, retargeting outreach campaigns, or any variation like "find businesses running ads but not retargeting", "ad leaking businesses", "retarget pitch", "missing FB pixel leads", "rerun retarget campaign", "more retarget leads", or "redo the retarget pitches".
---

# Retarget Prospector — Orchestrator

End-to-end pipeline: discover → verify ads → audit pixels → qualify → compose outreach → auto-send (gated). Wraps existing `pipelines/retarget_prospector/prospect_no_pixel.py`, `pipelines/retarget_prospector/cold_email.py`, and a 4-agent team.

## ICP (authoritative)

The full target definition lives in `references/icp.md` — **read it before every run**. Summary:

> Considered-purchase **UK** local service businesses, currently **spending on Google Ads**, with missing or underused **Meta** remarketing infrastructure.

Hard gates (in eval order): geography (UK only) → category (whitelist + blacklist) → **active Google Ads (GATC or site Conversion Tag) — REQUIRED** → website → trust → size → Meta cohort.

Meta status segments qualified prospects into cohorts (not a rejection):
- **Cohort A** — Meta pixel installed, no active Meta ads (`meta_dormant_pixel`)
- **Cohort B** — no pixel, no active Meta ads (`meta_greenfield`)
- **Cohort C** — active Meta ads (3+ creatives) with missing pixel or infra gap (`meta_infra_gap`) — highest priority

Anything passing Gate 3 (Google Ads) but with a complete Meta setup and no leak is `rejected_no_leak`. Phase 1 must only crawl whitelist categories in single UK cities.

## 트리거 키워드
초기 실행 + 후속 작업 모두 지원해야 함:
- "find businesses running ads without retargeting"
- "retargeting prospects in {city}"
- "ad leak leads"
- "missing pixel campaign"
- "rerun retarget pipeline"
- "redo the outreach for {slug}"
- "more retarget leads from yesterday"

## 실행 모드
**하이브리드.** Phase 1-3 = 병렬 서브 에이전트 (throughput). Phase 4 = 에이전트 팀 (qualifier + composer 공유 컨텍스트). Phase 5 = orchestrator 직접 실행 (auto-send 가드레일).

## Phase 0a: Preflight (필수)

실제 prospect 실행 전에 반드시 health check 통과:
```bash
cd "/Users/foxy/Hermes Bot"
python3 validation/preflight.py
```
non-zero exit → 즉시 중단하고 사용자에게 어떤 check 가 실패했는지 보고. 절대 실패한 dependency 로 실행 진입하지 마라 — silent scraper 실패가 false negative 의 주요 원인이다.

추가로 detector eval gate 최소 주 1회 또는 scraper 수정 후 재실행:
```bash
python3 validation/eval_detectors.py
```
실패 시 생산 실행 차단. `validation/ground_truth.json` 에 대해 precision/recall/FP rate 를 측정하며 FP rate == 0 필수.

## Phase 0: 컨텍스트 확인

매 실행 시작 시 분류:
1. `_workspace/retarget/` 존재 여부 확인.
2. 사용자 요청 분류:
   - **초기 실행** — 카테고리/도시 새로 지정. 기존 `_workspace/retarget/` 있으면 `_workspace/retarget_prev_{date}/` 로 이동.
   - **부분 재실행** — "redo outreach for {slug}" → 해당 slug의 `_outreach.json`만 삭제하고 Phase 4부터 재실행.
   - **확장 실행** — "more leads" → 기존 `candidates.json` 유지, Phase 1만 다시 실행하여 새 후보 추가.
   - **상태 조회** — "show retarget pipeline status" → `_workspace/` 읽고 요약만 출력. Phase 1 진행 안 함.
3. `_workspace/retarget/` 폴더 보장.

## Phase 1: 후보 발견

**ICP precheck.** Before crawling, validate the user's request against `references/icp.md`:
- City must be UK (London, Manchester, Edinburgh, Birmingham, Leeds, Glasgow, Bristol, Cardiff, Liverpool, etc.). Reject "UK" as a single input — crawl one city at a time.
- Category must be in the ICP whitelist. Reject blacklist categories (emergency trades, restaurants, retail, NHS) immediately and ask the user to choose a whitelist category.

```bash
cd "/Users/foxy/Hermes Bot"
python3 -m pipelines.retarget_prospector.prospect_no_pixel "{whitelist_category}" "{uk_city}" --limit {limit} --meta-ads --country GB
```

출력은 `prospects/{category}-{city}-poor-pixels.json` 이미 생성됨. 이를 `_workspace/retarget/candidates.json` 으로 복사.

각 후보의 minimal fields: `slug`, `business_name`, `category`, `country`, `address`, `website`, `phone`, `email`(있으면), `rating`, `review_count`, `team_size`, `services`, `last_modified`, `accreditations`, `companies_house`, `linkedin_employees`, `facebook_page`(있으면), `linkedin_url`(있으면). 누락된 트러스트/사이즈 필드는 빈 값으로 두고 qualifier 가 게이트에서 처리한다.

**사용자가 candidates 검토를 원하면 여기서 일시정지.** 기본은 자동 진행.

## Phase 2: 광고 검증 (병렬)

각 후보마다 `ad-intel-scout` 서브 에이전트를 `Agent` 도구로 spawn. 5개씩 배치로 병렬 실행 (`run_in_background: true`). API/스크래핑 rate limit 고려하여 최대 5 동시.

각 에이전트 prompt에 포함:
- 후보의 business_name, website, domain, facebook_page, linkedin_url
- 출력 경로: `_workspace/retarget/{slug}_ads.json`
- "ad-verification 스킬을 사용하여 Meta Ad Library, GATC, LinkedIn Ads 모두 확인"
- `model: "opus"` 명시

모든 배치 완료 대기 후 다음 phase.

## Phase 3: 픽셀 감사 (병렬)

각 후보마다 `pixel-auditor` 서브 에이전트 spawn. 동일 패턴, 5 동시.

각 에이전트 prompt에 포함:
- 후보의 website
- 출력 경로: `_workspace/retarget/{slug}_pixels.json`
- "pixel-leak-analysis 스킬을 참조"
- `model: "opus"` 명시

## Phase 4: 자격심사 + 피치 작성 (에이전트 팀)

`TeamCreate` 로 팀 구성:
- 팀명: `retarget-team`
- 멤버: `retarget-qualifier`, `outreach-composer`
- 리더: orchestrator (메인 세션)

각 후보에 대해:
1. `TaskCreate` — qualifier 에게 `references/icp.md` + `_ads.json` + `_pixels.json` + 원본 `candidates.json` 레코드 읽고 `_qualified.json` 작성 요청. qualifier 는 7개 게이트(geo, category, google_ads, website, trust, size, meta_cohort)를 순서대로 평가하고 verdict + cohort A/B/C 출력.
2. qualifier 가 `verdict: rejected_*` 출력 시 composer 호출 생략. 거절 사유는 `icp_gates` 에 게이트별로 기록.
3. `verdict: qualified` 면 `TaskCreate` — composer 에게 `_outreach.json` + `_outreach.md` 작성 요청. composer 는 `cohort` 로 템플릿 선택 (A=`meta_dormant_pixel`, B=`meta_greenfield`, C=`meta_infra_gap`).

팀 통신: qualifier → composer 핸드오프는 `SendMessage` 로 cohort + pitch_angle + priority 만 전달, 상세는 파일에서 읽음.

### Phase 4b: Composer Grounding Gate (필수)

composer 가 `_outreach.json` 작성 완료 후, **모든 파일** 에 대해 hallucination guard 를 실행:
```bash
cd "/Users/foxy/Hermes Bot"
for f in _workspace/retarget/*_outreach.json; do
  python3 .claude/skills/ad-verification/scripts/validate_composer_output.py "$f" --output "$f"
done
```
각 파일의 `composer_validation.passed == false` 이면 해당 outreach 를 `_workspace/retarget/rejected/` 로 이동하고 Phase 5 에서 제외. 사유(`errors` 리스트)를 Phase 6 보고에 포함.

이 단계는 optional 이 아니다. composer 는 ad creative 에서 inventing quote 를 할 수 있으므로 verbatim grounding check 없이 발송하면 prospect 에게 거짓 주장을 보내는 셈이다.

모든 후보 처리 완료 후 `TeamDelete`.

## Phase 5: 발송 (가드레일)

**Dry-run 은 기본값이다.** 사용자가 명시적으로 `really send` / `send for real` / `send live` 같은 문구를 줄 때만 실제 발송. 그 외 모든 경우 `_workspace/retarget/dry_run_report.md` 만 작성하고 SMTP 호출 0회.

dry-run 보고서 내용:
- 발송 대상 후보 목록 (slug, business_name, priority, pitch_angle, email subject)
- 각 후보의 confirmed_platforms + audit_gaps + leak_surface (검증용)
- composer_validation 결과 요약 (passed count, rejected count)
- 예상 발송 시간대 + account 분배
- **"To send for real, re-run with `really send`"** 안내

발송 전 안전 체크 (실제 발송 경로):
1. Phase 0a preflight 가 이번 세션에서 이미 통과했는가? 미통과면 중단.
2. Dry-run 플래그 확인 — 첫 실행은 무조건 dry-run. 사용자가 "really send" 명시해야 진짜 발송.
2. 자동발송 자격 필터: `auto_send_eligible: true` AND `priority >= 8` AND not in `_workspace/retarget/sent.jsonl`
3. **하드 한도: per-run 최대 20건.** 초과 시 오버플로우는 manual review 큐로.
4. 도메인 reputation 보호: 동일 도메인 send_log 기반 daily limit 준수 (`cold_email.count_sends_today`).

발송 루프 (Python 스크립트로 실행):
```bash
cd "/Users/foxy/Hermes Bot"
python3 -c "
import json, sys
sys.path.insert(0, '.')
from cold_email import send_smtp, pick_account, count_sends_today
from pathlib import Path
from datetime import datetime, timezone

ws = Path('_workspace/retarget')
sent_log_path = ws / 'sent.jsonl'
sent_slugs = set()
if sent_log_path.exists():
    for line in sent_log_path.read_text().splitlines():
        sent_slugs.add(json.loads(line)['slug'])

# load qualified outreach files, send those eligible
sent_count = 0
for outreach_file in ws.glob('*_outreach.json'):
    if sent_count >= 20:
        break
    data = json.loads(outreach_file.read_text())
    if not data.get('auto_send_eligible'):
        continue
    slug = data['slug']
    if slug in sent_slugs:
        continue
    # ... pick_account, send_smtp, append to sent.jsonl
    sent_count += 1
print(f'sent: {sent_count}')
"
```

(실제 발송 코드는 orchestrator 가 직접 작성. 위는 패턴 예시.)

WhatsApp 메시지: v1 은 발송 안 함. `_workspace/retarget/whatsapp_queue.md` 에만 작성. 사용자가 수동 발송.

## Phase 6: 보고

다음을 사용자에게 보고:
- 후보 총 N → 자격 통과 M → 자동발송 K → 수동검토 J → 거절 R
- Top 3 qualified leads (priority + leak_summary)
- 거절 사유 분포 (rejected_no_ads / no_leak / unreachable)
- `_workspace/retarget/` 경로 안내

## 데이터 흐름

```
pipelines/retarget_prospector/prospect_no_pixel.py → _workspace/retarget/candidates.json
                    ↓
        ┌───────────┴───────────┐
        ▼                       ▼
ad-intel-scout × N      pixel-auditor × N
        │                       │
{slug}_ads.json         {slug}_pixels.json
        └───────────┬───────────┘
                    ▼
            retarget-qualifier
                    ▼
            {slug}_qualified.json
                    ▼ (qualified only)
            outreach-composer
                    ▼
            {slug}_outreach.json + .md
                    ▼ (auto_send_eligible only)
            cold_email.send_smtp
                    ▼
            sent.jsonl
```

## 에러 핸들링

| 시나리오 | 동작 |
|---------|------|
| Phase 1 0 candidates | 보고 후 종료. 카테고리/도시 변경 제안. |
| ad-intel-scout 모든 platform unknown | qualifier 가 reject. 보고에 포함. |
| pixel-auditor unreachable | qualifier 가 reject. 사용자가 도메인 검토. |
| qualifier 0 qualified | 보고 후 종료. 다른 카테고리 시도 제안. |
| send_smtp hard_bounce | `cold_email` 이 `suppressed.json` 에 자동 추가. 다음 후보로. |
| send_smtp soft fail | 1회 재시도 후 manual review 큐로. |

## 테스트 시나리오

**정상 흐름:** 사용자 "find 5 electricians in Edinburgh running ads without retargeting"
1. Phase 0: 신규 실행 분류
2. Phase 1: `pipelines/retarget_prospector/prospect_no_pixel.py electrician Edinburgh --limit 5 --meta-ads` 실행, 5 후보
3. Phase 2-3: 5개 ad-intel + 5개 pixel-auditor 병렬
4. Phase 4: qualifier 가 3개 qualified, 2개 reject
5. Phase 5: dry-run (첫 실행), 발송 안 함, draft 만 출력
6. Phase 6: 보고

**에러 흐름:** GATC 스크래퍼가 selector 변경으로 실패
1. ad-intel-scout 가 `has_google_ads: unknown`, `errors: ["gatc: selector_failed"]` 기록
2. 다른 source (Meta, LinkedIn) 만으로 confidence 계산
3. qualifier 가 평소대로 처리 (no-op for unknowns)
4. 보고에 GATC 실패 빈도 포함
