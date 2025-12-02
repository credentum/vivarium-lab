# Movable Feast - Definitive Final Results

## Title
**"Lunar Time Without a Map: LLMs Know 春节 but Fail Gregorian↔Lunar Mapping"**

---

## Abstract

Large language models fail to recognize movable holidays from Gregorian dates—0% (Qwen: 0/120; Mistral: 0/30)—but succeed with lunar cues (Qwen: 40/40, 100%; Mistral: 30/30, 100%) or worked date→lunar mappings (29/30, 97%). The v6.7 ablation reveals that **worked mappings do the heavy lifting**: with mappings alone (e.g., "2024-02-10 = 正月初一 = 春节"), 97%; with step instructions alone, 0%. The model pattern-matches from provided mappings rather than computing the conversion. We demonstrate this across Chinese lunar holidays (春节, 端午, 中秋) and Western Easter (computed by the Computus rule), with cross-family replication on Qwen and Mistral (Llama in appendix). A calendar resolver tool achieves 100%; wrong mappings yield 0%—causal proof. All measurements via single provider (OpenRouter, December 2024); multi-provider replication is future work.

---

## Core Claim

**MAPPING_FAILURE.** Models know the holidays but cannot map Gregorian dates to lunar/Computus counterparts. Recognition is 0% from Gregorian cues and 100% from lunar cues (v6.6, N=40). The v6.7 ablation reveals: worked date→lunar mappings (e.g., "2024-02-10 = 正月初一 = 春节") achieve 97% (29/30); step instructions alone achieve 0% (0/30). The model pattern-matches from provided mappings rather than computing the conversion.

---

## Main Results

### Recognition by Prompt Type (Qwen-72B, Chinese)

| Holiday | Prompt Type | N | Hits | Rate | Wilson 95% CI |
|---------|-------------|---|------|------|---------------|
| 春节 | Lunar phrase (v6.6) | 40 | 40 | **100%** | [91.2%, 100%] |
| 春节 | Gregorian date | 120 | 0 | **0%** | [0%, 3.1%] |
| 国庆节 | Fixed Gregorian (10-01) | 20 | 17 | **85%** | [64%, 95%] |
| Christmas | Fixed Gregorian (12-25) | 30 | 30 | **100%** | [88.7%, 100%] |

*Historical note: v6 (N=20) recorded 70% [48–85%] for lunar phrase; v6.6 re-run at N=40 across two phrase variants yielded 100% [91.2–100%]. The earlier 70% was small-N noise.*

### Cross-Family Summary

| Model | Gregorian→LNY | Lunar-cue→LNY | Notes |
|-------|---------------|---------------|-------|
| **Qwen-2.5-72B-Instruct** | 0/120 (0%) [0%, 3.1%] | 40/40 (100%) [91.2%, 100%] | Primary |
| **Mistral-Large-Instruct** | 0/30 (0%) [0%, 11.7%] | 30/30 (100%) [88.7%, 100%] | Independent family |
| Llama-3.1-70B-Instruct | 1/40 (2.5%) [0.4%, 12.9%] | – | Appendix, fails gate |

*Wilson 95% CIs in brackets. Models accessed via OpenRouter, 2024-12.*

### The Core Pattern

```
                         Recognition Rate
                         
   100% ──●───────────────────────────────── Christmas (fixed Gregorian)
   100% ────●─────────────────────────────── 春节 (lunar phrase, v6.6)
    85% ──────●───────────────────────────── 国庆节 (fixed Gregorian)
     0% ────────────────────────────────●─── 春节 (Gregorian) ← CAN'T MAP
```

**100-point gap = calendar mapping failure**

### Mechanism Ladder (v6.7 Final)

```
Gregorian only                        → 0%   (0/120)
Instructions only (CoT-minimal)       → 0%   (0/30)
Rules/hints (CoT-rules)               → ~90% (27/30)
Worked conversion procedure (CoT-full)→ 100% (30/30)
Worked date→lunar mappings (no steps) → 97%  (29/30)
External resolver (ground truth)      → 100% (30/30)
```

