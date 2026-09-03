# Architecture

Status: **proposed, pre-implementation.** No production code exists yet.
This document defines the layers, boundaries, and technology choices that
implementation must follow. Changes here require updating the dependent
protocol documents in the same commit.

Decisions that are expensive to reverse are enumerated in §16. Everything not
listed there is intended to be cheap to change.

---

## 1. Design forces

The architecture is shaped by five constraints, in priority order:

1. **Causality is structural, not procedural.** Look-ahead bias must be hard
   to introduce, not merely forbidden by review.
2. **One implementation per concept.** A feature computed in research and the
   same feature computed in replay/paper trading must be the same code — not
   an equivalent one.
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
                        │  Research · Feature Specification    │
                        │  Adversarial                         │
                        │  (Orchestrator: DEFERRED)            │
                        └───────────────┬──────────────────────┘
                                        │ typed specs & critiques
                                        │ (never numbers, never orders)
╔═══════════════════════════════════════▼══════════════════════════════════╗
║                   DETERMINISTIC QUANTITATIVE ENGINE                       ║
║                                                                           ║
║  L0  ACQUISITION      vendor clients, raw capture, checksums              ║
║  L1a RAW QUALITY      file integrity, sequence gaps, monotonicity,        ║
║                       coverage — operates on vendor records               ║
║  L2  NORMALIZATION    vendor schema -> canonical events                   ║
║  L1b SEMANTIC QUALITY book integrity, crossed/locked quotes, aggressor    ║
║                       coverage — operates on canonical events             ║
║  L3  EVENT STORE      immutable canonical partitions + manifest           ║
║  L4  REFERENCE        instruments, calendars, sessions, roll policy       ║
║  L5  FEATURE ENGINE   streaming state machines, versioned, testable       ║
║  L6  MARKET CONTEXT   deterministic regime/context classification         ║
║  L7  STRATEGY         versioned spec + deterministic rule evaluation      ║
║  L8  SIMULATION       event-driven backtester, execution model, accounting║
║  L9  STATISTICS       metrics, baselines, resampling, inference           ║
║  L10 VALIDATION       splits, walk-forward, stress, robustness            ║
║  L11 REGISTRY         experiments, runs, lineage, research memory         ║
║  L12 PAPER TRADING    same engine, live event source, simulated fills     ║
║  L13 LIVE EXECUTION   NOT BUILT — isolated future layer                   ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Quality is deliberately split across the normalization boundary: L1a can only
see vendor records, L1b can only see canonical events. A check that needs a
rebuilt book belongs in L1b, and a check that needs raw file structure
belongs in L1a. Neither may reach across.

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
    limitations.md
    features/                  # one operational-definition doc per feature
    experiments/               # OF-XXXX human-readable records
  src/ofa/
    core/          # types, time, price/tick, ids, errors, versioning, provenance
    data/
      vendors/     # one adapter per vendor; the only vendor-aware code
      quality/     # raw/ (L1a) and semantic/ (L1b) validators
      normalize/   # vendor -> canonical
      store/       # partitioned event store, manifests, readback
      replay/      # deterministic event replay, capability-scoped iterators
    reference/     # instruments, sessions, calendars, roll policy
    features/
      base.py      # Feature protocol, registry, versioning
      price/  profile/  vwap/  orderflow/  liquidity/
    labels/        # separate labelling pass — never imported by features/
    context/       # deterministic market-context classifiers
    strategy/      # spec model, rule evaluation, position/risk rules
    sim/           # event loop, execution model, accounting, ledger
    stats/         # metrics, baselines, resampling
    validation/    # split policy, walk-forward, stress, robustness suite
    registry/      # experiments, runs, lineage, research memory
    agents/        # contracts, profiles, agent implementations
    cli/           # documented entry points
  tests/
    unit/  property/  golden/  integration/
    fixtures/synthetic/        # clearly labelled, never research data
  data/                        # gitignored
    raw/  canonical/  features/  labels/  runs/
