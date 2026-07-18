from __future__ import annotations

import math
import inspect
from dataclasses import FrozenInstanceError, fields, replace
from types import SimpleNamespace

import pytest

import moira.occultations as occultations
import moira.stars as stars_module
from moira.geoutils import wrap_longitude_deg
from moira.occultations import (
    _star_topocentric_target_geometry,
    lunar_star_graze_product_at,
    lunar_star_graze_product_track,
    lunar_star_graze_circumstances,
    lunar_star_occultation,
)


def test_limb_profile_provider_adjusts_occultation_margin() -> None:
    jd = 2460641.97
    lat = 61.17638888888889
    lon = -76.25
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075

    _, base_margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        None,
    )
    _, raised_margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        None,
        0.0,
        lambda _jd, _lat, _lon, _elev, _pa, _dist: 0.01,
    )

    assert abs((raised_margin - base_margin) - 0.01) < 1e-12


def test_lunar_star_graze_circumstances_are_self_consistent() -> None:
    jd = 2460641.97
    lat = 61.17638888888889
    lon = -76.25
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075

    circumstances = lunar_star_graze_circumstances(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
    )

    separation, margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        None,
    )

    assert math.isfinite(circumstances.tan_z)
    assert 0.0 <= circumstances.position_angle_deg < 360.0
    assert 0.0 <= circumstances.axis_angle_deg < 360.0
    assert -180.0 <= circumstances.cusp_angle_deg < 180.0
    assert circumstances.cusp_pole in {"N", "S"}
    assert abs(circumstances.apparent_separation_deg - separation) < 1e-12
    assert abs(circumstances.margin_deg - margin) < 1e-12
    assert abs(circumstances.zenith_distance_deg - (90.0 - circumstances.moon_altitude_deg)) < 1e-12


def test_lunar_star_graze_product_at_defaults_to_nominal_limit() -> None:
    jd = 2460641.97
    lat = 61.17638888888889
    lon = -76.25
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075

    product = lunar_star_graze_product_at(
        star_lon,
        star_lat,
        jd,
        lon,
        lat,
    )

    assert product.product_kind == "nominal_limit"
    assert product.has_profile_conditioned_band is False
    assert product.practical_line_latitude_deg == product.nominal_limit_latitude_deg
    assert product.profile_band_south_latitude_deg is None
    assert product.profile_band_north_latitude_deg is None


def test_lunar_star_graze_product_track_defaults_to_nominal_limit() -> None:
    jd = 2460641.97
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075
    track = lunar_star_graze_product_track(
        star_lon,
        star_lat,
        [jd, jd],
        [-76.25, -63.0],
        [61.17638888888889, 54.40641666666667],
    )

    assert track.product_kind == "nominal_limit"
    assert track.has_profile_conditioned_band is False
    assert track.practical_line_latitude_deg == track.nominal_limit_latitude_deg
    assert track.profile_band_south_latitude_deg is None
    assert track.profile_band_north_latitude_deg is None
    assert len(track.longitude_deg) == 2
    assert len(track.nominal_limit_latitude_deg) == 2


def test_lunar_star_occultation_topocentric_branch_uses_tt_for_star_and_obliquity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sampled_jd_tt: list[float] = []
    obliquity_jd_tt: list[float] = []
    separations = iter((1.0, 2.0, 3.0))

    monkeypatch.setattr(
        occultations,
        "sky_position_at",
        lambda *args, **kwargs: SimpleNamespace(right_ascension=0.0, declination=0.0),
    )
    monkeypatch.setattr(
        occultations,
        "_ut1_to_ephemeris_tt",
        lambda jd, _reader: jd + 0.25,
    )

    def _fake_star_at(name: str, jd_tt: float, **_: object) -> object:
        sampled_jd_tt.append(jd_tt)
        return SimpleNamespace(longitude=10.0, latitude=5.0)

    monkeypatch.setattr(stars_module, "star_at", _fake_star_at)

    def _fake_true_obliquity(jd_tt: float) -> float:
        obliquity_jd_tt.append(jd_tt)
        return 23.4

    monkeypatch.setattr(occultations, "true_obliquity", _fake_true_obliquity)
    monkeypatch.setattr(occultations, "ecliptic_to_equatorial", lambda lon, lat, eps: (lon, lat))
    monkeypatch.setattr(
        occultations,
        "_angular_separation_equatorial",
        lambda *args: next(separations),
    )

    jd_start = 2451545.0
    step_days = 0.1
    lunar_star_occultation(
        10.0,
        5.0,
        "Sirius",
        jd_start,
        jd_start + step_days,
        step_days=step_days,
        observer_lat=51.5,
        observer_lon=-0.1,
        reader=object(),
    )

    expected_jd_tt = [
        jd_start - step_days + 0.25,
        jd_start + 0.25,
        jd_start + step_days + 0.25,
    ]
    assert sampled_jd_tt == pytest.approx(expected_jd_tt, abs=1e-12)
    assert obliquity_jd_tt == pytest.approx(expected_jd_tt, abs=1e-12)


def test_occultation_longitude_wrapping_preserves_positive_180_boundary() -> None:
    assert wrap_longitude_deg(180.0) == 180.0
    assert wrap_longitude_deg(540.0) == 180.0


