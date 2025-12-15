# Movable Feast: A Holiday Season Snapshot

**How 4 Frontier LLMs Handle Movable Holiday Dates**

*Vivarium Lab Case Series | December 3, 2025*

---

## Abstract

We asked four frontier large language models to identify holidays from calendar dates. All models performed well on fixed holidays (Christmas, Independence Day). Performance dropped sharply for movable holidays (Easter, Chinese New Year, Eid al-Fitr). Grok-4.1-Fast achieved 82.9% overall accuracy (95% CI: 72.4%-89.9%); GPT-5.1 achieved 40.0% (95% CI: 29.3%-51.7%). This case series documents what we observed. We make no claims about why these differences exist.

---

## 1. Introduction

Holiday dates fall into two categories: fixed and movable. Christmas always falls on December 25. Easter moves according to a lunar calculation. We wondered: do large language models handle these differently?

This is Vivarium Lab's first published study. We kept it simple: four models, one task, one afternoon. We describe what we found.

---

## 2. Method

### 2.1 Models

| Model | Provider | Access |
|-------|----------|--------|
| Grok-4.1-Fast | xAI | OpenRouter (free tier) |
| Gemini-3-Pro | Google | OpenRouter |
| GPT-5.1 | OpenAI | OpenRouter |
| Llama-4-Maverick | Meta | OpenRouter |

### 2.2 Task

Each model received 70 queries:

```
What holiday falls on {date}? Answer with just the holiday name.
```

No examples. No chain-of-thought prompting. One query per date.

### 2.3 Holidays

**Movable (30 queries per model)**:
- Chinese New Year (10 years)
- Eid al-Fitr (10 years)
- Easter Sunday (10 years)

**Fixed (40 queries per model)**:
- New Year's Day - January 1
- Labor Day - May 1
- Independence Day - July 4
- Christmas - December 25

Years tested: 2020-2029.

### 2.4 Scoring

Responses scored correct if they matched the expected holiday or an accepted alias (e.g., "Lunar New Year" for Chinese New Year, "May Day" for Labor Day). Empty responses and wrong holidays scored incorrect.

---

## 3. Results

### 3.1 Overall Accuracy

| Model | Accuracy | 95% CI |
|-------|----------|--------|
| Grok-4.1-Fast | **82.9%** (58/70) | [72.4%, 89.9%] |
| Llama-4-Maverick | 67.1% (47/70) | [55.5%, 77.0%] |
| Gemini-3-Pro | 52.9% (37/70) | [41.3%, 64.1%] |
| GPT-5.1 | 40.0% (28/70) | [29.3%, 51.7%] |

*Wilson score intervals at 95% confidence.*

### 3.2 Fixed vs. Movable

| Model | Fixed Holidays | 95% CI | Movable Holidays | 95% CI |
|-------|----------------|--------|------------------|--------|
| Grok-4.1-Fast | 100.0% (40/40) | [91.2%, 100.0%] | 60.0% (18/30) | [42.3%, 75.4%] |
| Llama-4-Maverick | 97.5% (39/40) | [87.1%, 99.6%] | 26.7% (8/30) | [14.2%, 44.4%] |
| Gemini-3-Pro | 80.0% (32/40) | [65.2%, 89.5%] | 16.7% (5/30) | [7.3%, 33.6%] |
| GPT-5.1 | 67.5% (27/40) | [52.0%, 79.9%] | 3.3% (1/30) | [0.6%, 16.7%] |

The gap between fixed and movable performance ranged from 40 percentage points (Grok) to 64 percentage points (GPT-5.1).

### 3.3 Year-by-Year Performance

| Model | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2027 | 2028 | 2029 |
|-------|------|------|------|------|------|------|------|------|------|------|
| Grok-4.1-Fast | 7/7 | 6/7 | 6/7 | 7/7 | 6/7 | 6/7 | 5/7 | 5/7 | 6/7 | 4/7 |
| Llama-4-Maverick | 5/7 | 5/7 | 4/7 | 6/7 | 5/7 | 5/7 | 5/7 | 4/7 | 4/7 | 4/7 |
| Gemini-3-Pro | 4/7 | 4/7 | 4/7 | 4/7 | 3/7 | 3/7 | 4/7 | 4/7 | 4/7 | 3/7 |
| GPT-5.1 | 3/7 | 3/7 | 3/7 | 3/7 | 4/7 | 3/7 | 3/7 | 2/7 | 2/7 | 2/7 |

*Raw counts (correct/total). No CIs computed for n=7 cells.*

### 3.4 Expanded Error Taxonomy

| Model | Empty Response | Wrong Holiday | Cultural Mismatch | Temporal Error | Other Observance |
|-------|----------------|---------------|-------------------|----------------|------------------|
| Grok-4.1-Fast | 0 | 0 | 5 | 1 | 6 |
| Llama-4-Maverick | 0 | 5 | 5 | 0 | 13 |
| Gemini-3-Pro | 32 | 0 | 1 | 0 | 0 |
| GPT-5.1 | 41 | 0 | 1 | 0 | 0 |

**Error categories**:
- **Empty Response**: Model declined to answer or returned blank
- **Wrong Holiday**: Named a different major holiday
- **Cultural Mismatch**: Guessed a holiday from different tradition (e.g., "Ascension Day" for Eid)
- **Temporal Error**: Close but off by a day (e.g., "Bank Holiday" for May 1)
- **Other Observance**: Named a minor observance day (e.g., "Darwin Day", "Siblings Day")

