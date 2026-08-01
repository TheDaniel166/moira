#!/usr/bin/env python3
"""Evaluate the Jones/MYSTIC pilot against thresholds frozen before holdouts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THRESHOLD_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_admission_thresholds.json"
)
THRESHOLD_SCHEMA = "moira.visibility-phase4-jones-mystic-admission-thresholds/v2"
CHECKPOINT_SCHEMA = "moira.visibility-phase4-jones-mystic-threshold-checkpoint/v2"
ARTIFACT_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-artifact/v2"
PILOT_CHECKPOINT_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-checkpoint/v2"


class JonesMysticThresholdError(ValueError):
    """Raised when a threshold declaration or pilot evaluation is invalid."""


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_receipt(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    label = path.relative_to(relative_to).as_posix() if relative_to else path.name
    return {
        "path": label,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _safe_repo_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise JonesMysticThresholdError(f"{label} must be a repository path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise JonesMysticThresholdError(f"{label} escapes the repository")
    return REPO_ROOT.joinpath(*path.parts)


def _verify_repo_file(
    *, path_value: Any, bytes_value: Any, sha_value: Any, label: str
) -> Path:
    path = _safe_repo_path(path_value, f"{label}.path")
    if (
        not isinstance(bytes_value, int)
        or bytes_value <= 0
        or not isinstance(sha_value, str)
        or len(sha_value) != 64
        or not path.is_file()
        or path.stat().st_size != bytes_value
        or sha256_file(path) != sha_value
    ):
        raise JonesMysticThresholdError(f"{label} receipt differs: {path}")
    return path


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JonesMysticThresholdError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesMysticThresholdError(f"{label} must be a JSON object")
    return payload


def validate_threshold_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != THRESHOLD_SCHEMA:
        raise JonesMysticThresholdError("unsupported threshold schema")
    if spec.get("status") != (
        "corrected_v2_thresholds_frozen_after_pilot_before_holdout_execution"
    ):
        raise JonesMysticThresholdError("threshold freeze ordering changed")
    correction = spec.get("correction_history")
    if (
        not isinstance(correction, dict)
        or correction.get("supersedes_threshold_id")
        != "physical-heliacal-phase4-jones-mystic-thresholds-2026-07-31"
        or correction.get("reason")
        != "v1_aerosol_layer_boundary_ownership_invalidated"
    ):
        raise JonesMysticThresholdError("threshold correction history is missing")
    invalidation = correction.get("invalidation_checkpoint")
    if not isinstance(invalidation, dict):
        raise JonesMysticThresholdError("v1 invalidation receipt is missing")
    _verify_repo_file(
        path_value=invalidation.get("path"),
        bytes_value=invalidation.get("bytes"),
        sha_value=invalidation.get("sha256"),
        label="v1 invalidation checkpoint",
    )
    boundary = spec.get("runtime_boundary")
    if boundary != {
        "engine_changes_authorized": False,
        "public_api_changes_authorized": False,
        "runtime_table_authorized": False,
        "production_data_pack_authorized": False,
        "spectral_grid_authorized": False,
        "runtime_dependency": False,
        "network_dependency": False,
        "external_source_bytes_redistributed": False,
    }:
        raise JonesMysticThresholdError("threshold runtime boundary was weakened")

    pilot = spec.get("pilot_checkpoint")
    if not isinstance(pilot, dict):
        raise JonesMysticThresholdError("pilot checkpoint receipt is missing")
    _verify_repo_file(
        path_value=pilot.get("path"),
        bytes_value=pilot.get("bytes"),
        sha_value=pilot.get("sha256"),
        label="pilot checkpoint",
    )
    source = spec.get("source_audit")
    if not isinstance(source, dict):
        raise JonesMysticThresholdError("source-audit receipt is missing")
    _verify_repo_file(
        path_value=source.get("spec_path"),
        bytes_value=source.get("spec_bytes"),
        sha_value=source.get("spec_sha256"),
        label="source-audit spec",
    )
    _verify_repo_file(
        path_value=source.get("fits_parser_path"),
        bytes_value=source.get("fits_parser_bytes"),
        sha_value=source.get("fits_parser_sha256"),
        label="source-audit FITS parser",
    )
    capture = source.get("operational_capture")
    if (
        not isinstance(capture, dict)
        or capture.get("comparison_role")
        != "source_owned_operational_comparison_not_independent_oracle"
        or capture.get("component_column") != "flux_sml"
        or capture.get("wavelength_nm") != 550.0
    ):
        raise JonesMysticThresholdError("operational comparison contract changed")

    thresholds = spec.get("thresholds")
    if not isinstance(thresholds, dict):
        raise JonesMysticThresholdError("threshold families are missing")
    expected_numeric = {
        ("monte_carlo", "maximum_relative_standard_error_all_pilot_cases"): 0.0125,
        ("monte_carlo", "maximum_relative_standard_error_base_1m"): 0.004,
        (
            "monte_carlo",
            "maximum_standard_error_sqrt_photon_scaled_max_to_min_ratio",
        ): 1.05,
        (
            "monte_carlo",
            "maximum_300k_multiseed_sample_relative_standard_deviation",
        ): 0.01,
        (
            "monte_carlo",
            "maximum_multiseed_sample_rsd_to_mean_reported_relative_error_ratio",
        ): 1.0,
        (
            "aerosol_representation",
            "maximum_absolute_table_angle_reconstruction_error",
        ): 0.25,
        (
            "aerosol_representation",
            "maximum_relative_table_angle_reconstruction_error",
        ): 0.01,
        ("aerosol_representation", "maximum_absolute_raw_k0_minus_one"): 0.001,
        (
            "aerosol_representation",
            "maximum_unrepresented_aod_fraction_above_profile_top",
        ): 1e-6,
        (
            "lunar_source_linearity",
            "maximum_radiance_to_source_ratio_max_to_min",
        ): 1.00001,
        (
            "source_owned_operational_comparison",
            "maximum_absolute_magnitude_difference",
        ): 0.15,
    }
    for (family, key), expected in expected_numeric.items():
        if thresholds.get(family, {}).get(key) != expected:
            raise JonesMysticThresholdError(f"frozen threshold differs: {family}.{key}")
    if (
        thresholds["source_owned_operational_comparison"].get(
            "independent_oracle_claimed"
        )
        is not False
    ):
        raise JonesMysticThresholdError("operational capture was promoted to an oracle")

    holdouts = spec.get("sealed_holdout_protocol")
    if (
        not isinstance(holdouts, dict)
        or holdouts.get("holdouts_used_to_select_thresholds") is not False
        or holdouts.get("photon_count_per_case") != 1_000_000
        or holdouts.get("random_seed") != 271_828_183
        or holdouts.get("exact_repeat_case_id")
        != "holdout_v2_interior_cross_axis"
        or holdouts.get("maximum_relative_standard_error_per_holdout") != 0.005
        or holdouts.get("absolute_radiance_expectations_prefrozen") is not False
    ):
        raise JonesMysticThresholdError("sealed holdout protocol changed")
    gate = spec.get("gate")
    if (
        not isinstance(gate, dict)
        or gate.get("spectral_grid_admitted") is not False
        or gate.get("production_admission_allowed") is not False
        or gate.get("runtime_model_admitted") is not False
        or gate.get("next_gate")
        != "execute_replacement_v2_sealed_holdouts_against_frozen_thresholds"
    ):
        raise JonesMysticThresholdError("threshold gate state changed")


def load_threshold_spec(path: Path = DEFAULT_THRESHOLD_PATH) -> dict[str, Any]:
    spec = _load_json(path, "threshold specification")
    validate_threshold_spec(spec)
    return spec


def inspect_thresholds(path: Path = DEFAULT_THRESHOLD_PATH) -> dict[str, Any]:
    spec = load_threshold_spec(path)
    return {
        "threshold_id": spec["threshold_id"],
        "status": spec["status"],
        "pilot_model_id": spec["pilot_model_id"],
        "holdouts_used_to_select_thresholds": spec["sealed_holdout_protocol"][
            "holdouts_used_to_select_thresholds"
        ],
        "sealed_holdout_count": 3,
        "spectral_grid_admitted": spec["gate"]["spectral_grid_admitted"],
        "production_admission_allowed": spec["gate"]["production_admission_allowed"],
        "runtime_dependency": False,
    }


def _load_fits_parser(spec: dict[str, Any]) -> Any:
    source = spec["source_audit"]
    path = _safe_repo_path(source["fits_parser_path"], "fits parser path")
    module_spec = importlib.util.spec_from_file_location(
        "_moira_phase4_source_audit_for_thresholds", path
    )
    if module_spec is None or module_spec.loader is None:
        raise JonesMysticThresholdError("cannot load bound FITS parser")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _skycalc_radiance(
    path: Path,
    spec: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    capture = spec["source_audit"]["operational_capture"]
    if (
        not path.is_file()
        or path.stat().st_size != capture["bytes"]
        or sha256_file(path) != capture["sha256"]
    ):
        raise JonesMysticThresholdError("SkyCalc operational capture receipt differs")
    parser = _load_fits_parser(spec)
    _header, _comments, table = parser._fits_binary_table(path.read_bytes())
    wavelengths = table.get("lam")
    component = table.get(capture["component_column"])
    if not isinstance(wavelengths, tuple) or not isinstance(component, tuple):
        raise JonesMysticThresholdError("SkyCalc component columns are missing")
    matches = [
        index
        for index, wavelength in enumerate(wavelengths)
        if math.isclose(
            wavelength,
            capture["wavelength_nm"],
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ]
    if len(matches) != 1:
        raise JonesMysticThresholdError("SkyCalc capture lacks one exact 550 nm row")
    index = matches[0]
    photon_radiance = component[index]
    if not math.isfinite(photon_radiance) or photon_radiance <= 0.0:
        raise JonesMysticThresholdError("SkyCalc 550 nm component is not positive")
    wavelength_m = capture["wavelength_nm"] * 1e-9
    photon_energy_joule = 6.62607015e-34 * 299792458.0 / wavelength_m
    square_arcseconds_per_steradian = (180.0 / math.pi * 3600.0) ** 2
    radiance = (
        photon_radiance * photon_energy_joule / 1000.0 * square_arcseconds_per_steradian
    )
    return radiance, {
        "capture": file_receipt(path),
        "wavelength_nm": capture["wavelength_nm"],
        "flux_sml_photon_s-1_m-2_micrometre-1_arcsec-2": photon_radiance,
        "converted_radiance_W_m-2_nm-1_sr-1": radiance,
        "conversion": (
            "photon_energy_hc_over_lambda_times_square_arcseconds_per_"
            "steradian_divided_by_1000_nm_per_micrometre"
        ),
        "comparison_role": capture["comparison_role"],
    }


def _load_bound_manifest(
    artifact_root: Path,
    threshold_spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pilot_path = _safe_repo_path(
        threshold_spec["pilot_checkpoint"]["path"], "pilot checkpoint"
    )
    checkpoint = _load_json(pilot_path, "pilot checkpoint")
    manifest_receipt = checkpoint.get("artifact_manifest")
    if not isinstance(manifest_receipt, dict):
        raise JonesMysticThresholdError("pilot checkpoint omits artifact manifest")
    manifest_path = artifact_root / manifest_receipt.get("path", "")
    if (
        not artifact_root.is_dir()
        or not manifest_path.is_file()
        or manifest_path.stat().st_size != manifest_receipt.get("bytes")
        or sha256_file(manifest_path) != manifest_receipt.get("sha256")
    ):
        raise JonesMysticThresholdError("artifact manifest differs from the pilot lock")
    manifest = _load_json(manifest_path, "pilot artifact manifest")
    pilot_correction = checkpoint.get("correction_history")
    if (
        checkpoint.get("schema") != PILOT_CHECKPOINT_SCHEMA
        or checkpoint.get("status")
        != "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
        or not isinstance(pilot_correction, dict)
        or pilot_correction.get("reason")
        != "correct_libradtran_explicit_aerosol_layer_boundary_ownership"
        or pilot_correction.get("invalidation_checkpoint")
        != threshold_spec["correction_history"]["invalidation_checkpoint"]
        or checkpoint.get("aerosol_explicit_profile_layout")
        != "top_marker_then_null_gap_then_layer_files_at_lower_boundaries"
        or manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("pilot_model_id") != threshold_spec["pilot_model_id"]
        or manifest.get("correction_history") != pilot_correction
        or manifest.get("acceptance_thresholds_frozen") is not False
        or manifest.get("production_admission_allowed") is not False
        or manifest.get("runtime_dependency") is not False
    ):
        raise JonesMysticThresholdError("pilot artifact boundary differs")
    return checkpoint, manifest


def evaluate_thresholds(
    *,
    artifact_root: Path,
    skycalc_capture: Path,
    threshold_path: Path = DEFAULT_THRESHOLD_PATH,
) -> dict[str, Any]:
    spec = load_threshold_spec(threshold_path)
    pilot_checkpoint, manifest = _load_bound_manifest(artifact_root, spec)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 15:
        raise JonesMysticThresholdError("pilot artifact case count differs")
    by_id = {case.get("case_id"): case for case in cases if isinstance(case, dict)}
    if len(by_id) != 15:
        raise JonesMysticThresholdError("pilot artifact case identities differ")
    thresholds = spec["thresholds"]

    repeat = pilot_checkpoint["diagnostics"]["fixed_seed_repeat"]
    required_repeat_files = thresholds["fixed_seed_repeat"][
        "required_byte_identical_files"
    ]
    repeat_passed = repeat.get("passed") is True and all(
        repeat.get("byte_identical_files", {}).get(name) is True
        for name in required_repeat_files
    )

    relative_errors = [
        case["derived"]["relative_monte_carlo_standard_error"] for case in cases
    ]
    if any(not math.isfinite(value) or value <= 0.0 for value in relative_errors):
        raise JonesMysticThresholdError("pilot relative errors are invalid")
    radiances = [
        case["derived"]["directional_radiance_W_m-2_nm-1_sr-1"] for case in cases
    ]
    if any(not math.isfinite(value) or value <= 0.0 for value in radiances):
        raise JonesMysticThresholdError("pilot directional radiances are invalid")
    monte = thresholds["monte_carlo"]
    maximum_relative_error = max(relative_errors)
    base_1m_error = by_id["base_p1m_s49979687"]["derived"][
        "relative_monte_carlo_standard_error"
    ]
    convergence = pilot_checkpoint["diagnostics"]["photon_count_convergence"][
        "standard_error_sqrt_photon_scaled_max_to_min_ratio"
    ]
    multiseed = pilot_checkpoint["diagnostics"]["multi_seed_spread"]
    sample_rsd = multiseed["radiance_sample_relative_standard_deviation"]
    mean_reported_relative_error = (
        multiseed["mean_reported_standard_error_W_m-2_nm-1_sr-1"]
        / multiseed["radiance_mean_W_m-2_nm-1_sr-1"]
    )
    sample_to_reported = sample_rsd / mean_reported_relative_error

    aerosol_thresholds = thresholds["aerosol_representation"]
    representation = pilot_checkpoint["aerosol_representation"]
    aod550 = manifest["source_derivations"]["aod550"]
    integrated_aod = pilot_checkpoint["aerosol_integrated_aod_to_profile_top"]
    unrepresented_aod_fraction = (aod550 - integrated_aod) / aod550

    linearity_ids = thresholds["lunar_source_linearity"]["case_ids"]
    source_ratios = {
        case_id: (
            by_id[case_id]["derived"]["directional_radiance_W_m-2_nm-1_sr-1"]
            / by_id[case_id]["derived"]["toa_lunar_irradiance_W_m-2_nm-1"]
        )
        for case_id in linearity_ids
    }
    linearity_ratio = max(source_ratios.values()) / min(source_ratios.values())

    skycalc_radiance, skycalc_receipt = _skycalc_radiance(skycalc_capture, spec)
    comparison_case_id = thresholds["source_owned_operational_comparison"][
        "mystic_case_id"
    ]
    mystic_radiance = by_id[comparison_case_id]["derived"][
        "directional_radiance_W_m-2_nm-1_sr-1"
    ]
    mystic_to_skycalc_ratio = mystic_radiance / skycalc_radiance
    magnitude_difference = -2.5 * math.log10(mystic_to_skycalc_ratio)

    checks = {
        "fixed_seed_repeat": repeat_passed,
        "all_directional_outputs_finite_positive": all(
            value > 0.0 for value in radiances
        ),
        "maximum_relative_standard_error_all_pilot_cases": maximum_relative_error
        <= monte["maximum_relative_standard_error_all_pilot_cases"],
        "maximum_relative_standard_error_base_1m": base_1m_error
        <= monte["maximum_relative_standard_error_base_1m"],
        "standard_error_sqrt_photon_scaling": convergence
        <= monte["maximum_standard_error_sqrt_photon_scaled_max_to_min_ratio"],
        "multiseed_sample_relative_standard_deviation": sample_rsd
        <= monte["maximum_300k_multiseed_sample_relative_standard_deviation"],
        "multiseed_sample_to_reported_error_ratio": sample_to_reported
        <= monte["maximum_multiseed_sample_rsd_to_mean_reported_relative_error_ratio"],
        "aerosol_absolute_reconstruction_error": representation[
            "max_absolute_table_angle_reconstruction_error"
        ]
        <= aerosol_thresholds["maximum_absolute_table_angle_reconstruction_error"],
        "aerosol_relative_reconstruction_error": representation[
            "max_relative_table_angle_reconstruction_error"
        ]
        <= aerosol_thresholds["maximum_relative_table_angle_reconstruction_error"],
        "aerosol_raw_k0": abs(representation["raw_k0"] - 1.0)
        <= aerosol_thresholds["maximum_absolute_raw_k0_minus_one"],
        "aerosol_unrepresented_column": unrepresented_aod_fraction
        <= aerosol_thresholds["maximum_unrepresented_aod_fraction_above_profile_top"],
        "lunar_source_linearity": linearity_ratio
        <= thresholds["lunar_source_linearity"][
            "maximum_radiance_to_source_ratio_max_to_min"
        ],
        "source_owned_operational_comparison": abs(magnitude_difference)
        <= thresholds["source_owned_operational_comparison"][
            "maximum_absolute_magnitude_difference"
        ],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "schema": CHECKPOINT_SCHEMA,
        "threshold_id": spec["threshold_id"],
        "status": "corrected_v2_pilot_passes_threshold_gate_holdouts_not_executed",
        "pilot_model_id": spec["pilot_model_id"],
        "correction_history": spec["correction_history"],
        "threshold_spec": file_receipt(threshold_path, relative_to=REPO_ROOT),
        "threshold_auditor": file_receipt(
            Path(__file__).resolve(), relative_to=REPO_ROOT
        ),
        "pilot_checkpoint": spec["pilot_checkpoint"],
        "artifact_manifest": pilot_checkpoint["artifact_manifest"],
        "skycalc_operational_comparison": {
            **skycalc_receipt,
            "mystic_case_id": comparison_case_id,
            "mystic_radiance_W_m-2_nm-1_sr-1": mystic_radiance,
            "mystic_to_skycalc_radiance_ratio": mystic_to_skycalc_ratio,
            "signed_magnitude_difference": magnitude_difference,
            "absolute_magnitude_difference": abs(magnitude_difference),
            "maximum_absolute_magnitude_difference": thresholds[
                "source_owned_operational_comparison"
            ]["maximum_absolute_magnitude_difference"],
            "independent_oracle_claimed": False,
        },
        "observed": {
            "maximum_relative_standard_error_all_pilot_cases": maximum_relative_error,
            "relative_standard_error_base_1m": base_1m_error,
            "standard_error_sqrt_photon_scaled_max_to_min_ratio": convergence,
            "multiseed_sample_relative_standard_deviation": sample_rsd,
            "multiseed_mean_reported_relative_error": mean_reported_relative_error,
            "multiseed_sample_rsd_to_mean_reported_relative_error_ratio": sample_to_reported,
            "aerosol_representation": representation,
            "unrepresented_aod_fraction_above_profile_top": unrepresented_aod_fraction,
            "lunar_source_radiance_ratios": source_ratios,
            "lunar_source_ratio_max_to_min": linearity_ratio,
        },
        "checks": checks,
        "all_frozen_thresholds_passed": not failed,
        "failed_checks": failed,
        "holdouts_used_to_select_thresholds": False,
        "sealed_holdouts_executed": False,
        "sealed_holdout_execution_allowed": not failed,
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_model_admitted": False,
        "runtime_dependency": False,
        "network_dependency": False,
        "external_source_bytes_redistributed": False,
        "next_gate": "execute_replacement_v2_sealed_holdouts_against_frozen_thresholds",
    }
    if failed:
        raise JonesMysticThresholdError(
            f"pilot failed frozen threshold checks: {', '.join(failed)}"
        )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("--skycalc-capture", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLD_PATH)
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="validate and print the frozen threshold declaration only",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.inspect:
            print(
                json.dumps(
                    inspect_thresholds(args.thresholds), indent=2, sort_keys=True
                )
            )
            return 0
        result = evaluate_thresholds(
            artifact_root=args.artifact_root,
            skycalc_capture=args.skycalc_capture,
            threshold_path=args.thresholds,
        )
    except (JonesMysticThresholdError, OSError) as exc:
        print(f"Jones/MYSTIC threshold evaluation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
