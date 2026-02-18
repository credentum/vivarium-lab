"""Tests for governance_monitoring.py — health and defection detection."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from governance_monitoring import (
    get_commons_health_string,
    check_harvest_exceeds_sustainable_limit_boolean,
    detect_defection_risk_table,
    get_defection_analysis_table,
)


class TestCommonsHealth:
    """Tests for get_commons_health_string."""

    def test_thriving(self):
        assert get_commons_health_string(100) == "thriving"

    def test_thriving_boundary(self):
        assert get_commons_health_string(81) == "thriving"

    def test_stable(self):
        assert get_commons_health_string(50) == "stable"

    def test_stable_boundary(self):
        assert get_commons_health_string(80) == "stable"

    def test_unhealthy(self):
        assert get_commons_health_string(20) == "unhealthy"

    def test_critical(self):
        assert get_commons_health_string(10) == "critical"

    def test_collapsed(self):
        assert get_commons_health_string(4) == "collapsed"

    def test_at_collapse_threshold(self):
        """Pool at exactly 5 is critical, not collapsed."""
        assert get_commons_health_string(5) != "collapsed"

    def test_zero_pool(self):
        assert get_commons_health_string(0) == "collapsed"


class TestHarvestExceedsLimit:
    """Tests for check_harvest_exceeds_sustainable_limit_boolean."""

    def test_within_limit(self):
        assert check_harvest_exceeds_sustainable_limit_boolean(10, 10) is False

    def test_exceeds_limit(self):
        assert check_harvest_exceeds_sustainable_limit_boolean(11, 10) is True

    def test_zero_harvest(self):
        assert check_harvest_exceeds_sustainable_limit_boolean(0, 10) is False

    def test_exactly_at_limit(self):
        assert check_harvest_exceeds_sustainable_limit_boolean(10.0, 10.0) is False


class TestDefectionRisk:
    """Tests for detect_defection_risk_table."""

    def test_cooperative_agent(self):
        """Agent taking 10 against norm of 10 = low risk."""
        result = detect_defection_risk_table([10, 10, 10], 10)
        assert result["risk_level"] == "low"
        assert result["is_escalating"] is False

    def test_emma_pattern_sudden_raid(self):
        """Emma's GovSim pattern: stable then sudden 58."""
        result = detect_defection_risk_table([10, 10, 10, 10, 58], 10)
        assert result["risk_level"] == "high"
        assert result["max_recent"] == 58

    def test_emma_pattern_total_raid(self):
        """Emma requesting 100 against norm of 10."""
        result = detect_defection_risk_table([10, 100], 10)
        assert result["risk_level"] == "high"

    def test_moderate_overshoot(self):
        """Agent taking 16 against norm of 10."""
        result = detect_defection_risk_table([10, 16], 10)
        assert result["risk_level"] == "medium"

    def test_escalating(self):
        """Each round higher than the last."""
        result = detect_defection_risk_table([8, 10, 12, 15], 10)
        assert result["is_escalating"] is True

    def test_not_escalating(self):
        """Varies up and down."""
        result = detect_defection_risk_table([10, 12, 10, 11], 10)
        assert result["is_escalating"] is False

    def test_empty_history(self):
        result = detect_defection_risk_table([], 10)
        assert result["risk_level"] == "low"


class TestDefectionAnalysis:
    """Tests for get_defection_analysis_table."""

    def test_all_cooperative(self):
        """All agents at or below limit."""
        harvests = {
            "John": [10, 10, 10],
            "Kate": [10, 10, 10],
        }
        result = get_defection_analysis_table(harvests, 10)
        for agent in result:
            assert agent["times_exceeded"] == 0
            assert agent["compliance_rate"] == 1.0

    def test_single_defector(self):
        """One agent exceeds, others don't — matches GovSim advisory pattern."""
        harvests = {
            "John": [10, 10, 10],
            "Kate": [10, 10, 10],
            "Emma": [10, 10, 58],
        }
        result = get_defection_analysis_table(harvests, 10)
        # Sorted by compliance rate, worst first
        assert result[0]["name"] == "Emma"
        assert result[0]["times_exceeded"] == 1
        assert result[0]["max_single"] == 58

    def test_distributed_defection(self):
        """Multiple agents exceed — matches universalization pattern."""
        harvests = {
            "John": [10, 100],
            "Kate": [10, 15],
            "Jack": [10, 20],
            "Emma": [10, 16],
        }
        result = get_defection_analysis_table(harvests, 10)
        defectors = [a for a in result if a["times_exceeded"] > 0]
        assert len(defectors) == 4  # All exceeded at some point

    def test_empty_history(self):
        result = get_defection_analysis_table({"John": []}, 10)
        assert result[0]["rounds_played"] == 0
        assert result[0]["compliance_rate"] == 1.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
