#!/usr/bin/env python3
"""
Movable Feast v2.7 - Study Execution Script
A Holiday Season Snapshot: How 4 Frontier LLMs Handle Movable Holiday Dates

Vivarium Lab - December 2024
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment from project root
from pathlib import Path
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Study configuration - Current Frontier Models (Dec 2024)
MODELS = {
    "grok-4.1-fast": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4.1-fast:free",  # Free tier available
        "max_tokens": 50,
    },
    "gemini-3-pro": {
        "provider": "openrouter",
        "model_id": "google/gemini-3-pro-preview",
        "max_tokens": 500,  # Reasoning model needs more tokens
    },
    "gpt-5.1": {
        "provider": "openrouter",
        "model_id": "openai/gpt-5.1",  # Via OpenRouter
        "max_tokens": 50,
    },
    "llama-4-maverick": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-4-maverick",
        "max_tokens": 50,
    },
}

PROMPT_TEMPLATE = "What holiday falls on {date}? Answer with just the holiday name."


@dataclass
class Response:
    item_id: int
    model: str
    date: str
    expected: str
    response: str
    correct: bool
    error: Optional[str] = None
    latency_ms: int = 0


def load_ground_truth():
    """Load the ground truth test items."""
    gt_path = Path(__file__).parent.parent / "data" / "ground_truth.json"
    with open(gt_path) as f:
        return json.load(f)


def check_correct(response: str, expected: str, alias_sets: dict) -> bool:
    """Check if response matches expected holiday (with aliases)."""
    if not response:
        return False

    response_lower = response.strip().lower()
    expected_lower = expected.lower()

    # Direct match
    if response_lower == expected_lower:
        return True

    # Check aliases
    aliases = alias_sets.get(expected, [expected])
    for alias in aliases:
        if alias.lower() in response_lower or response_lower in alias.lower():
            return True

    return False


async def query_openai(prompt: str, model_id: str) -> tuple[str, int]:
    """Query OpenAI API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    start = time.time()
    response = await client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
        temperature=0,
    )
    latency = int((time.time() - start) * 1000)

    return response.choices[0].message.content.strip(), latency


async def query_anthropic(prompt: str, model_id: str) -> tuple[str, int]:
    """Query Anthropic API."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    start = time.time()
    response = await client.messages.create(
        model=model_id,
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}],
    )
    latency = int((time.time() - start) * 1000)

    return response.content[0].text.strip(), latency


async def query_google(prompt: str, model_id: str) -> tuple[str, int]:
    """Query Google Gemini API."""
    import google.generativeai as genai

    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(model_id)

    start = time.time()
    response = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config={"max_output_tokens": 50, "temperature": 0}
    )
    latency = int((time.time() - start) * 1000)

    return response.text.strip(), latency


async def query_openrouter(prompt: str, model_id: str, max_tokens: int = 50) -> tuple[str, int]:
    """Query OpenRouter API (unified access to all frontier models)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )

    start = time.time()
    response = await client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0,
    )
    latency = int((time.time() - start) * 1000)

    # Handle reasoning models that may return empty content with reasoning field
    content = response.choices[0].message.content or ""
    return content.strip(), latency


async def query_model(model_name: str, prompt: str) -> tuple[str, int, Optional[str]]:
    """Query a model and return response, latency, and any error."""
    config = MODELS[model_name]
    provider = config["provider"]
    model_id = config["model_id"]
    max_tokens = config.get("max_tokens", 50)

    try:
        if provider == "openrouter":
            return (*await query_openrouter(prompt, model_id, max_tokens), None)
        elif provider == "openai":
            return (*await query_openai(prompt, model_id), None)
        elif provider == "anthropic":
            return (*await query_anthropic(prompt, model_id), None)
        elif provider == "google":
            return (*await query_google(prompt, model_id), None)
        else:
            return "", 0, f"Unknown provider: {provider}"
    except Exception as e:
        return "", 0, str(e)


async def run_model(model_name: str, items: list, alias_sets: dict, dry_run: bool = False) -> list[Response]:
    """Run all items for a single model."""
    results = []

    for i, item in enumerate(items):
        prompt = PROMPT_TEMPLATE.format(date=item["date"])

        if dry_run:
            response_text = f"[DRY RUN] {item['holiday']}"
            latency = 0
            error = None
        else:
            response_text, latency, error = await query_model(model_name, prompt)

        correct = check_correct(response_text, item["holiday"], alias_sets)

        result = Response(
            item_id=item["id"],
            model=model_name,
            date=item["date"],
            expected=item["holiday"],
            response=response_text,
            correct=correct,
            error=error,
            latency_ms=latency,
        )
        results.append(result)

        status = "✓" if correct else "✗"
        print(f"  [{model_name}] {i+1}/{len(items)} {item['date']} -> {response_text[:25]:25s} {status}")

        # Rate limiting per model
        if not dry_run:
            await asyncio.sleep(0.3)

    return results


async def run_study(models: list[str] = None, dry_run: bool = False, parallel: bool = True):
    """Run the full study."""
    gt = load_ground_truth()
    items = gt["items"]
    alias_sets = gt["alias_sets"]

    if models is None:
        models = list(MODELS.keys())

    total = len(models) * len(items)

    print(f"=" * 60)
    print(f"MOVABLE FEAST v2.7 - Study Execution")
    print(f"=" * 60)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Models: {', '.join(models)}")
    print(f"Items: {len(items)}")
    print(f"Total queries: {total}")
    print(f"Parallel: {parallel}")
    print(f"Dry run: {dry_run}")
    print(f"=" * 60)

    if parallel and len(models) > 1:
        # Run all models in parallel
        print(f"\nRunning {len(models)} models in parallel...")
        tasks = [run_model(m, items, alias_sets, dry_run) for m in models]
        all_results = await asyncio.gather(*tasks)
        results = [r for model_results in all_results for r in model_results]
    else:
        # Sequential execution
        results = []
        for model_name in models:
            print(f"\n[{model_name}] Starting...")
            model_results = await run_model(model_name, items, alias_sets, dry_run)
            results.extend(model_results)

    # Print summaries
    print(f"\n{'=' * 60}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 60}")
    for model_name in models:
        model_results = [r for r in results if r.model == model_name]
        correct = sum(1 for r in model_results if r.correct)
        accuracy = correct / len(model_results) if model_results else 0
        print(f"  {model_name:20s}: {accuracy:6.1%} ({correct}/{len(model_results)})")

    # Save results
    output_dir = Path(__file__).parent.parent / "data" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"results_{timestamp}.json"

    output = {
        "metadata": {
            "study": "Movable Feast v2.7",
            "timestamp": datetime.now().isoformat(),
            "models": models,
            "items": len(items),
            "dry_run": dry_run,
        },
        "results": [asdict(r) for r in results],
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 60}")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run Movable Feast v2.7 Study")
    parser.add_argument("--models", nargs="+", choices=list(MODELS.keys()),
                        help="Models to test (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without making API calls")

    args = parser.parse_args()

    asyncio.run(run_study(models=args.models, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
