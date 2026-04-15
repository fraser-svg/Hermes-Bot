---
name: no-website-prospector
description: Find UK local-service businesses with NO website (or a broken/placeholder website), auto-generate a professional website for each via the Hermes core/generate.py pipeline, deploy to Cloudflare Pages, and append each to an outreach CSV with name, location, phone, email, and live site URL. Use whenever the user asks to find no-website prospects, build sites for no-website leads, generate outreach for businesses missing websites, or issues follow-ups like "more no-website leads", "rerun no-website", "redo outreach for {slug}", "build site for {business}", "find companies with no website", "prospect businesses without websites". DO NOT use for retarget/pixel-leak prospecting — that is a separate pipeline (retarget-prospector).
---

# No-Website Prospector Orchestrator

UK local-service businesses 중 웹사이트 없거나 형편없는 곳 찾기 → Hermes로 사이트 자동 생성 → Cloudflare Pages 배포 → outreach CSV 업데이트 파이프라인.

## Core Loop

```
discover (prospect.py)
  → website health probe
  → qualify (no-website-qualifier agent, per candidate)
  → build each qualified (hermes-design-harness)
  → deploy each built (core/deploy.py)
  → discover email (best-effort)
  → emit outreach CSV (pipelines/no_website_prospector/emit_nowebsite_outreach.py)
```

## Phase 0 — 컨텍스트 확인

`_workspace/nowebsite/` 존재 여부로 실행 모드 결정:

- 미존재 → **초기 실행**
- 존재 + 사용자가 "more leads" / "add cities" → **증분 실행** (기존 산출물 보존, 새 cities/categories만 탐색)
- 존재 + 사용자가 "redo outreach for {slug}" → **부분 재실행** (해당 slug만 Phase 3-6 재실행)
- 존재 + 사용자가 "rerun everything" → `_workspace/nowebsite/`를 `_workspace/nowebsite_prev_{timestamp}/`로 이동 후 초기 실행

## Phase 1 — Discover

입력 수집:
- cities: 쉼표 리스트 (예: "Edinburgh, Glasgow, Stirling"). 사용자가 명시 안 했으면 AskUserQuestion으로 확인.
- categories: 쉼표 리스트 (예: "electrician, plumber, roofer"). 명시 안 했으면 화이트리스트 기본값(`electrician, plumber, roofer, hvac, cleaner, locksmith`) 제안 후 확인.
- limit per (city × category): 기본 20.

실행:
```bash
python3 -m pipelines.no_website_prospector.run_nowebsite_pipeline --cities "<cities>" --categories "<cats>" --limit <n> --discover-only
```

출력: `_workspace/nowebsite/candidates.json` (prospect.py가 `websiteUri` 비어있는 레코드만 보존).

## Phase 2 — Qualify

각 candidate에 대해:
1. **Website health probe** — candidate에 `website_url`이 비어있지 않으면 HEAD/GET으로 HTTP 상태 + `<title>` 확인. placeholder 시그널 탐지. 결과를 `candidate.website_health`에 기록. 비어있으면 `status=no_site`.
2. **Qualifier agent** 호출 — `Agent(subagent_type="no-website-qualifier", model="opus", ...)`로 candidate 전달. verdict + cohort 수집.

대량 처리 시 헬스 프로브는 파이프라인 스크립트가 일괄 실행하고, qualifier agent는 결과를 종합하여 verdict 반환.

출력: `_workspace/nowebsite/{slug}_qualified.json` × N.

## Phase 3 — Build (per qualified prospect)

**Default build path: `template-site-builder` skill** (uses Claude Code + `core/templates/ULTIMATE_TEMPLATE.html`, no OpenRouter spend). Alternative `hermes-design-harness` is available for Gemini-based full generation when OpenRouter credit is present.

각 qualified record에 대해:
1. `template-site-builder` 스킬 invoke → Phase 1 (`core/fill_template.py <slug>`) + Phase 2 (author 21 copy slots inline using COPY.md + frontend-design skill) + Phase 3 (`core/validate_filled_html.py`).
2. 산출물: `output/{slug}.html`. Validator must exit 0 (score ≥ 8.0, no sentinels, no banned vocab).

