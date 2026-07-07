# GovSim Experiment — Runnable Artifact & Raw Evidence

This directory is the reproducibility artifact behind the
[Governance as Computation](../README.md) study. It contains the governance
extensions, analysis scripts, tests, and **raw run logs** that produced the
headline result (soft advisory 80% survival vs 0% baseline, p=0.008).

Previously the study README said the codebase was "available upon request." It's here now.

## What's in here

| Path | What it is |
|------|-----------|
| `EXPERIMENT_REPORT.md` | The raw experiment report (as written during the run, incl. its own honest limitations section). |
| `raw_logs/results_exp_condition*.log` | **The primary evidence** — raw run output for conditions 1,2,3,4,5 (Feb 17–18 2026). Condition 6 (raw_math) log lived only in the full run archive (see Provenance). |
| `governance_library/` | The governance extensions injected into GovSim — schema, advisory/deliberation logic, and the Jan-14 deliberation sessions/transcripts that generated the policy. |
| `patch/concurrent_env.py` | The **one modified GovSim file** (`simulation/scenarios/common/environment/concurrent_env.py`) enabling the concurrent-harvest conditions. See `PROVENANCE.md` for the exact diff. |
| `analyze_validation_results.py`, `compare_results.py`, `extract_results.py` | Analysis scripts (Mann-Whitney U, Fisher's exact, effect sizes). |
| `tests/` | Unit + integration (mock) tests for the governance library. |
| `PROVENANCE.md` | Git base commit, remotes, working-tree status, and the tracked diff at backup time. |
| `../configs/exp_condition*.yaml` | The 6 condition configs (already committed at the study root — not duplicated here). |
| `../data/results.json` | Processed results (already committed at the study root). |

## How to reproduce

1. Clone upstream GovSim (the study builds on it):
   `git clone https://github.com/giorgiopiatti/GovSim` — base commit recorded in `PROVENANCE.md`
   (`1d11adf`, "Merge pull request #5 from pedrocurvo/fix/setup").
2. Apply the one code change: replace
   `simulation/scenarios/common/environment/concurrent_env.py` with `patch/concurrent_env.py`
   (or apply the diff in `PROVENANCE.md`).
3. Drop the 6 `../configs/exp_condition*.yaml` into
   `simulation/scenarios/sheep/conf/experiment/` and add `governance_library/` to the repo root.
4. Run each condition (5 seeds) with Claude Haiku 4.5; outputs land as `results_exp_condition*.log`.
5. `python extract_results.py && python compare_results.py` to regenerate the stats.

## Note on completeness

The **full raw simulation output** (`simulation/results/`, ~282 MB of per-run dumps) is **not**
committed here to keep the research repo lean — it's published as a **GitHub Release asset**:

- Release: [`govsim-experiment-archive-v1`](https://github.com/credentum/vivarium-lab/releases/tag/govsim-experiment-archive-v1)
- Asset: `govsim-experiment.tgz` (~108 MB), with `govsim-experiment.tgz.sha256` for integrity.

The `raw_logs/` here are the condition-level logs, which are the evidence the report and stats are
derived from. To restore the full per-run archive for re-analysis, download the release asset,
verify the sha256, and `tar -xzf govsim-experiment.tgz`.
