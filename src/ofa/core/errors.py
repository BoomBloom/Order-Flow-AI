"""Error types for the deterministic core.

Every error carries a project-specific base (``OfaError``) so that core
failures can be caught as a family, and a standard-library base so that
callers and tests can rely on ordinary Python semantics (a bad type raises a
``TypeError``, an out-of-range value raises an ``OverflowError``, and so on).
"""


class OfaError(Exception):
    """Base class for every error raised by the deterministic core."""


class PriceTypeError(OfaError, TypeError):
    """A value in a price path was not an exact integer.

    Raised for floats, bools, strings, and any other non-``int`` input.
    Floats are never permitted in a price path, not even when they happen to
    hold an integral value: accepting one would make the price path's
    exactness depend on the caller.
    """


class PriceOverflowError(OfaError, OverflowError):
    """A price or tick count fell outside the signed 64-bit range.

    Raised instead of silently wrapping or promoting to an arbitrary-precision
    integer, so that a value which could not round-trip through storage fails
    at the point it is created.
    """


class PriceNotOnGridError(OfaError, ValueError):
    """A price is not an exact multiple of the tick size.

    Tick conversion is exact-only: an off-grid price is an error, never a
    rounding. See ``docs/architecture.md`` section 16, item 3.
    """


class InvalidTickSizeError(OfaError, ValueError):
    """A tick size was zero or negative."""


class TimeTypeError(OfaError, TypeError):
    """A value in a time path was not of the exact type required.

    Raised for floats, bools, strings, and any other non-``int`` where an
    exact integer is expected — nanoseconds, or the year, month and day of a
    trading date — and for non-``datetime`` input where an aware datetime is
    required.

    Floats are never permitted: a float cannot hold a nanosecond instant
    exactly, so accepting one would make exactness depend on the magnitude of
    the value. ``bool`` is rejected explicitly because it is a subclass of
    ``int`` and would otherwise be read as 0 or 1.
    """


class TimeOverflowError(OfaError, OverflowError):
    """An instant fell outside the signed 64-bit nanosecond range.

    Raised instead of wrapping or silently promoting to an arbitrary-precision
    integer. ``datetime`` spans a far wider calendar range than int64
    nanoseconds, so conversion from a datetime can legitimately overflow.
    """


class NaiveDatetimeError(OfaError, ValueError):
    """A datetime carried no timezone information.

    A naive datetime does not denote an instant, because the zone it was
    written in is unknown. It is rejected rather than assumed to be UTC.
    """


class NonUtcDatetimeError(OfaError, ValueError):
    """An aware datetime had a non-zero UTC offset.

    It is rejected rather than silently converted, so that a caller who meant
    exchange-local time is told, instead of having the value reinterpreted.
    """


class InexactDatetimeError(OfaError, ValueError):
    """An instant carried a sub-microsecond remainder that a datetime cannot hold.

    A Python ``datetime`` stores microseconds. Converting an instant that is
    not an exact whole number of microseconds would lose information, so the
    exact conversion raises instead of truncating or rounding. Callers that
    accept the loss use the explicit lossy path, which returns the discarded
    remainder alongside the datetime.
    """


class InvalidTradeDateError(OfaError, ValueError):
    """The year, month and day do not form a valid Gregorian calendar date.

    Raised for impossible combinations such as 30 February, month 13, or
    29 February in a non-leap year, and for years outside the range a Python
    ``date`` can represent. It is not raised for a date that merely fails to
    be a trading day: whether a valid date is a session the exchange held is a
    calendar question, answered in the reference layer, not here.
    """


class CanonicalTypeError(OfaError, TypeError):
    """A value has no canonical form because its type is not supported.

    The canonical type set is closed and explicit. A type outside it raises
    rather than being serialized on a guess, because guessing is how two
    logically different values acquire the same content hash.

    Raised for floats and sets, for arbitrary objects and dataclasses, for a
    non-string mapping key, and for a subclass of a supported type — an
    ``IntEnum``, a ``NamedTuple``, an ``OrderedDict`` — where canonicalizing it
    as its base would silently discard the identity the subclass carries.
    """


class CanonicalValueError(OfaError, ValueError):
    """A value of a supported type could not be canonicalized.

    The type is right but the value is not representable: a string holding a
    lone surrogate, which cannot be encoded as UTF-8, or a structure nested
    past the canonical depth limit.
    """


class IdentifierTypeError(OfaError, TypeError):
    """An identifier was given a value of the wrong type.

    Raised for a non-``int`` where an identifier index is required and for a
    non-``str`` where an opaque token is required, including a subclass of
    either. ``bool`` is rejected explicitly because it is a subclass of ``int``
    and would otherwise be read as index 0 or 1.
    """


class InvalidIdentifierError(OfaError, ValueError):
    """An identifier's value is of the right type but not a valid identifier.

    Raised for an index outside the signed 32-bit range — not an arithmetic
    overflow, since identifiers support no arithmetic, but simply a value the
    stored schema cannot hold — and for an opaque token that is empty, is a
    relative-path name, or carries a path separator, whitespace, a control
    character or anything unencodable.
    """
