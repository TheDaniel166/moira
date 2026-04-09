# Moira Engine — Feature Roadmap & Mathematical Accuracy Register

**Engine version**: post-Phase α (sub-arcsecond accuracy certified)
**Last updated**: 2026-04-04 (harmograms H1-H5 completed; bridge layer expanded; selective root exports added)
**Purpose**: Canonical record of implementation status, missing features, and mathematical improvement opportunities.

---

## Part 0 — Implementation Status

### Features implemented since initial roadmap (2026-03-16)

The following items from the original roadmap have been fully implemented and
are exposed in the `moira` package namespace:

| # | Feature | Status | Location |
|---|---------|--------|----------|
| 1 | Vertex / Anti-Vertex | **Done** | `houses.py` — `calculate_houses()` now populates `HouseCusps.vertex` via `_asc_from_armc(armc+90, obliquity, -lat)` |
| 2 | Antiscia & Contra-Antiscia | **Done** | `antiscia.py` — `antiscia()`, `find_antiscia()`, `AntisciaAspect` |
| 3 | Parallel & Contra-Parallel aspects | **Done** | `aspects.py` — `find_declination_aspects()`, `DeclinationAspect` |
| 4 | Parans | **Done** | `parans.py` — `find_parans()`, `natal_parans()`, `Paran`, full paran-field analysis suite |
| 5 | Generic planet return | **Done** | `transits.py` — `planet_return()` |
| 7 | Annual Profections | **Done** | `profections.py` — `annual_profection()`, `monthly_profection()`, `profection_schedule()`, `ProfectionResult` |
| 8 | Firdaria | **Done** | `timelords.py` — `firdaria()`, `current_firdaria()`, `FirdarPeriod` |
| 9 | Vimshottari Dasha | **Done** | `dasha.py` — `vimshottari()`, `current_dasha()`, `dasha_balance()`, `DashaPeriod` |
| 10 | Nakshatra Positions | **Done** | `sidereal.py` — `nakshatra_of()`, `all_nakshatras_at()`, `NakshatraPosition` |
| 11 | Zodiacal Releasing | **Done** | `timelords.py` — `zodiacal_releasing()`, `current_releasing()`, `ReleasingPeriod` |
| 12 | Hyleg / Alcocoden | **Done** | `longevity.py` — `find_hyleg()`, `calculate_longevity()`, `HylegResult` |
| 14 | Astrocartography / ACG | **Done** | `astrocartography.py` — `acg_lines()`, `acg_from_chart()`, `ACGLine` |
| 15 | Local Space Chart | **Done** | `local_space.py` — `local_space_positions()` |
| 16 | 90° Dial / Midpoints | **Done** | `midpoints.py` — `calculate_midpoints()`, `midpoints_to_point()`, `Midpoint` |

### Additional capabilities present but not in original roadmap

| Feature | Location |
|---------|----------|
| Galactic coordinates | `galactic.py` — `galactic_position_of()`, `all_galactic_positions()` |
| Uranian / TNP bodies | `uranian.py` — `UranianBody`, `uranian_at()`, `all_uranian_at()` |
| Harmonic charts | `harmonics.py` — `calculate_harmonic()`, `aspect_harmonic_profile()`, `HARMONIC_PRESETS` |
| Gauquelin sectors | `gauquelin.py` — `gauquelin_sector()`, `all_gauquelin_sectors()`, `GauquelinPosition` |
| Occultations | `occultations.py` — `close_approaches()`, `lunar_occultation()`, `CloseApproach` |
| Planetary hours | `planetary_hours.py` — `planetary_hours()`, `PlanetaryHour`, `PlanetaryHoursDay` |
| Primary directions | `primary_directions.py` — `find_primary_arcs()`, `PrimaryArc` |
| Planetary stations | `stations.py` — `find_stations()`, `next_station()`, `StationEvent` |
| Arabic lunar mansions | `manazil.py` — `mansion_of()`, `all_mansions_at()`, `MansionInfo` |
| Sothic cycle | `sothic.py` — `sothic_rising()`, `sothic_epochs()`, `SothicEntry` |
| Jones chart shapes | `chart_shape.py` — `classify_chart_shape()`, `ChartShape`, `ChartShapeType` |
| Varga / divisional charts | `varga.py` — `navamsa()`, `calculate_varga()`, `dashamansa()`, etc. — **wired** (`moira.__all__`, 46 tests) |
| Heliacal rising / setting | `fixed_stars.py` — `heliacal_rising()`, `heliacal_setting()` — **wired** (`moira.__all__`, 46 tests) |
| Hayz / in sect | `dignities.py` — `is_in_hayz()`, `is_in_sect()`, `SectStateKind`, `SectTruth`, `SectClassification` — **wired** (`moira.__all__`, 46 tests) |
| Harmograms research engine | `harmograms/` — spectral vectors, zero-Aries parts, intensity spectra, projections, traces, comparison helpers |
| Harmogram bridge layer | `bridges/harmograms.py` — native chart/progression adapters, body filters, and datetime-range sample builders |

