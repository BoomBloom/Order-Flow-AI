"""Property tests for the provenance-tier partial order.

The oracle is an independent strength ranking written out here, so the tests
do not merely restate the implementation's own table.
"""

from __future__ import annotations

from typing import Final

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ofa.core.errors import IncomparableProvenanceError
from ofa.core.hashing import canonical_bytes, content_hash
from ofa.core.provenance import ProvenanceTier

#: Independent oracle: strongest to weakest, written from the specification's
#: prose rather than read from the module under test.
RANKED: Final[list[ProvenanceTier]] = [
    ProvenanceTier.OBSERVED,
    ProvenanceTier.RECONSTRUCTED,
    ProvenanceTier.INFERRED,
]

data_tiers = st.sampled_from(RANKED)
all_tiers = st.sampled_from(list(ProvenanceTier))


@given(data_tiers, data_tiers)
def test_satisfies_agrees_with_the_independent_ranking(
    supplied: ProvenanceTier, required: ProvenanceTier
) -> None:
    expected = RANKED.index(supplied) <= RANKED.index(required)
    assert supplied.satisfies(required) is expected


@given(data_tiers)
def test_satisfies_is_reflexive(tier: ProvenanceTier) -> None:
    assert tier.satisfies(tier)


@given(data_tiers, data_tiers)
def test_satisfies_is_antisymmetric(left: ProvenanceTier, right: ProvenanceTier) -> None:
    if left.satisfies(right) and right.satisfies(left):
        assert left is right


@given(data_tiers, data_tiers, data_tiers)
def test_satisfies_is_transitive(
    first: ProvenanceTier, second: ProvenanceTier, third: ProvenanceTier
) -> None:
    if first.satisfies(second) and second.satisfies(third):
        assert first.satisfies(third)


@given(data_tiers, data_tiers)
def test_exactly_one_direction_holds_for_distinct_tiers(
    left: ProvenanceTier, right: ProvenanceTier
) -> None:
    if left is not right:
        assert left.satisfies(right) != right.satisfies(left)


@given(all_tiers)
def test_simulated_is_incomparable_in_both_directions(other: ProvenanceTier) -> None:
    with pytest.raises(IncomparableProvenanceError):
        ProvenanceTier.SIMULATED.satisfies(other)
    with pytest.raises(IncomparableProvenanceError):
        other.satisfies(ProvenanceTier.SIMULATED)


@given(all_tiers)
def test_canonical_form_is_the_member_name(tier: ProvenanceTier) -> None:
    produced = canonical_bytes(tier)
    assert produced.endswith(f'"{tier.name}"]'.encode("ascii"))
    assert produced.startswith(b'["enum",')
    assert produced == canonical_bytes(tier)


@given(all_tiers, all_tiers)
def test_distinct_tiers_never_share_a_digest(left: ProvenanceTier, right: ProvenanceTier) -> None:
    if left is not right:
        assert content_hash(left) != content_hash(right)