def test_occultation_greatest_location_honors_objective_eval_limit(
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

    def objective(latitude: float, longitude: float) -> float:
        nonlocal call_count
        call_count += 1
        return scores.get((latitude, longitude), 99.0)

    monkeypatch.setattr(occultations, "_GEO_SEARCH_MAX_OBJECTIVE_EVALS", 5)

    with pytest.raises(
        occultations._OccultationPathSolveError,
        match="evaluation limit exhausted",
    ):
        occultations._solve_occultation_greatest_location(objective)

    assert call_count == 5


def test_star_graze_solver_near_south_pole_never_leaves_legal_latitudes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sampled_latitudes: list[float] = []

    def fake_geometry(
        _star_lon: float,
        _star_lat: float,
        _jd: float,
        latitude: float,
        _longitude: float,
        _reader: object,
        _observer_elev_m: float,
        _provider: object,
        _refraction_adjusted: bool,
    ) -> tuple[float, float, float, float]:
        sampled_latitudes.append(latitude)
        return 0.0, latitude + 89.75, 0.0, 0.0

    monkeypatch.setattr(
        occultations,
        "_star_topocentric_target_geometry",
        fake_geometry,
    )

    root = occultations._solve_star_graze_latitude(
        0.0,
        0.0,
        2451545.0,
        0.0,
        -89.0,
        reader=object(),
    )

    assert root == pytest.approx(-89.75, abs=1e-12)
    assert sampled_latitudes
    assert all(-90.0 <= latitude <= 90.0 for latitude in sampled_latitudes)


def test_star_graze_solver_no_bracket_stops_at_legal_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sampled_latitudes: list[float] = []

    def fake_geometry(
        _star_lon: float,
        _star_lat: float,
        _jd: float,
        latitude: float,
        _longitude: float,
        _reader: object,
        _observer_elev_m: float,
        _provider: object,
        _refraction_adjusted: bool,
    ) -> tuple[float, float, float, float]:
        sampled_latitudes.append(latitude)
        return 0.0, 1.0, 0.0, 0.0

    monkeypatch.setattr(
        occultations,
        "_star_topocentric_target_geometry",
        fake_geometry,
    )

    with pytest.raises(ValueError, match="Could not bracket"):
        occultations._solve_star_graze_latitude(
            0.0,
            0.0,
            2451545.0,
            0.0,
            -89.0,
            reader=object(),
        )

    assert -90.0 in sampled_latitudes
    assert all(-90.0 <= latitude <= 90.0 for latitude in sampled_latitudes)


def test_profile_refinement_cannot_newton_step_beyond_a_pole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sampled_latitudes: list[float] = []
    profile = object()

    def fake_geometry(
        _star_lon: float,
        _star_lat: float,
        _jd: float,
        latitude: float,
        _longitude: float,
        _reader: object,
        _observer_elev_m: float,
        provider: object,
        _refraction_adjusted: bool,
    ) -> tuple[float, float, float, float]:
        sampled_latitudes.append(latitude)
        root = 91.0 if provider is profile else 89.75
        return 0.0, latitude - root, 0.0, 0.0

    monkeypatch.setattr(
        occultations,
        "_star_topocentric_target_geometry",
        fake_geometry,
    )

    with pytest.raises(ValueError, match="Could not bracket"):
        occultations._solve_star_graze_latitude(
            0.0,
            0.0,
            2451545.0,
            0.0,
            89.0,
            reader=object(),
            limb_profile_provider=profile,  # type: ignore[arg-type]
        )

    assert sampled_latitudes
    assert all(-90.0 <= latitude <= 90.0 for latitude in sampled_latitudes)


def test_directed_graze_boundaries_select_opposite_band_limbs() -> None:
    sampled_latitudes: list[float] = []

    def band_margin(latitude: float) -> float:
        sampled_latitudes.append(latitude)
        return 1.0 - (latitude / 10.0) ** 2

    north = occultations._solve_directed_latitude_root(band_margin, 0.0, 1)
    south = occultations._solve_directed_latitude_root(band_margin, 0.0, -1)

    assert north == pytest.approx(10.0, abs=1e-12)
    assert south == pytest.approx(-10.0, abs=1e-12)
    assert all(-90.0 <= latitude <= 90.0 for latitude in sampled_latitudes)


@pytest.mark.parametrize(
    ("nominal_limit", "expected_profile_seeds"),
    (
        (89.75, (90.0, 88.75)),
        (-89.75, (-88.75, -90.0)),
    ),
)
def test_profile_conditioned_product_bounds_directional_seeds_at_poles(
    monkeypatch: pytest.MonkeyPatch,
    nominal_limit: float,
    expected_profile_seeds: tuple[float, float],
) -> None:
    profile = object()
    sampled_guesses: list[tuple[float, object | None]] = []

    def fake_solve(
        _star_lon: float,
        _star_lat: float,
        _jd: float,
        _longitude: float,
        guess_latitude: float,
        *,
        observer_elev_m: float,
        reader: object,
        limb_profile_provider: object | None,
        refraction_adjusted: bool,
    ) -> float:
        del observer_elev_m, reader, refraction_adjusted
        if not -90.0 <= guess_latitude <= 90.0:
            raise ValueError("illegal latitude seed")
        sampled_guesses.append((guess_latitude, limb_profile_provider))
        if limb_profile_provider is None:
            return nominal_limit
        return guess_latitude

    monkeypatch.setattr(occultations, "_solve_star_graze_latitude", fake_solve)

    product = lunar_star_graze_product_at(
        0.0,
        0.0,
        2451545.0,
        0.0,
        nominal_limit,
        reader=object(),
        limb_profile_provider=profile,  # type: ignore[arg-type]
    )

    assert sampled_guesses[0] == (nominal_limit, None)
    assert tuple(guess for guess, _provider in sampled_guesses[1:]) == expected_profile_seeds
    assert all(-90.0 <= guess <= 90.0 for guess, _provider in sampled_guesses)
    assert product.profile_band_south_latitude_deg == min(expected_profile_seeds)
    assert product.profile_band_north_latitude_deg == max(expected_profile_seeds)


def test_moon_axis_position_angle_uses_explicit_tt_without_double_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, float] = {}

    def _fake_planet_at(body: str, jd_ut: float, **kwargs: object) -> object:
        captured["jd_ut"] = jd_ut
        captured["jd_tt"] = float(kwargs["jd_tt"])
        return SimpleNamespace(longitude=10.0, latitude=5.0)

    monkeypatch.setattr(occultations, "planet_at", _fake_planet_at)
    monkeypatch.setattr(occultations, "true_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr(occultations, "nutation", lambda jd_tt: (0.0, 0.0))
    monkeypatch.setattr(occultations, "ecliptic_to_equatorial", lambda lon, lat, eps: (lon, lat))

    occultations._moon_axis_position_angle_deg(2451545.123)

    assert captured["jd_ut"] == pytest.approx(2451545.123)
    assert captured["jd_tt"] == pytest.approx(2451545.123)


def test_occultation_greatest_location_admits_an_exact_pole() -> None:
    latitude, longitude, distance = occultations._solve_occultation_greatest_location(
        lambda lat, lon: occultations._surface_distance_km(lat, lon, 90.0, 73.0)
    )

    assert latitude == 90.0
    assert longitude == 0.0
    assert distance < 1e-8


def test_clearance_center_maximizes_footprint_not_separation() -> None:
    def geometry(
        _jd: float,
        latitude: float,
        _longitude: float,
    ) -> tuple[float, float, float, float]:
        return abs(latitude), 1.0 - abs(latitude - 10.0), 0.0, 0.0

    center = occultations._solve_occultation_clearance_center(
        geometry,
        0.0,
        complete_surface=True,
    )

    assert center.latitude_deg == pytest.approx(10.0, abs=1e-8)
    assert center.clearance_deg == pytest.approx(1.0, abs=1e-12)
    assert center.separation_deg == pytest.approx(10.0, abs=1e-8)


def test_cross_track_limits_are_seam_safe_and_width_is_two_half_widths() -> None:
    center = occultations.OccultationPathPoint(0.0, 0.0, 180.0, 0.0, 0.5)
    before = occultations.OccultationPathPoint(-1.0, 0.0, 179.8, 0.0, 0.5)
    after = occultations.OccultationPathPoint(1.0, 0.0, -179.8, 0.0, 0.5)
    direction = occultations._track_direction_ne(before, center, after)
    half_width_km = 75.0

    def geometry(
        _jd: float,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float, float, float]:
        distance = occultations._surface_distance_km(0.0, 180.0, latitude, longitude)
        separation = math.degrees(distance / occultations.EARTH_RADIUS_KM)
        clearance = math.degrees((half_width_km - distance) / occultations.EARTH_RADIUS_KM)
        return separation, clearance, 0.0, 0.0

    center = replace(center, clearance_deg=math.degrees(half_width_km / occultations.EARTH_RADIUS_KM))
    left = occultations._solve_cross_track_boundary(
        geometry,
        center,
        direction,
        occultations.OccultationPathBoundarySide.LEFT,
    )
    right = occultations._solve_cross_track_boundary(
        geometry,
        center,
        direction,
        occultations.OccultationPathBoundarySide.RIGHT,
    )

    assert direction[0] == pytest.approx(0.0, abs=1e-12)
    assert direction[1] > 0.0
    assert occultations._surface_distance_km(0.0, 179.9, 0.0, -179.9) < 23.0
    assert left.point.latitude_deg > 0.0
    assert right.point.latitude_deg < 0.0
    assert left.cross_track_distance_km + right.cross_track_distance_km == pytest.approx(
        2.0 * half_width_km,
        abs=2e-6,
    )


def test_boundary_endpoint_coalesces_only_within_declared_residual() -> None:
    center = occultations.OccultationPathPoint(
        0.0,
        10.0,
        20.0,
        0.25,
        -2.6119524876300204e-09,
    )
    boundary = occultations._solve_cross_track_boundary(
        lambda *_: (0.0, 0.0, 0.0, 0.0),
        center,
        (0.0, 1.0),
        occultations.OccultationPathBoundarySide.LEFT,
    )
    assert boundary.cross_track_distance_km == 0.0

    with pytest.raises(occultations._OccultationPathSolveError, match="outside"):
        occultations._solve_cross_track_boundary(
            lambda *_: (0.0, 0.0, 0.0, 0.0),
            replace(center, clearance_deg=-2e-7),
            (0.0, 1.0),
            occultations.OccultationPathBoundarySide.LEFT,
        )


def test_exact_pole_short_containment_is_solved_continuously() -> None:
    jd_start = -0.001
    jd_end = 0.001
    speed_km_per_day = 100_000.0
    half_width_km = 1.0

    def center_at(jd_ut: float) -> occultations.OccultationPathPoint:
        latitude, longitude = occultations._offset_geographic_km(
            90.0,
            0.0,
            speed_km_per_day * jd_ut,
            0.0,
        )
        return occultations.OccultationPathPoint(
            jd_ut,
            latitude,
            longitude,
            0.0,
            math.degrees(half_width_km / occultations.EARTH_RADIUS_KM),
        )

    def geometry(
        jd_ut: float,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float, float, float]:
        center = center_at(jd_ut)
        distance = occultations._surface_distance_km(
            center.latitude_deg,
            center.longitude_deg,
            latitude,
            longitude,
        )
        return (
            math.degrees(distance / occultations.EARTH_RADIUS_KM),
            math.degrees((half_width_km - distance) / occultations.EARTH_RADIUS_KM),
            0.0,
            0.0,
        )

    crossings = occultations._solve_occultation_pole_crossings(
        geometry,
        center_at,
        jd_start,
        jd_end,
    )

    assert tuple(crossing.pole for crossing in crossings) == (
        occultations.OccultationGeographicPole.NORTH,
        occultations.OccultationGeographicPole.NORTH,
    )
    assert tuple(crossing.phase for crossing in crossings) == (
        occultations.OccultationPoleCrossingPhase.INGRESS,
        occultations.OccultationPoleCrossingPhase.EGRESS,
    )
    assert crossings[0].point.jd_ut == pytest.approx(-1e-5, abs=1e-10)
    assert crossings[1].point.jd_ut == pytest.approx(1e-5, abs=1e-10)
    assert (crossings[1].point.jd_ut - crossings[0].point.jd_ut) * 86400.0 < 300.0
    assert all(crossing.point.longitude_deg == 0.0 for crossing in crossings)
    assert all(crossing.boundary_side is None for crossing in crossings)


def test_pole_contacts_coalesce_with_declared_boundary_residual() -> None:
    edge_clearance = -5.0e-8

    def north_clearance(jd_ut: float) -> float:
        return 1.0e-3 - (1.0e-3 - edge_clearance) * ((jd_ut - 0.5) / 0.5) ** 2

    def geometry(
        jd_ut: float,
        latitude: float,
        _longitude: float,
    ) -> tuple[float, float, float, float]:
        value = north_clearance(jd_ut) if latitude > 0.0 else -1.0
        return 0.0, value, 0.0, 0.0

    def center_at(jd_ut: float) -> occultations.OccultationPathPoint:
        return occultations.OccultationPathPoint(jd_ut, 0.0, jd_ut * 10.0, 0.0, 1.0)

    crossings = occultations._solve_occultation_pole_crossings(
        geometry,
        center_at,
        0.0,
        1.0,
    )

    assert tuple(crossing.point.jd_ut for crossing in crossings) == (0.0, 1.0)
    assert all(
        crossing.point.clearance_deg == pytest.approx(edge_clearance, abs=1e-15)
        for crossing in crossings
    )


def test_disjoint_pole_containment_intervals_fail_closed() -> None:
    def north_clearance(jd_ut: float) -> float:
        return max(
            1.0e-3 - ((jd_ut - 0.3) / 0.03) ** 2,
            1.0e-3 - ((jd_ut - 0.7) / 0.03) ** 2,
        )

    def geometry(
        jd_ut: float,
        latitude: float,
        _longitude: float,
    ) -> tuple[float, float, float, float]:
        value = north_clearance(jd_ut) if latitude > 0.0 else -1.0
        return 0.0, value, 0.0, 0.0

    with pytest.raises(
        occultations._OccultationPathSolveError,
        match="multiple disjoint",
    ):
        occultations._solve_occultation_pole_crossings(
            geometry,
            lambda jd_ut: occultations.OccultationPathPoint(
                jd_ut,
                0.0,
                jd_ut * 10.0,
                0.0,
                1.0,
            ),
            0.0,
            1.0,
        )


def _valid_synthetic_topology() -> occultations.OccultationPathTopology:
    centers = tuple(
        occultations.OccultationPathPoint(
            float(index),
            0.0,
            float(index),
            0.0,
            0.0 if index in {0, 8} else 1.0,
        )
        for index in range(9)
    )

    def track(side: occultations.OccultationPathBoundarySide) -> occultations.OccultationPathBoundaryTrack:
        return occultations.OccultationPathBoundaryTrack(
            side,
            tuple(
                occultations.OccultationPathBoundaryPoint(
                    side,
                    occultations.OccultationPathPoint(
                        center.jd_ut,
                        center.latitude_deg,
                        center.longitude_deg,
                        center.separation_deg,
                        0.0,
                    ),
                    0.0,
                )
                for center in centers
            ),
        )

    left = track(occultations.OccultationPathBoundarySide.LEFT)
    right = track(occultations.OccultationPathBoundarySide.RIGHT)
    summary = occultations.OccultationPathGeometry(
        occulting_body=occultations.Body.MOON,
        occulted_body="Synthetic",
        jd_greatest_ut=4.0,
        central_line_lats=tuple(point.latitude_deg for point in centers),
        central_line_lons=tuple(point.longitude_deg for point in centers),
        path_width_km=0.0,
        duration_at_greatest_s=8.0 * 86400.0,
    )
    return occultations.OccultationPathTopology(
        summary=summary,
        topology=occultations.OccultationPathTopologyKind.TWO_SIDED_BAND,
        centers=centers,
        boundaries=(left, right),
        greatest_left=left.points[4],
        greatest_right=right.points[4],
        pole_crossings=(),
        lunar_limb_model="SPHERICAL_MEAN_LIMB",
        target_model="POINT_SOURCE",
        observer_elevation_m=12.5,
    )


def test_topology_vessel_is_immutable_and_geometrically_bound() -> None:
    topology = _valid_synthetic_topology()

    assert topology.observer_elevation_m == 12.5
    assert topology.summary.central_line_lats == tuple(point.latitude_deg for point in topology.centers)
    with pytest.raises(FrozenInstanceError):
        topology.observer_elevation_m = 0.0  # type: ignore[misc]

    bad_left_point = replace(topology.boundaries[0].points[0], cross_track_distance_km=1.0)
    bad_left = replace(
        topology.boundaries[0],
        points=(bad_left_point, *topology.boundaries[0].points[1:]),
    )
    with pytest.raises(ValueError, match="spherical center distance"):
        replace(topology, boundaries=(bad_left, topology.boundaries[1]))

    crossing = occultations.OccultationPoleCrossing(
        occultations.OccultationGeographicPole.NORTH,
        occultations.OccultationPoleCrossingPhase.INGRESS,
        occultations.OccultationPathPoint(4.0, 90.0, 73.0, 0.0, 0.0),
        None,
    )
    with pytest.raises(ValueError, match="one ingress then one egress"):
        replace(topology, pole_crossings=(crossing,))


def test_topology_vessel_enforces_lunar_target_and_duration_semantics() -> None:
    topology = _valid_synthetic_topology()

    with pytest.raises(ValueError, match="Moon as occulting"):
        replace(
            topology,
            summary=replace(topology.summary, occulting_body=occultations.Body.MARS),
        )
    with pytest.raises(ValueError, match="solid-body topology"):
        replace(topology, target_model="JPL_EQUATORIAL_SOLID_BODY")
    with pytest.raises(ValueError, match="point-source topology"):
        replace(
            topology,
            summary=replace(topology.summary, occulted_body=occultations.Body.MARS),
        )
    with pytest.raises(ValueError, match="cannot exceed"):
        replace(
            topology,
            summary=replace(
                topology.summary,
                duration_at_greatest_s=8.0 * 86400.0 + 1.0,
            ),
        )
    with pytest.raises(ValueError, match="must be positive"):
        replace(
            topology,
            summary=replace(topology.summary, duration_at_greatest_s=0.0),
        )


def test_topology_observer_elevation_has_a_wgs84_computational_floor() -> None:
    floor = occultations._OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M
    below_floor = math.nextafter(floor, -math.inf)

    assert occultations._validate_topology_observer_elevation(floor) == floor
    with pytest.raises(ValueError, match="semi-minor-axis"):
        occultations._validate_topology_observer_elevation(below_floor)
    with pytest.raises(ValueError, match="semi-minor-axis"):
        replace(
            _valid_synthetic_topology(),
            observer_elevation_m=below_floor,
        )


def test_legacy_path_vessel_fields_and_sampling_contract_are_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(field.name for field in fields(occultations.OccultationPathGeometry)) == (
        "occulting_body",
        "occulted_body",
        "jd_greatest_ut",
        "central_line_lats",
        "central_line_lons",
        "path_width_km",
        "duration_at_greatest_s",
    )
    boundary_calls: list[occultations.OccultationPathBoundarySide] = []

    def fake_center(
        _position_func: object,
        jd_ut: float,
        **_kwargs: object,
    ) -> occultations.OccultationPathPoint:
        return occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            jd_ut * 10.0,
            0.0,
            0.5 - abs(jd_ut),
        )

    def fake_boundary(
        _position_func: object,
        center: occultations.OccultationPathPoint,
        _direction: tuple[float, float],
        side: occultations.OccultationPathBoundarySide,
    ) -> occultations.OccultationPathBoundaryPoint:
        boundary_calls.append(side)
        return occultations.OccultationPathBoundaryPoint(
            side,
            replace(center, clearance_deg=0.0),
            10.0 if side is occultations.OccultationPathBoundarySide.LEFT else 11.0,
        )

    monkeypatch.setattr(occultations, "_solve_occultation_clearance_center", fake_center)
    monkeypatch.setattr(occultations, "_solve_cross_track_boundary", fake_boundary)

    def geometry(
        jd_ut: float,
        _latitude: float,
        _longitude: float,
    ) -> tuple[float, float, float, float]:
        return 0.0, 0.5 - abs(jd_ut), 0.0, 0.0

    summaries = tuple(
        occultations._build_occultation_path_geometry(
            occulted_body="Synthetic",
            jd_mid=0.0,
            position_func=geometry,
            sample_count=count,
        )
        for count in (1, 2, 5)
    )

    assert tuple(len(summary.central_line_lats) for summary in summaries) == (1, 2, 5)
    assert {summary.path_width_km for summary in summaries} == {21.0}
    assert all(
        summary.duration_at_greatest_s == pytest.approx(86400.0, abs=1e-6)
        for summary in summaries
    )
    assert boundary_calls == [
        occultations.OccultationPathBoundarySide.LEFT,
        occultations.OccultationPathBoundarySide.RIGHT,
    ] * 3


