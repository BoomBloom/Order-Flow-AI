# CLAUDE.md

Operating contract for any human or AI contributor to this repository.
Read this file completely before proposing or writing code.

---

## PROJECT

**Order Flow Multi-Agent Quantitative Research Platform.**

A quantitative research laboratory for discovering and validating trading
hypotheses using market structure, order flow, liquidity, and market
microstructure data.

This is **not** an autonomous trading bot. The deliverable is a reproducible
research apparatus that can decide whether a claimed edge is statistically
defensible out of sample.

Initial markets (in priority order): **NQ**, **ES**, **6E** (CME futures).
Future markets: BTC, ETH, US equities, additional futures. Do not build for
them yet.

Default trading mode is **simulation only**. `LIVE_TRADING = FALSE` is not a
configuration default that may be flipped casually; live execution is a
separate, isolated, explicitly-enabled layer that does not exist yet.

---

## DOCUMENT MAP

| Document | Authority over |
| --- | --- |
| `CLAUDE.md` (this file) | Working rules, precedence, definition of done |
| `docs/architecture.md` | Layers, module boundaries, technology choices, irreversible decisions |
| `docs/data_specification.md` | Canonical schemas, provenance tiers, capability matrix |
| `docs/research_protocol.md` | Hypothesis lifecycle, split policy, registry, lineage |
| `docs/validation_protocol.md` | Baselines, gates, robustness, acceptance criteria |
| `docs/agent_architecture.md` | Agent roster, typed contracts, model routing |
| `docs/roadmap.md` | Phases, sequencing, per-phase definition of done |
| `docs/limitations.md` | UNVERIFIED register and known limitations |

If two documents conflict, the conflict is a bug. Fix the documents before
writing code.

---

# CORE PRINCIPLES

## 1. Research before implementation

Do not code a strategy from a vague idea. Every idea becomes a formal
hypothesis first (`docs/research_protocol.md`).

Bad: "Absorption probably causes reversals."

Good: "At prior-session VAH, when defined absorption occurs and aggressive
buying fails to produce price continuation within N seconds, the conditional
probability of a downward move of X ticks before an adverse Y ticks exceeds
the time-of-day-matched baseline after transaction costs."

## 2. Never assume an edge exists

The system exists to discover whether an edge exists, not to confirm a
preferred concept. A negative result is a successful research result.

Never change a rule solely because an experiment failed. Changing a rule
after seeing confirmation results creates a **new experiment lineage**
(`docs/research_protocol.md`, Discovery/Confirmation Separation).

## 3. Prevent information leakage

Never use information unavailable at the decision timestamp: future prices,
trades, book states, volume, session statistics, profile values, or labels.

Highest-risk areas: completed-session statistics, rolling windows,
normalization, profile construction, VWAP anchoring, label construction,
resampling, event aggregation, contract roll adjustment, and feature state
carried across a split boundary.

The architecture defends against this structurally: **features are
event-streaming state machines and there is exactly one implementation of
each feature**. Research "batch" computation is a replay of the same
streaming code, never a vectorized re-derivation.

Three leakage rules that are easy to violate silently:

- **Decision clock.** Decisions are timestamped at `ts_recv` (when we could
  have known), never at `ts_event` (when the exchange acted). See
  `docs/architecture.md` §9.
- **Labels.** Labels are computed in a separate, marked pass and are never
  visible to a feature. Purge width is driven by the label horizon.
- **Warm-up.** Every split segment begins with a burn-in in which events are
  consumed but signals are discarded, at least as long as the longest feature
  lookback in the spec.

## 4. Deterministic engine first

Deterministic code performs: data processing, feature generation, signal
generation, backtesting, execution simulation, accounting, metrics,
statistics, risk.

LLMs perform: research, hypothesis generation, interpretation, critique,
experiment design, documentation, code assistance.

Never use an LLM as an opaque numerical calculator.

## 5. Hard hot-path boundary

The hot path is:

```
MARKET EVENT -> FEATURE -> SIGNAL -> RISK -> ORDER
```

No LLM inference, remote model call, agent delegation, or non-deterministic
component may exist anywhere in that path. This holds in backtest, in
replay, in paper trading, and in any future live layer.

