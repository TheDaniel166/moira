"""Annual and HPIERS bridge clock controls without EOP observations."""
import math
import pytest

from moira import julian
from moira._eclipse_annual_clock_bounds import bound_annual_no_eop_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,month", [(2015, 2), (2015, 6), (2016, 1), (2018, 1), (2023, 7)])
def test_no_eop_annual_and_bridge(planetary_reader, monkeypatch, year, month):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {})
    anchor = julian.julian_day(year, month, 1)
    result = bound_annual_no_eop_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1, 1))
    out = RationalInterval.point(anchor) + result.output_offset_days
    for jd in (anchor - 1, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 1):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
def test_nonempty_eop_fails_closed(planetary_reader):
    with pytest.raises(NativeClockBoundsUnavailable, match="empty EOP"):
        bound_annual_no_eop_ut1_to_tt(planetary_reader, julian.julian_day(2018, 1, 1),
                                      RationalInterval.point(0))