```

`src/ofa/labels/` is a sibling of `features/`, not a child. A CI import check
asserts that nothing under `features/` imports `labels/`.

---

## 4. L0–L3: the data spine

**L0 Acquisition** writes vendor bytes to `data/raw/<vendor>/<dataset>/...`
unmodified, alongside a sidecar manifest (request parameters, retrieval
timestamp, byte count, SHA-256). Raw files are never edited or deleted by
pipeline code.

**L1a Raw structural quality** runs before normalization on vendor records:
file integrity and checksum match, sequence-number gaps against the vendor's
documented tolerance, timestamp monotonicity, record counts, and session
coverage. It cannot check anything requiring a rebuilt book.

**L2 Normalization** converts vendor records into canonical events. This is
the only layer permitted to know vendor field names. It records
`transformation_version` and the **provenance tier** of every derived field
(§4.1) — notably whether aggressor side was `OBSERVED` from the exchange or
`INFERRED` by a heuristic.

**L1b Semantic quality** runs after normalization on canonical events: book
integrity (crossed, locked, negative size, level-count mismatch), quote
sanity, aggressor coverage (share of `UNKNOWN`), trade prices against the
day's range, `is_synthetic` snapshot share, and message-rate anomalies.

Both quality stages produce machine-readable reports per
(instrument, `trade_date`). A partition with a failing hard check is
quarantined, not silently repaired.

**L3 Event store** holds immutable canonical partitions keyed
`instrument / trade_date / event_type` in Parquet, plus a `manifest.json`
carrying provenance and the partition's **capability record**
(`docs/data_specification.md` §3). Readback is deterministic and ordered by
`(ts_event, sequence, ingest_index)`.

### 4.1 Provenance tiers

Every field and every derived quantity carries one of four tiers, used
consistently across storage, features, simulation, and reporting:

| Tier | Definition | Examples |
| --- | --- | --- |
| `OBSERVED` | Present in the vendor feed as delivered | trade price, exchange-supplied aggressor flag, `ts_event` |
| `RECONSTRUCTED` | Deterministically derived from observed data, no free parameters, no counterfactual | BBO from MBO, book state from applied deltas |
| `INFERRED` | Derived by a heuristic that can be wrong | tick-rule or quote-rule aggressor side |
| `SIMULATED` | Counterfactual: describes a hypothetical order of ours that never existed | queue position, fill, fill price, slippage, latency effect |

`INFERRED` is not a weaker `RECONSTRUCTED`; it has an error rate.
`SIMULATED` quantities are never described as measured or observed anywhere
in the codebase, in reports, or in commit messages.

### 4.2 Partition key

Partitions are keyed on **`trade_date`**, the exchange session date, not the
UTC calendar date. A CME Globex session opening Sunday evening US Central
belongs entirely to Monday's `trade_date`. Keying on calendar date would
split every session across two partitions and force every session-scoped
feature to span them.

`trade_date` is assigned by the L4 calendar, never by truncating a timestamp.

### 4.3 Replay

Replay is a first-class capability, not a debugging afterthought: given a run
ID and a timestamp, the system reproduces the exact event sequence that
preceded feature calculation, signal generation, simulated order, and fill.

The replay runner is also where capability scoping is enforced (§6.3).

---

## 5. L4: reference data

Instruments, tick size, tick value, multiplier, currency, expiration, and
activation come from vendor instrument definitions, never from constants
typed by hand.

Sessions are explicit objects, not `if hour > 9` conditions. A `SessionDef`
names its segments with exchange-local boundaries resolved to UTC nanoseconds
per `trade_date`, plus a holiday-calendar version. The segmentation for CME
equity-index futures is not assumed to apply to 6E; see `docs/limitations.md`.

**Contract roll** is a policy object, not an assumption:

- Research operates on **unadjusted per-contract prices**. Volume profile,
  VWAP, and all price-level features are computed within a single contract.
- A continuous series exists only for cross-contract statistics and carries
  its adjustment method and roll dates explicitly.
- The roll rule (for example: front month until volume in the deferred month
  exceeds the front month for N consecutive sessions) is versioned; changing
  it invalidates dependent feature versions.

### 5.1 Roll behaviour for stateful features

A feature carrying state across a roll would be mixing two instruments. Every
stateful feature declares a `roll_policy`, and there is no default:

| Policy | Meaning | Appropriate for |
| --- | --- | --- |
| `RESET` | `on_reset()` is called at the roll boundary; state is discarded and warm-up restarts | Price-level state: profile, VWAP, POC/VAH/VAL, anchored VWAP |
| `CARRY` | State persists across the roll | Instrument-agnostic state only: trade-count rates, time-of-day counters |
| `CARRY_ADJUSTED` | State persists with an explicit, versioned price adjustment applied | Requires written justification; the adjustment is recorded in the feature manifest |

`RESET` is the expected policy for anything price-level. A feature specifying
`CARRY` for price-level state fails review. Sessions in which a reset occurs
are flagged in feature output so downstream analysis can exclude or segregate
roll weeks.

---

## 6. L5: feature engine

### 6.1 Streaming-only contract

Every feature is a state machine:

```python
class Feature(Protocol):
    name: str
    version: str                # semantic; bump on any behavioural change
    params: FeatureParams       # frozen, hashed into the feature id
    requires: DataRequirement   # e.g. TRADES | BBO | MBP_10 | MBO
    lookback: Lookback          # longest history needed; drives warm-up
    roll_policy: RollPolicy     # RESET | CARRY | CARRY_ADJUSTED

    def on_event(self, event: CanonicalEvent) -> FeatureUpdate | None: ...
    def on_gap(self, gap: StreamGap) -> FeatureUpdate | None: ...
    def on_reset(self, reason: ResetReason) -> None: ...
    def snapshot(self) -> FeatureState: ...