LLMs operate only in research, offline analysis, hypothesis generation,
validation commentary, and other non-time-critical workflows.

## 6. Data honesty

Never fabricate market data. Never approximate unavailable information and
present it as equivalent to the real thing.

Every quantity carries a **provenance tier**:

| Tier | Meaning |
| --- | --- |
| `OBSERVED` | Present in the vendor feed as delivered |
| `RECONSTRUCTED` | Deterministically derived from observed data, no free parameters, no counterfactual (e.g. BBO from MBO) |
| `INFERRED` | Derived by a heuristic that can be wrong (e.g. tick-rule aggressor side) |
| `SIMULATED` | Counterfactual — describes a hypothetical order of ours that never existed (queue position, fill, slippage, latency) |

Never describe a `SIMULATED` quantity as measured, or an `INFERRED` one as
reconstructed. If a feature requires data we do not have, say so, record it
in the data capability matrix, and state the minimum additional data
required. Synthetic data is permitted **only** as clearly labelled test
fixtures under `tests/fixtures/synthetic/`, never as a research dataset.

## 7. Reproducibility is a hard requirement

Every result must be reproducible from stored configuration plus versioned
data. Every result must be traceable along:

```
DATASET -> FEATURE VERSION -> HYPOTHESIS -> STRATEGY VERSION
        -> BACKTEST RUN -> VALIDATION RUN -> CONCLUSION
```

## 8. Say which controls are enforced

Every control in these documents is labelled **[ENFORCED]** (code refuses the
invalid state) or **[PROCESS]** (a discipline we hold ourselves to, which
code cannot check). Never present a process control as if it were enforced.
Example: the registry can refuse a validation run whose thresholds are
missing `[ENFORCED]`; it cannot stop a researcher plotting the confirmation
sample in a notebook `[PROCESS]`.

---

# ARCHITECTURE (summary)

```
RAW DATA
  -> DATA QUALITY (L1a raw structural)
  -> NORMALIZATION
  -> CANONICAL EVENTS
  -> DATA QUALITY (L1b post-normalization semantic)
  -> FEATURE ENGINE
  -> MARKET CONTEXT
  -> HYPOTHESIS
  -> BACKTEST
  -> STATISTICS
  -> ADVERSARIAL VALIDATION
  -> RESEARCH REGISTRY
  -> PAPER TRADING
  -> (LIVE EXECUTION — not built)
```

Full detail: `docs/architecture.md`. The decisions that are expensive to
reverse are listed explicitly in `docs/architecture.md` §16; changing one of
them is a project-level decision, not an implementation detail.

---

# AGENTS (summary)

Three active agent types:

1. **Research Agent** — literature, evidence grading, hypothesis generation.
2. **Feature Specification Agent** — operationalizes ambiguous concepts, with
   three versioned domain profiles: `market_structure`, `order_flow`,
   `liquidity`.
3. **Adversarial Agent** — attacks results, generates alternative
   explanations.

**Orchestrator: deferred.** Until the deterministic research loop is
operational and there is evidence that automated orchestration beats a
documented human workflow plus the registry query CLI, the orchestrator role
is performed by a human. See `docs/agent_architecture.md` §2.

Before proposing a new agent — or splitting an existing one — it must pass
the **Agent Existence Test**:

1. Why can't this be a deterministic function or service?
2. What reasoning does it perform?
3. What unique information does it consume?
4. What typed output does it produce?
5. What breaks if we delete it?

A domain difference alone is not an agent boundary; it is a **profile** on an
existing agent. Question 5 must be answered without appealing to tidiness.

Agents communicate through **versioned typed schemas**, not free prose.
Agents never place trades and never produce numbers that deterministic code
could produce. Full detail: `docs/agent_architecture.md`.

---

# DATA RULES

Raw data is immutable. Derived data is reproducible and disposable.

Every dataset records: source, source version, instrument, venue, date
range, timezone, session definition, transformation version, feature
version, generation timestamp, code revision, and its **capability record**
(what this partition actually contains, per `docs/data_specification.md` §3).

