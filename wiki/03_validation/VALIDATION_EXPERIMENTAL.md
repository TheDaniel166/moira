## Moira Experimental Validation

Version: 2.0
Date: 2026-03-23
Runtime target: Python 3.14

This document covers Moira subsystems that are experimental, modernized, or
not normally validated against a single canonical astrology package. In this
layer, the validation standard is a mix of:

- inherited astronomical validation from lower layers
- doctrine and mathematical invariants
- curated external references where a real oracle exists
- explicit disclosure when a subsystem is still only partially validated

The goal is truthfulness, not false symmetry with the core astronomy and
astrology validation docs.

---

## 1. Status Table

| Domain | Validation basis | Status |
|---|---|---|
| Sovereign fixed-star positions | sovereign catalog/schema/search tests in `tests/unit/test_stars_sovereign_catalog.py`, identity tests in `tests/integration/test_stars_sovereign_identity.py`, Swiss audit in `tests/integration/test_stars_external_reference.py`, and SOFA/ERFA audit in `tests/integration/test_stars_erfa_reference.py` | Validated |
| Stellar quality mapping | boundary and vessel tests in the sovereign star suite; no external oracle exists for the interpretive mapping itself | Validated |
| Variable stars | catalog integrity, phase arithmetic, light-curve behavior, extremum helpers in `tests/unit/test_variable_stars.py`, plus external ephemeris spot checks for Algol (AAVSO VSX), Delta Cephei, and Eta Aquilae (GCVS) in `tests/integration/test_variable_stars_external_reference.py` | Validated |
| Extended physical bodies | Horizons / kernel-backed fixture suites for TNOs, centaurs, asteroids, and selected minor bodies | Validated |
| Galactic transforms and reference points | invariant tests in `tests/unit/test_experimental_validation.py` plus Astropy/ERFA oracle audit in `tests/integration/test_galactic_oracle_reference.py` | Validated |
| Uranian bodies / Transpluto | locked formulas and range checks in `tests/unit/test_experimental_validation.py` | Validated |
| Astrocartography | dedicated geometry and wrapper suite in `tests/unit/test_astrocartography.py` plus validated planetary positions | Validated |
| Local space | dedicated spherical-astronomy and wrapper suite in `tests/unit/test_local_space.py` plus validated topocentric positions | Validated |
| Longevity | doctrine tables and scoring logic in `tests/unit/test_experimental_validation.py` | Validated |
| Timelords | doctrine and structural invariants in `tests/unit/test_experimental_validation.py` and `tests/unit/test_timelords.py` | Validated |
| Gauquelin sectors | canonical diurnal-arc logic in `tests/unit/test_experimental_validation.py` | Validated |
| Arabic lunar mansions (Manazil) | equal-station arithmetic and boundary tests in `tests/unit/test_experimental_validation.py` | Validated |
| Varga divisions | explicit geometric-division doctrine tests in `tests/unit/test_varga.py` plus public-surface coverage | Validated |
| Synastry composites | midpoint and reference-place composite behavior in `tests/unit/test_synastry.py` | Validated |
| Sothic cycle | doctrine, policy, and profile structure in `tests/unit/test_sothic.py` | Validated |
| Multiple star systems | dedicated unit suite for catalog lookup, orbital behavior, resolvability, magnitudes, wrappers, and public surface, plus Sirius AB orbit spot checks against a published yearly ephemeris in `tests/integration/test_multiple_stars_external_reference.py` | Validated |

---

## 2. Validation Philosophy

Experimental subsystems do not all admit the same kind of truth claim.

- Some are physically anchored and can inherit real astronomy validation.
- Some are computationally novel and are best validated by doctrine, invariants,
  and explicit policy surfaces.
- Some are modern interpretive layers with no meaningful external oracle.
- A few are still under-validated and are marked that way directly.

Moira should not claim stronger validation than the subsystem actually has.

---

## 3. Sovereign Star and Stellar Extensions

### 3.1 Sovereign fixed-star positions

Current state:
- the named-star engine is now fully sovereign and is sourced from
  `moira/data/star_registry.csv`, `moira/data/star_lore.json`, and
  `moira/data/star_provenance.json`
- executable dependence on Gaia loaders and Swiss star files has been removed
- catalog loading, name/nomenclature routing, search ordering, magnitude
  filtering, and exact-case Bayer collision handling are explicitly covered in
  `tests/unit/test_stars_sovereign_catalog.py` and
  `tests/integration/test_stars_sovereign_identity.py`
- the full catalog now validates cleanly after resolving the 19 Bayer
  case-collision rows that had previously poisoned the stored J2000 ecliptic
  reference columns

