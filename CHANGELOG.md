# Changelog

All notable changes to the Moira project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.3] - 2026-07-04

### Added
- **Draconic Chart Frame**: Added the node-anchored `moira.draconic` module (`draconic_longitude`, `draconic_positions`, `draconic_chart`, `draconic_chart_from_positions`, and the `DraconicAnchor` / `DraconicChart` / `DraconicPosition` vessels) exposed through the facade, plus a bounded `/v1/draconic/*` REST family — longitude rotation, caller-supplied positions, and engine-backed chart — for mean- and true-node draconic frames.
- **Chart-Shape Handle Identity**: Added an authoritative `handle_bodies` frozenset to the `ChartShape` vessel and its `ChartShapeResponse`, separating the display label (`handle_planet`, e.g. `"Neptune/Pluto"`) from the actual handle body set, enforced by real `__post_init__` invariants (non-empty, subset of `clusters[1]`, disjoint from `clusters[0]`).

### Fixed
- **Draconic Longitude Precision**: `draconic_longitude` now reduces both operands to `[0, 360)` before subtraction, so multi-revolution longitudes reach the rotation by one exact floating-point path.
- **Seesaw Seam Classification**: Fixed `chart_shape` Seesaw detection so a clean two-cluster chart with one cluster crossing the 0/360 longitude seam is no longer misclassified as Splash (VALIDATION CODEX RULE-20).

### Changed
- **Chart-Shape Doctrine Docs**: Synced the frozen chart-shape docstrings and VALIDATION CODEX to the implemented behavior — bowl-core Bucket metrics, the strict `> 60` handle threshold, tight conjunction-pair handles, unconditional Splash fallback, and seam-safe Seesaw.

### Validation
- Draconic and chart-shape engine unit tests, docstring governance, and the draconic and relationship REST route tests pass in the project virtual environment. The new public surface is additive; existing facade and REST semantics are unchanged.

## [3.4.2] - 2026-06-27

### Added
- **Website Planet Pipeline Visibility**: Added first-class per-stage planetary reduction breakdowns to the REST pipeline surface, including ordered physical stages, arcsecond longitude deltas, compatibility intermediate longitudes, and pre-topocentric geocentric longitude.

### Validation
- This is a REST transport and visibility patch release. It exposes already-owned apparent-reduction truth for HTTP clients and does not intentionally change final planetary position semantics.

## [3.4.0] - 2026-06-24

### Added
- **Profile Bundle REST Routes**: Added REST profile-bundle routes composing Western and Vedic chart profiles for frontend and workspace consumers.
- **Mixed-Subject Astrocartography Routes**: Added mixed-subject astrocartography REST routes.
- **Modern-Planet Dignities**: Extended dignity computation to include modern planets and additional policies.

### Changed
- **Solar Event Approximation**: Refined solar-event approximation with supporting tests.

### Validation
- Release cut with Git LFS checkout skipped during the PyPI release workflow.

## [3.3.4] - 2026-06-15

### Fixed
- **PyPI macOS Wheel Runners**: Replaced the retired `macos-13` Intel runner with the supported `macos-26-intel` label and moved the arm64 macOS wheel job to `macos-26`.

### Validation
- This is a packaging and release-workflow patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.3] - 2026-06-15

### Fixed
- **PyPI Wheel Matrix Scope**: Constrained Linux and Windows release wheels to 64-bit architectures and updated cibuildwheel to `4.1.0` so the release workflow can build the intended CPython 3.10-3.14 wheel set without entering unsupported 32-bit native-extension targets.

### Validation
- This is a packaging and release-workflow patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.2] - 2026-06-15

### Fixed
- **PyPI Wheel Matrix Build Constraints**: Updated the PyPI release workflow to use current cibuildwheel dependency constraints so isolated wheel builds can satisfy the `packaging>=24.2` build requirement on macOS and other runners.

### Validation
- This is a packaging and release-workflow patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.1] - 2026-06-15

### Fixed
- **PyPI Wheel Build Isolation**: Declared `packaging>=24.2` in the build-system requirements so isolated wheel builds satisfy modern setuptools license-expression normalization on GitHub Actions.

### Validation
- This is a packaging-only patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.0] - 2026-06-15

### Added
- **Expanded FastAPI Surface**: Admitted a large set of typed REST route families for Vedic, classical, spatial, catalog, specialist, electional, orbital, phenomena, sidereal utility, and harmonic products.
- **Server Transport Standards**: Added backend standards and transport design records for the newly admitted route families, including explicit deferrals for doctrine-heavy or specialist surfaces.
- **Facade Convenience Parity**: Added `Moira` convenience wrappers for admitted Vedic, Huber, Nine Parts, Lord of the Orb, and sidereal utility surfaces while preserving owner-module doctrine.
- **Astrocartography Rendering Support**: Added a rendering-adapter workflow and server support for map-oriented astrocartography consumers.