def test_legacy_path_preserves_zero_non_event_without_boundary_slices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            12.0,
            34.0,
            1.0,
            -0.1,
        ),
    )

    def forbidden_boundary(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy non-event must not solve boundary slices")

    monkeypatch.setattr(occultations, "_solve_cross_track_boundary", forbidden_boundary)
    summary = occultations._build_occultation_path_geometry(
        occulted_body="Synthetic",
        jd_mid=0.0,
        position_func=lambda *_: (1.0, -0.1, 0.0, 0.0),
        sample_count=9,
    )

    assert summary.central_line_lats == (12.0,)
    assert summary.central_line_lons == (34.0,)
    assert summary.path_width_km == 0.0
    assert summary.duration_at_greatest_s == 0.0


def test_topology_at_non_event_is_a_domain_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            1.0,
            -0.1,
        ),
    )

    with pytest.raises(occultations._OccultationPathNotPresentError) as exc_info:
        occultations.lunar_occultation_path_topology_at(
            occultations.Body.MARS,
            0.0,
            reader=object(),
        )

    assert isinstance(exc_info.value, ValueError)
    assert not isinstance(exc_info.value, ArithmeticError)


def test_greatest_site_duration_is_not_global_footprint_lifetime() -> None:
    center = occultations.OccultationPathPoint(0.0, 10.0, 20.0, 0.0, 0.1)

    def geometry(
        jd_ut: float,
        _latitude: float,
        _longitude: float,
    ) -> tuple[float, float, float, float]:
        return 0.0, 0.1 - abs(jd_ut), 0.0, 0.0

    duration_s = occultations._solve_occultation_greatest_site_duration(
        geometry,
        center,
        -1.0,
        1.0,
    )

    assert duration_s == pytest.approx(0.2 * 86400.0, abs=1e-6)
    assert duration_s < 2.0 * 86400.0


