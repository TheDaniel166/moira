"""Governance checks for the Orbital Core Stage 2 validation receipt."""

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
    / "orbital_core_stage2_validation_2026-09-15.json"
)
FIXTURE_PATH = TEST_ROOT / "fixtures" / "horizons_apsidal_passages_reference.json"
WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?<!http)(?<!htt)(?:[a-z]:[\\/])"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage2_receipt_is_path_free_and_binds_the_frozen_authority() -> None:
    rendered = RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = json.loads(rendered)
    fixture_bytes = FIXTURE_PATH.read_bytes()
    fixture = json.loads(fixture_bytes)

    assert receipt["schema"] == "moira.orbital-core-stage2.validation/v1"
    assert not WINDOWS_ABSOLUTE_PATH.search(rendered)
    assert receipt["authority_fixture"]["sha256"] == hashlib.sha256(
        fixture_bytes
    ).hexdigest()
    assert receipt["authority_fixture"]["bytes"] == len(fixture_bytes)
    assert receipt["authority_fixture"]["schema"] == fixture["schema_version"]
    assert receipt["authority_fixture"]["generator_version"] == fixture[
        "generator_version"
    ]
    assert receipt["authority_fixture"]["acceptance_gates"] == fixture[
        "acceptance_gates"
    ]
    assert receipt["authority_fixture"]["record_count"] == len(fixture["records"])
    assert receipt["authority_fixture"]["event_count"] == sum(
        len(record["events"]) for record in fixture["records"]
    )
    assert receipt["authority_fixture"]["bodies"] == [
        record["body"] for record in fixture["records"]
    ]


def test_stage2_receipt_does_not_overstate_catalog_or_release_readiness() -> None:
    receipt = _load(RECEIPT_PATH)
    gates = receipt["test_gates"]
    counts = receipt["test_gate_counts"]

    assert receipt["status"] == "implementation_review_ready_release_blocked"
    assert receipt["release_or_deployment_performed"] is False
    assert receipt["algorithm_version"] == "MOIRA_APSIDAL_PASSAGES_V1"
    assert gates["planetary_authority"] == "passed"
    assert counts["planetary_authority"]["passed"] == 10
    assert counts["live_jpl_horizons"]["passed"] == 2
    assert counts["catalog_kernel_slice"] == {
        "authority_not_run": 6,
        "runtime_smoke_passed": 1,
    }
    assert counts["stage2_final_consolidated"] == {
        "collected": 297,
        "passed": 289,
        "skipped": 8,
    }
    assert gates["catalog_authority"].startswith("NOT RUN - six comparisons")
    assert "not authority parity" in gates["catalog_runtime_smoke"]
    assert "baseline nested-project" in gates["non_external_network"]
    assert "66 inherited Stage 1 findings" in gates["changed_file_ruff"]
    assert gates["stage2_final_consolidated"].startswith(
        "passed with two jplephem prerequisite skips"
    )
    assert receipt["blockers"]
    assert len(receipt["catalog_authority_diagnostics"]) == 9


def test_stage2_receipt_records_disjoint_fixture_roles() -> None:
    receipt = _load(RECEIPT_PATH)
    fixture = _load(FIXTURE_PATH)
    roles = [record["fixture_role"] for record in fixture["records"]]

    assert fixture["fixture_role"] == "disjoint_calibration_and_holdout"
    assert receipt["authority_fixture"]["calibration_records"] == roles.count(
        "calibration"
    )
    assert receipt["authority_fixture"]["holdout_records"] == roles.count("holdout")
    assert set(roles) == {"calibration", "holdout"}
