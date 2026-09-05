# Phase 1 planning and decision package

Date: 2026-09-06. Status: planning artifact; Phase 1A remains open.
Baseline: `55fc6bfe6fe6c8856db15510f3d744acc07acc09`.

## Objective and authority

Deliver the smallest auditable NQ data spine after evidence and design gates
pass. `roadmap.md` owns sequencing, `architecture.md` owns module boundaries,
and `data_specification.md` owns data semantics. This plan organizes work; it
does not finalize `CanonicalEvent`, `Feature`, `Lookback` or a vendor choice.

Repository Phase 1A corresponds to master Phase 1 (vendor evidence), 1B to
master Phase 2 (event contract), 1C to master Phase 3 (acquisition/normalization),
and 1D to master Phase 4 (store/replay). Repository Phase 2 retains full
reference/session/roll coverage and extends a bounded prerequisite from 1B.
Feature/Lookback opens before repository Phase 3; label contracts remain in
repository Phase 5 before validation needs label-horizon purging. These are
sequencing clarifications, not changes to the deterministic architecture.

## Current evidence and proposed use of references

- [Repository audit](reference_repository_audit.md): all 38 named public
  repositories assessed; large projects sampled, fork divergence not fully
  resolved. Rankings are qualitative and do not authorize reuse.
- [Vendor matrix](vendor_capability_matrix.md): dated primary-source claims,
  capture-point and snapshot caveats, unknowns and approval requirements.
  Public documentation is not proof of a purchased partition's contents.
- Candidate design inputs for discussion: Nautilus adapter/event boundaries;
  Lean scenario checklists; OpenBB provider registration. Independently derive
  OFA designs and fixtures after inspecting relevant pinned source and license.
- Later candidates: decision-time causal tests from ML4T/Freqtrade and research
  records from Qlib. No reference-derived feature, framework or strategy is
  selected by this plan. Preserve the user's requested idea discussion.

## Vendor decision package — 1A

These comparisons summarize the linked vendor matrix, researched 2026-09-05;
recheck commercial terms before requesting a quote or access.

| Candidate | What makes it worth evaluating | What blocks selection |
| --- | --- | --- |
| Databento GLBX.MDP3 | Detailed public event schemas, vendor-capture timestamps and historical/live schema families | Consumer availability differs from capture time; snapshot and sequence mapping unresolved; exact contract/date coverage, quote, license and sample quality unverified |
| Rithmic | Advertised CME depth/MBO and historical access; potentially relevant to existing user access | Trader Pro entitlement does not prove API entitlement; historical receive time, sequence, aggressor, schema vintage and price require technical answers |
| CME DataMine | Exchange-owned historical products and direct protocol evidence | Purchased-file fields cannot be inferred from live MDP; exact layout, receive timestamps, entitlement, quote and sample are unknown |

Public Databento plan headlines in the evidence report are $199/$1,750/$4,500
monthly. They are not quotes for this historical sample or a proposed purchase.
No exact bounded NQ acquisition cost is established for any candidate.

Request from the user, before account-specific work:

1. Intended use: personal/internal research or commercial/distributed outputs;
   this is an input to vendor licensing confirmation, not a legal determination.
2. Existing permitted access: vendor/broker/platform and entitlement documents,
   with secrets omitted. Do not infer API rights from a platform login.
3. Which candidate may be contacted or used for a quote/sample, and a spending
   ceiling if paid work is authorized. Candidate evaluation is not vendor lock.

Before contact, prepare the exact request: NQ outright contract and date range
to be agreed, trades+BBO minimum, optional MBP-10/MBO quoted separately, normal
trading plus pause/reopen, burst and applicable recovery/snapshot periods.
Ask for field layout/version, timestamp capture points, sequence domains and
resets, aggressor unknown cases, reference/status coverage, permitted local
retention, use/redistribution restrictions, fees, byte volume and API rights.
Do not send a request, create an account or use credentials without approval.

