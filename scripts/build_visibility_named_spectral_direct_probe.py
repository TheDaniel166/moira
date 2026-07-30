#!/usr/bin/env python3
"""Build the Phase 1 named-atmosphere full-spectral direct probe.

This laboratory remains outside Moira's runtime dependency graph.  It binds an
official external REPTRAN module, exercises all six AFGL named atmospheres,
measures the 290-level candidate against independently refined vertical grids,
and keeps REPTRAN resolution error separate from vertical-grid error.

The bulk matrix uses ``twostr`` only for the direct-beam channel.  Selected
anchors are rerun with the frozen 16-stream DISORT configuration and must
produce byte-identical stdout before the artifact can close.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SPEC_PATH = (
    SCRIPT_ROOT
    / "visibility_reference_lab"
    / "phase1_named_spectral_direct_probe_spec.json"
)
BASE_BUILDER_PATH = SCRIPT_ROOT / "build_visibility_radiance_lut.py"
VALIDATOR_PATH = SCRIPT_ROOT / "validate_visibility_named_spectral_direct_probe.py"

SPEC_SCHEMA = "moira.visibility-named-spectral-direct-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-named-spectral-direct-probe-artifact/v1"
RUN_SCHEMA = "moira.visibility-named-spectral-direct-probe-run/v1"
ARTIFACT_STATUS = "phase1_named_spectral_direct_evidence_not_runtime_data_pack"
DATA_LINK_NAME = "libradtran_data"
EXTERNAL_RECEIPTS_NAME = "external-data-files.json"
MANIFEST_NAME = "artifact-manifest.json"
RUN_FILES = frozenset(
    {
        "input.inp",
        "randomseed",
        "result.json",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    }
)
_SPECTRUM_LINE = re.compile(
    r"^\s*([0-9]+(?:\.[0-9]+)?)\s+"
    r"([+\-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[eE][+\-]?[0-9]+)\s*$"
)


def _load_base_lab() -> Any:
    module_spec = importlib.util.spec_from_file_location(
        "_moira_visibility_reference_lab_named_spectral",
        BASE_BUILDER_PATH,
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load checkpoint-one builder: {BASE_BUILDER_PATH}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


base_lab = _load_base_lab()
VisibilityLabError = base_lab.VisibilityLabError


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


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisibilityLabError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VisibilityLabError(f"{label} must be an array")
    return value


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


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VisibilityLabError(f"{label} must be a nonempty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise VisibilityLabError(f"{label} must be safe and canonical")
    return value


def _safe_repo_path(value: Any, label: str) -> Path:
    return REPO_ROOT / _safe_relative_path(value, label)


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise VisibilityLabError(f"{label} must be a lowercase SHA-256")
    return value


def _verify_declared_repo_file(
    declaration: dict[str, Any],
    role: str,
) -> Path:
    path = _safe_repo_path(declaration.get(f"{role}_path"), role)
    expected_bytes = declaration.get(f"{role}_bytes")
    expected_sha256 = _validate_sha256(
        declaration.get(f"{role}_sha256"),
        f"{role}_sha256",
    )
    if not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise VisibilityLabError(f"{role}_bytes must be a positive integer")
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != expected_bytes
        or base_lab.sha256_file(path) != expected_sha256
    ):
        raise VisibilityLabError(f"declared predecessor identity differs: {path}")
    return path


def _validate_source_receipt(receipt: Any) -> dict[str, Any]:
    item = _require_dict(receipt, "governing source receipt")
    _safe_relative_path(item.get("path"), "governing source receipt path")
    if not isinstance(item.get("bytes"), int) or item["bytes"] <= 0:
        raise VisibilityLabError("governing source receipt bytes are invalid")
    _validate_sha256(item.get("sha256"), "governing source receipt sha256")
    if set(item) != {"path", "bytes", "sha256"}:
        raise VisibilityLabError("governing source receipt shape differs")
    return item


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibilityLabError(f"cannot read probe specification: {path}") from exc
    if not isinstance(payload, dict):
        raise VisibilityLabError("probe specification must be a JSON object")
    validate_spec(payload)
    return payload


def _decimal_levels(
    segments: list[Any],
    *,
    divisor: int,
) -> list[float]:
    if divisor not in {1, 2, 4}:
        raise VisibilityLabError("vertical-grid step divisor is not admitted")
    levels: list[Decimal] = []
    previous_stop: Decimal | None = None
    for index, raw_segment in enumerate(segments):
        segment = _require_dict(raw_segment, f"vertical segment {index}")
        if set(segment) != {"start", "stop", "step"}:
            raise VisibilityLabError("vertical-grid segment shape differs")
        start = Decimal(
            str(_require_number(segment["start"], "segment start", 0.0, 120.0))
        )
        stop = Decimal(
            str(_require_number(segment["stop"], "segment stop", 0.0, 120.0))
        )
        base_step = Decimal(
            str(_require_number(segment["step"], "segment step", 0.001, 10.0))
        )
        step = base_step / Decimal(divisor)
        if start >= stop or (stop - start) % step != 0:
            raise VisibilityLabError("vertical-grid segment is not exactly divisible")
        if previous_stop is not None and start != previous_stop:
            raise VisibilityLabError("vertical-grid segments are not contiguous")
        count = int((stop - start) / step)
        for offset in range(count + 1):
            value = start + Decimal(offset) * step
            if not levels or value != levels[-1]:
                levels.append(value)
        previous_stop = stop
    if not levels or levels[0] != 0 or levels[-1] != 120:
        raise VisibilityLabError("vertical-grid domain must be exactly 0-120 km")
    return [float(value) for value in levels]


def vertical_grids(spec: dict[str, Any]) -> dict[str, list[float] | None]:
    section = _require_dict(spec.get("vertical_grids"), "vertical_grids")
    expected_ids = {
        "source_native",
        "near_horizon_piecewise_refined_v1",
        "near_horizon_piecewise_reference_v1",
        "near_horizon_piecewise_convergence_v1",
        "base_segments_km",
    }
    if set(section) != expected_ids:
        raise VisibilityLabError("vertical-grid inventory differs")
    segments = _require_list(section["base_segments_km"], "base_segments_km")
    result: dict[str, list[float] | None] = {"source_native": None}
    for grid_id in (
        "near_horizon_piecewise_refined_v1",
        "near_horizon_piecewise_reference_v1",
        "near_horizon_piecewise_convergence_v1",
    ):
        declaration = _require_dict(section[grid_id], grid_id)
        divisor = declaration.get("step_divisor")
        if not isinstance(divisor, int):
            raise VisibilityLabError(f"{grid_id} step_divisor must be an integer")
        levels = _decimal_levels(segments, divisor=divisor)
        if len(levels) != declaration.get("expected_level_count"):
            raise VisibilityLabError(f"{grid_id} level count differs")
        result[grid_id] = levels
    source = _require_dict(section["source_native"], "source_native")
    if (
        source.get("atm_z_grid_emitted") is not False
        or source.get("expected_level_count") != 50
    ):
        raise VisibilityLabError("source-native grid declaration differs")
    return result


def _profile_declarations(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles = _require_dict(spec.get("profiles"), "profiles")
    expected = {
        "tropical",
        "midlatitude_summer",
        "midlatitude_winter",
        "subarctic_summer",
        "subarctic_winter",
        "us_standard",
    }
    if set(profiles) != expected:
        raise VisibilityLabError("named AFGL profile inventory differs")
    codes: set[str] = set()
    paths: set[str] = set()
    for profile_id, raw in profiles.items():
        declaration = _require_dict(raw, f"profile {profile_id}")
        if set(declaration) != {"code", "path"}:
            raise VisibilityLabError(f"profile {profile_id} shape differs")
        code = declaration.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[a-z]{3}", code):
            raise VisibilityLabError(f"profile {profile_id} code is invalid")
        path = _safe_relative_path(
            declaration.get("path"),
            f"profile {profile_id} path",
        )
        if not path.startswith("atmmod/") or not path.endswith(".dat"):
            raise VisibilityLabError(f"profile {profile_id} path is outside atmmod")
        if code in codes or path in paths:
            raise VisibilityLabError("profile codes and paths must be unique")
        codes.add(code)
        paths.add(path)
    return profiles


def _altitude_code(value: float) -> str:
    return f"{value:05.2f}".replace(".", "p")


def _run_id(
    spec: dict[str, Any],
    *,
    profile: str,
    altitude: float,
    grid_id: str,
    resolution: str,
    solver: str,
) -> str:
    profile_code = spec["profiles"][profile]["code"]
    grid_code = spec["vertical_grids"][grid_id]["code"]
    resolution_code = {"medium": "rm", "fine": "rf"}[resolution]
    solver_code = {"twostr": "t2", "disort": "d16"}[solver]
    return (
        f"{profile_code}_a{_altitude_code(altitude)}_"
        f"{grid_code}_{resolution_code}_{solver_code}"
    )


def _vertical_conditions(spec: dict[str, Any]) -> list[tuple[str, float]]:
    matrix = spec["probe_matrix"]
    stress = float(matrix["vertical_profile_stress_altitude_deg"])
    conditions = [(profile, stress) for profile in spec["profiles"]]
    sweep = matrix["vertical_altitude_sweep"]
    conditions.extend(
        (sweep["profile"], float(altitude))
        for altitude in sweep["target_true_altitude_deg"]
    )
    if len(conditions) != len(set(conditions)):
        raise VisibilityLabError("vertical probe conditions are not unique")
    return conditions


def expand_runs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    runs: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
    grids = vertical_grids(spec)

    def add(
        profile: str,
        altitude: float,
        grid_id: str,
        resolution: str,
        solver: str,
        role: str,
    ) -> dict[str, Any]:
        key = (profile, altitude, grid_id, resolution, solver)
        if key not in runs:
            levels = grids[grid_id]
            runs[key] = {
                "run_id": _run_id(
                    spec,
                    profile=profile,
                    altitude=altitude,
                    grid_id=grid_id,
                    resolution=resolution,
                    solver=solver,
                ),
                "profile": profile,
                "atmosphere_path": spec["profiles"][profile]["path"],
                "target_true_altitude_deg": altitude,
                "grid_id": grid_id,
                "grid_level_count": (
                    spec["vertical_grids"][grid_id]["expected_level_count"]
                    if levels is None
                    else len(levels)
                ),
                "REPTRAN_resolution": resolution,
                "rte_solver": solver,
                "roles": [],
            }
        if role not in runs[key]["roles"]:
            runs[key]["roles"].append(role)
            runs[key]["roles"].sort()
        return runs[key]

    matrix = spec["probe_matrix"]
    for profile, altitude in _vertical_conditions(spec):
        for grid_id in matrix["vertical_grid_ids"]:
            add(
                profile,
                altitude,
                grid_id,
                matrix["vertical_resolution"],
                "twostr",
                "vertical_grid_matrix",
            )

    convergence = matrix["reference_convergence_case"]
    add(
        convergence["profile"],
        float(convergence["target_true_altitude_deg"]),
        convergence["grid_id"],
        convergence["resolution"],
        "twostr",
        "reference_convergence",
    )

    transfer = matrix["fine_vertical_transfer_case"]
    for grid_id in transfer["grid_ids"]:
        add(
            transfer["profile"],
            float(transfer["target_true_altitude_deg"]),
            grid_id,
            transfer["resolution"],
            "twostr",
            "fine_vertical_transfer",
        )

    spectral = matrix["spectral_resolution_cases"]
    spectral_conditions = [
        (profile, float(spectral["all_profiles_target_true_altitude_deg"]))
        for profile in spec["profiles"]
    ]
    spectral_conditions.extend(
        ("us_standard", float(altitude))
        for altitude in spectral["us_standard_additional_target_true_altitude_deg"]
    )
    for profile, altitude in spectral_conditions:
        for resolution in spectral["resolutions"]:
            add(
                profile,
                altitude,
                spectral["grid_id"],
                resolution,
                "twostr",
                "spectral_resolution_matrix",
            )

    for parity in matrix["DISORT_parity_cases"]:
        profile = parity["profile"]
        altitude = float(parity["target_true_altitude_deg"])
        grid_id = parity["grid_id"]
        resolution = parity["resolution"]
        add(
            profile,
            altitude,
            grid_id,
            resolution,
            "twostr",
            "DISORT_parity_source",
        )
        add(
            profile,
            altitude,
            grid_id,
            resolution,
            "disort",
            "DISORT_parity_anchor",
        )

    repeat = matrix["repeat_control"]
    original = add(
        repeat["profile"],
        float(repeat["target_true_altitude_deg"]),
        repeat["grid_id"],
        repeat["resolution"],
        repeat["solver"],
        "repeat_source",
    )
    repeated = dict(original)
    repeated["run_id"] = original["run_id"] + "_repeat"
    repeated["roles"] = ["repeat_control"]
    repeated["repeat_of"] = original["run_id"]
    expanded = [*runs.values(), repeated]
    ids = [run["run_id"] for run in expanded]
    if len(ids) != len(set(ids)):
        raise VisibilityLabError("expanded run identifiers collide")
    return expanded


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != SPEC_SCHEMA:
        raise VisibilityLabError("unsupported named-spectral probe schema")
    if (
        spec.get("status") != "research_probe_not_runtime_data_pack"
        or spec.get("spec_id")
        != "physical-heliacal-phase1-named-spectral-direct-probe-2026-07-30"
    ):
        raise VisibilityLabError("named-spectral probe identity differs")

    base_labs = _require_dict(spec.get("base_labs"), "base_labs")
    if set(base_labs) != {"direct_geometry_checkpoint"}:
        raise VisibilityLabError("predecessor lab inventory differs")
    predecessor = _require_dict(
        base_labs["direct_geometry_checkpoint"],
        "direct_geometry_checkpoint",
    )
    if set(predecessor) != {
        f"{role}_{field}"
        for role in ("spec", "builder", "validator", "checkpoint")
        for field in ("path", "bytes", "sha256")
    }:
        raise VisibilityLabError("predecessor identity shape differs")

    source = _require_dict(spec.get("source"), "source")
    if set(source) != {
        "libRadtran",
        "REPTRAN_module",
        "merged_data_root",
        "governing_files",
    }:
        raise VisibilityLabError("source identity shape differs")
    libradtran = _require_dict(source["libRadtran"], "libRadtran")
    reptran = _require_dict(source["REPTRAN_module"], "REPTRAN_module")
    merged = _require_dict(source["merged_data_root"], "merged_data_root")
    if (
        libradtran.get("version") != "2.0.6"
        or libradtran.get("archive_bytes") != 154147176
        or libradtran.get("archive_sha256")
        != "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
        or libradtran.get("uvspec_sha256")
        != "d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a"
    ):
        raise VisibilityLabError("libRadtran identity differs")
    if (
        reptran.get("archive_bytes") != 698709957
        or reptran.get("archive_sha256")
        != "55893c80bcc999651bac3bf014ee64aaf602653ba640eb5bebe787a5d8eacce7"
        or reptran.get("archive_member_count") != 292
        or reptran.get("archive_regular_file_count") != 292
        or reptran.get("embedded_notice_or_license_file_count") != 0
    ):
        raise VisibilityLabError("REPTRAN module identity differs")
    if (
        merged.get("regular_file_count") != 1478
        or merged.get("regular_file_bytes") != 873635625
        or merged.get("canonical_file_receipts_bytes") != 204827
        or merged.get("canonical_file_receipts_sha256")
        != "68f1817782e424ef617dab03ad985a3fbcb91fa2ed0239a8c2de1e8cb6855b59"
    ):
        raise VisibilityLabError("merged data-root identity differs")
    governing = _require_list(source["governing_files"], "governing_files")
    if len(governing) != 6:
        raise VisibilityLabError("governing source-file count differs")
    for receipt in governing:
        _validate_source_receipt(receipt)

    boundary = _require_dict(spec.get("runtime_boundary"), "runtime_boundary")
    false_fields = (
        "engine_changes_authorized",
        "public_api_changes_authorized",
        "runtime_table_authorized",
        "runtime_dependency_on_libRadtran",
        "runtime_dependency_on_REPTRAN",
        "network_dependency",
    )
    if any(boundary.get(field) is not False for field in false_fields):
        raise VisibilityLabError("runtime boundary authorizes an inadmissible change")

    scientific = _require_dict(
        spec.get("scientific_boundary"),
        "scientific_boundary",
    )
    if (
        scientific.get("quantity")
        != "clear_molecular_atmosphere_direct_spectral_transmission"
        or scientific.get("ambiguity_policy")
        != "fail_closed_and_keep_unadmitted_dimensions_open"
        or "aerosol" not in scientific.get("excluded", [])
        or "CIE_response_integration" not in scientific.get("excluded", [])
    ):
        raise VisibilityLabError("scientific boundary differs")

    _profile_declarations(spec)
    grids = vertical_grids(spec)
    if {
        grid_id: (
            spec["vertical_grids"][grid_id]["expected_level_count"]
            if levels is None
            else len(levels)
        )
        for grid_id, levels in grids.items()
    } != {
        "source_native": 50,
        "near_horizon_piecewise_refined_v1": 290,
        "near_horizon_piecewise_reference_v1": 579,
        "near_horizon_piecewise_convergence_v1": 1157,
    }:
        raise VisibilityLabError("vertical-grid level counts differ")

    spectral = _require_dict(spec.get("spectral_design"), "spectral_design")
    if (
        spectral.get("wavelength_start_nm") != 380.0
        or spectral.get("wavelength_stop_nm") != 780.0
        or spectral.get("output_grid_step_nm") != 0.05
        or spectral.get("expected_output_row_count") != 8001
        or spectral.get("diagnostic_bin_width_nm") != [1.0, 5.0, 20.0]
        or spectral.get("REPTRAN_resolutions", {}).get("fine", {}).get("role")
        != "admitted_full_spectral_reference"
    ):
        raise VisibilityLabError("spectral design differs")
    _safe_relative_path(spectral.get("solar_source_path"), "solar source path")

    solver = _require_dict(spec.get("solver"), "solver")
    if (
        solver.get("governing_solver") != "disort"
        or solver.get("governing_geometry") != "pseudospherical"
        or solver.get("governing_number_of_streams") != 16
        or solver.get("bulk_direct_beam_accelerator") != "twostr"
        or solver.get("output_columns") != ["lambda", "edir"]
        or solver.get("random_seed") != 49979687
    ):
        raise VisibilityLabError("solver contract differs")

    matrix = _require_dict(spec.get("probe_matrix"), "probe_matrix")
    if matrix.get("vertical_profile_stress_altitude_deg") != 0.25:
        raise VisibilityLabError("vertical stress altitude differs")
    if matrix.get("vertical_grid_ids") != [
        "source_native",
        "near_horizon_piecewise_refined_v1",
        "near_horizon_piecewise_reference_v1",
    ]:
        raise VisibilityLabError("vertical grid matrix differs")
    if len(_require_list(matrix.get("DISORT_parity_cases"), "parity cases")) != 4:
        raise VisibilityLabError("DISORT parity case count differs")

    acceptance = _require_dict(spec.get("acceptance"), "acceptance")
    required_acceptance = {
        "spectrum_wavelength_abs_tolerance_nm",
        "direct_transmission_upper_tolerance",
        "opaque_bin_direct_transmission_floor",
        "candidate_vs_reference_max_magnitude_difference_by_bin_nm",
        "reference_vs_convergence_max_magnitude_difference_by_bin_nm",
        "combined_candidate_grid_error_bound_by_bin_nm",
        "fine_candidate_vs_reference_max_magnitude_difference_by_bin_nm",
        "medium_vs_fine_characterization_sanity_cap_by_bin_nm",
        "maximum_opacity_classification_mismatches",
        "DISORT_parity_differing_stdout_line_count",
        "repeat_byte_identity_required",
    }
    if set(acceptance) != required_acceptance:
        raise VisibilityLabError("acceptance shape differs")
    for field in (
        "candidate_vs_reference_max_magnitude_difference_by_bin_nm",
        "reference_vs_convergence_max_magnitude_difference_by_bin_nm",
        "combined_candidate_grid_error_bound_by_bin_nm",
        "fine_candidate_vs_reference_max_magnitude_difference_by_bin_nm",
        "medium_vs_fine_characterization_sanity_cap_by_bin_nm",
    ):
        limits = _require_dict(acceptance[field], field)
        if set(limits) != {"1", "5", "20"}:
            raise VisibilityLabError(f"{field} bin inventory differs")
        for key, value in limits.items():
            _require_number(value, f"{field} {key}", 0.0, 20.0)

    runs = expand_runs(spec)
    if len(runs) != 54:
        raise VisibilityLabError(f"expanded run count differs: {len(runs)}")


def _format_number(value: float) -> str:
    if value == 0.0:
        return "0"
    return format(value, ".15g")


def render_input(
    run: dict[str, Any],
    spec: dict[str, Any],
    levels: list[float] | None,
) -> str:
    spectral = spec["spectral_design"]
    solver = spec["solver"]
    solar_zenith = 90.0 - float(run["target_true_altitude_deg"])
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        f"atmosphere_file {DATA_LINK_NAME}/{run['atmosphere_path']}",
        f"source solar {DATA_LINK_NAME}/{spectral['solar_source_path']}",
        (
            f"wavelength {_format_number(spectral['wavelength_start_nm'])} "
            f"{_format_number(spectral['wavelength_stop_nm'])}"
        ),
        f"mol_abs_param reptran {run['REPTRAN_resolution']}",
    ]
    if levels is not None:
        lines.append("atm_z_grid " + " ".join(_format_number(value) for value in levels))
    lines.extend(
        [
            f"sza {_format_number(solar_zenith)}",
            f"rte_solver {run['rte_solver']}",
            "pseudospherical",
        ]
    )
    if run["rte_solver"] == "disort":
        lines.append(f"number_of_streams {solver['governing_number_of_streams']}")
    lines.extend(
        [
            f"mc_randomseed {solver['random_seed']}",
            "output_quantity transmittance",
            "output_user lambda edir",
            "zout 0",
            "quiet",
        ]
    )
    rendered = "\n".join(lines) + "\n"
    forbidden = (
        "aerosol_",
        "aerosol_default",
        "albedo ",
        "cloud",
        "altitude ",
        "mol_modify",
        "ozone_column",
        "mc_spherical",
    )
    if any(token in rendered for token in forbidden):
        raise VisibilityLabError("controlled input crossed the scientific boundary")
    return rendered


def _parse_afgl_levels(path: Path) -> list[float]:
    levels: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        try:
            levels.append(float(fields[0]))
        except (IndexError, ValueError) as exc:
            raise VisibilityLabError(f"malformed AFGL atmosphere: {path}") from exc
    if len(levels) != 50 or any(a <= b for a, b in zip(levels, levels[1:])):
        raise VisibilityLabError(f"AFGL source levels differ: {path}")
    if levels[0] != 120.0 or levels[-1] != 0.0:
        raise VisibilityLabError(f"AFGL source vertical extent differs: {path}")
    return levels


def parse_spectrum(
    text: str,
    *,
    run: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    wavelengths: list[float] = []
    horizontal: list[float] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _SPECTRUM_LINE.fullmatch(line)
        if match is None:
            raise VisibilityLabError(f"unexpected uvspec stdout line: {line!r}")
        wavelengths.append(float(match.group(1)))
        horizontal.append(float(match.group(2)))
    spectral = spec["spectral_design"]
    expected_count = int(spectral["expected_output_row_count"])
    if len(wavelengths) != expected_count:
        raise VisibilityLabError(
            f"unexpected spectrum row count for {run['run_id']}: {len(wavelengths)}"
        )
    start = float(spectral["wavelength_start_nm"])
    step = float(spectral["output_grid_step_nm"])
    tolerance = float(spec["acceptance"]["spectrum_wavelength_abs_tolerance_nm"])
    for index, wavelength in enumerate(wavelengths):
        expected = start + index * step
        if not math.isclose(wavelength, expected, rel_tol=0.0, abs_tol=tolerance):
            raise VisibilityLabError(
                f"wavelength grid differs for {run['run_id']} at row {index}"
            )
    sine_altitude = math.sin(
        math.radians(float(run["target_true_altitude_deg"]))
    )
    if not sine_altitude > 0:
        raise VisibilityLabError("direct probe requires positive target altitude")
    direct = [value / sine_altitude for value in horizontal]
    upper_tolerance = float(
        spec["acceptance"]["direct_transmission_upper_tolerance"]
    )
    if any(
        not math.isfinite(value)
        or value < 0.0
        or value > 1.0 + upper_tolerance
        for value in direct
    ):
        raise VisibilityLabError(f"direct transmission is out of range: {run['run_id']}")
    return {
        "wavelengths_nm": wavelengths,
        "horizontal_direct_transmittance": horizontal,
        "direct_spectral_transmission": direct,
        "summary": {
            "row_count": len(direct),
            "wavelength_start_nm": wavelengths[0],
            "wavelength_stop_nm": wavelengths[-1],
            "wavelength_step_nm": step,
            "zero_sample_count": sum(value == 0.0 for value in direct),
            "minimum_direct_spectral_transmission": min(direct),
            "maximum_direct_spectral_transmission": max(direct),
        },
    }


def bin_comparison(
    candidate: list[float],
    reference: list[float],
    *,
    bin_width_nm: float,
    spec: dict[str, Any],
) -> dict[str, Any]:
    if len(candidate) != len(reference):
        raise VisibilityLabError("spectral comparison lengths differ")
    spectral = spec["spectral_design"]
    step = float(spectral["output_grid_step_nm"])
    span = float(spectral["wavelength_stop_nm"]) - float(
        spectral["wavelength_start_nm"]
    )
    points_per_bin = int(round(bin_width_nm / step))
    bin_count = int(round(span / bin_width_nm))
    if (
        not math.isclose(points_per_bin * step, bin_width_nm)
        or not math.isclose(bin_count * bin_width_nm, span)
        or len(candidate) != bin_count * points_per_bin + 1
    ):
        raise VisibilityLabError("diagnostic bin does not align to spectral grid")
    floor = float(spec["acceptance"]["opaque_bin_direct_transmission_floor"])
    deltas: list[float] = []
    opacity_mismatches = 0
    opaque_both = 0
    maximum = -1.0
    maximum_start = 0.0
    candidate_mean_sum = 0.0
    reference_mean_sum = 0.0
    start_nm = float(spectral["wavelength_start_nm"])
    for bin_index in range(bin_count):
        offset = bin_index * points_per_bin
        candidate_mean = math.fsum(
            candidate[offset : offset + points_per_bin]
        ) / points_per_bin
        reference_mean = math.fsum(
            reference[offset : offset + points_per_bin]
        ) / points_per_bin
        candidate_mean_sum += candidate_mean
        reference_mean_sum += reference_mean
        candidate_opaque = candidate_mean <= floor
        reference_opaque = reference_mean <= floor
        if candidate_opaque and reference_opaque:
            opaque_both += 1
            continue
        if candidate_opaque != reference_opaque:
            opacity_mismatches += 1
            continue
        delta = abs(-2.5 * math.log10(candidate_mean / reference_mean))
        deltas.append(delta)
        if delta > maximum:
            maximum = delta
            maximum_start = start_nm + bin_index * bin_width_nm
    if not deltas:
        raise VisibilityLabError("spectral comparison has no evaluable bins")
    ordered = sorted(deltas)

    def quantile(fraction: float) -> float:
        index = math.floor((len(ordered) - 1) * fraction)
        return ordered[index]

    overall = abs(
        -2.5 * math.log10(candidate_mean_sum / reference_mean_sum)
    )
    return {
        "bin_width_nm": bin_width_nm,
        "evaluated_bin_count": len(deltas),
        "both_opaque_bin_count": opaque_both,
        "opacity_classification_mismatch_count": opacity_mismatches,
        "overall_mean_magnitude_difference": overall,
        "p95_magnitude_difference": quantile(0.95),
        "p99_magnitude_difference": quantile(0.99),
        "maximum_magnitude_difference": maximum,
        "maximum_bin_start_nm": maximum_start,
    }


def _run_key(
    *,
    profile: str,
    altitude: float,
    grid_id: str,
    resolution: str,
    solver: str,
) -> tuple[Any, ...]:
    return (profile, altitude, grid_id, resolution, solver)


def _run_lookup(runs: Iterable[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for run in runs:
        if "repeat_of" in run:
            continue
        key = _run_key(
            profile=run["profile"],
            altitude=float(run["target_true_altitude_deg"]),
            grid_id=run["grid_id"],
            resolution=run["REPTRAN_resolution"],
            solver=run["rte_solver"],
        )
        if key in result:
            raise VisibilityLabError("nonrepeat run lookup collides")
        result[key] = run
    return result


def _recursive_file_receipts(
    root: Path,
    *,
    exclude: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise VisibilityLabError(f"artifact contains a symlink: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in exclude:
                receipts.append(base_lab.file_receipt(path, relative_to=root))
    return receipts


def _verify_receipts(root: Path, receipts: list[dict[str, Any]]) -> None:
    for receipt in receipts:
        path = root / receipt["path"]
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != receipt["bytes"]
            or base_lab.sha256_file(path) != receipt["sha256"]
        ):
            raise VisibilityLabError(f"file receipt mismatch: {path}")


def external_data_receipts(data_root: Path) -> tuple[list[dict[str, Any]], bytes]:
    if data_root.is_symlink() or not data_root.is_dir():
        raise VisibilityLabError("merged data root must be a real directory")
    receipts = _recursive_file_receipts(data_root)
    return receipts, _compact_json_bytes(receipts)


def _verify_reptran_archive(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    declaration = spec["source"]["REPTRAN_module"]
    resolved = path.resolve()
    if (
        resolved.is_symlink()
        or not resolved.is_file()
        or resolved.stat().st_size != declaration["archive_bytes"]
        or base_lab.sha256_file(resolved) != declaration["archive_sha256"]
    ):
        raise VisibilityLabError("REPTRAN archive identity differs")
    member_names: list[str] = []
    with tarfile.open(resolved, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            member_path = Path(member.name)
            if (
                not member.isfile()
                or member_path.is_absolute()
                or ".." in member_path.parts
                or not member.name.startswith(declaration["archive_prefix"])
            ):
                raise VisibilityLabError("REPTRAN archive member is unsafe")
            member_names.append(member.name)
    if (
        len(members) != declaration["archive_member_count"]
        or len(member_names) != declaration["archive_regular_file_count"]
        or len(member_names) != len(set(member_names))
    ):
        raise VisibilityLabError("REPTRAN archive inventory differs")
    return base_lab.file_receipt(resolved)


def _verify_governing_sources(
    spec: dict[str, Any],
    libradtran_root: Path,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for expected in spec["source"]["governing_files"]:
        path = libradtran_root / expected["path"]
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != expected["bytes"]
            or base_lab.sha256_file(path) != expected["sha256"]
        ):
            raise VisibilityLabError(f"governing libRadtran source differs: {path}")
        receipts.append(dict(expected))
    return receipts


def _run_uvspec(
    *,
    uvspec: Path,
    data_root: Path,
    run_dir: Path,
    input_text: str,
) -> None:
    if not run_dir.is_dir() or any(run_dir.iterdir()):
        raise VisibilityLabError("uvspec run directory must exist and be empty")
    (run_dir / "input.inp").write_text(input_text, encoding="utf-8")
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
        if re.search(r"(?im)(?:^|\s)(?:error|\*\*\*\s*error)\b", completed.stderr):
            raise VisibilityLabError(
                f"uvspec reported a semantic error; preserved at {run_dir}"
            )
    finally:
        if data_link.is_symlink():
            data_link.unlink()
    actual = {path.name for path in run_dir.iterdir()}
    expected = RUN_FILES - {"result.json"}
    if actual != expected:
        raise VisibilityLabError(
            f"uvspec file inventory differs at {run_dir}: "
            f"expected {sorted(expected)}, found {sorted(actual)}"
        )
    if (run_dir / "randomseed").read_text(encoding="utf-8").strip() != "49979687":
        raise VisibilityLabError(f"random-seed receipt differs at {run_dir}")


def _resume_run(
    run_dir: Path,
    *,
    expected_run: dict[str, Any],
    generation_fingerprint: str,
    spec: dict[str, Any],
) -> dict[str, Any] | None:
    result_path = run_dir / "result.json"
    if not result_path.is_file() or result_path.is_symlink():
        return None
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibilityLabError(f"cannot resume run: {run_dir}") from exc
    if (
        not isinstance(result, dict)
        or result.get("schema") != RUN_SCHEMA
        or result.get("generation_fingerprint") != generation_fingerprint
        or result.get("run") != expected_run
    ):
        raise VisibilityLabError(f"stale or mismatched completed run: {run_dir}")
    if {path.name for path in run_dir.iterdir()} != RUN_FILES:
        raise VisibilityLabError(f"completed run inventory differs: {run_dir}")
    receipts = result.get("files")
    if not isinstance(receipts, list):
        raise VisibilityLabError(f"completed run has no file receipts: {run_dir}")
    _verify_receipts(run_dir, receipts)
    parsed = parse_spectrum(
        (run_dir / "stdout.txt").read_text(encoding="utf-8"),
        run=expected_run,
        spec=spec,
    )
    if result.get("spectrum") != parsed["summary"]:
        raise VisibilityLabError(f"completed run summary differs: {run_dir}")
    return result


def _build_run(
    run: dict[str, Any],
    *,
    levels: list[float] | None,
    spec: dict[str, Any],
    generation_fingerprint: str,
    uvspec: Path,
    data_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    final_dir = output_root / run["run_id"]
    resumed = _resume_run(
        final_dir,
        expected_run=run,
        generation_fingerprint=generation_fingerprint,
        spec=spec,
    )
    if resumed is not None:
        return resumed
    if final_dir.exists():
        raise VisibilityLabError(f"partial or stale run directory exists: {final_dir}")
    input_text = render_input(run, spec, levels)
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{run['run_id']}.", dir=output_root)
    )
    try:
        _run_uvspec(
            uvspec=uvspec,
            data_root=data_root,
            run_dir=temp_dir,
            input_text=input_text,
        )
        parsed = parse_spectrum(
            (temp_dir / "stdout.txt").read_text(encoding="utf-8"),
            run=run,
            spec=spec,
        )
        receipts = _recursive_file_receipts(temp_dir)
        result = {
            "schema": RUN_SCHEMA,
            "generation_fingerprint": generation_fingerprint,
            "run": run,
            "spectrum": parsed["summary"],
            "files": receipts,
        }
        (temp_dir / "result.json").write_bytes(base_lab.canonical_json_bytes(result))
        temp_dir.rename(final_dir)
        return result
    except Exception:
        raise


def _spectrum_for_run(
    output_root: Path,
    run: dict[str, Any],
    spec: dict[str, Any],
) -> list[float]:
    parsed = parse_spectrum(
        (output_root / run["run_id"] / "stdout.txt").read_text(encoding="utf-8"),
        run=run,
        spec=spec,
    )
    return parsed["direct_spectral_transmission"]


def _comparison_for_runs(
    output_root: Path,
    candidate: dict[str, Any],
    reference: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    candidate_values = _spectrum_for_run(output_root, candidate, spec)
    reference_values = _spectrum_for_run(output_root, reference, spec)
    return {
        _format_number(width): bin_comparison(
            candidate_values,
            reference_values,
            bin_width_nm=float(width),
            spec=spec,
        )
        for width in spec["spectral_design"]["diagnostic_bin_width_nm"]
    }


def _get_run(
    lookup: dict[tuple[Any, ...], dict[str, Any]],
    *,
    profile: str,
    altitude: float,
    grid_id: str,
    resolution: str,
    solver: str = "twostr",
) -> dict[str, Any]:
    key = _run_key(
        profile=profile,
        altitude=altitude,
        grid_id=grid_id,
        resolution=resolution,
        solver=solver,
    )
    try:
        return lookup[key]
    except KeyError as exc:
        raise VisibilityLabError(f"required run is absent: {key}") from exc


def summarize_comparisons(
    output_root: Path,
    runs: list[dict[str, Any]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    lookup = _run_lookup(runs)
    vertical: list[dict[str, Any]] = []
    for profile, altitude in _vertical_conditions(spec):
        source = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id="source_native",
            resolution="medium",
        )
        candidate = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id="near_horizon_piecewise_refined_v1",
            resolution="medium",
        )
        reference = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id="near_horizon_piecewise_reference_v1",
            resolution="medium",
        )
        vertical.append(
            {
                "profile": profile,
                "target_true_altitude_deg": altitude,
                "source_run_id": source["run_id"],
                "candidate_run_id": candidate["run_id"],
                "reference_run_id": reference["run_id"],
                "source_vs_reference": _comparison_for_runs(
                    output_root,
                    source,
                    reference,
                    spec,
                ),
                "candidate_vs_reference": _comparison_for_runs(
                    output_root,
                    candidate,
                    reference,
                    spec,
                ),
            }
        )

    reference = _get_run(
        lookup,
        profile="us_standard",
        altitude=0.25,
        grid_id="near_horizon_piecewise_reference_v1",
        resolution="medium",
    )
    convergence = _get_run(
        lookup,
        profile="us_standard",
        altitude=0.25,
        grid_id="near_horizon_piecewise_convergence_v1",
        resolution="medium",
    )
    reference_convergence = {
        "reference_run_id": reference["run_id"],
        "convergence_run_id": convergence["run_id"],
        "comparison": _comparison_for_runs(
            output_root,
            reference,
            convergence,
            spec,
        ),
    }

    fine_candidate = _get_run(
        lookup,
        profile="us_standard",
        altitude=0.25,
        grid_id="near_horizon_piecewise_refined_v1",
        resolution="fine",
    )
    fine_reference = _get_run(
        lookup,
        profile="us_standard",
        altitude=0.25,
        grid_id="near_horizon_piecewise_reference_v1",
        resolution="fine",
    )
    fine_vertical = {
        "candidate_run_id": fine_candidate["run_id"],
        "reference_run_id": fine_reference["run_id"],
        "comparison": _comparison_for_runs(
            output_root,
            fine_candidate,
            fine_reference,
            spec,
        ),
    }

    spectral_matrix = spec["probe_matrix"]["spectral_resolution_cases"]
    spectral_conditions = [
        (
            profile,
            float(spectral_matrix["all_profiles_target_true_altitude_deg"]),
        )
        for profile in spec["profiles"]
    ]
    spectral_conditions.extend(
        ("us_standard", float(altitude))
        for altitude in spectral_matrix[
            "us_standard_additional_target_true_altitude_deg"
        ]
    )
    spectral_resolution: list[dict[str, Any]] = []
    for profile, altitude in spectral_conditions:
        medium = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id=spectral_matrix["grid_id"],
            resolution="medium",
        )
        fine = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id=spectral_matrix["grid_id"],
            resolution="fine",
        )
        spectral_resolution.append(
            {
                "profile": profile,
                "target_true_altitude_deg": altitude,
                "medium_run_id": medium["run_id"],
                "fine_run_id": fine["run_id"],
                "medium_vs_fine": _comparison_for_runs(
                    output_root,
                    medium,
                    fine,
                    spec,
                ),
            }
        )

    parity: list[dict[str, Any]] = []
    for anchor in spec["probe_matrix"]["DISORT_parity_cases"]:
        kwargs = {
            "profile": anchor["profile"],
            "altitude": float(anchor["target_true_altitude_deg"]),
            "grid_id": anchor["grid_id"],
            "resolution": anchor["resolution"],
        }
        twostr = _get_run(lookup, **kwargs, solver="twostr")
        disort = _get_run(lookup, **kwargs, solver="disort")
        twostr_bytes = (
            output_root / twostr["run_id"] / "stdout.txt"
        ).read_bytes()
        disort_bytes = (
            output_root / disort["run_id"] / "stdout.txt"
        ).read_bytes()
        twostr_lines = twostr_bytes.splitlines()
        disort_lines = disort_bytes.splitlines()
        differing = sum(
            left != right
            for left, right in zip(twostr_lines, disort_lines)
        ) + abs(len(twostr_lines) - len(disort_lines))
        parity.append(
            {
                "twostr_run_id": twostr["run_id"],
                "DISORT_run_id": disort["run_id"],
                "stdout_byte_identical": twostr_bytes == disort_bytes,
                "differing_stdout_line_count": differing,
                "stdout_sha256": _sha256_bytes(twostr_bytes),
            }
        )

    repeated = next(run for run in runs if "repeat_of" in run)
    original_dir = output_root / repeated["repeat_of"]
    repeat_dir = output_root / repeated["run_id"]
    repeat_files = (
        "input.inp",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    )
    repeat_receipt = {
        "original_run_id": repeated["repeat_of"],
        "repeat_run_id": repeated["run_id"],
        "files": [
            {
                "path": name,
                "original_sha256": base_lab.sha256_file(original_dir / name),
                "repeat_sha256": base_lab.sha256_file(repeat_dir / name),
                "byte_identical": (
                    (original_dir / name).read_bytes()
                    == (repeat_dir / name).read_bytes()
                ),
            }
            for name in repeat_files
        ],
    }

    widths = [_format_number(value) for value in spec["spectral_design"][
        "diagnostic_bin_width_nm"
    ]]
    maximum_candidate = {
        width: max(
            row["candidate_vs_reference"][width][
                "maximum_magnitude_difference"
            ]
            for row in vertical
        )
        for width in widths
    }
    convergence_error = {
        width: reference_convergence["comparison"][width][
            "maximum_magnitude_difference"
        ]
        for width in widths
    }
    combined_bound = {
        width: maximum_candidate[width] + convergence_error[width]
        for width in widths
    }
    maxima = {
        "candidate_vs_reference_by_bin_nm": maximum_candidate,
        "reference_vs_convergence_by_bin_nm": convergence_error,
        "combined_candidate_grid_error_bound_by_bin_nm": combined_bound,
        "fine_candidate_vs_reference_by_bin_nm": {
            width: fine_vertical["comparison"][width][
                "maximum_magnitude_difference"
            ]
            for width in widths
        },
        "medium_vs_fine_by_bin_nm": {
            width: max(
                row["medium_vs_fine"][width]["maximum_magnitude_difference"]
                for row in spectral_resolution
            )
            for width in widths
        },
        "source_vs_reference_by_bin_nm": {
            width: max(
                row["source_vs_reference"][width][
                    "maximum_magnitude_difference"
                ]
                for row in vertical
            )
            for width in widths
        },
    }

    result = {
        "vertical_grid_matrix": vertical,
        "reference_convergence": reference_convergence,
        "fine_vertical_transfer": fine_vertical,
        "spectral_resolution_matrix": spectral_resolution,
        "DISORT_parity": parity,
        "fixed_input_repeat": repeat_receipt,
        "maxima": maxima,
    }
    enforce_acceptance(result, spec)
    return result


def enforce_acceptance(summary: dict[str, Any], spec: dict[str, Any]) -> None:
    acceptance = spec["acceptance"]
    maxima = summary["maxima"]
    mapping = (
        (
            "candidate_vs_reference_by_bin_nm",
            "candidate_vs_reference_max_magnitude_difference_by_bin_nm",
        ),
        (
            "reference_vs_convergence_by_bin_nm",
            "reference_vs_convergence_max_magnitude_difference_by_bin_nm",
        ),
        (
            "combined_candidate_grid_error_bound_by_bin_nm",
            "combined_candidate_grid_error_bound_by_bin_nm",
        ),
        (
            "fine_candidate_vs_reference_by_bin_nm",
            "fine_candidate_vs_reference_max_magnitude_difference_by_bin_nm",
        ),
        (
            "medium_vs_fine_by_bin_nm",
            "medium_vs_fine_characterization_sanity_cap_by_bin_nm",
        ),
    )
    for result_field, limit_field in mapping:
        for width, value in maxima[result_field].items():
            if value > float(acceptance[limit_field][width]):
                raise VisibilityLabError(
                    f"{result_field} exceeds the {width} nm acceptance limit"
                )
    mismatch_limit = int(
        acceptance["maximum_opacity_classification_mismatches"]
    )

    def comparisons(value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, dict):
            if "opacity_classification_mismatch_count" in value:
                yield value
            for child in value.values():
                yield from comparisons(child)
        elif isinstance(value, list):
            for child in value:
                yield from comparisons(child)

    if any(
        item["opacity_classification_mismatch_count"] > mismatch_limit
        for item in comparisons(
            {
                "vertical": summary["vertical_grid_matrix"],
                "convergence": summary["reference_convergence"],
                "fine": summary["fine_vertical_transfer"],
                "spectral": summary["spectral_resolution_matrix"],
            }
        )
    ):
        raise VisibilityLabError("spectral comparison changes opacity classification")
    parity_limit = int(
        acceptance["DISORT_parity_differing_stdout_line_count"]
    )
    if any(
        not item["stdout_byte_identical"]
        or item["differing_stdout_line_count"] > parity_limit
        for item in summary["DISORT_parity"]
    ):
        raise VisibilityLabError("twostr direct output differs from DISORT")
    if (
        acceptance["repeat_byte_identity_required"]
        and not all(
            item["byte_identical"]
            for item in summary["fixed_input_repeat"]["files"]
        )
    ):
        raise VisibilityLabError("fixed-input repeat is not byte-identical")


def _run_contract(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": spec["source"],
        "runtime_boundary": spec["runtime_boundary"],
        "scientific_boundary": spec["scientific_boundary"],
        "profiles": spec["profiles"],
        "vertical_grids": spec["vertical_grids"],
        "spectral_design": spec["spectral_design"],
        "solver": spec["solver"],
        "probe_matrix": spec["probe_matrix"],
    }


def _checkpoint1_paths(
    predecessor_spec_path: Path,
) -> dict[str, Path]:
    predecessor = json.loads(predecessor_spec_path.read_text(encoding="utf-8"))
    declaration = predecessor["base_labs"]["checkpoint1"]
    paths: dict[str, Path] = {}
    for role in ("spec", "builder", "validator"):
        path = _safe_repo_path(
            declaration[f"{role}_path"],
            f"checkpoint1 {role}",
        )
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != declaration[f"{role}_bytes"]
            or base_lab.sha256_file(path) != declaration[f"{role}_sha256"]
        ):
            raise VisibilityLabError(
                f"checkpoint-one {role} identity differs"
            )
        paths[role] = path
    if paths["builder"].resolve() != BASE_BUILDER_PATH.resolve():
        raise VisibilityLabError("imported checkpoint-one builder path differs")
    return paths


def build_artifact(
    *,
    spec_path: Path,
    source_archive: Path,
    reptran_archive: Path,
    libradtran_root: Path,
    data_root: Path,
    output_root: Path,
    max_new_runs: int | None = None,
) -> dict[str, Any]:
    spec_bytes = spec_path.read_bytes()
    spec = load_spec(spec_path)
    if max_new_runs is not None and max_new_runs <= 0:
        raise VisibilityLabError("max_new_runs must be positive")
    predecessor_decl = spec["base_labs"]["direct_geometry_checkpoint"]
    predecessor_paths = {
        role: _verify_declared_repo_file(predecessor_decl, role)
        for role in ("spec", "builder", "validator", "checkpoint")
    }
    checkpoint1_paths = _checkpoint1_paths(predecessor_paths["spec"])

    output_root = output_root.resolve()
    if output_root.is_symlink():
        raise VisibilityLabError("output root must not be a symlink")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / MANIFEST_NAME
    if manifest_path.exists():
        raise VisibilityLabError(
            f"artifact manifest already exists; choose a new output root: {manifest_path}"
        )

    tooling_paths = {
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH.resolve(),
        **{f"predecessor_{role}": path for role, path in predecessor_paths.items()},
        **{
            f"checkpoint1_{role}": path
            for role, path in checkpoint1_paths.items()
        },
    }
    for role, path in tooling_paths.items():
        if path.is_symlink() or not path.is_file():
            raise VisibilityLabError(f"required tooling file is missing: {role}")
    tooling = {
        role: base_lab.file_receipt(path, relative_to=REPO_ROOT)
        for role, path in tooling_paths.items()
    }
    specifications = {
        "named_spectral_direct_probe": base_lab.file_receipt(
            spec_path.resolve(),
            relative_to=REPO_ROOT,
        ),
        "direct_geometry_checkpoint": tooling["predecessor_spec"],
    }

    libradtran_root = libradtran_root.resolve()
    checkpoint1_path = checkpoint1_paths["spec"]
    checkpoint1_spec = json.loads(checkpoint1_path.read_text(encoding="utf-8"))
    base_lab.validate_spec(checkpoint1_spec)
    generator = base_lab.verify_generator(
        checkpoint1_spec,
        source_archive=source_archive,
        libradtran_root=libradtran_root,
    )
    if generator["uvspec_sha256"] != spec["source"]["libRadtran"][
        "uvspec_sha256"
    ]:
        raise VisibilityLabError("uvspec executable identity differs")
    governing_sources = _verify_governing_sources(spec, libradtran_root)
    reptran_receipt = _verify_reptran_archive(reptran_archive, spec)

    data_root = data_root.resolve()
    data_receipts, data_receipts_bytes = external_data_receipts(data_root)
    merged = spec["source"]["merged_data_root"]
    if (
        len(data_receipts) != merged["regular_file_count"]
        or sum(item["bytes"] for item in data_receipts)
        != merged["regular_file_bytes"]
        or len(data_receipts_bytes) != merged["canonical_file_receipts_bytes"]
        or _sha256_bytes(data_receipts_bytes)
        != merged["canonical_file_receipts_sha256"]
    ):
        raise VisibilityLabError("merged REPTRAN data-root receipt differs")
    external_receipts_path = output_root / EXTERNAL_RECEIPTS_NAME
    if external_receipts_path.exists():
        if (
            external_receipts_path.is_symlink()
            or external_receipts_path.read_bytes() != data_receipts_bytes
        ):
            raise VisibilityLabError("persisted external-data receipt differs")
    else:
        external_receipts_path.write_bytes(data_receipts_bytes)

    source_levels = {
        profile: _parse_afgl_levels(data_root / declaration["path"])
        for profile, declaration in spec["profiles"].items()
    }
    if any(len(levels) != 50 for levels in source_levels.values()):
        raise VisibilityLabError("named atmosphere source-grid count differs")

    environment = base_lab.environment_receipt()
    bound_generator = {
        **generator,
        "governing_source_files": governing_sources,
        "REPTRAN_archive": reptran_receipt,
        "merged_data_root": {
            **merged,
            "receipt_file": EXTERNAL_RECEIPTS_NAME,
        },
        "named_atmosphere_source_levels": {
            profile: {
                "path": spec["profiles"][profile]["path"],
                "level_count": len(levels),
                "levels_km_descending": levels,
            }
            for profile, levels in source_levels.items()
        },
    }
    execution_tooling_roles = (
        "builder",
        "predecessor_spec",
        "checkpoint1_spec",
        "checkpoint1_builder",
    )
    execution_tooling = {
        role: tooling[role]
        for role in execution_tooling_roles
    }
    generation_identity = {
        "execution_tooling": execution_tooling,
        "run_contract_sha256": _sha256_bytes(
            base_lab.canonical_json_bytes(_run_contract(spec))
        ),
        "generator": bound_generator,
        "environment": environment,
    }
    generation_fingerprint = _sha256_bytes(
        base_lab.canonical_json_bytes(generation_identity)
    )

    runs = expand_runs(spec)
    allowed_entries = {
        EXTERNAL_RECEIPTS_NAME,
        *(run["run_id"] for run in runs),
    }
    unexpected = sorted(
        entry.name for entry in output_root.iterdir()
        if entry.name not in allowed_entries
    )
    if unexpected:
        raise VisibilityLabError(
            "output root contains unowned or partial entries: "
            + ", ".join(unexpected)
        )

    grids = vertical_grids(spec)
    uvspec = libradtran_root / "bin" / "uvspec"
    results: list[dict[str, Any]] = []
    newly_built = 0
    for index, run in enumerate(runs, start=1):
        existing = _resume_run(
            output_root / run["run_id"],
            expected_run=run,
            generation_fingerprint=generation_fingerprint,
            spec=spec,
        )
        if existing is not None:
            results.append(existing)
            continue
        if max_new_runs is not None and newly_built >= max_new_runs:
            break
        result = _build_run(
            run,
            levels=grids[run["grid_id"]],
            spec=spec,
            generation_fingerprint=generation_fingerprint,
            uvspec=uvspec,
            data_root=data_root,
            output_root=output_root,
        )
        results.append(result)
        newly_built += 1
        print(
            f"completed {index}/{len(runs)} {run['run_id']}",
            flush=True,
        )

    completed_ids = {
        entry.name
        for entry in output_root.iterdir()
        if entry.is_dir() and (entry / "result.json").is_file()
    }
    expected_ids = {run["run_id"] for run in runs}
    if completed_ids != expected_ids:
        return {
            "complete": False,
            "spec_id": spec["spec_id"],
            "generation_fingerprint": generation_fingerprint,
            "completed_run_count": len(completed_ids),
            "remaining_run_count": len(expected_ids - completed_ids),
            "newly_built_run_count": newly_built,
            "artifact_manifest_written": False,
        }

    results = [
        _resume_run(
            output_root / run["run_id"],
            expected_run=run,
            generation_fingerprint=generation_fingerprint,
            spec=spec,
        )
        for run in runs
    ]
    if any(result is None for result in results):
        raise VisibilityLabError("completed run could not be resumed")
    typed_results = [result for result in results if result is not None]
    summary = summarize_comparisons(output_root, runs, spec)

    if spec_path.read_bytes() != spec_bytes:
        raise VisibilityLabError("probe specification changed during generation")
    for role, path in tooling_paths.items():
        receipt = tooling[role]
        if (
            path.stat().st_size != receipt["bytes"]
            or base_lab.sha256_file(path) != receipt["sha256"]
        ):
            raise VisibilityLabError(f"{role} changed during generation")
    if base_lab.sha256_file(uvspec) != generator["uvspec_sha256"]:
        raise VisibilityLabError("uvspec executable changed during generation")
    _verify_governing_sources(spec, libradtran_root)
    _verify_reptran_archive(reptran_archive, spec)

    run_summaries = [
        {
            "run": result["run"],
            "spectrum": result["spectrum"],
        }
        for result in typed_results
    ]
    files = _recursive_file_receipts(output_root)
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
        "scientific_boundary": spec["scientific_boundary"],
        "run_count": len(runs),
        "twostr_run_count": sum(run["rte_solver"] == "twostr" for run in runs),
        "DISORT_run_count": sum(run["rte_solver"] == "disort" for run in runs),
        "run_summaries": run_summaries,
        "comparisons": summary,
        "files": files,
    }
    manifest_path.write_bytes(base_lab.canonical_json_bytes(manifest))
    return {
        "complete": True,
        "spec_id": spec["spec_id"],
        "generation_fingerprint": generation_fingerprint,
        "completed_run_count": len(runs),
        "remaining_run_count": 0,
        "newly_built_run_count": newly_built,
        "artifact_manifest_written": True,
        "manifest_sha256": base_lab.sha256_file(manifest_path),
        "comparisons": summary["maxima"],
    }


def inspect_spec(spec_path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(spec_path)
    runs = expand_runs(spec)
    grids = vertical_grids(spec)
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "profile_count": len(spec["profiles"]),
        "vertical_condition_count": len(_vertical_conditions(spec)),
        "vertical_grid_level_counts": {
            grid_id: (
                spec["vertical_grids"][grid_id]["expected_level_count"]
                if levels is None
                else len(levels)
            )
            for grid_id, levels in grids.items()
        },
        "spectral_output_row_count": spec["spectral_design"][
            "expected_output_row_count"
        ],
        "run_count": len(runs),
        "twostr_run_count": sum(run["rte_solver"] == "twostr" for run in runs),
        "DISORT_run_count": sum(run["rte_solver"] == "disort" for run in runs),
        "repeat_run_count": sum("repeat_of" in run for run in runs),
        "fine_reference_admitted": True,
        "runtime_data_pack_authorized": False,
        "engine_changes_authorized": False,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or inspect the external Phase 1 named-spectral direct probe."
        )
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--inspect-spec", action="store_true")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--reptran-archive", type=Path)
    parser.add_argument("--libradtran-root", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--max-new-runs", type=int)
    args = parser.parse_args(argv)
    if not args.inspect_spec:
        required = (
            "source_archive",
            "reptran_archive",
            "libradtran_root",
            "data_root",
            "output_root",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            parser.error(
                "build mode requires "
                + ", ".join(f"--{name.replace('_', '-')}" for name in missing)
            )
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.inspect_spec:
            payload = inspect_spec(args.spec)
        else:
            payload = build_artifact(
                spec_path=args.spec,
                source_archive=args.source_archive,
                reptran_archive=args.reptran_archive,
                libradtran_root=args.libradtran_root,
                data_root=args.data_root,
                output_root=args.output_root,
                max_new_runs=args.max_new_runs,
            )
    except (OSError, ValueError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
