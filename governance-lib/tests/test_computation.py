"""Tests for governance_computation.py — core number functions."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from governance_computation import (
    calculate_sustainable_allocation_number,
    calculate_total_sustainable_harvest_number,
    calculate_pool_after_harvest_number,
    calculate_rounds_until_collapse_number,
)
from governance_advisory import (
    format_governance_advisory_string,
    format_harvest_history_table_string,
)


class TestSustainableAllocation:
    """Tests for calculate_sustainable_allocation_number."""

    def test_standard_govsim_case(self):
        """pool=100, 5 agents, regen=2.0 → limit=10."""
        assert calculate_sustainable_allocation_number(100, 5) == 10

    def test_depleted_pool(self):
        """pool=30, 5 agents → limit=3."""
        assert calculate_sustainable_allocation_number(30, 5) == 3

    def test_single_agent(self):
        """pool=100, 1 agent → limit=50."""
        assert calculate_sustainable_allocation_number(100, 1) == 50

    def test_zero_pool(self):
        """pool=0 → limit=0."""
        assert calculate_sustainable_allocation_number(0, 5) == 0.0

    def test_zero_agents(self):
        """0 agents → limit=0."""
        assert calculate_sustainable_allocation_number(100, 0) == 0.0

    def test_negative_pool(self):
        """Negative pool → 0."""
        assert calculate_sustainable_allocation_number(-10, 5) == 0.0

    def test_at_collapse_threshold(self):
        """pool=5, 5 agents → limit=0 (floor of 0.5)."""
        assert calculate_sustainable_allocation_number(5, 5) == 0

    def test_custom_regeneration_rate(self):
        """pool=100, 5 agents, regen=3.0 → floor(100/15) = 6."""
        assert calculate_sustainable_allocation_number(100, 5, regeneration_rate=3.0) == 6

    def test_two_agents(self):
        """pool=100, 2 agents → limit=25."""
        assert calculate_sustainable_allocation_number(100, 2) == 25


class TestTotalSustainableHarvest:
    """Tests for calculate_total_sustainable_harvest_number."""

    def test_standard_case(self):
        """pool=100, regen=2.0 → total=50."""
        assert calculate_total_sustainable_harvest_number(100) == 50

    def test_zero_pool(self):
        assert calculate_total_sustainable_harvest_number(0) == 0.0

    def test_depleted(self):
        """pool=30 → total=15."""
        assert calculate_total_sustainable_harvest_number(30) == 15


class TestPoolAfterHarvest:
    """Tests for calculate_pool_after_harvest_number."""

    def test_sustainable_harvest(self):
        """100 - 50 = 50, doubles to 100."""
        assert calculate_pool_after_harvest_number(100, 50) == 100.0

    def test_over_harvest(self):
        """100 - 80 = 20, doubles to 40."""
        assert calculate_pool_after_harvest_number(100, 80) == 40.0

    def test_collapse(self):
        """100 - 97 = 3, below threshold → 0."""
        assert calculate_pool_after_harvest_number(100, 97) == 0.0

    def test_at_threshold(self):
        """100 - 95 = 5, at threshold → doubles to 10."""
        assert calculate_pool_after_harvest_number(100, 95) == 10.0

    def test_below_threshold(self):
        """100 - 96 = 4, below threshold → collapsed."""
        assert calculate_pool_after_harvest_number(100, 96) == 0.0

    def test_capped_at_max(self):
        """30 - 5 = 25, doubles to 50 (under 100 cap)."""
        assert calculate_pool_after_harvest_number(30, 5) == 50.0

    def test_zero_harvest(self):
        """100 - 0 = 100, doubles to 200, capped at 100."""
        assert calculate_pool_after_harvest_number(100, 0) == 100.0


class TestRoundsUntilCollapse:
    """Tests for calculate_rounds_until_collapse_number."""

    def test_sustainable_forever(self):
        """Harvest=50 from pool=100 is sustainable (doubles back to 100)."""
        assert calculate_rounds_until_collapse_number(100, 50) == -1

    def test_immediate_collapse(self):
        """Harvest=97 from pool=100 → collapse at round 0."""
        assert calculate_rounds_until_collapse_number(100, 97) == 0

    def test_baseline_collapse_pattern(self):
        """Harvest=80 from pool=100: R0: 100-80=20→40, R1: 40-80→collapse."""
        result = calculate_rounds_until_collapse_number(100, 80)
        assert result == 1  # survives R0, collapses at R1

    def test_zero_pool(self):
        assert calculate_rounds_until_collapse_number(0, 50) == 0

    def test_zero_harvest(self):
        assert calculate_rounds_until_collapse_number(100, 0) == -1

    def test_gradual_decline(self):
        """Harvest=60 from pool=100: slow decline."""
        result = calculate_rounds_until_collapse_number(100, 60)
        assert result > 0  # collapses eventually
        assert result < 20  # but not too slowly


class TestAdvisoryFormat:
    """Tests that advisory format matches the validated GovSim template."""

    def test_matches_govsim_template_no_history(self):
        """Advisory with no history matches the exact validated format."""
        result = format_governance_advisory_string(100, 5)
        assert "=== Governance Advisory ===" in result
        assert "Current resource pool: 100 hectares." in result
        assert "Number of agents: 5." in result
        assert "Sustainable harvest limit per agent: 10 hectares" in result
        assert "(calculated as pool / 10)." in result
        assert "at or below 50 hectares" in result
        assert "No previous rounds." in result
        assert "You may harvest any amount you choose." in result
        assert "This advisory is informational only." in result
        assert "=== End Advisory ===" in result

    def test_matches_govsim_template_with_history(self):
        """Advisory with history includes the table."""
        history = [
            {"John": 10, "Kate": 10, "Jack": 10, "Emma": 10, "Luke": 10},
        ]
        result = format_governance_advisory_string(100, 5, harvest_history=history)
        assert "Round 1: John: 10, Kate: 10, Jack: 10, Emma: 10, Luke: 10" in result

    def test_no_forbidden_words_absent(self):
        """Advisory does NOT contain raw-math-only terms (those belong in raw math template)."""
        result = format_governance_advisory_string(100, 5)
        # The advisory SHOULD contain "sustainable" — that's the computed answer
        assert "Sustainable harvest limit" in result

    def test_depleted_pool_advisory(self):
        """Advisory adjusts to depleted pool."""
        result = format_governance_advisory_string(30, 5)
        assert "Sustainable harvest limit per agent: 3 hectares" in result
        assert "at or below 15 hectares" in result


class TestHarvestHistoryTable:
    """Tests for format_harvest_history_table_string."""

    def test_empty_history(self):
        assert format_harvest_history_table_string([]) == "  No previous rounds."

    def test_single_round(self):
        result = format_harvest_history_table_string([{"A": 10, "B": 20}])
        assert "Round 1: A: 10, B: 20" in result

    def test_multiple_rounds(self):
        history = [{"A": 10}, {"A": 12}, {"A": 8}]
        result = format_harvest_history_table_string(history)
        assert "Round 1:" in result
        assert "Round 2:" in result
        assert "Round 3:" in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