### Deferred doctrine candidate — Astrodynes / Cosmodynes

Status: primary-source unblocked; implementation still pending

Reason:
- Moira can support this structurally as a derived doctrine/scoring subsystem.
- `Astrodyne-Manual.pdf` is now in hand and materially unblocks the doctrine.
- The manual provides the governing scoring rules, worked examples, house-power
  table, zodiacal and parallel aspect procedures, and harmony/discord rollups.
- Remaining work is now transcription and validation of the referenced tables,
  not uncertainty about the family's primary lineage.

Constraint:
- Do not implement an approximate or blended "power score" and label it
  astrodynes/cosmodynes.
- Do not claim full source completeness or parity until the remaining tables
  referenced by the manual are transcribed and validated against worked
  examples.

Unblocker:
- Transcribe the remaining referenced tables from the manual/companion Church
  of Light material and validate an implementation against manual examples.
- See `wiki/05_research/astrodynes/astrodynes_source_assessment_2026-04-09.md`
  for the current source audit and the exact remaining gaps.

---

## Part I — Remaining Open Features

All three original public-surface wiring gaps are now closed.  No open Part I
items remain from the original roadmap.

### ~~6. Heliacal Rising & Setting — public surface gap~~  `Done`

`heliacal_rising()` and `heliacal_setting()` are exported from `moira.__all__`
and tested in `tests/unit/test_public_surface_gaps.py`.

---

### ~~13. Hayz / In Sect — public surface gap~~  `Done`

`is_in_hayz()`, `is_in_sect()`, `SectStateKind`, `SectTruth`, and
`SectClassification` are exported from `moira.__all__` and tested in
`tests/unit/test_public_surface_gaps.py`.

---

### ~~Varga / divisional charts — public surface gap~~  `Done`

`varga.py` (`navamsa`, `calculate_varga`, `dashamansa`, `dwadashamsa`,
`saptamsa`, `trimshamsa`, `VargaPoint`) wired into `moira.__init__` and
`moira.__all__`; tested in `tests/unit/test_public_surface_gaps.py`.

---

## Part II — Mathematical Accuracy Improvements

Status reflects work done since the original roadmap entry.

### A. Ayanamsa: Star-anchored TRUE_* systems  `HIGH IMPACT` — **Done**

`ayanamsa()` now routes `mode="true"` calls for systems in `_STAR_ANCHORED`
through `_star_anchored_ayanamsa()`, which calls `fixed_star_at()` for the
anchor star at the requested JD and computes `star_tropical_lon − target_sidereal`.

Affected systems: `TRUE_CHITRAPAKSHA` (Spica = 180°), `TRUE_REVATI`
(Revati = 0°), `ALDEBARAN_15_TAU` (Aldebaran = 45°), `TRUE_PUSHYA`
(Asellus Australis = 106.667°).

`Ayanamsa.LAHIRI` remains epoch-anchored (23°15′00.658″ at 21 Mar 1956),
matching `SE_SIDM_LAHIRI` in SwissEph — Lahiri is not star-anchored by doctrine.

Polynomial `mode="mean"` path unchanged for all systems (fallback and research).

Verified: Spica sidereal longitude = 180.000° ± 0.001° at J1956, J2000, J2020.
Tests: `tests/unit/test_sidereal.py` (50 tests).

---

### B. Vertex Calculation  `HIGH IMPACT` — **Done**

Vertex is now populated in `calculate_houses()`:
```python
vertex = _asc_from_armc((armc + 90.0) % 360.0, obliquity, -latitude)
```

---

### C. Topocentric Correction: WGS-84 Elevation Term  `MEDIUM IMPACT` — **Done**

