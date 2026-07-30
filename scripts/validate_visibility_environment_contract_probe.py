#!/usr/bin/env python3
"""Independently validate a Phase 1 environmental-contract probe artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_environment_contract_probe_spec.json"
)
BUILDER_PATH = REPO_ROOT / "scripts" / "build_visibility_environment_contract_probe.py"
VALIDATOR_PATH = Path(__file__).resolve()

SPEC_SCHEMA = "moira.visibility-environment-contract-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-environment-contract-probe-artifact/v1"
RUN_SCHEMA = "moira.visibility-environment-contract-probe-run/v1"
ARTIFACT_STATUS = "phase1_environment_contract_evidence_not_runtime_data_pack"
MANIFEST_NAME = "artifact-manifest.json"
DATA_LINK_NAME = "libradtran_data"
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


class ValidationError(ValueError):
    """Raised when an environmental-contract artifact is invalid."""


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
        raise ValidationError(f"{label} path is empty")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValidationError(f"{label} path is unsafe")
    return value


def _valid_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValidationError(f"{label} SHA-256 is invalid")
    return value


def _validate_receipt_shape(receipt: Any, label: str) -> dict[str, Any]:
    if not isinstance(receipt, dict) or set(receipt) != {
        "path",
        "bytes",
        "sha256",
    }:
        raise ValidationError(f"{label} receipt shape differs")
    _safe_relative_path(receipt["path"], label)
    if not isinstance(receipt["bytes"], int) or receipt["bytes"] < 0:
        raise ValidationError(f"{label} byte count is invalid")
    _valid_sha(receipt["sha256"], label)
    return receipt


def _validate_artifact_file(
    root: Path,
    receipt: Any,
    label: str,
) -> Path:
    value = _validate_receipt_shape(receipt, label)
    path = (root / value["path"]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label} leaves artifact root") from exc
    if path.is_symlink() or not path.is_file():
        raise ValidationError(f"{label} is missing or is a symlink")
    if path.stat().st_size != value["bytes"]:
        raise ValidationError(f"{label} byte count differs")
    if _sha256_file(path) != value["sha256"]:
        raise ValidationError(f"{label} checksum differs")
    return path


def _repo_receipt(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": resolved.relative_to(REPO_ROOT.resolve()).as_posix(),
        "bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def load_spec(path: Path) -> dict[str, Any]:
    spec = _load_json(path, "environment probe spec")
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("spec_id")
        != "physical-heliacal-phase1-environment-contract-probe-2026-07-30"
        or spec.get("status") != "research_probe_not_runtime_data_pack"
    ):
        raise ValidationError("environment probe identity differs")
    if spec.get("acceptance", {}).get("expected_run_count") != 73:
        raise ValidationError("environment probe run count differs")
    boundary = spec.get("runtime_boundary")
    if not isinstance(boundary, dict):
        raise ValidationError("runtime boundary is absent")
    forbidden_true = (
        "network_allowed",
        "automatic_download_allowed",
        "engine_dependency_allowed",
        "engine_runtime_invocation_allowed",
        "production_data_pack_authorized",
        "engine_changes_authorized",
    )
    if any(boundary.get(key) is not False for key in forbidden_true):
        raise ValidationError("runtime boundary was widened")
    if boundary.get("generated_numerical_products_only") is not True:
        raise ValidationError("generated-product boundary differs")
    profiles = (
        spec.get("environment_contract", {})
        .get("aerosol", {})
        .get("named_profiles")
    )
    if not isinstance(profiles, dict) or set(profiles) != {
        f"{kind}_{season}"
        for kind in ("rural", "maritime", "urban", "tropospheric")
        for season in ("summer", "winter")
    }:
        raise ValidationError("named aerosol inventory differs")
    oracle = spec.get("direct_extinction_oracle")
    if (
        not isinstance(oracle, dict)
        or oracle.get("aerosol_scattering_override")
        != "aerosol_modify ssa set 0"
        or oracle.get("rte_solver") != "disort"
        or oracle.get("geometry") != "pseudospherical"
        or oracle.get("number_of_streams") != 16
    ):
        raise ValidationError("direct extinction oracle differs")
    return spec


def _format_number(value: float) -> str:
    if float(value) == 0.0:
        return "0"
    return format(float(value), ".15g")


def _canonical_float(value: float) -> float:
    """Remove platform-libm noise below the probe's serialized precision."""
    return float(format(float(value), ".15g"))


