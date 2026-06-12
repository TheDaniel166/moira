# P10-04 Galactic Coordinates Transport Design

Version: 0.1
Date: 2026-06-12
Status: P10-04 admitted; six bounded routes live
Scope: Phase 10 Galactic Coordinates REST admission design

This document declares the transport design for the first bounded Galactic
Coordinates REST surface. The design has now been implemented as the first
P10-04 admission slice.

Galactic Coordinates is a high-sensitivity frame-conversion family. The REST
surface must not flatten J2000/ICRS equatorial truth, true-of-date ecliptic
truth, IAU galactic frame truth, obliquity, or `jd_tt` provenance.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/02_standards/GALACTIC_BACKEND_STANDARD.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Authoritative engine module:

- `moira/galactic.py`

Authoritative engine vessel:

- `GalacticPosition`

Authoritative engine functions:

- `equatorial_to_galactic(...)`
- `galactic_to_equatorial(...)`
- `ecliptic_to_galactic(...)`
- `galactic_to_ecliptic(...)`
- `galactic_position_of(...)`
- `all_galactic_positions(...)`
- `galactic_reference_points(...)`

`moira.sky.galactic` remains a re-export surface and is not the REST authority.

---

## 1. Route Family

Router prefix:

- `/v1/galactic`

Route tag:

- `galactic`

First admission routes:

- `POST /v1/galactic/equatorial-to-galactic`
- `POST /v1/galactic/galactic-to-equatorial`
- `POST /v1/galactic/ecliptic-to-galactic`
- `POST /v1/galactic/galactic-to-ecliptic`
- `POST /v1/galactic/reference-points`
- `POST /v1/galactic/chart/positions`

The first admission is bounded and synchronous. It exposes coordinate-frame
products only.

No galactic houses, rendered maps, projection helpers, catalog sweeps, fixed
star proper-motion products, or observer-local horizon products are admitted by
this design.

---

## 2. Governing Products

### 2.1 Equatorial To Galactic

One J2000/ICRS equatorial coordinate produces one IAU galactic coordinate:

- right ascension
- declination
- galactic longitude
- galactic latitude

### 2.2 Galactic To Equatorial

One IAU galactic coordinate produces one J2000/ICRS equatorial coordinate:

- galactic longitude
- galactic latitude
- right ascension
- declination

### 2.3 Ecliptic To Galactic

One true-of-date ecliptic coordinate produces one IAU galactic coordinate:

- ecliptic longitude
- ecliptic latitude
- obliquity
- `jd_tt`
- galactic longitude
- galactic latitude

### 2.4 Galactic To Ecliptic

One IAU galactic coordinate produces one true-of-date ecliptic coordinate:

- galactic longitude
- galactic latitude
- obliquity
- `jd_tt`
- ecliptic longitude
- ecliptic latitude

### 2.5 Reference Points

One epoch produces the named galactic landmarks in true-of-date ecliptic
coordinates:

- Galactic Center
- Galactic Anti-Center
- North Galactic Pole
- South Galactic Pole
- Super-Galactic Center

### 2.6 Chart Positions

One chart produces one bounded list of `GalacticPosition` vessels:

- body name
- galactic longitude
- galactic latitude
- source ecliptic longitude
- source ecliptic latitude
- proximity to galactic plane
- galactic hemisphere
- angular distance to Galactic Center
- angular distance to Galactic Anti-Center

---

## 3. Transport Stance

First admission stance:

- `bounded_sync`

Reason:

- raw transform routes return one coordinate pair
- reference-point output is fixed at five landmarks
- chart-backed output is bounded by body count
- no async, map rendering, catalog sweep, or grid product is needed

Recommended first REST bound:

- maximum chart bodies: `12`

---

## 4. Request Models

### 4.1 Equatorial To Galactic Request

Fields:

- `right_ascension: float`
- `declination: float`

Validation:

- right ascension must be finite
- declination must be finite and in `[-90, 90]`

Frame:

- source frame is always `equatorial_j2000_icrs`
- target frame is always `galactic_iau_1958`

### 4.2 Galactic To Equatorial Request

Fields:

- `galactic_longitude: float`
- `galactic_latitude: float`

Validation:

- galactic longitude must be finite
- galactic latitude must be finite and in `[-90, 90]`

Frame:

- source frame is always `galactic_iau_1958`
- target frame is always `equatorial_j2000_icrs`

### 4.3 Ecliptic To Galactic Request

Fields:

- `ecliptic_longitude: float`
- `ecliptic_latitude: float`
- `obliquity: float`
- `jd_tt: float`

Validation:

- ecliptic longitude must be finite
- ecliptic latitude must be finite and in `[-90, 90]`
- obliquity must be finite
- `jd_tt` must be finite

Frame:

- source frame is always `ecliptic_true_of_date`
- intermediate frame is `equatorial_true_of_date`
- matrix frame is `equatorial_j2000_icrs`
- target frame is `galactic_iau_1958`

### 4.4 Galactic To Ecliptic Request

Fields:

- `galactic_longitude: float`
- `galactic_latitude: float`
- `obliquity: float`
- `jd_tt: float`

Validation:

- galactic longitude must be finite
- galactic latitude must be finite and in `[-90, 90]`
- obliquity must be finite
- `jd_tt` must be finite

Frame:

- source frame is always `galactic_iau_1958`
- matrix frame is `equatorial_j2000_icrs`
- intermediate frame is `equatorial_true_of_date`
- target frame is `ecliptic_true_of_date`

