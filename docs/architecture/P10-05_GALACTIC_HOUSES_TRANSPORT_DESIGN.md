# P10-05 Galactic Houses Transport Design

Version: 0.1
Date: 2026-06-12
Status: P10-05 admitted; three bounded routes live
Scope: Phase 10 Galactic Houses REST admission design

This document declares the transport design for the first bounded Galactic
Houses REST surface. The design has now been implemented as the first P10-05
admission slice.

Galactic Houses is a high-sensitivity derived house-system family. The REST
surface must not flatten native galactic cusp truth, ecliptic projection truth,
trisection direction, chart location, or epoch provenance.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `docs/architecture/P10-04_GALACTIC_COORDINATES_TRANSPORT_DESIGN.md`
- `wiki/02_standards/GALACTIC_BACKEND_STANDARD.md`
- `wiki/02_standards/GALACTIC_HOUSES_BACKEND_STANDARD.md`

Authoritative engine module:

- `moira/galactic_houses.py`

Authoritative engine vessels:

- `GalacticAngles`
- `GalacticHouseCusps`
- `GalacticHousePlacement`
- `GalacticHouseBoundaryProfile`

Authoritative engine functions:

- `calculate_galactic_houses(...)`
- `assign_galactic_house(...)`
- `body_galactic_house_position(...)`
- `describe_galactic_boundary(...)`

---

## 1. Route Family

Router prefix:

- `/v1/galactic-houses`

Route tag:

- `galactic-houses`

First admission routes:

- `POST /v1/galactic-houses/cusps`
- `POST /v1/galactic-houses/placement`
- `POST /v1/galactic-houses/chart/placements`

The first admission is bounded and synchronous. It exposes Galactic Porphyry
house cusps and placement products only.

No rendered charts, projection helpers, map products, catalog sweeps, alternate
galactic house systems, or convenience drawing adapters are admitted by this
design.

---

## 2. Governing Products

### 2.1 Cusps

One chart moment and observer location produces one `GalacticHouseCusps` vessel:

- twelve native galactic cusps
- twelve ecliptic projected cusps
- four galactic angles in both frames
- trisection direction

### 2.2 Direct Placement

One supplied galactic longitude plus one supplied cusp set produces one
placement:

- house number
- normalized galactic longitude
- exact-on-cusp flag
- opening cusp longitude
- fractional house position
- boundary profile

### 2.3 Chart Placements

One chart moment and observer location plus a bounded body list produces:

- chart Galactic Porphyry cusps
- one placement per returned body
- source body ecliptic longitude and latitude
- body galactic longitude and latitude
- fractional galactic-house position
- boundary profile

---

## 3. Transport Stance

First admission stance:

- `bounded_sync`

Reason:

- cusp output is one fixed-size vessel
- direct placement output is one placement
- chart-backed placement output is bounded by body count
- no async, map rendering, catalog sweep, or grid product is needed

Recommended first REST bound:

- maximum chart bodies: `12`

---

## 4. Request Models

### 4.1 Cusps Request

Fields:

- `dt: datetime`
- `latitude: float`
- `longitude: float`

Validation:

- `dt` must be timezone-aware
- latitude must be finite and in `[-90, 90]`
- longitude must be finite and in `[-180, 180]`

### 4.2 Direct Placement Request

Fields:

- `galactic_longitude: float`
- `house_cusps: GalacticHouseCuspsRequest`
- `near_cusp_threshold: float = 3.0`

`GalacticHouseCuspsRequest` fields:

- `cusps_gal: list[float]`
- `cusps_ecl: list[float]`
- `angles: GalacticAnglesRequest`
- `forward: bool`

Validation:

- galactic longitude must be finite
- cusp lists must contain exactly twelve finite values
- ecliptic and galactic cusp values must be in `[0, 360)`
- angle values must be finite
- `near_cusp_threshold` must be finite and positive

### 4.3 Chart Placements Request

Fields:

- `dt: datetime`
- `latitude: float`
- `longitude: float`
- `bodies: list[str] | None = None`
- `near_cusp_threshold: float = 3.0`

Validation:

- `dt` must be timezone-aware
- latitude must be finite and in `[-90, 90]`
- longitude must be finite and in `[-180, 180]`
- body list must be non-empty when supplied
- body count must not exceed `12`
- body names must be non-empty
- `near_cusp_threshold` must be finite and positive

---

## 5. Response Models

### 5.1 Cusps Response

Fields:

- `cusps`
- `provenance`

`cusps` must include:

- `cusps_gal`
- `cusps_ecl`
- `angles`
- `forward`

