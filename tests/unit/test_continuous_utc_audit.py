"""Continuous-UTC invariants (effective 2027-05-20): no new leap seconds, |UT1-UTC| up to 3600 s."""
import pytest

from moira.julian import (
    EOPRegistry,
    LEAP_SECONDS,
    _ut1_to_utc,
    datetime_from_jd,
    tai_minus_utc,
    utc_to_ut1,
)

_MJD = 61400
_TABLES = {
    "const+3600": lambda i: 3600.0,
    "const-3600": lambda i: -3600.0,
    "ramp-3600": lambda i: -3600.0 * i / 60,
    "ramp+3600": lambda i: 3600.0 * i / 60,
    "realistic": lambda i: -0.05 - 0.0001 * i,
}


@pytest.fixture(params=sorted(_TABLES))
def table(request, monkeypatch):
    data = {_MJD + i: _TABLES[request.param](i) for i in range(61)}
    monkeypatch.setattr(EOPRegistry, "_data", data)
    return request.param, data


def test_tai_minus_utc_is_constant_after_last_leap_second() -> None:
    last_jd, last_offset = LEAP_SECONDS[-1]
    for years in (0.0, 1.0, 14.0, 70.0):
        assert tai_minus_utc(last_jd + 365.25 * years + 0.5) == last_offset


def test_utc_ut1_round_trip_and_delta_t_continuity(table) -> None:
    _, data = table
    n, lo, hi = 3000, _MJD + 1, _MJD + 59
    prev = None
    for i in range(n):
        jd = lo + 2400000.5 + (hi - lo) * i / n + 0.00013
        ut1 = utc_to_ut1(jd)
        assert abs(_ut1_to_utc(ut1) - jd) * 86400 < 1e-3
        delta_t = EOPRegistry._delta_t_from_ut1(ut1)
        assert delta_t is not None
        if prev is not None:
            # Fastest ramp is 60 s/day; sampling step is (hi-lo)/n days.
            assert abs(delta_t - prev) < 60.0 * (hi - lo) / n * 1.05 + 1e-6
        prev = delta_t


def test_civil_date_survives_ut1_round_trip_near_midnight(table) -> None:
    # An hour of DUT1 moves UT1 across the civil-day boundary; the UTC label must not move.
    for fraction in (0.0001, 0.5, 0.9791, 0.99999):
        jd_utc = _MJD + 20 + 2400000.5 + fraction
        back = datetime_from_jd(_ut1_to_utc(utc_to_ut1(jd_utc)))
        assert back == datetime_from_jd(jd_utc)


def test_bundled_data_is_continuous_past_last_eop_row() -> None:
    last = max(EOPRegistry._ensure_loaded())
    previous = None
    for k in range(-5, 800):
        jd = last + 2400000.5 + k
        dut1 = (utc_to_ut1(jd) - jd) * 86400
        assert abs(_ut1_to_utc(utc_to_ut1(jd)) - jd) * 86400 < 1e-3
        if previous is not None:
            assert abs(dut1 - previous) < 0.01
        previous = dut1
