# Validation Protocol

Status: **proposed, pre-implementation.**

Authority over: how a strategy is attacked, which tests are mandatory, what
the verdict object contains, and what may be called `VALIDATED`.

The validation engine is deterministic code. The Adversarial Agent reads its
output; it does not produce it. The agent is never rewarded for a positive
result.

---

## 1. Default attitude

Search for reasons the result might be false, not reasons to approve it.
Prefer rejecting a weak strategy over approving a questionable one. Never
change a strategy definition to improve validation performance. Never hide a
failed test.

---

## 2. Pre-registration is a precondition

Validation cannot start unless the experiment record already contains, from
its `FORMALIZED` transition:

- the **split policy** (`docs/research_protocol.md` §4), and
- the **acceptance thresholds** (`docs/research_protocol.md` §5).

The registry refuses the run otherwise `[ENFORCED]`. Thresholds chosen after
seeing results would make every gate below decorative, so this is a hard
precondition rather than a convention.

---

## 3. The ten required questions

Every validation run answers all ten, each backed by a computed result:

1. Did the edge exist outside the discovery segment?
2. Does it survive realistic transaction costs?
3. Does a small parameter change destroy it?
4. Does one regime or one period generate most of the profit?
5. Is the sample size adequate for the claimed effect?
6. Was the hypothesis selected after seeing the data?
7. How many related hypotheses and variants were tested — registered and
   self-reported?
8. Could the result be explained by random variation?
9. Does the effect exist at multiple scales, or only at one arbitrary
   parameter?
10. Is the expected edge economically meaningful after costs?

An unanswered question is a failed validation, not an omission.

---

## 4. Gates

Applied in order. Failing a gate stops the run; later gates are not
attempted.

### Gate 0 — Integrity

- Data quality reports (L1a and L1b) for every consumed partition show no
  open hard failures.
- Every partition's capability record satisfies the declared requirement at
  the declared minimum provenance tier.
- No feature reads a completed-session value inside its own session
  (leakage assertions).
- No module under `features/` imports `labels/` (the separate labelling pass
  delivered in Phase 5; `docs/architecture.md` §6.7).
- The decision clock is `ts_recv`, or `ts_event + assumed_feed_delay_ns` with
  the assumption recorded.
- Every fill consulted only events strictly after order arrival.
- Warm-up was applied at every segment boundary, and its length is at least
  the longest feature `lookback`.
- Purge width is at least the `label_horizon`.
- The run is byte-reproducible from its stored configuration.
- Every referenced feature version, label version, and dataset version is
  pinned.

A Gate 0 failure is an engineering defect, not a research result.

### Gate 1 — Sample adequacy

- Minimum trade count for the claimed effect size, per the pre-registered
  threshold.
- **Effective** sample size after accounting for overlapping and clustered
  events. Signals within a single session are not independent observations;
  the effective count is closer to the number of sessions than the number of
  trades.
- Occurrences distributed across the period, not concentrated in a few
  sessions.
- Power analysis: given the observed variance, could this sample have
  detected the pre-registered effect at all?

### Gate 2 — Baseline separation

The strategy must beat its baselines (`docs/research_protocol.md` §6) by more
than the cost hurdle, in the discovery segment, before confirmation is
touched. Failing here saves the confirmation sample.

### Gate 3 — Confirmation

Evaluation on the untouched confirmation segment(s) with the frozen
definition, using the experiment's pre-registered split scheme. Reported with
the discovery result side by side, including the degradation ratio against
the pre-registered tolerance.

For `COMBINATORIAL_PURGED_CV`, this yields a distribution of out-of-sample
paths rather than a single number; the pre-registered threshold applies to
the distribution's stated statistic, not to a cherry-picked path.

For `CROSS_INSTRUMENT`, the confirmation instrument is named at
`FORMALIZED`. Reporting only the instrument that worked is prohibited.

### Gate 4 — Robustness

All of:

- **Walk-forward** — rolling anchored windows; report per-window results and
  their dispersion, not only the aggregate.
- **Purge and embargo verification** — samples whose label horizon crosses a
  segment boundary are removed; the embargo buffer is applied and recorded.
- **Parameter sensitivity** — evaluate a surface, not a point. The result
  must sit on a plateau, not a spike. Report the fraction of neighbouring
  parameter sets that remain profitable after costs.
- **Cost stress** — 1x, 2x, 3x commissions and fees; report the break-even
  cost multiple.
- **Slippage stress** — from the modelled slippage up to adverse assumptions;
  report the break-even slippage in ticks.
- **Order-latency stress** — sweep the assumed decision-to-exchange latency;
  report the latency at which the edge disappears.
- **Feed-delay stress** — where the decision clock rests on
  `assumed_feed_delay_ns`, sweep it. An edge that dies under a plausible feed
  delay was never an edge; it was look-ahead.
- **Queue-model stress** (limit-order strategies) — optimistic versus
  conservative simulated queue models. A conclusion that survives only the
  optimistic model is not a conclusion.
- **Regime decomposition** — by volatility tercile, trend/balance context,
  time of day, day of week, and calendar year. Report profit concentration:
  what fraction of PnL comes from the top 5% of sessions?
- **Roll-week decomposition** — results with roll sessions included and
  excluded, since roll weeks have different flow characteristics and features
  reset there.
- **Multi-scale check** — does the effect persist across neighbouring
  event/time windows, or only at one arbitrary value?
- **Block bootstrap / Monte Carlo** — stationary block bootstrap using
  **session-level blocks as the default unit**, because intra-session signals
  are dependent. Trade-level blocks may be used only with a stated
  justification. Randomized-entry Monte Carlo for the null distribution.