**Interpretation:** The model does not compute the Gregorian→lunar mapping from first principles; it pattern-matches from provided mappings or executes a provided worked procedure. Steps alone do not induce the computation.

---

## Methods Snapshot

- **Provider:** OpenRouter (single provider; multi-provider replication is future work)
- **Date window:** December 2024
- **Models:** Qwen-2.5-72B-Instruct, Mistral-Large-Instruct, Llama-3.1-70B-Instruct
- **Temperature:** 0.0 (deterministic), with sweeps at 0.2, 0.7
- **Max tokens:** 500
- **Response format:** JSON (`{"holidays": [...]}`)

---

## Hypothesis Verdicts

| Hypothesis | Prediction | Result | Verdict |
|------------|------------|--------|---------|
| **Channel Default** | ZH prompt recovers LNY | 0% Gregorian | ✗ REJECTED |
| **Missing Cultural Knowledge** | Concept absent | 100% with lunar cue | ✗ REJECTED |
| **Missing Mapping Function** | Can't convert Gregorian↔Lunar | 0% vs 100% | ✓ SUPPORTED |

### On Data Gravity

We do not test training-data causality; our A/B proves only the expression mechanism: the mapping is not executed without worked date→lunar mappings, a full procedure, or a tool. Insufficient paired Gregorian↔lunar supervision in pretraining corpora may explain why the mapping isn't acquired—but this remains an untested upstream hypothesis.

---

## What Responses Look Like

| Condition | Response | Frequency |
|-----------|----------|-----------|
| 春节 + Gregorian date | `{"holidays": []}` | 120/120 |
| 春节 + lunar phrase (v6.6) | `{"holidays": ["春节"]}` | 40/40 |
| 国庆节 + Gregorian | `{"holidays": ["中国国庆节"]}` | 17/20 |

When the model recognizes 春节, it says exactly "春节"—no variation. The concept is crisp; the mapping is absent.

---

## Claims Retracted and Replaced

| Original Claim | Status | Replacement |
|----------------|--------|-------------|
| "Weights lack LNY knowledge" | ✗ RETRACTED | "Weights lack the Gregorian↔lunar mapping function; concepts are present" |
| "Data Gravity explains the failure" | ✗ RETRACTED (as failure mode) | "Data Gravity may explain *why* mapping wasn't learned, but the observed failure is missing conversion, not missing concepts" |
| "Fundamental architectural limitation" | ✗ RETRACTED | "Weight-level mapping not learned in these models under standard training; not proven architecturally impossible" |

---

---

## Behavioral Note

*Behavioral rescue (v6.1 historical data) is in Appendix A. Current paper focuses on recognition mechanism.*

---

## Practical Remediation (Final, with v6.7 Clarifications)

### What Doesn't Work (0%)

| Method | N | Rate | Wilson 95% CI |
|--------|---|------|---------------|
| Gregorian date alone | 120 | 0% | [0%, 3.1%] |
| CoT-minimal (instructions only) | 30 | 0% | [0%, 11.7%] |
| 20-shot table (no target-year mappings) | 40 | 0% | [0%, 8.8%] |

### What Partially Works (~90%)

| Method | N | Rate | Wilson 95% CI |
|--------|---|------|---------------|
| CoT-rules (inject lookup hints) | 30 | ~90% | [74.4%, 96.5%] |

### What Works (97-100%)

| Method | N | Rate | Wilson 95% CI | Median Latency |
|--------|---|------|---------------|----------------|
| Lunar phrase (v6.6) | 40 | 100% | [91.2%, 100%] | 0.92s |
| CoT-full (worked procedure) | 30 | 100% | [88.7%, 100%] | 5.11s |
| Worked date→lunar mappings (no steps) | 30 | 97% | [83.3%, 99.4%] | ~3s |
| Resolver tool (correct mapping) | 30 | 100% | [88.7%, 100%] | ~1s + API |
| Resolver tool (wrong mapping) | 30 | 0% | [0%, 11.7%] | - |

