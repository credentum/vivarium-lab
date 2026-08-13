#!/usr/bin/env python3
"""Apply the pre-registered empirical ambiguity gate to a completed run's
Control-condition data (README.md fix #2).

The rule was written before any data existed; only its *application* -- which
items pass or fail -- happens after the Control panels run. This decides
which items are trustworthy for the NEXT (confirmatory) item bank. It does
not change this pilot's own AUROC verdict.
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"

AMBIGUOUS_MAX_AGREEMENT = 0.80  # ambiguous items must score BELOW this on Control
CLEAR_MIN_AGREEMENT = 0.90      # clear items must score ABOVE this on Control, AND be correct


def latest_results_file() -> Path:
    files = sorted(RESULTS_DIR.glob("results_*.json"))
    if not files:
        raise FileNotFoundError(f"no results files found in {RESULTS_DIR}")
    return files[-1]


def load_control_panels(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return [p for p in data["panels"] if p["condition"] == "control"]


def apply_gate(control_panels: list[dict]) -> dict:
    results = {"passed": [], "failed": []}
    for panel in control_panels:
        bucket = panel["bucket"]
        agreement = panel["agreement_fraction"]
        correct = panel["majority_correct"]

        if bucket == "ambiguous":
            passed = agreement < AMBIGUOUS_MAX_AGREEMENT
            reason = f"agreement={agreement:.2f} {'<' if passed else '>='} {AMBIGUOUS_MAX_AGREEMENT}"
        else:  # clear
            passed = agreement > CLEAR_MIN_AGREEMENT and correct
            reason = f"agreement={agreement:.2f}, correct={correct}"

        entry = {
            "item_id": panel["item_id"], "bucket": bucket, "agreement": agreement,
            "correct": correct, "reason": reason,
        }
        (results["passed"] if passed else results["failed"]).append(entry)

    return results


def main():
    parser = argparse.ArgumentParser(description="Apply the pre-registered item-bank ambiguity gate")
    parser.add_argument("--file", type=Path, help="results JSON file (default: latest in data/results/)")
    args = parser.parse_args()

    path = args.file or latest_results_file()
    print(f"Applying ambiguity gate to: {path}")
    print(f"  ambiguous items must score Control agreement < {AMBIGUOUS_MAX_AGREEMENT}")
    print(f"  clear items must score Control agreement > {CLEAR_MIN_AGREEMENT} AND be correct")
    print()

    control_panels = load_control_panels(path)
    results = apply_gate(control_panels)

    print(f"PASSED ({len(results['passed'])}):")
    for e in results["passed"]:
        print(f"  {e['item_id']:12s} [{e['bucket']:9s}] {e['reason']}")

    print(f"\nFAILED ({len(results['failed'])}) -- exclude from next item bank:")
    for e in results["failed"]:
        print(f"  {e['item_id']:12s} [{e['bucket']:9s}] {e['reason']}")

    print(f"\n{len(results['passed'])}/{len(control_panels)} items passed the gate.")


if __name__ == "__main__":
    main()
