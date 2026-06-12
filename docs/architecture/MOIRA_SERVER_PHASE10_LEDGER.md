# Moira Server Phase 10 Evaluation Ledger

Version: 0.8
Date: 2026-06-12
Status: P10-01 through P10-04 admitted; remaining Phase 10 families under evaluation
Scope: Spatial and Earth-facing mapping REST candidate evaluation

Phase 10 covers spatial, geographic, and frame-transform surfaces. These
families are closer to the astronomical substrate than most Phase 9 doctrine
families. Their REST admission must preserve coordinate frame truth,
observer/location semantics, result-size boundaries, and validation provenance.

This ledger records Phase 10 evaluation status and the admitted
Astrocartography, Local Space, Geodetic, and Galactic Coordinates transport
slices. It does not broaden the remaining Phase 10 families beyond their
evaluation state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`
- `wiki/03_validation/VALIDATION_ASTROLOGY.md`

---

## 1. Phase 10 Boundary

Candidate modules:

- `moira.astrocartography`
- `moira.local_space`
- `moira.geodetic`
- `moira.galactic`
- `moira.galactic_houses`
- `moira.gauquelin`

Candidate route families later:

- `/v1/astrocartography/*`
- `/v1/local-space/*`
- `/v1/geodetic/*`
- `/v1/galactic/*`
- `/v1/gauquelin/*`

Phase 10 must distinguish:

- geographic positions from celestial positions
- ecliptic, equatorial, galactic, horizontal, and geodetic frames
- line products from sampled curves
- bounded single-chart outputs from dense map/grid products
- direct caller-owned inputs from chart-backed server-derived inputs

---

## 2. Current Evaluation Summary

| Unit | Engine family | Status | Reason |
|---|---|---|---|
| P10-01 | Astrocartography | `admitted` | Four bounded line/subplanetary routes are live with direct and chart-backed shapes, explicit provenance, sampled-curve bounds, route tests, and route-count audit; dense map/grid products remain deferred. |
| P10-02 | Local Space | `admitted` | Two bounded direct/chart-backed horizon-position routes are live with explicit observer, LST, RA/Dec provenance, route tests, and route-count audit; rendered compass charts, map products, projection products, and catalog sweeps remain deferred. |
| P10-03 | Geodetic | `admitted` | Four bounded direct/chart-backed location-chart and equivalent-longitude routes are live with explicit zodiac and ayanamsa provenance, route tests, and route-count audit; primitive helper routes, map products, projection products, geographic search, relocation synthesis, and catalog sweeps remain deferred. |
| P10-04 | Galactic Coordinates | `admitted` | Six bounded raw-transform, reference-point, and chart-backed galactic position routes are live with explicit frame, epoch, body, and stage provenance; galactic houses, maps, projections, catalog sweeps, and proper-motion products remain deferred. |
| P10-05 | Galactic Houses | `admit_after_minor_engine_work` | Public vessels and tests exist, but REST admission needs explicit route doctrine for Galactic Porphyry angles, cusp membership, and boundary profiles. |
| P10-06 | Gauquelin Sectors | `admit_after_minor_engine_work` | Core sector vessel and external-reference validation exist, but REST admission needs an apparent RA/Dec/LST derivation contract and clear handling for circumpolar/never-rises statuses. |

P10-01 is admitted as a narrow synchronous line/point product family. P10-02 is
admitted as a narrow synchronous observer-local horizon-position family. P10-03
is admitted as a narrow synchronous geodetic chart/equivalent family. P10-04 is
admitted as a narrow synchronous galactic coordinate-frame family. The remaining
Phase 10 families still need family-specific
backend-standard packets and transport designs before route work.

---

## 3. Shared Pre-Route Work

Before any Phase 10 router work, create a shared spatial transport design that
answers:

- how chart-backed routes obtain apparent RA/Dec, ecliptic longitude/latitude,
  JD, LST, obliquity, and observer truth
- which routes may use existing `ChartContext` directly
- which routes need a compact provenance block
- how large sampled outputs are bounded
- which frame labels are serialized for every result family

This should be a design document only at first, likely:

- `docs/architecture/PHASE10_SPATIAL_TRANSPORT_PRIMITIVES.md`

It should not replace engine computation. It should only define how the server
will expose existing spatial truth without flattening frames.

---

## 4. P10-01 Astrocartography

Status: `admitted`

Governing object:

- Astrocartography line products: MC/IC meridians, ASC/DSC sampled curves, and
  subplanetary points.

Evidence:

- Engine module: `moira/astrocartography.py`
- Backend standard: `wiki/02_standards/ASTROCARTOGRAPHY_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P10-01_ASTROCARTOGRAPHY_TRANSPORT_DESIGN.md`
- Public surfaces include `ACGLine`, `SubPlanetaryPoint`, `acg_lines`,
  `acg_from_chart`, `subplanetary_points`, and `subplanetary_from_chart`.
- Facade support exists through `SpatialFacadeMixin.astrocartography(...)`.
- Unit tests exist: `tests/unit/test_astrocartography.py`.
- Validation index records Astrocartography as validated in
  `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`.

Readiness:

- The bounded line-product surface is close to REST admission.
- Dense grids, contour extraction, tiled maps, or rendered map products should
  remain deferred until an async/bounded-output policy exists.

Required before implementation:

- Completed. The live surface implements only the four routes declared by the
  transport design.
- Explicit request/response models, serializers, services, and router were
  added under `moira_server`.
- Focused parity, structural, adversarial, and route-registration tests were
  added in `tests/server/test_server_astrocartography_routes.py`.
- The REST reference was updated after route tests and route-count audit passed.
- Dense grids, rendered maps, tiled maps, contour extraction, and all-catalog
  fixed-star sweeps remain deferred.

Live routes:

- `POST /v1/astrocartography/lines`
- `POST /v1/astrocartography/chart/lines`
- `POST /v1/astrocartography/subplanetary`
- `POST /v1/astrocartography/chart/subplanetary`

Admission verification:

- `python -m py_compile` over the new models, services, serializers, router,
  route exports, app wiring, and route tests.
- `python -m pytest tests/server/test_server_astrocartography_routes.py -q`
- `python -m pytest tests/unit/test_astrocartography.py tests/server/test_server_astrocartography_routes.py -q`
- Route registry audit after admission: 251 non-documentation routes, 247
  versioned `/v1` routes, and exactly 4 `/v1/astrocartography/*` routes.

Recommended first transport stance:

- synchronous for bounded line products
- no dense map/grid route in first admission

---

## 5. P10-02 Local Space

Status: `admitted`

Governing object:

- Observer-local horizon positions: azimuth, altitude, compass direction, and
  above-horizon state.

Evidence:

- Engine module: `moira/local_space.py`
- Backend standard: `wiki/02_standards/LOCAL_SPACE_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P10-02_LOCAL_SPACE_TRANSPORT_DESIGN.md`
- Public surfaces include `LocalSpacePosition`, `local_space_positions`, and
  `local_space_from_chart`.
- Facade support exists through `SpatialFacadeMixin.local_space(...)`.
- Unit tests exist: `tests/unit/test_local_space.py`.

Readiness:

- The core result vessel is REST-shaped and bounded.
- The first admission should expose both direct RA/Dec/LST and chart-backed
  datetime/observer route shapes.
- Direct input guards now reject non-finite latitude, LST, RA/Dec, invalid
  declination, and empty body names.

Required before implementation:

- Completed. Local Space backend-standard/admission packet exists.
- Completed. Apparent RA/Dec provenance for chart-backed routes is declared.
- Completed. Observer coordinate validation and LST provenance are declared.
- Completed. First admission does not expose a refraction flag; altitude remains
  the engine's unrefracted horizon altitude unless a later design changes that
  explicitly.
- Completed. The live surface implements only the two routes declared by the
  transport design.
- Explicit request/response models, serializers, services, and router were
  added under `moira_server`.
- Focused direct parity, chart-backed parity, adversarial, and
  route-registration tests were added in
  `tests/server/test_server_local_space_routes.py`.
- The REST reference was updated after route tests and route-count audit passed.

Live routes:

- `POST /v1/local-space/positions`
- `POST /v1/local-space/chart/positions`

Admission verification:

- `python -m py_compile` over the new models, services, serializers, router,
  route exports, app wiring, and route tests.
- `python -m pytest tests/server/test_server_local_space_routes.py -q`
- `python -m pytest tests/unit/test_local_space.py tests/server/test_server_local_space_routes.py -q`
- Route registry audit after admission: 253 non-documentation routes, 249
  versioned `/v1` routes, and exactly 2 `/v1/local-space/*` routes.

Recommended first transport stance:

- synchronous
- direct and chart-backed shapes, both provenance-explicit

---

## 6. P10-03 Geodetic

Status: `admitted`

Governing object:

- Geodetic MC/ASC, location-native geodetic chart, and planet-to-geographic
  equivalent longitudes.

Evidence:

- Engine module: `moira/geodetic.py`
- Backend standard: `wiki/02_standards/GEODETIC_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P10-03_GEODETIC_TRANSPORT_DESIGN.md`
- Public surfaces include `GeodeticChart`, `geodetic_mc`, `geodetic_asc`,
  `geodetic_chart`, `geodetic_chart_from_chart`, `geodetic_equivalents`, and
  `geodetic_equivalents_from_chart`.
- Facade support exists through `SpatialFacadeMixin.geodetic(...)` and
  `SpatialFacadeMixin.geodetic_planet_equivalents(...)`.
- Unit tests exist: `tests/unit/test_geodetic.py`.

Readiness:

- Direct and chart-backed geodetic chart routes are bounded.
- Direct and chart-backed equivalent routes are bounded by body count.
- Zodiac policy and ayanamsa provenance are declared.
- Primitive `geodetic_mc` and `geodetic_asc` helper routes are deferred; first
  admission should expose chart/equivalent products only.
- Engine input guards now reject non-finite geographic coordinates, obliquity,
  ayanamsa, invalid zodiac, empty equivalent body names, and non-finite
  equivalent longitudes.

Required before implementation:

- Completed. Geodetic backend-standard/admission packet exists.
- Completed. Tropical vs sidereal policy serialization is declared.
- Completed. Primitive `geodetic_mc` and `geodetic_asc` routes are deferred.
- Completed. Ayanamsa provenance for sidereal geodetic chart/equivalent
  products is declared.
- Completed. The live surface implements only the four routes declared by the
  transport design.
- Explicit request/response models, serializers, services, and router were
  added under `moira_server`.
- Focused direct parity, chart-backed parity, adversarial, and
  route-registration tests were added in
  `tests/server/test_server_geodetic_routes.py`.
- The REST reference was updated after route tests and route-count audit passed.

Live routes:

- `POST /v1/geodetic/location-chart`
- `POST /v1/geodetic/chart/location-chart`
- `POST /v1/geodetic/equivalents`
- `POST /v1/geodetic/chart/equivalents`

Admission verification:

- `python -m py_compile` over the new models, services, serializers, router,
  route exports, app wiring, and route tests.
- `python -m pytest tests/server/test_server_geodetic_routes.py -q`
- `python -m pytest tests/unit/test_geodetic.py tests/server/test_server_geodetic_routes.py -q`
- Route registry audit after admission: 257 non-documentation routes, 253
  versioned `/v1` routes, and exactly 4 `/v1/geodetic/*` routes.

Recommended first transport stance:

- synchronous
- expose chart/equivalents before primitive math helpers unless primitive
  routes are explicitly needed

---

## 7. P10-04 Galactic Coordinates

Status: `admitted`

Governing object:

- IAU galactic coordinate transforms, chart-body galactic positions, and
  galactic reference points.

Evidence:

- Engine module: `moira/galactic.py`
- Public surfaces include `GalacticPosition`, `equatorial_to_galactic`,
  `galactic_to_equatorial`, `ecliptic_to_galactic`,
  `galactic_to_ecliptic`, `galactic_position_of`,
  `all_galactic_positions`, and `galactic_reference_points`.
- `moira.sky.galactic` re-exports the galactic engine surface.
- Integration oracle tests exist:
  `tests/integration/test_galactic_oracle_reference.py`.
- Input-guard unit tests exist: `tests/unit/test_galactic.py`.
- Validation index records galactic transforms and reference points as
  validated in `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`.
- Backend-standard packet exists:
  `wiki/02_standards/GALACTIC_BACKEND_STANDARD.md`.
- Transport design exists:
  `docs/architecture/P10-04_GALACTIC_COORDINATES_TRANSPORT_DESIGN.md`.
- Live transport files exist under `moira_server/models/galactic.py`,
  `moira_server/services/galactic.py`,
  `moira_server/serializers/galactic.py`, and
  `moira_server/routers/galactic.py`.
- Route tests exist: `tests/server/test_server_galactic_routes.py`.

Readiness:

- The mathematical frame is strong, input hygiene has been hardened, and the
  REST surface now has separate live raw-transform, chart-position, and
  reference-point schemas.

Resolved for transport design:

- Galactic backend-standard/admission packet written.
- Raw transform routes are separated from chart-backed position routes.
- Frame labels are preserved: ecliptic true-of-date, equatorial J2000/ICRS,
  galactic IAU 1958, and epoch/JD fields.
- `moira.galactic` is the documented REST authority; `moira.sky.galactic`
  remains a re-export surface.

Recommended first implementation stance:

- synchronous
- bounded raw transforms, reference points, and chart-body galactic positions
- no galactic houses, rendered maps, catalog sweeps, fixed-star proper-motion
  products, or projection helpers in P10-04

Live routes:

- `POST /v1/galactic/equatorial-to-galactic`
- `POST /v1/galactic/galactic-to-equatorial`
- `POST /v1/galactic/ecliptic-to-galactic`
- `POST /v1/galactic/galactic-to-ecliptic`
- `POST /v1/galactic/reference-points`
- `POST /v1/galactic/chart/positions`

Admission verification:

- `python -m py_compile` over the new models, services, serializers, router,
  route exports, app wiring, and route tests.
- `python -m pytest tests/unit/test_galactic.py tests/server/test_server_galactic_routes.py -q`
- Route registry audit after admission: 263 non-documentation routes, 259
  versioned `/v1` routes, and exactly 6 `/v1/galactic/*` routes.

---

## 8. P10-05 Galactic Houses

Status: `admit_after_minor_engine_work`

Governing object:

- Galactic Porphyry angles, cusp sets, body-house placement, and boundary
  profiles.

Evidence:

- Engine module: `moira/galactic_houses.py`
- Public surfaces include `GalacticAngles`, `GalacticHouseCusps`,
  `GalacticHousePlacement`, `GalacticHouseBoundaryProfile`,
  `calculate_galactic_houses`, `assign_galactic_house`,
  `body_galactic_house_position`, and `describe_galactic_boundary`.
- Root package exports include `calculate_galactic_houses`.
- Unit tests exist:
  `tests/unit/test_galactic_houses.py` and
  `tests/unit/test_galactic_houses_public_api.py`.

Readiness:

- The engine has a strong governing object and result vessels.
- REST admission should follow Galactic Coordinates because it depends on
  those frame semantics.

Required before transport design:

- Write or identify a Galactic Houses backend-standard/admission packet.
- Define chart-time/location request truth and observer validation.
- Decide whether body-house placement is chart-backed in first admission or
  direct from supplied galactic/ecliptic body position.
- Preserve both galactic and ecliptic cusp truth in responses.

Recommended first transport stance:

- synchronous
- admit after P10-04 Galactic Coordinates admission

---

## 9. P10-06 Gauquelin Sectors

Status: `admit_after_minor_engine_work`

Governing object:

- Gauquelin sector placement, plus-zone classification, degree-in-sector, and
  horizon status.

Evidence:

- Engine module: `moira/gauquelin.py`
- Public surfaces include `GauquelinHorizonStatus`, `GauquelinPosition`,
  `gauquelin_sector`, and `all_gauquelin_sectors`.
- Facade support exists through `SpatialFacadeMixin.gauquelin_sectors(...)`.
- External-reference validation exists:
  `tests/integration/test_gauquelin_external_reference.py`.
- Validation index records Gauquelin external reference checks in
  `wiki/03_validation/VALIDATION_ASTROLOGY.md`.

Readiness:

- The direct sector engine is bounded and result-shaped.
- Chart-backed REST requires a careful apparent RA/Dec and LST derivation
  contract.

Required before transport design:

- Write or identify a Gauquelin backend-standard/admission packet.
- Define direct input route shape for RA/Dec/LST.
- Define chart-backed input route shape only after the shared spatial
  derivation design exists.
- Preserve `horizon_status` explicitly; do not collapse circumpolar or
  never-rises cases into ordinary sector errors.
- Decide whether custom sector counts are admitted or canonical 36-sector
  mode is first.

Recommended first transport stance:

- synchronous for direct sector and bounded all-body sector products
- chart-backed route after shared spatial derivation primitives are designed

---

## 10. Proposed Evaluation Order

Recommended Phase 10 sequence:

1. P10-01 Astrocartography bounded line products.
2. P10-02 Local Space.
3. P10-03 Geodetic.
4. P10-04 Galactic Coordinates.
5. P10-05 Galactic Houses.
6. P10-06 Gauquelin Sectors.

Reason:

- Astrocartography is already called out as the first Phase 10 line-product
  surface in the full exposure plan.
- Local Space and Geodetic are bounded observer/location products.
- Galactic Coordinates should precede Galactic Houses because it owns the
  underlying frame.
- Gauquelin should wait until apparent RA/Dec/LST derivation policy is explicit.

---

## 11. Post-Phase-10 Rendering Convenience Operation

After the Phase 10 computational families are admitted, Moira may add a
separate rendering-convenience operation for Astrocartography map clients.

This must be treated as a map-adapter layer, not as a new astronomical
computation and not as an implicit widening of P10-01.

Permitted scope:

- consume existing `ACGLine` vessels or the admitted Astrocartography REST line
  response shape
- split sampled ASC/DSC curves at antimeridian crossings for browser map
  rendering
- normalize point order and longitude representation for stable map drawing
- materialize MC/IC meridians as explicit render primitives
- attach line-type/body style hints that do not change computational meaning
- preserve the original Astrocartography provenance block without reducing it

Forbidden scope without a separate admission design:

- new public computation routes
- GeoJSON route variants
- Web Mercator or other projection ownership
- rendered maps
- tile generation
- dense grids
- contour extraction
- catalog-wide fixed-star or asteroid sweeps
- async heavy-output workflows

Recommended artifact:

- `docs/architecture/POST_PHASE10_ASTROCARTOGRAPHY_RENDERING_ADAPTER_WORKFLOW.md`

Recommended implementation stance:

- start as an internal serializer/helper or website adapter
- keep computational truth in `moira.astrocartography`
- keep REST truth in the four admitted P10-01 routes
- prove adapter behavior with structural tests for dateline splitting,
  meridian materialization, provenance preservation, and stable render primitive
  ordering

Admission rule:

- A rendering adapter may make maps easier to draw, but it must not claim to be
  a map product, tile product, contour product, GeoJSON authority, or new
  Astrocartography computation unless a later design admits that product
  explicitly.

---

## 12. Explicit Non-Goals For Evaluation

The remaining Phase 10 evaluation does not:

- add REST routes
- create request or response models
- introduce async job infrastructure
- add map rendering
- expose dense grid or tiled map products
- change astronomical engine computation
- change validation baselines

---

## 13. Evaluation Result

Phase 10 is proceeding family by family. P10-01 through P10-04 have completed
transport design and first-route implementation; the remaining Phase 10
families are still at evaluation.

The shared spatial transport primitive artifact is still recommended before
later families that depend on apparent RA/Dec, LST, or frame-bridging policy:

- `docs/architecture/PHASE10_SPATIAL_TRANSPORT_PRIMITIVES.md`

For P10-01 specifically, any next step is a separate expansion design, not an
implicit widening of the admitted surface. Expansion candidates include:

- async/heavy map products
- dense grids
- contours
- rendered/tiled maps
- catalog-wide fixed-star sweeps
