"""Governance checks for the Orbital Core Stage 3 validation receipt."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


TEST_ROOT = Path(__file__).parents[1]
RECEIPT_PATH = (
    TEST_ROOT
    / "artifacts"
    / "release"
    / "orbital_core_stage3_validation_2026-09-16.json"
)
FIXTURE_PATH = (
    TEST_ROOT / "fixtures" / "horizons_orbital_elements_catalog_holdout.json"
)
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<!http)(?<!htt)(?:[a-z]:[\\/])")
ACCEPTANCE_GATES = {
    "arg_pericenter_angular_absolute_deg": 5.0e-10,
    "eccentricity_absolute": 2.0e-14,
    "inclination_absolute_deg": 2.0e-12,
    "node_angular_absolute_deg": 5.0e-10,
    "semi_major_axis_absolute_au": 2.0e-13,
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage3_receipt_is_path_free_and_binds_the_frozen_authority() -> None:
    rendered = RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = json.loads(rendered)
    fixture_bytes = FIXTURE_PATH.read_bytes()
    fixture = json.loads(fixture_bytes)

    assert receipt["schema"] == "moira.orbital-core-stage3.validation/v1"
    assert not WINDOWS_ABSOLUTE_PATH.search(rendered)
    authority = receipt["authority_fixture"]
    assert authority["sha256"] == hashlib.sha256(fixture_bytes).hexdigest()
    assert authority["bytes"] == len(fixture_bytes)
    assert authority["schema"] == fixture["schema_version"]
    assert authority["generator_version"] == fixture["generator_version"]
    assert authority["fixture_role"] == fixture["fixture_role"]
    assert authority["record_count"] == len(fixture["records"])
    assert authority["bodies"] == [record["body"] for record in fixture["records"]]
    assert authority["acceptance_gates"] == ACCEPTANCE_GATES


def test_stage3_receipt_freezes_the_exact_migration_contract() -> None:
    receipt = _load(RECEIPT_PATH)
    contract = receipt["migration_contract"]

    assert contract == {
        "center": "SUN",
        "frame": "TRUE_ECLIPTIC_OF_DATE",
        "frame_epoch_scale": "TT_JD",
        "frame_model_interval_tt": [2415020.0, 2488070.0],
        "input_time_scale": "UT1_JD",
        "legacy_vessel": "OrbitalNode unchanged",
        "pericenter_mapping": "pericenter_ecliptic_lon_deg",
        "state_evaluation_scale": "TDB_JD",
    }
    assert receipt["algorithm_version"] == (
        "MOIRA_GEOMETRIC_NODE_ORBITAL_CORE_STAGE3_V1"
    )


def test_stage3_receipt_does_not_overstate_catalog_or_release_readiness() -> None:
    receipt = _load(RECEIPT_PATH)
    counts = receipt["test_gate_counts"]
    gates = receipt["test_gates"]

    assert receipt["status"] == "implementation_review_ready_release_blocked"
    assert receipt["release_or_deployment_performed"] is False
    assert receipt["network_boundary"]["external_network_used"] is False
    assert counts["planetary_core_adapter"]["passed"] == 9
    assert counts["catalog_kernel_slice"] == {
        "authority_not_run": 6,
        "loaded_adapter_passed": 6,
        "unavailable_adapter_not_run": 0,
    }
    assert counts["full_catalog"] == {
        "bodies_passed": 10522,
        "releases_not_run": 0,
        "releases_passed": 2,
    }
    assert counts["stage3_focused"] == {
        "collected": 42,
        "passed": 36,
        "skipped": 6,
    }
    assert counts["orbital_regression"] == {
        "collected": 452,
        "passed": 440,
        "skipped": 12,
    }
    assert gates["catalog_authority"].startswith("NOT RUN - six comparisons")
    assert "10,025" in gates["full_catalog"]
    assert "497" in gates["full_catalog"]
    assert "baseline nested-project" in gates["non_external_network"]
    assert gates["live_jpl_horizons"].startswith("NOT RUN")
    assert receipt["blockers"]
    assert all("not installed" not in item.lower() for item in receipt["blockers"])

    releases = {
        (item["catalog_id"], item["catalog_version"]): item
        for item in receipt["catalog_release_identity"]
    }
    full_asteroids = releases[("moira-asteroids", "2026.08.12.1")]
    assert full_asteroids == {
        "body_count": 10025,
        "catalog_id": "moira-asteroids",
        "catalog_version": "2026.08.12.1",
        "manifest_sha256": (
            "9985f6e2da31e926f95391df17054e429ad72552ddc0793eaaaa3273f46febf0"
        ),
        "shard_count": 401,
    }
