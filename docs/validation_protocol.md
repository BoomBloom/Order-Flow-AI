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

## 2. The ten required questions

Every validation run answers all ten, each backed by a computed result:

1. Did the edge exist outside the discovery period?
2. Does it survive realistic transaction costs?
3. Does a small parameter change destroy it?
4. Does one regime or one period generate most of the profit?
5. Is the sample size adequate for the claimed effect?
6. Was the hypothesis selected after seeing the data?
7. How many related hypotheses and variants were tested?
8. Could the result be explained by random variation?
9. Does the effect exist at multiple scales, or only at one arbitrary
   parameter?
10. Is the expected edge economically meaningful after costs?

An unanswered question is a failed validation, not an omission.

---

## 3. Gates

Applied in order. Failing a gate stops the run; later gates are not
attempted.

### Gate 0 — Integrity

- Data quality reports for every consumed partition show no open hard
  failures.
- No feature reads a completed-session value inside its own session
  (leakage assertions).
- Every fill consulted only events strictly after order arrival.
- The run is byte-reproducible from its stored configuration.
- Every referenced feature version and dataset version is pinned.

A Gate 0 failure is an engineering defect, not a research result.

### Gate 1 — Sample adequacy

- Minimum trade count for the claimed effect size, pre-registered.
- Effective sample size after accounting for overlapping/clustered events.
- Occurrences distributed across the period, not concentrated in a few
  sessions.
- Power analysis: given the observed variance, could this sample have
  detected the pre-registered effect at all?

### Gate 2 — Baseline separation

The strategy must beat its baselines (`docs/research_protocol.md` §5) by more
than the cost hurdle, in the discovery sample, before confirmation is
touched. Failing here saves the confirmation sample.

### Gate 3 — Confirmation

One evaluation on the untouched confirmation sample with the frozen
definition. Reported with the discovery result side by side, including the
degradation ratio.

### Gate 4 — Robustness

All of:

- **Walk-forward** — rolling anchored windows; report per-window results and
  their dispersion, not only the aggregate.
- **Purged and embargoed splits** — remove training samples whose label
  horizon overlaps test data; embargo a buffer after each test window.
- **Parameter sensitivity** — evaluate a surface, not a point. The result
  must sit on a plateau, not a spike. Report the fraction of neighbouring
  parameter sets that remain profitable after costs.
- **Cost stress** — 1x, 2x, 3x commissions and fees; report the break-even
  cost multiple.
- **Slippage stress** — from the modelled slippage up to adverse assumptions;
  report the break-even slippage in ticks.
- **Latency stress** — sweep the assumed decision-to-exchange latency;
  report the latency at which the edge disappears.
- **Queue-model stress** (limit-order strategies) — optimistic versus
  conservative fill assumptions; a conclusion that only survives the
  optimistic model is not a conclusion.
- **Regime decomposition** — by volatility tercile, trend/balance context,
  time of day, day of week, and calendar year. Report profit concentration:
  what fraction of PnL comes from the top 5% of sessions?
- **Multi-scale check** — does the effect persist across neighbouring
  event/time windows, or only at one arbitrary value?
- **Block bootstrap / Monte Carlo** — stationary block bootstrap over trade
  sequences and over event-time blocks to get sampling distributions for
  expectancy, profit factor, and drawdown. Randomized-entry Monte Carlo for
  the null distribution.

### Gate 5 — Multiple testing

Adjust for the hypothesis family recorded in the registry. Report the family
size, the number of parameter variants, the adjustment method (e.g.
Benjamini–Hochberg for a family of related hypotheses, and a deflated
performance statistic for parameter searches), and the adjusted result.

A result that survives only unadjusted is `FAILED`, not `PROMISING`.

### Gate 6 — Economic significance

- Expectancy per trade in ticks and currency, net of all costs.
- Expectancy as a multiple of the round-trip cost. A strategy earning a
  fraction of the spread is not tradable.
- Capacity: typical size at the entry price level versus intended size, and
  the market-impact assumption.
- Opportunity: trades per month, exposure, turnover.
- Drawdown and recovery characteristics at the intended sizing.

### Gate 7 — Holdout

Single evaluation on the most recent reserved period. Once used for a
lineage, it is spent.

---

## 4. Metrics

Reported for every run, with bootstrap confidence intervals where meaningful:

**Return:** expectancy (ticks, currency, R), average win, average loss,
profit factor, total net PnL, PnL after each cost scenario.

**Risk-adjusted:** Sharpe-like ratio on the appropriate sampling frequency,
with its limitations stated; Sortino; return over maximum drawdown.

**Distribution:** full payoff distribution, skew, kurtosis, worst 1% of
trades, maximum adverse excursion and maximum favourable excursion
distributions.

**Path:** maximum drawdown, drawdown duration, longest losing streak, equity
curve stability across periods (per-year, per-quarter breakdown).

**Activity:** trade count, trades per session, time in market, turnover,
average holding time.

**Execution:** fill rate, realized versus modelled slippage, share of PnL
attributable to the slippage assumption.

Win rate may be reported but never as the headline and never alone.

---

## 5. Verdict object

Validation emits a structured, stored object — not prose:

```json
{
  "run_id": "...", "experiment_id": "OF-0001",
  "strategy_version": "...", "dataset_version": "...",
  "gates": [{"gate": "G0_INTEGRITY", "passed": true, "checks": [...]}],
  "verdict": "FAILED | INSUFFICIENT_EVIDENCE | PROMISING | VALIDATED",
  "primary_failure_reason": "...",
  "metrics": {...},
  "robustness": {"break_even_cost_multiple": 1.4,
                 "break_even_slippage_ticks": 0.3,
                 "parameter_plateau_fraction": 0.22,
                 "top5pct_session_pnl_share": 0.61},
  "multiple_testing": {"family_size": 14, "variants": 96,
                       "adjustment": "...", "adjusted_result": "..."},
  "evidence_against": ["..."], "evidence_for": ["..."],
  "remaining_uncertainty": ["..."],
  "required_next_experiment": "..."
}
```

The verdict is computed from pre-registered thresholds. An agent may add
commentary in a separate field; it may not change `verdict`.

---

## 6. What `VALIDATED` requires

All of:

- Gates 0–7 passed.
- The confirmation result is in the same direction as discovery and does not
  degrade beyond the pre-registered tolerance.
- Positive expectancy at 2x modelled costs.
- Positive expectancy under the conservative queue model, for limit-order
  strategies.
- No single regime, year, or session decile carries the result (profit
  concentration below the pre-registered threshold).
- The parameter neighbourhood is a plateau.
- Survives multiple-testing adjustment for its family.
- Holdout consistent with confirmation.

Anything short of this is `PROMISING` at best, and `PROMISING` only ever
means "worth another, differently designed experiment".

`VALIDATED` still does not mean profitable in the future. It means the
historical evidence survived a serious attempt to destroy it.

---

## 7. Common failure modes this protocol targets

Look-ahead in session statistics; overlapping-sample inflation of
significance; parameter mining presented as a single test; a location effect
mislabelled as an order-flow effect; results carried by one volatility
regime or one year; edges smaller than the spread; optimistic limit-order
fills; roll-period artifacts; survivorship in instrument or period selection;
the same holdout period reused across dozens of lineages until something
passes.
