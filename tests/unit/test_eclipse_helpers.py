from __future__ import annotations

import pytest

import moira.eclipse as eclipse
from moira.geoutils import wrap_longitude_deg
from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import find_lunar_contacts_canon, lunar_canon_geometry
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


def test_shadow_axis_offset_tracks_opposition_distance() -> None:
    assert shadow_axis_offset_deg(180.0) == 0.0
    assert shadow_axis_offset_deg(179.25) == 0.75
    assert shadow_axis_offset_deg(181.25) == 1.25


def test_lunar_magnitude_helpers_match_current_formulas() -> None:
    umbral = lunar_umbral_magnitude(0.75, 0.25, 0.40)
    penumbral = lunar_penumbral_magnitude(1.25, 0.25, 0.40)
    assert abs(umbral - 1.2) < 1e-12
    assert abs(penumbral - 2.2) < 1e-12


def test_angular_separation_handles_wraparound() -> None:
    sep = angular_separation(359.9, 0.0, 0.1, 0.0)
    assert sep < 0.21


def test_longitude_wrapping_preserves_positive_180_boundary() -> None:
    assert wrap_longitude_deg(180.0) == 180.0
    assert wrap_longitude_deg(540.0) == 180.0


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


def test_solar_greatest_location_honors_objective_eval_limit(monkeypatch: pytest.MonkeyPatch) -> None:
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

    latitude, longitude, separation = eclipse._solve_solar_greatest_location(object(), 2451401.96)

    assert latitude == -80.0
    assert longitude == -100.0
    assert separation == 1.0
    assert call_count == 5


def test_solar_central_interval_returns_zero_width_when_deadline_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_best_margin(calc, jd_ut):
        nonlocal call_count
        call_count += 1
        return 0.0, 0.0, 0.5

    monkeypatch.setattr(eclipse, "_best_solar_central_margin", fake_best_margin)
    monkeypatch.setattr(eclipse, "_SOLAR_CENTRAL_INTERVAL_TIMEOUT_S", 0.0)
    monkeypatch.setattr(eclipse.time, "perf_counter", lambda: 100.0)

    left, right = eclipse._solve_solar_central_interval(object(), 2451401.96)

    assert left == 2451401.96
    assert right == 2451401.96
    assert call_count == 0


def test_refine_minimum_finds_parabola_vertex() -> None:
    best = refine_minimum(lambda x: (x - 3.25) ** 2, 3.0, window_days=1.0, tol_days=1e-7)
    assert abs(best - 3.25) < 1e-5


def test_refine_greatest_eclipse_helpers_return_local_event_maxima() -> None:
    calc = EclipseCalculator()

    lunar_seed = 2451564.7  # 2000-01-21 total lunar eclipse
    lunar_best = refine_lunar_greatest_eclipse(calc, lunar_seed)
    lunar_data = calc.calculate_jd(lunar_best)
    assert lunar_data.is_lunar_eclipse
    assert lunar_data.eclipse_type.is_total

    solar_seed = 2451401.96  # 1999-08-11 total solar eclipse
    solar_best = refine_solar_greatest_eclipse(calc, solar_seed)
    solar_data = calc.calculate_jd(solar_best)
    assert solar_data.is_solar_eclipse
    assert solar_data.eclipse_type.is_total


def test_total_lunar_eclipse_reports_larger_penumbral_than_umbral_magnitude() -> None:
    calc = EclipseCalculator()
    data = calc.calculate_jd(2451564.705)  # 2000-01-21 total lunar eclipse near maximum
    assert data.is_lunar_eclipse
    assert data.eclipse_type.is_total
    assert data.eclipse_type.magnitude_penumbra > data.eclipse_type.magnitude_umbral


@pytest.mark.slow
def test_lunar_contact_solver_returns_ordered_contacts_for_total_eclipse() -> None:
    calc = EclipseCalculator()
    contacts = find_lunar_contacts(calc, 2451564.705)
    assert contacts.p1 is not None
    assert contacts.u1 is not None
    assert contacts.u2 is not None
    assert contacts.u3 is not None
    assert contacts.u4 is not None
    assert contacts.p4 is not None
    assert contacts.p1 < contacts.u1 < contacts.u2 < contacts.greatest
    assert contacts.greatest < contacts.u3 < contacts.u4 < contacts.p4


@pytest.mark.slow
def test_lunar_canon_geometry_and_search_path_are_available() -> None:
    calc = EclipseCalculator()
    geom = lunar_canon_geometry(calc, 2451564.705)
    assert geom.gamma_earth_radii >= 0.0
    assert geom.penumbra_radius_earth_radii > geom.umbra_radius_earth_radii > 0.0
    contacts = find_lunar_contacts_canon(calc, 2451564.705)
    assert contacts.p1_ut is not None
    event = calc.next_lunar_eclipse_canon(2451560.0, kind="total")
    assert event.data.is_lunar_eclipse
    assert event.data.eclipse_type.is_total


def test_unified_lunar_analysis_api_exposes_native_and_canon_modes() -> None:
    calc = EclipseCalculator()

    native = calc.analyze_lunar_eclipse(2451560.0, kind="total", mode="native")
    assert native.mode == "native"
    assert native.event.data.is_lunar_eclipse
    assert native.event.data.eclipse_type.is_total
    assert native.gamma_earth_radii is None
    assert abs(native.contacts.greatest - native.event.jd_ut) < 1e-6

    canon = calc.analyze_lunar_eclipse(2451560.0, kind="total", mode="nasa_compat")
    assert canon.mode == "nasa_compat"
    assert canon.event.data.is_lunar_eclipse
    assert canon.event.data.eclipse_type.is_total
    assert canon.gamma_earth_radii is not None
    assert abs(canon.contacts.greatest_ut - canon.event.jd_ut) < 1e-6
    assert canon.canon_method == "nasa_shadow_axis_geometric_moon"
    assert "geometric Moon" in canon.source_model


def test_unified_native_penumbral_analysis_keeps_contact_model_aligned() -> None:
    calc = EclipseCalculator()

    native = calc.analyze_lunar_eclipse(2744232.0, kind="penumbral", mode="native")
    assert native.mode == "native"
    assert not native.event.data.is_lunar_eclipse
    assert native.event.data.eclipse_type.magnitude_penumbra > 0.0
    assert abs(native.contacts.greatest - native.event.jd_ut) < 1e-6


def test_local_lunar_circumstances_api_returns_contact_bundle() -> None:
    calc = EclipseCalculator()

    local = calc.lunar_local_circumstances(
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


def test_solar_local_circumstances_api_returns_observer_bundle() -> None:
    calc = EclipseCalculator()

    local = calc.solar_local_circumstances(
        2451400.0,
        50.0,
        0.0,
        kind="total",
    )

    assert local.event.data.is_solar_eclipse
    assert local.event.data.eclipse_type.is_total
    assert -90.0 <= local.sun.altitude <= 90.0
    assert -90.0 <= local.moon.altitude <= 90.0
    assert 0.0 <= local.sun.azimuth <= 360.0
    assert 0.0 <= local.moon.azimuth <= 360.0
    assert local.topocentric_separation_deg >= 0.0
    assert local.sun.visible == (local.sun.altitude > 0.0)
    assert local.moon.visible == (local.moon.altitude > 0.0)