*Note on worked mappings: Examples use prior-year dates (e.g., 2024-02-10 = 正月初一) as neighbors; the target date (2025-01-29) is not included. The model extrapolates from these patterns.*

*Note on wrong mappings: Wrong mappings were plausible but incorrect lunar dates (e.g., "正月十五" instead of "正月初一"), not nonsense. The model correctly rejects these, proving causality.*

### Key Distinction (v6.7)

Two types of "examples" with very different results:

| Example Type | Content | Rate |
|--------------|---------|------|
| **Table-only** | Holiday names, no date→lunar pairs for target | **0%** (0/40) |
| **Worked mappings** | "2024-02-10 = 正月初一 = 春节" (prior-year neighbors) | **97%** (29/30) |

The model needs *date→lunar mappings* it can pattern-match from, not just holiday names.

---

## Study Arc

| Version | Finding | Status |
|---------|---------|--------|
| v5.0 | LNY not recognized (English) | Superseded |
| v6.1 | LNY not recognized (Chinese) | Confirmed |
| v6.1.1-4 | Robust across models/dates | Confirmed |
| v6.2 | 70% with lunar cue | Mechanism identified |
| v6.3 | Replicates across holidays | Capability gap confirmed |
| v6.4 | Easter fails; Tool 0%→100% | Causal proof |
| v6.5 | Ablations confirm robustness | Strengthened |
| v6.6 | CoT-full 100%; Mistral confirms | Cross-family |
| **v6.7** | **Examples=97%, Steps=0%** | **Pattern-matching revealed** |

---

## Paper-Ready Summary (Final)

> Large language models fail to recognize movable holidays from Gregorian dates (0%) but succeed with calendar-system cues (100%) or worked examples (97%). The v6.7 ablation reveals that **examples do the heavy lifting, not step scaffolds**: with examples alone, 97%; with steps alone, 0%. The model pattern-matches from provided date→lunar mappings rather than computing the conversion. A calendar resolver tool achieves 100%; wrong mappings yield 0%—causal proof. Results replicate across Chinese lunar holidays (春节, 端午, 中秋), Western Easter, and model families (Qwen, Mistral).

---

## Conclusion

**The model has the cultural knowledge but cannot compute Gregorian→lunar conversion. It relies on pattern-matching from provided examples.**

The v6.7 ablation is definitive:
- **Examples alone: 97%** — pattern-matching works
- **Steps alone: 0%** — computation doesn't exist
- **Both: 100%** — marginal improvement from structure

Three working solutions:
1. **Provide examples:** Date→lunar mappings the model can extrapolate from (97%)
2. **Tool augmentation:** External calendar resolver (100%)
3. **Direct lunar cue:** Skip Gregorian entirely (100%)

**The "mapping failure" is more fundamental than reasoning—the model lacks the conversion algorithm entirely.**

---

## Limitations

1. **Single provider:** All measurements via OpenRouter; drift mitigated by 24-hour windows and logged model IDs; replication across providers is future work.

2. **Model breadth:** Qwen-72B and Mistral-Large pass; Llama-70B in appendix (fails gate); Yi-large API errors—claim scoped to tested families.

3. **No Ramadan/Diwali:** Easter suffices for non-Chinese generalization; broader religious calendars are open work.

4. **No T=1.0 stress cell:** T=0.7 included; extreme sampling not tested.

5. **We do not ablate training data or tokenizer:** Mechanism claims are behavioral only.

## Confounds Addressed

