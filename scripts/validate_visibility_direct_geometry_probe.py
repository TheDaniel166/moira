#!/usr/bin/env python3
"""Independently validate a Phase 1 direct-geometry probe artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_direct_geometry_probe_spec.json"
)
SPEC_SCHEMA = "moira.visibility-direct-geometry-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-direct-geometry-probe-artifact/v1"
CASE_SCHEMA = "moira.visibility-direct-geometry-probe-case/v1"
ARTIFACT_STATUS = "phase1_direct_geometry_evidence_not_runtime_data_pack"
CASE_FILES = frozenset(
    {
        "atmosphere.dat",
        "input.inp",
        "molecular_tau.dat",
        "randomseed",
        "result.json",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    }
)

_GK15_ABSCISSAE = (
    0.9914553711208126,
    0.9491079123427585,
    0.8648644233597691,
    0.7415311855993945,
    0.5860872354676911,
    0.4058451513773972,
    0.2077849550078985,
    0.0,
)
_GK15_WEIGHTS = (
    0.02293532201052922,
    0.06309209262997855,
    0.1047900103222502,
    0.1406532597155259,
    0.1690047266392679,
    0.1903505780647854,
    0.2044329400752989,
    0.2094821410847278,
)
_G7_WEIGHTS = (
    0.1294849661688697,
    0.2797053914892767,
    0.3818300505051189,
    0.4179591836734694,
)


class ValidationError(ValueError):
    """Raised when a direct-geometry artifact violates its receipt."""


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{label} must be a JSON object")
    return payload


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} path must be a nonempty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValidationError(f"{label} path is not safe and canonical")
    return value


def _validate_file_receipt(
    root: Path,
    receipt: Any,
    *,
    label: str,
) -> str:
    if not isinstance(receipt, dict):
        raise ValidationError(f"{label} receipt must be an object")
    relative = _safe_relative_path(receipt.get("path"), label)
    byte_count = receipt.get("bytes")
    expected_sha = receipt.get("sha256")
    if (
        not isinstance(byte_count, int)
        or byte_count < 0
        or not isinstance(expected_sha, str)
        or len(expected_sha) != 64
    ):
        raise ValidationError(f"{label} receipt has an invalid size or SHA-256")
    path = root / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != byte_count
        or _sha256_file(path) != expected_sha
    ):
        raise ValidationError(f"{label} receipt mismatch: {path}")
    return relative


def _levels_from_segments(segments: Any) -> list[float]:
    if not isinstance(segments, list) or not segments:
        raise ValidationError("refined vertical-grid segments are missing")
    levels: set[Decimal] = set()
    previous_stop: Decimal | None = None
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValidationError("vertical-grid segment must be an object")
        try:
            start = Decimal(str(segment["start"]))
            stop = Decimal(str(segment["stop"]))
            step = Decimal(str(segment["step"]))
        except (KeyError, ValueError) as exc:
            raise ValidationError("vertical-grid segment is malformed") from exc
        if (
            not start.is_finite()
            or not stop.is_finite()
            or not step.is_finite()
            or start < 0
            or stop > 120
            or start >= stop
            or step <= 0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise ValidationError("vertical-grid segments are invalid")
        count_decimal = (stop - start) / step
        count = int(count_decimal)
        if Decimal(count) != count_decimal:
            raise ValidationError("vertical-grid segment does not divide exactly")
        for offset in range(count + 1):
            levels.add(start + step * offset)
        previous_stop = stop
    return [float(value) for value in sorted(levels, reverse=True)]


def _vertical_grids(spec: dict[str, Any]) -> dict[str, list[float]]:
    grids = spec["vertical_grids"]
    source = grids["source_grid_control"]
    refined = grids["refined_candidate"]
    return {
        source["grid_id"]: [
            float(value) for value in source["levels_km_descending"]
        ],
        refined["grid_id"]: _levels_from_segments(refined["segments_km"]),
    }


def _load_spec(path: Path) -> dict[str, Any]:
    spec = _load_json(path, "direct-geometry specification")
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("status") != "research_probe_not_runtime_data_pack"
        or spec.get("runtime_boundary")
        != {
            "network_allowed": False,
            "automatic_download_allowed": False,
            "engine_dependency_allowed": False,
            "engine_runtime_invocation_allowed": False,
            "generated_numerical_products_only": True,
        }
    ):
        raise ValidationError("unsupported direct-geometry specification")
    boundary = spec.get("scientific_boundary")
    if (
        not isinstance(boundary, dict)
        or boundary.get("model_id")
        != "libradtran_2_0_6_direct_spherical_geometry_probe_v1"
        or boundary.get("earth_radius_km") != 6370.0
        or boundary.get("top_altitude_km") != 120.0
        or boundary.get("refraction")
        != "disabled_true_geometric_line_of_sight"
        or boundary.get("production_solver") != "disort"
        or boundary.get("production_geometry") != "pseudospherical"
        or boundary.get("production_number_of_streams") != 16
        or boundary.get("random_seed_option") != 49979687
        or boundary.get("random_seed_role")
        != "fixed_nonoperative_uvspec_output_control"
        or boundary.get("minimum_admitted_target_true_altitude_deg") != 0.25
        or boundary.get("exact_horizon_status")
        != "diagnostic_only_not_admitted"
        or boundary.get("uavgdir_production_status")
        != (
            "forbidden_because_delta_m_scaled_aerosol_direct_mean_intensity_"
            "is_not_unscaled_direct_transmission"
        )
    ):
        raise ValidationError("direct-geometry scientific boundary changed")
    controlled = spec.get("controlled_exponential_atmospheres")
    if (
        not isinstance(controlled, dict)
        or controlled.get("wavelength_nm") != 550.0
        or controlled.get("vertical_optical_depth") != 0.1
        or controlled.get("scale_height_km")
        != [0.25, 0.5, 1.0, 1.5, 8.0, 20.0]
        or controlled.get("density_law")
        != "exp_minus_altitude_over_scale_height"
        or controlled.get("libRadtran_transport")
        != "mol_tau_file_abs_with_all_scattering_disabled"
        or controlled.get("target_true_altitude_deg")
        != {
            "diagnostic_only": [0.0, 0.05, 0.1],
            "admitted_domain": [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0],
            "vertical_control": [90.0],
        }
    ):
        raise ValidationError("controlled atmosphere declaration changed")
    grids = _vertical_grids(spec)
    if (
        set(grids) != {
            "afglus_source_levels_v1",
            "near_horizon_piecewise_refined_v1",
        }
        or len(grids["afglus_source_levels_v1"]) != 50
        or len(grids["near_horizon_piecewise_refined_v1"]) != 290
        or any(
            a <= b
            for levels in grids.values()
            for a, b in zip(levels, levels[1:])
        )
        or any(
            levels[0] != 120.0 or levels[-1] != 0.0
            for levels in grids.values()
        )
    ):
        raise ValidationError("vertical-grid declaration changed")
    acceptance = spec.get("acceptance")
    if acceptance != {
        "admitted_libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs_tolerance": 0.00002,
        "admitted_positive_altitude_extraction_relative_tolerance": 0.00005,
        "refined_midpoint_vs_continuous_admitted_relative_slant_optical_depth_tolerance": 0.001,
        "vertical_control_slant_optical_depth_abs_tolerance": 0.00002,
        "diagnostic_subdomain_has_no_admission_tolerance": True,
    }:
        raise ValidationError("direct-geometry acceptance policy changed")
    oracle = spec.get("independent_oracle")
    if (
        not isinstance(oracle, dict)
        or oracle.get("validator_method")
        != (
            "adaptive_gauss_kronrod_15_over_squared_altitude_transform_of_"
            "straight_spherical_ray"
        )
        or oracle.get("libRadtran_surface_reconstruction")
        != (
            "bottom_layer_midpoint_chapman_factor_applied_to_full_surface_"
            "vertical_optical_depth"
        )
        or oracle.get("builder_initial_equal_root_altitude_panels") != 64
        or oracle.get("maximum_recursion_depth") != 30
        or oracle.get("stored_oracle_cross_method_relative_tolerance") != 2e-9
    ):
        raise ValidationError("independent-oracle policy changed")
    source = spec.get("source")
    if (
        not isinstance(source, dict)
        or source.get("version") != "2.0.6"
        or source.get("archive_bytes") != 154147176
        or source.get("archive_sha256")
        != "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
        or source.get("uvspec_sha256")
        != "d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a"
        or not isinstance(source.get("governing_files"), list)
        or len(source["governing_files"]) != 6
    ):
        raise ValidationError("libRadtran source identity changed")
    return spec


def _number_token(value: float, *, width: int = 0, decimals: int = 3) -> str:
    rendered = f"{float(value):0{width}.{decimals}f}" if width else (
        f"{float(value):.{decimals}f}"
    )
    return rendered.replace("-", "m").replace(".", "p")


def _expected_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    controlled = spec["controlled_exponential_atmospheres"]
    axes = controlled["target_true_altitude_deg"]
    classified_altitudes = [
        *[(float(value), "diagnostic_only") for value in axes["diagnostic_only"]],
        *[(float(value), "admitted_domain") for value in axes["admitted_domain"]],
        *[(float(value), "vertical_control") for value in axes["vertical_control"]],
    ]
    cases: list[dict[str, Any]] = []
    for grid_id in _vertical_grids(spec):
        grid_token = (
            "source"
            if grid_id == "afglus_source_levels_v1"
            else "refined"
        )
        for scale_height in controlled["scale_height_km"]:
            for altitude, domain_role in classified_altitudes:
                cases.append(
                    {
                        "case_id": (
                            f"geometry_{grid_token}"
                            f"_h{_number_token(scale_height)}km"
                            f"_alt{_number_token(altitude, width=6, decimals=2)}deg"
                        ),
                        "grid_id": grid_id,
                        "scale_height_km": float(scale_height),
                        "target_true_altitude_deg": altitude,
                        "domain_role": domain_role,
                    }
                )
    repeat_policy = spec["repeat_control"]
    original = next(
        case
        for case in cases
        if case["grid_id"] == repeat_policy["grid_id"]
        and case["scale_height_km"] == float(repeat_policy["scale_height_km"])
        and case["target_true_altitude_deg"]
        == float(repeat_policy["target_true_altitude_deg"])
    )
    return [
        *cases,
        {
            **original,
            "case_id": f"{original['case_id']}_repeat",
            "repeat_of": original["case_id"],
        },
    ]


def _layer_optical_depths(
    levels: list[float],
    *,
    scale_height_km: float,
    vertical_optical_depth: float,
) -> list[float]:
    top = levels[0]
    denominator = 1.0 - math.exp(-top / scale_height_km)
    depths = [0.0]
    for high, low in zip(levels, levels[1:]):
        depths.append(
            vertical_optical_depth
            * (
                math.exp(-low / scale_height_km)
                - math.exp(-high / scale_height_km)
            )
            / denominator
        )
    return depths


def _shell_slant_optical_depth(
    levels: list[float],
    *,
    earth_radius_km: float,
    scale_height_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
) -> float:
    depths = _layer_optical_depths(
        levels,
        scale_height_km=scale_height_km,
        vertical_optical_depth=vertical_optical_depth,
    )
    impact = earth_radius_km * math.cos(
        math.radians(target_true_altitude_deg)
    )
    total = 0.0
    compensation = 0.0
    for high, low, depth in zip(levels, levels[1:], depths[1:]):
        high_radius = earth_radius_km + high
        low_radius = earth_radius_km + low
        high_length = math.sqrt(
            (high_radius - impact) * (high_radius + impact)
        )
        low_length = math.sqrt(
            max(0.0, (low_radius - impact) * (low_radius + impact))
        )
        term = depth * (high_length - low_length) / (high - low)
        corrected = term - compensation
        next_total = total + corrected
        compensation = (next_total - total) - corrected
        total = next_total
    return total


def _midpoint_chapman_surface_slant_optical_depth(
    levels: list[float],
    *,
    earth_radius_km: float,
    scale_height_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
) -> float:
    """Independently reconstruct cdisort's surface Chapman-factor use."""
    depths = _layer_optical_depths(
        levels,
        scale_height_km=scale_height_km,
        vertical_optical_depth=vertical_optical_depth,
    )
    bottom_high = levels[-2]
    bottom_low = levels[-1]
    midpoint_altitude = (bottom_high + bottom_low) / 2.0
    midpoint_radius = earth_radius_km + midpoint_altitude
    impact = midpoint_radius * math.cos(
        math.radians(target_true_altitude_deg)
    )

    slant_total = 0.0
    slant_compensation = 0.0
    for layer_index in range(len(levels) - 1):
        high = levels[layer_index]
        low = levels[layer_index + 1]
        if high <= midpoint_altitude:
            continue
        path_low = (
            midpoint_altitude
            if layer_index == len(levels) - 2
            else low
        )
        high_radius = earth_radius_km + high
        low_radius = earth_radius_km + path_low
        high_distance = math.sqrt(
            (high_radius - impact) * (high_radius + impact)
        )
        low_distance = math.sqrt(
            max(0.0, (low_radius - impact) * (low_radius + impact))
        )
        term = (
            depths[layer_index + 1]
            * (high_distance - low_distance)
            / (high - low)
        )
        corrected = term - slant_compensation
        next_total = slant_total + corrected
        slant_compensation = (next_total - slant_total) - corrected
        slant_total = next_total

    vertical_total = 0.0
    vertical_compensation = 0.0
    for depth in [*depths[1:-1], 0.5 * depths[-1]]:
        corrected = depth - vertical_compensation
        next_total = vertical_total + corrected
        vertical_compensation = (next_total - vertical_total) - corrected
        vertical_total = next_total
    return vertical_optical_depth * slant_total / vertical_total


