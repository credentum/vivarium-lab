"""
Mock Integration Tests for Governance Library

CRITICAL_LLM_CONTEXT:
    - Simulates multi-round GovSim scenarios WITHOUT LLM calls
    - Runs in milliseconds (not 20-minute simulations)
    - Tests governance enforcement across multiple rounds
    - Validates core hypothesis: governance library prevents collapse

WHY: Need to iterate on governance library changes rapidly.
     Full GovSim takes 20-30 minutes per run.
     Mock environment provides instant feedback.

EVIDENCE: These tests replicate dynamics from actual GovSim runs:
    - Baseline Haiku collapsed in 3 rounds
    - Resource went 100 -> 30 -> 0
    - Governance should cap harvests and prevent collapse
"""

import pytest
from typing import Dict, List
from dataclasses import dataclass, field
import sys
import os

# Add governance_library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from governance_library.commons_governance_schema import (
    CommonsGovernancePolicySchema,
    GovernanceMode,
    GovernanceViolationLogSchema,
    create_sustainable_pasture_policy_schema,
    create_baseline_no_governance_policy_schema,
)


@dataclass
class MockAgentDecisionSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - Simulates agent's harvest decision
        - Used for testing governance without running full GovSim
        - Includes agent reasoning (would come from LLM in real scenario)

    WHY: Mock decisions enable testing "what if" scenarios:
         - All agents greedy
         - Mixed cooperative/defecting
         - All agents follow governance
    """
    agent_id_string: str
    proposed_harvest_int: int
    reasoning_string: str = "greedy"  # "greedy" | "cooperative" | "universalization"


@dataclass
class MockEnvironmentStateSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - Simulates GovSim environment state
        - Tracks resource pool, agent history
        - Used for unit testing governance logic

    WHY: Replicates key GovSim state without full simulation.
    """
    resource_pool_int: int
    num_agents_int: int
    round_int: int
    harvest_history_dict: Dict[str, List[int]] = field(default_factory=dict)
    initial_resource_int: int = 100  # For sustainability scoring