External reference coverage:
- `tests/integration/test_stars_erfa_reference.py`
  uses an independent SOFA/ERFA path built from registry RA/Dec, proper motion,
  and parallax via `erfa.pmsafe`, `erfa.pnm06a`, and true-obliquity rotation
- `tests/integration/test_stars_external_reference.py`
  audits the same anchor stars against an offline Swiss `swetest` fixture
  generated by `scripts/build_stars_swetest_fixture.py`
- the internal sovereign catalog sweep checks all 1809 stars at J2000 against
  the stored registry reference columns

Status: Validated

Measured residuals:
- internal sovereign J2000 sweep against registry reference columns:
  worst residual `0.003971602°` (`14.30"`) in longitude for `ome Dra`; latitude
  residuals are materially smaller
- ERFA anchor oracle across `Sirius`, `Algol`, `Spica`, and `Aldebaran` from
  `J1000` to `J3000`: worst residual `0.000000133772°` (`0.00048"`) in
  longitude for `Sirius`; worst latitude residual `0.000000006849°`
  (`0.000025"`)
- ERFA full-catalog J2000 sweep: no large outliers remain after the case-routing
  repair; the remaining differences are at numerical-noise scale
- Swiss audit across the same anchor matrix: worst residual `0.007512431°`
  (`27.04"`) in longitude for `Sirius` at `J1900`; this residual is not
  materially driven by TT-vs-UT alignment

What this means:
- against ERFA, the sovereign star engine is now effectively at numerical-noise
  scale on the audited anchor set
- against Swiss, the remaining difference is on the order of a few hundredths
  of a degree at worst and reflects model/convention differences rather than a
  Delta T defect
- the catalog is now internally coherent end to end under both sovereign and
  ERFA sweeps

### 3.2 Stellar quality mapping

This layer is interpretive rather than astronomical, but it remains explicitly
bounded by unit coverage in the sovereign star suite.

Covered:
- NaN handling
- boundary transitions between declared BP-RP ranges
- resulting `StellarQuality` vessel semantics on sovereign `FixedStar` results

Status: Validated

What this does not mean:
- there is still no external oracle for the interpretive mapping itself
- the validation claim is that Moira's declared mapping is implemented
  correctly and consistently

### 3.3 Variable stars

Validated in `tests/unit/test_variable_stars.py` and
`tests/integration/test_variable_stars_external_reference.py`.

What is covered:
- catalog integrity
- phase arithmetic
- light-curve shape expectations by variable-star type
- next-minimum / next-maximum helpers
- type filters and convenience APIs
- external ephemeris spot checks for:
  - Algol against AAVSO VSX epoch-of-minimum and period
  - Delta Cephei against published GCVS epoch-of-maximum and period
  - Eta Aquilae against published GCVS epoch-of-maximum and period
- forward minima prediction against the external linear ephemeris for Algol

Status: Validated

External comparison numbers:
- Algol (`bet Per`, AAVSO VSX):
  - external epoch of minimum: `HJD 2455565.33243`
  - Moira epoch of minimum: `2455565.33243`
  - epoch delta: `0.0 d`
  - external period: `2.867323862 d`
  - Moira period: `2.867323862 d`
  - period delta: `0.0 d`
- Delta Cephei (`del Cep`, GCVS):
  - external epoch of maximum: `JD 2436075.445`
  - Moira epoch of maximum: `2436075.445`
  - epoch delta: `0.0 d`
  - external period: `5.366341 d`
  - Moira period: `5.366341 d`
  - period delta: `0.0 d`
- Eta Aquilae (`eta Aql`, GCVS):
  - external epoch of maximum: `JD 2436084.656`
  - Moira epoch of maximum: `2436084.656`
  - epoch delta: `0.0 d`
  - external period: `7.176641 d`
  - Moira period: `7.176641 d`
  - period delta: `0.0 d`

Observed agreement in the external suite:
- catalog ephemeris agreement for all three spot-check stars: exact match to
  the cited published values
- Algol forward linear-minimum prediction: exact to floating-point precision in
  the offline test corpus

### 3.4 Multiple star systems

Validated in `tests/unit/test_multiple_stars.py` and
`tests/integration/test_multiple_stars_external_reference.py`.

Covered:
- catalog lookup by name, designation, and alias
- type-specific behavior for visual, wide, spectroscopic, and optical systems
- time-varying visual-binary separation for Sirius and Alpha Centauri
- fixed reference behavior for wide and optical systems
- Dawes-limit resolvability logic, including the inclusive boundary
- dominant-component selection
- combined-magnitude flux-sum doctrine
- full snapshot structure from `components_at()`
- named convenience functions and `Moira` wrapper methods
- public surface exposure from both `moira.multiple_stars` and top-level `moira`

Status: Validated

Truth basis:
- this subsystem is currently validated by published catalog/orbital doctrine
  plus explicit invariant tests
