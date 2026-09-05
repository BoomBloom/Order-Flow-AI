# PLAN.md — Project Control Document

High-level control document for the Order Flow Multi-Agent Quantitative
Research Platform. It tracks **what is decided, what is next, and what may
not start yet**.

This is not an architecture specification. It introduces no design decisions
of its own. Where detail is needed, it points to the authoritative document
rather than restating it — if this file and an authoritative document ever
disagree, the authoritative document wins and this file is the bug.

| Concern | Authoritative document |
| --- | --- |
| Working rules, definition of done | `CLAUDE.md` |
| Layers, boundaries, technology, irreversible decisions | `docs/architecture.md` |
| Canonical schemas, provenance, capability | `docs/data_specification.md` |
| Hypothesis lifecycle, split policy, registry | `docs/research_protocol.md` |
| Gates, metrics, verdict, acceptance | `docs/validation_protocol.md` |
| Agent roster, contracts, model routing | `docs/agent_architecture.md` |
| Phase detail and per-phase definition of done | `docs/roadmap.md` |
| UNVERIFIED register, permanent limitations | `docs/limitations.md` |

---

## 1. Objective

Build a reproducible research laboratory that can take a vague trading idea
and determine whether it contains a statistically defensible out-of-sample
edge — and prove it wrong when it does not.

Initial markets: **NQ**, **ES**, **6E** (CME futures), in that priority.

Success is a research apparatus with defensible methodology. A visually
impressive multi-agent system without it is not success.

---

## 2. Current status

**Documentation / Architecture Gate: COMPLETE.**

- Architecture and protocol documents written and cross-audited.
- Architecture gate run; 3 CRITICAL and 12 IMPORTANT findings applied.
- Two architectural decisions taken: agent roster collapsed to three active
  types with the Orchestrator deferred; split policy made per-experiment
  configuration.

**Phase 0 — Repository foundation: COMPLETE.**

Delivered and committed:

| Milestone | Content |
| --- | --- |
| Toolchain | `pyproject.toml`, `ruff`, `mypy --strict`, `pytest`, `hypothesis`, `make check` |
| Step 1 | `Price`, `Ticks`, `TickGrid` — `int64` fixed-point at 1e-9, exact-only tick conversion |
| Step 2 | `UtcNanos`, `TradeDate` — exact UTC-nanosecond instant and assigned trading date |
| Step 3 | Canonical serialization and stable content hashing (`ofa-canon-1`); `RunId`, `InstrumentId`, `ProvenanceId` |
| M1 | `ProvenanceTier`, `DataRequirement`, `CapabilityEntry`, `CapabilityRecord`, `RollPolicy`, `ResetReason` |
| M2 | Schema-version registry, code-revision resolution, `ofa version` |
| M3 | Pinned toolchain, CI, dependency/SDK/`data` guards, deterministic Phase 0 artifact, limitations closure |

