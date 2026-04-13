#!/usr/bin/env python3
"""Ground-truth eval for retarget-prospector detectors.

Runs each detector (pixel audit, Meta Ad Library, Google Ads Transparency,
LinkedIn Ads) against labelled entries in ground_truth.json and reports
precision / recall / false-positive-rate / unknown-rate per detector.

Gate (pipeline-blocking defaults):
    - false_positive_rate == 0
    - recall >= 0.80
    - unknown_rate <= 0.20

Distinguishes `unknown` (detector failure / auth miss) from `false`
(detector confidently says no). `unknown` never counts as a negative.

Usage:
    python3 validation/eval_detectors.py
    python3 validation/eval_detectors.py --only pixel
    python3 validation/eval_detectors.py --gate-strict
    python3 validation/eval_detectors.py --output validation/eval_report.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".claude/skills/ad-verification/scripts"))

from prospect_no_pixel import check_meta_ads  # noqa: E402
from audit_pixels_v2 import audit_one as audit_pixels_v2_one  # noqa: E402

GROUND_TRUTH = Path(__file__).resolve().parent / "ground_truth.json"
GATC_SCRIPT = BASE_DIR / ".claude/skills/ad-verification/scripts/check_google_ads_transparency.py"
LINKEDIN_SCRIPT = BASE_DIR / ".claude/skills/ad-verification/scripts/check_linkedin_ads.py"


# ---------------------------------------------------------------------------
# Detector wrappers — each returns one of {True, False, None}
# where None means "unknown" (scraper failure / auth miss / N/A label).
#
# Pixel detectors share a single rendered-browser pass, cached per-entry,
# so Stripe / HubSpot / Shopify are only visited once per eval run.
# ---------------------------------------------------------------------------


_PIXEL_CACHE: dict[str, dict[str, Any]] = {}
_PIXEL_CONTEXT = {"ctx": None, "browser": None, "pw": None}


def _pixel_context():
    if _PIXEL_CONTEXT["ctx"] is None:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
            locale="en-GB",
        )
        _PIXEL_CONTEXT.update(pw=pw, browser=browser, ctx=ctx)
    return _PIXEL_CONTEXT["ctx"]


def _shutdown_pixel_context():
    if _PIXEL_CONTEXT["ctx"]:
        try:
            _PIXEL_CONTEXT["ctx"].close()
            _PIXEL_CONTEXT["browser"].close()
            _PIXEL_CONTEXT["pw"].stop()
        except Exception:
            pass


def _audit_cached(entry: dict) -> dict[str, Any]:
    key = entry["domain"]
    if key in _PIXEL_CACHE:
        return _PIXEL_CACHE[key]
    candidate = {"website_url": entry["website"], "business_name": entry["name"]}
    ctx = _pixel_context()
    result = audit_pixels_v2_one(ctx, candidate)
    _PIXEL_CACHE[key] = result
    return result


def _pixel_field(entry: dict, field: str) -> bool | None:
    result = _audit_cached(entry)
    if result.get("status") != "ok":
        return None  # blocked / error / skipped → unknown, never false
    return bool(result.get(field))


def detect_fb_pixel(entry: dict) -> bool | None:
    return _pixel_field(entry, "facebook_pixel")


def detect_google_ads_tag(entry: dict) -> bool | None:
    return _pixel_field(entry, "google_ads_remarketing")


def detect_meta_ads(entry: dict) -> bool | None:
    result = check_meta_ads(entry["name"], country="GB")
    is_ad = result.get("is_advertiser")
    if is_ad is None:
        return None
    return bool(is_ad)


def detect_google_ads_active(entry: dict) -> bool | None:
    if not GATC_SCRIPT.exists():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(GATC_SCRIPT), entry["domain"], "--region", "GB"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data.get("has_google_ads")


def detect_linkedin_ads(entry: dict) -> bool | None:
    url = entry.get("linkedin_url")
    if not url:
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(LINKEDIN_SCRIPT), url],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data.get("has_linkedin_ads")


DETECTORS: dict[str, tuple[str, Callable[[dict], bool | None]]] = {
    "pixel_fb": ("has_fb_pixel", detect_fb_pixel),
    "pixel_gads": ("has_google_ads_tag", detect_google_ads_tag),
    "meta_library": ("has_meta_ads", detect_meta_ads),
    "gatc": ("has_google_ads_active", detect_google_ads_active),
    "linkedin": ("has_linkedin_ads", detect_linkedin_ads),
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass
class Metrics:
    tp: int = 0  # predicted true,  label true
    fp: int = 0  # predicted true,  label false  — the bug we hunt
    tn: int = 0  # predicted false, label false
    fn: int = 0  # predicted false, label true
    unknown_when_labelled: int = 0  # predicted None, label not None
    skipped_unlabelled: int = 0     # label is None — not evaluated
    samples: list[dict] = field(default_factory=list)

    @property
    def labelled(self) -> int:
        return self.tp + self.fp + self.tn + self.fn + self.unknown_when_labelled

    @property
    def recall(self) -> float:
        positives = self.tp + self.fn + sum(
            1 for s in self.samples if s["label"] is True and s["pred"] is None
        )
        return self.tp / positives if positives else 1.0

    @property
    def precision(self) -> float:
        called_pos = self.tp + self.fp
        return self.tp / called_pos if called_pos else 1.0

    @property
    def fp_rate(self) -> float:
        negatives = self.tn + self.fp
        return self.fp / negatives if negatives else 0.0

    @property
    def unknown_rate(self) -> float:
        return self.unknown_when_labelled / self.labelled if self.labelled else 0.0


def score(detector_name: str, label_key: str, fn: Callable[[dict], bool | None], entries: list[dict]) -> Metrics:
    m = Metrics()
    for entry in entries:
        label = entry["expected"].get(label_key)
        if label is None:
            m.skipped_unlabelled += 1
            continue
        try:
            pred = fn(entry)
        except Exception as e:
            pred = None
            m.samples.append({"name": entry["name"], "label": label, "pred": None, "error": str(e)[:120]})
        else:
            m.samples.append({"name": entry["name"], "label": label, "pred": pred})

        if pred is None:
            m.unknown_when_labelled += 1
        elif pred is True and label is True:
            m.tp += 1
        elif pred is True and label is False:
            m.fp += 1
        elif pred is False and label is False:
            m.tn += 1
        elif pred is False and label is True:
            m.fn += 1
    return m


def check_gate(m: Metrics, strict: bool) -> list[str]:
    errors: list[str] = []
    if m.fp_rate > 0:
        errors.append(f"fp_rate={m.fp_rate:.2f} > 0 (false positive — DO NOT ship)")
    recall_floor = 0.80
    unknown_ceiling = 0.20
    if strict:
        recall_floor, unknown_ceiling = 0.90, 0.10
    if m.labelled and m.recall < recall_floor:
        errors.append(f"recall={m.recall:.2f} < {recall_floor}")
    if m.unknown_rate > unknown_ceiling:
        errors.append(f"unknown_rate={m.unknown_rate:.2f} > {unknown_ceiling}")
    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="comma-separated detector names")
    parser.add_argument("--gate-strict", action="store_true", help="raise recall floor / tighten unknown ceiling")
    parser.add_argument("--output", default="", help="optional JSON report path")
    args = parser.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}

    gt = json.loads(GROUND_TRUTH.read_text())
    entries = gt["entries"]
    print(f"loaded {len(entries)} ground-truth entries")
    print()

    report: dict[str, Any] = {"detectors": {}, "gate_errors": {}, "gate_strict": args.gate_strict}
    overall_fail = False

    pixel_detectors = {"pixel_fb", "pixel_gads"}
    pixel_context_live = False
    for name, (label_key, fn) in DETECTORS.items():
        if only and name not in only:
            continue
        # Playwright sync contexts cannot coexist in one thread. Shut down the
        # pixel context before any non-pixel detector spins up its own browser.
        if name not in pixel_detectors and pixel_context_live:
            _shutdown_pixel_context()
            pixel_context_live = False
        if name in pixel_detectors:
            pixel_context_live = True
        print(f"=== {name} (label: {label_key}) ===")
        m = score(name, label_key, fn, entries)
        errors = check_gate(m, args.gate_strict)

        print(
            f"  labelled={m.labelled}  skipped={m.skipped_unlabelled}  "
            f"tp={m.tp} fp={m.fp} tn={m.tn} fn={m.fn} unknown={m.unknown_when_labelled}"
        )
        print(
            f"  precision={m.precision:.2f}  recall={m.recall:.2f}  "
            f"fp_rate={m.fp_rate:.2f}  unknown_rate={m.unknown_rate:.2f}"
        )
        if errors:
            overall_fail = True
            for e in errors:
                print(f"  [FAIL] {e}")
        else:
            print("  [ ok ] gate passed")
        print()

        report["detectors"][name] = {
            "labelled": m.labelled,
            "tp": m.tp,
            "fp": m.fp,
            "tn": m.tn,
            "fn": m.fn,
            "unknown": m.unknown_when_labelled,
            "precision": round(m.precision, 3),
            "recall": round(m.recall, 3),
            "fp_rate": round(m.fp_rate, 3),
            "unknown_rate": round(m.unknown_rate, 3),
            "samples": m.samples,
        }
        report["gate_errors"][name] = errors

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(f"report → {args.output}")

    _shutdown_pixel_context()

    if overall_fail:
        print("EVAL FAILED — retarget-prospector must NOT run against production prospects")
        return 1
    print("EVAL OK — all detectors pass gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
