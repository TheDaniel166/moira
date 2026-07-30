#!/usr/bin/env python3
"""Independently validate a Phase 1 elevated-site probe artifact."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_elevated_site_probe_spec.json"
)
SPEC_SCHEMA = "moira.visibility-elevated-site-probe-spec/v1"
ARTIFACT_SCHEMA = "moira.visibility-elevated-site-probe-artifact/v1"
CASE_SCHEMA = "moira.visibility-elevated-site-probe-case/v1"
PROFILE_SCHEMA = "moira.visibility-elevated-site-profile-set/v1"
ARTIFACT_STATUS = "phase1_elevated_site_evidence_not_runtime_data_pack"
SCIENTIFIC_REPEAT_FILES = (
    "mc.flx.spc",
    "mc.flx.std.spc",
    "mc.rad.spc",
    "mc.rad.std.spc",
    "mc0.rad",
    "mc0.rad.std",
    "randomseed",
)


class ValidationError(ValueError):
    """Raised when an elevated-site artifact violates its receipt."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} path must be a nonempty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValidationError(f"{label} path is not safe and canonical: {value!r}")
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
    path = root / Path(relative)
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != byte_count
        or _sha256_file(path) != expected_sha
    ):
        raise ValidationError(f"{label} receipt mismatch: {path}")
    return relative


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{label} must be a JSON object")
    return payload


def _load_spec(path: Path) -> dict[str, Any]:
    spec = _load_json(path, "elevated-site probe specification")
    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("status") != "research_probe_not_runtime_data_pack"
    ):
        raise ValidationError("unsupported elevated-site probe specification")
    boundary = spec.get("runtime_boundary")
    if boundary != {
        "network_allowed": False,
        "automatic_download_allowed": False,
        "engine_dependency_allowed": False,
        "engine_runtime_invocation_allowed": False,
        "generated_numerical_products_only": True,
    }:
        raise ValidationError("specification runtime boundary was weakened")
    construction = spec.get("atmosphere_construction")
    if not isinstance(construction, dict):
        raise ValidationError("atmosphere construction is missing")
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
        raise ValidationError("specification O4 closure policy changed")
    altitudes = construction.get("site_altitudes_m")
    if (
        not isinstance(altitudes, list)
        or not altitudes
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 5000.0
            for value in altitudes
        )
        or any(float(a) >= float(b) for a, b in zip(altitudes, altitudes[1:]))
    ):
        raise ValidationError("specification site-altitude axis is invalid")
    direct = spec.get("direct_oracle_profile")
    mystic = spec.get("mystic_elevated_smoke_profile")
    if not isinstance(direct, dict) or not isinstance(mystic, dict):
        raise ValidationError("probe profiles are incomplete")
    if (
        direct.get("rte_solver") != "disort"
        or direct.get("geometry") != "pseudospherical"
        or direct.get("number_of_streams") != 16
        or mystic.get("sea_level_source_profile_control") is not True
    ):
        raise ValidationError("probe solver contract changed")
    return spec


def _site_token(site_altitude_m: float) -> str:
    return f"{int(round(float(site_altitude_m))):04d}m"


def _angle_token(value: float) -> str:
    return f"{float(value):05.2f}".replace(".", "p")


def _wavelength_token(value: float) -> str:
    return f"{int(round(float(value))):04d}nm"


def _profile_filename(site_altitude_m: float) -> str:
    return f"afglus_site_{_site_token(site_altitude_m)}.dat"


def _o4_filename(site_altitude_m: float) -> str:
    return f"o4_site_{_site_token(site_altitude_m)}.dat"


def _expected_direct_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    construction = spec["atmosphere_construction"]
    direct = spec["direct_oracle_profile"]
    return [
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
        for site, target, wavelength in itertools.product(
            construction["site_altitudes_m"],
            direct["target_true_altitude_deg"],
            direct["wavelength_nm"],
        )
    ]


def _expected_mystic_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    mystic = spec["mystic_elevated_smoke_profile"]
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
    cases = [
        {
            "case_id": "mystic_source_site_0000m_control",
            "kind": "mystic_spherical_source_profile_control",
            "profile_method": "source_profile",
            "site_altitude_m": 0.0,
            **shared,
        }
    ]
    for site in spec["atmosphere_construction"]["site_altitudes_m"]:
        cases.append(
            {
                "case_id": f"mystic_truncated_site_{_site_token(site)}",
                "kind": "mystic_spherical_truncated_profile",
                "profile_method": "truncated_profile",
                "site_altitude_m": float(site),
                **shared,
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
            **shared,
        }
    )
    return cases


