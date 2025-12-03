# GPT-5-Pro Ruthless Review of v2.2 Core Study

**Model**: gpt-5-pro-2025-10-06
**Response Time**: 444.5s
**Usage**: ResponseUsage(input_tokens=2428, input_tokens_details=InputTokensDetails(cached_tokens=0), output_tokens=10827, output_tokens_details=OutputTokensDetails(reasoning_tokens=7488), total_tokens=13255)

---

Blunt verdict up front: v2.2 is a real improvement in scope control, ground-truth conventions, and model specification. But the stats and N planning are still not defensible. The sample-size arithmetic is inconsistent with the described dataset; the power analysis is wrong; H4 is under-specified; H2’s design is confounded (single fixed-date control); and key analysis choices (TOST margins vs actual power, unit of analysis, multiplicity) remain underspecified. This will not survive peer review as written.

1) Did v2.2 address the v2.1 critiques?

1. No power analysis — critical blocker
- Partially addressed, but still wrong.
- You claim: “detect 10-point differences (80% vs 90%)” with N=90 per group. That is not correct. Standard two-proportion power (α=0.05, two-sided, 80% power) for 0.80 vs 0.90 yields ≈199 per group; one-sided ≈156 per group. Your N=90 underpowers by ~1.7–2.2×.
- Worse: your main claims include ±5% equivalence margins (H1, H4). For TOST with δ=5% around ~85% accuracy, you need roughly ≈630 per group to have 80% power. Your design is nowhere near this.

2. Sample size math inconsistent (700–900 claimed vs ~14k calculated)
- Still broken.
- You say: “100 items × 4 prompts × 4 holidays × 2 languages = 3,200 queries” (positives), then +3,200 negatives = 6,400.
- But your dataset defines only 25 years per holiday. There is exactly one positive per holiday-year. With 25 years, you have 25 positives per holiday, not 100. With 4 holidays × 25 years × 2 languages × 4 prompts = 800 positives total, not 3,200. Doubling for negatives → ≈1,600, not 6,400.
- Also, your year ranges sum to 28 years (1995–2005 = 11, 2015–2025 = 11, 2030–2035 = 6), yet you say “Total years per holiday: 25.” Inconsistent. You need a frozen, enumerated year list; the math must match that list.

3. Ground truth underspecified (time zones, calendar conventions)
- Mostly fixed. You now pin down calendar conventions and time zones, and specify libraries. Good.
- Still needed:
  - Freeze library versions and the exact official tables used for verification (source URLs, SHA256 hash of the CSV/Parquet).
  - Define accepted holiday label strings per language (synonym mapping) to avoid false negatives from lexical variants.

4. Hypotheses H2/H5 have backwards nulls — need equivalence tests
- Partially fixed.
- H1 now uses TOST equivalence with ±5%. Good direction, but underpowered given actual N.
- H3 is incoherent: you state a margin (“no prompt effect larger than ±10%”) but propose standard pairwise contrasts (superiority). That’s not an equivalence test. Choose one: either (a) state superiority hypotheses and test with GLMM contrasts, or (b) state equivalence/non-inferiority with TOST and power it.
- H4 equivalence is specified but the synthetic calendar construction is missing (see below). As written, H4 cannot be run.

5. H1 clustering undefined (no metric, algorithm, significance test)
- Removed from core claims. Fixed.

6. Missing item-level random effects in GLMM
- Fixed at a basic level: you include (1 | item) and (1 | model).
- But “item” is undefined. If item includes the prompt text, that will absorb prompt effects. If not, you need cross-classified random effects: one for the event-year-language (“content”) and one for the prompt template. See “GLMM specification” below.

7. Need to prune conditions and do real power plan
- Conditions pruned. Good.
- Real power plan: not yet. Your N plan doesn’t match the dataset you actually defined, and it ignores mixed-effects variance components and multiplicity. You need simulation-based power for the GLMM and for TOST under the actual design.

8. Call volume infeasible
- Fixed. Even after correcting your arithmetic, the run is feasible (likely <20k–50k calls depending on final N). But see the corrected N calculations below.

2) New methodological weaknesses introduced by v2.2

