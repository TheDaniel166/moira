# Solar and Lunar Eclipse Cartography and Global Circumstances Plan

**Date:** 2026-07-22  
**Status:** Engine, conforming adaptive cartography, and REST admission
implemented; duration cartography and native dense-field acceleration remain
deferred  
**Repository:** Moira engine  
**Runtime:** Project `.venv`, Python 3.14 baseline  
**Protected zones:** `moira/eclipse.py`, eclipse geometry/search/contact modules,
`src/native/`, public exports, facade, server contracts, validation fixtures, and
eclipse standards

## Goal

Deliver three related but semantically distinct first-class eclipse products:

1. a NumPy-free cartography product that maps accurately solved observer-local
   maximum magnitude and obscuration over the globe; and
2. a global-circumstances solver that exposes the full physical event summary,
   including P contacts, U contacts, central-line limits, conjunctions, greatest
   eclipse, greatest duration, geocentric coordinates, gamma, magnitude,
   obscuration, path width, duration, and explicit time-scale metadata; and
3. a lunar global-circumstances product that exposes the complete geocentric
   eclipse summary, including penumbral and umbral magnitudes, signed gamma,
   Sun/Moon coordinates, semidiameters, parallaxes, contacts, durations,
   shadow-model identity, and explicit time-scale metadata.

The products share ephemeris states, local disc geometry, time policy, and
validation evidence. They do not collapse into one vessel:

- global circumstances answer **what defines the event and when its global
  milestones occur**;
- cartography answers **what an observer at each location experiences**; and
- the existing footprint continues to answer **where the swept penumbral cone
  reaches the WGS-84 surface**; while
- lunar global circumstances answer **how the Moon traverses Earth's
  geocentric shadow and under which declared shadow and time models**.

## Scope lock

This is a planning artifact only. Implementation begins after the combined
three-workstream plan is reviewed.

The following are intentionally outside the first admission:

- atmospheric refraction;
- terrain or observer elevation;
- lunar-limb topography and Baily's Beads;
- weather or practical observing quality;
- a NumPy, CuPy, SciPy, or `jplephem` dependency;
- restoration or rebinding of the legacy native cartography header;
- dense duration contours before local contact and greatest-duration semantics
  are independently proven;
- website presentation changes or deployment; and
- any change to the current partial-event shape of `SolarEclipsePath`.

## Existing engine truth

The implementation must build on the admitted engine surfaces rather than the
deleted raster experiment:

- `EclipseCalculator.solar_besselian_elements()` provides content-identified
  DE441/LE441 instantaneous Besselian elements.
- `EclipseCalculator.solar_eclipse_path()` provides the central axis on WGS 84,
  width at greatest eclipse, and local central duration at the greatest-eclipse
  site.
- `EclipseCalculator.solar_eclipse_footprint()` provides P1/P4, optional P2/P3,
  penumbral limits, sunrise/sunset closure, and admitted footprint topology.
- `EclipseCalculator.lunar_eclipse_visibility_map()` is the current model for an
  immutable eclipse map vessel, facade admission, serialization, and REST
  exposure. It is not a solar magnitude-map implementation.
- `_find_contact_pair()` in `moira/_eclipse_contact_solver.py` is the current
  bounded signed-clearance contact pattern.

The removed `moira/solar_cartography.py` and `moira/lunar_cartography.py` are
historical research inputs only. They used NumPy/CuPy grids, fixed time sweeps,
private cross-module imports, and presentation-shaped contours. The current
`src/native/include/cartography.hpp` explicitly marks its observer-grid
functions as legacy and unadmitted. Neither is to be restored wholesale.

## Governing doctrine

### Astronomical model

- Planetary/lunar identity: content-identified DE441/LE441, failing closed for
  another or indeterminate reader.
- Solar/lunar states: the existing Earth-reception light-time policy used by
  the admitted solar shadow axis.
- Terrestrial surface: WGS84 zero elevation.
- Limb model: Moira spherical mean-limb Sun and Moon radii.
- Global contact geometry: physical common-tangent shadow cones against WGS84.
- Local cartographic geometry: apparent topocentric Sun/Moon centers and radii
  under the same declared correction policy.
- Daylight policy for the first product:
  `GEOMETRIC_SUN_CENTER_NONNEGATIVE_ALTITUDE`.
- No atmospheric or topographic correction is implied.

### Time model

Every event epoch must carry its actual scale rather than relying on a column
heading or serializer convention:

- computation occurs at reader-bound TT;
- physical Earth rotation and geographic results use UT1;
- engine results retain both `jd_tt` and `jd_ut1` where the distinction matters;
- UTC calendar rendering is a transport/display conversion and must expose the
  applicable clock policy;
- Delta T is reported with its selected Moira policy and value;
- an external TD/TT value must never be labeled UTC; and
- external fixtures compare common scales, normally TT for event geometry.

### Quantity model

The engine must keep these quantities separate:

- **eclipse magnitude:** linear fraction of the solar diameter obscured; for a
  central eclipse, the Moon/Sun apparent-diameter ratio;
- **obscuration:** fraction of the apparent solar-disc area covered by the
  lunar disc;
