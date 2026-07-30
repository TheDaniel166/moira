from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import pytest

from moira._visibility_lut import (
    VisibilityDataPackConfig,
    VisibilityDataPackDomainError,
    VisibilityDataPackLoadError,
    load_visibility_data_pack,
)
from moira._visibility_targets import (
    VisibilityTargetContext,
    VisibilityTargetProfileError,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENGINE_COMPATIBILITY_PATH = (
    _REPO_ROOT
    / "moira"
    / "data"
    / "physical_heliacal_visibility_data_pack_compatibility_v1.json"
)
_SOURCE_COMPATIBILITY_PATH = (
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_heliacal_visibility_data_pack_compatibility_v1.json"
)
_COMPATIBILITY_SHA256 = (
    "f50b199a211b75f7e6701f69c86020918f01df4940cfd1d3b86c6d6036659e37"
)
_ENGINE_COMPATIBILITY_V1_1_PATH = (
    _REPO_ROOT
    / "moira"
    / "data"
    / "physical_heliacal_visibility_data_pack_compatibility_v1_1.json"
)
_SOURCE_COMPATIBILITY_V1_1_PATH = (
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_heliacal_visibility_data_pack_compatibility_v1_1.json"
)
_COMPATIBILITY_V1_1_SHA256 = (
    "7ba04e30cd5f0b48f39aadd8264d862fde010e4700bf0248bc6c3f840d70969c"
)
_MANIFEST_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-manifest/v1"
)
_FILE_ROLES = {
    "axes": "axes.json",
    "checksums": "SHA256SUMS",
    "direct_extinction": "direct-extinction-1nm.f32le",
    "error_envelope": "error-envelope.json",
    "notice": "NOTICE.md",
    "photopic_luminance": (
        "solar-twilight-photopic-luminance.f32le"
    ),
    "photopic_relative_standard_error": (
        "solar-twilight-photopic-rse.f32le"
    ),
    "provenance": "provenance.json",
    "readme": "README.md",
    "scotopic_luminance": (
        "solar-twilight-scotopic-luminance.f32le"
    ),
    "scotopic_relative_standard_error": (
        "solar-twilight-scotopic-rse.f32le"
    ),
}
_SOURCE_ARTIFACT = {
    "spec_id": "synthetic-phase2-loader-test-v1",
    "manifest": {
        "bytes": 123,
        "sha256": "a" * 64,
    },
}


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_json_bytes(value))


def _write_f32(path: Path, values: list[float]) -> None:
    path.write_bytes(struct.pack(f"<{len(values)}f", *values))


