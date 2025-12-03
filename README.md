# Movable Feast v2.7

**How 4 Frontier LLMs Handle Movable Holiday Dates**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Vivarium Lab Case Series | December 2025*

---

## TL;DR

We asked four frontier LLMs to identify holidays from calendar dates. All models performed well on fixed holidays (Christmas, Independence Day). Performance dropped sharply for movable holidays (Easter, Chinese New Year, Eid al-Fitr).

```
Model               Overall    Fixed     Movable
─────────────────────────────────────────────────
Grok-4.1-Fast       82.9%      100.0%    60.0%
Llama-4-Maverick    67.1%      97.5%     26.7%
Gemini-3-Pro        52.9%      80.0%     16.7%
GPT-5.1             40.0%      67.5%     3.3%
```

The gap between fixed and movable performance: **40-64 percentage points**.

---

## Key Finding

Fixed holidays are memorized. Movable holidays require calculation. Current frontier models struggle with the calculation.

| Holiday Type | Example | How Date Works | Model Performance |
|--------------|---------|----------------|-------------------|
| **Fixed** | Christmas | Always Dec 25 | 67-100% |
| **Movable** | Easter | Lunar calculation | 3-60% |

---

## Results

### Overall Accuracy

| Model | Accuracy | 95% CI |
|-------|----------|--------|
| Grok-4.1-Fast | **82.9%** (58/70) | [72.4%, 89.9%] |
| Llama-4-Maverick | 67.1% (47/70) | [55.5%, 77.0%] |
| Gemini-3-Pro | 52.9% (37/70) | [41.3%, 64.1%] |
| GPT-5.1 | 40.0% (28/70) | [29.3%, 51.7%] |

*Wilson score intervals at 95% confidence.*

### Error Types

| Type | Description | Example |
|------|-------------|---------|
| **Empty** | No response | "" |
| **Wrong Holiday** | Different holiday | "Good Friday" for Easter Sunday |
| **Cultural Mismatch** | Wrong tradition | "Spring Festival" for Easter |
| **Temporal Error** | Wrong year's date | 2024 Easter date for 2025 query |
| **Other Observance** | Related but wrong | "Holy Saturday" for Easter Sunday |

### Easter: The Hardest Test

All models achieved **0% accuracy** on movable Easter dates across 10 years tested.

Easter requires the Computus algorithm (first Sunday after the Paschal full moon). No model could reliably compute this.

---

## Methodology

### Task

```
What holiday falls on {date}? Answer with just the holiday name.
```

No examples. No chain-of-thought. One query per date.

### Holidays Tested

**Fixed (40 queries per model)**:
- New Year's Day (January 1)
- Labor Day (May 1)
- Independence Day (July 4)
- Christmas (December 25)

**Movable (30 queries per model)**:
- Chinese New Year (10 years)
- Eid al-Fitr (10 years)
- Easter Sunday (10 years)

Years: 2020-2029

### Models

| Model | Provider | Access |
|-------|----------|--------|
| Grok-4.1-Fast | xAI | OpenRouter |
| Gemini-3-Pro | Google | OpenRouter |
| GPT-5.1 | OpenAI | OpenRouter |
| Llama-4-Maverick | Meta | OpenRouter |

---

## Repository Structure

```
movable_feast/
├── README.md              # This file
├── docs/
│   └── REPORT_v2.7.md     # Full case series report
├── scripts/
│   └── run_study.py       # Main experiment script
└── results/
    └── study_results.json # Raw results
```

---

## Reproduction

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"
python scripts/run_study.py
```

---

## Limitations

This is a case series, not a controlled experiment:

- Single provider (OpenRouter)
- One prompt format
- Temperature 0.0 only
- Limited date range (2020-2029)
- No investigation of *why* models fail

We describe what we observed. We make no claims about underlying mechanisms.

---

## Implications

### For Engineers

If your application needs holiday recognition from dates:
- Fixed holidays: LLMs work fine
- Movable holidays: Use a calendar API

### For Researchers

The fixed/movable gap suggests:
- Fixed dates may be memorized from training data
- Movable dates may require computation LLMs can't reliably perform
- Training data cutoffs may affect future date performance

These are hypotheses. We didn't test them.

---

## Citation

```bibtex
@misc{movablefeast2025,
  title={Movable Feast v2.7: How Frontier LLMs Handle Movable Holiday Dates},
  author={Vivarium Lab},
  year={2025},
  howpublished={GitHub: \url{https://github.com/credentum/movable_feast}},
  organization={Credentum.ai}
}
```

---

## About

**Vivarium Lab** is Credentum's research arm. We test AI capabilities with simple, honest experiments and report what we find.

- Website: [credentum.ai](https://credentum.ai)
- Follow: [@credentum](https://twitter.com/credentum) | [Bluesky](https://bsky.app/profile/credentum.bsky.social)

*"Truth, remembered. Especially when it wounds."*

---

## License

MIT License. See [LICENSE](LICENSE) for details.
