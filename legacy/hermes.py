"""Hermes - Website Generation Agent.

Chat interface powered by GPT. Understands natural language commands
and routes ALL work through the proper pipeline:
  - prospect.py for finding businesses
  - generate.py for building websites

GPT NEVER generates HTML directly. It only talks to the user and
decides which scripts to run.

Usage:
    python3 hermes.py
    python3 hermes.py --auto
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
PROSPECTS_DIR = BASE_DIR / "prospects"
REPORT_PATH = BASE_DIR / "build_report.json"
OUTPUT_DIR = BASE_DIR / "output"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HERMES_MODEL = "openai/gpt-4.1-mini"

SYSTEM_PROMPT = """\
You are Hermes, a website generation agent. You help users find local service \
businesses that need websites and build them.

YOU CANNOT BUILD WEBSITES YOURSELF. You are the brain, not the builder. \
When the user wants something done, you output a COMMAND that the system executes.

## COMMANDS YOU CAN OUTPUT

To trigger an action, output EXACTLY one of these on its own line. \
The system will detect it and run the right script.

### Find businesses without websites:
```
CMD:PROSPECT category="electrician" location="Edinburgh" limit=10
```

### Build a website for a specific prospect (by number from prospect results):
```
CMD:BUILD_PROSPECT 1
```

### Build websites for ALL prospects found:
```
CMD:BUILD_ALL
```

### Build from manually provided business details:
```
CMD:BUILD_MANUAL
{json business details here}
```

### Open the latest website in the browser:
```
CMD:PREVIEW
```

## RULES

1. When the user asks to "find" or "search" businesses, output CMD:PROSPECT.
2. When the user asks to "build" or "make" websites for prospects, output CMD:BUILD_ALL or CMD:BUILD_PROSPECT N.
3. When the user gives you business details directly, output CMD:BUILD_MANUAL with the JSON.
4. NEVER try to generate HTML, CSS, or website code yourself. You literally cannot.
5. Keep your responses short. The user wants results, not essays.
6. After a command runs, the system will show you the results. Summarize them for the user.
7. If the user asks to find businesses AND build websites in one request, \
output CMD:PROSPECT first. After seeing results, output CMD:BUILD_ALL.

## CATEGORIES
electrician, plumber, roofer, hvac, cleaner, painter, locksmith, mover, pest control, landscaper

## EXAMPLE CONVERSATION

User: find me 5 electricians in edinburgh without websites
You: CMD:PROSPECT category="electrician" location="Edinburgh" limit=5

[system shows prospect results]

You: Found 3 electricians in Edinburgh without a website:
1. Spark Brothers - 4.9/5, 23 reviews
2. Murray Electrical - 4.7/5, 8 reviews
3. Capital Sparks - 4.5/5, 12 reviews

Want me to build websites for all of them?

User: yes build them all
You: CMD:BUILD_ALL

[system builds each site]

