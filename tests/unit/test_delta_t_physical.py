"""Unit proofs for the source-bounded Delta-T physical surface.

These tests prove Moira's declared routing, arithmetic, and failure policy.
Agreement with :func:`moira.julian.delta_t` is regression/source-priority
consistency; it is not an independent external-oracle comparison.
"""

from __future__ import annotations

import math

import pytest

import moira.delta_t_physical as dtp
import moira.julian as julian_module
from moira.constants import JULIAN_YEAR
from moira.julian import delta_t as canonical_delta_t


PUBLIC_YEAR_FUNCTIONS = (
    dtp.secular_trend,
    dtp.fluid_lowfreq,
    dtp.historical_core_delta_t,
    dtp.core_delta_t,
    dtp.cryo_delta_t,
    dtp.delta_t_hybrid,
    dtp.delta_t_hybrid_uncertainty,
    dtp.delta_t_distribution,
    dtp.delta_t_breakdown,
)


def _clear_model_caches() -> None:
    for function in (
        dtp._reference_total,
        dtp._reference_slope,
        dtp._load_smh2016_points,
        dtp._load_smh2016_table,
        dtp._load_smh2016_uncertainty_table,
        dtp._load_grace_series,
        dtp._load_core_series,
        dtp._load_historical_core_series,
        dtp._get_core_dt_series,
        dtp._core_recent_stats,
    ):
        cache_clear = getattr(function, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()


@pytest.fixture(autouse=True)
def _isolated_model_caches() -> None:
    _clear_model_caches()
    yield
    _clear_model_caches()


def test_public_constants_preserve_the_established_surface() -> None:
    assert dtp.TIDAL_COEFF == 31.0
    assert dtp.GIA_COEFF == -3.0
    assert dtp.REFERENCE_LOD == pytest.approx(69.11474233219883, abs=1e-12)
    assert dtp.REFERENCE_YEAR == pytest.approx(
        julian_module._monthly_mean_representative_epoch(2026, 4), abs=1e-12
    )


def test_secular_trend_is_reference_anchored_curvature() -> None:
    assert dtp.secular_trend(dtp.REFERENCE_YEAR) == dtp.REFERENCE_LOD
    for offset in (1.0, 50.0, 100.0):
        before = dtp.secular_trend(dtp.REFERENCE_YEAR - offset)
        after = dtp.secular_trend(dtp.REFERENCE_YEAR + offset)
        assert before == pytest.approx(after, abs=1e-12)

    expected = dtp.REFERENCE_LOD + dtp.TIDAL_COEFF + dtp.GIA_COEFF
    assert dtp.secular_trend(dtp.REFERENCE_YEAR + 100.0) == pytest.approx(
        expected, abs=1e-12
    )


def test_future_secular_compatibility_helper_is_curvature_only() -> None:
    for year in (dtp.REFERENCE_YEAR, 2050.0, 2100.0):
        assert dtp._future_secular_baseline(year) == dtp.secular_trend(year)


@pytest.mark.parametrize(
    "component",
    (
        dtp.fluid_lowfreq,
        dtp.historical_core_delta_t,
        dtp.core_delta_t,
        dtp.cryo_delta_t,
    ),
)
@pytest.mark.parametrize("year", (-2000.0, 1840.0, 1962.5, 2026.0, 2100.0))
def test_candidate_component_attributions_are_quarantined(component, year: float) -> None:
    assert component(year) == 0.0


def test_candidate_loaders_cannot_change_the_admitted_total(monkeypatch) -> None:
    def forbidden_loader():
        raise AssertionError("quarantined research artifact entered the admitted model")

    monkeypatch.setattr(dtp, "_load_grace_series", forbidden_loader)
    monkeypatch.setattr(dtp, "_load_core_series", forbidden_loader)
    monkeypatch.setattr(dtp, "_load_historical_core_series", forbidden_loader)

    assert math.isfinite(dtp.delta_t_hybrid(2000.0))
    assert math.isfinite(dtp.delta_t_hybrid(2100.0))
    assert math.isfinite(dtp.delta_t_hybrid_uncertainty(2100.0))


def test_legacy_private_fit_coefficients_are_neutral() -> None:
    assert dtp._modern_bridge_coefficients() == (0.0, 0.0)
    assert dtp._fit_fluid_lowfreq_coefficients() == (0.0, 0.0)


@pytest.mark.parametrize(
    "year",
    (-2000.0, -720.0, 0.0, 1000.0, 1839.9, 1840.0, 1962.5, 2000.0, 2026.0),
)
def test_source_era_total_uses_canonical_priority(year: float) -> None:
    assert dtp.delta_t_hybrid(year) == canonical_delta_t(year)


@pytest.mark.parametrize("year", (-2000.0, 0.0, 1840.0, 1962.5, 2026.0))
def test_source_era_breakdown_is_baseline_plus_explicit_bridge(year: float) -> None:
    breakdown = dtp.delta_t_breakdown(year)
    assert breakdown.total == canonical_delta_t(year)
    assert breakdown.secular == dtp.secular_trend(year)
    assert breakdown.bridge == pytest.approx(
        breakdown.total - breakdown.secular, abs=1e-12
    )
    assert breakdown.core == 0.0
    assert breakdown.cryo == 0.0
    assert breakdown.fluid == 0.0
    assert breakdown.residual == 0.0


def _future_formula(year: float) -> float:
    boundary = julian_module._delta_t_observation_boundary()
    horizon = year - boundary.year
    reference_total = boundary.total
    reference_slope = boundary.slope
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    return reference_total + reference_slope * horizon + curvature * (horizon / 100.0) ** 2


@pytest.mark.parametrize("year", (2027.0, 2030.0, 2050.0, 2100.0, 2150.0))
def test_future_mean_is_boundary_conditioned_formula(year: float) -> None:
    assert dtp.delta_t_hybrid(year) == pytest.approx(_future_formula(year), abs=1e-12)


def test_physical_model_consumes_the_dynamic_annual_boundary(monkeypatch) -> None:
    monkeypatch.setattr(
        julian_module,
        "_DELTA_T_ANNUAL",
        julian_module._DELTA_T_ANNUAL
        + ((julian_module._monthly_mean_representative_epoch(2027, 12), 70.0),),
    )
    boundary = julian_module._delta_t_observation_boundary()
    expected_year = julian_module._monthly_mean_representative_epoch(2027, 12)
    assert dtp._reference_year() == expected_year
    assert dtp._reference_total() == 70.0
    previous_year, previous_total = julian_module._DELTA_T_ANNUAL[-2]
    assert dtp._reference_slope() == pytest.approx(
        (70.0 - previous_total) / (expected_year - previous_year), abs=1e-12
    )
    assert dtp.delta_t_hybrid(expected_year + 0.0001) == pytest.approx(
        _future_formula(expected_year + 0.0001), abs=1e-12
    )


def test_current_2100_scenario_is_not_the_rejected_historical_slope_path() -> None:
    assert dtp.delta_t_hybrid(2100.0) == pytest.approx(83.29435995149662, abs=1e-10)
    assert dtp.delta_t_hybrid(2100.0) < 100.0


@pytest.mark.parametrize("seam", (1840.0, 1962.5))
def test_source_era_total_and_components_are_continuous_at_internal_seams(seam: float) -> None:
    epsilon = 1e-6
    left = dtp.delta_t_breakdown(seam - epsilon)
    right = dtp.delta_t_breakdown(seam + epsilon)
    for field in ("total", "secular", "core", "cryo", "fluid", "bridge", "residual"):
        assert abs(getattr(right, field) - getattr(left, field)) < 1e-3


def test_reference_handoff_is_componentwise_continuous() -> None:
    epsilon = 1e-7
    left = dtp.delta_t_breakdown(dtp.REFERENCE_YEAR - epsilon)
    at = dtp.delta_t_breakdown(dtp.REFERENCE_YEAR)
    right = dtp.delta_t_breakdown(dtp.REFERENCE_YEAR + epsilon)
    for field in ("total", "secular", "core", "cryo", "fluid", "bridge", "residual"):
        assert getattr(left, field) == pytest.approx(getattr(at, field), abs=1e-6)
        assert getattr(right, field) == pytest.approx(getattr(at, field), abs=1e-6)


def test_reference_handoff_is_c1() -> None:
    step = 1e-3
    at = dtp.delta_t_hybrid(dtp.REFERENCE_YEAR)
    left_slope = (at - dtp.delta_t_hybrid(dtp.REFERENCE_YEAR - step)) / step
    right_slope = (dtp.delta_t_hybrid(dtp.REFERENCE_YEAR + step) - at) / step
    expected = julian_module._delta_t_observation_boundary().slope
    assert left_slope == pytest.approx(expected, abs=1e-8)
    assert right_slope == pytest.approx(expected, abs=3e-6)
    assert right_slope == pytest.approx(left_slope, abs=3e-6)


def test_era_labels_are_stable() -> None:
    assert dtp.delta_t_breakdown(1000.0).era == "pre-1840"
    assert dtp.delta_t_breakdown(1840.0).era == "historical"
    assert dtp.delta_t_breakdown(1962.5).era == "measured"
    assert dtp.delta_t_breakdown(2026.0).era == "measured"
    assert dtp.delta_t_breakdown(dtp.REFERENCE_YEAR + 0.0001).era == "future"


def test_breakdown_vessel_fields_and_additive_identity_are_preserved() -> None:
    assert tuple(dtp.DeltaTBreakdown.__dataclass_fields__) == (
        "year",
        "total",
        "secular",
        "core",
        "cryo",
        "fluid",
        "bridge",
        "residual",
        "era",
    )
    for year in (-2000.0, 1850.0, 2000.0, 2026.0, 2100.0):
        result = dtp.delta_t_breakdown(year)
        reconstructed = math.fsum(
            (result.secular, result.core, result.cryo, result.fluid, result.bridge, result.residual)
        )
        assert reconstructed == pytest.approx(result.total, abs=1e-12)


def test_hpiers_source_errors_are_retained() -> None:
    assert dtp._smh2016_uncertainty(-2000.0) == 2520.0
    assert dtp._smh2016_uncertainty(0.0) == 90.0
    assert dtp._smh2016_uncertainty(2016.0) == 0.05
    assert dtp._smh2016_uncertainty(-1850.0) == pytest.approx(2340.0, abs=1e-12)


def test_hpiers_lookup_is_bounded_instead_of_clamped() -> None:
    with pytest.raises(ValueError, match="source-bounded"):
        dtp._smh2016_lookup(-2000.0001)
    with pytest.raises(ValueError, match="defined on"):
        dtp._smh2016_lookup(2016.0001)
    with pytest.raises(ValueError, match="defined on"):
        dtp._smh2016_uncertainty(2016.0001)


def test_hpiers_declared_conflict_keeps_later_mean_and_max_error(tmp_path, monkeypatch) -> None:
    table = tmp_path / "delta_t_hpiers_2016.txt"
    table.write_text(
        "-2000 46800 2520\n"
        "1850 9.3 0.1\n"
        "1850 9.32 0.2\n"
        "2016 68.04 0.05\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dtp, "_DATA_DIR", tmp_path)
    _clear_model_caches()

    points = dtp._load_smh2016_points()
    seam = next(point for point in points if point.year == 1850.0)
    assert seam.delta_t == 9.32
    assert seam.error == 0.2


@pytest.mark.parametrize(
    "contents, message",
    (
        ("-2000 46800\n2016 68 0.05\n", "expected year, Delta-T, and error"),
        ("-2000 46800 2520\n0 nan 90\n2016 68 0.05\n", "non-finite"),
        ("-2000 46800 2520\n0 10570 -1\n2016 68 0.05\n", "negative source error"),
        ("-2000 46800 2520\n10 100 1\n0 90 1\n2016 68 0.05\n", "not non-decreasing"),
        ("-2000 46800 2520\n0 10570 90\n0 10571 90\n2016 68 0.05\n", "conflicting duplicate"),
    ),
)
def test_hpiers_loader_fails_closed_on_malformed_data(
    tmp_path, monkeypatch, contents: str, message: str
) -> None:
    (tmp_path / "delta_t_hpiers_2016.txt").write_text(contents, encoding="utf-8")
    monkeypatch.setattr(dtp, "_DATA_DIR", tmp_path)
    _clear_model_caches()
    with pytest.raises(ValueError, match=message):
        dtp._load_smh2016_points()


def test_hpiers_loader_fails_closed_when_required_file_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(dtp, "_DATA_DIR", tmp_path)
    _clear_model_caches()
    with pytest.raises(FileNotFoundError, match="authority table is missing"):
        dtp._load_smh2016_points()


def test_uncertainty_uses_source_error_then_modern_floor() -> None:
    assert dtp.delta_t_hybrid_uncertainty(-2000.0) == 2520.0
    assert dtp.delta_t_hybrid_uncertainty(0.0) == 90.0
    assert dtp.delta_t_hybrid_uncertainty(2016.0) == 0.06
    assert dtp.delta_t_hybrid_uncertainty(2020.0) == 0.06
    assert dtp.delta_t_hybrid_uncertainty(2026.0) == 0.06


def test_future_uncertainty_is_an_arithmetic_uncalibrated_policy_scale() -> None:
    year = 2100.0
    horizon = year - dtp.REFERENCE_YEAR
    centuries_squared = (horizon / 100.0) ** 2
    expected = math.fsum(
        (
            dtp._MODERN_SOURCE_ERROR_FLOOR,
            dtp._TIDAL_COEFF_SIGMA * centuries_squared,
            dtp._GIA_COEFF_SIGMA * centuries_squared,
            dtp._future_stochastic_delta_t_sigma(year),
        )
    )
    assert dtp.delta_t_hybrid_uncertainty(year) == pytest.approx(expected, abs=1e-12)
    assert "uncalibrated" in (dtp.delta_t_hybrid_uncertainty.__doc__ or "")
    assert "boundary slope" in (dtp.delta_t_hybrid_uncertainty.__doc__ or "")


def test_uncertainty_is_continuous_and_grows_after_the_reference() -> None:
    epsilon = 1e-7
    at = dtp.delta_t_hybrid_uncertainty(dtp.REFERENCE_YEAR)
    right = dtp.delta_t_hybrid_uncertainty(dtp.REFERENCE_YEAR + epsilon)
    assert right == pytest.approx(at, abs=1e-6)
    values = [dtp.delta_t_hybrid_uncertainty(y) for y in (2026.0, 2030.0, 2050.0, 2100.0)]
    assert values == sorted(values)


def test_integrated_ou_scale_uses_stable_short_horizon_limit() -> None:
    for horizon in (1e-2, 1e-4, 1e-6):
        actual_horizon = (dtp.REFERENCE_YEAR + horizon) - dtp.REFERENCE_YEAR
        actual = dtp._future_stochastic_delta_t_sigma(dtp.REFERENCE_YEAR + horizon)
        brownian = (
            JULIAN_YEAR
            / 1000.0
            * dtp._LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR
            * math.sqrt(actual_horizon**3 / 3.0)
        )
        assert actual == pytest.approx(brownian, rel=5e-4)


def test_integrated_ou_scale_matches_exact_long_horizon_formula() -> None:
    horizon = 2100.0 - dtp.REFERENCE_YEAR
    theta = dtp._LOD_OU_REVERSION_RATE
    z = theta * horizon
    one_minus_exp = -math.expm1(-z)
    bracket = 2.0 * z - 2.0 * one_minus_exp - one_minus_exp**2
    expected = (
        JULIAN_YEAR
        / 1000.0
        * dtp._LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR
        * math.sqrt(bracket / (2.0 * theta**3))
    )
    assert dtp._future_stochastic_delta_t_sigma(2100.0) == pytest.approx(
        expected, rel=1e-12
    )


@pytest.mark.parametrize("bad_theta", (0.0, -0.1, math.nan, math.inf))
def test_integrated_ou_scale_rejects_invalid_reversion_rate(monkeypatch, bad_theta: float) -> None:
    monkeypatch.setattr(dtp, "_LOD_OU_REVERSION_RATE", bad_theta)
    with pytest.raises(ValueError, match="mean-reversion rate"):
        dtp._future_stochastic_delta_t_sigma(2030.0)


def test_residual_spline_is_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="residual spline is quarantined"):
        dtp._fitted_residual_spline()


@pytest.mark.parametrize("bad_year", (math.nan, math.inf, -math.inf))
@pytest.mark.parametrize("function", PUBLIC_YEAR_FUNCTIONS)
def test_public_year_surfaces_reject_non_finite_inputs(function, bad_year: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        function(bad_year)


@pytest.mark.parametrize("function", PUBLIC_YEAR_FUNCTIONS)
def test_public_year_surfaces_reject_pre_source_dates(function) -> None:
    with pytest.raises(ValueError, match="source-bounded"):
        function(-2000.0001)


@pytest.mark.parametrize("function", PUBLIC_YEAR_FUNCTIONS)
def test_public_year_surfaces_reject_finite_unrepresentable_future(function) -> None:
    with pytest.raises(ValueError, match="representable"):
        function(1.0e100)


def test_future_scenario_remains_computable_beyond_validation_boundary() -> None:
    # 2150 is a forecast-confidence boundary, not a hard mathematical domain
    # limit.  Values beyond it are continuous unvalidated extrapolations.
    for year in (2150.0, 2150.0001, 2200.0):
        assert dtp.delta_t_hybrid(year) == pytest.approx(_future_formula(year), abs=1e-12)
        assert math.isfinite(dtp.delta_t_hybrid_uncertainty(year))


def test_distribution_vessel_and_probability_helpers_are_preserved() -> None:
    assert tuple(dtp.DeltaTDistribution.__dataclass_fields__) == ("year", "mean", "sigma")
    distribution = dtp.delta_t_distribution(2100.0)
    assert distribution.mean == dtp.delta_t_hybrid(2100.0)
    assert distribution.sigma == dtp.delta_t_hybrid_uncertainty(2100.0)
    assert distribution.variance == distribution.sigma**2
    assert distribution.pdf(distribution.mean) > distribution.pdf(
        distribution.mean + 2.0 * distribution.sigma
    )
    low, high = distribution.interval(2.0)
    assert low < distribution.mean < high


@pytest.mark.parametrize(
    "kwargs",
    (
        {"year": math.nan, "mean": 0.0, "sigma": 1.0},
        {"year": 2000.0, "mean": math.inf, "sigma": 1.0},
        {"year": 2000.0, "mean": 0.0, "sigma": math.inf},
        {"year": 2000.0, "mean": 0.0, "sigma": -1.0},
    ),
)
def test_distribution_rejects_invalid_manual_construction(kwargs) -> None:
    with pytest.raises(ValueError):
        dtp.DeltaTDistribution(**kwargs)


def test_distribution_rejects_nan_pdf_and_non_finite_interval_scale() -> None:
    distribution = dtp.delta_t_distribution(2100.0)
    with pytest.raises(ValueError, match="PDF input"):
        distribution.pdf(math.nan)
    with pytest.raises(ValueError, match="Interval scale"):
        distribution.interval(math.inf)


def test_research_lod_integrator_uses_milliseconds_to_seconds() -> None:
    series = ((2000.0, 1.0), (2001.0, 3.0), (2002.0, 1.0))
    result = dtp._lod_series_to_delta_t(series)
    mean_lod = 5.0 / 3.0
    expected_first = (
        ((1.0 - mean_lod) + (3.0 - mean_lod))
        / 2.0
        * JULIAN_YEAR
        / 1000.0
    )
    assert result[1][1] == pytest.approx(expected_first, abs=1e-12)


@pytest.mark.parametrize(
    "series",
    (
        ((2000.0, 1.0), (2000.0, 2.0)),
        ((2001.0, 1.0), (2000.0, 2.0)),
        ((2000.0, math.nan),),
        ((math.inf, 1.0),),
    ),
)
def test_research_lod_integrator_rejects_malformed_series(series) -> None:
    with pytest.raises(ValueError):
        dtp._lod_series_to_delta_t(series)


def test_midyear_spacing_respects_calendar_length() -> None:
    assert dtp._series_epoch_delta_days(2000.5, 2001.5) == pytest.approx(365.5)
    assert dtp._series_epoch_delta_days(2000.0, 2001.0) == pytest.approx(JULIAN_YEAR)
    with pytest.raises(ValueError):
        dtp._series_epoch_delta_days(2001.0, 2000.0)


def test_quarantined_raw_artifacts_remain_strict_diagnostics() -> None:
    grace = dtp._load_grace_series()
    core = dtp._load_core_series()
    assert grace
    assert core
    assert all(a[0] < b[0] for a, b in zip(grace, grace[1:]))
    assert all(flag in (0, 1) for _, _, flag in grace)
    assert all(a[0] < b[0] for a, b in zip(core, core[1:]))


def test_breakdown_and_distribution_remain_available_from_public_facades() -> None:
    from moira.essentials import DeltaTBreakdown, delta_t_breakdown
    from moira.facade import DeltaTDistribution, delta_t_distribution

    assert isinstance(delta_t_breakdown(2000.0), DeltaTBreakdown)
    assert isinstance(delta_t_distribution(2100.0), DeltaTDistribution)
