"""Basis-neutral internal EOP gaps use bounded source interpolation."""
import math
import pytest

from moira import julian
from moira._eclipse_eop_gap_bounds import bound_eop_gap_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.requires_ephemeris
def test_neutral_gap_and_adjacent_endpoints(planetary_reader, monkeypatch):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: -0.2})
    data = julian.EOPRegistry._ensure_loaded()
    left = julian.EOPRegistry._segment_bounds(58000, data)[2]
    right = julian.EOPRegistry._segment_bounds(58003, data)[0]
    for jd in (left, math.nextafter(left, math.inf), (left + right) / 2,
               math.nextafter(right, -math.inf)):
        result = bound_eop_gap_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
        assert (RationalInterval.point(jd) + result.output_offset_days).contains(
            _ut1_to_ephemeris_tt(jd, planetary_reader)
        )
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_eop_gap_ut1_to_tt(planetary_reader, right, RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_historical_tidal_gap_is_enclosed(planetary_reader, monkeypatch):
    mjd = int(julian.julian_day(1960, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {mjd: 0.1, mjd + 3: -0.1})
    jd = 2400000.5 + mjd + 2
    receipt = bound_eop_gap_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
    assert (RationalInterval.point(jd) + receipt.output_offset_days).contains(
        _ut1_to_ephemeris_tt(jd, planetary_reader)
    )

@pytest.mark.requires_ephemeris
def test_positive_dut1_utc_label_before_right_ut1_start(planetary_reader, monkeypatch):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: 0.8})
    data = julian.EOPRegistry._ensure_loaded()
    right = julian.EOPRegistry._segment_bounds(58003, data)[0]
    midnight = 2400000.5 + 58003
    assert midnight < right
    for jd in (midnight, math.nextafter(midnight, math.inf), math.nextafter(right, -math.inf)):
        receipt = bound_eop_gap_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
        assert (RationalInterval.point(jd) + receipt.output_offset_days).contains(
            _ut1_to_ephemeris_tt(jd, planetary_reader)
        )
    with pytest.raises(NativeClockBoundsUnavailable):
        bound_eop_gap_ut1_to_tt(planetary_reader, right, RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_invalid_annual_table_fails_closed(planetary_reader, monkeypatch):
    monkeypatch.setattr(julian.EOPRegistry, "_data", {58000: 0.1, 58003: 0.2})
    monkeypatch.setattr(julian, "_DELTA_T_ANNUAL", ((2010.0, 65.0), (2010.0, 66.0)))
    with pytest.raises(NativeClockBoundsUnavailable, match="annual model table"):
        bound_eop_gap_ut1_to_tt(planetary_reader, 2400000.5 + 58002,
                                        RationalInterval.point(0))

@pytest.mark.requires_ephemeris
def test_mixed_historical_neutral_gap_is_enclosed(planetary_reader, monkeypatch):
    first = int(julian.julian_day(2014, 1, 1) - 2400000.5)
    last = int(julian.julian_day(2018, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {first: 0.1, last: 0.2})
    jd = julian.julian_day(2016, 1, 1)
    receipt = bound_eop_gap_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
    assert (RationalInterval.point(jd) + receipt.output_offset_days).contains(
        _ut1_to_ephemeris_tt(jd, planetary_reader)
    )

@pytest.mark.requires_ephemeris
def test_historical_gap_endpoints_and_interval(planetary_reader, monkeypatch):
    mjd = int(julian.julian_day(1960, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {mjd: 0.1, mjd + 3: 0.8})
    data = julian.EOPRegistry._ensure_loaded()
    left = julian.EOPRegistry._segment_bounds(mjd, data)[2]
    right = julian.EOPRegistry._segment_bounds(mjd + 3, data)[0]
    mid = (left + right) / 2
    receipt = bound_eop_gap_ut1_to_tt(planetary_reader, mid, RationalInterval(-0.9, 0.9))
    out = RationalInterval.point(mid) + receipt.output_offset_days
    for jd in (mid - 0.8, mid, mid + 0.8):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))
    for jd in (left, math.nextafter(left, math.inf), math.nextafter(right, -math.inf)):
        receipt = bound_eop_gap_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
        assert (RationalInterval.point(jd) + receipt.output_offset_days).contains(
            _ut1_to_ephemeris_tt(jd, planetary_reader)
        )

@pytest.mark.requires_ephemeris
def test_historical_gap_without_reader_identity_fails_closed(planetary_reader, monkeypatch):
    mjd = int(julian.julian_day(1960, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {mjd: 0.1, mjd + 3: 0.8})
    monkeypatch.setattr(planetary_reader, "_kernel_identity", None)
    with pytest.raises(NativeClockBoundsUnavailable, match="identity unavailable"):
        bound_eop_gap_ut1_to_tt(planetary_reader, 2400000.5 + mjd + 2,
                                RationalInterval.point(0))

@pytest.mark.requires_ephemeris
def test_eop_endpoint_before_tai_utc_coverage_fails_closed(planetary_reader, monkeypatch):
    first = int(julian.julian_day(-2050, 1, 1) - 2400000.5)
    last = int(julian.julian_day(2018, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {first: 0.1, last: 0.2})
    with pytest.raises(NativeClockBoundsUnavailable, match="predates admitted TAI-UTC"):
        bound_eop_gap_ut1_to_tt(planetary_reader, julian.julian_day(2016, 1, 1),
                                RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_gap_zero_weight_bridge_and_unsupported_branch_transition(planetary_reader, monkeypatch):
    first = int(julian.julian_day(2014, 1, 1) - 2400000.5)
    last = int(julian.julian_day(2018, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {first: 0.1, last: 0.2})
    left = julian.EOPRegistry._segment_bounds(first, julian.EOPRegistry._data)[2]
    receipt = bound_eop_gap_ut1_to_tt(planetary_reader, left, RationalInterval.point(0))
    assert (RationalInterval.point(left) + receipt.output_offset_days).contains(
        _ut1_to_ephemeris_tt(left, planetary_reader)
    )
    bridge_day = julian.julian_day(2015, 3, 1)
    assert julian._resolve_delta_t(
        julian._continuous_decimal_year_from_jd(bridge_day)
    ).source_product == "hpiers_to_usno_bridge"
    receipt = bound_eop_gap_ut1_to_tt(
        planetary_reader, bridge_day, RationalInterval(-0.5, 0.5)
    )
    out = RationalInterval.point(bridge_day) + receipt.output_offset_days
    for jd in (bridge_day - 0.5, bridge_day - 0.25, bridge_day,
               bridge_day + 0.25, bridge_day + 0.5):
        assert out.contains(_ut1_to_ephemeris_tt(jd, planetary_reader))

    # A box actually straddling the bridge-to-annual transition remains
    # unsupported. Verify the source labels on both sides of the box.
    bridge_end = julian._delta_t_hpiers_annual_bridge()[1][0]
    seam_day = julian.julian_day(2015, 1, 1) + (bridge_end - 2015) * 365
    assert julian._resolve_delta_t(julian._continuous_decimal_year_from_jd(
        seam_day - 0.5)).source_product == "hpiers_to_usno_bridge"
    assert julian._resolve_delta_t(julian._continuous_decimal_year_from_jd(
        seam_day + 0.5)).source_product == "usno_monthly_aggregate"
    with pytest.raises(NativeClockBoundsUnavailable, match="base crosses model boundary"):
        bound_eop_gap_ut1_to_tt(planetary_reader, seam_day, RationalInterval(-0.5, 0.5))

@pytest.mark.requires_ephemeris
def test_gap_with_hpiers_annual_bridge_endpoint(planetary_reader, monkeypatch):
    first = int(julian.julian_day(2015, 3, 1) - 2400000.5)
    last = int(julian.julian_day(2018, 1, 1) - 2400000.5)
    monkeypatch.setattr(julian.EOPRegistry, "_data", {first: 0.1, last: 0.2})
    data = julian.EOPRegistry._ensure_loaded()
    left = julian.EOPRegistry._segment_bounds(first, data)
    source = julian._resolve_delta_t(julian._continuous_decimal_year_from_jd(left[2]))
    assert source.source_product == "hpiers_to_usno_bridge"
    assert len(source.tidal_terms) == 1 and 0 < source.tidal_terms[0].coefficient < 1
    jd = julian.julian_day(2016, 1, 1)
    receipt = bound_eop_gap_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
    assert (RationalInterval.point(jd) + receipt.output_offset_days).contains(
        _ut1_to_ephemeris_tt(jd, planetary_reader)
    )
