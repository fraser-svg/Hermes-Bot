#!/usr/bin/env python3
"""Hermes Full Pipeline — prospect → build → deploy → outreach.

End-to-end autonomous pipeline. Finds businesses, builds their websites,
deploys to Netlify, generates outreach emails with Stripe payment links,
queues for manual approval before sending.

Usage:
    python3 pipeline.py "electrician" "Edinburgh"
    python3 pipeline.py "plumber" "Glasgow" --limit 10 --top 3
    python3 pipeline.py "roofer" "Inverness" --send   # auto-approve (careful)

Requires in .env: GOOGLE_MAPS_API, openrouter, NETLIFY_AUTH_TOKEN,
                  SENDGRID_API_KEY, STRIPE_SECRET_KEY
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
REPORT_PATH = BASE_DIR / "build_report.json"
OUTPUT_DIR = BASE_DIR / "output"


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python3 pipeline.py <category> <city> [--limit N] [--top N] [--send]")
        print('Example: python3 pipeline.py "electrician" "Edinburgh"')
        return 1

    category = args[0]
    city = args[1]
    limit = 20
    top_n = 5
    auto_send = "--send" in args

    i = 2
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--top" and i + 1 < len(args):
            top_n = int(args[i + 1])
            i += 2
        else:
            i += 1

    print("=" * 60)
    print("  HERMES FULL PIPELINE")
    print(f"  {category} in {city} | top {top_n}")
    print("=" * 60)

    # ---------------------------------------------------------------
    # STEP 1: Prospect
    # ---------------------------------------------------------------
    print("\n--- STEP 1: PROSPECT ---\n")

    from prospect import prospect, save_prospects
    prospects = prospect(category, city, limit)

    if not prospects:
        print("No prospects found.")
        return 0

    save_prospects(prospects, category, city)

    # Sort by opportunity (rating * reviews)
    prospects.sort(
        key=lambda x: (x.get("rating", 0) * x.get("review_count", 0)),
        reverse=True,
    )
    to_build = prospects[:top_n]
    print(f"\nTop {len(to_build)} prospects selected for build.\n")

    # ---------------------------------------------------------------
    # STEP 2: Build
    # ---------------------------------------------------------------
    print("--- STEP 2: BUILD ---\n")

    built_files: list[Path] = []

    for idx, biz in enumerate(to_build):
        name = biz["business_name"]
        print(f"[{idx + 1}/{len(to_build)}] Building: {name}")

        DETAILS_PATH.parent.mkdir(exist_ok=True)
        DETAILS_PATH.write_text(json.dumps(biz, indent=2))

        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "generate.py")],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            timeout=180,
        )

        if REPORT_PATH.exists():
            report = json.loads(REPORT_PATH.read_text())
            output_file = report.get("output_file", "")
            score = report.get("validation", {}).get("score", "?")
            success = report.get("success", False)
            print(f"  Score: {score} | {'PASS' if success else 'FAIL'}")
            if output_file and success:
                built_files.append(Path(output_file))
        else:
            print(f"  FAIL: no build report")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")

    if not built_files:
        print("\nNo sites built successfully.")
        return 1

    print(f"\n{len(built_files)} sites built.\n")

    # ---------------------------------------------------------------
    # STEP 3: Deploy
    # ---------------------------------------------------------------
    print("--- STEP 3: DEPLOY ---\n")

    from deploy import deploy_one, load_deploy_log, save_deploy_log, get_netlify_token

    try:
        netlify_token = get_netlify_token()
    except RuntimeError as e:
        print(f"Deploy skipped: {e}")
        print("Add NETLIFY_AUTH_TOKEN to .env to enable deploys.")
        return 0

    deploys = load_deploy_log()

    for html_path in built_files:
        if not html_path.exists():
            # Try output dir
            html_path = OUTPUT_DIR / html_path.name
        if html_path.exists():
            print(f"[{html_path.name}]")
            deploy_one(html_path, netlify_token, deploys)

    save_deploy_log(deploys)
    print(f"\n{len(built_files)} sites deployed.\n")

    # ---------------------------------------------------------------
    # STEP 4: Outreach
    # ---------------------------------------------------------------
    print("--- STEP 4: OUTREACH ---\n")

    from outreach import process_all

    process_all(preview_only=not auto_send)

    if not auto_send:
        print("\nEmails queued. Review prospects/outreach.json")
        print("When ready: python3 outreach.py --send <slug>")
    else:
        print("\nEmails sent (auto-approve mode).")

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Prospects found: {len(prospects)}")
    print(f"  Sites built: {len(built_files)}")
    print(f"  Sites deployed: {len(built_files)}")
    print(f"  Outreach: {'SENT' if auto_send else 'QUEUED (review + approve)'}")
    print()
    print("Next steps:")
    print("  1. Review outreach.json — check email quality")
    print("  2. Add contact emails where missing")
    print("  3. python3 outreach.py --send <slug>")
    print("  4. Start webhook server: python3 webhook_server.py")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
