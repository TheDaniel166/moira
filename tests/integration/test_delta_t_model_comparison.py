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
  post-2026   : diverge significantly — table cascade uses M&S parabolic
                extrapolation; physical model uses tidal + cryo + core 10-yr mean.
                Divergence reaches ~22 s by 2050, ~118 s by 2100.

The divergence in the future era is expected and intentional.  The physical
model is the preferred source for future-epoch work; the table cascade's
polynomial extrapolation is known to overshoot the physically plausible range.
"""
from __future__ import annotations

import math
import pytest

from moira.julian import DeltaTPolicy, delta_t as _table_delta_t
from moira.delta_t_physical import delta_t_hybrid as _physical_delta_t


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
# Future era (post-2026): models diverge — physical is lower than table
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize(("year", "min_divergence_s"), [
    (2050.0, 10.0),
    (2075.0, 40.0),
    (2100.0, 80.0),
])
def test_future_era_models_diverge(year: float, min_divergence_s: float) -> None:
    """
    The table cascade uses the M&S parabolic extrapolation past 2026, which
    grows steeply.  The physical model uses tidal + cryo + core 10-year mean,
    which grows conservatively.  Divergence must exceed the threshold — if it
    doesn't, something has changed in one of the models.
    """
    table, physical = _both(year)
    divergence = table - physical
    assert divergence > min_divergence_s, (
        f"year={year}: table={table:.3f} s, physical={physical:.3f} s, "
        f"divergence={divergence:.3f} s — expected > {min_divergence_s} s. "
        "Table cascade parabola may have changed, or physical model is drifting up."
    )


@pytest.mark.integration
def test_future_era_physical_is_lower_than_table() -> None:
    """Physical model must be consistently below the table cascade post-2026."""
    for year in (2040.0, 2060.0, 2080.0, 2100.0, 2150.0):
        table, physical = _both(year)
        assert physical < table, (
            f"year={year}: physical={physical:.3f} s >= table={table:.3f} s — "
            "expected physical model to be lower than parabolic table extrapolation"
        )


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
