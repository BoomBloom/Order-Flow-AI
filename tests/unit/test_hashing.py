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
from enum import KEEP, Enum, Flag, IntEnum, IntFlag, StrEnum
from typing import Final, NamedTuple, cast

import pytest

from ofa.core import hashing
from ofa.core.capability import CapabilityEntry, CapabilityRecord, DataRequirement
from ofa.core.errors import (
    CanonicalTypeError,
    CanonicalValueError,
    InvalidIdentifierError,
    OfaError,
)
from ofa.core.hashing import (
    _MAX_CANONICAL_DEPTH,
    CANONICAL_FORMAT_VERSION,
    canonical_bytes,
    content_hash,
    params_hash,
)
from ofa.core.ids import INT32_MAX, INT32_MIN, InstrumentId, ProvenanceId, RunId
from ofa.core.lifecycle import ResetReason, RollPolicy
from ofa.core.money import Price, Ticks
from ofa.core.provenance import ProvenanceTier
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


#: Step 3b identifier vectors. These live in their own table so that the Step
#: 3a table above remains visibly, byte-for-byte untouched: adding a canonical
#: tag is additive and must not disturb a single digest already pinned.
IDENTIFIER_VECTORS: Final[list[tuple[object, bytes, str]]] = [
    (
        RunId("abc"),
        b'["run_id","abc"]',
        "400dfb9078c0489a887e9198b76161823254ed22da925461fbf0dccb874beaa7",
    ),
    (
        RunId("Run-A"),
        b'["run_id","Run-A"]',
        "e14de8977639e7ce1bb8921d8c003e7c97495bdf16c1819b81c1e5ea6ba02944",
    ),
    (
        RunId("3"),
        b'["run_id","3"]',
        "1b84788d38bc2fb6289b5543d23b74e7bf8f760a39b7bc3a071ae7468b0f857a",
    ),
    (
        RunId("\u00e9t\u00e9"),
        b'["run_id","\\u00e9t\\u00e9"]',
        "6cbd4a75ab28a8df705002d0947f5ebc8ff4de59bb8ace6b3b8ecc183a8dec2b",
    ),
    (
        InstrumentId(0),
        b'["instrument_id",0]',
        "df159ef8405e613d2b500a287caf2ab69e1b0667e485e1f120532c19ee01bb16",
    ),
    (
        InstrumentId(7),
        b'["instrument_id",7]',
        "d708a1dd9a4c44f3f2dce0552978e126a808f9d07ea507e6754b9dcb639d6293",
    ),
    (
        InstrumentId(-1),
        b'["instrument_id",-1]',
        "99bf194048c38c5a081710fc208bb05094444cb5480fb37534799f01ec8cc505",
    ),
    (
        InstrumentId(INT32_MIN),
        b'["instrument_id",-2147483648]',
        "8c7808c3af598e44d703671c7c424564208ef1425688f6aa11e14217cdcc6e5b",
    ),
    (
        InstrumentId(INT32_MAX),
        b'["instrument_id",2147483647]',
        "f8e2bae05531081c50ed59800605c7031c76504d41469c9b68af2674b723591c",
    ),
    (
        ProvenanceId(0),
        b'["provenance_id",0]',
        "53ee3f6a9951c0969ae4ae6d1cc99ddbca773c0ea5682d0fb532f535e266d776",
    ),
    (
        ProvenanceId(3),
        b'["provenance_id",3]',
        "512e56a80059a9d7505a6f98d97ec4cc4929c78d549fcbe7356ec0d72d24a567",
    ),
    (
        ProvenanceId(-1),
        b'["provenance_id",-1]',
        "ec8c4230a0440a461d0708552c277cbc97ba61df1dad6c7ed7396a872bd74134",
    ),
    (
        ProvenanceId(INT32_MAX),
        b'["provenance_id",2147483647]',
        "bca7121aa5bae463eb2fa6292545f0da00cbe49f0f78f5792d07986c58df7ed8",
    ),
]

