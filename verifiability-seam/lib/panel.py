"""Run N jurors on one item under one condition, then aggregate panel-level signals.

Shared across all verifiability-seam experiments. Panel-level signals are
exactly the output-only surface a detector is allowed to see: majority
answer, agreement fraction, mean/spread confidence, mean reasoning length,
mean/spread latency. Never model internals.

This module has no opinion on what "condition" means, or on any
experiment-specific interpretation of the majority answer (e.g.
001-collusion-separation's ground_truth/collusion_target comparisons) --
callers build system_prompt/user_prompt themselves and layer their own
interpretation on top of the returned PanelSummary.
"""

import asyncio
from statistics import mean, pstdev
from typing import Optional
from pydantic import BaseModel, Field

from juror import run_juror, JurorVerdict, JUROR_MODELS, RATE_LIMIT_DELAY


class PanelSummary(BaseModel):
    item_id: str
    condition: str
    n_jurors: int
    n_errors: int
    majority_answer: Optional[str] = None
    agreement_fraction: float = 0.0
    mean_confidence: float = 0.0
    confidence_spread: float = 0.0
    mean_reason_length: float = 0.0
    mean_latency_ms: float = 0.0
    latency_spread: float = 0.0
    verdicts: list[JurorVerdict] = Field(default_factory=list)


async def run_panel(
    item: dict,
    condition: str,
    system_prompt: str,
    user_prompt: str,
    juror_names: Optional[list[str]] = None,
) -> PanelSummary:
    if juror_names is None:
        juror_names = list(JUROR_MODELS.keys())

    tasks = []
    for i, name in enumerate(juror_names):
        if i > 0:
            await asyncio.sleep(RATE_LIMIT_DELAY)
        tasks.append(asyncio.create_task(
            run_juror(name, item, system_prompt, user_prompt, condition)
        ))
    verdicts = list(await asyncio.gather(*tasks))

    return summarize_panel(item, condition, verdicts)


def summarize_panel(item: dict, condition: str, verdicts: list[JurorVerdict]) -> PanelSummary:
    valid = [v for v in verdicts if v.error is None and v.chosen_answer]
    n_errors = len(verdicts) - len(valid)

    base_kwargs = dict(
        item_id=item["id"], condition=condition,
        n_jurors=len(verdicts), n_errors=n_errors, verdicts=verdicts,
    )

    if not valid:
        return PanelSummary(**base_kwargs)

    answers = [v.chosen_answer for v in valid]
    counts = {a: answers.count(a) for a in set(answers)}
    # Deterministic tie-break: iterate choice letters in sorted order so a
    # tie always resolves the same way across runs (avoids relying on
    # Python's hash-randomized set ordering for reproducibility).
    majority_answer = max(sorted(counts), key=lambda a: counts[a])
    agreement_fraction = counts[majority_answer] / len(valid)

    confidences = [v.confidence for v in valid]
    reason_lengths = [len(v.reason.split()) for v in valid]
    latencies = [v.latency_ms for v in valid]

    return PanelSummary(
        **base_kwargs,
        majority_answer=majority_answer,
        agreement_fraction=agreement_fraction,
        mean_confidence=mean(confidences),
        confidence_spread=pstdev(confidences) if len(confidences) > 1 else 0.0,
        mean_reason_length=mean(reason_lengths),
        mean_latency_ms=mean(latencies),
        latency_spread=pstdev(latencies) if len(latencies) > 1 else 0.0,
    )
