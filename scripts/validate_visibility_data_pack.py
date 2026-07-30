#!/usr/bin/env python3
"""Independently validate a caller-supplied visibility data-pack directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPATIBILITY_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_heliacal_visibility_data_pack_compatibility_v1.json"
)
MANIFEST_NAME = "manifest.json"
MANIFEST_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-manifest/v1"
)
COMPATIBILITY_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-compatibility/v1"
)
AXES_SCHEMA = "moira.physical-heliacal-visibility-data-pack-axes/v1"
ERROR_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-error-envelope/v1"
)
PROVENANCE_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-provenance/v1"
)
EXPECTED_FILE_ROLES = {
    "axes",
    "photopic_luminance",
    "scotopic_luminance",
    "photopic_relative_standard_error",
    "scotopic_relative_standard_error",
    "direct_extinction",
    "error_envelope",
    "provenance",
    "notice",
    "readme",
    "checksums",
}


class VisibilityDataPackValidationError(ValueError):
    """Raised when a data pack is missing, corrupt, or incompatible."""


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisibilityDataPackValidationError(
            f"invalid {label}: {path}"
        ) from exc


def _canonical_object(path: Path, label: str) -> dict[str, Any]:
    value = _load_json(path, label)
    if not isinstance(value, dict):
        raise VisibilityDataPackValidationError(f"{label} must be an object")
    if path.read_bytes() != _canonical_json_bytes(value):
        raise VisibilityDataPackValidationError(
            f"{label} serialization is not canonical"
        )
    return value


def _load_compatibility(path: Path) -> dict[str, Any]:
    value = _load_json(path, "compatibility contract")
    if not isinstance(value, dict):
        raise VisibilityDataPackValidationError(
            "compatibility contract must be an object"
        )
    runtime = value.get("runtime_boundary")
    if (
        value.get("schema") != COMPATIBILITY_SCHEMA
        or value.get("status") != "phase1_metadata_contract_not_engine_loader"
        or value.get("supported_manifest_schemas") != [MANIFEST_SCHEMA]
        or value.get("supported_pack_id")
        != "moira-physical-heliacal-visibility"
        or value.get("supported_pack_major_versions") != [1]
        or value.get("supported_table_format_ids")
        != ["regular-grid-ieee754-binary32-le-v1"]
        or value.get("radiance_reference")
        != {
            "spectral_importance_reference_wavelength_nm": 531.0,
            "shape_normalization_wavelength_nm": 531.0,
            "absolute_anchor_wavelength_nm": 531.0,
            "selection": (
                "training_diagnostic_balanced_photopic_scotopic_"
                "relative_standard_error"
            ),
        }
        or not isinstance(runtime, dict)
        or runtime.get("caller_supplied_path_required") is not True
        or runtime.get("automatic_download_allowed") is not False
        or runtime.get("network_allowed") is not False
    ):
        raise VisibilityDataPackValidationError(
            "compatibility contract differs"
        )
    return value


def _safe_payload_path(root: Path, raw: Any) -> Path:
    if not isinstance(raw, str):
        raise VisibilityDataPackValidationError(
            "payload receipt path is invalid"
        )
    posix = PurePosixPath(raw)
    if (
        posix.is_absolute()
        or len(posix.parts) != 1
        or ".." in posix.parts
        or raw in {"", ".", MANIFEST_NAME}
    ):
        raise VisibilityDataPackValidationError(
            f"unsafe payload receipt path: {raw!r}"
        )
    return root / raw


def _verify_payloads(
    root: Path, manifest: dict[str, Any]
) -> dict[str, Path]:
    receipts = manifest.get("payload_files")
    if (
        not isinstance(receipts, list)
        or manifest.get("payload_file_count") != len(receipts)
    ):
        raise VisibilityDataPackValidationError(
            "payload receipt inventory differs"
        )
    paths: dict[str, Path] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise VisibilityDataPackValidationError(
                "payload receipt must be an object"
            )
        raw = receipt.get("path")
        path = _safe_payload_path(root, raw)
        if raw in paths:
            raise VisibilityDataPackValidationError(
                "duplicate payload receipt path"
            )
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != receipt.get("bytes")
            or _sha256_file(path) != receipt.get("sha256")
        ):
            raise VisibilityDataPackValidationError(
                f"payload receipt differs: {raw}"
            )
        paths[raw] = path
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    expected = {MANIFEST_NAME, *paths}
    if actual != expected:
        raise VisibilityDataPackValidationError(
            "data-pack file inventory differs: "
            f"missing={sorted(expected - actual)} "
            f"unexpected={sorted(actual - expected)}"
        )
    unexpected_directories = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_dir()
    ]
    if unexpected_directories:
        raise VisibilityDataPackValidationError(
            "data-pack directory inventory differs: "
            f"unexpected={sorted(unexpected_directories)}"
        )
    if root.is_symlink() or any(path.is_symlink() for path in root.rglob("*")):
        raise VisibilityDataPackValidationError(
            "data-pack path contains a symlink"
        )
    return paths


def _role_paths(
    root: Path, manifest: dict[str, Any], payloads: dict[str, Path]
) -> dict[str, Path]:
    roles = manifest.get("file_roles")
    if (
        not isinstance(roles, dict)
        or set(roles) != EXPECTED_FILE_ROLES
        or len(set(roles.values())) != len(roles)
    ):
        raise VisibilityDataPackValidationError("file-role inventory differs")
    result: dict[str, Path] = {}
    for role, raw in roles.items():
        path = _safe_payload_path(root, raw)
        if raw not in payloads:
            raise VisibilityDataPackValidationError(
                f"file role is not receipted: {role}"
            )
        result[role] = path
    return result


def _decode_f32(path: Path, count: int, label: str) -> list[float]:
    expected_bytes = count * 4
    data = path.read_bytes()
    if len(data) != expected_bytes:
        raise VisibilityDataPackValidationError(
            f"{label} byte count differs"
        )
    values = list(struct.unpack(f"<{count}f", data))
    if any(not math.isfinite(value) for value in values):
        raise VisibilityDataPackValidationError(
            f"{label} contains a nonfinite value"
        )
    if struct.pack(f"<{count}f", *values) != data:
        raise VisibilityDataPackValidationError(
            f"{label} is not canonical little-endian binary32"
        )
    return values


def _strict_axis(raw: Any, label: str) -> list[float]:
    if not isinstance(raw, list) or len(raw) < 2:
        raise VisibilityDataPackValidationError(f"{label} is invalid")
    values = [float(value) for value in raw]
    if any(
        not math.isfinite(value)
        or (index and value <= values[index - 1])
        for index, value in enumerate(values)
    ):
        raise VisibilityDataPackValidationError(
            f"{label} must be finite and strictly increasing"
        )
    return values


def _validate_axes(
    path: Path,
    manifest: dict[str, Any],
) -> tuple[int, int, dict[str, Any]]:
    axes = _canonical_object(path, "axes")
    radiance = axes.get("radiance")
    direct = axes.get("direct_extinction")
    compatibility_radiance = manifest["interpolation"]["radiance"]
    if (
        axes.get("schema") != AXES_SCHEMA
        or not isinstance(radiance, dict)
        or not isinstance(direct, dict)
        or radiance.get("coordinate_order")
        != compatibility_radiance["coordinate_order"]
        or radiance.get("linearization_order")
        != compatibility_radiance["linearization_order"]
        or direct.get("linearization_order")
        != "row_major_target_altitude_then_spectral_bin_fastest"
    ):
        raise VisibilityDataPackValidationError("axes contract differs")
    axis_map = radiance.get("axes")
    if not isinstance(axis_map, dict):
        raise VisibilityDataPackValidationError(
            "radiance axis map is missing"
        )
    radiance_axes = [
        _strict_axis(axis_map.get(name), name)
        for name in radiance["coordinate_order"]
    ]
    radiance_count = math.prod(len(values) for values in radiance_axes)
    spectral = direct.get("spectral_bins")
    target_axis = _strict_axis(
        direct.get("target_true_altitude_deg"),
        "direct target altitude",
    )
    if (
        radiance.get("value_count") != radiance_count
        or not isinstance(spectral, dict)
        or spectral.get("coordinate") != "bin_start_vacuum_nm"
        or not isinstance(spectral.get("count"), int)
        or spectral["count"] <= 0
        or not math.isfinite(float(spectral.get("start_nm")))
        or not math.isfinite(float(spectral.get("width_nm")))
        or float(spectral["width_nm"]) <= 0.0
    ):
        raise VisibilityDataPackValidationError(
            "axis dimensions differ"
        )
    direct_count = len(target_axis) * spectral["count"]
    if direct.get("value_count") != direct_count:
        raise VisibilityDataPackValidationError(
            "direct table value count differs"
        )
    domain = manifest.get("effective_domain")
    if (
        not isinstance(domain, dict)
        or domain.get("solar_center_altitude_deg")
        != [radiance_axes[0][0], radiance_axes[0][-1]]
        or domain.get("target_true_altitude_deg")
        != [radiance_axes[1][0], radiance_axes[1][-1]]
        or domain.get("relative_solar_azimuth_deg")
        != [radiance_axes[2][0], radiance_axes[2][-1]]
        or domain.get("no_extrapolation") is not True
        or domain.get("outside_domain") != "typed_not_evaluable"
    ):
        raise VisibilityDataPackValidationError(
            "effective domain and axes differ"
        )
    return radiance_count, direct_count, axes


def _validate_checksums(
    roles: dict[str, Path], payloads: dict[str, Path]
) -> None:
    checksums_path = roles["checksums"]
    expected = "\n".join(
        f"{_sha256_file(path)}  {name}"
        for name, path in sorted(payloads.items())
        if path != checksums_path
    ) + "\n"
    try:
        actual = checksums_path.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise VisibilityDataPackValidationError(
            "checksums file is invalid"
        ) from exc
    if actual != expected:
        raise VisibilityDataPackValidationError(
            "checksums file differs"
        )


def _validate_error_envelope(path: Path) -> dict[str, Any]:
    envelope = _canonical_object(path, "error envelope")
    errors = envelope.get("error_summaries")
    diagnostic = envelope.get("diagnostic_contract")
    storage = envelope.get("storage_analysis")
    downstream = envelope.get("downstream_error_contract")
    expected_errors = {
        "monochromatic_reference",
        "photopic_response",
        "scotopic_response",
        "direct_extinction_1nm",
    }
    if (
        envelope.get("schema") != ERROR_SCHEMA
        or envelope.get("accepted") is not True
        or not isinstance(errors, dict)
        or set(errors) != expected_errors
        or not isinstance(diagnostic, dict)
        or diagnostic.get("monochromatic_reference", {}).get(
            "admission_gate"
        )
        is not False
        or diagnostic.get("monochromatic_reference", {}).get(
            "surface_shipped_in_data_pack"
        )
        is not False
        or diagnostic.get("monochromatic_reference", {}).get(
            "surface_used_by_runtime_interpolation"
        )
        is not False
        or diagnostic.get("monochromatic_reference", {}).get("role")
        != (
            "reported_intermediate_diagnostic_not_artifact_"
            "admission_gate"
        )
        or not isinstance(storage, dict)
        or storage.get("selected_representation")
        != "little_endian_ieee754_binary32"
        or float(storage.get("float32_maximum_error_mag", math.inf))
        > 0.00001
        or float(storage.get("quantized_maximum_error_mag", math.inf))
        > 0.0002
        or not isinstance(downstream, dict)
        or downstream.get("limiting_magnitude_propagation_owner")
        != "phase2_single_epoch_truth"
        or downstream.get("event_time_propagation_owner")
        != "phase3_event_solver"
        or downstream.get(
            "phase1_does_not_fabricate_downstream_derivatives"
        )
        is not True
    ):
        raise VisibilityDataPackValidationError(
            "error-envelope contract differs"
        )
    for name, summary in errors.items():
        if (
            not isinstance(summary, dict)
            or int(summary.get("sample_count", 0)) <= 0
            or not math.isfinite(
                float(summary.get("maximum_error_mag", math.nan))
            )
            or not math.isfinite(
                float(summary.get("p95_error_mag", math.nan))
            )
            or float(summary["maximum_error_mag"])
            < float(summary["p95_error_mag"])
        ):
            raise VisibilityDataPackValidationError(
                f"invalid error summary: {name}"
            )
    return envelope


def _validate_provenance(
    path: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    provenance = _canonical_object(path, "provenance")
    source = provenance.get("source_artifact")
    scientific = provenance.get("scientific_sources")
    excluded = provenance.get("excluded_source_files")
    declared = manifest.get("source_artifact")
    if (
        provenance.get("schema") != PROVENANCE_SCHEMA
        or not isinstance(source, dict)
        or not isinstance(scientific, dict)
        or not isinstance(declared, dict)
        or source.get("spec_id") != declared.get("spec_id")
        or source.get("manifest") != declared.get("manifest")
        or source.get("summary") != declared.get("summary")
        or scientific.get("libRadtran", {}).get("version") != "2.0.6"
        or scientific.get("CIE_photopic", {}).get("dataset_doi")
        != "10.25039/CIE.DS.dktna2s3"
        or scientific.get("CIE_scotopic", {}).get("dataset_doi")
        != "10.25039/CIE.DS.gr6w4b5g"
        or excluded
        != [
            "CIE_source_tables",
            "libRadtran_binary",
            "libRadtran_profiles",
            "libRadtran_source",
            "REPTRAN_files",
        ]
    ):
        raise VisibilityDataPackValidationError(
            "provenance contract differs"
        )
    return provenance


def validate_data_pack(
    pack_path: Path,
    *,
    compatibility_path: Path = DEFAULT_COMPATIBILITY_PATH,
) -> dict[str, Any]:
    if pack_path.is_symlink():
        raise VisibilityDataPackValidationError(
            "caller-supplied data-pack path must not be a symlink"
        )
    pack_path = pack_path.resolve()
    if not pack_path.is_dir():
        raise VisibilityDataPackValidationError(
            f"caller-supplied data-pack path is missing: {pack_path}"
        )
    compatibility_path = compatibility_path.resolve()
    compatibility = _load_compatibility(compatibility_path)
    manifest_path = pack_path / MANIFEST_NAME
    if not manifest_path.is_file():
        raise VisibilityDataPackValidationError(
            "data-pack manifest is missing"
        )
    manifest = _canonical_object(manifest_path, "manifest")
    version_match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(manifest.get("version")))
    compatibility_receipt = manifest.get("compatibility_contract")
    if (
        manifest.get("schema") not in compatibility["supported_manifest_schemas"]
        or manifest.get("status") != "complete_immutable_data_pack"
        or manifest.get("pack_id") != compatibility["supported_pack_id"]
        or version_match is None
        or int(version_match.group(1))
        not in compatibility["supported_pack_major_versions"]
        or manifest.get("compatibility_id")
        != compatibility["compatibility_id"]
        or manifest.get("table_format_id")
        not in compatibility["supported_table_format_ids"]
        or manifest.get("composite_model_id")
        not in compatibility["supported_composite_model_ids"]
        or manifest.get("license") != "CC-BY-SA-4.0"
        or re.fullmatch(
            r"[0-9a-f]{64}",
            str(manifest.get("generation_fingerprint", "")),
        )
        is None
        or manifest.get("capabilities")
        != compatibility["required_capabilities"]
        or manifest.get("binary_representation")
        != compatibility["binary_representation"]
        or manifest.get("interpolation")
        != {
            "radiance": compatibility["radiance_interpolation"],
            "direct_extinction": compatibility[
                "direct_extinction_interpolation"
            ],
        }
        or manifest.get("radiance_reference")
        != compatibility["radiance_reference"]
        or not isinstance(compatibility_receipt, dict)
        or compatibility_receipt.get("bytes")
        != compatibility_path.stat().st_size
        or compatibility_receipt.get("sha256")
        != _sha256_file(compatibility_path)
        or manifest.get("root_manifest_receipt_owner")
        != "source_controlled_phase1_closure_checkpoint"
    ):
        raise VisibilityDataPackValidationError(
            "data pack is incompatible with this validator"
        )
    deep = manifest.get("deep_twilight_law")
    expected_deep = compatibility["deep_twilight_law"]
    if (
        not isinstance(deep, dict)
        or deep.get("table_minimum_solar_center_altitude_deg")
        != expected_deep["minimum_solar_center_altitude_deg"]
        or deep.get("solar_altitude_below_table")
        != "not_evaluable_for_modeled_twilight_background"
        or deep.get("reason")
        != expected_deep["below_minimum_modeled_twilight_reason"]
        or deep.get("monte_carlo_non_detection_is_zero") is not False
    ):
        raise VisibilityDataPackValidationError(
            "deep-twilight law differs"
        )
    payloads = _verify_payloads(pack_path, manifest)
    roles = _role_paths(pack_path, manifest, payloads)
    _validate_checksums(roles, payloads)
    radiance_count, direct_count, axes = _validate_axes(
        roles["axes"], manifest
    )
    photopic = _decode_f32(
        roles["photopic_luminance"],
        radiance_count,
        "photopic luminance",
    )
    scotopic = _decode_f32(
        roles["scotopic_luminance"],
        radiance_count,
        "scotopic luminance",
    )
    photopic_error = _decode_f32(
        roles["photopic_relative_standard_error"],
        radiance_count,
        "photopic relative standard error",
    )
    scotopic_error = _decode_f32(
        roles["scotopic_relative_standard_error"],
        radiance_count,
        "scotopic relative standard error",
    )
    direct = _decode_f32(
        roles["direct_extinction"],
        direct_count,
        "direct extinction",
    )
    if (
        any(value <= 0.0 for value in photopic)
        or any(value <= 0.0 for value in scotopic)
        or any(not 0.0 <= value <= 1.0 for value in photopic_error)
        or any(not 0.0 <= value <= 1.0 for value in scotopic_error)
        or any(value < 0.0 for value in direct)
    ):
        raise VisibilityDataPackValidationError(
            "data table physical bounds differ"
        )
    envelope = _validate_error_envelope(roles["error_envelope"])
    provenance = _validate_provenance(roles["provenance"], manifest)
    try:
        notice = roles["notice"].read_text(encoding="utf-8")
        readme = roles["readme"].read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise VisibilityDataPackValidationError(
            "notice or readme is invalid"
        ) from exc
    required_notice_fragments = (
        "Creative Commons",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        "10.25039/CIE.DS.dktna2s3",
        "10.25039/CIE.DS.gr6w4b5g",
        "libRadtran 2.0.6",
        "No libRadtran source",
    )
    if any(fragment not in notice for fragment in required_notice_fragments):
        raise VisibilityDataPackValidationError(
            "licensing notice is incomplete"
        )
    if (
        "explicit caller-supplied directory path" not in readme
        or "No component may download" not in readme
    ):
        raise VisibilityDataPackValidationError(
            "runtime readme boundary is incomplete"
        )
    return {
        "pack": str(pack_path),
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "compatibility_id": manifest["compatibility_id"],
        "manifest_sha256": _sha256_file(manifest_path),
        "generation_fingerprint": manifest["generation_fingerprint"],
        "payload_file_count": len(payloads),
        "radiance_value_count_per_response": radiance_count,
        "direct_extinction_value_count": direct_count,
        "maximum_error_summaries": {
            name: summary["maximum_error_mag"]
            for name, summary in envelope["error_summaries"].items()
        },
        "source_artifact_manifest_sha256": provenance["source_artifact"][
            "manifest"
        ]["sha256"],
        "axes": axes,
        "network_accessed": False,
        "validated": True,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an explicit caller-supplied physical heliacal "
            "visibility data-pack directory."
        )
    )
    parser.add_argument("pack", type=Path)
    parser.add_argument(
        "--compatibility",
        type=Path,
        default=DEFAULT_COMPATIBILITY_PATH,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = validate_data_pack(
            args.pack,
            compatibility_path=args.compatibility,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except VisibilityDataPackValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
