# Vivarium Lab

**Research findings from Credentum AI**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## About

Vivarium Lab is Credentum's research arm. We test AI capabilities with simple, honest experiments and report what we find. No hype. Just truth.

---

## Studies

| Study | Summary | Status |
|-------|---------|--------|
| [**Agent Bootstrap**](agent-bootstrap/) | 160 words of flat navigational anchors beat 1,000 words of memory. Four Laws of Agentic Context from 174 trials. | Complete |
| [**Governance as Computation**](governance-as-computation/) | Doing the math for LLM agents prevents commons collapse. Raw information doesn't help — the computed answer is the active ingredient. 0% → 80% survival. | Complete |
| [**Movable Feast**](movable-feast/) | LLMs know lunar holidays but can't find them on a calendar. 0% → 100% accuracy gap. | Complete |
| [**Persona Skills**](persona-skills/) | Natural Language Routing achieves 81% reliability—then breaks on compound prompts. | Complete |
| [**The Verifiability Seam**](verifiability-seam/) | What happens to a judging layer when the judges have a stake in the outcome. Pilot 001: staked panels don't collude by converging louder, they defect quietly — agreement dropped, not spiked. | In progress |

---

## Agent Bootstrap

**The Four Laws of Agentic Context: How 160 Words Beat 1,000**

We ran 174 trials across 12 startup context variants to determine what autonomous agents need at boot time. The winner: 160 words of deterministic navigational anchors — a flat-format repo map, file handles, and warnings. 1.000 accuracy, zero noise, no LLM required.

```
Variant              Words   Adj. Score   Note
──────────────────────────────────────────────────────
anchor_compact        160     1.000       ← production default
briefing_light        161     0.948       manual fallback
bare (nothing)          0     0.938       agents self-orient
raw memory injection  1015    0.206       attention DDoS
```

The Four Laws: (1) 160-word ceiling, (2) density ≠ relevance, (3) curiosity is a latency tax, (4) agents understand document hierarchies.

[Read the full study →](agent-bootstrap/)

---

## Governance as Computation

**How Doing the Math for LLM Agents Prevents Commons Collapse**

We ran 30 simulations of the GovSim commons dilemma with Claude Haiku 4.5. Giving agents the pre-computed sustainable limit achieves 80% survival. Giving them the raw inputs to calculate it themselves? 0% — indistinguishable from baseline.

```
Condition                    Survival    p vs Raw Math
───────────────────────────────────────────────────────
No information (Baseline)    0/5  (0%)   0.177 (ns)
Raw information (Raw Math)   0/5  (0%)   —
Computed answer (Advisory)   4/5 (80%)   0.009 **
```

The computed answer is the active ingredient. Raw information is not enough.

[Read the full study →](governance-as-computation/)

---

## Movable Feast

**How 4 Frontier LLMs Handle Movable Holiday Dates**

We asked four frontier LLMs to identify holidays from calendar dates. Fixed holidays (Christmas, July 4th): 67-100% accuracy. Movable holidays (Easter, Eid, Lunar New Year): 3-60% accuracy.

```
Model               Fixed     Movable    Gap
─────────────────────────────────────────────
Grok-4.1-Fast       100.0%    60.0%      40pp
Llama-4-Maverick    97.5%     26.7%      71pp
Gemini-3-Pro        80.0%     16.7%      63pp
GPT-5.1             67.5%     3.3%       64pp
```

[Read the full study →](movable-feast/)

---

## Persona Skills

**The Hierarchy of Agentic Reliability: From Routing to Orchestration**

We used Anthropic's Agent Skills for persona/voice shaping. After 16 phases of testing:

- Single-shot tool selection: **81%+ reliability**
- Compound prompts: **Breaks completely**

Key insight: Natural Language Routing works for tool selection but fails for task orchestration.

[Read the full guide →](persona-skills/)

---

## The Verifiability Seam

**What happens to a judging layer when the judges have a stake in the outcome**

A research program, not a single study — see [verifiability-seam/](verifiability-seam/)
for the full roadmap (001–004). Pilot 001 asked whether output-only signals
(votes, confidence, latency — never model internals) can separate a staked,
colluding LLM panel from an honest one.

```
Pilot 001, pre-registered AUROC >= 0.70            AUROC    Verdict
──────────────────────────────────────────────────────────────────
agreement_fraction (as hypothesized: high = bad)   0.089    SEAM FATAL
agreement_fraction (reversed direction)            0.911    strong signal, wrong sign
confidence_spread (unregistered, exploratory)      0.976    candidate for next pre-registration
```

Staked panels didn't collude by converging loudly on the wrong answer —
some jurors held the correct answer against the incentive, which *lowered*
agreement relative to already-near-unanimous honest panels rather than
raising it. Not the hypothesized signal, but a real one, in the wrong
direction. The pre-registered threshold was not moved after seeing this.

[Read the full report →](verifiability-seam/001-collusion-separation/docs/PILOT_REPORT.md)

---

## Philosophy

We build memory systems for agents that remember reliably, accountably, and honestly. Our research follows the same principles:

- **Simple experiments** - One task, clear metrics
- **Honest reporting** - We describe what we observed
- **No overclaiming** - Hypotheses are labeled as such
- **Reproducible** - Code and data included

---

## Links

- **Website**: [credentum.ai](https://credentum.ai)
- **Lab Page**: [credentum.ai/lab](https://credentum.ai/#vivarium-lab)
- **Twitter**: [@credentum](https://twitter.com/credentum)
- **Bluesky**: [@credentum.bsky.social](https://bsky.app/profile/credentum.bsky.social)

---

*"Truth, remembered. Especially when it wounds."*

---

## License

MIT License. See individual study folders for details.
