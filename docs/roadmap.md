# Implementation Roadmap

Status: **Phase 0 complete; later phases proposed.** Phases are sequential. A
phase is not started until the previous phase meets the Definition of Done in
`CLAUDE.md`:

1. Implementation exists. 2. Tests exist. 3. Tests pass. 4. Runnable from a
documented command. 5. Output inspectable. 6. Reproducible. 7. Limitations
documented.

Passing unit tests alone is not sufficient.

---

## Phase 0 — Repository foundation

**Goal:** a repository that can hold serious work. Nothing that touches data,
features, strategies, simulation, or agents.

### In scope — exact

- `pyproject.toml`, pinned toolchain, `ruff`, `mypy --strict`, `pytest`, CI.
- `src/ofa/core/`: UTC-nanosecond time primitives; integer fixed-point price
  with exact-only tick-grid conversion; id and run-id primitives; **stable**
  content hashing for `params_hash`; error types; manifest primitives — the
  dependency-free capability record and provenance types only, the full
  dataset manifest being deferred to Phase 1 (`docs/limitations.md` §5, D5);
  the provenance-tier enum (`OBSERVED`, `RECONSTRUCTED`, `INFERRED`,
  `SIMULATED`); the `DataRequirement` enum.
- **Protocol declarations — DEFERRED by accepted scope amendment.**
  `CanonicalEvent` and `Feature` (`on_event` / `on_gap` / `on_reset` /
  `snapshot`, plus `requires`, `lookback`, `roll_policy`) are **not** declared
  in Phase 0. The `Feature` signature names `FeatureParams`, `Lookback`,
  `StreamGap`, `FeatureUpdate` and `FeatureState`, none of which this
  specification defines beyond the name, and `Lookback` carries an unresolved
  conflict between event-count, volume, time and session windows against the
  requirement that warm-up be "at least the longest lookback". The
  `CanonicalEvent` envelope's typing trades directly against §16 item 1's ban
  on per-event validation. The event gate closes in Phase 1B; the Feature /
  Lookback gate closes before Phase 3;
  both are recorded in `docs/limitations.md` §5, D3 and D4.
- `docs/limitations.md` kept current as the UNVERIFIED register.

### Out of scope — exact

Every vendor client; any data download; the event store; replay; reference
data; any feature; any label; strategy; simulator; statistics; validation;
registry; any agent; and any CLI command beyond `ofa version`. **No
market-data SDK may appear in `pyproject.toml` at Phase 0.**

### Exit criteria — exact

1. `make check` (ruff + `mypy --strict` + pytest) is green on a clean clone
   and is documented in the README.
2. Property tests hold: price↔tick round-trips exactly; a price off the tick
   grid raises rather than rounds; UTC-ns conversions round-trip; no float
   appears in any price-typed path.
3. `params_hash` is byte-identical across two **separate interpreter
   processes** — this specifically catches Python's salted `hash()`, which
   would silently break `feature_id` reproducibility forever.
4. `ofa version` prints the code revision and every schema version.
5. Two independent generations of the Phase 0 artifact, in separate
   interpreter processes under different hash seeds, are byte-identical.
6. CI asserts `data/` is gitignored and that no market-data SDK is in the
   dependency set.
7. `docs/limitations.md` carries the current UNVERIFIED register.

**No agents. No features. No strategies. No data.**

---

## Phase 1 — The data spine (one instrument, one source)

**Goal:** prove the smallest real data path end to end.

```
ONE REAL INSTRUMENT -> ONE REAL DATA SOURCE -> INGESTION -> NORMALIZATION
    -> STORAGE -> READBACK -> REPLAY
```

Scope: NQ, one front-month contract, a bounded date range (target ~20
sessions), trades + BBO at minimum, MBP-10 if the chosen vendor tier allows.

### Sequential gates within Phase 1

Phase 0 must pass before 1A. Each following gate requires its predecessor's
exit evidence. The user-approved planning reconciliation preserves repository
phase numbers; master-roadmap Phases 1–4 map to 1A–1D below.

