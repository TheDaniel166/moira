"""Build reproducible libRadtran/MYSTIC Phase 1 reference-lab artifacts.

This is an offline research build tool. It verifies a caller-supplied,
checksum-pinned libRadtran source archive and invokes a caller-supplied
libRadtran build. It never downloads anything and is not imported by Moira's
installed runtime.

The Phase 1 specification deliberately authorizes only convergence,
geometry-smoke, and direct-transmission-smoke profiles. It does not authorize
a production visibility data pack or a full Cartesian expansion of the
candidate domain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT / "scripts" / "visibility_reference_lab" / "phase1_lab_spec.json"
)
SPEC_SCHEMA = "moira.visibility-reference-lab-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-reference-lab-artifact/v1"
CASE_SCHEMA = "moira.visibility-reference-lab-case/v1"
DATA_LINK_NAME = "libradtran_data"
EXPECTED_OUTPUTS = ("mc.rad.spc", "mc.rad.std.spc")
CALCULATION_DIRECTIONAL_RADIANCE = "directional_twilight_radiance"
CALCULATION_DIRECT_TRANSMISSION = "direct_spectral_transmission"
MYSTIC_CASE_FILES = frozenset(
    {
        "input.inp",
        "mc.flx.spc",
        "mc.flx.std.spc",
        "mc.rad.spc",
        "mc.rad.std.spc",
        "mc0.rad",
        "mc0.rad.std",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    }
)
DIRECT_TRANSMISSION_CASE_FILES = frozenset(
    {
        "input.inp",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    }
)
class VisibilityLabError(ValueError):
    """Raised when a reference-lab input or artifact violates its contract."""


def canonical_json_bytes(payload: object) -> bytes:
    """Return the canonical JSON representation used by lab artifacts."""
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_receipt(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    label = path.relative_to(relative_to).as_posix() if relative_to else path.name
    return {
        "path": label,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def tree_receipt(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    if not path.is_dir():
        raise VisibilityLabError(f"source data tree not found: {path}")
    members = sorted(
        member
        for member in path.rglob("*")
        if member.is_file()
        and not member.name.startswith("._")
        and member.name not in {"Makefile", "Makefile.in"}
    )
    if not members:
        raise VisibilityLabError(f"source data tree is empty: {path}")
    digest = hashlib.sha256()
    total_bytes = 0
    for member in members:
        relative = member.relative_to(path).as_posix()
        member_bytes = member.stat().st_size
        member_sha256 = sha256_file(member)
        digest.update(
            f"{relative}\0{member_bytes}\0{member_sha256}\n".encode("utf-8")
        )
        total_bytes += member_bytes
    label = path.relative_to(relative_to).as_posix() if relative_to else path.name
    return {
        "path": label,
        "file_count": len(members),
        "bytes": total_bytes,
        "tree_sha256": digest.hexdigest(),
        "tree_hash_law": "sha256(relative_path_nul_bytes_nul_file_sha256_lf)",
        "excluded_names": ["._*", "Makefile", "Makefile.in"],
    }


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VisibilityLabError("lab specification must be a JSON object")
    validate_spec(payload)
    return payload


def _strictly_increasing(values: list[Any], label: str) -> None:
    if not values or not all(isinstance(value, (int, float)) for value in values):
        raise VisibilityLabError(f"{label} must be a non-empty numeric array")
    floats = [float(value) for value in values]
    if not all(math.isfinite(value) for value in floats):
        raise VisibilityLabError(f"{label} must contain only finite values")
    if any(right <= left for left, right in zip(floats, floats[1:], strict=False)):
        raise VisibilityLabError(f"{label} must be strictly increasing")


def _require_range(value: Any, label: str, low: float, high: float) -> float:
    if not isinstance(value, (int, float)):
        raise VisibilityLabError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise VisibilityLabError(f"{label} must be in [{low}, {high}]")
    return number


def _validate_relative_source_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("data/"):
        raise VisibilityLabError(f"{label} must be a relative libRadtran data/ path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise VisibilityLabError(f"{label} must not escape the libRadtran data tree")
    return value


def _validate_atmosphere_case(
    case: dict[str, Any],
    spec: dict[str, Any],
    *,
    require_wavelength: bool = True,
) -> None:
    _require_range(case.get("observer_altitude_m"), "observer_altitude_m", 0.0, 5000.0)
    _require_range(
        case.get("surface_pressure_hpa"),
        "surface_pressure_hpa",
        500.0,
        1100.0,
    )
    _require_range(case.get("aod550"), "aod550", 0.0, 1.0)
    _require_range(
        case.get("angstrom_exponent"),
        "angstrom_exponent",
        0.0,
        2.5,
    )
    _require_range(case.get("ozone_du"), "ozone_du", 200.0, 500.0)
    _require_range(case.get("ground_albedo"), "ground_albedo", 0.0, 1.0)

    source_datasets = spec["source_datasets"]
    if case.get("atmosphere_profile") not in source_datasets["atmosphere_files"]:
        raise VisibilityLabError("case names an unknown atmosphere_profile")
    if case.get("aerosol_profile") not in source_datasets["aerosol_profiles"]:
        raise VisibilityLabError("case names an unknown aerosol_profile")

    if "wavelength_nm" in case:
        _require_range(case["wavelength_nm"], "wavelength_nm", 380.0, 780.0)
    elif require_wavelength:
        raise VisibilityLabError("runnable case is missing wavelength_nm")


def _validate_random_seed(value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisibilityLabError("random_seed must be an integer")
    if not 0 < value <= 2_147_483_647:
        raise VisibilityLabError("random_seed must be in [1, 2147483647]")


def validate_case(
    case: dict[str, Any],
    spec: dict[str, Any],
    *,
    require_run_controls: bool = True,
) -> None:
    _require_range(
        case.get("solar_center_altitude_deg"),
        "solar_center_altitude_deg",
        -18.0,
        0.0,
    )
    target_altitude = _require_range(
        case.get("target_true_altitude_deg"),
        "target_true_altitude_deg",
        0.0,
        45.0,
    )
    if target_altitude == 0.0:
        raise VisibilityLabError(
            "target_true_altitude_deg=0 is not representable because libRadtran "
            "forbids umu=0; the first pilot domain starts at 0.25 degrees"
        )
    _require_range(
        case.get("relative_solar_azimuth_deg"),
        "relative_solar_azimuth_deg",
        0.0,
        180.0,
    )
    _validate_atmosphere_case(
        case,
        spec,
        require_wavelength=require_run_controls,
    )

    if require_run_controls:
        photon_count = case.get("photon_count")
        if not isinstance(photon_count, int) or isinstance(photon_count, bool):
            raise VisibilityLabError("photon_count must be an integer")
        if photon_count <= 0:
            raise VisibilityLabError("photon_count must be positive")
        _validate_random_seed(case.get("random_seed"))


def validate_direct_transmission_case(
    case: dict[str, Any],
    spec: dict[str, Any],
) -> None:
    target_altitude = _require_range(
        case.get("target_true_altitude_deg"),
        "target_true_altitude_deg",
        0.0,
        45.0,
    )
    if target_altitude == 0.0:
        raise VisibilityLabError(
            "target_true_altitude_deg=0 cannot normalize direct irradiance; "
            "the first pilot domain starts at 0.25 degrees"
        )
    _validate_atmosphere_case(case, spec)
    _validate_random_seed(case.get("random_seed"))


def expected_case_files(case: dict[str, Any]) -> frozenset[str]:
    calculation_kind = case.get("calculation_kind")
    if calculation_kind == CALCULATION_DIRECTIONAL_RADIANCE:
        return MYSTIC_CASE_FILES
    if calculation_kind == CALCULATION_DIRECT_TRANSMISSION:
        return DIRECT_TRANSMISSION_CASE_FILES
    raise VisibilityLabError(f"unsupported calculation kind: {calculation_kind!r}")


def profile_model_id(spec: dict[str, Any], profile: str) -> str:
    if profile == "direct_transmission_smoke":
        return str(spec["direct_transmission_solver"]["model_id"])
    return str(spec["model_id"])


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != SPEC_SCHEMA:
        raise VisibilityLabError(f"unsupported lab specification: {spec.get('schema')!r}")
    if spec.get("status") != "research_pilot_not_runtime_data_pack":
        raise VisibilityLabError("Phase 1 specification must remain a research pilot")

    source = spec.get("source")
    if not isinstance(source, dict):
        raise VisibilityLabError("source receipt is missing")
    if source.get("version") != "2.0.6":
        raise VisibilityLabError("only libRadtran 2.0.6 is admitted")
    archive_sha256 = source.get("archive_sha256")
    if not isinstance(archive_sha256, str) or len(archive_sha256) != 64:
        raise VisibilityLabError("source archive_sha256 is invalid")
    if not isinstance(source.get("archive_bytes"), int) or source["archive_bytes"] <= 0:
        raise VisibilityLabError("source archive_bytes is invalid")

    boundary = spec.get("runtime_boundary")
    if not isinstance(boundary, dict):
        raise VisibilityLabError("runtime_boundary is missing")
    for field in (
        "network_allowed",
        "automatic_download_allowed",
        "engine_dependency_allowed",
        "engine_runtime_invocation_allowed",
    ):
        if boundary.get(field) is not False:
            raise VisibilityLabError(f"{field} must remain false")
    if boundary.get("generated_numerical_products_only") is not True:
        raise VisibilityLabError("only generated numerical products may cross the lab boundary")

    pilot_limits = spec.get("pilot_limits")
    if not isinstance(pilot_limits, dict):
        raise VisibilityLabError("pilot_limits is missing")
    if pilot_limits.get("observer_altitude_m") != [0.0]:
        raise VisibilityLabError("the initial MYSTIC pilot must remain sea-level only")
    if pilot_limits.get("minimum_target_true_altitude_deg") != 0.25:
        raise VisibilityLabError("the initial MYSTIC target-altitude floor must remain 0.25")
    if pilot_limits.get("production_data_pack_authorized") is not False:
        raise VisibilityLabError("the Phase 1 pilot must not authorize a production data pack")

    solver = spec.get("solver")
    if not isinstance(solver, dict):
        raise VisibilityLabError("solver receipt is missing")
    required_solver_values = {
        "rte_solver": "mystic",
        "geometry": "1D_spherical",
        "molecular_absorption": "crs",
        "variance_reduction": "vroom_on",
        "radiance_estimator": "escape",
        "random_seed_option": "mc_randomseed",
    }
    for key, expected in required_solver_values.items():
        if solver.get(key) != expected:
            raise VisibilityLabError(f"solver.{key} must be {expected!r}")
    if solver.get("serial_execution_required") is not True:
        raise VisibilityLabError("the Phase 1 pilot must execute serially")

    direct_solver = spec.get("direct_transmission_solver")
    if not isinstance(direct_solver, dict):
        raise VisibilityLabError("direct_transmission_solver receipt is missing")
    required_direct_solver_values = {
        "model_id": "libradtran_2_0_6_disort_pseudospherical_direct_v1",
        "rte_solver": "disort",
        "geometry": "pseudospherical",
        "number_of_streams": 16,
        "output_quantity": "transmittance",
        "output_columns": ["lambda", "edir"],
        "normalization": (
            "direct_transmission_equals_edir_divided_by_sin_"
            "target_true_altitude"
        ),
        "refraction": "disabled_true_geometric_line_of_sight",
        "random_seed_role": "fixed_nonoperative_uvspec_output_control",
        "serial_execution_required": True,
    }
    for key, expected in required_direct_solver_values.items():
        if direct_solver.get(key) != expected:
            raise VisibilityLabError(
                f"direct_transmission_solver.{key} must be {expected!r}"
            )

    source_datasets = spec.get("source_datasets")
    if not isinstance(source_datasets, dict):
        raise VisibilityLabError("source_datasets is missing")
    _validate_relative_source_path(
        source_datasets.get("solar_spectrum"),
        "source_datasets.solar_spectrum",
    )
    for name, relative_path in source_datasets.get("data_trees", {}).items():
        _validate_relative_source_path(relative_path, f"data_trees.{name}")
    for name, relative_path in source_datasets.get("atmosphere_files", {}).items():
        _validate_relative_source_path(relative_path, f"atmosphere_files.{name}")
    for name, profile in source_datasets.get("aerosol_profiles", {}).items():
        if not isinstance(profile, dict):
            raise VisibilityLabError(f"aerosol profile {name!r} must be an object")
        if profile.get("haze") not in {1, 4, 5, 6}:
            raise VisibilityLabError(f"aerosol profile {name!r} has invalid haze")
        if profile.get("season") not in {1, 2}:
            raise VisibilityLabError(f"aerosol profile {name!r} has invalid season")

    domain = spec.get("candidate_domain")
    if not isinstance(domain, dict):
        raise VisibilityLabError("candidate_domain is missing")
    if domain.get("sampling_law") != (
        "adaptive_sparse_design_required_no_cartesian_product_authorized"
    ):
        raise VisibilityLabError("a full Cartesian candidate-domain expansion is prohibited")
    for field in (
        "solar_center_altitude_deg",
        "target_true_altitude_deg",
        "relative_solar_azimuth_deg",
        "observer_altitude_m",
        "surface_pressure_hpa",
        "aod550",
        "angstrom_exponent",
        "ozone_du",
        "ground_albedo",
    ):
        _strictly_increasing(domain.get(field), f"candidate_domain.{field}")
    if 0.0 in [float(value) for value in domain["target_true_altitude_deg"]]:
        raise VisibilityLabError("the candidate target-altitude grid must not include umu=0")

    convergence = spec.get("convergence_profile")
    if not isinstance(convergence, dict):
        raise VisibilityLabError("convergence_profile is missing")
    base_case = dict(convergence.get("base_case", {}))
    base_case["photon_count"] = 1
    base_case["random_seed"] = 1
    validate_case(base_case, spec)
    _strictly_increasing(convergence.get("photon_counts"), "photon_counts")
    if not all(isinstance(value, int) for value in convergence["photon_counts"]):
        raise VisibilityLabError("photon_counts must contain integers")
    seeds = convergence.get("random_seeds")
    if not isinstance(seeds, list) or len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise VisibilityLabError("random_seeds must contain at least three unique values")
    if convergence.get("exact_repeat_seed") not in seeds:
        raise VisibilityLabError("exact_repeat_seed must be one of random_seeds")

    smoke_defaults = spec.get("geometry_smoke_defaults")
    if not isinstance(smoke_defaults, dict):
        raise VisibilityLabError("geometry_smoke_defaults is missing")
    smoke_ids: set[str] = set()
    for geometry in spec.get("geometry_smoke_cases", []):
        if not isinstance(geometry, dict):
            raise VisibilityLabError("geometry smoke case must be an object")
        case_id = geometry.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in smoke_ids:
            raise VisibilityLabError("geometry smoke case IDs must be non-empty and unique")
        smoke_ids.add(case_id)
        merged = dict(smoke_defaults)
        merged.update({key: value for key, value in geometry.items() if key != "case_id"})
        validate_case(merged, spec)

    direct_profile = spec.get("direct_transmission_profile")
    if not isinstance(direct_profile, dict):
        raise VisibilityLabError("direct_transmission_profile is missing")
    direct_defaults = direct_profile.get("defaults")
    direct_cases = direct_profile.get("cases")
    if not isinstance(direct_defaults, dict) or not isinstance(direct_cases, list):
        raise VisibilityLabError("direct transmission profile is malformed")
    direct_ids: set[str] = set()
    for direct in direct_cases:
        if not isinstance(direct, dict):
            raise VisibilityLabError("direct transmission case must be an object")
        case_id = direct.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in direct_ids:
            raise VisibilityLabError(
                "direct transmission case IDs must be non-empty and unique"
            )
        direct_ids.add(case_id)
        merged = dict(direct_defaults)
        merged.update({key: value for key, value in direct.items() if key != "case_id"})
        validate_direct_transmission_case(merged, spec)
    repeats = [direct for direct in direct_cases if "repeat_of" in direct]
    if len(repeats) != 1:
        raise VisibilityLabError(
            "direct transmission profile must contain exactly one repeat"
        )
    repeat_of = repeats[0].get("repeat_of")
    if (
        not isinstance(repeat_of, str)
        or repeat_of not in direct_ids
        or repeat_of == repeats[0]["case_id"]
    ):
        raise VisibilityLabError("direct transmission repeat target is invalid")

    holdout_ids: set[str] = set()
    for holdout in spec.get("reserved_holdout_cases", []):
        if not isinstance(holdout, dict):
            raise VisibilityLabError("reserved holdout must be an object")
        case_id = holdout.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in holdout_ids:
            raise VisibilityLabError("reserved holdout IDs must be non-empty and unique")
        holdout_ids.add(case_id)
        validate_case(holdout, spec, require_run_controls=False)


def _format_number(value: float | int) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return format(float(value), ".12g")


def render_mystic_input(case: dict[str, Any], spec: dict[str, Any]) -> str:
    """Render one deterministic, path-neutral libRadtran input file."""
    validate_case(case, spec)
    if float(case["observer_altitude_m"]) != 0.0:
        raise VisibilityLabError(
            "the initial MYSTIC pilot supports sea level only; libRadtran rejects "
            "its generic altitude option with MYSTIC, so nonzero observer altitude "
            "requires an admitted atmosphere/elevation construction"
        )
    source_datasets = spec["source_datasets"]
    atmosphere_path = source_datasets["atmosphere_files"][case["atmosphere_profile"]]
    solar_path = source_datasets["solar_spectrum"]
    aerosol = source_datasets["aerosol_profiles"][case["aerosol_profile"]]
    solver = spec["solver"]

    solar_zenith = 90.0 - float(case["solar_center_altitude_deg"])
    viewing_umu = -math.sin(math.radians(float(case["target_true_altitude_deg"])))
    angstrom_beta = float(case["aod550"]) * (
        0.55 ** float(case["angstrom_exponent"])
    )
    data_atmosphere = f"{DATA_LINK_NAME}/{atmosphere_path.removeprefix('data/')}"
    data_solar = f"{DATA_LINK_NAME}/{solar_path.removeprefix('data/')}"
    cross_sections = solver["cross_sections"]

    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        f"atmosphere_file {data_atmosphere}",
        f"source solar {data_solar}",
        "mol_abs_param crs",
        f"crs_model rayleigh {cross_sections['rayleigh']}",
        f"crs_model O3 {cross_sections['O3']}",
        f"crs_model NO2 {cross_sections['NO2']}",
        f"crs_model O4 {cross_sections['O4']}",
        (
            f"wavelength {_format_number(case['wavelength_nm'])} "
            f"{_format_number(case['wavelength_nm'])}"
        ),
        f"sza {_format_number(solar_zenith)}",
        "phi0 0",
        f"earth_radius {_format_number(solver['earth_radius_km'])}",
        f"pressure {_format_number(case['surface_pressure_hpa'])}",
        f"mol_modify O3 {_format_number(case['ozone_du'])} DU",
        f"albedo {_format_number(case['ground_albedo'])}",
        "aerosol_default",
        f"aerosol_haze {aerosol['haze']}",
        f"aerosol_season {aerosol['season']}",
        (
            f"aerosol_angstrom {_format_number(case['angstrom_exponent'])} "
            f"{_format_number(angstrom_beta)}"
        ),
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {case['photon_count']}",
        f"mc_randomseed {case['random_seed']}",
        "mc_escape",
        "mc_std",
        "mc_vroom on",
        "zout 0",
        f"umu {_format_number(viewing_umu)}",
        f"phi {_format_number(case['relative_solar_azimuth_deg'])}",
        "quiet",
    ]
    return "\n".join(lines) + "\n"


def render_direct_transmission_input(
    case: dict[str, Any],
    spec: dict[str, Any],
) -> str:
    """Render one deterministic pseudo-spherical direct-transmission input."""
    validate_direct_transmission_case(case, spec)
    if float(case["observer_altitude_m"]) != 0.0:
        raise VisibilityLabError(
            "the initial direct-transmission pilot supports sea level only; "
            "nonzero observer altitude requires an admitted truncated-atmosphere "
            "construction"
        )
    source_datasets = spec["source_datasets"]
    atmosphere_path = source_datasets["atmosphere_files"][case["atmosphere_profile"]]
    solar_path = source_datasets["solar_spectrum"]
    aerosol = source_datasets["aerosol_profiles"][case["aerosol_profile"]]
    radiance_solver = spec["solver"]
    direct_solver = spec["direct_transmission_solver"]

    target_zenith = 90.0 - float(case["target_true_altitude_deg"])
    angstrom_beta = float(case["aod550"]) * (
        0.55 ** float(case["angstrom_exponent"])
    )
    data_atmosphere = f"{DATA_LINK_NAME}/{atmosphere_path.removeprefix('data/')}"
    data_solar = f"{DATA_LINK_NAME}/{solar_path.removeprefix('data/')}"
    cross_sections = radiance_solver["cross_sections"]

    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        f"atmosphere_file {data_atmosphere}",
        f"source solar {data_solar}",
        "mol_abs_param crs",
        f"crs_model rayleigh {cross_sections['rayleigh']}",
        f"crs_model O3 {cross_sections['O3']}",
        f"crs_model NO2 {cross_sections['NO2']}",
        f"crs_model O4 {cross_sections['O4']}",
        (
            f"wavelength {_format_number(case['wavelength_nm'])} "
            f"{_format_number(case['wavelength_nm'])}"
        ),
        f"sza {_format_number(target_zenith)}",
        "phi0 0",
        f"earth_radius {_format_number(radiance_solver['earth_radius_km'])}",
        f"pressure {_format_number(case['surface_pressure_hpa'])}",
        f"mol_modify O3 {_format_number(case['ozone_du'])} DU",
        f"albedo {_format_number(case['ground_albedo'])}",
        "aerosol_default",
        f"aerosol_haze {aerosol['haze']}",
        f"aerosol_season {aerosol['season']}",
        (
            f"aerosol_angstrom {_format_number(case['angstrom_exponent'])} "
            f"{_format_number(angstrom_beta)}"
        ),
        f"rte_solver {direct_solver['rte_solver']}",
        direct_solver["geometry"],
        f"number_of_streams {direct_solver['number_of_streams']}",
        f"output_quantity {direct_solver['output_quantity']}",
        f"output_user {' '.join(direct_solver['output_columns'])}",
        f"mc_randomseed {case['random_seed']}",
        "zout 0",
        "quiet",
    ]
    return "\n".join(lines) + "\n"


def expand_profile(spec: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if profile == "convergence":
        convergence = spec["convergence_profile"]
        for photon_count in convergence["photon_counts"]:
            for random_seed in convergence["random_seeds"]:
                case = dict(convergence["base_case"])
                case.update(
                    {
                        "case_id": (
                            f"convergence_n{photon_count:09d}_s{random_seed:010d}"
                        ),
                        "calculation_kind": CALCULATION_DIRECTIONAL_RADIANCE,
                        "photon_count": photon_count,
                        "random_seed": random_seed,
                    }
                )
                validate_case(case, spec)
                cases.append(case)
        repeat_case = dict(convergence["base_case"])
        repeat_case.update(
            {
                "case_id": "convergence_exact_repeat",
                "calculation_kind": CALCULATION_DIRECTIONAL_RADIANCE,
                "photon_count": convergence["photon_counts"][0],
                "random_seed": convergence["exact_repeat_seed"],
                "repeat_of": (
                    f"convergence_n{convergence['photon_counts'][0]:09d}_"
                    f"s{convergence['exact_repeat_seed']:010d}"
                ),
            }
        )
        validate_case(repeat_case, spec)
        cases.append(repeat_case)
    elif profile == "geometry_smoke":
        defaults = spec["geometry_smoke_defaults"]
        for geometry in spec["geometry_smoke_cases"]:
            case = dict(defaults)
            case.update({key: value for key, value in geometry.items() if key != "case_id"})
            case["case_id"] = f"geometry_{geometry['case_id']}"
            case["calculation_kind"] = CALCULATION_DIRECTIONAL_RADIANCE
            validate_case(case, spec)
            cases.append(case)
    elif profile == "direct_transmission_smoke":
        direct_profile = spec["direct_transmission_profile"]
        defaults = direct_profile["defaults"]
        for direct in direct_profile["cases"]:
            case = dict(defaults)
            case.update({key: value for key, value in direct.items() if key != "case_id"})
            case["case_id"] = f"direct_{direct['case_id']}"
            case["calculation_kind"] = CALCULATION_DIRECT_TRANSMISSION
            if "repeat_of" in case:
                case["repeat_of"] = f"direct_{case['repeat_of']}"
            validate_direct_transmission_case(case, spec)
            cases.append(case)
    else:
        raise VisibilityLabError(f"unsupported build profile: {profile!r}")
    return cases


def _run_text(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise VisibilityLabError(f"{command[0]} failed: {detail}")
    return (completed.stdout + completed.stderr).strip()


def verify_generator(
    spec: dict[str, Any],
    *,
    source_archive: Path,
    libradtran_root: Path,
) -> dict[str, Any]:
    source_archive = source_archive.resolve()
    libradtran_root = libradtran_root.resolve()
    if not source_archive.is_file():
        raise VisibilityLabError(f"source archive not found: {source_archive}")
    source = spec["source"]
    if source_archive.stat().st_size != source["archive_bytes"]:
        raise VisibilityLabError("libRadtran source archive byte count does not match")
    if sha256_file(source_archive) != source["archive_sha256"]:
        raise VisibilityLabError("libRadtran source archive SHA-256 does not match")

    uvspec = libradtran_root / "bin" / "uvspec"
    data_root = libradtran_root / "data"
    if not uvspec.is_file():
        raise VisibilityLabError(f"uvspec executable not found: {uvspec}")
    if not data_root.is_dir():
        raise VisibilityLabError(f"libRadtran data directory not found: {data_root}")
    version_output = _run_text([str(uvspec), "-v"])
    expected_version = f"{source['version']}-MYSTIC"
    if expected_version not in version_output:
        raise VisibilityLabError(
            f"uvspec version does not identify {expected_version!r}: {version_output!r}"
        )

    source_files: list[dict[str, Any]] = []
    relative_paths = [spec["source_datasets"]["solar_spectrum"]]
    relative_paths.extend(spec["source_datasets"]["atmosphere_files"].values())
    for relative_path in sorted(set(relative_paths)):
        path = libradtran_root / relative_path
        if not path.is_file():
            raise VisibilityLabError(f"required source dataset not found: {path}")
        source_files.append(file_receipt(path, relative_to=libradtran_root))
    source_trees = [
        tree_receipt(
            libradtran_root / relative_path,
            relative_to=libradtran_root,
        )
        for relative_path in sorted(spec["source_datasets"]["data_trees"].values())
    ]

    build_receipts = []
    for name in ("Makeconf", "config.log", "config.status"):
        path = libradtran_root / name
        if not path.is_file():
            raise VisibilityLabError(f"required build receipt not found: {path}")
        build_receipts.append(file_receipt(path, relative_to=libradtran_root))

    config_status = libradtran_root / "config.status"
    if not os.access(config_status, os.X_OK):
        raise VisibilityLabError(f"config.status is not executable: {config_status}")
    configure_options = _run_text(
        [str(config_status), "--config"],
        cwd=libradtran_root,
    )
    required_configure_tokens = (
        "CC=gcc",
        "CFLAGS=-O2",
        "CXX=g++",
        "CXXFLAGS=-O2",
        "F77=gfortran",
        "FFLAGS=-O2",
    )
    missing_tokens = [
        token for token in required_configure_tokens if token not in configure_options
    ]
    if missing_tokens:
        raise VisibilityLabError(
            "libRadtran configure receipt omits required build settings: "
            + ", ".join(missing_tokens)
        )

    makeconf_text = (libradtran_root / "Makeconf").read_text(
        encoding="utf-8",
        errors="replace",
    )
    required_makeconf_markers = (
        "mystic-version = 2.0.6-MYSTIC",
        "HAVE_MYSTIC=-DHAVE_MYSTIC=1",
        "HAVE_MYSTIC3D=-DHAVE_MYSTIC3D=0",
        "HAVE_LIBGSL =-DHAVE_LIBGSL=1",
        "-DHAVE_NETCDF4=1",
    )
    missing_markers = [
        marker for marker in required_makeconf_markers if marker not in makeconf_text
    ]
    if missing_markers:
        raise VisibilityLabError(
            "libRadtran Makeconf omits required build capabilities: "
            + ", ".join(missing_markers)
        )

    return {
        "source_archive": file_receipt(source_archive),
        "source_archive_expected_url": source["archive_url"],
        "uvspec_version": version_output,
        "uvspec_sha256": sha256_file(uvspec),
        "configure_options": configure_options,
        "build_capabilities": {
            "mystic": True,
            "mystic_3d": False,
            "gsl": True,
            "netcdf4": True,
            "vroom_exercised_by_cases": True,
        },
        "build_files": build_receipts,
        "source_datasets": source_files,
        "source_data_trees": source_trees,
    }


def _tool_version(command: str, *args: str) -> str | None:
    executable = shutil.which(command)
    if executable is None:
        return None
    try:
        output = _run_text([executable, *args])
    except VisibilityLabError:
        return None
    return output.splitlines()[0] if output else ""


def environment_receipt() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": sys.version.splitlines()[0],
        "tools": {
            "gcc": _tool_version("gcc", "--version"),
            "g++": _tool_version("g++", "--version"),
            "gfortran": _tool_version("gfortran", "--version"),
            "make": _tool_version("make", "--version"),
            "flex": _tool_version("flex", "--version"),
            "netcdf": _tool_version("nc-config", "--version"),
            "gsl": _tool_version("gsl-config", "--version"),
        },
    }


def _parse_scalar_output(path: Path, label: str) -> tuple[float, float]:
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 1 or len(rows[0]) < 5:
        raise VisibilityLabError(f"{label} must contain exactly one scalar spectral row")
    wavelength = float(rows[0][0])
    value = float(rows[0][-1])
    if not math.isfinite(wavelength) or not math.isfinite(value) or value < 0.0:
        raise VisibilityLabError(f"{label} contains an invalid value")
    return wavelength, value


def _parse_monochromatic_geometry(path: Path) -> tuple[float, float]:
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 1 or len(rows[0]) < 8:
        raise VisibilityLabError("mc0.rad must contain exactly one radiance row")
    viewing_zenith = float(rows[0][2])
    viewing_azimuth = float(rows[0][3]) % 360.0
    if not math.isfinite(viewing_zenith) or not math.isfinite(viewing_azimuth):
        raise VisibilityLabError("mc0.rad contains non-finite viewing geometry")
    return viewing_zenith, viewing_azimuth


def _parse_direct_transmission_output(
    path: Path,
    case: dict[str, Any],
) -> dict[str, float]:
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 1 or len(rows[0]) != 2:
        raise VisibilityLabError(
            "direct-transmission output must contain one lambda/edir row"
        )
    wavelength = float(rows[0][0])
    normalized_direct_irradiance = float(rows[0][1])
    if (
        not math.isfinite(wavelength)
        or wavelength != float(case["wavelength_nm"])
        or not math.isfinite(normalized_direct_irradiance)
        or normalized_direct_irradiance <= 0.0
    ):
        raise VisibilityLabError("direct-transmission output contains invalid values")

    altitude_radians = math.radians(float(case["target_true_altitude_deg"]))
    geometric_projection = math.sin(altitude_radians)
    direct_transmission = normalized_direct_irradiance / geometric_projection
    if not 0.0 < direct_transmission <= 1.0:
        raise VisibilityLabError("normalized direct transmission is outside (0, 1]")
    extinction_magnitude = -2.5 * math.log10(direct_transmission)
    return {
        "wavelength_nm": wavelength,
        "target_true_altitude_deg": float(case["target_true_altitude_deg"]),
        "normalized_direct_irradiance_edir_over_e0": normalized_direct_irradiance,
        "geometric_projection_sin_altitude": geometric_projection,
        "direct_spectral_transmission": direct_transmission,
        "extinction_magnitude": extinction_magnitude,
    }


def _completed_case(path: Path, expected_case: dict[str, Any]) -> dict[str, Any] | None:
    result_path = path / "case-result.json"
    if not result_path.is_file():
        return None
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("schema") != CASE_SCHEMA or result.get("case") != expected_case:
        raise VisibilityLabError(f"completed case does not match requested inputs: {path}")
    receipts = result.get("files")
    if not isinstance(receipts, list):
        raise VisibilityLabError(f"completed case has no file inventory: {path}")
    expected_files = expected_case_files(expected_case)
    received_names: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise VisibilityLabError(f"completed case has an invalid receipt: {path}")
        name = receipt.get("path")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name not in expected_files
            or name in received_names
        ):
            raise VisibilityLabError(
                f"completed case has an invalid file inventory: {path}"
            )
        received_names.add(name)
        artifact = path / name
        if (
            not artifact.is_file()
            or artifact.is_symlink()
            or not isinstance(receipt.get("bytes"), int)
            or artifact.stat().st_size != receipt["bytes"]
            or not isinstance(receipt.get("sha256"), str)
            or sha256_file(artifact) != receipt["sha256"]
        ):
            raise VisibilityLabError(f"completed case artifact failed checksum: {artifact}")
    if received_names != expected_files:
        raise VisibilityLabError(f"completed case file inventory is incomplete: {path}")
    actual_names = {artifact.name for artifact in path.iterdir() if artifact.is_file()}
    if actual_names != expected_files | {"case-result.json"}:
        raise VisibilityLabError(f"completed case contains an unbound file: {path}")
    if any(artifact.is_symlink() for artifact in path.iterdir()):
        raise VisibilityLabError(f"completed case contains a symlink: {path}")
    return result


def run_case(
    case: dict[str, Any],
    spec: dict[str, Any],
    *,
    uvspec: Path,
    data_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    case_id = case["case_id"]
    final_dir = output_root / case_id
    if final_dir.exists():
        completed = _completed_case(final_dir, case)
        if completed is not None:
            return completed
        raise VisibilityLabError(
            f"partial case directory exists; inspect it before retrying: {final_dir}"
        )

    temp_dir = Path(tempfile.mkdtemp(prefix=f".{case_id}.", dir=output_root))
    data_link = temp_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    calculation_kind = case.get("calculation_kind")
    if calculation_kind == CALCULATION_DIRECTIONAL_RADIANCE:
        input_text = render_mystic_input(case, spec)
    elif calculation_kind == CALCULATION_DIRECT_TRANSMISSION:
        input_text = render_direct_transmission_input(case, spec)
    else:
        raise VisibilityLabError(
            f"unsupported calculation kind for {case_id}: {calculation_kind!r}"
        )
    (temp_dir / "input.inp").write_text(input_text, encoding="utf-8", newline="\n")

    syntax = subprocess.run(
        [str(uvspec), "-c"],
        cwd=temp_dir,
        input=input_text,
        check=False,
        capture_output=True,
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
    if syntax.returncode != 0 or "Error" in syntax.stderr or "Exiting" in syntax.stderr:
        raise VisibilityLabError(
            f"uvspec syntax check failed for {case_id}; preserved at {temp_dir}"
        )

    completed = subprocess.run(
        [str(uvspec)],
        cwd=temp_dir,
        input=input_text,
        check=False,
        capture_output=True,
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
    if completed.returncode != 0:
        raise VisibilityLabError(
            f"uvspec failed for {case_id}; preserved at {temp_dir}"
        )
    if "Error" in completed.stderr or "Exiting" in completed.stderr:
        raise VisibilityLabError(
            f"uvspec reported a semantic error for {case_id}; preserved at {temp_dir}"
        )
    if calculation_kind == CALCULATION_DIRECTIONAL_RADIANCE:
        for filename in EXPECTED_OUTPUTS:
            path = temp_dir / filename
            if not path.is_file() or path.stat().st_size == 0:
                raise VisibilityLabError(
                    f"uvspec omitted {filename} for {case_id}; preserved at {temp_dir}"
                )
    expected_files = expected_case_files(case)
    actual_names = {path.name for path in temp_dir.iterdir() if path.is_file()}
    if actual_names != expected_files:
        missing = sorted(expected_files - actual_names)
        unexpected = sorted(actual_names - expected_files)
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if unexpected:
            detail.append("unexpected=" + ",".join(unexpected))
        raise VisibilityLabError(
            f"uvspec file inventory mismatch for {case_id}: {' '.join(detail)}; "
            f"preserved at {temp_dir}"
        )

    random_seed_path = temp_dir / "randomseed"
    if (
        not random_seed_path.is_file()
        or random_seed_path.read_text(encoding="utf-8").strip()
        != str(case["random_seed"])
    ):
        raise VisibilityLabError(
            f"uvspec random-seed receipt mismatch for {case_id}; preserved at {temp_dir}"
        )

    if calculation_kind == CALCULATION_DIRECTIONAL_RADIANCE:
        wavelength, radiance = _parse_scalar_output(
            temp_dir / "mc.rad.spc",
            "mc.rad.spc",
        )
        std_wavelength, reported_std = _parse_scalar_output(
            temp_dir / "mc.rad.std.spc",
            "mc.rad.std.spc",
        )
        if wavelength != std_wavelength or wavelength != float(case["wavelength_nm"]):
            raise VisibilityLabError(
                f"uvspec wavelength mismatch for {case_id}; preserved at {temp_dir}"
            )
        viewing_zenith, viewing_azimuth = _parse_monochromatic_geometry(
            temp_dir / "mc0.rad"
        )
        expected_zenith = 90.0 + float(case["target_true_altitude_deg"])
        expected_azimuth = float(case["relative_solar_azimuth_deg"]) % 360.0
        if not math.isclose(viewing_zenith, expected_zenith, abs_tol=1e-6):
            raise VisibilityLabError(
                f"uvspec viewing-zenith mismatch for {case_id}; preserved at {temp_dir}"
            )
        if not math.isclose(viewing_azimuth, expected_azimuth, abs_tol=1e-6):
            raise VisibilityLabError(
                f"uvspec viewing-azimuth mismatch for {case_id}; preserved at {temp_dir}"
            )
        result_summary: dict[str, float | None] = {
            "wavelength_nm": wavelength,
            "viewing_zenith_deg": viewing_zenith,
            "viewing_azimuth_deg": viewing_azimuth,
            "escape_spectral_radiance_mw_m2_nm_sr": radiance,
            "reported_standard_deviation_mw_m2_nm_sr": reported_std,
            "reported_relative_standard_deviation": (
                reported_std / radiance if radiance > 0.0 else None
            ),
        }
    else:
        result_summary = _parse_direct_transmission_output(
            temp_dir / "stdout.txt",
            case,
        )

    files = [
        file_receipt(path, relative_to=temp_dir)
        for path in sorted(temp_dir.iterdir())
        if path.is_file() and path.name != "case-result.json"
    ]
    result: dict[str, Any] = {
        "schema": CASE_SCHEMA,
        "case": case,
        "result": result_summary,
        "files": files,
    }
    (temp_dir / "case-result.json").write_bytes(canonical_json_bytes(result))
    data_link.unlink()
    os.replace(temp_dir, final_dir)
    return result


def _verify_repeat(
    output_root: Path,
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    repeats = [result for result in results if "repeat_of" in result["case"]]
    if not repeats:
        return None
    if len(repeats) != 1:
        raise VisibilityLabError("exactly one convergence repeat is expected")
    repeat = repeats[0]
    original_id = repeat["case"]["repeat_of"]
    original = next(
        (result for result in results if result["case"]["case_id"] == original_id),
        None,
    )
    if original is None:
        raise VisibilityLabError("repeat names a missing original case")
    if (
        original["case"].get("calculation_kind")
        != repeat["case"].get("calculation_kind")
    ):
        raise VisibilityLabError("repeat calculation kind differs from its original")
    filenames = tuple(sorted(expected_case_files(repeat["case"])))
    mismatches = [
        filename
        for filename in filenames
        if (output_root / repeat["case"]["case_id"] / filename).read_bytes()
        != (output_root / original_id / filename).read_bytes()
    ]
    if mismatches:
        raise VisibilityLabError(
            "fixed-seed repeat was not byte-identical: " + ", ".join(mismatches)
        )
    return {
        "original_case_id": original_id,
        "repeat_case_id": repeat["case"]["case_id"],
        "byte_identical_files": list(filenames),
    }


def build_profile(
    spec_path: Path,
    *,
    source_archive: Path,
    libradtran_root: Path,
    output_root: Path,
    profile: str,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    if not isinstance(spec, dict):
        raise VisibilityLabError("lab specification must be a JSON object")
    validate_spec(spec)
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "artifact-manifest.json"
    if manifest_path.exists():
        raise VisibilityLabError(
            f"artifact manifest already exists; choose a new output root: {manifest_path}"
        )

    cases = expand_profile(spec, profile)
    allowed_case_ids = {case["case_id"] for case in cases}
    unexpected_entries = sorted(
        entry.name for entry in output_root.iterdir() if entry.name not in allowed_case_ids
    )
    if unexpected_entries:
        raise VisibilityLabError(
            "output root contains unowned or partial entries: "
            + ", ".join(unexpected_entries)
        )

    tooling_paths = {
        "builder": Path(__file__).resolve(),
        "validator": REPO_ROOT / "scripts" / "validate_visibility_radiance_lut.py",
    }
    tooling = {
        role: file_receipt(path, relative_to=REPO_ROOT)
        for role, path in tooling_paths.items()
    }
    generator = verify_generator(
        spec,
        source_archive=source_archive,
        libradtran_root=libradtran_root,
    )
    libradtran_root = libradtran_root.resolve()
    results = [
        run_case(
            case,
            spec,
            uvspec=libradtran_root / "bin" / "uvspec",
            data_root=libradtran_root / "data",
            output_root=output_root,
        )
        for case in cases
    ]
    repeat_check = _verify_repeat(output_root, results)

    if spec_path.read_bytes() != spec_bytes:
        raise VisibilityLabError(
            "lab specification changed during generation; no manifest was emitted"
        )
    for role, path in tooling_paths.items():
        if (
            path.stat().st_size != tooling[role]["bytes"]
            or sha256_file(path) != tooling[role]["sha256"]
        ):
            raise VisibilityLabError(
                f"{role} changed during generation; no manifest was emitted"
            )
    source_archive = source_archive.resolve()
    if (
        source_archive.stat().st_size != generator["source_archive"]["bytes"]
        or sha256_file(source_archive) != generator["source_archive"]["sha256"]
    ):
        raise VisibilityLabError(
            "libRadtran source archive changed during generation; no manifest was emitted"
        )
    uvspec = libradtran_root / "bin" / "uvspec"
    if sha256_file(uvspec) != generator["uvspec_sha256"]:
        raise VisibilityLabError(
            "uvspec binary changed during generation; no manifest was emitted"
        )
    for receipt in generator["source_datasets"]:
        path = libradtran_root / receipt["path"]
        if (
            path.stat().st_size != receipt["bytes"]
            or sha256_file(path) != receipt["sha256"]
        ):
            raise VisibilityLabError(
                f"source dataset changed during generation: {receipt['path']}"
            )
    for receipt in generator["source_data_trees"]:
        current = tree_receipt(
            libradtran_root / receipt["path"],
            relative_to=libradtran_root,
        )
        if current != receipt:
            raise VisibilityLabError(
                f"source data tree changed during generation: {receipt['path']}"
            )

    case_receipts = []
    for result in results:
        case_dir = output_root / result["case"]["case_id"]
        case_receipts.append(
            {
                "case_id": result["case"]["case_id"],
                "case_result": file_receipt(
                    case_dir / "case-result.json",
                    relative_to=output_root,
                ),
                "result": result["result"],
            }
        )

    manifest: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_status": "phase1_reference_lab_evidence_not_runtime_data_pack",
        "tooling": tooling,
        "spec": {
            "path": spec_path.name,
            "sha256": sha256_bytes(spec_bytes),
            "spec_id": spec["spec_id"],
        },
        "model_id": profile_model_id(spec, profile),
        "composite_model_id": spec["composite_model_id"],
        "profile": profile,
        "generator": generator,
        "environment": environment_receipt(),
        "runtime_boundary": spec["runtime_boundary"],
        "case_count": len(case_receipts),
        "cases": case_receipts,
        "fixed_seed_repeat_check": repeat_check,
    }
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return manifest


def inspect_spec(spec_path: Path) -> dict[str, Any]:
    spec = load_spec(spec_path)
    convergence_cases = expand_profile(spec, "convergence")
    geometry_cases = expand_profile(spec, "geometry_smoke")
    direct_transmission_cases = expand_profile(spec, "direct_transmission_smoke")
    domain = spec["candidate_domain"]
    candidate_axis_product = math.prod(
        len(domain[field])
        for field in (
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
            "observer_altitude_m",
            "surface_pressure_hpa",
            "aod550",
            "angstrom_exponent",
            "ozone_du",
            "ground_albedo",
            "atmosphere_profiles",
            "aerosol_profiles",
        )
    )
    spectral = domain["build_spectral_grid_nm"]
    spectral_count = round(
        (float(spectral["stop"]) - float(spectral["start"]))
        / float(spectral["step"])
    ) + 1
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "convergence_case_count": len(convergence_cases),
        "geometry_smoke_case_count": len(geometry_cases),
        "direct_transmission_smoke_case_count": len(direct_transmission_cases),
        "reserved_holdout_case_count": len(spec["reserved_holdout_cases"]),
        "candidate_axis_product_before_spectral_grid": candidate_axis_product,
        "build_spectral_sample_count": spectral_count,
        "prohibited_full_cartesian_case_count": (
            candidate_axis_product * spectral_count
        ),
        "sampling_law": domain["sampling_law"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inspect", help="validate and summarize the lab specification")
    build_parser = subparsers.add_parser(
        "build",
        help="run one authorized offline MYSTIC evidence profile",
    )
    build_parser.add_argument("--source-archive", type=Path, required=True)
    build_parser.add_argument("--libradtran-root", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument(
        "--profile",
        choices=(
            "convergence",
            "geometry_smoke",
            "direct_transmission_smoke",
        ),
        required=True,
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            print(canonical_json_bytes(inspect_spec(args.spec)).decode("utf-8"), end="")
        else:
            manifest = build_profile(
                args.spec,
                source_archive=args.source_archive,
                libradtran_root=args.libradtran_root,
                output_root=args.output,
                profile=args.profile,
            )
            print(
                json.dumps(
                    {
                        "artifact_manifest": str(
                            args.output.resolve() / "artifact-manifest.json"
                        ),
                        "case_count": manifest["case_count"],
                        "profile": manifest["profile"],
                    },
                    sort_keys=True,
                )
            )
    except (OSError, json.JSONDecodeError, VisibilityLabError) as exc:
        parser.exit(2, f"visibility reference lab: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
