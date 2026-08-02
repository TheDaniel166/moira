from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts import build_visibility_phase4_jones_mystic_lower_boundary as builder
from scripts import validate_visibility_phase4_jones_mystic_lower_boundary as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_lower_boundary_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_lower_boundary_checkpoint_2026-08-02.json"
)


def _receipt(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_lower_boundary_contract_is_frozen_but_not_admitted() -> None:
    assert builder.inspect_contract() == {
        "status": "lower_boundary_contract_frozen_execution_not_yet_run",
        "experiment_id": (
            "physical-heliacal-phase4-jones-mystic-lower-boundary-2026-08-02"
        ),
        "profile_ids": [
            builder.CONTROL_PROFILE_ID,
            builder.CANDIDATE_PROFILE_ID,
        ],
        "unique_case_count": 3,
        "executed_run_count_with_candidate_repeat": 7,
        "observer_altitude_km": 2.64,
        "candidate_surface_altitude_km": 2.0,
        "runtime_model_admitted": False,
        "production_admission_allowed": False,
        "spectral_grid_admitted": False,
    }


def test_contract_binds_every_corrected_v2_receipt() -> None:
    contracts = builder.load_contracts()
    spec = contracts["spec"]
    for role, path in contracts["lineage_paths"].items():
        assert spec["lineage"][role] == _receipt(path)
    assert contracts["pilot_checkpoint"]["fixed_seed_repeat_passed"] is True
    assert (
        contracts["threshold_checkpoint"]["all_frozen_thresholds_passed"]
        is True
    )
    assert (
        contracts["holdout_checkpoint"]["all_frozen_holdout_checks_passed"]
        is True
    )
    assert contracts["threshold_checkpoint"]["runtime_model_admitted"] is False
    assert contracts["holdout_checkpoint"]["runtime_model_admitted"] is False


def test_execution_matrix_reuses_only_the_three_reserved_holdouts() -> None:
    contracts = builder.load_contracts()
    cases = builder.experiment_cases(contracts)
    protocol = contracts["spec"]["execution_protocol"]
    control = cases[builder.CONTROL_PROFILE_ID]
    candidate = cases[builder.CANDIDATE_PROFILE_ID]
    assert [case["case_id"] for case in control] == protocol["case_ids"]
    assert [case["case_id"] for case in candidate[:-1]] == protocol["case_ids"]
    assert candidate[-1]["case_id"] == (
        "holdout_v2_interior_cross_axis_candidate_repeat"
    )
    assert candidate[-1]["repeat_of"] == "holdout_v2_interior_cross_axis"
    assert all(case["photon_count"] == 1_000_000 for case in control + candidate)
    assert all(case["random_seed"] == 271_828_183 for case in control + candidate)
    assert all(
        case["class"] == "lower_boundary_reserved_holdout_reuse"
        for case in control + candidate
    )


def test_candidate_pressure_and_aerosol_columns_close_exactly() -> None:
    candidate = builder.load_spec()["profiles"][builder.CANDIDATE_PROFILE_ID]
    pressure = candidate["target_observer_pressure_hpa"] * (
        candidate["source_surface_pressure_hpa"]
        / candidate["source_observer_pressure_hpa"]
    )
    assert pressure == pytest.approx(candidate["surface_pressure_hpa"], abs=1e-12)
    reference = candidate["aerosol_normalization_reference_km"]
    bottom = candidate["aerosol_profile_bottom_km"]
    top = candidate["aerosol_profile_top_km"]
    scale = candidate["aerosol_scale_height_km"]
    aod = candidate["observer_to_infinite_top_aod550"]
    above = aod * (1.0 - math.exp(-(top - reference) / scale))
    total = aod * (
        math.exp((reference - bottom) / scale)
        - math.exp(-(top - reference) / scale)
    )
    assert above == pytest.approx(candidate["observer_to_20km_aod550"], abs=1e-15)
    assert total == pytest.approx(candidate["surface_to_20km_aod550"], abs=1e-15)
    assert total - above == pytest.approx(
        candidate["below_observer_aod550"], abs=1e-15
    )


def test_candidate_adds_lower_levels_without_moving_v2_boundaries() -> None:
    contracts = builder.load_contracts()
    control, candidate = builder._aerosol_boundaries(contracts["pilot_spec"])
    assert candidate[:4] == [2.0, 2.25, 2.5, 2.64]
    assert candidate[3:] == control
    assert candidate[-1] == 20.0
    assert all(high > low for low, high in zip(candidate, candidate[1:], strict=False))
    assert {"mc0.rad", "mc0.rad.std"} <= builder.expected_run_files(
        contracts, builder.CONTROL_PROFILE_ID
    )
    assert {"mc3.rad", "mc3.rad.std"} <= builder.expected_run_files(
        contracts, builder.CANDIDATE_PROFILE_ID
    )
    assert {"mc0.rad", "mc0.rad.std"}.isdisjoint(
        builder.expected_run_files(contracts, builder.CANDIDATE_PROFILE_ID)
    )


def test_discarded_pre_admission_attempts_are_explicit_and_non_authoritative() -> (
    None
):
    history = builder.load_spec()["pre_admission_execution_history"]
    assert history["successful_artifact_count_before_final_refreeze"] == 2
    assert history["discarded_attempt_count_before_final_refreeze"] == 5
    assert len(history["discarded_attempts"]) == 5
    assert all(
        attempt["artifact_authoritative"] is False
        for attempt in history["discarded_attempts"]
    )


def test_builder_and_validator_independently_render_both_profiles() -> None:
    contracts = builder.load_contracts()
    case = builder.experiment_cases(contracts)[builder.CONTROL_PROFILE_ID][0]
    for profile_id, pressure, ozone, zout in (
        (builder.CONTROL_PROFILE_ID, b"pressure 744\n", b"258", b"zout 0\n"),
        (
            builder.CANDIDATE_PROFILE_ID,
            b"pressure 806.248807263\n",
            b"259.199917818",
            b"zout 0.64\n",
        ),
    ):
        built = builder.render_input(
            case, contracts=contracts, profile_id=profile_id
        )
        independently_rendered = validator._expected_input(
            case,
            validator._load_contracts(SPEC_PATH),
            profile_id,
        )
        assert built == independently_rendered
        assert pressure in built
        assert ozone in built
        assert zout in built
        assert b"aerosol_file explicit ../../shared/aerosol_profile.dat\n" in built
        assert b"\r" not in built


def test_candidate_profile_probe_is_bound_to_observer_above_surface() -> None:
    contracts = builder.load_contracts()
    control = builder.render_profile_probe(contracts, builder.CONTROL_PROFILE_ID)
    candidate = builder.render_profile_probe(contracts, builder.CANDIDATE_PROFILE_ID)
    assert b"pressure 744\n" in control
    assert b"mol_modify O3 258 DU\n" in control
    assert b"zout 0\n" in control
    assert b"pressure 806.248807263\n" in candidate
    assert b"mol_modify O3 259.199917818 DU\n" in candidate
    assert b"zout 0.64\n" in candidate
    assert b"output_user zout_sea p n_o3\n" in candidate


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["runtime_boundary"].__setitem__(
                "runtime_model_admitted", True
            ),
            "runtime boundary is not closed",
        ),
        (
            lambda payload: payload["profiles"][builder.CANDIDATE_PROFILE_ID].__setitem__(
                "surface_pressure_hpa", 795.0
            ),
            "candidate profile differs",
        ),
        (
            lambda payload: payload["execution_protocol"].__setitem__(
                "candidate_control_difference_threshold_prefrozen", True
            ),
            "execution protocol differs",
        ),
    ],
)
def test_builder_rejects_contract_mutations(
    tmp_path: Path, mutation: object, message: str
) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    mutation(payload)  # type: ignore[operator]
    mutated = tmp_path / "mutated-lower-boundary-spec.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(builder.JonesMysticLowerBoundaryError, match=message):
        builder.load_spec(mutated)