- Sirius AB now also has a dedicated external spot check against a published
  yearly orbit ephemeris

Representative computed values from the current validated corpus:
- Sirius (`visual`):
  - `JD 2451545.0`: separation `4.6236436381"`; position angle `149.7428251338°`
  - `JD 2458849.5`: separation `11.2280299559"`; position angle `68.2561769339°`
  - combined magnitude: `-1.4601190421`
- Alpha Centauri (`visual`):
  - `JD 2451545.0`: separation `14.2571111404"`; position angle `222.1788135176°`
  - `JD 2464328.5`: separation `6.4073379950"`; position angle `34.4508871197°`
  - combined magnitude: `-0.2719470331`
- Castor (`wide`):
  - reference separation `3.9"`; reference position angle `52.0°`
  - combined magnitude: `1.5759885857`
- Albireo (`optical`):
  - reference separation `34.4"`; reference position angle `54.0°`
  - combined magnitude: `2.9329843961`
- Capella (`spectroscopic`):
  - separation `0.0"`; position angle `0.0°`
  - combined magnitude: `0.0798366601`
- Spica (`spectroscopic`):
  - separation `0.0"`; position angle `0.0°`
  - combined magnitude: `0.8868955636`

Observed agreement in the validation suite:
- Sirius AB published orbit ephemeris comparison:
  - `2000-01-01` (`JD 2451544.5`):
    published `rho=4.460"`, `theta=151.2°`;
    Moira `rho=4.6231468665"`, `theta=149.7581702725°`;
    residuals `+0.1631468665"`, `-1.4418297275°`
  - `2020-01-01` (`JD 2458849.5`):
    published `rho=11.193"`, `theta=68.1°`;
    Moira `rho=11.2280299559"`, `theta=68.2561769339°`;
    residuals `+0.0350299559"`, `+0.1561769339°`
  - `2030-01-01` (`JD 2462502.5`):
    published `rho=10.392"`, `theta=48.9°`;
    Moira `rho=10.3807681631"`, `theta=48.8288701968°`;
    residuals `-0.0112318369"`, `-0.0711298032°`
- Sirius and Alpha Centauri separations are strictly positive and vary across
  multi-decade epochs, confirming live Kepler/Thiele-Innes behavior
- Castor and Albireo separation / position-angle outputs are time-invariant at
  their declared reference values
- Capella and Spica remain fixed at `0.0"` separation and are never resolvable
- combined magnitudes match the declared flux-sum formula to within `1e-9`

---

## 4. Extended Physical Bodies

This area is much stronger than the previous version of this document implied.

Validated areas include curated fixture-based coverage for:
- TNOs
- centaurs
- classical asteroids
- broader main-belt bodies
- selected small-body kernels such as Pandora, Amor, Apollo, Icarus, Karma,
  and Persephone

These validations are grounded in the same Horizons / kernel-based astronomy
work used elsewhere in the repo.

Status: Validated

---

## 5. Galactic and Uranian Layers

### 5.1 Galactic transforms

Validated in `tests/unit/test_experimental_validation.py` and
`tests/integration/test_galactic_oracle_reference.py`.

Covered:
- rotation behavior
- round-trip consistency
- canonical galactic center and north galactic pole reference behavior
- direct ICRS <-> Galactic comparison against Astropy's external frame transform
- true-of-date ecliptic bridge audit using explicit ecliptic geometry, ERFA
  `pnm06a`, and Astropy's Galactic frame as the final oracle

Status: Validated

Measured residuals:
- direct `equatorial_to_galactic()` / `galactic_to_equatorial()` oracle checks
  stay below `0.1"` on the audited cases, with worst measured residual
  `0.0658"` at the North Galactic Pole oracle check
- `ecliptic_to_galactic()` / `galactic_to_ecliptic()` audited through the
  ERFA/Astropy bridge stay below `0.1"` across the audited span from
  `500 BCE` to `2100 CE`; the broader sweep produced worst measured residuals
  of `0.0318"` for ecliptic -> galactic and `0.0319"` for galactic -> ecliptic

Important scope note:
- this galactic audit is indexed by `jd_tt` directly, so the residual envelope
  does not presently indicate a Delta-T-model limitation
- the time-dependent term here is the of-date/J2000 frame bridge

### 5.2 Uranian bodies and Transpluto

Validated in `tests/unit/test_experimental_validation.py`.

Covered:
- locked formula output
- daily-motion expectations
- range and structural sanity

Status: Validated

This is still a model-defined subsystem. Differences from other Uranian
packages are treated as model differences unless Moira violates its own stated
formula basis.

---

## 6. Derived Geometric Techniques

### 6.1 Astrocartography

`astrocartography.py` derives line geometry from already validated planet
positions, and now has its own dedicated validation surface in
`tests/unit/test_astrocartography.py`.

