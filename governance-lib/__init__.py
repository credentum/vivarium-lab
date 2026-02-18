"""
Governance Computation Library

Empirically validated governance functions for multi-agent coordination.
Every function returns a computed answer, not raw data.

Usage:
    from governance_lib import calculate_sustainable_allocation_number
    from governance_lib import format_governance_advisory_string

EVIDENCE:
    Credentum AI. (2026). Governance as Computation. Vivarium Lab.
    github.com/credentum/vivarium-lab/governance-as-information
"""

from .governance_computation import (
    calculate_sustainable_allocation_number,
    calculate_total_sustainable_harvest_number,
    calculate_pool_after_harvest_number,
    calculate_rounds_until_collapse_number,
)
from .governance_advisory import (
    format_governance_advisory_string,
    format_harvest_history_table_string,
)
from .governance_monitoring import (
    get_commons_health_string,
    check_harvest_exceeds_sustainable_limit_boolean,
    detect_defection_risk_table,
    get_defection_analysis_table,
)
from .governance_principles import (
    get_governance_design_principles_table,
)

__all__ = [
    "calculate_sustainable_allocation_number",
    "calculate_total_sustainable_harvest_number",
    "calculate_pool_after_harvest_number",
    "calculate_rounds_until_collapse_number",
    "format_governance_advisory_string",
    "format_harvest_history_table_string",
    "get_commons_health_string",
    "check_harvest_exceeds_sustainable_limit_boolean",
    "detect_defection_risk_table",
    "get_defection_analysis_table",
    "get_governance_design_principles_table",
]
