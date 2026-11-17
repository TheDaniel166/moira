"""Conditional future-side EOP taper controls."""
import pytest

from moira import julian
from moira._eclipse_future_taper_bounds import bound_post_eop_future_taper_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("days", [1, 30, 180, 360])
def test_post_eop_taper_values(planetary_reader, days):
    data = julian.EOPRegistry._ensure_loaded()
    last = julian.EOPRegistry._segment_bounds(max(data), data)[2]
    anchor = last + days
    receipt = bound_post_eop_future_taper_ut1_to_tt(planetary_reader, anchor, RationalInterval(-0.1, 0.1))
    out = RationalInterval.point(anchor) + receipt.output_offset_days
    for jd in (anchor - 0.05, anchor, anchor + 0.05):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
def test_post_eop_boundary_crossing_is_unavailable(planetary_reader):
    data = julian.EOPRegistry._ensure_loaded()
    last = julian.EOPRegistry._segment_bounds(max(data), data)[2]
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_post_eop_future_taper_ut1_to_tt(planetary_reader, last, RationalInterval(-1, 1))

@pytest.mark.requires_ephemeris
def test_taper_exact_endpoints_and_rounding_neighbors(planetary_reader):
    import math

    data = julian.EOPRegistry._ensure_loaded()
    last = julian.EOPRegistry._segment_bounds(max(data), data)[2]
    end = last + julian._EOP_HANDOFF_WINDOW_DAYS
    for jd in (last, math.nextafter(last, math.inf), math.nextafter(end, -math.inf), end):
        result = bound_post_eop_future_taper_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
        assert (RationalInterval.point(jd) + result.output_offset_days).contains(
            _ut1_to_ephemeris_tt(jd, planetary_reader)
        )
    after = math.nextafter(end, math.inf)
    result = bound_post_eop_future_taper_ut1_to_tt(planetary_reader, after, RationalInterval.point(0))
    assert (RationalInterval.point(after) + result.output_offset_days).contains(
        _ut1_to_ephemeris_tt(after, planetary_reader)
    )


@pytest.mark.requires_ephemeris
def test_taper_non_neutral_boundary_fails_closed(planetary_reader, monkeypatch):
    mjd = int(julian.julian_day(1960, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {mjd: 0.1})
    last = julian.EOPRegistry._segment_bounds(mjd, julian.EOPRegistry._data)[2]
    with pytest.raises(NativeClockBoundsUnavailable, match="not future-model neutral"):
        bound_post_eop_future_taper_ut1_to_tt(planetary_reader, last + 1, RationalInterval.point(0))
