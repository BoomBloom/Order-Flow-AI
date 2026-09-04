"""Example-based tests for exact UTC-nanosecond instants.

The `type: ignore` comments mark the places where mypy already rejects the
call statically; the test then proves the runtime guard rejects it too.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from ofa.core.errors import (
    NaiveDatetimeError,
    NonUtcDatetimeError,
    OfaError,
    TimeOverflowError,
    TimeTypeError,
)
from ofa.core.time import (
    EPOCH,
    INT64_MAX,
    INT64_MIN,
    NS_PER_SECOND,
    UtcNanos,
)

# --------------------------------------------------------------------------
# Construction and type rejection
# --------------------------------------------------------------------------


def test_holds_exact_nanoseconds() -> None:
    assert UtcNanos(0).nanos == 0
    assert UtcNanos(1_710_163_800_123_456_789).nanos == 1_710_163_800_123_456_789


def test_epoch_is_zero() -> None:
    assert UtcNanos.from_datetime(EPOCH) == UtcNanos(0)


def test_negative_values_are_pre_epoch_and_supported() -> None:
    assert UtcNanos(-1).nanos == -1
    assert UtcNanos(-NS_PER_SECOND).nanos == -1_000_000_000


def test_rejects_float() -> None:
    with pytest.raises(TimeTypeError):
        UtcNanos(1.5)  # type: ignore[arg-type]


def test_rejects_integral_float() -> None:
    """An integral float is still a float: exactness must not depend on luck."""
    with pytest.raises(TimeTypeError):
        UtcNanos(2.0)  # type: ignore[arg-type]


def test_rejects_bool() -> None:
    """bool subclasses int; UtcNanos(True) must not mean one nanosecond."""
    with pytest.raises(TimeTypeError):
        UtcNanos(True)


def test_rejects_str_and_none() -> None:
    with pytest.raises(TimeTypeError):
        UtcNanos("0")  # type: ignore[arg-type]
    with pytest.raises(TimeTypeError):
        UtcNanos(None)  # type: ignore[arg-type]


def test_error_hierarchy() -> None:
    assert issubclass(TimeTypeError, TypeError)
    assert issubclass(TimeOverflowError, OverflowError)
    assert issubclass(NaiveDatetimeError, ValueError)
    assert issubclass(NonUtcDatetimeError, ValueError)
    for err in (TimeTypeError, TimeOverflowError, NaiveDatetimeError, NonUtcDatetimeError):
        assert issubclass(err, OfaError)


# --------------------------------------------------------------------------
# int64 boundaries
# --------------------------------------------------------------------------


def test_accepts_int64_bounds() -> None:
    assert UtcNanos(INT64_MAX).nanos == INT64_MAX
    assert UtcNanos(INT64_MIN).nanos == INT64_MIN


def test_rejects_one_past_int64_bounds() -> None:
    with pytest.raises(TimeOverflowError):
        UtcNanos(INT64_MAX + 1)
    with pytest.raises(TimeOverflowError):
        UtcNanos(INT64_MIN - 1)


# --------------------------------------------------------------------------
# from_datetime: timezone handling
# --------------------------------------------------------------------------


def test_rejects_naive_datetime() -> None:
    with pytest.raises(NaiveDatetimeError):
        UtcNanos.from_datetime(datetime(2024, 3, 11, 13, 30))


def test_rejects_non_zero_offset_datetime() -> None:
    chicago = datetime(2024, 3, 11, 8, 30, tzinfo=ZoneInfo("America/Chicago"))
    with pytest.raises(NonUtcDatetimeError):
        UtcNanos.from_datetime(chicago)


def test_rejects_fixed_non_zero_offset() -> None:
    with pytest.raises(NonUtcDatetimeError):
        UtcNanos.from_datetime(datetime(2024, 3, 11, tzinfo=timezone(timedelta(hours=1))))


def test_accepts_timezone_utc() -> None:
    dt = datetime(2024, 3, 11, 13, 30, tzinfo=UTC)
    assert UtcNanos.from_datetime(dt).nanos == 1_710_163_800_000_000_000


def test_accepts_zero_offset_timezone_object() -> None:
    dt = datetime(2024, 3, 11, 13, 30, tzinfo=timezone(timedelta(0)))
    assert UtcNanos.from_datetime(dt) == UtcNanos(1_710_163_800_000_000_000)


def test_accepts_zoneinfo_utc() -> None:
    dt = datetime(2024, 3, 11, 13, 30, tzinfo=ZoneInfo("UTC"))
    assert UtcNanos.from_datetime(dt) == UtcNanos(1_710_163_800_000_000_000)


def test_accepts_zone_whose_actual_offset_is_zero() -> None:
    """London in January is at +00:00, so it denotes an unambiguous instant."""
    london_winter = datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("Europe/London"))
    assert london_winter.utcoffset() == timedelta(0)
    utc_equivalent = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    assert UtcNanos.from_datetime(london_winter) == UtcNanos.from_datetime(utc_equivalent)


# --------------------------------------------------------------------------
# from_datetime: type and range
# --------------------------------------------------------------------------


def test_rejects_non_datetime_input() -> None:
    with pytest.raises(TimeTypeError):
        UtcNanos.from_datetime(0)  # type: ignore[arg-type]
    with pytest.raises(TimeTypeError):
        UtcNanos.from_datetime("2024-03-11T13:30:00Z")  # type: ignore[arg-type]


def test_rejects_plain_date() -> None:
    """date is not a datetime; it carries no instant."""
    with pytest.raises(TimeTypeError):
        UtcNanos.from_datetime(date(2024, 3, 11))  # type: ignore[arg-type]


def test_datetime_min_and_max_overflow_int64_nanoseconds() -> None:
    """datetime spans years 1-9999; int64 nanoseconds span 1677-2262."""
    with pytest.raises(TimeOverflowError):
        UtcNanos.from_datetime(datetime.min.replace(tzinfo=UTC))
    with pytest.raises(TimeOverflowError):
        UtcNanos.from_datetime(datetime.max.replace(tzinfo=UTC))


def test_representable_range_endpoints_convert() -> None:
    """The extremes of the int64 range are still inside datetime's range."""
    just_inside_low = datetime(1678, 1, 1, tzinfo=UTC)
    just_inside_high = datetime(2261, 1, 1, tzinfo=UTC)
    assert INT64_MIN < UtcNanos.from_datetime(just_inside_low).nanos < 0
    assert 0 < UtcNanos.from_datetime(just_inside_high).nanos < INT64_MAX


