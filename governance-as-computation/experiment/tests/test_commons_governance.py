"""
Unit Tests for Commons Governance Schema

CRITICAL_LLM_CONTEXT:
    - Tests governance policy validation logic
    - Runs in milliseconds (not 20-minute GovSim simulations)
    - Validates schema follows LLM-optimized patterns

WHY: Need rapid iteration on governance library changes.
     Unit tests provide sub-second feedback.
"""

import pytest
from datetime import datetime
import sys
import os

# Add governance_library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from governance_library.commons_governance_schema import (
    CommonsGovernancePolicySchema,
    GovernanceMode,
    GovernanceViolationLogSchema,
    GovernanceSessionSummarySchema,
    create_sustainable_pasture_policy_schema,
    create_baseline_no_governance_policy_schema,
)


class TestCommonsGovernancePolicySchema:
    """Unit tests for governance policy validation logic"""

    @pytest.fixture
    def standard_policy_schema(self):
        """
        CRITICAL_LLM_CONTEXT:
            - Standard policy for 5-agent pasture scenario
            - Max 15 per agent, threshold accounts for doubling
            - Soft mode (informs but doesn't enforce)
        """
        return CommonsGovernancePolicySchema(
            policy_name_string="pasture_sustainability_v1",
            max_harvest_per_agent_int=15,
            sustainable_threshold_per_round_int=50,
            mode_enum=GovernanceMode.SOFT,
            evidence_sources_list=["NeurIPS-2024-Piatti", "Hardin-1968"]
        )

    def test_validate_sustainable_harvest_returns_true(self, standard_policy_schema):
        """
        SCENARIO: Agent proposes harvest within sustainable bounds
        EXPECTED: Validation returns True
        WHY: 10 flocks per agent leaves room for regrowth
        """
        result_bool = standard_policy_schema.validate_harvest_decision_boolean(
            proposed_harvest_int=10,
            resource_pool_int=100,
            num_agents_int=5
        )
        assert result_bool is True

    def test_validate_excessive_harvest_returns_false(self, standard_policy_schema):
        """
        SCENARIO: Agent proposes harvest exceeding sustainable threshold
        EXPECTED: Validation returns False
        WHY: 20 flocks exceeds resource_pool // (5 * 2) = 10 threshold
        """
        result_bool = standard_policy_schema.validate_harvest_decision_boolean(
            proposed_harvest_int=20,
            resource_pool_int=100,
            num_agents_int=5
        )
        assert result_bool is False

    def test_validate_exact_threshold_returns_true(self, standard_policy_schema):
        """
        SCENARIO: Agent proposes harvest exactly at threshold
        EXPECTED: Validation returns True
        WHY: Threshold is inclusive (<=, not <)
        """
        result_bool = standard_policy_schema.validate_harvest_decision_boolean(
            proposed_harvest_int=10,  # Exactly resource_pool // (5 * 2)
            resource_pool_int=100,
            num_agents_int=5
        )
        assert result_bool is True

    def test_calculate_max_allowed_respects_policy_limit(self, standard_policy_schema):
        """
        SCENARIO: Dynamic threshold exceeds policy max_harvest
        EXPECTED: Returns policy limit (15)
        WHY: Policy max acts as hard ceiling
        """
        max_allowed_int = standard_policy_schema.calculate_max_allowed_harvest_int(
            resource_pool_int=200,  # Dynamic threshold would be 200 // 10 = 20
            num_agents_int=5
        )
        assert max_allowed_int == 15  # Policy limit

    def test_calculate_max_allowed_respects_dynamic_threshold(self, standard_policy_schema):
        """
        SCENARIO: Resource pool low, dynamic threshold below policy max
        EXPECTED: Returns dynamic threshold (5)
        WHY: Sustainability requires leaving half for regrowth
        """
        max_allowed_int = standard_policy_schema.calculate_max_allowed_harvest_int(
            resource_pool_int=50,  # Dynamic threshold = 50 // 10 = 5
            num_agents_int=5
        )
        assert max_allowed_int == 5  # Dynamic threshold

    def test_universalization_prompt_includes_collective_impact(self, standard_policy_schema):
        """
        SCENARIO: Generate prompt for agent considering 15 flocks
        EXPECTED: Prompt explains collective impact (15 * 5 = 75 total)
        WHY: Forces agent to reason about "what if everyone did this"
        """
        prompt_string = standard_policy_schema.generate_universalization_prompt_string(
            proposed_harvest_int=15,
            agent_name_string="John"
        )
        assert "15 flocks" in prompt_string
        assert "75 total" in prompt_string
        assert "sustainable" in prompt_string.lower()

    def test_edge_case_zero_resource_pool(self, standard_policy_schema):
        """
        SCENARIO: Resource pool depleted (collapse scenario)
        EXPECTED: Max allowed is 0
        WHY: Cannot harvest from empty pool
        """
        max_allowed_int = standard_policy_schema.calculate_max_allowed_harvest_int(
            resource_pool_int=0,
            num_agents_int=5
        )
        assert max_allowed_int == 0

    def test_edge_case_single_agent(self, standard_policy_schema):
        """
        SCENARIO: Only 1 agent in simulation
        EXPECTED: Threshold is resource_pool // 2 (capped by policy)
        WHY: Still need to leave half for regrowth
        """
        max_allowed_int = standard_policy_schema.calculate_max_allowed_harvest_int(
            resource_pool_int=100,
            num_agents_int=1
        )
        # Dynamic threshold = 100 // 2 = 50, but policy max is 15
        assert max_allowed_int == 15  # Min of policy (15) and dynamic (50)

    def test_edge_case_zero_agents(self, standard_policy_schema):
        """
        SCENARIO: No agents (edge case)
        EXPECTED: Max allowed is 0
        WHY: Division by zero protection
        """
        max_allowed_int = standard_policy_schema.calculate_max_allowed_harvest_int(
            resource_pool_int=100,
            num_agents_int=0
        )
        assert max_allowed_int == 0

    def test_edge_case_negative_proposal(self, standard_policy_schema):
        """
        SCENARIO: Agent proposes negative harvest (nonsensical)
        EXPECTED: Validation returns True (negative < threshold)
        WHY: Technically valid but should be caught elsewhere
        """
        result_bool = standard_policy_schema.validate_harvest_decision_boolean(
            proposed_harvest_int=-5,
            resource_pool_int=100,
            num_agents_int=5
        )
        assert result_bool is True

    def test_governance_observation_includes_key_info(self, standard_policy_schema):
        """
        SCENARIO: Generate governance observation for round 3
        EXPECTED: Contains policy name, resource pool, max sustainable
        WHY: SOFT mode uses observations to advise agents
        """
        observation_string = standard_policy_schema.generate_governance_observation_string(
            resource_pool_int=60,
            num_agents_int=5,
            round_int=3
        )
        assert "Round 3" in observation_string
        assert "pasture_sustainability_v1" in observation_string
        assert "60" in observation_string
        assert "6" in observation_string  # 60 // 10 = 6 max sustainable


