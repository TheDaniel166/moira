#!/usr/bin/env python3
"""Independently validate the Jones/MYSTIC sealed 550 nm holdout artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
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
DEFAULT_THRESHOLD_CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_threshold_checkpoint_2026-07-31.json"
)
HOLDOUT_BUILDER_PATH = (
    REPO_ROOT / "scripts" / "build_visibility_phase4_jones_mystic_holdouts.py"
)

ARTIFACT_SCHEMA = "moira.visibility-phase4-jones-mystic-holdout-artifact/v2"
CHECKPOINT_SCHEMA = "moira.visibility-phase4-jones-mystic-holdout-checkpoint/v2"
CASE_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-case/v2"
MANIFEST_NAME = "holdout-manifest.json"
CHECKPOINT_NAME = "holdout-checkpoint.json"
EXPECTED_RUN_FILES = frozenset(
    {
        "input.inp",
        "lunar_source.dat",
        "mc.flx.spc",
        "mc.flx.std.spc",
        "mc.rad.spc",
        "mc.rad.std.spc",
        "mc0.rad",
        "mc0.rad.std",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    }
)
SCIENTIFIC_REPEAT_FILES = (
    "mc.rad.spc",
    "mc.rad.std.spc",
    "mc0.rad",
    "mc0.rad.std",
    "randomseed",
)


class JonesMysticHoldoutValidationError(ValueError):
    """Raised when sealed-holdout evidence violates its frozen contract."""


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
        raise JonesMysticHoldoutValidationError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesMysticHoldoutValidationError(f"{label} must be a JSON object")
    return payload


def _safe_relative(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise JonesMysticHoldoutValidationError(f"{label} path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise JonesMysticHoldoutValidationError(f"{label} path escapes its root")
    return path


def _verify_receipt(root: Path, receipt: Any, label: str) -> Path:
    if not isinstance(receipt, dict):
        raise JonesMysticHoldoutValidationError(f"{label} receipt is missing")
    relative = _safe_relative(receipt.get("path"), label)
    path = root.joinpath(*relative.parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise JonesMysticHoldoutValidationError(
            f"{label} receipt escapes its root"
        ) from exc
    if (
        not path.is_file()
        or path.is_symlink()
        or not isinstance(receipt.get("bytes"), int)
        or receipt["bytes"] < 0
        or not isinstance(receipt.get("sha256"), str)
        or len(receipt["sha256"]) != 64
        or path.stat().st_size != receipt["bytes"]
        or sha256_file(path) != receipt["sha256"]
    ):
        raise JonesMysticHoldoutValidationError(f"{label} receipt differs: {path}")
    return path


def _verify_repo_receipt(receipt: Any, label: str) -> Path:
    return _verify_receipt(REPO_ROOT, receipt, label)


def _load_module(path: Path, name: str) -> Any:
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise JonesMysticHoldoutValidationError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _require_close(
    actual: Any,
    expected: float,
    label: str,
    *,
    tolerance: float = 1e-15,
) -> None:
    if (
        isinstance(actual, bool)
        or not isinstance(actual, (int, float))
        or not math.isfinite(float(actual))
        or not math.isclose(
            float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance
        )
    ):
        raise JonesMysticHoldoutValidationError(
            f"{label} differs: expected {expected!r}, got {actual!r}"
        )


def _separation(case: dict[str, Any]) -> float:
    target = math.radians(float(case["target_true_altitude_deg"]))
    moon = math.radians(float(case["moon_true_altitude_deg"]))
    azimuth = math.radians(float(case["relative_moon_azimuth_deg"]))
    cosine = math.sin(target) * math.sin(moon) + math.cos(target) * math.cos(
        moon
    ) * math.cos(azimuth)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _load_contracts(
    *,
    threshold_path: Path,
    threshold_checkpoint_path: Path,
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
        raise JonesMysticHoldoutValidationError(
            "frozen-threshold checkpoint is not admissible"
        )
    bound_threshold_path = _verify_repo_receipt(
        threshold_checkpoint.get("threshold_spec"), "threshold specification"
    )
    if bound_threshold_path.resolve() != threshold_path.resolve():
        raise JonesMysticHoldoutValidationError(
            "threshold path differs from checkpoint"
        )
    threshold_auditor_path = _verify_repo_receipt(
        threshold_checkpoint.get("threshold_auditor"), "threshold auditor"
    )
    threshold_auditor = _load_module(
        threshold_auditor_path, "_moira_phase4_threshold_auditor_for_validation"
    )
    threshold_spec = threshold_auditor.load_threshold_spec(bound_threshold_path)
    if threshold_checkpoint.get("correction_history") != threshold_spec.get(
        "correction_history"
    ):
        raise JonesMysticHoldoutValidationError(
            "threshold correction lineage differs"
        )
    pilot_checkpoint_path = _verify_repo_receipt(
        threshold_spec.get("pilot_checkpoint"), "pilot checkpoint"
    )
    if threshold_checkpoint.get("pilot_checkpoint") != threshold_spec.get(
        "pilot_checkpoint"
    ):
        raise JonesMysticHoldoutValidationError("pilot checkpoint lineage differs")
    pilot_checkpoint = _read_json(pilot_checkpoint_path, "pilot checkpoint")
    tooling = pilot_checkpoint.get("tooling")
    if (
        pilot_checkpoint.get("schema")
        != "moira.visibility-phase4-jones-mystic-pilot-checkpoint/v2"
        or pilot_checkpoint.get("status")
        != "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
        or not isinstance(tooling, dict)
    ):
        raise JonesMysticHoldoutValidationError("pilot checkpoint lineage is invalid")
    pilot_spec_path = _verify_repo_receipt(tooling.get("spec"), "pilot specification")
    _verify_repo_receipt(tooling.get("builder"), "pilot builder")
    pilot_validator_path = _verify_repo_receipt(
        tooling.get("validator"), "pilot validator"
    )
    pilot_validator = _load_module(
        pilot_validator_path, "_moira_phase4_pilot_validator_for_holdouts"
    )
    pilot_spec = pilot_validator._load_spec(pilot_spec_path)
    if pilot_checkpoint.get("correction_history") != pilot_spec.get(
        "correction_history"
    ) or pilot_checkpoint.get("aerosol_explicit_profile_layout") != pilot_spec.get(
        "aerosol", {}
    ).get("explicit_profile_layout"):
        raise JonesMysticHoldoutValidationError(
            "pilot correction lineage is invalid"
        )
    protocol = threshold_spec.get("sealed_holdout_protocol")
    if (
        not isinstance(protocol, dict)
        or protocol.get("holdouts_used_to_select_thresholds") is not False
        or protocol.get("photon_count_per_case") != 1_000_000
        or protocol.get("random_seed") != 271_828_183
        or protocol.get("exact_repeat_case_id") != "holdout_v2_interior_cross_axis"
        or protocol.get("maximum_relative_standard_error_per_holdout") != 0.005
        or protocol.get("absolute_radiance_expectations_prefrozen") is not False
    ):
        raise JonesMysticHoldoutValidationError("sealed-holdout protocol differs")
    return {
        "threshold_spec": threshold_spec,
        "threshold_checkpoint": threshold_checkpoint,
        "threshold_path": bound_threshold_path,
        "threshold_checkpoint_path": threshold_checkpoint_path,
        "pilot_checkpoint": pilot_checkpoint,
        "pilot_checkpoint_path": pilot_checkpoint_path,
        "pilot_spec": pilot_spec,
        "pilot_spec_path": pilot_spec_path,
        "pilot_validator": pilot_validator,
    }


def _expected_cases(contracts: dict[str, Any]) -> list[dict[str, Any]]:
    protocol = contracts["threshold_spec"]["sealed_holdout_protocol"]
    cases = []
    for reserved in contracts["pilot_spec"]["reserved_holdout_cases"]:
        cases.append(
            {
                **reserved,
                "class": "sealed_holdout",
                "target_moon_separation_deg": _separation(reserved),
                "photon_count": protocol["photon_count_per_case"],
                "random_seed": protocol["random_seed"],
            }
        )
    anchor_id = protocol["exact_repeat_case_id"]
    anchor = next(case for case in cases if case["case_id"] == anchor_id)
    cases.append(
        {
            **anchor,
            "case_id": f"{anchor_id}_repeat",
            "repeat_of": anchor_id,
        }
    )
    return cases


def _verify_tooling(manifest: dict[str, Any], contracts: dict[str, Any]) -> None:
    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict) or set(tooling) != {
        "holdout_builder",
        "holdout_validator",
        "pilot_builder",
        "pilot_validator",
    }:
        raise JonesMysticHoldoutValidationError("holdout tooling shape differs")
    builder_path = _verify_repo_receipt(tooling["holdout_builder"], "holdout builder")
    validator_path = _verify_repo_receipt(
        tooling["holdout_validator"], "holdout validator"
    )
    if builder_path.resolve() != HOLDOUT_BUILDER_PATH.resolve():
        raise JonesMysticHoldoutValidationError("holdout builder path differs")
    if validator_path.resolve() != Path(__file__).resolve():
        raise JonesMysticHoldoutValidationError("holdout validator path differs")
    if (
        tooling["pilot_builder"] != contracts["pilot_checkpoint"]["tooling"]["builder"]
        or tooling["pilot_validator"]
        != contracts["pilot_checkpoint"]["tooling"]["validator"]
    ):
        raise JonesMysticHoldoutValidationError("pilot tooling lineage differs")


def _verify_cases(
    artifact_root: Path,
    manifest: dict[str, Any],
    contracts: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    expected_cases = _expected_cases(contracts)
    expected_by_id = {case["case_id"]: case for case in expected_cases}
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise JonesMysticHoldoutValidationError("holdout case count differs")
    actual_by_id = {
        case.get("case_id"): case for case in cases if isinstance(case, dict)
    }
    if set(actual_by_id) != set(expected_by_id):
        raise JonesMysticHoldoutValidationError("holdout case identities differ")
    runs_root = artifact_root / "runs"
    if (
        not runs_root.is_dir()
        or runs_root.is_symlink()
        or {path.name for path in runs_root.iterdir() if path.is_dir()}
        != set(expected_by_id)
    ):
        raise JonesMysticHoldoutValidationError("holdout run inventory differs")

    validator = contracts["pilot_validator"]
    spec = contracts["pilot_spec"]
    checked = []
    for expected_case in expected_cases:
        case_id = expected_case["case_id"]
        result = actual_by_id[case_id]
        if result.get("case") != expected_case:
            raise JonesMysticHoldoutValidationError(
                f"holdout case matrix drift: {case_id}"
            )
        case_path = _verify_receipt(
            artifact_root, result.get("case_manifest"), f"case manifest {case_id}"
        )
        case_manifest = _read_json(case_path, f"case manifest {case_id}")
        if (
            case_manifest.get("schema") != CASE_SCHEMA
            or case_manifest.get("case") != expected_case
        ):
            raise JonesMysticHoldoutValidationError(
                f"holdout case contract differs: {case_id}"
            )
        run_dir = case_path.parent
        receipts = case_manifest.get("files")
        if not isinstance(receipts, list):
            raise JonesMysticHoldoutValidationError(
                f"case file receipts are missing: {case_id}"
            )
        names = set()
        for index, receipt in enumerate(receipts):
            path = _verify_receipt(
                artifact_root, receipt, f"{case_id} file receipt {index}"
            )
            if path.parent != run_dir or path.name in names:
                raise JonesMysticHoldoutValidationError(
                    f"case file inventory is noncanonical: {case_id}"
                )
            names.add(path.name)
        if names != EXPECTED_RUN_FILES:
            raise JonesMysticHoldoutValidationError(
                f"case file inventory differs: {case_id}"
            )
        if {path.name for path in run_dir.iterdir() if path.is_file()} != (
            EXPECTED_RUN_FILES | {"case.json"}
        ) or any(path.is_symlink() for path in run_dir.iterdir()):
            raise JonesMysticHoldoutValidationError(
                f"case directory contains undeclared entries: {case_id}"
            )

        lunar = validator._lunar_source(expected_case, source, spec)
        lunar_rows = [
            [float(token) for token in line.split()]
            for line in (run_dir / "lunar_source.dat")
            .read_text(encoding="ascii")
            .splitlines()
            if line
        ]
        if len(lunar_rows) != 3 or any(len(row) != 2 for row in lunar_rows):
            raise JonesMysticHoldoutValidationError(
                f"lunar-source shape differs: {case_id}"
            )
        for row, wavelength in zip(
            lunar_rows, spec["lunar_source"]["source_file_grid_nm"], strict=True
        ):
            _require_close(row[0], wavelength, f"{case_id} lunar wavelength")
            _require_close(
                row[1],
                lunar["toa_lunar_irradiance_W_m-2_nm-1"],
                f"{case_id} lunar irradiance",
                tolerance=1e-20,
            )
        if (run_dir / "input.inp").read_bytes() != validator._render_input(
            expected_case, spec
        ):
            raise JonesMysticHoldoutValidationError(
                f"libRadtran input differs: {case_id}"
            )
        radiance = validator._parse_directional(run_dir / "mc.rad.spc")
        standard_error = validator._parse_directional(run_dir / "mc.rad.std.spc")
        derived = case_manifest.get("derived")
        if not isinstance(derived, dict) or derived != result.get("derived"):
            raise JonesMysticHoldoutValidationError(
                f"derived receipt differs: {case_id}"
            )
        _require_close(
            derived.get("target_moon_separation_deg"),
            _separation(expected_case),
            f"{case_id} separation",
            tolerance=1e-12,
        )
        _require_close(
            derived.get("disk_equivalent_albedo"),
            lunar["disk_equivalent_albedo"],
            f"{case_id} lunar albedo",
        )
        _require_close(
            derived.get("toa_lunar_irradiance_W_m-2_nm-1"),
            lunar["toa_lunar_irradiance_W_m-2_nm-1"],
            f"{case_id} lunar irradiance derivation",
            tolerance=1e-20,
        )
        _require_close(
            derived.get("directional_radiance_W_m-2_nm-1_sr-1"),
            radiance,
            f"{case_id} radiance",
        )
        _require_close(
            derived.get("directional_standard_error_W_m-2_nm-1_sr-1"),
            standard_error,
            f"{case_id} standard error",
        )
        _require_close(
            derived.get("relative_monte_carlo_standard_error"),
            standard_error / radiance,
            f"{case_id} relative standard error",
        )
        checked.append(result)
    return checked


def _diagnostics(
    artifact_root: Path,
    cases: list[dict[str, Any]],
    contracts: dict[str, Any],
) -> dict[str, Any]:
    protocol = contracts["threshold_spec"]["sealed_holdout_protocol"]
    anchor_id = protocol["exact_repeat_case_id"]
    repeat_id = f"{anchor_id}_repeat"
    repeat_files = {
        name: (
            (artifact_root / "runs" / anchor_id / name).read_bytes()
            == (artifact_root / "runs" / repeat_id / name).read_bytes()
        )
        for name in SCIENTIFIC_REPEAT_FILES
    }
    measurements = []
    for case in cases:
        if case["case_id"] == repeat_id:
            continue
        derived = case["derived"]
        measurements.append(
            {
                "case_id": case["case_id"],
                "directional_radiance_W_m-2_nm-1_sr-1": derived[
                    "directional_radiance_W_m-2_nm-1_sr-1"
                ],
                "directional_standard_error_W_m-2_nm-1_sr-1": derived[
                    "directional_standard_error_W_m-2_nm-1_sr-1"
                ],
                "relative_monte_carlo_standard_error": derived[
                    "relative_monte_carlo_standard_error"
                ],
            }
        )
    maximum = max(row["relative_monte_carlo_standard_error"] for row in measurements)
    allowed = protocol["maximum_relative_standard_error_per_holdout"]
    checks = {
        "all_directional_outputs_finite_positive": all(
            math.isfinite(row["directional_radiance_W_m-2_nm-1_sr-1"])
            and row["directional_radiance_W_m-2_nm-1_sr-1"] > 0.0
            and math.isfinite(row["directional_standard_error_W_m-2_nm-1_sr-1"])
            and row["directional_standard_error_W_m-2_nm-1_sr-1"] > 0.0
            for row in measurements
        ),
        "maximum_relative_standard_error_per_holdout": maximum <= allowed,
        "exact_fixed_seed_repeat": all(repeat_files.values()),
    }
    return {
        "measurements": measurements,
        "maximum_relative_standard_error": maximum,
        "maximum_allowed_relative_standard_error": allowed,
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


def validate_holdouts(
    *,
    artifact_root: Path,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
    threshold_path: Path = DEFAULT_THRESHOLD_PATH,
    threshold_checkpoint_path: Path = DEFAULT_THRESHOLD_CHECKPOINT_PATH,
) -> dict[str, Any]:
    if os.name != "posix":
        raise JonesMysticHoldoutValidationError(
            "Jones/MYSTIC holdouts must be validated in the POSIX lab"
        )
    contracts = _load_contracts(
        threshold_path=threshold_path,
        threshold_checkpoint_path=threshold_checkpoint_path,
    )
    if not artifact_root.is_dir() or artifact_root.is_symlink():
        raise JonesMysticHoldoutValidationError(
            f"holdout artifact root is invalid: {artifact_root}"
        )
    if {path.name for path in artifact_root.iterdir()} != {
        "shared",
        "runs",
        MANIFEST_NAME,
        CHECKPOINT_NAME,
    }:
        raise JonesMysticHoldoutValidationError(
            "holdout artifact top-level inventory differs"
        )
    manifest = _read_json(artifact_root / MANIFEST_NAME, "holdout manifest")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("status")
        != "corrected_v2_sealed_holdout_gate_passed_not_runtime_data_pack"
        or manifest.get("pilot_model_id") != contracts["pilot_spec"]["pilot_model_id"]
        or manifest.get("wavelength_nm") != 550.0
        or manifest.get("thresholds_frozen_before_execution") is not True
        or manifest.get("holdouts_used_to_select_thresholds") is not False
        or manifest.get("sealed_holdout_count") != 3
        or manifest.get("executed_case_count_with_repeat") != 4
        or manifest.get("absolute_radiance_expectations_prefrozen") is not False
    ):
        raise JonesMysticHoldoutValidationError("holdout manifest identity differs")
    for key in (
        "spectral_grid_admitted",
        "production_admission_allowed",
        "runtime_model_admitted",
        "runtime_dependency",
        "network_dependency",
        "external_source_bytes_redistributed",
    ):
        if manifest.get(key) is not False:
            raise JonesMysticHoldoutValidationError(
                f"holdout manifest boundary changed: {key}"
            )
    expected_threshold_contract = {
        "spec": file_receipt(contracts["threshold_path"], relative_to=REPO_ROOT),
        "checkpoint": file_receipt(
            contracts["threshold_checkpoint_path"], relative_to=REPO_ROOT
        ),
    }
    if manifest.get("threshold_contract") != expected_threshold_contract:
        raise JonesMysticHoldoutValidationError("threshold lineage differs")
    if manifest.get("pilot_contract") != {
        "spec": contracts["pilot_checkpoint"]["tooling"]["spec"],
        "checkpoint": contracts["threshold_spec"]["pilot_checkpoint"],
    }:
        raise JonesMysticHoldoutValidationError("pilot lineage differs")
    expected_correction_history = {
        "pilot": contracts["pilot_spec"]["correction_history"],
        "threshold": contracts["threshold_spec"]["correction_history"],
    }
    if manifest.get("correction_history") != expected_correction_history:
        raise JonesMysticHoldoutValidationError("holdout correction lineage differs")
    _verify_tooling(manifest, contracts)

    validator = contracts["pilot_validator"]
    spec = contracts["pilot_spec"]
    validator._verify_generator(
        manifest,
        spec,
        uvspec=uvspec,
        lib_radtran_archive=lib_radtran_archive,
        data_root=data_root,
    )
    payloads = validator._read_eso_archive(eso_archive, spec)
    source = validator._parse_source_members(payloads)
    source_receipt = manifest.get("external_source")
    if (
        not isinstance(source_receipt, dict)
        or source_receipt.get("redistributed") is not False
        or len(source_receipt.get("members", [])) != 8
        or any(
            receipt.get("redistributed") is not False
            for receipt in source_receipt.get("members", [])
        )
    ):
        raise JonesMysticHoldoutValidationError("external-source boundary differs")
    validator._verify_external(
        eso_archive, source_receipt.get("archive"), "ESO archive"
    )
    derivations = manifest.get("source_derivations")
    if not isinstance(derivations, dict):
        raise JonesMysticHoldoutValidationError("source derivations are missing")
    _require_close(
        derivations.get("solar_irradiance_550nm_W_m-2_micrometre-1"),
        source["solar"],
        "solar derivation",
    )
    _require_close(derivations.get("aod550"), source["aod550"], "AOD derivation")
    if (
        derivations.get("rolo_constant_coefficients") != source["rolo_constants"]
        or derivations.get("rolo_interpolated_coefficients_550nm")
        != source["rolo_coefficients"]
    ):
        raise JonesMysticHoldoutValidationError("ROLO derivation differs")
    validator._verify_shared(artifact_root, manifest, spec, source, data_root)
    if manifest.get("aerosol_explicit_profile_layout") != spec["aerosol"].get(
        "explicit_profile_layout"
    ):
        raise JonesMysticHoldoutValidationError(
            "explicit aerosol profile layout differs"
        )
    cases = _verify_cases(artifact_root, manifest, contracts, source)
    diagnostics = _diagnostics(artifact_root, cases, contracts)
    if diagnostics != manifest.get("diagnostics"):
        raise JonesMysticHoldoutValidationError(
            "independent holdout diagnostics differ"
        )
    if not diagnostics["all_frozen_holdout_checks_passed"]:
        raise JonesMysticHoldoutValidationError(
            "sealed holdouts fail the frozen thresholds"
        )

    checkpoint = _read_json(artifact_root / CHECKPOINT_NAME, "holdout checkpoint")
    if (
        checkpoint.get("schema") != CHECKPOINT_SCHEMA
        or checkpoint.get("status")
        != "corrected_v2_sealed_holdouts_pass_frozen_thresholds"
        or checkpoint.get("artifact_manifest")
        != file_receipt(artifact_root / MANIFEST_NAME)
        or checkpoint.get("threshold_contract") != expected_threshold_contract
        or checkpoint.get("tooling") != manifest.get("tooling")
        or checkpoint.get("generator") != manifest.get("generator")
        or checkpoint.get("correction_history") != expected_correction_history
        or checkpoint.get("aerosol_explicit_profile_layout")
        != spec["aerosol"].get("explicit_profile_layout")
        or checkpoint.get("measurements") != diagnostics["measurements"]
        or checkpoint.get("fixed_seed_repeat") != diagnostics["fixed_seed_repeat"]
        or checkpoint.get("checks") != diagnostics["checks"]
        or checkpoint.get("all_frozen_holdout_checks_passed") is not True
        or checkpoint.get("failed_checks") != []
        or checkpoint.get("next_gate")
        != "resolve_lower_boundary_on_corrected_v2_then_design_spectral_admission"
    ):
        raise JonesMysticHoldoutValidationError("holdout checkpoint differs")
    for key in (
        "holdouts_used_to_select_thresholds",
        "absolute_radiance_expectations_prefrozen",
        "spectral_grid_admitted",
        "production_admission_allowed",
        "runtime_model_admitted",
        "runtime_dependency",
        "network_dependency",
        "external_source_bytes_redistributed",
    ):
        if checkpoint.get(key) is not False:
            raise JonesMysticHoldoutValidationError(
                f"holdout checkpoint boundary changed: {key}"
            )
    return {
        "status": "valid_corrected_v2_holdout_evidence",
        "pilot_model_id": spec["pilot_model_id"],
        "sealed_holdout_count": 3,
        "executed_case_count_with_repeat": 4,
        "maximum_relative_standard_error": diagnostics[
            "maximum_relative_standard_error"
        ],
        "maximum_allowed_relative_standard_error": diagnostics[
            "maximum_allowed_relative_standard_error"
        ],
        "fixed_seed_repeat_passed": True,
        "thresholds_frozen_before_execution": True,
        "holdouts_used_to_select_thresholds": False,
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_dependency": False,
        "next_gate": (
            "resolve_lower_boundary_on_corrected_v2_then_design_spectral_admission"
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--lib-radtran-archive", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--eso-archive", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLD_PATH)
    parser.add_argument(
        "--threshold-checkpoint",
        type=Path,
        default=DEFAULT_THRESHOLD_CHECKPOINT_PATH,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate_holdouts(
            artifact_root=args.artifact_root,
            uvspec=args.uvspec,
            lib_radtran_archive=args.lib_radtran_archive,
            data_root=args.data_root,
            eso_archive=args.eso_archive,
            threshold_path=args.thresholds,
            threshold_checkpoint_path=args.threshold_checkpoint,
        )
    except (JonesMysticHoldoutValidationError, OSError) as exc:
        print(f"Jones/MYSTIC holdout validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