- Equivalence margin/power mismatch: You use ±5% equivalence in H1/H4 but only plan N to detect 10% differences. That cannot support equivalence claims.
- H2 is confounded: Only one fixed-date holiday (Christmas). Any “movable vs fixed” effect is indistinguishable from “Christmas idiosyncrasy.” You need multiple fixed-date controls to claim a class-level difference.
- H3 is contaminated by a trivial condition: resolver-correct hands the answer to the model. Including this in “prompt-condition sensitivity” makes the contrast meaningless for “reasoning” and conflates instruction-following with calendar competence.
- Synthetic calendars (H4) are not specified: No grammar, no rule families, no few-shot sampling protocol, no leak checks, no generalization sets, no ground truth generation. H4 is not executable.
- Item definition is unclear: Without a clear “item” identity, your random-effects structure is at risk of mis-specification and pseudo-replication.
- Negative sampling lacks balance specs: “1–2 random dates,” “±1-day,” “impossible dates” per year is vague. Counts per category must be fixed and balanced across holidays/languages/prompts to avoid base-rate and difficulty confounds.
- JSON retry policy: “Retry once if JSON invalid” introduces post-hoc variability and may systematically benefit some prompts/models. Either treat invalid JSON as incorrect (preferred) or pre-specify identical retry behavior across all conditions and count both attempts for audit.
- Year strata definition inconsistent: The document alternates between 3 and 4 strata (past, recent, future, and “stress” singled out). Define strata explicitly and enumerate the exact years per stratum.
- Language scoring not frozen: You need canonicalized holiday labels per language (e.g., multiple acceptable Chinese strings for Eid, Easter). Otherwise, lexical variance becomes a dominant error source.
- Multiplicity control family undefined: You say “BH correction,” but over which family? All tests across H2/H3 contrasts? Or per-hypothesis families? This matters for FDR control.

3) Statistical validity

Power analysis
- Two-proportion power for 80% vs 90%, α=0.05, two-sided requires ≈199 per group; one-sided ≈156. Your N=90 is incorrect.
- Equivalence with ±5% margin (TOST) at p≈0.85 needs ≈630 per group for 80% power. Your design cannot support H1/H4 equivalence unless you aggregate very large Ns per stratum or increase years.
- You must do simulation-based power for the GLMM with (1|model) and (1|item) (and likely additional random effects; see below). simr (R) or custom Monte Carlo is fine. Input realistic variance components based on pilot runs.

Tests and model specification
- GLMM formula: correct ~ prompt_condition + year_stratum + holiday + language + (1 | model) + (1 | item)
  - Define item as the underlying event-year-language (content), not including the prompt text. Then add a crossed random intercept for prompt_template: (1 | prompt_template). Without this, either (a) item conflates prompts and wipes out fixed prompt effects or (b) different prompts to the same content become dependent with no random structure.
  - Consider random slopes by model for prompt_condition: (1 + prompt_condition | model). Prompt sensitivity varies by model; ignoring this inflates Type I error on prompt contrasts.
- Outcome coding: You list “holiday correct,” “holiday incorrect,” “false positive,” “refusal.” Pre-specify the binary outcome for the GLMM. If refusals exist, count them as incorrect and separately analyze refusal rate with a secondary model.
- H1 TOST: If you insist on equivalence with ±5%, do TOST on model-adjusted marginal means from the GLMM (marginal effects across controlled factors), not naive proportions. Predefine which strata are compared (recent vs past, recent vs future, recent vs stress). Apply multiplicity correction across these TOST pairs.
- H3 testing: Either drop the ±10% language and do standard superiority contrasts across non-trivial prompts (exclude resolver-correct from this family), or perform equivalence with a justified margin and power it.
- H2: As designed, not valid for the claimed construct. With only Christmas as fixed control, any effect is a “Christmas vs everything else” effect. Either:
  - Add ≥3 fixed-date holidays across both languages (e.g., New Year’s Day, Labor Day, National Day), or
  - Reframe H2 as “Christmas vs each movable holiday” with no class-level claim.

4) Feasibility

- Call volume as stated (51k) is based on incorrect N arithmetic. With the dataset you actually described (25 years/holiday):
  - Positives: 4 holidays × 25 years × 2 languages × 4 prompts = 800
  - Negatives at 1:1: +800 → 1,600 per model
  - For 8 models: ~12,800 calls (plus retries). Feasible.
- If you correct power to what is required for ±5% equivalence (H1/H4), you will need far more items per stratum unless you relax the margin or aggregate across more years. That pushes calls up, but still likely manageable (<100k) if you plan it, because generation of ground truth is cheap.

5) Specific, actionable fixes

Sampling and dataset
- Freeze and publish the exact year lists per stratum. Fix the inconsistency (25 vs 28). If you need N, increase the year range deterministically (e.g., 1975–2035) and mark pre-/post-training years for analysis.
- Decide the unit count:
  - Option A (equivalence faithful): Keep ±5% equivalence, then expand years so that per TOST comparison you have ≈630+ items per group (after any exclusions), or aggregate across holidays and prompts to hit that N. Make the math explicit.
  - Option B (feasible now): Relax H1/H4 to ±10% and/or switch to non-inferiority with a single-sided margin you can power with your actual N. State why ±10% is practically meaningful.
