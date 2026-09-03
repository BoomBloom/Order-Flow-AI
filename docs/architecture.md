# Architecture

Status: **proposed, pre-implementation.** No production code exists yet.
This document defines the layers, boundaries, and technology choices that
implementation must follow. Changes here require updating the dependent
protocol documents in the same commit.

---

## 1. Design forces

The architecture is shaped by five constraints, in priority order:

1. **Causality is structural, not procedural.** Look-ahead bias must be hard
   to introduce, not merely forbidden by review.
2. **One implementation per concept.** A feature computed in research and the
   same feature computed in replay/paper trading must be the same code.
3. **Reproducibility by construction.** Every artifact carries the version of
   the code, config, and data that produced it.
4. **The hot path is deterministic.** `EVENT -> FEATURE -> SIGNAL -> RISK ->
   ORDER` contains no model calls, no network, no agent.
5. **Cheap falsification.** Running an experiment and killing it must be
   fast, or the system will not be used honestly.

---

## 2. Layer model

```
                        ┌──────────────────────────────────────┐
                        │        AGENT / RESEARCH LAYER        │
                        │  (LLM, offline, advisory, typed I/O) │
                        │  Orchestrator · Research · Structure  │
                        │  OrderFlow · Liquidity · Adversarial  │
                        └───────────────┬──────────────────────┘
                                        │ typed specs & critiques
                                        │ (never numbers, never orders)
╔═══════════════════════════════════════▼══════════════════════════════════╗
║                   DETERMINISTIC QUANTITATIVE ENGINE                       ║
║                                                                           ║
║  L0 ACQUISITION      vendor clients, raw capture, checksums               ║
║  L1 DATA QUALITY     completeness, monotonicity, gaps, sequence integrity ║
║  L2 NORMALIZATION    vendor schema -> canonical events                    ║
║  L3 EVENT STORE      immutable canonical partitions + manifest            ║
║  L4 REFERENCE        instruments, calendars, sessions, roll policy        ║
║  L5 FEATURE ENGINE   streaming state machines, versioned, testable        ║
║  L6 MARKET CONTEXT   deterministic regime/context classification          ║
║  L7 STRATEGY         versioned spec + deterministic rule evaluation       ║
║  L8 SIMULATION       event-driven backtester, execution model, accounting ║
║  L9 STATISTICS       metrics, baselines, resampling, inference            ║
║  L10 VALIDATION      splits, walk-forward, stress, robustness             ║
║  L11 REGISTRY        experiments, runs, lineage, research memory          ║
║  L12 PAPER TRADING   same engine, live event source, simulated fills      ║
║  L13 LIVE EXECUTION  NOT BUILT — isolated future layer                    ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dependencies point **downward only**. L5 may not import L7. L8 may not
import L10. The agent layer may read any artifact but may write only to the
registry, and only as proposals and commentary.

---

## 3. Repository layout (target)

```
Order-Flow-AI/
  CLAUDE.md
  README.md
  pyproject.toml
  docs/
    architecture.md            research_protocol.md
    validation_protocol.md     data_specification.md
    agent_architecture.md      roadmap.md
    features/                  # one operational-definition doc per feature family
    experiments/               # OF-XXXX human-readable records
  src/ofa/
    core/          # types, time, money, ids, errors, versioning
    data/
      vendors/     # one adapter per vendor; the only vendor-aware code
      quality/     # validators and quality reports
      normalize/   # vendor -> canonical
      store/       # partitioned event store, manifests, readback
      replay/      # deterministic event replay
    reference/     # instruments, sessions, calendars, roll policy
    features/
      base.py      # Feature protocol, registry, versioning
      price/  profile/  vwap/  orderflow/  liquidity/
    context/       # deterministic market-context classifiers
    strategy/      # spec model, rule evaluation, position/risk rules
    sim/           # event loop, execution model, accounting, ledger
    stats/         # metrics, baselines, resampling
    validation/    # splits, walk-forward, stress, robustness suite
    registry/      # experiments, runs, lineage, research memory
    agents/        # contracts, orchestrator, agent implementations
    cli/           # documented entry points
  tests/
    unit/  property/  golden/  integration/
    fixtures/synthetic/        # clearly labelled, never research data
  data/                        # gitignored
    raw/  canonical/  features/  runs/
