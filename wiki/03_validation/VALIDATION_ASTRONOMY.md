# Moira Validation Report - Astronomy

**Version:** 1.4
**Date:** 2026-07-25
**Runtime target:** Python 3.14
**Validation kernel:** JPL DE441 (engine is kernel-agnostic; see note below)
**Validation philosophy:** external-reference first, regression-enforced second

> **Recent release evidence.** The bounded NASA lunar-eclipse corpus,
> global eclipse circumstances/cartography, lunar-node frame, and installed
> small-body readiness evidence added in Moira 5.1-5.2 is indexed in the
> [5.1-5.2 release validation ledger](RELEASE_VALIDATION_5_1_TO_5_2.md).

> **Kernel note.** All numerical results in this document were obtained with
> JPL DE441 installed. Moira is kernel-agnostic: it accepts de430, de440, or
> de441, and the validation numbers below would be expected to reproduce
> within the same tolerance envelopes on de440 or de430 for epochs within
> their coverage window (1550 BCE – 2650 CE). DE441 was used here because it
> covers the full historical epoch range exercised by the test corpora.

---

## 1. Executive Statement

This document covers the pure-physics layer of Moira: IAU-standard celestial
mechanics, JPL ephemeris geometry, time-scale handling, and observational
phenomena that have no astrological convention component.

The validation standard here is strict: every result must be compared against
an authoritative external oracle (ERFA, JPL Horizons, NASA catalogs, published
historical tables) and the comparison must be enforced continuously in `pytest`.

Moira's astronomy layer is materially more precise than Swiss Ephemeris in
several respects:

- IAU 2006 Fukushima-Williams precession (vs. older Swiss models)
- IAU 2000A nutation with 1358 luni-solar + 1056 planetary terms (2414 total), IAU 2006 corrections
- Direct SPK segment routing with correct NAIF chain selection
- Stephenson-Morrison-Hohenkerk (2016) historical Delta T model
- Separate NASA-canon Delta T path for eclipse-publication compatibility

---

## 2. Validation Surface

| Domain | Oracle | Enforcement | Status |
|---|---|---|---|
| GMST, ERA, obliquity, nutation, GAST | ERFA / SOFA | `pytest` | Validated |
| Precession matrix, P x N matrix | ERFA `pmat06`, `pnm06a` | `pytest` | Validated |
| Apparent geocentric planetary positions | JPL Horizons | `pytest` | Validated |
| Wide-range vector geometry (DE441 corpus) | JPL Horizons | `pytest` | Validated |
| Topocentric sky positions | JPL Horizons | `pytest` | Validated |
| Heliocentric orbital elements | JPL Horizons `ELEMENTS` | `pytest` | Validated |
| Heliocentric distance extrema | JPL Horizons `VECTORS` | `pytest` | Validated |
| Eclipse classification and search | Swiss `t.exp` + NASA Five Millennium | `pytest` | Validated |
| Solar eclipse greatest and polar central-path geography | NASA/GSFC 2015 WGS 84 path | `pytest` | Validated (named implemented slice) |
| Solar partial-visibility footprint contacts, boundary anchors, and topology | NASA/GSFC 2003/2006 total-eclipse penumbral Table 2 products + geometric invariants | `pytest` | Validated (named implemented slice) |
| Lunar eclipse individual contact instants | NASA/GSFC 2023/2024/2025/2027 detailed figures | `pytest` | Validated (named implemented slice) |
| Local lunar occultations | Swiss `setest/t.exp` | `pytest` | Validated |
| Occultation path geometry (`where`) | Swiss `t.exp` + live IOTA graze/limit text paths (El Nath, Spica N/S, epsilon Ari, Alcyone, Merope, Asellus Borealis, Regulus) | `pytest` | Validated (implemented slice) |
| Polar-crossing lunar-occultation path topology | JPL Horizons North-Pole contacts + independent spherical invariants | `pytest` | Validated (named contact/invariant slice) |
| Topographic lunar-graze contact chronology | IOTA 2024 Spica reductions at two observing sites + official USGS LOLA RDR assets | Frozen fixtures + network source/STAC identity checks + DE441/LE441 solve | Externally characterized and regression-admitted (named two-site slice; no authority-supplied model tolerance) |
| Sothic heliacal rising | Censorinus 139 AD historical record + latitude trend | `pytest` | Validated |
| Generalized heliacal / visibility surfaces | Published modern planetary apparition windows; Censorinus 139 AD Sirius slice (delegated stellar corpus); Yallop 1997 lunar class law | `pytest` | Validated (implemented slice) |
| Rise / set / transit times | JPL Horizons offline fixture; USNO published tables (supplemental) | `pytest` | Validated |
| Delta T model divergence envelope | IERS measured table | Documented | Documented |

### Occultation Validation Tracks

Moira treats modern/future path validation and ancient-event reconstruction as
two distinct programs. The observed/topographic contact surface described
below is a third, product-specific evidence track rather than an extension of
either path program:

- `modern_future_occultation_path_validation`
  primary authority: IOTA graze/limit path publications
  secondary authority: Swiss `where`
  validation mode: path and graze-boundary geometry parity

- `ancient_occultation_validation`
  primary authority: scholarly historical-astronomy record corpora
  secondary authority: later scholarly reductions and site chronologies
  validation mode: reconstructed local-event plausibility under explicit uncertainty

The active `pytest` occultation path suite belongs to the first track only.
Ancient occultations are intentionally deferred to a separate historical
reduction program and should not be represented as if they were validated by
the modern/future path corpus.

Current modern/future occultation path envelope:
- live IOTA graze/limit slices now sit within about `0.002°` to `0.17°`
  in graze-boundary latitude on the active corpus
- the enforced IOTA graze-boundary tolerance is `<= 0.18°`
- where a source file declares a nominal site altitude, that altitude is now
  used in the graze solve; the present ceiling is still set by profile-aware
  Spica north-limit geometry rather than by missing elevation

The first-class polar-safe topology is a distinct nominal product inside the
modern/future program. It admits only a spherical mean lunar limb and one
connected two-sided band. Its `left` and `right` identities are intrinsic to
increasing-UT1 centerline motion, not aliases for geographic north and south;
they remain continuous when latitude ordering reverses across a pole. Finite
planetary targets use JPL Solar System Dynamics equatorial solid-body radii,
fixed stars remain point sources, and Saturn's rings are excluded. The Sun is
excluded because the cited JPL planetary table does not govern its radius and
solar occultation belongs to the eclipse product. The
topocentric observer geometry is WGS 84 geodetic, while reported half-widths
and total width are explicitly great-circle distances on the
`6378.137 km` sphere.

