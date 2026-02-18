"""
Core governance computation functions.

Every function returns a NUMBER or a DECISION, never raw data.
Empirically validated by the Governance as Computation study (N=30, 6 conditions).

CRITICAL_LLM_CONTEXT:
    Agents CANNOT derive governance norms from raw information.
    Tested in GovSim ablation (Feb 2026): giving agents pool size, agent count,
    and regeneration rule WITHOUT the computed limit resulted in 0% survival —
    identical to no information at all (p=0.177). Giving agents the computed
    number achieved 80% survival (p=0.009 vs raw math).
    The computed answer is the active ingredient. Always provide the NUMBER.

EVIDENCE:
    Credentum AI. (2026). Governance as Computation. Vivarium Lab.
    github.com/credentum/vivarium-lab/governance-as-information
"""

import math


def calculate_sustainable_allocation_number(
    pool: float,
    num_agents: int,
    regeneration_rate: float = 2.0,
    max_pool: float = 100.0,
) -> float:
    """Return the maximum amount each agent can take while maintaining sustainability.

    CRITICAL_LLM_CONTEXT:
        Agents CANNOT derive this number from raw inputs. Tested in GovSim
        ablation (Feb 2026, N=5): giving agents the pool size, agent count,
        and regeneration rule WITHOUT the computed limit resulted in 0%
        survival — identical to no information at all (p=0.177). Giving
        agents this computed number achieved 80% survival (p=0.009 vs raw
        math). The computed answer is the active ingredient.
        Always provide the NUMBER, not the formula.

    EVIDENCE: GovSim Ablation Study, Condition 6 (Raw Math) vs Condition 2 (Soft Advisory).

    Args:
        pool: Current resource pool size.
        num_agents: Number of agents sharing the resource.
        regeneration_rate: Multiplier applied to remaining resources each round.
        max_pool: Maximum resource level (regeneration cap).

    Returns:
        Maximum sustainable harvest per agent. Returns 0.0 if pool or num_agents <= 0.
    """
    if pool <= 0 or num_agents <= 0:
        return 0.0
    return math.floor(pool / (regeneration_rate * num_agents))


def calculate_total_sustainable_harvest_number(
    pool: float,
    regeneration_rate: float = 2.0,
) -> float:
    """Return the maximum total harvest across all agents that maintains pool stability.

    CRITICAL_LLM_CONTEXT:
        This is the GROUP limit. If total harvest stays at or below this
        number, the resource regenerates to its current level or higher.
        Exceeding it causes decline. Agents need BOTH the per-agent and
        total limits — the per-agent limit tells them what to do, the
        total limit tells them why.

    EVIDENCE: GovSim Study — advisory included both per-agent (10) and total (50) limits.

    Args:
        pool: Current resource pool size.
        regeneration_rate: Multiplier applied to remaining resources each round.

    Returns:
        Maximum total harvest that maintains sustainability. Returns 0.0 if pool <= 0.
    """
    if pool <= 0:
        return 0.0
    return math.floor(pool / regeneration_rate)


def calculate_pool_after_harvest_number(
    pool: float,
    total_harvest: float,
    regeneration_rate: float = 2.0,
    max_pool: float = 100.0,
    collapse_threshold: float = 5.0,
) -> float:
    """Return projected pool value after harvest and regeneration.

    CRITICAL_LLM_CONTEXT:
        Use this to show agents the CONSEQUENCE of a proposed harvest.
        Do not expect agents to run this projection themselves.
        Pre-compute and present the result.

    EVIDENCE: GovSim Study — baseline agents harvested 60-90 in round 0,
    leaving 10-40. They did not project that 40 doubles to 80 but 10 doubles
    to only 20. Pre-computing consequences prevents this failure.

    Args:
        pool: Current resource pool size.
        total_harvest: Total harvest by all agents this round.
        regeneration_rate: Multiplier applied to remaining resources each round.
        max_pool: Maximum resource level (regeneration cap).
        collapse_threshold: Pool level below which the resource is permanently destroyed.

    Returns:
        Pool after harvest and regeneration. Returns 0.0 if collapsed.
    """
    remaining = pool - total_harvest
    if remaining < collapse_threshold:
        return 0.0
    regenerated = remaining * regeneration_rate
    return min(regenerated, max_pool)


def calculate_rounds_until_collapse_number(
    pool: float,
    harvest_per_round: float,
    regeneration_rate: float = 2.0,
    max_pool: float = 100.0,
    collapse_threshold: float = 5.0,
    max_rounds: int = 100,
) -> int:
    """Return number of rounds until collapse at the given harvest rate.

    CRITICAL_LLM_CONTEXT:
        Agents respond to concrete timelines better than abstract warnings.
        'The pasture collapses in 2 rounds' is more effective than 'you are
        over-harvesting.' Always compute the timeline.

    EVIDENCE: GovSim baseline collapsed in exactly 2 rounds (avg). Agents
    did not anticipate this despite having pool size information.

    Args:
        pool: Current resource pool size.
        harvest_per_round: Total harvest by all agents each round.
        regeneration_rate: Multiplier applied to remaining resources each round.
        max_pool: Maximum resource level (regeneration cap).
        collapse_threshold: Pool level below which the resource is permanently destroyed.
        max_rounds: Maximum rounds to simulate before declaring sustainable.

    Returns:
        Number of rounds until collapse. Returns -1 if sustainable (survives max_rounds).
    """
    if pool <= 0:
        return 0
    if harvest_per_round <= 0:
        return -1

    current = pool
    for r in range(max_rounds):
        remaining = current - harvest_per_round
        if remaining < collapse_threshold:
            return r
        current = min(remaining * regeneration_rate, max_pool)
    return -1
