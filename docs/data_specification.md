# Data Specification

Status: **proposed, pre-implementation.**

Authority over: canonical event schemas, provenance requirements, the data
capability matrix, and market-specific data semantics.

---

## 1. Non-negotiables

1. Raw data is immutable. Pipeline code never edits or deletes it.
2. Derived data is reproducible and disposable.
3. No feature may depend on unavailable information. If required information
   is unavailable, we do not invent an approximation and present it as
   equivalent — we record the gap in the capability matrix.
4. Every event distinguishes **exchange timestamp**, **receive timestamp**,
   and **sequence number**.
5. Prices are integers. Float prices are forbidden in storage, comparison,
   and accounting.
6. All internal timestamps are UTC nanoseconds since epoch (`int64`). Local
   exchange time exists only in session definitions and human-facing output.
7. Synthetic data is permitted only as labelled test fixtures.

---

## 2. Data capability matrix

Filled in per instrument and per vendor **before** designing any feature that
depends on the capability. `Reconstructable` means derivable from a lower
level without inventing information (e.g. BBO from an MBO book).

| Capability | Required data | Granularity | Historical | Live | Reconstructable | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Trade price / size / time | Trades (L1) | event | TBD | TBD | no | — |
| Aggressor side (exchange-supplied) | Trades with aggressor flag | event | TBD | TBD | no | — |
| Aggressor side (inferred) | Trades + BBO | event | TBD | TBD | yes (lossy) | — |
| Best bid/offer | BBO / MBP-1 | event | TBD | TBD | from MBP-10 or MBO | — |
| Depth to 10 levels | MBP-10 | event | TBD | TBD | from MBO | — |
| Full book by order | MBO (L3) | event | TBD | TBD | no | — |
| Order add/cancel/modify | MBO | event | TBD | TBD | no | — |
| Queue position | MBO | event | TBD | TBD | no | — |
| Sweep identification | Trades + book deltas | event | TBD | TBD | partial | — |
| Volume at price | Trades | event | TBD | TBD | yes | — |
| TPO structure | Trades or 30-min bars | 30-min | TBD | TBD | yes | — |
| Session / auction state | Status messages | event | TBD | TBD | partial | — |
| Instrument definitions | Vendor definition records | daily | TBD | TBD | no | — |
| Settlement prices | Vendor statistics | daily | TBD | TBD | no | — |
| Options positioning / GEX | Options chains + OI | daily | out of scope | out of scope | no | — |

**Rules attached to this table:**

- `TBD` must be replaced by a verified yes/no with a citation to vendor
  documentation before any dependent feature is implemented. We do not
  assume a vendor supports something.
- A feature whose required capability is `no` for the target instrument is
  **not implemented**. It is documented as blocked, with the minimum
  additional data required and the assumptions an approximation would
  introduce.
- Inferred capabilities are always flagged in event provenance so downstream
  analysis can segregate them.

---

## 3. Canonical event schemas

All events carry a common envelope:

| Field | Type | Meaning |
| --- | --- | --- |
| `ts_event` | `int64` | Exchange event timestamp, UTC ns. Primary ordering key. |
| `ts_recv` | `int64 \| null` | Capture/receive timestamp, UTC ns. Null if the vendor does not supply it. |
| `sequence` | `int64 \| null` | Venue sequence number, preserved verbatim. |
| `instrument_id` | `int32` | Internal id resolved from the instrument registry. |
| `venue` | `str` | e.g. `GLBX`. |
| `provenance_id` | `int32` | Index into the run manifest: vendor, dataset, transformation version, inference flags. |

### 3.1 Trade

| Field | Type | Notes |
| --- | --- | --- |
| `price` | `int64` | Fixed-point, 1e-9 units. Tick index derived via instrument `tick_size`. |
| `size` | `uint32` | Contracts. |
| `aggressor` | `enum{BUY, SELL, UNKNOWN}` | `BUY` = buyer initiated (lifted the offer). |
| `aggressor_source` | `enum{EXCHANGE, INFERRED_QUOTE, INFERRED_TICK}` | Never silently inferred. |
| `trade_id` | `int64 \| null` | Venue trade identifier where available. |
| `flags` | `uint8` | Vendor flags preserved (e.g. last-in-packet, implied). |

`aggressor = UNKNOWN` is a legitimate value. Order-flow features must define
their behaviour when it occurs, and must not silently treat it as zero delta
without recording the excluded volume.

### 3.2 Quote (BBO / MBP-1)

`bid_px`, `bid_sz`, `bid_ct`, `ask_px`, `ask_sz`, `ask_ct` (`int64`/`uint32`).
Crossed or locked quotes are recorded as received and flagged by L1, never
"fixed".

### 3.3 BookSnapshot

`depth` (levels captured), and per level `bid_px`, `bid_sz`, `bid_ct`,
`ask_px`, `ask_sz`, `ask_ct`. Carries `is_synthetic` when reconstructed from
deltas rather than delivered as a snapshot.

### 3.4 BookDelta (MBP)

`action` (`ADD`, `CANCEL`, `MODIFY`, `CLEAR`, `TRADE`, `FILL`), `side`
(`BID`, `ASK`, `NONE`), `price`, `size`, `level`. Book state is rebuilt by
applying deltas in `(ts_event, sequence)` order; a rebuild that violates
integrity invariants raises rather than repairs.

