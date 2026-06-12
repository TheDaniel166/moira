# P10-03 Geodetic Transport Design

Version: 0.1
Date: 2026-06-12
Status: P10-03 admitted; four bounded routes live
Scope: Phase 10 Geodetic REST admission design

This document declares the transport design for the first bounded Geodetic
REST surface. The design has now been implemented as the first P10-03
admission slice.

Geodetic is a high-sensitivity geographic/ecliptic mapping family. The REST
surface must not flatten geographic longitude, ecliptic zodiac policy,
obliquity derivation, ayanamsa provenance, or equivalent-longitude semantics.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/02_standards/GEODETIC_BACKEND_STANDARD.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Authoritative engine module:

- `moira/geodetic.py`

Authoritative engine vessel:

- `GeodeticChart`

Authoritative engine functions:

- `geodetic_chart(...)`
- `geodetic_chart_from_chart(...)`
- `geodetic_equivalents(...)`
- `geodetic_equivalents_from_chart(...)`

Primitive helpers:

- `geodetic_mc(...)`
- `geodetic_asc(...)`

Primitive helpers are not admitted as first REST routes. They remain internal
computational steps behind the chart and equivalent products.

---

## 1. Route Family

Router prefix:

- `/v1/geodetic`

Route tag:

- `geodetic`

First admission routes:

- `POST /v1/geodetic/location-chart`
- `POST /v1/geodetic/chart/location-chart`
- `POST /v1/geodetic/equivalents`
- `POST /v1/geodetic/chart/equivalents`

The first admission is deliberately narrow. It exposes bounded geodetic chart
and equivalent-longitude products only.

No rendered map, projection, geographic search, relocation synthesis, primitive
MC-only, or primitive ASC-only route is admitted by this design.

---

## 2. Governing Products

### 2.1 Location Chart

One location produces one `GeodeticChart`:

- geographic latitude
- geographic longitude
- Geodetic MC
- Geodetic ASC
- obliquity used
- zodiac policy
- ayanamsa offset

### 2.2 Equivalent Longitudes

One body ecliptic longitude produces one geographic longitude where that body
is native to the Geodetic MC.

The result is a mapping from body name to geographic longitude in
`[-180, 180]`.

---

## 3. Transport Stance

First admission stance:

- `bounded_sync`

Reason:

- direct location chart output is a single vessel
- direct equivalents output is one longitude per supplied body
- chart-backed equivalents are bounded by body count
- no async or map-rendering workflow is needed

Do not admit:

- unbounded body lists
- catalog-wide fixed-star geodetic sweeps
- rendered maps
- projection products
- geographic search
- relocation synthesis
- primitive helper routes

---

## 4. Shared Request Policy

All P10-03 routes must validate:

- geographic latitude is finite and in `(-90, 90)` at the REST layer
- geographic longitude is finite and in `[-180, 180]`
- obliquity is finite for direct chart routes
- ecliptic longitudes are finite for direct equivalents
- body names are non-empty
- chart-backed body count is bounded
- datetime inputs are timezone-aware
- zodiac is either `tropical` or `sidereal`
- sidereal requests require ayanamsa policy

Recommended first REST bounds:

- maximum bodies: `12`

Reason:

- equivalent longitude output is compact, but chart-backed equivalents may
  require chart body derivation per requested body.

---

## 5. Zodiac And Ayanamsa Policy

Zodiac values:

- `tropical`
- `sidereal`

Direct chart route:

- `zodiac="tropical"` defaults `ayanamsa_deg` to `0.0`
- `zodiac="sidereal"` requires explicit finite `ayanamsa_deg`
- direct caller owns the numeric ayanamsa offset

Direct equivalents route:

- accepts `ayanamsa_deg=0.0` for tropical longitudes
- accepts explicit finite `ayanamsa_deg` for sidereal longitudes
- direct caller owns whether supplied longitudes are tropical or sidereal

Chart-backed routes:

- `zodiac="tropical"` uses `ayanamsa_system=None` and `ayanamsa_deg=0.0`
- `zodiac="sidereal"` requires `ayanamsa_system`
- the service resolves and serializes `ayanamsa_deg`
- invalid ayanamsa names are rejected by the sidereal engine

Do not use ambient/global sidereal state.

---

## 6. Provenance Contract

Every response must include a provenance block.

Minimum provenance fields:

