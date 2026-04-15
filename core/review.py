"""Hermes Website Reviewer — AI-powered critical design review.

Screenshots a generated website at desktop + mobile viewports via Playwright CLI,
sends screenshots + HTML to a vision model via OpenRouter, returns a structured
grade card across 4 dimensions: design, UX, content, flow.

Usage:
    python3 review.py output/spartan-electrical.html   # review specific file
    python3 review.py                                    # review latest (index.html)
    python3 review.py --cheap                            # use Gemini Flash (cheaper)
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
REPORT_PATH = BASE_DIR / "review_report.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_DEFAULT = "anthropic/claude-sonnet-4"
MODEL_CHEAP = "google/gemini-2.5-flash"
MAX_TOKENS = 4096

CHEAP_MODE = "--cheap" in sys.argv


# ---------------------------------------------------------------------------
# Review rubric — condensed from prompts/website_builder.md
# Focuses on what regex CAN'T catch: subjective visual quality, UX feel, copy
# ---------------------------------------------------------------------------

REVIEW_RUBRIC = """You are a brutally honest website design critic. You review websites
built for local service businesses (electricians, plumbers, roofers, etc).

Grade the website across 4 dimensions, 1-10 each. Be harsh — an 8 means genuinely
impressive, a 5 means mediocre, a 3 means embarrassing. Most AI-generated sites
deserve a 5-7. Reserve 9-10 for sites you'd show a client with pride.

## DESIGN (1-10)

Check these specific criteria:
- Typography: Is it Inter with weight 800 for H1, tight letter-spacing (-0.04em+)?
  Body text max-width 650px? Line-height 1.6+? Clear size hierarchy H1 > H2 > body?
