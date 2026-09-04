"""Example-based tests for canonical serialization and stable content hashing.

The golden vector table is the spine of this file. Its byte strings and
digests are pinned literals, so any drift in a tag, in the key ordering, in
the separators, in the encoding, or in the format prefix fails loudly instead
of silently invalidating every identity the project has stored.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum, IntEnum, StrEnum
from typing import Final, NamedTuple, cast

import pytest

from ofa.core import hashing
from ofa.core.errors import CanonicalTypeError, CanonicalValueError, OfaError
from ofa.core.hashing import (
    _MAX_CANONICAL_DEPTH,
    CANONICAL_FORMAT_VERSION,
    canonical_bytes,
    content_hash,
    params_hash,
)
from ofa.core.money import Price, Ticks
from ofa.core.time import TradeDate, UtcNanos


def _make_enum(
    name: str,
    members: object,
    *,
    module: str,
    qualname: str | None = None,
) -> type[Enum]:
    """Build an enum whose defining module and qualified name are chosen here.

    Going through a helper keeps the class name a runtime argument, so two
    enums may deliberately share a name — which is exactly what the identity
    tests need — without the type checker objecting that a variable name does
    not match the enum's name.
    """
    return cast("type[Enum]", Enum(name, members, module=module, qualname=qualname))


# An enum whose defining module is an explicit literal rather than whatever
# name the test runner gives this file. That is what makes its canonical form
# pinnable in the golden table below.
COLOUR = _make_enum("Colour", ["RED", "GREEN"], module="ofa_golden_a")

#: (value, canonical bytes, digest). Computed once and pinned by hand.
GOLDEN_VECTORS: Final[list[tuple[object, bytes, str]]] = [
    (None, b'["none"]', "94cc39686e5a9449f676ec45a7095e879b280e0d1fd3c21667e1a438457551ad"),
    (True, b'["bool",true]', "61db2212df8976bab86101d485c6766676fce5f47a1f6c33dd1362b24af7549d"),
    (False, b'["bool",false]', "08d37dd76ab8101210d46bdbe664efc672dffdfa4563aadb0a148007a440f994"),
    (0, b'["int",0]', "98083a6b6d0ac4b50da773ef7dd70a31cc7003cd9b374b83fff0afb0870c3732"),
    (-1, b'["int",-1]', "3c20154f751fac85f87fb6915968ced21b92725363dd7d0c1c8f06be4fa41966"),
    (
        2**63,
        b'["int",9223372036854775808]',
        "d2c48d0e23d8fdf99b3f55c4df50d52ff9b774709ffe0f3d85258edd2f6cd362",
    ),
    ("", b'["str",""]', "450238b7e8bc8079b7eeca453472594b60b29d5a8412c3a7f9c206d315ce77b3"),
    ("abc", b'["str","abc"]', "a8c99b25abe5cb280f2948e95bccf443b97888cf6bb356be8af41e2a1177bee5"),
    (
        "été",
        b'["str","\\u00e9t\\u00e9"]',
        "c5a9aebc1da7e06128b1edc93a209ae7191ca8825efc8c5e0eec17a3556702f3",
    ),
    (b"", b'["bytes",""]', "dfdab7b6f5b4f4de6f559871758164ce1b0b47f63537f6ac6daf0a6761342a3c"),
    (
        b"\x01\xff",
        b'["bytes","01ff"]',
        "178d84f709c3a3ad8debff2de0f9059ecc49e73f5ed58f3b9470db020f270b3f",
    ),
    ([], b'["seq",[]]', "14e09d6787098f3e91bcaceed702879d75089755f11e9a127dab27a67b764582"),
    ((), b'["seq",[]]', "14e09d6787098f3e91bcaceed702879d75089755f11e9a127dab27a67b764582"),
    (
        [1, "a", None],
        b'["seq",[["int",1],["str","a"],["none"]]]',
        "3ebbff75cdfb2cba2e7746d84263593ce267edea404ff358aeae4f746af3fa12",
    ),
    (
        (1, "a", None),
        b'["seq",[["int",1],["str","a"],["none"]]]',
        "3ebbff75cdfb2cba2e7746d84263593ce267edea404ff358aeae4f746af3fa12",
    ),
    ({}, b'["map",[]]', "9766cc52ef90b9aa5956fc98d3f377e032b8bdc7f14e81ded487d905c28c194b"),
    (
        {"b": 1, "a": 2},
        b'["map",[["a",["int",2]],["b",["int",1]]]]',
        "b31daf37817340caed64fe5da49471a4e01a919451f9d61525d0bcc45964d31e",
    ),
    (
        {"a": 2, "b": 1},
        b'["map",[["a",["int",2]],["b",["int",1]]]]',
        "b31daf37817340caed64fe5da49471a4e01a919451f9d61525d0bcc45964d31e",
    ),
    (
        {"A": 1, "Z": 2, "a": 3, "É": 4},
        b'["map",[["A",["int",1]],["Z",["int",2]],["a",["int",3]],["\\u00c9",["int",4]]]]',
        "4a42bbc170b4cbdac4ad90f3d236d0dbf8acef03345306f7c67c02672eebdff1",
    ),
    (
        {"outer": {"y": [1, 2], "x": {"k": True}}},
        b'["map",[["outer",["map",[["x",["map",[["k",["bool",true]]]]],'
        b'["y",["seq",[["int",1],["int",2]]]]]]]]]',
        "70ba6accbdde4221969bc597b5940d87276cd9070c6d1d6b59de37dd33792f0b",
    ),
    (
        Price(1_500_000_000),
        b'["price",1500000000]',
        "b4c41864690c04edf5f5a33e7646a72e0ae51d40400e9fe36c0bb614e26443e1",
    ),
    (
        Price(-1),
        b'["price",-1]',
        "c5d2e9312ff4a26ca0d9c718b4f8b10b4f7541f782b11f01e1d501a70e40d9bb",
    ),
    (
        Ticks(-6),
        b'["ticks",-6]',
        "d659517f937c5c82b79b5ed1104b5bf59d76e686c74d6fed9adc51bad05c7de2",
    ),
    (
        UtcNanos(0),
        b'["utc_nanos",0]',
        "774e6c8008f0e0aa694aa54b5b3c6b726ac1b5e343ed7ffea59bb5fc6f3e2c75",
    ),
    (
        UtcNanos(-1),
        b'["utc_nanos",-1]',
        "b3bfc8931f4a770a1a67777babdec8f27dd7d01cacec57d8bc57110790363754",
    ),
    (
        TradeDate(2024, 3, 11),
        b'["trade_date","2024-03-11"]',
        "cd0edad69e7058756fbdcb3a97097bcdd45476e734cab2e541241c083734332e",
    ),
    (
        TradeDate(1, 1, 1),
        b'["trade_date","0001-01-01"]',
        "64b5469ecbe7d8ee959960ae7aa9148e0f78a89fb9cfdc842e8eee4942e9973e",
    ),
    (
        COLOUR["RED"],
        b'["enum","ofa_golden_a","Colour","RED"]',
        "057f12a714873df4a263a3746965a1b8b8711f9dd777a02d44db1006b1a17813",
    ),
]


# --------------------------------------------------------------------------
# Golden vectors
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "expected", "_digest"), GOLDEN_VECTORS)
def test_canonical_bytes_match_pinned_vectors(value: object, expected: bytes, _digest: str) -> None:
    assert canonical_bytes(value) == expected


@pytest.mark.parametrize(("value", "_expected", "digest"), GOLDEN_VECTORS)
def test_content_hash_matches_pinned_vectors(value: object, _expected: bytes, digest: str) -> None:
    assert content_hash(value) == digest


def test_golden_vectors_cover_every_canonical_tag() -> None:
    """Every tag the canonicalizer can emit has at least one pinned vector."""
    tags = {canonical_bytes(value).split(b'"')[1] for value, _, _ in GOLDEN_VECTORS}
    assert tags == {
        b"none",
        b"bool",
        b"int",
        b"str",
        b"bytes",
        b"seq",
        b"map",
        b"price",
        b"ticks",
        b"utc_nanos",
        b"trade_date",
        b"enum",
    }


# --------------------------------------------------------------------------
# Encoding and rendering contract
# --------------------------------------------------------------------------


def test_output_is_pure_ascii_even_for_non_ascii_input() -> None:
    produced = canonical_bytes({"kéy": "中文\U0001f600"})
    produced.decode("ascii")  # raises if a non-ASCII byte escaped
    assert b"\\u" in produced


def test_no_incidental_whitespace() -> None:
    produced = canonical_bytes({"a": [1, 2], "b": {"c": 3}})
    assert b" " not in produced
    assert b"\n" not in produced
    assert b"\t" not in produced


#: A value exercising every structural tag at once, for the JSON-validity
#: checks below.
REPRESENTATIVE_NESTED: Final[dict[str, object]] = {
    "zeta": "été 中文",
    "alpha": [1, -2, True, False, None],
    "nested": {"b": Price(1_500_000_000), "a": Ticks(-6), "c": {"deep": (7, 8)}},
    "raw": b"\x00\xff\x10",
    "when": UtcNanos(-1),
    "day": TradeDate(2024, 3, 11),
    "colour": COLOUR["RED"],
    "big": 2**70,
}


def test_canonical_bytes_are_valid_json() -> None:
    """The canonical bytes parse as JSON.

    This asserts validity only. It deliberately does not assert that parsing
    reconstructs the original value: the tagged representation is not
    object-preserving JSON, and ``json.loads`` returns the tagged tree, not the
    dict, Price, TradeDate or enum member that produced it.
    """
    parsed = json.loads(canonical_bytes(REPRESENTATIVE_NESTED).decode("ascii"))
    assert isinstance(parsed, list)
    assert parsed[0] == "map"


@pytest.mark.parametrize(("value", "_expected", "_digest"), GOLDEN_VECTORS)
def test_every_golden_vector_is_valid_json(value: object, _expected: bytes, _digest: str) -> None:
    parsed = json.loads(canonical_bytes(value).decode("ascii"))
    assert isinstance(parsed, list)
    assert isinstance(parsed[0], str)


def test_nfc_and_nfd_spellings_are_different_values() -> None:
    """Strings are not normalized: reject-or-preserve, never transform."""
    nfc = "é"
    nfd = "é"
    assert nfc != nfd
    assert canonical_bytes(nfc) != canonical_bytes(nfd)


# --------------------------------------------------------------------------
# Ordering
# --------------------------------------------------------------------------


def test_mapping_key_insertion_order_is_irrelevant() -> None:
    forward = {"a": 1, "b": 2, "c": 3}
    backward = {"c": 3, "b": 2, "a": 1}
    assert canonical_bytes(forward) == canonical_bytes(backward)
    assert content_hash(forward) == content_hash(backward)


def test_mapping_keys_sort_by_unicode_code_point() -> None:
    produced = canonical_bytes({"a": 1, "A": 2, "Z": 3, "b": 4})
    assert produced == (
        b'["map",[["A",["int",2]],["Z",["int",3]],["a",["int",1]],["b",["int",4]]]]'
    )


def test_sequence_order_is_significant() -> None:
    assert canonical_bytes([1, 2]) != canonical_bytes([2, 1])


def test_nested_mapping_order_is_irrelevant_at_every_level() -> None:
    forward = {"outer": {"x": 1, "y": 2}, "other": [{"p": 1, "q": 2}]}
    backward = {"other": [{"q": 2, "p": 1}], "outer": {"y": 2, "x": 1}}
    assert canonical_bytes(forward) == canonical_bytes(backward)


# --------------------------------------------------------------------------
# Ambiguity: values that must not collide
# --------------------------------------------------------------------------


class _Side(IntEnum):
    BUY = 1


class _Tier(StrEnum):
    OBSERVED = "observed"


DistinctPair = tuple[object, object]

MUST_DIFFER: Final[list[DistinctPair]] = [
    (True, 1),
    (False, 0),
    ("1", 1),
    ("true", True),
    (_Side.BUY, 1),
    (_Tier.OBSERVED, "observed"),
    (b"1", "1"),
    (b"ab", "ab"),
    (Price(5), 5),
    (Price(5), Ticks(5)),
    (Price(5), UtcNanos(5)),
    (Ticks(5), UtcNanos(5)),
    (UtcNanos(5), 5),
    (TradeDate(2024, 3, 11), "2024-03-11"),
    ([], {}),
    ([], None),
    ({}, None),
    ({"a": 1}, [["a", 1]]),
    ([1], 1),
    (COLOUR["RED"], "RED"),
    (COLOUR["RED"], COLOUR["GREEN"]),
]


@pytest.mark.parametrize(("left", "right"), MUST_DIFFER)
def test_distinct_values_have_distinct_canonical_forms(left: object, right: object) -> None:
    assert canonical_bytes(left) != canonical_bytes(right)
    assert content_hash(left) != content_hash(right)


def test_bool_key_and_string_key_cannot_collide_because_bool_keys_are_rejected() -> None:
    """Plain JSON renders {True: 1} and {"true": 1} identically. Here one raises."""
    assert canonical_bytes({"true": 1}) == b'["map",[["true",["int",1]]]]'
    with pytest.raises(CanonicalTypeError):
        canonical_bytes({True: 1})


def test_int_key_and_string_key_cannot_collide() -> None:
    """Plain JSON renders {1: "a", "1": "b"} with a duplicate key."""
    with pytest.raises(CanonicalTypeError):
        canonical_bytes({1: "a", "1": "b"})


def test_identically_named_enums_in_different_modules_differ() -> None:
    """__qualname__ alone would make these two indistinguishable."""
    here = _make_enum("Colour", ["RED"], module="ofa_golden_a")
    there = _make_enum("Colour", ["RED"], module="ofa_golden_b")
    assert canonical_bytes(here["RED"]) != canonical_bytes(there["RED"])


def test_identically_named_enums_in_one_module_differ_by_qualname() -> None:
    outer = _make_enum("Outer", ["RED"], module="ofa_golden_a", qualname="Outer")
    inner = _make_enum("Outer", ["RED"], module="ofa_golden_a", qualname="Wrap.Outer")
    assert canonical_bytes(outer["RED"]) != canonical_bytes(inner["RED"])


def test_enum_identity_is_the_member_name_not_its_value() -> None:
    """Renumbering a member's value must not move the hash."""
    first = _make_enum("Tier", [("OBSERVED", 1)], module="ofa_golden_a")
    renumbered = _make_enum("Tier", [("OBSERVED", 7)], module="ofa_golden_a")
    assert first["OBSERVED"].value != renumbered["OBSERVED"].value
    assert canonical_bytes(first["OBSERVED"]) == canonical_bytes(renumbered["OBSERVED"])