def _synthetic_pack(tmp_path: Path) -> Path:
    pack_dir = tmp_path / "physical-visibility-pack"
    pack_dir.mkdir()
    compatibility = json.loads(
        _ENGINE_COMPATIBILITY_PATH.read_text(encoding="utf-8")
    )

    _write_json(
        pack_dir / _FILE_ROLES["axes"],
        {
            "schema": (
                "moira.physical-heliacal-visibility-data-pack-axes/v1"
            ),
            "radiance": {
                "axes": {
                    "solar_center_altitude_deg": [-9.0, 0.0],
                    "target_true_altitude_deg": [0.25, 45.0],
                    "relative_solar_azimuth_deg": [0.0, 180.0],
                },
                "coordinate_order": [
                    "solar_center_altitude_deg",
                    "target_true_altitude_deg",
                    "relative_solar_azimuth_deg",
                ],
                "linearization_order": (
                    "row_major_last_axis_fastest"
                ),
                "value_count": 8,
            },
            "direct_extinction": {
                "linearization_order": (
                    "row_major_target_altitude_then_spectral_bin_fastest"
                ),
                "spectral_bins": {
                    "coordinate": "bin_start_vacuum_nm",
                    "start_nm": 380.0,
                    "width_nm": 1.0,
                    "count": 400,
                },
                "target_true_altitude_deg": [0.25, 45.0],
                "value_count": 800,
            },
        },
    )
    _write_json(
        pack_dir / _FILE_ROLES["error_envelope"],
        {
            "schema": (
                "moira.physical-heliacal-visibility-data-pack-error-envelope/v1"
            ),
            "accepted": True,
            "error_summaries": {
                "photopic_response": {
                    "maximum_error_mag": 0.35,
                    "p95_error_mag": 0.28,
                },
                "scotopic_response": {
                    "maximum_error_mag": 0.25,
                    "p95_error_mag": 0.24,
                },
                "direct_extinction_1nm": {
                    "maximum_error_mag": 0.02,
                    "p95_error_mag": 0.003,
                },
            },
            "storage_analysis": {
                "float32_maximum_error_mag": 0.000001,
                "selected_representation": (
                    "little_endian_ieee754_binary32"
                ),
                (
                    "storage_error_is_separate_from_solver_and_"
                    "interpolation_error"
                ): True,
            },
            "downstream_error_contract": {
                "background_interpolation_error_unit": (
                    "surface_brightness_magnitude"
                ),
                "direct_extinction_error_unit": "magnitude",
                "per_cell_solver_uncertainty_required": True,
                "limiting_magnitude_propagation_owner": (
                    "phase2_single_epoch_truth"
                ),
                "event_time_propagation_owner": "phase3_event_solver",
                (
                    "phase1_does_not_fabricate_downstream_"
                    "derivatives"
                ): True,
            },
            "diagnostic_contract": {
                "monochromatic_reference": {
                    "surface_shipped_in_data_pack": False,
                    "surface_used_by_runtime_interpolation": False,
                    "admission_gate": False,
                }
            },
        },
    )
    _write_json(
        pack_dir / _FILE_ROLES["provenance"],
        {
            "schema": (
                "moira.physical-heliacal-visibility-data-pack-provenance/v1"
            ),
            "excluded_source_files": [
                "CIE_source_tables",
                "libRadtran_binary",
                "libRadtran_profiles",
                "libRadtran_source",
                "REPTRAN_files",
            ],
            "scientific_sources": {
                "CIE_photopic": {
                    "dataset_doi": "10.25039/CIE.DS.dktna2s3"
                },
                "CIE_scotopic": {
                    "dataset_doi": "10.25039/CIE.DS.gr6w4b5g"
                },
                "libRadtran": {"version": "2.0.6"},
                "REPTRAN_module": {
                    "module_id": "libradtran_reptran_2024_all",
                    "resolution": "fine",
                },
            },
            "source_artifact": _SOURCE_ARTIFACT,
        },
    )
    (pack_dir / _FILE_ROLES["notice"]).write_text(
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
    (pack_dir / _FILE_ROLES["readme"]).write_text(
        "Use an explicit caller-supplied directory path.\n"
        "No component may download a replacement automatically.\n",
        encoding="utf-8",
    )

    photopic = [10.0**index for index in range(8)]
    _write_f32(
        pack_dir / _FILE_ROLES["photopic_luminance"],
        photopic,
    )
    _write_f32(
        pack_dir / _FILE_ROLES["scotopic_luminance"],
        [2.0 * value for value in photopic],
    )
    _write_f32(
        pack_dir / _FILE_ROLES[
            "photopic_relative_standard_error"
        ],
        [0.01 * (index + 1) for index in range(8)],
    )
    _write_f32(
        pack_dir / _FILE_ROLES[
            "scotopic_relative_standard_error"
        ],
        [0.02 * (index + 1) for index in range(8)],
    )
    _write_f32(
        pack_dir / _FILE_ROLES["direct_extinction"],
        [1.0] * 400 + [3.0] * 400,
    )

    names_without_checksums = sorted(
        set(_FILE_ROLES.values()) - {_FILE_ROLES["checksums"]}
    )
    checksum_text = "".join(
        f"{_sha256(pack_dir / name)}  {name}\n"
        for name in names_without_checksums
    )
    (pack_dir / _FILE_ROLES["checksums"]).write_text(
        checksum_text,
        encoding="ascii",
        newline="\n",
    )
    payloads = [
        {
            "path": name,
            "bytes": (pack_dir / name).stat().st_size,
            "sha256": _sha256(pack_dir / name),
        }
        for name in sorted(_FILE_ROLES.values())
    ]
    _write_json(
        pack_dir / "manifest.json",
        {
            "schema": _MANIFEST_SCHEMA,
            "status": "complete_immutable_data_pack",
            "pack_id": "moira-physical-heliacal-visibility",
            "version": "1.0.0",
            "compatibility_id": (
                "moira-physical-heliacal-visibility-data-pack-v1"
            ),
            "composite_model_id": (
                "clear_sky_naked_eye_point_source_v1"
            ),
            "table_format_id": (
                "regular-grid-ieee754-binary32-le-v1"
            ),
            "license": "CC-BY-SA-4.0",
            "capabilities": compatibility["required_capabilities"],
            "interpolation": {
                "radiance": compatibility["radiance_interpolation"],
                "direct_extinction": compatibility[
                    "direct_extinction_interpolation"
                ],
            },
            "radiance_reference": compatibility["radiance_reference"],
            "binary_representation": compatibility[
                "binary_representation"
            ],
            "root_manifest_receipt_owner": (
                "source_controlled_phase1_closure_checkpoint"
            ),
            "compatibility_contract": {
                "path": str(_SOURCE_COMPATIBILITY_PATH),
                "bytes": _ENGINE_COMPATIBILITY_PATH.stat().st_size,
                "sha256": _COMPATIBILITY_SHA256,
            },
            "generation_fingerprint": "b" * 64,
            "deep_twilight_law": {
                "table_minimum_solar_center_altitude_deg": -9.0,
                "solar_altitude_below_table": (
                    "not_evaluable_for_modeled_twilight_background"
                ),
                "reason": "solar_twilight_below_data_pack_domain",
                "monte_carlo_non_detection_is_zero": False,
            },
            "effective_domain": {
                "atmosphere_profile": ["us_standard"],
                "aerosol_profile": ["rural_summer"],
                "observer_altitude_m": [0.0, 0.0],
                "surface_pressure_hpa": [1013.25, 1013.25],
                "aod550": [0.1, 0.1],
                "angstrom_exponent": [1.3, 1.3],
                "ozone_du": [300.0, 300.0],
                "ground_albedo": [0.2, 0.2],
                "solar_center_altitude_deg": [-9.0, 0.0],
                "target_true_altitude_deg": [0.25, 45.0],
                "relative_solar_azimuth_deg": [0.0, 180.0],
                "refraction": (
                    "disabled_true_geometric_line_of_sight"
                ),
                "outside_domain": "typed_not_evaluable",
                "no_extrapolation": True,
            },
            "file_roles": _FILE_ROLES,
            "payload_file_count": len(payloads),
            "payload_files": payloads,
            "source_artifact": _SOURCE_ARTIFACT,
        },
    )
    return pack_dir


def _read_manifest(pack_dir: Path) -> dict[str, Any]:
    return json.loads(
        (pack_dir / "manifest.json").read_text(encoding="utf-8")
    )


def _write_manifest(pack_dir: Path, manifest: dict[str, Any]) -> None:
    _write_json(pack_dir / "manifest.json", manifest)


def _refresh_payload_receipts(pack_dir: Path) -> None:
    """Re-sign a synthetic pack after an intentional authenticated mutation."""

    manifest = _read_manifest(pack_dir)
    role_names = set(manifest["file_roles"].values())
    checksum_name = manifest["file_roles"]["checksums"]
    names_without_checksums = sorted(role_names - {checksum_name})
    (pack_dir / checksum_name).write_text(
        "".join(
            f"{_sha256(pack_dir / name)}  {name}\n"
            for name in names_without_checksums
        ),
        encoding="ascii",
        newline="\n",
    )
    manifest["payload_files"] = [
        {
            "path": name,
            "bytes": (pack_dir / name).stat().st_size,
            "sha256": _sha256(pack_dir / name),
        }
        for name in sorted(role_names)
    ]
    manifest["payload_file_count"] = len(manifest["payload_files"])
    _write_manifest(pack_dir, manifest)


def test_installed_compatibility_contract_is_exact_phase1_contract() -> None:
    installed = _ENGINE_COMPATIBILITY_PATH.read_bytes()

    assert installed == _SOURCE_COMPATIBILITY_PATH.read_bytes()
    assert hashlib.sha256(installed).hexdigest() == _COMPATIBILITY_SHA256


def test_installed_phase2_compatibility_contract_is_exact() -> None:
    installed = _ENGINE_COMPATIBILITY_V1_1_PATH.read_bytes()
    contract = json.loads(installed)

    assert installed == _SOURCE_COMPATIBILITY_V1_1_PATH.read_bytes()
    assert (
        hashlib.sha256(installed).hexdigest()
        == _COMPATIBILITY_V1_1_SHA256
    )
    assert contract["supported_pack_minor_versions"] == [1]
    assert contract["target_profiles"]["target_ids"] == [
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
    ]
    assert (
        contract["runtime_boundary"]["automatic_download_allowed"]
        is False
    )
    assert contract["runtime_boundary"]["network_allowed"] is False


def test_loads_valid_pack_with_identity_and_domain_receipts(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    manifest_sha256 = _sha256(pack_dir / "manifest.json")

    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(
            directory=pack_dir,
            expected_manifest_sha256=manifest_sha256,
        )
    )

    assert pack.receipt.pack_id == "moira-physical-heliacal-visibility"
    assert pack.receipt.version == "1.0.0"
    assert pack.receipt.manifest_sha256 == manifest_sha256
    assert pack.receipt.engine_contract_version == 1
    assert pack.receipt.source_artifact_manifest_sha256 == "a" * 64
    assert pack.receipt.source_dataset_ids == (
        "CIE_photopic:10.25039/CIE.DS.dktna2s3",
        "CIE_scotopic:10.25039/CIE.DS.gr6w4b5g",
        "libRadtran:2.0.6",
        "REPTRAN:libradtran_reptran_2024_all",
    )
    assert pack.domain.solar_center_altitude_deg == (-9.0, 0.0)
    assert pack.domain.target_true_altitude_deg == (0.25, 45.0)
    assert pack.domain.no_extrapolation is True


def test_phase1_pack_has_no_planetary_target_profiles(
    tmp_path: Path,
) -> None:
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(directory=_synthetic_pack(tmp_path))
    )

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        pack.resolve_target_profile(
            "Venus",
            VisibilityTargetContext(phase_angle_deg=30.0),
        )

    assert exc_info.value.reason == "target_spectral_profile_missing"


