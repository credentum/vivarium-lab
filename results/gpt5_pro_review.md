# GPT-5-Pro Ruthless Review

**Model**: gpt-5-pro-2025-10-06
**Response Time**: 337.1s
**Usage**: ResponseUsage(input_tokens=1929, input_tokens_details=InputTokensDetails(cached_tokens=0), output_tokens=7792, output_tokens_details=OutputTokensDetails(reasoning_tokens=4352), total_tokens=9721)

---

Ruthless assessment of the Movable Feast study

Executive verdict
- As written, the paper overclaims and is underpowered. The “algorithmic behavior” claim for Grok is not justified by the current design and N. The three-class taxonomy is plausible as a behavioral clustering on this dataset, but not yet stable or generalizable.
- The upgrade plan fixes important credibility gaps (N, years, negatives, release), but misses critical controls: provider/tool leakage, caching/version drift, mixed-effects modeling, multiple-comparison control, output parsing reliability, and deliberately hard calendar edge-cases (leap months, 2033 Chinese-calendar anomaly, Western vs Orthodox Easter).
- With the upgrades plus the missing controls below, this is workshop-quality for ACL/EMNLP/NeurIPS Datasets & Benchmarks. Without them, expect “nice blog post” reviews.

1) Remaining methodological weaknesses not addressed by the proposed upgrades

Sampling and power
- N=20 per cell is unusable for stratification. Even N=100/cell (planned) is underpowered to distinguish near-ceiling models. Detecting a 4-point difference (0.99 vs 0.95) at alpha=0.01, power=0.9 requires ~540 samples per group. If you want to claim “indistinguishable from algorithmic conversion,” you need thousands of cases spanning hard years and languages with Clopper–Pearson intervals that rule out meaningful gaps.
- Current averaging masks dependence. You report averages without modeling clustering (by model, language, holiday, year). This inflates effective N and deflates CIs.

Provider/tool confounds
- Single broker, unknown tool policy. OpenRouter may alter system prompts, route models, cache answers, or enable hidden tools. Your “algorithmic” behavior may be a silent tool, KB hook, or cache hit. The upgrade plan does not add a provider/tool ablation.
- No verification of tool usage. You did not log tool availability flags, function-call traces, or provider headers. You cannot rule out tool-injected overrides.

Temporal/version confounds
- No version pinning or hash. “Grok-4.1-Fast” in December 2025 is not a stable artifact. Without model version fingerprints and reruns across dates, you can’t claim reproducibility.
- Caching contamination. If OpenRouter caches per-prompt, later runs could leak earlier answers across conditions.

Task design and negatives
- Positives-only or imbalanced positives. Without a well-specified negative set (non-holiday dates within valid ranges; impossible dates; out-of-range dates for a given holiday), accuracy overstates utility. Precision/recall/F1 are essential, but your planned negatives are underspecified. You need calibrated base rates and hard negatives that are calendar-plausible, not just “fake date strings.”
- Overlap risk between few-shot examples and test years. “Examples-only” risks year overlap or near-neighbor contamination. You need strict non-overlap in year, language, and format between demonstrations and tests.

Calendar complexity not probed
- No “hard-year” stress tests. Chinese lunisolar edge cases (2033/2034 anomaly, intercalary months, years near winter solstice edge), Vietnamese deviations, Korean calendar conventions, and lunar month boundaries are not targeted. For Easter, you must include both Western (Gregorian) and Orthodox (Julian-based) calculations across centuries; for Islamic holidays, Umm al-Qura vs arithmetic tabular variants. None of this is in the current paper; the upgrade plan mentions adding calendars but not hard-year sampling.
- Format robustness. You didn’t test diverse, adversarial, or low-resource date formats: spelled-out numbers, local era names, Arabic numerals with locale separators, code-switched prompts, Romanization variants, diacritic-stripped Vietnamese (Tet/Tết), and ambiguous formats (02/03/2016).

Evaluation and parsing
- Output extraction fragility. You do not report an extraction spec, inter-annotator agreement, or robustness to verbosity. Without a deterministic, pre-registered parser and adjudication protocol, scores are not reproducible.
- No refusal/abstention accounting. Refusals, hedges, and multi-guess answers need explicit scoring rules; otherwise, you’re mixing calibration with accuracy.

Stats and controls
- No mixed-effects modeling. You need a logistic mixed-effects model with random intercepts for model, language, holiday, and year to account for clustering and to test fixed effects (prompt condition, year-era). Without this, “three classes” may be a dataset artifact.
- Multiple comparisons not controlled. You’re doing many cells and pairwise model comparisons without FDR/Bonferroni control.
- No pre-registered analysis plan or held-out split. Absent pre-registration and a frozen test set, the taxonomy can drift with analyst degrees of freedom.

Mechanistic overreach
- Behavior ≠ mechanism. “Indistinguishable from algorithmic conversion” is an overreach without mechanism-level evidence or stress tests that algorithmically isolate conversion versus table lookup versus tool calls. Your own limitations section concedes no interpretability, yet the abstract asserts algorithmic behavior.

2) Challenge to the core claims