def test_list_and_tuple_share_one_sequence_tag() -> None:
    assert canonical_bytes([1, "a"]) == canonical_bytes((1, "a"))
    assert content_hash([1, "a"]) == content_hash((1, "a"))


# --------------------------------------------------------------------------
# Rejected types
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Params:
    window: int


@dataclass(frozen=True, slots=True)
class _OtherParams:
    window: int


class _Point(NamedTuple):
    x: int


class _MyInt(int):
    pass


class _MyStr(str):
    pass


class _MyBytes(bytes):
    pass


class _MyList(list[int]):
    pass


class _MyDict(dict[str, int]):
    pass


def _example_function() -> None:  # pragma: no cover - referenced, never called
    return None


REJECTED_TYPES: Final[list[object]] = [
    1.0,
    0.5,
    float("nan"),
    float("inf"),
    -0.0,
    complex(1, 2),
    Decimal("1.5"),
    {1, 2},
    frozenset({1, 2}),
    bytearray(b"ab"),
    memoryview(b"ab"),
    datetime(2024, 3, 11, tzinfo=UTC),
    date(2024, 3, 11),
    _Params(window=5),
    _Point(x=1),
    _MyInt(1),
    _MyStr("a"),
    _MyBytes(b"a"),
    _MyList([1]),
    _MyDict({"a": 1}),
    OrderedDict({"a": 1}),
    defaultdict(int),
    Counter("aa"),
    object(),
    _Params,
    _example_function,
    range(3),
    iter([1, 2]),
]