_OBSERVED_ENTRY: Final = CapabilityEntry(present=True, tier=ProvenanceTier.OBSERVED)
_INFERRED_ENTRY: Final = CapabilityEntry(present=True, tier=ProvenanceTier.INFERRED)
_ABSENT_ENTRY: Final = CapabilityEntry(present=False, tier=None)

#: M1 vectors. A third table, again so the two tables above stay visibly
#: untouched: the flag and capability tags are additive and must disturb
#: nothing already pinned.
M1_VECTORS: Final[list[tuple[object, bytes, str]]] = [
    (
        ProvenanceTier.OBSERVED,
        b'["enum","ofa.core.provenance","ProvenanceTier","OBSERVED"]',
        "b669d2cb46af0dd2e85be6d00bbe73904abcf954152fa54b2b69153189784fc7",
    ),
    (
        ProvenanceTier.RECONSTRUCTED,
        b'["enum","ofa.core.provenance","ProvenanceTier","RECONSTRUCTED"]',
        "859a6e2e73833319ac68c671c771ae32b40643019507762b6e759fef59c0358b",
    ),
    (
        ProvenanceTier.INFERRED,
        b'["enum","ofa.core.provenance","ProvenanceTier","INFERRED"]',
        "4daef4bf1c33e5db87cea592ee5149e8c5fb2b1e991a9599136a6c726b8007b8",
    ),
    (
        ProvenanceTier.SIMULATED,
        b'["enum","ofa.core.provenance","ProvenanceTier","SIMULATED"]',
        "1760d466428a181cc89987ac565f55714302dba84618c28a055dfd06120c17cf",
    ),
    (
        RollPolicy.RESET,
        b'["enum","ofa.core.lifecycle","RollPolicy","RESET"]',
        "6d356818cc57741680c2c785cc1dbf4e7b12e339ce78b9da529961a621b9fceb",
    ),
    (
        RollPolicy.CARRY_ADJUSTED,
        b'["enum","ofa.core.lifecycle","RollPolicy","CARRY_ADJUSTED"]',
        "67b467af0d7dc1612e3716503a0b6d063eb8de0697f6cd7a08415630644e18c7",
    ),
    (
        ResetReason.SPLIT_SEGMENT_START,
        b'["enum","ofa.core.lifecycle","ResetReason","SPLIT_SEGMENT_START"]',
        "f99819130be5afa04436fd986476589cb33aaa33b23e9cae24c3e2af6da2394d",
    ),
    (
        DataRequirement(0),
        b'["flag","ofa.core.capability","DataRequirement",[]]',
        "42b9055b966e00e139af6a90f9356c0fa40c4beb690bb23fd2913ad36c536133",
    ),
    (
        DataRequirement.TRADES,
        b'["flag","ofa.core.capability","DataRequirement",["TRADES"]]',
        "395b7bed5384a5515f413b433c21330096729fc10043a59d6fc448d02f5b0a5f",
    ),
    (
        DataRequirement.STATUS,
        b'["flag","ofa.core.capability","DataRequirement",["STATUS"]]',
        "eae51fbf55926597259d387135fb6f40fe5afb4227dc6ae12ca30db3707b4530",
    ),
    (
        DataRequirement.TRADES | DataRequirement.BBO,
        b'["flag","ofa.core.capability","DataRequirement",["BBO","TRADES"]]',
        "48a2c3856c4ca967141f30527f755d5eb7dab300ccf95aea3aaf45eb1fb051f7",
    ),
    (
        DataRequirement.BBO | DataRequirement.TRADES,
        b'["flag","ofa.core.capability","DataRequirement",["BBO","TRADES"]]',
        "48a2c3856c4ca967141f30527f755d5eb7dab300ccf95aea3aaf45eb1fb051f7",
    ),
    (
        DataRequirement.TRADES
        | DataRequirement.AGGRESSOR
        | DataRequirement.BBO
        | DataRequirement.MBP_10
        | DataRequirement.MBO
        | DataRequirement.TS_RECV
        | DataRequirement.STATUS,
        b'["flag","ofa.core.capability","DataRequirement",'
        b'["AGGRESSOR","BBO","MBO","MBP_10","STATUS","TRADES","TS_RECV"]]',
        "c560d1468519ec7a5a2c07c3b31788006078b7022444affe6d537842787c3d1b",
    ),
    (
        _OBSERVED_ENTRY,
        b'["capability_entry",true,["enum","ofa.core.provenance","ProvenanceTier","OBSERVED"]]',
        "1eb5bad70d36f84b98b365121ade6e3fd5de75ad81ff6df12c7bf0bf10fb01ce",
    ),
    (
        _INFERRED_ENTRY,
        b'["capability_entry",true,["enum","ofa.core.provenance","ProvenanceTier","INFERRED"]]',
        "aabaaf919322c320b49cf9a40590036a3461157de91a29d4a4ee3d5b11dd0c1d",
    ),
    (
        _ABSENT_ENTRY,
        b'["capability_entry",false,["none"]]',
        "1ee2205d926590349f6a3569ad32697f9a09d5d58c37239105acd7263d73f1c9",
    ),
    (
        CapabilityRecord(()),
        b'["capability_record",[]]',
        "1a2e0a9afc6a0ca803ed7227a212cb4e17822094f3dbd4ba680cd833d63a7fbb",
    ),
    (
        CapabilityRecord(
            (
                (DataRequirement.TRADES, _OBSERVED_ENTRY),
                (DataRequirement.AGGRESSOR, _INFERRED_ENTRY),
                (DataRequirement.MBO, _ABSENT_ENTRY),
            )
        ),
        b'["capability_record",[[["flag","ofa.core.capability","DataRequirement",'
        b'["TRADES"]],["capability_entry",true,["enum","ofa.core.provenance",'
        b'"ProvenanceTier","OBSERVED"]]],[["flag","ofa.core.capability",'
        b'"DataRequirement",["AGGRESSOR"]],["capability_entry",true,["enum",'
        b'"ofa.core.provenance","ProvenanceTier","INFERRED"]]],[["flag",'
        b'"ofa.core.capability","DataRequirement",["MBO"]],["capability_entry",'
        b'false,["none"]]]]]',
        "1ab3772a5627c05b09c832884a196d399e843735068c5eb08b1e7e3d28a94a33",
    ),
]

