"""Targeted replay of the historical one-limit solar-path failures.

This is a native-regression corpus, not an independent proof of NASA topology
or full five-millennium accuracy.  NASA type codes are source annotations only.
The external anchors are independently scoped to the published 2003 and 2044
catalog rows with rounded numerical fields and cross-model tolerances.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import moira.eclipse as eclipse
from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.julian import julian_day


pytestmark = pytest.mark.requires_ephemeris
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "moira_solar_one_limit_92_baseline.json"
BASELINE = json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_replay_fixture_documents_its_bounded_provenance():
    assert BASELINE["count"] == len(BASELINE["records"]) == 92
    assert BASELINE["calculation_version"] == "6.13.1"
    assert len({row["lunation_number"] for row in BASELINE["records"]}) == 92
    assert sorted(row["native_jd_tt"] for row in BASELINE["records"]) == [
        row["native_jd_tt"] for row in BASELINE["records"]
    ]
    assert all(row["nasa_source_url"].startswith((
        "https://eclipse.gsfc.nasa.gov/", "https://ntrs.nasa.gov/",
    )) for row in BASELINE["records"])
    assert sum("closed two-limit product" in row["historical_failure"]
               for row in BASELINE["records"]) == 91
    assert sum("no neighboring surface point" in row["historical_failure"]
               for row in BASELINE["records"]) == 1


@pytest.mark.slow
@pytest.mark.parametrize("case", BASELINE["records"], ids=lambda row: str(row["lunation_number"]))
def test_each_historical_event_returns_an_honest_native_path(eclipse_calculator, case):
    """One-limit support never fabricates a numeric closed-footprint width."""
    path = eclipse_calculator.solar_eclipse_path(case["native_jd_ut1"] - 1.0, sample_count=2)
    data = path.eclipse_data
    assert data.saros_lunation_number == case["lunation_number"]
    assert data.saros_series == case["saros_series"]
    assert str(data.eclipse_type) == case["native_type"]
    assert math.isfinite(path.max_eclipse_lat)
    assert math.isfinite(path.max_eclipse_lon)
    assert -90 <= path.max_eclipse_lat <= 90
    assert -180 <= path.max_eclipse_lon <= 180
    assert path.umbral_width_status in {"available", "closed_width_not_admitted"}
    if path.umbral_width_status == "available":
        assert path.umbral_width_km is not None
        assert math.isfinite(path.umbral_width_km) and path.umbral_width_km > 0
    else:
        assert path.umbral_width_km is None
        assert path.umbral_width_reason


# NASA/GSFC Five Millennium Catalog, 2001–2100, integer-degree positions and
# seconds.  These are bounded cross-model comparison tolerances, not physical
# accuracy claims. NASA's published calendar times are TD/TT, not UT/UTC.
# https://eclipse.gsfc.nasa.gov/SEcat5/SE2001-2100.html
@pytest.mark.slow
@pytest.mark.parametrize(
    "ymd,hms,lunation,saros,nasa_gamma,nasa_magnitude,nasa_lat,nasa_lon,nasa_duration",
    [((2003, 5, 31), (4, 9, 22), 42, 147, 0.9960, 0.9384, 67, -24, 217),
     ((2044, 2, 28), (20, 24, 39), 546, 121, -0.9954, 0.9600, -62, -26, 147)],
)
def test_modern_one_limit_global_values_preserve_native_circumstances(
    eclipse_calculator, ymd, hms, lunation, saros, nasa_gamma,
    nasa_magnitude, nasa_lat, nasa_lon, nasa_duration,
):
    start = julian_day(*ymd) - 1.0
    path = eclipse_calculator.solar_eclipse_path(start, sample_count=2)
    result = eclipse_calculator.solar_global_circumstances(start)
    event = result.event
    assert event.data.saros_lunation_number == lunation
    assert event.data.saros_series == saros
    assert str(event.data.eclipse_type) == "Annular"
    assert path.umbral_width_status == "closed_width_not_admitted"
    assert path.umbral_width_km is None
    assert result.greatest.path_width_status == "closed_width_not_admitted"
    assert result.greatest.path_width_km is None
    # NASA published the TD maximum to 1 second and coordinates to 1 degree.
    hh, mm, ss = hms
    nasa_tt = julian_day(*ymd, hh + mm / 60 + ss / 3600)
    native_tt = _ut1_to_ephemeris_tt(event.jd_ut, eclipse_calculator._reader)
    assert abs(native_tt - nasa_tt) * 86400 < 3.0
    assert result.gamma_earth_radii == pytest.approx(nasa_gamma, abs=0.0002)
    assert result.greatest.magnitude == pytest.approx(nasa_magnitude, abs=0.001)
    assert result.greatest.latitude_deg == pytest.approx(nasa_lat, abs=1.0)
    assert result.greatest.longitude_deg == pytest.approx(nasa_lon, abs=1.0)
    assert result.greatest.central_duration_seconds == pytest.approx(nasa_duration, abs=3.0)
    assert result.umbral_contacts is not None
    assert result.umbral_contacts.u1.epoch.jd_ut1 < event.jd_ut < result.umbral_contacts.u4.epoch.jd_ut1
    assert (result.umbral_contacts.u2 is None) == (result.umbral_contacts.u3 is None)
    # Greatest-duration width is solved independently; do not infer its state
    # from the greatest-eclipse width or vice versa.
    assert result.greatest_duration is not None
    if ymd == (2044, 2, 28):
        assert result.greatest_duration.path_width_status == "width_not_computed"
        assert result.greatest_duration.path_width_reason == "central_axis_boundary"
        assert result.greatest_duration.path_width_km is None
    else:
        assert result.greatest_duration.path_width_status in {"available", "closed_width_not_admitted"}


def test_arbitrary_width_failure_is_not_silently_downgraded(eclipse_calculator, monkeypatch):
    """Only a proven, typed unsupported condition may yield an absent width."""
    def fail_unexpectedly(*_args, **_kwargs):
        raise ArithmeticError("injected unexpected geometry failure")

    monkeypatch.setattr(eclipse, "_solve_solar_umbral_width_km", fail_unexpectedly)
    with pytest.raises(ArithmeticError, match="injected unexpected geometry failure"):
        eclipse_calculator.solar_eclipse_path(julian_day(2024, 4, 1), sample_count=2)


def test_2003_nasa_path_table_distinguishes_horizon_from_cone_edge(eclipse_calculator):
    """At 04:08 UT NASA's northern limit is a terminator, not a cone edge.

    https://eclipse.gsfc.nasa.gov/SEpubs/20030000/tables/table_1.3.html
    NASA used DE200/LE200, while the native ephemeris is DE441.  These
    deliberately bounded cross-model tolerances are not accuracy estimates.
    """
    jd_ut1 = julian_day(2003, 5, 31, 4 + 8 / 60)
    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, jd_ut1)
    north = eclipse._wgs84_surface_xyz_km(64 + 1.6 / 60, -28.0)
    south = eclipse._wgs84_surface_xyz_km(72 + 30.5 / 60, -(8 + 25.8 / 60))
    north_alt = math.degrees(math.asin(eclipse._topocentric_solar_altitude_proxy(shadow, north)))
    south_alt = math.degrees(math.asin(eclipse._topocentric_solar_altitude_proxy(shadow, south)))
    assert abs(north_alt) < 0.01
    assert eclipse._central_shadow_clearance_km(shadow, north) > 1.0
    assert south_alt > 1.0
    assert eclipse._central_shadow_clearance_km(shadow, south) == pytest.approx(0.0, abs=3.0)
    center = eclipse._solar_axis_surface_point(eclipse_calculator, jd_ut1)
    assert center.latitude_deg == pytest.approx(66 + 28.3 / 60, abs=0.05)
    assert center.longitude_deg == pytest.approx(-(24 + 7.9 / 60), abs=0.05)


def test_short_central_interval_does_not_fabricate_a_tangent(eclipse_calculator):
    """The -500 graze has no sampled tangent and incomplete generators."""
    case = next(row for row in BASELINE["records"] if row["lunation_number"] == -30916)
    event = eclipse_calculator.next_solar_eclipse(case["native_jd_ut1"] - 1.0)
    assert event.data.saros_lunation_number == -30916
    center = eclipse._solar_axis_surface_point(eclipse_calculator, event.jd_ut)
    assert center is not None
    step = eclipse._SOLAR_TRACK_TANGENT_STEP_DAYS
    assert eclipse._solar_axis_surface_point(eclipse_calculator, event.jd_ut - step) is None
    assert eclipse._solar_axis_surface_point(eclipse_calculator, event.jd_ut + step) is None
    with pytest.raises(ArithmeticError, match="no neighboring surface point"):
        eclipse._solar_axis_track_direction_itrf(eclipse_calculator, event.jd_ut, center)
    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, event.jd_ut)
    with pytest.raises(eclipse._ClosedWidthUnavailable):
        eclipse._central_shadow_generator_points(shadow)
    path = eclipse_calculator.solar_eclipse_path(case["native_jd_ut1"] - 1.0, sample_count=2)
    assert path.eclipse_data.saros_lunation_number == -30916
    assert path.umbral_width_status == "closed_width_not_admitted"
    assert path.umbral_width_reason == "incomplete_generator_intersections"
    assert path.umbral_width_km is None
