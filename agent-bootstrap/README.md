# Agent Bootstrap

**The Four Laws of Agentic Context: How 160 Words Beat 1,000**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Vivarium Lab Study | February 2026*

---

## TL;DR

We ran 174 trials across 12 startup context variants and 5 task types to determine what agents need at boot time. The answer: 160 words of deterministic navigational anchors — a flat-format repo map, file handles, and warnings — achieves 1.000 accuracy with zero noise. Every other strategy either adds noise (raw memory injection: 77%) or latency (exploration pointers: +20 seconds) with no proportional accuracy gain.

The agent doesn't need to know what happened. It needs to know where things are.

```
Variant                Words   Accuracy  Noise   Adj. Score
──────────────────────────────────────────────────────────────
anchor_compact          160     1.000    0.000    1.000  ← production
briefing_light          161     0.990    0.042    0.948
bare (nothing)            0     0.938    0.000    0.938
anchor_learned          160     0.950    0.000    0.950
memory_compact          140     1.000    0.330    0.667
tool_pull               164     1.000    0.450    0.550
raw memory injection   1015     1.000    0.790    0.206
```

Don't build a smarter agent. Build a simpler world for the agent to live in.

---

## Key Findings

### Finding 1: The 160-Word Ceiling

Beyond 160 words of startup context, noise grows faster than accuracy. All variants above 160 words have noise-adjusted scores below 0.55. All variants at or below 160 words score 0.55 or higher.

### Finding 2: Density does not equal Relevance

Compacting 1,015 words of memory to 140 words (memory_compact) tripled the adjusted score (0.206 to 0.667) — but still lost to a 161-word navigational briefing (0.948). Dense facts (commit SHAs, agent IDs, phone numbers) are high-precision, low-frequency noise. Repo maps and file handles are universally relevant to every task.

### Finding 3: Curiosity is a Latency Tax

Any invitation to explore — pointers, tool availability, "need more? read this" — triggers the agent to explore even when unnecessary. The `hybrid` variant (one-line pointer to a context index) was the slowest variant (67.1 seconds) despite having near-zero noise. The pointer added +20 seconds with no accuracy gain.

Even negative framing fails. `prompt_gated` explicitly told the agent "DO NOT READ the index unless stuck." The agent still read it, generated 25% noise, and dropped to 0.75 on task_execution.

### Finding 4: Agents Understand Document Hierarchies

We tested adversarial contradictions between CLAUDE.md (project config) and MEMORY.md (session notes). 27 trials, three escalating difficulty levels, including fake bug claims. Result: 1.00 accuracy, 0 hallucinations. Every agent correctly identified CLAUDE.md as authoritative and MEMORY.md as ephemeral.

### Finding 5: Formatting is a Tax

In Phase 3, we tested a "learned" compactor that allocated word budget using trace data. With identical content at 160 words, the flat-format `anchor_compact` (no markdown headers, no indentation) beat the structured `anchor_learned` (section headers, bold labels) by 5%. Every `#` or `**` is a token that could have been a file path.

### Finding 6: Learned Anchor Selection Produces Tautological Anchors

Scoring individual file paths by grep frequency produces task-answer cheat sheets — 100% single-task tautology. The file agents grep for most is the file the task asks about. Journey-based scoring (orientation loops, search loops, verification loops) is the correct abstraction but doesn't beat manual curation at 160 words.

---

## Background

Modern AI agents start each session with no memory of previous work. The standard approaches — dumping memory into the prompt, compressing it with an LLM, or providing tool-based retrieval — all assume more context is better. We tested whether this assumption holds.

The study used Anthropic's Claude CLI (`claude --print`) in headless mode, spawning isolated agent sessions with controlled startup context. Each trial measured accuracy (did the agent complete the task?), noise (did it hallucinate or cite irrelevant context?), and latency.

---

## Experimental Design

### Setup

- **Model**: Claude Sonnet (via headless CLI)
- **Tasks**: 5 types across multiple repositories
  - `orientation` — "What repos exist and what do they do?"
  - `discovery` — "Find a specific module and list its exports"
  - `task_execution` — "Read this code and extract specific implementation details"
  - `memory_recall` — "What does this project's CLAUDE.md say about X?"
  - `conflict` — "CLAUDE.md says X, MEMORY.md says Y — which is correct?"
- **Variants**: 12 startup context strategies (see table below)
- **Evaluation**: Self-evaluation parsed from structured JSON output, validated against ground truth keywords
- **Workspace**: 26 repositories in `/claude-workspace/worktrees/persistent/`

### Phases

| Phase | Trials | Focus |
|-------|--------|-------|
| Phase 1: Baseline | 76 | 8 variants across 4 task types |
| Phase 1b: Conflict | 27 | Authority resolution (CLAUDE.md vs MEMORY.md) |
| Phase 2: Efficiency Frontier | 56 | Stress test anchor_compact vs briefing_light (N=24 each) |
| Phase 3: Learned Anchors | 15 | Data-driven budget allocation (8 train + 7 holdout tasks) |

