#!/usr/bin/env python3
"""
Build NotebookLM-ready source bundles for the Moira repository.

The output is a set of plain-text files in ``scratch/notebooklm_sources`` that
cover the live codebase and major documentation while excluding tests and
compiled/binary artifacts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "scratch" / "notebooklm_sources"
WORD_LIMIT = 500_000
BYTE_LIMIT = 200 * 1024 * 1024
TEXT_EXTENSIONS = {
    ".py",
    ".cpp",
    ".hpp",
    ".h",
    ".md",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".csv",
    ".dat",
    ".kiro",
}
ALLOWED_NO_EXTENSION = {"LICENSE"}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".vs",
    "__pycache__",
    "build",
    "dist",
    "tests",
    "scratch",
    "kernels",
    "Release",
}


@dataclass(frozen=True)
class BundleSpec:
    slug: str
    title: str
    description: str
    includes: tuple[str, ...]


BUNDLES: tuple[BundleSpec, ...] = (
    BundleSpec(
        slug="01_repo_overview_and_native_backend",
        title="Repository Overview And Native Backend",
        description=(
            "Repository-level guidance, packaging entrypoints, runtime policy, and "
            "the current native C++ backend surface."
        ),
        includes=(
            "AGENTS.md",
            ".github/copilot-instructions.md",
            "README.md",
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "CMakeLists.txt",
            "app.py",
            "sitecustomize.py",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "LICENSE",
            "FRAME_CONVENTIONS_EXPLAINED.md",
            "MOIRA_COMPETITIVE_ANALYSIS.md",
            "MOON_ERROR_INVESTIGATION.md",
            "ORACLE_VALIDATION_COMPLETE.md",
            "CLEANUP_COMPLETE.md",
            "SHARD_16_REMOVAL.md",
            "src/native",
        ),
    ),
    BundleSpec(
        slug="02_facades_core_and_export_governance",
        title="Facades Core And Export Governance",
        description=(
            "Public package surface, facades, runtime resolution helpers, "
            "compatibility layers, bridges, and export-governance tooling."
        ),
        includes=(
            "moira/__init__.py",
            "moira/facade.py",
            "moira/_facade_astronomy.py",
            "moira/_facade_classical.py",
            "moira/_facade_core.py",
            "moira/_facade_kernel.py",
            "moira/_facade_predictive.py",
            "moira/_facade_relationships.py",
            "moira/_facade_spatial.py",
            "moira/_facade_special.py",
            "moira/_kernel_paths.py",
            "moira/_spk_body_kernel.py",
            "moira/dispatch.py",
            "moira/moira_native.py",
            "moira/constants.py",
            "moira/compat",
            "moira/bridges",
            "moira/_export_governance",
        ),
    ),
    BundleSpec(
        slug="03_astronomy_time_coordinates_and_sky",
        title="Astronomy Time Coordinates And Sky",
        description=(
            "Astronomical substrate modules for time systems, coordinate handling, "
            "polar motion, corrections, and sky-frame helpers."
        ),
        includes=(
            "moira/julian.py",
            "moira/delta_t_physical.py",
            "moira/precession.py",
            "moira/nutation_2000a.py",
            "moira/obliquity.py",
            "moira/polar_motion.py",
            "moira/corrections.py",
            "moira/coordinates.py",
            "moira/geodetic.py",
            "moira/geoutils.py",
            "moira/local_space.py",
            "moira/light_cone.py",
            "moira/sky",
        ),
    ),
    BundleSpec(
        slug="04_planets_small_bodies_and_motion",
        title="Planets Small Bodies And Motion",
        description=(
            "Planetary, orbital, small-body, and kernel-facing motion modules."
        ),
        includes=(
            "moira/planets.py",
            "moira/planetocentric.py",
            "moira/orbits.py",
            "moira/ssb.py",
            "moira/phase.py",
            "moira/phenomena.py",
            "moira/stations.py",
            "moira/nodes.py",
            "moira/planetary_nodes.py",
            "moira/asteroids.py",
            "moira/asteroid_families.py",
            "moira/comets.py",
            "moira/centaurs.py",
            "moira/main_belt.py",
            "moira/tno.py",
            "moira/download_kernels.py",
            "moira/spk_reader.py",
        ),
    ),
    BundleSpec(
        slug="05_events_visibility_stars_and_eclipses",
        title="Events Visibility Stars And Eclipses",
        description=(
            "Rise/set, heliacal, stellar, occultation, and eclipse computation "
            "surfaces."
        ),
        includes=(
            "moira/rise_set.py",
            "moira/heliacal.py",
            "moira/stars.py",
            "moira/star_types.py",
            "moira/variable_stars.py",
            "moira/royal_stars.py",
            "moira/fixed_star_groups.py",
            "moira/multiple_stars.py",
            "moira/lunar_limb.py",
            "moira/occultations.py",
            "moira/parans.py",
            "moira/eclipse.py",
            "moira/eclipse_canon.py",
            "moira/eclipse_contacts.py",
            "moira/eclipse_geometry.py",
            "moira/eclipse_search.py",
        ),
    ),
    BundleSpec(
        slug="06_houses_spatial_and_charting",
        title="Houses Spatial And Charting",
        description=(
            "House computation, galactic/spatial charting, and chart container "
            "modules."
        ),
        includes=(
            "moira/houses.py",
            "moira/galactic_houses.py",
            "moira/astrocartography.py",
            "moira/chart.py",
            "moira/chart_shape.py",
            "moira/gauquelin.py",
            "moira/galactic.py",
            "moira/_solar.py",
            "moira/sky/galactic.py",
        ),
    ),
    BundleSpec(
        slug="07_astrological_systems_general",
        title="Astrological Systems General",
        description=(
            "Major interpretive and technique modules outside primary directions, "
            "including predictive, classical, and Vedic surfaces."
        ),
        includes=(
            "moira/aspects.py",
            "moira/dignities.py",
            "moira/dignities_types.py",
            "moira/egyptian_bounds.py",
            "moira/classical.py",
            "moira/classical_asteroids.py",
            "moira/lord_of_the_orb.py",
            "moira/lord_of_the_turn.py",
            "moira/lots.py",
            "moira/triplicity.py",
            "moira/decanates.py",
            "moira/hermetic_decans.py",
            "moira/harmonics.py",
            "moira/synastry.py",
            "moira/transits.py",
            "moira/progressions.py",
            "moira/predictive.py",
            "moira/profections.py",
            "moira/timelords.py",
            "moira/void_of_course.py",
            "moira/planetary_hours.py",
            "moira/electional.py",
            "moira/panchanga.py",
            "moira/shadbala.py",
            "moira/varga.py",
            "moira/vedic.py",
            "moira/vedic_dignities.py",
            "moira/ashtakavarga.py",
            "moira/jaimini.py",
            "moira/manazil.py",
            "moira/midpoints.py",
            "moira/uranian.py",
            "moira/sothic.py",
            "moira/patterns.py",
            "moira/nine_parts.py",
            "moira/babylonian.py",
            "moira/behenian_stars.py",
            "moira/cycles.py",
            "moira/essentials.py",
            "moira/experimental_placidus.py",
            "moira/huber.py",
            "moira/longevity.py",
        ),
    ),
    BundleSpec(
        slug="08_primary_directions_and_harmograms",
        title="Primary Directions And Harmograms",
        description=(
            "Primary directions engine modules and the harmograms subsystem."
        ),
        includes=(
            "moira/primary_directions",
            "moira/harmograms",
        ),
    ),
    BundleSpec(
        slug="09_constellations_and_catalog_code",
        title="Constellations And Catalog Code",
        description=(
            "Constellation source modules and adjacent lightweight catalog code."
        ),
        includes=(
            "moira/constellations",
            "moira/fixed_star_groups.py",
            "moira/star_types.py",
        ),
    ),
    BundleSpec(
        slug="10_data_registries_and_catalog_assets",
        title="Data Registries And Catalog Assets",
        description=(
            "Registry-like and catalog-like data assets, including star and asteroid "
            "metadata surfaces."
        ),
        includes=(
            "moira/data/__init__.py",
            "moira/data/leap_seconds.py",
            "moira/data/asteroid_families.csv",
            "moira/data/modern-iau-star-names-clean.csv",
            "moira/data/star_lore.json",
            "moira/data/star_provenance.json",
            "moira/data/star_registry.csv",
        ),
    ),
    BundleSpec(
        slug="11_data_reference_series_and_ephemeris_inputs",
        title="Data Reference Series And Ephemeris Inputs",
        description=(
            "Time-series and reference-table data assets that support astronomical "
            "computation."
        ),
        includes=(
            "moira/data/aam_glaam_annual.txt",
            "moira/data/babylonian_chronology_pd_1971.dat",
            "moira/data/core_angular_momentum.txt",
            "moira/data/delta_t_hpiers_2016.txt",
            "moira/data/grace_lod_contribution.txt",
            "moira/data/iau2000a_ls.txt",
            "moira/data/iau2000a_pl.txt",
            "moira/data/iau2006_x.txt",
            "moira/data/iers_eop.txt",
            "moira/data/iers_polar_motion.txt",
            "moira/data/oam_ecco_annual.txt",
        ),
    ),
    BundleSpec(
        slug="12_scripts_tools_and_operations",
        title="Scripts Tools And Operations",
        description=(
            "Repository operational scripts for building, auditing, validation, "
            "benchmarking, diagnostics, and data acquisition."
        ),
        includes=("scripts",),
    ),
    BundleSpec(
        slug="13_docs_architecture_and_internal_guides",
        title="Docs Architecture And Internal Guides",
        description=(
            "Architecture plans, internal design notes, and Moira package docs."
        ),
        includes=(
            "docs",
            "moira/docs",
        ),
    ),
    BundleSpec(
        slug="14_wiki_foundations_doctrine_and_standards",
        title="Wiki Foundations Doctrine And Standards",
        description=(
            "Foundational wiki material, doctrine, service boundaries, and standards."
        ),
        includes=(
            "wiki/Home.md",
            "wiki/00_foundations",
            "wiki/01_doctrines",
            "wiki/02_services",
            "wiki/02_standards",
        ),
    ),
    BundleSpec(
        slug="15_wiki_validation_research_roadmaps_and_kiro",
        title="Wiki Validation Research Roadmaps And Kiro",
        description=(
            "Validation ledgers, research notes, roadmaps, and Kiro specs/steering."
        ),
        includes=(
            "wiki/03_release",
            "wiki/03_standards",
            "wiki/03_validation",
            "wiki/05_research",
            "wiki/06_roadmap",
            ".kiro",
        ),
    ),
)


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if path.name in ALLOWED_NO_EXTENSION:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def resolve_includes(entries: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for entry in entries:
        entry_path = REPO_ROOT / entry
        if any(char in entry for char in "*?[]"):
            matches = REPO_ROOT.glob(entry)
            files.extend(path for path in matches if path.is_file() and should_include(path))
            continue
        if entry_path.is_file() and should_include(entry_path):
            files.append(entry_path)
            continue
        if entry_path.is_dir():
            files.extend(
                path for path in entry_path.rglob("*") if path.is_file() and should_include(path)
            )
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in sorted(files):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        deduped.append(path)
    return deduped


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def render_bundle(spec: BundleSpec, files: list[Path], generated_at: str) -> tuple[str, dict[str, object]]:
    lines = [
        f"NOTEBOOKLM SOURCE: {spec.title}",
        "",
        f"Generated: {generated_at}",
        f"Repository root: {REPO_ROOT}",
        "Scope: live repository snapshot for NotebookLM ingestion",
        "Exclusions: tests/, scratch/, build artifacts, binaries, images, kernels, virtual environments",
        f"Description: {spec.description}",
        "",
        "Included roots:",
        *[f"- {entry}" for entry in spec.includes],
        "",
    ]

    total_bytes = 0
    total_words = 0
    file_records: list[dict[str, object]] = []

    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        body = read_text(path)
        byte_count = len(body.encode("utf-8"))
        word_count = count_words(body)
        total_bytes += byte_count
        total_words += word_count
        file_records.append(
            {
                "path": rel,
                "bytes": byte_count,
                "words": word_count,
            }
        )
        lines.extend(
            [
                f"--- BEGIN FILE: {rel} ---",
                body,
                f"--- END FILE: {rel} ---",
                "",
            ]
        )

    if total_words > WORD_LIMIT:
        raise ValueError(
            f"Bundle {spec.slug} exceeds NotebookLM word limit: {total_words} > {WORD_LIMIT}"
        )
    if total_bytes > BYTE_LIMIT:
        raise ValueError(
            f"Bundle {spec.slug} exceeds NotebookLM byte limit: {total_bytes} > {BYTE_LIMIT}"
        )

    return "\n".join(lines), {
        "slug": spec.slug,
        "title": spec.title,
        "description": spec.description,
        "output_file": f"{spec.slug}.txt",
        "files": len(files),
        "bytes": total_bytes,
        "words": total_words,
        "includes": list(spec.includes),
        "file_records": file_records,
    }


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "generated_at": generated_at,
        "repository_root": str(REPO_ROOT),
        "output_dir": str(OUTPUT_DIR),
        "bundle_count": len(BUNDLES),
        "word_limit_per_source": WORD_LIMIT,
        "byte_limit_per_source": BYTE_LIMIT,
        "exclusions": sorted(EXCLUDED_PARTS),
        "bundles": [],
    }

    for existing in OUTPUT_DIR.glob("*.txt"):
        existing.unlink()
    manifest_path = OUTPUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()

    for spec in BUNDLES:
        files = resolve_includes(spec.includes)
        text, stats = render_bundle(spec, files, generated_at)
        output_path = OUTPUT_DIR / f"{spec.slug}.txt"
        output_path.write_text(text, encoding="utf-8")
        manifest["bundles"].append(stats)
        print(
            f"{output_path.name}: files={stats['files']} words={stats['words']} bytes={stats['bytes']}"
        )

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest.json: bundles={len(BUNDLES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