품질 기준: 15/15 validation AND 0 readability warnings 미달 시 재빌드 1회, 여전히 실패하면 건너뛰고 `{slug}_build_failed.json`에 이유 기록.

## Phase 4 — Deploy

```bash
python3 -m core.deploy output/{slug}.html
```

`prospects/deploys.json`에서 해당 slug의 `url` 조회. pipeline 스크립트가 `_workspace/nowebsite/{slug}_deployed.json`에 기록.

## Phase 5 — Email Discovery (best-effort)

No-website cohort는 접근 가능한 사이트가 없으므로 email 소스가 제한적. 전략:
1. candidate의 GBP record에 이미 email 필드가 있는지 확인 (드뭄).
2. Companies House 이름 조회로 등록 연락처 확인 (`.claude/skills/ad-verification/scripts/lookup_companies_house.py` 재사용).
3. 모두 실패하면 `email=""`, `email_source="not_found"`로 남김. 사용자가 수동 enrichment.

이 Phase는 실패해도 파이프라인 중단하지 않음.

## Phase 6 — Emit Outreach CSV

```bash
python3 -m pipelines.no_website_prospector.emit_nowebsite_outreach
```

출력: `output/nowebsite_outreach.csv`. 컬럼:
```
business_name, city, address, phone_number, phone_e164, email, email_source,
website_url, slug, rating, review_count, cohort, deployed_at
```

기존 CSV가 있으면 slug로 dedup 후 append. 최종 통계 출력 (cohort A/B/C 분포).

## User Summary

파이프라인 종료 시 사용자에게 요약:
```
Discovered: {N} candidates
Qualified: {Q} ({A} greenfield / {B} broken / {C} placeholder)
Built: {K} sites (score 15/15)
Deployed: {D} to Cloudflare Pages
CSV rows: {R} (output/nowebsite_outreach.csv)

Next: review CSV, run pipelines/retarget_prospector/cold_email.py for outreach.
```

피드백 요청: "개선할 부분 있나요? 추가 cities/categories/gates?"

## Error Handling

| 실패 | 대응 |
|------|------|
| Google Places API 키 없음 | 즉시 중단, `.env`에 `GOOGLE_API_KEY` 추가 안내 |
| 특정 city/category 0 hits | 경고 로그, 다음으로 진행 |
| Website health probe timeout | `health=broken`로 처리 (추정 상 접근 불가는 고객에게도 보이지 않음) |
| Build 실패 (validation < 15/15) | 1회 재시도, 실패 시 해당 prospect 건너뛰고 `_build_failed.json` 기록 |
| Deploy 실패 (wrangler) | 재시도 1회, 실패 시 CSV에서 `website_url=""`, `deploy_status="failed"`로 표시 |

Atomic 원칙: 중간 실패가 이미 배포된 사이트를 롤백하지 않는다. CSV는 최종 단계에서 새로 작성되므로 부분 데이터도 일관성 유지.

## 테스트 시나리오

**정상 흐름:** "Find me UK electricians with no website in Stirling, build them sites" → Phase 1이 Places API로 Stirling electricians 20개 검색 → websiteUri 없는 N개 candidate → health probe로 전원 no_site 확인 → qualifier가 rating≥3.8, reviews≥10 통과한 K개 qualified → K개 사이트 build/deploy → CSV에 K 행 append.

**에러 흐름:** "Run no-website for London plumbers" → Places API 응답 timeout → preflight가 감지 → 사용자에게 API 키 점검 요청, 중단.

**부분 재실행:** "Redo outreach for stirling-sparks" → Phase 0이 기존 `_workspace/nowebsite/` 감지 → 해당 slug만 Phase 3-6 재실행 → CSV에서 해당 행만 갱신.

## References

- `references/qualification-gates.md` — gate 순서 + website health probe 상세 룰
- `../hermes-design-harness/SKILL.md` — per-prospect build 실행
- `../../agents/no-website-qualifier.md` — qualifier agent 정의
- 번들된 bridge scripts: `pipelines/no_website_prospector/run_nowebsite_pipeline.py`, `pipelines/no_website_prospector/emit_nowebsite_outreach.py` (repo root에 위치)