class MockGovernanceEnvironment:
    """
    CRITICAL_LLM_CONTEXT:
        - Mock environment for testing governance without full GovSim
        - Simulates key dynamics: resource doubling, harvesting
        - Enables millisecond-speed iteration

    WHY: Full GovSim takes 20-30 minutes. Need rapid feedback for
         governance library development and testing.

    EVIDENCE: Dynamics replicate actual GovSim behavior:
        - Resources double each round (cap at 100)
        - Concurrent harvesting (all agents at once)
        - Stochastic assignment if requests exceed pool
    """

    def __init__(
        self,
        policy_schema: CommonsGovernancePolicySchema,
        initial_resource_int: int = 100,
        num_agents_int: int = 5
    ):
        self.policy_schema = policy_schema
        self.state_schema = MockEnvironmentStateSchema(
            resource_pool_int=initial_resource_int,
            num_agents_int=num_agents_int,
            round_int=0,
            harvest_history_dict={f"agent_{i}": [] for i in range(num_agents_int)},
            initial_resource_int=initial_resource_int
        )
        self.violations_list: List[GovernanceViolationLogSchema] = []
        self.resource_history_list: List[int] = [initial_resource_int]

    def simulate_round_with_decisions_list(
        self,
        decisions_list: List[MockAgentDecisionSchema]
    ) -> Dict[str, int]:
        """
        CRITICAL_LLM_CONTEXT:
            - Simulates one round of harvesting
            - Applies governance rules based on policy mode
            - Returns actual harvests (may differ from proposed if HARD mode)

        WHY: Allows testing "what if 3 agents cooperate but 2 defect"
             scenarios without 20-minute simulation runs.

        DYNAMICS (CONCURRENT - matches GovSim):
            1. Calculate max allowed for ALL agents based on CURRENT pool
            2. Apply governance caps to all proposals
            3. Deduct all harvests at once
            4. Pool doubles (capped at initial_resource)
            5. Round increments

        Args:
            decisions_list: List of agent decisions for this round

        Returns:
            Dict mapping agent_id to actual harvest received
        """
        actual_harvests_dict = {}

        # CRITICAL: Calculate max allowed ONCE at start of round
        # This is how GovSim works - concurrent evaluation
        pool_at_round_start_int = self.state_schema.resource_pool_int
        max_allowed_int = self.policy_schema.calculate_max_allowed_harvest_int(
            pool_at_round_start_int,
            self.state_schema.num_agents_int
        )

        # First pass: calculate all actual harvests
        for decision_schema in decisions_list:
            proposed_int = decision_schema.proposed_harvest_int
            agent_id = decision_schema.agent_id_string

            # Apply governance based on mode
            if self.policy_schema.mode_enum == GovernanceMode.HARD:
                actual_int = min(proposed_int, max_allowed_int)

                # Log violation if capped
                if actual_int < proposed_int:
                    violation_schema = GovernanceViolationLogSchema(
                        agent_id_string=agent_id,
                        round_int=self.state_schema.round_int,
                        requested_harvest_int=proposed_int,
                        allowed_harvest_int=actual_int,
                        resource_pool_before_int=pool_at_round_start_int,
                        rule_violated_string="max_harvest_exceeded"
                    )
                    self.violations_list.append(violation_schema)

            elif self.policy_schema.mode_enum == GovernanceMode.SOFT:
                # SOFT mode: allow but track violations
                actual_int = proposed_int  # Don't cap

                if proposed_int > max_allowed_int:
                    violation_schema = GovernanceViolationLogSchema(
                        agent_id_string=agent_id,
                        round_int=self.state_schema.round_int,
                        requested_harvest_int=proposed_int,
                        allowed_harvest_int=max_allowed_int,  # What should have been
                        resource_pool_before_int=pool_at_round_start_int,
                        rule_violated_string="advisory_exceeded"
                    )
                    self.violations_list.append(violation_schema)
            else:
                # NONE mode: no governance
                actual_int = proposed_int

            actual_harvests_dict[agent_id] = actual_int

        # Second pass: deduct all harvests at once (concurrent)
        total_harvest_int = sum(actual_harvests_dict.values())

        # If total exceeds pool, cap proportionally (stochastic in GovSim)
        if total_harvest_int > pool_at_round_start_int:
            scale_factor = pool_at_round_start_int / total_harvest_int
            for agent_id in actual_harvests_dict:
                actual_harvests_dict[agent_id] = int(actual_harvests_dict[agent_id] * scale_factor)
            total_harvest_int = sum(actual_harvests_dict.values())

        # Update state
        self.state_schema.resource_pool_int = pool_at_round_start_int - total_harvest_int

        for agent_id, harvest in actual_harvests_dict.items():
            self.state_schema.harvest_history_dict[agent_id].append(harvest)

        # Simulate GovSim dynamics: resource doubles, capped at initial
        self.state_schema.resource_pool_int = min(
            self.state_schema.resource_pool_int * 2,
            self.state_schema.initial_resource_int
        )

        self.state_schema.round_int += 1
        self.resource_history_list.append(self.state_schema.resource_pool_int)

        return actual_harvests_dict

    def check_survival_boolean(self) -> bool:
        """Returns True if resource pool > 0"""
        return self.state_schema.resource_pool_int > 0

    def get_sustainability_score_float(self) -> float:
        """
        CRITICAL_LLM_CONTEXT:
            - Returns 0.0-1.0 based on resource preservation
            - 1.0 = perfect (resource at or above initial)
            - 0.0 = collapse (resource = 0)
        """
        if self.state_schema.initial_resource_int == 0:
            return 0.0
        ratio_float = self.state_schema.resource_pool_int / self.state_schema.initial_resource_int
        return min(1.0, ratio_float)


