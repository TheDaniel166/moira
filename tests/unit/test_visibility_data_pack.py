from __future__ import annotations

import ast
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import pytest

from scripts.build_visibility_data_pack import (
    _f32_bytes,
    canonical_json_bytes,
    inspect_spec,
)
from scripts.validate_visibility_data_pack import (
    VisibilityDataPackValidationError,
    validate_data_pack,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_heliacal_visibility_data_pack_compatibility_v1.json"
)
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_visibility_data_pack_spec.json"
)
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_visibility_data_pack.py"
BUILDER_PATH = REPO_ROOT / "scripts" / "build_visibility_data_pack.py"
PACK_CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_visibility_data_pack_checkpoint_2026-07-30.json"
)
CLOSURE_CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_closure_checkpoint_2026-07-30.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _synthetic_pack(root: Path) -> Path:
    root.mkdir()
    compatibility = json.loads(
        COMPATIBILITY_PATH.read_text(encoding="utf-8")
    )
    roles = {
        "axes": "axes.json",
        "photopic_luminance": "photopic.bin",
        "scotopic_luminance": "scotopic.bin",
        "photopic_relative_standard_error": "photopic-rse.bin",
        "scotopic_relative_standard_error": "scotopic-rse.bin",
        "direct_extinction": "direct.bin",
        "error_envelope": "error-envelope.json",
        "provenance": "provenance.json",
        "notice": "NOTICE.md",
        "readme": "README.md",
        "checksums": "SHA256SUMS",
    }
    axes = {
        "schema": "moira.physical-heliacal-visibility-data-pack-axes/v1",
        "radiance": {
            "coordinate_order": [
                "solar_center_altitude_deg",
                "target_true_altitude_deg",
                "relative_solar_azimuth_deg",
            ],
            "linearization_order": "row_major_last_axis_fastest",
            "axes": {
                "solar_center_altitude_deg": [-9.0, 0.0],
                "target_true_altitude_deg": [0.25, 45.0],
                "relative_solar_azimuth_deg": [0.0, 180.0],
            },
            "value_count": 8,
        },
        "direct_extinction": {
            "target_true_altitude_deg": [0.25, 45.0],
            "spectral_bins": {
                "start_nm": 380.0,
                "width_nm": 1.0,
                "count": 2,
                "coordinate": "bin_start_vacuum_nm",
            },
            "linearization_order": (
                "row_major_target_altitude_then_spectral_bin_fastest"
            ),
            "value_count": 4,
        },
    }
    _write_json(root / roles["axes"], axes)
    (root / roles["photopic_luminance"]).write_bytes(
        _f32_bytes([0.1 + index * 0.01 for index in range(8)], "photopic")
    )
    (root / roles["scotopic_luminance"]).write_bytes(
        _f32_bytes([0.2 + index * 0.01 for index in range(8)], "scotopic")
    )
    (root / roles["photopic_relative_standard_error"]).write_bytes(
        _f32_bytes([0.05] * 8, "photopic rse")
    )
    (root / roles["scotopic_relative_standard_error"]).write_bytes(
        _f32_bytes([0.06] * 8, "scotopic rse")
    )
    (root / roles["direct_extinction"]).write_bytes(
        _f32_bytes([1.0, 0.9, 0.2, 0.1], "direct")
    )
    error_summaries = {
        name: {
            "sample_count": 1,
            "maximum_error_mag": 0.1,
            "p95_error_mag": 0.05,
        }
        for name in (
            "monochromatic_reference",
            "photopic_response",
            "scotopic_response",
            "direct_extinction_1nm",
        )
    }
    _write_json(
        root / roles["error_envelope"],
        {
            "schema": (
                "moira.physical-heliacal-visibility-data-pack-error-envelope/v1"
            ),
            "accepted": True,
            "error_summaries": error_summaries,
            "diagnostic_contract": {
                "monochromatic_reference": {
                    "admission_gate": False,
                    "surface_shipped_in_data_pack": False,
                    "surface_used_by_runtime_interpolation": False,
                    "role": (
                        "reported_intermediate_diagnostic_not_artifact_"
                        "admission_gate"
                    ),
                    "comparison_threshold_passed": False,
                    "maximum_comparison_error_mag": 0.5,
                    "p95_comparison_error_mag": 0.3,
                }
            },
            "monte_carlo": {},
            "storage_analysis": {
                "selected_representation": (
                    "little_endian_ieee754_binary32"
                ),
                "float32_maximum_error_mag": 1e-7,
                "quantized_maximum_error_mag": 0.0001,
            },
            "downstream_error_contract": {
                "limiting_magnitude_propagation_owner": (
                    "phase2_single_epoch_truth"
                ),
                "event_time_propagation_owner": "phase3_event_solver",
                "phase1_does_not_fabricate_downstream_derivatives": True,
            },
        },
    )
    source_artifact = {
        "spec_id": "synthetic-radiance-source",
        "manifest": {"bytes": 123, "sha256": "a" * 64},
        "summary": {"bytes": 456, "sha256": "b" * 64},
    }
    _write_json(
        root / roles["provenance"],
        {
            "schema": (
                "moira.physical-heliacal-visibility-data-pack-provenance/v1"
            ),
            "build_date": "2026-07-30",
            "source_artifact": {
                **source_artifact,
                "generation_fingerprint": "c" * 64,
                "independent_validation": {"validated": True},
            },
            "scientific_sources": {
                "libRadtran": {"version": "2.0.6"},
                "CIE_photopic": {
                    "dataset_doi": "10.25039/CIE.DS.dktna2s3"
                },
                "CIE_scotopic": {
                    "dataset_doi": "10.25039/CIE.DS.gr6w4b5g"
                },
            },
            "source_tooling": {},
            "data_pack_tooling": {},
            "excluded_source_files": [
                "CIE_source_tables",
                "libRadtran_binary",
                "libRadtran_profiles",
                "libRadtran_source",
                "REPTRAN_files",
            ],
        },
    )
    (root / roles["notice"]).write_text(
        "\n".join(
            (
                "Creative Commons",
                "https://creativecommons.org/licenses/by-sa/4.0/",
                "10.25039/CIE.DS.dktna2s3",
                "10.25039/CIE.DS.gr6w4b5g",
                "libRadtran 2.0.6",
                "No libRadtran source",
            )
        ),
        encoding="utf-8",
    )
    (root / roles["readme"]).write_text(
        "explicit caller-supplied directory path\n"
        "No component may download a replacement automatically.\n",
        encoding="utf-8",
    )
    checksum_inputs = sorted(
        (
            path
            for path in root.iterdir()
            if path.name != roles["checksums"]
        ),
        key=lambda path: path.name,
    )
    (root / roles["checksums"]).write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in checksum_inputs),
        encoding="ascii",
    )
    payload_paths = sorted(root.iterdir(), key=lambda path: path.name)
    compatibility_receipt = {
        "path": COMPATIBILITY_PATH.relative_to(REPO_ROOT).as_posix(),
        "bytes": COMPATIBILITY_PATH.stat().st_size,
        "sha256": _sha256(COMPATIBILITY_PATH),
    }
    manifest = {
        "schema": (
            "moira.physical-heliacal-visibility-data-pack-manifest/v1"
        ),
        "status": "complete_immutable_data_pack",
        "pack_id": "moira-physical-heliacal-visibility",
        "version": "1.0.0",
        "compatibility_id": compatibility["compatibility_id"],
        "composite_model_id": "clear_sky_naked_eye_point_source_v1",
        "table_format_id": "regular-grid-ieee754-binary32-le-v1",
        "license": "CC-BY-SA-4.0",
        "generation_fingerprint": "d" * 64,
        "effective_domain": {
            "solar_center_altitude_deg": [-9.0, 0.0],
            "target_true_altitude_deg": [0.25, 45.0],
            "relative_solar_azimuth_deg": [0.0, 180.0],
            "no_extrapolation": True,
            "outside_domain": "typed_not_evaluable",
        },
        "deep_twilight_law": {
            "table_minimum_solar_center_altitude_deg": -9.0,
            "solar_altitude_below_table": (
                "not_evaluable_for_modeled_twilight_background"
            ),
            "reason": "solar_twilight_below_data_pack_domain",
            "monte_carlo_non_detection_is_zero": False,
        },
        "capabilities": compatibility["required_capabilities"],
        "interpolation": {
            "radiance": compatibility["radiance_interpolation"],
            "direct_extinction": compatibility[
                "direct_extinction_interpolation"
            ],
        },
        "radiance_reference": compatibility["radiance_reference"],
        "binary_representation": compatibility["binary_representation"],
        "source_artifact": source_artifact,
        "compatibility_contract": compatibility_receipt,
        "tooling": {},
        "file_roles": roles,
        "payload_file_count": len(payload_paths),
        "payload_files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in payload_paths
        ],
        "root_manifest_receipt_owner": (
            "source_controlled_phase1_closure_checkpoint"
        ),
    }
    _write_json(root / "manifest.json", manifest)
    return root


