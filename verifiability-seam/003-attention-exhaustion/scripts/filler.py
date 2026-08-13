"""Cheap, programmatic filler-item generator for docket load.

No LLM call needed to build these -- filler exists to consume context and
turns, not to be scientifically interesting on its own. Per design: filler
must be predominantly routine/clear, not contested, or a docket conflates
"long" with "brutal" and measures difficulty-load instead of volume-load.
"""

import random

_LETTERS = ["a", "b", "c", "d"]


def _mc_item(item_id: str, prompt: str, correct: int, distractors: list[int]) -> dict:
    values = [correct] + distractors
    random.Random(item_id).shuffle(values)
    choices = {letter: str(v) for letter, v in zip(_LETTERS, values)}
    ground_truth = next(letter for letter, v in choices.items() if int(v) == correct)
    return {"id": item_id, "bucket": "filler", "prompt": prompt, "choices": choices, "ground_truth": ground_truth}


def generate_filler_items(n: int, seed: int = 0) -> list[dict]:
    """Generate n simple, unambiguous arithmetic items -- routine docket filler."""
    rng = random.Random(seed)
    items = []
    for i in range(n):
        a, b = rng.randint(2, 99), rng.randint(2, 99)
        op = rng.choice(["+", "-", "*"])
        if op == "+":
            correct = a + b
            prompt = f"What is {a} + {b}?"
        elif op == "-":
            a, b = max(a, b), min(a, b)  # keep it non-negative
            correct = a - b
            prompt = f"What is {a} - {b}?"
        else:
            correct = a * b
            prompt = f"What is {a} x {b}?"
        spread = max(1, abs(correct) // 10)
        distractors = set()
        while len(distractors) < 3:
            d = correct + rng.choice([-1, 1]) * rng.randint(1, spread + 5)
            if d != correct:
                distractors.add(d)
        items.append(_mc_item(f"filler_{seed}_{i:04d}", prompt, correct, list(distractors)))
    return items


if __name__ == "__main__":
    items = generate_filler_items(5, seed=1)
    for it in items:
        print(it["id"], it["prompt"], it["choices"], "GT=" + it["ground_truth"])