def test_radiance_node_and_log10_midpoint_interpolation(
    tmp_path: Path,
) -> None:
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(directory=_synthetic_pack(tmp_path))
    )

    node = pack.interpolate_twilight_luminance(
        solar_center_altitude_deg=-9.0,
        target_true_altitude_deg=0.25,
        relative_solar_azimuth_deg=0.0,
    )
    midpoint = pack.interpolate_twilight_luminance(
        solar_center_altitude_deg=-4.5,
        target_true_altitude_deg=22.625,
        relative_solar_azimuth_deg=90.0,
    )

    assert node.photopic_luminance_cd_m2 == 1.0
    assert node.scotopic_luminance_cd_m2 == 2.0
    assert node.photopic_solver_relative_standard_error_bound == pytest.approx(
        0.01
    )
    assert midpoint.photopic_luminance_cd_m2 == pytest.approx(10.0**3.5)
    assert midpoint.scotopic_luminance_cd_m2 == pytest.approx(
        2.0 * 10.0**3.5
    )
    assert (
        midpoint.photopic_solver_relative_standard_error_bound
        == pytest.approx(0.08)
    )
    assert (
        midpoint.scotopic_solver_relative_standard_error_bound
        == pytest.approx(0.16)
    )
    assert (
        midpoint.solver_uncertainty_bound_method
        == "maximum_contributing_corner"
    )


