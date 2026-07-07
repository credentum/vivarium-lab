#!/usr/bin/env python3
"""Extract resource trajectory from simulation logs."""
import sys
import json

log_file = sys.argv[1] if len(sys.argv) > 1 else "log_env.json"

with open(log_file) as f:
    logs = json.load(f)

# Get harvest actions only
harvest_logs = [log for log in logs if log.get('action') == 'harvesting']

print('=== SIMULATION RESULTS ===')
print(f'Total harvest actions: {len(harvest_logs)}')
print()
print('Round-by-round resource levels:')
print('Round | Before Harvest | After Harvest | Total Harvested')
print('------|----------------|---------------|----------------')

for log in harvest_logs:
    round_num = log.get('round', 'N/A')
    before = log.get('resource_in_pool_before_harvesting', 'N/A')
    after = log.get('resource_in_pool_after_harvesting', 'N/A')
    if before != 'N/A' and after != 'N/A':
        harvested = before - after
        print(f'{round_num:5} | {before:14} | {after:13} | {harvested:15}')

# Find final state
if harvest_logs:
    final = harvest_logs[-1]
    print()
    print('=== FINAL STATE ===')
    print(f'Final round: {final.get("round")}')
    print(f'Final resource pool: {final.get("resource_in_pool_after_harvesting")} hectares')

    # Determine verdict
    final_resource = final.get("resource_in_pool_after_harvesting", 0)
    if final_resource < 20:
        print(f'VERDICT: ✗ COLLAPSED (resource dropped to {final_resource})')
    elif final_resource >= 80:
        print(f'VERDICT: ✓ SURVIVED (resource maintained at {final_resource})')
    else:
        print(f'VERDICT: ⚠ DEGRADED (resource at {final_resource}, not collapsed but not thriving)')