- **central duration:** local C2-C3 or A2-A3 interval at one named site;
- **greatest eclipse (GE):** the admitted global shadow-axis maximum;
- **greatest duration (GD):** the site and epoch where lawful local central
  duration is maximal; and
- **visibility footprint:** the swept penumbral-cone boundary, not a magnitude
  or obscuration contour.

## Architecture

```text
DE441/LE441 reader and time policy
        |
        v
shared solar shadow and topocentric disc geometry
        |
        +--> Global circumstances solver
        |      P1-P4 | U1-U4 | C1/C2 | conjunctions | GE | GD
        |      gamma | coordinates | magnitude | obscuration | width/duration
        |
        +--> Scalar observer evaluator
               local maximum epoch | magnitude | obscuration | class | altitude
                       |
                       v
               adaptive globe mesh
                       |
                       v
               contour and band components
                       |
                       v
               facade / REST / website rendering
```

Python owns all product meaning, policy, topology admission, typed vessels, and
validation interpretation. Native C++ may later accelerate only stable dense
evaluation after the Python manuscript is proven.

## Shared result objects

Place neutral data vessels and pure numerical helpers in small modules so the
already large `moira/eclipse.py` does not become the permanent home for new
solver and mesh logic. Recommended boundary:

- new `moira/_eclipse_solar_geometry.py`: private solar-only computational
  substrate for exact topocentric snapshots, apparent discs, stable separation,
  obscuration, Earth-fixed shadow state, WGS84 intersections/tangencies, and
  solar-specific objective functions;
- new `moira/eclipse_global.py`: epoch, contact, coordinate, greatest-site, and
  global-circumstances vessels plus global solver orchestration;
- new `moira/_globe_mesh.py`: semantics-free adaptive spherical triangulation,
  vertex identity, refinement, and contour-graph assembly reusable by a future
  distinct lunar cartography product;
- existing `moira/eclipse.py`: thin `EclipseCalculator` delegation and the
  minimum bridging access to established private state while extraction is
  proven;
- new `moira/eclipse_cartography.py`: scalar site evaluation, solar field
  doctrine, and solar map vessels; and
- existing `moira/_eclipse_contact_solver.py`: general bounded extrema and
  signed-contact primitives that are independent of solar doctrine.

Avoid circular imports by keeping result vessels independent of
`EclipseCalculator`, using callables/protocols for numerical helpers, and using
local imports from `EclipseCalculator` methods only where necessary. Do not
move broad sections of `eclipse.py` until characterization tests prove that the
current path and footprint outputs remain unchanged.

### Proposed global vessels

- `SolarEclipseEpoch`
  - `jd_tt`
  - `jd_ut1`
  - derived UTC representation where supported
  - `delta_t_seconds = TT - UT1`
  - `dut1_seconds = UT1 - UTC`
  - conversion/source identity and explicit scale/model metadata
- `SolarEclipseUmbralContactKind`
  - `U1`, `U2`, `U3`, `U4`
- `SolarEclipseUmbralContact`
  - kind, epoch, WGS84 contact point, tangency classification
- `SolarEclipseUmbralContacts`
  - optional U1-U4 with paired-presence and ordering invariants
- `SolarEclipseCentralLineLimit`
  - first/last axis intersection with epoch and WGS84 point
- `SolarEclipseGeocentricBodyState`
  - apparent RA, declination, semidiameter, horizontal parallax, distance,
    frame, correction policy
- `SolarEclipseGlobalSiteCircumstances`
  - epoch, latitude, longitude, Sun altitude/azimuth, path width, central
    duration, local central-contact witnesses, optimizer residual, magnitude,
    obscuration, and local class
- `SolarEclipseGlobalCircumstances`
  - searched event;
  - existing P contacts by reference, not duplication;
  - optional U contacts;
  - optional central-line limits;
  - equatorial and ecliptic conjunctions;
  - GE and optional GD sites;
  - Sun/Moon geocentric states at GE;
  - signed gamma;
  - Delta T value and policy;
  - ephemeris, surface, limb, frame, and timescale metadata.

### Proposed cartography vessels

- `SolarEclipseMapSample`
  - geographic point, local-maximum epoch, magnitude, obscuration, local class,
    Sun altitude, and convergence/error metadata
- `EclipseContourComponent`
  - quantity, threshold, component identifier, closed/open status, winding,
    and ordered points
- `EclipseContourLevel`
  - one magnitude or obscuration threshold and its components
- `SolarEclipseCartography`
  - parent global-circumstances provenance;
  - requested thresholds;
  - magnitude and obscuration contour levels;
  - optional classified fill bands;
  - mesh/adaptation tolerances and achieved residuals;
  - ephemeris, surface, limb, daylight, and time policy;
  - explicit statement that duration contours are unavailable in version 1.

Longitude discontinuities are represented by separate lawful components, not
by drawing a segment across the map. Exact poles use a canonical longitude
only for serialization; topology must never depend on that arbitrary value.

## Part I - Global circumstances and solver

This part is implemented first because it supplies the lawful epochs,
central-shadow semantics, and exact local evaluator used by cartography.

### Task 1. Freeze the contract and authority fixture

**Files:**

