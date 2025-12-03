#!/usr/bin/env python3
"""
GPT-5-Pro Ruthless Review of Movable Feast Study
"""

import os
import time
from dotenv import load_dotenv
import openai

load_dotenv()

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

RUTHLESS_REVIEWER_PERSONA = """You are a ruthless, data-driven AI evaluation and alignment researcher with expertise across:

machine learning theory
statistical methodology
cognitive psychology
temporal reasoning
cross-cultural computational linguistics
LLM interpretability
benchmark design
experimental rigor

You operate with a strict, uncompromising standard:

No hype. No speculation disguised as fact.
Every claim must be grounded in reproducible data, statistical power, or established literature.

Methodological ruthlessness.
You identify weaknesses in sampling, confounds, prompt leakage, insufficient N, statistical misuse, dataset bias, or unverifiable claims immediately.

Zero tolerance for hand-waving.
If something is not mechanistically supported or empirically justified, you call it out.

You distinguish between behavior, inference, and mechanism.

Behavioral evidence ≠ algorithmic capability
Failure modes ≠ global incompetence
Success under examples ≠ latent ability

You assess generalization, not just accuracy.
You systematically challenge claims of "algorithmic behavior" with counterfactuals:

year shifts
adversarial dates
impossible dates
prompt ablations
tool-injected overrides
multilingual perturbations

You do not sugar-coat feedback.
Feedback is blunt, precise, and focused on improving rigor.

You default to falsification.
You look for ways findings:

could be artifacts
could be memorization
could be prompt-induced
could be biased by provider, temperature, instruction tuning

You examine claims for overreach.
Any time the user implies:

"algorithmic generalization"
"mechanistic competence"
"architectural advantage"
You demand evidence or reframe the claim.

You maximize clarity.
You communicate in concise, technical language suitable for:

peer-review
NeurIPS / ACL rebuttals
capability eval standards
alignment risk analysis

You always prefer:

reproducible experiments
transparent data
statistically valid results
clean controls
mechanistic humility
honest limitations

Your purpose is to pressure-test the Movable Feast study, strengthen its methodology, and ensure that any published claim can withstand serious peer-review.

You act without deference or politeness.
You serve the truth, not the ego of the researcher."""

DOCUMENT_1 = r"""
[DOCUMENT 1: MAIN PAPER - LaTeX Source]

\title{Lunar Time Without a Map: Capability Stratification in LLM Gregorian--Lunar Holiday Mapping}

ABSTRACT:
Large language models (LLMs) exhibit sharply divergent abilities in recognizing movable-date holidays (e.g., Lunar New Year, Easter) from Gregorian dates. Earlier evaluations on Qwen-72B and Mistral-Large show 0% accuracy from Gregorian dates alone and 97-100% accuracy when provided worked Gregorian→lunar mappings, demonstrating pattern-matching rather than calendrical computation. Extending the evaluation to frontier models reveals a three-class capability structure:
(A) Algorithmic models (e.g., Grok-4.1-Fast) exhibit behavior indistinguishable from an internal or densely memorized conversion mechanism;
(B) Pattern-triggered models (e.g., Claude-Opus-4.5, Gemini-3-Pro) succeed only when linguistic or structural cues activate latent mappings, with subtypes distinguished by example-triggered vs. instruction-triggered activation;
(C) Pattern-matching models (e.g., GPT-5.1, Qwen-72B) fail without explicit in-context mappings.

KEY RESULTS:
- Grok-4.1-Fast: 99% avg (Class A - Algorithmic)
- Claude-Opus-4.5: 83% avg (Class B1 - Example-triggered)
- Gemini-3-Pro: 63% avg (Class B2 - Instruction-triggered)
- GPT-5.1: 19% avg (Class C - Pattern-matching)
- Qwen-72B: ~25% (Class C)
- Mistral-Large: ~25% (Class C)

METHODOLOGY:
- Languages: zh, vi, ko, en
- N=20 per cell for frontier models
- Temperature = 0.0
- Provider: OpenRouter (December 2025)
- Prompt conditions: Gregorian-only, Minimal, CoT-minimal, Examples-only, CoT-full, Resolver, Resolver-wrong

KEY CLAIMS:
1. LLMs stratify into three capability classes for temporal reasoning
2. Class A behavior is "indistinguishable from algorithmic conversion"
3. CoT prompting cannot recover missing functions
4. Cost-performance inversion (free Grok beats expensive GPT-5.1)
5. Cross-cultural asymmetries in Vietnamese Tết recognition

LIMITATIONS ACKNOWLEDGED:
- Single provider (OpenRouter)
- N=20 per cell (wider CIs)
- No mechanistic interpretability proof for Class A
- Only 2025 Lunar New Year tested
- Only zh/vi/ko/en evaluated
"""

DOCUMENT_2 = """
[DOCUMENT 2: UPGRADE RECOMMENDATIONS]

10 PRIORITIZED IMPROVEMENTS:

CORE FIXES (Credibility):
1. Increase N to 100+ per cell, expand to 10-20 years (2010-2040), stratify by era
2. Run year-randomization tests: past (1995), future (2045), fake/impossible dates
3. Add false-positive analysis: precision/recall/F1, hallucination rates per class
4. Release code + data on GitHub/HF for reproducibility

ENHANCEMENTS (Novelty/Depth):
5. Add SPAN/TimeBench/TRAM positioning and direct comparison
6. Add mechanistic disclaimers + basic probes (adversarial prompts, logit analysis)
7. Expand to 8-10 models, add 2-3 more calendars (Islamic, Hindu)
8. Prototype "Holiday Agent" with tool-augmentation

DISSEMINATION (Impact):
9. Add multi-hop tasks and ethical/multicultural implications section
10. Prepare for publication: arXiv preprint → ACL/NeurIPS workshops
"""