Canonical event types: `Trade`, `Quote`, `BookSnapshot`, `BookDelta`,
`OrderEvent`, `InstrumentDef`, `SessionDef`, `StatusEvent`.

Always distinguish **exchange timestamp** (`ts_event`), **receive
timestamp** (`ts_recv`), and **sequence number**. Preserve original event
identity and ordering.

Partitions are keyed on **`trade_date`** — the exchange session date, not the
UTC calendar date. A Globex session that opens Sunday evening belongs
entirely to Monday's `trade_date`.

Prices are integers. Never compare prices as floats. Conversions to the tick
grid are exact-only: a price not representable on the grid is an error, never
a rounding. Full detail: `docs/data_specification.md`.

---

# MARKET-SPECIFIC RULES

Do not assume NQ, ES, 6E, crypto, and equities share market structure.

- Centralized futures order books are not equivalent to fragmented equity
  markets.
- Crypto order flow is venue-specific unless a carefully defined aggregation
  model is used.
- Spot FX has no globally centralized order book. For FX research, use the
  6E future.
- Do not assume 6E shares the equity-index session model. Its session
  structure is UNVERIFIED (`docs/limitations.md`).

Market-specific behaviour lives behind the common interfaces defined in
`docs/data_specification.md`; it is never hard-coded into feature logic.

---

# FEATURE ENGINE RULES

Every feature is a versioned, deterministic, event-driven module. It declares
the data capability it requires and receives a **capability-scoped event
iterator** — consuming an undeclared event type is a runtime error, not a
silent success `[ENFORCED]`.

Every feature defines behaviour for stream discontinuity (`on_gap`) and state
reset (`on_reset`), including at contract roll. A feature that carries state
across a roll must state whether it resets or carries, and why.

Every ambiguous concept (absorption, exhaustion, aggression, acceptance,
sweep, stacking) must define, before any use:

1. Mathematical definition
2. Units
3. Event/time basis and window
4. Required data granularity and provenance tier
5. Parameters and their defaults
6. Edge-case behaviour (session boundary, gap, halt, thin book, roll, reset)
7. Known failure modes and interpretation limits
8. Tests, including synthetic golden cases

A feature without an operational definition may not be referenced by a
strategy. "Large buying but price does not rise" is not a definition.

**One implementation per concept.** An optimized implementation **replaces**
the reference implementation; it never sits beside it. The prior version may
be retained inside the test suite as an oracle, but it must not be importable
from `src/`. There is never a second production code path for a feature.

**Dataframes are confined to the storage boundary (L3 read/write) and to
statistics (L9).** Features, the strategy evaluator, and the simulator
consume event iterators and typed events — never a dataframe object.

---

# STRATEGY RULES

A strategy is data (a versioned spec) plus deterministic logic. Minimum
structure:

```
Market | Session | Context | Location | Setup | Trigger | Entry
Stop | Target | Exit | Sizing | Costs | Slippage | Latency
Invalidation | Cooldown | MaxConcurrent | ResearchMetadata
```

Discretionary wording ("strong buying", "heavy liquidity", "looks weak") is
forbidden unless it maps to a deterministic definition.

---

# BACKTEST RULES

- Order-flow strategies are not silently converted into candle-close
  strategies.
- **The decision clock is `ts_recv`.** `ts_event` orders the stream; it never
  triggers a decision. Where `ts_recv` is unavailable, an explicit
  `assumed_feed_delay_ns` is added to `ts_event` and recorded per run.
- Model timestamps, spread, commissions, slippage, latency, order type, fill
  logic, session boundaries.
- No future order-book state may influence an earlier fill. A fill may only
  consult events strictly after the order's simulated exchange-arrival
  timestamp.
- All fill, slippage, and queue-position quantities are `SIMULATED`. They are
  never described as measured or observed.
- A backtest run is immutable once written. Re-running produces a new run ID.

---

# VALIDATION RULES

No strategy may be evaluated without a defined **baseline / null
comparison**.

**Split policy is per-experiment configuration, not a constant.** It is
pre-registered in the experiment record and supports chronological block
splits (the default initial policy), interleaved block splits, purged and
embargoed cross-validation, combinatorial purged CV, cross-instrument
holdout, and time-extending holdout windows. Every scheme carries purge
(driven by label horizon), embargo, and per-segment warm-up. See
`docs/research_protocol.md` §4.

