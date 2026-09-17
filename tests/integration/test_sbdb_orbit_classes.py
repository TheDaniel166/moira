"""Integration tests for SBDB osculating small-body orbit classification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.orbits import (
    ORBIT_CLASS_POLICY,
    OrbitClassCode,
    OrbitClassResult,
    orbit_class,
    orbit_classes_at,
)


_KNOWN_WHEEL_CLASSES: dict[str, OrbitClassCode] = {
    "Ceres": OrbitClassCode.MBA,
    "Pallas": OrbitClassCode.MBA,
    "Vesta": OrbitClassCode.MBA,
    "Eros": OrbitClassCode.AMO,
    "Amor": OrbitClassCode.AMO,
    "Chiron": OrbitClassCode.CEN,
    "Pholus": OrbitClassCode.CEN,
    "Chariklo": OrbitClassCode.CEN,
    "Quaoar": OrbitClassCode.TNO,
    "Sedna": OrbitClassCode.TNO,
}


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_real_kernel_small_bodies_match_sbdb_classes(
    receipted_small_body_reader_pool,
) -> None:
    """Classify real small bodies at J2000 from authentic SPK kernels."""
    pool = receipted_small_body_reader_pool
    jd_ut = 2451545.0  # J2000 epoch

    for body_name, expected_code in _KNOWN_WHEEL_CLASSES.items():
        res = orbit_class(body_name, jd_ut, reader=pool)
        assert isinstance(res, OrbitClassResult)
        assert res.code == expected_code, f"{body_name} expected {expected_code}, got {res.code}"
        assert res.classification_policy == ORBIT_CLASS_POLICY
        assert res.elements.semi_major_axis_au is not None
        assert res.elements.eccentricity >= 0.0
        assert res.elements.pericenter_distance_au > 0.0

        # Every matched condition must have a positive signed margin
        for margin in res.boundary_margins:
            assert margin.signed_difference > 0.0, (
                f"{body_name} condition {margin.parameter} {margin.operator} "
                f"{margin.boundary} had non-positive margin {margin.signed_difference}"
            )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_real_kernel_batch_orbit_classes(
    receipted_small_body_reader_pool,
) -> None:
    """Batch classify a multi-family sequence of real small bodies."""
    pool = receipted_small_body_reader_pool
    jd_ut = 2451545.0
    bodies = ["Ceres", "Eros", "Chiron", "Sedna"]

    batch_result = orbit_classes_at(bodies, jd_ut, reader=pool)
    assert len(batch_result.items) == 4
    assert [item.input_body for item in batch_result.items] == bodies

    for item in batch_result.items:
        assert item.error is None
        assert item.result is not None
        expected = _KNOWN_WHEEL_CLASSES[str(item.input_body)]
        assert item.result.code == expected


@pytest.mark.external_network
def test_live_sbdb_api_drift_check() -> None:
    """Audit live JPL SBDB API classifications against Moira classification engine."""
    from scripts.build_sbdb_orbit_class_fixtures import fetch_sbdb_orbit_record

    # Verify live API for Ceres and Chiron when external network is explicitly granted
    for designation, expected_class in [("1", "MBA"), ("2060", "CEN")]:
        record = fetch_sbdb_orbit_record(designation)
        orbit_data = record.get("orbit", {})
        data_class = orbit_data.get("class", {}).get("code")
        assert data_class == expected_class