#: Every pinned vector, Step 3a, Step 3b and M1 together.
ALL_VECTORS: Final[list[tuple[object, bytes, str]]] = (
    GOLDEN_VECTORS + IDENTIFIER_VECTORS + M1_VECTORS
)

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
    tags = {canonical_bytes(value).split(b'"')[1] for value, _, _ in ALL_VECTORS}
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
        b"run_id",
        b"instrument_id",
        b"provenance_id",
        b"flag",
        b"capability_entry",
        b"capability_record",
    }


# --------------------------------------------------------------------------
# Step 3a regression guard
# --------------------------------------------------------------------------


def test_step_3a_golden_table_is_unchanged() -> None:
    """The Step 3a vectors are frozen: adding a tag must disturb none of them.

    A single fingerprint over the whole table, so an edit anywhere in it — a
    changed byte string, a changed digest, a reordered, added or removed row —
    fails here rather than being absorbed into a passing parametrized run.
    """
    fingerprint = hashlib.sha256()
    for _value, expected, digest in GOLDEN_VECTORS:
        fingerprint.update(expected)
        fingerprint.update(b"\x00")
        fingerprint.update(digest.encode("ascii"))
        fingerprint.update(b"\x00")
    assert len(GOLDEN_VECTORS) == 28
    assert (
        fingerprint.hexdigest()
        == "9db8f755f3bfd5943e39cc0f44d2fcc7bd285f62bb21c3ab8b32bc71b73fd443"
    )


