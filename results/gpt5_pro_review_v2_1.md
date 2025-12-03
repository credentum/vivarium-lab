# GPT-5-Pro Ruthless Review of v2.1 Plan

**Model**: gpt-5-pro-2025-10-06
**Response Time**: 377.3s
**Usage**: ResponseUsage(input_tokens=2295, input_tokens_details=InputTokensDetails(cached_tokens=0), output_tokens=9695, output_tokens_details=OutputTokensDetails(reasoning_tokens=5824), total_tokens=11990)

---

Ruthless audit of Movable Feast v2.1

Executive verdict
- Not yet rigorous enough for peer-review. The plan makes strong strides (pre-registration, mixed-effects modeling, provider ablation, negative controls, stress-year selection), but it has core statistical, definitional, and feasibility gaps that will invalidate key claims unless fixed.
- Critical blockers: no power analysis, inconsistent sample-size math, ambiguous ground truth (time zones and calendar variants), poorly formed nulls (H2/H5), under-specified H1 clustering test, missing item-level random effects, no plan for nondeterminism, and unclear scoring for multilingual outputs.
- Addressable with a focused pruning of conditions, a real power plan, explicit ground-truth conventions, corrected hypotheses and tests, and hardened execution controls.

1) Experimental design rigor: what’s solid vs missing
Strengths
- Multi-language and multi-calendar coverage, with stress-year inclusion (Chinese 2033–2034, Orthodox divergence, Umm al-Qura deviations).
- Good control design: negative controls, format perturbations, counterfactual shifts, resolver-correct vs resolver-wrong.
- Mixed-effects logistic regression planned; BH for multiple comparisons; pre-registration and code/data release.

Missing or weak
- Power analysis: absent. No justification of N at the cell level or family-wise error control across hypotheses.
- Sample-size inconsistency: claimed ~50 test cases per holiday per language contradicts the final total of “700–900 test queries per model.” The math is off by an order of magnitude (see Section 4).
- Ground truth is underspecified where it matters:
  - Time zone and jurisdiction conventions for lunisolar holidays (PRC vs Taiwan vs Hong Kong for CNY; Korea’s calendar for Seollal; Vietnam for Tết).
  - Islamic Eid: Umm al-Qura vs observed sighting vs arithmetic tabular. These differ by up to ±1–2 days; this will dominate “errors” if not locked down and stated in the prompt.
  - East Asian lunisolar computation edge cases (2033–2034) are contested; you must lock an authoritative convention and verify libraries against trusted tables.
- Hypotheses not all testable as stated; nulls mis-specified (H2, H5); H1 clustering undefined (no distance metric, cluster method, or significance test).
- Independence and hierarchical structure not addressed: multiple prompts on the same (holiday, year, language) item require item-level random effects; year alone is not enough.
- No defined handling of model nondeterminism (temperature, top_p, retries), model updates, or provider prompt mutation.
- Scoring and compliance: “strict JSON” is not enough; you need defined remediation for malformed JSON and multilingual date normalization rules.

2) Methodological weaknesses
Sampling and power
- Underpowered cells. With 50 items per holiday per language (and likely 100 if negatives are included equally), you cannot detect realistic effects once stratified by prompt condition, language, model, year-stratum, and holiday. After BH correction, power craters.
- No pre-specified minimal effects of interest (MEIs). H4 cites a 20% threshold without justification; for many claims (e.g., “maintain performance across years”), you need equivalence or non-inferiority bounds and power to support them.
- No plan for stratified or blocked sampling to ensure equal representation across “hard-year” edge cases within strata.

Confounds and alternative explanations
- Calendar convention confounds will swamp error analysis:
  - Chinese/Vietnamese/Korean lunisolar: different jurisdictions yield different official holidays for the same astronomical events; library choices may not match “real-world” observances the models were trained on.
  - Islamic Eid: if you grade against Umm al-Qura but the model outputs observed-sighting dates (or vice versa), you’ll misattribute definitional disagreements as reasoning failures.
  - Orthodox vs Western Easter: explicitly name the method in the prompt to avoid “label mismatch.”
