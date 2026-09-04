"""Deterministic core primitives.

Only the primitives delivered so far are exported. Ids, provenance,
capability, manifest, and versioning arrive in later Phase 0 steps; protocol
declarations arrive after that.
"""

from ofa.core.errors import (
    CanonicalTypeError,
    CanonicalValueError,
    InexactDatetimeError,
    InvalidTickSizeError,
    InvalidTradeDateError,
    NaiveDatetimeError,
    NonUtcDatetimeError,
    OfaError,
    PriceNotOnGridError,
    PriceOverflowError,
    PriceTypeError,
    TimeOverflowError,
    TimeTypeError,
)
from ofa.core.hashing import (
    CANONICAL_FORMAT_VERSION,
    canonical_bytes,
    content_hash,
    params_hash,
)
from ofa.core.money import INT64_MAX, INT64_MIN, PRICE_SCALE, Price, TickGrid, Ticks
from ofa.core.time import EPOCH, NS_PER_MICROSECOND, NS_PER_SECOND, TradeDate, UtcNanos

__all__ = [
    "CANONICAL_FORMAT_VERSION",
    "EPOCH",
    "INT64_MAX",
    "INT64_MIN",
    "NS_PER_MICROSECOND",
    "NS_PER_SECOND",
    "PRICE_SCALE",
    "CanonicalTypeError",
    "CanonicalValueError",
    "InexactDatetimeError",
    "InvalidTickSizeError",
    "InvalidTradeDateError",
    "NaiveDatetimeError",
    "NonUtcDatetimeError",
    "OfaError",
    "Price",
    "PriceNotOnGridError",
    "PriceOverflowError",
    "PriceTypeError",
    "TickGrid",
    "Ticks",
    "TimeOverflowError",
    "TimeTypeError",
    "TradeDate",
    "UtcNanos",
    "canonical_bytes",
    "content_hash",
    "params_hash",
]