You: Done! Built 3 websites:
- spark-brothers.html (15/15, readability PASS)
- murray-electrical.html (15/15, readability PASS)
- capital-sparks.html (14/15, 1 readability warning)
"""


def load_env() -> dict[str, str]:
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
    key = os.environ.get("OPENROUTER_API_KEY") or load_env().get("openrouter")
    if not key:
        raise RuntimeError("No OpenRouter API key. Set OPENROUTER_API_KEY or add 'openrouter' to .env")
    return key


def call_gpt(messages: list[dict], api_key: str) -> str:
    """Send messages to GPT via OpenRouter."""
    payload = json.dumps({
        "model": HERMES_MODEL,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.3,
    }).encode("utf-8")

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://hermes-bot.local",
            "X-Title": "Hermes Agent",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"OpenRouter error {e.code}: {error_body}") from e

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"No response: {json.dumps(body)}")
    return choices[0]["message"]["content"]


# ── Command Handlers ──────────────────────────────────────────────

# Holds the last set of prospects so BUILD_ALL / BUILD_PROSPECT can use them
_last_prospects: list[dict] = []


def handle_prospect(args: str) -> str:
    """Run prospect.py and return results as text."""
    global _last_prospects

    # Parse args like: category="electrician" location="Edinburgh" limit=10
    category = re.search(r'category="([^"]+)"', args)
    location = re.search(r'location="([^"]+)"', args)
    limit_match = re.search(r'limit=(\d+)', args)

    if not category or not location:
        return "ERROR: CMD:PROSPECT needs category and location. Example: CMD:PROSPECT category=\"electrician\" location=\"Edinburgh\""

    cat = category.group(1)
    loc = location.group(1)
    limit = int(limit_match.group(1)) if limit_match else 10

    try:
        from prospect import prospect, save_prospects
        prospects = prospect(cat, loc, limit)
        _last_prospects = prospects
        save_prospects(prospects, cat, loc)
    except Exception as e:
        return f"ERROR running prospector: {e}"

    if not prospects:
        return f"No businesses found in {loc} without a website for category '{cat}'."

    lines = [f"Found {len(prospects)} {cat}(s) in {loc} WITHOUT a website:\n"]
    for i, biz in enumerate(prospects):
        stars = f"{biz['rating']}/5" if biz.get('rating') else "no rating"
        reviews = f"{biz['review_count']} reviews" if biz.get('review_count') else "no reviews"
        phone = biz.get('phone_number') or 'no phone'
        lines.append(f"  [{i+1}] {biz['business_name']}")
        lines.append(f"      {stars} | {reviews} | {phone}")
        lines.append(f"      {biz.get('address', '')}")
        lines.append("")

    return "\n".join(lines)


def build_one(details: dict) -> dict:
    """Save details and run generate.py. Returns build report."""
    DETAILS_PATH.parent.mkdir(exist_ok=True)
    DETAILS_PATH.write_text(json.dumps(details, indent=2))

    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "generate.py")],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
        timeout=180,
    )

    if REPORT_PATH.exists():
        return json.loads(REPORT_PATH.read_text())
    return {"success": False, "error": result.stderr or "No report generated"}


def handle_build_prospect(args: str) -> str:
    """Build a website for a specific prospect by index."""
    try:
        idx = int(args.strip()) - 1
    except ValueError:
        return "ERROR: CMD:BUILD_PROSPECT needs a number. Example: CMD:BUILD_PROSPECT 1"

    if not _last_prospects:
        return "ERROR: No prospects loaded. Run CMD:PROSPECT first."
    if idx < 0 or idx >= len(_last_prospects):
        return f"ERROR: Pick a number between 1 and {len(_last_prospects)}."

    biz = _last_prospects[idx]
    print(f"\n⚡ Building website for: {biz['business_name']}")
    report = build_one(biz)
    return format_report(report)


def handle_build_all(_args: str) -> str:
    """Build websites for all prospects."""
    if not _last_prospects:
        return "ERROR: No prospects loaded. Run CMD:PROSPECT first."

    results = []
    for i, biz in enumerate(_last_prospects):
        print(f"\n⚡ [{i+1}/{len(_last_prospects)}] Building: {biz['business_name']}")
        report = build_one(biz)

        # Copy output to unique file (generate.py overwrites index.html each time)
        slug = re.sub(r"[^a-z0-9]+", "-", biz["business_name"].lower()).strip("-")
        output_file = OUTPUT_DIR / f"{slug}.html"

        score = report.get("validation", {}).get("score", "?")
        readability = "PASS" if report.get("readability", {}).get("pass") else "WARNINGS"
        results.append({
            "name": biz["business_name"],
            "file": str(output_file),
            "score": score,
            "readability": readability,
            "success": report.get("success", False),
        })

    lines = [f"Built {len(results)} websites:\n"]
    for r in results:
        status = "OK" if r["success"] else "FAILED"
        lines.append(f"  - {r['name']}: {r['score']} | Readability: {r['readability']} | {status}")
        lines.append(f"    File: {r['file']}")
    return "\n".join(lines)


def handle_build_manual(args: str) -> str:
    """Build from JSON provided inline."""
    try:
        # Find JSON in the args
        json_match = re.search(r"\{.*\}", args, re.DOTALL)
        if not json_match:
            return "ERROR: No JSON found. Include business details as JSON."
        details = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON: {e}"

    required = ["business_name", "business_category", "city", "phone_number"]
    missing = [f for f in required if not details.get(f)]
    if missing:
        return f"ERROR: Missing required fields: {', '.join(missing)}"

    print(f"\n⚡ Building website for: {details['business_name']}")
    report = build_one(details)
    return format_report(report)


def handle_preview(_args: str) -> str:
    """Open the latest build in the browser."""
    index_html = BASE_DIR / "index.html"
    if not index_html.exists():
        return "No website built yet. Nothing to preview."

    import platform
    if platform.system() == "Darwin":
        subprocess.run(["open", str(index_html)])
    elif platform.system() == "Linux":
        subprocess.run(["xdg-open", str(index_html)])
    else:
        subprocess.run(["start", str(index_html)], shell=True)

    return f"Opened {index_html} in browser."


def format_report(report: dict) -> str:
    """Format a build report as text for GPT to summarize."""
    if not report.get("success"):
        return f"BUILD FAILED: {report.get('error', 'Unknown error')}"

    score = report.get("validation", {}).get("score", "?")
    persona = report.get("persona", "?")
    size = report.get("html_size_kb", "?")
    output = report.get("output_file", "?")
    warnings = report.get("readability", {}).get("warnings", [])

    lines = [
        f"BUILD COMPLETE: {score} validation score",
        f"Persona: {persona}",
        f"Size: {size}KB",
        f"Output: {output}",
    ]
    if warnings:
        lines.append(f"READABILITY WARNINGS ({len(warnings)}):")
        for w in warnings:
            lines.append(f"  - {w}")
    else:
        lines.append("Readability: PASS")

    return "\n".join(lines)


# ── Command Router ────────────────────────────────────────────────

COMMAND_HANDLERS = {
    "PROSPECT": handle_prospect,
    "BUILD_PROSPECT": handle_build_prospect,
    "BUILD_ALL": handle_build_all,
    "BUILD_MANUAL": handle_build_manual,
    "PREVIEW": handle_preview,
}


def extract_and_run_commands(response: str) -> str | None:
    """Check if GPT's response contains a CMD: command. Run it if found."""
    for line in response.split("\n"):
        line = line.strip().strip("`")
        if line.startswith("CMD:"):
            # Parse: CMD:COMMAND_NAME args...
            parts = line[4:].strip().split(None, 1)
            cmd_name = parts[0] if parts else ""
            cmd_args = parts[1] if len(parts) > 1 else ""

            handler = COMMAND_HANDLERS.get(cmd_name)
            if handler:
                print(f"\n[Hermes executing: {cmd_name}]")
                return handler(cmd_args)
            else:
                return f"Unknown command: {cmd_name}. Available: {', '.join(COMMAND_HANDLERS.keys())}"

    # Check for multi-line BUILD_MANUAL (JSON might be on next lines)
    if "CMD:BUILD_MANUAL" in response:
        # Everything after CMD:BUILD_MANUAL is the JSON
        idx = response.index("CMD:BUILD_MANUAL")
        remainder = response[idx + len("CMD:BUILD_MANUAL"):]
        return handle_build_manual(remainder)

    return None


