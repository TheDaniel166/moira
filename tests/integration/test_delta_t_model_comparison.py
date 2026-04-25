"""
Integration comparison: 'hybrid' table cascade vs 'physical' model across all eras.

Purpose
-------
Verify the expected agreement and divergence profile between the two ΔT models
exposed through DeltaTPolicy:

  'hybrid'   — moira.julian.delta_t()          (table cascade + M&S polynomials)
  'physical' — delta_t_physical.delta_t_hybrid() (tidal + GIA + core + cryo + spline)

Key findings (confirmed 2026-04-08):
  pre-1840    : identical — both route through the SMH 2016 table
  1840–1962   : agree to < 0.01 s — historical bridge absorbs the gap exactly
  1962–2026   : agree within 2 s — residual spline tracks IERS
  post-2026   : physical model owns a deterministic tidal/GIA secular baseline
                and exposes stochastic LOD uncertainty through its PDF surface.

Large future divergence is interpreted through the probability distribution,
not hidden by forcing the central value onto a convention.
"""
from __future__ import annotations

import math
import pytest

from moira.julian import DeltaTPolicy, delta_t as _table_delta_t
from moira.delta_t_physical import (
    delta_t_hybrid as _physical_delta_t,
    delta_t_hybrid_uncertainty as _physical_delta_t_sigma,
)


def _both(year: float) -> tuple[float, float]:
    """Return (table, physical) ΔT for the given decimal year."""
    return _table_delta_t(year), _physical_delta_t(year)


# ---------------------------------------------------------------------------
# Pre-1840: both models use the SMH 2016 table — must be identical
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("year", [500.0, 1000.0, 1600.0, 1700.0, 1800.0, 1839.0])
def test_pre_1840_models_are_identical(year: float) -> None:
    table, physical = _both(year)
    assert table == physical, (
        f"year={year}: table={table:.3f} s, physical={physical:.3f} s — "
        "expected exact equality in pre-1840 era (both use SMH 2016 table)"
    )


# ---------------------------------------------------------------------------
# Historical era (1840–1962): agreement within 0.1 s
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("year", [1840.0, 1870.0, 1900.0, 1920.0, 1940.0, 1960.0])
def test_historical_era_models_agree_within_0_1s(year: float) -> None:
    table, physical = _both(year)
    diff = abs(physical - table)
    assert diff < 0.1, (
        f"year={year}: table={table:.3f} s, physical={physical:.3f} s, "
        f"diff={diff:.4f} s — expected < 0.1 s in historical era"
    )


# ---------------------------------------------------------------------------
# Measured era (1962–2026): agreement within 2 s
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("year", [1962.5, 1970.0, 1980.0, 1990.0, 2000.0, 2010.0, 2020.0, 2026.0])
def test_measured_era_models_agree_within_2s(year: float) -> None:
    table, physical = _both(year)
    diff = abs(physical - table)
    assert diff < 2.0, (
        f"year={year}: table={table:.3f} s, physical={physical:.3f} s, "
        f"diff={diff:.3f} s — expected < 2 s in measured era"
    )


# ---------------------------------------------------------------------------
# Future era (post-2026): conventional forecast should stay inside the stochastic envelope
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("year", [
    2050.0,
    2075.0,
    2100.0,
])
def test_future_era_table_forecast_is_inside_two_sigma_distribution(year: float) -> None:
    """
    The conventional table forecast is no longer forced into the physical
    central value. It must remain plausible under the stochastic LOD envelope.
    """
    table, physical = _both(year)
    divergence = abs(table - physical)
    sigma = _physical_delta_t_sigma(year)
    assert divergence < 2.0 * sigma, (
        f"year={year}: table={table:.3f} s, physical={physical:.3f} s, "
        f"divergence={divergence:.3f} s, sigma={sigma:.3f} s"
    )


@pytest.mark.integration
def test_future_era_physical_mean_is_not_conventional_policy_bridge() -> None:
    """Physical central value must be owned by the stochastic baseline, not forced to the table."""
    table, physical = _both(2100.0)
    assert abs(physical - table) > 10.0


# ---------------------------------------------------------------------------
# DeltaTPolicy round-trip: both models accessible through the policy surface
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_policy_physical_matches_direct_call() -> None:
    policy = DeltaTPolicy(model='physical')
    for year in (1900.0, 2000.0, 2026.0, 2075.0):
        assert policy.compute(year) == _physical_delta_t(year), (
            f"DeltaTPolicy(model='physical').compute({year}) does not match "
            "delta_t_hybrid({year}) directly"
        )


@pytest.mark.integration
def test_policy_hybrid_matches_direct_call() -> None:
    policy = DeltaTPolicy(model='hybrid')
    for year in (1900.0, 2000.0, 2026.0, 2075.0):
        assert policy.compute(year) == _table_delta_t(year), (
            f"DeltaTPolicy(model='hybrid').compute({year}) does not match "
            "delta_t({year}) directly"
        )


# ---------------------------------------------------------------------------
# Both models are finite across the full range
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("year", [-500.0, 0.0, 500.0, 1000.0, 1600.0, 1900.0,
                                   1962.0, 2000.0, 2026.0, 2075.0, 2150.0])
def test_both_models_finite_across_full_range(year: float) -> None:
    table, physical = _both(year)
    assert math.isfinite(table), f"table model non-finite at {year}"
    assert math.isfinite(physical), f"physical model non-finite at {year}"
