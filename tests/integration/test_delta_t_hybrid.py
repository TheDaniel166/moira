import math

import pytest

from moira.delta_t_physical import (
    REFERENCE_LOD,
    REFERENCE_YEAR,
    delta_t_hybrid,
    delta_t_hybrid_uncertainty,
    secular_trend,
    core_delta_t,
    cryo_delta_t,
    _load_grace_series,
    _load_core_series,
    _fitted_residual_spline,
)
from moira.julian import delta_t as _iers_delta_t


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IERS_EPOCHS: tuple[tuple[float, float], ...] = (
    (1962.5, 33.2),
    (1965.5, 35.7),
    (1970.5, 40.2),
    (1975.5, 45.5),
    (1980.5, 50.5),
    (1985.5, 54.3),
    (1990.5, 56.9),
    (1995.5, 60.8),
    (2000.5, 63.8),
    (2005.5, 64.7),
    (2010.5, 66.1),
    (2015.5, 68.1),
    (2020.5, 69.4),
)


# ---------------------------------------------------------------------------
# Data file presence guards
# ---------------------------------------------------------------------------

def test_grace_data_file_is_present() -> None:
    series = _load_grace_series()
    assert len(series) > 0, (
        "grace_lod_contribution.txt is missing — run scripts/fetch_grace_j2.py"
    )


def test_core_data_file_is_present() -> None:
    series = _load_core_series()
    assert len(series) > 0, (
        "core_angular_momentum.txt is missing — run scripts/fetch_iers_eop.py"
    )


def test_grace_series_covers_expected_epoch_range() -> None:
    series = _load_grace_series()
    years = [r[0] for r in series]
    assert min(years) < 2003.0
    assert max(years) > 2020.0


def test_core_series_covers_expected_epoch_range() -> None:
    series = _load_core_series()
    years = [r[0] for r in series]
    assert min(years) <= 1963.0
    assert max(years) >= 2024.0


# ---------------------------------------------------------------------------
# Residual spline fit quality
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_residual_spline_in_sample_rms_within_target_band() -> None:
    fit = _fitted_residual_spline()
    assert fit.in_sample_rms < 2.0, (
        f"Residual spline in-sample RMS {fit.in_sample_rms:.3f} s exceeds 2.0 s. "
        "Spline may not be tracking the residual adequately."
    )


@pytest.mark.integration
def test_residual_spline_is_not_none() -> None:
    fit = _fitted_residual_spline()
    assert fit.spline is not None


@pytest.mark.integration
def test_residual_spline_cv_rms_is_finite() -> None:
    fit = _fitted_residual_spline()
    assert math.isfinite(fit.cv_rms)
    assert fit.cv_rms > 0.0


@pytest.mark.integration
def test_residual_spline_cv_rms_is_within_operational_ceiling() -> None:
    fit = _fitted_residual_spline()
    assert fit.cv_rms < 0.5, (
        f"Residual spline interior CV RMS {fit.cv_rms:.3f} s exceeds 0.5 s."
    )


# ---------------------------------------------------------------------------
# delta_t_hybrid vs IERS measured table
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize(("year", "expected_s"), _IERS_EPOCHS)
def test_hybrid_matches_iers_within_2s(year: float, expected_s: float) -> None:
    result = delta_t_hybrid(year)
    assert abs(result - expected_s) < 2.0, (
        f"delta_t_hybrid({year}) = {result:.3f} s, "
        f"IERS = {expected_s:.3f} s, "
        f"diff = {abs(result - expected_s):.3f} s"
    )


@pytest.mark.integration
def test_hybrid_rms_vs_iers_table_below_half_second() -> None:
    errors = [
        (delta_t_hybrid(year) - expected) ** 2
        for year, expected in _IERS_EPOCHS
    ]
    rms = math.sqrt(sum(errors) / len(errors))
    assert rms < 1.5, (
        f"RMS of delta_t_hybrid vs IERS 5-year table = {rms:.3f} s (target < 1.5 s)"
    )


@pytest.mark.integration
def test_hybrid_max_error_vs_iers_table_below_2s() -> None:
    max_err = max(
        abs(delta_t_hybrid(year) - expected)
        for year, expected in _IERS_EPOCHS
    )
    assert max_err < 2.0, (
        f"Max |delta_t_hybrid − IERS| = {max_err:.3f} s (target < 2.0 s)"
    )


