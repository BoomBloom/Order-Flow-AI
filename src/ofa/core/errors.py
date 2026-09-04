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