- `requested_datetime`
- `normalized_datetime_utc`
- `jd_ut`
- `jd_tt`
- `obliquity_deg`
- `zodiac`
- `ayanamsa_system`
- `ayanamsa_deg`
- `requested_bodies`
- `returned_bodies`
- `coordinate_source`
- `stage_sequence`

Coordinate-source values:

- `direct_geographic_obliquity`
- `chart_epoch_obliquity`
- `direct_ecliptic_longitudes`
- `chart_tropical_longitudes`
- `chart_sidereal_longitudes`

Required stage sequences:

Direct location-chart route:

```text
direct_geographic_validation
zodiac_policy_validation
obliquity_validation
geodetic_chart_computation
response_materialization
```

Chart-backed location-chart route:

```text
datetime_validation
chart_context_derivation
zodiac_policy_validation
obliquity_derivation
ayanamsa_resolution
geodetic_chart_computation
response_materialization
```

Direct equivalents route:

```text
direct_longitude_validation
zodiac_policy_validation
geodetic_equivalent_computation
response_materialization
```

Chart-backed equivalents route:

```text
datetime_validation
chart_context_derivation
chart_body_validation
zodiac_policy_validation
ayanamsa_resolution
longitude_selection
geodetic_equivalent_computation
response_materialization
```

---

## 7. Request Models

### 7.1 Direct Location Chart

Route:

- `POST /v1/geodetic/location-chart`

Request:

- `geo_longitude: float`
- `geo_latitude: float`
- `obliquity: float`
- `zodiac: "tropical" | "sidereal" = "tropical"`
- `ayanamsa_deg: float | None = None`

Validation:

- `geo_longitude` finite in `[-180, 180]`
- `geo_latitude` finite in `(-90, 90)`
- `obliquity` finite
- `zodiac` valid
- sidereal requires finite `ayanamsa_deg`
- tropical defaults `ayanamsa_deg` to `0.0`

### 7.2 Chart-Backed Location Chart

Route:

- `POST /v1/geodetic/chart/location-chart`

Request:

- `dt: datetime`
- `geo_longitude: float`
- `geo_latitude: float`
- `zodiac: "tropical" | "sidereal" = "tropical"`
- `ayanamsa_system: str | None = None`

Validation:

- `dt` must be timezone-aware
- `geo_longitude` finite in `[-180, 180]`
- `geo_latitude` finite in `(-90, 90)`
- sidereal requires non-empty `ayanamsa_system`

### 7.3 Direct Equivalents

Route:

- `POST /v1/geodetic/equivalents`

Request:

- `longitudes: dict[str, float]`
- `zodiac: "tropical" | "sidereal" = "tropical"`
- `ayanamsa_deg: float | None = None`

Validation:

- map must be non-empty
- body names must be non-empty
- longitude values must be finite
- body count may contain at most 12 entries
- sidereal requires finite `ayanamsa_deg`
- tropical defaults `ayanamsa_deg` to `0.0`

### 7.4 Chart-Backed Equivalents

Route:

- `POST /v1/geodetic/chart/equivalents`

Request:

- `dt: datetime`
- `geo_longitude: float`
- `geo_latitude: float`
- `bodies: list[str] | None`
- `zodiac: "tropical" | "sidereal" = "tropical"`
- `ayanamsa_system: str | None = None`

Validation:

- `dt` must be timezone-aware
- `geo_longitude` finite in `[-180, 180]`
- `geo_latitude` finite in `(-90, 90)`
- body list must be non-empty when supplied
- body count may contain at most 12 entries
- body names must be chart-supported
- sidereal requires non-empty `ayanamsa_system`

---

## 8. Response Models

Geodetic chart response:

- `geo_latitude: float`
- `geo_longitude: float`
- `mc: float`
- `asc: float`
- `obliquity: float`
- `zodiac: str`
- `ayanamsa_deg: float`

Equivalent response:

- `body: str`
- `geographic_longitude: float`

Provenance response:

- `requested_datetime: str | None`
- `normalized_datetime_utc: str | None`
- `jd_ut: float | None`
- `jd_tt: float | None`
- `obliquity_deg: float | None`
- `zodiac: str`
- `ayanamsa_system: str | None`
- `ayanamsa_deg: float`
- `requested_bodies: list[str] | None`
- `returned_bodies: list[str]`
- `coordinate_source`
- `stage_sequence: list[str]`