- Time zone confounds: lunisolar calculations depend on time zone; libraries may use UTC or embedded offsets. You must pick a canonical zone per holiday and state it in prompts and gold labels.
- Prompt leakage across conditions: the same item across prompt conditions creates within-item correlation and shared variance. Without item-level random effects or blocked analysis, standard errors will be wrong.
- Provider ablation confound: aggregators may inject system prompts or alter decoding defaults. Without raw request/response capture and parameter parity checks, provider differences are uninterpretable.
- Language confounds: “deterministic phrasing” across languages is not the same as native equivalence. Poorly idiomatic prompts will depress scores in ways unrelated to temporal reasoning.

Controls and ablations gaps
- Year-shift tests are incomplete:
  - Metonic ±19 years is not appropriate for Easter (Gregorians do not repeat on 19 years; 532-year cycle for Julian; no short exact cycle for Gregorian).
  - Islamic calendar has ≈33-year solar drift; use ±33 shifts for Hijri-based tests.
- H1 clustering has no ablation to show stability: no bootstrap cluster robustness, no PERMANOVA, no silhouette/gap statistic plan.
- No “synonym/alias” control: models may treat “Lunar New Year”, “Chinese New Year”, “Spring Festival” differently; alias handling must be defined and tested.
- No systematic “ambiguity band” scoring for sighted calendars (e.g., accept ±1 day for observed Eid if the prompt does not fix the convention). Alternatively, eliminate ambiguity by baking the convention into the prompt and gold.

3) Hypotheses: testability and nulls
H1 — Behavioral stratification
- Vague. “Models cluster into distinct behavioral groups” is not a hypothesis without a defined representation (feature vector), distance metric, clustering algorithm, and a statistical test for non-random structure.
- The stated null (“no significant differences across models…”) is not the null for clustering. That’s a performance-difference null, not a structure null.
- Fix: Define a per-model feature vector (e.g., accuracy by holiday × language × prompt × year-stratum; or confusion-matrix embeddings; or principal components of error patterns). Pre-register:
  - Distance metric (e.g., cosine, JS divergence),
  - Clustering method (e.g., agglomerative with Ward),
  - Cluster stability via bootstrap Jaccard,
  - Significance via permutation tests on within/between distances (PERMANOVA),
  - Pre-specify k or an objective (gap statistic).

H2 — Temporal generalization
- Backwards null. You wrote H2₀: “Accuracy varies significantly across year strata.” Standard H0 should be “no difference,” but your claim is about maintained performance. If you want to claim maintenance, you need equivalence or non-inferiority.
- Fix: Use TOST for equivalence with pre-registered bounds (e.g., ±5 percentage points). Provide power for TOST. Alternatively, non-inferiority vs most recent stratum.

H3 — Holiday-type difficulty
- Testable, but you must control for convention ambiguity and task format. If fixed-date tasks are trivial yes/no and movable tasks require calendar resolution, you’re conflating task complexity with “holiday-type difficulty.”
- Fix: Match task format across types (classification under identical prompt scaffolds), and ensure the prompt doesn’t leak mapping hints differentially.

H4 — Prompt-condition sensitivity
- Threshold of 20% is arbitrary and very large. If the minimal effect of interest is 20%, most realistic differences will be null. If you mean “meaningful impact,” justify with a power and use either superiority tests or equivalence bounds depending on directionality.
- You also need to predefine primary contrasts (e.g., CoT-full vs minimal; resolver-correct vs minimal) and treat the family of contrasts with proper multiplicity control.

H5 — Synthetic-rule generalization
- Null is backwards again. If your claim is “models cannot generalize,” H0 should be “no difference” and you aim to reject it in favor of worse synthetic performance; or you run a non-inferiority test in the opposite direction.
- “Comparable” is undefined. Pre-register equivalence bounds and a generalization protocol (train few-shot on synthetic rule A; test on systematically held-out compositions that require rule application, not memorization).
- Ensure the synthetic rules are provably novel and compositional (e.g., pseudo-months, artificial leap rules, renamed tokens) with leakage checks.

4) Statistical validity and power
- Cell counts are not viable as written.
  - By your own numbers: 50 test cases per holiday per language. With 5 holidays × 4 languages = 20 cells → 1000 items per prompt condition.
  - With negatives equal to positives, that’s 2000 per prompt condition.
  - With “7 prompt conditions,” that’s ~14,000 items per model. Your document claims “700–900 per model,” which is inconsistent by 10–20×. Fix the arithmetic and the plan.