### Changed
- **REST Reference Truth**: Updated the REST reference and architecture ledgers to reflect the live server route registry and facade/init gap audit.
- **Route Admission Discipline**: Formalized post-Phase-9 and post-Phase-10 workflow boundaries for sidereal chart derivation, small-body/star astrocartography admission, and rendering support.

### Validation
- This release expands public transport, facade, standards, and documentation surfaces. The changes are additive and route-supporting; no intentional breaking public API changes were made.

## [3.2.4] - 2026-06-08

### Fixed
- **Release Lineage**: Reconciled the `v3.2.1` release branch into `main` so the release tag is contained in current history.
- **House Boundary Membership**: Preserved the documented half-open interval rule for `assign_house()`, so longitudes strictly below a closing cusp remain in the prior house while exact cusp hits enter the opening house.
- **Package Data Policy**: Made wheel builds obey the declared package-data policy so `.bsp` kernels are not silently bundled into PyPI artifacts.
- **Version Truth**: Aligned runtime metadata and release-facing doctrine tests with the `3.2.4` package version.

## [3.2.3] - 2026-05-30

### Added
- **Primary Directions REST Surface (P8-14)**: Completed the dedicated per-significator condition surface with a first-class typed `PrimaryDirectionsConditionResponse`, exposing `evaluate_primary_direction_condition` results through the `/profile` endpoint when `include_condition=true`.
- **Policy Ergonomics**: Extended conventional time-key derivation (`_get_chosen_key`) to all seven supported presets in the primary directions router, with explicit client key override always taking precedence.

### Changed
- Improved hardening and documentation around combined policy + submitted-arcs + enrichment paths in the primary directions transport layer (P8-14). Remaining 422 cases on the richest combinations are now explicitly documented rather than masked.

## [3.2.2] - 2026-05-23

### Added
- **High-Latitude House Solver**: Added experimental branch-aware Placidus solver (`experimental_placidus`) to search for unique ordered cusp cycles under polar conditions.
- **Supplemental Kernel Diagnostics**: Enhanced engine initialization to handle optional supplemental kernels and report missing ones gracefully.

## [3.2.1] - 2026-05-18

### Fixed
- **Adversarial House Singularities**: Corrected coordinate normalization at 360-degree bounds, zero-vector inputs, and resolved julian day/SPK evaluation edge cases (DEF-004/005/006 and TDF-001/002/003).

## [3.2.0] - 2026-05-15

### Added
- **Native Planetary Evaluator**: Introduced C++ `NativePlanetaryEvaluator` executing center chaining, rotation matrix operations, and light-time iterations natively.
- **SPK Kernel Compiler (GUI)**: Added Tkinter-based custom SPK Type 13 builder utility (`moira-daf-writer`).
- **Aspect Properties**: Added `is_partile` and `is_platic` properties to `AspectData`.
- **Zodiacal Helpers**: Added `house_of` function in `moira.houses`.
- **Sovereign Shards**: Bundled Git LFS-tracked Type 13 asteroid kernels (`sb441_type13`) for license-independent asteroid fleet calculations.

### Changed
- **Asteroid Pipeline**: Routed asteroid evaluations through the shared apparent reduction pipeline (`_apparent_geocentric_ecliptic`).

## [3.1.0] - 2026-05-10

### Added
- **Native House Engine**: Integrated C++ native house system engine bindings.

## [3.0.0] - 2026-05-08

### Changed
- **Immutable Result Semantics**: Frozen dataclass structures across all primary coordinate and chart outputs to enforce immutability.

## [2.2.0] - 2026-05-04

### Added
- **Sovereign Star Registry**: Full implementation of a license-independent, Gaia DR3-anchored registry of 1,809 named stars with sub-arcsecond epoch propagation.
- **Harmograms Engine**: Mathematically explicit research engine for planetary intensity spectra (Strata H1-H5), including zero-Aries parts and spectral projection.
- **Astrocartography (ACG)**: Planetary lines (MC, IC, ASC, DSC) and zenith-nadir calculations with full topocentric support.
- **Multiple Star Systems**: Keplerian orbital mechanics for visually resolvable binaries (Sirius AB, Alpha Centauri AB) across VISUAL, WIDE, SPECTROSCOPIC, and OPTICAL types.
- **Solar/Lunar Eclipse Cartography**: Besselian sample-based shadow band and contour extraction.
- **Void of Course Moon**: Integrated window detection and last-aspect analysis.
- **Jones Chart Shapes**: Automatic temperament type classification (all 7 Jones shapes).