Envelope:

- chart routes: `chart` plus `provenance`
- equivalents routes: `equivalents` plus `provenance`

---

## 9. Service Contract

Service layer responsibilities:

- validate chart-supported bodies before ephemeris work
- derive chart context through the existing server chart adapter
- derive true obliquity for chart-backed chart routes
- resolve ayanamsa explicitly for sidereal chart-backed routes
- select tropical or sidereal longitudes according to policy
- call the geodetic engine functions
- attach provenance without hiding the derivation path

The service must not:

- use global sidereal state
- infer sidereal policy without explicit request fields
- render a map
- project geographic longitudes into display frames
- expose primitive MC/ASC helpers as standalone routes

---

## 10. Serializer Contract

Serializers must map engine vessels explicitly:

- `GeodeticChart.geo_latitude`
- `GeodeticChart.geo_longitude`
- `GeodeticChart.mc`
- `GeodeticChart.asc`
- `GeodeticChart.obliquity`
- `GeodeticChart.zodiac`
- `GeodeticChart.ayanamsa_deg`

Do not serialize via `__dict__`.

---

## 11. Required Validation

Direct routes must reject:

- non-finite geographic longitude
- geographic longitude outside REST bounds
- non-finite geographic latitude
- geographic latitude outside REST bounds
- non-finite obliquity
- invalid zodiac
- sidereal zodiac without ayanamsa offset
- non-finite ayanamsa offset
- empty equivalents map
- empty body names
- non-finite equivalent longitude values
- too many equivalent bodies

Chart-backed routes must reject:

- naive datetime
- unsupported body names
- empty body list
- too many bodies
- invalid zodiac
- sidereal zodiac without ayanamsa system
- invalid ayanamsa system
- invalid geographic coordinates

---

## 12. Required Tests

Add:

- `tests/server/test_server_geodetic_routes.py`

Required parity tests:

- direct location-chart route matches `geodetic_chart(...)`
- chart-backed location-chart route matches service derivation and
  `geodetic_chart_from_chart(...)`
- direct equivalents route matches `geodetic_equivalents(...)`
- chart-backed equivalents route matches service derivation and
  `geodetic_equivalents_from_chart(...)`

Required structural tests:

- chart response preserves MC, ASC, obliquity, zodiac, and ayanamsa
- equivalents response returns one row per requested body
- provenance records zodiac, ayanamsa, coordinate source, and stage sequence
- route registration appears in the app route registry

Required adversarial tests:

- naive datetime is rejected
- unsupported chart body is rejected
- invalid zodiac is rejected
- sidereal request without ayanamsa policy is rejected
- invalid ayanamsa system is rejected
- invalid coordinates are rejected
- non-finite direct longitude/obliquity inputs are rejected
- too many bodies are rejected

Suggested implementation verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\geodetic.py moira_server\services\geodetic.py moira_server\serializers\geodetic.py moira_server\routers\geodetic.py tests\server\test_server_geodetic_routes.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_geodetic.py tests\server\test_server_geodetic_routes.py -q
```

Before declaring P10-03 admitted, run the route registry audit and update
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 13. Explicit Non-Goals

P10-03 first admission does not expose:

- primitive MC-only route
- primitive ASC-only route
- rendered maps
- projection products
- geographic search
- relocation chart synthesis
- dense geographic grids
- GeoJSON route variants
- Astrocartography lines
- Local Space positions
- Gauquelin sectors
- galactic coordinates or galactic houses

Those products require their own Phase 10 design records or later spatial
transport primitives.

---

## 14. Admission Decision

P10-03 is admitted.

The first implementation admits exactly these four routes:

- `POST /v1/geodetic/location-chart`
- `POST /v1/geodetic/chart/location-chart`
- `POST /v1/geodetic/equivalents`
- `POST /v1/geodetic/chart/equivalents`

No additional Geodetic routes were admitted during first implementation.

Admission verification:

- `python -m py_compile` over the Geodetic transport models, services,
  serializers, router, app wiring, package exports, and route tests.
- `python -m pytest tests/server/test_server_geodetic_routes.py -q`
- `python -m pytest tests/unit/test_geodetic.py tests/server/test_server_geodetic_routes.py -q`
- Route registry audit after admission: 257 non-documentation routes, 253
  versioned `/v1` routes, and exactly 4 `/v1/geodetic/*` routes.
