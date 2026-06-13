# Post-Phase-10 Astrocartography Minor-Body And Fixed-Star Admission Workflow

Version: 0.3
Date: 2026-06-12
Status: Direct-coordinate support admitted; selected minor-body chart support
partially admitted; fixed-star server-derived support deferred
Scope: Selected minor-body and fixed-star Astrocartography admission before
rendering convenience work

This document defines the next Astrocartography expansion after the first
bounded P10-01 REST admission and before any rendering-adapter implementation.

The purpose is to decide, harden, and document how Astrocartography may treat
minor bodies and fixed stars as first-class line/point subjects without hiding
coordinate provenance or smuggling catalog sweeps into a rendering layer.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `docs/architecture/P10-01_ASTROCARTOGRAPHY_TRANSPORT_DESIGN.md`
- `wiki/02_standards/ASTROCARTOGRAPHY_BACKEND_STANDARD.md`
- `wiki/02_services/REST_API_REFERENCE.md`

Authoritative computational source:

- `moira/astrocartography.py`

Related body-position sources:

- `moira/asteroids.py`
- `moira/comets.py`
- `moira/stars.py`

---

## 1. Purpose

The admitted Astrocartography engine is coordinate-driven. Its direct line and
subplanetary products can operate on any named subject when the caller supplies
apparent right ascension and declination. That makes minor-body and fixed-star
Astrocartography possible, but not automatically first-class.

First-class admission requires Moira to declare:

- which subject classes are admitted
- which coordinate source owns each subject's apparent place
- how body identity and catalog provenance are preserved
- which products remain selected-body products
- which catalog-wide or heavy-output products remain deferred
- which tests prove direct and server-derived behavior

This workflow must be completed before the Astrocartography rendering adapter,
because render primitives should not become the place where body-class policy is
invented.

---

## 2. Current Truth

The current P10-01 REST surface has four admitted routes:

- `POST /v1/astrocartography/lines`
- `POST /v1/astrocartography/chart/lines`
- `POST /v1/astrocartography/subplanetary`
- `POST /v1/astrocartography/chart/subplanetary`

Current body-class truth:

- Direct Astrocartography routes accept caller-owned RA/Dec maps keyed by body
  label. They are already capable of selected minor-body or fixed-star use when
  the caller supplies valid apparent RA/Dec and sidereal-time truth.
- Chart-backed Astrocartography line routes now admit selected asteroids whose
  topocentric RA/Dec can be derived through the admitted `sky_position_at`
  path. Chart-backed comet lines remain deferred because the public comet
  front door currently admits only the default apparent geocentric ecliptic
  path.
- Chart-backed Astrocartography subplanetary routes now admit selected
  asteroids and comets whose geocentric ecliptic position can be derived
  through `planet_at(...)` and converted to equatorial of date.
- Fixed stars are not chart bodies. They need an explicit selected-star
  admission surface or a documented direct-coordinate stance.
- Catalog-wide fixed-star, asteroid, comet, or small-body sweeps remain
  deferred.

---

## 3. Admission Boundary

Admitted in this workflow:

- direct RA/Dec Astrocartography for selected non-planet labels when the caller
  owns apparent RA/Dec truth
- selected asteroid chart-backed Astrocartography lines through the admitted
  topocentric RA/Dec path
- selected asteroid and comet chart-backed subplanetary points through the
  admitted geocentric ecliptic-to-equatorial path
- subject provenance for direct labels, chart planets, selected asteroids, and
  selected comets

Not admitted in this workflow:

- catalog-wide fixed-star sweeps
- catalog-wide asteroid or comet sweeps
- chart-backed comet Astrocartography lines
- server-derived fixed-star Astrocartography
- dense maps, grids, tiles, contours, or rendered images
- async job infrastructure
- projection authority such as Web Mercator
- visual style or rendering policy
- implied support for every object in every catalog

---

## 4. Subject-Class Doctrine

### 4.1 Direct Coordinates

Direct coordinate Astrocartography is the lowest-risk admission path.

Doctrine:

- the caller owns the supplied apparent RA/Dec and sidereal time
- Moira validates finite coordinate truth and operational bounds
- Moira computes Astrocartography lines or subplanetary points from those
  coordinates
- Moira does not reinterpret the subject class from the label alone

Required documentation change:

- describe `/v1/astrocartography/lines` and
  `/v1/astrocartography/subplanetary` as subject-label agnostic when the caller
  supplies valid apparent RA/Dec

