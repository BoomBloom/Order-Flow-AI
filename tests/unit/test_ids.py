"""Example-based tests for the identifier value types.

These test the types themselves. Their canonical representations are tested
alongside the rest of the canonical contract, in ``tests/unit/test_hashing.py``.
"""

from __future__ import annotations

import ast
import dataclasses
import operator
import re
from dataclasses import FrozenInstanceError
from decimal import Decimal
from enum import Enum, IntEnum, StrEnum
from typing import Final

import pytest

from ofa.core import ids
from ofa.core.errors import IdentifierTypeError, InvalidIdentifierError, OfaError
from ofa.core.ids import INT32_MAX, INT32_MIN, InstrumentId, ProvenanceId, RunId
from ofa.core.money import Price
from ofa.core.time import UtcNanos

IDENTIFIER_INDEX_TYPES: Final = [InstrumentId, ProvenanceId]


class _Symbol(StrEnum):
    NQ = "nq"


class _Index(IntEnum):
    FIRST = 1


class _MyStr(str):
    pass


class _MyInt(int):
    pass


# --------------------------------------------------------------------------
# RunId — accepted values
# --------------------------------------------------------------------------

VALID_RUN_IDS: Final[list[str]] = [
    "a",
    "r1",
    "run-2024-03-11-001",
    "Run_A",
    "RUN",
    "0",
    "run.1",
    "...",
    "a-b_c.d",
    "-leading-hyphen",
    "trailing-hyphen-",
    "café",  # the alphabet is not fixed here; only safety is enforced
    "実行",
    "a" * 512,  # no maximum length is fixed here either
]


@pytest.mark.parametrize("value", VALID_RUN_IDS)
def test_valid_run_ids_are_accepted_and_preserved(value: str) -> None:
    assert RunId(value).value == value


def test_run_id_preserves_case_rather_than_folding_it() -> None:
    assert RunId("Run-A").value == "Run-A"
    assert RunId("Run-A") != RunId("run-a")


def test_run_id_preserves_the_value_exactly() -> None:
    """No trimming, no stripping, no substitution — the value is stored as given."""
    for value in ("a--b", "a__b", "a..b", "0000"):
        assert RunId(value).value == value


# --------------------------------------------------------------------------
# RunId — rejected values
# --------------------------------------------------------------------------


def test_empty_run_id_is_rejected() -> None:
    with pytest.raises(InvalidIdentifierError, match="empty"):
        RunId("")


@pytest.mark.parametrize("value", [".", ".."])
def test_relative_path_names_are_rejected(value: str) -> None:
    with pytest.raises(InvalidIdentifierError, match="relative path"):
        RunId(value)


@pytest.mark.parametrize(
    "value",
    [
        "a/b",
        "/a",
        "a/",
        "/",
        "a//b",
        "../a",
        "a/..",
        "a\\b",
        "\\a",
        "a\\",
        "\\",
        "a\\..\\b",
    ],
)
def test_path_separators_are_rejected(value: str) -> None:
    """Both separators, on every platform: a name written on one host is read on another."""
    with pytest.raises(InvalidIdentifierError, match="single path component"):
        RunId(value)


@pytest.mark.parametrize(
    "value",
    [
        "a b",
        " a",
        "a ",
        " ",
        "a\tb",
        "a\nb",
        "a\rb",
        "a\x0bb",
        "a\x0cb",
        "a\x1cb",  # file separator: whitespace to Python, despite being C0
        "a\x1fb",  # unit separator: likewise
        "a\xa0b",  # no-break space
        "a\u2003b",  # em space
        "a\u3000b",  # ideographic space
    ],
)
def test_whitespace_is_rejected(value: str) -> None:
    with pytest.raises(InvalidIdentifierError, match="whitespace"):
        RunId(value)


@pytest.mark.parametrize(
    "value",
    ["a\x00b", "\x00", "a\x01b", "a\x08b", "a\x1bb", "a\x7fb", "\x7f"],
)
def test_control_characters_are_rejected(value: str) -> None:
    with pytest.raises(InvalidIdentifierError, match="control character"):
        RunId(value)


def test_lone_surrogate_run_id_is_rejected() -> None:
    with pytest.raises(InvalidIdentifierError, match="UTF-8"):
        RunId("a\ud800b")


