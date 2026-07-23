# Moira 5.2.0 - Global Eclipse Circumstances and Adaptive Cartography

**Release date:** 2026-07-23

**Public upgrade path:** 5.1.2 to 5.2.0

Moira 5.2.0 promotes global solar and lunar eclipse circumstances into
first-class, immutable engine products and admits a NumPy-free spherical
cartography surface for maximum-visible magnitude and obscuration. The release
is additive at the public API boundary and keeps astronomical policy,
timescales, ephemeris identity, surface model, and known exclusions explicit.

## Solar global circumstances

`EclipseCalculator.solar_global_circumstances(...)` and the corresponding
`Moira` facade method assemble:

- P1-P4 footprint contacts and event-swept penumbral limits;
- independently solved U1-U4 cone tangencies;
- first and last central-line limits;
- greatest eclipse and greatest duration as distinct optimizations;
- equatorial and ecliptic conjunctions;
- signed gamma and Besselian elements;
- geocentric apparent Sun and Moon states;
- WGS-84 zero-elevation greatest-site position, path width, local duration,
  magnitude, obscuration, altitude, and azimuth; and
- the existing event-swept visibility footprint by reference.

Authoritative horizon junctions, including the 2032 annular and 2049
near-singular hybrid cases exercised by the release corpus, are retained as
exact incidences. Only sub-0.5-second numerical micro-branches wholly confined
to the declared half-kilometre junction neighborhood are normalized.
Connected-component and sunrise/sunset incidence invariants remain strict.

## Lunar global circumstances

`EclipseCalculator.lunar_global_circumstances(...)` and the facade expose one
geocentric result with explicit `native` and `nasa_compat` modes. The result
carries:

- greatest eclipse in TT and UT1 with Delta T and time-policy identity;
- apparent geocentric Sun and Moon right ascension, declination, distance,
  semidiameter, and equatorial horizontal parallax;
- signed gamma, axis distance, lunar radius, umbral and penumbral shadow
  radii, and both eclipse magnitudes; and
- penumbral, partial, and total phase durations where those phases exist.

Mode purity is enforced: native physical geometry and NASA-compatibility
canon geometry cannot be mixed inside one result.

## Adaptive spherical cartography

`solar_eclipse_cartography(...)` evaluates the lawful observer-visible eclipse
interval at adaptive icosphere vertices and produces separate magnitude and
obscuration contours. Refinement is conforming across shared edges and is
driven by:

- midpoint field interpolation error;
- requested contour-level crossings;
- visibility and local-class transitions;
- polar topology; and
- antimeridian seam topology.

The result reports its requested and achieved depth, mesh triangle count,
maximum angular edge, field and angular tolerances, unresolved-edge count, and
convergence state. A flat renderer receives antimeridian-split segments; a 3D
globe retains spherical connectivity.

Duration contours, terrain and elevation, atmospheric refraction, weather,
lunar-limb topography, and projection-specific screen coordinates are not
part of this admitted product.

## REST admission

The optional FastAPI surface adds:

- `POST /v1/eclipses/solar/global-circumstances`;
- `POST /v1/eclipses/solar/cartography`; and
- `POST /v1/eclipses/lunar/global-circumstances`.

Request bounds and response convergence metadata are typed in the OpenAPI
contract. The server remains a transport layer; solver and cartography
doctrine stay in the engine.

## Validation evidence

The release exercises total, annular, hybrid, partial, polar-central, and
near-singular solar geometry; penumbral, partial, total, and limiting lunar
geometry; adaptive-mesh closure; antimeridian splitting; public exports;
native boundary behavior; and REST serialization.

The new global vessels are bound to the repository's existing NASA/GSFC
Besselian and hashed lunar-figure corpora. Detailed 2027-08-02 solar and
2026-08-28 lunar fields are additionally compared with declared EclipseWise
DE405/DE430 rows. These are named cross-model comparisons. Moira's runtime
continues to use content-identified DE441/LE441, its declared mean-limb and
WGS-84 policies, and its selected Delta-T model.

No NumPy, SciPy, Swiss Ephemeris, or jplephem runtime dependency is introduced.
A native dense-field cartography accelerator remains deferred until measured
production evidence justifies its boundary and parity cost.

## Performance smoke

One warm-reader Windows/Python 3.14 smoke using DE441/LE441 and the
2027-08-02 total eclipse measured:

- `solar_global_circumstances(...)`: 18.92 seconds wall time; and
- default `solar_eclipse_cartography(...)`: 39.74 seconds wall time.

The cartography result contained 21 evaluated mesh vertices and 38 triangles
at achieved depth 1. It correctly reported `converged=False` with 31 unresolved
edges under the requested default tolerances. These single-process timings are
performance evidence only. They establish the need for background execution,
request deduplication, caching, and explicit convergence handling in an
interactive website; they are not a throughput guarantee or scientific
validation result.
