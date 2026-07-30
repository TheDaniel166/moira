#!/usr/bin/env python3
"""Independently validate a Phase 1 radiance/response artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
import struct
import sys
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_radiance_response_probe_spec.json"
)
BUILDER_PATH = (
    REPO_ROOT / "scripts" / "build_visibility_radiance_response_probe.py"
)
SPEC_SCHEMA = "moira.visibility-radiance-response-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-radiance-response-artifact/v1"
RUN_SCHEMA = "moira.visibility-radiance-response-run/v1"
MANIFEST_NAME = "artifact-manifest.json"
SUMMARY_NAME = "summary.json"
DATA_LINK_NAME = "libradtran_data"


class ValidationError(ValueError):
    """Raised when a radiance/response artifact fails validation."""


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise ValidationError(f"{label} is unsafe")
    return path


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{label} is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{label} must be an object")
    return payload


def _verify_file(
    root: Path,
    receipt: dict[str, Any],
    label: str,
) -> Path:
    relative = _safe_relative(receipt.get("path"), f"{label}.path")
    path = root.joinpath(*relative.parts)
    if (
        not path.is_file()
        or path.is_symlink()
        or not isinstance(receipt.get("bytes"), int)
        or receipt["bytes"] < 0
        or path.stat().st_size != receipt["bytes"]
        or not isinstance(receipt.get("sha256"), str)
        or len(receipt["sha256"]) != 64
        or _sha256_file(path) != receipt["sha256"]
    ):
        raise ValidationError(f"{label} file receipt differs")
    return path


def _assert_numeric_equal(
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
            _assert_numeric_equal(
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
            _assert_numeric_equal(
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
        left = float(actual)
        right = float(expected)
        if (
            not math.isfinite(left)
            or not math.isfinite(right)
            or not math.isclose(
                left,
                right,
                rel_tol=5e-12,
                abs_tol=5e-14,
            )
        ):
            raise ValidationError(f"{label} numeric value differs")
        return
    if actual != expected:
        raise ValidationError(f"{label} differs")


def _vertical_grid(spec: dict[str, Any]) -> list[float]:
    declaration = spec["vertical_grid"]
    levels: list[Decimal] = []
    previous_stop: Decimal | None = None
    for item in declaration["segments_km"]:
        start = Decimal(str(item["start"]))
        stop = Decimal(str(item["stop"]))
        step = Decimal(str(item["step"]))
        if (
            start >= stop
            or (stop - start) % step != 0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise ValidationError("vertical-grid segments differ")
        for offset in range(int((stop - start) / step) + 1):
            value = start + offset * step
            if not levels or value != levels[-1]:
                levels.append(value)
        previous_stop = stop
    result = [float(value) for value in levels]
    if (
        len(result) != declaration["expected_level_count"]
        or result[0] != 0.0
        or result[-1] != 120.0
    ):
        raise ValidationError("vertical-grid identity differs")
    return result


def _direct_altitude_grid(
    spec: dict[str, Any],
) -> tuple[list[float], list[float]]:
    direct = spec["direct_solver"]
    segments = direct.get("training_grid_segments_deg")
    if not isinstance(segments, list):
        raise ValidationError("direct-grid segments differ")
    nodes: list[Decimal] = []
    previous_stop: Decimal | None = None
    for item in segments:
        if not isinstance(item, dict) or set(item) != {
            "start",
            "stop",
            "step",
        }:
            raise ValidationError("direct-grid segment shape differs")
        start = Decimal(str(item["start"]))
        stop = Decimal(str(item["stop"]))
        step = Decimal(str(item["step"]))
        if (
            start < Decimal("0.25")
            or stop > Decimal("45")
            or start >= stop
            or step <= 0
            or (stop - start) % step != 0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise ValidationError("direct-grid segment differs")
        for offset in range(int((stop - start) / step) + 1):
            value = start + offset * step
            if not nodes or nodes[-1] != value:
                nodes.append(value)
        previous_stop = stop
    holdouts = [
        (left + right) / 2 for left, right in zip(nodes, nodes[1:])
    ]
    try:
        declared_nodes = [
            Decimal(str(value))
            for value in direct["training_target_true_altitude_deg"]
        ]
        declared_holdouts = [
            Decimal(str(value))
            for value in direct[
                "reserved_target_true_altitude_holdouts_deg"
            ]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("direct-grid inventory differs") from exc
    if (
        nodes != declared_nodes
        or holdouts != declared_holdouts
        or len(nodes) != direct.get("training_node_count")
        or len(holdouts) != direct.get("reserved_holdout_count")
        or direct.get("training_grid_selection")
        != (
            "piecewise_dense_grid_from_exposed_v7_curvature_with_"
            "minimum_sixfold_near_horizon_interval_reduction"
        )
        or direct.get("reserved_holdout_selection")
        != (
            "untouched_midpoint_between_each_adjacent_dense_"
            "training_node"
        )
    ):
        raise ValidationError("direct training or holdout grid differs")
    return (
        [float(value) for value in nodes],
        [float(value) for value in holdouts],
    )


def _load_spec(path: Path) -> dict[str, Any]:
    spec = _load_json(path, "specification")
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("status") != "phase1_reference_build_not_engine_runtime"
        or spec.get("deep_twilight_law", {}).get(
            "solar_altitude_below_table"
        )
        != "not_evaluable_for_modeled_twilight_background"
        or spec.get("deep_twilight_law", {}).get(
            "monte_carlo_non_detection_is_zero"
        )
        is not False
    ):
        raise ValidationError("specification identity differs")
    runtime = spec.get("runtime_boundary")
    if not isinstance(runtime, dict) or any(
        runtime.get(field) is not False
        for field in (
            "network_allowed",
            "automatic_download_allowed",
            "engine_dependency_allowed",
            "engine_runtime_invocation_allowed",
            "libRadtran_redistribution_allowed",
            "REPTRAN_redistribution_allowed",
            "engine_changes_authorized",
        )
    ):
        raise ValidationError("runtime boundary differs")
    solver = spec.get("radiance_solver")
    if (
        not isinstance(solver, dict)
        or solver.get("spectral_importance_sampling") != "mc_spectral_is"
        or solver.get("spectral_importance_reference_wavelength_nm")
        != solver.get("normalization_wavelength_nm")
        or solver.get("spectral_importance_reference_wavelength_nm") != 531.0
        or solver.get("absolute_anchor_wavelength_nm") != 531.0
        or solver.get("spectral_importance_reference_selection")
        != (
            "training_diagnostic_balanced_photopic_scotopic_"
            "relative_standard_error"
        )
    ):
        raise ValidationError(
            "spectral importance reference differs"
        )
    if (
        runtime.get("generated_numerical_products_only") is not True
        or runtime.get("CIE_redistribution_in_data_pack_requires_notice")
        is not True
    ):
        raise ValidationError("generated-data boundary differs")
    _vertical_grid(spec)
    grid = spec["radiance_grid"]
    training_count = math.prod(
        len(grid[axis]["training_nodes"])
        for axis in (
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
        )
    )
    holdout_count = math.prod(
        len(grid[axis]["reserved_holdouts"])
        for axis in (
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
        )
    )
    response_holdouts = {
        tuple(float(value) for value in row)
        for row in grid["response_holdouts"]
    }
    monte_carlo = spec["adaptive_monte_carlo"]
    training_seeds = monte_carlo.get("training_random_seeds", [])
    holdout_seeds = monte_carlo.get("holdout_random_seeds", [])
    shape_training_seeds = monte_carlo.get(
        "spectral_shape_training_random_seeds", []
    )
    shape_holdout_seeds = monte_carlo.get(
        "spectral_shape_holdout_random_seeds", []
    )
    shape_photon_rows = monte_carlo.get(
        "spectral_shape_photons_per_seed_by_solar_center_altitude", []
    )
    shape_photon_schedule = (
        {
            float(row["solar_center_altitude_deg"]): int(
                row["photons_per_seed"]
            )
            for row in shape_photon_rows
            if isinstance(row, dict)
        }
        if isinstance(shape_photon_rows, list)
        else {}
    )
    if (
        training_count != grid["training_point_count"]
        or holdout_count != grid["monochromatic_holdout_point_count"]
        or len(response_holdouts) != grid["response_holdout_point_count"]
        or grid.get("response_holdout_selection")
        != (
            "complementary_latin_square_from_nine_untouched_"
            "originally_unselected_midpoint_combinations"
        )
        or grid.get("superseded_response_holdout_selection")
        != (
            "quarantined_after_partial_execution_by_bound_"
            "failed_checkpoint"
        )
        or monte_carlo.get("anchor_minimum_seed_count") != 3
        or monte_carlo.get("anchor_maximum_seed_count") != 16
        or len(training_seeds) != 16
        or len(holdout_seeds) != 16
        or len(set(training_seeds)) != 16
        or len(set(holdout_seeds)) != 16
        or not set(training_seeds).isdisjoint(holdout_seeds)
        or monte_carlo.get("spectral_shape_maximum_seed_count") != 8
        or len(shape_training_seeds) != 8
        or len(shape_holdout_seeds) != 8
        or len(set(shape_training_seeds)) != 8
        or len(set(shape_holdout_seeds)) != 8
        or not set(shape_training_seeds).isdisjoint(shape_holdout_seeds)
        or len(shape_photon_schedule) != 7
        or shape_photon_schedule
        != {
            -9.0: 100000,
            -7.5: 100000,
            -6.0: 30000,
            -4.5: 10000,
            -3.0: 10000,
            -1.5: 10000,
            0.0: 10000,
        }
        or monte_carlo.get("spectral_shape_photon_adaptation_basis")
        != (
            "training_and_quarantined_exposed_response_holdout_"
            "zero_normalization_only"
        )
        or spec["acceptance"][
            "thresholds_may_not_change_after_holdout_execution"
        ]
        is not True
        or spec["acceptance"].get(
            "monochromatic_reference_surface_shipped_in_data_pack"
        )
        is not False
        or spec["acceptance"].get(
            "monochromatic_reference_surface_used_by_runtime_interpolation"
        )
        is not False
        or spec["acceptance"].get("monochromatic_reference_role")
        != (
            "reported_intermediate_diagnostic_not_artifact_"
            "admission_gate"
        )
    ):
        raise ValidationError("grid or acceptance count differs")
    _direct_altitude_grid(spec)
    return spec


def _format_number(value: float | int) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    number = float(value)
    if number == 0.0:
        return "0"
    return format(number, ".15g")


def _common_input(
    spec: dict[str, Any],
    target_altitude_deg: float,
) -> list[str]:
    environment = spec["fixed_environment"]
    solver = spec["radiance_solver"]
    beta = float(environment["aod550"]) * (
        0.55 ** float(environment["angstrom_exponent"])
    )
    return [
        f"data_files_path {DATA_LINK_NAME}",
        (
            f"atmosphere_file {DATA_LINK_NAME}/"
            f"{environment['atmosphere_file'].removeprefix('data/')}"
        ),
        (
            f"source solar {DATA_LINK_NAME}/"
            f"{environment['solar_source'].removeprefix('data/')}"
        ),
        "atm_z_grid "
        + " ".join(_format_number(value) for value in _vertical_grid(spec)),
        f"earth_radius {_format_number(solver['earth_radius_km'])}",
        f"pressure {_format_number(environment['surface_pressure_hpa'])}",
        f"mol_modify O3 {_format_number(environment['ozone_du'])} DU",
        f"albedo {_format_number(environment['ground_albedo'])}",
        "aerosol_default",
        f"aerosol_vulcan {environment['aerosol_vulcan']}",
        f"aerosol_haze {environment['aerosol_haze']}",
        f"aerosol_season {environment['aerosol_season']}",
        (
            f"aerosol_angstrom "
            f"{_format_number(environment['angstrom_exponent'])} "
            f"{_format_number(beta)}"
        ),
        (
            "umu "
            + _format_number(
                -math.sin(math.radians(float(target_altitude_deg)))
            )
        ),
    ]


def _expected_input(run: dict[str, Any], spec: dict[str, Any]) -> str:
    kind = run["kind"]
    lines = _common_input(
        spec,
        float(run["target_true_altitude_deg"]),
    )
    if kind == "anchor":
        anchor_wavelength = spec["radiance_solver"][
            "absolute_anchor_wavelength_nm"
        ]
        lines[3:3] = [
            (
                "wavelength "
                f"{_format_number(anchor_wavelength)} "
                f"{_format_number(anchor_wavelength)}"
            ),
            "mol_abs_param reptran fine",
        ]
    elif kind in {"shape", "direct"}:
        lines[3:3] = [
            "wavelength 380 780",
            "mol_abs_param reptran fine",
        ]
    else:
        raise ValidationError(f"unknown run kind: {kind}")
    if kind in {"anchor", "shape"}:
        lines.extend(
            [
                (
                    "sza "
                    + _format_number(
                        90.0 - float(run["solar_center_altitude_deg"])
                    )
                ),
                "phi0 0",
                "rte_solver mystic",
                "mc_spherical 1D",
                f"mc_photons {run['photon_count']}",
                f"mc_randomseed {run['random_seed']}",
                "mc_escape",
                "mc_std",
                "mc_vroom on",
            ]
        )
        if kind == "shape":
            lines.append(
                "mc_spectral_is "
                + _format_number(
                    spec["radiance_solver"][
                        "spectral_importance_reference_wavelength_nm"
                    ]
                )
            )
        lines.extend(
            [
                "zout 0",
                f"phi {_format_number(run['relative_solar_azimuth_deg'])}",
                "quiet",
            ]
        )
    else:
        lines.extend(
            [
                "aerosol_modify ssa set 0",
                (
                    "sza "
                    + _format_number(
                        90.0 - float(run["target_true_altitude_deg"])
                    )
                ),
                "rte_solver twostr",
                "pseudospherical",
                "mc_randomseed 49979687",
                "output_quantity transmittance",
                "output_user lambda edir",
                "zout 0",
                "quiet",
            ]
        )
    return "\n".join(lines) + "\n"


def _assert_input_equivalent(
    actual_bytes: bytes,
    expected_text: str,
    run_id: str,
) -> None:
    expected_bytes = expected_text.encode("utf-8")
    if actual_bytes == expected_bytes:
        return
    try:
        actual_lines = actual_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValidationError(f"run input differs: {run_id}") from exc
    expected_lines = expected_text.splitlines()
    if len(actual_lines) != len(expected_lines):
        raise ValidationError(f"run input differs: {run_id}")
    relaxed_umu_count = 0
    for actual, expected in zip(actual_lines, expected_lines):
        if actual == expected:
            continue
        actual_fields = actual.split()
        expected_fields = expected.split()
        if (
            len(actual_fields) == 2
            and len(expected_fields) == 2
            and actual_fields[0] == expected_fields[0] == "umu"
        ):
            try:
                actual_value = float(actual_fields[1])
                expected_value = float(expected_fields[1])
            except ValueError as exc:
                raise ValidationError(
                    f"run input differs: {run_id}"
                ) from exc
            if (
                math.isfinite(actual_value)
                and math.isfinite(expected_value)
                and math.isclose(
                    actual_value,
                    expected_value,
                    rel_tol=5e-15,
                    abs_tol=5e-16,
                )
            ):
                relaxed_umu_count += 1
                continue
        raise ValidationError(f"run input differs: {run_id}")
    if relaxed_umu_count != 1:
        raise ValidationError(f"run input differs: {run_id}")


def _load_cie(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) != 2:
                raise ValidationError("CIE row shape differs")
            wavelength = int(row[0])
            value = float(row[1])
            if wavelength in result or not 0.0 <= value <= 1.0:
                raise ValidationError("CIE row differs")
            result[wavelength] = value
    if sorted(result) != list(range(min(result), max(result) + 1)):
        raise ValidationError("CIE grid differs")
    return result


def _cie_value(table: dict[int, float], wavelength: float) -> float:
    lower = math.floor(wavelength)
    upper = math.ceil(wavelength)
    if lower not in table or upper not in table:
        return 0.0
    if lower == upper:
        return table[lower]
    fraction = wavelength - lower
    return table[lower] * (1.0 - fraction) + table[upper] * fraction


def _parse_radiance(
    path: Path,
    expected_rows: int,
    expected_single_wavelength_nm: float | None = None,
) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 2:
            raise ValidationError("radiance row is malformed")
        wavelength = float(fields[0])
        value = float(fields[-1])
        if (
            not math.isfinite(wavelength)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValidationError("radiance row is invalid")
        wavelengths.append(wavelength)
        values.append(value)
    if len(wavelengths) != expected_rows:
        raise ValidationError("radiance row count differs")
    if expected_rows == 1:
        if (
            expected_single_wavelength_nm is None
            or not math.isclose(
                wavelengths[0],
                expected_single_wavelength_nm,
                abs_tol=1e-6,
            )
        ):
            raise ValidationError("anchor wavelength differs")
    else:
        for index, wavelength in enumerate(wavelengths):
            if not math.isclose(
                wavelength,
                380.0 + index * 0.05,
                abs_tol=1.1e-4,
            ):
                raise ValidationError("spectral wavelength differs")
    return wavelengths, values


def _response_integral(
    wavelengths: list[float],
    radiances: list[float],
    table: dict[int, float],
) -> float:
    weighted = [
        value * _cie_value(table, wavelength)
        for wavelength, value in zip(wavelengths, radiances)
    ]
    return math.fsum(
        (right_wavelength - left_wavelength)
        * (left_value + right_value)
        / 2.0
        for left_wavelength, right_wavelength, left_value, right_value in zip(
            wavelengths,
            wavelengths[1:],
            weighted,
            weighted[1:],
        )
    )


def _independent_result(
    directory: Path,
    run: dict[str, Any],
    spec: dict[str, Any],
    cie: dict[str, dict[int, float]],
) -> dict[str, Any]:
    kind = run["kind"]
    if kind == "anchor":
        anchor_wavelength = spec["radiance_solver"][
            "absolute_anchor_wavelength_nm"
        ]
        _, radiance = _parse_radiance(
            directory / "mc.rad.spc",
            1,
            anchor_wavelength,
        )
        _, deviation = _parse_radiance(
            directory / "mc.rad.std.spc",
            1,
            anchor_wavelength,
        )
        if radiance[0] <= 0:
            raise ValidationError("anchor radiance is nonpositive")
        return {
            "reference_radiance_mw_m2_nm_sr": radiance[0],
            "reported_standard_deviation_mw_m2_nm_sr": deviation[0],
            "reported_relative_standard_deviation": deviation[0]
            / radiance[0],
        }
    if kind == "shape":
        wavelengths, radiances = _parse_radiance(
            directory / "mc.rad.spc",
            spec["radiance_solver"]["expected_spectral_row_count"],
        )
        normalization_wavelength = float(
            spec["radiance_solver"]["normalization_wavelength_nm"]
        )
        normalization_index = round(
            (normalization_wavelength - 380.0) / 0.05
        )
        normalizer = radiances[normalization_index]
        if normalizer <= 0 or not math.isclose(
            wavelengths[normalization_index],
            normalization_wavelength,
            abs_tol=1e-6,
        ):
            raise ValidationError("shape normalizer differs")
        result: dict[str, Any] = {
            "normalization_reference_radiance_mw_m2_nm_sr": normalizer,
        }
        for response, table in cie.items():
            integral = _response_integral(
                wavelengths,
                radiances,
                table,
            )
            if integral <= 0:
                raise ValidationError("response integral is nonpositive")
            result[f"{response}_shape_nm"] = integral / normalizer
        return result
    wavelengths: list[float] = []
    horizontal: list[float] = []
    for line in (directory / "stdout.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 2:
            raise ValidationError("direct output row shape differs")
        wavelengths.append(float(fields[0]))
        horizontal.append(float(fields[1]))
    if len(wavelengths) != 8001:
        raise ValidationError("direct row count differs")
    for index, wavelength in enumerate(wavelengths):
        if not math.isclose(
            wavelength,
            380.0 + index * 0.05,
            abs_tol=1.1e-4,
        ):
            raise ValidationError("direct wavelength differs")
    sine = math.sin(math.radians(run["target_true_altitude_deg"]))
    direct = [value / sine for value in horizontal]
    if any(
        not math.isfinite(value)
        or value < 0.0
        or value > 1.0000001
        for value in direct
    ):
        raise ValidationError("direct transmission is out of range")
    floor = float(spec["direct_solver"]["opaque_transmission_floor"])
    binned = [
        math.fsum(direct[index * 20 : (index + 1) * 20]) / 20.0
        for index in range(400)
    ]
    return {
        "spectral_bin_start_nm": 380.0,
        "spectral_bin_width_nm": 1.0,
        "spectral_bin_count": 400,
        "direct_transmission_1nm": binned,
        "extinction_magnitude_1nm": [
            -2.5 * math.log10(max(value, floor)) for value in binned
        ],
    }


def _point_id(point: tuple[float, float, float]) -> str:
    return (
        f"s{abs(point[0]):04.1f}_h{point[1]:05.2f}_a{point[2]:05.1f}"
        .replace(".", "p")
    )


def _points(
    spec: dict[str, Any],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[float, float, float]],
    list[tuple[float, float, float]],
]:
    grid = spec["radiance_grid"]
    training = [
        tuple(float(value) for value in point)
        for point in itertools.product(
            grid["solar_center_altitude_deg"]["training_nodes"],
            grid["target_true_altitude_deg"]["training_nodes"],
            grid["relative_solar_azimuth_deg"]["training_nodes"],
        )
    ]
    holdouts = [
        tuple(float(value) for value in point)
        for point in itertools.product(
            grid["solar_center_altitude_deg"]["reserved_holdouts"],
            grid["target_true_altitude_deg"]["reserved_holdouts"],
            grid["relative_solar_azimuth_deg"]["reserved_holdouts"],
        )
    ]
    response_holdouts = [
        tuple(float(value) for value in point)
        for point in grid["response_holdouts"]
    ]
    return training, holdouts, response_holdouts


def _threshold(solar: float, spec: dict[str, Any]) -> float:
    matches = [
        float(row["maximum_relative_standard_error"])
        for row in spec["adaptive_monte_carlo"][
            "anchor_relative_standard_error_by_solar_altitude"
        ]
        if float(row["minimum_solar_altitude_deg"])
        <= solar
        <= float(row["maximum_solar_altitude_deg"])
    ]
    if len(matches) != 1:
        raise ValidationError("anchor uncertainty band is ambiguous")
    return matches[0]


def _shape_photon_count(
    solar_center_altitude_deg: float,
    spec: dict[str, Any],
) -> int:
    matches = [
        int(row["photons_per_seed"])
        for row in spec["adaptive_monte_carlo"][
            "spectral_shape_photons_per_seed_by_solar_center_altitude"
        ]
        if float(row["solar_center_altitude_deg"])
        == float(solar_center_altitude_deg)
    ]
    if len(matches) != 1:
        raise ValidationError(
            "spectral shape photon schedule is ambiguous"
        )
    return matches[0]


def _verify_monte_carlo_run_sequence(
    payloads: list[dict[str, Any]],
    point: tuple[float, float, float],
    partition: str,
    kind: str,
    spec: dict[str, Any],
) -> None:
    contract = spec["adaptive_monte_carlo"]
    if kind == "anchor":
        seed_key = (
            "training_random_seeds"
            if partition == "training"
            else "holdout_random_seeds"
        )
        photon_count = contract["anchor_photons_per_seed"]
    elif kind == "shape":
        seed_key = (
            "spectral_shape_training_random_seeds"
            if partition == "training"
            else "spectral_shape_holdout_random_seeds"
        )
        photon_count = _shape_photon_count(point[0], spec)
    else:
        raise ValidationError(f"unknown Monte Carlo run kind: {kind}")
    expected = [
        {
            "run_id": (
                f"{partition}__{_point_id(point)}__{kind}__r"
                f"{index + 1:02d}"
            ),
            "kind": kind,
            "partition": partition,
            "point_id": _point_id(point),
            "solar_center_altitude_deg": point[0],
            "target_true_altitude_deg": point[1],
            "relative_solar_azimuth_deg": point[2],
            "photon_count": photon_count,
            "random_seed": seed,
        }
        for index, seed in enumerate(contract[seed_key][: len(payloads)])
    ]
    if [payload["run"] for payload in payloads] != expected:
        raise ValidationError(
            f"{kind} seed or photon sequence differs"
        )


def _relative_error(
    values: list[float],
    deviations: list[float] | None = None,
) -> dict[str, float]:
    mean = statistics.fmean(values)
    between = statistics.stdev(values) / math.sqrt(len(values)) / mean
    reported = 0.0
    if deviations is not None:
        reported = (
            math.sqrt(math.fsum(value * value for value in deviations))
            / len(deviations)
            / mean
        )
    return {
        "mean": mean,
        "between_seed_relative_standard_error": between,
        "reported_aggregate_relative_standard_error": reported,
        "governing_relative_standard_error": max(between, reported),
    }


def _aggregate_anchor_group(
    payloads: list[dict[str, Any]],
    point: tuple[float, float, float],
    partition: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    minimum = spec["adaptive_monte_carlo"]["anchor_minimum_seed_count"]
    maximum = spec["adaptive_monte_carlo"]["anchor_maximum_seed_count"]
    threshold = _threshold(point[0], spec)
    if not minimum <= len(payloads) <= maximum:
        raise ValidationError("anchor seed count differs")
    _verify_monte_carlo_run_sequence(
        payloads,
        point,
        partition,
        "anchor",
        spec,
    )
    aggregate = _relative_error(
        [
            row["result"]["reference_radiance_mw_m2_nm_sr"]
            for row in payloads
        ],
        [
            row["result"]["reported_standard_deviation_mw_m2_nm_sr"]
            for row in payloads
        ],
    )
    if aggregate["governing_relative_standard_error"] > threshold:
        raise ValidationError("anchor aggregate did not converge")
    if len(payloads) > minimum:
        previous = _relative_error(
            [
                row["result"]["reference_radiance_mw_m2_nm_sr"]
                for row in payloads[:-1]
            ],
            [
                row["result"][
                    "reported_standard_deviation_mw_m2_nm_sr"
                ]
                for row in payloads[:-1]
            ],
        )
        if previous["governing_relative_standard_error"] <= threshold:
            raise ValidationError("anchor aggregate ran past convergence")
    return {
        "point_id": _point_id(point),
        "partition": partition,
        "solar_center_altitude_deg": point[0],
        "target_true_altitude_deg": point[1],
        "relative_solar_azimuth_deg": point[2],
        "seed_count": len(payloads),
        "photon_count": len(payloads)
        * spec["adaptive_monte_carlo"]["anchor_photons_per_seed"],
        "maximum_relative_standard_error": threshold,
        "mean_reference_radiance_mw_m2_nm_sr": aggregate["mean"],
        "between_seed_relative_standard_error": aggregate[
            "between_seed_relative_standard_error"
        ],
        "reported_aggregate_relative_standard_error": aggregate[
            "reported_aggregate_relative_standard_error"
        ],
        "governing_relative_standard_error": aggregate[
            "governing_relative_standard_error"
        ],
    }


def _aggregate_shape_group(
    payloads: list[dict[str, Any]],
    point: tuple[float, float, float],
    partition: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    contract = spec["adaptive_monte_carlo"]
    minimum = contract["spectral_shape_minimum_seed_count"]
    maximum = contract["spectral_shape_maximum_seed_count"]
    threshold = contract[
        "maximum_response_shape_relative_standard_error"
    ]
    if not minimum <= len(payloads) <= maximum:
        raise ValidationError("shape seed count differs")
    _verify_monte_carlo_run_sequence(
        payloads,
        point,
        partition,
        "shape",
        spec,
    )
    aggregates = {
        response: _relative_error(
            [row["result"][f"{response}_shape_nm"] for row in payloads]
        )
        for response in ("photopic", "scotopic")
    }
    if max(
        item["governing_relative_standard_error"]
        for item in aggregates.values()
    ) > threshold:
        raise ValidationError("shape aggregate did not converge")
    if len(payloads) > minimum:
        previous = {
            response: _relative_error(
                [
                    row["result"][f"{response}_shape_nm"]
                    for row in payloads[:-1]
                ]
            )
            for response in ("photopic", "scotopic")
        }
        if max(
            item["governing_relative_standard_error"]
            for item in previous.values()
        ) <= threshold:
            raise ValidationError("shape aggregate ran past convergence")
    return {
        "point_id": _point_id(point),
        "partition": partition,
        "solar_center_altitude_deg": point[0],
        "target_true_altitude_deg": point[1],
        "relative_solar_azimuth_deg": point[2],
        "seed_count": len(payloads),
        "photon_count": sum(
            row["run"]["photon_count"] for row in payloads
        ),
        "maximum_relative_standard_error": threshold,
        "photopic_shape_nm": aggregates["photopic"]["mean"],
        "photopic_relative_standard_error": aggregates["photopic"][
            "governing_relative_standard_error"
        ],
        "scotopic_shape_nm": aggregates["scotopic"]["mean"],
        "scotopic_relative_standard_error": aggregates["scotopic"][
            "governing_relative_standard_error"
        ],
    }


def _response(
    anchor: dict[str, Any],
    shape: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = {
        key: anchor[key]
        for key in (
            "point_id",
            "partition",
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
        )
    }
    for response, source in (
        ("photopic", "CIE_photopic"),
        ("scotopic", "CIE_scotopic"),
    ):
        result[f"{response}_luminance_cd_m2"] = (
            anchor["mean_reference_radiance_mw_m2_nm_sr"]
            * shape[f"{response}_shape_nm"]
            * spec["sources"][source]["luminous_efficacy_lm_per_w"]
            / 1000.0
        )
        result[f"{response}_relative_standard_error"] = math.hypot(
            anchor["governing_relative_standard_error"],
            shape[f"{response}_relative_standard_error"],
        )
    return result


def _bracket(nodes: list[float], value: float) -> tuple[float, float]:
    if value in nodes:
        return value, value
    for left, right in zip(nodes, nodes[1:]):
        if left < value < right:
            return left, right
    raise ValidationError("interpolation point lies outside nodes")


def _trilinear(
    table: dict[tuple[float, float, float], float],
    axes: tuple[list[float], list[float], list[float]],
    point: tuple[float, float, float],
) -> float:
    brackets = [
        _bracket(nodes, value) for nodes, value in zip(axes, point)
    ]
    result = 0.0
    choices = [
        [left] if left == right else [left, right]
        for left, right in brackets
    ]
    for corner in itertools.product(*choices):
        weight = 1.0
        for coordinate, value, (left, right) in zip(
            corner,
            point,
            brackets,
        ):
            if left != right:
                fraction = (value - left) / (right - left)
                weight *= fraction if coordinate == right else 1.0 - fraction
        result += weight * math.log10(table[tuple(corner)])
    return 10.0**result


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[math.floor((len(ordered) - 1) * fraction)]


def _errors(
    rows: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    values = [row[field] for row in rows]
    return {
        "sample_count": len(values),
        "mean_error_mag": statistics.fmean(values),
        "p95_error_mag": _quantile(values, 0.95),
        "maximum_error_mag": max(values),
        "worst_case": max(rows, key=lambda row: row[field]),
    }


def _direct_coordinate(value: float) -> float:
    return math.log10(value + 0.25)


def _direct_interpolate(
    table: dict[float, list[float]],
    altitude: float,
) -> list[float]:
    left, right = _bracket(sorted(table), altitude)
    if left == right:
        return table[left]
    fraction = (
        _direct_coordinate(altitude) - _direct_coordinate(left)
    ) / (_direct_coordinate(right) - _direct_coordinate(left))
    return [
        low * (1.0 - fraction) + high * fraction
        for low, high in zip(table[left], table[right])
    ]


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _independent_summary(
    spec: dict[str, Any],
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    direct_payloads: list[dict[str, Any]] = []
    for payload in payloads:
        run = payload["run"]
        if run["kind"] == "direct":
            direct_payloads.append(payload)
        else:
            key = (run["kind"], run["partition"], run["point_id"])
            groups.setdefault(key, []).append(payload)
    training, holdouts, response_holdouts = _points(spec)
    anchors: list[dict[str, Any]] = []
    shapes: list[dict[str, Any]] = []
    for partition, points in (
        ("training", training),
        ("holdout", holdouts),
    ):
        for point in points:
            key = ("anchor", partition, _point_id(point))
            rows = sorted(
                groups.pop(key, []),
                key=lambda row: row["run"]["run_id"],
            )
            anchors.append(
                _aggregate_anchor_group(
                    rows,
                    point,
                    partition,
                    spec,
                )
            )
    for partition, points in (
        ("training", training),
        ("holdout", response_holdouts),
    ):
        for point in points:
            key = ("shape", partition, _point_id(point))
            rows = sorted(
                groups.pop(key, []),
                key=lambda row: row["run"]["run_id"],
            )
            shapes.append(
                _aggregate_shape_group(
                    rows,
                    point,
                    partition,
                    spec,
                )
            )
    if groups:
        raise ValidationError("unexpected Monte Carlo run groups remain")
    expected_direct = {
        ("training", float(value))
        for value in spec["direct_solver"][
            "training_target_true_altitude_deg"
        ]
    } | {
        ("holdout", float(value))
        for value in spec["direct_solver"][
            "reserved_target_true_altitude_holdouts_deg"
        ]
    }
    received_direct = {
        (
            payload["run"]["partition"],
            float(payload["run"]["target_true_altitude_deg"]),
        )
        for payload in direct_payloads
    }
    if (
        received_direct != expected_direct
        or len(direct_payloads) != len(expected_direct)
    ):
        raise ValidationError("direct run inventory differs")
    anchor_by_key = {
        (row["partition"], row["point_id"]): row for row in anchors
    }
    response_products = [
        _response(
            anchor_by_key[(row["partition"], row["point_id"])],
            row,
            spec,
        )
        for row in shapes
    ]
    grid = spec["radiance_grid"]
    axes = (
        [
            float(value)
            for value in grid["solar_center_altitude_deg"][
                "training_nodes"
            ]
        ],
        [
            float(value)
            for value in grid["target_true_altitude_deg"]["training_nodes"]
        ],
        [
            float(value)
            for value in grid["relative_solar_azimuth_deg"][
                "training_nodes"
            ]
        ],
    )
    anchor_table = {
        (
            row["solar_center_altitude_deg"],
            row["target_true_altitude_deg"],
            row["relative_solar_azimuth_deg"],
        ): row["mean_reference_radiance_mw_m2_nm_sr"]
        for row in anchors
        if row["partition"] == "training"
    }
    mono_errors = []
    for row in anchors:
        if row["partition"] == "training":
            continue
        point = (
            row["solar_center_altitude_deg"],
            row["target_true_altitude_deg"],
            row["relative_solar_azimuth_deg"],
        )
        predicted = _trilinear(anchor_table, axes, point)
        truth = row["mean_reference_radiance_mw_m2_nm_sr"]
        mono_errors.append(
            {
                "point_id": row["point_id"],
                "predicted_reference_radiance_mw_m2_nm_sr": predicted,
                "truth_reference_radiance_mw_m2_nm_sr": truth,
                "truth_relative_standard_error": row[
                    "governing_relative_standard_error"
                ],
                "error_mag": 2.5 * abs(math.log10(predicted / truth)),
            }
        )
    response_error_rows: dict[str, list[dict[str, Any]]] = {
        "photopic": [],
        "scotopic": [],
    }
    for response in response_error_rows:
        field = f"{response}_luminance_cd_m2"
        table = {
            (
                row["solar_center_altitude_deg"],
                row["target_true_altitude_deg"],
                row["relative_solar_azimuth_deg"],
            ): row[field]
            for row in response_products
            if row["partition"] == "training"
        }
        for row in response_products:
            if row["partition"] == "training":
                continue
            point = (
                row["solar_center_altitude_deg"],
                row["target_true_altitude_deg"],
                row["relative_solar_azimuth_deg"],
            )
            predicted = _trilinear(table, axes, point)
            truth = row[field]
            response_error_rows[response].append(
                {
                    "point_id": row["point_id"],
                    "predicted_luminance_cd_m2": predicted,
                    "truth_luminance_cd_m2": truth,
                    "truth_relative_standard_error": row[
                        f"{response}_relative_standard_error"
                    ],
                    "error_mag": 2.5 * abs(math.log10(predicted / truth)),
                }
            )
    direct_table = {
        float(row["run"]["target_true_altitude_deg"]): row["result"][
            "extinction_magnitude_1nm"
        ]
        for row in direct_payloads
        if row["run"]["partition"] == "training"
    }
    direct_errors = []
    direct_holdouts = []
    for row in direct_payloads:
        if row["run"]["partition"] == "training":
            continue
        altitude = float(row["run"]["target_true_altitude_deg"])
        truth = row["result"]["extinction_magnitude_1nm"]
        predicted = _direct_interpolate(direct_table, altitude)
        direct_holdouts.append(
            {
                "target_true_altitude_deg": altitude,
                "extinction_magnitude_1nm": truth,
            }
        )
        for index, (guess, actual) in enumerate(zip(predicted, truth)):
            direct_errors.append(
                {
                    "target_true_altitude_deg": altitude,
                    "spectral_bin_start_nm": 380.0 + index,
                    "predicted_extinction_magnitude": guess,
                    "truth_extinction_magnitude": actual,
                    "error_mag": abs(guess - actual),
                }
            )
    training_responses = sorted(
        [
            row
            for row in response_products
            if row["partition"] == "training"
        ],
        key=lambda row: (
            row["solar_center_altitude_deg"],
            row["target_true_altitude_deg"],
            row["relative_solar_azimuth_deg"],
        ),
    )
    storage_values = [
        (f"radiance.{response}", row[f"{response}_luminance_cd_m2"])
        for row in training_responses
        for response in ("photopic", "scotopic")
    ] + [
        ("direct.extinction", value)
        for altitude in sorted(direct_table)
        for value in direct_table[altitude]
    ]
    step = float(spec["acceptance"]["quantized_log10_step"])
    float32_errors = []
    quantized_errors = []
    for label, value in storage_values:
        staged = _float32(value)
        if label.startswith("radiance."):
            float32_errors.append(2.5 * abs(math.log10(staged / value)))
            quantized_errors.append(
                2.5
                * abs(
                    round(math.log10(value) / step) * step
                    - math.log10(value)
                )
            )
        else:
            float32_errors.append(abs(staged - value))
            quantized_errors.append(
                abs(
                    round(value / (2.5 * step)) * (2.5 * step)
                    - value
                )
            )
    summaries = {
        "monochromatic_reference": _errors(mono_errors, "error_mag"),
        "photopic_response": _errors(
            response_error_rows["photopic"],
            "error_mag",
        ),
        "scotopic_response": _errors(
            response_error_rows["scotopic"],
            "error_mag",
        ),
        "direct_extinction_1nm": _errors(
            direct_errors,
            "error_mag",
        ),
    }
    acceptance = spec["acceptance"]
    monochromatic_diagnostic_passed = not (
        summaries["monochromatic_reference"]["maximum_error_mag"]
        > acceptance["monochromatic_holdout_maximum_error_mag"]
        or summaries["monochromatic_reference"]["p95_error_mag"]
        > acceptance["monochromatic_holdout_p95_error_mag"]
    )
    if (
        any(
            summaries[name]["maximum_error_mag"]
            > acceptance["response_holdout_maximum_error_mag"]
            or summaries[name]["p95_error_mag"]
            > acceptance["response_holdout_p95_error_mag"]
            for name in ("photopic_response", "scotopic_response")
        )
        or summaries["direct_extinction_1nm"]["maximum_error_mag"]
        > acceptance["direct_holdout_maximum_error_mag"]
        or summaries["direct_extinction_1nm"]["p95_error_mag"]
        > acceptance["direct_holdout_p95_error_mag"]
        or max(float32_errors)
        > acceptance["float32_storage_maximum_error_mag"]
        or max(quantized_errors)
        > acceptance["quantized_storage_maximum_error_mag"]
    ):
        raise ValidationError("independent acceptance failed")
    return {
        "schema": "moira.visibility-radiance-response-summary/v1",
        "spec_id": spec["spec_id"],
        "effective_domain": spec["effective_domain"],
        "deep_twilight_law": spec["deep_twilight_law"],
        "radiance_axes": {
            "solar_center_altitude_deg": axes[0],
            "target_true_altitude_deg": axes[1],
            "relative_solar_azimuth_deg": axes[2],
        },
        "response_training_table": training_responses,
        "direct_training_table": [
            {
                "target_true_altitude_deg": altitude,
                "extinction_magnitude_1nm": direct_table[altitude],
            }
            for altitude in sorted(direct_table)
        ],
        "direct_holdout_table": direct_holdouts,
        "error_summaries": summaries,
        "diagnostic_contract": {
            "monochromatic_reference": {
                "admission_gate": False,
                "surface_shipped_in_data_pack": False,
                "surface_used_by_runtime_interpolation": False,
                "role": acceptance["monochromatic_reference_role"],
                "comparison_threshold_passed": (
                    monochromatic_diagnostic_passed
                ),
                "maximum_comparison_error_mag": acceptance[
                    "monochromatic_holdout_maximum_error_mag"
                ],
                "p95_comparison_error_mag": acceptance[
                    "monochromatic_holdout_p95_error_mag"
                ],
            }
        },
        "monte_carlo": {
            "anchor_aggregate_count": len(anchors),
            "shape_aggregate_count": len(shapes),
            "maximum_anchor_relative_standard_error": max(
                row["governing_relative_standard_error"] for row in anchors
            ),
            "maximum_photopic_response_relative_standard_error": max(
                row["photopic_relative_standard_error"]
                for row in response_products
            ),
            "maximum_scotopic_response_relative_standard_error": max(
                row["scotopic_relative_standard_error"]
                for row in response_products
            ),
            "anchor_seed_count_distribution": {
                str(count): sum(
                    row["seed_count"] == count for row in anchors
                )
                for count in sorted({row["seed_count"] for row in anchors})
            },
            "shape_seed_count_distribution": {
                str(count): sum(
                    row["seed_count"] == count for row in shapes
                )
                for count in sorted({row["seed_count"] for row in shapes})
            },
        },
        "storage_analysis": {
            "selected_representation": "little_endian_ieee754_binary32",
            "float64_reference_maximum_error_mag": 0.0,
            "float32_value_count": len(float32_errors),
            "float32_maximum_error_mag": max(float32_errors),
            "quantized_log10_step": step,
            "quantized_maximum_error_mag": max(quantized_errors),
            "storage_error_is_separate_from_solver_and_interpolation_error": True,
        },
        "downstream_error_contract": {
            "direct_extinction_error_unit": "magnitude",
            "background_interpolation_error_unit": "surface_brightness_magnitude",
            "per_cell_solver_uncertainty_required": True,
            "limiting_magnitude_propagation_owner": "phase2_single_epoch_truth",
            "event_time_propagation_owner": "phase3_event_solver",
            "phase1_does_not_fabricate_downstream_derivatives": True,
        },
        "accepted": True,
    }


def _verify_tooling(
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
        raise ValidationError("tooling receipt is missing")
    for role, path in expected.items():
        receipt = tooling.get(role)
        if not isinstance(receipt, dict):
            raise ValidationError(f"{role} receipt is missing")
        if (
            receipt.get("path") != path.relative_to(REPO_ROOT).as_posix()
            or receipt.get("bytes") != path.stat().st_size
            or receipt.get("sha256") != _sha256_file(path)
        ):
            raise ValidationError(f"{role} receipt is stale")


def _verify_cie(
    cie_root: Path,
    spec: dict[str, Any],
) -> dict[str, dict[int, float]]:
    result: dict[str, dict[int, float]] = {}
    for response, name in (
        ("photopic", "CIE_photopic"),
        ("scotopic", "CIE_scotopic"),
    ):
        declaration = spec["sources"][name]
        for role in ("csv", "metadata"):
            path = cie_root / declaration[f"{role}_filename"]
            if (
                not path.is_file()
                or path.stat().st_size != declaration[f"{role}_bytes"]
                or _sha256_file(path) != declaration[f"{role}_sha256"]
            ):
                raise ValidationError(f"{response} CIE {role} differs")
        result[response] = _load_cie(
            cie_root / declaration["csv_filename"]
        )
    return result


def validate_artifact(
    artifact: Path,
    *,
    cie_root: Path,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    artifact = artifact.resolve()
    spec_path = spec_path.resolve()
    cie_root = cie_root.resolve()
    if not artifact.is_dir() or artifact.is_symlink():
        raise ValidationError("artifact root is missing or a symlink")
    spec = _load_spec(spec_path)
    manifest_path = artifact / MANIFEST_NAME
    manifest = _load_json(manifest_path, "artifact manifest")
    if (
        manifest_path.read_bytes() != _canonical_json_bytes(manifest)
        or manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("status")
        != "phase1_complete_reference_artifact_not_runtime_data_pack"
        or manifest.get("spec_id") != spec["spec_id"]
        or manifest.get("runtime_boundary") != spec["runtime_boundary"]
        or manifest.get("effective_domain") != spec["effective_domain"]
        or manifest.get("deep_twilight_law")
        != spec["deep_twilight_law"]
    ):
        raise ValidationError("manifest contract differs")
    _verify_tooling(manifest, spec_path)
    cie = _verify_cie(cie_root, spec)
    source = manifest.get("source")
    if (
        not isinstance(source, dict)
        or source.get("libRadtran_archive", {}).get("sha256")
        != spec["sources"]["libRadtran"]["archive_sha256"]
        or source.get("REPTRAN_archive", {}).get("sha256")
        != spec["sources"]["REPTRAN_module"]["archive_sha256"]
        or source.get("uvspec", {}).get("sha256")
        != spec["sources"]["libRadtran"]["uvspec_sha256"]
        or source.get("spectral_importance_reference_sources")
        != spec["radiance_solver"][
            "spectral_importance_reference_source_receipts"
        ]
    ):
        raise ValidationError("source receipt differs")
    runs = manifest.get("runs")
    if (
        not isinstance(runs, list)
        or manifest.get("run_count") != len(runs)
    ):
        raise ValidationError("manifest run count differs")
    payloads: list[dict[str, Any]] = []
    owned: set[str] = set()
    received_ids: set[str] = set()
    for index, receipt in enumerate(runs):
        if not isinstance(receipt, dict):
            raise ValidationError("run receipt must be an object")
        run = receipt.get("run")
        run_id = receipt.get("run_id")
        if (
            not isinstance(run, dict)
            or not isinstance(run_id, str)
            or run.get("run_id") != run_id
            or run_id in received_ids
        ):
            raise ValidationError("run identity differs")
        received_ids.add(run_id)
        result_receipt = receipt.get("result")
        if not isinstance(result_receipt, dict):
            raise ValidationError("run result receipt is missing")
        expected_path = f"runs/{run_id}/result.json"
        if result_receipt.get("path") != expected_path:
            raise ValidationError("run result path differs")
        result_path = _verify_file(
            artifact,
            result_receipt,
            f"run {index} result",
        )
        payload = _load_json(result_path, f"run {run_id}")
        if (
            result_path.read_bytes() != _canonical_json_bytes(payload)
            or payload.get("schema") != RUN_SCHEMA
            or payload.get("run") != run
            or not isinstance(payload.get("files"), list)
        ):
            raise ValidationError("run payload differs")
        directory = result_path.parent
        _assert_input_equivalent(
            (directory / "input.inp").read_bytes(),
            _expected_input(run, spec),
            run_id,
        )
        expected_files = (
            {
                "input.inp",
                "stdout.txt",
                "stderr.txt",
                "syntax.stdout.txt",
                "syntax.stderr.txt",
                "mc.rad.spc",
                "mc.rad.std.spc",
                "randomseed",
            }
            if run["kind"] in {"anchor", "shape"}
            else {
                "input.inp",
                "stdout.txt",
                "stderr.txt",
                "syntax.stdout.txt",
                "syntax.stderr.txt",
            }
        )
        file_names: set[str] = set()
        for file_receipt in payload["files"]:
            if not isinstance(file_receipt, dict):
                raise ValidationError("run file receipt differs")
            name = file_receipt.get("path")
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or name in file_names
                or name not in expected_files
            ):
                raise ValidationError("run file inventory differs")
            file_names.add(name)
            _verify_file(directory, file_receipt, f"{run_id}/{name}")
            owned.add(f"runs/{run_id}/{name}")
        if file_names != expected_files:
            raise ValidationError("run file inventory is incomplete")
        independent = _independent_result(directory, run, spec, cie)
        _assert_numeric_equal(
            payload["result"],
            independent,
            f"run {run_id} result",
        )
        payloads.append(payload)
        owned.add(expected_path)
    independent_summary = _independent_summary(spec, payloads)
    summary_receipt = manifest.get("summary")
    if not isinstance(summary_receipt, dict):
        raise ValidationError("summary receipt is missing")
    summary_path = _verify_file(artifact, summary_receipt, "summary")
    committed_summary = _load_json(summary_path, "summary")
    if summary_path.read_bytes() != _canonical_json_bytes(committed_summary):
        raise ValidationError("summary serialization is not canonical")
    _assert_numeric_equal(
        committed_summary,
        independent_summary,
        "independent summary",
    )
    owned.add(SUMMARY_NAME)
    actual = {
        path.relative_to(artifact).as_posix()
        for path in artifact.rglob("*")
        if path.is_file()
    }
    expected = {*owned, MANIFEST_NAME}
    if actual != expected:
        raise ValidationError(
            "artifact inventory differs: "
            f"missing={sorted(expected - actual)[:5]} "
            f"unexpected={sorted(actual - expected)[:5]}"
        )
    if any(path.is_symlink() for path in artifact.rglob("*")):
        raise ValidationError("artifact contains a symlink")
    return {
        "artifact": str(artifact),
        "manifest_sha256": _sha256_file(manifest_path),
        "generation_fingerprint": manifest["generation_fingerprint"],
        "run_count": len(payloads),
        "error_summaries": independent_summary["error_summaries"],
        "storage_analysis": independent_summary["storage_analysis"],
        "validated": True,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Phase 1 radiance/response artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--cie-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = validate_artifact(
            args.artifact,
            cie_root=args.cie_root,
            spec_path=args.spec,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
