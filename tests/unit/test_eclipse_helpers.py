from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

import moira.eclipse as eclipse
from moira.geoutils import (
    EARTH_KM_PER_DEG_LAT,
    offset_geographic_km,
    wrap_longitude_deg,
)
from moira.eclipse_canon import (
    _ut_to_tt_nasa_catalog,
    find_lunar_contacts_canon,
    lunar_canon_geometry,
)
from moira.eclipse_geometry import (
    angular_separation,
    lunar_penumbral_magnitude,
    lunar_umbral_magnitude,
    shadow_axis_offset_deg,
)
from moira.eclipse_search import (
    refine_lunar_greatest_eclipse,
    refine_minimum,
    refine_solar_greatest_eclipse,
)
from moira.eclipse_contacts import find_lunar_contacts
from moira.julian import julian_day


def _earth_fixed_shadow(
    *,
    fundamental_plane_point_xyz_km: tuple[float, float, float],
    axis_unit_away_from_sun: tuple[float, float, float],
    axis_projection_km: float,
    central_radius_km: float,
    central_cone_slope: float,
) -> eclipse._EarthFixedSolarShadow:
    reference = (
        (0.0, 0.0, 1.0)
        if abs(axis_unit_away_from_sun[2]) < 0.9
        else (1.0, 0.0, 0.0)
    )
    east = eclipse._shadow_unit(
        eclipse._shadow_cross(axis_unit_away_from_sun, reference),
        label="test shadow east",
    )
    north = eclipse._shadow_cross(axis_unit_away_from_sun, east)
    return eclipse._EarthFixedSolarShadow(
        fundamental_plane_point_xyz_km=fundamental_plane_point_xyz_km,
        axis_unit_away_from_sun=axis_unit_away_from_sun,
        axis_projection_km=axis_projection_km,
        central_radius_km=central_radius_km,
        central_cone_slope=central_cone_slope,
        penumbral_radius_km=200.0,
        penumbral_cone_slope=0.0,
        fundamental_east_unit_itrf=east,
        fundamental_north_unit_itrf=north,
        sun_xyz_from_earth_itrf_km=tuple(
            -150_000_000.0 * component
            for component in axis_unit_away_from_sun
        ),
    )


def test_shadow_axis_offset_tracks_opposition_distance() -> None:
    assert shadow_axis_offset_deg(180.0) == 0.0
    assert shadow_axis_offset_deg(179.25) == 0.75
    assert shadow_axis_offset_deg(181.25) == 1.25


def test_lunar_magnitude_helpers_match_current_formulas() -> None:
    umbral = lunar_umbral_magnitude(0.75, 0.25, 0.40)
    penumbral = lunar_penumbral_magnitude(1.25, 0.25, 0.40)
    assert umbral == pytest.approx(1.2, abs=1e-12)
    assert penumbral == pytest.approx(2.2, abs=1e-12)


def test_angular_separation_handles_wraparound() -> None:
    sep = angular_separation(359.9, 0.0, 0.1, 0.0)
    assert sep < 0.21


def test_longitude_wrapping_preserves_positive_180_boundary() -> None:
    assert wrap_longitude_deg(180.0) == 180.0
    assert wrap_longitude_deg(540.0) == 180.0


def test_geographic_offset_crosses_pole_instead_of_clamping() -> None:
    latitude, longitude = offset_geographic_km(
        89.0,
        0.0,
        2.0 * EARTH_KM_PER_DEG_LAT,
        0.0,
    )

    assert latitude == pytest.approx(89.0, abs=1.0e-12)
    assert longitude == pytest.approx(180.0, abs=1.0e-12)


def test_geographic_offset_canonicalizes_exact_pole_longitude() -> None:
    latitude, longitude = offset_geographic_km(
        0.0,
        123.0,
        90.0 * EARTH_KM_PER_DEG_LAT,
        0.0,
    )

    assert latitude == 90.0
    assert longitude == 0.0
    assert offset_geographic_km(90.0, 47.0, 0.0, 0.0) == (90.0, 0.0)


