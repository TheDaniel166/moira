# Orbital Core — Design Spec

**Date:** 2026-09-15
**Status:** Revised draft for review. Successive 2026-09-15 contract passes
corrected the gravity, time-scale, frame, source-receipt, passage, classification,
compatibility, Shadbala boundary and validation designs against the primary
authorities named below. An implementation plan may be written only after this
revised scope is approved; this document does not authorize implementation or
release.
**Repository:** `C:\dev\moira` (`moira-astro`)
**Related work:** Urania asteroid catalog (MoiraWeb); asteroid catalog
expansion (separate spec).

## Problem

`moira.orbits` was designed for the Mercury-through-Pluto legacy list. Every
other body Moira carries a trajectory for — the Earth–Moon barycenter, the Moon,
the 10,025
catalogued asteroids, centaurs and TNOs, and the periodic-comet catalog — has
no orbital elements and no perihelion/aphelion search. The P-GAP-03 standard
lists asteroid and comet elements as non-goals and the REST transport rejects
`Ceres`.

Consumers improvise around the gap. Urania's asteroid catalog labels every
body outside 18 hardcoded names "Main-belt asteroid", which is wrong for Eros,
Apollo, Icarus, Hektor and 46 catalogued TNOs and centaurs. Inside the engine,
orbital elements are computed in four places with different gravity values,
frames and body lookups; three of them are wrong in ways that reach public
output.

A 2026-09-14 spike showed the capability already exists: Moira's Sun-centered
small-body trajectories plus its existing state-to-elements math reproduce JPL
Horizons osculating elements (eccentricity within 3e-9, angles within 0.03″)
and JPL SBDB orbit classes.

## What is wrong today

Measured 2026-09-14/15 against JPL Horizons, JPL SBDB, JPL
`gm_Horizons.pck`,
the local DE441 kernel and the production kernel set. Numbers are in the
appendix.

### `moira/orbits.py`

- Body lookup is planet-only (`NAIF_ROUTES`). Asteroids, comets, NAIF integers
  and lowercase names raise a bare `KeyError`.
- Gravity does not follow JPL's rules. Mercury, Venus and Earth use the Sun's
  GM alone; Jupiter uses a non-DE440 system value; the Sun's value is the
  DE405-era `1.32712440018e11` although labeled DE441. At J2000 Earth's
  semi-major axis is 465 km from JPL's, Jupiter's 115 km, Mercury's 6 km.
- `KeplerianElements.epoch_jd` is documented as TT but holds the UT input.
  `DistanceExtremes` times have the same mismatch.
- Circular or zero-inclination orbits receive a silent 0° for undefined
  angles. Parabolic states raise. Hyperbolic states return a negative
  semi-major axis with mean anomaly 0 and an infinite period.
- `reader=None` crashes with `AttributeError`.
- `distance_extremes_at` delegates to `phenomena.perihelion/aphelion`, which
  reject non-planets and size their searches from a fixed planet-period table.

### Other copies of the element math

- `planetary_nodes.geometric_node` (REST `/v1/nodes`) documents support for
  "Chiron… asteroids, TNOs", but its lookup knows only the Sun, Moon and
  planets. It uses the DE405-era Sun GM and no planet GM.
- `phenomena` has its own planet-only heliocentric state code.
- `shadbala` contains two private osculating-element helpers, but their premise
  is not supported by the cited primary text. Raman's Chapter VI describes
  Chesta Bala for the five non-luminaries; Chapter X §§136–137 gives separate
  Sun and Moon rules. The Sun uses 90° added to its sayana longitude and the
  Moon uses its angular distance from the Sun, each reduced to 180° and divided
  by three. Neither rule calls for a lunar or solar apsis. The code and public
  standard repeatedly use an inapplicable "Raman Ch. 9" citation for the
  apsidal method; that chapter does not supply this construction.
  The current non-luminary speed-ratio shortcut also is not Raman's Chapter VI
  Seeghrochcha/mean-and-true-longitude construction. This is a doctrine defect,
  not an orbital-elements migration.
- Independently of that doctrine defect, the unused-after-correction apsidal
  helpers are astronomically inconsistent: the Earth body perihelion swings
  5.8° within a month because of the Moon; the lunar helper uses Earth-only
  gravity, returns perigee while the solar helper returns apogee, and both mix
  J2000-equinoctial angles with a longitude-of-date sidereal conversion.
- `nodes.true_lilith` is a correct fourth copy (Earth + Moon gravity, apogee
  orientation). It stays unchanged and serves as an in-house reference.

### Error infrastructure

- Two different classes are named `OutOfRangeError` (`spk_reader`,
  `_spk_body_kernel`). Reading a small-body kernel directly raises `KeyError`
  for a coverage miss; the kernel pool raises `OutOfRangeError` for the same
  condition.
- Two missing-kernel errors exist: `spk_reader.MissingKernelError`, raised by
  computational modules that find no reader, and
  `facade.MissingEphemerisKernelError`, raised by the facade's kernel loading
  and by server startup. REST maps only the second (to 503); the first has no
  handler and surfaces as a 500.
- REST maps every `ValueError` and `KeyError` to HTTP 422 `validation_error`.
  A typo, a date outside coverage and an uninstalled body are
  indistinguishable; an uninstalled asteroid reads like a date problem.
- `KernelPool.position_and_velocity` does not chain centers, and its docstring
  still says small-body readers raise `NotImplementedError`.

## Decisions

| # | Decision |
|---|---|
| D1 | `orbits.py` becomes the engine's single orbital-elements core. Perihelion/aphelion search and `geometric_node` move onto it in separately verified stages. Shadbala does not: its apsidal premise is contradicted by Raman's primary text and is corrected under a separate doctrine design. |
| D2 | A new typed core with explicit center and frame. Today's public functions remain as corrected planet wrappers. No 7.0 break. |
| D3 | Admitted bodies: planets (as their DE441 routes), the Earth body, the Earth–Moon barycenter, the Moon, and every catalogued asteroid (including centaurs and TNOs) and comet. |
| D4 | Centers in this design: Sun, and Earth for the Moon only. Solar-system-barycentric state routing is retained internally, but barycentric osculating elements are deferred to a separate design because no public primary source states the target-dependent Keplerian GM rule used by Horizons. |
| D5 | Planet inconsistencies are corrected with a pinned, hashed snapshot of JPL Horizons' element-conversion GMs. UT1 remains the public input scale, TT is used for Earth-orientation models and the existing `KernelReader` compatibility methods, and TDB is used for SPK polynomial evaluation and Horizons comparison. New internal methods name TDB explicitly; existing TT-labelled methods and the TT-facing native-evaluator surface convert exactly once before delegating and are not silently relabelled. TT<->TDB follows the pinned NAIF leapseconds-kernel model used by SPICE, not an unnamed approximation. The measured shifts go in the changelog. |
| D6 | One `OrbitalError` base. Every error also inherits the built-in type callers catch today, carries structured attributes, and replaces the inconsistent low-level errors at the boundary. Invalid requests raise; a legitimate "no answer" is a returned outcome. |
| D7 | Orbit class (stage 5) is an SBDB-style osculating asteroid classification at the requested date. It is computed from Moira's own Sun-centered elements with JPL's published boundaries and reports structured, unit-preserving margins for every evaluated predicate. Comet subclasses are deferred. |
| D8 | Engine first. REST access for small bodies is a later, separate stage. The existing `/v1/orbits/*` routes keep their planet list. |
| D9 | Four validation layers (math, kernel, full catalog, live), independent primary-source oracles, and separate calibration and frozen holdout corpora. No tolerance may absorb an unresolved systematic error. |
| D10 | Every state route carries an exact source receipt and an exact set of contiguous TDB coverage intervals. Public provenance uses stable logical identities and hashes, never local absolute paths. |
| D11 | IAU SOFA, not an existing internal transform, owns date-frame truth. Bias ownership is route-specific: `Pmat06` and `Pnm06a` already include it, `Ltp` does not, and `Ltpb` does. The current chart stack mixes those contracts. Stage 1 makes each selected matrix bias-inclusive exactly once; a blanket deletion of `apply_frame_bias` is forbidden. The protected-zone change has a call-site inventory, boundary tests, measured downstream shifts and its own receipt. |
| D12 | A passage search binds one deterministic state-route plan before sampling. It never changes kernel, segment-precedence policy or center chain inside a bracket. An endpoint is a found extremum only when a two-sided derivative/distance witness exists inside the bound route coverage. |
| D13 | Orbit-class precedence is an explicit Moira contract derived from JPL's published predicates; it is not inferred from the display order of JPL's table, where `AST` appears before `CEN` and `TNO`. The numerical parabolic tolerance is disclosed wherever it differs from JPL's literal `e = 1` wording. |
| D14 | The inspected Raman text resolves the Shadbala boundary: orbital apsides are not Chesta Bala inputs. Stage 1 preserves the current Shadbala algorithm, branches and public contract through adapters; its only permitted numerical change is the separately measured shared TT→TDB reader correction. A separately approved Shadbala design replaces the non-luminary and luminary rules together and removes the private orbital helpers. |

## Goals

- Every admitted body-center pair yields osculating elements in an explicit
  frame within that frame model's declared date range, with complete time,
  gravity, route and source provenance.
- The same bodies yield pericenter and apocenter passages, bounded by kernel
  coverage and honest when a passage is unavailable.
- J2000-ecliptic elements agree with frozen JPL Horizons holdout data within
  predeclared gates established from a disjoint calibration corpus. Moira's
  IAU 2006/2000A date frames agree with the pinned IAU SOFA routines; they are
  not presented as Horizons ecliptic-of-date output.
- Every failure is a named, structured, backward-compatible error.
- Engine modules stop carrying private copies of element math.
- Existing callers keep working. Behavior changes are limited to the approved
  corrections, each documented.

## Non-goals

- REST admission of small bodies (stage 6, with its own review).
- Mean elements or proper elements. Proper elements stay in
  `asteroid_families`.
- Elements about any other center (planets about Earth, satellites about
  planets).
- Solar-system-barycentric osculating elements. DE440/DE441 defines the SSB
  from the Sun, planetary systems, 343 asteroids, 30 KBOs and a KBO ring, while
  live Horizons returns target-dependent element-conversion GMs. Admission
  requires a separate primary-source-backed gravity contract; it is not
  approximated from Sun + planetary-system GMs in this design.
- Replacing the doctrine, API or internal element method of `true_lilith`,
  `true_node` or any other lunar product. Shared reader-clock and frame-bias
  corrections can still produce measured compatibility shifts in those
  consumers; Stage 1 must record them rather than claiming literal non-change.
- Unifying the two `OutOfRangeError` classes or the two missing-kernel errors
  inside `spk_reader` and `facade`, beyond relocating one class (see Errors).
  This spec translates them at the orbital boundary.
- Claiming that Moira's date frames are Horizons' ecliptic-of-date. Horizons
  uses its documented IAU76/80 and Owen routing; the frames in this API use the
  separately named SOFA contracts below.
- Extrapolating `TRUE_ECLIPTIC_OF_DATE` outside its declared modern model
  interval by combining incompatible precession and nutation families.
- The asteroid catalog expansion (1,198 TNOs and centaurs, designations,
  names) and the Urania catalog UI.

## Primary authorities

External doctrine and validation in this design use only first-party standards,
data products and service output:

