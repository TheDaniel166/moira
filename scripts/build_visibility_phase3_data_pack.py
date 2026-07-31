"""Build the immutable Phase 3 physical-visibility data pack.

The builder extends, but never mutates, the admitted Phase 2 pack.  It consumes
only explicit local source paths, verifies every declared identity, derives the
first source-complete stellar response profile, and writes a new versioned
directory.  It never opens a network connection or copies CALSPEC, BSC5, or
CIE source files into the resulting pack.

Astropy is a development-only FITS reader used by this offline build surface.
The installed Moira runtime neither imports Astropy nor parses the CALSPEC
source file.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "scripts" / "visibility_reference_lab"
DEFAULT_SPEC_PATH = (
    LAB_ROOT / "phase3_stellar_target_profile_pack_spec.json"
)
DEFAULT_COMPATIBILITY_PATH = (
    LAB_ROOT
    / "physical_heliacal_visibility_data_pack_compatibility_v1_2.json"
)
MANIFEST_NAME = "manifest.json"
STELLAR_PROFILE_FILENAME = "stellar-target-profiles.json"
STELLAR_PROFILE_SCHEMA = (
    "moira.physical-heliacal-visibility-stellar-target-profiles/v1"
)
STELLAR_CATALOG_ID = "calspec_bsc5_cie_stellar_profiles_v1"
BASE_COPY_ROLES = (
    "axes",
    "direct_extinction",
    "error_envelope",
    "photopic_luminance",
    "photopic_relative_standard_error",
    "scotopic_luminance",
    "scotopic_relative_standard_error",
    "target_profiles",
)


class VisibilityPhase3PackError(ValueError):
    """Raised when the Phase 3 pack cannot be built exactly."""


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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_receipt(
    path: Path,
    *,
    relative_to: Path | None = None,
) -> dict[str, Any]:
    display = (
        path.relative_to(relative_to).as_posix()
        if relative_to is not None
        else path.name
    )
    return {
        "path": display,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VisibilityPhase3PackError(
            f"invalid {label}: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise VisibilityPhase3PackError(f"{label} must be an object")
    return value


def verify_receipt(
    path: Path,
    receipt: dict[str, Any],
    label: str,
) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != receipt.get("bytes")
        or sha256_file(path) != receipt.get("sha256")
    ):
        raise VisibilityPhase3PackError(f"{label} identity differs")


def validate_base_pack(
    base_pack: Path,
    declaration: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    if not base_pack.is_dir() or base_pack.is_symlink():
        raise VisibilityPhase3PackError(
            "base pack must be a regular explicit directory"
        )
    manifest_path = base_pack / MANIFEST_NAME
    if (
        not manifest_path.is_file()
        or manifest_path.is_symlink()
        or sha256_file(manifest_path)
        != declaration.get("manifest_sha256")
    ):
        raise VisibilityPhase3PackError(
            "base-pack manifest identity differs"
        )
    manifest = load_json(manifest_path, "base-pack manifest")
    if (
        manifest.get("status") != "complete_immutable_data_pack"
        or manifest.get("pack_id") != declaration.get("pack_id")
        or manifest.get("version") != declaration.get("version")
    ):
        raise VisibilityPhase3PackError(
            "base-pack identity or status differs"
        )
    raw_roles = manifest.get("file_roles")
    payloads = manifest.get("payload_files")
    if not isinstance(raw_roles, dict) or not isinstance(payloads, list):
        raise VisibilityPhase3PackError(
            "base-pack inventory is malformed"
        )
    if any(
        not isinstance(role, str)
        or not isinstance(filename, str)
        for role, filename in raw_roles.items()
    ):
        raise VisibilityPhase3PackError(
            "base-pack file roles are malformed"
        )
    roles = dict(raw_roles)
    receipts = {
        item.get("path"): item
        for item in payloads
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if len(receipts) != len(payloads):
        raise VisibilityPhase3PackError(
            "base-pack payload receipts are malformed"
        )
    expected_names = set(roles.values()) | {MANIFEST_NAME}
    if {path.name for path in base_pack.iterdir()} != expected_names:
        raise VisibilityPhase3PackError(
            "base-pack root inventory differs"
        )
    for filename, receipt in receipts.items():
        verify_receipt(
            base_pack / filename,
            receipt,
            f"base-pack payload {filename}",
        )
    if tuple(declaration.get("immutable_payload_roles", ())) != BASE_COPY_ROLES:
        raise VisibilityPhase3PackError(
            "base-pack copy policy differs"
        )
    if any(role not in roles for role in BASE_COPY_ROLES):
        raise VisibilityPhase3PackError(
            "base-pack immutable role is missing"
        )
    return manifest, roles


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
    verify_receipt(calspec_spectrum, calspec, "CALSPEC Sirius spectrum")
    verify_receipt(bsc5_query, bsc5, "BSC5 Sirius query")
    verify_receipt(
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
        verify_receipt(path, declaration, role)
        cie[role] = {
            **file_receipt(path),
            "dataset_doi": declaration["dataset_doi"],
        }
    return {
        "calspec_sirius": {
            **file_receipt(calspec_spectrum),
            "source_url": calspec["source_url"],
            "spectrum_id": calspec["spectrum_id"],
        },
        "bsc5_sirius_query": {
            **file_receipt(bsc5_query),
            "catalog_id": bsc5["catalog_id"],
            "query_url": bsc5["query_url"],
        },
        "bsc5_readme": {
            **file_receipt(bsc5_readme),
            "catalog_id": bsc5["catalog_id"],
        },
        "cie": cie,
    }


def load_cie(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            for row in csv.reader(stream):
                if len(row) != 2:
                    raise VisibilityPhase3PackError(
                        f"invalid CIE row in {path.name}"
                    )
                wavelength = int(row[0])
                value = float(row[1])
                if (
                    wavelength in result
                    or not math.isfinite(value)
                    or value < 0.0
                ):
                    raise VisibilityPhase3PackError(
                        f"invalid CIE value in {path.name}"
                    )
                result[wavelength] = value
    except (OSError, UnicodeError, ValueError) as exc:
        raise VisibilityPhase3PackError(
            f"invalid CIE table: {path.name}"
        ) from exc
    if any(wavelength not in result for wavelength in range(380, 780)):
        raise VisibilityPhase3PackError(
            f"CIE table does not cover 380--779 nm: {path.name}"
        )
    return result


def load_calspec(
    path: Path,
) -> tuple[tuple[float, float], ...]:
    try:
        from astropy.io import fits
    except ImportError as exc:
        raise VisibilityPhase3PackError(
            "offline CALSPEC build requires the declared dev Astropy extra"
        ) from exc

    try:
        with fits.open(path, mode="readonly", memmap=False) as hdus:
            if len(hdus) != 2 or hdus[1].name != "SCI":
                raise VisibilityPhase3PackError(
                    "CALSPEC FITS HDU inventory differs"
                )
            table = hdus[1].data
            columns = tuple(hdus[1].columns.names)
            if columns != (
                "WAVELENGTH",
                "FLUX",
                "STATERROR",
                "SYSERROR",
                "FWHM",
                "DATAQUAL",
                "TOTEXP",
            ):
                raise VisibilityPhase3PackError(
                    "CALSPEC FITS columns differ"
                )
            rows = tuple(
                (float(wavelength), float(flux))
                for wavelength, flux, quality in zip(
                    table["WAVELENGTH"],
                    table["FLUX"],
                    table["DATAQUAL"],
                )
                if int(quality) == 1
            )
    except VisibilityPhase3PackError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise VisibilityPhase3PackError(
            "invalid CALSPEC Sirius FITS source"
        ) from exc
    if len(rows) < 2:
        raise VisibilityPhase3PackError(
            "CALSPEC Sirius spectrum is incomplete"
        )
    previous = float("-inf")
    for wavelength, flux in rows:
        if (
            not math.isfinite(wavelength)
            or not math.isfinite(flux)
            or wavelength <= previous
            or flux <= 0.0
        ):
            raise VisibilityPhase3PackError(
                "CALSPEC Sirius spectrum values differ"
            )
        previous = wavelength
    if rows[0][0] > 3800.0 or rows[-1][0] < 7790.0:
        raise VisibilityPhase3PackError(
            "CALSPEC Sirius spectrum does not cover 380--779 nm"
        )
    return rows


def interpolate_series(
    rows: tuple[tuple[float, float], ...],
    wavelength: float,
) -> float:
    coordinates = tuple(row[0] for row in rows)
    high = bisect.bisect_left(coordinates, wavelength)
    if high < len(rows) and coordinates[high] == wavelength:
        return rows[high][1]
    if high == 0 or high == len(rows):
        raise VisibilityPhase3PackError(
            f"source spectrum does not cover {wavelength}"
        )
    low = high - 1
    fraction = (wavelength - rows[low][0]) / (
        rows[high][0] - rows[low][0]
    )
    return rows[low][1] + fraction * (
        rows[high][1] - rows[low][1]
    )


def load_bsc5_sirius(path: Path) -> dict[str, Any]:
    try:
        rows = tuple(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("2491\t")
        )
    except (OSError, UnicodeError) as exc:
        raise VisibilityPhase3PackError(
            "invalid BSC5 Sirius query"
        ) from exc
    if len(rows) != 1:
        raise VisibilityPhase3PackError(
            "BSC5 Sirius query must contain one catalog row"
        )
    fields = rows[0].split("\t")
    if len(fields) != 6:
        raise VisibilityPhase3PackError(
            "BSC5 Sirius query columns differ"
        )
    try:
        result = {
            "hr_id": int(fields[0].strip()),
            "catalog_name": fields[1].strip(),
            "hd_id": int(fields[2].strip()),
            "visual_magnitude": float(fields[3].strip()),
            "visual_magnitude_code": fields[4].strip(),
            "b_minus_v": float(fields[5].strip()),
        }
    except ValueError as exc:
        raise VisibilityPhase3PackError(
            "BSC5 Sirius values differ"
        ) from exc
    if result != {
        "hr_id": 2491,
        "catalog_name": "9Alp CMa",
        "hd_id": 48915,
        "visual_magnitude": -1.46,
        "visual_magnitude_code": "",
        "b_minus_v": 0.0,
    }:
        raise VisibilityPhase3PackError(
            "BSC5 Sirius source record differs"
        )
    return result


def derive_stellar_profiles(
    spec: dict[str, Any],
    *,
    calspec_spectrum: Path,
    bsc5_query: Path,
    cie_root: Path,
    source_receipts: dict[str, Any],
) -> dict[str, Any]:
    bins = tuple(
        spec["spectral_bins"]["start_nm"]
        + index * spec["spectral_bins"]["width_nm"]
        for index in range(spec["spectral_bins"]["count"])
    )
    if bins != tuple(float(value) for value in range(380, 780)):
        raise VisibilityPhase3PackError(
            "spectral-bin contract differs"
        )
    calspec = load_calspec(calspec_spectrum)
    bsc5 = load_bsc5_sirius(bsc5_query)
    cie_photopic = load_cie(
        cie_root / spec["source_inputs"]["cie_photopic"]["filename"]
    )
    cie_scotopic = load_cie(
        cie_root / spec["source_inputs"]["cie_scotopic"]["filename"]
    )
    flux = tuple(
        interpolate_series(calspec, wavelength * 10.0)
        for wavelength in bins
    )
    photopic_integrand = tuple(
        value * cie_photopic[int(wavelength)]
        for wavelength, value in zip(bins, flux)
    )
    scotopic_integrand = tuple(
        value * cie_scotopic[int(wavelength)]
        for wavelength, value in zip(bins, flux)
    )
    photopic_total = math.fsum(photopic_integrand)
    scotopic_total = math.fsum(scotopic_integrand)
    if photopic_total <= 0.0 or scotopic_total <= 0.0:
        raise VisibilityPhase3PackError(
            "Sirius response integral is nonpositive"
        )

    bsc5_source_receipt = sha256_bytes(
        canonical_json_bytes(
            {
                "query": source_receipts["bsc5_sirius_query"],
                "readme": source_receipts["bsc5_readme"],
                "catalog_record": bsc5,
                "visual_photometry": {
                    "system_id": "johnson_v",
                    "magnitude": -1.46,
                },
            }
        )
    )
    spectral_derivation_receipt = sha256_bytes(
        canonical_json_bytes(
            {
                "calspec": source_receipts["calspec_sirius"],
                "cie": source_receipts["cie"],
                "derivation": spec["derivation"],
                "target": spec["target"],
            }
        )
    )
    profile = {
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
            "source_receipt_sha256": bsc5_source_receipt,
        },
        "spectral_profile_id": spec["target"]["spectral_profile_id"],
        "spectral_source_ids": [
            "STScI:CALSPEC:sirius_stis_005",
            "Bohlin:2014:10.1088/0004-6256/147/6/127",
            "CIE:10.25039/CIE.DS.dktna2s3",
            "CIE:10.25039/CIE.DS.gr6w4b5g",
        ],
        "spectral_source_receipt_sha256": spectral_derivation_receipt,
        "base_scotopic_to_photopic_ratio": (
            spec["source_inputs"]["cie_scotopic"][
                "luminous_efficacy_lm_per_w"
            ]
            * scotopic_total
            / (
                spec["source_inputs"]["cie_photopic"][
                    "luminous_efficacy_lm_per_w"
                ]
                * photopic_total
            )
        ),
        "base_photopic_extinction_weights": [
            value / photopic_total for value in photopic_integrand
        ],
        "base_scotopic_extinction_weights": [
            value / scotopic_total for value in scotopic_integrand
        ],
        "limitations": spec["target"]["limitations"],
    }
    return {
        "schema": STELLAR_PROFILE_SCHEMA,
        "status": "complete_immutable_stellar_target_profiles",
        "catalog_id": STELLAR_CATALOG_ID,
        "spectral_bins": spec["spectral_bins"],
        "profiles": [profile],
    }


def build_pack(
    *,
    spec_path: Path,
    compatibility_path: Path,
    base_pack: Path,
    calspec_spectrum: Path,
    bsc5_query: Path,
    bsc5_readme: Path,
    cie_root: Path,
    output: Path,
) -> dict[str, Any]:
    spec = load_json(spec_path, "Phase 3 pack specification")
    compatibility = load_json(
        compatibility_path,
        "Phase 3 compatibility contract",
    )
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-phase3-pack-spec/v1"
        or spec.get("status") != "phase3_offline_pack_extension"
        or compatibility.get("status")
        != "phase3_engine_loader_contract"
        or compatibility.get("compatibility_id")
        != spec["pack"]["compatibility_id"]
        or spec["runtime_boundary"]
        != {
            "network_allowed": False,
            "automatic_download_allowed": False,
            "source_files_may_be_copied_to_pack": False,
            "generated_response_products_only": True,
            "base_pack_may_be_mutated": False,
            "caller_supplied_paths_required": True,
            "legacy_native_arcus_dispatch_allowed": False,
        }
    ):
        raise VisibilityPhase3PackError(
            "Phase 3 specification contract differs"
        )
    base_manifest, base_roles = validate_base_pack(
        base_pack,
        spec["base_pack"],
    )
    source_receipts = _source_receipts(
        spec,
        calspec_spectrum=calspec_spectrum,
        bsc5_query=bsc5_query,
        bsc5_readme=bsc5_readme,
        cie_root=cie_root,
    )
    stellar_profiles = derive_stellar_profiles(
        spec,
        calspec_spectrum=calspec_spectrum,
        bsc5_query=bsc5_query,
        cie_root=cie_root,
        source_receipts=source_receipts,
    )

    if output.exists():
        raise VisibilityPhase3PackError(
            "output path already exists; immutable packs are never replaced"
        )
    output.mkdir(parents=False)
    file_roles = {
        role: base_roles[role] for role in BASE_COPY_ROLES
    }
    file_roles.update(
        {
            "notice": "NOTICE.md",
            "provenance": "provenance.json",
            "readme": "README.md",
            "checksums": "SHA256SUMS",
            "stellar_target_profiles": STELLAR_PROFILE_FILENAME,
        }
    )
    for role in BASE_COPY_ROLES:
        shutil.copyfile(
            base_pack / base_roles[role],
            output / file_roles[role],
        )
    stellar_bytes = canonical_json_bytes(stellar_profiles)
    (output / STELLAR_PROFILE_FILENAME).write_bytes(stellar_bytes)

    base_provenance = load_json(
        base_pack / base_roles["provenance"],
        "base provenance",
    )
    provenance = {
        "schema": (
            "moira.physical-heliacal-visibility-data-pack-provenance/v1"
        ),
        "build_date": spec["build_date"],
        "excluded_source_files": [
            *base_provenance["excluded_source_files"],
            "CALSPEC_source_spectrum",
            "BSC5_query_and_catalog_files",
        ],
        "scientific_sources": {
            **base_provenance["scientific_sources"],
            "CALSPEC_Sirius": {
                "spectrum_id": spec["source_inputs"]["calspec_sirius"][
                    "spectrum_id"
                ],
                "source_url": spec["source_inputs"]["calspec_sirius"][
                    "source_url"
                ],
                "publication_doi": spec["source_inputs"][
                    "calspec_publication"
                ]["publication_doi"],
                "systematic_fraction": spec["source_inputs"][
                    "calspec_sirius"
                ]["systematic_fraction"],
                "data_use_disposition": spec["source_inputs"][
                    "calspec_sirius"
                ]["data_use_disposition"],
            },
            "BSC5_Sirius_photometry": {
                "catalog_id": "V/50",
                "hr_id": 2491,
                "hd_id": 48915,
                "visual_system_id": "johnson_v",
                "visual_magnitude": -1.46,
                "data_use_disposition": spec["source_inputs"][
                    "bsc5_sirius_photometry"
                ]["data_use_disposition"],
            },
        },
        "source_artifact": base_manifest["source_artifact"],
        "base_pack": {
            "pack_id": spec["base_pack"]["pack_id"],
            "version": spec["base_pack"]["version"],
            "manifest_sha256": spec["base_pack"]["manifest_sha256"],
        },
        "target_profile_artifact": base_provenance[
            "target_profile_artifact"
        ],
        "stellar_target_profile_artifact": {
            "spec_id": spec["spec_id"],
            "stellar_target_profile_sha256": sha256_bytes(stellar_bytes),
            "source_input_receipts": source_receipts,
            "derivation": spec["derivation"],
        },
        "tooling": {
            "builder": file_receipt(
                Path(__file__).resolve(),
                relative_to=REPO_ROOT,
            ),
            "specification": file_receipt(
                spec_path,
                relative_to=REPO_ROOT,
            ),
            "compatibility_contract": file_receipt(
                compatibility_path,
                relative_to=REPO_ROOT,
            ),
        },
    }
    (output / file_roles["provenance"]).write_bytes(
        canonical_json_bytes(provenance)
    )
    base_notice = (
        base_pack / base_roles["notice"]
    ).read_text(encoding="utf-8")
    if not base_notice.endswith("\n"):
        raise VisibilityPhase3PackError(
            "base-pack notice must end with a newline"
        )
    (output / file_roles["notice"]).write_text(
        (
            base_notice
            + "\n## Phase 3 stellar-profile attribution\n\n"
            "The Sirius response profile is derived from the public STScI "
            "CALSPEC file sirius_stis_005.fits and the calibration lineage "
            "documented by Bohlin (2014), DOI "
            "10.1088/0004-6256/147/6/127. MAST and STScI are acknowledged "
            "as the archive and calibration providers.\n\n"
            "Johnson V=-1.46 and the HR 2491/HD 48915 identity are attributed "
            "to the Bright Star Catalogue, Fifth Revised Edition, VizieR "
            "catalog V/50 (Hoffleit and Warren). Only the attributed scalar "
            "fact is carried; the VizieR query and catalog are not "
            "redistributed.\n\n"
            "No CALSPEC FITS file or BSC5 table is redistributed.\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    (output / file_roles["readme"]).write_text(
        (
            "# Moira Physical Heliacal Visibility Data Pack 1.2.0\n\n"
            "Supply this immutable directory through an explicit "
            "caller-supplied directory path. No component may download, "
            "search for, regenerate, or silently replace it.\n\n"
            "Version 1.2.0 preserves every admitted Phase 2 table and "
            "planetary profile byte and adds one source-complete fixed-star "
            "profile for Sirius. Other fixed stars remain typed unsupported. "
            "The profile consumes no generic catalog color-index field and "
            "never invokes legacy native arcus dispatch.\n"
        ),
        encoding="utf-8",
        newline="\n",
    )

    names_without_checksums = sorted(
        set(file_roles.values()) - {file_roles["checksums"]}
    )
    (output / file_roles["checksums"]).write_text(
        "".join(
            f"{sha256_file(output / name)}  {name}\n"
            for name in names_without_checksums
        ),
        encoding="ascii",
        newline="\n",
    )
    payloads = [
        {
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha256_file(output / name),
        }
        for name in sorted(file_roles.values())
    ]
    generation_fingerprint = sha256_bytes(
        canonical_json_bytes(
            {
                "base_manifest_sha256": spec["base_pack"][
                    "manifest_sha256"
                ],
                "stellar_target_profile_sha256": sha256_bytes(
                    stellar_bytes
                ),
                "specification_sha256": sha256_file(spec_path),
                "compatibility_sha256": sha256_file(
                    compatibility_path
                ),
                "builder_sha256": sha256_file(
                    Path(__file__).resolve()
                ),
            }
        )
    )
    manifest = {
        "schema": spec["pack"]["manifest_schema"],
        "status": "complete_immutable_data_pack",
        "pack_id": spec["pack"]["pack_id"],
        "version": spec["pack"]["version"],
        "compatibility_id": spec["pack"]["compatibility_id"],
        "composite_model_id": spec["pack"]["composite_model_id"],
        "table_format_id": spec["pack"]["table_format_id"],
        "license": spec["pack"]["license"],
        "capabilities": compatibility["required_capabilities"],
        "interpolation": {
            "radiance": compatibility["radiance_interpolation"],
            "direct_extinction": compatibility[
                "direct_extinction_interpolation"
            ],
        },
        "radiance_reference": compatibility["radiance_reference"],
        "target_profile_contract": compatibility["target_profiles"],
        "stellar_target_profile_contract": compatibility[
            "stellar_target_profiles"
        ],
        "binary_representation": compatibility[
            "binary_representation"
        ],
        "root_manifest_receipt_owner": (
            "source_controlled_phase3_closure_receipt"
        ),
        "compatibility_contract": file_receipt(
            compatibility_path,
            relative_to=REPO_ROOT,
        ),
        "generation_fingerprint": generation_fingerprint,
        "deep_twilight_law": base_manifest["deep_twilight_law"],
        "effective_domain": base_manifest["effective_domain"],
        "file_roles": file_roles,
        "payload_file_count": len(payloads),
        "payload_files": payloads,
        "source_artifact": base_manifest["source_artifact"],
        "base_pack": provenance["base_pack"],
        "target_profile_artifact": base_manifest[
            "target_profile_artifact"
        ],
        "stellar_target_profile_artifact": {
            "spec_id": spec["spec_id"],
            "stellar_target_profile_sha256": sha256_bytes(
                stellar_bytes
            ),
        },
    }
    manifest_bytes = canonical_json_bytes(manifest)
    (output / MANIFEST_NAME).write_bytes(manifest_bytes)
    return {
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "output": str(output),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "stellar_target_profile_sha256": sha256_bytes(stellar_bytes),
        "generation_fingerprint": generation_fingerprint,
        "payload_file_count": len(payloads),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    result.add_argument(
        "--compatibility",
        type=Path,
        default=DEFAULT_COMPATIBILITY_PATH,
    )
    result.add_argument("--base-pack", type=Path, required=True)
    result.add_argument("--calspec-spectrum", type=Path, required=True)
    result.add_argument("--bsc5-query", type=Path, required=True)
    result.add_argument("--bsc5-readme", type=Path, required=True)
    result.add_argument("--cie-root", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        receipt = build_pack(
            spec_path=arguments.spec.resolve(),
            compatibility_path=arguments.compatibility.resolve(),
            base_pack=arguments.base_pack.resolve(),
            calspec_spectrum=arguments.calspec_spectrum.resolve(),
            bsc5_query=arguments.bsc5_query.resolve(),
            bsc5_readme=arguments.bsc5_readme.resolve(),
            cie_root=arguments.cie_root.resolve(),
            output=arguments.output.resolve(),
        )
    except VisibilityPhase3PackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
