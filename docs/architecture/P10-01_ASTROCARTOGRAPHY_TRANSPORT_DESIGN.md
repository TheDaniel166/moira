# P10-01 Astrocartography Transport Design

Version: 0.1
Date: 2026-06-11
Status: P10-01 admitted; four bounded routes live
Scope: Phase 10 Astrocartography REST admission design

This document declares the transport design for the first bounded
Astrocartography REST surface. The design has now been implemented as the
first P10-01 admission slice.

Astrocartography is a high-sensitivity spatial family. The REST surface must
not flatten frame truth, chart derivation, sampled geometry, or operational
bounds.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/02_standards/ASTROCARTOGRAPHY_BACKEND_STANDARD.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Authoritative engine module:

- `moira/astrocartography.py`

Authoritative engine vessels:

- `ACGLine`
- `SubPlanetaryPoint`

Authoritative engine functions:

- `acg_lines(...)`
- `acg_from_chart(...)`
- `subplanetary_points(...)`
- `subplanetary_from_chart(...)`

---

## 1. Route Family

Router prefix:

- `/v1/astrocartography`

Route tag:

- `astrocartography`

The first admission is deliberately narrow. It exposes bounded geographic line
and subplanetary point products only.

No dense map, contour, rendered image, tiled-map, atlas, or all-catalog sweep
route is admitted by this design.

---

## 2. Governing Products

### 2.1 ACG Lines

One body produces four line products:

- `MC`: one geographic meridian longitude
- `IC`: one geographic meridian longitude, antipodal to MC
- `ASC`: sampled geographic curve points
- `DSC`: sampled geographic curve points

The sampled ASC/DSC points are approximation samples, not a rendered map path
and not a topological contour product.

### 2.2 Subplanetary Points

One body produces two geographic point products:

- `Zenith`
- `Nadir`

The zenith latitude is WGS-84 geodetic latitude derived from the body's
geocentric declination. The nadir point is antipodal to the zenith point.

---

## 3. Transport Stance

First admission stance:

- `bounded_sync`

Reason:

- A bounded body list and bounded latitude sampling step produce modest
  response sizes.
- The product is inspectable as one response when body count and sampling are
  constrained.
- No background job or async workflow is needed for the first line/point
  products.

Do not admit:

- unbounded body lists
- catalog-wide fixed-star ACG
- rendered maps
- dense geographic grids
- contour extraction
- map tile generation
- route-level projection into Web Mercator or other display frames

Those are different operational products and require separate async or bounded
map-product design.

---

## 4. Shared Request Policy

All P10-01 routes must validate:

- body names are non-empty
- body count is bounded
- numeric inputs are finite
- declination is in `[-90, 90]`
- latitude sampling step is finite and bounded
- datetime inputs are timezone-aware
- observer latitude is in `(-90, 90)` when supplied
- observer longitude is in `[-180, 180]` when supplied

Recommended first REST bounds:

- maximum bodies: `12`
- default `lat_step`: `2.0`
- minimum `lat_step`: `0.5`
- maximum `lat_step`: `10.0`

Reason:

- `lat_step=2.0` yields roughly 90 latitude samples per ASC/DSC curve.
- `lat_step=0.5` is already a materially larger output and should be the
  first-admission lower bound.
- Values finer than `0.5` belong to a later heavy-output route or async job.

The engine-level guard allows a broader mathematical range. REST should use
stricter operational bounds.

---

## 5. Provenance Contract

Every chart-backed response must include a provenance block.

Minimum provenance fields:

- `requested_datetime`
- `normalized_datetime_utc`
- `jd_ut`
- `jd_tt`
- `gmst_deg`
- `obliquity_deg`
- `nutation_longitude_deg`
- `requested_bodies`
- `returned_bodies`
- `observer`
- `coordinate_source`
- `stage_sequence`

Observer provenance:

- `latitude`
- `longitude`
- `elevation_m`
- whether observer was caller-supplied or chart-derived

Coordinate-source values:

- `direct_ra_dec`
- `chart_apparent_topocentric_ra_dec`
- `chart_geocentric_ecliptic_to_equatorial`