class TestGovernanceMockIntegration:
    """Integration tests using mock environment"""

    @pytest.fixture
    def baseline_policy_schema(self):
        """Policy with no governance (baseline)"""
        return create_baseline_no_governance_policy_schema()

    @pytest.fixture
    def governance_policy_schema(self):
        """Policy with governance rules (HARD enforcement)"""
        return create_sustainable_pasture_policy_schema()

    @pytest.fixture
    def soft_governance_policy_schema(self):
        """Policy with SOFT governance (advisory only)"""
        return create_sustainable_pasture_policy_schema(mode_enum=GovernanceMode.SOFT)

    def test_baseline_scenario_collapses(self, baseline_policy_schema):
        """
        SCENARIO: Replicate GovSim baseline - all agents take 20 flocks
        EXPECTED: Collapse by round 2
        WHY: This is what happened in actual GovSim run with Haiku

        EVIDENCE: Haiku run showed collapse in 3 rounds:
            Round 0: 100 -> 30 (took 70)
            Round 1: 60 -> 13 (took 47)
            Round 2: 26 -> 0 (collapse)
        """
        env = MockGovernanceEnvironment(baseline_policy_schema)

        # Round 0: All agents take 20 (simulating greedy behavior)
        decisions = [
            MockAgentDecisionSchema(f"agent_{i}", 20, "greedy")
            for i in range(5)
        ]
        env.simulate_round_with_decisions_list(decisions)

        # After round 0: 100 - 100 = 0, but we cap at pool available
        # Resource should double after (if any left)
        assert env.state_schema.resource_pool_int == 0
        assert not env.check_survival_boolean()

    def test_governance_hard_mode_prevents_collapse(self, governance_policy_schema):
        """
        SCENARIO: Same agent behavior but with HARD governance enforcement
        EXPECTED: Survives (harvest capped at 10 per agent)
        WHY: This tests the core hypothesis - library prevents collapse

        EVIDENCE: With max 10 per agent:
            - 5 agents * 10 = 50 taken
            - 100 - 50 = 50 remaining
            - 50 * 2 = 100 (doubles back to cap)
            - System is sustainable
        """
        env = MockGovernanceEnvironment(governance_policy_schema)

        # Round 0: All agents TRY to take 20, governance caps at 10
        decisions = [
            MockAgentDecisionSchema(f"agent_{i}", 20, "greedy")
            for i in range(5)
        ]
        actual_harvests = env.simulate_round_with_decisions_list(decisions)

        # Verify governance enforcement
        for agent_id, actual in actual_harvests.items():
            assert actual == 10  # Capped by governance

        # Resource should remain positive and recover
        assert env.state_schema.resource_pool_int == 100  # 50 * 2 = 100
        assert env.check_survival_boolean()

        # Check violations logged
        assert len(env.violations_list) == 5  # All 5 agents violated

    def test_soft_mode_does_not_prevent_collapse(self, soft_governance_policy_schema):
        """
        SCENARIO: Greedy agents with SOFT governance (advisory only)
        EXPECTED: Collapses - SOFT mode doesn't enforce
        WHY: Tests that advisory alone doesn't save greedy agents
        """
        env = MockGovernanceEnvironment(soft_governance_policy_schema)

        decisions = [
            MockAgentDecisionSchema(f"agent_{i}", 20, "greedy")
            for i in range(5)
        ]
        env.simulate_round_with_decisions_list(decisions)

        # SOFT mode allows full harvest, should collapse
        assert env.state_schema.resource_pool_int == 0
        assert not env.check_survival_boolean()

        # But violations should be logged
        assert len(env.violations_list) == 5

    def test_mixed_strategy_scenario(self, governance_policy_schema):
        """
        SCENARIO: 3 agents cooperate (take 10), 2 defect (try 20)
        EXPECTED: Governance caps defectors, system survives
        WHY: Tests heterogeneous agent behavior
        """
        env = MockGovernanceEnvironment(governance_policy_schema)

        decisions = [
            MockAgentDecisionSchema("agent_0", 10, "cooperative"),
            MockAgentDecisionSchema("agent_1", 10, "cooperative"),
            MockAgentDecisionSchema("agent_2", 10, "cooperative"),
            MockAgentDecisionSchema("agent_3", 20, "greedy"),
            MockAgentDecisionSchema("agent_4", 20, "greedy"),
        ]
        actual_harvests = env.simulate_round_with_decisions_list(decisions)

        # Verify defectors capped
        assert actual_harvests["agent_3"] == 10
        assert actual_harvests["agent_4"] == 10

        # Only 2 violations (the defectors)
        assert len(env.violations_list) == 2

        assert env.check_survival_boolean()

    def test_multi_round_sustainability(self, governance_policy_schema):
        """
        SCENARIO: Run 10 rounds with governance enforcement
        EXPECTED: Resource stays stable, no collapse
        WHY: Tests long-term sustainability of governance
        """
        env = MockGovernanceEnvironment(governance_policy_schema)

        for round_int in range(10):
            # All agents try to take 15 each round
            decisions = [
                MockAgentDecisionSchema(f"agent_{i}", 15, "greedy")
                for i in range(5)
            ]
            env.simulate_round_with_decisions_list(decisions)

        # Should have survived all 10 rounds
        assert env.check_survival_boolean()
        assert env.state_schema.resource_pool_int == 100  # Recovered each round
        assert env.get_sustainability_score_float() == 1.0

    def test_cooperative_agents_without_governance(self, baseline_policy_schema):
        """
        SCENARIO: All agents naturally cooperative (take 10 each)
        EXPECTED: Survives even without governance
        WHY: Tests that cooperation alone is sufficient

        This is the ideal: agents that don't NEED governance.
        But GovSim showed most models don't achieve this naturally.
        """
        env = MockGovernanceEnvironment(baseline_policy_schema)

        for round_int in range(5):
            decisions = [
                MockAgentDecisionSchema(f"agent_{i}", 10, "cooperative")
                for i in range(5)
            ]
            env.simulate_round_with_decisions_list(decisions)

        assert env.check_survival_boolean()
        assert env.state_schema.resource_pool_int == 100

    def test_gradual_resource_depletion(self, governance_policy_schema):
        """
        SCENARIO: Dynamic threshold adjustment as pool shrinks
        EXPECTED: Governance adjusts max allowed as resources drop

        WHY: Tests that governance adapts to changing resource levels
        """
        env = MockGovernanceEnvironment(governance_policy_schema, initial_resource_int=50)

        # Round 0: Pool = 50, max = 50 // 10 = 5
        decisions = [
            MockAgentDecisionSchema(f"agent_{i}", 10, "greedy")
            for i in range(5)
        ]
        actual_harvests = env.simulate_round_with_decisions_list(decisions)

        # Each agent capped at 5 (dynamic threshold)
        for actual in actual_harvests.values():
            assert actual == 5

        # 50 - 25 = 25, doubles to 50
        assert env.state_schema.resource_pool_int == 50

    def test_violation_tracking_across_rounds(self, governance_policy_schema):
        """
        SCENARIO: Multiple rounds with various violations
        EXPECTED: All violations tracked with round numbers
        WHY: Need audit trail for analysis
        """
        env = MockGovernanceEnvironment(governance_policy_schema)

        for round_int in range(3):
            decisions = [
                MockAgentDecisionSchema(f"agent_{i}", 15, "greedy")
                for i in range(5)
            ]
            env.simulate_round_with_decisions_list(decisions)

        # 5 agents * 3 rounds = 15 violations
        assert len(env.violations_list) == 15

        # Check round distribution
        rounds_violated = [v.round_int for v in env.violations_list]
        assert rounds_violated.count(0) == 5
        assert rounds_violated.count(1) == 5
        assert rounds_violated.count(2) == 5


