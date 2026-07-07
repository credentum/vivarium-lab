#!/usr/bin/env python3
"""
Analyze governance validation experiment results.

Extracts final resource levels from baseline vs governed trials.
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_results():
    results_dir = Path("simulation/results/sheep_v7.0")

    if not results_dir.exists():
        print(f"⚠ Results directory not found: {results_dir}")
        print("Run experiments first: bash run_validation_experiments.sh")
        return

    baseline_results = []
    governed_results = []

    for run_dir in sorted(results_dir.iterdir()):
        if not run_dir.is_dir():
            continue

        log_file = run_dir / "log_env.json"
        config_file = run_dir / ".hydra/config.yaml"

        if not log_file.exists():
            continue

        # Load config to check governance mode
        config_text = ""
        if config_file.exists():
            with open(config_file) as f:
                config_text = f.read()

        # Load simulation log
        with open(log_file) as f:
            logs = json.load(f)

        if not logs:
            continue

        # Extract final resource level
        final_resource = logs[-1].get("resource_in_pool_after_harvesting", 0)
        num_rounds = max(log.get("round", 0) for log in logs)

        # Classify as baseline or governed
        if "governance_test" in str(run_dir) or "mode: hard" in config_text.lower():
            governed_results.append({
                "run": run_dir.name,
                "final_resource": final_resource,
                "rounds": num_rounds
            })
        else:
            baseline_results.append({
                "run": run_dir.name,
                "final_resource": final_resource,
                "rounds": num_rounds
            })

    # Print summary
    print("=" * 60)
    print("GOVERNANCE VALIDATION RESULTS")
    print("=" * 60)
    print()

    print("BASELINE (NONE mode) - Expected: Collapse")
    print("-" * 60)
    if baseline_results:
        for result in baseline_results:
            status = "✗ COLLAPSED" if result["final_resource"] < 20 else "✓ SURVIVED"
            print(f"  {result['run'][:40]:<40} | {status} | Final: {result['final_resource']} hectares")

        avg_baseline = sum(r["final_resource"] for r in baseline_results) / len(baseline_results)
        collapse_count = sum(1 for r in baseline_results if r["final_resource"] < 20)
        print(f"\n  Average final resource: {avg_baseline:.1f} hectares")
        print(f"  Collapsed: {collapse_count}/{len(baseline_results)} runs")
    else:
        print("  ⚠ No baseline results found")

    print()
    print("GOVERNED (HARD mode) - Expected: Survival")
    print("-" * 60)
    if governed_results:
        for result in governed_results:
            status = "✓ SURVIVED" if result["final_resource"] >= 80 else "⚠ DEGRADED"
            print(f"  {result['run'][:40]:<40} | {status} | Final: {result['final_resource']} hectares")

        avg_governed = sum(r["final_resource"] for r in governed_results) / len(governed_results)
        survived_count = sum(1 for r in governed_results if r["final_resource"] >= 80)
        print(f"\n  Average final resource: {avg_governed:.1f} hectares")
        print(f"  Survived: {survived_count}/{len(governed_results)} runs")
    else:
        print("  ⚠ No governed results found")

    print()
    print("=" * 60)
    print("CONCLUSION")
    print("=" * 60)

    if baseline_results and governed_results:
        avg_baseline = sum(r["final_resource"] for r in baseline_results) / len(baseline_results)
        avg_governed = sum(r["final_resource"] for r in governed_results) / len(governed_results)
        collapse_count = sum(1 for r in baseline_results if r["final_resource"] < 20)
        survived_count = sum(1 for r in governed_results if r["final_resource"] >= 80)

        improvement = avg_governed - avg_baseline
        print(f"Governance improved final resource by {improvement:.1f} hectares")
        print(f"  ({avg_baseline:.1f} → {avg_governed:.1f})")

        baseline_collapse_rate = collapse_count / len(baseline_results) * 100
        governed_survive_rate = survived_count / len(governed_results) * 100

        print(f"\nBaseline collapse rate: {baseline_collapse_rate:.0f}%")
        print(f"Governed survival rate: {governed_survive_rate:.0f}%")

        if governed_survive_rate >= 80 and baseline_collapse_rate >= 60:
            print("\n✓ HYPOTHESIS CONFIRMED: Governance prevents collapse")
        else:
            print("\n⚠ HYPOTHESIS UNCLEAR: Results need investigation")
    else:
        print("⚠ Insufficient data for comparison")
        if not baseline_results:
            print("  - Missing baseline trials")
        if not governed_results:
            print("  - Missing governed trials")

if __name__ == "__main__":
    analyze_results()