class TestGovernanceViolationLogSchema:
    """Unit tests for violation logging"""

    def test_violation_log_captures_key_fields(self):
        """
        SCENARIO: Agent attempts to take 25 when only 10 allowed
        EXPECTED: Log captures all required fields for audit
        WHY: Provenance needed for human escalation and analysis
        """
        log_schema = GovernanceViolationLogSchema(
            agent_id_string="persona_2",
            round_int=1,
            requested_harvest_int=25,
            allowed_harvest_int=10,
            resource_pool_before_int=60,
            rule_violated_string="sustainable_threshold_exceeded"
        )

        assert log_schema.agent_id_string == "persona_2"
        assert log_schema.requested_harvest_int == 25
        assert log_schema.allowed_harvest_int == 10
        assert isinstance(log_schema.timestamp_datetime, datetime)

    def test_violation_log_to_audit_record(self):
        """
        SCENARIO: Convert violation to audit record dict
        EXPECTED: Dict contains all fields including excess
        WHY: Need serializable format for storage/analysis
        """
        log_schema = GovernanceViolationLogSchema(
            agent_id_string="persona_0",
            round_int=0,
            requested_harvest_int=20,
            allowed_harvest_int=10,
            resource_pool_before_int=100,
            rule_violated_string="max_harvest_exceeded"
        )

        audit_dict = log_schema.to_audit_record_dict()

        assert audit_dict["agent_id"] == "persona_0"
        assert audit_dict["excess_requested"] == 10  # 20 - 10
        assert "timestamp" in audit_dict


class TestGovernanceSessionSummarySchema:
    """Unit tests for session summary"""

    def test_sustainability_score_perfect(self):
        """
        SCENARIO: Resource maintained at initial level
        EXPECTED: Score = 1.0
        WHY: Perfect sustainability
        """
        summary_schema = GovernanceSessionSummarySchema(
            session_id_string="test_session",
            policy_schema=None,
            total_rounds_int=10,
            final_resource_pool_int=100,
            survival_achieved_bool=True,
            total_violations_int=0,
            resource_history_list=[100, 100, 100, 100, 100]
        )

        score_float = summary_schema.calculate_sustainability_score_float()
        assert score_float == 1.0

    def test_sustainability_score_collapse(self):
        """
        SCENARIO: Resource collapsed to zero
        EXPECTED: Score = 0.0
        WHY: Complete failure
        """
        summary_schema = GovernanceSessionSummarySchema(
            session_id_string="test_session",
            policy_schema=None,
            total_rounds_int=3,
            final_resource_pool_int=0,
            survival_achieved_bool=False,
            total_violations_int=0,
            resource_history_list=[100, 30, 0]
        )

        score_float = summary_schema.calculate_sustainability_score_float()
        assert score_float == 0.0

    def test_sustainability_score_partial(self):
        """
        SCENARIO: Resource declined but not collapsed
        EXPECTED: Score = 0.5 (half preserved)
        WHY: Partial success
        """
        summary_schema = GovernanceSessionSummarySchema(
            session_id_string="test_session",
            policy_schema=None,
            total_rounds_int=5,
            final_resource_pool_int=50,
            survival_achieved_bool=True,
            total_violations_int=3,
            resource_history_list=[100, 80, 60, 55, 50]
        )

        score_float = summary_schema.calculate_sustainability_score_float()
        assert score_float == 0.5