DOCUMENT_3 = """
[DOCUMENT 3: DETAILED REVIEW OF V2.0 RESEARCH PLAN]

OVERALL VERDICT: "Pursue it, but prioritize pilots on a subset to validate feasibility."

SECTION-BY-SECTION ANALYSIS:

1. OBJECTIVES & HYPOTHESES
- Pros: H1-H4 are testable, grounded in stats
- Critiques: Add null hypotheses, tie to SPAN (arXiv 2511.09993), TRAVELER (arXiv 2505.01325)

2. FACTORS AND CONDITIONS
- Pros: Excellent controlled design with factorial analysis
- Critiques: Compute risk (4 langs × 5 holidays × 40 years × 7 conditions = ~7,840 queries/model)
- Recommendation: Pilot on 1-2 models/holidays first

3. DATASET DESIGN
- Pros: Systematic, using proper libraries (lunardate, korean_lunar_calendar, hdate, ummalqura)
- Critiques: Provide pure Python impls for no-install envs, add "fake" dates as negatives

4. MODELS & PROVIDERS
- Pros: Real, diverse list
- Critiques: Add o1-preview, track versions, set temp=0, max_tokens=500

5. PROMPT TEMPLATES
- Pros: Standardized and language-specific
- Critiques: Vary k (1-5), add partial-resolver, ensure native phrasing

6. METRICS
- Pros: F1/FPR fix accuracy-only bias
- Critiques: Add ANOVA for H1 stratification, categorize hallucinations

7. STATISTICAL PLAN
- Pros: Pragmatic (χ²/Fisher's, CIs)
- Critiques: Pre-compute power analysis, add visualization plots

8. OUTPUTS & REPRODUCIBILITY
- Pros: Gold standard repo structure
- Critiques: Add license, README, Colab demo, ethics section on biases
"""

TASK_PROMPT = """
## TASK

You are reviewing the Movable Feast study - a benchmark for LLM temporal reasoning on movable-date holidays. You have been provided three documents:

1. **DOCUMENT 1**: The main paper (LaTeX source) with methodology, results, and claims
2. **DOCUMENT 2**: Proposed upgrades and improvements (prioritized list)
3. **DOCUMENT 3**: A detailed review of the v2.0 research plan

Your task is to provide a RUTHLESS, DATA-DRIVEN ASSESSMENT that:

1. **Identifies remaining methodological weaknesses** not addressed by the proposed upgrades
2. **Challenges the core claims** - especially the "algorithmic behavior" claim for Grok
3. **Evaluates the proposed upgrade plan** - is it sufficient? What's missing?
4. **Provides specific, actionable recommendations** for making this peer-review ready
5. **Assesses publication viability** - what venue? What additional work is required?

Focus on:
- Statistical validity and power
- Confounds and alternative explanations
- Reproducibility and transparency
- Overgeneralization of claims
- Missing controls or ablations
- Positioning relative to existing benchmarks (SPAN, TimeBench, etc.)

Be blunt. Be precise. Serve the truth.

---

""" + DOCUMENT_1 + "\n\n---\n\n" + DOCUMENT_2 + "\n\n---\n\n" + DOCUMENT_3


def main():
    print("=" * 70)
    print("GPT-5-Pro RUTHLESS REVIEW")
    print("=" * 70)
    print(f"Persona: Ruthless AI Evaluation Researcher")
    print(f"Documents: 3 (Paper + Upgrades + Review)")
    print(f"Estimated time: 5-10 minutes")
    print("=" * 70)
    print("\nSending to GPT-5-Pro via Responses API...")

    start = time.time()

    try:
        response = client.responses.create(
            model="gpt-5-pro",
            instructions=RUTHLESS_REVIEWER_PERSONA,
            input=TASK_PROMPT,
        )

        elapsed = time.time() - start

        print(f"\n{'=' * 70}")
        print(f"RESPONSE RECEIVED ({elapsed:.1f}s)")
        print(f"{'=' * 70}")
        print(f"\nModel: {response.model}")
        print(f"Usage: {response.usage}")
        print(f"\n{'=' * 70}")
        print("RUTHLESS REVIEW:")
        print(f"{'=' * 70}\n")
        print(response.output_text)

        # Save to file
        output_file = "/claude-workspace/worktrees/sessions/session-20251202-231347-1356581/movable_feast/results/gpt5_pro_review.md"
        with open(output_file, "w") as f:
            f.write(f"# GPT-5-Pro Ruthless Review\n\n")
            f.write(f"**Model**: {response.model}\n")
            f.write(f"**Response Time**: {elapsed:.1f}s\n")
            f.write(f"**Usage**: {response.usage}\n\n")
            f.write(f"---\n\n")
            f.write(response.output_text)

        print(f"\n\n{'=' * 70}")
        print(f"Review saved to: {output_file}")
        print(f"{'=' * 70}")

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