def _value_token(value: float, places: int) -> str:
    return f"{float(value):.{places}f}".replace("-", "m").replace(".", "p")


def _base_run(spec: dict[str, Any]) -> dict[str, Any]:
    baseline = dict(spec["probe_matrix"]["baseline"])
    profile = spec["environment_contract"]["aerosol"]["named_profiles"][
        baseline["aerosol_profile"]
    ]
    baseline.update(
        {
            "haze": profile["haze"],
            "season": profile["season"],
            "vulcan": 1,
            "pressure_override_hpa": None,
            "aerosol_ssa_zero": True,
            "delta_m": "off",
            "repeat_of": None,
        }
    )
    return baseline


def expected_runs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = spec["probe_matrix"]
    profiles = spec["environment_contract"]["aerosol"]["named_profiles"]
    baseline = _base_run(spec)
    runs: list[dict[str, Any]] = []

    def add(run_id: str, kind: str, **updates: Any) -> None:
        run = dict(baseline)
        run.update(updates)
        run["run_id"] = run_id
        run["kind"] = kind
        runs.append(run)

    for value in matrix["albedo_invariance_values"]:
        add(
            f"albedo_{_value_token(value, 2)}",
            "albedo_direct_invariance",
            ground_albedo=float(value),
        )
    for name in sorted(profiles):
        profile = profiles[name]
        add(
            f"aerosol_{name}",
            "named_aerosol_direct_invariance",
            aerosol_profile=name,
            haze=profile["haze"],
            season=profile["season"],
        )
    for haze in matrix["delta_m_haze_diagnostic_codes"]:
        add(
            f"delta_m_haze_{haze}",
            "raw_delta_m_haze_diagnostic",
            aerosol_profile=f"diagnostic_haze_{haze}_summer",
            haze=haze,
            season=1,
            aerosol_ssa_zero=False,
            delta_m="on",
        )
    aod = matrix["aod_sweep"]
    for altitude in aod["target_true_altitude_deg"]:
        for value in aod["aod550"]:
            add(
                (
                    f"aod_alt_{_value_token(altitude, 2)}"
                    f"_aod_{_value_token(value, 3)}"
                ),
                "aod_sweep",
                target_true_altitude_deg=float(altitude),
                aod550=float(value),
                wavelength_nm=float(aod["wavelength_nm"]),
            )
    angstrom = matrix["angstrom_sweep"]
    for alpha in angstrom["angstrom_exponent"]:
        for wavelength in angstrom["wavelength_nm"]:
            add(
                (
                    f"angstrom_{_value_token(alpha, 2)}"
                    f"_wavelength_{_value_token(wavelength, 1)}"
                ),
                "angstrom_sweep",
                angstrom_exponent=float(alpha),
                wavelength_nm=float(wavelength),
                target_true_altitude_deg=float(
                    angstrom["target_true_altitude_deg"]
                ),
                aod550=float(angstrom["aod550"]),
            )
    ozone = matrix["ozone_sweep"]
    for value in ozone["ozone_du"]:
        add(
            f"ozone_{_value_token(value, 1)}",
            "ozone_sweep",
            ozone_du=float(value),
            wavelength_nm=float(ozone["wavelength_nm"]),
            target_true_altitude_deg=float(ozone["target_true_altitude_deg"]),
            aod550=float(ozone["aod550"]),
        )
    pressure = matrix["pressure_sweep"]
    for ratio in pressure["pressure_ratio"]:
        add(
            f"pressure_ratio_{_value_token(ratio, 3)}",
            "pressure_sweep",
            pressure_ratio=float(ratio),
            pressure_override_hpa=(
                float(baseline["profile_surface_pressure_hpa"]) * float(ratio)
            ),
            wavelength_nm=float(pressure["wavelength_nm"]),
            target_true_altitude_deg=float(
                pressure["target_true_altitude_deg"]
            ),
            aod550=float(pressure["aod550"]),
        )
    repeat_of = matrix["exact_repeat_of"]
    original = next((run for run in runs if run["run_id"] == repeat_of), None)
    if original is None:
        raise ValidationError("repeat target is missing")
    repeat = dict(original)
    repeat["run_id"] = f"repeat_{repeat_of}"
    repeat["kind"] = "exact_repeat"
    repeat["repeat_of"] = repeat_of
    runs.append(repeat)
    if len(runs) != 73 or len({run["run_id"] for run in runs}) != 73:
        raise ValidationError("expected run expansion differs")
    return runs


