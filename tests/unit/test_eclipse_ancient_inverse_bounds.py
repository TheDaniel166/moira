"""Ancient inverse iteration controls."""
import math
import pytest

from moira import julian
from moira._eclipse_ancient_inverse_bounds import bound_ancient_native_tt_to_ut1
from moira._eclipse_interval import RationalInterval
from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-2900, -2500, -2101, -2100, -2099, -2050, -2001])
def test_ancient_inverse_polynomial_and_bridge(planetary_reader, year):
    ut = julian.julian_day(year, 1, 1)
    tt = _ut1_to_ephemeris_tt(ut, planetary_reader)
    result = bound_ancient_native_tt_to_ut1(planetary_reader, tt, RationalInterval(-0.01, 0.01))
    out = RationalInterval.point(tt) + result.output_offset_days
    for value in (tt - 0.005, math.nextafter(tt, -math.inf), tt,
                  math.nextafter(tt, math.inf), tt + 0.005):
        assert out.contains(_ephemeris_tt_to_ut1(value, planetary_reader))


@pytest.mark.requires_ephemeris
def test_ancient_inverse_hpiers_seam(planetary_reader):
    tt = julian.julian_day(-2000, 1, 1)
    result = bound_ancient_native_tt_to_ut1(planetary_reader, tt, RationalInterval(-1, 1))
    out = RationalInterval.point(tt) + result.output_offset_days
    for value in (tt - 1, math.nextafter(tt, -math.inf), tt,
                  math.nextafter(tt, math.inf), tt + 1):
        assert out.contains(_ephemeris_tt_to_ut1(value, planetary_reader))
