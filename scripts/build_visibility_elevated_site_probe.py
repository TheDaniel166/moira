#!/usr/bin/env python3
"""Build the Phase 1 elevated-site visibility reference-lab probe.

This tool is intentionally external to the Moira runtime.  It proves a
libRadtran construction for spherical MYSTIC at nonzero observer altitude
without changing the immutable checkpoint-one builder, validator, or spec.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SPEC_PATH = (
    SCRIPT_ROOT
    / "visibility_reference_lab"
    / "phase1_elevated_site_probe_spec.json"
)
BASE_BUILDER_PATH = SCRIPT_ROOT / "build_visibility_radiance_lut.py"
VALIDATOR_PATH = SCRIPT_ROOT / "validate_visibility_elevated_site_probe.py"

SPEC_SCHEMA = "moira.visibility-elevated-site-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-elevated-site-probe-artifact/v1"
CASE_SCHEMA = "moira.visibility-elevated-site-probe-case/v1"
PROFILE_SCHEMA = "moira.visibility-elevated-site-profile-set/v1"
ARTIFACT_STATUS = "phase1_elevated_site_evidence_not_runtime_data_pack"
DATA_LINK_NAME = "libradtran_data"

DIRECT_FILES = frozenset(
    {
        "input.inp",
        "randomseed",
        "stderr.txt",
        "stdout.txt",
        "syntax.stderr.txt",
        "syntax.stdout.txt",
    }
)
MYSTIC_FILES = frozenset(
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
MYSTIC_SCIENTIFIC_FILES = (
    "mc.flx.spc",
    "mc.flx.std.spc",
    "mc.rad.spc",
    "mc.rad.std.spc",
    "mc0.rad",
    "mc0.rad.std",
    "randomseed",
)


def _load_base_lab() -> Any:
    module_spec = importlib.util.spec_from_file_location(
        "_moira_visibility_reference_lab_checkpoint1",
        BASE_BUILDER_PATH,
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load checkpoint-one builder: {BASE_BUILDER_PATH}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


base_lab = _load_base_lab()
VisibilityLabError = base_lab.VisibilityLabError


def _float32(value: float) -> float:
    """Round one number at the same binary32 boundary used by libRadtran."""
    return struct.unpack("!f", struct.pack("!f", float(value)))[0]


def _format_float32(value: float) -> str:
    """Serialize enough significant digits to recover the same binary32 value."""
    return format(_float32(value), ".9g")


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
        raise VisibilityLabError(f"{label} must be finite and within [{low}, {high}]")
    return result


def _verify_declared_repo_file(
    declaration: dict[str, Any],
    *,
    label: str,
) -> Path:
    path_text = declaration.get(f"{label}_path")
    expected_bytes = declaration.get(f"{label}_bytes")
    expected_sha256 = declaration.get(f"{label}_sha256")
    if (
        not isinstance(path_text, str)
        or Path(path_text).is_absolute()
        or ".." in Path(path_text).parts
        or not isinstance(expected_bytes, int)
        or expected_bytes <= 0
        or not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
    ):
        raise VisibilityLabError(f"invalid checkpoint-one {label} declaration")
    path = REPO_ROOT / path_text
    if (
        not path.is_file()
        or path.stat().st_size != expected_bytes
        or base_lab.sha256_file(path) != expected_sha256
    ):
        raise VisibilityLabError(
            f"checkpoint-one {label} identity does not match: {path}"
        )
    return path


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VisibilityLabError("elevated-site probe specification must be an object")
    validate_spec(payload)
    return payload


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema") != SPEC_SCHEMA:
        raise VisibilityLabError("unsupported elevated-site probe spec schema")
    if spec.get("status") != "research_probe_not_runtime_data_pack":
        raise VisibilityLabError("elevated-site probe must remain research-only")
    if not isinstance(spec.get("spec_id"), str) or not spec["spec_id"]:
        raise VisibilityLabError("elevated-site probe requires a spec_id")

    boundary = spec.get("runtime_boundary")
    if boundary != {
        "network_allowed": False,
        "automatic_download_allowed": False,
        "engine_dependency_allowed": False,
        "engine_runtime_invocation_allowed": False,
        "generated_numerical_products_only": True,
    }:
        raise VisibilityLabError("elevated-site runtime boundary was weakened")

    base_declaration = spec.get("base_lab")
    if not isinstance(base_declaration, dict):
        raise VisibilityLabError("base_lab declaration is required")
    _verify_declared_repo_file(base_declaration, label="spec")
    _verify_declared_repo_file(base_declaration, label="builder")
    _verify_declared_repo_file(base_declaration, label="validator")

    source_semantics = spec.get("libradtran_source_semantics")
    if not isinstance(source_semantics, dict):
        raise VisibilityLabError("libRadtran source semantics are required")
    if (
        source_semantics.get("altitude_option")
        != "supported_for_1D_deterministic_solvers_and_rejected_for_montecarlo"
        or source_semantics.get("mc_elevation_file")
        != "rejected_with_mystic_spherical_geometry"
        or source_semantics.get("surface_without_altitude_option")
        != "bottom_level_of_atmosphere_file"
    ):
        raise VisibilityLabError("libRadtran elevated-site semantics changed")
    source_files = source_semantics.get("source_files")
    if not isinstance(source_files, list) or len(source_files) != 4:
        raise VisibilityLabError("four governing libRadtran source files are required")
    seen_source_paths: set[str] = set()
    for receipt in source_files:
        if not isinstance(receipt, dict):
            raise VisibilityLabError("invalid libRadtran source-file receipt")
        path_text = receipt.get("path")
        if (
            not isinstance(path_text, str)
            or Path(path_text).is_absolute()
            or ".." in Path(path_text).parts
            or path_text in seen_source_paths
            or not isinstance(receipt.get("bytes"), int)
            or receipt["bytes"] <= 0
            or not isinstance(receipt.get("sha256"), str)
            or len(receipt["sha256"]) != 64
        ):
            raise VisibilityLabError("invalid libRadtran source-file identity")
        seen_source_paths.add(path_text)

    construction = spec.get("atmosphere_construction")
    if not isinstance(construction, dict):
        raise VisibilityLabError("atmosphere construction is required")
    if (
        construction.get("source_profile") != "us_standard"
        or construction.get("source_path") != "data/atmmod/afglus.dat"
        or construction.get("level_order")
        != "strictly_descending_top_to_surface"
        or construction.get("pressure_policy")
        != "named_profile_derived_no_explicit_override_in_probe"
    ):
        raise VisibilityLabError("elevated-site atmosphere construction changed")
    interpolation = construction.get("interpolation_policy")
    if interpolation != {
        "name": "libradtran_2_0_6_default_z_interpolate_linmix",
        "pressure_hpa": "logarithmic",
        "temperature_k": "linear",
        "air_number_density_cm-3": "logarithmic",
        "trace_gas_number_density_cm-3": (
            "linear_mixing_ratio_against_interpolated_air"
        ),
        "numeric_staging": "binary32_at_libradtran_assignment_boundaries",
        "decimal_serialization": (
            "nine_significant_digits_binary32_round_trip"
        ),
    }:
        raise VisibilityLabError("unsupported atmosphere interpolation policy")
    if construction.get("derived_o4_closure") != {
        "source_level_formula": (
            "binary32((binary32(o2_number_density_cm-3) * 1e-23)^2)"
        ),
        "inserted_level_interpolation": (
            "linear_mixing_ratio_against_interpolated_air"
        ),
        "transport": (
            "mol_file_O4_cm_3_companion_to_truncated_atmosphere"
        ),
        "reason": (
            "preserve_libradtran_preinterpolation_o4_semantics_not_square_of_"
            "interpolated_o2"
        ),
    }:
        raise VisibilityLabError("unsupported derived O4 closure policy")
    altitudes = construction.get("site_altitudes_m")
    if (
        not isinstance(altitudes, list)
        or len(altitudes) < 2
        or any(
            _require_number(value, "site_altitudes_m", 0.0, 5000.0) != float(value)
            for value in altitudes
        )
        or any(float(a) >= float(b) for a, b in zip(altitudes, altitudes[1:]))
    ):
        raise VisibilityLabError("site altitudes must be strictly increasing")

    shared = spec.get("shared_atmosphere")
    if not isinstance(shared, dict):
        raise VisibilityLabError("shared atmosphere controls are required")
    _require_number(shared.get("ozone_du"), "ozone_du", 200.0, 500.0)
    _require_number(shared.get("aod550"), "aod550", 0.0, 1.0)
    _require_number(
        shared.get("angstrom_exponent"),
        "angstrom_exponent",
        0.0,
        2.5,
    )
    _require_number(shared.get("ground_albedo"), "ground_albedo", 0.0, 1.0)
    if shared.get("aerosol_profile") != "rural_summer":
        raise VisibilityLabError("probe aerosol profile must remain rural_summer")

    direct = spec.get("direct_oracle_profile")
    if not isinstance(direct, dict):
        raise VisibilityLabError("direct-oracle profile is required")
    if (
        direct.get("rte_solver") != "disort"
        or direct.get("geometry") != "pseudospherical"
        or direct.get("number_of_streams") != 16
    ):
        raise VisibilityLabError("direct-oracle solver identity changed")
    for value in direct.get("target_true_altitude_deg", []):
        _require_number(value, "direct target altitude", 0.25, 45.0)
    for value in direct.get("wavelength_nm", []):
        _require_number(value, "direct wavelength", 380.0, 780.0)
    if (
        not direct.get("target_true_altitude_deg")
        or not direct.get("wavelength_nm")
        or not isinstance(direct.get("random_seed"), int)
        or direct["random_seed"] <= 0
    ):
        raise VisibilityLabError("direct-oracle axes or seed are invalid")
    comparison = direct.get("comparison")
    if not isinstance(comparison, dict):
        raise VisibilityLabError("direct-oracle comparison policy is required")
    for label, value in comparison.items():
        if not label.endswith("_tolerance"):
            raise VisibilityLabError("unknown direct-oracle comparison field")
        _require_number(value, label, 0.0, 1.0)

    mystic = spec.get("mystic_elevated_smoke_profile")
    if not isinstance(mystic, dict):
        raise VisibilityLabError("MYSTIC elevated-site smoke profile is required")
    _require_number(
        mystic.get("solar_center_altitude_deg"),
        "solar_center_altitude_deg",
        -18.0,
        0.0,
    )
    _require_number(
        mystic.get("target_true_altitude_deg"),
        "target_true_altitude_deg",
        0.25,
        45.0,
    )
    _require_number(
        mystic.get("relative_solar_azimuth_deg"),
        "relative_solar_azimuth_deg",
        0.0,
        180.0,
    )
    _require_number(mystic.get("wavelength_nm"), "wavelength_nm", 380.0, 780.0)
    if (
        not isinstance(mystic.get("photon_count"), int)
        or mystic["photon_count"] <= 0
        or not isinstance(mystic.get("random_seed"), int)
        or mystic["random_seed"] <= 0
        or float(mystic.get("exact_repeat_site_altitude_m", -1.0))
        not in [float(value) for value in altitudes]
        or mystic.get("sea_level_source_profile_control") is not True
    ):
        raise VisibilityLabError("MYSTIC smoke controls are invalid")


def _parse_atmosphere_profile(text: str) -> list[list[float]]:
    rows: list[list[float]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 9:
            raise VisibilityLabError(
                f"atmosphere row {line_number} must contain exactly nine columns"
            )
        try:
            row = [_float32(float(field)) for field in fields]
        except ValueError as exc:
            raise VisibilityLabError(
                f"atmosphere row {line_number} contains a non-number"
            ) from exc
        if any(not math.isfinite(value) or value < 0.0 for value in row):
            raise VisibilityLabError(
                f"atmosphere row {line_number} contains an invalid value"
            )
        rows.append(row)
    if len(rows) < 2:
        raise VisibilityLabError("atmosphere profile must contain at least two levels")
    if any(rows[index][0] <= rows[index + 1][0] for index in range(len(rows) - 1)):
        raise VisibilityLabError("atmosphere levels must be strictly descending")
    if any(row[1] <= 0.0 or row[2] <= 0.0 or row[3] <= 0.0 for row in rows):
        raise VisibilityLabError(
            "pressure, temperature, and air density must remain positive"
        )
    return rows


def _linear_interpolate(
    z_low: float,
    value_low: float,
    z_high: float,
    value_high: float,
    altitude_km: float,
) -> float:
    fraction = (altitude_km - z_low) / (z_high - z_low)
    return _float32(value_low + fraction * (value_high - value_low))


def _log_interpolate(
    z_low: float,
    value_low: float,
    z_high: float,
    value_high: float,
    altitude_km: float,
) -> float:
    difference = abs(value_high - value_low)
    if difference <= 0.001 * value_low or min(value_low, value_high) <= 0.0:
        return _linear_interpolate(
            z_low,
            value_low,
            z_high,
            value_high,
            altitude_km,
        )
    fraction = (altitude_km - z_low) / (z_high - z_low)
    return _float32(
        math.exp(
            math.log(value_low)
            + fraction * (math.log(value_high) - math.log(value_low))
        )
    )


def _linmix_interpolate(
    z_low: float,
    gas_low: float,
    air_low: float,
    z_high: float,
    gas_high: float,
    air_high: float,
    altitude_km: float,
    interpolated_air: float,
) -> float:
    mixing_low = _float32(gas_low / air_low)
    mixing_high = _float32(gas_high / air_high)
    mixing = _linear_interpolate(
        z_low,
        mixing_low,
        z_high,
        mixing_high,
        altitude_km,
    )
    return _float32(mixing * interpolated_air)


def construct_truncated_atmosphere(
    source_text: str,
    site_altitude_m: float,
) -> tuple[bytes, dict[str, Any]]:
    """Cut a standard atmosphere at one site using libRadtran's default law."""
    altitude_m = _require_number(
        site_altitude_m,
        "site_altitude_m",
        0.0,
        5000.0,
    )
    altitude_km = _float32(altitude_m / 1000.0)
    rows = _parse_atmosphere_profile(source_text)
    if not rows[-1][0] <= altitude_km < rows[0][0]:
        raise VisibilityLabError("site altitude lies outside the atmosphere profile")

    exact_index = next(
        (
            index
            for index, row in enumerate(rows)
            if math.isclose(row[0], altitude_km, rel_tol=0.0, abs_tol=1e-7)
        ),
        None,
    )
    if exact_index is not None:
        selected = [list(row) for row in rows[: exact_index + 1]]
        bracket = [rows[exact_index][0], rows[exact_index][0]]
        interpolated = False
    else:
        upper_index = next(
            index
            for index in range(len(rows) - 1)
            if rows[index][0] > altitude_km > rows[index + 1][0]
        )
        high = rows[upper_index]
        low = rows[upper_index + 1]
        pressure = _log_interpolate(
            low[0],
            low[1],
            high[0],
            high[1],
            altitude_km,
        )
        temperature = _linear_interpolate(
            low[0],
            low[2],
            high[0],
            high[2],
            altitude_km,
        )
        air = _log_interpolate(
            low[0],
            low[3],
            high[0],
            high[3],
            altitude_km,
        )
        bottom = [altitude_km, pressure, temperature, air]
        for column in range(4, 9):
            bottom.append(
                _linmix_interpolate(
                    low[0],
                    low[column],
                    low[3],
                    high[0],
                    high[column],
                    high[3],
                    altitude_km,
                    air,
                )
            )
        selected = [list(row) for row in rows[: upper_index + 1]]
        selected.append(bottom)
        bracket = [low[0], high[0]]
        interpolated = True

    header = [
        "# Moira Phase 1 elevated-site reference-lab atmosphere.",
        "# Source: libRadtran 2.0.6 data/atmmod/afglus.dat.",
        "# Construction: default z_interpolate LINMIX, binary32 staged.",
        (
            "# z(km) p(hPa) T(K) air(cm-3) O3(cm-3) O2(cm-3) "
            "H2O(cm-3) CO2(cm-3) NO2(cm-3)"
        ),
    ]
    body = [" ".join(_format_float32(value) for value in row) for row in selected]
    payload = ("\n".join(header + body) + "\n").encode("utf-8")
    bottom = selected[-1]
    metadata = {
        "site_altitude_m": altitude_m,
        "site_altitude_km": bottom[0],
        "interpolated_bottom_level": interpolated,
        "bracketing_altitude_km": bracket,
        "level_count": len(selected),
        "bottom_level": {
            "altitude_km": bottom[0],
            "pressure_hpa": bottom[1],
            "temperature_k": bottom[2],
            "air_number_density_cm-3": bottom[3],
            "o3_number_density_cm-3": bottom[4],
            "o2_number_density_cm-3": bottom[5],
            "h2o_number_density_cm-3": bottom[6],
            "co2_number_density_cm-3": bottom[7],
            "no2_number_density_cm-3": bottom[8],
        },
    }
    return payload, metadata


