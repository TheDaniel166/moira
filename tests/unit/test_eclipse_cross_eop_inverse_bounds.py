"""Cross-source native inverse around outer EOP boundaries."""
import math
import pytest

from moira import julian
from moira._eclipse_cross_eop_inverse_bounds import bound_cross_eop_tt_to_ut1
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ephemeris_tt_to_ut1


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("first", [True, False])
def test_outer_eop_inverse_seeds_and_adjacent_floats(planetary_reader, first):
    data = julian.EOPRegistry._ensure_loaded()
    segment = julian.EOPRegistry._segment_bounds(min(data) if first else max(data), data)
    boundary = (segment[0] + segment[1] / 86400 if first else segment[2] + segment[3] / 86400)
    for tt in (math.nextafter(boundary, -math.inf), boundary,
               math.nextafter(boundary, math.inf)):
        result = bound_cross_eop_tt_to_ut1(planetary_reader, tt, RationalInterval.point(0))
        assert (RationalInterval.point(tt) + result.output_offset_days).contains(
            _ephemeris_tt_to_ut1(tt, planetary_reader)
        )


@pytest.mark.requires_ephemeris
def test_mixed_tt_seed_interval_remains_unavailable(planetary_reader):
    data = julian.EOPRegistry._ensure_loaded()
    s = julian.EOPRegistry._segment_bounds(min(data), data)
    tt = s[0] + s[1] / 86400
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_cross_eop_tt_to_ut1(planetary_reader, tt, RationalInterval(-0.01, 0.01))
