"""Conditional enclosure of the direct daily EOP clock."""
import math

import pytest

from moira import julian
from moira._eclipse_eop_clock_bounds import bound_direct_eop_ut1_to_tt
from moira._eclipse_clock_provider import bound_native_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,month,day", [(1973, 1, 5), (1999, 8, 11), (2000, 1, 1),
                                             (2016, 12, 31), (2024, 4, 8)])
def test_direct_eop_day_and_leap_edges(planetary_reader, year, month, day):
    anchor = julian.julian_day(year, month, day)
    bounds = bound_direct_eop_ut1_to_tt(planetary_reader, anchor, RationalInterval(-0.9, 0.9))
    out = RationalInterval.point(anchor) + bounds.output_offset_days
    for jd in (anchor - 0.9, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 0.9):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))
    assert not bounds.physical_delta_t_accuracy_certified
    assert not bounds.inverse_enclosed


@pytest.mark.requires_ephemeris
def test_eop_terminal_boundary_and_gap_are_rejected(planetary_reader):
    data = julian.EOPRegistry._ensure_loaded()
    final = julian.EOPRegistry._segment_bounds(max(data), data)[2]
    with pytest.raises(NativeClockBoundsUnavailable, match="fully cover"):
        bound_direct_eop_ut1_to_tt(planetary_reader, final, RationalInterval.point(0))
    with pytest.raises(NativeClockBoundsUnavailable, match="fully cover"):
        bound_direct_eop_ut1_to_tt(planetary_reader, final, RationalInterval(-1, 1))
    with pytest.raises(NativeClockBoundsUnavailable, match="fully cover"):
        bound_direct_eop_ut1_to_tt(planetary_reader, julian.julian_day(3000, 1, 1),
                                   RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_exact_eop_knot_uses_following_segment(planetary_reader):
    data = julian.EOPRegistry._ensure_loaded()
    knot = julian.EOPRegistry._segment_bounds(58000, data)[0]
    bounds = bound_direct_eop_ut1_to_tt(planetary_reader, knot, RationalInterval.point(0))
    out = RationalInterval.point(knot) + bounds.output_offset_days
    assert out.contains(_ut1_to_ephemeris_tt(knot, planetary_reader))

@pytest.mark.requires_ephemeris
def test_isolated_eop_rows_and_internal_gap(planetary_reader, monkeypatch):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: -0.2})
    data = julian.EOPRegistry._ensure_loaded()
    first = julian.EOPRegistry._segment_bounds(58000, data)
    start, end = first[0], first[2]
    inner = (start + end) / 2
    result = bound_direct_eop_ut1_to_tt(planetary_reader, inner, RationalInterval.point(0))
    assert (RationalInterval.point(inner) + result.output_offset_days).contains(
        _ut1_to_ephemeris_tt(inner, planetary_reader)
    )
    for jd in (end, math.nextafter(end, math.inf), end + 0.5):
        with pytest.raises(NativeClockBoundsUnavailable, match="fully cover"):
            bound_direct_eop_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
    before = math.nextafter(end, -math.inf)
    assert (RationalInterval.point(before) + bound_direct_eop_ut1_to_tt(
        planetary_reader, before, RationalInterval.point(0)
    ).output_offset_days).contains(_ut1_to_ephemeris_tt(before, planetary_reader))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,month,day", [(1999, 8, 11), (2016, 12, 31), (2024, 4, 8)])
def test_conditional_direct_eop_totality_covers_actual_serving_path(planetary_reader, year, month, day):
    anchor = julian.julian_day(year, month, day)
    offset = RationalInterval(-0.9, 0.9)
    result = bound_native_ut1_to_tt(planetary_reader, anchor, offset, require_totality=True)
    bounds = result.bounds
    assert result.branch == "direct_eop"
    assert bounds.forward_totality_conditionally_proved
    assert bounds.successful_outputs_only
    assert bounds.unchanged_eop_leap_and_source_dependencies_required
    assert bounds.normal_binary64_arithmetic_required
    assert not bounds.source_and_arithmetic_attested
    assert not bounds.physical_delta_t_accuracy_certified
    output = RationalInterval.point(anchor) + bounds.output_offset_days
    for jd in (anchor - 0.9, math.nextafter(anchor, -math.inf), anchor,
               math.nextafter(anchor, math.inf), anchor + 0.9):
        product = julian._resolve_delta_t_for_ut1(jd)
        assert product.source_product == "iers_eop_direct"
        assert product.retarget_mode == "basis_neutral"
        assert output.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))
    default = bound_direct_eop_ut1_to_tt(planetary_reader, anchor, offset)
    assert not default.forward_totality_conditionally_proved


@pytest.mark.requires_ephemeris
def test_conditional_totality_does_not_cross_missing_eop_rows(planetary_reader, monkeypatch):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: -0.2})
    end = julian.EOPRegistry._segment_bounds(58000, julian.EOPRegistry._ensure_loaded())[2]
    with pytest.raises(NativeClockBoundsUnavailable, match="fully cover"):
        bound_native_ut1_to_tt(planetary_reader, end, RationalInterval.point(0),
                               require_totality=True)


@pytest.mark.requires_ephemeris
def test_conditional_totality_rejects_unbounded_ut1(planetary_reader):
    with pytest.raises(NativeClockBoundsUnavailable, match="outside source domain"):
        bound_native_ut1_to_tt(planetary_reader, 40_000_001.0,
                               RationalInterval.point(0), require_totality=True)


@pytest.mark.requires_ephemeris
def test_conditional_totality_rejects_changed_dependency(planetary_reader, monkeypatch):
    anchor = julian.julian_day(2024, 4, 8)
    original = julian.tai_minus_utc
    monkeypatch.setattr(julian, "tai_minus_utc", lambda jd: original(jd))
    with pytest.raises(NativeClockBoundsUnavailable, match="totality source changed"):
        bound_native_ut1_to_tt(planetary_reader, anchor, RationalInterval.point(0),
                               require_totality=True)


@pytest.mark.requires_ephemeris
def test_conditional_totality_spans_2017_leap_boundary_knot(planetary_reader):
    data = julian.EOPRegistry._ensure_loaded()
    knot = julian.EOPRegistry._segment_bounds(57754, data)[0]
    radius = RationalInterval(-0.001, 0.001)
    bounds = bound_native_ut1_to_tt(
        planetary_reader, knot, radius, require_totality=True,
    ).bounds
    assert bounds.forward_totality_conditionally_proved
    output = RationalInterval.point(knot) + bounds.output_offset_days
    for jd in (math.nextafter(knot, -math.inf), knot, math.nextafter(knot, math.inf)):
        assert radius.contains(jd - knot)
        assert julian._resolve_delta_t_for_ut1(jd).source_product == "iers_eop_direct"
        assert output.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))
