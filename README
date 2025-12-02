# Movable Feast

**LLMs Know 春节 but Can't Find January 29: Pattern-Matching Beats Computation for Calendar Mapping**

[![arXiv](https://img.shields.io/badge/arXiv-coming%20soon-b31b1b.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## TL;DR

Large language models fail to recognize movable holidays (春节, Easter, etc.) from Gregorian dates—**0% recognition**—but succeed with worked date→lunar mappings (**97%**) or external tools (**100%**). 

The model **pattern-matches** from provided examples; it **cannot compute** Gregorian→lunar conversion.

```
Gregorian only                        → 0%   (0/120)
Instructions only ("Step 1, Step 2")  → 0%   (0/30)
Worked date→lunar mappings            → 97%  (29/30)
External calendar resolver            → 100% (30/30)
```

---

## Key Finding

**Don't write:**
```
Step 1: Convert the Gregorian date to lunar.
Step 2: Identify any holidays on that lunar date.
```
→ **0% success**

**Do write:**
```
Known mappings:
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节

What holiday is 2025-01-29?
```
→ **97% success**

**Or just use a calendar API** → **100% success**

---

## Results Summary

| Method | N | Rate | Wilson 95% CI |
|--------|---|------|---------------|
| Gregorian date alone | 120 | 0% | [0%, 3.1%] |
| CoT-minimal (instructions only) | 30 | 0% | [0%, 11.7%] |
| CoT-rules (lookup hints) | 30 | ~90% | [74.4%, 96.5%] |
| Worked date→lunar mappings | 30 | 97% | [83.3%, 99.4%] |
| CoT-full (worked procedure) | 30 | 100% | [88.7%, 100%] |
| Calendar resolver (correct) | 30 | 100% | [88.7%, 100%] |
| Calendar resolver (wrong) | 30 | 0% | [0%, 11.7%] |

### Cross-Family Replication

| Model | Gregorian→LNY | Lunar-cue→LNY |
|-------|---------------|---------------|
| Qwen-2.5-72B-Instruct | 0/120 (0%) | 40/40 (100%) |
| Mistral-Large-Instruct | 0/30 (0%) | 30/30 (100%) |
| Llama-3.1-70B-Instruct | 1/40 (2.5%) | – |

---

## Repository Structure

```
movable-feast/
├── README.md                          # This file
├── VIVARIUM_DEFINITIVE_FINAL.md       # Full paper/write-up
├── requirements.txt                   # Python dependencies
│
├── scripts/
│   ├── vivarium_v6_1_main.py          # Core recognition study
│   ├── vivarium_v6_2_causality.py     # 国庆节 + lunar phrase tests
│   ├── vivarium_v6_3_generalization.py # 端午/中秋, reverse mapping
│   ├── vivarium_v6_4_causal_proof.py  # Easter, Tool A/B, few-shot
│   ├── vivarium_v6_5_ablations.py     # Synonym/format/temp sweeps
│   ├── vivarium_v6_6_polish.py        # Cross-family, v6 reconciliation
│   └── vivarium_v6_7_cot_ablation.py  # Key finding: examples vs steps
│
└── results/
    ├── vivarium_v6_1_results_*.json
    ├── vivarium_v6_1_1_results_*.json  # Top-ups
    ├── vivarium_v6_1_2_results_*.json
    ├── vivarium_v6_1_3_results_*.json
    ├── vivarium_v6_1_4_results_*.json
    ├── vivarium_v6_2_results_*.json
    ├── vivarium_v6_3_results_*.json
    ├── vivarium_v6_4_results_*.json
    ├── vivarium_v6_5_results_*.json
    ├── vivarium_v6_6_results_*.json
    ├── vivarium_v6_6_part4_results_*.json
    └── vivarium_v6_7_results_*.json
```

---

## Reproduction

### Prerequisites

```bash
pip install openai
export OPENROUTER_API_KEY="your-key-here"
```

### Run Experiments

```bash
# Core finding (v6.7 - most important)
python scripts/vivarium_v6_7_cot_ablation.py

# Full study sequence
python scripts/vivarium_v6_1_main.py
python scripts/vivarium_v6_2_causality.py
python scripts/vivarium_v6_3_generalization.py
python scripts/vivarium_v6_4_causal_proof.py
python scripts/vivarium_v6_5_ablations.py
python scripts/vivarium_v6_6_polish.py
python scripts/vivarium_v6_7_cot_ablation.py
```

### Expected Runtime

| Script | Trials | ~Time |
|--------|--------|-------|
| v6.1 | 160 | 15 min |
| v6.2 | 60 | 5 min |
| v6.3 | 140 | 12 min |
| v6.4 | 200 | 18 min |
| v6.5 | 300 | 25 min |
| v6.6 | 180 | 15 min |
| v6.7 | 180 | 15 min |

---

## Methodology

### Holidays Tested

| Holiday | Calendar System | Date Rule |
|---------|-----------------|-----------|
| 春节 (Chinese New Year) | Chinese lunar | 正月初一 |
| 端午节 (Dragon Boat) | Chinese lunar | 五月初五 |
| 中秋节 (Mid-Autumn) | Chinese lunar | 八月十五 |
| 国庆节 (National Day) | Gregorian (fixed) | October 1 |
| Christmas | Gregorian (fixed) | December 25 |
| Easter | Computus | First Sunday after Paschal full moon |

### Models

- **Primary:** Qwen-2.5-72B-Instruct (via OpenRouter)
- **Cross-family:** Mistral-Large-Instruct, Llama-3.1-70B-Instruct
- **Temperature:** 0.0 (deterministic)
- **Provider:** OpenRouter (single provider; multi-provider replication is future work)

### Statistical Approach

- **Metric:** Recognition rate with Wilson 95% confidence intervals
- **Gate:** ≤10% CI upper bound for "failure" cells; ≥90% CI lower bound for "success" cells
- **Pre-registration:** Gates defined before running experiments

---

## Citation

```bibtex
@misc{movablefeast2024,
  title={Movable Feast: LLMs Know 春节 but Can't Map Gregorian Dates to Lunar Holidays},
  author={[Author]},
  year={2024},
  howpublished={GitHub: \url{https://github.com/[username]/movable-feast}},
  note={Vivarium Lab}
}
```

---

## Key Insight

The v6.7 ablation reveals that **worked examples do the heavy lifting, not step scaffolds**:

| Condition | Has Examples? | Has Steps? | Rate |
|-----------|---------------|------------|------|
| full | ✓ | ✓ | 100% |
| examples_no_steps | ✓ | ✗ | **97%** |
| no_examples | ✗ | ✓ | **0%** |
| minimal | ✗ | ✗ | 0% |

The model **pattern-matches** from provided date→lunar mappings. It **cannot compute** the Gregorian→lunar conversion independently.

---

## Practical Recommendations

### For Engineers

```python
# ❌ This doesn't work (0%)
prompt = """
Step 1: Convert 2025-01-29 to lunar date.
Step 2: Identify any holidays.
"""

# ✅ This works (97%)
prompt = """
Known: 2024-02-10 = 正月初一 = 春节
Known: 2024-09-17 = 八月十五 = 中秋节
What holiday is 2025-01-29?
"""

# ✅ Best: Use a calendar API (100%)
from calendar_resolver import lookup
info = lookup("2025-01-29")  # Returns: {"lunar": "正月初一", "holiday": "春节"}
prompt = f"Today is {info['lunar']} ({info['holiday']}). {original_prompt}"
```

### For Researchers

- **Observed failure:** Gregorian→lunar mapping not executed without worked examples or tool
- **Mechanism:** Pattern-matching, not computation
- **Upstream hypothesis:** Insufficient paired Gregorian↔lunar supervision in pretraining (untested)

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

This research was conducted at Vivarium Lab.

---

*"If you are lucky enough to have lived in Paris as a young man, then wherever you go for the rest of your life, it stays with you, for Paris is a movable feast."* — Ernest Hemingway

*If you are lucky enough to have a calendar API, then wherever your LLM goes for the rest of inference, it can find the holidays.* — This study