Required tests:

- direct line route accepts a non-planet asteroid-like label
- direct line route accepts a fixed-star-like label
- direct subplanetary route accepts the same non-planet labels
- provenance remains `coordinate_source="direct_ra_dec"`

### 4.2 Minor Bodies

Minor-body admission must distinguish identity classes:

- asteroids
- comets
- later small-body classes, if admitted separately

Required evaluation:

- confirm which minor-body modules expose the required coordinate frame for
  Astrocartography
- confirm whether RA/Dec is already available or must be derived from ecliptic
  longitude/latitude
- declare whether derived RA/Dec is geocentric or topocentric
- preserve catalog identity and orbital/kernel provenance
- confirm that selected-body lookup is bounded and deterministic

First preferred stance:

- direct-coordinate support is admitted and tested
- selected asteroid chart-backed line support is admitted and tested
- selected asteroid/comet chart-backed subplanetary support is admitted and
  tested
- selected comet chart-backed line support remains deferred until the
  topocentric RA/Dec comet path is admitted explicitly

### 4.3 Fixed Stars

Fixed-star admission must preserve star-catalog truth.

Required evaluation:

- confirm the star identity surface and aliases used by REST
- confirm epoch, proper-motion, and apparent-place policy
- confirm whether the star surface exposes apparent RA/Dec directly or whether
  the server must derive it from admitted star outputs
- preserve catalog provenance in every server-derived response
- bound selected-star count separately from catalog-wide operations

First preferred stance:

- direct-coordinate support is admitted and tested
- admit selected-star server-derived ACG only after star apparent-place policy
  is explicit
- keep catalog-wide fixed-star ACG deferred until async or bounded-output
  policy exists

---

## 5. Proposed Route Strategy

The current four P10-01 routes should remain the admitted base surface.

Implemented expansion:

1. Clarified direct-coordinate routes as subject-label agnostic.
2. Added tests proving direct routes accept selected non-planet labels.
3. Audited existing chart-backed routes for admitted minor-body behavior.
4. Kept selected minor-body support in the existing chart-backed routes where
   the coordinate path is admitted.
5. Deferred selected fixed-star server-derived ACG.

Possible later selected-subject routes, if admitted:

- `POST /v1/astrocartography/minor-body/lines`
- `POST /v1/astrocartography/minor-body/subplanetary`
- `POST /v1/astrocartography/fixed-star/lines`
- `POST /v1/astrocartography/fixed-star/subplanetary`

These route names are placeholders. They must not be implemented until a
transport design declares request/response models, identity policy, coordinate
source, provenance, and bounds.

---

## 6. Provenance Requirements

Direct coordinate responses must preserve:

- `coordinate_source="direct_ra_dec"`
- requested subject labels
- returned subject labels
- sidereal-time source supplied by caller
- sampling policy

Server-derived minor-body responses must preserve:

- subject class
- canonical identifier
- requested alias, when applicable
- position-source module
- coordinate frame before RA/Dec conversion
- RA/Dec derivation stage sequence
- JD/time scale used by the body-position source
- catalog/kernel/orbital provenance where available

Current admitted subject provenance fields:

- `requested_label`
- `returned_label`
- `subject_class`
- `canonical_name`
- `naif_id`
- `position_source`

Server-derived fixed-star responses must preserve:

- catalog identifier
- requested alias, when applicable
- catalog/source provenance
- epoch/proper-motion policy
- apparent-place policy
- RA/Dec derivation stage sequence
- JD/time scale used by the star-position source

---

## 7. Verification Requirements

Implemented verification includes:

- unit or service tests proving direct ACG accepts non-planet labels without
  changing coordinate truth
- route tests proving non-planet direct labels serialize with stable provenance
- a chart-backed minor-body audit showing selected asteroid lines are admitted,
  selected asteroid/comet subplanetary points are admitted, and selected comet
  lines are deferred
- a fixed-star audit showing that chart-backed routes reject fixed stars rather
  than silently claiming star support
- adversarial rejection for invalid RA/Dec, empty labels, oversized selected
  subject lists, and non-finite time or coordinate inputs

If server-derived minor-body or fixed-star routes are added later, they must
also prove:

- direct-vs-derived equivalence where the same RA/Dec is supplied through both
  paths
- stable subject identity canonicalization
- provenance preservation
- bounded output size

---

