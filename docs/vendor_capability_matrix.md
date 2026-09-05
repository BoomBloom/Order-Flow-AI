# Phase 1 Vendor Capability and Evidence Matrix

Status: **research evidence only; no vendor selected; Phase 1 remains gated**

Research date: **2026-09-05**

Review corrections: **2026-09-06**. Proposed snapshot mappings and downstream-delay treatment below are unresolved design questions, not amendments to the locked ordering tuple or decision-clock contract.

Verifier: **Codex Research Evidence Agent**

## 1. Scope and decision rule

This report evaluates public, first-party evidence for the Phase 1 data spine:
one NQ front-month contract, a bounded date range, event trades and BBO at
minimum, with MBP-10 or MBO only where the acquired tier verifiably supplies
them. It covers Databento, Rithmic, CME DataMine/direct CME MDP 3.0, and the
Rithmic-facing platforms Sierra Chart, Bookmap, Quantower, and MotiveWave.

It does **not** select or recommend a vendor. A product-level statement such as
"MBO supported" is not enough to establish the exact historical record schema,
capture timestamp semantics, sequence domain, completeness, license, or price
for the user's intended use. Material unknowns remain for every route, and the
purchase- and entitlement-dependent checks in §8 require explicit user action.

The repository's locked semantics remain controlling:

- event order is `(ts_event, sequence, ingest_index)`;
- the decision clock is `ts_recv`; absence requires a recorded and stress-tested
  `assumed_feed_delay_ns`;
- vendor-delivered fields are `OBSERVED`, deterministic derivations are
  `RECONSTRUCTED`, heuristics are `INFERRED`, and hypothetical execution remains
  `SIMULATED`;
- a historical conclusion transfers to a live feed only when the live
  capability record is an equal-or-stronger superset;
- the final `CanonicalEvent` representation remains deferred and is not designed
  here.

### Evidence grades

| Grade | Meaning in this report |
| --- | --- |
| **VERIFIED** | A current first-party schema, protocol, pricing, or entitlement page directly states the field or capability. This still requires sample-byte verification for the purchased partition. |
| **STRONGLY SUPPORTED** | Multiple or closely related first-party statements support the claim, but the exact requested product/tier/record contract is not public. |
| **INFERRED** | A reasonable implication, explicitly not a vendor guarantee. It cannot close a Phase 1 gate. |
| **UNKNOWN** | Public first-party evidence does not establish the claim, is ambiguous, or is inaccessible without a dev kit, account, quote, license, or purchase. |

All grades describe public documentation as observed on 2026-09-05. They do not
promote a vendor-wide promise into a per-partition capability record.

## 2. Gate-level findings

| Register item | Public-evidence result | Gate status |
| --- | --- | --- |
| **V1 vendor, tier, cost, history** | Databento publishes current plan/history ranges and pay-as-you-go historical access. Rithmic publishes history back to Dec 2011 and a 40 GB/user/week limit but no public price. CME DataMine exposes self-service ordering and purchased-file API access but exact NQ product prices are not public in the reviewed pages. | **OPEN** — no vendor/tier selected; exact bounded NQ quote and license not verified. |
| **V2 historical `ts_recv`** | Databento GLBX.MDP3 schemas directly contain Databento capture-server `ts_recv`, with documented invalid-timestamp flags on synthetic/snapshot records. That timestamp proves when Databento captured the packet, not when an OFA process could consume it; it is a lower bound on the eventual OFA decision time unless the architecture deliberately defines the vendor capture point as the decision boundary. Rithmic describes receipt timestamping, but its public historical callback example does not define whether a distinct receipt timestamp is persisted. CME MDP supplies exchange event/send timestamps; reviewed DataMine pages do not establish a historical consumer/capture receipt timestamp. | **OPEN** — even for Databento. Selection requires sample-byte verification, capture-point metadata, a recorded/stressable downstream-delay model, and historical/live capture-point matching. The repository currently calls `ts_recv` both capture/receive time and "when we could have known" without resolving that boundary. |
| **V3 aggressor provenance** | CME Trade Summary directly publishes AggressorSide, including explicit no-aggressor cases. Databento normalizes this into trade `side`, with implied trades potentially `None`. Rithmic public API material does not define the historical trade-side field. | **OPEN** — sample-specific unknown share and exact Rithmic contract remain unverified. |
| **V4 MBP-10 depth/truncation** | Databento defines event MBP-10 over the top ten price levels, and CME defines MBP as top ten. That structural ten-level bound is not itself a data-loss event. Separate failure modes—transport/recovery gaps, incomplete snapshots, conflation, vendor omission, or inability to restore all ten levels—may truncate the usable book. Neither public source reviewed defines OFA's proposed `truncation_events` statistic or a guarantee covering those modes. | **OPEN** — schema availability and structural depth are verified; completeness is not. Define `truncation_events` operationally before recording it, and verify each loss/recovery mode from sample data and vendor semantics. |
| **V5 MBO availability/cost** | Databento and CME document full-depth order-event MBO; Rithmic advertises MBO/full depth. Exact bounded-request cost is only obtainable via Databento's estimator/API or a CME/Rithmic account/quote. | **OPEN** — availability is supported, exact entitlement and cost are purchase-dependent. |
| **V6 sequence semantics** | CME packet `MsgSeqNum` is per channel and resets weekly; `RptSeq` is per instrument update. Databento exposes venue `sequence` and `channel_id`, but the exact normalized gap policy for an OFA partition still needs sample and vendor confirmation. Rithmic public docs do not define its exposed historical sequence domain. | **OPEN — hard ordering/L1a gate.** Before ingestion, pin schema/version and source field; document whether the number is packet-, message-, event-, channel-, or instrument-scoped; retain channel identity; define reset, wrap, duplicate, gap, recovery/retransmission and snapshot behavior; and establish whether values are comparable across channels. Until then neither monotonicity nor `(ts_event, sequence, ingest_index)` ordering is implementable defensibly. |
| **V7 storage volume** | Databento exposes a billable-size endpoint and pricing estimator; CME's entitled-file list returns file sizes. No public source supplies NQ instrument-day volume for the exact requested schemas. | **OPEN** — measure before scaling. |
| **V8 live compatibility** | Databento publishes matching historical/live schema families and live replay/recovery behavior; Rithmic publishes live capabilities; direct CME differs materially in protocol and local capture. No live vendor or tier is selected and no actual live capability manifest exists. | **OPEN**, correctly deferred to Phase 10. |