def construct_truncated_o4_profile(
    source_text: str,
    site_altitude_m: float,
) -> tuple[bytes, dict[str, Any]]:
    """Reproduce libRadtran's preinterpolation O4 pseudo-density profile."""
    altitude_m = _require_number(
        site_altitude_m,
        "site_altitude_m",
        0.0,
        5000.0,
    )
    altitude_km = _float32(altitude_m / 1000.0)
    rows = _parse_atmosphere_profile(source_text)
    if not rows[-1][0] <= altitude_km < rows[0][0]:
        raise VisibilityLabError("site altitude lies outside the atmosphere profile")

    o4_rows = [
        [
            row[0],
            _float32((float(row[5]) * 1e-23) ** 2),
            row[3],
        ]
        for row in rows
    ]
    exact_index = next(
        (
            index
            for index, row in enumerate(o4_rows)
            if math.isclose(row[0], altitude_km, rel_tol=0.0, abs_tol=1e-7)
        ),
        None,
    )
    if exact_index is not None:
        selected = [list(row) for row in o4_rows[: exact_index + 1]]
        bracket = [o4_rows[exact_index][0], o4_rows[exact_index][0]]
        interpolated = False
    else:
        upper_index = next(
            index
            for index in range(len(o4_rows) - 1)
            if o4_rows[index][0] > altitude_km > o4_rows[index + 1][0]
        )
        high = o4_rows[upper_index]
        low = o4_rows[upper_index + 1]
        air = _log_interpolate(
            low[0],
            low[2],
            high[0],
            high[2],
            altitude_km,
        )
        o4 = _linmix_interpolate(
            low[0],
            low[1],
            low[2],
            high[0],
            high[1],
            high[2],
            altitude_km,
            air,
        )
        selected = [list(row) for row in o4_rows[: upper_index + 1]]
        selected.append([altitude_km, o4, air])
        bracket = [low[0], high[0]]
        interpolated = True

    header = [
        "# Moira Phase 1 elevated-site reference-lab O4 companion.",
        "# Reproduces libRadtran 2.0.6 preinterpolation O4 pseudo-density.",
        "# z(km) O4_scaled_density(cm-3)",
    ]
    body = [
        f"{_format_float32(row[0])} {_format_float32(row[1])}"
        for row in selected
    ]
    payload = ("\n".join(header + body) + "\n").encode("utf-8")
    bottom = selected[-1]
    metadata = {
        "site_altitude_m": altitude_m,
        "site_altitude_km": bottom[0],
        "interpolated_bottom_level": interpolated,
        "bracketing_altitude_km": bracket,
        "level_count": len(selected),
        "bottom_scaled_o4_density_cm-3": bottom[1],
    }
    return payload, metadata


