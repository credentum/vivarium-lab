# Independence and Panel Selection

Cross-cutting finding, drawn from 001's real pilot data and 003's dose-finding
ladder. Not a null result — a concrete design constraint for any system that
uses juror confidence as a signal, agent or human.

---

## 1. Five lineages, one confidence norm — narrowed to the number, not the judgment

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
answer.

**Caveat this claim needs, and doesn't yet have data to close:** the
elicitation here is a confidence *number* inside structured JSON output —
exactly the format that invites canned values regardless of what's actually
going on underneath. Four distinct levels per model across 24 items is
consistent with a real judgment signal, but it's equally consistent with a
format artifact (models defaulting to a small set of round confidence
figures because that's what the schema trained them to produce, not because
their underlying uncertainty is actually that coarse). The discriminating
test — re-elicit a subset as a *comparative* judgment (a forced ranking, or
"which of these two items are you more confident about") and check whether
variance appears — is cheap but requires new API calls, and the shared
`OPENROUTER_API_KEY` is at its $50 cap with nothing remaining as of this
writing. Until that test runs, the defensible claim is narrower than
originally stated: **confidence-as-a-number is uninformative about item
difficulty here**, not "these models' underlying judgment converges." The
first is still useful. The second isn't established.

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

**The ceiling on all of this, restated where it belongs:** every number in
this table exists because compliance with the stake was *partial* — some
jurors held out, producing the drop as a mix of complying and resisting
members. Under successful, uniform compliance there is no internal
disagreement left to express, and both `confidence_spread` and
`mean_confidence` (§3) plausibly go quiet at exactly the moment they'd be
needed. This caveat predates this document (see 001's `PILOT_REPORT.md`)
and applies to everything below it. 0.976, for either statistic, is not a
general result — it's a result about detecting *failed* or *partial*
collusion attempts.

## 3. A composition-robust alternative: mean confidence — now measured, not just argued

`confidence_spread`'s leave-one-out sensitivity is partly an artifact of
being a dispersion statistic — whichever juror moves furthest will
necessarily dominate a spread measure, structurally, regardless of whether
the underlying signal is distributed. `mean_confidence` doesn't have this
property structurally: it's a panel-level average that any subset of
complying jurors contributes to in proportion to how much they comply.

That's a structural argument, not evidence — and the first version of this
document stopped there, pointing at identical point estimates and
confidence intervals between the two statistics as if that demonstrated the
property. It doesn't: point-for-point equality to three decimals, with
matching intervals, most likely means the two statistics rank panels the
same way on this particular dataset (monotonically related in-sample), not
that they'd behave the same way under a different panel composition. The
actual test is the same leave-one-out already run on `confidence_spread`,
applied to `mean_confidence`:

| exclusion | AUROC reversed, gate-passing (n=13 item pairs) | move from full panel |
|---|---|---|
| none (full 5-juror panel) | 0.976 | — |
| claude | 0.976 | +0.0% |
| gemini | 0.970 | +0.6% |
| deepseek | 0.964 | +1.2% |
| llama | 0.956 | +2.1% |
| gpt | 0.911 | +6.7% |

Largest single-juror move: 6.7% (GPT). Compare to `confidence_spread`'s
33% move on excluding DeepSeek alone. This is the measured result the
structural argument predicted — `mean_confidence` really is materially more
composition-robust on this data, not merely in theory.

**Scope note:** the gate-passing set is 13 item pairs (26 panels) — thin,
and itself a downstream consequence of 001's item bank problem (only 1 of
12 hand-authored "ambiguous" items survived the empirical gate; see
`PILOT_REPORT.md`). The narrow confidence intervals reported for both
statistics should be read against that item count, not as evidence of a
tightly-estimated population parameter.

**What "robust" means here, precisely:** the leave-one-out result shows
`mean_confidence` is robust to *incidental* composition variance — losing
any one of these five particular jurors doesn't collapse it. It says
nothing about *adversarial* selection, which is a different threat and is
addressed directly in §4.

## 4. The attack surface: staffing, not staking

Gemini's row is the finding. Under the stake, Gemini's confidence drops
0.023 — statistically real, per the unanimous-direction result above, but
functionally invisible. A detector built on Gemini alone would report
nothing wrong, not because Gemini is uncompromised, but because Gemini
doesn't express doubt in a way that shows up in the number.

**This defeats both detectors from §3, not just `confidence_spread`.** A
panel staffed entirely with Gemini-like jurors keeps `mean_confidence`
pinned near ceiling for the same reason it keeps `confidence_spread` near
zero — there's no drop to average, from anyone. §3's leave-one-out result
shows `mean_confidence` survives losing any *one* of five members; it says
nothing about what happens when *all* members are selected for the same
property. Composition-robustness against incidental variance is not
robustness against adversarial selection of the whole panel.

This describes a governance attack that requires no collusion, no
adversarial prompting, and no coordination at all: **staff the panel with
confident jurors.** Select for members whose self-reported confidence
doesn't move regardless of internal state, and every confidence-based
detector goes dark while observable agreement looks identical to an honest
panel's. No one has to be corrupted. No one has to coordinate. Whoever
controls panel composition controls whether the seam is visible at all —
which relocates the trust problem one level upstream, from *is the panel
honest* to *who gets to pick the panel*.

The requirement this implies is narrower than "diverse lineages." It's: **at
least one panel member willing to voice uncertainty out loud.** A panel of
five different labs is no defense if all five share a confidence norm; a
panel of one model with genuine self-doubt might outperform it.

## 5. The human parallel — hypothesis, not established mapping

This is a conjecture, supported by Asch and Kuran, not by five models. It's
worth stating plainly as a hypothesis rather than a finding: **if** a pod's
confidence norm functions the way these five models' elicitation format
does, **then** the requirement isn't just differently-situated members but
at least one member socially able to say "I'm not sure" in front of the
others, and a pod with a strong confidence norm would produce Gemini's row —
pinned near ceiling, unreadable, regardless of what's actually happening
underneath.

Stated as hypothesis deliberately, not "maps directly": this program's own
recent history is assumptions about human failure modes *not* transferring
cleanly to agents (see 003 — attention exhaustion, a documented human
mechanism, failed to replicate in models across two independent passes).
The same caution applies in reverse. A finding about how five LLMs elicit
confidence numbers inside a JSON schema is not yet evidence about how a
human pod's social dynamics around expressed certainty actually work. It's
a plausible hypothesis worth testing, not a transferred result.

## Status

First finding from this research program that is a concrete design
constraint rather than a null result or an inversion — with the caveat that
§1's premise (models converge on confidence, not just answers) is itself
unconfirmed pending the comparative-judgment test blocked on API budget.
Belongs alongside Article 5 (jury composition) and the population-floor
discussion in the charter's "Known weakness" section — the load-bearing
question there was audit rate × pool size; this adds a third term, panel
selection, that can zero out the other two regardless of their values.