**Acceptance thresholds are pre-registered at `FORMALIZED`** and stored in
the experiment record. The registry refuses a validation run whose experiment
lacks them `[ENFORCED]`.

Use, as appropriate: parameter sensitivity, regime analysis,
transaction-cost and slippage stress, latency and queue-model stress,
sample-size analysis, block bootstrap (session-level blocks by default) and
Monte Carlo, multiple-testing accounting.

Evaluate expectancy, average R, profit factor, risk-adjusted return,
drawdown, trade count, payoff distribution, skew, tail behaviour, exposure,
turnover, and stability across periods. **Win rate alone is never
sufficient.** Full detail: `docs/validation_protocol.md`.

---

# MULTIPLE TESTING

The registry records the number of hypotheses tested, the **hypothesis
family** (defined in `docs/research_protocol.md` §8), parameter variants,
selection criteria, every failed experiment, and a self-reported
**discovery search log** covering exploration that never became a registered
experiment. Never present the best result of a large search as though it were
an isolated test.

---

# OBSERVABILITY

Every run (deterministic or agent) records: run ID, parent run, component,
model and prompt version where applicable, input versions, outputs, latency,
token usage, cost, status, and errors.

---

# MODEL ROUTING

Not every task needs the strongest model. Roles:

| Role | Typical use |
| --- | --- |
| Strategic | Architecture, research design |
| Synthesis | Hypothesis generation from evidence |
| Adversarial | Validation critique |
| Implementation | Routine code generation |
| Classification | Cheap structured labelling |

Deterministic quantitative calculations must not call a model at all.

---

# WHAT NOT TO BUILD YET

Until the deterministic research loop is validated end to end, do not build:

live execution, autonomous trading, reinforcement learning, neural
prediction models, automated strategy optimizers, a GEX subsystem, a complex
dashboard/UI, multi-market optimization, or the Orchestrator agent.

These are later phases. See `docs/roadmap.md`.

---

# ENGINEERING RULES

Before changing code:

1. Read `CLAUDE.md`.
2. Inspect the relevant code.
3. Identify dependencies.
4. State the intended change.
5. Implement the smallest coherent change.
6. Add or update tests.
7. Run tests.
8. Review for regressions.
9. Report exactly what changed.

Do not make unrelated refactors. Do not redesign architecture during an
implementation task. Do not silently widen scope. Do not change an item in
`docs/architecture.md` §16 without an explicit decision.

## Code quality

Prefer small modules, explicit types, pure deterministic functions,
immutable raw-data boundaries, clear interfaces, testable components.

Avoid hidden global state, magic constants, giant classes, implicit market
assumptions, duplicated feature logic, and opaque AI-generated decision
logic.

Every module gets type annotations and passes the configured type checker.
Non-obvious microstructure assumptions get a comment naming the assumption
and its failure mode.

## Dependencies

Before adding one: explain why it is needed, what the alternatives are, the
maintenance implication, and only then add it. Never invent an external API
or exchange capability. If unsure whether a vendor supports something, say
so and record it in `docs/limitations.md` instead of assuming.

---

# DEFINITION OF DONE

A phase or task is complete only when **all** of the following hold:

1. The implementation exists.
2. Tests exist.
3. Tests pass.
4. It can be run from a documented command.
5. The output is inspectable by a human.
6. The result is reproducible.
7. Known limitations are documented.

Passing unit tests alone is not sufficient.

---

# SECURITY

No credentials in the repository. Data-vendor and model API keys come from
environment variables or an untracked local env file. No live-trading
capability during research. Any future live module sits behind explicit
configuration, a separate process boundary, and its own safeguards.

---

# DEFINITION OF PROJECT SUCCESS

The project succeeds when it can take a vague trading idea and turn it into:
a precise hypothesis -> deterministic features -> a reproducible backtest ->
realistic execution simulation -> out-of-sample validation -> adversarial
robustness testing -> a permanent research record -> a paper-trading
candidate.

A visually impressive multi-agent system without defensible research
methodology is **not** success.
