"""Load and validate the item bank for Seam Disproof 001."""

import json
from pathlib import Path

ITEM_BANK_PATH = Path(__file__).parent.parent / "data" / "item_bank.json"

REQUIRED_ITEM_KEYS = {"id", "bucket", "prompt", "choices", "ground_truth", "collusion_target"}
VALID_BUCKETS = {"clear", "ambiguous"}


def load_item_bank(path: Path = ITEM_BANK_PATH) -> list[dict]:
    """Load and validate the item bank. Raises ValueError on any schema violation."""
    with open(path) as f:
        data = json.load(f)

    items = data["items"]
    seen_ids = set()

    for item in items:
        missing = REQUIRED_ITEM_KEYS - item.keys()
        if missing:
            raise ValueError(f"item {item.get('id', '?')} missing keys: {missing}")
        if item["id"] in seen_ids:
            raise ValueError(f"duplicate item id: {item['id']}")
        seen_ids.add(item["id"])
        if item["bucket"] not in VALID_BUCKETS:
            raise ValueError(f"item {item['id']} has invalid bucket: {item['bucket']}")
        if len(item["choices"]) != 4:
            raise ValueError(f"item {item['id']} does not have exactly 4 choices")
        if item["ground_truth"] not in item["choices"]:
            raise ValueError(f"item {item['id']} ground_truth not among choices")
        if item["collusion_target"] not in item["choices"]:
            raise ValueError(f"item {item['id']} collusion_target not among choices")
        if item["ground_truth"] == item["collusion_target"]:
            raise ValueError(f"item {item['id']} ground_truth == collusion_target")

    return items


def format_choices(choices: dict) -> str:
    """Render a choices dict as a lettered list for the juror prompt."""
    return "\n".join(f"{key}) {text}" for key, text in sorted(choices.items()))


if __name__ == "__main__":
    items = load_item_bank()
    clear = [i for i in items if i["bucket"] == "clear"]
    ambiguous = [i for i in items if i["bucket"] == "ambiguous"]
    print(f"Loaded {len(items)} items: {len(clear)} clear, {len(ambiguous)} ambiguous")