```

---

## 4. L0–L3: the data spine

**L0 Acquisition** writes vendor bytes to `data/raw/<vendor>/<dataset>/...`
unmodified, alongside a sidecar manifest (request parameters, retrieval
timestamp, byte count, SHA-256). Raw files are never edited or deleted by
pipeline code.

**L1 Data quality** runs before normalization and produces a machine-readable
quality report per (instrument, date): event counts, sequence-number gaps,
timestamp monotonicity violations, session coverage, book-integrity failures
(crossed/locked, negative depth), and per-check pass/fail. A dataset with a
failing hard check is quarantined, not silently repaired.

**L2 Normalization** converts vendor records into canonical events. This is
the only layer permitted to know vendor field names. It records
`transformation_version` and any inference it performed (for example
aggressor-side inference where the vendor does not supply it).

**L3 Event store** holds immutable canonical partitions
(`instrument / date / event_type`) in Parquet, plus a `manifest.json`
describing provenance per `docs/data_specification.md`. Readback is
deterministic and ordered by `(ts_event, sequence, ingest_index)`.

**Replay** is a first-class capability, not a debugging afterthought: given a
run ID and a timestamp, the system reproduces the exact event sequence that
preceded feature calculation, signal generation, simulated order, and fill.

---

## 5. L4: reference data

Instruments, tick size, tick value, multiplier, currency, expiration, and
activation come from vendor instrument definitions, never from constants
typed by hand.

Sessions are explicit objects, not `if hour > 9` conditions. A `SessionDef`
names its segments (for CME equity index futures: pre-open, Globex overnight,
RTH open, RTH close, settlement) with exchange-local boundaries resolved to
UTC nanoseconds per calendar date, plus a holiday-calendar version.

**Contract roll** is a policy object, not an assumption:

- Research operates on **unadjusted per-contract prices**. Volume profile,
  VWAP, and all price-level features are computed within a single contract.
- A continuous series exists only for cross-contract statistics and carries
  its adjustment method and roll dates explicitly.
- The roll rule (for example: front month until volume in the deferred month
  exceeds the front month for N consecutive sessions) is versioned; changing
  it invalidates dependent feature versions.

---

## 6. L5: feature engine

### Streaming-only contract

Every feature is a state machine:

```python
class Feature(Protocol):
    name: str
    version: str            # semantic; bump on any behavioural change
    params: FeatureParams   # frozen, hashed into the feature id
    requires: DataRequirement  # e.g. TRADES | BBO | MBP_10 | MBO

    def on_event(self, event: CanonicalEvent) -> FeatureUpdate | None: ...
    def snapshot(self) -> FeatureState: ...
```

A feature sees events exactly once, in order, and cannot see the future
because it has never been given the future. There is no vectorized
"research-mode" alternative implementation. Batch feature generation is a
replay of `on_event` over stored events; that is the only mode.

This costs throughput and buys structural causality. Performance work
(vectorized inner loops inside a single feature, compiled kernels) is
permitted only where it provably preserves identical output against golden
tests.

### Feature identity

`feature_id = f"{name}@{version}#{params_hash}"`. Feature outputs are stored
under `data/features/<instrument>/<date>/<feature_id>.parquet` with a
manifest linking dataset version, code revision, and generation timestamp.
Two runs claiming the same `feature_id` must produce byte-identical output;
CI enforces this on golden fixtures.

### Families

- **price / microstructure** — mid, spread, trade price/size, trade
  frequency, trade velocity, realized range, realized volatility
- **volume profile** — volume-at-price, POC, VAH/VAL, HVN/LVN, profile shape
- **market profile** — TPO structure (data permitting), Initial Balance,
  opening range, value migration, acceptance/rejection, balance/imbalance
- **vwap** — session VWAP, anchored VWAP, distance, slope, interaction
- **order flow** — bid/ask volume, delta, delta rate, CVD, footprint
  imbalance, stacked imbalance, absorption, exhaustion, aggression
- **liquidity** — depth, depth imbalance, concentration, withdrawal,
  replenishment, stacking, pulling, sweeps, book pressure, migration

Each family gets an operational-definition document in `docs/features/`
before implementation, following the eight-point checklist in `CLAUDE.md`.

### Point-in-time profile values

Session-derived values (POC, VAH, VAL, IB, session VWAP) exist in two forms
and they are **not interchangeable**:

- `prior_session.*` — final values of a completed session; available from the
  moment that session closes.
- `developing.*` — the value as it stood at time *t* within the current
  session.

Using a completed-session value inside its own session is a leakage bug.
Naming makes the distinction unavoidable; tests assert it.

---

## 7. L6: market context

Context labels (`BALANCED`, `IMBALANCED`, `BREAKOUT_ATTEMPT`, `ACCEPTANCE`,
`REJECTION`, `ROTATION`, `TRENDING`) are produced by deterministic
classifiers over features, with published thresholds and versions. An LLM may
propose a classifier; it may never emit the label at decision time.

---

## 8. L7: strategy representation

A strategy is a versioned spec (YAML, validated into a typed model) plus a
deterministic evaluator. The spec carries market, session, context filter,
location filter, setup, trigger, entry, stop, target, exit, sizing, costs,
slippage model, latency assumption, invalidation, cooldown, and maximum
concurrent positions.

Conceptually:

```
CONTEXT + LOCATION + ORDER-FLOW CONDITION + LIQUIDITY CONDITION
    -> TRIGGER -> EXECUTION RULE -> RISK RULE