## 8. Implementation Plan

This work should proceed in gated slices. Each slice must leave the REST truth
more explicit than it found it. Do not implement rendering-adapter work until
all gates below are resolved.

Protected zones implicated:

- public REST transport models and route semantics
- chart-backed body derivation policy
- small-body kernel/provenance truth
- fixed-star catalog/proper-motion/apparent-place truth

Runtime edits must stay narrow. Do not alter the astronomical core unless an
audit proves a missing public coordinate vessel or derivation helper is required.

### 8.1 Slice A: Direct-Coordinate Admission Hardening

Status: Completed.

Goal:

- Admit selected minor-body and fixed-star Astrocartography through the existing
  direct RA/Dec routes.

Files likely touched:

- `tests/server/test_server_astrocartography_routes.py`
- `docs/architecture/P10-01_ASTROCARTOGRAPHY_TRANSPORT_DESIGN.md`
- `wiki/02_services/REST_API_REFERENCE.md`

Implementation tasks:

1. Add route tests for `/v1/astrocartography/lines` with labels such as
   `Ceres`, `Halley`, and `Sirius`, using caller-owned RA/Dec fixtures.
2. Add route tests for `/v1/astrocartography/subplanetary` with the same
   labels.
3. Assert that the response preserves labels exactly in `planet`,
   `requested_bodies`, and `returned_bodies`.
4. Assert that provenance remains `coordinate_source="direct_ra_dec"`.
5. Assert that line and point counts are unchanged by non-planet labels.
6. Add adversarial tests for empty labels, oversized maps, non-finite RA/Dec,
   invalid declination, non-finite `gmst_deg`, and non-finite `jd_ut`.

Expected result:

- Direct-coordinate minor-body and fixed-star Astrocartography becomes a tested
  current capability.
