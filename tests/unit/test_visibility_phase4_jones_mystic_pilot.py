from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts import build_visibility_phase4_jones_mystic_pilot as builder
from scripts import validate_visibility_phase4_jones_mystic_pilot as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_pilot_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_pilot_checkpoint_2026-07-31.json"
)
INVALIDATION_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_v1_invalidation_checkpoint_2026-07-31.json"
)


def test_pilot_spec_is_bounded_external_and_not_admitted() -> None:
    assert builder.inspect_spec(SPEC_PATH) == {
        "spec_id": "physical-heliacal-phase4-jones-mystic-pilot-v2-2026-07-31",
        "status": "frozen_corrected_external_pilot_matrix_not_runtime_data_pack",
        "pilot_model_id": "jones_paranal_mystic_550nm_pilot_v2",
        "executed_case_count": 15,
        "reserved_holdout_case_count": 3,
        "wavelength_nm": 550.0,
        "acceptance_thresholds_status": "pilot_results_required_before_freeze",
        "production_admission_allowed": False,
        "runtime_dependency": False,
    }


def test_committed_checkpoint_binds_exact_generator_and_tooling() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert checkpoint["status"] == (
        "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
    )
    assert checkpoint["artifact_manifest"] == {
        "bytes": 41237,
        "path": "artifact-manifest.json",
        "sha256": "f3a139617abe43ffc1098a6b2df5e90dc10a48a32b1219316a772e6d60245aa7",
    }
    assert checkpoint["executed_case_count"] == 15
    assert checkpoint["reserved_holdout_case_count"] == 3
    assert checkpoint["fixed_seed_repeat_passed"] is True
    assert checkpoint["acceptance_thresholds_frozen"] is False
    assert checkpoint["production_admission_allowed"] is False
    assert checkpoint["runtime_dependency"] is False
    assert checkpoint["external_source"]["redistributed"] is False
    for receipt in checkpoint["tooling"].values():
        payload = (REPO_ROOT / receipt["path"]).read_bytes()
        assert receipt["bytes"] == len(payload)
        assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()


def test_v1_invalidation_is_immutable_and_bound_by_v2() -> None:
    invalidation = json.loads(INVALIDATION_PATH.read_text(encoding="utf-8"))
    assert INVALIDATION_PATH.read_bytes() == builder.canonical_json_bytes(invalidation)
    assert invalidation["status"] == (
        "v1_pilot_threshold_and_holdout_evidence_invalidated_before_runtime_admission"
    )
    assert invalidation["defect"]["source_rule"] == (
        "an aerosol_file explicit property file defines the layer starting at the "
        "listed altitude; the uppermost line only marks the top and its properties "
        "are ignored"
    )
    assert invalidation["runtime_boundary"] == {
        "engine_or_public_api_affected": False,
        "external_v1_artifacts_remain_reproducible": True,
        "external_v1_artifacts_valid_for_scientific_admission": False,
        "production_data_pack_affected": False,
        "runtime_model_affected": False,
    }
    receipt = {
        "path": INVALIDATION_PATH.relative_to(REPO_ROOT).as_posix(),
        "bytes": INVALIDATION_PATH.stat().st_size,
        "sha256": hashlib.sha256(INVALIDATION_PATH.read_bytes()).hexdigest(),
    }
    spec = builder.load_spec(SPEC_PATH)
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert spec["correction_history"]["invalidation_checkpoint"] == receipt
    assert checkpoint["correction_history"]["invalidation_checkpoint"] == receipt


def test_pilot_matrix_covers_six_axes_and_keeps_holdouts_sealed() -> None:
    spec = builder.load_spec(SPEC_PATH)
    cases = spec["pilot_cases"]
    case_ids = {case["case_id"] for case in cases}
    holdout_ids = {case["case_id"] for case in spec["reserved_holdout_cases"]}
    assert case_ids.isdisjoint(holdout_ids)
    assert {case["target_true_altitude_deg"] for case in cases} >= {5.0, 60.0}
    assert {case["moon_true_altitude_deg"] for case in cases} >= {5.0, 45.0}
    assert {case["relative_moon_azimuth_deg"] for case in cases} >= {
        0.0,
        108.53218095317945,
        180.0,
    }
    assert {case["lunar_phase_angle_deg"] for case in cases} >= {1.55, 50.0, 97.0}
    assert {case["waxing_state"] for case in cases} == {"waxing", "waning"}
    assert {case["moon_earth_distance_ratio"] for case in cases} >= {
        0.91,
        1.0,
        1.08,
    }
    assert {case["photon_count"] for case in cases} == {100000, 300000, 1000000}
    assert {case["random_seed"] for case in cases} == {
        49979687,
        67867967,
        86028121,
    }


def test_every_declared_separation_is_geometrically_consistent() -> None:
    for case in builder.load_spec(SPEC_PATH)["pilot_cases"]:
        calculated = builder.target_moon_separation_deg(
            case["target_true_altitude_deg"],
            case["moon_true_altitude_deg"],
            case["relative_moon_azimuth_deg"],
        )
        assert calculated == pytest.approx(
            case["target_moon_separation_deg"], abs=1e-12
        )


