#!/usr/bin/env python3
"""Audit the external ESO/Jones source boundary for Phase 4 visibility.

This script reads an explicitly supplied official SM-01 archive.  It never
downloads, extracts, compiles, or executes GPL code.  Its output is a source
receipt and an admission-boundary audit, not a runtime moonlight data pack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_source_audit_spec.json"
)
SPEC_SCHEMA = "moira.visibility-jones-source-audit-spec/v1"
SPEC_ID = "physical-heliacal-phase4-jones-source-audit-2026-07-31"
CHECKPOINT_SCHEMA = "moira.visibility-jones-source-audit-checkpoint/v1"
CHECKPOINT_ID = "physical-heliacal-phase4-jones-source-audit-2026-07-31"
EXPECTED_ARCHIVE_BYTES = 431651392
EXPECTED_ARCHIVE_SHA256 = (
    "e09b1d62c8af212486f50097fe76d9dc"
    "bb242f4fbadf720a4a85be361cc9116b"
)
EXPECTED_MODEL_ID = "jones_paranal_scattered_moonlight_2013_v1"
EXPECTED_MEMBER_SHA256 = {
    "SM-01/README.txt": (
        "66cd5f8b7c8b55a2b6f50507a55fdef"
        "175d7c9196797061c3ded03535dbd4b95"
    ),
    "SM-01/sm-01_mod2/src/sm_scatmoonlight.c": (
        "686dcce3e4aadf41785b9b26bdeeee858"
        "c730030969c7dd4045748527985a5ea"
    ),
    "SM-01/sm-01_mod2/src/sm_scatmoonlight.h": (
        "8ade158bee9638dd6bd1cfc0d44191f4"
        "d9dcd131b5bfb65c82c04ca875839ec6"
    ),
    "SM-01/sm-01_mod2/src/sm_skyemcomp.c": (
        "eaa20b583c24f81cf15f7f63ac561240"
        "3fbfb939cbe933f43df24bb56573adc6"
    ),
    "SM-01/sm-01_mod2/src/sm_skyemcomp.h": (
        "3f19ce3648aa06210407f7be8f4d5417"
        "42c2008491d8a9a27ea8a31950c77264"
    ),
    "SM-01/sm-01_mod2/data/moonalbedo.dat": (
        "86b9f9860fabb283de6659aabee895918"
        "6dc03e9d081aaa7c2761c2869ff16cc"
    ),
    "SM-01/sm-01_mod2/data/mie_paranal_ref.dat": (
        "16bb135bb7972be955c0bcae19f8fb6f"
        "d7781696137bb7d1e089ea5a5beb1954"
    ),
    "SM-01/sm-01_mod2/data/mie_m15s1.dat": (
        "dba01f9b49ddf9a547bccc7eaca013be"
        "c1e4b1d8e081ec5ec4dd284ea7ec425e"
    ),
    "SM-01/sm-01_mod2/data/dscatcor_m15s1.dat": (
        "09fc0a6f81cf630099d008a96b82a72d"
        "f1296bbed12f00e633c98b8cd480efec"
    ),
    "SM-01/sm-01_mod2/data/sscatcor_m15s1.dat": (
        "2bf48a71e007bc557bd088d53ede15e97"
        "163d9154f19b1e411b104c38c4a18b8"
    ),
    "SM-01/sm-01_mod2/data/multiscat_m15s1.dat": (
        "87534ff402b103197bba5e34742bd5972"
        "3f04121866a224bcb34eed45d65cd38"
    ),
    "SM-01/sm-01_mod2/data/solspec_ext.dat": (
        "0f75353a72cfd7f1b314652f47aa9edf"
        "f33434be5154bdfd590e2b5b2926933d"
    ),
    "SM-01/sm-01_mod2/data/o3trans.dat": (
        "cb06c173f393d6d55e3c39551665abb8"
        "f5d6c1a846cd0fd739a15d0155f94502"
    ),
    "SM-01/sm-01_mod2/test/test_skymodel_etc.par": (
        "294ddff66df11b0406e61a82531e384a"
        "2641a4c2bafdc763887201b3e34c94cd"
    ),
    "SM-01/sm-01_mod2/test/test_instrument_etc.par": (
        "da6b60b60bf8679fae1aec3050453e7c"
        "326067513ade6de19ebfbf91b98299ce"
    ),
    "SM-01/sm-01_mod2/test/sm_filenames.dat": (
        "0cef2328ef50c5fb5fafc3d24c80441f"
        "836bdb330695056f8993756ae1ddfbd0"
    ),
    "SM-01/sm-01_mod2/test/test_radspec.fits": (
        "70e7b4526c6162342fa13100fea51eabb"
        "b8c37119467a272dce88730cfd0b917"
    ),
    "SM-01/sm-01_mod2/test/test_transspec.fits": (
        "d26dc93e0c69bb235c435daea5d98fe7"
        "c3fd79a8f0585b69576359ff7a6e5caf"
    ),
}
EXPECTED_SKYCALC_FITS_BYTES = 80640
EXPECTED_SKYCALC_FITS_SHA256 = (
    "12d7625e1ec1afc718928d873fdb0001"
    "d3fd800b19d33a6c5dc2ce135dbbc230"
)
EXPECTED_SKYCALC_COMPONENT_SHA256 = (
    "8e15e62b5aa5cab32961f3be7ba300f4"
    "6217d20614e91bdc131aa8ee8b2e1c29"
)
_FITS_BLOCK_BYTES = 2880
_FITS_CARD_BYTES = 80


class JonesSourceAuditError(ValueError):
    """Raised when the external source differs from the frozen receipt."""


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
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


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JonesSourceAuditError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesSourceAuditError(f"{label} must be a JSON object")
    return payload


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise JonesSourceAuditError(
            f"{label} must be a lowercase SHA-256"
        )
    return value


def _require_safe_member_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise JonesSourceAuditError("source member path must be nonempty")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise JonesSourceAuditError(
            f"source member path is not canonical: {value!r}"
        )
    return value


def validate_spec(spec: dict[str, Any]) -> None:
    """Validate the independently frozen Phase 4 source-audit contract."""

    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("spec_id") != SPEC_ID
        or spec.get("status")
        != "source_audit_and_artifact_contract_not_runtime_model"
    ):
        raise JonesSourceAuditError("source-audit spec identity differs")

    model = spec.get("model_contract")
    if (
        not isinstance(model, dict)
        or model.get("candidate_model_id") != EXPECTED_MODEL_ID
        or model.get("admission_status") != "not_admitted"
        or model.get("implementation_method")
        != "independent_offline_spectral_artifact"
        or model.get("silent_fallback_allowed") is not False
    ):
        raise JonesSourceAuditError("candidate model contract differs")

    boundary = spec.get("runtime_boundary")
    if boundary != {
        "engine_changes_authorized": False,
        "public_api_changes_authorized": False,
        "production_data_pack_authorized": False,
        "runtime_dependency_on_eso_code": False,
        "runtime_dependency_on_libradtran": False,
        "network_dependency": False,
        "automatic_download_allowed": False,
        "external_source_bytes_redistributed": False,
    }:
        raise JonesSourceAuditError("runtime boundary must remain closed")

    authority = spec.get("primary_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("doi") != "10.1051/0004-6361/201322433"
        or authority.get("rolo_empirical_phase_domain_deg")
        != [1.55, 97.0]
        or authority.get("paper_extrapolates_rolo_to_deg") != 180.0
        or authority.get("first_moira_admission_extrapolates_rolo")
        is not False
    ):
        raise JonesSourceAuditError("primary-authority boundary differs")

    package = spec.get("eso_source_package")
    if (
        not isinstance(package, dict)
        or package.get("archive_bytes") != EXPECTED_ARCHIVE_BYTES
        or package.get("archive_sha256") != EXPECTED_ARCHIVE_SHA256
        or package.get("license") != "GPL-2.0-or-later"
    ):
        raise JonesSourceAuditError("ESO source-package receipt differs")
    members = package.get("required_members")
    if not isinstance(members, list) or not members:
        raise JonesSourceAuditError("required source members are absent")
    paths: list[str] = []
    for receipt in members:
        if not isinstance(receipt, dict) or set(receipt) != {
            "path",
            "bytes",
            "sha256",
            "role",
        }:
            raise JonesSourceAuditError("source member receipt shape differs")
        path = _require_safe_member_path(receipt.get("path"))
        paths.append(path)
        if (
            not isinstance(receipt.get("bytes"), int)
            or receipt["bytes"] <= 0
            or not isinstance(receipt.get("role"), str)
            or not receipt["role"]
        ):
            raise JonesSourceAuditError(
                f"source member receipt is invalid: {path}"
            )
        _require_sha256(receipt.get("sha256"), f"{path} sha256")
    if len(paths) != len(set(paths)):
        raise JonesSourceAuditError("source member paths must be unique")
    if set(paths) != set(EXPECTED_MEMBER_SHA256):
        raise JonesSourceAuditError(
            "required source-member inventory differs"
        )
    for path, sha256 in EXPECTED_MEMBER_SHA256.items():
        matching = [
            receipt
            for receipt in members
            if receipt["path"] == path
        ]
        if len(matching) != 1 or matching[0]["sha256"] != sha256:
            raise JonesSourceAuditError(
                f"governing source member differs: {path}"
            )

    fixture = spec.get("source_owned_regression_fixture")
    if (
        not isinstance(fixture, dict)
        or fixture.get("derived_lunar_phase_angle_deg") != 102.1
        or fixture.get("inside_first_moira_admission_domain") is not False
        or fixture.get("optical_signature_sha256")
        != "ba33c681486a24b4703120c2dc5ab0cb"
        "7df3ed8201b44707629fa88f5a1a0b52"
    ):
        raise JonesSourceAuditError(
            "source-owned regression boundary differs"
        )

    capture = spec.get("operational_comparison_capture")
    if (
        not isinstance(capture, dict)
        or capture.get("skycalc_version") != "2.0.9"
        or capture.get("fits_bytes") != EXPECTED_SKYCALC_FITS_BYTES
        or capture.get("fits_sha256") != EXPECTED_SKYCALC_FITS_SHA256
        or capture.get("component_signature_sha256")
        != EXPECTED_SKYCALC_COMPONENT_SHA256
        or capture.get("component_column") != "flux_sml"
        or capture.get("derived_lunar_phase_angle_deg") != 50.0
        or capture.get("role")
        != "versioned_source_owned_operational_comparison_not_independent_oracle"
        or capture.get("all_other_emission_components_zero") is not True
        or capture.get("total_flux_equals_scattered_moonlight") is not True
    ):
        raise JonesSourceAuditError(
            "operational comparison-capture boundary differs"
        )

    domain = spec.get("first_admission_domain")
    if (
        not isinstance(domain, dict)
        or domain.get("site_id") != "cerro_paranal_jones_2013"
        or domain.get("site_transfer_allowed") is not False
        or domain.get("observer_altitude_m") != 2640.0
        or domain.get("surface_pressure_hpa") != 744.0
        or domain.get("aerosol_single_scattering_albedo") != 0.97
        or domain.get("lunar_phase_angle_deg") != [1.55, 97.0]
        or domain.get("moon_earth_distance_ratio") != [0.91, 1.08]
        or domain.get("target_true_altitude_deg") != [0.25, 90.0]
        or domain.get("moon_true_altitude_deg") != [0.0, 90.0]
        or domain.get("relative_moon_azimuth_deg") != [0.0, 180.0]
        or domain.get("spectral_wavelength_nm") != [380.0, 780.0]
        or domain.get("waxing_and_waning_are_distinct") is not True
        or domain.get("geometry_consistency_required") is not True
        or domain.get("phase_extrapolation_policy") != "rejected"
        or domain.get("outside_domain_policy") != "not_evaluable"
        or domain.get("subhorizon_moon_policy")
        != "not_evaluable_until_separately_admitted"
        or domain.get("site_substitution_policy") != "rejected"
    ):
        raise JonesSourceAuditError("first admission domain differs")

    artifact = spec.get("independent_artifact_contract")
    expected_axes = [
        "target_true_altitude_deg",
        "moon_true_altitude_deg",
        "relative_moon_azimuth_deg",
        "lunar_phase_angle_deg",
        "waxing_state",
        "moon_earth_distance_ratio",
    ]
    if (
        not isinstance(artifact, dict)
        or artifact.get("required_coordinate_axes") != expected_axes
        or artifact.get("artifact_schema")
        != "moira.visibility-jones-spectral-moonlight-artifact/v1"
        or artifact.get("artifact_status") != "required_not_yet_generated"
        or artifact.get("external_generator")
        != {
            "name": "libRadtran",
            "version": "2.0.6",
            "solver": "MYSTIC",
            "geometry": "spherical_one_dimensional_atmosphere",
            "archive_sha256": (
                "64930cc40b6e4a37aa220520974d330fc"
                "1563796f466a649b2238131f2d69840"
            ),
            "runtime_dependency": False,
        }
        or artifact.get("fixed_environment_receipts")
        != [
            "site_identity",
            "observer_altitude",
            "pressure_profile",
            "molecular_profile",
            "aerosol_extinction",
            "aerosol_phase_function",
            "single_scattering_albedo",
            "ozone_column",
            "ground_reflectance",
        ]
        or artifact.get("required_spectral_inputs")
        != [
            "source_locked_solar_spectrum",
            "source_locked_lunar_albedo_model",
            "photopic_response",
            "scotopic_response",
        ]
        or artifact.get("required_outputs")
        != [
            "spectral_radiance",
            "photopic_luminance_cd_m2",
            "scotopic_luminance_cd_m2",
            "solver_numerical_error",
            "interpolation_error",
            "storage_error",
        ]
        or artifact.get("required_validation_classes")
        != [
            "fixed_seed_repeatability",
            "photon_count_convergence",
            "grid_convergence",
            "source_owned_operational_comparison",
            "independent_geometry_holdout",
            "component_isolation",
            "domain_rejection",
        ]
        or artifact.get("official_eso_code_used_as_generator") is not False
        or artifact.get("official_eso_code_used_as_independent_oracle")
        is not False
        or artifact.get("production_admission_allowed") is not False
        or artifact.get("acceptance_thresholds_status")
        != "pilot_results_required_before_freeze"
    ):
        raise JonesSourceAuditError(
            "independent artifact contract differs"
        )

    sensitivity = spec.get("atmospheric_sensitivity_contract")
    if (
        not isinstance(sensitivity, dict)
        or sensitivity.get("current_runtime_pack_atmosphere_axes") != []
        or sensitivity.get(
            "current_pack_can_produce_atmospheric_sensitivity_envelope"
        )
        is not False
        or sensitivity.get("required_method")
        != "separate_immutable_admitted_scenario_packs"
        or sensitivity.get("scenario_event_evaluation")
        != "rerun_complete_event_search_per_pack"
        or sensitivity.get("interval_composition")
        != "hull_only_when_every_scenario_has_comparable_owned_event"
        or sensitivity.get("missing_or_noncomparable_scenario_policy")
        != "typed_not_bounded"
        or sensitivity.get("interpolation_between_scenario_packs_allowed")
        is not False
        or sensitivity.get("probabilistic_confidence_claimed") is not False
    ):
        raise JonesSourceAuditError(
            "atmospheric sensitivity boundary differs"
        )


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = _load_json(path, "Jones source-audit spec")
    validate_spec(spec)
    return spec


def inspect_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = load_spec(path)
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "candidate_model_id": spec["model_contract"][
            "candidate_model_id"
        ],
        "admission_status": spec["model_contract"]["admission_status"],
        "required_source_member_count": len(
            spec["eso_source_package"]["required_members"]
        ),
        "first_admission_site_id": spec["first_admission_domain"][
            "site_id"
        ],
        "first_admission_phase_domain_deg": spec[
            "first_admission_domain"
        ]["lunar_phase_angle_deg"],
        "source_fixture_inside_admission_domain": spec[
            "source_owned_regression_fixture"
        ]["inside_first_moira_admission_domain"],
        "artifact_status": spec["independent_artifact_contract"][
            "artifact_status"
        ],
        "atmospheric_sensitivity_available": spec[
            "atmospheric_sensitivity_contract"
        ]["current_pack_can_produce_atmospheric_sensitivity_envelope"],
        "runtime_dependency": False,
    }


def _parse_parameter_file(payload: bytes) -> dict[str, str | float]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JonesSourceAuditError(
            "source parameter file is not UTF-8"
        ) from exc
    result: dict[str, str | float] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise JonesSourceAuditError(
                f"source parameter line is malformed: {raw_line!r}"
            )
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key in result:
            raise JonesSourceAuditError(
                f"source parameter key is invalid: {key!r}"
            )
        try:
            result[key] = float(value)
        except ValueError:
            result[key] = value
    return result


def _parse_fits_scalar(raw: str) -> object:
    value = raw.lstrip()
    if value.startswith("'"):
        characters: list[str] = []
        index = 1
        while index < len(value):
            if value[index] != "'":
                characters.append(value[index])
                index += 1
                continue
            if index + 1 < len(value) and value[index + 1] == "'":
                characters.append("'")
                index += 2
                continue
            return "".join(characters).strip()
        raise JonesSourceAuditError("FITS string card is malformed")
    value = value.split("/", 1)[0].strip()
    if value in {"T", "F"}:
        return value == "T"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value.replace("D", "E"))
        except ValueError as exc:
            raise JonesSourceAuditError(
                f"unsupported FITS scalar: {value!r}"
            ) from exc


def _fits_header(
    payload: bytes,
    offset: int,
) -> tuple[dict[str, object], tuple[str, ...], int]:
    if offset % _FITS_BLOCK_BYTES:
        raise JonesSourceAuditError("FITS header is not block aligned")
    values: dict[str, object] = {}
    comments: list[str] = []
    cursor = offset
    end_seen = False
    while cursor + _FITS_CARD_BYTES <= len(payload):
        card = payload[cursor : cursor + _FITS_CARD_BYTES]
        try:
            text = card.decode("ascii")
        except UnicodeDecodeError as exc:
            raise JonesSourceAuditError("FITS card is not ASCII") from exc
        cursor += _FITS_CARD_BYTES
        key = text[:8].strip()
        if key == "END":
            end_seen = True
            break
        if key == "COMMENT":
            comments.append(text[8:].strip())
        elif key and text[8:10] == "= ":
            if key in values:
                raise JonesSourceAuditError(
                    f"duplicate FITS header key: {key}"
                )
            values[key] = _parse_fits_scalar(text[10:])
    if not end_seen:
        raise JonesSourceAuditError("FITS header lacks END")
    next_offset = (
        (cursor + _FITS_BLOCK_BYTES - 1)
        // _FITS_BLOCK_BYTES
        * _FITS_BLOCK_BYTES
    )
    if next_offset > len(payload):
        raise JonesSourceAuditError("FITS header is truncated")
    return values, tuple(comments), next_offset


def _fits_hdu_data_bytes(header: dict[str, object]) -> int:
    bitpix = header.get("BITPIX")
    naxis = header.get("NAXIS")
    if not isinstance(bitpix, int) or not isinstance(naxis, int):
        raise JonesSourceAuditError("FITS dimensional header is incomplete")
    if naxis < 0:
        raise JonesSourceAuditError("FITS NAXIS is invalid")
    elements = 0 if naxis == 0 else 1
    for index in range(1, naxis + 1):
        length = header.get(f"NAXIS{index}")
        if not isinstance(length, int) or length < 0:
            raise JonesSourceAuditError("FITS axis length is invalid")
        elements *= length
    pcount = header.get("PCOUNT", 0)
    gcount = header.get("GCOUNT", 1)
    if not isinstance(pcount, int) or not isinstance(gcount, int):
        raise JonesSourceAuditError("FITS group header is invalid")
    return (abs(bitpix) // 8 * elements + pcount) * gcount


def _next_fits_hdu_offset(header_end: int, data_bytes: int) -> int:
    return (
        header_end
        + data_bytes
        + _FITS_BLOCK_BYTES
        - 1
    ) // _FITS_BLOCK_BYTES * _FITS_BLOCK_BYTES


def _fits_binary_table(
    payload: bytes,
) -> tuple[
    dict[str, object],
    tuple[str, ...],
    dict[str, tuple[float, ...]],
]:
    primary, _, primary_data = _fits_header(payload, 0)
    extension_offset = _next_fits_hdu_offset(
        primary_data,
        _fits_hdu_data_bytes(primary),
    )
    extension, comments, data_offset = _fits_header(
        payload,
        extension_offset,
    )
    if extension.get("XTENSION") != "BINTABLE":
        raise JonesSourceAuditError("FITS extension is not BINTABLE")
    row_bytes = extension.get("NAXIS1")
    row_count = extension.get("NAXIS2")
    field_count = extension.get("TFIELDS")
    if (
        not isinstance(row_bytes, int)
        or not isinstance(row_count, int)
        or not isinstance(field_count, int)
        or row_bytes <= 0
        or row_count <= 0
        or field_count <= 0
    ):
        raise JonesSourceAuditError("FITS binary-table shape is invalid")
    if extension.get("PCOUNT", 0) != 0 or extension.get("GCOUNT", 1) != 1:
        raise JonesSourceAuditError(
            "FITS binary table uses unsupported groups or heap data"
        )
    columns: list[tuple[str, int]] = []
    column_names: set[str] = set()
    column_offset = 0
    for index in range(1, field_count + 1):
        name = extension.get(f"TTYPE{index}")
        form = extension.get(f"TFORM{index}")
        if not isinstance(name, str) or form != "1D":
            raise JonesSourceAuditError(
                "source FITS audit supports only named 1D float64 columns"
            )
        if name in column_names:
            raise JonesSourceAuditError(
                f"duplicate FITS binary-table column: {name}"
            )
        column_names.add(name)
        columns.append((name, column_offset))
        column_offset += 8
    if column_offset != row_bytes:
        raise JonesSourceAuditError("FITS row width differs from columns")
    data_end = data_offset + row_bytes * row_count
    if data_end > len(payload):
        raise JonesSourceAuditError("FITS binary table is truncated")
    values: dict[str, list[float]] = {
        name: [] for name, _ in columns
    }
    for row_index in range(row_count):
        row_offset = data_offset + row_index * row_bytes
        for name, field_offset in columns:
            value = struct.unpack_from(
                ">d",
                payload,
                row_offset + field_offset,
            )[0]
            if not math.isfinite(value):
                raise JonesSourceAuditError(
                    f"FITS column {name} contains a non-finite value"
                )
            values[name].append(value)
    return (
        extension,
        comments,
        {name: tuple(column) for name, column in values.items()},
    )


def _component_signature(
    wavelengths: tuple[float, ...],
    values: tuple[float, ...],
    *,
    prefix: str,
    lower: float,
    upper: float,
) -> tuple[str, int, float, float]:
    if len(wavelengths) != len(values) or not wavelengths:
        raise JonesSourceAuditError("component spectrum is incomplete")
    rows = [
        (wavelength, value)
        for wavelength, value in zip(wavelengths, values, strict=True)
        if lower - 1e-10 <= wavelength <= upper + 1e-10
    ]
    if not rows:
        raise JonesSourceAuditError("component signature domain is empty")
    payload = bytearray(prefix.encode("ascii") + b"\n")
    for wavelength, value in rows:
        payload.extend(struct.pack(">dd", wavelength, value))
    return (
        _sha256_bytes(bytes(payload)),
        len(rows),
        rows[0][0],
        rows[-1][0],
    )


def _read_tar_member(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
) -> bytes:
    if not member.isfile() or member.issym() or member.islnk():
        raise JonesSourceAuditError(
            f"source member is not a regular file: {member.name}"
        )
    stream = archive.extractfile(member)
    if stream is None:
        raise JonesSourceAuditError(
            f"cannot read source member: {member.name}"
        )
    return stream.read()


def _audit_source_fixture(
    members: dict[str, bytes],
    spec: dict[str, Any],
) -> dict[str, Any]:
    fixture = spec["source_owned_regression_fixture"]
    parameters = _parse_parameter_file(
        members[fixture["parameter_member"]]
    )
    expected_parameters = fixture["expected_parameters"]
    audited_parameters = {
        key: parameters.get(key)
        for key in expected_parameters
    }
    if audited_parameters != expected_parameters:
        raise JonesSourceAuditError(
            "source-owned regression parameters differ"
        )
    phase_angle = round(
        abs(180.0 - float(parameters["alpha"])),
        12,
    )
    if not math.isclose(
        phase_angle,
        fixture["derived_lunar_phase_angle_deg"],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise JonesSourceAuditError(
            "source-owned lunar phase derivation differs"
        )
    header, _, table = _fits_binary_table(
        members[fixture["radiance_member"]]
    )
    if (
        header.get("NAXIS1") != fixture["fits_row_bytes"]
        or header.get("NAXIS2") != fixture["fits_row_count"]
        or fixture["wavelength_column"] not in table
        or fixture["component_column"] not in table
    ):
        raise JonesSourceAuditError(
            "source-owned regression FITS shape differs"
        )
    lower, upper = fixture["optical_signature_domain_micrometre"]
    signature, count, actual_lower, actual_upper = _component_signature(
        table[fixture["wavelength_column"]],
        table[fixture["component_column"]],
        prefix=fixture["optical_signature_prefix"],
        lower=lower,
        upper=upper,
    )
    if (
        signature != fixture["optical_signature_sha256"]
        or count != fixture["optical_signature_row_count"]
        or not math.isclose(actual_lower, lower, abs_tol=1e-10)
        or not math.isclose(actual_upper, upper, abs_tol=1e-10)
    ):
        raise JonesSourceAuditError(
            "source-owned scattered-moonlight signature differs"
        )
    admitted_lower, admitted_upper = spec["first_admission_domain"][
        "lunar_phase_angle_deg"
    ]
    inside_domain = admitted_lower <= phase_angle <= admitted_upper
    if inside_domain is not fixture["inside_first_moira_admission_domain"]:
        raise JonesSourceAuditError(
            "source-owned fixture domain classification differs"
        )
    return {
        "parameter_member": fixture["parameter_member"],
        "radiance_member": fixture["radiance_member"],
        "derived_lunar_phase_angle_deg": phase_angle,
        "first_admission_phase_domain_deg": [
            admitted_lower,
            admitted_upper,
        ],
        "inside_first_admission_domain": inside_domain,
        "regression_role": fixture["regression_role"],
        "fits_row_count": header["NAXIS2"],
        "fits_row_bytes": header["NAXIS1"],
        "optical_signature_row_count": count,
        "optical_signature_sha256": signature,
    }


def _skycalc_input_from_comments(comments: tuple[str, ...]) -> dict[str, Any]:
    try:
        start = comments.index("Input parameters:") + 1
    except ValueError as exc:
        raise JonesSourceAuditError(
            "SkyCalc FITS lacks input-parameter comments"
        ) from exc
    text = " ".join(comments[start:]).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JonesSourceAuditError(
            "SkyCalc input-parameter comments are malformed"
        ) from exc
    if not isinstance(payload, dict):
        raise JonesSourceAuditError(
            "SkyCalc input-parameter receipt is not an object"
        )
    return payload


def _audit_operational_capture(
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    capture = spec["operational_comparison_capture"]
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != capture["fits_bytes"]
        or _sha256_file(path) != capture["fits_sha256"]
    ):
        raise JonesSourceAuditError(
            "SkyCalc operational-capture file receipt differs"
        )
    payload = path.read_bytes()
    header, comments, table = _fits_binary_table(payload)
    version_lines = [
        value
        for value in comments
        if value.startswith("SkyCalc version:")
    ]
    if version_lines != [
        f"SkyCalc version: {capture['skycalc_version']}"
    ]:
        raise JonesSourceAuditError("SkyCalc version receipt differs")
    if _skycalc_input_from_comments(comments) != capture["query"]:
        raise JonesSourceAuditError("SkyCalc input receipt differs")
    other_components = (
        "flux_ssl",
        "flux_zl",
        "flux_tie",
        "flux_tme",
        "flux_ael",
        "flux_arc",
    )
    required_columns = {
        "lam",
        "flux",
        capture["component_column"],
        *other_components,
    }
    if (
        header.get("NAXIS2") != capture["row_count"]
        or not required_columns.issubset(table)
    ):
        raise JonesSourceAuditError("SkyCalc table shape differs")
    wavelengths = table["lam"]
    component = table[capture["component_column"]]
    lower, upper = capture["wavelength_domain_nm"]
    signature, count, actual_lower, actual_upper = _component_signature(
        wavelengths,
        component,
        prefix=capture["component_signature_prefix"],
        lower=lower,
        upper=upper,
    )
    if (
        signature != capture["component_signature_sha256"]
        or count != capture["row_count"]
        or not math.isclose(actual_lower, lower, abs_tol=1e-12)
        or not math.isclose(actual_upper, upper, abs_tol=1e-12)
    ):
        raise JonesSourceAuditError(
            "SkyCalc scattered-moonlight signature differs"
        )
    other_zero = all(
        all(value == 0.0 for value in table[name])
        for name in other_components
    )
    flux_matches = table["flux"] == component
    if (
        other_zero is not capture["all_other_emission_components_zero"]
        or flux_matches
        is not capture["total_flux_equals_scattered_moonlight"]
    ):
        raise JonesSourceAuditError(
            "SkyCalc component-isolation receipt differs"
        )
    return {
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "skycalc_version": capture["skycalc_version"],
        "capture_date": capture["capture_date"],
        "derived_lunar_phase_angle_deg": capture[
            "derived_lunar_phase_angle_deg"
        ],
        "inside_first_admission_domain": True,
        "row_count": count,
        "component_signature_sha256": signature,
        "component_isolated": other_zero and flux_matches,
        "role": capture["role"],
    }


def audit_archive(
    archive_path: Path,
    *,
    spec_path: Path = DEFAULT_SPEC_PATH,
    skycalc_fits_path: Path | None = None,
) -> dict[str, Any]:
    """Audit an explicit official archive and optional captured SkyCalc FITS."""

    spec = load_spec(spec_path)
    if archive_path.is_symlink() or not archive_path.is_file():
        raise JonesSourceAuditError(
            f"ESO source archive is absent: {archive_path}"
        )
    if archive_path.stat().st_size != EXPECTED_ARCHIVE_BYTES:
        raise JonesSourceAuditError("ESO source archive byte count differs")
    archive_sha256 = _sha256_file(archive_path)
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise JonesSourceAuditError("ESO source archive SHA-256 differs")

    receipts = spec["eso_source_package"]["required_members"]
    expected_paths = {receipt["path"] for receipt in receipts}
    payloads: dict[str, bytes] = {}
    audited_members: list[dict[str, Any]] = []
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            all_members = archive.getmembers()
            names = [member.name for member in all_members]
            if len(names) != len(set(names)):
                raise JonesSourceAuditError(
                    "ESO source archive contains duplicate member names"
                )
            by_name = {member.name: member for member in all_members}
            if not expected_paths.issubset(by_name):
                missing = sorted(expected_paths.difference(by_name))
                raise JonesSourceAuditError(
                    f"ESO source archive lacks required members: {missing}"
                )
            for receipt in receipts:
                path = receipt["path"]
                payload = _read_tar_member(archive, by_name[path])
                if (
                    len(payload) != receipt["bytes"]
                    or _sha256_bytes(payload) != receipt["sha256"]
                ):
                    raise JonesSourceAuditError(
                        f"ESO source member receipt differs: {path}"
                    )
                payloads[path] = payload
                audited_members.append(
                    {
                        "path": path,
                        "bytes": len(payload),
                        "sha256": _sha256_bytes(payload),
                        "role": receipt["role"],
                    }
                )
    except (OSError, tarfile.TarError) as exc:
        raise JonesSourceAuditError(
            f"cannot inspect ESO source archive: {archive_path}"
        ) from exc

    source_fixture = _audit_source_fixture(payloads, spec)
    spec_bytes = spec_path.read_bytes()
    auditor_path = Path(__file__).resolve()
    auditor_bytes = auditor_path.read_bytes()
    result: dict[str, Any] = {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint_id": CHECKPOINT_ID,
        "status": "source_audit_complete_runtime_model_not_admitted",
        "spec": {
            "path": spec_path.relative_to(REPO_ROOT).as_posix(),
            "bytes": len(spec_bytes),
            "sha256": _sha256_bytes(spec_bytes),
        },
        "auditor": {
            "path": auditor_path.relative_to(REPO_ROOT).as_posix(),
            "bytes": len(auditor_bytes),
            "sha256": _sha256_bytes(auditor_bytes),
        },
        "archive": {
            "url": spec["eso_source_package"]["url"],
            "release": spec["eso_source_package"]["release"],
            "bytes": archive_path.stat().st_size,
            "sha256": archive_sha256,
            "license": spec["eso_source_package"]["license"],
        },
        "required_member_count": len(audited_members),
        "required_members": audited_members,
        "source_owned_regression_fixture": source_fixture,
        "admission_decision": {
            "candidate_model_id": EXPECTED_MODEL_ID,
            "admitted": False,
            "first_admission_site_id": spec["first_admission_domain"][
                "site_id"
            ],
            "first_admission_phase_domain_deg": spec[
                "first_admission_domain"
            ]["lunar_phase_angle_deg"],
            "phase_extrapolation_allowed": False,
            "independent_artifact_status": spec[
                "independent_artifact_contract"
            ]["artifact_status"],
            "acceptance_thresholds_status": spec[
                "independent_artifact_contract"
            ]["acceptance_thresholds_status"],
        },
        "atmospheric_sensitivity": {
            "available_from_current_pack": False,
            "required_method": spec["atmospheric_sensitivity_contract"][
                "required_method"
            ],
            "probabilistic_confidence_claimed": False,
        },
        "runtime_dependency": False,
        "network_dependency": False,
        "external_source_bytes_redistributed": False,
    }
    if skycalc_fits_path is not None:
        result["operational_comparison_capture"] = (
            _audit_operational_capture(skycalc_fits_path, spec)
        )
    else:
        result["operational_comparison_capture"] = {
            "verified": False,
            "reason": "explicit_skycalc_fits_path_not_supplied",
            "role": spec["operational_comparison_capture"]["role"],
        }
    return result


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit an explicit official ESO SM-01 archive without "
            "extracting or executing it."
        )
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--skycalc-fits", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = audit_archive(
            args.archive,
            spec_path=args.spec,
            skycalc_fits_path=args.skycalc_fits,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(_canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