- No new routes are added.
- No small-body or fixed-star position computation is claimed.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_astrocartography_routes.py -q
```

Admission gate:

- If this slice passes, documentation may truthfully say selected non-planet
  labels are supported only when the caller supplies apparent RA/Dec.

### 8.2 Slice B: Chart-Backed Minor-Body Audit

Status: Completed.

Goal:

- Determine whether existing chart-backed Astrocartography already supports
  selected asteroids and comets, partially supports them, or only appears to.

Files likely touched:

- `tests/server/test_server_astrocartography_routes.py`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- this workflow document, if the audit result changes the plan

Code paths to audit:

- `moira_server.services._shared.require_supported_chart_bodies(...)`
- `moira_server.services.astrocartography._build_chart(...)`
- `moira_server.services.astrocartography.compute_astrocartography_chart_lines(...)`
- `moira_server.services.astrocartography.compute_astrocartography_chart_subplanetary(...)`
- `moira.planets.sky_position_at(...)`
- `moira.planets.planet_at(...)`
- `moira.asteroids.asteroid_at(...)`
- `moira.comets.comet_at(...)`

Audit questions:

- Does `require_supported_chart_bodies(..., allow_small_bodies=True)` admit the
  selected asteroid/comet name?
- Does `engine.chart(..., bodies=request.bodies)` preserve the selected
  asteroid/comet in chart context truth?
- Does chart-backed line computation derive RA/Dec through `sky_position_at`
  for selected asteroids and comets without collapsing provenance?
- Does chart-backed subplanetary computation derive ecliptic coordinates
  through `planet_at` for selected asteroids and comets with the correction
  switches required by small-body policy?
- Do missing kernels fail with a clear operational error rather than a false
  unsupported-body or validation error?

Test stance:

- Prefer service-level audit tests first, because local kernel availability may
  vary.
- Mark kernel-dependent tests with the existing ephemeris/network markers used
  by the route test suite.
- If deterministic kernels are not available in normal CI, add explicit tests
  proving validation behavior and document the runtime dependency gap.

Admission gate:

- Selected asteroid chart-backed lines are admitted with subject provenance.
- Selected asteroid and comet chart-backed subplanetary points are admitted
  with subject provenance.
- Selected comet chart-backed lines are deferred because the public comet
  front door currently rejects the topocentric RA/Dec mode needed by the line
  route.

### 8.3 Slice C: Minor-Body RA/Dec Derivation Contract

Status: Partially completed.

Goal:

- Define the explicit RA/Dec derivation contract for server-derived selected
  asteroid and comet Astrocartography.

Files likely touched if runtime work is required:

- `moira_server/models/astrocartography.py`
- `moira_server/services/astrocartography.py`
- `moira_server/serializers/astrocartography.py`
- `tests/server/test_server_astrocartography_routes.py`

Preferred derivation for lines:

- Use `sky_position_at(...)` when it already owns the selected small-body
  apparent topocentric RA/Dec pipeline.
- Preserve `coordinate_source="chart_apparent_topocentric_ra_dec"` only if the
  path is genuinely apparent and topocentric for that subject.

Preferred derivation for subplanetary:

- Use a geocentric apparent ecliptic source, then convert to equatorial of date
  with the same obliquity used in the response provenance.
- Preserve `coordinate_source="chart_geocentric_ecliptic_to_equatorial"` only
  when this is exactly the derivation performed.

Required provenance additions if selected minor bodies are admitted:

- `subject_class`
- `canonical_body`
- `requested_body`
- `naif_id`
- `position_source`
- `kernel_source` or `reader_source`, when known
- `small_body_family` such as `asteroid` or `comet`

Implemented now:

- `subject_class`
- `canonical_name`
- `requested_label`
- `returned_label`
- `naif_id`
- `position_source`

Deferred:

- detailed kernel/source-reader provenance beyond the public position source

Decision:

- If provenance additions would break the existing response model, do not wedge
  them into generic chart provenance silently. Design explicit minor-body ACG
  response models or a provenance extension first.

Admission gate:

- Selected minor-body server-derived ACG is admitted only after tests prove the
  derivation and provenance for both supported products.

### 8.4 Slice D: Fixed-Star Derivation Audit

Status: Completed for current admission boundary; server-derived fixed-star
ACG remains deferred.

Goal:

- Decide whether fixed-star Astrocartography should remain direct-coordinate
  only or gain selected server-derived routes.

Files and code paths to audit:

- `moira.stars.star_at(...)`
- `moira_server.services.stars.compute_star_position(...)`
- `moira_server.serializers.stars.serialize_star(...)`
- `moira_server.models.stars.StarPositionResponse`
- `moira.coordinates.ecliptic_to_equatorial(...)`

Audit questions:

- Does the public star result expose RA/Dec directly? If not, can RA/Dec be
  derived from the returned ecliptic longitude/latitude and true obliquity
  without losing apparent-place truth?
- Is the star longitude/latitude at TT epoch an observed/apparent position, a
  true physical position, or policy-dependent?
- How are proper motion, parallax, light-time split, and catalog provenance
  represented?
- Does the REST star surface currently serialize enough provenance for ACG, or
  would Astrocartography need its own fixed-star provenance block?

Preferred first stance:

- Keep fixed-star ACG direct-coordinate only until the fixed-star apparent-place
  and RA/Dec derivation policy is written explicitly.

Possible later selected-star routes:

- `POST /v1/astrocartography/fixed-star/lines`
- `POST /v1/astrocartography/fixed-star/subplanetary`

These routes should accept selected names only. They must not accept an
unbounded catalog query.

Admission gate:

- Selected fixed-star server-derived ACG is admitted only after the star
  apparent-place policy, coordinate derivation, and provenance are explicit and
  tested.

### 8.5 Slice E: Transport Design For Any New Routes

Status: Not required for the completed slice.

Goal:

- If Slices B through D show that existing routes are insufficient, write a
  focused transport design before implementing routes.

Design artifact options:

- `docs/architecture/P10-01A_ASTROCARTOGRAPHY_MINOR_BODY_TRANSPORT_DESIGN.md`
- `docs/architecture/P10-01B_ASTROCARTOGRAPHY_FIXED_STAR_TRANSPORT_DESIGN.md`

Each design must declare:

- route names
- request models
- response models
- subject identity policy
- coordinate-source policy
- provenance fields
- maximum selected subjects
- kernel/catalog dependency behavior
- failure semantics for missing kernels or missing stars
- verification commands

Do not add public routes directly from this workflow document alone. This
workflow governs sequencing; route implementation needs a transport design.

### 8.6 Slice F: Documentation Truth Cleanup

Status: Completed for the current admission boundary.

Goal:

- Keep public and architecture docs aligned with the final admission decision.

Files likely touched:

- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `docs/architecture/P10-01_ASTROCARTOGRAPHY_TRANSPORT_DESIGN.md`
- `docs/architecture/POST_PHASE10_ASTROCARTOGRAPHY_RENDERING_ADAPTER_WORKFLOW.md`
- `wiki/02_services/REST_API_REFERENCE.md`
- `wiki/02_standards/ASTROCARTOGRAPHY_BACKEND_STANDARD.md`, if computation
  semantics change

Required final wording:

- Direct-coordinate selected minor-body/fixed-star support is either admitted
  and tested, or not claimed.
- Server-derived selected minor-body support is either admitted with provenance
  or explicitly deferred.
- Server-derived selected fixed-star support is either admitted with provenance
  or explicitly deferred.
- Catalog-wide sweeps remain deferred unless a separate async/bounded-output
  design admits them.
- Rendering adapter remains downstream.

### 8.7 Slice G: Final Verification And Admission Receipt

Status: Completed for the current admission boundary.

Required verification for direct-coordinate-only admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\\models\\astrocartography.py moira_server\\services\\astrocartography.py moira_server\\serializers\\astrocartography.py tests\\server\\test_server_astrocartography_routes.py
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_astrocartography_routes.py -q
```

