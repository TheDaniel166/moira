from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts import build_visibility_phase4_jones_mystic_holdouts as holdouts


REPO_ROOT = Path(__file__).resolve().parents[2]
THRESHOLD_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_admission_thresholds.json"
)
THRESHOLD_CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_threshold_checkpoint_2026-07-31.json"
)
HOLDOUT_CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_holdout_checkpoint_2026-07-31.json"
)


def _receipt(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_holdout_contract_is_authorized_but_not_admitted() -> None:
    assert holdouts.inspect_contract() == {
        "status": "sealed_holdout_execution_authorized_not_yet_executed",
        "pilot_model_id": "jones_paranal_mystic_550nm_pilot_v1",
        "sealed_holdout_count": 3,
        "executed_case_count_with_repeat": 4,
        "photon_count_per_case": 1_000_000,
        "random_seed": 135_791_357,
        "holdouts_used_to_select_thresholds": False,
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_dependency": False,
    }


def test_execution_matrix_is_derived_only_from_reserved_holdouts() -> None:
    contracts = holdouts.load_contracts()
    cases = holdouts.holdout_cases(contracts)
    reserved = contracts["pilot_spec"]["reserved_holdout_cases"]
    reserved_ids = {case["case_id"] for case in reserved}
    assert {case["case_id"] for case in cases[:-1]} == reserved_ids
    assert cases[-1]["case_id"] == "holdout_interior_combination_repeat"
    assert cases[-1]["repeat_of"] == "holdout_interior_combination"
    assert all(case["class"] == "sealed_holdout" for case in cases)
    assert all(case["photon_count"] == 1_000_000 for case in cases)
    assert all(case["random_seed"] == 135_791_357 for case in cases)
    for case in cases:
        calculated = contracts["pilot_builder"].target_moon_separation_deg(
            case["target_true_altitude_deg"],
            case["moon_true_altitude_deg"],
            case["relative_moon_azimuth_deg"],
        )
        assert math.isclose(
            case["target_moon_separation_deg"], calculated, abs_tol=1e-12
        )


def test_frozen_contract_has_no_absolute_radiance_expectation() -> None:
    contracts = holdouts.load_contracts()
    protocol = contracts["threshold_spec"]["sealed_holdout_protocol"]
    assert protocol["holdouts_used_to_select_thresholds"] is False
    assert protocol["absolute_radiance_expectations_prefrozen"] is False
    assert protocol["source_owned_comparison_used_as_holdout"] is False
    assert protocol["maximum_relative_standard_error_per_holdout"] == 0.005


def test_committed_holdout_checkpoint_binds_exact_tooling_and_results() -> None:
    checkpoint = json.loads(HOLDOUT_CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert HOLDOUT_CHECKPOINT_PATH.read_bytes() == holdouts.canonical_json_bytes(
        checkpoint
    )
    assert checkpoint["schema"] == holdouts.CHECKPOINT_SCHEMA
    assert checkpoint["status"] == "sealed_holdouts_pass_frozen_thresholds"
    assert checkpoint["threshold_contract"] == {
        "spec": _receipt(THRESHOLD_PATH),
        "checkpoint": _receipt(THRESHOLD_CHECKPOINT_PATH),
    }
    assert checkpoint["tooling"]["holdout_builder"] == _receipt(Path(holdouts.__file__))
    validator_path = (
        REPO_ROOT / "scripts" / "validate_visibility_phase4_jones_mystic_holdouts.py"
    )
    assert checkpoint["tooling"]["holdout_validator"] == _receipt(validator_path)
    assert checkpoint["sealed_holdout_count"] == 3
    assert checkpoint["executed_case_count_with_repeat"] == 4
    assert (
        checkpoint["maximum_relative_standard_error"]
        <= checkpoint["maximum_allowed_relative_standard_error"]
    )
    assert checkpoint["fixed_seed_repeat"]["passed"] is True
    assert all(checkpoint["fixed_seed_repeat"]["byte_identical_files"].values())
    assert all(checkpoint["checks"].values())
    assert checkpoint["all_frozen_holdout_checks_passed"] is True
    assert checkpoint["failed_checks"] == []
    assert checkpoint["thresholds_frozen_before_execution"] is True
    assert checkpoint["holdouts_used_to_select_thresholds"] is False
    assert checkpoint["absolute_radiance_expectations_prefrozen"] is False
    assert checkpoint["spectral_grid_admitted"] is False
    assert checkpoint["production_admission_allowed"] is False
    assert checkpoint["runtime_model_admitted"] is False
    assert checkpoint["runtime_dependency"] is False


def test_execution_rejects_a_checkpoint_that_claims_holdouts_ran(
    tmp_path: Path,
) -> None:
    checkpoint = json.loads(THRESHOLD_CHECKPOINT_PATH.read_text(encoding="utf-8"))
    checkpoint["sealed_holdouts_executed"] = True
    mutated = tmp_path / "mutated-threshold-checkpoint.json"
    mutated.write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(
        holdouts.JonesMysticHoldoutError,
        match="frozen-threshold checkpoint is not admissible",
    ):
        holdouts.load_contracts(
            threshold_path=THRESHOLD_PATH,
            threshold_checkpoint_path=mutated,
        )


def test_execution_rejects_a_threshold_path_outside_the_checkpoint(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "copied-thresholds.json"
    copied.write_bytes(THRESHOLD_PATH.read_bytes())
    with pytest.raises(
        holdouts.JonesMysticHoldoutError,
        match="threshold path differs from checkpoint",
    ):
        holdouts.load_contracts(threshold_path=copied)