def test_planetary_path_clearance_uses_jpl_radius_and_topocentric_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    positions = iter(
        (
            SimpleNamespace(
                right_ascension=0.0,
                declination=0.0,
                distance=400_000.0,
                azimuth=0.0,
                altitude=45.0,
            ),
            SimpleNamespace(
                right_ascension=0.0,
                declination=0.0,
                distance=123_456.0,
                azimuth=0.0,
                altitude=45.0,
            ),
        )
    )
    radius_calls: list[tuple[float, float]] = []
    monkeypatch.setattr(occultations, "sky_position_at", lambda *args, **kwargs: next(positions))
    monkeypatch.setattr(occultations, "_angular_separation_equatorial", lambda *args: 0.0)
    monkeypatch.setattr(occultations, "_position_angle_equatorial", lambda *args: 0.0)

    def apparent_radius(radius_km: float, distance_km: float) -> float:
        radius_calls.append((radius_km, distance_km))
        return radius_km / distance_km

    monkeypatch.setattr(occultations, "_apparent_radius", apparent_radius)
    occultations._planet_topocentric_target_geometry(
        occultations.Body.MARS,
        0.0,
        0.0,
        0.0,
        object(),
    )

    assert radius_calls[-1] == (3396.19, 123_456.0)


def test_parallax_envelope_admits_geocentrically_wide_polar_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def planet_at(body: str, *_: object, **__: object) -> object:
        if body == occultations.Body.MOON:
            return SimpleNamespace(longitude=0.0, latitude=0.0, distance=384_400.0)
        return SimpleNamespace(longitude=1.1, latitude=0.0, distance=80_000_000.0)

    monkeypatch.setattr(occultations, "planet_at", planet_at)
    envelope = occultations._planet_occultation_candidate_envelope(
        occultations.Body.MARS,
        0.0,
        0.0,
        object(),
    )

    assert 1.1 > occultations._MOON_MEAN_RADIUS_DEG
    assert envelope > 0.0