### Gate 5 — Multiple testing

Adjust for the hypothesis family as defined in `docs/research_protocol.md`
§8.1. Report the family size, the registered parameter-variant count, the
**self-reported discovery search count** (marked `[PROCESS]`), the adjustment
method, and the adjusted result.

A result that survives only unadjusted is `FAILED`, not `PROMISING`.

### Gate 6 — Economic significance

- Expectancy per trade in ticks and currency, net of all costs.
- Expectancy as a multiple of the round-trip cost. A strategy earning a
  fraction of the spread is not tradable.
- **Capacity** — intended size versus typical displayed depth at the entry
  price, and the resulting bound on self-impact bias
  (`docs/architecture.md` §9.4). A strategy whose size is material relative
  to displayed depth has results biased optimistically by an amount the
  backtest cannot measure.
- Opportunity: trades per month, exposure, turnover.
- Drawdown and recovery characteristics at the intended sizing.

### Gate 7 — Holdout

Evaluation on the experiment's declared holdout. Under `FIXED`, this is a
single evaluation and the window is spent for the lineage. Under
`TIME_EXTENDING`, the run records the exact calendar window consumed, and
subsequent evaluations of the same lineage may only use windows arriving
after it.

---

## 5. Metrics

Reported for every run, with bootstrap confidence intervals (session-block
resampled) where meaningful:

**Return:** expectancy (ticks, currency, R), average win, average loss,
profit factor, total net PnL, PnL after each cost scenario.

**Risk-adjusted:** Sharpe-like ratio on the appropriate sampling frequency,
with its limitations stated; Sortino; return over maximum drawdown.

**Distribution:** full payoff distribution, skew, kurtosis, worst 1% of
trades, maximum adverse excursion and maximum favourable excursion
distributions.

**Path:** maximum drawdown, drawdown duration, longest losing streak, equity
curve stability across periods (per-year, per-quarter breakdown).

**Activity:** trade count, effective sample size, trades per session, time in
market, turnover, average holding time.

**Execution (all `SIMULATED`):** fill rate, simulated slippage against the
modelled assumption, share of PnL attributable to the slippage assumption,
fill-rate difference between optimistic and conservative queue models.
None of these are described as measured.

Win rate may be reported but never as the headline and never alone.

---

## 6. Verdict object

Validation emits a structured, stored object — not prose:

```json
{
  "run_id": "...", "experiment_id": "OF-0001",
  "strategy_version": "...", "dataset_version": "...",
  "split_policy": {"scheme": "CHRONOLOGICAL_BLOCK", "purge_ns": "...",
                   "embargo_ns": "...", "warm_up": "...",
                   "holdout_policy": "TIME_EXTENDING"},
  "thresholds_registered_at": "FORMALIZED@2026-01-14T...",
  "decision_clock": {"source": "ts_recv"},
  "gates": [{"gate": "G0_INTEGRITY", "passed": true, "checks": [...]}],
  "verdict": "FAILED | INSUFFICIENT_EVIDENCE | PROMISING | VALIDATED",
  "primary_failure_reason": "...",
  "metrics": {...},
  "robustness": {"break_even_cost_multiple": 1.4,
                 "break_even_slippage_ticks": 0.3,
                 "order_latency_breakpoint_ns": "...",
                 "feed_delay_breakpoint_ns": "...",
                 "parameter_plateau_fraction": 0.22,
                 "top5pct_session_pnl_share": 0.61,
                 "queue_model_fill_rate_delta": 0.31},
  "multiple_testing": {"family_size": 14, "registered_variants": 96,
                       "self_reported_discovery_variants": 40,
                       "adjustment": "...", "adjusted_result": "..."},
  "capability": {"partitions_checked": 412, "min_tier_satisfied": true},
  "evidence_against": ["..."], "evidence_for": ["..."],
  "remaining_uncertainty": ["..."],
  "required_next_experiment": "..."
}
```

The verdict is computed from the pre-registered thresholds. An agent may add
commentary in a separate field; it may not change `verdict`.

---

## 7. What `VALIDATED` requires

All of:

- Gates 0–7 passed.
- The confirmation result is in the same direction as discovery and does not
  degrade beyond the pre-registered tolerance.
- Positive expectancy at 2x modelled costs.
- Positive expectancy under the **conservative** simulated queue model, for
  limit-order strategies.
- Survives the feed-delay stress where the decision clock is assumption-based.
- No single regime, year, or session decile carries the result (profit
  concentration below the pre-registered threshold).
- The parameter neighbourhood is a plateau.
- Survives multiple-testing adjustment for its family.
- Holdout consistent with confirmation.

Anything short of this is `PROMISING` at best, and `PROMISING` only ever
means "worth another, differently designed experiment".

`VALIDATED` still does not mean profitable in the future. It means the
historical evidence survived a serious attempt to destroy it, under stated
assumptions that include an unmeasurable self-impact bias in our favour.

---

## 8. Common failure modes this protocol targets

Look-ahead from using `ts_event` as a decision clock; look-ahead in
completed-session statistics; labels leaking into features; feature state
carried across a split boundary without burn-in; overlapping-sample and
intra-session inflation of significance; parameter mining presented as a
single test; a location effect mislabelled as an order-flow effect; results
carried by one volatility regime or one year; edges smaller than the spread;
optimistic simulated queue fills; unmodelled self-impact; roll-period
artifacts; contract, period, and instrument selection bias; and the same
holdout window reused across lineages until something passes.
