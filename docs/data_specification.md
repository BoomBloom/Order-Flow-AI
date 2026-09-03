# Data Specification

Status: **proposed, pre-implementation.**

Authority over: canonical event schemas, provenance tiers, per-partition
capability records, the data capability matrix, and market-specific data
semantics.

---

## 1. Non-negotiables

1. Raw data is immutable. Pipeline code never edits or deletes it.
2. Derived data is reproducible and disposable.
3. No feature may depend on unavailable information. If required information
   is unavailable, we do not invent an approximation and present it as
   equivalent — we record the gap in the capability matrix.
4. Every event distinguishes **exchange timestamp** (`ts_event`), **receive
   timestamp** (`ts_recv`), and **sequence number**.
5. Every quantity carries a **provenance tier** (§2).
6. Prices are integers. Float prices are forbidden in storage, comparison,
   and accounting. Tick-grid conversion is exact-only.
7. All internal timestamps are UTC nanoseconds since epoch (`int64`). Local
   exchange time exists only in session definitions and human-facing output.
8. Partitions are keyed on **`trade_date`**, the exchange session date.
9. Synthetic data is permitted only as labelled test fixtures.

---

## 2. Provenance tiers

| Tier | Definition | Typical examples |
| --- | --- | --- |
| `OBSERVED` | Present in the vendor feed as delivered | trade price and size, exchange-supplied aggressor flag, `ts_event`, instrument definitions |
| `RECONSTRUCTED` | Deterministically derived from observed data; no free parameters, no counterfactual | BBO derived from MBO, book state from applied deltas, volume-at-price from trades |
| `INFERRED` | Derived by a heuristic with a non-zero error rate | tick-rule or quote-rule aggressor side, sweep classification from trade clustering |
| `SIMULATED` | Counterfactual — describes a hypothetical order of ours that never existed | queue position, fill, fill price, slippage, latency effect |

Rules:

- `INFERRED` is **not** a lossy `RECONSTRUCTED`. Reconstruction is
  deterministic and exact; inference can be wrong. They are never merged into
  one column value or one confidence label.
- Features declare the minimum acceptable tier for each input. A run that
  would supply a weaker tier fails rather than silently degrading
  `[ENFORCED]`.
- `SIMULATED` quantities are never described as measured or observed, in
  code, in reports, or in commit messages.
- Every stored column and every derived quantity resolves to exactly one
  tier, recorded in the partition manifest.

---

## 3. Capability records (per partition)

Capability is **not** a static property of a vendor. It varies by partition:
aggressor flags can be present on most days and absent on some; MBP-10 depth
can truncate during bursts; `ts_recv` can be present in one dataset vintage
and absent in another.

Every canonical partition manifest therefore carries a capability record:

```json
{
  "capabilities": {
    "TRADES":      {"present": true,  "tier": "OBSERVED"},
    "AGGRESSOR":   {"present": true,  "tier": "OBSERVED", "unknown_share": 0.003},
    "BBO":         {"present": true,  "tier": "OBSERVED"},
    "MBP_10":      {"present": true,  "tier": "OBSERVED", "truncation_events": 12},
    "MBO":         {"present": false, "tier": null},
    "TS_RECV":     {"present": false, "tier": null,
                    "assumed_feed_delay_ns": 350000,
                    "assumption_source": "run config, stress-tested"},
    "STATUS":      {"present": true,  "tier": "OBSERVED"}
  }
}
```

Enforcement `[ENFORCED]`:

- The store asserts the capability record on read against the declared
  requirement of every feature in the run.
- A missing capability, or one at a weaker tier than declared acceptable,
  fails the run. It never degrades silently.
- Capability records are aggregated per experiment so a result can state
  exactly which partitions supplied which tier.

### 3.1 Historical / live compatibility

A research conclusion is transferable to paper trading only if the live
capability record is a **superset at an equal or stronger provenance tier**
than the record the research consumed `[ENFORCED]`.

A conclusion built on `OBSERVED` aggressor side may not be paper traded on a
live feed offering only `INFERRED` aggressor side. Where research assumed a
feed delay and the live feed supplies real `ts_recv`, the difference between
assumed and observed delay is reported as part of the paper-trading
acceptance test (`docs/architecture.md` §12.1).

---

## 4. Data capability matrix

Filled in per instrument and per vendor **before** designing any feature that
depends on the capability. `Reconstructable` uses the §2 vocabulary strictly.