@pytest.mark.parametrize("value", REJECTED_TYPES)
def test_unsupported_types_are_rejected(value: object) -> None:
    with pytest.raises(CanonicalTypeError):
        canonical_bytes(value)


@pytest.mark.parametrize("value", REJECTED_TYPES)
def test_unsupported_types_are_rejected_when_nested(value: object) -> None:
    with pytest.raises(CanonicalTypeError):
        canonical_bytes({"outer": [value]})


def test_float_rejection_names_the_reason() -> None:
    with pytest.raises(CanonicalTypeError, match="float"):
        canonical_bytes(1.0)


def test_set_rejection_names_the_reason() -> None:
    with pytest.raises(CanonicalTypeError, match="no order"):
        canonical_bytes({1, 2})


def test_two_dataclasses_with_identical_fields_both_raise() -> None:
    """Neither is canonicalized, so neither can silently collide with the other."""
    with pytest.raises(CanonicalTypeError):
        canonical_bytes(_Params(window=5))
    with pytest.raises(CanonicalTypeError):
        canonical_bytes(_OtherParams(window=5))


@pytest.mark.parametrize("key", [1, True, None, 1.5, b"a", (1,), _MyStr("a"), _Tier.OBSERVED])
def test_non_string_mapping_keys_are_rejected(key: object) -> None:
    with pytest.raises(CanonicalTypeError):
        canonical_bytes({key: 1})


