#!/usr/bin/env python3
"""Execute the Jones/MYSTIC sealed 550 nm holdouts against frozen thresholds.

This research tool is outside Moira's installed runtime. It verifies the
committed pilot and threshold receipts, accepts only caller-supplied locked
external inputs, and writes generated numerical evidence outside the repo.
It never downloads data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THRESHOLD_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_admission_thresholds.json"
)
DEFAULT_THRESHOLD_CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_threshold_checkpoint_2026-07-31.json"
)
VALIDATOR_PATH = (
    REPO_ROOT / "scripts" / "validate_visibility_phase4_jones_mystic_holdouts.py"
)

ARTIFACT_SCHEMA = "moira.visibility-phase4-jones-mystic-holdout-artifact/v2"
CHECKPOINT_SCHEMA = "moira.visibility-phase4-jones-mystic-holdout-checkpoint/v2"
CASE_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-case/v2"
MANIFEST_NAME = "holdout-manifest.json"
CHECKPOINT_NAME = "holdout-checkpoint.json"
HOLDOUT_STATUS_PASSED = (
    "corrected_v2_sealed_holdout_gate_passed_not_runtime_data_pack"
)
HOLDOUT_STATUS_FAILED = (
    "corrected_v2_sealed_holdout_gate_failed_not_runtime_data_pack"
)


class JonesMysticHoldoutError(ValueError):
    """Raised when the sealed-holdout contract or execution is invalid."""


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


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JonesMysticHoldoutError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesMysticHoldoutError(f"{label} must be a JSON object")
    return payload


def _safe_repo_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise JonesMysticHoldoutError(f"{label} must be a repository path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise JonesMysticHoldoutError(f"{label} escapes the repository")
    return REPO_ROOT.joinpath(*path.parts)


def _verify_repo_receipt(receipt: Any, label: str) -> Path:
    if not isinstance(receipt, dict):
        raise JonesMysticHoldoutError(f"{label} receipt is missing")
    path = _safe_repo_path(receipt.get("path"), f"{label}.path")
    if (
        not path.is_file()
        or not isinstance(receipt.get("bytes"), int)
        or receipt["bytes"] <= 0
        or not isinstance(receipt.get("sha256"), str)
        or len(receipt["sha256"]) != 64
        or path.stat().st_size != receipt["bytes"]
        or sha256_file(path) != receipt["sha256"]
    ):
        raise JonesMysticHoldoutError(f"{label} receipt differs: {path}")
    return path


def _load_module(path: Path, name: str) -> Any:
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise JonesMysticHoldoutError(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def load_contracts(
    *,
    threshold_path: Path = DEFAULT_THRESHOLD_PATH,
    threshold_checkpoint_path: Path = DEFAULT_THRESHOLD_CHECKPOINT_PATH,
) -> dict[str, Any]:
    threshold_checkpoint = _read_json(
        threshold_checkpoint_path, "frozen-threshold checkpoint"
    )
    if (
        threshold_checkpoint.get("schema")
        != "moira.visibility-phase4-jones-mystic-threshold-checkpoint/v2"
        or threshold_checkpoint.get("status")
        != "corrected_v2_pilot_passes_threshold_gate_holdouts_not_executed"
        or threshold_checkpoint.get("all_frozen_thresholds_passed") is not True
        or threshold_checkpoint.get("failed_checks") != []
        or threshold_checkpoint.get("holdouts_used_to_select_thresholds") is not False
        or threshold_checkpoint.get("sealed_holdouts_executed") is not False
        or threshold_checkpoint.get("sealed_holdout_execution_allowed") is not True
        or threshold_checkpoint.get("production_admission_allowed") is not False
        or threshold_checkpoint.get("runtime_model_admitted") is not False
    ):
        raise JonesMysticHoldoutError("frozen-threshold checkpoint is not admissible")

    bound_threshold_path = _verify_repo_receipt(
        threshold_checkpoint.get("threshold_spec"), "threshold specification"
    )
    if bound_threshold_path.resolve() != threshold_path.resolve():
        raise JonesMysticHoldoutError("threshold path differs from checkpoint")
    threshold_auditor_path = _verify_repo_receipt(
        threshold_checkpoint.get("threshold_auditor"), "threshold auditor"
    )
    threshold_auditor = _load_module(
        threshold_auditor_path, "_moira_phase4_threshold_auditor_for_holdouts"
    )
    threshold_spec = threshold_auditor.load_threshold_spec(bound_threshold_path)
    if threshold_checkpoint.get("correction_history") != threshold_spec.get(
        "correction_history"
    ):
        raise JonesMysticHoldoutError("threshold correction lineage differs")

    pilot_checkpoint_path = _verify_repo_receipt(
        threshold_spec.get("pilot_checkpoint"), "pilot checkpoint"
    )
    if threshold_checkpoint.get("pilot_checkpoint") != threshold_spec.get(
        "pilot_checkpoint"
    ):
        raise JonesMysticHoldoutError("pilot checkpoint lineage differs")
    pilot_checkpoint = _read_json(pilot_checkpoint_path, "pilot checkpoint")
    if (
        pilot_checkpoint.get("schema")
        != "moira.visibility-phase4-jones-mystic-pilot-checkpoint/v2"
        or pilot_checkpoint.get("status")
        != "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
        or pilot_checkpoint.get("executed_case_count") != 15
        or pilot_checkpoint.get("reserved_holdout_case_count") != 3
        or pilot_checkpoint.get("fixed_seed_repeat_passed") is not True
        or pilot_checkpoint.get("production_admission_allowed") is not False
        or pilot_checkpoint.get("runtime_dependency") is not False
    ):
        raise JonesMysticHoldoutError("pilot checkpoint lineage is invalid")

    pilot_tooling = pilot_checkpoint.get("tooling")
    if not isinstance(pilot_tooling, dict):
        raise JonesMysticHoldoutError("pilot tooling receipts are missing")
    pilot_spec_path = _verify_repo_receipt(
        pilot_tooling.get("spec"), "pilot specification"
    )
    pilot_builder_path = _verify_repo_receipt(
        pilot_tooling.get("builder"), "pilot builder"
    )
    _verify_repo_receipt(pilot_tooling.get("validator"), "pilot validator")
    pilot_builder = _load_module(
        pilot_builder_path, "_moira_phase4_pilot_builder_for_holdouts"
    )
    pilot_spec = pilot_builder.load_spec(pilot_spec_path)
    if pilot_checkpoint.get("correction_history") != pilot_spec.get(
        "correction_history"
    ) or pilot_checkpoint.get("aerosol_explicit_profile_layout") != pilot_spec.get(
        "aerosol", {}
    ).get("explicit_profile_layout"):
        raise JonesMysticHoldoutError("pilot correction lineage is invalid")

    protocol = threshold_spec.get("sealed_holdout_protocol")
    if (
        not isinstance(protocol, dict)
        or protocol.get("source")
        != "reserved_holdout_cases_in_phase4_jones_mystic_pilot_spec"
        or protocol.get("holdouts_used_to_select_thresholds") is not False
        or protocol.get("photon_count_per_case") != 1_000_000
        or protocol.get("random_seed") != 271_828_183
        or protocol.get("exact_repeat_case_id") != "holdout_v2_interior_cross_axis"
        or protocol.get("maximum_relative_standard_error_per_holdout") != 0.005
        or protocol.get("all_directional_outputs_must_be_finite_and_positive")
        is not True
        or protocol.get("absolute_radiance_expectations_prefrozen") is not False
        or protocol.get("source_owned_comparison_used_as_holdout") is not False
    ):
        raise JonesMysticHoldoutError("sealed-holdout protocol differs")

    return {
        "threshold_spec": threshold_spec,
        "threshold_checkpoint": threshold_checkpoint,
        "threshold_path": bound_threshold_path,
        "threshold_checkpoint_path": threshold_checkpoint_path,
        "pilot_checkpoint": pilot_checkpoint,
        "pilot_checkpoint_path": pilot_checkpoint_path,
        "pilot_spec": pilot_spec,
        "pilot_spec_path": pilot_spec_path,
        "pilot_builder": pilot_builder,
    }


def holdout_cases(contracts: dict[str, Any]) -> list[dict[str, Any]]:
    spec = contracts["pilot_spec"]
    builder = contracts["pilot_builder"]
    protocol = contracts["threshold_spec"]["sealed_holdout_protocol"]
    cases = []
    for reserved in spec["reserved_holdout_cases"]:
        case = {
            **reserved,
            "class": "sealed_holdout",
            "target_moon_separation_deg": builder.target_moon_separation_deg(
                float(reserved["target_true_altitude_deg"]),
                float(reserved["moon_true_altitude_deg"]),
                float(reserved["relative_moon_azimuth_deg"]),
            ),
            "photon_count": protocol["photon_count_per_case"],
            "random_seed": protocol["random_seed"],
        }
        builder.validate_case(case, runnable=True)
        cases.append(case)

    repeat_id = protocol["exact_repeat_case_id"]
    anchor = next(case for case in cases if case["case_id"] == repeat_id)
    repeat = {
        **anchor,
        "case_id": f"{repeat_id}_repeat",
        "repeat_of": repeat_id,
    }
    builder.validate_case(repeat, runnable=True)
    cases.append(repeat)
    return cases


def inspect_contract(
    *,
    threshold_path: Path = DEFAULT_THRESHOLD_PATH,
    threshold_checkpoint_path: Path = DEFAULT_THRESHOLD_CHECKPOINT_PATH,
) -> dict[str, Any]:
    contracts = load_contracts(
        threshold_path=threshold_path,
        threshold_checkpoint_path=threshold_checkpoint_path,
    )
    cases = holdout_cases(contracts)
    protocol = contracts["threshold_spec"]["sealed_holdout_protocol"]
    return {
        "status": "corrected_v2_sealed_holdout_execution_authorized_not_yet_executed",
        "pilot_model_id": contracts["pilot_spec"]["pilot_model_id"],
        "sealed_holdout_count": 3,
        "executed_case_count_with_repeat": len(cases),
        "photon_count_per_case": protocol["photon_count_per_case"],
        "random_seed": protocol["random_seed"],
        "holdouts_used_to_select_thresholds": False,
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_dependency": False,
    }


def _source_and_generator(
    contracts: dict[str, Any],
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
) -> dict[str, Any]:
    builder = contracts["pilot_builder"]
    spec = contracts["pilot_spec"]
    generator_lock = spec["external_generators"]["libRadtran"]
    lib_receipt = builder._verify_external_file(
        lib_radtran_archive,
        expected_bytes=generator_lock["archive_bytes"],
        expected_sha256=generator_lock["archive_sha256"],
        label="libRadtran source archive",
    )
    uvspec_receipt = builder._verify_uvspec(uvspec, spec)
    data_receipt = builder.tree_receipt(data_root)
    if data_receipt != generator_lock["data_root_receipt"]:
        raise JonesMysticHoldoutError("libRadtran data-root receipt differs")
    payloads, member_receipts = builder._read_eso_members(eso_archive, spec)
    by_role = {
        receipt["role"]: payloads[receipt["path"]]
        for receipt in spec["external_source"]["required_members"]
    }
    solar = builder.parse_solar_irradiance_550(
        by_role["top_of_atmosphere_solar_spectrum"]
    )
    rolo_constants, rolo_table = builder.parse_rolo(
        by_role["rolo_disk_equivalent_lunar_reflectance"]
    )
    rolo_coefficients = builder._linear_interpolate_rows(rolo_table, 550.0)
    aod550 = builder.parse_aod550(by_role["paranal_aerosol_extinction"])
    _angles, phase_values = builder.parse_phase_function_550(
        by_role["source_owned_aerosol_phase_function"]
    )
    lunar = spec["lunar_source"]
    if not math.isclose(
        solar,
        lunar["solar_irradiance_550nm_W_m-2_micrometre-1"],
        rel_tol=0.0,
        abs_tol=lunar["source_interpolation_absolute_tolerance"],
    ):
        raise JonesMysticHoldoutError("550 nm solar derivation differs")
    if rolo_coefficients != lunar["rolo_interpolated_coefficients_550nm"]:
        raise JonesMysticHoldoutError("550 nm ROLO derivation differs")
    if not math.isclose(aod550, spec["aerosol"]["aod550"], abs_tol=1e-15):
        raise JonesMysticHoldoutError("550 nm aerosol derivation differs")

    source_inputs = {
        "solar_irradiance": solar,
        "rolo_constants": rolo_constants,
        "rolo_coefficients": rolo_coefficients,
        "correction_divisor": lunar["rolo_correction_divisor"],
        "moon_solid_angle_sr": lunar["moon_solid_angle_sr"],
    }
    return {
        "generator": {
            "libRadtran_source_archive": lib_receipt,
            "uvspec": uvspec_receipt,
            "data_root": data_receipt,
        },
        "external_source": {
            "archive": file_receipt(eso_archive),
            "members": member_receipts,
            "redistributed": False,
        },
        "source_inputs": source_inputs,
        "source_derivations": {
            "solar_irradiance_550nm_W_m-2_micrometre-1": solar,
            "rolo_constant_coefficients": rolo_constants,
            "rolo_interpolated_coefficients_550nm": rolo_coefficients,
            "aod550": aod550,
        },
        "phase_values": phase_values,
    }


def _diagnostics(
    root: Path,
    cases: list[dict[str, Any]],
    protocol: dict[str, Any],
    scientific_repeat_files: tuple[str, ...],
) -> dict[str, Any]:
    anchor_id = protocol["exact_repeat_case_id"]
    repeat_id = f"{anchor_id}_repeat"
    repeat_files = {
        name: (
            (root / "runs" / anchor_id / name).read_bytes()
            == (root / "runs" / repeat_id / name).read_bytes()
        )
        for name in scientific_repeat_files
    }
    unique_cases = [case for case in cases if case["case_id"] != repeat_id]
    measurements = [
        {
            "case_id": case["case_id"],
            "directional_radiance_W_m-2_nm-1_sr-1": case["derived"][
                "directional_radiance_W_m-2_nm-1_sr-1"
            ],
            "directional_standard_error_W_m-2_nm-1_sr-1": case["derived"][
                "directional_standard_error_W_m-2_nm-1_sr-1"
            ],
            "relative_monte_carlo_standard_error": case["derived"][
                "relative_monte_carlo_standard_error"
            ],
        }
        for case in unique_cases
    ]
    maximum_relative_error = max(
        row["relative_monte_carlo_standard_error"] for row in measurements
    )
    checks = {
        "all_directional_outputs_finite_positive": all(
            math.isfinite(row["directional_radiance_W_m-2_nm-1_sr-1"])
            and row["directional_radiance_W_m-2_nm-1_sr-1"] > 0.0
            and math.isfinite(row["directional_standard_error_W_m-2_nm-1_sr-1"])
            and row["directional_standard_error_W_m-2_nm-1_sr-1"] > 0.0
            for row in measurements
        ),
        "maximum_relative_standard_error_per_holdout": maximum_relative_error
        <= protocol["maximum_relative_standard_error_per_holdout"],
        "exact_fixed_seed_repeat": all(repeat_files.values()),
    }
    return {
        "measurements": measurements,
        "maximum_relative_standard_error": maximum_relative_error,
        "maximum_allowed_relative_standard_error": protocol[
            "maximum_relative_standard_error_per_holdout"
        ],
        "fixed_seed_repeat": {
            "anchor_case_id": anchor_id,
            "repeat_case_id": repeat_id,
            "byte_identical_files": repeat_files,
            "passed": all(repeat_files.values()),
        },
        "checks": checks,
        "all_frozen_holdout_checks_passed": all(checks.values()),
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
    }


def _tooling_receipts(contracts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "holdout_builder": file_receipt(
            Path(__file__).resolve(), relative_to=REPO_ROOT
        ),
        "holdout_validator": file_receipt(VALIDATOR_PATH, relative_to=REPO_ROOT),
        "pilot_builder": contracts["pilot_checkpoint"]["tooling"]["builder"],
        "pilot_validator": contracts["pilot_checkpoint"]["tooling"]["validator"],
    }


def build_holdouts(
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
    output_root: Path,
    threshold_path: Path = DEFAULT_THRESHOLD_PATH,
    threshold_checkpoint_path: Path = DEFAULT_THRESHOLD_CHECKPOINT_PATH,
) -> dict[str, Any]:
    if os.name != "posix":
        raise JonesMysticHoldoutError(
            "Jones/MYSTIC holdouts must run in the POSIX libRadtran lab"
        )
    contracts = load_contracts(
        threshold_path=threshold_path,
        threshold_checkpoint_path=threshold_checkpoint_path,
    )
    if output_root.exists():
        raise JonesMysticHoldoutError(f"output root already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    if not VALIDATOR_PATH.is_file():
        raise JonesMysticHoldoutError(f"holdout validator is missing: {VALIDATOR_PATH}")

    source = _source_and_generator(
        contracts,
        uvspec=uvspec,
        lib_radtran_archive=lib_radtran_archive,
        data_root=data_root,
        eso_archive=eso_archive,
    )
    cases = holdout_cases(contracts)
    builder = contracts["pilot_builder"]
    spec = contracts["pilot_spec"]
    protocol = contracts["threshold_spec"]["sealed_holdout_protocol"]
    temporary_path = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    try:
        shared_inputs = builder.construct_shared_inputs(
            temporary_path,
            spec=spec,
            data_root=data_root,
            phase_values=source["phase_values"],
        )
        results = []
        for case in cases:
            print(f"running {case['case_id']} (1000000 photons)", flush=True)
            results.append(
                builder.run_case(
                    case,
                    root=temporary_path,
                    uvspec=uvspec,
                    data_root=data_root,
                    spec=spec,
                    source_inputs=source["source_inputs"],
                )
            )
        diagnostics = _diagnostics(
            temporary_path,
            results,
            protocol,
            builder.SCIENTIFIC_REPEAT_FILES,
        )
        passed = diagnostics["all_frozen_holdout_checks_passed"]
        manifest = {
            "schema": ARTIFACT_SCHEMA,
            "status": HOLDOUT_STATUS_PASSED if passed else HOLDOUT_STATUS_FAILED,
            "candidate_model_id": contracts["threshold_spec"]["candidate_model_id"],
            "pilot_model_id": spec["pilot_model_id"],
            "correction_history": {
                "pilot": spec["correction_history"],
                "threshold": contracts["threshold_spec"]["correction_history"],
            },
            "wavelength_nm": spec["solver"]["wavelength_nm"],
            "threshold_contract": {
                "spec": file_receipt(
                    contracts["threshold_path"], relative_to=REPO_ROOT
                ),
                "checkpoint": file_receipt(
                    contracts["threshold_checkpoint_path"], relative_to=REPO_ROOT
                ),
            },
            "pilot_contract": {
                "spec": contracts["pilot_checkpoint"]["tooling"]["spec"],
                "checkpoint": contracts["threshold_spec"]["pilot_checkpoint"],
            },
            "tooling": _tooling_receipts(contracts),
            "generator": source["generator"],
            "external_source": source["external_source"],
            "source_derivations": source["source_derivations"],
            "shared_inputs": shared_inputs,
            "aerosol_explicit_profile_layout": shared_inputs["aerosol"][
                "explicit_profile_layout"
            ],
            "cases": results,
            "diagnostics": diagnostics,
            "environment": {
                "platform": platform.platform(),
                "python": sys.version,
                "execution_order": "serial",
            },
            "thresholds_frozen_before_execution": True,
            "holdouts_used_to_select_thresholds": False,
            "sealed_holdout_count": 3,
            "executed_case_count_with_repeat": len(results),
            "absolute_radiance_expectations_prefrozen": False,
            "spectral_grid_admitted": False,
            "production_admission_allowed": False,
            "runtime_model_admitted": False,
            "runtime_dependency": False,
            "network_dependency": False,
            "external_source_bytes_redistributed": False,
        }
        manifest_path = temporary_path / MANIFEST_NAME
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        checkpoint = {
            "schema": CHECKPOINT_SCHEMA,
            "status": (
                "corrected_v2_sealed_holdouts_pass_frozen_thresholds"
                if passed
                else "corrected_v2_sealed_holdouts_fail_frozen_thresholds"
            ),
            "pilot_model_id": spec["pilot_model_id"],
            "correction_history": manifest["correction_history"],
            "aerosol_explicit_profile_layout": manifest[
                "aerosol_explicit_profile_layout"
            ],
            "artifact_manifest": file_receipt(manifest_path),
            "threshold_contract": manifest["threshold_contract"],
            "tooling": manifest["tooling"],
            "generator": manifest["generator"],
            "sealed_holdout_count": 3,
            "executed_case_count_with_repeat": len(results),
            "measurements": diagnostics["measurements"],
            "maximum_relative_standard_error": diagnostics[
                "maximum_relative_standard_error"
            ],
            "maximum_allowed_relative_standard_error": diagnostics[
                "maximum_allowed_relative_standard_error"
            ],
            "fixed_seed_repeat": diagnostics["fixed_seed_repeat"],
            "checks": diagnostics["checks"],
            "all_frozen_holdout_checks_passed": passed,
            "failed_checks": diagnostics["failed_checks"],
            "thresholds_frozen_before_execution": True,
            "holdouts_used_to_select_thresholds": False,
            "absolute_radiance_expectations_prefrozen": False,
            "spectral_grid_admitted": False,
            "production_admission_allowed": False,
            "runtime_model_admitted": False,
            "runtime_dependency": False,
            "network_dependency": False,
            "external_source_bytes_redistributed": False,
            "next_gate": (
                "resolve_lower_boundary_on_corrected_v2_then_design_spectral_admission"
                if passed
                else "stop_and_investigate_sealed_holdout_failure"
            ),
        }
        (temporary_path / CHECKPOINT_NAME).write_bytes(canonical_json_bytes(checkpoint))
        temporary_path.replace(output_root)
        return checkpoint
    except BaseException:
        shutil.rmtree(temporary_path, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--lib-radtran-archive", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--eso-archive", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLD_PATH)
    parser.add_argument(
        "--threshold-checkpoint",
        type=Path,
        default=DEFAULT_THRESHOLD_CHECKPOINT_PATH,
    )
    parser.add_argument(
        "--inspect-contract",
        action="store_true",
        help="verify and print the sealed contract without running MYSTIC",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.inspect_contract:
            print(
                json.dumps(
                    inspect_contract(
                        threshold_path=args.thresholds,
                        threshold_checkpoint_path=args.threshold_checkpoint,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        checkpoint = build_holdouts(
            uvspec=args.uvspec,
            lib_radtran_archive=args.lib_radtran_archive,
            data_root=args.data_root,
            eso_archive=args.eso_archive,
            output_root=args.output_root,
            threshold_path=args.thresholds,
            threshold_checkpoint_path=args.threshold_checkpoint,
        )
    except (JonesMysticHoldoutError, OSError) as exc:
        print(f"Jones/MYSTIC sealed holdout failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(checkpoint, indent=2, sort_keys=True))
    return 0 if checkpoint["all_frozen_holdout_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
