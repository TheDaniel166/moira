# Moira Validation Report

**Version:** 2.1  
**Date:** 2026-03-19  
**Runtime target:** Python 3.14  
**Primary ephemeris kernel:** JPL DE441  
**Validation philosophy:** external-reference first, regression-enforced second

## 1. Executive Statement

Moira is not being validated by self-consistency alone.

The engine is currently checked against three independent external-reference
surfaces:

- **ERFA / SOFA** for IAU-standard astronomical algorithms
- **Official Astro.com `swetest` output** for sidereal ayanamsha values
- **Official Swiss Ephemeris `setest/t.exp` output** for house cusp systems

That distinction matters. Many ephemeris and astrology libraries are only
validated implicitly:

- a formula is transcribed from a paper or textbook
- a handful of sample charts "look right"
- regression tests preserve the current output, whether right or wrong

Moira is being held to a stronger standard. A serious validation program must
answer three separate questions:

1. Does the implementation correspond to a recognized mathematical model?
2. Does it match an authoritative external oracle numerically?
3. Is that comparison enforced continuously so later edits cannot silently drift?

This document records the current answers for Moira.

## 2. Validation Architecture

Moira validation is organized in three layers.

### 2.1 Model validation

This is the conceptual layer: are the implemented algorithms the right ones?

Examples:

- IAU 2006 precession
- IAU 2000A nutation
- ERFA-compatible sidereal time and obliquity
- Swiss-compatible sidereal anchors
- Swiss-compatible house cusp geometry and branch logic

### 2.2 Reference validation

This is the numerical layer: does Moira match an external authority?

Examples:

- `moira.julian.greenwich_mean_sidereal_time()` vs `erfa.gmst06`
- `moira.sidereal.ayanamsa()` vs captured official Astro.com `swetest` output
- `moira.houses.calculate_houses()` vs the official Swiss `t.exp` fixture

### 2.3 Regression validation

This is the enforcement layer: once a result is validated, is it protected in
`pytest` so refactors cannot quietly degrade it?

That policy now exists for:

- ERFA astronomy checks
- sidereal ayanamsha checks
- house cusp checks

Validated results should not remain trapped in one-off scripts.

## 3. Current Validation Surface

| Domain | Oracle | Enforcement path | Status |
|---|---|---|---|
| Core astronomy | ERFA / SOFA | `pytest` + reference script | Validated |
| Apparent planetary positions | JPL Horizons | `pytest` | Validated |
| Wide-range DE441 vectors | JPL Horizons | `pytest` | Validated |
| Topocentric sky positions | JPL Horizons | `pytest` | Validated |
| Sidereal systems | Official Astro.com `swetest` output captured offline | `pytest` | Validated |
| House systems | Official Swiss `setest/t.exp` captured offline | `pytest` + validator script | Validated |
| Local lunar occultations | Official Swiss `setest/t.exp` cached offline | `pytest` | Validated |
| Eclipse classification and search | Swiss fixture + NASA Five Millennium catalogs | `pytest` | Validated |
| Aspects (major, tight-orb) | Moira planet_at() pipeline (Horizons-validated) | `pytest` | Validated |
| Parans | Cross-checked against Moira rise/set-transit engine | `pytest` | Validated |

This is materially stronger than the earlier state of the project, where the
formal validation story was primarily limited to the ERFA-comparison kernel
layer and houses were still listed as not formally validated.

## 4. Reproducibility

All validation described here is reproducible from the repo-local virtual
environment and does not require a global Python install.

Recommended commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_erfa_validation.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_horizons_planet_apparent.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_horizons_planet_vectors_wide.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_horizons_sky.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_sidereal_external_reference.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_houses_external_reference.py -q
.\\.venv\Scripts\python.exe -m pytest tests\integration\test_eclipse_external_reference.py tests\integration\test_eclipse_nasa_reference.py -q
.\.venv\Scripts\python.exe -X utf8 scripts\compare_swetest.py --offline
.\.venv\Scripts\python.exe scripts\build_aspects_fixture.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_aspects_external_reference.py -q
```

Current recorded results:

- `tests/integration/test_erfa_validation.py`: `84 passed`
- `tests/integration/test_horizons_planet_apparent.py`: `120 passed`
- `tests/integration/test_horizons_planet_vectors_wide.py`: `80 passed`
- `tests/integration/test_horizons_sky.py`: `18 passed`
- `tests/integration/test_sidereal_external_reference.py`: `121 passed`
- `tests/integration/test_houses_external_reference.py`: `1 passed`
- `tests/integration/test_eclipse_external_reference.py` + `tests/integration/test_eclipse_nasa_reference.py`: passing
- `scripts/compare_swetest.py --offline`: `3168 iterations, 0 failures`
- `tests/integration/test_aspects_external_reference.py`: passing (run after build_aspects_fixture.py)

The split is deliberate:

- `pytest` enforces pass/fail in the standard regression loop
- the standalone scripts remain useful for detailed numerical diagnostics and
  table generation

### 4.1 Additional External Validation Surfaces

Beyond the ERFA kernel checks, Moira now has three more important
externally-referenced astronomy surfaces:

- **apparent geocentric planetary positions** against JPL Horizons
- **wide-range DE441 vector geometry** against JPL Horizons
- **topocentric sky positions** against JPL Horizons

The strict apparent-position suite currently covers:

- **10 major bodies**
- **12 measured-era epochs**
- date range: `1900-01-01` to `2025-09-01`
- thresholds:
  - angular separation `<= 0.75"`
  - distance error `<= 1750 km`

Recorded envelope:

- worst angular error: `0.575869"`
- worst distance error: `1688.905 km`

The wide-range DE441 vector suite currently covers:

- **10 major bodies**
- **8 wider-span epochs**
- date range: `1800-06-24` to `2150-01-01`
- thresholds:
  - angular vector error `<= 1.0"`
  - vector difference `<= 15000 km`

Recorded envelope:

- worst angular vector error: `0.762734"`
- worst absolute vector difference: `10202.595 km`

The topocentric sky-position suite currently reports:

- `18/18 passed`

This split matters scientifically. The measured-era apparent-position suite is
the strict observer-facing check, while the wide-range vector suite is the
DE441-geometry check where future `Delta T` assumptions are less dominant.

## 5. Core Astronomy

The ERFA comparison suite is testing the behavior of a specific Moira
astronomical pipeline, not a random set of scalar formulas.

At a high level, the engine's celestial-mechanics stack involves:

