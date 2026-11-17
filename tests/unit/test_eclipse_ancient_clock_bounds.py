"""Ancient native clock enclosures on the real DE441 tidal basis."""
import math

import pytest

from moira import julian
from moira._eclipse_ancient_clock_bounds import bound_ancient_native_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-2900, -2500, -2200, -2101, -2100, -2099, -2050, -2001])
def test_ancient_polynomial_and_bridge(planetary_reader, year):
    anchor = julian.julian_day(year, 1, 1)
    result = bound_ancient_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1, 1))
    out = RationalInterval.point(anchor) + result.output_offset_days
    for jd in (anchor - 1, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 1):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
def test_hpiers_seam_is_explicitly_unavailable(planetary_reader):
    with pytest.raises(NativeClockBoundsUnavailable, match="HPIERS table branch"):
        bound_ancient_native_ut1_to_tt(planetary_reader, julian.julian_day(-2000, 1, 1),
                                        RationalInterval(-1, 1))


def test_two_term_fsum_enclosure_has_extra_neighbor_and_covers_omitted_zero():
    from moira._eclipse_ancient_clock_bounds import _fsum_bounds

    p = RationalInterval.point
    result = _fsum_bounds(p(1.0), p(0.0))
    assert result.contains(math.nextafter(1.0, -math.inf))
    assert result.contains(math.nextafter(1.0, math.inf))
    assert result.contains(math.fsum((1.0,)))