def test_validator_does_not_import_the_builder_under_audit() -> None:
    source = Path(validator.__file__).read_text(encoding="utf-8")
    assert "import build_visibility_phase4_jones_mystic_lower_boundary" not in source
    assert "_load_module(BUILDER_PATH" not in source


def test_committed_checkpoint_binds_the_reproducible_lower_boundary_result() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert CHECKPOINT_PATH.read_bytes() == builder.canonical_json_bytes(checkpoint)
    assert hashlib.sha256(CHECKPOINT_PATH.read_bytes()).hexdigest() == (
        "6c3ef3b750ff235719a3b9014e05bb5a5a7f6c022decc2f83a0f4f85f4906b31"
    )
    assert checkpoint["schema"] == builder.CHECKPOINT_SCHEMA
    assert checkpoint["status"] == (
        "source_faithful_lower_boundary_profile_verified_not_runtime_admitted"
    )
    assert checkpoint["artifact_manifest"] == {
        "bytes": 71981,
        "path": "lower-boundary-manifest.json",
        "sha256": (
            "4223b52c001f5f6e427130bdc4523c1031f617e904987c823a3cd18883911736"
        ),
    }
    assert checkpoint["source_faithful_profile_id"] == builder.CANDIDATE_PROFILE_ID
    assert checkpoint["all_lower_boundary_checks_passed"] is True
    assert checkpoint["failed_checks"] == []
    assert all(checkpoint["checks"].values())
    assert checkpoint["candidate_fixed_seed_repeat"]["passed"] is True
    assert all(
        checkpoint["candidate_fixed_seed_repeat"]["byte_identical_files"].values()
    )
    assert checkpoint["maximum_relative_standard_error"] <= checkpoint[
        "maximum_allowed_relative_standard_error"
    ]
    assert checkpoint["tooling"]["spec"] == _receipt(SPEC_PATH)
    assert checkpoint["tooling"]["builder"] == _receipt(Path(builder.__file__))
    assert checkpoint["tooling"]["validator"] == _receipt(Path(validator.__file__))
    assert [row["candidate_relative_change"] for row in checkpoint["measurements"]] == [
        0.05456133257863671,
        0.024387583626620968,
        0.006286620454454939,
    ]
    assert checkpoint["candidate_numerical_difference_used_for_model_selection"] is False
    assert checkpoint["spectral_grid_admitted"] is False
    assert checkpoint["production_admission_allowed"] is False
    assert checkpoint["runtime_model_admitted"] is False
    assert checkpoint["runtime_dependency"] is False
    assert checkpoint["network_dependency"] is False