- create `tests/fixtures/nasa_solar_global_circumstances_reference.json`
- create `tests/integration/test_eclipse_global_circumstances_reference.py`
- modify `wiki/02_standards/ECLIPSE_MODEL_STANDARD.md` only when the executable
  contract is ready to be admitted

The fixture must record, for every source row:

- source URL and retrieval date;
- archived file SHA-256 when a PDF/table is cached;
- source ephemeris and lunar-radius convention;
- source Delta T and time scale;
- event class and applicable contacts;
- comparison semantics and units; and
- tolerance category.

Initial event corpus:

- 2027-02-06 annular: complete P/U/C/conjunction/GE/GD/coordinate table;
- 2027-08-02 total: ordinary low/mid-latitude total event and existing website
  regression target;
- one validated hybrid event;
- one global partial event, proving lawful absence of U contacts and GD; and
- the existing 2015 polar central event, proving pole/tangency behavior.

NASA/GSFC Besselian documentation governs field meanings and contact
semantics. EclipseWise/Fred Espenak tables may supply complete operational rows
only as a declared cross-model comparator. They do not replace Moira's DE441
substrate or justify tuning Moira toward DE405/VSOP87/ELP2000 output.

### Task 2. Add scale-explicit epochs and public quantity contracts

**Files:**

- create `moira/eclipse_global.py`
- create `tests/unit/test_eclipse_global.py`

Implement and prove:

- strict finite/type validation for all public fields;
- TT/UT1 pairing under the active reader policy;
- unambiguous units, frames, sign conventions, and correction-policy labels
  for magnitude, obscuration, gamma, RA/declination, semidiameter, parallax,
  Delta T, and DUT1; and
- sexagesimal/calendar formatting only as convenience or serialization, never
  as stored computational truth.

### Task 3. Generalize bounded numerical primitives

**Files:**

- modify `moira/_eclipse_contact_solver.py`
- modify or extend its focused unit tests

Add a generic bounded maximum/minimum helper that:

- accepts finite ordered bounds and an explicit seed/bracket;
- evaluates endpoints as candidates;
- detects a constant or non-finite objective;
- uses a tolerance no smaller than a safe ULP multiple;
- never assumes the global interval is unimodal; and
- exposes measured convergence information to the caller.

Keep product-specific branch selection in `eclipse.py` or
`eclipse_cartography.py`; the generic solver must not know what GE, GD, or an
eclipse contact means.

### Task 3A. Characterize and extract private solar geometry conservatively

**Files:**

- create `moira/_eclipse_solar_geometry.py`
- add characterization tests around existing path and footprint helpers
- modify `moira/eclipse.py` only after those characterization tests pass

Move only independently testable solar-specific primitives needed by both new
products. Preserve existing behavior through thin wrappers until all current
path, polar-path, footprint, fold, and junction regressions pass. The new
private module must not import public result vessels or lunar doctrine.

Implement and prove exact apparent-disc magnitude and exact Euclidean
two-circle obscuration here, with explicit branches for disjoint discs,
external tangency, partial overlap, internal tangency, containment,
equal/concentric discs, zero-radius rejection, and near-tangent floating-point
clamping.

### Task 4. Promote central-line limits without changing path semantics

**Files:**

- modify `moira/eclipse.py`
- modify `tests/integration/test_eclipse_polar_path_nasa_reference.py`
- add focused global-circumstances unit tests

Reuse `_solve_solar_central_interval()` but preserve its result epochs and
points in typed central-line-limit vessels. `SolarEclipsePath` remains
backward-compatible: its current coordinate arrays and partial one-point shape
do not change.

Central-line limits are axis/WGS84 tangencies. They must remain distinct from
U1-U4 cone tangencies.

### Task 5. Solve U1-U4 from the central cone

**Files:**

- modify `moira/eclipse.py`
- add `tests/unit/test_eclipse_umbral_contacts.py`
- extend the global reference integration test

Define two signed central-cone/WGS84 objectives at each epoch:

- exterior support: whether any point of the umbral/antumbral cone intersects
  WGS84; and
- interior support: whether the instantaneous central cone section is fully
  admitted across the relevant Earth-limb topology.

Solve:

- U1: first exterior tangency;
- U2: first interior tangency;
- U3: last interior tangency; and
- U4: last exterior tangency.

The solver must handle:

- total, annular, and hybrid cone sign changes;
- partial events with no U contacts;
- grazing/coalesced U2/U3;
- contact pairs truncated by a kernel boundary;
- polar contact points and undefined pole longitude;
- antimeridian normalization;
- one-branch and multi-branch support extrema; and
- explicit numerical failure rather than invented timestamps.

Required invariants include contact family ordering, WGS84 surface residual,
central-cone tangency residual, and containment within P1-P4 where applicable.

### Task 6. Solve conjunctions and geocentric parameters

**Files:**

- modify `moira/eclipse.py`
- extend `moira/eclipse_global.py`
- extend global unit and integration tests

At the searched event:

- solve ecliptic conjunction as apparent geocentric longitude equality;
- solve equatorial conjunction as apparent geocentric RA equality with explicit
  wrap handling;
- compute apparent geocentric Sun/Moon RA and declination at GE;
- compute semidiameters from the declared mean radii and distances;
- compute equatorial horizontal parallaxes;
- derive signed gamma from the admitted Besselian orientation; and
- compute GE magnitude and obscuration at the admitted GE site.

