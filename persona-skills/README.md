# Persona Skills for Claude

**The Hierarchy of Agentic Reliability: From Routing to Orchestration**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Vivarium Lab Research Guide | December 2025*

---

## TL;DR

We used Anthropic's Agent Skills system for persona/voice shaping (off-label but effective). After 16 phases of testing, we achieved **81%+ routing reliability** for single-shot tool selection.

Then we found the ceiling: **compound prompts fail completely**.

```
Task Type              Reliability
─────────────────────────────────────
Single-shot routing    81%+
Multi-step workflows   Breaks
```

Natural Language Routing works for tool selection. It fails for task orchestration.

---

## Key Findings

### 1. Activation is Bimodal

| Prompt Type | Activation Rate |
|-------------|-----------------|
| Abstract trigger phrase only | ~0% |
| Concrete dilemma with named options | ~100% |

### 2. Few-Shot Examples Double Activation

- Semantic definitions only: **39%** activation
- With few-shot examples: **81%** activation

Examples create a "semantic cone" - the model interpolates between them.

### 3. Three Failure Classes (All Solved)

| Failure | Symptom | Solution |
|---------|---------|----------|
| **Ambiguity** | Wrong skill activates | Few-shot examples |
| **Overconfidence** | Skill activates when shouldn't | PROHIBITED constraints |
| **Collision** | Overlapping namespaces | Scope exclusion |

### 4. The Hard Limit

Compound prompts ("do X, then trigger Y") fail due to:
- **Token Gravity**: Early tasks absorb all attention
- **Context Decay**: Later instructions fade

Multi-step workflows require a Supervisor or Human-in-the-Loop.

---

## Repository Structure

```
persona-skills/
├── README.md              # This file
├── guide.md               # Full 1,450-line practitioner's guide
├── skill-descriptions-v3.md  # Skill description patterns
└── SKILL.md               # Example skill file
```

---

## The Full Guide

[`guide.md`](guide.md) contains:

- 16-phase experiment narrative
- 48 systematic test results
- Expert Panel Framework
- Skill templates you can copy
- Reproducible test harness
- Recommendations for skill authors

---

## Recommendations

| Use Case | Recommended Approach |
|----------|---------------------|
| Single-shot tool selection | Natural Language Routing |
| Multi-step workflows | Human-in-the-Loop OR Supervisor pattern |
| High-reliability routing | Few-shot examples + PROHIBITED constraints |
| Persona/behavioral skills | Observable signals + verbal tics + examples |

---

## Citation

```bibtex
@misc{personaskills2025,
  title={Persona Skills for Claude: The Hierarchy of Agentic Reliability},
  author={Vivarium Lab},
  year={2025},
  howpublished={GitHub: \url{https://github.com/credentum/vivarium-lab}},
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

MIT License.
