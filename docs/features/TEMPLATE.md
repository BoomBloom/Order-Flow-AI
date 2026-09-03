# Feature: <name>

`feature_id`: `<name>@<version>#<params_hash>`
Family: price | profile | market_profile | vwap | orderflow | liquidity
Status: PROPOSED | IMPLEMENTED | DEPRECATED

## 1. Mathematical definition

State the formula. No prose substitutes. Define every symbol.

## 2. Units and output type

Ticks, contracts, ratio, boolean, enum — and the value range.

## 3. Event / time basis

Which canonical events drive it, the window (event-count, volume, or time),
and the update semantics (on every event, on window close).

## 4. Required data capability

Cross-reference `docs/data_specification.md` §2. If any requirement is
unavailable for the target instrument, this feature is BLOCKED — state the
minimum additional data required. Do not approximate.

## 5. Parameters

| Parameter | Type | Default | Rationale for the default |
| --- | --- | --- | --- |

Defaults are proposals until an experiment justifies them. Note the
sensitivity expected in validation.

## 6. Edge cases

Session start/end, gaps, halts and auctions, thin or empty book, crossed
quotes, roll dates, `aggressor = UNKNOWN`, first N events of a window,
insufficient history.

## 7. Failure modes and interpretation limits

What this feature will report confidently while being wrong. What it does
**not** measure.

## 8. Tests

- Synthetic golden cases with hand-computed expected values
- Property tests (invariants that must always hold)
- Leakage test: `prior_session.*` vs `developing.*` behaviour
- Determinism: byte-identical output across runs