These fields must name their frame and correction policy. They must not be
assembled from a mixture of geometric, apparent, topocentric, and geocentric
states.

### Task 7. Solve greatest duration independently of greatest eclipse

**Files:**

- modify `moira/eclipse.py`
- add `tests/unit/test_eclipse_greatest_duration.py`
- extend the global reference integration test

Algorithm:

1. obtain every lawful central-path branch between the central-line limits;
2. scan each branch only to discover candidate brackets;
3. at each candidate epoch, intersect the shadow axis with WGS84;
4. solve the site's exact local C2-C3 or A2-A3 mean-limb contacts;
5. refine every local duration maximum in TT;
6. test branch endpoints explicitly because GD can occur at sunrise/sunset;
7. select the lawful global maximum; and
8. convert/report its UT1 epoch only after the TT optimization closes.

Do not assume GD is close to GE or that duration is unimodal. Partial events
return `None` for GD. Grazing central events may return a zero/coalesced
duration only when the mean-limb geometry proves it.

### Task 8. Assemble and admit the engine surface

**Files:**

- modify `moira/eclipse.py`
- modify `moira/__init__.py`
- modify `moira/sky/eclipse.py`
- modify `moira/_facade_special.py`
- modify `moira/facade.py`
- modify `tests/unit/test_api_surface_adversarial_audit.py`

Add:

```python
EclipseCalculator.solar_global_circumstances(
    jd_start,
    *,
    kind="any",
    backward=False,
) -> SolarEclipseGlobalCircumstances
```

and the corresponding `Moira` facade method. Engine and facade exports must
share the same governing class identities. Do not copy the current path
service's direct-calculator bypass; use the admitted facade boundary.

## Part II - NumPy-free solar cartography

### Task 9. Implement one exact scalar observer evaluation

**Files:**

- create `moira/eclipse_cartography.py`
- create `tests/unit/test_eclipse_cartography.py`

For one WGS84 zero-elevation site:

1. use P1-P4 as the lawful search interval;
2. sample only to find every candidate local maximum and horizon transition;
3. refine topocentric disc-separation minima and magnitude/obscuration maxima;
4. enforce the declared geometric Sun-center daylight policy;
5. compare endpoints and horizon-constrained candidates;
6. return the local maximum epoch, apparent radii, separation, magnitude,
   obscuration, local class, and Sun altitude; and
7. report no visible eclipse distinctly from a numerical zero.

Magnitude and obscuration may reach their extrema at slightly different
instants. The implementation must either solve each quantity independently or
prove and document a shared-epoch policy; it must not silently reuse one
quantity's maximum for the other.

### Task 10. Build a deterministic adaptive globe mesh

**Files:**

- modify `moira/eclipse_cartography.py`
- create `moira/_globe_mesh.py`
- create `tests/unit/test_globe_mesh.py`
- add synthetic mesh tests

Use a closed spherical triangulation rather than a latitude/longitude raster.
Put mesh connectivity and contour-graph mechanics in `_globe_mesh.py`; keep
solar quantities in `eclipse_cartography.py`. Refine cells when any of the
following is true:

- a requested magnitude threshold is bracketed;
- a requested obscuration threshold is bracketed;
- the visibility/daylight state changes;
- a penumbral or central boundary crosses the cell;
- interpolation error exceeds the declared field tolerance; or
- the cell intersects a polar or antimeridian topology transition.

The refinement contract must include:

- maximum angular edge length;
- magnitude/obscuration interpolation tolerances;
- maximum refinement depth and explicit non-convergence behavior;
- deterministic vertex identity and evaluation caching;
- stable spherical interpolation; and
- no dependence on map projection.

### Task 11. Extract and validate contour components

**Files:**

- modify `moira/eclipse_cartography.py`
- add contour topology and direct-residual tests

Use marching triangles on the converged mesh. Then:

- join segments by mesh identity, not rounded longitude;
- preserve multiple components;
- canonicalize winding;
- split lawful antimeridian crossings for transport;
- handle pole-enclosing rings without artificial closure lines;
- reject open interior contours unless they lawfully terminate at the
  visibility/daylight boundary; and
- directly re-evaluate sampled contour points against the scalar evaluator.

The public product carries vector components suitable for flat maps and the
3D globe. The engine does not emit projection-specific screen coordinates.

### Task 12. Admit magnitude and obscuration only

Version 1 admits:

- maximum visible magnitude contours/bands;
- maximum visible obscuration contours/bands;
- local classification boundaries; and
- optional sparse field samples for diagnostics, not a public global raster.

Duration contours remain explicitly unavailable until:

- local C1-C4/A1-A4 contact semantics are first-class;
- GD has passed external and invariant validation;
- adaptive integration error is bounded independently; and
- a distinct duration-contour contract is reviewed.

The old cartography module's duration accumulation is not reused. A later
admission should be a distinct `SolarEclipseDurationCartography` product rather
than an incidental option on the magnitude/obscuration map.

### Task 13. Add native acceleration only after Python proof

**Files:**

- create `src/native/include/solar_eclipse_cartography.hpp`
- modify `src/native/bindings/moira_native.cpp`
- modify `moira/moira_native.py` only if the public native wrapper pattern
  requires it
