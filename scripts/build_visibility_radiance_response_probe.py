#!/usr/bin/env python3
"""Build the final Phase 1 radiance/response reference artifact.

This is an offline research tool.  It consumes caller-supplied, checksum-bound
libRadtran, REPTRAN, and CIE inputs; it never downloads and is not imported by
the installed Moira runtime.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import shutil
import statistics
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_radiance_response_probe_spec.json"
)
VALIDATOR_PATH = (
    REPO_ROOT / "scripts" / "validate_visibility_radiance_response_probe.py"
)
SPEC_SCHEMA = "moira.visibility-radiance-response-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-radiance-response-artifact/v1"
RUN_SCHEMA = "moira.visibility-radiance-response-run/v1"
MANIFEST_NAME = "artifact-manifest.json"
SUMMARY_NAME = "summary.json"
DATA_LINK_NAME = "libradtran_data"
NAMED_DIRECT_MANIFEST_SHA256 = (
    "b2bac79b30a3458fe17f8446b3da40f61deba1d7320b679724ebd60a65a539e8"
)
EXTERNAL_DATA_RECEIPTS_SHA256 = (
    "68f1817782e424ef617dab03ad985a3fbcb91fa2ed0239a8c2de1e8cb6855b59"
)


class VisibilityRadianceResponseError(ValueError):
    """Raised when a Phase 1 reference-build contract is violated."""


class BuildBudgetReached(RuntimeError):
    """Raised internally after a bounded resumable build reaches its budget."""


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def compact_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_receipt(path: Path, *, relative_to: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisibilityRadianceResponseError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VisibilityRadianceResponseError(f"{label} must be an array")
    return value


def _require_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisibilityRadianceResponseError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise VisibilityRadianceResponseError(f"{label} must be finite")
    return number


def _strictly_increasing(values: list[Any], label: str) -> list[float]:
    result = [_require_finite(value, label) for value in values]
    if not result or any(
        right <= left for left, right in zip(result, result[1:])
    ):
        raise VisibilityRadianceResponseError(
            f"{label} must be strictly increasing"
        )
    return result


def _verify_declared_file(
    declaration: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
) -> Path:
    relative = declaration.get("path")
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise VisibilityRadianceResponseError("declared file path is unsafe")
    path = root / relative
    if (
        not path.is_file()
        or path.stat().st_size != declaration.get("bytes")
        or sha256_file(path) != declaration.get("sha256")
    ):
        raise VisibilityRadianceResponseError(
            f"declared file identity differs: {relative}"
        )
    return path


def _decimal_vertical_grid(spec: dict[str, Any]) -> list[float]:
    declaration = _require_dict(spec.get("vertical_grid"), "vertical_grid")
    segments = _require_list(declaration.get("segments_km"), "segments_km")
    levels: list[Decimal] = []
    previous_stop: Decimal | None = None
    for index, item in enumerate(segments):
        segment = _require_dict(item, f"vertical segment {index}")
        if set(segment) != {"start", "stop", "step"}:
            raise VisibilityRadianceResponseError(
                "vertical-grid segment shape differs"
            )
        start = Decimal(str(segment["start"]))
        stop = Decimal(str(segment["stop"]))
        step = Decimal(str(segment["step"]))
        if (
            start < 0
            or stop > 120
            or start >= stop
            or step <= 0
            or (stop - start) % step != 0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise VisibilityRadianceResponseError(
                "vertical-grid segments are invalid"
            )
        count = int((stop - start) / step)
        for offset in range(count + 1):
            value = start + offset * step
            if not levels or levels[-1] != value:
                levels.append(value)
        previous_stop = stop
    result = [float(value) for value in levels]
    if (
        not result
        or result[0] != 0.0
        or result[-1] != 120.0
        or len(result) != declaration.get("expected_level_count")
    ):
        raise VisibilityRadianceResponseError("vertical-grid identity differs")
    return result


def _decimal_direct_altitude_grid(
    spec: dict[str, Any],
) -> tuple[list[float], list[float]]:
    direct = _require_dict(spec.get("direct_solver"), "direct solver")
    segments = _require_list(
        direct.get("training_grid_segments_deg"),
        "direct training-grid segments",
    )
    nodes: list[Decimal] = []
    previous_stop: Decimal | None = None
    for index, item in enumerate(segments):
        segment = _require_dict(item, f"direct grid segment {index}")
        if set(segment) != {"start", "stop", "step"}:
            raise VisibilityRadianceResponseError(
                "direct-grid segment shape differs"
            )
        start = Decimal(str(segment["start"]))
        stop = Decimal(str(segment["stop"]))
        step = Decimal(str(segment["step"]))
        if (
            start < Decimal("0.25")
            or stop > Decimal("45")
            or start >= stop
            or step <= 0
            or (stop - start) % step != 0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise VisibilityRadianceResponseError(
                "direct-grid segments are invalid"
            )
        count = int((stop - start) / step)
        for offset in range(count + 1):
            value = start + offset * step
            if not nodes or nodes[-1] != value:
                nodes.append(value)
        previous_stop = stop
    holdouts = [
        (left + right) / 2 for left, right in zip(nodes, nodes[1:])
    ]
    declared_nodes = [
        Decimal(str(value))
        for value in _strictly_increasing(
            direct.get("training_target_true_altitude_deg", []),
            "direct training altitudes",
        )
    ]
    declared_holdouts = [
        Decimal(str(value))
        for value in _strictly_increasing(
            direct.get("reserved_target_true_altitude_holdouts_deg", []),
            "direct holdout altitudes",
        )
    ]
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
        raise VisibilityRadianceResponseError(
            "direct training or holdout grid differs"
        )
    return (
        [float(value) for value in nodes],
        [float(value) for value in holdouts],
    )


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibilityRadianceResponseError(
            f"cannot read specification: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise VisibilityRadianceResponseError(
            "radiance-response specification must be an object"
        )
    validate_spec(payload)
    return payload


def validate_spec(spec: dict[str, Any]) -> None:
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("status") != "phase1_reference_build_not_engine_runtime"
        or spec.get("composite_model_id")
        != "clear_sky_naked_eye_point_source_v1"
    ):
        raise VisibilityRadianceResponseError(
            "specification identity differs"
        )
    runtime = _require_dict(spec.get("runtime_boundary"), "runtime boundary")
    expected_false = (
        "network_allowed",
        "automatic_download_allowed",
        "engine_dependency_allowed",
        "engine_runtime_invocation_allowed",
        "libRadtran_redistribution_allowed",
        "REPTRAN_redistribution_allowed",
        "engine_changes_authorized",
    )
    if any(runtime.get(field) is not False for field in expected_false):
        raise VisibilityRadianceResponseError("runtime boundary widened")
    if (
        runtime.get("generated_numerical_products_only") is not True
        or runtime.get("CIE_redistribution_in_data_pack_requires_notice")
        is not True
    ):
        raise VisibilityRadianceResponseError(
            "runtime data and notice boundary differs"
        )
    for declaration in _require_dict(
        spec.get("predecessors"),
        "predecessors",
    ).values():
        _verify_declared_file(_require_dict(declaration, "predecessor"))
    sources = _require_dict(spec.get("sources"), "sources")
    if sources.get("libRadtran", {}).get("archive_sha256") != (
        "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
    ):
        raise VisibilityRadianceResponseError("libRadtran source lock differs")
    if sources.get("REPTRAN_module", {}).get("archive_sha256") != (
        "55893c80bcc999651bac3bf014ee64aaf602653ba640eb5bebe787a5d8eacce7"
    ):
        raise VisibilityRadianceResponseError("REPTRAN source lock differs")
    if sources.get("CIE_photopic", {}).get("license") != "CC BY-SA 4.0":
        raise VisibilityRadianceResponseError("photopic license differs")
    if sources.get("CIE_scotopic", {}).get("license") != "CC BY-SA 4.0":
        raise VisibilityRadianceResponseError("scotopic license differs")
    deep = _require_dict(spec.get("deep_twilight_law"), "deep twilight law")
    if (
        deep.get("table_minimum_solar_center_altitude_deg") != -9.0
        or deep.get("solar_altitude_below_table")
        != "not_evaluable_for_modeled_twilight_background"
        or deep.get("monte_carlo_non_detection_is_zero") is not False
    ):
        raise VisibilityRadianceResponseError("deep-twilight law differs")
    solver = _require_dict(spec.get("radiance_solver"), "radiance solver")
    if (
        solver.get("spectral_importance_sampling") != "mc_spectral_is"
        or solver.get("spectral_importance_reference_wavelength_nm")
        != solver.get("normalization_wavelength_nm")
        or solver.get("spectral_importance_reference_wavelength_nm") != 531.0
        or solver.get("absolute_anchor_wavelength_nm") != 531.0
        or solver.get("spectral_importance_reference_selection")
        != (
            "training_diagnostic_balanced_photopic_scotopic_"
            "relative_standard_error"
        )
        or solver.get("spectral_importance_reference_source_receipts")
        != [
            {
                "path": "src/uvspec_lex.l",
                "bytes": 581415,
                "sha256": (
                    "174755190e50ecc3099c80a29cb71627c0a33a5e2009d1869c23140095658d89"
                ),
            },
            {
                "path": "src/solve_rte.c",
                "bytes": 304484,
                "sha256": (
                    "c90ed56c331758c71f89397c714cf1cab476dac9e5500ba1ebed0b60b6ad7475"
                ),
            },
        ]
    ):
        raise VisibilityRadianceResponseError(
            "spectral importance reference differs"
        )
    grid = _require_dict(spec.get("radiance_grid"), "radiance grid")
    solar = _require_dict(
        grid.get("solar_center_altitude_deg"),
        "solar axis",
    )
    target = _require_dict(
        grid.get("target_true_altitude_deg"),
        "target axis",
    )
    azimuth = _require_dict(
        grid.get("relative_solar_azimuth_deg"),
        "azimuth axis",
    )
    training_axes = [
        _strictly_increasing(solar.get("training_nodes", []), "solar nodes"),
        _strictly_increasing(target.get("training_nodes", []), "target nodes"),
        _strictly_increasing(
            azimuth.get("training_nodes", []),
            "azimuth nodes",
        ),
    ]
    holdout_axes = [
        _strictly_increasing(
            solar.get("reserved_holdouts", []),
            "solar holdouts",
        ),
        _strictly_increasing(
            target.get("reserved_holdouts", []),
            "target holdouts",
        ),
        _strictly_increasing(
            azimuth.get("reserved_holdouts", []),
            "azimuth holdouts",
        ),
    ]
    if (
        math.prod(len(axis) for axis in training_axes)
        != grid.get("training_point_count")
        or math.prod(len(axis) for axis in holdout_axes)
        != grid.get("monochromatic_holdout_point_count")
        or grid.get("interpolation_quantity")
        != "log10_response_luminance"
        or grid.get("interpolation_method") != "trilinear"
    ):
        raise VisibilityRadianceResponseError("radiance grid count differs")
    response_holdouts = _require_list(
        grid.get("response_holdouts"),
        "response holdouts",
    )
    expected_holdout_set = set(itertools.product(*holdout_axes))
    received_holdouts: set[tuple[float, float, float]] = set()
    for raw in response_holdouts:
        values = _require_list(raw, "response holdout")
        if len(values) != 3:
            raise VisibilityRadianceResponseError(
                "response holdout shape differs"
            )
        point = tuple(float(value) for value in values)
        if point not in expected_holdout_set:
            raise VisibilityRadianceResponseError(
                "response holdout is outside reserved axes"
            )
        received_holdouts.add(point)
    if (
        len(received_holdouts) != len(response_holdouts)
        or len(received_holdouts) != grid.get("response_holdout_point_count")
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
    ):
        raise VisibilityRadianceResponseError(
            "response holdout inventory differs"
        )
    monte_carlo = _require_dict(
        spec.get("adaptive_monte_carlo"),
        "adaptive Monte Carlo",
    )
    if (
        monte_carlo.get("anchor_minimum_seed_count") != 3
        or monte_carlo.get("anchor_maximum_seed_count") != 16
        or len(monte_carlo.get("training_random_seeds", [])) != 16
        or len(monte_carlo.get("holdout_random_seeds", [])) != 16
        or monte_carlo.get("spectral_shape_minimum_seed_count") != 3
        or monte_carlo.get("spectral_shape_maximum_seed_count") != 8
        or len(monte_carlo.get("spectral_shape_training_random_seeds", []))
        != 8
        or len(monte_carlo.get("spectral_shape_holdout_random_seeds", []))
        != 8
    ):
        raise VisibilityRadianceResponseError(
            "adaptive Monte Carlo inventory differs"
        )
    shape_photon_rows = _require_list(
        monte_carlo.get(
            "spectral_shape_photons_per_seed_by_solar_center_altitude"
        ),
        "spectral shape photon schedule",
    )
    shape_photon_schedule = {
        float(row["solar_center_altitude_deg"]): int(
            row["photons_per_seed"]
        )
        for raw in shape_photon_rows
        for row in [_require_dict(raw, "spectral shape photon row")]
    }
    expected_shape_photon_schedule = {
        -9.0: 100000,
        -7.5: 100000,
        -6.0: 30000,
        -4.5: 10000,
        -3.0: 10000,
        -1.5: 10000,
        0.0: 10000,
    }
    if (
        len(shape_photon_schedule) != len(shape_photon_rows)
        or shape_photon_schedule != expected_shape_photon_schedule
        or monte_carlo.get("spectral_shape_photon_adaptation_basis")
        != (
            "training_and_quarantined_exposed_response_holdout_"
            "zero_normalization_only"
        )
    ):
        raise VisibilityRadianceResponseError(
            "spectral shape photon schedule differs"
        )
    direct = _require_dict(spec.get("direct_solver"), "direct solver")
    _decimal_direct_altitude_grid(spec)
    if (
        direct.get("spectral_bin_count") != 400
        or direct.get("spectral_bin_width_nm") != 1.0
        or direct.get("aerosol_scattering_override")
        != "aerosol_modify ssa set 0"
    ):
        raise VisibilityRadianceResponseError("direct-solver contract differs")
    _decimal_vertical_grid(spec)
    acceptance = _require_dict(spec.get("acceptance"), "acceptance")
    if (
        acceptance.get("thresholds_may_not_change_after_holdout_execution")
        is not True
        or acceptance.get(
            "monochromatic_reference_surface_shipped_in_data_pack"
        )
        is not False
        or acceptance.get(
            "monochromatic_reference_surface_used_by_runtime_interpolation"
        )
        is not False
        or acceptance.get("monochromatic_reference_role")
        != (
            "reported_intermediate_diagnostic_not_artifact_"
            "admission_gate"
        )
    ):
        raise VisibilityRadianceResponseError(
            "acceptance or diagnostic-role contract differs"
        )


def inspect_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(path)
    grid = spec["radiance_grid"]
    return {
        "spec_id": spec["spec_id"],
        "training_point_count": grid["training_point_count"],
        "monochromatic_holdout_point_count": grid[
            "monochromatic_holdout_point_count"
        ],
        "response_holdout_point_count": grid[
            "response_holdout_point_count"
        ],
        "direct_run_count": len(
            spec["direct_solver"]["training_target_true_altitude_deg"]
        )
        + len(
            spec["direct_solver"][
                "reserved_target_true_altitude_holdouts_deg"
            ]
        ),
        "minimum_run_count": (
            (
                grid["training_point_count"]
                + grid["monochromatic_holdout_point_count"]
            )
            * spec["adaptive_monte_carlo"]["anchor_minimum_seed_count"]
            + (
                grid["training_point_count"]
                + grid["response_holdout_point_count"]
            )
            * spec["adaptive_monte_carlo"][
                "spectral_shape_minimum_seed_count"
            ]
            + len(
                spec["direct_solver"][
                    "training_target_true_altitude_deg"
                ]
            )
            + len(
                spec["direct_solver"][
                    "reserved_target_true_altitude_holdouts_deg"
                ]
            )
        ),
        "runtime_boundary": spec["runtime_boundary"],
        "deep_twilight_law": spec["deep_twilight_law"],
    }


def _format_number(value: float | int) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    number = float(value)
    if number == 0.0:
        return "0"
    return format(number, ".15g")


def _point_id(point: tuple[float, float, float]) -> str:
    solar, target, azimuth = point
    return (
        f"s{abs(solar):04.1f}_h{target:05.2f}_a{azimuth:05.1f}"
        .replace(".", "p")
    )


def radiance_points(
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


def _anchor_threshold(solar_altitude: float, spec: dict[str, Any]) -> float:
    declarations = spec["adaptive_monte_carlo"][
        "anchor_relative_standard_error_by_solar_altitude"
    ]
    matches = [
        float(item["maximum_relative_standard_error"])
        for item in declarations
        if float(item["minimum_solar_altitude_deg"])
        <= solar_altitude
        <= float(item["maximum_solar_altitude_deg"])
    ]
    if len(matches) != 1:
        raise VisibilityRadianceResponseError(
            f"anchor uncertainty band is ambiguous at {solar_altitude}"
        )
    return matches[0]


def _common_input_lines(
    spec: dict[str, Any],
    *,
    target_altitude_deg: float,
) -> list[str]:
    environment = spec["fixed_environment"]
    solver = spec["radiance_solver"]
    levels = _decimal_vertical_grid(spec)
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
        "atm_z_grid " + " ".join(_format_number(value) for value in levels),
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


def render_input(run: dict[str, Any], spec: dict[str, Any]) -> str:
    kind = run["kind"]
    if kind in {"anchor", "shape"}:
        lines = _common_input_lines(
            spec,
            target_altitude_deg=float(run["target_true_altitude_deg"]),
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
        else:
            lines[3:3] = [
                "wavelength 380 780",
                "mol_abs_param reptran fine",
            ]
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
        return "\n".join(lines) + "\n"
    if kind == "direct":
        lines = _common_input_lines(
            spec,
            target_altitude_deg=float(run["target_true_altitude_deg"]),
        )
        lines[3:3] = [
            "wavelength 380 780",
            "mol_abs_param reptran fine",
        ]
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
    raise VisibilityRadianceResponseError(f"unsupported run kind: {kind}")


def _parse_radiance_file(
    path: Path,
    *,
    expected_rows: int,
    expected_single_wavelength_nm: float | None = None,
) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    radiances: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 2:
            raise VisibilityRadianceResponseError(
                f"malformed MYSTIC radiance row: {line!r}"
            )
        try:
            wavelength = float(fields[0])
            radiance = float(fields[-1])
        except ValueError as exc:
            raise VisibilityRadianceResponseError(
                f"malformed MYSTIC radiance row: {line!r}"
            ) from exc
        if (
            not math.isfinite(wavelength)
            or not math.isfinite(radiance)
            or radiance < 0
        ):
            raise VisibilityRadianceResponseError(
                "MYSTIC radiance contains invalid values"
            )
        wavelengths.append(wavelength)
        radiances.append(radiance)
    if len(wavelengths) != expected_rows:
        raise VisibilityRadianceResponseError(
            f"MYSTIC radiance row count differs: {len(wavelengths)}"
        )
    if expected_rows == 1:
        if (
            expected_single_wavelength_nm is None
            or not math.isclose(
                wavelengths[0],
                expected_single_wavelength_nm,
                abs_tol=1e-6,
            )
        ):
            raise VisibilityRadianceResponseError(
                "anchor wavelength differs"
            )
    else:
        for index, wavelength in enumerate(wavelengths):
            expected = 380.0 + index * 0.05
            if not math.isclose(wavelength, expected, abs_tol=1.1e-4):
                raise VisibilityRadianceResponseError(
                    f"spectral wavelength differs at row {index}"
                )
    return wavelengths, radiances


def _load_cie_table(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) != 2:
                raise VisibilityRadianceResponseError(
                    f"malformed CIE row: {row!r}"
                )
            try:
                wavelength = int(row[0])
                response = float(row[1])
            except ValueError as exc:
                raise VisibilityRadianceResponseError(
                    f"malformed CIE row: {row!r}"
                ) from exc
            if wavelength in result or not 0.0 <= response <= 1.0:
                raise VisibilityRadianceResponseError(
                    "CIE response table is invalid"
                )
            result[wavelength] = response
    keys = sorted(result)
    if not keys or keys != list(range(keys[0], keys[-1] + 1)):
        raise VisibilityRadianceResponseError(
            "CIE wavelength grid is incomplete"
        )
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


def _trapezoid_response(
    wavelengths: list[float],
    radiances: list[float],
    table: dict[int, float],
) -> float:
    weighted = [
        radiance * _cie_value(table, wavelength)
        for wavelength, radiance in zip(wavelengths, radiances)
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


def parse_run(
    run: dict[str, Any],
    directory: Path,
    spec: dict[str, Any],
    cie_tables: dict[str, dict[int, float]],
) -> dict[str, Any]:
    kind = run["kind"]
    if kind == "anchor":
        _, radiances = _parse_radiance_file(
            directory / "mc.rad.spc",
            expected_rows=1,
            expected_single_wavelength_nm=spec["radiance_solver"][
                "absolute_anchor_wavelength_nm"
            ],
        )
        _, deviations = _parse_radiance_file(
            directory / "mc.rad.std.spc",
            expected_rows=1,
            expected_single_wavelength_nm=spec["radiance_solver"][
                "absolute_anchor_wavelength_nm"
            ],
        )
        radiance = radiances[0]
        deviation = deviations[0]
        if radiance <= 0 or deviation < 0:
            raise VisibilityRadianceResponseError(
                "anchor sample is zero or invalid"
            )
        return {
            "reference_radiance_mw_m2_nm_sr": radiance,
            "reported_standard_deviation_mw_m2_nm_sr": deviation,
            "reported_relative_standard_deviation": deviation / radiance,
        }
    if kind == "shape":
        wavelengths, radiances = _parse_radiance_file(
            directory / "mc.rad.spc",
            expected_rows=spec["radiance_solver"][
                "expected_spectral_row_count"
            ],
        )
        normalization_wavelength = float(
            spec["radiance_solver"]["normalization_wavelength_nm"]
        )
        normalization_index = round(
            (normalization_wavelength - 380.0) / 0.05
        )
        if not math.isclose(
            wavelengths[normalization_index],
            normalization_wavelength,
            abs_tol=1e-6,
        ):
            raise VisibilityRadianceResponseError(
                "spectral normalization row differs"
            )
        normalizer = radiances[normalization_index]
        if normalizer <= 0:
            raise VisibilityRadianceResponseError(
                "spectral normalization sample is zero"
            )
        result: dict[str, Any] = {
            "normalization_reference_radiance_mw_m2_nm_sr": normalizer,
        }
        for response_name, table in cie_tables.items():
            integral = _trapezoid_response(
                wavelengths,
                radiances,
                table,
            )
            if not math.isfinite(integral) or integral <= 0:
                raise VisibilityRadianceResponseError(
                    f"{response_name} response integral is invalid"
                )
            result[f"{response_name}_shape_nm"] = integral / normalizer
        return result
    if kind == "direct":
        wavelengths: list[float] = []
        horizontal: list[float] = []
        for line in (directory / "stdout.txt").read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != 2:
                raise VisibilityRadianceResponseError(
                    f"unexpected direct-output row: {line!r}"
                )
            try:
                wavelength, irradiance = map(float, fields)
            except ValueError as exc:
                raise VisibilityRadianceResponseError(
                    f"unexpected direct-output row: {line!r}"
                ) from exc
            wavelengths.append(wavelength)
            horizontal.append(irradiance)
        if len(wavelengths) != 8001:
            raise VisibilityRadianceResponseError(
                "direct spectrum row count differs"
            )
        for index, wavelength in enumerate(wavelengths):
            if not math.isclose(
                wavelength,
                380.0 + index * 0.05,
                abs_tol=1.1e-4,
            ):
                raise VisibilityRadianceResponseError(
                    f"direct wavelength differs at row {index}"
                )
        sine = math.sin(
            math.radians(float(run["target_true_altitude_deg"]))
        )
        direct = [value / sine for value in horizontal]
        if any(
            not math.isfinite(value)
            or value < 0.0
            or value > 1.0000001
            for value in direct
        ):
            raise VisibilityRadianceResponseError(
                "direct transmission is out of range"
            )
        points_per_bin = 20
        floor = float(spec["direct_solver"]["opaque_transmission_floor"])
        binned = [
            math.fsum(
                direct[index * points_per_bin : (index + 1) * points_per_bin]
            )
            / points_per_bin
            for index in range(spec["direct_solver"]["spectral_bin_count"])
        ]
        extinction = [
            -2.5 * math.log10(max(value, floor)) for value in binned
        ]
        return {
            "spectral_bin_start_nm": 380.0,
            "spectral_bin_width_nm": 1.0,
            "spectral_bin_count": len(extinction),
            "direct_transmission_1nm": binned,
            "extinction_magnitude_1nm": extinction,
        }
    raise VisibilityRadianceResponseError(f"unsupported run kind: {kind}")


def _kept_run_files(kind: str) -> set[str]:
    common = {
        "input.inp",
        "stdout.txt",
        "stderr.txt",
        "syntax.stdout.txt",
        "syntax.stderr.txt",
    }
    if kind in {"anchor", "shape"}:
        return common | {
            "mc.rad.spc",
            "mc.rad.std.spc",
            "randomseed",
        }
    return common


def _completed_run(
    final_dir: Path,
    run: dict[str, Any],
    expected_input: str | None = None,
) -> dict[str, Any] | None:
    result_path = final_dir / "result.json"
    if not result_path.is_file() or result_path.is_symlink():
        return None
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        payload.get("schema") != RUN_SCHEMA
        or payload.get("run") != run
        or result_path.read_bytes() != canonical_json_bytes(payload)
        or (
            expected_input is not None
            and (final_dir / "input.inp").read_bytes()
            != expected_input.encode("utf-8")
        )
    ):
        return None
    receipts = payload.get("files")
    if not isinstance(receipts, list):
        return None
    expected_names = _kept_run_files(run["kind"])
    received: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            return None
        name = receipt.get("path")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in received
            or name not in expected_names
        ):
            return None
        path = final_dir / name
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != receipt.get("bytes")
            or sha256_file(path) != receipt.get("sha256")
        ):
            return None
        received.add(name)
    actual = {
        path.name
        for path in final_dir.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if (
        received != expected_names
        or actual != expected_names | {"result.json"}
        or any(path.is_symlink() for path in final_dir.iterdir())
    ):
        return None
    return payload


@dataclass
class RunBuilder:
    uvspec: Path
    data_root: Path
    output_root: Path
    spec: dict[str, Any]
    cie_tables: dict[str, dict[int, float]]
    max_new_runs: int | None
    reuse_runs_root: Path | None = None
    new_run_count: int = 0
    reused_run_count: int = 0

    def run(self, declaration: dict[str, Any]) -> dict[str, Any]:
        runs_root = self.output_root / "runs"
        runs_root.mkdir(exist_ok=True)
        final_dir = runs_root / declaration["run_id"]
        expected_input = render_input(declaration, self.spec)
        if final_dir.exists():
            completed = _completed_run(
                final_dir,
                declaration,
                expected_input,
            )
            if completed is None:
                raise VisibilityRadianceResponseError(
                    f"partial or stale run directory exists: {final_dir}"
                )
            return completed
        if self.reuse_runs_root is not None:
            reusable_dir = self.reuse_runs_root / declaration["run_id"]
            reusable = _completed_run(
                reusable_dir,
                declaration,
                expected_input,
            )
            if reusable is not None:
                shutil.copytree(reusable_dir, final_dir)
                copied = _completed_run(
                    final_dir,
                    declaration,
                    expected_input,
                )
                if copied is None:
                    raise VisibilityRadianceResponseError(
                        f"copied run cache failed validation: {final_dir}"
                    )
                self.reused_run_count += 1
                return copied
        if (
            self.max_new_runs is not None
            and self.new_run_count >= self.max_new_runs
        ):
            raise BuildBudgetReached
        temp_dir = Path(
            tempfile.mkdtemp(
                prefix=f".{declaration['run_id']}.",
                dir=runs_root,
            )
        )
        try:
            (temp_dir / DATA_LINK_NAME).symlink_to(
                self.data_root,
                target_is_directory=True,
            )
            input_text = expected_input
            (temp_dir / "input.inp").write_text(
                input_text,
                encoding="utf-8",
                newline="\n",
            )
            syntax = subprocess.run(
                [str(self.uvspec), "-c"],
                cwd=temp_dir,
                input=input_text,
                capture_output=True,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            (temp_dir / "syntax.stdout.txt").write_text(
                syntax.stdout,
                encoding="utf-8",
                newline="\n",
            )
            (temp_dir / "syntax.stderr.txt").write_text(
                syntax.stderr,
                encoding="utf-8",
                newline="\n",
            )
            if (
                syntax.returncode != 0
                or "Error" in syntax.stderr
                or "Exiting" in syntax.stderr
            ):
                raise VisibilityRadianceResponseError(
                    f"uvspec syntax check failed: {temp_dir}"
                )
            completed = subprocess.run(
                [str(self.uvspec)],
                cwd=temp_dir,
                input=input_text,
                capture_output=True,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            (temp_dir / "stdout.txt").write_text(
                completed.stdout,
                encoding="utf-8",
                newline="\n",
            )
            (temp_dir / "stderr.txt").write_text(
                completed.stderr,
                encoding="utf-8",
                newline="\n",
            )
            if (
                completed.returncode != 0
                or "Error" in completed.stderr
                or "Exiting" in completed.stderr
            ):
                raise VisibilityRadianceResponseError(
                    f"uvspec run failed: {temp_dir}"
                )
            result = parse_run(
                declaration,
                temp_dir,
                self.spec,
                self.cie_tables,
            )
            kept = _kept_run_files(declaration["kind"])
            data_link = temp_dir / DATA_LINK_NAME
            if data_link.is_symlink():
                data_link.unlink()
            for path in list(temp_dir.iterdir()):
                if path.name not in kept:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
            receipts = [
                {
                    "path": name,
                    "bytes": (temp_dir / name).stat().st_size,
                    "sha256": sha256_file(temp_dir / name),
                }
                for name in sorted(kept)
            ]
            payload = {
                "schema": RUN_SCHEMA,
                "run": declaration,
                "result": result,
                "files": receipts,
            }
            (temp_dir / "result.json").write_bytes(
                canonical_json_bytes(payload)
            )
            temp_dir.replace(final_dir)
            self.new_run_count += 1
            return payload
        except Exception:
            raise


def _anchor_run(
    point: tuple[float, float, float],
    *,
    partition: str,
    seed_index: int,
    seed: int,
    spec: dict[str, Any],
) -> dict[str, Any]:
    solar, target, azimuth = point
    return {
        "run_id": (
            f"{partition}__{_point_id(point)}__anchor__r{seed_index + 1:02d}"
        ),
        "kind": "anchor",
        "partition": partition,
        "point_id": _point_id(point),
        "solar_center_altitude_deg": solar,
        "target_true_altitude_deg": target,
        "relative_solar_azimuth_deg": azimuth,
        "photon_count": spec["adaptive_monte_carlo"][
            "anchor_photons_per_seed"
        ],
        "random_seed": seed,
    }


def _shape_run(
    point: tuple[float, float, float],
    *,
    partition: str,
    seed_index: int,
    seed: int,
    spec: dict[str, Any],
) -> dict[str, Any]:
    solar, target, azimuth = point
    return {
        "run_id": (
            f"{partition}__{_point_id(point)}__shape__r{seed_index + 1:02d}"
        ),
        "kind": "shape",
        "partition": partition,
        "point_id": _point_id(point),
        "solar_center_altitude_deg": solar,
        "target_true_altitude_deg": target,
        "relative_solar_azimuth_deg": azimuth,
        "photon_count": _shape_photon_count(solar, spec),
        "random_seed": seed,
    }


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
        raise VisibilityRadianceResponseError(
            "spectral shape photon schedule is ambiguous"
        )
    return matches[0]


def _direct_run(
    target_altitude: float,
    *,
    partition: str,
) -> dict[str, Any]:
    return {
        "run_id": (
            f"direct__{partition}__h{target_altitude:05.2f}".replace(
                ".",
                "p",
            )
        ),
        "kind": "direct",
        "partition": partition,
        "target_true_altitude_deg": target_altitude,
    }


def _relative_standard_error(
    values: list[float],
    reported_deviations: list[float] | None = None,
) -> dict[str, float]:
    mean = statistics.fmean(values)
    if not math.isfinite(mean) or mean <= 0:
        raise VisibilityRadianceResponseError(
            "Monte Carlo aggregate mean is invalid"
        )
    between = (
        statistics.stdev(values) / math.sqrt(len(values)) / mean
        if len(values) >= 2
        else math.inf
    )
    reported = 0.0
    if reported_deviations is not None:
        reported = (
            math.sqrt(math.fsum(value * value for value in reported_deviations))
            / len(reported_deviations)
            / mean
        )
    return {
        "mean": mean,
        "between_seed_relative_standard_error": between,
        "reported_aggregate_relative_standard_error": reported,
        "governing_relative_standard_error": max(between, reported),
    }


def _build_anchor_aggregate(
    builder: RunBuilder,
    point: tuple[float, float, float],
    *,
    partition: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    monte_carlo = builder.spec["adaptive_monte_carlo"]
    seeds = monte_carlo[
        "training_random_seeds"
        if partition == "training"
        else "holdout_random_seeds"
    ]
    minimum = int(monte_carlo["anchor_minimum_seed_count"])
    maximum = int(monte_carlo["anchor_maximum_seed_count"])
    threshold = _anchor_threshold(point[0], builder.spec)
    payloads: list[dict[str, Any]] = []
    aggregate: dict[str, float] | None = None
    for index, seed in enumerate(seeds[:maximum]):
        payloads.append(
            builder.run(
                _anchor_run(
                    point,
                    partition=partition,
                    seed_index=index,
                    seed=seed,
                    spec=builder.spec,
                )
            )
        )
        if len(payloads) >= minimum:
            aggregate = _relative_standard_error(
                [
                    item["result"]["reference_radiance_mw_m2_nm_sr"]
                    for item in payloads
                ],
                [
                    item["result"][
                        "reported_standard_deviation_mw_m2_nm_sr"
                    ]
                    for item in payloads
                ],
            )
            if aggregate["governing_relative_standard_error"] <= threshold:
                break
    if (
        aggregate is None
        or aggregate["governing_relative_standard_error"] > threshold
    ):
        raise VisibilityRadianceResponseError(
            f"anchor convergence failed for {partition} {_point_id(point)}"
        )
    return (
        {
            "point_id": _point_id(point),
            "partition": partition,
            "solar_center_altitude_deg": point[0],
            "target_true_altitude_deg": point[1],
            "relative_solar_azimuth_deg": point[2],
            "seed_count": len(payloads),
            "photon_count": len(payloads)
            * monte_carlo["anchor_photons_per_seed"],
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
        },
        payloads,
    )


def _build_shape_aggregate(
    builder: RunBuilder,
    point: tuple[float, float, float],
    *,
    partition: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    monte_carlo = builder.spec["adaptive_monte_carlo"]
    seeds = monte_carlo[
        "spectral_shape_training_random_seeds"
        if partition == "training"
        else "spectral_shape_holdout_random_seeds"
    ]
    minimum = int(monte_carlo["spectral_shape_minimum_seed_count"])
    maximum = int(monte_carlo["spectral_shape_maximum_seed_count"])
    threshold = float(
        monte_carlo["maximum_response_shape_relative_standard_error"]
    )
    payloads: list[dict[str, Any]] = []
    aggregates: dict[str, dict[str, float]] | None = None
    for index, seed in enumerate(seeds[:maximum]):
        payloads.append(
            builder.run(
                _shape_run(
                    point,
                    partition=partition,
                    seed_index=index,
                    seed=seed,
                    spec=builder.spec,
                )
            )
        )
        if len(payloads) >= minimum:
            aggregates = {
                response: _relative_standard_error(
                    [
                        item["result"][f"{response}_shape_nm"]
                        for item in payloads
                    ]
                )
                for response in ("photopic", "scotopic")
            }
            if max(
                item["governing_relative_standard_error"]
                for item in aggregates.values()
            ) <= threshold:
                break
    if aggregates is None or max(
        item["governing_relative_standard_error"]
        for item in aggregates.values()
    ) > threshold:
        raise VisibilityRadianceResponseError(
            f"spectral-shape convergence failed for {partition} "
            f"{_point_id(point)}"
        )
    return (
        {
            "point_id": _point_id(point),
            "partition": partition,
            "solar_center_altitude_deg": point[0],
            "target_true_altitude_deg": point[1],
            "relative_solar_azimuth_deg": point[2],
            "seed_count": len(payloads),
            "photon_count": sum(
                item["run"]["photon_count"] for item in payloads
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
        },
        payloads,
    )


def _response_product(
    anchor: dict[str, Any],
    shape: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "point_id": anchor["point_id"],
        "partition": anchor["partition"],
        "solar_center_altitude_deg": anchor[
            "solar_center_altitude_deg"
        ],
        "target_true_altitude_deg": anchor["target_true_altitude_deg"],
        "relative_solar_azimuth_deg": anchor[
            "relative_solar_azimuth_deg"
        ],
    }
    for response, source_name in (
        ("photopic", "CIE_photopic"),
        ("scotopic", "CIE_scotopic"),
    ):
        efficacy = float(
            spec["sources"][source_name]["luminous_efficacy_lm_per_w"]
        )
        luminance = (
            anchor["mean_reference_radiance_mw_m2_nm_sr"]
            * shape[f"{response}_shape_nm"]
            * efficacy
            / 1000.0
        )
        uncertainty = math.hypot(
            anchor["governing_relative_standard_error"],
            shape[f"{response}_relative_standard_error"],
        )
        result[f"{response}_luminance_cd_m2"] = luminance
        result[f"{response}_relative_standard_error"] = uncertainty
    return result


def _bracket(nodes: list[float], value: float) -> tuple[float, float]:
    if value in nodes:
        return value, value
    for lower, upper in zip(nodes, nodes[1:]):
        if lower < value < upper:
            return lower, upper
    raise VisibilityRadianceResponseError(
        f"value lies outside interpolation grid: {value}"
    )


def _trilinear_log(
    table: dict[tuple[float, float, float], float],
    axes: tuple[list[float], list[float], list[float]],
    point: tuple[float, float, float],
) -> float:
    brackets = [
        _bracket(nodes, value) for nodes, value in zip(axes, point)
    ]
    choices = [
        [lower] if lower == upper else [lower, upper]
        for lower, upper in brackets
    ]
    result = 0.0
    for corner in itertools.product(*choices):
        weight = 1.0
        for coordinate, value, (lower, upper) in zip(
            corner,
            point,
            brackets,
        ):
            if lower != upper:
                fraction = (value - lower) / (upper - lower)
                weight *= fraction if coordinate == upper else 1.0 - fraction
        sample = table[tuple(float(value) for value in corner)]
        if sample <= 0:
            raise VisibilityRadianceResponseError(
                "log interpolation encountered a nonpositive value"
            )
        result += weight * math.log10(sample)
    return 10.0**result


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        raise VisibilityRadianceResponseError("empty error population")
    ordered = sorted(values)
    return ordered[math.floor((len(ordered) - 1) * fraction)]


def _error_summary(
    rows: list[dict[str, Any]],
    *,
    error_field: str,
) -> dict[str, Any]:
    errors = [float(row[error_field]) for row in rows]
    worst = max(rows, key=lambda row: float(row[error_field]))
    return {
        "sample_count": len(errors),
        "mean_error_mag": statistics.fmean(errors),
        "p95_error_mag": _quantile(errors, 0.95),
        "maximum_error_mag": max(errors),
        "worst_case": worst,
    }


def _direct_coordinate(target_altitude: float) -> float:
    return math.log10(target_altitude + 0.25)


def _linear_direct_extinction(
    table: dict[float, list[float]],
    target_altitude: float,
) -> list[float]:
    nodes = sorted(table)
    lower, upper = _bracket(nodes, target_altitude)
    if lower == upper:
        return table[lower]
    lower_x = _direct_coordinate(lower)
    upper_x = _direct_coordinate(upper)
    fraction = (
        _direct_coordinate(target_altitude) - lower_x
    ) / (upper_x - lower_x)
    return [
        left * (1.0 - fraction) + right * fraction
        for left, right in zip(table[lower], table[upper])
    ]


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def summarize(
    spec: dict[str, Any],
    anchors: list[dict[str, Any]],
    shapes: list[dict[str, Any]],
    direct_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_by_key = {
        (row["partition"], row["point_id"]): row for row in anchors
    }
    shape_by_key = {
        (row["partition"], row["point_id"]): row for row in shapes
    }
    response_products = [
        _response_product(
            anchor_by_key[key],
            shape,
            spec,
        )
        for key, shape in shape_by_key.items()
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
    anchor_training = {
        (
            row["solar_center_altitude_deg"],
            row["target_true_altitude_deg"],
            row["relative_solar_azimuth_deg"],
        ): row["mean_reference_radiance_mw_m2_nm_sr"]
        for row in anchors
        if row["partition"] == "training"
    }
    monochromatic_errors: list[dict[str, Any]] = []
    for row in anchors:
        if row["partition"] != "holdout":
            continue
        point = (
            row["solar_center_altitude_deg"],
            row["target_true_altitude_deg"],
            row["relative_solar_azimuth_deg"],
        )
        predicted = _trilinear_log(anchor_training, axes, point)
        truth = row["mean_reference_radiance_mw_m2_nm_sr"]
        monochromatic_errors.append(
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
    response_errors: dict[str, list[dict[str, Any]]] = {
        "photopic": [],
        "scotopic": [],
    }
    for response in response_errors:
        field = f"{response}_luminance_cd_m2"
        training = {
            (
                row["solar_center_altitude_deg"],
                row["target_true_altitude_deg"],
                row["relative_solar_azimuth_deg"],
            ): row[field]
            for row in response_products
            if row["partition"] == "training"
        }
        for row in response_products:
            if row["partition"] != "holdout":
                continue
            point = (
                row["solar_center_altitude_deg"],
                row["target_true_altitude_deg"],
                row["relative_solar_azimuth_deg"],
            )
            predicted = _trilinear_log(training, axes, point)
            truth = row[field]
            response_errors[response].append(
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
    direct_training = {
        float(payload["run"]["target_true_altitude_deg"]): payload["result"][
            "extinction_magnitude_1nm"
        ]
        for payload in direct_payloads
        if payload["run"]["partition"] == "training"
    }
    direct_errors: list[dict[str, Any]] = []
    direct_holdouts: list[dict[str, Any]] = []
    for payload in direct_payloads:
        if payload["run"]["partition"] != "holdout":
            continue
        altitude = float(payload["run"]["target_true_altitude_deg"])
        truth = payload["result"]["extinction_magnitude_1nm"]
        predicted = _linear_direct_extinction(direct_training, altitude)
        direct_holdouts.append(
            {
                "target_true_altitude_deg": altitude,
                "extinction_magnitude_1nm": truth,
            }
        )
        for index, (predicted_value, truth_value) in enumerate(
            zip(predicted, truth)
        ):
            direct_errors.append(
                {
                    "target_true_altitude_deg": altitude,
                    "spectral_bin_start_nm": 380.0 + index,
                    "predicted_extinction_magnitude": predicted_value,
                    "truth_extinction_magnitude": truth_value,
                    "error_mag": abs(predicted_value - truth_value),
                }
            )
    training_responses = sorted(
        (
            row
            for row in response_products
            if row["partition"] == "training"
        ),
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
    ]
    storage_values.extend(
        (
            "direct.extinction",
            value,
        )
        for altitude in sorted(direct_training)
        for value in direct_training[altitude]
    )
    float32_errors: list[float] = []
    quantized_errors: list[float] = []
    step = float(spec["acceptance"]["quantized_log10_step"])
    for label, value in storage_values:
        staged = _float32(value)
        if label.startswith("radiance."):
            if staged <= 0:
                raise VisibilityRadianceResponseError(
                    "float32 storage underflowed a radiance product"
                )
            float32_errors.append(2.5 * abs(math.log10(staged / value)))
            quantized = round(math.log10(value) / step) * step
            quantized_errors.append(
                2.5 * abs(quantized - math.log10(value))
            )
        else:
            float32_errors.append(abs(staged - value))
            quantized = round(value / (2.5 * step)) * (2.5 * step)
            quantized_errors.append(abs(quantized - value))
    error_summaries = {
        "monochromatic_reference": _error_summary(
            monochromatic_errors,
            error_field="error_mag",
        ),
        "photopic_response": _error_summary(
            response_errors["photopic"],
            error_field="error_mag",
        ),
        "scotopic_response": _error_summary(
            response_errors["scotopic"],
            error_field="error_mag",
        ),
        "direct_extinction_1nm": _error_summary(
            direct_errors,
            error_field="error_mag",
        ),
    }
    acceptance = spec["acceptance"]
    failures: list[str] = []
    monochromatic_diagnostic_passed = not (
        error_summaries["monochromatic_reference"]["maximum_error_mag"]
        > acceptance["monochromatic_holdout_maximum_error_mag"]
        or error_summaries["monochromatic_reference"]["p95_error_mag"]
        > acceptance["monochromatic_holdout_p95_error_mag"]
    )
    for response in ("photopic_response", "scotopic_response"):
        if (
            error_summaries[response]["maximum_error_mag"]
            > acceptance["response_holdout_maximum_error_mag"]
            or error_summaries[response]["p95_error_mag"]
            > acceptance["response_holdout_p95_error_mag"]
        ):
            failures.append(f"{response}_holdout_error")
    if (
        error_summaries["direct_extinction_1nm"]["maximum_error_mag"]
        > acceptance["direct_holdout_maximum_error_mag"]
        or error_summaries["direct_extinction_1nm"]["p95_error_mag"]
        > acceptance["direct_holdout_p95_error_mag"]
    ):
        failures.append("direct_holdout_error")
    if max(float32_errors) > acceptance[
        "float32_storage_maximum_error_mag"
    ]:
        failures.append("float32_storage_error")
    if max(quantized_errors) > acceptance[
        "quantized_storage_maximum_error_mag"
    ]:
        failures.append("quantized_storage_error")
    if failures:
        raise VisibilityRadianceResponseError(
            "artifact acceptance failed: " + ", ".join(failures)
        )
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
                "extinction_magnitude_1nm": direct_training[altitude],
            }
            for altitude in sorted(direct_training)
        ],
        "direct_holdout_table": direct_holdouts,
        "error_summaries": error_summaries,
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


def _verify_source_inputs(
    spec: dict[str, Any],
    *,
    source_archive: Path,
    reptran_archive: Path,
    libradtran_root: Path,
    data_root: Path,
    cie_root: Path,
    named_direct_artifact: Path,
) -> tuple[Path, dict[str, Any], dict[str, dict[int, float]]]:
    declarations = spec["sources"]
    for path, declaration, label in (
        (
            source_archive,
            declarations["libRadtran"],
            "libRadtran archive",
        ),
        (
            reptran_archive,
            declarations["REPTRAN_module"],
            "REPTRAN archive",
        ),
    ):
        if (
            not path.is_file()
            or path.stat().st_size != declaration["archive_bytes"]
            or sha256_file(path) != declaration["archive_sha256"]
        ):
            raise VisibilityRadianceResponseError(f"{label} identity differs")
    uvspec = libradtran_root / "bin" / "uvspec"
    lib = declarations["libRadtran"]
    if (
        not uvspec.is_file()
        or uvspec.stat().st_size != lib["uvspec_bytes"]
        or sha256_file(uvspec) != lib["uvspec_sha256"]
    ):
        raise VisibilityRadianceResponseError("uvspec identity differs")
    named_manifest = named_direct_artifact / "artifact-manifest.json"
    external_receipts = named_direct_artifact / "external-data-files.json"
    if (
        not named_manifest.is_file()
        or sha256_file(named_manifest) != NAMED_DIRECT_MANIFEST_SHA256
        or not external_receipts.is_file()
        or sha256_file(external_receipts)
        != EXTERNAL_DATA_RECEIPTS_SHA256
    ):
        raise VisibilityRadianceResponseError(
            "named-spectral predecessor artifact differs"
        )
    try:
        receipts = json.loads(external_receipts.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VisibilityRadianceResponseError(
            "external data receipt list is invalid"
        ) from exc
    if (
        not isinstance(receipts, list)
        or len(receipts) != 1478
        or external_receipts.read_bytes() != compact_json_bytes(receipts)
    ):
        raise VisibilityRadianceResponseError(
            "external data receipt inventory differs"
        )
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise VisibilityRadianceResponseError(
                "external data receipt is invalid"
            )
        relative = receipt.get("path")
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise VisibilityRadianceResponseError(
                "external data receipt path is unsafe"
            )
        path = data_root / relative
        if (
            not path.is_file()
            or path.stat().st_size != receipt.get("bytes")
            or sha256_file(path) != receipt.get("sha256")
        ):
            raise VisibilityRadianceResponseError(
                f"external data-root file differs: {relative}"
            )
    spectral_reference_sources: list[dict[str, Any]] = []
    for declaration in spec["radiance_solver"][
        "spectral_importance_reference_source_receipts"
    ]:
        path = libradtran_root / declaration["path"]
        if (
            not path.is_file()
            or path.stat().st_size != declaration["bytes"]
            or sha256_file(path) != declaration["sha256"]
        ):
            raise VisibilityRadianceResponseError(
                "spectral importance reference source differs: "
                f"{declaration['path']}"
            )
        spectral_reference_sources.append(dict(declaration))
    cie_tables: dict[str, dict[int, float]] = {}
    cie_receipts: dict[str, Any] = {}
    for response, source_name in (
        ("photopic", "CIE_photopic"),
        ("scotopic", "CIE_scotopic"),
    ):
        declaration = declarations[source_name]
        response_receipts: dict[str, Any] = {}
        for role in ("csv", "metadata"):
            path = cie_root / declaration[f"{role}_filename"]
            if (
                not path.is_file()
                or path.stat().st_size != declaration[f"{role}_bytes"]
                or sha256_file(path) != declaration[f"{role}_sha256"]
            ):
                raise VisibilityRadianceResponseError(
                    f"{response} CIE {role} identity differs"
                )
            response_receipts[role] = {
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        cie_tables[response] = _load_cie_table(
            cie_root / declaration["csv_filename"]
        )
        cie_receipts[response] = response_receipts
    source_receipt = {
        "libRadtran_archive": {
            "bytes": source_archive.stat().st_size,
            "sha256": sha256_file(source_archive),
        },
        "REPTRAN_archive": {
            "bytes": reptran_archive.stat().st_size,
            "sha256": sha256_file(reptran_archive),
        },
        "uvspec": {
            "bytes": uvspec.stat().st_size,
            "sha256": sha256_file(uvspec),
        },
        "named_direct_manifest_sha256": sha256_file(named_manifest),
        "external_data_receipts": {
            "file_count": len(receipts),
            "bytes": external_receipts.stat().st_size,
            "sha256": sha256_file(external_receipts),
        },
        "CIE": cie_receipts,
        "spectral_importance_reference_sources": (
            spectral_reference_sources
        ),
    }
    return uvspec, source_receipt, cie_tables


def _tooling_receipt(spec_path: Path) -> dict[str, Any]:
    paths = {
        "spec": spec_path,
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH,
    }
    result: dict[str, Any] = {}
    for role, path in paths.items():
        if not path.is_file():
            raise VisibilityRadianceResponseError(
                f"{role} tooling file is missing: {path}"
            )
        result[role] = file_receipt(path, relative_to=REPO_ROOT)
    return result


def _run_manifest_receipt(
    output_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    result_path = (
        output_root / "runs" / payload["run"]["run_id"] / "result.json"
    )
    return {
        "run_id": payload["run"]["run_id"],
        "run": payload["run"],
        "result": file_receipt(result_path, relative_to=output_root),
    }


def build_artifact(
    *,
    spec_path: Path,
    source_archive: Path,
    reptran_archive: Path,
    libradtran_root: Path,
    data_root: Path,
    cie_root: Path,
    named_direct_artifact: Path,
    output_root: Path,
    max_new_runs: int | None,
    reuse_runs_from: Path | None,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    output_root = output_root.resolve()
    if max_new_runs is not None and max_new_runs < 0:
        raise VisibilityRadianceResponseError(
            "max-new-runs must be non-negative"
        )
    if output_root.is_symlink():
        raise VisibilityRadianceResponseError(
            "output root must not be a symlink"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    if (output_root / MANIFEST_NAME).exists():
        raise VisibilityRadianceResponseError(
            "completed artifact is immutable; choose a new output directory"
        )
    reuse_runs_root: Path | None = None
    if reuse_runs_from is not None:
        reuse_runs_from = reuse_runs_from.resolve()
        if (
            reuse_runs_from == output_root
            or reuse_runs_from.is_symlink()
            or not (reuse_runs_from / "runs").is_dir()
        ):
            raise VisibilityRadianceResponseError(
                "reusable run cache is missing, unsafe, or is the output"
            )
        reuse_runs_root = reuse_runs_from / "runs"
    spec = load_spec(spec_path)
    uvspec, source_receipt, cie_tables = _verify_source_inputs(
        spec,
        source_archive=source_archive.resolve(),
        reptran_archive=reptran_archive.resolve(),
        libradtran_root=libradtran_root.resolve(),
        data_root=data_root.resolve(),
        cie_root=cie_root.resolve(),
        named_direct_artifact=named_direct_artifact.resolve(),
    )
    builder = RunBuilder(
        uvspec=uvspec,
        data_root=data_root.resolve(),
        output_root=output_root,
        spec=spec,
        cie_tables=cie_tables,
        max_new_runs=max_new_runs,
        reuse_runs_root=reuse_runs_root,
    )
    training, holdouts, response_holdouts = radiance_points(spec)
    anchors: list[dict[str, Any]] = []
    shapes: list[dict[str, Any]] = []
    run_payloads: list[dict[str, Any]] = []
    try:
        for partition, points in (
            ("training", training),
            ("holdout", holdouts),
        ):
            for point in points:
                aggregate, payloads = _build_anchor_aggregate(
                    builder,
                    point,
                    partition=partition,
                )
                anchors.append(aggregate)
                run_payloads.extend(payloads)
        for partition, points in (
            ("training", training),
            ("holdout", response_holdouts),
        ):
            for point in points:
                aggregate, payloads = _build_shape_aggregate(
                    builder,
                    point,
                    partition=partition,
                )
                shapes.append(aggregate)
                run_payloads.extend(payloads)
        direct_payloads: list[dict[str, Any]] = []
        for partition, altitudes in (
            (
                "training",
                spec["direct_solver"][
                    "training_target_true_altitude_deg"
                ],
            ),
            (
                "holdout",
                spec["direct_solver"][
                    "reserved_target_true_altitude_holdouts_deg"
                ],
            ),
        ):
            for altitude in altitudes:
                payload = builder.run(
                    _direct_run(float(altitude), partition=partition)
                )
                direct_payloads.append(payload)
                run_payloads.append(payload)
    except BuildBudgetReached:
        return {
            "status": "incomplete_resumable",
            "output": str(output_root),
            "new_run_count": builder.new_run_count,
            "reused_run_count": builder.reused_run_count,
            "manifest_emitted": False,
        }
    summary = summarize(
        spec,
        anchors,
        shapes,
        direct_payloads,
    )
    summary_path = output_root / SUMMARY_NAME
    summary_path.write_bytes(canonical_json_bytes(summary))
    tooling = _tooling_receipt(spec_path)
    generation_identity = {
        "spec_id": spec["spec_id"],
        "tooling": tooling,
        "source": source_receipt,
        "runtime_boundary": spec["runtime_boundary"],
        "effective_domain": spec["effective_domain"],
        "deep_twilight_law": spec["deep_twilight_law"],
    }
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "status": "phase1_complete_reference_artifact_not_runtime_data_pack",
        "spec_id": spec["spec_id"],
        "generation_fingerprint": sha256_bytes(
            canonical_json_bytes(generation_identity)
        ),
        "tooling": tooling,
        "source": source_receipt,
        "runtime_boundary": spec["runtime_boundary"],
        "effective_domain": spec["effective_domain"],
        "deep_twilight_law": spec["deep_twilight_law"],
        "run_count": len(run_payloads),
        "runs": [
            _run_manifest_receipt(output_root, payload)
            for payload in sorted(
                run_payloads,
                key=lambda payload: payload["run"]["run_id"],
            )
        ],
        "summary": file_receipt(summary_path, relative_to=output_root),
    }
    manifest_path = output_root / MANIFEST_NAME
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return {
        "status": "complete_reference_artifact",
        "output": str(output_root),
        "new_run_count": builder.new_run_count,
        "reused_run_count": builder.reused_run_count,
        "run_count": len(run_payloads),
        "generation_fingerprint": manifest["generation_fingerprint"],
        "manifest_sha256": sha256_file(manifest_path),
        "summary": {
            "error_summaries": summary["error_summaries"],
            "storage_analysis": summary["storage_analysis"],
            "monte_carlo": summary["monte_carlo"],
        },
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the final Phase 1 radiance/response artifact."
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--inspect-spec", action="store_true")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--reptran-archive", type=Path)
    parser.add_argument("--libradtran-root", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--cie-root", type=Path)
    parser.add_argument("--named-direct-artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-new-runs", type=int)
    parser.add_argument("--reuse-runs-from", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.inspect_spec:
            print(json.dumps(inspect_spec(args.spec), indent=2, sort_keys=True))
            return 0
        required = (
            "source_archive",
            "reptran_archive",
            "libradtran_root",
            "data_root",
            "cie_root",
            "named_direct_artifact",
            "output",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise VisibilityRadianceResponseError(
                "build requires: " + ", ".join(missing)
            )
        result = build_artifact(
            spec_path=args.spec,
            source_archive=args.source_archive,
            reptran_archive=args.reptran_archive,
            libradtran_root=args.libradtran_root,
            data_root=args.data_root,
            cie_root=args.cie_root,
            named_direct_artifact=args.named_direct_artifact,
            output_root=args.output,
            max_new_runs=args.max_new_runs,
            reuse_runs_from=args.reuse_runs_from,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except VisibilityRadianceResponseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