### 3.5 OrderEvent (MBO / L3)

Adds `order_id` and, where derivable, `priority`. This is the only source
that supports true queue-position modelling.

### 3.6 InstrumentDef

`instrument_id`, `raw_symbol`, `product`, `exchange`, `tick_size`,
`tick_value`, `multiplier`, `currency`, `activation`, `expiration`,
`min_lot`, `security_type`, `definition_ts`. Sourced from vendor definition
records, never hand-typed.

### 3.7 SessionDef

`session_id`, `instrument_id`, `trade_date`, `timezone`,
`calendar_version`, and ordered `segments[]` of
`(name, start_ts_utc, end_ts_utc)`.

For CME equity-index and FX futures the initial segmentation is: `PRE_OPEN`,
`OVERNIGHT` (Globex), `RTH`, `POST`, `SETTLEMENT`. Exact boundaries are
resolved per trade date from an exchange calendar, including holiday and
early-close dates, and the calendar version is recorded. Nothing infers a
session from a wall-clock comparison in feature code.

### 3.8 StatusEvent / AuctionEvent

`status` (`PRE_OPEN`, `OPEN`, `PAUSE`, `HALT`, `RESUME`, `CLOSE`,
`SETTLEMENT`, `UNKNOWN`), `reason`, `is_trading`. Features and the simulator
must define behaviour under halt and auction states.

---

## 4. Ordering and identity

Canonical ordering key: `(ts_event, sequence, ingest_index)` where
`ingest_index` is the position in the source file, used only to break exact
ties deterministically.

Original identity is preserved: `sequence`, `trade_id`, `order_id`, and
vendor flags are never dropped during normalization. Replay reproduces the
exact ordering.

---

## 5. Provenance and dataset manifests

Every canonical partition and every derived dataset writes a manifest:

```json
{
  "dataset_id": "canonical/GLBX/NQ/2024-03-11",
  "source": {"vendor": "<vendor>", "dataset": "<vendor dataset id>",
             "request": {...}, "retrieved_at": "...",
             "raw_sha256": ["..."]},
  "instrument": {"raw_symbol": "NQH4", "instrument_id": 1234,
                 "definition_ts": "..."},
  "date_range": {"start": "...", "end": "..."},
  "timezone": "UTC",
  "session_definition": {"calendar_version": "cme-2024.1",
                         "session_id": "..."},
  "transformation_version": "normalize@1.2.0",
  "feature_version": null,
  "inference_flags": ["aggressor_source=EXCHANGE"],
  "code_revision": "<git sha>",
  "generated_at": "...",
  "quality_report": "quality/GLBX/NQ/2024-03-11.json"
}
```

A derived dataset without a complete manifest is invalid and must not be used
in an experiment.

---

## 6. Storage layout

```
data/
  raw/<vendor>/<dataset>/<instrument>/<date>/<file>        # immutable + .manifest.json
  quality/<venue>/<instrument>/<date>.json
  canonical/<venue>/<instrument>/<date>/<event_type>.parquet
  features/<venue>/<instrument>/<date>/<feature_id>.parquet
  runs/<run_id>/                                           # backtest + validation artifacts
```

`data/` is gitignored. Manifests make any partition reconstructible from raw.

---

## 7. Data quality checks

**Hard (quarantine on failure):** timestamp monotonicity within a partition;
sequence gaps beyond vendor-documented tolerance; book integrity (crossed,
negative size, level count mismatch); trade prices outside the day's
recorded range; missing instrument definition; session coverage below
threshold.

**Soft (report and flag):** unusual message-rate spikes or dropouts, zero-
volume periods inside RTH, elevated `UNKNOWN` aggressor share, unusually wide
spread persistence, `is_synthetic` snapshot share.

Quality reports are stored and referenced by every downstream manifest. An
experiment that consumed a partition with an open hard failure is invalid.

---

## 8. Market-specific semantics

### CME futures (NQ, ES, 6E) — initial scope

Single central limit order book per contract; exchange-supplied aggressor
side on trades; explicit instrument definitions; implied orders exist and are
flagged; contract roll is a first-class policy (see
`docs/architecture.md` §5). Research prices are per-contract and unadjusted.

### Crypto (future)

No consolidated book. Every dataset is venue-scoped; spot, perpetual, and
dated futures are distinct instruments with distinct semantics (funding,
liquidation cascades, 24/7 sessions). Cross-venue aggregation requires an
explicitly defined and documented model, and is not the default.

### US equities (future)

Fragmented venues; consolidated tape versus venue book distinctions; odd
lots; corporate actions; halts and LULD bands; opening and closing auctions;
regular versus extended hours. None of this maps onto the futures session
model, so it requires its own `SessionDef` and reference-data handling.

### Spot FX

No globally centralized order book. Not used. FX research uses the 6E
future.

---

## 9. Known limitations to state in every report

- Historical MBO/MBP is a capture of a feed, not a perfect record of exchange
  state; sequence gaps and vendor normalization exist.
- Inferred aggressor side is lossy at and inside the spread.
- Queue position is unknowable without MBO and is a model even with it.
- Latency between our decision point and the exchange is assumed, not
  measured, until a live paper-trading link exists.