def _verify_current_repo_receipt(
    receipt: Any,
    *,
    expected_path: str,
    label: str,
) -> None:
    if not isinstance(receipt, dict) or receipt.get("path") != expected_path:
        raise ValidationError(f"{label} points at an unexpected repository path")
    _validate_file_receipt(REPO_ROOT, receipt, label=label)


def _verify_tool_and_spec_receipts(
    manifest: dict[str, Any],
    spec: dict[str, Any],
    spec_path: Path,
) -> dict[str, Any]:
    tooling = manifest.get("tooling")
    specifications = manifest.get("specifications")
    if not isinstance(tooling, dict) or set(tooling) != {
        "builder",
        "validator",
        "checkpoint1_builder",
        "checkpoint1_validator",
    }:
        raise ValidationError("artifact tooling receipt is incomplete")
    if not isinstance(specifications, dict) or set(specifications) != {
        "elevated_site_probe",
        "checkpoint1_lab",
    }:
        raise ValidationError("artifact specification receipt is incomplete")
    _verify_current_repo_receipt(
        tooling["builder"],
        expected_path="scripts/build_visibility_elevated_site_probe.py",
        label="elevated-site builder",
    )
    _verify_current_repo_receipt(
        tooling["validator"],
        expected_path="scripts/validate_visibility_elevated_site_probe.py",
        label="elevated-site validator",
    )
    _verify_current_repo_receipt(
        tooling["checkpoint1_builder"],
        expected_path="scripts/build_visibility_radiance_lut.py",
        label="checkpoint-one builder",
    )
    _verify_current_repo_receipt(
        tooling["checkpoint1_validator"],
        expected_path="scripts/validate_visibility_radiance_lut.py",
        label="checkpoint-one validator",
    )
    relative_spec = spec_path.resolve().relative_to(REPO_ROOT).as_posix()
    _verify_current_repo_receipt(
        specifications["elevated_site_probe"],
        expected_path=relative_spec,
        label="elevated-site specification",
    )
    base_spec_path = spec["base_lab"]["spec_path"]
    _verify_current_repo_receipt(
        specifications["checkpoint1_lab"],
        expected_path=base_spec_path,
        label="checkpoint-one specification",
    )
    base_spec = _load_json(REPO_ROOT / base_spec_path, "checkpoint-one specification")
    for label in ("spec", "builder", "validator"):
        declaration = spec["base_lab"]
        path = REPO_ROOT / declaration[f"{label}_path"]
        if (
            not path.is_file()
            or path.stat().st_size != declaration[f"{label}_bytes"]
            or _sha256_file(path) != declaration[f"{label}_sha256"]
        ):
            raise ValidationError(f"checkpoint-one {label} identity changed")
    return base_spec


def _verify_complete_artifact_inventory(
    artifact_root: Path,
    manifest: dict[str, Any],
) -> None:
    receipts = manifest.get("files")
    if not isinstance(receipts, list) or not receipts:
        raise ValidationError("artifact has no complete file inventory")
    expected: set[str] = set()
    for index, receipt in enumerate(receipts):
        relative = _validate_file_receipt(
            artifact_root,
            receipt,
            label=f"artifact file {index}",
        )
        if relative == "artifact-manifest.json" or relative in expected:
            raise ValidationError("artifact inventory contains a duplicate or manifest")
        expected.add(relative)
    actual: set[str] = set()
    for path in artifact_root.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"artifact contains a symlink: {path}")
        if path.is_file() and path.name != "artifact-manifest.json":
            actual.add(path.relative_to(artifact_root).as_posix())
    if actual != expected:
        raise ValidationError(
            "artifact inventory is incomplete or extended: "
            f"missing={sorted(expected - actual)} "
            f"unexpected={sorted(actual - expected)}"
        )


