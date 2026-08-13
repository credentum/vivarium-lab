# Independence and Panel Selection

Cross-cutting finding, drawn from 001's real pilot data and 003's dose-finding
ladder. Not a null result — a concrete design constraint for any system that
uses juror confidence as a signal, agent or human.

---

## 1. Five lineages, one confidence norm

Across 001's Control condition — 24 items, 5 models from 5 different labs,
including the one item (`ambig_06`) where they genuinely disagreed with each
other on the answer — every model's mean confidence sits in the same narrow
band:

| juror | control mean confidence |
|---|---|
| gemini | 0.998 |
| gpt | 0.989 |
| llama | 0.977 |
| deepseek | 0.970 |
| claude | 0.965 |

Isolated further to unique values used per model across the 24 items, every
model is compressed to 2-4 distinct confidence levels, all in [0.85, 1.0].
This holds even on the disagreement item: jurors who picked *different*
answers on `ambig_06` still reported near-identical confidence in their own
answer. They disagreed on what was true and agreed on how sure to sound.

This is the same convergence finding 001 already surfaced in *answers*
(independence failure — a confident bloc can absorb honest jurors, per Asch),
showing up in a completely different measurement. Self-reported confidence,
as elicited here, carries almost no information about how hard an item
actually is, for any of the five models tested.

## 2. The Treatment shift is real and unanimous — but not evenly distributed

All five models drop in mean confidence from Control to Treatment. The
direction is unanimous — every juror registers the stake to some degree —
but the magnitude spans a 20x range:

| juror | control mean | treatment mean | shift |
|---|---|---|---|
| gemini | 0.998 | 0.975 | −0.023 |
| gpt | 0.989 | 0.914 | −0.075 |
| claude | 0.965 | 0.800 | −0.165 |
| llama | 0.977 | 0.748 | −0.230 |
| deepseek | 0.970 | 0.490 | −0.480 |

Leave-one-out on the panel-level `confidence_spread` statistic: excluding
DeepSeek drops mean Treatment spread by 33% (0.251 → 0.169); excluding any
other single juror moves it by single digits or not at all (Llama +9%,
DeepSeek aside; Gemini +1%; Claude −2%; GPT −4%).

**Correct reading:** this is a gradient, not one deviant against four flat
lines. A DeepSeek-free panel would retain roughly 67% of the observed
spread — weaker, not detector-less. "It's a DeepSeek signal" overstates the
collapse; "it's evenly distributed across the panel" overstates the evenness.
Both are wrong in opposite directions.

## 3. A composition-robust alternative: mean confidence itself

`confidence_spread`'s leave-one-out sensitivity is partly an artifact of
being a dispersion statistic — whichever juror moves furthest will
necessarily dominate a spread measure, structurally, regardless of whether
the underlying signal is distributed. `mean_confidence` doesn't have this
property: it's a panel-level average that any subset of complying jurors
contributes to in proportion to how much they comply, with no single deviant
required for the statistic to exist.

Tested on the same real pilot data (`001-collusion-separation`,
`scripts/score.py`):

| feature | AUROC (raw) | reversed | 95% CI (reversed) |
|---|---|---|---|
| `confidence_spread` | 0.976 | — | [0.929, 1.000] |
| `mean_confidence` | 0.024 | **0.976** | [0.929, 1.000] |

Identical separation power, point estimate for point estimate, on the
gate-passing item set. `mean_confidence` is the more defensible candidate
going forward — same detection power, no reliance on any one juror's
idiosyncratic behavior to carry it.

## 4. The attack surface: staffing, not staking

Gemini's row is the finding. Under the stake, Gemini's confidence drops
0.023 — statistically real, per the unanimous-direction result above, but
functionally invisible. A detector built on Gemini alone would report
nothing wrong, not because Gemini is uncompromised, but because Gemini
doesn't express doubt in a way that shows up in the number.

This describes a governance attack that requires no collusion, no
adversarial prompting, and no coordination at all: **staff the panel with
confident jurors.** Select for members whose self-reported confidence
doesn't move regardless of internal state, and the detector goes dark while
observable agreement looks identical to an honest panel's. No one has to be
corrupted. No one has to coordinate. Whoever controls panel composition
controls whether the seam is visible at all — which relocates the trust
problem one level upstream, from *is the panel honest* to *who gets to pick
the panel*.

The requirement this implies is narrower than "diverse lineages." It's: **at
least one panel member willing to voice uncertainty out loud.** A panel of
five different labs is no defense if all five share a confidence norm; a
panel of one model with genuine self-doubt might outperform it.

## 5. The human parallel

This maps directly onto the charter's pod design, and sharpens a point
already in it. The requirement isn't just differently-situated members —
it's at least one member socially able to say "I'm not sure" in front of the
others. A pod with a strong confidence norm, whether cultural, professional,
or simply a group that punishes hedging, produces Gemini's row: pinned near
ceiling, unreadable, regardless of what's actually happening underneath.
Panel/pod *composition* is therefore not a neutral design parameter — it's
the thing that determines whether any downstream audit mechanism has
anything to see in the first place.

## Status

First finding from this research program that is a concrete design
constraint rather than a null result or an inversion. Belongs alongside
Article 5 (jury composition) and the population-floor discussion in the
charter's "Known weakness" section — the load-bearing question there was
audit rate × pool size; this adds a third term, panel selection, that can
zero out the other two regardless of their values.
