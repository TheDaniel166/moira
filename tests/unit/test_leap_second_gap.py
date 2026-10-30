"""UT1 instants inside an inserted leap second (invariant and authority validation).

A UTC-coded Julian Day has 86400 seconds per day, so 23:59:60 has no label and
``utc_to_tt`` steps by one second at the leap boundary.  ``_ut1_to_utc`` used to alternate
between the two sides of that step: the label ran backwards in time and the round trip
through TT was one second out.  The rule is now monotone and nearest-boundary, so the round
trip is off by at most 0.5 s, and only inside that one second.  Timing never uses the
label: ET comes from TT (``tt_to_tdb(ut_to_tt(...))``).  Checked at five leap seconds
(EOP-covered and pre-EOP), one-millisecond steps.

Civil display: ``utc_calendar_from_ut1`` shows the real ``23:59:60.x`` (``CalendarDateTime``
and RFC 3339 allow it); ``utc_datetime_from_ut1`` cannot, and takes the nearest-boundary label.

Authority for ET: SPICE ``str2et`` on the real ``... 23:59:60.x UTC`` string with the pinned
``naif0012.tls``; measured agreement of Moira's TT-derived ET 0.04 ms (binary64 Julian-day
quantisation), against up to 450 ms for a route through the UTC label.
"""
import math
from pathlib import Path

import pytest

from moira import julian as J
from moira.lunar_limb import _default_cache_root

# (effective JD of the post-leap day, UTC date string of the leap day for str2et)
_LEAPS = (
    (2457754.5, "2016-12-31"),
    (2457204.5, "2015-06-30"),
    (2456109.5, "2012-06-30"),
    (2441683.5, "1972-12-31"),  # before the bundled EOP data: Delta-T model path
    (2441499.5, "1972-06-30"),
)


def _gap_tt_bounds(leap_jd: float):
    index = [i for i, (jd, _) in enumerate(J.LEAP_SECONDS) if jd == leap_jd][0]
    pre, post = J.LEAP_SECONDS[index - 1][1], J.LEAP_SECONDS[index][1]
    return (
        leap_jd + (pre + J.TAI_TT_OFFSET) / 86400.0,
        leap_jd + (post + J.TAI_TT_OFFSET) / 86400.0,
    )


@pytest.mark.parametrize(("leap_jd", "_label"), _LEAPS)
def test_gap_label_is_monotone_and_within_half_a_second(leap_jd, _label) -> None:
    start_tt, end_tt = _gap_tt_bounds(leap_jd)
    start_ut1 = J.tt_to_ut(start_tt)
    previous_label = -math.inf
    in_gap = 0
    for step in range(-2500, 3500):
        ut1 = start_ut1 + step * 0.001 / 86400.0
        label = J._ut1_to_utc(ut1)
        assert label >= previous_label, "UTC label must never run backwards"
        previous_label = label
        error_s = abs(J.utc_to_tt(label) - J.ut_to_tt(ut1)) * 86400.0
        if J._leap_second_gap_utc(ut1) is not None:
            in_gap += 1
            assert error_s <= 0.5 + 1e-3
        else:
            assert error_s < 1e-3, "outside the gap the round trip stays at the clock's own precision"
    assert 995 <= in_gap <= 1005, "the gap is one second long"


@pytest.mark.parametrize(("leap_jd", "_label"), _LEAPS)
def test_gap_halves_take_the_nearest_boundary(leap_jd, _label) -> None:
    start_tt, end_tt = _gap_tt_bounds(leap_jd)
    early = J.tt_to_ut(start_tt + 0.2 / 86400.0)
    late = J.tt_to_ut(start_tt + 0.8 / 86400.0)
    assert J._ut1_to_utc(early) == math.nextafter(leap_jd, -math.inf)
    assert J._ut1_to_utc(late) == leap_jd
    # The labels sit on the two sides of the TT step.
    assert J.utc_to_tt(J._ut1_to_utc(early)) < J.utc_to_tt(J._ut1_to_utc(late))


