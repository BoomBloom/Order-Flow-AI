"""Property tests for the identifier value types.

No float appears in any strategy: identifiers carry an exact integer or an
opaque token, and neither has a float path to exercise.
"""

from __future__ import annotations

import operator
import unicodedata
from typing import Final

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ofa.core.errors import IdentifierTypeError, InvalidIdentifierError
from ofa.core.hashing import canonical_bytes, content_hash
from ofa.core.ids import INT32_MAX, INT32_MIN, InstrumentId, ProvenanceId, RunId

int32s = st.integers(min_value=INT32_MIN, max_value=INT32_MAX)

outside_int32 = st.one_of(
    st.integers(max_value=INT32_MIN - 1),
    st.integers(min_value=INT32_MAX + 1),
)

#: Characters a run id may hold: no separators, no whitespace, no control or
#: surrogate code points. The alphabet is not fixed by the type, so this is
#: deliberately broad rather than a mirror of an implementation regex.
_run_id_characters = st.characters(
    exclude_categories=("Cc", "Cf", "Cs", "Co", "Cn", "Zs", "Zl", "Zp"),
    exclude_characters="/\\",
)

run_ids: Final[st.SearchStrategy[str]] = (
    st.text(alphabet=_run_id_characters, min_size=1, max_size=24)
    .filter(lambda text: not any(character.isspace() for character in text))
    .filter(lambda text: text not in (".", ".."))
)

INDEX_TYPES: Final = [InstrumentId, ProvenanceId]
IndexType = type[InstrumentId] | type[ProvenanceId]


# --------------------------------------------------------------------------
# Value preservation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("identifier", INDEX_TYPES)
@given(int32s)
def test_int32_value_is_preserved_exactly(identifier: IndexType, value: int) -> None:
    assert identifier(value).value == value
    assert type(identifier(value).value) is int


@given(run_ids)
def test_run_id_value_is_preserved_exactly(value: str) -> None:
    """Preserved, not normalized: the stored value is the value supplied."""
    assert RunId(value).value == value
    assert RunId(value).value is value


@given(run_ids)
def test_run_id_is_not_unicode_normalized(value: str) -> None:
    decomposed = unicodedata.normalize("NFD", value)
    composed = unicodedata.normalize("NFC", value)
    if decomposed != composed:
        try:
            left, right = RunId(decomposed), RunId(composed)
        except InvalidIdentifierError:
            return
        assert left != right
        assert canonical_bytes(left) != canonical_bytes(right)


# --------------------------------------------------------------------------
# Boundary rejection
# --------------------------------------------------------------------------


@pytest.mark.parametrize("identifier", INDEX_TYPES)
@given(outside_int32)
def test_values_outside_int32_are_always_rejected(identifier: IndexType, value: int) -> None:
    with pytest.raises(InvalidIdentifierError):
        identifier(value)


@pytest.mark.parametrize("identifier", INDEX_TYPES)
@given(st.text(max_size=8))
def test_strings_are_never_accepted_as_an_index(identifier: IndexType, value: str) -> None:
    with pytest.raises(IdentifierTypeError):
        identifier(value)  # type: ignore[arg-type]


@given(st.integers())
def test_integers_are_never_accepted_as_a_run_id(value: int) -> None:
    with pytest.raises(IdentifierTypeError):
        RunId(value)  # type: ignore[arg-type]


@given(
    st.text(alphabet=_run_id_characters, max_size=8),
    st.text(alphabet=_run_id_characters, max_size=8),
)
def test_any_value_containing_a_separator_is_rejected(left: str, right: str) -> None:
    for separator in ("/", "\\"):
        with pytest.raises(InvalidIdentifierError):
            RunId(f"{left}{separator}{right}")


# --------------------------------------------------------------------------
# Equality, hashing and canonical agreement
# --------------------------------------------------------------------------


@pytest.mark.parametrize("identifier", INDEX_TYPES)
@given(int32s)
def test_equal_indices_agree_on_equality_hash_and_canonical_bytes(
    identifier: IndexType, value: int
) -> None:
    left, right = identifier(value), identifier(value)
    assert left == right
    assert hash(left) == hash(right)
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_hash(left) == content_hash(right)


@given(run_ids)
def test_equal_run_ids_agree_on_equality_hash_and_canonical_bytes(value: str) -> None:
    left, right = RunId(value), RunId(str(value))
    assert left == right
    assert hash(left) == hash(right)
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_hash(left) == content_hash(right)


@given(int32s)
def test_identifier_kinds_sharing_a_number_never_share_a_canonical_form(
    value: int,
) -> None:
    forms = {
        canonical_bytes(InstrumentId(value)),
        canonical_bytes(ProvenanceId(value)),
        canonical_bytes(value),
    }
    assert len(forms) == 3
    digests = {
        content_hash(InstrumentId(value)),
        content_hash(ProvenanceId(value)),
        content_hash(value),
    }
    assert len(digests) == 3


@given(run_ids)
def test_a_run_id_never_shares_a_canonical_form_with_its_string(value: str) -> None:
    assert canonical_bytes(RunId(value)) != canonical_bytes(value)
    assert content_hash(RunId(value)) != content_hash(value)


@given(int32s)
def test_indices_of_different_kinds_never_compare_equal(value: int) -> None:
    """mypy rejects each comparison as non-overlapping; runtime agrees."""
    assert InstrumentId(value) != ProvenanceId(value)  # type: ignore[comparison-overlap]
    assert InstrumentId(value) != value  # type: ignore[comparison-overlap]
    assert ProvenanceId(value) != value  # type: ignore[comparison-overlap]


@given(int32s, int32s)
def test_indices_compare_equal_exactly_when_their_values_do(left: int, right: int) -> None:
    assert (InstrumentId(left) == InstrumentId(right)) == (left == right)


# --------------------------------------------------------------------------
# Canonical output stability and absence of ordering
# --------------------------------------------------------------------------


@given(run_ids)
def test_run_id_canonical_output_is_stable_and_ascii(value: str) -> None:
    first = canonical_bytes(RunId(value))
    assert first == canonical_bytes(RunId(value))
    first.decode("ascii")
    assert first.startswith(b'["run_id",')


@pytest.mark.parametrize("identifier", INDEX_TYPES)
@given(int32s)
def test_index_canonical_output_is_stable_and_ascii(identifier: IndexType, value: int) -> None:
    first = canonical_bytes(identifier(value))
    assert first == canonical_bytes(identifier(value))
    first.decode("ascii")


@given(int32s, int32s)
def test_indices_are_never_orderable(left: int, right: int) -> None:
    for operation in (operator.lt, operator.le, operator.gt, operator.ge):
        with pytest.raises(TypeError):
            operation(InstrumentId(left), InstrumentId(right))  # type: ignore[arg-type]


@given(run_ids, run_ids)
def test_run_ids_are_never_orderable(left: str, right: str) -> None:
    for operation in (operator.lt, operator.le, operator.gt, operator.ge):
        with pytest.raises(TypeError):
            operation(RunId(left), RunId(right))  # type: ignore[arg-type]