| Capability | Required data | Granularity | Historical | Live | Derivable as | Verified by / date / source |
| --- | --- | --- | --- | --- | --- | --- |
| Trade price / size / time | Trades (L1) | event | TBD | TBD | — | — |
| Aggressor side (exchange) | Trades with aggressor flag | event | TBD | TBD | — | — |
| Aggressor side (heuristic) | Trades + BBO | event | TBD | TBD | `INFERRED` | — |
| Receive timestamp (`ts_recv`) | Capture timestamps | event | TBD | TBD | — | — |
| Best bid/offer | BBO / MBP-1 | event | TBD | TBD | `RECONSTRUCTED` from MBP-10 or MBO | — |
| Depth to 10 levels | MBP-10 | event | TBD | TBD | `RECONSTRUCTED` from MBO | — |
| Full book by order | MBO (L3) | event | TBD | TBD | — | — |
| Order add/cancel/modify | MBO | event | TBD | TBD | — | — |
| Queue position | MBO + priority rule | event | TBD | TBD | `SIMULATED` only | — |
| Sweep identification | Trades + book deltas | event | TBD | TBD | `INFERRED` | — |
| Volume at price | Trades | event | TBD | TBD | `RECONSTRUCTED` | — |
| TPO structure | Trades or 30-min bars | 30-min | TBD | TBD | `RECONSTRUCTED` | — |
| Session / auction state | Status messages | event | TBD | TBD | partial | — |
| Instrument definitions | Vendor definition records | daily | TBD | TBD | — | — |
| Settlement prices | Vendor statistics | daily | TBD | TBD | — | — |
| Options positioning / GEX | Options chains + OI | daily | out of scope | out of scope | — | — |

**Rules attached to this table:**

- `TBD` must be replaced by a verified yes/no, with the verifier's name, the
  date, and the vendor documentation version, before any dependent feature is
  implemented. We do not assume a vendor supports something.
- **Queue position is never `OBSERVED` or `RECONSTRUCTED`.** Even with full
  MBO we reconstruct the *book's* state and then simulate a hypothetical
  order's insertion under a priority assumption. It is `SIMULATED` by
  definition.
- A feature whose required capability is absent for the target instrument is
  **not implemented**. It is documented as blocked, with the minimum
  additional data required and the assumptions an approximation would
  introduce.
- Unverified rows are mirrored in `docs/limitations.md`.

---

## 5. Canonical event schemas

Canonical events are frozen, slotted, typed structures — not validated models
(`docs/architecture.md` §13). Validation happens where data enters, not per
event.

All events carry a common envelope:

| Field | Type | Meaning |
| --- | --- | --- |
| `ts_event` | `int64` | Exchange event timestamp, UTC ns. **Ordering key. Never the decision clock.** |
| `ts_recv` | `int64 \| null` | Capture/receive timestamp, UTC ns. **The decision clock.** Null if the vendor does not supply it. |
| `sequence` | `int64 \| null` | Venue sequence number, preserved verbatim. |
| `instrument_id` | `int32` | Internal id resolved from the instrument registry. |
| `trade_date` | `date` | Exchange session date, assigned by the L4 calendar. |
| `venue` | `str` | e.g. `GLBX`. |
| `provenance_id` | `int32` | Index into the run manifest: vendor, dataset, transformation version, per-field tiers. |

### 5.1 Trade

| Field | Type | Notes |
| --- | --- | --- |
| `price` | `int64` | Fixed-point, 1e-9 units. Tick index derived via instrument `tick_size`, exact-only. |
| `size` | `uint32` | Contracts. |
| `aggressor` | `enum{BUY, SELL, UNKNOWN}` | `BUY` = buyer initiated (lifted the offer). |
| `aggressor_tier` | `enum{OBSERVED, INFERRED}` | Never silently inferred. |
| `trade_id` | `int64 \| null` | Venue trade identifier where available. |
| `flags` | `uint8` | Vendor flags preserved (e.g. last-in-packet, implied). |

`aggressor = UNKNOWN` is a legitimate value. Order-flow features must define
their behaviour when it occurs, and must not silently treat it as zero delta
without recording the excluded volume. The per-partition `unknown_share` is
part of the capability record.

### 5.2 Quote (BBO / MBP-1)

