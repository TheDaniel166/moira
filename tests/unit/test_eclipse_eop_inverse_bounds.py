"""Direct-EOP native inverse interval controls."""
import math
import pytest

from moira import julian
from moira._eclipse_eop_inverse_bounds import bound_direct_eop_tt_to_ut1
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,month,day", [(1975, 1, 1), (2000, 1, 1), (2016, 12, 31), (2024, 4, 8)])
def test_eop_inverse_contains_actual_iterations(planetary_reader, year, month, day):
    ut = julian.julian_day(year, month, day)
    anchor = _ut1_to_ephemeris_tt(ut, planetary_reader)
    result = bound_direct_eop_tt_to_ut1(planetary_reader, anchor, RationalInterval(-0.01, 0.01))
    out = RationalInterval.point(anchor) + result.output_offset_days
    for tt in (anchor - 0.005, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 0.005):
        assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))
    assert not result.inverse_uniqueness_certified
    assert not result.physical_delta_t_accuracy_certified


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [1900, 3000])
def test_non_eop_inverse_is_unavailable(planetary_reader, year):
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_direct_eop_tt_to_ut1(planetary_reader, julian.julian_day(year, 1, 1),
                                    RationalInterval.point(0))