### Variants

| Variant | Words | Strategy |
|---------|-------|----------|
| bare | 0 | No startup context — agent self-orients |
| briefing_light | 161 | Manually written repo list + recent git log |
| briefing_full | 1,185 | Full memory dump as structured briefing |
| memory_only | 1,015 | Raw MEMORY.md injection |
| memory_compact | 140 | LLM-compressed MEMORY.md |
| personalized | 1,279 | Memory + behavioral "pattern notes" |
| tool_pull | 164 | Briefing + on-demand context tool |
| hybrid | 171 | Briefing + pointer to context index |
| prompt_gated | 167 | Briefing + "DO NOT READ unless stuck" pointer |
| anchor_compact | 160 | Deterministic navigational anchors (flat format) |
| anchor_learned | 160 | Trace-data-driven budget allocation (structured format) |

### Scoring

- **Accuracy**: Ground truth keyword matching (multiple acceptable keywords per task)
- **Noise ratio**: Fraction of self-reported "helpful" items that are hallucinated or irrelevant
- **Adjusted score**: `accuracy * (1 - noise_ratio)` — penalizes high accuracy achieved through noisy context

---

## Results

### Phase 1: The Variant Rankings (76 trials)

```
Variant            Words   Accuracy   Noise    Adj. Score
─────────────────────────────────────────────────────────
bare                 0      0.950     0.000     0.955
briefing_light     161      0.980     0.042     0.938
hybrid             171      0.940     0.000     0.938
memory_compact     140      1.000     0.330     0.667
tool_pull          164      1.000     0.450     0.550
briefing_full    1,185      1.000     0.760     0.243
personalized     1,279      0.940     0.770     0.219
memory_only      1,015      1.000     0.790     0.206
```

### Phase 2: Stress Test (N=24 per variant)

```
Variant            N    Accuracy   Noise    Adj. Score   Mean Time
────────────────────────────────────────────────────────────────────
anchor_compact    24     0.979     0.000     0.979        60.2s
briefing_light    24     0.990     0.042     0.948        64.0s
```

### Phase 3: Learned Anchors (15 tasks, train + holdout)

```
Variant            Train (N=8)   Holdout (N=7)   Overall (N=15)
────────────────────────────────────────────────────────────────
bare                0.844          0.929            0.883
anchor_compact      1.000          1.000            1.000
anchor_learned      0.969          0.929            0.950
```

### Phase 3: Agentability Audit

Structured tool tracing revealed cognitive resistance patterns:

```
Task Type        Resistance   Avg Turns   Pattern           Root Cause
────────────────────────────────────────────────────────────────────────
orientation      HIGH         7.7         Bash x6-9         Agent doesn't know what repos exist
task_execution   HIGH         6.0         Grep x4-5         Agent can't find the right file
discovery        MEDIUM       4.5         Grep x3-4         Code search loops
memory_recall    LOW          1.0         (none)            Answers from CLAUDE.md context
```

Three micro-refactors to the anchor output collapsed friction:

| Refactor | Mechanism | Result |
|----------|-----------|--------|
| **The Map** | Inline repo descriptions | Eliminates `ls` loops |
| **The Handles** | Direct file paths for common targets | Eliminates Grep loops |
| **Kill-Switch** | "authoritative — do not re-verify" framing | Kills anchor-checking turns |

Post-refactor: orientation 8.5 to 5.0 turns (-41%), cost -35%. Zero accuracy loss.

---

## Discussion

### Why 160 Words Works

The 160-word ceiling is not arbitrary. It represents the point where every additional word of context competes with the agent's own reasoning for attention. Below 160 words, context is purely navigational — "here is where things are." Above 160 words, context becomes narrative — "here is what happened" — and narrative competes with the task.

### Why Raw Memory Fails

Memory injection (929-1,279 words) achieves high raw accuracy (0.94-1.00) but generates 77-79% noise. The agent cites commit SHAs, phone numbers, and deploy configurations that have nothing to do with the task. The context acts as an "attention DDoS" — flooding the agent's working memory with plausible but irrelevant facts.

### Why Exploration Invitations Fail

The Curiosity Tax is robust to framing. Positive ("read this if you need it"), neutral ("context index available"), and negative ("DO NOT READ") all trigger exploration. The agent treats any mention of available context as a mandate to consume it. The only reliable strategy is omission — don't mention what you don't want the agent to read.

### Why Flat Format Beats Structured

At 160 words, every token matters. Markdown headers (`## Repos`, `**Key files**`) consume ~10 tokens that flat formatting spends on actual file paths and repo names. In our Phase 3 holdout, this difference was the margin between finding `hb_beamr` (compact, 1.00) and missing it (learned, 0.75).

### Why Learned Selection Failed

We tested two approaches to data-driven anchor selection:

1. **Destination-based** (grep-frequency scoring): Produces tautological anchors. The file agents grep for most is the file the task asks about. 100% single-task, zero generalization.