def _parse_profile(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 9:
            raise ValidationError(
                f"profile {path} row {line_number} does not have nine columns"
            )
        try:
            row = [float(field) for field in fields]
        except ValueError as exc:
            raise ValidationError(f"profile {path} contains a non-number") from exc
        if any(not math.isfinite(value) or value < 0.0 for value in row):
            raise ValidationError(f"profile {path} contains an invalid value")
        rows.append(row)
    if len(rows) < 2 or any(
        rows[index][0] <= rows[index + 1][0]
        for index in range(len(rows) - 1)
    ):
        raise ValidationError(f"profile {path} is not strictly top-down")
    return rows


def _parse_o4_profile(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 2:
            raise ValidationError(
                f"O4 profile {path} row {line_number} does not have two columns"
            )
        try:
            row = [float(field) for field in fields]
        except ValueError as exc:
            raise ValidationError(
                f"O4 profile {path} contains a non-number"
            ) from exc
        if any(not math.isfinite(value) or value < 0.0 for value in row):
            raise ValidationError(f"O4 profile {path} contains an invalid value")
        rows.append(row)
    if len(rows) < 2 or any(
        rows[index][0] <= rows[index + 1][0]
        for index in range(len(rows) - 1)
    ):
        raise ValidationError(f"O4 profile {path} is not strictly top-down")
    return rows


def _verify_profiles(
    artifact_root: Path,
    spec: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[float, dict[str, str]]:
    profiles_root = artifact_root / "profiles"
    profile_set = _load_json(profiles_root / "profiles.json", "profile set")
    if (
        profile_set.get("schema") != PROFILE_SCHEMA
        or profile_set.get("construction")
        != spec["atmosphere_construction"]["interpolation_policy"]
        or profile_set.get("o4_closure")
        != spec["atmosphere_construction"]["derived_o4_closure"]
    ):
        raise ValidationError("profile-set schema is unsupported")
    profiles = profile_set.get("profiles")
    expected_altitudes = [
        float(value)
        for value in spec["atmosphere_construction"]["site_altitudes_m"]
    ]
    if not isinstance(profiles, list) or len(profiles) != len(expected_altitudes):
        raise ValidationError("profile-set count does not match the specification")
    seen: set[float] = set()
    verified: dict[float, dict[str, str]] = {}
    for receipt in profiles:
        if not isinstance(receipt, dict):
            raise ValidationError("profile-set entry is invalid")
        altitude_m = float(receipt.get("site_altitude_m", math.nan))
        filename = receipt.get("filename")
        if (
            altitude_m not in expected_altitudes
            or altitude_m in seen
            or not isinstance(filename, str)
            or filename != _profile_filename(altitude_m)
        ):
            raise ValidationError("profile-set identity is invalid")
        seen.add(altitude_m)
        path = profiles_root / filename
        if (
            not path.is_file()
            or path.stat().st_size != receipt.get("bytes")
            or _sha256_file(path) != receipt.get("sha256")
        ):
            raise ValidationError(f"profile-set checksum mismatch: {path}")
        rows = _parse_profile(path)
        bottom = rows[-1]
        if not math.isclose(
            bottom[0],
            altitude_m / 1000.0,
            rel_tol=0.0,
            abs_tol=5e-7,
        ):
            raise ValidationError(f"profile bottom altitude is wrong: {path}")
        bottom_receipt = receipt.get("bottom_level")
        if not isinstance(bottom_receipt, dict):
            raise ValidationError(f"profile bottom receipt is missing: {path}")
        labels = (
            "altitude_km",
            "pressure_hpa",
            "temperature_k",
            "air_number_density_cm-3",
            "o3_number_density_cm-3",
            "o2_number_density_cm-3",
            "h2o_number_density_cm-3",
            "co2_number_density_cm-3",
            "no2_number_density_cm-3",
        )
        for label, value in zip(labels, bottom):
            if not math.isclose(
                float(bottom_receipt[label]),
                value,
                rel_tol=5e-8,
                abs_tol=1e-12,
            ):
                raise ValidationError(f"profile bottom receipt differs for {label}")
        o4_receipt = receipt.get("o4_companion")
        if not isinstance(o4_receipt, dict):
            raise ValidationError(f"profile O4 receipt is missing: {path}")
        o4_filename = o4_receipt.get("filename")
        if (
            not isinstance(o4_filename, str)
            or o4_filename != _o4_filename(altitude_m)
        ):
            raise ValidationError(f"profile O4 identity is invalid: {path}")
        o4_path = profiles_root / o4_filename
        if (
            not o4_path.is_file()
            or o4_path.stat().st_size != o4_receipt.get("bytes")
            or _sha256_file(o4_path) != o4_receipt.get("sha256")
        ):
            raise ValidationError(f"profile O4 checksum mismatch: {o4_path}")
        o4_rows = _parse_o4_profile(o4_path)
        o4_bottom = o4_rows[-1]
        if (
            not math.isclose(
                o4_bottom[0],
                altitude_m / 1000.0,
                rel_tol=0.0,
                abs_tol=5e-7,
            )
            or not math.isclose(
                o4_bottom[1],
                float(o4_receipt.get("bottom_scaled_o4_density_cm-3", math.nan)),
                rel_tol=5e-8,
                abs_tol=1e-30,
            )
        ):
            raise ValidationError(f"profile O4 bottom receipt differs: {o4_path}")
        verified[altitude_m] = {
            "atmosphere_sha256": str(receipt["sha256"]),
            "o4_sha256": str(o4_receipt["sha256"]),
        }
    if seen != set(expected_altitudes) or manifest.get("profile_count") != len(seen):
        raise ValidationError("profile-set coverage is incomplete")
    return verified


def _verify_case_file_receipts(case_dir: Path, result: dict[str, Any]) -> None:
    receipts = result.get("files")
    if not isinstance(receipts, list) or not receipts:
        raise ValidationError(f"case has no file inventory: {case_dir}")
    expected: set[str] = set()
    for index, receipt in enumerate(receipts):
        relative = _validate_file_receipt(
            case_dir,
            receipt,
            label=f"{case_dir.name} file {index}",
        )
        if relative == "case-result.json" or relative in expected:
            raise ValidationError(f"case inventory contains a duplicate: {case_dir}")
        expected.add(relative)
    actual = {
        path.relative_to(case_dir).as_posix()
        for path in case_dir.rglob("*")
        if path.is_file() and path.name != "case-result.json"
    }
    if actual != expected:
        raise ValidationError(f"case inventory is incomplete or extended: {case_dir}")
    if any(path.is_symlink() for path in case_dir.rglob("*")):
        raise ValidationError(f"case contains a symlink: {case_dir}")


def _verify_direct_case(
    case_dir: Path,
    result: dict[str, Any],
    case: dict[str, Any],
    spec: dict[str, Any],
    profile_receipt: dict[str, str],
) -> dict[str, float]:
    source = result.get("altitude_option_result")
    truncated = result.get("truncated_profile_result")
    comparison = result.get("comparison")
    if (
        not isinstance(source, dict)
        or not isinstance(truncated, dict)
        or not isinstance(comparison, dict)
    ):
        raise ValidationError(f"direct comparison is incomplete: {case_dir}")
    projection = math.sin(math.radians(case["target_true_altitude_deg"]))
    for method, values in (("source", source), ("truncated", truncated)):
        normalized = float(
            values.get("normalized_direct_irradiance_edir_over_e0", math.nan)
        )
        transmission = float(
            values.get("direct_spectral_transmission", math.nan)
        )
        extinction = float(values.get("extinction_magnitude", math.nan))
        if (
            not math.isfinite(normalized)
            or normalized <= 0.0
            or not math.isfinite(transmission)
            or not 0.0 < transmission <= 1.0
            or not math.isfinite(extinction)
            or float(values.get("wavelength_nm", math.nan))
            != case["wavelength_nm"]
            or not math.isclose(
                float(
                    values.get(
                        "geometric_projection_sin_altitude",
                        math.nan,
                    )
                ),
                projection,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or not math.isclose(
                transmission,
                normalized / projection,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or not math.isclose(
                extinction,
                -2.5 * math.log10(transmission),
                rel_tol=0.0,
                abs_tol=1e-15,
            )
        ):
            raise ValidationError(
                f"{method} direct result is internally inconsistent: {case_dir}"
            )
    tolerance_names = {
        "normalized_direct_irradiance_edir_over_e0": (
            "normalized_direct_irradiance_abs_tolerance"
        ),
        "direct_spectral_transmission": (
            "direct_spectral_transmission_abs_tolerance"
        ),
        "extinction_magnitude": "extinction_magnitude_abs_tolerance",
    }
    recorded_differences = comparison.get("absolute_differences")
    recorded_tolerances = comparison.get("tolerances")
    expected_tolerances = spec["direct_oracle_profile"]["comparison"]
    if (
        comparison.get("status") != "within_declared_absolute_tolerances"
        or not isinstance(recorded_differences, dict)
        or recorded_tolerances != expected_tolerances
    ):
        raise ValidationError(f"direct comparison policy differs: {case_dir}")
    differences: dict[str, float] = {}
    for field, tolerance_name in tolerance_names.items():
        difference = abs(float(source[field]) - float(truncated[field]))
        if (
            not math.isclose(
                difference,
                float(recorded_differences.get(field, math.nan)),
                rel_tol=0.0,
                abs_tol=1e-18,
            )
            or difference > float(expected_tolerances[tolerance_name])
        ):
            raise ValidationError(f"direct comparison exceeds tolerance: {case_dir}")
        differences[field] = difference

    altitude_input = (
        case_dir / "altitude_option" / "input.inp"
    ).read_text(encoding="utf-8")
    truncated_input = (
        case_dir / "truncated_profile" / "input.inp"
    ).read_text(encoding="utf-8")
    expected_altitude_line = f"altitude {case['site_altitude_m'] / 1000.0:g}"
    if (
        expected_altitude_line not in altitude_input.splitlines()
        or any(
            line.startswith("altitude ")
            for line in truncated_input.splitlines()
        )
        or "mc_elevation_file" in truncated_input
        or "atmosphere_file atmosphere.dat" not in truncated_input.splitlines()
        or "mol_file O4 o4.dat cm_3" not in truncated_input.splitlines()
        or any(
            line.startswith("mol_file O4 ")
            for line in altitude_input.splitlines()
        )
    ):
        raise ValidationError(f"direct altitude construction is wrong: {case_dir}")
    rows = _parse_profile(
        case_dir / "truncated_profile" / "atmosphere.dat"
    )
    if (
        _sha256_file(case_dir / "truncated_profile" / "atmosphere.dat")
        != profile_receipt["atmosphere_sha256"]
        or _sha256_file(case_dir / "truncated_profile" / "o4.dat")
        != profile_receipt["o4_sha256"]
    ):
        raise ValidationError(
            f"direct case does not use the admitted profiles: {case_dir}"
        )
    if not math.isclose(
        rows[-1][0],
        case["site_altitude_m"] / 1000.0,
        rel_tol=0.0,
        abs_tol=5e-7,
    ):
        raise ValidationError(f"direct case profile has the wrong bottom: {case_dir}")
    o4_rows = _parse_o4_profile(
        case_dir / "truncated_profile" / "o4.dat"
    )
    if not math.isclose(
        o4_rows[-1][0],
        case["site_altitude_m"] / 1000.0,
        rel_tol=0.0,
        abs_tol=5e-7,
    ):
        raise ValidationError(f"direct O4 profile has the wrong bottom: {case_dir}")
    return differences


def _verify_mystic_case(
    case_dir: Path,
    result: dict[str, Any],
    case: dict[str, Any],
    profile_receipt: dict[str, str],
) -> None:
    values = result.get("result")
    if not isinstance(values, dict):
        raise ValidationError(f"MYSTIC result is missing: {case_dir}")
    radiance = float(
        values.get("escape_spectral_radiance_mw_m2_nm_sr", math.nan)
    )
    standard_deviation = float(
        values.get("reported_standard_deviation_mw_m2_nm_sr", math.nan)
    )
    if (
        not math.isfinite(radiance)
        or radiance < 0.0
        or not math.isfinite(standard_deviation)
        or standard_deviation < 0.0
        or float(values.get("wavelength_nm", math.nan)) != case["wavelength_nm"]
    ):
        raise ValidationError(f"MYSTIC result is invalid: {case_dir}")
    input_text = (case_dir / "mystic" / "input.inp").read_text(encoding="utf-8")
    if (
        "mc_spherical 1D" not in input_text.splitlines()
        or any(line.startswith("altitude ") for line in input_text.splitlines())
        or "mc_elevation_file" in input_text
    ):
        raise ValidationError(f"MYSTIC elevated-site input is invalid: {case_dir}")
    atmosphere_path = case_dir / "mystic" / "atmosphere.dat"
    if case["profile_method"] == "source_profile":
        if (
            atmosphere_path.exists()
            or (case_dir / "mystic" / "o4.dat").exists()
            or any(
                line.startswith("mol_file O4 ")
                for line in input_text.splitlines()
            )
        ):
            raise ValidationError(
                f"source-profile control embeds a profile: {case_dir}"
            )
    else:
        if "mol_file O4 o4.dat cm_3" not in input_text.splitlines():
            raise ValidationError(f"MYSTIC input lacks O4 closure: {case_dir}")
        if (
            _sha256_file(atmosphere_path)
            != profile_receipt["atmosphere_sha256"]
            or _sha256_file(case_dir / "mystic" / "o4.dat")
            != profile_receipt["o4_sha256"]
        ):
            raise ValidationError(
                f"MYSTIC case does not use the admitted profiles: {case_dir}"
            )
        rows = _parse_profile(atmosphere_path)
        if not math.isclose(
            rows[-1][0],
            case["site_altitude_m"] / 1000.0,
            rel_tol=0.0,
            abs_tol=5e-7,
        ):
            raise ValidationError(f"MYSTIC profile has the wrong bottom: {case_dir}")
        o4_rows = _parse_o4_profile(case_dir / "mystic" / "o4.dat")
        if not math.isclose(
            o4_rows[-1][0],
            case["site_altitude_m"] / 1000.0,
            rel_tol=0.0,
            abs_tol=5e-7,
        ):
            raise ValidationError(
                f"MYSTIC O4 profile has the wrong bottom: {case_dir}"
            )


def _verify_byte_identity(
    artifact_root: Path,
    receipt: Any,
    *,
    expected_original: str,
    expected_comparison: str,
    label: str,
) -> None:
    if (
        not isinstance(receipt, dict)
        or receipt.get("original_case_id") != expected_original
        or receipt.get("comparison_case_id") != expected_comparison
        or receipt.get("byte_identical_files") != list(SCIENTIFIC_REPEAT_FILES)
    ):
        raise ValidationError(f"{label} receipt is invalid")
    for filename in SCIENTIFIC_REPEAT_FILES:
        original = artifact_root / expected_original / "mystic" / filename
        comparison = artifact_root / expected_comparison / "mystic" / filename
        if original.read_bytes() != comparison.read_bytes():
            raise ValidationError(f"{label} is not byte-identical: {filename}")


def _verify_generator(
    manifest: dict[str, Any],
    spec: dict[str, Any],
    base_spec: dict[str, Any],
) -> None:
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise ValidationError("generator receipt is missing")
    archive = generator.get("source_archive")
    source = base_spec.get("source")
    if (
        not isinstance(archive, dict)
        or not isinstance(source, dict)
        or archive.get("bytes") != source.get("archive_bytes")
        or archive.get("sha256") != source.get("archive_sha256")
        or source.get("version") not in str(generator.get("uvspec_version"))
        or not isinstance(generator.get("uvspec_sha256"), str)
        or len(generator["uvspec_sha256"]) != 64
    ):
        raise ValidationError("libRadtran generator identity is invalid")
    governing = generator.get("governing_source_files")
    expected = spec["libradtran_source_semantics"]["source_files"]
    if governing != expected:
        raise ValidationError("governing libRadtran source receipts differ")


def validate_artifact(
    artifact_root: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
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

    spec = _load_spec(spec_path.resolve())
    manifest = _load_json(manifest_path, "artifact manifest")
    if (
        manifest.get("schema") != ARTIFACT_SCHEMA
        or manifest.get("artifact_status") != ARTIFACT_STATUS
        or manifest.get("spec_id") != spec.get("spec_id")
        or manifest.get("runtime_boundary") != spec.get("runtime_boundary")
    ):
        raise ValidationError("artifact identity or runtime boundary differs")
    base_spec = _verify_tool_and_spec_receipts(manifest, spec, spec_path.resolve())
    _verify_generator(manifest, spec, base_spec)
    expected_generation_identity = {
        "tooling": manifest.get("tooling"),
        "specifications": manifest.get("specifications"),
        "generator": manifest.get("generator"),
        "environment": manifest.get("environment"),
        "runtime_boundary": manifest.get("runtime_boundary"),
    }
    if manifest.get("generation_identity") != expected_generation_identity:
        raise ValidationError("artifact generation identity is inconsistent")
    _verify_complete_artifact_inventory(artifact_root, manifest)
    profile_receipts = _verify_profiles(artifact_root, spec, manifest)

    direct_cases = _expected_direct_cases(spec)
    mystic_cases = _expected_mystic_cases(spec)
    expected_cases = {
        case["case_id"]: case for case in [*direct_cases, *mystic_cases]
    }
    if (
        manifest.get("direct_comparison_case_count") != len(direct_cases)
        or manifest.get("mystic_case_count") != len(mystic_cases)
        or manifest.get("case_count") != len(expected_cases)
    ):
        raise ValidationError("artifact case counts differ from the specification")
    case_summaries = manifest.get("cases")
    if (
        not isinstance(case_summaries, list)
        or {entry.get("case_id") for entry in case_summaries if isinstance(entry, dict)}
        != set(expected_cases)
    ):
        raise ValidationError("artifact case summary inventory is incomplete")

    direct_differences: list[dict[str, float]] = []
    for case_id, expected_case in expected_cases.items():
        case_dir = artifact_root / case_id
        if not case_dir.is_dir() or case_dir.is_symlink():
            raise ValidationError(f"case directory is missing: {case_id}")
        result = _load_json(case_dir / "case-result.json", f"case {case_id}")
        if result.get("schema") != CASE_SCHEMA or result.get("case") != expected_case:
            raise ValidationError(f"case identity differs: {case_id}")
        if result.get("generation_identity") != expected_generation_identity:
            raise ValidationError(f"case generation identity differs: {case_id}")
        _verify_case_file_receipts(case_dir, result)
        profile_receipt = profile_receipts[expected_case["site_altitude_m"]]
        if expected_case["kind"] == "direct_altitude_oracle_comparison":
            direct_differences.append(
                _verify_direct_case(
                    case_dir,
                    result,
                    expected_case,
                    spec,
                    profile_receipt,
                )
            )
        else:
            _verify_mystic_case(
                case_dir,
                result,
                expected_case,
                profile_receipt,
            )

    maximum_differences = {
        field: max(receipt[field] for receipt in direct_differences)
        for field in (
            "normalized_direct_irradiance_edir_over_e0",
            "direct_spectral_transmission",
            "extinction_magnitude",
        )
    }
    recorded_maximum = manifest.get(
        "direct_comparison_maximum_absolute_differences"
    )
    if not isinstance(recorded_maximum, dict) or any(
        not math.isclose(
            maximum_differences[field],
            float(recorded_maximum.get(field, math.nan)),
            rel_tol=0.0,
            abs_tol=1e-18,
        )
        for field in maximum_differences
    ):
        raise ValidationError("artifact maximum-difference receipt differs")

    _verify_byte_identity(
        artifact_root,
        manifest.get("sea_level_source_vs_truncated_control"),
        expected_original="mystic_source_site_0000m_control",
        expected_comparison="mystic_truncated_site_0000m",
        label="sea-level source/truncated control",
    )
    repeat_site = spec["mystic_elevated_smoke_profile"][
        "exact_repeat_site_altitude_m"
    ]
    repeat_token = _site_token(repeat_site)
    _verify_byte_identity(
        artifact_root,
        manifest.get("fixed_seed_repeat_check"),
        expected_original=f"mystic_truncated_site_{repeat_token}",
        expected_comparison=f"mystic_truncated_site_{repeat_token}_repeat",
        label="fixed-seed elevated-site repeat",
    )

    allowed_root_entries = {
        "artifact-manifest.json",
        "profiles",
        *expected_cases,
    }
    actual_root_entries = {path.name for path in artifact_root.iterdir()}
    if actual_root_entries != allowed_root_entries:
        raise ValidationError("artifact root contains an unowned entry")

    return {
        "manifest_sha256": manifest_sha256,
        "profile_count": manifest["profile_count"],
        "direct_comparison_case_count": len(direct_cases),
        "mystic_case_count": len(mystic_cases),
        "case_count": len(expected_cases),
        "all_files_bound": True,
        "direct_oracle_comparisons_within_tolerance": True,
        "sea_level_control_byte_identical": True,
        "fixed_seed_repeat_byte_identical": True,
        "network_dependency": False,
        "runtime_dependency": False,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Phase 1 elevated-site reference-lab artifact."
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