- JPL Solar System Dynamics, [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html)
  and [Horizons API specification](https://ssd-api.jpl.nasa.gov/doc/horizons.html).
- JPL Solar System Dynamics,
  [`gm_Horizons.pck`](https://ssd.jpl.nasa.gov/ftp/xfr/gm_Horizons.pck), the
  current element-conversion mass-parameter artifact named by the Horizons
  manual.
- Park, Folkner, Williams and Boggs,
  [The JPL Planetary and Lunar Ephemerides DE440 and DE441](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440_and_de441.pdf),
  published by the JPL ephemeris team.
- NASA/JPL NAIF, [SPK Required Reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html)
  and [SPICE Time Required Reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/time.html).
- NASA/JPL NAIF,
  [`naif0012.tls`](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls),
  the versioned leapseconds kernel containing the `DELTET/K`, `DELTET/EB` and
  `DELTET/M` constants used by SPICE's TT/TDB conversion.
- IAU Standards of Fundamental Astronomy,
  [SOFA Issue 2023-10-11 and model notes](https://www.iausofa.org/current-software)
  and its
  [versioned ANSI C source](https://www.iausofa.org/s/sofa_c-20231011.zip),
  including `iauEcm06`, `iauPmat06`, `iauPnm06a`, `iauObl06`, `iauNut06a`,
  `iauLtecm`, `iauLtp`, `iauLtpb`, `iauLtpecl`, `iauLtpequ` and `iauDtdb`.
- JPL Small-Body Database,
  [official orbit-class definitions](https://ssd-api.jpl.nasa.gov/doc/sbdb_filter.html)
  and [query API specification](https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html).
- B. V. Raman, *Graha and Bhava Balas*, inspected primary-text scan containing
  a thirteenth-edition preface dated 1 February 1992, is the primary doctrinal
  source for the
  Shadbala boundary. Chapter VI, "Chesta Bala or Motional Strength"
  (pp. 64–79), governs the five non-luminaries; Chapter X §§136–137
  (pp. 101–103) gives the special Sun and Moon rules. Stage 4 must preserve a
  hash of the inspected page images and record the exact edition/imprint before
  changing the doctrine. Later summaries of Raman are not substitutes.

Frozen Horizons and SBDB API responses are primary-source data artifacts. Each
fixture carries the full request, response hash, retrieval timestamp and
service signature/version. No blog, tutorial by a third party, crowd-sourced
table or unsourced remembered convention is an authority for acceptance.

The mutable/current landing pages are discovery surfaces, not reproducibility
anchors. The Stage 1 source ledger pins the artifacts retrieved 2026-09-15:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `gm_Horizons.pck` | 15,428 | `169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c` |
| `naif0012.tls` | 5,257 | `678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b` |
| `sofa_c-20231011.zip` | 3,686,708 | `375729d8c0a254fd27c55484de5c8b83cccef351e1ef19d9cf7f26f5485e5538` |

## Architecture

### Units

| Unit | Status | Responsibility | Depends on |
|---|---|---|---|
| `moira/_orbital_errors.py` | new, private | Every orbital error class. Imported by the other units; public names re-exported from `moira.orbits`. | `spk_reader`, `small_body_identity` |
| `moira/_ephemeris_gm.py` | new, private | The pinned JPL Horizons GM snapshot, source hash, gravity-rule selection, and admission by planetary ephemeris identity. | `spk_reader._EphemerisKernelIdentity` |
| `moira/_orbital_state.py` | new, private | Resolve body identity; check center admissibility; fetch the state and exact route receipt; intersect exact coverage intervals; translate low-level ephemeris failures. | `constants`, `small_body_identity`, `spk_reader`, `_spk_body_kernel`, `_ephemeris_time`, `julian`, `_orbital_errors` |
| `moira/_orbital_frames.py` | new, private | Construct the three declared element frames from the pinned SOFA contracts; own model routing, single-bias assembly and frame provenance without reusing an unaudited chart transform. | `coordinates`, `precession`, `obliquity`, `nutation_2000a` |
| `moira/_ephemeris_time.py`, `moira/julian.py` | existing, extended | Bind UT1->TT to the serving ephemeris identity; implement the pure, versioned NAIF-LSK TT<->TDB conversion in `julian.py`; and perform stable-identity iteration at pool boundaries. The pure converter stays below `spk_reader` to avoid an import cycle. | pinned `naif0012.tls` constants; `_ephemeris_time.py` also depends on `spk_reader` |
| `moira/spk_reader.py` | existing, extended without adding requirements to the public `KernelReader` protocol | Private, explicitly TDB-named state/source-receipt and exact-disjoint-interval capability; TT compatibility adapters; velocity-capable center chaining for built-in orbital routes. | existing reader implementations, pure TT<->TDB converter in `julian.py` |
| `moira/_spk_body_kernel.py` | existing, extended | Preserve verified manifest identity, release hashes and exact segment intervals on readers opened from a sovereign manifest. | `small_body_catalog_release` |
| `moira/orbits.py` | rewritten, public | Enums, vessels, element extraction, `osculating_elements`, `apsidal_passages`, legacy wrappers. | the units above |

Errors live below `orbits.py` so that `_orbital_state.py` can raise them
without an import cycle.

### Data flow of `osculating_elements`

1. Validate `jd_ut` (a finite real number other than `bool`), `center` and
   `frame` (enum members or their string values). Failure:
   `OrbitalInputError`.
2. Resolve the body to an `OrbitalBodyIdentity` (see Body resolution).
3. Check that the center is allowed for the body. Failure:
   `OrbitalCenterNotAllowedError`.
4. Bind the reader: the explicit `reader`, else the active reader context.
   None available: `OrbitalKernelMissingError`.
   The strict API also requires the private TDB route/source capability. A
   third-party object satisfying only the historical `KernelReader` protocol
   remains valid for legacy calls but raises `OrbitalSourceReceiptError` here;
   the core never guesses its epoch scale or serving source. For a pool, capture
   one immutable ordered-reader snapshot and generation under a read lease;
   clock identity and state routing below must use that same snapshot.
5. Convert UT1 to TT and TDB and bind the planetary-ephemeris identity as one
   stable operation:
   - resolve Moira's source-owned ΔT product at `jd_ut`;
   - form provisional TT and TDB, then select the planetary identity at that
     TDB epoch. A pool obtains it from its TDB-named planetary route. A
     standalone planetary reader supplies its content-derived identity and
     must serve the canonical clock routes at that epoch. A standalone
     sovereign small-body reader instead supplies the DE440/DE441 integration
     identity from its verified manifest. An unidentified standalone reader is
     not silently assumed to be DE441;
   - apply any declared historical tidal-basis correction for that identity;
   - recompute TT and TDB and require the selected identity to remain the same.
     If the corrected epoch crosses a pool boundary, repeat to a fixed point or
     raise `OrbitalTimeBasisError`; never query a TDB kernel with a TT-labelled
     coordinate.
   The TT/TDB leg uses the pinned NAIF LSK equations in the Time section.
   Representability failures are `OrbitalInputError`; an unavailable or
   unstable tidal-basis identity is `OrbitalTimeBasisError`.
6. Select the pinned Horizons GM snapshot from the bound identity. Not DE440
   or DE441: `OrbitalGravityModelError` in the new API; the legacy wrapper's
   compatibility policy is described below.
7. Fetch the state through the explicitly TDB-named capability at `epoch_tdb`,
   in km and km/day in ICRF, together with the
   exact serving-reader and segment receipt for every route leg:
   - **Sun:** planets through their route legs minus SSB→Sun; small bodies
     directly from their segment. Every small-body kernel in production is
     Sun-centered; a segment with any other center is chained through the
     planetary kernel inside `_orbital_state.py`.
    - **Earth (Moon only):** EMB→Moon minus EMB→Earth.
    - On a miss, check whether any reader has the body at any date before
      blaming the date: `OrbitalBodyNotLoadedError` versus
      `OrbitalCoverageError`.
    - If a state can be read but the serving route, source identity or exact
      coverage cannot be proven, the strict API raises
      `OrbitalSourceReceiptError` instead of fabricating provenance.
8. Rotate position and velocity into the frame.
9. Extract elements.
10. Return `OsculatingElements` with UT1, TT and TDB epochs and complete
    provenance.

### Body resolution

| Input | Resolves to |
|---|---|
| `"Mercury"`, `"Venus"` (any case) | planet body, NAIF 199 / 299 |
| `"Earth"` | planet body, NAIF 399 |
| `"Earth-Moon Barycenter"`, `"Earth Moon Barycenter"`, `"EMB"` | Earth–Moon barycenter, NAIF 3 |
| `"Moon"` | Moon, NAIF 301 |
| `"Mars"` … `"Pluto"` | planet system barycenter, NAIF 4–9 (as DE441 serves them) |
| asteroid or comet name, alias, or `asteroid:`/`comet:` qualified name | via `small_body_identity.resolve_small_body_identity` |
| `int` | the identity with that NAIF ID among the above |
| names Moira knows as non-orbital points (Sun, lunar nodes, Lilith variants, lots, Uranian hypotheticals, fixed stars), or NAIF IDs Moira does not serve (e.g. 599) | `OrbitalBodyNotSupportedError`, with the reason |
| anything else | `OrbitalBodyNotFoundError`, with close matches (`difflib`, deterministic) |

`bool` is not an admitted `int` body ID. Malformed body types raise
`OrbitalInputError`; a well-formed string or integer that resolves nowhere
raises `OrbitalBodyNotFoundError`.

### Center admissibility

| Body kind | Sun | Earth |
|---|---|---|
| Planet body, planet system barycenter, Earth–Moon barycenter | yes | no |
| Moon | no | yes |
| Asteroid, comet | yes | no |

## Gravity

### Primary source and frozen snapshot

`moira/_ephemeris_gm.py` holds the values needed by this design from JPL
Horizons' official `gm_Horizons.pck`, retrieved 2026-09-15. The source artifact
is mutable, so Moira pins its retrieval date, byte length (15,428) and SHA-256
`169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c`.
`PROVENANCE.md` records the URL and receipt. A live audit may report upstream
drift, but it never silently changes a released Moira gravity policy.

This is deliberately not described as the DE440 ASTRO-VALUES table. The JPL
artifact states that DE440/441 values are replaced by newer satellite-system
solutions where necessary to keep osculating-element conversion internally
consistent. The Horizons manual identifies this artifact as the mass-parameter
source used when converting state vectors to osculating elements.

| NAIF | Body | GM (km³/s²) |
|---|---|---|
| 10 | Sun | 132712440041.27942 |
| 1 | Mercury system | 22031.868551400003 |
| 2 | Venus system | 324858.592 |
| 3 | Earth–Moon system | 403503.2356254802 |
| 4 | Mars system | 42828.37442560939 |
| 5 | Jupiter system | 126712761.8414429 |
| 6 | Saturn system | 37940584.92052428 |
| 7 | Uranus system | 5794556.3999999985 |
| 8 | Neptune system | 6836531.640925204 |
| 9 | Pluto system | 975.4308664317557 |
| 199 | Mercury | 22031.868551400003 |
| 299 | Venus | 324858.592 |
| 399 | Earth | 398600.43550702266 |
| 301 | Moon | 4902.80011845755 |

### Rules

Every result records the rule, the GM used and its components.

| Center | Body | GM |
|---|---|---|
| Sun | planet body (199, 299, 399) | Sun + body |
| Sun | planet system barycenter (4–9) | Sun + system |
| Sun | Earth–Moon barycenter (3) | Sun + Earth–Moon system |
| Sun | asteroid, comet | Sun |
| Earth | Moon | Earth + Moon |

The frozen primary-source fixtures verify every row against the `Keplerian GM`
line returned by Horizons ELEMENTS. No value is inferred from an adjacent
ephemeris release and no systematic difference is admitted through a wider
numeric gate.

### Why solar-system-barycentric elements are deferred

The DE440/DE441 paper defines its solar-system barycenter using the Sun, eight
planetary-system barycenters, the Pluto-system barycenter, 343 asteroids, 30
KBOs and a KBO ring. It is therefore not represented by Sun + systems 1–9.
Official Horizons ELEMENTS probes also return different barycentric Keplerian
GMs for a massless small-body target, Earth and the Jupiter barycenter. The
results are compatible with a target-dependent barycentric reduction, but that
formula is an inference and is not adopted as doctrine without a public primary
source. A later design may admit this center using either a published rule or a
fully versioned JPL reference table with independently verified semantics.

### Admission by ephemeris identity

The pinned snapshot is admitted only when the pool's planetary kernel identity
(`_EphemerisKernelIdentity.planetary_ephemeris`, derived from the SPK summary
label) is `DE440` or `DE441`. Any other identity, or an unidentified planetary
reader, raises `OrbitalGravityModelError` from the new API. This follows the
precedent in `spk_reader` for admitting lunar tidal terms: no adjacent release
is inferred from numerical or naming similarity. The old wrapper uses a frozen
legacy gravity policy for readers it accepted before this change, as specified
under Compatibility; that path does not claim Horizons parity.

A standalone sovereign small-body reader is admitted only when its verified
manifest records the planetary ephemeris used to generate/integrate that
release and that identity is DE440 or DE441. A filename, target-state residual
or current machine configuration cannot supply this missing fact. Existing
manifests that lack it must be revised through their own provenance process or
used behind a pool that supplies the admitted planetary identity.

## Frames

| Frame | Construction |
|---|---|
| `J2000_ECLIPTIC` | ICRF axes rotated about x by the Horizons-documented IAU76/80 J2000 obliquity 84381.448″, with no frame bias. This is the fixed ecliptic in which JPL publishes asteroid/comet elements. |
| `MEAN_ECLIPTIC_OF_DATE` | The closed TT interval from Julian epoch 1900.0 through 2100.0 (`JD 2415020.0` through `2488070.0`) uses the IAU SOFA `Ecm06` ICRS-to-ecliptic matrix. Outside that interval, use SOFA `Ltecm`, the Vondrák long-term ICRS-to-ecliptic matrix. Both routines already own frame bias. |
| `TRUE_ECLIPTIC_OF_DATE` | Supported only on that same closed TT interval. Let `epsa = iauObl06(TT)` and `(dpsi, deps) = iauNut06a(TT)`; obtain the bias-precession-nutation matrix `rnpb = iauPnm06a(TT)`, then form `Rx(epsa + deps) * rnpb` in SOFA's rotation convention. Outside the closed interval, raise `OrbitalFrameUnavailableError`. |

- IAU SOFA Issue 2023-10-11 is the primary validation oracle. A locally
  compiled copy of that exact source produces the frozen validation values;
  no derivative implementation is treated as authority. Stage 1 proves every
  matrix against the corresponding pinned SOFA routine or the explicit
  composition above.
- The 1900.0/2100.0 router is explicit because SOFA states that the Vondrák
  long-term model remains within 100 microarcseconds of IAU 2006 during the
  20th and 21st centuries. Switch-boundary tests enforce continuity before the
  mean-frame routing is admitted. SOFA documents the Vondrák model over
  +/-200,000 years, which contains the complete DE440/DE441 span.
- There is no corresponding primary long-term nutation model in the admitted
  source set. SOFA's `iauNut06a` components are explicitly relative to the IAU
  2006 mean equinox and ecliptic, and `iauNumat` requires a consistent mean
  obliquity. Combining them with the Vondrák long-term triad would be an
  unvalidated hybrid. The true frame therefore fails explicitly outside
  1900.0–2100.0; callers needing the long span request
  `MEAN_ECLIPTIC_OF_DATE`.
- Horizons' ecliptic-of-date is not a validation oracle for either Moira date
  frame: the Horizons manual specifies IAU76/80 in the modern interval and
  Owen outside it. Only `J2000_ECLIPTIC` is compared directly with Horizons
  ELEMENTS.
- The current chart stack is not copied. On its IAU route, an explicit
  `apply_frame_bias` precedes a `Pmat06`-equivalent matrix and duplicates bias.
  On its long-term route, the current `Ltp`-equivalent matrix does not include
  bias, so the same explicit operation is required. Stage 1 either makes the
  router return `Pmat06`/`Ltpb`-equivalent bias-inclusive matrices and removes
  every external bias at inventoried consumers, or keeps route-specific bias
  assembly. Mixing those two repairs is forbidden.
- Position and velocity are rotated by the same instantaneous orthogonal
  matrix only. The derivative of a moving coordinate frame is deliberately
  excluded: osculating elements describe one inertial state expressed in
  different axes, not motion in a non-inertial frame.
- Consequently only inclination, node, argument of pericenter and the
  longitudes derived from them change between frames. Semi-major axis,
  eccentricity, pericenter and apocenter distances, anomalies, mean motion,
  period and time of pericenter are identical in every frame.
- At J2000.0, `MEAN_ECLIPTIC_OF_DATE` and `J2000_ECLIPTIC` differ by about
  0.042″ because the former contains ICRS frame bias and the IAU 2006
  84381.406″ obliquity while the latter uses the Horizons 84381.448″ fixed
  obliquity without bias. `TRUE_ECLIPTIC_OF_DATE` also includes IAU 2000A
  nutation. These are intended differences, not a parity residual.
- Provenance records the exact matrix routine/model, router branch and declared
  TT support interval. A result assembled with `Ltecm` is never labelled
  simply `IAU_2006`.

## Time

- Input stays `jd_ut` (UT1) for compatibility.
- `epoch_tt` comes from `_ut1_to_ephemeris_tt(jd_ut, reader)` and is used by
  precession, nutation and obliquity models.
- `epoch_tdb` is the epoch passed to the new internal TDB reader capability.
  SPICE defines ephemeris time as TDB; TT is never passed to that capability
  while being labelled TDB.
- The governing conversion is the NAIF LSK relation
  `TDB - TT = K sin(E)`, `E = M + EB sin(M)`,
  `M = M0 + M1*t`, where `t` is TDB seconds from J2000. Stage 1 pins the
  `naif0012.tls` constants (`K=1.657e-3 s`, `EB=1.671e-2`,
  `M0=6.239996 rad`, `M1=1.99096871e-7 rad/s`) and solves the implicit TDB
  argument to a fixed point. TDB→TT is the inverse of the same policy.
- This is the operational SPICE model, which NAIF documents as omitting small
  periodic terms and being accurate to about 30 µs. It is not relabelled as the
  fuller SOFA Fairhead-Bretagnon model. Stage 1 validates its implementation
  against frozen outputs from the pinned NAIF equations and separately records
  the model difference from geocentric SOFA `Dtdb` over 1950-01-01 through
  2050-12-31. The latter gate is 50 µs and is not extrapolated beyond SOFA's
  published 1950–2050 accuracy statement.
- Results record `jd_ut`, `epoch_tt`, `epoch_tdb`, `delta_t_seconds`,
  `tdb_minus_tt_seconds`, the Delta-T source/basis receipt, and the TT/TDB
  converter policy/version/source hash. The offset is computed before adding
  two single-part Julian dates so its sub-millisecond evidence is not lost to
  binary64 JD resolution; epoch round-trip tests include the explicit ULP
  budget of the public single-float representation.
- The public `KernelReader.position`, `position_and_velocity` and
  `has_segment_at` methods retain their documented TT input contract. Built-in
  readers convert that TT argument once with the pinned converter and delegate
  to private `*_tdb` operations. Their legacy `coverage()` returns the same
  one-span-per-pair shape in TT; the strict core instead uses exact disjoint
  `coverage_intervals_tdb`. This avoids both a silent protocol reinterpretation
  and a TT value being evaluated as though it were TDB.
- The public `SpkReader.evaluator` and `KernelPool.evaluator` interval arguments
  and returned evaluator remain TT-facing. Their adapter converts interval
  endpoints for TDB segment selection and converts each evaluation epoch once;
  a private `evaluator_tdb` surface is raw TDB. Native and Python consumers are
  included in the same parity and shift audit.
- Kernel and segment coverage endpoints are TDB. Calendar renderings are
  secondary display values and always carry their time scale.
- **Time of pericenter** is an element of the osculating conic, computed in
  TDB. Results expose both `time_of_pericenter_tdb` and its converted
  `time_of_pericenter_tt`. It can lie far outside kernel coverage (thousands of
  years for Sedna) and is documented as an analytic conic value, not an
  ephemeris event.
- For an elliptic orbit, Moira follows the branch observed in Horizons: the
  nearest osculating periapsis. With displayed mean anomaly normalized to
  `[0, 360)`, computation wraps `M_signed` into `(-180, 180]` and uses
  `Tp = epoch_tdb - M_signed / n`. An exact 180° tie selects the previous
  passage and is frozen by test. Hyperbolic and parabolic trajectories have
  their unique signed conic passage.
- **Pericenter passages** are events found on the actual trajectory by
  `apsidal_passages`; their search and returned event epochs never leave the
  exact contiguous TDB coverage shared by every state-route leg.
- A found passage's `epoch_tt` is obtained with the inverse of the pinned
  TT/TDB policy. Its `jd_ut` is then obtained by
  `_ephemeris_tt_to_ut1(epoch_tt, bound_reader)` on the same route-plan
  identity, and a forward UT1->TT check must close within the declared
  binary64 budget. Failure to bind or invert that clock surface raises
  `OrbitalTimeBasisError`; no event is returned with a guessed UT label.

## Orbit shapes and element extraction

### Shape

| Condition | Shape |
|---|---|
| `e < 1 − PARABOLIC_E_TOL` | elliptic |
| `abs(e − 1) ≤ PARABOLIC_E_TOL` | parabolic |
| `e > 1 + PARABOLIC_E_TOL` | hyperbolic |

`PARABOLIC_E_TOL`, `CIRCULAR_E_TOL` and `EQUATORIAL_SIN_I_TOL` are separate,
dimensionless constants. The spike proposes `1e-10` for each; Stage 1 measures
their numerical floor on calibration states and freezes the accepted values
before the holdout corpus runs. Rectilinear and zero-state checks do not compare
the dimensional magnitude `|h|` with one of these constants. They use a
documented dimensionless metric such as `|h| / (|r| |v|)`, with explicit zero
position and zero velocity checks.

### Extraction

The state boundary is km and km/day, while the pinned GMs are km³/s².
Extraction converts velocity exactly once to km/s and thereafter uses
`r` in km, `v` in km/s and `mu` in km³/s². Durations produced in seconds are
converted to days only at the result boundary. The passage search separately
uses its native km/day velocity and names it `v_day`; the two unit systems are
never mixed.

- `h = r × v`; eccentricity vector `((|v|² − μ/|r|) r − (r·v) v) / μ`.
- Pericenter distance `q = |h|² / (μ (1 + e))`, accurate at every
  eccentricity. Semi-major axis `a = q / (1 − e)` only when not parabolic.
  Today's code derives `a` from orbital energy, which fails near `e = 1`.
- Inclination `atan2(sqrt(h_x² + h_y²), h_z)`; node `atan2(h_x, −h_y)`.
- Argument of pericenter and true anomaly from the node, eccentricity vector
  and position with `atan2` forms.
- `mean_anomaly_deg` uses `E − e sin E` for an ellipse and
  `e sinh(H) − H` for a hyperbola. The elliptic value is normalized for
  display; the hyperbolic value is signed and unbounded, matching Horizons'
  single `MA` concept rather than inventing a second public field.
- Time of pericenter has one frozen branch per numerical shape. For an ellipse,
  compute `sin(E) = dot(r,v) / (e sqrt(mu a))`,
  `cos(E) = (1 - |r|/a) / e` and signed `E = atan2(sin(E), cos(E))`, then
  signed `M = E - e sin(E)`. For a hyperbola, obtain signed `H` from
  `sinh(H) = dot(r,v) / (e sqrt(-mu a))`. For the parabolic branch, use
  `D = dot(r,v) / sqrt(2 mu q)` and Barker's
  `epoch_tdb - Tp = sqrt(2 q^3 / mu) (D + D^3/3)`. These expressions, their
  unit conversions and their near-branch numerical conditioning are tested
  against closed forms and Horizons `Tp` for NEOWISE, Hale–Bopp and
  'Oumuamua. There is no unresolved "universal functions or Barker" choice.
- Mean motion starts as `sqrt(μ / |a|³)` in rad/s and is converted explicitly
  to degrees/day (ellipse and hyperbola); period is `2π/n` converted to days
  (ellipse); apocenter distance is `a (1 + e)` (ellipse).
- Direction angles are normalized to `[0, 360)`. Elliptic mean anomaly is
  displayed in `[0, 360)` but is signed only for the `Tp` branch computation.
  Hyperbolic mean anomaly is signed and unbounded. Every field's range and unit
  is part of its public docstring and REST schema.

### Elements by shape

`None` means not defined. There are no placeholder numbers.

| Element | Ellipse | Parabola | Hyperbola |
|---|---|---|---|
| `eccentricity`, `pericenter_distance_au`, `inclination_deg` | yes | yes | yes |
| `true_anomaly_deg`, `time_of_pericenter_tdb`, `time_of_pericenter_tt` | yes | yes | yes |
| `semi_major_axis_au` | yes | — | yes, negative |
| `mean_motion_deg_per_day` | yes | — | yes |
| `mean_anomaly_deg` | yes, `[0, 360)` display | — | yes, signed and unbounded |
| `orbital_period_days`, `apocenter_distance_au` | yes | — | — |

### Undefined angles

| Condition | Undefined | Still defined |
|---|---|---|
| `abs(sin i) < EQUATORIAL_SIN_I_TOL` (equatorial, prograde or retrograde) | `lon_ascending_node_deg`, `arg_pericenter_deg`, `arg_latitude_deg` | conventional planar `lon_pericenter_deg` from the eccentricity vector, `true_longitude_deg`, pericenter-vector longitude/latitude |
| `e < CIRCULAR_E_TOL` (circular ellipse) | `arg_pericenter_deg`, `true_anomaly_deg`, `mean_anomaly_deg`, both time-of-pericenter fields, `lon_pericenter_deg`, both pericenter-vector direction fields | `arg_latitude_deg`, `true_longitude_deg`, conventional `mean_longitude_deg` |
| both | union of the two undefined sets | true longitude, conventional mean longitude |

Shape-specific undefined fields are also explicit: a parabolic result marks
`semi_major_axis_au`, `mean_motion_deg_per_day`, `mean_anomaly_deg`,
`orbital_period_days`, `apocenter_distance_au` and `mean_longitude_deg` with
reason `PARABOLIC`; a hyperbolic result marks `orbital_period_days`,
`apocenter_distance_au` and `mean_longitude_deg` with reason `HYPERBOLIC`.
The measured eccentricity is never snapped to 1.0 merely because it selected
the numerical parabolic branch; provenance carries `PARABOLIC_E_TOL`.

- `undefined` lists each undefined field with
  `reasons: tuple[UndefinedElementReason, ...]`. Reasons are deduplicated and
  ordered `CIRCULAR`, `EQUATORIAL`, `PARABOLIC`, `HYPERBOLIC`, so simultaneous
  singularities remain visible and deterministic.
- `lon_pericenter_deg` is `Ω + ω` (a dogleg angle for inclined orbits), taken
  directly from the eccentricity vector when the node is undefined.
- `pericenter_ecliptic_lon_deg` and `pericenter_ecliptic_lat_deg` give the
  direction of the pericenter vector in the frame. This is unambiguous at any
  inclination and is what apsidal longitudes should use.
- For an exactly retrograde-equatorial orbit, the node remains undefined and
  the planar `lon_pericenter_deg` convention is the longitude of the
  eccentricity vector. It is not presented as a limiting value of `Ω + ω`.
- `true_longitude_deg` is `Ω + ω + ν`, with fallbacks from the position vector
  when node or pericenter is undefined.
- `mean_longitude_deg` is `ϖ + M` for ellipses (equal to the true longitude
  for circular orbits).
- Earth illustrates the need: in the J2000 ecliptic its node moves 135° → 180°
  → 346° and its argument of perihelion 327° → 281° → 116° across 2000, 2026
  and 1900, while its longitude of perihelion stays between 100° and 102°.

## State-route and coverage capability

The existing `KernelReader` numeric protocol remains source-compatible and
keeps its TT-labelled public methods. Stage 1 adds a private capability used by
the built-in readers and `_orbital_state.py`; it is not added as a structural
requirement to `KernelReader`:

- `OrbitalStateRoute` carries the ICRF position and velocity at `epoch_tdb` and
  an ordered tuple of `OrbitalStateLeg` records.
- `OrbitalStateRoutePlan` binds the selected readers, segment-precedence rule,
  center chain, ordered serving-segment schedule and exact common coverage
  before a multi-epoch computation. A plan may name several segments from one
  reader across adjacent intervals; it may not introduce a reader or segment
  that was absent from the frozen schedule. Evaluating it returns
  `OrbitalStateRoute` values whose leg identities match the applicable schedule
  entries.
- The plan owns an immutable pool-order/generation snapshot and a read lease
  for the lifetime of the single-epoch call or multi-epoch search. `add` cannot
  alter an existing plan, and `close` is serialized until its active leases are
  released. Planetary clock identity, gravity selection and every state leg are
  derived from that one snapshot; none independently re-reads mutable pool
  order.
- Each leg records center and target NAIF IDs, stable kernel label, the serving
  kernel/shard SHA-256 (or an immutable manifest digest that resolves to those
  exact bytes), segment type, exact inclusive TDB interval, and the selected
  reader's deterministic pool index. A label without a content identity is not
  a strict source receipt.
- A sovereign small-body leg also records `catalog_id`, `catalog_version`,
  manifest SHA-256, release timestamp and whether coverage is restricted to an
  observed arc. Manifest paths and release directories remain internal.
- Coverage is a sorted tuple of disjoint, non-overlapping closed TDB intervals.
  It is never collapsed to `(minimum_start, maximum_end)` across a gap.
- The coverage of a chained state is the interval intersection of every route
  leg. The passage search uses only the one contiguous intersection containing
  its start epoch and never steps across a gap.
- Source selection and the receipt are one atomic operation. Looking up a state
  and later guessing which pooled reader served it is forbidden.
- Reader/release hashes are verified and cached when the source is opened or
  its manifest is admitted. A public orbital call never re-hashes an 18 GB
  release or exposes the local cache path.

The new private operations and exact interval capability use explicit
`epoch_tdb`/`*_tdb` names and TDB docstrings. Existing public `jd` parameter
names, signatures and TT contract remain unchanged; the built-in adapter
conversion and its small measured output shift are recorded in the changelog.
An implementation must not "fix" the ambiguity by relabelling the old methods
without conversion.

The private boundary is capability-checked, not added to the runtime-checkable
public protocol. Built-in readers expose direct/reverse state evaluation at an
explicit `epoch_tdb`, `coverage_intervals_tdb(center, target)` returning every
closed segment interval, and a stable segment/source receipt. `KernelPool`
additionally exposes TDB-named planetary-identity selection, atomic routed
state-with-receipt evaluation and route-plan construction for an interval.
There is no fallback from this strict boundary to the old TT methods: absence
of any required capability is `OrbitalSourceReceiptError`.

`SpkReader.evaluator()` and `KernelPool.evaluator()` are part of the same clock
boundary even though they are not members of `KernelReader`. Their public
`jd_tt`/`jd_end_tt` contract stays TT, segment selection converts both endpoints
to TDB, and the returned evaluator converts each TT evaluation argument exactly
once before delegating to the raw SPK evaluator. A private, explicitly named
TDB evaluator capability is the only route that returns the raw evaluator.
Stage 1 inventories and measures every current evaluator consumer, including
the native eclipse and fixed-star searches; it may not leave the two evaluator
paths with different epoch semantics.

`KernelPool.position_and_velocity` gains the same deterministic center-chain
semantics as `position`. A new internal
`position_and_velocity_tdb_with_receipt` operation performs that routing and
returns `OrbitalStateRoute` atomically; the existing TT numeric method converts
once, delegates to it and discards the receipt. Direct, reverse and chained
paths are frozen by tests. The current unchained velocity behavior is therefore
fixed in Stage 1, not left as a follow-up.

Passage search calls a companion route-planning operation once. It does not
re-run pool priority independently at each sample. A bracket never straddles a
scheduled segment seam: sampling lands at the seam and begins the next bracket
on the other side. A candidate exactly on a seam is found only when two-sided
position/velocity evaluations meet a predeclared continuity gate and establish
the same extremum; otherwise the outcome records the seam as the plan edge. If
no single deterministic plan covers the requested direction, the first plan
edge is the coverage edge. The search does not splice kernels merely because
their union appears continuous. A future cross-kernel seam policy requires its
own continuity evidence and versioned route receipt.

## Results

All vessels are frozen dataclasses with slots and follow the engine's
docstring governance.

### Enums (`str, Enum`)

| Enum | Members |
|---|---|
| `OrbitalCenter` | `SUN`, `EARTH` |
| `OrbitalFrame` | `J2000_ECLIPTIC`, `MEAN_ECLIPTIC_OF_DATE`, `TRUE_ECLIPTIC_OF_DATE` |
| `OrbitShape` | `ELLIPTIC`, `PARABOLIC`, `HYPERBOLIC` |
| `OrbitalBodyKind` | `PLANET_BODY`, `PLANET_SYSTEM_BARYCENTER`, `EARTH_MOON_BARYCENTER`, `MOON`, `ASTEROID`, `COMET` |
| `UndefinedElementReason` | `EQUATORIAL`, `CIRCULAR`, `PARABOLIC`, `HYPERBOLIC` |
| `ApsidalDirection` | `NEXT`, `PREVIOUS` |
| `ApsidalPassageStatus` | `FOUND`, `BEYOND_COVERAGE`, `NOT_IN_WINDOW` |
| `OrbitClassCode` (stage 5) | `IEO`, `ATE`, `APO`, `AMO`, `MCA`, `IMB`, `MBA`, `OMB`, `TJN`, `AST`, `CEN`, `TNO`, `PAA`, `HYA` |

### `OsculatingElements`

| Group | Fields |
|---|---|
| Identity | `body: OrbitalBodyIdentity` (`name`, `kind`, `naif_id`) |
| Request | `center`, `frame`, `jd_ut`, `epoch_tt`, `epoch_tdb`, `delta_t_seconds`, `tdb_minus_tt_seconds` |
| Shape | `shape` |
| Elements | the fields in "Elements by shape" |
| Longitudes | `lon_ascending_node_deg`, `arg_pericenter_deg`, `lon_pericenter_deg`, `arg_latitude_deg`, `true_longitude_deg`, `mean_longitude_deg`, `pericenter_ecliptic_lon_deg`, `pericenter_ecliptic_lat_deg` |
| Undefined | `undefined: tuple[UndefinedElement, ...]` (`field`, `reasons`) |
| Provenance | `provenance: OsculatingElementsProvenance` |

`OsculatingElementsProvenance`:

| Field | Content |
|---|---|
| `state_source: OrbitalStateSource` | stable kernel/release identities and hashes, segment center and target, exact route legs; no absolute paths |
| `gravity: OrbitalGravity` | rule name, GM in km³/s², component NAIF IDs, pinned source URL/retrieval date/SHA-256, planetary ephemeris identity |
| `frame_construction` | frame enum, exact matrix routine, router branch and selected precession/obliquity/nutation model labels |
| `frame_model_interval_tt` | exact closed TT interval Moira admits for the selected SOFA construction (`Ecm06`/modern true: JD 2415020.0–2488070.0; `Ltecm`: Julian epochs -200000.0 through +200000.0, converted by SOFA's Julian-epoch definition); `None` only for the fixed J2000 frame. The separately recorded router branch says which portion selected that construction. |
| `time_conversion` | ΔT policy/source/basis, TT→TDB policy/version/source hash and numeric offsets |
| `singularity_thresholds` | named dimensionless thresholds and degenerate-state metric/version |

### `ApsidalPassages` (stage 2)

| Field | Content |
|---|---|
| `body` (`OrbitalBodyIdentity`), `center`, `direction`, `jd_ut`, `start_epoch_tt`, `start_epoch_tdb` | request |
| `pericenter`, `apocenter` | `ApsidalPassageOutcome` |
| `provenance` | algorithm version, sampling constants, refinement tolerance, extremum semantics, search-window source, frozen route-plan identity and ordered segment schedule, each route/segment schedule entry actually used with its evaluation count, seam continuity evidence, exact contiguous TDB interval searched and total evaluation count |

`ApsidalPassageOutcome`: `status`, `epoch_tdb`, `epoch_tt`, `jd_ut`,
`distance_au`, `coverage_edge_tdb`, `detail`. The four event-value fields are
all set only for `FOUND`; `coverage_edge_tdb` is set only for
`BEYOND_COVERAGE`; all inapplicable fields are `None`. `jd_ut` is the verified
inverse-clock coordinate described in Time, not a relabelled TT/TDB value.

### `OrbitClassResult` and batch vessels (stage 5)

| Vessel | Fields |
|---|---|
| `OrbitClassPredicate` | `code`, ordered conditions with parameter/unit/operator/boundary, `matched` |
| `OrbitClassResult` | body identity, `epoch_tdb`, source `OsculatingElements`, class `code`, JPL title, `classification_policy`, ordered evaluated predicates, structured boundary margins |
| `OrbitalErrorReceipt` | stable `error_code`, public message, and a key-sorted tuple of allowlisted JSON-scalar/JSON-array detail entries derived from documented orbital error attributes; no traceback, local path or arbitrary `repr` |
| `OrbitClassBatchItem` | `input_index`, original `input_body`, exactly one of `result` or `error` |
| `OrbitClassBatchResult` | request epoch/time receipt and ordered tuple of items |

## Public API

```python
def osculating_elements(
    body: str | int,
    jd_ut: float,
    *,
    center: OrbitalCenter,
    frame: OrbitalFrame,
    reader: KernelReader | None = None,
) -> OsculatingElements: ...

def apsidal_passages(            # stage 2
    body: str | int,
    jd_ut: float,
    *,
    center: OrbitalCenter,
    direction: ApsidalDirection,
    max_days: float | None = None,
    reader: KernelReader | None = None,
) -> ApsidalPassages: ...

def orbit_class(                 # stage 5, asteroids only
    body: str | int,
    jd_ut: float,
    *,
    reader: KernelReader | None = None,
) -> OrbitClassResult: ...

def orbit_classes_at(            # stage 5
    bodies: Sequence[str | int],
    jd_ut: float,
    *,
    reader: KernelReader | None = None,
) -> OrbitClassBatchResult: ...
```

- `center`, `frame` and `direction` are required keywords with no defaults,
  following the engine's law of policy explicitness.
- Facade: `Moira.osculating_elements(body, jd_ut, *, center, frame)` and
  (stage 2) `Moira.apsidal_passages(...)`, passing `reader=self._reader`, in
  the style of `Moira.phenomena`.
- Exports from `moira`, `moira.facade` and `moira.predictive`; the API-surface
  audit test lists every new name.
- `OrbitClassBatchResult.items` preserves input order and duplicates. Each
  `OrbitClassBatchItem` carries `input_index`, `input_body` and exactly one of
  `result` or a serializable `OrbitalErrorReceipt`; one unavailable body does
  not erase successfully classified neighbors. Request-level failures such as
  an invalid epoch still raise normally. The input echo is verbatim only for a
  string, a non-Boolean integer or a Boolean rejected as such; any other runtime
  object is represented by its fully qualified type name, never its `repr`.
- `orbit_class` obtains its frame-invariant classification inputs from a
  canonical `center=SUN`, `frame=J2000_ECLIPTIC` element result; the embedded
  `OsculatingElements` makes that choice visible.
- `OrbitalErrorReceipt` serializes only an explicit allowlist per error class:
  enums become their string values; finite numbers, strings, booleans and
  `None` remain JSON scalars; non-finite numeric inputs become the strings
  `"NaN"`, `"Infinity"` or `"-Infinity"`; tuples become arrays; and an
  unsupported input object is represented only by its fully qualified type
  name. User-controlled `repr`, exception `args`, filesystem paths and chained
  exception text are never copied into a batch receipt.

### Apsidal passages (stage 2)

- The search starts at `start_epoch_tdb` and is inclusive: a candidate within
  the published time/root tolerances of the start is the next or previous event
  only when guard evaluations on both sides establish its extremum type. Guard
  evaluations may lie just behind the directional start or just beyond an
  explicit `max_days` endpoint, but the returned event may not; every guard
  must remain inside the bound route plan's coverage. A candidate on a kernel
  coverage edge without a two-sided witness is not reported as found.
- The search interval is the intersection of `max_days`, when supplied, with
  the exact contiguous route-coverage interval containing the start. A finite
  `max_days` must be a positive real number other than `bool`; its endpoint and
  the kernel coverage endpoint are inclusive.
- With `max_days=None`, an elliptic start shape searches at most 1.5 starting
  osculating periods or to the coverage edge, whichever comes first. A
  parabolic or hyperbolic start shape searches to the coverage edge. These are
  search bounds only and do not assume the actual N-body trajectory follows the
  starting conic.
- Before sampling, the search binds one `OrbitalStateRoutePlan`. The sampled
  function is radial velocity
  `g(t) = dot(r(t), v_day(t)) / |r(t)|`. A negative-to-positive crossing is a
  local distance minimum; a positive-to-negative crossing is a local maximum.
- The initial sampling scale comes from the osculating orbit, but every step is
  capped by a fraction of the local radial timescale `|r| / |v|`, a fixed
  maximum step and the remaining search interval. The minimum step, maximum
  step, fractions and evaluation budget are named constants in an algorithm
  version; Stage 2 freezes them from calibration before running holdout tests.
  No step crosses a segment or coverage boundary.
- A sign change brackets one root. A safeguarded bracketed root solver refines
  it; distances immediately before and after the candidate independently
  confirm minimum versus maximum. Every admitted route supplies velocity, so
  Stage 2 has no derivative-free golden-section fallback and no second
  algorithm whose selection policy would be ambiguous.
- Meaning is unchanged from today's standard: the next or previous local
  minimum or maximum of distance. Documentation distinguishes the Moon-driven
  wobble of the Earth body from the smoother Earth–Moon-barycenter product;
  it does not publish an unmeasured passage-time offset.
- `NOT_IN_WINDOW` means that no qualifying, isolated, two-sided local extremum
  was established before the explicit or automatic limit. It does not claim
  that the trajectory has no extremum outside the searched interval. A
  constant-radius or numerically flat synthetic interval therefore returns
  `NOT_IN_WINDOW`, with `detail="NO_ISOLATED_EXTREMUM"`, rather than choosing
  an arbitrary sample as a passage.
- A start date outside coverage raises `OrbitalCoverageError`.
- Outcomes: `FOUND`; `BEYOND_COVERAGE` with the edge in the search direction;
  `NOT_IN_WINDOW` when an explicit `max_days` or the automatic 1.5-period
  elliptic bound ends first. The outcome detail and provenance distinguish
  `EXPLICIT_MAX_DAYS` from `AUTO_PERIOD`. If a window endpoint and a route-plan
  edge coincide within the published time tolerance, the route-plan edge wins:
  the result is `BEYOND_COVERAGE`, with detail distinguishing an ephemeris edge
  from an unadmitted source seam.
- An osculating hyperbolic or parabolic shape does not short-circuit the actual
  N-body trajectory search or assert that no future extremum can exist. Its
  analytic `apocenter_distance_au` remains `None`; an event search that reaches
  its boundary returns `BEYOND_COVERAGE` or `NOT_IN_WINDOW` honestly.
- Failure to converge or exhausting the fixed evaluation budget raises
  `OrbitalSearchError` with the optional bracket, algorithm version, evaluation
  count and final residual. Computational exhaustion is not misreported as a
  physical absence of an event.
- The migrated `phenomena.perihelion`/`aphelion` surface uses the only admitted
  center for each body: Earth for the Moon and Sun for every other admitted
  body. It does not silently expose a new center policy.

### Orbit class (stage 5)

Stage 5 is explicitly an **SBDB-style osculating asteroid classification** at
the requested epoch. It is not a claim that an instantaneous threshold test has
proved long-term resonance or dynamical membership. Comet subclasses are out
of scope because JPL's comet rules also require the Jupiter Tisserand parameter
or period doctrine; catalogued comets retain body kind `COMET` until a separate
design admits those rules.

`OrbitClassCode` contains `IEO`, `ATE`, `APO`, `AMO`, `MCA`, `IMB`, `MBA`,
`OMB`, `TJN`, `AST`, `CEN`, `TNO`, `PAA` and `HYA`. `OrbitClassResult` contains
the body identity, `epoch_tdb`, source `OsculatingElements`, code, JPL title,
the ordered predicates evaluated and `boundary_margins`.

- Numerical shape is evaluated first: `OrbitShape.PARABOLIC` maps to `PAA`
  and `OrbitShape.HYPERBOLIC` maps to `HYA`. This means Moira's disclosed
  `PARABOLIC_E_TOL` governs the finite-precision neighborhood around JPL's
  literal `e = 1` definition; the result receipt shows that predicate and its
  margin. This is tested as an intentional, bounded Moira numerical policy.
- Elliptic asteroids use this precedence, derived from the JPL predicates:
  `IEO`, `ATE`, `APO`, `AMO`, `MCA`, `IMB`, `MBA`, `OMB`, `TJN`, `CEN`,
  `TNO`, then fallback `AST`. `AST` cannot be evaluated where it appears in
  JPL's display table because it is a fallback and would otherwise swallow
  `CEN` and `TNO`.
- JPL's inequalities remain strict. A value exactly on an excluded boundary
  does not get silently nudged; it falls through to the next matching rule or
  `AST`, and a zero margin makes the boundary condition visible.
- `OrbitClassBoundaryMargin` is structured as parameter, value, operator,
  boundary, signed difference and unit. Margins in `a`, `q`, `Q` and `e` are
  not collapsed into one dimensionally meaningless scalar. `signed_difference`
  is positive on the admitted side, zero at the strict boundary and negative
  on the rejected side: `value - boundary` for a lower bound and
  `boundary - value` for an upper bound.
- The batch helper accepts an ordered iterable of bodies plus one epoch and
  returns results in input order. A failure is associated with its input; it
  does not silently remove an entry or reorder duplicates.
- Stage 5 freezes every predicate as data (code, parameter, operator, boundary
  and unit), then tests single-boundary, overlap and fall-through cases. The
  implementation may not infer precedence from enum order or documentation
  table order.

## Errors

### Rules

1. `OrbitalError(Exception)` is the base of every orbital error.
2. Each error also inherits the built-in or existing public error type callers
   catch today, so existing `except` blocks and REST handlers keep working.
3. Errors carry structured attributes; messages say what went wrong and what
   to do.
4. The core catches the inconsistent low-level errors (both
   `OutOfRangeError` classes, the small-body kernel's coverage `KeyError`, ΔT
   basis errors) and raises one consistent error with the original chained
   (`raise … from`).
5. Before blaming the date, the core checks whether any loaded kernel has the
   body at any date.
6. Invalid requests raise; a legitimate "no answer" is a returned outcome.
   Unusual orbit shapes are not errors.
7. `KeyError` subclasses override `__str__` so messages are not quoted.
8. `bool` is rejected explicitly wherever an integer or real number is
   accepted. Python's implicit `bool`-as-`int` relationship is never treated as
   a valid body ID, epoch or search window.
9. The class declarations, MRO, constructor signatures, `args`, attributes and
   pickle round trips are frozen by tests; cooperative `super()` is required.

### Classes

| Error | Raised when | Also inherits | Attributes |
|---|---|---|---|
| `OrbitalInputError` | non-finite or non-representable date; wrong type; unknown enum value for center, frame or direction; invalid `max_days` | `ValueError` | `parameter`, `value`, `allowed` |
| `OrbitalBodyNotFoundError` | name or NAIF ID in no catalog Moira knows | `KeyError` | `query`, `close_matches` |
| `OrbitalAmbiguousBodyError` | name exists as both asteroid and comet | `AmbiguousSmallBodyNameError` | `query`, `candidates` |
| `OrbitalBodyNotSupportedError` | the body has no orbit product (see Body resolution) | `ValueError` | `body`, `kind`, `reason` |
| `OrbitalCenterNotAllowedError` | invalid body/center pairing | `ValueError` | `body`, `center`, `allowed_centers` |
| `OrbitalFrameUnavailableError` | a valid frame has no admitted model at `epoch_tt` | `ValueError` | `frame`, `epoch_tt`, `supported_intervals_tt` |
| `OrbitalLegacyBodyNotAllowedError` | any known body outside a legacy planet-only wrapper's admitted list | `KeyError`, `ValueError` | `body`, `legacy_api`, `allowed_bodies`, `replacement_api` |
| `OrbitalBodyNotLoadedError` | catalogued, but no loaded kernel has the body | `KeyError` (as `asteroid_at`) | `body`, `naif_id`, `catalog`, `catalog_version`, `install_url` |
| `OrbitalCoverageError` | TDB epoch outside every exact common state-route interval | `spk_reader.OutOfRangeError` | `body`, `naif_id`, `requested_epoch_tdb`, `covered_intervals_tdb`, stable kernel/release labels, `coverage_restricted_to_observed_arc` |
| `OrbitalKernelMissingError` | no usable reader/source context | `MissingKernelError`, `MissingEphemerisKernelError` | `detail` |
| `OrbitalGravityModelError` | planetary kernel is not DE440 or DE441 | `RuntimeError` | `planetary_ephemeris`, `summary_label`, `admitted` |
| `OrbitalTimeBasisError` | ΔT cannot be bound to one admitted, stable ephemeris tidal basis, or a required TT/UT1 inverse does not close | `RuntimeError` | conversion direction, provisional/final identity labels, iteration count, source product, optional round-trip residual |
| `OrbitalSourceReceiptError` | a numeric state is available but its serving route, source identity or exact coverage cannot be established | `RuntimeError` | `center`, `target`, `reader_type`, `missing_capability` |
| `OrbitalStateDegenerateError` | zero position, zero velocity, or dimensionlessly rectilinear motion | `ValueError` | `condition`, `body`, `epoch_tdb`, `position_norm_km`, `velocity_norm_km_per_day`, normalized angular-momentum metric and threshold |
| `OrbitalSearchError` (stage 2) | refinement does not converge or the fixed evaluation budget is exhausted | `ArithmeticError` | optional `bracket_tdb`, `iterations`, `evaluations`, `tolerance_days`, optional `final_residual`, `algorithm_version` |
| `OrbitalPassageUnavailableError` (stage 2) | legacy `distance_extremes_at` cannot produce both required found events | `ValueError` | complete `passages`, ordered `missing_kinds` |

The declaration order is `class X(OrbitalError, CompatibilityBase)`. The
compatibility base is the type in the third column. Where two existing types
are required, `OrbitalKernelMissingError` uses `(OrbitalError,
MissingKernelError, MissingEphemerisKernelError)` and
`OrbitalLegacyBodyNotAllowedError` uses `(OrbitalError, KeyError, ValueError)`.
Stage 1 proves that each MRO is constructible before the hierarchy is admitted;
no dynamic base injection or exception wrapping by class-name string is
allowed.

`MissingEphemerisKernelError` moves from `moira/facade.py` to
`moira/spk_reader.py` beside `MissingKernelError` and stays re-exported from
`moira.facade` and `moira` under the same name. This removes the import cycle
that would otherwise prevent `OrbitalKernelMissingError` from inheriting it.
The old import path resolves to the identical class object. The module-path
change for newly pickled exceptions is listed in the changelog; old pickle
payloads naming `moira.facade.MissingEphemerisKernelError` remain loadable
through the re-export.

### Legacy wrapper behavior

| Case | Today | After |
|---|---|---|
| unknown name | `KeyError` | `OrbitalBodyNotFoundError` (`KeyError`) |
| any known asteroid, comet, Moon, EMB or non-planet other than Sun | `KeyError` or `ValueError` | `OrbitalLegacyBodyNotAllowedError` (`KeyError` and `ValueError`), message points to `osculating_elements` and its required center |
| Sun | `ValueError` | `OrbitalBodyNotSupportedError` (`ValueError`) |
| NaN or infinite date | `ValueError` | `OrbitalInputError` (`ValueError`) |
| `reader=None` | `AttributeError` | active reader context; `OrbitalKernelMissingError` if none |
| date outside DE441 | `OutOfRangeError` | `OrbitalCoverageError` (`OutOfRangeError`) naming the body and DE441's span |
| no passage found (stage 2) | `ValueError` | `OrbitalPassageUnavailableError` (`ValueError`) |

The only deliberate built-in exception-type change is `reader=None`. Changes
to epoch meaning, gravity values and newly rejected Boolean inputs are semantic
corrections and are listed separately in the changelog and migration note.

### REST mapping

Registered in `moira_server/errors.py`; the server matches handlers along the
exception's MRO, so these take priority over the generic `ValueError` and
`KeyError` handlers.

| Error | HTTP | `error_code` | `category` |
|---|---|---|---|
| `OrbitalInputError` | 422 | `invalid_parameter` | `input_validation` |
| `OrbitalBodyNotSupportedError` | 422 | `body_not_supported` | `input_validation` |
| `OrbitalCenterNotAllowedError` | 422 | `center_not_allowed` | `input_validation` |
| `OrbitalFrameUnavailableError` | 422 | `frame_outside_model_range` | `input_validation` |
| `OrbitalLegacyBodyNotAllowedError` | 422 | `body_not_allowed_in_legacy_api` | `input_validation` |
| `OrbitalAmbiguousBodyError` | 422 | `ambiguous_body` | `input_validation` |
| `OrbitalBodyNotFoundError` | 422 | `unknown_body` | `input_validation` |
| `OrbitalCoverageError` | 422 | `date_outside_ephemeris_coverage` (exact covered intervals in `details`) | `ephemeris_coverage` |
| `OrbitalBodyNotLoadedError` | 503 | `body_ephemeris_not_installed` | `ephemeris_availability` |
| `OrbitalKernelMissingError` | 503 | `kernel_not_ready` | `kernel_readiness` |
| `OrbitalGravityModelError` | 503 | `ephemeris_model_not_admitted` | `server_configuration` |
| `OrbitalTimeBasisError` | 503 | `time_basis_unavailable` | `server_configuration` |
| `OrbitalSourceReceiptError` | 503 | `ephemeris_source_receipt_unavailable` | `server_configuration` |
| `OrbitalStateDegenerateError`, `OrbitalSearchError` | 500 | `computation_failed` (logged with the request ID) | `computation` |
| `OrbitalPassageUnavailableError` | 422 | `passage_unavailable` | `orbital_event_availability` |

## Compatibility

- `orbital_elements_at(body, jd_ut, reader)` runs the core with
  `center=SUN`, `frame=J2000_ECLIPTIC`. It admits the planets it admits today
  (Mercury–Pluto and Earth), returns `KeplerianElements`, sets `epoch_jd` to
  TT and applies the pinned Horizons gravity rules for an admitted DE440/441
  reader. `reader` may be `None`.
- A reader accepted by today's wrapper but lacking an admitted DE440/441
  identity runs the same extraction core through a private
  `LEGACY_ORBITS_V1` gravity policy. This preserves source compatibility and
  does not claim Horizons parity. The new `osculating_elements` API remains
  strict and raises `OrbitalGravityModelError` for that reader.
- A third-party reader implementing only the frozen `KernelReader` protocol
  remains usable by the legacy wrappers. It is not required to grow private
  source-receipt methods. The strict API admits it only if it also exposes the
  new TDB route capability; otherwise it raises `OrbitalSourceReceiptError`.
- Built-in `KernelReader` TT methods preserve their signatures and input scale,
  but now convert TT to TDB before polynomial evaluation. That is a measured
  correctness change, not a source break or a relabelling. The exact TDB
  methods are private and used by the strict core.
- `distance_extremes_at` (stage 2) runs `apsidal_passages` with `center=SUN`,
  `direction=NEXT`, keeps its planet list, and reports TT times as the frozen
  `DistanceExtremes` field contract states. Its currently contradictory
  function-level UT1 wording is corrected in the same stage.
- `phenomena.perihelion` and `phenomena.aphelion` (stage 2) preserve the
  `PhenomenonEvent.jd_ut` name and UT1 meaning. They obtain that value from the
  core's verified TDB→TT→UT1 inverse; they never place a TT or TDB coordinate
  into the legacy `jd_ut` field.
- REST `/v1/orbits/elements` (stage 1) and `/v1/orbits/distance-extremes`
  (stage 2) keep `ADMITTED_ORBIT_BODIES`. `OrbitTimeResponse` gains
  `input_time_scale: "UT1_JD"`, `state_evaluation_scale: "TDB_JD"` and
  `output_time_scale: "TT_JD"`; provenance gains the time conversion,
  gravity rule, GM and source receipt.
- `_keplerian_from_state` and `_rot_eq_to_ecl` remain exact adapters: same
  import names, positional signature, accepted units and legacy result fields
  until the separately approved Shadbala correction removes that consumer.
  Given the same state they reproduce the old helper values. Stage 1 runs the
  complete existing Chesta Bala regression surface; any end-to-end numerical
  movement must be solely the measured shared TT→TDB reader correction and is
  frozen separately from the adapter test. Importability alone is not
  sufficient. The adapter is then removed only with the source-correct
  Shadbala change, not by this orbital implementation.

## Stages

Each stage is its own implementation plan, its own verified change and its
own completion receipt under AGENTS.md. Protected zones are declared before
editing in every stage.

| Stage | Scope | Protected zones | Consumer-visible change |
|---|---|---|---|
| 1 Elements | `_orbital_errors.py`, `_ephemeris_gm.py`, `_orbital_state.py`, `_orbital_frames.py`, public TT compatibility adapters (including evaluator wrappers) plus private TDB state/source/exact-coverage capabilities, pinned NAIF TT/TDB conversion, SOFA frame router and branch-aware single-bias correction, rewritten `orbits.py` elements API and vessels, legacy adapters, `MissingEphemerisKernelError` relocation, exports, facade method and frozen facade contract, REST `/v1/orbits/elements` time block and orbital error handlers, docs | `orbits.py`, `spk_reader.py`, `_spk_body_kernel.py`, `_ephemeris_time.py`, `julian.py`; the reader/evaluator and frame-transform inventories below; native evaluator bindings; `shadbala.py` compatibility, `facade.py`, `_facade_predictive.py`, `__init__.py`, `moira_server/`, catalogs/provenance, `wiki/03_validation/`, `PROVENANCE.md` | new functions; all built-in SPK evaluation receives TDB behind preserved TT-facing contracts; output epoch correctly TT; planet elements corrected (time, gravity); mean-date frame routes own bias exactly once; true-date requests outside JD(TT) 2415020.0–2488070.0 fail explicitly; every changed consumer is measured separately |
| 2 Passages | versioned passage search, `apsidal_passages`, `ApsidalPassages`, `distance_extremes_at` wrapper, `phenomena.perihelion/aphelion` on the core (any admitted body; still `PhenomenonEvent \| None`), REST `/v1/orbits/distance-extremes` time block | `orbits.py`, `phenomena.py`, `spk_reader.py`, `_spk_body_kernel.py`, `moira_server/` | passages for all admitted pairs; event evaluation TDB; `DistanceExtremes.*_jd` correctly TT while `PhenomenonEvent.jd_ut` remains verified UT1 |
| 3 Nodes | `planetary_nodes.geometric_node` on the core (Sun center, true ecliptic of date, gravity rules); `OrbitalNode` unchanged | `moira_server/` (nodes routes) | works for asteroids and comets; planet values shift slightly; the true-date model fails explicitly outside its 1900.0–2100.0 interval |
| 4 Shadbala (separate design required) | replace the current speed-ratio and apsidal shortcuts with the complete primary-text doctrine: Raman Chapter VI for the five non-luminaries and Chapter X §§136–137 for the Sun and Moon; remove `_sun_mandoccha_lon`, `_moon_mandoccha_lon` and private orbit-helper imports; correct every inapplicable "Ch. 9" citation | `shadbala.py` doctrine and public vessels, standards, tests, inspected primary-page receipt; `orbits.py` only for adapter removal | intentional Shadbala numerical/doctrinal correction; no apsidal input and no claim that an orbital-core migration preserves the old values |
| 5 Orbit class | asteroid-only `orbit_class(body, jd_ut, *, reader=None)` from Sun-centered elements; `OrbitClassResult`, codes, ordered predicates and structured boundary margins; `OrbitClassBatchResult` helper preserving every input | `orbits.py`, exports, SBDB fixture generator | new SBDB-style osculating asteroid classification; no comet subclass claim |
| 6 REST small bodies | admission of small bodies to `/v1/orbits/*` | `moira_server/` | separate design review |

Stage 1 is one release stage but three mandatory, separately reviewable and
separately revertible gates:

1. **1A — reader clock:** pure pinned TT<->TDB conversion, private TDB
   capabilities, public TT state/evaluator adapters, exact coverage and the
   complete reader-consumer parity/shift inventory.
2. **1B — frame ownership:** independent SOFA oracle fixtures, the new orbital
   frame router, and the protected chart-stack single-bias repair with a
   complete frame-consumer inventory.
3. **1C — orbital elements:** errors, GM policy, state routing, extraction,
   vessels, public/facade/REST surfaces, legacy adapters and documentation,
   built only after 1A and 1B are green.

Each gate has its own scoped test receipt. Stage 1 is complete, and 6.7.0 may be
tagged, only after the combined suite proves all three together; a later gate
may not weaken or replace evidence from an earlier gate.

The review-date protected call-site inventories are explicit starting points,
not substitutes for regenerating the search in the Stage 1 plan:

- Reader/evaluator calls: `_facade_classical.py`, `_spk_body_kernel.py`,
  `asteroids.py`, `comets.py`, `daf_writer_ui.py`, `draconic.py`, `eclipse.py`,
  `lunar_limb.py`, `mundane.py`, `nodes.py`, `orbits.py`, `phase.py`,
  `phenomena.py`, `planetary_nodes.py`, `planets.py`, `shadbala.py`,
  `spk_reader.py`, `stars.py`, and the native evaluator bindings.
- Frame-transform calls: `comets.py`, `coordinates.py`, `corrections.py`,
  `eclipse.py`, `eclipse_besselian.py`, `galactic.py`,
  `lunar_eclipse_global.py`, `lunar_limb.py`, `nodes.py`, `occultations.py`,
  `planetary_nodes.py`, `planets.py`, `precession.py`, and `sky/position.py`.

Exit criteria for every stage:

- the stage's unit tests and kernel-layer tests pass;
- the live layer has run, or its absence is recorded with the reason;
- the full-catalog layer has run where the catalogs are installed, or is
  recorded as not run;
- the wrapper compatibility matrix passes;
- `pytest -m "not external_network"` with `MOIRA_TEST_MODE=1`,
  `MOIRA_NO_DOWNLOAD=1` and `MOIRA_STRICT_KNOWN_ISSUES=1` shows no new
  failures;
- the documentation scripts have run;
- the AGENTS.md completion receipt is written.

Release: after Stage 1, `moira-astro` 6.7.0, then the guarded box pin (staging,
then production) and the Workspace engine contract, following the engine train
in `moira-state/ARCHITECTURE.md`. A release candidate may not use the local-skip
allowance: the live primary-source audit and inventory-wide asteroid and comet
catalog checks are mandatory release evidence. Later stages release as they
complete.

## Validation and tests

### Layers

| Layer | Runs | Authority | Content |
|---|---|---|---|
| 1 Math | everywhere; no kernels | synthetic closed forms; pinned NAIF LSK equations; pinned IAU SOFA matrices; disjoint frozen Horizons VECTORS + ELEMENTS calibration and holdout records at identical TDB instants | every asteroid class including PAA/HYA and every equality boundary; retrograde, high-inclination, near-circular, near-parabolic and unbound examples; every admitted gravity rule; exact circular, parabolic, 0°/180° inclination, simultaneous singularity and degenerate states; elliptic `Tp` branch edges; the exact modern true-ecliptic composition and explicit true-frame out-of-range result |
| 2 Kernel | anywhere with DE441 and the packaged 25-body catalog | frozen Horizons holdout ELEMENTS; NAIF segment descriptors; pinned SOFA and NAIF source artifacts | planets, Earth, Earth–Moon barycenter, Moon about Earth and all 25 packaged bodies; every admitted center; public TT adapters and exact TDB evaluation with no double conversion; direct/reverse/chained route receipts and frozen multi-segment route plans; disjoint coverage, gap, precedence, seam-continuity and frame-router boundaries; representative epochs inside actual coverage |
| 3 Full catalog | local skip allowed only when releases are absent; mandatory on the release host | sovereign manifest/release receipts and kernel segment descriptors; representative frozen Horizons holdout records | inventory-wide resolution, finite state, velocity, exact coverage, source receipt and element smoke checks for every installed asteroid and comet; detailed numeric checks for named representative comets, observed-arc asteroids, Hektor, Atira and each orbit-shape/class boundary |
| 4 Live | opt-in `external_network` in an isolated process; mandatory release audit | live JPL Horizons and JPL SBDB APIs | regenerates candidate fixtures, reports GM/source/API drift and compares them with the reviewed frozen corpus; never rewrites accepted fixtures automatically |

- Fixtures are keyed by TDB instants. Tests call the API with the UT that
  Moira's own ΔT policy maps to each instant, so ΔT modelling differences do
  not enter the comparison.
- Fixtures record query parameters, retrieval time, Horizons' center, frame
  and Keplerian GM lines, response SHA-256, API signature/version, and the orbit
  solution ID. When the kernel's manifest metadata records the solution it was
  built from, a mismatch is reported as data drift, not a code failure.
- SBDB label fixtures also record the exact SBDB element set and its osculation
  epoch. Direct label parity is asserted only by evaluating the published JPL
  predicates on that same element set. At any other requested epoch, Moira's
  result is compared with those predicates applied independently to Horizons
  elements at the identical TDB instant; it is not compared blindly with
  SBDB's current stored label.
- Generators: `scripts/build_orbital_elements_fixtures.py` and, in Stage 5,
  `scripts/build_sbdb_orbit_class_fixtures.py` (network, outside pytest). They
  write candidate artifacts; accepting or replacing a frozen fixture is a
  reviewed source-data change.

### Fixtures and test files

| File | Layer |
|---|---|
| `tests/fixtures/horizons_orbital_elements_calibration.json` | 1 calibration only |
| `tests/fixtures/horizons_orbital_elements_holdout.json` | 1 and 2 acceptance; no overlap with calibration |
| `tests/fixtures/horizons_orbital_elements_catalog_holdout.json` | 3 representative numeric acceptance |
| `tests/fixtures/horizons_apsidal_passages_reference.json` | stage 2 |
| `tests/fixtures/sbdb_orbit_classes.json` | stage 5 exact SBDB element sets, osculation epochs, source labels and response receipts |
| `tests/unit/test_orbital_extraction.py` | 1 and synthetic edge cases |
| `tests/unit/test_ephemeris_gm.py` | gravity table, rules, identity admission |
| `tests/unit/test_orbital_frames.py` | frozen SOFA `Ecm06` and `Ltecm` mean-frame values; frozen `Obl06` + `Nut06a` + `Pnm06a` true-frame composition; exact 1900.0/2100.0 routing and outside-range failure; frame invariants and route-specific no-double/no-missing-bias tests including the protected chart stack |
| `tests/unit/test_orbital_time_scales.py` | UT1→TT→TDB stable identity binding, pinned NAIF equations, SOFA 1950–2050 comparison, public-TT/private-TDB state and evaluator adapter behavior with exactly one conversion, labels, offsets, ULP budget, forward/inverse round trips and passage TDB→TT→UT1 reconstruction |
| `tests/unit/test_orbital_state_routes.py` | atomic receipts, direct/reverse/chained routing, frozen ordered multi-segment schedules, pool-generation snapshot/lease behavior under interleaved `add`/`close`, no unplanned fallback, exact seam behavior, continuity gates and disjoint interval intersection |
| `tests/unit/test_orbital_errors.py` | every error class and REST code, wrapper compatibility, `OrbitalLegacyBodyNotAllowedError` dual built-in compatibility, frame-range and source-capability failures, guard |
| `tests/integration/test_orbital_elements_kernels.py` | 2 |
| `tests/integration/test_orbital_elements_full_catalog.py` | 3 inventory-wide smoke plus representative numeric holdout |
| `tests/integration/test_horizons_orbits.py` (extended) | 4 |
| `tests/integration/test_sbdb_orbit_classes.py` | frozen SBDB same-element/same-epoch label parity, live primary-source drift audit and requested-date Horizons predicate parity |
| `tests/unit/test_orbital_elements.py`, `tests/unit/test_distance_extremes.py`, `tests/unit/test_shadbala.py`, `tests/server/test_server_orbits_routes.py`, `tests/unit/test_api_surface_adversarial_audit.py` (updated) | compatibility |

### In-house cross-checks

- **Frames:** matrices first agree independently with SOFA `Ecm06` or `Ltecm`
  for the mean frame and the specified `Obl06` + `Nut06a` + `Pnm06a`
  composition for the modern true frame; date-frame node and
  pericenter directions then equal J2000 directions rotated by the same
  matrix. Corrected chart-position functions are a compatibility witness, not
  the oracle. Frame-invariant elements remain identical across frames.
- **Moon:** over the admitted modern true-frame interval, the lunar apogee from
  the core (Moon about Earth) agrees with `nodes.true_lilith` within a
  predeclared compatibility gate. The residual from the legacy helper's rounded
  GM is recorded; this in-house comparison is not the frame or gravity oracle.
- **Earth versus barycenter:** a regression test records the 5.8° monthly
  swing of the Earth body's perihelion longitude against the barycenter's
  0.04°.
- **Legacy wrappers:** each planet result differs from the previous code only
  by the approved corrections, checked against the measured shifts.
- **Shadbala compatibility:** with frozen input states, the Stage 1 adapters
  reproduce the complete pre-Stage-1 Chesta Bala surface exactly. End-to-end
  tests separately admit only the measured shared TT→TDB reader shift. The
  later source-correction stage intentionally replaces those values under its
  own approved doctrine design.

### Apsidal passage validation (stage 2)

- Found passages against extrema refined from Horizons vectors: the eight
  planets plus the Pluto-system target; Earth versus the barycenter; Eros;
  Chiron; 1P/Halley in 2061; 2P/Encke; Sedna around 2076; Eris around 2257.
- Outcomes: Sedna's aphelion is `BEYOND_COVERAGE`; unbound and near-parabolic
  searches do not short-circuit from the starting osculating shape; `max_days`,
  exact-start inclusion, two-sided endpoint witnesses, fixed route identity,
  coverage endpoints, gaps and the evaluation budget are honored. Synthetic
  exact-seam extrema exercise both an admitted continuous seam and a rejected
  discontinuous seam; no bracket crosses either seam.

### Gates

- Gates are proposed from the calibration corpus by element and body/shape
  class, with an analytic floating-point floor and a documented model/data
  error budget. They are frozen before the disjoint holdout corpus runs. A
  holdout failure returns the design to investigation; its observation is not
  folded into a larger gate during the same change.
- A gate changes only with a new measurement recorded in the validation paper.
  AGENTS.md forbids loosening a tolerance to make a failing test pass.
- Expected from the spike: small-body eccentricity near 1e-8, angles near
  0.01″, semi-major axis within a few parts in 10⁸; planets with corrected
  gravity near 0.01 km (today's 1e-5 au gates tighten); the Moon's eccentricity
  near 1e-10. These are calibration expectations, not accepted gates until the
  measured budget is reviewed and the holdout remains untouched.

### Error tests

- Every class: trigger, exact MRO, built-in compatibility (`isinstance`),
  constructor/`args`, attributes, message, chained original and pickle round
  trip through every promised re-export. This explicitly proves
  `OrbitalLegacyBodyNotAllowedError` is both `KeyError` and `ValueError` and
  that frame-range, time-inversion and missing-private-capability failures keep
  their distinct public identities.
- Wrapper compatibility matrix: every row of the legacy behavior table.
- REST: status, `error_code`, `category` and `details` for every mapping.
- Guard: bad inputs, including Boolean IDs/epochs/windows, across every public
  orbital function; any exception that is not an `OrbitalError` fails the test.

### Verification commands (per AGENTS.md)

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m pytest <new and changed test files> -q
.\.venv\Scripts\python.exe -m pytest -m "not external_network"
.\.venv\Scripts\python.exe -m pytest -m "external_network" --run-external-network tests\integration\test_horizons_orbits.py tests\integration\test_sbdb_orbit_classes.py
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\ruff.exe check <changed files> --no-fix
```

Repository-wide ruff is an audit baseline in this repository, not a gate.

## Documentation

| Document | Change | Stage |
|---|---|---|
| `wiki/02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md` | rewritten: scope, bodies, centers, frames, gravity, time, shapes, undefined elements, errors, passage semantics, non-goals | 1, 2 |
| `wiki/03_validation/VALIDATION_ASTRONOMY.md` §5.6 | corpus, gates, measured residuals | 1, 2 |
| `wiki/02_standards/API_REFERENCE.md` | new functions, vessels, enums, errors | 1, 2, 5 |
| `wiki/02_services/REST_API_REFERENCE.md` | time block, error mapping | 1, 2 |
| `docs/architecture/P-GAP-03_ORBITAL_ELEMENTS_TRANSPORT_DESIGN.md` | UT1/TT/TDB time block, exact coverage intervals, stable source receipt, error mapping | 1, 2 |
| `PROVENANCE.md` | pinned Horizons GM snapshot, receipt, reader route/source receipt and TT/TDB conversion | 1 |
| `CHANGELOG.md` | Added, Changed (planet shifts listed), Fixed, Compatibility | every stage |
| `wiki/02_standards/PLANETARY_NODES_BACKEND_STANDARD.md` | geometric node on the core | 3 |
| Shadbala standard | replace the inapplicable Chapter 9/apsidal account with the inspected Chapter VI and Chapter X doctrine and receipt | separate stage 4 design |
| Phenomena docs | orbital-core passage migration and center rule | 2 |

After documentation changes: `scripts/check_doc_consistency.py`,
`scripts/sync_git_wiki.py` (regenerates `moira.wiki/`, which is never edited by
hand) and `scripts/build_website_docs_bundle.py`.

## Deferred work and stage-entry decisions

1. **Solar-system-barycentric elements.** They are outside this design and get
   a separate primary-source review. The evidence in the appendix is retained
   to prevent a later design from repeating the rejected Sun + systems 1–9
   approximation.
2. **Full-catalog release environment.** Layer 3 needs the comet release
   (306 MB) and asteroid release (18.4 GB). The Stage 1 plan names the machine
   and acquisition receipt; the run is mandatory before 6.7.0 is tagged.
3. **Shadbala correction.** The primary text has already disproved the current
   apsidal premise. In the inspected scan containing the thirteenth-edition
   preface, Chapter VI
   (pp. 64–79) supplies the five non-luminary construction, while Chapter X
   §§136–137 (pp. 101–103) gives a Sun rule based on sayana longitude plus 90°
   and a Moon rule based on Sun–Moon angular distance; both reduce the angle to
   180° and divide by three. Before Stage 4, preserve hashes of the actual page
   images, record the exact imprint, and write a Shadbala-specific design that
   covers every affected vessel, test and public citation. This orbital spec
   preserves the existing output only until that separately approved change.
4. **Follow-ups outside this spec.** Unify the two low-level
   `OutOfRangeError` classes beyond the orbital boundary; consolidate the two
   missing-kernel classes beyond the compatible relocation described here; and
   correct stale coverage claims in
   `wiki/01_doctrines/BEYOND_SWISS_EPHEMERIS.md` during catalog-expansion work.

## Appendix: evidence

### Spike, 2026-09-14

The packaged 25-body catalog, `SmallBodyKernel.position_and_velocity` (km and
km/day), rotation by the J2000 obliquity and `_keplerian_from_state` with the
Sun's GM, against Horizons ELEMENTS at 2026-09-14 TDB and J2000 TDB (50
comparisons).

| Element | Largest difference |
|---|---|
| eccentricity | 3.0e-9 (Asbolus) |
| inclination | 0.00014″ |
| node | 0.0017″ |
| argument of perihelion | 0.0017″ |
| mean anomaly | 0.021″ (Amor) |
| perihelion distance | 5.1 km (Varuna) |
| semi-major axis | 729 km (Sedna, 9e-9 relative) |

Orbit classes from Moira's elements matched classes from Horizons' elements in
50 of 50 cases, and JPL SBDB's labels for all 25 bodies.

### Orbit-class rules against JPL SBDB

- Up to 400 SBDB bodies per asteroid class (4,198 in total) classified from
  SBDB's own elements: all agree once the five boundary cases are evaluated at
  full precision (Anagolay q = 1.016868; three Mars-crossers with q ≈ 1.6656;
  2004 KV18 a = 30.09951).
- All 1,263 numbered TNOs and centaurs agree; observed centaur semi-major
  axes span 5.549–30.0995 au and TNOs start at 30.18 au.
- JPL's published boundaries: Atira Q < 0.983; Aten a < 1.0, Q > 0.983; Apollo
  a > 1.0, q < 1.017; Amor 1.017 < q < 1.3; Mars-crosser 1.3 < q < 1.666,
  a < 3.2; inner main belt a < 2.0, q > 1.666; main belt 2.0 < a < 3.2,
  q > 1.666; outer main belt 3.2 < a < 4.6; Jupiter Trojan 4.6 < a < 5.5,
  e < 0.3; otherwise AST; centaur 5.5 < a < 30.1 and TNO a > 30.1. All of
  these numbers, including CEN and TNO, are now explicit in JPL's official
  SBDB filter documentation.

### Admitted gravity conventions (live Horizons Keplerian GM, 2026-09-15)

Official ELEMENTS probes at JDTDB 2460000.5 returned:

| Target | Center | Horizons GM (km³/s²) | Pinned rule |
|---|---|---:|---|
| Mercury (199) | Sun | 132712462073.14793 | Sun + 199 |
| Earth (399) | Sun | 132712838641.71489 | Sun + 399 |
| Earth–Moon barycenter (3) | Sun | 132712843544.51501 | Sun + 3 |
| Jupiter barycenter (5) | Sun | 132839152803.12083 | Sun + 5 |
| Moon (301) | Earth | 403503.23562548013 | 399 + 301 |
| Ceres (massless small-body rule) | Sun | 132712440041.27939 | Sun |

The small differences in the final printed digits are Horizons text-output
precision, not gates for a different gravity model.

### Rejected barycentric approximation

At the same official epoch, Horizons returned 132890518820.19876 km³/s² for
Ceres about the SSB, 132889323022.47902 for Earth about the SSB, and
132510742886.05025 for the Jupiter barycenter about the SSB. This disproves one
shared `Sun + systems 1–9` rule for all targets.

The earlier spike nevertheless tried that approximation. Its residuals are
retained only as negative evidence; they are not accepted validation results:

| Body | Semi-major axis difference | Eccentricity difference |
|---|---|---|
| Ceres | 0.6 km | 1.3e-9 |
| Chiron | 4.0 km | 8.0e-10 |
| Eris | −2.9 km | −1.2e-9 |
| Sedna | 1,340.8 km | 2.6e-9 |

With the Sun's GM alone the differences were 655,719 km, 4,897,984 km,
5,400,795 km and 1,045,419,389 km. Neither approximation is admitted by this
design.

### Exploratory Sun-centered versus barycentric drift, 1950–2026

This diagnostic motivates future barycentric work but is not part of the
admitted API or its gates.

| Body | Sun-centered | Barycentric |
|---|---|---|
| Ceres | 0.005 au | 0.031 au |
| Eros | 0.000 au | 0.019 au |
| Chiron | 0.104 au | 0.007 au |
| Eris | 0.231 au | 0.000 au |
| Sedna | 45.0 au (505 → 550) | 0.016 au (506.44) |

### Moon about Earth against Horizons (J2000)

| Gravity | Eccentricity difference | Perigee longitude difference |
|---|---|---|
| Earth only (Shadbala today) | −9.57e-3 | +23,441.52″ (6.5°) |
| Earth + Moon | −9.6e-13 | 0.00″ |

### Earth body versus Earth–Moon barycenter (from 2026-09-14, 30 days, 3-day steps)

| Body | Longitude of perihelion range | Swing |
|---|---|---|
| Earth (399) | 100.144°–105.919° | 5.774° |
| Earth–Moon barycenter (3) | 103.025°–103.070° | 0.044° |

Earth's inclination to the J2000 ecliptic: 1.51″ (2000), 7.95″ (2026), 49.71″
(1900).

### Earlier planet-shift spike (J2000, Sun-centered)

| Planet | Semi-major axis shift using the former DE440 candidate | Existing code vs JPL |
|---|---:|---:|
| Mercury | −6.3 km | 6.3 km |
| Venus | −267.2 km | not measured |
| Earth | −465.2 km | 465.2 km |
| Jupiter | −115.0 km | 115.0 km |

These measurements predate the corrected pinned `gm_Horizons.pck` decision.
Stage 1 regenerates calibration and holdout evidence; this table is not a claim
about the final residual.

### Horizons elliptic `Tp` branch

For Earth about the Sun at JDTDB 2451545.0, official Horizons output gives
`MA = 358.6172562416435°` and `Tp = 2451546.403877782170`, a periapsis about
1.4 days after the epoch. This is the nearest branch obtained by treating the
displayed anomaly as a small negative signed angle, not the previous passage
implied by subtracting a positive 358.6°. It freezes the branch rule in the
Time section.

### Primary-source query receipt

The 2026-09-15 live probes used JPL's official Horizons API with
`EPHEM_TYPE=ELEMENTS`, `MAKE_EPHEM=YES`, `OBJ_DATA=NO`,
`REF_PLANE=ECLIPTIC`, `CSV_FORMAT=NO`, and an explicit `TLIST` interpreted as
JDTDB by the ELEMENTS product. Sun-centered probes used `CENTER=500@10`, the
lunar probe `CENTER=500@399`, and SSB diagnostics `CENTER=500@0`. Target
commands were `199`, `399`, `3`, `5`, `301`, and `1;` for Ceres. The accepted
fixture generator additionally sends `TIME_TYPE=TDB` explicitly and stores the
complete request and response digest.

The GM source receipt is the JPL artifact URL in Primary authorities, retrieved
2026-09-15, 15,428 bytes, SHA-256
`169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c`.
The same audit retrieved official NAIF `naif0012.tls` (5,257 bytes, SHA-256
`678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b`)
and official IAU SOFA `sofa_c-20231011.zip` (3,686,708 bytes, SHA-256
`375729d8c0a254fd27c55484de5c8b83cccef351e1ef19d9cf7f26f5485e5538`).

### Frame-bias audit

`precession.precession_matrix()` is `Pmat06`-equivalent only inside its current
`|T| <= 50`-century branch. Outside, it is `Ltp`-equivalent and therefore maps
from the J2000 mean equator/equinox rather than directly from ICRS. The current
planet date-frame path applies `apply_frame_bias()` before both branches. A
J2000 unit-x-vector probe showed that this duplicates bias on the `Pmat06`
branch by about 17.66 mas; the same operation is required by the current
`Ltp` branch.

The current ±50-century router is also not continuous at the precision claimed
in its docstring: direct pinned-SOFA `Pmat06` versus `Ltpb` comparisons differ
by about 16.92″ at `T=-50` and 29.59″ at `T=+50`. This design therefore uses
the SOFA-supported 20th/21st-century overlap for `Ecm06`/`Ltecm` routing and
freezes both switch boundaries. Stage 1 must not repair the defect by deleting
one call globally; it replaces or branches the complete bias-owning transform
and measures every affected chart consumer.

### JPL's unbound-orbit format ('Oumuamua, 2017-09-04 TDB)

EC 1.1997, QR 0.2560 au, IN 122.74°, OM 24.60°, W 241.88°, Tp JD 2458005.997,
N 0.6792°/day, MA −3.7337°, TA 307.52°, A −1.2818 au, AD and PR
9.999999999999998E+99 (placeholders).

### Production small-body kernels

Every small-body kernel on the production host is Sun-centered (segment center
10): `asteroids.bsp` (300 bodies, Type 13), `centaurs.bsp`, `comets.bsp`,
`custom_type13.bsp`, `family_bodies_001`–`008.bsp`, `minor_bodies.bsp`,
`sb441-n373s.bsp` (373 bodies, Type 2), the 10,025-body release shards and the
40 comet release shards.