def _site_token(site_altitude_m: float) -> str:
    return f"{int(round(float(site_altitude_m))):04d}m"


def _angle_token(value: float) -> str:
    return f"{float(value):05.2f}".replace(".", "p")


def _wavelength_token(value: float) -> str:
    return f"{int(round(float(value))):04d}nm"


def expand_direct_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    construction = spec["atmosphere_construction"]
    direct = spec["direct_oracle_profile"]
    cases: list[dict[str, Any]] = []
    for site, target, wavelength in itertools.product(
        construction["site_altitudes_m"],
        direct["target_true_altitude_deg"],
        direct["wavelength_nm"],
    ):
        cases.append(
            {
                "case_id": (
                    f"direct_site_{_site_token(site)}"
                    f"_alt_{_angle_token(target)}"
                    f"_{_wavelength_token(wavelength)}"
                ),
                "kind": "direct_altitude_oracle_comparison",
                "site_altitude_m": float(site),
                "target_true_altitude_deg": float(target),
                "wavelength_nm": float(wavelength),
                "random_seed": direct["random_seed"],
            }
        )
    return cases


def expand_mystic_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    construction = spec["atmosphere_construction"]
    mystic = spec["mystic_elevated_smoke_profile"]
    cases: list[dict[str, Any]] = []
    cases.append(
        {
            "case_id": "mystic_source_site_0000m_control",
            "kind": "mystic_spherical_source_profile_control",
            "profile_method": "source_profile",
            "site_altitude_m": 0.0,
        }
    )
    for site in construction["site_altitudes_m"]:
        cases.append(
            {
                "case_id": f"mystic_truncated_site_{_site_token(site)}",
                "kind": "mystic_spherical_truncated_profile",
                "profile_method": "truncated_profile",
                "site_altitude_m": float(site),
            }
        )
    repeat_site = float(mystic["exact_repeat_site_altitude_m"])
    cases.append(
        {
            "case_id": (
                f"mystic_truncated_site_{_site_token(repeat_site)}_repeat"
            ),
            "kind": "mystic_spherical_truncated_profile",
            "profile_method": "truncated_profile",
            "site_altitude_m": repeat_site,
            "repeat_of": f"mystic_truncated_site_{_site_token(repeat_site)}",
        }
    )
    shared = {
        "solar_center_altitude_deg": float(mystic["solar_center_altitude_deg"]),
        "target_true_altitude_deg": float(mystic["target_true_altitude_deg"]),
        "relative_solar_azimuth_deg": float(
            mystic["relative_solar_azimuth_deg"]
        ),
        "wavelength_nm": float(mystic["wavelength_nm"]),
        "photon_count": mystic["photon_count"],
        "random_seed": mystic["random_seed"],
    }
    for case in cases:
        case.update(shared)
    return cases


