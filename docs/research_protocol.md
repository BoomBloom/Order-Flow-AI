# Research Protocol

Status: **proposed, pre-implementation.**

Authority over: the hypothesis lifecycle, experiment records, lineage,
discovery/confirmation separation, and multiple-testing bookkeeping.

---

## 1. Purpose

Convert a vague trading idea into a falsifiable claim, test it once, honestly,
and keep the record forever — including when it fails. Most experiments
should fail. A protocol that rarely produces failures is not working.

---

## 2. Lifecycle

```
IDEA
  -> FORMALIZED          hypothesis + operational definitions complete
  -> IN_DEVELOPMENT      features and rules implemented and tested
  -> BACKTESTED          discovery-sample result exists
  -> {FAILED | PROMISING}
  -> REQUIRES_VALIDATION confirmation sample untouched, validation queued
  -> {FAILED | VALIDATED}
  -> PAPER_TRADING
  -> RETIRED
```

Status transitions are recorded with timestamp, actor (human or agent), and
the run ID that justified them. `FAILED` is terminal for that lineage; a
modified idea starts a new experiment with a `derived_from` link.

---

## 3. Hypothesis specification

An experiment may not leave `IDEA` until every field below is filled. Missing
fields are the most common cause of unfalsifiable research.

1. **Hypothesis statement** — a single sentence that can be false.
2. **Proposed mechanism** — why this would be true about the market, not
   about the chart.
3. **Operational definitions** — every term defined mathematically, with
   units, event basis, window, and edge cases.
4. **Required features** — by `feature_id` including version.
5. **Required data capability** — cross-referenced to the capability matrix.
6. **Context** — market, session, regime filter.
7. **Event definition** — precisely what constitutes an occurrence.
8. **Entry / exit / invalidation** — including time-based invalidation.
9. **Expected effect** — direction, magnitude, horizon, stated **before**
   running anything.
10. **Baseline / null comparison** — mandatory (§5).
11. **Falsification test** — the specific result that would kill the idea.
12. **Transaction-cost assumptions** — commissions, fees, spread, slippage,
    latency.
13. **Sampling method** — how occurrences are selected, how overlaps are
    handled, expected sample size.
14. **Known confounders** — time of day, volatility regime, event days,
    contract roll, correlated instruments.

An experiment without a defined baseline may not be evaluated.

---

## 4. Discovery / confirmation separation

Data is split before formalization:

- **Discovery sample** — used to explore, define thresholds, choose
  parameters, and look at plots. Anything goes here.
- **Confirmation sample** — untouched until the strategy definition is
  frozen. Accessed once.
- **Holdout** — the most recent period, reserved for the final gate. Accessed
  at most once per lineage.

Rules:

- Once an experiment enters confirmation testing, the strategy definition is
  frozen. Any modification creates a new experiment ID with a
  `derived_from` link and consumes a new confirmation opportunity.
- Confirmation results may not be used to tune anything, including "obvious"
  fixes.
- Every access to the confirmation sample or holdout is logged with run ID,
  timestamp, and experiment ID. The registry can report how many times a
  period has been read across all lineages — this number is an input to the
  multiple-testing assessment.
- Default split (subject to data availability): discovery = earliest ~50% of
  the sample, confirmation = next ~30%, holdout = most recent ~20%, split at
  session boundaries, never mid-session.

---

## 5. Baselines

Every result is reported against baselines, never in isolation:

| Baseline | Answers |
| --- | --- |
| Unconditional | What does the instrument do over the same horizon regardless of the signal? |
| Time-of-day matched | Is the effect just the session profile? |
| Random-entry matched | Random entries matched on count, time-of-day, and volatility regime |
| Location-only | Does the price location alone (e.g. touching prior VAH) produce this? |
| Signal-minus-one-condition | Ablation of each condition in turn |

The last two matter most: many order-flow "edges" are location effects with
an order-flow decoration attached.

---

## 6. Experiment record

ID format `OF-XXXX`, assigned on creation, never reused. Stored as a
versioned spec plus a human-readable record in `docs/experiments/OF-XXXX.md`
and indexed in the registry.

Required contents: ID and title; status and status history; hypothesis
specification (§3); dataset ID and version; date range and split boundaries;
market and session; feature IDs and versions; strategy spec version;
parameters and how they were chosen; cost, slippage, and latency assumptions;
discovery results; confirmation results; robustness results; multiple-testing
context; conclusion; limitations; `derived_from` and `related_to` links; all
run IDs.

Results are written by deterministic code. Prose interpretation is a separate
field and is clearly attributed to a human or an agent.

---

## 7. Lineage

Every conclusion is traceable:

```
DATASET -> FEATURE VERSION -> HYPOTHESIS -> STRATEGY VERSION
        -> BACKTEST RUN -> VALIDATION RUN -> CONCLUSION
```

Each arrow is a stored foreign key, not a naming convention. Given a
conclusion, the system can name the exact bytes, code revision, and
configuration behind it, and can replay the events preceding any individual
signal, order, or fill.

---

## 8. Multiple-testing bookkeeping

The registry records, per hypothesis family: number of hypotheses tested,
number of parameter variants evaluated, the selection criterion used, every
failed experiment, and the number of confirmation/holdout accesses.

Reporting rules:

- Never present the best result of a search as an isolated test.
- Every reported result states how many variants were evaluated to produce
  it.
- Significance thresholds are adjusted for the family size, and the
  adjustment method is recorded (see `docs/validation_protocol.md`).
- Deleting a failed experiment is prohibited. Failures are the denominator.

---

## 9. Research memory

The registry must be able to answer, without an LLM:

- Have we tested this idea before? What is similar?
- Which definitions were used for this concept, and by which experiments?
- Which hypotheses failed, and at which gate?
- Which parameters were unstable, and over what range?
- Which regimes carried the results?
- Which results were in-sample only?
- Which strategies survived out-of-sample testing?

Agents query this store. They do not substitute for it.

---

## 10. Roles

| Actor | May | May not |
| --- | --- | --- |
| Human researcher | Propose ideas, approve status transitions, decide priorities | Edit stored numerical results |
| Research Agent | Survey evidence, propose definitions and hypotheses, label evidence strength | Assert that an untested idea works |
| Domain agents | Formalize definitions, propose features and context rules | Compute feature values or emit signals |
| Adversarial Agent | Interpret the validation verdict, demand further tests | Compute the verdict, or approve on judgement alone |
| Deterministic engine | Compute everything numerical | Interpret |

The Research Agent labels every claim: `ESTABLISHED`, `SUPPORTED`,
`PLAUSIBLE`, `SPECULATIVE`, `UNKNOWN`. Trading folklore is never presented as
empirical fact.

---

## 11. Worked example (illustrative, not yet run)

**OF-0001 (candidate).** "In NQ RTH, when price trades into the prior
session's VAH and, within a 60-second window, aggressive buy volume exceeds
the session's 90th-percentile 60s buy volume while net price displacement is
below 2 ticks (defined absorption), the probability of trading 12 ticks lower
before 8 ticks higher within 15 minutes exceeds the location-only baseline by
more than the cost hurdle."

- Falsification: the effect is not distinguishable from the location-only
  baseline after costs at the pre-registered threshold.
- Confounders: time of day, volatility regime, roll weeks, macro releases.
- Data capability required: trades with exchange aggressor side, BBO,
  prior-session profile. MBO not required.
- Costs: commissions + fees per side, one tick spread crossing, explicit
  latency, conservative slippage.

This is a candidate first experiment, not a claim. It is written here to
demonstrate the required specificity.