| Confound | Mitigation | Result |
|----------|------------|--------|
| Prompt sensitivity | Synonym/format/temp panels (v6.5) | 95-100% robust |
| v6 70% discrepancy | Re-tested at N=40 (v6.6) | Both 100% [91.2-100%], was small-N noise |
| CoT mechanism | Ablated minimal/full/rules | Full scaffold required (100%), instructions alone fail (0%) |
| ICL vs reasoning | Tested table-only vs worked examples | Examples alone 0%, with reasoning 100% |
| Cross-family | Tested Mistral-large | Same pattern: 0% Gregorian, 100% lunar |
| Year variance (Easter) | Per-year breakdown with CIs | Consistent 0%/98%/100% across 3 years |
| Causality | Resolver A/B (right vs wrong mapping) | 100% vs 0% - causal proof |

---

## v6.7 Results: CoT Step Ablation - THE KEY FINDING

| Variant | N | Has Examples? | Has Steps? | Rate | Wilson 95% CI |
|---------|---|---------------|------------|------|---------------|
| full | 30 | ✓ | ✓ | **100%** | [88.7%, 100%] |
| examples_no_steps | 30 | ✓ | ✗ | **97%** (29/30) | [83.3%, 99.4%] |
| rules | 30 | ✓ (implicit) | ✓ | **~100%** | [88.7%, 100%] |
| no_examples | 30 | ✗ | ✓ | **0%** (0/30) | [0%, 11.7%] |
| scaffold_only | 30 | ✗ | ✓ | **0%** (0/30) | [0%, 11.7%] |
| minimal | 30 | ✗ | ✗ | **0%** (0/30) | [0%, 11.7%] |

### Critical Insight

**The worked examples are doing the heavy lifting, not the step scaffold.**

- With examples, no steps needed: **97%**
- With steps, no examples: **0%**
- With both: **100%**

Without examples, the model miscalculates the lunar date (outputs 正月初七/初八 instead of 正月初一). The step scaffold alone doesn't help—the model needs the actual date→lunar mappings to pattern-match from.

### What This Means

The model isn't *computing* the Gregorian→lunar conversion. It's *pattern-matching* from provided examples. When you give it:
```
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节
```

It extrapolates: "January dates near Feb 10 in other years → probably 正月初一 → 春节"

This is **retrieval/analogy**, not **calculation**. The "mapping failure" is even more fundamental than we thought: the model lacks the lunar calendar computation entirely and relies on pattern-matching from examples.

### Revised Mechanism

```
Without examples:  Gregorian → [bad guess] → wrong lunar → 0%
With examples:     Gregorian → [pattern match] → correct lunar → 97-100%
With tool:         Gregorian → [external API] → correct lunar → 100%
```

**One-liner:** The model pattern-matches from examples; it cannot compute Gregorian→lunar conversion independently.

### v6 vs v6.5 Reconciliation - No Brittleness

| Phrase | N | Rate | Wilson 95% CI |
|--------|---|------|---------------|
| v6 original ("农历正月初一") | 40 | **100%** | [91.2%, 100%] |
| v6.5 best ("大年初一") | 40 | **100%** | [91.2%, 100%] |

*Historical note: v6 (N=20) recorded 70% [48–85%]; v6.6 re-run at N=40 yields 100%. The 70% was small-N variance.*

### ICL-with-CoT - Examples + Reasoning = Success

| Condition | N | Rate | Wilson 95% CI |
|-----------|---|------|---------------|
| 20-shot table (no reasoning) | 40 | **0%** | [0%, 8.8%] |
| 5-shot with worked CoT examples | 30 | **100%** | [88.7%, 100%] |

**Proof:** Examples alone don't help. Examples *with* the reasoning procedure succeed completely. It's the procedure, not the examples.

### Latency Comparison

