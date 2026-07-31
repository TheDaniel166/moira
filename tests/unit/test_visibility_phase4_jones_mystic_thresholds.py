from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import audit_visibility_phase4_jones_mystic_thresholds as thresholds


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_admission_thresholds.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_threshold_checkpoint_2026-07-31.json"
)


def _receipt(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_threshold_spec_is_frozen_before_holdouts_and_not_admitted() -> None:
    assert thresholds.inspect_thresholds(SPEC_PATH) == {
        "threshold_id": ("physical-heliacal-phase4-jones-mystic-thresholds-2026-07-31"),
        "status": "thresholds_frozen_after_pilot_before_holdout_execution",
        "pilot_model_id": "jones_paranal_mystic_550nm_pilot_v1",
        "holdouts_used_to_select_thresholds": False,
        "sealed_holdout_count": 3,
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_dependency": False,
    }


def test_threshold_checkpoint_binds_current_evaluator_and_freeze() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert CHECKPOINT_PATH.read_bytes() == thresholds.canonical_json_bytes(checkpoint)
    assert checkpoint["schema"] == thresholds.CHECKPOINT_SCHEMA
    assert checkpoint["status"] == (
        "pilot_passes_frozen_threshold_gate_holdouts_not_executed"
    )
    assert checkpoint["threshold_spec"] == _receipt(SPEC_PATH)
    assert checkpoint["threshold_auditor"] == _receipt(Path(thresholds.__file__))
    assert checkpoint["all_frozen_thresholds_passed"] is True
    assert checkpoint["failed_checks"] == []
    assert all(checkpoint["checks"].values())
    assert checkpoint["holdouts_used_to_select_thresholds"] is False
    assert checkpoint["sealed_holdouts_executed"] is False
    assert checkpoint["sealed_holdout_execution_allowed"] is True
    assert checkpoint["spectral_grid_admitted"] is False
    assert checkpoint["production_admission_allowed"] is False
    assert checkpoint["runtime_model_admitted"] is False
    assert checkpoint["runtime_dependency"] is False
    assert checkpoint["external_source_bytes_redistributed"] is False


def test_checkpoint_measurements_remain_inside_frozen_thresholds() -> None:
    spec = thresholds.load_threshold_spec(SPEC_PATH)
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    observed = checkpoint["observed"]
    monte_carlo = spec["thresholds"]["monte_carlo"]
    aerosol = spec["thresholds"]["aerosol_representation"]

    assert (
        observed["maximum_relative_standard_error_all_pilot_cases"]
        <= (monte_carlo["maximum_relative_standard_error_all_pilot_cases"])
    )
    assert (
        observed["relative_standard_error_base_1m"]
        <= (monte_carlo["maximum_relative_standard_error_base_1m"])
    )
    assert (
        observed["standard_error_sqrt_photon_scaled_max_to_min_ratio"]
        <= (monte_carlo["maximum_standard_error_sqrt_photon_scaled_max_to_min_ratio"])
    )
    assert (
        observed["multiseed_sample_relative_standard_deviation"]
        <= (monte_carlo["maximum_300k_multiseed_sample_relative_standard_deviation"])
    )
    assert (
        observed["multiseed_sample_rsd_to_mean_reported_relative_error_ratio"]
        <= monte_carlo[
            "maximum_multiseed_sample_rsd_to_mean_reported_relative_error_ratio"
        ]
    )
    assert (
        observed["aerosol_representation"][
            "max_absolute_table_angle_reconstruction_error"
        ]
        <= aerosol["maximum_absolute_table_angle_reconstruction_error"]
    )
    assert (
        observed["aerosol_representation"][
            "max_relative_table_angle_reconstruction_error"
        ]
        <= aerosol["maximum_relative_table_angle_reconstruction_error"]
    )
    assert (
        abs(observed["aerosol_representation"]["raw_k0"] - 1.0)
        <= aerosol["maximum_absolute_raw_k0_minus_one"]
    )
    assert (
        observed["unrepresented_aod_fraction_above_profile_top"]
        <= aerosol["maximum_unrepresented_aod_fraction_above_profile_top"]
    )


def test_threshold_spec_rejects_holdout_leakage(tmp_path: Path) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload["sealed_holdout_protocol"]["holdouts_used_to_select_thresholds"] = True
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        thresholds.JonesMysticThresholdError, match="sealed holdout protocol changed"
    ):
        thresholds.load_threshold_spec(mutated)


def test_threshold_spec_rejects_operational_capture_as_oracle(
    tmp_path: Path,
) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload["thresholds"]["source_owned_operational_comparison"][
        "independent_oracle_claimed"
    ] = True
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        thresholds.JonesMysticThresholdError,
        match="operational capture was promoted to an oracle",
    ):
        thresholds.load_threshold_spec(mutated)
