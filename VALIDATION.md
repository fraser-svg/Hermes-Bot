# Validation: Sharp (Rust LLM Reverse Proxy)
Status: KILLED
Date: 2026-04-10

## Problem
OpenRouter middleman markup on LLM API calls, late-triggering context compression (50% fill), no unified cost dashboard across providers.

## Who
Developer running hermes-agent sessions for website generation pipeline.

## Pain (quantified)
- OpenRouter markup: ~15-30% on provider prices, estimated $5-20/month at current volume
- Compression gap: unknown token waste between turn 3 and 50% threshold
- Cost visibility: no unified dashboard (inconvenience, not blocker)

## Existing Solutions
1. hermes-agent already supports direct provider APIs (zero code change eliminates OpenRouter)
2. LiteLLM Proxy (40K+ stars): model routing, format conversion, cost tracking, streaming — battle-tested
3. context_compressor.py threshold tunable (5-line patch for earlier compression)

## Kill Test
If never built: $5-20/month extra OpenRouter cost, some token waste. No website goes unbuilt. North star unaffected.

## Kill Reason
Solution complexity (Rust workspace, 11 files, format conversion reimplementation) vastly exceeds problem magnitude. Existing tools solve 90%+ of stated pain with zero to minimal code.

## Recommended Path
1. Direct provider API keys in hermes-agent config (zero code)
2. Lower compression threshold in context_compressor.py (5 lines)
3. If proxy needed: LiteLLM (pip install + config file)