**Gate conclusion:** public research narrows the questions but does not satisfy
the Phase 1 prerequisite "vendor selected; V1-V6 resolved." No implementation or
purchase should begin from this report alone.

## 3. Access, product, and economic matrix

| Route | API / protocol / language | Historical and live access | Retention / replay | Entitlement and licensing | Public pricing | Grade |
| --- | --- | --- | --- | --- | --- | --- |
| **Databento GLBX.MDP3** | Historical HTTP API; live proprietary Raw API over TCP; official Python, C++, Rust clients; DBN, CSV, JSON. | Historical and live services expose trades, BBO/MBP-1, MBP-10, MBO, definitions, statistics, and status. | GLBX history advertised from June 2010 / 16+ years overall. Standard includes 1 year L1 and 1 month L2/L3; longer history remains pay-as-you-go. Live normally offers intraday replay within 24h; GLBX MBO/definitions have special weekly-session replay. | API key/account required. Live requires plan and venue questionnaire/license. Personal CME use is included with Standard up to two devices; commercial/non-display/distribution terms and fees differ. Publisher restrictions pass through. | Historical usage-based with estimator/API quote; Standard $199/month, Plus $1,750/month, Unlimited $4,500/month as of the research date. | **VERIFIED** for published interface/plan terms; exact user quote **UNKNOWN**. |
| **Rithmic API suite** | R\|API+ C++/.NET; R\|Protocol WebSocket + Protocol Buffers for any language; Diamond C/C++ Linux/co-location. | Public marketing pages advertise normalized live/delayed/historical data, full depth, MBO, BBO, tick-by-tick, and reference lookup; no reviewed public schema binds those claims to exact fields or vintages. | Tick history is advertised back to Dec 2011, limited to 40 GB per user per week. Public pages do not define exact historical MBO retention or replay record schema. | Dev kit requires contact information. Production and paper access require conformance; live credentials and fees come through an FCM/broker. | No public API/data price found. | Interface names/requirements **VERIFIED**; advertised data breadth **STRONGLY SUPPORTED** only; historical field contract and price **UNKNOWN**. |
| **CME DataMine (historical)** | Purchased flat files downloadable through REST API; OAuth 2.0 or Basic Auth with an entitled CME API ID; also SFTP/S3/file browser. | Historical trades, BBO, market depth, MBO, PCAP, settlements and reference products exist. DataMine is not the direct real-time MDP feed. | MBO history is available from each channel's MBO launch; older MBP depth history is product-dependent. Download/replay is file-based and local after acquisition. | CME login, order, declared use, license questionnaire/agreement, payment, and optionally API ID are required. Non-display and distribution are explicit use categories. | Exact NQ/ES/6E dataset price not present on reviewed public pages; portal/cart or sales quote required. | Product/access **VERIFIED**; exact schema/tier/price **UNKNOWN** until catalog order evidence. |
| **Direct CME MDP 3.0 / Smart Stream (live)** | MDP 3.0 UDP multicast with SBE/FIX Binary; recovery feeds; cloud SBE/JSON and WebSocket variants exist. | Direct real-time MDP includes event data, MBP, MBO, trades, status, statistics, and definitions. It is not automatically the same product contract as DataMine historical files. | Packet recovery/snapshot mechanisms are specified. The consumer must capture its own receive timestamp; CME publishes exchange processing and gateway-send timestamps, not the consumer's receipt time. | Direct connection, market-data agreements, certification/connectivity, and potentially redistribution/non-display fees require CME engagement. | No complete intended-use cost established here. | Protocol capabilities **VERIFIED**; suitability/cost **UNKNOWN**. |

