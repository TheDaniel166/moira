#!/usr/bin/env python3
"""Build the Phase 1 altitude/pressure direct-transmission holdout probe.

This is offline research tooling. It executes an already built, checksum-bound
libRadtran tree and writes only immutable external evidence. It is not an
engine runtime dependency and does not authorize a production data pack.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_altitude_pressure_interpolation_probe_spec.json"
)
VALIDATOR_PATH = (
    REPO_ROOT / "scripts" / "validate_visibility_altitude_pressure_interpolation_probe.py"
)
MANIFEST_NAME = "manifest.json"
SUMMARY_NAME = "summary.json"
RUN_SCHEMA = "moira.visibility-altitude-pressure-interpolation-run/v1"
ARTIFACT_STATUS = (
    "phase1_altitude_pressure_interpolation_probe_not_runtime_data_pack"
)
DATA_LINK_NAME = "_libradtran_data"
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


class VisibilityAltitudePressureProbeError(ValueError):
    """Raised when the altitude/pressure probe violates its frozen contract."""


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


def _file_receipt(
    path: Path,
    *,
    relative_to: Path | None = None,
) -> dict[str, Any]:
    resolved = path.resolve()
    display = (
        resolved.relative_to(relative_to.resolve()).as_posix()
        if relative_to is not None
        else resolved.name
    )
    return {
        "path": display,
        "bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _canonical_float(value: float) -> float:
    if not math.isfinite(value):
        raise VisibilityAltitudePressureProbeError("non-finite derived value")
    return float(format(value, ".15g"))


def _format_number(value: float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise VisibilityAltitudePressureProbeError("non-finite input value")
    return format(number, ".15g")


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisibilityAltitudePressureProbeError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VisibilityAltitudePressureProbeError(f"{label} must be an array")
    return value


def _strictly_increasing(values: Any, label: str) -> list[float]:
    raw = _require_list(values, label)
    parsed: list[float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VisibilityAltitudePressureProbeError(
                f"{label} contains a non-number"
            )
        parsed.append(float(value))
    if not parsed or any(
        not math.isfinite(value) for value in parsed
    ) or any(a >= b for a, b in zip(parsed, parsed[1:])):
        raise VisibilityAltitudePressureProbeError(
            f"{label} must be finite and strictly increasing"
        )
    return parsed


def _valid_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise VisibilityAltitudePressureProbeError(f"{label} is not SHA-256")
    return value


def _validate_declared_receipt(receipt: Any, label: str) -> dict[str, Any]:
    value = _require_dict(receipt, label)
    path = value.get("path")
    byte_count = value.get("bytes")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count <= 0
    ):
        raise VisibilityAltitudePressureProbeError(f"{label} receipt is invalid")
    _valid_sha(value.get("sha256"), f"{label} sha256")
    return value


def _vertical_grid_segments(
    declaration: dict[str, Any],
) -> list[tuple[float, float, float]]:
    raw_segments = _require_list(
        declaration.get("base_segments_km_above_surface"),
        "vertical-grid segments",
    )
    parsed: list[tuple[float, float, float]] = []
    previous_stop: float | None = None
    for index, raw in enumerate(raw_segments):
        segment = _require_dict(raw, f"vertical-grid segment {index}")
        if set(segment) != {"start", "stop", "step"}:
            raise VisibilityAltitudePressureProbeError(
                "vertical-grid segment shape differs"
            )
        values: list[float] = []
        for label in ("start", "stop", "step"):
            value = segment[label]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise VisibilityAltitudePressureProbeError(
                    f"vertical-grid segment {label} differs"
                )
            values.append(float(value))
        start, stop, step = values
        if (
            start < 0.0
            or start >= stop
            or step <= 0.0
            or (previous_stop is not None and start != previous_stop)
        ):
            raise VisibilityAltitudePressureProbeError(
                "vertical-grid segment domain differs"
            )
        parsed.append((start, stop, step))
        previous_stop = stop
    return parsed


def site_relative_vertical_grid(
    observer_altitude_m: float,
    spec: dict[str, Any],
) -> list[float]:
    """Reconstruct the frozen near-surface grid relative to one site."""
    altitude_m = float(observer_altitude_m)
    if not math.isfinite(altitude_m) or not 0.0 <= altitude_m <= 5000.0:
        raise VisibilityAltitudePressureProbeError(
            "observer altitude is outside the vertical-grid domain"
        )
    declaration = _require_dict(
        spec.get("site_relative_vertical_grid"),
        "site-relative vertical grid",
    )
    site_km = Decimal(str(altitude_m)) / Decimal("1000")
    top_km = Decimal(str(declaration.get("top_of_atmosphere_km")))
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
        raise VisibilityAltitudePressureProbeError(
            "site-relative vertical grid lacks its surface"
        )
    if relative_levels[-1] != relative_top:
        relative_levels.append(relative_top)
    levels = [float(site_km + value) for value in relative_levels]
    if (
        levels[0] != float(site_km)
        or levels[-1] != float(top_km)
        or any(a >= b for a, b in zip(levels, levels[1:]))
    ):
        raise VisibilityAltitudePressureProbeError(
            "site-relative vertical grid is invalid"
        )
    return levels


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibilityAltitudePressureProbeError(
            f"cannot load specification: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise VisibilityAltitudePressureProbeError(
            "specification must be an object"
        )
    validate_spec(payload)
    return payload


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != (
        "moira.visibility-altitude-pressure-interpolation-probe-spec/v1"
    ):
        raise VisibilityAltitudePressureProbeError("specification schema differs")
    if spec.get("status") != "research_probe_not_runtime_data_pack":
        raise VisibilityAltitudePressureProbeError("specification status differs")
    if spec.get("composite_model_id") != (
        "clear_sky_naked_eye_point_source_v1"
    ):
        raise VisibilityAltitudePressureProbeError("composite model differs")

    predecessor = _require_dict(spec.get("predecessor"), "predecessor")
    for label in ("spec", "builder", "validator", "checkpoint"):
        _validate_declared_receipt(
            {
                "path": predecessor.get(f"{label}_path"),
                "bytes": predecessor.get(f"{label}_bytes"),
                "sha256": predecessor.get(f"{label}_sha256"),
            },
            f"predecessor {label}",
        )
    dependency = _validate_declared_receipt(
        spec.get("construction_dependency"),
        "construction dependency",
    )
    if dependency.get("functions") != [
        "construct_truncated_atmosphere",
        "construct_truncated_o4_profile",
    ]:
        raise VisibilityAltitudePressureProbeError(
            "construction dependency functions differ"
        )
    grid_predecessor = _validate_declared_receipt(
        spec.get("vertical_grid_predecessor"),
        "vertical-grid predecessor",
    )
    if (
        grid_predecessor.get("source_grid_id")
        != "near_horizon_piecewise_refined_v1"
        or grid_predecessor.get("source_grid_expected_level_count") != 290
    ):
        raise VisibilityAltitudePressureProbeError(
            "vertical-grid predecessor differs"
        )
    refinements = _require_list(
        spec.get("refinement_from_failed_designs"),
        "failed-design refinements",
    )
    expected_refinement_laws = [
        "v1_promote_failed_altitude_holdouts_without_relaxing_thresholds",
        (
            "v2_reject_native_vertical_grid_after_source_bound_aerosol_"
            "discretization_diagnosis_and_use_new_holdouts"
        ),
        (
            "v3_retain_scientific_design_and_repair_binary32_round_trip_"
            "validation_without_reusing_the_failed_manifest"
        ),
        (
            "v4_retain_scientific_design_and_replace_cross_platform_"
            "transcendental_byte_equality_with_checksum_bound_numeric_"
            "validation"
        ),
    ]
    if len(refinements) != len(expected_refinement_laws):
        raise VisibilityAltitudePressureProbeError(
            "failed-design refinement count differs"
        )
    for index, (refinement, law) in enumerate(
        zip(refinements, expected_refinement_laws)
    ):
        declaration = _require_dict(
            refinement,
            f"failed-design refinement {index}",
        )
        _validate_declared_receipt(
            {
                "path": declaration.get("receipt_path"),
                "bytes": declaration.get("receipt_bytes"),
                "sha256": declaration.get("receipt_sha256"),
            },
            f"failed-design receipt {index}",
        )
        if (
            declaration.get("law") != law
            or declaration.get("thresholds_relaxed") is not False
        ):
            raise VisibilityAltitudePressureProbeError(
                "failed-design refinement law differs"
            )

    boundary = _require_dict(spec.get("runtime_boundary"), "runtime boundary")
    expected_boundary = {
        "network_allowed": False,
        "automatic_download_allowed": False,
        "engine_dependency_allowed": False,
        "engine_runtime_invocation_allowed": False,
        "generated_numerical_products_only": True,
        "production_data_pack_authorized": False,
        "engine_changes_authorized": False,
    }
    if boundary != expected_boundary:
        raise VisibilityAltitudePressureProbeError("runtime boundary differs")

    source = _require_dict(spec.get("libradtran_source"), "libRadtran source")
    if (
        source.get("version") != "2.0.6"
        or source.get("archive_bytes") != 154147176
        or source.get("archive_sha256")
        != "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
        or source.get("uvspec_version") != "uvspec, version 2.0.6-MYSTIC"
    ):
        raise VisibilityAltitudePressureProbeError("libRadtran identity differs")
    _valid_sha(source.get("uvspec_sha256"), "uvspec sha256")
    source_files = _require_list(source.get("source_files"), "source files")
    if len(source_files) != 4:
        raise VisibilityAltitudePressureProbeError("source file count differs")
    for index, receipt in enumerate(source_files):
        _validate_declared_receipt(receipt, f"source file {index}")

    profiles = _require_dict(spec.get("atmosphere_profiles"), "profiles")
    expected_profiles = {
        "tropical",
        "midlatitude_summer",
        "midlatitude_winter",
        "subarctic_summer",
        "subarctic_winter",
        "us_standard",
    }
    if set(profiles) != expected_profiles:
        raise VisibilityAltitudePressureProbeError("profile inventory differs")
    for name, declaration in profiles.items():
        receipt = _validate_declared_receipt(declaration, f"profile {name}")
        if receipt.get("aerosol_season") not in {1, 2}:
            raise VisibilityAltitudePressureProbeError(
                f"profile season differs: {name}"
            )

    axes = _require_dict(spec.get("axes"), "axes")
    altitude = _require_dict(axes.get("observer_altitude_m"), "altitude axis")
    pressure = _require_dict(axes.get("pressure_ratio"), "pressure axis")
    altitude_nodes = _strictly_increasing(
        altitude.get("training_nodes"),
        "altitude training nodes",
    )
    altitude_holdouts = _strictly_increasing(
        altitude.get("reserved_holdouts"),
        "altitude holdouts",
    )
    pressure_nodes = _strictly_increasing(
        pressure.get("training_nodes"),
        "pressure training nodes",
    )
    pressure_holdouts = _strictly_increasing(
        pressure.get("reserved_holdouts"),
        "pressure holdouts",
    )
    if altitude_nodes != [
        0.0,
        500.0,
        1000.0,
        1500.0,
        2250.0,
        3000.0,
        4000.0,
        5000.0,
    ]:
        raise VisibilityAltitudePressureProbeError("altitude nodes differ")
    if altitude_holdouts != [
        125.0,
        375.0,
        625.0,
        875.0,
        1125.0,
        1375.0,
        1688.0,
        2062.0,
        2438.0,
        2812.0,
        3250.0,
        3750.0,
        4250.0,
        4750.0,
    ]:
        raise VisibilityAltitudePressureProbeError("altitude holdouts differ")
    if pressure_nodes != [0.85, 0.925, 1.0, 1.04, 1.08]:
        raise VisibilityAltitudePressureProbeError("pressure nodes differ")
    if pressure_holdouts != [
        0.8688,
        0.9063,
        0.9438,
        0.9813,
        1.01,
        1.03,
        1.05,
        1.07,
    ]:
        raise VisibilityAltitudePressureProbeError("pressure holdouts differ")
    if set(altitude_nodes) & set(altitude_holdouts):
        raise VisibilityAltitudePressureProbeError("altitude holdouts overlap")
    if set(pressure_nodes) & set(pressure_holdouts):
        raise VisibilityAltitudePressureProbeError("pressure holdouts overlap")
    if (
        pressure.get("absolute_pressure_hard_bounds_hpa") != [500.0, 1100.0]
        or pressure.get("ratio_hard_bounds") != [0.85, 1.08]
        or pressure.get("admission_law")
        != "absolute_and_ratio_bounds_must_both_pass"
    ):
        raise VisibilityAltitudePressureProbeError("pressure law differs")
    if _strictly_increasing(
        axes.get("target_true_altitude_deg"),
        "target altitude axis",
    ) != [0.25, 5.0, 20.0]:
        raise VisibilityAltitudePressureProbeError("target altitude axis differs")
    if _strictly_increasing(
        axes.get("wavelength_nm"),
        "wavelength axis",
    ) != [400.0, 550.0, 780.0]:
        raise VisibilityAltitudePressureProbeError("wavelength axis differs")

    environment = _require_dict(spec.get("fixed_environment"), "environment")
    if (
        environment.get("aerosol_scattering_override")
        != "aerosol_modify ssa set 0"
        or environment.get("temperature_and_humidity")
        != "named_profile_derived"
        or environment.get("ground_albedo") != 0.0
    ):
        raise VisibilityAltitudePressureProbeError("fixed environment differs")
    closure = _require_dict(spec.get("pressure_o4_closure"), "O4 closure")
    if (
        closure.get("physical_override")
        != "source_equivalent_truncated_o4_profile_times_pressure_ratio_squared"
        or closure.get("ratio_one_control_required") is not True
    ):
        raise VisibilityAltitudePressureProbeError("pressure O4 closure differs")
    vertical_grid = _require_dict(
        spec.get("site_relative_vertical_grid"),
        "site-relative vertical grid",
    )
    if (
        vertical_grid.get("grid_id")
        != "site_relative_near_horizon_piecewise_refined_v1"
        or vertical_grid.get("source_grid_id")
        != grid_predecessor["source_grid_id"]
        or vertical_grid.get("source_sea_level_level_count") != 290
        or vertical_grid.get("top_of_atmosphere_km") != 120.0
        or vertical_grid.get("construction")
        != (
            "truncate_relative_grid_at_120km_minus_site_translate_by_site_"
            "and_append_exact_120km"
        )
    ):
        raise VisibilityAltitudePressureProbeError(
            "site-relative vertical-grid contract differs"
        )
    if _vertical_grid_segments(vertical_grid) != [
        (0.0, 2.0, 0.025),
        (2.0, 5.0, 0.05),
        (5.0, 10.0, 0.1),
        (10.0, 25.0, 0.25),
        (25.0, 50.0, 1.0),
        (50.0, 120.0, 5.0),
    ]:
        raise VisibilityAltitudePressureProbeError(
            "site-relative vertical-grid segments differ"
        )
    if len(site_relative_vertical_grid(0.0, spec)) != 290:
        raise VisibilityAltitudePressureProbeError(
            "site-relative sea-level grid count differs"
        )

    solver = _require_dict(spec.get("direct_solver"), "direct solver")
    if (
        solver.get("rte_solver") != "disort"
        or solver.get("geometry") != "pseudospherical"
        or solver.get("number_of_streams") != 16
        or solver.get("molecular_absorption") != "crs"
        or solver.get("normalization")
        != "direct_transmission_equals_edir_divided_by_sin_target_true_altitude"
        or solver.get("serial_execution_required") is not True
    ):
        raise VisibilityAltitudePressureProbeError("direct solver differs")

    candidates = spec.get("interpolation_candidates")
    if candidates != [
        "bilinear_direct_transmission",
        "bilinear_optical_depth",
        "bilinear_extinction_magnitude",
    ]:
        raise VisibilityAltitudePressureProbeError(
            "interpolation candidates differ"
        )
    admission = _require_dict(
        spec.get("interpolation_admission"),
        "interpolation admission",
    )
    if (
        admission.get("required_method") != "bilinear_extinction_magnitude"
        or admission.get("training_only") is not True
        or admission.get("no_extrapolation") is not True
        or admission.get("query_requires_valid_bracketing_cell") is not True
        or admission.get("node_values_are_not_refit_to_holdouts") is not True
        or admission.get("reserved_holdouts_previously_unseen") is not True
    ):
        raise VisibilityAltitudePressureProbeError(
            "interpolation admission law differs"
        )
    for name in (
        "maximum_absolute_extinction_error_mag",
        "p95_absolute_extinction_error_mag",
        "maximum_relative_transmission_error",
    ):
        value = admission.get(name)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0.0 < float(value) < 1.0
        ):
            raise VisibilityAltitudePressureProbeError(
                f"invalid interpolation threshold: {name}"
            )


def _verify_declared_repo_file(
    receipt: dict[str, Any],
    label: str,
) -> Path:
    path = (REPO_ROOT / str(receipt["path"])).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise VisibilityAltitudePressureProbeError(
            f"{label} escapes repository"
        ) from exc
    if (
        not path.is_file()
        or path.stat().st_size != receipt["bytes"]
        or _sha256_file(path) != receipt["sha256"]
    ):
        raise VisibilityAltitudePressureProbeError(f"{label} receipt differs")
    return path


def _verify_declared_source_file(
    root: Path,
    receipt: dict[str, Any],
    label: str,
) -> Path:
    path = (root / str(receipt["path"])).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise VisibilityAltitudePressureProbeError(
            f"{label} escapes source tree"
        ) from exc
    if (
        not path.is_file()
        or path.stat().st_size != receipt["bytes"]
        or _sha256_file(path) != receipt["sha256"]
    ):
        raise VisibilityAltitudePressureProbeError(f"{label} receipt differs")
    return path


def _load_construction_dependency(path: Path) -> ModuleType:
    module_spec = importlib.util.spec_from_file_location(
        "moira_visibility_elevated_site_dependency",
        path,
    )
    if module_spec is None or module_spec.loader is None:
        raise VisibilityAltitudePressureProbeError(
            "cannot load construction dependency"
        )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for name in (
        "construct_truncated_atmosphere",
        "construct_truncated_o4_profile",
        "_float32",
        "_format_float32",
    ):
        if not callable(getattr(module, name, None)):
            raise VisibilityAltitudePressureProbeError(
                f"construction dependency lacks {name}"
            )
    return module


def _profile_filename(profile: str, altitude_m: float, kind: str) -> str:
    altitude_token = f"{int(round(altitude_m)):04d}m"
    suffix = "dat" if kind in {"atmosphere", "o4"} else "json"
    return f"{profile}__{altitude_token}__{kind}.{suffix}"


def _replace_profile_source_header(
    payload: bytes,
    source_path: str,
) -> bytes:
    text = payload.decode("utf-8")
    text = text.replace(
        "data/atmmod/afglus.dat",
        source_path,
        1,
    )
    return text.encode("utf-8")


def _scale_o4_payload(
    payload: bytes,
    pressure_ratio: float,
    dependency: ModuleType,
) -> bytes:
    if math.isclose(pressure_ratio, 1.0, rel_tol=0.0, abs_tol=0.0):
        return payload
    ratio_squared = dependency._float32(
        dependency._float32(pressure_ratio)
        * dependency._float32(pressure_ratio)
    )
    output: list[str] = []
    for line in payload.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            output.append(line)
            continue
        fields = stripped.split()
        if len(fields) != 2:
            raise VisibilityAltitudePressureProbeError(
                "O4 companion row shape differs"
            )
        altitude = float(fields[0])
        density = dependency._float32(float(fields[1]))
        scaled = dependency._float32(density * ratio_squared)
        output.append(
            f"{dependency._format_float32(altitude)} "
            f"{dependency._format_float32(scaled)}"
        )
    return ("\n".join(output) + "\n").encode("utf-8")


def _all_axis_values(axis: dict[str, Any]) -> list[float]:
    return sorted(
        {
            *(float(value) for value in axis["training_nodes"]),
            *(float(value) for value in axis["reserved_holdouts"]),
        }
    )


def _prepare_profiles(
    *,
    output_root: Path,
    libradtran_root: Path,
    spec: dict[str, Any],
    dependency: ModuleType,
) -> tuple[dict[tuple[str, float], dict[str, Any]], list[dict[str, Any]]]:
    profiles_root = output_root / spec["artifact"]["profiles_directory"]
    profiles_root.mkdir(exist_ok=True)
    altitude_values = _all_axis_values(
        spec["axes"]["observer_altitude_m"]
    )
    prepared: dict[tuple[str, float], dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    for profile, declaration in spec["atmosphere_profiles"].items():
        source_path = _verify_declared_source_file(
            libradtran_root,
            declaration,
            f"atmosphere profile {profile}",
        )
        source_text = source_path.read_text(encoding="utf-8")
        for altitude_m in altitude_values:
            atmosphere_bytes, atmosphere_metadata = (
                dependency.construct_truncated_atmosphere(
                    source_text,
                    altitude_m,
                )
            )
            atmosphere_bytes = _replace_profile_source_header(
                atmosphere_bytes,
                declaration["path"],
            )
            o4_bytes, o4_metadata = dependency.construct_truncated_o4_profile(
                source_text,
                altitude_m,
            )
            atmosphere_name = _profile_filename(
                profile,
                altitude_m,
                "atmosphere",
            )
            o4_name = _profile_filename(profile, altitude_m, "o4")
            metadata_name = _profile_filename(
                profile,
                altitude_m,
                "metadata",
            )
            atmosphere_path = profiles_root / atmosphere_name
            o4_path = profiles_root / o4_name
            metadata_path = profiles_root / metadata_name
            metadata = {
                "profile": profile,
                "source": declaration["path"],
                "observer_altitude_m": altitude_m,
                "profile_surface_pressure_hpa": _canonical_float(
                    float(atmosphere_metadata["bottom_level"]["pressure_hpa"])
                ),
                "atmosphere_construction": atmosphere_metadata,
                "o4_construction": o4_metadata,
            }
            expected_metadata = _canonical_json_bytes(metadata)
            expected = {
                atmosphere_path: atmosphere_bytes,
                o4_path: o4_bytes,
                metadata_path: expected_metadata,
            }
            for path, payload in expected.items():
                if path.exists():
                    if path.is_symlink() or path.read_bytes() != payload:
                        raise VisibilityAltitudePressureProbeError(
                            f"existing profile evidence differs: {path}"
                        )
                else:
                    path.write_bytes(payload)
            prepared[(profile, altitude_m)] = {
                "atmosphere_bytes": atmosphere_bytes,
                "o4_bytes": o4_bytes,
                "metadata": metadata,
            }
            receipts.append(
                {
                    "profile": profile,
                    "observer_altitude_m": altitude_m,
                    "profile_surface_pressure_hpa": metadata[
                        "profile_surface_pressure_hpa"
                    ],
                    "atmosphere": _file_receipt(
                        atmosphere_path,
                        relative_to=output_root,
                    ),
                    "o4": _file_receipt(o4_path, relative_to=output_root),
                    "metadata": _file_receipt(
                        metadata_path,
                        relative_to=output_root,
                    ),
                }
            )
    return prepared, receipts


def _value_token(value: float, places: int) -> str:
    scale = 10**places
    return f"{int(round(float(value) * scale)):0{places + 2}d}"


def expand_runs(
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
        for altitude_m in altitude_values:
            profile_pressure = float(
                profiles[(profile, altitude_m)]["metadata"][
                    "profile_surface_pressure_hpa"
                ]
            )
            vertical_grid = site_relative_vertical_grid(altitude_m, spec)
            altitude_is_node = altitude_m in altitude_nodes
            for ratio in pressure_values:
                requested_pressure = _canonical_float(profile_pressure * ratio)
                if not lower_pressure <= requested_pressure <= upper_pressure:
                    continue
                pressure_is_node = ratio in pressure_nodes
                if altitude_is_node and pressure_is_node:
                    partition = "training"
                elif not altitude_is_node and pressure_is_node:
                    partition = "altitude_holdout"
                elif altitude_is_node and not pressure_is_node:
                    partition = "pressure_holdout"
                else:
                    partition = "joint_holdout"
                for target_altitude in spec["axes"]["target_true_altitude_deg"]:
                    run_id = (
                        f"{profile}__z{int(round(altitude_m)):04d}"
                        f"__p{_value_token(ratio, 4)}"
                        f"__h{_value_token(float(target_altitude), 2)}"
                    )
                    runs.append(
                        {
                            "run_id": run_id,
                            "partition": partition,
                            "profile": profile,
                            "profile_source_path": declaration["path"],
                            "aerosol_season": declaration["aerosol_season"],
                            "observer_altitude_m": altitude_m,
                            "vertical_grid_id": spec[
                                "site_relative_vertical_grid"
                            ]["grid_id"],
                            "vertical_grid_level_count": len(vertical_grid),
                            "profile_surface_pressure_hpa": profile_pressure,
                            "pressure_ratio": ratio,
                            "requested_surface_pressure_hpa": requested_pressure,
                            "target_true_altitude_deg": float(target_altitude),
                            "wavelength_nm": [
                                float(value)
                                for value in spec["axes"]["wavelength_nm"]
                            ],
                        }
                    )
    run_ids = [run["run_id"] for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise VisibilityAltitudePressureProbeError("run identifiers collide")
    return runs


def _wavelength_grid_text(run: dict[str, Any]) -> str:
    return "".join(f"{_format_number(value)}\n" for value in run["wavelength_nm"])


def render_input(run: dict[str, Any], spec: dict[str, Any]) -> str:
    solver = spec["direct_solver"]
    environment = spec["fixed_environment"]
    cross_sections = solver["cross_sections"]
    alpha = float(environment["angstrom_exponent"])
    beta = _canonical_float(float(environment["aod550"]) * (0.55**alpha))
    target_altitude = float(run["target_true_altitude_deg"])
    vertical_grid = site_relative_vertical_grid(
        float(run["observer_altitude_m"]),
        spec,
    )
    if len(vertical_grid) != run["vertical_grid_level_count"]:
        raise VisibilityAltitudePressureProbeError(
            "run vertical-grid level count differs"
        )
    lines = [
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
    rendered = "\n".join(lines) + "\n"
    for forbidden in (
        "altitude ",
        "mc_spherical",
        "mol_abs_param reptran",
        "aerosol_visibility",
        "rh_file",
        "radiosonde",
    ):
        if forbidden in rendered:
            raise VisibilityAltitudePressureProbeError(
                "rendered input crossed the probe boundary"
            )
    return rendered


def parse_output(
    text: str,
    run: dict[str, Any],
) -> list[dict[str, float]]:
    rows = [line.split() for line in text.splitlines() if line.strip()]
    if len(rows) != len(run["wavelength_nm"]):
        raise VisibilityAltitudePressureProbeError(
            f"output row count differs for {run['run_id']}: {len(rows)}"
        )
    projection = math.sin(
        math.radians(float(run["target_true_altitude_deg"]))
    )
    parsed: list[dict[str, float]] = []
    for fields, expected_wavelength in zip(rows, run["wavelength_nm"]):
        if len(fields) != 2:
            raise VisibilityAltitudePressureProbeError(
                f"output columns differ for {run['run_id']}"
            )
        try:
            wavelength = float(fields[0])
            horizontal = float(fields[1])
        except ValueError as exc:
            raise VisibilityAltitudePressureProbeError(
                f"non-numeric output for {run['run_id']}"
            ) from exc
        transmission = horizontal / projection
        if (
            not math.isclose(
                wavelength,
                float(expected_wavelength),
                rel_tol=0.0,
                abs_tol=5.0e-4,
            )
            or not math.isfinite(horizontal)
            or not math.isfinite(transmission)
            or not 0.0 < transmission <= 1.0000001
        ):
            raise VisibilityAltitudePressureProbeError(
                f"output value differs for {run['run_id']}"
            )
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


def _run_uvspec(
    *,
    uvspec: Path,
    data_root: Path,
    run_dir: Path,
    input_text: str,
) -> str:
    data_link = run_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    try:
        syntax = subprocess.run(
            [str(uvspec), "-c"],
            cwd=run_dir,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        (run_dir / "syntax.stdout.txt").write_text(
            syntax.stdout,
            encoding="utf-8",
            newline="\n",
        )
        (run_dir / "syntax.stderr.txt").write_text(
            syntax.stderr,
            encoding="utf-8",
            newline="\n",
        )
        if (
            syntax.returncode != 0
            or "Error" in syntax.stderr
            or "Exiting" in syntax.stderr
        ):
            raise VisibilityAltitudePressureProbeError(
                f"uvspec syntax check failed in {run_dir.name}"
            )
        completed = subprocess.run(
            [str(uvspec)],
            cwd=run_dir,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        (run_dir / "stdout.txt").write_text(
            completed.stdout,
            encoding="utf-8",
            newline="\n",
        )
        (run_dir / "stderr.txt").write_text(
            completed.stderr,
            encoding="utf-8",
            newline="\n",
        )
        if (
            completed.returncode != 0
            or "Error" in completed.stderr
            or "Exiting" in completed.stderr
        ):
            raise VisibilityAltitudePressureProbeError(
                f"uvspec failed in {run_dir.name}"
            )
        return completed.stdout
    finally:
        if data_link.is_symlink():
            data_link.unlink()


def _result_payload(
    run: dict[str, Any],
    result: list[dict[str, float]],
) -> bytes:
    return _canonical_json_bytes(
        {
            "schema": RUN_SCHEMA,
            "run": run,
            "result": result,
        }
    )


def _verify_existing_run(
    *,
    run_dir: Path,
    run: dict[str, Any],
    spec: dict[str, Any],
    atmosphere_bytes: bytes,
    o4_bytes: bytes,
) -> list[dict[str, float]]:
    present = {path.name for path in run_dir.iterdir() if path.is_file()}
    if present != RUN_FILES or any(path.is_symlink() for path in run_dir.iterdir()):
        raise VisibilityAltitudePressureProbeError(
            f"existing run inventory differs: {run_dir}"
        )
    expected_input = render_input(run, spec)
    expected_grid = _wavelength_grid_text(run)
    if (
        (run_dir / "input.inp").read_text(encoding="utf-8") != expected_input
        or (run_dir / "wavelength_grid.dat").read_text(encoding="utf-8")
        != expected_grid
        or (run_dir / "atmosphere.dat").read_bytes() != atmosphere_bytes
        or (run_dir / "o4.dat").read_bytes() != o4_bytes
        or (run_dir / "randomseed").read_text(encoding="utf-8").strip()
        != str(spec["direct_solver"]["random_seed"])
    ):
        raise VisibilityAltitudePressureProbeError(
            f"existing run input differs: {run_dir}"
        )
    result = parse_output(
        (run_dir / "stdout.txt").read_text(encoding="utf-8"),
        run,
    )
    if (run_dir / "result.json").read_bytes() != _result_payload(run, result):
        raise VisibilityAltitudePressureProbeError(
            f"existing run result differs: {run_dir}"
        )
    return result


def _write_run(
    *,
    runs_root: Path,
    uvspec: Path,
    data_root: Path,
    run: dict[str, Any],
    spec: dict[str, Any],
    profile: dict[str, Any],
    dependency: ModuleType,
) -> list[dict[str, float]]:
    final_dir = runs_root / run["run_id"]
    atmosphere_bytes = profile["atmosphere_bytes"]
    o4_bytes = _scale_o4_payload(
        profile["o4_bytes"],
        float(run["pressure_ratio"]),
        dependency,
    )
    if final_dir.exists():
        if not final_dir.is_dir() or final_dir.is_symlink():
            raise VisibilityAltitudePressureProbeError(
                f"run path is invalid: {final_dir}"
            )
        return _verify_existing_run(
            run_dir=final_dir,
            run=run,
            spec=spec,
            atmosphere_bytes=atmosphere_bytes,
            o4_bytes=o4_bytes,
        )

    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{run['run_id']}.", dir=runs_root)
    )
    try:
        input_text = render_input(run, spec)
        (temp_dir / "input.inp").write_text(
            input_text,
            encoding="utf-8",
            newline="\n",
        )
        (temp_dir / "wavelength_grid.dat").write_text(
            _wavelength_grid_text(run),
            encoding="utf-8",
            newline="\n",
        )
        (temp_dir / "atmosphere.dat").write_bytes(atmosphere_bytes)
        (temp_dir / "o4.dat").write_bytes(o4_bytes)
        stdout = _run_uvspec(
            uvspec=uvspec,
            data_root=data_root,
            run_dir=temp_dir,
            input_text=input_text,
        )
        if not (temp_dir / "randomseed").is_file():
            raise VisibilityAltitudePressureProbeError(
                f"random-seed receipt is missing: {run['run_id']}"
            )
        result = parse_output(stdout, run)
        (temp_dir / "result.json").write_bytes(_result_payload(run, result))
        present = {path.name for path in temp_dir.iterdir() if path.is_file()}
        if present != RUN_FILES:
            raise VisibilityAltitudePressureProbeError(
                f"new run inventory differs: {run['run_id']}"
            )
        os.replace(temp_dir, final_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return result


def _bracket(nodes: list[float], value: float) -> tuple[float, float]:
    if value in nodes:
        return value, value
    for lower, upper in zip(nodes, nodes[1:]):
        if lower < value < upper:
            return lower, upper
    raise VisibilityAltitudePressureProbeError(
        f"holdout lies outside training nodes: {value}"
    )


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
    if not values:
        raise VisibilityAltitudePressureProbeError("empty percentile input")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return _linear(ordered[lower], ordered[upper], position - lower)


def summarize(
    *,
    runs: list[dict[str, Any]],
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
    run_by_id = {run["run_id"]: run for run in runs}
    for run in runs:
        if run["partition"] != "training":
            continue
        for row in results[run["run_id"]]:
            key = (
                str(run["profile"]),
                float(run["target_true_altitude_deg"]),
                float(row["wavelength_nm"]),
                float(run["observer_altitude_m"]),
                float(run["pressure_ratio"]),
            )
            lookup[key] = row

    methods = {
        name: {
            "errors_mag": [],
            "relative_transmission_errors": [],
            "partition_errors_mag": {
                "altitude_holdout": [],
                "pressure_holdout": [],
                "joint_holdout": [],
            },
        }
        for name in spec["interpolation_candidates"]
    }
    evaluated_count = 0
    excluded_count = 0
    excluded_by_partition = {
        "altitude_holdout": 0,
        "pressure_holdout": 0,
        "joint_holdout": 0,
    }
    holdout_count = 0
    worst_cases: dict[str, dict[str, Any] | None] = {
        name: None for name in methods
    }
    for run_id, run in run_by_id.items():
        partition = str(run["partition"])
        if partition == "training":
            continue
        holdout_count += len(results[run_id])
        altitude = float(run["observer_altitude_m"])
        pressure = float(run["pressure_ratio"])
        z_bracket = _bracket(altitude_nodes, altitude)
        p_bracket = _bracket(pressure_nodes, pressure)
        for truth in results[run_id]:
            wavelength = float(truth["wavelength_nm"])
            corner_rows: dict[tuple[float, float], dict[str, float]] = {}
            for z_value in set(z_bracket):
                for p_value in set(p_bracket):
                    key = (
                        str(run["profile"]),
                        float(run["target_true_altitude_deg"]),
                        wavelength,
                        z_value,
                        p_value,
                    )
                    if key in lookup:
                        corner_rows[(z_value, p_value)] = lookup[key]
            required_corners = {
                (z_value, p_value)
                for z_value in set(z_bracket)
                for p_value in set(p_bracket)
            }
            if set(corner_rows) != required_corners:
                excluded_count += 1
                excluded_by_partition[partition] += 1
                continue
            evaluated_count += 1
            for method, accumulator in methods.items():
                if method == "bilinear_direct_transmission":
                    values = {
                        key: row["direct_spectral_transmission"]
                        for key, row in corner_rows.items()
                    }
                    predicted_transmission = _bilinear(
                        values,
                        z_bracket,
                        p_bracket,
                        altitude,
                        pressure,
                    )
                    predicted_extinction = -2.5 * math.log10(
                        predicted_transmission
                    )
                elif method == "bilinear_optical_depth":
                    values = {
                        key: row["optical_depth"]
                        for key, row in corner_rows.items()
                    }
                    predicted_tau = _bilinear(
                        values,
                        z_bracket,
                        p_bracket,
                        altitude,
                        pressure,
                    )
                    predicted_transmission = math.exp(-predicted_tau)
                    predicted_extinction = (
                        2.5 / math.log(10.0)
                    ) * predicted_tau
                elif method == "bilinear_extinction_magnitude":
                    values = {
                        key: row["extinction_magnitude"]
                        for key, row in corner_rows.items()
                    }
                    predicted_extinction = _bilinear(
                        values,
                        z_bracket,
                        p_bracket,
                        altitude,
                        pressure,
                    )
                    predicted_transmission = 10.0 ** (
                        -predicted_extinction / 2.5
                    )
                else:
                    raise VisibilityAltitudePressureProbeError(
                        f"unsupported interpolation method: {method}"
                    )
                error_mag = abs(
                    predicted_extinction - truth["extinction_magnitude"]
                )
                relative_error = abs(
                    predicted_transmission
                    - truth["direct_spectral_transmission"]
                ) / truth["direct_spectral_transmission"]
                accumulator["errors_mag"].append(error_mag)
                accumulator["relative_transmission_errors"].append(
                    relative_error
                )
                accumulator["partition_errors_mag"][partition].append(error_mag)
                worst = worst_cases[method]
                if worst is None or error_mag > worst["absolute_error_mag"]:
                    worst_cases[method] = {
                        "run_id": run_id,
                        "profile": run["profile"],
                        "partition": partition,
                        "observer_altitude_m": altitude,
                        "pressure_ratio": pressure,
                        "target_true_altitude_deg": run[
                            "target_true_altitude_deg"
                        ],
                        "wavelength_nm": wavelength,
                        "truth_extinction_magnitude": truth[
                            "extinction_magnitude"
                        ],
                        "predicted_extinction_magnitude": _canonical_float(
                            predicted_extinction
                        ),
                        "absolute_error_mag": _canonical_float(error_mag),
                        "relative_transmission_error": _canonical_float(
                            relative_error
                        ),
                    }

    if evaluated_count == 0:
        raise VisibilityAltitudePressureProbeError(
            "no holdout values were evaluable"
        )
    method_summary: dict[str, Any] = {}
    for name, accumulator in methods.items():
        errors = accumulator["errors_mag"]
        relative_errors = accumulator["relative_transmission_errors"]
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
                for partition, values in accumulator[
                    "partition_errors_mag"
                ].items()
                if values
            },
            "worst_case": worst_cases[name],
        }
    partitions: dict[str, int] = {}
    for run in runs:
        partitions[run["partition"]] = partitions.get(run["partition"], 0) + 1
    summary = {
        "schema": (
            "moira.visibility-altitude-pressure-interpolation-summary/v1"
        ),
        "run_count": len(runs),
        "partition_run_counts": partitions,
        "spectral_value_count": len(runs)
        * len(spec["axes"]["wavelength_nm"]),
        "training_spectral_value_count": partitions["training"]
        * len(spec["axes"]["wavelength_nm"]),
        "holdout_spectral_value_count": holdout_count,
        "evaluated_holdout_value_count": evaluated_count,
        "excluded_holdout_value_count": excluded_count,
        "excluded_holdout_values_by_partition": excluded_by_partition,
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
    enforce_acceptance(summary, spec)
    return summary


def enforce_acceptance(summary: dict[str, Any], spec: dict[str, Any]) -> None:
    if summary["evaluated_holdout_value_count"] <= 0:
        raise VisibilityAltitudePressureProbeError(
            "no holdout values were evaluable"
        )
    admission = spec["interpolation_admission"]
    method = summary["interpolation_methods"][admission["required_method"]]
    failures: list[str] = []
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
            failures.append(
                f"{metric}={method[metric]} exceeds {threshold}"
            )
    if failures:
        raise VisibilityAltitudePressureProbeError(
            "interpolation admission failed: " + "; ".join(failures)
        )


def _run_receipt(
    output_root: Path,
    runs_root: Path,
    run: dict[str, Any],
    result: list[dict[str, float]],
) -> dict[str, Any]:
    run_dir = runs_root / run["run_id"]
    return {
        "run_id": run["run_id"],
        "partition": run["partition"],
        "files": [
            _file_receipt(run_dir / name, relative_to=output_root)
            for name in sorted(RUN_FILES)
        ],
        "result": result,
    }


def _parse_declared_predecessor(
    predecessor: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for label in ("spec", "builder", "validator", "checkpoint"):
        parsed[label] = {
            "path": predecessor[f"{label}_path"],
            "bytes": predecessor[f"{label}_bytes"],
            "sha256": predecessor[f"{label}_sha256"],
        }
    return parsed


def _parse_declared_refinements(
    refinements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "path": declaration["receipt_path"],
            "bytes": declaration["receipt_bytes"],
            "sha256": declaration["receipt_sha256"],
        }
        for declaration in refinements
    ]


def build_artifact(
    *,
    spec_path: Path,
    source_archive: Path,
    libradtran_root: Path,
    output_root: Path,
    max_new_runs: int | None = None,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    spec = load_spec(spec_path)
    source_archive = source_archive.resolve()
    libradtran_root = libradtran_root.resolve()
    output_root = output_root.resolve()
    if output_root.is_symlink():
        raise VisibilityAltitudePressureProbeError(
            "output root must not be a symlink"
        )
    if max_new_runs is not None and max_new_runs <= 0:
        raise VisibilityAltitudePressureProbeError(
            "max-new-runs must be positive"
        )
    if (
        not source_archive.is_file()
        or source_archive.stat().st_size
        != spec["libradtran_source"]["archive_bytes"]
        or _sha256_file(source_archive)
        != spec["libradtran_source"]["archive_sha256"]
    ):
        raise VisibilityAltitudePressureProbeError(
            "source archive receipt differs"
        )
    if not libradtran_root.is_dir():
        raise VisibilityAltitudePressureProbeError("libRadtran root is missing")
    data_root = (libradtran_root / "data").resolve()
    uvspec = (libradtran_root / "bin" / "uvspec").resolve()
    if (
        not data_root.is_dir()
        or not uvspec.is_file()
        or _sha256_file(uvspec)
        != spec["libradtran_source"]["uvspec_sha256"]
    ):
        raise VisibilityAltitudePressureProbeError(
            "built libRadtran identity differs"
        )
    version = subprocess.run(
        [str(uvspec), "--version"],
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    version_text = (version.stdout or version.stderr).strip()
    if (
        version.returncode != 0
        or spec["libradtran_source"]["uvspec_version"] not in version_text
    ):
        raise VisibilityAltitudePressureProbeError("uvspec version differs")

    predecessor_declarations = _parse_declared_predecessor(spec["predecessor"])
    predecessor_paths = {
        label: _verify_declared_repo_file(receipt, f"predecessor {label}")
        for label, receipt in predecessor_declarations.items()
    }
    dependency_path = _verify_declared_repo_file(
        spec["construction_dependency"],
        "construction dependency",
    )
    dependency = _load_construction_dependency(dependency_path)
    vertical_grid_predecessor_path = _verify_declared_repo_file(
        spec["vertical_grid_predecessor"],
        "vertical-grid predecessor",
    )
    refinement_declarations = _parse_declared_refinements(
        spec["refinement_from_failed_designs"]
    )
    refinement_paths = [
        _verify_declared_repo_file(
            declaration,
            f"failed-design receipt {index}",
        )
        for index, declaration in enumerate(refinement_declarations)
    ]
    refinement_receipts = [
        _file_receipt(path, relative_to=REPO_ROOT)
        for path in refinement_paths
    ]
    source_paths = [
        _verify_declared_source_file(
            libradtran_root,
            receipt,
            f"source file {receipt['path']}",
        )
        for receipt in spec["libradtran_source"]["source_files"]
    ]
    profile_source_paths = [
        _verify_declared_source_file(
            libradtran_root,
            receipt,
            f"atmosphere profile {name}",
        )
        for name, receipt in spec["atmosphere_profiles"].items()
    ]
    if not VALIDATOR_PATH.is_file():
        raise VisibilityAltitudePressureProbeError(
            "independent validator is missing"
        )
    tooling_paths = {
        "spec": spec_path,
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH.resolve(),
        "construction_dependency": dependency_path,
    }
    tooling = {
        label: _file_receipt(path, relative_to=REPO_ROOT)
        for label, path in tooling_paths.items()
    }
    predecessor_receipts = {
        label: _file_receipt(path, relative_to=REPO_ROOT)
        for label, path in predecessor_paths.items()
    }
    source_receipts = [
        _file_receipt(path, relative_to=libradtran_root)
        for path in source_paths
    ]
    profile_source_receipts = [
        _file_receipt(path, relative_to=libradtran_root)
        for path in profile_source_paths
    ]
    generation_fingerprint = _sha256_bytes(
        _compact_json_bytes(
            {
                "tooling": tooling,
                "predecessor": predecessor_receipts,
                "vertical_grid_predecessor": _file_receipt(
                    vertical_grid_predecessor_path,
                    relative_to=REPO_ROOT,
                ),
                "refinements": refinement_receipts,
                "source_archive": _file_receipt(source_archive),
                "uvspec": _file_receipt(
                    uvspec,
                    relative_to=libradtran_root,
                ),
                "source_files": source_receipts,
                "atmosphere_profiles": profile_source_receipts,
            }
        )
    )

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / MANIFEST_NAME
    if manifest_path.exists():
        raise VisibilityAltitudePressureProbeError(
            "artifact manifest already exists; artifacts are immutable"
        )
    allowed_root_entries = {
        spec["artifact"]["profiles_directory"],
        spec["artifact"]["runs_directory"],
    }
    unexpected = sorted(
        entry.name
        for entry in output_root.iterdir()
        if entry.name not in allowed_root_entries
    )
    if unexpected:
        raise VisibilityAltitudePressureProbeError(
            "output root contains unowned entries: " + ", ".join(unexpected)
        )
    profiles, profile_receipts = _prepare_profiles(
        output_root=output_root,
        libradtran_root=libradtran_root,
        spec=spec,
        dependency=dependency,
    )
    runs = expand_runs(spec, profiles)
    runs_root = output_root / spec["artifact"]["runs_directory"]
    runs_root.mkdir(exist_ok=True)
    expected_run_ids = {run["run_id"] for run in runs}
    unexpected_runs = sorted(
        entry.name
        for entry in runs_root.iterdir()
        if entry.name not in expected_run_ids
    )
    if unexpected_runs:
        raise VisibilityAltitudePressureProbeError(
            "runs directory contains unowned entries: "
            + ", ".join(unexpected_runs[:10])
        )

    new_run_count = 0
    results: dict[str, list[dict[str, float]]] = {}
    for run in runs:
        run_dir = runs_root / run["run_id"]
        existed = run_dir.exists()
        if (
            not existed
            and max_new_runs is not None
            and new_run_count >= max_new_runs
        ):
            continue
        results[run["run_id"]] = _write_run(
            runs_root=runs_root,
            uvspec=uvspec,
            data_root=data_root,
            run=run,
            spec=spec,
            profile=profiles[(run["profile"], run["observer_altitude_m"])],
            dependency=dependency,
        )
        if not existed:
            new_run_count += 1

    if len(results) != len(runs):
        return {
            "status": "partial_resumable_artifact",
            "output": str(output_root),
            "total_run_count": len(runs),
            "completed_run_count": len(results),
            "new_run_count": new_run_count,
            "remaining_run_count": len(runs) - len(results),
            "generation_fingerprint": generation_fingerprint,
        }

    summary = summarize(runs=runs, results=results, spec=spec)
    summary_path = output_root / SUMMARY_NAME
    summary_path.write_bytes(_canonical_json_bytes(summary))
    run_receipts = [
        _run_receipt(
            output_root,
            runs_root,
            run,
            results[run["run_id"]],
        )
        for run in runs
    ]
    manifest = {
        "schema": spec["artifact"]["schema"],
        "status": ARTIFACT_STATUS,
        "spec_id": spec["spec_id"],
        "generation_fingerprint": generation_fingerprint,
        "runtime_boundary": spec["runtime_boundary"],
        "tooling": tooling,
        "predecessor": predecessor_receipts,
        "vertical_grid_predecessor": _file_receipt(
            vertical_grid_predecessor_path,
            relative_to=REPO_ROOT,
        ),
        "refinements": refinement_receipts,
        "source": {
            "archive": _file_receipt(source_archive),
            "uvspec": _file_receipt(uvspec, relative_to=libradtran_root),
            "uvspec_version": version_text,
            "source_files": source_receipts,
            "atmosphere_profiles": profile_source_receipts,
        },
        "axes": spec["axes"],
        "fixed_environment": spec["fixed_environment"],
        "pressure_o4_closure": spec["pressure_o4_closure"],
        "site_relative_vertical_grid": spec["site_relative_vertical_grid"],
        "direct_solver": spec["direct_solver"],
        "interpolation_admission": spec["interpolation_admission"],
        "profiles": profile_receipts,
        "runs": run_receipts,
        "summary": _file_receipt(summary_path, relative_to=output_root),
    }
    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    validation = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--spec",
            str(spec_path),
            str(output_root),
        ],
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if validation.returncode != 0:
        manifest_path.unlink(missing_ok=True)
        summary_path.unlink(missing_ok=True)
        raise VisibilityAltitudePressureProbeError(
            "independent validation failed:\n"
            + validation.stdout
            + validation.stderr
        )
    return {
        "status": "complete_validated_artifact",
        "output": str(output_root),
        "run_count": len(runs),
        "generation_fingerprint": generation_fingerprint,
        "manifest_sha256": _sha256_file(manifest_path),
        "summary": summary,
    }


def inspect_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(path)
    profile_count = len(spec["atmosphere_profiles"])
    altitude_count = len(_all_axis_values(spec["axes"]["observer_altitude_m"]))
    pressure_count = len(_all_axis_values(spec["axes"]["pressure_ratio"]))
    target_count = len(spec["axes"]["target_true_altitude_deg"])
    return {
        "spec_id": spec["spec_id"],
        "profile_count": profile_count,
        "maximum_unfiltered_run_count": (
            profile_count * altitude_count * pressure_count * target_count
        ),
        "wavelength_count_per_run": len(spec["axes"]["wavelength_nm"]),
        "hard_pressure_filter_applied_during_expansion": True,
        "runtime_boundary": spec["runtime_boundary"],
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or inspect the Phase 1 altitude/pressure interpolation probe."
        )
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--inspect-spec", action="store_true")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--libradtran-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-new-runs", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.inspect_spec:
            print(json.dumps(inspect_spec(args.spec), indent=2, sort_keys=True))
            return 0
        missing = [
            name
            for name in ("source_archive", "libradtran_root", "output")
            if getattr(args, name) is None
        ]
        if missing:
            raise VisibilityAltitudePressureProbeError(
                "missing required build arguments: " + ", ".join(missing)
            )
        result = build_artifact(
            spec_path=args.spec,
            source_archive=args.source_archive,
            libradtran_root=args.libradtran_root,
            output_root=args.output,
            max_new_runs=args.max_new_runs,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except VisibilityAltitudePressureProbeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