def test_parallax_bound_reaches_180_degrees_inside_the_observer_sphere() -> None:
    exterior = occultations._horizontal_parallax_deg(100.0, 50.0)

    assert exterior == pytest.approx(30.0, abs=1.0e-12)
    assert occultations._horizontal_parallax_deg(100.0, 100.0) == 180.0
    assert occultations._horizontal_parallax_deg(100.0, 101.0) == 180.0
    with pytest.raises(ArithmeticError, match="observer radius"):
        occultations._horizontal_parallax_deg(100.0, -1.0)


def test_sun_is_legacy_only_not_an_occultation_topology_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="admitted JPL solid-body planet"):
        occultations.lunar_occultation_path_topology_at(
            occultations.Body.SUN,
            0.0,
            reader=object(),
        )

    positions = iter(
        (
            SimpleNamespace(
                right_ascension=0.0,
                declination=0.0,
                distance=400_000.0,
                azimuth=0.0,
                altitude=45.0,
            ),
            SimpleNamespace(
                right_ascension=0.0,
                declination=0.0,
                distance=149_000_000.0,
                azimuth=0.0,
                altitude=45.0,
            ),
        )
    )
    radius_calls: list[tuple[float, float]] = []
    monkeypatch.setattr(occultations, "sky_position_at", lambda *args, **kwargs: next(positions))
    monkeypatch.setattr(occultations, "_angular_separation_equatorial", lambda *args: 0.0)
    monkeypatch.setattr(occultations, "_position_angle_equatorial", lambda *args: 0.0)

    def apparent_radius(radius_km: float, distance_km: float) -> float:
        radius_calls.append((radius_km, distance_km))
        return radius_km / distance_km

    monkeypatch.setattr(occultations, "_apparent_radius", apparent_radius)
    occultations._planet_topocentric_target_geometry(
        occultations.Body.SUN,
        0.0,
        0.0,
        0.0,
        object(),
    )

    assert radius_calls[-1] == (occultations.SUN_RADIUS_KM, 149_000_000.0)