Sources: [Databento pricing](https://databento.com/pricing),
[Databento quickstart](https://databento.com/docs/quickstart),
[Databento portal/licensing](https://databento.com/docs/portal),
[Databento historical API](https://databento.com/docs/api-reference-historical),
[Databento live API](https://databento.com/docs/api-reference-live),
[Rithmic API documentation](https://www.rithmic.com/documentation),
[Rithmic technology](https://www.rithmic.com/technology),
[Rithmic CME exchange coverage](https://www.rithmic.com/platforms/exchanges),
[CME DataMine](https://www.cmegroup.com/datamine.html),
[CME DataMine API](https://www.cmegroup.com/datamine/datamine-api.html),
[CME ordering workflow](https://www.cmegroup.com/tools-information/webhelp/data-services-portal/Content/Ordering-CME-Datamine-Products.html), and
[direct CME MDP](https://www.cmegroup.com/market-data/distributor/market-data-platform.html).

## 4. Event capability matrix

### 4.1 Databento GLBX.MDP3

| OFA capability | Historical | Live | Provenance / caveat | Evidence grade |
| --- | --- | --- | --- | --- |
| Trades: price, size, time | Yes, event schema. | Yes. | Delivered normalized fields are `OBSERVED`; price is signed integer at 1e-9 scale. | **VERIFIED** |
| BBO | MBP-1 event updates; interval BBO and trade-aligned TBBO also exist. | Same schema family. | BBO reconstructed from MBO would be `RECONSTRUCTED`; delivered MBP-1 is `OBSERVED` after vendor normalization. | **VERIFIED** |
| MBP-10 | Every update affecting top ten price levels; includes aggregate size and order count. | Same advertised schema. | Top-ten boundary is structural, not an occasional failure. A separate "burst truncation" guarantee/statistic was not found. | Availability **VERIFIED**; truncation semantics **UNKNOWN** |
| MBO / order events | Add, cancel, modify, clear, trade, fill; order ID, channel ID, flags, venue sequence. Historical synthetic snapshots and live periodic snapshots. | Yes. | Delivered normalized records are `OBSERVED` vendor output. Book state produced by applying those records is `RECONSTRUCTED`; equivalence to the complete native CME feed and partition completeness remain unknown until verified. A hypothetical OFA order's queue position remains `SIMULATED`. | Schema **VERIFIED**; native equivalence/completeness **UNKNOWN** |
| Aggressor | Trade `side` is initiating side; CME Trade Summary is source. Implied/opening cases may be `None`. | Same schema. | Defined side can be `OBSERVED`; `None` must remain `UNKNOWN`, never silently inferred. Partition `unknown_share` must be measured. | **VERIFIED** |
| `ts_event` | CME tag 60 TransactTime, nanoseconds. | Yes. | Matching-engine-received/start-of-event time; suitable for OFA ordering, not decision clock. | **VERIFIED** |
| `ts_recv` | Databento capture-server receive time, nanoseconds, stored in trades/MBP/MBO/definitions/status/statistics. | Yes; optional `ts_out` can also be requested live. | Hardware timestamped and PTP/GPS synchronized at Databento. It is not automatically OFA consumer decision time: downstream transport/processing delay and capture-point comparability must be recorded and stressed. Synthetic MBO snapshots carry `F_BAD_TS_RECV`; weekly-session snapshot records can be buffered/reordered and assigned the last record's receipt time. | Vendor field **VERIFIED**; OFA decision-clock sufficiency **OPEN** |
| Sequence | `sequence` is described as message sequence assigned at venue; MBO also has `channel_id`. | Same. | Public docs do not fully specify normalized source field/domain, wrap/reset, duplicate, recovery, snapshot, or gap tolerance for OFA. CME packet and per-instrument sequences are distinct; an adapter must not conflate them or compare unrelated channels. | Fields **VERIFIED**; ordering/L1a semantics **UNKNOWN and blocking** |
| Status | Status schema has action, reason, trading event, best-efforts `is_trading`/`is_quoting`; historical midnight snapshot. | Yes. | Granularity varies by publisher/dataset; CME-specific completeness needs sample verification. Snapshot state is initialization/control information, not naively an ordinary event at its carried historical `ts_event`. | **VERIFIED** schema; partition completeness and snapshot mapping **UNKNOWN** |
| Reference / definitions | Point-in-time definitions with symbol, tick size, activation, expiration, limits, and other fields. | Yes. | Vendor-normalized from CME definitions; verify each required OFA `InstrumentDef` field rather than hand-fill. | **VERIFIED** |
| Statistics / settlements | Official statistics schema includes preliminary/final settlement, OI, volume, `ts_ref`, flags. | Yes. | CME publication time varies; multiple records can exist and final is most accurate. No future final statistic may be backfilled into an earlier decision. | **VERIFIED** |
| NQ / ES / 6E | GLBX parent-symbol examples explicitly show ES and NQ; the latency example explicitly uses 6E and requests GLBX MBO. Dataset covers all CME futures/options. | Advertised CME coverage. | Exact contract/date availability and cost must be queried before purchase. | **VERIFIED** product coverage; exact partition **UNKNOWN** |

**Blocking snapshot rule:** Databento MBO snapshots and historical status
snapshots cannot enter the ordinary event stream naively. A snapshot may carry
an old exchange `ts_event` while its `ts_recv` is the snapshot-generation or
final-record time, and MBO snapshot records may be flagged `F_BAD_TS_RECV`.
Sorting such records as ordinary events can move initialization state backward
in event time or present a synthetic timestamp as a decision clock. Before the
CanonicalEvent gate closes, the design must choose and test one explicit policy:
(a) exclude snapshot records from ordinary events and use them only to seed
state, or (b) map them to typed reset/control semantics with a separate effective
time and preserved source timestamps/flags. The same gate must define replay,
gap recovery, and provenance behavior. Until then, snapshot-bearing partitions
are not safe for general replay.

Primary evidence:
[trades schema](https://databento.com/docs/schemas-and-data-formats/trades),
[MBO schema](https://databento.com/docs/schemas-and-data-formats/mbo),
[MBP-10 schema](https://databento.com/docs/schemas-and-data-formats/mbp-10),
[status schema](https://databento.com/docs/schemas-and-data-formats/status),
[instrument definitions](https://databento.com/docs/schemas-and-data-formats/instrument-definitions),
[statistics](https://databento.com/docs/schemas-and-data-formats/statistics),
[common timestamp conventions](https://databento.com/docs/standards-and-conventions/common-fields-enums-types),
[CME GLBX normalization](https://databento.com/docs/knowledge-base/datasets),
[MBO snapshots](https://databento.com/docs/standards-and-conventions/mbo-snapshot),
[ES/NQ request](https://databento.com/docs/examples/basics-historical/requesting), and
[6E MBO request](https://databento.com/docs/examples/algo-trading/latency).

### 4.2 Rithmic

| OFA capability | Public evidence | Grade / unresolved issue |
| --- | --- | --- |
| Trades / BBO / depth | Rithmic marketing pages advertise unthrottled tick-by-tick, BBO, full depth, and normalized exchange data. | **STRONGLY SUPPORTED**, not field-level verified; exact historical callback fields, throttling/conflation policy, recovery, and completeness flags **UNKNOWN**. |
| MBP-10 | Full market depth is advertised, often beyond ten levels. Public pages do not define a stable MBP-10 event schema. | Marketing claim **STRONGLY SUPPORTED**; depth/event contract and canonical mapping **UNKNOWN**. |
| MBO / add-cancel-modify | MBO and individual orders are explicitly advertised. The public pages do not enumerate action, order-ID, priority, historical coverage, or snapshot semantics. | Marketing claim **STRONGLY SUPPORTED**; field/vintage/completeness contract **UNKNOWN**. |
| Aggressor | Public API pages reviewed do not define a trade aggressor field. R Trader Pro release notes acknowledge trades with no aggressor, but do not specify API provenance or encoding. | **UNKNOWN**. |
| `ts_event` | Rithmic states exchange-native timestamps are preserved; historical example exposes `iSsboe`. Exact meaning and resolution require the dev-kit contract. | **STRONGLY SUPPORTED**, not enough to map safely. |
| `ts_recv` | Rithmic marketing states market-data receipt is timestamped in microseconds by its platform. The public historical replay example exposes one timestamp and does not prove a distinct receipt time survives in history or corresponds to OFA consumer availability. | Live platform timestamping **STRONGLY SUPPORTED**; historical `ts_recv`, capture point, and downstream delay **UNKNOWN**. |
| Sequence / status / reference | Symbol/contract/exchange metadata lookup is advertised. No public field-level sequence, reset, recovery-gap, or status contract was found. | Reference breadth **STRONGLY SUPPORTED**; sequence/status **UNKNOWN**. |
| Retention / replay | Marketing states historical tick data back to Dec 2011 and a 40 GB/user/week limit. Public material does not establish that every historical date contains MBO, BBO, distinct `ts_recv`, or exchange sequence. | Advertised history breadth **STRONGLY SUPPORTED**; schema-by-vintage and entitlement-specific coverage **UNKNOWN**. |
| NQ / ES / 6E | Rithmic covers CME Group and describes all exchange-sent levels; R Trader examples use ES. This strongly implies all three CME futures, but exact per-account permissions are broker/FCM controlled. | **STRONGLY SUPPORTED**, entitlement-specific **UNKNOWN**. |

Primary evidence:
[Rithmic API suite](https://www.rithmic.com/documentation),
[Rithmic builders](https://www.rithmic.com/solutions/builders),
[Rithmic technology](https://www.rithmic.com/technology),
[Rithmic exchange coverage](https://www.rithmic.com/platforms/exchanges), and
[R Trader Pro release notes](https://www.rithmic.com/products/r-trader-pro/releases).

**Blocking request to Rithmic before selection:** obtain the dev kit and a
written field-level answer for historical trades, BBO/MBP/MBO, `ts_event`, a
distinct historical receive timestamp, aggressor enum/unknown cases, packet or
instrument sequence identity/reset/gap behavior, recovery markers, status,
definitions, and per-product history dates. This requires user approval because
the request discloses contact/company details and may lead to commercial terms.

### 4.3 CME DataMine and direct MDP 3.0

| OFA capability | CME evidence | Grade / applicability |
| --- | --- | --- |
| Trades and aggressor | MDP Trade Summary includes price, quantity, per-instrument `RptSeq`, trade ID, and `AggressorSide` values 0/Buy/Sell. No-aggressor cases include opens/reopens and implied participation. | Direct MDP **VERIFIED**. Must verify the purchased DataMine file retains these exact fields. |
| BBO / MBP-10 | CME's historical Market Depth FAQ describes book recreation and top 10 levels in FIX/FAST; current MDP MBP remains maximum ten levels. | **VERIFIED** as CME products; exact vintage/file format must be selected. |
| MBO | MBO provides all price levels, anonymous order ID, and PriorityID; supported for all Globex futures/options, with historical data from each channel's launch. | **VERIFIED**. Exact DataMine product and price remain **UNKNOWN**. |
| `ts_event` / send time | MDP has TransactTime and packet SendingTime. | **VERIFIED** exchange/gateway times. |
| `ts_recv` | CME's exchange feed does not emit the downstream consumer's receipt time. A direct-feed consumer may create a local capture timestamp if its capture system is explicitly instrumented; reviewed DataMine pages do not claim to provide a historical capture-server receipt field. | Direct local receive time is implementation- and capture-point-dependent; DataMine historical `ts_recv` **UNKNOWN** and must not be assumed. |
| Sequence | UDP `MsgSeqNum` is per channel, increments per packet, resets weekly; maximum uint32. Trade `RptSeq` is per instrument update. TCP connection sequences reset on connection termination. | Source semantics **VERIFIED**. Mapping remains a hard gate: pin the exact source field/schema, retain domain and channel, define reset/wrap/duplicate/recovery/snapshot rules, and do not compare unrelated channel sequences. |
| Status / definitions | MDP disseminates market security status, recovery, statistics, and security definitions; Reference Data API provides instrument/product lifecycle data. | **VERIFIED** product capability; DataMine bundle inclusion **UNKNOWN** until tier selected. |
| Depth and history | Legacy DataMine depth files are millisecond FIX/FAST and 10 levels; MBO is full-depth and only available from rollout dates (completed 2017). These are different products/vintages. | **VERIFIED** distinction; never treat legacy MBP as MBO. |
| NQ / ES / 6E | CME identifies NQ, ES, and Euro FX futures as Globex products; MBO supports all Globex futures. | **VERIFIED** exchange coverage; catalog dates/entitlements still required. |

Primary evidence:
[CME MBO FAQ](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html),
[CME Trade Summary](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457418925/MDP%2B3.0%2B-%2BTrade%2BSummary),
[CME Trade Summary order detail](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457225774/MDP%2B3.0%2B-%2BTrade%2BSummary%2BOrder%2BLevel%2BDetail),
[CME SBE technical headers](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457638617/MDP-30---SBE-Technical-Headers),
[CME Market Depth FAQ](https://www.cmegroup.com/market-data/files/cme-group-market-depth-faq.pdf),
[CME real-time and historical overview](https://www.cmegroup.com/market-data/real-time-and-historical-data.html), and
[CME Reference Data API](https://www.cmegroup.com/trading/market-tech-and-data-services/cme-reference-data-api.html).

## 5. Platform integration matrix (supplementary only)

These products can corroborate that a Rithmic entitlement reaches a user-facing
platform. They do not establish a lossless, exportable, field-level raw capture
contract suitable for OFA L0. None should be treated as the vendor adapter
without separate API/export documentation and sample verification.

| Platform | First-party documented Rithmic behavior | OFA relevance and limits | Grade |
| --- | --- | --- | --- |
| **Sierra Chart** | Rithmic service supports streaming real-time data, historical intraday, and market depth; it explicitly says historical BidVolume/AskVolume is not supplied through this integration and warns of non-precision timestamps, missing history, and depth issues. | Evidence of a materially narrower/altered interface than Rithmic's broad marketing. Not proof of historical aggressor, MBO, sequence, or `ts_recv`. | Integration **VERIFIED**; OFA raw suitability **UNKNOWN**. |
| **Bookmap** | Rithmic connection advertises CME MBO and full depth. Bookmap's connectivity guide states futures backfill is up to 24 hours for all connections and that broker/Rithmic credentials are needed; MBO can be disabled by aggregated-quotes mode. | Useful live visual validation, but platform backfill is much shorter than Rithmic's server-history claim and may depend on settings. Export field semantics are unverified. | Live MBO **VERIFIED**; acquisition suitability **UNKNOWN**. |
| **Quantower** | Rithmic connection provides full depth; MBO must be activated. Existing broker/prop credentials and correct server are required. Its troubleshooting page confirms the 40 GB weekly historical tick limit and account-specific permission failures. | Corroborates entitlement and history-limit behavior; does not document historical record fields or a raw export contract. | Integration/history limit **VERIFIED**; OFA raw suitability **UNKNOWN**. |
| **MotiveWave** | Connection table reports Rithmic historical tick data and full market depth. DOM docs expose Rithmic MBO. Its volume-analysis docs say historical Rithmic ticks include trade/BBO fields but an unknown history limit; missing BBO can trigger tick-rule inference, and some unsupported feeds generate synthetic ticks from bars. DOM history is accumulated at one-second intervals in memory. | Explicit warning that platform-derived order-flow fields may be `INFERRED` or generated and that DOM history is sampled, not raw event history. Any export would need provenance audit before use. | Display capabilities **VERIFIED**; lossless raw acquisition **UNKNOWN**. |

Sources:
[Sierra Chart Rithmic service](https://www.sierrachart.com/?l=doc%2FRithmic.php),
[Bookmap Rithmic](https://bookmap.com/en/partner/rithmic),
[Bookmap futures connectivity](https://bookmap.com/wp-content/themes/bookmap/Bookmap_Connectivity.pdf),
[Quantower Rithmic connection](https://help.quantower.com/quantower/connections/connection-to-rithmic),
[Quantower Rithmic issues](https://help.quantower.com/quantower/connections/connection-to-rithmic/rithmic-issues),
[MotiveWave connection details](https://docs.motivewave.com/knowledge-base/connection/connection-details),
[MotiveWave volume/order-flow data semantics](https://docs.motivewave.com/user-guide/volume-order-flow-analysis-guide/introduction), and
[MotiveWave DOM](https://docs.motivewave.com/user-guide/volume-order-flow-analysis-guide/depth-of-market).

## 6. Contradictory or easily conflated evidence

1. **Databento MBO says queue position can be determined, but OFA queue
   position is still `SIMULATED`.** Databento/CME can preserve priority among
   observed orders. They cannot observe the position of OFA's counterfactual
   order. Further, Databento does not expose CME `MDOrderPriority`; it states
   FIFO is reflected by message order, and it buffers/sorts weekly snapshot
   records. This is enough to reconstruct observed priority under documented
   cases, not to relabel simulated execution as observed.

2. **Databento `ts_recv` is real but not universally valid.** General schema
   pages describe hardware receive time, while MBO snapshot documentation marks
   synthetic/snapshot records `F_BAD_TS_RECV`. A blanket rule that every
   Databento `ts_recv` is decision-grade would contradict the vendor's own flag
   semantics. Even a valid value timestamps Databento's capture point, not
   necessarily OFA availability; downstream delay remains a separate quantity.

3. **Rithmic's broad history statement does not prove historical MBO or
   historical receipt time.** Its public site places MBO, full depth, receipt
   timestamping, and history back to 2011 on the same product pages. The public
   historical callback example exposes only one timestamp, and no reviewed
   field table ties every capability together by vintage. This is a missing
   contract, not permission to infer one.

4. **Rithmic platform interfaces are not equivalent.** Rithmic advertises full
   MBO and long tick history; Bookmap documents only up to 24 hours of platform
   backfill, Sierra Chart says historical BidVolume/AskVolume is unavailable
   and warns of timestamp/history issues, and MotiveWave may backfill or infer
   fields. These are likely integration/product limitations rather than proof
   that Rithmic's core claims are false, but they demonstrate why OFA must audit
   the exact API path.

5. **CME legacy Market Depth and current MBO are distinct.** The legacy
   DataMine FAQ describes millisecond FIX/FAST, top-ten MBP files. CME's MBO FAQ
   describes full depth/order granularity from the channel rollout dates. A
   purchase called "market depth" must not be assumed to be MBO.

6. **CME direct live protocol does not imply DataMine file contents.** MDP 3.0
   defines exchange event/send times, packet sequence, per-instrument sequence,
   status, and order events. DataMine delivers separately licensed flat files.
   Each purchased dataset's fields and vintage must be inspected independently.

## 7. Provenance and timing consequences

- Databento-defined aggressor side sourced from CME tag 5797 may be recorded as
  `OBSERVED`; undefined/implied/opening side remains unknown. A heuristic fill
  is a new `INFERRED` field, never a repair of the observed field.
- A Databento MBO record as delivered is `OBSERVED` vendor output; applying
  delivered deltas to produce book state is `RECONSTRUCTED`. Neither label says
  the normalized stream is complete or byte-equivalent to native CME. Native
  equivalence and completeness remain quality/capability questions.
- Vendor normalization is part of provenance. Databento's reordering of CME
  weekly MBO snapshots and status/MBO synthetic snapshots must be represented in
  source flags and quality reports. Snapshot records are excluded from ordinary
  ordering or mapped to explicit reset/control semantics at the CanonicalEvent
  gate; they are not inserted as ordinary events using stale `ts_event` or bad
  `ts_recv`.
- If the chosen historical path cannot prove a distinct capture receipt time,
  `ts_recv` is absent. OFA must use and record `ts_event +
  assumed_feed_delay_ns`; exchange gateway send time is not the consumer's
  receive time. If vendor-capture time is available, capture-point metadata and
  downstream vendor-to-OFA delay must still be recorded and stressed. The
  architecture must clarify whether `ts_recv` means vendor capture or OFA
  consumer availability and require historical/live measurements at compatible
  boundaries.
- CME packet `MsgSeqNum`, CME per-instrument `RptSeq`, and any vendor-normalized
  `sequence` are different domains. L1a gap checks require the exact domain,
  channel, schema/version/source field, reset schedule, wrap behavior,
  duplicates, recovery/retransmission markers, snapshot behavior, and an
  explicit ruling on cross-channel comparability. V6 blocks ordinary ordering
  and L1a implementation until all are pinned.
- MBP-10 cannot support observed individual-order queue state. MBO can
  reconstruct the observed book, but OFA's hypothetical queue and fills remain
  `SIMULATED` and still require verified matching/modification rules.
- A platform that samples DOM, synthesizes ticks, or infers bid/ask volume is not
  equivalent to raw event capture. Such fields must carry weaker provenance or
  be excluded.

## 8. User-specific entitlements, purchases, and approvals required

No action below was taken. Each requires explicit user approval.

| Action requiring approval | Why it is required | Evidence to retain after approval |
| --- | --- | --- |
| Create/use a Databento account and API key; run authenticated metadata cost/size queries for one specified NQ contract and ~20 sessions across trades, MBP-1, MBP-10, and MBO. | Closes exact price, byte volume, date coverage, schema availability, and sample-field questions. | Machine-readable quote, request parameters, dataset/version, schema list, coverage range, billable bytes/cost, license classification, and sample DBN metadata. |
| Activate Databento live CME or commercial/non-display access. | Requires a plan, subscriber questionnaire, and possibly direct venue agreement/fees. Not needed for Phase 1 historical-only work unless deliberately purchased. | Executed license, subscriber classification, device/use limits, entitlements, effective dates, and live schema test. |
| Request Rithmic dev kit and written technical answers. | Public documentation is insufficient for V2, V3, V6, historical schema/vintage, and pricing. Request discloses personal/company contact details. | Dev-kit version, field definitions, history coverage matrix, sample records, data license, broker/FCM terms, and written support answers. |
| Obtain Rithmic production/paper credentials through broker/FCM and pass conformance. | Required by Rithmic for production/paper API access; fees and permissions are account-specific. | Conformance result, server/system, market-data permissions, exchange agreements, per-user limits, and price. |
| Place a CME DataMine order / create an entitled CME API ID. | Exact catalog tier, file schema, price, and dates are visible through the purchase/licensing flow; API only downloads entitled files. | Cart quote, license/use classification, dataset/file IDs, layout/version, coverage dates, file sizes, and sample files. |
| Contract for direct CME MDP or Smart Stream. | Connectivity, certification, data agreements, non-display/distribution rights, and local capture infrastructure are material commitments beyond Phase 1's smallest data spine. | Executed agreements, channel list, protocol/schema version, certification, connectivity topology, timestamps, loss/recovery plan, and full cost. |
| Purchase or use Sierra Chart, Bookmap, Quantower, or MotiveWave as an acquisition intermediary. | Platform licenses and Rithmic credentials may apply, and no reviewed public contract proves lossless raw export. | Exact platform/API/export agreement, binary/CSV layout, timestamp/sequence semantics, sampling/conflation settings, and byte comparison against direct source. |

## 9. Minimum verification experiment before vendor selection

For each candidate still under consideration, obtain a small real NQ sample
covering a normal period, the daily pause/reopen, a burst, and (for MBO) a
snapshot/recovery boundary. Without implementing Phase 1, inspect and archive:

1. request, license/tier, exact product/schema version, raw checksum and bytes;
2. every timestamp field and flag, including capture-point identity,
   downstream-delay measurement, and invalid/synthetic timestamp cases;
3. exact schema/version and sequence source field/domain; packet, message,
   channel and instrument scope; reset, wrap, duplicate, gap,
   recovery/retransmission, snapshot and cross-channel comparison behavior;
4. trades with defined and undefined aggressor, with source-message mapping;
5. BBO/MBP-10/MBO action coverage, order counts, depth bounds, clear/snapshot;
6. status, definition and settlement/reference publication behavior;
7. actual file size and cost per NQ instrument-session;
8. deterministic replay feasibility without vendor-network access after capture;
9. license permission for immutable local raw retention and intended research
   artifacts; and
10. a written historical/live capability comparison, while leaving V8 open
    until a live route is actually selected.

For any MBO or status snapshot in the sample, run the proposed CanonicalEvent
policy both as a state seed/reset-control input and under a deliberately naive
ordinary-event insertion. The naive path must be rejected when old `ts_event`,
snapshot-generation `ts_recv`, or `F_BAD_TS_RECV` would violate causal ordering.

The evidence must be recorded per partition. A successful sample cannot justify
a static claim that every date or vintage has the same capability.

## 10. Unresolved blockers

- No vendor or paid tier has user approval.
- No authenticated quote, entitlement response, or real sample was accessed.
- Exact bounded NQ cost and storage volume remain unknown for every route.
- The repository has not resolved whether decision-clock `ts_recv` denotes the
  vendor capture boundary or availability to the OFA consumer. A vendor capture
  timestamp alone does not close V2; capture metadata, downstream-delay stress,
  and historical/live boundary compatibility remain required.
- Rithmic historical `ts_recv`, aggressor, sequence/reset, status, and
  schema-by-vintage semantics remain unknown from public documentation.
- CME DataMine historical receive-timestamp availability and exact current
  file layouts for the intended product remain unknown.
- Databento's exact OFA L1a sequence mapping is unresolved: schema/version,
  source field/domain, channel identity, reset/wrap/duplicate/recovery/snapshot
  behavior, and cross-channel comparability are all hard V6 gates.
- `truncation_events` is not operationally defined. Structural MBP-10 depth must
  be kept separate from transport/recovery gaps, incomplete snapshots,
  conflation, omission, and failure to restore all ten levels; actual partition
  quality must be measured.
- The CanonicalEvent gate has not decided whether MBO/status snapshots are
  excluded from ordinary events or represented as reset/control inputs with
  separate effective time. Snapshot-bearing replay remains blocked.
- User licensing classification (personal vs commercial; display vs
  non-display; internal vs external/redistribution) is unknown and materially
  changes entitlement and cost.
- V8 remains deliberately open because Phase 10's live source is not selected.
- E1/E2 matching and modification-priority rules are outside this vendor report
  and still block trusted simulated queue/limit-order conclusions.

Accordingly, this report is sufficient to frame a controlled vendor evidence
request, but **not** sufficient to select a vendor or begin Phase 1 ingestion.