`bid_px`, `bid_sz`, `bid_ct`, `ask_px`, `ask_sz`, `ask_ct` (`int64`/`uint32`).
Crossed or locked quotes are recorded as received and flagged by L1b, never
"fixed".

### 5.3 BookSnapshot

`depth` (levels captured), and per level `bid_px`, `bid_sz`, `bid_ct`,
`ask_px`, `ask_sz`, `ask_ct`. Carries `is_synthetic` when `RECONSTRUCTED`
from deltas rather than delivered as a snapshot.

### 5.4 BookDelta (MBP)

`action` (`ADD`, `CANCEL`, `MODIFY`, `CLEAR`, `TRADE`, `FILL`), `side`
(`BID`, `ASK`, `NONE`), `price`, `size`, `level`. Book state is rebuilt by
applying deltas in `(ts_event, sequence)` order; a rebuild that violates
integrity invariants raises rather than repairs.

### 5.5 OrderEvent (MBO / L3)

Adds `order_id` and, where derivable, `priority`. This is the only source
that supports a defensible **simulated** queue position — and even then only
under a verified venue priority rule (`docs/architecture.md` §9.3).

### 5.6 InstrumentDef

`instrument_id`, `raw_symbol`, `product`, `exchange`, `tick_size`,
`tick_value`, `multiplier`, `currency`, `activation`, `expiration`,
`min_lot`, `security_type`, `definition_ts`. Sourced from vendor definition
records, never hand-typed.

### 5.7 SessionDef

`session_id`, `instrument_id`, `trade_date`, `timezone`, `calendar_version`,
and ordered `segments[]` of `(name, start_ts_utc, end_ts_utc)`.

For CME equity-index futures the initial segmentation is: `PRE_OPEN`,
`OVERNIGHT` (Globex), `RTH`, `POST`, `SETTLEMENT`. **This segmentation is not
assumed to apply to 6E** — FX futures conventions differ and are UNVERIFIED
(`docs/limitations.md`). Boundaries are resolved per `trade_date` from an
exchange calendar including holidays and early closes, with the calendar
version recorded. Nothing infers a session from a wall-clock comparison in
feature code.

### 5.8 StatusEvent / AuctionEvent

`status` (`PRE_OPEN`, `OPEN`, `PAUSE`, `HALT`, `RESUME`, `CLOSE`,
`SETTLEMENT`, `UNKNOWN`), `reason`, `is_trading`. Features and the simulator
must define behaviour under halt and auction states, including whether a
resume triggers `on_reset(HALT_RESUME)`.

---

## 6. Ordering, identity, and the clock

**Ordering key:** `(ts_event, sequence, ingest_index)`, where `ingest_index`
is the position in the source file, used only to break exact ties
deterministically.

`sequence` monotonicity within a partition is a **per-vendor property to be
verified**, not assumed — venue sequence numbers are often per-channel and
may reset. `ingest_index` is the guaranteed tiebreaker regardless.

**Decision clock:** `ts_recv`. `ts_event` orders the stream and never
triggers a decision. Where `ts_recv` is absent, the run supplies
`assumed_feed_delay_ns` and the decision clock becomes
`ts_event + assumed_feed_delay_ns`, recorded in the run manifest and reported
with every dependent result (`docs/architecture.md` §9.1).

Original identity is preserved: `sequence`, `trade_id`, `order_id`, and
vendor flags are never dropped during normalization. Replay reproduces the
exact ordering.

---

## 7. Labels

Labels are **not** events and **not** features. They are computed in a
separate, explicitly marked pass (`src/ofa/labels/`) that is permitted to
read future data, because that is what a label is.

Every label dataset records:

- `label_definition` and version
- `label_horizon` — the maximum event or wall-clock distance into the future
  consumed
- the barrier or outcome parameters
- the events from which the outcome was determined, for replay

`label_horizon` drives purge width in every split scheme
(`docs/research_protocol.md` §4). No module under `features/` may import
`labels/` `[ENFORCED]`.

---

## 8. Provenance and dataset manifests

Every canonical partition and every derived dataset writes a manifest:

```json
{
  "dataset_id": "canonical/GLBX/NQ/2024-03-11",
  "source": {"vendor": "<vendor>", "dataset": "<vendor dataset id>",
             "request": {...}, "retrieved_at": "...",
             "raw_sha256": ["..."]},
  "instrument": {"raw_symbol": "NQH4", "instrument_id": 1234,
                 "definition_ts": "..."},
  "trade_date": "2024-03-11",
  "date_range": {"start": "...", "end": "..."},
  "timezone": "UTC",
  "session_definition": {"calendar_version": "cme-2024.1",
                         "session_id": "..."},
  "capabilities": { "...": "..." },
  "field_provenance": {"aggressor": "OBSERVED", "bbo": "OBSERVED"},
  "transformation_version": "normalize@1.2.0",
  "feature_version": null,
  "label_version": null,
  "code_revision": "<git sha>",
  "generated_at": "...",
  "quality_reports": {"raw": "quality/raw/GLBX/NQ/2024-03-11.json",
                      "semantic": "quality/semantic/GLBX/NQ/2024-03-11.json"}
}
```

A derived dataset without a complete manifest is invalid and must not be used
in an experiment.

---

## 9. Storage layout

```
data/
  raw/<vendor>/<dataset>/<instrument>/<trade_date>/<file>   # immutable + .manifest.json
  quality/raw/<venue>/<instrument>/<trade_date>.json        # L1a
  quality/semantic/<venue>/<instrument>/<trade_date>.json   # L1b
  canonical/<venue>/<instrument>/<trade_date>/<event_type>.parquet
  features/<venue>/<instrument>/<trade_date>/<feature_id>.parquet
  labels/<venue>/<instrument>/<trade_date>/<label_id>.parquet
  runs/<run_id>/                                            # backtest + validation artifacts
```

`data/` is gitignored. Manifests make any partition reconstructible from raw.

---

## 10. Data quality checks

### 10.1 L1a — raw structural (pre-normalization)

**Hard (quarantine on failure):** checksum mismatch against the acquisition
manifest; timestamp monotonicity violations within a file; sequence gaps
beyond vendor-documented tolerance; record count mismatch; session coverage
below threshold; missing instrument definition.

**Soft (report and flag):** message-rate spikes or dropouts, unusually small
or large file size for the instrument-date.

### 10.2 L1b — semantic (post-normalization)

**Hard:** book integrity (crossed, locked, negative size, level-count
mismatch); trade prices outside the day's recorded range; `trade_date`
assignment inconsistent with the session calendar.

**Soft:** elevated `UNKNOWN` aggressor share; persistent wide spread;
`is_synthetic` snapshot share above threshold; zero-volume periods inside
RTH; MBP-10 truncation events.

Both reports are stored and referenced by every downstream manifest. An
experiment that consumed a partition with an open hard failure is invalid.

---

## 11. Market-specific semantics

### CME futures (NQ, ES, 6E) — initial scope

Single central limit order book per contract; exchange-supplied aggressor
side on trades (to be verified per vendor); explicit instrument definitions;
implied orders exist and are flagged; contract roll is a first-class policy
(`docs/architecture.md` §5). Research prices are per-contract and unadjusted.

Matching-algorithm assumptions (FIFO price-time priority for these outrights)
are **UNVERIFIED** and are tracked in `docs/limitations.md`. No queue model
may be relied upon for a conclusion until they are verified against the CME
rulebook.

### Crypto (future)

No consolidated book. Every dataset is venue-scoped; spot, perpetual, and
dated futures are distinct instruments with distinct semantics (funding,
liquidation cascades, 24/7 sessions — where `trade_date` needs its own
definition). Cross-venue aggregation requires an explicitly defined and
documented model, and is not the default.

### US equities (future)

Fragmented venues; consolidated tape versus venue book distinctions; odd
lots; corporate actions; halts and LULD bands; opening and closing auctions;
regular versus extended hours. None of this maps onto the futures session
model, so it requires its own `SessionDef` and reference-data handling.

### Spot FX

No globally centralized order book. Not used. FX research uses the 6E
future.

---

## 12. Known limitations to state in every report

- Historical MBO/MBP is a capture of a feed, not a perfect record of exchange
  state; sequence gaps and vendor normalization exist.
- `INFERRED` aggressor side is wrong some of the time, especially at and
  inside the spread.
- Queue position is `SIMULATED` and depends on a venue priority rule that is
  currently UNVERIFIED.
- Where `ts_recv` is unavailable, the decision clock rests on an assumed feed
  delay, which is a configured assumption and not a measurement.
- Self-impact and market impact are unmodelled; see `docs/architecture.md`
  §9.4.
