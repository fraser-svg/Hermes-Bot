# Design-Only Prompt (Stage 2)

You receive pre-written website content as JSON. Your ONLY job is HTML/CSS layout and styling. Do NOT rewrite the copy. Use it exactly as provided.

## Aesthetic: YC Startup

Think Stripe, Linear, Vercel applied to a local business.

### Typography
- Font: Inter (weights 400, 500, 600, 700, 800)
- H1: clamp(2.5rem, 6vw, 4.5rem), weight 800, letter-spacing -0.05em
- H2: clamp(1.75rem, 4vw, 2.75rem), weight 700, letter-spacing -0.03em
- H3: 1.25rem, weight 600
- Body: 1rem, weight 400, line-height 1.65, max-width 650px
- Labels: 0.875rem, weight 500, uppercase, letter-spacing 0.05em

### Palette
- Canvas: #FFFFFF, alt sections: #F3F4F6
- Borders: #E5E7EB (1px only)
- Ink: #111827 (headings), #6B7280 (body)
- Accent: provided in the data JSON as `accent_color`. Use ONLY for primary CTA button and icon highlights.
- 90% white/gray, 10% accent. No color anywhere else.

### Layout Rules
- Bento grid for services (mixed card sizes, NOT uniform 3-column)
- Each section uses a DIFFERENT layout from the one above it
- Rigid spacing: 4/8/16/24/32/48/64/96/128px scale
- Section padding: 96px top/bottom desktop, 64px mobile
- At least 2 overlapping elements (image crossing section boundary, badges floating between sections)
- Generous negative space. If busy, delete 30%.

### Cards & Shadows
- Border: 1px solid #E5E7EB
- Radius: 16px on all containers
- Shadow: `0 1px 3px rgba(0,0,0,0.08), 0 8px 20px rgba(0,0,0,0.04)`
- Hover: `0 1px 3px rgba(0,0,0,0.1), 0 12px 32px rgba(0,0,0,0.08)` + translateY(-2px)

### Buttons (CRITICAL - no slop)
- Primary: solid accent fill OR #111827 fill with white text. border-radius 8px. No gradient. No glow. No colored shadow.
- Secondary: transparent, 1px solid #E5E7EB, color #111827. Same radius.
- Hover: darken 10% + translateY(-1px). Nothing else.
- Text: sentence case. Not ALL CAPS.

### Hero
- Full-bleed Unsplash photo background (use the `hero_image_url` from data)
- Dark gradient overlay: linear-gradient(270deg, transparent 20%, rgba(0,0,0,0.75) 100%)
- White text with text-shadow: 0 2px 8px rgba(0,0,0,0.5)
- Min-height: 85vh desktop, 500px mobile
- Trust badges below CTA with semi-transparent dark pill backgrounds

### Section Dividers
- Dead straight 1px lines or no divider (just spacing). NEVER wavy SVGs.

### Images
- Hero: background-image with dark overlay
- About: real Unsplash photo (use `about_image_url` from data), integrated into layout not centered clip-art
- All images: object-fit cover, border-radius 16px

### Accent Section (ONE per site)
- Full-width #111827 background with white/accent text
- Contains the stats (jobs completed, rating, years, response time)
- Layered above and below by white sections

### Footer
- #111827 background, white text at 0.85 opacity
- Simple: brand name, nav links, legal

### Mobile
- Single column below 768px
- Sticky bottom CTA bar with phone number
- Stack all grids to 1 column

### Readability (NON-NEGOTIABLE)
- text-shadow on ALL white text over images
- Hero overlay opacity >= 0.6 where text sits
- No white text on gold/yellow
- No text below 0.7 opacity
- ::placeholder { color: #9CA3AF; }
- All CTA buttons 4.5:1 contrast minimum

### Anti-Slop Checklist
Before outputting, verify:
- [ ] No gradient buttons
- [ ] No pill-shaped buttons (100px radius)
- [ ] No wavy SVG dividers
- [ ] No warm cream/beige backgrounds
- [ ] No decorative serif fonts
- [ ] No generic copy ("revolutionary", "unmatched", "experience the best")
- [ ] Inter font loaded from Google Fonts
- [ ] Bento grid layout (not uniform columns)
- [ ] City name appears in hero headline
- [ ] Layered shadows (not single heavy shadows)

## Output
Return ONLY the complete HTML document. No explanations. No markdown fences. Start with <!DOCTYPE html>.
