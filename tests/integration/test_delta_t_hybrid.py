"""Integration proofs for the admitted Delta-T model layers.

The canonical-vs-physical comparisons below exercise Moira's internal source
priority and public vessels.  They do not constitute external-oracle proof.
"""

import math

import pytest

import moira.delta_t_physical as dtp
import moira.julian as julian_module
from moira.julian import delta_t as canonical_delta_t


@pytest.mark.parametrize(
    "year",
    (
        -2000.0,
        -720.0,
        0.0,
        1000.0,
        1840.0,
        1962.5,
        1970.0,
        1980.0,
        1990.0,
        2000.0,
        2010.0,
        2020.0,
        2026.0,
    ),
)
def test_source_priority_total_is_exact_through_reference_epoch(year: float) -> None:
    assert dtp.delta_t_hybrid(year) == canonical_delta_t(year)


def test_source_priority_grid_is_exact_not_merely_within_a_loose_tolerance() -> None:
    year = -2000.0
    while year <= dtp.REFERENCE_YEAR:
        assert dtp.delta_t_hybrid(year) == canonical_delta_t(year)
        year += 7.25


@pytest.mark.parametrize("year", (-2000.0, 1840.0, 1962.5, 2000.0, 2026.0, 2050.0, 2100.0))
def test_candidate_attribution_fields_are_zero_in_every_era(year: float) -> None:
    result = dtp.delta_t_breakdown(year)
    assert result.core == 0.0
    assert result.cryo == 0.0
    assert result.fluid == 0.0
    assert result.residual == 0.0


def test_quarantined_artifacts_are_present_only_as_research_diagnostics() -> None:
    grace = dtp._load_grace_series()
    total_lod = dtp._load_core_series()
    assert len(grace) > 10
    assert len(total_lod) > 10

    for year in (2005.0, 2015.0, 2026.0, 2100.0):
        assert dtp.cryo_delta_t(year) == 0.0
        assert dtp.core_delta_t(year) == 0.0


def test_historical_source_uncertainty_anchors_are_exercised_from_packaged_table() -> None:
    expected = {
        -2000.0: 2520.0,
        -720.0: 180.0,
        0.0: 90.0,
        1000.0: 15.0,
        1800.0: 0.5,
        2015.0: 0.05,
    }
    for year, source_error in expected.items():
        assert dtp.delta_t_hybrid_uncertainty(year) == source_error


def test_modern_uncertainty_floor_bridges_to_the_forecast_continuously() -> None:
    assert dtp.delta_t_hybrid_uncertainty(2016.0) == 0.06
    assert dtp.delta_t_hybrid_uncertainty(2020.0) == 0.06
    assert dtp.delta_t_hybrid_uncertainty(2026.0) == 0.06
    assert dtp.delta_t_hybrid_uncertainty(dtp.REFERENCE_YEAR + 1e-7) == pytest.approx(
        0.06, abs=1e-6
    )


def test_future_scenario_is_boundary_conditioned_and_continues_past_confidence_boundary() -> None:
    boundary = julian_module._delta_t_observation_boundary()
    reference = boundary.total
    slope = boundary.slope
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF

    for year in (2027.0, 2030.0, 2050.0, 2100.0, 2150.0, 2150.0001, 2200.0):
        horizon = year - boundary.year
        expected = reference + slope * horizon + curvature * (horizon / 100.0) ** 2
        assert dtp.delta_t_hybrid(year) == pytest.approx(expected, abs=1e-12)

def test_total_and_every_numeric_component_are_continuous_at_model_seams() -> None:
    for seam in (1840.0, 1962.5, dtp.REFERENCE_YEAR):
        epsilon = 1e-7
        left = dtp.delta_t_breakdown(seam - epsilon)
        right = dtp.delta_t_breakdown(seam + epsilon)
        for field in ("total", "secular", "core", "cryo", "fluid", "bridge", "residual"):
            assert abs(getattr(right, field) - getattr(left, field)) < 1e-5


def test_future_handoff_matches_value_and_observed_boundary_slope() -> None:
    step = 1e-3
    reference = dtp.delta_t_hybrid(dtp.REFERENCE_YEAR)
    left_slope = (reference - dtp.delta_t_hybrid(dtp.REFERENCE_YEAR - step)) / step
    right_slope = (dtp.delta_t_hybrid(dtp.REFERENCE_YEAR + step) - reference) / step
    source_slope = julian_module._delta_t_observation_boundary().slope
    assert left_slope == pytest.approx(source_slope, abs=1e-8)
    assert right_slope == pytest.approx(source_slope, abs=3e-6)


def test_future_uncertainty_scale_is_finite_and_monotone_on_validation_grid() -> None:
    years = (2026.0, 2030.0, 2050.0, 2075.0, 2100.0, 2150.0)
    values = [dtp.delta_t_hybrid_uncertainty(year) for year in years]
    assert all(math.isfinite(value) and value > 0.0 for value in values)
    assert values == sorted(values)


def test_residual_validation_is_explicitly_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="not an independent, fail-closed authority validation"):
        dtp._fitted_residual_spline()


def test_breakdown_and_distribution_public_exports_are_unchanged() -> None:
    from moira import facade
    from moira import essentials

    facade_breakdown = facade.delta_t_breakdown(2000.0)
    essentials_breakdown = essentials.delta_t_breakdown(2000.0)
    facade_distribution = facade.delta_t_distribution(2100.0)
    essentials_distribution = essentials.delta_t_distribution(2100.0)

    assert isinstance(facade_breakdown, dtp.DeltaTBreakdown)
    assert isinstance(essentials_breakdown, dtp.DeltaTBreakdown)
    assert isinstance(facade_distribution, dtp.DeltaTDistribution)
    assert isinstance(essentials_distribution, dtp.DeltaTDistribution)
