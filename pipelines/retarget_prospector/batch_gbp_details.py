#!/usr/bin/env python3
"""Fetch Google Places API Details for prospects (gated).

Input: _workspace/retarget_scotland/scotland_prospects.json
Output: _workspace/retarget_scotland/scotland_prospects_gbp_details.json

Each row must have `place_id` (or we extract from google_maps_url where possible).
If no place_id, we resolve via Places Text Search first.

Budget cap: --max-calls flag (default 400). Prints running cost estimate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from prospect_no_pixel import load_env  # noqa: E402

PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join([
    "id",
    "displayName",
    "primaryType",
    "primaryTypeDisplayName",
    "types",
    "formattedAddress",
    "nationalPhoneNumber",
    "internationalPhoneNumber",
    "websiteUri",
    "regularOpeningHours",
    "editorialSummary",
    "userRatingCount",
    "rating",
    "reviews",
    "photos",
    "businessStatus",
    "paymentOptions",
    "parkingOptions",
    "accessibilityOptions",
])

SEARCH_FIELD_MASK = "places.id,places.displayName,places.formattedAddress"

# Pricing (Jan 2026 Google Places API New): Place Details (Advanced) ~$0.017/call.
COST_PER_CALL = 0.017


def _api_key(env: dict) -> str:
    return (
        os.environ.get("GOOGLE_PLACES_API_KEY")
        or os.environ.get("GOOGLE_MAPS_API")
        or env.get("GOOGLE_PLACES_API_KEY")
        or env.get("GOOGLE_MAPS_API")
        or ""
    )


def resolve_place_id(name: str, address: str, key: str) -> str | None:
    query = f"{name} {address}".strip()
    if not query:
        return None
    body = json.dumps({"textQuery": query, "regionCode": "GB"}).encode()
    req = Request(
        PLACES_SEARCH_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": SEARCH_FIELD_MASK,
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"  search error for {name!r}: {e}", file=sys.stderr)
        return None
    places = data.get("places") or []
    if not places:
        return None
    return places[0].get("id")


def fetch_details(place_id: str, key: str) -> tuple[dict | None, str | None]:
    url = PLACES_DETAILS_URL.format(place_id=quote(place_id, safe=""))
    req = Request(
        url,
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELD_MASK},
    )
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode()), None
    except HTTPError as e:
        return None, f"http {e.code}: {e.read()[:160]!r}"
    except URLError as e:
        return None, f"network: {e}"


def extract_place_id_from_maps_url(url: str) -> str | None:
    if not url:
        return None
    # cid= is not a place_id, but can try the !1s token or ChIJ token
    m = re.search(r"(ChIJ[A-Za-z0-9_\-]+)", url)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="_workspace/retarget_scotland/scotland_prospects.json")
    ap.add_argument("--output", default="_workspace/retarget_scotland/scotland_prospects_gbp_details.json")
    ap.add_argument("--max-calls", type=int, default=400, help="Budget cap")
    ap.add_argument("--probe", action="store_true", help="Single-row probe call and exit")
    args = ap.parse_args()

    env = load_env()
    key = _api_key(env)
    if not key:
        print("FAIL: no GOOGLE_PLACES_API_KEY / GOOGLE_MAPS_API in env", file=sys.stderr)
        return 2

    inp = Path(args.input)
    out = Path(args.output)
    rows = json.loads(inp.read_text())

    if args.probe:
        rows = rows[:1]
        print(f"PROBE mode — {len(rows)} row", file=sys.stderr)

    calls = 0
    search_calls = 0
    results = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for i, row in enumerate(rows, 1):
        if calls >= args.max_calls:
            print(f"budget cap reached ({calls} details calls)", file=sys.stderr)
            row["gbp_details_error"] = "budget_cap"
            results.append(row)
            continue
        place_id = row.get("place_id") or extract_place_id_from_maps_url(row.get("google_maps_url", ""))
        if not place_id:
            pid = resolve_place_id(row.get("business_name", ""), row.get("address", ""), key)
            search_calls += 1
            if not pid:
                row["gbp_details_error"] = "no_place_id"
                row["gbp_details_checked_at"] = now
                results.append(row)
                continue
            place_id = pid
        details, err = fetch_details(place_id, key)
        calls += 1
        row["place_id"] = place_id
        if err:
            row["gbp_details_error"] = err
        else:
            row["gbp_details"] = details
        row["gbp_details_checked_at"] = now
        results.append(row)
        if i % 25 == 0:
            print(f"[{i}/{len(rows)}] details_calls={calls} search_calls={search_calls} est_cost=${calls*COST_PER_CALL:.2f}", file=sys.stderr)

    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}", file=sys.stderr)
    print(f"details_calls={calls} search_calls={search_calls} est_cost=${calls*COST_PER_CALL:.2f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