Required additional verification if server-derived minor bodies are admitted:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_astrocartography_routes.py -q -m "network or requires_ephemeris"
```

Required additional verification if new routes are admitted:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_astrocartography_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_astrocartography.py tests/server/test_server_astrocartography_routes.py -q
```

Route registry audit:

- Confirm `/v1/astrocartography/*` route count stays at 4 for
  direct-coordinate-only admission.
- If new selected-subject routes are admitted, update the route count and REST
  reference only after route tests pass.

Final admission receipt must state:

- files changed
- admitted body classes
- deferred body classes
- whether any new routes were added
- verification actually run
- remaining dependency gaps, especially kernel or catalog availability

---

## 9. Completion Rule

This workflow is complete only when the documentation and tests can state one
of the following truthfully:

- direct-coordinate minor-body and fixed-star Astrocartography is supported,
  while server-derived support remains deferred; or
- direct-coordinate support is supported and selected server-derived support is
  partially admitted with explicit provenance and explicit deferrals; or
- direct-coordinate support is supported and selected server-derived
  minor-body/fixed-star support is fully admitted with explicit provenance; or
- a narrower stance is chosen and the REST reference says so plainly.

The rendering adapter must remain downstream of this decision. It may render
whatever Astrocartography lines are already admitted, but it must not become
the policy layer for minor bodies, fixed stars, or catalog sweeps.

---

## 10. Implementation Receipt

Implemented current admission boundary:

- direct-coordinate selected non-planet labels are admitted through the
  existing direct line and subplanetary routes
- selected asteroid chart-backed lines are admitted with subject provenance
- selected asteroid/comet chart-backed subplanetary points are admitted with
  subject provenance
- selected comet chart-backed lines are deferred because the public comet path
  rejects the topocentric RA/Dec mode required by chart-backed ACG lines
- server-derived fixed-star Astrocartography remains deferred
- no new public routes were added

Runtime files changed:

- `moira_server/models/astrocartography.py`
- `moira_server/services/astrocartography.py`
- `moira_server/serializers/astrocartography.py`
- `tests/server/test_server_astrocartography_routes.py`

Documentation files changed:

- `docs/architecture/P10-01_ASTROCARTOGRAPHY_TRANSPORT_DESIGN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/02_services/REST_API_REFERENCE.md`

Verification run:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\astrocartography.py moira_server\services\astrocartography.py moira_server\serializers\astrocartography.py tests\server\test_server_astrocartography_routes.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_astrocartography.py tests/server/test_server_astrocartography_routes.py -q
.\.venv\Scripts\python.exe -c "from moira_server.app import create_app; from moira_server.config import ServerConfig; app=create_app(ServerConfig(docs_enabled=False)); paths=sorted({route.path for route in app.routes if route.path.startswith('/v1/astrocartography')}); all_non_doc=[route for route in app.routes if getattr(route,'include_in_schema',True) and route.path not in {'/docs','/redoc','/openapi.json'}]; v1=[route for route in all_non_doc if route.path.startswith('/v1')]; print('astrocartography_routes', len(paths), paths); print('non_documentation_routes', len(all_non_doc)); print('versioned_v1_routes', len(v1))"
```

Observed verification result:

- 48 focused tests passed
- route registry remained at exactly four `/v1/astrocartography/*` routes
- total route counts remained 269 non-documentation routes and 265 versioned
  `/v1` routes
