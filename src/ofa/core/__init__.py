"""Deterministic core primitives.

Only the primitives delivered so far are exported. The dataset manifest is
Phase 1 work, and the CanonicalEvent and Feature protocol declarations await
their own architecture gate.
"""

from ofa.core.capability import CapabilityEntry, CapabilityRecord, DataRequirement
from ofa.core.errors import (
    CanonicalTypeError,
    CanonicalValueError,
    CapabilityTypeError,
    IdentifierTypeError,
    IncomparableProvenanceError,
    InexactDatetimeError,
    InvalidCapabilityError,
    InvalidCodeRevisionError,
    InvalidIdentifierError,
    InvalidTickSizeError,
    InvalidTradeDateError,
    NaiveDatetimeError,
    NonUtcDatetimeError,
    OfaError,
    PriceNotOnGridError,
    PriceOverflowError,
    PriceTypeError,
    ProvenanceTypeError,
    TimeOverflowError,
    TimeTypeError,
    VersioningTypeError,
)
from ofa.core.hashing import (
    CANONICAL_FORMAT_VERSION,
    canonical_bytes,
    content_hash,
    params_hash,
)
from ofa.core.ids import INT32_MAX, INT32_MIN, InstrumentId, ProvenanceId, RunId
from ofa.core.lifecycle import ResetReason, RollPolicy
from ofa.core.money import INT64_MAX, INT64_MIN, PRICE_SCALE, Price, TickGrid, Ticks
from ofa.core.provenance import ProvenanceTier
from ofa.core.time import EPOCH, NS_PER_MICROSECOND, NS_PER_SECOND, TradeDate, UtcNanos
from ofa.core.versioning import (
    SCHEMA_VERSIONS,
    CodeRevision,
    RevisionState,
    render_version_report,
    resolve_code_revision,
    version_report,
)

__all__ = [
    "CANONICAL_FORMAT_VERSION",
    "EPOCH",
    "INT32_MAX",
    "INT32_MIN",
    "INT64_MAX",
    "INT64_MIN",
    "NS_PER_MICROSECOND",
    "NS_PER_SECOND",
    "PRICE_SCALE",
    "SCHEMA_VERSIONS",
    "CanonicalTypeError",
    "CanonicalValueError",
    "CapabilityEntry",
    "CapabilityRecord",
    "CapabilityTypeError",
    "CodeRevision",
    "DataRequirement",
    "IdentifierTypeError",
    "IncomparableProvenanceError",
    "InexactDatetimeError",
    "InstrumentId",
    "InvalidCapabilityError",
    "InvalidCodeRevisionError",
    "InvalidIdentifierError",
    "InvalidTickSizeError",
    "InvalidTradeDateError",
    "NaiveDatetimeError",
    "NonUtcDatetimeError",
    "OfaError",
    "Price",
    "PriceNotOnGridError",
    "PriceOverflowError",
    "PriceTypeError",
    "ProvenanceId",
    "ProvenanceTier",
    "ProvenanceTypeError",
    "ResetReason",
    "RevisionState",
    "RollPolicy",
    "RunId",
    "TickGrid",
    "Ticks",
    "TimeOverflowError",
    "TimeTypeError",
    "TradeDate",
    "UtcNanos",
    "VersioningTypeError",
    "canonical_bytes",
    "content_hash",
    "params_hash",
    "render_version_report",
    "resolve_code_revision",
    "version_report",
]
