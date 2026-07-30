"""Validated runtime access to the external physical-visibility data pack.

This internal module owns only the Phase 2 table boundary:

* validate one explicit caller-supplied pack directory;
* bind its exact manifest and payload identities;
* enforce the pack's declared numerical domain; and
* interpolate response luminance and direct spectral extinction.

It performs no search, download, radiative-transfer calculation, limiting
magnitude evaluation, event solving, or public-policy selection.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._visibility_targets import (
    ResolvedVisibilityTargetProfile,
    VisibilityPackTargetProfile,
    VisibilityTargetContext,
    VisibilityTargetProfileError,
    parse_visibility_target_profiles,
    target_profile_by_id,
)

_COMPATIBILITY_V1_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "physical_heliacal_visibility_data_pack_compatibility_v1.json"
)
_COMPATIBILITY_V1_SHA256 = (
    "f50b199a211b75f7e6701f69c86020918f01df4940cfd1d3b86c6d6036659e37"
)
_COMPATIBILITY_V1_1_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "physical_heliacal_visibility_data_pack_compatibility_v1_1.json"
)
_COMPATIBILITY_V1_1_SHA256 = (
    "7ba04e30cd5f0b48f39aadd8264d862fde010e4700bf0248bc6c3f840d70969c"
)
_MANIFEST_NAME = "manifest.json"
_MANIFEST_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-manifest/v1"
)
_AXES_SCHEMA = "moira.physical-heliacal-visibility-data-pack-axes/v1"
_ERROR_ENVELOPE_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-error-envelope/v1"
)
_PROVENANCE_SCHEMA = (
    "moira.physical-heliacal-visibility-data-pack-provenance/v1"
)
_PACK_ID = "moira-physical-heliacal-visibility"
_COMPATIBILITY_V1_ID = (
    "moira-physical-heliacal-visibility-data-pack-v1"
)
_COMPATIBILITY_V1_1_ID = (
    "moira-physical-heliacal-visibility-data-pack-v1.1"
)
_COMPOSITE_MODEL_ID = "clear_sky_naked_eye_point_source_v1"
_TABLE_FORMAT_ID = "regular-grid-ieee754-binary32-le-v1"
_ENGINE_CONTRACT_ID = "moira-physical-visibility-engine-contract-v1"
_ENGINE_CONTRACT_VERSION = 1
_V1_REQUIRED_CAPABILITIES = frozenset(
    {
        "direct_spectral_extinction_regular_grid",
        "per_cell_solver_relative_standard_error",
        "solar_twilight_photopic_luminance_regular_grid",
        "solar_twilight_scotopic_luminance_regular_grid",
    }
)
_V1_FILE_ROLE_KEYS = frozenset(
    {
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
)
_V1_1_REQUIRED_CAPABILITIES = _V1_REQUIRED_CAPABILITIES | {
    "planetary_target_spectral_profiles"
}
_V1_1_FILE_ROLE_KEYS = _V1_FILE_ROLE_KEYS | {"target_profiles"}
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class _CompatibilityIdentity:
    path: Path
    sha256: str
    compatibility_id: str
    pack_minor_version: int
    status: str
    required_capabilities: frozenset[str]
    file_role_keys: frozenset[str]
    root_manifest_receipt_owner: str


class VisibilityDataPackLoadError(ValueError):
    """Typed fail-closed data-pack error consumed by the public policy layer."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class VisibilityDataPackDomainError(ValueError):
    """Typed interpolation-domain failure consumed by the public policy layer."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class VisibilityDataPackConfig:
    """Explicit local runtime configuration for one immutable data pack."""

    directory: Path | str
    expected_pack_id: str = _PACK_ID
    expected_composite_model_id: str = _COMPOSITE_MODEL_ID
    expected_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.directory, str) and not self.directory.strip():
            raise ValueError("directory must be an explicit filesystem path")
        try:
            directory = Path(self.directory)
        except TypeError as exc:
            raise ValueError(
                "directory must be an explicit filesystem path"
            ) from exc
        object.__setattr__(self, "directory", directory)
        if (
            not isinstance(self.expected_pack_id, str)
            or not self.expected_pack_id
        ):
            raise ValueError("expected_pack_id must not be empty")
        if (
            not isinstance(self.expected_composite_model_id, str)
            or not self.expected_composite_model_id
        ):
            raise ValueError(
                "expected_composite_model_id must not be empty"
            )
        if self.expected_manifest_sha256 is not None:
            _require_sha256(
                self.expected_manifest_sha256,
                "expected_manifest_sha256",
                error_type=ValueError,
            )


@dataclass(frozen=True, slots=True)
class VisibilityDataPackReceipt:
    """Immutable public-ready identity receipt for a loaded pack."""

    pack_id: str
    version: str
    compatibility_id: str
    composite_model_id: str
    table_format_id: str
    engine_contract_id: str
    engine_contract_version: int
    manifest_sha256: str
    generation_fingerprint: str
    payload_sha256: tuple[tuple[str, str], ...]
    source_artifact_spec_id: str
    source_artifact_manifest_sha256: str
    source_dataset_ids: tuple[str, ...]
    license: str
    notice_sha256: str


@dataclass(frozen=True, slots=True)
class VisibilityDataPackDomain:
    """The exact effective domain declared by the first data pack."""

    atmosphere_profile: str
    aerosol_profile: str
    observer_altitude_m: float
    surface_pressure_hpa: float
    aod550: float
    angstrom_exponent: float
    ozone_du: float
    ground_albedo: float
    solar_center_altitude_deg: tuple[float, float]
    target_true_altitude_deg: tuple[float, float]
    relative_solar_azimuth_deg: tuple[float, float]
    refraction: str
    outside_domain: str
    no_extrapolation: bool


@dataclass(frozen=True, slots=True)
class VisibilityRadianceSample:
    """Response-integrated twilight luminance at one in-domain geometry."""

    solar_center_altitude_deg: float
    target_true_altitude_deg: float
    relative_solar_azimuth_deg: float
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    photopic_solver_relative_standard_error_bound: float
    scotopic_solver_relative_standard_error_bound: float
    solver_uncertainty_bound_method: str
    photopic_interpolation_maximum_error_mag: float
    photopic_interpolation_p95_error_mag: float
    scotopic_interpolation_maximum_error_mag: float
    scotopic_interpolation_p95_error_mag: float
    storage_maximum_error_mag: float


@dataclass(frozen=True, slots=True)
class VisibilityDirectExtinctionSpectrum:
    """Interpolated direct extinction and transmission over the pack bins."""

    target_true_altitude_deg: float
    spectral_bin_start_nm: tuple[float, ...]
    extinction_magnitude: tuple[float, ...]
    transmission: tuple[float, ...]
    interpolation_maximum_error_mag: float
    interpolation_p95_error_mag: float
    storage_maximum_error_mag: float


@dataclass(frozen=True, slots=True)
class VisibilityDataPack:
    """Validated immutable tables plus deterministic interpolation methods."""

    receipt: VisibilityDataPackReceipt
    domain: VisibilityDataPackDomain
    _solar_axis: tuple[float, ...]
    _target_radiance_axis: tuple[float, ...]
    _azimuth_axis: tuple[float, ...]
    _photopic_luminance: tuple[float, ...]
    _scotopic_luminance: tuple[float, ...]
    _photopic_rse: tuple[float, ...]
    _scotopic_rse: tuple[float, ...]
    _direct_target_axis: tuple[float, ...]
    _spectral_bin_start_nm: tuple[float, ...]
    _direct_extinction: tuple[float, ...]
    _photopic_error_max_mag: float
    _photopic_error_p95_mag: float
    _scotopic_error_max_mag: float
    _scotopic_error_p95_mag: float
    _direct_error_max_mag: float
    _direct_error_p95_mag: float
    _storage_error_max_mag: float
    _target_profiles: tuple[VisibilityPackTargetProfile, ...] = ()

    def interpolate_twilight_luminance(
        self,
        *,
        solar_center_altitude_deg: float,
        target_true_altitude_deg: float,
        relative_solar_azimuth_deg: float,
    ) -> VisibilityRadianceSample:
        """Interpolate photopic/scotopic luminance without extrapolation."""

        solar = _finite_coordinate(
            solar_center_altitude_deg, "solar_center_altitude_deg"
        )
        target = _finite_coordinate(
            target_true_altitude_deg, "target_true_altitude_deg"
        )
        azimuth = _finite_coordinate(
            relative_solar_azimuth_deg, "relative_solar_azimuth_deg"
        )
        if solar < self._solar_axis[0]:
            raise VisibilityDataPackDomainError(
                "solar_twilight_below_data_pack_domain",
                (
                    f"solar_center_altitude_deg={solar} is below "
                    f"{self._solar_axis[0]}"
                ),
            )
        solar_bracket = _axis_bracket(
            self._solar_axis,
            solar,
            "solar_altitude_out_of_domain",
            "solar_center_altitude_deg",
        )
        target_bracket = _axis_bracket(
            self._target_radiance_axis,
            target,
            "target_altitude_out_of_domain",
            "target_true_altitude_deg",
        )
        azimuth_bracket = _axis_bracket(
            self._azimuth_axis,
            azimuth,
            "criterion_out_of_domain",
            "relative_solar_azimuth_deg",
        )
        brackets = (solar_bracket, target_bracket, azimuth_bracket)
        shape = (
            len(self._solar_axis),
            len(self._target_radiance_axis),
            len(self._azimuth_axis),
        )
        photopic, photopic_rse = _trilinear_log10_with_rse_bound(
            self._photopic_luminance,
            self._photopic_rse,
            shape,
            brackets,
        )
        scotopic, scotopic_rse = _trilinear_log10_with_rse_bound(
            self._scotopic_luminance,
            self._scotopic_rse,
            shape,
            brackets,
        )
        return VisibilityRadianceSample(
            solar_center_altitude_deg=solar,
            target_true_altitude_deg=target,
            relative_solar_azimuth_deg=azimuth,
            photopic_luminance_cd_m2=photopic,
            scotopic_luminance_cd_m2=scotopic,
            photopic_solver_relative_standard_error_bound=photopic_rse,
            scotopic_solver_relative_standard_error_bound=scotopic_rse,
            solver_uncertainty_bound_method="maximum_contributing_corner",
            photopic_interpolation_maximum_error_mag=(
                self._photopic_error_max_mag
            ),
            photopic_interpolation_p95_error_mag=(
                self._photopic_error_p95_mag
            ),
            scotopic_interpolation_maximum_error_mag=(
                self._scotopic_error_max_mag
            ),
            scotopic_interpolation_p95_error_mag=(
                self._scotopic_error_p95_mag
            ),
            storage_maximum_error_mag=self._storage_error_max_mag,
        )

    def interpolate_direct_extinction_spectrum(
        self,
        *,
        target_true_altitude_deg: float,
    ) -> VisibilityDirectExtinctionSpectrum:
        """Interpolate every direct-extinction bin in the admitted coordinate."""

        target = _finite_coordinate(
            target_true_altitude_deg, "target_true_altitude_deg"
        )
        low, high, fraction = _axis_bracket(
            tuple(
                math.log10(value + 0.25)
                for value in self._direct_target_axis
            ),
            math.log10(target + 0.25)
            if target > -0.25
            else float("-inf"),
            "target_altitude_out_of_domain",
            "target_true_altitude_deg",
            displayed_domain=(
                self._direct_target_axis[0],
                self._direct_target_axis[-1],
            ),
            displayed_value=target,
        )
        bin_count = len(self._spectral_bin_start_nm)
        low_offset = low * bin_count
        if low == high:
            extinction = self._direct_extinction[
                low_offset : low_offset + bin_count
            ]
        else:
            high_offset = high * bin_count
            extinction = tuple(
                self._direct_extinction[low_offset + index]
                + fraction
                * (
                    self._direct_extinction[high_offset + index]
                    - self._direct_extinction[low_offset + index]
                )
                for index in range(bin_count)
            )
        transmission = tuple(
            10.0 ** (-0.4 * magnitude) for magnitude in extinction
        )
        return VisibilityDirectExtinctionSpectrum(
            target_true_altitude_deg=target,
            spectral_bin_start_nm=self._spectral_bin_start_nm,
            extinction_magnitude=tuple(extinction),
            transmission=transmission,
            interpolation_maximum_error_mag=self._direct_error_max_mag,
            interpolation_p95_error_mag=self._direct_error_p95_mag,
            storage_maximum_error_mag=self._storage_error_max_mag,
        )

    def resolve_target_profile(
        self,
        target_id: str,
        context: VisibilityTargetContext,
    ) -> ResolvedVisibilityTargetProfile:
        """Resolve one pack-owned target spectrum for its source domain."""

        if not isinstance(target_id, str) or not target_id:
            raise ValueError("target_id must be a nonempty string")
        if not isinstance(context, VisibilityTargetContext):
            raise TypeError(
                "context must be a VisibilityTargetContext"
            )
        profile = target_profile_by_id(
            self._target_profiles,
            target_id,
        )
        return profile.resolve(context)


def load_visibility_data_pack(
    config: VisibilityDataPackConfig,
) -> VisibilityDataPack:
    """Load and independently validate exactly one explicit pack directory."""

    directory = Path(config.directory)
    if not directory.exists() or not directory.is_dir():
        _load_failure(
            "visibility_data_pack_missing",
            f"data-pack directory does not exist: {directory}",
        )
    if directory.is_symlink():
        _load_failure(
            "visibility_data_pack_incompatible",
            "data-pack directory must not be a symlink",
        )

    manifest_path = directory / _MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        _load_failure(
            "visibility_data_pack_missing",
            f"{_MANIFEST_NAME} is missing or is not a regular file",
        )
    manifest_sha256 = _sha256_file(manifest_path)
    if (
        config.expected_manifest_sha256 is not None
        and manifest_sha256 != config.expected_manifest_sha256
    ):
        _load_failure(
            "visibility_data_pack_checksum_mismatch",
            "root manifest SHA-256 differs from the caller expectation",
        )
    manifest = _read_json_dict(
        manifest_path,
        "root manifest",
        "visibility_data_pack_incompatible",
    )
    compatibility, compatibility_identity = (
        _load_compatibility_contract(manifest.get("version"))
    )
    file_roles, payload_receipts = _validate_manifest(
        manifest,
        compatibility,
        compatibility_identity,
        config,
    )
    _validate_inventory_and_payloads(
        directory,
        file_roles,
        payload_receipts,
    )

    axes = _read_json_dict(
        directory / file_roles["axes"],
        "axes",
        "visibility_data_pack_incompatible",
    )
    error_envelope = _read_json_dict(
        directory / file_roles["error_envelope"],
        "error envelope",
        "visibility_data_pack_incompatible",
    )
    provenance = _read_json_dict(
        directory / file_roles["provenance"],
        "provenance",
        "visibility_data_pack_incompatible",
    )
    domain = _validate_domain(manifest.get("effective_domain"))
    radiance_axes, direct_axes = _validate_axes(axes, domain)
    error_values = _validate_error_envelope(error_envelope)
    source_dataset_ids = _validate_provenance(
        provenance,
        manifest,
        compatibility_identity,
    )
    _validate_notice_and_readme(
        directory,
        file_roles,
        compatibility_identity,
    )
    target_profiles: tuple[VisibilityPackTargetProfile, ...] = ()
    if "target_profiles" in file_roles:
        target_payload = _read_json_dict(
            directory / file_roles["target_profiles"],
            "target profiles",
            "visibility_data_pack_incompatible",
        )
        try:
            target_profiles = parse_visibility_target_profiles(
                target_payload
            )
        except VisibilityTargetProfileError as exc:
            _load_failure(exc.reason, exc.detail)

    radiance_count = (
        len(radiance_axes[0])
        * len(radiance_axes[1])
        * len(radiance_axes[2])
    )
    photopic = _read_f32_table(
        directory / file_roles["photopic_luminance"],
        radiance_count,
        "photopic luminance",
        strictly_positive=True,
    )
    scotopic = _read_f32_table(
        directory / file_roles["scotopic_luminance"],
        radiance_count,
        "scotopic luminance",
        strictly_positive=True,
    )
    photopic_rse = _read_f32_table(
        directory / file_roles["photopic_relative_standard_error"],
        radiance_count,
        "photopic relative standard error",
        strictly_positive=False,
    )
    scotopic_rse = _read_f32_table(
        directory / file_roles["scotopic_relative_standard_error"],
        radiance_count,
        "scotopic relative standard error",
        strictly_positive=False,
    )
    if any(value >= 1.0 for value in (*photopic_rse, *scotopic_rse)):
        _load_failure(
            "visibility_data_pack_incompatible",
            "relative standard error must be below one",
        )
    direct_count = len(direct_axes[0]) * len(direct_axes[1])
    direct_extinction = _read_f32_table(
        directory / file_roles["direct_extinction"],
        direct_count,
        "direct extinction",
        strictly_positive=False,
    )

    source_artifact = _require_dict(
        manifest.get("source_artifact"),
        "source artifact",
    )
    source_manifest = _require_dict(
        source_artifact.get("manifest"),
        "source artifact manifest",
    )
    notice_receipt = payload_receipts[file_roles["notice"]]
    receipt = VisibilityDataPackReceipt(
        pack_id=manifest["pack_id"],
        version=manifest["version"],
        compatibility_id=manifest["compatibility_id"],
        composite_model_id=manifest["composite_model_id"],
        table_format_id=manifest["table_format_id"],
        engine_contract_id=_ENGINE_CONTRACT_ID,
        engine_contract_version=_ENGINE_CONTRACT_VERSION,
        manifest_sha256=manifest_sha256,
        generation_fingerprint=manifest["generation_fingerprint"],
        payload_sha256=tuple(
            (name, payload_receipts[name]["sha256"])
            for name in sorted(payload_receipts)
        ),
        source_artifact_spec_id=source_artifact["spec_id"],
        source_artifact_manifest_sha256=source_manifest["sha256"],
        source_dataset_ids=source_dataset_ids,
        license=manifest["license"],
        notice_sha256=notice_receipt["sha256"],
    )
    return VisibilityDataPack(
        receipt=receipt,
        domain=domain,
        _solar_axis=radiance_axes[0],
        _target_radiance_axis=radiance_axes[1],
        _azimuth_axis=radiance_axes[2],
        _photopic_luminance=photopic,
        _scotopic_luminance=scotopic,
        _photopic_rse=photopic_rse,
        _scotopic_rse=scotopic_rse,
        _direct_target_axis=direct_axes[0],
        _spectral_bin_start_nm=direct_axes[1],
        _direct_extinction=direct_extinction,
        _photopic_error_max_mag=error_values["photopic_max"],
        _photopic_error_p95_mag=error_values["photopic_p95"],
        _scotopic_error_max_mag=error_values["scotopic_max"],
        _scotopic_error_p95_mag=error_values["scotopic_p95"],
        _direct_error_max_mag=error_values["direct_max"],
        _direct_error_p95_mag=error_values["direct_p95"],
        _storage_error_max_mag=error_values["storage_max"],
        _target_profiles=target_profiles,
    )


def _load_compatibility_contract(
    pack_version: Any,
) -> tuple[dict[str, Any], _CompatibilityIdentity]:
    version = _semantic_version(pack_version)
    identities = {
        (1, 0): _CompatibilityIdentity(
            path=_COMPATIBILITY_V1_PATH,
            sha256=_COMPATIBILITY_V1_SHA256,
            compatibility_id=_COMPATIBILITY_V1_ID,
            pack_minor_version=0,
            status="phase1_metadata_contract_not_engine_loader",
            required_capabilities=_V1_REQUIRED_CAPABILITIES,
            file_role_keys=_V1_FILE_ROLE_KEYS,
            root_manifest_receipt_owner=(
                "source_controlled_phase1_closure_checkpoint"
            ),
        ),
        (1, 1): _CompatibilityIdentity(
            path=_COMPATIBILITY_V1_1_PATH,
            sha256=_COMPATIBILITY_V1_1_SHA256,
            compatibility_id=_COMPATIBILITY_V1_1_ID,
            pack_minor_version=1,
            status="phase2_engine_loader_contract",
            required_capabilities=_V1_1_REQUIRED_CAPABILITIES,
            file_role_keys=_V1_1_FILE_ROLE_KEYS,
            root_manifest_receipt_owner=(
                "source_controlled_phase2_closure_checkpoint"
            ),
        ),
    }
    identity = identities.get(version[:2])
    if identity is None:
        _load_failure(
            "visibility_data_pack_incompatible",
            "pack version has no installed compatibility contract",
        )
    if (
        not identity.path.is_file()
        or identity.path.is_symlink()
        or _sha256_file(identity.path) != identity.sha256
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "installed metadata compatibility contract differs",
        )
    value = _read_json_dict(
        identity.path,
        "installed compatibility contract",
        "visibility_data_pack_incompatible",
    )
    runtime = _require_dict(value.get("runtime_boundary"), "runtime boundary")
    if (
        value.get("schema")
        != "moira.physical-heliacal-visibility-data-pack-compatibility/v1"
        or value.get("compatibility_id") != identity.compatibility_id
        or value.get("status") != identity.status
        or value.get("supported_manifest_schemas") != [_MANIFEST_SCHEMA]
        or value.get("supported_pack_id") != _PACK_ID
        or value.get("supported_pack_major_versions") != [1]
        or value.get("supported_table_format_ids") != [_TABLE_FORMAT_ID]
        or value.get("supported_composite_model_ids")
        != [_COMPOSITE_MODEL_ID]
        or frozenset(value.get("required_capabilities", ()))
        != identity.required_capabilities
        or runtime.get("caller_supplied_path_required") is not True
        or runtime.get("automatic_download_allowed") is not False
        or runtime.get("network_allowed") is not False
        or runtime.get("libRadtran_required") is not False
        or runtime.get("REPTRAN_required") is not False
        or runtime.get("CIE_source_tables_required") is not False
        or runtime.get("engine_loader_implementation_owner")
        != "phase2_single_epoch_truth"
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "installed metadata compatibility contract is unsupported",
        )
    if identity.pack_minor_version == 0:
        if (
            "supported_pack_minor_versions" in value
            or "target_profiles" in value
            or "planetary_source_spectra_required" in runtime
        ):
            _load_failure(
                "visibility_data_pack_incompatible",
                "Phase 1 compatibility fields differ",
            )
    else:
        target_contract = _require_dict(
            value.get("target_profiles"),
            "target-profile compatibility contract",
        )
        if (
            value.get("supported_pack_minor_versions") != [1]
            or target_contract
            != {
                "schema": (
                    "moira.physical-heliacal-visibility-"
                    "target-profiles/v1"
                ),
                "file_role": "target_profiles",
                "target_ids": [
                    "Mercury",
                    "Venus",
                    "Mars",
                    "Jupiter",
                    "Saturn",
                ],
                "spectral_bins": {
                    "coordinate": "bin_start_vacuum_nm",
                    "start_nm": 380.0,
                    "width_nm": 1.0,
                    "count": 400,
                },
                "color_warp_method": (
                    "johnson_cousins_piecewise_linear_"
                    "differential_magnitude_v1"
                ),
                "outside_domain": "typed_not_evaluable",
            }
            or runtime.get("planetary_source_spectra_required")
            is not False
        ):
            _load_failure(
                "visibility_data_pack_incompatible",
                "Phase 2 target-profile compatibility fields differ",
            )
    return value, identity


def _validate_manifest(
    manifest: dict[str, Any],
    compatibility: dict[str, Any],
    compatibility_identity: _CompatibilityIdentity,
    config: VisibilityDataPackConfig,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    version = _semantic_version(manifest.get("version"))
    capabilities = manifest.get("capabilities")
    compatibility_receipt = _require_dict(
        manifest.get("compatibility_contract"),
        "compatibility receipt",
    )
    if (
        manifest.get("schema") not in compatibility["supported_manifest_schemas"]
        or manifest.get("schema") != _MANIFEST_SCHEMA
        or manifest.get("status") != "complete_immutable_data_pack"
        or manifest.get("pack_id") != config.expected_pack_id
        or manifest.get("pack_id") != compatibility["supported_pack_id"]
        or version[0]
        not in compatibility["supported_pack_major_versions"]
        or version[1] != compatibility_identity.pack_minor_version
        or manifest.get("compatibility_id")
        != compatibility_identity.compatibility_id
        or manifest.get("composite_model_id")
        != config.expected_composite_model_id
        or manifest.get("composite_model_id")
        not in compatibility["supported_composite_model_ids"]
        or manifest.get("table_format_id")
        not in compatibility["supported_table_format_ids"]
        or manifest.get("table_format_id") != _TABLE_FORMAT_ID
        or manifest.get("license") != "CC-BY-SA-4.0"
        or not isinstance(capabilities, list)
        or frozenset(capabilities)
        != compatibility_identity.required_capabilities
        or manifest.get("interpolation")
        != {
            "radiance": compatibility["radiance_interpolation"],
            "direct_extinction": compatibility[
                "direct_extinction_interpolation"
            ],
        }
        or manifest.get("radiance_reference")
        != compatibility["radiance_reference"]
        or manifest.get("binary_representation")
        != compatibility["binary_representation"]
        or manifest.get("root_manifest_receipt_owner")
        != compatibility_identity.root_manifest_receipt_owner
        or compatibility_receipt.get("bytes")
        != compatibility_identity.path.stat().st_size
        or compatibility_receipt.get("sha256")
        != compatibility_identity.sha256
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "root manifest differs from the engine compatibility contract",
        )
    if compatibility_identity.pack_minor_version == 0:
        if "target_profile_contract" in manifest:
            _load_failure(
                "visibility_data_pack_incompatible",
                "Phase 1 manifest unexpectedly declares target profiles",
            )
    elif (
        manifest.get("target_profile_contract")
        != compatibility["target_profiles"]
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "target-profile manifest contract differs",
        )
    _require_sha256(
        manifest.get("generation_fingerprint"),
        "generation fingerprint",
    )
    deep_twilight = _require_dict(
        manifest.get("deep_twilight_law"),
        "deep twilight law",
    )
    contract_twilight = compatibility["deep_twilight_law"]
    if (
        deep_twilight.get("table_minimum_solar_center_altitude_deg")
        != contract_twilight["minimum_solar_center_altitude_deg"]
        or deep_twilight.get("solar_altitude_below_table")
        != "not_evaluable_for_modeled_twilight_background"
        or deep_twilight.get("reason")
        != contract_twilight["below_minimum_modeled_twilight_reason"]
        or deep_twilight.get("monte_carlo_non_detection_is_zero") is not False
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "deep-twilight law differs",
        )
    roles_raw = _require_dict(manifest.get("file_roles"), "file roles")
    if (
        frozenset(roles_raw)
        != compatibility_identity.file_role_keys
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "file-role inventory differs",
        )
    file_roles: dict[str, str] = {}
    for role, filename in roles_raw.items():
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in {".", "..", _MANIFEST_NAME}
        ):
            _load_failure(
                "visibility_data_pack_incompatible",
                f"unsafe file-role path for {role}",
            )
        file_roles[role] = filename
    if len(set(file_roles.values())) != len(file_roles):
        _load_failure(
            "visibility_data_pack_incompatible",
            "file-role paths are not unique",
        )
    payloads = manifest.get("payload_files")
    if (
        not isinstance(payloads, list)
        or manifest.get("payload_file_count") != len(file_roles)
        or len(payloads) != len(file_roles)
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "payload receipt count differs",
        )
    payload_receipts: dict[str, dict[str, Any]] = {}
    for raw in payloads:
        receipt = _require_dict(raw, "payload receipt")
        path = receipt.get("path")
        if (
            not isinstance(path, str)
            or path in payload_receipts
            or not isinstance(receipt.get("bytes"), int)
            or isinstance(receipt.get("bytes"), bool)
            or receipt["bytes"] < 0
        ):
            _load_failure(
                "visibility_data_pack_incompatible",
                "payload receipt is malformed",
            )
        _require_sha256(receipt.get("sha256"), f"payload {path} SHA-256")
        payload_receipts[path] = receipt
    if set(payload_receipts) != set(file_roles.values()):
        _load_failure(
            "visibility_data_pack_incompatible",
            "payload receipts do not match file roles",
        )
    if compatibility_identity.pack_minor_version == 1:
        target_artifact = _require_dict(
            manifest.get("target_profile_artifact"),
            "target-profile artifact",
        )
        target_filename = file_roles["target_profiles"]
        if (
            target_artifact.get("target_profile_sha256")
            != payload_receipts[target_filename]["sha256"]
        ):
            _load_failure(
                "visibility_data_pack_incompatible",
                "target-profile artifact receipt differs",
            )
    return file_roles, payload_receipts


def _validate_inventory_and_payloads(
    directory: Path,
    file_roles: dict[str, str],
    payload_receipts: dict[str, dict[str, Any]],
) -> None:
    try:
        children = list(directory.iterdir())
    except OSError as exc:
        _load_failure(
            "visibility_data_pack_missing",
            f"data-pack directory cannot be read: {exc}",
        )
    expected = set(file_roles.values()) | {_MANIFEST_NAME}
    if {child.name for child in children} != expected:
        _load_failure(
            "visibility_data_pack_checksum_mismatch",
            "data-pack root file inventory differs",
        )
    for child in children:
        if child.is_symlink() or not child.is_file():
            _load_failure(
                "visibility_data_pack_checksum_mismatch",
                f"{child.name} is not a regular non-symlink file",
            )
    for filename, receipt in payload_receipts.items():
        path = directory / filename
        if (
            path.stat().st_size != receipt["bytes"]
            or _sha256_file(path) != receipt["sha256"]
        ):
            _load_failure(
                "visibility_data_pack_checksum_mismatch",
                f"payload receipt differs: {filename}",
            )
    checksum_path = directory / file_roles["checksums"]
    expected_lines = [
        f"{payload_receipts[name]['sha256']}  {name}"
        for name in sorted(
            set(file_roles.values()) - {file_roles["checksums"]}
        )
    ]
    try:
        checksum_text = checksum_path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        _load_failure(
            "visibility_data_pack_checksum_mismatch",
            f"SHA256SUMS cannot be read: {exc}",
        )
    if checksum_text != "\n".join(expected_lines) + "\n":
        _load_failure(
            "visibility_data_pack_checksum_mismatch",
            "SHA256SUMS content differs from the manifest",
        )


def _validate_domain(raw: Any) -> VisibilityDataPackDomain:
    value = _require_dict(raw, "effective domain")
    if (
        value.get("outside_domain") != "typed_not_evaluable"
        or value.get("no_extrapolation") is not True
        or value.get("refraction")
        != "disabled_true_geometric_line_of_sight"
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "effective-domain failure law differs",
        )
    return VisibilityDataPackDomain(
        atmosphere_profile=_fixed_domain_string(
            value, "atmosphere_profile"
        ),
        aerosol_profile=_fixed_domain_string(value, "aerosol_profile"),
        observer_altitude_m=_fixed_domain_number(
            value, "observer_altitude_m"
        ),
        surface_pressure_hpa=_fixed_domain_number(
            value, "surface_pressure_hpa"
        ),
        aod550=_fixed_domain_number(value, "aod550"),
        angstrom_exponent=_fixed_domain_number(
            value, "angstrom_exponent"
        ),
        ozone_du=_fixed_domain_number(value, "ozone_du"),
        ground_albedo=_fixed_domain_number(value, "ground_albedo"),
        solar_center_altitude_deg=_domain_interval(
            value, "solar_center_altitude_deg"
        ),
        target_true_altitude_deg=_domain_interval(
            value, "target_true_altitude_deg"
        ),
        relative_solar_azimuth_deg=_domain_interval(
            value, "relative_solar_azimuth_deg"
        ),
        refraction=value["refraction"],
        outside_domain=value["outside_domain"],
        no_extrapolation=True,
    )


def _validate_axes(
    value: dict[str, Any],
    domain: VisibilityDataPackDomain,
) -> tuple[
    tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]],
    tuple[tuple[float, ...], tuple[float, ...]],
]:
    if value.get("schema") != _AXES_SCHEMA:
        _load_failure(
            "visibility_data_pack_incompatible",
            "axes schema differs",
        )
    radiance = _require_dict(value.get("radiance"), "radiance axes")
    axes = _require_dict(radiance.get("axes"), "radiance axis values")
    if (
        radiance.get("coordinate_order")
        != [
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
        ]
        or radiance.get("linearization_order")
        != "row_major_last_axis_fastest"
        or set(axes)
        != {
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
        }
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "radiance axes differ",
        )
    solar = _strict_axis(axes["solar_center_altitude_deg"], "solar axis")
    target = _strict_axis(axes["target_true_altitude_deg"], "target axis")
    azimuth = _strict_axis(
        axes["relative_solar_azimuth_deg"], "azimuth axis"
    )
    if radiance.get("value_count") != len(solar) * len(target) * len(azimuth):
        _load_failure(
            "visibility_data_pack_incompatible",
            "radiance value count differs",
        )
    if (
        (solar[0], solar[-1]) != domain.solar_center_altitude_deg
        or (target[0], target[-1]) != domain.target_true_altitude_deg
        or (azimuth[0], azimuth[-1])
        != domain.relative_solar_azimuth_deg
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "radiance axes do not span the declared domain",
        )

    direct = _require_dict(
        value.get("direct_extinction"),
        "direct-extinction axes",
    )
    direct_target = _strict_axis(
        direct.get("target_true_altitude_deg"),
        "direct target axis",
    )
    spectral = _require_dict(
        direct.get("spectral_bins"),
        "direct spectral bins",
    )
    if (
        direct.get("linearization_order")
        != "row_major_target_altitude_then_spectral_bin_fastest"
        or spectral.get("coordinate") != "bin_start_vacuum_nm"
        or spectral.get("start_nm") != 380.0
        or spectral.get("width_nm") != 1.0
        or spectral.get("count") != 400
        or direct.get("value_count") != len(direct_target) * 400
        or (direct_target[0], direct_target[-1])
        != domain.target_true_altitude_deg
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "direct-extinction axes differ",
        )
    wavelengths = tuple(380.0 + index for index in range(400))
    return (solar, target, azimuth), (direct_target, wavelengths)


def _validate_error_envelope(value: dict[str, Any]) -> dict[str, float]:
    if value.get("schema") != _ERROR_ENVELOPE_SCHEMA or value.get(
        "accepted"
    ) is not True:
        _load_failure(
            "visibility_data_pack_incompatible",
            "error envelope is not admitted",
        )
    summaries = _require_dict(
        value.get("error_summaries"),
        "error summaries",
    )
    photopic = _require_dict(
        summaries.get("photopic_response"),
        "photopic error summary",
    )
    scotopic = _require_dict(
        summaries.get("scotopic_response"),
        "scotopic error summary",
    )
    direct = _require_dict(
        summaries.get("direct_extinction_1nm"),
        "direct-extinction error summary",
    )
    storage = _require_dict(
        value.get("storage_analysis"),
        "storage analysis",
    )
    downstream = _require_dict(
        value.get("downstream_error_contract"),
        "downstream error contract",
    )
    diagnostic = _require_dict(
        _require_dict(
            value.get("diagnostic_contract"),
            "diagnostic contract",
        ).get("monochromatic_reference"),
        "monochromatic diagnostic",
    )
    if (
        downstream.get("per_cell_solver_uncertainty_required") is not True
        or downstream.get("limiting_magnitude_propagation_owner")
        != "phase2_single_epoch_truth"
        or downstream.get("event_time_propagation_owner")
        != "phase3_event_solver"
        or downstream.get("background_interpolation_error_unit")
        != "surface_brightness_magnitude"
        or downstream.get("direct_extinction_error_unit")
        != "magnitude"
        or downstream.get(
            "phase1_does_not_fabricate_downstream_derivatives"
        )
        is not True
        or storage.get("selected_representation")
        != "little_endian_ieee754_binary32"
        or storage.get(
            "storage_error_is_separate_from_solver_and_interpolation_error"
        )
        is not True
        or diagnostic.get("surface_shipped_in_data_pack") is not False
        or diagnostic.get("surface_used_by_runtime_interpolation") is not False
        or diagnostic.get("admission_gate") is not False
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "error-envelope policy differs",
        )
    result = {
        "photopic_max": _nonnegative_finite(
            photopic.get("maximum_error_mag"),
            "photopic maximum error",
        ),
        "photopic_p95": _nonnegative_finite(
            photopic.get("p95_error_mag"),
            "photopic p95 error",
        ),
        "scotopic_max": _nonnegative_finite(
            scotopic.get("maximum_error_mag"),
            "scotopic maximum error",
        ),
        "scotopic_p95": _nonnegative_finite(
            scotopic.get("p95_error_mag"),
            "scotopic p95 error",
        ),
        "direct_max": _nonnegative_finite(
            direct.get("maximum_error_mag"),
            "direct maximum error",
        ),
        "direct_p95": _nonnegative_finite(
            direct.get("p95_error_mag"),
            "direct p95 error",
        ),
        "storage_max": _nonnegative_finite(
            storage.get("float32_maximum_error_mag"),
            "float32 maximum error",
        ),
    }
    if (
        result["photopic_p95"] > result["photopic_max"]
        or result["scotopic_p95"] > result["scotopic_max"]
        or result["direct_p95"] > result["direct_max"]
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "p95 error exceeds its declared maximum",
        )
    return result


def _validate_provenance(
    value: dict[str, Any],
    manifest: dict[str, Any],
    compatibility_identity: _CompatibilityIdentity,
) -> tuple[str, ...]:
    if value.get("schema") != _PROVENANCE_SCHEMA:
        _load_failure(
            "visibility_data_pack_incompatible",
            "provenance schema differs",
        )
    excluded = value.get("excluded_source_files")
    if not isinstance(excluded, list) or not {
        "CIE_source_tables",
        "libRadtran_binary",
        "libRadtran_profiles",
        "libRadtran_source",
        "REPTRAN_files",
    }.issubset(excluded):
        _load_failure(
            "visibility_data_pack_incompatible",
            "source-file exclusion receipt differs",
        )
    sources = _require_dict(
        value.get("scientific_sources"),
        "scientific sources",
    )
    photopic = _require_dict(sources.get("CIE_photopic"), "CIE photopic")
    scotopic = _require_dict(sources.get("CIE_scotopic"), "CIE scotopic")
    libradtran = _require_dict(sources.get("libRadtran"), "libRadtran")
    reptran = _require_dict(sources.get("REPTRAN_module"), "REPTRAN")
    if (
        photopic.get("dataset_doi") != "10.25039/CIE.DS.dktna2s3"
        or scotopic.get("dataset_doi") != "10.25039/CIE.DS.gr6w4b5g"
        or libradtran.get("version") != "2.0.6"
        or reptran.get("module_id") != "libradtran_reptran_2024_all"
        or reptran.get("resolution") != "fine"
        or value.get("source_artifact") is None
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "scientific source identity differs",
        )
    provenance_source = _require_dict(
        value.get("source_artifact"),
        "provenance source artifact",
    )
    manifest_source = _require_dict(
        manifest.get("source_artifact"),
        "manifest source artifact",
    )
    source_spec_id = manifest_source.get("spec_id")
    if not isinstance(source_spec_id, str) or not source_spec_id:
        _load_failure(
            "visibility_data_pack_incompatible",
            "source-artifact specification identity differs",
        )
    source_manifest = _require_dict(
        manifest_source.get("manifest"),
        "manifest source-artifact manifest",
    )
    _require_sha256(
        source_manifest.get("sha256"),
        "source-artifact manifest SHA-256",
    )
    if (
        provenance_source.get("spec_id") != manifest_source.get("spec_id")
        or provenance_source.get("manifest")
        != manifest_source.get("manifest")
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "source-artifact provenance differs",
        )
    source_ids = (
        f"CIE_photopic:{photopic['dataset_doi']}",
        f"CIE_scotopic:{scotopic['dataset_doi']}",
        f"libRadtran:{libradtran['version']}",
        f"REPTRAN:{reptran['module_id']}",
    )
    if compatibility_identity.pack_minor_version == 0:
        return source_ids

    payne = _require_dict(
        sources.get("Payne_planetary_spectra"),
        "Payne planetary spectra",
    )
    mallama = _require_dict(
        sources.get("Mallama_planetary_photometry"),
        "Mallama planetary photometry",
    )
    solar = _require_dict(
        sources.get("target_profile_solar_spectrum"),
        "target-profile solar spectrum",
    )
    target_artifact = _require_dict(
        value.get("target_profile_artifact"),
        "target-profile artifact",
    )
    manifest_target_artifact = _require_dict(
        manifest.get("target_profile_artifact"),
        "manifest target-profile artifact",
    )
    target_sha256 = _require_sha256(
        target_artifact.get("target_profile_sha256"),
        "target-profile SHA-256",
    )
    if (
        payne.get("record_doi") != "10.5281/zenodo.17470005"
        or payne.get("publication_doi") != "10.3847/PSJ/ae2feb"
        or payne.get("license") != "CC-BY-4.0"
        or mallama.get("publication_doi")
        != "10.1016/j.icarus.2016.09.023"
        or mallama.get("arxiv_id") != "1609.05048"
        or solar.get("source_id")
        != "libRadtran:2.0.6:data/solar_flux/atlas_plus_modtran"
        or solar.get("sha256")
        != "432600ef415706c401a4c0e17c6b733a631f1556a78c3da32e936830288b414b"
        or target_artifact.get("spec_id")
        != manifest_target_artifact.get("spec_id")
        or target_sha256
        != manifest_target_artifact.get("target_profile_sha256")
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "planetary target-profile provenance differs",
        )
    return source_ids + (
        "Payne_planetary_spectra:10.5281/zenodo.17470005",
        "Mallama_planetary_photometry:10.1016/j.icarus.2016.09.023",
        "target_profile_solar_spectrum:libRadtran:2.0.6",
    )


def _validate_notice_and_readme(
    directory: Path,
    file_roles: dict[str, str],
    compatibility_identity: _CompatibilityIdentity,
) -> None:
    try:
        notice = (directory / file_roles["notice"]).read_text(
            encoding="utf-8"
        )
        readme = (directory / file_roles["readme"]).read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        _load_failure(
            "visibility_data_pack_incompatible",
            f"notice or README cannot be read: {exc}",
        )
    required_notice = (
        "Creative Commons",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        "10.25039/CIE.DS.dktna2s3",
        "10.25039/CIE.DS.gr6w4b5g",
        "libRadtran 2.0.6",
        "No libRadtran source",
    )
    if any(fragment not in notice for fragment in required_notice):
        _load_failure(
            "visibility_data_pack_incompatible",
            "licensing notice is incomplete",
        )
    if compatibility_identity.pack_minor_version == 1 and any(
        fragment not in notice
        for fragment in (
            "10.5281/zenodo.17470005",
            "10.3847/PSJ/ae2feb",
            "10.1016/j.icarus.2016.09.023",
            "CC BY 4.0",
            "No libRadtran source",
        )
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "planetary-profile licensing notice is incomplete",
        )
    if (
        "explicit caller-supplied directory path" not in readme
        or "No component may download" not in readme
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            "runtime README boundary is incomplete",
        )


def _read_f32_table(
    path: Path,
    expected_count: int,
    label: str,
    *,
    strictly_positive: bool,
) -> tuple[float, ...]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _load_failure(
            "visibility_data_pack_checksum_mismatch",
            f"{label} cannot be read: {exc}",
        )
    if len(raw) != expected_count * 4:
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} byte count differs",
        )
    values = struct.unpack(f"<{expected_count}f", raw)
    if any(
        not math.isfinite(value)
        or (value <= 0.0 if strictly_positive else value < 0.0)
        for value in values
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} contains an inadmissible value",
        )
    return tuple(float(value) for value in values)


def _trilinear_log10_with_rse_bound(
    values: tuple[float, ...],
    relative_standard_errors: tuple[float, ...],
    shape: tuple[int, int, int],
    brackets: tuple[
        tuple[int, int, float],
        tuple[int, int, float],
        tuple[int, int, float],
    ],
) -> tuple[float, float]:
    weighted_log10 = 0.0
    total_weight = 0.0
    rse_bound = 0.0
    for solar_index, solar_weight in _bracket_weights(brackets[0]):
        for target_index, target_weight in _bracket_weights(brackets[1]):
            for azimuth_index, azimuth_weight in _bracket_weights(
                brackets[2]
            ):
                weight = solar_weight * target_weight * azimuth_weight
                if weight == 0.0:
                    continue
                index = (
                    (solar_index * shape[1] + target_index) * shape[2]
                    + azimuth_index
                )
                weighted_log10 += weight * math.log10(values[index])
                total_weight += weight
                rse_bound = max(rse_bound, relative_standard_errors[index])
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-15):
        raise AssertionError("trilinear interpolation weights do not sum to 1")
    return 10.0**weighted_log10, rse_bound


def _bracket_weights(
    bracket: tuple[int, int, float],
) -> tuple[tuple[int, float], ...]:
    low, high, fraction = bracket
    if low == high:
        return ((low, 1.0),)
    return ((low, 1.0 - fraction), (high, fraction))


def _axis_bracket(
    axis: tuple[float, ...],
    value: float,
    reason: str,
    label: str,
    *,
    displayed_domain: tuple[float, float] | None = None,
    displayed_value: float | None = None,
) -> tuple[int, int, float]:
    if value < axis[0] or value > axis[-1] or not math.isfinite(value):
        domain = displayed_domain or (axis[0], axis[-1])
        shown = value if displayed_value is None else displayed_value
        raise VisibilityDataPackDomainError(
            reason,
            f"{label}={shown} is outside [{domain[0]}, {domain[1]}]",
        )
    position = bisect.bisect_left(axis, value)
    if position < len(axis) and value == axis[position]:
        return position, position, 0.0
    low = position - 1
    high = position
    fraction = (value - axis[low]) / (axis[high] - axis[low])
    return low, high, fraction


def _strict_axis(raw: Any, label: str) -> tuple[float, ...]:
    if not isinstance(raw, list) or len(raw) < 2:
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} must contain at least two values",
        )
    values: list[float] = []
    for raw_value in raw:
        if isinstance(raw_value, bool) or not isinstance(
            raw_value, (int, float)
        ):
            _load_failure(
                "visibility_data_pack_incompatible",
                f"{label} contains a nonnumeric value",
            )
        value = float(raw_value)
        if not math.isfinite(value):
            _load_failure(
                "visibility_data_pack_incompatible",
                f"{label} contains a nonfinite value",
            )
        values.append(value)
    if any(right <= left for left, right in zip(values, values[1:])):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} is not strictly increasing",
        )
    return tuple(values)


def _fixed_domain_string(value: dict[str, Any], key: str) -> str:
    raw = value.get(key)
    if (
        not isinstance(raw, list)
        or len(raw) != 1
        or not isinstance(raw[0], str)
        or not raw[0]
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{key} is not a fixed named domain",
        )
    return raw[0]


def _fixed_domain_number(value: dict[str, Any], key: str) -> float:
    raw = value.get(key)
    if (
        not isinstance(raw, list)
        or len(raw) != 2
        or raw[0] != raw[1]
    ):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{key} is not a fixed numeric domain",
        )
    return _finite_manifest_number(raw[0], key)


def _domain_interval(
    value: dict[str, Any],
    key: str,
) -> tuple[float, float]:
    raw = value.get(key)
    if not isinstance(raw, list) or len(raw) != 2:
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{key} is not an interval",
        )
    lower = _finite_manifest_number(raw[0], f"{key} lower")
    upper = _finite_manifest_number(raw[1], f"{key} upper")
    if upper < lower:
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{key} interval is reversed",
        )
    return lower, upper


def _finite_manifest_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} is not numeric",
        )
    number = float(value)
    if not math.isfinite(number):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} is not finite",
        )
    return number


def _semantic_version(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, str):
        return (-1, -1, -1)
    parts = value.split(".")
    if (
        len(parts) != 3
        or any(not part.isdecimal() for part in parts)
        or any(len(part) > 1 and part.startswith("0") for part in parts)
    ):
        return (-1, -1, -1)
    return int(parts[0]), int(parts[1]), int(parts[2])


def _finite_coordinate(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisibilityDataPackDomainError(
            "criterion_out_of_domain",
            f"{label} must be numeric",
        )
    number = float(value)
    if not math.isfinite(number):
        raise VisibilityDataPackDomainError(
            "criterion_out_of_domain",
            f"{label} must be finite",
        )
    return number


def _nonnegative_finite(value: Any, label: str) -> float:
    number = _finite_manifest_number(value, label)
    if number < 0.0:
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} must be nonnegative",
        )
    return number


def _read_json_dict(
    path: Path,
    label: str,
    reason: str,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _load_failure(reason, f"{label} cannot be decoded: {exc}")
    if not isinstance(value, dict):
        _load_failure(reason, f"{label} must be a JSON object")
    return value


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} must be an object",
        )
    return value


def _require_sha256(
    value: Any,
    label: str,
    *,
    error_type: type[Exception] | None = None,
) -> str:
    valid = (
        isinstance(value, str)
        and len(value) == 64
        and not (set(value) - _HEX_DIGITS)
    )
    if not valid:
        if error_type is ValueError:
            raise ValueError(f"{label} must be a lowercase SHA-256 digest")
        _load_failure(
            "visibility_data_pack_incompatible",
            f"{label} is not a lowercase SHA-256 digest",
        )
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        _load_failure(
            "visibility_data_pack_checksum_mismatch",
            f"{path.name} cannot be hashed: {exc}",
        )
    return digest.hexdigest()


def _load_failure(reason: str, detail: str) -> None:
    raise VisibilityDataPackLoadError(reason, detail)
