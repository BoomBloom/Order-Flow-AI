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
| `docs/architecture.md` | Layers, module boundaries, technology choices |
| `docs/data_specification.md` | Canonical schemas, provenance, capability matrix |
| `docs/research_protocol.md` | Hypothesis lifecycle, experiment registry, lineage |
| `docs/validation_protocol.md` | Baselines, splits, robustness, acceptance gates |
| `docs/agent_architecture.md` | Agent contracts, orchestration, model routing |
| `docs/roadmap.md` | Phases, sequencing, per-phase definition of done |

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
resampling, event aggregation, contract roll adjustment.

The architecture defends against this structurally: **features are
event-streaming state machines and there is exactly one implementation of
each feature**. Research "batch" computation is a replay of the same
streaming code, never a vectorized re-derivation.

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

If a feature requires data we do not have, say so, record it in the data
capability matrix, and state the minimum additional data required. Synthetic
data is permitted **only** as clearly labelled test fixtures under
`tests/fixtures/synthetic/`, never as a research dataset.

## 7. Reproducibility is a hard requirement

Every result must be reproducible from stored configuration plus versioned
data. Every result must be traceable along:

```
DATASET -> FEATURE VERSION -> HYPOTHESIS -> STRATEGY VERSION
        -> BACKTEST RUN -> VALIDATION RUN -> CONCLUSION
```

---

# ARCHITECTURE (summary)

```
RAW DATA
  -> DATA QUALITY
  -> NORMALIZATION
  -> CANONICAL EVENTS
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

Full detail: `docs/architecture.md`.

---

# AGENTS (summary)

Orchestrator, Research, Market Structure, Order Flow, Liquidity,
Validation/Adversarial. Six total. No others.

Before proposing a new agent it must pass the **Agent Existence Test**:

1. Why can't this be a deterministic function or service?
2. What reasoning does it perform?
3. What unique information does it consume?
4. What typed output does it produce?
5. What breaks if we delete it?

If those cannot be answered convincingly, do not create the agent.

Agents communicate through **versioned typed schemas**, not free prose.
Agents never place trades and never produce numbers that deterministic code
could produce. Full detail: `docs/agent_architecture.md`.

---

# DATA RULES

Raw data is immutable. Derived data is reproducible and disposable.

Every dataset records: source, source version, instrument, venue, date
range, timezone, session definition, transformation version, feature
version, generation timestamp, and code revision.

Canonical event types: `Trade`, `Quote`, `BookSnapshot`, `BookDelta`,
`OrderEvent`, `InstrumentDef`, `SessionDef`, `StatusEvent`.

Always distinguish **exchange timestamp**, **receive timestamp**, and
**sequence number**. Preserve original event identity and ordering.

Prices are integers. Never compare prices as floats. Full detail:
`docs/data_specification.md`.

---

# MARKET-SPECIFIC RULES

Do not assume NQ, ES, 6E, crypto, and equities share market structure.

- Centralized futures order books are not equivalent to fragmented equity
  markets.
- Crypto order flow is venue-specific unless a carefully defined aggregation
  model is used.
- Spot FX has no globally centralized order book. For FX research, use the
  6E future.

Market-specific behaviour lives behind the common interfaces defined in
`docs/data_specification.md`; it is never hard-coded into feature logic.

---

# FEATURE ENGINE RULES

Every feature is a versioned, deterministic, event-driven module.

Every ambiguous concept (absorption, exhaustion, aggression, acceptance,
sweep, stacking) must define, before any use:

1. Mathematical definition
2. Units
3. Event/time basis and window
4. Required data granularity
5. Parameters and their defaults
6. Edge-case behaviour (session boundary, gap, halt, thin book, roll)
7. Known failure modes and interpretation limits
8. Tests, including synthetic golden cases

A feature without an operational definition may not be referenced by a
strategy. "Large buying but price does not rise" is not a definition.

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
- Model timestamps, spread, commissions, slippage, latency, order type, fill
  logic, session boundaries.
- No future order-book state may influence an earlier fill. A fill may only
  consult events strictly after the order's simulated exchange-arrival
  timestamp.
- A backtest run is immutable once written. Re-running produces a new run ID.

---

# VALIDATION RULES

No strategy may be evaluated without a defined **baseline / null
comparison**.

Use, as appropriate: discovery/confirmation split, purged and embargoed
cross-validation, walk-forward, parameter sensitivity, regime analysis,
transaction-cost and slippage stress, sample-size analysis, block bootstrap
and Monte Carlo, multiple-testing accounting.

Evaluate expectancy, average R, profit factor, risk-adjusted return,
drawdown, trade count, payoff distribution, skew, tail behaviour, exposure,
turnover, and stability across periods. **Win rate alone is never
sufficient.** Full detail: `docs/validation_protocol.md`.

---

# MULTIPLE TESTING

The registry records the number of hypotheses tested, related hypothesis
families, parameter variants, selection criteria, and every failed
experiment. Never present the best result of a large search as though it
were an isolated test.

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
dashboard/UI, or multi-market optimization.

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
implementation task. Do not silently widen scope.

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
or exchange capability. If unsure whether a vendor supports something,
say so instead of assuming.

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
