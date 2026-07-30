#!/usr/bin/env python3
"""Build the separately distributed physical heliacal visibility data pack.

The builder consumes one independently validated Phase 1 reference artifact.
It copies only response-integrated numerical products, error envelopes, and
provenance.  It never imports libRadtran, opens a network connection, edits
the engine package, or downloads a missing input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "scripts" / "visibility_reference_lab"
DEFAULT_SPEC_PATH = LAB_ROOT / "phase1_visibility_data_pack_spec.json"
DEFAULT_COMPATIBILITY_PATH = (
    LAB_ROOT
    / "physical_heliacal_visibility_data_pack_compatibility_v1.json"
)
RADIANCE_VALIDATOR_PATH = (
    REPO_ROOT / "scripts" / "validate_visibility_radiance_response_probe.py"
)
PACK_VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_visibility_data_pack.py"
MANIFEST_NAME = "manifest.json"
SPEC_SCHEMA = "moira.physical-heliacal-visibility-data-pack-spec/v1"
COMPATIBILITY_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-compatibility/v1"
)
MANIFEST_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-manifest/v1"
)
SUMMARY_SCHEMA = "moira.visibility-radiance-response-summary/v1"


class VisibilityDataPackError(ValueError):
    """Raised when the visibility data pack cannot be built safely."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_receipt(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    receipt_path = (
        path.relative_to(relative_to).as_posix()
        if relative_to is not None
        else path.relative_to(REPO_ROOT).as_posix()
    )
    return {
        "path": receipt_path,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisibilityDataPackError(f"invalid {label}: {path}") from exc


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisibilityDataPackError(f"{label} must be an object")
    return value


def _load_compatibility(path: Path) -> dict[str, Any]:
    value = _require_dict(load_json(path, "compatibility contract"), "compatibility")
    runtime = _require_dict(value.get("runtime_boundary"), "runtime boundary")
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
        or runtime.get("caller_supplied_path_required") is not True
        or runtime.get("automatic_download_allowed") is not False
        or runtime.get("network_allowed") is not False
        or runtime.get("engine_loader_implementation_owner")
        != "phase2_single_epoch_truth"
    ):
        raise VisibilityDataPackError("compatibility contract differs")
    return value