# --------------------------------------------------------------------------
# Rejected values of supported types
# --------------------------------------------------------------------------


def test_lone_surrogate_string_is_rejected() -> None:
    with pytest.raises(CanonicalValueError, match="UTF-8"):
        canonical_bytes("\ud800")


def test_lone_surrogate_mapping_key_is_rejected() -> None:
    with pytest.raises(CanonicalValueError, match="UTF-8"):
        canonical_bytes({"\ud800": 1})


def _nest(depth: int) -> object:
    value: object = 0
    for _ in range(depth):
        value = [value]
    return value


def test_nesting_at_the_depth_limit_is_accepted() -> None:
    canonical_bytes(_nest(_MAX_CANONICAL_DEPTH))


def test_nesting_past_the_depth_limit_is_rejected() -> None:
    with pytest.raises(CanonicalValueError, match="deeper"):
        canonical_bytes(_nest(_MAX_CANONICAL_DEPTH + 1))


def test_self_referential_structure_raises_rather_than_recursing_forever() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises(CanonicalValueError):
        canonical_bytes(cyclic)


# --------------------------------------------------------------------------
# Digest contract
# --------------------------------------------------------------------------


HEX_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")


@pytest.mark.parametrize(("value", "_expected", "_digest"), GOLDEN_VECTORS)
def test_digest_is_sixty_four_lowercase_hex_characters(
    value: object, _expected: bytes, _digest: str
) -> None:
    assert HEX_DIGEST.fullmatch(content_hash(value))