def test_step_3b_identifier_table_is_unchanged() -> None:
    """The Step 3b vectors are frozen for the same reason as the Step 3a ones."""
    fingerprint = hashlib.sha256()
    for _value, expected, digest in IDENTIFIER_VECTORS:
        fingerprint.update(expected)
        fingerprint.update(b"\x00")
        fingerprint.update(digest.encode("ascii"))
        fingerprint.update(b"\x00")
    assert len(IDENTIFIER_VECTORS) == 13
    assert (
        fingerprint.hexdigest()
        == "ea25269bf5a430aff15af6ab08cade16607535c7dbd4d44bf79880d6bad0eb6a"
    )


def test_m1_tags_are_additive_only() -> None:
    """No M1 tag collides with a tag that already existed."""
    existing = {
        canonical_bytes(value).split(b'"')[1] for value, _, _ in GOLDEN_VECTORS + IDENTIFIER_VECTORS
    }
    added = {canonical_bytes(value).split(b'"')[1] for value, _, _ in M1_VECTORS}
    assert {b"flag", b"capability_entry", b"capability_record"} <= added
    assert added - existing == {b"flag", b"capability_entry", b"capability_record"}


def test_identifier_tags_are_additive_only() -> None:
    """No identifier tag collides with a tag that already existed."""
    existing = {canonical_bytes(value).split(b'"')[1] for value, _, _ in GOLDEN_VECTORS}
    added = {canonical_bytes(value).split(b'"')[1] for value, _, _ in IDENTIFIER_VECTORS}
    assert added == {b"run_id", b"instrument_id", b"provenance_id"}
    assert existing.isdisjoint(added)


# --------------------------------------------------------------------------
# M1: flag and capability canonicalization
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "expected", "_digest"), M1_VECTORS)
def test_m1_canonical_bytes_match_pinned_vectors(
    value: object, expected: bytes, _digest: str
) -> None:
    assert canonical_bytes(value) == expected


@pytest.mark.parametrize(("value", "_expected", "digest"), M1_VECTORS)
def test_m1_content_hash_matches_pinned_vectors(
    value: object, _expected: bytes, digest: str
) -> None:
    assert content_hash(value) == digest


@pytest.mark.parametrize(("value", "_expected", "_digest"), M1_VECTORS)
def test_m1_vectors_are_valid_json(value: object, _expected: bytes, _digest: str) -> None:
    parsed = json.loads(canonical_bytes(value).decode("ascii"))
    assert isinstance(parsed, list)
    assert isinstance(parsed[0], str)


def test_empty_flag_canonicalizes_instead_of_raising() -> None:
    """Its .name is None; reaching the encoder previously raised AttributeError."""
    assert DataRequirement(0).name is None
    assert canonical_bytes(DataRequirement(0)) == (
        b'["flag","ofa.core.capability","DataRequirement",[]]'
    )


def test_no_flag_value_escapes_the_error_contract() -> None:
    """Every value of the flag, empty through full, canonicalizes cleanly."""
    for raw in range(0, 128):
        produced = canonical_bytes(DataRequirement(raw))
        produced.decode("ascii")
        assert produced.startswith(b'["flag",')


class _FirstOrder(IntFlag):
    ALPHA = 1
    BETA = 2


class _SecondOrder(IntFlag):
    BETA = 2
    ALPHA = 1


def test_composite_canonical_form_ignores_declaration_order() -> None:
    """Flag.name joins members in declaration order; the canonical form must not."""
    first = _FirstOrder.ALPHA | _FirstOrder.BETA
    second = _SecondOrder.ALPHA | _SecondOrder.BETA
    assert first.name != second.name
    assert first.value == second.value
    assert json.loads(canonical_bytes(first).decode("ascii"))[3] == ["ALPHA", "BETA"]
    assert json.loads(canonical_bytes(second).decode("ascii"))[3] == ["ALPHA", "BETA"]


def test_composite_canonical_form_ignores_combination_order() -> None:
    left = DataRequirement.TRADES | DataRequirement.BBO
    right = DataRequirement.BBO | DataRequirement.TRADES
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_hash(left) == content_hash(right)


class _WithAlias(IntFlag):
    TRADES = 1
    BBO = 2
    BOTH = 3