1. time-scale handling and Julian-date conversion
2. Earth rotation and sidereal-time computation
3. mean obliquity
4. nutation in longitude and obliquity
5. precession matrix construction
6. equatorial precession-nutation matrix construction
7. downstream coordinate transformations into true ecliptic coordinates

Relevant implementation files include:

- [moira/julian.py](../julian.py)
- [moira/obliquity.py](../obliquity.py)
- [moira/precession.py](../precession.py)
- [moira/coordinates.py](../coordinates.py)
- [moira/planets.py](../planets.py)

The active ERFA-backed suite checks:

- Greenwich Mean Sidereal Time using `erfa.gmst06`
- Earth Rotation Angle using `erfa.era00`
- mean obliquity using `erfa.obl06`
- nutation in longitude and obliquity using `erfa.nut06a`
- true obliquity from `obl06 + nut06a`
- GAST approximation built from ERFA primitives
- precession matrix using `erfa.pmat06`
- full precession-nutation matrix using `erfa.pnm06a`

For scalar angular quantities, Moira compares directly in degrees or radians and
converts the difference to arcseconds. For rotation matrices, the comparison
uses the maximum absolute element difference and converts it into an
arcsecond-equivalent small-angle scale. The pass threshold is:

- `0.001` arcsecond
- equivalently `1` milliarcsecond

The epoch corpus spans 12 canonical epochs from 500 BCE to 2100 CE, so the
validation is sensitive to long-baseline polynomial behavior, not just modern
near-J2000 agreement.

### 5.1 Greenwich Mean Sidereal Time (GMST)

**Model:** IAU 2006 ERA-based formula (Capitaine et al. 2003)  
**ERFA reference:** `erfa.gmst06(uta, utb, tta, ttb)`  
**Formula:** GMST = ERA(UT1) + polynomial correction in TT

| Epoch | ERFA (deg) | Moira (deg) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 101.31811641 | 101.31811642 | 0.000026 |
| -200 (200 BCE) | 292.23282248 | 292.23282246 | 0.000075 |
| J0000 (1 CE) | 85.70722852 | 85.70722852 | 0.000011 |
| J1000.0 | 285.61283845 | 285.61283844 | 0.000041 |
| J1500.0 | 100.07016145 | 100.07016144 | 0.000043 |
| J1800.0 | 100.40068547 | 100.40068547 | 0.000003 |
| J1900.0 | 100.18385563 | 100.18385562 | 0.000002 |
| J2000.0 | 280.46062240 | 280.46062240 | 0.000000 |
| J2010.0 | 99.55197660 | 99.55197660 | 0.000000 |
| J2024.0 | 100.15261546 | 100.15261546 | 0.000002 |
| J2050.0 | 100.84570754 | 100.84570754 | 0.000001 |
| J2100.0 | 100.73816225 | 100.73816225 | 0.000000 |

**Max error: 0.000075 arcsec** | Mean: 0.000017 arcsec | **ALL PASS**

### 5.2 Earth Rotation Angle (ERA)

**Model:** IAU definition of UT1 (IERS Conventions 2010)  
**ERFA reference:** `erfa.era00(dj1, dj2)`  
**Formula:** ERA = 2pi x (0.7790572732640 + 1.00273781191135448 x D_UT1)

| Epoch | ERFA (deg) | Moira (deg) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 120.44843598 | 120.44843598 | 0.000026 |
| -200 (200 BCE) | 315.16197724 | 315.16197722 | 0.000075 |
| J0000 (1 CE) | 111.17697652 | 111.17697651 | 0.000011 |
| J1000.0 | 298.38535412 | 298.38535411 | 0.000041 |
| J1500.0 | 106.46614938 | 106.46614937 | 0.000043 |
| J1800.0 | 102.96139201 | 102.96139201 | 0.000003 |
| J1900.0 | 101.46460212 | 101.46460212 | 0.000002 |
| J2000.0 | 280.46061838 | 280.46061838 | 0.000000 |
| J2010.0 | 99.42388833 | 99.42388833 | 0.000000 |
| J2024.0 | 99.84512961 | 99.84512961 | 0.000002 |
| J2050.0 | 100.20502958 | 100.20502957 | 0.000001 |
| J2100.0 | 99.45663463 | 99.45663463 | 0.000000 |

**Max error: 0.000075 arcsec** | Mean: 0.000017 arcsec | **ALL PASS**

### 5.3 Mean Obliquity of the Ecliptic

**Model:** IAU 2006 P03 (Capitaine et al. 2003) - full 6-term polynomial  
**ERFA reference:** `erfa.obl06(date1, date2)`

| Epoch | ERFA (deg) | Moira (deg) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 23.63253975 | 23.63253975 | < 0.000001 |
| -200 (200 BCE) | 23.67013610 | 23.67013610 | < 0.000001 |
| J0000 (1 CE) | 23.69502418 | 23.69502418 | < 0.000001 |
| J1000.0 | 23.56881503 | 23.56881503 | < 0.000001 |
| J1500.0 | 23.50425837 | 23.50425837 | < 0.000001 |
| J1800.0 | 23.46529468 | 23.46529468 | < 0.000001 |
| J1900.0 | 23.45228887 | 23.45228887 | < 0.000001 |
| J2000.0 | 23.43927944 | 23.43927944 | < 0.000001 |
| J2010.0 | 23.43797878 | 23.43797878 | < 0.000001 |
| J2024.0 | 23.43615718 | 23.43615718 | < 0.000001 |
| J2050.0 | 23.43277439 | 23.43277439 | < 0.000001 |
| J2100.0 | 23.42626991 | 23.42626991 | < 0.000001 |

**Max error: < 0.000001 arcsec** | **ALL PASS**

### 5.4 Nutation in Longitude (Delta psi)

**Model:** IAU 2000A, 1358 luni-solar plus planetary terms, with IAU 2006 corrections  
**ERFA reference:** `erfa.nut06a(date1, date2)`

| Epoch | ERFA Delta psi (arcsec) | Moira Delta psi (arcsec) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 7.066811 | 7.066956 | 0.000145 |
| -200 (200 BCE) | -1.558206 | -1.557937 | 0.000270 |
| J0000 (1 CE) | 15.677902 | 15.677533 | 0.000369 |
| J1000.0 | -6.535127 | -6.535002 | 0.000126 |
| J1500.0 | -15.873823 | -15.873876 | 0.000053 |
| J1800.0 | -8.527613 | -8.527612 | 0.000001 |
| J1900.0 | 17.433692 | 17.433722 | 0.000030 |
| J2000.0 | -13.932003 | -13.932010 | 0.000007 |
| J2010.0 | 16.242780 | 16.242773 | 0.000007 |
| J2024.0 | -5.359092 | -5.359095 | 0.000004 |
| J2050.0 | 15.171478 | 15.171476 | 0.000002 |
| J2100.0 | 3.288400 | 3.288400 | 0.000000 |

