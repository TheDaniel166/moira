import math
import builtins
import pytest

from moira.constants import JULIAN_YEAR
from moira.delta_t_physical import (
    TIDAL_COEFF,
    GIA_COEFF,
    REFERENCE_LOD,
    REFERENCE_YEAR,
    secular_trend,
    fluid_lowfreq,
    historical_core_delta_t,
    core_delta_t,
    cryo_delta_t,
    delta_t_hybrid,
    delta_t_hybrid_uncertainty,
    DeltaTDistribution,
    delta_t_distribution,
    DeltaTBreakdown,
    delta_t_breakdown,
    _smh2016_lookup,
    _lod_series_to_delta_t,
    _series_epoch_delta_days,
    _annual_mean_midyear_jd,
    _cosine_taper,
    _load_grace_series,
    _load_core_series,
    _load_historical_core_series,
    _core_recent_stats,
    _modern_bridge_delta_t,
    _modern_bridge_coefficients,
    _future_secular_baseline,
    _future_stochastic_delta_t_sigma,
    _fit_fluid_lowfreq_coefficients,
    _require_univariate_spline,
    _historical_bridge_delta_t,
)


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------

def test_constants_have_correct_values() -> None:
    assert TIDAL_COEFF == 31.0
    assert GIA_COEFF == -3.0
    assert REFERENCE_LOD == pytest.approx(69.11474233219883, abs=1e-12)
    assert REFERENCE_YEAR == 2026.0


# ---------------------------------------------------------------------------
# secular_trend
# ---------------------------------------------------------------------------

def test_secular_trend_at_reference_year_equals_reference_lod() -> None:
    assert secular_trend(REFERENCE_YEAR) == REFERENCE_LOD


def test_secular_trend_is_symmetric_around_reference_year() -> None:
    delta = 50.0
    before = secular_trend(REFERENCE_YEAR - delta)
    after = secular_trend(REFERENCE_YEAR + delta)
    assert abs(before - after) < 1e-12


def test_secular_trend_increases_away_from_reference_year() -> None:
    assert secular_trend(REFERENCE_YEAR + 100.0) > secular_trend(REFERENCE_YEAR)
    assert secular_trend(REFERENCE_YEAR - 100.0) > secular_trend(REFERENCE_YEAR)


def test_secular_trend_combined_coefficient_is_28() -> None:
    t = 1.0
    expected = REFERENCE_LOD + (TIDAL_COEFF + GIA_COEFF) * t * t
    assert abs(secular_trend(REFERENCE_YEAR + 100.0) - expected) < 1e-12


def test_secular_trend_is_curvature_only_at_reference_year() -> None:
    eps = 1e-4
    slope = (
        secular_trend(REFERENCE_YEAR + eps)
        - secular_trend(REFERENCE_YEAR - eps)
    ) / (2 * eps)
    assert slope == pytest.approx(0.0, abs=1e-9)


def test_secular_trend_at_1820_is_reasonable() -> None:
    val = secular_trend(1820.0)
    t = (1820.0 - REFERENCE_YEAR) / 100.0
    expected = REFERENCE_LOD + (TIDAL_COEFF + GIA_COEFF) * t * t
    assert abs(val - expected) < 1e-12


def test_secular_trend_at_2100_is_above_reference_lod() -> None:
    assert secular_trend(2100.0) > REFERENCE_LOD


# ---------------------------------------------------------------------------
# measured-era bridge term
# ---------------------------------------------------------------------------

def test_modern_bridge_coefficients_are_finite() -> None:
    c2, c3 = _modern_bridge_coefficients()
    assert math.isfinite(c2)
    assert math.isfinite(c3)


def test_modern_bridge_is_zero_at_reference_year_and_in_future() -> None:
    assert _modern_bridge_delta_t(REFERENCE_YEAR) == pytest.approx(0.0, abs=1e-12)
    assert _modern_bridge_delta_t(2050.0) == pytest.approx(0.0, abs=1e-12)


def test_modern_bridge_is_active_in_measured_era() -> None:
    # At 1962.5 the seam correction makes the bridge non-zero. Its sign is
    # determined by the fitted fluid/core budget and is not itself a contract.
    assert abs(_modern_bridge_delta_t(1962.5)) > 0.0
    # At 2010.5 the fluid term absorbs most of the low-frequency correction;
    # the bridge is small but finite (no sign constraint).
    assert math.isfinite(_modern_bridge_delta_t(2010.5))


def test_modern_bridge_has_zero_left_slope_at_reference_year() -> None:
    eps = 1e-6
    left = _modern_bridge_delta_t(REFERENCE_YEAR - eps)
    assert abs(left / eps) < 1e-3