class _Kept(IntFlag, boundary=KEEP):
    """A flag that retains undeclared bits, as IntFlag does by default."""

    ALPHA = 1


def test_a_flag_carrying_undeclared_bits_is_refused() -> None:
    """It would otherwise canonicalize as the members it does contain."""
    assert _Kept(4).name is None
    assert tuple(_Kept(4)) == ()
    with pytest.raises(CanonicalValueError, match="does not decompose"):
        canonical_bytes(_Kept(4))
    with pytest.raises(CanonicalValueError, match="does not decompose"):
        canonical_bytes(_Kept(5))


def test_an_undecomposable_flag_never_collides_with_the_empty_flag() -> None:
    """The collision this guard exists to prevent: unequal values, one digest."""
    assert _Kept(0) != _Kept(4)
    assert canonical_bytes(_Kept(0)) == b'["flag","tests.unit.test_hashing","_Kept",[]]'
    with pytest.raises(CanonicalValueError):
        canonical_bytes(_Kept(4))


def test_a_nameless_member_is_refused_rather_than_encoded() -> None:
    """A defensive guard the public dispatch cannot currently reach.

    Flag iteration yields only named members and plain enum members always have
    names, so nothing routes a nameless member into the encoder today. The
    guard is asserted directly so it cannot rot into a silent empty string.
    """
    nameless = _Kept(4)
    assert nameless.name is None
    with pytest.raises(CanonicalValueError, match="no member name"):
        hashing._member_name(nameless, "probe")


def test_a_composite_alias_matches_the_union_of_its_parts() -> None:
    assert canonical_bytes(_WithAlias.BOTH) == canonical_bytes(_WithAlias.TRADES | _WithAlias.BBO)


def test_a_flag_is_never_its_integer_or_a_plain_enum() -> None:
    flag = DataRequirement.TRADES
    assert canonical_bytes(flag) != canonical_bytes(flag.value)
    assert canonical_bytes(flag).startswith(b'["flag",')
    assert canonical_bytes(ProvenanceTier.OBSERVED).startswith(b'["enum",')


def test_plain_enums_keep_the_enum_tag_unchanged() -> None:
    """Adding the flag path must not alter existing enum semantics."""
    for value in (ProvenanceTier.OBSERVED, RollPolicy.RESET, ResetReason.HALT_RESUME):
        assert canonical_bytes(value).startswith(b'["enum",')
    assert canonical_bytes(_Side.BUY).startswith(b'["enum",')
    assert canonical_bytes(_Tier.OBSERVED).startswith(b'["enum",')


def test_int_enum_and_str_enum_are_not_treated_as_flags() -> None:
    assert not isinstance(_Side.BUY, Flag)
    assert not isinstance(_Tier.OBSERVED, Flag)


def test_two_flag_types_with_the_same_member_names_differ() -> None:
    assert canonical_bytes(_FirstOrder.ALPHA) != canonical_bytes(_WithAlias.TRADES)


def test_capability_entry_distinguishes_presence_and_tier() -> None:
    observed = CapabilityEntry(present=True, tier=ProvenanceTier.OBSERVED)
    inferred = CapabilityEntry(present=True, tier=ProvenanceTier.INFERRED)
    absent = CapabilityEntry(present=False, tier=None)
    forms = {canonical_bytes(entry) for entry in (observed, inferred, absent)}
    assert len(forms) == 3


def test_capability_record_order_does_not_reach_the_canonical_form() -> None:
    entry = CapabilityEntry(present=True, tier=ProvenanceTier.OBSERVED)
    other = CapabilityEntry(present=False, tier=None)
    forward = CapabilityRecord(((DataRequirement.TRADES, entry), (DataRequirement.MBO, other)))
    backward = CapabilityRecord(((DataRequirement.MBO, other), (DataRequirement.TRADES, entry)))
    assert canonical_bytes(forward) == canonical_bytes(backward)


def test_an_empty_record_is_not_an_empty_sequence_or_map() -> None:
    forms = {
        canonical_bytes(CapabilityRecord(())),
        canonical_bytes([]),
        canonical_bytes({}),
        canonical_bytes(DataRequirement(0)),
    }
    assert len(forms) == 4


