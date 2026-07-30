"""Build the immutable Phase 2 physical-visibility data pack.

The builder extends, but never mutates, the admitted Phase 1 pack.  It consumes
only explicit local source paths, verifies every declared identity, derives
planetary response integrands, and writes a new versioned directory.  It never
opens a network connection or copies a third-party source table into the pack.
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
    LAB_ROOT / "phase2_planetary_target_profile_pack_spec.json"
)
DEFAULT_COMPATIBILITY_PATH = (
    LAB_ROOT
    / "physical_heliacal_visibility_data_pack_compatibility_v1_1.json"
)
MANIFEST_NAME = "manifest.json"
TARGET_PROFILE_FILENAME = "planetary-target-profiles.json"
TARGET_PROFILE_SCHEMA = (
    "moira.physical-heliacal-visibility-target-profiles/v1"
)
TARGET_CATALOG_ID = (
    "payne_2026_mallama_2017_cie_target_profiles_v1"
)
TARGET_IDS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
BASE_COPY_ROLES = (
    "axes",
    "direct_extinction",
    "error_envelope",
    "photopic_luminance",
    "photopic_relative_standard_error",
    "scotopic_luminance",
    "scotopic_relative_standard_error",
)


class VisibilityPhase2PackError(ValueError):
    """Raised when the Phase 2 pack cannot be built exactly."""


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
        raise VisibilityPhase2PackError(
            f"invalid {label}: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise VisibilityPhase2PackError(f"{label} must be an object")
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
        raise VisibilityPhase2PackError(f"{label} identity differs")


def validate_base_pack(
    base_pack: Path,
    declaration: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not base_pack.is_dir() or base_pack.is_symlink():
        raise VisibilityPhase2PackError(
            "base pack must be a regular explicit directory"
        )
    manifest_path = base_pack / MANIFEST_NAME
    if (
        not manifest_path.is_file()
        or sha256_file(manifest_path)
        != declaration["manifest_sha256"]
    ):
        raise VisibilityPhase2PackError(
            "base-pack manifest identity differs"
        )
    manifest = load_json(manifest_path, "base-pack manifest")
    if (
        manifest.get("status") != "complete_immutable_data_pack"
        or manifest.get("pack_id") != declaration["pack_id"]
        or manifest.get("version") != declaration["version"]
    ):
        raise VisibilityPhase2PackError(
            "base-pack identity or status differs"
        )
    roles = manifest.get("file_roles")
    payloads = manifest.get("payload_files")
    if not isinstance(roles, dict) or not isinstance(payloads, list):
        raise VisibilityPhase2PackError(
            "base-pack inventory is malformed"
        )
    receipts = {
        item.get("path"): item
        for item in payloads
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if len(receipts) != len(payloads):
        raise VisibilityPhase2PackError(
            "base-pack payload receipts are malformed"
        )
    expected_names = set(roles.values()) | {MANIFEST_NAME}
    if {path.name for path in base_pack.iterdir()} != expected_names:
        raise VisibilityPhase2PackError(
            "base-pack root inventory differs"
        )
    for filename, receipt in receipts.items():
        verify_receipt(
            base_pack / filename,
            receipt,
            f"base-pack payload {filename}",
        )
    if tuple(declaration["immutable_payload_roles"]) != BASE_COPY_ROLES:
        raise VisibilityPhase2PackError(
            "base-pack copy policy differs"
        )
    return manifest, roles


def validate_source_inputs(
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
        verify_receipt(path, declaration, f"{target_id} spectrum")
        spectra[target_id] = {
            **file_receipt(path),
            "record_doi": payne["record_doi"],
        }

    cie_receipts: dict[str, Any] = {}
    for role in ("cie_photopic", "cie_scotopic"):
        declaration = declarations[role]
        path = cie_root / declaration["filename"]
        verify_receipt(path, declaration, role)
        cie_receipts[role] = {
            **file_receipt(path),
            "dataset_doi": declaration["dataset_doi"],
        }

    solar_declaration = declarations["solar_spectrum"]
    verify_receipt(solar_spectrum, solar_declaration, "solar spectrum")
    mallama_declaration = declarations[
        "mallama_planetary_photometry"
    ]
    verify_receipt(
        mallama_pdf,
        mallama_declaration,
        "Mallama photometry paper",
    )
    return {
        "payne_planetary_spectra": spectra,
        "cie": cie_receipts,
        "solar_spectrum": {
            **file_receipt(solar_spectrum),
            "source_id": solar_declaration["source_id"],
        },
        "mallama_planetary_photometry": {
            **file_receipt(mallama_pdf),
            "publication_doi": mallama_declaration[
                "publication_doi"
            ],
            "arxiv_id": mallama_declaration["arxiv_id"],
        },
    }


def load_planetary_albedo(path: Path) -> tuple[tuple[float, float], ...]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["Wavelength", "Albedo"]:
                raise VisibilityPhase2PackError(
                    f"planetary spectrum columns differ: {path.name}"
                )
            all_rows = tuple(
                (float(row["Wavelength"]), float(row["Albedo"]))
                for row in reader
            )
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        raise VisibilityPhase2PackError(
            f"invalid planetary spectrum: {path.name}"
        ) from exc
    if not all_rows or any(
        not math.isfinite(wavelength)
        or not math.isfinite(value)
        or value < 0.0
        for wavelength, value in all_rows
    ):
        raise VisibilityPhase2PackError(
            f"{path.name} contains invalid source values"
        )
    visible_rows = tuple(
        (wavelength, value)
        for wavelength, value in all_rows
        if 0.30 <= wavelength <= 1.00
    )
    validate_strict_series(
        visible_rows,
        f"{path.name} visible subset",
        positive_value=True,
    )
    return visible_rows


def load_cie(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            for row in csv.reader(stream):
                if len(row) != 2:
                    raise VisibilityPhase2PackError(
                        f"invalid CIE row in {path.name}"
                    )
                wavelength = int(row[0])
                value = float(row[1])
                if (
                    wavelength in result
                    or not math.isfinite(value)
                    or value < 0.0
                ):
                    raise VisibilityPhase2PackError(
                        f"invalid CIE value in {path.name}"
                    )
                result[wavelength] = value
    except (OSError, UnicodeError, ValueError) as exc:
        raise VisibilityPhase2PackError(
            f"invalid CIE table: {path.name}"
        ) from exc
    if any(wavelength not in result for wavelength in range(380, 780)):
        raise VisibilityPhase2PackError(
            f"CIE table does not cover 380--779 nm: {path.name}"
        )
    return result


def load_solar_spectrum(
    path: Path,
) -> tuple[tuple[float, float], ...]:
    rows: list[tuple[float, float]] = []
    try:
        for line in path.read_text(encoding="ascii").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields = stripped.split()
            if len(fields) != 2:
                raise VisibilityPhase2PackError(
                    "invalid solar-spectrum row"
                )
            rows.append((float(fields[0]), float(fields[1])))
    except (OSError, UnicodeError, ValueError) as exc:
        raise VisibilityPhase2PackError(
            "invalid solar spectrum"
        ) from exc
    result = tuple(rows)
    validate_strict_series(
        result,
        path.name,
        positive_value=True,
    )
    return result


def validate_strict_series(
    rows: tuple[tuple[float, float], ...],
    label: str,
    *,
    positive_value: bool,
) -> None:
    if len(rows) < 2:
        raise VisibilityPhase2PackError(f"{label} is incomplete")
    last_wavelength = float("-inf")
    for wavelength, value in rows:
        if (
            not math.isfinite(wavelength)
            or not math.isfinite(value)
            or wavelength <= last_wavelength
            or (positive_value and value <= 0.0)
        ):
            raise VisibilityPhase2PackError(
                f"{label} values are invalid"
            )
        last_wavelength = wavelength


def interpolate_series(
    rows: tuple[tuple[float, float], ...],
    wavelength: float,
) -> float:
    x_values = tuple(row[0] for row in rows)
    high = bisect.bisect_left(x_values, wavelength)
    if high < len(rows) and x_values[high] == wavelength:
        return rows[high][1]
    if high == 0 or high == len(rows):
        raise VisibilityPhase2PackError(
            f"source spectrum does not cover {wavelength} nm"
        )
    low = high - 1
    fraction = (wavelength - rows[low][0]) / (
        rows[high][0] - rows[low][0]
    )
    return rows[low][1] + fraction * (
        rows[high][1] - rows[low][1]
    )


def derive_target_profiles(
    spec: dict[str, Any],
    *,
    planetary_spectra_dir: Path,
    cie_root: Path,
    solar_spectrum: Path,
    source_receipts: dict[str, Any],
) -> dict[str, Any]:
    bins = tuple(
        spec["spectral_bins"]["start_nm"]
        + index * spec["spectral_bins"]["width_nm"]
        for index in range(spec["spectral_bins"]["count"])
    )
    if bins != tuple(float(value) for value in range(380, 780)):
        raise VisibilityPhase2PackError(
            "spectral-bin contract differs"
        )
    cie_photopic = load_cie(
        cie_root
        / spec["source_inputs"]["cie_photopic"]["filename"]
    )
    cie_scotopic = load_cie(
        cie_root
        / spec["source_inputs"]["cie_scotopic"]["filename"]
    )
    solar = load_solar_spectrum(solar_spectrum)
    profiles: list[dict[str, Any]] = []
    for target_id in TARGET_IDS:
        declaration = spec["source_inputs"][
            "payne_planetary_spectra"
        ]["files"][target_id]
        albedo = load_planetary_albedo(
            planetary_spectra_dir / declaration["filename"]
        )
        energy = tuple(
            interpolate_series(albedo, wavelength / 1000.0)
            * interpolate_series(solar, wavelength)
            for wavelength in bins
        )
        photopic_integrand = tuple(
            value * cie_photopic[int(wavelength)]
            for wavelength, value in zip(bins, energy)
        )
        scotopic_integrand = tuple(
            value * cie_scotopic[int(wavelength)]
            for wavelength, value in zip(bins, energy)
        )
        photopic_total = math.fsum(photopic_integrand)
        scotopic_total = math.fsum(scotopic_integrand)
        if photopic_total <= 0.0 or scotopic_total <= 0.0:
            raise VisibilityPhase2PackError(
                f"{target_id} response integral is nonpositive"
            )
        color_model = dict(spec["color_models"][target_id])
        color_model.pop("source_note", None)
        color_model.setdefault("limitations", [])
        derivation_receipt = {
            "target_id": target_id,
            "source_receipts": {
                "planetary_spectrum": source_receipts[
                    "payne_planetary_spectra"
                ][target_id],
                "cie": source_receipts["cie"],
                "solar_spectrum": source_receipts["solar_spectrum"],
                "mallama_planetary_photometry": source_receipts[
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
                    "payne_2026_"
                    f"{target_id.lower()}_cie_response_v1"
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
                    spec["source_inputs"]["solar_spectrum"][
                        "source_id"
                    ],
                ],
                "spectral_source_receipt_sha256": sha256_bytes(
                    canonical_json_bytes(derivation_receipt)
                ),
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
        "schema": TARGET_PROFILE_SCHEMA,
        "status": "complete_immutable_target_profiles",
        "catalog_id": TARGET_CATALOG_ID,
        "spectral_bins": spec["spectral_bins"],
        "color_warp_method": spec["derivation"][
            "color_warp_method"
        ],
        "profiles": profiles,
    }


def build_pack(
    *,
    spec_path: Path,
    compatibility_path: Path,
    base_pack: Path,
    planetary_spectra_dir: Path,
    cie_root: Path,
    solar_spectrum: Path,
    mallama_pdf: Path,
    output: Path,
) -> dict[str, Any]:
    spec = load_json(spec_path, "Phase 2 pack specification")
    compatibility = load_json(
        compatibility_path,
        "Phase 2 compatibility contract",
    )
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-phase2-pack-spec/v1"
        or spec.get("status") != "phase2_offline_pack_extension"
        or compatibility.get("status") != "phase2_engine_loader_contract"
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
        }
    ):
        raise VisibilityPhase2PackError(
            "Phase 2 specification contract differs"
        )
    base_manifest, base_roles = validate_base_pack(
        base_pack,
        spec["base_pack"],
    )
    source_receipts = validate_source_inputs(
        spec,
        planetary_spectra_dir=planetary_spectra_dir,
        cie_root=cie_root,
        solar_spectrum=solar_spectrum,
        mallama_pdf=mallama_pdf,
    )
    target_profiles = derive_target_profiles(
        spec,
        planetary_spectra_dir=planetary_spectra_dir,
        cie_root=cie_root,
        solar_spectrum=solar_spectrum,
        source_receipts=source_receipts,
    )

    if output.exists():
        raise VisibilityPhase2PackError(
            "output path already exists; immutable packs are never replaced"
        )
    output.mkdir(parents=False)
    try:
        file_roles = {
            role: base_roles[role] for role in BASE_COPY_ROLES
        }
        file_roles.update(
            {
                "notice": "NOTICE.md",
                "provenance": "provenance.json",
                "readme": "README.md",
                "checksums": "SHA256SUMS",
                "target_profiles": TARGET_PROFILE_FILENAME,
            }
        )
        for role in BASE_COPY_ROLES:
            shutil.copyfile(
                base_pack / base_roles[role],
                output / file_roles[role],
            )
        target_bytes = canonical_json_bytes(target_profiles)
        (output / TARGET_PROFILE_FILENAME).write_bytes(target_bytes)

        provenance = {
            "schema": (
                "moira.physical-heliacal-visibility-data-pack-"
                "provenance/v1"
            ),
            "build_date": spec["build_date"],
            "excluded_source_files": [
                "CIE_source_tables",
                "libRadtran_binary",
                "libRadtran_profiles",
                "libRadtran_source",
                "REPTRAN_files",
                "Payne_planetary_source_spectra",
                "Mallama_publication_files",
                "solar_spectrum_source_file",
            ],
            "scientific_sources": {
                **load_json(
                    base_pack / base_roles["provenance"],
                    "base provenance",
                )["scientific_sources"],
                "Payne_planetary_spectra": {
                    "record_doi": spec["source_inputs"][
                        "payne_planetary_spectra"
                    ]["record_doi"],
                    "publication_doi": spec["source_inputs"][
                        "payne_planetary_spectra"
                    ]["publication_doi"],
                    "license": "CC-BY-4.0",
                },
                "Mallama_planetary_photometry": {
                    "publication_doi": spec["source_inputs"][
                        "mallama_planetary_photometry"
                    ]["publication_doi"],
                    "arxiv_id": "1609.05048",
                },
                "target_profile_solar_spectrum": {
                    "source_id": spec["source_inputs"][
                        "solar_spectrum"
                    ]["source_id"],
                    "sha256": spec["source_inputs"][
                        "solar_spectrum"
                    ]["sha256"],
                },
            },
            "source_artifact": base_manifest["source_artifact"],
            "base_pack": {
                "pack_id": spec["base_pack"]["pack_id"],
                "version": spec["base_pack"]["version"],
                "manifest_sha256": spec["base_pack"][
                    "manifest_sha256"
                ],
            },
            "target_profile_artifact": {
                "spec_id": spec["spec_id"],
                "target_profile_sha256": sha256_bytes(target_bytes),
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
        (output / file_roles["notice"]).write_text(
            (
                "# Notices\n\n"
                "This separately distributed data pack is licensed under "
                "Creative Commons Attribution-ShareAlike 4.0:\n"
                "https://creativecommons.org/licenses/by-sa/4.0/\n\n"
                "It contains generated response products derived from CIE "
                "datasets 10.25039/CIE.DS.dktna2s3 and "
                "10.25039/CIE.DS.gr6w4b5g (CC BY-SA 4.0).\n\n"
                "Planetary reflectance spectra are derived from Payne et al. "
                "(2026), DOI 10.3847/PSJ/ae2feb, versioned data record "
                "10.5281/zenodo.17470005 (CC BY 4.0).\n\n"
                "Broadband planetary color behavior is derived from Mallama "
                "et al. (2017), DOI 10.1016/j.icarus.2016.09.023.\n\n"
                "The extraterrestrial solar spectrum is identified from "
                "libRadtran 2.0.6 data/solar_flux/atlas_plus_modtran. "
                "No libRadtran source, executable, REPTRAN file, CIE source "
                "table, or planetary source spectrum is redistributed.\n"
            ),
            encoding="utf-8",
            newline="\n",
        )
        (output / file_roles["readme"]).write_text(
            (
                "# Moira Physical Heliacal Visibility Data Pack 1.1.0\n\n"
                "Supply this immutable directory through an explicit "
                "caller-supplied directory path. No component may download, "
                "search for, regenerate, or silently replace it.\n\n"
                "Version 1.1.0 preserves the admitted Phase 1 atmosphere "
                "tables and adds pack-owned planetary target profiles for "
                "Mercury, Venus, Mars, Jupiter, and Saturn. Source-domain "
                "limits fail closed.\n"
            ),
            encoding="utf-8",
            newline="\n",
        )

        names_without_checksums = sorted(
            set(file_roles.values()) - {file_roles["checksums"]}
        )
        checksums = "".join(
            f"{sha256_file(output / name)}  {name}\n"
            for name in names_without_checksums
        )
        (output / file_roles["checksums"]).write_text(
            checksums,
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
                    "target_profile_sha256": sha256_bytes(
                        target_bytes
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
            "composite_model_id": spec["pack"][
                "composite_model_id"
            ],
            "table_format_id": spec["pack"]["table_format_id"],
            "license": spec["pack"]["license"],
            "capabilities": compatibility["required_capabilities"],
            "interpolation": {
                "radiance": compatibility["radiance_interpolation"],
                "direct_extinction": compatibility[
                    "direct_extinction_interpolation"
                ],
            },
            "radiance_reference": compatibility[
                "radiance_reference"
            ],
            "target_profile_contract": compatibility[
                "target_profiles"
            ],
            "binary_representation": compatibility[
                "binary_representation"
            ],
            "root_manifest_receipt_owner": (
                "source_controlled_phase2_closure_checkpoint"
            ),
            "compatibility_contract": file_receipt(
                compatibility_path,
                relative_to=REPO_ROOT,
            ),
            "generation_fingerprint": generation_fingerprint,
            "deep_twilight_law": base_manifest[
                "deep_twilight_law"
            ],
            "effective_domain": base_manifest["effective_domain"],
            "file_roles": file_roles,
            "payload_file_count": len(payloads),
            "payload_files": payloads,
            "source_artifact": base_manifest["source_artifact"],
            "base_pack": provenance["base_pack"],
            "target_profile_artifact": {
                "spec_id": spec["spec_id"],
                "target_profile_sha256": sha256_bytes(target_bytes),
            },
        }
        manifest_bytes = canonical_json_bytes(manifest)
        (output / MANIFEST_NAME).write_bytes(manifest_bytes)
    except Exception:
        # The caller supplied a new output directory.  Leave any partial
        # directory visible for forensic inspection; never replace or delete
        # an existing artifact implicitly.
        raise

    return {
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "output": str(output),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "target_profile_sha256": sha256_bytes(target_bytes),
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
    result.add_argument(
        "--planetary-spectra-dir",
        type=Path,
        required=True,
    )
    result.add_argument("--cie-root", type=Path, required=True)
    result.add_argument("--solar-spectrum", type=Path, required=True)
    result.add_argument("--mallama-pdf", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        receipt = build_pack(
            spec_path=arguments.spec.resolve(),
            compatibility_path=arguments.compatibility.resolve(),
            base_pack=arguments.base_pack.resolve(),
            planetary_spectra_dir=(
                arguments.planetary_spectra_dir.resolve()
            ),
            cie_root=arguments.cie_root.resolve(),
            solar_spectrum=arguments.solar_spectrum.resolve(),
            mallama_pdf=arguments.mallama_pdf.resolve(),
            output=arguments.output.resolve(),
        )
    except VisibilityPhase2PackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