`corrections.py::topocentric_correction()` already uses the full WGS-84
geodetic model:
- `f = 1.0 / 298.257223563` (WGS-84 flattening)
- `a = EARTH_RADIUS_KM = 6378.137` (equatorial radius, km)
- elevation converted to km and applied via the standard C/S auxiliary values

The roadmap entry was written before this work was completed.

---

### D. Apparent Sidereal Time: IAU 2006 GAST  `MEDIUM IMPACT` — **Done**

Already fully implemented in `julian.py`:
- `greenwich_mean_sidereal_time()` uses `θ_ERA` (IAU 2000) as foundation plus the
  Capitaine et al. (2003) 5th-order polynomial correction (SOFA `iauGmst06`).
- `_gast_complementary_terms()` implements all 9 periodic terms from IERS 2010
  Table 5.2c (dominant term 0.00264″ from Moon's node Ω; total ≤ 0.04″).
- `apparent_sidereal_time()` computes GAST = GMST + Δψ·cos(ε) + CT.

The roadmap entry was written before this work was completed.  Agreement with
SOFA `iauGmst06` is better than 0.0001″ for 1800–2200.

---

### E. Delta-T: IERS Bulletin data  `MEDIUM IMPACT` — **Done**

`_DELTA_T_ANNUAL` in `julian.py` updated with 12-month arithmetic means from
USNO `deltat.data` (source: maia.usno.navy.mil/ser7/deltat.data, fetched 2026-03-22).
2015–2025 are fully observed; 2026 uses the Jan 2026 IERS Bulletin A value (~69.1 s).

Key corrections vs. prior table (observed overestimates):
- 2022: 69.6 → 69.25 (−0.35 s)
- 2023: 69.5 → 69.20 (−0.30 s)
- 2024: 69.4 → 69.17 (−0.23 s)
- 2025: 69.3 → 69.13 (−0.17 s)

The 1955–2015 blend point was also fixed to reference `_DELTA_T_ANNUAL[0]`
directly rather than a hardcoded literal, so future table updates auto-propagate.

---

### F. Topocentric tag on Chart positions  `MEDIUM IMPACT` — **Done**

`PlanetData` (in `planets.py`) already carries `is_topocentric: bool = False`
and `planets.py::planet_at()` populates it from the `_topocentric` local at
line 589.  `FixedStar` and `GaiaStarPosition` carry the same field.  All
three result vessels surface the geocentric/topocentric distinction explicitly.

---

### G. Fixed Star Proper Motion: Epoch and Reference Frame  `LOW IMPACT` — **Done**

`fixed_stars.py` already handles per-entry epoch correctly:
- ICRS-tagged entries (Hipparcos-sourced) use `_J1991_25 = 2448349.0625` as
  the propagation start epoch.
- J2000 and B1950 entries use their stated epochs.
- `pm_ra` is stored and applied as `μ_α*` (i.e. `μ_α · cos δ`, the reduced
  form), which is documented in `_apply_proper_motion()`.

The roadmap entry was written before this work was completed.

---

### H. Obliquity: Unify P03 Throughout  `LOW IMPACT` — **Done**

`obliquity.py::mean_obliquity()` already delegates directly to
`precession.mean_obliquity_p03` (imported as `_mean_obliquity_p03`).  There
is no divergent polynomial — the module docstring explicitly states "IAU 2006
P03 / Capitaine, Wallace & Chapront 2003".  The roadmap entry was written
before this unification was confirmed.

---

### I. Equation of the Equinoxes: Full Periodic Terms  `LOW IMPACT` — **Done**

`julian.py::_gast_complementary_terms()` already implements all 9 periodic
terms from IERS 2010 Conventions Table 5.2c (reference: SOFA `iauEect00`).
The dominant term (Moon's node Ω) reaches ±0.00264″; the full series sums
to ≤0.04″.  `apparent_sidereal_time()` adds these CT terms on top of
`Δψ·cos(ε)`.  The roadmap entry predated this implementation.

---

### J. Aspects: Stationary Planet State  `LOW IMPACT` — **Done**

`aspects.py` already defines `MotionState` with values `APPLYING`,
`SEPARATING`, `STATIONARY`, `INDETERMINATE`, and `NONE`, plus the
`aspect_motion_state()` function that derives the correct state from any
aspect vessel.  The `bool | None` ambiguity is fully resolved.

---

## Part III — Summary Priority Table

### Status — all original items closed

All Part I features and Part II math improvements are now done.  The table
below shows the full historical record; nothing is currently open.

| # | Feature / Improvement | Type | Priority | Location |
|---|---|---|---|---|
| ~~6~~ | ~~Heliacal rising/setting~~ | Feature | **Done** | `fixed_stars.py` |
| ~~13~~ | ~~Hayz / in sect~~ | Feature | **Done** | `dignities.py` |
| ~~—~~ | ~~Varga divisional charts~~ | Feature | **Done** | `varga.py` |
| ~~A~~ | ~~Ayanamsa: star-anchored TRUE_* systems~~ | Math | **Done** | `sidereal.py` |
| ~~C~~ | ~~Topocentric: WGS-84 elevation~~ | Math | **Done** | `corrections.py` |
| ~~D~~ | ~~Apparent sidereal time: IAU 2006 GAST~~ | Math | **Done** | `julian.py` |
| ~~E~~ | ~~Delta-T: IERS Bulletin data~~ | Math | **Done** | `julian.py` |
| ~~F~~ | ~~Topocentric tag on Chart positions~~ | Math | **Done** | `planets.py` |
| ~~G~~ | ~~Fixed star proper motion: epoch + parallax~~ | Math | **Done** | `fixed_stars.py` |
| ~~H~~ | ~~Obliquity: unify P03 throughout~~ | Math | **Done** | `obliquity.py` |
| ~~I~~ | ~~Equation of the equinoxes: full periodic~~ | Math | **Done** | `julian.py` |
| ~~J~~ | ~~Stationary aspect state~~ | Math | **Done** | `aspects.py` |

---

## Part III-B — New Capabilities Added Post-Audit

| Feature | Location | Notes |
|---------|----------|-------|
| Multiple star systems | `multiple_stars.py` | 8 systems; Kepler orbital mechanics for VISUAL binaries |
| Harmograms subsystem | `harmograms/` | H1-H5 complete: spectral foundations, intensity doctrine, projection, trace layer, research tooling |
| Harmogram bridge layer | `bridges/harmograms.py` | Engine-facing adapters for chart/progression sources, body filtering, and range sampling |
| Harmograms root exports | `moira.__init__` | Selected stable harmograms types and computation surfaces exported from package root |

### Multiple Star Systems — `multiple_stars.py`  **Done** (2026-03-22)

Catalog of 8 astrologically significant multiple star systems with full orbital
mechanics for visually resolvable pairs.

**Types implemented:**
- `VISUAL` — Kepler + Thiele-Innes projection: Sirius (50.09-yr), α Centauri (79.91-yr)
- `WIDE` — reference separation/PA, period too long for reliable computation: Castor, Mizar, Acrux
- `SPECTROSCOPIC` — sub-milliarcsecond separation, unresolvable: Capella (104-day), Spica (4-day)
- `OPTICAL` — chance alignment confirmed by Gaia DR3 parallax: Albireo

**Catalog:**
| System | Type | Highlight |
|--------|------|-----------|
| Sirius | VISUAL | Sirius B (white dwarf) orbital mechanics; Dogon/esoteric significance |
| Castor | WIDE | Sextuple system — three nested binaries; Gemini's duality made literal |
| Alpha Centauri | VISUAL | Solar twin + K-dwarf; nearest stars; approaching 2035 periastron |
| Mizar | WIDE | First telescopic binary (1650); first spectroscopic binary (1889) |
| Albireo | OPTICAL | Gold + sapphire colour contrast; confirmed optical by Gaia DR3 |
| Capella | SPECTROSCOPIC | Two G-giant twins, invisible duality; 6th brightest star |
| Acrux | WIDE | Southern Cross alpha; two blue B-type giants; navigational anchor |
| Spica | SPECTROSCOPIC | Behenian star; tidally distorted ellipsoidal binary in 4-day orbit |

**Public API:** `MultiType`, `StarComponent`, `OrbitalElements`, `MultipleStarSystem`,
`angular_separation_at()`, `position_angle_at()`, `is_resolvable()`,
`dominant_component()`, `combined_magnitude()`, `components_at()`,
`multiple_star()`, `list_multiple_stars()`, `multiple_stars_by_type()`,
`sirius_ab_separation_at()`, `sirius_b_resolvable()`,
`castor_separation_at()`, `alpha_cen_separation_at()`

**Chart methods:** `Moira.multiple_star_separation()`, `Moira.multiple_star_components()`

**Future candidates:** Antares B (occulted by Moon, Mars-companion hidden star),
Theta Orionis (the Trapezium, heart of M42), Epsilon Aurigae (27-yr eclipse binary —
already in variable_stars.py, worth cross-linking), Gamma Velorum (WC8+O Wolf-Rayet).

---

### Harmograms Subsystem — `harmograms/`  **Done** (2026-04-04)

Mathematically explicit harmograms engine built in visible strata rather than
as one opaque score.

**Implemented strata:**
- H1 spectral foundations:
  - point-set harmonic vectors
  - zero-Aries parts construction
  - zero-Aries parts harmonic vectors
- H2 intensity doctrine:
  - named intensity families
  - conjunction inclusion policy
  - explicit normalization and harmonic-domain policy
- H3 projection layer:
  - explicit spectral projection vessels
  - truncated-realization classification carried visibly
- H4 trace layer:
  - named trace families
  - time-domain harmogram traces over supplied snapshots
- H5 research tooling:
  - contributor ranking
  - spectrum comparison
  - trace-series comparison

**Admitted intensity families:**
- cosine bell
- top hat
- triangular
- gaussian

**Admitted trace families:**
- dynamic zero-Aries parts
- transit-to-natal zero-Aries parts
- directed-to-natal zero-Aries parts
- progressed-to-natal zero-Aries parts

**Public engine shape:**
- selected stable types and computation surfaces exported from `moira.__init__`
- no facade-first harmogram workflow has been frozen
- service/workflow orchestration remains intentionally outside the engine core

**Bridge layer present:**
- `bridges/harmograms.py`
- native `Chart` / `ProgressedChart` / mapping adapters
- explicit body-selection filters
- progression-family sample builders
- datetime-range chart sampling builders

This keeps the engine boundary clean:
- mathematics in `moira.harmograms`
- expressive adaptation in `moira.bridges`
- no service-layer canonization in `moira.facade`

---

## Part IV — What Moira Already Has That Swiss Ephemeris Lacks

For reference, capabilities where Moira exceeds the standard Swiss Ephemeris distribution:

- **IAU 2000A full nutation** (1365-term series) — SwissEph uses a truncated version in its default mode
- **Hermetic decans** with all 36 Egyptian decan ruling stars and their computed positions
- **Centaur SPK kernels** (Pholus, Chariklo, Asbolus, Hylonome) — SwissEph has fewer
- **TNO kernel support** (Quaoar, Varuna, Ixion, Orcus) via SPK Type 13
- **499 Arabic parts / Lots** — SwissEph ships far fewer
- **Primary directions** (Placidus semi-arc, mundane) — SwissEph requires the `swe_dirhut()` C function
- **Hermetic / Ptolemaic 36-decan hour system** with sunrise/sunset computation
- **Tertiary progressions** alongside secondary and solar arc
- **Relativistic aberration and deflection** applied uniformly to all bodies
- **Constellations directory** (34 constellation star groups)
- **Planetary hours** with full day/night cycle and decan hours
- **Royal stars**, **Behenian stars**, **Pleiades / Hyades** as named groups
- **Multiple star systems** — Kepler orbital mechanics for visual binaries (Sirius B, α Centauri AB); VISUAL / WIDE / SPECTROSCOPIC / OPTICAL types; 8-system catalog
- **Eclipse Saros classification** with heptagonal vertex labelling
- **Jones whole-chart shape classification** (all 7 temperament types)
- **Gauquelin sector analysis**
- **Vimshottari Dasha** with nakshatra balance
- **Zodiacal releasing** (Vettius Valens method)
- **Firdaria** (Persian/Arabic time-lord system)
- **Astrocartography / ACG lines** (MC, IC, ASC, DSC per planet)
- **Local space chart** positions
- **Paran field analysis** with contour extraction and stability metrics
- **Galactic coordinate system** transformations
- **Uranian / transneptunian bodies** (Hamburg School TNPs)
- **Harmonic charts** with full aspect-harmonic profile
- **Harmograms subsystem** with explicit spectral vectors, zero-Aries parts, intensity spectra, projections, and named trace families
- **Varga / divisional charts** (navamsa, dashamansa, etc.)
- **Sothic cycle** reconstruction (Egyptian calendar anchor)
- **Arabic lunar mansions** (manazil, all 28)
- **Hyleg / Alcocoden** longevity calculation

