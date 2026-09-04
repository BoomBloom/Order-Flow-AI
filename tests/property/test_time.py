"""Property tests for exact UTC-nanosecond instants.

The datetime properties use an independent oracle: expected nanoseconds are
computed from ``calendar.timegm`` over the UTC time tuple, which shares no
code path with the implementation's ``timedelta``-field arithmetic.
"""

from __future__ import annotations

import calendar
from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from ofa.core.time import INT64_MAX, INT64_MIN, NS_PER_SECOND, UtcNanos

int64s = st.integers(min_value=INT64_MIN, max_value=INT64_MAX)

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
