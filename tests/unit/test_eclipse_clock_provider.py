"""Provider receipt covers an entire admitted branch or fails closed."""
import pytest

from moira import julian
from moira._eclipse_clock_provider import bound_native_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,branch", [(-2500, "ancient_polynomial_or_bridge"),
                                          (-1999, "historical_hpiers"),
                                          (1900, "historical_hpiers"),
                                          (2000, "direct_eop"),
                                          (2050, "future_scenario"),
                                          (3000, "future_scenario")])
def test_provider_ledger_and_output(planetary_reader, year, branch):
    anchor = julian.julian_day(year, 6, 1)
    receipt = bound_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1, 1))
    assert receipt.branch == branch
    assert not receipt.source_and_arithmetic_attested
    assert not receipt.physical_delta_t_accuracy_certified
    result = RationalInterval.point(anchor) + receipt.bounds.output_offset_days
    for jd in (anchor - 1, anchor, anchor + 1):
        assert result.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("first_boundary", [True, False])
def test_outer_eop_seams_compose_without_losing_represented_inputs(planetary_reader, first_boundary):
    import math
    data = julian.EOPRegistry._ensure_loaded()
    row = min(data) if first_boundary else max(data)
    segment = julian.EOPRegistry._segment_bounds(row, data)
    jd = segment[0] if first_boundary else segment[2]
    receipt = bound_native_ut1_to_tt(planetary_reader, jd, RationalInterval(-1, 1))
    assert receipt.branch == "composite_eop"
    out = RationalInterval.point(jd) + receipt.bounds.output_offset_days
    for value in (jd - 1, math.nextafter(jd, -math.inf), jd,
                  math.nextafter(jd, math.inf), jd + 1):
        assert out.contains(_ut1_to_ephemeris_tt(value, planetary_reader))


@pytest.mark.requires_ephemeris
def test_neutral_internal_gap_gets_provider_receipt(planetary_reader, monkeypatch):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: -0.2})
    jd = 2400000.5 + 58002
    receipt = bound_native_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
    assert receipt.branch == "eop_gap"
    assert (RationalInterval.point(jd) + receipt.bounds.output_offset_days).contains(
        _ut1_to_ephemeris_tt(jd, planetary_reader)
    )

@pytest.mark.requires_ephemeris
def test_ancient_hpiers_seam_hulls_both_source_branches(planetary_reader):
    anchor = julian.julian_day(-2000, 1, 1)
    receipt = bound_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1, 1))
    assert receipt.branch == "ancient_hpiers_seam"
    out = RationalInterval.point(anchor) + receipt.bounds.output_offset_days
    for jd in (anchor - 1, anchor, anchor + 1):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))

@pytest.mark.requires_ephemeris
def test_composite_normalizes_nonrepresentable_integer_anchor(planetary_reader):
    from fractions import Fraction
    data = julian.EOPRegistry._ensure_loaded()
    jd = julian.EOPRegistry._segment_bounds(min(data), data)[0]
    anchor = 2**53 + 1
    offset = Fraction.from_float(jd) - Fraction.from_float(float(anchor))
    receipt = bound_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(offset - 1, offset + 1))
    assert receipt.branch == "composite_eop"
    assert receipt.bounds.anchor_jd == float(anchor)
    out = RationalInterval.point(float(anchor)) + receipt.bounds.output_offset_days
    for value in (jd - 1, jd, jd + 1):
        assert out.contains(_ut1_to_ephemeris_tt(value, planetary_reader))

@pytest.mark.requires_ephemeris
def test_composes_neutral_gap_with_adjacent_eop_segments(planetary_reader, monkeypatch):
    import math
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: 0.8})
    data = julian.EOPRegistry._ensure_loaded()
    left = julian.EOPRegistry._segment_bounds(58000, data)[2]
    right = julian.EOPRegistry._segment_bounds(58003, data)[0]
    anchor = (left + right) / 2
    receipt = bound_native_ut1_to_tt(planetary_reader, anchor, RationalInterval(-1.2, 1.2))
    assert receipt.branch == "composite_eop"
    out = RationalInterval.point(anchor) + receipt.bounds.output_offset_days
    for jd in (left - 0.1, math.nextafter(left, -math.inf), left,
               math.nextafter(left, math.inf), (left + right) / 2,
               math.nextafter(right, -math.inf), right,
               math.nextafter(right, math.inf), right + 0.1):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))

@pytest.mark.requires_ephemeris
def test_representative_five_millennium_forward_grid(planetary_reader):
    for year in (*range(-1999, 3001, 100), 3000):
        jd = julian.julian_day(year, 6, 1)
        receipt = bound_native_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
        out = RationalInterval.point(jd) + receipt.bounds.output_offset_days
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader)), year
