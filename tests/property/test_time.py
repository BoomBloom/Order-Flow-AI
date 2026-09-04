"""Property tests for the core temporal value types.

The datetime properties use an independent oracle: expected nanoseconds are
computed from ``calendar.timegm`` over the UTC time tuple, which shares no
code path with the implementation's ``timedelta``-field arithmetic. The
TradeDate properties use the standard library's own ``date`` as the oracle
for ordering and ISO rendering.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ofa.core.errors import InvalidTradeDateError, TimeTypeError
from ofa.core.time import (
    INT64_MAX,
    INT64_MIN,
    NS_PER_MICROSECOND,
    NS_PER_SECOND,
    TradeDate,
    UtcNanos,
)

int64s = st.integers(min_value=INT64_MIN, max_value=INT64_MAX)

#: Below this the floored microsecond falls under INT64_MIN, so the floored
#: datetime cannot itself be expressed as a UtcNanos. Properties that
#: reconstruct through from_datetime are stated on this restricted domain.
LOWEST_ALIGNED = INT64_MIN + 808
reconstructable = st.integers(min_value=LOWEST_ALIGNED, max_value=INT64_MAX)
aligned_reconstructable = st.integers(
    min_value=LOWEST_ALIGNED // NS_PER_MICROSECOND,
    max_value=INT64_MAX // NS_PER_MICROSECOND,
).map(lambda us: us * NS_PER_MICROSECOND)

# Bounded well inside the int64 nanosecond window (1677-09-21 to 2262-04-11)
# so that every generated datetime is representable.
utc_datetimes = st.datetimes(
    min_value=datetime(1678, 1, 1),
    max_value=datetime(2261, 12, 31),
    timezones=st.just(UTC),
)


def _expected_nanos(dt: datetime) -> int:
    """Independent oracle: seconds from timegm, microseconds added separately."""
    return calendar.timegm(dt.utctimetuple()) * NS_PER_SECOND + dt.microsecond * 1_000


@given(int64s)
def test_construction_preserves_the_exact_value(value: int) -> None:
    assert UtcNanos(value).nanos == value
    assert type(UtcNanos(value).nanos) is int


@given(int64s, int64s)
def test_ordering_matches_integer_ordering(left: int, right: int) -> None:
    assert (UtcNanos(left) < UtcNanos(right)) == (left < right)
    assert (UtcNanos(left) == UtcNanos(right)) == (left == right)


@given(int64s)
def test_equal_instants_hash_equally(value: int) -> None:
    assert hash(UtcNanos(value)) == hash(UtcNanos(value))


@given(utc_datetimes)
def test_from_datetime_matches_an_independent_oracle(dt: datetime) -> None:
    assert UtcNanos.from_datetime(dt).nanos == _expected_nanos(dt)


@given(utc_datetimes)
def test_from_datetime_never_produces_a_float(dt: datetime) -> None:
    assert type(UtcNanos.from_datetime(dt).nanos) is int


@given(utc_datetimes)
def test_pre_and_post_epoch_signs_are_correct(dt: datetime) -> None:
    """The sign of the instant follows the epoch, in both directions."""
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    nanos = UtcNanos.from_datetime(dt).nanos
    assert (nanos < 0) == (dt < epoch)
    assert (nanos == 0) == (dt == epoch)


@given(utc_datetimes)
def test_microsecond_offsets_shift_the_instant_exactly(dt: datetime) -> None:
    """Adding one microsecond adds exactly one thousand nanoseconds."""
    shifted = dt + timedelta(microseconds=1)
    assert UtcNanos.from_datetime(shifted).nanos - UtcNanos.from_datetime(dt).nanos == 1_000


@given(utc_datetimes)
def test_conversion_is_monotonic_in_the_datetime(dt: datetime) -> None:
    later = dt + timedelta(seconds=1)
    assert UtcNanos.from_datetime(dt) < UtcNanos.from_datetime(later)


@given(int64s)
def test_remainder_is_always_within_one_microsecond(nanos: int) -> None:
    """Total across the whole domain, including the lower band."""
    _, remainder = UtcNanos(nanos).to_datetime_with_remainder()
    assert 0 <= remainder <= 999
    assert type(remainder) is int


@given(int64s)
def test_split_reconstructs_the_instant_by_integer_arithmetic(nanos: int) -> None:
    """The mathematical identity, stated without a UtcNanos round trip.

    This holds everywhere, including the lower 808 ns band where the floored
    datetime is not itself representable.
    """
    _, remainder = UtcNanos(nanos).to_datetime_with_remainder()
    floored_microseconds = nanos // NS_PER_MICROSECOND
    assert floored_microseconds * NS_PER_MICROSECOND + remainder == nanos


@given(int64s)
def test_alignment_predicate_matches_a_zero_remainder(nanos: int) -> None:
    instant = UtcNanos(nanos)
    _, remainder = instant.to_datetime_with_remainder()
    assert instant.is_microsecond_aligned == (remainder == 0)


@given(reconstructable)
def test_reconstruction_through_from_datetime_on_its_true_domain(nanos: int) -> None:
    """The round trip holds above the band, and is claimed only there."""
    moment, remainder = UtcNanos(nanos).to_datetime_with_remainder()
    assert UtcNanos.from_datetime(moment).nanos + remainder == nanos


@given(aligned_reconstructable)
def test_exact_conversion_round_trips(nanos: int) -> None:
    instant = UtcNanos(nanos)
    assert UtcNanos.from_datetime(instant.to_datetime()) == instant


@given(reconstructable)
def test_floored_datetime_never_exceeds_the_true_instant(nanos: int) -> None:
    moment, _ = UtcNanos(nanos).to_datetime_with_remainder()
    assert UtcNanos.from_datetime(moment).nanos <= nanos


@given(int64s)
def test_returned_datetime_is_always_utc_aware(nanos: int) -> None:
    moment, _ = UtcNanos(nanos).to_datetime_with_remainder()
    assert moment.tzinfo is UTC


@given(int64s, int64s)
def test_datetime_conversion_is_weakly_monotonic(left: int, right: int) -> None:
    """Weak, not strict: instants inside one microsecond share a datetime."""
    if left > right:
        left, right = right, left
    earlier, _ = UtcNanos(left).to_datetime_with_remainder()
    later, _ = UtcNanos(right).to_datetime_with_remainder()
    assert earlier <= later


# --------------------------------------------------------------------------
# TradeDate
# --------------------------------------------------------------------------

dates = st.dates()
components = st.integers(min_value=-5, max_value=10_050)


@given(dates)
def test_trade_date_to_date_round_trips_any_valid_date(value: date) -> None:
    assert TradeDate(value.year, value.month, value.day).to_date() == value


@given(dates)
def test_trade_date_isoformat_matches_the_standard_library(value: date) -> None:
    """Independent oracle: the stdlib date's own ISO rendering."""
    assert TradeDate(value.year, value.month, value.day).isoformat() == value.isoformat()