### 4.5 Reference Points Request

Fields:

- `obliquity: float`
- `jd_tt: float`

Validation:

- obliquity must be finite
- `jd_tt` must be finite

### 4.6 Chart Positions Request

Fields:

- `dt: datetime`
- `bodies: list[str] | None = None`
- `observer_lat: float = 0.0`
- `observer_lon: float = 0.0`
- `observer_elev_m: float = 0.0`

Validation:

- `dt` must be timezone-aware
- body list must be non-empty when supplied
- body count must not exceed `12`
- body names must be non-empty
- observer coordinates must be finite
- observer latitude must be in `[-90, 90]`
- observer longitude must be in `[-180, 180]`

Observer fields are retained because chart construction currently owns apparent
body derivation through the server chart context. The galactic coordinate
product itself is not an observer-horizon product.

---

## 5. Response Models

### 5.1 Coordinate Responses

Galactic coordinate response:

- `galactic_longitude`
- `galactic_latitude`
- `source_frame`
- `target_frame`
- `provenance`

Equatorial coordinate response:

- `right_ascension`
- `declination`
- `source_frame`
- `target_frame`
- `provenance`

Ecliptic coordinate response:

- `ecliptic_longitude`
- `ecliptic_latitude`
- `source_frame`
- `target_frame`
- `provenance`

### 5.2 Reference Point Response

Each reference point:

- `name`
- `ecliptic_longitude`
- `ecliptic_latitude`
- `source_frame`
- `target_frame`

Envelope:

- `points`
- `provenance`

### 5.3 Chart Position Response

Each chart position:

- `body`
- `galactic_longitude`
- `galactic_latitude`
- `ecliptic_longitude`
- `ecliptic_latitude`
- `near_galactic_plane`
- `galactic_hemisphere`
- `angular_distance_to_galactic_center`
- `angular_distance_to_galactic_anticenter`

Envelope:

- `positions`
- `provenance`

---

## 6. Provenance Contract

Every response must include a provenance block.

Minimum provenance fields:

- `requested_datetime`
- `normalized_datetime_utc`
- `jd_ut`
- `jd_tt`
- `obliquity_deg`
- `requested_bodies`
- `returned_bodies`
- `source_frame`
- `target_frame`
- `coordinate_source`
- `stage_sequence`

Coordinate-source values:

- `direct_equatorial_j2000_icrs`
- `direct_galactic_iau_1958`
- `direct_ecliptic_true_of_date`
- `reference_point_catalog_j2000_icrs`
- `chart_ecliptic_true_of_date`

Required stage sequences:

Direct equatorial to galactic:

```text
direct_equatorial_validation
iau_galactic_rotation
response_materialization
```

Direct galactic to equatorial:

```text
direct_galactic_validation
iau_galactic_inverse_rotation
response_materialization
```

Direct ecliptic to galactic:

```text
direct_ecliptic_validation
ecliptic_to_true_equatorial
true_equatorial_to_j2000_icrs
iau_galactic_rotation
response_materialization
```

Direct galactic to ecliptic:

```text
direct_galactic_validation
iau_galactic_inverse_rotation
j2000_icrs_to_true_equatorial
true_equatorial_to_ecliptic
response_materialization
```

Reference points:

```text
epoch_validation
j2000_reference_point_selection
j2000_icrs_to_true_equatorial
true_equatorial_to_ecliptic
response_materialization
```

Chart positions:

```text
datetime_validation
chart_context_derivation
chart_body_validation
obliquity_derivation
jd_tt_derivation
chart_ecliptic_coordinate_selection
ecliptic_to_galactic_computation
response_materialization
```

---

## 7. Verification Requirements For Admission

Before admitting routes, run:

- `python -m py_compile` for new galactic model, service, serializer, router,
  app wiring, and route test files
- `python -m pytest tests/unit/test_galactic.py -q`
- `python -m pytest tests/unit/test_experimental_validation.py -q`
- `python -m pytest tests/integration/test_galactic_oracle_reference.py -q`
- route tests for every admitted `/v1/galactic/*` route
- route-count audit showing total non-doc routes and `/v1/galactic/*` count

Route tests must include:

- successful direct equatorial to galactic transform
- successful direct galactic to equatorial transform
- successful direct ecliptic to galactic transform
- successful direct galactic to ecliptic transform
- successful reference-point response with five landmarks
- successful chart-backed positions response with bounded bodies
- adversarial rejection for naive datetimes
- adversarial rejection for non-finite coordinates
- adversarial rejection for out-of-range declination or latitude
- adversarial rejection for empty body names and excessive body count

---

## 8. Deferred Scope

Deferred to later admissions:

- P10-05 Galactic Houses
- galactic map rendering
- fixed-star catalog sweeps
- proper-motion star products
- dense sky grids
- projection-specific browser conveniences
- observer-local galactic horizon products

These are not failures of P10-04. They are distinct products with different
governing objects.

---

## 9. Admission State

P10-04 is admitted as a bounded synchronous galactic coordinate-frame route
family.

Implemented files:

- `moira_server/models/galactic.py`
- `moira_server/services/galactic.py`
- `moira_server/serializers/galactic.py`
- `moira_server/routers/galactic.py`
- route wiring in `moira_server/app.py`
- exports in package `__init__.py` files
- `tests/server/test_server_galactic_routes.py`
- REST reference documentation updates
- route-count audit update

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
- route registry audit after admission: 263 non-documentation routes, 259
  versioned `/v1` routes, and exactly 6 `/v1/galactic/*` routes.