def test_digest_is_sha256_over_the_prefixed_canonical_bytes() -> None:
    value = {"a": 1, "b": [2, 3]}
    expected = hashlib.sha256(b"ofa-canon-1\x00" + canonical_bytes(value)).hexdigest()
    assert content_hash(value) == expected


def test_digest_is_not_a_bare_hash_of_the_canonical_bytes() -> None:
    """The format prefix is part of the contract, not decoration."""
    value = {"a": 1}
    assert content_hash(value) != hashlib.sha256(canonical_bytes(value)).hexdigest()


def test_format_version_is_the_pinned_string() -> None:
    assert CANONICAL_FORMAT_VERSION == "ofa-canon-1"


def test_repeated_calls_are_stable_within_a_process() -> None:
    value = {"b": [1, {"c": Price(7)}], "a": TradeDate(2024, 3, 11)}
    assert canonical_bytes(value) == canonical_bytes(value)
    assert content_hash(value) == content_hash(value)


def test_equal_but_distinct_objects_hash_identically() -> None:
    left = {"a": [Price(5), UtcNanos(9)], "b": "x"}
    right = {"b": "x", "a": [Price(5), UtcNanos(9)]}
    assert left is not right
    assert content_hash(left) == content_hash(right)


def test_changing_one_parameter_changes_the_digest() -> None:
    base = {"window": 60, "threshold": 3, "side": "BUY"}
    changed = {"window": 61, "threshold": 3, "side": "BUY"}
    dropped = {"window": 60, "threshold": 3}
    assert content_hash(base) != content_hash(changed)
    assert content_hash(base) != content_hash(dropped)


