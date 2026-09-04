"""Instants as exact UTC nanoseconds.

This module implements the timestamp half of the locked data contract
(``docs/data_specification.md`` section 1 item 7 and section 6): all internal
timestamps are UTC nanoseconds since the Unix epoch, held as ``int64``. Local
exchange time exists only in session definitions and human-facing output,
neither of which lives here.

``UtcNanos`` is a value, not an identifier. Nanosecond timestamps are **not**
unique in a market-data stream — many events routinely share a ``ts_event`` —
so the canonical ordering key remains ``(ts_event, sequence, ingest_index)``
(``docs/architecture.md`` section 16 item 5).

Floats never enter a time path. ``datetime.timestamp()`` and
``timedelta.total_seconds()`` both return floats and both lose nanoseconds at
market-data magnitudes, so conversion from a datetime uses the integer
``days``/``seconds``/``microseconds`` fields of a ``timedelta`` only.

Deliberately absent, and asserted absent by tests:

* arithmetic. ``UtcNanos - UtcNanos`` is a duration, which is a different
  dimension from an instant, and ``UtcNanos + UtcNanos`` has no meaning. A
  duration type will be introduced when a caller needs one.
* ``now()`` or any other wall-clock read, which would destroy replay
  determinism.
* any conversion to a trading date. A trade date is assigned by the exchange
  calendar in the reference layer (L4), never derived from an instant: a
  Globex session opening Sunday evening belongs to Monday's trade date, and
  daylight-saving shifts move that boundary twice a year.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from ofa.core.errors import (
    NaiveDatetimeError,
    NonUtcDatetimeError,
    TimeOverflowError,
    TimeTypeError,
)

#: Nanoseconds per microsecond, the finest unit a Python ``datetime`` holds.
NS_PER_MICROSECOND: Final = 1_000

#: Nanoseconds per second.
NS_PER_SECOND: Final = 1_000_000_000

#: Seconds per day, used to fold a ``timedelta``'s integer fields together.
_SECONDS_PER_DAY: Final = 86_400

#: Inclusive bounds of the signed 64-bit range. In calendar terms this spans
#: 1677-09-21T00:12:43Z to 2262-04-11T23:47:16Z, which is far wider than any
#: market data we will hold but far narrower than ``datetime``'s own range.
INT64_MIN: Final = -(2**63)
INT64_MAX: Final = 2**63 - 1

#: The Unix epoch as an aware datetime, used as the conversion origin.
EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)


def _exact_int(value: object, what: str) -> int:
    """Return ``value`` as an ``int``, rejecting every other type.

    ``bool`` is rejected explicitly even though it is a subclass of ``int``:
    ``UtcNanos(True)`` would otherwise silently mean one nanosecond past the
    epoch.
    """
    if isinstance(value, bool):
        raise TimeTypeError(f"{what} must be an int, not bool")
    if not isinstance(value, int):
        raise TimeTypeError(
            f"{what} must be an int, not {type(value).__name__}; "
            f"floats are never permitted in a time path"
        )
    return value


def _in_int64(value: int, what: str) -> int:
    """Return ``value`` if it fits the signed 64-bit range, else raise."""
    if value < INT64_MIN or value > INT64_MAX:
        raise TimeOverflowError(
            f"{what} is outside the signed 64-bit nanosecond range "
            f"[{INT64_MIN}, {INT64_MAX}]: {value}"
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class UtcNanos:
    """An instant, as a signed 64-bit count of UTC nanoseconds since the epoch.

    Equality, ordering, and hashing are exact integer operations. Negative
    values denote instants before 1970-01-01T00:00:00Z and are fully
    supported.
    """

    nanos: int

    def __post_init__(self) -> None:
        _in_int64(_exact_int(self.nanos, "UtcNanos.nanos"), "UtcNanos.nanos")

    @classmethod
    def from_datetime(cls, dt: datetime) -> UtcNanos:
        """Convert an aware, zero-offset datetime to an exact instant.

        The conversion is exact in this direction: a ``datetime`` holds
        microseconds, and every microsecond is an exact whole number of
        nanoseconds.

        A naive datetime raises ``NaiveDatetimeError`` because it does not
        denote an instant. An aware datetime with a non-zero UTC offset raises
        ``NonUtcDatetimeError`` rather than being converted, so a caller who
        passed exchange-local time is told instead of having the value
        silently reinterpreted. Any aware datetime whose actual offset is zero
        is accepted, including ``ZoneInfo("UTC")``, because it denotes an
        unambiguous instant.

        ``datetime`` spans a far wider calendar range than int64 nanoseconds,
        so an instant outside that range raises ``TimeOverflowError``.
        """
        if not isinstance(dt, datetime):
            raise TimeTypeError(f"from_datetime expects a datetime, not {type(dt).__name__}")
        offset = dt.utcoffset()
        if offset is None:
            raise NaiveDatetimeError(
                "naive datetime has no timezone and does not denote an instant; "
                "attach timezone.utc explicitly"
            )
        if offset != timedelta(0):
            raise NonUtcDatetimeError(
                f"datetime has a non-zero UTC offset ({offset}); "
                f"convert it deliberately rather than relying on this boundary"
            )
        # Integer fields only. total_seconds() and timestamp() return floats
        # and lose nanoseconds at market-data magnitudes.
        delta = dt - EPOCH
        nanos = (
            delta.days * _SECONDS_PER_DAY + delta.seconds
        ) * NS_PER_SECOND + delta.microseconds * NS_PER_MICROSECOND
        return cls(_in_int64(nanos, "instant from datetime"))