### Changed
- **Facade Refactor**: Introduced `CoreFacadeMixin` and a unified constants library to modularize astronomical calculations.
- **Registry Performance**: Optimized star lookup speeds through binary-mapped substrate headers.

## [2.1.3] - 2026-04-25

### Added
- **Galactic Porphyry Houses**: Implemented the Galactic Porphyry house system with tests.
- **Triplicity Backend**: Added the triplicity computation backend with tests and documentation.
- **Electional Scoring**: Added scoring for electional windows with refined boundary handling.
- **Facade Mixins**: Introduced internal facade mixins (kernel, predictive, relationships, spatial, special topics).
- **Docstring Governance**: Added docstring-governance tests and behavior-preservation checks.

### Changed
- **Placidus Cusps**: Enhanced Placidus cusp calculation with a Newton-Raphson solver.
- **APC Houses**: Completed the APC primary-source re-derivation and oracle campaign.
- **Delta T Hybrid Model**: Refined physical Delta T accuracy and uncertainty; added tests.
- **SPK Reader**: Refactored SPK reader integration onto the KernelReader protocol.

### Fixed
- **README**: Corrected the DOI badge link format.

## [2.1.2] - 2026-04-16

### Changed
- **Code Cleanup**: General code and test cleanup across modules.

## [2.1.1] - 2026-04-16

### Added
- **Swiss Ephemeris Attribution**: Added source attribution for Swiss Ephemeris-derived code in `houses.py`.

## [2.1.0] - 2026-04-16

### Added
- **Traditional Dignities**: Complete Hellenistic and Medieval dignity suite including Sect, Hayz, Domicile, Exaltation, Triplicity, Terms, and Face.
- **Predictive Techniques**: High-fidelity implementations of Firdaria, Zodiacal Releasing (Valens method), and Annual/Monthly Profections.
- **Vedic Suite**: Comprehensive Jyotish tools including Vimshottari Dasha, Varga/divisional charts (D9, D10, D12, etc.), Shadbala, Ashtakavarga, and Panchanga.
- **Longevity Engine**: Hyleg and Alcocoden calculation with explicit planetary condition profiling.
- **Ayanamsa Systems**: Implementation of 40+ sidereal systems including star-anchored "True" ayanamsas.
- **Primary Directions**: Placidus semi-arc and mundane directions with speculum computation.
- **Heliacal Phenomena**: General visibility surface (V5) for rising/setting, acronychal events, and lunar crescent visibility.
- **Fixed Star Lore**: Integration of 499 Arabic Parts (Lots) and 36 Hermetic decans with ruling stars.

## [2.0.4] - 2026-04-15

### Added
- **Comet SPK Kernel Builder**: Added a script to build comet SPK kernels from JPL Horizons data.

### Changed
- **License Remediation**: Refined the license-remediation log and removed Swiss Ephemeris references from documentation.

## [2.0.3] - 2026-04-10

### Changed
- **Release Maintenance**: Version bump to 2.0.3 (release/CI maintenance; no distinct runtime changes).

## [2.0.2] - 2026-04-10

### Fixed
- **CI Hardening Gate**: Stabilized the hardening gate so it runs without kernels.

## [2.0.1] - 2026-04-10

### Fixed
- **CI Workflows**: Fixed acceptance and hardening workflow failures.

## [2.0.0] - 2026-04-10

### Added
- **Phase α Accuracy Certification**: Transition to a sub-arcsecond accurate substrate grounded in IAU ERFA/SOFA standards.
- **JPL DE441 Support**: Integration of high-precision long-term planetary ephemerides.
- **IAU 2006 Standards**: Implementation of the full IAU 2000A/2006 precession and nutation models.
- **Relativistic Reduction Pipeline**: Geometric positions corrected for light-time, gravitational deflection, annual aberration, and frame bias.
- **Unified Facade**: Introduction of the `Moira` class and `Chart` objects as the stable public surface.

## [1.2.1] - 2026-04-06

### Fixed
- **Facade Bugs**: Fixed latent facade bugs.

### Changed
- **Galactic Positions**: Refactored galactic position calculation to convert Julian date from UT.

## [1.2.0] - 2026-04-06