def expected_input(run: dict[str, Any], spec: dict[str, Any]) -> str:
    oracle = spec["direct_extinction_oracle"]
    assets = oracle["input_assets"]
    cross_sections = assets["cross_sections"]
    alpha = float(run["angstrom_exponent"])
    beta = _canonical_float(float(run["aod550"]) * (0.55**alpha))
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        f"atmosphere_file {DATA_LINK_NAME}/{assets['atmosphere_path']}",
        f"source solar {DATA_LINK_NAME}/{assets['solar_source_path']}",
        (
            f"wavelength {_format_number(run['wavelength_nm'])} "
            f"{_format_number(run['wavelength_nm'])}"
        ),
        f"mol_abs_param {oracle['molecular_absorption']}",
        f"crs_model rayleigh {cross_sections['rayleigh']}",
        f"crs_model O3 {cross_sections['O3']}",
        f"crs_model NO2 {cross_sections['NO2']}",
        f"crs_model O4 {cross_sections['O4']}",
        f"earth_radius {_format_number(assets['earth_radius_km'])}",
    ]
    if run["pressure_override_hpa"] is not None:
        lines.append(f"pressure {_format_number(run['pressure_override_hpa'])}")
    lines.extend(
        [
            f"mol_modify O3 {_format_number(run['ozone_du'])} DU",
            f"albedo {_format_number(run['ground_albedo'])}",
            "aerosol_default",
            f"aerosol_vulcan {run['vulcan']}",
            f"aerosol_haze {run['haze']}",
            f"aerosol_season {run['season']}",
            f"aerosol_angstrom {_format_number(alpha)} {_format_number(beta)}",
        ]
    )
    if run["aerosol_ssa_zero"]:
        lines.append(oracle["aerosol_scattering_override"])
    lines.extend(
        [
            f"sza {_format_number(90.0 - float(run['target_true_altitude_deg']))}",
            f"rte_solver {oracle['rte_solver']}",
            oracle["geometry"],
            f"number_of_streams {oracle['number_of_streams']}",
            f"deltam {run['delta_m']}",
            f"output_quantity {oracle['output_quantity']}",
            "output_user " + " ".join(oracle["output_columns"]),
            f"mc_randomseed {oracle['random_seed']}",
            "zout 0",
            "quiet",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_output(
    text: str,
    run: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValidationError(f"output row count differs: {run['run_id']}")
    fields = lines[0].split()
    if len(fields) != 2:
        raise ValidationError(f"output column count differs: {run['run_id']}")
    try:
        wavelength, horizontal = (float(field) for field in fields)
    except ValueError as exc:
        raise ValidationError(f"output is nonnumeric: {run['run_id']}") from exc
    if not math.isclose(
        wavelength,
        float(run["wavelength_nm"]),
        rel_tol=0.0,
        abs_tol=5.0e-4,
    ):
        raise ValidationError(f"output wavelength differs: {run['run_id']}")
    transmission = _canonical_float(
        horizontal
        / math.sin(math.radians(float(run["target_true_altitude_deg"])))
    )
    upper = 1.0 + float(
        spec["acceptance"]["direct_transmission_upper_tolerance"]
    )
    if (
        not math.isfinite(horizontal)
        or not math.isfinite(transmission)
        or horizontal < 0.0
        or transmission < 0.0
        or transmission > upper
    ):
        raise ValidationError(f"direct transmission is invalid: {run['run_id']}")
    alpha = float(run["angstrom_exponent"])
    extinction_magnitude = (
        math.inf
        if transmission == 0.0
        else _canonical_float(-2.5 * math.log10(transmission))
    )
    return {
        "wavelength_nm": wavelength,
        "horizontal_direct_transmittance": horizontal,
        "direct_spectral_transmission": transmission,
        "extinction_magnitude": extinction_magnitude,
        "angstrom_beta": _canonical_float(
            float(run["aod550"]) * (0.55**alpha)
        ),
    }


def _strict(values: list[float], direction: str) -> bool:
    if direction == "decreasing":
        return all(left > right for left, right in zip(values, values[1:]))
    if direction == "increasing":
        return all(left < right for left, right in zip(values, values[1:]))
    raise ValidationError(f"unknown monotonic direction: {direction}")


def independent_summary(
    artifact: Path,
    runs: list[dict[str, Any]],
    results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    run_by_id = {run["run_id"]: run for run in runs}

    def stdout_bytes(run_id: str) -> bytes:
        return (artifact / run_id / "stdout.txt").read_bytes()

    albedo_ids = [
        run["run_id"] for run in runs if run["kind"] == "albedo_direct_invariance"
    ]
    albedo_count = len(
        {_sha256_bytes(stdout_bytes(run_id)) for run_id in albedo_ids}
    )

    haze_groups: dict[int, list[str]] = defaultdict(list)
    for run in runs:
        if run["kind"] == "named_aerosol_direct_invariance":
            haze_groups[int(run["season"])].append(run["run_id"])
    haze_counts = {
        str(season): len(
            {_sha256_bytes(stdout_bytes(run_id)) for run_id in run_ids}
        )
        for season, run_ids in sorted(haze_groups.items())
    }
    season_representatives = {
        season: stdout_bytes(sorted(run_ids)[0])
        for season, run_ids in haze_groups.items()
    }

    diagnostic_ids = [
        run["run_id"] for run in runs if run["kind"] == "raw_delta_m_haze_diagnostic"
    ]
    diagnostic_count = len(
        {_sha256_bytes(stdout_bytes(run_id)) for run_id in diagnostic_ids}
    )

    aod_groups: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run["kind"] == "aod_sweep":
            aod_groups[float(run["target_true_altitude_deg"])].append(run)
    aod_summary: list[dict[str, Any]] = []
    for altitude, rows in sorted(aod_groups.items()):
        ordered = sorted(rows, key=lambda run: float(run["aod550"]))
        transmissions = [
            results[run["run_id"]]["direct_spectral_transmission"]
            for run in ordered
        ]
        clear = transmissions[0]
        ratios = []
        for run, transmission in zip(ordered[1:], transmissions[1:]):
            ratios.append(
                (
                    math.inf
                    if transmission <= 0.0 or clear <= 0.0
                    else (
                        _canonical_float(
                            -math.log(transmission / clear)
                            / float(run["aod550"])
                        )
                    )
                )
            )
        finite = [value for value in ratios if math.isfinite(value)]
        aod_summary.append(
            {
                "target_true_altitude_deg": altitude,
                "strictly_decreasing": _strict(transmissions, "decreasing"),
                "tau_per_aod_minimum": min(finite) if finite else math.inf,
                "tau_per_aod_maximum": max(finite) if finite else math.inf,
                "tau_per_aod_ratio_spread": (
                    _canonical_float(max(finite) / min(finite))
                    if finite
                    else math.inf
                ),
            }
        )

    alpha_groups: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run["kind"] == "angstrom_sweep":
            alpha_groups[float(run["wavelength_nm"])].append(run)
    alpha_summary: dict[str, Any] = {}
    for wavelength, rows in sorted(alpha_groups.items()):
        ordered = sorted(rows, key=lambda run: float(run["angstrom_exponent"]))
        transmissions = [
            results[run["run_id"]]["direct_spectral_transmission"]
            for run in ordered
        ]
        alpha_summary[_format_number(wavelength)] = {
            "stdout_hash_count": len(
                {
                    _sha256_bytes(stdout_bytes(run["run_id"]))
                    for run in ordered
                }
            ),
            "strictly_decreasing": _strict(transmissions, "decreasing"),
            "strictly_increasing": _strict(transmissions, "increasing"),
        }

    def sweep(kind: str, key: str) -> tuple[list[float], list[float]]:
        rows = sorted(
            (run for run in runs if run["kind"] == kind),
            key=lambda run: float(run[key]),
        )
        return (
            [float(run[key]) for run in rows],
            [
                results[run["run_id"]]["direct_spectral_transmission"]
                for run in rows
            ],
        )

    ozone_values, ozone_transmission = sweep("ozone_sweep", "ozone_du")
    pressure_values, pressure_transmission = sweep(
        "pressure_sweep",
        "pressure_ratio",
    )
    repeat = next(run for run in runs if run["kind"] == "exact_repeat")
    original = run_by_id[repeat["repeat_of"]]
    repeat_names = (
        "input.inp",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    )
    repeat_files = [
        {
            "path": name,
            "byte_identical": (
                (artifact / original["run_id"] / name).read_bytes()
                == (artifact / repeat["run_id"] / name).read_bytes()
            ),
        }
        for name in repeat_names
    ]
    return {
        "run_count": len(runs),
        "albedo_direct": {
            "run_ids": albedo_ids,
            "stdout_hash_count": albedo_count,
        },
        "named_aerosol_direct": {
            "same_season_stdout_hash_counts": haze_counts,
            "season_representatives_differ": (
                season_representatives[1] != season_representatives[2]
            ),
        },
        "raw_delta_m_haze_diagnostic": {
            "run_ids": diagnostic_ids,
            "distinct_stdout_count": diagnostic_count,
        },
        "aod_sweep": aod_summary,
        "angstrom_sweep": alpha_summary,
        "ozone_sweep": {
            "ozone_du": ozone_values,
            "strictly_decreasing": _strict(
                ozone_transmission,
                "decreasing",
            ),
        },
        "pressure_sweep": {
            "pressure_ratio": pressure_values,
            "strictly_decreasing": _strict(
                pressure_transmission,
                "decreasing",
            ),
        },
        "exact_repeat": {
            "original_run_id": original["run_id"],
            "repeat_run_id": repeat["run_id"],
            "files": repeat_files,
            "all_required_files_byte_identical": all(
                row["byte_identical"] for row in repeat_files
            ),
        },
    }


def enforce_acceptance(summary: dict[str, Any], spec: dict[str, Any]) -> None:
    acceptance = spec["acceptance"]
    if summary["run_count"] != acceptance["expected_run_count"]:
        raise ValidationError("run count fails acceptance")
    if not summary["exact_repeat"]["all_required_files_byte_identical"]:
        raise ValidationError("exact repeat differs")
    if summary["albedo_direct"]["stdout_hash_count"] != 1:
        raise ValidationError("albedo contaminated direct output")
    if any(
        count != 1
        for count in summary["named_aerosol_direct"][
            "same_season_stdout_hash_counts"
        ].values()
    ):
        raise ValidationError("haze contaminated admitted direct output")
    if summary["raw_delta_m_haze_diagnostic"]["distinct_stdout_count"] <= 1:
        raise ValidationError("delta-M diagnostic did not differ")
    if not all(row["strictly_decreasing"] for row in summary["aod_sweep"]):
        raise ValidationError("AOD sweep is not monotonic")
    near_horizon = min(
        summary["aod_sweep"],
        key=lambda row: row["target_true_altitude_deg"],
    )
    if near_horizon["tau_per_aod_ratio_spread"] < acceptance[
        "near_horizon_aod_tau_per_aod_ratio_spread_minimum"
    ]:
        raise ValidationError("AOD nonlinearity bound is not met")
    alpha = summary["angstrom_sweep"]
    if (
        alpha["550"]["stdout_hash_count"] != 1
        or not alpha["400"]["strictly_decreasing"]
        or not alpha["780"]["strictly_increasing"]
    ):
        raise ValidationError("Angstrom response differs")
    if not summary["ozone_sweep"]["strictly_decreasing"]:
        raise ValidationError("ozone response differs")
    if not summary["pressure_sweep"]["strictly_decreasing"]:
        raise ValidationError("pressure response differs")
    if not summary["named_aerosol_direct"]["season_representatives_differ"]:
        raise ValidationError("aerosol season response did not differ")


def validate_artifact(
    artifact: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    artifact = artifact.resolve()
    spec_path = spec_path.resolve()
    if artifact.is_symlink() or not artifact.is_dir():
        raise ValidationError("artifact root is missing or is a symlink")
    spec = load_spec(spec_path)
    manifest_path = artifact / MANIFEST_NAME
    manifest = _load_json(manifest_path, "artifact manifest")
    if manifest_path.read_bytes() != _canonical_json_bytes(manifest):
        raise ValidationError("artifact manifest is not canonical JSON")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("status") != ARTIFACT_STATUS
        or manifest.get("spec_id") != spec["spec_id"]
        or manifest.get("runtime_boundary") != spec["runtime_boundary"]
    ):
        raise ValidationError("artifact identity or boundary differs")

    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict) or set(tooling) != {
        "spec",
        "builder",
        "validator",
    }:
        raise ValidationError("tooling inventory differs")
    current_tooling = {
        "spec": _repo_receipt(spec_path),
        "builder": _repo_receipt(BUILDER_PATH),
        "validator": _repo_receipt(VALIDATOR_PATH),
    }
    if tooling != current_tooling:
        raise ValidationError("tooling receipt differs")

    predecessor = manifest.get("predecessor")
    if not isinstance(predecessor, dict) or set(predecessor) != {
        "spec",
        "builder",
        "validator",
        "checkpoint",
    }:
        raise ValidationError("predecessor inventory differs")
    declared = spec["predecessor"]
    for role, receipt in predecessor.items():
        _validate_receipt_shape(receipt, f"predecessor {role}")
        if receipt != {
            "path": declared[f"{role}_path"],
            "bytes": declared[f"{role}_bytes"],
            "sha256": declared[f"{role}_sha256"],
        }:
            raise ValidationError(f"predecessor {role} differs")
        path = REPO_ROOT / receipt["path"]
        if not path.is_file() or _repo_receipt(path) != receipt:
            raise ValidationError(f"predecessor {role} is not present")

    source = manifest.get("source")
    if not isinstance(source, dict) or set(source) != {
        "archive",
        "uvspec",
        "uvspec_version",
        "source_files",
        "shettle_tau550_files",
        "runtime_assets",
    }:
        raise ValidationError("source inventory differs")
    archive = _validate_receipt_shape(source["archive"], "source archive")
    if (
        archive["bytes"] != spec["libradtran_source"]["archive_bytes"]
        or archive["sha256"] != spec["libradtran_source"]["archive_sha256"]
    ):
        raise ValidationError("source archive identity differs")
    uvspec = _validate_receipt_shape(source["uvspec"], "uvspec")
    if uvspec["sha256"] != spec["libradtran_source"]["uvspec_sha256"]:
        raise ValidationError("uvspec checksum differs")
    if spec["libradtran_source"]["uvspec_version"] not in source["uvspec_version"]:
        raise ValidationError("uvspec version differs")
    for label, manifest_rows, declared_rows in (
        (
            "source files",
            source["source_files"],
            spec["libradtran_source"]["source_files"],
        ),
        (
            "Shettle files",
            source["shettle_tau550_files"],
            spec["libradtran_source"]["shettle_tau550_files"],
        ),
    ):
        if not isinstance(manifest_rows, list) or len(manifest_rows) != len(
            declared_rows
        ):
            raise ValidationError(f"{label} inventory differs")
        expected = [
            {
                "path": row["path"],
                "bytes": row["bytes"],
                "sha256": row["sha256"],
            }
            for row in declared_rows
        ]
        if manifest_rows != expected:
            raise ValidationError(f"{label} receipts differ")
    runtime_assets = source["runtime_assets"]
    if not isinstance(runtime_assets, list) or len(runtime_assets) != 2:
        raise ValidationError("runtime asset inventory differs")
    for index, receipt in enumerate(runtime_assets):
        _validate_receipt_shape(receipt, f"runtime asset {index}")

    expected_fingerprint = _sha256_bytes(
        _compact_json_bytes(
            {
                "spec": tooling["spec"],
                "builder": tooling["builder"],
                "validator": tooling["validator"],
                "predecessor": predecessor,
                "source_archive": source["archive"],
                "uvspec": source["uvspec"],
                "source_files": source["source_files"],
                "shettle_files": source["shettle_tau550_files"],
                "runtime_assets": source["runtime_assets"],
            }
        )
    )
    if manifest.get("generation_fingerprint") != expected_fingerprint:
        raise ValidationError("generation fingerprint differs")

    runs = expected_runs(spec)
    expected_ids = [run["run_id"] for run in runs]
    manifest_runs = manifest.get("runs")
    if not isinstance(manifest_runs, list) or [
        row.get("run_id") for row in manifest_runs if isinstance(row, dict)
    ] != expected_ids:
        raise ValidationError("manifest run order differs")
    expected_root_entries = set(expected_ids) | {MANIFEST_NAME}
    actual_root_entries = {entry.name for entry in artifact.iterdir()}
    if actual_root_entries != expected_root_entries:
        raise ValidationError("artifact root inventory differs")

    results: dict[str, dict[str, Any]] = {}
    for run, receipt in zip(runs, manifest_runs):
        if not isinstance(receipt, dict) or set(receipt) != {
            "run_id",
            "kind",
            "files",
            "result",
        }:
            raise ValidationError(f"run receipt shape differs: {run['run_id']}")
        if receipt["run_id"] != run["run_id"] or receipt["kind"] != run["kind"]:
            raise ValidationError(f"run identity differs: {run['run_id']}")
        run_dir = artifact / run["run_id"]
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise ValidationError(f"run directory differs: {run['run_id']}")
        entries = {entry.name for entry in run_dir.iterdir()}
        if entries != RUN_FILES:
            raise ValidationError(f"run file inventory differs: {run['run_id']}")
        files = receipt["files"]
        if not isinstance(files, list) or len(files) != len(RUN_FILES):
            raise ValidationError(f"run file receipts differ: {run['run_id']}")
        validated_names = {
            _validate_artifact_file(
                artifact,
                file_receipt,
                f"{run['run_id']} file",
            ).name
            for file_receipt in files
        }
        if validated_names != RUN_FILES:
            raise ValidationError(f"run receipt inventory differs: {run['run_id']}")
        expected_text = expected_input(run, spec)
        if (run_dir / "input.inp").read_text(encoding="utf-8") != expected_text:
            raise ValidationError(f"rendered input differs: {run['run_id']}")
        result = parse_output(
            (run_dir / "stdout.txt").read_text(encoding="utf-8"),
            run,
            spec,
        )
        result_payload = _load_json(run_dir / "result.json", "run result")
        if (run_dir / "result.json").read_bytes() != _canonical_json_bytes(
            result_payload
        ):
            raise ValidationError(f"run result is not canonical: {run['run_id']}")
        if result_payload != {
            "schema": RUN_SCHEMA,
            "run": run,
            "result": result,
        }:
            raise ValidationError(f"run result payload differs: {run['run_id']}")
        if receipt["result"] != result:
            raise ValidationError(f"manifest result differs: {run['run_id']}")
        results[run["run_id"]] = result

    summary = independent_summary(artifact, runs, results)
    if manifest.get("summary") != summary:
        raise ValidationError("artifact summary differs")
    enforce_acceptance(summary, spec)
    return {
        "artifact": str(artifact),
        "manifest_sha256": _sha256_file(manifest_path),
        "generation_fingerprint": manifest["generation_fingerprint"],
        "run_count": summary["run_count"],
        "validated": True,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Phase 1 environmental-contract artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    print(
        json.dumps(
            validate_artifact(args.artifact, spec_path=args.spec),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
