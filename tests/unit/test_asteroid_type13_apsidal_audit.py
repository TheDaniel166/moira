"""Govern the exhaustive asteroid Type-13 apsidal sampling audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import audit_asteroid_type13_apsides as audit


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    ROOT
    / "tests"
    / "artifacts"
    / "oracle"
    / "asteroid_type13_apsidal_sampling_audit_2026-09-28.json"
)


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_partitions_every_admitted_asteroid(artifact: dict) -> None:
    universe = artifact["admitted_universe"]
    partition = artifact["catalog_partition"]

    assert artifact["status"] == "complete_catalog_partition"
    assert universe["body_count"] == 11_223
    assert universe["missing_perihelion_count"] == 0
    assert universe["unbound_orbit_count"] == 0
    assert partition == {
        "direct_authority_body_count": 126,
        "outer_invariant_body_count": 11_097,
        "partition_total": 11_223,
    }


def test_audit_is_bound_to_current_identity_and_manifest(artifact: dict) -> None:
    universe = artifact["admitted_universe"]
    identity_path = ROOT / universe["identity_path"]
    manifest_path = ROOT / universe["manifest_path"]

    assert _sha256(identity_path) == universe["identity_sha256"]
    assert _sha256(manifest_path) == universe["manifest_sha256"]


def test_every_direct_candidate_has_complete_extremum_evidence(
    artifact: dict,
) -> None:
    results = artifact["direct_results"]
    numbers = {result["number"] for result in results}

    assert len(results) == len(numbers) == 126
    assert all(result["sbdb_perihelion_au"] < 1.3 for result in results)
    assert all(result["radial_extrema_detected"] > 0 for result in results)
    assert all(result["off_grid_witness_count"] > 0 for result in results)
    assert all(result["authority_series_consistent"] is True for result in results)
    assert all(
        result["shared_node_max_radial_error_km"] <= audit.SHARED_NODE_GATE_KM
        for result in results
    )
    assert all(
        result["shared_node_max_cartesian_error_km"] <= audit.SHARED_NODE_GATE_KM
        for result in results
    )
    assert all(result["worst_radial_error"]["error_km"] >= 0.0 for result in results)
    assert all(
        result["worst_cartesian_error"]["error_km"] >= 0.0
        for result in results
    )


def test_repair_scope_is_exactly_the_failed_direct_set(artifact: dict) -> None:
    gate = artifact["acceptance_gate"]["distance_absolute_km"]
    results = artifact["direct_results"]
    expected = {
        result["number"]
        for result in results
        if result["worst_radial_error"]["error_km"] > gate
    }
    declared = {body["number"] for body in artifact["repair_scope"]["bodies"]}

    assert expected == declared
    assert len(expected) == artifact["repair_scope"]["body_count"] == 59
    assert artifact["repair_scope"]["shard_count"] == 40
    assert len(set(artifact["repair_scope"]["shard_indices"])) == 40
    assert all(result["passed"] == (result["number"] not in expected) for result in results)


def test_outer_domain_bound_has_large_margin(artifact: dict) -> None:
    bound = artifact["outer_domain_invariant"]

    assert bound["perihelion_distance_au"] == audit.DIRECT_CUTOFF_AU
    assert bound["passed"] is True
    assert bound["worst_radial_error"]["error_km"] < 0.001
    assert bound["radial_margin_factor"] > 800.0


def test_audit_sampling_and_gate_match_the_governed_policy(artifact: dict) -> None:
    assert artifact["sampling"] == {
        "base_step_days": audit.BASE_STEP_DAYS,
        "authority_step_days": audit.AUDIT_STEP_DAYS,
        "window_size": audit.WINDOW_SIZE,
        "same_start_stop_interval": True,
        "direct_cutoff_au": audit.DIRECT_CUTOFF_AU,
        "shared_node_consistency_gate_km": audit.SHARED_NODE_GATE_KM,
    }
    assert artifact["acceptance_gate"]["distance_absolute_au"] == (
        audit.DISTANCE_GATE_AU
    )
    assert artifact["acceptance_gate"]["distance_absolute_km"] == pytest.approx(
        audit.DISTANCE_GATE_KM,
        abs=1.0e-15,
    )
