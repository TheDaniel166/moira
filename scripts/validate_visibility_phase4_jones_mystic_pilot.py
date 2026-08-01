#!/usr/bin/env python3
"""Independently validate a Phase 4 Jones/MYSTIC 550 nm pilot artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import struct
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_mystic_pilot_spec.json"
)
BUILDER_PATH = REPO_ROOT / "scripts" / "build_visibility_phase4_jones_mystic_pilot.py"
SPEC_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-spec/v2"
ARTIFACT_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-artifact/v2"
CASE_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-case/v2"
CHECKPOINT_SCHEMA = "moira.visibility-phase4-jones-mystic-pilot-checkpoint/v2"
ARTIFACT_STATUS = "corrected_external_pilot_complete_not_runtime_data_pack"
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


class JonesMysticPilotValidationError(ValueError):
    """Raised when an external pilot artifact fails independent validation."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_receipt(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise JonesMysticPilotValidationError(f"data root not found: {path}")
    members = sorted(
        member
        for member in path.rglob("*")
        if member.is_file()
        and not member.name.startswith("._")
        and member.name not in {"Makefile", "Makefile.in"}
    )
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


def _safe_relative(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise JonesMysticPilotValidationError(f"{label} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise JonesMysticPilotValidationError(f"{label} is not a safe relative path")
    return path


def _verify_receipt(
    root: Path,
    receipt: dict[str, Any],
    label: str,
) -> Path:
    if not isinstance(receipt, dict):
        raise JonesMysticPilotValidationError(f"{label} receipt is missing")
    relative = _safe_relative(receipt.get("path"), f"{label}.path")
    path = root.joinpath(*relative.parts)
    expected_bytes = receipt.get("bytes")
    expected_hash = receipt.get("sha256")
    if not isinstance(expected_bytes, int) or expected_bytes < 0:
        raise JonesMysticPilotValidationError(f"{label}.bytes is invalid")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise JonesMysticPilotValidationError(f"{label}.sha256 is invalid")
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != expected_bytes
        or sha256_file(path) != expected_hash
    ):
        raise JonesMysticPilotValidationError(f"{label} receipt differs: {path}")
    return path


def _verify_external(
    path: Path,
    receipt: dict[str, Any],
    label: str,
) -> None:
    if (
        not path.is_file()
        or path.stat().st_size != receipt.get("bytes")
        or sha256_file(path) != receipt.get("sha256")
    ):
        raise JonesMysticPilotValidationError(f"{label} receipt differs: {path}")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JonesMysticPilotValidationError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesMysticPilotValidationError(f"{label} must be a JSON object")
    return payload


def _require_close(
    actual: float,
    expected: float,
    label: str,
    *,
    tolerance: float = 1e-15,
) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise JonesMysticPilotValidationError(
            f"{label} differs: actual={actual!r}, expected={expected!r}"
        )


def _load_spec(path: Path) -> dict[str, Any]:
    spec = _read_json(path, "pilot specification")
    if spec.get("schema") != SPEC_SCHEMA:
        raise JonesMysticPilotValidationError("pilot spec schema differs")
    if spec.get("status") != (
        "frozen_corrected_external_pilot_matrix_not_runtime_data_pack"
    ):
        raise JonesMysticPilotValidationError("pilot spec status differs")
    if spec.get("pilot_model_id") != "jones_paranal_mystic_550nm_pilot_v2":
        raise JonesMysticPilotValidationError("pilot model identity differs")
    correction = spec.get("correction_history")
    if (
        not isinstance(correction, dict)
        or correction.get("supersedes_pilot_model_id")
        != "jones_paranal_mystic_550nm_pilot_v1"
        or correction.get("reason")
        != "correct_libradtran_explicit_aerosol_layer_boundary_ownership"
    ):
        raise JonesMysticPilotValidationError("pilot correction history differs")
    _verify_receipt(
        REPO_ROOT,
        correction.get("invalidation_checkpoint"),
        "v1 invalidation checkpoint",
    )
    aerosol = spec.get("aerosol")
    if (
        not isinstance(aerosol, dict)
        or aerosol.get("explicit_profile_layout")
        != "top_marker_then_null_gap_then_layer_files_at_lower_boundaries"
        or aerosol.get("layer_file_ownership")
        != "listed_altitude_inclusive_lower_boundary_to_next_higher_boundary"
        or aerosol.get("uppermost_marker_properties_ignored") is not True
    ):
        raise JonesMysticPilotValidationError("aerosol profile contract differs")
    if spec.get("pilot_gate", {}).get("acceptance_thresholds_status") != (
        "pilot_results_required_before_freeze"
    ):
        raise JonesMysticPilotValidationError("pilot thresholds were prefrozen")
    if spec.get("pilot_gate", {}).get("production_admission_allowed") is not False:
        raise JonesMysticPilotValidationError("pilot spec authorizes production")
    cases = spec.get("pilot_cases")
    holdouts = spec.get("reserved_holdout_cases")
    if not isinstance(cases, list) or len(cases) != 15:
        raise JonesMysticPilotValidationError("pilot spec case count differs")
    if not isinstance(holdouts, list) or len(holdouts) != 3:
        raise JonesMysticPilotValidationError("pilot holdout count differs")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    holdout_ids = [case.get("case_id") for case in holdouts if isinstance(case, dict)]
    if (
        len(case_ids) != 15
        or len(set(case_ids)) != 15
        or len(holdout_ids) != 3
        or len(set(holdout_ids)) != 3
        or set(case_ids) & set(holdout_ids)
    ):
        raise JonesMysticPilotValidationError("pilot and holdout IDs are not sealed")
    for index, receipt in enumerate(spec.get("governing_checkpoints", [])):
        if not isinstance(receipt, dict):
            raise JonesMysticPilotValidationError("governing receipt is invalid")
        _verify_receipt(REPO_ROOT, receipt, f"governing checkpoint {index}")
    return spec


def _numeric_rows(payload: bytes) -> list[list[float]]:
    rows = []
    for raw in payload.decode("ascii").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            rows.append([float(token) for token in line.split()])
    return rows


def _interpolate(rows: list[list[float]], x: float) -> list[float]:
    for row in rows:
        if row[0] == x:
            return row[1:]
    for left, right in zip(rows, rows[1:], strict=False):
        if left[0] < x < right[0]:
            fraction = (x - left[0]) / (right[0] - left[0])
            return [
                low + fraction * (high - low)
                for low, high in zip(left[1:], right[1:], strict=True)
            ]
    raise JonesMysticPilotValidationError("source interpolation bracket is missing")


def _parse_source_members(payloads: dict[str, bytes]) -> dict[str, Any]:
    solar_rows = _numeric_rows(payloads["SM-01/sm-01_mod2/data/solspec_ext.dat"])
    if len(solar_rows) != 1741 or any(len(row) != 2 for row in solar_rows):
        raise JonesMysticPilotValidationError("solar source table shape differs")
    solar = _interpolate(solar_rows, 0.55)[0]

    rolo_rows = _numeric_rows(payloads["SM-01/sm-01_mod2/data/moonalbedo.dat"])
    if len(rolo_rows) != 34 or rolo_rows[1] != [32.0]:
        raise JonesMysticPilotValidationError("ROLO source table shape differs")
    rolo_constants = rolo_rows[0]
    rolo_table = rolo_rows[2:]
    if len(rolo_constants) != 4 or any(len(row) != 11 for row in rolo_table):
        raise JonesMysticPilotValidationError("ROLO coefficient shape differs")
    rolo_coefficients = _interpolate(rolo_table, 550.0)

    aod_rows = _numeric_rows(payloads["SM-01/sm-01_mod2/data/mie_paranal_ref.dat"])
    aod550 = _interpolate(aod_rows, 0.55)[0]

    phase_rows = _numeric_rows(payloads["SM-01/sm-01_mod2/data/mie_m15s1.dat"])
    if len(phase_rows) != 43 or phase_rows[0] != [40.0, 181.0]:
        raise JonesMysticPilotValidationError("aerosol phase table shape differs")
    wavelengths = phase_rows[1]
    angles = phase_rows[2]
    matrix = phase_rows[3:]
    if angles != [float(value) for value in range(181)]:
        raise JonesMysticPilotValidationError("aerosol angle grid differs")
    phase_values = matrix[wavelengths.index(0.55)]
    mu_rows = sorted(
        (math.cos(math.radians(angle)), value)
        for angle, value in zip(angles, phase_values, strict=True)
    )
    integral = 0.0
    first_moment = 0.0
    for (mu0, phase0), (mu1, phase1) in zip(mu_rows, mu_rows[1:], strict=False):
        width = mu1 - mu0
        integral += 0.5 * (phase0 + phase1) * width
        first_moment += 0.5 * (mu0 * phase0 + mu1 * phase1) * width
    return {
        "solar": solar,
        "rolo_constants": rolo_constants,
        "rolo_coefficients": rolo_coefficients,
        "aod550": aod550,
        "phase_values": phase_values,
        "phase_source_half_normalization": integral / 2.0,
        "phase_source_asymmetry": first_moment / integral,
    }


def _read_eso_archive(
    archive_path: Path,
    spec: dict[str, Any],
) -> dict[str, bytes]:
    source = spec["external_source"]
    _verify_external(
        archive_path,
        {"bytes": source["archive_bytes"], "sha256": source["archive_sha256"]},
        "ESO archive",
    )
    payloads = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for expected in source["required_members"]:
            member = archive.getmember(expected["path"])
            stream = archive.extractfile(member)
            if not member.isfile() or stream is None:
                raise JonesMysticPilotValidationError(
                    f"ESO member is not readable: {expected['path']}"
                )
            payload = stream.read()
            if (
                len(payload) != expected["bytes"]
                or sha256_bytes(payload) != expected["sha256"]
            ):
                raise JonesMysticPilotValidationError(
                    f"ESO member receipt differs: {expected['path']}"
                )
            payloads[expected["path"]] = payload
    return payloads


def _lunar_source(
    case: dict[str, Any], source: dict[str, Any], spec: dict[str, Any]
) -> dict[str, float]:
    phase_deg = float(case["lunar_phase_angle_deg"])
    phase_rad = math.radians(phase_deg)
    signed_phase = phase_rad if case["waxing_state"] == "waxing" else -phase_rad
    coefficients = source["rolo_coefficients"]
    a0, a1, a2, a3, b1, b2, b3, d1, d2, d3 = coefficients
    p1, p2, p3, p4 = source["rolo_constants"]
    exponent = (
        a0
        + a1 * phase_rad
        + a2 * phase_rad**2
        + a3 * phase_rad**3
        + b1 * signed_phase
        + b2 * signed_phase**3
        + b3 * signed_phase**5
        + d1 * math.exp(-phase_deg / p1)
        + d2 * math.exp(-phase_deg / p2)
        + d3 * math.cos((phase_deg - p3) / p4)
    )
    lunar = spec["lunar_source"]
    albedo = math.exp(exponent) / lunar["rolo_correction_divisor"]
    flux = (
        source["solar"]
        * albedo
        * lunar["moon_solid_angle_sr"]
        / math.pi
        / float(case["moon_earth_distance_ratio"]) ** 2
        / 1000.0
    )
    return {
        "disk_equivalent_albedo": albedo,
        "toa_lunar_irradiance_W_m-2_nm-1": flux,
    }


def _separation(case: dict[str, Any]) -> float:
    target = math.radians(float(case["target_true_altitude_deg"]))
    moon = math.radians(float(case["moon_true_altitude_deg"]))
    azimuth = math.radians(float(case["relative_moon_azimuth_deg"]))
    cosine = math.sin(target) * math.sin(moon) + math.cos(target) * math.cos(
        moon
    ) * math.cos(azimuth)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _gauss_legendre(order: int) -> tuple[list[float], list[float]]:
    nodes = [0.0] * order
    weights = [0.0] * order
    for index in range((order + 1) // 2):
        root = math.cos(math.pi * (index + 0.75) / (order + 0.5))
        for _iteration in range(32):
            previous = 1.0
            current = root
            for degree in range(2, order + 1):
                following = (
                    (2 * degree - 1) * root * current - (degree - 1) * previous
                ) / degree
                previous, current = current, following
            derivative = order * (root * current - previous) / (root**2 - 1.0)
            updated = root - current / derivative
            if abs(updated - root) <= 2e-16:
                root = updated
                break
            root = updated
        else:
            raise JonesMysticPilotValidationError("quadrature root did not converge")
        previous = 1.0
        current = root
        for degree in range(2, order + 1):
            following = (
                (2 * degree - 1) * root * current - (degree - 1) * previous
            ) / degree
            previous, current = current, following
        derivative = order * (root * current - previous) / (root**2 - 1.0)
        weight = 2.0 / ((1.0 - root**2) * derivative**2)
        nodes[index] = -root
        nodes[order - index - 1] = root
        weights[index] = weight
        weights[order - index - 1] = weight
    return nodes, weights


def _phase_at_mu(mu: float, phase_values: list[float]) -> float:
    angle = math.degrees(math.acos(max(-1.0, min(1.0, mu))))
    if angle >= 180.0:
        return phase_values[180]
    lower = min(179, int(angle))
    fraction = angle - lower
    return phase_values[lower] + fraction * (
        phase_values[lower + 1] - phase_values[lower]
    )


def _moments_and_diagnostics(
    phase_values: list[float], moment_count: int, quadrature_order: int
) -> tuple[list[float], dict[str, float]]:
    nodes, weights = _gauss_legendre(quadrature_order)
    raw = [0.0] * moment_count
    for mu, weight in zip(nodes, weights, strict=True):
        factor = 0.5 * weight * _phase_at_mu(mu, phase_values)
        previous = 1.0
        raw[0] += factor
        current = mu
        raw[1] += factor * current
        for degree in range(2, moment_count):
            following = (
                (2 * degree - 1) * mu * current - (degree - 1) * previous
            ) / degree
            raw[degree] += factor * following
            previous, current = current, following
    moments = [value / raw[0] for value in raw]
    maximum_absolute = 0.0
    maximum_relative = 0.0
    for angle, expected in enumerate(phase_values):
        mu = math.cos(math.radians(angle))
        reconstructed = moments[0]
        previous = 1.0
        current = mu
        reconstructed += 3.0 * moments[1] * current
        for degree in range(2, moment_count):
            following = (
                (2 * degree - 1) * mu * current - (degree - 1) * previous
            ) / degree
            reconstructed += (2 * degree + 1) * moments[degree] * following
            previous, current = current, following
        absolute = abs(reconstructed - expected)
        maximum_absolute = max(maximum_absolute, absolute)
        maximum_relative = max(maximum_relative, absolute / expected)
    return moments, {
        "raw_k0": raw[0],
        "normalized_k0": moments[0],
        "normalized_k1": moments[1],
        "max_absolute_table_angle_reconstruction_error": maximum_absolute,
        "max_relative_table_angle_reconstruction_error": maximum_relative,
    }


def _float32(value: float) -> float:
    return struct.unpack("!f", struct.pack("!f", float(value)))[0]


def _format_float32(value: float) -> str:
    return format(_float32(value), ".9g")


def _parse_atmosphere(text: str) -> list[list[float]]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            values = [_float32(float(token)) for token in stripped.split()]
            if len(values) != 9:
                raise JonesMysticPilotValidationError("AFGL atmosphere shape differs")
            rows.append(values)
    if len(rows) < 2 or any(rows[i][0] <= rows[i + 1][0] for i in range(len(rows) - 1)):
        raise JonesMysticPilotValidationError("AFGL atmosphere altitude order differs")
    return rows


def _linear(z0: float, v0: float, z1: float, v1: float, z: float) -> float:
    fraction = (z - z0) / (z1 - z0)
    return _float32(v0 + fraction * (v1 - v0))


def _logarithmic(z0: float, v0: float, z1: float, v1: float, z: float) -> float:
    if abs(v1 - v0) <= 0.001 * v0 or min(v0, v1) <= 0.0:
        return _linear(z0, v0, z1, v1, z)
    fraction = (z - z0) / (z1 - z0)
    return _float32(math.exp(math.log(v0) + fraction * (math.log(v1) - math.log(v0))))


def _linmix(
    z0: float,
    gas0: float,
    air0: float,
    z1: float,
    gas1: float,
    air1: float,
    z: float,
    air: float,
) -> float:
    mixing0 = _float32(gas0 / air0)
    mixing1 = _float32(gas1 / air1)
    mixing = _linear(z0, mixing0, z1, mixing1, z)
    return _float32(mixing * air)


def _expected_atmosphere(source_text: str, altitude_m: float) -> tuple[bytes, bytes]:
    altitude = _float32(altitude_m / 1000.0)
    rows = _parse_atmosphere(source_text)
    upper_index = next(
        index
        for index in range(len(rows) - 1)
        if rows[index][0] > altitude > rows[index + 1][0]
    )
    high = rows[upper_index]
    low = rows[upper_index + 1]
    pressure = _logarithmic(low[0], low[1], high[0], high[1], altitude)
    temperature = _linear(low[0], low[2], high[0], high[2], altitude)
    air = _logarithmic(low[0], low[3], high[0], high[3], altitude)
    bottom = [altitude, pressure, temperature, air]
    for column in range(4, 9):
        bottom.append(
            _linmix(
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
    atmosphere_header = [
        "# Moira Phase 1 elevated-site reference-lab atmosphere.",
        "# Source: libRadtran 2.0.6 data/atmmod/afglus.dat.",
        "# Construction: default z_interpolate LINMIX, binary32 staged.",
        "# z(km) p(hPa) T(K) air(cm-3) O3(cm-3) O2(cm-3) H2O(cm-3) CO2(cm-3) NO2(cm-3)",
    ]
    atmosphere_body = [
        " ".join(_format_float32(value) for value in row) for row in selected
    ]
    atmosphere = ("\n".join(atmosphere_header + atmosphere_body) + "\n").encode()

    o4_source = [
        [row[0], _float32((float(row[5]) * 1e-23) ** 2), row[3]] for row in rows
    ]
    high_o4 = o4_source[upper_index]
    low_o4 = o4_source[upper_index + 1]
    o4_air = _logarithmic(low_o4[0], low_o4[2], high_o4[0], high_o4[2], altitude)
    o4_value = _linmix(
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
    o4_header = [
        "# Moira Phase 1 elevated-site reference-lab O4 companion.",
        "# Reproduces libRadtran 2.0.6 preinterpolation O4 pseudo-density.",
        "# z(km) O4_scaled_density(cm-3)",
    ]
    o4_body = [
        f"{_format_float32(row[0])} {_format_float32(row[1])}" for row in selected_o4
    ]
    o4 = ("\n".join(o4_header + o4_body) + "\n").encode()
    return atmosphere, o4


def _render_lunar_source(flux: float, spec: dict[str, Any]) -> bytes:
    return (
        "\n".join(
            f"{float(wavelength):.1f} {flux:.17e}"
            for wavelength in spec["lunar_source"]["source_file_grid_nm"]
        )
        + "\n"
    ).encode("ascii")


def _render_input(case: dict[str, Any], spec: dict[str, Any]) -> bytes:
    site = spec["site_and_atmosphere"]
    wavelength = float(spec["solver"]["wavelength_nm"])
    lunar_zenith = 90.0 - float(case["moon_true_altitude_deg"])
    viewing_umu = -math.sin(math.radians(float(case["target_true_altitude_deg"])))
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
        "zout 0",
        f"umu {viewing_umu:.17g}",
        f"phi {float(case['relative_moon_azimuth_deg']):.17g}",
        "quiet",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def _parse_directional(path: Path) -> float:
    rows = [
        line.split() for line in path.read_text(encoding="ascii").splitlines() if line
    ]
    if len(rows) != 1 or len(rows[0]) != 5:
        raise JonesMysticPilotValidationError(
            f"directional output shape differs: {path}"
        )
    _require_close(float(rows[0][0]), 550.0, "directional wavelength", tolerance=1e-6)
    value = float(rows[0][4])
    if not math.isfinite(value) or value <= 0.0:
        raise JonesMysticPilotValidationError(
            f"directional output is not finite and positive: {path}"
        )
    return value


def _verify_tooling(
    artifact_root: Path,
    manifest: dict[str, Any],
    spec_path: Path,
) -> None:
    expected = {
        "spec": spec_path,
        "builder": BUILDER_PATH,
        "validator": Path(__file__).resolve(),
    }
    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict):
        raise JonesMysticPilotValidationError("tooling receipt is missing")
    for role, path in expected.items():
        receipt = tooling.get(role)
        if not isinstance(receipt, dict):
            raise JonesMysticPilotValidationError(f"tooling omits {role}")
        expected_relative = path.relative_to(REPO_ROOT).as_posix()
        if receipt.get("path") != expected_relative:
            raise JonesMysticPilotValidationError(f"{role} path receipt differs")
        _verify_receipt(REPO_ROOT, receipt, f"tooling {role}")
    del artifact_root


def _verify_generator(
    manifest: dict[str, Any],
    spec: dict[str, Any],
    *,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
) -> None:
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise JonesMysticPilotValidationError("generator receipt is missing")
    lock = spec["external_generators"]["libRadtran"]
    archive_receipt = generator.get("libRadtran_source_archive")
    _verify_external(lib_radtran_archive, archive_receipt, "libRadtran archive")
    if (
        archive_receipt.get("bytes") != lock["archive_bytes"]
        or archive_receipt.get("sha256") != lock["archive_sha256"]
    ):
        raise JonesMysticPilotValidationError("libRadtran source lock differs")
    uvspec_receipt = generator.get("uvspec")
    if not isinstance(uvspec_receipt, dict):
        raise JonesMysticPilotValidationError("uvspec receipt is missing")
    if (
        not uvspec.is_file()
        or uvspec.stat().st_size != uvspec_receipt.get("bytes")
        or sha256_file(uvspec) != uvspec_receipt.get("sha256")
        or uvspec_receipt.get("sha256") != lock["uvspec_sha256"]
    ):
        raise JonesMysticPilotValidationError("uvspec executable receipt differs")
    version = subprocess.run(
        [str(uvspec), "-v"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    version_text = (version.stdout + version.stderr).strip()
    if version.returncode != 0 or version_text != lock["uvspec_version"]:
        raise JonesMysticPilotValidationError("uvspec version receipt differs")
    build_root = uvspec.parent.parent
    build_receipts = uvspec_receipt.get("build_files")
    if not isinstance(build_receipts, list) or len(build_receipts) != 3:
        raise JonesMysticPilotValidationError("uvspec build receipts are incomplete")
    for receipt in build_receipts:
        _verify_receipt(build_root, receipt, "uvspec build file")
    actual_data = tree_receipt(data_root)
    if actual_data != lock["data_root_receipt"] or actual_data != generator.get(
        "data_root"
    ):
        raise JonesMysticPilotValidationError("libRadtran data-root receipt differs")


def _verify_shared(
    artifact_root: Path,
    manifest: dict[str, Any],
    spec: dict[str, Any],
    source: dict[str, Any],
    data_root: Path,
) -> None:
    shared = artifact_root / "shared"
    if not shared.is_dir() or shared.is_symlink():
        raise JonesMysticPilotValidationError("shared input directory is invalid")
    declared = manifest.get("shared_inputs")
    if not isinstance(declared, dict):
        raise JonesMysticPilotValidationError("shared-input receipt is missing")
    receipts = declared.get("files")
    if not isinstance(receipts, list):
        raise JonesMysticPilotValidationError("shared file receipts are missing")
    declared_names = set()
    for index, receipt in enumerate(receipts):
        path = _verify_receipt(artifact_root, receipt, f"shared file {index}")
        if path.parent != shared or path.name in declared_names:
            raise JonesMysticPilotValidationError(
                "shared file inventory is noncanonical"
            )
        declared_names.add(path.name)
    actual_names = {path.name for path in shared.iterdir() if path.is_file()}
    if declared_names != actual_names or any(
        path.is_symlink() for path in shared.iterdir()
    ):
        raise JonesMysticPilotValidationError("shared file inventory differs")

    atmosphere_source = data_root / spec["site_and_atmosphere"][
        "atmosphere_source_path"
    ].removeprefix("data/")
    source_text = atmosphere_source.read_text(encoding="ascii")
    expected_atmosphere, expected_o4 = _expected_atmosphere(
        source_text, spec["site_and_atmosphere"]["observer_altitude_m"]
    )
    if (shared / "atmosphere.dat").read_bytes() != expected_atmosphere:
        raise JonesMysticPilotValidationError("truncated atmosphere bytes differ")
    if (shared / "o4.dat").read_bytes() != expected_o4:
        raise JonesMysticPilotValidationError("O4 companion bytes differ")

    aerosol = spec["aerosol"]
    source_invariants = aerosol["source_invariants"]
    _require_close(
        source["phase_source_half_normalization"],
        source_invariants["half_solid_angle_normalization"],
        "source phase normalization",
        tolerance=source_invariants["absolute_tolerance"],
    )
    _require_close(
        source["phase_source_asymmetry"],
        source_invariants["asymmetry_parameter"],
        "source phase asymmetry",
        tolerance=source_invariants["absolute_tolerance"],
    )
    moments, representation = _moments_and_diagnostics(
        source["phase_values"],
        aerosol["legendre_moment_count"],
        aerosol["gauss_legendre_quadrature_order"],
    )
    declared_representation = declared.get("aerosol", {}).get("representation")
    if not isinstance(declared_representation, dict):
        raise JonesMysticPilotValidationError(
            "aerosol representation receipt is missing"
        )
    for key, expected in representation.items():
        _require_close(
            float(declared_representation.get(key)),
            expected,
            f"aerosol representation {key}",
            tolerance=2e-15,
        )

    moment_text = " ".join(format(value, ".17e") for value in moments)
    bottom = float(aerosol["profile_bottom_km"])
    top = float(aerosol["profile_top_km"])
    step = float(aerosol["nominal_layer_thickness_km"])
    boundaries = [bottom]
    while boundaries[-1] + step < top - 1e-12:
        boundaries.append(round(boundaries[-1] + step, 12))
    boundaries.append(top)
    profile_lines = [
        f"{float(aerosol['null_top_boundary_km']):.8f} ../../shared/null_layer.dat",
        f"{top:.8f} ../../shared/null_layer.dat",
    ]
    layer_rows = []
    integrated = 0.0
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
        integrated += extinction * (high - low)
        filename = f"aerosol_layer_{index:03d}.dat"
        expected_rows = [
            f"{float(wavelength):.1f} {extinction:.17e} "
            f"{float(aerosol['single_scattering_albedo']):.17g} {moment_text}"
            for wavelength in aerosol["explicit_file_wavelength_grid_nm"]
        ]
        expected_bytes = ("\n".join(expected_rows) + "\n").encode("ascii")
        if (shared / filename).read_bytes() != expected_bytes:
            raise JonesMysticPilotValidationError(
                f"explicit aerosol layer differs: {filename}"
            )
        layer_rows.append((low, filename))
    for low, filename in reversed(layer_rows):
        profile_lines.append(f"{low:.8f} ../../shared/{filename}")
    expected_profile = ("\n".join(profile_lines) + "\n").encode("ascii")
    if (shared / "aerosol_profile.dat").read_bytes() != expected_profile:
        raise JonesMysticPilotValidationError("explicit aerosol profile differs")
    if (shared / "null_layer.dat").read_bytes() != b"100 0 1 1\n100000 0 1 1\n":
        raise JonesMysticPilotValidationError("explicit null aerosol layer differs")
    _require_close(
        declared["aerosol"]["integrated_aod_to_profile_top"],
        integrated,
        "integrated aerosol column",
        tolerance=1e-16,
    )
    if declared["aerosol"].get("explicit_profile_layout") != aerosol.get(
        "explicit_profile_layout"
    ) or declared["aerosol"].get("layer_file_binding_count") != len(layer_rows):
        raise JonesMysticPilotValidationError(
            "explicit aerosol profile metadata differs"
        )


def _verify_cases(
    artifact_root: Path,
    manifest: dict[str, Any],
    spec: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 15:
        raise JonesMysticPilotValidationError("artifact case count differs")
    expected_by_id = {case["case_id"]: case for case in spec["pilot_cases"]}
    actual_by_id = {
        case.get("case_id"): case for case in cases if isinstance(case, dict)
    }
    if set(actual_by_id) != set(expected_by_id):
        raise JonesMysticPilotValidationError(
            "artifact case IDs differ from the matrix"
        )
    runs_root = artifact_root / "runs"
    if not runs_root.is_dir() or runs_root.is_symlink():
        raise JonesMysticPilotValidationError("runs directory is invalid")
    if {path.name for path in runs_root.iterdir() if path.is_dir()} != set(
        expected_by_id
    ):
        raise JonesMysticPilotValidationError("run-directory inventory differs")

    checked = []
    for case_id in [case["case_id"] for case in spec["pilot_cases"]]:
        expected_case = expected_by_id[case_id]
        result = actual_by_id[case_id]
        if result.get("case") != expected_case:
            raise JonesMysticPilotValidationError(f"case matrix drift: {case_id}")
        case_path = _verify_receipt(
            artifact_root, result.get("case_manifest"), f"case manifest {case_id}"
        )
        case_manifest = _read_json(case_path, f"case manifest {case_id}")
        if (
            case_manifest.get("schema") != CASE_SCHEMA
            or case_manifest.get("case") != expected_case
        ):
            raise JonesMysticPilotValidationError(
                f"case manifest contract differs: {case_id}"
            )
        run_dir = case_path.parent
        receipts = case_manifest.get("files")
        if not isinstance(receipts, list):
            raise JonesMysticPilotValidationError(
                f"case file receipts are missing: {case_id}"
            )
        names = set()
        for index, receipt in enumerate(receipts):
            path = _verify_receipt(
                artifact_root, receipt, f"{case_id} file receipt {index}"
            )
            if path.parent != run_dir or path.name in names:
                raise JonesMysticPilotValidationError(
                    f"case file inventory is noncanonical: {case_id}"
                )
            names.add(path.name)
        if names != EXPECTED_RUN_FILES:
            raise JonesMysticPilotValidationError(
                f"case file inventory differs: {case_id}"
            )
        if {path.name for path in run_dir.iterdir() if path.is_file()} != (
            EXPECTED_RUN_FILES | {"case.json"}
        ) or any(path.is_symlink() for path in run_dir.iterdir()):
            raise JonesMysticPilotValidationError(
                f"case directory contains undeclared entries: {case_id}"
            )

        source_result = _lunar_source(expected_case, source, spec)
        lunar_bytes = (run_dir / "lunar_source.dat").read_bytes()
        if b"\r" in lunar_bytes:
            raise JonesMysticPilotValidationError(
                f"lunar source is not LF-only: {case_id}"
            )
        lunar_rows = [
            [float(token) for token in line.split()]
            for line in lunar_bytes.decode("ascii").splitlines()
            if line
        ]
        if len(lunar_rows) != 3 or any(len(row) != 2 for row in lunar_rows):
            raise JonesMysticPilotValidationError(
                f"lunar source shape differs: {case_id}"
            )
        for row, wavelength in zip(
            lunar_rows,
            spec["lunar_source"]["source_file_grid_nm"],
            strict=True,
        ):
            _require_close(row[0], wavelength, f"{case_id} lunar wavelength")
            _require_close(
                row[1],
                source_result["toa_lunar_irradiance_W_m-2_nm-1"],
                f"{case_id} lunar irradiance",
                tolerance=1e-20,
            )
        if (run_dir / "input.inp").read_bytes() != _render_input(expected_case, spec):
            raise JonesMysticPilotValidationError(
                f"libRadtran input differs: {case_id}"
            )
        radiance = _parse_directional(run_dir / "mc.rad.spc")
        standard_error = _parse_directional(run_dir / "mc.rad.std.spc")
        derived = case_manifest.get("derived")
        if not isinstance(derived, dict) or derived != result.get("derived"):
            raise JonesMysticPilotValidationError(f"derived receipt differs: {case_id}")
        if set(derived) != {
            "target_moon_separation_deg",
            "disk_equivalent_albedo",
            "toa_lunar_irradiance_W_m-2_nm-1",
            "directional_radiance_W_m-2_nm-1_sr-1",
            "directional_standard_error_W_m-2_nm-1_sr-1",
            "relative_monte_carlo_standard_error",
        }:
            raise JonesMysticPilotValidationError(
                f"independent derived shape differs: {case_id}"
            )
        _require_close(
            derived["target_moon_separation_deg"],
            _separation(expected_case),
            f"{case_id} target-Moon separation",
            tolerance=1e-12,
        )
        _require_close(
            derived["disk_equivalent_albedo"],
            source_result["disk_equivalent_albedo"],
            f"{case_id} lunar albedo",
            tolerance=1e-15,
        )
        _require_close(
            derived["toa_lunar_irradiance_W_m-2_nm-1"],
            source_result["toa_lunar_irradiance_W_m-2_nm-1"],
            f"{case_id} lunar irradiance",
            tolerance=1e-20,
        )
        _require_close(
            derived["directional_radiance_W_m-2_nm-1_sr-1"],
            radiance,
            f"{case_id} directional radiance",
        )
        _require_close(
            derived["directional_standard_error_W_m-2_nm-1_sr-1"],
            standard_error,
            f"{case_id} directional standard error",
        )
        _require_close(
            derived["relative_monte_carlo_standard_error"],
            standard_error / radiance,
            f"{case_id} relative standard error",
        )
        checked.append(result)

    anchor = artifact_root / "runs" / "base_p300k_s49979687"
    repeat = artifact_root / "runs" / "base_p300k_s49979687_repeat"
    for name in SCIENTIFIC_REPEAT_FILES:
        if (anchor / name).read_bytes() != (repeat / name).read_bytes():
            raise JonesMysticPilotValidationError(
                f"fixed-seed repeat differs for {name}"
            )
    return checked


def _recompute_diagnostics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {case["case_id"]: case for case in cases}
    repeat_files = {name: True for name in SCIENTIFIC_REPEAT_FILES}
    convergence = []
    for case_id in (
        "base_p100k_s49979687",
        "base_p300k_s49979687",
        "base_p1m_s49979687",
    ):
        row = by_id[case_id]
        derived = row["derived"]
        photons = row["case"]["photon_count"]
        standard_error = derived["directional_standard_error_W_m-2_nm-1_sr-1"]
        convergence.append(
            {
                "case_id": case_id,
                "photon_count": photons,
                "radiance_W_m-2_nm-1_sr-1": derived[
                    "directional_radiance_W_m-2_nm-1_sr-1"
                ],
                "standard_error_W_m-2_nm-1_sr-1": standard_error,
                "relative_standard_error": derived[
                    "relative_monte_carlo_standard_error"
                ],
                "standard_error_times_sqrt_photons": standard_error
                * math.sqrt(photons),
            }
        )
    scaled = [row["standard_error_times_sqrt_photons"] for row in convergence]
    seed_ids = [
        "base_p300k_s49979687",
        "base_p300k_s67867967",
        "base_p300k_s86028121",
    ]
    radiances = [
        by_id[case_id]["derived"]["directional_radiance_W_m-2_nm-1_sr-1"]
        for case_id in seed_ids
    ]
    errors = [
        by_id[case_id]["derived"]["directional_standard_error_W_m-2_nm-1_sr-1"]
        for case_id in seed_ids
    ]
    mean = statistics.fmean(radiances)
    return {
        "fixed_seed_repeat": {
            "anchor_case_id": "base_p300k_s49979687",
            "repeat_case_id": "base_p300k_s49979687_repeat",
            "byte_identical_files": repeat_files,
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
            "radiance_mean_W_m-2_nm-1_sr-1": mean,
            "radiance_sample_standard_deviation_W_m-2_nm-1_sr-1": statistics.stdev(
                radiances
            ),
            "radiance_sample_relative_standard_deviation": statistics.stdev(radiances)
            / mean,
            "mean_reported_standard_error_W_m-2_nm-1_sr-1": statistics.fmean(errors),
            "acceptance_threshold_applied": False,
        },
    }


def _verify_checkpoint(
    artifact_root: Path,
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    checkpoint = _read_json(artifact_root / CHECKPOINT_NAME, "pilot checkpoint")
    if checkpoint.get("schema") != CHECKPOINT_SCHEMA:
        raise JonesMysticPilotValidationError("checkpoint schema differs")
    if checkpoint.get("status") != (
        "corrected_v2_pilot_generated_thresholds_not_yet_frozen"
    ):
        raise JonesMysticPilotValidationError("checkpoint status differs")
    if checkpoint.get("correction_history") != manifest.get("correction_history"):
        raise JonesMysticPilotValidationError("checkpoint correction lineage differs")
    receipt = checkpoint.get("artifact_manifest")
    _verify_receipt(artifact_root, receipt, "checkpoint artifact manifest")
    if receipt.get("path") != MANIFEST_NAME:
        raise JonesMysticPilotValidationError("checkpoint manifest path differs")
    if checkpoint.get("tooling") != manifest.get("tooling") or checkpoint.get(
        "generator"
    ) != manifest.get("generator"):
        raise JonesMysticPilotValidationError("checkpoint lineage differs")
    radiances = [
        case["derived"]["directional_radiance_W_m-2_nm-1_sr-1"] for case in cases
    ]
    errors = [case["derived"]["relative_monte_carlo_standard_error"] for case in cases]
    if checkpoint.get("directional_radiance_range_W_m-2_nm-1_sr-1") != [
        min(radiances),
        max(radiances),
    ] or checkpoint.get("relative_monte_carlo_standard_error_range") != [
        min(errors),
        max(errors),
    ]:
        raise JonesMysticPilotValidationError("checkpoint measured range differs")
    for key in (
        "acceptance_thresholds_frozen",
        "spectral_grid_admitted",
        "production_admission_allowed",
        "runtime_dependency",
        "network_dependency",
        "external_source_bytes_redistributed",
    ):
        if checkpoint.get(key) is not False:
            raise JonesMysticPilotValidationError(f"checkpoint boundary changed: {key}")
    return checkpoint


def validate_pilot(
    *,
    artifact_root: Path,
    uvspec: Path,
    lib_radtran_archive: Path,
    data_root: Path,
    eso_archive: Path,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    if os.name != "posix":
        raise JonesMysticPilotValidationError(
            "the Jones/MYSTIC artifact must be validated in the POSIX lab environment"
        )
    spec = _load_spec(spec_path)
    if not artifact_root.is_dir() or artifact_root.is_symlink():
        raise JonesMysticPilotValidationError(
            f"artifact root is invalid: {artifact_root}"
        )
    top_names = {path.name for path in artifact_root.iterdir()}
    if top_names != {"shared", "runs", MANIFEST_NAME, CHECKPOINT_NAME}:
        raise JonesMysticPilotValidationError("artifact top-level inventory differs")
    manifest = _read_json(artifact_root / MANIFEST_NAME, "artifact manifest")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("status") != ARTIFACT_STATUS
        or manifest.get("spec_id") != spec["spec_id"]
        or manifest.get("pilot_model_id") != spec["pilot_model_id"]
        or manifest.get("correction_history") != spec["correction_history"]
    ):
        raise JonesMysticPilotValidationError("artifact identity differs")
    for key in (
        "acceptance_thresholds_frozen",
        "spectral_grid_admitted",
        "production_admission_allowed",
        "runtime_dependency",
        "network_dependency",
        "external_source_bytes_redistributed",
    ):
        if manifest.get(key) is not False:
            raise JonesMysticPilotValidationError(f"artifact boundary changed: {key}")
    _verify_tooling(artifact_root, manifest, spec_path)
    _verify_generator(
        manifest,
        spec,
        uvspec=uvspec,
        lib_radtran_archive=lib_radtran_archive,
        data_root=data_root,
    )
    payloads = _read_eso_archive(eso_archive, spec)
    source = _parse_source_members(payloads)
    source_derivations = manifest.get("source_derivations")
    if not isinstance(source_derivations, dict):
        raise JonesMysticPilotValidationError("source derivations are missing")
    _require_close(
        source_derivations["solar_irradiance_550nm_W_m-2_micrometre-1"],
        source["solar"],
        "solar source derivation",
    )
    _require_close(source_derivations["aod550"], source["aod550"], "AOD derivation")
    if (
        source_derivations.get("rolo_constant_coefficients") != source["rolo_constants"]
        or source_derivations.get("rolo_interpolated_coefficients_550nm")
        != source["rolo_coefficients"]
    ):
        raise JonesMysticPilotValidationError("ROLO source derivation differs")
    source_receipt = manifest.get("external_source")
    if (
        not isinstance(source_receipt, dict)
        or source_receipt.get("redistributed") is not False
    ):
        raise JonesMysticPilotValidationError(
            "ESO source redistribution boundary differs"
        )
    _verify_external(eso_archive, source_receipt.get("archive"), "ESO archive manifest")
    if len(source_receipt.get("members", [])) != 8 or any(
        receipt.get("redistributed") is not False
        for receipt in source_receipt.get("members", [])
    ):
        raise JonesMysticPilotValidationError("ESO member receipts differ")
    _verify_shared(artifact_root, manifest, spec, source, data_root)
    cases = _verify_cases(artifact_root, manifest, spec, source)
    diagnostics = _recompute_diagnostics(cases)
    if diagnostics != manifest.get("diagnostics"):
        raise JonesMysticPilotValidationError("independent pilot diagnostics differ")
    checkpoint = _verify_checkpoint(artifact_root, manifest, cases)
    if checkpoint.get("diagnostics") != diagnostics:
        raise JonesMysticPilotValidationError("checkpoint diagnostics differ")
    return {
        "status": "valid",
        "spec_id": spec["spec_id"],
        "pilot_model_id": spec["pilot_model_id"],
        "executed_case_count": len(cases),
        "reserved_holdout_case_count": len(spec["reserved_holdout_cases"]),
        "fixed_seed_repeat_passed": True,
        "acceptance_thresholds_frozen": False,
        "production_admission_allowed": False,
        "runtime_dependency": False,
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
        result = validate_pilot(
            artifact_root=args.artifact_root,
            uvspec=args.uvspec,
            lib_radtran_archive=args.lib_radtran_archive,
            data_root=args.data_root,
            eso_archive=args.eso_archive,
            spec_path=args.spec,
        )
    except (JonesMysticPilotValidationError, OSError, tarfile.TarError) as exc:
        print(f"Jones/MYSTIC pilot validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
