"""Structural and invariant tests for conventional Uranian positions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import math

import pytest

from moira.uranian import (
    UranianBody,
    _URANIAN_ELEMENTS,
    _solve_eccentric_anomaly,
    all_uranian_at,
    list_uranian,
    uranian_at,
)


def test_catalog_separates_hamburg_eight_from_transpluto() -> None:
    assert len(UranianBody.HAMBURG) == 8
    assert UranianBody.TRANSPLUTO not in UranianBody.HAMBURG
    assert UranianBody.ALL == UranianBody.HAMBURG + (UranianBody.TRANSPLUTO,)
    assert list_uranian() == list(UranianBody.ALL)


def test_element_sources_and_epochs_remain_separate() -> None:
    for name in UranianBody.HAMBURG:
        elements = _URANIAN_ELEMENTS[name]
        assert elements.epoch_jd_tt == 2415020.0
        assert elements.equinox_jd_tt == 2415020.0
        assert elements.body_group == "hamburg_eight"
        assert elements.source_family == "neely_1980_hamburg_revised"

    transpluto = _URANIAN_ELEMENTS[UranianBody.TRANSPLUTO]
    assert transpluto.epoch_jd_tt == 2368547.66
    assert transpluto.equinox_jd_tt == 2431456.5
    assert transpluto.eccentricity == 0.3
    assert transpluto.body_group == "transpluto"
    assert transpluto.source_family == "sevin_strubell_1952_transpluto"


def test_hamburg_orbits_have_century_scale_periods() -> None:
    periods = {
        name: _URANIAN_ELEMENTS[name].period_years
        for name in UranianBody.HAMBURG
    }
    assert 250.0 < periods[UranianBody.CUPIDO] < 275.0
    assert 750.0 < periods[UranianBody.POSEIDON] < 780.0
    assert all(period > 250.0 for period in periods.values())


@pytest.mark.parametrize("eccentricity", [0.0, 0.0046, 0.3])
@pytest.mark.parametrize("mean_anomaly", [0.0, 0.4, math.pi, 5.9])
def test_kepler_solver_satisfies_governing_equation(
    eccentricity: float,
    mean_anomaly: float,
) -> None:
    eccentric_anomaly = _solve_eccentric_anomaly(mean_anomaly, eccentricity)
    residual = eccentric_anomaly - eccentricity * math.sin(eccentric_anomaly)
    assert residual == pytest.approx(mean_anomaly, abs=1.0e-13)


def test_unknown_and_non_finite_inputs_fail_before_kernel_resolution() -> None:
    with pytest.raises(KeyError, match="Unknown Uranian body"):
        uranian_at("Nibiru", 2451545.0)
    with pytest.raises(ValueError, match="jd_ut must be finite"):
        uranian_at(UranianBody.CUPIDO, math.nan)
    with pytest.raises(ValueError, match="jd_ut must be finite"):
        all_uranian_at(math.inf)


def test_apparent_positions_carry_geometry_motion_and_provenance(moira_engine) -> None:
    positions = all_uranian_at(2451545.0, reader=moira_engine._reader)

    assert list(positions) == list(UranianBody.ALL)
    assert any(position.retrograde for position in positions.values())
    assert any(not position.retrograde for position in positions.values())
    for position in positions.values():
        assert 0.0 <= position.longitude < 360.0
        assert math.isfinite(position.latitude)
        assert position.distance_au > 39.0
        assert position.retrograde is (position.speed < 0.0)
        assert position.model == "fixed_keplerian_orbit_apparent_geocentric"
        assert position.frame == "apparent_geocentric_true_ecliptic_of_date"


def test_single_and_bulk_paths_are_equivalent(moira_engine) -> None:
    bulk = all_uranian_at(2452164.032291667, reader=moira_engine._reader)
    single = uranian_at(
        UranianBody.VULKANUS,
        2452164.032291667,
        reader=moira_engine._reader,
    )
    assert single == bulk[UranianBody.VULKANUS]


def test_position_vessel_is_immutable(moira_engine) -> None:
    position = uranian_at(
        UranianBody.CUPIDO,
        2451545.0,
        reader=moira_engine._reader,
    )
    with pytest.raises(FrozenInstanceError):
        position.longitude = 0.0