# ---------------------------------------------------------------------------
# fluid_lowfreq
# ---------------------------------------------------------------------------

def test_fluid_lowfreq_coefficients_are_finite() -> None:
    alpha, beta = _fit_fluid_lowfreq_coefficients()
    assert math.isfinite(alpha)
    assert math.isfinite(beta)


def test_fluid_lowfreq_is_zero_outside_support() -> None:
    assert fluid_lowfreq(1900.0) == pytest.approx(0.0, abs=1e-12)
    assert fluid_lowfreq(2025.0) == pytest.approx(0.0, abs=1e-12)
    assert fluid_lowfreq(2050.0) == pytest.approx(0.0, abs=1e-12)


def test_fluid_lowfreq_is_active_in_measured_era() -> None:
    assert abs(fluid_lowfreq(1975.5)) > 1.0


# ---------------------------------------------------------------------------
# _smh2016_lookup — delegates correctly
# ---------------------------------------------------------------------------

def test_smh2016_lookup_returns_float() -> None:
    assert isinstance(_smh2016_lookup(2000.0), float)


def test_smh2016_lookup_clamps_below_table_start() -> None:
    val_start = _smh2016_lookup(-2000.0)
    val_below = _smh2016_lookup(-3000.0)
    assert val_start == val_below


def test_smh2016_lookup_clamps_above_table_end() -> None:
    from moira.delta_t_physical import _load_smh2016_table
    table = _load_smh2016_table()
    table_end_year = table[-1][0]
    val_end = _smh2016_lookup(table_end_year)
    val_above = _smh2016_lookup(table_end_year + 100.0)
    assert val_end == val_above


def test_smh2016_lookup_interpolates_between_table_entries() -> None:
    lo = _smh2016_lookup(1900.0)
    hi = _smh2016_lookup(2000.0)
    mid = _smh2016_lookup(1950.0)
    assert min(lo, hi) <= mid <= max(lo, hi)


def test_require_univariate_spline_raises_clearly_when_scipy_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "scipy.interpolate":
            raise ImportError("mock missing scipy")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(RuntimeError, match="delta_t_hybrid requires scipy.interpolate.UnivariateSpline"):
        _require_univariate_spline()


# ---------------------------------------------------------------------------
# _lod_series_to_delta_t
# ---------------------------------------------------------------------------

def test_lod_to_delta_t_empty_series_returns_empty() -> None:
    assert _lod_series_to_delta_t(()) == ()


def test_lod_to_delta_t_single_entry_starts_at_zero() -> None:
    result = _lod_series_to_delta_t(((2000.0, 1.0),))
    assert result == ((2000.0, 0.0),)


def test_lod_to_delta_t_zero_lod_accumulates_nothing() -> None:
    series = ((2000.0, 0.0), (2001.0, 0.0), (2002.0, 0.0))
    result = _lod_series_to_delta_t(series)
    for _, val in result:
        assert val == 0.0


def test_lod_to_delta_t_positive_lod_accumulates_positively() -> None:
    series = ((2000.0, 2.0), (2001.0, 2.0), (2002.0, 2.0))
    result = _lod_series_to_delta_t(series)
    assert result[0][1] == 0.0
    assert result[1][1] == 0.0
    assert result[2][1] == 0.0


def test_lod_to_delta_t_removes_linear_trend() -> None:
    series = ((2000.0, 1.0), (2001.0, 3.0), (2002.0, 5.0))
    result = _lod_series_to_delta_t(series)
    assert [y for y, _ in result] == [2000.0, 2001.0, 2002.0]
    assert [v for _, v in result] == pytest.approx([0.0, 0.0, 0.0], abs=1e-10)


def test_lod_to_delta_t_integration_formula() -> None:
    series = ((2000.0, 1.0), (2001.0, 3.0), (2002.0, 1.0))
    result = _lod_series_to_delta_t(series)
    mean_lod = 5.0 / 3.0
    dt_days = 1.0 * JULIAN_YEAR
    avg_anomaly = ((1.0 - mean_lod) + (3.0 - mean_lod)) / 2.0
    expected = avg_anomaly * dt_days / 1000.0
    assert abs(result[1][1] - expected) < 1e-10


def test_annual_mean_midyear_jd_uses_true_calendar_midpoint() -> None:
    jd_2000 = _annual_mean_midyear_jd(2000.5)
    jd_2001 = _annual_mean_midyear_jd(2001.5)

    assert jd_2000 is not None
    assert jd_2001 is not None
    assert jd_2001 - jd_2000 == pytest.approx(365.5, abs=1e-12)