1. “LLMs stratify into three capability classes”
- With N=20/cell and one holiday/year, you cannot separate stable behavioral clusters from sampling noise, prompt artifacts, or provider routing. The taxonomy may collapse under:
  - Year shifts to hard cases (e.g., 2033/2034 for Chinese; years with leap months; Orthdox Easter divergences).
  - Format perturbations and multilingual ablations (diacritics; code-switch; ambiguous formats).
  - Provider/model-version changes. 
- Treat this as a provisional behavioral clustering on a narrow slice, not a capability taxonomy.

2. “Class A behavior is indistinguishable from algorithmic conversion”
- Unsupported. Alternative explanations not ruled out:
  - Densely memorized tables for common years/holidays.
  - Hidden tools/KG hooks via provider.
  - Cache hits induced by standardized prompts.
- Necessary falsification you did not run:
  - Counterfactual calendar tasks (synthetic but rule-based remappings unseen in pretraining).
  - Leap-month and 2033/2034 Chinese-calendar edge cases across languages.
  - Contradiction-resistance tests (resolver-wrong with large, structured conflicts; mixed partial hints; adversarial system prompts).
  - Format adversaries and locales not common on the web.
- Absent these, “algorithmic” should be replaced with “near-ceiling performance on this slice.”

3. “CoT prompting cannot recover missing functions”
- You tested a narrow set of CoT prompts. Stronger tests:
  - Induce step-by-step algorithmic scaffolding with pseudo-code, worked partial algorithms, or scratchpad arithmetic constraints.
  - Allow limited external tool use (calendar library) to test whether reasoning scaffolds compensate for internal gaps.
- Current evidence supports “CoT doesn’t help on our setup,” not a general claim.

4. “Cost-performance inversion”
- Price is not a scientific variable; prices change weekly and vary by broker. This belongs in a practitioner note, not a key claim.

5. “Cross-cultural asymmetries in Vietnamese Tết recognition”
- Likely confounded by orthography (diacritics), lexical variants, and dataset formatting. You need:
  - Matched prompts with/without diacritics.
  - Native-speaker-vetted phrasing.
  - Balanced positive/negative sets across orthographic variants.

3) Evaluation of the proposed upgrade plan

Strong additions
- Increasing N and years; adding negatives; releasing code/data; adding F1; comparisons to SPAN/TimeBench; adding more calendars/models.

Critical gaps still missing
- Provider/tool ablations:
  - Run the full suite on at least two independent providers per model (native vendor APIs if possible) with tools disabled and logging of any function-call channels. Capture full request/response metadata and headers. Confirm no tool availability at the API layer.
- Version pinning and drift control:
  - Log model version IDs/hashes and rerun a stability subset on two different dates to estimate temporal variance.
- Mixed-effects modeling and multiple comparisons:
  - Pre-register a hierarchical logistic regression plan and FDR control. Without this, stratification claims are statistically weak.
- Hard-year and edge-case sampling:
  - Explicit stratification for known pathological years and rules (Chinese 2033/2034, intercalary months; Islamic Umm al-Qura vs arithmetic; Western vs Orthodox Easter) and for locale scripts/orthographies.
- Deterministic parsing and adjudication:
  - A strict output schema, deterministic parser, and blinded human adjudication for ambiguous outputs; report inter-annotator agreement.
- Format robustness:
  - Systematic perturbation set: numeric, spelled-out, locale separators, code-switched, diacritic-stripped, ambiguous D/M/Y, mixed scripts.
- Power analysis:
  - Formal sample-size calculations tied to the smallest effect you intend to detect (e.g., 5-point gaps at alpha=0.01 require ~500+ samples per group).
- Pre-registration and frozen test split:
  - Publish a pre-registration and keep a held-out evaluation set untouched until camera-ready.

4) Specific, actionable recommendations

Minimum viability changes for claims about behavior classes
- Sampling and power
  - Per model × holiday × language × condition, target N≥300 if you want to distinguish 10-point differences at alpha=0.01 with >0.9 power; N≥500 if you need to resolve 4–5 point gaps near ceiling.
  - Years: 1990–2050 with stratified sampling to include hard cases (must include 2001, 2012, 2014, 2015, 2017, 2018, 2033–2035 for Chinese/Vietnamese; 2010–2040 for Western/Orthodox Easter; Islamic years covering drift vs Umm al-Qura differences).
- Provider and tool control
  - Run each suite across two providers: broker (OpenRouter) and native APIs (Anthropic, OpenAI, Google, xAI). Disable tools explicitly, verify tool schemas absent, and log headers. Include a documented “no-tools” JSON payload and store raw responses.
  - Add a tool-positive control: same prompts with a simple calendar tool enabled to show upper bound and to test that “algorithmic” behavior exceeds tool-free baselines.
- Adversarial and counterfactual tests
  - Year-shift tests: ±1, ±19 (Metonic), and synthetic “misaligned” mappings to detect table lookup vs rule application.
  - Impossible/invalid and out-of-range negatives: dates outside valid holiday windows that are still plausible (e.g., Feb 25 for CNY), plus syntactic invalids; report precision, recall, FPR.
  - Resolver-wrong gradient: vary magnitude and structure of wrong hints; include internally consistent but globally wrong calendars to test contradiction resistance.
  - Format perturbations: date string variants, localized month names, diacritic removal, mixed-script, and code-switch ablations; report per-perturbation drop.
