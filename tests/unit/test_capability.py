"""Example-based tests for data requirements and capability records."""

from __future__ import annotations

import dataclasses
import operator
from enum import STRICT, IntFlag
from typing import Final

import pytest

from ofa.core.capability import CapabilityEntry, CapabilityRecord, DataRequirement
from ofa.core.errors import (
    CapabilityTypeError,
    IncomparableProvenanceError,
    InvalidCapabilityError,
    OfaError,
)
from ofa.core.provenance import ProvenanceTier

DR: Final = DataRequirement
OBSERVED: Final = CapabilityEntry(present=True, tier=ProvenanceTier.OBSERVED)
RECONSTRUCTED: Final = CapabilityEntry(present=True, tier=ProvenanceTier.RECONSTRUCTED)
INFERRED: Final = CapabilityEntry(present=True, tier=ProvenanceTier.INFERRED)
ABSENT: Final = CapabilityEntry(present=False, tier=None)
SIMULATED: Final = CapabilityEntry(present=True, tier=ProvenanceTier.SIMULATED)


# --------------------------------------------------------------------------
# DataRequirement membership and composition
# --------------------------------------------------------------------------


def test_members_are_exactly_those_the_capability_record_names() -> None:
    """data_specification.md section 3 fixes this set."""
    assert [member.name for member in DR] == [
        "TRADES",
        "AGGRESSOR",
        "BBO",
        "MBP_10",
        "MBO",
        "TS_RECV",
        "STATUS",
    ]


def test_every_member_occupies_a_distinct_single_bit() -> None:
    values = [member.value for member in DR]
    assert values == [1, 2, 4, 8, 16, 32, 64]
    assert all(len(tuple(member)) == 1 for member in DR)


def test_no_zero_member_is_declared() -> None:
    """ "Requires nothing" is an absence, not a capability."""
    assert 0 not in {member.value for member in DR}
    assert tuple(DR(0)) == ()


def test_the_boundary_is_strict_not_keep() -> None:
    """IntFlag keeps undeclared bits by default; here they are refused."""
    assert DR._boundary_ is STRICT  # type: ignore[attr-defined]


@pytest.mark.parametrize("raw", [128, 129, 255, 4096])
def test_values_carrying_undeclared_bits_cannot_be_constructed(raw: int) -> None:
    """Under the default KEEP boundary, DR(128) would be a nameless capability
    that canonicalizes exactly like DR(0) — two unequal values, one digest."""
    with pytest.raises(ValueError, match="invalid value"):
        DR(raw)


@pytest.mark.parametrize("raw", list(range(0, 128)))
def test_every_value_within_the_declared_bits_is_constructible(raw: int) -> None:
    assert DR(raw).value == raw


def test_minus_one_resolves_to_every_declared_capability() -> None:
    """Python's all-bits idiom, normalized into the declared set rather than
    kept as an out-of-range value, so it stays unambiguous."""
    every = DR(-1)
    assert every == DR(127)
    assert set(every) == set(DR)


def test_requirements_compose_with_or() -> None:
    combined = DR.TRADES | DR.BBO
    assert set(combined) == {DR.TRADES, DR.BBO}
    assert combined.value == DR.TRADES.value | DR.BBO.value


def test_coverage_is_the_subset_test() -> None:
    available = DR.TRADES | DR.BBO | DR.MBP_10
    required = DR.TRADES | DR.BBO
    assert (required & available) == required
    assert (DR.MBO & available) != DR.MBO


def test_composition_is_order_independent() -> None:
    assert (DR.TRADES | DR.BBO) == (DR.BBO | DR.TRADES)


# --------------------------------------------------------------------------
# CapabilityEntry invariants
# --------------------------------------------------------------------------


def test_present_entry_carries_a_tier() -> None:
    assert OBSERVED.present is True
    assert OBSERVED.tier is ProvenanceTier.OBSERVED


def test_absent_entry_carries_no_tier() -> None:
    assert ABSENT.present is False
    assert ABSENT.tier is None


def test_present_without_a_tier_is_rejected() -> None:
    with pytest.raises(InvalidCapabilityError, match="unknown quality"):
        CapabilityEntry(present=True, tier=None)


def test_absent_with_a_tier_is_rejected() -> None:
    with pytest.raises(InvalidCapabilityError, match="is not there"):
        CapabilityEntry(present=False, tier=ProvenanceTier.OBSERVED)


@pytest.mark.parametrize("value", [0, 1, "yes", None, 1.0, [], ProvenanceTier.OBSERVED])
def test_non_bool_presence_is_rejected(value: object) -> None:
    """0 and 1 included: presence is not a number."""
    with pytest.raises(CapabilityTypeError, match="bool"):
        CapabilityEntry(present=value, tier=ProvenanceTier.OBSERVED)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["OBSERVED", 1, True, 1.5, object(), DR.TRADES])