- Color discipline: 90% white/gray canvas, 10% single accent color? Cold whites
  (#FFFFFF/#F9FAFB), not warm cream? Ink is near-black (#111827)?
- Spacing rhythm: Consistent scale (4/8/16/32/64px)? Sections breathing with
  generous padding? No cramped areas?
- Cards: Bento grid with mixed sizes (not boring uniform 3-col)? Layered shadows
  (not single heavy drop shadow)? Border-radius consistent (12/16/24px)?
- Section rhythm: Canvas/canvas-alt backgrounds alternating? ONE bold accent-colored
  section at visual midpoint? Dark hero → light body → dark footer?
- Anti-slop: NO wavy blob dividers, NO gradient buttons, NO pill-shaped everything,
  NO colored/glow shadows, NO 3D icons, NO generic stock photo energy?
- Photos: Cool color temperature? Relevant to the trade? Architectural/macro style?
  Hero overlay dark enough for white text?

## UX (1-10)

- Hero impact: Full-bleed photo? CTA visible above fold? Clear value proposition
  readable in 3 seconds?
- Navigation: Sticky/fixed? Logo left, phone + CTA right? On mobile: max 56px
  height, logo text small, CTA button max 2 words?
- Mobile layout: Single column below 768px? Buttons full-width? Adequate touch
  targets (44px+)? Text not tiny?
- CTAs: Primary (filled) + ghost (outlined) button pattern? Accent color only for
  "click me" elements? Phone number tel: linked?
- Forms: 5 or fewer required fields? Clear labels? Visible focus states?
  Placeholder text readable (#9CA3AF minimum)?
- Scroll progression: Each section feels like a natural next step? No jarring jumps?

## CONTENT (1-10)

- Hero headline: Contains city name + specific benefit? Max 8 words? NOT generic
  ("Professional Services" = instant 3/10)?
- Copy specificity: Every sentence has a number, place name, or action verb?
  NO banned words: revolutionary, unmatched, experience, synergy, cutting-edge,
  state-of-the-art, world-class, premier?
- Service descriptions: Say what happens, not value propositions? Max 15 words per
  card description?
- Reviews: Sound like real humans wrote them? Mention specific work done? Not
  generic praise like "Great service, highly recommend"?
- About section: Feels human? Max ~60 words? Verifiable claims (years, certs)?
- Trust signals: Stats bar with believable numbers? Not suspiciously round
  (exactly 1000 jobs = fake feeling)?

## FLOW (1-10)

- Section order: Nav → Hero → Services → Social Proof → About/Why Us →
  Service Areas → Contact → Footer? Logical progression?
- Narrative arc: Problem (hero) → Solution (services) → Proof (reviews/stats) →
  Trust (about/credentials) → Action (contact form)?
- Visual pacing: Dark (hero) → Light → Light → BOLD ACCENT → Light → Dark (footer)?
  The "heartbeat" rhythm?
- Overlap element: At least ONE section-boundary overlap (hero extending into
  services, trust badges bridging sections)? Premium depth feel?
- Journey: Does scrolling feel like a guided journey toward calling/booking?
  Or random sections bolted together?

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown fences, no explanation). Schema:

{
  "design": {
    "score": <int 1-10>,
    "summary": "<one sentence>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
  },
  "ux": {
    "score": <int 1-10>,
    "summary": "<one sentence>",
    "strengths": ["..."],
    "weaknesses": ["..."]
  },
  "content": {
    "score": <int 1-10>,
    "summary": "<one sentence>",
    "strengths": ["..."],
    "weaknesses": ["..."]
  },
  "flow": {
    "score": <int 1-10>,
    "summary": "<one sentence>",
    "strengths": ["..."],
    "weaknesses": ["..."]
  },
  "fixes": [
    {
      "dimension": "<design|ux|content|flow>",
      "severity": "<critical|high|medium>",
      "issue": "<what's wrong>",
      "fix": "<specific actionable fix>"
    }
  ]
}

Include fixes for EVERY weakness. Be specific — "fix the headline" is useless,
"Change hero H1 from 'Professional Electrical Services' to 'Edinburgh Emergency
Electrician. 45-Min Response.'" is useful.
"""


# ---------------------------------------------------------------------------
# Helpers (matching generate.py patterns)
# ---------------------------------------------------------------------------

def load_env() -> dict[str, str]:
    """Load .env file into dict."""
    env: dict[str, str] = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def get_api_key() -> str:
    """Get OpenRouter API key from env."""
    key = os.environ.get("OPENROUTER_API_KEY") or load_env().get("openrouter")
    if not key:
        raise RuntimeError("No OpenRouter API key. Set OPENROUTER_API_KEY or add 'openrouter' to .env")
    return key


def resolve_html_path(argv: list[str]) -> Path:
    """Resolve which HTML file to review."""
    # Filter out flags
    args = [a for a in argv[1:] if not a.startswith("--")]
    if args:
        path = Path(args[0])
        if not path.is_absolute():
            path = BASE_DIR / path
    else:
        path = BASE_DIR / "index.html"

    if not path.exists():
        raise FileNotFoundError(f"HTML file not found: {path}")
    if not path.suffix.lower() == ".html":
        raise ValueError(f"Expected .html file, got: {path}")
    return path


def score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 9:
        return "A"
    if score >= 8:
        return "B"
    if score >= 7:
        return "C"
    if score >= 6:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Playwright screenshots
# ---------------------------------------------------------------------------

def ensure_playwright() -> None:
    """Ensure Playwright + Chromium are available."""
    if not shutil.which("npx"):
        raise RuntimeError("npx not found. Install Node.js: https://nodejs.org/")

    result = subprocess.run(
        ["npx", "playwright", "--version"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Playwright not found. Install: npm install -g playwright\n"
            "Then: npx playwright install chromium"
        )

    # Check if chromium is installed by attempting a trivial screenshot
    test_png = tempfile.mktemp(suffix=".png", prefix="hermes_pw_test_")
    test_result = subprocess.run(
        ["npx", "playwright", "screenshot", "--browser", "chromium",
         "--viewport-size=1,1", "data:text/html,<h1>test</h1>", test_png],
        capture_output=True, text=True, timeout=60,
    )
    if os.path.exists(test_png):
        os.unlink(test_png)
    if test_result.returncode != 0 and "browser" in test_result.stderr.lower():
        print("Installing Chromium for Playwright (one-time)...")
        subprocess.run(
            ["npx", "playwright", "install", "chromium"],
            check=True, timeout=300,
        )


def capture_screenshots(html_path: Path) -> tuple[str, str]:
    """Capture desktop + mobile screenshots, return base64 encoded PNGs."""
    # Use unique temp dir per run to avoid race conditions and symlink attacks
    tmp_dir = tempfile.mkdtemp(prefix="hermes_review_")
    desktop_path = os.path.join(tmp_dir, "desktop.png")
    mobile_path = os.path.join(tmp_dir, "mobile.png")

    file_url = html_path.as_uri()

    viewports = [
        ("desktop", "1440,900", desktop_path),
        ("mobile", "375,812", mobile_path),
    ]

    try:
        for label, size, out_path in viewports:
            print(f"  Capturing {label} screenshot ({size})...")
            result = subprocess.run(
                ["npx", "playwright", "screenshot",
                 "--browser", "chromium",
                 f"--viewport-size={size}",
                 "--full-page",
                 file_url, out_path],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Screenshot failed ({label}): {result.stderr}")

        desktop_b64 = base64.b64encode(Path(desktop_path).read_bytes()).decode("ascii")
        mobile_b64 = base64.b64encode(Path(mobile_path).read_bytes()).decode("ascii")
    finally:
        # Always clean up temp screenshots (success or failure)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return desktop_b64, mobile_b64


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def call_reviewer(
    desktop_b64: str, mobile_b64: str, html: str, api_key: str,
) -> str:
    """Send screenshots + HTML to vision model, return raw response text."""
    model = MODEL_CHEAP if CHEAP_MODE else MODEL_DEFAULT

    # Truncate HTML if massive (keep style + first 800 lines of body)
    html_lines = html.split("\n")
    if len(html_lines) > 800:
        html = "\n".join(html_lines[:800]) + "\n<!-- ... truncated ... -->"

    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Review this local service business website. "
                "Desktop screenshot (1440px wide), mobile screenshot (375px wide), "
                "and full HTML source are provided.\n\n"
                f"HTML source ({len(html)} chars):\n```html\n{html}\n```"
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{desktop_b64}"},
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{mobile_b64}"},
        },
    ]

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": REVIEW_RUBRIC},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.2,
    }).encode("utf-8")

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://hermes-bot.local",
            "X-Title": "Hermes Website Reviewer",
        },
        method="POST",
    )

    print(f"  Calling {model} for review...")
    try:
        with urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No response body"
        raise RuntimeError(f"OpenRouter API error {e.code}: {error_body}") from e

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"No response from model. Full response: {json.dumps(body)}")

    return choices[0]["message"]["content"]


# ---------------------------------------------------------------------------
# Parse response
# ---------------------------------------------------------------------------

def parse_review(raw: str) -> dict:
    """Extract structured review JSON from model response."""
    # Try to find JSON in markdown fences first
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
    text = fence_match.group(1).strip() if fence_match else raw.strip()

    # Find first { and try json.loads from there, trimming from the end on failure
    brace_start = text.find("{")
    if brace_start == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")

    candidate = text[brace_start:]

    # Try parsing as-is first, then progressively trim trailing non-JSON
    review = None
    for end_offset in range(len(candidate), 0, -1):
        chunk = candidate[:end_offset]
        if not chunk.rstrip().endswith("}"):
            continue
        try:
            review = json.loads(chunk)
            break
        except json.JSONDecodeError:
            continue

    if review is None:
        raise ValueError(f"Could not parse JSON from response: {candidate[:300]}")

    # Validate required dimensions
    for dim in ("design", "ux", "content", "flow"):
        if dim not in review:
            raise ValueError(f"Missing dimension '{dim}' in review response")
        dim_data = review[dim]
        if not isinstance(dim_data, dict):
            raise ValueError(f"Dimension '{dim}' is not an object: {type(dim_data)}")
        score = dim_data.get("score")
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            raise ValueError(f"Invalid score for {dim}: {score}")

    return review


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_review_report(
    html_path: Path, html: str, review: dict,
) -> dict:
    """Build structured report dict."""
    model = MODEL_CHEAP if CHEAP_MODE else MODEL_DEFAULT

    scores = {}
    for dim in ("design", "ux", "content", "flow"):
        s = review[dim]["score"]
        scores[dim] = {
            "score": s,
            "grade": score_to_grade(s),
            "summary": review[dim].get("summary", ""),
            "strengths": review[dim].get("strengths", []),
            "weaknesses": review[dim].get("weaknesses", []),
        }

    avg = sum(scores[d]["score"] for d in scores) / 4
    avg = round(avg, 1)

    return {
        "file": str(html_path.relative_to(BASE_DIR)) if html_path.is_relative_to(BASE_DIR) else str(html_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "scores": scores,
        "overall": {
            "score": avg,
            "grade": score_to_grade(avg),
        },
        "fixes": review.get("fixes", []),
        "html_size_kb": round(len(html.encode("utf-8")) / 1024, 1),
    }


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------

# ANSI colors
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def sanitize_terminal(text: str) -> str:
    """Strip ANSI/OSC escape sequences from model output to prevent terminal injection."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b\[[0-9;]*m", "", text)


