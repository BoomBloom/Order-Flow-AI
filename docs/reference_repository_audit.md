# BoomBloom reference-repository audit

**Audit date:** 2026-09-05; review corrections: 2026-09-06

**Scope:** Read-only review of public repositories owned by `BoomBloom`, using first-party GitHub repository metadata, source trees, source files, tests, and project documentation.

**OFA baseline:** Commit `2fbc9a517fedf18ed9537784cc5a774235c995e7`, its `CLAUDE.md`, `AGENTS.md`, `PLAN.md`, and the user-supplied master roadmap.

## Executive conclusion

No audited repository should be adopted wholesale or added as an OFA dependency. The useful material is mostly architectural precedent, test methodology, boundary design, and hypotheses to formalize—not production code to transplant.

The five highest-value references are:

1. **NautilusTrader** — adapt its research/replay/live event-path parity, deterministic-clock thinking, adapter boundary, and regression discipline. Do not import the framework or inherit its much larger execution surface.
2. **machine-learning-for-trading** — adapt its point-in-time validation ideas, especially event-time versus knowledge-time checks and tests that demonstrate why weak leakage heuristics fail.
3. **Freqtrade** — adapt the differential “baseline versus sliced run” leakage falsifier. Reject its dataframe-wide feature path and candle-binned order-flow representation as OFA production semantics.
4. **Lean** — study its mature regression suite, brokerage/data boundary, order-state machine, warm-up, and fill-model test coverage. Adapt patterns selectively; do not adopt the engine.
5. **Qlib** — adapt only its run-recorder vocabulary and simulator component seams. Do not adopt its batch/time-step execution model, MLflow coupling, floating amounts, or scientific runtime.

**qapf is the highest-value failure archive**, immediately after the top five: it records silent factor-engine output, dependency-pin cascades, stale sample data, and multiprocessing re-import failure. Its 16-agent autonomous-prop-firm target and proposed LLM-to-trading composition remain rejected.

Several repositories contain attractive but dangerous patterns: direct LLM trade decisions, autonomous execution, dataframe look-ahead exposure, floating-point prices/ledger values, generic “L2” abstractions, bar-close backtests standing in for event simulation, reinforcement-learning optimization, weak promotion gates, mutable global state, wall-clock/UUID identities, and strategy claims without preregistered falsification. These are recorded under category **Q** and are not OFA design inputs except as failure cases.

## Method and limits