@pytest.mark.parametrize(
    "value",
    [1, 0, None, b"abc", 1.5, True, False, ["a"], ("a",), {"a": 1}, Price(1), UtcNanos(1)],
)
def test_non_string_run_id_is_rejected(value: object) -> None:
    with pytest.raises(IdentifierTypeError):
        RunId(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [_MyStr("abc"), _Symbol.NQ])
def test_string_subclass_run_id_is_rejected(value: str) -> None:
    with pytest.raises(IdentifierTypeError, match="subclass"):
        RunId(value)


# --------------------------------------------------------------------------
# InstrumentId and ProvenanceId — accepted values
# --------------------------------------------------------------------------


@pytest.mark.parametrize("identifier", IDENTIFIER_INDEX_TYPES)
@pytest.mark.parametrize("value", [0, 1, 7, -1, -7, 1234, INT32_MIN, INT32_MAX])
def test_index_identifiers_accept_the_signed_int32_range(
    identifier: type[InstrumentId] | type[ProvenanceId], value: int
) -> None:
    assert identifier(value).value == value


def test_int32_bounds_are_the_signed_thirty_two_bit_range() -> None:
    assert INT32_MIN == -(2**31)
    assert INT32_MAX == 2**31 - 1


# --------------------------------------------------------------------------
# InstrumentId and ProvenanceId — rejected values
# --------------------------------------------------------------------------


@pytest.mark.parametrize("identifier", IDENTIFIER_INDEX_TYPES)
@pytest.mark.parametrize("value", [INT32_MIN - 1, INT32_MAX + 1, 2**63, -(2**63), 2**31])
def test_values_outside_int32_are_rejected(
    identifier: type[InstrumentId] | type[ProvenanceId], value: int
) -> None:
    with pytest.raises(InvalidIdentifierError, match="32-bit"):
        identifier(value)


@pytest.mark.parametrize("identifier", IDENTIFIER_INDEX_TYPES)
@pytest.mark.parametrize("value", [True, False])
def test_bool_is_rejected_as_an_index(
    identifier: type[InstrumentId] | type[ProvenanceId], value: bool
) -> None:
    """bool is an int subclass; True would otherwise mean index 1."""
    with pytest.raises(IdentifierTypeError, match="bool"):
        identifier(value)