@given(dates, dates)
def test_trade_date_ordering_matches_date_ordering(left: date, right: date) -> None:
    """The central invariant: chronological ordering, identical to date's."""
    a = TradeDate(left.year, left.month, left.day)
    b = TradeDate(right.year, right.month, right.day)
    assert (a < b) == (left < right)
    assert (a == b) == (left == right)
    assert (a > b) == (left > right)


@given(dates)
def test_equal_trade_dates_hash_equally(value: date) -> None:
    a = TradeDate(value.year, value.month, value.day)
    b = TradeDate(value.year, value.month, value.day)
    assert a == b
    assert hash(a) == hash(b)


@given(components, components, components)
def test_arbitrary_components_either_construct_correctly_or_raise(
    year: int, month: int, day: int
) -> None:
    """Never a wrong date, and never an unexpected exception type."""
    try:
        trade_date = TradeDate(year, month, day)
    except InvalidTradeDateError:
        with pytest.raises(ValueError):
            date(year, month, day)
    else:
        assert trade_date.to_date() == date(year, month, day)


@given(st.booleans(), st.integers(min_value=0, max_value=2))
def test_a_bool_in_any_position_is_rejected(flag: bool, position: int) -> None:
    parts: list[object] = [2024, 3, 11]
    parts[position] = flag
    with pytest.raises(TimeTypeError):
        TradeDate(*parts)  # type: ignore[arg-type]