# --------------------------------------------------------------------------
# from_datetime: exactness, hand-computed
# --------------------------------------------------------------------------


def test_known_instant_matches_hand_calculation() -> None:
    """2024-03-11T13:30:00.123456Z, computed independently of the module.

    Days from 1970-01-01 to 2024-03-11 = 19793. Seconds into the day for
    13:30:00 = 48600. So 19793*86400 + 48600 = 1710163800 seconds, then the
    microsecond field contributes 123456 * 1000 nanoseconds.
    """
    dt = datetime(2024, 3, 11, 13, 30, 0, 123456, tzinfo=UTC)
    expected = (19_793 * 86_400 + 48_600) * NS_PER_SECOND + 123_456 * 1_000
    assert expected == 1_710_163_800_123_456_000
    assert UtcNanos.from_datetime(dt).nanos == expected


def test_pre_epoch_instant_matches_hand_calculation() -> None:
    """1969-12-31T23:59:59.999999Z is exactly one microsecond before the epoch."""
    dt = datetime(1969, 12, 31, 23, 59, 59, 999_999, tzinfo=UTC)
    assert UtcNanos.from_datetime(dt).nanos == -1_000


def test_one_second_before_epoch() -> None:
    dt = datetime(1969, 12, 31, 23, 59, 59, tzinfo=UTC)
    assert UtcNanos.from_datetime(dt) == UtcNanos(-NS_PER_SECOND)


def test_far_pre_epoch_conversion_is_exact_where_a_float_path_would_drift() -> None:
    """A float seconds path loses over a microsecond at this magnitude.

    int((dt - EPOCH).total_seconds() * 1e9) yields -9208549799999997952 here,
    which is 1048 ns away from the exact value. This test fails if the
    implementation ever routes through a float.
    """
    dt = datetime(1678, 3, 11, 13, 30, 0, 1, tzinfo=UTC)
    assert UtcNanos.from_datetime(dt).nanos == -9_208_549_799_999_999_000


# --------------------------------------------------------------------------
# Value semantics
# --------------------------------------------------------------------------


def test_is_immutable() -> None:
    instant = UtcNanos(5)
    with pytest.raises(AttributeError):
        instant.nanos = 6  # type: ignore[misc]


def test_equality_ordering_and_hashing_are_deterministic() -> None:
    assert UtcNanos(5) == UtcNanos(5)
    assert UtcNanos(5) != UtcNanos(6)
    assert UtcNanos(5) != 5  # type: ignore[comparison-overlap]
    assert UtcNanos(-1) < UtcNanos(0) < UtcNanos(1)
    assert hash(UtcNanos(5)) == hash(UtcNanos(5))
    assert len({UtcNanos(5), UtcNanos(5), UtcNanos(6)}) == 2


def test_does_not_support_arithmetic() -> None:
    """An instant is not a duration; no arithmetic is part of the API."""
    for name in ("__add__", "__sub__", "__mul__", "__truediv__"):
        assert not hasattr(UtcNanos, name), f"UtcNanos must not define {name}"


def test_has_no_wall_clock_or_trade_date_conversion() -> None:
    """Absence is the enforcement: these must not appear in a later step."""
    for name in ("now", "today", "to_trade_date", "from_timestamp", "to_timestamp"):
        assert not hasattr(UtcNanos, name), f"UtcNanos must not define {name}"
