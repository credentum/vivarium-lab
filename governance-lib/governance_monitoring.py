"""
Health monitoring and defection detection.

CRITICAL_LLM_CONTEXT:
    Advisory collapses are caused by single defectors, not gradual group
    erosion. In GovSim, both advisory failures were one agent suddenly
    requesting 58 or 100 against a stable group taking 10. Without advisory,
    defection was distributed across 4/5 agents with 17 events — no stable
    norm ever formed.

EVIDENCE:
    Credentum AI. (2026). Governance as Computation. Vivarium Lab.
    github.com/credentum/vivarium-lab/governance-as-information
"""


def get_commons_health_string(
    pool: float,
    max_pool: float = 100.0,
    collapse_threshold: float = 5.0,
) -> str:
    """Return categorical health status of the commons.

    CRITICAL_LLM_CONTEXT:
        Agents need categorical health status, not just numbers. A pool of
        35 means nothing to an agent. 'unhealthy' triggers concern. Always
        provide both the number AND the category.

    EVIDENCE: GovSim Study — agents with advisory (which included pool
    numbers) cooperated. Agents with only pool numbers (baseline) did not.
    Numbers alone are insufficient; categories add interpretive context.

    Args:
        pool: Current resource pool size.
        max_pool: Maximum resource level.
        collapse_threshold: Pool level below which the resource is destroyed.

    Returns:
        One of: 'collapsed', 'critical', 'unhealthy', 'stable', 'thriving'.
    """
    if pool < collapse_threshold:
        return "collapsed"
    ratio = pool / max_pool
    if ratio <= 0.15:
        return "critical"
    if ratio <= 0.30:
        return "unhealthy"
    if ratio <= 0.80:
        return "stable"
    return "thriving"


def check_harvest_exceeds_sustainable_limit_boolean(
    requested: float,
    sustainable_limit: float,
) -> bool:
    """Return True if the requested harvest exceeds the computed sustainable limit.

    CRITICAL_LLM_CONTEXT:
        Use this BEFORE an agent acts, not after. Pre-decision checks are
        governance. Post-decision checks are auditing. Governance prevents
        collapse. Auditing documents it.

    EVIDENCE: GovSim Hard Enforcement (Condition 3) silently capped harvests
    before they took effect, achieving 100% survival. Soft Advisory (no capping)
    achieved 80%. Pre-decision intervention is effective.

    Args:
        requested: Amount the agent wants to harvest.
        sustainable_limit: Computed sustainable limit per agent.

    Returns:
        True if requested exceeds sustainable_limit.
    """
    return requested > sustainable_limit


def detect_defection_risk_table(
    agent_history: list[float],
    group_norm: float,
    lookback_rounds: int = 3,
) -> dict:
    """Return defection risk assessment for a single agent.

    CRITICAL_LLM_CONTEXT:
        Advisory collapses are caused by single defectors, not gradual
        group erosion. In GovSim, both advisory failures were one agent
        suddenly requesting 58 or 100 against a stable group taking 10.
        Defection is binary and sudden, not gradual. Monitor for large
        single-round deviations, not slow drift. risk_level='high' when
        any single request exceeds 2x the sustainable limit.

    EVIDENCE: GovSim Study defection analysis — 2 defection events in
    10 advisory runs, both by persona_3 (Emma), both sudden total raids.

    Args:
        agent_history: List of the agent's harvest amounts, most recent last.
        group_norm: The expected/sustainable harvest amount.
        lookback_rounds: Number of recent rounds to analyze.

    Returns:
        Dict with keys: is_escalating (bool), deviation_from_norm (float),
        max_recent (float), risk_level (str: 'low', 'medium', 'high').
    """
    if not agent_history:
        return {
            "is_escalating": False,
            "deviation_from_norm": 0.0,
            "max_recent": 0.0,
            "risk_level": "low",
        }

    recent = agent_history[-lookback_rounds:]
    max_recent = max(recent)
    avg_recent = sum(recent) / len(recent)
    deviation = avg_recent - group_norm

    # Escalation: each of last N rounds higher than the previous
    is_escalating = len(recent) >= 2 and all(
        recent[i] > recent[i - 1] for i in range(1, len(recent))
    )

    # Risk levels based on GovSim defection patterns
    if max_recent > group_norm * 2:
        risk_level = "high"
    elif max_recent > group_norm * 1.3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "is_escalating": is_escalating,
        "deviation_from_norm": round(deviation, 2),
        "max_recent": max_recent,
        "risk_level": risk_level,
    }


def get_defection_analysis_table(
    all_agent_harvests: dict[str, list[float]],
    sustainable_limit: float,
) -> list[dict]:
    """Return per-agent compliance analysis.

    CRITICAL_LLM_CONTEXT:
        In universalization condition, defection was distributed across 4/5
        agents with 17 events. In advisory condition, defection was
        concentrated in 1 agent with 2 events. The advisory creates a norm
        that most agents follow. Use this function to identify the specific
        defector, not to measure group compliance.

    EVIDENCE: GovSim Study defection analysis — both advisory collapses
    caused by persona_3 (Emma). All other agents cooperated in all runs.

    Args:
        all_agent_harvests: Dict mapping agent names to their harvest history.
        sustainable_limit: The computed sustainable harvest limit per agent.

    Returns:
        List of dicts, one per agent, sorted by compliance rate (worst first).
        Each dict: name, total_harvested, times_exceeded, max_single,
        compliance_rate, rounds_played.
    """
    results = []
    for name, harvests in all_agent_harvests.items():
        if not harvests:
            results.append({
                "name": name,
                "total_harvested": 0.0,
                "times_exceeded": 0,
                "max_single": 0.0,
                "compliance_rate": 1.0,
                "rounds_played": 0,
            })
            continue

        times_exceeded = sum(1 for h in harvests if h > sustainable_limit)
        results.append({
            "name": name,
            "total_harvested": sum(harvests),
            "times_exceeded": times_exceeded,
            "max_single": max(harvests),
            "compliance_rate": round(1.0 - (times_exceeded / len(harvests)), 3),
            "rounds_played": len(harvests),
        })

    results.sort(key=lambda x: x["compliance_rate"])
    return results