- Modeling and statistics
  - Use a mixed-effects logistic model: correct ~ condition + language + holiday + year-era + (1|model) + (1|language:holiday) + (1|year), with cluster-robust SEs. Report likelihood-ratio tests for fixed effects.
  - Control FDR across multiple comparisons (Benjamini–Hochberg).
  - Report per-class and macro/micro metrics: accuracy, precision, recall, F1, FPR, refusal rate. Include confusion matrices per language/holiday.
  - Calibration: reliability plots for confidence (if models provide scores) or proxy via logprobs.
- Parsing and adjudication
  - Enforce a JSON output schema; reject non-conforming outputs; count as errors unless a secondary pass is pre-registered.
  - For free-form conditions, pre-register a deterministic regex/normalizer. Run a blinded double-annotation on a 10% sample; report κ.
- Mechanistic humility and probes
  - Replace “algorithmic” with “near-ceiling on tool-free, provider-controlled tests, including edge cases.” Add targeted probes:
    - Synthetic-calendar generalization: define a simple, unseen mapping rule family; provide k-shot examples for k∈{1,3,5}; test generalization to new years. True algorithmic composition should extrapolate; memorization should not.
    - Leap-month localization probes: ask for intermediate computations (lunar month index, leap flag) without giving worked examples. Analyze consistency across steps.
    - Logit-level analysis if available: show that outputs change minimally under paraphrase/format perturbations if behavior is rule-like; large swings imply pattern triggers.
- Contamination checks
  - Compute web frequency of exact test tuples (date ↔ holiday) and exclude high-frequency cases from one split; report performance on low-frequency subsets.
- Reproducibility
  - Release: code, exact prompts, raw responses, evaluation scripts, frozen dataset with license, provider configs, and a Colab. Include model version IDs and run timestamps. Provide a seed and retry policy.

5) Reframing the core claims

- Stratification: “We observe consistent behavioral clusters across models on movable-date holiday recognition under controlled prompts and provider/tool constraints.” Avoid “capability classes” until stability is shown across providers, versions, formats, and hard-year strata.
- Grok “algorithmic”: Replace with “near-ceiling performance that survives adversarial years, formats, and contradiction; indistinguishable from a rule-based converter on our tests.” Do not imply internal implementation.
- CoT limits: “On our tasks, CoT variants did not recover performance for models lacking the underlying mapping; however, we do not claim that CoT cannot scaffold missing functionality in general.”
- Cost-performance: Move to appendix as a practical observation, not a scientific claim.
- Vietnamese asymmetry: Report after controlling for orthography and format; otherwise present as a hypothesis.

6) Positioning relative to existing benchmarks

- SPAN, TimeBench, TRAVELER, TimeQA: Position Movable Feast as a targeted, cross-cultural, calendar-specific benchmark focusing on movable-date holiday mapping and calendar conversion stress tests, with hard-year and intercalation coverage absent in general temporal QA suites. Include direct head-to-head results on overlapping capabilities or a mapping of task differences. If you can show that models scoring high on TimeBench still fail on leap-month years or Orthodox vs Western Easter distinctions, that’s your novelty.

7) Publication viability and venue

- Near-term target: ACL/EMNLP Findings or workshops (e.g., Evaluation and Benchmarks, Temporal Reasoning). For NeurIPS Datasets & Benchmarks, you must deliver:
  - Large-N with power analysis,
  - Multi-provider/tool controls,
  - Hard-year calendar coverage (including 2033/2034 Chinese anomaly and Orthodox Easter),
  - Pre-registration and release,
  - Mixed-effects analysis with multiple-comparison control,
  - Clean ablations (format, negatives, contradiction).
- Without the above, expect rejection on grounds of overclaiming and insufficient controls. With them, this is viable as a strong benchmark paper with a restrained claims section.

Concrete checklist to be peer-review ready
- Power: pre-computed, justifying N per cell for your smallest claimed effect.
- Providers: at least two providers per model; no-tools confirmed; logs published.
- Years: 1990–2050 with hard-year strata; negatives balanced; precision/recall/FPR reported.
- Calendars: at minimum Chinese, Vietnamese, Korean lunisolar; Western and Orthodox Easter; Islamic (Umm al-Qura vs arithmetic). Document rule sources.
- Formats: perturbation battery; per-perturbation metrics.
- Stats: mixed-effects logistic regression; FDR control; CIs; stability across runs/dates.
- Parsing: strict schema; adjudication; κ reported.
- Claims: mechanistic humility; no price-based claims in abstract.
- Repo: code, data, prompts, raw logs, model/version metadata, license, Colab.

Bottom line: Do the provider/tool ablations, hard-year stress tests, and mixed-effects analysis, and tone down mechanism claims. Then you have a defensible, useful benchmark that can survive peer review. Without those, the “algorithmic behavior” claim for Grok will get torn apart.