@pytest.mark.parametrize("identifier", IDENTIFIER_INDEX_TYPES)
@pytest.mark.parametrize(
    "value",
    [1.0, 0.0, 1.5, float("nan"), "1", "", None, b"1", Decimal("1"), [1], (1,), Price(1)],
)
def test_non_integer_values_are_rejected_as_an_index(
    identifier: type[InstrumentId] | type[ProvenanceId], value: object
) -> None:
    with pytest.raises(IdentifierTypeError):
        identifier(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("identifier", IDENTIFIER_INDEX_TYPES)
@pytest.mark.parametrize("value", [_MyInt(1), _Index.FIRST])
def test_integer_subclasses_are_rejected_as_an_index(
    identifier: type[InstrumentId] | type[ProvenanceId], value: int
) -> None:
    with pytest.raises(IdentifierTypeError, match="subclass"):
        identifier(value)


# --------------------------------------------------------------------------
# Equality, hashing, and the semantic distinction between the two indices
# --------------------------------------------------------------------------


def test_identifiers_compare_equal_by_value() -> None:
    assert RunId("r1") == RunId("r1")
    assert RunId("r1") != RunId("r2")
    assert InstrumentId(7) == InstrumentId(7)
    assert InstrumentId(7) != InstrumentId(8)
    assert ProvenanceId(3) == ProvenanceId(3)


def test_instrument_and_provenance_indices_never_compare_equal() -> None:
    """Two types over one int32 exist precisely so these do not conflate.

    mypy rejects each of these comparisons as non-overlapping, which is the
    static half of the same guarantee; the assertions prove it holds at
    runtime too.
    """
    assert InstrumentId(3) != ProvenanceId(3)  # type: ignore[comparison-overlap]
    assert ProvenanceId(3) != InstrumentId(3)  # type: ignore[comparison-overlap]


def test_identifiers_never_compare_equal_to_their_payload() -> None:
    assert RunId("3") != "3"  # type: ignore[comparison-overlap]
    assert InstrumentId(3) != 3  # type: ignore[comparison-overlap]
    assert ProvenanceId(3) != 3  # type: ignore[comparison-overlap]
    assert RunId("3") != InstrumentId(3)  # type: ignore[comparison-overlap]


def test_identifiers_are_hashable_and_usable_as_dict_keys() -> None:
    mapping = {RunId("r1"): 1, InstrumentId(7): 2, ProvenanceId(7): 3}
    assert mapping[RunId("r1")] == 1
    assert mapping[InstrumentId(7)] == 2
    assert mapping[ProvenanceId(7)] == 3
    assert len({InstrumentId(7), ProvenanceId(7)}) == 2
    assert len({RunId("r1"), RunId("r1")}) == 1


def test_equal_identifiers_hash_equally() -> None:
    assert hash(RunId("r1")) == hash(RunId("r1"))
    assert hash(InstrumentId(7)) == hash(InstrumentId(7))


# --------------------------------------------------------------------------
# Immutability
# --------------------------------------------------------------------------


@pytest.mark.parametrize("identifier", [RunId("r1"), InstrumentId(7), ProvenanceId(3)])
def test_identifiers_are_immutable(identifier: object) -> None:
    with pytest.raises(FrozenInstanceError):
        identifier.value = "other"  # type: ignore[attr-defined]


@pytest.mark.parametrize("identifier", [RunId("r1"), InstrumentId(7), ProvenanceId(3)])
def test_identifiers_are_slotted_and_reject_new_attributes(identifier: object) -> None:
    # TypeError, not AttributeError: @dataclass(frozen=True, slots=True)
    # rebuilds the class, so the frozen __setattr__ closure captures the
    # original one and its super() call fails first. Either way the attribute
    # cannot be added, which is what matters here.
    with pytest.raises((AttributeError, TypeError)):
        identifier.extra = 1  # type: ignore[attr-defined]
    assert not hasattr(identifier, "__dict__")


@pytest.mark.parametrize("identifier", [RunId, InstrumentId, ProvenanceId])
def test_identifiers_are_frozen_slotted_dataclasses(identifier: type) -> None:
    assert dataclasses.is_dataclass(identifier)
    parameters = identifier.__dataclass_params__  # type: ignore[attr-defined]
    assert parameters.frozen is True
    assert parameters.eq is True
    assert parameters.order is False


# --------------------------------------------------------------------------
# Absence: no ordering
# --------------------------------------------------------------------------


ORDER_PAIRS: Final[list[tuple[object, object]]] = [
    (RunId("a"), RunId("b")),
    (InstrumentId(1), InstrumentId(2)),
    (ProvenanceId(1), ProvenanceId(2)),
]


@pytest.mark.parametrize(("left", "right"), ORDER_PAIRS)
def test_identifiers_have_no_ordering(left: object, right: object) -> None:
    """A label is not a magnitude. Sorting is done by an explicit key instead."""
    # The operators, not the dunders: object.__lt__ returns NotImplemented, and
    # it is the operator protocol that turns that into a TypeError.
    for operation in (operator.lt, operator.le, operator.gt, operator.ge):
        with pytest.raises(TypeError):
            operation(left, right)  # type: ignore[arg-type]


@pytest.mark.parametrize(("left", "right"), ORDER_PAIRS)
def test_identifiers_cannot_be_sorted_directly(left: object, right: object) -> None:
    with pytest.raises(TypeError):
        sorted([right, left])  # type: ignore[type-var]


@pytest.mark.parametrize("identifier", [RunId, InstrumentId, ProvenanceId])
@pytest.mark.parametrize("operation", ["__lt__", "__le__", "__gt__", "__ge__"])
def test_ordering_operators_are_not_defined_on_the_class(identifier: type, operation: str) -> None:
    assert operation not in vars(identifier)


# --------------------------------------------------------------------------
# Absence: no arithmetic, conversion, generation, registry or filesystem API
# --------------------------------------------------------------------------


PROHIBITED_MEMBERS: Final[list[str]] = [
    "new",
    "mint",
    "generate",
    "create",
    "next",
    "now",
    "random",
    "uuid",
    "uuid4",
    "from_uuid",
    "from_str",
    "from_string",
    "from_int",
    "parse",
    "to_path",
    "path",
    "as_path",
    "resolve",
    "lookup",
    "registry",
    "manifest",
    "to_json",
    "from_json",
    "__add__",
    "__sub__",
    "__mul__",
    "__int__",
    "__index__",
    "__str__",
    "__fspath__",
]


@pytest.mark.parametrize("identifier", [RunId, InstrumentId, ProvenanceId])
@pytest.mark.parametrize("member", PROHIBITED_MEMBERS)
def test_prohibited_members_are_absent(identifier: type, member: str) -> None:
    assert member not in vars(identifier)


@pytest.mark.parametrize("identifier", [RunId, InstrumentId, ProvenanceId])
def test_public_api_is_only_the_value_field(identifier: type) -> None:
    public = {name for name in dir(identifier) if not name.startswith("_")}
    assert public == {"value"}


def test_identifiers_do_not_implicitly_convert_to_their_payload() -> None:
    with pytest.raises(TypeError):
        int(InstrumentId(3))  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        [0, 1, 2, 3][InstrumentId(1)]  # type: ignore[call-overload]


# --------------------------------------------------------------------------
# Absence assertions over the parsed module: nothing may generate an identifier
# --------------------------------------------------------------------------


def _module_tree() -> ast.Module:
    with open(ids.__file__, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def test_module_imports_nothing_that_could_mint_an_identifier() -> None:
    """No clock, no entropy, no UUIDs, no filesystem."""
    imported: set[str] = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(
        {"random", "secrets", "uuid", "time", "datetime", "os", "pathlib", "socket"}
    )
    assert imported <= {"__future__", "dataclasses", "typing", "ofa"}


def test_module_defines_no_generator_function() -> None:
    defined = {
        node.name
        for node in ast.walk(_module_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert defined.isdisjoint(
        {"new", "mint", "generate", "create", "next", "now", "random", "uuid"}
    )


def test_module_calls_no_nondeterministic_builtin() -> None:
    called = {
        node.func.id
        for node in ast.walk(_module_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"id", "hash", "eval", "exec", "open", "input"})


def test_module_declares_no_third_party_dependency() -> None:
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module.split(".")[0] in {"__future__", "dataclasses", "typing", "ofa"}


# --------------------------------------------------------------------------
# Error family
# --------------------------------------------------------------------------


def test_identifier_errors_belong_to_the_ofa_family_and_a_stdlib_family() -> None:
    assert issubclass(IdentifierTypeError, OfaError)
    assert issubclass(IdentifierTypeError, TypeError)
    assert issubclass(InvalidIdentifierError, OfaError)
    assert issubclass(InvalidIdentifierError, ValueError)


def test_no_overflow_specific_identifier_error_exists() -> None:
    """An identifier supports no arithmetic, so nothing can overflow."""
    from ofa.core import errors

    names = {name for name in vars(errors) if name.endswith("Error")}
    assert "IdentifierOverflowError" not in names


def test_out_of_range_index_is_a_value_error_not_an_overflow_error() -> None:
    with pytest.raises(InvalidIdentifierError) as caught:
        InstrumentId(INT32_MAX + 1)
    assert not isinstance(caught.value, OverflowError)


# --------------------------------------------------------------------------
# Documented semantics
# --------------------------------------------------------------------------


def test_provenance_id_documents_that_it_is_manifest_scoped() -> None:
    """The one semantic a reader must not miss is stated in the docstring."""
    doc = ProvenanceId.__doc__ or ""
    assert "manifest-scoped" in doc
    assert "never" in doc and "the same provenance" in doc


def test_run_id_documents_that_the_alphabet_is_not_fixed_here() -> None:
    doc = RunId.__doc__ or ""
    assert re.search(r"alphabet", doc)
    assert "not" in doc


def test_module_documents_that_core_never_mints_an_identifier() -> None:
    doc = ids.__doc__ or ""
    assert "never mints" in doc


class _Colour(Enum):
    RED = "red"


def test_enum_is_not_accepted_as_any_identifier() -> None:
    with pytest.raises(IdentifierTypeError):
        RunId(_Colour.RED)  # type: ignore[arg-type]
    with pytest.raises(IdentifierTypeError):
        InstrumentId(_Colour.RED)  # type: ignore[arg-type]
