"""Property tests for exact prices and tick-grid conversion.

These cover the invariants that must hold across the whole int64 range, not
just at hand-picked values: exact round-tripping, off-grid rejection, ordering
consistency with integer arithmetic, and the absence of floats.

Hypothesis strategies here never generate floats as *valid* price input.
Floats appear only in the rejection tests in ``tests/unit/test_money.py``.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from ofa.core.errors import PriceNotOnGridError
from ofa.core.money import INT64_MAX, INT64_MIN, Price, TickGrid, Ticks

# Tick sizes span one nanounit up to a large grid, so the properties are not
# only exercised on realistic futures ticks.
tick_sizes = st.integers(min_value=1, max_value=10**12)
int64s = st.integers(min_value=INT64_MIN, max_value=INT64_MAX)


@st.composite
def grid_and_tick_count(draw: st.DrawFn) -> tuple[TickGrid, Ticks]:
    """A grid and a tick count whose product is guaranteed to fit int64."""
    tick_size = draw(tick_sizes)
    limit = INT64_MAX // tick_size
    count = draw(st.integers(min_value=-limit, max_value=limit))
    return TickGrid(Price(tick_size)), Ticks(count)


@given(grid_and_tick_count())
def test_ticks_round_trip_exactly(case: tuple[TickGrid, Ticks]) -> None:
    grid, ticks = case
    assert grid.to_ticks(grid.from_ticks(ticks)) == ticks


@given(grid_and_tick_count())
def test_prices_produced_by_the_grid_are_on_the_grid(case: tuple[TickGrid, Ticks]) -> None:
    grid, ticks = case
    assert grid.is_on_grid(grid.from_ticks(ticks)) is True


@st.composite
def grid_count_and_sub_tick_offset(draw: st.DrawFn) -> tuple[TickGrid, Ticks, int]:
    """A grid, a tick count, and a non-zero offset strictly inside one tick.

    Bounds are chosen so that ``count * tick_size + offset`` always fits int64,
    so the strategy needs no ``assume()`` filtering and every generated example
    exercises the property.
    """
    tick_size = draw(st.integers(min_value=2, max_value=10**12))
    limit = INT64_MAX // tick_size - 1
    count = draw(st.integers(min_value=-limit, max_value=limit))
    offset = draw(st.integers(min_value=1, max_value=tick_size - 1))
    return TickGrid(Price(tick_size)), Ticks(count), offset


@given(grid_count_and_sub_tick_offset())
def test_off_grid_prices_always_raise(case: tuple[TickGrid, Ticks, int]) -> None:
    """Any non-zero sub-tick offset must raise, never round to a neighbour."""
    grid, ticks, offset = case
    off_grid = Price(grid.from_ticks(ticks).nanounits + offset)
    assert grid.is_on_grid(off_grid) is False
    with pytest.raises(PriceNotOnGridError):
        grid.to_ticks(off_grid)


@given(grid_and_tick_count())
def test_conversion_never_produces_a_float(case: tuple[TickGrid, Ticks]) -> None:
    grid, ticks = case
    price = grid.from_ticks(ticks)
    assert type(price.nanounits) is int
    assert type(grid.to_ticks(price).count) is int


@given(int64s, int64s)
def test_ordering_matches_integer_ordering(left: int, right: int) -> None:
    assert (Price(left) < Price(right)) == (left < right)
    assert (Price(left) == Price(right)) == (left == right)


@given(int64s)
def test_equal_prices_hash_equally(value: int) -> None:
    assert hash(Price(value)) == hash(Price(value))


@given(int64s)
def test_double_negation_is_identity_when_in_range(value: int) -> None:
    assume(value != INT64_MIN)
    negated = -Price(value)
    assert -negated == Price(value)


@given(tick_sizes)
def test_zero_is_on_every_grid(tick_size: int) -> None:
    grid = TickGrid(Price(tick_size))
    assert grid.to_ticks(Price(0)) == Ticks(0)
