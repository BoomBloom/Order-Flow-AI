# Limitations and UNVERIFIED Register

Status: **open register.** Every entry is either verified (with verifier,
date, and source) or blocking something specific. Nothing here may be
promoted to an assumption by silence.

Two categories:

- **UNVERIFIED** — we do not know yet. Must be resolved before the dependent
  work is trusted.
- **KNOWN LIMITATION** — we do know, and it cannot be fixed with the data
  available. Must be stated in every affected report.

---

## 1. UNVERIFIED — data vendor and feed

| # | Item | Blocks | Verified by / date / source |
| --- | --- | --- | --- |
| V1 | Vendor identity, tiers, cost, and history depth | Phase 1 | — |
| V2 | **Whether the chosen vendor supplies `ts_recv` historically** | The decision clock (`architecture.md` §9.1); every backtest | — |
| V3 | Whether aggressor side is exchange-supplied (`OBSERVED`) for NQ/ES/6E | Every order-flow feature | — |
| V4 | MBP-10 availability, depth, and truncation behaviour under burst | All liquidity features | — |
| V5 | MBO availability and cost | Queue-level modelling; Phase 4 liquidity work | — |
| V6 | Vendor sequence-number semantics: per-channel, resets, documented gap tolerance | L1a checks; the ordering key | — |
| V7 | Storage volume per instrument-day at each data tier | Scaling beyond one instrument | — |
| V8 | Live feed vendor and its capability record relative to the historical one | Phase 10 paper trading | — |

If V2 resolves to "not supplied", the decision clock rests on
`assumed_feed_delay_ns` for all historical work. That is a configured
assumption, mandatory to stress-test, and reported with every dependent
result.

---

## 2. UNVERIFIED — exchange and instrument semantics

| # | Item | Blocks | Verified by / date / source |
| --- | --- | --- | --- |
| E1 | **CME matching algorithm for NQ/ES/6E outrights.** Believed FIFO price-time priority; unverified against the CME rulebook. Allocation algorithms vary by product. | Every simulated queue position; all limit-order conclusions | — |
| E2 | Priority effect of order modification: size increase, size decrease, price change | The limit-order fill model | — |
| E3 | **6E session structure.** Not assumed to match the equity-index segmentation. | `SessionDef` for 6E; any 6E research | — |
| E4 | Holiday and early-close calendar source and its versioning | Phase 2 | — |
| E5 | Implied-order treatment in the trade and book feeds | Order-flow and liquidity features | — |
| E6 | Settlement and daily-statistic publication timing relative to session close | Any feature referencing settlement | — |

**No queue model may be relied upon for a research conclusion until E1 and E2
are verified.** Until then, limit-order results are exploratory only.

---

## 3. UNVERIFIED — costs and execution environment

| # | Item | Blocks |
| --- | --- | --- |
| C1 | Commission, exchange, clearing, and NFA fee schedule for the intended broker | Gate 6 economic significance |
| C2 | Realistic decision-to-exchange order latency for the intended setup | Order-latency stress; every fill |
| C3 | Achievable colocation/connectivity assumptions, if any | Whether latency-sensitive hypotheses are researchable at all |

---

## 4. UNVERIFIED — platform

| # | Item | Blocks |
| --- | --- | --- |
| P1 | LLM provider, models per routing role, and budget | Phase 8 |
| P2 | Compute environment (local vs cloud) and available disk | Data-tier and history-depth decisions |

---

## 5. DEFERRED — decisions taken deliberately, not yet made

Each of these is a decision the project has consciously postponed rather than
overlooked. A deferral is closed by making the decision at its named gate, not
by an implementer picking an answer while writing adjacent code.

