"""Native HPIERS inverse encloses initial and reader-bound iterations."""
import math
import pytest

from moira import julian
from moira._eclipse_historical_inverse_bounds import bound_historical_native_tt_to_ut1
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-1999, -500, 0, 1600, 1900, 1955, 1970])
def test_historical_inverse_year_boundary(planetary_reader, year):
    ut = julian.julian_day(year, 1, 1)
    anchor = _ut1_to_ephemeris_tt(ut, planetary_reader)
    result = bound_historical_native_tt_to_ut1(planetary_reader, anchor, RationalInterval(-0.01, 0.01))
    out = RationalInterval.point(anchor) + result.output_offset_days
    for tt in (anchor - 0.005, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 0.005):
        assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))
    assert not result.inverse_uniqueness_certified
    assert not result.physical_delta_t_accuracy_certified


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-2100, -2000, 1972, 2020, 3000])
def test_other_inverse_branches_fail_closed(planetary_reader, year):
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_historical_native_tt_to_ut1(planetary_reader, julian.julian_day(year, 1, 1),
                                           RationalInterval(-0.1, 0.1))

@pytest.mark.requires_ephemeris
def test_first_eop_seed_guard_and_source_replacement(planetary_reader, monkeypatch):
    data = julian.EOPRegistry._ensure_loaded()
    first_label = 2400000.5 + min(data)
    with pytest.raises(NativeClockBoundsUnavailable, match="initial inverse might use EOP"):
        bound_historical_native_tt_to_ut1(planetary_reader, first_label - 4,
                                           RationalInterval.point(0))
    monkeypatch.setattr(julian, "delta_t_from_jd", lambda _jd: 0.0)
    with pytest.raises(NativeClockBoundsUnavailable, match="source changed"):
        bound_historical_native_tt_to_ut1(planetary_reader, julian.julian_day(1900, 1, 1),
                                           RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_actual_early_fixed_point_is_enclosed(planetary_reader):
    from moira._ephemeris_time import _ephemeris_delta_t
    tt = _ut1_to_ephemeris_tt(julian.julian_day(1900, 6, 1), planetary_reader)
    current = julian.tt_to_ut(tt)
    for _ in range(12):
        next_ut = tt - _ephemeris_delta_t(current, planetary_reader).seconds / 86400.0
        if next_ut == current:
            break
        current = next_ut
    else:
        pytest.fail("control did not reach the expected early equality")
    receipt = bound_historical_native_tt_to_ut1(planetary_reader, tt, RationalInterval.point(0))
    assert (RationalInterval.point(tt) + receipt.output_offset_days).contains(current)
