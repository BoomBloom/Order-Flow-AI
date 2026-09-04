"""Canonical serialization and stable content hashing.

A *content hash* here is a hash of meaning, not of memory. Two values that are
logically equal must produce byte-identical canonical output — and therefore
an identical digest — in different interpreter processes, on different
machines, and on different days. This is what makes ``params_hash``
reproducible (``docs/architecture.md`` section 6.4 and the section 13 table
row), and it is a Phase 0 exit criterion in its own right
(``docs/roadmap.md``, Phase 0 exit criterion 3).

Nothing here may depend on Python's built-in ``hash()``, on object identity,
on memory addresses, on the per-process hash seed, on ``repr()``, or on the
iteration order of an unordered container. Each of those is deterministic
*within* one process and varies *between* processes, which is precisely the
failure mode that would silently destroy reproducibility.

Why not plain ``json.dumps(obj, sort_keys=True)``
-------------------------------------------------

Because it is ambiguous. Measured on CPython 3.11:

* ``{True: 1}`` and ``{"true": 1}`` both render as ``{"true": 1}``.
* ``{1: "a", "1": "b"}`` renders as ``{"1": "a", "1": "b"}`` — a duplicate key,
  which is not even valid JSON.
* An ``IntEnum`` member renders as its integer; a ``StrEnum`` member renders
  as its string. Both collide with the raw value.
* A tuple and a list are indistinguishable.
* ``float("nan")`` renders as ``NaN`` by default, which is not valid JSON.

So every value is wrapped in a **type tag** before rendering. The tag is what
removes the ambiguity; JSON is only the rendering. Each canonical node is a
JSON array whose first element names the type::

    None                  ["none"]
    True                  ["bool",true]
    5                     ["int",5]
    "abc"                 ["str","abc"]
    b"\\x01\\xff"           ["bytes","01ff"]
    [a, b] / (a, b)       ["seq",[<a>,<b>]]
    {"b": 1, "a": 2}      ["map",[["a",<2>],["b",<1>]]]
    Side.BUY              ["enum","pkg.mod","Side","BUY"]
    Reqs.TRADES|Reqs.BBO  ["flag","pkg.mod","Reqs",["BBO","TRADES"]]
    Price(1500000000)     ["price",1500000000]
    Ticks(-6)             ["ticks",-6]
    UtcNanos(-1)          ["utc_nanos",-1]
    TradeDate(2024,3,11)  ["trade_date","2024-03-11"]
    RunId("abc")          ["run_id","abc"]
    InstrumentId(7)       ["instrument_id",7]
    ProvenanceId(3)       ["provenance_id",3]
    CapabilityEntry(...)  ["capability_entry",true,["enum",…,"OBSERVED"]]
    CapabilityRecord(...) ["capability_record",[[<flag>,<entry>],…]]

The supported set is **closed**. Anything not listed above raises rather than
being canonicalized on a guess. New tags may be added later; because a tag is
only ever added, never redefined, doing so cannot change any digest produced
today.

Deliberately absent, and asserted absent by tests:

* **Floats.** ``0.0 == -0.0`` while their bytes differ, and ``NaN != NaN``, so
  a float cannot carry a stable identity. There is no opt-in mode. This
  matches ``money.py`` and ``time.py``, which reject floats outright.
* **Sets.** A set has no order, any imposed order needs a total order the
  elements may not have, and Python collapses ``{1, True}`` to ``{1}`` — so a
  set cannot faithfully describe its own contents. Pass a sorted tuple.
* **Arbitrary dataclasses and objects.** Two different classes with identical
  fields would hash identically, which is the exact collision this module
  exists to prevent. Support arrives with a concrete parameter type.
* **Unicode normalization.** Normalizing is a lossy transform, and this
  project rejects rather than transforms. NFC and NFD spellings of the same
  glyph are different strings and hash differently.
* **Re-hashing or truncation.** A digest is the full 64-character lowercase
  SHA-256 hex, always.

The canonical form is expensive to change: once a digest is stored, altering a
tag, the key ordering, the separators, the encoding, or the prefix invalidates
it. That is why the hashed bytes carry ``CANONICAL_FORMAT_VERSION`` — a future
change bumps the version, making every digest change deliberately and
visibly rather than silently.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum, Flag
from typing import Final

from ofa.core.capability import CapabilityEntry, CapabilityRecord
from ofa.core.errors import CanonicalTypeError, CanonicalValueError
from ofa.core.ids import InstrumentId, ProvenanceId, RunId
from ofa.core.money import Price, Ticks
from ofa.core.time import TradeDate, UtcNanos

#: Version of the canonical serialization contract. It is hashed ahead of the
#: canonical bytes, so changing the contract changes every digest deliberately
#: instead of silently invalidating stored identities.
CANONICAL_FORMAT_VERSION: Final = "ofa-canon-1"

#: The version prefix as hashed bytes. The NUL terminator keeps the version
#: from running into the canonical bytes that follow it. This also separates
#: our digests from a plain SHA-256 of file contents, which the acquisition
#: manifests use for ``raw_sha256``.
_FORMAT_PREFIX: Final = CANONICAL_FORMAT_VERSION.encode("ascii") + b"\x00"

#: Compact JSON separators. The defaults insert spaces; any drift here changes
#: every digest, so they are pinned rather than left implicit.
_SEPARATORS: Final = (",", ":")

#: Maximum nesting depth. A structure deeper than this raises a clean error
#: rather than exhausting the interpreter stack, and it bounds the recursion
#: for any self-referential structure that reached us.
#:
#: Private on purpose: this is an implementation safety limit, not a domain
#: primitive and not configuration. Nothing outside this module depends on its
#: value, and raising or lowering it changes no canonical output.
_MAX_CANONICAL_DEPTH: Final = 32

# A canonical node is a JSON array whose first element is its type tag. bool is
# a subtype of int, so int covers it.
_Canonical = str | int | list["_Canonical"]


def _encodable_str(value: str, what: str) -> str:
    """Return ``value`` if it can be represented in the canonical encoding.

    ``json.dumps`` accepts a lone surrogate and escapes it happily, but the
    result cannot be encoded as UTF-8. Checking here means the failure is a
    clear domain error at the offending value rather than a ``UnicodeError``
    from deep inside the renderer.
    """
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalValueError(
            f"{what} contains characters that cannot be encoded as UTF-8 "
            f"(a lone surrogate, most likely) and has no canonical form: {exc}"
        ) from exc
    return value


def _member_name(member: Enum, what: str) -> str:
    """Return an enum member's name, refusing an unnamed one.

    ``Enum.name`` is ``None`` for a flag value that names no member — most
    obviously the empty flag. Reaching the encoder with ``None`` would raise a
    bare ``AttributeError``, escaping the error contract every other path in
    this module keeps, so it is caught here instead.
    """
    name = member.name
    if name is None:
        raise CanonicalValueError(
            f"{what} has no member name and no canonical form; it is an unnamed "
            f"value of {type(member).__qualname__}"
        )
    return _encodable_str(name, what)


def _canonicalize_flag(value: Flag) -> _Canonical:
    """Canonicalize a flag as the sorted names of the members it contains.

    A flag is a *set* of capabilities, so its canonical form is a set: the
    members it decomposes into, sorted by name. Two things follow, and both are
    the reason this path exists rather than reusing the enum tag.

    Declaration order cannot affect the result. ``Flag.name`` for a composite
    is the members joined in *definition* order, so ``TRADES|BBO`` and
    ``BBO|TRADES`` — the same value, from two enums whose members were declared
    in different orders — would hash differently. Reordering a member list is
    the kind of edit a reviewer waves through as cosmetic; it must not move
    every digest that contains a requirement.

    The empty flag canonicalizes as an empty list. Its ``name`` is ``None``,
    which previously reached the encoder and raised ``AttributeError``.

    Aliases collapse correctly for free: a composite alias and the explicit
    union of its parts are the same value, decompose identically, and so
    produce identical bytes.

    A value that does not decompose into its own members is refused. ``IntFlag``
    keeps undeclared bits by default, and those bits are invisible to
    iteration — so a value carrying one would canonicalize as the members it
    does contain, giving two unequal values the same digest.
    """
    cls = type(value)
    names: list[str] = []
    covered = 0
    for member in value:
        names.append(_member_name(member, "flag member name"))
        covered |= member.value
    if covered != value.value:
        # Undeclared bits are invisible to iteration, so a value carrying them
        # would canonicalize as the members it *does* contain — and two unequal
        # values would share a digest. IntFlag keeps such bits by default
        # (boundary=KEEP), which is how DataRequirement(0) and
        # DataRequirement(128) came to look identical.
        raise CanonicalValueError(
            f"{cls.__qualname__} value {value.value} does not decompose into its "
            f"members: the bits {value.value & ~covered} name nothing, so the value "
            f"has no faithful canonical form"
        )
    return [
        "flag",
        _encodable_str(cls.__module__, "flag module"),
        _encodable_str(cls.__qualname__, "flag qualified name"),
        sorted(names),
    ]


def _canonicalize_enum(value: Enum) -> _Canonical:
    """Canonicalize an enum member by identity, never by value.

    The tag carries the defining module, the class qualified name, and the
    member name. Module and qualname together are what keep two identically
    named enum classes in different modules distinguishable. The member *name*
    is the identity: a member's value may be renumbered or restyled without
    changing what it denotes, so hashing the value would make an editorial
    change look like a semantic one — and would collide with the raw ``int``
    or ``str`` besides.

    Renaming or moving an enum class is therefore a hash-breaking change. That
    is intentional: it is a change of identity.
    """
    cls = type(value)
    return [
        "enum",
        _encodable_str(cls.__module__, "enum module"),
        _encodable_str(cls.__qualname__, "enum qualified name"),
        _member_name(value, "enum member name"),
    ]


def _canonicalize_mapping(value: dict[object, object], depth: int) -> _Canonical:
    """Canonicalize a mapping as sorted ``[key, value]`` pairs.

    Keys must be exactly ``str``. Restricting them is what removes the
    ``{True: 1}`` versus ``{"true": 1}`` collision and the duplicate-key
    rendering of ``{1: "a", "1": "b"}``: neither is representable rather than
    silently wrong.

    Keys are sorted by Python's ordering on ``str``, which is Unicode code
    point order. The sorted pair list is built here rather than delegated to
    ``json.dumps(sort_keys=True)``, so ordering is a property of this module
    and cannot be lost by a renderer flag going missing.
    """
    keys: list[str] = []
    for key in value:
        if isinstance(key, bool) or not isinstance(key, str) or type(key) is not str:
            raise CanonicalTypeError(
                f"mapping keys must be exactly str, not {type(key).__name__}; "
                f"a non-string key has no unambiguous canonical form"
            )
        keys.append(_encodable_str(key, "mapping key"))
    return ["map", [[key, _canonicalize(value[key], depth + 1)] for key in sorted(keys)]]


def _canonicalize(value: object, depth: int) -> _Canonical:
    """Return the tagged canonical node for ``value``.

    Dispatch order is load-bearing. ``bool`` is checked before ``int`` because
    it is a subclass of it, and ``Enum`` is checked before both ``int`` and
    ``str`` because ``IntEnum`` and ``StrEnum`` are subclasses of those. After
    that, types are matched **exactly**: a subclass is rejected rather than
    canonicalized as its base, because a subclass carries an identity the base
    tag would silently discard — a ``NamedTuple`` is not a plain sequence, and
    an ``int`` subclass is not a plain integer.
    """
    if depth > _MAX_CANONICAL_DEPTH:
        raise CanonicalValueError(
            f"value is nested deeper than the canonical limit of {_MAX_CANONICAL_DEPTH}; "
            f"a structure this deep is more likely a cycle than a parameter set"
        )

    if value is None:
        return ["none"]

    # Before int: bool is a subclass of int, and True would otherwise be 1.
    if isinstance(value, bool):
        return ["bool", value]

    # Before Enum: a Flag is a set of members, not one member, and its own
    # tag is what makes it insensitive to declaration order and able to express
    # the empty value. Plain enums — including IntEnum and StrEnum — are not
    # Flags and keep the enum tag exactly as before.
    if isinstance(value, Flag):
        return _canonicalize_flag(value)

    # Before int and str: IntEnum and StrEnum are subclasses of those, and
    # would otherwise collide with the raw value they happen to carry.
    if isinstance(value, Enum):
        return _canonicalize_enum(value)

    # Before int and str. These are not subclasses of their payload types
    # today, so the order is not strictly required — it is here so that an
    # identifier can never be canonicalized as a bare number or a bare string
    # even if one of them were ever reshaped. The distinct tags are what keep
    # 3, InstrumentId(3), ProvenanceId(3), "3" and RunId("3") five different
    # values.
    if type(value) is RunId:
        return ["run_id", _encodable_str(value.value, "RunId.value")]

    if type(value) is InstrumentId:
        return ["instrument_id", value.value]

    if type(value) is ProvenanceId:
        return ["provenance_id", value.value]

    if isinstance(value, int):
        if type(value) is not int:
            raise CanonicalTypeError(
                f"{type(value).__name__} is an int subclass and has no canonical form; "
                f"canonicalizing it as a plain int would discard its identity"
            )
        return ["int", value]

    if isinstance(value, str):
        if type(value) is not str:
            raise CanonicalTypeError(
                f"{type(value).__name__} is a str subclass and has no canonical form; "
                f"canonicalizing it as a plain str would discard its identity"
            )
        return ["str", _encodable_str(value, "string")]

    if isinstance(value, bytes):
        if type(value) is not bytes:
            raise CanonicalTypeError(
                f"{type(value).__name__} is a bytes subclass and has no canonical form"
            )
        return ["bytes", value.hex()]

    if isinstance(value, (list, tuple)):
        if type(value) is not list and type(value) is not tuple:
            raise CanonicalTypeError(
                f"{type(value).__name__} is a list or tuple subclass and has no canonical "
                f"form; a named tuple in particular carries field names that the plain "
                f"sequence tag would discard"
            )
        # list and tuple share one tag on purpose: the canonical form describes
        # logical sequence content, and the Python container choice carries no
        # domain meaning. Changing a literal from a list to a tuple must not
        # change an identity.
        return ["seq", [_canonicalize(item, depth + 1) for item in value]]

    if isinstance(value, dict):
        if type(value) is not dict:
            raise CanonicalTypeError(
                f"{type(value).__name__} is a dict subclass and has no canonical form; "
                f"its ordering or default behaviour is not part of the contract"
            )
        return _canonicalize_mapping(value, depth)

    if type(value) is Price:
        return ["price", value.nanounits]

    if type(value) is Ticks:
        return ["ticks", value.count]

    if type(value) is UtcNanos:
        return ["utc_nanos", value.nanos]

    if type(value) is CapabilityEntry:
        return [
            "capability_entry",
            value.present,
            ["none"] if value.tier is None else _canonicalize_enum(value.tier),
        ]

    if type(value) is CapabilityRecord:
        return [
            "capability_record",
            [
                [_canonicalize_flag(capability), _canonicalize(entry, depth + 1)]
                for capability, entry in value.entries
            ],
        ]

    if type(value) is TradeDate:
        # isoformat() is already the type's canonical string form: zero-padded,
        # locale-independent, and produced by the standard library.
        return ["trade_date", value.isoformat()]

    if isinstance(value, float):
        raise CanonicalTypeError(
            "float has no canonical form and is never permitted: 0.0 and -0.0 compare "
            "equal while their bytes differ, and NaN is not equal to itself, so a float "
            "cannot carry a stable identity"
        )

    if isinstance(value, (set, frozenset)):
        raise CanonicalTypeError(
            f"{type(value).__name__} has no canonical form: a set has no order, imposing "
            f"one requires a total order its elements may not have, and Python collapses "
            f"{{1, True}} to {{1}}. Pass a sorted tuple instead"
        )

    raise CanonicalTypeError(
        f"{type(value).__name__} is not a supported canonical type. Supported: None, "
        f"bool, int, str, bytes, list, tuple, dict with str keys, Enum, Price, Ticks, "
        f"UtcNanos, TradeDate, RunId, InstrumentId, ProvenanceId, CapabilityEntry, "
        f"CapabilityRecord"
    )


def canonical_bytes(value: object) -> bytes:
    """Return the canonical byte representation of ``value``.

    The result is pure ASCII: non-ASCII characters are escaped by the renderer,
    so the bytes are identical under any UTF-8 encoder and there is no locale
    or codec variance to reason about. The declared encoding is UTF-8, of which
    this is a subset.

    This is *not* a JSON serialization of ``value`` — it is compact JSON of a
    tagged encoding of ``value``, and parsing it will not give ``value`` back.
    It exists to be hashed and, when two digests disagree, to be diffed.

    Raises ``CanonicalTypeError`` for an unsupported type and
    ``CanonicalValueError`` for a supported type holding an uncanonicalizable
    value.
    """
    node = _canonicalize(value, depth=0)
    text = json.dumps(
        node,
        ensure_ascii=True,
        allow_nan=False,
        check_circular=True,
        separators=_SEPARATORS,
        # Ordering is built into the node by _canonicalize_mapping. Delegating
        # it here would mean a lost flag silently changes every digest.
        sort_keys=False,
    )
    return text.encode("ascii")


def content_hash(value: object) -> str:
    """Return the stable content hash of ``value`` as 64 lowercase hex digits.

    SHA-256 from the standard library, over the format version prefix followed
    by the canonical bytes. The full digest is returned; it is never truncated,
    so no birthday bound has to be argued about later. Lowercase is fixed
    because these digests end up in filenames, and two filesystems in common
    use are case-insensitive.
    """
    return hashlib.sha256(_FORMAT_PREFIX + canonical_bytes(value)).hexdigest()


def params_hash(params: dict[str, object]) -> str:
    """Return the stable content hash of a parameter set.

    This is a named restriction of :func:`content_hash`, not a second hash:
    for the same mapping the two return the same digest, because they are the
    same computation. It exists to constrain the input at the signature — a
    parameter set is always a string-keyed mapping — and to give the call site
    the vocabulary ``docs/architecture.md`` uses.

    It hashes the parameters only. A feature's name and version are carried
    literally in its identifier, so folding them in here would make the hash
    move for reasons already visible elsewhere.
    """
    if type(params) is not dict:
        raise CanonicalTypeError(
            f"params must be a dict with str keys, not {type(params).__name__}"
        )
    return content_hash(params)