Required stage sequences:

Direct line route:

```text
direct_ra_dec_validation
sidereal_time_validation
sampling_policy_validation
acg_line_computation
response_materialization
```

Chart-backed line route:

```text
datetime_validation
chart_context_derivation
observer_policy_resolution
apparent_sidereal_time_derivation
body_ra_dec_derivation
sampling_policy_validation
acg_line_computation
response_materialization
```

Direct subplanetary route:

```text
direct_ra_dec_validation
sidereal_time_validation
subplanetary_point_computation
response_materialization
```

Chart-backed subplanetary route:

```text
datetime_validation
chart_context_derivation
apparent_sidereal_time_derivation
geocentric_ecliptic_position_derivation
ecliptic_to_equatorial_conversion
subplanetary_point_computation
response_materialization
```

---

## 6. Observer Doctrine

Astrocartography has two different chart-backed observer situations. They must
not be collapsed.

### 6.1 Chart-Derived Observer

If no explicit observer override is supplied, chart-backed line routes use the
chart request observer fields:

- `observer_lat`
- `observer_lon`
- `observer_elev_m`

This matches the existing chart-backed pattern and the current
`acg_from_chart(...)` behavior.

### 6.2 Observer Override

Line routes may accept an explicit observer override:

- `acg_observer_lat`
- `acg_observer_lon`
- `acg_observer_elev_m`

If admitted, this override must be named distinctly from the chart birth
observer. It changes apparent RA/Dec derivation for topocentric handling.

Do not silently reuse a relocated observer without exposing that fact in
provenance.

### 6.3 Subplanetary Observer

Subplanetary points do not use a terrestrial observer location. They are
defined by the body's apparent geocentric direction and Greenwich apparent
sidereal time.

Chart-backed subplanetary routes should not require observer latitude or
longitude.

---

## 7. Route Shapes

### 7.1 Direct ACG Lines

Route:

- `POST /v1/astrocartography/lines`

Transport stance:

- `bounded_sync`

Purpose:

- Compute ACG lines from caller-owned apparent RA/Dec and Greenwich apparent
  sidereal time.

Input:

- `positions`: map of body name to RA/Dec object
- `gmst_deg`
- optional `lat_step`
- optional `jd_ut`
- optional `refraction`

Request body shape:

```json
{
  "positions": {
    "Sun": {"right_ascension": 100.0, "declination": 10.0}
  },
  "gmst_deg": 20.0,
  "lat_step": 2.0,
  "jd_ut": 2451545.0,
  "refraction": false
}
```

Truth boundary:

- The caller owns the supplied RA/Dec and sidereal-time truth.
- The server validates and transports those values.
- The server does not reinterpret direct RA/Dec as chart-derived.

Engine path:

- `moira.astrocartography.acg_lines(...)`

Response:

- list of `ACGLine` responses
- provenance block with `coordinate_source="direct_ra_dec"`

### 7.2 Chart-Backed ACG Lines

Route:

- `POST /v1/astrocartography/chart/lines`

Transport stance:

- `bounded_sync`

Purpose:

- Build a chart through the stable server engine, derive apparent RA/Dec for
  selected bodies, derive Greenwich apparent sidereal time, and compute ACG
  lines.

Input:

- `dt`
- optional `bodies`
- optional chart observer fields:
  - `observer_lat`
  - `observer_lon`
  - `observer_elev_m`
- optional explicit ACG observer override:
  - `acg_observer_lat`
  - `acg_observer_lon`
  - `acg_observer_elev_m`
- optional `lat_step`
- optional `refraction`

Truth boundary:

- The server owns chart construction, sidereal-time derivation, and apparent
  RA/Dec derivation.
- The response must expose observer policy and coordinate-source provenance.

Engine path:

1. Build chart through the stable injected `Moira` instance.
2. Resolve observer policy.
3. Derive `jd_tt`, nutation, true obliquity, and Greenwich apparent sidereal
   time.
4. Derive apparent RA/Dec for each selected body through the same public sky
   position surface used by the engine/facade.