def _squared_altitude_integrand(
    *,
    earth_radius_km: float,
    scale_height_km: float,
    top_altitude_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
) -> Callable[[float], float]:
    radius = earth_radius_km
    altitude_radians = math.radians(target_true_altitude_deg)
    one_minus_cosine = 2.0 * math.sin(altitude_radians / 2.0) ** 2
    normalization = scale_height_km * (
        1.0 - math.exp(-top_altitude_km / scale_height_km)
    )
    beta_zero = vertical_optical_depth / normalization

    def integrand(root_altitude: float) -> float:
        if root_altitude == 0.0:
            return (
                beta_zero * math.sqrt(2.0 * radius)
                if target_true_altitude_deg == 0.0
                else 0.0
            )
        altitude = root_altitude * root_altitude
        radial = radius + altitude
        denominator = math.sqrt(
            (altitude + radius * one_minus_cosine)
            * (2.0 * radius + altitude - radius * one_minus_cosine)
        )
        return (
            2.0
            * root_altitude
            * beta_zero
            * math.exp(-altitude / scale_height_km)
            * radial
            / denominator
        )

    return integrand


def _gk15_interval(
    function: Callable[[float], float],
    start: float,
    stop: float,
) -> tuple[float, float, int]:
    center = (start + stop) / 2.0
    half_length = (stop - start) / 2.0
    center_value = function(center)
    if not math.isfinite(center_value) or center_value < 0.0:
        raise ValidationError("Gauss-Kronrod integrand is invalid")
    kronrod = _GK15_WEIGHTS[-1] * center_value
    gauss = _G7_WEIGHTS[-1] * center_value
    evaluations = 1
    gauss_weight_index = 0
    for index, abscissa in enumerate(_GK15_ABSCISSAE[:-1]):
        offset = half_length * abscissa
        left = function(center - offset)
        right = function(center + offset)
        evaluations += 2
        if (
            not math.isfinite(left)
            or not math.isfinite(right)
            or left < 0.0
            or right < 0.0
        ):
            raise ValidationError("Gauss-Kronrod integrand is invalid")
        pair = left + right
        kronrod += _GK15_WEIGHTS[index] * pair
        if index in (1, 3, 5):
            gauss += _G7_WEIGHTS[gauss_weight_index] * pair
            gauss_weight_index += 1
    kronrod *= half_length
    gauss *= half_length
    return kronrod, abs(kronrod - gauss), evaluations


