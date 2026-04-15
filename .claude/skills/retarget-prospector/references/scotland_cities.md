# Scotland City List — Retarget Prospector Sweep

Full Scotland coverage, tiered by population. The Scotland sweep runs every city on this list; tiering only sets execution order so the largest prospect pools return first and the user can pause between tiers if quota or review bandwidth runs short.

This is not a top-N filter. Every city here is in-scope.

## Tier 1 — Major cities (population > 200k)

Hit these first. Largest pools of considered-purchase businesses and Google Ads spenders.

| City | Slug | Approx pop |
|------|------|-----------|
| Glasgow | `glasgow` | 635k |
| Edinburgh | `edinburgh` | 525k |
| Aberdeen | `aberdeen` | 220k |
| Dundee | `dundee` | 150k (included — capital of Tayside, viable pool) |

## Tier 2 — Mid-sized (50k–200k)

Run after Tier 1 verification passes.

| City | Slug |
|------|------|
| Paisley | `paisley` |
| East Kilbride | `east-kilbride` |
| Livingston | `livingston` |
| Hamilton | `hamilton` |
| Cumbernauld | `cumbernauld` |
| Kirkcaldy | `kirkcaldy` |
| Dunfermline | `dunfermline` |
| Ayr | `ayr` |
| Perth | `perth` |
| Inverness | `inverness` |
| Kilmarnock | `kilmarnock` |
| Greenock | `greenock` |
| Coatbridge | `coatbridge` |
| Glenrothes | `glenrothes` |
| Airdrie | `airdrie` |
| Stirling | `stirling` |
| Falkirk | `falkirk` |

## Tier 3 — Smaller towns (20k–50k, considered-purchase viable)

Run last. Smaller prospect pools but often underserved by competitors.

| City | Slug |
|------|------|
| St Andrews | `st-andrews` |
| Dumfries | `dumfries` |
| Motherwell | `motherwell` |
| Wishaw | `wishaw` |
| Bearsden | `bearsden` |
| Bishopbriggs | `bishopbriggs` |
| Newton Mearns | `newton-mearns` |
| Clydebank | `clydebank` |
| Renfrew | `renfrew` |
| Rutherglen | `rutherglen` |
| Cambuslang | `cambuslang` |
| Elgin | `elgin` |
| Oban | `oban` |
| Fort William | `fort-william` |

## Category matrix

Each city runs against the full Gate 2 whitelist from `icp.md`. Prioritise these categories for Tier 1 sweeps where the Google-Ads-spender density is highest:

1. `dentist`
2. `aesthetic clinic`
3. `cosmetic clinic`
4. `solicitor` (private client only)
5. `accountant`
6. `financial advisor`
7. `mortgage broker`
8. `optician`
9. `vet`
10. `architect`
11. `interior designer`
12. `wedding venue`
13. `private school`
14. `driving school` (intensive only)

Tier 2 and Tier 3 cities can start with the top 5 categories only and expand if the pool is thin.

## Idempotence

`scripts/crawl_scotland.py` skips a `(city, category)` pair if its output file was written in the last 14 days, unless `--force` is passed. This makes monthly refreshes cheap.