| Gate | Work | Exit evidence before proceeding |
| --- | --- | --- |
| 1A — Vendor evidence and decision | Review primary-source capabilities, reference findings, entitlement questions and sample plan. No production adapter. | User-approved source/tier and permitted sample access; source-field and entitlement questions from V1–V6 resolved for the intended scope with documentation and sample evidence. Canonical mapping remains in 1B. An optional capability may be verified absent; unknown required source capabilities block. |
| 1B — Event and prerequisite design | Resolve D4 before any canonical implementation; review clock capture point, sequence domains, snapshots, missing values, serialization and schema evolution. Design the bounded instrument/session/calendar prerequisite. | Reviewed event decision record and independently tested contract; verified instrument identity, tick grid and L4 calendar assignment for the selected contract/date range. Any locked-semantic change requires explicit approval. |
| 1C — Acquisition and normalization | Implement approved-source raw acquisition, L1a, normalization and L1b. Resolve D5/D6 and X2 before dependent metadata is written. | Raw checksums, versioned transformations, per-field provenance, quality reports and rejection fixtures; approved dependencies; real bounded data inspected. |
| 1D — Store, readback and replay | Implement canonical partitions, complete manifests and offline deterministic replay. | All original Phase 1 exit criteria below, including byte-identical replay, capability checks and green CI. |

V2/V6 remain open until both source evidence in 1A and canonical timing/ordering
decisions in 1B are complete; 1A does not require a future canonical schema.

The bounded prerequisite in 1B uses the existing instrument-registry and L4
calendar ownership; it is not a second calendar or a timestamp-truncation
fallback. Verify every session used by Phase 1, including any boundary or
exception in the selected range. Missing reference evidence blocks dependent
normalization. Phase 2 extends this same implementation to its full holiday,
early-close and roll acceptance coverage. This explicitly moves the necessary
prerequisite slice ahead of its consumers without starting full Phase 2 early.

Planning and open choices are recorded in [phase1_plan.md](phase1_plan.md).
Neither public research nor this plan closes 1A, selects a vendor, or declares
the final event/Feature contracts.

### Data-spine implementation scope (after the gates permit it)

- Vendor adapter (the only vendor-aware module), raw capture with checksums
  and sidecar manifests.
- **L1a** raw structural quality checks; **L1b** post-normalization semantic
  checks; both producing stored reports.
- Normalization into canonical `Trade` / `Quote` / (`BookDelta`) events with
  per-field provenance tiers.
- Partitioned Parquet event store keyed on **`trade_date`**, with full
  manifests including the **per-partition capability record**.
- Deterministic readback and replay CLI, with capability assertion at read.

**Real data, not synthetic substitutes.** No agents. No features.

**Done when:** `ofa ingest`, `ofa quality`, `ofa normalize`, `ofa replay` run
from documented commands; replaying the same partition twice produces
byte-identical output; the capability matrix in
`docs/data_specification.md` §4 is filled in with verified values, verifier,
date, and vendor-doc version for the chosen vendor — including **whether
`ts_recv` is supplied**; limitations are recorded.

---

## Phase 2 — Reference data, sessions, calendars, roll

Prerequisite: Phase 1 exit. Extend the bounded instrument/calendar foundation
delivered in 1B; retain one registry and one L4 calendar implementation.

- Instrument registry from vendor definitions.
- Exchange calendar with holidays and early closes; versioned.
- `SessionDef` generation and `trade_date` assignment per instrument. The
  equity-index segmentation is not assumed to hold for 6E.
- Contract roll policy object; per-contract research prices; optional
  labelled continuous series.

**Done when:** sessions and `trade_date` assignments for the Phase 1 range
are generated and checked against exchange documentation, including at least
one early-close day, one holiday, and one roll week.

---

## Phase 3 — Feature engine core + first families

- `Feature` protocol implementation, registry, versioning, `feature_id`
  hashing, capability-scoped event iterators, gap/reset handling, roll policy.
- Feature runner (replay-driven), feature store with manifests.
- Families: price/microstructure, VWAP (session + anchored), volume profile.
- `prior_session.*` versus `developing.*` split enforced by tests.
- One operational-definition document per feature in `docs/features/`.

**Done when:** golden synthetic fixtures produce hand-verifiable values;
property tests hold; a leakage suite fails if a completed-session value is
read inside its own session; consuming an undeclared event type raises; a
roll triggers the declared policy; feature output is byte-reproducible.

---

## Phase 4 — Order flow and liquidity features

- Order flow: bid/ask volume, delta, delta rate, CVD, footprint imbalance,
  stacked imbalance, trade velocity, trade-size behaviour, and formalized
  absorption / exhaustion / aggression definitions.
- Liquidity (requires MBP-10; MBO for queue-level work): depth, depth
  imbalance, concentration, withdrawal, replenishment, stacking, pulling,
  sweeps, book pressure, migration.
- Explicit handling of `UNKNOWN` and `INFERRED` aggressor volume.

