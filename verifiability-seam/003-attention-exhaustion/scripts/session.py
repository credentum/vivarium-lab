"""Multi-turn juror session: grind through a docket, probe at a controlled position.

Load is structural, not instructed -- nobody tells the juror it is tired.
Position within a real, growing conversation is the only manipulation.
"""

import os
import re
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from juror import JUROR_MODELS, OPENROUTER_BASE_URL, extract_json_object

SYSTEM_PROMPT = (
    "You are evaluating a sequence of multiple-choice items, one at a time, "
    "in a single ongoing session. For each item, respond with ONLY a JSON "
    "object in this exact format, no other text:\n"
    '{"chosen_answer": "<letter>", "confidence": <a decimal from 0.0 to 1.0 '
    "inclusive, representing how sure you are -- 1.0 is fully confident, 0.0 "
    'is a total guess; never negative>, "reason": "<one or two sentence reason>"}'
)


def format_choices(choices: dict) -> str:
    return "\n".join(f"{key}) {text}" for key, text in sorted(choices.items()))


def build_user_turn(item: dict) -> str:
    return f"{item['prompt']}\n\n{format_choices(item['choices'])}"


class TurnResult(BaseModel):
    turn_index: int  # 1-indexed position in the session
    item_id: str
    chosen_answer: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str = ""
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None


class SessionResult(BaseModel):
    juror_name: str
    model_id: str
    probe_item_id: str
    probe_position: int
    turns: list[TurnResult] = Field(default_factory=list)

    @property
    def probe_turn(self) -> Optional[TurnResult]:
        return self.turns[-1] if self.turns else None

    @property
    def total_prompt_tokens(self) -> int:
        return sum(t.prompt_tokens for t in self.turns)

    @property
    def total_completion_tokens(self) -> int:
        return sum(t.completion_tokens for t in self.turns)


async def run_session(
    juror_name: str,
    docket_items: list[dict],
    probe_item: dict,
    probe_position: int,
    retry_count: int = 3,
    temperature: float = 0.0,
) -> SessionResult:
    """Run one juror through `probe_position - 1` filler items, then the probe.

    docket_items must supply at least `probe_position - 1` items; the probe
    item must not itself appear among them (checked by the caller).

    temperature=0 (default) is deterministic -- fine for a single point
    estimate, useless for repeats. Screening/rate-cell runs that need real
    sampling variance across k repeats must pass temperature>0.
    """
    import openai

    config = JUROR_MODELS[juror_name]
    model_id = config["model_id"]
    max_tokens = config.get("max_tokens", 300)
    api_key = os.environ.get("OPENROUTER_API_KEY")

    result = SessionResult(juror_name=juror_name, model_id=model_id,
                            probe_item_id=probe_item["id"], probe_position=probe_position)

    if not api_key:
        result.turns.append(TurnResult(turn_index=probe_position, item_id=probe_item["id"],
                                        error="OPENROUTER_API_KEY not set"))
        return result

    client = openai.AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    sequence = list(docket_items[: probe_position - 1]) + [probe_item]
    assert len(sequence) == probe_position

    for i, item in enumerate(sequence, start=1):
        messages.append({"role": "user", "content": build_user_turn(item)})

        last_error: Optional[Exception] = None
        turn_result = None
        for attempt in range(retry_count):
            try:
                start = time.time()
                response = await client.chat.completions.create(
                    model=model_id, messages=messages, max_tokens=max_tokens, temperature=temperature,
                )
                latency_ms = int((time.time() - start) * 1000)
                content = response.choices[0].message.content or ""
                parsed = extract_json_object(content)
                chosen = str(parsed.get("chosen_answer", "")).strip().lower()
                if chosen not in item["choices"]:
                    raise ValueError(f"chosen_answer {chosen!r} not among choices")

                usage = response.usage
                turn_result = TurnResult(
                    turn_index=i, item_id=item["id"], chosen_answer=chosen,
                    confidence=float(parsed.get("confidence", 0.0)),
                    reason=str(parsed.get("reason", ""))[:500],
                    latency_ms=latency_ms,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                )
                messages.append({"role": "assistant", "content": content})
                break
            except Exception as e:
                last_error = e
                if attempt < retry_count - 1:
                    await asyncio.sleep(0.5 * (2**attempt))

        if turn_result is None:
            # Filler-turn failures don't need to be correct, just need the
            # session to keep flowing -- append a stub assistant turn so
            # context continues to accumulate. Probe-turn failures are
            # recorded as a real error (no stub, no silent pass).
            if item["id"] == probe_item["id"]:
                result.turns.append(TurnResult(turn_index=i, item_id=item["id"], error=str(last_error)))
                return result
            stub = '{"chosen_answer": "a", "confidence": 0.5, "reason": "stub after retry failure"}'
            messages.append({"role": "assistant", "content": stub})
            turn_result = TurnResult(turn_index=i, item_id=item["id"], error=f"filler stub: {last_error}")

        result.turns.append(turn_result)

    return result