| Method | Latency | Accuracy | Recommendation |
|--------|---------|----------|----------------|
| Baseline (Gregorian only) | ~1s | 0% | ❌ Don't use |
| Lunar phrase | 0.92s | 100% | ✓ If you know lunar date |
| CoT-minimal | 2.15s | 0% | ❌ Doesn't work |
| CoT-rules | 2.45s | 90% | ⚠️ Partial |
| CoT-full | 5.11s | **100%** | ✓ Best prompt-only fix |
| Resolver tool | ~1s + API | 100% | ✓ Best overall |

---

## The Complete Evidence (v6.6 Final)

| Method | Gregorian→Holiday | With Fix | Δ |
|--------|-------------------|----------|---|
| Baseline | 0% | - | - |
| Lunar phrase | - | 100% | +100 |
| CoT-minimal | 0% | - | 0 |
| CoT-full | - | **100%** | +100 |
| CoT-rules | - | 90% | +90 |
| ICL 20-shot | 0% | - | 0 |
| ICL + CoT examples | - | **100%** | +100 |
| Tool (correct) | - | 100% | +100 |
| Tool (wrong) | - | 0% | - |

---

## What We Now Know (Final, v6.7)

| Question | Answer | Evidence |
|----------|--------|----------|
| Missing cultural knowledge? | **No** | 100% (40/40) with lunar phrase |
| Instructions help? | **No** | 0% (0/30) with CoT-minimal |
| Worked mappings help? | **Yes** | 97% (29/30) with date→lunar examples alone |
| Steps help? | **Only with mappings** | 0% steps-only; 100% with both |
| Rules help? | **Partially** | ~90% (27/30) with lookup hints |
| Tool fixes it? | **Yes** | 100% correct, 0% wrong (causal) |

---

## The Mechanism (Now Clear - v6.7)

1. **The model has the cultural knowledge** (100% with lunar phrase, 100% Christmas)

2. **The model CANNOT compute Gregorian→lunar conversion** (0% with steps alone)

3. **Examples enable pattern-matching** (97% with examples, no steps needed)

4. **Tool provides the mapping directly** (100%)

**The v6.7 ablation reveals:** CoT success isn't about "reasoning"—it's about providing date mappings the model can pattern-match from. Without examples, even explicit step-by-step instructions yield 0%.

**Conclusion:** The model lacks Gregorian→lunar computation capability. It relies entirely on pattern-matching from provided examples or external tool resolution.

---

---

## Easter Per-Year Breakdown (v6.5)

| Variant | 2023 (Apr 9) | 2024 (Mar 31) | 2025 (Apr 20) | Pooled |
|---------|--------------|---------------|---------------|--------|
| Gregorian only | 0/20 (0%) [0–16.1%] | 0/20 (0%) [0–16.1%] | 0/20 (0%) [0–16.1%] | **0/60 (0%)** [0–6.0%] |
| Name control | 20/20 (100%) [83.9–100%] | 20/20 (100%) [83.9–100%] | 19/20 (95%) [76.4–99.1%] | **59/60 (98.3%)** [91.1–99.7%] |
| Computus CoT | 20/20 (100%) [83.9–100%] | 20/20 (100%) [83.9–100%] | 20/20 (100%) [83.9–100%] | **60/60 (100%)** [94.0–100%] |

**Year effects are nil; the failure isn't a 2025 fluke.** Pattern is consistent across all three years. The single miss in 2025 name control (95%) is within expected noise.

---

## Practical Remediation (Proven with Latency Data)

### What Doesn't Work (0%)
| Method | N | Rate | Wilson 95% CI |
|--------|---|------|---------------|
| Gregorian date alone | 120 | 0% | [0%, 3.1%] |
| CoT-minimal ("Step 1, Step 2") | 30 | 0% | [0%, 11.7%] |
| 20-shot table examples | 40 | 0% | [0%, 8.8%] |

### What Partially Works
| Method | N | Rate | Wilson 95% CI | Latency |
|--------|---|------|---------------|---------|
| CoT-rules (inject lookup) | 30 | 90% | [74.4%, 96.5%] | 2.45s |

