"""Governance for the current small-body orbital catalog admission."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADMISSION_PATH = (
    ROOT
    / "tests"
    / "artifacts"
    / "oracle"
    / "small_body_orbital_catalog_admission_2026-09-28.json"
)
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<!http)(?<!htt)(?:[a-z]:[\\/])")
EXPECTED_GATES = {
    "apocenter_distance_absolute_au": 1.0e-5,
    "arg_pericenter_angular_absolute_deg": 0.05,
    "eccentricity_absolute": 1.0e-5,
    "inclination_absolute_deg": 1.0e-3,
    "mean_anomaly_angular_absolute_deg": 0.05,
    "node_angular_absolute_deg": 1.0e-3,
    "pericenter_distance_absolute_au": 1.0e-5,
    "semi_major_axis_absolute_au": 1.0e-5,
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_admission_binds_the_refreshed_primary_authority_fixture() -> None:
    rendered = ADMISSION_PATH.read_text(encoding="utf-8")
    admission = json.loads(rendered)
    authority = admission["authority_fixture"]
    fixture_path = ROOT / authority["path"]
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)

    assert admission["schema"] == (
        "moira.small-body-orbital-catalog-admission/v1"
    )
    assert admission["status"] == "admitted"
    assert not WINDOWS_ABSOLUTE_PATH.search(rendered)
    assert authority["sha256"] == hashlib.sha256(fixture_bytes).hexdigest()
    assert authority["bytes"] == len(fixture_bytes)
    assert authority["record_count"] == len(fixture["records"]) == 6
    assert authority["source"] == "official NASA/JPL Horizons API"
    assert authority["target_solutions"] == {
        record["body"]: record["authority"]["target_solution"]
        for record in fixture["records"]
    }
    assert admission["acceptance_gates"] == EXPECTED_GATES
    assert set(admission["measured_maxima"]) == set(EXPECTED_GATES)
    assert all(
        admission["measured_maxima"][field] <= limit
        for field, limit in EXPECTED_GATES.items()
    )
    assert "Pre-existing product tolerances" in admission["gate_origin"]


def test_admission_binds_exact_sealed_release_manifests() -> None:
    admission = _load(ADMISSION_PATH)
    releases = {
        (item["catalog_id"], item["catalog_version"]): item
        for item in admission["catalog_release_identity"]
    }
    expected = {
        ("moira-asteroids", "2026.09.18.1"): (
            ROOT / "moira" / "kernels" / "asteroids" / "manifest.json"
        ),
        ("moira-comets", "2026.07.28.1"): (
            ROOT / "moira" / "kernels" / "comets" / "manifest.json"
        ),
    }

    assert set(releases) == set(expected)
    for key, manifest_path in expected.items():
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        release = releases[key]
        assert release["manifest_sha256"] == hashlib.sha256(
            manifest_bytes
        ).hexdigest()
        assert release["body_count"] == manifest["body_count"]
        assert release["shard_count"] == manifest["shard_count"]
        assert release["sampling_step_days"] == manifest["sampling"][
            "step_days"
        ]


def test_admission_records_exhaustive_scope_without_overstating_it() -> None:
    admission = _load(ADMISSION_PATH)
    gate = admission["full_catalog_gate"]

    assert gate == {
        "bodies_passed": 11720,
        "releases_passed": 2,
        "scope": "11223 asteroids plus 497 periodic comets",
        "status": "passed",
    }
    assert admission["network_boundary"] == {
        "external_network_used": True,
        "live_drift_audit_cases_passed": 17,
        "live_drift_audit_cases_total": 17,
        "source": "official NASA/JPL Horizons API",
    }
    assert admission["limitations"]
    assert any(
        "not 11720 independent Horizons queries" in limitation
        for limitation in admission["limitations"]
    )
    assert admission["release_or_deployment_performed"] is False
    assert admission["verification"] == {
        "exhaustive_elements": {
            "bodies": 11720,
            "call_seconds": 93.095,
            "command": (
                ".venv/Scripts/python.exe -m pytest "
                "tests/integration/test_orbital_elements_full_catalog.py "
                "-q -rA --durations=5"
            ),
            "passed": 1,
            "skipped": 0,
        },
        "exhaustive_geometric_nodes": {
            "asteroid_call_seconds": 80.918,
            "bodies": 11720,
            "comet_call_seconds": 2.381,
            "command": (
                ".venv/Scripts/python.exe -m pytest "
                "tests/integration/test_geometric_nodes_full_catalog.py "
                "-q -rA --durations=5"
            ),
            "passed": 2,
            "skipped": 0,
        },
        "focused_offline_authority": {
            "command": (
                ".venv/Scripts/python.exe -m pytest "
                "tests/integration/test_orbital_elements_kernels.py "
                "tests/integration/test_geometric_nodes_kernels.py -q -rA"
            ),
            "passed": 44,
            "skipped": 0,
        },
        "live_primary_drift": {
            "command": (
                ".venv/Scripts/python.exe -m pytest "
                "tests/integration/test_horizons_orbits.py::"
                "test_stage1_exact_tdb_horizons_authority_has_not_drifted "
                "-m external_network --run-external-network -q -rA"
            ),
            "passed": 17,
            "skipped": 0,
        },
    }
