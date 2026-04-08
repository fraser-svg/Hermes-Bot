"""Hermes Pipeline Runner - No AI brain needed.

Finds businesses without websites and builds them sites.
Runs prospect.py then generate.py for each prospect.
No GPT involved. Just execution.

Usage:
    python3 run.py "electrician" "Edinburgh"
    python3 run.py "plumber" "Glasgow" --limit 10
    python3 run.py "roofer" "Inverness" --top 3
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
REPORT_PATH = BASE_DIR / "build_report.json"
OUTPUT_DIR = BASE_DIR / "output"


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python3 run.py <category> <city> [--limit N] [--top N]")
        print("Example: python3 run.py \"electrician\" \"Edinburgh\"")
        sys.exit(1)

    category = args[0]
    city = args[1]
    limit = 20
    top_n = 99  # build all by default

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

    # Step 1: Find prospects
    print("=" * 60)
    print(f"  HERMES PIPELINE: {category} in {city}")
    print("=" * 60)

    from prospect import prospect, save_prospects
    prospects = prospect(category, city, limit)

    if not prospects:
        print("\nNo prospects found. Every business has a website.")
        sys.exit(0)

    save_prospects(prospects, category, city)

    # Sort by rating * review_count (best prospects first)
    prospects.sort(
        key=lambda x: (x.get("rating", 0) * x.get("review_count", 0)),
        reverse=True,
    )

    # Limit to top N
    to_build = prospects[:top_n]
    print(f"\nBuilding websites for {len(to_build)} prospects...\n")

    # Step 2: Build each one
    results = []
    for i, biz in enumerate(to_build):
        name = biz["business_name"]
        print(f"[{i+1}/{len(to_build)}] {name}")
        print(f"  {biz.get('rating', '?')}/5 | {biz.get('review_count', '?')} reviews | {biz.get('phone_number', 'no phone')}")

        # Save details
        DETAILS_PATH.write_text(json.dumps(biz, indent=2))

        # Run generate.py
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "generate.py")],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            timeout=180,
        )

        if REPORT_PATH.exists():
            report = json.loads(REPORT_PATH.read_text())
        else:
            report = {"success": False, "error": result.stderr}

        score = report.get("validation", {}).get("score", "FAIL")
        readability = "PASS" if report.get("readability", {}).get("pass") else "WARN"
        output_file = report.get("output_file", "?")

        status = "OK" if report.get("success") else "FAIL"
        print(f"  -> {score} | Readability: {readability} | {status}")
        print(f"  -> {output_file}\n")

        results.append({
            "name": name,
            "score": score,
            "readability": readability,
            "file": output_file,
            "success": report.get("success", False),
            "phone": biz.get("phone_number", ""),
            "rating": biz.get("rating", 0),
            "reviews": biz.get("review_count", 0),
            "maps_url": biz.get("google_maps_url", ""),
        })

    # Step 3: Summary
    print("=" * 60)
    print("  BUILD SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["success"])
    print(f"  Built: {passed}/{len(results)} websites")
    print()
    for r in results:
        flag = "PASS" if r["success"] else "FAIL"
        print(f"  [{flag}] {r['name']}")
        print(f"        {r['score']} | Readability: {r['readability']}")
        print(f"        Phone: {r['phone']} | {r['rating']}/5 ({r['reviews']} reviews)")
        print(f"        File: {r['file']}")
        if r.get("maps_url"):
            print(f"        Maps: {r['maps_url']}")
        print()

    # Save summary
    summary_path = BASE_DIR / "prospects" / f"{category}-{city.lower().replace(' ', '-')}-builds.json"
    summary_path.parent.mkdir(exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2))
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