# ── Main Loop ─────────────────────────────────────────────────────

def auto_build():
    """Skip chat, build from existing business_details.json."""
    if not DETAILS_PATH.exists():
        print("No business_details.json found. Run without --auto to collect details.")
        sys.exit(1)

    details = json.loads(DETAILS_PATH.read_text())
    print(f"Building website for: {details.get('business_name', 'Unknown')}")
    report = build_one(details)
    print(format_report(report))


def chat_mode():
    """Interactive chat with command execution."""
    api_key = get_api_key()

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("=" * 50)
    print("  HERMES - Website Builder")
    print("=" * 50)
    print("  Commands I understand:")
    print("  - Find businesses: 'find electricians in Edinburgh'")
    print("  - Build websites:  'build them all'")
    print("  - Manual build:    give me business details")
    print("  - Preview:         'show me the website'")
    print("  - Quit:            'quit'")
    print("=" * 50)

    # Get initial greeting
    messages.append({"role": "user", "content": "Hello, I'm ready to work."})
    greeting = call_gpt(messages, api_key)
    messages.append({"role": "assistant", "content": greeting})

    # Check if greeting contains a command (it shouldn't, but just in case)
    cmd_result = extract_and_run_commands(greeting)
    if cmd_result:
        print(f"\n{cmd_result}")
    else:
        print(f"\nHermes: {greeting}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        messages.append({"role": "user", "content": user_input})

        # Get GPT's response
        response = call_gpt(messages, api_key)
        messages.append({"role": "assistant", "content": response})

        # Check for commands in the response
        cmd_result = extract_and_run_commands(response)

        if cmd_result:
            # GPT issued a command - show the command result
            # Also strip the CMD: line from what we show the user
            clean_response = re.sub(r"```?\s*CMD:.*?```?", "", response, flags=re.DOTALL).strip()
            if clean_response:
                print(f"\nHermes: {clean_response}")

            print(f"\n{cmd_result}")

            # Feed the result back to GPT so it can summarize
            messages.append({
                "role": "system",
                "content": f"Command result:\n{cmd_result}\n\nSummarize this for the user. Be brief."
            })
            summary = call_gpt(messages, api_key)
            messages.append({"role": "assistant", "content": summary})
            print(f"\nHermes: {summary}\n")
        else:
            # No command - just show GPT's response
            print(f"\nHermes: {response}\n")


def main():
    if "--auto" in sys.argv:
        auto_build()
    else:
        chat_mode()


if __name__ == "__main__":
    main()