def test_direct_extinction_uses_declared_log_altitude_coordinate(
    tmp_path: Path,
) -> None:
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(directory=_synthetic_pack(tmp_path))
    )
    midpoint_target = 10.0 ** (
        (math.log10(0.25 + 0.25) + math.log10(45.0 + 0.25))
        / 2.0
    ) - 0.25

    spectrum = pack.interpolate_direct_extinction_spectrum(
        target_true_altitude_deg=midpoint_target
    )

    assert len(spectrum.spectral_bin_start_nm) == 400
    assert spectrum.spectral_bin_start_nm == tuple(
        float(value) for value in range(380, 780)
    )
    assert spectrum.extinction_magnitude == pytest.approx((2.0,) * 400)
    assert spectrum.transmission == pytest.approx(
        (10.0 ** (-0.8),) * 400
    )


@pytest.mark.parametrize(
    ("arguments", "reason"),
    (
        (
            {
                "solar_center_altitude_deg": -9.01,
                "target_true_altitude_deg": 1.0,
                "relative_solar_azimuth_deg": 90.0,
            },
            "solar_twilight_below_data_pack_domain",
        ),
        (
            {
                "solar_center_altitude_deg": 0.01,
                "target_true_altitude_deg": 1.0,
                "relative_solar_azimuth_deg": 90.0,
            },
            "solar_altitude_out_of_domain",
        ),
        (
            {
                "solar_center_altitude_deg": -6.0,
                "target_true_altitude_deg": 0.24,
                "relative_solar_azimuth_deg": 90.0,
            },
            "target_altitude_out_of_domain",
        ),
        (
            {
                "solar_center_altitude_deg": -6.0,
                "target_true_altitude_deg": 1.0,
                "relative_solar_azimuth_deg": 180.01,
            },
            "criterion_out_of_domain",
        ),
        (
            {
                "solar_center_altitude_deg": float("nan"),
                "target_true_altitude_deg": 1.0,
                "relative_solar_azimuth_deg": 90.0,
            },
            "criterion_out_of_domain",
        ),
    ),
)
def test_radiance_interpolation_fails_closed_outside_domain(
    tmp_path: Path,
    arguments: dict[str, float],
    reason: str,
) -> None:
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(directory=_synthetic_pack(tmp_path))
    )

    with pytest.raises(VisibilityDataPackDomainError) as exc_info:
        pack.interpolate_twilight_luminance(**arguments)

    assert exc_info.value.reason == reason