def test_compatibility_contract_is_phase1_metadata_only() -> None:
    value = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    assert value["supported_pack_major_versions"] == [1]
    assert value["radiance_reference"] == {
        "spectral_importance_reference_wavelength_nm": 531.0,
        "shape_normalization_wavelength_nm": 531.0,
        "absolute_anchor_wavelength_nm": 531.0,
        "selection": (
            "training_diagnostic_balanced_photopic_scotopic_"
            "relative_standard_error"
        ),
    }
    assert value["runtime_boundary"] == {
        "caller_supplied_path_required": True,
        "automatic_download_allowed": False,
        "network_allowed": False,
        "libRadtran_required": False,
        "REPTRAN_required": False,
        "CIE_source_tables_required": False,
        "engine_loader_implementation_owner": "phase2_single_epoch_truth",
    }


def test_data_pack_spec_binds_the_v9_reference_artifact() -> None:
    inspected = inspect_spec(SPEC_PATH, COMPATIBILITY_PATH)
    assert inspected["spec_id"] == (
        "physical-heliacal-visibility-data-pack-1.0.0-2026-07-30"
    )
    assert inspected["pack"]["version"] == "1.0.0"
    assert inspected["source_artifact"]["spec_id"] == (
        "physical-heliacal-phase1-radiance-response-v9-2026-07-30"
    )
    assert inspected["failed_predecessors"]["notice_checkpoint"]["path"] == (
        "tests/artifacts/visibility_reference_lab/"
        "phase1_visibility_data_pack_v1_failed_notice_checkpoint_2026-07-30.json"
    )
    assert inspected["payload_file_count"] == 11
    assert inspected["runtime_boundary"]["network_allowed"] is False
    assert (
        inspected["runtime_boundary"]["engine_loader_in_scope"] is False
    )


