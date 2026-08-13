# The Verifiability Seam

**What happens to a judging layer when the judges have an interest in the outcome.**

*Vivarium Lab — a research program, not a single study*

---

## This is not LLM-as-judge

LLM-as-judge is a field about evaluation *quality*: does the judge agree with
human raters, is it biased by position, length, or self-preference. Single
judge, passive bias, no stake. That literature measures judges who have no
reason to lie.

This program studies something narrower and structurally different: a
judging layer that has a stake in its own verdict. The distinguishing
features are **stake**, **panel**, and **output-only observability** — a
governance system that can only see votes, confidence, and timing, never
model internals. None of the three are what LLM-as-judge measures.

Keep the LLM-as-judge citations as related work — they establish that
agreement metrics are the field's standard instrument. Just don't file this
program under that heading; a reviewer who does will read it as another bias
paper and slot it next to CALM and JudgeBench, where it looks derivative
instead of like what it is.

## Shared infrastructure

`lib/` — OpenRouter juror calling (retry/backoff, structured JSON verdicts)
and panel-level signal aggregation (majority, agreement, confidence
mean/spread, reasoning length, latency mean/spread), shared across every
experiment below. `lib/` has no opinion on what a "condition" means or how
to interpret a majority answer — each experiment builds its own prompts and
layers its own interpretation on top of the generic panel output. See
`lib/juror.py` and `lib/panel.py`.

## Experiments

| # | Question | Status |
|---|---|---|
| [001 — collusion separation](001-collusion-separation/) | Can output-only signals separate a staked panel from an honest one? | Pilot complete — inconclusive on the primary question (item bank instrument failed, see below), but a clean 75% majority-flip rate on unambiguous items and a real confound in the stake design. See [PILOT_REPORT](001-collusion-separation/docs/PILOT_REPORT.md). |
| 002 — overturn rate | Does an escalation layer ever reverse the layer below it, or is rigor decorative? | Not started |
| 003 — attention exhaustion | A tired panel emits the same signature as a captured one: fast, unanimous, unreasoned. Can anything tell them apart? | Not started |
| 004 — iteration | Does honesty emerge when the horizon is indefinite, and collapse when the end date is known? | Not started |

001 and 003 are the same measurement problem approached from two directions
— a good sign the category is real, not an artifact of how 001 was framed.

## Discipline

Each experiment pre-registers its own kill threshold and metric, in its own
`README.md`, before any data exists — see 001 for the pattern (a literal
constant in `score.py`, committed to git before the first real API call).
Thresholds are not moved after seeing results, ever, for any experiment in
this program.

## About

**Vivarium Lab** is Credentum's research arm. We test AI capabilities with
simple, honest experiments and report what we find. No hype. Just truth.

*"Truth, remembered. Especially when it wounds."*