All seven Phase 0 exit criteria in `docs/roadmap.md` are now met, verified from
a clean checkout by [GitHub Actions run 33959395015](https://github.com/BoomBloom/Order-Flow-AI/actions/runs/33959395015)
at revision `e69114d0576b07c61a12cc9356eb116235b3b281` rather than by inspection.

Deliberately **not** built in Phase 0, each deferred to a named gate and
recorded in `docs/limitations.md` §5:

- **`Feature` protocol and `Lookback`** (D3) — the signature names five types
  the specification never defines, and `Lookback` carries a real conflict
  between event-count, volume, time and session windows against language
  requiring a single "longest" lookback. Needs its own design gate before
  Phase 3.
- **`CanonicalEvent` envelope** (D4) — whether the envelope carries raw
  integers or the core value types is a genuine trade-off against §16 item 1's
  ban on per-event validation. Needs an event-representation gate.
- **`feature_id`** (D2) — Phase 3, with the feature registry.
- **The dataset manifest** (D5) — Phase 1, where the vendor is known and
  Pydantic is legitimately at the boundary.
- **Capability quality statistics** (D6) — Phase 1.

Two documentation conflicts remain open and are recorded rather than silently
resolved (`docs/limitations.md` §7): the feature storage path, and whether
`venue` is a top-level manifest field.

No vendor selected. No data acquired. No runtime dependencies declared.

---

## 3. Non-negotiable boundaries

These hold in every phase and are not traded away for convenience.

1. **Hot path is deterministic.** `MARKET EVENT -> FEATURE -> SIGNAL -> RISK
   -> ORDER` contains no LLM inference, no remote model call, no agent
   delegation, and no non-deterministic component — in backtest, replay,
   paper trading, or any future live layer.
2. **Simulation only.** `LIVE_TRADING = FALSE`. No live execution capability
   exists or is built during research.
3. **Raw data is immutable.** Derived data is reproducible and disposable.
4. **No fabricated data.** Synthetic data exists only as labelled test
   fixtures, never as a research dataset. Unavailable information is recorded
   as unavailable, never approximated and presented as equivalent.
5. **Provenance is explicit.** Every quantity is `OBSERVED`,
   `RECONSTRUCTED`, `INFERRED`, or `SIMULATED`. Fills, slippage, and queue
   position are always `SIMULATED` and never described as measured.
6. **Reproducibility.** Every result traces `DATASET -> FEATURE VERSION ->
   HYPOTHESIS -> STRATEGY VERSION -> BACKTEST RUN -> VALIDATION RUN ->
   CONCLUSION`.
7. **A failed hypothesis is a successful result.** Failures are never deleted;
   they are the denominator.
8. **Enforced vs process controls are labelled.** A `[PROCESS]` discipline is
   never reported as if code enforced it.

---

## 4. Locked architectural decisions

Changing any of these is a project-level decision requiring a migration plan,
never an incidental implementation choice. Full detail and blast radius:
`docs/architecture.md` §16.

| # | Decision |
| --- | --- |
| 1 | Canonical events are frozen slotted structures behind a Protocol; no per-event validation. Pydantic is used at boundaries only |
| 2 | `Feature` protocol: `on_event` / `on_gap` / `on_reset` / `snapshot`, plus `requires`, `lookback`, `roll_policy` |
| 3 | Prices are `int64` fixed-point at 1e-9; tick-grid conversion is exact-only |
| 4 | Partition key is `trade_date` (exchange session date), not UTC calendar date |
| 5 | Event ordering key is `(ts_event, sequence, ingest_index)` |
| 6 | Decision clock is `ts_recv`, or `ts_event + assumed_feed_delay_ns` when unavailable |
| 7 | Storage layout and manifest schema, including per-partition capability records |
| 8 | Streaming-only, single-implementation feature engine; batch is replay; an optimization replaces the reference implementation and never sits beside it |
| 9 | Labels are a separate pass from features; `label_horizon` drives purge width |
| 10 | Canonical content-hash format: type-tagged canonical JSON hashed as SHA-256 over an `ofa-canon-1` version prefix, full lowercase hex digest |

Two further decisions, taken at the architecture gate:

| Decision | Summary | Authority |
| --- | --- | --- |
| **Agent roster** | Three active agent types: Research, Feature Specification (profiles `market_structure`, `order_flow`, `liquidity`), Adversarial. Orchestrator deferred | `docs/agent_architecture.md` §2 |
| **Split policy** | Per-experiment pre-registered configuration, eight required fields, six schemes; chronological block is the default, not the only option | `docs/research_protocol.md` §4 |

---

## 5. Remaining UNVERIFIED decisions

Tracked in full in `docs/limitations.md`. Nothing here is promoted to an
assumption by silence, and an UNVERIFIED item that blocks a phase blocks it.

| Area | Open questions | Blocks |
| --- | --- | --- |
| Vendor and feed (V1–V8) | Vendor identity, tiers, cost, history depth; **whether `ts_recv` is supplied historically**; aggressor-side provenance; MBP-10 truncation; MBO availability; sequence semantics; storage volume; live feed | Phase 1 onward |
| Exchange semantics (E1–E6) | **CME matching algorithm and modify-priority for NQ/ES/6E outrights**; 6E session structure; calendar source; implied orders; settlement timing | Phase 2, Phase 5 |
| Costs and execution (C1–C3) | Fee schedule; realistic order latency; connectivity assumptions | Phase 6 Gate 6 |
| Platform (P1–P2) | LLM provider, models per role, budget; compute environment and disk | Phase 8; data-tier sizing |

Two gate the most work: **V2** decides whether the decision clock is real or
assumption-based, and **E1/E2** decide whether any simulated queue model can
support a conclusion at all.

---

## 6. Phase gating rule

**A phase may not begin until every exit criterion of its predecessor
passes.** Exit criteria are the Definition of Done in `CLAUDE.md`:
implementation exists · tests exist · tests pass · runnable from a documented
command · output inspectable · reproducible · limitations documented.

Passing unit tests alone is never sufficient. Partial completion does not
unlock the next phase. Where a phase is blocked by an UNVERIFIED item, the
item is resolved — not assumed around.

---

## 7. Phases

Summaries only. Per-phase detail and the full "Done when" text live in
`docs/roadmap.md`.

### Phase 0 — Repository foundation

- **Prerequisites:** none. Architecture gate complete.
- **Scope:** tooling and CI; `src/ofa/core/` primitives (UTC-ns time, integer
  fixed-point price with exact tick conversion, ids, stable content hashing,
  errors, capability/provenance manifest primitives, provenance-tier and
  `DataRequirement` enums); `docs/limitations.md` kept current. The
  `CanonicalEvent` and `Feature` protocol declarations and the full dataset
  manifest are **deferred by accepted scope amendment** — see
  `docs/roadmap.md` Phase 0 and `docs/limitations.md` §5.
- **Out of scope:** all vendor code, data download, event store, replay,
  reference data, features, labels, strategy, simulator, statistics,
  validation, registry, agents, and any CLI beyond `ofa version`. **No
  market-data SDK in `pyproject.toml`.**
- **Exit criteria:** `make check` green on a clean clone · price/tick and
  time property tests hold, no float in any price path · `params_hash`
  identical across separate interpreter processes · `ofa version` prints code
  revision and schema versions · repeat runs produce identical artifacts · CI
  asserts `data/` gitignored and no market-data SDK present ·
  `docs/limitations.md` current.

### Phase 1 — The data spine (one instrument, one source)

- **Prerequisites:** Phase 0 exit; vendor selected; V1–V6 resolved.
- **Scope:** one instrument (NQ front month), one real source, bounded date
  range: ingestion, L1a raw checks, normalization with per-field provenance,
  L1b semantic checks, `trade_date`-keyed store with capability records,
  deterministic readback and replay.
- **Out of scope:** features, labels, strategies, agents, second instrument.
- **Exit criteria:** documented `ingest` / `quality` / `normalize` / `replay`
  commands · byte-identical repeat replay · capability matrix filled with
  verified values, verifier, date, and vendor-doc version — including whether
  `ts_recv` is supplied · limitations recorded.

### Phase 2 — Reference data, sessions, calendars, roll

- **Prerequisites:** Phase 1 exit; E3–E4 resolved.
- **Scope:** instrument registry from vendor definitions; versioned exchange
  calendar; `SessionDef` and `trade_date` assignment; roll policy;
  per-contract unadjusted research prices.
- **Out of scope:** features; assuming the equity-index session model applies
  to 6E.
- **Exit criteria:** sessions and `trade_date` assignments checked against
  exchange documentation across at least one early close, one holiday, and
  one roll week.

### Phase 3 — Feature engine core + first families

- **Prerequisites:** Phase 2 exit.
- **Scope:** `Feature` implementation, registry, `feature_id` hashing,
  capability-scoped iterators, gap/reset handling, roll policy; feature store;
  price/microstructure, VWAP, volume profile; `prior_session.*` vs
  `developing.*`; one definition doc per feature.
- **Out of scope:** order flow, liquidity, labels, strategies.
- **Exit criteria:** golden fixtures hand-verifiable · property tests hold ·
  leakage suite fails on same-session completed values · undeclared event
  type raises · roll triggers the declared policy · byte-reproducible output.

### Phase 4 — Order flow and liquidity features

- **Prerequisites:** Phase 3 exit; V3–V5 resolved for anything book-related.
- **Scope:** order-flow family; liquidity family (MBP-10 minimum, MBO for
  queue-level work); explicit `UNKNOWN` and `INFERRED` aggressor handling.
- **Out of scope:** anything the capability record cannot support — recorded
  as blocked, never approximated.
- **Exit criteria:** every concept has an eight-section definition doc,
  golden cases, and a stated failure-mode list; blocked items documented.

### Phase 5 — Labels, strategy spec, event-driven backtester

- **Prerequisites:** Phase 4 exit; C1–C2 for cost realism; E1–E2 before any
  limit-order conclusion is trusted.
- **Scope:** `src/ofa/labels/` as a separate pass emitting `label_horizon`,
  with the CI check that `features/` never imports it; strategy spec model
  bound to pinned `feature_id`s; deterministic event loop on the `ts_recv`
  decision clock; order latency; future-only fills; optimistic and
  conservative simulated queue models with explicit cancel/replace,
  partial-fill, priority-loss, and same-timestamp semantics; integer-tick
  ledger.
- **Out of scope:** statistics, validation gates, registry, agents.
- **Exit criteria:** reference strategy PnL hand-computable on fixtures · no
  fill consulted an event at or before order arrival · no decision taken
  before `ts_recv` · byte-identical repeat runs · any fill replayable with
  its preceding event window · every execution artifact labelled `SIMULATED`.

**Labels are in Phase 5, not Phase 6.** Purging in Phase 6 depends on
`label_horizon` existing, so the labelling pass must precede the split engine.

### Phase 6 — Statistics and validation engine

- **Prerequisites:** Phase 5 exit (labels included).
- **Scope:** metrics with session-block bootstrap; baseline generators; the
  split policy engine (all six schemes, label-horizon purging, embargo,
  per-segment warm-up, fixed and time-extending holdout); cost, slippage,
  order-latency, feed-delay and queue-model stress; regime and roll-week
  decomposition; multiple-testing adjustment; the gated verdict object.
- **Out of scope:** registry persistence, agents.
- **Exit criteria:** the gate sequence returns `FAILED` for a known-noise
  strategy naming the correct gate; a run whose experiment lacks
  pre-registered thresholds or split policy is refused.

### Phase 7 — Registry, lineage, research memory

- **Prerequisites:** Phase 6 exit.
- **Scope:** SQLite index over immutable artifacts; experiment records;
  lineage keys; confirmation/holdout access logging by calendar window;
  hypothesis-family assignment; variant counts and the self-reported
  discovery search log; threshold and split-policy pre-registration
  enforcement; the query CLI.
- **Out of scope:** agents.
- **Exit criteria:** every Phase 6 run registered; one command traces a
  conclusion back to raw bytes, capability record, and code revision.

### Phase 8 — Agent layer

- **Prerequisites:** Phase 7 exit; P1 resolved.
- **Scope:** typed contracts and schema versioning; agent run logging with
  profile version, tokens, cost; the three active agents; model routing;
  human-approval checkpoints; human-performed orchestration workflow.
- **Out of scope:** the Orchestrator agent; any agent in the hot path; any
  agent producing numbers deterministic code owns.
- **Exit criteria:** an agent-proposed spec compiles into a real feature
  through human review · schema-invalid output rejected · agent outage leaves
  the deterministic pipeline unaffected · CI proves no agent import in the
  hot path.

### Phase 9 — First real experiment: OF-0001

- **Prerequisites:** Phase 8 exit.
- **Scope:** one real hypothesis through the full loop and every gate, with
  its record published — including, and especially, on failure.
- **Out of scope:** acting on the result.
- **Exit criteria:** complete experiment record with pre-registered
  thresholds and split policy, discovery, confirmation, robustness,
  multiple-testing context, verdict, and conclusion, reproducible from stored
  config.

### Phase 10 — Extension (only after Phase 9)

- **Prerequisites:** Phase 9 exit.
- **Scope, in order:** ES and 6E (6E session structure verified, not
  assumed); additional hypothesis families; the paper-trading harness (live
  event source, simulated fills, historical/live capability compatibility
  check, replay-divergence alarm). The Orchestrator is considered here at the
  earliest, and only against §8 below.
- **Out of scope:** live execution, autonomous trading, RL, neural
  prediction, automated strategy optimizers, GEX subsystem, dashboards,
  multi-market optimization, crypto, equities.
- **Exit criteria:** per `docs/roadmap.md`; paper trading is accepted only
  when a paper session and a replay of the same recorded session do not
  diverge.

---

## 8. Deferred: Orchestrator agent

**Status: deferred. Not built before Phase 10, and not then without
evidence.**

The Orchestrator performs genuine reasoning, but with few experiments the
human researcher is the orchestrator and the registry query CLI supplies the
prior-work lookup that was its most valuable step. Building it early risks a
prose-generating middleman between a human and a deterministic engine.

Unlock conditions — all three, per `docs/agent_architecture.md` §2.2:

1. The deterministic research loop is operational end to end (Phase 9
   complete).
2. Manual prior-work lookup and prioritization are demonstrably a bottleneck.
3. A written comparison shows what it adds beyond the documented human
   workflow plus the registry CLI.

Until then `docs/research_protocol.md` §13 assigns the orchestration role to
the human researcher.

---

## 9. Deferred: AI Traders

**Status: deferred indefinitely. Does not exist and is not designed.**

An *AI Trader* means any LLM or learned model that generates, selects, or
influences a trade decision at decision time. This is distinct from the
research agents, which never touch a decision.

This is not a new decision — it follows from the hot-path boundary (§3.1) and
from the existing prohibition on autonomous trading, reinforcement learning,
and neural prediction models in `CLAUDE.md` and `docs/roadmap.md`.

Deferral conditions:

1. The deterministic research and simulation foundation is validated —
   Phase 9 complete, with at least one experiment carried through every gate.
2. The paper-trading harness runs without replay divergence (Phase 10).
3. Introducing one would require an explicit architectural decision, its own
   gate, and a written account of how it could exist without violating the
   hot-path boundary — which, as currently specified, it cannot.

Nothing in the current architecture anticipates an AI Trader. If one is ever
proposed, it starts from the boundary, not from an exception to it.

---

## 10. Three component classes — do not conflate

| | Research agents | AI traders | Deterministic risk / execution |
| --- | --- | --- | --- |
| **Exists?** | Phase 8 | No — deferred (§9) | Phase 5 (simulated); live layer not built |
| **Runs when?** | Offline, non-time-critical | Would run at decision time | Decision time, in the hot path |
| **Uses a model?** | Yes | Would | **Never** |
| **Determinism** | Not required | — | Required; byte-reproducible |
| **Produces** | Typed proposals, definitions, critiques | Would produce trade decisions | Signals, risk decisions, orders, fills, accounting |
| **May produce numbers deterministic code owns?** | No | — | It *is* the deterministic code |
| **May place a trade?** | No | — | Simulated only; live requires an isolated future layer |
| **Authority** | `docs/agent_architecture.md` | §9 above | `docs/architecture.md` §7–§9 |

The distinction that matters: research agents advise *what to test*;
deterministic components decide *what happens*. An AI trader would collapse
that separation, which is why it is deferred rather than scheduled.

---

## 11. Immediate next action

Phase 0's implementation is complete and verified from a clean checkout. Two
things gate what follows, and they are independent of each other:

1. **Resolve the vendor question (V1–V2).** Phase 1 cannot start without it,
   and V2 in particular — whether `ts_recv` is supplied historically — decides
   whether the decision clock is measured or assumed.
2. **Hold the two deferred design gates**, `Lookback` / `Feature` and the
   `CanonicalEvent` envelope. Neither blocks Phase 1's data spine; both block
   Phase 3.

Phase 1 may begin once V1–V6 are resolved. Nothing in Phase 0 remains to
build.
