# OF-XXXX — <title>

Status: IDEA | FORMALIZED | IN_DEVELOPMENT | BACKTESTED | FAILED | PROMISING |
REQUIRES_VALIDATION | VALIDATED | PAPER_TRADING | RETIRED

Derived from: `<OF-XXXX or none>` · Related: `<...>` ·
Hypothesis family: `<family id>`

## Hypothesis specification

1. Hypothesis statement
2. Proposed mechanism
3. Operational definitions
4. Required features (`feature_id` with version)
5. Required data capability **and minimum provenance tier** per input
6. Context (market, session, regime filter)
7. Event definition
8. Label definition and `label_horizon`
9. Entry / exit / invalidation
10. Expected effect (direction, magnitude, horizon) — **stated before running**
11. Baseline / null comparison
12. Falsification test
13. Cost, slippage, order-latency, feed-delay, and queue-model assumptions
14. Sampling method and expected sample size
15. Known confounders
16. Selection-bias disclosure (see below)

## Split policy — pre-registered at FORMALIZED

| Field | Value |
| --- | --- |
| `scheme` | CHRONOLOGICAL_BLOCK / INTERLEAVED_BLOCK / PURGED_KFOLD / COMBINATORIAL_PURGED_CV / CROSS_INSTRUMENT / HYBRID |
| `segments` | |
| `purge` (≥ `label_horizon`) | |
| `embargo` | |
| `warm_up` (≥ longest feature `lookback`) | |
| `boundary_rule` | |
| `holdout_policy` | FIXED / TIME_EXTENDING |
| `rationale` | |

## Acceptance thresholds — pre-registered at FORMALIZED

The registry refuses a validation run if these are absent `[ENFORCED]`.

| Threshold | Value |
| --- | --- |
| Minimum trade count / effective sample size | |
| Minimum net expectancy (ticks; × round-trip cost) | |
| Maximum discovery→confirmation degradation | |
| Maximum profit concentration (top-5% session PnL share) | |
| Minimum parameter-plateau fraction | |
| Minimum break-even cost multiple | |
| Minimum break-even slippage (ticks) | |
| Multiple-testing adjustment method and adjusted threshold | |

## Data and versions

Dataset ID and version · `trade_date` range · segment boundaries · capability
records consumed (and provenance tiers) · decision clock (`ts_recv` or
assumed feed delay) · feature versions · label version · strategy spec
version · code revision.

## Parameters

Values and exactly how they were chosen. Which segment was used to choose
them.

## Results

Discovery (run IDs) · Confirmation (run IDs, access log) · Robustness ·
Holdout (calendar window consumed).

Numbers in this section are written by deterministic code only. All execution
quantities are `SIMULATED`.

## Multiple-testing context

Hypothesis family and why this experiment belongs to it · family size ·
registered parameter variants · selection criterion · related failed
experiments · confirmation/holdout accesses by calendar window.

### Discovery search log `[PROCESS — self-reported]`

- Approximate variants / thresholds / windows explored during discovery
- Features and locations tried and abandoned
- Criterion by which this variant was selected for formalization
- Was the hypothesis formed before or after looking at the data?

## Selection-bias disclosure `[PROCESS]`

- **Contract selection** — roll sessions included, flagged, or excluded?
- **Period selection** — range, and why it starts and ends where it does
- **Instrument selection** — tried on other instruments first? what happened?

## Verdict

Verdict object reference · primary failure reason (if any).

## Interpretation

Attributed prose. Human or named agent (with profile and version). Clearly
separated from computed results.

## Limitations

Include the applicable permanent limitations from `docs/limitations.md`
(self-impact bias, simulated queue position, feed-delay assumption, inferred
aggressor share).

## Status history

| Timestamp | From | To | Actor | Justifying run |
| --- | --- | --- | --- | --- |
