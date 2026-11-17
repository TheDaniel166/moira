"""Future deterministic native clock enclosures, not physical error bounds."""
import math

import pytest

from moira import julian
from moira._eclipse_future_clock_bounds import bound_future_native_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [2030, 2050, 2150, 2200, 2500, 3000])
def test_future_scenario_year_edges(planetary_reader, year):
    anchor = julian.julian_day(year, 1, 1)
    bounds = bound_future_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1, 1))
    out = RationalInterval.point(anchor) + bounds.output_offset_days
    for jd in (anchor - 1, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 1):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))
    assert not bounds.physical_delta_t_accuracy_certified
    assert not bounds.source_and_arithmetic_attested


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [1900, 2020, 2026])
def test_pre_future_or_handoff_is_unavailable(planetary_reader, year):
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_future_native_ut1_to_tt(planetary_reader, julian.julian_day(year, 1, 1),
                                      RationalInterval.point(0))

@pytest.mark.requires_ephemeris
def test_future_cutoff_tracks_actual_window(planetary_reader, monkeypatch):
    from moira import _eclipse_native_clock_bounds as native

    monkeypatch.setattr(julian, "_EOP_HANDOFF_WINDOW_DAYS", 100000.0)
    monkeypatch.setattr(native, "_CONSTANTS", (*native._CONSTANTS[:3], 100000.0))
    with pytest.raises(NativeClockBoundsUnavailable, match="EOP handoff"):
        bound_future_native_ut1_to_tt(planetary_reader, julian.julian_day(2200, 1, 1),
                                      RationalInterval.point(0))
    bound_future_native_ut1_to_tt(planetary_reader, julian.julian_day(2500, 1, 1),
                                  RationalInterval.point(0))