# --------------------------------------------------------------------------
# Identifier canonicalization
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "expected", "_digest"), IDENTIFIER_VECTORS)
def test_identifier_canonical_bytes_match_pinned_vectors(
    value: object, expected: bytes, _digest: str
) -> None:
    assert canonical_bytes(value) == expected


@pytest.mark.parametrize(("value", "_expected", "digest"), IDENTIFIER_VECTORS)
def test_identifier_content_hash_matches_pinned_vectors(
    value: object, _expected: bytes, digest: str
) -> None:
    assert content_hash(value) == digest


def test_five_values_holding_three_are_five_distinct_canonical_forms() -> None:
    """3, InstrumentId(3), ProvenanceId(3), "3" and RunId("3") never conflate."""
    values: list[object] = [3, InstrumentId(3), ProvenanceId(3), "3", RunId("3")]
    assert len({canonical_bytes(value) for value in values}) == 5
    assert len({content_hash(value) for value in values}) == 5


@pytest.mark.parametrize("number", [0, 1, 3, -1, INT32_MIN, INT32_MAX])
def test_an_index_identifier_is_never_its_raw_integer(number: int) -> None:
    assert canonical_bytes(InstrumentId(number)) != canonical_bytes(number)
    assert canonical_bytes(ProvenanceId(number)) != canonical_bytes(number)
    assert content_hash(InstrumentId(number)) != content_hash(number)
    assert content_hash(ProvenanceId(number)) != content_hash(number)


@pytest.mark.parametrize("number", [0, 1, 3, -1, INT32_MIN, INT32_MAX])
def test_instrument_and_provenance_indices_never_share_a_canonical_form(
    number: int,
) -> None:
    assert canonical_bytes(InstrumentId(number)) != canonical_bytes(ProvenanceId(number))
    assert content_hash(InstrumentId(number)) != content_hash(ProvenanceId(number))


@pytest.mark.parametrize("text", ["3", "abc", "", "Run-A"])
def test_a_run_id_is_never_its_raw_string(text: str) -> None:
    if text:
        assert canonical_bytes(RunId(text)) != canonical_bytes(text)
        assert content_hash(RunId(text)) != content_hash(text)
    else:
        with pytest.raises(InvalidIdentifierError):
            RunId(text)


def test_identifier_canonicalization_is_deterministic() -> None:
    for value in (RunId("r1"), InstrumentId(7), ProvenanceId(3)):
        assert canonical_bytes(value) == canonical_bytes(value)
        assert content_hash(value) == content_hash(value)


def test_identifiers_nest_inside_containers() -> None:
    payload = {
        "run": RunId("r1"),
        "instrument": InstrumentId(7),
        "provenance": [ProvenanceId(0), ProvenanceId(1)],
    }
    assert canonical_bytes(payload) == (
        b'["map",[["instrument",["instrument_id",7]],'
        b'["provenance",["seq",[["provenance_id",0],["provenance_id",1]]]],'
        b'["run",["run_id","r1"]]]]'
    )


def test_identifier_canonical_form_reflects_the_run_id_case() -> None:
    """RunId does not normalize, so neither does its canonical form."""
    assert canonical_bytes(RunId("Run-A")) != canonical_bytes(RunId("run-a"))


def test_an_invalid_run_id_can_never_reach_the_canonicalizer() -> None:
    """Validation is at construction, so there is no unsafe value to serialize."""
    for bad in ("", ".", "..", "a/b", "a b", "a\x00b"):
        with pytest.raises(InvalidIdentifierError):
            canonical_bytes(RunId(bad))


@pytest.mark.parametrize(("value", "_expected", "_digest"), IDENTIFIER_VECTORS)
def test_identifier_vectors_are_valid_json(value: object, _expected: bytes, _digest: str) -> None:
    parsed = json.loads(canonical_bytes(value).decode("ascii"))
    assert isinstance(parsed, list)
    assert isinstance(parsed[0], str)


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
