"""Native inverse provider branch and unavailable ledger."""
import pytest

from moira import julian
from moira._eclipse_clock_inverse_provider import bound_native_tt_to_ut1
from moira._eclipse_interval import RationalInterval
from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,branch", [(-1999, "historical_hpiers"), (1900, "historical_hpiers"),
                                          (2000, "direct_eop"), (2050, "future_scenario"),
                                          (3000, "future_scenario")])
def test_inverse_provider_selects_supported_branch(planetary_reader, year, branch):
    ut = julian.julian_day(year, 6, 1)
    tt = _ut1_to_ephemeris_tt(ut, planetary_reader)
    receipt = bound_native_tt_to_ut1(planetary_reader, tt, RationalInterval.point(0))
    assert receipt.branch == branch
    out = RationalInterval.point(tt) + receipt.bounds.output_offset_days
    assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))
    assert not receipt.physical_delta_t_accuracy_certified


@pytest.mark.requires_ephemeris
def test_inverse_historical_internal_gap_is_enclosed(planetary_reader, monkeypatch):
    mjd = int(julian.julian_day(1960, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {mjd: 0.1, mjd + 3: -0.1})
    tt = 2400000.5 + mjd + 2
    receipt = bound_native_tt_to_ut1(planetary_reader, tt, RationalInterval.point(0))
    assert (RationalInterval.point(tt) + receipt.bounds.output_offset_days).contains(
        _ephemeris_tt_to_ut1(tt, planetary_reader)
    )

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("first", [True, False])
def test_inverse_dispatch_composes_outer_eop_seed_seams(planetary_reader, first):
    import math
    data = julian.EOPRegistry._ensure_loaded()
    segment = julian.EOPRegistry._segment_bounds(min(data) if first else max(data), data)
    boundary = (segment[0] + segment[1] / 86400 if first else segment[2] + segment[3] / 86400)
    receipt = bound_native_tt_to_ut1(planetary_reader, boundary, RationalInterval(-0.001, 0.001))
    assert receipt.branch == "composite_eop"
    out = RationalInterval.point(boundary) + receipt.bounds.output_offset_days
    for tt in (boundary - 0.0005, math.nextafter(boundary, -math.inf), boundary,
               math.nextafter(boundary, math.inf), boundary + 0.0005):
        assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))

@pytest.mark.requires_ephemeris
def test_inverse_composite_normalizes_large_integer_anchor(planetary_reader):
    from fractions import Fraction
    data = julian.EOPRegistry._ensure_loaded()
    first = julian.EOPRegistry._segment_bounds(min(data), data)
    tt = first[0] + first[1] / 86400
    anchor = 2**53 + 1
    offset = Fraction.from_float(tt) - Fraction.from_float(float(anchor))
    receipt = bound_native_tt_to_ut1(planetary_reader, anchor, RationalInterval(offset - Fraction(1, 1000),
                                                                                 offset + Fraction(1, 1000)))
    assert receipt.branch == "composite_eop"
    out = RationalInterval.point(float(anchor)) + receipt.bounds.output_offset_days
    assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))

@pytest.mark.requires_ephemeris
def test_inverse_composes_neutral_internal_gap(planetary_reader, monkeypatch):
    import math
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: 0.8})
    data = julian.EOPRegistry._ensure_loaded()
    left = julian.EOPRegistry._segment_bounds(58000, data)
    right = julian.EOPRegistry._segment_bounds(58003, data)
    left_tt = left[2] + left[3] / 86400
    right_tt = right[0] + right[1] / 86400
    anchor = (left_tt + right_tt) / 2
    receipt = bound_native_tt_to_ut1(planetary_reader, anchor, RationalInterval(-1.2, 1.2))
    assert receipt.branch == "composite_eop"
    out = RationalInterval.point(anchor) + receipt.bounds.output_offset_days
    for tt in (left_tt - 0.1, math.nextafter(left_tt, -math.inf), left_tt,
               math.nextafter(left_tt, math.inf), anchor,
               math.nextafter(right_tt, -math.inf), right_tt,
               math.nextafter(right_tt, math.inf), right_tt + 0.1):
        assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))

@pytest.mark.requires_ephemeris
def test_inverse_composes_historical_internal_gap(planetary_reader, monkeypatch):
    import math
    mjd = int(julian.julian_day(1960, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {mjd: 0.1, mjd + 3: 0.8})
    data = julian.EOPRegistry._ensure_loaded()
    left = julian.EOPRegistry._segment_bounds(mjd, data)
    right = julian.EOPRegistry._segment_bounds(mjd + 3, data)
    left_tt = left[2] + left[3] / 86400
    right_tt = right[0] + right[1] / 86400
    anchor = (left_tt + right_tt) / 2
    receipt = bound_native_tt_to_ut1(planetary_reader, anchor, RationalInterval(-1.2, 1.2))
    assert receipt.branch == "composite_eop"
    out = RationalInterval.point(anchor) + receipt.bounds.output_offset_days
    for tt in (left_tt - 0.1, math.nextafter(left_tt, -math.inf), left_tt,
               math.nextafter(left_tt, math.inf), anchor,
               math.nextafter(right_tt, -math.inf), right_tt,
               math.nextafter(right_tt, math.inf), right_tt + 0.1):
        assert out.contains(_ephemeris_tt_to_ut1(tt, planetary_reader))

@pytest.mark.requires_ephemeris
def test_inverse_mixed_hpiers_annual_gap(planetary_reader, monkeypatch):
    first = int(julian.julian_day(2014, 1, 1) - 2400000.5)
    last = int(julian.julian_day(2018, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {first: 0.1, last: 0.2})
    tt = julian.julian_day(2016, 1, 1)
    receipt = bound_native_tt_to_ut1(planetary_reader, tt, RationalInterval(-0.01, 0.01))
    out = RationalInterval.point(tt) + receipt.bounds.output_offset_days
    for value in (tt - 0.005, tt, tt + 0.005):
        assert out.contains(_ephemeris_tt_to_ut1(value, planetary_reader))