After approved sample access, inspect raw bytes and hashes, flags, timestamp
meaning, sequence/recovery behavior, tick grids, event actions and provenance.
Record gaps and counterexamples as well as positive evidence. Samples belong
outside Git under the approved data policy. This bounded evidence inspection
is not a production adapter or a substitute for schema-design review.

Close 1A only with an explicit source/tier decision and the required V1–V6
source-field and entitlement evidence for the selected scope. Canonical
mapping belongs to 1B; V2/V6 close only after both evidence and mapping are
resolved, so 1A does not depend on an unbuilt canonical schema.
Verified absence of optional depth/MBO is
valid; silently substituting inferred data is not. V7 must be measured before
scaling; V8 remains a later live-transfer gate.

## Event and prerequisite design agenda — 1B

All rows below are unresolved. The design record must evaluate alternatives,
name the chosen policy and evidence, undergo independent review, and obtain
approval for any change to locked semantics before implementation.

| Decision | Evidence/alternatives to evaluate | Required adversarial checks |
| --- | --- | --- |
| D4 envelope representation | Raw integer fields versus existing core value types, preserving frozen/slotted structures and boundary-only validation | Wrong units/types, exact fixed-point boundaries, missing fields, stable serialization and schema evolution |
| Receive-time capture point | Vendor capture, vendor egress and OFA consumer receipt are distinct; preserve source time and evaluate recorded downstream-delay treatment | Earlier capture must not masquerade as later consumer availability; explicit fallback when receipt is absent; historical/live boundary compatibility |
| Sequence and ingest index | Per-schema native sequence field/domain/channel/version, missing sequence, reset epochs and deterministic ingest-index assignment | Same timestamps, cross-channel values, resets, duplicates, recovery and shuffled physical storage; preserve `(ts_event, sequence, ingest_index)` |
| Snapshots/reset controls | Exclusion with explicit state initialization versus typed boundary controls; preserve raw flags and old timestamps | Stale snapshot `ts_event` cannot move state into the past; incomplete/duplicate initialization rejected; bad receive-time flags retained |
| Instrument/session prerequisite | Existing registry and L4 own identity, tick grid and `trade_date`; bounded selected contract/date coverage | Sunday open, pause/reopen, DST and any holiday/early close in the range; unresolved assignments rejected, no UTC-date truncation |
| D5/D6 and X2 metadata | Manifest identity, venue, reference versions, quality definitions and injected wall-clock metadata; dependency approval separate | Missing provenance/capabilities rejected; structural depth distinguished from loss; metadata reproducible from explicit inputs |
| Vendor-field ownership | Resolve architecture's adapter-only vendor awareness versus L2 vendor field names and L1a raw inspection before 1C | Vendor objects cannot escape the approved boundary; raw quality and normalization ownership must be unambiguous |

The clock rule remains `ts_recv`, with explicit recorded fallback if absent.
This agenda does not rename it, add an implicit delay, or change ordering.
Snapshot alternatives are proposals, not a new canonical control schema.
Schema-specific source preservation must not promote reconstructed/inferred
or synthetic values to observed market facts.

## Later implementation and verification

Follow the 1C/1D acceptance gates in `roadmap.md`. Keep vendor objects in the
adapter, raw acquisition immutable and canonical processing offline. Reject
unavailable capabilities. Repeated replay must be independent of file listing
order, hash seed and wall clock. Record transformations and all assumptions.

Review with an independent correctness/temporal reviewer for 1B, adding
microstructure review for book/snapshot semantics. Root integrates changes and
runs `make check`, `make guards`, relevant new contract/integration tests,
`git diff --check`, and real CI for the exact pushed revision. No new test is
claimed implemented by this planning document.

The planning milestone is complete when the roadmap and PLAN agree on
dependencies, this package identifies concrete open decisions, review findings
are resolved, and CI succeeds. Phase 1 itself remains incomplete until 1D.
