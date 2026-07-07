#!/usr/bin/env python3
"""Compare baseline vs governed simulation results."""
import sys
import json

def analyze_simulation(log_file, name):
    with open(log_file) as f:
        logs = json.load(f)

    harvest_logs = [log for log in logs if log.get('action') == 'harvesting']

    print(f'=== {name} ===')
    print(f'Total harvests: {len(harvest_logs)}')
    print()

    # Show round-by-round
    rounds = {}
    for log in harvest_logs:
        round_num = log.get('round')
        if round_num not in rounds:
            rounds[round_num] = {
                'before': log.get('resource_in_pool_before_harvesting'),
                'after': log.get('resource_in_pool_after_harvesting'),
                'wanted': [],
                'collected': []
            }
        rounds[round_num]['wanted'].append(log.get('wanted_resource', 0))
        rounds[round_num]['collected'].append(log.get('resource_collected', 0))

    print('Round | Pool Before | Total Wanted | Total Collected | Pool After | Enforcement?')
    print('------|-------------|--------------|-----------------|------------|-------------')

    for round_num in sorted(rounds.keys()):
        r = rounds[round_num]
        total_wanted = sum(r['wanted'])
        total_collected = sum(r['collected'])
        enforced = '✓ YES' if total_wanted > total_collected else 'NO'
        print(f'{round_num:5} | {r["before"]:11.1f} | {total_wanted:12.1f} | {total_collected:15.1f} | {r["after"]:10.1f} | {enforced:11}')

    # Final verdict
    final = harvest_logs[-1]
    final_resource = final.get('resource_in_pool_after_harvesting', 0)

    print()
    print(f'Final resource: {final_resource} hectares')

    if final_resource == 0:
        print('VERDICT: ✗ COLLAPSED')
    elif final_resource >= 80:
        print('VERDICT: ✓ SURVIVED')
    else:
        print('VERDICT: ⚠ DEGRADED (stable but not optimal)')

    print()
    return final_resource

if __name__ == "__main__":
    baseline_log = "/claude-workspace/GovSim/simulation/results/sheep_v7.0/dummy-0rw0b20a/log_env.json"
    governed_log = "/claude-workspace/GovSim/simulation/results/sheep_governance_test/v7.0/dummy-kloa7f5t/log_env.json"

    print("=" * 80)
    print("GOVERNANCE VALIDATION: BASELINE vs GOVERNED")
    print("=" * 80)
    print()

    baseline_final = analyze_simulation(baseline_log, "BASELINE (NONE mode)")
    governed_final = analyze_simulation(governed_log, "GOVERNED (HARD mode)")

    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f'Baseline final resource: {baseline_final} hectares')
    print(f'Governed final resource: {governed_final} hectares')
    print(f'Improvement: {governed_final - baseline_final:+.1f} hectares')
    print()

    if baseline_final == 0 and governed_final > 0:
        print('✓ HYPOTHESIS CONFIRMED: Governance prevents collapse')
        print(f'  - Baseline: Complete collapse (0 hectares)')
        print(f'  - Governed: {"Survived" if governed_final >= 80 else "Stable"} ({governed_final} hectares)')
    else:
        print('⚠ HYPOTHESIS UNCLEAR: Review results')