```

Rules reference features by `feature_id`. A spec that references an
unregistered feature or an unpinned version fails validation.

---

## 9. L8: simulation

A single-threaded, deterministic event loop consumes canonical events and
drives feature updates, then strategy evaluation, then the execution model.

**Execution model requirements:**

- Decisions are timestamped at the event that produced them.
- An order arrives at the simulated exchange at `decision_ts + latency`,
  where latency is an explicit configured distribution, defaulting to a
  conservative constant.
- Fills consult only events with `ts_event > order_arrival_ts`.
- Market orders cross the book as it exists at arrival, consuming levels and
  paying spread; the resulting slippage is measured, not assumed.
- Limit orders require a queue model. With MBO data, model true queue
  position; with MBP-10, use a conservative rule (fill only after the level
  trades through, or after traded volume at the level exceeds the depth ahead
  at submission). The chosen model is recorded per run.
- Commissions, exchange and clearing fees are per-instrument config.
- Session boundaries, halts, and auction states suspend or flatten per spec.

Accounting is an explicit ledger: orders, fills, positions, realized and
unrealized PnL in ticks and currency, fees, and exposure over time. All PnL
arithmetic is integer-tick based where possible.

---

## 10. L9–L10: statistics and validation

Statistics compute metrics and their sampling behaviour; validation applies
the protocol in `docs/validation_protocol.md`: baselines, discovery/
confirmation separation, purged and embargoed splits, walk-forward,
parameter sensitivity surfaces, regime decomposition, cost and slippage
stress, block bootstrap, and multiple-testing accounting.

Validation is a **library that produces a verdict object**, not a human
judgement recorded in prose. The Adversarial Agent interprets the verdict; it
does not compute it and cannot override it.

---

## 11. L11: registry and research memory

SQLite index (queryable) over immutable on-disk artifacts (auditable), with
human-readable experiment records in `docs/experiments/`.

The registry answers: Have we tested this idea? What is similar? What
definitions were used? What failed and why? Which parameters were unstable?
Which regimes mattered? Which results were in-sample only? What survived?

Research memory is never "the conversation history".

---

## 12. L12: paper trading

Same engine, different event source: a live feed adapter emitting canonical
events into the same replay loop, with simulated fills. Divergence between a
paper session and a replay of the same recorded session is a correctness
alarm, and is the acceptance test for this layer.

---

## 13. Technology choices

| Choice | Rationale | Alternatives rejected |
| --- | --- | --- |
| Python 3.11+ | Research ecosystem, vendor SDKs, team velocity. Hot path is offline, so Python's speed is a throughput cost, not a correctness cost. | Rust/C++: better latency, far slower research iteration. Revisit for specific kernels only. |
| Typed models (pydantic v2) | Versioned schemas for canonical events, strategy specs, and agent contracts; validation at boundaries. | Dataclasses alone: no validation, no schema versioning. |
| Polars + PyArrow | Columnar Parquet I/O, predictable memory on multi-GB event data. | Pandas: heavier memory, weaker typing. Add only if a stats dependency demands it. |
| Parquet on local disk | Immutable, columnar, partitionable, portable. | Databases as the primary store: unnecessary coupling for append-only event data. |
| DuckDB | Ad-hoc SQL over Parquet for research queries without an ETL step. | Custom query code. |
| SQLite (stdlib) | Registry index; single-file, transactional, zero-ops. | Postgres: operational overhead unjustified at this scale. |
| pytest + Hypothesis | Property tests for feature invariants (e.g. CVD is path-consistent; profile mass conserves). | Example-based tests alone. |
| mypy (strict) + ruff | Typing and lint are correctness tools here. | — |
| argparse + a thin CLI module | Documented run commands with no dependency. | Typer/Click: add later only if the CLI grows. |
| Market data vendor: **undecided** | Requires MBP-10 or MBO for CME Globex, plus verified historical depth and cost. Candidates to evaluate: Databento, CME DataMine, and a live-feed vendor for later phases. | Nothing is assumed about vendor capability until verified against their documentation. |

Deferred deliberately: numba/Cython, Rust extensions, workflow orchestrators,
message buses, dashboards, feature-store products, ML frameworks.

---

## 14. Concurrency and determinism

The research pipeline parallelizes **across** partitions (instrument, date),
never **within** an event stream. Any given (instrument, date, feature_id) is
computed by one deterministic single-threaded pass. Random number generation
is seeded per run and the seed is recorded.

---

## 15. Known architectural risks

| Risk | Mitigation |
| --- | --- |
| Streaming-only features are slow over years of MBO data | Partition-parallel batch generation; cache feature outputs; compile only proven-equivalent kernels |
| MBO storage volume for three instruments over multiple years | Start with one instrument and a bounded date range; measure before scaling; keep MBP-10 as the default tier |
| Queue-position modelling error dominates limit-order results | Prefer strategies whose conclusions survive both optimistic and conservative queue models; report both |
| Vendor schema drift | All vendor knowledge confined to L2 adapters; golden tests over stored raw samples |
| Roll handling contaminating profile features | Per-contract research prices; continuous series is opt-in and labelled |
| Researcher degrees of freedom | Discovery/confirmation separation and mandatory multiple-testing accounting |
| Agents drifting into computation | Typed contracts, no numeric fields in agent outputs that deterministic code owns, hot-path boundary enforced in review and CI |
