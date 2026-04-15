# Slot Map — ULTIMATE_TEMPLATE.html

Template has 47 unique `{{slot}}` placeholders, bucketed by who fills them.

## Direct data (filled by `core/fill_template.py`)

| Slot | Source | Notes |
|------|--------|-------|
| `{{business.name}}` | `candidate.business_name` | — |
| `{{business.category}}` | `candidate.business_category` | lowercase |
| `{{business.city}}` | `candidate.city` | — |
| `{{business.address}}` | `candidate.address` | footer only |
| `{{business.phone}}` | `candidate.phone_number` | display form |
| `{{business.phone_tel}}` | derived | E.164 (`+44…`) |
| `{{business.rating}}` | `candidate.rating` | drops trailing `.0` |
| `{{business.review_count}}` | `candidate.review_count` | — |
| `{{review_{1..3}_quote}}` | `candidate.google_reviews[i].text` | truncated ≤30 words, COPY.md §5 |
| `{{logo_html}}` | `candidate.business_name` | no logo URL in GBP data; falls back to styled text |

## Derived / lookup (filled by `core/fill_template.py` via `vertical-defaults.json`)

| Slot | Derivation |
|------|-----------|
| `{{category_article}}` | "an" if category starts with vowel, else "a" |
| `{{year}}` | current year |
| `{{years_short}}` | "Local" placeholder — GBP has no founding year |
| `{{response_window}}` | vertical-defaults.response_window |
| `{{service_radius}}` | `hint.format(city=candidate.city)` |
| `{{credential_human}}` | vertical-defaults.credential_human |
| `{{credential_marker}}` | vertical-defaults.credential_marker |
| `{{credential_subtext}}` | vertical-defaults.credential_subtext |
| `{{hero_image_url}}` | `hero_images.resolve(category).hero` |
| `{{service_{1..6}_icon}}` | digits 1–6 (CSS themes them) |
| `<html data-persona="…">` | vertical-defaults.persona ("cold" or "warm") |

## Copy (filled by Claude Code — ME — following `copy-instructions.md`)

Every copy slot is replaced with a sentinel by `core/fill_template.py`:
```html
<!-- COPY_TODO:<slot>|<instruction> -->[[WRITE_<slot>]]
```

| Slot | Formula | Length |
|------|---------|--------|
| `{{hero_subhead}}` | COPY.md §3 S-A/S-B/S-C/S-D | ≤25 words |
| `{{service_{1..6}_title}}` | COPY.md §6 title | ≤4 words, sentence case |
| `{{service_{1..6}_description}}` | COPY.md §6 description | outcome_verb + deliverable. + qualifier/proof. ≤15 words |
| `{{faq_{1..5}_answer}}` | COPY.md §7 Q1–Q5 | 25–40 words per question |
| `{{review_{1..3}_name}}` | COPY.md §5 attribution | "First-name, neighborhood/town" — never surname |

## Additional injections

`core/fill_template.py` injects before `</head>`:
- `<meta name="description" …>` — derived from business fields (satisfies validator check)
- `<script type="application/ld+json">` LocalBusiness schema — (satisfies validator check)
