# P10-06 Gauquelin Sectors Transport Design

Version: 0.2
Date: 2026-06-12
Status: P10-06 admitted; three bounded routes live
Scope: Phase 10 Gauquelin Sectors REST admission design

This document declares the transport design for the first bounded Gauquelin
Sectors REST surface. The design has now been implemented as the P10-06
admission slice.

Gauquelin Sectors is a high-sensitivity observer and horizon product. The REST
surface must not flatten apparent RA/Dec truth, local sidereal time, effective
horizon altitude, canonical 36-sector plus-zone semantics, or circumpolar and
never-rising states.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/02_standards/GAUQUELIN_BACKEND_STANDARD.md`

Authoritative engine module:

- `moira/gauquelin.py`

Authoritative engine vessels:

- `GauquelinHorizonStatus`
- `GauquelinPosition`

Authoritative engine functions:

- `gauquelin_sector(...)`
- `all_gauquelin_sectors(...)`

---

## 1. Route Family

Router prefix:

- `/v1/gauquelin`

Route tag:

- `gauquelin`

First admission routes:

- `POST /v1/gauquelin/sector`
- `POST /v1/gauquelin/sectors`
- `POST /v1/gauquelin/chart/sectors`

The first admission is bounded, synchronous, and canonical 36-sector only.

No rendered wheels, map products, statistical workflows, catalog sweeps, or
custom sector-count REST routes are admitted by this design.

---

## 2. Governing Products

### 2.1 Direct Sector

One apparent RA/Dec value, observer latitude, and LST produces one
`GauquelinPosition` vessel:

- sector number
- zone label
- diurnal position
- degree in sector
- plus-zone flag
- horizon status

### 2.2 Direct Sectors

One bounded map of body labels to apparent RA/Dec pairs, plus observer latitude
and LST, produces one `GauquelinPosition` per supplied body.

Input order must be preserved when the request body uses an ordered JSON object
or an explicit list shape.

### 2.3 Chart Sectors

One chart moment, observer location, and bounded body list produces one
`GauquelinPosition` per returned body. Chart-backed routes must derive apparent
topocentric RA/Dec through the same sky-position path used by validated
Gauquelin reference tests, then derive LST from `jd_ut`, observer longitude,
nutation, and true obliquity.

---

## 3. Transport Stance

First admission stance:

- `bounded_sync`

Reason:

- one sector result is a compact vessel
- direct multi-body output is bounded by request body count
- chart-backed output is bounded by selected body count
- no async, map rendering, statistical search, catalog sweep, or grid product
  is needed

Recommended first REST bounds:

- maximum direct bodies: `24`
- maximum chart bodies: `12`

---

## 4. Request Models

### 4.1 Direct Sector Request

Fields:

- `body: str | None = None`
- `right_ascension: float`
- `declination: float`
- `latitude: float`
- `local_sidereal_time: float`
- `horizon_altitude: float = -0.5667`
- `sectors: Literal[36] = 36`

Validation:

- `right_ascension` must be finite
- `declination` must be finite and in `[-90, 90]`
- `latitude` must be finite and in `[-90, 90]`
- `local_sidereal_time` must be finite
- `horizon_altitude` must be finite
- `sectors` must be exactly `36`
- `body`, when supplied, must be non-empty

### 4.2 Direct Sectors Request

Fields:

- `bodies: list[GauquelinDirectBodyInput]`
- `latitude: float`
- `local_sidereal_time: float`
- `horizon_altitude: float = -0.5667`
- `sectors: Literal[36] = 36`

`GauquelinDirectBodyInput` fields:

- `body: str`
- `right_ascension: float`
- `declination: float`

Validation:

- `bodies` must be non-empty
- body count must not exceed `24`
- body names must be non-empty and unique
- right ascensions must be finite
- declinations must be finite and in `[-90, 90]`
- latitude, LST, horizon altitude, and sectors follow direct-sector validation

### 4.3 Chart Sectors Request

Fields:

- `dt: datetime`
- `latitude: float`
- `longitude: float`
- `bodies: list[str] | None = None`
- `horizon_altitude: float = -0.5667`
- `sectors: Literal[36] = 36`

Validation:

- `dt` must be timezone-aware
- latitude must be finite and in `[-90, 90]`
- longitude must be finite and in `[-180, 180]`
- body list must be non-empty when supplied
- body count must not exceed `12`
- body names must be non-empty
- horizon altitude must be finite
- sectors must be exactly `36`

---

## 5. Response Models

### 5.1 Position Response

Every serialized position must include:

- `body`
- `sector`
- `zone`
- `diurnal_position`
- `sectors`
- `degree_in_sector`
- `is_plus_zone`
- `horizon_status`

`horizon_status` values:

- `normal`
- `circumpolar`
- `never_rises`

### 5.2 Direct Sector Response

Fields:

- `position`
- `provenance`

### 5.3 Direct Sectors Response

Fields:

- `positions`
- `provenance`

### 5.4 Chart Sectors Response

Fields:

- `positions`
- `provenance`

Each chart-backed position should also preserve source coordinate detail:

- `right_ascension`
- `declination`

These source coordinate fields may be nested beside the position result, but
they must remain visible in the response shape.

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
- `local_sidereal_time`
- `horizon_altitude`
- `sectors`
- `requested_bodies`
- `returned_bodies`
- `coordinate_source`
- `stage_sequence`

Coordinate-source values:

- `direct_apparent_ra_dec_lst`
- `direct_apparent_ra_dec_map_lst`
- `chart_apparent_topocentric_ra_dec_lst`

Required stage sequences:

Direct sector:

```text
direct_ra_dec_validation
location_validation
lst_validation
horizon_altitude_validation
canonical_sector_policy_validation
gauquelin_sector_computation
response_materialization
```

Direct sectors:

```text
direct_body_list_validation
direct_ra_dec_validation
location_validation
lst_validation
horizon_altitude_validation
canonical_sector_policy_validation
gauquelin_sector_computation
response_materialization
```

Chart sectors:

```text
datetime_validation
location_validation
chart_body_validation
jd_ut_derivation
jd_tt_derivation
nutation_derivation
true_obliquity_derivation
local_sidereal_time_derivation
apparent_topocentric_ra_dec_derivation
horizon_altitude_validation
canonical_sector_policy_validation
gauquelin_sector_computation
response_materialization
```

---

## 7. Degeneracy And Error Policy

Circumpolar and never-rising body states are valid computational results.

REST implementation must:

- preserve `horizon_status`
- return sectors and diurnal positions for these degenerate states
- avoid converting them into HTTP validation errors
- avoid silently removing affected bodies from multi-body responses

Validation errors are reserved for malformed inputs: naive datetimes,
non-finite values, out-of-range declination or latitude, invalid longitude,
empty body names, excessive body lists, or non-canonical REST sector counts.

---

## 8. Verification Requirements For Admission

Before admitting routes, run:

- `python -m py_compile` for new Gauquelin model, service, serializer, router,
  app wiring, and route test files
- `python -m pytest tests/unit/test_gauquelin.py tests/unit/test_session_fixes.py tests/integration/test_gauquelin_external_reference.py -q`
- route tests for every admitted `/v1/gauquelin/*` route
- route-count audit showing total non-doc routes and `/v1/gauquelin/*` count

Route tests must include:

- successful direct single-sector response
- successful direct multi-body response
- successful chart-backed body response
- adversarial rejection for naive datetimes on chart-backed routes
- adversarial rejection for non-finite RA/Dec/LST/location/horizon inputs
- adversarial rejection for out-of-range declination, latitude, and longitude
- adversarial rejection for non-canonical REST sector counts
- preservation of `circumpolar` and `never_rises` horizon statuses

---

## 9. Deferred Scope

Deferred until a later design:

- custom sector-count REST policy
- rendered Gauquelin wheels
- map products
- statistical research or replication workflows
- catalog-wide asteroid, comet, or fixed-star sweeps
- async jobs
- global observer state

---

## 10. Admission Rule

P10-06 is admitted as a bounded synchronous canonical Gauquelin route family.

Live routes:

- `POST /v1/gauquelin/sector`
- `POST /v1/gauquelin/sectors`
- `POST /v1/gauquelin/chart/sectors`

Admission verification:

- `python -m py_compile` over the new model, service, serializer, router,
  route exports, app wiring, model exports, and route test files.
- `python -m pytest tests/server/test_server_gauquelin_routes.py -q`
- `python -m pytest tests/unit/test_gauquelin.py tests/unit/test_session_fixes.py tests/integration/test_gauquelin_external_reference.py tests/server/test_server_gauquelin_routes.py -q`
- Route registry audit after admission: 269 non-documentation routes, 265
  versioned `/v1` routes, and exactly 3 `/v1/gauquelin/*` routes.