def _adaptive_gauss_kronrod_15(
    function: Callable[[float], float],
    start: float,
    stop: float,
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
    maximum_depth: int,
) -> tuple[float, dict[str, int | float]]:
    evaluations = 0
    deepest = 0

    def recurse(
        left: float,
        right: float,
        requested_absolute: float,
        depth: int,
    ) -> float:
        nonlocal evaluations, deepest
        deepest = max(deepest, maximum_depth - depth)
        value, error, count = _gk15_interval(function, left, right)
        evaluations += count
        tolerance = max(requested_absolute, relative_tolerance * abs(value))
        if error <= tolerance:
            return value
        if depth <= 0:
            raise ValidationError("adaptive Gauss-Kronrod oracle did not converge")
        middle = (left + right) / 2.0
        return recurse(
            left,
            middle,
            requested_absolute / 2.0,
            depth - 1,
        ) + recurse(
            middle,
            right,
            requested_absolute / 2.0,
            depth - 1,
        )

    result = recurse(start, stop, absolute_tolerance, maximum_depth)
    return result, {
        "function_evaluations": evaluations,
        "maximum_depth_used": deepest,
        "requested_relative_tolerance": relative_tolerance,
        "requested_absolute_tolerance": absolute_tolerance,
    }


def independent_continuous_slant_optical_depth(
    *,
    earth_radius_km: float,
    scale_height_km: float,
    top_altitude_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
    relative_tolerance: float,
    absolute_tolerance: float,
    maximum_depth: int,
) -> tuple[float, dict[str, int | float]]:
    function = _squared_altitude_integrand(
        earth_radius_km=earth_radius_km,
        scale_height_km=scale_height_km,
        top_altitude_km=top_altitude_km,
        target_true_altitude_deg=target_true_altitude_deg,
        vertical_optical_depth=vertical_optical_depth,
    )
    return _adaptive_gauss_kronrod_15(
        function,
        0.0,
        math.sqrt(top_altitude_km),
        relative_tolerance=relative_tolerance,
        absolute_tolerance=absolute_tolerance,
        maximum_depth=maximum_depth,
    )


