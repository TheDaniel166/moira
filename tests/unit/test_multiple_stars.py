from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

import moira
import moira.multiple_stars as ms


J2000 = 2451545.0
J2010 = 2455197.5
J2020 = 2458849.5
J2035 = 2464328.5


def _combined_mag_formula(system: ms.MultipleStarSystem) -> float:
    flux = sum(
        10.0 ** (-component.magnitude / 2.5)
        for component in system.components
        if math.isfinite(component.magnitude)
    )
    return -2.5 * math.log10(flux)


def test_multiple_star_lookup_resolves_alias_and_designation() -> None:
    sirius_by_name = ms.multiple_star("Sirius")
    sirius_by_designation = ms.multiple_star("alp CMa")
    sirius_by_alias = ms.multiple_star("dog star")

    assert sirius_by_name is sirius_by_designation is sirius_by_alias


def test_multiple_star_lookup_raises_for_unknown_name() -> None:
    with pytest.raises(KeyError, match="Unknown multiple star system"):
        ms.multiple_star("Not A Real Star System")


def test_list_multiple_stars_is_sorted_and_complete() -> None:
    names = ms.list_multiple_stars()
    assert names == sorted(names)
    assert names == [
        "Acrux",
        "Albireo",
        "Alpha Centauri",
        "Capella",
        "Castor",
        "Mizar",
        "Sirius",
        "Spica",
    ]


def test_multiple_stars_by_type_filters_and_deduplicates() -> None:
    assert [s.name for s in ms.multiple_stars_by_type(ms.MultiType.VISUAL)] == [
        "Sirius",
        "Alpha Centauri",
    ]
    assert [s.name for s in ms.multiple_stars_by_type(ms.MultiType.WIDE)] == [
        "Castor",
        "Mizar",
        "Acrux",
    ]
    assert [s.name for s in ms.multiple_stars_by_type(ms.MultiType.SPECTROSCOPIC)] == [
        "Capella",
        "Spica",
    ]
    assert [s.name for s in ms.multiple_stars_by_type(ms.MultiType.OPTICAL)] == [
        "Albireo",
    ]


def test_visual_separations_are_positive_and_time_varying() -> None:
    sirius = ms.multiple_star("Sirius")
    alpha_cen = ms.multiple_star("Alpha Centauri")

    s_2000 = ms.angular_separation_at(sirius, J2000)
    s_2020 = ms.angular_separation_at(sirius, J2020)
    a_2000 = ms.angular_separation_at(alpha_cen, J2000)
    a_2035 = ms.angular_separation_at(alpha_cen, J2035)

    assert s_2000 > 0.0
    assert s_2020 > 0.0
    assert a_2000 > 0.0
    assert a_2035 > 0.0
    assert s_2000 != pytest.approx(s_2020)
    assert a_2000 != pytest.approx(a_2035)


def test_wide_and_optical_systems_return_fixed_reference_values() -> None:
    castor = ms.multiple_star("Castor")
    albireo = ms.multiple_star("Albireo")

    assert ms.angular_separation_at(castor, J2000) == pytest.approx(ms.angular_separation_at(castor, J2035))
    assert ms.position_angle_at(castor, J2000) == pytest.approx(ms.position_angle_at(castor, J2035))
    assert ms.angular_separation_at(albireo, J2000) == pytest.approx(ms.angular_separation_at(albireo, J2035))
    assert ms.position_angle_at(albireo, J2000) == pytest.approx(ms.position_angle_at(albireo, J2035))


def test_spectroscopic_systems_have_zero_separation_and_no_resolvability() -> None:
    for name in ("Capella", "Spica"):
        system = ms.multiple_star(name)
        assert ms.angular_separation_at(system, J2000) == pytest.approx(0.0)
        assert ms.position_angle_at(system, J2000) == pytest.approx(0.0)
        assert ms.is_resolvable(system, J2000, aperture_mm=60.0) is False
        assert ms.is_resolvable(system, J2000, aperture_mm=400.0) is False