| # | Deferred item | Why it is not decided | Decided at |
| --- | --- | --- | --- |
| D1 | **Final `RunId` grammar.** The type enforces only single-path-component safety: non-empty, no path separator, not `.` or `..`, no whitespace or control character, UTF-8 encodable. The permitted alphabet, any maximum length, a Windows drive or alternate-stream colon, and the reserved device names (`CON`, `NUL`, `COM1`…) are **not** constrained. | The grammar belongs to the code that mints run ids, which does not exist. Fixing it now would be guessing. | Run lifecycle / storage design |
| D2 | **`feature_id` construction.** `docs/architecture.md` §6.4 fixes the format as `name@version#params_hash`, but nothing constructs one. | `docs/roadmap.md` places `feature_id` hashing in Phase 3. Freezing the feature name grammar and version syntax before `features/base.py` and the concrete parameter model exist would lock two things by accident. | Phase 3 |
| D3 | **`Feature` protocol and `Lookback`.** Neither is declared. `RollPolicy` and `ResetReason` are, because their members are fully specified. | The `Feature` signature names `FeatureParams`, `Lookback`, `StreamGap`, `FeatureUpdate` and `FeatureState`, none of which the specification defines beyond the name. `Lookback` additionally carries a real conflict: `docs/features/TEMPLATE.md` §3 allows event-count, volume or time windows and the worked example uses whole prior sessions, while `docs/research_protocol.md` §4.3 and `docs/validation_protocol.md` require warm-up to be "at least the longest lookback" — a scalar maximum over dimensions that cannot be converted into one another without a data-dependent assumption. | A dedicated Feature Engine / `Lookback` design gate, before Phase 3 |
| D4 | **`CanonicalEvent` envelope representation.** The protocol is not declared. | Whether `ts_event`, `instrument_id`, `trade_date` and `provenance_id` are raw `int`/`date` or the core value types is a genuine trade-off: the value types exist to stop exactly these fields being confused, but `docs/architecture.md` §16 item 1 forbids per-event validation on a path processing millions of events. Separately, the ordering key `(ts_event, sequence, ingest_index)` names `ingest_index`, which the §5 envelope field table does not list. | An event-representation architecture gate |
| D5 | **Full dataset manifest.** Phase 0 ships the dependency-free capability primitives only. | `docs/architecture.md` §13 commits manifests to Pydantic v2, and Phase 0 carries zero runtime dependencies. Half the manifest is also unspecifiable today: `source.request` is vendor-shaped, `dataset_id` depends on the storage layout, `session_id` needs the bounded Phase 1B reference/calendar foundation (extended in Phase 2), and `retrieved_at`/`generated_at` are wall-clock reads that the core must never take. | Phase 1, where the vendor is chosen and Pydantic is legitimately at the boundary |
| D6 | **Per-capability quality statistics.** `CapabilityEntry` carries `present` and `tier` only. `unknown_share`, `truncation_events`, `assumed_feed_delay_ns` and `assumption_source` from the §3 example are absent. | `unknown_share` is a float in the example, and floats are forbidden in exact paths — representing a ratio exactly is an open decision. The other three come from quality layers (L1a/L1b) or run configuration, none of which exist. | Phase 1, alongside the manifest |

---

## 6. KNOWN LIMITATIONS — permanent, must be stated in reports

| # | Limitation | Consequence |
| --- | --- | --- |
| K1 | **Self-impact is unmodelled.** Our simulated order absorbs no volume and displaces nobody. | Passive fill rates overstated; market-order slippage understated; market impact absent. Bias is optimistic and unmeasurable from historical data. Bounded only by capacity analysis. |
| K2 | **Queue position is `SIMULATED`, never observed.** Even full MBO gives the book's state, not our nonexistent order's place in it. | Limit-order results depend on a model; both optimistic and conservative variants must be reported. |
| K3 | The conservative MBP-10 queue rule **ignores cancellations**, which are the dominant queue-advance mechanism in liquid futures. | It systematically under-fills. That is its intended error direction. |
| K4 | Historical MBO/MBP is a **capture of a feed**, not exchange state. | Sequence gaps and vendor normalization exist and are visible in L1a reports. |
| K5 | `INFERRED` aggressor side has a non-zero error rate, worst at and inside the spread. | Features consuming it must declare it and report excluded/uncertain volume. |
| K6 | Where `ts_recv` is unavailable, the decision clock is an **assumption**, not a measurement. | Mandatory feed-delay stress; an edge that dies under plausible delay was look-ahead. |
| K7 | Notebook discipline is a `[PROCESS]` control. Code cannot prevent a researcher from plotting the confirmation sample. | The discovery search log is self-reported and labelled as such. |
| K8 | Contract, period, and instrument selection biases are disclosed, not eliminated. | Every experiment record carries the §9 disclosure of `research_protocol.md`. |
| K9 | Streaming-only feature computation is slower than vectorized computation. | Accepted cost of structural causality. Mitigated by partition parallelism and caching, never by a second code path. |
| K10 | **The canonical content-hash format is expensive to change.** It is `docs/architecture.md` §16 item 10: altering a type tag, the key ordering, the separators, the encoding or the version prefix renames every stored feature partition and invalidates every experiment record that references one — silently, because the new digest looks exactly as valid as the old. | Changing it is a project-level decision with a migration plan. The `ofa-canon-1` prefix is the migration mechanism: bumping it changes every digest at once, deliberately and visibly. Adding a **new** tag is safe and needs no bump. |
| K11 | `feature_id` contains `#`, a URL fragment delimiter that also needs quoting in some shells. | The format is fixed by `docs/architecture.md` §6.4. Consumers must quote it in paths and escape it in URLs. |
| K12 | The identifier primitives reject integer subclasses (including `IntEnum`); `money.py` and `time.py`, which predate the canonicalizer's exact-type dispatch, accept them. | A documented divergence, not an accident. The older modules are unchanged because their semantics are already committed. |