def _common_input_lines(
    spec: dict[str, Any],
    base_spec: dict[str, Any],
    atmosphere_file: str,
    *,
    o4_companion_file: str | None,
) -> list[str]:
    source_datasets = base_spec["source_datasets"]
    shared = spec["shared_atmosphere"]
    solver = base_spec["solver"]
    aerosol = source_datasets["aerosol_profiles"][shared["aerosol_profile"]]
    solar_path = source_datasets["solar_spectrum"].removeprefix("data/")
    angstrom_beta = float(shared["aod550"]) * (
        0.55 ** float(shared["angstrom_exponent"])
    )
    cross_sections = solver["cross_sections"]
    lines = [
        f"data_files_path {DATA_LINK_NAME}",
        f"atmosphere_file {atmosphere_file}",
        f"source solar {DATA_LINK_NAME}/{solar_path}",
        "mol_abs_param crs",
        f"crs_model rayleigh {cross_sections['rayleigh']}",
        f"crs_model O3 {cross_sections['O3']}",
        f"crs_model NO2 {cross_sections['NO2']}",
        f"crs_model O4 {cross_sections['O4']}",
        f"earth_radius {base_lab._format_number(solver['earth_radius_km'])}",
        f"mol_modify O3 {base_lab._format_number(shared['ozone_du'])} DU",
        f"albedo {base_lab._format_number(shared['ground_albedo'])}",
        "aerosol_default",
        f"aerosol_haze {aerosol['haze']}",
        f"aerosol_season {aerosol['season']}",
        (
            f"aerosol_angstrom "
            f"{base_lab._format_number(shared['angstrom_exponent'])} "
            f"{base_lab._format_number(angstrom_beta)}"
        ),
    ]
    if o4_companion_file is not None:
        lines.append(f"mol_file O4 {o4_companion_file} cm_3")
    return lines


def render_direct_input(
    case: dict[str, Any],
    spec: dict[str, Any],
    base_spec: dict[str, Any],
    *,
    method: str,
) -> str:
    if method not in {"altitude_option", "truncated_profile"}:
        raise VisibilityLabError(f"unsupported direct comparison method: {method}")
    source_path = spec["atmosphere_construction"]["source_path"].removeprefix(
        "data/"
    )
    atmosphere_file = (
        f"{DATA_LINK_NAME}/{source_path}"
        if method == "altitude_option"
        else "atmosphere.dat"
    )
    lines = _common_input_lines(
        spec,
        base_spec,
        atmosphere_file,
        o4_companion_file=(
            None if method == "altitude_option" else "o4.dat"
        ),
    )
    if method == "altitude_option":
        lines.append(
            f"altitude {base_lab._format_number(case['site_altitude_m'] / 1000.0)}"
        )
    target_zenith = 90.0 - float(case["target_true_altitude_deg"])
    direct = spec["direct_oracle_profile"]
    lines.extend(
        [
            (
                f"wavelength {base_lab._format_number(case['wavelength_nm'])} "
                f"{base_lab._format_number(case['wavelength_nm'])}"
            ),
            f"sza {base_lab._format_number(target_zenith)}",
            "phi0 0",
            f"rte_solver {direct['rte_solver']}",
            direct["geometry"],
            f"number_of_streams {direct['number_of_streams']}",
            "output_quantity transmittance",
            "output_user lambda edir",
            f"mc_randomseed {case['random_seed']}",
            "zout 0",
            "quiet",
        ]
    )
    rendered = "\n".join(lines) + "\n"
    if method == "truncated_profile" and (
        "\naltitude " in rendered or "mc_elevation_file" in rendered
    ):
        raise VisibilityLabError("truncated-profile input contains a forbidden option")
    if method == "truncated_profile" and "mol_file O4 o4.dat cm_3" not in lines:
        raise VisibilityLabError("truncated-profile input lacks O4 closure")
    return rendered