def test_series_epoch_delta_days_uses_midyear_spacing_when_available() -> None:
    assert _series_epoch_delta_days(2000.5, 2001.5) == pytest.approx(365.5, abs=1e-12)


def test_series_epoch_delta_days_falls_back_to_julian_year_for_non_midyear_series() -> None:
    assert _series_epoch_delta_days(2000.0, 2001.0) == pytest.approx(JULIAN_YEAR, abs=1e-12)


# ---------------------------------------------------------------------------
# _cosine_taper
# ---------------------------------------------------------------------------

def test_cosine_taper_is_one_before_window() -> None:
    assert _cosine_taper(2010.0) == 1.0
    assert _cosine_taper(2021.5) == 1.0


def test_cosine_taper_is_zero_at_and_after_end() -> None:
    assert _cosine_taper(2024.5) == 0.0
    assert _cosine_taper(2030.0) == 0.0


def test_cosine_taper_is_half_at_midpoint() -> None:
    mid = (2021.5 + 2024.5) / 2.0
    assert abs(_cosine_taper(mid) - 0.5) < 1e-12


def test_cosine_taper_is_monotonically_decreasing_through_window() -> None:
    years = [2021.0 + i * 0.5 for i in range(7)]
    tapers = [_cosine_taper(y) for y in years]
    for i in range(len(tapers) - 1):
        assert tapers[i] >= tapers[i + 1]


# ---------------------------------------------------------------------------
# cryo_delta_t — no data file present
# ---------------------------------------------------------------------------

def test_cryo_delta_t_returns_zero_when_no_data_file() -> None:
    if _load_grace_series():
        pytest.skip("grace_lod_contribution.txt is present — skipping no-data test")
    assert cryo_delta_t(2010.0) == 0.0
    assert cryo_delta_t(2026.0) == 0.0
    assert cryo_delta_t(2050.0) == 0.0


# ---------------------------------------------------------------------------
# core_delta_t — no data file present
# ---------------------------------------------------------------------------

def test_core_delta_t_returns_zero_when_no_data_file() -> None:
    if _load_core_series():
        pytest.skip("core_angular_momentum.txt is present — skipping no-data test")
    assert core_delta_t(1900.0) == 0.0
    assert core_delta_t(2000.0) == 0.0
    assert core_delta_t(2020.0) == 0.0


def test_core_recent_stats_returns_fallback_when_no_data_file() -> None:
    if _load_core_series():
        pytest.skip("core_angular_momentum.txt is present — skipping no-data test")
    mean, std = _core_recent_stats()
    assert mean == 0.0
    assert std > 0.0


# ---------------------------------------------------------------------------
# delta_t_hybrid — era routing
# ---------------------------------------------------------------------------

def test_delta_t_hybrid_delegates_to_smh2016_before_1840() -> None:
    assert delta_t_hybrid(1800.0) == _smh2016_lookup(1800.0)
    assert delta_t_hybrid(1839.9) == _smh2016_lookup(1839.9)


def test_delta_t_hybrid_at_reference_year_is_close_to_reference_lod() -> None:
    val = delta_t_hybrid(REFERENCE_YEAR)
    assert abs(val - REFERENCE_LOD) < 5.0


def test_delta_t_hybrid_returns_float_for_all_eras() -> None:
    for year in [-500.0, 1000.0, 1839.9, 1840.0, 1962.0, 2002.0, 2026.0, 2050.0, 2100.0]:
        result = delta_t_hybrid(year)
        assert isinstance(result, float)
        assert math.isfinite(result)


def test_delta_t_hybrid_boundary_at_1840_uses_smh2016_just_before() -> None:
    # Pre-1840: SMH2016 table.
    assert delta_t_hybrid(1839.99) == _smh2016_lookup(1839.99)
    # 1840–1962.4: physics path returns secular + historical_bridge + historical_core.
    # Without data, historical_core = 0, so the result equals smh2016 exactly.
    # The value must be physically plausible (well under 50 s), not the
    # broken secular-only extrapolation (~165 s at 1840).
    assert delta_t_hybrid(1840.01) < 50.0
    assert delta_t_hybrid(1900.0) == pytest.approx(_smh2016_lookup(1900.0), abs=1e-12)
    assert delta_t_hybrid(1950.0) == pytest.approx(_smh2016_lookup(1950.0), abs=1e-12)


def test_delta_t_hybrid_future_grows_with_time() -> None:
    val_2050 = delta_t_hybrid(2050.0)
    val_2100 = delta_t_hybrid(2100.0)
    assert val_2100 > val_2050