@pytest.mark.parametrize(
    ("span_days", "step_days"),
    (
        (1.0, 0.2500001),
        (400.0001, 0.25),
        (400.0, 0.09),
        (1.0, math.nextafter(0.0, 1.0)),
    ),
)
def test_topology_range_policy_rejects_before_reader_or_envelope(
    monkeypatch: pytest.MonkeyPatch,
    span_days: float,
    step_days: float,
) -> None:
    reader_calls = 0

    def forbidden_reader() -> object:
        nonlocal reader_calls
        reader_calls += 1
        raise AssertionError("invalid topology range must not acquire a reader")

    monkeypatch.setattr(occultations, "get_reader", forbidden_reader)
    start = 2451545.0
    with pytest.raises(ValueError):
        occultations.lunar_occultation_path_topology(
            occultations.Body.MARS,
            start,
            start + span_days,
            step_days=step_days,
        )

    assert reader_calls == 0


def test_topology_range_rejects_nonadvancing_binary64_lattice() -> None:
    start = 2451545.0
    end = math.nextafter(start, math.inf)

    with pytest.raises(ValueError, match="strictly advancing"):
        occultations._validate_topology_range(
            start,
            end,
            (end - start) / 2.0,
        )


def test_topology_range_uses_deterministic_ceiling_segment_count() -> None:
    start, end, step, segments = occultations._validate_topology_range(
        10.0,
        11.0,
        0.24,
    )

    assert (start, end, step) == (10.0, 11.0, 0.24)
    assert segments == 5


@pytest.mark.parametrize("peak_jd", (0.02, 0.98))
def test_candidate_search_recovers_hidden_first_and_last_cell_peaks(
    monkeypatch: pytest.MonkeyPatch,
    peak_jd: float,
) -> None:
    def clearance(jd_ut: float) -> float:
        return 1.0e-4 - (jd_ut - peak_jd) ** 2

    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            clearance(jd_ut),
        ),
    )
    epochs = occultations._find_global_occultation_epochs(
        jd_start=0.0,
        jd_end=1.0,
        step_days=0.25,
        segment_count=4,
        candidate_envelope=clearance,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    )

    assert epochs == pytest.approx((peak_jd,), abs=1e-7)


def test_candidate_search_rejects_constrained_global_boundary_maximum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clearance = lambda jd_ut: 1.0 - jd_ut
    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            clearance(jd_ut),
        ),
    )

    assert occultations._find_global_occultation_epochs(
        jd_start=0.0,
        jd_end=1.0,
        step_days=0.25,
        segment_count=4,
        candidate_envelope=clearance,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    ) == ()


def test_candidate_search_expands_an_internal_artificial_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = lambda jd_ut: 1.0 - (jd_ut - 0.5) ** 2
    exact = lambda jd_ut: 0.25 - (jd_ut - 0.25) ** 2
    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            exact(jd_ut),
        ),
    )
    epochs = occultations._find_global_occultation_epochs(
        jd_start=0.0,
        jd_end=1.0,
        step_days=0.25,
        segment_count=4,
        candidate_envelope=envelope,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    )

    assert epochs == pytest.approx((0.25,), abs=1e-7)


