from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.compat.nasa.eclipse import next_nasa_lunar_eclipse
from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    LunarCanonValidationCase,
    compare_lunar_canon_methods,
    lunar_canon_geometry,
)
from moira.julian import ut_to_tt_nasa_canon


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _modern_cases() -> tuple[LunarCanonValidationCase, ...]:
    fixture = _load_fixture()
    return tuple(
        LunarCanonValidationCase(
            label=str(row["label"]),
            nasa_ut=float(row["ut_jd"]),
            nasa_gamma_earth_radii=float(row["gamma"]),
            eclipse_type=str(row["type"]),
        )
        for row in fixture["lunar_modern_validation"]
    )


@pytest.mark.slow
def test_lunar_canon_method_comparison_prefers_geometric_moon_on_modern_sample() -> None:
    calc = EclipseCalculator()
    comparisons = {
        comparison.method: comparison
        for comparison in compare_lunar_canon_methods(calc, _modern_cases())
    }

    geometric = comparisons["nasa_shadow_axis_geometric_moon"]
    retarded = comparisons["nasa_shadow_axis_retarded_moon"]

    assert geometric.method == DEFAULT_LUNAR_CANON_METHOD
    assert geometric.max_timing_residual_seconds <= 60.0
    assert geometric.max_gamma_residual_earth_radii <= 0.013
    assert geometric.mean_timing_residual_seconds < retarded.mean_timing_residual_seconds
    assert geometric.max_timing_residual_seconds < retarded.max_timing_residual_seconds


@pytest.mark.slow
def test_lunar_canon_geometry_tracks_published_gamma_at_nasa_instants() -> None:
    calc = EclipseCalculator()

    for case in _modern_cases():
        geom = lunar_canon_geometry(
            calc,
            ut_to_tt_nasa_canon(case.nasa_ut),
            method=DEFAULT_LUNAR_CANON_METHOD,
        )
        assert abs(geom.gamma_earth_radii - case.nasa_gamma_earth_radii) <= 0.013, case.label


@pytest.mark.slow
def test_nasa_compat_public_wrapper_stays_within_documented_modern_residual_envelope() -> None:
    calc = EclipseCalculator()

    for case in _modern_cases():
        compat = next_nasa_lunar_eclipse(case.nasa_ut - 5.0, kind="total", calculator=calc)
        err_seconds = abs(compat.jd_ut - case.nasa_ut) * 86400.0
        gamma_err = abs(compat.gamma_earth_radii - case.nasa_gamma_earth_radii)

        assert compat.canon_method == DEFAULT_LUNAR_CANON_METHOD
        assert "geometric Moon" in compat.source_model
        assert compat.moira_event.data.is_lunar_eclipse
        assert compat.moira_event.data.eclipse_type.is_total
        assert err_seconds <= 60.0, case.label
        assert gamma_err <= 0.013, case.label


@pytest.mark.slow
def test_native_path_remains_distinct_from_nasa_compat_for_problem_case() -> None:
    calc = EclipseCalculator()
    seed = 2452952.0  # 2003-11-09 total lunar eclipse

    native = calc.analyze_lunar_eclipse(seed, kind="total", mode="native")
    compat = calc.analyze_lunar_eclipse(seed, kind="total", mode="nasa_compat")

    assert native.event.data.eclipse_type.is_total
    assert compat.event.data.eclipse_type.is_total
    assert abs(native.event.jd_ut - compat.event.jd_ut) * 86400.0 >= 30.0
