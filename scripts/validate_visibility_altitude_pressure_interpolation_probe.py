#!/usr/bin/env python3
"""Independently validate a Phase 1 altitude/pressure probe artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_altitude_pressure_interpolation_probe_spec.json"
)
BUILDER_PATH = (
    REPO_ROOT / "scripts" / "build_visibility_altitude_pressure_interpolation_probe.py"
)
MANIFEST_NAME = "manifest.json"
SUMMARY_NAME = "summary.json"
RUN_SCHEMA = "moira.visibility-altitude-pressure-interpolation-run/v1"
ARTIFACT_SCHEMA = "moira.visibility-altitude-pressure-interpolation-artifact/v1"
ARTIFACT_STATUS = (
    "phase1_altitude_pressure_interpolation_probe_not_runtime_data_pack"
)
RUN_FILES = frozenset(
    {
        "atmosphere.dat",
        "input.inp",
        "o4.dat",
        "randomseed",
        "result.json",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
        "wavelength_grid.dat",
    }
)
DATA_LINK_NAME = "_libradtran_data"


class ValidationError(ValueError):
    """Raised when an altitude/pressure artifact is incomplete or inconsistent."""


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _compact_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_float(value: float) -> float:
    if not math.isfinite(value):
        raise ValidationError("non-finite derived value")
    return float(format(value, ".15g"))


def _float32(value: float) -> float:
    return struct.unpack("!f", struct.pack("!f", float(value)))[0]


def _assert_cross_platform_equal(
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    if isinstance(actual, dict) or isinstance(expected, dict):
        if (
            not isinstance(actual, dict)
            or not isinstance(expected, dict)
            or set(actual) != set(expected)
        ):
            raise ValidationError(f"{label} object shape differs")
        for key in sorted(actual):
            _assert_cross_platform_equal(
                actual[key],
                expected[key],
                f"{label}.{key}",
            )
        return
    if isinstance(actual, list) or isinstance(expected, list):
        if (
            not isinstance(actual, list)
            or not isinstance(expected, list)
            or len(actual) != len(expected)
        ):
            raise ValidationError(f"{label} array shape differs")
        for index, (actual_item, expected_item) in enumerate(
            zip(actual, expected)
        ):
            _assert_cross_platform_equal(
                actual_item,
                expected_item,
                f"{label}[{index}]",
            )
        return
    if (
        isinstance(actual, bool)
        or isinstance(expected, bool)
        or actual is None
        or expected is None
        or isinstance(actual, str)
        or isinstance(expected, str)
    ):
        if actual != expected:
            raise ValidationError(f"{label} differs")
        return
    if isinstance(actual, (int, float)) and isinstance(
        expected,
        (int, float),
    ):
        if isinstance(actual, int) and isinstance(expected, int):
            if actual != expected:
                raise ValidationError(f"{label} differs")
            return
        actual_float = float(actual)
        expected_float = float(expected)
        if (
            not math.isfinite(actual_float)
            or not math.isfinite(expected_float)
            or not math.isclose(
                actual_float,
                expected_float,
                rel_tol=5e-13,
                abs_tol=5e-15,
            )
        ):
            raise ValidationError(f"{label} numeric value differs")
        return
    if actual != expected:
        raise ValidationError(f"{label} differs")


def _format_number(value: float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError("non-finite input value")
    return format(number, ".15g")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{label} must be an object")
    return payload


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationError(f"{label} path escapes its root")
    return path.as_posix()


def _valid_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValidationError(f"{label} is not SHA-256")
    return value


def _validate_receipt_shape(receipt: Any, label: str) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ValidationError(f"{label} receipt is missing")
    _safe_relative_path(receipt.get("path"), label)
    byte_count = receipt.get("bytes")
    if (
        isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count < 0
    ):
        raise ValidationError(f"{label} byte count is invalid")
    _valid_sha(receipt.get("sha256"), f"{label} sha256")
    return receipt


def _verify_file_receipt(
    root: Path,
    receipt: dict[str, Any],
    label: str,
) -> Path:
    relative = _safe_relative_path(receipt.get("path"), label)
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label} escapes artifact root") from exc
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != receipt.get("bytes")
        or _sha256_file(path) != receipt.get("sha256")
    ):
        raise ValidationError(f"{label} checksum differs")
    return path


def _repo_receipt(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": resolved.relative_to(REPO_ROOT.resolve()).as_posix(),
        "bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _vertical_grid_segments(
    declaration: dict[str, Any],
) -> list[tuple[float, float, float]]:
    raw_segments = declaration.get("base_segments_km_above_surface")
    if not isinstance(raw_segments, list):
        raise ValidationError("vertical-grid segments are missing")
    parsed: list[tuple[float, float, float]] = []
    previous_stop: float | None = None
    for raw in raw_segments:
        if not isinstance(raw, dict) or set(raw) != {"start", "stop", "step"}:
            raise ValidationError("vertical-grid segment shape differs")
        values: list[float] = []
        for label in ("start", "stop", "step"):
            value = raw[label]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ValidationError("vertical-grid segment value differs")
            values.append(float(value))
        start, stop, step = values
        if (
            start < 0.0
            or start >= stop
            or step <= 0.0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise ValidationError("vertical-grid segment domain differs")
        parsed.append((start, stop, step))
        previous_stop = stop
    return parsed


def _site_relative_vertical_grid(
    observer_altitude_m: float,
    spec: dict[str, Any],
) -> list[float]:
    altitude_m = float(observer_altitude_m)
    if not math.isfinite(altitude_m) or not 0.0 <= altitude_m <= 5000.0:
        raise ValidationError("observer altitude is outside the grid domain")
    declaration = spec.get("site_relative_vertical_grid")
    if not isinstance(declaration, dict):
        raise ValidationError("site-relative vertical-grid contract is missing")
    try:
        site_km = Decimal(str(altitude_m)) / Decimal("1000")
        top_km = Decimal(str(declaration["top_of_atmosphere_km"]))
    except (KeyError, ArithmeticError) as exc:
        raise ValidationError("site-relative vertical-grid top differs") from exc
    relative_top = top_km - site_km
    relative_levels: list[Decimal] = []
    for start_value, stop_value, step_value in _vertical_grid_segments(
        declaration
    ):
        start = Decimal(str(start_value))
        stop = Decimal(str(stop_value))
        step = Decimal(str(step_value))
        if start > relative_top:
            break
        clipped_stop = min(stop, relative_top)
        count = int((clipped_stop - start) // step)
        for offset in range(count + 1):
            value = start + Decimal(offset) * step
            if value > clipped_stop:
                break
            if not relative_levels or value != relative_levels[-1]:
                relative_levels.append(value)
        if clipped_stop == relative_top:
            break
    if not relative_levels or relative_levels[0] != Decimal("0"):
        raise ValidationError("site-relative vertical grid lacks its surface")
    if relative_levels[-1] != relative_top:
        relative_levels.append(relative_top)
    levels = [float(site_km + value) for value in relative_levels]
    if (
        levels[0] != float(site_km)
        or levels[-1] != float(top_km)
        or any(a >= b for a, b in zip(levels, levels[1:]))
    ):
        raise ValidationError("site-relative vertical grid is invalid")
    return levels


def _load_spec(path: Path) -> dict[str, Any]:
    spec = _load_json(path, "specification")
    if spec.get("schema") != (
        "moira.visibility-altitude-pressure-interpolation-probe-spec/v1"
    ):
        raise ValidationError("specification schema differs")
    if spec.get("status") != "research_probe_not_runtime_data_pack":
        raise ValidationError("specification status differs")
    axes = spec.get("axes")
    if not isinstance(axes, dict):
        raise ValidationError("specification axes are missing")
    if set(spec.get("atmosphere_profiles", {})) != {
        "tropical",
        "midlatitude_summer",
        "midlatitude_winter",
        "subarctic_summer",
        "subarctic_winter",
        "us_standard",
    }:
        raise ValidationError("specification profile inventory differs")
    refinements = spec.get("refinement_from_failed_designs")
    if (
        not isinstance(refinements, list)
        or len(refinements) != 4
        or any(
            not isinstance(refinement, dict)
            or refinement.get("thresholds_relaxed") is not False
            for refinement in refinements
        )
    ):
        raise ValidationError("failed-design refinements are missing")
    if _vertical_grid_segments(spec["site_relative_vertical_grid"]) != [
        (0.0, 2.0, 0.025),
        (2.0, 5.0, 0.05),
        (5.0, 10.0, 0.1),
        (10.0, 25.0, 0.25),
        (25.0, 50.0, 1.0),
        (50.0, 120.0, 5.0),
    ] or len(_site_relative_vertical_grid(0.0, spec)) != 290:
        raise ValidationError("site-relative vertical-grid contract differs")
    return spec


def _all_axis_values(axis: dict[str, Any]) -> list[float]:
    return sorted(
        {
            *(float(value) for value in axis["training_nodes"]),
            *(float(value) for value in axis["reserved_holdouts"]),
        }
    )


def _profile_filename(profile: str, altitude_m: float, kind: str) -> str:
    altitude_token = f"{int(round(altitude_m)):04d}m"
    suffix = "dat" if kind in {"atmosphere", "o4"} else "json"
    return f"{profile}__{altitude_token}__{kind}.{suffix}"


def _parse_atmosphere_bottom(path: Path) -> list[float]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != 9:
            raise ValidationError(f"atmosphere row shape differs: {path}")
        try:
            row = [float(field) for field in fields]
        except ValueError as exc:
            raise ValidationError(f"atmosphere row is non-numeric: {path}") from exc
        if any(not math.isfinite(value) or value < 0.0 for value in row):
            raise ValidationError(f"atmosphere row is invalid: {path}")
        rows.append(row)
    if (
        len(rows) < 2
        or any(a[0] <= b[0] for a, b in zip(rows, rows[1:]))
    ):
        raise ValidationError(f"atmosphere levels are invalid: {path}")
    return rows[-1]


def _parse_o4(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != 2:
            raise ValidationError(f"O4 row shape differs: {path}")
        try:
            altitude, density = (float(field) for field in fields)
        except ValueError as exc:
            raise ValidationError(f"O4 row is non-numeric: {path}") from exc
        if (
            not math.isfinite(altitude)
            or not math.isfinite(density)
            or altitude < 0.0
            or density < 0.0
        ):
            raise ValidationError(f"O4 row is invalid: {path}")
        rows.append((altitude, density))
    if (
        len(rows) < 2
        or any(a[0] <= b[0] for a, b in zip(rows, rows[1:]))
    ):
        raise ValidationError(f"O4 levels are invalid: {path}")
    return rows


def _verify_profiles(
    artifact: Path,
    manifest: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[
    dict[tuple[str, float], dict[str, Any]],
    set[str],
]:
    declarations = manifest.get("profiles")
    if not isinstance(declarations, list):
        raise ValidationError("profile receipts are missing")
    expected_count = len(spec["atmosphere_profiles"]) * len(
        _all_axis_values(spec["axes"]["observer_altitude_m"])
    )
    if len(declarations) != expected_count:
        raise ValidationError("profile receipt count differs")
    profiles: dict[tuple[str, float], dict[str, Any]] = {}
    owned: set[str] = set()
    for declaration in declarations:
        if not isinstance(declaration, dict):
            raise ValidationError("profile declaration is invalid")
        profile = declaration.get("profile")
        altitude = declaration.get("observer_altitude_m")
        if (
            profile not in spec["atmosphere_profiles"]
            or isinstance(altitude, bool)
            or not isinstance(altitude, (int, float))
        ):
            raise ValidationError("profile identity is invalid")
        altitude = float(altitude)
        key = (str(profile), altitude)
        if (
            key in profiles
            or altitude
            not in _all_axis_values(spec["axes"]["observer_altitude_m"])
        ):
            raise ValidationError("profile identity collides")
        expected_names = {
            "atmosphere": _profile_filename(profile, altitude, "atmosphere"),
            "o4": _profile_filename(profile, altitude, "o4"),
            "metadata": _profile_filename(profile, altitude, "metadata"),
        }
        paths: dict[str, Path] = {}
        for role, expected_name in expected_names.items():
            receipt = _validate_receipt_shape(
                declaration.get(role),
                f"profile {key} {role}",
            )
            if Path(receipt["path"]).name != expected_name:
                raise ValidationError(f"profile filename differs: {key} {role}")
            path = _verify_file_receipt(
                artifact,
                receipt,
                f"profile {key} {role}",
            )
            paths[role] = path
            owned.add(receipt["path"])
        metadata = _load_json(paths["metadata"], f"profile metadata {key}")
        if (
            metadata.get("profile") != profile
            or float(metadata.get("observer_altitude_m", math.nan)) != altitude
            or metadata.get("source")
            != spec["atmosphere_profiles"][profile]["path"]
        ):
            raise ValidationError(f"profile metadata identity differs: {key}")
        bottom = _parse_atmosphere_bottom(paths["atmosphere"])
        o4_rows = _parse_o4(paths["o4"])
        declared_pressure = float(
            declaration.get("profile_surface_pressure_hpa", math.nan)
        )
        metadata_pressure = float(
            metadata.get("profile_surface_pressure_hpa", math.nan)
        )
        if (
            _float32(bottom[0]) != _float32(altitude / 1000.0)
            or _float32(o4_rows[-1][0])
            != _float32(altitude / 1000.0)
            or _float32(bottom[1]) != _float32(declared_pressure)
            or declared_pressure != metadata_pressure
        ):
            raise ValidationError(f"profile surface values differ: {key}")
        profiles[key] = {
            "profile_surface_pressure_hpa": declared_pressure,
            "atmosphere_path": paths["atmosphere"],
            "o4_path": paths["o4"],
        }
    return profiles, owned


def _value_token(value: float, places: int) -> str:
    scale = 10**places
    return f"{int(round(float(value) * scale)):0{places + 2}d}"


def _expected_runs(
    spec: dict[str, Any],
    profiles: dict[tuple[str, float], dict[str, Any]],
) -> list[dict[str, Any]]:
    altitude_axis = spec["axes"]["observer_altitude_m"]
    pressure_axis = spec["axes"]["pressure_ratio"]
    altitude_nodes = set(float(value) for value in altitude_axis["training_nodes"])
    pressure_nodes = set(float(value) for value in pressure_axis["training_nodes"])
    altitude_values = _all_axis_values(altitude_axis)
    pressure_values = _all_axis_values(pressure_axis)
    lower_pressure, upper_pressure = (
        float(value)
        for value in pressure_axis["absolute_pressure_hard_bounds_hpa"]
    )
    runs: list[dict[str, Any]] = []
    for profile, declaration in spec["atmosphere_profiles"].items():
        for altitude in altitude_values:
            profile_pressure = float(
                profiles[(profile, altitude)]["profile_surface_pressure_hpa"]
            )
            vertical_grid = _site_relative_vertical_grid(altitude, spec)
            for ratio in pressure_values:
                requested = _canonical_float(profile_pressure * ratio)
                if not lower_pressure <= requested <= upper_pressure:
                    continue
                if altitude in altitude_nodes and ratio in pressure_nodes:
                    partition = "training"
                elif altitude not in altitude_nodes and ratio in pressure_nodes:
                    partition = "altitude_holdout"
                elif altitude in altitude_nodes and ratio not in pressure_nodes:
                    partition = "pressure_holdout"
                else:
                    partition = "joint_holdout"
                for target in spec["axes"]["target_true_altitude_deg"]:
                    runs.append(
                        {
                            "run_id": (
                                f"{profile}__z{int(round(altitude)):04d}"
                                f"__p{_value_token(ratio, 4)}"
                                f"__h{_value_token(float(target), 2)}"
                            ),
                            "partition": partition,
                            "profile": profile,
                            "profile_source_path": declaration["path"],
                            "aerosol_season": declaration["aerosol_season"],
                            "observer_altitude_m": altitude,
                            "vertical_grid_id": spec[
                                "site_relative_vertical_grid"
                            ]["grid_id"],
                            "vertical_grid_level_count": len(vertical_grid),
                            "profile_surface_pressure_hpa": profile_pressure,
                            "pressure_ratio": ratio,
                            "requested_surface_pressure_hpa": requested,
                            "target_true_altitude_deg": float(target),
                            "wavelength_nm": [
                                float(value)
                                for value in spec["axes"]["wavelength_nm"]
                            ],
                        }
                    )
    return runs


def _wavelength_grid_text(run: dict[str, Any]) -> str:
    return "".join(f"{_format_number(value)}\n" for value in run["wavelength_nm"])


def _expected_input(run: dict[str, Any], spec: dict[str, Any]) -> str:
    solver = spec["direct_solver"]
    environment = spec["fixed_environment"]
    cross_sections = solver["cross_sections"]
    alpha = float(environment["angstrom_exponent"])
    beta = _canonical_float(float(environment["aod550"]) * (0.55**alpha))
    target_altitude = float(run["target_true_altitude_deg"])
    vertical_grid = _site_relative_vertical_grid(
        float(run["observer_altitude_m"]),
        spec,
    )
    if len(vertical_grid) != run["vertical_grid_level_count"]:
        raise ValidationError("run vertical-grid level count differs")
    return (
        "\n".join(
            [
                f"data_files_path {DATA_LINK_NAME}",
                "atmosphere_file atmosphere.dat",
                "atm_z_grid "
                + " ".join(_format_number(value) for value in vertical_grid),
                (
                    f"source solar {DATA_LINK_NAME}/"
                    f"{solver['solar_source_path'].removeprefix('data/')}"
                ),
                (
                    f"wavelength {_format_number(min(run['wavelength_nm']))} "
                    f"{_format_number(max(run['wavelength_nm']))}"
                ),
                "wavelength_grid_file wavelength_grid.dat",
                "spline_file wavelength_grid.dat",
                f"mol_abs_param {solver['molecular_absorption']}",
                f"crs_model rayleigh {cross_sections['rayleigh']}",
                f"crs_model O3 {cross_sections['O3']}",
                f"crs_model NO2 {cross_sections['NO2']}",
                f"crs_model O4 {cross_sections['O4']}",
                f"earth_radius {_format_number(solver['earth_radius_km'])}",
                f"pressure {_format_number(run['requested_surface_pressure_hpa'])}",
                f"mol_modify O3 {_format_number(environment['ozone_du'])} DU",
                f"albedo {_format_number(environment['ground_albedo'])}",
                "aerosol_default",
                f"aerosol_vulcan {environment['aerosol_vulcan']}",
                f"aerosol_haze {environment['aerosol_haze']}",
                f"aerosol_season {run['aerosol_season']}",
                (
                    f"aerosol_angstrom {_format_number(alpha)} "
                    f"{_format_number(beta)}"
                ),
                environment["aerosol_scattering_override"],
                "mol_file O4 o4.dat cm_3",
                f"sza {_format_number(90.0 - target_altitude)}",
                f"rte_solver {solver['rte_solver']}",
                solver["geometry"],
                f"number_of_streams {solver['number_of_streams']}",
                f"output_quantity {solver['output_quantity']}",
                "output_user " + " ".join(solver["output_columns"]),
                f"mc_randomseed {solver['random_seed']}",
                "zout 0",
                "quiet",
            ]
        )
        + "\n"
    )


def _parse_output(
    text: str,
    run: dict[str, Any],
) -> list[dict[str, float]]:
    rows = [line.split() for line in text.splitlines() if line.strip()]
    if len(rows) != len(run["wavelength_nm"]):
        raise ValidationError(f"output row count differs: {run['run_id']}")
    projection = math.sin(
        math.radians(float(run["target_true_altitude_deg"]))
    )
    parsed: list[dict[str, float]] = []
    for fields, expected_wavelength in zip(rows, run["wavelength_nm"]):
        if len(fields) != 2:
            raise ValidationError(f"output column count differs: {run['run_id']}")
        try:
            wavelength = float(fields[0])
            horizontal = float(fields[1])
        except ValueError as exc:
            raise ValidationError(f"output is non-numeric: {run['run_id']}") from exc
        transmission = horizontal / projection
        if (
            not math.isclose(
                wavelength,
                float(expected_wavelength),
                rel_tol=0.0,
                abs_tol=5e-4,
            )
            or not math.isfinite(horizontal)
            or not math.isfinite(transmission)
            or not 0.0 < transmission <= 1.0000001
        ):
            raise ValidationError(f"output value is invalid: {run['run_id']}")
        transmission = _canonical_float(transmission)
        parsed.append(
            {
                "wavelength_nm": _canonical_float(wavelength),
                "horizontal_direct_transmittance": _canonical_float(horizontal),
                "geometric_projection_sin_altitude": _canonical_float(projection),
                "direct_spectral_transmission": transmission,
                "optical_depth": _canonical_float(-math.log(transmission)),
                "extinction_magnitude": _canonical_float(
                    -2.5 * math.log10(transmission)
                ),
            }
        )
    return parsed


def _verify_o4_scaling(base_path: Path, run_path: Path, ratio: float) -> None:
    base_rows = _parse_o4(base_path)
    run_rows = _parse_o4(run_path)
    if len(base_rows) != len(run_rows):
        raise ValidationError("run O4 level count differs")
    ratio_squared = ratio * ratio
    for (base_altitude, base_density), (run_altitude, run_density) in zip(
        base_rows,
        run_rows,
    ):
        if (
            base_altitude != run_altitude
            or not math.isclose(
                run_density,
                base_density * ratio_squared,
                rel_tol=3e-7,
                abs_tol=1e-15,
            )
        ):
            raise ValidationError("run O4 pressure scaling differs")


def _verify_runs(
    artifact: Path,
    manifest: dict[str, Any],
    spec: dict[str, Any],
    profiles: dict[tuple[str, float], dict[str, Any]],
    expected_runs: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, float]]], set[str]]:
    receipts = manifest.get("runs")
    if not isinstance(receipts, list) or len(receipts) != len(expected_runs):
        raise ValidationError("run receipt count differs")
    receipt_by_id: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(
            receipt.get("run_id"),
            str,
        ):
            raise ValidationError("run receipt identity is invalid")
        if receipt["run_id"] in receipt_by_id:
            raise ValidationError("run receipt identity collides")
        receipt_by_id[receipt["run_id"]] = receipt
    expected_ids = {run["run_id"] for run in expected_runs}
    if set(receipt_by_id) != expected_ids:
        raise ValidationError("run identity inventory differs")

    results: dict[str, list[dict[str, float]]] = {}
    owned: set[str] = set()
    for run in expected_runs:
        receipt = receipt_by_id[run["run_id"]]
        if receipt.get("partition") != run["partition"]:
            raise ValidationError(f"run partition differs: {run['run_id']}")
        file_receipts = receipt.get("files")
        if not isinstance(file_receipts, list) or len(file_receipts) != len(
            RUN_FILES
        ):
            raise ValidationError(f"run file receipts differ: {run['run_id']}")
        paths: dict[str, Path] = {}
        for file_receipt in file_receipts:
            validated = _validate_receipt_shape(
                file_receipt,
                f"run {run['run_id']} file",
            )
            filename = Path(validated["path"]).name
            if filename not in RUN_FILES or filename in paths:
                raise ValidationError(f"run file inventory differs: {run['run_id']}")
            paths[filename] = _verify_file_receipt(
                artifact,
                validated,
                f"run {run['run_id']} {filename}",
            )
            owned.add(validated["path"])
        if set(paths) != RUN_FILES:
            raise ValidationError(f"run filenames differ: {run['run_id']}")
        if (
            paths["input.inp"].read_text(encoding="utf-8")
            != _expected_input(run, spec)
            or paths["wavelength_grid.dat"].read_text(encoding="utf-8")
            != _wavelength_grid_text(run)
            or paths["randomseed"].read_text(encoding="utf-8").strip()
            != str(spec["direct_solver"]["random_seed"])
        ):
            raise ValidationError(f"run input differs: {run['run_id']}")
        profile = profiles[(run["profile"], run["observer_altitude_m"])]
        if (
            paths["atmosphere.dat"].read_bytes()
            != profile["atmosphere_path"].read_bytes()
        ):
            raise ValidationError(f"run atmosphere differs: {run['run_id']}")
        _verify_o4_scaling(
            profile["o4_path"],
            paths["o4.dat"],
            float(run["pressure_ratio"]),
        )
        independently_parsed_result = _parse_output(
            paths["stdout.txt"].read_text(encoding="utf-8"),
            run,
        )
        stored_payload = _load_json(
            paths["result.json"],
            f"run result {run['run_id']}",
        )
        if (
            paths["result.json"].read_bytes()
            != _canonical_json_bytes(stored_payload)
            or stored_payload.get("schema") != RUN_SCHEMA
            or stored_payload.get("run") != run
            or not isinstance(stored_payload.get("result"), list)
        ):
            raise ValidationError(f"run result payload differs: {run['run_id']}")
        stored_result = stored_payload["result"]
        _assert_cross_platform_equal(
            stored_result,
            independently_parsed_result,
            f"run result {run['run_id']}",
        )
        if receipt.get("result") != stored_result:
            raise ValidationError(f"manifest run result differs: {run['run_id']}")
        results[run["run_id"]] = stored_result
    return results, owned


def _bracket(nodes: list[float], value: float) -> tuple[float, float]:
    if value in nodes:
        return value, value
    for lower, upper in zip(nodes, nodes[1:]):
        if lower < value < upper:
            return lower, upper
    raise ValidationError(f"holdout lies outside training nodes: {value}")


def _linear(lower_value: float, upper_value: float, fraction: float) -> float:
    return lower_value + fraction * (upper_value - lower_value)


def _bilinear(
    corners: dict[tuple[float, float], float],
    altitude_bracket: tuple[float, float],
    pressure_bracket: tuple[float, float],
    altitude: float,
    pressure: float,
) -> float:
    z0, z1 = altitude_bracket
    p0, p1 = pressure_bracket
    z_fraction = 0.0 if z0 == z1 else (altitude - z0) / (z1 - z0)
    p_fraction = 0.0 if p0 == p1 else (pressure - p0) / (p1 - p0)
    low = _linear(corners[(z0, p0)], corners[(z1, p0)], z_fraction)
    high = _linear(corners[(z0, p1)], corners[(z1, p1)], z_fraction)
    return _linear(low, high, p_fraction)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return _linear(ordered[lower], ordered[upper], position - lower)


def _independent_summary(
    expected_runs: list[dict[str, Any]],
    results: dict[str, list[dict[str, float]]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    altitude_nodes = [
        float(value)
        for value in spec["axes"]["observer_altitude_m"]["training_nodes"]
    ]
    pressure_nodes = [
        float(value)
        for value in spec["axes"]["pressure_ratio"]["training_nodes"]
    ]
    lookup: dict[
        tuple[str, float, float, float, float],
        dict[str, float],
    ] = {}
    for run in expected_runs:
        if run["partition"] != "training":
            continue
        for row in results[run["run_id"]]:
            lookup[
                (
                    run["profile"],
                    run["target_true_altitude_deg"],
                    row["wavelength_nm"],
                    run["observer_altitude_m"],
                    run["pressure_ratio"],
                )
            ] = row

    methods = {
        name: {
            "errors": [],
            "relative_errors": [],
            "partitions": {
                "altitude_holdout": [],
                "pressure_holdout": [],
                "joint_holdout": [],
            },
            "worst": None,
        }
        for name in spec["interpolation_candidates"]
    }
    evaluated = 0
    excluded = 0
    excluded_partitions = {
        "altitude_holdout": 0,
        "pressure_holdout": 0,
        "joint_holdout": 0,
    }
    holdout_values = 0
    for run in expected_runs:
        partition = run["partition"]
        if partition == "training":
            continue
        holdout_values += len(results[run["run_id"]])
        altitude = run["observer_altitude_m"]
        pressure = run["pressure_ratio"]
        z_bracket = _bracket(altitude_nodes, altitude)
        p_bracket = _bracket(pressure_nodes, pressure)
        for truth in results[run["run_id"]]:
            corners: dict[tuple[float, float], dict[str, float]] = {}
            for z_value in set(z_bracket):
                for p_value in set(p_bracket):
                    key = (
                        run["profile"],
                        run["target_true_altitude_deg"],
                        truth["wavelength_nm"],
                        z_value,
                        p_value,
                    )
                    if key in lookup:
                        corners[(z_value, p_value)] = lookup[key]
            required = {
                (z_value, p_value)
                for z_value in set(z_bracket)
                for p_value in set(p_bracket)
            }
            if set(corners) != required:
                excluded += 1
                excluded_partitions[partition] += 1
                continue
            evaluated += 1
            for name, accumulator in methods.items():
                if name == "bilinear_direct_transmission":
                    predicted_transmission = _bilinear(
                        {
                            key: row["direct_spectral_transmission"]
                            for key, row in corners.items()
                        },
                        z_bracket,
                        p_bracket,
                        altitude,
                        pressure,
                    )
                    predicted_extinction = -2.5 * math.log10(
                        predicted_transmission
                    )
                elif name == "bilinear_optical_depth":
                    tau = _bilinear(
                        {
                            key: row["optical_depth"]
                            for key, row in corners.items()
                        },
                        z_bracket,
                        p_bracket,
                        altitude,
                        pressure,
                    )
                    predicted_transmission = math.exp(-tau)
                    predicted_extinction = (2.5 / math.log(10.0)) * tau
                else:
                    predicted_extinction = _bilinear(
                        {
                            key: row["extinction_magnitude"]
                            for key, row in corners.items()
                        },
                        z_bracket,
                        p_bracket,
                        altitude,
                        pressure,
                    )
                    predicted_transmission = 10.0 ** (
                        -predicted_extinction / 2.5
                    )
                error = abs(
                    predicted_extinction - truth["extinction_magnitude"]
                )
                relative_error = abs(
                    predicted_transmission
                    - truth["direct_spectral_transmission"]
                ) / truth["direct_spectral_transmission"]
                accumulator["errors"].append(error)
                accumulator["relative_errors"].append(relative_error)
                accumulator["partitions"][partition].append(error)
                worst = accumulator["worst"]
                if worst is None or error > worst["absolute_error_mag"]:
                    accumulator["worst"] = {
                        "run_id": run["run_id"],
                        "profile": run["profile"],
                        "partition": partition,
                        "observer_altitude_m": altitude,
                        "pressure_ratio": pressure,
                        "target_true_altitude_deg": run[
                            "target_true_altitude_deg"
                        ],
                        "wavelength_nm": truth["wavelength_nm"],
                        "truth_extinction_magnitude": truth[
                            "extinction_magnitude"
                        ],
                        "predicted_extinction_magnitude": _canonical_float(
                            predicted_extinction
                        ),
                        "absolute_error_mag": _canonical_float(error),
                        "relative_transmission_error": _canonical_float(
                            relative_error
                        ),
                    }

    if evaluated == 0:
        raise ValidationError("no holdout values were evaluated")
    method_summary: dict[str, Any] = {}
    for name, accumulator in methods.items():
        errors = accumulator["errors"]
        relative_errors = accumulator["relative_errors"]
        method_summary[name] = {
            "evaluated_holdout_value_count": len(errors),
            "maximum_absolute_extinction_error_mag": _canonical_float(max(errors)),
            "mean_absolute_extinction_error_mag": _canonical_float(
                sum(errors) / len(errors)
            ),
            "p95_absolute_extinction_error_mag": _canonical_float(
                _percentile(errors, 0.95)
            ),
            "maximum_relative_transmission_error": _canonical_float(
                max(relative_errors)
            ),
            "partition_maximum_absolute_extinction_error_mag": {
                partition: _canonical_float(max(values))
                for partition, values in accumulator["partitions"].items()
                if values
            },
            "worst_case": accumulator["worst"],
        }
    partitions: dict[str, int] = {}
    for run in expected_runs:
        partitions[run["partition"]] = partitions.get(run["partition"], 0) + 1
    return {
        "schema": (
            "moira.visibility-altitude-pressure-interpolation-summary/v1"
        ),
        "run_count": len(expected_runs),
        "partition_run_counts": partitions,
        "spectral_value_count": len(expected_runs)
        * len(spec["axes"]["wavelength_nm"]),
        "training_spectral_value_count": partitions["training"]
        * len(spec["axes"]["wavelength_nm"]),
        "holdout_spectral_value_count": holdout_values,
        "evaluated_holdout_value_count": evaluated,
        "excluded_holdout_value_count": excluded,
        "excluded_holdout_values_by_partition": excluded_partitions,
        "excluded_reason": (
            "hard_pressure_bounds_remove_one_or_more_required_training_corners"
        ),
        "interpolation_methods": method_summary,
        "required_method": spec["interpolation_admission"]["required_method"],
        "effective_domain_law": (
            "inside_hard_bounds_and_inside_a_complete_valid_training_cell"
        ),
        "pressure_o4_closure": spec["pressure_o4_closure"],
        "site_relative_vertical_grid": spec["site_relative_vertical_grid"],
    }


def _enforce_acceptance(summary: dict[str, Any], spec: dict[str, Any]) -> None:
    if summary["evaluated_holdout_value_count"] <= 0:
        raise ValidationError("no holdout values were evaluated")
    admission = spec["interpolation_admission"]
    method = summary["interpolation_methods"][admission["required_method"]]
    for metric, threshold in (
        (
            "maximum_absolute_extinction_error_mag",
            admission["maximum_absolute_extinction_error_mag"],
        ),
        (
            "p95_absolute_extinction_error_mag",
            admission["p95_absolute_extinction_error_mag"],
        ),
        (
            "maximum_relative_transmission_error",
            admission["maximum_relative_transmission_error"],
        ),
    ):
        if float(method[metric]) > float(threshold):
            raise ValidationError(
                f"interpolation threshold failed: {metric}={method[metric]}"
            )


def _verify_current_repo_tooling(
    manifest: dict[str, Any],
    spec_path: Path,
    spec: dict[str, Any],
) -> None:
    expected_paths = {
        "spec": spec_path,
        "builder": BUILDER_PATH,
        "validator": Path(__file__).resolve(),
        "construction_dependency": (
            REPO_ROOT / spec["construction_dependency"]["path"]
        ),
    }
    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict) or set(tooling) != set(expected_paths):
        raise ValidationError("tooling inventory differs")
    for label, path in expected_paths.items():
        if not path.is_file() or tooling[label] != _repo_receipt(path):
            raise ValidationError(f"current tooling differs: {label}")

    predecessor = manifest.get("predecessor")
    if not isinstance(predecessor, dict) or set(predecessor) != {
        "spec",
        "builder",
        "validator",
        "checkpoint",
    }:
        raise ValidationError("predecessor inventory differs")
    for label in predecessor:
        declaration = {
            "path": spec["predecessor"][f"{label}_path"],
            "bytes": spec["predecessor"][f"{label}_bytes"],
            "sha256": spec["predecessor"][f"{label}_sha256"],
        }
        path = REPO_ROOT / declaration["path"]
        if not path.is_file() or predecessor[label] != _repo_receipt(path):
            raise ValidationError(f"predecessor differs: {label}")
    grid_declaration = spec["vertical_grid_predecessor"]
    grid_path = REPO_ROOT / grid_declaration["path"]
    expected_grid_predecessor = {
        "path": grid_declaration["path"],
        "bytes": grid_declaration["bytes"],
        "sha256": grid_declaration["sha256"],
    }
    if (
        not grid_path.is_file()
        or manifest.get("vertical_grid_predecessor")
        != expected_grid_predecessor
        or _repo_receipt(grid_path) != expected_grid_predecessor
    ):
        raise ValidationError("vertical-grid predecessor receipt differs")
    expected_refinements = [
        {
            "path": declaration["receipt_path"],
            "bytes": declaration["receipt_bytes"],
            "sha256": declaration["receipt_sha256"],
        }
        for declaration in spec["refinement_from_failed_designs"]
    ]
    actual_refinements = manifest.get("refinements")
    if actual_refinements != expected_refinements:
        raise ValidationError("failed-design refinement inventory differs")
    for index, declaration in enumerate(expected_refinements):
        path = REPO_ROOT / declaration["path"]
        if not path.is_file() or _repo_receipt(path) != declaration:
            raise ValidationError(
                f"failed-design refinement receipt differs: {index}"
            )


def _verify_source_manifest(
    manifest: dict[str, Any],
    spec: dict[str, Any],
) -> None:
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValidationError("source manifest is missing")
    archive = _validate_receipt_shape(source.get("archive"), "source archive")
    if (
        archive["bytes"] != spec["libradtran_source"]["archive_bytes"]
        or archive["sha256"] != spec["libradtran_source"]["archive_sha256"]
    ):
        raise ValidationError("source archive identity differs")
    uvspec = _validate_receipt_shape(source.get("uvspec"), "uvspec")
    if uvspec["sha256"] != spec["libradtran_source"]["uvspec_sha256"]:
        raise ValidationError("uvspec identity differs")
    if spec["libradtran_source"]["uvspec_version"] not in str(
        source.get("uvspec_version")
    ):
        raise ValidationError("uvspec version differs")
    for key, declarations in (
        ("source_files", spec["libradtran_source"]["source_files"]),
        (
            "atmosphere_profiles",
            list(spec["atmosphere_profiles"].values()),
        ),
    ):
        receipts = source.get(key)
        if not isinstance(receipts, list) or len(receipts) != len(declarations):
            raise ValidationError(f"source {key} inventory differs")
        expected = [
            {
                "path": declaration["path"],
                "bytes": declaration["bytes"],
                "sha256": declaration["sha256"],
            }
            for declaration in declarations
        ]
        if receipts != expected:
            raise ValidationError(f"source {key} receipts differ")
    fingerprint_payload = {
        "tooling": manifest["tooling"],
        "predecessor": manifest["predecessor"],
        "vertical_grid_predecessor": manifest["vertical_grid_predecessor"],
        "refinements": manifest["refinements"],
        "source_archive": archive,
        "uvspec": uvspec,
        "source_files": source["source_files"],
        "atmosphere_profiles": source["atmosphere_profiles"],
    }
    if manifest.get("generation_fingerprint") != _sha256_bytes(
        _compact_json_bytes(fingerprint_payload)
    ):
        raise ValidationError("generation fingerprint differs")


def _verify_inventory(
    artifact: Path,
    owned: set[str],
) -> None:
    actual: set[str] = set()
    for path in artifact.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"artifact contains a symlink: {path}")
        if path.is_file():
            actual.add(path.relative_to(artifact).as_posix())
    expected = {*owned, MANIFEST_NAME, SUMMARY_NAME}
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValidationError(
            f"artifact inventory differs: missing={missing[:5]} "
            f"unexpected={unexpected[:5]}"
        )


def validate_artifact(
    artifact: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    artifact = artifact.resolve()
    spec_path = spec_path.resolve()
    if not artifact.is_dir() or artifact.is_symlink():
        raise ValidationError("artifact root is missing or is a symlink")
    spec = _load_spec(spec_path)
    manifest_path = artifact / MANIFEST_NAME
    manifest = _load_json(manifest_path, "artifact manifest")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("status") != ARTIFACT_STATUS
        or manifest.get("spec_id") != spec["spec_id"]
        or manifest.get("runtime_boundary") != spec["runtime_boundary"]
        or manifest.get("axes") != spec["axes"]
        or manifest.get("fixed_environment") != spec["fixed_environment"]
        or manifest.get("pressure_o4_closure")
        != spec["pressure_o4_closure"]
        or manifest.get("site_relative_vertical_grid")
        != spec["site_relative_vertical_grid"]
        or manifest.get("direct_solver") != spec["direct_solver"]
        or manifest.get("interpolation_admission")
        != spec["interpolation_admission"]
    ):
        raise ValidationError("manifest contract differs")
    _verify_current_repo_tooling(manifest, spec_path, spec)
    _verify_source_manifest(manifest, spec)
    profiles, owned_profiles = _verify_profiles(artifact, manifest, spec)
    expected_runs = _expected_runs(spec, profiles)
    results, owned_runs = _verify_runs(
        artifact,
        manifest,
        spec,
        profiles,
        expected_runs,
    )
    summary_receipt = _validate_receipt_shape(
        manifest.get("summary"),
        "summary",
    )
    if summary_receipt["path"] != SUMMARY_NAME:
        raise ValidationError("summary path differs")
    summary_path = _verify_file_receipt(
        artifact,
        summary_receipt,
        "summary",
    )
    committed_summary = _load_json(summary_path, "summary")
    if summary_path.read_bytes() != _canonical_json_bytes(committed_summary):
        raise ValidationError("summary serialization is not canonical")
    independent_summary = _independent_summary(expected_runs, results, spec)
    _assert_cross_platform_equal(
        committed_summary,
        independent_summary,
        "independent summary",
    )
    _enforce_acceptance(independent_summary, spec)
    _verify_inventory(
        artifact,
        {*owned_profiles, *owned_runs},
    )
    return {
        "artifact": str(artifact),
        "generation_fingerprint": manifest["generation_fingerprint"],
        "manifest_sha256": _sha256_file(manifest_path),
        "run_count": len(expected_runs),
        "evaluated_holdout_value_count": independent_summary[
            "evaluated_holdout_value_count"
        ],
        "excluded_holdout_value_count": independent_summary[
            "excluded_holdout_value_count"
        ],
        "required_method": independent_summary["required_method"],
        "required_method_metrics": independent_summary[
            "interpolation_methods"
        ][independent_summary["required_method"]],
        "validated": True,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Phase 1 altitude/pressure interpolation artifact."
        )
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = validate_artifact(args.artifact, spec_path=args.spec)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