def test_direct_extinction_fails_closed_outside_domain(
    tmp_path: Path,
) -> None:
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(directory=_synthetic_pack(tmp_path))
    )

    with pytest.raises(VisibilityDataPackDomainError) as exc_info:
        pack.interpolate_direct_extinction_spectrum(
            target_true_altitude_deg=45.01
        )

    assert exc_info.value.reason == "target_altitude_out_of_domain"


@pytest.mark.parametrize("directory", ("", "   ", None))
def test_config_rejects_missing_explicit_directory(directory: Any) -> None:
    with pytest.raises(ValueError, match="explicit filesystem path"):
        VisibilityDataPackConfig(directory=directory)


def test_missing_pack_has_stable_reason(tmp_path: Path) -> None:
    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=tmp_path / "missing")
        )

    assert exc_info.value.reason == "visibility_data_pack_missing"


def test_caller_manifest_receipt_mismatch_has_stable_reason(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(
                directory=pack_dir,
                expected_manifest_sha256="0" * 64,
            )
        )

    assert (
        exc_info.value.reason
        == "visibility_data_pack_checksum_mismatch"
    )


@pytest.mark.parametrize(
    "version",
    ("2.0.0", "1", "1.0", "01.0.0", "1.0.0-rc1", 1),
)
def test_unsupported_or_malformed_pack_version_fails_closed(
    tmp_path: Path,
    version: Any,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    manifest = _read_manifest(pack_dir)
    manifest["version"] = version
    _write_manifest(pack_dir, manifest)

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=pack_dir)
        )

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_malformed_source_receipt_is_a_typed_load_failure(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    manifest = _read_manifest(pack_dir)
    manifest["source_artifact"]["manifest"].pop("sha256")
    _write_manifest(pack_dir, manifest)

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=pack_dir)
        )

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_corrupt_payload_has_stable_checksum_reason(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    payload = pack_dir / _FILE_ROLES["photopic_luminance"]
    payload.write_bytes(payload.read_bytes() + b"\x00")

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=pack_dir)
        )

    assert (
        exc_info.value.reason
        == "visibility_data_pack_checksum_mismatch"
    )


def test_authenticated_relative_standard_error_at_one_fails_closed(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    _write_f32(
        pack_dir
        / _FILE_ROLES["photopic_relative_standard_error"],
        [1.0] + [0.01] * 7,
    )
    _refresh_payload_receipts(pack_dir)

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=pack_dir)
        )

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_authenticated_p95_above_maximum_fails_closed(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    envelope_path = pack_dir / _FILE_ROLES["error_envelope"]
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["error_summaries"]["direct_extinction_1nm"][
        "p95_error_mag"
    ] = 0.03
    _write_json(envelope_path, envelope)
    _refresh_payload_receipts(pack_dir)

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=pack_dir)
        )

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_unexpected_root_file_has_stable_checksum_reason(
    tmp_path: Path,
) -> None:
    pack_dir = _synthetic_pack(tmp_path)
    (pack_dir / "unexpected.txt").write_text("not admitted", encoding="utf-8")

    with pytest.raises(VisibilityDataPackLoadError) as exc_info:
        load_visibility_data_pack(
            VisibilityDataPackConfig(directory=pack_dir)
        )

    assert (
        exc_info.value.reason
        == "visibility_data_pack_checksum_mismatch"
    )
