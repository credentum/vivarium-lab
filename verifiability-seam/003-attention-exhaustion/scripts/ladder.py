#!/usr/bin/env python3
"""Dose-finding ladder: locate where docket position starts degrading a juror's
own output, before committing to a main-run docket depth.

Geometric spacing, not linear -- the order of magnitude is unknown. Run the
cheap rungs first; only escalate to deeper (quadratically costlier) rungs if
no degradation has appeared yet. If Gate B fails at every rung tried, that is
the second inversion (charter: "tired is the common case") and gets reported
as a real finding, not a broken setup.
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
from session import run_session, SessionResult

RESULTS_DIR = Path(__file__).parent.parent / "data" / "ladder"

# ambig_06 (Turkey / UN geoscheme) was the one item in 001's hand-authored
# bank that empirically showed real Control-condition disagreement
# (agreement=0.60) -- a proven-contested probe, reused here rather than
# waiting on Gate A (which comes after this ladder in the sequencing).
CONTESTED_PROBE = {
    "id": "probe_ambig_06", "bucket": "contested",
    "prompt": "Under the United Nations geoscheme, which continent is Turkey classified as being in?",
    "choices": {"a": "Neither", "b": "Asia", "c": "Europe", "d": "Both equally"},
    "ground_truth": "b",
}


async def run_ladder(juror_names: list[str], positions: list[int], probe: dict = CONTESTED_PROBE):
    max_filler_needed = max(positions) - 1
    filler_pool = generate_filler_items(max_filler_needed, seed=7)

    results: list[SessionResult] = []
    for position in positions:
        for juror_name in juror_names:
            print(f"[position={position:4d}] {juror_name}: running {position} turns...", flush=True)
            session = await run_session(juror_name, filler_pool, probe, position)
            results.append(session)
            probe_turn = session.probe_turn
            if probe_turn and probe_turn.error is None:
                correct = "correct" if probe_turn.chosen_answer == probe["ground_truth"] else "WRONG"
                print(f"  -> answer={probe_turn.chosen_answer} ({correct}) conf={probe_turn.confidence:.2f} "
                      f"reason_len={len(probe_turn.reason.split())}w latency={probe_turn.latency_ms}ms "
                      f"cum_prompt_tok={session.total_prompt_tokens} cum_completion_tok={session.total_completion_tokens}")
            else:
                print(f"  -> ERROR: {probe_turn.error if probe_turn else 'no turns recorded'}")

    return results


def summarize(results: list[SessionResult]) -> None:
    print("\n" + "=" * 78)
    print(f"{'position':>8s} {'juror':>10s} {'correct':>8s} {'conf':>6s} {'reason_w':>9s} "
          f"{'latency':>8s} {'prompt_tok':>11s} {'compl_tok':>10s}")
    print("=" * 78)
    for s in results:
        t = s.probe_turn
        if t is None or t.error:
            print(f"{s.probe_position:>8d} {s.juror_name:>10s} {'ERROR':>8s}")
            continue
        correct = "yes" if t.chosen_answer == s.probe_item_id and False else None  # placeholder, unused
        print(f"{s.probe_position:>8d} {s.juror_name:>10s} {str(t.chosen_answer):>8s} "
              f"{t.confidence:>6.2f} {len(t.reason.split()):>9d} {t.latency_ms:>7d}ms "
              f"{s.total_prompt_tokens:>11d} {s.total_completion_tokens:>10d}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run the dose-finding ladder")
    parser.add_argument("--positions", type=int, nargs="+", default=[1, 10, 30],
                         help="docket positions to test (default: 1 10 30, cheap rungs first)")
    parser.add_argument("--jurors", nargs="+", default=["claude", "gemini"],
                         help="juror names from lib/juror.py's JUROR_MODELS (default: 2 cheap/diverse)")
    args = parser.parse_args()

    results = asyncio.run(run_ladder(args.jurors, args.positions))
    summarize(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"ladder_{timestamp}.json"
    with open(out_file, "w") as f:
        json.dump({
            "metadata": {"positions": args.positions, "jurors": args.jurors, "timestamp": datetime.now().isoformat()},
            "sessions": [s.model_dump() for s in results],
        }, f, indent=2)
    print(f"\nSaved: {out_file}")


if __name__ == "__main__":
    main()