def test_candidate_dedup_uses_solver_scale_and_strongest_earliest_policy() -> None:
    tolerance = occultations._occultation_candidate_time_tolerance(
        40_000_000.0,
        40_000_001.0,
    )
    expected = max(4.0e-8, 8.0 * math.ulp(40_000_001.0))
    candidates = occultations._deduplicate_occultation_candidates(
        [
            (10.0, 1.0),
            (10.0 + tolerance / 2.0, 2.0),
            (20.0, 3.0),
            (20.0 + tolerance / 2.0, 3.0),
        ],
        tolerance_days=tolerance,
    )

    assert tolerance == expected
    assert candidates == (
        (10.0 + tolerance / 2.0, 2.0),
        (20.0, 3.0),
    )


def test_candidate_support_grouping_is_transitive_and_preserves_gaps() -> None:
    groups = occultations._group_occultation_candidates_by_positive_support(
        [
            (0.5, 1.0, 0.0, 1.0),
            (1.4, 2.0, 0.9, 2.0),
            (2.4, 3.0, 1.9, 3.0),
            (4.5, 4.0, 4.0, 5.0),
        ],
        tolerance_days=1.0e-8,
    )

    assert tuple(len(group) for group in groups) == (3, 1)
    assert groups[0][0][2:] == (0.0, 1.0)
    assert groups[0][-1][2:] == (1.9, 3.0)
    assert groups[1][0][2:] == (4.0, 5.0)

    touching = occultations._group_occultation_candidates_by_positive_support(
        [
            (0.5, 1.0, 0.0, 1.0),
            (1.5, 1.0, 1.0, 2.0),
        ],
        tolerance_days=1.0e-8,
    )
    assert tuple(len(group) for group in touching) == (1, 1)


def test_candidate_search_coalesces_one_flat_positive_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def clearance(jd_ut: float) -> float:
        return 0.1 - 2.0 * max(abs(jd_ut - 0.5) - 0.2, 0.0) ** 2

    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            clearance(jd_ut),
        ),
    )
    epochs = occultations._find_global_occultation_epochs(
        jd_start=0.0,
        jd_end=1.0,
        step_days=0.25,
        segment_count=4,
        candidate_envelope=clearance,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    )

    assert len(epochs) == 1
    assert 0.3 <= epochs[0] <= 0.7


def test_candidate_search_keeps_exact_positive_components_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def clearance(jd_ut: float) -> float:
        return max(
            0.01 - ((jd_ut - 0.3) / 0.08) ** 2,
            0.01 - ((jd_ut - 0.7) / 0.08) ** 2,
        )

    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            clearance(jd_ut),
        ),
    )
    epochs = occultations._find_global_occultation_epochs(
        jd_start=0.0,
        jd_end=1.0,
        step_days=0.25,
        segment_count=4,
        candidate_envelope=clearance,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    )

    assert epochs == pytest.approx((0.3, 0.7), abs=1e-7)


def test_component_global_greatest_outside_request_suppresses_interior_hump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def clearance(jd_ut: float) -> float:
        return (
            0.005
            - 0.02 * (jd_ut - 0.6) ** 2
            + 0.03 * math.exp(-((jd_ut - 0.4) / 0.08) ** 2)
            + 0.06 * math.exp(-((jd_ut - 1.0) / 0.08) ** 2)
        )

    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            clearance(jd_ut),
        ),
    )
    epochs = occultations._find_global_occultation_epochs(
        jd_start=0.25,
        jd_end=0.75,
        step_days=0.125,
        segment_count=4,
        candidate_envelope=clearance,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    )

    assert epochs == ()


def test_component_global_greatest_selects_stronger_in_range_hump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def clearance(jd_ut: float) -> float:
        return (
            0.005
            - 0.02 * (jd_ut - 0.5) ** 2
            + 0.03 * math.exp(-((jd_ut - 0.4) / 0.06) ** 2)
            + 0.06 * math.exp(-((jd_ut - 0.65) / 0.06) ** 2)
        )

    monkeypatch.setattr(
        occultations,
        "_solve_occultation_clearance_center",
        lambda _position_func, jd_ut, **_kwargs: occultations.OccultationPathPoint(
            jd_ut,
            0.0,
            0.0,
            0.0,
            clearance(jd_ut),
        ),
    )
    epochs = occultations._find_global_occultation_epochs(
        jd_start=0.25,
        jd_end=0.75,
        step_days=0.125,
        segment_count=4,
        candidate_envelope=clearance,
        position_func=lambda *_: (0.0, 0.0, 0.0, 0.0),
    )

    assert len(epochs) == 1
    assert epochs[0] == pytest.approx(0.65, abs=0.01)
    assert clearance(epochs[0]) > clearance(0.4)


def test_component_global_greatest_lattice_has_explicit_budget() -> None:
    with pytest.raises(
        occultations._OccultationPathSolveError,
        match="lattice budget exceeded",
    ):
        occultations._solve_occultation_component_greatest(
            lambda jd_ut: occultations.OccultationPathPoint(
                jd_ut,
                0.0,
                0.0,
                0.0,
                1.0,
            ),
            0.0,
            3.0,
            ((1.0, 1.0),),
        )