---

## 7. OPEN — documentation conflicts not yet resolved

These are conflicts between authoritative documents. `CLAUDE.md` states that a
conflict between two documents is a bug; these are recorded rather than
silently resolved, because choosing a side is an editorial decision.

| # | Conflict | Status |
| --- | --- | --- |
| X1 | **Feature storage path.** `docs/architecture.md` §6.4 gives `data/features/<instrument>/<trade_date>/<feature_id>.parquet`; `docs/data_specification.md` §9 gives `features/<venue>/<instrument>/<trade_date>/<feature_id>.parquet`, with `<venue>` present. The data-specification form is self-consistent with every sibling path and with `dataset_id` in the §8 manifest example, so it is the likelier intent — but the architecture document holds authority over §16 item 7, "storage layout and manifest schema". | Open. No storage code exists, so nothing depends on it yet. |
| X2 | **`venue` in the dataset record.** `CLAUDE.md` requires every dataset to record `venue`; the §8 manifest example in `docs/data_specification.md` has no top-level `venue` field, carrying it only inside `dataset_id`. | Open. Resolve with the manifest in Phase 1. |

---

### Additional open design gates from vendor evidence

| # | Conflict or unresolved semantics | Status |
| --- | --- | --- |
| X3 | **Receive-time capture point.** Architecture §9.1 defines `ts_recv` as when we could have known; the data envelope calls it capture/receive time. Vendor-capture time precedes consumer receipt and does not establish decision availability by itself. | Open; resolve at Phase 1B with primary evidence and explicit delay/measurement treatment. No clock change approved. |
| X4 | **Snapshot and sequence mapping.** Synthetic initialization may carry stale exchange times; packet/channel/instrument sequences are different domains. The fixed ordering tuple alone does not define their canonical mapping. | Open; Phase 1B must preserve raw timestamps/flags, define comparable sequence semantics and causality-safe initialization. See `vendor_capability_matrix.md` and `phase1_plan.md`. |
| X5 | **Vendor-field ownership.** Architecture's adapter-only vendor awareness, L2 vendor-field-name permission and L1a raw checks need a consistent implementation boundary. | Open; resolve before 1C without allowing vendor objects into higher deterministic layers. |

## 8. Resolution protocol

The Phase 1 sequencing reconciliation is in `roadmap.md` (1A–1D) and
`phase1_plan.md`. D4 now explicitly blocks 1B exit and canonical normalization,
storage and replay, but not vendor evidence gathering. D5/D6 block dependent
1C metadata. The bounded reference/calendar prerequisite is delivered in 1B
and extended in Phase 2; no provisional session identifier is permitted.
No deferred semantic decision is closed by this schedule.

- A row moves out of UNVERIFIED only with a named verifier, a date, and a
  citation to primary documentation (vendor docs, exchange rulebook).
- Resolving a row that contradicts a design assumption requires updating the
  affected document in the same commit.
- An UNVERIFIED item that blocks a phase blocks it. It is not worked around
  by assumption.