- Power example (two-proportion test, alpha 0.05, power 0.8):
  - To detect a 10-point absolute accuracy difference (e.g., 0.70 vs 0.80) with p*(1-p) ≈ 0.21 requires ≈330 items per group (~660 total).
  - With 50 per group you’re badly underpowered for anything less than ~20-point effects. After BH correction across many contrasts, you’ll be functionally blind.
- For equivalence (TOST) with ±5 points, you’ll need on the order of 1–2k items per group depending on baseline accuracy. That implies you must either:
  - Prune hypotheses and conditions dramatically, or
  - Aggregate across strata, or
  - Accept much larger equivalence bounds (and justify them), or
  - Increase N substantially (and budget accordingly).
- Mixed-effects models: include item-level random intercepts (holiday-year-language item) and likely random slopes for prompt condition by model. Without item effects, you will inflate Type I error because multiple prompts share the same item difficulty.
- Overdispersion: consider beta-binomial or cluster-robust SEs if binomial variance is violated.
- Define multiplicity families per hypothesis and pre-register the correction method per family. Don’t BH across the entire analysis indiscriminately.

5) Reproducibility and pre-registration gaps
- Pre-registration must include:
  - Exact hypotheses and nulls (including equivalence/non-inferiority bounds).
  - Sampling plan with explicit Ns per cell and handling of negatives.
  - Model decoding parameters (temperature, top_p, seed), retry policy for invalid JSON, and refusal handling.
  - Cluster analysis details for H1.
  - Primary endpoints and primary contrasts.
  - Exclusion criteria and failure handling (timeouts, provider errors).
- Freeze prompts and gold labels prior to evaluation. Lock calendar conventions and time zones in the prompt text itself to avoid “reasonable alternative” answers.
- Verify gold labels against at least two independent sources for each calendar:
  - CNY/Tết/Seollal: official government calendars and astronomical tables; note any jurisdiction divergences.
  - Islamic: official Umm al-Qura tables for the chosen years if that’s your convention; otherwise specify “observational sighting” and grade with ±1-day acceptance or eliminate the category.
  - Easter: verified tables for Western and Orthodox.
- Release raw prompts and raw outputs with hashes and provider headers. Aggregator calls must include the exact raw payload to detect prompt mutation.

6) Practical execution and feasibility
- Call volume/cost: Once you fix the arithmetic, this is large. At 14,000 calls per model × ~10 models × 2 providers = ~280,000 calls. Add replicates for nondeterminism or retries and you exceed 300k. You need a budget, rate-limit plan, and a stable window to avoid model version drift.
- Model drift: Some providers roll silent updates. You must pin exact model versions (where possible) and run all models within a short window. If versions cannot be fixed (e.g., “preview” models), either exclude them from primary analysis or rerun when stabilized.
- JSON compliance: Expect 5–15% noncompliance for some models under multilingual prompts. Define one retry, then score as noncompliant failure. Pre-register this.
- Provider ablation: Aggregators may inject unknown system prompts. You must capture raw wire requests and responses, and preflight “echo” calls to confirm no hidden system messages.

7) Specific, actionable recommendations
Fix the ground truth and prompts
- Specify the calendar convention, time zone, and jurisdiction in each prompt and in the gold labels. Example: “Use the PRC civil calendar (Beijing time, UTC+8) for Chinese New Year.” “Use Saudi Umm al-Qura civil calendar for Eid.” “Use the Gregorian computus for Western Easter and Julian computus for Orthodox.”
- Where a holiday is jurisdiction-specific (Tết vs CNY vs Seollal), lock the jurisdiction in the prompt language and scoring.
- For inherently sighted calendars (Islamic), either:
  - Restrict to a single civil convention (Umm al-Qura) and bake that into the prompt, or
  - Accept ±1 day and pre-register that tolerance. Don’t mix conventions.