def test_phase1_pack_and_closure_receipts_bind_current_repository_bytes() -> None:
    pack_checkpoint = json.loads(
        PACK_CHECKPOINT_PATH.read_text(encoding="utf-8")
    )
    assert pack_checkpoint["status"] == (
        "phase1_complete_immutable_data_pack_not_engine_runtime"
    )
    assert pack_checkpoint["validation"][
        "linux_independent_validation_passed"
    ]
    assert pack_checkpoint["validation"][
        "windows_independent_validation_passed"
    ]
    for receipt in pack_checkpoint["tooling"]:
        path = REPO_ROOT / receipt["path"]
        assert path.stat().st_size == receipt["bytes"]
        assert _sha256(path) == receipt["sha256"]

    closure = json.loads(CLOSURE_CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert closure["phase"] == 1
    assert closure["status"] == (
        "complete_reference_laboratory_and_data_pack_not_engine_runtime"
    )
    assert closure["runtime_boundary"]["engine_code_changed"] is False
    assert closure["runtime_boundary"]["engine_loader_implemented"] is False
    assert closure["scientific_boundary"][
        "first_runtime_data_pack_is_fixed_environment_baseline"
    ]
    for receipt in closure["admitted_receipts"]:
        path = REPO_ROOT / receipt["path"]
        assert path.stat().st_size == receipt["bytes"]
        assert _sha256(path) == receipt["sha256"]


def test_binary32_encoding_is_little_endian() -> None:
    assert _f32_bytes([1.0, 2.0], "fixture") == struct.pack("<ff", 1.0, 2.0)


def test_independent_validator_accepts_a_complete_pack(
    tmp_path: Path,
) -> None:
    pack = _synthetic_pack(tmp_path / "pack")
    result = validate_data_pack(pack)
    assert result["validated"] is True
    assert result["network_accessed"] is False
    assert result["radiance_value_count_per_response"] == 8
    assert result["direct_extinction_value_count"] == 4


def test_missing_pack_fails_explicitly_without_download(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        VisibilityDataPackValidationError,
        match="caller-supplied data-pack path is missing",
    ):
        validate_data_pack(tmp_path / "missing")


def test_corrupt_payload_fails_closed(tmp_path: Path) -> None:
    pack = _synthetic_pack(tmp_path / "pack")
    with (pack / "photopic.bin").open("ab") as stream:
        stream.write(b"\x00")
    with pytest.raises(
        VisibilityDataPackValidationError,
        match="payload receipt differs",
    ):
        validate_data_pack(pack)


def test_unsupported_major_version_fails_compatibility(
    tmp_path: Path,
) -> None:
    pack = _synthetic_pack(tmp_path / "pack")
    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "2.0.0"
    _write_json(manifest_path, manifest)
    with pytest.raises(
        VisibilityDataPackValidationError,
        match="incompatible",
    ):
        validate_data_pack(pack)


def test_unexpected_file_fails_exact_inventory(tmp_path: Path) -> None:
    pack = _synthetic_pack(tmp_path / "pack")
    (pack / "unbound.bin").write_bytes(b"unbound")
    with pytest.raises(
        VisibilityDataPackValidationError,
        match="file inventory differs",
    ):
        validate_data_pack(pack)


def test_unexpected_directory_fails_exact_inventory(
    tmp_path: Path,
) -> None:
    pack = _synthetic_pack(tmp_path / "pack")
    (pack / "unbound-directory").mkdir()
    with pytest.raises(
        VisibilityDataPackValidationError,
        match="directory inventory differs",
    ):
        validate_data_pack(pack)


def test_caller_supplied_symlink_is_rejected(tmp_path: Path) -> None:
    pack = _synthetic_pack(tmp_path / "pack")
    link = tmp_path / "pack-link"
    try:
        link.symlink_to(pack, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable in this environment")
    with pytest.raises(
        VisibilityDataPackValidationError,
        match="must not be a symlink",
    ):
        validate_data_pack(link)


def test_tools_import_neither_each_other_nor_network_clients() -> None:
    imported_by_tool: dict[Path, set[str]] = {}
    for path in (BUILDER_PATH, VALIDATOR_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_by_tool[path] = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
    assert "scripts.build_visibility_data_pack" not in imported_by_tool[
        VALIDATOR_PATH
    ]
    network_clients = {
        "http.client",
        "requests",
        "socket",
        "urllib",
        "urllib.request",
    }
    assert all(
        imported.isdisjoint(network_clients)
        for imported in imported_by_tool.values()
    )
