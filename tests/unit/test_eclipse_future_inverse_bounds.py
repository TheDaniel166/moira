"""Post-handoff future native inverse iteration enclosure."""
import math
import pytest

from moira import julian
from moira._eclipse_future_inverse_bounds import bound_future_native_tt_to_ut1
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [2030, 2100, 2150, 2500, 3000])
def test_future_inverse_year_boundary(planetary_reader, year):
    ut = julian.julian_day(year, 1, 1)
    anchor = _ut1_to_ephemeris_tt(ut, planetary_reader)
    result = bound_future_native_tt_to_ut1(planetary_reader, anchor, RationalInterval(-0.01, 0.01))
    out = RationalInterval.point(anchor) + result.output_offset_days
    for tt in (anchor - 0.005, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 0.005):
        assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))
    assert not result.inverse_uniqueness_certified
    assert not result.physical_delta_t_accuracy_certified


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [1900, 2020, 2027])
def test_future_inverse_rejects_other_branches(planetary_reader, year):
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_future_native_tt_to_ut1(planetary_reader, julian.julian_day(year, 1, 1),
                                       RationalInterval(-0.1, 0.1))