### Added
- **Classical Framework Modules**: Added the essentials, classical, and predictive astrology framework modules.
- **Quadrant / Huber / Manazil**: Added Rudhyar quadrant emphasis, the diurnal quadrant framework, the Huber engine, and the Manazil engine, with tests.
- **API Drift Guards**: Added public-API drift tests and facade duplicate-entry detection scripts.
- **Eclipse Convenience**: Added a module-level `next_solar_eclipse_at_location` wrapper.

### Changed
- **Kernel Safety**: Improved error handling in `daf_writer` and hardened `download_kernels`.

## [1.0.3] - 2026-04-05

### Added
- **Synodic Phase Detection**: Added phase detection for synodic phases.
- **Dispositorship**: Added modern and multi-doctrine dispositorship foundations and handling.
- **Kernel Management GUI**: Added a Tkinter kernel-management GUI and auto-discovery of planetary kernels.
- **Apparent Magnitude**: Added apparent-magnitude calculations with tests.
- **Repository Hygiene**: Added issue/PR templates and fixed cross-repo pytest collection bleed.

### Changed
- **Ephemeris Handling**: Refactored ephemeris handling and expanded kernel documentation.

_(Version 1.0.2 was skipped.)_

## [1.0.1] - 2026-04-01

### Fixed
- **Kernel Download Links**: Corrected the JPL DE441 kernel download links in the README and `download_kernels.py`.

### Changed
- **README**: Updated to reflect stable status and improved kernel handling.

## [1.0.0] - 2026-04-01

### Added
- **Initial Stable Release**: Core planetary positions, house systems (17 systems), and zodiacal aspects.
- **Kernel Management**: Integrated CLI and GUI tools for JPL kernel acquisition and configuration.

## [0.4.0] - 2026-03-27 — ACCIDENTAL TAG

- This tag was cut from a commit reporting "No code changes detected; skipping commit" and is out of sequence with the surrounding `0.1.x` development line. It introduced no changes and should be treated as an accidental tag; recorded here only for provenance.

## [0.1.7] - 2026-04-01

### Added
- **Kernel Path Resolution**: Added kernel path resolution and download functionality.

### Changed
- **Delta T**: Delta T refinements.

## [0.1.6] - 2026-03-30

- Release/version marker tagged immediately after 0.1.5 with no distinct code changes.

## [0.1.5] - 2026-03-30

### Added
- **Primary Directions Subsystem**: Added the primary-directions subsystem — roadmap, doctrine, core classes, presets, and Placidus rapt-parallel logic — with tests.
- **Physical Delta T**: Added planetary, stellar, and physical Delta T modules, including a physics-based hybrid computation with OAM/AAM proxy data and validation.

## [0.1.4] - 2026-03-27

### Added
- **Star Catalog**: Added a comprehensive star catalog with Gaia DR3 integration and constellation-specific APIs.
- **Egyptian Bounds**: Added the Egyptian bounds subsystem with tests.
- **Variable-Star Condition Profile**: Added `VarStarConditionProfile` and related void-of-course snapshots.

### Changed
- **Dependency Removal**: Removed executable dependence on Gaia loaders and Swiss star files; constellation modules now resolve by star name.
- **Corrections**: Enhanced atmospheric refraction and geocentric corrections.

## [0.1.3] - 2026-03-25

### Added
- **Multi-Body Deflection & Refraction**: Enhanced gravitational deflection with multi-body support and added atmospheric refraction.
- **Void-of-Course Tests**: Added comprehensive void-of-course tests covering all VALIDATION CODEX rules.

### Changed
- **Performance**: Added NumPy support for rotation-matrix composition; improved lazy loading and chart calculation.

## [0.1.2] - 2026-03-24

### Added
- **NumPy Nutation Acceleration**: Added NumPy acceleration for nutation calculations.

### Changed
- **Packaging**: Configured the PyPI publishing workflow and set the package name to `moira-astro`.

_(Version 0.1.1 was skipped.)_

## [0.1.0] - 2026-03-24

### Added
- **Initial Public Release**: First public release of the Moira astronomy-first astrology engine, establishing the public API and foundational modules (orbits, stars, planets, phenomena).
- **Gaia DR3 Integration**: Added Gaia DR3 star-catalog download and processing and the Light Box Doctrine for transparent computation.
- **Core Subsystems**: House systems, parans, synastry, void-of-course Moon, variable stars, and an eclipse catalog, with extensive unit and integration tests.
- **Packaging**: GitHub Actions workflow for PyPI publishing.

---

_Entries for versions 0.1.0 through 2.1.3 (and 3.4.0) were reconstructed from git commit history and may be less detailed than contemporaneously written entries. Version tags 0.4.0 and 0.1.6 are recorded as accidental/marker tags._