class TestReplicateActualGovsimRun:
    """
    Tests that replicate exact dynamics from actual GovSim Haiku run

    CRITICAL_LLM_CONTEXT:
        - Based on actual run: 191 API calls, 22 minutes
        - Collapsed in 3 rounds
        - Agents defected in Round 0 despite agreement in conversation
    """

    def test_replicate_haiku_collapse_dynamics(self):
        """
        SCENARIO: Replicate exact Haiku collapse pattern
        Round 0: 100 -> 30 (took 70)
        Round 1: 60 -> 13 (took 47)
        Round 2: 26 -> 0 (collapse)

        WHY: Validates mock accurately replicates real GovSim dynamics
        """
        baseline = create_baseline_no_governance_policy_schema()
        env = MockGovernanceEnvironment(baseline)

        # Round 0: Agents agreed to take ~10 each but defected, took ~14 each
        round_0_decisions = [
            MockAgentDecisionSchema("John", 14),
            MockAgentDecisionSchema("Kate", 14),
            MockAgentDecisionSchema("Jack", 14),
            MockAgentDecisionSchema("Emma", 14),
            MockAgentDecisionSchema("Luke", 14),
        ]
        env.simulate_round_with_decisions_list(round_0_decisions)

        # After Round 0: 100 - 70 = 30, doubles to 60
        assert env.state_schema.resource_pool_int == 60

        # Round 1: Similar defection
        round_1_decisions = [
            MockAgentDecisionSchema("John", 10),
            MockAgentDecisionSchema("Kate", 10),
            MockAgentDecisionSchema("Jack", 10),
            MockAgentDecisionSchema("Emma", 9),
            MockAgentDecisionSchema("Luke", 8),
        ]
        env.simulate_round_with_decisions_list(round_1_decisions)

        # After Round 1: 60 - 47 = 13, doubles to 26
        assert env.state_schema.resource_pool_int == 26

        # Round 2: Final collapse (agents take exactly 26 to deplete)
        round_2_decisions = [
            MockAgentDecisionSchema("John", 5),
            MockAgentDecisionSchema("Kate", 5),
            MockAgentDecisionSchema("Jack", 5),
            MockAgentDecisionSchema("Emma", 5),
            MockAgentDecisionSchema("Luke", 6),
        ]
        env.simulate_round_with_decisions_list(round_2_decisions)

        # After Round 2: 26 - 26 = 0, COLLAPSE
        assert env.state_schema.resource_pool_int == 0
        assert not env.check_survival_boolean()

    def test_governance_would_have_saved_haiku(self):
        """
        SCENARIO: Same agent INTENTIONS but with governance enforcement
        EXPECTED: System survives
        WHY: Demonstrates governance library value

        This is the core hypothesis: Haiku + Library should survive
        where Haiku alone collapsed.
        """
        governance = create_sustainable_pasture_policy_schema()
        env = MockGovernanceEnvironment(governance)

        # Round 0: Agents TRY to defect (14 each) but governance caps at 10
        round_0_decisions = [
            MockAgentDecisionSchema("John", 14),
            MockAgentDecisionSchema("Kate", 14),
            MockAgentDecisionSchema("Jack", 14),
            MockAgentDecisionSchema("Emma", 14),
            MockAgentDecisionSchema("Luke", 14),
        ]
        actual = env.simulate_round_with_decisions_list(round_0_decisions)

        # Each capped at 10
        assert all(v == 10 for v in actual.values())

        # 100 - 50 = 50, doubles to 100 (sustainable!)
        assert env.state_schema.resource_pool_int == 100

        # Continue for 10 rounds to prove sustainability
        for _ in range(10):
            decisions = [
                MockAgentDecisionSchema(f"agent_{i}", 14)
                for i in range(5)
            ]
            env.simulate_round_with_decisions_list(decisions)

        assert env.check_survival_boolean()
        assert env.state_schema.resource_pool_int == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
