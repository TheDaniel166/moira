#!/usr/bin/env python3
"""Build the checksum-bound Jones/MYSTIC lower-boundary experiment.

This research-only tool compares the exact corrected-v2 observer-bottom
control with the Jones/ESO 2,000 m model bottom and 2,640 m observer geometry.
It accepts only caller-supplied, checksum-locked inputs, writes generated
evidence outside the repository, never downloads data, and cannot admit a
runtime model or public API contract.
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
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_lower_boundary_spec.json"
)
VALIDATOR_PATH = (
    REPO_ROOT
    / "scripts"
    / "validate_visibility_phase4_jones_mystic_lower_boundary.py"
)

SPEC_SCHEMA = "moira.visibility-phase4-jones-mystic-lower-boundary-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-phase4-jones-mystic-lower-boundary-artifact/v1"
CASE_SCHEMA = "moira.visibility-phase4-jones-mystic-lower-boundary-case/v1"
CHECKPOINT_SCHEMA = (
    "moira.visibility-phase4-jones-mystic-lower-boundary-checkpoint/v1"
)
MANIFEST_NAME = "lower-boundary-manifest.json"
CHECKPOINT_NAME = "lower-boundary-checkpoint.json"
CONTROL_PROFILE_ID = "observer_bottom_control_v2"
CANDIDATE_PROFILE_ID = "jones_2000m_ground_observer_2640m_v1"
DATA_LINK_NAME = "data"


class JonesMysticLowerBoundaryError(ValueError):
    """Raised when the frozen lower-boundary contract is violated."""


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_receipt(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    label = path.relative_to(relative_to).as_posix() if relative_to else path.name
    return {"path": label, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JonesMysticLowerBoundaryError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesMysticLowerBoundaryError(f"{label} must be a JSON object")
    return payload


def _safe_repo_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise JonesMysticLowerBoundaryError(f"{label} must be a repository path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise JonesMysticLowerBoundaryError(f"{label} escapes the repository")
    return REPO_ROOT.joinpath(*path.parts)


def _verify_repo_receipt(receipt: Any, label: str) -> Path:
    if not isinstance(receipt, dict):
        raise JonesMysticLowerBoundaryError(f"{label} receipt is missing")
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
        raise JonesMysticLowerBoundaryError(f"{label} receipt differs: {path}")
    return path


def _verify_external_file(
    path: Path, *, expected_bytes: int, expected_sha256: str, label: str
) -> dict[str, Any]:
    if (
        not path.is_file()
        or path.stat().st_size != expected_bytes
        or sha256_file(path) != expected_sha256
    ):
        raise JonesMysticLowerBoundaryError(f"{label} receipt differs: {path}")
    return file_receipt(path)


def _load_module(path: Path, name: str) -> Any:
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise JonesMysticLowerBoundaryError(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _read_bound_tar_member(
    archive: Path, receipt: dict[str, Any], *, label: str
) -> bytes:
    member_path = receipt.get("path")
    if not isinstance(member_path, str) or not member_path:
        raise JonesMysticLowerBoundaryError(f"{label} member path is missing")
    try:
        with tarfile.open(archive, "r:*") as bundle:
            member = bundle.getmember(member_path)
            extracted = bundle.extractfile(member)
            payload = extracted.read() if extracted is not None else b""
    except (OSError, KeyError, tarfile.TarError) as exc:
        raise JonesMysticLowerBoundaryError(
            f"cannot read {label} member: {member_path}"
        ) from exc
    if (
        len(payload) != receipt.get("bytes")
        or sha256_bytes(payload) != receipt.get("sha256")
    ):
        raise JonesMysticLowerBoundaryError(f"{label} member receipt differs")
    return payload


def _parse_assignments(payload: bytes) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for raw_line in payload.decode("ascii").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        assignments[key.strip()] = value.strip()
    return assignments


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = _read_json(path, "lower-boundary specification")
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("status")
        != "refrozen_after_nondeterministic_profile_probe_receipt_exclusion_before_final_artifact"
        or spec.get("pilot_model_id") != "jones_paranal_mystic_550nm_pilot_v2"
        or spec.get("candidate_model_id")
        != "jones_paranal_scattered_moonlight_2013_v1"
    ):
        raise JonesMysticLowerBoundaryError("lower-boundary specification differs")
    boundary = spec.get("runtime_boundary")
    if not isinstance(boundary, dict) or any(
        boundary.get(key) is not False
        for key in (
            "engine_changes_authorized",
            "public_api_changes_authorized",
            "runtime_model_admitted",
            "production_data_pack_authorized",
            "spectral_grid_authorized",
            "runtime_dependency",
            "network_dependency",
            "automatic_download_allowed",
            "external_source_bytes_redistributed",
        )
    ):
        raise JonesMysticLowerBoundaryError("runtime boundary is not closed")
    protocol = spec.get("execution_protocol")
    if (
        not isinstance(protocol, dict)
        or protocol.get("wavelength_nm") != 550.0
        or protocol.get("case_source") != "corrected_v2_reserved_holdout_cases"
        or protocol.get("profiles_per_case")
        != [CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID]
        or protocol.get("photon_count_per_run") != 1_000_000
        or protocol.get("random_seed") != 271_828_183
        or protocol.get("exact_repeat_profile_id") != CANDIDATE_PROFILE_ID
        or protocol.get("exact_repeat_case_id")
        != "holdout_v2_interior_cross_axis"
        or protocol.get("maximum_relative_standard_error_per_run") != 0.005
        or protocol.get("control_must_exactly_reproduce_corrected_v2_holdout_checkpoint")
        is not True
        or protocol.get("candidate_absolute_radiance_expectations_prefrozen")
        is not False
        or protocol.get("candidate_control_difference_threshold_prefrozen")
        is not False
        or protocol.get("source_authority_selects_profile_not_numerical_closeness")
        is not True
    ):
        raise JonesMysticLowerBoundaryError("execution protocol differs")
    history = spec.get("pre_admission_execution_history")
    if (
        not isinstance(history, dict)
        or history.get("successful_artifact_count_before_final_refreeze") != 2
        or history.get("discarded_attempt_count_before_final_refreeze") != 5
        or not isinstance(history.get("discarded_attempts"), list)
        or len(history["discarded_attempts"]) != 5
        or any(
            attempt.get("artifact_authoritative") is not False
            for attempt in history["discarded_attempts"]
        )
    ):
        raise JonesMysticLowerBoundaryError(
            "pre-admission execution history differs"
        )
    _validate_profiles(spec)
    return spec


def _validate_profiles(spec: dict[str, Any]) -> None:
    profiles = spec.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != {
        CONTROL_PROFILE_ID,
        CANDIDATE_PROFILE_ID,
    }:
        raise JonesMysticLowerBoundaryError("profile inventory differs")
    control = profiles[CONTROL_PROFILE_ID]
    candidate = profiles[CANDIDATE_PROFILE_ID]
    expected_control = {
        "surface_altitude_km": 2.64,
        "observer_altitude_km": 2.64,
        "zout_above_surface_km": 0.0,
        "surface_pressure_hpa": 744.0,
        "ozone_column_du_above_surface": 258.0,
        "aerosol_profile_bottom_km": 2.64,
        "aerosol_normalization_reference_km": 2.64,
        "mystic_altitude_radiance_file_stem": "mc0",
    }
    if any(control.get(key) != value for key, value in expected_control.items()):
        raise JonesMysticLowerBoundaryError("control profile differs")
    expected_candidate = {
        "surface_altitude_km": 2.0,
        "observer_altitude_km": 2.64,
        "zout_above_surface_km": 0.64,
        "source_surface_pressure_hpa": 795.0,
        "source_observer_pressure_hpa": 733.6196899414062,
        "target_observer_pressure_hpa": 744.0,
        "surface_pressure_hpa": 806.2488072631218,
        "ozone_column_du_above_surface": 259.19991781804873,
        "aerosol_profile_bottom_km": 2.0,
        "aerosol_normalization_reference_km": 2.64,
        "aerosol_profile_top_km": 20.0,
        "aerosol_scale_height_km": 1.2,
        "observer_to_infinite_top_aod550": 0.0294,
        "observer_to_20km_aod550": 0.02939998466958803,
        "surface_to_20km_aod550": 0.05011536771007698,
        "below_observer_aod550": 0.020715383040488946,
        "mystic_altitude_radiance_file_stem": "mc3",
    }
    if any(candidate.get(key) != value for key, value in expected_candidate.items()):
        raise JonesMysticLowerBoundaryError("candidate profile differs")
    calculated_pressure = candidate["target_observer_pressure_hpa"] * (
        candidate["source_surface_pressure_hpa"]
        / candidate["source_observer_pressure_hpa"]
    )
    if not math.isclose(
        calculated_pressure,
        candidate["surface_pressure_hpa"],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise JonesMysticLowerBoundaryError("candidate pressure derivation differs")
    calculated_above = candidate["observer_to_infinite_top_aod550"] * (
        1.0
        - math.exp(
            -(
                candidate["aerosol_profile_top_km"]
                - candidate["aerosol_normalization_reference_km"]
            )
            / candidate["aerosol_scale_height_km"]
        )
    )
    calculated_total = candidate["observer_to_infinite_top_aod550"] * (
        math.exp(
            (
                candidate["aerosol_normalization_reference_km"]
                - candidate["aerosol_profile_bottom_km"]
            )
            / candidate["aerosol_scale_height_km"]
        )
        - math.exp(
            -(
                candidate["aerosol_profile_top_km"]
                - candidate["aerosol_normalization_reference_km"]
            )
            / candidate["aerosol_scale_height_km"]
        )
    )
    for actual, expected, label in (
        (calculated_above, candidate["observer_to_20km_aod550"], "above-observer AOD"),
        (calculated_total, candidate["surface_to_20km_aod550"], "total AOD"),
        (
            calculated_total - calculated_above,
            candidate["below_observer_aod550"],
            "below-observer AOD",
        ),
    ):
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15):
            raise JonesMysticLowerBoundaryError(f"candidate {label} differs")


def load_contracts(spec_path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(spec_path)
    lineage = spec.get("lineage")
    if not isinstance(lineage, dict):
        raise JonesMysticLowerBoundaryError("lineage receipts are missing")
    paths = {
        role: _verify_repo_receipt(receipt, role)
        for role, receipt in lineage.items()
    }
    invalidation = _read_json(paths["v1_invalidation_checkpoint"], "v1 invalidation")
    pilot_checkpoint = _read_json(
        paths["corrected_v2_pilot_checkpoint"], "corrected-v2 pilot checkpoint"
    )
    threshold_checkpoint = _read_json(
        paths["corrected_v2_threshold_checkpoint"], "corrected-v2 threshold checkpoint"
    )
    holdout_checkpoint = _read_json(
        paths["corrected_v2_holdout_checkpoint"], "corrected-v2 holdout checkpoint"
    )
    if (
        invalidation.get("schema")
        != "moira.visibility-phase4-jones-mystic-v1-invalidation-checkpoint/v1"
        or invalidation.get("status")
        != "v1_pilot_threshold_and_holdout_evidence_invalidated_before_runtime_admission"
    ):
        raise JonesMysticLowerBoundaryError("v1 invalidation lineage differs")
    if (
        pilot_checkpoint.get("schema")
        != "moira.visibility-phase4-jones-mystic-pilot-checkpoint/v2"
        or pilot_checkpoint.get("status")
        != "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
        or pilot_checkpoint.get("fixed_seed_repeat_passed") is not True
    ):
        raise JonesMysticLowerBoundaryError("corrected-v2 pilot lineage differs")
    if (
        threshold_checkpoint.get("schema")
        != "moira.visibility-phase4-jones-mystic-threshold-checkpoint/v2"
        or threshold_checkpoint.get("all_frozen_thresholds_passed") is not True
        or threshold_checkpoint.get("failed_checks") != []
        or threshold_checkpoint.get("runtime_model_admitted") is not False
    ):
        raise JonesMysticLowerBoundaryError("corrected-v2 threshold lineage differs")
    if (
        holdout_checkpoint.get("schema")
        != "moira.visibility-phase4-jones-mystic-holdout-checkpoint/v2"
        or holdout_checkpoint.get("status")
        != "corrected_v2_sealed_holdouts_pass_frozen_thresholds"
        or holdout_checkpoint.get("all_frozen_holdout_checks_passed") is not True
        or holdout_checkpoint.get("failed_checks") != []
        or holdout_checkpoint.get("runtime_model_admitted") is not False
    ):
        raise JonesMysticLowerBoundaryError("corrected-v2 holdout lineage differs")

    tooling = pilot_checkpoint.get("tooling")
    if not isinstance(tooling, dict):
        raise JonesMysticLowerBoundaryError("pilot tooling receipts are missing")
    pilot_spec_path = _verify_repo_receipt(tooling.get("spec"), "pilot spec")
    if file_receipt(pilot_spec_path, relative_to=REPO_ROOT) != lineage[
        "corrected_v2_pilot_specification"
    ]:
        raise JonesMysticLowerBoundaryError("pilot specification lineage differs")
    pilot_builder_path = _verify_repo_receipt(tooling.get("builder"), "pilot builder")
    _verify_repo_receipt(tooling.get("validator"), "pilot validator")
    pilot_builder = _load_module(
        pilot_builder_path, "_moira_phase4_pilot_builder_for_lower_boundary"
    )
    pilot_spec = pilot_builder.load_spec(pilot_spec_path)
    elevated_builder = _load_module(
        paths["elevated_atmosphere_constructor"],
        "_moira_phase4_elevated_builder_for_lower_boundary",
    )

    protocol = spec["execution_protocol"]
    reserved = {case["case_id"]: case for case in pilot_spec["reserved_holdout_cases"]}
    if list(reserved) != protocol["case_ids"]:
        raise JonesMysticLowerBoundaryError("reserved holdout case order differs")
    expected_control = {row["case_id"]: row for row in holdout_checkpoint["measurements"]}
    if set(expected_control) != set(protocol["case_ids"]):
        raise JonesMysticLowerBoundaryError("control measurement inventory differs")
    return {
        "spec": spec,
        "spec_path": spec_path,
        "lineage_paths": paths,
        "pilot_checkpoint": pilot_checkpoint,
        "threshold_checkpoint": threshold_checkpoint,
        "holdout_checkpoint": holdout_checkpoint,
        "pilot_spec": pilot_spec,
        "pilot_spec_path": pilot_spec_path,
        "pilot_builder": pilot_builder,
        "elevated_builder": elevated_builder,
        "reserved_cases": reserved,
        "expected_control": expected_control,
    }


def experiment_cases(contracts: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    spec = contracts["spec"]
    protocol = spec["execution_protocol"]
    builder = contracts["pilot_builder"]
    base = []
    for case_id in protocol["case_ids"]:
        case = {
            **contracts["reserved_cases"][case_id],
            "class": "lower_boundary_reserved_holdout_reuse",
            "target_moon_separation_deg": builder.target_moon_separation_deg(
                float(contracts["reserved_cases"][case_id]["target_true_altitude_deg"]),
                float(contracts["reserved_cases"][case_id]["moon_true_altitude_deg"]),
                float(contracts["reserved_cases"][case_id]["relative_moon_azimuth_deg"]),
            ),
            "photon_count": protocol["photon_count_per_run"],
            "random_seed": protocol["random_seed"],
        }
        builder.validate_case(case, runnable=True)
        base.append(case)
    candidate = [dict(case) for case in base]
    anchor = next(
        case
        for case in candidate
        if case["case_id"] == protocol["exact_repeat_case_id"]
    )
    repeat = {
        **anchor,
        "case_id": f"{anchor['case_id']}_candidate_repeat",
        "repeat_of": anchor["case_id"],
    }
    builder.validate_case(repeat, runnable=True)
    candidate.append(repeat)
    return {CONTROL_PROFILE_ID: base, CANDIDATE_PROFILE_ID: candidate}


def expected_run_files(
    contracts: dict[str, Any], profile_id: str
) -> frozenset[str]:
    stem = contracts["spec"]["profiles"][profile_id][
        "mystic_altitude_radiance_file_stem"
    ]
    return frozenset(
        (contracts["pilot_builder"].EXPECTED_RUN_FILES - {"mc0.rad", "mc0.rad.std"})
        | {f"{stem}.rad", f"{stem}.rad.std"}
    )


def scientific_repeat_files(
    contracts: dict[str, Any], profile_id: str
) -> tuple[str, ...]:
    stem = contracts["spec"]["profiles"][profile_id][
        "mystic_altitude_radiance_file_stem"
    ]
    return tuple(
        f"{stem}{name.removeprefix('mc0')}" if name.startswith("mc0") else name
        for name in contracts["pilot_builder"].SCIENTIFIC_REPEAT_FILES
    )


def inspect_contract(spec_path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    contracts = load_contracts(spec_path)
    cases = experiment_cases(contracts)
    return {
        "status": "lower_boundary_contract_frozen_execution_not_yet_run",
        "experiment_id": contracts["spec"]["experiment_id"],
        "profile_ids": list(cases),
        "unique_case_count": 3,
        "executed_run_count_with_candidate_repeat": sum(map(len, cases.values())),
        "observer_altitude_km": 2.64,
        "candidate_surface_altitude_km": 2.0,
        "runtime_model_admitted": False,
        "production_admission_allowed": False,
        "spectral_grid_admitted": False,
    }


def _source_and_generator(
    contracts: dict[str, Any],
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
) -> dict[str, Any]:
    spec = contracts["spec"]
    pilot_spec = contracts["pilot_spec"]
    builder = contracts["pilot_builder"]
    source_semantics = spec["source_semantics"]
    lib_lock = source_semantics["libradtran_archive"]
    lib_receipt = _verify_external_file(
        lib_radtran_archive,
        expected_bytes=lib_lock["bytes"],
        expected_sha256=lib_lock["sha256"],
        label="libRadtran source archive",
    )
    uvspec_receipt = builder._verify_uvspec(uvspec, pilot_spec)
    data_receipt = builder.tree_receipt(data_root)
    if data_receipt != pilot_spec["external_generators"]["libRadtran"][
        "data_root_receipt"
    ]:
        raise JonesMysticLowerBoundaryError("libRadtran data-root receipt differs")
    eso_lock = source_semantics["eso_archive"]
    eso_receipt = _verify_external_file(
        eso_archive,
        expected_bytes=eso_lock["bytes"],
        expected_sha256=eso_lock["sha256"],
        label="ESO source archive",
    )
    eso_payloads, eso_members = builder._read_eso_members(eso_archive, pilot_spec)
    config_receipt = source_semantics["eso_model_configuration"]
    config_payload = _read_bound_tar_member(
        eso_archive, config_receipt, label="ESO model configuration"
    )
    assignments = _parse_assignments(config_payload)
    for key, expected in config_receipt["required_assignments"].items():
        try:
            actual = float(assignments[key])
        except (KeyError, ValueError) as exc:
            raise JonesMysticLowerBoundaryError(
                f"ESO model configuration assignment differs: {key}"
            ) from exc
        if not math.isclose(actual, float(expected), rel_tol=0.0, abs_tol=1e-15):
            raise JonesMysticLowerBoundaryError(
                f"ESO model configuration assignment differs: {key}"
            )
    lib_members = []
    for member in source_semantics["libradtran_members"]:
        _read_bound_tar_member(lib_radtran_archive, member, label=member["role"])
        lib_members.append(member)

    by_role = {
        receipt["role"]: eso_payloads[receipt["path"]]
        for receipt in pilot_spec["external_source"]["required_members"]
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
    lunar = pilot_spec["lunar_source"]
    if not math.isclose(
        solar,
        lunar["solar_irradiance_550nm_W_m-2_micrometre-1"],
        rel_tol=0.0,
        abs_tol=lunar["source_interpolation_absolute_tolerance"],
    ):
        raise JonesMysticLowerBoundaryError("solar source derivation differs")
    if any(
        not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15)
        for actual, expected in zip(
            rolo_coefficients,
            lunar["rolo_interpolated_coefficients_550nm"],
            strict=True,
        )
    ):
        raise JonesMysticLowerBoundaryError("ROLO source derivation differs")
    if not math.isclose(aod550, 0.0294, rel_tol=0.0, abs_tol=1e-15):
        raise JonesMysticLowerBoundaryError("aerosol source derivation differs")
    return {
        "generator": {
            "libRadtran_source_archive": lib_receipt,
            "libRadtran_members": lib_members,
            "uvspec": uvspec_receipt,
            "data_root": data_receipt,
        },
        "external_source": {
            "archive": eso_receipt,
            "pilot_members": eso_members,
            "model_configuration": config_receipt,
            "redistributed": False,
        },
        "source_inputs": {
            "solar_irradiance": solar,
            "rolo_constants": rolo_constants,
            "rolo_coefficients": rolo_coefficients,
            "correction_divisor": lunar["rolo_correction_divisor"],
            "moon_solid_angle_sr": lunar["moon_solid_angle_sr"],
        },
        "source_derivations": {
            "solar_irradiance_550nm_W_m-2_micrometre-1": solar,
            "rolo_constant_coefficients": rolo_constants,
            "rolo_interpolated_coefficients_550nm": rolo_coefficients,
            "aod550": aod550,
            "eso_required_assignments": {
                key: float(assignments[key])
                for key in config_receipt["required_assignments"]
            },
        },
        "phase_values": phase_values,
    }


def _data_rows(payload: bytes, columns: int) -> list[list[float]]:
    rows = []
    for line in payload.decode("ascii").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            values = [float(token) for token in stripped.split()]
            if len(values) != columns:
                raise JonesMysticLowerBoundaryError("profile row shape differs")
            rows.append(values)
    return rows


def _join_profiles(
    observer_payload: bytes, surface_payload: bytes, *, columns: int
) -> bytes:
    observer_lines = observer_payload.decode("ascii").splitlines()
    header = [line for line in observer_lines if line.strip().startswith("#")]
    observer_rows = _data_rows(observer_payload, columns)
    surface_rows = _data_rows(surface_payload, columns)
    observer_altitude = observer_rows[-1][0]
    tail = [row for row in surface_rows if row[0] < observer_altitude - 1e-7]
    if not tail or not math.isclose(tail[-1][0], 2.0, rel_tol=0.0, abs_tol=1e-7):
        raise JonesMysticLowerBoundaryError("candidate surface profile differs")
    combined = observer_rows + tail
    if any(combined[index][0] <= combined[index + 1][0] for index in range(len(combined) - 1)):
        raise JonesMysticLowerBoundaryError("candidate profile is not descending")
    body = [
        " ".join(format(float(value), ".9g") for value in row)
        for row in combined
    ]
    return ("\n".join(header + body) + "\n").encode("ascii")


def _aerosol_boundaries(pilot_spec: dict[str, Any]) -> tuple[list[float], list[float]]:
    aerosol = pilot_spec["aerosol"]
    bottom = float(aerosol["profile_bottom_km"])
    top = float(aerosol["profile_top_km"])
    step = float(aerosol["nominal_layer_thickness_km"])
    control = [bottom]
    while control[-1] + step < top - 1e-12:
        control.append(round(control[-1] + step, 12))
    control.append(top)
    candidate = [2.0, 2.25, 2.5, 2.64] + control[1:]
    return control, candidate


def _write_candidate_shared(
    root: Path,
    *,
    contracts: dict[str, Any],
    data_root: Path,
    phase_values: list[float],
) -> dict[str, Any]:
    shared = root / "shared"
    shared.mkdir()
    pilot_spec = contracts["pilot_spec"]
    candidate = contracts["spec"]["profiles"][CANDIDATE_PROFILE_ID]
    elevated = contracts["elevated_builder"]
    source_path = data_root / pilot_spec["site_and_atmosphere"][
        "atmosphere_source_path"
    ].removeprefix("data/")
    source_text = source_path.read_text(encoding="ascii")
    atmosphere_2640, atmosphere_2640_meta = elevated.construct_truncated_atmosphere(
        source_text, 2640.0
    )
    atmosphere_2000, atmosphere_2000_meta = elevated.construct_truncated_atmosphere(
        source_text, 2000.0
    )
    o4_2640, o4_2640_meta = elevated.construct_truncated_o4_profile(source_text, 2640.0)
    o4_2000, o4_2000_meta = elevated.construct_truncated_o4_profile(source_text, 2000.0)
    atmosphere = _join_profiles(atmosphere_2640, atmosphere_2000, columns=9)
    o4 = _join_profiles(o4_2640, o4_2000, columns=2)
    (shared / "atmosphere.dat").write_bytes(atmosphere)
    (shared / "o4.dat").write_bytes(o4)

    aerosol = pilot_spec["aerosol"]
    moments, representation = contracts["pilot_builder"].compute_legendre_moments(
        phase_values,
        moment_count=aerosol["legendre_moment_count"],
        quadrature_order=aerosol["gauss_legendre_quadrature_order"],
    )
    moment_text = " ".join(format(value, ".17e") for value in moments)
    null_payload = b"100 0 1 1\n100000 0 1 1\n"
    (shared / "null_layer.dat").write_bytes(null_payload)
    control_boundaries, boundaries = _aerosol_boundaries(pilot_spec)
    reference = float(candidate["aerosol_normalization_reference_km"])
    scale_height = float(candidate["aerosol_scale_height_km"])
    aod_reference = float(candidate["observer_to_infinite_top_aod550"])
    layers = []
    for index, (low, high) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        extinction = aod_reference * (
            math.exp(-(low - reference) / scale_height)
            - math.exp(-(high - reference) / scale_height)
        ) / (high - low)
        filename = f"aerosol_layer_{index:03d}.dat"
        rows = [
            f"{float(wavelength):.1f} {extinction:.17e} "
            f"{float(aerosol['single_scattering_albedo']):.17g} {moment_text}"
            for wavelength in aerosol["explicit_file_wavelength_grid_nm"]
        ]
        (shared / filename).write_bytes(("\n".join(rows) + "\n").encode("ascii"))
        layers.append(
            {
                "index": index,
                "low_km": low,
                "high_km": high,
                "extinction_km-1": extinction,
                "filename": filename,
            }
        )
    profile = contracts["pilot_builder"].render_explicit_aerosol_profile(
        layers,
        profile_top_km=float(candidate["aerosol_profile_top_km"]),
        null_top_boundary_km=float(aerosol["null_top_boundary_km"]),
    )
    (shared / "aerosol_profile.dat").write_bytes(profile)
    integrated = sum(
        float(layer["extinction_km-1"])
        * (float(layer["high_km"]) - float(layer["low_km"]))
        for layer in layers
    )
    above_layers = [layer for layer in layers if float(layer["low_km"]) >= 2.64]
    return {
        "atmosphere": {
            "surface_construction": atmosphere_2000_meta,
            "observer_construction": atmosphere_2640_meta,
            "explicit_observer_level_km": 2.64,
            "bottom_level_km": 2.0,
            "level_count": len(_data_rows(atmosphere, 9)),
        },
        "o4_companion": {
            "surface_construction": o4_2000_meta,
            "observer_construction": o4_2640_meta,
            "explicit_observer_level_km": 2.64,
            "bottom_level_km": 2.0,
            "level_count": len(_data_rows(o4, 2)),
        },
        "atmosphere_source": file_receipt(source_path),
        "aerosol": {
            "layer_count": len(layers),
            "boundaries_km": boundaries,
            "control_boundaries_km": control_boundaries,
            "above_observer_boundaries_preserved": boundaries[3:]
            == control_boundaries,
            "above_observer_layer_count": len(above_layers),
            "below_observer_layer_count": len(layers) - len(above_layers),
            "explicit_profile_layout": aerosol["explicit_profile_layout"],
            "uppermost_marker_km": float(aerosol["null_top_boundary_km"]),
            "lowest_physical_layer_boundary_km": 2.0,
            "integrated_aod_to_profile_top": integrated,
            "observer_to_profile_top_aod": sum(
                float(layer["extinction_km-1"])
                * (float(layer["high_km"]) - float(layer["low_km"]))
                for layer in above_layers
            ),
            "below_observer_aod": sum(
                float(layer["extinction_km-1"])
                * (float(layer["high_km"]) - float(layer["low_km"]))
                for layer in layers
                if float(layer["high_km"]) <= 2.64
            ),
            "representation": representation,
            "normalized_moments_sha256": sha256_bytes(canonical_json_bytes(moments)),
        },
        "files": [
            file_receipt(path, relative_to=root)
            for path in sorted(shared.iterdir())
            if path.is_file()
        ],
    }


def _profile_site_spec(contracts: dict[str, Any], profile_id: str) -> dict[str, Any]:
    site = dict(contracts["pilot_spec"]["site_and_atmosphere"])
    profile = contracts["spec"]["profiles"][profile_id]
    site["surface_pressure_hpa"] = profile["surface_pressure_hpa"]
    site["ozone_column_du"] = profile["ozone_column_du_above_surface"]
    return site


def render_input(
    case: dict[str, Any], *, contracts: dict[str, Any], profile_id: str
) -> bytes:
    site = _profile_site_spec(contracts, profile_id)
    profile = contracts["spec"]["profiles"][profile_id]
    wavelength = float(contracts["spec"]["execution_protocol"]["wavelength_nm"])
    viewing_umu = -math.sin(math.radians(float(case["target_true_altitude_deg"])))
    lunar_zenith = 90.0 - float(case["moon_true_altitude_deg"])
    cross_sections = site["cross_sections"]
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        "atmosphere_file ../../shared/atmosphere.dat",
        "source solar lunar_source.dat per_nm",
        "mol_abs_param crs",
        f"crs_model rayleigh {cross_sections['rayleigh']}",
        f"crs_model O3 {cross_sections['O3']}",
        f"crs_model NO2 {cross_sections['NO2']}",
        f"crs_model O4 {cross_sections['O4']}",
        "mol_file O4 ../../shared/o4.dat cm_3",
        f"wavelength {wavelength:.12g} {wavelength:.12g}",
        f"sza {lunar_zenith:.15g}",
        "phi0 0",
        f"earth_radius {float(site['earth_radius_km']):.12g}",
        f"pressure {float(site['surface_pressure_hpa']):.12g}",
        f"mol_modify O3 {float(site['ozone_column_du']):.12g} DU",
        f"albedo {float(site['ground_albedo_550nm']):.12g}",
        "aerosol_default",
        "aerosol_file explicit ../../shared/aerosol_profile.dat",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {case['photon_count']}",
        f"mc_randomseed {case['random_seed']}",
        "mc_escape",
        "mc_std",
        "mc_vroom on",
        f"zout {float(profile['zout_above_surface_km']):.12g}",
        f"umu {viewing_umu:.17g}",
        f"phi {float(case['relative_moon_azimuth_deg']):.17g}",
        "quiet",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def render_profile_probe(contracts: dict[str, Any], profile_id: str) -> bytes:
    site = _profile_site_spec(contracts, profile_id)
    profile = contracts["spec"]["profiles"][profile_id]
    cross_sections = site["cross_sections"]
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        "atmosphere_file ../shared/atmosphere.dat",
        "source thermal",
        "mol_abs_param crs",
        f"crs_model rayleigh {cross_sections['rayleigh']}",
        f"crs_model O3 {cross_sections['O3']}",
        f"crs_model NO2 {cross_sections['NO2']}",
        f"crs_model O4 {cross_sections['O4']}",
        "mol_file O4 ../shared/o4.dat cm_3",
        "wavelength 550 550",
        f"pressure {float(site['surface_pressure_hpa']):.12g}",
        f"mol_modify O3 {float(site['ozone_column_du']):.12g} DU",
        f"zout {float(profile['zout_above_surface_km']):.12g}",
        "output_user zout_sea p n_o3",
        "quiet",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def _run_process(command: list[str], *, cwd: Path, input_bytes: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command, cwd=cwd, input=input_bytes, check=False, capture_output=True
    )


def _run_profile_probe(
    root: Path,
    *,
    contracts: dict[str, Any],
    profile_id: str,
    uvspec: Path,
    data_root: Path,
) -> dict[str, Any]:
    probe_dir = root / "profile-probe"
    probe_dir.mkdir()
    input_bytes = render_profile_probe(contracts, profile_id)
    (probe_dir / "input.inp").write_bytes(input_bytes)
    data_link = probe_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    try:
        executed = _run_process([str(uvspec)], cwd=probe_dir, input_bytes=input_bytes)
        (probe_dir / "stdout.txt").write_bytes(executed.stdout)
        (probe_dir / "stderr.txt").write_bytes(executed.stderr)
        if executed.returncode != 0:
            raise JonesMysticLowerBoundaryError(
                f"profile probe failed for {profile_id}: "
                f"{executed.stderr.decode('utf-8', errors='replace')}"
            )
    finally:
        if data_link.is_symlink():
            data_link.unlink()
    incidental_randomseed = probe_dir / "randomseed"
    if incidental_randomseed.is_file() and not incidental_randomseed.is_symlink():
        incidental_randomseed.unlink()
    elif incidental_randomseed.exists() or incidental_randomseed.is_symlink():
        raise JonesMysticLowerBoundaryError(
            f"profile probe randomseed is not a removable regular file: {profile_id}"
        )
    actual_files = {path.name for path in probe_dir.iterdir() if path.is_file()}
    expected_files = {"input.inp", "stdout.txt", "stderr.txt"}
    if actual_files != expected_files or any(
        path.is_symlink() for path in probe_dir.iterdir()
    ):
        raise JonesMysticLowerBoundaryError(
            f"profile probe inventory differs for {profile_id}; "
            f"missing={sorted(expected_files - actual_files)}, "
            f"unexpected={sorted(actual_files - expected_files)}"
        )
    rows = [line.split() for line in executed.stdout.decode("ascii").splitlines() if line]
    if len(rows) != 1 or len(rows[0]) != 3:
        raise JonesMysticLowerBoundaryError(f"profile probe shape differs: {profile_id}")
    values = [float(token) for token in rows[0]]
    return {
        "profile_id": profile_id,
        "observer_altitude_km": values[0],
        "observer_pressure_hpa": values[1],
        "observer_o3_number_density_cm-3": values[2],
        "files": [
            file_receipt(path, relative_to=root)
            for path in sorted(probe_dir.iterdir())
            if path.is_file()
        ],
    }


def _run_case(
    case: dict[str, Any],
    *,
    root: Path,
    contracts: dict[str, Any],
    profile_id: str,
    uvspec: Path,
    data_root: Path,
    source_inputs: dict[str, Any],
) -> dict[str, Any]:
    builder = contracts["pilot_builder"]
    run_dir = root / "runs" / case["case_id"]
    run_dir.mkdir(parents=True)
    source = builder.lunar_source_flux_550(case, **source_inputs)
    lunar_bytes = builder.render_lunar_source(source["toa_lunar_irradiance_W_m-2_nm-1"], contracts["pilot_spec"])
    input_bytes = render_input(case, contracts=contracts, profile_id=profile_id)
    (run_dir / "lunar_source.dat").write_bytes(lunar_bytes)
    (run_dir / "input.inp").write_bytes(input_bytes)
    data_link = run_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    try:
        syntax = _run_process([str(uvspec), "-c"], cwd=run_dir, input_bytes=input_bytes)
        (run_dir / "syntax.stdout.txt").write_bytes(syntax.stdout)
        (run_dir / "syntax.stderr.txt").write_bytes(syntax.stderr)
        if syntax.returncode != 0:
            raise JonesMysticLowerBoundaryError(
                f"uvspec syntax check failed for {profile_id}/{case['case_id']}: "
                f"{syntax.stderr.decode('utf-8', errors='replace')}"
            )
        executed = _run_process([str(uvspec)], cwd=run_dir, input_bytes=input_bytes)
        (run_dir / "stdout.txt").write_bytes(executed.stdout)
        (run_dir / "stderr.txt").write_bytes(executed.stderr)
        if executed.returncode != 0:
            raise JonesMysticLowerBoundaryError(
                f"uvspec failed for {profile_id}/{case['case_id']}: "
                f"{executed.stderr.decode('utf-8', errors='replace')}"
            )
    finally:
        if data_link.is_symlink():
            data_link.unlink()
    actual = {path.name for path in run_dir.iterdir() if path.is_file()}
    expected_files = expected_run_files(contracts, profile_id)
    if actual != expected_files or any(
        path.is_symlink() for path in run_dir.iterdir()
    ):
        missing = sorted(expected_files - actual)
        unexpected = sorted(actual - expected_files)
        raise JonesMysticLowerBoundaryError(
            f"run inventory differs for {profile_id}/{case['case_id']}; "
            f"missing={missing}, unexpected={unexpected}"
        )
    radiance = builder.parse_directional_output(run_dir / "mc.rad.spc")
    standard_error = builder.parse_directional_output(run_dir / "mc.rad.std.spc")
    case_manifest = {
        "schema": CASE_SCHEMA,
        "profile_id": profile_id,
        "case": case,
        "derived": {
            "target_moon_separation_deg": builder.target_moon_separation_deg(
                float(case["target_true_altitude_deg"]),
                float(case["moon_true_altitude_deg"]),
                float(case["relative_moon_azimuth_deg"]),
            ),
            **source,
            "directional_radiance_W_m-2_nm-1_sr-1": radiance,
            "directional_standard_error_W_m-2_nm-1_sr-1": standard_error,
            "relative_monte_carlo_standard_error": standard_error / radiance,
        },
        "files": [
            file_receipt(path, relative_to=root)
            for path in sorted(run_dir.iterdir())
            if path.is_file()
        ],
    }
    case_path = run_dir / "case.json"
    case_path.write_bytes(canonical_json_bytes(case_manifest))
    return {
        "profile_id": profile_id,
        "case_id": case["case_id"],
        "case": case,
        "case_manifest": file_receipt(case_path, relative_to=root),
        "derived": case_manifest["derived"],
    }


def _diagnostics(
    artifact_root: Path,
    *,
    contracts: dict[str, Any],
    results: dict[str, list[dict[str, Any]]],
    probes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    protocol = contracts["spec"]["execution_protocol"]
    control = {row["case_id"]: row for row in results[CONTROL_PROFILE_ID]}
    candidate = {
        row["case_id"]: row
        for row in results[CANDIDATE_PROFILE_ID]
        if "repeat_of" not in row["case"]
    }
    measurements = []
    for case_id in protocol["case_ids"]:
        control_row = control[case_id]["derived"]
        candidate_row = candidate[case_id]["derived"]
        control_radiance = control_row["directional_radiance_W_m-2_nm-1_sr-1"]
        candidate_radiance = candidate_row["directional_radiance_W_m-2_nm-1_sr-1"]
        combined_error = math.hypot(
            control_row["directional_standard_error_W_m-2_nm-1_sr-1"],
            candidate_row["directional_standard_error_W_m-2_nm-1_sr-1"],
        )
        measurements.append(
            {
                "case_id": case_id,
                "control_directional_radiance_W_m-2_nm-1_sr-1": control_radiance,
                "control_directional_standard_error_W_m-2_nm-1_sr-1": control_row[
                    "directional_standard_error_W_m-2_nm-1_sr-1"
                ],
                "control_relative_standard_error": control_row[
                    "relative_monte_carlo_standard_error"
                ],
                "candidate_directional_radiance_W_m-2_nm-1_sr-1": candidate_radiance,
                "candidate_directional_standard_error_W_m-2_nm-1_sr-1": candidate_row[
                    "directional_standard_error_W_m-2_nm-1_sr-1"
                ],
                "candidate_relative_standard_error": candidate_row[
                    "relative_monte_carlo_standard_error"
                ],
                "candidate_to_control_radiance_ratio": candidate_radiance
                / control_radiance,
                "candidate_relative_change": candidate_radiance / control_radiance - 1.0,
                "candidate_minus_control_magnitude": -2.5
                * math.log10(candidate_radiance / control_radiance),
                "combined_monte_carlo_standard_error_W_m-2_nm-1_sr-1": combined_error,
                "candidate_control_difference_z_score": (
                    candidate_radiance - control_radiance
                )
                / combined_error,
            }
        )
    expected_control = contracts["expected_control"]
    control_exact = all(
        control[case_id]["derived"]["directional_radiance_W_m-2_nm-1_sr-1"]
        == expected_control[case_id]["directional_radiance_W_m-2_nm-1_sr-1"]
        and control[case_id]["derived"][
            "directional_standard_error_W_m-2_nm-1_sr-1"
        ]
        == expected_control[case_id][
            "directional_standard_error_W_m-2_nm-1_sr-1"
        ]
        for case_id in protocol["case_ids"]
    )
    repeat_anchor = protocol["exact_repeat_case_id"]
    repeat_id = f"{repeat_anchor}_candidate_repeat"
    repeat_files = {
        name: (
            artifact_root
            / "profiles"
            / CANDIDATE_PROFILE_ID
            / "runs"
            / repeat_anchor
            / name
        ).read_bytes()
        == (
            artifact_root
            / "profiles"
            / CANDIDATE_PROFILE_ID
            / "runs"
            / repeat_id
            / name
        ).read_bytes()
        for name in scientific_repeat_files(contracts, CANDIDATE_PROFILE_ID)
    }
    unique_results = results[CONTROL_PROFILE_ID] + [
        row for row in results[CANDIDATE_PROFILE_ID] if "repeat_of" not in row["case"]
    ]
    maximum_rse = max(
        row["derived"]["relative_monte_carlo_standard_error"] for row in unique_results
    )
    control_probe = probes[CONTROL_PROFILE_ID]
    candidate_probe = probes[CANDIDATE_PROFILE_ID]
    candidate_shared = _read_json(
        artifact_root / "profiles" / CANDIDATE_PROFILE_ID / "shared-metadata.json",
        "candidate shared metadata",
    )
    checks = {
        "control_exactly_reproduces_corrected_v2_holdout_checkpoint": control_exact,
        "all_directional_outputs_finite_positive": all(
            math.isfinite(row["derived"]["directional_radiance_W_m-2_nm-1_sr-1"])
            and row["derived"]["directional_radiance_W_m-2_nm-1_sr-1"] > 0.0
            and math.isfinite(
                row["derived"]["directional_standard_error_W_m-2_nm-1_sr-1"]
            )
            and row["derived"]["directional_standard_error_W_m-2_nm-1_sr-1"] > 0.0
            for row in unique_results
        ),
        "maximum_relative_standard_error_per_run": maximum_rse
        <= protocol["maximum_relative_standard_error_per_run"],
        "candidate_exact_fixed_seed_repeat": all(repeat_files.values()),
        "both_profiles_evaluate_at_2640m_and_744hpa": all(
            math.isclose(probe["observer_altitude_km"], 2.64, rel_tol=0.0, abs_tol=1e-6)
            and math.isclose(probe["observer_pressure_hpa"], 744.0, rel_tol=0.0, abs_tol=1e-9)
            for probe in probes.values()
        ),
        "candidate_observer_o3_matches_control": math.isclose(
            candidate_probe["observer_o3_number_density_cm-3"],
            control_probe["observer_o3_number_density_cm-3"],
            rel_tol=0.0,
            abs_tol=1.0,
        ),
        "candidate_has_explicit_2000m_bottom_and_2640m_observer": (
            candidate_shared["atmosphere"]["bottom_level_km"] == 2.0
            and candidate_shared["atmosphere"]["explicit_observer_level_km"] == 2.64
            and candidate_shared["o4_companion"]["bottom_level_km"] == 2.0
            and candidate_shared["o4_companion"]["explicit_observer_level_km"] == 2.64
        ),
        "candidate_preserves_all_corrected_v2_boundaries_above_observer": candidate_shared[
            "aerosol"
        ]["above_observer_boundaries_preserved"]
        is True,
        "candidate_restores_frozen_below_observer_aod": math.isclose(
            candidate_shared["aerosol"]["below_observer_aod"],
            contracts["spec"]["profiles"][CANDIDATE_PROFILE_ID][
                "below_observer_aod550"
            ],
            rel_tol=0.0,
            abs_tol=1e-15,
        ),
    }
    return {
        "measurements": measurements,
        "profile_probes": probes,
        "maximum_relative_standard_error": maximum_rse,
        "maximum_allowed_relative_standard_error": protocol[
            "maximum_relative_standard_error_per_run"
        ],
        "candidate_fixed_seed_repeat": {
            "anchor_case_id": repeat_anchor,
            "repeat_case_id": repeat_id,
            "byte_identical_files": repeat_files,
            "passed": all(repeat_files.values()),
        },
        "candidate_numerical_difference_used_for_model_selection": False,
        "checks": checks,
        "all_lower_boundary_checks_passed": all(checks.values()),
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
    }


def _tooling_receipts(contracts: dict[str, Any]) -> dict[str, Any]:
    if not VALIDATOR_PATH.is_file():
        raise JonesMysticLowerBoundaryError(
            f"lower-boundary validator is missing: {VALIDATOR_PATH}"
        )
    return {
        "spec": file_receipt(contracts["spec_path"], relative_to=REPO_ROOT),
        "builder": file_receipt(Path(__file__).resolve(), relative_to=REPO_ROOT),
        "validator": file_receipt(VALIDATOR_PATH, relative_to=REPO_ROOT),
        "pilot_builder": contracts["pilot_checkpoint"]["tooling"]["builder"],
        "pilot_validator": contracts["pilot_checkpoint"]["tooling"]["validator"],
        "elevated_atmosphere_constructor": contracts["spec"]["lineage"][
            "elevated_atmosphere_constructor"
        ],
    }


def build_experiment(
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
    output_root: Path,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    if os.name != "posix":
        raise JonesMysticLowerBoundaryError(
            "the lower-boundary experiment must run in the POSIX libRadtran lab"
        )
    contracts = load_contracts(spec_path)
    if output_root.exists():
        raise JonesMysticLowerBoundaryError(f"output root already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    source = _source_and_generator(
        contracts,
        uvspec=uvspec,
        lib_radtran_archive=lib_radtran_archive,
        data_root=data_root,
        eso_archive=eso_archive,
    )
    cases = experiment_cases(contracts)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    try:
        profiles_root = temporary / "profiles"
        profiles_root.mkdir()
        shared_metadata: dict[str, dict[str, Any]] = {}
        results: dict[str, list[dict[str, Any]]] = {}
        probes: dict[str, dict[str, Any]] = {}
        for profile_id in (CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID):
            profile_root = profiles_root / profile_id
            profile_root.mkdir()
            if profile_id == CONTROL_PROFILE_ID:
                shared = contracts["pilot_builder"].construct_shared_inputs(
                    profile_root,
                    spec=contracts["pilot_spec"],
                    data_root=data_root,
                    phase_values=source["phase_values"],
                )
            else:
                shared = _write_candidate_shared(
                    profile_root,
                    contracts=contracts,
                    data_root=data_root,
                    phase_values=source["phase_values"],
                )
            shared_metadata[profile_id] = shared
            (profile_root / "shared-metadata.json").write_bytes(
                canonical_json_bytes(shared)
            )
            probes[profile_id] = _run_profile_probe(
                profile_root,
                contracts=contracts,
                profile_id=profile_id,
                uvspec=uvspec,
                data_root=data_root,
            )
            results[profile_id] = []
            for case in cases[profile_id]:
                print(
                    f"running {profile_id}/{case['case_id']} "
                    f"({case['photon_count']} photons)",
                    flush=True,
                )
                results[profile_id].append(
                    _run_case(
                        case,
                        root=profile_root,
                        contracts=contracts,
                        profile_id=profile_id,
                        uvspec=uvspec,
                        data_root=data_root,
                        source_inputs=source["source_inputs"],
                    )
                )
        diagnostics = _diagnostics(
            temporary, contracts=contracts, results=results, probes=probes
        )
        passed = diagnostics["all_lower_boundary_checks_passed"]
        status = (
            "source_faithful_lower_boundary_profile_verified_not_runtime_admitted"
            if passed
            else "lower_boundary_experiment_failed_not_runtime_admitted"
        )
        manifest = {
            "schema": ARTIFACT_SCHEMA,
            "status": status,
            "experiment_id": contracts["spec"]["experiment_id"],
            "candidate_model_id": contracts["spec"]["candidate_model_id"],
            "pilot_model_id": contracts["spec"]["pilot_model_id"],
            "wavelength_nm": 550.0,
            "tooling": _tooling_receipts(contracts),
            "lineage": contracts["spec"]["lineage"],
            "generator": source["generator"],
            "external_source": source["external_source"],
            "source_semantics": contracts["spec"]["source_semantics"],
            "pre_admission_execution_history": contracts["spec"][
                "pre_admission_execution_history"
            ],
            "source_derivations": source["source_derivations"],
            "profiles": {
                profile_id: {
                    "contract": contracts["spec"]["profiles"][profile_id],
                    "shared_metadata": file_receipt(
                        profiles_root / profile_id / "shared-metadata.json",
                        relative_to=temporary,
                    ),
                    "shared_inputs": shared_metadata[profile_id],
                    "profile_probe": probes[profile_id],
                    "runs": results[profile_id],
                }
                for profile_id in (CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID)
            },
            "diagnostics": diagnostics,
            "environment": {
                "platform": platform.platform(),
                "python": sys.version,
                "execution_order": "serial_control_then_candidate",
            },
            "candidate_absolute_radiance_expectations_prefrozen": False,
            "candidate_control_difference_threshold_prefrozen": False,
            "candidate_numerical_difference_used_for_model_selection": False,
            "source_authority_selects_profile": True,
            "spectral_grid_admitted": False,
            "production_admission_allowed": False,
            "runtime_model_admitted": False,
            "runtime_dependency": False,
            "network_dependency": False,
            "external_source_bytes_redistributed": False,
        }
        manifest_path = temporary / MANIFEST_NAME
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        checkpoint = {
            "schema": CHECKPOINT_SCHEMA,
            "status": status,
            "experiment_id": manifest["experiment_id"],
            "candidate_model_id": manifest["candidate_model_id"],
            "pilot_model_id": manifest["pilot_model_id"],
            "artifact_manifest": file_receipt(manifest_path),
            "tooling": manifest["tooling"],
            "lineage": manifest["lineage"],
            "source_semantics": manifest["source_semantics"],
            "pre_admission_execution_history": manifest[
                "pre_admission_execution_history"
            ],
            "profile_contracts": {
                profile_id: contracts["spec"]["profiles"][profile_id]
                for profile_id in (CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID)
            },
            "measurements": diagnostics["measurements"],
            "profile_probes": diagnostics["profile_probes"],
            "maximum_relative_standard_error": diagnostics[
                "maximum_relative_standard_error"
            ],
            "maximum_allowed_relative_standard_error": diagnostics[
                "maximum_allowed_relative_standard_error"
            ],
            "candidate_fixed_seed_repeat": diagnostics[
                "candidate_fixed_seed_repeat"
            ],
            "checks": diagnostics["checks"],
            "all_lower_boundary_checks_passed": passed,
            "failed_checks": diagnostics["failed_checks"],
            "source_faithful_profile_id": CANDIDATE_PROFILE_ID if passed else None,
            "candidate_numerical_difference_used_for_model_selection": False,
            "spectral_grid_admitted": False,
            "production_admission_allowed": False,
            "runtime_model_admitted": False,
            "runtime_dependency": False,
            "network_dependency": False,
            "external_source_bytes_redistributed": False,
            "next_gate": (
                "design_jones_2000m_ground_spectral_admission_matrix"
                if passed
                else "stop_and_investigate_lower_boundary_failure"
            ),
        }
        (temporary / CHECKPOINT_NAME).write_bytes(canonical_json_bytes(checkpoint))
        temporary.replace(output_root)
        return checkpoint
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--lib-radtran-archive", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--eso-archive", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument(
        "--inspect-contract",
        action="store_true",
        help="verify and print the frozen contract without running MYSTIC",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.inspect_contract:
            print(json.dumps(inspect_contract(args.spec), indent=2, sort_keys=True))
            return 0
        checkpoint = build_experiment(
            uvspec=args.uvspec,
            lib_radtran_archive=args.lib_radtran_archive,
            data_root=args.data_root,
            eso_archive=args.eso_archive,
            output_root=args.output_root,
            spec_path=args.spec,
        )
    except (JonesMysticLowerBoundaryError, OSError) as exc:
        print(f"Jones/MYSTIC lower-boundary experiment failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(checkpoint, indent=2, sort_keys=True))
    return 0 if checkpoint["all_lower_boundary_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