Each cusp list must preserve one-based house meaning by order:

- item 0 is house 1
- item 3 is house 4
- item 6 is house 7
- item 9 is house 10

### 5.2 Placement Response

Fields:

- `placement`
- `fractional_position`
- `boundary`
- `provenance`

### 5.3 Chart Placements Response

Fields:

- `cusps`
- `placements`
- `provenance`

Each chart-backed placement must include:

- `body`
- `ecliptic_longitude`
- `ecliptic_latitude`
- `galactic_longitude`
- `galactic_latitude`
- `placement`
- `fractional_position`
- `boundary`

---

## 6. Provenance Contract

Every response must include a provenance block.

Minimum provenance fields:

- `requested_datetime`
- `normalized_datetime_utc`
- `jd_ut`
- `jd_tt`
- `latitude`
- `longitude`
- `obliquity_deg`
- `armc_deg`
- `requested_bodies`
- `returned_bodies`
- `coordinate_source`
- `stage_sequence`

Coordinate-source values:

- `chart_time_location_galactic_porphyry`
- `direct_galactic_longitude_and_supplied_cusps`
- `chart_ecliptic_to_galactic_positions`

Required stage sequences:

Cusps:

```text
datetime_validation
location_validation
jd_ut_derivation
jd_tt_derivation
obliquity_derivation
armc_derivation
galactic_angle_search
galactic_porphyry_trisection
ecliptic_projection
response_materialization
```

Direct placement:

```text
direct_galactic_longitude_validation
supplied_cusp_validation
galactic_house_assignment
fractional_position_derivation
boundary_profile_derivation
response_materialization
```

Chart placements:

```text
datetime_validation
location_validation
chart_context_derivation
chart_body_validation
jd_tt_derivation
obliquity_derivation
armc_derivation
galactic_angle_search
galactic_porphyry_trisection
chart_ecliptic_coordinate_selection
ecliptic_to_galactic_computation
galactic_house_assignment
fractional_position_derivation
boundary_profile_derivation
response_materialization
```

---

## 7. Degeneracy And Error Policy

The engine can raise `RuntimeError` when the galactic pole passes through the
zenith and the sweep does not yield exactly two horizon crossings.

REST implementation must preserve this as a computation-domain error. It must
not silently synthesize cusps or substitute an alternate house system.

---

## 8. Verification Requirements For Admission

Before admitting routes, run:

- `python -m py_compile` for new galactic-house model, service, serializer,
  router, app wiring, and route test files
- `python -m pytest tests/unit/test_galactic_houses.py tests/unit/test_galactic_houses_public_api.py -q`
- route tests for every admitted `/v1/galactic-houses/*` route
- route-count audit showing total non-doc routes and `/v1/galactic-houses/*`
  count

Route tests must include:

- successful cusp response
- successful direct placement response
- successful chart-backed body placement response
- adversarial rejection for naive datetimes
- adversarial rejection for non-finite JD/location/longitude values
- adversarial rejection for invalid latitude or longitude
- adversarial rejection for malformed supplied cusps
- adversarial rejection for empty body names and excessive body count
- adversarial rejection for non-positive near-cusp threshold

---

## 9. Deferred Scope

Deferred to later admissions:

- rendered galactic house charts
- projection-specific drawing helpers
- map products
- catalog-wide body or star sweeps
- alternate galactic house systems
- async heavy-output workflows

These are distinct products with different governing objects.

---

## 10. Admission State

P10-05 is admitted as a bounded synchronous Galactic Porphyry house route
family.

Implemented files:

- `moira_server/models/galactic_houses.py`
- `moira_server/services/galactic_houses.py`
- `moira_server/serializers/galactic_houses.py`
- `moira_server/routers/galactic_houses.py`
- route wiring in `moira_server/app.py`
- exports in package `__init__.py` files
- `tests/server/test_server_galactic_houses_routes.py`
- REST reference documentation updates
- route-count audit update

Live routes:

- `POST /v1/galactic-houses/cusps`
- `POST /v1/galactic-houses/placement`
- `POST /v1/galactic-houses/chart/placements`

Admission verification:

- `python -m py_compile` over the new models, services, serializers, router,
  route exports, app wiring, and route tests.
- `python -m pytest tests/unit/test_galactic_houses.py tests/unit/test_galactic_houses_public_api.py tests/server/test_server_galactic_houses_routes.py tests/server/test_server_galactic_routes.py -q`
- route registry audit after admission: 266 non-documentation routes, 262
  versioned `/v1` routes, and exactly 3 `/v1/galactic-houses/*` routes.
