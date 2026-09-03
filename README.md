# Order Flow AI

A quantitative **research laboratory** for market structure, order flow,
liquidity, and market microstructure — built to determine whether a trading
hypothesis has statistically defensible out-of-sample edge, and to prove it
wrong when it does not.

This is not a trading bot. Live trading does not exist in this repository and
is not a near-term goal.

## Status

**Initialization phase — architecture only.** No production code yet. The
repository currently contains the design contract that implementation must
follow.

## Read in this order

1. [`CLAUDE.md`](CLAUDE.md) — the operating contract. Read before writing any
   code.
2. [`docs/architecture.md`](docs/architecture.md) — layers, boundaries,
   technology choices.
3. [`docs/data_specification.md`](docs/data_specification.md) — canonical
   schemas, provenance, data capability matrix.
4. [`docs/research_protocol.md`](docs/research_protocol.md) — hypothesis
   lifecycle, experiment records, lineage.
5. [`docs/validation_protocol.md`](docs/validation_protocol.md) — how a
   strategy gets attacked, and what `VALIDATED` requires.
6. [`docs/agent_architecture.md`](docs/agent_architecture.md) — the six
   agents, their typed contracts, and why each one exists.
7. [`docs/roadmap.md`](docs/roadmap.md) — phases and per-phase definition of
   done.

## Scope

- Initial markets: **NQ**, **ES**, **6E** (CME futures).
- Later, only after the core loop is proven: BTC/ETH, US equities, additional
  futures.

## Non-negotiables

- The hot path `EVENT -> FEATURE -> SIGNAL -> RISK -> ORDER` contains no LLM,
  no network call, and no agent.
- Raw data is immutable; derived data is reproducible; nothing is fabricated.
- Every experiment has a baseline, a falsification test, and a permanent
  record — including failures.
- A failed hypothesis is a successful research result.