5. Call `acg_lines(...)`.

Response:

- list of `ACGLine` responses
- provenance block with `coordinate_source="chart_apparent_topocentric_ra_dec"`

### 7.3 Direct Subplanetary Points

Route:

- `POST /v1/astrocartography/subplanetary`

Transport stance:

- `bounded_sync`

Purpose:

- Compute zenith/nadir geographic points from caller-owned apparent RA/Dec and
  Greenwich apparent sidereal time.

Input:

- `positions`: map of body name to RA/Dec object
- `gmst_deg`

Truth boundary:

- The caller owns the supplied RA/Dec and sidereal-time truth.

Engine path:

- `moira.astrocartography.subplanetary_points(...)`

Response:

- list of `SubPlanetaryPoint` responses
- provenance block with `coordinate_source="direct_ra_dec"`

### 7.4 Chart-Backed Subplanetary Points

Route:

- `POST /v1/astrocartography/chart/subplanetary`

Transport stance:

- `bounded_sync`

Purpose:

- Build a chart through the stable server engine and compute zenith/nadir
  points for selected bodies.

Input:

- `dt`
- optional `bodies`

Truth boundary:

- The server owns chart construction, sidereal-time derivation, ecliptic
  position derivation, and ecliptic-to-equatorial conversion.
- No terrestrial observer is required for this product.

Engine path:

1. Build chart through the stable injected `Moira` instance.
2. Derive `jd_tt`, nutation, true obliquity, and Greenwich apparent sidereal
   time.
3. Derive each selected body's geocentric ecliptic longitude/latitude through
   the admitted `planet_at(...)` path.
4. Convert to equatorial RA/Dec of date.
5. Call `subplanetary_points(...)`.

Response:

- list of `SubPlanetaryPoint` responses
- provenance block with
  `coordinate_source="chart_geocentric_ecliptic_to_equatorial"`

---

## 8. Response Models

### 8.1 ACG Position Input Echo

Direct responses should not echo all input positions by default. Provenance
may include only:

- returned body names
- coordinate source
- sidereal time
- sampling policy

If a diagnostic route later needs full input echo, it must be designed
separately.

### 8.2 ACG Line Response

Fields:

- `planet`
- `line_type`
- `longitude`
- `points`

Point shape:

- `latitude`
- `longitude`

Rules:

- `MC` and `IC` responses must have `longitude` and empty `points`.
- `ASC` and `DSC` responses must have `longitude=null` and non-empty `points`
  unless a high-declination body has no valid samples.
- Do not encode sampled points as anonymous two-item arrays in transport.
  Use named `latitude` and `longitude` fields.

### 8.3 Subplanetary Point Response

Fields:

- `planet`
- `point_type`
- `latitude`
- `longitude`

Rules:

- `point_type` is `Zenith` or `Nadir`.
- Coordinates are geographic degrees.
- Longitude is wrapped to `[-180, 180)`.

### 8.4 Response Envelopes

Line response:

- `lines`
- `provenance`

Subplanetary response:

- `points`
- `provenance`

Do not bundle subplanetary points into the line response unless a later
combined route is explicitly admitted.

---

## 9. Transport Models To Add During Implementation

Recommended files:

- `moira_server/models/astrocartography.py`
- `moira_server/services/astrocartography.py`
- `moira_server/serializers/astrocartography.py`
- `moira_server/routers/astrocartography.py`
- `tests/server/test_server_astrocartography_routes.py`

Model candidates:

- `AstrocartographyCoordinateRequest`
- `AstrocartographyDirectLinesRequest`
- `AstrocartographyChartLinesRequest`
- `AstrocartographyDirectSubplanetaryRequest`
- `AstrocartographyChartSubplanetaryRequest`
- `AstrocartographyPointResponse`
- `AstrocartographyLineResponse`
- `AstrocartographyProvenanceResponse`
- `AstrocartographyLinesResponse`
- `AstrocartographySubplanetaryResponse`

Service result candidates:

- `AstrocartographyProvenance`
- `AstrocartographyLinesResult`
- `AstrocartographySubplanetaryResult`

---

## 10. Serializer Contract

Serializers must map engine vessels explicitly:

- `ACGLine.planet`
- `ACGLine.line_type`
- `ACGLine.longitude`
- `ACGLine.points`
- `SubPlanetaryPoint.planet`
- `SubPlanetaryPoint.point_type`
- `SubPlanetaryPoint.latitude`
- `SubPlanetaryPoint.longitude`

Do not serialize via `__dict__`.

Do not convert sampled points into GeoJSON in first admission. GeoJSON is a map
interchange format and would imply projection/rendering semantics not admitted
by this transport design.

---

## 11. Required Validation

Direct routes must reject:

- empty positions map
- empty body name
- non-finite RA
- non-finite Dec
- Dec outside `[-90, 90]`
- non-finite `gmst_deg`
- non-finite `lat_step`
- `lat_step < 0.5`
- `lat_step > 10.0`
- body count greater than the route maximum

Chart-backed routes must reject:

- naive datetime
- unsupported body names
- empty body list
- body count greater than the route maximum
- non-finite observer values
- observer latitude outside `(-90, 90)` when observer is supplied
- observer longitude outside `[-180, 180]` when observer is supplied
- partial ACG observer override, if override fields are admitted

Refraction:

- first admission may expose `refraction: bool`
- default must be `false`
- response provenance must record the requested refraction flag

---

## 12. Required Tests

Add:

- `tests/server/test_server_astrocartography_routes.py`

Required parity tests:

- direct line route matches `acg_lines(...)`
- chart-backed line route matches service derivation and `acg_lines(...)`
- direct subplanetary route matches `subplanetary_points(...)`
- chart-backed subplanetary route matches service derivation and
  `subplanetary_points(...)`

Required structural tests:

- one body returns four line records
- MC/IC responses carry longitude and no points
- ASC/DSC responses carry points and no longitude
- one body returns Zenith and Nadir point records
- provenance records coordinate source and stage sequence
- route registration appears in the app route registry

Required adversarial tests:

- naive datetime is rejected
- unsupported chart body is rejected
- empty direct position map is rejected
- invalid `lat_step` is rejected
- non-finite direct RA/Dec is rejected
- Dec outside `[-90, 90]` is rejected
- non-finite `gmst_deg` is rejected
- too many bodies are rejected
- partial observer override is rejected

Suggested implementation verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\astrocartography.py moira_server\services\astrocartography.py moira_server\serializers\astrocartography.py moira_server\routers\astrocartography.py tests\server\test_server_astrocartography_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_astrocartography_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_astrocartography.py tests\server\test_server_astrocartography_routes.py -q
```

Before declaring P10-01 admitted, run the route registry audit and update
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 13. Explicit Non-Goals

P10-01 first admission does not expose:

- dense map grids
- rendered maps
- tile generation
- contour extraction
- GeoJSON route variants
- all fixed-star catalog sweeps
- all asteroid catalog sweeps
- relocation chart synthesis
- local-space positions
- geodetic equivalents
- Gauquelin sectors
- galactic coordinates or galactic houses

Those products require their own Phase 10 design records or later spatial
transport primitives.

---

## 14. Admission Decision

P10-01 is admitted.

The first implementation admits exactly these four routes:

- `POST /v1/astrocartography/lines`
- `POST /v1/astrocartography/chart/lines`
- `POST /v1/astrocartography/subplanetary`
- `POST /v1/astrocartography/chart/subplanetary`

No additional Astrocartography routes were admitted during first implementation.

Admission verification:

- `python -m py_compile` over the Astrocartography transport models, services,
  serializers, router, app wiring, package exports, and route tests.
- `python -m pytest tests/server/test_server_astrocartography_routes.py -q`
- `python -m pytest tests/unit/test_astrocartography.py tests/server/test_server_astrocartography_routes.py -q`
- Route registry audit after admission: 251 non-documentation routes, 247
  versioned `/v1` routes, and exactly 4 `/v1/astrocartography/*` routes.
