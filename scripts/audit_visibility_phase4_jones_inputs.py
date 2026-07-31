#!/usr/bin/env python3
"""Audit the external input authorities for the Jones Phase 4 candidate.

The audit is intentionally offline.  It reads explicit operator-supplied
files, verifies immutable receipts, and emits a provenance checkpoint.  It
does not download, extract to disk, compile, execute, redistribute, or admit
any external implementation or data product.
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
    / "phase4_jones_input_authority_spec.json"
)
SPEC_SCHEMA = "moira.visibility-jones-input-authority-spec/v1"
SPEC_ID = "physical-heliacal-phase4-jones-input-authority-2026-07-31"
CHECKPOINT_SCHEMA = "moira.visibility-jones-input-authority-checkpoint/v1"
CHECKPOINT_ID = "physical-heliacal-phase4-jones-input-authority-2026-07-31"
EXPECTED_MODEL_ID = "jones_paranal_scattered_moonlight_2013_v1"
_FITS_BLOCK_BYTES = 2880
_FITS_CARD_BYTES = 80


class JonesInputAuthorityError(ValueError):
    """Raised when an input differs from the frozen authority receipt."""


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


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise JonesInputAuthorityError(
            f"{label} must be a lowercase SHA-256"
        )
    return value


def _require_safe_member_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise JonesInputAuthorityError("archive member path must be nonempty")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise JonesInputAuthorityError(
            f"archive member path is not canonical: {value!r}"
        )
    return value


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JonesInputAuthorityError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise JonesInputAuthorityError(f"{label} must be a JSON object")
    return payload


def validate_spec(spec: dict[str, Any]) -> None:
    """Validate the frozen authority classifications and closed boundary."""

    if (
        spec.get("schema") != SPEC_SCHEMA
        or spec.get("spec_id") != SPEC_ID
        or spec.get("status") != "input_authority_audit_not_runtime_model"
        or spec.get("candidate_model_id") != EXPECTED_MODEL_ID
        or spec.get("candidate_spectral_domain_nm") != [380.0, 780.0]
    ):
        raise JonesInputAuthorityError("input-authority spec identity differs")

    if spec.get("runtime_boundary") != {
        "engine_changes_authorized": False,
        "public_api_changes_authorized": False,
        "production_data_pack_authorized": False,
        "external_source_bytes_redistributed": False,
        "network_dependency": False,
        "automatic_download_allowed": False,
    }:
        raise JonesInputAuthorityError("runtime boundary must remain closed")

    package = spec.get("eso_source_package")
    if (
        not isinstance(package, dict)
        or package.get("release") != "1.0.0"
        or package.get("bytes") != 431651392
        or package.get("sha256")
        != "e09b1d62c8af212486f50097fe76d9dc"
        "bb242f4fbadf720a4a85be361cc9116b"
        or package.get("license") != "GPL-2.0-or-later"
        or package.get("role")
        != "external_source_owned_input_lineage_not_redistributed"
    ):
        raise JonesInputAuthorityError("ESO package receipt differs")

    solar = spec.get("solar_irradiance")
    if (
        not isinstance(solar, dict)
        or solar.get("authority_status")
        != "independently_reconstructable_in_candidate_domain"
        or solar.get("outside_independent_domain_policy")
        != "not_admitted_without_separate_source_receipt"
    ):
        raise JonesInputAuthorityError("solar authority policy differs")
    _validate_file_receipt(solar.get("eso_member"), "solar ESO member")
    _validate_file_receipt(
        solar.get("independent_stis_reference"),
        "STIS solar reference",
    )
    _validate_file_receipt(
        solar.get("independent_nmsu_reference"),
        "NMSU solar reference",
    )

    lunar = spec.get("lunar_reflectance")
    if (
        not isinstance(lunar, dict)
        or lunar.get("authority_status")
        != "independently_reconstructable_with_empirical_phase_domain"
        or lunar.get("empirical_phase_domain_deg") != [1.55, 97.0]
        or lunar.get("outside_empirical_phase_domain_policy")
        != "not_evaluable"
        or lunar.get("libration_terms_in_candidate") is not False
    ):
        raise JonesInputAuthorityError("lunar authority policy differs")
    _validate_file_receipt(lunar.get("eso_member"), "lunar ESO member")
    table = lunar.get("published_table_contract")
    if (
        not isinstance(table, dict)
        or table.get("wavelength_row_count") != 32
        or table.get("coefficient_columns_per_row_including_wavelength")
        != 11
        or table.get("table4_transcription_checked") is not True
    ):
        raise JonesInputAuthorityError("ROLO table contract differs")
    _require_sha256(
        table.get("constant_coefficients_numeric_sha256"),
        "ROLO constant coefficients",
    )
    _require_sha256(table.get("table4_numeric_sha256"), "ROLO Table 4")

    aerosol = spec.get("aerosol_phase_function")
    if (
        not isinstance(aerosol, dict)
        or aerosol.get("authority_status")
        != "source_owned_checksum_locked_not_reconstructable"
    ):
        raise JonesInputAuthorityError("aerosol authority policy differs")
    _validate_file_receipt(aerosol.get("eso_member"), "aerosol ESO member")
    falsification = aerosol.get("reconstruction_falsification")
    if (
        not isinstance(falsification, dict)
        or falsification.get("match") is not False
        or falsification.get("invented_transform_allowed") is not False
        or falsification.get("unresolved_transform")
        != "undocumented_m15s1_transformation_or_smoothing"
    ):
        raise JonesInputAuthorityError(
            "aerosol reconstruction disposition differs"
        )
    policy = aerosol.get("pilot_use_policy")
    if policy != {
        "allowed": True,
        "role": (
            "external_source_owned_input_not_independent_"
            "microphysics_oracle"
        ),
        "exact_receipt_required": True,
        "independent_radiative_transfer_claim_allowed": True,
        "independent_aerosol_reconstruction_claim_allowed": False,
        "bytes_may_be_committed_to_repository": False,
        "generated_artifact_distribution_status": (
            "unresolved_requires_release_disposition"
        ),
    }:
        raise JonesInputAuthorityError("aerosol pilot-use policy differs")

    mie = aerosol.get("identified_mie_authority")
    if not isinstance(mie, dict):
        raise JonesInputAuthorityError("Mie authority receipt is absent")
    _validate_file_receipt(mie, "EODG Mie archive")
    if mie.get("duplicate_path_policy") != (
        "one_regular_member_plus_self_hardlink_duplicate_allowed"
    ):
        raise JonesInputAuthorityError("EODG duplicate-path policy differs")
    required_members = mie.get("required_members")
    if not isinstance(required_members, list) or len(required_members) != 3:
        raise JonesInputAuthorityError("EODG member receipts differ")
    for index, receipt in enumerate(required_members):
        _validate_file_receipt(receipt, f"EODG member {index}")
        _require_safe_member_path(receipt["path"])

    gate = spec.get("gate_decision")
    if gate != {
        "input_authority_gate_closed": True,
        "independent_mystic_pilot_may_proceed": True,
        "production_admission_allowed": False,
        "acceptance_thresholds_may_be_frozen_before_pilot": False,
        "aerosol_reconstruction_blocker_is_silently_ignored": False,
        "aerosol_reconstruction_blocker_is_misreported_as_model_failure": (
            False
        ),
        "next_gate": "freeze_and_generate_independent_mystic_pilot_matrix",
    }:
        raise JonesInputAuthorityError("input-authority gate differs")


def _validate_file_receipt(value: Any, label: str) -> None:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("bytes"), int)
        or value["bytes"] <= 0
    ):
        raise JonesInputAuthorityError(f"{label} byte receipt differs")
    _require_sha256(value.get("sha256"), label)
    if "path" in value:
        _require_safe_member_path(value["path"])


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    spec = _load_json(path, "input-authority spec")
    validate_spec(spec)
    return spec


def inspect_spec(path: Path = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    """Return the high-level decisions without requiring external files."""

    spec = load_spec(path)
    return {
        "spec_id": spec["spec_id"],
        "status": spec["status"],
        "candidate_model_id": spec["candidate_model_id"],
        "solar_authority_status": spec["solar_irradiance"][
            "authority_status"
        ],
        "lunar_authority_status": spec["lunar_reflectance"][
            "authority_status"
        ],
        "aerosol_authority_status": spec["aerosol_phase_function"][
            "authority_status"
        ],
        "input_authority_gate_closed": spec["gate_decision"][
            "input_authority_gate_closed"
        ],
        "pilot_may_proceed": spec["gate_decision"][
            "independent_mystic_pilot_may_proceed"
        ],
        "production_admission_allowed": spec["gate_decision"][
            "production_admission_allowed"
        ],
        "runtime_dependency": False,
    }


def _require_external_file(path: Path, receipt: dict[str, Any], label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise JonesInputAuthorityError(f"{label} is absent: {path}")
    if path.stat().st_size != receipt["bytes"]:
        raise JonesInputAuthorityError(f"{label} byte count differs")
    if _sha256_file(path) != receipt["sha256"]:
        raise JonesInputAuthorityError(f"{label} SHA-256 differs")


def _read_tar_members(
    archive_path: Path,
    receipts: list[dict[str, Any]],
    *,
    label: str,
    allow_self_hardlink_duplicates: bool = False,
) -> dict[str, bytes]:
    expected_paths = {receipt["path"] for receipt in receipts}
    payloads: dict[str, bytes] = {}
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            by_name: dict[str, list[tarfile.TarInfo]] = {}
            for member in members:
                by_name.setdefault(member.name, []).append(member)
            duplicates = {
                name: occurrences
                for name, occurrences in by_name.items()
                if len(occurrences) > 1
            }
            if duplicates and not allow_self_hardlink_duplicates:
                raise JonesInputAuthorityError(
                    f"{label} contains duplicate member names"
                )
            for name, occurrences in duplicates.items():
                regular = [member for member in occurrences if member.isfile()]
                self_links = [
                    member
                    for member in occurrences
                    if member.islnk() and member.linkname == name
                ]
                if len(regular) != 1 or len(self_links) != len(occurrences) - 1:
                    raise JonesInputAuthorityError(
                        f"{label} has an unsafe duplicate member: {name}"
                    )
            if not expected_paths.issubset(by_name):
                missing = sorted(expected_paths.difference(by_name))
                raise JonesInputAuthorityError(
                    f"{label} lacks required members: {missing}"
                )
            for receipt in receipts:
                occurrences = by_name[receipt["path"]]
                member = next(
                    (candidate for candidate in occurrences if candidate.isfile()),
                    occurrences[0],
                )
                if not member.isfile() or member.issym() or member.islnk():
                    raise JonesInputAuthorityError(
                        f"{label} member is not a regular file: {member.name}"
                    )
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise JonesInputAuthorityError(
                        f"cannot read {label} member: {member.name}"
                    )
                payload = extracted.read()
                if (
                    len(payload) != receipt["bytes"]
                    or _sha256_bytes(payload) != receipt["sha256"]
                ):
                    raise JonesInputAuthorityError(
                        f"{label} member receipt differs: {member.name}"
                    )
                payloads[member.name] = payload
    except (OSError, tarfile.TarError) as exc:
        raise JonesInputAuthorityError(
            f"cannot inspect {label}: {archive_path}"
        ) from exc
    return payloads


def _parse_two_column_ascii(payload: bytes, label: str) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise JonesInputAuthorityError(f"{label} is not ASCII") from exc
    for line in text.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if len(fields) != 2:
            raise JonesInputAuthorityError(f"{label} row shape differs")
        try:
            rows.append((float(fields[0]), float(fields[1])))
        except ValueError as exc:
            raise JonesInputAuthorityError(
                f"{label} contains a nonnumeric row"
            ) from exc
    return rows


def _fits_scalar(raw: str) -> int | float | str | bool:
    value = raw.split("/", 1)[0].strip()
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].strip()
    if value == "T":
        return True
    if value == "F":
        return False
    try:
        return int(value)
    except ValueError:
        try:
            return float(value.replace("D", "E"))
        except ValueError:
            return value


def _fits_header(payload: bytes, offset: int) -> tuple[dict[str, Any], int]:
    header: dict[str, Any] = {}
    while True:
        block = payload[offset : offset + _FITS_BLOCK_BYTES]
        if len(block) != _FITS_BLOCK_BYTES:
            raise JonesInputAuthorityError("STIS FITS header is truncated")
        for card_offset in range(0, _FITS_BLOCK_BYTES, _FITS_CARD_BYTES):
            card = block[card_offset : card_offset + _FITS_CARD_BYTES]
            try:
                text = card.decode("ascii")
            except UnicodeDecodeError as exc:
                raise JonesInputAuthorityError(
                    "STIS FITS header is not ASCII"
                ) from exc
            key = text[:8].strip()
            if key == "END":
                return header, offset + _FITS_BLOCK_BYTES
            if key and text[8:10] == "= ":
                header[key] = _fits_scalar(text[10:])
        offset += _FITS_BLOCK_BYTES


def _read_stis_rows(payload: bytes) -> list[tuple[float, float]]:
    primary, extension_offset = _fits_header(payload, 0)
    extension, data_offset = _fits_header(payload, extension_offset)
    if (
        primary.get("SIMPLE") is not True
        or primary.get("TARGETID") != "SUN_REFERENCE"
        or extension.get("XTENSION") != "BINTABLE"
        or extension.get("NAXIS1") != 20
        or extension.get("NAXIS2") != 1467
        or extension.get("TFIELDS") != 5
        or [extension.get(f"TTYPE{i}") for i in range(1, 6)]
        != ["WAVELENGTH", "FLUX", "SYSERROR", "FWHM", "DATAQUAL"]
        or [extension.get(f"TFORM{i}") for i in range(1, 6)]
        != ["E", "E", "E", "E", "E"]
        or extension.get("TUNIT1") != "ANGSTROMS"
        or extension.get("TUNIT2") != "FLAM"
    ):
        raise JonesInputAuthorityError("STIS FITS table contract differs")
    row_count = int(extension["NAXIS2"])
    row_bytes = int(extension["NAXIS1"])
    end = data_offset + row_count * row_bytes
    if end > len(payload):
        raise JonesInputAuthorityError("STIS FITS table is truncated")
    rows: list[tuple[float, float]] = []
    for offset in range(data_offset, end, row_bytes):
        wavelength, flux, _error, _fwhm, _quality = struct.unpack(
            ">5f", payload[offset : offset + row_bytes]
        )
        if not math.isfinite(wavelength) or not math.isfinite(flux):
            raise JonesInputAuthorityError("STIS FITS contains nonfinite data")
        rows.append((wavelength, flux))
    return rows


def _audit_solar(
    eso_payload: bytes,
    stis_path: Path,
    nmsu_path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    solar = spec["solar_irradiance"]
    stis_receipt = solar["independent_stis_reference"]
    nmsu_receipt = solar["independent_nmsu_reference"]
    _require_external_file(stis_path, stis_receipt, "STIS solar reference")
    _require_external_file(nmsu_path, nmsu_receipt, "NMSU solar reference")

    eso_rows = _parse_two_column_ascii(eso_payload, "ESO solar table")
    stis_rows_raw = _read_stis_rows(stis_path.read_bytes())
    if (
        len(eso_rows) != solar["eso_member"]["row_count"]
        or [eso_rows[0][0], eso_rows[-1][0]]
        != solar["eso_member"]["wavelength_domain_micrometre"]
        or len(stis_rows_raw) != stis_receipt["row_count"]
    ):
        raise JonesInputAuthorityError("solar table shape differs")
    stis_rows = [
        (wavelength / 10000.0, flux * 10.0)
        for wavelength, flux in stis_rows_raw
    ]
    compared = len(stis_rows)
    wavelength_deltas = [
        abs(eso_rows[index][0] - stis_rows[index][0])
        for index in range(compared)
    ]
    absolute_flux_deltas = [
        abs(eso_rows[index][1] - stis_rows[index][1])
        for index in range(compared)
    ]
    relative_flux_deltas = [
        absolute_flux_deltas[index]
        / max(abs(stis_rows[index][1]), 1e-300)
        for index in range(compared)
    ]
    contract = solar["equivalence_contract"]
    if (
        compared != contract["eso_rows_compared_to_stis"]
        or max(wavelength_deltas)
        > contract["max_wavelength_delta_micrometre"]
        or max(absolute_flux_deltas)
        > contract["max_absolute_flux_delta_W_m-2_micrometre-1"]
        or max(relative_flux_deltas)
        > contract["max_relative_flux_delta"]
    ):
        raise JonesInputAuthorityError("ESO/STIS solar equivalence differs")

    lower, upper = spec["candidate_spectral_domain_nm"]
    candidate_indices = [
        index
        for index, (wavelength, _flux) in enumerate(eso_rows[:compared])
        if lower / 1000.0 <= wavelength <= upper / 1000.0
    ]
    candidate_bytes = "".join(
        f"{eso_rows[index][0]:.5f} {eso_rows[index][1]:.8e}\n"
        for index in candidate_indices
    ).encode("ascii")
    actual_domain = [
        eso_rows[candidate_indices[0]][0],
        eso_rows[candidate_indices[-1]][0],
    ]
    if (
        len(candidate_indices) != contract["candidate_domain_row_count"]
        or actual_domain != contract["candidate_domain_actual_micrometre"]
        or _sha256_bytes(candidate_bytes)
        != contract["candidate_domain_eso_numeric_sha256"]
    ):
        raise JonesInputAuthorityError("candidate solar signature differs")

    nmsu_rows = _parse_nmsu_rows(nmsu_path.read_bytes())
    if len(nmsu_rows) != nmsu_receipt["populated_row_count"]:
        raise JonesInputAuthorityError("NMSU populated-row count differs")
    nmsu_by_wavelength = {
        round(wavelength / 10000.0, 8): flux * 10.0
        for wavelength, flux in nmsu_rows
    }
    common = [
        (wavelength, flux, nmsu_by_wavelength[round(wavelength, 8)])
        for wavelength, flux in eso_rows
        if round(wavelength, 8) in nmsu_by_wavelength
    ]
    common_relative = [
        abs(eso_flux - nmsu_flux) / max(abs(nmsu_flux), 1e-300)
        for _wavelength, eso_flux, nmsu_flux in common
    ]
    if (
        len(common) != nmsu_receipt["exact_common_grid_row_count"]
        or max(common_relative)
        > nmsu_receipt["max_relative_flux_delta_on_common_grid"]
    ):
        raise JonesInputAuthorityError("NMSU solar crosscheck differs")

    return {
        "authority_status": solar["authority_status"],
        "eso_member": _member_result(solar["eso_member"]),
        "stis_reference": _external_result(stis_path, stis_receipt),
        "nmsu_reference": _external_result(nmsu_path, nmsu_receipt),
        "eso_rows_compared_to_stis": compared,
        "max_wavelength_delta_micrometre": max(wavelength_deltas),
        "max_absolute_flux_delta_W_m-2_micrometre-1": max(
            absolute_flux_deltas
        ),
        "max_relative_flux_delta": max(relative_flux_deltas),
        "candidate_domain_row_count": len(candidate_indices),
        "candidate_domain_actual_micrometre": actual_domain,
        "candidate_domain_eso_numeric_sha256": _sha256_bytes(
            candidate_bytes
        ),
        "nmsu_common_grid_row_count": len(common),
        "role": "independent_candidate_domain_input_authority",
    }


def _parse_nmsu_rows(payload: bytes) -> list[tuple[float, float]]:
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise JonesInputAuthorityError("NMSU solar file is not ASCII") from exc
    rows: list[tuple[float, float]] = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        try:
            rows.append((float(fields[0]), float(fields[1])))
        except ValueError:
            continue
    return rows


def _audit_lunar(payload: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    lunar = spec["lunar_reflectance"]
    contract = lunar["published_table_contract"]
    try:
        lines = [
            line.strip()
            for line in payload.decode("ascii").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        constants = [float(value) for value in lines[0].split()]
        declared_rows = int(lines[1])
        rows = [[float(value) for value in line.split()] for line in lines[2:]]
    except (UnicodeDecodeError, ValueError, IndexError) as exc:
        raise JonesInputAuthorityError("ROLO coefficient table is malformed") from exc
    constant_bytes = (
        " ".join(f"{value:.5f}" for value in constants) + "\n"
    ).encode("ascii")
    table_bytes = "".join(
        " ".join(f"{value:.5f}" for value in row) + "\n" for row in rows
    ).encode("ascii")
    if (
        constants != contract["constant_coefficients"]
        or declared_rows != contract["wavelength_row_count"]
        or len(rows) != declared_rows
        or any(
            len(row)
            != contract["coefficient_columns_per_row_including_wavelength"]
            for row in rows
        )
        or [rows[0][0], rows[-1][0]] != contract["wavelength_domain_nm"]
        or _sha256_bytes(constant_bytes)
        != contract["constant_coefficients_numeric_sha256"]
        or _sha256_bytes(table_bytes) != contract["table4_numeric_sha256"]
    ):
        raise JonesInputAuthorityError("ROLO published-table receipt differs")
    return {
        "authority_status": lunar["authority_status"],
        "eso_member": _member_result(lunar["eso_member"]),
        "constant_coefficients_numeric_sha256": _sha256_bytes(
            constant_bytes
        ),
        "wavelength_row_count": len(rows),
        "wavelength_domain_nm": [rows[0][0], rows[-1][0]],
        "table4_numeric_sha256": _sha256_bytes(table_bytes),
        "empirical_phase_domain_deg": lunar["empirical_phase_domain_deg"],
        "outside_empirical_phase_domain_policy": lunar[
            "outside_empirical_phase_domain_policy"
        ],
        "role": "independent_phase_bounded_input_authority",
    }


def _audit_aerosol(payload: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    aerosol = spec["aerosol_phase_function"]
    member = aerosol["eso_member"]
    try:
        lines = [line.strip() for line in payload.decode("ascii").splitlines()]
        wavelength_count, angle_count = [int(value) for value in lines[0].split()]
        wavelengths = [float(value) for value in lines[1].split()]
        angles = [float(value) for value in lines[2].split()]
        matrix = [
            [float(value) for value in line.split()]
            for line in lines[3:]
            if line
        ]
    except (UnicodeDecodeError, ValueError, IndexError) as exc:
        raise JonesInputAuthorityError(
            "ESO aerosol phase table is malformed"
        ) from exc
    if (
        wavelength_count != member["wavelength_count"]
        or angle_count != member["angle_count"]
        or len(wavelengths) != wavelength_count
        or len(angles) != angle_count
        or len(matrix) != wavelength_count
        or any(len(row) != angle_count for row in matrix)
        or [wavelengths[0], wavelengths[-1]]
        != member["wavelength_domain_micrometre"]
        or [angles[0], angles[-1]] != member["angle_domain_deg"]
        or any(
            not math.isclose(
                angles[index] - angles[index - 1],
                member["angle_step_deg"],
                abs_tol=1e-12,
            )
            for index in range(1, len(angles))
        )
    ):
        raise JonesInputAuthorityError("ESO aerosol table shape differs")
    try:
        wavelength_index = wavelengths.index(0.55)
    except ValueError as exc:
        raise JonesInputAuthorityError(
            "ESO aerosol table lacks 0.55 micrometre"
        ) from exc
    phase = matrix[wavelength_index]
    mu_phase = sorted(
        (math.cos(math.radians(angle)), value)
        for angle, value in zip(angles, phase, strict=True)
    )
    integral = 0.0
    first_moment = 0.0
    for (mu0, phase0), (mu1, phase1) in zip(
        mu_phase,
        mu_phase[1:],
    ):
        width = mu1 - mu0
        integral += 0.5 * (phase0 + phase1) * width
        first_moment += 0.5 * (mu0 * phase0 + mu1 * phase1) * width
    normalization = integral / 2.0
    asymmetry = first_moment / integral
    invariants = aerosol["numeric_invariants_at_0_55_micrometre"]
    tolerance = invariants["absolute_tolerance"]
    if (
        not math.isclose(
            normalization,
            invariants["half_solid_angle_normalization"],
            abs_tol=tolerance,
        )
        or not math.isclose(
            asymmetry,
            invariants["asymmetry_parameter"],
            abs_tol=tolerance,
        )
    ):
        raise JonesInputAuthorityError("ESO aerosol invariants differ")
    selected: dict[str, float] = {}
    for angle_text, expected in invariants["selected_phase_values"].items():
        angle = float(angle_text)
        try:
            value = phase[angles.index(angle)]
        except ValueError as exc:
            raise JonesInputAuthorityError(
                f"ESO aerosol table lacks angle {angle_text}"
            ) from exc
        if not math.isclose(value, expected, abs_tol=tolerance):
            raise JonesInputAuthorityError(
                f"ESO aerosol phase value differs at {angle_text} degrees"
            )
        selected[angle_text] = value
    return {
        "authority_status": aerosol["authority_status"],
        "eso_member": _member_result(member),
        "wavelength_count": wavelength_count,
        "angle_count": angle_count,
        "half_solid_angle_normalization_at_0_55_micrometre": normalization,
        "asymmetry_parameter_at_0_55_micrometre": asymmetry,
        "selected_phase_values_at_0_55_micrometre": selected,
        "reconstruction_falsification": aerosol[
            "reconstruction_falsification"
        ],
        "pilot_use_policy": aerosol["pilot_use_policy"],
    }


def _member_result(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": receipt["path"],
        "bytes": receipt["bytes"],
        "sha256": receipt["sha256"],
    }


def _external_result(path: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "filename": receipt["filename"],
        "url": receipt.get("url", receipt.get("landing_page")),
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "redistributed": False,
    }


def audit_inputs(
    eso_archive_path: Path,
    *,
    stis_solar_path: Path,
    nmsu_solar_path: Path,
    eodg_archive_path: Path,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, Any]:
    """Audit all external Phase 4 input authorities and emit a receipt."""

    spec = load_spec(spec_path)
    package = spec["eso_source_package"]
    _require_external_file(eso_archive_path, package, "ESO source archive")
    solar_member = spec["solar_irradiance"]["eso_member"]
    lunar_member = spec["lunar_reflectance"]["eso_member"]
    aerosol_member = spec["aerosol_phase_function"]["eso_member"]
    eso_payloads = _read_tar_members(
        eso_archive_path,
        [solar_member, lunar_member, aerosol_member],
        label="ESO source archive",
    )

    mie = spec["aerosol_phase_function"]["identified_mie_authority"]
    _require_external_file(eodg_archive_path, mie, "EODG Mie archive")
    eodg_payloads = _read_tar_members(
        eodg_archive_path,
        mie["required_members"],
        label="EODG Mie archive",
        allow_self_hardlink_duplicates=True,
    )

    spec_bytes = spec_path.read_bytes()
    auditor_path = Path(__file__).resolve()
    auditor_bytes = auditor_path.read_bytes()
    return {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint_id": CHECKPOINT_ID,
        "status": "input_authority_audit_complete_runtime_model_not_admitted",
        "candidate_model_id": EXPECTED_MODEL_ID,
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
        "eso_source_package": {
            "url": package["url"],
            "release": package["release"],
            "bytes": eso_archive_path.stat().st_size,
            "sha256": _sha256_file(eso_archive_path),
            "license": package["license"],
            "redistributed": False,
        },
        "solar_irradiance": _audit_solar(
            eso_payloads[solar_member["path"]],
            stis_solar_path,
            nmsu_solar_path,
            spec,
        ),
        "lunar_reflectance": _audit_lunar(
            eso_payloads[lunar_member["path"]],
            spec,
        ),
        "aerosol_phase_function": _audit_aerosol(
            eso_payloads[aerosol_member["path"]],
            spec,
        ),
        "eodg_mie_authority": {
            "bytes": eodg_archive_path.stat().st_size,
            "sha256": _sha256_file(eodg_archive_path),
            "required_members": [
                {
                    "path": receipt["path"],
                    "bytes": len(eodg_payloads[receipt["path"]]),
                    "sha256": _sha256_bytes(eodg_payloads[receipt["path"]]),
                }
                for receipt in mie["required_members"]
            ],
            "executed_by_auditor": False,
            "redistributed": False,
        },
        "gate_decision": spec["gate_decision"],
        "runtime_dependency": False,
        "network_dependency": False,
        "external_source_bytes_redistributed": False,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit explicit Jones/ESO, STIS, NMSU, and Oxford EODG input "
            "authorities without downloading or executing them."
        )
    )
    parser.add_argument("eso_archive", type=Path)
    parser.add_argument("--stis-solar", type=Path, required=True)
    parser.add_argument("--nmsu-solar", type=Path, required=True)
    parser.add_argument("--eodg-archive", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = audit_inputs(
            args.eso_archive,
            stis_solar_path=args.stis_solar,
            nmsu_solar_path=args.nmsu_solar,
            eodg_archive_path=args.eodg_archive,
            spec_path=args.spec,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(_canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