def test_non_tier_is_rejected(value: object) -> None:
    with pytest.raises(CapabilityTypeError, match="ProvenanceTier"):
        CapabilityEntry(present=True, tier=value)  # type: ignore[arg-type]


def test_a_simulated_entry_may_be_constructed() -> None:
    """Representable as provenance; it simply can never satisfy a requirement."""
    assert SIMULATED.tier is ProvenanceTier.SIMULATED


def test_entries_are_frozen_and_slotted() -> None:
    parameters = CapabilityEntry.__dataclass_params__  # type: ignore[attr-defined]
    assert parameters.frozen is True
    assert parameters.order is False
    assert not hasattr(OBSERVED, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        OBSERVED.present = False  # type: ignore[misc]


def test_entries_compare_by_value() -> None:
    assert CapabilityEntry(present=True, tier=ProvenanceTier.OBSERVED) == OBSERVED
    assert OBSERVED != INFERRED
    assert OBSERVED != ABSENT


# --------------------------------------------------------------------------
# CapabilityRecord construction and invariants
# --------------------------------------------------------------------------


def test_record_orders_its_entries_canonically() -> None:
    forward = CapabilityRecord(((DR.TRADES, OBSERVED), (DR.MBO, ABSENT)))
    backward = CapabilityRecord(((DR.MBO, ABSENT), (DR.TRADES, OBSERVED)))
    assert forward == backward
    assert forward.entries == backward.entries
    assert [capability.name for capability, _ in forward.entries] == ["TRADES", "MBO"]


def test_record_preserves_entry_content_exactly() -> None:
    """Only the order is normalized, never what the record says."""
    record = CapabilityRecord(((DR.AGGRESSOR, INFERRED), (DR.TRADES, OBSERVED)))
    assert dict(record.entries) == {DR.TRADES: OBSERVED, DR.AGGRESSOR: INFERRED}


def test_empty_record_is_valid() -> None:
    record = CapabilityRecord(())
    assert record.entries == ()
    assert record.present == DR(0)


def test_composite_key_is_rejected() -> None:
    with pytest.raises(InvalidCapabilityError, match="exactly one capability"):
        CapabilityRecord(((DR.TRADES | DR.BBO, OBSERVED),))


def test_empty_key_is_rejected() -> None:
    with pytest.raises(InvalidCapabilityError, match="exactly one capability"):
        CapabilityRecord(((DR(0), OBSERVED),))


def test_duplicate_capability_is_rejected() -> None:
    with pytest.raises(InvalidCapabilityError, match="more than once"):
        CapabilityRecord(((DR.TRADES, OBSERVED), (DR.TRADES, ABSENT)))


@pytest.mark.parametrize(
    "entries",
    [
        [(DR.TRADES, OBSERVED)],
        {DR.TRADES: OBSERVED},
        ((DR.TRADES, OBSERVED, "extra"),),
        ((DR.TRADES,),),
        (("TRADES", OBSERVED),),
        ((DR.TRADES, ProvenanceTier.OBSERVED),),
        ((DR.TRADES, True),),
    ],
)
def test_malformed_entries_are_rejected(entries: object) -> None:
    with pytest.raises(CapabilityTypeError):
        CapabilityRecord(entries)  # type: ignore[arg-type]


def test_records_are_frozen_slotted_and_hashable() -> None:
    record = CapabilityRecord(((DR.TRADES, OBSERVED),))
    parameters = CapabilityRecord.__dataclass_params__  # type: ignore[attr-defined]
    assert parameters.frozen is True
    assert not hasattr(record, "__dict__")
    assert hash(record) == hash(CapabilityRecord(((DR.TRADES, OBSERVED),)))
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.entries = ()  # type: ignore[misc]


def test_records_are_not_orderable() -> None:
    left = CapabilityRecord(((DR.TRADES, OBSERVED),))
    right = CapabilityRecord(((DR.BBO, OBSERVED),))
    for operation in (operator.lt, operator.le, operator.gt, operator.ge):
        with pytest.raises(TypeError):
            operation(left, right)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Lookup and presence
# --------------------------------------------------------------------------


def test_entry_returns_the_recorded_entry() -> None:
    record = CapabilityRecord(((DR.TRADES, OBSERVED), (DR.MBO, ABSENT)))
    assert record.entry(DR.TRADES) is OBSERVED
    assert record.entry(DR.MBO) is ABSENT


def test_entry_returns_none_for_a_capability_the_record_omits() -> None:
    """Omitted means nobody looked; recorded absent is a measured negative."""
    record = CapabilityRecord(((DR.TRADES, OBSERVED),))
    assert record.entry(DR.MBO) is None
    assert record.entry(DR.BBO) is None


def test_entry_rejects_a_composite_lookup() -> None:
    record = CapabilityRecord(((DR.TRADES, OBSERVED),))
    with pytest.raises(InvalidCapabilityError):
        record.entry(DR.TRADES | DR.BBO)


def test_present_reports_only_capabilities_recorded_present() -> None:
    record = CapabilityRecord(((DR.TRADES, OBSERVED), (DR.AGGRESSOR, INFERRED), (DR.MBO, ABSENT)))
    assert record.present == (DR.TRADES | DR.AGGRESSOR)
    assert DR.MBO not in record.present


# --------------------------------------------------------------------------
# unmet: the enforcement query
# --------------------------------------------------------------------------


FULL: Final = CapabilityRecord(
    (
        (DR.TRADES, OBSERVED),
        (DR.AGGRESSOR, INFERRED),
        (DR.BBO, RECONSTRUCTED),
        (DR.MBO, ABSENT),
    )
)


def test_a_satisfied_requirement_yields_nothing_unmet() -> None:
    assert FULL.unmet(DR.TRADES, ProvenanceTier.OBSERVED) == DR(0)
    assert FULL.unmet(DR.TRADES | DR.BBO, ProvenanceTier.INFERRED) == DR(0)


def test_an_empty_requirement_is_always_satisfied() -> None:
    assert CapabilityRecord(()).unmet(DR(0), ProvenanceTier.OBSERVED) == DR(0)


def test_a_capability_recorded_absent_is_unmet() -> None:
    assert FULL.unmet(DR.MBO, ProvenanceTier.INFERRED) == DR.MBO


def test_a_capability_missing_from_the_record_is_unmet() -> None:
    assert FULL.unmet(DR.STATUS, ProvenanceTier.INFERRED) == DR.STATUS


def test_a_capability_at_too_weak_a_tier_is_unmet() -> None:
    """The [ENFORCED] rule: a weaker tier fails rather than degrading silently."""
    assert FULL.unmet(DR.AGGRESSOR, ProvenanceTier.OBSERVED) == DR.AGGRESSOR
    assert FULL.unmet(DR.BBO, ProvenanceTier.OBSERVED) == DR.BBO
    assert FULL.unmet(DR.BBO, ProvenanceTier.RECONSTRUCTED) == DR(0)


def test_unmet_reports_every_failing_capability_not_just_the_first() -> None:
    unmet = FULL.unmet(DR.TRADES | DR.AGGRESSOR | DR.MBO | DR.STATUS, ProvenanceTier.OBSERVED)
    assert unmet == (DR.AGGRESSOR | DR.MBO | DR.STATUS)
    assert DR.TRADES not in unmet


def test_a_simulated_capability_raises_rather_than_counting_as_unmet() -> None:
    """Simulated input is a category error, not a thin feed."""
    record = CapabilityRecord(((DR.TRADES, SIMULATED),))
    with pytest.raises(IncomparableProvenanceError):
        record.unmet(DR.TRADES, ProvenanceTier.OBSERVED)


def test_a_simulated_capability_outside_the_requirement_is_not_consulted() -> None:
    record = CapabilityRecord(((DR.TRADES, OBSERVED), (DR.MBO, SIMULATED)))
    assert record.unmet(DR.TRADES, ProvenanceTier.OBSERVED) == DR(0)


@pytest.mark.parametrize("value", ["TRADES", 1, True, None, ProvenanceTier.OBSERVED])
def test_unmet_rejects_a_non_requirement(value: object) -> None:
    with pytest.raises(CapabilityTypeError, match="DataRequirement"):
        FULL.unmet(value, ProvenanceTier.OBSERVED)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["OBSERVED", 1, True, None, DR.TRADES])
def test_unmet_rejects_a_non_tier(value: object) -> None:
    with pytest.raises(CapabilityTypeError, match="ProvenanceTier"):
        FULL.unmet(DR.TRADES, value)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Type identity and the error family
# --------------------------------------------------------------------------


class _Other(IntFlag):
    TRADES = 1


def test_another_flag_type_is_not_a_data_requirement() -> None:
    with pytest.raises(CapabilityTypeError):
        CapabilityRecord(((_Other.TRADES, OBSERVED),))  # type: ignore[arg-type]


def test_capability_errors_belong_to_both_families() -> None:
    assert issubclass(CapabilityTypeError, OfaError)
    assert issubclass(CapabilityTypeError, TypeError)
    assert issubclass(InvalidCapabilityError, OfaError)
    assert issubclass(InvalidCapabilityError, ValueError)


def test_quality_statistics_are_deliberately_absent() -> None:
    """unknown_share and friends need decisions this milestone does not make."""
    fields = {field.name for field in dataclasses.fields(CapabilityEntry)}
    assert fields == {"present", "tier"}
    for absent in ("unknown_share", "truncation_events", "assumed_feed_delay_ns"):
        assert absent not in fields