- add `tests/unit/test_native_eclipse_cartography.py`
- add Python/native differential tests

The native boundary may accelerate:

- batched topocentric Sun/Moon vectors for already-declared epochs/sites;
- apparent radii, stable separation, magnitude, and obscuration evaluation;
  and
- repeated mesh-vertex evaluations.

The native boundary must not decide:

- time/correction policy;
- whether a site is lawfully visible;
- which extrema are globally admitted;
- contour topology or component identity;
- refinement termination; or
- public result semantics.

Bindings accept ordinary Python sequences/buffers and return pybind-owned
scalars or tuples. NumPy is not imported or required. The Python scalar
evaluator remains the parity oracle. `src/native/include/cartography.hpp`
remains untouched and unbound.

### Task 14. Add engine/facade surface

**Files:**

- modify `moira/eclipse.py`
- modify `moira/__init__.py`
- modify `moira/sky/eclipse.py`
- modify `moira/_facade_special.py`
- modify `moira/facade.py`
- modify public-surface snapshot tests

Add:

```python
EclipseCalculator.solar_eclipse_cartography(
    jd_start,
    *,
    kind="any",
    backward=False,
    magnitude_levels=(0.2, 0.4, 0.6, 0.8, 0.9),
    obscuration_levels=(0.2, 0.4, 0.6, 0.8, 0.9),
    angular_tolerance_deg=...,
    field_tolerance=...,
) -> SolarEclipseCartography
```

Thresholds, refinement depth, and tolerances require strict bounded input
validation. Defaults are product policy and must be documented rather than
chosen for a particular screenshot.

## Transport admission

Transport follows only after the corresponding engine slice and public
snapshots are green. The lunar endpoint may be admitted after its own engine
gates pass; it does not wait for the solar cartography slice.

**Files:**

- modify `moira_server/models/phenomena.py`
- modify `moira_server/services/phenomena.py`
- modify `moira_server/serializers/phenomena.py`
- modify `moira_server/routers/phenomena.py`
- modify the corresponding package `__init__.py` exports
- add focused server tests

Recommended additive endpoints:

- `POST /v1/eclipses/solar/global-circumstances`
- `POST /v1/eclipses/solar/cartography`
- `POST /v1/eclipses/lunar/global-circumstances`

The response contract must expose model/timescale metadata and separate
magnitude from obscuration. It should serialize contour components directly or
through a formally declared GeoJSON adapter; it must not make GeoJSON the
engine's governing object.

Starlette `TestClient` tests require the repository's `loopback` marker because
their AnyIO/event-loop plumbing may use local sockets. That marker admits only
numeric loopback or local IPC and does not authorize external egress.

Website consumption is a later bounded integration. The same engine components
must render on both flat map and globe without recomputation or projection-
specific engine branches.

## Validation program

### Evidence classes

- **Physical invariants:** WGS84 membership, cone-clearance roots, disc-overlap
  identities, contact ordering, mesh convergence, contour residuals.
- **Python/native differential:** same declared inputs and policy, with explicit
  numeric tolerances.
- **Primary-authority comparison:** NASA/GSFC definitions, Besselian fields,
  published path/contact rows.
- **Cross-model corroboration:** EclipseWise/Fred Espenak complete tables under
  their declared ephemeris, Delta T, and lunar-radius conventions.
- **Regression:** dated Moira fixtures and website event cases; never presented
  as external truth.

### Initial cross-model calibration ceilings

These are proposed gates to calibrate against the corpus, not source
uncertainties and not permission to tune Moira toward another model:

| Product | Initial ceiling |
|---|---:|
| U1-U4 common-TT epoch | 10 s |
| GE/GD common-TT epoch | 5 s |
| GE/GD WGS84 site | 5 km |
| GE/GD central duration | 3 s |
| central width | 3 km |
| magnitude | 0.005 |
| gamma | 0.0002 Earth radii |

Cartography has no dense authoritative numeric corpus in the checkout. Do not
claim atlas-grade dense contour parity from a published image. Validate it by:

- direct scalar re-evaluation on every selected contour segment;
- convergence under tighter mesh tolerances;
- published city/path/circumstance anchors where available;
- containment within the admitted visibility footprint;
- correct polar/antimeridian topology; and
- independent spot checks against primary or domain-primary tables.

### Adversarial corpus

At minimum cover:

- total, annular, hybrid, and global partial events;
- one-limit and two-limit penumbral footprints;
- polar central lines and polar-enclosing contours;
- antimeridian crossings;
- sunrise/sunset GE or GD candidates;
- grazing/coalesced U2/U3;
- nearly tangent apparent discs;
- Moon larger, equal to, and smaller than Sun;
- kernel start/end truncation;
- rejected non-DE441/LE441 readers;
- refinement exhaustion and non-finite objective rejection; and
- deterministic results across repeated runs and Python/native paths.

## Verification sequence

Use the project interpreter for every command and set deterministic/no-download
environment policy as appropriate.

