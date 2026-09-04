"""Exact integer fixed-point prices and tick-grid conversion.

This module implements two locked architecture decisions
(``docs/architecture.md`` section 13 and section 16 item 3):

* Prices are signed 64-bit fixed-point integers at a scale of 1e-9. One
  ``Price`` unit is one *nanounit* of the instrument's quote currency.
* Conversion to and from a tick grid is **exact only**. A price that does not
  land on the grid raises; it is never rounded to the nearest tick.

Floats never enter a price path. This is enforced twice over: statically,
because every public signature is annotated with exact integer types and the
package is type-checked under ``mypy --strict``; and at runtime, because every
constructor rejects non-``int`` input, including ``bool``.

The tick grid is anchored at zero and its size is supplied by the caller. This
module holds no instrument metadata: tick sizes come from instrument
definitions in the reference layer (L4), which does not exist yet, and must
never be hard-coded here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ofa.core.errors import (
    InvalidTickSizeError,
    PriceNotOnGridError,
    PriceOverflowError,
    PriceTypeError,
)

#: Nanounits per whole quote-currency unit. A price of 1.5 is 1_500_000_000.
PRICE_SCALE: Final = 1_000_000_000

#: Inclusive bounds of the signed 64-bit range that prices and tick counts
#: must remain within, so that any value can round-trip through storage.
INT64_MIN: Final = -(2**63)
INT64_MAX: Final = 2**63 - 1


def _exact_int(value: object, what: str) -> int:
    """Return ``value`` as an ``int``, rejecting every other type.

    ``bool`` is rejected explicitly even though it is a subclass of ``int``:
    ``Price(True)`` would otherwise silently mean one nanounit.
    """
    if isinstance(value, bool):
        raise PriceTypeError(f"{what} must be an int, not bool")
    if not isinstance(value, int):
        raise PriceTypeError(
            f"{what} must be an int, not {type(value).__name__}; "
            f"floats are never permitted in a price path"
        )
    return value


def _in_int64(value: int, what: str) -> int:
    """Return ``value`` if it fits the signed 64-bit range, else raise."""
    if value < INT64_MIN or value > INT64_MAX:
        raise PriceOverflowError(
            f"{what} is outside the signed 64-bit range [{INT64_MIN}, {INT64_MAX}]: {value}"
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class Price:
    """An exact price, held as a signed 64-bit count of nanounits.

    Equality, ordering, hashing, and negation are exact integer operations.

    Addition and subtraction between two prices are deliberately **not**
    defined. ``Price + Price`` has no meaning in this domain, and
    ``Price - Price`` is meaningful but yields a price *difference* — a spread,
    an excursion, a stop distance — which is a different dimension from a
    price. A ``PriceDelta`` type will be introduced when a concrete downstream
    requirement needs one (spread, excursion, stop distance, or accounting);
    until then the operations stay absent rather than silently mistyped.
    Multiplication and division by another price are likewise undefined.
    """

    nanounits: int

    def __post_init__(self) -> None:
        _in_int64(_exact_int(self.nanounits, "Price.nanounits"), "Price.nanounits")

    def __neg__(self) -> Price:
        return Price(_in_int64(-self.nanounits, "negated price"))


@dataclass(frozen=True, slots=True, order=True)
class Ticks:
    """A signed count of ticks on some tick grid.

    A ``Ticks`` value is meaningful only alongside the ``TickGrid`` that
    produced it; the count alone does not identify a price.
    """

    count: int

    def __post_init__(self) -> None:
        _in_int64(_exact_int(self.count, "Ticks.count"), "Ticks.count")

    def __add__(self, other: Ticks) -> Ticks:
        if not isinstance(other, Ticks):
            raise PriceTypeError(f"cannot add {type(other).__name__} to Ticks")
        return Ticks(_in_int64(self.count + other.count, "tick sum"))

    def __sub__(self, other: Ticks) -> Ticks:
        if not isinstance(other, Ticks):
            raise PriceTypeError(f"cannot subtract {type(other).__name__} from Ticks")
        return Ticks(_in_int64(self.count - other.count, "tick difference"))

    def __neg__(self) -> Ticks:
        return Ticks(_in_int64(-self.count, "negated tick count"))


@dataclass(frozen=True, slots=True)
class TickGrid:
    """A price grid of uniformly spaced ticks, anchored at zero.

    The grid is defined solely by its tick size. Instrument identity, tick
    value, and multiplier live in the reference layer and are not this
    module's concern.
    """

    tick_size: Price

    def __post_init__(self) -> None:
        if not isinstance(self.tick_size, Price):
            raise PriceTypeError(
                f"TickGrid.tick_size must be a Price, not {type(self.tick_size).__name__}"
            )
        if self.tick_size.nanounits <= 0:
            raise InvalidTickSizeError(
                f"tick size must be strictly positive, got {self.tick_size.nanounits} nanounits"
            )

    def is_on_grid(self, price: Price) -> bool:
        """Return whether ``price`` is an exact multiple of the tick size."""
        if not isinstance(price, Price):
            raise PriceTypeError(f"expected a Price, not {type(price).__name__}")
        return price.nanounits % self.tick_size.nanounits == 0

    def to_ticks(self, price: Price) -> Ticks:
        """Convert ``price`` to a tick count, exactly.

        Raises ``PriceNotOnGridError`` if the price is not an exact multiple of
        the tick size. It is never rounded.
        """
        if not isinstance(price, Price):
            raise PriceTypeError(f"expected a Price, not {type(price).__name__}")
        quotient, remainder = divmod(price.nanounits, self.tick_size.nanounits)
        if remainder != 0:
            raise PriceNotOnGridError(
                f"price {price.nanounits} is not a multiple of tick size "
                f"{self.tick_size.nanounits} (remainder {remainder} nanounits)"
            )
        return Ticks(_in_int64(quotient, "tick count"))

    def from_ticks(self, ticks: Ticks) -> Price:
        """Convert a tick count to the price it represents on this grid."""
        if not isinstance(ticks, Ticks):
            raise PriceTypeError(f"expected Ticks, not {type(ticks).__name__}")
        return Price(_in_int64(ticks.count * self.tick_size.nanounits, "price from ticks"))
