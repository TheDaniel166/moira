"""Policy comparison for canonical and explicitly physical Delta-T routing.

This module checks internal policy contracts only.  It intentionally contains
no fabricated IERS/Horizons fixture and makes no external parity claim.
"""

import math

import pytest

from moira.delta_t_physical import REFERENCE_YEAR, delta_t_hybrid as physical_delta_t
from moira.julian import DeltaTPolicy, delta_t as canonical_delta_t


@pytest.mark.parametrize(
    "year",
    (-2000.0, -720.0, 0.0, 1000.0, 1840.0, 1962.5, 2000.0, 2020.0, 2026.0),
)
def test_physical_policy_preserves_canonical_source_priority_through_2026(year: float) -> None:
    assert physical_delta_t(year) == canonical_delta_t(year)
    assert DeltaTPolicy(model="physical").compute(year) == canonical_delta_t(year)


@pytest.mark.parametrize(
    "year", (REFERENCE_YEAR + 0.0001, 2030.0, 2050.0, 2100.0, 2150.0)
)
def test_canonical_future_router_delegates_to_admitted_physical_scenario(year: float) -> None:
    assert canonical_delta_t(year) == physical_delta_t(year)
    assert DeltaTPolicy(model="hybrid").compute(year) == physical_delta_t(year)
    assert DeltaTPolicy(model="physical").compute(year) == physical_delta_t(year)


def test_explicit_physical_policy_enforces_only_the_source_floor() -> None:
    physical = DeltaTPolicy(model="physical")
    with pytest.raises(ValueError):
        physical.compute(-3000.0)
    assert math.isfinite(canonical_delta_t(-3000.0))

    # 2150 is a validation/confidence boundary.  The declared scenario remains
    # a continuous, explicitly unvalidated extrapolation beyond it.
    for year in (2150.0001, 2200.0):
        assert math.isfinite(physical.compute(year))
        assert physical.compute(year) == canonical_delta_t(year)


def test_nasa_canon_remains_a_distinct_explicit_policy() -> None:
    nasa = DeltaTPolicy(model="nasa_canon")
    physical = DeltaTPolicy(model="physical")
    differences = [
        abs(nasa.compute(year) - physical.compute(year))
        for year in (-1000.0, 1000.0, 1900.0, 2100.0)
    ]
    assert any(difference > 1e-6 for difference in differences)


def test_fixed_policy_remains_independent_of_all_model_routing() -> None:
    fixed = DeltaTPolicy(model="fixed", fixed_delta_t=123.456)
    for year in (-10000.0, 2000.0, 10000.0):
        assert fixed.compute(year) == 123.456


@pytest.mark.parametrize("year", (-2000.0, 0.0, 2026.0, 2050.0, 2150.0))
def test_admitted_physical_outputs_are_finite(year: float) -> None:
    assert math.isfinite(physical_delta_t(year))
