#!/usr/bin/env python3
"""Build the Phase 1 direct-transmission spherical-geometry probe.

This source-owned laboratory is external to the Moira runtime.  It compares
libRadtran's pseudo-spherical direct beam with:

* an exact shell-path calculation for the identical piecewise-constant
  extinction layers; and
* an independently integrated continuous exponential atmosphere.

The controlled pure-absorption construction also permits a diagnostic
``uavgdir`` extraction at the exact geometric horizon.  That extraction is
explicitly forbidden for the production aerosol model, where libRadtran's
delta-M scaling makes it a different quantity from unscaled direct
transmission.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SPEC_PATH = (
    SCRIPT_ROOT
    / "visibility_reference_lab"
    / "phase1_direct_geometry_probe_spec.json"
)
BASE_BUILDER_PATH = SCRIPT_ROOT / "build_visibility_radiance_lut.py"
VALIDATOR_PATH = SCRIPT_ROOT / "validate_visibility_direct_geometry_probe.py"

SPEC_SCHEMA = "moira.visibility-direct-geometry-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-direct-geometry-probe-artifact/v1"
CASE_SCHEMA = "moira.visibility-direct-geometry-probe-case/v1"
ARTIFACT_STATUS = "phase1_direct_geometry_evidence_not_runtime_data_pack"
DATA_LINK_NAME = "libradtran_data"
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


def _load_base_lab() -> Any:
    module_spec = importlib.util.spec_from_file_location(
        "_moira_visibility_reference_lab_checkpoint1_direct_geometry",
        BASE_BUILDER_PATH,
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load checkpoint-one builder: {BASE_BUILDER_PATH}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


base_lab = _load_base_lab()
VisibilityLabError = base_lab.VisibilityLabError


def _require_number(
    value: Any,
    label: str,
    low: float,
    high: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisibilityLabError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise VisibilityLabError(
            f"{label} must be finite and within [{low}, {high}]"
        )
    return result


def _strictly_increasing(values: list[Any], label: str) -> list[float]:
    result = [
        _require_number(value, label, -1.0e9, 1.0e9)
        for value in values
    ]
    if not result or any(a >= b for a, b in zip(result, result[1:])):
        raise VisibilityLabError(f"{label} must be strictly increasing")
    return result


def _strictly_decreasing(values: list[Any], label: str) -> list[float]:
    result = [
        _require_number(value, label, -1.0e9, 1.0e9)
        for value in values
    ]
    if not result or any(a <= b for a, b in zip(result, result[1:])):
        raise VisibilityLabError(f"{label} must be strictly decreasing")
    return result


def _safe_repo_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise VisibilityLabError(f"{label} path must be a nonempty string")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise VisibilityLabError(f"{label} path must remain inside the repository")
    return REPO_ROOT / relative


def _verify_declared_repo_file(
    declaration: dict[str, Any],
    *,
    label: str,
) -> Path:
    path = _safe_repo_path(declaration.get(f"{label}_path"), label)
    expected_bytes = declaration.get(f"{label}_bytes")
    expected_sha256 = declaration.get(f"{label}_sha256")
    if (
        not isinstance(expected_bytes, int)
        or expected_bytes <= 0
        or not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
    ):
        raise VisibilityLabError(f"invalid declared {label} identity")
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != expected_bytes
        or base_lab.sha256_file(path) != expected_sha256
    ):
        raise VisibilityLabError(f"declared {label} identity does not match: {path}")
    return path


def _validate_source_receipt(receipt: Any) -> None:
    if not isinstance(receipt, dict):
        raise VisibilityLabError("governing source receipt must be an object")
    path = receipt.get("path")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or Path(path).as_posix() != path
        or not isinstance(receipt.get("bytes"), int)
        or receipt["bytes"] <= 0
        or not isinstance(receipt.get("sha256"), str)
        or len(receipt["sha256"]) != 64
    ):
        raise VisibilityLabError("governing source receipt is malformed")


def _levels_from_segments(segments: list[dict[str, Any]]) -> list[float]:
    levels: set[Decimal] = set()
    previous_stop: Decimal | None = None
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise VisibilityLabError("vertical-grid segment must be an object")
        start = Decimal(str(_require_number(
            segment.get("start"),
            f"segment {index} start",
            0.0,
            120.0,
        )))
        stop = Decimal(str(_require_number(
            segment.get("stop"),
            f"segment {index} stop",
            0.0,
            120.0,
        )))
        step = Decimal(str(_require_number(
            segment.get("step"),
            f"segment {index} step",
            0.000001,
            120.0,
        )))
        if start >= stop:
            raise VisibilityLabError("vertical-grid segment start must precede stop")
        if previous_stop is not None and start != previous_stop:
            raise VisibilityLabError("vertical-grid segments must be contiguous")
        count_decimal = (stop - start) / step
        count = int(count_decimal)
        if Decimal(count) != count_decimal:
            raise VisibilityLabError("vertical-grid segment must divide exactly")
        for offset in range(count + 1):
            levels.add(start + step * offset)
        previous_stop = stop
    if not levels:
        raise VisibilityLabError("refined vertical grid is empty")
    return [float(value) for value in sorted(levels, reverse=True)]


def _target_altitudes(spec: dict[str, Any]) -> list[float]:
    axes = spec["controlled_exponential_atmospheres"][
        "target_true_altitude_deg"
    ]
    return [
        *[float(value) for value in axes["diagnostic_only"]],
        *[float(value) for value in axes["admitted_domain"]],
        *[float(value) for value in axes["vertical_control"]],
    ]


def vertical_grids(spec: dict[str, Any]) -> dict[str, list[float]]:
    grids = spec["vertical_grids"]
    return {
        grids["source_grid_control"]["grid_id"]: [
            float(value)
            for value in grids["source_grid_control"]["levels_km_descending"]
        ],
        grids["refined_candidate"]["grid_id"]: _levels_from_segments(
            grids["refined_candidate"]["segments_km"]
        ),
    }


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != SPEC_SCHEMA:
        raise VisibilityLabError("unsupported direct-geometry probe spec schema")
    if spec.get("status") != "research_probe_not_runtime_data_pack":
        raise VisibilityLabError("direct-geometry probe must remain research-only")
    if not isinstance(spec.get("spec_id"), str) or not spec["spec_id"]:
        raise VisibilityLabError("direct-geometry probe requires a spec_id")

    if spec.get("runtime_boundary") != {
        "network_allowed": False,
        "automatic_download_allowed": False,
        "engine_dependency_allowed": False,
        "engine_runtime_invocation_allowed": False,
        "generated_numerical_products_only": True,
    }:
        raise VisibilityLabError("direct-geometry runtime boundary was weakened")

    base_labs = spec.get("base_labs")
    if not isinstance(base_labs, dict) or set(base_labs) != {
        "checkpoint1",
        "elevated_site_checkpoint",
    }:
        raise VisibilityLabError("both frozen base laboratories are required")
    for lab_name, declaration in base_labs.items():
        if not isinstance(declaration, dict):
            raise VisibilityLabError(f"{lab_name} declaration must be an object")
        for role in ("spec", "builder", "validator"):
            _verify_declared_repo_file(declaration, label=role)

    source = spec.get("source")
    if not isinstance(source, dict):
        raise VisibilityLabError("libRadtran source declaration is required")
    if (
        source.get("name") != "libRadtran"
        or source.get("version") != "2.0.6"
        or source.get("role") != "external_reference_generator_only"
        or source.get("archive_bytes") != 154147176
        or source.get("archive_sha256")
        != "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
        or source.get("uvspec_sha256")
        != "d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a"
    ):
        raise VisibilityLabError("libRadtran source identity changed")
    source_files = source.get("governing_files")
    if not isinstance(source_files, list) or len(source_files) != 6:
        raise VisibilityLabError("six governing libRadtran source files are required")
    seen_source_paths: set[str] = set()
    for receipt in source_files:
        _validate_source_receipt(receipt)
        if receipt["path"] in seen_source_paths:
            raise VisibilityLabError("governing source paths must be unique")
        seen_source_paths.add(receipt["path"])

    boundary = spec.get("scientific_boundary")
    if not isinstance(boundary, dict):
        raise VisibilityLabError("scientific boundary is required")
    expected_boundary = {
        "model_id": "libradtran_2_0_6_direct_spherical_geometry_probe_v1",
        "quantity": "unscattered_direct_spectral_transmission",
        "earth_radius_km": 6370.0,
        "top_altitude_km": 120.0,
        "refraction": "disabled_true_geometric_line_of_sight",
        "multiple_scattering": "disabled_in_controlled_oracle_only",
        "production_solver": "disort",
        "production_geometry": "pseudospherical",
        "production_number_of_streams": 16,
        "random_seed_option": 49979687,
        "random_seed_role": "fixed_nonoperative_uvspec_output_control",
        "positive_altitude_extraction": (
            "edir_over_e0_divided_by_sin_true_altitude"
        ),
        "pure_absorption_cross_check": "four_pi_times_uavgdir_over_e0",
        "uavgdir_production_status": (
            "forbidden_because_delta_m_scaled_aerosol_direct_mean_intensity_"
            "is_not_unscaled_direct_transmission"
        ),
        "exact_horizon_status": "diagnostic_only_not_admitted",
        "minimum_admitted_target_true_altitude_deg": 0.25,
    }
    if boundary != expected_boundary:
        raise VisibilityLabError("scientific boundary changed")

    controlled = spec.get("controlled_exponential_atmospheres")
    if not isinstance(controlled, dict):
        raise VisibilityLabError("controlled exponential atmospheres are required")
    if (
        controlled.get("density_law")
        != "exp_minus_altitude_over_scale_height"
        or controlled.get("layer_optical_depth_law")
        != (
            "exact_vertical_integral_of_density_law_normalized_to_declared_top"
        )
        or controlled.get("libRadtran_transport")
        != "mol_tau_file_abs_with_all_scattering_disabled"
    ):
        raise VisibilityLabError("controlled atmosphere law changed")
    _require_number(controlled.get("wavelength_nm"), "wavelength", 380.0, 780.0)
    _require_number(
        controlled.get("vertical_optical_depth"),
        "vertical optical depth",
        1.0e-6,
        1.0,
    )
    scale_heights = _strictly_increasing(
        controlled.get("scale_height_km", []),
        "scale height",
    )
    if scale_heights != [0.25, 0.5, 1.0, 1.5, 8.0, 20.0]:
        raise VisibilityLabError("controlled scale-height axis changed")
    axes = controlled.get("target_true_altitude_deg")
    if not isinstance(axes, dict) or set(axes) != {
        "diagnostic_only",
        "admitted_domain",
        "vertical_control",
    }:
        raise VisibilityLabError("target-altitude axes are incomplete")
    diagnostic = _strictly_increasing(
        axes["diagnostic_only"],
        "diagnostic target altitude",
    )
    admitted = _strictly_increasing(
        axes["admitted_domain"],
        "admitted target altitude",
    )
    vertical = [
        _require_number(value, "vertical control", 0.0, 90.0)
        for value in axes["vertical_control"]
    ]
    if diagnostic != [0.0, 0.05, 0.1]:
        raise VisibilityLabError("diagnostic target-altitude axis changed")
    if admitted != [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0]:
        raise VisibilityLabError("admitted target-altitude axis changed")
    if vertical != [90.0]:
        raise VisibilityLabError("vertical control must contain only 90 degrees")

    grids = spec.get("vertical_grids")
    if not isinstance(grids, dict) or set(grids) != {
        "source_grid_control",
        "refined_candidate",
    }:
        raise VisibilityLabError("two vertical-grid declarations are required")
    source_grid = grids["source_grid_control"]
    refined_grid = grids["refined_candidate"]
    if (
        not isinstance(source_grid, dict)
        or source_grid.get("grid_id") != "afglus_source_levels_v1"
        or source_grid.get("status")
        != "comparison_control_not_production_design"
        or not isinstance(refined_grid, dict)
        or refined_grid.get("grid_id")
        != "near_horizon_piecewise_refined_v1"
        or refined_grid.get("status")
        != "candidate_for_later_actual_atmosphere_validation"
    ):
        raise VisibilityLabError("vertical-grid identity changed")
    source_levels = _strictly_decreasing(
        source_grid.get("levels_km_descending", []),
        "source-grid level",
    )
    if source_levels[0] != 120.0 or source_levels[-1] != 0.0:
        raise VisibilityLabError("source grid must span 120 km to the surface")
    refined_levels = _levels_from_segments(refined_grid.get("segments_km", []))
    if (
        refined_levels[0] != 120.0
        or refined_levels[-1] != 0.0
        or len(refined_levels) != 290
    ):
        raise VisibilityLabError("refined grid must contain the frozen 290 levels")

    oracle = spec.get("independent_oracle")
    if not isinstance(oracle, dict):
        raise VisibilityLabError("independent-oracle policy is required")
    if (
        oracle.get("builder_method")
        != (
            "adaptive_simpson_over_squared_altitude_transform_of_straight_"
            "spherical_ray"
        )
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
    ):
        raise VisibilityLabError("independent-oracle methods changed")
    for label in (
        "builder_relative_tolerance",
        "builder_absolute_tolerance",
        "validator_relative_tolerance",
        "validator_absolute_tolerance",
        "stored_oracle_cross_method_relative_tolerance",
    ):
        _require_number(oracle.get(label), label, 1.0e-15, 1.0e-6)

    acceptance = spec.get("acceptance")
    if not isinstance(acceptance, dict):
        raise VisibilityLabError("acceptance policy is required")
    expected_acceptance = {
        "admitted_libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs_tolerance": 0.00002,
        "admitted_positive_altitude_extraction_relative_tolerance": 0.00005,
        "refined_midpoint_vs_continuous_admitted_relative_slant_optical_depth_tolerance": 0.001,
        "vertical_control_slant_optical_depth_abs_tolerance": 0.00002,
        "diagnostic_subdomain_has_no_admission_tolerance": True,
    }
    if acceptance != expected_acceptance:
        raise VisibilityLabError("acceptance policy changed")

    repeat = spec.get("repeat_control")
    if repeat != {
        "grid_id": "near_horizon_piecewise_refined_v1",
        "scale_height_km": 1.5,
        "target_true_altitude_deg": 0.25,
    }:
        raise VisibilityLabError("repeat control changed")


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibilityLabError(f"cannot read direct-geometry spec: {path}") from exc
    if not isinstance(payload, dict):
        raise VisibilityLabError("direct-geometry specification must be an object")
    validate_spec(payload)
    return payload


def _number_token(value: float, *, width: int = 0, decimals: int = 3) -> str:
    rendered = f"{float(value):0{width}.{decimals}f}" if width else (
        f"{float(value):.{decimals}f}"
    )
    return rendered.replace("-", "m").replace(".", "p")


def expand_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    grid_ids = list(vertical_grids(spec))
    controlled = spec["controlled_exponential_atmospheres"]
    axes = controlled["target_true_altitude_deg"]
    classified_altitudes = [
        *[(float(value), "diagnostic_only") for value in axes["diagnostic_only"]],
        *[(float(value), "admitted_domain") for value in axes["admitted_domain"]],
        *[(float(value), "vertical_control") for value in axes["vertical_control"]],
    ]
    cases: list[dict[str, Any]] = []
    for grid_id in grid_ids:
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
    return cases


def repeat_case(spec: dict[str, Any]) -> dict[str, Any]:
    expected = spec["repeat_control"]
    original = next(
        case
        for case in expand_cases(spec)
        if case["grid_id"] == expected["grid_id"]
        and case["scale_height_km"] == float(expected["scale_height_km"])
        and case["target_true_altitude_deg"]
        == float(expected["target_true_altitude_deg"])
    )
    return {
        **original,
        "case_id": f"{original['case_id']}_repeat",
        "repeat_of": original["case_id"],
    }


def _format_number(value: float) -> str:
    return format(float(value), ".17g")


def render_atmosphere(levels_descending: list[float]) -> bytes:
    """Render a benign atmosphere whose extinction comes only from mol_tau."""
    lines = [
        "# z[km] pressure[hPa] temperature[K]",
    ]
    for altitude in levels_descending:
        pressure = 1013.25 * math.exp(-altitude / 8.0)
        lines.append(
            " ".join(
                (
                    _format_number(altitude),
                    _format_number(pressure),
                    "288.14999999999998",
                )
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def layer_optical_depths(
    levels_descending: list[float],
    *,
    scale_height_km: float,
    vertical_optical_depth: float,
) -> list[float]:
    top = levels_descending[0]
    denominator = 1.0 - math.exp(-top / scale_height_km)
    values = [0.0]
    for high, low in zip(levels_descending, levels_descending[1:]):
        layer_fraction = (
            math.exp(-low / scale_height_km)
            - math.exp(-high / scale_height_km)
        ) / denominator
        values.append(vertical_optical_depth * layer_fraction)
    if not math.isclose(
        math.fsum(values),
        vertical_optical_depth,
        rel_tol=2.0e-15,
        abs_tol=2.0e-15,
    ):
        raise VisibilityLabError("controlled layer optical depths do not close")
    return values


def render_molecular_tau(
    levels_descending: list[float],
    *,
    scale_height_km: float,
    vertical_optical_depth: float,
) -> bytes:
    depths = layer_optical_depths(
        levels_descending,
        scale_height_km=scale_height_km,
        vertical_optical_depth=vertical_optical_depth,
    )
    lines = ["# altitude[km] absorption_optical_depth_of_layer_above"]
    lines.extend(
        f"{_format_number(altitude)} {_format_number(depth)}"
        for altitude, depth in zip(levels_descending, depths)
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_input(case: dict[str, Any], spec: dict[str, Any]) -> str:
    controlled = spec["controlled_exponential_atmospheres"]
    boundary = spec["scientific_boundary"]
    solar_zenith = 90.0 - float(case["target_true_altitude_deg"])
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        "atmosphere_file atmosphere.dat",
        f"source solar {DATA_LINK_NAME}/solar_flux/atlas_plus_modtran",
        (
            f"wavelength {_format_number(controlled['wavelength_nm'])} "
            f"{_format_number(controlled['wavelength_nm'])}"
        ),
        "mol_abs_param crs",
        "mol_tau_file abs molecular_tau.dat",
        "no_scattering",
        "albedo 0",
        f"earth_radius {_format_number(boundary['earth_radius_km'])}",
        f"sza {_format_number(solar_zenith)}",
        f"rte_solver {boundary['production_solver']}",
        boundary["production_geometry"],
        (
            "number_of_streams "
            f"{boundary['production_number_of_streams']}"
        ),
        f"mc_randomseed {boundary['random_seed_option']}",
        "output_quantity transmittance",
        "output_user lambda edir uavgdir",
        "zout 0",
        "quiet",
    ]
    rendered = "\n".join(lines) + "\n"
    forbidden = ("aerosol_", "mc_spherical", "altitude ", "atm_z_grid")
    if any(token in rendered for token in forbidden):
        raise VisibilityLabError("controlled direct input crossed its boundary")
    return rendered


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
    exact_horizon = target_true_altitude_deg == 0.0

    def integrand(root_altitude: float) -> float:
        if root_altitude == 0.0:
            if exact_horizon:
                return beta_zero * math.sqrt(2.0 * radius)
            return 0.0
        altitude = root_altitude * root_altitude
        radial_distance = radius + altitude
        radial_minus_impact = altitude + radius * one_minus_cosine
        radial_plus_impact = (
            2.0 * radius + altitude - radius * one_minus_cosine
        )
        denominator_squared = radial_minus_impact * radial_plus_impact
        if denominator_squared <= 0.0:
            raise VisibilityLabError("spherical oracle encountered invalid geometry")
        density = beta_zero * math.exp(-altitude / scale_height_km)
        return (
            2.0
            * root_altitude
            * density
            * radial_distance
            / math.sqrt(denominator_squared)
        )

    return integrand


def _adaptive_simpson(
    function: Callable[[float], float],
    start: float,
    stop: float,
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
    initial_panels: int,
    maximum_depth: int,
) -> tuple[float, dict[str, int | float]]:
    if initial_panels <= 0:
        raise VisibilityLabError("adaptive Simpson initial panels must be positive")
    evaluations = 0

    def evaluate(value: float) -> float:
        nonlocal evaluations
        evaluations += 1
        result = function(value)
        if not math.isfinite(result) or result < 0.0:
            raise VisibilityLabError("spherical oracle integrand is invalid")
        return result

    deepest = 0

    def recurse(
        left: float,
        right: float,
        f_left: float,
        f_middle: float,
        f_right: float,
        estimate: float,
        tolerance: float,
        depth: int,
    ) -> float:
        nonlocal deepest
        deepest = max(deepest, maximum_depth - depth)
        middle = (left + right) / 2.0
        left_middle = (left + middle) / 2.0
        right_middle = (middle + right) / 2.0
        f_left_middle = evaluate(left_middle)
        f_right_middle = evaluate(right_middle)
        left_estimate = (
            (middle - left)
            * (f_left + 4.0 * f_left_middle + f_middle)
            / 6.0
        )
        right_estimate = (
            (right - middle)
            * (f_middle + 4.0 * f_right_middle + f_right)
            / 6.0
        )
        refined = left_estimate + right_estimate
        delta = refined - estimate
        if depth <= 0:
            raise VisibilityLabError("adaptive Simpson oracle did not converge")
        if abs(delta) <= 15.0 * tolerance:
            return refined + delta / 15.0
        return recurse(
            left,
            middle,
            f_left,
            f_left_middle,
            f_middle,
            left_estimate,
            tolerance / 2.0,
            depth - 1,
        ) + recurse(
            middle,
            right,
            f_middle,
            f_right_middle,
            f_right,
            right_estimate,
            tolerance / 2.0,
            depth - 1,
        )

    panel_width = (stop - start) / initial_panels
    panel_results: list[float] = []
    for panel in range(initial_panels):
        left = start + panel * panel_width
        right = stop if panel == initial_panels - 1 else left + panel_width
        middle = (left + right) / 2.0
        f_left = evaluate(left)
        f_middle = evaluate(middle)
        f_right = evaluate(right)
        whole = (
            (right - left)
            * (f_left + 4.0 * f_middle + f_right)
            / 6.0
        )
        target = max(
            absolute_tolerance / initial_panels,
            relative_tolerance * abs(whole),
        )
        panel_results.append(
            recurse(
                left,
                right,
                f_left,
                f_middle,
                f_right,
                whole,
                target,
                maximum_depth,
            )
        )
    value = math.fsum(panel_results)
    return value, {
        "function_evaluations": evaluations,
        "maximum_depth_used": deepest,
        "initial_equal_root_altitude_panels": initial_panels,
        "requested_relative_tolerance": relative_tolerance,
        "requested_absolute_tolerance": absolute_tolerance,
    }


def continuous_slant_optical_depth(
    *,
    earth_radius_km: float,
    scale_height_km: float,
    top_altitude_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
    relative_tolerance: float,
    absolute_tolerance: float,
    initial_panels: int,
    maximum_depth: int,
) -> tuple[float, dict[str, int | float]]:
    integrand = _squared_altitude_integrand(
        earth_radius_km=earth_radius_km,
        scale_height_km=scale_height_km,
        top_altitude_km=top_altitude_km,
        target_true_altitude_deg=target_true_altitude_deg,
        vertical_optical_depth=vertical_optical_depth,
    )
    return _adaptive_simpson(
        integrand,
        0.0,
        math.sqrt(top_altitude_km),
        relative_tolerance=relative_tolerance,
        absolute_tolerance=absolute_tolerance,
        initial_panels=initial_panels,
        maximum_depth=maximum_depth,
    )


def shell_slant_optical_depth(
    levels_descending: list[float],
    *,
    earth_radius_km: float,
    scale_height_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
) -> float:
    layer_depths = layer_optical_depths(
        levels_descending,
        scale_height_km=scale_height_km,
        vertical_optical_depth=vertical_optical_depth,
    )
    impact_parameter = earth_radius_km * math.cos(
        math.radians(target_true_altitude_deg)
    )
    terms: list[float] = []
    for high, low, layer_depth in zip(
        levels_descending,
        levels_descending[1:],
        layer_depths[1:],
    ):
        high_radius = earth_radius_km + high
        low_radius = earth_radius_km + low
        high_path = math.sqrt(
            (high_radius - impact_parameter)
            * (high_radius + impact_parameter)
        )
        low_path = math.sqrt(
            max(
                0.0,
                (low_radius - impact_parameter)
                * (low_radius + impact_parameter),
            )
        )
        path_length = high_path - low_path
        terms.append(layer_depth * path_length / (high - low))
    result = math.fsum(terms)
    if not math.isfinite(result) or result <= 0.0:
        raise VisibilityLabError("shell-path optical depth is invalid")
    return result


def midpoint_chapman_surface_slant_optical_depth(
    levels_descending: list[float],
    *,
    earth_radius_km: float,
    scale_height_km: float,
    target_true_altitude_deg: float,
    vertical_optical_depth: float,
) -> float:
    """Reconstruct libRadtran's surface direct-beam Chapman application.

    cdisort evaluates the Chapman optical depth at the midpoint of the
    surface-adjacent layer, derives an effective Chapman factor there, and
    applies that factor to the full vertical optical depth at the surface.
    This intentionally differs from summing complete layer shells along a ray
    whose observer is at the surface.
    """
    layer_depths = layer_optical_depths(
        levels_descending,
        scale_height_km=scale_height_km,
        vertical_optical_depth=vertical_optical_depth,
    )
    bottom_high = levels_descending[-2]
    bottom_low = levels_descending[-1]
    observer_altitude = bottom_low + (bottom_high - bottom_low) / 2.0
    observer_radius = earth_radius_km + observer_altitude
    impact_parameter = observer_radius * math.cos(
        math.radians(target_true_altitude_deg)
    )
    chapman_terms: list[float] = []
    for index, (high, low, layer_depth) in enumerate(
        zip(
            levels_descending,
            levels_descending[1:],
            layer_depths[1:],
        )
    ):
        if high <= observer_altitude:
            continue
        actual_low = (
            observer_altitude
            if index == len(levels_descending) - 2
            else low
        )
        high_radius = earth_radius_km + high
        low_radius = earth_radius_km + actual_low
        high_path = math.sqrt(
            (high_radius - impact_parameter)
            * (high_radius + impact_parameter)
        )
        low_path = math.sqrt(
            max(
                0.0,
                (low_radius - impact_parameter)
                * (low_radius + impact_parameter),
            )
        )
        chapman_terms.append(
            layer_depth * (high_path - low_path) / (high - low)
        )
    chapman_tau_to_midpoint = math.fsum(chapman_terms)
    vertical_tau_to_midpoint = (
        math.fsum(layer_depths[1:-1]) + 0.5 * layer_depths[-1]
    )
    result = (
        vertical_optical_depth
        * chapman_tau_to_midpoint
        / vertical_tau_to_midpoint
    )
    if not math.isfinite(result) or result <= 0.0:
        raise VisibilityLabError(
            "midpoint-Chapman surface optical depth is invalid"
        )
    return result


def _parse_output(
    path: Path,
    case: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        line.split()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 1 or len(rows[0]) != 3:
        raise VisibilityLabError("direct output must contain lambda/edir/uavgdir")
    try:
        wavelength, edir, uavgdir = [float(value) for value in rows[0]]
    except ValueError as exc:
        raise VisibilityLabError("direct output contains nonnumeric data") from exc
    expected_wavelength = float(
        spec["controlled_exponential_atmospheres"]["wavelength_nm"]
    )
    if (
        wavelength != expected_wavelength
        or not math.isfinite(edir)
        or not math.isfinite(uavgdir)
        or edir < 0.0
        or uavgdir <= 0.0
    ):
        raise VisibilityLabError("direct output values are invalid")

    altitude = float(case["target_true_altitude_deg"])
    actinic_transmission = 4.0 * math.pi * uavgdir
    projected_transmission: float | None = None
    if altitude > 0.0:
        projected_transmission = edir / math.sin(math.radians(altitude))
        if (
            not math.isfinite(projected_transmission)
            or projected_transmission <= 0.0
        ):
            raise VisibilityLabError("projected direct transmission is invalid")
        selected = projected_transmission
        selected_channel = "edir_over_sin_true_altitude"
    else:
        selected = actinic_transmission
        selected_channel = "four_pi_uavgdir_pure_absorption_diagnostic"
    if not 0.0 < selected <= 1.0 or not 0.0 < actinic_transmission <= 1.0:
        raise VisibilityLabError("direct transmission is outside (0, 1]")
    return {
        "wavelength_nm": wavelength,
        "edir_over_e0_horizontal": edir,
        "uavgdir_over_e0_mean_intensity": uavgdir,
        "edir_projected_transmission": projected_transmission,
        "four_pi_uavgdir_transmission": actinic_transmission,
        "selected_transmission": selected,
        "selected_channel": selected_channel,
        "selected_slant_optical_depth": -math.log(selected),
        "selected_extinction_magnitude": -2.5 * math.log10(selected),
    }


def _recursive_file_receipts(
    root: Path,
    *,
    exclude: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise VisibilityLabError(f"artifact contains a symlink: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in exclude:
                receipts.append(base_lab.file_receipt(path, relative_to=root))
    return receipts


def _verify_receipts(root: Path, receipts: list[dict[str, Any]]) -> None:
    expected = {receipt["path"] for receipt in receipts}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise VisibilityLabError("artifact file inventory is incomplete")
    for receipt in receipts:
        path = root / receipt["path"]
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != receipt["bytes"]
            or base_lab.sha256_file(path) != receipt["sha256"]
        ):
            raise VisibilityLabError(f"artifact file receipt mismatch: {path}")


def _run_uvspec(
    *,
    uvspec: Path,
    data_root: Path,
    run_dir: Path,
    input_text: str,
    atmosphere_bytes: bytes,
    molecular_tau_bytes: bytes,
) -> None:
    if not run_dir.is_dir() or any(run_dir.iterdir()):
        raise VisibilityLabError("uvspec run directory must exist and be empty")
    (run_dir / "input.inp").write_text(input_text, encoding="utf-8")
    (run_dir / "atmosphere.dat").write_bytes(atmosphere_bytes)
    (run_dir / "molecular_tau.dat").write_bytes(molecular_tau_bytes)
    data_link = run_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    try:
        syntax = subprocess.run(
            [str(uvspec), "-c"],
            cwd=run_dir,
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        (run_dir / "syntax.stdout.txt").write_text(
            syntax.stdout,
            encoding="utf-8",
        )
        (run_dir / "syntax.stderr.txt").write_text(
            syntax.stderr,
            encoding="utf-8",
        )
        if syntax.returncode != 0:
            raise VisibilityLabError(
                f"uvspec syntax check failed; preserved at {run_dir}"
            )
        completed = subprocess.run(
            [str(uvspec)],
            cwd=run_dir,
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        (run_dir / "stdout.txt").write_text(
            completed.stdout,
            encoding="utf-8",
        )
        (run_dir / "stderr.txt").write_text(
            completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise VisibilityLabError(f"uvspec failed; preserved at {run_dir}")
    finally:
        if data_link.is_symlink():
            data_link.unlink()
    actual = {path.name for path in run_dir.iterdir()}
    expected = CASE_FILES - {"result.json"}
    if actual != expected:
        raise VisibilityLabError(
            f"uvspec file inventory mismatch at {run_dir}: "
            f"expected {sorted(expected)}, found {sorted(actual)}"
        )


def _generation_fingerprint(generation_identity: dict[str, Any]) -> str:
    return base_lab.sha256_bytes(base_lab.canonical_json_bytes(generation_identity))


def _resume_case(
    case_dir: Path,
    *,
    expected_case: dict[str, Any],
    generation_fingerprint: str,
) -> dict[str, Any] | None:
    result_path = case_dir / "result.json"
    if not result_path.is_file() or result_path.is_symlink():
        return None
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != CASE_SCHEMA
        or payload.get("case") != expected_case
        or payload.get("generation_fingerprint") != generation_fingerprint
        or set(path.name for path in case_dir.iterdir()) != CASE_FILES
    ):
        return None
    receipts = payload.get("files")
    if not isinstance(receipts, list):
        return None
    try:
        _verify_receipts(
            case_dir,
            [
                *receipts,
                base_lab.file_receipt(result_path, relative_to=case_dir),
            ],
        )
    except VisibilityLabError:
        return None
    return payload


def _comparison(
    *,
    parsed: dict[str, Any],
    shell_tau: float,
    midpoint_tau: float,
    continuous_tau: float,
    case: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    selected_tau = float(parsed["selected_slant_optical_depth"])
    vertical_tau = float(
        spec["controlled_exponential_atmospheres"]["vertical_optical_depth"]
    )
    shell_vs_continuous = abs(shell_tau - continuous_tau) / continuous_tau
    midpoint_vs_shell = abs(midpoint_tau - shell_tau) / shell_tau
    midpoint_vs_continuous = (
        abs(midpoint_tau - continuous_tau) / continuous_tau
    )
    extraction_relative: float | None = None
    projected = parsed["edir_projected_transmission"]
    if projected is not None:
        extraction_relative = (
            abs(float(projected) - float(parsed["four_pi_uavgdir_transmission"]))
            / float(projected)
        )
    altitude = float(case["target_true_altitude_deg"])
    plane_parallel_tau = (
        vertical_tau / math.sin(math.radians(altitude))
        if altitude > 0.0
        else None
    )
    plane_parallel_relative = (
        abs(plane_parallel_tau - continuous_tau) / continuous_tau
        if plane_parallel_tau is not None
        else None
    )
    result = {
        "libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs": abs(
            selected_tau - midpoint_tau
        ),
        "positive_altitude_extraction_relative_difference": extraction_relative,
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
            plane_parallel_relative
        ),
        "vertical_control_slant_optical_depth_abs_difference": (
            abs(selected_tau - vertical_tau)
            if case["domain_role"] == "vertical_control"
            else None
        ),
    }
    acceptance = spec["acceptance"]
    admission_enforced = case["domain_role"] in {
        "admitted_domain",
        "vertical_control",
    }
    if (
        admission_enforced
        and result[
            "libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs"
        ]
        > acceptance[
            "admitted_libRadtran_vs_midpoint_chapman_reconstruction_slant_optical_depth_abs_tolerance"
        ]
    ):
        raise VisibilityLabError(
            "libRadtran differs from its midpoint-Chapman reconstruction"
        )
    if (
        admission_enforced
        and extraction_relative is not None
        and extraction_relative
        > acceptance["admitted_positive_altitude_extraction_relative_tolerance"]
    ):
        raise VisibilityLabError("direct extraction channels disagree")
    if (
        case["grid_id"] == "near_horizon_piecewise_refined_v1"
        and case["domain_role"] == "admitted_domain"
        and midpoint_vs_continuous
        > acceptance[
            "refined_midpoint_vs_continuous_admitted_relative_slant_optical_depth_tolerance"
        ]
    ):
        raise VisibilityLabError(
            "refined grid exceeds the continuous-atmosphere admission tolerance"
        )
    vertical_difference = result[
        "vertical_control_slant_optical_depth_abs_difference"
    ]
    if (
        vertical_difference is not None
        and vertical_difference
        > acceptance["vertical_control_slant_optical_depth_abs_tolerance"]
    ):
        raise VisibilityLabError("vertical optical-depth control failed")
    return result


def _build_case(
    case: dict[str, Any],
    *,
    levels_descending: list[float],
    spec: dict[str, Any],
    generation_fingerprint: str,
    uvspec: Path,
    data_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    final_dir = output_root / case["case_id"]
    resumed = _resume_case(
        final_dir,
        expected_case=case,
        generation_fingerprint=generation_fingerprint,
    )
    if resumed is not None:
        return resumed
    if final_dir.exists():
        raise VisibilityLabError(f"partial or stale case directory exists: {final_dir}")

    controlled = spec["controlled_exponential_atmospheres"]
    boundary = spec["scientific_boundary"]
    oracle = spec["independent_oracle"]
    atmosphere_bytes = render_atmosphere(levels_descending)
    molecular_tau_bytes = render_molecular_tau(
        levels_descending,
        scale_height_km=float(case["scale_height_km"]),
        vertical_optical_depth=float(controlled["vertical_optical_depth"]),
    )
    input_text = render_input(case, spec)
    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{case['case_id']}.",
            dir=output_root,
        )
    )
    try:
        _run_uvspec(
            uvspec=uvspec,
            data_root=data_root,
            run_dir=temp_dir,
            input_text=input_text,
            atmosphere_bytes=atmosphere_bytes,
            molecular_tau_bytes=molecular_tau_bytes,
        )
        parsed = _parse_output(temp_dir / "stdout.txt", case, spec)
        shell_tau = shell_slant_optical_depth(
            levels_descending,
            earth_radius_km=float(boundary["earth_radius_km"]),
            scale_height_km=float(case["scale_height_km"]),
            target_true_altitude_deg=float(case["target_true_altitude_deg"]),
            vertical_optical_depth=float(controlled["vertical_optical_depth"]),
        )
        midpoint_tau = midpoint_chapman_surface_slant_optical_depth(
            levels_descending,
            earth_radius_km=float(boundary["earth_radius_km"]),
            scale_height_km=float(case["scale_height_km"]),
            target_true_altitude_deg=float(case["target_true_altitude_deg"]),
            vertical_optical_depth=float(controlled["vertical_optical_depth"]),
        )
        continuous_tau, convergence = continuous_slant_optical_depth(
            earth_radius_km=float(boundary["earth_radius_km"]),
            scale_height_km=float(case["scale_height_km"]),
            top_altitude_km=float(boundary["top_altitude_km"]),
            target_true_altitude_deg=float(case["target_true_altitude_deg"]),
            vertical_optical_depth=float(controlled["vertical_optical_depth"]),
            relative_tolerance=float(oracle["builder_relative_tolerance"]),
            absolute_tolerance=float(oracle["builder_absolute_tolerance"]),
            initial_panels=int(
                oracle["builder_initial_equal_root_altitude_panels"]
            ),
            maximum_depth=int(oracle["maximum_recursion_depth"]),
        )
        comparison = _comparison(
            parsed=parsed,
            shell_tau=shell_tau,
            midpoint_tau=midpoint_tau,
            continuous_tau=continuous_tau,
            case=case,
            spec=spec,
        )
        files = _recursive_file_receipts(temp_dir)
        result = {
            "schema": CASE_SCHEMA,
            "artifact_status": ARTIFACT_STATUS,
            "case": case,
            "generation_fingerprint": generation_fingerprint,
            "layer_count": len(levels_descending) - 1,
            "result": parsed,
            "oracles": {
                "same_layer_shell_slant_optical_depth": shell_tau,
                "libRadtran_midpoint_chapman_reconstructed_slant_optical_depth": (
                    midpoint_tau
                ),
                "continuous_exponential_slant_optical_depth": continuous_tau,
                "continuous_exponential_airmass": (
                    continuous_tau / float(controlled["vertical_optical_depth"])
                ),
                "adaptive_simpson_convergence": convergence,
            },
            "comparison": comparison,
            "files": files,
        }
        (temp_dir / "result.json").write_bytes(
            base_lab.canonical_json_bytes(result)
        )
        if set(path.name for path in temp_dir.iterdir()) != CASE_FILES:
            raise VisibilityLabError("completed case file inventory is invalid")
        temp_dir.rename(final_dir)
        return result
    except Exception as exc:
        raise VisibilityLabError(
            f"direct-geometry case failed; preserved at {temp_dir}"
        ) from exc


def _verify_libradtran_sources(
    spec: dict[str, Any],
    libradtran_root: Path,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for expected in spec["source"]["governing_files"]:
        path = libradtran_root / expected["path"]
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != expected["bytes"]
            or base_lab.sha256_file(path) != expected["sha256"]
        ):
            raise VisibilityLabError(
                f"governing libRadtran source identity mismatch: {path}"
            )
        receipts.append(base_lab.file_receipt(path, relative_to=libradtran_root))
    return receipts


def _parse_afgl_levels(path: Path) -> list[float]:
    levels: list[float] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        try:
            level = float(fields[0])
        except (IndexError, ValueError) as exc:
            raise VisibilityLabError(
                f"invalid AFGL level on line {line_number}"
            ) from exc
        if not math.isfinite(level):
            raise VisibilityLabError("AFGL level is non-finite")
        levels.append(level)
    _strictly_decreasing(levels, "AFGL level")
    return levels


def _receipt_matches(path: Path, receipt: dict[str, Any]) -> bool:
    return (
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_size == receipt.get("bytes")
        and base_lab.sha256_file(path) == receipt.get("sha256")
    )


def _repeat_receipt(
    output_root: Path,
    original_case_id: str,
    repeat_case_id: str,
) -> dict[str, Any]:
    compared_files = (
        "atmosphere.dat",
        "input.inp",
        "molecular_tau.dat",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    )
    differences: list[str] = []
    receipts: list[dict[str, Any]] = []
    for filename in compared_files:
        original = output_root / original_case_id / filename
        repeated = output_root / repeat_case_id / filename
        if original.read_bytes() != repeated.read_bytes():
            differences.append(filename)
        receipts.append(
            {
                "path": (
                    f"{original_case_id}/{filename}"
                    f" == {repeat_case_id}/{filename}"
                ),
                "sha256": base_lab.sha256_file(original),
            }
        )
    if differences:
        raise VisibilityLabError(
            "fixed-input direct repeat differs: " + ", ".join(differences)
        )
    return {
        "byte_identical": True,
        "original_case_id": original_case_id,
        "repeat_case_id": repeat_case_id,
        "compared_files": receipts,
    }


def build_probe(
    spec_path: Path,
    *,
    source_archive: Path,
    libradtran_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    if not isinstance(spec, dict):
        raise VisibilityLabError("direct-geometry specification must be an object")
    validate_spec(spec)

    base_paths: dict[str, Path] = {}
    for lab_name, declaration in spec["base_labs"].items():
        for role in ("spec", "builder", "validator"):
            base_paths[f"{lab_name}_{role}"] = _verify_declared_repo_file(
                declaration,
                label=role,
            )
    checkpoint1_spec = json.loads(
        base_paths["checkpoint1_spec"].read_text(encoding="utf-8")
    )
    base_lab.validate_spec(checkpoint1_spec)

    output_root = output_root.resolve()
    if output_root.is_symlink():
        raise VisibilityLabError("output root must not be a symlink")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "artifact-manifest.json"
    if manifest_path.exists():
        raise VisibilityLabError(
            f"artifact manifest already exists; choose a new output root: {manifest_path}"
        )

    cases = expand_cases(spec)
    repeated = repeat_case(spec)
    all_cases = [*cases, repeated]
    allowed_entries = {case["case_id"] for case in all_cases}
    unexpected = sorted(
        entry.name for entry in output_root.iterdir()
        if entry.name not in allowed_entries
    )
    if unexpected:
        raise VisibilityLabError(
            "output root contains unowned or partial entries: "
            + ", ".join(unexpected)
        )

    tooling_paths = {
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH.resolve(),
        **base_paths,
    }
    for role, path in tooling_paths.items():
        if not path.is_file() or path.is_symlink():
            raise VisibilityLabError(f"required tooling file is missing: {role}")
    tooling = {
        role: base_lab.file_receipt(path, relative_to=REPO_ROOT)
        for role, path in tooling_paths.items()
    }
    specifications = {
        "direct_geometry_probe": base_lab.file_receipt(
            spec_path,
            relative_to=REPO_ROOT,
        ),
        "checkpoint1_lab": tooling["checkpoint1_spec"],
        "elevated_site_checkpoint": tooling["elevated_site_checkpoint_spec"],
    }

    libradtran_root = libradtran_root.resolve()
    generator = base_lab.verify_generator(
        checkpoint1_spec,
        source_archive=source_archive,
        libradtran_root=libradtran_root,
    )
    if generator["uvspec_sha256"] != spec["source"]["uvspec_sha256"]:
        raise VisibilityLabError("uvspec executable identity changed")
    governing_sources = _verify_libradtran_sources(spec, libradtran_root)
    source_grid = vertical_grids(spec)["afglus_source_levels_v1"]
    actual_afgl_levels = _parse_afgl_levels(
        libradtran_root / "data" / "atmmod" / "afglus.dat"
    )
    if actual_afgl_levels != source_grid:
        raise VisibilityLabError("source-grid control does not match afglus.dat")

    environment = base_lab.environment_receipt()
    bound_generator = {
        **generator,
        "governing_source_files": governing_sources,
        "source_grid_control": {
            "path": "data/atmmod/afglus.dat",
            "level_count": len(actual_afgl_levels),
            "levels_km_descending": actual_afgl_levels,
        },
    }
    generation_identity = {
        "tooling": tooling,
        "specifications": specifications,
        "generator": bound_generator,
        "environment": environment,
        "runtime_boundary": spec["runtime_boundary"],
    }
    generation_fingerprint = _generation_fingerprint(generation_identity)
    grids = vertical_grids(spec)
    uvspec = libradtran_root / "bin" / "uvspec"
    data_root = libradtran_root / "data"

    results = [
        _build_case(
            case,
            levels_descending=grids[case["grid_id"]],
            spec=spec,
            generation_fingerprint=generation_fingerprint,
            uvspec=uvspec,
            data_root=data_root,
            output_root=output_root,
        )
        for case in all_cases
    ]

    repeat_receipt = _repeat_receipt(
        output_root,
        repeated["repeat_of"],
        repeated["case_id"],
    )
    nonrepeat_results = [
        result for result in results
        if "repeat_of" not in result["case"]
    ]
    refined_admitted = [
        result
        for result in nonrepeat_results
        if result["case"]["grid_id"] == "near_horizon_piecewise_refined_v1"
        and result["case"]["domain_role"] == "admitted_domain"
    ]
    source_admitted = [
        result
        for result in nonrepeat_results
        if result["case"]["grid_id"] == "afglus_source_levels_v1"
        and result["case"]["domain_role"] == "admitted_domain"
    ]
    diagnostics = [
        result
        for result in nonrepeat_results
        if result["case"]["domain_role"] == "diagnostic_only"
    ]
    admission_controls = [
        result
        for result in nonrepeat_results
        if result["case"]["domain_role"]
        in {"admitted_domain", "vertical_control"}
    ]

    def maximum(results_subset: list[dict[str, Any]], field: str) -> float:
        return max(float(result["comparison"][field]) for result in results_subset)

    summary = {
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

    if spec_path.read_bytes() != spec_bytes:
        raise VisibilityLabError("direct-geometry specification changed during build")
    for role, path in tooling_paths.items():
        if not _receipt_matches(path, tooling[role]):
            raise VisibilityLabError(f"{role} changed during generation")
    if not _receipt_matches(
        source_archive.resolve(),
        generator["source_archive"],
    ):
        raise VisibilityLabError("libRadtran source archive changed during build")
    if base_lab.sha256_file(uvspec) != generator["uvspec_sha256"]:
        raise VisibilityLabError("uvspec executable changed during build")
    _verify_libradtran_sources(spec, libradtran_root)

    case_summaries = [
        {
            "case": result["case"],
            "layer_count": result["layer_count"],
            "result": result["result"],
            "oracles": {
                key: value
                for key, value in result["oracles"].items()
                if key != "adaptive_simpson_convergence"
            },
            "comparison": result["comparison"],
        }
        for result in results
    ]
    file_inventory = _recursive_file_receipts(output_root)
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_status": ARTIFACT_STATUS,
        "spec_id": spec["spec_id"],
        "model_id": spec["scientific_boundary"]["model_id"],
        "tooling": tooling,
        "specifications": specifications,
        "generator": bound_generator,
        "environment": environment,
        "generation_identity": generation_identity,
        "generation_fingerprint": generation_fingerprint,
        "runtime_boundary": spec["runtime_boundary"],
        "grid_level_counts": {
            grid_id: len(levels)
            for grid_id, levels in grids.items()
        },
        "case_count": len(results),
        "nonrepeat_case_count": len(nonrepeat_results),
        "uvspec_run_count": len(results),
        "cases": case_summaries,
        "summary": summary,
        "fixed_input_repeat": repeat_receipt,
        "files": file_inventory,
    }
    manifest_path.write_bytes(base_lab.canonical_json_bytes(manifest))
    return manifest


def inspect_spec(spec_path: Path) -> dict[str, Any]:
    spec = load_spec(spec_path)
    cases = expand_cases(spec)
    grids = vertical_grids(spec)
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "vertical_grid_level_counts": {
            grid_id: len(levels)
            for grid_id, levels in grids.items()
        },
        "controlled_scale_height_count": len(
            spec["controlled_exponential_atmospheres"]["scale_height_km"]
        ),
        "target_altitude_count": len(_target_altitudes(spec)),
        "nonrepeat_case_count": len(cases),
        "uvspec_run_count": len(cases) + 1,
        "exact_horizon_admitted": False,
        "runtime_data_pack_authorized": False,
        "frozen_predecessor_identity_count": 6,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or inspect the external Phase 1 direct-geometry probe."
        )
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_SPEC_PATH,
        help="Path to the versioned direct-geometry specification.",
    )
    parser.add_argument(
        "--inspect-spec",
        action="store_true",
        help="Validate and summarize the specification without running libRadtran.",
    )
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--libradtran-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    if not args.inspect_spec:
        missing = [
            name
            for name in ("source_archive", "libradtran_root", "output_root")
            if getattr(args, name) is None
        ]
        if missing:
            parser.error(
                "build mode requires " + ", ".join(f"--{name.replace('_', '-')}" for name in missing)
            )
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.inspect_spec:
            payload = inspect_spec(args.spec)
        else:
            payload = build_probe(
                args.spec,
                source_archive=args.source_archive,
                libradtran_root=args.libradtran_root,
                output_root=args.output_root,
            )
    except (OSError, ValueError, VisibilityLabError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(base_lab.canonical_json_bytes(payload).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