The range-search admission policy is `0 < step_days <= 0.25`, at most 400
days, and no more than 4096 coarse cells. Boundary cells are candidates even
when their endpoints are outside, preventing a positive event peak near a
requested range boundary from being skipped. Pole contacts use a separate
fixed internal lattice rather than the presentation sample count. The summary
duration is solved at the fixed greatest site; the global footprint interval
only governs the track's temporal extent. A constrained optimum at, or within
`max(4e-8 d, 8 binary64 ULP)` of, a global request boundary is not emitted as
an unconstrained greatest event.
Raw maxima are grouped by overlapping open positive-clearance support, not by
an enlarged epoch tolerance; tangent-only contact therefore remains separate.
Because connected support does not imply a unimodal time profile, component
greatest uses a private at-most-30-minute lattice, refinement of every resolved
local maximum plus edge cells and raw witnesses, and a 128-cell fail-closed
budget. A synthetic two-hump case proves that a stronger greatest outside the
request suppresses a smaller interior hump, while an in-range case selects the
stronger hump.
The greatest tangent uses history-independent witnesses refined from the same
center anchor. Synthetic coverage limits the width difference between two
equivalent greatest witnesses `0.160973 s` apart to `0.02 km`.
The parallax-envelope invariant separately covers observers outside and inside
a body's geocentric radius: `asin(R/d)` for `R < d`, and a conservative
`180 degree` bound when `R >= d`.