Repair hypotheses and tests
- H1: Define the representation, distance, clustering algorithm, and statistical validation. Pre-register silhouette/gap, bootstrap stability, and PERMANOVA.
- H2: Convert to equivalence/non-inferiority with pre-registered bounds. Power it or narrow the scope.
- H3: Match task structure across fixed and movable sets; avoid confounding by different prompt scaffolds.
- H4: Justify MEI; predefine primary contrasts. Consider smaller MEIs (e.g., 5–10 points) and adjust N or limit families.
- H5: Flip the null to standard form. Use synthetic rules with held-out compositions and adversarial renaming. Pre-register equivalence bounds if claiming “comparable,” or superiority if claiming “cannot generalize.”

Do a real power plan
- Decide what effects matter (e.g., 5–10 points). Compute required N per group after multiplicity correction. If infeasible, prune:
  - Reduce holidays to 3 core types for v2.1 (e.g., Western Easter, CNY, Eid).
  - Reduce languages to 2 for v2.1 (e.g., zh, en), add others in v2.2.
  - Reduce prompt conditions to 4 core (minimal, CoT-minimal, CoT-full, resolver-correct). Move resolver-wrong, partial-resolver, and synthetic to v2.2 or a separate study.
- Alternatively, aggregate across languages within a holiday type for primary tests, with language as a random effect, then do language-specific analyses as exploratory.

Strengthen models and runs
- Fix decoding: temperature=0, top_p=1 where possible; if a provider disallows true determinism, run k=3 replicates per item and use majority vote; record variance as “stability.”
- Include an item-level random intercept in GLMM, and a random slope for prompt condition by model if estimates are stable.
- Add a classical baseline: an explicit calendar program that implements the gold rules and a “memorization baseline” (e.g., nearest-neighbor over year/date patterns from a held-out year set). This bounds performance and distinguishes calendar-rule competence from pattern matching.

Harden ablations and controls
- Year shift:
  - East Asian lunisolar: test ±19 as a stress (not invariance) and document non-cycle years.
  - Islamic: add ±33-year shifts.
  - Easter: add ±532-year synthetic test for Julian; for Gregorian, use random far-shift as a pure counterfactual control (no cycle assumption).
- Add alias/synonym tests and ensure the primary scoring uses canonical names in the prompt to avoid semantic confounds.
- Add a “format ambiguity” control with locale-specific numeric formats (e.g., 03/04 vs 04/03), and pre-register how you handle ambiguity (explicitly disallow ambiguous formats in prompts is better).

Define compliance and refusal handling
- JSON schema: one retry upon invalid JSON; if still invalid, mark as noncompliant error. Pre-register the exact rule.
- Refusal: detect via a reserved field (e.g., “refusal”: true) and also regex fallback; pre-register patterns.
- Provider logs: store request/response bodies, headers, model IDs, timestamps.

8) Feasibility and execution risks
- Cost/time: with corrected Ns, you are in the 200k–300k+ call range for a full run. Compute a budget per model and schedule runs within a stable version window. If not feasible, prune to a powered core study.
- Library correctness: cross-validate libraries against authoritative tables for all chosen years. For Chinese 2033–2034, document and justify the convention or exclude ambiguous cases from primary analysis.
- Model churn: exclude “preview” models from primary claims; include them as exploratory.

9) Does v2.1 address the first review?
Caveat: I don’t have your first review text. Based on common v1 critiques, v2.1 does make clear progress:
- Added pre-registration, provider ablation, stress-year tests, mixed-effects modeling, multiplicity correction, and JSON-only outputs.
- Included negative controls, counterfactual year shifts, and resolver ablations.

Remaining unaddressed issues that v2.1 still has:
- No power analysis and inconsistent Ns (critical).
- Ground-truth conventions, time zones, and jurisdiction ambiguities (critical).
- Ill-formed nulls and insufficiently specified H1 clustering (critical).
- No item-level random effects; no nondeterminism policy; no provider prompt mutation control (major).
- Overbroad condition set that will dilute power and blow up cost (major).

Bottom line
- As written, v2.1 will generate attractive plots but cannot support strong claims about temporal generalization or mechanism. Ambiguous ground truth and underpowered contrasts will turn “differences” into artifacts of conventions and noise.
- If you implement the recommendations above—especially fixing the nulls, pruning and powering a core study, locking calendar conventions/time zones in prompts and gold, adding item-level random effects, and documenting provider behavior—you can produce results that withstand serious peer review.