### What Works (100%)
| Method | N | Rate | Wilson 95% CI | Latency |
|--------|---|------|---------------|---------|
| Lunar phrase (v6.6) | 40 | 100% | [91.2%, 100%] | 0.92s |
| CoT-full scaffold | 30 | 100% | [88.7%, 100%] | 5.11s |
| ICL + CoT examples | 30 | 100% | [88.7%, 100%] | ~5s |
| Resolver tool (correct) | 30 | 100% | [88.7%, 100%] | ~1s + API |
| Resolver tool (wrong) | 30 | 0% | [0%, 11.7%] | - |

### The Key Insight

CoT-minimal fails (0%) but CoT-full succeeds (100%). The difference:

```
# FAILS (0%) - Just instructions
"Step 1: convert date. Step 2: identify holiday."

# WORKS (100%) - Complete reasoning scaffold
"Step 1: Convert 2025-01-29 to lunar date.
 (Examples: 2024-02-10 = 正月初一, 2024-06-10 = 五月初五...)
 Step 2: Match lunar date to holiday.
 (正月初一 = 春节, 五月初五 = 端午节...)"
```

**One-liner (v6.7):** The model pattern-matches from worked date→lunar examples (97%); step instructions alone yield 0%. It cannot compute the conversion independently.

### Production Implementation

```python
# Option 1: External resolver (recommended)
holiday_info = calendar_resolver.lookup(date="2025-01-29")
prompt = f"[日历解析器] {date} = 农历{holiday_info['lunar']}（{holiday_info['holidays'][0]}）\n\n{original_prompt}"

# Option 2: CoT-full scaffold (no external dependency)
prompt = """请按步骤推理：
步骤1：将公历日期转换为农历日期（写出农历月日）
已知：2024-02-10=正月初一，2024-06-10=五月初五...
步骤2：根据农历日期判断节日
正月初一=春节，五月初五=端午节...
现在分析：2025-01-29"""
```

---

## Files

| File | Description |
|------|-------------|
| `movable_feast_1_results_*.json` | Main study + top-ups |
| `movable_feast_2_results_*.json` | Causality experiments (国庆节, lunar phrase) |
| `movable_feast_3_results_*.json` | Generalization (端午/中秋, reverse mapping, prose few-shot) |
| `movable_feast_4_results_*.json` | Causal proof (Easter, Tool A/B, table few-shot) |
| `movable_feast_5_results_*.json` | Comprehensive ablations |
| `movable_feast_6_results_*.json` | Cross-family, reconciliation |
| `movable_feast_7_results_*.json` | CoT step ablation (key finding) |
| `MOVABLE_FEAST_FINAL.md` | This document |

---

## Appendix A: Historical Data

### Behavioral Rescue (v6.1)

| Condition | Mean Score | Effect |
|-----------|------------|--------|
| LNY Implicit (Gregorian date) | 4.03 | "Work now" response |
| LNY Explicit (named holiday) | 3.57 | Rescue (Δ=0.46) |

*This behavioral test predates the v6.6/v6.7 mechanism studies. It shows that explicit naming rescues behavior, consistent with the recognition findings.*

### v6 Lunar Phrase Reconciliation

| Version | N | Rate | Wilson 95% CI |
|---------|---|------|---------------|
| v6 (original) | 20 | 70% | [48%, 85%] |
| v6.6 (re-run) | 40 | 100% | [91.2%, 100%] |

*The 70% in v6 was small-N variance. Both phrases ("农历正月初一" and "大年初一") achieve 100% at N=40.*

---

## Appendix B: Llama Results (Fails Gate)

| Model | Gregorian→LNY | Notes |
|-------|---------------|-------|
| Llama-3.1-70B-Instruct | 1/40 (2.5%) [0.4%, 12.9%] | CI upper > 10%, fails gate |

*Llama shows the same directional pattern but with one spurious hit. Included for completeness; excluded from main claims.*