1. Small pure-unit slices:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_global.py -q
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_umbral_contacts.py -q
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_greatest_duration.py -q
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_cartography.py -q
   ```

2. Existing protected regression slices:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_helpers.py tests\unit\test_eclipse_footprint.py -q
   .\.venv\Scripts\python.exe -m pytest tests\integration\test_eclipse_besselian_nasa_reference.py tests\integration\test_eclipse_polar_path_nasa_reference.py -q
   .\.venv\Scripts\python.exe -m pytest tests\integration\test_eclipse_footprint_nasa_reference.py tests\integration\test_eclipse_footprint_fold_regression.py -q
   ```

3. New external-reference slice:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\integration\test_eclipse_global_circumstances_reference.py -q
   .\.venv\Scripts\python.exe -m pytest tests\integration\test_lunar_eclipse_global_circumstances_reference.py -q
   ```

4. Native parity after the accelerator exists:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_native_eclipse_cartography.py tests\test_native_parity.py -q
   ```

5. Public and server contracts:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_api_surface_adversarial_audit.py -q
   .\.venv\Scripts\python.exe -m pytest tests\server\test_server_eclipse_global_circumstances.py tests\server\test_server_eclipse_cartography.py -q
   ```

6. Deterministic network-excluding suite and documentation guard only after
   targeted slices pass:

   ```powershell
   $env:MOIRA_TEST_MODE = "1"
   $env:MOIRA_STRICT_KNOWN_ISSUES = "1"
   .\.venv\Scripts\python.exe -m pytest -m "not external_network"
   .\.venv\Scripts\python.exe scripts\check_doc_consistency.py
   ```

Any benchmark added for the adaptive mesh or native evaluator is performance
evidence only. It is not scientific validation.

## Delivery order and stop gates

1. Approve the combined three-workstream plan.
2. Freeze shared scale/body-state vessels, timescale doctrine, source fixtures,
   model identities, and tolerances.
3. Implement pure epoch/disc geometry and generic numerical primitives.
4. Assemble and validate the lunar global-circumstances product from the
   existing lunar event, canon, contact, and visibility substrate.
5. Implement and validate solar C limits, U contacts, conjunctions, GE
   parameters, and GD.
6. Admit the solar and lunar global engine/facade surfaces.
7. Implement and prove the scalar solar observer evaluator.
8. Implement adaptive mesh and magnitude/obscuration contours in Python.
9. Admit cartography only after convergence and topology gates pass.
10. Measure before adding the new native accelerator.
11. Prove Python/native parity, then admit the native path.
12. Add REST transport.
13. Integrate the website in its isolated worktree and verify flat map and
    globe independently.
14. Run release gates only after engine, transport, and presentation scopes are
    separately green.

Each stage stops on semantic ambiguity, missing authority, failed invariant,
or unexplained Python/native divergence. No known-issues entry may hide a
failure introduced by this work.

## Protected work and preservation rules

- Declare protected-zone edits before touching eclipse, native, facade, server,
  validation, or standards files.
- Preserve the unrelated in-progress Pancha Pakshi roadmap modification.
- Do not alter website or Urania Workspace production while proving engine
  products.
- Do not replace or weaken current `SolarEclipsePath`, footprint, or lunar
  visibility-map contracts.
- Do not claim complete eclipse-subsystem proof from this feature's corpus.
- Do not delete the legacy native header until a separate archaeological and
  reuse decision is approved.

## Part III - Lunar global circumstances and parameter reproduction

### Feasibility finding

All twelve categories in the supplied 2026-08-28 lunar-eclipse parameter table
are computable from the current engine:

- penumbral magnitude;
- umbral magnitude;
- signed gamma;
- apparent geocentric Sun right ascension and declination;
- apparent geocentric Moon right ascension and declination;
- Sun and Moon semidiameters;
- Sun and Moon equatorial horizontal parallaxes; and
- Delta T.

They are now assembled into the first-class
`LunarEclipseGlobalCircumstances` result, with explicit `native` and
`nasa_compat` modes. Its derivation remains visibly owned by
`LunarEclipseAnalysis`, the lunar-canon geometry and contact vessels,
planetary states, angular-radius and parallax helpers, and the selected
time-policy functions.

The source row is not model-neutral. The EclipseWise figure declares:

- JPL DE430;
- Delta T = 72.3 seconds;
- Herald/Sinnott shadow rule; and
- shadow enlargement = 1.000.

Moira's admitted planetary/lunar substrate is DE441/LE441. The current
`nasa_compat` lunar path uses its own catalog Delta-T policy and Danjon-style
shadow convention; its name therefore does not imply exact compatibility with
this newer EclipseWise figure.

A current DE441 evaluation demonstrates the boundary:

| Quantity | Moira current model | EclipseWise row |
|---|---:|---:|
| Gamma | 0.496409 | 0.49644 |
| Umbral magnitude | 0.929816 | 0.93187 |
| Penumbral magnitude | 1.965261 | 1.96645 |
| Sun RA / declination | 10h26m57.86s / +09°42'52.67" | 10h26m57.9s / +09°42'52.7" |
| Moon RA / declination | 22h26m06.38s / -09°18'03.28" | 22h26m06.3s / -09°18'03.6" |
| Sun semidiameter / parallax | 15'50.45" / 8.71" | 15'50.0" / 8.7" |
| Moon semidiameter / parallax | 15'17.92" / 56'09.89" | 15'18.2" / 56'09.9" |
| Delta T | 75.393 s | 72.3 s |

This is strong cross-model corroboration, not exact-table parity. The
implementation must expose both of the following without conflation:

1. **Moira native global circumstances:** DE441/LE441 and the admitted Moira
   time, limb, and shadow policies.
2. **Named source compatibility:** an optional, explicitly named profile only
   after its DE430 resource, Delta-T policy, and Herald/Sinnott shadow
   derivation are independently admitted and validated.

Do not alter native constants, Delta T, or shadow radii merely to make the
EclipseWise row match.

### Governing lunar product

Lunar global circumstances describe one geocentric Moon/Earth-shadow event.
They are not a lunar version of a solar Besselian surface path:

- eclipse depth is governed by the Moon's separation from the anti-solar
  shadow axis and the declared umbral/penumbral radii;
- the event's intrinsic magnitude at one instant is global, not a different
  value for each terrestrial location;
- observers differ primarily by whether the Moon is above their horizon during
  each contact and by their local apparent circumstances; and
- no solar-style central-line corridor, path width, or spatial magnitude
  contour is implied.

The new result must preserve three distinct layers:

1. global geocentric shadow geometry;
2. event timing and contacts; and
3. observer visibility, already represented separately by
   `LunarEclipseVisibilityMap` and `LunarEclipseLocalCircumstances`.

### Proposed architecture

**Files:**

- create `moira/lunar_eclipse_global.py`
- extend `moira/eclipse_global.py` only with genuinely neutral shared vessels
- modify `moira/eclipse.py` for thin calculator delegation
- modify `moira/__init__.py` and `moira/sky/eclipse.py` for public identity
- modify `moira/_facade_special.py` and `moira/facade.py` for facade admission
- add focused unit, integration, public-surface, and server tests

Keep lunar shadow geometry in `moira/eclipse_canon.py`, angular-size/parallax
physics in `moira/eclipse_geometry.py`, and contact solving in
`moira/eclipse_contacts.py`. Do not move established algorithms merely to make
the new vessel look self-contained.

Parts I and III may share only neutral objects whose semantics are identical:

- `EclipseEpoch` or an equivalent scale-explicit instant;
- `GeocentricBodyState`;
- ephemeris identity;
- correction-policy identity; and
- time-scale/Delta-T provenance.

Solar-specific GE/GD sites, Besselian gamma, WGS84 tangencies, path width,
obscuration, and cartography types must not leak into the lunar product.

### Proposed result contract

Add immutable vessels equivalent to:

- `LunarEclipseShadowPolicy`
  - model identity;
  - umbral/penumbral enlargement rule and parameters;
  - lunar-radius/limb convention;
  - source authority or derivation identity;
- `LunarEclipseGeocentricGeometry`
  - signed gamma and sign convention;
  - shadow-axis distance;
  - Moon, umbra, and penumbra radii in declared angular and normalized units;
  - penumbral and umbral magnitude as separate fields;
  - epsilon or equivalent axis-motion orientation when admitted;
- `LunarEclipseGlobalCircumstances`
  - existing mode-consistent `LunarEclipseAnalysis` by reference rather than
    duplicated event/contact fields;
  - greatest-eclipse epoch in TT and UT1;
  - explicit Delta T value and policy;
  - P1/U1/U2/U3/U4/P4 contacts available through that analysis with lawful
    optionality;
  - penumbral, partial, and total phase durations where applicable;
  - apparent geocentric Sun and Moon states at greatest eclipse;
  - lunar shadow geometry;
  - ephemeris, frame, origin, reception/light-time, aberration, limb, shadow,
    and timescale metadata;
  - selected computational profile, such as `native`, the existing bounded
    `nasa_compat`, or a future source-specific compatibility profile.

`GeocentricBodyState` stores numeric radians/degrees and distances. Sexagesimal
RA/declination and calendar strings are formatting conveniences only.

The coordinate contract must state:

- geocentric origin;
- true equator and equinox of date or another explicitly selected frame;
- apparent versus geometric state;
- reception light-time and aberration policy;
- no topocentric displacement or atmospheric refraction; and
- whether the stated epoch is TT, UT1, or a derived display clock.

### Task 15. Freeze the lunar authority fixture and model taxonomy

**Files:**

- create `tests/fixtures/lunar_eclipse_global_parameters_reference.json`
- create `tests/integration/test_lunar_eclipse_global_circumstances_reference.py`

Record the complete EclipseWise 2026-08-28 row, greatest-eclipse instant,
contacts, shadow radii, opposition epochs, source URL, retrieval date, source
ephemeris, Delta T, shadow rule, enlargement, units, scales, and archived
artifact hash where one is retained. Record that the figure uses the Moon's
center of mass and Herald/Sinnott atmospheric-shadow geometry rather than
leaving those semantics implicit.

Classify each assertion explicitly as:

- native physical/invariant validation;
- same-model authority validation;
- cross-model corroboration; or
- regression.

Until DE430 plus the source shadow rule is admitted, the screenshot row is a
cross-model corpus. It is not a strict native-output golden fixture.

The initial event set must also include:

- one total lunar eclipse with U2/U3 and totality duration;
- the 2026-08-28 deep partial event;
- one penumbral-only event with all umbral contacts lawfully absent;
- one grazing/coalescing umbral boundary case;
- one event on each signed-gamma side; and
- one kernel/time-policy boundary case.

### Task 16. Assemble the native lunar global product

**Files:**

- create `moira/lunar_eclipse_global.py`
- modify `moira/eclipse.py`
- add `tests/unit/test_lunar_eclipse_global_circumstances.py`

Build the result from the existing searched event, native contact solver,
shadow-axis geometry, body-state reduction, apparent-radius/parallax helpers,
and selected Delta-T policy. One named epoch must drive every row; do not
quietly mix greatest eclipse, equatorial opposition, and ecliptic opposition.

Required invariants:

- finite, ordered contacts within P1-P4;
- contact presence consistent with eclipse class;
- `penumbral_magnitude >= umbral_magnitude`;
- signed gamma consistent with the declared fundamental-plane orientation;
- parallax consistent with distance and the declared Earth radius;
- semidiameter consistent with distance and mean-limb radius;
- RA/declination reconstruct the stored unit vector within tolerance;
- TT-UT1 equals the reported Delta T within numerical tolerance; and
- repeated calls are deterministic and do not mutate cached event state.

Native signed gamma must be derived from the native shadow geometry. It must
not be borrowed from a different compatibility profile.

### Task 17. Preserve compatibility profiles as explicit policy

**Files:**

- modify `moira/eclipse_canon.py` only where a new admitted profile requires it
- add focused profile and lineage tests
- update eclipse standards only after admission

Keep the existing `nasa_compat` behavior backward-compatible. If exact
EclipseWise reproduction is required, introduce a separately named profile
such as `eclipsewise_de430_herald_sinnott` only after:

1. the DE430 resource is lawfully acquired and content-identified;
2. the Herald/Sinnott shadow rule is derived from an authoritative source;
3. the Delta-T rule/value is explicit rather than fixture-injected;
4. every differing constant and enlargement convention is visible;
5. same-model tests reproduce the source row under declared tolerances; and
6. the sovereignty audit confirms the implementation is source-derived rather
   than reverse-fitted to published outputs.

Exact-table compatibility is optional. The first-class native summary is not
blocked by it.

No C++ helper is proposed for this product. It is a constant-cost summary
assembled once per event from existing engine states and solvers; native work
would add boundary and parity risk without addressing a measured dense-work
bottleneck.

### Task 18. Admit the public engine and facade surface

Add:

```python
EclipseCalculator.lunar_global_circumstances(
    jd_start,
    *,
    kind="any",
    backward=False,
    mode="native",
) -> LunarEclipseGlobalCircumstances
```

and the corresponding `Moira` facade method. Validate mode, event class, search
direction, kernel identity, and unsupported source profiles before computation.
Engine and facade exports must reference the same public class identities.

The existing `analyze_lunar_eclipse()`,
`lunar_eclipse_local_circumstances()`, and
`lunar_eclipse_visibility_map()` remain stable and may be referenced by the new
product rather than duplicated.

### Task 19. Keep lunar cartography a distinct follow-on

Part II's `_globe_mesh.py` may later support lunar map products, but the mapped
scalar must be defined first. Lawful candidates include:

- contact visibility;
- maximum visible phase at each observer;
- Moon altitude at maximum visible phase;
- local visible penumbral/partial/total duration; and
- contact-specific rise/set boundaries.

Do not draw a solar-style global lunar magnitude band merely by projecting one
geocentric magnitude value over Earth. A `maximum visible magnitude` map would
combine the time-varying global shadow geometry with each site's horizon
visibility and must solve the observer's lawful visible time interval.

The existing `LunarEclipseVisibilityMap` remains the admitted first map
product. A future magnitude/duration layer requires a separate typed contract,
adaptive-field convergence proof, and source/invariant corpus before it is
added to either flat map or globe.

### Lunar validation gates and provisional tolerances

The first pass must record residual distributions and calibrate tolerances from
the declared model differences rather than treating the source's printed
precision as uncertainty. The following values are exploratory cross-model
ceilings for the 2026 event, subject to confirmation across the full corpus
before they become acceptance gates:

| Product | Initial ceiling |
|---|---:|
| apparent RA/declination | 2 arcseconds |
| semidiameter/parallax | 1 arcsecond |
| signed gamma | 0.0002 Earth radii |
| penumbral/umbral magnitude | 0.005 |
| greatest/contact common-TT epoch | 10 seconds |

These are calibration targets for DE441 versus the cited DE430 product, not
same-model compatibility tolerances. A future admitted
`eclipsewise_de430_herald_sinnott` profile requires materially tighter,
field-specific gates derived from the source precision and numerical method.

Run the new lunar slice with the existing focused regressions:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lunar_eclipse_global_circumstances.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_lunar_eclipse_global_circumstances_reference.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_lunar_nasa_compat_reference.py tests\integration\test_eclipse_lunar_contacts_nasa_reference.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lunar_eclipse_visibility.py tests\integration\test_lunar_eclipse_visibility.py -q
```

The first lunar release stops if a field mixes models without metadata,
if native and compatibility outputs are silently substituted, if contact or
timescale invariants fail, or if a published comparison cannot be classified
honestly by evidence type.
