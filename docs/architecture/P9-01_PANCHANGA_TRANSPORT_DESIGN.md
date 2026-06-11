# P9-01 Panchanga Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-01 admitted; four Panchanga routes live and tested
Scope: Phase 9 Panchanga REST admission design

This document declares the initial REST route shapes for Panchanga before any
Pydantic request models, response models, serializers, services, or routers are
implemented.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/PANCHANGA_BACKEND_STANDARD.md`

The governing engine object is the five-limb Panchanga instant:

- Tithi
- Vara
- Nakshatra
- Yoga
- Karana

The authoritative engine function is `moira.panchanga.panchanga_at(...)`.

---

## 1. Route Family

Router prefix:

- `/v1/panchanga`

Route tag:

- `panchanga`

This family is live. The admitted paths are recorded in
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Direct Panchanga Instant

Route:

- `POST /v1/panchanga/instant`

Transport stance:

- `direct_sync`

Purpose:

- Compute Panchanga from caller-supplied derived astronomical inputs.

Required input doctrine:

- Sun tropical longitude
- Moon tropical longitude
- Julian Day UT
- ayanamsa or explicit Panchanga policy

Engine path:

- `panchanga_at(sun_tropical_lon, moon_tropical_lon, jd, ayanamsa_system, policy)`

Truth boundary:

- The caller owns the supplied Sun/Moon longitudes.
- The server validates and transports those inputs but does not derive or
  reinterpret them.

Response:

- Panchanga result only.
- Profile products are not silently bundled into the base response.

### 2.2 Chart-Backed Panchanga Instant

Route:

- `POST /v1/panchanga/chart`

Transport stance:

- `bounded_sync`

Purpose:

- Compute Panchanga from a datetime by deriving Sun/Moon through the stable
  process engine.

Required input doctrine:

- timezone-aware datetime
- optional observer/chart context if the route later admits chart request
  parity with `Moira.chart(...)`
- ayanamsa or explicit Panchanga policy

Engine path:

1. Build a chart through the stable injected `Moira` instance.
2. Extract tropical Sun and Moon longitudes from the chart.
3. Convert the datetime to JD UT.
4. Call `panchanga_at(...)`.

Truth boundary:

- The server owns the chart derivation path for Sun/Moon longitudes.
- The response must make this route visibly distinct from
  `/v1/panchanga/instant`, because the inputs are not caller-supplied
  longitudes.

Response:

- Panchanga result only.
- Profile products are not silently bundled into the base response.

### 2.3 Direct Panchanga Profile

Route:

- `POST /v1/panchanga/instant/profile`

Transport stance:

- `direct_sync`

Purpose:

- Compute the Panchanga aggregate profile from caller-supplied Sun/Moon
  tropical longitudes and JD.

Engine path:

1. Call `panchanga_at(...)`.
2. Call `panchanga_profile(result)`.

Response:

- Panchanga profile only, unless later model design proves a combined envelope
  is necessary.

### 2.4 Chart-Backed Panchanga Profile

Route:

- `POST /v1/panchanga/chart/profile`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the Panchanga aggregate profile from datetime-derived chart truth.

Engine path:

1. Build a chart through the stable injected `Moira` instance.
2. Extract tropical Sun and Moon longitudes.
3. Convert datetime to JD UT.
4. Call `panchanga_at(...)`.
5. Call `panchanga_profile(result)`.

Response:

- Panchanga profile only, unless later model design proves a combined envelope
  is necessary.

---

## 3. Required Response Semantics

The Panchanga result response must preserve:

- `jd`
- `ayanamsa_system`
- `tithi`
- `vara`
- `vara_lord`
- `nakshatra`
- `yoga`
- `karana`

Each Panchanga element must preserve at least:

- `name`
- `index`
- `number`
- `degrees_elapsed`
- `degrees_remaining`

Nakshatra must serialize the full `NakshatraPosition` structure returned by
`moira.sidereal.nakshatra_of`, not just the nakshatra name.

Required Nakshatra fields:

- `nakshatra`
- `nakshatra_index`
- `nakshatra_lord`
- `pada`
- `degrees_in`
- `sidereal_lon`

The Panchanga profile response must preserve:

- `jd`
- `paksha`
- `is_purnima`
- `is_amavasya`
- `yoga_class`
- `karana_type`
- `vara_lord`
- `vara_lord_type`
- `ayanamsa_system`

---

## 4. Explicit Non-Goals For First Admission

Do not include in the first Panchanga REST increment:

- sunrise-based daily Panchanga correction
- location-specific Hindu calendrical day rollover
- Muhurta ranking
- generic `/v1/vedic` catch-all transport
- chart interpretation text
- route-triggered kernel or ayanamsa global mutation

If sunrise-based Panchanga is later admitted, it must be a separately named
route because it is not the same computational object as the instantaneous
`panchanga_at(...)` surface.

---

## 5. Transport Models

Model file:

- `moira_server/models/panchanga.py`

Declared request models:

- `PanchangaDirectRequest`
- `PanchangaChartRequest`
- `PanchangaPolicyRequest`

Declared response models:

- `PanchangaElementResponse`
- `NakshatraPositionResponse`
- `PanchangaResultResponse`
- `PanchangaProfileResponse`

Model work must preserve the direct-vs-chart-backed distinction rather than
using one ambiguous request shape with optional fields that change ownership of
the Sun/Moon longitudes.

Validation owned by the models:

- direct routes reject non-finite Sun/Moon longitude and JD inputs
- chart-backed routes reject naive datetimes
- chart-backed routes reject non-finite observer inputs
- chart-backed routes require observer latitude and longitude to be supplied
  together when either is supplied
- policy and top-level ayanamsa fields reject empty strings

Validation still owned by later service/route tests:

- ayanamsa names must be accepted or rejected according to the engine's
  sidereal policy surface
- route-level error envelopes must map model and service validation honestly

---

## 6. Verification Requirements For Admission

Before these routes can be marked live:

- direct route parity against `panchanga_at(...)`
- chart-backed route parity against `engine.chart(...)` plus `panchanga_at(...)`
- profile route parity against `panchanga_profile(...)`
- adversarial rejection for naive datetimes on chart-backed routes
- adversarial rejection for non-finite longitude/JD inputs
- adversarial rejection for invalid ayanamsa or policy values
- serializer proof that Nakshatra is not flattened
- boundary test proving no request path calls kernel lifecycle mutators
- route registration check proving all admitted paths are present

Only after those checks pass should the live REST reference be updated.

---

## 7. Serializer And Service Adapter Status

Serializer file:

- `moira_server/serializers/panchanga.py`

Service file:

- `moira_server/services/panchanga.py`

Declared serializer helpers:

- `serialize_panchanga_element`
- `serialize_nakshatra_position`
- `serialize_panchanga_result`
- `serialize_panchanga_profile`

Declared service helpers:

- `compute_panchanga_direct`
- `compute_panchanga_direct_profile`
- `compute_panchanga_chart`
- `compute_panchanga_chart_profile`

The chart-backed service helper derives Sun and Moon through the stable injected
`Moira` instance and then calls `panchanga_at(...)`. The direct service helper
uses caller-supplied Sun/Moon tropical longitudes and JD.

Router file:

- `moira_server/routers/panchanga.py`

Registered routes:

- `POST /v1/panchanga/instant`
- `POST /v1/panchanga/instant/profile`
- `POST /v1/panchanga/chart`
- `POST /v1/panchanga/chart/profile`

Verification:

- `tests/server/test_server_panchanga_service.py`
- `tests/server/test_server_panchanga_routes.py`
