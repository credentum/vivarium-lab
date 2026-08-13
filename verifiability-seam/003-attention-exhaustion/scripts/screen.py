#!/usr/bin/env python3
"""Screen candidate dose-finding probes at position=1, k repeats, nonzero
temperature. Keep only items where jurors reliably succeed fresh -- a probe
needs headroom to fall from, or "no degradation found" is uninformative
(the floor-effect problem discovered when ambig_06 was used as the probe).
"""

import sys
import json
import asyncio
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv("/claude-workspace/.env")
sys.path.insert(0, str(Path(__file__).parent))

from session import run_session

# Reuse 001's 12 hand-authored "clear" items as candidates -- already
# empirically verified as 100% both-model-correct under a related (not
# identical) prompt in 001's own Control condition. Screening here checks
# whether that holds for this harness's prompt too, rather than assuming it.
ITEM_BANK_001 = Path(__file__).parent.parent.parent / "001-collusion-separation" / "data" / "item_bank.json"


def load_candidates() -> list[dict]:
    items = json.load(open(ITEM_BANK_001))["items"]
    return [i for i in items if i["bucket"] == "clear"]


async def screen_item(juror_name: str, item: dict, k: int, temperature: float) -> float:
    """Run k repeats at position=1, return fraction correct."""
    correct = 0
    for _ in range(k):
        session = await run_session(juror_name, [], item, probe_position=1, temperature=temperature)
        t = session.probe_turn
        if t and t.error is None and t.chosen_answer == item["ground_truth"]:
            correct += 1
    return correct / k


async def run_screen(juror_names: list[str], k: int = 5, temperature: float = 0.7) -> dict:
    candidates = load_candidates()
    results = defaultdict(dict)
    for item in candidates:
        print(f"[{item['id']}] {item['prompt'][:50]}...", flush=True)
        for juror_name in juror_names:
            rate = await screen_item(juror_name, item, k, temperature)
            results[item["id"]][juror_name] = rate
            print(f"  {juror_name:10s} {rate:.2f} ({int(rate*k)}/{k})")
    return dict(results)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Screen dose-finding probe candidates")
    parser.add_argument("--jurors", nargs="+", default=["claude", "gemini"])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--threshold", type=float, default=0.80)
    args = parser.parse_args()

    results = asyncio.run(run_screen(args.jurors, args.k, args.temperature))

    print("\n" + "=" * 60)
    print(f"PASSED (all jurors >= {args.threshold:.0%} correct fresh):")
    passed = []
    for item_id, per_juror in results.items():
        if all(rate >= args.threshold for rate in per_juror.values()):
            passed.append(item_id)
            print(f"  {item_id:12s} " + " ".join(f"{j}={r:.2f}" for j, r in per_juror.items()))

    print(f"\n{len(passed)}/{len(results)} candidates passed.")

    out_file = Path(__file__).parent.parent / "data" / "ladder" / "screen_results.json"
    with open(out_file, "w") as f:
        json.dump({"results": results, "passed": passed, "k": args.k, "temperature": args.temperature}, f, indent=2)
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
