# Research Protocol

Status: **proposed, pre-implementation.**

Authority over: the hypothesis lifecycle, split policy, experiment records,
lineage, and multiple-testing bookkeeping.

---

## 1. Purpose

Convert a vague trading idea into a falsifiable claim, test it once, honestly,
and keep the record forever — including when it fails. Most experiments
should fail. A protocol that rarely produces failures is not working.

---

## 2. Lifecycle

```
IDEA
  -> FORMALIZED          hypothesis, split policy, and thresholds complete
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

**`FORMALIZED` is a hard gate.** An experiment may not enter it without a
complete hypothesis specification (§3), a pre-registered split policy (§4),
and pre-registered acceptance thresholds (§5). The registry refuses a
validation run for an experiment missing either of the last two
`[ENFORCED]`.

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
5. **Required data capability and minimum provenance tier** — cross-
   referenced to `docs/data_specification.md` §3–4.
6. **Context** — market, session, regime filter.
7. **Event definition** — precisely what constitutes an occurrence.
8. **Label definition and `label_horizon`** — the outcome being predicted and
   how far into the future it looks. Labels are produced by the separate
   labelling pass (`src/ofa/labels/`, delivered in Phase 5) and are never
   visible to a feature; see `docs/architecture.md` §6.7.
9. **Entry / exit / invalidation** — including time-based invalidation.
10. **Expected effect** — direction, magnitude, horizon, stated **before**
    running anything.
11. **Baseline / null comparison** — mandatory (§6).
12. **Falsification test** — the specific result that would kill the idea.
13. **Transaction-cost, slippage, latency, and queue-model assumptions.**
14. **Sampling method** — how occurrences are selected, how overlaps are
    handled, expected sample size.
15. **Known confounders** — time of day, volatility regime, event days,
    contract roll, correlated instruments.
16. **Selection-bias disclosure** (§9).

An experiment without a defined baseline may not be evaluated.

---

## 4. Split policy — pre-registered, per experiment

**There is no universal split.** The 50/30/20 chronological split is a
*default starting policy*, not a rule. Split policy is experiment
configuration, recorded at `FORMALIZED`, and validated before any run.

### 4.1 What every scheme must specify

Regardless of scheme, a `SplitPolicy` declares **eight fields**, all
required:

| Field | Meaning |
| --- | --- |
| `scheme` | One of §4.2 |
| `segments` | Named disjoint segments and their selection rule |
| `purge` | Removal of samples whose label horizon overlaps another segment |
| `embargo` | Additional buffer after each evaluation window |
| `warm_up` | Per-segment burn-in (§4.3) |
| `boundary_rule` | Where a segment may start/end — session boundaries by default, never mid-session |
| `holdout_policy` | Fixed or time-extending (§4.4) |
| `rationale` | Why this scheme suits this hypothesis |

**Purge width is driven by `label_horizon`**, not chosen by hand. A sample
whose label resolves inside another segment is purged from the training or
discovery side. This is the mechanism that stops an outcome from being
visible on both sides of a boundary.

`label_horizon` is emitted by the labelling pass, which is why the split
engine (Phase 6) depends on labels existing (Phase 5). A split policy cannot
be executed against a strategy whose labels are undefined.

### 4.2 Supported schemes

| Scheme | Description | Suits |
| --- | --- | --- |
| `CHRONOLOGICAL_BLOCK` | Contiguous time blocks: discovery, confirmation, holdout. **Default initial policy.** | Ideas where regime drift is itself part of the question |
| `INTERLEAVED_BLOCK` | Alternating blocks (e.g. by month) assigned to segments, with purge and embargo | Avoiding the confound where one regime lands entirely in one segment |
| `PURGED_KFOLD` | K-fold with label-horizon purging and embargo | Parameter-stability work with limited data |
| `COMBINATORIAL_PURGED_CV` | Multiple train/test combinations of purged blocks, yielding a distribution of out-of-sample paths rather than one | Where a single OOS path would be uninformative |
| `CROSS_INSTRUMENT` | Discover on one instrument, confirm on another (e.g. NQ → ES, then 6E as a structural contrast) | Microstructure claims that should generalize across correlated products |
| `HYBRID` | An explicit composition, e.g. chronological within instrument plus a cross-instrument holdout | Stated explicitly, never implied |

Notes:

- `CHRONOLOGICAL_BLOCK` remains the default because it is the most honest
  about regime drift. But it confounds "the edge decayed" with "the regime
  changed", which is exactly why it must not be the only option.
- `CROSS_INSTRUMENT` is strong evidence: a flow effect present only in the
  instrument it was discovered on is probably overfit. It is not free —
  NQ and ES are highly correlated, so agreement between them is weaker
  evidence than agreement between NQ and 6E.

### 4.3 Warm-up / burn-in — mandatory

Every segment begins with a burn-in period in which **events are consumed but
signals are discarded**.

- Length ≥ the longest `lookback` declared by any feature in the strategy
  spec.
- Rationale: a feature carrying multi-session state into the confirmation
  window was warmed on discovery data. Causality is intact, but segment
  independence is not.
- The runner calls `on_reset(SPLIT_SEGMENT_START)` at each segment boundary,
  then replays the burn-in window before signals are honoured.
- Burn-in length and the driving feature are recorded in the run manifest.

Omitting this is a silent leak between discovery and confirmation, and it was
the reason this section exists.

### 4.4 Holdout policy

Two options, declared per experiment:

- **`FIXED`** — a fixed reserved window. Once evaluated for a lineage, it is
  spent for that lineage.
- **`TIME_EXTENDING`** (preferred where the data feed continues) — the
  holdout is defined as "data arriving after date D", so newly arriving
  sessions continuously replenish it. Each experiment records the exact
  calendar window it consumed.

Time-extending holdout converts a one-shot resource into a renewable one and
gives honest accounting of how much genuinely unseen data each conclusion
rested on. A fixed holdout erodes monotonically across experiments and
eventually stops being a holdout at all.

Every confirmation and holdout access is logged with run ID, timestamp,
experiment ID, and calendar window `[ENFORCED]`. The registry reports how
many times a period has been read across all lineages; this is an input to
the multiple-testing assessment.

### 4.5 Freeze rule

Once an experiment enters confirmation testing, the strategy definition is
frozen. Any modification creates a new experiment ID with a `derived_from`
link and consumes a new confirmation opportunity. Confirmation results may
not be used to tune anything, including "obvious" fixes.

Note the honest limit: the freeze rule and the prohibition on peeking are
`[PROCESS]` controls for anything a researcher does in a notebook. The
registry can log and refuse *runs* `[ENFORCED]`; it cannot stop a person from
plotting the confirmation sample. §7 addresses this directly.

---

## 5. Acceptance thresholds — pre-registered

Every numeric bar the experiment must clear is written into the experiment
record at `FORMALIZED`, before any run:

- minimum trade count and minimum effective sample size
- minimum expectancy net of costs, in ticks and as a multiple of round-trip
  cost
- maximum acceptable discovery→confirmation degradation
- maximum acceptable profit concentration (top-5%-of-sessions PnL share)
- minimum parameter-plateau fraction
- minimum break-even cost multiple and slippage tolerance
- the multiple-testing adjustment method and the adjusted threshold

The registry refuses a validation run when these are absent `[ENFORCED]`.
Without this binding, every gate in `docs/validation_protocol.md` could be
set after seeing results, which would make the entire validation apparatus
theater.

---

## 6. Baselines

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

## 7. Enforced vs process controls

Being honest about which is which is the point.

| Control | Class |
| --- | --- |
| Registry refuses validation without thresholds or split policy | `[ENFORCED]` |
| Confirmation/holdout run access logged per calendar window | `[ENFORCED]` |
| Feature cannot import labels; cannot consume undeclared capability | `[ENFORCED]` |
| Feature warm-up applied at every segment boundary | `[ENFORCED]` |
| Capability and provenance tier asserted at read | `[ENFORCED]` |
| Not plotting the confirmation sample in a notebook | `[PROCESS]` |
| Not tuning after seeing confirmation results | `[PROCESS]` |
| Completeness and honesty of the discovery search log (§8) | `[PROCESS]` |
| Selection-bias disclosure (§9) | `[PROCESS]` |

A `[PROCESS]` control is not worthless — but it is never reported as if code
enforced it.

---

## 8. Multiple testing

### 8.1 Hypothesis family — definition

Two hypotheses belong to the **same family** when all three hold:

1. **Same scope** — same instrument set and session segment.
2. **Same location concept** — both anchored to the same structural reference
   (prior VAH/VAL, POC, IB extreme, VWAP, opening range, unanchored).
3. **Overlapping trigger feature family** — the triggers draw on at least one
   shared feature family (order flow, liquidity, profile, VWAP, price).

Family assignment is recorded at `FORMALIZED`. It may be overridden — in
either direction — only with written justification in the experiment record,
because the family size drives the significance adjustment and is therefore
the most attackable number in the protocol.

### 8.2 What the registry records

Per family: hypotheses tested, parameter variants evaluated, selection
criterion, every failed experiment, and confirmation/holdout accesses.

### 8.3 Discovery search log

The registry counts what was registered. The real multiplicity lives in the
exploratory work that never became an experiment — the twenty variants tried
in a notebook before one looked interesting.

Every experiment carries a `discovery_search_log`:

- approximate number of variants/thresholds/windows explored during discovery
- which features and locations were tried and abandoned
- the criterion by which this variant was selected for formalization
- whether the hypothesis was formed before or after looking at the data

This is **self-reported `[PROCESS]`** and is labelled as such wherever it is
displayed. An under-reported search log invalidates the adjustment silently,
which is why it is stated plainly rather than dressed up as a control.

### 8.4 Reporting rules

- Never present the best result of a search as an isolated test.
- Every reported result states how many variants were evaluated to produce
  it, plus the self-reported discovery search count.
- Significance thresholds are adjusted for family size, with the adjustment
  method recorded.
- Deleting a failed experiment is prohibited. Failures are the denominator.

---

## 9. Selection-bias disclosure — required

Futures research has weak classical survivorship bias but three real
analogues. Every experiment record discloses:

1. **Contract selection** — front-month-only excludes periods when activity
   migrated to the deferred contract, and treats roll weeks as ordinary. State
   how roll sessions were handled: included, flagged, or excluded.
2. **Period selection** — the date range is bounded by what history we
   purchased and by where the vendor's coverage starts. State the range and
   why it starts and ends where it does.
3. **Instrument selection** — NQ/ES/6E were chosen for liquidity *and*
   researcher familiarity. State whether the hypothesis was tried on other
   instruments first, and what happened.

`[PROCESS]`. It is disclosure, not enforcement — but an undisclosed selection
is indistinguishable from a hidden search.

---

## 10. Experiment record

ID format `OF-XXXX`, assigned on creation, never reused. Stored as a
versioned spec plus a human-readable record in `docs/experiments/OF-XXXX.md`
and indexed in the registry. See `docs/experiments/TEMPLATE.md` for the exact
required contents.

Results are written by deterministic code. Prose interpretation is a separate
field and is clearly attributed to a human or a named agent.

---

## 11. Lineage

Every conclusion is traceable:

```
DATASET -> FEATURE VERSION -> HYPOTHESIS -> STRATEGY VERSION
        -> BACKTEST RUN -> VALIDATION RUN -> CONCLUSION
