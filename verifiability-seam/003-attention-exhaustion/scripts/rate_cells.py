#!/usr/bin/env python3
"""Rate-cell ladder: positions 1/10/30/100, k repeats per cell, on screened
probes with real headroom. A rate per cell instead of a single noisy point.
Position 300 is deliberately excluded -- too expensive to use as a repeated
cell, and the floor-effect finding already means depth alone wasn't the
blocker on the previous pass.

Sessions are independent of each other (only turns *within* one session are
sequential), so they run concurrently here, bounded by a semaphore -- a
functional necessity at this call volume, not a harness redesign.
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/claude-workspace/.env")
sys.path.insert(0, str(Path(__file__).parent))

from filler import generate_filler_items
from session import run_session

RESULTS_DIR = Path(__file__).parent.parent / "data" / "ladder"
ITEM_BANK_001 = Path(__file__).parent.parent.parent / "001-collusion-separation" / "data" / "item_bank.json"

PROBE_IDS = ["clear_01", "clear_04", "clear_06", "clear_09", "clear_11"]


def load_probes() -> list[dict]:
    items = {i["id"]: i for i in json.load(open(ITEM_BANK_001))["items"]}
    return [items[pid] for pid in PROBE_IDS]


async def run_cell(sem, filler_pool, juror_name, probe, position, temperature, rep_idx):
    async with sem:
        # Offset the filler slice per repeat so repeats don't share identical
        # docket content, while staying within the shared pool.
        offset = (rep_idx * 37) % max(1, len(filler_pool) - position + 1)
        docket = filler_pool[offset:offset + position - 1]
        session = await run_session(juror_name, docket, probe, position, temperature=temperature)
        return session


async def run_all(positions, probes, jurors, k, temperature, max_concurrency):
    max_filler_needed = max(positions) - 1
    filler_pool = generate_filler_items(max_filler_needed + k * 50, seed=11)  # generous, offsets need headroom
    sem = asyncio.Semaphore(max_concurrency)

    tasks = []
    meta = []
    for probe in probes:
        for position in positions:
            for juror_name in jurors:
                for rep in range(k):
                    tasks.append(run_cell(sem, filler_pool, juror_name, probe, position, temperature, rep))
                    meta.append((probe["id"], position, juror_name, rep))

    print(f"Launching {len(tasks)} sessions, max {max_concurrency} concurrent...", flush=True)
    sessions = await asyncio.gather(*tasks)

    results = []
    for (probe_id, position, juror_name, rep), session in zip(meta, sessions):
        t = session.probe_turn
        results.append({
            "probe_id": probe_id, "position": position, "juror": juror_name, "rep": rep,
            "correct": (t.chosen_answer == next(p for p in probes if p["id"] == probe_id)["ground_truth"]) if t and not t.error else None,
            "confidence": t.confidence if t and not t.error else None,
            "reason_len": len(t.reason.split()) if t and not t.error else None,
            "latency_ms": t.latency_ms if t and not t.error else None,
            "prompt_tokens": session.total_prompt_tokens,
            "completion_tokens": session.total_completion_tokens,
            "error": t.error if t else "no turns",
        })
        status = "OK " if results[-1]["error"] is None else "ERR"
        print(f"[{status}] {probe_id} pos={position:3d} {juror_name:8s} rep={rep} "
              f"correct={results[-1]['correct']} conf={results[-1]['confidence']}")

    return results


def summarize(results: list[dict]):
    from collections import defaultdict
    cells = defaultdict(list)
    for r in results:
        cells[(r["probe_id"], r["position"], r["juror"])].append(r)

    print("\n" + "=" * 90)
    print(f"{'probe':>10s} {'pos':>5s} {'juror':>8s} {'acc':>6s} {'mean_conf':>10s} {'mean_reason_w':>14s} {'mean_lat_ms':>12s}")
    print("=" * 90)
    for (probe_id, pos, juror), rs in sorted(cells.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        valid = [r for r in rs if r["error"] is None]
        if not valid:
            print(f"{probe_id:>10s} {pos:>5d} {juror:>8s}   ALL ERRORS")
            continue
        acc = sum(1 for r in valid if r["correct"]) / len(valid)
        mean_conf = sum(r["confidence"] for r in valid) / len(valid)
        mean_rw = sum(r["reason_len"] for r in valid) / len(valid)
        mean_lat = sum(r["latency_ms"] for r in valid) / len(valid)
        print(f"{probe_id:>10s} {pos:>5d} {juror:>8s} {acc:>6.2f} {mean_conf:>10.2f} {mean_rw:>14.1f} {mean_lat:>12.0f}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run rate-cell dose-finding ladder")
    parser.add_argument("--positions", type=int, nargs="+", default=[1, 10, 30, 100])
    parser.add_argument("--jurors", nargs="+", default=["claude", "gemini"])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-concurrency", type=int, default=15)
    args = parser.parse_args()

    probes = load_probes()
    results = asyncio.run(run_all(args.positions, probes, args.jurors, args.k, args.temperature, args.max_concurrency))
    summarize(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"rate_cells_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w") as f:
        json.dump({"metadata": vars(args), "results": results}, f, indent=2)
    print(f"\nSaved: {out_file}")


if __name__ == "__main__":
    main()
