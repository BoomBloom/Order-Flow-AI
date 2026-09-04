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
| V9 | **Rithmic entitlement scope.** An R\|Trader Pro subscription authenticates certified third-party front-ends. Whether the same entitlement permits a self-written R\|API+ / R\|Protocol client without separate Rithmic application certification is unknown. | Whether a first-party live adapter (`architecture.md` §12) is possible at all, or whether live capture must run through a certified platform | — |
| V10 | **Rithmic historical depth availability.** Believed forward-record-only for L2, with no deep archive. If confirmed, no Rithmic-sourced confirmation sample exists until self-capture accumulates. | Phase 1 source selection; every split policy in `research_protocol.md` §4 | — |
| V11 | **Rithmic L2 depth semantics for NQ/ES/6E:** number of price levels, aggregated MBP vs. by-order MBO, and truncation behaviour under burst. Supersedes V4/V5 for this vendor. | All liquidity features; §12.1 transferability of any liquidity conclusion | — |
| V12 | **Timestamp fields surviving to a self-recorded capture.** Whether exchange time and a receive time both survive Rithmic normalization and the recording front-end, or only one. A platform-local receive stamp is a genuine `ts_recv` for the decision clock, but it measures our own network path, not the vendor's. | The decision clock (`architecture.md` §9.1) for any self-recorded partition; V2 for the live feed | — |
| V13 | **Whether CME sequence numbers survive Rithmic normalization and the front-end.** Believed lost; unverified. | L1a gap detection and the `(ts_event, sequence, ingest_index)` ordering key for self-recorded data | — |
| V14 | **Aggressor side through Rithmic:** exchange-supplied flag (`OBSERVED`) or requiring tick/quote-rule inference (`INFERRED`). Supersedes V3 for this vendor. | Every order-flow feature; §12.1 transferability of every order-flow conclusion | — |

If V2 resolves to "not supplied", the decision clock rests on
`assumed_feed_delay_ns` for all historical work. That is a configured
assumption, mandatory to stress-test, and reported with every dependent
result.

V9–V14 concern a **candidate live/self-capture source** (Rithmic, reached
through a certified front-end) and are recorded separately from V1–V8, which
concern the **historical research source**. These may be different vendors.
Where they are, `architecture.md` §12.1 governs whether a conclusion drawn on
the historical source may be paper traded on the live one, and the two
capability records must be compared explicitly rather than assumed
compatible. User-reported vendor capability does not resolve any row here:
§6 requires a named verifier, a date, and primary documentation.

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
| C4 | **Market-data licensing terms for recording and storing a CME feed for research**, under the applicable subscriber category and the front-end vendor's terms | Whether a self-recorded capture is a usable research dataset at all |

---

## 4. UNVERIFIED — platform

| # | Item | Blocks |
| --- | --- | --- |
| P1 | LLM provider, models per routing role, and budget | Phase 8 |
| P2 | Compute environment (local vs cloud) and available disk | Data-tier and history-depth decisions |

---

## 5. KNOWN LIMITATIONS — permanent, must be stated in reports

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

---

## 6. Resolution protocol

- A row moves out of UNVERIFIED only with a named verifier, a date, and a
  citation to primary documentation (vendor docs, exchange rulebook).
- Resolving a row that contradicts a design assumption requires updating the
  affected document in the same commit.
- An UNVERIFIED item that blocks a phase blocks it. It is not worked around
  by assumption.
