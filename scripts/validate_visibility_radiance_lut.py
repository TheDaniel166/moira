"""Validate an offline Phase 1 visibility-reference-lab artifact.

The validator is standard-library-only. It verifies the root manifest, every
bound case receipt, every per-file checksum, fixed-seed repeat evidence, and
the boundary that forbids libRadtran or CIE source data inside this research
artifact.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_visibility_radiance_lut import (
    ARTIFACT_SCHEMA,
    CALCULATION_DIRECT_TRANSMISSION,
    CALCULATION_DIRECTIONAL_RADIANCE,
    CASE_SCHEMA,
    DEFAULT_SPEC_PATH,
    VisibilityLabError,
    expected_case_files,
    expand_profile,
    load_spec,
    profile_model_id,
    sha256_file,
)

REPEAT_PROFILES = frozenset({"convergence", "direct_transmission_smoke"})


def _safe_relative_path(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise VisibilityLabError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise VisibilityLabError(f"{label} is not a safe relative path")
    return path


def _verify_file(root: Path, receipt: dict[str, Any], label: str) -> Path:
    relative = _safe_relative_path(receipt.get("path"), f"{label}.path")
    path = root.joinpath(*relative.parts)
    if not path.is_file() or path.is_symlink():
        raise VisibilityLabError(f"{label} is missing, not regular, or a symlink: {path}")
    expected_bytes = receipt.get("bytes")
    expected_sha256 = receipt.get("sha256")
    if not isinstance(expected_bytes, int) or expected_bytes < 0:
        raise VisibilityLabError(f"{label}.bytes is invalid")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise VisibilityLabError(f"{label}.sha256 is invalid")
    if path.stat().st_size != expected_bytes:
        raise VisibilityLabError(f"{label} byte count mismatch: {path}")
    if sha256_file(path) != expected_sha256:
        raise VisibilityLabError(f"{label} SHA-256 mismatch: {path}")
    return path


def _require_nonnegative_finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)):
        raise VisibilityLabError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise VisibilityLabError(f"{label} must be finite and non-negative")
    return number


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise VisibilityLabError(f"{label} must be a lowercase SHA-256")
    return value


def _validate_generator_receipt(
    manifest: dict[str, Any],
    spec: dict[str, Any],
) -> None:
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise VisibilityLabError("artifact generator receipt is missing")
    archive = generator.get("source_archive")
    if not isinstance(archive, dict):
        raise VisibilityLabError("source archive receipt is missing")
    if archive.get("bytes") != spec["source"]["archive_bytes"]:
        raise VisibilityLabError("source archive byte receipt differs from the source lock")
    if archive.get("sha256") != spec["source"]["archive_sha256"]:
        raise VisibilityLabError("source archive hash receipt differs from the source lock")
    if generator.get("source_archive_expected_url") != spec["source"]["archive_url"]:
        raise VisibilityLabError("source archive URL receipt differs from the source lock")
    version = generator.get("uvspec_version")
    if not isinstance(version, str) or "2.0.6-MYSTIC" not in version:
        raise VisibilityLabError("generator does not identify libRadtran 2.0.6-MYSTIC")
    _validate_sha256(generator.get("uvspec_sha256"), "generator.uvspec_sha256")
    configure_options = generator.get("configure_options")
    if not isinstance(configure_options, str):
        raise VisibilityLabError("generator.configure_options must be a string")
    required_configure_tokens = (
        "CC=gcc",
        "CFLAGS=-O2",
        "CXX=g++",
        "CXXFLAGS=-O2",
        "F77=gfortran",
        "FFLAGS=-O2",
    )
    if any(token not in configure_options for token in required_configure_tokens):
        raise VisibilityLabError("generator.configure_options is incomplete")
    if generator.get("build_capabilities") != {
        "mystic": True,
        "mystic_3d": False,
        "gsl": True,
        "netcdf4": True,
        "vroom_exercised_by_cases": True,
    }:
        raise VisibilityLabError("generator build-capability receipt is unsupported")
    build_receipts = generator.get("build_files")
    if not isinstance(build_receipts, list):
        raise VisibilityLabError("generator build-file receipts are missing")
    expected_build_files = {"Makeconf", "config.log", "config.status"}
    received_build_files: set[str] = set()
    for index, receipt in enumerate(build_receipts):
        if not isinstance(receipt, dict):
            raise VisibilityLabError("generator build-file receipt must be an object")
        path = _safe_relative_path(receipt.get("path"), f"build_files[{index}]")
        if len(path.parts) != 1 or path.name not in expected_build_files:
            raise VisibilityLabError("generator build-file receipt is not canonical")
        if path.name in received_build_files:
            raise VisibilityLabError("duplicate generator build-file receipt")
        received_build_files.add(path.name)
        if not isinstance(receipt.get("bytes"), int) or receipt["bytes"] <= 0:
            raise VisibilityLabError("generator build-file byte receipt is invalid")
        _validate_sha256(receipt.get("sha256"), "build file SHA-256")
    if received_build_files != expected_build_files:
        raise VisibilityLabError("generator build-file inventory is incomplete")

    required_paths = {spec["source_datasets"]["solar_spectrum"]}
    required_paths.update(spec["source_datasets"]["atmosphere_files"].values())
    dataset_receipts = generator.get("source_datasets")
    if not isinstance(dataset_receipts, list):
        raise VisibilityLabError("generator source-dataset receipts are missing")
    received_paths: set[str] = set()
    for index, receipt in enumerate(dataset_receipts):
        if not isinstance(receipt, dict):
            raise VisibilityLabError("generator source-dataset receipt must be an object")
        path = _safe_relative_path(receipt.get("path"), f"source_datasets[{index}]")
        if path.as_posix() in received_paths:
            raise VisibilityLabError("duplicate generator source-dataset receipt")
        received_paths.add(path.as_posix())
        if not isinstance(receipt.get("bytes"), int) or receipt["bytes"] <= 0:
            raise VisibilityLabError("generator source-dataset byte receipt is invalid")
        _validate_sha256(receipt.get("sha256"), "source dataset SHA-256")
    if received_paths != required_paths:
        raise VisibilityLabError("generator source-dataset inventory differs from the spec")

    required_trees = set(spec["source_datasets"]["data_trees"].values())
    tree_receipts = generator.get("source_data_trees")
    if not isinstance(tree_receipts, list):
        raise VisibilityLabError("generator source-data-tree receipts are missing")
    received_trees: set[str] = set()
    for index, receipt in enumerate(tree_receipts):
        if not isinstance(receipt, dict):
            raise VisibilityLabError("generator source-data-tree receipt must be an object")
        path = _safe_relative_path(receipt.get("path"), f"source_data_trees[{index}]")
        if path.as_posix() in received_trees:
            raise VisibilityLabError("duplicate generator source-data-tree receipt")
        received_trees.add(path.as_posix())
        if not isinstance(receipt.get("file_count"), int) or receipt["file_count"] <= 0:
            raise VisibilityLabError("generator source-data-tree file count is invalid")
        if not isinstance(receipt.get("bytes"), int) or receipt["bytes"] <= 0:
            raise VisibilityLabError("generator source-data-tree byte receipt is invalid")
        _validate_sha256(receipt.get("tree_sha256"), "source data tree SHA-256")
        if receipt.get("tree_hash_law") != (
            "sha256(relative_path_nul_bytes_nul_file_sha256_lf)"
        ):
            raise VisibilityLabError("generator source-data-tree hash law is unsupported")
    if received_trees != required_trees:
        raise VisibilityLabError("generator source-data-tree inventory differs from the spec")

    environment = manifest.get("environment")
    if not isinstance(environment, dict) or not isinstance(
        environment.get("platform"),
        str,
    ):
        raise VisibilityLabError("artifact environment receipt is missing")
    if not isinstance(environment.get("python"), str):
        raise VisibilityLabError("artifact Python receipt is missing")
    tools = environment.get("tools")
    if not isinstance(tools, dict):
        raise VisibilityLabError("artifact toolchain receipt is missing")
    for required_tool in ("gcc", "g++", "gfortran", "make", "flex", "netcdf", "gsl"):
        if not isinstance(tools.get(required_tool), str) or not tools[required_tool]:
            raise VisibilityLabError(f"artifact toolchain omits {required_tool}")


def _validate_tooling_receipt(manifest: dict[str, Any]) -> None:
    tooling = manifest.get("tooling")
    if not isinstance(tooling, dict):
        raise VisibilityLabError("artifact tooling receipt is missing")
    expected = {
        "builder": Path(__file__).resolve().with_name(
            "build_visibility_radiance_lut.py"
        ),
        "validator": Path(__file__).resolve(),
    }
    repo_root = Path(__file__).resolve().parents[1]
    for role, path in expected.items():
        receipt = tooling.get(role)
        if not isinstance(receipt, dict):
            raise VisibilityLabError(f"artifact tooling receipt omits {role}")
        if receipt.get("path") != path.relative_to(repo_root).as_posix():
            raise VisibilityLabError(f"artifact {role} path receipt is not canonical")
        if receipt.get("bytes") != path.stat().st_size:
            raise VisibilityLabError(f"artifact {role} byte receipt is stale")
        if receipt.get("sha256") != sha256_file(path):
            raise VisibilityLabError(f"artifact {role} SHA-256 receipt is stale")


def _verify_case(
    artifact_root: Path,
    receipt: dict[str, Any],
) -> tuple[dict[str, Any], set[str]]:
    case_id = receipt.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise VisibilityLabError("case receipt has an invalid case_id")
    result_receipt = receipt.get("case_result")
    if not isinstance(result_receipt, dict):
        raise VisibilityLabError(f"{case_id} is missing its case-result receipt")
    expected_result_path = f"{case_id}/case-result.json"
    if result_receipt.get("path") != expected_result_path:
        raise VisibilityLabError(f"{case_id} case-result path is not canonical")
    result_path = _verify_file(
        artifact_root,
        result_receipt,
        f"cases[{case_id}].case_result",
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("schema") != CASE_SCHEMA:
        raise VisibilityLabError(f"{case_id} uses an unsupported case schema")
    case = result.get("case")
    if not isinstance(case, dict) or case.get("case_id") != case_id:
        raise VisibilityLabError(f"{case_id} case identity mismatch")
    if result.get("result") != receipt.get("result"):
        raise VisibilityLabError(f"{case_id} summary differs from case-result.json")

    summary = result["result"]
    wavelength = _require_nonnegative_finite(summary.get("wavelength_nm"), "wavelength")
    if wavelength != float(case["wavelength_nm"]):
        raise VisibilityLabError(f"{case_id} wavelength differs from its input")
    calculation_kind = case.get("calculation_kind")
    if calculation_kind == CALCULATION_DIRECTIONAL_RADIANCE:
        viewing_zenith = _require_nonnegative_finite(
            summary.get("viewing_zenith_deg"),
            "viewing zenith",
        )
        viewing_azimuth = _require_nonnegative_finite(
            summary.get("viewing_azimuth_deg"),
            "viewing azimuth",
        )
        if not math.isclose(
            viewing_zenith,
            90.0 + float(case["target_true_altitude_deg"]),
            abs_tol=1e-6,
        ):
            raise VisibilityLabError(f"{case_id} viewing zenith differs from its input")
        if not math.isclose(
            viewing_azimuth % 360.0,
            float(case["relative_solar_azimuth_deg"]) % 360.0,
            abs_tol=1e-6,
        ):
            raise VisibilityLabError(f"{case_id} viewing azimuth differs from its input")
        radiance = _require_nonnegative_finite(
            summary.get("escape_spectral_radiance_mw_m2_nm_sr"),
            "radiance",
        )
        reported_std = _require_nonnegative_finite(
            summary.get("reported_standard_deviation_mw_m2_nm_sr"),
            "reported standard deviation",
        )
        expected_relative = reported_std / radiance if radiance > 0.0 else None
        if summary.get("reported_relative_standard_deviation") != expected_relative:
            raise VisibilityLabError(
                f"{case_id} relative standard deviation is inconsistent"
            )
    elif calculation_kind == CALCULATION_DIRECT_TRANSMISSION:
        target_altitude = _require_nonnegative_finite(
            summary.get("target_true_altitude_deg"),
            "target true altitude",
        )
        if target_altitude != float(case["target_true_altitude_deg"]):
            raise VisibilityLabError(f"{case_id} target altitude differs from its input")
        normalized_edir = _require_nonnegative_finite(
            summary.get("normalized_direct_irradiance_edir_over_e0"),
            "normalized direct irradiance",
        )
        projection = _require_nonnegative_finite(
            summary.get("geometric_projection_sin_altitude"),
            "geometric projection",
        )
        expected_projection = math.sin(math.radians(target_altitude))
        if normalized_edir <= 0.0 or not math.isclose(
            projection,
            expected_projection,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise VisibilityLabError(f"{case_id} direct-irradiance geometry is invalid")
        transmission = _require_nonnegative_finite(
            summary.get("direct_spectral_transmission"),
            "direct spectral transmission",
        )
        expected_transmission = normalized_edir / projection
        if not 0.0 < transmission <= 1.0 or not math.isclose(
            transmission,
            expected_transmission,
            rel_tol=1e-15,
            abs_tol=0.0,
        ):
            raise VisibilityLabError(f"{case_id} direct transmission is inconsistent")
        extinction = _require_nonnegative_finite(
            summary.get("extinction_magnitude"),
            "extinction magnitude",
        )
        if not math.isclose(
            extinction,
            -2.5 * math.log10(transmission),
            rel_tol=1e-15,
            abs_tol=0.0,
        ):
            raise VisibilityLabError(f"{case_id} extinction magnitude is inconsistent")
    else:
        raise VisibilityLabError(
            f"{case_id} uses an unsupported calculation kind: {calculation_kind!r}"
        )

    files = result.get("files")
    if not isinstance(files, list) or not files:
        raise VisibilityLabError(f"{case_id} has no bound files")
    seen: set[str] = set()
    expected_files = expected_case_files(case)
    for file_receipt in files:
        if not isinstance(file_receipt, dict):
            raise VisibilityLabError(f"{case_id} contains an invalid file receipt")
        relative = _safe_relative_path(file_receipt.get("path"), f"{case_id}.file")
        if len(relative.parts) != 1 or relative.name not in expected_files:
            raise VisibilityLabError(
                f"{case_id} binds an unexpected lab artifact: {relative.as_posix()}"
            )
        if relative.name in seen:
            raise VisibilityLabError(f"{case_id} binds {relative.name} more than once")
        seen.add(relative.name)
        _verify_file(result_path.parent, file_receipt, f"{case_id}.{relative.name}")
    missing = expected_files - seen
    if missing:
        raise VisibilityLabError(
            f"{case_id} does not bind required files: {', '.join(sorted(missing))}"
        )
    bound_paths = {expected_result_path}
    bound_paths.update(f"{case_id}/{name}" for name in seen)
    return result, bound_paths


def _verify_fixed_seed_repeat(
    artifact_root: Path,
    manifest: dict[str, Any],
    cases_by_id: dict[str, dict[str, Any]],
) -> None:
    receipt = manifest.get("fixed_seed_repeat_check")
    if manifest.get("profile") not in REPEAT_PROFILES:
        if receipt is not None:
            raise VisibilityLabError("artifact profile must not claim a repeat check")
        return
    if not isinstance(receipt, dict):
        raise VisibilityLabError("convergence artifact is missing fixed-seed repeat evidence")
    original_id = receipt.get("original_case_id")
    repeat_id = receipt.get("repeat_case_id")
    if original_id not in cases_by_id or repeat_id not in cases_by_id:
        raise VisibilityLabError("fixed-seed repeat references an unknown case")
    files = receipt.get("byte_identical_files")
    expected_files = sorted(expected_case_files(cases_by_id[repeat_id]["case"]))
    if files != expected_files:
        raise VisibilityLabError("fixed-seed repeat file list is not canonical")
    for filename in files:
        original = artifact_root / original_id / filename
        repeat = artifact_root / repeat_id / filename
        if original.read_bytes() != repeat.read_bytes():
            raise VisibilityLabError(
                f"fixed-seed repeat differs for {filename}: {original_id} vs {repeat_id}"
            )


def validate_artifact(
    artifact_root: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    manifest_path = artifact_root / "artifact-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise VisibilityLabError(f"artifact manifest not found: {manifest_path}")
    manifest_sha256 = sha256_file(manifest_path)
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256.lower()
    ):
        raise VisibilityLabError("artifact manifest SHA-256 does not match expectation")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise VisibilityLabError("unsupported artifact manifest schema")
    if manifest.get("artifact_status") != (
        "phase1_reference_lab_evidence_not_runtime_data_pack"
    ):
        raise VisibilityLabError("artifact status overclaims the Phase 1 evidence")
    if manifest.get("profile") not in {
        "convergence",
        "geometry_smoke",
        "direct_transmission_smoke",
    }:
        raise VisibilityLabError("artifact profile is not authorized")

    spec = load_spec(spec_path)
    spec_receipt = manifest.get("spec")
    if not isinstance(spec_receipt, dict):
        raise VisibilityLabError("artifact has no specification receipt")
    if spec_receipt.get("spec_id") != spec["spec_id"]:
        raise VisibilityLabError("artifact specification identity mismatch")
    if spec_receipt.get("sha256") != sha256_file(spec_path):
        raise VisibilityLabError("artifact specification SHA-256 mismatch")
    if manifest.get("model_id") != profile_model_id(spec, manifest["profile"]):
        raise VisibilityLabError("artifact model identity mismatch")
    if manifest.get("composite_model_id") != spec["composite_model_id"]:
        raise VisibilityLabError("artifact composite-model identity mismatch")
    if manifest.get("runtime_boundary") != spec["runtime_boundary"]:
        raise VisibilityLabError("artifact runtime boundary differs from the specification")
    _validate_tooling_receipt(manifest)
    _validate_generator_receipt(manifest, spec)

    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != manifest.get("case_count"):
        raise VisibilityLabError("artifact case count is inconsistent")
    expected_cases = {
        case["case_id"]: case for case in expand_profile(spec, manifest["profile"])
    }
    expected_case_count = len(expected_cases)
    if len(cases) != expected_case_count:
        raise VisibilityLabError("artifact does not contain the full authorized profile")

    cases_by_id: dict[str, dict[str, Any]] = {}
    bound_paths = {"artifact-manifest.json"}
    for receipt in cases:
        if not isinstance(receipt, dict):
            raise VisibilityLabError("artifact contains an invalid case receipt")
        result, case_paths = _verify_case(artifact_root, receipt)
        case_id = result["case"]["case_id"]
        if case_id in cases_by_id:
            raise VisibilityLabError(f"duplicate case ID: {case_id}")
        if case_id not in expected_cases or result["case"] != expected_cases[case_id]:
            raise VisibilityLabError(f"{case_id} differs from the authorized profile")
        cases_by_id[case_id] = result
        bound_paths.update(case_paths)
    if cases_by_id.keys() != expected_cases.keys():
        raise VisibilityLabError("artifact case inventory differs from the authorized profile")

    _verify_fixed_seed_repeat(artifact_root, manifest, cases_by_id)

    actual_files = {
        path.relative_to(artifact_root).as_posix()
        for path in artifact_root.rglob("*")
        if path.is_file()
    }
    if actual_files != bound_paths:
        unbound = sorted(actual_files - bound_paths)
        missing = sorted(bound_paths - actual_files)
        detail = []
        if unbound:
            detail.append("unbound=" + ",".join(unbound))
        if missing:
            detail.append("missing=" + ",".join(missing))
        raise VisibilityLabError("artifact file inventory mismatch: " + " ".join(detail))
    if any(path.is_symlink() for path in artifact_root.rglob("*")):
        raise VisibilityLabError("artifact must not contain symlinks")

    return {
        "manifest_sha256": manifest_sha256,
        "profile": manifest["profile"],
        "case_count": len(cases_by_id),
        "fixed_seed_repeat_verified": manifest["profile"] == "convergence",
        "exact_repeat_verified": manifest["profile"] in REPEAT_PROFILES,
        "all_files_bound": True,
        "runtime_dependency": False,
        "network_dependency": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args(argv)
    try:
        result = validate_artifact(
            args.artifact_root,
            spec_path=args.spec,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
    except (OSError, json.JSONDecodeError, VisibilityLabError) as exc:
        parser.exit(2, f"visibility reference lab validation: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
