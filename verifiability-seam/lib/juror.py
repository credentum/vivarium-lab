"""Single juror call via OpenRouter: retry/backoff + structured JSON verdict.

Shared across all verifiability-seam experiments (001-collusion-separation,
future 002/003/004) -- this module knows nothing about any specific
experiment's conditions or item schema beyond "an item has an id and a
choices dict." Prompt construction is the calling experiment's job.

Mirrors the async OpenRouter pattern used elsewhere in this workspace
(project-vivarium/research-agents/run_parallel_scouts.py) and the Pydantic
confidence-scored contract convention (project-vivarium/press-corps/src/models/contracts.py).
"""

import os
import re
import json
import time
import asyncio
from typing import Optional
from pydantic import BaseModel, Field

RATE_LIMIT_DELAY = 0.5
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Mixed model families -- a real panel isn't a monoculture. Pulled from a
# live query of OpenRouter's /models catalog (see README.md "Models") rather
# than hardcoded from memory -- prior slugs like gemini-2.0-flash-001 had
# already been deprecated/renamed by the time this was checked.
JUROR_MODELS = {
    "claude": {"model_id": "anthropic/claude-haiku-4.5", "max_tokens": 300},
    # gpt-5-mini is a reasoning model -- its hidden chain-of-thought tokens
    # count against max_tokens. At 300 it burned the whole budget on
    # reasoning and returned empty content (finish_reason="length"),
    # confirmed against a live call. Needs real headroom.
    "gpt": {"model_id": "openai/gpt-5-mini", "max_tokens": 1500},
    "gemini": {"model_id": "google/gemini-2.5-flash", "max_tokens": 300},
    "llama": {"model_id": "meta-llama/llama-4-maverick", "max_tokens": 300},
    "deepseek": {"model_id": "deepseek/deepseek-v3.2", "max_tokens": 300},
}


class JurorVerdict(BaseModel):
    juror_name: str
    model_id: str
    item_id: str
    condition: str  # free-form label, meaning defined by the calling experiment
    chosen_answer: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str = ""
    latency_ms: int = 0
    error: Optional[str] = None


def extract_json_object(text: str) -> dict:
    """Extract a JSON object from raw model text, handling code fences."""
    patterns = [
        r"```json\s*(\{[\s\S]*?\})\s*```",
        r"```\s*(\{[\s\S]*?\})\s*```",
        r"(\{[\s\S]*\})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON object found in response: {text[:200]!r}")


async def run_juror(
    juror_name: str,
    item: dict,
    system_prompt: str,
    user_prompt: str,
    condition: str,
    retry_count: int = 3,
) -> JurorVerdict:
    """Call one juror on one item under one condition, with retry/backoff.

    `system_prompt` and `user_prompt` are built by the calling experiment
    (e.g. 001-collusion-separation's conditions.py) -- this module has no
    opinion on condition semantics or prompt wording.
    """
    import openai

    config = JUROR_MODELS[juror_name]
    model_id = config["model_id"]
    max_tokens = config.get("max_tokens", 300)
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        return JurorVerdict(
            juror_name=juror_name, model_id=model_id, item_id=item["id"],
            condition=condition, error="OPENROUTER_API_KEY not set",
        )

    client = openai.AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)

    last_error: Optional[Exception] = None
    for attempt in range(retry_count):
        try:
            start = time.time()
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0,
            )
            latency_ms = int((time.time() - start) * 1000)
            content = response.choices[0].message.content or ""
            parsed = extract_json_object(content)

            chosen = str(parsed.get("chosen_answer", "")).strip().lower()
            if chosen not in item["choices"]:
                raise ValueError(f"chosen_answer {chosen!r} not among item choices")

            return JurorVerdict(
                juror_name=juror_name, model_id=model_id, item_id=item["id"],
                condition=condition, chosen_answer=chosen,
                confidence=float(parsed.get("confidence", 0.0)),
                reason=str(parsed.get("reason", ""))[:500],
                latency_ms=latency_ms,
            )
        except Exception as e:
            last_error = e
            if attempt < retry_count - 1:
                await asyncio.sleep(RATE_LIMIT_DELAY * (2**attempt))

    return JurorVerdict(
        juror_name=juror_name, model_id=model_id, item_id=item["id"],
        condition=condition, error=str(last_error),
    )