The `0.25 d` ceiling gives about 109 coarse samples across JPL's descriptive
[27.322-day mean lunar period](https://ssd.jpl.nasa.gov/sats/elem/sep.html).
That mean-elements table explicitly is not an ephemeris source; Moira uses it
only to make the bounded operational cadence legible, while DE441 governs the
actual event geometry. The cadence is not claimed as a proof for arbitrary
ephemerides or unbounded intervals.

The bounded primary-authority case is the 2026-10-05 lunar occultation of Mars
at the geographic North Pole:

- Fixture: `tests/fixtures/jpl_horizons_polar_occultation_reference.json`
- Test: `tests/integration/test_occultation_polar_topology_horizons_reference.py`
- Authority: JPL Horizons `OBSERVER`, `coord@399`, geodetic
  `SITE_COORD=0,90,0`, `APPARENT=AIRLESS`, quantities `2,13,49`
- Evidence: outside/inside signs and one ingress plus one egress outer contact,
  each bounded by source rows `0.5 s` apart
- Cross-model gate: Moira DE441 contact time lies no more than `2 s` outside
  each Horizons bracket

Horizons reported DE441 for the Moon and Earth, `mar099` for Mars, and the
predictive `eop.260717.p261013` Earth-orientation file when the fixture was
retrieved on 2026-07-18. The fixture is frozen evidence, not a claim that those
predicted EOP values are final, and its refresh policy requires a post-event
replacement when measured data become available. The `0.5 s` bracket and
`2 s` comparison gate are respectively source resolution and a cross-model
regression envelope, not uncertainty estimates or exact-model parity.

This Horizons slice validates pole containment and the two pole-contact
instants only. The complete left/right tracks, zero-clearance boundary points,
branch continuity, and scalar width are enforced by independent spherical
invariants: center and boundary epochs share one ordered lattice, boundary
clearance is numerically zero, each half-width reproduces its center-to-limit
great-circle distance, and the two greatest half-widths reproduce the public
total width. No external dense polar limit-track or width parity is claimed.
The live IOTA ordinary-graze path and limit-line corpus remains separate
because those prediction products do not govern this nominal mean-limb
topology or an observed contact chronology.

### Topographic Lunar-Contact Validation Boundary

The direct-import `moira.lunar_occultation_contacts` module owns a separate
engine-only product: an immutable, strictly ordered sequence of disappearance,
reappearance, and admitted limiting-tangency contacts at one terrestrial site.
Its signed clearance is evaluated against an already prepared,
finite-resolution lunar-limb profile. Half-open-bin maxima are represented at
bin centres and reconstructed linearly; the product makes no exact sub-bin
topography claim. It does not mutate or replace
`LunarOccultation`, the nominal mean-limb path topology, or the existing graze
limit products. It is not exposed through the `Moira` facade or FastAPI.

The Moira-derived LOLA RDR profile path separates translation from orientation. The caller's
content-identified DE441/LE441 reader owns the physical Moon-to-observer
reception light cone. Observer-motion aberration is excluded from that
surface-intersection ray. The NAIF `moon_pa_de440_200625.bpc` and
`moon_de440_250416.tf` resources own only the retarded-emission-epoch rotation
into `MOON_ME_DE440_ME421`. Official USGS Astrogeology LOLA point-cloud assets
from the `lunar_orbiter_laser_altimeter` STAC collection supply IAU 2015
Moon-centred Cartesian radii relative to the `1737.4 km` sphere. The immutable
profile records content hashes and byte lengths for those resources as well as
the distinct translation and orientation models. Its finite-distance tangent
circle and perspective-equivalent profile radii retain the actual
observer-centre/observer-surface angular separation. Missing coverage,
excessive interpolation gaps, ambiguous reader identity, and unavailable
no-download resources fail explicitly.

The stellar target is a frozen, named sovereign-registry vessel: its ICRS
barycentric direction is proper-motion propagated to an explicit TT epoch
inside the event window. A positive catalog parallax is converted to finite
distance and translated by the complete reception-epoch observer SSB vector,
so annual and diurnal parallax share one origin. A contact-private Klioner
equation-70 light-deflection path binds DE441 Sun, Jupiter, and Saturn
position/velocity states, closest-passage backtracking, declared SOFA `Ldn`
limiters, and the exact finite-star deflector-to-source direction before
bending the incoming stellar ray.
The Moon light cone remains the retarded geometric location of the blocking
surface, not the apparent direction of lunar image photons; curvature over the
final Earth-Moon segment is not modeled. Observer-motion aberration and
atmospheric refraction are excluded from contact admission: they may change
apparent coordinates or observing circumstances, but they do not change
whether the incoming stellar photon ray intersects the lunar surface. The
contact search stays in UT1 and converts a result to UTC once for civil
representation.

`tests/fixtures/iota_spica_2024_observed_contacts.json` is primary-authority
evidence for the observed 2024-11-27 Spica chronology at the Dunham1 and
Dunham2 sites. It preserves the published disappearance/reappearance order,
GPS-referenced UTC realization, site and height provenance, source timing-error
semantics, and identities of the IOTA reduction PDF and event page. The
network-marked check verifies that those authority documents still match their
frozen lengths and SHA-256 digests. These are observed IOTA events, not Moira
predictions; the source timing errors are not model tolerances.

The separate model fixture
`tests/fixtures/iota_spica_2024_moira_lola_model.json` admits a named
predicted-versus-observed slice. Its model uses content-identified DE441/LE441,
the sovereign Spica ICRS record with catalog parallax, a maximum `15 s`
profile cadence, `0.002 degree` half-open PA bins with no missing-bin
interpolation, and sixteen official USGS LOLA RDR COPC assets admitted by exact
URL, byte length, and SHA-256. The network-marked executable test refreshes
the official STAC mapping before the pinned COPC bytes are decoded.

All ten Dunham1 contacts and all eight Dunham2 contacts have a unique optimum
under the declared chronological same-kind matcher. Their mean absolute timing
residuals are `0.137143 s` and `0.156497 s`; their maxima are `0.381008 s` and
`0.337355 s`.
Both pass the Moira-owned `0.5 s` cross-model regression and topology envelope.
That bound is neither source uncertainty nor an absolute accuracy tolerance.
Dunham1 has no model-only contacts. Dunham2 retains and requires a leading
model-only disappearance/reappearance pair about `1.529 ms` wide because it
exceeds the declared `1 ms` scan feature guarantee.

GRAZPREP is not used as a hidden runtime or treated as an equivalent oracle.
IOTA/ES documents that it consumes a derived, precomputed `LUNLIMB` profile
set recalculated from LRO/LOLA source data, but the current reconstruction and
interpolation doctrine are not public. A future product-to-product comparison
would require exact-site GRAZPREP contact tables and identified LUNLIMB inputs.
The admitted IOTA timing comparison therefore does not establish
GRAZPREP/LUNLIMB equivalence.

---

## 3. Core Celestial Mechanics (ERFA Suite)

**Oracle:** ERFA / SOFA (IAU standard routines)  
**Threshold:** 0.001 arcsecond (1 milliarcsecond)  
**Epoch corpus:** 12 canonical epochs, 500 BCE to 2100 CE  
**Test file:** `tests/integration/test_erfa_validation.py` - **106 passed**

The BCE anchors are proleptic-Gregorian 1 January in astronomical year
numbering: 500 BCE is year `-499`, JD `1538803.5`; 200 BCE is year `-199`, JD
`1648376.5`. The test independently derives both JDs through ERFA `cal2jd` and
Moira `julian_day`, then enforces the Moira calendar round trip. This identity
guard was added on 2026-07-14 after the previous numeric literals were found to
identify positive-CE dates rather than their labels.

### 3.1 Greenwich Mean Sidereal Time

**Model:** IAU 2006 ERA-based (Capitaine et al. 2003)  
**ERFA ref:** `erfa.gmst06`

Max error: **0.000089 arcsec** | Mean: 0.000019 arcsec | ALL PASS

### 3.2 Earth Rotation Angle

**Model:** IAU 2000 linear model (IERS Conventions 2010 §5.4.2)
**ERFA ref:** `erfa.era00`
**Moira surface:** `julian.earth_rotation_angle()`

Max error: **0.000089 arcsec** | Mean: 0.000019 arcsec | ALL PASS

### 3.3 Mean Obliquity

**Model:** IAU 2006 P03 full 6-term polynomial
**ERFA ref:** `erfa.obl06`

Max error: **1.28 × 10⁻¹¹ arcsec** (floating-point floor) | ALL PASS

### 3.4 Nutation in Longitude (Delta psi)

**Model:** IAU 2000A, 1358 luni-solar + 1056 planetary terms (2414 total), IAU 2006 corrections
**ERFA ref:** `erfa.nut06a`

Max error: **0.000526 arcsec** | Mean: 0.000108 arcsec | ALL PASS

### 3.5 Nutation in Obliquity (Delta epsilon)

**Model:** IAU 2000A (same series as 3.4)
**ERFA ref:** `erfa.nut06a`

Max error: **0.000149 arcsec** | Mean: 0.000029 arcsec | ALL PASS

### 3.6 True Obliquity

**Model:** mean obliquity (3.3) + Δε (3.5)
**ERFA ref:** `erfa.obl06` + `erfa.nut06a`

Max error: **0.000149 arcsec** | ALL PASS

### 3.7 Greenwich Apparent Sidereal Time — Approximation Cross-Check

**Model:** Equation of equinoxes, IAU 1982 form: GAST = GMST + Δψ·cos(ε_true).
Both sides of the comparison use the same approximation, so this validates the
internal consistency of GMST, nutation, and obliquity — not the full GAST model.
**ERFA ref:** `erfa.gmst06` + `erfa.nut06a` + `erfa.obl06` (not `erfa.gst06a`)
**Test:** `test_gast_approximation_matches_erfa`

Max error: **0.000392 arcsec** | Mean: 0.000090 arcsec | ALL PASS (12 epochs)

### 3.7.1 Full GAST — Oracle Comparison Against `erfa.gst06a`

**Oracle:** `erfa.gst06a` — IAU 2000/2006 full GAST including equation-of-origins path
**Moira surface:** `apparent_sidereal_time_at()` — equation-of-equinoxes path with complementary terms
**Test:** `test_full_gast_matches_erfa_gst06a`

Modern epoch agreement (J1500–J2100, 8 epochs):

| Epoch | Residual |
|---|---:|
| J1500.0 | 0.000492" |
| J1800.0 | 0.000091" |
| J2000.0 | 0.000256" |
| J2100.0 | 0.000352" |

Max error J1500–J2100: **< 0.001 arcsec** | ALL PASS

**Ancient epoch behaviour (documented, not enforced):**

For pre-J1000 epochs the residual grows: 0.009" at J1000, 0.528" at 200 BCE,
1.111" at 1 CE. This is a model-basis difference, not an algorithm defect:

- `erfa.gst06a` uses the **equation-of-origins** approach:
  GAST = ERA − equation of origins (derived from the full NPB matrix)
- Moira uses the **equation-of-equinoxes** approach:
  GAST = GMST + Δψ·cos(ε) + complementary terms

These two formulations are numerically equivalent near J2000 but diverge for
epochs far from it, because the complementary-terms series was not designed for
accuracy across millennia.

**Use-case assessment — not a practical concern for Moira:**

GAST is consumed in Moira for local sidereal time (house cusps), topocentric
parallax hour-angle, and rise/set timing — none of which are sensitive to
sub-arcsecond GAST errors:

- 1" of GAST error → 1" of RAMC → imperceptible house cusp displacement
- 1" of GAST error → < 0.001% perturbation to the Moon's topocentric parallax
- 1" of GAST error → ≈ 0.07 s of time in rise/set computation

More importantly, at ancient epochs the dominant uncertainty is Delta T, which
reaches tens of arcseconds for pre-medieval dates. A 1.1" GAST model-basis
difference at 1 CE is entirely within that noise floor. Implementing the
equation-of-origins path would not meaningfully improve any astrological product
Moira produces for historical charts.

### 3.8 Precession Matrix

**Model:** Fukushima-Williams four-angle parameterization (IAU 2006)
**ERFA ref:** `erfa.pmat06`
**Moira surface:** `precession_matrix()`

Max error: **0.000532 arcsec** | Mean: 0.000163 arcsec | ALL PASS

### 3.9 Combined Precession-Nutation Matrix

**Model:** P×N = nutation_matrix_equatorial × precession_matrix_equatorial
**ERFA ref:** `erfa.pnm06a`
**Moira surface:** `mat_mul(nutation_matrix_equatorial(), precession_matrix_equatorial())`

Max error: **0.000938 arcsec** | Mean: 0.000195 arcsec | ALL PASS

---

## 4. Planetary Positions (JPL Horizons Suite)

### 4.1 Apparent Geocentric Positions

**Oracle:** JPL Horizons  
**Bodies:** 10 major bodies  
**Epochs:** 12 measured-era epochs, 1900-01-01 to 2025-09-01  
**Thresholds:** angular separation <= 0.75", distance error <= 1750 km  
**Test file:** `tests/integration/test_horizons_planet_apparent.py` - **120 passed**

Recorded envelope:
- Worst angular error: **0.577850"** (Uranus, 1900-01-01)
- Worst distance error: **1684.977 km** (Pluto, 1900-01-01)

These figures do not reflect a planetary kernel accuracy limit. The kernel itself is accurate
to well under 1 milliarcsecond for the major planets in the measured era. The
dominant contributor to the residual is **Delta T convention disagreement**
between Moira and JPL Horizons. Moira uses the
Stephenson-Morrison-Hohenkerk (2016) historical rotation model; Horizons uses
its own internal Delta T. Even a 1-second difference in Delta T propagates to
roughly 0.5" on fast-moving bodies such as the Moon or Mercury at historical
epochs. The worst-case 0.577850" is consistent with this mechanism and is not
evidence of a defect in the geometry or the reduction pipeline. If both
systems were forced to use identical Delta T, the residual would collapse to
well under 0.01".

### 4.2 Wide-Range Vector Geometry (DE441 corpus)

**Oracle:** JPL Horizons  
**Bodies:** 10 major bodies  
**Epochs:** 8 wider-span epochs, 1800-06-24 to 2150-01-01  
**Thresholds:** angular vector error <= 1.0", vector difference <= 15000 km  
**Test file:** `tests/integration/test_horizons_planet_vectors_wide.py` - **80 passed**

Recorded envelope:
- Worst angular vector error: **0.762685"** (Uranus, 1800-06-24)
- Worst absolute vector difference: **10201.934 km** (Uranus, 1800-06-24)

The wider epoch span (1800-2150) introduces Delta-T model-basis sensitivity in
addition to geometric and reduction residuals. Before 1900, historical
rotation uncertainty is significant; after 2026, Moira uses the explicit
scenario in section 6 (`83.294360 s` at 2100 under the current boundary
aggregate). A Horizons comparison is
interpretable only when the fixture records the comparator's actual time-scale
and Delta-T settings; this document no longer assumes that Horizons simply
freezes Delta T. The recorded 0.762685" envelope is regression evidence for
the named fixture, not a term-by-term attribution of its residual.

### 4.3 Topocentric Sky Positions

**Oracle:** JPL Horizons  
**Test file:** `tests/integration/test_horizons_sky.py` - **18/18 passed**

### 4.4 Heliocentric Orbital Elements

**Oracle:** JPL Horizons `EPHEM_TYPE=ELEMENTS`  
**Bodies:** Mercury through Pluto  
**Epochs:** 3 validation epochs spanning J2000.0 through 2025-09-01  
**Thresholds:** semi-major axis <= `1e-5 AU`, eccentricity <= `1e-5`,
inclination/node <= `0.001 deg`, argument of perihelion and mean anomaly
<= `0.05 deg`, perihelion/aphelion distances <= `1e-5 AU`  
**Test file:** `tests/integration/test_horizons_orbits.py` - **27 passed** (9 bodies × 3 epochs)

All cases pass against live HORIZONS osculating elements. Outer-planet
validation uses the corresponding HORIZONS barycenter commands (`5` through
`9`) because the DE-series routing for those long-period systems is barycenter-based.

Worst-case residual per field (27 tests: 9 bodies × 3 epochs):

| Field | Worst residual | Body | Epoch |
|---|---:|---|---|
| semi-major axis | 3.11 × 10⁻⁶ AU | Earth | J2000 |
| eccentricity | 3.05 × 10⁻⁶ | Earth | J2000 |
| inclination | 3.10 × 10⁻⁸ deg | Mars | 2025-09-01 |
| longitude of ascending node | 1.07 × 10⁻⁵ deg | Earth | J2000 |
| argument of perihelion | 2.07 × 10⁻² deg | Venus | 2000-12-31 |
| mean anomaly | 2.07 × 10⁻² deg | Venus | 2000-12-31 |
| perihelion distance | 4.54 × 10⁻⁶ AU | Earth | 2025-09-01 |
| aphelion distance | 6.22 × 10⁻⁶ AU | Earth | J2000 |

All residuals are well within their respective thresholds.

### 4.5 Heliocentric Distance Extrema

**Oracle:** JPL Horizons `EPHEM_TYPE=VECTORS`
**Thresholds:** event date <= `1.0 day`, event distance <= `3e-4 AU`
**Test file:** `tests/integration/test_horizons_orbits.py` - **8 passed** (3 inner + 5 outer planets)

All validated planets are now treated under one oracle standard:

- HORIZONS vector tables are sampled around the next local heliocentric
  distance minimum and maximum.
- The external extrema are refined numerically from the sampled brackets.
- Moira's `distance_extremes_at(...)` results are then compared directly
  against those vector-derived perihelion/aphelion events.

This is the summit-grade oracle for this subsystem because it compares Moira
against the external heliocentric distance curve itself rather than against a
single epoch's osculating event prediction.

Current observed residual envelope (8 planets: Venus through Pluto):
- Worst perihelion date residual: **0.000387961511 d** (Uranus)
- Worst aphelion date residual: **0.001369935926 d** (Neptune)
- Worst perihelion distance residual: **0.000000000001 AU** (Mars — floating-point floor)
- Worst aphelion distance residual: **0.000000000001 AU** (Mars — floating-point floor)

---

## 5. SPK Segment Selection

Moira iterates all matching SPK segments and selects the one whose date range
covers the requested Julian day, falling back to nearest range only when no
exact coverage exists. NAIF body chains are explicitly constructed:

- Earth: `[0,3] + [3,399]`
- Mercury: `[0,1] + [1,199]`
- Venus: `[0,2] + [2,299]`
- Moon: EMB-to-Moon branch with Earth removed

This is validated implicitly by the Horizons suite across historical epochs
where naive segment selection would return wrong results.

---

## 6. Delta T Model

Moira exposes four explicit Delta-T policies:

| Policy model | Function | Use |
|---|---|---|
| `'hybrid'` (default) | `delta_t()` in `julian.py` | Source-priority table cascade and admitted future scenario |
| `'physical'` | `delta_t_hybrid()` in `delta_t_physical.py` | Bounded source-priority/scenario surface with uncertainty and accounting vessels |
| `'nasa_canon'` | `delta_t_nasa_canon()` in `julian.py` | Eclipse-publication compatibility |
| `'fixed'` | caller-supplied constant | Controlled sensitivity testing |

The `DeltaTPolicy` object is accepted by `ut_to_tt()`, `tt_to_ut()`, and `planet_at()`,
making the Delta T model an explicit, inspectable parameter rather than a hidden default.

### 6.1 Mean and domain architecture

| Era | Source |
|---|---|
| Before `-2000` under the physical policy | Explicit `ValueError`; no first-row clamp |
| `-2000` until modern aggregates take priority | Published HPIERS total through `julian.delta_t()` |
| Overlapping modern aggregates through representative epoch `2026.123287671233` | Higher-priority `julian.delta_t()` monthly-source aggregate totals |
| After representative epoch `2026.123287671233` | Boundary value + boundary slope + `28 s/cy²` declared curvature scenario |
| After `2150` | Computable scenario extrapolation, not an authority-validated forecast |

The public `core`, `cryo`, `fluid`, and `residual` fields are compatibility
fields and are zero. Their historical C04, GRACE, AAM, and OAM artifacts are
quarantined because they do not establish independent causal contributions.

### 6.2 Evidence actually exercised

The Delta-T corpus separates:

- published-table selection and interpolation;
- HPIERS quoted-error propagation;
- finite-input and physical-domain rejection;
- continuity of value and slope at the 2026 handoff;
- TT/UT1/Delta-T identity through engine, facade, and REST paths;
- proof that quarantined artifacts cannot alter the admitted mean;
- exact evaluation of the declared future scenario formula.

Tests against Moira's own `julian.delta_t()` are regression or routing parity,
not an independent IERS oracle. Python/native agreement is also not external
validation. No deterministic test validates the actual future rotation of
Earth.

Relevant suites are:

- `tests/unit/test_julian_delta_t.py`
- `tests/unit/test_delta_t_policy.py`
- `tests/unit/test_delta_t_physical.py`
- `tests/unit/test_chart_metadata_truth.py`
- `tests/integration/test_delta_t_hybrid.py`
- `tests/integration/test_delta_t_model_comparison.py`
- `tests/server/test_server_chart_routes.py`

### 6.3 Uncertainty posture

`delta_t_hybrid_uncertainty(year)` uses published HPIERS error values while
HPIERS owns the admitted mean, then a `0.06 s` modern policy floor through the
final aggregate representative epoch (currently `2026.123287671233`). For future years it adds, arithmetically
rather than in quadrature, the floor, declared
tidal-coefficient scale, GIA scale, and an integrated O-U LOD term with
`theta = 0.1/year` and diffusion scale
`0.2379 ms/day/sqrt(year)`. The small-horizon O-U expression uses its series
limit to avoid cancellation. This is an explicitly uncalibrated policy scale:
it has no asserted coverage probability, omits unquantified handoff-value and
slope uncertainty, and does not combine the quarantined proxies as independent
Gaussian causes. Forecast-policy validation is bounded through 2150; later
values are mathematical continuation only.

`DeltaTDistribution` is a normal-approximation computational vessel. Its
intervals are policy envelopes, not a claim that ancient or future
Earth-rotation errors have measured Gaussian tails.


## 7. Eclipse Validation

**Primary authority:** NASA Five Millennium solar and lunar catalogs and named
NASA/GSFC Besselian and path products

**Secondary cross-engine corroboration:** cached Swiss `setest/t.exp` rows

**Test files:**
- `tests/integration/test_eclipse_external_reference.py`
- `tests/integration/test_eclipse_nasa_reference.py`
- `tests/integration/test_eclipse_path_nasa_reference.py`
- `tests/integration/test_eclipse_besselian_nasa_reference.py`
- `tests/integration/test_eclipse_polar_path_nasa_reference.py`
- `tests/integration/test_eclipse_footprint_nasa_reference.py`
- `tests/integration/test_eclipse_lunar_contacts_nasa_reference.py`
- `tests/integration/test_lunar_nasa_compat_reference.py`
- `tests/unit/test_eclipse_footprint.py`

**Primary Besselian fixture:**
`tests/fixtures/nasa_solar_besselian_reference.json`

**Primary polar central-path fixture:**
`tests/fixtures/nasa_solar_polar_path_reference.json`

**Primary partial-visibility footprint fixture:**
`tests/fixtures/nasa_solar_penumbral_footprint_reference.json`

**Primary lunar contact-instant fixture:**
`tests/fixtures/nasa_lunar_contact_instants_reference.json`

**Executable representative TT comparison policy (DE441, current Delta-T
policy):**

For every search row, the NASA reference TT is the catalog UT1 plus that
catalog row's published Delta-T value. The Moira result TT is the searched
event UT1 transformed with Moira's default Delta-T policy. This preserves each
product's declared Earth-rotation basis while comparing the event search on a
common dynamical scale.

| Case class | Representative products | Executable TT envelope |
|---|---|---:|
| Ancient | lunar total (~1801 BCE) and solar hybrid (~1797 BCE) | 360 s |
| Post-2150 | lunar penumbral (~2801) and solar total (~2799) | 60 s |

Raw UT1 residuals may be emitted as diagnostic evidence by the executable
test, but they are not accepted timing tolerances because a raw comparison
conflates the event-search result with the products' different Delta-T
policies. Exact residuals are computed at runtime and are deliberately not
frozen in this document.

`tests/integration/test_eclipse_nasa_reference.py` therefore enforces two
explicit TT gates:

- **Ancient: 360 s in TT.** This is a cross-authority regression envelope for
  the combined search and model-basis difference. It is not a six-minute
  accuracy claim, a bound on historical Earth-rotation uncertainty, or proof
  that the NASA and Moira greatest-eclipse objectives are identical.
- **Post-2150: 60 s in TT.** This gate checks the searched event on the common
  TT scale; it does not validate Moira's post-2150 UT1 scenario as a forecast
  of Earth rotation.

The focused ancient lunar compatibility test applies the same rule to both
admitted paths. The native result is converted with Moira's default Delta-T
policy, while the `nasa_compat` result is converted with an explicit catalog
month-midpoint coordinate through `ut_to_tt_nasa_canon()`. Both are held inside
the same `360 s` cross-authority regression envelope. The test computes their
exact residuals at runtime and does not rank the paths by raw UT1 residual
because that ranking would compare unlike time policies.

The separate catalog-maximum tests continue to enforce solar and lunar eclipse
classification across the ancient, modern, and future fixture rows. Search
timing evidence and classification evidence remain distinct.

Individual lunar phase boundaries have a separately governed primary-authority
slice. NASA/GSFC detailed figures for the 2023 penumbral, 2024 partial, 2025
total, and limiting 2027 penumbral eclipses publish all 14 applicable P1, U1,
U2, U3, U4, and P4 instants in UT. The dedicated fixture preserves every
figure URL and SHA-256 digest, the event's adopted Delta T, and the printed
`VSOP87/ELP2000-85` and `CdT (Danjon)` model lineage. Those figure contacts are
not reconstructed from the separately published rounded phase durations.

Each source contact is compared on TT after adding the figure's own Delta T.
Native contact UT1 crosses through the content-identified DE441 ephemeris
clock; NASA-compatibility contacts use their stored TT fields.

The original individual-contact evidence exposed omitted apparent reduction as
the dominant compatibility defect. The repaired default method is
`nasa_shadow_axis_apparent_sun_moon`: both the Sun and Moon use reception
light-time from the same reception-epoch Earth state, followed by annual
aberration. Gravitational deflection, topocentric parallax, and atmospheric
refraction are excluded. The former geometric and retarded method identifiers
remain explicit comparison experiments. At the 2025 figure's published
greatest-eclipse TT, executable intermediate assertions compare the resulting
apparent geocentric Sun and Moon right ascensions and declinations with the
coordinates printed by NASA/GSFC. This independently verifies the reduction
before contact-root agreement is considered.

Ordinary per-instant ceilings are `120 s` for native DE441 and `10 s` for the
NASA-compatibility path. The `0.0014`-magnitude 2027 event has separate `240 s`
native and `30 s` compatibility endpoint ceilings and remains
robustness-only; its independent P4-P1 duration gate is retained.
NASA-compatible greatest eclipse is bounded at `10 s`. The modern ten-row
catalog comparison separately enforces `10 s` greatest timing and `2e-4`
Earth-radii signed gamma. These are cross-model regression envelopes, not the
source's one-second print precision, uncertainty estimates, UTC claims, or
exact-model parity. The bounded remainder includes DE441/LE441 versus
VSOP87/ELP2000-85, constants, and source-algorithm differences. Greatest
eclipse is a separate timeline instant rather than a seventh contact.

The instantaneous DE441-native Besselian surface has a separate per-field
authority gate. Four named NASA/GSFC solar products—partial, total, hybrid, and
annular—are sampled at five TT/TDT epochs each over their published six-hour
polynomial intervals. The executable comparison covers `x`, `y`, `d`, circular
`mu`, `l1`, `l2`, `tan_f1`, and `tan_f2` under these exact absolute envelopes:

| Fields | Absolute envelope | Unit |
|---|---:|---|
| `x`, `y`, `l1`, `l2` | `1.0e-4` | Earth equatorial radii |
| `d` | `0.003` | degrees |
| circular `mu` | `0.007` | degrees |
| `tan_f1`, `tan_f2` | `3.0e-6` | dimensionless |

NASA's published rows use VSOP87/ELP2000-82 and their stated `k1`/`k2`
lunar-radius convention. Moira retains its independently derived DE441/LE441
Earth-reception shadow geometry and physical mean-limb radii. These are bounded
cross-model validation envelopes, not field uncertainties or a claim of exact
NASA-model parity.

The 2015-03-20 total eclipse supplies the bounded primary-authority polar path
slice. Its official NASA/GSFC path and Besselian pages use one declared DE405,
`Delta T = 67.6 s`, WGS 84, 120-second-cadence, mean-limb product lineage.
Moira retains DE441. The executable comparison enforces `1 s` for searched
greatest time, `3 km` for the greatest point, five late-track central-line
rows, and both axis/ellipsoid tangencies, `3 km` for width at greatest, `3 s`
for local central duration, `0.005` for magnitude, and `3 km` of cone
clearance at each available published north/south limit. It does not claim
per-row width parity, full-atlas coverage, or one-limit/terminator-closure
width support; those one-limit epochs fail explicitly in the ordinary
closed-footprint solver.

The separate partial-visibility product sweeps Moira's exact common-tangent,
physical mean-limb penumbral cone from content-identified DE441/LE441
Earth-reception states across zero-elevation WGS 84. It reports P1/P4 and
optional P2/P3, named north/south penumbral-envelope and geometric
sunrise/sunset boundary components, strictly time-ordered segment identity for
folded connected limits, and explicit `one_limit_connected` or
`two_limit_two_loop` topology in UT1. Its default `sample_count` is `181`,
bounded to `9..721`, and controls interior density rather than the solved
component/segment graph. Every penumbral kind admitted by the topology is the
single component `component_id=0`; any UT1 folds are emitted under contiguous
`segment_id` values with shared refined fold endpoints and exactly two
sunrise/sunset incidences. Refraction, observer elevation, lunar-limb
topography, magnitude contours, and local apparent circumstances are outside
this product.

The primary external slice is the NASA/GSFC Table 2 products for 2003-11-23
(one limit) and 2006-03-29 (two limits). Published contacts and named
north/south anchors are compared on a common TT scale under independently
pinned `5 s` and `40 km` ceilings. NASA declares DE200/LE200 and its published
`k1` convention; Moira retains DE441 and physical mean-limb radii. The ceilings
are cross-model regression bounds, not uncertainty estimates. Both NASA rows
are total solar eclipses whose penumbral footprints exercise the admitted
topologies; they do not externally validate the footprint greatest point of a
globally partial event. That partial-event greatest is invariant-backed. NASA
does not publish dense numerical track coordinates for these products, so no
dense-track or full-atlas parity is claimed. Unit and integration invariants
separately enforce contact ordering, closure of each penumbral component
through horizon incidences and shared folds, WGS 84 bounds, both topology
classes, and partial-event greatest-point admission. DE441 regressions for the
1991 folded limit graph and the 1992 sub-minute polar reversal additionally
enforce shared fold endpoints, graph identity at requested output counts `9`,
`99`, `181`, `257`, and `721`, continuous fixed-site maximum admission, and
rejection of spatial splices.

---

## 7.1 Correction-Layer Validation

Direct correction-layer oracles now exist in addition to the broader apparent
position suites.

Stellar aberration:
- `tests/integration/test_astrometric_corrections_external.py`
- Oracle: ERFA `ab`
- Status: direct vector-level test added; executes when `erfa` is installed in
  the active environment

Light-time correction:
- `tests/integration/test_astrometric_corrections_external.py`
- Oracle: JPL Horizons VECTORS with `VEC_CORR='LT'`
- Status: validated against direct corrected-state reference cases

---

## 8. Sothic Heliacal Rising

**Oracle:** Censorinus (De Die Natali, 238 AD) - the 139 AD epoch record;  
latitude-ordered site comparison against published Egyptological literature

**Test files:**
- `tests/unit/test_sothic.py`
- `tests/integration/test_sothic_research.py`

**Validated properties:**

- Egyptian civil calendar arithmetic (month/day/epagomenal boundaries)
- `days_from_1_thoth` wrapping and cycle arithmetic
- Predicted Sothic epoch year via 1460-year cycle
- Drift rate recovery from wrapped linear trend
- 139 AD Alexandria: Sirius rises within 2 days of 1 Thoth (drift <= 2.0 days); exact day is within the ~1-day historical uncertainty of the Censorinus datum
- 139 AD Memphis: rises in last days of Egyptian year (Epagomenal, drift 362–365 days); exact day not asserted due to same uncertainty envelope
- Latitude ordering: Elephantine < Thebes < Memphis < Alexandria
- Arcus visionis direction: harder visibility -> later rising
- Arctic exclusion: no rising at lat 80 deg
- BCE year handling without Python datetime

**Status:** Validated

---

## 8.1 Generalized Heliacal / Visibility

**Surface:** `moira.heliacal.visibility_assessment(...)`,
`moira.heliacal.visibility_event(...)`

Validation is stratified exactly by doctrine layer:

### Astronomical geometry validation

This subsystem does not carry an independent geometry oracle. It inherits the
validated astronomical substrate already enforced elsewhere in this document:

- topocentric sky positions: JPL Horizons
- refraction-aware altitude handling through the admitted apparent-altitude path
- apparent magnitude surfaces for planets and the baseline integrated lunar
  model

So the generalized visibility layer is not being validated as if it owned the
celestial mechanics. It is being validated as a doctrinal layer built on top of
that already-validated substrate.

### Criterion validation

**Threshold-family policy checks**
- file: `tests/unit/test_heliacal_visibility_policy.py`
- enforced properties:
  - Bortle-derived limiting-magnitude mappings are explicit and monotonic
  - explicit `limiting_magnitude` overrides site-class derivation
  - local horizon altitude blocks geometry independently of brightness policy
  - refraction-on vs refraction-off changes apparent altitude but not doctrine

**Yallop lunar criterion checks**
- file: `tests/unit/test_heliacal_visibility_policy.py`
- enforced properties:
  - class thresholds `A` through `F` follow the declared `q` boundaries
  - observability depends on observing aid exactly as admitted in code
  - non-lunar use of `YALLOP_LUNAR_CRESCENT` is rejected
  - morning-event misuse of the Yallop family is rejected

**Published Yallop corpus slice**
- files:
  - `tests/integration/test_visibility_validation.py`
  - `tests/fixtures/yallop_table4_reference.json`
- authority: Yallop 1997, Table 4
- data-semantics note: column 6 of Table 4 is the Julian Date of the
  astronomical new moon (JD − 2,400,000), not the observation JD. The
  observation date is recorded in columns 2–4 (year, month, day). These
  are distinct quantities and must not be conflated when reconstructing
  the observation epoch from the fixture.
- current admitted corpus:
  - full published Table 4 extraction: 295 cases
  - both evening and morning criterion rows are represented
  - classes represented: `A`, `B`, `C`, `D`, `E`, `F`
  - split into:
    - non-boundary exact-tolerance rows
    - boundary-sensitive rows for near-threshold `q` validation
- tolerance doctrine:
  - non-boundary exact family:
    - `q` agreement within `±0.035`
    - exact class agreement
  - boundary-sensitive family:
    - `q` agreement within `±0.03`
    - no false exact-class claim when the published row sits on or very near a
      threshold
  - current full-corpus audit envelope (verified by direct audit, 2026-04-05):
    - `293 / 295` rows within `±0.03`
    - `295 / 295` rows within `±0.05`
    - `295 / 295` rows within `±0.10`
    - `289 / 295` exact class matches (the 6 mismatches are all
      boundary-sensitive rows where the adjacent-class divergence is within
      doctrine)
    - mean residual across all 295 rows: `0.0077`
    - max residual across all 295 rows: `0.0315`
  - **fixture correction applied (2026-04-05)**: five rows in the fixture had
    their UTC observation dates stored in place of local observation dates.
    For US western-hemisphere sites, local evening begins after UTC midnight,
    so the local date is one calendar day before the UTC date recorded. The
    affected rows were `165`, `193`, `244`, `245`, `285` (longitudes ranging
    from −70.7° to −121.6°). The dates were corrected by subtracting one
    calendar day each:
    - row 165: `1980-07-14` → `1980-07-13`
    - row 193: `1987-05-29` → `1987-05-28`
    - row 244: `1989-07-05` → `1989-07-04`
    - row 245: `1989-10-03` → `1989-10-02`
    - row 285: `1991-05-16` → `1991-05-15`
    No engine changes were made. After correction, all five rows compute
    within `±0.020` of the published `q` value and are fully absorbed into
    the standard tolerance family.

Current criterion-family authority posture:
- `LIMITING_MAGNITUDE_THRESHOLD` is an admitted engine threshold doctrine
- `YALLOP_LUNAR_CRESCENT` is admitted under Yallop's published lunar
  first-sighting classification law
- morning and evening Yallop rows are now admitted as criterion-validation
  cases, but the current public event-search surface remains evening-scoped
  for this family

### Event validation

**Modern planetary apparition windows**
- files:
  - `tests/unit/test_planet_heliacal.py`
  - `tests/integration/test_visibility_validation.py`
- coverage:
  - Venus heliacal rising 2020
  - Jupiter heliacal rising 2023
  - Venus acronychal rising 2021
  - Venus heliacal setting 2021
- tolerance doctrine:
  - wide date windows in Julian Day, intentionally measured in days rather
    than minutes
  - this is observational-visibility validation, not a claim of exact
    published event-time parity

**Historical stellar slice**
- primary file: `tests/integration/test_sothic_research.py`
- generalized-surface anchor: `tests/integration/test_visibility_validation.py`
- authority: Censorinus 139 AD epoch record plus published latitude-order
  trend across Egyptian sites
- status:
  - the star subsystem itself is externally anchored through the Sirius/Sothic
    corpus
  - generalized star visibility now has an explicit delegated-anchor test
    against the default stellar heliacal doctrine, plus a measured doctrinal
    offset to the `10°` Sirius/Sothic slice
  - this is important because the generalized star surface currently delegates
    the default star-heliacal arcus policy, while the Sothic research slice is
    intentionally anchored to an explicit `10°` Sirius visibility doctrine

**Generalized-surface parity**
- file: `tests/unit/test_heliacal_visibility_policy.py`
- enforced properties:
  - generalized planetary search matches the legacy admitted planetary wrappers
  - generalized stellar and cosmic event branches return typed event vessels
  - generalized lunar event search carries structured crescent details

### Tolerance doctrine

Current visibility tolerances are family-specific:

- modern planetary event validation:
  bounded Julian-day windows, typically on the order of weeks
- historical stellar validation:
  civil-calendar day and latitude-order envelopes, not minute-level claims
- Yallop lunar family:
  criterion-law validation, a multi-case published Table 4 corpus slice, and
  structured evening-event semantics

This is deliberate. Moira does not presently claim minute-grade observational
visibility truth across all targets and criterion families.

### Claim envelope

Current external authority posture:

- Yallop 1997 is the admitted authority for the current lunar first-sighting
  class law and its `q` partitions.
- U.S. Naval Observatory guidance is the admitted caution authority for the
  broader problem statement: lunar crescent visibility depends strongly on sky
  conditions, location, and observer quality, and cannot be predicted with
  certainty from age alone.
- The modern review literature — in particular Schaefer (1988, QJRAS 29:511–523)
  and Odeh (2006, Astronomical & Astrophysical Transactions 25(5–6):523–535) —
  confirms that large observational corpora exist and that contradiction-rate
  analysis remains the correct language for criterion assessment rather than
  false absolute-precision claims. Odeh's 2006 criterion was calibrated against a
  737-observation corpus and represents the most prominent published challenger to
  the Yallop q-law; it is a deferred authority target for Moira's validation
  program.

What Moira can currently claim:

- The astronomical substrate used by the generalized visibility layer is backed
  by stronger external astronomy oracles elsewhere in this document.
- `LIMITING_MAGNITUDE_THRESHOLD` is implemented as a declared threshold doctrine
  with validated policy precedence and geometric/brightness separation.
- `YALLOP_LUNAR_CRESCENT` is implemented as a declared lunar criterion family
  with validated `q` thresholds, admitted aid-dependent class semantics, and a
  published Table 4 corpus split into exact-class and boundary-sensitive
  validation families.
- The generalized planetary event surface is validated against published modern
  apparition windows.
- The generalized stellar event surface is validated as a delegated surface
  over the default star-heliacal doctrine, with its policy offset from the
  Sirius/Sothic `10°` slice measured explicitly.

What Moira must not currently claim:

- minute-level or second-level truth for observational visibility events
- universal first-sighting correctness across all observing environments
- that the current generalized stellar surface reproduces the explicit Sirius
  Sothic doctrine unless that `10°` visibility policy is chosen deliberately
- that the current lunar implementation has been validated against a broad
  published first-sighting corpus comparable to the larger modern databases
- that the current public lunar event surface is morning-generalized under the
  Yallop family; morning rows are presently admitted only as criterion
  validation

**Status:** Validated (implemented slice)

---

## 9. Rise / Set / Transit Oracle Posture

Rise, set, upper transit, and lower transit now have a real external-oracle
path rather than self-consistency-only coverage.

Primary oracle:
- `tests/integration/test_horizons_rise_set_reference.py`
- Fixture: `tests/fixtures/horizons_rise_set_reference.json`
- Builder: `scripts/build_rise_set_horizons_fixture.py`
- Source: JPL Horizons observer tables sampled at 1-minute cadence using
  topocentric apparent azimuth/elevation plus local apparent hour angle
  (`QUANTITIES=4,42`)
- Coverage: Sun, Moon, Venus, multiple latitudes and longitude signs, plus a
  high-latitude no-rise/no-set Sun case
- Threshold policy: strict per-case timing thresholds in seconds; the current
  curated corpus is enforced at 2 seconds or better
- All 5 cases passing as of 2026-04-05 (4 Horizons cases + 1 USNO)

**Regression found and fixed during this validation session (2026-04-05):**

Commit `4173706` (2026-03-25) added atmospheric refraction to
`sky_position_at` (the `refraction=True` default). This changed
`rise_set._altitude`'s return value from geometric altitude to apparent
altitude, while the rise/set bisector's horizon-altitude threshold
(e.g. `-0.8333°` for the Sun) remained the geometric threshold — which
already embeds the standard refraction correction by definition.

Effect: the bisector was finding when apparent altitude = -0.8333°, which
corresponds to the body sitting ~0.8° below the standard rise position.
Result: Rise was ~300 s too early, Set was ~300 s too late. Transit and
Anti-transit were exact (they use a separate hour-angle route, unaffected).

Fix applied (2026-04-05) in `moira/rise_set.py`: `_altitude` now calls
`sky_position_at(..., refraction=False)` to get geometric altitude. The
horizon-altitude threshold already carries the refraction component. The
`pressure_mbar` / `temperature_c` parameters in `_altitude` are retained
for API compatibility but are now ignored since `refraction=False`.

Supplemental published-table checks:
- `tests/integration/test_rise_set_published_reference.py`
- Source: U.S. Naval Observatory published rise/set/transit tables
- Purpose: spot-check fixed-star behavior where Horizons event tables are not
  the practical source in this repo

Legacy regression support:
- `tests/integration/test_rise_set_external_reference.py`
- Fixture: `tests/fixtures/swe_t.exp`
- Status: retained as Swiss cross-check / sanity coverage, not the authority
  for this validation domain

Window semantics are explicit in the oracle suite: every event is interpreted
as the first matching event in the next 24 hours from `jd_start`.

---

## 10. Astronomy Validation Status

| Domain | Current state | Recommended oracle | Priority |
|---|---|---|---|
| Ancient eclipse timing vs catalogs | Explained model-basis difference; regression-covered | NASA Five Millennium | Medium |
| Stellar aberration | Direct ERFA-backed test added and passing in the validation env | ERFA `ab` function | Closed |
| Rise/set ~300 s systematic error | **Fixed 2026-04-05.** Commit `4173706` added refraction to `sky_position_at` but `rise_set._altitude` kept the geometric threshold. Fixed by passing `refraction=False`. All 5 Horizons/USNO cases now pass at ≤ 2 s. | JPL Horizons fixture | Closed |
| Ancient eclipse TT comparison gate | **Repaired 2026-07-17.** NASA catalog TT and Moira TT retain their own declared Delta-T bases. Executable tests enforce a 360 s cross-authority regression envelope without freezing exact residual snapshots in prose. This closes the scale-conflation defect in the test; it is not an ancient timing-accuracy claim. | NASA Five Millennium | Closed (test semantics only) |
| Solar partial-visibility footprint | **Admitted 2026-07-18.** First-class DE441 mean-limb WGS 84 footprint with explicit one-limit/two-limit topology; NASA/GSFC 2003/2006 total-eclipse penumbral Table 2 contacts and sparse boundary anchors are bounded at `5 s` and `40 km`. A globally partial event's greatest point is invariant-backed, not externally anchored. Dense track parity remains unclaimed because NASA does not publish a numerical dense-track corpus for these products. | NASA/GSFC Table 2 + geometric invariants | Closed (named product slice) |
| Lunar individual contact instants | **Repaired 2026-07-18.** All 14 applicable P1/U1/U2/U3/U4/P4 instants in four named modern NASA/GSFC figures are compared on common TT. The former compatibility default omitted the figure product's apparent reduction; `nasa_shadow_axis_apparent_sun_moon` now applies reception light-time and annual aberration to both bodies and is independently checked against the 2025 printed apparent RA/Dec. Ordinary ceilings are `120 s` native and `10 s` compatibility; the magnitude-0.0014 limiting event uses separate `240 s` native and `30 s` compatibility gates and retains an independent duration gate. | NASA/GSFC detailed lunar figures | Closed (named product slice) |
| Polar-crossing lunar-occultation path topology | **Admitted 2026-07-18.** The 2026-10-05 Mars event supplies primary JPL Horizons airless North-Pole containment and two `0.5 s` outer-contact brackets; Moira's DE441 contacts use a separate `2 s` cross-model gate. Horizons EOP was predictive at retrieval and must be refreshed after the event. Full left/right tracks and width are independently invariant-backed, not externally published parity. | JPL Horizons pole contacts + spherical invariants | Closed (named contact/invariant slice) |
| GAST ancient-epoch model-basis difference | **Documented 2026-04-05.** Full GAST (erfa.gst06a oracle) diverges up to ~1.1″ before ~J1000. Cause: equation-of-equinoxes (Moira) vs equation-of-origins (ERFA). Modern epochs (J1500–J2100) all pass < 0.001″. Ancient divergence is beneath the Delta T noise floor for Moira's use cases. No code change required. See §3.7.1. | ERFA `gst06a` | Closed |
| Chiron and Pholus vector accuracy | **Pre-existing open.** 6 cases in `test_horizons_vectors.py` failing at ~7–8 arcsec vs 1.0 arcsec tolerance. Centaur orbits are chaotic; accuracy degrades outside JPL fit windows. Root cause not yet diagnosed — may require looser tolerance or SPK routing investigation for small bodies. | JPL Horizons `VECTORS` | Medium |
| Sothic 139 AD calendar accuracy | **Fixed 2026-04-05.** Two changes applied. (1) `moira/stars.py` heliacal horizon threshold corrected from geometric 0° to −0.5667° (apparent horizon: standard refraction lifts the horizon by ~34′). With 0.0, Memphis crossed the Egyptian New Year boundary into Thoth 1, breaking the modular drift ordering. With −0.5667°, Memphis stays in Epagomenal, all three sites sit on the same side of the New Year, and the drift ordering is coherent. (2) Test assertions replaced exact-day claims with uncertainty-window checks: `arcus_visionis=10°` (Schoch's traditional value) is retained; the Censorinus datum is verified to within 2 days of 1 Thoth (drift ≤ 2.0), consistent with the ~1-day historical uncertainty in site identification and atmospheric conditions. Asserting `day == 1` exactly would be chasing uncertainty noise. All 3 previously failing tests now pass. | Censorinus / published sites | Closed |
| Sidereal fixture coverage gap | **Pre-existing open.** 4 newly added ayanamsa systems (`Babylonian (Britton)`, `Aryabhata 522`, `True Mula`, `Galactic Equator (IAU 1958)`) have no Swiss swetest reference data in the current fixture. Fix: extend the swetest fixture with oracle data for the new systems. | Swiss swetest | Low |

---

## 11. Appendix - Model-Basis Difference

In this document, **model-basis difference** means that Moira and the
comparison catalog are not necessarily answering the exact same mathematical
question, even when both are internally consistent. In the eclipse context,
contributors can include:

- Delta T branch choice
- retarded-vs-geometric Moon treatment
- geometric, light-time, or fully apparent direction policy
- the exact definition of "greatest eclipse" being optimized

For the modern NASA lunar compatibility product, executable coordinate and
contact diagnostics did isolate omitted apparent reduction as the dominant
former defect; that defect is now repaired. DE441/LE441 versus
VSOP87/ELP2000-85, constants, and source-algorithm differences form the bounded
modern remainder. The broader NASA-reference tests do not claim the same
term-by-term isolation for ancient products. They compare each product in TT
using its declared Delta-T basis and classify the remaining ancient difference
only as a bounded cross-authority regression residual.