def test_is_resolvable_uses_dawes_limit_inclusive_boundary() -> None:
    castor = ms.multiple_star("Castor")
    rho = ms.angular_separation_at(castor, J2020)
    aperture_exact = 116.0 / rho

    assert ms.is_resolvable(castor, J2020, aperture_mm=aperture_exact) is True
    assert ms.is_resolvable(castor, J2020, aperture_mm=max(aperture_exact - 0.01, 1e-6)) is False


def test_dominant_component_returns_brightest_component() -> None:
    sirius = ms.multiple_star("Sirius")
    dominant = ms.dominant_component(sirius)
    assert dominant.label == "A"
    assert dominant.magnitude == min(component.magnitude for component in sirius.components)


def test_combined_magnitude_matches_flux_sum_formula() -> None:
    for name in ms.list_multiple_stars():
        system = ms.multiple_star(name)
        assert ms.combined_magnitude(system) == pytest.approx(_combined_mag_formula(system), abs=1e-9)


def test_components_at_returns_structured_snapshot() -> None:
    sirius = ms.multiple_star("Sirius")
    snapshot = ms.components_at(sirius, J2020)

    assert snapshot["separation_arcsec"] == pytest.approx(ms.angular_separation_at(sirius, J2020))
    assert snapshot["position_angle_deg"] == pytest.approx(ms.position_angle_at(sirius, J2020))
    assert snapshot["dominant_component"] == "A"
    assert snapshot["is_resolvable_100mm"] == ms.is_resolvable(sirius, J2020, 100.0)
    assert snapshot["is_resolvable_200mm"] == ms.is_resolvable(sirius, J2020, 200.0)
    assert set(snapshot["components"]) == {"A", "B"}
    assert snapshot["components"]["A"]["spectral_type"] == sirius.components[0].spectral_type


def test_named_convenience_functions_match_generic_api() -> None:
    sirius = ms.multiple_star("Sirius")
    castor = ms.multiple_star("Castor")
    alpha_cen = ms.multiple_star("Alpha Centauri")

    assert ms.sirius_ab_separation_at(J2020) == pytest.approx(ms.angular_separation_at(sirius, J2020))
    assert ms.sirius_b_resolvable(J2020, aperture_mm=120.0) == ms.is_resolvable(sirius, J2020, 120.0)
    assert ms.castor_separation_at(J2020) == pytest.approx(ms.angular_separation_at(castor, J2020))
    assert ms.alpha_cen_separation_at(J2020) == pytest.approx(ms.angular_separation_at(alpha_cen, J2020))


def test_public_surface_is_exposed_from_module_and_top_level_package() -> None:
    expected = {
        "MultiType",
        "StarComponent",
        "OrbitalElements",
        "MultipleStarSystem",
        "angular_separation_at",
        "position_angle_at",
        "is_resolvable",
        "dominant_component",
        "combined_magnitude",
        "components_at",
        "multiple_star",
        "list_multiple_stars",
        "multiple_stars_by_type",
        "sirius_ab_separation_at",
        "sirius_b_resolvable",
        "castor_separation_at",
        "alpha_cen_separation_at",
    }
    assert set(ms.__all__) == expected
    assert "_CATALOG" not in ms.__all__
    assert "_solve_kepler" not in ms.__all__


def test_moira_wrapper_methods_match_subsystem_outputs() -> None:
    engine = moira.Moira()
    dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    jd = moira.jd_from_datetime(dt)
    sirius = ms.multiple_star("Sirius")

    separation_info = engine.multiple_star_separation("Sirius", dt, aperture_mm=150.0)
    assert separation_info["separation_arcsec"] == pytest.approx(ms.angular_separation_at(sirius, jd))
    assert separation_info["position_angle_deg"] == pytest.approx(ms.position_angle_at(sirius, jd))
    assert separation_info["is_resolvable"] == ms.is_resolvable(sirius, jd, 150.0)
    assert separation_info["dominant_component"] == "A"
    assert separation_info["combined_magnitude"] == pytest.approx(ms.combined_magnitude(sirius))
    assert separation_info["system_type"] == sirius.system_type

    component_info = engine.multiple_star_components("Sirius", dt)
    assert component_info == ms.components_at(sirius, jd)
