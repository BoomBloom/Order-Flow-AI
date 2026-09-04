"""Example-based tests for provenance tiers and their partial order."""

from __future__ import annotations

import operator
from enum import Enum
from typing import Final

import pytest

from ofa.core.errors import IncomparableProvenanceError, OfaError, ProvenanceTypeError
from ofa.core.provenance import ProvenanceTier

DATA_TIERS: Final = [
    ProvenanceTier.OBSERVED,
    ProvenanceTier.RECONSTRUCTED,
    ProvenanceTier.INFERRED,
]

#: Strongest first. The order the specification states in prose.
STRENGTH_ORDER: Final = DATA_TIERS


def test_the_four_tiers_are_exactly_those_the_specification_names() -> None:
    assert [tier.name for tier in ProvenanceTier] == [
        "OBSERVED",
        "RECONSTRUCTED",
        "INFERRED",
        "SIMULATED",
    ]


def test_each_value_is_its_own_name() -> None:
    """So the member and the string a manifest records cannot drift apart."""
    for tier in ProvenanceTier:
        assert tier.value == tier.name


# --------------------------------------------------------------------------
# The order over the three data tiers
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tier", DATA_TIERS)
def test_every_data_tier_satisfies_itself(tier: ProvenanceTier) -> None:
    assert tier.satisfies(tier)


def test_stronger_tiers_satisfy_weaker_requirements() -> None:
    assert ProvenanceTier.OBSERVED.satisfies(ProvenanceTier.RECONSTRUCTED)
    assert ProvenanceTier.OBSERVED.satisfies(ProvenanceTier.INFERRED)
    assert ProvenanceTier.RECONSTRUCTED.satisfies(ProvenanceTier.INFERRED)


def test_weaker_tiers_do_not_satisfy_stronger_requirements() -> None:
    assert not ProvenanceTier.INFERRED.satisfies(ProvenanceTier.RECONSTRUCTED)
    assert not ProvenanceTier.INFERRED.satisfies(ProvenanceTier.OBSERVED)
    assert not ProvenanceTier.RECONSTRUCTED.satisfies(ProvenanceTier.OBSERVED)


def test_the_order_is_transitive_and_antisymmetric() -> None:
    strongest, middle, weakest = STRENGTH_ORDER
    assert strongest.satisfies(middle) and middle.satisfies(weakest)
    assert strongest.satisfies(weakest)
    assert not weakest.satisfies(strongest)


def test_inferred_is_not_a_lossy_reconstructed() -> None:
    """The specification forbids merging the two; they never compare equal.

    mypy rejects both comparisons as non-overlapping, which is the static half
    of the same guarantee.
    """
    assert ProvenanceTier.INFERRED is not ProvenanceTier.RECONSTRUCTED  # type: ignore[comparison-overlap]
    assert ProvenanceTier.INFERRED != ProvenanceTier.RECONSTRUCTED  # type: ignore[comparison-overlap]
    assert not ProvenanceTier.INFERRED.satisfies(ProvenanceTier.RECONSTRUCTED)


# --------------------------------------------------------------------------
# SIMULATED is incomparable, and says so loudly
# --------------------------------------------------------------------------


@pytest.mark.parametrize("other", DATA_TIERS)
def test_simulated_cannot_satisfy_a_data_requirement(other: ProvenanceTier) -> None:
    with pytest.raises(IncomparableProvenanceError, match="outside the data-tier order"):
        ProvenanceTier.SIMULATED.satisfies(other)


@pytest.mark.parametrize("other", DATA_TIERS)
def test_simulated_cannot_be_required(other: ProvenanceTier) -> None:
    with pytest.raises(IncomparableProvenanceError):
        other.satisfies(ProvenanceTier.SIMULATED)


def test_simulated_compared_with_itself_still_raises() -> None:
    """Not even reflexively: the question is malformed, not close."""
    with pytest.raises(IncomparableProvenanceError):
        ProvenanceTier.SIMULATED.satisfies(ProvenanceTier.SIMULATED)


def test_simulated_failure_is_never_silently_false() -> None:
    """The distinction that matters: a category error, not a thin feed."""
    with pytest.raises(IncomparableProvenanceError) as caught:
        ProvenanceTier.SIMULATED.satisfies(ProvenanceTier.OBSERVED)
    assert isinstance(caught.value, ValueError)
    assert isinstance(caught.value, OfaError)


def test_simulated_remains_a_recordable_tier() -> None:
    """It may be stored as provenance; it may only never satisfy a requirement."""
    assert ProvenanceTier.SIMULATED in set(ProvenanceTier)
    assert ProvenanceTier("SIMULATED") is ProvenanceTier.SIMULATED


# --------------------------------------------------------------------------
# No total order is advertised
# --------------------------------------------------------------------------


@pytest.mark.parametrize("operation", [operator.lt, operator.le, operator.gt, operator.ge])
def test_tiers_are_not_orderable_by_operator(operation: object) -> None:
    """`<` would advertise a total order over four members that have none."""
    with pytest.raises(TypeError):
        operation(ProvenanceTier.OBSERVED, ProvenanceTier.INFERRED)  # type: ignore[operator]


@pytest.mark.parametrize("member", ["__lt__", "__le__", "__gt__", "__ge__"])
def test_ordering_operators_are_not_defined(member: str) -> None:
    assert member not in vars(ProvenanceTier)


def test_tiers_cannot_be_sorted_directly() -> None:
    with pytest.raises(TypeError):
        sorted(DATA_TIERS)  # type: ignore[type-var]


def test_tier_is_not_an_int() -> None:
    """IntEnum would give SIMULATED an accidental position in the order."""
    assert not isinstance(ProvenanceTier.OBSERVED, int)
    assert ProvenanceTier.OBSERVED != 3  # type: ignore[comparison-overlap]


def test_internal_rank_excludes_simulated() -> None:
    from ofa.core.provenance import _DATA_TIER_RANK

    assert set(_DATA_TIER_RANK) == set(DATA_TIERS)
    assert ProvenanceTier.SIMULATED not in _DATA_TIER_RANK


# --------------------------------------------------------------------------
# Type rejection
# --------------------------------------------------------------------------


class _Other(Enum):
    OBSERVED = "OBSERVED"


@pytest.mark.parametrize(
    "value", ["OBSERVED", 1, 0, None, True, 1.5, b"OBSERVED", _Other.OBSERVED, object()]
)
def test_non_tier_minimum_is_rejected(value: object) -> None:
    with pytest.raises(ProvenanceTypeError):
        ProvenanceTier.OBSERVED.satisfies(value)  # type: ignore[arg-type]


def test_a_tier_name_is_not_a_tier() -> None:
    """Comparing against the string would succeed or fail by direction."""
    with pytest.raises(ProvenanceTypeError):
        ProvenanceTier.OBSERVED.satisfies("OBSERVED")  # type: ignore[arg-type]


def test_provenance_errors_belong_to_both_families() -> None:
    assert issubclass(ProvenanceTypeError, OfaError)
    assert issubclass(ProvenanceTypeError, TypeError)
    assert issubclass(IncomparableProvenanceError, OfaError)
    assert issubclass(IncomparableProvenanceError, ValueError)
