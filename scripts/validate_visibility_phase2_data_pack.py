"""Independently validate one immutable Phase 2 visibility data pack.

This read-only validator does not import the builder or the Moira runtime. It
recomputes the planetary response payload from explicit, checksum-locked local
sources, verifies the unchanged Phase 1 payload inheritance, and checks the
complete Phase 2 root inventory and receipts. It never uses a network.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "scripts" / "visibility_reference_lab"
DEFAULT_SPEC = LAB_ROOT / "phase2_planetary_target_profile_pack_spec.json"
DEFAULT_COMPATIBILITY = (
    LAB_ROOT
    / "physical_heliacal_visibility_data_pack_compatibility_v1_1.json"
)
BUILDER_PATH = REPO_ROOT / "scripts" / "build_visibility_phase2_data_pack.py"
MANIFEST_NAME = "manifest.json"
TARGET_FILENAME = "planetary-target-profiles.json"
TARGET_IDS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
BASE_ROLES = (
    "axes",
    "direct_extinction",
    "error_envelope",
    "photopic_luminance",
    "photopic_relative_standard_error",
    "scotopic_luminance",
    "scotopic_relative_standard_error",
)


class ValidationError(ValueError):
    """Raised when any independent Phase 2 admission check fails."""


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _receipt(path: Path) -> dict[str, Any]:
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _verify_declared_file(
    path: Path,
    declaration: dict[str, Any],
    label: str,
) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != declaration.get("bytes")
        or _sha256(path) != declaration.get("sha256")
    ):
        raise ValidationError(f"{label} identity differs")


def _linear_sample(
    rows: tuple[tuple[float, float], ...],
    coordinate: float,
) -> float:
    coordinates = tuple(row[0] for row in rows)
    high = bisect.bisect_right(coordinates, coordinate)
    if high and coordinates[high - 1] == coordinate:
        return rows[high - 1][1]
    if high == 0 or high == len(rows):
        raise ValidationError(
            f"source series does not cover {coordinate}"
        )
    low = high - 1
    fraction = (
        (coordinate - coordinates[low])
        / (coordinates[high] - coordinates[low])
    )
    return rows[low][1] + fraction * (
        rows[high][1] - rows[low][1]
    )


def _strict_series(
    rows: tuple[tuple[float, float], ...],
    label: str,
    *,
    allow_zero: bool,
) -> tuple[tuple[float, float], ...]:
    if len(rows) < 2:
        raise ValidationError(f"{label} is incomplete")
    previous = float("-inf")
    for coordinate, value in rows:
        if (
            not math.isfinite(coordinate)
            or not math.isfinite(value)
            or coordinate <= previous
            or value < 0.0
            or (not allow_zero and value == 0.0)
        ):
            raise ValidationError(f"{label} contains invalid values")
        previous = coordinate
    return rows


def _planet_rows(path: Path) -> tuple[tuple[float, float], ...]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            if header != ["Wavelength", "Albedo"]:
                raise ValidationError(
                    f"{path.name} columns differ"
                )
            all_rows = tuple(
                (float(row[0]), float(row[1]))
                for row in reader
                if len(row) == 2
            )
    except (OSError, UnicodeError, ValueError, StopIteration) as exc:
        raise ValidationError(
            f"invalid planetary spectrum: {path.name}"
        ) from exc
    if not all_rows or any(
        not math.isfinite(wavelength)
        or not math.isfinite(value)
        or value < 0.0
        for wavelength, value in all_rows
    ):
        raise ValidationError(
            f"{path.name} full source file contains invalid values"
        )
    visible = tuple(
        (wavelength, value)
        for wavelength, value in all_rows
        if 0.30 <= wavelength <= 1.00
    )
    return _strict_series(
        visible,
        f"{path.name} admitted subset",
        allow_zero=False,
    )


def _cie_values(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            for row in csv.reader(stream):
                if len(row) != 2:
                    raise ValidationError(
                        f"{path.name} row shape differs"
                    )
                wavelength = int(row[0])
                value = float(row[1])
                if (
                    wavelength in result
                    or not math.isfinite(value)
                    or value < 0.0
                ):
                    raise ValidationError(
                        f"{path.name} value differs"
                    )
                result[wavelength] = value
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValidationError(
            f"invalid CIE response: {path.name}"
        ) from exc
    if set(range(380, 780)) - set(result):
        raise ValidationError(
            f"{path.name} does not cover every admitted bin"
        )
    return result


def _solar_rows(path: Path) -> tuple[tuple[float, float], ...]:
    rows: list[tuple[float, float]] = []
    try:
        for line in path.read_text(encoding="ascii").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 2:
                raise ValidationError("solar-spectrum row differs")
            rows.append((float(fields[0]), float(fields[1])))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValidationError("invalid solar spectrum") from exc
    return _strict_series(
        tuple(rows),
        path.name,
        allow_zero=False,
    )


def _source_receipts(
    spec: dict[str, Any],
    *,
    planetary_spectra_dir: Path,
    cie_root: Path,
    solar_spectrum: Path,
    mallama_pdf: Path,
) -> dict[str, Any]:
    declarations = spec["source_inputs"]
    payne = declarations["payne_planetary_spectra"]
    spectra: dict[str, Any] = {}
    for target_id in TARGET_IDS:
        declaration = payne["files"][target_id]
        path = planetary_spectra_dir / declaration["filename"]
        _verify_declared_file(path, declaration, f"{target_id} spectrum")
        spectra[target_id] = {
            **_receipt(path),
            "record_doi": payne["record_doi"],
        }
    cie: dict[str, Any] = {}
    for role in ("cie_photopic", "cie_scotopic"):
        declaration = declarations[role]
        path = cie_root / declaration["filename"]
        _verify_declared_file(path, declaration, role)
        cie[role] = {
            **_receipt(path),
            "dataset_doi": declaration["dataset_doi"],
        }
    solar_declaration = declarations["solar_spectrum"]
    mallama_declaration = declarations[
        "mallama_planetary_photometry"
    ]
    _verify_declared_file(
        solar_spectrum,
        solar_declaration,
        "solar spectrum",
    )
    _verify_declared_file(
        mallama_pdf,
        mallama_declaration,
        "Mallama paper",
    )
    return {
        "payne_planetary_spectra": spectra,
        "cie": cie,
        "solar_spectrum": {
            **_receipt(solar_spectrum),
            "source_id": solar_declaration["source_id"],
        },
        "mallama_planetary_photometry": {
            **_receipt(mallama_pdf),
            "publication_doi": mallama_declaration["publication_doi"],
            "arxiv_id": mallama_declaration["arxiv_id"],
        },
    }


def _expected_profiles(
    spec: dict[str, Any],
    receipts: dict[str, Any],
    *,
    planetary_spectra_dir: Path,
    cie_root: Path,
    solar_spectrum: Path,
) -> dict[str, Any]:
    declarations = spec["source_inputs"]
    bins = tuple(float(value) for value in range(380, 780))
    if spec["spectral_bins"] != {
        "coordinate": "bin_start_vacuum_nm",
        "start_nm": 380.0,
        "width_nm": 1.0,
        "count": 400,
    }:
        raise ValidationError("spectral-bin specification differs")
    photopic = _cie_values(
        cie_root / declarations["cie_photopic"]["filename"]
    )
    scotopic = _cie_values(
        cie_root / declarations["cie_scotopic"]["filename"]
    )
    solar = _solar_rows(solar_spectrum)
    profiles: list[dict[str, Any]] = []
    for target_id in TARGET_IDS:
        planet_declaration = declarations[
            "payne_planetary_spectra"
        ]["files"][target_id]
        albedo = _planet_rows(
            planetary_spectra_dir / planet_declaration["filename"]
        )
        energy = tuple(
            _linear_sample(albedo, wavelength / 1000.0)
            * _linear_sample(solar, wavelength)
            for wavelength in bins
        )
        photopic_integrand = tuple(
            energy[index] * photopic[int(wavelength)]
            for index, wavelength in enumerate(bins)
        )
        scotopic_integrand = tuple(
            energy[index] * scotopic[int(wavelength)]
            for index, wavelength in enumerate(bins)
        )
        photopic_total = math.fsum(photopic_integrand)
        scotopic_total = math.fsum(scotopic_integrand)
        if photopic_total <= 0.0 or scotopic_total <= 0.0:
            raise ValidationError(
                f"{target_id} response integral is nonpositive"
            )
        color_model = dict(spec["color_models"][target_id])
        color_model.pop("source_note", None)
        color_model.setdefault("limitations", [])
        derivation_receipt = {
            "target_id": target_id,
            "source_receipts": {
                "planetary_spectrum": receipts[
                    "payne_planetary_spectra"
                ][target_id],
                "cie": receipts["cie"],
                "solar_spectrum": receipts["solar_spectrum"],
                "mallama_planetary_photometry": receipts[
                    "mallama_planetary_photometry"
                ],
            },
            "derivation": spec["derivation"],
            "color_model": color_model,
        }
        profiles.append(
            {
                "target_id": target_id,
                "spectral_profile_id": (
                    f"payne_2026_{target_id.lower()}_cie_response_v1"
                ),
                "spectral_source_ids": [
                    "Payne_et_al:2026:10.3847/PSJ/ae2feb",
                    "Zenodo:10.5281/zenodo.17470005",
                    (
                        "Mallama_et_al:2017:"
                        "10.1016/j.icarus.2016.09.023"
                    ),
                    "CIE:10.25039/CIE.DS.dktna2s3",
                    "CIE:10.25039/CIE.DS.gr6w4b5g",
                    declarations["solar_spectrum"]["source_id"],
                ],
                "spectral_source_receipt_sha256": _sha256_bytes(
                    _canonical_json(derivation_receipt)
                ),
                "base_scotopic_to_photopic_ratio": (
                    declarations["cie_scotopic"][
                        "luminous_efficacy_lm_per_w"
                    ]
                    * scotopic_total
                    / (
                        declarations["cie_photopic"][
                            "luminous_efficacy_lm_per_w"
                        ]
                        * photopic_total
                    )
                ),
                "base_photopic_extinction_weights": [
                    value / photopic_total
                    for value in photopic_integrand
                ],
                "base_scotopic_extinction_weights": [
                    value / scotopic_total
                    for value in scotopic_integrand
                ],
                "color_model": color_model,
            }
        )
    return {
        "schema": (
            "moira.physical-heliacal-visibility-target-profiles/v1"
        ),
        "status": "complete_immutable_target_profiles",
        "catalog_id": (
            "payne_2026_mallama_2017_cie_target_profiles_v1"
        ),
        "spectral_bins": spec["spectral_bins"],
        "color_warp_method": spec["derivation"][
            "color_warp_method"
        ],
        "profiles": profiles,
    }


def _payload_receipts(
    pack: Path,
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    roles = manifest.get("file_roles")
    payloads = manifest.get("payload_files")
    if (
        not isinstance(roles, dict)
        or not isinstance(payloads, list)
        or manifest.get("payload_file_count") != len(payloads)
        or len(payloads) != len(roles)
    ):
        raise ValidationError("pack inventory receipt is malformed")
    expected = set(roles.values()) | {MANIFEST_NAME}
    if {path.name for path in pack.iterdir()} != expected:
        raise ValidationError("pack root inventory differs")
    result: dict[str, dict[str, Any]] = {}
    for item in payloads:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or item["path"] in result
        ):
            raise ValidationError("payload receipt is malformed")
        result[item["path"]] = item
    if set(result) != set(roles.values()):
        raise ValidationError("payload paths differ from file roles")
    for filename, receipt in result.items():
        _verify_declared_file(
            pack / filename,
            receipt,
            f"payload {filename}",
        )
    checksum_lines = (
        pack / roles["checksums"]
    ).read_text(encoding="ascii").splitlines()
    checksum_map = {
        fields[1]: fields[0]
        for fields in (
            line.split("  ", maxsplit=1)
            for line in checksum_lines
        )
        if len(fields) == 2
    }
    expected_checksum_names = set(roles.values()) - {
        roles["checksums"]
    }
    if set(checksum_map) != expected_checksum_names or any(
        checksum_map[name] != _sha256(pack / name)
        for name in expected_checksum_names
    ):
        raise ValidationError("SHA256SUMS differs")
    return result


def validate(
    *,
    pack: Path,
    expected_manifest_sha256: str,
    spec_path: Path,
    compatibility_path: Path,
    base_pack: Path,
    planetary_spectra_dir: Path,
    cie_root: Path,
    solar_spectrum: Path,
    mallama_pdf: Path,
) -> dict[str, Any]:
    if not pack.is_dir() or pack.is_symlink():
        raise ValidationError("pack must be an explicit regular directory")
    spec = _json(spec_path, "Phase 2 specification")
    compatibility = _json(
        compatibility_path,
        "Phase 2 compatibility contract",
    )
    manifest_path = pack / MANIFEST_NAME
    if (
        not manifest_path.is_file()
        or _sha256(manifest_path) != expected_manifest_sha256
    ):
        raise ValidationError("root manifest identity differs")
    manifest = _json(manifest_path, "root manifest")
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-phase2-pack-spec/v1"
        or manifest.get("status") != "complete_immutable_data_pack"
        or manifest.get("pack_id") != spec["pack"]["pack_id"]
        or manifest.get("version") != spec["pack"]["version"]
        or manifest.get("compatibility_id")
        != compatibility.get("compatibility_id")
        or manifest.get("target_profile_contract")
        != compatibility.get("target_profiles")
        or manifest.get("capabilities")
        != compatibility.get("required_capabilities")
        or manifest.get("root_manifest_receipt_owner")
        != "source_controlled_phase2_closure_checkpoint"
    ):
        raise ValidationError("root manifest contract differs")
    compatibility_receipt = manifest.get("compatibility_contract")
    if (
        not isinstance(compatibility_receipt, dict)
        or compatibility_receipt.get("bytes")
        != compatibility_path.stat().st_size
        or compatibility_receipt.get("sha256")
        != _sha256(compatibility_path)
    ):
        raise ValidationError("compatibility receipt differs")
    payloads = _payload_receipts(pack, manifest)

    base_manifest_path = base_pack / MANIFEST_NAME
    if (
        not base_manifest_path.is_file()
        or _sha256(base_manifest_path)
        != spec["base_pack"]["manifest_sha256"]
    ):
        raise ValidationError("base-pack identity differs")
    base_manifest = _json(base_manifest_path, "base manifest")
    base_payloads = {
        item["path"]: item
        for item in base_manifest["payload_files"]
    }
    for role in BASE_ROLES:
        phase2_name = manifest["file_roles"][role]
        base_name = base_manifest["file_roles"][role]
        if (
            phase2_name != base_name
            or payloads[phase2_name] != base_payloads[base_name]
            or (pack / phase2_name).read_bytes()
            != (base_pack / base_name).read_bytes()
        ):
            raise ValidationError(
                f"base payload inheritance differs for {role}"
            )

    source_receipts = _source_receipts(
        spec,
        planetary_spectra_dir=planetary_spectra_dir,
        cie_root=cie_root,
        solar_spectrum=solar_spectrum,
        mallama_pdf=mallama_pdf,
    )
    expected_profiles = _expected_profiles(
        spec,
        source_receipts,
        planetary_spectra_dir=planetary_spectra_dir,
        cie_root=cie_root,
        solar_spectrum=solar_spectrum,
    )
    expected_target_bytes = _canonical_json(expected_profiles)
    target_path = pack / manifest["file_roles"]["target_profiles"]
    if target_path.read_bytes() != expected_target_bytes:
        raise ValidationError(
            "planetary target payload differs from independent derivation"
        )
    target_sha256 = _sha256_bytes(expected_target_bytes)
    if (
        manifest.get("target_profile_artifact")
        != {
            "spec_id": spec["spec_id"],
            "target_profile_sha256": target_sha256,
        }
    ):
        raise ValidationError("target-profile root receipt differs")

    provenance = _json(
        pack / manifest["file_roles"]["provenance"],
        "provenance",
    )
    target_artifact = provenance.get("target_profile_artifact")
    tooling = provenance.get("tooling")
    if (
        not isinstance(target_artifact, dict)
        or target_artifact.get("spec_id") != spec["spec_id"]
        or target_artifact.get("target_profile_sha256")
        != target_sha256
        or target_artifact.get("source_input_receipts")
        != source_receipts
        or target_artifact.get("derivation") != spec["derivation"]
        or not isinstance(tooling, dict)
    ):
        raise ValidationError("target-profile provenance differs")
    tool_paths = {
        "builder": BUILDER_PATH,
        "specification": spec_path,
        "compatibility_contract": compatibility_path,
    }
    for role, path in tool_paths.items():
        receipt = tooling.get(role)
        if (
            not isinstance(receipt, dict)
            or receipt.get("bytes") != path.stat().st_size
            or receipt.get("sha256") != _sha256(path)
        ):
            raise ValidationError(f"{role} tooling receipt differs")

    expected_fingerprint = _sha256_bytes(
        _canonical_json(
            {
                "base_manifest_sha256": (
                    spec["base_pack"]["manifest_sha256"]
                ),
                "target_profile_sha256": target_sha256,
                "specification_sha256": _sha256(spec_path),
                "compatibility_sha256": _sha256(
                    compatibility_path
                ),
                "builder_sha256": _sha256(BUILDER_PATH),
            }
        )
    )
    if manifest.get("generation_fingerprint") != expected_fingerprint:
        raise ValidationError("generation fingerprint differs")

    return {
        "status": "accepted",
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "manifest_sha256": expected_manifest_sha256,
        "target_profile_sha256": target_sha256,
        "generation_fingerprint": expected_fingerprint,
        "payload_file_count": len(payloads),
        "target_ids": list(TARGET_IDS),
        "base_payload_roles_verified": list(BASE_ROLES),
        "network_used": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument(
        "--expected-manifest-sha256",
        required=True,
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--compatibility",
        type=Path,
        default=DEFAULT_COMPATIBILITY,
    )
    parser.add_argument("--base-pack", type=Path, required=True)
    parser.add_argument(
        "--planetary-spectra-dir",
        type=Path,
        required=True,
    )
    parser.add_argument("--cie-root", type=Path, required=True)
    parser.add_argument("--solar-spectrum", type=Path, required=True)
    parser.add_argument("--mallama-pdf", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = validate(
            pack=arguments.pack.resolve(),
            expected_manifest_sha256=(
                arguments.expected_manifest_sha256
            ),
            spec_path=arguments.spec.resolve(),
            compatibility_path=arguments.compatibility.resolve(),
            base_pack=arguments.base_pack.resolve(),
            planetary_spectra_dir=(
                arguments.planetary_spectra_dir.resolve()
            ),
            cie_root=arguments.cie_root.resolve(),
            solar_spectrum=arguments.solar_spectrum.resolve(),
            mallama_pdf=arguments.mallama_pdf.resolve(),
        )
    except (OSError, ValidationError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
