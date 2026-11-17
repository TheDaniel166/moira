"""Inverse of the two admitted outer EOP taper branches."""
import pytest

from moira import julian
from moira._eclipse_interval import RationalInterval
from moira._eclipse_taper_inverse_bounds import (
    bound_post_eop_taper_tt_to_ut1, bound_pre_eop_taper_tt_to_ut1,
)
from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("historical,days", [(True, 30), (True, 180), (True, 360),
                                               (False, 30), (False, 180), (False, 360)])
def test_taper_inverse_iterations(planetary_reader, historical, days):
    data = julian.EOPRegistry._ensure_loaded()
    segment = julian.EOPRegistry._segment_bounds(min(data) if historical else max(data), data)
    ut = segment[0] - days if historical else segment[2] + days
    tt = _ut1_to_ephemeris_tt(ut, planetary_reader)
    provider = bound_pre_eop_taper_tt_to_ut1 if historical else bound_post_eop_taper_tt_to_ut1
    result = provider(planetary_reader, tt, RationalInterval(-0.001, 0.001))
    out = RationalInterval.point(tt) + result.output_offset_days
    for value in (tt - 0.0005, tt, tt + 0.0005):
        assert out.contains(_ephemeris_tt_to_ut1(value, planetary_reader))
    assert not result.inverse_uniqueness_certified
    assert not result.physical_delta_t_accuracy_certified