def test_lunar_source_formula_preserves_phase_side_and_inverse_square_distance() -> (
    None
):
    spec = builder.load_spec(SPEC_PATH)
    lunar = spec["lunar_source"]
    base = spec["pilot_cases"][0]
    kwargs = {
        "solar_irradiance": lunar["solar_irradiance_550nm_W_m-2_micrometre-1"],
        "rolo_constants": lunar["rolo_constant_coefficients"],
        "rolo_coefficients": lunar["rolo_interpolated_coefficients_550nm"],
        "correction_divisor": lunar["rolo_correction_divisor"],
        "moon_solid_angle_sr": lunar["moon_solid_angle_sr"],
    }
    base_result = builder.lunar_source_flux_550(base, **kwargs)
    assert base_result["toa_lunar_irradiance_W_m-2_nm-1"] == pytest.approx(
        lunar["base_case_flux_550nm_W_m-2_nm-1"], abs=5e-21
    )
    waning = {**base, "waxing_state": "waning"}
    waning_result = builder.lunar_source_flux_550(waning, **kwargs)
    assert (
        waning_result["toa_lunar_irradiance_W_m-2_nm-1"]
        < base_result["toa_lunar_irradiance_W_m-2_nm-1"]
    )
    near = {**base, "moon_earth_distance_ratio": 0.91}
    far = {**base, "moon_earth_distance_ratio": 1.08}
    near_flux = builder.lunar_source_flux_550(near, **kwargs)[
        "toa_lunar_irradiance_W_m-2_nm-1"
    ]
    far_flux = builder.lunar_source_flux_550(far, **kwargs)[
        "toa_lunar_irradiance_W_m-2_nm-1"
    ]
    assert near_flux / far_flux == pytest.approx((1.08 / 0.91) ** 2, rel=1e-15)


def test_standard_library_legendre_projection_preserves_isotropic_phase() -> None:
    moments, diagnostics = builder.compute_legendre_moments(
        [1.0] * 181,
        moment_count=16,
        quadrature_order=64,
    )
    assert moments[0] == 1.0
    assert max(abs(value) for value in moments[1:]) < 2e-15
    assert diagnostics["raw_k0"] == pytest.approx(1.0, abs=2e-15)
    assert diagnostics["max_absolute_table_angle_reconstruction_error"] < 2e-12


def test_explicit_aerosol_profile_binds_files_to_lower_boundaries() -> None:
    layers = [
        {
            "low_km": 2.0,
            "high_km": 2.25,
            "filename": "aerosol_layer_000.dat",
        },
        {
            "low_km": 2.25,
            "high_km": 2.5,
            "filename": "aerosol_layer_001.dat",
        },
    ]
    assert builder.render_explicit_aerosol_profile(
        layers,
        profile_top_km=2.5,
        null_top_boundary_km=120.0,
    ) == (
        b"120.00000000 ../../shared/null_layer.dat\n"
        b"2.50000000 ../../shared/null_layer.dat\n"
        b"2.25000000 ../../shared/aerosol_layer_001.dat\n"
        b"2.00000000 ../../shared/aerosol_layer_000.dat\n"
    )


def test_builder_and_validator_independently_render_same_mystic_contract() -> None:
    spec = builder.load_spec(SPEC_PATH)
    case = spec["pilot_cases"][0]
    built = builder.render_input(case, spec)
    independently_rendered = validator._render_input(case, spec)
    assert built == independently_rendered
    assert b"\r" not in built
    assert b"source solar lunar_source.dat per_nm\n" in built
    assert b"mc_spherical 1D\n" in built
    assert b"aerosol_default\n" in built
    assert b"aerosol_file explicit ../../shared/aerosol_profile.dat\n" in built
    assert b"pressure 744\n" in built
    assert b"mol_modify O3 258 DU\n" in built
    assert b"albedo 0.155819\n" in built


def test_spec_rejects_prefrozen_thresholds(tmp_path: Path) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload["pilot_gate"]["acceptance_thresholds_status"] = "accepted"
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        builder.JonesMysticPilotError, match="thresholds were prematurely frozen"
    ):
        builder.load_spec(mutated)


def test_spec_rejects_production_admission(tmp_path: Path) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload["pilot_gate"]["production_admission_allowed"] = True
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        builder.JonesMysticPilotError, match="cannot authorize production admission"
    ):
        builder.load_spec(mutated)


def test_subdomain_phase_is_rejected_before_execution() -> None:
    case = dict(builder.load_spec(SPEC_PATH)["pilot_cases"][0])
    case["lunar_phase_angle_deg"] = math.nextafter(1.55, 0.0)
    with pytest.raises(builder.JonesMysticPilotError, match="lunar_phase_angle_deg"):
        builder.validate_case(case, runnable=True)
