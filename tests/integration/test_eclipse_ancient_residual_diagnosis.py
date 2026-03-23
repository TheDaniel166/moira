from __future__ import annotations

import json
from pathlib import Path

from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import refine_lunar_greatest_eclipse_canon_tt
from moira.eclipse_search import refine_minimum
from moira.julian import tt_to_ut_nasa_canon


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"
_JD_SECONDS = 86400.0


def _load_ancient_total_case() -> dict[str, float | str]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return next(case for case in fixture["search_cases"]["lunar"] if case["label"] == "ancient_total")


def _error_seconds(jd_ut: float, expected_ut_jd: float) -> float:
    return (jd_ut - expected_ut_jd) * _JD_SECONDS


def test_ancient_lunar_total_residual_breakdown_is_explicit() -> None:
    """
    Diagnose the documented ancient lunar total residual into its main causes.

    This test keeps the remaining open astronomy limitation transparent instead
    of treating it as a single unexplained number.
    """
    row = _load_ancient_total_case()
    seed = float(row["seed_jd"]) + 40.0
    expected = float(row["expected_ut_jd"])
    calc = EclipseCalculator()

    native_retarded = refine_minimum(
        lambda jd: calc._lunar_shadow_axis_distance_km(
            jd,
            retarded_moon=True,
            delta_t_mode="native",
        ),
        seed,
        window_days=0.125,
        tol_days=1e-7,
        max_iter=100,
    )
    native_geometric = refine_minimum(
        lambda jd: calc._lunar_shadow_axis_distance_km(
            jd,
            retarded_moon=False,
            delta_t_mode="native",
        ),
        seed,
        window_days=0.125,
        tol_days=1e-7,
        max_iter=100,
    )
    nasa_retarded = refine_minimum(
        lambda jd: calc._lunar_shadow_axis_distance_km(
            jd,
            retarded_moon=True,
            delta_t_mode="nasa_canon",
        ),
        seed,
        window_days=0.125,
        tol_days=1e-7,
        max_iter=100,
    )
    nasa_geometric = refine_minimum(
        lambda jd: calc._lunar_shadow_axis_distance_km(
            jd,
            retarded_moon=False,
            delta_t_mode="nasa_canon",
        ),
        seed,
        window_days=0.125,
        tol_days=1e-7,
        max_iter=100,
    )

    canon_geometric_tt = refine_lunar_greatest_eclipse_canon_tt(
        calc,
        seed,
        method="nasa_shadow_axis_geometric_moon",
        window_days=0.125,
        tol_days=1e-7,
    )
    canon_retarded_tt = refine_lunar_greatest_eclipse_canon_tt(
        calc,
        seed,
        method="nasa_shadow_axis_retarded_moon",
        window_days=0.125,
        tol_days=1e-7,
    )
    canon_geometric = tt_to_ut_nasa_canon(canon_geometric_tt)
    canon_retarded = tt_to_ut_nasa_canon(canon_retarded_tt)

    native_retarded_err = abs(_error_seconds(native_retarded, expected))
    native_geometric_err = abs(_error_seconds(native_geometric, expected))
    nasa_retarded_err = abs(_error_seconds(nasa_retarded, expected))
    nasa_geometric_err = abs(_error_seconds(nasa_geometric, expected))

    native_moon_model_shift = abs(_error_seconds(native_retarded, native_geometric))
    delta_t_branch_shift = abs(_error_seconds(native_retarded, nasa_retarded))
    canon_alignment_geometric = abs(_error_seconds(nasa_geometric, canon_geometric))
    canon_alignment_retarded = abs(_error_seconds(nasa_retarded, canon_retarded))

    assert native_retarded_err <= 60.0
    assert native_retarded_err < native_geometric_err
    assert native_retarded_err < nasa_geometric_err
    assert native_retarded_err < nasa_retarded_err

    # The retarded/geometric Moon choice is a real contributor, but smaller
    # than the time-scale branch change for this ancient case.
    assert native_moon_model_shift >= 20.0
    assert delta_t_branch_shift >= 300.0

    # When the Delta T branch and Moon treatment are aligned, the native
    # shadow-axis objective and the canon gamma objective collapse to the same
    # ancient timing to within a fraction of a second.
    assert canon_alignment_geometric <= 1.0
    assert canon_alignment_retarded <= 1.0