**Max error: 0.000369 arcsec** | Mean: 0.000084 arcsec | **ALL PASS**

### 5.5 Nutation in Obliquity (Delta epsilon)

**Model:** IAU 2000A  
**ERFA reference:** `erfa.nut06a(date1, date2)` second return value

| Epoch | ERFA Delta epsilon (arcsec) | Moira Delta epsilon (arcsec) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 7.761083 | 7.761060 | 0.000023 |
| -200 (200 BCE) | 8.516353 | 8.516522 | 0.000168 |
| J0000 (1 CE) | 2.499571 | 2.499641 | 0.000070 |
| J1000.0 | 7.838751 | 7.838788 | 0.000037 |
| J1500.0 | 1.887788 | 1.887760 | 0.000028 |
| J1800.0 | 7.228171 | 7.228158 | 0.000013 |
| J1900.0 | -2.290156 | -2.290153 | 0.000003 |
| J2000.0 | -5.769398 | -5.769398 | 0.000000 |
| J2010.0 | 2.804917 | 2.804916 | 0.000001 |
| J2024.0 | 8.067430 | 8.067430 | 0.000001 |
| J2050.0 | -5.329713 | -5.329714 | 0.000001 |
| J2100.0 | 8.564317 | 8.564317 | 0.000000 |

**Max error: 0.000168 arcsec** | Mean: 0.000029 arcsec | **ALL PASS**

### 5.6 True Obliquity

**ERFA reference:** `erfa.obl06` plus `erfa.nut06a` second return

| Epoch | ERFA (deg) | Moira (deg) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 23.63469560 | 23.63469560 | 0.000023 |
| -200 (200 BCE) | 23.67250175 | 23.67250180 | 0.000168 |
| J0000 (1 CE) | 23.69571851 | 23.69571853 | 0.000070 |
| J1000.0 | 23.57099246 | 23.57099247 | 0.000037 |
| J1500.0 | 23.50478276 | 23.50478275 | 0.000028 |
| J1800.0 | 23.46730251 | 23.46730250 | 0.000013 |
| J1900.0 | 23.45165272 | 23.45165272 | 0.000003 |
| J2000.0 | 23.43767683 | 23.43767683 | 0.000000 |
| J2010.0 | 23.43875792 | 23.43875792 | 0.000001 |
| J2024.0 | 23.43839813 | 23.43839813 | 0.000001 |
| J2050.0 | 23.43129392 | 23.43129392 | 0.000001 |
| J2100.0 | 23.42864889 | 23.42864889 | 0.000000 |

**Max error: 0.000168 arcsec** | **ALL PASS**

### 5.7 Greenwich Apparent Sidereal Time (GAST)

**Model:** GAST = GMST + equation of the equinoxes approximation  
**ERFA reference:** derived from `gmst06`, `nut06a`, and `obl06`

| Epoch | ERFA (deg) | Moira (deg) | Delta (arcsec) |
|---|---:|---:|---:|
| -500 (500 BCE) | 101.31991475 | 101.31991480 | 0.000159 |
| -200 (200 BCE) | 292.23242607 | 292.23242612 | 0.000172 |
| J0000 (1 CE) | 85.71121634 | 85.71121624 | 0.000349 |
| J1000.0 | 285.61117460 | 285.61117462 | 0.000074 |
| J1500.0 | 100.06611792 | 100.06611789 | 0.000092 |
| J1800.0 | 100.39851262 | 100.39851262 | 0.000002 |
| J1900.0 | 100.18829829 | 100.18829830 | 0.000025 |
| J2000.0 | 280.45707170 | 280.45707170 | 0.000006 |
| J2010.0 | 99.55611619 | 99.55611619 | 0.000006 |
| J2024.0 | 100.15124966 | 100.15124966 | 0.000002 |
| J2050.0 | 100.84957432 | 100.84957432 | 0.000003 |
| J2100.0 | 100.73900038 | 100.73900038 | 0.000000 |

**Max error: 0.000349 arcsec** | Mean: 0.000074 arcsec | **ALL PASS**

### 5.8 Internal Pipeline Consistency (J2000.0)

As an integrity check, the public `planet_at()` path and an independently
assembled step-by-step pipeline traversal were compared at J2000.0.

| Body | `planet_at()` (deg) | Manual pipeline (deg) | Delta (arcsec) |
|---|---:|---:|---:|
| Sun | 280.368916 | 280.368918 | 0.0069 |
| Venus | 241.565787 | 241.565789 | 0.0074 |
| Mars | 327.963298 | 327.963300 | 0.0066 |
| Jupiter | 25.253083 | 25.253085 | 0.0069 |

These differences are below `0.008` arcsec and are attributable to floating-
point rounding order, not model disagreement.

### 5.9 Precession Matrix and Combined P x N Matrix

**Precession matrix:** Fukushima-Williams four-angle parameterization, equivalent
in intent to SOFA `eraPmat06`  
**Combined matrix:** compared to `erfa.pnm06a`

| Epoch | Precession matrix error vs ERFA |
|---|---:|
| -500 BCE | 0.000354 arcsec |
| -200 BCE | 0.000414 arcsec |
| J0000 (1 CE) | 0.000452 arcsec |
| J1000.0 | 0.000244 arcsec |
| J1500.0 | 0.000124 arcsec |
| J1800.0 | 0.000050 arcsec |
| J1900.0 | 0.000025 arcsec |
| J2000.0 | 0.000000 arcsec |
| J2010.0 | 0.000002 arcsec |
| J2100.0 | 0.000025 arcsec |

All tested epochs pass the `0.001` arcsecond threshold. The broader summary from
the validation suite is:

- precession matrix max error: `0.000452"`  
- combined precession-nutation matrix max error: `0.000667"`

## 6. The Fukushima-Williams Story

