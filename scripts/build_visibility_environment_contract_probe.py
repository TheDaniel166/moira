#!/usr/bin/env python3
"""Build the Phase 1 environmental-contract semantics probe.

This source-locked laboratory is deliberately narrower than a production
visibility table.  It verifies how libRadtran 2.0.6 maps Moira's proposed
pressure, ozone, aerosol, and albedo inputs, and it distinguishes physical
line-of-sight extinction from delta-M solver bookkeeping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SPEC_PATH = (
    SCRIPT_ROOT
    / "visibility_reference_lab"
    / "phase1_environment_contract_probe_spec.json"
)
VALIDATOR_PATH = SCRIPT_ROOT / "validate_visibility_environment_contract_probe.py"

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


class VisibilityEnvironmentProbeError(ValueError):
    """Raised when the environmental probe violates its frozen contract."""


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


def _file_receipt(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
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


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisibilityEnvironmentProbeError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VisibilityEnvironmentProbeError(f"{label} must be an array")
    return value


def _require_number(
    value: Any,
    label: str,
    low: float,
    high: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisibilityEnvironmentProbeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise VisibilityEnvironmentProbeError(f"{label} is out of range")
    return result


def _strictly_increasing(values: list[Any], label: str) -> list[float]:
    result = [
        _require_number(value, f"{label} value", -1.0e12, 1.0e12)
        for value in values
    ]
    if not result or any(left >= right for left, right in zip(result, result[1:])):
        raise VisibilityEnvironmentProbeError(
            f"{label} must be nonempty and strictly increasing"
        )
    return result


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibilityEnvironmentProbeError(f"cannot read probe spec: {path}") from exc
    if not isinstance(payload, dict):
        raise VisibilityEnvironmentProbeError("probe spec must be a JSON object")
    validate_spec(payload)
    return payload


def _validate_declared_receipt(receipt: Any, label: str) -> None:
    value = _require_dict(receipt, label)
    required = {"path", "bytes", "sha256"}
    if not required.issubset(value):
        raise VisibilityEnvironmentProbeError(f"{label} receipt is incomplete")
    path = value["path"]
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
    ):
        raise VisibilityEnvironmentProbeError(f"{label} path is unsafe")
    if not isinstance(value["bytes"], int) or value["bytes"] <= 0:
        raise VisibilityEnvironmentProbeError(f"{label} bytes are invalid")
    sha = value["sha256"]
    if (
        not isinstance(sha, str)
        or len(sha) != 64
        or any(character not in "0123456789abcdef" for character in sha)
    ):
        raise VisibilityEnvironmentProbeError(f"{label} SHA-256 is invalid")


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != SPEC_SCHEMA:
        raise VisibilityEnvironmentProbeError("unsupported environment probe schema")
    if (
        spec.get("spec_id")
        != "physical-heliacal-phase1-environment-contract-probe-2026-07-30"
        or spec.get("status") != "research_probe_not_runtime_data_pack"
    ):
        raise VisibilityEnvironmentProbeError("environment probe identity differs")

    predecessor = _require_dict(spec.get("predecessor"), "predecessor")
    expected_predecessor_keys = {
        f"{role}_{field}"
        for role in ("spec", "builder", "validator", "checkpoint")
        for field in ("path", "bytes", "sha256")
    }
    if set(predecessor) != expected_predecessor_keys:
        raise VisibilityEnvironmentProbeError("predecessor receipt inventory differs")
    for role in ("spec", "builder", "validator", "checkpoint"):
        _validate_declared_receipt(
            {
                "path": predecessor[f"{role}_path"],
                "bytes": predecessor[f"{role}_bytes"],
                "sha256": predecessor[f"{role}_sha256"],
            },
            f"predecessor {role}",
        )

    boundary = _require_dict(spec.get("runtime_boundary"), "runtime_boundary")
    if (
        any(
            boundary.get(key) is not False
            for key in (
                "network_allowed",
                "automatic_download_allowed",
                "engine_dependency_allowed",
                "engine_runtime_invocation_allowed",
                "production_data_pack_authorized",
                "engine_changes_authorized",
            )
        )
        or boundary.get("generated_numerical_products_only") is not True
    ):
        raise VisibilityEnvironmentProbeError("runtime boundary was widened")

    source = _require_dict(spec.get("libradtran_source"), "libradtran_source")
    if (
        source.get("version") != "2.0.6"
        or source.get("archive_bytes") != 154147176
        or source.get("archive_sha256")
        != "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
        or source.get("uvspec_version") != "uvspec, version 2.0.6-MYSTIC"
    ):
        raise VisibilityEnvironmentProbeError("libRadtran source identity differs")
    source_files = _require_list(source.get("source_files"), "source_files")
    if len(source_files) != 10:
        raise VisibilityEnvironmentProbeError("source-file inventory differs")
    source_paths: set[str] = set()
    for index, receipt in enumerate(source_files):
        _validate_declared_receipt(receipt, f"source_files[{index}]")
        value = _require_dict(receipt, f"source_files[{index}]")
        if not isinstance(value.get("role"), str) or not value["role"]:
            raise VisibilityEnvironmentProbeError("source-file role is missing")
        source_paths.add(value["path"])
    if len(source_paths) != len(source_files):
        raise VisibilityEnvironmentProbeError("source-file paths are duplicated")
    shettle = _require_list(
        source.get("shettle_tau550_files"),
        "shettle_tau550_files",
    )
    if len(shettle) != 8:
        raise VisibilityEnvironmentProbeError("Shettle receipt inventory differs")
    for index, receipt in enumerate(shettle):
        _validate_declared_receipt(receipt, f"shettle_tau550_files[{index}]")

    contract = _require_dict(spec.get("environment_contract"), "environment_contract")
    molecular = _require_dict(contract.get("molecular_atmosphere"), "molecular")
    if molecular.get("profiles") != [
        "tropical",
        "midlatitude_summer",
        "midlatitude_winter",
        "subarctic_summer",
        "subarctic_winter",
        "us_standard",
    ]:
        raise VisibilityEnvironmentProbeError("molecular profile inventory differs")
    if (
        molecular.get("temperature_policy")
        != "profile_derived_no_independent_override_in_first_pack"
        or molecular.get("water_vapor_and_relative_humidity_policy")
        != "profile_derived_no_independent_override_in_first_pack"
    ):
        raise VisibilityEnvironmentProbeError("profile-derived environment law differs")

    altitude = _require_dict(contract.get("observer_altitude"), "observer_altitude")
    if _strictly_increasing(altitude.get("candidate_nodes", []), "altitude nodes") != [
        0.0,
        500.0,
        1500.0,
        3000.0,
        5000.0,
    ]:
        raise VisibilityEnvironmentProbeError("observer-altitude candidates differ")
    _strictly_increasing(altitude.get("reserved_holdouts", []), "altitude holdouts")
    if altitude.get("interpolation") != (
        "not_admitted_until_holdout_error_is_measured"
    ):
        raise VisibilityEnvironmentProbeError("altitude interpolation was admitted")

    pressure = _require_dict(contract.get("surface_pressure"), "surface_pressure")
    pressure_nodes = _strictly_increasing(
        pressure.get("candidate_ratio_nodes", []),
        "pressure nodes",
    )
    if pressure_nodes != [0.85, 0.925, 1.0, 1.04, 1.08]:
        raise VisibilityEnvironmentProbeError("pressure ratio nodes differ")
    if (
        pressure.get("absolute_hard_bounds_hpa") != [500.0, 1100.0]
        or pressure.get("ratio_hard_bounds") != [0.85, 1.08]
        or pressure.get("admission_law")
        != "absolute_and_ratio_bounds_must_both_pass"
    ):
        raise VisibilityEnvironmentProbeError("pressure admission law differs")

    ozone = _require_dict(contract.get("ozone"), "ozone")
    if _strictly_increasing(ozone.get("candidate_nodes", []), "ozone nodes") != [
        200.0,
        250.0,
        300.0,
        350.0,
        400.0,
        500.0,
    ]:
        raise VisibilityEnvironmentProbeError("ozone nodes differ")

    aerosol = _require_dict(contract.get("aerosol"), "aerosol")
    profiles = _require_dict(aerosol.get("named_profiles"), "named aerosol profiles")
    expected_profiles = {
        f"{kind}_{season}"
        for kind in ("rural", "maritime", "urban", "tropospheric")
        for season in ("summer", "winter")
    }
    if set(profiles) != expected_profiles:
        raise VisibilityEnvironmentProbeError("named aerosol inventory is incomplete")
    expected_haze = {
        "rural": 1,
        "maritime": 4,
        "urban": 5,
        "tropospheric": 6,
    }
    for name, profile in profiles.items():
        value = _require_dict(profile, f"aerosol profile {name}")
        kind, season = name.split("_", 1)
        if value != {
            "haze": expected_haze[kind],
            "season": 1 if season == "summer" else 2,
        }:
            raise VisibilityEnvironmentProbeError(f"aerosol profile differs: {name}")
    if aerosol.get("visibility_input_policy") != (
        "not_exposed_because_aod550_is_authoritative"
    ):
        raise VisibilityEnvironmentProbeError("aerosol visibility became public")
    if _strictly_increasing(
        aerosol["aod550"].get("candidate_nodes", []),
        "AOD nodes",
    ) != [0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0]:
        raise VisibilityEnvironmentProbeError("AOD nodes differ")
    if _strictly_increasing(
        aerosol["angstrom_exponent"].get("candidate_nodes", []),
        "Angstrom nodes",
    ) != [0.0, 0.5, 1.0, 1.3, 1.8, 2.5]:
        raise VisibilityEnvironmentProbeError("Angstrom nodes differ")
    if aerosol.get("direct_table_dimensions") != [
        "season",
        "aod550",
        "angstrom_exponent",
    ]:
        raise VisibilityEnvironmentProbeError("direct aerosol dimensions differ")

    albedo = _require_dict(contract.get("ground_albedo"), "ground_albedo")
    if (
        albedo.get("direct_table_role") != "excluded"
        or albedo.get("radiance_table_role") != "included"
    ):
        raise VisibilityEnvironmentProbeError("ground-albedo role differs")
    _strictly_increasing(albedo.get("candidate_nodes", []), "albedo nodes")

    oracle = _require_dict(
        spec.get("direct_extinction_oracle"),
        "direct_extinction_oracle",
    )
    if (
        oracle.get("rte_solver") != "disort"
        or oracle.get("geometry") != "pseudospherical"
        or oracle.get("number_of_streams") != 16
        or oracle.get("aerosol_scattering_override")
        != "aerosol_modify ssa set 0"
        or oracle.get("delta_m_option") != "off"
        or oracle.get("normalization")
        != "direct_transmission_equals_edir_divided_by_sin_target_true_altitude"
    ):
        raise VisibilityEnvironmentProbeError("direct extinction oracle differs")
    assets = _require_dict(oracle.get("input_assets"), "input_assets")
    if (
        assets.get("atmosphere_path") != "atmmod/afglus.dat"
        or assets.get("solar_source_path") != "solar_flux/atlas_plus_modtran"
        or assets.get("earth_radius_km") != 6370.0
    ):
        raise VisibilityEnvironmentProbeError("direct input assets differ")

    matrix = _require_dict(spec.get("probe_matrix"), "probe_matrix")
    baseline = _require_dict(matrix.get("baseline"), "baseline")
    if (
        baseline.get("atmosphere_profile") != "us_standard"
        or baseline.get("observer_altitude_m") != 0.0
        or baseline.get("profile_surface_pressure_hpa") != 1013.0
    ):
        raise VisibilityEnvironmentProbeError("probe baseline differs")
    acceptance = _require_dict(spec.get("acceptance"), "acceptance")
    runs = expand_runs(spec, validate=False)
    if len(runs) != acceptance.get("expected_run_count") or len(runs) != 73:
        raise VisibilityEnvironmentProbeError("expanded run count differs")


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


def expand_runs(
    spec: dict[str, Any],
    *,
    validate: bool = True,
) -> list[dict[str, Any]]:
    if validate:
        if spec.get("schema") != SPEC_SCHEMA:
            raise VisibilityEnvironmentProbeError("unsupported environment probe schema")
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

    aod_sweep = matrix["aod_sweep"]
    for altitude in aod_sweep["target_true_altitude_deg"]:
        for aod in aod_sweep["aod550"]:
            add(
                (
                    f"aod_alt_{_value_token(altitude, 2)}"
                    f"_aod_{_value_token(aod, 3)}"
                ),
                "aod_sweep",
                target_true_altitude_deg=float(altitude),
                aod550=float(aod),
                wavelength_nm=float(aod_sweep["wavelength_nm"]),
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
        absolute = float(baseline["profile_surface_pressure_hpa"]) * float(ratio)
        add(
            f"pressure_ratio_{_value_token(ratio, 3)}",
            "pressure_sweep",
            pressure_ratio=float(ratio),
            pressure_override_hpa=absolute,
            wavelength_nm=float(pressure["wavelength_nm"]),
            target_true_altitude_deg=float(
                pressure["target_true_altitude_deg"]
            ),
            aod550=float(pressure["aod550"]),
        )

    repeat_of = matrix["exact_repeat_of"]
    original = next((run for run in runs if run["run_id"] == repeat_of), None)
    if original is None:
        raise VisibilityEnvironmentProbeError("exact-repeat target is absent")
    repeat = dict(original)
    repeat["run_id"] = f"repeat_{repeat_of}"
    repeat["kind"] = "exact_repeat"
    repeat["repeat_of"] = repeat_of
    runs.append(repeat)

    ids = [run["run_id"] for run in runs]
    if len(ids) != len(set(ids)):
        raise VisibilityEnvironmentProbeError("expanded run IDs are not unique")
    return runs


def inspect_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(path)
    runs = expand_runs(spec)
    counts: dict[str, int] = defaultdict(int)
    for run in runs:
        counts[run["kind"]] += 1
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "run_count": len(runs),
        "run_kind_counts": dict(sorted(counts.items())),
        "named_aerosol_profile_count": len(
            spec["environment_contract"]["aerosol"]["named_profiles"]
        ),
        "pressure_coordinate": spec["environment_contract"]["surface_pressure"][
            "table_coordinate"
        ],
        "temperature_override_admitted": False,
        "relative_humidity_override_admitted": False,
        "production_data_pack_authorized": False,
        "engine_changes_authorized": False,
    }


def render_input(run: dict[str, Any], spec: dict[str, Any]) -> str:
    oracle = spec["direct_extinction_oracle"]
    assets = oracle["input_assets"]
    cross_sections = assets["cross_sections"]
    target_altitude = float(run["target_true_altitude_deg"])
    if not 0.0 < target_altitude <= 45.0:
        raise VisibilityEnvironmentProbeError("target altitude is out of probe range")
    aod = float(run["aod550"])
    alpha = float(run["angstrom_exponent"])
    beta = _canonical_float(aod * (0.55**alpha))
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        (
            f"atmosphere_file {DATA_LINK_NAME}/"
            f"{assets['atmosphere_path']}"
        ),
        (
            f"source solar {DATA_LINK_NAME}/"
            f"{assets['solar_source_path']}"
        ),
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
        lines.append(
            f"pressure {_format_number(run['pressure_override_hpa'])}"
        )
    lines.extend(
        [
            f"mol_modify O3 {_format_number(run['ozone_du'])} DU",
            f"albedo {_format_number(run['ground_albedo'])}",
            "aerosol_default",
            f"aerosol_vulcan {run['vulcan']}",
            f"aerosol_haze {run['haze']}",
            f"aerosol_season {run['season']}",
            (
                f"aerosol_angstrom {_format_number(alpha)} "
                f"{_format_number(beta)}"
            ),
        ]
    )
    if run["aerosol_ssa_zero"]:
        lines.append(oracle["aerosol_scattering_override"])
    lines.extend(
        [
            f"sza {_format_number(90.0 - target_altitude)}",
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
    rendered = "\n".join(lines) + "\n"
    forbidden = (
        "altitude ",
        "mc_spherical",
        "mol_abs_param reptran",
        "aerosol_visibility",
        "rh_file",
        "radiosonde",
    )
    if any(token in rendered for token in forbidden):
        raise VisibilityEnvironmentProbeError(
            "rendered input crossed the scientific boundary"
        )
    if run["aerosol_ssa_zero"] != (
        oracle["aerosol_scattering_override"] in lines
    ):
        raise VisibilityEnvironmentProbeError(
            "aerosol scattering override rendering differs"
        )
    return rendered


def parse_output(
    text: str,
    run: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise VisibilityEnvironmentProbeError(
            f"unexpected output row count for {run['run_id']}: {len(lines)}"
        )
    fields = lines[0].split()
    if len(fields) != 2:
        raise VisibilityEnvironmentProbeError(
            f"unexpected output columns for {run['run_id']}"
        )
    try:
        wavelength = float(fields[0])
        horizontal = float(fields[1])
    except ValueError as exc:
        raise VisibilityEnvironmentProbeError(
            f"non-numeric output for {run['run_id']}"
        ) from exc
    if not math.isclose(
        wavelength,
        float(run["wavelength_nm"]),
        rel_tol=0.0,
        abs_tol=5.0e-4,
    ):
        raise VisibilityEnvironmentProbeError(
            f"output wavelength differs for {run['run_id']}"
        )
    sine_altitude = math.sin(
        math.radians(float(run["target_true_altitude_deg"]))
    )
    transmission = _canonical_float(horizontal / sine_altitude)
    if (
        not math.isfinite(horizontal)
        or not math.isfinite(transmission)
        or horizontal < 0.0
        or transmission < 0.0
        or transmission
        > 1.0
        + float(spec["acceptance"]["direct_transmission_upper_tolerance"])
    ):
        raise VisibilityEnvironmentProbeError(
            f"direct transmission is out of range for {run['run_id']}"
        )
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


def _verify_declared_repo_file(
    predecessor: dict[str, Any],
    role: str,
) -> Path:
    path = (REPO_ROOT / predecessor[f"{role}_path"]).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise VisibilityEnvironmentProbeError(
            f"predecessor {role} leaves repository"
        ) from exc
    if (
        not path.is_file()
        or path.stat().st_size != predecessor[f"{role}_bytes"]
        or _sha256_file(path) != predecessor[f"{role}_sha256"]
    ):
        raise VisibilityEnvironmentProbeError(
            f"predecessor {role} receipt differs"
        )
    return path


def _verify_declared_source_file(
    root: Path,
    receipt: dict[str, Any],
    label: str,
) -> Path:
    path = (root / receipt["path"]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise VisibilityEnvironmentProbeError(f"{label} leaves source root") from exc
    if (
        not path.is_file()
        or path.stat().st_size != receipt["bytes"]
        or _sha256_file(path) != receipt["sha256"]
    ):
        raise VisibilityEnvironmentProbeError(f"{label} receipt differs")
    return path


def _run_uvspec(
    uvspec: Path,
    data_root: Path,
    run_dir: Path,
    input_text: str,
) -> dict[str, Any]:
    if not run_dir.is_dir() or any(run_dir.iterdir()):
        raise VisibilityEnvironmentProbeError("run directory must begin empty")
    (run_dir / "input.inp").write_text(input_text, encoding="utf-8")
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
            raise VisibilityEnvironmentProbeError(
                f"uvspec syntax check failed in {run_dir.name}"
            )
        completed = subprocess.run(
            [str(uvspec)],
            cwd=run_dir,
            input=input_text,
            text=True,
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
            raise VisibilityEnvironmentProbeError(
                f"uvspec failed in {run_dir.name}"
            )
        if not (run_dir / "randomseed").is_file():
            raise VisibilityEnvironmentProbeError(
                f"uvspec random-seed receipt is missing in {run_dir.name}"
            )
        return {"stdout": completed.stdout}
    finally:
        if data_link.is_symlink():
            data_link.unlink()


def _write_run(
    output_root: Path,
    uvspec: Path,
    data_root: Path,
    run: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    final_dir = output_root / run["run_id"]
    if final_dir.exists():
        raise VisibilityEnvironmentProbeError(
            f"run directory already exists: {final_dir}"
        )
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{run['run_id']}.", dir=output_root)
    )
    try:
        input_text = render_input(run, spec)
        completed = _run_uvspec(uvspec, data_root, temp_dir, input_text)
        result = parse_output(completed["stdout"], run, spec)
        result_payload = {
            "schema": RUN_SCHEMA,
            "run": run,
            "result": result,
        }
        (temp_dir / "result.json").write_bytes(
            _canonical_json_bytes(result_payload)
        )
        present = {path.name for path in temp_dir.iterdir() if path.is_file()}
        if present != RUN_FILES:
            raise VisibilityEnvironmentProbeError(
                f"run file inventory differs for {run['run_id']}: {sorted(present)}"
            )
        os.replace(temp_dir, final_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    files = [
        _file_receipt(final_dir / name, relative_to=output_root)
        for name in sorted(RUN_FILES)
    ]
    return {
        "run_id": run["run_id"],
        "kind": run["kind"],
        "files": files,
        "result": result,
    }


def _strict(values: list[float], direction: str) -> bool:
    if direction == "decreasing":
        return all(left > right for left, right in zip(values, values[1:]))
    if direction == "increasing":
        return all(left < right for left, right in zip(values, values[1:]))
    raise VisibilityEnvironmentProbeError(f"unknown monotonic direction: {direction}")


def summarize(
    output_root: Path,
    runs: list[dict[str, Any]],
    run_receipts: list[dict[str, Any]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    run_by_id = {run["run_id"]: run for run in runs}
    result_by_id = {receipt["run_id"]: receipt["result"] for receipt in run_receipts}

    def stdout_bytes(run_id: str) -> bytes:
        return (output_root / run_id / "stdout.txt").read_bytes()

    albedo_ids = [
        run["run_id"] for run in runs if run["kind"] == "albedo_direct_invariance"
    ]
    albedo_hashes = {_sha256_bytes(stdout_bytes(run_id)) for run_id in albedo_ids}

    haze_groups: dict[int, list[str]] = defaultdict(list)
    for run in runs:
        if run["kind"] == "named_aerosol_direct_invariance":
            haze_groups[int(run["season"])].append(run["run_id"])
    haze_group_hash_counts = {
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
    diagnostic_distinct = len(
        {_sha256_bytes(stdout_bytes(run_id)) for run_id in diagnostic_ids}
    )

    aod_rows: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run["kind"] == "aod_sweep":
            aod_rows[float(run["target_true_altitude_deg"])].append(run)
    aod_summary: list[dict[str, Any]] = []
    for altitude, rows in sorted(aod_rows.items()):
        ordered = sorted(rows, key=lambda row: float(row["aod550"]))
        transmissions = [
            result_by_id[row["run_id"]]["direct_spectral_transmission"]
            for row in ordered
        ]
        clear = transmissions[0]
        tau_per_aod = []
        for row, transmission in zip(ordered[1:], transmissions[1:]):
            aod = float(row["aod550"])
            if transmission <= 0.0 or clear <= 0.0:
                value = math.inf
            else:
                value = _canonical_float(
                    -math.log(transmission / clear) / aod
                )
            tau_per_aod.append(value)
        finite = [value for value in tau_per_aod if math.isfinite(value)]
        spread = (
            _canonical_float(max(finite) / min(finite))
            if finite
            else math.inf
        )
        aod_summary.append(
            {
                "target_true_altitude_deg": altitude,
                "strictly_decreasing": _strict(transmissions, "decreasing"),
                "tau_per_aod_minimum": min(finite) if finite else math.inf,
                "tau_per_aod_maximum": max(finite) if finite else math.inf,
                "tau_per_aod_ratio_spread": spread,
            }
        )

    angstrom_rows: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run["kind"] == "angstrom_sweep":
            angstrom_rows[float(run["wavelength_nm"])].append(run)
    angstrom_summary: dict[str, Any] = {}
    for wavelength, rows in sorted(angstrom_rows.items()):
        ordered = sorted(rows, key=lambda row: float(row["angstrom_exponent"]))
        transmissions = [
            result_by_id[row["run_id"]]["direct_spectral_transmission"]
            for row in ordered
        ]
        stdout_hash_count = len(
            {_sha256_bytes(stdout_bytes(row["run_id"])) for row in ordered}
        )
        angstrom_summary[_format_number(wavelength)] = {
            "stdout_hash_count": stdout_hash_count,
            "strictly_decreasing": _strict(transmissions, "decreasing"),
            "strictly_increasing": _strict(transmissions, "increasing"),
        }

    def sweep_values(kind: str, key: str) -> tuple[list[float], list[float]]:
        rows = sorted(
            (run for run in runs if run["kind"] == kind),
            key=lambda run: float(run[key]),
        )
        return (
            [float(run[key]) for run in rows],
            [
                result_by_id[run["run_id"]]["direct_spectral_transmission"]
                for run in rows
            ],
        )

    ozone_values, ozone_transmissions = sweep_values("ozone_sweep", "ozone_du")
    pressure_values, pressure_transmissions = sweep_values(
        "pressure_sweep",
        "pressure_ratio",
    )

    repeated = next(run for run in runs if run["kind"] == "exact_repeat")
    original = run_by_id[repeated["repeat_of"]]
    repeat_file_names = (
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
                (output_root / original["run_id"] / name).read_bytes()
                == (output_root / repeated["run_id"] / name).read_bytes()
            ),
        }
        for name in repeat_file_names
    ]

    summary = {
        "run_count": len(runs),
        "albedo_direct": {
            "run_ids": albedo_ids,
            "stdout_hash_count": len(albedo_hashes),
        },
        "named_aerosol_direct": {
            "same_season_stdout_hash_counts": haze_group_hash_counts,
            "season_representatives_differ": (
                season_representatives[1] != season_representatives[2]
            ),
        },
        "raw_delta_m_haze_diagnostic": {
            "run_ids": diagnostic_ids,
            "distinct_stdout_count": diagnostic_distinct,
        },
        "aod_sweep": aod_summary,
        "angstrom_sweep": angstrom_summary,
        "ozone_sweep": {
            "ozone_du": ozone_values,
            "strictly_decreasing": _strict(
                ozone_transmissions,
                "decreasing",
            ),
        },
        "pressure_sweep": {
            "pressure_ratio": pressure_values,
            "strictly_decreasing": _strict(
                pressure_transmissions,
                "decreasing",
            ),
        },
        "exact_repeat": {
            "original_run_id": original["run_id"],
            "repeat_run_id": repeated["run_id"],
            "files": repeat_files,
            "all_required_files_byte_identical": all(
                row["byte_identical"] for row in repeat_files
            ),
        },
    }
    enforce_acceptance(summary, spec)
    return summary


def enforce_acceptance(summary: dict[str, Any], spec: dict[str, Any]) -> None:
    acceptance = spec["acceptance"]
    if summary["run_count"] != acceptance["expected_run_count"]:
        raise VisibilityEnvironmentProbeError("run count fails acceptance")
    if (
        acceptance["exact_repeat_byte_identity_required"]
        and not summary["exact_repeat"]["all_required_files_byte_identical"]
    ):
        raise VisibilityEnvironmentProbeError("exact repeat is not byte-identical")
    if (
        acceptance["albedo_direct_stdout_identity_required"]
        and summary["albedo_direct"]["stdout_hash_count"] != 1
    ):
        raise VisibilityEnvironmentProbeError("albedo contaminated direct output")
    if acceptance["same_season_haze_direct_stdout_identity_required"] and any(
        count != 1
        for count in summary["named_aerosol_direct"][
            "same_season_stdout_hash_counts"
        ].values()
    ):
        raise VisibilityEnvironmentProbeError(
            "haze contaminated admitted direct extinction"
        )
    if (
        acceptance["raw_delta_m_haze_distinct_output_required"]
        and summary["raw_delta_m_haze_diagnostic"]["distinct_stdout_count"] <= 1
    ):
        raise VisibilityEnvironmentProbeError(
            "raw delta-M diagnostic did not expose haze dependence"
        )
    if (
        acceptance["aod_transmission_strictly_decreasing_required"]
        and not all(row["strictly_decreasing"] for row in summary["aod_sweep"])
    ):
        raise VisibilityEnvironmentProbeError("AOD sweep is not monotonic")
    near_horizon = min(
        summary["aod_sweep"],
        key=lambda row: row["target_true_altitude_deg"],
    )
    if near_horizon["tau_per_aod_ratio_spread"] < acceptance[
        "near_horizon_aod_tau_per_aod_ratio_spread_minimum"
    ]:
        raise VisibilityEnvironmentProbeError(
            "AOD nonlinearity diagnostic is below the frozen bound"
        )
    angstrom = summary["angstrom_sweep"]
    if (
        acceptance["angstrom_550_stdout_identity_required"]
        and angstrom["550"]["stdout_hash_count"] != 1
    ):
        raise VisibilityEnvironmentProbeError("AOD550 changed across Angstrom alpha")
    if (
        acceptance["angstrom_400_transmission_strictly_decreasing_required"]
        and not angstrom["400"]["strictly_decreasing"]
    ):
        raise VisibilityEnvironmentProbeError("400 nm Angstrom response differs")
    if (
        acceptance["angstrom_780_transmission_strictly_increasing_required"]
        and not angstrom["780"]["strictly_increasing"]
    ):
        raise VisibilityEnvironmentProbeError("780 nm Angstrom response differs")
    if (
        acceptance["ozone_600_transmission_strictly_decreasing_required"]
        and not summary["ozone_sweep"]["strictly_decreasing"]
    ):
        raise VisibilityEnvironmentProbeError("ozone response differs")
    if (
        acceptance["pressure_550_transmission_strictly_decreasing_required"]
        and not summary["pressure_sweep"]["strictly_decreasing"]
    ):
        raise VisibilityEnvironmentProbeError("pressure response differs")
    if (
        acceptance["season_direct_output_difference_required"]
        and not summary["named_aerosol_direct"][
            "season_representatives_differ"
        ]
    ):
        raise VisibilityEnvironmentProbeError("aerosol seasons did not differ")


def build_artifact(
    *,
    spec_path: Path,
    source_archive: Path,
    libradtran_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    spec = load_spec(spec_path)
    source_archive = source_archive.resolve()
    libradtran_root = libradtran_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise VisibilityEnvironmentProbeError(
            "output root already exists; artifacts are immutable"
        )
    if (
        not source_archive.is_file()
        or source_archive.stat().st_size
        != spec["libradtran_source"]["archive_bytes"]
        or _sha256_file(source_archive)
        != spec["libradtran_source"]["archive_sha256"]
    ):
        raise VisibilityEnvironmentProbeError("source archive receipt differs")
    if not libradtran_root.is_dir():
        raise VisibilityEnvironmentProbeError("libRadtran root is missing")
    data_root = (libradtran_root / "data").resolve()
    uvspec = (libradtran_root / "bin" / "uvspec").resolve()
    if not data_root.is_dir() or not uvspec.is_file():
        raise VisibilityEnvironmentProbeError("built libRadtran tree is incomplete")
    if _sha256_file(uvspec) != spec["libradtran_source"]["uvspec_sha256"]:
        raise VisibilityEnvironmentProbeError("uvspec executable receipt differs")
    version = subprocess.run(
        [str(uvspec), "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    version_text = (version.stdout or version.stderr).strip()
    if version.returncode != 0 or spec["libradtran_source"][
        "uvspec_version"
    ] not in version_text:
        raise VisibilityEnvironmentProbeError("uvspec version differs")

    predecessor = spec["predecessor"]
    predecessor_paths = {
        role: _verify_declared_repo_file(predecessor, role)
        for role in ("spec", "builder", "validator", "checkpoint")
    }
    source_paths = [
        _verify_declared_source_file(
            libradtran_root,
            receipt,
            f"source file {receipt['path']}",
        )
        for receipt in spec["libradtran_source"]["source_files"]
    ]
    shettle_paths = [
        _verify_declared_source_file(
            libradtran_root,
            receipt,
            f"Shettle file {receipt['path']}",
        )
        for receipt in spec["libradtran_source"]["shettle_tau550_files"]
    ]
    if not VALIDATOR_PATH.is_file():
        raise VisibilityEnvironmentProbeError("independent validator is missing")
    tooling_paths = {
        "spec": spec_path,
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH.resolve(),
    }
    tooling = {
        role: _file_receipt(path, relative_to=REPO_ROOT)
        for role, path in tooling_paths.items()
    }
    predecessor_receipts = {
        role: _file_receipt(path, relative_to=REPO_ROOT)
        for role, path in predecessor_paths.items()
    }
    source_receipts = [
        _file_receipt(path, relative_to=libradtran_root)
        for path in source_paths
    ]
    shettle_receipts = [
        _file_receipt(path, relative_to=libradtran_root)
        for path in shettle_paths
    ]
    assets = spec["direct_extinction_oracle"]["input_assets"]
    runtime_asset_paths = [
        data_root / assets["atmosphere_path"],
        data_root / assets["solar_source_path"],
    ]
    runtime_assets = [
        _file_receipt(path, relative_to=libradtran_root)
        for path in runtime_asset_paths
    ]
    generation_fingerprint = _sha256_bytes(
        _compact_json_bytes(
            {
                "spec": tooling["spec"],
                "builder": tooling["builder"],
                "validator": tooling["validator"],
                "predecessor": predecessor_receipts,
                "source_archive": _file_receipt(source_archive),
                "uvspec": _file_receipt(uvspec, relative_to=libradtran_root),
                "source_files": source_receipts,
                "shettle_files": shettle_receipts,
                "runtime_assets": runtime_assets,
            }
        )
    )

    output_root.mkdir(parents=True)
    runs = expand_runs(spec)
    try:
        run_receipts = [
            _write_run(output_root, uvspec, data_root, run, spec) for run in runs
        ]
        summary = summarize(output_root, runs, run_receipts, spec)
        manifest = {
            "schema": ARTIFACT_SCHEMA,
            "status": ARTIFACT_STATUS,
            "spec_id": spec["spec_id"],
            "generation_fingerprint": generation_fingerprint,
            "tooling": tooling,
            "predecessor": predecessor_receipts,
            "source": {
                "archive": _file_receipt(source_archive),
                "uvspec": _file_receipt(uvspec, relative_to=libradtran_root),
                "uvspec_version": version_text,
                "source_files": source_receipts,
                "shettle_tau550_files": shettle_receipts,
                "runtime_assets": runtime_assets,
            },
            "runtime_boundary": spec["runtime_boundary"],
            "runs": run_receipts,
            "summary": summary,
        }
        (output_root / MANIFEST_NAME).write_bytes(
            _canonical_json_bytes(manifest)
        )
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
        )
        if validation.returncode != 0:
            raise VisibilityEnvironmentProbeError(
                "independent validation failed:\n"
                + validation.stdout
                + validation.stderr
            )
        return manifest
    except Exception:
        shutil.rmtree(output_root, ignore_errors=True)
        raise


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or inspect the Phase 1 environmental-contract probe."
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--inspect-spec", action="store_true")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--libradtran-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.inspect_spec:
        print(
            json.dumps(
                inspect_spec(args.spec),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if (
        args.source_archive is None
        or args.libradtran_root is None
        or args.output is None
    ):
        raise VisibilityEnvironmentProbeError(
            "--source-archive, --libradtran-root, and --output are required"
        )
    manifest = build_artifact(
        spec_path=args.spec,
        source_archive=args.source_archive,
        libradtran_root=args.libradtran_root,
        output_root=args.output,
    )
    print(
        json.dumps(
            {
                "artifact": str(args.output.resolve()),
                "manifest_sha256": _sha256_file(
                    args.output.resolve() / MANIFEST_NAME
                ),
                "generation_fingerprint": manifest["generation_fingerprint"],
                "run_count": manifest["summary"]["run_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VisibilityEnvironmentProbeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
