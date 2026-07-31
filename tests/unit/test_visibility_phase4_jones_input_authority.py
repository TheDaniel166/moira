from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_visibility_phase4_jones_inputs import (
    JonesInputAuthorityError,
    audit_inputs,
    inspect_spec,
    load_spec,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_input_authority_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_input_authority_checkpoint_2026-07-31.json"
)


def test_input_authority_spec_is_bounded_and_nonruntime() -> None:
    assert inspect_spec(SPEC_PATH) == {
        "spec_id": (
            "physical-heliacal-phase4-jones-input-authority-2026-07-31"
        ),
        "status": "input_authority_audit_not_runtime_model",
        "candidate_model_id": (
            "jones_paranal_scattered_moonlight_2013_v1"
        ),
        "solar_authority_status": (
            "independently_reconstructable_in_candidate_domain"
        ),
        "lunar_authority_status": (
            "independently_reconstructable_with_empirical_phase_domain"
        ),
        "aerosol_authority_status": (
            "source_owned_checksum_locked_not_reconstructable"
        ),
        "input_authority_gate_closed": True,
        "pilot_may_proceed": True,
        "production_admission_allowed": False,
        "runtime_dependency": False,
    }


def test_committed_checkpoint_binds_auditor_and_spec() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert checkpoint["status"] == (
        "input_authority_audit_complete_runtime_model_not_admitted"
    )
    assert checkpoint["runtime_dependency"] is False
    assert checkpoint["network_dependency"] is False
    assert checkpoint["external_source_bytes_redistributed"] is False
    assert checkpoint["eso_source_package"]["redistributed"] is False
    assert checkpoint["eodg_mie_authority"]["executed_by_auditor"] is False
    assert checkpoint["eodg_mie_authority"]["redistributed"] is False
    for receipt_name in ("auditor", "spec"):
        receipt = checkpoint[receipt_name]
        payload = (REPO_ROOT / receipt["path"]).read_bytes()
        assert receipt["bytes"] == len(payload)
        assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()


def test_solar_input_is_independently_bound_in_candidate_domain() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    solar = checkpoint["solar_irradiance"]
    assert solar["authority_status"] == (
        "independently_reconstructable_in_candidate_domain"
    )
    assert solar["eso_rows_compared_to_stis"] == 1467
    assert solar["candidate_domain_row_count"] == 325
    assert solar["candidate_domain_actual_micrometre"] == [
        0.38061,
        0.77921,
    ]
    assert solar["candidate_domain_eso_numeric_sha256"] == (
        "fcdb33a16166f8ee3e9f894371f3d79e"
        "14efddb063753104d547897071be9024"
    )
    assert solar["max_wavelength_delta_micrometre"] <= 5.5e-06
    assert (
        solar["max_absolute_flux_delta_W_m-2_micrometre-1"] <= 0.0005
    )
    assert solar["max_relative_flux_delta"] <= 4.5e-06
    assert solar["stis_reference"]["redistributed"] is False
    assert solar["nmsu_reference"]["redistributed"] is False


def test_rolo_input_is_primary_table_bound_and_phase_limited() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    lunar = checkpoint["lunar_reflectance"]
    assert lunar["authority_status"] == (
        "independently_reconstructable_with_empirical_phase_domain"
    )
    assert lunar["wavelength_row_count"] == 32
    assert lunar["wavelength_domain_nm"] == [350.0, 2383.6]
    assert lunar["table4_numeric_sha256"] == (
        "620b1ca086edda0221a1db7461d696024"
        "79c5c584aa403843084786b5608278e"
    )
    assert lunar["empirical_phase_domain_deg"] == [1.55, 97.0]
    assert lunar["outside_empirical_phase_domain_policy"] == (
        "not_evaluable"
    )


def test_aerosol_source_truth_is_not_reconstruction_truth() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    aerosol = checkpoint["aerosol_phase_function"]
    assert aerosol["authority_status"] == (
        "source_owned_checksum_locked_not_reconstructable"
    )
    assert aerosol["wavelength_count"] == 40
    assert aerosol["angle_count"] == 181
    assert aerosol["half_solid_angle_normalization_at_0_55_micrometre"] == (
        pytest.approx(1.0010108296057996, abs=1e-12)
    )
    assert aerosol["asymmetry_parameter_at_0_55_micrometre"] == (
        pytest.approx(0.680602583549528, abs=1e-12)
    )
    falsification = aerosol["reconstruction_falsification"]
    assert falsification["match"] is False
    assert falsification["invented_transform_allowed"] is False
    assert falsification["calculated_asymmetry_parameter"] == (
        pytest.approx(0.595268389115, abs=1e-12)
    )
    policy = aerosol["pilot_use_policy"]
    assert policy["allowed"] is True
    assert policy["independent_radiative_transfer_claim_allowed"] is True
    assert policy["independent_aerosol_reconstruction_claim_allowed"] is False
    assert policy["bytes_may_be_committed_to_repository"] is False


def test_gate_allows_only_the_external_input_pilot() -> None:
    gate = load_spec(SPEC_PATH)["gate_decision"]
    assert gate["input_authority_gate_closed"] is True
    assert gate["independent_mystic_pilot_may_proceed"] is True
    assert gate["production_admission_allowed"] is False
    assert gate["acceptance_thresholds_may_be_frozen_before_pilot"] is False
    assert gate["aerosol_reconstruction_blocker_is_silently_ignored"] is False
    assert gate[
        "aerosol_reconstruction_blocker_is_misreported_as_model_failure"
    ] is False
    assert gate["next_gate"] == (
        "freeze_and_generate_independent_mystic_pilot_matrix"
    )


def test_validator_rejects_invented_aerosol_transform(tmp_path: Path) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload["aerosol_phase_function"]["reconstruction_falsification"][
        "invented_transform_allowed"
    ] = True
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(
        JonesInputAuthorityError,
        match="aerosol reconstruction disposition differs",
    ):
        load_spec(mutated)


def test_audit_rejects_wrong_eso_archive_before_tar_processing(
    tmp_path: Path,
) -> None:
    wrong = tmp_path / "SM-01.tar.gz"
    wrong.write_bytes(b"not the official archive")
    with pytest.raises(
        JonesInputAuthorityError,
        match="ESO source archive byte count differs",
    ):
        audit_inputs(
            wrong,
            stis_solar_path=tmp_path / "missing-stis.fits",
            nmsu_solar_path=tmp_path / "missing-nmsu.txt",
            eodg_archive_path=tmp_path / "missing-eodg.tar.gz",
            spec_path=SPEC_PATH,
        )
