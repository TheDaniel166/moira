#!/usr/bin/env python3
"""Independently validate a Jones/MYSTIC lower-boundary artifact.

The validator reconstructs the scientific inputs from the immutable pilot
validator and checksum-locked sources. It never imports the lower-boundary
builder whose output it audits.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_lower_boundary_spec.json"
)
BUILDER_PATH = (
    REPO_ROOT / "scripts" / "build_visibility_phase4_jones_mystic_lower_boundary.py"
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


class JonesMysticLowerBoundaryValidationError(ValueError):
    """Raised when lower-boundary evidence fails independent validation."""


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
        raise JonesMysticLowerBoundaryValidationError(
            f"cannot read {label}: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise JonesMysticLowerBoundaryValidationError(
            f"{label} must be a JSON object"
        )
    return payload


def _safe_path(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise JonesMysticLowerBoundaryValidationError(f"{label} path is missing")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise JonesMysticLowerBoundaryValidationError(f"{label} path escapes root")
    return root.joinpath(*path.parts)


def _verify_receipt(root: Path, receipt: Any, label: str) -> Path:
    if not isinstance(receipt, dict):
        raise JonesMysticLowerBoundaryValidationError(f"{label} receipt is missing")
    path = _safe_path(root, receipt.get("path"), label)
    if (
        not path.is_file()
        or path.is_symlink()
        or not isinstance(receipt.get("bytes"), int)
        or receipt["bytes"] < 0
        or path.stat().st_size != receipt["bytes"]
        or not isinstance(receipt.get("sha256"), str)
        or len(receipt["sha256"]) != 64
        or sha256_file(path) != receipt["sha256"]
    ):
        raise JonesMysticLowerBoundaryValidationError(
            f"{label} receipt differs: {path}"
        )
    return path


def _verify_external(path: Path, receipt: Any, label: str) -> None:
    if (
        not isinstance(receipt, dict)
        or not path.is_file()
        or path.stat().st_size != receipt.get("bytes")
        or sha256_file(path) != receipt.get("sha256")
    ):
        raise JonesMysticLowerBoundaryValidationError(f"{label} receipt differs")


def _load_module(path: Path, name: str) -> Any:
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise JonesMysticLowerBoundaryValidationError(
            f"cannot load independent validator: {path}"
        )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _load_spec(path: Path) -> dict[str, Any]:
    spec = _read_json(path, "lower-boundary specification")
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("status")
        != "refrozen_after_nondeterministic_profile_probe_receipt_exclusion_before_final_artifact"
        or spec.get("pilot_model_id") != "jones_paranal_mystic_550nm_pilot_v2"
        or spec.get("candidate_model_id")
        != "jones_paranal_scattered_moonlight_2013_v1"
    ):
        raise JonesMysticLowerBoundaryValidationError(
            "lower-boundary specification identity differs"
        )
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
        raise JonesMysticLowerBoundaryValidationError("runtime boundary changed")
    protocol = spec.get("execution_protocol")
    if (
        not isinstance(protocol, dict)
        or protocol.get("case_ids")
        != [
            "holdout_v2_low_altitude_oblique",
            "holdout_v2_interior_cross_axis",
            "holdout_v2_phase_boundary_waxing",
        ]
        or protocol.get("profiles_per_case")
        != [CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID]
        or protocol.get("photon_count_per_run") != 1_000_000
        or protocol.get("random_seed") != 271_828_183
        or protocol.get("exact_repeat_profile_id") != CANDIDATE_PROFILE_ID
        or protocol.get("exact_repeat_case_id")
        != "holdout_v2_interior_cross_axis"
        or protocol.get("maximum_relative_standard_error_per_run") != 0.005
        or protocol.get("candidate_absolute_radiance_expectations_prefrozen")
        is not False
        or protocol.get("candidate_control_difference_threshold_prefrozen")
        is not False
        or protocol.get("source_authority_selects_profile_not_numerical_closeness")
        is not True
    ):
        raise JonesMysticLowerBoundaryValidationError("execution protocol changed")
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
        raise JonesMysticLowerBoundaryValidationError(
            "pre-admission execution history changed"
        )
    _verify_profile_contracts(spec)
    return spec


def _verify_profile_contracts(spec: dict[str, Any]) -> None:
    profiles = spec.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != {
        CONTROL_PROFILE_ID,
        CANDIDATE_PROFILE_ID,
    }:
        raise JonesMysticLowerBoundaryValidationError("profile inventory changed")
    control = profiles[CONTROL_PROFILE_ID]
    candidate = profiles[CANDIDATE_PROFILE_ID]
    if (
        control.get("surface_altitude_km") != 2.64
        or control.get("observer_altitude_km") != 2.64
        or control.get("zout_above_surface_km") != 0.0
        or control.get("surface_pressure_hpa") != 744.0
        or control.get("ozone_column_du_above_surface") != 258.0
        or control.get("aerosol_profile_bottom_km") != 2.64
        or control.get("mystic_altitude_radiance_file_stem") != "mc0"
    ):
        raise JonesMysticLowerBoundaryValidationError("control profile changed")
    if (
        candidate.get("surface_altitude_km") != 2.0
        or candidate.get("observer_altitude_km") != 2.64
        or candidate.get("zout_above_surface_km") != 0.64
        or candidate.get("source_surface_pressure_hpa") != 795.0
        or candidate.get("source_observer_pressure_hpa") != 733.6196899414062
        or candidate.get("target_observer_pressure_hpa") != 744.0
        or candidate.get("surface_pressure_hpa") != 806.2488072631218
        or candidate.get("ozone_column_du_above_surface")
        != 259.19991781804873
        or candidate.get("aerosol_profile_bottom_km") != 2.0
        or candidate.get("aerosol_normalization_reference_km") != 2.64
        or candidate.get("aerosol_profile_top_km") != 20.0
        or candidate.get("aerosol_scale_height_km") != 1.2
        or candidate.get("observer_to_infinite_top_aod550") != 0.0294
        or candidate.get("mystic_altitude_radiance_file_stem") != "mc3"
    ):
        raise JonesMysticLowerBoundaryValidationError("candidate profile changed")
    pressure = candidate["target_observer_pressure_hpa"] * (
        candidate["source_surface_pressure_hpa"]
        / candidate["source_observer_pressure_hpa"]
    )
    if not math.isclose(
        pressure, candidate["surface_pressure_hpa"], rel_tol=0.0, abs_tol=1e-12
    ):
        raise JonesMysticLowerBoundaryValidationError(
            "candidate pressure derivation changed"
        )
    reference = candidate["aerosol_normalization_reference_km"]
    bottom = candidate["aerosol_profile_bottom_km"]
    top = candidate["aerosol_profile_top_km"]
    scale = candidate["aerosol_scale_height_km"]
    reference_aod = candidate["observer_to_infinite_top_aod550"]
    above = reference_aod * (1.0 - math.exp(-(top - reference) / scale))
    total = reference_aod * (
        math.exp((reference - bottom) / scale) - math.exp(-(top - reference) / scale)
    )
    if (
        not math.isclose(
            above,
            candidate["observer_to_20km_aod550"],
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        or not math.isclose(
            total,
            candidate["surface_to_20km_aod550"],
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        or not math.isclose(
            total - above,
            candidate["below_observer_aod550"],
            rel_tol=0.0,
            abs_tol=1e-15,
        )
    ):
        raise JonesMysticLowerBoundaryValidationError(
            "candidate aerosol derivation changed"
        )


def _load_contracts(spec_path: Path) -> dict[str, Any]:
    spec = _load_spec(spec_path)
    lineage = spec.get("lineage")
    if not isinstance(lineage, dict):
        raise JonesMysticLowerBoundaryValidationError("lineage is missing")
    paths = {
        role: _verify_receipt(REPO_ROOT, receipt, role)
        for role, receipt in lineage.items()
    }
    invalidation = _read_json(paths["v1_invalidation_checkpoint"], "v1 invalidation")
    pilot_checkpoint = _read_json(
        paths["corrected_v2_pilot_checkpoint"], "pilot checkpoint"
    )
    threshold_checkpoint = _read_json(
        paths["corrected_v2_threshold_checkpoint"], "threshold checkpoint"
    )
    holdout_checkpoint = _read_json(
        paths["corrected_v2_holdout_checkpoint"], "holdout checkpoint"
    )
    if (
        invalidation.get("status")
        != "v1_pilot_threshold_and_holdout_evidence_invalidated_before_runtime_admission"
        or pilot_checkpoint.get("status")
        != "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
        or pilot_checkpoint.get("fixed_seed_repeat_passed") is not True
        or threshold_checkpoint.get("all_frozen_thresholds_passed") is not True
        or threshold_checkpoint.get("failed_checks") != []
        or holdout_checkpoint.get("status")
        != "corrected_v2_sealed_holdouts_pass_frozen_thresholds"
        or holdout_checkpoint.get("all_frozen_holdout_checks_passed") is not True
        or holdout_checkpoint.get("failed_checks") != []
    ):
        raise JonesMysticLowerBoundaryValidationError("evidence lineage is invalid")
    tooling = pilot_checkpoint.get("tooling")
    if not isinstance(tooling, dict):
        raise JonesMysticLowerBoundaryValidationError("pilot tooling is missing")
    pilot_spec_path = _verify_receipt(REPO_ROOT, tooling.get("spec"), "pilot spec")
    if file_receipt(pilot_spec_path, relative_to=REPO_ROOT) != lineage[
        "corrected_v2_pilot_specification"
    ]:
        raise JonesMysticLowerBoundaryValidationError(
            "pilot specification lineage changed"
        )
    pilot_validator_path = _verify_receipt(
        REPO_ROOT, tooling.get("validator"), "pilot validator"
    )
    _verify_receipt(REPO_ROOT, tooling.get("builder"), "pilot builder")
    pilot_validator = _load_module(
        pilot_validator_path, "_moira_pilot_validator_for_lower_boundary_validation"
    )
    pilot_spec = pilot_validator._load_spec(pilot_spec_path)
    reserved = {case["case_id"]: case for case in pilot_spec["reserved_holdout_cases"]}
    if list(reserved) != spec["execution_protocol"]["case_ids"]:
        raise JonesMysticLowerBoundaryValidationError(
            "reserved holdout inventory changed"
        )
    expected_control = {row["case_id"]: row for row in holdout_checkpoint["measurements"]}
    if set(expected_control) != set(reserved):
        raise JonesMysticLowerBoundaryValidationError(
            "control measurement inventory changed"
        )
    return {
        "spec": spec,
        "spec_path": spec_path,
        "lineage_paths": paths,
        "pilot_checkpoint": pilot_checkpoint,
        "threshold_checkpoint": threshold_checkpoint,
        "holdout_checkpoint": holdout_checkpoint,
        "pilot_spec": pilot_spec,
        "pilot_spec_path": pilot_spec_path,
        "pilot_validator": pilot_validator,
        "reserved": reserved,
        "expected_control": expected_control,
    }


def _read_tar_member(archive: Path, receipt: dict[str, Any], label: str) -> bytes:
    try:
        with tarfile.open(archive, "r:*") as bundle:
            member = bundle.getmember(receipt["path"])
            stream = bundle.extractfile(member)
            payload = stream.read() if stream is not None else b""
    except (OSError, KeyError, tarfile.TarError) as exc:
        raise JonesMysticLowerBoundaryValidationError(
            f"cannot read {label} member"
        ) from exc
    if (
        len(payload) != receipt.get("bytes")
        or sha256_bytes(payload) != receipt.get("sha256")
    ):
        raise JonesMysticLowerBoundaryValidationError(
            f"{label} member receipt differs"
        )
    return payload


def _parse_assignments(payload: bytes) -> dict[str, float]:
    assignments = {}
    for raw_line in payload.decode("ascii").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            assignments[key.strip()] = float(value.strip())
        except ValueError:
            continue
    return assignments


def _verify_sources(
    manifest: dict[str, Any],
    contracts: dict[str, Any],
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
) -> dict[str, Any]:
    spec = contracts["spec"]
    pilot_spec = contracts["pilot_spec"]
    validator = contracts["pilot_validator"]
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise JonesMysticLowerBoundaryValidationError("generator receipt is missing")
    validator._verify_generator(
        manifest,
        pilot_spec,
        uvspec=uvspec,
        lib_radtran_archive=lib_radtran_archive,
        data_root=data_root,
    )
    semantics = spec["source_semantics"]
    _verify_external(
        lib_radtran_archive,
        semantics["libradtran_archive"],
        "libRadtran source archive",
    )
    if generator.get("libRadtran_members") != semantics["libradtran_members"]:
        raise JonesMysticLowerBoundaryValidationError(
            "libRadtran source-member receipts differ"
        )
    for receipt in semantics["libradtran_members"]:
        _read_tar_member(lib_radtran_archive, receipt, receipt["role"])
    _verify_external(eso_archive, semantics["eso_archive"], "ESO source archive")
    payloads = validator._read_eso_archive(eso_archive, pilot_spec)
    source = validator._parse_source_members(payloads)
    config_receipt = semantics["eso_model_configuration"]
    config = _parse_assignments(
        _read_tar_member(eso_archive, config_receipt, "ESO configuration")
    )
    for key, expected in config_receipt["required_assignments"].items():
        if not math.isclose(
            config.get(key, math.nan), float(expected), rel_tol=0.0, abs_tol=1e-15
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"ESO configuration assignment differs: {key}"
            )
    external = manifest.get("external_source")
    if (
        not isinstance(external, dict)
        or external.get("redistributed") is not False
        or external.get("model_configuration") != config_receipt
    ):
        raise JonesMysticLowerBoundaryValidationError(
            "external-source boundary differs"
        )
    _verify_external(eso_archive, external.get("archive"), "manifest ESO archive")
    if manifest.get("source_semantics") != semantics:
        raise JonesMysticLowerBoundaryValidationError("source semantics differ")
    derivations = manifest.get("source_derivations")
    expected_derivations = {
        "solar_irradiance_550nm_W_m-2_micrometre-1": source["solar"],
        "rolo_constant_coefficients": source["rolo_constants"],
        "rolo_interpolated_coefficients_550nm": source["rolo_coefficients"],
        "aod550": source["aod550"],
        "eso_required_assignments": {
            key: config[key] for key in config_receipt["required_assignments"]
        },
    }
    if derivations != expected_derivations:
        raise JonesMysticLowerBoundaryValidationError(
            "independent source derivations differ"
        )
    return source


def _expected_cases(contracts: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    protocol = contracts["spec"]["execution_protocol"]
    validator = contracts["pilot_validator"]
    base = []
    for case_id in protocol["case_ids"]:
        reserved = contracts["reserved"][case_id]
        case = {
            **reserved,
            "class": "lower_boundary_reserved_holdout_reuse",
            "target_moon_separation_deg": validator._separation(reserved),
            "photon_count": protocol["photon_count_per_run"],
            "random_seed": protocol["random_seed"],
        }
        base.append(case)
    candidate = [dict(case) for case in base]
    anchor = next(
        case for case in candidate if case["case_id"] == protocol["exact_repeat_case_id"]
    )
    candidate.append(
        {
            **anchor,
            "case_id": f"{anchor['case_id']}_candidate_repeat",
            "repeat_of": anchor["case_id"],
        }
    )
    return {CONTROL_PROFILE_ID: base, CANDIDATE_PROFILE_ID: candidate}


def _expected_run_files(
    contracts: dict[str, Any], profile_id: str
) -> frozenset[str]:
    stem = contracts["spec"]["profiles"][profile_id][
        "mystic_altitude_radiance_file_stem"
    ]
    return frozenset(
        (contracts["pilot_validator"].EXPECTED_RUN_FILES - {"mc0.rad", "mc0.rad.std"})
        | {f"{stem}.rad", f"{stem}.rad.std"}
    )


def _scientific_repeat_files(
    contracts: dict[str, Any], profile_id: str
) -> tuple[str, ...]:
    stem = contracts["spec"]["profiles"][profile_id][
        "mystic_altitude_radiance_file_stem"
    ]
    return tuple(
        f"{stem}{name.removeprefix('mc0')}" if name.startswith("mc0") else name
        for name in contracts["pilot_validator"].SCIENTIFIC_REPEAT_FILES
    )


def _expected_input(
    case: dict[str, Any], contracts: dict[str, Any], profile_id: str
) -> bytes:
    pilot_spec = contracts["pilot_spec"]
    site = dict(pilot_spec["site_and_atmosphere"])
    profile = contracts["spec"]["profiles"][profile_id]
    site["surface_pressure_hpa"] = profile["surface_pressure_hpa"]
    site["ozone_column_du"] = profile["ozone_column_du_above_surface"]
    wavelength = float(contracts["spec"]["execution_protocol"]["wavelength_nm"])
    viewing_umu = -math.sin(math.radians(float(case["target_true_altitude_deg"])))
    lunar_zenith = 90.0 - float(case["moon_true_altitude_deg"])
    cross_sections = site["cross_sections"]
    lines = [
        "data_files_path data",
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


def _expected_probe_input(contracts: dict[str, Any], profile_id: str) -> bytes:
    site = dict(contracts["pilot_spec"]["site_and_atmosphere"])
    profile = contracts["spec"]["profiles"][profile_id]
    site["surface_pressure_hpa"] = profile["surface_pressure_hpa"]
    site["ozone_column_du"] = profile["ozone_column_du_above_surface"]
    cross_sections = site["cross_sections"]
    lines = [
        "data_files_path data",
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


def _exact_profile(
    source_text: str, altitude_m: float, validator: Any
) -> tuple[bytes, dict[str, Any], bytes, dict[str, Any]]:
    altitude = validator._float32(altitude_m / 1000.0)
    rows = validator._parse_atmosphere(source_text)
    exact_index = next(
        (
            index
            for index, row in enumerate(rows)
            if math.isclose(row[0], altitude, rel_tol=0.0, abs_tol=1e-7)
        ),
        None,
    )
    if exact_index is not None:
        selected = [list(row) for row in rows[: exact_index + 1]]
        bracket = [rows[exact_index][0], rows[exact_index][0]]
        interpolated = False
    else:
        upper_index = next(
            index
            for index in range(len(rows) - 1)
            if rows[index][0] > altitude > rows[index + 1][0]
        )
        high = rows[upper_index]
        low = rows[upper_index + 1]
        pressure = validator._logarithmic(
            low[0], low[1], high[0], high[1], altitude
        )
        temperature = validator._linear(
            low[0], low[2], high[0], high[2], altitude
        )
        air = validator._logarithmic(low[0], low[3], high[0], high[3], altitude)
        bottom = [altitude, pressure, temperature, air]
        for column in range(4, 9):
            bottom.append(
                validator._linmix(
                    low[0],
                    low[column],
                    low[3],
                    high[0],
                    high[column],
                    high[3],
                    altitude,
                    air,
                )
            )
        selected = [list(row) for row in rows[: upper_index + 1]] + [bottom]
        bracket = [low[0], high[0]]
        interpolated = True
    header = [
        "# Moira Phase 1 elevated-site reference-lab atmosphere.",
        "# Source: libRadtran 2.0.6 data/atmmod/afglus.dat.",
        "# Construction: default z_interpolate LINMIX, binary32 staged.",
        "# z(km) p(hPa) T(K) air(cm-3) O3(cm-3) O2(cm-3) H2O(cm-3) CO2(cm-3) NO2(cm-3)",
    ]
    atmosphere = (
        "\n".join(
            header
            + [
                " ".join(validator._format_float32(value) for value in row)
                for row in selected
            ]
        )
        + "\n"
    ).encode("ascii")
    bottom = selected[-1]
    atmosphere_metadata = {
        "site_altitude_m": float(altitude_m),
        "site_altitude_km": bottom[0],
        "interpolated_bottom_level": interpolated,
        "bracketing_altitude_km": bracket,
        "level_count": len(selected),
        "bottom_level": {
            "altitude_km": bottom[0],
            "pressure_hpa": bottom[1],
            "temperature_k": bottom[2],
            "air_number_density_cm-3": bottom[3],
            "o3_number_density_cm-3": bottom[4],
            "o2_number_density_cm-3": bottom[5],
            "h2o_number_density_cm-3": bottom[6],
            "co2_number_density_cm-3": bottom[7],
            "no2_number_density_cm-3": bottom[8],
        },
    }

    o4_source = [
        [row[0], validator._float32((float(row[5]) * 1e-23) ** 2), row[3]]
        for row in rows
    ]
    if exact_index is not None:
        selected_o4 = [list(row) for row in o4_source[: exact_index + 1]]
        o4_bracket = [o4_source[exact_index][0], o4_source[exact_index][0]]
        o4_interpolated = False
    else:
        high_o4 = o4_source[upper_index]
        low_o4 = o4_source[upper_index + 1]
        o4_air = validator._logarithmic(
            low_o4[0], low_o4[2], high_o4[0], high_o4[2], altitude
        )
        o4_value = validator._linmix(
            low_o4[0],
            low_o4[1],
            low_o4[2],
            high_o4[0],
            high_o4[1],
            high_o4[2],
            altitude,
            o4_air,
        )
        selected_o4 = [list(row) for row in o4_source[: upper_index + 1]] + [
            [altitude, o4_value, o4_air]
        ]
        o4_bracket = [low_o4[0], high_o4[0]]
        o4_interpolated = True
    o4_header = [
        "# Moira Phase 1 elevated-site reference-lab O4 companion.",
        "# Reproduces libRadtran 2.0.6 preinterpolation O4 pseudo-density.",
        "# z(km) O4_scaled_density(cm-3)",
    ]
    o4 = (
        "\n".join(
            o4_header
            + [
                f"{validator._format_float32(row[0])} "
                f"{validator._format_float32(row[1])}"
                for row in selected_o4
            ]
        )
        + "\n"
    ).encode("ascii")
    o4_metadata = {
        "site_altitude_m": float(altitude_m),
        "site_altitude_km": selected_o4[-1][0],
        "interpolated_bottom_level": o4_interpolated,
        "bracketing_altitude_km": o4_bracket,
        "level_count": len(selected_o4),
        "bottom_scaled_o4_density_cm-3": selected_o4[-1][1],
    }
    return atmosphere, atmosphere_metadata, o4, o4_metadata


def _data_rows(payload: bytes, columns: int) -> list[list[float]]:
    rows = []
    for line in payload.decode("ascii").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            values = [float(token) for token in stripped.split()]
            if len(values) != columns:
                raise JonesMysticLowerBoundaryValidationError(
                    "profile row shape differs"
                )
            rows.append(values)
    return rows


def _join_profiles(observer: bytes, surface: bytes, columns: int) -> bytes:
    lines = observer.decode("ascii").splitlines()
    header = [line for line in lines if line.strip().startswith("#")]
    observer_rows = _data_rows(observer, columns)
    surface_rows = _data_rows(surface, columns)
    tail = [row for row in surface_rows if row[0] < observer_rows[-1][0] - 1e-7]
    combined = observer_rows + tail
    body = [" ".join(format(value, ".9g") for value in row) for row in combined]
    return ("\n".join(header + body) + "\n").encode("ascii")


def _shared_inventory(profile_root: Path, declared: dict[str, Any]) -> None:
    shared = profile_root / "shared"
    receipts = declared.get("files")
    if not shared.is_dir() or shared.is_symlink() or not isinstance(receipts, list):
        raise JonesMysticLowerBoundaryValidationError(
            "shared input inventory is invalid"
        )
    declared_names = set()
    for index, receipt in enumerate(receipts):
        path = _verify_receipt(profile_root, receipt, f"shared file {index}")
        if path.parent != shared or path.name in declared_names:
            raise JonesMysticLowerBoundaryValidationError(
                "shared receipt inventory is noncanonical"
            )
        declared_names.add(path.name)
    actual_names = {path.name for path in shared.iterdir() if path.is_file()}
    if declared_names != actual_names or any(path.is_symlink() for path in shared.iterdir()):
        raise JonesMysticLowerBoundaryValidationError("shared inventory differs")


def _candidate_boundaries(pilot_spec: dict[str, Any]) -> tuple[list[float], list[float]]:
    aerosol = pilot_spec["aerosol"]
    control = [float(aerosol["profile_bottom_km"])]
    top = float(aerosol["profile_top_km"])
    step = float(aerosol["nominal_layer_thickness_km"])
    while control[-1] + step < top - 1e-12:
        control.append(round(control[-1] + step, 12))
    control.append(top)
    return control, [2.0, 2.25, 2.5, 2.64] + control[1:]


def _expected_candidate_shared(
    profile_root: Path,
    contracts: dict[str, Any],
    source: dict[str, Any],
    data_root: Path,
) -> dict[str, Any]:
    validator = contracts["pilot_validator"]
    pilot_spec = contracts["pilot_spec"]
    candidate = contracts["spec"]["profiles"][CANDIDATE_PROFILE_ID]
    source_path = data_root / pilot_spec["site_and_atmosphere"][
        "atmosphere_source_path"
    ].removeprefix("data/")
    source_text = source_path.read_text(encoding="ascii")
    atm_2640, atm_2640_meta, o4_2640, o4_2640_meta = _exact_profile(
        source_text, 2640.0, validator
    )
    atm_2000, atm_2000_meta, o4_2000, o4_2000_meta = _exact_profile(
        source_text, 2000.0, validator
    )
    atmosphere = _join_profiles(atm_2640, atm_2000, 9)
    o4 = _join_profiles(o4_2640, o4_2000, 2)
    shared = profile_root / "shared"
    if (shared / "atmosphere.dat").read_bytes() != atmosphere:
        raise JonesMysticLowerBoundaryValidationError(
            "candidate atmosphere bytes differ"
        )
    if (shared / "o4.dat").read_bytes() != o4:
        raise JonesMysticLowerBoundaryValidationError("candidate O4 bytes differ")

    aerosol = pilot_spec["aerosol"]
    moments, representation = validator._moments_and_diagnostics(
        source["phase_values"],
        aerosol["legendre_moment_count"],
        aerosol["gauss_legendre_quadrature_order"],
    )
    moment_text = " ".join(format(value, ".17e") for value in moments)
    control_boundaries, boundaries = _candidate_boundaries(pilot_spec)
    layers = []
    reference = float(candidate["aerosol_normalization_reference_km"])
    scale = float(candidate["aerosol_scale_height_km"])
    reference_aod = float(candidate["observer_to_infinite_top_aod550"])
    for index, (low, high) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        extinction = reference_aod * (
            math.exp(-(low - reference) / scale)
            - math.exp(-(high - reference) / scale)
        ) / (high - low)
        filename = f"aerosol_layer_{index:03d}.dat"
        expected = (
            "\n".join(
                f"{float(wavelength):.1f} {extinction:.17e} "
                f"{float(aerosol['single_scattering_albedo']):.17g} {moment_text}"
                for wavelength in aerosol["explicit_file_wavelength_grid_nm"]
            )
            + "\n"
        ).encode("ascii")
        if (shared / filename).read_bytes() != expected:
            raise JonesMysticLowerBoundaryValidationError(
                f"candidate aerosol layer differs: {filename}"
            )
        layers.append(
            {
                "index": index,
                "low_km": low,
                "high_km": high,
                "extinction_km-1": extinction,
                "filename": filename,
            }
        )
    profile_lines = [
        f"{float(aerosol['null_top_boundary_km']):.8f} ../../shared/null_layer.dat",
        f"{float(candidate['aerosol_profile_top_km']):.8f} ../../shared/null_layer.dat",
    ] + [
        f"{float(layer['low_km']):.8f} ../../shared/{layer['filename']}"
        for layer in reversed(layers)
    ]
    if (shared / "aerosol_profile.dat").read_bytes() != (
        "\n".join(profile_lines) + "\n"
    ).encode("ascii"):
        raise JonesMysticLowerBoundaryValidationError(
            "candidate aerosol profile differs"
        )
    if (shared / "null_layer.dat").read_bytes() != b"100 0 1 1\n100000 0 1 1\n":
        raise JonesMysticLowerBoundaryValidationError(
            "candidate null aerosol layer differs"
        )
    integrated = sum(
        float(layer["extinction_km-1"])
        * (float(layer["high_km"]) - float(layer["low_km"]))
        for layer in layers
    )
    above = [layer for layer in layers if float(layer["low_km"]) >= 2.64]
    expected = {
        "atmosphere": {
            "surface_construction": atm_2000_meta,
            "observer_construction": atm_2640_meta,
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
            "above_observer_layer_count": len(above),
            "below_observer_layer_count": len(layers) - len(above),
            "explicit_profile_layout": aerosol["explicit_profile_layout"],
            "uppermost_marker_km": float(aerosol["null_top_boundary_km"]),
            "lowest_physical_layer_boundary_km": 2.0,
            "integrated_aod_to_profile_top": integrated,
            "observer_to_profile_top_aod": sum(
                float(layer["extinction_km-1"])
                * (float(layer["high_km"]) - float(layer["low_km"]))
                for layer in above
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
            file_receipt(path, relative_to=profile_root)
            for path in sorted(shared.iterdir())
            if path.is_file()
        ],
    }
    return expected


def _verify_shared(
    profile_root: Path,
    profile_entry: dict[str, Any],
    contracts: dict[str, Any],
    source: dict[str, Any],
    data_root: Path,
    profile_id: str,
) -> dict[str, Any]:
    receipt_path = _verify_receipt(
        profile_root.parent.parent,
        profile_entry.get("shared_metadata"),
        f"{profile_id} shared metadata",
    )
    declared = _read_json(receipt_path, f"{profile_id} shared metadata")
    if declared != profile_entry.get("shared_inputs"):
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} shared metadata differs"
        )
    _shared_inventory(profile_root, declared)
    if profile_id == CONTROL_PROFILE_ID:
        contracts["pilot_validator"]._verify_shared(
            profile_root,
            {"shared_inputs": declared},
            contracts["pilot_spec"],
            source,
            data_root,
        )
    else:
        expected = _expected_candidate_shared(
            profile_root, contracts, source, data_root
        )
        if declared != expected:
            raise JonesMysticLowerBoundaryValidationError(
                "candidate shared metadata differs from independent reconstruction"
            )
    return declared


def _verify_probe(
    profile_root: Path,
    declared: dict[str, Any],
    contracts: dict[str, Any],
    profile_id: str,
) -> dict[str, Any]:
    probe = profile_root / "profile-probe"
    if (
        not probe.is_dir()
        or probe.is_symlink()
        or {path.name for path in probe.iterdir()}
        != {"input.inp", "stdout.txt", "stderr.txt"}
        or any(path.is_symlink() for path in probe.iterdir())
    ):
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} profile-probe inventory differs"
        )
    if (probe / "input.inp").read_bytes() != _expected_probe_input(
        contracts, profile_id
    ):
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} profile-probe input differs"
        )
    rows = [
        line.split()
        for line in (probe / "stdout.txt").read_text(encoding="ascii").splitlines()
        if line
    ]
    if len(rows) != 1 or len(rows[0]) != 3:
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} profile-probe output differs"
        )
    values = [float(value) for value in rows[0]]
    expected = {
        "profile_id": profile_id,
        "observer_altitude_km": values[0],
        "observer_pressure_hpa": values[1],
        "observer_o3_number_density_cm-3": values[2],
        "files": [
            file_receipt(path, relative_to=profile_root)
            for path in sorted(probe.iterdir())
            if path.is_file()
        ],
    }
    if declared != expected:
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} profile-probe receipt differs"
        )
    return expected


def _verify_runs(
    profile_root: Path,
    declared: Any,
    contracts: dict[str, Any],
    source: dict[str, Any],
    profile_id: str,
    expected_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    validator = contracts["pilot_validator"]
    if not isinstance(declared, list) or len(declared) != len(expected_cases):
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} run count differs"
        )
    runs = profile_root / "runs"
    expected_by_id = {case["case_id"]: case for case in expected_cases}
    actual_by_id = {
        row.get("case_id"): row for row in declared if isinstance(row, dict)
    }
    if (
        not runs.is_dir()
        or runs.is_symlink()
        or set(actual_by_id) != set(expected_by_id)
        or {path.name for path in runs.iterdir() if path.is_dir()}
        != set(expected_by_id)
    ):
        raise JonesMysticLowerBoundaryValidationError(
            f"{profile_id} run inventory differs"
        )
    checked = []
    for expected_case in expected_cases:
        case_id = expected_case["case_id"]
        declared_row = actual_by_id[case_id]
        run = runs / case_id
        expected_scientific_files = _expected_run_files(contracts, profile_id)
        expected_names = set(expected_scientific_files) | {"case.json"}
        if (
            {path.name for path in run.iterdir()} != expected_names
            or any(path.is_symlink() for path in run.iterdir())
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} file inventory differs"
            )
        case_path = _verify_receipt(
            profile_root,
            declared_row.get("case_manifest"),
            f"{profile_id}/{case_id} case manifest",
        )
        case_manifest = _read_json(case_path, f"{profile_id}/{case_id} case manifest")
        if (
            case_manifest.get("schema") != CASE_SCHEMA
            or case_manifest.get("profile_id") != profile_id
            or case_manifest.get("case") != expected_case
            or declared_row.get("case") != expected_case
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} case contract differs"
            )
        receipts = case_manifest.get("files")
        if not isinstance(receipts, list) or len(receipts) != len(
            expected_scientific_files
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} file receipts differ"
            )
        receipt_names = set()
        for index, receipt in enumerate(receipts):
            path = _verify_receipt(
                profile_root, receipt, f"{profile_id}/{case_id} file {index}"
            )
            if path.parent != run or path.name in receipt_names:
                raise JonesMysticLowerBoundaryValidationError(
                    f"{profile_id}/{case_id} file receipt is noncanonical"
                )
            receipt_names.add(path.name)
        if receipt_names != set(expected_scientific_files):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} scientific file receipts differ"
            )
        if (run / "input.inp").read_bytes() != _expected_input(
            expected_case, contracts, profile_id
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} input differs"
            )
        lunar = validator._lunar_source(
            expected_case, source, contracts["pilot_spec"]
        )
        lunar_bytes = (run / "lunar_source.dat").read_bytes()
        lunar_rows = [
            [float(token) for token in line.split()]
            for line in lunar_bytes.decode("ascii").splitlines()
            if line
        ]
        if (
            b"\r" in lunar_bytes
            or len(lunar_rows) != 3
            or any(len(row) != 2 for row in lunar_rows)
            or any(
                not math.isclose(
                    row[0], float(wavelength), rel_tol=0.0, abs_tol=1e-12
                )
                or not math.isclose(
                    row[1],
                    lunar["toa_lunar_irradiance_W_m-2_nm-1"],
                    rel_tol=0.0,
                    abs_tol=1e-20,
                )
                for row, wavelength in zip(
                    lunar_rows,
                    contracts["pilot_spec"]["lunar_source"][
                        "source_file_grid_nm"
                    ],
                    strict=True,
                )
            )
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} lunar source differs"
            )
        radiance = validator._parse_directional(run / "mc.rad.spc")
        standard_error = validator._parse_directional(run / "mc.rad.std.spc")
        derived = case_manifest.get("derived")
        if (
            not isinstance(derived, dict)
            or declared_row.get("derived") != derived
            or declared_row.get("profile_id") != profile_id
            or set(derived)
            != {
                "target_moon_separation_deg",
                "disk_equivalent_albedo",
                "toa_lunar_irradiance_W_m-2_nm-1",
                "directional_radiance_W_m-2_nm-1_sr-1",
                "directional_standard_error_W_m-2_nm-1_sr-1",
                "relative_monte_carlo_standard_error",
            }
            or not math.isclose(
                derived["target_moon_separation_deg"],
                validator._separation(expected_case),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            or not math.isclose(
                derived["disk_equivalent_albedo"],
                lunar["disk_equivalent_albedo"],
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or not math.isclose(
                derived["toa_lunar_irradiance_W_m-2_nm-1"],
                lunar["toa_lunar_irradiance_W_m-2_nm-1"],
                rel_tol=0.0,
                abs_tol=1e-20,
            )
            or derived["directional_radiance_W_m-2_nm-1_sr-1"] != radiance
            or derived["directional_standard_error_W_m-2_nm-1_sr-1"]
            != standard_error
            or derived["relative_monte_carlo_standard_error"]
            != standard_error / radiance
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id}/{case_id} derived evidence differs"
            )
        checked.append(declared_row)
    return checked


def _recompute_diagnostics(
    artifact_root: Path,
    contracts: dict[str, Any],
    results: dict[str, list[dict[str, Any]]],
    probes: dict[str, dict[str, Any]],
    shared: dict[str, dict[str, Any]],
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
        c0 = control[case_id]["derived"]
        c1 = candidate[case_id]["derived"]
        r0 = c0["directional_radiance_W_m-2_nm-1_sr-1"]
        r1 = c1["directional_radiance_W_m-2_nm-1_sr-1"]
        combined = math.hypot(
            c0["directional_standard_error_W_m-2_nm-1_sr-1"],
            c1["directional_standard_error_W_m-2_nm-1_sr-1"],
        )
        measurements.append(
            {
                "case_id": case_id,
                "control_directional_radiance_W_m-2_nm-1_sr-1": r0,
                "control_directional_standard_error_W_m-2_nm-1_sr-1": c0[
                    "directional_standard_error_W_m-2_nm-1_sr-1"
                ],
                "control_relative_standard_error": c0[
                    "relative_monte_carlo_standard_error"
                ],
                "candidate_directional_radiance_W_m-2_nm-1_sr-1": r1,
                "candidate_directional_standard_error_W_m-2_nm-1_sr-1": c1[
                    "directional_standard_error_W_m-2_nm-1_sr-1"
                ],
                "candidate_relative_standard_error": c1[
                    "relative_monte_carlo_standard_error"
                ],
                "candidate_to_control_radiance_ratio": r1 / r0,
                "candidate_relative_change": r1 / r0 - 1.0,
                "candidate_minus_control_magnitude": -2.5 * math.log10(r1 / r0),
                "combined_monte_carlo_standard_error_W_m-2_nm-1_sr-1": combined,
                "candidate_control_difference_z_score": (r1 - r0) / combined,
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
    anchor = protocol["exact_repeat_case_id"]
    repeat = f"{anchor}_candidate_repeat"
    repeat_files = {
        name: (
            artifact_root
            / "profiles"
            / CANDIDATE_PROFILE_ID
            / "runs"
            / anchor
            / name
        ).read_bytes()
        == (
            artifact_root
            / "profiles"
            / CANDIDATE_PROFILE_ID
            / "runs"
            / repeat
            / name
        ).read_bytes()
        for name in _scientific_repeat_files(contracts, CANDIDATE_PROFILE_ID)
    }
    unique = results[CONTROL_PROFILE_ID] + [
        row for row in results[CANDIDATE_PROFILE_ID] if "repeat_of" not in row["case"]
    ]
    maximum_rse = max(
        row["derived"]["relative_monte_carlo_standard_error"] for row in unique
    )
    control_probe = probes[CONTROL_PROFILE_ID]
    candidate_probe = probes[CANDIDATE_PROFILE_ID]
    candidate_shared = shared[CANDIDATE_PROFILE_ID]
    checks = {
        "control_exactly_reproduces_corrected_v2_holdout_checkpoint": control_exact,
        "all_directional_outputs_finite_positive": all(
            math.isfinite(row["derived"]["directional_radiance_W_m-2_nm-1_sr-1"])
            and row["derived"]["directional_radiance_W_m-2_nm-1_sr-1"] > 0.0
            and math.isfinite(
                row["derived"]["directional_standard_error_W_m-2_nm-1_sr-1"]
            )
            and row["derived"]["directional_standard_error_W_m-2_nm-1_sr-1"] > 0.0
            for row in unique
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
            "anchor_case_id": anchor,
            "repeat_case_id": repeat,
            "byte_identical_files": repeat_files,
            "passed": all(repeat_files.values()),
        },
        "candidate_numerical_difference_used_for_model_selection": False,
        "checks": checks,
        "all_lower_boundary_checks_passed": all(checks.values()),
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
    }


def _verify_tooling(manifest: dict[str, Any], contracts: dict[str, Any]) -> None:
    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict):
        raise JonesMysticLowerBoundaryValidationError("tooling receipts are missing")
    expected = {
        "spec": contracts["spec_path"],
        "builder": BUILDER_PATH,
        "validator": Path(__file__).resolve(),
    }
    for role, path in expected.items():
        receipt_path = _verify_receipt(REPO_ROOT, tooling.get(role), f"tooling {role}")
        if receipt_path.resolve() != path.resolve():
            raise JonesMysticLowerBoundaryValidationError(
                f"tooling {role} path differs"
            )
    if (
        tooling.get("pilot_builder")
        != contracts["pilot_checkpoint"]["tooling"]["builder"]
        or tooling.get("pilot_validator")
        != contracts["pilot_checkpoint"]["tooling"]["validator"]
        or tooling.get("elevated_atmosphere_constructor")
        != contracts["spec"]["lineage"]["elevated_atmosphere_constructor"]
    ):
        raise JonesMysticLowerBoundaryValidationError(
            "bound tooling lineage differs"
        )


def _expected_checkpoint(
    artifact_root: Path,
    manifest: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    passed = diagnostics["all_lower_boundary_checks_passed"]
    return {
        "schema": CHECKPOINT_SCHEMA,
        "status": manifest["status"],
        "experiment_id": manifest["experiment_id"],
        "candidate_model_id": manifest["candidate_model_id"],
        "pilot_model_id": manifest["pilot_model_id"],
        "artifact_manifest": file_receipt(artifact_root / MANIFEST_NAME),
        "tooling": manifest["tooling"],
        "lineage": manifest["lineage"],
        "source_semantics": manifest["source_semantics"],
        "pre_admission_execution_history": manifest[
            "pre_admission_execution_history"
        ],
        "profile_contracts": {
            profile_id: manifest["profiles"][profile_id]["contract"]
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
        "candidate_fixed_seed_repeat": diagnostics["candidate_fixed_seed_repeat"],
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


def validate_artifact(
    artifact_root: Path,
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    if os.name != "posix":
        raise JonesMysticLowerBoundaryValidationError(
            "the lower-boundary artifact must be validated in the POSIX lab"
        )
    contracts = _load_contracts(spec_path)
    if (
        not artifact_root.is_dir()
        or artifact_root.is_symlink()
        or {path.name for path in artifact_root.iterdir()}
        != {"profiles", MANIFEST_NAME, CHECKPOINT_NAME}
    ):
        raise JonesMysticLowerBoundaryValidationError(
            "artifact top-level inventory differs"
        )
    manifest = _read_json(artifact_root / MANIFEST_NAME, "artifact manifest")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("experiment_id") != contracts["spec"]["experiment_id"]
        or manifest.get("candidate_model_id")
        != contracts["spec"]["candidate_model_id"]
        or manifest.get("pilot_model_id") != contracts["spec"]["pilot_model_id"]
        or manifest.get("wavelength_nm") != 550.0
        or manifest.get("lineage") != contracts["spec"]["lineage"]
        or manifest.get("pre_admission_execution_history")
        != contracts["spec"]["pre_admission_execution_history"]
    ):
        raise JonesMysticLowerBoundaryValidationError("artifact identity differs")
    for key in (
        "candidate_absolute_radiance_expectations_prefrozen",
        "candidate_control_difference_threshold_prefrozen",
        "candidate_numerical_difference_used_for_model_selection",
        "spectral_grid_admitted",
        "production_admission_allowed",
        "runtime_model_admitted",
        "runtime_dependency",
        "network_dependency",
        "external_source_bytes_redistributed",
    ):
        if manifest.get(key) is not False:
            raise JonesMysticLowerBoundaryValidationError(
                f"artifact boundary changed: {key}"
            )
    if manifest.get("source_authority_selects_profile") is not True:
        raise JonesMysticLowerBoundaryValidationError(
            "source-authority selection boundary changed"
        )
    _verify_tooling(manifest, contracts)
    source = _verify_sources(
        manifest,
        contracts,
        uvspec=uvspec,
        lib_radtran_archive=lib_radtran_archive,
        data_root=data_root,
        eso_archive=eso_archive,
    )
    profiles_root = artifact_root / "profiles"
    if (
        not profiles_root.is_dir()
        or profiles_root.is_symlink()
        or {path.name for path in profiles_root.iterdir() if path.is_dir()}
        != {CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID}
    ):
        raise JonesMysticLowerBoundaryValidationError("profile directories differ")
    profile_entries = manifest.get("profiles")
    if not isinstance(profile_entries, dict) or set(profile_entries) != {
        CONTROL_PROFILE_ID,
        CANDIDATE_PROFILE_ID,
    }:
        raise JonesMysticLowerBoundaryValidationError("profile manifest differs")
    expected_cases = _expected_cases(contracts)
    shared: dict[str, dict[str, Any]] = {}
    probes: dict[str, dict[str, Any]] = {}
    results: dict[str, list[dict[str, Any]]] = {}
    for profile_id in (CONTROL_PROFILE_ID, CANDIDATE_PROFILE_ID):
        profile_root = profiles_root / profile_id
        if (
            {path.name for path in profile_root.iterdir()}
            != {"shared", "shared-metadata.json", "profile-probe", "runs"}
            or profile_entries[profile_id].get("contract")
            != contracts["spec"]["profiles"][profile_id]
        ):
            raise JonesMysticLowerBoundaryValidationError(
                f"{profile_id} profile inventory differs"
            )
        shared[profile_id] = _verify_shared(
            profile_root,
            profile_entries[profile_id],
            contracts,
            source,
            data_root,
            profile_id,
        )
        probes[profile_id] = _verify_probe(
            profile_root,
            profile_entries[profile_id].get("profile_probe"),
            contracts,
            profile_id,
        )
        results[profile_id] = _verify_runs(
            profile_root,
            profile_entries[profile_id].get("runs"),
            contracts,
            source,
            profile_id,
            expected_cases[profile_id],
        )
    diagnostics = _recompute_diagnostics(
        artifact_root, contracts, results, probes, shared
    )
    if diagnostics != manifest.get("diagnostics"):
        raise JonesMysticLowerBoundaryValidationError(
            "independent diagnostics differ"
        )
    expected_status = (
        "source_faithful_lower_boundary_profile_verified_not_runtime_admitted"
        if diagnostics["all_lower_boundary_checks_passed"]
        else "lower_boundary_experiment_failed_not_runtime_admitted"
    )
    if manifest.get("status") != expected_status:
        raise JonesMysticLowerBoundaryValidationError("artifact status differs")
    checkpoint = _read_json(
        artifact_root / CHECKPOINT_NAME, "lower-boundary checkpoint"
    )
    if checkpoint != _expected_checkpoint(artifact_root, manifest, diagnostics):
        raise JonesMysticLowerBoundaryValidationError(
            "lower-boundary checkpoint differs"
        )
    return {
        "status": "valid",
        "experiment_id": contracts["spec"]["experiment_id"],
        "source_faithful_profile_id": checkpoint["source_faithful_profile_id"],
        "all_lower_boundary_checks_passed": checkpoint[
            "all_lower_boundary_checks_passed"
        ],
        "executed_run_count_with_candidate_repeat": 7,
        "next_gate": checkpoint["next_gate"],
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_model_admitted": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--lib-radtran-archive", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--eso-archive", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate_artifact(
            args.artifact_root,
            uvspec=args.uvspec,
            lib_radtran_archive=args.lib_radtran_archive,
            data_root=args.data_root,
            eso_archive=args.eso_archive,
            spec_path=args.spec,
        )
    except (JonesMysticLowerBoundaryValidationError, OSError) as exc:
        print(f"Jones/MYSTIC lower-boundary validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