def render_mystic_input(
    case: dict[str, Any],
    spec: dict[str, Any],
    base_spec: dict[str, Any],
) -> str:
    source_path = spec["atmosphere_construction"]["source_path"].removeprefix(
        "data/"
    )
    atmosphere_file = (
        f"{DATA_LINK_NAME}/{source_path}"
        if case["profile_method"] == "source_profile"
        else "atmosphere.dat"
    )
    lines = _common_input_lines(
        spec,
        base_spec,
        atmosphere_file,
        o4_companion_file=(
            None if case["profile_method"] == "source_profile" else "o4.dat"
        ),
    )
    solar_zenith = 90.0 - float(case["solar_center_altitude_deg"])
    viewing_umu = -math.sin(
        math.radians(float(case["target_true_altitude_deg"]))
    )
    lines.extend(
        [
            (
                f"wavelength {base_lab._format_number(case['wavelength_nm'])} "
                f"{base_lab._format_number(case['wavelength_nm'])}"
            ),
            f"sza {base_lab._format_number(solar_zenith)}",
            "phi0 0",
            "rte_solver mystic",
            "mc_spherical 1D",
            f"mc_photons {case['photon_count']}",
            f"mc_randomseed {case['random_seed']}",
            "mc_escape",
            "mc_std",
            "mc_vroom on",
            "zout 0",
            f"umu {base_lab._format_number(viewing_umu)}",
            f"phi {base_lab._format_number(case['relative_solar_azimuth_deg'])}",
            "quiet",
        ]
    )
    rendered = "\n".join(lines) + "\n"
    if "\naltitude " in rendered or "mc_elevation_file" in rendered:
        raise VisibilityLabError("spherical MYSTIC input contains a forbidden option")
    if (
        case["profile_method"] == "truncated_profile"
        and "mol_file O4 o4.dat cm_3" not in lines
    ):
        raise VisibilityLabError("spherical MYSTIC input lacks O4 closure")
    return rendered


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _run_uvspec(
    *,
    uvspec: Path,
    data_root: Path,
    run_dir: Path,
    input_text: str,
    expected_seed: int,
    expected_files: frozenset[str],
    atmosphere_bytes: bytes | None,
    o4_bytes: bytes | None,
) -> None:
    run_dir.mkdir(parents=True)
    if atmosphere_bytes is not None:
        (run_dir / "atmosphere.dat").write_bytes(atmosphere_bytes)
    if o4_bytes is not None:
        (run_dir / "o4.dat").write_bytes(o4_bytes)
    _write_text(run_dir / "input.inp", input_text)
    data_link = run_dir / DATA_LINK_NAME
    data_link.symlink_to(data_root, target_is_directory=True)
    try:
        syntax = subprocess.run(
            [str(uvspec), "-c"],
            cwd=run_dir,
            input=input_text,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _write_text(run_dir / "syntax.stdout.txt", syntax.stdout)
        _write_text(run_dir / "syntax.stderr.txt", syntax.stderr)
        if (
            syntax.returncode != 0
            or "Error" in syntax.stderr
            or "Exiting" in syntax.stderr
        ):
            raise VisibilityLabError(
                f"uvspec syntax check failed; preserved at {run_dir}"
            )

        completed = subprocess.run(
            [str(uvspec)],
            cwd=run_dir,
            input=input_text,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _write_text(run_dir / "stdout.txt", completed.stdout)
        _write_text(run_dir / "stderr.txt", completed.stderr)
        if (
            completed.returncode != 0
            or "Error" in completed.stderr
            or "Exiting" in completed.stderr
        ):
            raise VisibilityLabError(f"uvspec failed; preserved at {run_dir}")
    finally:
        if data_link.is_symlink():
            data_link.unlink()

    expected = set(expected_files)
    if atmosphere_bytes is not None:
        expected.add("atmosphere.dat")
    if o4_bytes is not None:
        expected.add("o4.dat")
    actual = {path.name for path in run_dir.iterdir() if path.is_file()}
    if actual != expected:
        raise VisibilityLabError(
            f"uvspec file inventory mismatch at {run_dir}: "
            f"missing={sorted(expected - actual)} "
            f"unexpected={sorted(actual - expected)}"
        )
    seed_path = run_dir / "randomseed"
    if seed_path.read_text(encoding="utf-8").strip() != str(expected_seed):
        raise VisibilityLabError(f"uvspec random-seed receipt mismatch at {run_dir}")


def _parse_direct_output(
    path: Path,
    case: dict[str, Any],
) -> dict[str, float]:
    rows = [
        line.split()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 1 or len(rows[0]) != 2:
        raise VisibilityLabError("direct output must contain one lambda/edir row")
    wavelength = float(rows[0][0])
    normalized = float(rows[0][1])
    if (
        not math.isfinite(wavelength)
        or wavelength != float(case["wavelength_nm"])
        or not math.isfinite(normalized)
        or normalized <= 0.0
    ):
        raise VisibilityLabError("direct output contains invalid values")
    projection = math.sin(
        math.radians(float(case["target_true_altitude_deg"]))
    )
    transmission = normalized / projection
    if not 0.0 < transmission <= 1.0:
        raise VisibilityLabError("direct spectral transmission is outside (0, 1]")
    return {
        "wavelength_nm": wavelength,
        "normalized_direct_irradiance_edir_over_e0": normalized,
        "geometric_projection_sin_altitude": projection,
        "direct_spectral_transmission": transmission,
        "extinction_magnitude": -2.5 * math.log10(transmission),
    }


def _parse_mystic_output(
    run_dir: Path,
    case: dict[str, Any],
) -> dict[str, float | None]:
    wavelength, radiance = base_lab._parse_scalar_output(
        run_dir / "mc.rad.spc",
        "mc.rad.spc",
    )
    std_wavelength, standard_deviation = base_lab._parse_scalar_output(
        run_dir / "mc.rad.std.spc",
        "mc.rad.std.spc",
    )
    if wavelength != std_wavelength or wavelength != float(case["wavelength_nm"]):
        raise VisibilityLabError("MYSTIC output wavelength does not match the case")
    viewing_zenith, viewing_azimuth = base_lab._parse_monochromatic_geometry(
        run_dir / "mc0.rad"
    )
    expected_zenith = 90.0 + float(case["target_true_altitude_deg"])
    expected_azimuth = float(case["relative_solar_azimuth_deg"]) % 360.0
    if not math.isclose(viewing_zenith, expected_zenith, abs_tol=1e-6):
        raise VisibilityLabError("MYSTIC viewing zenith does not match the case")
    if not math.isclose(viewing_azimuth, expected_azimuth, abs_tol=1e-6):
        raise VisibilityLabError("MYSTIC viewing azimuth does not match the case")
    return {
        "wavelength_nm": wavelength,
        "viewing_zenith_deg": viewing_zenith,
        "viewing_azimuth_deg": viewing_azimuth,
        "escape_spectral_radiance_mw_m2_nm_sr": radiance,
        "reported_standard_deviation_mw_m2_nm_sr": standard_deviation,
        "reported_relative_standard_deviation": (
            standard_deviation / radiance if radiance > 0.0 else None
        ),
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
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in exclude:
            continue
        receipts.append(base_lab.file_receipt(path, relative_to=root))
    return receipts


def _verify_receipts(root: Path, receipts: list[dict[str, Any]]) -> None:
    expected: set[str] = set()
    for receipt in receipts:
        relative = receipt.get("path")
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or relative in expected
        ):
            raise VisibilityLabError(f"invalid file receipt under {root}")
        expected.add(relative)
        path = root / Path(relative)
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != receipt.get("bytes")
            or base_lab.sha256_file(path) != receipt.get("sha256")
        ):
            raise VisibilityLabError(f"file receipt mismatch: {path}")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if actual != expected | {"case-result.json"}:
        raise VisibilityLabError(f"case contains an unbound file: {root}")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise VisibilityLabError(f"case contains a symlink: {root}")


def _resume_case(
    case_dir: Path,
    expected_case: dict[str, Any],
    expected_generation_identity: dict[str, Any],
) -> dict[str, Any] | None:
    result_path = case_dir / "case-result.json"
    if not result_path.is_file():
        return None
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("schema") != CASE_SCHEMA or result.get("case") != expected_case:
        raise VisibilityLabError(f"completed case does not match: {case_dir}")
    if result.get("generation_identity") != expected_generation_identity:
        raise VisibilityLabError(
            f"completed case generation identity does not match: {case_dir}"
        )
    receipts = result.get("files")
    if not isinstance(receipts, list):
        raise VisibilityLabError(f"completed case has no file receipts: {case_dir}")
    _verify_receipts(case_dir, receipts)
    return result


def _comparison_receipt(
    source_result: dict[str, float],
    truncated_result: dict[str, float],
    spec: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "normalized_direct_irradiance_edir_over_e0": (
            "normalized_direct_irradiance_abs_tolerance"
        ),
        "direct_spectral_transmission": (
            "direct_spectral_transmission_abs_tolerance"
        ),
        "extinction_magnitude": "extinction_magnitude_abs_tolerance",
    }
    tolerances = spec["direct_oracle_profile"]["comparison"]
    differences: dict[str, float] = {}
    for field, tolerance_name in fields.items():
        difference = abs(source_result[field] - truncated_result[field])
        if difference > float(tolerances[tolerance_name]):
            raise VisibilityLabError(
                f"truncated atmosphere differs from altitude oracle for {field}: "
                f"{difference} > {tolerances[tolerance_name]}"
            )
        differences[field] = difference
    return {
        "status": "within_declared_absolute_tolerances",
        "absolute_differences": differences,
        "tolerances": dict(tolerances),
    }


def _build_direct_case(
    case: dict[str, Any],
    *,
    spec: dict[str, Any],
    base_spec: dict[str, Any],
    atmosphere_bytes: bytes,
    atmosphere_metadata: dict[str, Any],
    o4_bytes: bytes,
    o4_metadata: dict[str, Any],
    generation_identity: dict[str, Any],
    uvspec: Path,
    data_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    final_dir = output_root / case["case_id"]
    if final_dir.exists():
        resumed = _resume_case(final_dir, case, generation_identity)
        if resumed is not None:
            return resumed
        raise VisibilityLabError(f"partial case directory exists: {final_dir}")
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{case['case_id']}.", dir=output_root)
    )
    try:
        source_dir = temp_dir / "altitude_option"
        truncated_dir = temp_dir / "truncated_profile"
        _run_uvspec(
            uvspec=uvspec,
            data_root=data_root,
            run_dir=source_dir,
            input_text=render_direct_input(
                case,
                spec,
                base_spec,
                method="altitude_option",
            ),
            expected_seed=case["random_seed"],
            expected_files=DIRECT_FILES,
            atmosphere_bytes=None,
            o4_bytes=None,
        )
        _run_uvspec(
            uvspec=uvspec,
            data_root=data_root,
            run_dir=truncated_dir,
            input_text=render_direct_input(
                case,
                spec,
                base_spec,
                method="truncated_profile",
            ),
            expected_seed=case["random_seed"],
            expected_files=DIRECT_FILES,
            atmosphere_bytes=atmosphere_bytes,
            o4_bytes=o4_bytes,
        )
        source_result = _parse_direct_output(source_dir / "stdout.txt", case)
        truncated_result = _parse_direct_output(
            truncated_dir / "stdout.txt",
            case,
        )
        comparison = _comparison_receipt(
            source_result,
            truncated_result,
            spec,
        )
        files = _recursive_file_receipts(temp_dir)
        result = {
            "schema": CASE_SCHEMA,
            "case": case,
            "generation_identity": generation_identity,
            "atmosphere": atmosphere_metadata,
            "o4_companion": o4_metadata,
            "altitude_option_result": source_result,
            "truncated_profile_result": truncated_result,
            "comparison": comparison,
            "files": files,
        }
        (temp_dir / "case-result.json").write_bytes(
            base_lab.canonical_json_bytes(result)
        )
        os.replace(temp_dir, final_dir)
        return result
    except Exception as exc:
        raise VisibilityLabError(
            f"direct comparison failed; preserved at {temp_dir}: {exc}"
        ) from exc


def _build_mystic_case(
    case: dict[str, Any],
    *,
    spec: dict[str, Any],
    base_spec: dict[str, Any],
    atmosphere_bytes: bytes,
    atmosphere_metadata: dict[str, Any],
    o4_bytes: bytes,
    o4_metadata: dict[str, Any],
    generation_identity: dict[str, Any],
    uvspec: Path,
    data_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    final_dir = output_root / case["case_id"]
    if final_dir.exists():
        resumed = _resume_case(final_dir, case, generation_identity)
        if resumed is not None:
            return resumed
        raise VisibilityLabError(f"partial case directory exists: {final_dir}")
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{case['case_id']}.", dir=output_root)
    )
    try:
        run_dir = temp_dir / "mystic"
        profile_bytes = (
            None if case["profile_method"] == "source_profile" else atmosphere_bytes
        )
        profile_o4_bytes = (
            None if case["profile_method"] == "source_profile" else o4_bytes
        )
        _run_uvspec(
            uvspec=uvspec,
            data_root=data_root,
            run_dir=run_dir,
            input_text=render_mystic_input(case, spec, base_spec),
            expected_seed=case["random_seed"],
            expected_files=MYSTIC_FILES,
            atmosphere_bytes=profile_bytes,
            o4_bytes=profile_o4_bytes,
        )
        scientific_result = _parse_mystic_output(run_dir, case)
        files = _recursive_file_receipts(temp_dir)
        result = {
            "schema": CASE_SCHEMA,
            "case": case,
            "generation_identity": generation_identity,
            "atmosphere": atmosphere_metadata,
            "o4_companion": (
                None
                if case["profile_method"] == "source_profile"
                else o4_metadata
            ),
            "result": scientific_result,
            "files": files,
        }
        (temp_dir / "case-result.json").write_bytes(
            base_lab.canonical_json_bytes(result)
        )
        os.replace(temp_dir, final_dir)
        return result
    except Exception as exc:
        raise VisibilityLabError(
            f"MYSTIC elevated-site case failed; preserved at {temp_dir}: {exc}"
        ) from exc


def _compare_case_files(
    output_root: Path,
    original_id: str,
    comparison_id: str,
) -> dict[str, Any]:
    mismatches = [
        filename
        for filename in MYSTIC_SCIENTIFIC_FILES
        if (
            output_root / original_id / "mystic" / filename
        ).read_bytes()
        != (
            output_root / comparison_id / "mystic" / filename
        ).read_bytes()
    ]
    if mismatches:
        raise VisibilityLabError(
            f"MYSTIC controls differ for {original_id} and {comparison_id}: "
            + ", ".join(mismatches)
        )
    return {
        "original_case_id": original_id,
        "comparison_case_id": comparison_id,
        "byte_identical_files": list(MYSTIC_SCIENTIFIC_FILES),
    }


def _profile_filename(site_altitude_m: float) -> str:
    return f"afglus_site_{_site_token(site_altitude_m)}.dat"


def _o4_filename(site_altitude_m: float) -> str:
    return f"o4_site_{_site_token(site_altitude_m)}.dat"


def _prepare_profiles(
    output_root: Path,
    spec: dict[str, Any],
    source_text: str,
) -> dict[
    float,
    tuple[bytes, dict[str, Any], bytes, dict[str, Any]],
]:
    profiles: dict[
        float,
        tuple[bytes, dict[str, Any], bytes, dict[str, Any]],
    ] = {}
    for site in spec["atmosphere_construction"]["site_altitudes_m"]:
        atmosphere_payload, atmosphere_metadata = (
            construct_truncated_atmosphere(source_text, site)
        )
        o4_payload, o4_metadata = construct_truncated_o4_profile(
            source_text,
            site,
        )
        profiles[float(site)] = (
            atmosphere_payload,
            atmosphere_metadata,
            o4_payload,
            o4_metadata,
        )

    profile_dir = output_root / "profiles"
    profile_manifest = {
        "schema": PROFILE_SCHEMA,
        "construction": spec["atmosphere_construction"]["interpolation_policy"],
        "o4_closure": spec["atmosphere_construction"]["derived_o4_closure"],
        "profiles": [
            {
                **metadata,
                "filename": _profile_filename(site),
                "bytes": len(payload),
                "sha256": base_lab.sha256_bytes(payload),
                "o4_companion": {
                    **o4_metadata,
                    "filename": _o4_filename(site),
                    "bytes": len(o4_payload),
                    "sha256": base_lab.sha256_bytes(o4_payload),
                },
            }
            for site, (
                payload,
                metadata,
                o4_payload,
                o4_metadata,
            ) in sorted(profiles.items())
        ],
    }
    expected_files = {
        _profile_filename(site): payload
        for site, (payload, _, _, _) in profiles.items()
    }
    expected_files.update(
        {
            _o4_filename(site): o4_payload
            for site, (_, _, o4_payload, _) in profiles.items()
        }
    )
    expected_files["profiles.json"] = base_lab.canonical_json_bytes(profile_manifest)
    if profile_dir.exists():
        actual_names = {
            path.name for path in profile_dir.iterdir() if path.is_file()
        }
        if actual_names != set(expected_files) or any(
            (profile_dir / name).read_bytes() != payload
            for name, payload in expected_files.items()
        ):
            raise VisibilityLabError("existing profile directory is stale or partial")
        if any(path.is_symlink() for path in profile_dir.iterdir()):
            raise VisibilityLabError("profile directory contains a symlink")
        return profiles

    temp_dir = Path(tempfile.mkdtemp(prefix=".profiles.", dir=output_root))
    for name, payload in expected_files.items():
        (temp_dir / name).write_bytes(payload)
    os.replace(temp_dir, profile_dir)
    return profiles


def _verify_libradtran_source_semantics(
    spec: dict[str, Any],
    libradtran_root: Path,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for expected in spec["libradtran_source_semantics"]["source_files"]:
        path = libradtran_root / expected["path"]
        if (
            not path.is_file()
            or path.stat().st_size != expected["bytes"]
            or base_lab.sha256_file(path) != expected["sha256"]
        ):
            raise VisibilityLabError(
                f"governing libRadtran source identity differs: {path}"
            )
        receipts.append(base_lab.file_receipt(path, relative_to=libradtran_root))
    return receipts


def _receipt_matches(path: Path, receipt: dict[str, Any]) -> bool:
    return (
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_size == receipt.get("bytes")
        and base_lab.sha256_file(path) == receipt.get("sha256")
    )


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
        raise VisibilityLabError("elevated-site specification must be an object")
    validate_spec(spec)

    base_declaration = spec["base_lab"]
    base_spec_path = _verify_declared_repo_file(base_declaration, label="spec")
    base_builder_path = _verify_declared_repo_file(
        base_declaration,
        label="builder",
    )
    base_validator_path = _verify_declared_repo_file(
        base_declaration,
        label="validator",
    )
    base_spec = json.loads(base_spec_path.read_text(encoding="utf-8"))
    base_lab.validate_spec(base_spec)

    output_root = output_root.resolve()
    if output_root.is_symlink():
        raise VisibilityLabError("output root must not be a symlink")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "artifact-manifest.json"
    if manifest_path.exists():
        raise VisibilityLabError(
            f"artifact manifest already exists; choose a new output root: {manifest_path}"
        )

    direct_cases = expand_direct_cases(spec)
    mystic_cases = expand_mystic_cases(spec)
    allowed_entries = {
        "profiles",
        *(case["case_id"] for case in direct_cases),
        *(case["case_id"] for case in mystic_cases),
    }
    unexpected = sorted(
        entry.name for entry in output_root.iterdir() if entry.name not in allowed_entries
    )
    if unexpected:
        raise VisibilityLabError(
            "output root contains unowned or partial entries: " + ", ".join(unexpected)
        )

    tooling_paths = {
        "builder": Path(__file__).resolve(),
        "validator": VALIDATOR_PATH.resolve(),
        "checkpoint1_builder": base_builder_path.resolve(),
        "checkpoint1_validator": base_validator_path.resolve(),
    }
    for role, path in tooling_paths.items():
        if not path.is_file():
            raise VisibilityLabError(f"required {role} is missing: {path}")
    tooling = {
        role: base_lab.file_receipt(path, relative_to=REPO_ROOT)
        for role, path in tooling_paths.items()
    }
    specifications = {
        "elevated_site_probe": base_lab.file_receipt(
            spec_path,
            relative_to=REPO_ROOT,
        ),
        "checkpoint1_lab": base_lab.file_receipt(
            base_spec_path,
            relative_to=REPO_ROOT,
        ),
    }

    libradtran_root = libradtran_root.resolve()
    generator = base_lab.verify_generator(
        base_spec,
        source_archive=source_archive,
        libradtran_root=libradtran_root,
    )
    governing_source_files = _verify_libradtran_source_semantics(
        spec,
        libradtran_root,
    )
    bound_generator = {
        **generator,
        "governing_source_files": governing_source_files,
    }
    environment = base_lab.environment_receipt()
    generation_identity = {
        "tooling": tooling,
        "specifications": specifications,
        "generator": bound_generator,
        "environment": environment,
        "runtime_boundary": spec["runtime_boundary"],
    }
    source_profile_path = (
        libradtran_root / spec["atmosphere_construction"]["source_path"]
    )
    source_text = source_profile_path.read_text(encoding="utf-8")
    profiles = _prepare_profiles(output_root, spec, source_text)

    uvspec = libradtran_root / "bin" / "uvspec"
    data_root = libradtran_root / "data"
    direct_results = [
        _build_direct_case(
            case,
            spec=spec,
            base_spec=base_spec,
            atmosphere_bytes=profiles[case["site_altitude_m"]][0],
            atmosphere_metadata=profiles[case["site_altitude_m"]][1],
            o4_bytes=profiles[case["site_altitude_m"]][2],
            o4_metadata=profiles[case["site_altitude_m"]][3],
            generation_identity=generation_identity,
            uvspec=uvspec,
            data_root=data_root,
            output_root=output_root,
        )
        for case in direct_cases
    ]
    mystic_results = [
        _build_mystic_case(
            case,
            spec=spec,
            base_spec=base_spec,
            atmosphere_bytes=profiles[case["site_altitude_m"]][0],
            atmosphere_metadata=profiles[case["site_altitude_m"]][1],
            o4_bytes=profiles[case["site_altitude_m"]][2],
            o4_metadata=profiles[case["site_altitude_m"]][3],
            generation_identity=generation_identity,
            uvspec=uvspec,
            data_root=data_root,
            output_root=output_root,
        )
        for case in mystic_cases
    ]

    sea_level_control = _compare_case_files(
        output_root,
        "mystic_source_site_0000m_control",
        "mystic_truncated_site_0000m",
    )
    repeat_site = spec["mystic_elevated_smoke_profile"][
        "exact_repeat_site_altitude_m"
    ]
    fixed_seed_repeat = _compare_case_files(
        output_root,
        f"mystic_truncated_site_{_site_token(repeat_site)}",
        f"mystic_truncated_site_{_site_token(repeat_site)}_repeat",
    )

    if spec_path.read_bytes() != spec_bytes:
        raise VisibilityLabError("probe specification changed during generation")
    for role, path in tooling_paths.items():
        if not _receipt_matches(path, tooling[role]):
            raise VisibilityLabError(f"{role} changed during generation")
    for label, path in {
        "elevated_site_probe": spec_path,
        "checkpoint1_lab": base_spec_path,
    }.items():
        if not _receipt_matches(path, specifications[label]):
            raise VisibilityLabError(f"{label} specification changed during generation")
    source_archive = source_archive.resolve()
    if not _receipt_matches(source_archive, generator["source_archive"]):
        raise VisibilityLabError("libRadtran source archive changed during generation")
    if base_lab.sha256_file(uvspec) != generator["uvspec_sha256"]:
        raise VisibilityLabError("uvspec executable changed during generation")
    _verify_libradtran_source_semantics(spec, libradtran_root)

    maximum_differences = {
        field: max(
            result["comparison"]["absolute_differences"][field]
            for result in direct_results
        )
        for field in (
            "normalized_direct_irradiance_edir_over_e0",
            "direct_spectral_transmission",
            "extinction_magnitude",
        )
    }
    case_summaries = [
        {
            "case_id": result["case"]["case_id"],
            "kind": result["case"]["kind"],
            "result": (
                result.get("comparison")
                if result["case"]["kind"] == "direct_altitude_oracle_comparison"
                else result["result"]
            ),
        }
        for result in [*direct_results, *mystic_results]
    ]
    file_inventory = _recursive_file_receipts(output_root)
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_status": ARTIFACT_STATUS,
        "tooling": tooling,
        "specifications": specifications,
        "spec_id": spec["spec_id"],
        "models": {
            "direct_oracle": spec["direct_oracle_profile"]["model_id"],
            "mystic_elevated_smoke": spec["mystic_elevated_smoke_profile"][
                "model_id"
            ],
        },
        "generator": bound_generator,
        "environment": environment,
        "generation_identity": generation_identity,
        "runtime_boundary": spec["runtime_boundary"],
        "profile_count": len(profiles),
        "direct_comparison_case_count": len(direct_results),
        "mystic_case_count": len(mystic_results),
        "case_count": len(case_summaries),
        "cases": case_summaries,
        "direct_comparison_maximum_absolute_differences": maximum_differences,
        "sea_level_source_vs_truncated_control": sea_level_control,
        "fixed_seed_repeat_check": fixed_seed_repeat,
        "files": file_inventory,
    }
    manifest_path.write_bytes(base_lab.canonical_json_bytes(manifest))
    return manifest


def inspect_spec(spec_path: Path) -> dict[str, Any]:
    spec = load_spec(spec_path)
    direct_cases = expand_direct_cases(spec)
    mystic_cases = expand_mystic_cases(spec)
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "site_profile_count": len(
            spec["atmosphere_construction"]["site_altitudes_m"]
        ),
        "direct_comparison_case_count": len(direct_cases),
        "direct_uvspec_run_count": 2 * len(direct_cases),
        "mystic_case_count": len(mystic_cases),
        "total_uvspec_run_count": 2 * len(direct_cases) + len(mystic_cases),
        "checkpoint1_identity_preserved": True,
        "runtime_data_pack_authorized": False,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or inspect the external Phase 1 elevated-site visibility probe."
        )
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_SPEC_PATH,
        help="Versioned elevated-site probe specification.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inspect")
    build = subparsers.add_parser("build")
    build.add_argument("--source-archive", type=Path, required=True)
    build.add_argument("--libradtran-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "inspect":
            payload = inspect_spec(args.spec)
        else:
            payload = build_probe(
                args.spec,
                source_archive=args.source_archive,
                libradtran_root=args.libradtran_root,
                output_root=args.output,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
