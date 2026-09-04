"""Example-based tests for exact UTC-nanosecond instants.

The `type: ignore` comments mark the places where mypy already rejects the
call statically; the test then proves the runtime guard rejects it too.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from ofa.core.errors import (
    InexactDatetimeError,
    InvalidTradeDateError,
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
    NS_PER_MICROSECOND,
    NS_PER_SECOND,
    TradeDate,
    UtcNanos,
)

#: The lowest and highest microsecond-aligned instants inside the int64 range.
#: Below LOWEST_ALIGNED the floored microsecond itself falls under INT64_MIN.
LOWEST_ALIGNED = INT64_MIN + 808
HIGHEST_ALIGNED = INT64_MAX - 807

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


# --------------------------------------------------------------------------
# is_microsecond_aligned
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nanos", [0, 1_000, -1_000, NS_PER_SECOND, -NS_PER_SECOND, LOWEST_ALIGNED, HIGHEST_ALIGNED]
)
def test_aligned_values_report_aligned(nanos: int) -> None:
    assert UtcNanos(nanos).is_microsecond_aligned is True


@pytest.mark.parametrize("nanos", [1, 999, -1, -999, 567, INT64_MIN, INT64_MAX])
def test_unaligned_values_report_unaligned(nanos: int) -> None:
    assert UtcNanos(nanos).is_microsecond_aligned is False


@pytest.mark.parametrize(
    "nanos",
    [
        0,
        1,
        999,
        1_000,
        -1,
        -999,
        -1_000,
        -1_500,
        567,
        INT64_MIN,
        INT64_MAX,
        LOWEST_ALIGNED,
        HIGHEST_ALIGNED,
    ],
)
def test_alignment_predicate_agrees_with_exact_conversion(nanos: int) -> None:
    """The predicate is exactly the condition under which to_datetime succeeds."""
    instant = UtcNanos(nanos)
    if instant.is_microsecond_aligned:
        instant.to_datetime()
    else:
        with pytest.raises(InexactDatetimeError):
            instant.to_datetime()


# --------------------------------------------------------------------------
# to_datetime: exact path
# --------------------------------------------------------------------------


def test_epoch_converts_exactly() -> None:
    assert UtcNanos(0).to_datetime() == datetime(1970, 1, 1, tzinfo=UTC)


def test_known_instant_converts_exactly() -> None:
    expected = datetime(2024, 3, 11, 13, 30, 0, 123_456, tzinfo=UTC)
    assert UtcNanos(1_710_163_800_123_456_000).to_datetime() == expected


def test_aligned_pre_epoch_converts_exactly() -> None:
    assert UtcNanos(-NS_PER_SECOND).to_datetime() == datetime(1969, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_returned_datetime_is_utc_aware() -> None:
    """B6: tzinfo must be datetime.UTC, not merely some zero-offset object."""
    moment = UtcNanos(0).to_datetime()
    assert moment.tzinfo is UTC
    assert moment.utcoffset() == timedelta(0)


def test_aligned_int64_extremes_convert_and_round_trip() -> None:
    for nanos in (LOWEST_ALIGNED, HIGHEST_ALIGNED):
        instant = UtcNanos(nanos)
        assert UtcNanos.from_datetime(instant.to_datetime()) == instant


@pytest.mark.parametrize("remainder", [1, 567, 999])
def test_sub_microsecond_remainder_raises(remainder: int) -> None:
    with pytest.raises(InexactDatetimeError):
        UtcNanos(1_710_163_800_123_456_000 + remainder).to_datetime()


def test_minus_one_nanosecond_raises_rather_than_flooring_silently() -> None:
    with pytest.raises(InexactDatetimeError):
        UtcNanos(-1).to_datetime()


def test_inexact_error_hierarchy() -> None:
    assert issubclass(InexactDatetimeError, ValueError)
    assert issubclass(InexactDatetimeError, OfaError)


# --------------------------------------------------------------------------
# to_datetime_with_remainder: the explicit lossy path
# --------------------------------------------------------------------------


def test_aligned_values_have_zero_remainder() -> None:
    moment, remainder = UtcNanos(0).to_datetime_with_remainder()
    assert moment == datetime(1970, 1, 1, tzinfo=UTC)
    assert remainder == 0


def test_remainder_is_returned_and_reconstructs_the_instant() -> None:
    nanos = 1_710_163_800_123_456_567
    moment, remainder = UtcNanos(nanos).to_datetime_with_remainder()
    assert remainder == 567
    assert UtcNanos.from_datetime(moment).nanos + remainder == nanos


def test_minus_one_nanosecond_floors_and_reports_remainder_999() -> None:
    """Floor, not truncation: the remainder is 999, never -1."""
    moment, remainder = UtcNanos(-1).to_datetime_with_remainder()
    assert moment == datetime(1969, 12, 31, 23, 59, 59, 999_999, tzinfo=UTC)
    assert remainder == 999


def test_minus_fifteen_hundred_nanoseconds_floors_correctly() -> None:
    moment, remainder = UtcNanos(-1_500).to_datetime_with_remainder()
    assert moment == datetime(1969, 12, 31, 23, 59, 59, 999_998, tzinfo=UTC)
    assert remainder == 500


def test_int64_max_floors_and_round_trips() -> None:
    moment, remainder = UtcNanos(INT64_MAX).to_datetime_with_remainder()
    assert remainder == 807
    assert UtcNanos.from_datetime(moment).nanos + remainder == INT64_MAX


def test_lossy_path_returns_utc_aware_datetime() -> None:
    moment, _ = UtcNanos(567).to_datetime_with_remainder()
    assert moment.tzinfo is UTC


# --------------------------------------------------------------------------
# The lower 808 ns band (decision B1)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("nanos", [INT64_MIN, INT64_MIN + 807])
def test_lower_band_returns_correct_pair_without_raising(nanos: int) -> None:
    """B1: the method is total. The pair is correct even at the very bottom."""
    moment, remainder = UtcNanos(nanos).to_datetime_with_remainder()
    assert moment == datetime(1677, 9, 21, 0, 12, 43, 145_224, tzinfo=UTC)
    assert 0 <= remainder <= 999
    # The mathematical identity holds, verified by integer arithmetic rather
    # than by a UtcNanos round trip, which is not available in this band.
    floored_microseconds = nanos // NS_PER_MICROSECOND
    assert floored_microseconds * NS_PER_MICROSECOND + remainder == nanos


@pytest.mark.parametrize("nanos", [INT64_MIN, INT64_MIN + 807])
def test_lower_band_floored_datetime_is_not_representable_as_utcnanos(nanos: int) -> None:
    """The documented limit: the datetime alone falls below INT64_MIN."""
    moment, _ = UtcNanos(nanos).to_datetime_with_remainder()
    with pytest.raises(TimeOverflowError):
        UtcNanos.from_datetime(moment)


def test_first_value_above_the_band_round_trips_normally() -> None:
    instant = UtcNanos(LOWEST_ALIGNED)
    moment, remainder = instant.to_datetime_with_remainder()
    assert remainder == 0
    assert UtcNanos.from_datetime(moment) == instant


def test_no_aligned_value_lies_inside_the_band() -> None:
    """Why to_datetime() is unaffected by the band."""
    assert not any(UtcNanos(n).is_microsecond_aligned for n in range(INT64_MIN, INT64_MIN + 808))
    assert UtcNanos(LOWEST_ALIGNED).is_microsecond_aligned is True


# --------------------------------------------------------------------------
# The datetime representation is output-only
# --------------------------------------------------------------------------


def test_distinct_instants_can_share_one_datetime() -> None:
    """Documented and intentional: datetime is not an identity or ordering key."""
    earlier, later = UtcNanos(1_710_163_800_123_456_001), UtcNanos(1_710_163_800_123_456_999)
    assert earlier != later
    assert earlier.to_datetime_with_remainder()[0] == later.to_datetime_with_remainder()[0]


def test_datetime_ordering_is_only_weakly_monotonic() -> None:
    """Sorting by datetime would silently reorder same-microsecond events."""
    earlier, later = UtcNanos(1_710_163_800_123_456_001), UtcNanos(1_710_163_800_123_456_999)
    assert earlier < later
    assert not earlier.to_datetime_with_remainder()[0] < later.to_datetime_with_remainder()[0]


# --------------------------------------------------------------------------
# TradeDate: valid construction
# --------------------------------------------------------------------------


def test_trade_date_exposes_its_components() -> None:
    trade_date = TradeDate(2024, 3, 11)
    assert (trade_date.year, trade_date.month, trade_date.day) == (2024, 3, 11)


def test_trade_date_to_date() -> None:
    assert TradeDate(2024, 3, 11).to_date() == date(2024, 3, 11)
    assert type(TradeDate(2024, 3, 11).to_date()) is date


def test_trade_date_isoformat_is_the_canonical_string() -> None:
    assert TradeDate(2024, 3, 11).isoformat() == "2024-03-11"


@pytest.mark.parametrize(
    ("year", "month", "day", "expected"),
    [(1, 1, 1, "0001-01-01"), (99, 3, 11, "0099-03-11"), (9999, 12, 31, "9999-12-31")],
)
def test_trade_date_isoformat_pads_to_four_digit_years(
    year: int, month: int, day: int, expected: str
) -> None:
    assert TradeDate(year, month, day).isoformat() == expected


def test_trade_date_isoformat_is_filesystem_safe() -> None:
    """It is a directory-name component in the stored partition layout."""
    rendered = TradeDate(2024, 3, 11).isoformat()
    assert "/" not in rendered
    assert "\\" not in rendered
    assert rendered == "2024-03-11"


@pytest.mark.parametrize(("year", "month", "day"), [(2024, 2, 29), (2000, 2, 29)])
def test_leap_days_are_accepted(year: int, month: int, day: int) -> None:
    assert TradeDate(year, month, day).to_date() == date(year, month, day)


def test_year_boundaries_are_accepted() -> None:
    assert TradeDate(1, 1, 1).to_date() == date(1, 1, 1)
    assert TradeDate(9999, 12, 31).to_date() == date(9999, 12, 31)


# --------------------------------------------------------------------------
# TradeDate: invalid Gregorian dates
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [
        (2023, 2, 29),  # not a leap year
        (1900, 2, 29),  # century non-leap year
        (2024, 2, 30),  # February never has 30 days
        (2024, 4, 31),  # April has 30
        (2024, 13, 1),  # month above range
        (2024, 0, 1),  # month below range
        (2024, 1, 0),  # day below range
        (2024, 1, 32),  # day above range
        (0, 1, 1),  # year below the representable range
        (10000, 1, 1),  # year above the representable range
        (-1, 1, 1),
    ],
)
def test_invalid_calendar_dates_raise(year: int, month: int, day: int) -> None:
    with pytest.raises(InvalidTradeDateError):
        TradeDate(year, month, day)


def test_invalid_trade_date_error_hierarchy() -> None:
    assert issubclass(InvalidTradeDateError, ValueError)
    assert issubclass(InvalidTradeDateError, OfaError)


# --------------------------------------------------------------------------
# TradeDate: type rejection
# --------------------------------------------------------------------------


def test_trade_date_rejects_bool_year() -> None:
    """date(True, 3, 11) would silently mean year 1."""
    with pytest.raises(TimeTypeError):
        TradeDate(True, 3, 11)


def test_trade_date_rejects_bool_month() -> None:
    """date(2024, True, 11) would silently mean January."""
    with pytest.raises(TimeTypeError):
        TradeDate(2024, True, 11)


def test_trade_date_rejects_bool_day() -> None:
    with pytest.raises(TimeTypeError):
        TradeDate(2024, 3, True)


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("bad", [2024.0, 3.5, "2024", None])
def test_trade_date_rejects_non_integer_components(position: int, bad: object) -> None:
    components: list[object] = [2024, 3, 11]
    components[position] = bad
    with pytest.raises(TimeTypeError):
        TradeDate(*components)  # type: ignore[arg-type]


def test_trade_date_rejects_a_datetime_component() -> None:
    with pytest.raises(TimeTypeError):
        TradeDate(datetime(2024, 3, 11, tzinfo=UTC), 3, 11)  # type: ignore[arg-type]


def test_trade_date_rejects_a_date_component() -> None:
    with pytest.raises(TimeTypeError):
        TradeDate(date(2024, 3, 11), 3, 11)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# TradeDate: value semantics
# --------------------------------------------------------------------------


def test_trade_date_is_immutable() -> None:
    trade_date = TradeDate(2024, 3, 11)
    with pytest.raises(AttributeError):
        trade_date.year = 2025  # type: ignore[misc]


def test_trade_date_equality_and_hashing() -> None:
    assert TradeDate(2024, 3, 11) == TradeDate(2024, 3, 11)
    assert TradeDate(2024, 3, 11) != TradeDate(2024, 3, 12)
    assert hash(TradeDate(2024, 3, 11)) == hash(TradeDate(2024, 3, 11))
    assert len({TradeDate(2024, 3, 11), TradeDate(2024, 3, 11), TradeDate(2024, 3, 12)}) == 2


def test_trade_date_is_not_equal_to_a_plain_date_or_tuple() -> None:
    assert TradeDate(2024, 3, 11) != date(2024, 3, 11)
    assert TradeDate(2024, 3, 11) != (2024, 3, 11)  # type: ignore[comparison-overlap]


def test_trade_date_ordering_is_chronological() -> None:
    assert TradeDate(2024, 3, 9) < TradeDate(2024, 3, 10)
    assert TradeDate(2024, 3, 31) < TradeDate(2024, 4, 1)
    assert TradeDate(2024, 12, 31) < TradeDate(2025, 1, 1)
    assert TradeDate(2024, 3, 11) <= TradeDate(2024, 3, 11)


def test_trade_date_is_not_comparable_to_utcnanos() -> None:
    with pytest.raises(TypeError):
        _ = TradeDate(2024, 3, 11) < UtcNanos(0)  # type: ignore[operator]


def test_trade_date_is_not_comparable_to_a_plain_date() -> None:
    with pytest.raises(TypeError):
        _ = TradeDate(2024, 3, 11) < date(2024, 3, 12)  # type: ignore[operator]


# --------------------------------------------------------------------------
# TradeDate: the prohibited conversions must stay absent
# --------------------------------------------------------------------------


def test_trade_date_has_no_conversion_or_wall_clock_methods() -> None:
    """Absence is the enforcement: a trading date is assigned, never derived."""
    for name in (
        "from_date",
        "from_datetime",
        "from_iso",
        "from_timestamp",
        "from_utc_nanos",
        "to_utc_nanos",
        "today",
        "now",
        "next",
        "previous",
        "__add__",
        "__sub__",
    ):
        assert not hasattr(TradeDate, name), f"TradeDate must not define {name}"


def test_utcnanos_still_has_no_trade_date_conversion() -> None:
    for name in ("to_trade_date", "trade_date", "from_trade_date"):
        assert not hasattr(UtcNanos, name), f"UtcNanos must not define {name}"
