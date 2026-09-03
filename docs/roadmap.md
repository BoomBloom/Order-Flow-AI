# Implementation Roadmap

Status: **proposed.** Phases are sequential. A phase is not started until the
previous phase meets the Definition of Done in `CLAUDE.md`:

1. Implementation exists. 2. Tests exist. 3. Tests pass. 4. Runnable from a
documented command. 5. Output inspectable. 6. Reproducible. 7. Limitations
documented.

Passing unit tests alone is not sufficient.

---

## Phase 0 — Repository foundation

**Goal:** a repository that can hold serious work.

- `pyproject.toml`, pinned toolchain, `ruff`, `mypy --strict`, `pytest`.
- `src/ofa/core`: typed primitives — UTC-ns time, fixed-point price, tick
  arithmetic, ids, versioning helpers, errors.
- CI: lint, type check, test, and a check that `data/` stays gitignored.
- `docs/features/` and `docs/experiments/` templates.

**Done when:** `make check` (or documented equivalent) passes on a clean
clone, and core primitives have property tests (price/tick round-trips,
timestamp conversions, no float leakage).

**No agents. No features. No strategies.**

---

## Phase 1 — The data spine (one instrument, one source)

**Goal:** prove the smallest real data path end to end.

```
ONE REAL INSTRUMENT -> ONE REAL DATA SOURCE -> INGESTION -> NORMALIZATION
    -> STORAGE -> READBACK -> REPLAY
```

Scope: NQ, one front-month contract, a bounded date range (target ~20
sessions), trades + BBO at minimum, MBP-10 if the chosen vendor tier allows.

- Vendor adapter (the only vendor-aware module), raw capture with checksums
  and sidecar manifests.
- Data quality checks (hard and soft) producing stored reports.
- Normalization into canonical `Trade` / `Quote` / (`BookDelta`) events.
- Partitioned Parquet event store with full manifests.
- Deterministic readback and replay CLI: replay a session, print event
  counts, session coverage, and a window of events around a given timestamp.

**Real data, not synthetic substitutes.** No agents. No features.

**Done when:** `ofa ingest`, `ofa quality`, `ofa normalize`, `ofa replay` all
run from documented commands; replaying the same partition twice produces
byte-identical output; the capability matrix in
`docs/data_specification.md` is filled in with verified yes/no values for the
chosen vendor; limitations are written down.

---

## Phase 2 — Reference data, sessions, calendars, roll

- Instrument registry from vendor definitions.
- Exchange calendar with holidays and early closes; versioned.
- `SessionDef` generation with segment boundaries per trade date.
- Contract roll policy object; per-contract research prices; optional labelled
  continuous series.

**Done when:** sessions for the Phase 1 date range are generated and
inspected against exchange documentation, including at least one early-close
and one roll week.

---

## Phase 3 — Feature engine core + first families

- `Feature` protocol, registry, versioning, `feature_id` hashing.
- Feature runner (replay-driven), feature store with manifests.
- Families: price/microstructure, VWAP (session + anchored), volume profile
  (volume-at-price, POC, VAH/VAL, HVN/LVN).
- `prior_session.*` versus `developing.*` split enforced by tests.
- One operational-definition document per feature in `docs/features/`.

**Done when:** golden synthetic fixtures produce hand-verifiable values;
property tests hold (profile mass conservation, VWAP monotonic in known
constructions); a leakage test suite fails if a completed-session value is
read inside its own session; feature output is byte-reproducible.

---

## Phase 4 — Order flow and liquidity features

- Order flow: bid/ask volume, delta, delta rate, CVD, footprint imbalance,
  stacked imbalance, trade velocity, trade-size behaviour, and formalized
  absorption / exhaustion / aggression definitions.
- Liquidity (requires MBP-10; MBO for queue-level work): depth, depth
  imbalance, concentration, withdrawal, replenishment, stacking, pulling,
  sweeps, book pressure, migration.
- Explicit handling of `aggressor = UNKNOWN` volume.

**Done when:** every implemented concept has an operational-definition doc
with the eight required sections, synthetic golden cases, and a stated
failure-mode list; anything blocked by data capability is documented as
blocked rather than approximated.

---

## Phase 5 — Strategy spec + event-driven backtester

- Strategy spec model and YAML validation; rules bound to pinned
  `feature_id`s.
- Deterministic event loop; latency model; order arrival; fill logic against
  future-only events; market and limit orders; queue models (optimistic and
  conservative).
- Ledger and accounting in integer ticks; commissions and fees per
  instrument; session boundary and halt behaviour.
- Run artifacts: orders, fills, positions, equity curve, and an event-replay
  index for any signal.

**Done when:** a trivial reference strategy on synthetic fixtures produces
hand-computable PnL; a leakage test proves no fill consulted an event at or
before order arrival; two runs of the same config are byte-identical; any
single fill can be replayed with its preceding event window.

---

## Phase 6 — Statistics and validation engine

- Metrics suite (`docs/validation_protocol.md` §4) with bootstrap intervals.
- Baseline generators (unconditional, time-of-day matched, random-entry
  matched, location-only, ablations).
- Split machinery: discovery/confirmation/holdout, purged and embargoed CV,
  walk-forward.
- Stress: cost, slippage, latency, queue model.
- Regime decomposition, parameter surfaces, block bootstrap, Monte Carlo.
- Multiple-testing adjustment; the gated verdict object.

**Done when:** the full gate sequence runs on the Phase 5 reference strategy
and correctly returns `FAILED` for a strategy known to be noise, with the
failure reason naming the right gate.

---

## Phase 7 — Registry, lineage, research memory

- SQLite index + immutable artifacts + `docs/experiments/OF-XXXX.md` records.
- Lineage foreign keys end to end; confirmation/holdout access logging;
  hypothesis-family and variant bookkeeping.
- Query CLI answering the §9 questions in `docs/research_protocol.md`.

**Done when:** every Phase 6 run is registered and a single command traces a
conclusion back to raw bytes and code revision.

---

## Phase 8 — Agent layer

- Typed contracts and schema versioning; agent run logging with token/cost.
- Orchestrator with mandatory registry lookup; conflict reports.
- The five agents, each gated on the deterministic layer it advises.
- Model routing table wired to roles; human-approval checkpoints enforced.

**Done when:** an agent-proposed feature spec compiles into a real feature
module through human review; a schema-invalid output is rejected; agent
outages leave the deterministic pipeline unaffected; a CI check proves no
agent import exists anywhere in the hot path.

---

## Phase 9 — First real experiment: OF-0001

Run the full loop on a real hypothesis (candidate in
`docs/research_protocol.md` §11), through every gate, and publish the record
— including if, and especially if, it fails.

**Done when:** a complete experiment record exists with discovery,
confirmation, robustness, multiple-testing context, verdict, and conclusion,
reproducible from stored config.

---

## Phase 10 — Extension (only after Phase 9)

In order: ES and 6E; additional hypothesis families; the paper-trading
harness (live event source, simulated fills, replay-divergence alarm).

Explicitly **not** in scope until the loop is proven: live execution,
autonomous trading, RL, neural prediction, automated strategy optimizers, GEX
subsystem, dashboards, multi-market optimization, crypto, equities.
