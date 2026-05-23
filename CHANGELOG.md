# Changelog

All notable changes to the Moira project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [2.0.0] - 2026-04-10

### Added
- **Phase α Accuracy Certification**: Transition to a sub-arcsecond accurate substrate grounded in IAU ERFA/SOFA standards.
- **JPL DE441 Support**: Integration of high-precision long-term planetary ephemerides.
- **IAU 2006 Standards**: Implementation of the full IAU 2000A/2006 precession and nutation models.
- **Relativistic Reduction Pipeline**: Geometric positions corrected for light-time, gravitational deflection, annual aberration, and frame bias.
- **Unified Facade**: Introduction of the `Moira` class and `Chart` objects as the stable public surface.

## [1.0.0] - 2026-04-01

### Added
- **Initial Stable Release**: Core planetary positions, house systems (17 systems), and zodiacal aspects.
- **Kernel Management**: Integrated CLI and GUI tools for JPL kernel acquisition and configuration.
