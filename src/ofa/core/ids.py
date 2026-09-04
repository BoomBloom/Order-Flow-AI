"""Identifier value types.

Three identifiers appear in the stored data contract, and they are three
genuinely different kinds of thing. Treating them uniformly — or as bare
``str`` and ``int`` — is how a run identifier ends up compared against an
instrument index, so each gets its own type.

* ``RunId`` names one immutable run and its artifact directory,
  ``data/runs/<run_id>/`` (``docs/data_specification.md`` section 9). It is an
  opaque token, **not** derived from content: ``CLAUDE.md`` states that
  re-running produces a *new* run id, so a hash of the same configuration —
  which would repeat — cannot be it.
* ``InstrumentId`` is the ``int32`` instrument key carried on every canonical
  event, "resolved from the instrument registry"
  (``docs/data_specification.md`` section 5).
* ``ProvenanceId`` is an ``int32`` "index into the run manifest" (same
  section). It is **scoped to that manifest** — see its docstring.

**Core never mints an identifier.** Minting a run id needs a clock or an
entropy source, and neither belongs here: ``time.py`` already refuses a
wall-clock read because it would destroy replay determinism, and the same
reasoning applies to randomness. These types validate a value someone else
produced. The layer that owns the run lifecycle owns the minting.

Deliberately absent, and asserted absent by tests:

* generation of any kind — no ``new``, ``mint``, ``generate``, ``create`` or
  ``now``, no UUIDs, no randomness, no timestamps.
* ordering. An identifier is a label, not a magnitude: instrument 5 is not
  "less than" instrument 7 in any domain sense, and the lexical order of two
  opaque tokens means nothing. Sorting a collection of identifiers is done by
  an explicit key at the call site, where the intent is visible.
* arithmetic, and implicit conversion to ``str`` or ``int``. An identifier
  that silently behaves as its payload is the confusion these types exist to
  prevent.
* normalization. A value is preserved exactly or rejected, never folded,
  trimmed or case-changed — the same discipline as an off-grid price, which
  raises rather than rounding.
* parsing, formatting and filesystem helpers. Building a path from a run id
  belongs to the layer that owns the store.

The alphabet and maximum length a run id may use are **deliberately not fixed
here.** What is enforced is only what safety requires: a run id must be
non-empty and usable as a single path component. The rest is run-lifecycle
policy, and freezing it before that code exists would be guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ofa.core.errors import IdentifierTypeError, InvalidIdentifierError

#: Inclusive bounds of the signed 32-bit range. ``instrument_id`` and
#: ``provenance_id`` are ``int32`` in the canonical event envelope
#: (``docs/data_specification.md`` section 5), so a value that could not
#: round-trip through storage fails where it is created.
INT32_MIN: Final = -(2**31)
INT32_MAX: Final = 2**31 - 1

#: Both separators are rejected regardless of host platform. A name created on
#: one operating system is read on another, so a backslash is a hazard on a
#: POSIX machine exactly as a forward slash is on Windows.
_PATH_SEPARATORS: Final = ("/", "\\")

#: The two relative-path names. Either would make ``data/runs/<run_id>/``
#: resolve somewhere other than a child directory.
_RESERVED_PATH_NAMES: Final = (".", "..")


def _exact_int(value: object, what: str) -> int:
    """Return ``value`` as an ``int``, rejecting every other type.

    ``bool`` is rejected explicitly even though it is a subclass of ``int``:
    ``InstrumentId(True)`` would otherwise silently mean instrument 1. Other
    subclasses are rejected too, so an ``IntEnum`` member cannot become an
    instrument index by carrying the right number.

    This is deliberately stricter than the integer checks in ``money.py`` and
    ``time.py``, which predate the canonicalizer's exact-type dispatch. Those
    modules are not being changed to match; the two rules are documented rather
    than silently different.
    """
    if isinstance(value, bool):
        raise IdentifierTypeError(f"{what} must be an int, not bool")
    if not isinstance(value, int):
        raise IdentifierTypeError(
            f"{what} must be an int, not {type(value).__name__}; "
            f"floats and strings are never coerced to an identifier"
        )
    if type(value) is not int:
        raise IdentifierTypeError(
            f"{what} must be exactly an int, not the subclass {type(value).__name__}"
        )
    return value


def _in_int32(value: int, what: str) -> int:
    """Return ``value`` if it fits the signed 32-bit range, else raise."""
    if value < INT32_MIN or value > INT32_MAX:
        raise InvalidIdentifierError(
            f"{what} is outside the signed 32-bit range [{INT32_MIN}, {INT32_MAX}]: {value}"
        )
    return value


def _exact_str(value: object, what: str) -> str:
    """Return ``value`` as a ``str``, rejecting every other type.

    A subclass is rejected too. A ``StrEnum`` member compares equal to its
    string and would slip through, leaving an identifier whose payload is not
    actually a ``str`` — and the canonical form is built on exact types.
    """
    if not isinstance(value, str):
        raise IdentifierTypeError(f"{what} must be a str, not {type(value).__name__}")
    if type(value) is not str:
        raise IdentifierTypeError(
            f"{what} must be exactly a str, not the subclass {type(value).__name__}"
        )
    return value


@dataclass(frozen=True, slots=True)
class RunId:
    """An opaque identifier for one immutable run.

    The value is whatever the run lifecycle assigned. This type does not
    interpret it, does not normalize it, and cannot produce one: it checks
    that the token is safe to use as a single path component and stores it
    unchanged.

    Validation is only what safety requires. The value must be a non-empty
    ``str``; it must not contain a path separator, a whitespace character or a
    control character; it must not be ``.`` or ``..``; and it must be encodable
    as UTF-8, which rejects a lone surrogate that no filesystem or manifest
    could carry. Case is preserved because nothing here changes the value —
    ``RunId("Run-A")`` keeps its capitals and is a different identifier from
    ``RunId("run-a")``.

    **Scope of this guarantee.** ``RunId`` currently guarantees basic
    single-path-component safety only. Platform-specific filesystem naming
    restrictions — a Windows drive or alternate-stream colon, the reserved
    device names ``CON``, ``NUL``, ``COM1`` and their siblings, per-filesystem
    length limits — and the final run-id grammar remain a later lifecycle and
    storage decision. The permitted alphabet and any maximum length are fixed
    by the code that mints run ids, not by the type that carries them.

    Equality is by value and there is no ordering: two run ids are the same run
    or they are not, and neither comes "before" the other.
    """

    value: str

    def __post_init__(self) -> None:
        text = _exact_str(self.value, "RunId.value")
        if not text:
            raise InvalidIdentifierError("RunId.value must not be empty")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidIdentifierError(
                f"RunId.value contains characters that cannot be encoded as UTF-8 "
                f"(a lone surrogate, most likely): {exc}"
            ) from exc
        if text in _RESERVED_PATH_NAMES:
            raise InvalidIdentifierError(
                f"RunId.value must not be {text!r}: it names a relative path rather "
                f"than a directory"
            )
        for separator in _PATH_SEPARATORS:
            if separator in text:
                raise InvalidIdentifierError(
                    f"RunId.value must be a single path component and must not contain "
                    f"{separator!r}: {text!r}"
                )
        for position, character in enumerate(text):
            if character.isspace():
                raise InvalidIdentifierError(
                    f"RunId.value must not contain whitespace; found {character!r} at "
                    f"position {position} of {text!r}"
                )
            if ord(character) < 0x20 or ord(character) == 0x7F:
                raise InvalidIdentifierError(
                    f"RunId.value must not contain a control character; found "
                    f"U+{ord(character):04X} at position {position}"
                )


@dataclass(frozen=True, slots=True)
class InstrumentId:
    """The internal ``int32`` key for one instrument.

    Assigned by the instrument registry in the reference layer, which does not
    exist yet: this type carries the answer and never computes it. There is no
    registry lookup, no symbol resolution and no minting here.

    Equality is by value and there is no ordering. The number is a dense index,
    so comparing two of them has no domain meaning even though comparing the
    underlying integers would succeed.

    An ``InstrumentId`` never compares equal to a ``ProvenanceId`` holding the
    same number, which is the point of having two types over one ``int32``.
    """

    value: int

    def __post_init__(self) -> None:
        _in_int32(_exact_int(self.value, "InstrumentId.value"), "InstrumentId.value")


@dataclass(frozen=True, slots=True)
class ProvenanceId:
    """An ``int32`` index into **one** run manifest's provenance table.

    This is the semantic that is easy to get wrong, so it is stated plainly:
    a ``ProvenanceId`` is **manifest-scoped and not globally meaningful.**
    ``docs/data_specification.md`` section 5 defines ``provenance_id`` as an
    "index into the run manifest: vendor, dataset, transformation version,
    per-field tiers". Index 3 of one manifest and index 3 of another describe
    different vendors, datasets and tiers.

    Consequently ``ProvenanceId(3) == ProvenanceId(3)`` means "the same index",
    never "the same provenance". Two provenance records are the same only when
    their manifests agree, which is a question for the layer that holds the
    manifests — there is no lookup here, and none may be added.

    A content hash containing a ``ProvenanceId`` therefore hashes an index, not
    a provenance. Anything that must hash provenance hashes the manifest
    record.

    Equality is by value and there is no ordering, for the same reason as
    ``InstrumentId``: the number is a position in a table, not a magnitude.
    """

    value: int

    def __post_init__(self) -> None:
        _in_int32(_exact_int(self.value, "ProvenanceId.value"), "ProvenanceId.value")