```

A feature sees events exactly once, in order, and cannot see the future
because it has never been given the future. There is no vectorized
"research-mode" alternative implementation. Batch feature generation is a
replay of `on_event` over stored events; that is the only mode.

### 6.2 Gap and reset semantics

`on_gap` and `on_reset` exist from the first feature onward because
retrofitting them later means revisiting every feature's correctness.

- **`on_gap(StreamGap)`** — the stream is known to be incomplete: a
  sequence-number gap, a capture dropout, or a live disconnect and resume.
  The feature decides whether its state remains valid, degrades, or must
  invalidate. A feature that cannot survive a gap says so by invalidating,
  and downstream signals are suppressed until it is warm again.
- **`on_reset(ResetReason)`** — state must be discarded. Reasons:
  `SESSION_START`, `CONTRACT_ROLL`, `SPLIT_SEGMENT_START`, `HALT_RESUME`,
  `LIVE_RECONNECT`.

**Replay and live must be indistinguishable to a feature.** In replay, gaps
come from the stored quality report; live, they come from the feed adapter.
Because both arrive through the same two methods, a feature cannot behave
differently in the two modes — which is what makes L12's divergence alarm
meaningful.

### 6.3 Capability-scoped iteration

A feature declares `requires`. The replay runner hands it an iterator scoped
to exactly those event types. Consuming an undeclared event type raises
`UndeclaredCapabilityError` `[ENFORCED]`.

Before a run begins, the runner asserts the declared requirement against each
partition's **capability record**. A partition that lacks a required
capability — or supplies it at a weaker provenance tier than the feature
declares acceptable — fails the run rather than silently producing values
computed from `INFERRED` inputs.

### 6.4 Feature identity and single implementation

`feature_id = f"{name}@{version}#{params_hash}"`, where `params_hash` is a
stable content hash (not Python's salted `hash()`), reproducible across
processes and machines.

Feature outputs are stored under
`data/features/<instrument>/<trade_date>/<feature_id>.parquet` with a
manifest linking dataset version, capability record, code revision, and
generation timestamp. Two runs claiming the same `feature_id` must produce
byte-identical output; CI enforces this on golden fixtures.

**An optimized implementation replaces the reference implementation.** It
never sits beside it. Golden tests are a finite sample and cannot prove two
code paths equivalent, so we do not maintain two. A superseded implementation
may live in the test suite as an oracle; it must not be importable from
`src/`. There is never a second production code path for a feature.

### 6.5 Families

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
Concepts with multiple defensible definitions (value area is the obvious one)
record the competing definitions rather than silently picking one.

### 6.6 Point-in-time profile values

Session-derived values (POC, VAH, VAL, IB, session VWAP) exist in two forms
and they are **not interchangeable**:

- `prior_session.*` — final values of a completed session; available from the
  moment that session closes.
- `developing.*` — the value as it stood at time *t* within the current
  session.

Using a completed-session value inside its own session is a leakage bug.
Naming makes the distinction unavoidable; tests assert it.

### 6.7 Labels are not features

Labels (barrier outcomes, forward returns, event classifications) are
computed in `src/ofa/labels/` in a **separate, explicitly marked pass** that
is permitted to read future data, because that is what a label is.

The labelling pass is delivered in **Phase 5** alongside the strategy spec and
backtester, because purging in Phase 6 depends on `label_horizon` existing.

- No module under `features/` may import `labels/` `[ENFORCED]` by a CI
  import check.
- Label output carries a `label_horizon` — the maximum event or wall-clock
  distance into the future the label consumed.
- `label_horizon` drives purge width in every split scheme
  (`docs/research_protocol.md` §4).

---

## 7. L6: market context

Context labels (`BALANCED`, `IMBALANCED`, `BREAKOUT_ATTEMPT`, `ACCEPTANCE`,
`REJECTION`, `ROTATION`, `TRENDING`) are produced by deterministic
classifiers over features, with published thresholds and versions. An LLM may
propose a classifier; it may never emit the label at decision time.

Despite the shared word, a context label is a feature, not a label in the
§6.7 sense: it is computed from past information only and lives under
`context/`, not `labels/`.

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
unregistered feature or an unpinned version fails validation. The strategy's
declared capability requirement is the union of its features' requirements.

---

## 9. L8: simulation

A single-threaded, deterministic event loop consumes canonical events and
drives feature updates, then strategy evaluation, then the execution model.

### 9.1 The decision clock

**Decisions are timestamped at `ts_recv`, not `ts_event`.**

`ts_event` is the exchange's action time and orders the stream. `ts_recv` is
the earliest moment we could have known about the event. Reacting at
`ts_event` assumes zero feed latency and produces a silent, universal
look-ahead of feed-delay magnitude — which for order-flow strategies is
material.

Where `ts_recv` is unavailable (a vendor that does not supply it, or a
historical dataset without capture timestamps):

- an explicit `assumed_feed_delay_ns` is configured per run,
- the decision clock becomes `ts_event + assumed_feed_delay_ns`,
- the assumption is recorded in the run manifest and reported alongside every
  result derived from it,
- the value is treated as a stress-test axis, not a constant to be forgotten.

The order lifecycle therefore uses three distinct times:

```
ts_event         exchange action time      (ordering, replay)
ts_recv          we could have known       (decision clock)
order_arrival_ts decision + order latency  (fill eligibility)
```

`order_arrival_ts = decision_ts + order_latency`, where `order_latency` is a
separate, explicitly configured distribution (defaulting to a conservative
constant) representing our decision-to-exchange path. It is not the same
quantity as `assumed_feed_delay_ns` and the two are never conflated.

### 9.2 Fill model

- Fills consult only events with `ts_event > order_arrival_ts`.
- Market orders cross the book as it exists at arrival, consuming levels and
  paying spread. **The resulting slippage is `SIMULATED`, not measured.** It
  is computed against a book our own order would have perturbed, and it
  excludes market impact.
- Limit orders require a **simulated queue position**. There is no such thing
  as an observed queue position for an order that never existed: with MBO we
  can reconstruct the book's order-by-order state and then *simulate* a
  hypothetical insertion under a priority assumption; with MBP-10 we can only
  bound it.
- The queue model in force is recorded per run, and every limit-order result
  is reported under both an optimistic and a conservative model.

### 9.3 Queue and priority assumptions

| Assumption | Status |
| --- | --- |
| CME matches these outright futures FIFO by price-time priority | **UNVERIFIED** — believed true for NQ/ES/6E outrights, unverified against the CME rulebook. Allocation algorithms vary by product. No queue model may be trusted until verified. See `docs/limitations.md`. |
| A size increase on modify loses queue priority; a size decrease retains it | **UNVERIFIED** — venue-specific; must be verified before the limit-order model is used for a conclusion |

Explicit semantics the model must define, with the chosen behaviour recorded
per run:

- **Cancel/replace** — a replace is modelled as cancel-then-add at the tail
  unless the venue rule verifiably preserves priority for that modification.
- **Priority loss on modify** — size increase → tail; size decrease →
  priority retained; price change → always tail.
- **Partial fills** — a resting order fills incrementally as volume trades at
  its price; the remainder retains its queue position.
- **Same-timestamp ordering** — when our simulated order and venue events
  share a timestamp, our order is placed **behind** all events at that
  timestamp. Ties never resolve in our favour.
- **Queue advance from cancellations** — in liquid futures, most queue
  advance comes from cancellations ahead of us, not from trades. The
  conservative MBP-10 rule (fill only after the level trades through, or
  after traded volume at the level exceeds the depth ahead at submission)
  **ignores cancellations entirely and therefore systematically under-fills**.
  That is the intended direction of its error and it must be reported as
  such.

### 9.4 Self-impact bias

Our simulated order does not exist in the replayed stream. It absorbs no
volume, displaces nobody, and changes no one else's behaviour. Consequences,
all of which bias results **optimistically** and must be stated in every
execution report:

- A resting simulated order would in reality have absorbed volume that
  historically filled someone else; passive fill rates are overstated.
- A simulated market order would in reality have moved the book; realized
  slippage is understated, and market impact is entirely unmodelled.
- Strategies whose size is material relative to displayed depth at the entry
  price are affected most; capacity analysis (Gate 6) exists to bound this.

There is no way to remove this bias with historical data. The correct
response is to state it, bound it via capacity analysis, and prefer
conclusions that survive conservative assumptions.

### 9.5 Accounting

An explicit ledger: orders, fills, positions, realized and unrealized PnL in
ticks and currency, fees, and exposure over time. All PnL arithmetic is
integer-tick based where possible. Session boundaries, halts, and auction
states suspend or flatten per spec.

---

## 10. L9–L10: statistics and validation

Statistics compute metrics and their sampling behaviour. **The default
resampling unit is the session block**, not the individual trade: signals
within one session are not independent observations.

Validation applies the protocol in `docs/validation_protocol.md`: baselines,
the experiment's pre-registered split policy, walk-forward, parameter
sensitivity surfaces, regime decomposition, cost/slippage/latency/queue
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

It also enforces protocol invariants that code can check `[ENFORCED]`:

- A validation run is refused if the experiment lacks pre-registered
  acceptance thresholds.
- A validation run is refused if the experiment lacks a pre-registered split
  policy.
- Confirmation and holdout accesses are logged per experiment and per
  calendar window.

Research memory is never "the conversation history".

---

## 12. L12: paper trading

Same engine, different event source: a live feed adapter emitting canonical
events into the same replay loop, with simulated fills. Divergence between a
paper session and a replay of the same recorded session is a correctness
alarm, and is the acceptance test for this layer.

### 12.1 Historical/live capability compatibility

Historical and live feeds differ — different transport, different
normalization, often different timestamp availability. A research conclusion
is transferable to paper trading **only if the live capability record is a
superset of the capability record the research consumed, at the same or a
stronger provenance tier** `[ENFORCED]`.

Concretely, a conclusion built on `OBSERVED` aggressor side may not be paper
traded on a live feed that only supports `INFERRED` aggressor side. The paper
session records its own capability manifest, and the comparison against the
research manifest is part of the layer's acceptance test. Where `ts_recv` is
available live but was assumed historically, the difference between the
assumed feed delay and the observed one is reported.

---

## 13. Technology choices

| Choice | Rationale | Alternatives rejected |
| --- | --- | --- |
| Python 3.11+ | Research ecosystem, vendor SDKs, team velocity. Hot path is offline, so Python's speed is a throughput cost, not a correctness cost. | Rust/C++: better latency, far slower research iteration. Revisit for specific kernels only. |
| **Canonical events: frozen slotted dataclasses (or Arrow-backed structs), consumed through a Protocol** | The event type is the most-depended-on object in the system. It must stay free of framework coupling and must not carry per-event validation overhead on a path that processes millions of events. | Pydantic models for events: per-event validation on the hot path, and couples the most expensive-to-reverse type to a library. |
| **Pydantic v2 at boundaries only** — manifests, capability records, strategy specs, split policies, run config, agent contracts | Validation belongs where untrusted or hand-authored data enters, and where schema versioning matters. Volume there is tiny. | Validating everywhere: cost without benefit. Validating nowhere: unchecked hand-authored specs. |
| **Dataframes confined to L3 store I/O and L9 statistics** | Keeps the streaming contract intact and keeps the dataframe library genuinely replaceable. Features, strategy, and simulator consume typed events and iterators — never a dataframe object. | Dataframes throughout: erodes streaming causality and welds the project to one library. |
| Polars + PyArrow (at those boundaries) | Columnar Parquet I/O, predictable memory on multi-GB event data. | Pandas: heavier memory, weaker typing. Add only if a stats dependency demands it. |
| Parquet on local disk | Immutable, columnar, partitionable, portable. | Databases as the primary store: unnecessary coupling for append-only event data. |
| DuckDB | Ad-hoc SQL over Parquet for research queries without an ETL step. | Custom query code. |
| SQLite (stdlib) | Registry index; single-file, transactional, zero-ops. | Postgres: operational overhead unjustified at this scale. |
| Integer fixed-point prices (`int64`, 1e-9 scale) | Exact comparison and accounting. Tick index derived from instrument `tick_size`; conversions are **exact-only** — a price off the tick grid is an error, never a rounding. | Floats: silent comparison errors. Decimal: slower, unnecessary given a fixed scale. |
| Stable content hashing for `params_hash` | Python's `hash()` is salted per process; `feature_id` must be reproducible across processes and machines. | `hash()`: silently breaks reproducibility. |
| pytest + Hypothesis | Property tests for feature invariants (e.g. CVD is path-consistent; profile mass conserves). | Example-based tests alone. |
| mypy (strict) + ruff | Typing and lint are correctness tools here. | — |
| argparse + a thin CLI module | Documented run commands with no dependency. | Typer/Click: add later only if the CLI grows. |
| Market data vendor: **undecided** | Requires MBP-10 or MBO for CME Globex, plus verified historical depth, `ts_recv` availability, and cost. Candidates to evaluate: Databento, CME DataMine, and a live-feed vendor for later phases. | Nothing is assumed about vendor capability until verified against their documentation. |

Deferred deliberately: numba/Cython, Rust extensions, workflow orchestrators,
message buses, dashboards, feature-store products, ML frameworks.

---

## 14. Concurrency and determinism

The research pipeline parallelizes **across** partitions (instrument,
`trade_date`), never **within** an event stream. Any given
(instrument, `trade_date`, `feature_id`) is computed by one deterministic
single-threaded pass. Random number generation is seeded per run and the seed
is recorded.

---

## 15. Known architectural risks

| Risk | Mitigation |
| --- | --- |
| Streaming-only features are slow over years of MBO data | Partition-parallel batch generation; cache feature outputs; optimize by replacing the reference implementation, never by adding a second one |
| MBO storage volume for three instruments over multiple years | Start with one instrument and a bounded date range; measure before scaling; keep MBP-10 as the default tier |
| Simulated queue position dominates limit-order results | Report optimistic and conservative models; treat conclusions that need the optimistic model as unproven |
| Self-impact bias is unremovable with historical data | State it in every execution report; bound it with capacity analysis |
| Vendor schema drift | All vendor knowledge confined to L2 adapters; golden tests over stored raw samples |
| Roll handling contaminating profile features | Per-contract research prices; explicit `roll_policy` per feature; roll sessions flagged in output |
| Researcher degrees of freedom | Discovery/confirmation separation, pre-registered thresholds, discovery search log |
| Agents drifting into computation | Typed contracts, no numeric fields agents may own, hot-path boundary enforced by CI import checks |
| Feed-delay assumption forgotten when `ts_recv` is absent | Recorded per run, reported with every dependent result, and a mandatory stress axis |

---

## 16. Decisions that are expensive to reverse

These are load-bearing. Changing one invalidates stored data, every feature,
or every result. Each requires an explicit project-level decision and a
migration plan — never an incidental implementation choice.

| # | Decision | Current commitment | What breaks if changed |
| --- | --- | --- | --- |
| 1 | **Canonical event representation** | Frozen slotted dataclasses / Arrow structs behind a Protocol; no per-event validation | Every feature, the simulator, the store, replay |
| 2 | **`Feature` protocol shape** | `on_event` / `on_gap` / `on_reset` / `snapshot`, plus `requires`, `lookback`, `roll_policy` | Every feature must be revisited for correctness, not just signature |
| 3 | **Price representation** | `int64` fixed-point at 1e-9; exact-only tick-grid conversion | All stored data, all accounting, all comparisons |
| 4 | **Partition key** | `trade_date` (exchange session date) | Full canonical rebuild from raw; every session-scoped feature |
| 5 | **Event ordering key** | `(ts_event, sequence, ingest_index)` | Replay determinism; every stored result's reproducibility |
| 6 | **Simulation decision clock** | `ts_recv`, or `ts_event + assumed_feed_delay_ns` when unavailable | Every backtest result ever produced |
| 7 | **Storage layout and manifest schema** | `data/{raw,canonical,features,labels,runs}/...` with per-partition manifests and capability records | Lineage for every stored artifact |
| 8 | **Streaming-only, single-implementation feature engine** | One code path per feature; batch is replay | The project's central causality guarantee |
| 9 | **Labels separated from features** | `labels/` sibling package, CI import check, `label_horizon` drives purging | Every split, purge, and validation result |

Raw data immutability is what makes items 4, 5, and 7 recoverable at all: a
partition-key or ordering change is a rebuild, not a data loss. That property
is itself non-negotiable.