def _parse_controlled_files(
    case_dir: Path,
    *,
    case: dict[str, Any],
    levels: list[float],
    spec: dict[str, Any],
) -> dict[str, float | None]:
    atmosphere_rows: list[list[float]] = []
    for line in (case_dir / "atmosphere.dat").read_text(
        encoding="utf-8"
    ).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            fields = stripped.split()
            if len(fields) != 3:
                raise ValidationError("controlled atmosphere must have three columns")
            try:
                atmosphere_rows.append([float(value) for value in fields])
            except ValueError as exc:
                raise ValidationError("controlled atmosphere is nonnumeric") from exc
    if (
        len(atmosphere_rows) != len(levels)
        or [row[0] for row in atmosphere_rows] != levels
        or any(
            not all(math.isfinite(value) for value in row)
            or row[1] <= 0.0
            or row[2] <= 0.0
            for row in atmosphere_rows
        )
    ):
        raise ValidationError("controlled atmosphere levels or values differ")

    tau_rows: list[list[float]] = []
    for line in (case_dir / "molecular_tau.dat").read_text(
        encoding="utf-8"
    ).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            fields = stripped.split()
            if len(fields) != 2:
                raise ValidationError("controlled tau file must have two columns")
            try:
                tau_rows.append([float(value) for value in fields])
            except ValueError as exc:
                raise ValidationError("controlled tau file is nonnumeric") from exc
    expected_depths = _layer_optical_depths(
        levels,
        scale_height_km=float(case["scale_height_km"]),
        vertical_optical_depth=float(
            spec["controlled_exponential_atmospheres"]["vertical_optical_depth"]
        ),
    )
    if (
        len(tau_rows) != len(levels)
        or [row[0] for row in tau_rows] != levels
        or any(
            not math.isclose(row[1], expected, rel_tol=2e-14, abs_tol=2e-16)
            for row, expected in zip(tau_rows, expected_depths)
        )
    ):
        raise ValidationError("controlled tau layers differ from the declared law")

    input_lines = (case_dir / "input.inp").read_text(
        encoding="utf-8"
    ).splitlines()
    expected_lines = {
        "data_files_path libradtran_data",
        "atmosphere_file atmosphere.dat",
        "source solar libradtran_data/solar_flux/atlas_plus_modtran",
        "wavelength 550 550",
        "mol_abs_param crs",
        "mol_tau_file abs molecular_tau.dat",
        "no_scattering",
        "albedo 0",
        "earth_radius 6370",
        f"sza {format(90.0 - float(case['target_true_altitude_deg']), '.17g')}",
        "rte_solver disort",
        "pseudospherical",
        "number_of_streams 16",
        "mc_randomseed 49979687",
        "output_quantity transmittance",
        "output_user lambda edir uavgdir",
        "zout 0",
        "quiet",
    }
    if (
        len(input_lines) != len(expected_lines)
        or set(input_lines) != expected_lines
        or any(
            token in "\n".join(input_lines)
            for token in ("aerosol_", "mc_spherical", "altitude ", "atm_z_grid")
        )
    ):
        raise ValidationError("controlled uvspec input differs from the contract")

    rows = [
        line.split()
        for line in (case_dir / "stdout.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    if len(rows) != 1 or len(rows[0]) != 3:
        raise ValidationError("direct output must contain lambda/edir/uavgdir")
    try:
        wavelength, edir, uavgdir = [float(value) for value in rows[0]]
    except ValueError as exc:
        raise ValidationError("direct output is nonnumeric") from exc
    if (
        wavelength != 550.0
        or not math.isfinite(edir)
        or not math.isfinite(uavgdir)
        or edir < 0.0
        or uavgdir <= 0.0
    ):
        raise ValidationError("direct output values are invalid")
    altitude = float(case["target_true_altitude_deg"])
    actinic = 4.0 * math.pi * uavgdir
    projected = (
        edir / math.sin(math.radians(altitude))
        if altitude > 0.0
        else None
    )
    selected = projected if projected is not None else actinic
    if not 0.0 < selected <= 1.0 or not 0.0 < actinic <= 1.0:
        raise ValidationError("direct transmission is outside (0, 1]")
    return {
        "wavelength_nm": wavelength,
        "edir_over_e0_horizontal": edir,
        "uavgdir_over_e0_mean_intensity": uavgdir,
        "edir_projected_transmission": projected,
        "four_pi_uavgdir_transmission": actinic,
        "selected_transmission": selected,
        "selected_channel": (
            "edir_over_sin_true_altitude"
            if projected is not None
            else "four_pi_uavgdir_pure_absorption_diagnostic"
        ),
        "selected_slant_optical_depth": -math.log(selected),
        "selected_extinction_magnitude": -2.5 * math.log10(selected),
    }


def _assert_close(
    actual: Any,
    expected: float,
    label: str,
    *,
    relative_tolerance: float = 2e-13,
    absolute_tolerance: float = 2e-14,
) -> None:
    if (
        isinstance(actual, bool)
        or not isinstance(actual, (int, float))
        or not math.isfinite(float(actual))
        or not math.isclose(
            float(actual),
            expected,
            rel_tol=relative_tolerance,
            abs_tol=absolute_tolerance,
        )
    ):
        raise ValidationError(f"{label} differs")


def _verify_case_receipts(case_dir: Path, result: dict[str, Any]) -> None:
    receipts = result.get("files")
    if not isinstance(receipts, list):
        raise ValidationError("case file receipts are missing")
    expected = CASE_FILES - {"result.json"}
    actual_receipts = {
        _validate_file_receipt(case_dir, receipt, label="case file")
        for receipt in receipts
    }
    if actual_receipts != expected:
        raise ValidationError("case file receipt inventory differs")
    actual_files = {
        path.name for path in case_dir.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if actual_files != CASE_FILES or any(path.is_symlink() for path in case_dir.iterdir()):
        raise ValidationError("case directory contains an unowned entry")


def _verify_repo_receipt(
    receipt: Any,
    *,
    expected_path: str,
    label: str,
) -> None:
    if not isinstance(receipt, dict) or receipt.get("path") != expected_path:
        raise ValidationError(f"{label} repository path differs")
    _validate_file_receipt(REPO_ROOT, receipt, label=label)


def _verify_tooling(
    manifest: dict[str, Any],
    spec: dict[str, Any],
    spec_path: Path,
) -> None:
    tooling = manifest.get("tooling")
    specifications = manifest.get("specifications")
    if not isinstance(tooling, dict) or not isinstance(specifications, dict):
        raise ValidationError("tooling or specification receipts are missing")
    expected_tooling_paths = {
        "builder": "scripts/build_visibility_direct_geometry_probe.py",
        "validator": "scripts/validate_visibility_direct_geometry_probe.py",
        "checkpoint1_spec": (
            "scripts/visibility_reference_lab/phase1_lab_spec.json"
        ),
        "checkpoint1_builder": "scripts/build_visibility_radiance_lut.py",
        "checkpoint1_validator": "scripts/validate_visibility_radiance_lut.py",
        "elevated_site_checkpoint_spec": (
            "scripts/visibility_reference_lab/"
            "phase1_elevated_site_probe_spec.json"
        ),
        "elevated_site_checkpoint_builder": (
            "scripts/build_visibility_elevated_site_probe.py"
        ),
        "elevated_site_checkpoint_validator": (
            "scripts/validate_visibility_elevated_site_probe.py"
        ),
    }
    if set(tooling) != set(expected_tooling_paths):
        raise ValidationError("tooling receipt inventory differs")
    for role, expected_path in expected_tooling_paths.items():
        _verify_repo_receipt(
            tooling[role],
            expected_path=expected_path,
            label=role,
        )
    if spec_path != DEFAULT_SPEC_PATH.resolve():
        expected_spec_path = spec_path.relative_to(REPO_ROOT).as_posix()
    else:
        expected_spec_path = (
            "scripts/visibility_reference_lab/"
            "phase1_direct_geometry_probe_spec.json"
        )
    expected_specifications = {
        "direct_geometry_probe": expected_spec_path,
        "checkpoint1_lab": expected_tooling_paths["checkpoint1_spec"],
        "elevated_site_checkpoint": (
            expected_tooling_paths["elevated_site_checkpoint_spec"]
        ),
    }
    if set(specifications) != set(expected_specifications):
        raise ValidationError("specification receipt inventory differs")
    for role, expected_path in expected_specifications.items():
        _verify_repo_receipt(
            specifications[role],
            expected_path=expected_path,
            label=role,
        )

    for lab_name, declaration in spec["base_labs"].items():
        prefix = (
            "checkpoint1"
            if lab_name == "checkpoint1"
            else "elevated_site_checkpoint"
        )
        for role in ("spec", "builder", "validator"):
            receipt = tooling[f"{prefix}_{role}"]
            if (
                receipt["bytes"] != declaration[f"{role}_bytes"]
                or receipt["sha256"] != declaration[f"{role}_sha256"]
            ):
                raise ValidationError("frozen predecessor identity differs")


def _verify_generator(manifest: dict[str, Any], spec: dict[str, Any]) -> None:
    generator = manifest.get("generator")
    source = spec["source"]
    if not isinstance(generator, dict):
        raise ValidationError("generator receipt is missing")
    archive = generator.get("source_archive")
    if (
        not isinstance(archive, dict)
        or archive.get("bytes") != source["archive_bytes"]
        or archive.get("sha256") != source["archive_sha256"]
        or source["version"] not in str(generator.get("uvspec_version"))
        or generator.get("uvspec_sha256") != source["uvspec_sha256"]
        or generator.get("governing_source_files")
        != source["governing_files"]
    ):
        raise ValidationError("libRadtran generator identity differs")
    source_grid = generator.get("source_grid_control")
    expected_grid = _vertical_grids(spec)["afglus_source_levels_v1"]
    if source_grid != {
        "path": "data/atmmod/afglus.dat",
        "level_count": len(expected_grid),
        "levels_km_descending": expected_grid,
    }:
        raise ValidationError("libRadtran source-grid receipt differs")


def _verify_artifact_inventory(
    artifact_root: Path,
    manifest: dict[str, Any],
) -> None:
    receipts = manifest.get("files")
    if not isinstance(receipts, list):
        raise ValidationError("artifact file inventory is missing")
    expected_paths = {
        _validate_file_receipt(artifact_root, receipt, label="artifact file")
        for receipt in receipts
    }
    actual_paths: set[str] = set()
    for path in artifact_root.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"artifact contains a symlink: {path}")
        if path.is_file() and path.name != "artifact-manifest.json":
            actual_paths.add(path.relative_to(artifact_root).as_posix())
    if actual_paths != expected_paths:
        raise ValidationError("artifact file inventory is incomplete")


def _verify_repeat(
    artifact_root: Path,
    receipt: Any,
    *,
    original_case_id: str,
    repeat_case_id: str,
) -> None:
    if (
        not isinstance(receipt, dict)
        or receipt.get("byte_identical") is not True
        or receipt.get("original_case_id") != original_case_id
        or receipt.get("repeat_case_id") != repeat_case_id
    ):
        raise ValidationError("fixed-input repeat receipt differs")
    compared = receipt.get("compared_files")
    filenames = (
        "atmosphere.dat",
        "input.inp",
        "molecular_tau.dat",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    )
    if not isinstance(compared, list) or len(compared) != len(filenames):
        raise ValidationError("fixed-input repeat file receipt is incomplete")
    for entry, filename in zip(compared, filenames):
        original = artifact_root / original_case_id / filename
        repeated = artifact_root / repeat_case_id / filename
        expected_path = (
            f"{original_case_id}/{filename} == {repeat_case_id}/{filename}"
        )
        if (
            not isinstance(entry, dict)
            or entry.get("path") != expected_path
            or entry.get("sha256") != _sha256_file(original)
            or original.read_bytes() != repeated.read_bytes()
        ):
            raise ValidationError("fixed-input repeat is not byte-identical")


def validate_artifact(
    artifact_root: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    spec_path = spec_path.resolve()
    if not artifact_root.is_dir() or artifact_root.is_symlink():
        raise ValidationError("artifact root must be a real directory")
    manifest_path = artifact_root / "artifact-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValidationError("artifact manifest is missing")
    manifest_sha256 = _sha256_file(manifest_path)
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256
    ):
        raise ValidationError("artifact manifest SHA-256 does not match")

    spec = _load_spec(spec_path)
    manifest = _load_json(manifest_path, "artifact manifest")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("artifact_status") != ARTIFACT_STATUS
        or manifest.get("spec_id") != spec.get("spec_id")
        or manifest.get("model_id")
        != spec["scientific_boundary"]["model_id"]
        or manifest.get("runtime_boundary") != spec.get("runtime_boundary")
    ):
        raise ValidationError("artifact identity or runtime boundary differs")
    _verify_tooling(manifest, spec, spec_path)
    _verify_generator(manifest, spec)
    generation_identity = {
        "tooling": manifest.get("tooling"),
        "specifications": manifest.get("specifications"),
        "generator": manifest.get("generator"),
        "environment": manifest.get("environment"),
        "runtime_boundary": manifest.get("runtime_boundary"),
    }
    if manifest.get("generation_identity") != generation_identity:
        raise ValidationError("artifact generation identity is inconsistent")
    generation_fingerprint = _sha256_bytes(
        _canonical_json_bytes(generation_identity)
    )
    if manifest.get("generation_fingerprint") != generation_fingerprint:
        raise ValidationError("artifact generation fingerprint differs")
    _verify_artifact_inventory(artifact_root, manifest)

    expected_cases = _expected_cases(spec)
    expected_by_id = {case["case_id"]: case for case in expected_cases}
    if (
        len(expected_by_id) != 145
        or manifest.get("case_count") != 145
        or manifest.get("nonrepeat_case_count") != 144
        or manifest.get("uvspec_run_count") != 145
        or manifest.get("grid_level_counts")
        != {
            grid_id: len(levels)
            for grid_id, levels in _vertical_grids(spec).items()
        }
    ):
        raise ValidationError("artifact case or grid counts differ")
    case_summaries = manifest.get("cases")
    if (
        not isinstance(case_summaries, list)
        or len(case_summaries) != len(expected_cases)
        or {
            entry.get("case", {}).get("case_id")
            for entry in case_summaries
            if isinstance(entry, dict)
        }
        != set(expected_by_id)
    ):
        raise ValidationError("artifact case summary inventory differs")
    summary_by_id = {
        entry["case"]["case_id"]: entry
        for entry in case_summaries
    }

    grids = _vertical_grids(spec)
    controlled = spec["controlled_exponential_atmospheres"]
    boundary = spec["scientific_boundary"]
    oracle = spec["independent_oracle"]
    acceptance = spec["acceptance"]
    validated_results: list[dict[str, Any]] = []
    for case_id, expected_case in expected_by_id.items():
        case_dir = artifact_root / case_id
        if not case_dir.is_dir() or case_dir.is_symlink():
            raise ValidationError(f"case directory is missing: {case_id}")
        result = _load_json(case_dir / "result.json", f"case {case_id}")
        if (
            result.get("schema") != CASE_SCHEMA
            or result.get("artifact_status") != ARTIFACT_STATUS
            or result.get("case") != expected_case
            or result.get("generation_fingerprint") != generation_fingerprint
            or result.get("layer_count") != len(grids[expected_case["grid_id"]]) - 1
        ):
            raise ValidationError(f"case identity differs: {case_id}")
        _verify_case_receipts(case_dir, result)
        parsed = _parse_controlled_files(
            case_dir,
            case=expected_case,
            levels=grids[expected_case["grid_id"]],
            spec=spec,
        )
        recorded_result = result.get("result")
        if not isinstance(recorded_result, dict) or set(recorded_result) != set(parsed):
            raise ValidationError(f"case result shape differs: {case_id}")
        for field, expected in parsed.items():
            actual = recorded_result[field]
            if expected is None:
                if actual is not None:
                    raise ValidationError(f"case result {field} differs")
            elif isinstance(expected, str):
                if actual != expected:
                    raise ValidationError(f"case result {field} differs")
            else:
                _assert_close(actual, float(expected), f"case result {field}")

        shell_tau = _shell_slant_optical_depth(
            grids[expected_case["grid_id"]],
            earth_radius_km=float(boundary["earth_radius_km"]),
            scale_height_km=float(expected_case["scale_height_km"]),
            target_true_altitude_deg=float(
                expected_case["target_true_altitude_deg"]
            ),
            vertical_optical_depth=float(controlled["vertical_optical_depth"]),
        )
        midpoint_tau = _midpoint_chapman_surface_slant_optical_depth(
            grids[expected_case["grid_id"]],
            earth_radius_km=float(boundary["earth_radius_km"]),
            scale_height_km=float(expected_case["scale_height_km"]),
            target_true_altitude_deg=float(
                expected_case["target_true_altitude_deg"]
            ),
            vertical_optical_depth=float(controlled["vertical_optical_depth"]),
        )
        independent_tau, independent_convergence = (
            independent_continuous_slant_optical_depth(
                earth_radius_km=float(boundary["earth_radius_km"]),
                scale_height_km=float(expected_case["scale_height_km"]),
                top_altitude_km=float(boundary["top_altitude_km"]),
                target_true_altitude_deg=float(
                    expected_case["target_true_altitude_deg"]
                ),
                vertical_optical_depth=float(
                    controlled["vertical_optical_depth"]
                ),
                relative_tolerance=float(oracle["validator_relative_tolerance"]),
                absolute_tolerance=float(oracle["validator_absolute_tolerance"]),
                maximum_depth=int(oracle["maximum_recursion_depth"]),
            )
        )
        oracles = result.get("oracles")
        if not isinstance(oracles, dict):
            raise ValidationError(f"case oracles are missing: {case_id}")
        _assert_close(
            oracles.get("same_layer_shell_slant_optical_depth"),
            shell_tau,
            "same-layer shell oracle",
        )
        _assert_close(
            oracles.get(
                "libRadtran_midpoint_chapman_reconstructed_slant_optical_depth"
            ),
            midpoint_tau,
            "midpoint-Chapman reconstruction",
        )
        stored_continuous = oracles.get(
            "continuous_exponential_slant_optical_depth"
        )
        _assert_close(
            stored_continuous,
            independent_tau,
            "independent continuous oracle",
            relative_tolerance=float(
                oracle["stored_oracle_cross_method_relative_tolerance"]
            ),
            absolute_tolerance=2e-12,
        )
        _assert_close(
            oracles.get("continuous_exponential_airmass"),
            independent_tau / float(controlled["vertical_optical_depth"]),
            "continuous airmass",
            relative_tolerance=2e-9,
            absolute_tolerance=2e-11,
        )
        builder_convergence = oracles.get("adaptive_simpson_convergence")
        if (
            not isinstance(builder_convergence, dict)
            or builder_convergence.get("function_evaluations", 0) <= 0
            or builder_convergence.get("maximum_depth_used", -1) < 0
            or independent_convergence["function_evaluations"] <= 0
        ):
            raise ValidationError("oracle convergence receipt is invalid")

        selected_tau = float(parsed["selected_slant_optical_depth"])
        shell_vs_continuous = abs(shell_tau - independent_tau) / independent_tau
        midpoint_vs_shell = abs(midpoint_tau - shell_tau) / shell_tau
        midpoint_vs_continuous = (
            abs(midpoint_tau - independent_tau) / independent_tau
        )
        projected = parsed["edir_projected_transmission"]
        extraction_relative = (
            abs(float(projected) - float(parsed["four_pi_uavgdir_transmission"]))
            / float(projected)
            if projected is not None
            else None
        )
        altitude = float(expected_case["target_true_altitude_deg"])
        plane_tau = (
            float(controlled["vertical_optical_depth"])
            / math.sin(math.radians(altitude))
            if altitude > 0.0
            else None
        )
        plane_relative = (
            abs(plane_tau - independent_tau) / independent_tau
            if plane_tau is not None
            else None
        )
        expected_comparison = {
            "libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs": abs(
                selected_tau - midpoint_tau
            ),
            "positive_altitude_extraction_relative_difference": (
                extraction_relative
            ),
            "same_layer_shell_vs_continuous_relative_slant_optical_depth": (
                shell_vs_continuous
            ),
            "midpoint_chapman_vs_same_layer_shell_relative_slant_optical_depth": (
                midpoint_vs_shell
            ),
            "midpoint_chapman_vs_continuous_relative_slant_optical_depth": (
                midpoint_vs_continuous
            ),
            "plane_parallel_vs_continuous_relative_slant_optical_depth": (
                plane_relative
            ),
            "vertical_control_slant_optical_depth_abs_difference": (
                abs(
                    selected_tau
                    - float(controlled["vertical_optical_depth"])
                )
                if expected_case["domain_role"] == "vertical_control"
                else None
            ),
        }
        comparison = result.get("comparison")
        if not isinstance(comparison, dict) or set(comparison) != set(
            expected_comparison
        ):
            raise ValidationError(f"case comparison shape differs: {case_id}")
        for field, expected in expected_comparison.items():
            actual = comparison[field]
            if expected is None:
                if actual is not None:
                    raise ValidationError(f"case comparison {field} differs")
            else:
                _assert_close(
                    actual,
                    expected,
                    f"case comparison {field}",
                    relative_tolerance=3e-9,
                    absolute_tolerance=3e-12,
                )
        if (
            (
                expected_case["domain_role"]
                in {"admitted_domain", "vertical_control"}
                and expected_comparison[
                    "libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs"
                ]
                > acceptance[
                    "admitted_libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs_tolerance"
                ]
            )
            or (
                expected_case["domain_role"]
                in {"admitted_domain", "vertical_control"}
                and extraction_relative is not None
                and extraction_relative
                > acceptance[
                    "admitted_positive_altitude_extraction_relative_tolerance"
                ]
            )
            or (
                expected_case["grid_id"]
                == "near_horizon_piecewise_refined_v1"
                and expected_case["domain_role"] == "admitted_domain"
                and midpoint_vs_continuous
                > acceptance[
                    "refined_midpoint_vs_continuous_admitted_relative_slant_optical_depth_tolerance"
                ]
            )
            or (
                expected_comparison[
                    "vertical_control_slant_optical_depth_abs_difference"
                ]
                is not None
                and expected_comparison[
                    "vertical_control_slant_optical_depth_abs_difference"
                ]
                > acceptance[
                    "vertical_control_slant_optical_depth_abs_tolerance"
                ]
            )
        ):
            raise ValidationError(f"case exceeds an acceptance tolerance: {case_id}")

        expected_summary = summary_by_id[case_id]
        if (
            expected_summary.get("case") != expected_case
            or expected_summary.get("layer_count") != result["layer_count"]
            or expected_summary.get("result") != result["result"]
            or expected_summary.get("comparison") != result["comparison"]
            or expected_summary.get("oracles")
            != {
                key: value
                for key, value in result["oracles"].items()
                if key != "adaptive_simpson_convergence"
            }
        ):
            raise ValidationError(f"manifest case summary differs: {case_id}")
        validated_results.append(
            {
                "case": expected_case,
                "comparison": expected_comparison,
            }
        )

    nonrepeat = [
        result for result in validated_results
        if "repeat_of" not in result["case"]
    ]
    refined_admitted = [
        result for result in nonrepeat
        if result["case"]["grid_id"] == "near_horizon_piecewise_refined_v1"
        and result["case"]["domain_role"] == "admitted_domain"
    ]
    source_admitted = [
        result for result in nonrepeat
        if result["case"]["grid_id"] == "afglus_source_levels_v1"
        and result["case"]["domain_role"] == "admitted_domain"
    ]
    diagnostics = [
        result for result in nonrepeat
        if result["case"]["domain_role"] == "diagnostic_only"
    ]
    admission_controls = [
        result
        for result in nonrepeat
        if result["case"]["domain_role"]
        in {"admitted_domain", "vertical_control"}
    ]

    def maximum(subset: list[dict[str, Any]], field: str) -> float:
        return max(float(result["comparison"][field]) for result in subset)

    expected_summary = {
        "maximum_admitted_libradtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs": (
            maximum(
                admission_controls,
                "libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs",
            )
        ),
        "maximum_admitted_positive_altitude_extraction_relative_difference": max(
            float(
                result["comparison"][
                    "positive_altitude_extraction_relative_difference"
                ]
            )
            for result in admission_controls
            if result["comparison"][
                "positive_altitude_extraction_relative_difference"
            ]
            is not None
        ),
        "maximum_source_grid_admitted_midpoint_vs_continuous_relative_error": maximum(
            source_admitted,
            "midpoint_chapman_vs_continuous_relative_slant_optical_depth",
        ),
        "maximum_refined_grid_admitted_midpoint_vs_continuous_relative_error": maximum(
            refined_admitted,
            "midpoint_chapman_vs_continuous_relative_slant_optical_depth",
        ),
        "maximum_diagnostic_midpoint_vs_continuous_relative_error": maximum(
            diagnostics,
            "midpoint_chapman_vs_continuous_relative_slant_optical_depth",
        ),
        "maximum_diagnostic_libradtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs": (
            maximum(
                diagnostics,
                "libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs",
            )
        ),
        "maximum_refined_grid_admitted_same_layer_shell_vs_continuous_relative_error": maximum(
            refined_admitted,
            "same_layer_shell_vs_continuous_relative_slant_optical_depth",
        ),
        "maximum_plane_parallel_admitted_relative_error": max(
            float(
                result["comparison"][
                    "plane_parallel_vs_continuous_relative_slant_optical_depth"
                ]
            )
            for result in refined_admitted
        ),
    }
    summary = manifest.get("summary")
    if not isinstance(summary, dict) or set(summary) != set(expected_summary):
        raise ValidationError("artifact numerical summary shape differs")
    for field, expected in expected_summary.items():
        _assert_close(
            summary[field],
            expected,
            f"artifact summary {field}",
            relative_tolerance=3e-9,
            absolute_tolerance=3e-12,
        )

    repeated = expected_cases[-1]
    _verify_repeat(
        artifact_root,
        manifest.get("fixed_input_repeat"),
        original_case_id=repeated["repeat_of"],
        repeat_case_id=repeated["case_id"],
    )
    allowed_root_entries = {
        "artifact-manifest.json",
        *expected_by_id,
    }
    if {path.name for path in artifact_root.iterdir()} != allowed_root_entries:
        raise ValidationError("artifact root contains an unowned entry")

    return {
        "manifest_sha256": manifest_sha256,
        "case_count": len(expected_cases),
        "uvspec_run_count": len(expected_cases),
        "all_files_bound": True,
        "independent_continuous_oracle_recomputed": True,
        "same_layer_shell_oracle_recomputed": True,
        "midpoint_chapman_reconstruction_recomputed": True,
        "refined_admitted_cases_within_tolerance": True,
        "fixed_input_repeat_byte_identical": True,
        "exact_horizon_admitted": False,
        "network_dependency": False,
        "runtime_dependency": False,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Phase 1 direct-geometry reference artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_SPEC_PATH,
    )
    parser.add_argument("--expected-manifest-sha256")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = validate_artifact(
            args.artifact,
            spec_path=args.spec,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