def test_subsecond_translated_footprint_has_stable_greatest_tangent_and_width() -> None:
    epoch_delta_days = 0.160973 / 86400.0

    def footprint_center(jd_ut: float) -> tuple[float, float]:
        return 20.0 + 4.0 * jd_ut, 30.0 + 6.0 * jd_ut

    def geometry(
        jd_ut: float,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float, float, float]:
        center_latitude, center_longitude = footprint_center(jd_ut)
        north_km = (latitude - center_latitude) * 111.32
        east_km = (
            (longitude - center_longitude)
            * 111.32
            * math.cos(math.radians(center_latitude))
        )
        ellipse_radius = math.hypot(north_km / 120.0, east_km / 200.0)
        return ellipse_radius, 1.0 - ellipse_radius, 0.0, 0.0

    def direction_and_width(jd_ut: float) -> tuple[tuple[float, float], float]:
        center = occultations._solve_occultation_clearance_center(
            geometry,
            jd_ut,
            complete_surface=True,
            refinement_steps_deg=occultations._GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG,
        )
        direction = occultations._solve_occultation_greatest_track_direction(
            geometry,
            center,
        )
        left = occultations._solve_cross_track_boundary(
            geometry,
            center,
            direction,
            occultations.OccultationPathBoundarySide.LEFT,
        )
        right = occultations._solve_cross_track_boundary(
            geometry,
            center,
            direction,
            occultations.OccultationPathBoundarySide.RIGHT,
        )
        return direction, left.cross_track_distance_km + right.cross_track_distance_km

    first_direction, first_width = direction_and_width(0.0)
    second_direction, second_width = direction_and_width(epoch_delta_days)

    assert second_direction == pytest.approx(first_direction, abs=2.0e-4)
    assert second_width == pytest.approx(first_width, abs=0.02)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"jd_start": 2.0, "jd_end": 1.0},
        {"jd_start": math.nan, "jd_end": 2.0},
        {"jd_start": 1.0, "jd_end": 2.0, "step_days": 0.0},
        {"jd_start": 1.0, "jd_end": 2.0, "sample_count": False},
        {"jd_start": 1.0, "jd_end": 2.0, "sample_count": 8},
        {"jd_start": 1.0, "jd_end": 2.0, "sample_count": 722},
        {"jd_start": 1.0, "jd_end": 2.0, "observer_elev_m": math.inf},
    ),
)
def test_planet_topology_rejects_invalid_inputs_before_kernel(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        occultations.lunar_occultation_path_topology(
            occultations.Body.MARS,
            reader=object(),
            **kwargs,
        )


@pytest.mark.parametrize(
    ("star_lon", "star_lat", "star_name"),
    (
        (math.inf, 0.0, "Star"),
        (0.0, 91.0, "Star"),
        (0.0, 0.0, "  "),
        (0.0, 0.0, " Star "),
        (0.0, 0.0, "Sun"),
        (0.0, 0.0, "mars"),
    ),
)
def test_star_topology_rejects_invalid_identity_before_kernel(
    star_lon: float,
    star_lat: float,
    star_name: str,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        occultations.lunar_star_occultation_path_topology_at(
            star_lon,
            star_lat,
            star_name,
            1.0,
            reader=object(),
        )


def test_first_class_topology_has_no_unbounded_limb_provider_parameter() -> None:
    for function in (
        occultations.lunar_occultation_path_topology,
        occultations.lunar_occultation_path_topology_at,
        occultations.lunar_star_occultation_path_topology,
        occultations.lunar_star_occultation_path_topology_at,
    ):
        assert "limb_profile_provider" not in inspect.signature(function).parameters


def test_minimum_search_terminates_below_jd_binary64_spacing() -> None:
    center = 2461318.712345678
    calls = 0

    def objective(jd_ut: float) -> float:
        nonlocal calls
        calls += 1
        return (jd_ut - center) ** 2

    jd_minimum, value = occultations._bisect_minimum(
        objective,
        center - 0.1,
        center + 0.1,
        tol=1.0e-20,
    )

    assert abs(jd_minimum - center) <= 4.0 * math.ulp(center)
    assert value <= (4.0 * math.ulp(center)) ** 2
    assert calls < 128


@pytest.mark.parametrize(
    ("left", "right", "tolerance"),
    (
        (math.nan, 2.0, 1e-6),
        (1.0, math.inf, 1e-6),
        (2.0, 1.0, 1e-6),
        (1.0, 2.0, 0.0),
        (1.0, 2.0, math.nan),
    ),
)
def test_minimum_search_rejects_invalid_bounds_and_tolerance(
    left: float,
    right: float,
    tolerance: float,
) -> None:
    with pytest.raises(ValueError):
        occultations._bisect_minimum(
            lambda value: value * value,
            left,
            right,
            tol=tolerance,
        )


def test_bisection_root_stops_when_jd_midpoint_cannot_advance() -> None:
    left = 2461318.75
    right = math.nextafter(left, math.inf)
    calls = 0

    def objective(jd_ut: float) -> float:
        nonlocal calls
        calls += 1
        return -1.0 if jd_ut == left else 1.0

    root = occultations._bisection_root(objective, left, right)

    assert root in {left, right}
    assert calls == 2


@pytest.mark.parametrize(
    ("track_direction", "pole", "expected"),
    (
        (
            (0.0, 1.0),
            occultations.OccultationGeographicPole.NORTH,
            occultations.OccultationPathBoundarySide.LEFT,
        ),
        (
            (0.0, -1.0),
            occultations.OccultationGeographicPole.NORTH,
            occultations.OccultationPathBoundarySide.RIGHT,
        ),
        (
            (0.0, 1.0),
            occultations.OccultationGeographicPole.SOUTH,
            occultations.OccultationPathBoundarySide.RIGHT,
        ),
        (
            (0.0, -1.0),
            occultations.OccultationGeographicPole.SOUTH,
            occultations.OccultationPathBoundarySide.LEFT,
        ),
        (
            (1.0, 0.0),
            occultations.OccultationGeographicPole.NORTH,
            None,
        ),
    ),
)
def test_pole_side_is_intrinsic_to_increasing_ut1_track_orientation(
    track_direction: tuple[float, float],
    pole: occultations.OccultationGeographicPole,
    expected: occultations.OccultationPathBoundarySide | None,
) -> None:
    assert occultations._classify_occultation_pole_side(track_direction, pole) is expected
