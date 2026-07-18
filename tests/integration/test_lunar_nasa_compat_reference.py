from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.compat.nasa.eclipse import next_nasa_lunar_eclipse
from moira.eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    LunarCanonValidationCase,
    compare_lunar_canon_methods,
    lunar_canon_geometry,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _modern_rows() -> tuple[dict, ...]:
    return tuple(_load_fixture()["lunar_modern_validation"])


def _modern_cases() -> tuple[LunarCanonValidationCase, ...]:
    return tuple(
        LunarCanonValidationCase(
            label=str(row["label"]),
            nasa_ut=float(row["ut_jd"]),
            nasa_gamma_earth_radii=float(row["gamma"]),
            eclipse_type=str(row["type"]),
        )
        for row in _modern_rows()
    )


def test_lunar_nasa_fixture_preserves_catalog_provenance_and_signed_gamma() -> None:
    fixture = _load_fixture()
    source = fixture["source"]
    rows = _modern_rows()

    assert source["lunar_catalog_url"].startswith("https://eclipse.gsfc.nasa.gov/")
    assert source["lunar_catalog_key_url"].startswith("https://eclipse.gsfc.nasa.gov/")
    assert "north positive, south negative" in source["lunar_modern_validation_note"]
    assert any(float(row["gamma"]) < 0.0 for row in rows)
    assert any(float(row["gamma"]) > 0.0 for row in rows)

    for row in rows:
        assert row["source_url"].startswith("https://eclipse.gsfc.nasa.gov/LEsaros/")
        derived_ut = float(row["td_jd"]) - float(row["delta_t_s"]) / 86400.0
        assert float(row["ut_jd"]) == pytest.approx(derived_ut, abs=1e-12)

    may_2023 = next(row for row in rows if row["label"] == "2023-05-05 penumbral")
    assert float(may_2023["gamma"]) == -1.0349


@pytest.mark.slow
def test_lunar_canon_method_comparison_prefers_apparent_sun_moon_on_modern_sample(
    eclipse_calculator,
) -> None:
    """Rank compatibility policies on reconstructed catalog UT/TT.

    This is compatibility-regression evidence. The separate signed-gamma test
    below performs the external comparison at each fixture's published TD.
    """
    calc = eclipse_calculator
    comparisons = {
        comparison.method: comparison
        for comparison in compare_lunar_canon_methods(calc, _modern_cases())
    }

    apparent = comparisons["nasa_shadow_axis_apparent_sun_moon"]
    legacy_methods = (
        comparisons["nasa_shadow_axis_geometric_moon"],
        comparisons["nasa_shadow_axis_retarded_moon"],
    )

    assert len(_modern_cases()) == 10
    assert apparent.method == DEFAULT_LUNAR_CANON_METHOD
    assert apparent.max_timing_residual_seconds <= 10.0
    assert apparent.max_gamma_residual_earth_radii <= 2.0e-4
    for legacy in legacy_methods:
        assert (
            apparent.mean_timing_residual_seconds
            < legacy.mean_timing_residual_seconds
        )
        assert (
            apparent.max_timing_residual_seconds
            < legacy.max_timing_residual_seconds
        )
        assert (
            apparent.max_gamma_residual_earth_radii
            < legacy.max_gamma_residual_earth_radii
        )


@pytest.mark.slow
def test_lunar_canon_geometry_tracks_published_signed_gamma_at_nasa_instants(eclipse_calculator) -> None:
    calc = eclipse_calculator

    for row in _modern_rows():
        geom = lunar_canon_geometry(
            calc,
            float(row["td_jd"]),
            method=DEFAULT_LUNAR_CANON_METHOD,
        )
        assert abs(geom.gamma_earth_radii - float(row["gamma"])) <= 2.0e-4, str(
            row["label"]
        )


@pytest.mark.slow
def test_nasa_compat_public_wrapper_stays_within_documented_modern_residual_envelope(eclipse_calculator) -> None:
    calc = eclipse_calculator

    for case in (case for case in _modern_cases() if case.eclipse_type == "T"):
        compat = next_nasa_lunar_eclipse(case.nasa_ut - 5.0, kind="total", calculator=calc)
        err_seconds = abs(compat.jd_ut - case.nasa_ut) * 86400.0
        gamma_err = abs(compat.gamma_earth_radii - case.nasa_gamma_earth_radii)

        assert compat.canon_method == DEFAULT_LUNAR_CANON_METHOD
        assert compat.canon_method == "nasa_shadow_axis_apparent_sun_moon"
        assert "annual-aberration" in compat.source_model
        assert compat.moira_event.data.is_lunar_eclipse
        assert compat.moira_event.data.eclipse_type.is_total
        assert err_seconds <= 10.0, case.label
        assert gamma_err <= 2.0e-4, case.label


@pytest.mark.slow
def test_native_path_remains_distinct_from_nasa_compat_for_problem_case(eclipse_calculator) -> None:
    calc = eclipse_calculator
    seed = 2452952.0  # 2003-11-09 total lunar eclipse

    native = calc.analyze_lunar_eclipse(seed, kind="total", mode="native")
    compat = calc.analyze_lunar_eclipse(seed, kind="total", mode="nasa_compat")

    assert native.event.data.eclipse_type.is_total
    assert compat.event.data.eclipse_type.is_total
    assert abs(native.event.jd_ut - compat.event.jd_ut) * 86400.0 >= 30.0