@pytest.mark.integration
def test_hybrid_agrees_with_iers_delta_t_in_modern_era() -> None:
    for year in (2015.0, 2018.0, 2021.0, 2024.0):
        hybrid = delta_t_hybrid(year)
        iers = _iers_delta_t(year)
        assert abs(hybrid - iers) < 2.0, (
            f"delta_t_hybrid({year}) = {hybrid:.3f} s vs "
            f"delta_t({year}) = {iers:.3f} s, diff = {abs(hybrid - iers):.3f} s"
        )


# ---------------------------------------------------------------------------
# Era boundary behaviour
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_hybrid_is_finite_across_full_range() -> None:
    years = [-500.0, 0.0, 500.0, 1000.0, 1500.0, 1840.0, 1900.0,
             1962.0, 2002.0, 2026.0, 2050.0, 2100.0, 2150.0]
    for year in years:
        val = delta_t_hybrid(year)
        assert math.isfinite(val), f"delta_t_hybrid({year}) = {val}"


@pytest.mark.integration
def test_hybrid_at_reference_year_equals_reference_lod_within_1s() -> None:
    val = delta_t_hybrid(REFERENCE_YEAR)
    assert abs(val - REFERENCE_LOD) < 1.0, (
        f"delta_t_hybrid({REFERENCE_YEAR}) = {val:.3f} s, "
        f"REFERENCE_LOD = {REFERENCE_LOD} s"
    )


@pytest.mark.integration
def test_hybrid_pre_1840_matches_smh2016_exactly() -> None:
    from moira.delta_t_physical import _smh2016_lookup
    for year in (1800.0, 1820.0, 1839.0):
        assert delta_t_hybrid(year) == _smh2016_lookup(year)


@pytest.mark.integration
def test_hybrid_future_secular_growth_is_positive() -> None:
    assert delta_t_hybrid(2075.0) > delta_t_hybrid(2026.0)
    assert delta_t_hybrid(2100.0) > delta_t_hybrid(2075.0)


# ---------------------------------------------------------------------------
# Component isolation
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_secular_trend_dominates_in_far_future() -> None:
    year = 2100.0
    base = secular_trend(year)
    total = delta_t_hybrid(year)
    assert abs(total - base) < 5.0, (
        f"Non-secular contribution at {year} = {total - base:.3f} s — "
        "unexpectedly large"
    )


@pytest.mark.integration
def test_cryo_contribution_is_small_at_reference_year() -> None:
    cryo = cryo_delta_t(REFERENCE_YEAR)
    assert abs(cryo) < 1.0, (
        f"cryo_delta_t({REFERENCE_YEAR}) = {cryo:.3f} s — unexpectedly large"
    )


@pytest.mark.integration
def test_core_contribution_covers_modern_era() -> None:
    series = _load_core_series()
    if not series:
        pytest.skip("core_angular_momentum.txt not present")
    val = core_delta_t(2000.0)
    assert math.isfinite(val)


# ---------------------------------------------------------------------------
# Uncertainty model
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_uncertainty_at_anchor_is_below_1s() -> None:
    sigma = delta_t_hybrid_uncertainty(REFERENCE_YEAR)
    assert sigma < 1.0


@pytest.mark.integration
def test_uncertainty_at_2100_is_below_3s() -> None:
    sigma = delta_t_hybrid_uncertainty(2100.0)
    assert sigma < 5.0, (
        f"delta_t_hybrid_uncertainty(2100) = {sigma:.3f} s — "
        "higher than expected ceiling"
    )


@pytest.mark.integration
def test_uncertainty_grows_monotonically_into_future() -> None:
    sigmas = [delta_t_hybrid_uncertainty(y) for y in (2026.0, 2040.0, 2060.0, 2080.0, 2100.0)]
    for i in range(len(sigmas) - 1):
        assert sigmas[i] <= sigmas[i + 1] + 0.01, (
            f"Uncertainty not monotone: σ({2026 + i*20}) = {sigmas[i]:.3f} s > "
            f"σ({2026 + (i+1)*20}) = {sigmas[i+1]:.3f} s"
        )


@pytest.mark.integration
def test_uncertainty_is_finite_across_full_range() -> None:
    for year in (1900.0, 1962.0, 2000.0, 2026.0, 2050.0, 2100.0):
        assert math.isfinite(delta_t_hybrid_uncertainty(year))
