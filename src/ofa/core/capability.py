"""What a partition actually contains, and how good it is.

``docs/data_specification.md`` section 3 states the rule this module exists to
carry: **capability is not a static property of a vendor.** It varies by
partition. Aggressor flags can be present on most days and absent on some;
MBP-10 depth can truncate during bursts; ``ts_recv`` can be present in one
dataset vintage and absent in another. So capability is recorded per
partition, and a run asserts its features' declared requirements against that
record rather than against a vendor's brochure.

``DataRequirement`` is what a feature asks for. ``CapabilityRecord`` is what a
partition supplies. :meth:`CapabilityRecord.unmet` is the question between
them, and it answers with the requirements that were *not* met rather than a
bare boolean, so a caller can say which feed was missing.

Deliberately absent
-------------------

**The per-capability quality statistics are not modelled yet.** Section 3's
example carries ``unknown_share``, ``truncation_events``,
``assumed_feed_delay_ns`` and ``assumption_source`` alongside presence and
tier. They are omitted here for three separate reasons, and all three would
have to be resolved to add them:

* ``unknown_share`` is written as ``0.003`` — a float. Floats are forbidden in
  exact paths and rejected outright by the canonical form, so representing a
  ratio exactly (parts per million as an integer? a rational?) is an open
  decision, not an implementation detail.
* ``truncation_events`` is produced by the L1a raw quality layer and
  ``unknown_share`` by L1b. Neither layer exists.
* ``assumed_feed_delay_ns`` and ``assumption_source`` come from run
  configuration, not from the data.

**No I/O, no parsing, no manifest.** This module holds the value types. The
full dataset manifest — vendor request shapes, retrieval timestamps, dataset
ids, session definitions — is Phase 1 work, where the vendor is known and
Pydantic is legitimately available at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import STRICT, IntFlag

from ofa.core.errors import CapabilityTypeError, InvalidCapabilityError
from ofa.core.provenance import ProvenanceTier


class DataRequirement(IntFlag, boundary=STRICT):
    """The data a feature requires, or that a partition supplies.

    The member set is fixed by ``docs/data_specification.md`` section 3's
    capability record. A flag rather than a plain enum because requirements
    compose: ``docs/architecture.md`` section 6.1 declares
    ``requires: DataRequirement  # e.g. TRADES | BBO | MBP_10 | MBO``.

    Coverage is the ordinary subset test, ``(required & available) ==
    required``. The empty requirement is ``DataRequirement(0)``; no zero member
    is declared, because "requires nothing" is an absence rather than a
    capability.

    The integer values are stable but incidental. The canonical form hashes
    the sorted *names* of the members a value decomposes into, so a value is
    never persisted as a bitmask and renumbering could not silently
    reinterpret stored data.

    The boundary is ``STRICT`` rather than ``IntFlag``'s default of ``KEEP``.
    Under ``KEEP`` an undeclared bit is retained silently but is invisible to
    iteration, so ``DataRequirement(128)`` would hold a capability that nothing
    can name and would canonicalize exactly like ``DataRequirement(0)``. Here it
    raises instead.
    """

    TRADES = 1
    AGGRESSOR = 2
    BBO = 4
    MBP_10 = 8
    MBO = 16
    TS_RECV = 32
    STATUS = 64


def _single_capability(value: object, what: str) -> DataRequirement:
    """Return ``value`` if it names exactly one capability, else raise."""
    if not isinstance(value, DataRequirement):
        raise CapabilityTypeError(f"{what} must be a DataRequirement, not {type(value).__name__}")
    members = tuple(value)
    if len(members) != 1:
        raise InvalidCapabilityError(
            f"{what} must name exactly one capability, not {len(members)} "
            f"({value!r}); a record is keyed by single capabilities so that each "
            f"one carries its own presence and tier"
        )
    return value


@dataclass(frozen=True, slots=True)
class CapabilityEntry:
    """Whether one capability is present in a partition, and at what tier.

    The two fields are bound together by an invariant taken straight from the
    specification's example: a present capability has a tier, and an absent one
    has none. ``{"present": true, "tier": null}`` would claim data of unknown
    quality, and ``{"present": false, "tier": "OBSERVED"}`` would claim quality
    for data that is not there. Both raise.

    ``present`` must be an actual ``bool``. ``0`` and ``1`` are rejected so
    that presence cannot be smuggled in as a number, the mirror of the rule
    that keeps ``bool`` out of the integer primitives.
    """

    present: bool
    tier: ProvenanceTier | None

    def __post_init__(self) -> None:
        if type(self.present) is not bool:
            raise CapabilityTypeError(
                f"CapabilityEntry.present must be a bool, not {type(self.present).__name__}"
            )
        if self.tier is not None and not isinstance(self.tier, ProvenanceTier):
            raise CapabilityTypeError(
                f"CapabilityEntry.tier must be a ProvenanceTier or None, not "
                f"{type(self.tier).__name__}"
            )
        if self.present and self.tier is None:
            raise InvalidCapabilityError(
                "a present capability must carry a provenance tier; recording it as "
                "present with no tier would claim data of unknown quality"
            )
        if not self.present and self.tier is not None:
            raise InvalidCapabilityError(
                f"an absent capability must not carry a provenance tier, got "
                f"{self.tier.name}; recording one would claim quality for data that "
                f"is not there"
            )


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    """What one partition actually contains.

    Entries are held as a tuple of ``(capability, entry)`` pairs rather than a
    mapping, so the record is genuinely immutable and hashable. The pairs are
    sorted on construction: only their **order** is normalized, never their
    content, so two records built from the same entries in different orders
    compare equal and canonicalize to identical bytes.

    A capability absent from the record is not the same as one recorded absent.
    The first is unknown — nobody looked — and the second is a measured
    negative. :meth:`unmet` treats both as unmet, but the record preserves the
    distinction for anything that needs it.
    """

    entries: tuple[tuple[DataRequirement, CapabilityEntry], ...]

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple:
            raise CapabilityTypeError(
                f"CapabilityRecord.entries must be a tuple of (capability, entry) "
                f"pairs, not {type(self.entries).__name__}"
            )
        seen: set[DataRequirement] = set()
        for pair in self.entries:
            if type(pair) is not tuple or len(pair) != 2:
                raise CapabilityTypeError(
                    "each CapabilityRecord entry must be a (capability, entry) pair"
                )
            capability = _single_capability(pair[0], "CapabilityRecord key")
            if not isinstance(pair[1], CapabilityEntry):
                raise CapabilityTypeError(
                    f"CapabilityRecord value must be a CapabilityEntry, not "
                    f"{type(pair[1]).__name__}"
                )
            if capability in seen:
                raise InvalidCapabilityError(
                    f"capability {capability.name} appears more than once; a partition "
                    f"has one answer per capability"
                )
            seen.add(capability)
        # Canonical ordering only. The pairs themselves are untouched, so this
        # normalizes how the record is written down and never what it says.
        object.__setattr__(
            self, "entries", tuple(sorted(self.entries, key=lambda pair: pair[0].value))
        )

    def entry(self, capability: DataRequirement) -> CapabilityEntry | None:
        """The entry for one capability, or ``None`` if the record omits it."""
        wanted = _single_capability(capability, "capability")
        for held, entry in self.entries:
            if held is wanted:
                return entry
        return None

    @property
    def present(self) -> DataRequirement:
        """Every capability this partition records as present."""
        available = DataRequirement(0)
        for capability, entry in self.entries:
            if entry.present:
                available |= capability
        return available

    def unmet(self, required: DataRequirement, minimum_tier: ProvenanceTier) -> DataRequirement:
        """Which of ``required`` this partition does not supply at ``minimum_tier``.

        An empty result means the partition satisfies the requirement. A
        capability counts as unmet when it is missing from the record, recorded
        absent, or present at a tier weaker than ``minimum_tier``.

        A capability recorded at ``SIMULATED`` raises
        ``IncomparableProvenanceError`` rather than counting as unmet. Simulated
        output offered as market-data input is a category error, not a thin
        feed, and the two must not be handled by the same branch.

        This is the query behind the specification's ``[ENFORCED]`` rule that
        the store asserts a capability record on read against the declared
        requirement of every feature in the run.
        """
        if not isinstance(required, DataRequirement):
            raise CapabilityTypeError(
                f"required must be a DataRequirement, not {type(required).__name__}"
            )
        if not isinstance(minimum_tier, ProvenanceTier):
            raise CapabilityTypeError(
                f"minimum_tier must be a ProvenanceTier, not {type(minimum_tier).__name__}"
            )
        missing = DataRequirement(0)
        for capability in required:
            entry = self.entry(capability)
            if entry is None or not entry.present or entry.tier is None:
                missing |= capability
            elif not entry.tier.satisfies(minimum_tier):
                missing |= capability
        return missing