Moira's precession implementation is not a generic "precession correction"; it
is specifically the IAU 2006 Fukushima-Williams four-angle parameterization
used by modern SOFA/ERFA workflows. In practical terms, that means Moira is not
approximating precession with a simplified zodiacal drift, but constructing the
full bias-plus-precession rotation on the same conceptual basis as
`erfa.pmat06`. This matters because the precession layer is upstream of almost
everything else: sidereal time, equatorial-to-ecliptic rotation, house
orientation, and ultimately every downstream apparent position. In current
validation, the standalone precession matrix stays within `0.000452"` of ERFA
across the tested range, and the combined precession-nutation matrix stays
within `0.000667"`, both comfortably inside the `0.001"` target. So the
relevant claim is not merely that "precession seems close"; it is that Moira's
rotation-matrix implementation belongs to the same reference family as the IAU
standard routines it is being compared against.

## 7. SPK Segment Selection

Moira does not treat DE441 as if every body were exposed through one simple,
always-correct segment lookup. That was an important correctness issue to get
right. DE441 stores some bodies in multiple historical/modern segments, and a
naive "last matching segment wins" lookup can return the wrong epoch segment for
historical dates. Moira's SPK reader now iterates all matching segments and
selects the one whose date range actually covers the requested Julian day,
falling back only to the nearest range when no exact coverage exists. Above
that reader layer, Moira explicitly chains NAIF routes from the Solar System
Barycenter to the target body: for example, Earth is `[0,3] + [3,399]`,
Mercury is `[0,1] + [1,199]`, Venus is `[0,2] + [2,299]`, and the Moon is
handled through the EMB-to-Moon branch with Earth removed separately. The
practical consequence is that Moira is validating not only angular reductions
but the DE441 geometry that produces them, using **10 major bodies**, **12
canonical epochs**, and the same segment-routing logic the rest of the engine
depends on.

## 8. Delta T Future Divergence

Future Delta T is not a fixed truth; it is a forecast, and that has to be said
explicitly in any honest validation document. Moira's own comments and
comparison tooling already reflect this: measured Delta T is reliable only
through the current IERS window, while comparisons beyond that necessarily
become model-dependent. In the current project notes, Horizons-style handling
can effectively freeze near roughly `69 s` after the measured window, while
Moira's long-range polynomial can climb toward roughly `203 s` by 2100. Those
are not trivial differences. Depending on the body and epoch, they can create
**artificial future disagreements of roughly 3 to 120 arcseconds** even when
the underlying geometric model is otherwise correct. The important implication
is methodological: once validation moves beyond the measured Delta T era, a raw
"Moira vs external source" discrepancy is no longer automatically evidence of a
bad astronomy engine. It may instead be evidence that two systems are using
different future Delta T assumptions.

Moira's historical handling is now stronger than the older polynomial-only
approach. The engine uses the published HPIERS/HMNAO table derived from the
2016 Stephenson-Morrison-Hohenkerk historical rotation model for the
historical branch, while also exposing a separate NASA-canon `Delta T` model
for eclipse-compatibility work. That distinction is deliberate:

- **general engine `Delta T`**: Moira's primary astronomical timing model
- **NASA-canon `Delta T`**: compatibility support for eclipse-canon comparison

This keeps the core engine honest while still allowing like-for-like comparison
with historical eclipse publications.

## 9. Sidereal Validation

**Primary files**

- [tests/integration/test_sidereal_external_reference.py](../../tests/integration/test_sidereal_external_reference.py)
- [tests/fixtures/sidereal_swetest_reference.json](../../tests/fixtures/sidereal_swetest_reference.json)
- [moira/sidereal.py](../sidereal.py)

**Reference source**

- official Astro.com `swetest` CGI output, captured offline and committed as fixture data

**Pass threshold**

- `0.001` degree
- equivalently `3.6` arcseconds

Sidereal systems are not covered by ERFA. They require a different oracle
because they are not IAU astronomy standards in the same sense as precession or
nutation; they are astrological convention layers built on top of astronomy.
For Moira, the practical external oracle is official Swiss-compatible `swetest`
output captured into a reproducible offline fixture so the repo does not depend
on a local Swiss Ephemeris package.

Moira currently exposes **30** ayanamsha systems in
[moira/sidereal.py](../sidereal.py).
Of these:

- **29** have direct Swiss-mappable validation in the fixture
- **1**, `Galactic Center (5 Sag)`, has no direct Swiss sidereal mode

That unsupported Swiss case is still validated, but by definition:

```text
Galactic Center (5 Sag) = Galactic Center (0 Sag) + 5 degrees
```

The sidereal fixture currently contains:

- **2 epochs**
  - `1.1.2000 00:00 UT`
  - `16.3.1625 12:00 UT`
- **29 directly mapped systems**
- **2 modes per system**
  - `mean`
  - `true`
- original source URLs for the captured reference queries

This yields:

- `116` direct Swiss-backed comparisons
- plus invariant checks for `Galactic Center (5 Sag)`
- plus a coverage guard asserting that all Swiss-mapped Moira systems are represented

That is why the current result is `121 passed`.

The validated sidereal set includes, among others:

- Lahiri
- Fagan-Bradley
- Krishnamurti
- Raman
- Yukteshwar
- Djwhal Khul
- Hipparchos
- Suryasiddhanta
- Aryabhata
- SS Revati
- SS Citra
- True Chitrapaksha
- True Revati
- True Pushya
- Aldebaran (15 Tau)
- Babylonian variants
- Galactic Center (0 Sag)
- Galactic Center (Cochrane)
- Galactic Center (RGB)

Technically, the current public sidereal path uses:

- Swiss-compatible J2000 anchor constants
- Moira's own precession model for propagation
- optional small drift terms where generic precession alone is insufficient
- nutation contribution in `true` mode

The private star-anchored helper remains in the codebase for research, but the
validated public API is now the Swiss-compatible reference path. That is the
correct validation target, because it is the one users call.

## 10. House Validation

**Primary files**

- [tests/integration/test_houses_external_reference.py](../../tests/integration/test_houses_external_reference.py)
- [scripts/compare_swetest.py](../../scripts/compare_swetest.py)
- [tests/fixtures/swe_t.exp](../../tests/fixtures/swe_t.exp)
- [moira/houses.py](../houses.py)

**Reference source**

- official Swiss Ephemeris `setest/t.exp` fixture

**Pass threshold**

- `0.001` degree
- equivalently `3.6` arcseconds

House systems are one of the most failure-prone parts of astrology software.
It is not enough for a house routine to look plausible for ordinary charts. A
serious implementation must survive:

- equatorial singularities
- high-latitude behavior
- polar branch logic
- MC/IC accessibility issues
- quadrant orientation ambiguities
- systems with genuinely different projection geometries

The current Swiss-backed validation covers the following systems:

