# Order Flow AI

A quantitative **research laboratory** for market structure, order flow,
liquidity, and market microstructure — built to determine whether a trading
hypothesis has statistically defensible out-of-sample edge, and to prove it
wrong when it does not.

This is not a trading bot. Live trading does not exist in this repository and
is not a near-term goal.

## Status

**Phase 0 — repository foundation: COMPLETE.** The seven exit criteria passed
from a clean checkout in [GitHub Actions run 33959395015](https://github.com/BoomBloom/Order-Flow-AI/actions/runs/33959395015)
at revision `e69114d0576b07c61a12cc9356eb116235b3b281`.

What exists today, all under `src/ofa/core/`: exact integer fixed-point prices
with exact-only tick conversion; UTC-nanosecond instants and assigned trading
dates; canonical serialization and stable cross-process content hashing;
identifier, provenance and data-capability primitives; and the `ofa version`
command.

What does not exist: any vendor client, any data, any event store, any
feature, strategy, simulator, validation engine, or agent. There are **no
runtime dependencies** — the core is standard library only. See
[`PLAN.md`](PLAN.md) §2 for delivered milestones and the design gates that
remain deliberately deferred.

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
6. [`docs/agent_architecture.md`](docs/agent_architecture.md) — the three
   active agents, their typed contracts, and why each one exists.
7. [`docs/roadmap.md`](docs/roadmap.md) — phases and per-phase definition of
   done.
8. [`docs/limitations.md`](docs/limitations.md) — the UNVERIFIED register and
   permanent known limitations.

## Development

Python 3.11+. The core has no runtime dependencies; the development extras are
`pytest`, `hypothesis`, `mypy` and `ruff`.

```sh
python -m venv .venv && source .venv/bin/activate
make install-dev          # editable install plus the pinned development toolchain
make check                # ruff + ruff format --check + mypy --strict + pytest
make guards               # the Phase 0 exit-criteria guards on their own
ofa version               # package version, code revision, schema versions
```

`make check` is the gate: it must be green before anything is committed. CI
runs exactly these commands from a fresh checkout.

Every target invokes its tool as `python -m …` rather than as a bare `ruff` or
`mypy` from `PATH`, so the tools always come from the same environment as the
package. A globally installed, isolated `mypy` cannot see `pytest` or
`hypothesis` and will type-check the suite against imports it cannot resolve;
going through the interpreter makes that impossible. Activating the virtualenv
is the whole setup — or target another interpreter explicitly:

```sh
make check PYTHON=/path/to/python
```

The development toolchain is pinned exactly, so a clean checkout installs the
same `ruff`, `mypy`, `pytest` and `hypothesis` that CI uses. The package itself
has no runtime dependencies, and a test fails if one is ever added.

`ofa version` prints deterministic JSON — the package version, the current
code revision with its `CLEAN` / `DIRTY` / `UNKNOWN` state, and every
registered schema version. Outside a Git checkout the revision is reported as
`UNKNOWN` with a null hash; it is never fabricated.

## Scope

- Initial markets: **NQ**, **ES**, **6E** (CME futures).
- Later, only after the core loop is proven: BTC/ETH, US equities, additional
  futures.

## Non-negotiables

- The hot path `EVENT -> FEATURE -> SIGNAL -> RISK -> ORDER` contains no LLM,
  no network call, and no agent.
- Raw data is immutable; derived data is reproducible; nothing is fabricated.
- Every quantity is labelled `OBSERVED`, `RECONSTRUCTED`, `INFERRED`, or
  `SIMULATED`. Fills, slippage, and queue position are always `SIMULATED` and
  are never described as measured.
- Decisions are timestamped at `ts_recv` — when we could have known — never at
  the exchange's `ts_event`.
- Every experiment has a baseline, a falsification test, pre-registered
  thresholds and split policy, and a permanent record — including failures.
- A failed hypothesis is a successful research result.