# --------------------------------------------------------------------------
# params_hash
# --------------------------------------------------------------------------


def test_params_hash_equals_content_hash_for_the_same_mapping() -> None:
    params = {"window": 60, "tier": "OBSERVED", "levels": (1, 2, 3)}
    assert params_hash(params) == content_hash(params)


def test_params_hash_is_insensitive_to_key_insertion_order() -> None:
    assert params_hash({"a": 1, "b": 2}) == params_hash({"b": 2, "a": 1})


@pytest.mark.parametrize("value", [[], (), "abc", 1, None, {1: 2}])
def test_params_hash_requires_a_string_keyed_dict(value: object) -> None:
    with pytest.raises(CanonicalTypeError):
        params_hash(value)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Error family
# --------------------------------------------------------------------------


def test_canonical_errors_belong_to_the_ofa_family_and_a_stdlib_family() -> None:
    assert issubclass(CanonicalTypeError, OfaError)
    assert issubclass(CanonicalTypeError, TypeError)
    assert issubclass(CanonicalValueError, OfaError)
    assert issubclass(CanonicalValueError, ValueError)


# --------------------------------------------------------------------------
# Absence assertions: the forbidden mechanisms must not appear in the module
# --------------------------------------------------------------------------

# These walk the parsed syntax tree rather than the raw text. The module's own
# docstring names hash(), repr() and sort_keys=True while explaining why they
# are forbidden, so a textual scan would fail on the explanation instead of on
# the code.


def _module_tree() -> ast.Module:
    with open(hashing.__file__, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def _called_builtin_names() -> set[str]:
    return {
        node.func.id
        for node in ast.walk(_module_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("hash", "Python's hash() is salted per process and would break reproducibility"),
        ("repr", "repr() is not a defined serialization contract"),
        ("id", "object identity varies between processes"),
        ("float", "no value is ever converted to a float"),
        ("eval", "nothing here evaluates source"),
        ("exec", "nothing here executes source"),
    ],
)
def test_forbidden_builtin_is_never_called(name: str, reason: str) -> None:
    assert name not in _called_builtin_names(), reason


def test_key_ordering_is_never_delegated_to_the_renderer() -> None:
    """sort_keys=True would mean a lost flag silently changes every digest."""
    delegated = [
        keyword
        for node in ast.walk(_module_tree())
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "sort_keys"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
    ]
    assert delegated == []


def test_module_imports_nothing_nondeterministic() -> None:
    imported: set[str] = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"random", "secrets", "pickle", "time", "os", "uuid"})


def test_module_declares_no_third_party_dependency() -> None:
    """Everything imported is standard library or first-party ofa."""
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            root = node.module.split(".")[0]
            assert root in {"__future__", "enum", "typing", "ofa"}, root