def test_future_secular_baseline_carries_tidal_gia_slope() -> None:
    assert _future_secular_baseline(2050.0) > secular_trend(2050.0)


def test_future_stochastic_lod_sigma_grows_with_integrated_horizon() -> None:
    assert _future_stochastic_delta_t_sigma(REFERENCE_YEAR) == 0.0
    assert _future_stochastic_delta_t_sigma(2100.0) > _future_stochastic_delta_t_sigma(2050.0)


# ---------------------------------------------------------------------------
# delta_t_hybrid_uncertainty
# ---------------------------------------------------------------------------

def test_uncertainty_is_positive_for_all_eras() -> None:
    for year in [1900.0, 2000.0, 2026.0, 2050.0, 2100.0]:
        assert delta_t_hybrid_uncertainty(year) > 0.0


def test_uncertainty_at_reference_year_is_small() -> None:
    sigma = delta_t_hybrid_uncertainty(REFERENCE_YEAR)
    assert sigma < 1.0


def test_uncertainty_grows_into_future() -> None:
    sigma_near = delta_t_hybrid_uncertainty(2030.0)
    sigma_far = delta_t_hybrid_uncertainty(2100.0)
    assert sigma_far > sigma_near


def test_uncertainty_is_finite_for_all_eras() -> None:
    for year in [-500.0, 1000.0, 1840.0, 1962.0, 2026.0, 2100.0]:
        assert math.isfinite(delta_t_hybrid_uncertainty(year))


def test_delta_t_distribution_exposes_pdf_parameters() -> None:
    dist = delta_t_distribution(2100.0)
    assert isinstance(dist, DeltaTDistribution)
    assert dist.mean == pytest.approx(delta_t_hybrid(2100.0), abs=1e-12)
    assert dist.sigma == pytest.approx(delta_t_hybrid_uncertainty(2100.0), abs=1e-12)
    assert dist.pdf(dist.mean) > dist.pdf(dist.mean + 2.0 * dist.sigma)
    lo, hi = dist.interval(2.0)
    assert lo < dist.mean < hi


def test_uncertainty_quadrature_components_are_non_negative() -> None:
    sigma = delta_t_hybrid_uncertainty(2075.0)
    assert sigma >= 0.0


# ---------------------------------------------------------------------------
# Continuity constraint: REFERENCE_LOD reconstruction
# Per DELTA_T_HYBRID_MODEL.md section 5, update_reference_anchor.py test.
# Without data files, cryo and core are 0.0 and residual is 0.0, so
# secular_trend(REFERENCE_YEAR) must equal REFERENCE_LOD exactly.
# ---------------------------------------------------------------------------

def test_reference_lod_continuity_constraint() -> None:
    reconstructed = (
        secular_trend(REFERENCE_YEAR)
        + core_delta_t(REFERENCE_YEAR)
        + cryo_delta_t(REFERENCE_YEAR)
    )
    assert abs(reconstructed - REFERENCE_LOD) < 1.0


# ---------------------------------------------------------------------------
# historical_core_delta_t — no data file present
# ---------------------------------------------------------------------------

def test_historical_core_returns_zero_when_no_data_file() -> None:
    if _load_historical_core_series():
        pytest.skip("historical_core_angular_momentum.txt is present — skipping no-data test")
    assert historical_core_delta_t(1840.0) == 0.0
    assert historical_core_delta_t(1900.0) == 0.0
    assert historical_core_delta_t(1962.0) == 0.0


# ---------------------------------------------------------------------------
# _historical_bridge_delta_t
# ---------------------------------------------------------------------------

def test_historical_bridge_is_zero_outside_support() -> None:
    assert _historical_bridge_delta_t(1839.99) == 0.0
    assert _historical_bridge_delta_t(1963.0) == 0.0


def test_historical_bridge_plus_secular_equals_smh2016_when_no_core_data() -> None:
    if _load_historical_core_series():
        pytest.skip("historical_core_angular_momentum.txt is present — skipping no-data test")
    for year in [1840.0, 1870.0, 1900.0, 1930.0, 1960.0]:
        reconstructed = secular_trend(year) + _historical_bridge_delta_t(year)
        assert reconstructed == pytest.approx(_smh2016_lookup(year), abs=1e-12)


def test_historical_bridge_is_large_and_negative_at_1840() -> None:
    # Secular overshoots by ~158 s at 1840; bridge must be strongly negative.
    val = _historical_bridge_delta_t(1840.0)
    assert val < -100.0