```

Each arrow is a stored foreign key, not a naming convention. Given a
conclusion, the system can name the exact bytes, code revision, capability
record, and configuration behind it, and can replay the events preceding any
individual signal, order, or fill.

---

## 12. Research memory

The registry must be able to answer, without an LLM:

- Have we tested this idea before? What is similar? What family is it in?
- Which definitions were used for this concept, and by which experiments?
- Which hypotheses failed, and at which gate?
- Which parameters were unstable, and over what range?
- Which regimes carried the results?
- Which results were in-sample only?
- Which strategies survived out-of-sample testing?
- How many times has this calendar window been used as confirmation or
  holdout?

Agents query this store. They do not substitute for it.

---

## 13. Roles

| Actor | May | May not |
| --- | --- | --- |
| Human researcher | Propose ideas, approve status transitions, decide priorities, perform the orchestration role | Edit stored numerical results |
| Research Agent | Survey evidence, propose definitions and hypotheses, label evidence strength | Assert that an untested idea works |
| Feature Specification Agent | Formalize definitions and propose features and context rules, under a domain profile | Compute feature values or emit signals |
| Adversarial Agent | Interpret the validation verdict, demand further tests | Compute the verdict, or approve on judgement alone |
| Deterministic engine | Compute everything numerical | Interpret |

The Research Agent labels every claim: `ESTABLISHED`, `SUPPORTED`,
`PLAUSIBLE`, `SPECULATIVE`, `UNKNOWN`. Trading folklore is never presented as
empirical fact.

The Orchestrator is deferred; until it exists, the human researcher performs
that role using the registry query CLI (`docs/agent_architecture.md` §2).

---

## 14. Worked example (illustrative, not yet run)

**OF-0001 (candidate).** "In NQ RTH, when price trades into the prior
session's VAH and, within a 60-second window, aggressive buy volume exceeds
the session's 90th-percentile 60s buy volume while net price displacement is
below 2 ticks (defined absorption), the probability of trading 12 ticks lower
before 8 ticks higher within 15 minutes exceeds the location-only baseline by
more than the cost hurdle."

- Falsification: the effect is not distinguishable from the location-only
  baseline after costs at the pre-registered threshold.
- Label horizon: 15 minutes → purge width ≥ 15 minutes at every segment
  boundary.
- Split policy: `CHRONOLOGICAL_BLOCK` for discovery/confirmation, with a
  `CROSS_INSTRUMENT` check on ES as a secondary gate; `TIME_EXTENDING`
  holdout.
- Warm-up: driven by the prior-session profile feature — at least one full
  prior session per segment.
- Confounders: time of day, volatility regime, roll weeks, macro releases.
- Data capability required: trades with `OBSERVED` aggressor side, BBO,
  prior-session profile. MBO not required.
- Costs: commissions + fees per side, one tick spread crossing, explicit
  order latency, feed-delay assumption if `ts_recv` is unavailable,
  conservative slippage.

This is a candidate first experiment, not a claim. It is written here to
demonstrate the required specificity.