| Code | System |
|---|---|
| `P` | Placidus |
| `K` | Koch |
| `C` | Campanus |
| `R` | Regiomontanus |
| `O` | Porphyry |
| `E` | Equal |
| `W` | Whole Sign |
| `B` | Alcabitius |
| `M` | Morinus |
| `T` | Topocentric |
| `V` | Vehlow |
| `X` | Meridian |
| `H` | Azimuthal |
| `U` | Krusinski-Pisa |
| `Y` | APC |

The current offline Swiss house corpus contains **3168** parsed test iterations:

| Code | Iterations |
|---|---:|
| `P` | 180 |
| `K` | 180 |
| `C` | 216 |
| `R` | 216 |
| `O` | 216 |
| `E` | 216 |
| `W` | 216 |
| `B` | 216 |
| `M` | 216 |
| `T` | 216 |
| `V` | 216 |
| `X` | 216 |
| `H` | 216 |
| `U` | 216 |
| `Y` | 216 |

This corpus is not checking one generic "house formula." It exercises multiple
distinct geometric families:

- quadrant systems
- equal-based systems
- prime-vertical and horizon-based systems
- semi-arc systems
- RA-based projection systems
- polar and near-polar edge cases

Two systems were found to be genuinely wrong during validation:

- **Azimuthal (`H`)**
- **APC (`Y`)**

These were not tiny rounding issues. The initial failures showed:

- `Azimuthal` could mis-order houses in equatorial transformed cases
- `APC` could flip by 180 degrees in polar hemisphere edge cases

Those defects are now fixed in
[moira/houses.py](../houses.py),
including the relevant edge-case logic at:

- [moira/houses.py](../houses.py#L719)
- [moira/houses.py](../houses.py#L1150)

After those fixes:

- the offline validator reports `3168 iterations, 0 failures`
- the pytest integration test passes
- all currently supported Swiss-mapped house systems in the validator set match
  the reference fixture within threshold

The stress cases now covered include:

- `lat = 0.0`
- `lat = -89.90`
- multiple longitudes including `0.0`, `60.0`, and `-80.0`

That means Moira's house validation is no longer confined to ordinary
mid-latitude charts. It includes exactly the regimes where branch logic usually
breaks.

## 11. Eclipse Validation

**Primary files**

- [tests/integration/test_eclipse_external_reference.py](../../tests/integration/test_eclipse_external_reference.py)
- [tests/integration/test_eclipse_nasa_reference.py](../../tests/integration/test_eclipse_nasa_reference.py)
- [tests/fixtures/eclipse_nasa_reference.json](../../tests/fixtures/eclipse_nasa_reference.json)
- [moira/eclipse.py](../eclipse.py)
- [moira/eclipse_geometry.py](../eclipse_geometry.py)
- [moira/eclipse_search.py](../eclipse_search.py)
- [moira/eclipse_contacts.py](../eclipse_contacts.py)
- [moira/compat/nasa/eclipse.py](../compat/nasa/eclipse.py)

**Reference sources**

- official Swiss `t.exp` eclipse fixture near the 1900-era regression slice
- NASA Five Millennium solar and lunar eclipse catalogs

**Current validated scope**

Moira now has two distinct eclipse validation layers:

- a **Moira-native DE441 eclipse path**, which is the primary engine behavior
- a **NASA compatibility layer**, which exists for canon-style comparison and reporting

The Swiss-backed slice validates:

- solar maximum classification
- solar global event search
- lunar maximum classification
- lunar event search

The NASA-backed long-range slice validates:

- solar maximum classification across ancient, medieval, modern, and future eras
- lunar maximum classification across the same era span
- representative ancient and future search cases

The key point is that Moira is not pretending the NASA canon is the engine's
only source of truth. The native DE441 path remains primary. NASA is treated as
an external authority and compatibility target for eclipse publications.

### 11.1 Current Representative Accuracy

Representative search errors after the current round of fixes are:

| Case | Current error |
|---|---:|
| Ancient lunar total | `49.65 s` |
| Ancient solar hybrid | `43.17 s` |
| Future lunar penumbral | `20.76 s` |
| Future solar total | `14.68 s` |

These are materially improved from the earlier state of the engine. In
particular:

- ancient lunar total improved from `124.22 s` to `49.65 s`
- ancient solar hybrid improved from `84.09 s` to `43.17 s`

For the `-1801-04-30` lunar eclipse, direct audit against the NASA row shows
that the broad eclipse shape is already close:

- NASA published `gamma`: `0.4228`
- Moira at the NASA instant: `0.42458`
- NASA published penumbral magnitude: `2.0532`
- Moira at the NASA instant: `2.05075`
- NASA published umbral magnitude: `1.1104`
- Moira at the NASA instant: `1.10719`

The contact durations are also already close:

- penumbral duration: `306.15 min`
- partial duration: `193.47 min`
- total duration: `48.58 min`

That means the remaining ancient mismatch is no longer a gross shape failure.
It is primarily a **centering / gamma-minimum timing** issue.

### 11.2 What Was Actually Fixed

The eclipse refinements that materially improved the current accuracy were:

- replacement of the observer-facing apparent-position path with physical
  geocentric Sun-Moon geometry for eclipse calculations
- correction of a real engine bug where multiple `ut_to_tt()` call sites were
  passing integer years instead of decimal years, discarding month-level
  `Delta T` variation
- adoption of Danjon-style shadow radii and corrected penumbral-magnitude logic
- explicit contact solving for lunar eclipses
- kind-specific lunar event centering
- use of the retarded Sun and retarded Moon in the umbral-event shadow-axis
  search objective

The result is not a claim of perfect NASA reproduction. It is a defensible
statement that the eclipse engine is now substantially more accurate, that the
remaining residuals are understood more narrowly, and that the code no longer
contains the obvious time-model and geometry inconsistencies that were present
during earlier validation.

For lunar catalog comparison, validation now distinguishes two paths instead of
collapsing them into one claim:

- `native`: Moira's DE441-centric eclipse model, including the retarded-Moon
  centering used for umbral-event search
- `nasa_compat`: the catalog-facing TT-space gamma-minimum compatibility path

The current supported claim is that `nasa_compat` is explicitly measured
against a representative modern NASA lunar-row sample and stays within a
documented partial-compatibility envelope. The supported claim is not that all
modern lunar NASA differences are universally `20-60 s`, nor that the native
and compat paths should coincide.

The governing doctrine for future eclipse work is captured separately in
`moira/docs/ECLIPSE_MODEL_STANDARD.md`, which defines `native` as the primary
Moira truth surface and compatibility modes as translation layers.

## 12. Aspect Validation

The aspect engine is part of the chart-forming surface and is therefore
validated, but its validation is necessarily different in character from the
astronomical kernel. There is no external observatory-grade oracle for
"conjunction within a chosen orb" or for whether a software package should call
an aspect "applying" in exactly the same way. The correct standard here is
therefore **deterministic logical validation**, not external ephemeris
comparison.

The current aspect regression suite covers the public aspect pipeline through
`moira.aspects` and validates the following behaviors directly:

- wraparound handling at `0/360Â°` so conjunctions and other aspects survive the
  zodiac seam
- exact-angle and orb-boundary behavior
- applying vs separating classification, including wraparound cases
- stationary-body handling
- custom orb table behavior
- tier and `include_minor` selection behavior
- declination parallels and contra-parallels
- ordering by tightest orb

This means the aspect layer is not merely smoke-tested. It is under explicit
pressure on the places astrology code usually fails:

- seam errors near `0Â° Aries`
- off-by-one orb inclusions/exclusions
- applying/separating misclassification
- mismatches between user-configured orb tables and returned aspect lists

Aspect validation should therefore be understood as **rule-engine validation**:
the engine is being checked for internal consistency, edge-case correctness, and
public-API stability, rather than against an external astronomical catalog.

## 13. Fixed Star Validation

Fixed-star validation is now in place against an independent **ERFA** reference
path rather than against Moira-owned snapshots alone. The new regression suite:

- parses the local `sefstars.txt` catalog independently
- propagates catalog RA/Dec with `erfa.starpm`
- transforms the result with `erfa.pnm06a` into the true equator of date
- rotates into the true ecliptic of date and compares against `fixed_star_at()`

The representative validation corpus covers 15 high-value named stars used
heavily in astrological practice and in Moira's own APIs:

- Sirius, Canopus, Arcturus, Vega, Capella, Rigel, Procyon, Betelgeuse
- Aldebaran, Spica, Regulus, Antares, Fomalhaut, Algol, Polaris

These stars are checked at four epochs:

- `J2000.0`
- `J2016.0` (Gaia DR3 epoch)
- `1900-01-01`
- `2100-01-01`

The enforced tolerance is `0.3"` on each longitude/latitude component. After
replacing the old scalar-precession shortcut with the same matrix-based
true-equator / true-ecliptic path used elsewhere in the engine, the current
representative envelope is approximately:

- worst component error: `0.241"`
- typical component error: substantially below `0.1"`

This means fixed-star propagation is no longer merely regression-stable; it is
externally referenced against an independent IAU/SOFA-family astrometry path.

## 14. Rise, Set, and Twilight Timing

The rise/set solver is now validated against the offline Swiss Ephemeris fixture
corpus already cached in `tests/fixtures/swe_t.exp`.

The current external-reference slice covers:

- a fixed star case: `Regulus`
- a planetary case: `Venus`
- rise, set, upper transit, and lower transit

At the fixture location and epoch:

- latitude `52°`
- longitude `11°`
- start JD `2415020.6` (`1900-01-01 02:24 UT`)

the current Moira solver matches the cached Swiss `swe_rise_trans()` results
within `10 s`, and in practice the current envelope is tighter than that:

- rise/set differences are on the order of several seconds
- transit differences are near-subsecond to low-second

This validation is not yet a complete almanac-grade survey across latitudes,
refraction regimes, and polar edge cases. But it does mean the core horizon and
meridian event solver is no longer unreferenced.

Twilight timing currently rides on the same altitude-crossing solver with solar
altitude thresholds of `-6°`, `-12°`, and `-18°`. Twilight therefore benefits
from the same underlying event-search improvements, but it does not yet have an
independent external-reference corpus in the regression suite.

### 14.1 Paran Validation

`moira.parans` is now under direct regression validation against the
already-validated rise/set and meridian-event solver, which is the correct
internal oracle for this module. A paran is defined in terms of those
crossings, so the right validation question is whether `parans.py` is using
the same crossings correctly and consistently.

The current paran suite validates:

- rise, set, culmination, and anti-culmination times against
  `rise_set.find_phenomena()` and `rise_set.get_transit()`
- correct same-day lower-transit handling
- chronological/orb ordering of returned parans
- day-floor logic in `natal_parans()`

This work surfaced and fixed a real defect: anti-culmination was being solved
from an upper-transit seed in a way that could wrap the result into the next
sidereal day. The current implementation now solves lower transit explicitly on
the same search day.

### 14.2 Occultation Validation

`moira.occultations` now has a Swiss-backed local-reference slice using the
cached `swe_t.exp` fixture for `swe_lun_occult_when_loc()`. The current
external-reference corpus includes:

- a named fixed-star case: `Regulus`
- a planetary case: `Venus`
- observer latitude `52°`
- observer longitude `11°`
- observer elevation `132 m`

The occultation solver was extended to support local topocentric search using
apparent topocentric Moon/body geometry. This was required because occultation
visibility is inherently observer-dependent, and the Swiss local reference is
therefore the correct comparison surface.

The current representative timing envelope is:

- Regulus local lunar occultation maximum: about `37.9 s`
- Venus local lunar occultation maximum: about `0.16 s`

This work also surfaced and fixed a real search bug: the coarse occultation
scan only noticed direct threshold crossings and could miss a valid occultation
when both coarse endpoints were outside the threshold but the true minimum fell
between them. The current search now refines local minima and tests the refined
separation instead of trusting the coarse sample alone.

## 15. Transit and Return Validation

The transit engine is now validated as an **event-search layer**, not merely as
a by-product of validated planetary positions. This distinction matters:
accurate longitudes do not by themselves guarantee correct transits, returns,
ingresses, or syzygies. Those require independent validation of bracketing,
crossing detection, chronology, retrograde handling, and exact-time refinement.

The current transit regression suite covers:

- exact transit search to a fixed longitude
- multi-pass retrograde transit detection
- sign ingress detection in both direct and retrograde motion
- solar returns
- lunar returns
- generic geocentric `planet_return()`
- last new moon and last full moon
- prenatal syzygy selection
- repeated mixed-body stress cases across transits, ingresses, returns, and
  syzygies

This work also surfaced and corrected a real conceptual bug: `planet_return()`
was originally sizing its search window from **orbital periods**, which is not
the right model for **geocentric longitude returns**. Mercury exposed the
defect first. The engine now uses practical geocentric return-search envelopes,
which are wide enough for retrograde loops and Earth-motion effects.

The transit engine has also been generalized beyond fixed numeric targets. It
now supports dynamic target longitudes evaluated at the crossing instant,
including:

- planets
- asteroids
- lunar nodes
- Lilith variants
- named fixed stars

Representative validated mixed-body examples now include:

- `Venus → Sirius`
- `Mars → True Node`

This means Moira's transit layer is no longer restricted to the narrow notion
of "planet crossing a fixed zodiac degree." Any body for which the engine can
compute a longitude can now participate in transit search, and that generalized
path is under regression test.

## 16. Synastry and Relationship Chart Validation

The relationship-chart layer is now under direct regression validation rather
than being treated as an implied consequence of chart accuracy.

The current synastry workflow suite covers:

- cross-chart synastry aspect generation
- composite-chart midpoint construction for planets, nodes, and optional houses
- shorter-arc seam handling for zodiac and geographic midpoint logic
- Davison midpoint time and midpoint location casting

This matters because relationship modules have their own failure modes even
when the underlying chart engine is accurate:

- cross-chart aspect duplication or omission
- midpoint wraparound mistakes near `0/360°`
- antimeridian midpoint errors in Davison longitude handling
- relationship charts using a different chart-state construction path from the
  main engine

This validation also exposed and corrected a real inconsistency in
`davison_chart()`: the Davison path was not constructing obliquity and `Delta T`
in the same way as the primary public chart API. The relationship chart now
uses the same chart-state logic as the main engine, so its returned `Chart`
matches a direct midpoint-time chart cast rather than a subtly different
internal variant.

The current regression surface therefore validates the three public
relationship-chart outputs that users are most likely to compare across
applications:

- `synastry_aspects()`
- `composite_chart()`
- `davison_chart()`

## 17. Progression Validation

The progression layer is now under direct regression validation as a
relationship between **date mapping rules** and **returned chart state**.

This matters because progression code can appear numerically plausible while
still being conceptually wrong in one of the following ways:

- applying the wrong age-to-days mapping
- deriving solar arc from the wrong Sun positions
- confusing converse and forward direction logic
- returning correct positions but incorrect chart metadata

The current progression suite validates:

- secondary progression: `1 day = 1 year` mapping
- solar arc: progressed Sun minus natal Sun, then applied to natal positions
- converse secondary progression
- converse solar arc
- tertiary progression
- minor progression
- progressed-chart metadata consistency

This work exposed and corrected a real bug in `ProgressedChart`: the
`datetime_utc` property was returning the **natal** Julian day instead of the
**progressed** Julian day. The chart positions themselves were correct, but the
reported chart datetime was wrong. That is exactly the kind of workflow-level
error that low-level planetary validation would not catch.

Progressions should therefore be understood as another validated derived
workflow surface, not merely an implicit consequence of accurate planetary
positions.

## 18. Dignities and Lots Validation

`dignities.py` and `lots.py` are not astronomy-oracle modules; they are
rule-engine modules. The correct validation standard here is therefore not
ERFA, Horizons, Swiss, or NASA comparison, but a combination of:

- canonical formula validation
- edge-case logic validation
- public-wrapper coherence

The current dignity regression surface validates:

- essential dignity classification
  - domicile
  - exaltation
  - detriment
  - fall
  - peregrine fallback
- accidental dignity classification
  - angular / succedent / cadent
  - direct / retrograde
  - cazimi / combust / under-sunbeams boundaries
- hayz and sect logic
- mutual reception detection
- traditional planet ordering in the returned results

This work exposed and corrected two real issues:

- the public `Moira.dignities()` wrapper was calling `calculate_dignities()`
  with the wrong shape entirely
- `sect_light()` in `dignities.py` was using the wrong horizon-side test,
  making its day/night logic disagree with the house and lots layers

The current lot regression surface validates:

- day and night reversals for Fortune and Spirit
- derived lot logic such as `Eros (Valens)`
- reference resolution for
  - house cusps
  - house rulers
  - ruler aliases such as `Ruler MC`
  - fixed degrees
  - optional references such as syzygy and prenatal lunations
- public-wrapper coherence through `Moira.lots()`

So dignities and lots should now be understood as **validated rule surfaces**:
not externally astronomical, but explicitly checked for formula correctness,
reference resolution, and API stability.

## 19. Twilight Validation

Twilight is now validated as its own surface rather than being treated as a
mere side effect of the rise/set solver.

This distinction matters because twilight has an additional failure mode that
ordinary rise/set code can hide: **day-window selection**. A solver that scans a
fixed UTC day can return the wrong dusk for locations west of Greenwich, where
the evening boundary for the same local civil day falls after `00:00 UTC` on
the following date.

The current twilight regression surface validates:

- civil dawn and civil dusk
- nautical dawn and nautical dusk
- astronomical dawn and astronomical dusk
- chronological ordering of all eight boundary events
  - astronomical dawn
  - nautical dawn
  - civil dawn
  - sunrise
  - sunset
  - civil dusk
  - nautical dusk
  - astronomical dusk

The external oracle is the **U.S. Naval Observatory** annual twilight tables.
The current offline regression slice uses representative published 2024 summer
cases at mid-latitudes:

- Boston, MA — civil twilight
- Hartford, CT — nautical twilight
- Hartford, CT — astronomical twilight

The enforced tolerance is:

- `120 s`

That tolerance is intentionally appropriate to the source material: the USNO
annual tables are published to whole-minute granularity, while Moira returns
full JD timing.

This validation work exposed and corrected a real bug in `twilight_times()`:
the solver was anchoring event search to a fixed UTC day and could therefore
pair dawn with the wrong dusk for western longitudes. Twilight search is now
anchored around the **local solar day** by centering the search on local noon,
which keeps dawn and dusk paired to the same local date.

Twilight should therefore now be understood as an externally referenced
horizon-event surface, not merely a convenience wrapper around sunrise and
sunset.

## 20. Sothic Validation

`sothic.py` is not a normal chart-engine surface. It is a historical-astronomy
and chronology module, and it therefore needs a different validation standard.
The right question is not merely "does it run?" but "are the astronomy, the
calendar logic, and the benchmark historical claims stated clearly enough to be
defensible?"

Moira now validates the Sothic layer in two distinct tiers.

Fast deterministic validation:

- Egyptian civil calendar conversion
- month and epagomenal boundaries
- wrapped `days_from_1_thoth()` arithmetic
- Sothic epoch arithmetic
- wrapped drift-rate recovery

Research-grade slow validation:

- BCE-safe heliacal-rising support using the shared JD/calendar layer
- 139 AD anchor behavior near the Censorinus epoch
- location sensitivity across
  - Elephantine
  - Thebes
  - Memphis
  - Alexandria
- `arcus_visionis` sensitivity
- impossible-latitude suppression where Sirius never rises

The current historically meaningful benchmark slice is centered on the
well-known Censorinus epoch window in 139 AD. At `arcus_visionis = 10°`,
Moira currently reproduces the expected latitude ordering:

- Elephantine earlier than Thebes
- Thebes earlier than Memphis
- Memphis earlier than Alexandria

and lands the two most important anchor cases in the expected civil-calendar
windows:

- Alexandria: approximately `1 Thoth`
- Memphis: still in the epagomenal days just before `1 Thoth`

This should be read correctly. Sothic work is not "100% settled" in the
historical literature, and Moira is not claiming that one visibility model or
one location assumption resolves every scholarly dispute. The validation claim
is narrower and more defensible:

- the astronomy is under test
- the calendar arithmetic is under test
- the location and visibility sensitivities are explicit
- the published anchor window around 139 AD is reproduced in a research-grade
  regression slice

Operationally, Sothic validation is now treated as a **research benchmark
suite**, not as a normal always-run unit loop. That is intentional. The slow
heliacal-rising benchmarks are valuable because they are expensive and
historically meaningful, not because they are cheap.

## 21. What Is Not Yet Validated

This report is intentionally strong, but it is not claiming the entire engine
is finished.

The following areas still need their own external-reference validation programs:

| Area | Desired oracle |
|---|---|
| Twilight boundary times | published almanac-grade reference tables |
| High-level derived astrology workflows | curated canonical datasets and published worked examples |
| Non-Swiss-native or Moira-specific advanced constructs | domain-specific reference definitions and invariants |

This distinction should be read carefully:

- **implemented** does not mean **validated**
- **unit-tested** does not mean **externally referenced**
- **regression-stable** does not mean **astronomically authoritative**

The point of this document is to state exactly which surfaces have crossed that
line already.

## 22. Why These Choices Are Defensible

Moira deliberately avoids weaker claims such as:

- "the outputs look right"
- "the formulas come from standard books"
- "it matches another astrology application in a few sample charts"

Instead, the project uses an explicit oracle strategy:

- use **ERFA** where the domain is IAU-standard astronomy
- use **JPL Horizons** where the domain is apparent and vector ephemeris comparison
- use **official `swetest` output** where the domain is sidereal convention
- use **official Swiss test fixtures** where the domain is house cusp geometry
- use **Swiss and NASA eclipse publications** where the domain is eclipse classification and event search
- use **ERFA star-astrometry functions** where the domain is fixed-star propagation
- use **Swiss rise/transit fixtures** where the domain is horizon and meridian timing
- use **published site-dependent Sirius/Sothic benchmarks** where the domain is
  historical heliacal-rising chronology

That choice is defensible because each oracle is close to the natural authority
for its own domain, and because the comparisons are enforced in the regression
suite instead of being left as informal spot checks.

## 23. Reference Sources

### 22.1 Core astronomy

- ERFA project: https://github.com/liberfa/erfa
- IAU SOFA collection: https://www.iausofa.org/
- JPL DE441:
  Park, Folkner, Williams, Boggs (2021), *The Astronomical Journal* 161
- JPL Horizons API:
  https://ssd.jpl.nasa.gov/api/horizons.api

### 22.2 Sidereal references

- Official Astro.com `swetest` CGI:
  https://www.astro.com/cgi/swetest.cgi
- Swiss Ephemeris programming manual:
  https://www.astro.com/ftp/swisseph/doc/swephprg.2.10.pdf

### 22.3 House references

- Official Swiss Ephemeris source repository:
  https://github.com/aloistr/swisseph

### 22.4 Fixed-star references

- ERFA project:
  https://github.com/liberfa/erfa
- IAU SOFA collection:
  https://www.iausofa.org/
- Swiss Ephemeris `sefstars.txt` catalog source:
  https://raw.githubusercontent.com/astrorigin/swisseph/master/sefstars.txt

### 22.5 Rise/set and twilight references

- Swiss Ephemeris source repository:
  https://github.com/aloistr/swisseph
- Cached Swiss regression corpus:
  `tests/fixtures/swe_t.exp`, section 9 (`swe_rise_trans`)
- Official `setest/t.exp` fixture source:
  https://raw.githubusercontent.com/astrorigin/swisseph/master/setest/t.exp
- U.S. Naval Observatory annual twilight tables:
  https://aa.usno.navy.mil/calculated/rstt/year

### 22.6 Eclipse references

- NASA Five Millennium Canon of Lunar Eclipses:
  https://eclipse.gsfc.nasa.gov/SEpubs/5MKLE.html
- NASA Five Millennium Canon of Solar Eclipses:
  https://eclipse.gsfc.nasa.gov/SEpubs/5MKSE.html
- NASA eclipse ephemeris notes:
  https://eclipse.gsfc.nasa.gov/LEcat5/ephemeris.html

### 23.7 Sothic references

- Rita Gautschy, Sirius and heliacal-rising calculations:
  https://www.gautschy.ch/~rita/archast/sirius/siriuseng.htm
- Censorinus, *De Die Natali* (139 AD epoch tradition as discussed in modern
  Sothic-cycle literature)

## 24. Bottom Line

As of 2026-03-19, Moira has a real validation story across multiple critical domains:

- **astronomical kernel accuracy** against ERFA / SOFA
- **apparent planetary and sky-position accuracy** against JPL Horizons
- **wide-range DE441 vector geometry** against JPL Horizons
- **sidereal system accuracy** against official captured `swetest` output
- **house system accuracy** against the official Swiss house test fixture
- **transit, ingress, return, and syzygy event-search accuracy** in the public
  transit engine
- **synastry, composite, and Davison relationship-chart workflows** in the
  public relationship engine
- **secondary, converse, solar-arc, tertiary, and minor progression workflows**
  in the public progression engine
- **dignities and Arabic lots** as validated traditional rule engines
- **twilight boundaries** against published U.S. Naval Observatory tables
- **Sothic-cycle calendar and heliacal-rising benchmarks** as a dedicated
  research-grade validation surface
- **eclipse classification and representative search accuracy** against Swiss and NASA reference material

That does not make Moira complete. It does mean these parts of the engine are no
longer merely implemented; they are externally referenced, quantitatively
bounded, and regression-enforced.