class TestFactoryFunctions:
    """Unit tests for policy factory functions"""

    def test_sustainable_pasture_policy_defaults(self):
        """
        SCENARIO: Create default sustainable policy
        EXPECTED: Max 10 per agent, HARD mode
        WHY: These defaults prevent collapse in 5-agent scenario
        """
        policy_schema = create_sustainable_pasture_policy_schema()

        assert policy_schema.max_harvest_per_agent_int == 10
        assert policy_schema.mode_enum == GovernanceMode.HARD
        assert policy_schema.sustainable_threshold_per_round_int == 50
        assert "NeurIPS-2024-Piatti-GovSim" in policy_schema.evidence_sources_list

    def test_sustainable_pasture_policy_custom(self):
        """
        SCENARIO: Create custom policy with SOFT mode
        EXPECTED: Custom values applied
        WHY: Allow experimentation with different limits
        """
        policy_schema = create_sustainable_pasture_policy_schema(
            max_per_agent_int=8,
            mode_enum=GovernanceMode.SOFT
        )

        assert policy_schema.max_harvest_per_agent_int == 8
        assert policy_schema.mode_enum == GovernanceMode.SOFT

    def test_baseline_policy_no_enforcement(self):
        """
        SCENARIO: Create baseline policy for comparison
        EXPECTED: NONE mode, high limits (effectively disabled)
        WHY: Need to reproduce collapse behavior
        """
        policy_schema = create_baseline_no_governance_policy_schema()

        assert policy_schema.mode_enum == GovernanceMode.NONE
        assert policy_schema.max_harvest_per_agent_int >= 100
        assert policy_schema.violation_triggers_escalation_bool is False


class TestGovsimScenarioValidation:
    """
    Tests that validate governance against known GovSim outcomes

    CRITICAL_LLM_CONTEXT:
        - These tests replicate exact GovSim pasture scenarios
        - Baseline SHOULD fail validation (what happened in collapse)
        - Governance SHOULD pass validation (what would prevent collapse)
    """

    @pytest.fixture
    def govsim_governance_policy(self):
        """Policy designed to prevent GovSim collapse"""
        return create_sustainable_pasture_policy_schema()

    def test_round_0_collapse_scenario_fails_validation(self, govsim_governance_policy):
        """
        SCENARIO: Replicate Round 0 of actual GovSim Haiku run
        ACTUAL: Agents took 70 total (14 per agent average)
        EXPECTED: Validation fails - this harvest is unsustainable

        EVIDENCE: GovSim run showed Round 0: 100 -> 30 hectares
        """
        # Round 0: resource_pool = 100, 5 agents
        # Haiku agents took average ~14 each

        # Check if 14 per agent would pass governance
        result_bool = govsim_governance_policy.validate_harvest_decision_boolean(
            proposed_harvest_int=14,
            resource_pool_int=100,
            num_agents_int=5
        )
        assert result_bool is False  # 14 > 10 (policy limit)

    def test_sustainable_harvest_passes_validation(self, govsim_governance_policy):
        """
        SCENARIO: Agent follows governance advice (take 10)
        EXPECTED: Validation passes
        WHY: 10 per agent = 50 total, leaving 50 to double to 100
        """
        result_bool = govsim_governance_policy.validate_harvest_decision_boolean(
            proposed_harvest_int=10,
            resource_pool_int=100,
            num_agents_int=5
        )
        assert result_bool is True

    def test_low_resource_scenario_adjusts_threshold(self, govsim_governance_policy):
        """
        SCENARIO: Resource pool depleted to 26 (Round 2 of collapse)
        EXPECTED: Max allowed drops to 2 (26 // 10 = 2)
        WHY: Dynamic threshold prevents final collapse
        """
        max_allowed_int = govsim_governance_policy.calculate_max_allowed_harvest_int(
            resource_pool_int=26,
            num_agents_int=5
        )
        assert max_allowed_int == 2  # 26 // 10 = 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
