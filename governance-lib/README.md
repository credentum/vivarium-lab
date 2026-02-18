# governance-lib

Empirically validated governance functions for multi-agent resource coordination. Every function returns a computed answer — not raw data — because agents cannot derive governance norms from raw information. This was tested: giving LLM agents all the inputs but no computed answer achieved 0% survival, identical to no information at all. Giving them the computed number achieved 80% survival. The computed answer is the active ingredient.

## Installation

Copy the `governance-lib/` directory into your project, or add it to your Python path:

```python
import sys
sys.path.insert(0, "path/to/governance-lib")
```

## Quick Start

```python
from governance_lib import calculate_sustainable_allocation_number
from governance_lib import format_governance_advisory_string

limit = calculate_sustainable_allocation_number(pool=100, num_agents=5)
# → 10 (the number agents need — not the formula)

advisory = format_governance_advisory_string(pool=100, num_agents=5)
# → The exact advisory text that achieved 80% survival in 30 GovSim simulations
```

## Functions

### Core Computation (`governance_computation.py`)
- `calculate_sustainable_allocation_number(pool, num_agents)` — Per-agent harvest limit
- `calculate_total_sustainable_harvest_number(pool)` — Group harvest limit
- `calculate_pool_after_harvest_number(pool, total_harvest)` — Projected pool after harvest + regeneration
- `calculate_rounds_until_collapse_number(pool, harvest_per_round)` — Countdown to collapse (-1 if sustainable)

### Advisory Formatting (`governance_advisory.py`)
- `format_governance_advisory_string(pool, num_agents, harvest_history)` — The validated advisory template
- `format_harvest_history_table_string(history)` — Per-round harvest table

### Monitoring (`governance_monitoring.py`)
- `get_commons_health_string(pool)` — Health status: thriving/stable/unhealthy/critical/collapsed
- `check_harvest_exceeds_sustainable_limit_boolean(requested, limit)` — Simple threshold check
- `detect_defection_risk_table(agent_history, group_norm)` — Risk level + escalation detection
- `get_defection_analysis_table(all_agent_harvests, limit)` — Per-agent compliance analysis

### Design Principles (`governance_principles.py`)
- `get_governance_design_principles_table()` — 5 empirically validated governance principles

## Evidence

Based on the [Governance as Computation](../governance-as-computation/) study (Credentum AI, 2026). 30 GovSim simulations across 6 conditions with Claude Haiku 4.5.

> Don't tell agents what's right. Tell them what's true. The morality is in the weights. The math isn't.
