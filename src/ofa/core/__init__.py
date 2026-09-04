"""Deterministic core primitives.

Only the primitives delivered so far are exported. Time, ids, hashing,
provenance, capability, manifest, and versioning arrive in later Phase 0
steps; protocol declarations arrive after that.
"""

from ofa.core.errors import (
    InexactDatetimeError,
    InvalidTickSizeError,
    NaiveDatetimeError,
    NonUtcDatetimeError,
    OfaError,
    PriceNotOnGridError,
    PriceOverflowError,
    PriceTypeError,
    TimeOverflowError,
    TimeTypeError,
)
from ofa.core.money import INT64_MAX, INT64_MIN, PRICE_SCALE, Price, TickGrid, Ticks
from ofa.core.time import EPOCH, NS_PER_MICROSECOND, NS_PER_SECOND, UtcNanos

__all__ = [
    "EPOCH",
    "INT64_MAX",
    "INT64_MIN",
    "NS_PER_MICROSECOND",
    "NS_PER_SECOND",
    "PRICE_SCALE",
    "InexactDatetimeError",
    "InvalidTickSizeError",
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
    "UtcNanos",
]
