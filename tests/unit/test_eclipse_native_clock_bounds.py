"""Conditional historical native clock bounds against the real DE441 clock."""
from __future__ import annotations

from fractions import Fraction
import math
import sys

import pytest

from moira import julian
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import (
    NativeClockBoundsUnavailable, bound_historical_native_ut1_to_tt,
)
from moira._ephemeris_time import _ut1_to_ephemeris_tt


def absolute(bounds):
    return RationalInterval.point(bounds.anchor_jd) + bounds.output_offset_days


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-1999, -1500, -500, 0, 500, 1000, 1600, 1800, 1900, 1955, 1970])
def test_de441_year_boundary_and_neighbors(planetary_reader, year):
    anchor = julian.julian_day(year, 1, 1)
    bounds = bound_historical_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1, 1))
    assert bounds.successful_outputs_only
    assert not bounds.source_and_arithmetic_attested
    assert not bounds.coverage_success_guaranteed
    assert not bounds.physical_delta_t_accuracy_certified
    assert not bounds.inverse_enclosed
    for jd in (anchor - 1, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 1):
        assert absolute(bounds).contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-1900, -1000, -100, 100, 1500, 1700, 1850, 1920, 1960])
def test_hpiers_knots(planetary_reader, year):
    anchor = julian.julian_day(year, 1, 1)
    bounds = bound_historical_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-0.1, 0.1))
    for jd in (anchor - 0.1, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 0.1):
        assert absolute(bounds).contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [-2100, -2000, 1972, 2020, 3000])
def test_unsupported_source_epochs_fail_closed(planetary_reader, year):
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_historical_native_ut1_to_tt(planetary_reader, julian.julian_day(year, 1, 1),
                                          RationalInterval(-1, 1))


@pytest.mark.requires_ephemeris
def test_reader_and_source_changes_are_rejected(planetary_reader, monkeypatch):
    anchor = julian.julian_day(1900, 1, 1)
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_historical_native_ut1_to_tt(object(), anchor, RationalInterval.point(0))
    monkeypatch.setattr(julian, "_DELTA_T_HPIERS_2016", tuple(list(julian._DELTA_T_HPIERS_2016)))
    with pytest.raises(NativeClockBoundsUnavailable, match="source changed"):
        bound_historical_native_ut1_to_tt(planetary_reader, anchor, RationalInterval.point(0))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("anchor,offset", [(sys.float_info.max, 0), (-sys.float_info.max, 0),
                                            (2451545.0, Fraction(10)**1000)])
def test_large_input_fails_closed(planetary_reader, anchor, offset):
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_historical_native_ut1_to_tt(planetary_reader, anchor, RationalInterval.point(offset))

@pytest.mark.requires_ephemeris
def test_handoff_cutoff_tracks_larger_source_window(planetary_reader, monkeypatch):
    from moira import _eclipse_native_clock_bounds as native

    # Model an unchanged source imported with a larger EOP taper window.
    monkeypatch.setattr(julian, "_EOP_HANDOFF_WINDOW_DAYS", 100000.0)
    constants = (*native._CONSTANTS[:3], 100000.0)
    monkeypatch.setattr(native, "_CONSTANTS", constants)
    with pytest.raises(NativeClockBoundsUnavailable, match="EOP handoff"):
        native.bound_historical_native_ut1_to_tt(
            planetary_reader, julian.julian_day(1800, 1, 1), RationalInterval.point(0)
        )
    native.bound_historical_native_ut1_to_tt(
        planetary_reader, julian.julian_day(1500, 1, 1), RationalInterval.point(0)
    )
