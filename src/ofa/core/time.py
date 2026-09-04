"""Core temporal value types: an exact instant, and an assigned trading date.

``UtcNanos`` is an instant. ``TradeDate`` is a trading date that something
else assigned. They are deliberately unrelated: this module offers no
conversion between them in either direction, and none may be added here.

This module implements the timestamp half of the locked data contract
(``docs/data_specification.md`` section 1 item 7 and section 6): all internal
timestamps are UTC nanoseconds since the Unix epoch, held as ``int64``. Local
exchange time exists only in session definitions and human-facing output,
neither of which lives here.

``UtcNanos`` is a value, not an identifier. Nanosecond timestamps are **not**
unique in a market-data stream — many events routinely share a ``ts_event`` —
so the canonical ordering key remains ``(ts_event, sequence, ingest_index)``
(``docs/architecture.md`` section 16 item 5).

**The datetime representation is for human-facing output and interoperability
only.** It must never become the canonical timestamp representation, an event
ordering key, or an identity key. The canonical representation is integer
nanoseconds; ordering remains ``(ts_event, sequence, ingest_index)``. This is
not a stylistic preference: a Python ``datetime`` holds microseconds, so
**different ``UtcNanos`` values intentionally map to the same datetime**.
Sorting or comparing by the converted datetime silently reorders events that
share a microsecond, and datetime equality returns true for instants that are
not equal.

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
from datetime import UTC, date, datetime, timedelta
from typing import Final

from ofa.core.errors import (
    InexactDatetimeError,
    InvalidTradeDateError,
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

    def _split_microseconds(self) -> tuple[int, int]:
        """Split this instant into whole microseconds and a nanosecond remainder.

        Floor division, so the remainder is always in ``0..999`` and the
        microsecond component is always at or before the true instant — on
        both sides of the epoch. Truncation toward zero would yield negative
        remainders before 1970 and break monotonicity across the epoch.

        This is the single implementation of the split; the alignment
        predicate and both datetime conversions derive from it.
        """
        return divmod(self.nanos, NS_PER_MICROSECOND)

    @property
    def is_microsecond_aligned(self) -> bool:
        """Whether this instant is an exact whole number of microseconds.

        Equivalently: whether :meth:`to_datetime` will succeed rather than
        raising ``InexactDatetimeError``.
        """
        return self._split_microseconds()[1] == 0

    def to_datetime_with_remainder(self) -> tuple[datetime, int]:
        """The floored instant, plus the sub-microsecond remainder it discards.

        Returns an aware UTC datetime at or before the true instant, and the
        remainder in nanoseconds, always in ``0..999``. Together the pair is a
        complete representation of the original instant::

            floored_microseconds * NS_PER_MICROSECOND + remainder == self.nanos

        The loss is returned rather than hidden, so a caller cannot discard it
        without doing so visibly.

        The datetime component **alone** is not guaranteed to be representable
        as a ``UtcNanos``. For the lowest 808 nanoseconds of the int64 range
        the floored microsecond lies just below ``INT64_MIN``, so
        :meth:`from_datetime` on that datetime raises ``TimeOverflowError``
        even though the returned pair is correct. No microsecond-aligned value
        falls in that band, so :meth:`to_datetime` is unaffected.
        """
        microseconds, remainder = self._split_microseconds()
        return EPOCH + timedelta(microseconds=microseconds), remainder

    def to_datetime(self) -> datetime:
        """This instant as an aware UTC datetime, exactly.

        Raises ``InexactDatetimeError`` when the instant carries a
        sub-microsecond remainder that a Python ``datetime`` cannot hold. It is
        never truncated and never rounded, so a datetime returned from here is
        always the true instant. Use :meth:`to_datetime_with_remainder` to
        accept the loss deliberately.
        """
        moment, remainder = self.to_datetime_with_remainder()
        if remainder != 0:
            raise InexactDatetimeError(
                f"instant {self.nanos} carries a sub-microsecond remainder of "
                f"{remainder} ns, which a datetime cannot hold; use "
                f"to_datetime_with_remainder() to accept the loss explicitly"
            )
        return moment


@dataclass(frozen=True, slots=True, order=True)
class TradeDate:
    """A trading date, given as an explicit year, month and day.

    A trading date is **assigned**, not derived. The exchange session date is
    fixed by an exchange calendar in the reference layer (L4), which knows
    about holidays, early closes and daylight-saving shifts; a Globex session
    opening on a Sunday evening belongs to Monday's trading date. This type
    holds the answer, never computes it.

    Consequently there is no conversion here in either direction — no
    ``from_datetime``, no ``from_utc_nanos``, no ``to_utc_nanos`` — and none
    may be added. That mapping is a function of an instant, an instrument and
    a calendar version, so it belongs to the layer that holds all three.
    ``docs/architecture.md`` section 4.2 puts it directly: a trade date is
    "assigned by the L4 calendar, never by truncating a timestamp".

    The type is deliberately free of venue, timezone and session information.
    Two venues' ``TradeDate(2024, 3, 11)`` compare equal while covering
    different intervals of real time; equality here means "the same labelled
    date", not "the same session".

    Ordering is chronological, but **adjacency is not**: ``TradeDate(2024, 3,
    8)`` and ``TradeDate(2024, 3, 11)`` are consecutive trading days across a
    weekend. There is no successor or predecessor operation, and calendar
    arithmetic on the result of :meth:`to_date` is not trading-date
    sequencing — that is a calendar question for L4.

    Construction takes three integers rather than a ``date`` on purpose.
    ``datetime`` is a subclass of ``date``, so a constructor accepting a
    ``date`` would silently accept a ``datetime`` and discard its time of day.
    Three integers make that mistake unrepresentable.
    """

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        _exact_int(self.year, "TradeDate.year")
        _exact_int(self.month, "TradeDate.month")
        _exact_int(self.day, "TradeDate.day")
        # Only once the components are known to be exact integers is a date
        # built, so the calendar check can never be handed a bool or a float.
        self._as_date()

    def _as_date(self) -> date:
        """Build the standard-library date, translating its error to ours.

        Gregorian correctness — leap years, month lengths, the representable
        year range — is delegated to the standard library rather than
        reimplemented here.
        """
        try:
            return date(self.year, self.month, self.day)
        except ValueError as exc:
            raise InvalidTradeDateError(
                f"({self.year}, {self.month}, {self.day}) is not a valid "
                f"Gregorian calendar date: {exc}"
            ) from exc

    def to_date(self) -> date:
        """This trading date as a standard-library ``date``.

        An interoperability and display boundary, like
        :meth:`UtcNanos.to_datetime`. Do not do calendar arithmetic on the
        result to move between trading days: the next trading date is not
        generally the next calendar date.
        """
        return self._as_date()

    def isoformat(self) -> str:
        """The canonical string form, ``YYYY-MM-DD``, zero-padded.

        Deterministic and locale-independent.
        """
        return self._as_date().isoformat()
