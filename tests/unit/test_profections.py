from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from moira.profections import (
    LeapDayAnniversaryPolicy,
    profection_schedule,
)


def test_schedule_uses_civil_anniversary_not_fractional_julian_year() -> None:
    natal = datetime(2000, 7, 1, 12, 0, tzinfo=timezone.utc)
    current = datetime(2001, 7, 1, 12, 0, tzinfo=timezone.utc)

    result = profection_schedule(0.0, natal, current)

    assert result.age_years == 1
    assert result.age_basis == "civil_anniversary"


def test_schedule_compares_the_anniversary_in_the_natal_timezone() -> None:
    natal_zone = timezone(timedelta(hours=-5))
    natal = datetime(2000, 7, 1, 23, 0, tzinfo=natal_zone)
    before_local_anniversary = datetime(
        2001,
        7,
        2,
        3,
        30,
        tzinfo=timezone.utc,
    )

    result = profection_schedule(0.0, natal, before_local_anniversary)

    assert result.age_years == 0


def test_schedule_rejects_naive_or_prebirth_chronology() -> None:
    aware_natal = datetime(2000, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        profection_schedule(0.0, datetime(2000, 1, 1), aware_natal)
    with pytest.raises(ValueError, match="before natal"):
        profection_schedule(
            0.0,
            aware_natal,
            datetime(1999, 12, 31, 23, 59, tzinfo=timezone.utc),
        )


def test_february_29_anniversary_policy_is_explicit_and_divergent() -> None:
    natal = datetime(2000, 2, 29, 12, 0, tzinfo=timezone.utc)
    current = datetime(2001, 2, 28, 13, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="leap_day_policy"):
        profection_schedule(0.0, natal, current)

    february_28 = profection_schedule(
        0.0,
        natal,
        current,
        leap_day_policy=LeapDayAnniversaryPolicy.FEBRUARY_28,
    )
    march_1 = profection_schedule(
        0.0,
        natal,
        current,
        leap_day_policy=LeapDayAnniversaryPolicy.MARCH_1,
    )

    assert february_28.age_years == 1
    assert march_1.age_years == 0
    assert (
        february_28.leap_day_policy
        == LeapDayAnniversaryPolicy.FEBRUARY_28
    )
    assert march_1.leap_day_policy == LeapDayAnniversaryPolicy.MARCH_1