def test_geographic_offset_uses_canonical_pole_tangent_basis() -> None:
    latitude, longitude = offset_geographic_km(
        90.0,
        81.0,
        EARTH_KM_PER_DEG_LAT,
        EARTH_KM_PER_DEG_LAT,
    )

    assert latitude == pytest.approx(90.0 - math.sqrt(2.0), abs=1.0e-12)
    assert longitude == pytest.approx(135.0, abs=1.0e-12)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ((math.nan, 0.0, 0.0, 0.0), "latitude must be finite"),
        ((0.0, math.inf, 0.0, 0.0), "longitude must be finite"),
        ((0.0, 0.0, math.nan, 0.0), "north_km must be finite"),
        ((0.0, 0.0, 0.0, math.inf), "east_km must be finite"),
        ((90.0001, 0.0, 0.0, 0.0), r"latitude must be in \[-90, 90\]"),
    ],
)
def test_geographic_offset_rejects_non_geographic_inputs(
    args: tuple[float, float, float, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        offset_geographic_km(*args)


def test_solar_greatest_location_searches_canonical_pole_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluated: list[tuple[float, float]] = []

    def fake_geometry(calc, jd_ut, latitude, longitude):
        evaluated.append((latitude, longitude))
        separation = 0.0 if latitude == 90.0 else 10.0
        return separation, 0.0, 0.0

    monkeypatch.setattr(eclipse, "_topocentric_solar_geometry", fake_geometry)

    latitude, longitude, separation = eclipse._solve_solar_greatest_location(
        object(),
        2451401.96,
    )

    assert (latitude, longitude, separation) == (90.0, 0.0, 0.0)
    assert evaluated == [(-90.0, 0.0), (90.0, 0.0)]


def test_solar_greatest_location_refines_in_pole_tangent_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_latitude = 89.9
    target_longitude = 90.0
    evaluated: list[tuple[float, float]] = []

    def fake_geometry(calc, jd_ut, latitude, longitude):
        assert math.isfinite(latitude)
        assert math.isfinite(longitude)
        assert -90.0 <= latitude <= 90.0
        assert -180.0 < longitude <= 180.0
        evaluated.append((latitude, longitude))
        separation = eclipse._angular_separation(
            longitude,
            latitude,
            target_longitude,
            target_latitude,
        )
        return separation, 0.0, 0.0

    monkeypatch.setattr(eclipse, "_topocentric_solar_geometry", fake_geometry)

    latitude, longitude, separation = eclipse._solve_solar_greatest_location(
        object(),
        2451401.96,
    )

    assert latitude > 89.5
    assert separation <= eclipse._GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG
    assert any(candidate_latitude > 89.5 for candidate_latitude, _ in evaluated)


@pytest.mark.parametrize(
    ("axis_unit", "expected_latitude"),
    [
        ((0.0, 0.0, -1.0), 90.0),
        ((0.0, 0.0, 1.0), -90.0),
    ],
)
def test_wgs84_axis_surface_point_canonicalizes_only_an_exact_pole(
    axis_unit: tuple[float, float, float],
    expected_latitude: float,
) -> None:
    shadow = _earth_fixed_shadow(
        fundamental_plane_point_xyz_km=(0.0, 0.0, 0.0),
        axis_unit_away_from_sun=axis_unit,
        axis_projection_km=-100_000.0,
        central_radius_km=100.0,
        central_cone_slope=0.0,
    )

    point = eclipse._axis_surface_point_from_shadow(shadow)

    assert point is not None
    assert point.latitude_deg == pytest.approx(expected_latitude, abs=1.0e-12)
    assert point.longitude_deg == 0.0


def test_wgs84_line_intersection_distinguishes_tangent_from_miss() -> None:
    tangent_margin, tangent_roots = eclipse._wgs84_line_intersection_parameters(
        (eclipse.EARTH_RADIUS_KM, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    miss_margin, miss_roots = eclipse._wgs84_line_intersection_parameters(
        (eclipse.EARTH_RADIUS_KM + 1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )

    assert tangent_margin == pytest.approx(0.0, abs=1.0e-12)
    assert tangent_roots == pytest.approx((0.0, 0.0), abs=1.0e-12)
    assert miss_margin < 0.0
    assert miss_roots is None


def test_high_latitude_spherical_hit_can_miss_the_wgs84_ellipsoid() -> None:
    polar_offset_km = eclipse._WGS84_POLAR_RADIUS_KM + 1.0
    assert polar_offset_km < eclipse.EARTH_RADIUS_KM

    margin, roots = eclipse._wgs84_line_intersection_parameters(
        (0.0, 0.0, polar_offset_km),
        (1.0, 0.0, 0.0),
    )

    assert margin < 0.0
    assert roots is None


def test_axis_tangency_materialization_uses_the_coalesced_chord_root() -> None:
    half_chord_km = 1.0
    x_km = math.sqrt(eclipse.EARTH_RADIUS_KM**2 - half_chord_km**2)
    shadow = _earth_fixed_shadow(
        fundamental_plane_point_xyz_km=(x_km, 0.0, 0.0),
        axis_unit_away_from_sun=(0.0, 1.0, 0.0),
        axis_projection_km=-100_000.0,
        central_radius_km=100.0,
        central_cone_slope=0.0,
    )

    near_point = eclipse._axis_surface_point_from_shadow(shadow)
    tangent_point = eclipse._axis_surface_tangent_point_from_shadow(shadow)

    assert near_point is not None
    assert tangent_point is not None
    assert near_point.xyz_itrf_km[1] == pytest.approx(-half_chord_km, abs=1.0e-9)
    assert tangent_point.xyz_itrf_km[1] == pytest.approx(0.0, abs=1.0e-12)


def test_central_shadow_width_is_full_footprint_support_span() -> None:
    half_width_km = 100.0
    shadow = _earth_fixed_shadow(
        fundamental_plane_point_xyz_km=(0.0, 0.0, 0.0),
        axis_unit_away_from_sun=(1.0, 0.0, 0.0),
        axis_projection_km=-100_000.0,
        central_radius_km=half_width_km,
        central_cone_slope=0.0,
    )
    center = eclipse._axis_surface_point_from_shadow(shadow)
    assert center is not None

    width_km = eclipse._central_shadow_support_width_km(
        shadow,
        center.xyz_itrf_km,
        (0.0, 0.0, 1.0),
    )

    assert width_km == pytest.approx(2.0 * half_width_km, abs=1.0e-9)


def test_central_path_fails_on_spherical_wgs84_centrality_divergence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = SimpleNamespace(
        jd_ut=2451545.0,
        data=SimpleNamespace(
            eclipse_type=eclipse.EclipseType(
                is_partial=False,
                is_annular=False,
                is_total=True,
                is_hybrid=False,
                magnitude_umbral=1.0,
                magnitude_penumbra=1.0,
            )
        ),
    )

    class FakeCalculator:
        def _search_solar_eclipse(self, *args, **kwargs):
            return event

    monkeypatch.setattr(eclipse, "_solar_axis_surface_point", lambda *args: None)

    with pytest.raises(
        ArithmeticError,
        match="classification is central.*does not intersect",
    ):
        eclipse.EclipseCalculator.solar_eclipse_path(FakeCalculator(), 2451545.0)


def test_solar_greatest_location_exits_early_on_exact_conjunction(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_geometry(calc, jd_ut, latitude, longitude):
        nonlocal call_count
        call_count += 1
        if latitude == -80.0 and longitude == -140.0:
            return 0.0, 0.0, 0.0
        return 10.0, 0.0, 0.0

    monkeypatch.setattr(eclipse, "_topocentric_solar_geometry", fake_geometry)

    latitude, longitude, separation = eclipse._solve_solar_greatest_location(object(), 2451401.96)

    assert latitude == -80.0
    assert longitude == -140.0
    assert separation == 0.0
    assert call_count < 10


def test_solar_greatest_location_raises_when_objective_eval_limit_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scores = {
        (-80.0, -180.0): 5.0,
        (-80.0, -160.0): 4.0,
        (-80.0, -140.0): 3.0,
        (-80.0, -120.0): 2.0,
        (-80.0, -100.0): 1.0,
    }
    call_count = 0

    def fake_geometry(calc, jd_ut, latitude, longitude):
        nonlocal call_count
        call_count += 1
        return scores.get((latitude, longitude), 99.0), 0.0, 0.0

    monkeypatch.setattr(eclipse, "_topocentric_solar_geometry", fake_geometry)
    monkeypatch.setattr(eclipse, "_GEO_SEARCH_MAX_OBJECTIVE_EVALS", 5)

    with pytest.raises(eclipse._SearchLimitReached, match="evaluation limit"):
        eclipse._solve_solar_greatest_location(object(), 2451401.96)

    assert call_count == 5


def test_solar_central_interval_raises_when_evaluation_limit_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_axis_margin(calc, jd_ut):
        nonlocal call_count
        call_count += 1
        return 0.5
    
    monkeypatch.setattr(
        eclipse,
        "_solar_axis_surface_discriminant_km2",
        fake_axis_margin,
    )
    monkeypatch.setattr(eclipse, "_SOLAR_CENTRAL_INTERVAL_MAX_MARGIN_EVALS", 0)

    with pytest.raises(eclipse._SearchLimitReached, match="evaluation limit"):
        eclipse._solve_solar_central_interval(object(), 2451401.96)

    assert call_count == 0


def test_refine_minimum_finds_parabola_vertex() -> None:
    best = refine_minimum(lambda x: (x - 3.25) ** 2, 3.0, window_days=1.0, tol_days=1e-7)
    assert abs(best - 3.25) < 1e-5


def test_refine_minimum_falls_back_cleanly_when_window_is_not_unimodal() -> None:
    def objective(x: float) -> float:
        return min((x + 0.35) ** 2, (x - 0.2) ** 2 + 0.01)

    best = refine_minimum(objective, 0.0, window_days=1.0, tol_days=1e-6)
    assert abs(best + 0.35) < 1e-3


def test_refine_greatest_eclipse_helpers_return_local_event_maxima(eclipse_calculator) -> None:
    lunar_seed = 2451564.7  # 2000-01-21 total lunar eclipse
    lunar_best = refine_lunar_greatest_eclipse(eclipse_calculator, lunar_seed)
    lunar_data = eclipse_calculator.calculate_jd(lunar_best)
    assert lunar_data.is_lunar_eclipse
    assert lunar_data.eclipse_type.is_total

    solar_seed = 2451401.96  # 1999-08-11 total solar eclipse
    solar_best = refine_solar_greatest_eclipse(eclipse_calculator, solar_seed)
    solar_data = eclipse_calculator.calculate_jd(solar_best)
    assert solar_data.is_solar_eclipse
    assert solar_data.eclipse_type.is_total


def test_solar_shadow_axis_refinement_is_subsecond_stable(eclipse_calculator) -> None:
    seed = 2451401.96
    native_search = refine_solar_greatest_eclipse(
        eclipse_calculator,
        seed,
        tol_days=1.0e-9,
    )
    tighter = refine_solar_greatest_eclipse(
        eclipse_calculator,
        seed,
        tol_days=1.0e-11,
    )

    assert abs(native_search - tighter) * 86400.0 < 0.1
    center_distance = eclipse_calculator._native_solar_shadow_axis_distance_km(native_search)
    half_second = 0.5 / 86400.0
    assert center_distance <= eclipse_calculator._native_solar_shadow_axis_distance_km(
        native_search - half_second
    )
    assert center_distance <= eclipse_calculator._native_solar_shadow_axis_distance_km(
        native_search + half_second
    )


def test_total_lunar_eclipse_reports_larger_penumbral_than_umbral_magnitude(eclipse_calculator) -> None:
    data = eclipse_calculator.calculate_jd(2451564.705)  # 2000-01-21 total lunar eclipse near maximum
    assert data.is_lunar_eclipse
    assert data.eclipse_type.is_total
    assert data.eclipse_type.magnitude_penumbra > data.eclipse_type.magnitude_umbral


def test_explicit_native_lunar_event_surface_exposes_model_choice(eclipse_calculator) -> None:
    geometric = eclipse_calculator.calculate_jd(2451564.705)
    native_umbral = eclipse_calculator.calculate_lunar_event_jd(2451564.705, kind="umbral")
    native_penumbral = eclipse_calculator.calculate_lunar_event_jd(2451564.705, kind="penumbral")

    assert geometric == native_penumbral
    assert native_umbral.is_lunar_eclipse
    assert native_umbral.eclipse_type.is_total


def test_explicit_native_lunar_event_surface_rejects_unknown_kind(eclipse_calculator) -> None:
    with pytest.raises(ValueError, match="Unsupported native lunar event kind"):
        eclipse_calculator.calculate_lunar_event_jd(2451564.705, kind="hybrid")


@pytest.mark.slow
def test_lunar_contact_solver_returns_ordered_contacts_for_total_eclipse(eclipse_calculator) -> None:
    contacts = find_lunar_contacts(eclipse_calculator, 2451564.705)
    assert contacts.p1 is not None
    assert contacts.u1 is not None
    assert contacts.u2 is not None
    assert contacts.u3 is not None
    assert contacts.u4 is not None
    assert contacts.p4 is not None
    assert contacts.p1 < contacts.u1 < contacts.u2 < contacts.greatest
    assert contacts.greatest < contacts.u3 < contacts.u4 < contacts.p4


@pytest.mark.slow
def test_lunar_canon_geometry_and_search_path_are_available(eclipse_calculator) -> None:
    geom = lunar_canon_geometry(eclipse_calculator, 2451564.705)
    assert geom.gamma_earth_radii < 0.0
    assert geom.penumbra_radius_earth_radii > geom.umbra_radius_earth_radii > 0.0
    contacts = find_lunar_contacts_canon(eclipse_calculator, 2451564.705)
    assert contacts.p1_ut is not None
    event = eclipse_calculator.next_lunar_eclipse_canon(2451560.0, kind="total")
    assert event.data.is_lunar_eclipse
    assert event.data.eclipse_type.is_total


def test_unified_lunar_analysis_api_exposes_native_and_canon_modes(eclipse_calculator) -> None:
    native = eclipse_calculator.analyze_lunar_eclipse(2451560.0, kind="total", mode="native")
    assert native.mode == "native"
    assert native.event.data.is_lunar_eclipse
    assert native.event.data.eclipse_type.is_total
    assert native.gamma_earth_radii is None
    assert abs(native.contacts.greatest - native.event.jd_ut) < 1e-6

    canon = eclipse_calculator.analyze_lunar_eclipse(2451560.0, kind="total", mode="nasa_compat")
    assert canon.mode == "nasa_compat"
    assert canon.event.data.is_lunar_eclipse
    assert canon.event.data.eclipse_type.is_total
    assert canon.gamma_earth_radii is not None
    assert abs(canon.contacts.greatest_ut - canon.event.jd_ut) < 1e-6
    assert canon.canon_method == "nasa_shadow_axis_apparent_sun_moon"
    assert "annual-aberration" in canon.source_model


def test_canon_event_data_uses_the_declared_nasa_time_basis(eclipse_calculator) -> None:
    event = eclipse_calculator.next_lunar_eclipse_canon(2451560.0, kind="total")
    expected = eclipse_calculator._calculate_jd_internal(
        event.jd_ut,
        delta_t_mode="nasa_canon",
        lunar_canon_method="nasa_shadow_axis_apparent_sun_moon",
    )

    assert event.data == expected


@pytest.mark.slow
def test_limiting_canon_event_data_uses_the_same_penumbral_geometry(
    eclipse_calculator,
) -> None:
    event = eclipse_calculator.next_lunar_eclipse_canon(
        julian_day(2027, 7, 1),
        kind="penumbral",
    )
    contacts = find_lunar_contacts_canon(eclipse_calculator, event.jd_ut)
    geometry = lunar_canon_geometry(
        eclipse_calculator,
        _ut_to_tt_nasa_catalog(event.jd_ut),
        method="nasa_shadow_axis_apparent_sun_moon",
    )

    assert event.jd_ut == pytest.approx(contacts.greatest_ut, abs=1.0e-7)
    assert event.data.is_lunar_eclipse
    assert str(event.data.eclipse_type) == "Penumbral"
    assert event.data.eclipse_type.magnitude_umbral == 0.0
    assert event.data.eclipse_type.magnitude_penumbra == pytest.approx(
        geometry.penumbral_magnitude,
        abs=1.0e-12,
    )
    assert event.data.eclipse_magnitude == pytest.approx(
        geometry.penumbral_magnitude,
        abs=1.0e-12,
    )


def test_unified_native_penumbral_analysis_keeps_contact_model_aligned(eclipse_calculator) -> None:
    native = eclipse_calculator.analyze_lunar_eclipse(2744232.0, kind="penumbral", mode="native")
    assert native.mode == "native"
    assert native.event.data.is_lunar_eclipse
    assert native.event.data.is_eclipse()
    assert str(native.event.data.eclipse_type) == "Penumbral"
    assert native.event.data.eclipse_type.magnitude_penumbra > 0.0
    assert abs(native.contacts.greatest - native.event.jd_ut) < 1e-6


@pytest.mark.slow
def test_native_any_search_skips_eclipse_season_full_moon_without_overlap(
    eclipse_calculator,
) -> None:
    event = eclipse_calculator.next_lunar_eclipse(2453307.628820612, kind="any")

    assert event.jd_ut != pytest.approx(2453455.387181155, abs=1.0e-6)
    assert event.data.is_lunar_eclipse
    assert event.data.is_eclipse()
    assert event.data.eclipse_type.magnitude_penumbra > 0.0


@pytest.mark.slow
def test_local_visible_solar_search_requires_actual_disk_overlap(
    eclipse_calculator,
) -> None:
    local = eclipse_calculator.next_solar_eclipse_at_location(
        2457754.5,
        51.4779,
        0.0,
        max_lunations=12,
    )

    # The 2017-02-26 global event is daylight at Greenwich but has no local
    # overlap.  The search must continue to the locally visible 2017-08 event.
    assert local.event.jd_ut > 2457900.0
    assert local.topocentric_overlap
    assert local.sun.visible
    assert local.topocentric_separation_deg < 1.0
    assert local.event.data.is_solar_eclipse
    assert local.event.data.solar_topocentric_separation == pytest.approx(
        local.topocentric_separation_deg,
        abs=1.0e-12,
    )


@pytest.mark.slow
def test_local_visible_solar_result_and_kind_use_local_classification(
    eclipse_calculator,
) -> None:
    local = eclipse_calculator.next_solar_eclipse_at_location(
        2457754.5,
        40.7128,
        -74.0060,
        kind="partial",
        max_lunations=12,
    )

    assert local.event.jd_ut > 2457900.0
    assert local.event.data.eclipse_type.is_partial
    assert not local.event.data.eclipse_type.is_total
    assert local.event.data.eclipse_magnitude == pytest.approx(
        (
            local.event.data.sun_apparent_radius
            + local.event.data.moon_apparent_radius
            - local.topocentric_separation_deg
        )
        / (2.0 * local.event.data.sun_apparent_radius),
        abs=1.0e-12,
    )

    with pytest.raises(RuntimeError, match="No solar eclipse of kind 'total'"):
        eclipse_calculator.next_solar_eclipse_at_location(
            2457754.5,
            40.7128,
            -74.0060,
            kind="total",
            max_lunations=12,
        )


def test_local_lunar_circumstances_api_returns_contact_bundle(eclipse_calculator) -> None:
    local = eclipse_calculator.lunar_local_circumstances(
        2451560.0,
        51.5,
        -0.1,
        kind="total",
        mode="native",
    )

    assert local.analysis.event.data.is_lunar_eclipse
    assert local.analysis.event.data.eclipse_type.is_total
    assert -90.0 <= local.greatest.altitude <= 90.0
    assert 0.0 <= local.greatest.azimuth <= 360.0
    assert local.p1 is not None
    assert local.u1 is not None
    assert local.u2 is not None
    assert local.u3 is not None
    assert local.u4 is not None
    assert local.p4 is not None
    assert local.p1.jd_ut < local.u1.jd_ut < local.u2.jd_ut < local.greatest.jd_ut
    assert local.greatest.jd_ut < local.u3.jd_ut < local.u4.jd_ut < local.p4.jd_ut


def test_solar_local_circumstances_api_returns_observer_bundle(eclipse_calculator) -> None:
    global_event = eclipse_calculator.next_solar_eclipse(
        2451400.0,
        kind="total",
    )
    local = eclipse_calculator.solar_local_circumstances(
        2451400.0,
        50.0,
        0.0,
        kind="total",
    )

    assert local.event == global_event
    assert local.event.data.is_solar_eclipse
    assert local.event.data.eclipse_type.is_total
    assert -90.0 <= local.sun.altitude <= 90.0
    assert -90.0 <= local.moon.altitude <= 90.0
    assert 0.0 <= local.sun.azimuth <= 360.0
    assert 0.0 <= local.moon.azimuth <= 360.0
    assert local.topocentric_separation_deg >= 0.0
    assert local.sun.visible == (local.sun.altitude > 0.0)
    assert local.moon.visible == (local.moon.altitude > 0.0)

