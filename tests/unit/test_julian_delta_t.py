from __future__ import annotations

import pytest

from moira.julian import (
    calendar_datetime_from_jd,
    decimal_year,
    decimal_year_from_jd,
    delta_t,
    delta_t_nasa_canon,
    datetime_from_jd,
    julian_day,
    safe_datetime_from_jd,
    ut_to_tt,
)


def test_decimal_year_uses_mid_month_convention() -> None:
    assert decimal_year(2000, 1) == 2000.0416666666667
    assert decimal_year(2000, 7) == 2000.5416666666667


def test_decimal_year_from_jd_tracks_calendar_month() -> None:
    jd = julian_day(2000, 7, 1, 0.0)
    assert decimal_year_from_jd(jd) == 2000.5416666666667


def test_delta_t_interpolates_observed_table() -> None:
    assert abs(delta_t(1962.5) - 34.45) < 1e-9


def test_delta_t_uses_historical_anchor_table_before_1955() -> None:
    assert abs(delta_t(1900.0) - (-1.98)) < 1e-9
    assert abs(delta_t(1950.0) - 29.12) < 1e-9
    assert abs(delta_t(-500.0) - 16800.0) < 1e-9


def test_delta_t_interpolates_historical_anchor_table() -> None:
    assert abs(delta_t(1925.0) - 23.79) < 1e-9


def test_ut_to_tt_uses_decimal_year_not_integer_year_only() -> None:
    jd = julian_day(2150, 7, 1, 0.0)
    tt_decimal = ut_to_tt(jd)
    tt_integer = ut_to_tt(jd, year=2150.0)
    assert abs((tt_decimal - tt_integer) * 86400.0) > 0.1


def test_nasa_canon_delta_t_matches_catalog_basis_for_ancient_eclipse_year() -> None:
    assert abs(delta_t_nasa_canon(-1800.67) - 41747.0) < 1.0


def test_calendar_datetime_from_jd_supports_bce_years() -> None:
    jd = julian_day(-1321, 7, 20, 0.0)
    cal = calendar_datetime_from_jd(jd)
    assert cal.year == -1321
    assert cal.month == 8
    assert cal.day == 1
    assert cal.isoformat().startswith("-1321-08-01T00:00:00")


def test_safe_datetime_from_jd_returns_none_for_bce() -> None:
    jd = julian_day(-500, 1, 1, 0.0)
    assert safe_datetime_from_jd(jd) is None


def test_datetime_from_jd_raises_helpful_error_for_bce() -> None:
    jd = julian_day(-500, 1, 1, 0.0)
    with pytest.raises(ValueError, match="calendar_datetime_from_jd"):
        datetime_from_jd(jd)
