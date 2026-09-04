"""Example-based tests for exact prices and tick-grid conversion.

The `type: ignore` comments below are load-bearing: they mark the places where
mypy already rejects the call statically, and the test then proves the runtime
guard rejects it too. Both halves of the "no float in a price path" guarantee
are exercised.
"""

from __future__ import annotations

import pytest

from ofa.core.errors import (
    InvalidTickSizeError,
    OfaError,
    PriceNotOnGridError,
    PriceOverflowError,
    PriceTypeError,
)
from ofa.core.money import INT64_MAX, INT64_MIN, PRICE_SCALE, Price, TickGrid, Ticks

# A quarter-point tick, as used by the CME equity-index futures this project
# targets first. Declared here as a fixture value only; no instrument metadata
# lives in the code under test.
QUARTER_TICK = Price(PRICE_SCALE // 4)


# --------------------------------------------------------------------------
# Construction and type rejection
# --------------------------------------------------------------------------


def test_price_holds_exact_nanounits() -> None:
    assert Price(1_500_000_000).nanounits == 1_500_000_000
    assert Price(0).nanounits == 0
    assert Price(-7).nanounits == -7


def test_price_rejects_float() -> None:
    with pytest.raises(PriceTypeError):
        Price(1.5)  # type: ignore[arg-type]


def test_price_rejects_integral_float() -> None:
    """An integral float is still a float: exactness must not depend on luck."""
    with pytest.raises(PriceTypeError):
        Price(2.0)  # type: ignore[arg-type]


def test_price_rejects_bool() -> None:
    """bool is a subclass of int; Price(True) must not mean one nanounit."""
    with pytest.raises(PriceTypeError):
        Price(True)


def test_price_rejects_str_and_none() -> None:
    with pytest.raises(PriceTypeError):
        Price("100")  # type: ignore[arg-type]
    with pytest.raises(PriceTypeError):
        Price(None)  # type: ignore[arg-type]


def test_price_type_error_is_a_type_error() -> None:
    assert issubclass(PriceTypeError, TypeError)
    assert issubclass(PriceTypeError, OfaError)


def test_ticks_reject_float_and_bool() -> None:
    with pytest.raises(PriceTypeError):
        Ticks(1.5)  # type: ignore[arg-type]
    with pytest.raises(PriceTypeError):
        Ticks(True)


# --------------------------------------------------------------------------
# int64 boundaries
# --------------------------------------------------------------------------


def test_price_accepts_int64_bounds() -> None:
    assert Price(INT64_MAX).nanounits == INT64_MAX
    assert Price(INT64_MIN).nanounits == INT64_MIN


def test_price_rejects_values_beyond_int64() -> None:
    with pytest.raises(PriceOverflowError):
        Price(INT64_MAX + 1)
    with pytest.raises(PriceOverflowError):
        Price(INT64_MIN - 1)


def test_negating_int64_min_overflows() -> None:
    """-INT64_MIN is one past INT64_MAX; the asymmetry must not wrap."""
    with pytest.raises(PriceOverflowError):
        -Price(INT64_MIN)


def test_ticks_bounds_and_overflow() -> None:
    assert Ticks(INT64_MAX).count == INT64_MAX
    with pytest.raises(PriceOverflowError):
        Ticks(INT64_MAX + 1)
    with pytest.raises(PriceOverflowError):
        Ticks(INT64_MAX) + Ticks(1)


def test_price_overflow_error_is_an_overflow_error() -> None:
    assert issubclass(PriceOverflowError, OverflowError)


# --------------------------------------------------------------------------
# Arithmetic and type safety
# --------------------------------------------------------------------------


def test_price_negation_is_exact() -> None:
    assert -Price(3) == Price(-3)
    assert -Price(-3) == Price(3)
    assert -Price(0) == Price(0)


def test_price_negation_returns_int_backed_values() -> None:
    negated = -Price(3)
    assert type(negated.nanounits) is int
    assert not isinstance(negated.nanounits, float)


def test_price_does_not_support_addition_or_subtraction() -> None:
    """Price + Price is meaningless; Price - Price yields a delta, not a Price.

    Both stay absent until a ``PriceDelta`` type exists, so a caller cannot
    silently produce a mistyped quantity.
    """
    with pytest.raises(TypeError):
        Price(1) + Price(2)  # type: ignore[operator]
    with pytest.raises(TypeError):
        Price(1) - Price(2)  # type: ignore[operator]
    with pytest.raises(TypeError):
        Price(1) + 1  # type: ignore[operator]
    with pytest.raises(TypeError):
        Price(1) + Ticks(1)  # type: ignore[operator]


def test_price_and_ticks_are_not_comparable() -> None:
    with pytest.raises(TypeError):
        _ = Price(1) < Ticks(1)  # type: ignore[operator]


def test_price_is_immutable() -> None:
    price = Price(5)
    with pytest.raises(AttributeError):
        price.nanounits = 6  # type: ignore[misc]


def test_equality_ordering_and_hashing_are_deterministic() -> None:
    assert Price(5) == Price(5)
    assert Price(5) != Price(6)
    assert Price(5) != 5  # type: ignore[comparison-overlap]
    assert Price(-1) < Price(0) < Price(1)
    assert hash(Price(5)) == hash(Price(5))
    assert len({Price(5), Price(5), Price(6)}) == 2


# --------------------------------------------------------------------------
# Tick grid
# --------------------------------------------------------------------------


def test_tick_grid_rejects_non_positive_tick_size() -> None:
    with pytest.raises(InvalidTickSizeError):
        TickGrid(Price(0))
    with pytest.raises(InvalidTickSizeError):
        TickGrid(Price(-1))


def test_tick_grid_rejects_non_price_tick_size() -> None:
    with pytest.raises(PriceTypeError):
        TickGrid(250_000_000)  # type: ignore[arg-type]


def test_exact_conversion_round_trip() -> None:
    grid = TickGrid(QUARTER_TICK)
    price = Price(21_500 * PRICE_SCALE + PRICE_SCALE // 2)  # 21500.50
    ticks = grid.to_ticks(price)
    assert ticks == Ticks(86_002)
    assert grid.from_ticks(ticks) == price


def test_off_grid_price_raises_and_is_never_rounded() -> None:
    grid = TickGrid(QUARTER_TICK)
    off_grid = Price(PRICE_SCALE // 10)  # 0.10 is not a multiple of 0.25
    with pytest.raises(PriceNotOnGridError):
        grid.to_ticks(off_grid)


def test_one_nanounit_off_grid_raises_on_both_sides() -> None:
    grid = TickGrid(QUARTER_TICK)
    on_grid = grid.from_ticks(Ticks(4))
    assert grid.to_ticks(on_grid) == Ticks(4)
    for neighbour in (Price(on_grid.nanounits - 1), Price(on_grid.nanounits + 1)):
        with pytest.raises(PriceNotOnGridError):
            grid.to_ticks(neighbour)


def test_negative_prices_convert_and_reject_correctly() -> None:
    grid = TickGrid(QUARTER_TICK)
    assert grid.to_ticks(Price(-PRICE_SCALE)) == Ticks(-4)
    with pytest.raises(PriceNotOnGridError):
        grid.to_ticks(Price(-PRICE_SCALE - 1))


def test_zero_is_on_the_grid() -> None:
    grid = TickGrid(QUARTER_TICK)
    assert grid.to_ticks(Price(0)) == Ticks(0)
    assert grid.from_ticks(Ticks(0)) == Price(0)


def test_is_on_grid_predicate_does_not_raise() -> None:
    grid = TickGrid(QUARTER_TICK)
    assert grid.is_on_grid(Price(PRICE_SCALE)) is True
    assert grid.is_on_grid(Price(PRICE_SCALE // 10)) is False


def test_from_ticks_overflow_raises() -> None:
    grid = TickGrid(QUARTER_TICK)
    with pytest.raises(PriceOverflowError):
        grid.from_ticks(Ticks(INT64_MAX))


def test_tick_grid_rejects_float_arguments() -> None:
    grid = TickGrid(QUARTER_TICK)
    with pytest.raises(PriceTypeError):
        grid.to_ticks(1.5)  # type: ignore[arg-type]
    with pytest.raises(PriceTypeError):
        grid.from_ticks(4.0)  # type: ignore[arg-type]
    with pytest.raises(PriceTypeError):
        grid.is_on_grid(1.5)  # type: ignore[arg-type]


def test_price_not_on_grid_error_is_a_value_error() -> None:
    assert issubclass(PriceNotOnGridError, ValueError)
    assert issubclass(InvalidTickSizeError, ValueError)