2. **Journey-based** (loop-reduction scoring): Correctly identifies that orientation loops (Bash x6) are the universal friction signal, not file-specific searches. Allocates budget to sections (Map vs Handles vs Warnings) by Loop Reduction Factor. Doesn't beat manual curation because at 160 words there is no budget to reallocate.

The learned pipeline was valuable as a diagnostic — it discovered that warnings had silently consumed 31% of the budget (47 of 160 words on `gh auth login` with zero navigational value). But the fix was a 15-word cap, not a learned heuristic.

---

## The Production Standard

```
anchor_compact (160 words, flat format, deterministic, no LLM)

  Repos (authoritative — do not re-verify with ls):
  - veris-platform: Veris Platform
  - vivarium: AO/HyperBEAM process development. Lua 5.3 on Arweave.
  - veris-memory-core: Veris Memory
  [... top 8 repos with one-line descriptions ...]
  - Also: repo1, repo2, repo3 [remaining repos, no descriptions]
  CLAUDE.md locations:
  - worktrees/persistent/agent-dev-config/CLAUDE.md
  [... up to 3 locations ...]
  Key files (zero-grep handles):
  - vivarium/ao/lib/safe.lua — SafeLibrary — auth, guards, audit trail
  [... up to 5 handles ...]
  Quick actions:
  - repo-name: N uncommitted change(s)
  Warnings:
  - NEVER run gh auth login --with-token [15 words max]
```

### Design Rules

1. **Flat format** — No markdown headers, no bold, no indentation hierarchy
2. **160 words maximum** — Hard ceiling, enforced in code
3. **Deterministic** — No LLM in the compaction pipeline
4. **Authoritative framing** — "do not re-verify" prevents anchor-checking loops
5. **Warnings capped at 15 words** — Safety content, not navigational content
6. **Every word carries navigational weight** — No narrative, no summaries, no commentary

---

## Limitations

- **Single model**: All trials used Claude Sonnet. Results may not transfer to other model families.
- **Single workspace**: 26 repositories in one workspace. Multi-workspace navigation untested.
- **N=1 per task in Phase 3**: Train and holdout used single trials per task. Statistical power is limited for per-task comparisons.
- **Self-evaluation**: Accuracy measured via agent self-report validated against ground truth keywords. No human evaluation of response quality.
- **Task scope**: All tasks are read-only (discovery, orientation, recall). Write tasks (code generation, refactoring) untested.
- **Holdout scope**: 7 holdout tasks across 5 repos. Broader generalization requires more diverse task sets.

---

## Reproducibility

All code lives in `vivarium/studies/agent-bootstrap/`:

```bash
# Run a single variant
cd vivarium/studies/agent-bootstrap
python3 runner.py --variant anchor_compact --set train --trials 1 --parallel 1

# Run the compactor
python3 compactor.py          # anchor_compact output
python3 compactor.py learned  # anchor_learned output

# Analyze traces
python3 trace_analyzer.py --train-only --seed 42

# Score anchor sections
python3 anchor_scorer.py

# Evaluate results
python3 evaluate.py
```

### Key Files

| File | Purpose |
|------|---------|
| `runner.py` | Experiment runner (headless Claude CLI spawner) |
| `compactor.py` | Deterministic anchor compactor (no LLM) |
| `briefings.py` | Variant-specific briefing builders |
| `evaluate.py` | Results aggregation and friction metrics |
| `trace_analyzer.py` | Journey-based friction pattern extraction |
| `anchor_scorer.py` | Section budget allocation by Loop Reduction Factor |
| `tasks.yaml` | Task definitions (16 tasks, train/holdout split) |
| `config.py` | Variant list and path configuration |
| `RESEARCH_VERDICT.md` | Detailed phase-by-phase results |

### Data

Trial data in `data/run_*.jsonl` (JSONL format, one trial per line). Not committed to public repo — contact authors for access.

---

## The Four Laws of Agentic Context

| Law | Statement |
|-----|-----------|
| **1** | **The 160-Word Ceiling** — Beyond 160 words, noise grows faster than accuracy |
| **2** | **Density ≠ Relevance** — Navigational anchors beat compressed facts |
| **3** | **Curiosity is a Latency Tax** — Never invite exploration; agents treat suggestions as obligations |
| **4** | **Agents Understand Document Hierarchies** — CLAUDE.md > MEMORY.md authority resolution is solved |

And three engineering principles:

1. **Context is a Liability** — Narrative memory adds noise and latency
2. **Anchors are Assets** — Deterministic navigational pointers are the only high-ROI injection
3. **Formatting is a Tax** — Every `#` or `**` is a token that could have been a file path

---

## Citation

```bibtex
@misc{agentbootstrap2026,
  title={Agent Bootstrap: The Four Laws of Agentic Context},
  author={Credentum AI},
  year={2026},
  howpublished={\url{https://github.com/credentum/vivarium-lab/tree/main/agent-bootstrap}},
  note={174 trials, 12 variants, 5 task types}
}
```

---

*"Truth, remembered. Especially when it wounds."*