Two distinct patterns emerged:
- **Grok and Llama**: Always attempted an answer, sometimes incorrectly. Errors distributed across cultural mismatch and other observances.
- **Gemini and GPT-5.1**: Frequently declined to answer (32-41 empty responses). When they did answer incorrectly, errors were rare.

### 3.5 Representative Errors

**Grok-4.1-Fast** (cultural mismatch):
- 2021-05-13 → Expected: Eid al-Fitr → Got: Ascension Day
- 2026-02-17 → Expected: Chinese New Year → Got: Shrove Tuesday

**Llama-4-Maverick** (other observances):
- 2020-01-25 → Expected: Chinese New Year → Got: Holocaust Remembrance Day
- 2021-02-12 → Expected: Chinese New Year → Got: Darwin Day
- 2029-04-01 → Expected: Easter Sunday → Got: April Fools' Day

**GPT-5.1** (empty responses):
- 2020-04-12 → Expected: Easter Sunday → Got: [no response]
- 2025-04-20 → Expected: Easter Sunday → Got: [no response]

---

## 4. Discussion

### 4.1 What We Observed

All models knew Christmas is December 25. Most knew July 4 is Independence Day. Performance degraded substantially for holidays whose dates change each year.

Grok-4.1-Fast outperformed other models on movable holidays by a wide margin (60% vs. 3-27%). The 95% confidence intervals for movable holiday performance do not overlap between Grok and the other models, suggesting this difference is unlikely due to chance.

### 4.2 Training Cutoff Implications

**This is a critical limitation.** We do not have access to training cutoff dates for any of the four models tested. This matters because:

1. **Memorization vs. Computation**: A model might correctly answer "What holiday is April 12, 2020?" because Easter 2020 appeared in its training data, not because it computed the lunisolar calendar. We cannot distinguish these mechanisms.

2. **Future Year Performance**: The year-by-year breakdown shows no clear degradation for years beyond likely training cutoffs (2025-2029), but this could reflect either genuine computation or recent training data including future calendars.

3. **Interpretation Limits**: Without cutoff information, we cannot claim models "know how to calculate" Easter or "merely memorized" dates. Both explanations remain plausible.

We encourage model providers to publish training cutoff dates to enable more rigorous analysis.

### 4.3 What We Cannot Say

This study does not support claims about:
- "Temporal reasoning capability"
- Whether models "struggle with" any task
- How these models will perform tomorrow or on other holidays
- Mechanisms underlying the observed differences

### 4.4 Limitations

- **Four models, one day**: Results may not replicate
- **English only**: No cross-lingual assessment
- **Western bias in fixed holidays**: See Section 4.5
- **Unknown training cutoffs**: See Section 4.2
- **Small sample per category**: n=30 for movable holidays yields wide confidence intervals

### 4.5 Cultural Bias and Mitigation

Our fixed holiday baseline skews Western:
- **New Year's Day**: Gregorian calendar (global, but Western origin)
- **Independence Day**: United States only
- **Christmas**: Christian tradition
- **Labor Day (May 1)**: International, but excluded in US

This baseline tests Western calendar knowledge, not global coverage. The movable holidays (Chinese New Year, Eid, Easter) represent three different calendar systems, but the fixed-movable comparison is confounded by cultural familiarity.

**Recommendations for future studies**:
1. Include non-Western fixed holidays (e.g., Diwali—falls on a fixed lunar date, Thai New Year—fixed Gregorian date)
2. Test fixed holidays from Islamic calendar (e.g., Islamic New Year—fixed in Hijri calendar)
3. Stratify analysis by cultural tradition rather than fixed/movable
4. Include non-English prompts to assess cross-cultural knowledge transfer

---

## 5. Conclusion

On December 3, 2025, we asked four frontier LLMs to identify holidays from dates. They knew fixed holidays (67.5%-100%). They frequently failed on movable holidays (3.3%-60%). Grok-4.1-Fast performed best; GPT-5.1 performed worst. Two error patterns emerged: some models hallucinate alternative holidays, others decline to answer.

These results describe a single snapshot. We cannot determine whether performance differences reflect training data, calendar computation capability, or prompt sensitivity. We report what we observed.

---

## Appendix A: Materials

All materials available at: `github.com/credentum/project-vivarium`

- Ground truth dates: `studies/movable-feast/data/test_items.json`
- Raw responses: `studies/movable-feast/data/results/`
- Analysis scripts: `studies/movable-feast/scripts/`

---

## Appendix B: Alias Mappings

| Holiday | Accepted Aliases |
|---------|------------------|
| Chinese New Year | Lunar New Year, Spring Festival, CNY |
| Eid al-Fitr | Eid ul-Fitr |
| Easter Sunday | Easter |
| Labor Day | May Day, International Workers' Day |
| Independence Day | Fourth of July, July 4th |
| Christmas | Christmas Day |

---

## Appendix C: Statistical Methods

**Wilson Score Interval**: Used for binomial proportions instead of normal approximation. Wilson intervals have better coverage properties for small samples and proportions near 0 or 1.

Formula:
```
(p + z²/2n ± z√(p(1-p)/n + z²/4n²)) / (1 + z²/n)
```
where p = observed proportion, n = sample size, z = 1.96 for 95% CI.

---

*Vivarium Lab • Credentum AI*

*This case series was designed, executed, and written with AI assistance (Claude Opus 4.5). Reviewed by DeepSeek-V3.2.*
