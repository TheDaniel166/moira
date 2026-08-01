#!/usr/bin/env python3
"""Build the checksum-bound Phase 4 Jones/MYSTIC 550 nm pilot.

This research tool is deliberately outside Moira's installed runtime. It
accepts only caller-supplied, checksum-locked libRadtran and ESO source inputs,
runs the frozen pilot matrix serially, and writes generated numerical evidence
to an external artifact directory. It never downloads data.
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
import statistics
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
    / "phase4_jones_mystic_pilot_spec.json"
)
VALIDATOR_PATH = (
    REPO_ROOT / "scripts" / "validate_visibility_phase4_jones_mystic_pilot.py"
)
ELEVATED_BUILDER_PATH = (
    REPO_ROOT / "scripts" / "build_visibility_elevated_site_probe.py"
)

SPEC_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-spec/v2"
ARTIFACT_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-artifact/v2"
CASE_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-case/v2"
CHECKPOINT_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-checkpoint/v2"
ARTIFACT_STATUS = "corrected_external_pilot_complete_not_runtime_data_pack"
DATA_LINK_NAME = "data"
MANIFEST_NAME = "artifact-manifest.json"
CHECKPOINT_NAME = "pilot-checkpoint.json"
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


class JonesMysticPilotError(ValueError):
    """Raised when the pilot specification or artifact violates its contract."""


def canonical_json_bytes(payload: object) -> bytes:
    """Return the canonical JSON representation used by this pilot."""
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
    return {
        "path": label,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def tree_receipt(path: Path) -> dict[str, Any]:
    """Hash a libRadtran data tree with the admitted Phase 1 receipt law."""
    if not path.is_dir():
        raise JonesMysticPilotError(f"libRadtran data root not found: {path}")
    members = sorted(
        member
        for member in path.rglob("*")
        if member.is_file()
        and not member.name.startswith("._")
        and member.name not in {"Makefile", "Makefile.in"}
    )
    if not members:
        raise JonesMysticPilotError(f"libRadtran data root is empty: {path}")
    digest = hashlib.sha256()
    total_bytes = 0
    for member in members:
        relative = member.relative_to(path).as_posix()
        member_bytes = member.stat().st_size
        member_hash = sha256_file(member)
        digest.update(f"{relative}\0{member_bytes}\0{member_hash}\n".encode("utf-8"))
        total_bytes += member_bytes
    return {
        "file_count": len(members),
        "bytes": total_bytes,
        "tree_sha256": digest.hexdigest(),
        "tree_hash_law": "sha256(relative_path_nul_bytes_nul_file_sha256_lf)",
        "excluded_names": ["._*", "Makefile", "Makefile.in"],
    }


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise JonesMysticPilotError(f"{label} must be a lowercase SHA-256")
    return value


def _require_number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JonesMysticPilotError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise JonesMysticPilotError(
            f"{label} must be finite and within [{low}, {high}]"
        )
    return result


def _safe_repo_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise JonesMysticPilotError(f"{label} must be a relative repository path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise JonesMysticPilotError(f"{label} escapes the repository")
    return REPO_ROOT.joinpath(*pure.parts)


def _verify_repo_receipt(receipt: dict[str, Any], label: str) -> Path:
    path = _safe_repo_path(receipt.get("path"), f"{label}.path")
    expected_bytes = receipt.get("bytes")
    expected_hash = _validate_sha256(receipt.get("sha256"), f"{label}.sha256")
    if not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise JonesMysticPilotError(f"{label}.bytes must be a positive integer")
    if (
        not path.is_file()
        or path.stat().st_size != expected_bytes
        or sha256_file(path) != expected_hash
    ):
        raise JonesMysticPilotError(f"repository receipt differs for {label}: {path}")
    return path


def target_moon_separation_deg(
    target_altitude_deg: float,
    moon_altitude_deg: float,
    relative_azimuth_deg: float,
) -> float:
    target_altitude = math.radians(target_altitude_deg)
    moon_altitude = math.radians(moon_altitude_deg)
    relative_azimuth = math.radians(relative_azimuth_deg)
    cosine = math.sin(target_altitude) * math.sin(moon_altitude) + math.cos(
        target_altitude
    ) * math.cos(moon_altitude) * math.cos(relative_azimuth)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def validate_case(case: dict[str, Any], *, runnable: bool) -> None:
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise JonesMysticPilotError("every pilot case requires a case_id")
    target = _require_number(
        case.get("target_true_altitude_deg"),
        f"{case_id}.target_true_altitude_deg",
        0.25,
        90.0,
    )
    moon = _require_number(
        case.get("moon_true_altitude_deg"),
        f"{case_id}.moon_true_altitude_deg",
        0.0,
        90.0,
    )
    azimuth = _require_number(
        case.get("relative_moon_azimuth_deg"),
        f"{case_id}.relative_moon_azimuth_deg",
        0.0,
        180.0,
    )
    phase = _require_number(
        case.get("lunar_phase_angle_deg"),
        f"{case_id}.lunar_phase_angle_deg",
        1.55,
        97.0,
    )
    del phase
    if case.get("waxing_state") not in {"waxing", "waning"}:
        raise JonesMysticPilotError(f"{case_id}.waxing_state is unsupported")
    _require_number(
        case.get("moon_earth_distance_ratio"),
        f"{case_id}.moon_earth_distance_ratio",
        0.91,
        1.08,
    )
    if runnable:
        if not isinstance(case.get("class"), str) or not case["class"]:
            raise JonesMysticPilotError(f"{case_id}.class is required")
        photon_count = case.get("photon_count")
        random_seed = case.get("random_seed")
        if (
            not isinstance(photon_count, int)
            or isinstance(photon_count, bool)
            or photon_count < 100000
            or photon_count > 1000000
        ):
            raise JonesMysticPilotError(f"{case_id}.photon_count is unsupported")
        if (
            not isinstance(random_seed, int)
            or isinstance(random_seed, bool)
            or not 0 < random_seed <= 2_147_483_647
        ):
            raise JonesMysticPilotError(f"{case_id}.random_seed is unsupported")
        declared = _require_number(
            case.get("target_moon_separation_deg"),
            f"{case_id}.target_moon_separation_deg",
            0.0,
            180.0,
        )
        calculated = target_moon_separation_deg(target, moon, azimuth)
        if not math.isclose(declared, calculated, rel_tol=0.0, abs_tol=1e-12):
            raise JonesMysticPilotError(
                f"{case_id} target-Moon separation is geometrically inconsistent"
            )


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != SPEC_SCHEMA:
        raise JonesMysticPilotError("unsupported Jones/MYSTIC pilot schema")
    if spec.get("status") != (
        "frozen_corrected_external_pilot_matrix_not_runtime_data_pack"
    ):
        raise JonesMysticPilotError("pilot must remain a frozen external matrix")
    if spec.get("pilot_model_id") != "jones_paranal_mystic_550nm_pilot_v2":
        raise JonesMysticPilotError("pilot model identity changed")
    correction = spec.get("correction_history")
    if (
        not isinstance(correction, dict)
        or correction.get("supersedes_pilot_model_id")
        != "jones_paranal_mystic_550nm_pilot_v1"
        or correction.get("reason")
        != "correct_libradtran_explicit_aerosol_layer_boundary_ownership"
    ):
        raise JonesMysticPilotError("pilot correction history is missing")
    _verify_repo_receipt(
        correction.get("invalidation_checkpoint"), "v1 invalidation checkpoint"
    )
    boundary = spec.get("runtime_boundary")
    if boundary != {
        "engine_changes_authorized": False,
        "public_api_changes_authorized": False,
        "runtime_table_authorized": False,
        "production_data_pack_authorized": False,
        "runtime_dependency_on_libRadtran": False,
        "runtime_dependency_on_eso_source_bytes": False,
        "network_dependency": False,
        "automatic_download_allowed": False,
        "external_source_bytes_redistributed": False,
        "generated_artifact_role": "external_phase4_validation_evidence_only",
    }:
        raise JonesMysticPilotError("pilot runtime boundary was weakened")

    governing = spec.get("governing_checkpoints")
    if not isinstance(governing, list) or len(governing) != 5:
        raise JonesMysticPilotError("five governing checkpoint receipts are required")
    roles: set[str] = set()
    for index, receipt in enumerate(governing):
        if not isinstance(receipt, dict):
            raise JonesMysticPilotError("governing receipt must be an object")
        role = receipt.get("role")
        if not isinstance(role, str) or not role or role in roles:
            raise JonesMysticPilotError("governing receipt roles must be unique")
        roles.add(role)
        _verify_repo_receipt(receipt, f"governing_checkpoints[{index}]")

    generator = spec.get("external_generators", {}).get("libRadtran")
    if not isinstance(generator, dict):
        raise JonesMysticPilotError("libRadtran generator lock is missing")
    if (
        generator.get("version") != "2.0.6"
        or generator.get("solver") != "MYSTIC"
        or generator.get("geometry") != "spherical_one_dimensional_atmosphere"
        or generator.get("uvspec_version") != "uvspec, version 2.0.6-MYSTIC"
    ):
        raise JonesMysticPilotError("libRadtran generator identity changed")
    _validate_sha256(generator.get("archive_sha256"), "libRadtran archive")
    _validate_sha256(generator.get("uvspec_sha256"), "uvspec executable")
    expected_tree = generator.get("data_root_receipt")
    if not isinstance(expected_tree, dict) or expected_tree.get("tree_hash_law") != (
        "sha256(relative_path_nul_bytes_nul_file_sha256_lf)"
    ):
        raise JonesMysticPilotError("libRadtran data-root receipt is invalid")
    _validate_sha256(expected_tree.get("tree_sha256"), "libRadtran data root")

    external = spec.get("external_source")
    if not isinstance(external, dict):
        raise JonesMysticPilotError("ESO external-source lock is missing")
    _validate_sha256(external.get("archive_sha256"), "ESO archive")
    required_members = external.get("required_members")
    if not isinstance(required_members, list) or len(required_members) != 8:
        raise JonesMysticPilotError("eight ESO source members are required")
    member_paths: set[str] = set()
    for index, receipt in enumerate(required_members):
        if not isinstance(receipt, dict):
            raise JonesMysticPilotError("ESO source receipt must be an object")
        path_text = receipt.get("path")
        if (
            not isinstance(path_text, str)
            or not path_text.startswith("SM-01/")
            or path_text in member_paths
            or not isinstance(receipt.get("bytes"), int)
            or receipt["bytes"] <= 0
        ):
            raise JonesMysticPilotError(
                f"invalid ESO source member receipt at index {index}"
            )
        member_paths.add(path_text)
        _validate_sha256(receipt.get("sha256"), f"ESO member {path_text}")

    site = spec.get("site_and_atmosphere")
    if (
        not isinstance(site, dict)
        or site.get("full_jones_reproduction_claimed") is not False
    ):
        raise JonesMysticPilotError("pilot design limitation must remain explicit")
    if site.get("pilot_design_limitation") != (
        "ground_and_atmosphere_bottom_are_at_the_2640m_observer_instead_of_"
        "the_Jones_2000m_lower_model_boundary"
    ):
        raise JonesMysticPilotError("pilot atmosphere limitation changed")
    _require_number(site.get("observer_altitude_m"), "observer_altitude_m", 2640, 2640)
    _require_number(site.get("surface_pressure_hpa"), "surface_pressure_hpa", 744, 744)
    _require_number(site.get("ozone_column_du"), "ozone_column_du", 258, 258)
    _require_number(site.get("ground_albedo_550nm"), "ground_albedo_550nm", 0, 1)

    aerosol = spec.get("aerosol")
    if not isinstance(aerosol, dict):
        raise JonesMysticPilotError("aerosol construction is missing")
    if (
        aerosol.get("legendre_moment_count") != 512
        or aerosol.get("gauss_legendre_quadrature_order") != 2048
        or aerosol.get("explicit_profile_layout")
        != "top_marker_then_null_gap_then_layer_files_at_lower_boundaries"
        or aerosol.get("layer_file_ownership")
        != "listed_altitude_inclusive_lower_boundary_to_next_higher_boundary"
        or aerosol.get("uppermost_marker_properties_ignored") is not True
        or aerosol.get("independent_aerosol_microphysics_reconstruction_claimed")
        is not False
        or aerosol.get("representation_error_status")
        != "measure_and_report_without_prefrozen_acceptance_threshold"
    ):
        raise JonesMysticPilotError("aerosol representation contract changed")
    _require_number(aerosol.get("aod550"), "aod550", 0.0294, 0.0294)
    _require_number(
        aerosol.get("single_scattering_albedo"),
        "single_scattering_albedo",
        0.97,
        0.97,
    )

    lunar = spec.get("lunar_source")
    if not isinstance(lunar, dict):
        raise JonesMysticPilotError("lunar-source construction is missing")
    if lunar.get("outside_empirical_phase_domain_policy") != "not_evaluable":
        raise JonesMysticPilotError("lunar phase-domain policy changed")

    cases = spec.get("pilot_cases")
    if not isinstance(cases, list) or len(cases) != 15:
        raise JonesMysticPilotError("the frozen pilot requires exactly 15 cases")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise JonesMysticPilotError("pilot case must be an object")
        validate_case(case, runnable=True)
        if case["case_id"] in case_ids:
            raise JonesMysticPilotError("pilot case IDs must be unique")
        case_ids.add(case["case_id"])
    repeats = [case for case in cases if "repeat_of" in case]
    if len(repeats) != 1 or repeats[0].get("repeat_of") != ("base_p300k_s49979687"):
        raise JonesMysticPilotError("the fixed-seed repeat anchor changed")

    holdouts = spec.get("reserved_holdout_cases")
    if not isinstance(holdouts, list) or len(holdouts) != 3:
        raise JonesMysticPilotError("three reserved holdout cases are required")
    holdout_ids: set[str] = set()
    for holdout in holdouts:
        if not isinstance(holdout, dict):
            raise JonesMysticPilotError("holdout case must be an object")
        validate_case(holdout, runnable=False)
        if holdout["case_id"] in holdout_ids or holdout["case_id"] in case_ids:
            raise JonesMysticPilotError(
                "holdout case IDs must remain sealed and unique"
            )
        holdout_ids.add(holdout["case_id"])

    gate = spec.get("pilot_gate")
    if not isinstance(gate, dict) or gate.get("acceptance_thresholds_status") != (
        "pilot_results_required_before_freeze"
    ):
        raise JonesMysticPilotError("pilot thresholds were prematurely frozen")
    if gate.get("production_admission_allowed") is not False:
        raise JonesMysticPilotError("pilot cannot authorize production admission")


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise JonesMysticPilotError("Jones/MYSTIC pilot spec must be an object")
    validate_spec(payload)
    return payload


def inspect_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(path)
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "pilot_model_id": spec["pilot_model_id"],
        "executed_case_count": len(spec["pilot_cases"]),
        "reserved_holdout_case_count": len(spec["reserved_holdout_cases"]),
        "wavelength_nm": spec["solver"]["wavelength_nm"],
        "acceptance_thresholds_status": spec["pilot_gate"][
            "acceptance_thresholds_status"
        ],
        "production_admission_allowed": spec["pilot_gate"][
            "production_admission_allowed"
        ],
        "runtime_dependency": False,
    }


def _verify_external_file(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise JonesMysticPilotError(f"{label} not found: {path}")
    receipt = file_receipt(path)
    if receipt["bytes"] != expected_bytes:
        raise JonesMysticPilotError(f"{label} byte count differs")
    if receipt["sha256"] != expected_sha256:
        raise JonesMysticPilotError(f"{label} SHA-256 differs")
    return receipt


def _read_eso_members(
    archive_path: Path,
    spec: dict[str, Any],
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    external = spec["external_source"]
    _verify_external_file(
        archive_path,
        expected_bytes=external["archive_bytes"],
        expected_sha256=external["archive_sha256"],
        label="ESO SM-01 archive",
    )
    payloads: dict[str, bytes] = {}
    receipts: list[dict[str, Any]] = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for expected in external["required_members"]:
            member = archive.getmember(expected["path"])
            if not member.isfile():
                raise JonesMysticPilotError(
                    f"ESO member is not a regular file: {expected['path']}"
                )
            stream = archive.extractfile(member)
            if stream is None:
                raise JonesMysticPilotError(
                    f"ESO member cannot be read: {expected['path']}"
                )
            payload = stream.read()
            if (
                len(payload) != expected["bytes"]
                or sha256_bytes(payload) != expected["sha256"]
            ):
                raise JonesMysticPilotError(
                    f"ESO member receipt differs: {expected['path']}"
                )
            payloads[expected["path"]] = payload
            receipts.append(
                {
                    "path": expected["path"],
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    "role": expected["role"],
                    "redistributed": False,
                }
            )
    return payloads, receipts


def _numeric_rows(payload: bytes) -> list[list[float]]:
    rows: list[list[float]] = []
    for raw_line in payload.decode("ascii").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append([float(token) for token in line.split()])
    return rows


def _linear_interpolate_rows(rows: list[list[float]], x: float) -> list[float]:
    if not rows or not rows[0][0] <= x <= rows[-1][0]:
        raise JonesMysticPilotError("interpolation point lies outside source table")
    for row in rows:
        if math.isclose(row[0], x, rel_tol=0.0, abs_tol=1e-15):
            return row[1:]
    for lower, upper in zip(rows, rows[1:], strict=False):
        if lower[0] < x < upper[0]:
            fraction = (x - lower[0]) / (upper[0] - lower[0])
            return [
                low + fraction * (high - low)
                for low, high in zip(lower[1:], upper[1:], strict=True)
            ]
    raise JonesMysticPilotError("source-table interpolation bracket was not found")


def parse_solar_irradiance_550(payload: bytes) -> float:
    rows = _numeric_rows(payload)
    if len(rows) != 1741 or any(len(row) != 2 for row in rows):
        raise JonesMysticPilotError("ESO solar spectrum shape differs")
    return _linear_interpolate_rows(rows, 0.55)[0]


def parse_rolo(payload: bytes) -> tuple[list[float], list[list[float]]]:
    rows = _numeric_rows(payload)
    if len(rows) != 34 or len(rows[0]) != 4 or rows[1] != [32.0]:
        raise JonesMysticPilotError("ROLO table shape differs")
    table = rows[2:]
    if len(table) != 32 or any(len(row) != 11 for row in table):
        raise JonesMysticPilotError("ROLO coefficient table shape differs")
    return rows[0], table


def parse_aod550(payload: bytes) -> float:
    rows = _numeric_rows(payload)
    if any(len(row) != 2 for row in rows):
        raise JonesMysticPilotError("Paranal aerosol-extinction table shape differs")
    return _linear_interpolate_rows(rows, 0.55)[0]


def parse_phase_function_550(payload: bytes) -> tuple[list[float], list[float]]:
    rows = _numeric_rows(payload)
    if len(rows) != 43 or rows[0] != [40.0, 181.0]:
        raise JonesMysticPilotError("ESO aerosol phase-function header differs")
    wavelengths = rows[1]
    angles = rows[2]
    values = rows[3:]
    if (
        len(wavelengths) != 40
        or len(angles) != 181
        or any(len(row) != 181 for row in values)
        or angles != [float(value) for value in range(181)]
    ):
        raise JonesMysticPilotError("ESO aerosol phase-function grid differs")
    index = next(
        (
            offset
            for offset, wavelength in enumerate(wavelengths)
            if math.isclose(wavelength, 0.55, rel_tol=0.0, abs_tol=1e-15)
        ),
        None,
    )
    if index is None:
        raise JonesMysticPilotError("ESO phase table omits 0.55 micrometre")
    return angles, values[index]


def lunar_source_flux_550(
    case: dict[str, Any],
    *,
    solar_irradiance: float,
    rolo_constants: list[float],
    rolo_coefficients: list[float],
    correction_divisor: float,
    moon_solid_angle_sr: float,
) -> dict[str, float]:
    phase_deg = float(case["lunar_phase_angle_deg"])
    phase_rad = math.radians(phase_deg)
    signed_phase_rad = phase_rad if case["waxing_state"] == "waxing" else -phase_rad
    distance = float(case["moon_earth_distance_ratio"])
    a0, a1, a2, a3, b1, b2, b3, d1, d2, d3 = rolo_coefficients
    p1, p2, p3, p4 = rolo_constants
    a_term = a0 + a1 * phase_rad + a2 * phase_rad**2 + a3 * phase_rad**3
    b_term = b1 * signed_phase_rad + b2 * signed_phase_rad**3 + b3 * signed_phase_rad**5
    d_term = (
        d1 * math.exp(-phase_deg / p1)
        + d2 * math.exp(-phase_deg / p2)
        + d3 * math.cos((phase_deg - p3) / p4)
    )
    disk_equivalent_albedo = math.exp(a_term + b_term + d_term) / correction_divisor
    flux = (
        solar_irradiance
        * disk_equivalent_albedo
        * moon_solid_angle_sr
        / math.pi
        / distance**2
        / 1000.0
    )
    return {
        "disk_equivalent_albedo": disk_equivalent_albedo,
        "toa_lunar_irradiance_W_m-2_nm-1": flux,
    }


def _gauss_legendre_nodes_weights(order: int) -> tuple[list[float], list[float]]:
    nodes = [0.0] * order
    weights = [0.0] * order
    half = (order + 1) // 2
    for index in range(half):
        root = math.cos(math.pi * (index + 0.75) / (order + 0.5))
        derivative = 0.0
        for _iteration in range(32):
            p_previous = 1.0
            p_current = root
            if order == 0:
                polynomial = p_previous
            elif order == 1:
                polynomial = p_current
            else:
                for degree in range(2, order + 1):
                    p_next = (
                        (2 * degree - 1) * root * p_current - (degree - 1) * p_previous
                    ) / degree
                    p_previous, p_current = p_current, p_next
                polynomial = p_current
            derivative = order * (root * polynomial - p_previous) / (root**2 - 1.0)
            updated = root - polynomial / derivative
            if abs(updated - root) <= 2e-16:
                root = updated
                break
            root = updated
        else:
            raise JonesMysticPilotError("Gauss-Legendre root solver did not converge")
        p_previous = 1.0
        p_current = root
        for degree in range(2, order + 1):
            p_next = (
                (2 * degree - 1) * root * p_current - (degree - 1) * p_previous
            ) / degree
            p_previous, p_current = p_current, p_next
        polynomial = p_current if order > 0 else p_previous
        derivative = order * (root * polynomial - p_previous) / (root**2 - 1.0)
        weight = 2.0 / ((1.0 - root**2) * derivative**2)
        nodes[index] = -root
        nodes[order - index - 1] = root
        weights[index] = weight
        weights[order - index - 1] = weight
    return nodes, weights


def _phase_value_at_mu(mu: float, phase_values: list[float]) -> float:
    angle = math.degrees(math.acos(max(-1.0, min(1.0, mu))))
    lower = min(179, int(math.floor(angle)))
    fraction = angle - lower
    if angle >= 180.0:
        return phase_values[180]
    return phase_values[lower] + fraction * (
        phase_values[lower + 1] - phase_values[lower]
    )


def compute_legendre_moments(
    phase_values: list[float],
    *,
    moment_count: int,
    quadrature_order: int,
) -> tuple[list[float], dict[str, float]]:
    nodes, weights = _gauss_legendre_nodes_weights(quadrature_order)
    raw = [0.0] * moment_count
    for mu, weight in zip(nodes, weights, strict=True):
        weighted_phase = 0.5 * weight * _phase_value_at_mu(mu, phase_values)
        p_previous = 1.0
        raw[0] += weighted_phase
        if moment_count == 1:
            continue
        p_current = mu
        raw[1] += weighted_phase * p_current
        for degree in range(2, moment_count):
            p_next = (
                (2 * degree - 1) * mu * p_current - (degree - 1) * p_previous
            ) / degree
            raw[degree] += weighted_phase * p_next
            p_previous, p_current = p_current, p_next
    normalization = raw[0]
    if not math.isfinite(normalization) or normalization <= 0.0:
        raise JonesMysticPilotError("phase-function normalization is invalid")
    moments = [value / normalization for value in raw]

    max_absolute_error = 0.0
    max_relative_error = 0.0
    for angle, expected in enumerate(phase_values):
        mu = math.cos(math.radians(angle))
        reconstructed = moments[0]
        p_previous = 1.0
        if moment_count > 1:
            p_current = mu
            reconstructed += 3.0 * moments[1] * p_current
            for degree in range(2, moment_count):
                p_next = (
                    (2 * degree - 1) * mu * p_current - (degree - 1) * p_previous
                ) / degree
                reconstructed += (2 * degree + 1) * moments[degree] * p_next
                p_previous, p_current = p_current, p_next
        absolute_error = abs(reconstructed - expected)
        relative_error = absolute_error / expected
        max_absolute_error = max(max_absolute_error, absolute_error)
        max_relative_error = max(max_relative_error, relative_error)
    diagnostics = {
        "raw_k0": normalization,
        "normalized_k0": moments[0],
        "normalized_k1": moments[1],
        "max_absolute_table_angle_reconstruction_error": max_absolute_error,
        "max_relative_table_angle_reconstruction_error": max_relative_error,
    }
    return moments, diagnostics


def _load_elevated_builder() -> Any:
    module_spec = importlib.util.spec_from_file_location(
        "_moira_phase4_elevated_atmosphere", ELEVATED_BUILDER_PATH
    )
    if module_spec is None or module_spec.loader is None:
        raise JonesMysticPilotError("cannot load elevated-atmosphere construction")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def render_explicit_aerosol_profile(
    layers: list[dict[str, float | str]],
    *,
    profile_top_km: float,
    null_top_boundary_km: float,
) -> bytes:
    """Serialize libRadtran layer ownership without shifting the profile."""
    if not layers:
        raise JonesMysticPilotError("explicit aerosol profile requires layers")
    if not null_top_boundary_km > profile_top_km:
        raise JonesMysticPilotError("null aerosol boundary must exceed profile top")
    for index, layer in enumerate(layers):
        low = float(layer["low_km"])
        high = float(layer["high_km"])
        if not high > low:
            raise JonesMysticPilotError("aerosol layer has non-positive thickness")
        if index and not math.isclose(
            low,
            float(layers[index - 1]["high_km"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise JonesMysticPilotError("aerosol layers are not contiguous")
    if not math.isclose(
        float(layers[-1]["high_km"]),
        profile_top_km,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise JonesMysticPilotError("aerosol layers do not reach profile top")

    # libRadtran applies a file from the listed altitude upward to the next
    # entry. The uppermost entry is only a marker and its file is ignored.
    lines = [
        f"{null_top_boundary_km:.8f} ../../shared/null_layer.dat",
        f"{profile_top_km:.8f} ../../shared/null_layer.dat",
    ]
    for layer in reversed(layers):
        lines.append(
            f"{float(layer['low_km']):.8f} ../../shared/{layer['filename']}"
        )
    return ("\n".join(lines) + "\n").encode("ascii")


def construct_shared_inputs(
    root: Path,
    *,
    spec: dict[str, Any],
    data_root: Path,
    phase_values: list[float],
) -> dict[str, Any]:
    shared = root / "shared"
    shared.mkdir()
    elevated = _load_elevated_builder()
    site = spec["site_and_atmosphere"]
    atmosphere_source = data_root / site["atmosphere_source_path"].removeprefix("data/")
    if not atmosphere_source.is_file():
        raise JonesMysticPilotError(
            f"AFGL atmosphere source not found: {atmosphere_source}"
        )
    source_text = atmosphere_source.read_text(encoding="ascii")
    atmosphere_bytes, atmosphere_metadata = elevated.construct_truncated_atmosphere(
        source_text, site["observer_altitude_m"]
    )
    o4_bytes, o4_metadata = elevated.construct_truncated_o4_profile(
        source_text, site["observer_altitude_m"]
    )
    (shared / "atmosphere.dat").write_bytes(atmosphere_bytes)
    (shared / "o4.dat").write_bytes(o4_bytes)

    aerosol = spec["aerosol"]
    moments, representation = compute_legendre_moments(
        phase_values,
        moment_count=aerosol["legendre_moment_count"],
        quadrature_order=aerosol["gauss_legendre_quadrature_order"],
    )
    moment_text = " ".join(format(value, ".17e") for value in moments)
    null_payload = b"100 0 1 1\n100000 0 1 1\n"
    (shared / "null_layer.dat").write_bytes(null_payload)

    bottom = float(aerosol["profile_bottom_km"])
    top = float(aerosol["profile_top_km"])
    step = float(aerosol["nominal_layer_thickness_km"])
    boundaries = [bottom]
    while boundaries[-1] + step < top - 1e-12:
        boundaries.append(round(boundaries[-1] + step, 12))
    boundaries.append(top)
    layers: list[dict[str, float | str]] = []
    for index, (low, high) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        extinction = (
            float(aerosol["aod550"])
            * (
                math.exp(-(low - bottom) / float(aerosol["vertical_scale_height_km"]))
                - math.exp(
                    -(high - bottom) / float(aerosol["vertical_scale_height_km"])
                )
            )
            / (high - low)
        )
        filename = f"aerosol_layer_{index:03d}.dat"
        rows = []
        for wavelength in aerosol["explicit_file_wavelength_grid_nm"]:
            rows.append(
                f"{float(wavelength):.1f} {extinction:.17e} "
                f"{float(aerosol['single_scattering_albedo']):.17g} {moment_text}"
            )
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
    profile_bytes = render_explicit_aerosol_profile(
        layers,
        profile_top_km=top,
        null_top_boundary_km=float(aerosol["null_top_boundary_km"]),
    )
    (shared / "aerosol_profile.dat").write_bytes(profile_bytes)
    integrated_aod = sum(
        float(layer["extinction_km-1"])
        * (float(layer["high_km"]) - float(layer["low_km"]))
        for layer in layers
    )
    shared_receipts = [
        file_receipt(path, relative_to=root)
        for path in sorted(shared.iterdir())
        if path.is_file()
    ]
    return {
        "atmosphere": atmosphere_metadata,
        "o4_companion": o4_metadata,
        "atmosphere_source": file_receipt(atmosphere_source),
        "aerosol": {
            "layer_count": len(layers),
            "boundaries_km": boundaries,
            "explicit_profile_layout": aerosol["explicit_profile_layout"],
            "uppermost_marker_km": float(aerosol["null_top_boundary_km"]),
            "null_gap_lower_boundary_km": top,
            "lowest_physical_layer_boundary_km": bottom,
            "layer_file_binding_count": len(layers),
            "integrated_aod_to_profile_top": integrated_aod,
            "unrepresented_aod_above_profile_top": float(aerosol["aod550"])
            - integrated_aod,
            "representation": representation,
            "normalized_moments_sha256": sha256_bytes(canonical_json_bytes(moments)),
        },
        "files": shared_receipts,
    }


def render_lunar_source(flux: float, spec: dict[str, Any]) -> bytes:
    rows = [
        f"{float(wavelength):.1f} {flux:.17e}"
        for wavelength in spec["lunar_source"]["source_file_grid_nm"]
    ]
    return ("\n".join(rows) + "\n").encode("ascii")


def render_input(case: dict[str, Any], spec: dict[str, Any]) -> bytes:
    site = spec["site_and_atmosphere"]
    wavelength = float(spec["solver"]["wavelength_nm"])
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
        "zout 0",
        f"umu {viewing_umu:.17g}",
        f"phi {float(case['relative_moon_azimuth_deg']):.17g}",
        "quiet",
    ]
    rendered = ("\n".join(lines) + "\n").encode("ascii")
    if b"\r" in rendered:
        raise JonesMysticPilotError("rendered libRadtran input is not LF-only")
    return rendered


def parse_directional_output(path: Path) -> float:
    rows = [
        line.split() for line in path.read_text(encoding="ascii").splitlines() if line
    ]
    if len(rows) != 1 or len(rows[0]) != 5:
        raise JonesMysticPilotError(f"unexpected directional output shape: {path}")
    wavelength = float(rows[0][0])
    value = float(rows[0][4])
    if not math.isclose(wavelength, 550.0, rel_tol=0.0, abs_tol=1e-6):
        raise JonesMysticPilotError(f"unexpected output wavelength: {path}")
    if not math.isfinite(value) or value <= 0.0:
        raise JonesMysticPilotError(
            f"directional output is not finite and positive: {path}"
        )
    return value


def _run_process(
    command: list[str],
    *,
    cwd: Path,
    input_bytes: bytes,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        check=False,
        capture_output=True,
    )


def run_case(
    case: dict[str, Any],
    *,
    root: Path,
    uvspec: Path,
    data_root: Path,
    spec: dict[str, Any],
    source_inputs: dict[str, Any],
) -> dict[str, Any]:
    run_dir = root / "runs" / case["case_id"]
    run_dir.mkdir(parents=True)
    source = lunar_source_flux_550(case, **source_inputs)
    lunar_bytes = render_lunar_source(source["toa_lunar_irradiance_W_m-2_nm-1"], spec)
    input_bytes = render_input(case, spec)
    (run_dir / "lunar_source.dat").write_bytes(lunar_bytes)
    (run_dir / "input.inp").write_bytes(input_bytes)
    data_link = run_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    try:
        syntax = _run_process([str(uvspec), "-c"], cwd=run_dir, input_bytes=input_bytes)
        (run_dir / "syntax.stdout.txt").write_bytes(syntax.stdout)
        (run_dir / "syntax.stderr.txt").write_bytes(syntax.stderr)
        if syntax.returncode != 0:
            raise JonesMysticPilotError(
                f"uvspec syntax check failed for {case['case_id']}: "
                f"{syntax.stderr.decode('utf-8', errors='replace')}"
            )
        executed = _run_process([str(uvspec)], cwd=run_dir, input_bytes=input_bytes)
        (run_dir / "stdout.txt").write_bytes(executed.stdout)
        (run_dir / "stderr.txt").write_bytes(executed.stderr)
        if executed.returncode != 0:
            raise JonesMysticPilotError(
                f"uvspec failed for {case['case_id']}: "
                f"{executed.stderr.decode('utf-8', errors='replace')}"
            )
    finally:
        if data_link.is_symlink():
            data_link.unlink()
    actual_names = {path.name for path in run_dir.iterdir() if path.is_file()}
    if actual_names != EXPECTED_RUN_FILES:
        missing = sorted(EXPECTED_RUN_FILES - actual_names)
        unexpected = sorted(actual_names - EXPECTED_RUN_FILES)
        raise JonesMysticPilotError(
            f"unexpected run inventory for {case['case_id']}; "
            f"missing={missing}, unexpected={unexpected}"
        )
    if any(path.is_symlink() for path in run_dir.iterdir()):
        raise JonesMysticPilotError("run directory retains a symlink")
    radiance = parse_directional_output(run_dir / "mc.rad.spc")
    standard_error = parse_directional_output(run_dir / "mc.rad.std.spc")
    files = [
        file_receipt(path, relative_to=root)
        for path in sorted(run_dir.iterdir())
        if path.is_file()
    ]
    case_manifest = {
        "schema": CASE_SCHEMA,
        "case": case,
        "derived": {
            "target_moon_separation_deg": target_moon_separation_deg(
                float(case["target_true_altitude_deg"]),
                float(case["moon_true_altitude_deg"]),
                float(case["relative_moon_azimuth_deg"]),
            ),
            **source,
            "directional_radiance_W_m-2_nm-1_sr-1": radiance,
            "directional_standard_error_W_m-2_nm-1_sr-1": standard_error,
            "relative_monte_carlo_standard_error": standard_error / radiance,
        },
        "files": files,
    }
    case_path = run_dir / "case.json"
    case_path.write_bytes(canonical_json_bytes(case_manifest))
    return {
        "case_id": case["case_id"],
        "case": case,
        "case_manifest": file_receipt(case_path, relative_to=root),
        "derived": case_manifest["derived"],
    }


def _verify_uvspec(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    generator = spec["external_generators"]["libRadtran"]
    if not path.is_file():
        raise JonesMysticPilotError(f"uvspec executable not found: {path}")
    if sha256_file(path) != generator["uvspec_sha256"]:
        raise JonesMysticPilotError("uvspec executable SHA-256 differs")
    version = subprocess.run(
        [str(path), "-v"], check=False, capture_output=True, text=True, encoding="utf-8"
    )
    version_text = (version.stdout + version.stderr).strip()
    if version.returncode != 0 or version_text != generator["uvspec_version"]:
        raise JonesMysticPilotError(
            f"uvspec version differs: returncode={version.returncode}, {version_text!r}"
        )
    build_root = path.parent.parent
    build_files = []
    for name in ("Makeconf", "config.log", "config.status"):
        build_file = build_root / name
        if not build_file.is_file():
            raise JonesMysticPilotError(
                f"libRadtran build receipt missing: {build_file}"
            )
        build_files.append(file_receipt(build_file))
    return {
        "path_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "version": version_text,
        "build_files": build_files,
    }


def summarize_cases(root: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {case["case_id"]: case for case in cases}
    repeat = by_id["base_p300k_s49979687_repeat"]
    anchor = by_id[repeat["case_id"].removesuffix("_repeat")]
    repeat_equal = {}
    for name in SCIENTIFIC_REPEAT_FILES:
        left = root / "runs" / anchor["case_id"] / name
        right = root / "runs" / repeat["case_id"] / name
        repeat_equal[name] = left.read_bytes() == right.read_bytes()
    if not all(repeat_equal.values()):
        raise JonesMysticPilotError("fixed-seed repeat is not byte-identical")

    convergence_ids = [
        "base_p100k_s49979687",
        "base_p300k_s49979687",
        "base_p1m_s49979687",
    ]
    convergence = []
    for case_id in convergence_ids:
        derived = by_id[case_id]["derived"]
        photon_count = by_id[case_id]["case"]["photon_count"]
        standard_error = derived["directional_standard_error_W_m-2_nm-1_sr-1"]
        convergence.append(
            {
                "case_id": case_id,
                "photon_count": photon_count,
                "radiance_W_m-2_nm-1_sr-1": derived[
                    "directional_radiance_W_m-2_nm-1_sr-1"
                ],
                "standard_error_W_m-2_nm-1_sr-1": standard_error,
                "relative_standard_error": derived[
                    "relative_monte_carlo_standard_error"
                ],
                "standard_error_times_sqrt_photons": standard_error
                * math.sqrt(photon_count),
            }
        )
    scaled = [row["standard_error_times_sqrt_photons"] for row in convergence]

    seed_ids = [
        "base_p300k_s49979687",
        "base_p300k_s67867967",
        "base_p300k_s86028121",
    ]
    seed_radiances = [
        by_id[case_id]["derived"]["directional_radiance_W_m-2_nm-1_sr-1"]
        for case_id in seed_ids
    ]
    reported_standard_errors = [
        by_id[case_id]["derived"]["directional_standard_error_W_m-2_nm-1_sr-1"]
        for case_id in seed_ids
    ]
    seed_mean = statistics.fmean(seed_radiances)
    return {
        "fixed_seed_repeat": {
            "anchor_case_id": anchor["case_id"],
            "repeat_case_id": repeat["case_id"],
            "byte_identical_files": repeat_equal,
            "passed": True,
        },
        "photon_count_convergence": {
            "measurements": convergence,
            "standard_error_sqrt_photon_scaled_max_to_min_ratio": max(scaled)
            / min(scaled),
            "acceptance_threshold_applied": False,
        },
        "multi_seed_spread": {
            "case_ids": seed_ids,
            "radiance_mean_W_m-2_nm-1_sr-1": seed_mean,
            "radiance_sample_standard_deviation_W_m-2_nm-1_sr-1": statistics.stdev(
                seed_radiances
            ),
            "radiance_sample_relative_standard_deviation": statistics.stdev(
                seed_radiances
            )
            / seed_mean,
            "mean_reported_standard_error_W_m-2_nm-1_sr-1": statistics.fmean(
                reported_standard_errors
            ),
            "acceptance_threshold_applied": False,
        },
    }


def _tooling_receipts(spec_path: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "spec": spec_path,
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH,
    }
    receipts = {}
    for role, path in paths.items():
        if not path.is_file():
            raise JonesMysticPilotError(f"pilot tooling is missing {role}: {path}")
        receipts[role] = file_receipt(path, relative_to=REPO_ROOT)
    return receipts


def _build_checkpoint(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    cases = manifest["cases"]
    relative_errors = [
        case["derived"]["relative_monte_carlo_standard_error"] for case in cases
    ]
    radiances = [
        case["derived"]["directional_radiance_W_m-2_nm-1_sr-1"] for case in cases
    ]
    return {
        "schema": CHECKPOINT_SCHEMA,
        "spec_id": manifest["spec_id"],
        "status": "corrected_v2_pilot_generated_thresholds_not_yet_frozen",
        "pilot_model_id": manifest["pilot_model_id"],
        "correction_history": manifest["correction_history"],
        "artifact_manifest": file_receipt(manifest_path),
        "tooling": manifest["tooling"],
        "generator": manifest["generator"],
        "external_source": {
            "archive": manifest["external_source"]["archive"],
            "member_count": len(manifest["external_source"]["members"]),
            "redistributed": False,
        },
        "executed_case_count": len(cases),
        "reserved_holdout_case_count": manifest["reserved_holdout_case_count"],
        "wavelength_nm": manifest["wavelength_nm"],
        "aerosol_representation": manifest["shared_inputs"]["aerosol"][
            "representation"
        ],
        "aerosol_integrated_aod_to_profile_top": manifest["shared_inputs"]["aerosol"][
            "integrated_aod_to_profile_top"
        ],
        "aerosol_explicit_profile_layout": manifest["shared_inputs"]["aerosol"][
            "explicit_profile_layout"
        ],
        "relative_monte_carlo_standard_error_range": [
            min(relative_errors),
            max(relative_errors),
        ],
        "directional_radiance_range_W_m-2_nm-1_sr-1": [
            min(radiances),
            max(radiances),
        ],
        "diagnostics": manifest["diagnostics"],
        "fixed_seed_repeat_passed": manifest["diagnostics"]["fixed_seed_repeat"][
            "passed"
        ],
        "acceptance_thresholds_frozen": False,
        "spectral_grid_admitted": False,
        "production_admission_allowed": False,
        "runtime_dependency": False,
        "network_dependency": False,
        "external_source_bytes_redistributed": False,
        "next_gate": (
            "review_corrected_v2_pilot_and_freeze_falsifiable_admission_thresholds"
        ),
    }


def build_pilot(
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
    output_root: Path,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    if os.name != "posix":
        raise JonesMysticPilotError(
            "the Jones/MYSTIC pilot must run in the POSIX libRadtran lab environment"
        )
    spec = load_spec(spec_path)
    if output_root.exists():
        raise JonesMysticPilotError(f"output root already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)

    generator_lock = spec["external_generators"]["libRadtran"]
    lib_archive_receipt = _verify_external_file(
        lib_radtran_archive,
        expected_bytes=generator_lock["archive_bytes"],
        expected_sha256=generator_lock["archive_sha256"],
        label="libRadtran source archive",
    )
    uvspec_receipt = _verify_uvspec(uvspec, spec)
    data_receipt = tree_receipt(data_root)
    if data_receipt != generator_lock["data_root_receipt"]:
        raise JonesMysticPilotError("libRadtran data-root receipt differs")
    eso_payloads, eso_member_receipts = _read_eso_members(eso_archive, spec)
    eso_archive_receipt = file_receipt(eso_archive)

    member_by_role = {
        receipt["role"]: eso_payloads[receipt["path"]]
        for receipt in spec["external_source"]["required_members"]
    }
    solar = parse_solar_irradiance_550(
        member_by_role["top_of_atmosphere_solar_spectrum"]
    )
    rolo_constants, rolo_table = parse_rolo(
        member_by_role["rolo_disk_equivalent_lunar_reflectance"]
    )
    rolo_coefficients = _linear_interpolate_rows(rolo_table, 550.0)
    aod550 = parse_aod550(member_by_role["paranal_aerosol_extinction"])
    _angles, phase_values = parse_phase_function_550(
        member_by_role["source_owned_aerosol_phase_function"]
    )
    lunar_spec = spec["lunar_source"]
    if not math.isclose(
        solar,
        lunar_spec["solar_irradiance_550nm_W_m-2_micrometre-1"],
        rel_tol=0.0,
        abs_tol=lunar_spec["source_interpolation_absolute_tolerance"],
    ):
        raise JonesMysticPilotError("550 nm solar interpolation differs from the spec")
    if any(
        not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15)
        for actual, expected in zip(
            rolo_coefficients,
            lunar_spec["rolo_interpolated_coefficients_550nm"],
            strict=True,
        )
    ):
        raise JonesMysticPilotError("550 nm ROLO interpolation differs from the spec")
    if not math.isclose(aod550, spec["aerosol"]["aod550"], rel_tol=0.0, abs_tol=1e-15):
        raise JonesMysticPilotError("550 nm aerosol extinction differs from the spec")
    ground = spec["site_and_atmosphere"]["ground_albedo_derivation"]
    ground_unadjusted = _linear_interpolate_rows(
        [
            [ground["wavelength_micrometre"][0], ground["uncorrected_reflectance"][0]],
            [ground["wavelength_micrometre"][1], ground["uncorrected_reflectance"][1]],
        ],
        ground["linear_interpolation_wavelength_micrometre"],
    )[0]
    calculated_ground = ground_unadjusted * ground["sutter_to_omi_correction"]
    if not math.isclose(
        calculated_ground,
        spec["site_and_atmosphere"]["ground_albedo_550nm"],
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise JonesMysticPilotError("550 nm ground-albedo derivation differs")

    source_inputs = {
        "solar_irradiance": solar,
        "rolo_constants": rolo_constants,
        "rolo_coefficients": rolo_coefficients,
        "correction_divisor": lunar_spec["rolo_correction_divisor"],
        "moon_solid_angle_sr": lunar_spec["moon_solid_angle_sr"],
    }
    base_source = lunar_source_flux_550(spec["pilot_cases"][0], **source_inputs)
    if not math.isclose(
        base_source["toa_lunar_irradiance_W_m-2_nm-1"],
        lunar_spec["base_case_flux_550nm_W_m-2_nm-1"],
        rel_tol=0.0,
        abs_tol=5e-21,
    ):
        raise JonesMysticPilotError("base lunar-source flux differs from the spec")

    temporary_path = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    try:
        shared_inputs = construct_shared_inputs(
            temporary_path,
            spec=spec,
            data_root=data_root,
            phase_values=phase_values,
        )
        case_results = []
        for case in spec["pilot_cases"]:
            print(
                f"running {case['case_id']} ({case['photon_count']} photons)",
                flush=True,
            )
            case_results.append(
                run_case(
                    case,
                    root=temporary_path,
                    uvspec=uvspec,
                    data_root=data_root,
                    spec=spec,
                    source_inputs=source_inputs,
                )
            )
        diagnostics = summarize_cases(temporary_path, case_results)
        manifest = {
            "schema": ARTIFACT_SCHEMA,
            "spec_id": spec["spec_id"],
            "status": ARTIFACT_STATUS,
            "pilot_model_id": spec["pilot_model_id"],
            "correction_history": spec["correction_history"],
            "wavelength_nm": spec["solver"]["wavelength_nm"],
            "tooling": _tooling_receipts(spec_path),
            "generator": {
                "libRadtran_source_archive": lib_archive_receipt,
                "uvspec": uvspec_receipt,
                "data_root": data_receipt,
            },
            "external_source": {
                "archive": eso_archive_receipt,
                "members": eso_member_receipts,
                "redistributed": False,
            },
            "source_derivations": {
                "solar_irradiance_550nm_W_m-2_micrometre-1": solar,
                "rolo_constant_coefficients": rolo_constants,
                "rolo_interpolated_coefficients_550nm": rolo_coefficients,
                "aod550": aod550,
                "ground_albedo_550nm": calculated_ground,
                "base_lunar_source": base_source,
            },
            "shared_inputs": shared_inputs,
            "cases": case_results,
            "reserved_holdout_case_count": len(spec["reserved_holdout_cases"]),
            "diagnostics": diagnostics,
            "environment": {
                "platform": platform.platform(),
                "python": sys.version,
                "execution_order": "serial",
            },
            "acceptance_thresholds_frozen": False,
            "spectral_grid_admitted": False,
            "production_admission_allowed": False,
            "runtime_dependency": False,
            "network_dependency": False,
            "external_source_bytes_redistributed": False,
        }
        manifest_path = temporary_path / MANIFEST_NAME
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        checkpoint = _build_checkpoint(manifest, manifest_path)
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
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument(
        "--inspect-spec",
        action="store_true",
        help="validate and print the frozen matrix without running MYSTIC",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.inspect_spec:
            print(json.dumps(inspect_spec(args.spec), indent=2, sort_keys=True))
            return 0
        checkpoint = build_pilot(
            uvspec=args.uvspec,
            lib_radtran_archive=args.lib_radtran_archive,
            data_root=args.data_root,
            eso_archive=args.eso_archive,
            output_root=args.output_root,
            spec_path=args.spec,
        )
    except (JonesMysticPilotError, OSError, tarfile.TarError) as exc:
        print(f"Jones/MYSTIC pilot build failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(checkpoint, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