def _load_spec(path: Path) -> dict[str, Any]:
    value = _require_dict(load_json(path, "data-pack specification"), "specification")
    runtime = _require_dict(value.get("runtime_boundary"), "runtime boundary")
    pack = _require_dict(value.get("pack"), "pack declaration")
    source = _require_dict(value.get("source_artifact"), "source artifact")
    checkpoint = _require_dict(
        source.get("checkpoint"),
        "source checkpoint",
    )
    checkpoint_relative = checkpoint.get("path")
    failed_predecessors = _require_dict(
        value.get("failed_predecessors"),
        "failed predecessors",
    )
    failed_notice_checkpoint = _require_dict(
        failed_predecessors.get("notice_checkpoint"),
        "failed notice checkpoint",
    )
    failed_notice_relative = failed_notice_checkpoint.get("path")
    direct = _require_dict(value.get("direct_table"), "direct table")
    if (
        value.get("schema") != SPEC_SCHEMA
        or value.get("status") != "phase1_data_pack_build_not_engine_runtime"
        or pack.get("pack_id") != "moira-physical-heliacal-visibility"
        or pack.get("version") != "1.0.0"
        or pack.get("manifest_schema") != MANIFEST_SCHEMA
        or pack.get("table_format_id")
        != "regular-grid-ieee754-binary32-le-v1"
        or source.get("spec_id")
        != "physical-heliacal-phase1-radiance-response-v9-2026-07-30"
        or not isinstance(checkpoint_relative, str)
        or Path(checkpoint_relative).is_absolute()
        or ".." in Path(checkpoint_relative).parts
        or not isinstance(failed_notice_relative, str)
        or Path(failed_notice_relative).is_absolute()
        or ".." in Path(failed_notice_relative).parts
        or direct.get("spectral_bin_start_nm") != 380.0
        or direct.get("spectral_bin_width_nm") != 1.0
        or direct.get("spectral_bin_count") != 400
        or len(direct.get("target_true_altitude_deg", [])) != 57
        or runtime.get("network_allowed") is not False
        or runtime.get("automatic_download_allowed") is not False
        or runtime.get("engine_package_mutation_allowed") is not False
        or runtime.get("engine_loader_in_scope") is not False
        or runtime.get("caller_supplied_output_path_required") is not True
        or runtime.get("source_artifact_must_validate_independently")
        is not True
        or runtime.get("libRadtran_or_REPTRAN_files_may_be_copied")
        is not False
        or runtime.get("CIE_source_tables_may_be_copied") is not False
        or runtime.get("generated_numerical_products_only") is not True
    ):
        raise VisibilityDataPackError("data-pack specification differs")
    _verify_receipt(
        REPO_ROOT / checkpoint_relative,
        checkpoint,
        "source checkpoint",
    )
    _verify_receipt(
        REPO_ROOT / failed_notice_relative,
        failed_notice_checkpoint,
        "failed notice checkpoint",
    )
    filenames = _require_dict(value.get("files"), "file inventory")
    expected_names = {
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
    if set(filenames) != expected_names or len(set(filenames.values())) != len(
        filenames
    ):
        raise VisibilityDataPackError("data-pack file inventory differs")
    for filename in filenames.values():
        if (
            not isinstance(filename, str)
            or Path(filename).name != filename
            or filename in {".", "..", MANIFEST_NAME}
        ):
            raise VisibilityDataPackError("unsafe data-pack filename")
    return value


def inspect_spec(
    spec_path: Path = DEFAULT_SPEC_PATH,
    compatibility_path: Path = DEFAULT_COMPATIBILITY_PATH,
) -> dict[str, Any]:
    spec = _load_spec(spec_path)
    compatibility = _load_compatibility(compatibility_path)
    return {
        "spec_id": spec["spec_id"],
        "pack": spec["pack"],
        "source_artifact": spec["source_artifact"],
        "failed_predecessors": spec["failed_predecessors"],
        "payload_file_count": len(spec["files"]),
        "compatibility_id": compatibility["compatibility_id"],
        "runtime_boundary": spec["runtime_boundary"],
    }


def _verify_receipt(path: Path, receipt: dict[str, Any], label: str) -> None:
    if (
        not path.is_file()
        or path.stat().st_size != receipt.get("bytes")
        or sha256_file(path) != receipt.get("sha256")
    ):
        raise VisibilityDataPackError(f"{label} receipt differs")


def _validate_source_artifact(
    source_artifact: Path,
    cie_root: Path,
    radiance_spec_path: Path,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    declaration = _require_dict(
        spec.get("source_artifact"), "source-artifact declaration"
    )
    manifest_path = source_artifact / "artifact-manifest.json"
    summary_path = source_artifact / "summary.json"
    _verify_receipt(
        manifest_path,
        _require_dict(declaration.get("manifest"), "source manifest receipt"),
        "source manifest",
    )
    _verify_receipt(
        summary_path,
        _require_dict(declaration.get("summary"), "source summary receipt"),
        "source summary",
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(RADIANCE_VALIDATOR_PATH),
            str(source_artifact),
            "--cie-root",
            str(cie_root),
            "--spec",
            str(radiance_spec_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise VisibilityDataPackError(
            f"source artifact independent validation failed: {detail}"
        )
    try:
        validation = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VisibilityDataPackError(
            "source artifact validator returned invalid JSON"
        ) from exc
    manifest = _require_dict(load_json(manifest_path, "source manifest"), "manifest")
    summary = _require_dict(load_json(summary_path, "source summary"), "summary")
    if (
        manifest.get("status")
        != "phase1_complete_reference_artifact_not_runtime_data_pack"
        or manifest.get("spec_id") != declaration.get("spec_id")
        or summary.get("schema") != SUMMARY_SCHEMA
        or summary.get("accepted") is not True
        or validation.get("validated") is not True
        or validation.get("manifest_sha256") != sha256_file(manifest_path)
    ):
        raise VisibilityDataPackError("source artifact contract differs")
    return manifest, summary, validation


def _f32_bytes(values: list[float], label: str) -> bytes:
    converted: list[float] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise VisibilityDataPackError(f"{label} contains a nonfinite value")
        converted.append(number)
    return struct.pack(f"<{len(converted)}f", *converted)


def _response_tables(
    summary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    axes = _require_dict(summary.get("radiance_axes"), "radiance axes")
    axis_names = (
        "solar_center_altitude_deg",
        "target_true_altitude_deg",
        "relative_solar_azimuth_deg",
    )
    axis_values = tuple(
        [float(value) for value in axes[name]] for name in axis_names
    )
    expected = [
        (solar, target, azimuth)
        for solar in axis_values[0]
        for target in axis_values[1]
        for azimuth in axis_values[2]
    ]
    rows = summary.get("response_training_table")
    if not isinstance(rows, list):
        raise VisibilityDataPackError("response training table is missing")
    by_point: dict[tuple[float, float, float], dict[str, Any]] = {}
    for raw in rows:
        row = _require_dict(raw, "response training row")
        key = tuple(float(row[name]) for name in axis_names)
        if key in by_point:
            raise VisibilityDataPackError("duplicate response training point")
        by_point[key] = row
    if set(by_point) != set(expected):
        raise VisibilityDataPackError("response training grid differs")
    products = {
        "photopic_luminance": [
            float(by_point[point]["photopic_luminance_cd_m2"])
            for point in expected
        ],
        "scotopic_luminance": [
            float(by_point[point]["scotopic_luminance_cd_m2"])
            for point in expected
        ],
        "photopic_relative_standard_error": [
            float(by_point[point]["photopic_relative_standard_error"])
            for point in expected
        ],
        "scotopic_relative_standard_error": [
            float(by_point[point]["scotopic_relative_standard_error"])
            for point in expected
        ],
    }
    if (
        any(value <= 0.0 for value in products["photopic_luminance"])
        or any(value <= 0.0 for value in products["scotopic_luminance"])
        or any(
            not 0.0 <= value <= 1.0
            for name in (
                "photopic_relative_standard_error",
                "scotopic_relative_standard_error",
            )
            for value in products[name]
        )
    ):
        raise VisibilityDataPackError("response table physical bounds differ")
    axes_payload = {
        "schema": "moira.physical-heliacal-visibility-data-pack-axes/v1",
        "radiance": {
            "coordinate_order": list(axis_names),
            "linearization_order": "row_major_last_axis_fastest",
            "axes": {name: list(values) for name, values in zip(axis_names, axis_values)},
            "value_count": len(expected),
        },
    }
    return axes_payload, products


def _direct_table(
    summary: dict[str, Any], spec: dict[str, Any]
) -> tuple[dict[str, Any], list[float]]:
    declaration = _require_dict(spec.get("direct_table"), "direct table")
    rows = summary.get("direct_training_table")
    if not isinstance(rows, list):
        raise VisibilityDataPackError("direct training table is missing")
    expected_altitudes = [
        float(value) for value in declaration["target_true_altitude_deg"]
    ]
    by_altitude: dict[float, list[float]] = {}
    for raw in rows:
        row = _require_dict(raw, "direct training row")
        altitude = float(row["target_true_altitude_deg"])
        if altitude in by_altitude:
            raise VisibilityDataPackError("duplicate direct training altitude")
        values = [float(value) for value in row["extinction_magnitude_1nm"]]
        by_altitude[altitude] = values
    bin_count = int(declaration["spectral_bin_count"])
    if (
        set(by_altitude) != set(expected_altitudes)
        or any(len(by_altitude[altitude]) != bin_count for altitude in expected_altitudes)
    ):
        raise VisibilityDataPackError("direct training grid differs")
    flattened = [
        value
        for altitude in expected_altitudes
        for value in by_altitude[altitude]
    ]
    if any(not math.isfinite(value) or value < 0.0 for value in flattened):
        raise VisibilityDataPackError("direct extinction values differ")
    axes_payload = {
        "target_true_altitude_deg": expected_altitudes,
        "spectral_bins": {
            "start_nm": float(declaration["spectral_bin_start_nm"]),
            "width_nm": float(declaration["spectral_bin_width_nm"]),
            "count": bin_count,
            "coordinate": "bin_start_vacuum_nm",
        },
        "linearization_order": (
            "row_major_target_altitude_then_spectral_bin_fastest"
        ),
        "value_count": len(flattened),
    }
    return axes_payload, flattened


def _notice(spec: dict[str, Any]) -> str:
    return """# Moira Physical Heliacal Visibility Data Pack Notice

This separately distributed data pack is licensed under the Creative Commons
Attribution-ShareAlike 4.0 International license:
https://creativecommons.org/licenses/by-sa/4.0/

The response-integrated products use:

- CIE spectral luminous efficiency for photopic vision, International
  Commission on Illumination (CIE), 2019,
  DOI 10.25039/CIE.DS.dktna2s3, CC BY-SA 4.0.
- CIE spectral luminous efficiency for scotopic vision, International
  Commission on Illumination (CIE), 2019,
  DOI 10.25039/CIE.DS.gr6w4b5g, CC BY-SA 4.0.

The numerical reference calculations were generated offline with libRadtran 2.0.6
and the separately acquired REPTRAN 2024 module. No libRadtran source, binary,
profile, REPTRAN file, or CIE source table is included in this pack.
The exact generator and source identities are recorded in provenance.json.

The Moira engine source and wheel remain separate MIT-licensed artifacts.
This pack is optional, caller supplied, and is never downloaded during a
calculation.
"""


def _readme(spec: dict[str, Any]) -> str:
    pack = spec["pack"]
    return f"""# Moira Physical Heliacal Visibility Data Pack {pack['version']}

This immutable pack supplies the response-integrated Phase 1 atmosphere
tables for `{pack['composite_model_id']}`. It is not the Moira engine and
contains no event solver or limiting-magnitude implementation.

Use requires an explicit caller-supplied directory path. Validate that
directory with `scripts/validate_visibility_data_pack.py` before loading it.
Missing, corrupt, unsupported, or out-of-domain data must fail explicitly.
No component may download a replacement automatically.

Radiance values are positive IEEE-754 binary32 little-endian values,
linearized in the axis order declared by axes.json and interpolated
trilinearly in log10 luminance. Direct extinction values use the same binary
representation and linear interpolation in
log10(target_true_altitude_deg + 0.25) independently in every spectral bin.
Extrapolation is prohibited.

See NOTICE.md for licensing and provenance.json for exact scientific inputs.
"""


def _write_payload(
    root: Path,
    filename: str,
    content: bytes,
) -> Path:
    path = root / filename
    path.write_bytes(content)
    return path


def _generation_tooling(
    spec_path: Path, compatibility_path: Path
) -> dict[str, dict[str, Any]]:
    return {
        "specification": file_receipt(spec_path),
        "compatibility_contract": file_receipt(compatibility_path),
        "builder": file_receipt(Path(__file__).resolve()),
        "data_pack_validator": file_receipt(PACK_VALIDATOR_PATH),
        "source_artifact_validator": file_receipt(RADIANCE_VALIDATOR_PATH),
    }


def build_data_pack(
    *,
    spec_path: Path,
    compatibility_path: Path,
    radiance_spec_path: Path,
    source_artifact: Path,
    cie_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    compatibility_path = compatibility_path.resolve()
    radiance_spec_path = radiance_spec_path.resolve()
    source_artifact = source_artifact.resolve()
    cie_root = cie_root.resolve()
    output_root = output_root.resolve()
    spec = _load_spec(spec_path)
    compatibility = _load_compatibility(compatibility_path)
    radiance_spec = _require_dict(
        load_json(radiance_spec_path, "radiance specification"),
        "radiance specification",
    )
    radiance_solver = _require_dict(
        radiance_spec.get("radiance_solver"),
        "radiance solver",
    )
    expected_reference = {
        "spectral_importance_reference_wavelength_nm": radiance_solver.get(
            "spectral_importance_reference_wavelength_nm"
        ),
        "shape_normalization_wavelength_nm": radiance_solver.get(
            "normalization_wavelength_nm"
        ),
        "absolute_anchor_wavelength_nm": radiance_solver.get(
            "absolute_anchor_wavelength_nm"
        ),
        "selection": radiance_solver.get(
            "spectral_importance_reference_selection"
        ),
    }
    if expected_reference != compatibility["radiance_reference"]:
        raise VisibilityDataPackError(
            "radiance reference differs from compatibility contract"
        )
    manifest_source, summary, validation = _validate_source_artifact(
        source_artifact,
        cie_root,
        radiance_spec_path,
        spec,
    )
    if output_root.exists():
        raise VisibilityDataPackError(
            f"output already exists and is immutable: {output_root}"
        )
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_root.with_name(f".{output_root.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise VisibilityDataPackError(
            f"temporary output already exists: {temporary}"
        )
    temporary.mkdir()

    axes_payload, response_products = _response_tables(summary)
    direct_axes, direct_values = _direct_table(summary, spec)
    axes_payload["direct_extinction"] = direct_axes
    filenames = spec["files"]
    payload_paths: list[Path] = []
    payload_paths.append(
        _write_payload(
            temporary,
            filenames["axes"],
            canonical_json_bytes(axes_payload),
        )
    )
    for key in (
        "photopic_luminance",
        "scotopic_luminance",
        "photopic_relative_standard_error",
        "scotopic_relative_standard_error",
    ):
        payload_paths.append(
            _write_payload(
                temporary,
                filenames[key],
                _f32_bytes(response_products[key], key),
            )
        )
    payload_paths.append(
        _write_payload(
            temporary,
            filenames["direct_extinction"],
            _f32_bytes(direct_values, "direct extinction"),
        )
    )
    error_envelope = {
        "schema": (
            "moira.physical-heliacal-visibility-data-pack-error-envelope/v1"
        ),
        "accepted": summary["accepted"],
        "error_summaries": summary["error_summaries"],
        "diagnostic_contract": summary["diagnostic_contract"],
        "monte_carlo": summary["monte_carlo"],
        "storage_analysis": summary["storage_analysis"],
        "downstream_error_contract": summary["downstream_error_contract"],
    }
    payload_paths.append(
        _write_payload(
            temporary,
            filenames["error_envelope"],
            canonical_json_bytes(error_envelope),
        )
    )
    tooling = _generation_tooling(spec_path, compatibility_path)
    source_manifest_path = source_artifact / "artifact-manifest.json"
    source_summary_path = source_artifact / "summary.json"
    stable_validation = {
        key: validation[key]
        for key in (
            "validated",
            "manifest_sha256",
            "generation_fingerprint",
            "run_count",
        )
    }
    provenance = {
        "schema": (
            "moira.physical-heliacal-visibility-data-pack-provenance/v1"
        ),
        "build_date": spec["build_date"],
        "source_artifact": {
            "spec_id": manifest_source["spec_id"],
            "generation_fingerprint": manifest_source[
                "generation_fingerprint"
            ],
            "manifest": {
                "bytes": source_manifest_path.stat().st_size,
                "sha256": sha256_file(source_manifest_path),
            },
            "summary": {
                "bytes": source_summary_path.stat().st_size,
                "sha256": sha256_file(source_summary_path),
            },
            "independent_validation": stable_validation,
        },
        "scientific_sources": radiance_spec["sources"],
        "source_artifact_input_receipts": manifest_source["source"],
        "source_tooling": manifest_source["tooling"],
        "data_pack_tooling": tooling,
        "excluded_source_files": [
            "CIE_source_tables",
            "libRadtran_binary",
            "libRadtran_profiles",
            "libRadtran_source",
            "REPTRAN_files",
        ],
    }
    payload_paths.append(
        _write_payload(
            temporary,
            filenames["provenance"],
            canonical_json_bytes(provenance),
        )
    )
    payload_paths.append(
        _write_payload(
            temporary,
            filenames["notice"],
            _notice(spec).encode("utf-8"),
        )
    )
    payload_paths.append(
        _write_payload(
            temporary,
            filenames["readme"],
            _readme(spec).encode("utf-8"),
        )
    )
    checksum_lines = [
        f"{sha256_file(path)}  {path.name}"
        for path in sorted(payload_paths, key=lambda item: item.name)
    ]
    checksums_path = _write_payload(
        temporary,
        filenames["checksums"],
        ("\n".join(checksum_lines) + "\n").encode("ascii"),
    )
    payload_paths.append(checksums_path)
    payload_receipts = [
        file_receipt(path, relative_to=temporary)
        for path in sorted(payload_paths, key=lambda item: item.name)
    ]
    fingerprint_payload = {
        "specification": spec,
        "compatibility": compatibility,
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "source_summary_sha256": sha256_file(source_summary_path),
        "tooling": tooling,
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "complete_immutable_data_pack",
        "pack_id": spec["pack"]["pack_id"],
        "version": spec["pack"]["version"],
        "compatibility_id": compatibility["compatibility_id"],
        "composite_model_id": spec["pack"]["composite_model_id"],
        "table_format_id": spec["pack"]["table_format_id"],
        "license": spec["pack"]["license"],
        "generation_fingerprint": sha256_bytes(
            canonical_json_bytes(fingerprint_payload)
        ),
        "effective_domain": summary["effective_domain"],
        "deep_twilight_law": summary["deep_twilight_law"],
        "capabilities": compatibility["required_capabilities"],
        "interpolation": {
            "radiance": compatibility["radiance_interpolation"],
            "direct_extinction": compatibility[
                "direct_extinction_interpolation"
            ],
        },
        "radiance_reference": compatibility["radiance_reference"],
        "binary_representation": compatibility["binary_representation"],
        "source_artifact": spec["source_artifact"],
        "compatibility_contract": file_receipt(compatibility_path),
        "tooling": tooling,
        "file_roles": filenames,
        "payload_file_count": len(payload_receipts),
        "payload_files": payload_receipts,
        "root_manifest_receipt_owner": (
            "source_controlled_phase1_closure_checkpoint"
        ),
    }
    manifest_path = temporary / MANIFEST_NAME
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    os.replace(temporary, output_root)
    return {
        "status": "complete_immutable_data_pack",
        "output": str(output_root),
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "generation_fingerprint": manifest["generation_fingerprint"],
        "manifest_bytes": (output_root / MANIFEST_NAME).stat().st_size,
        "manifest_sha256": sha256_file(output_root / MANIFEST_NAME),
        "payload_file_count": manifest["payload_file_count"],
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the physical heliacal visibility data pack."
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument(
        "--compatibility",
        type=Path,
        default=DEFAULT_COMPATIBILITY_PATH,
    )
    parser.add_argument("--radiance-spec", type=Path)
    parser.add_argument("--source-artifact", type=Path)
    parser.add_argument("--cie-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--inspect-spec", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.inspect_spec:
            print(
                json.dumps(
                    inspect_spec(args.spec, args.compatibility),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        required = (
            "radiance_spec",
            "source_artifact",
            "cie_root",
            "output",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise VisibilityDataPackError(
                "build requires: " + ", ".join(missing)
            )
        result = build_data_pack(
            spec_path=args.spec,
            compatibility_path=args.compatibility,
            radiance_spec_path=args.radiance_spec,
            source_artifact=args.source_artifact,
            cie_root=args.cie_root,
            output_root=args.output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except VisibilityDataPackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
