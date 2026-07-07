"""
Governance Library for GovSim Commons Simulation

CRITICAL_LLM_CONTEXT:
    - Provides governance schemas to prevent commons collapse
    - Includes persona deliberation framework (Scientist → Judge → Librarian)
    - Supports iteration (Judge rejects → Scientist refines)
    - Supports retrieval (learn from past deliberations)

WHY: Governance structure > Model intelligence for commons problems
EVIDENCE: GovSim NeurIPS 2024, Learning Panel 2026-01-14
"""

# JSON Session Manager
from .json_session_manager import (
    DeliberationSessionSchema,
    read_session_schema,
    update_session_void,
    create_new_session_schema,
    list_past_sessions_list,
    delete_session_void,
)

# Retrieval Utilities
from .retrieval_utilities import (
    read_existing_governance_schema_string,
    retrieve_past_successful_deliberations_list,
    format_past_deliberations_string,
)

# Persona Deliberation with Iteration
from .deliberate_governance import (
    run_deliberation_with_iteration_loop,
    run_scientist_persona_with_retrieval,
    run_judge_persona_with_verdict_extraction,
    run_librarian_persona,
)

# Ablation Study Framework
from .deliberation_ablation import (
    run_ablation_study_and_return_results_dict,
    evaluate_schema_in_mock_env_dict,
)

# Commons Governance Schema
from .commons_governance_schema import (
    GovernanceMode,
    CommonsGovernancePolicySchema,
    create_sustainable_pasture_policy_schema,
    create_baseline_no_governance_policy_schema,
)

__all__ = [
    # Session Management
    "DeliberationSessionSchema",
    "read_session_schema",
    "update_session_void",
    "create_new_session_schema",
    "list_past_sessions_list",
    "delete_session_void",
    # Retrieval
    "read_existing_governance_schema_string",
    "retrieve_past_successful_deliberations_list",
    "format_past_deliberations_string",
    # Deliberation
    "run_deliberation_with_iteration_loop",
    "run_scientist_persona_with_retrieval",
    "run_judge_persona_with_verdict_extraction",
    "run_librarian_persona",
    # Ablation
    "run_ablation_study_and_return_results_dict",
    "evaluate_schema_in_mock_env_dict",
    # Governance Schema
    "GovernanceMode",
    "CommonsGovernancePolicySchema",
    "create_sustainable_pasture_policy_schema",
    "create_baseline_no_governance_policy_schema",
]