Covered:
- MC / IC antipodal meridian logic
- ASC / DSC symmetry about the MC meridian
- zero-declination special case, where rising and setting reduce to fixed
  meridians
- high-declination circumpolar omission behavior
- line-vessel structure and repr shape
- `acg_from_chart()` wrapper plumbing for apparent sidereal time and RA/Dec
  collection

Status: Validated

Important scope note:
- this validates the geographic line engine
- Moira does not implement a separate rendered world-map projection layer here,
  so a map-image oracle is not the relevant validation target for this module

### 6.2 Local space

`local_space.py` derives azimuth/altitude outputs from validated topocentric
positions and now has its own dedicated validation surface in
`tests/unit/test_local_space.py`.

Covered:
- equatorial cardinal cases for zenith, nadir, east, and west horizon points
- north/south meridian cases at nonzero latitude
- azimuth sorting
- 8-point compass labeling
- `LocalSpacePosition` repr and above/below-horizon semantics
- `local_space_from_chart()` wrapper plumbing for sidereal time and RA/Dec
  collection

Status: Validated

---

## 7. Traditional-Experimental Boundary Techniques

### 7.1 Longevity

Validated in `tests/unit/test_experimental_validation.py`.

Covered:
- Ptolemaic years
- face rulers
- Egyptian bounds
- triplicity support
- dignity scoring
- hyleg selection priority
- longevity band selection

Status: Validated

### 7.2 Timelords

Validated across `tests/unit/test_experimental_validation.py` and
`tests/unit/test_timelords.py`.

Covered:
- Firdaria sequence structure
- sub-period grouping
- Zodiacal Releasing minor-year table behavior
- active-period and profile helpers

Status: Validated

### 7.3 Gauquelin sectors

Validated in `tests/unit/test_experimental_validation.py`.

Covered:
- sector range
- plus-zone classification
- field integrity and edge cases

Status: Validated

### 7.4 Arabic lunar mansions

Validated in `tests/unit/test_experimental_validation.py`.

Covered:
- mansion span arithmetic
- boundary advancement
- wraparound
- all 28 mansions reachable

Status: Validated

### 7.5 Varga divisions

`varga.py` explicitly implements the standard geometric-division model, not the
full set of sign-specific Parasari special rules used by some Jyotish
software. The correct validation target is therefore the geometric doctrine
the module actually declares.

Validated in:
- `tests/unit/test_varga.py`
- `tests/unit/test_public_surface_gaps.py`

Covered:
- D1 identity behavior
- segment-to-sign advancement at exact division boundaries
- degree reset at segment boundaries
- 360-degree periodicity
- scaled remainder mapping for degree-within-varga-sign
- convenience-function naming and divisor preservation
- output range invariants across multiple divisors
- public-surface wiring and return-type exposure

Status: Validated

Important scope note:
- this validates Moira's declared geometric varga engine
- it does not claim full equivalence to sign-offset doctrines used by JHora or
  other specialized Jyotish software

### 7.6 Synastry composites

The previous status here was too weak.

`tests/unit/test_synastry.py` already validates:
- midpoint composite construction
- shortest-arc midpoint behavior across seams
- reference-place composite houses
- relation/classification/condition-profile integrity
- policy handling and input guards

Status: Validated

---

## 8. Sothic Cycle

`tests/unit/test_sothic.py` provides a real validation surface for the Sothic
subsystem.

Covered:
- Egyptian civil-date logic
- annual Sothic rising result structure
- epoch filtering behavior
- drift-rate and prediction helpers
- policy validation
- condition-profile and network-profile structure

Status: Validated

This remains a doctrine/model subsystem rather than a mainstream external
software-comparison subsystem.

---

## 9. Remaining Work

The main experimental items that still need more validation are:

1. Sovereign fixed-star positions
   The core oracle path now exists via SOFA/ERFA and offline Swiss fixtures.
   Remaining work is narrower: broaden the published-anchor corpus beyond the
   current star set if a richer external published reference set is desired.

2. Optional external spot checks
   Astrocartography and local space are now geometry-validated internally, but
   software-to-software spot checks would still be useful as supplemental
   corroboration if a clean declared reference is available.

These are the real remaining gaps. Everything else listed as validated above
already has a concrete test surface in the repo.

---

## 10. Practical Reading

Interpret the status labels strictly:

- Validated
  There is a real enforcement surface in the repo appropriate to the subsystem.

- Partial
  There is meaningful coverage, but an important dedicated validation layer is
  still missing.

- Documented
  The subsystem is intentionally model-defined and transparent, but not
  externally validated in the usual sense.

- Needs validation
  The implementation exists, but the repo still lacks an adequate validation
  suite for it.

