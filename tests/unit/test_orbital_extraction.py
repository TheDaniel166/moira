"""Closed-form and singularity tests for Stage 1 conic extraction."""

from __future__ import annotations

import math

import pytest

from moira._orbital_errors import OrbitalStateDegenerateError
from moira.constants import KM_PER_AU
from moira.orbits import (
    OrbitShape,
    UndefinedElementReason,
    _extract_osculating_conic,
)


MU = 132712440041.27942
EPOCH = 2451545.0


def _periapsis_state(
    *,
    pericenter_km: float,
    eccentricity: float,
    retrograde: bool = False,
):
    speed = math.sqrt(MU * (1.0 + eccentricity) / pericenter_km)
    if retrograde:
        speed = -speed
    return (pericenter_km, 0.0, 0.0), (0.0, speed * 86400.0, 0.0)


def _extract(position, velocity):
    return _extract_osculating_conic(
        position,
        velocity,
        MU,
        body_name="synthetic",
        epoch_tdb=EPOCH,
    )


def _undefined(result, field):
    return next(item.reasons for item in result.undefined if item.field == field)


def test_exact_circular_equatorial_state_has_explicit_undefined_fields():
    radius = 7000.0
    speed_day = math.sqrt(MU / radius) * 86400.0
    result = _extract((radius, 0.0, 0.0), (0.0, speed_day, 0.0))

    assert result.shape is OrbitShape.ELLIPTIC
    assert result.eccentricity == pytest.approx(0.0, abs=2e-16)
    assert result.lon_ascending_node_deg is None
    assert result.arg_pericenter_deg is None
    assert result.true_anomaly_deg is None
    assert result.mean_anomaly_deg is None
    assert result.time_of_pericenter_tdb is None
    assert result.true_longitude_deg == pytest.approx(0.0)
    assert result.mean_longitude_deg == pytest.approx(0.0)
    assert _undefined(result, "arg_pericenter_deg") == (
        UndefinedElementReason.CIRCULAR,
        UndefinedElementReason.EQUATORIAL,
    )


def test_exact_retrograde_equatorial_state_preserves_180_degree_inclination():
    position, velocity = _periapsis_state(
        pericenter_km=0.8 * KM_PER_AU,
        eccentricity=0.2,
        retrograde=True,
    )
    result = _extract(position, velocity)

    assert result.inclination_deg == pytest.approx(180.0)
    assert result.lon_ascending_node_deg is None
    assert result.lon_pericenter_deg == pytest.approx(0.0)
    assert UndefinedElementReason.EQUATORIAL in _undefined(
        result, "lon_ascending_node_deg"
    )


def test_elliptic_periapsis_recovers_closed_form_and_time():
    q = 0.8 * KM_PER_AU
    position, velocity = _periapsis_state(pericenter_km=q, eccentricity=0.2)
    result = _extract(position, velocity)

    assert result.shape is OrbitShape.ELLIPTIC
    assert result.semi_major_axis_au == pytest.approx(1.0, rel=2e-15)
    assert result.pericenter_distance_au == pytest.approx(0.8, rel=2e-15)
    assert result.apocenter_distance_au == pytest.approx(1.2, rel=2e-15)
    assert result.true_anomaly_deg == pytest.approx(0.0, abs=1e-12)
    assert result.mean_anomaly_deg == pytest.approx(0.0, abs=1e-12)
    assert result.time_of_pericenter_tdb == pytest.approx(EPOCH, abs=1e-12)


def test_parabolic_periapsis_uses_barker_branch_without_placeholders():
    q = 0.5 * KM_PER_AU
    position, velocity = _periapsis_state(pericenter_km=q, eccentricity=1.0)
    result = _extract(position, velocity)

    assert result.shape is OrbitShape.PARABOLIC
    assert result.semi_major_axis_au is None
    assert result.mean_motion_deg_per_day is None
    assert result.mean_anomaly_deg is None
    assert result.orbital_period_days is None
    assert result.apocenter_distance_au is None
    assert result.time_of_pericenter_tdb == pytest.approx(EPOCH, abs=1e-12)
    assert _undefined(result, "semi_major_axis_au") == (
        UndefinedElementReason.PARABOLIC,
    )


def test_hyperbolic_periapsis_has_negative_axis_and_signed_anomaly():
    q = 1.0 * KM_PER_AU
    position, velocity = _periapsis_state(pericenter_km=q, eccentricity=1.5)
    result = _extract(position, velocity)

    assert result.shape is OrbitShape.HYPERBOLIC
    assert result.semi_major_axis_au == pytest.approx(-2.0, rel=2e-15)
    assert result.mean_anomaly_deg == pytest.approx(0.0, abs=1e-12)
    assert result.time_of_pericenter_tdb == pytest.approx(EPOCH, abs=1e-12)
    assert result.orbital_period_days is None
    assert result.apocenter_distance_au is None
    assert result.mean_longitude_deg is None


@pytest.mark.parametrize(
    ("position", "velocity", "condition"),
    [
        ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), "ZERO_POSITION"),
        ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), "ZERO_VELOCITY"),
        ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), "RECTILINEAR_STATE"),
    ],
)
def test_degenerate_states_fail_with_dimensionless_receipt(
    position, velocity, condition
):
    with pytest.raises(OrbitalStateDegenerateError) as caught:
        _extract(position, velocity)
    assert caught.value.condition == condition
    assert caught.value.threshold > 0.0


def test_scalar_elements_are_invariant_under_a_common_orthogonal_rotation():
    q = 0.8 * KM_PER_AU
    position, velocity = _periapsis_state(pericenter_km=q, eccentricity=0.2)
    angle = math.radians(37.0)
    cosine, sine = math.cos(angle), math.sin(angle)

    def rotate(vector):
        x, y, z = vector
        return (cosine * x - sine * y, sine * x + cosine * y, z)

    original = _extract(position, velocity)
    rotated = _extract(rotate(position), rotate(velocity))
    assert rotated.eccentricity == pytest.approx(original.eccentricity, abs=2e-15)
    assert rotated.semi_major_axis_au == pytest.approx(
        original.semi_major_axis_au, rel=2e-15
    )
    assert rotated.pericenter_distance_au == pytest.approx(
        original.pericenter_distance_au, rel=2e-15
    )
    assert rotated.mean_anomaly_deg == pytest.approx(
        original.mean_anomaly_deg, abs=2e-12
    )