- Balance negatives per holiday-year: Fix exact counts per category:
  - For each positive (holiday-year-language), include: 1 random non-holiday date (same month), 1 near-date (±1 day), 1 impossible date. This gives a 1:3 negative:positive ratio unless you downsample. Keep ratios identical across holidays/languages/prompts.
  - Alternatively keep 1:1 overall by sampling exactly one negative type per positive, cycling types evenly.
- Freeze accepted label sets per language for each holiday (“Christmas,” “圣诞节/圣诞节日,” “开斋节/开斋节日,” “复活节,” “春节/农历新年,” etc.), and canonicalize scoring.

Hypotheses and tests
- H1: Specify the exact pairs (recent vs past; recent vs future; recent vs stress if separate). Do TOST on GLMM-adjusted marginal means. Justify the margin. Power it via simulation with the actual random-effects structure.
- H2: Either add ≥3 fixed-date holidays to legitimately test “movable vs fixed,” or reframe to “Christmas vs [Easter/CNY/Eid]” and present it as holiday-specific difficulty, not class-level.
- H3: Remove resolver-correct from the “prompt sensitivity” family or analyze it separately as “oracle compliance.” For prompt effects, compare minimal vs CoT-minimal vs examples-only. Decide: superiority or equivalence. If equivalence, predefine margins and power it. If superiority, drop the ±10% language.
- H4: Either fully specify and implement the synthetic calendar regime (grammar, generation of held-out synthetic rule families, few-shot selection, guarantees of novelty vs pretraining, and ground truth generator) or drop H4 from v2.2. As written, H4 is not executable.

GLMM and analysis details
- Define item as event-year-language (“content_id”). Add crossed random effects:
  - correct ~ prompt + year_stratum + holiday + language
            + (1 | model) + (1 | content_id) + (1 | prompt_template)
  - Strongly consider random slopes for prompt by model: (1 + prompt | model), if data support it. If not, at least report model-by-prompt heterogeneity descriptively and use cluster-robust SEs clustered by model.
- Outcome handling:
  - Pre-specify that invalid JSON and refusals count as incorrect in the primary endpoint. Report refusal and invalid-JSON rates separately.
  - No retries, or count retries as separate logged attempts but score the first output as the endpoint for fairness. If you keep a retry, apply it identically across all conditions and models and report both pass rates.
- Multiplicity:
  - Define the families for BH correction. Example: H3 pairwise prompt contrasts constitute one family per language, or one combined family if you pool languages. TOST pairs for H1 are another family.
- CIs:
  - For GLMM fixed effects, report profile likelihood CIs or bootstrapped CIs. Clopper–Pearson applies to raw proportions, not mixed models. Be consistent.

Prompt design and controls
- Standardize date formatting (ISO 8601) across languages to remove formatting confounds.
- Add a “resolver-wrong” or “shuffled-examples” control back in v2.2 or v3.0 to measure susceptibility to injected mappings. Without it, “examples-only” cannot disentangle generalization from example-following.
- Ensure that “examples-only” uses examples that are non-informative about the target (e.g., distant years or contradictory patterns), or else treat it explicitly as an example-following condition.

Reproducibility
- Publish exact library versions, year CSV with checksums, prompt JSON schemas with checksums, and the roster of models with provider/version pins. Log and publish seeds.

6) Publication readiness verdict

Not ready for peer review. Major blockers:
- Incorrect power analysis and mismatched equivalence margins.
- Inconsistent N arithmetic and unresolved year-list conflicts.
- H2 confounded by having only one fixed-date holiday.
- H3 hypothesis/test mismatch and contamination by a trivial oracle condition.
- H4 under-specified and not executable.
- GLMM random-effects structure and unit-of-analysis not clearly defined.

Path to readiness:
- Fix the N plan with either: (a) expanded years to meet equivalence-power requirements, or (b) relaxed margins/shift to superiority and power that. Use simulation-based power for the GLMM and TOST.
- Add fixed-date controls or reframe H2.
- Cleanly define item identity and crossed random effects.
- Freeze years, labels, and multiplicity families.
- Either implement H4 fully or drop it from v2.2.

Once these are corrected and the numbers line up with the actual dataset, this can be a solid, minimal, publishable core. Right now, the statistical plan and the dataset do not match, and several hypotheses are not testable as specified.