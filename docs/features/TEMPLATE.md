# Feature: <name>

`feature_id`: `<name>@<version>#<params_hash>`
Family: price | profile | market_profile | vwap | orderflow | liquidity
Status: PROPOSED | IMPLEMENTED | BLOCKED | DEPRECATED
Proposed by: human | Feature Specification Agent (`<profile>@<version>`)

## 1. Mathematical definition

State the formula. No prose substitutes. Define every symbol.

## 2. Units and output type

Ticks, contracts, ratio, boolean, enum — and the value range.

## 3. Event / time basis

Which canonical events drive it (`requires`), the window (event-count,
volume, or time), `lookback` (longest history needed — this drives split
warm-up), and update semantics (on every event, on window close).

## 4. Required data capability and provenance tier

Cross-reference `docs/data_specification.md` §3–4. State the **minimum
acceptable provenance tier** for each input — e.g. aggressor side
`OBSERVED` only, or `INFERRED` acceptable with the error reported.

If any requirement is unavailable for the target instrument, this feature is
**BLOCKED** — state the minimum additional data required. Do not approximate.

## 5. Parameters

| Parameter | Type | Default | Rationale for the default |
| --- | --- | --- | --- |

Defaults are proposals until an experiment justifies them. Note the
sensitivity expected in validation.

## 6. Gap, reset, and roll behaviour

- `on_gap(StreamGap)` — does state remain valid, degrade, or invalidate?
  How long until warm again?
- `on_reset(reason)` — behaviour for `SESSION_START`, `CONTRACT_ROLL`,
  `SPLIT_SEGMENT_START`, `HALT_RESUME`, `LIVE_RECONNECT`.
- `roll_policy` — `RESET` | `CARRY` | `CARRY_ADJUSTED`, with justification.
  Price-level state must be `RESET`.

## 7. Other edge cases

Session start/end, gaps in trading, halts and auctions, thin or empty book,
crossed quotes, `aggressor = UNKNOWN` (and how excluded volume is reported),
first N events of a window, insufficient history.

## 8. Failure modes and interpretation limits

What this feature will report confidently while being wrong. What it does
**not** measure. Competing definitions in common use that this one rejects,
and why.

## 9. Tests

- Synthetic golden cases with hand-computed expected values
- Property tests (invariants that must always hold)
- Leakage test: `prior_session.*` vs `developing.*` behaviour
- Capability test: consuming an undeclared event type raises
- Gap/reset/roll behaviour tests
- Determinism: byte-identical output across runs and across processes