**Done when:** every implemented concept has an operational-definition doc
with the eight required sections, synthetic golden cases, and a stated
failure-mode list; anything blocked by data capability is documented as
blocked rather than approximated.

---

## Phase 5 — Labels, strategy spec, event-driven backtester

- `src/ofa/labels/` as a separate pass with `label_horizon`; CI import check
  that `features/` never imports it.
- Strategy spec model and YAML validation; rules bound to pinned
  `feature_id`s.
- Deterministic event loop with the **`ts_recv` decision clock** (or
  `ts_event + assumed_feed_delay_ns`, recorded); order latency; fill logic
  against future-only events; market and limit orders; simulated queue models
  (optimistic and conservative) with explicit cancel/replace, partial-fill,
  priority-loss, and same-timestamp semantics.
- Ledger and accounting in integer ticks; commissions and fees per
  instrument; session boundary and halt behaviour.
- Run artifacts: orders, fills, positions, equity curve, event-replay index.

**Done when:** a trivial reference strategy on synthetic fixtures produces
hand-computable PnL; a leakage test proves no fill consulted an event at or
before order arrival; a clock test proves no decision was taken before
`ts_recv`; two runs of the same config are byte-identical; any single fill
can be replayed with its preceding event window; every execution artifact is
labelled `SIMULATED`.

---

## Phase 6 — Statistics and validation engine

- Metrics suite with session-block bootstrap intervals.
- Baseline generators (unconditional, time-of-day matched, random-entry
  matched, location-only, ablations).
- **Split policy engine**: chronological block, interleaved block, purged
  k-fold, combinatorial purged CV, cross-instrument, hybrid — with
  label-horizon purging, embargo, per-segment warm-up, and fixed or
  time-extending holdout.
- Stress: cost, slippage, order latency, feed delay, queue model.
- Regime and roll-week decomposition, parameter surfaces, block bootstrap,
  Monte Carlo.
- Multiple-testing adjustment; the gated verdict object.

**Done when:** the full gate sequence runs on the Phase 5 reference strategy
and correctly returns `FAILED` for a strategy known to be noise, naming the
right gate; and a run whose experiment lacks pre-registered thresholds or a
split policy is refused.

---

## Phase 7 — Registry, lineage, research memory

- SQLite index + immutable artifacts + `docs/experiments/OF-XXXX.md` records.
- Lineage foreign keys end to end; confirmation/holdout access logging by
  calendar window; hypothesis-family assignment; registered variant counts
  and the self-reported discovery search log.
- Threshold and split-policy pre-registration enforcement.
- Query CLI answering the questions in `docs/research_protocol.md` §12 —
  this is also the tool that stands in for the deferred Orchestrator.

**Done when:** every Phase 6 run is registered and a single command traces a
conclusion back to raw bytes, capability record, and code revision.

---

## Phase 8 — Agent layer

- Typed contracts and schema versioning; agent run logging with profile
  version, token usage, and cost.
- **Three agents:** Research, Feature Specification (profiles
  `market_structure`, `order_flow`, `liquidity`), Adversarial.
- Model routing table wired to roles; human-approval checkpoints enforced;
  human performs the orchestration workflow.

**Done when:** an agent-proposed feature spec compiles into a real feature
module through human review; a schema-invalid output is rejected; agent
outages leave the deterministic pipeline unaffected; a CI check proves no
agent import exists anywhere in the hot path.

---

## Phase 9 — First real experiment: OF-0001

Run the full loop on a real hypothesis (candidate in
`docs/research_protocol.md` §14), through every gate, and publish the record
— including if, and especially if, it fails.

**Done when:** a complete experiment record exists with pre-registered
thresholds and split policy, discovery, confirmation, robustness,
multiple-testing context, verdict, and conclusion, reproducible from stored
config.

---

## Phase 10 — Extension (only after Phase 9)

In order: ES and 6E (with 6E's session structure verified, not assumed);
additional hypothesis families; the paper-trading harness (live event source,
simulated fills, historical/live capability compatibility check, replay-
divergence alarm).

**Orchestrator agent:** considered here at the earliest, and only if the
deferral conditions in `docs/agent_architecture.md` §2.2 are met — the loop is
operational, manual orchestration is demonstrably a bottleneck, and a written
comparison shows what it adds over the human workflow plus the registry CLI.

Explicitly **not** in scope until the loop is proven: live execution,
autonomous trading, RL, neural prediction, automated strategy optimizers, GEX
subsystem, dashboards, multi-market optimization, crypto, equities.
