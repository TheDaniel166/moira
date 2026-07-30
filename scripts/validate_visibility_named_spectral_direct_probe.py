#!/usr/bin/env python3
"""Independently validate the Phase 1 named-spectral direct artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_named_spectral_direct_probe_spec.json"
)
SPEC_SCHEMA = "moira.visibility-named-spectral-direct-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-named-spectral-direct-probe-artifact/v1"
RUN_SCHEMA = "moira.visibility-named-spectral-direct-probe-run/v1"
ARTIFACT_STATUS = "phase1_named_spectral_direct_evidence_not_runtime_data_pack"
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


class ValidationError(ValueError):
    """Raised when a named-spectral artifact violates its receipt."""


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
        raise ValidationError(f"{label} must be a nonempty path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValidationError(f"{label} must be safe and canonical")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValidationError(f"{label} must be a lowercase SHA-256")
    return value


def _validate_file_receipt(
    root: Path,
    receipt: Any,
    *,
    label: str,
) -> str:
    if not isinstance(receipt, dict) or set(receipt) != {
        "path",
        "bytes",
        "sha256",
    }:
        raise ValidationError(f"{label} receipt shape differs")
    relative = _safe_relative_path(receipt.get("path"), f"{label} path")
    byte_count = receipt.get("bytes")
    sha256 = _validate_sha256(receipt.get("sha256"), f"{label} sha256")
    if not isinstance(byte_count, int) or byte_count < 0:
        raise ValidationError(f"{label} byte count is invalid")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != byte_count
        or _sha256_file(path) != sha256
    ):
        raise ValidationError(f"{label} receipt differs: {path}")
    return relative


def _format_number(value: float) -> str:
    if value == 0.0:
        return "0"
    return format(value, ".15g")


def _altitude_code(value: float) -> str:
    return f"{value:05.2f}".replace(".", "p")


def _decimal_levels(
    segments: list[Any],
    *,
    divisor: int,
) -> list[float]:
    levels: list[Decimal] = []
    previous_stop: Decimal | None = None
    for raw in segments:
        if not isinstance(raw, dict) or set(raw) != {"start", "stop", "step"}:
            raise ValidationError("vertical-grid segment shape differs")
        start = Decimal(str(raw["start"]))
        stop = Decimal(str(raw["stop"]))
        step = Decimal(str(raw["step"])) / Decimal(divisor)
        if start >= stop or (stop - start) % step != 0:
            raise ValidationError("vertical-grid segment is not divisible")
        if previous_stop is not None and start != previous_stop:
            raise ValidationError("vertical-grid segments are not contiguous")
        count = int((stop - start) / step)
        for offset in range(count + 1):
            value = start + Decimal(offset) * step
            if not levels or levels[-1] != value:
                levels.append(value)
        previous_stop = stop
    if not levels or levels[0] != 0 or levels[-1] != 120:
        raise ValidationError("vertical-grid extent differs")
    return [float(value) for value in levels]


def _vertical_grids(spec: dict[str, Any]) -> dict[str, list[float] | None]:
    section = spec["vertical_grids"]
    result: dict[str, list[float] | None] = {"source_native": None}
    for grid_id in (
        "near_horizon_piecewise_refined_v1",
        "near_horizon_piecewise_reference_v1",
        "near_horizon_piecewise_convergence_v1",
    ):
        declaration = section[grid_id]
        levels = _decimal_levels(
            section["base_segments_km"],
            divisor=int(declaration["step_divisor"]),
        )
        if len(levels) != declaration["expected_level_count"]:
            raise ValidationError(f"{grid_id} level count differs")
        result[grid_id] = levels
    return result


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
    return conditions


def expected_runs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    runs: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
    grids = _vertical_grids(spec)

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
    conditions = [
        (profile, float(spectral["all_profiles_target_true_altitude_deg"]))
        for profile in spec["profiles"]
    ]
    conditions.extend(
        ("us_standard", float(altitude))
        for altitude in spectral["us_standard_additional_target_true_altitude_deg"]
    )
    for profile, altitude in conditions:
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
    return [*runs.values(), repeated]


def _validate_spec(spec: dict[str, Any]) -> None:
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("spec_id")
        != "physical-heliacal-phase1-named-spectral-direct-probe-2026-07-30"
        or spec.get("status") != "research_probe_not_runtime_data_pack"
    ):
        raise ValidationError("probe specification identity differs")
    boundary = spec.get("runtime_boundary")
    if not isinstance(boundary, dict) or any(
        boundary.get(field) is not False
        for field in (
            "engine_changes_authorized",
            "public_api_changes_authorized",
            "runtime_table_authorized",
            "runtime_dependency_on_libRadtran",
            "runtime_dependency_on_REPTRAN",
            "network_dependency",
        )
    ):
        raise ValidationError("runtime boundary differs")
    source = spec.get("source")
    if not isinstance(source, dict):
        raise ValidationError("source receipt is absent")
    if (
        source["libRadtran"]["archive_sha256"]
        != "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
        or source["REPTRAN_module"]["archive_sha256"]
        != "55893c80bcc999651bac3bf014ee64aaf602653ba640eb5bebe787a5d8eacce7"
        or source["merged_data_root"]["canonical_file_receipts_sha256"]
        != "68f1817782e424ef617dab03ad985a3fbcb91fa2ed0239a8c2de1e8cb6855b59"
        or source["REPTRAN_module"]["embedded_notice_or_license_file_count"] != 0
    ):
        raise ValidationError("external source identity differs")
    if (
        set(spec.get("profiles", {}))
        != {
            "tropical",
            "midlatitude_summer",
            "midlatitude_winter",
            "subarctic_summer",
            "subarctic_winter",
            "us_standard",
        }
        or len(_vertical_grids(spec)) != 4
        or spec["spectral_design"]["expected_output_row_count"] != 8001
        or spec["spectral_design"]["REPTRAN_resolutions"]["fine"]["role"]
        != "admitted_full_spectral_reference"
        or spec["solver"]["governing_solver"] != "disort"
        or spec["solver"]["bulk_direct_beam_accelerator"] != "twostr"
    ):
        raise ValidationError("bounded scientific design differs")
    if len(expected_runs(spec)) != 54:
        raise ValidationError("expected run count differs")


def _expected_input(
    run: dict[str, Any],
    spec: dict[str, Any],
    levels: list[float] | None,
) -> str:
    spectral = spec["spectral_design"]
    solar_zenith = 90.0 - float(run["target_true_altitude_deg"])
    lines = [
        "data_files_path libradtran_data",
        f"atmosphere_file libradtran_data/{run['atmosphere_path']}",
        f"source solar libradtran_data/{spectral['solar_source_path']}",
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
        lines.append(
            f"number_of_streams {spec['solver']['governing_number_of_streams']}"
        )
    lines.extend(
        [
            f"mc_randomseed {spec['solver']['random_seed']}",
            "output_quantity transmittance",
            "output_user lambda edir",
            "zout 0",
            "quiet",
        ]
    )
    return "\n".join(lines) + "\n"


def _parse_spectrum(
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
            raise ValidationError(f"unexpected uvspec stdout line: {line!r}")
        wavelengths.append(float(match.group(1)))
        horizontal.append(float(match.group(2)))
    spectral = spec["spectral_design"]
    if len(wavelengths) != spectral["expected_output_row_count"]:
        raise ValidationError(f"spectrum row count differs: {run['run_id']}")
    start = float(spectral["wavelength_start_nm"])
    step = float(spectral["output_grid_step_nm"])
    tolerance = float(spec["acceptance"]["spectrum_wavelength_abs_tolerance_nm"])
    for index, wavelength in enumerate(wavelengths):
        if not math.isclose(
            wavelength,
            start + index * step,
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise ValidationError(f"wavelength grid differs: {run['run_id']}")
    sine_altitude = math.sin(
        math.radians(float(run["target_true_altitude_deg"]))
    )
    direct = [value / sine_altitude for value in horizontal]
    upper = float(spec["acceptance"]["direct_transmission_upper_tolerance"])
    if any(
        not math.isfinite(value) or value < 0 or value > 1.0 + upper
        for value in direct
    ):
        raise ValidationError(f"direct transmission is out of range: {run['run_id']}")
    return {
        "values": direct,
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


def _bin_comparison(
    candidate: list[float],
    reference: list[float],
    *,
    bin_width_nm: float,
    spec: dict[str, Any],
) -> dict[str, Any]:
    spectral = spec["spectral_design"]
    step = float(spectral["output_grid_step_nm"])
    span = float(spectral["wavelength_stop_nm"]) - float(
        spectral["wavelength_start_nm"]
    )
    points_per_bin = int(round(bin_width_nm / step))
    bin_count = int(round(span / bin_width_nm))
    if len(candidate) != bin_count * points_per_bin + 1:
        raise ValidationError("spectral comparison grid differs")
    floor = float(spec["acceptance"]["opaque_bin_direct_transmission_floor"])
    deltas: list[float] = []
    opaque_both = 0
    mismatch = 0
    maximum = -1.0
    maximum_start = 0.0
    candidate_total = 0.0
    reference_total = 0.0
    for bin_index in range(bin_count):
        offset = bin_index * points_per_bin
        candidate_mean = math.fsum(
            candidate[offset : offset + points_per_bin]
        ) / points_per_bin
        reference_mean = math.fsum(
            reference[offset : offset + points_per_bin]
        ) / points_per_bin
        candidate_total += candidate_mean
        reference_total += reference_mean
        candidate_opaque = candidate_mean <= floor
        reference_opaque = reference_mean <= floor
        if candidate_opaque and reference_opaque:
            opaque_both += 1
            continue
        if candidate_opaque != reference_opaque:
            mismatch += 1
            continue
        delta = abs(-2.5 * math.log10(candidate_mean / reference_mean))
        deltas.append(delta)
        if delta > maximum:
            maximum = delta
            maximum_start = (
                float(spectral["wavelength_start_nm"])
                + bin_index * bin_width_nm
            )
    if not deltas:
        raise ValidationError("no spectral bins are evaluable")
    ordered = sorted(deltas)

    def quantile(fraction: float) -> float:
        return ordered[math.floor((len(ordered) - 1) * fraction)]

    return {
        "bin_width_nm": bin_width_nm,
        "evaluated_bin_count": len(deltas),
        "both_opaque_bin_count": opaque_both,
        "opacity_classification_mismatch_count": mismatch,
        "overall_mean_magnitude_difference": abs(
            -2.5 * math.log10(candidate_total / reference_total)
        ),
        "p95_magnitude_difference": quantile(0.95),
        "p99_magnitude_difference": quantile(0.99),
        "maximum_magnitude_difference": maximum,
        "maximum_bin_start_nm": maximum_start,
    }


def _compare(
    spectra: dict[str, list[float]],
    candidate_id: str,
    reference_id: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    return {
        _format_number(width): _bin_comparison(
            spectra[candidate_id],
            spectra[reference_id],
            bin_width_nm=float(width),
            spec=spec,
        )
        for width in spec["spectral_design"]["diagnostic_bin_width_nm"]
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


def _lookup_runs(runs: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    lookup: dict[tuple[Any, ...], dict[str, Any]] = {}
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
        lookup[key] = run
    return lookup


def _get_run(
    lookup: dict[tuple[Any, ...], dict[str, Any]],
    *,
    profile: str,
    altitude: float,
    grid_id: str,
    resolution: str,
    solver: str = "twostr",
) -> dict[str, Any]:
    try:
        return lookup[
            _run_key(
                profile=profile,
                altitude=altitude,
                grid_id=grid_id,
                resolution=resolution,
                solver=solver,
            )
        ]
    except KeyError as exc:
        raise ValidationError("required comparison run is absent") from exc


def _recompute_comparisons(
    artifact_root: Path,
    runs: list[dict[str, Any]],
    spectra: dict[str, list[float]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    lookup = _lookup_runs(runs)
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
                "source_vs_reference": _compare(
                    spectra,
                    source["run_id"],
                    reference["run_id"],
                    spec,
                ),
                "candidate_vs_reference": _compare(
                    spectra,
                    candidate["run_id"],
                    reference["run_id"],
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
        "comparison": _compare(
            spectra,
            reference["run_id"],
            convergence["run_id"],
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
        "comparison": _compare(
            spectra,
            fine_candidate["run_id"],
            fine_reference["run_id"],
            spec,
        ),
    }

    spectral = spec["probe_matrix"]["spectral_resolution_cases"]
    spectral_conditions = [
        (profile, float(spectral["all_profiles_target_true_altitude_deg"]))
        for profile in spec["profiles"]
    ]
    spectral_conditions.extend(
        ("us_standard", float(altitude))
        for altitude in spectral["us_standard_additional_target_true_altitude_deg"]
    )
    spectral_resolution: list[dict[str, Any]] = []
    for profile, altitude in spectral_conditions:
        medium = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id=spectral["grid_id"],
            resolution="medium",
        )
        fine = _get_run(
            lookup,
            profile=profile,
            altitude=altitude,
            grid_id=spectral["grid_id"],
            resolution="fine",
        )
        spectral_resolution.append(
            {
                "profile": profile,
                "target_true_altitude_deg": altitude,
                "medium_run_id": medium["run_id"],
                "fine_run_id": fine["run_id"],
                "medium_vs_fine": _compare(
                    spectra,
                    medium["run_id"],
                    fine["run_id"],
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
            artifact_root / twostr["run_id"] / "stdout.txt"
        ).read_bytes()
        disort_bytes = (
            artifact_root / disort["run_id"] / "stdout.txt"
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
                "original_sha256": _sha256_file(
                    artifact_root / repeated["repeat_of"] / name
                ),
                "repeat_sha256": _sha256_file(
                    artifact_root / repeated["run_id"] / name
                ),
                "byte_identical": (
                    (
                        artifact_root / repeated["repeat_of"] / name
                    ).read_bytes()
                    == (artifact_root / repeated["run_id"] / name).read_bytes()
                ),
            }
            for name in repeat_files
        ],
    }

    widths = [
        _format_number(value)
        for value in spec["spectral_design"]["diagnostic_bin_width_nm"]
    ]
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
    maxima = {
        "candidate_vs_reference_by_bin_nm": maximum_candidate,
        "reference_vs_convergence_by_bin_nm": convergence_error,
        "combined_candidate_grid_error_bound_by_bin_nm": {
            width: maximum_candidate[width] + convergence_error[width]
            for width in widths
        },
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
    return {
        "vertical_grid_matrix": vertical,
        "reference_convergence": reference_convergence,
        "fine_vertical_transfer": fine_vertical,
        "spectral_resolution_matrix": spectral_resolution,
        "DISORT_parity": parity,
        "fixed_input_repeat": repeat_receipt,
        "maxima": maxima,
    }


def _assert_close(
    actual: Any,
    expected: Any,
    label: str,
    *,
    relative_tolerance: float = 2e-12,
    absolute_tolerance: float = 2e-14,
) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValidationError(f"{label} shape differs")
        for key, value in expected.items():
            _assert_close(
                actual[key],
                value,
                f"{label}.{key}",
                relative_tolerance=relative_tolerance,
                absolute_tolerance=absolute_tolerance,
            )
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValidationError(f"{label} length differs")
        for index, value in enumerate(expected):
            _assert_close(
                actual[index],
                value,
                f"{label}[{index}]",
                relative_tolerance=relative_tolerance,
                absolute_tolerance=absolute_tolerance,
            )
        return
    if isinstance(expected, float):
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not math.isclose(
                float(actual),
                expected,
                rel_tol=relative_tolerance,
                abs_tol=absolute_tolerance,
            )
        ):
            raise ValidationError(f"{label} differs")
        return
    if actual != expected:
        raise ValidationError(f"{label} differs")


def _enforce_acceptance(summary: dict[str, Any], spec: dict[str, Any]) -> None:
    acceptance = spec["acceptance"]
    maxima = summary["maxima"]
    fields = (
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
    for result_field, limit_field in fields:
        for width, value in maxima[result_field].items():
            if value > float(acceptance[limit_field][width]):
                raise ValidationError(f"{result_field} exceeds acceptance")

    def comparisons(value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, dict):
            if "opacity_classification_mismatch_count" in value:
                yield value
            for child in value.values():
                yield from comparisons(child)
        elif isinstance(value, list):
            for child in value:
                yield from comparisons(child)

    mismatch_limit = int(
        acceptance["maximum_opacity_classification_mismatches"]
    )
    if any(
        item["opacity_classification_mismatch_count"] > mismatch_limit
        for item in comparisons(summary)
    ):
        raise ValidationError("opacity classification differs")
    if any(
        not item["stdout_byte_identical"]
        or item["differing_stdout_line_count"]
        > acceptance["DISORT_parity_differing_stdout_line_count"]
        for item in summary["DISORT_parity"]
    ):
        raise ValidationError("DISORT direct-beam parity failed")
    if (
        acceptance["repeat_byte_identity_required"]
        and not all(
            item["byte_identical"]
            for item in summary["fixed_input_repeat"]["files"]
        )
    ):
        raise ValidationError("fixed-input repeat differs")


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


def validate_artifact(
    artifact_root: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise ValidationError("artifact root must be a real directory")
    spec = _load_json(spec_path, "probe specification")
    _validate_spec(spec)
    manifest_path = artifact_root / MANIFEST_NAME
    manifest = _load_json(manifest_path, "artifact manifest")
    manifest_sha256 = _sha256_file(manifest_path)
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256
    ):
        raise ValidationError("artifact manifest SHA-256 differs")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("artifact_status") != ARTIFACT_STATUS
        or manifest.get("spec_id") != spec["spec_id"]
        or manifest.get("model_id") != spec["scientific_boundary"]["model_id"]
        or manifest.get("runtime_boundary") != spec["runtime_boundary"]
        or manifest.get("scientific_boundary") != spec["scientific_boundary"]
    ):
        raise ValidationError("artifact manifest identity differs")

    specifications = manifest.get("specifications")
    if not isinstance(specifications, dict):
        raise ValidationError("artifact specifications are absent")
    _validate_file_receipt(
        REPO_ROOT,
        specifications.get("named_spectral_direct_probe"),
        label="named-spectral specification",
    )
    if specifications["named_spectral_direct_probe"]["path"] != str(
        spec_path.resolve().relative_to(REPO_ROOT).as_posix()
    ):
        raise ValidationError("active specification path differs")

    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict):
        raise ValidationError("artifact tooling receipts are absent")
    for role, receipt in tooling.items():
        _validate_file_receipt(REPO_ROOT, receipt, label=f"tooling {role}")

    generation_identity = manifest.get("generation_identity")
    execution_tooling_roles = {
        "builder",
        "predecessor_spec",
        "checkpoint1_spec",
        "checkpoint1_builder",
    }
    if (
        not isinstance(generation_identity, dict)
        or generation_identity.get("execution_tooling")
        != {
            role: tooling[role]
            for role in execution_tooling_roles
        }
        or generation_identity.get("run_contract_sha256")
        != _sha256_bytes(_canonical_json_bytes(_run_contract(spec)))
        or manifest.get("generation_fingerprint")
        != _sha256_bytes(_canonical_json_bytes(generation_identity))
    ):
        raise ValidationError("generation identity differs")

    generator = manifest.get("generator")
    merged = spec["source"]["merged_data_root"]
    if (
        not isinstance(generator, dict)
        or generator.get("uvspec_sha256")
        != spec["source"]["libRadtran"]["uvspec_sha256"]
        or generator.get("REPTRAN_archive", {}).get("bytes")
        != spec["source"]["REPTRAN_module"]["archive_bytes"]
        or generator.get("REPTRAN_archive", {}).get("sha256")
        != spec["source"]["REPTRAN_module"]["archive_sha256"]
        or generator.get("merged_data_root", {}).get("receipt_file")
        != EXTERNAL_RECEIPTS_NAME
        or {
            key: generator["merged_data_root"].get(key)
            for key in (
                "regular_file_count",
                "regular_file_bytes",
                "canonical_file_receipts_bytes",
                "canonical_file_receipts_sha256",
            )
        }
        != {
            key: merged[key]
            for key in (
                "regular_file_count",
                "regular_file_bytes",
                "canonical_file_receipts_bytes",
                "canonical_file_receipts_sha256",
            )
        }
    ):
        raise ValidationError("bound generator identity differs")

    external_path = artifact_root / EXTERNAL_RECEIPTS_NAME
    try:
        external_receipts = json.loads(external_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("cannot read external-data receipts") from exc
    if not isinstance(external_receipts, list):
        raise ValidationError("external-data receipts must be an array")
    external_bytes = _compact_json_bytes(external_receipts)
    if (
        external_path.read_bytes() != external_bytes
        or len(external_receipts) != merged["regular_file_count"]
        or sum(
            receipt.get("bytes", -1)
            for receipt in external_receipts
            if isinstance(receipt, dict)
        )
        != merged["regular_file_bytes"]
        or len(external_bytes) != merged["canonical_file_receipts_bytes"]
        or _sha256_bytes(external_bytes)
        != merged["canonical_file_receipts_sha256"]
    ):
        raise ValidationError("external-data receipts differ")
    external_names: set[str] = set()
    for receipt in external_receipts:
        if not isinstance(receipt, dict) or set(receipt) != {
            "path",
            "bytes",
            "sha256",
        }:
            raise ValidationError("external-data receipt shape differs")
        relative = _safe_relative_path(receipt["path"], "external-data path")
        if relative in external_names:
            raise ValidationError("external-data paths collide")
        external_names.add(relative)
        if not isinstance(receipt["bytes"], int) or receipt["bytes"] < 0:
            raise ValidationError("external-data byte count differs")
        _validate_sha256(receipt["sha256"], "external-data sha256")

    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValidationError("artifact file receipts are absent")
    receipt_paths = {
        _validate_file_receipt(
            artifact_root,
            receipt,
            label=f"artifact file {index}",
        )
        for index, receipt in enumerate(files)
    }
    actual_paths: set[str] = set()
    for path in artifact_root.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"artifact contains a symlink: {path}")
        if path.is_file() and path != manifest_path:
            actual_paths.add(path.relative_to(artifact_root).as_posix())
    if receipt_paths != actual_paths or len(receipt_paths) != len(files):
        raise ValidationError("artifact file inventory differs")

    runs = expected_runs(spec)
    expected_by_id = {run["run_id"]: run for run in runs}
    if (
        manifest.get("run_count") != len(runs)
        or manifest.get("twostr_run_count")
        != sum(run["rte_solver"] == "twostr" for run in runs)
        or manifest.get("DISORT_run_count")
        != sum(run["rte_solver"] == "disort" for run in runs)
    ):
        raise ValidationError("artifact run counts differ")
    run_summaries = manifest.get("run_summaries")
    if not isinstance(run_summaries, list) or len(run_summaries) != len(runs):
        raise ValidationError("artifact run summaries differ")
    summaries_by_id = {
        item["run"]["run_id"]: item
        for item in run_summaries
        if isinstance(item, dict)
        and isinstance(item.get("run"), dict)
        and isinstance(item["run"].get("run_id"), str)
    }
    if set(summaries_by_id) != set(expected_by_id):
        raise ValidationError("artifact run-summary identifiers differ")

    grids = _vertical_grids(spec)
    spectra: dict[str, list[float]] = {}
    for run in runs:
        run_id = run["run_id"]
        run_dir = artifact_root / run_id
        if (
            run_dir.is_symlink()
            or not run_dir.is_dir()
            or {path.name for path in run_dir.iterdir()} != RUN_FILES
        ):
            raise ValidationError(f"run inventory differs: {run_id}")
        result = _load_json(run_dir / "result.json", f"run result {run_id}")
        if (
            result.get("schema") != RUN_SCHEMA
            or result.get("generation_fingerprint")
            != manifest["generation_fingerprint"]
            or result.get("run") != run
        ):
            raise ValidationError(f"run result identity differs: {run_id}")
        result_files = result.get("files")
        if not isinstance(result_files, list):
            raise ValidationError(f"run file receipts are absent: {run_id}")
        result_paths = {
            _validate_file_receipt(
                run_dir,
                receipt,
                label=f"run {run_id} file",
            )
            for receipt in result_files
        }
        if result_paths != RUN_FILES - {"result.json"}:
            raise ValidationError(f"run-bound file inventory differs: {run_id}")
        expected_input = _expected_input(run, spec, grids[run["grid_id"]])
        if (run_dir / "input.inp").read_text(encoding="utf-8") != expected_input:
            raise ValidationError(f"controlled input differs: {run_id}")
        if (run_dir / "randomseed").read_text(encoding="utf-8").strip() != str(
            spec["solver"]["random_seed"]
        ):
            raise ValidationError(f"random-seed receipt differs: {run_id}")
        if re.search(
            r"(?im)(?:^|\s)(?:error|\*\*\*\s*error)\b",
            (run_dir / "stderr.txt").read_text(encoding="utf-8"),
        ):
            raise ValidationError(f"uvspec stderr reports an error: {run_id}")
        parsed = _parse_spectrum(
            (run_dir / "stdout.txt").read_text(encoding="utf-8"),
            run=run,
            spec=spec,
        )
        _assert_close(
            result.get("spectrum"),
            parsed["summary"],
            f"run spectrum summary {run_id}",
        )
        _assert_close(
            summaries_by_id[run_id],
            {
                "run": run,
                "spectrum": parsed["summary"],
            },
            f"manifest run summary {run_id}",
        )
        spectra[run_id] = parsed["values"]

    recomputed = _recompute_comparisons(artifact_root, runs, spectra, spec)
    _assert_close(
        manifest.get("comparisons"),
        recomputed,
        "artifact comparisons",
    )
    _enforce_acceptance(recomputed, spec)

    allowed_entries = {
        MANIFEST_NAME,
        EXTERNAL_RECEIPTS_NAME,
        *expected_by_id,
    }
    if {path.name for path in artifact_root.iterdir()} != allowed_entries:
        raise ValidationError("artifact root contains an unowned entry")
    return {
        "manifest_sha256": manifest_sha256,
        "run_count": len(runs),
        "twostr_run_count": sum(run["rte_solver"] == "twostr" for run in runs),
        "DISORT_run_count": sum(run["rte_solver"] == "disort" for run in runs),
        "named_profile_count": len(spec["profiles"]),
        "all_files_bound": True,
        "external_data_root_bound": True,
        "vertical_grid_comparisons_recomputed": True,
        "spectral_resolution_comparisons_recomputed": True,
        "DISORT_parity_byte_identical": True,
        "fixed_input_repeat_byte_identical": True,
        "fine_reference_admitted": True,
        "runtime_dependency": False,
        "network_dependency": False,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Phase 1 named-spectral direct artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
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
