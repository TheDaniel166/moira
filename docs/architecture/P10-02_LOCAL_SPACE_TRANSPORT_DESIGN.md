# P10-02 Local Space Transport Design

Version: 0.1
Date: 2026-06-12
Status: P10-02 admitted; two bounded routes live
Scope: Phase 10 Local Space REST admission design

This document declares the transport design for the first bounded Local Space
REST surface. The design has now been implemented as the first P10-02
admission slice.

Local Space is a high-sensitivity observer-local horizon family. The REST
surface must not flatten apparent RA/Dec truth, observer location, local
sidereal time, altitude semantics, or compass-direction semantics.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/02_standards/LOCAL_SPACE_BACKEND_STANDARD.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Authoritative engine module:

- `moira/local_space.py`

Authoritative engine vessel:

- `LocalSpacePosition`

Authoritative engine functions:

- `local_space_positions(...)`
- `local_space_from_chart(...)`

---

## 1. Route Family

Router prefix:

- `/v1/local-space`

Route tag:

- `local-space`

First admission routes:

- `POST /v1/local-space/positions`
- `POST /v1/local-space/chart/positions`

The first admission is deliberately narrow. It exposes bounded horizon
azimuth/altitude products only.

No rendered compass chart, map, projection, SVG, raster, relocation synthesis,
or unbounded catalog route is admitted by this design.

---

## 2. Governing Product

One body produces one Local Space position:

- body name
- azimuth, navigational convention, North at `0` degrees
- altitude, signed degrees above or below the horizon
- above-horizon boolean
- 8-point compass direction

The response is an observer-local horizon product. It is not an ecliptic chart,
not a house system, not a visual map, and not a relocation chart.

---

## 3. Transport Stance

First admission stance:

- `bounded_sync`

Reason:

- A bounded body list produces a compact result.
- The product is one position per body.
- No background job or async workflow is needed for the first horizon-position
  product.

Do not admit:

- unbounded body lists
- catalog-wide fixed-star Local Space
- rendered charts
- map projection products
- SVG or raster outputs
- relocation synthesis

---

## 4. Shared Request Policy

All P10-02 routes must validate:

- body names are non-empty
- body count is bounded
- numeric inputs are finite
- declination is in `[-90, 90]`
- observer latitude is in `(-90, 90)` for REST chart-backed routes
- observer longitude is in `[-180, 180]`
- datetime inputs are timezone-aware

Recommended first REST bounds:

- maximum bodies: `12`

Reason:

- one response row per body is modest, but bounded body lists prevent accidental
  catalog-style route use.
- chart-backed routes may trigger ephemeris calls per body and should remain
  visibly bounded.

---

## 5. Provenance Contract

Every response must include a provenance block.

Minimum provenance fields:

- `requested_datetime`
- `normalized_datetime_utc`
- `jd_ut`
- `jd_tt`
- `lst_deg`
- `observer`
- `requested_bodies`
- `returned_bodies`
- `coordinate_source`
- `stage_sequence`

Observer provenance:

- `latitude`
- `longitude`
- `elevation_m`
- whether observer was direct caller-supplied or chart-request supplied

Coordinate-source values:

- `direct_ra_dec`
- `chart_apparent_topocentric_ra_dec`

Required stage sequences:

Direct route:

```text
direct_ra_dec_validation
observer_latitude_validation
local_sidereal_time_validation
local_space_computation
response_materialization
```

Chart-backed route:

```text
datetime_validation
chart_context_derivation
observer_policy_validation
local_sidereal_time_derivation
body_ra_dec_derivation
local_space_computation
response_materialization
```

---

## 6. Observer Doctrine

Local Space is explicitly observer-local.

Direct route:

- requires observer `latitude`
- requires caller-owned `lst_deg`
- does not require longitude because LST already carries longitude/time truth

Chart-backed route:

- requires observer latitude and longitude
- may accept observer elevation
- derives LST from chart `jd_ut`, nutation, true obliquity, and observer
  longitude
- derives apparent RA/Dec through the server's admitted sky-position path for
  the same observer

The chart birth location and Local Space observer must not be silently
collapsed. If the chart request supplies observer fields, they are the Local
Space observer for first admission.

---

## 7. Request Models

### 7.1 Direct Positions

Route:

- `POST /v1/local-space/positions`

Request:

- `positions: dict[str, {right_ascension: float, declination: float}]`
- `latitude: float`
- `lst_deg: float`

Validation:

- `positions` must be non-empty
- `positions` may contain at most 12 entries
- RA/Dec must be finite
- declination must be in `[-90, 90]`
- latitude must be finite and in `(-90, 90)` at the REST layer
- `lst_deg` must be finite

### 7.2 Chart-Backed Positions

Route:

- `POST /v1/local-space/chart/positions`

Request:

- `dt: datetime`
- `bodies: list[str] | None`
- `observer_lat: float`
- `observer_lon: float`
- `observer_elev_m: float = 0.0`

Validation:

- `dt` must be timezone-aware
- `bodies`, when supplied, must be non-empty
- `bodies` may contain at most 12 entries
- body names must be supported by the chart-backed server path
- observer latitude must be in `(-90, 90)`
- observer longitude must be in `[-180, 180]`
- observer elevation must be finite

---

## 8. Response Models

Position response:

- `body: str`
- `azimuth: float`
- `altitude: float`
- `is_above: bool`
- `compass_direction: str`

Provenance response:

- `requested_datetime: str | None`
- `normalized_datetime_utc: str | None`
- `jd_ut: float | None`
- `jd_tt: float | None`
- `lst_deg: float`
- `observer`
- `requested_bodies: list[str] | None`
- `returned_bodies: list[str]`
- `coordinate_source`
- `stage_sequence: list[str]`

Envelope:

- `positions: list[LocalSpacePositionResponse]`
- `provenance: LocalSpaceProvenanceResponse`

---

## 9. Service Contract

Service layer responsibilities:

- validate chart-supported bodies before ephemeris work
- derive chart context from the existing server chart adapter
- derive `jd_tt`, nutation, true obliquity, and local apparent sidereal time
- derive apparent RA/Dec for each requested body through `sky_position_at(...)`
- call `local_space_positions(...)`
- attach provenance without hiding the derivation path

The service must not:

- render a chart
- project output into a map frame
- infer a missing observer longitude
- infer a missing observer latitude
- collapse direct LST input into chart-backed longitude/time truth

---

## 10. Serializer Contract

Serializers must map engine vessels explicitly:

- `LocalSpacePosition.body`
- `LocalSpacePosition.azimuth`
- `LocalSpacePosition.altitude`
- `LocalSpacePosition.is_above`
- `LocalSpacePosition.compass_direction()`

Do not serialize via `__dict__`.

---

## 11. Required Validation

Direct routes must reject:

- empty positions map
- empty body name
- non-finite RA
- non-finite Dec
- Dec outside `[-90, 90]`
- non-finite latitude
- latitude outside REST observer bounds
- non-finite `lst_deg`
- body count greater than route maximum

Chart-backed routes must reject:

- naive datetime
- unsupported body names
- empty body list
- body count greater than route maximum
- non-finite observer values
- observer latitude outside `(-90, 90)`
- observer longitude outside `[-180, 180]`

Refraction:

- no refraction flag is admitted in first P10-02
- if refraction is later added, it must be provenance-visible and shared with
  the sky-position derivation doctrine

---

## 12. Required Tests

Add:

- `tests/server/test_server_local_space_routes.py`

Required parity tests:

- direct position route matches `local_space_positions(...)`
- chart-backed position route matches service derivation and
  `local_space_positions(...)`

Required structural tests:

- one body returns one position record
- response includes azimuth, altitude, `is_above`, and compass direction
- positions remain sorted by azimuth
- provenance records coordinate source and stage sequence
- route registration appears in the app route registry

Required adversarial tests:

- naive datetime is rejected
- unsupported chart body is rejected
- empty direct position map is rejected
- non-finite direct RA/Dec is rejected
- Dec outside `[-90, 90]` is rejected
- non-finite latitude is rejected
- non-finite `lst_deg` is rejected
- too many bodies are rejected
- missing chart observer latitude or longitude is rejected

Suggested implementation verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\local_space.py moira_server\services\local_space.py moira_server\serializers\local_space.py moira_server\routers\local_space.py tests\server\test_server_local_space_routes.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_local_space.py tests\server\test_server_local_space_routes.py -q
```

Before declaring P10-02 admitted, run the route registry audit and update
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 13. Explicit Non-Goals

P10-02 first admission does not expose:

- rendered compass charts
- map products
- SVG or raster outputs
- relocation chart synthesis
- local-space path products
- dense geographic grids
- GeoJSON route variants
- Astrocartography lines
- geodetic equivalents
- Gauquelin sectors
- galactic coordinates or galactic houses

Those products require their own Phase 10 design records or later spatial
transport primitives.

---

## 14. Admission Decision

P10-02 is admitted.

The first implementation admits exactly these two routes:

- `POST /v1/local-space/positions`
- `POST /v1/local-space/chart/positions`

No additional Local Space routes were admitted during first implementation.

Admission verification:

- `python -m py_compile` over the Local Space transport models, services,
  serializers, router, app wiring, package exports, and route tests.
- `python -m pytest tests/server/test_server_local_space_routes.py -q`
- `python -m pytest tests/unit/test_local_space.py tests/server/test_server_local_space_routes.py -q`
- Route registry audit after admission: 253 non-documentation routes, 249
  versioned `/v1` routes, and exactly 2 `/v1/local-space/*` routes.