The owner inventory came from GitHub’s public first-party endpoint, [`GET /users/BoomBloom/repos`](https://api.github.com/users/BoomBloom/repos?per_page=100&type=owner&sort=full_name). Exact branch heads were independently resolved with Git’s smart-HTTP protocol; source links below are pinned to those commits rather than floating branches.

Many entries are BoomBloom forks or mirrors. A pinned BoomBloom commit proves only the state inspected in that fork; it does not establish which lines came from the upstream project, whether the fork is ahead/behind/diverged, or whether an upstream fix/license change exists. This pass did not resolve every fork parent and divergence graph. Before a finding influences a phase design, re-check the fork’s `parent`/`source`, compare the pinned fork commit with current upstream, attribute the concept to the repository that authored it, and re-verify both upstream and fork license notices. No finding is represented as a BoomBloom-authored change unless that provenance was established.

This audit can establish what public source currently contains; it cannot establish private repositories, deleted repositories, owner intent, production deployment behavior, vendor entitlements, or correctness of claims not backed by code/tests. GitHub returned 58 public repositories. All 38 repositories named by the master roadmap were present. Three additional public repositories were relevant enough to sample: `deepseek-harness`, `ruflo`, and `hqchart`. `TabPFN` was screened because it is ML-related but rejected for current OFA scope. The remaining owner repositories were unrelated coursework, hardware, generic algorithms, or placeholders and are listed near the end.

“Deep review” below means targeted semantic inspection of relevant source/docs/tests, not a line-by-line security audit. Very large frameworks (`nautilus_trader`, `Lean`, `OpenBB`, `StockSharp`, `qlib`, `freqtrade`, `FinceptTerminal`) and book/catalog repositories were sampled at their architecture-critical modules. Catalogs and notebook collections cannot be treated as verified evidence merely because they link to or demonstrate a technique. Repositories without a detected license must be treated as **all rights reserved for reuse purposes** unless clarified; links and concepts may be studied, but code must not be copied.

## Authority and phase-label conflict

The pasted master roadmap and the repository’s authoritative roadmap assign materially different work to the same phase numbers. For example, the master calls Phase 1 a vendor-evidence gate and Phase 2 the canonical event model; repository [`PLAN.md`](../PLAN.md) and [`docs/roadmap.md`](roadmap.md) define Phase 1 as the one-source data spine and Phase 2 as reference data, sessions, calendars, and roll, while retaining named representation/design gates. Later feature, simulator, validation, registry, and agent numbers also differ.

Per `CLAUDE.md`’s document precedence, this report uses **repository-roadmap phase labels exclusively**. Thus “Phase 5” means the repository’s labels/strategy/backtester phase, not master-roadmap Phase 5. The conflict is itself a governance bug: reconcile the master roadmap with `PLAN.md`, `docs/roadmap.md`, and the accepted deferred gates before using this report to authorize any implementation or phase advance. This audit does not perform that reconciliation and opens no gate.

## Decision vocabulary

- **ADOPT** — use the concept essentially as stated, implemented independently under OFA contracts.
- **ADAPT** — retain the principle but redesign it for OFA’s deterministic/provenance/capability rules.
- **STUDY ONLY** — useful precedent, hypothesis seed, or failure case; no implementation commitment.
- **REJECT** — conflicts with locked OFA architecture or lacks sufficient rigor for the claimed role.

No entry marked ADOPT/ADAPT approves a library, dependency, vendor, runtime, or code copy.

## Ranking rubric

The ranking is a qualitative audit-priority judgment, not a measured score or adoption decision. No numerical scores were recorded. The considerations, in approximate priority order, are:

| Criterion | Question |
| --- | --- |
| Direct relevance | Does it address an OFA phase boundary or locked requirement? |
| Invariant compatibility | Can the concept preserve determinism, `ts_recv`, exact prices, provenance, capabilities, leakage controls, and roll resets? |
| Evidence maturity | Is the claim supported by executable source/tests rather than branding or prose? |
| Concept separability | Can the useful idea be implemented independently without importing the framework? |
| Dependency/license safety | What license and dependency questions would reuse introduce? |

Failure-case value is considered separately. That is why qapf is retained as a prominent failure archive even though Qlib ranks fifth for positive design value.

The knowledge-time examples below assume the capture point has been resolved by the event design gate. Vendor-capture `ts_recv` must not silently stand for receipt at the OFA consumer; see `vendor_capability_matrix.md` for the unresolved boundary and delay treatment. When risk and order layers exist, the causality checks should cover their pre-intervention decisions as well as features and signals.

## Ranked findings

### 1. NautilusTrader — highest architectural value

- **Source:** [`README.md`](https://github.com/BoomBloom/nautilus_trader/blob/e8daa045ab84fbe1c59e0b8a8d20ff70eacfcad0/README.md), especially the stated single event-driven architecture and shared execution/time semantics; adapter inventory begins at the same document’s integrations section.
- **Categories:** A, B, C, D, E, M, O, P, Q.
- **Concept:** One event-driven system spans research, deterministic simulation, and live execution; venue/data integrations translate external protocols through adapters into a normalized domain model.
- **OFA value / decision:** **ADAPT.** This is the closest public precedent for OFA’s required backtest/replay/paper/live semantic path and explicit adapter boundary. Study its clock, message-bus, execution, order-book, and regression-test seams during repository Phases 1, 2, 5, and 10.
- **Risks:** “Same strategy code” is not sufficient by itself—OFA additionally requires `(ts_event, sequence, ingest_index)`, `ts_recv` decisions, declared capability tiers, explicit provenance, future-only fills, and roll resets. Nautilus supports live execution and AI-training use cases that remain out of OFA scope. Its broad multi-asset model must not erase CME-specific semantics.
- **Dependency/license:** LGPL-3.0; Rust/Python/PyO3 and a large dependency surface. Study and independently implement narrow patterns; do not add it as a dependency without a separate architectural and license review.

### 2. machine-learning-for-trading — strongest temporal/leakage reference

- **Source:** [`02_financial_data_universe/14_point_in_time_validation.py`](https://github.com/BoomBloom/machine-learning-for-trading/blob/701fcc7ba83b3ac3b58c9ccbb3082a958f13d28d/02_financial_data_universe/14_point_in_time_validation.py).
- **Categories:** B, I, J, O, Q.
- **Concept:** Explicitly distinguishes event time from knowledge time, demonstrates centered-window leakage, shows that a naïve correlation heuristic misses obvious leaks, and uses data vintages for point-in-time macro values.
- **OFA value / decision:** **ADAPT**, but defer implementation until both the CanonicalEvent representation gate and the Feature/Lookback gate define the necessary contracts. The proposed test has two independent parts:
  1. **Replay ordering:** verify only that input events are processed by `(ts_event, sequence, ingest_index)`, including equal timestamps and reordered physical input. This is not a decision-time leakage test.
  2. **Knowledge-time intervention:** define each event’s effective knowledge time as observed `ts_recv`, or `ts_event + assumed_feed_delay_ns` when receive time is unavailable, with that fallback recorded in the run. Choose a decision cutoff `D`; run a baseline and a counterfactual that changes only information whose effective knowledge time is after `D`; compare only feature/signal outputs whose decision timestamp is at or before `D`. Those pre-intervention outputs must be identical. Outputs after `D` are expected to differ and must not be asserted invariant. Split-boundary variants must also preserve declared warm-up, label-horizon purge, and embargo state.
  Require release/vintage semantics for any later macro context. This test design is relevant to repository Phases 3–6 but must not prematurely define either deferred contract.
- **Risks:** Notebook demonstrations are educational, batch/dataframe-centric, and often daily-equity focused. They do not prove OFA’s event-stream timing or futures transferability. Correlation is never a sufficient leakage detector.
- **Dependency/license:** MIT, but examples depend on Polars/Plotly/provider APIs. Reimplement test ideas with existing OFA tools; no dependency implication.

### 3. Freqtrade — differential leakage testing, not an event model

- **Sources:** [`docs/lookahead-analysis.md`](https://github.com/BoomBloom/freqtrade/blob/f1e0e5844c85b71b43f60be2fbe50d449c471a6d/docs/lookahead-analysis.md) and [`docs/advanced-orderflow.md`](https://github.com/BoomBloom/freqtrade/blob/f1e0e5844c85b71b43f60be2fbe50d449c471a6d/docs/advanced-orderflow.md).
- **Categories:** D, G, I, O, Q.
- **Concept:** Re-run a baseline and signal-sliced variants, then compare indicators and trades to expose future dependence. The order-flow feature builds candle-level trades, footprint bins, imbalances, and delta.
- **OFA value / decision:** **ADAPT.** Retain the differential falsification principle, but implement the OFA-specific knowledge-time intervention described above only after the named representation and feature gates. Treat footprint/stacked-imbalance definitions only as hypothesis seeds for repository Phase 4.
- **Risks:** Its documentation explicitly says the full dataframe is populated up front and the order-flow feature is beta. Candle bins, floats, crypto trade semantics, whole-frame calculations, and cached computed columns conflict with OFA’s streaming-only production features, exact tick prices, and capability/provenance model.
- **Dependency/license:** GPL-3.0 and a large crypto-bot runtime. No code reuse or dependency.

### 4. Lean — regression and boundary precedent

- **Sources:** [`Algorithm.CSharp/AutomaticIndicatorWarmupDataTypeRegressionAlgorithm.cs`](https://github.com/BoomBloom/Lean/blob/b0006b29a26f41f48dcf5d436d15ad425f6fc9dc/Algorithm.CSharp/AutomaticIndicatorWarmupDataTypeRegressionAlgorithm.cs), [`Algorithm.CSharp/BacktestingAsynchronousOrdersRegressionAlgorithm.cs`](https://github.com/BoomBloom/Lean/blob/b0006b29a26f41f48dcf5d436d15ad425f6fc9dc/Algorithm.CSharp/BacktestingAsynchronousOrdersRegressionAlgorithm.cs), and the [`Brokerages/`](https://github.com/BoomBloom/Lean/tree/b0006b29a26f41f48dcf5d436d15ad425f6fc9dc/Brokerages) boundary.
- **Categories:** A, B, C, D, E, F, O, P, Q.
- **Concept:** Large executable regression corpus around warm-up, asynchronous orders, brokerage models, fill behavior, universes, and reference data; broker-specific behavior is isolated behind brokerage models.
- **OFA value / decision:** **ADAPT** the use of scenario algorithms as executable golden regressions and the separation of external adapters from engine state. Derive an attributed edge-case checklist from the cited scenarios, then implement independent OFA-native fixtures for sessions, roll, order transitions, partial fills, cancel/replace, and replay parity; do not translate or copy Lean tests.
- **Risks:** Lean’s broad bar/data-universe abstractions, C#/Python dual surface, live broker support, corporate-action semantics, and default models are not OFA specifications. An existing fill model is not evidence for CME matching rules or historical queue position.
- **Dependency/license:** Apache-2.0; very large .NET engine. Study only at source level; no dependency.

### 5. Qlib — recorder vocabulary and simulation decomposition only

- **Sources:** [`qlib/workflow/recorder.py`](https://github.com/BoomBloom/qlib/blob/79633dd9506ea689e5400dea0197717b5b3d74b7/qlib/workflow/recorder.py) and [`qlib/backtest/executor.py`](https://github.com/BoomBloom/qlib/blob/79633dd9506ea689e5400dea0197717b5b3d74b7/qlib/backtest/executor.py).
- **Categories:** A, B, D, E, F, I, J, M, P, Q.
- **Concept:** Run recorder with statuses, parameters, metrics, and artifacts; executor separates trade decision, account, exchange, calendar, and nested execution levels.
- **OFA value / decision:** **ADAPT** the vocabulary of a run recorder and separated simulator components for repository Phases 5–7. **STUDY ONLY** optimizer/risk-model implementations after OFA methodology is specified.
- **Risks:** Recorder is MLflow-coupled; executor is pandas/time-step oriented, uses floating amounts, a mutable default dictionary, and documented shallow-copy/shared-position behavior. Its factor engine and equity ML assumptions do not satisfy OFA’s streaming/event/capability/timing rules.
- **Dependency/license:** MIT but substantial Python/Cython/MLflow/scientific stack. Do not add as a dependency.

### 6. qapf — high-value failure archive, wrong target architecture

- **Source:** [`README.md`](https://github.com/BoomBloom/qapf/blob/f7f3ca61633c8dbe8dd6a72fb8ee6b81776eec33/README.md).
- **Categories:** A, D, I, J, K, L, M, O, P, Q.
- **Concept:** Separates TradingAgents’ LLM judgment graph from Qlib’s math/backtest layer; records a silent empty-result factor-engine failure, dependency-pin cascade, stale data, and a macOS multiprocessing re-import failure. It explicitly observes that TradingAgents’ “prop firm” framing is not quantitative rigor.
- **OFA value / decision:** **STUDY ONLY.** Retain the attributed lessons—record failed spikes and distinguish claimed from executed capability—in OFA’s own engineering process. Relevant to all design gates and especially repository Phases 6–8.
- **Risks:** Its mission is a 16-agent autonomous prop firm and it proposes composing LLM judgments with trading machinery. That violates OFA’s deliberately small research-agent roster and hard hot-path boundary. Several README conclusions are local experiments, not upstream guarantees.
- **Dependency/license:** No repository license detected. It vendors/forks large reference trees and proposes numerous dependencies. Do not copy or depend on it.

### 7. AgenticTrading — negative implementation case; independently specify baseline identity

The baseline fields and rejection conditions below are design proposals for the later validation gate, not approved contracts. That gate must determine applicability and explicit absent/not-applicable values; this audit does not require every baseline to consume every listed field.

The inspected worker keys reuse only by `(start_date, end_date, mode)`, can drop work on queue overflow or process restart, and logs failures without propagating a validation failure. The useful lesson is to make identity completeness and failure handling explicit.

- **Sources:** [`dashboard/backend/domain/backtesting/baseline_worker.py`](https://github.com/BoomBloom/AgenticTrading/blob/70239c32b29218c4d52ae989936a82578b8ba698/dashboard/backend/domain/backtesting/baseline_worker.py), [`currency.py`](https://github.com/BoomBloom/AgenticTrading/blob/70239c32b29218c4d52ae989936a82578b8ba698/dashboard/backend/domain/backtesting/currency.py), and [`LICENSE`](https://github.com/BoomBloom/AgenticTrading/blob/70239c32b29218c4d52ae989936a82578b8ba698/LICENSE).
- **Categories:** D, F, I, K, L, M, N, O, Q.
- **Concept:** The repository deduplicates baseline work by a run configuration and preserves native/reporting-currency fields, but does so through a daemon worker and float-valued currency context.
- **OFA value / decision:** **STUDY ONLY as a negative implementation case.** Do not adapt its cache key, daemon, or currency code. Independently define an OFA baseline identity as a canonical hash over the complete immutable experiment identity: baseline generator/version; dataset and partition-manifest hashes; capability/provenance record; instrument, venue, session, and date range; event/feature/label/schema versions; strategy/hypothesis family where applicable; split scheme, segments, purge, embargo, warm-up, boundary and holdout rules; costs, slippage, order latency, assumed feed delay, fill/queue model; initial capital and exact currency/FX source plus as-of policy; code revision; and RNG algorithm/seed for any permitted stochastic statistic. Results and source/native values remain immutable artifacts linked to that identity.
- **Fail-closed requirement:** Refuse generation or reuse when any identity field is missing/unknown, a capability is insufficient, FX history/as-of provenance is absent, stored metadata disagrees with the requested identity, an artifact is partial, or one identity resolves to non-byte-identical outputs. Cache hits must verify the full canonical identity and artifact hashes; scheduling order must not affect bytes.
- **Risks:** Background daemon scheduling can be nondeterministic; rates and money are floats; nearest-prior-date FX fallback is implicit policy; the platform includes live agent execution. All conflict with OFA unless independently redesigned behind exact types and explicit point-in-time/capability rules.
- **Dependency/license:** Custom **OpenMDW-1.0** license covering “Model Materials,” including related software and artifacts; it is not a standard permissive SPDX grant and includes notice and patent-litigation terms. No copying or dependency; legal review would be required for any reuse.

### 8. AI-Trader — append-like experiment events, not trustworthy identities

- **Source:** [`service/server/experiment_events.py`](https://github.com/BoomBloom/AI-Trader/blob/d03ff6c056b32ced735adf7c19ed8175adb1c8df/service/server/experiment_events.py) and its [`research/schemas/`](https://github.com/BoomBloom/AI-Trader/tree/d03ff6c056b32ced735adf7c19ed8175adb1c8df/research/schemas) catalog.
- **Categories:** J, K, L, M, N, Q.
- **Concept:** Structured experiment events capture actor, target, object, market, experiment, variant, metadata, and creation time; schemas support research exports.
- **OFA value / decision:** **ADAPT** the explicit actor/object/variant event vocabulary for immutable research lineage and agent-run audit in repository Phases 7–8.
- **Risks:** The event ID is random UUID and timestamp is wall-clock; JSON uses `default=str`; the insert is described as immutable but the shown helper does not make a hash chain or prove append-only storage. OFA must use canonical serialization, stable content identity where appropriate, controlled timestamps, schema versions, and parent lineage. Direct agent-native trading is **REJECTED**.
- **Dependency/license:** No detected license; Node/Python/services stack. No code reuse.

### 9. OpenBB — provider-extension boundary

- **Source:** [`openbb_platform/core/openbb_core/provider/abstract/provider.py`](https://github.com/BoomBloom/OpenBB/blob/3e071fcc2cd9f891cac6040ae60296dba76dab46/openbb_platform/core/openbb_core/provider/abstract/provider.py).
- **Categories:** A, C, J, N, P, Q.
- **Concept:** Provider entry points declare names, credentials, instructions, and a mapping from standard query models to fetchers.
- **OFA value / decision:** **ADAPT** only the registry/boundary concept: acquisition adapters should declare supported operations and requirements, while canonical capabilities remain verified per dataset partition rather than inferred from adapter registration (repository Phase 1).
- **Risks:** A standard response schema does not prove equivalent timestamp, sequence, depth, aggressor, or provenance semantics. OpenBB is analyst-data oriented and network/provider heavy, not a deterministic trading path.
- **Dependency/license:** Root [`LICENSE`](https://github.com/BoomBloom/OpenBB/blob/3e071fcc2cd9f891cac6040ae60296dba76dab46/LICENSE) states all repository files are **AGPL-3.0**. Network-copyleft implications require legal review for reuse. Do not copy or depend on the platform.

### 10. Pantheon-Trades — lifecycle and human promotion precedent

- **Sources:** [`docs/STRATEGY_LIFECYCLE.md`](https://github.com/BoomBloom/Pantheon-Trades/blob/b700fe3c76e9a79330c6c606e740fa66f02935be/docs/STRATEGY_LIFECYCLE.md) and [`docs/RISK_POLICY.md`](https://github.com/BoomBloom/Pantheon-Trades/blob/b700fe3c76e9a79330c6c606e740fa66f02935be/docs/RISK_POLICY.md).
- **Categories:** E, F, H, I, K, L, M, N, Q.
- **Concept:** Explicit strategy lifecycle, archived termination/post-mortem, paper/live routing, human promotion review, stale-data/spread/liquidity/exposure gates, and drawdown-triggered pauses.
- **OFA value / decision:** **ADAPT** lifecycle transition guards, permanent rejection/post-mortem records, and human approval checkpoints for Phases 7, 8, and 10. Risk must remain deterministic and authoritative.
- **Risks:** Its paper gate can be as small as ten trades; it promotes agent deliberation toward live prediction-market execution and adds blockchain/multisig machinery. Those are inadequate or irrelevant for OFA. The documented Kelly formula and thresholds require independent quantitative review and preregistration; never inherit them as defaults.
- **Dependency/license:** MIT, but polyglot web/service/contracts stack. No dependency.

### 11. TradingAgents — typed research debate, direct trade decisions rejected

- **Source:** [`tradingagents/graph/trading_graph.py`](https://github.com/BoomBloom/TradingAgents/blob/a33fd4c0f134485a43553a2c23a63cb14adbd88f/tradingagents/graph/trading_graph.py).
- **Categories:** J, K, L, M, O, Q.
- **Concept:** Graph-shaped analyst/researcher/risk debate, checkpoint invalidation keyed by graph-shape inputs, deferred outcome reflection, and structured state propagation.
- **OFA value / decision:** **STUDY ONLY** checkpoint compatibility and adversarial role separation for Phase 8. Any useful output must terminate in typed research/specification/critique records reviewed by a human.
- **Risks:** It produces a final BUY/SELL/HOLD trade decision and performs network lookups with fail-open behavior. LLM “risk managers” and agent decisions cannot enter OFA’s deterministic signal/risk/order path. Graph orchestration remains deferred.
- **Dependency/license:** Apache-2.0, LangGraph/model/provider dependencies and network calls. No dependency before Phase 8, and likely no wholesale adoption then.

### 12. OrderFlowTradingAlgoSierraChart — hypothesis seeds, implementation rejected

- **Source:** [`OrderFlow.cpp`](https://github.com/BoomBloom/OrderFlowTradingAlgoSierraChart/blob/8447e64eeef8a96252f8ddab3c8b97a343195d83/OrderFlow.cpp).
- **Categories:** G, H, E, F, Q.
- **Concept:** Cumulative delta, bar-level volume imbalance, fair-value-gap, ATR/volatility, time-window, and risk-threshold rules.
- **OFA value / decision:** **STUDY ONLY** as a list of claims to turn into falsifiable hypotheses with exact definitions and baselines. **REJECT** the implementation.
- **Risks:** It uses `float` throughout prices, volumes, ratios, and thresholds; bar arrays collapse event timing; cumulative state has no explicit gap/session/roll reset; aggressor semantics and data provenance are implicit; “professional-grade” is unsupported; thresholds appear arbitrary; no leakage, capability, execution, or statistical validation is evident.
- **Dependency/license:** No detected license and Sierra Chart ACSIL coupling. No copying.

### 13. backtesting.py — small pedagogical comparison only

- **Source:** [`backtesting/backtesting.py`](https://github.com/BoomBloom/backtesting.py/blob/ca2e2611621e472542ba90f7243a1fa06a7d7108/backtesting/backtesting.py) and [`backtesting/test/_test.py`](https://github.com/BoomBloom/backtesting.py/blob/ca2e2611621e472542ba90f7243a1fa06a7d7108/backtesting/test/_test.py).
- **Categories:** D, E, I, N, O, Q.
- **Concept:** Compact, readable bar backtest and broad tests expose a useful checklist of simple accounting scenarios.
- **OFA value / decision:** **STUDY ONLY.** Use the cited cases to write an attributed requirements checklist, then independently derive hand-computable OFA-native PnL fixtures and result-presentation tests in repository Phases 5–6. Its numerical outputs are not an OFA oracle.
- **Risks:** OHLC/dataframe simulation cannot represent OFA’s order-flow timing, receive clock, sequence, book, queue, or partial-fill semantics. Optimizer workflows invite repeated-search bias.
- **Dependency/license:** AGPL-3.0. No code reuse or dependency.

### 14. dsh-quant — research/tool separation as a discussion prompt

- **Sources:** [`quant-history/P_RESEARCH_LINKUP.md`](https://github.com/BoomBloom/dsh-quant/blob/bbc422d48328d4652ef7b8225bfafd2ae4158983/quant-history/P_RESEARCH_LINKUP.md), [`src/dsh-data/quality.ts`](https://github.com/BoomBloom/dsh-quant/blob/bbc422d48328d4652ef7b8225bfafd2ae4158983/src/dsh-data/quality.ts), and [`src/dsh-execution/trade-quality.ts`](https://github.com/BoomBloom/dsh-quant/blob/bbc422d48328d4652ef7b8225bfafd2ae4158983/src/dsh-execution/trade-quality.ts).
- **Categories:** C, E, F, I, J, K, L, M, N, P, Q.
- **Concept:** Separates a research corpus/report layer from tools and trading modules; exposes modular data-quality/execution/risk areas.
- **OFA value / decision:** **STUDY ONLY.** The research-as-data framing is directionally compatible with OFA’s evidence records, but claims must be traced to primary papers rather than cross-repository promotional notes.
- **Risks:** “AI-native Quant OS,” plugin breadth, and research→tools→live framing encourage scope explosion and weak authority boundaries. Module presence does not prove deterministic, statistically valid, or exchange-realistic behavior.
- **Dependency/license:** MIT, TypeScript/plugin ecosystem. No dependency.

### 15. Open-source catalogs — discovery aids, never evidence

- **Sources:** [`awesome-systematic-trading/README.md`](https://github.com/BoomBloom/awesome-systematic-trading/blob/1ce1eb2b7752aae1a7357afa47885c8bb8291404/README.md), [`best-of-algorithmic-trading/README.md`](https://github.com/BoomBloom/best-of-algorithmic-trading/blob/e281dccbc2ca88e47995858acab20de5270484de/README.md), [`awesome-quant/README.md`](https://github.com/BoomBloom/awesome-quant/blob/d2c678f3855a88bbb687d77cb8a693f7de209ddf/README.md), [`EliteQuant/README.md`](https://github.com/BoomBloom/EliteQuant/blob/61e911dcf16530201f2066db26cd5a8842916663/README.md), and [`Quant-Developers-Resources/README.md`](https://github.com/BoomBloom/Quant-Developers-Resources/blob/69ea984a3d6b2430ea537c571eff65ff57b18729/README.md).
- **Categories:** J, P, Q.
- **Concept:** Broad discovery indexes for libraries, papers, courses, datasets, and systems.
- **OFA value / decision:** **STUDY ONLY** as search seeds during phase-specific literature work. Every candidate must be re-verified against its upstream source, current license, exact version, and primary evidence.
- **Risks:** Popularity/rank is not rigor; links age; licenses and behavior drift; curated descriptions are secondary sources. Never cite a catalog as evidence for an edge or capability.
- **Dependency/license:** Mixed or absent at the catalog level; every linked project requires separate review.

## Complete roadmap-repository disposition

This table ensures that every repository named by the master roadmap is accounted for, including lower-yield repositories not worthy of a top-ranked detailed section.

| Repository (pinned source) | Categories | Decision | Useful finding / OFA phase | Principal reason not to copy |
| --- | --- | --- | --- | --- |
| [qapf](https://github.com/BoomBloom/qapf/tree/f7f3ca61633c8dbe8dd6a72fb8ee6b81776eec33) | A,D,I,J,K,L,M,O,Q | STUDY ONLY | Failure logs and claimed-vs-tested capability; all gates | Autonomous 16-agent target, no detected license |
| [TradingAgents](https://github.com/BoomBloom/TradingAgents/tree/a33fd4c0f134485a43553a2c23a63cb14adbd88f) | J,K,L,M,O,Q | STUDY ONLY | Typed critique/checkpoint ideas; Phase 8 | Direct LLM trade decisions and network dependency |
| [qlib](https://github.com/BoomBloom/qlib/tree/79633dd9506ea689e5400dea0197717b5b3d74b7) | A,B,D,E,F,I,J,M,P,Q | ADAPT | Recorder vocabulary and component seams; Phases 5–7 | Batch/float/MLflow semantics; large stack |
| [OpenBB](https://github.com/BoomBloom/OpenBB/tree/3e071fcc2cd9f891cac6040ae60296dba76dab46) | A,C,J,N,P,Q | ADAPT | Provider registry concept; repository Phase 1 | AGPL-3.0; normalized query model does not prove feed equivalence |
| [awesome-systematic-trading](https://github.com/BoomBloom/awesome-systematic-trading/tree/1ce1eb2b7752aae1a7357afa47885c8bb8291404) | H,J,P,Q | STUDY ONLY | Search seeds; phase-specific research | Secondary catalog, not evidence |
| [Vibe-Trading `agent/backtest/engines/base.py`](https://github.com/BoomBloom/Vibe-Trading/blob/7329cb096a7361f975f532c77fef5c93e31561c5/agent/backtest/engines/base.py) | D,E,F,K,L,N,Q | REJECT | Compare market-hook/config seams only; Phase 8/10 | Personal agent spans backtest through live markets; scope and authority conflict |
| [nautilus_trader `README.md`](https://github.com/BoomBloom/nautilus_trader/blob/e8daa045ab84fbe1c59e0b8a8d20ff70eacfcad0/README.md) | A,B,C,D,E,M,O,P,Q | ADAPT | Event parity, adapters, clocks, regression corpus; Phases 1–5/10 | Huge LGPL polyglot engine and live surface |
| [pwb-alphaevolve](https://github.com/BoomBloom/pwb-alphaevolve/blob/cf760d4bae4c7d3a3304b52862f26fef1ce73100/alphaevolve/evaluator/backtest.py) | D,H,I,K,O,Q | REJECT | Evaluator containment is a negative case; post-Phase 9 only | Automated strategy evolution/selection magnifies overfitting and holdout mining |
| [best-of-algorithmic-trading](https://github.com/BoomBloom/best-of-algorithmic-trading/tree/e281dccbc2ca88e47995858acab20de5270484de) | J,P,Q | STUDY ONLY | Discovery index | Ranked secondary catalog; CC-BY-SA content implications |
| [machine-learning-for-trading](https://github.com/BoomBloom/machine-learning-for-trading/tree/701fcc7ba83b3ac3b58c9ccbb3082a958f13d28d) | B,I,J,O,Q | ADAPT | PIT/leakage/adversarial fixtures; Phases 3–6 | Educational notebooks and batch assumptions |
| [Lean](https://github.com/BoomBloom/Lean/tree/b0006b29a26f41f48dcf5d436d15ad425f6fc9dc) | A,B,C,D,E,F,O,P,Q | ADAPT | Regression scenarios and boundary seams; Phases 1–6/10 | Broad engine defaults are not CME/OFA evidence |
| [freqtrade](https://github.com/BoomBloom/freqtrade/tree/f1e0e5844c85b71b43f60be2fbe50d449c471a6d) | D,G,I,O,Q | ADAPT | Differential leakage falsifier; Phases 3–6 | GPL crypto bot, dataframe/candle/float semantics |
| [TradeMaster `configs/_base_/agents/order_execution/eteo.py`](https://github.com/BoomBloom/TradeMaster/blob/1747cc18db3fe2639af12defc80e138c51a625c0/configs/_base_/agents/order_execution/eteo.py) | C,D,E,H,I,K,P,Q | REJECT | RL benchmark taxonomy may inform falsification; post-Phase 9 | RL trading/execution optimization is explicitly deferred and dependency-heavy |
| [openalgo](https://github.com/BoomBloom/openalgo/blob/755edf69c7a1e5337a541a09225de2701e768061/audit/BROKER_API_COMPATIBILITY.md) | A,C,E,F,M,O,Q | STUDY ONLY | Broker compatibility/audit checklist; future live gate | Live broker/credential surface, AGPL, Indian-market assumptions |
| [AutoHedge `experimental/btc_agent.py`](https://github.com/BoomBloom/AutoHedge/blob/c549c7950da112286e76725d49f6a25de8fa99bd/experimental/btc_agent.py) | E,F,K,L,Q | REJECT | Agent-risk separation claims as adversarial checklist; Phase 8 | Autonomous hedge-fund/live-execution framing and thin test evidence |
| [QuantDinger](https://github.com/BoomBloom/QuantDinger/blob/366ea33c276b5307ce8428da6dcca160532635ea/backend_api_python/app/data_sources/base.py) | A,C,D,E,K,L,N,Q | STUDY ONLY | Circuit-breaker/provider UX patterns; Phase 1/8 | Multi-asset/live/agent breadth; source abstraction does not encode OFA capabilities |
| [awesome-quant `scripts/audit_readme.py`](https://github.com/BoomBloom/awesome-quant/blob/d2c678f3855a88bbb687d77cb8a693f7de209ddf/scripts/audit_readme.py) | J,O,P,Q | STUDY ONLY | Catalog maintenance tests; research discovery | No detected license; catalog is secondary evidence |
| [quant-trading](https://github.com/BoomBloom/quant-trading/blob/611b73f2c3f577ac5b28aaa19ac8c43d3236c7a5/Monte%20Carlo%20project/Monte%20Carlo%20backtest.py) | D,H,I,Q | STUDY ONLY | Simple hypothesis examples/negative fixtures; Phase 6 | Script-level bar backtests, bundled data provenance unclear, no OFA timing model |
| [QuantResearch](https://github.com/BoomBloom/QuantResearch/blob/79bbf6a8b5ad74ac2c165663b5e12eb70d76a54e/backtest/comdty_roll.py) | B,D,H,I,Q | STUDY ONLY | Commodity-roll edge cases; Phase 2 | Legacy batch scripts; roll logic must be re-derived and RESET enforced |
| [gs-quant](https://github.com/BoomBloom/gs-quant/blob/fa9dd42f0677a0d2fb5819fca6e2f67de9458c06/gs_quant/timeseries/backtesting.py) | D,F,I,J,P,Q | STUDY ONLY | Metric/risk API vocabulary; Phase 6 | Service/data coupling, floats, non-order-flow focus; Apache does not approve APIs |
| [EliteQuant `README.md`](https://github.com/BoomBloom/EliteQuant/blob/61e911dcf16530201f2066db26cd5a8842916663/README.md) | J,P,Q | STUDY ONLY | Resource discovery | List repository, not primary evidence |
| [Quant-Developers-Resources `README.md`](https://github.com/BoomBloom/Quant-Developers-Resources/blob/69ea984a3d6b2430ea537c571eff65ff57b18729/README.md) | J,P,Q | STUDY ONLY | Terminology/learning index | No detected license and uneven secondary content |
| [pyql](https://github.com/BoomBloom/pyql/blob/6d0910e9208f33520d5afa23718145fb679b3972/quantlib/sim/simulate.pyx) | D,F,I,P,Q | STUDY ONLY | Attributed numerical edge-case checklist for later risk work | Cython/QuantLib wrapper; BSD-style license plus PSF notice; not event simulation |
| [FinceptTerminal](https://github.com/BoomBloom/FinceptTerminal/blob/ffe24dd6076e73e05170b8cca24bbc6096ad4bc4/fincept-qt/docs/backtesting-provider-process.md) | A,C,D,J,K,L,N,Q | STUDY ONLY | ADRs/provider process/reporting UX; repository Phases 1/8 | Custom dual AGPL/commercial restrictions require legal review; network-heavy |
| [FinRL `docs/source/finrl_meta/Data_layer.rst`](https://github.com/BoomBloom/FinRL/blob/2334a5fe6d30629157f13c3b0319e1637e15e123/docs/source/finrl_meta/Data_layer.rst) | C,D,H,I,K,P,Q | REJECT | Data-layer taxonomy only | RL/neural optimization explicitly out of scope; dependency-heavy |
| [stockpredictionai](https://github.com/BoomBloom/stockpredictionai/blob/fc83ea9a26189cbf9e50dd809f291bc11c6263e3/readme.md) | H,K,N,Q | REJECT | Negative example for unverifiable prediction claims | GAN/LSTM prediction, no detected license, no OFA event/validation path |
| [Sequoia-X](https://github.com/BoomBloom/Sequoia-X/blob/444c0db69ff36b46ef2b22ab265051d60c16029d/sequoia_x/strategy/base.py) | C,H,N,O,Q | REJECT | Strategy-plugin test ergonomics only | Daily A-share scanner, notification/live automation, incompatible market semantics |
| [FinRL-Trading](https://github.com/BoomBloom/FinRL-Trading/blob/e65d6f0483ead7d2ef4a5fc940cdf960392a25c1/src/backtest/backtest_engine.py) | A,C,D,E,F,H,I,K,Q | REJECT | Calendar/data-store seams may seed questions; Phase 2 | AI-native/RL portfolio platform; floats and daily-equity assumptions |
| [quant-wiki](https://github.com/BoomBloom/quant-wiki/blob/f08b94e13425c234b20e2641ec525178259b8684/docs/basic/quant/%E9%99%90%E4%BB%B7%E5%8D%95%E7%B0%BF_Limit%20Order%20Book.md) | B,E,G,H,J,Q | STUDY ONLY | Terminology and bibliography seeds; Phases 4/7 | Wiki/translation material is secondary, no detected license |
| [nofx](https://github.com/BoomBloom/nofx/blob/c04697dbcc975f07eecd29977fa1c0a2262015ef/docs/architecture/AGENT_CURRENT_DESIGN.zh-CN.md) | E,F,K,L,M,N,Q | REJECT | Agent observability/checklist ideas; Phase 8 | AGPL live AI trading terminal; agent influences execution |
| [StockSharp](https://github.com/BoomBloom/StockSharp/blob/20ea9f267db4cf4fc68d799d2abc8a3c0fb9fafd/Algo.Strategies/OrderPipeline.cs) | A,B,C,D,E,F,G,O,P,Q | STUDY ONLY | Attributed order-state edge-case checklist; repository Phases 5/10 | Proprietary/EULA-governed repository: no copying; semantics not evidence |
| [backtesting.py](https://github.com/BoomBloom/backtesting.py/blob/ca2e2611621e472542ba90f7243a1fa06a7d7108/backtesting/backtesting.py) | D,E,I,N,O,Q | STUDY ONLY | Accounting-scenario checklist for independent OFA fixtures; repository Phases 5/6 | AGPL bar/dataframe simulator cannot represent event path |
| [AgenticTrading `baseline_worker.py`](https://github.com/BoomBloom/AgenticTrading/blob/70239c32b29218c4d52ae989936a82578b8ba698/dashboard/backend/domain/backtesting/baseline_worker.py) | D,F,I,K,L,M,N,O,Q | STUDY ONLY | Negative baseline-cache case; independently specify complete identity/fail-closed behavior; repository Phases 6–8 | Custom OpenMDW-1.0; live agents, floats, asynchronous workers |
| [AI-Trader `experiment_events.py`](https://github.com/BoomBloom/AI-Trader/blob/d03ff6c056b32ced735adf7c19ed8175adb1c8df/service/server/experiment_events.py) | J,K,L,M,N,Q | ADAPT | Structured experiment-event vocabulary; Phases 7–8 | No detected license; random/wall-clock identities and agent-native trading |
| [Pantheon-Trades `STRATEGY_LIFECYCLE.md`](https://github.com/BoomBloom/Pantheon-Trades/blob/b700fe3c76e9a79330c6c606e740fa66f02935be/docs/STRATEGY_LIFECYCLE.md) | E,F,H,I,K,L,M,N,Q | ADAPT | Guarded lifecycle/human promotion/post-mortem; Phases 7–10 | Prediction-market/on-chain/live complexity; weak sample gate |
| [OrderFlowTradingAlgoSierraChart](https://github.com/BoomBloom/OrderFlowTradingAlgoSierraChart/blob/8447e64eeef8a96252f8ddab3c8b97a343195d83/OrderFlow.cpp) | E,F,G,H,Q | REJECT | Hypothesis seeds only; Phase 4/6 | Floats, bar timing, implicit provenance, arbitrary thresholds, no detected license |
| [dsh-quant `P_RESEARCH_LINKUP.md`](https://github.com/BoomBloom/dsh-quant/blob/bbc422d48328d4652ef7b8225bfafd2ae4158983/quant-history/P_RESEARCH_LINKUP.md) | C,E,F,I,J,K,L,M,N,P,Q | STUDY ONLY | Research/tool separation prompts; Phases 7–8 | “Quant OS” scope and live/AI authority blur |
| [prediction-market-alpha-playbook](https://github.com/BoomBloom/prediction-market-alpha-playbook/blob/4b330bf4323de85ae517809f9282e406a56456cc/NEG_RISK_NO_CARRY.md) | B,C,D,E,F,H,I,J,Q | STUDY ONLY | Adversarial mechanism/negative-risk case-study format; Phase 7 | Different venues/asset mechanics; prose playbook is not tested CME evidence |

## Newly discovered relevant repositories

| Repository (pinned source) | Categories | Decision | Finding and limits |
| --- | --- | --- | --- |
| [deepseek-harness `README.md`](https://github.com/BoomBloom/deepseek-harness/blob/4e84901e6471b79ec0338099867ebb4606d12bb5/README.md) | A,K,L,M,O,P,Q | STUDY ONLY | Generic “everything is a plugin” harness. Potential Phase 8 test/evaluation ideas, but not a trading reference; plugin dynamism and broad agent autonomy are the wrong default for OFA. MIT does not justify a dependency. Deep source audit was not warranted because its public description and repository scope are generic agent infrastructure, not market research or deterministic trading. |
| [ruflo `README.md`](https://github.com/BoomBloom/ruflo/blob/5234333c3462640ab348363ba4a142945fd2bc47/README.md) | K,L,M,N,P,Q | REJECT | Swarm/meta-harness and adaptive-memory ideas are premature while OFA’s orchestrator is gated. The repository is large, fast-moving generic orchestration, not an OFA phase dependency. MIT; no adoption. |
| [hqchart `README.md`](https://github.com/BoomBloom/hqchart/blob/12966bf36466ae7a8d6d8cab674c9dc2dfcdf14c/README.md) | N,P,Q | STUDY ONLY | Chart interaction and pluggable-data UI may inform a much later inspectability layer. It is unrelated to deterministic research semantics and embeds China/HK/crypto/equity conventions. Apache-2.0; no current phase work. |
| [TabPFN `README.md`](https://github.com/BoomBloom/TabPFN/blob/38f574987deb5f313a832e2b42108ee3ef190e85/README.md) | H,I,P,Q | REJECT | Tabular foundation-model research may be academically interesting only after the deterministic loop exists. Learned prediction is explicitly deferred, and no deep audit was needed for current architecture. |

No newly found public repository changes OFA’s locked architecture or opens a phase gate.

## Category A–Q synthesis

| Category | Best references | Governing conclusion for OFA |
| --- | --- | --- |
| A. Architecture | NautilusTrader, Lean, qapf | One deterministic event spine with narrow adapters; keep research agents out of it. |
| B. Event/data model | NautilusTrader, Lean, machine-learning-for-trading | Preserve source semantics, event/knowledge time, exact ordering, provenance, and capabilities; no generic “L2” shortcut. |
| C. Market-data adapters | NautilusTrader, OpenBB, openalgo | Adapt registry/adapter seams only after vendor evidence; an adapter’s existence does not prove historical fields. |
| D. Backtesting/simulation | NautilusTrader, Lean, Qlib, Freqtrade | Shared event semantics and differential leakage tests; reject bar/dataframe substitutes for order flow. |
| E. Execution | Lean, NautilusTrader, StockSharp | Mine state-machine tests, not default exchange mechanics; queue/fill claims require verified evidence. |
| F. Risk | Pantheon, AgenticTrading, Qlib | Deterministic fail-closed gates and immutable policies; independently validate formulas and thresholds. |
| G. Order-flow/microstructure | Freqtrade, OrderFlowTradingAlgoSierraChart, StockSharp | Hypothesis seeds only; exact definitions, aggressor provenance, tick prices, gap/reset/roll behavior, and tests are mandatory. |
| H. Strategy ideas | Catalogs, QuantResearch, prediction-market playbook | Inputs to formalization and falsification, never ready-made strategies. |
| I. Validation/statistics | machine-learning-for-trading, Freqtrade, qapf, Qlib | Prefer adversarial invariance tests and preregistered baselines; record silent failures and negative results. |
| J. Research tooling | Qlib recorder, AI-Trader schemas, catalogs | Structured evidence and immutable lineage; primary sources replace catalog descriptions. |
| K. Agent architecture | TradingAgents, AI-Trader, qapf | Typed research outputs can be studied; agents never issue authoritative numerical or trade decisions. |
| L. Orchestration | TradingAgents, qapf, ruflo | Remains deferred; checkpoint compatibility is useful but graph complexity is not justification. |
| M. Observability/audit | AI-Trader events, Qlib recorder, Pantheon lifecycle | Capture versions, parents, inputs, outputs, status, errors, and immutable artifacts; avoid wall-clock/random identity as reproducibility proof. |
| N. UI/reporting | FinceptTerminal, hqchart, Pantheon | Human inspectability matters; dashboards are downstream and cannot become the source of truth. |
| O. Testing/reproducibility | Lean, NautilusTrader, Freqtrade, qapf | Scenario regressions, differential leakage attacks, deterministic artifacts, and clean-environment tests. |
| P. Useful libraries | None approved | Every framework is too broad or semantically mismatched; reuse ideas, not dependencies. |
| Q. Dangerous patterns | Present across most agent/bot/bar repositories | Direct LLM trading, live-by-default surfaces, floats, look-ahead-prone frames, arbitrary thresholds, weak sample gates, RL search, generic feed semantics, and unverifiable “professional-grade” claims. |

## Phase-specific recommendations

1. **Repository Phase 1 — data spine:** Consult Nautilus adapter boundaries and OpenBB’s provider registry solely for interface questions. Vendor capability facts must still come from primary vendor/exchange documents. Add no framework.
2. **Repository Phase 2 — reference/session/roll:** Use cited Lean and QuantResearch scenarios to create an attributed edge-case checklist. CME/vendor primary sources remain authoritative; independently implement OFA fixtures and enforce price-level `RESET` at roll.
3. **Repository Phase 3 — feature design gate:** Bring forward machine-learning-for-trading’s point-in-time counterexamples and Freqtrade’s differential principle only after the CanonicalEvent and Feature/Lookback contracts are approved. Test replay ordering independently. For causality, intervene by effective knowledge time and assert invariance only for outputs at or before the decision cutoff.
4. **Repository Phase 4 — order flow:** Treat Freqtrade and Sierra Chart code as hypothesis catalogs. Require exact tick-grid definitions, declared input capabilities, explicit aggressor provenance, `UNKNOWN`, gap/reset behavior, and independently derived golden event fixtures.
5. **Repository Phase 5 — labels/strategy/backtester:** Build an attributed checklist from Lean/Nautilus/StockSharp scenarios, but independently derive OFA’s order states, same-timestamp rules, arrival clock, fills, queue simulations, and fixtures from the approved event model and verified exchange semantics.
6. **Repository Phase 6 — validation:** Define baseline identity completely and fail closed as specified in the AgenticTrading negative-case finding; do not copy its cache. Implement the approved knowledge-time leakage falsifier, never bar-engine optimization or RL search, and preserve label-horizon purge and warm-up requirements.
7. **Repository Phase 7 — registry:** Adapt Qlib’s recorder vocabulary and AI-Trader’s event fields into canonical, schema-versioned, append-only OFA artifacts with content lineage. Do not copy MLflow coupling, UUID-as-proof, or `default=str` serialization.
8. **Repository Phase 8 — agents:** Study typed state/checkpoint invalidation from TradingAgents and post-mortem/lifecycle ideas from Pantheon. Preserve three research-only agent types, human orchestration, and deterministic authority. No network/model import may reach the hot path.
9. **Repository Phase 10 and any later paper/live work:** Nautilus and Lean remain attributed edge-case references, not dependencies, test oracles, or exchange truth. Pantheon/openalgo/nofx are primarily warnings about the blast radius of credentials and live execution.

## Explicit rejections and unresolved implications

- **No dependency recommendation:** This audit does not authorize NautilusTrader, Lean, Qlib, MLflow, LangGraph, Freqtrade, Backtesting.py, OpenBB, QuantLib, or any agent framework.
- **No vendor recommendation:** Adapter lists do not resolve OFA V1–V8 and must not influence vendor selection without primary capability evidence.
- **No strategy recommendation:** Cumulative delta, imbalance, FVG, RL, GAN/LSTM, Kelly sizing, and prediction-market mechanisms remain hypotheses or rejected implementations, not approved OFA strategies.
- **License caution:** [`AgenticTrading/LICENSE`](https://github.com/BoomBloom/AgenticTrading/blob/70239c32b29218c4d52ae989936a82578b8ba698/LICENSE) is custom OpenMDW-1.0; [`OpenBB/LICENSE`](https://github.com/BoomBloom/OpenBB/blob/3e071fcc2cd9f891cac6040ae60296dba76dab46/LICENSE) is AGPL-3.0; [`pyql/LICENSE.txt`](https://github.com/BoomBloom/pyql/blob/6d0910e9208f33520d5afa23718145fb679b3972/LICENSE.txt) is BSD-style and contains a PSF-compatible notice for bundled `traits/protocols` material; [`FinceptTerminal/LICENSE`](https://github.com/BoomBloom/FinceptTerminal/blob/ffe24dd6076e73e05170b8cca24bbc6096ad4bc4/LICENSE) asserts dual AGPL/commercial terms plus additional commercial/internal-use and trade-dress restrictions that require legal review; [`StockSharp/LICENSE`](https://github.com/BoomBloom/StockSharp/blob/20ea9f267db4cf4fc68d799d2abc8a3c0fb9fafd/LICENSE) declares the repository proprietary and governed by a changing external EULA, so **no code may be copied**. Repositories still lacking a detected license include `qapf`, `AI-Trader`, `OrderFlowTradingAlgoSierraChart`, `awesome-quant`, `Quant-Developers-Resources`, and `quant-wiki`; they must not supply copied code. All GPL/AGPL/LGPL/custom terms require legal review before contemplated reuse.
- **Public-only limitation:** Private BoomBloom repositories could not be enumerated without credentials, which were neither requested nor used. `P-Research` and `QuantMind` are external inspirations named by the roadmap, not BoomBloom-owned repositories; they were intentionally not substituted into this owner audit and require their own primary-source review when their phase opens.
- **Repository-size and fork-divergence limitation:** The giant engines and content collections were targeted rather than exhaustively line-reviewed, and fork parent/ahead/behind/divergence was not exhaustively resolved. Before any cited concept influences a phase’s final design, the responsible phase review must inspect the exact fork and upstream modules, attribute authorship, compare their tests and revisions, and re-check all applicable license notices.

## Screened-out owner repositories

The current public inventory also contained repositories with no material OFA trading/quant/research architecture content: `Airgead-Banking-Investment-Calculator`, `CS-305-Software-Security`, `CS250`, `CS255`, `CS300-ABCU-Advising-Program`, `CS320-final-project`, `CS340-Grazioso-Salvare-Dashboard`, `CS_230_Project_Two_Design_Document`, `dd`, `graph-theory`, `lab-agile-planning`, `snhu-cs360-portfolio`, `sofle-hybrid-ergomech-zmk`, `ui-ux-pro-max-skill`, and `zmk-sofle-MA`. They were enumerated but excluded after metadata/scope screening. `Order-Flow-AI` itself is the target, not a reference repository.

## Final disposition

The audit supports OFA’s existing direction rather than changing it. Mature engines validate the value of a single event-driven path and adapter boundaries; leakage-focused projects validate aggressive temporal tests; lineage projects suggest useful record fields. Conversely, the many autonomous-agent and bar-backtest repositories demonstrate why OFA’s deterministic authority, explicit capabilities/provenance, exact time/price semantics, preregistration, and phase gates must remain stronger than the references.

The report should be treated as a phase-review index. Each later phase must re-open only its relevant pinned sources, compare them with current upstream, verify primary market/vendor evidence, and independently design the smallest OFA-native implementation.
