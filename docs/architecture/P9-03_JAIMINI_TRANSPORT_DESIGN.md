# P9-03 Jaimini Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-03 admitted; eight direct/chart-backed Jaimini routes live and tested
Scope: Phase 9 Jaimini REST admission design

This document declares the REST route shapes admitted for Jaimini Chara Karakas
and records the implemented model, serializer, service, router, and verification
state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/JAIMINI_BACKEND_STANDARD.md`

The governing engine object is the Jaimini Chara Karaka assignment:

- seven-karaka scheme over Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn
- optional eight-karaka scheme adding Rahu
- deterministic rank assignment by effective sidereal degree within sign
- explicit Rahu degree inversion
- explicit tie warnings

The authoritative engine function is `moira.jaimini.jaimini_karakas(...)`.

---

## 1. Route Family

Router prefix:

- `/v1/jaimini`

Route tag:

- `jaimini`

This family is live. The admitted paths are recorded in
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Direct Karaka Result

Route:

- `POST /v1/jaimini/karakas`

Transport stance:

- `direct_sync`

Purpose:

- Compute a full `JaiminiKarakaResult` from caller-supplied sidereal
  longitudes.

Required input doctrine:

- `sidereal_longitudes`: mapping of planet name to sidereal longitude
- `scheme`: 7 or 8
- optional Jaimini policy

Engine path:

1. Validate all supplied longitude values are finite.
2. Build `JaiminiPolicy` when explicit policy is supplied.
3. Call `jaimini_karakas(sidereal_longitudes, scheme, policy)`.
4. Call `validate_jaimini_output(result)` before serialization.

Truth boundary:

- The caller owns the sidereal longitude truth.
- The service validates transport shape but does not derive or reinterpret the
  supplied sidereal positions.
- For scheme 8, the caller must supply Rahu. Ketu is not a substitute.

Response:

- Full `JaiminiKarakaResult`.
- Tie warnings must be preserved.

### 2.2 Direct Chart Profile

Route:

- `POST /v1/jaimini/karakas/profile`

Transport stance:

- `direct_sync`

Purpose:

- Compute the aggregate Jaimini chart profile from caller-supplied sidereal
  longitudes.

Engine path:

1. Follow the same direct derivation path as `/v1/jaimini/karakas`.
2. Call `jaimini_chart_profile(result)`.

Response:

- `JaiminiChartProfile` only.
- The full assignment result is not silently bundled into the profile response.

### 2.3 Direct Condition Profile

Route:

- `POST /v1/jaimini/karakas/condition`

Transport stance:

- `direct_sync`

Purpose:

- Compute one `KarakaConditionProfile` from caller-supplied sidereal
  longitudes.

Required additional input:

- exactly one selector:
  - `karaka_name`, such as `Atmakaraka` or `Darakaraka`
  - `planet`, such as `Sun` or `Rahu`

Engine path:

1. Follow the same direct derivation path as `/v1/jaimini/karakas`.
2. Select one assignment through `result.by_karaka(...)` or
   `result.by_planet(...)`.
3. Call `karaka_condition_profile(assignment, result.scheme)`.

Response:

- `KarakaConditionProfile` only.

### 2.4 Direct Karaka Pair

Route:

- `POST /v1/jaimini/karakas/pair`

Transport stance:

- `direct_sync`

Purpose:

- Compute one `KarakaPair` edge between two named karaka roles from
  caller-supplied sidereal longitudes.

Required additional input:

- `role_a`
- `role_b`

Engine path:

1. Follow the same direct derivation path as `/v1/jaimini/karakas`.
2. Call `karaka_pair(result, role_a, role_b)`.

Response:

- `KarakaPair` only.

### 2.5 Chart-Backed Karaka Result

Route:

- `POST /v1/jaimini/chart/karakas`

Transport stance:

- `bounded_sync`

Purpose:

- Compute a full `JaiminiKarakaResult` from a timezone-aware datetime by
  deriving tropical planetary/node positions through Moira and converting them
  to sidereal longitudes.

Required input doctrine:

- timezone-aware datetime
- `scheme`: 7 or 8
- ayanamsa or explicit Jaimini policy

Engine path:

1. Build a planet `Chart` through the stable injected `Moira` instance for the
   seven classical planets.
2. When scheme 8 is requested, include nodes and source Rahu from
   `Body.TRUE_NODE`.
3. Convert tropical longitudes to sidereal longitudes with
   `tropical_to_sidereal(..., system=ayanamsa_system)`.
4. Materialize Rahu under the canonical key `Rahu`; do not expose `True Node`
   as the Jaimini planet name.
5. Call `jaimini_karakas(...)`.
6. Call `validate_jaimini_output(...)` before serialization.

Truth boundary:

- The server owns chart-backed longitude derivation.
- Chart-backed Jaimini is geocentric and location-free in the first admission.
- Scheme 8 uses Rahu from the true lunar node. Ketu is never included.
- The response must make chart-backed derivation visibly distinct from direct
  sidereal input.

Response:

- Full `JaiminiKarakaResult`.
- Tie warnings must be preserved.

### 2.6 Chart-Backed Chart Profile

Route:

- `POST /v1/jaimini/chart/profile`

Transport stance:

- `bounded_sync`

Purpose:

- Compute `JaiminiChartProfile` from server-derived chart truth.

Engine path:

1. Follow the same chart-backed derivation path as
   `/v1/jaimini/chart/karakas`.
2. Call `jaimini_chart_profile(result)`.

Response:

- `JaiminiChartProfile` only.

### 2.7 Chart-Backed Condition Profile

Route:

- `POST /v1/jaimini/chart/condition`

Transport stance:

- `bounded_sync`

Purpose:

- Compute one `KarakaConditionProfile` from server-derived chart truth.

Required additional input:

- exactly one selector:
  - `karaka_name`
  - `planet`

Engine path:

1. Follow the same chart-backed derivation path as
   `/v1/jaimini/chart/karakas`.
2. Select one assignment through `result.by_karaka(...)` or
   `result.by_planet(...)`.
3. Call `karaka_condition_profile(assignment, result.scheme)`.

Response:

- `KarakaConditionProfile` only.

### 2.8 Chart-Backed Karaka Pair

Route:

- `POST /v1/jaimini/chart/pair`

Transport stance:

- `bounded_sync`

Purpose:

- Compute one `KarakaPair` edge between two named karaka roles from
  server-derived chart truth.

Required additional input:

- `role_a`
- `role_b`

Engine path:

1. Follow the same chart-backed derivation path as
   `/v1/jaimini/chart/karakas`.
2. Call `karaka_pair(result, role_a, role_b)`.

Response:

- `KarakaPair` only.

---

## 3. Required Response Semantics

The Jaimini result response must preserve:

- `scheme`
- `atmakaraka`
- `assignments`
- `tie_warnings`
- `has_ties`

Each assignment must preserve:

- `karaka_name`
- `karaka_rank`
- `planet`
- `degree_in_sign`
- `sidereal_longitude`
- `is_rahu_inverted`

The condition profile response must preserve:

- `karaka_name`
- `karaka_rank`
- `planet`
- `planet_type`
- `degree_in_sign`
- `sidereal_longitude`
- `is_rahu_inverted`
- `is_atmakaraka`
- `is_darakaraka`

The chart profile response must preserve:

- `scheme`
- `atmakaraka_planet`
- `darakaraka_planet`
- `has_node_atmakaraka`
- `has_node_darakaraka`
- `has_ties`
- `tie_count`
- `profiles`

The pair response must preserve:

- `role_a`
- `role_b`
- `planet_a`
- `planet_b`
- `type_a`
- `type_b`
- `involves_node`
- `both_are_nodes`

---

## 4. Explicit Non-Goals For First Admission

Do not include in the first Jaimini REST increment:

- generic `/v1/vedic` catch-all transport
- Ketu as a karaka candidate
- textual chart interpretation
- hidden chart-location or house dependency
- topocentric Jaimini variation
- route-triggered kernel, ayanamsa, or global state mutation
- flattened Atmakaraka-only output as the primary result
- omission or suppression of tie warnings

The `atmakaraka(...)` convenience accessor can be reconsidered as a small route
later, but the first result route should preserve the full assignment vessel.

---

## 5. Transport Models

Model file:

- `moira_server/models/jaimini.py`

Declared request models:

- `JaiminiPolicyRequest`
- `JaiminiDirectRequest`
- `JaiminiChartRequest`
- `JaiminiConditionDirectRequest`
- `JaiminiConditionChartRequest`
- `JaiminiPairDirectRequest`
- `JaiminiPairChartRequest`

Declared response models:

- `KarakaAssignmentResponse`
- `JaiminiKarakaResultResponse`
- `KarakaConditionProfileResponse`
- `JaiminiChartProfileResponse`
- `KarakaPairResponse`

Model validation must reject:

- naive datetimes on chart-backed routes
- non-finite direct longitude inputs
- invalid scheme values
- empty ayanamsa fields
- condition requests with neither selector or both selectors
- pair requests with identical roles

Service validation must preserve engine failures for:

- missing required planets
- missing Rahu in direct scheme 8
- unknown condition selectors
- role names absent from the active scheme, such as `Putrakaraka` in scheme 7
- invalid ayanamsa names on chart-backed routes

---

## 6. Verification Requirements For Admission

Before these routes can be marked live:

- direct result route parity against `jaimini_karakas(...)`
- direct profile route parity against `jaimini_chart_profile(...)`
- direct condition route parity against `karaka_condition_profile(...)`
- direct pair route parity against `karaka_pair(...)`
- chart-backed route parity against `engine.chart(...)`,
  `tropical_to_sidereal(...)`, and `jaimini_karakas(...)`
- scheme 7 proof that Rahu is absent
- scheme 8 proof that Rahu is sourced from the true node and inversion is
  serialized
- serializer proof that `tie_warnings` are preserved
- serializer proof that `degree_in_sign` and `sidereal_longitude` both survive
  transport
- validator proof that `validate_jaimini_output(...)` is called on the base
  result path
- adversarial rejection for naive datetimes
- adversarial rejection for non-finite direct longitude inputs
- adversarial rejection for invalid schemes
- adversarial rejection for invalid condition selectors
- adversarial rejection for invalid or out-of-scheme pair roles
- boundary test proving no request path calls kernel lifecycle mutators
- route registration check proving all admitted paths are present

These checks are implemented in:

- `tests/server/test_server_jaimini_service.py`
- `tests/server/test_server_jaimini_routes.py`

The live REST reference has been updated only after those checks were added.

---

## 7. Serializer And Service Adapter Status

Serializer file:

- `moira_server/serializers/jaimini.py`

Service file:

- `moira_server/services/jaimini.py`

Declared serializer helpers:

- `serialize_karaka_assignment`
- `serialize_jaimini_result`
- `serialize_karaka_condition_profile`
- `serialize_jaimini_chart_profile`
- `serialize_karaka_pair`

Declared service helpers:

- `compute_jaimini_direct`
- `compute_jaimini_direct_profile`
- `compute_jaimini_direct_condition`
- `compute_jaimini_direct_pair`
- `compute_jaimini_chart`
- `compute_jaimini_chart_profile`
- `compute_jaimini_chart_condition`
- `compute_jaimini_chart_pair`

The service adapter must keep direct caller-owned sidereal truth distinct from
chart-backed server-derived sidereal truth. Chart-backed service code should
materialize intermediate support truth in named local variables:

- chart
- tropical longitudes
- true node longitude when scheme 8 is active
- ayanamsa system
- sidereal longitudes
- policy
- result

This is a protected doctrine surface. Do not hide Rahu sourcing or sidereal
conversion inside an opaque helper that makes scheme 8 provenance invisible.