def test_instants_away_from_a_leap_second_are_not_in_the_gap() -> None:
    for jd_utc in (J.julian_day(2000, 1, 1, 12.0), J.julian_day(2016, 12, 31, 12.0), J.julian_day(2018, 1, 1, 0.0)):
        assert J._leap_second_gap_utc(J.utc_to_ut1(jd_utc)) is None
    assert J._leap_second_gap_utc(100.0) is None


def _loaded_lsk_or_skip():
    sp = pytest.importorskip("spiceypy")
    lsk = Path(_default_cache_root()) / "kernels" / "naif0012.tls"
    if not lsk.exists():
        pytest.skip("pinned naif0012.tls is not cached locally")
    sp.kclear()
    sp.furnsh(str(lsk))
    return sp


@pytest.mark.parametrize(("leap_jd", "label"), _LEAPS)
@pytest.mark.parametrize("fraction", (0.05, 0.3, 0.55, 0.95))
def test_et_inside_leap_second_matches_spice_str2et(leap_jd, label, fraction) -> None:
    sp = _loaded_lsk_or_skip()
    start_tt, _ = _gap_tt_bounds(leap_jd)
    ut1 = J.tt_to_ut(start_tt + fraction / 86400.0)
    expected = sp.str2et(f"{label} 23:59:{60 + fraction:012.9f} UTC")
    moira_et = (J.tt_to_tdb(J.ut_to_tt(ut1)) - J.J2000) * 86400.0
    assert moira_et == pytest.approx(expected, abs=1.0e-4)



@pytest.mark.parametrize(("leap_jd", "label"), _LEAPS)
@pytest.mark.parametrize("fraction", (0.0, 0.25, 0.5, 0.9))
def test_civil_calendar_shows_the_real_leap_second(leap_jd, label, fraction) -> None:
    start_tt, _ = _gap_tt_bounds(leap_jd)
    ut1 = J.tt_to_ut(start_tt + fraction / 86400.0)
    civil = J.utc_calendar_from_ut1(ut1)
    assert civil.is_leap_second
    assert (civil.hour, civil.minute, civil.second) == (23, 59, 60)
    assert civil.date_string() == label
    # The fraction of the leap second is the real elapsed time from TT (float-JD precision ~40 us).
    assert civil.microsecond / 1e6 == pytest.approx(fraction, abs=2.0e-4)
    assert civil.isoformat().startswith(f"{label}T23:59:60.")
    assert J.format_calendar_utc(civil, include_seconds=True) == f"{label} 23:59:60 UTC"
    # datetime cannot hold second 60: it keeps the nearest-boundary label, within half a second.
    clamped = J.utc_datetime_from_ut1(ut1)
    assert J.safe_utc_datetime_from_ut1(ut1) == clamped
    assert clamped == J.datetime_from_jd(J._ut1_to_utc(ut1))


def test_civil_calendar_is_unchanged_outside_a_leap_second() -> None:
    for jd_utc in (J.julian_day(2000, 1, 1, 12.0), J.julian_day(2017, 1, 1, 0.5), J.julian_day(2016, 12, 31, 12.0)):
        ut1 = J.utc_to_ut1(jd_utc)
        civil = J.utc_calendar_from_ut1(ut1)
        assert not civil.is_leap_second
        assert civil == J.calendar_datetime_from_jd(J._ut1_to_utc(ut1))
        moment = J.utc_datetime_from_ut1(ut1)
        assert (moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second, moment.microsecond) == (
            civil.year, civil.month, civil.day, civil.hour, civil.minute, civil.second, civil.microsecond
        )


def test_civil_calendar_runs_forward_through_the_leap_second() -> None:
    """Seconds shown across a leap second never go backwards (...:59.9 -> :60.x -> 00:00.x)."""
    start_tt, _ = _gap_tt_bounds(2457754.5)
    start_ut1 = J.tt_to_ut(start_tt)
    previous = None
    for step in range(-1500, 2500):
        civil = J.utc_calendar_from_ut1(start_ut1 + step * 0.001 / 86400.0)
        key = (civil.year, civil.month, civil.day, civil.hour, civil.minute, civil.second, civil.microsecond)
        if previous is not None:
            assert key >= previous, "civil time must not run backwards"
        previous = key
