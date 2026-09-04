"""Property tests for data requirements and capability records.

The flag properties exist because of a specific defect: ``Flag.name`` for a
composite joins members in *declaration* order, so a canonical form built from
it would move whenever someone reordered an enum. These tests assert the
canonical form depends on the value alone.
"""

from __future__ import annotations

import json
from typing import Final

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ofa.core.capability import CapabilityEntry, CapabilityRecord, DataRequirement
from ofa.core.errors import IncomparableProvenanceError
from ofa.core.hashing import canonical_bytes, content_hash
from ofa.core.provenance import ProvenanceTier

DR: Final = DataRequirement
MEMBERS: Final[list[DataRequirement]] = list(DR)
DATA_TIERS: Final[list[ProvenanceTier]] = [
    ProvenanceTier.OBSERVED,
    ProvenanceTier.RECONSTRUCTED,
    ProvenanceTier.INFERRED,
]

member_sets = st.lists(st.sampled_from(MEMBERS), unique=True, max_size=len(MEMBERS))
data_tiers = st.sampled_from(DATA_TIERS)
all_tiers = st.sampled_from(list(ProvenanceTier))


def _combine(members: list[DataRequirement]) -> DataRequirement:
    combined = DR(0)
    for member in members:
        combined |= member
    return combined


def _entry(present: bool, tier: ProvenanceTier | None) -> CapabilityEntry:
    return CapabilityEntry(present=present, tier=tier)


# --------------------------------------------------------------------------
# Flag canonicalization
# --------------------------------------------------------------------------


@given(member_sets, st.randoms(use_true_random=False))
def test_canonical_form_ignores_the_order_members_were_combined_in(
    members: list[DataRequirement], rng: object
) -> None:
    shuffled = list(members)
    rng.shuffle(shuffled)  # type: ignore[attr-defined]
    assert canonical_bytes(_combine(members)) == canonical_bytes(_combine(shuffled))
    assert content_hash(_combine(members)) == content_hash(_combine(shuffled))


@given(member_sets)
def test_canonical_payload_is_the_sorted_member_names(
    members: list[DataRequirement],
) -> None:
    node = json.loads(canonical_bytes(_combine(members)).decode("ascii"))
    assert node[0] == "flag"
    # Every single-bit member has a name; only composites and the empty value
    # can be nameless, and neither appears in this list.
    names = [member.name for member in members]
    assert None not in names
    assert node[3] == sorted(name for name in names if name is not None)


@given(member_sets)
def test_every_flag_value_canonicalizes_without_raising(
    members: list[DataRequirement],
) -> None:
    """Including the empty flag, whose name is None."""
    produced = canonical_bytes(_combine(members))
    produced.decode("ascii")
    assert len(content_hash(_combine(members))) == 64


@given(member_sets, member_sets)
def test_equal_flags_agree_and_unequal_flags_differ(
    left: list[DataRequirement], right: list[DataRequirement]
) -> None:
    first, second = _combine(left), _combine(right)
    if first == second:
        assert canonical_bytes(first) == canonical_bytes(second)
    else:
        assert canonical_bytes(first) != canonical_bytes(second)
        assert content_hash(first) != content_hash(second)


@given(member_sets)
def test_a_flag_never_shares_a_canonical_form_with_its_integer(
    members: list[DataRequirement],
) -> None:
    combined = _combine(members)
    assert canonical_bytes(combined) != canonical_bytes(combined.value)


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@st.composite
def records(draw: st.DrawFn) -> CapabilityRecord:
    members = draw(member_sets)
    pairs: list[tuple[DataRequirement, CapabilityEntry]] = []
    for member in members:
        present = draw(st.booleans())
        tier = draw(all_tiers) if present else None
        pairs.append((member, _entry(present, tier)))
    return CapabilityRecord(tuple(pairs))


@given(records(), st.randoms(use_true_random=False))
def test_record_equality_and_canonical_form_ignore_entry_order(
    record: CapabilityRecord, rng: object
) -> None:
    shuffled = list(record.entries)
    rng.shuffle(shuffled)  # type: ignore[attr-defined]
    rebuilt = CapabilityRecord(tuple(shuffled))
    assert rebuilt == record
    assert canonical_bytes(rebuilt) == canonical_bytes(record)
    assert content_hash(rebuilt) == content_hash(record)


@given(records())
def test_record_preserves_every_entry_it_was_given(record: CapabilityRecord) -> None:
    for capability, entry in record.entries:
        assert record.entry(capability) is entry


@given(records())
def test_present_is_exactly_the_entries_recorded_present(
    record: CapabilityRecord,
) -> None:
    expected = _combine([capability for capability, entry in record.entries if entry.present])
    assert record.present == expected


@given(records(), member_sets, data_tiers)
def test_unmet_agrees_with_an_independent_walk(
    record: CapabilityRecord, members: list[DataRequirement], minimum: ProvenanceTier
) -> None:
    required = _combine(members)
    simulated = any(
        entry.tier is ProvenanceTier.SIMULATED
        for capability, entry in record.entries
        if capability in required
    )
    if simulated:
        with pytest.raises(IncomparableProvenanceError):
            record.unmet(required, minimum)
        return

    expected = DR(0)
    for capability in required:
        entry = record.entry(capability)
        if entry is None or entry.tier is None or not entry.present:
            expected |= capability
        elif not entry.tier.satisfies(minimum):
            expected |= capability
    assert record.unmet(required, minimum) == expected


@given(records(), data_tiers)
def test_nothing_is_unmet_for_an_empty_requirement(
    record: CapabilityRecord, minimum: ProvenanceTier
) -> None:
    assert record.unmet(DR(0), minimum) == DR(0)


@given(records(), member_sets, data_tiers)
def test_unmet_is_always_a_subset_of_what_was_required(
    record: CapabilityRecord, members: list[DataRequirement], minimum: ProvenanceTier
) -> None:
    required = _combine(members)
    try:
        unmet = record.unmet(required, minimum)
    except IncomparableProvenanceError:
        return
    assert (unmet & required) == unmet


@given(records())
def test_record_canonical_output_is_stable_and_ascii(record: CapabilityRecord) -> None:
    first = canonical_bytes(record)
    assert first == canonical_bytes(record)
    first.decode("ascii")
    assert first.startswith(b'["capability_record",')
