"""First-EOP HPIERS taper controls."""
import math
import pytest

from moira import julian
from moira._eclipse_historical_taper_bounds import bound_pre_eop_hpiers_taper_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("days", [1, 30, 180, 360])
def test_pre_eop_taper_values(planetary_reader, days):
    data = julian.EOPRegistry._ensure_loaded()
    first = julian.EOPRegistry._segment_bounds(min(data), data)[0]
    anchor = first - days
    receipt = bound_pre_eop_hpiers_taper_ut1_to_tt(planetary_reader, anchor, RationalInterval(-0.1, 0.1))
    out = RationalInterval.point(anchor) + receipt.output_offset_days
    for jd in (anchor - 0.05, anchor, anchor + 0.05):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
def test_pre_eop_taper_endpoints(planetary_reader):
    data = julian.EOPRegistry._ensure_loaded()
    first = julian.EOPRegistry._segment_bounds(min(data), data)[0]
    start = first - julian._EOP_HANDOFF_WINDOW_DAYS
    for jd in (start, math.nextafter(start, math.inf), math.nextafter(first, -math.inf), first):
        receipt = bound_pre_eop_hpiers_taper_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
        assert (RationalInterval.point(jd) + receipt.output_offset_days).contains(
            _ut1_to_ephemeris_tt(jd, planetary_reader)
        )
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_pre_eop_hpiers_taper_ut1_to_tt(planetary_reader, first, RationalInterval(-1, 1))