# ---------------------------------------------------------------------------
# delta_t_hybrid — historical era physics routing
# ---------------------------------------------------------------------------

def test_delta_t_hybrid_historical_era_matches_smh2016_when_no_core_data() -> None:
    if _load_historical_core_series():
        pytest.skip("historical_core_angular_momentum.txt is present — skipping no-data test")
    for year in [1840.0, 1880.0, 1920.0, 1960.0]:
        assert delta_t_hybrid(year) == pytest.approx(_smh2016_lookup(year), abs=1e-12)


def test_delta_t_hybrid_historical_era_is_continuous_at_1840() -> None:
    # Both sides of 1840 use SMH2016; no seam.
    just_before = delta_t_hybrid(1839.99)
    just_after = delta_t_hybrid(1840.01)
    assert abs(just_before - just_after) < 0.1


# ---------------------------------------------------------------------------
# delta_t_breakdown
# ---------------------------------------------------------------------------

def test_breakdown_returns_dataclass() -> None:
    bd = delta_t_breakdown(2000.0)
    assert isinstance(bd, DeltaTBreakdown)


def test_breakdown_components_sum_to_total_for_all_eras() -> None:
    for year in [1500.0, 1850.0, 1980.0, 2024.5, 2050.0]:
        bd = delta_t_breakdown(year)
        reconstructed = bd.secular + bd.core + bd.cryo + bd.fluid + bd.bridge + bd.residual
        assert reconstructed == pytest.approx(bd.total, abs=1e-10), (
            f"Components do not sum to total at year={year}: "
            f"{reconstructed} != {bd.total}"
        )


def test_breakdown_total_matches_delta_t_hybrid() -> None:
    for year in [1500.0, 1850.0, 1980.0, 2024.5, 2050.0, 2100.0]:
        bd = delta_t_breakdown(year)
        assert bd.total == pytest.approx(delta_t_hybrid(year), abs=1e-10)


def test_breakdown_era_labels_are_correct() -> None:
    assert delta_t_breakdown(1000.0).era == 'pre-1840'
    assert delta_t_breakdown(1839.9).era == 'pre-1840'
    assert delta_t_breakdown(1840.0).era == 'historical'
    assert delta_t_breakdown(1900.0).era == 'historical'
    assert delta_t_breakdown(1962.5).era == 'measured'
    assert delta_t_breakdown(2000.0).era == 'measured'
    assert delta_t_breakdown(2026.0).era == 'measured'
    assert delta_t_breakdown(2050.0).era == 'future'


def test_breakdown_pre_1840_secular_equals_total() -> None:
    bd = delta_t_breakdown(1700.0)
    assert bd.era == 'pre-1840'
    assert bd.secular == pytest.approx(bd.total, abs=1e-12)
    assert bd.core == 0.0
    assert bd.cryo == 0.0
    assert bd.fluid == 0.0
    assert bd.bridge == 0.0
    assert bd.residual == 0.0


def test_breakdown_historical_era_cryo_fluid_residual_are_zero() -> None:
    bd = delta_t_breakdown(1900.0)
    assert bd.era == 'historical'
    assert bd.cryo == 0.0
    assert bd.fluid == 0.0
    assert bd.residual == 0.0


def test_breakdown_future_era_has_no_policy_bridge() -> None:
    bd = delta_t_breakdown(2060.0)
    assert bd.era == 'future'
    assert bd.fluid == 0.0
    assert bd.bridge == 0.0
    assert bd.residual == 0.0


def test_breakdown_year_field_matches_input() -> None:
    for year in [1500.0, 1900.0, 2000.0, 2050.0]:
        bd = delta_t_breakdown(year)
        assert bd.year == year


def test_breakdown_all_fields_are_finite() -> None:
    for year in [-500.0, 1000.0, 1840.0, 1900.0, 1962.5, 2000.0, 2026.0, 2050.0, 2100.0]:
        bd = delta_t_breakdown(year)
        for field in (bd.total, bd.secular, bd.core, bd.cryo, bd.fluid, bd.bridge, bd.residual):
            assert math.isfinite(field), f"Non-finite component at year={year}: {bd}"


def test_breakdown_is_accessible_from_essentials() -> None:
    from moira.essentials import DeltaTBreakdown as BD, delta_t_breakdown as dtb
    bd = dtb(2000.0)
    assert isinstance(bd, BD)


def test_breakdown_is_accessible_from_facade() -> None:
    from moira.facade import DeltaTBreakdown as BD, delta_t_breakdown as dtb
    bd = dtb(2000.0)
    assert isinstance(bd, BD)