def grade_color(grade: str) -> str:
    """Color code for letter grade."""
    if grade == "A":
        return GREEN
    if grade in ("B", "C"):
        return YELLOW
    return RED


def progress_bar(score: int, width: int = 10) -> str:
    """Render a filled/empty progress bar."""
    filled = round(score * width / 10)
    return "\u2588" * filled + "\u2591" * (width - filled)


def print_terminal_summary(report: dict) -> None:
    """Print color-coded grade card to terminal."""
    print(f"\n{BOLD}=== HERMES WEBSITE REVIEW ==={RESET}")
    print(f"File: {report['file']} ({report['html_size_kb']} KB)\n")

    for dim in ("design", "ux", "content", "flow"):
        s = report["scores"][dim]
        color = grade_color(s["grade"])
        bar = progress_bar(s["score"])
        label = dim.upper().ljust(8)
        summary = sanitize_terminal(s.get("summary", ""))
        print(f"  {label} {color}{bar}  {s['score']}/10  {s['grade']}{RESET}  {DIM}{summary}{RESET}")

    overall = report["overall"]
    color = grade_color(overall["grade"])
    bar = progress_bar(overall["score"])
    print(f"\n  {BOLD}OVERALL  {color}{bar}  {overall['score']}/10  {overall['grade']}{RESET}")

    # Fixes
    fixes = report.get("fixes", [])
    critical_fixes = [f for f in fixes if f.get("severity") in ("critical", "high")]
    if critical_fixes:
        print(f"\n{BOLD}{RED}FIX THESE:{RESET}")
        for f in critical_fixes:
            dim = f.get("dimension", "?").upper()
            sev = f.get("severity", "?").upper()
            issue = sanitize_terminal(f.get("issue", ""))
            fix = sanitize_terminal(f.get("fix", ""))
            print(f"  {RED}[{dim}/{sev}]{RESET} {issue}")
            print(f"    {CYAN}{fix}{RESET}")

    medium_fixes = [f for f in fixes if f.get("severity") == "medium"]
    if medium_fixes:
        print(f"\n{BOLD}{YELLOW}IMPROVE:{RESET}")
        for f in medium_fixes:
            dim = f.get("dimension", "?").upper()
            issue = sanitize_terminal(f.get("issue", ""))
            fix = sanitize_terminal(f.get("fix", ""))
            print(f"  {YELLOW}[{dim}]{RESET} {issue} {DIM}-> {fix}{RESET}")

    print(f"\n{DIM}Model: {report['model']} | Report: review_report.json{RESET}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def review_website() -> dict:
    """Main review pipeline."""
    html_path = resolve_html_path(sys.argv)
    print(f"Reviewing: {html_path.name}")

    api_key = get_api_key()

    print("Screenshots:")
    ensure_playwright()
    desktop_b64, mobile_b64 = capture_screenshots(html_path)
    print(f"  Desktop: {len(desktop_b64) // 1024} KB (base64)")
    print(f"  Mobile:  {len(mobile_b64) // 1024} KB (base64)")

    html = html_path.read_text(encoding="utf-8")
    print(f"HTML: {len(html) // 1024} KB")

    raw_response = call_reviewer(desktop_b64, mobile_b64, html, api_key)
    review = parse_review(raw_response)

    report = build_review_report(html_path, html, review)
    REPORT_PATH.write_text(json.dumps(report, indent=2))

    print_terminal_summary(report)
    return report


if __name__ == "__main__":
    try:
        review_website()
    except Exception as e:
        # Only write error report if no valid report exists from this run
        if not REPORT_PATH.exists() or b'"scores"' not in REPORT_PATH.read_bytes():
            error = {"success": False, "error": str(e)}
            REPORT_PATH.write_text(json.dumps(error, indent=2))
        print(f"\n{RED}Error: {e}{RESET}")
        raise SystemExit(1)
