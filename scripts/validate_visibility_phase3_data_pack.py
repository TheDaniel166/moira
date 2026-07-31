"""Independently validate one immutable Phase 3 visibility data pack.

This read-only validator imports neither the pack builder nor Moira.  It
recomputes the Sirius response from explicit checksum-locked CALSPEC, BSC5,
and CIE sources, verifies byte-for-byte Phase 2 inheritance, and checks the
complete Phase 3 inventory, attribution, provenance, and generation receipts.
It never uses a network.
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
DEFAULT_SPEC = LAB_ROOT / "phase3_stellar_target_profile_pack_spec.json"
DEFAULT_COMPATIBILITY = (
    LAB_ROOT
    / "physical_heliacal_visibility_data_pack_compatibility_v1_2.json"
)
BUILDER_PATH = REPO_ROOT / "scripts" / "build_visibility_phase3_data_pack.py"
MANIFEST_NAME = "manifest.json"
STELLAR_PROFILE_FILENAME = "stellar-target-profiles.json"
BASE_ROLES = (
    "axes",
    "direct_extinction",
    "error_envelope",
    "photopic_luminance",
    "photopic_relative_standard_error",
    "scotopic_luminance",
    "scotopic_relative_standard_error",
    "target_profiles",
)


class ValidationError(ValueError):
    """Raised when any independent Phase 3 admission check fails."""


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


def _verify_file(
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


def _inventory(
    pack: Path,
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    roles = manifest.get("file_roles")
    payloads = manifest.get("payload_files")
    if (
        not isinstance(roles, dict)
        or not isinstance(payloads, list)
        or manifest.get("payload_file_count") != len(payloads)
        or len(roles) != len(payloads)
        or any(
            not isinstance(role, str) or not isinstance(name, str)
            for role, name in roles.items()
        )
    ):
        raise ValidationError("pack inventory receipt is malformed")
    expected_names = set(roles.values()) | {MANIFEST_NAME}
    if {path.name for path in pack.iterdir()} != expected_names:
        raise ValidationError("pack root inventory differs")
    receipts: dict[str, dict[str, Any]] = {}
    for item in payloads:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or item["path"] in receipts
        ):
            raise ValidationError("payload receipt is malformed")
        receipts[item["path"]] = item
    if set(receipts) != set(roles.values()):
        raise ValidationError("payload paths differ from file roles")
    for name, receipt in receipts.items():
        _verify_file(pack / name, receipt, f"payload {name}")

    checksum_path = pack / roles["checksums"]
    try:
        checksum_pairs = tuple(
            line.split("  ", maxsplit=1)
            for line in checksum_path.read_text(
                encoding="ascii"
            ).splitlines()
        )
    except (OSError, UnicodeError) as exc:
        raise ValidationError("invalid SHA256SUMS") from exc
    if any(len(pair) != 2 for pair in checksum_pairs):
        raise ValidationError("SHA256SUMS row differs")
    checksum_map = {
        name: digest for digest, name in checksum_pairs
    }
    expected_checksum_names = set(roles.values()) - {
        roles["checksums"]
    }
    if (
        set(checksum_map) != expected_checksum_names
        or any(
            checksum_map[name] != _sha256(pack / name)
            for name in expected_checksum_names
        )
    ):
        raise ValidationError("SHA256SUMS differs")
    return receipts


def _source_receipts(
    spec: dict[str, Any],
    *,
    calspec_spectrum: Path,
    bsc5_query: Path,
    bsc5_readme: Path,
    cie_root: Path,
) -> dict[str, Any]:
    sources = spec["source_inputs"]
    calspec = sources["calspec_sirius"]
    bsc5 = sources["bsc5_sirius_photometry"]
    _verify_file(calspec_spectrum, calspec, "CALSPEC Sirius spectrum")
    _verify_file(bsc5_query, bsc5, "BSC5 Sirius query")
    _verify_file(
        bsc5_readme,
        {
            "bytes": bsc5["readme_bytes"],
            "sha256": bsc5["readme_sha256"],
        },
        "BSC5 ReadMe",
    )
    cie: dict[str, Any] = {}
    for role in ("cie_photopic", "cie_scotopic"):
        declaration = sources[role]
        path = cie_root / declaration["filename"]
        _verify_file(path, declaration, role)
        cie[role] = {
            **_receipt(path),
            "dataset_doi": declaration["dataset_doi"],
        }
    return {
        "calspec_sirius": {
            **_receipt(calspec_spectrum),
            "source_url": calspec["source_url"],
            "spectrum_id": calspec["spectrum_id"],
        },
        "bsc5_sirius_query": {
            **_receipt(bsc5_query),
            "catalog_id": bsc5["catalog_id"],
            "query_url": bsc5["query_url"],
        },
        "bsc5_readme": {
            **_receipt(bsc5_readme),
            "catalog_id": bsc5["catalog_id"],
        },
        "cie": cie,
    }


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
                response = float(row[1])
                if (
                    wavelength in result
                    or not math.isfinite(response)
                    or response < 0.0
                ):
                    raise ValidationError(
                        f"{path.name} response differs"
                    )
                result[wavelength] = response
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValidationError(f"invalid CIE table: {path.name}") from exc
    if set(range(380, 780)) - set(result):
        raise ValidationError(
            f"{path.name} does not cover every admitted bin"
        )
    return result


def _calspec_rows(path: Path) -> tuple[tuple[float, float], ...]:
    try:
        from astropy.io import fits
    except ImportError as exc:
        raise ValidationError(
            "independent CALSPEC validation requires dev Astropy"
        ) from exc
    try:
        with fits.open(path, mode="readonly", memmap=False) as hdus:
            if (
                len(hdus) != 2
                or hdus[1].name != "SCI"
                or tuple(hdus[1].columns.names)
                != (
                    "WAVELENGTH",
                    "FLUX",
                    "STATERROR",
                    "SYSERROR",
                    "FWHM",
                    "DATAQUAL",
                    "TOTEXP",
                )
            ):
                raise ValidationError("CALSPEC FITS structure differs")
            table = hdus[1].data
            rows = tuple(
                (float(wavelength), float(flux))
                for wavelength, flux, quality in zip(
                    table["WAVELENGTH"],
                    table["FLUX"],
                    table["DATAQUAL"],
                )
                if int(quality) == 1
            )
    except ValidationError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise ValidationError("invalid CALSPEC Sirius FITS") from exc
    if len(rows) < 2:
        raise ValidationError("CALSPEC Sirius spectrum is incomplete")
    previous = float("-inf")
    for wavelength, flux in rows:
        if (
            not math.isfinite(wavelength)
            or not math.isfinite(flux)
            or wavelength <= previous
            or flux <= 0.0
        ):
            raise ValidationError("CALSPEC Sirius values differ")
        previous = wavelength
    if rows[0][0] > 3800.0 or rows[-1][0] < 7790.0:
        raise ValidationError(
            "CALSPEC Sirius does not cover 380--779 nm"
        )
    return rows


def _interpolate(
    rows: tuple[tuple[float, float], ...],
    coordinate: float,
) -> float:
    coordinates = tuple(row[0] for row in rows)
    high = bisect.bisect_left(coordinates, coordinate)
    if high < len(rows) and coordinates[high] == coordinate:
        return rows[high][1]
    if high == 0 or high == len(rows):
        raise ValidationError(
            f"CALSPEC spectrum does not cover {coordinate}"
        )
    low = high - 1
    fraction = (
        (coordinate - coordinates[low])
        / (coordinates[high] - coordinates[low])
    )
    return rows[low][1] + fraction * (
        rows[high][1] - rows[low][1]
    )


def _bsc5_record(path: Path) -> dict[str, Any]:
    try:
        rows = tuple(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("2491\t")
        )
    except (OSError, UnicodeError) as exc:
        raise ValidationError("invalid BSC5 Sirius query") from exc
    if len(rows) != 1:
        raise ValidationError("BSC5 Sirius row count differs")
    fields = rows[0].split("\t")
    if len(fields) != 6:
        raise ValidationError("BSC5 Sirius columns differ")
    try:
        record = {
            "hr_id": int(fields[0].strip()),
            "catalog_name": fields[1].strip(),
            "hd_id": int(fields[2].strip()),
            "visual_magnitude": float(fields[3].strip()),
            "visual_magnitude_code": fields[4].strip(),
            "b_minus_v": float(fields[5].strip()),
        }
    except ValueError as exc:
        raise ValidationError("BSC5 Sirius values differ") from exc
    if record != {
        "hr_id": 2491,
        "catalog_name": "9Alp CMa",
        "hd_id": 48915,
        "visual_magnitude": -1.46,
        "visual_magnitude_code": "",
        "b_minus_v": 0.0,
    }:
        raise ValidationError("BSC5 Sirius record differs")
    return record


def _expected_stellar_profiles(
    spec: dict[str, Any],
    receipts: dict[str, Any],
    *,
    calspec_spectrum: Path,
    bsc5_query: Path,
    cie_root: Path,
) -> dict[str, Any]:
    if spec["spectral_bins"] != {
        "coordinate": "bin_start_vacuum_nm",
        "start_nm": 380.0,
        "width_nm": 1.0,
        "count": 400,
    }:
        raise ValidationError("spectral-bin specification differs")
    sources = spec["source_inputs"]
    wavelengths = tuple(float(value) for value in range(380, 780))
    calspec = _calspec_rows(calspec_spectrum)
    bsc5 = _bsc5_record(bsc5_query)
    photopic = _cie_values(
        cie_root / sources["cie_photopic"]["filename"]
    )
    scotopic = _cie_values(
        cie_root / sources["cie_scotopic"]["filename"]
    )
    fluxes = tuple(
        _interpolate(calspec, wavelength * 10.0)
        for wavelength in wavelengths
    )
    photopic_integrand = tuple(
        flux * photopic[int(wavelength)]
        for wavelength, flux in zip(wavelengths, fluxes)
    )
    scotopic_integrand = tuple(
        flux * scotopic[int(wavelength)]
        for wavelength, flux in zip(wavelengths, fluxes)
    )
    photopic_total = math.fsum(photopic_integrand)
    scotopic_total = math.fsum(scotopic_integrand)
    if photopic_total <= 0.0 or scotopic_total <= 0.0:
        raise ValidationError("Sirius response integral is nonpositive")
    photometry_receipt = _sha256_bytes(
        _canonical_json(
            {
                "query": receipts["bsc5_sirius_query"],
                "readme": receipts["bsc5_readme"],
                "catalog_record": bsc5,
                "visual_photometry": {
                    "system_id": "johnson_v",
                    "magnitude": -1.46,
                },
            }
        )
    )
    spectral_receipt = _sha256_bytes(
        _canonical_json(
            {
                "calspec": receipts["calspec_sirius"],
                "cie": receipts["cie"],
                "derivation": spec["derivation"],
                "target": spec["target"],
            }
        )
    )
    return {
        "schema": (
            "moira.physical-heliacal-visibility-stellar-target-profiles/v1"
        ),
        "status": "complete_immutable_stellar_target_profiles",
        "catalog_id": "calspec_bsc5_cie_stellar_profiles_v1",
        "spectral_bins": spec["spectral_bins"],
        "profiles": [
            {
                "target_id": "Sirius",
                "catalog_identity": spec["target"]["catalog_identity"],
                "visual_photometry": {
                    "system_id": "johnson_v",
                    "magnitude": -1.46,
                    "model_id": spec["target"]["photometry_model_id"],
                    "source_ids": [
                        "BSC5:V/50:HR2491",
                        "Hoffleit_Warren:1991",
                    ],
                    "source_receipt_sha256": photometry_receipt,
                },
                "spectral_profile_id": spec["target"][
                    "spectral_profile_id"
                ],
                "spectral_source_ids": [
                    "STScI:CALSPEC:sirius_stis_005",
                    "Bohlin:2014:10.1088/0004-6256/147/6/127",
                    "CIE:10.25039/CIE.DS.dktna2s3",
                    "CIE:10.25039/CIE.DS.gr6w4b5g",
                ],
                "spectral_source_receipt_sha256": spectral_receipt,
                "base_scotopic_to_photopic_ratio": (
                    sources["cie_scotopic"][
                        "luminous_efficacy_lm_per_w"
                    ]
                    * scotopic_total
                    / (
                        sources["cie_photopic"][
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
                "limitations": spec["target"]["limitations"],
            }
        ],
    }


def validate(
    *,
    pack: Path,
    expected_manifest_sha256: str,
    spec_path: Path,
    compatibility_path: Path,
    base_pack: Path,
    calspec_spectrum: Path,
    bsc5_query: Path,
    bsc5_readme: Path,
    cie_root: Path,
) -> dict[str, Any]:
    if not pack.is_dir() or pack.is_symlink():
        raise ValidationError("pack must be an explicit regular directory")
    spec = _json(spec_path, "Phase 3 specification")
    compatibility = _json(
        compatibility_path,
        "Phase 3 compatibility contract",
    )
    manifest_path = pack / MANIFEST_NAME
    base_identity = {
        "pack_id": spec["base_pack"]["pack_id"],
        "version": spec["base_pack"]["version"],
        "manifest_sha256": spec["base_pack"]["manifest_sha256"],
    }
    if (
        not manifest_path.is_file()
        or manifest_path.is_symlink()
        or _sha256(manifest_path) != expected_manifest_sha256
    ):
        raise ValidationError("root manifest identity differs")
    manifest = _json(manifest_path, "root manifest")
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-phase3-pack-spec/v1"
        or spec.get("status") != "phase3_offline_pack_extension"
        or manifest.get("schema") != spec["pack"]["manifest_schema"]
        or manifest.get("status") != "complete_immutable_data_pack"
        or manifest.get("pack_id") != spec["pack"]["pack_id"]
        or manifest.get("version") != spec["pack"]["version"]
        or manifest.get("compatibility_id")
        != compatibility.get("compatibility_id")
        or manifest.get("capabilities")
        != compatibility.get("required_capabilities")
        or manifest.get("target_profile_contract")
        != compatibility.get("target_profiles")
        or manifest.get("stellar_target_profile_contract")
        != compatibility.get("stellar_target_profiles")
        or manifest.get("root_manifest_receipt_owner")
        != "source_controlled_phase3_closure_receipt"
        or manifest.get("base_pack") != base_identity
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
    payloads = _inventory(pack, manifest)

    base_manifest_path = base_pack / MANIFEST_NAME
    if (
        not base_pack.is_dir()
        or base_pack.is_symlink()
        or not base_manifest_path.is_file()
        or _sha256(base_manifest_path)
        != spec["base_pack"]["manifest_sha256"]
    ):
        raise ValidationError("base-pack identity differs")
    base_manifest = _json(base_manifest_path, "base manifest")
    base_payloads = _inventory(base_pack, base_manifest)
    for role in BASE_ROLES:
        phase3_name = manifest["file_roles"][role]
        base_name = base_manifest["file_roles"][role]
        if (
            phase3_name != base_name
            or payloads[phase3_name] != base_payloads[base_name]
            or (pack / phase3_name).read_bytes()
            != (base_pack / base_name).read_bytes()
        ):
            raise ValidationError(
                f"base payload inheritance differs for {role}"
            )

    source_receipts = _source_receipts(
        spec,
        calspec_spectrum=calspec_spectrum,
        bsc5_query=bsc5_query,
        bsc5_readme=bsc5_readme,
        cie_root=cie_root,
    )
    expected_profiles = _expected_stellar_profiles(
        spec,
        source_receipts,
        calspec_spectrum=calspec_spectrum,
        bsc5_query=bsc5_query,
        cie_root=cie_root,
    )
    profile_bytes = _canonical_json(expected_profiles)
    profile_sha256 = _sha256_bytes(profile_bytes)
    profile_path = pack / manifest["file_roles"][
        "stellar_target_profiles"
    ]
    if profile_path.read_bytes() != profile_bytes:
        raise ValidationError(
            "stellar profile differs from independent derivation"
        )
    if manifest.get("stellar_target_profile_artifact") != {
        "spec_id": spec["spec_id"],
        "stellar_target_profile_sha256": profile_sha256,
    }:
        raise ValidationError("stellar-profile root receipt differs")

    provenance = _json(
        pack / manifest["file_roles"]["provenance"],
        "provenance",
    )
    stellar_artifact = provenance.get("stellar_target_profile_artifact")
    tooling = provenance.get("tooling")
    if (
        provenance.get("base_pack") != base_identity
        or not isinstance(stellar_artifact, dict)
        or stellar_artifact.get("spec_id") != spec["spec_id"]
        or stellar_artifact.get("stellar_target_profile_sha256")
        != profile_sha256
        or stellar_artifact.get("source_input_receipts")
        != source_receipts
        or stellar_artifact.get("derivation") != spec["derivation"]
        or not isinstance(tooling, dict)
    ):
        raise ValidationError("stellar-profile provenance differs")
    source_blocks = provenance.get("scientific_sources")
    if (
        not isinstance(source_blocks, dict)
        or source_blocks.get("CALSPEC_Sirius", {}).get("spectrum_id")
        != "sirius_stis_005"
        or source_blocks.get("BSC5_Sirius_photometry")
        != {
            "catalog_id": "V/50",
            "hr_id": 2491,
            "hd_id": 48915,
            "visual_system_id": "johnson_v",
            "visual_magnitude": -1.46,
            "data_use_disposition": spec["source_inputs"][
                "bsc5_sirius_photometry"
            ]["data_use_disposition"],
        }
    ):
        raise ValidationError("scientific-source provenance differs")
    for role, path in {
        "builder": BUILDER_PATH,
        "specification": spec_path,
        "compatibility_contract": compatibility_path,
    }.items():
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
                "base_manifest_sha256": spec["base_pack"][
                    "manifest_sha256"
                ],
                "stellar_target_profile_sha256": profile_sha256,
                "specification_sha256": _sha256(spec_path),
                "compatibility_sha256": _sha256(compatibility_path),
                "builder_sha256": _sha256(BUILDER_PATH),
            }
        )
    )
    if manifest.get("generation_fingerprint") != expected_fingerprint:
        raise ValidationError("generation fingerprint differs")

    base_notice = (
        base_pack / base_manifest["file_roles"]["notice"]
    ).read_text(encoding="utf-8")
    notice = (
        pack / manifest["file_roles"]["notice"]
    ).read_text(encoding="utf-8")
    if (
        not notice.startswith(base_notice)
        or "## Phase 3 stellar-profile attribution" not in notice
        or "sirius_stis_005.fits" not in notice
        or "Bright Star Catalogue" not in notice
        or "No CALSPEC FITS file or BSC5 table is redistributed." not in notice
    ):
        raise ValidationError("Phase 3 notice attribution differs")
    readme = (
        pack / manifest["file_roles"]["readme"]
    ).read_text(encoding="utf-8")
    if (
        "Data Pack 1.2.0" not in readme
        or "adds one source-complete fixed-star profile for Sirius" not in readme
        or "never invokes legacy native arcus dispatch" not in readme
    ):
        raise ValidationError("Phase 3 README boundary differs")

    return {
        "status": "accepted",
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "manifest_sha256": expected_manifest_sha256,
        "stellar_target_profile_sha256": profile_sha256,
        "generation_fingerprint": expected_fingerprint,
        "payload_file_count": len(payloads),
        "stellar_target_ids": ["Sirius"],
        "base_payload_roles_verified": list(BASE_ROLES),
        "network_used": False,
        "builder_or_runtime_imported": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--compatibility",
        type=Path,
        default=DEFAULT_COMPATIBILITY,
    )
    parser.add_argument("--base-pack", type=Path, required=True)
    parser.add_argument("--calspec-spectrum", type=Path, required=True)
    parser.add_argument("--bsc5-query", type=Path, required=True)
    parser.add_argument("--bsc5-readme", type=Path, required=True)
    parser.add_argument("--cie-root", type=Path, required=True)
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
            calspec_spectrum=arguments.calspec_spectrum.resolve(),
            bsc5_query=arguments.bsc5_query.resolve(),
            bsc5_readme=arguments.bsc5_readme.resolve(),
            cie_root=arguments.cie_root.resolve(),
        )
    except (OSError, ValidationError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
