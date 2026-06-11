# P9-04 Classical Dignities Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-04 admitted; six chart-backed Classical Dignities routes live and tested
Scope: Phase 9 Classical Dignities REST admission design

This document declares the REST route shapes admitted for the Classical
Dignities family and records the implemented model, serializer, service,
router, and verification state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/DIGNITIES_BACKEND_STANDARD.md`

The governing engine object is classical dignity condition truth:

- essential dignity and debility
- accidental dignity and debility
- sect and hayz truth
- solar condition truth
- formal reception truth
- per-planet condition profiles
- chart-wide dignity condition aggregation
- reception / condition network projection

The authoritative engine service is `moira.dignities.DignitiesService`.

---

## 1. Route Family

Router prefix:

- `/v1/dignities`

Route tag:

- `dignities`

This family is live. The admitted paths are recorded in
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Chart-Backed Dignity Result

Route:

- `POST /v1/dignities/chart`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the full list of `PlanetaryDignity` results from a
  timezone-aware chart request, deriving the required planet positions and
  houses through Moira.

Required input doctrine:

- timezone-aware datetime
- observer latitude
- observer longitude
- optional observer elevation
- house system
- optional explicit `DignityComputationPolicy`

Engine path:

1. Build a planet `Chart` through the stable injected `Moira` instance for the
   seven classical planets.
2. Build houses through the same injected `Moira` instance.
3. Materialize engine `planet_positions` as dictionaries with `name`,
   `degree`, and `is_retrograde`.
4. Materialize engine `house_positions` as dictionaries with `number` and
   `degree`.
5. Build `DignityComputationPolicy` only from explicit transport policy.
6. Call `DignitiesService.calculate_dignities(...)`.

Truth boundary:

- The server owns chart-backed planet position, house, sect, solar condition,
  and reception derivation.
- The response must preserve dignity truth and classifications; it must not
  collapse to only `total_score`.
- `DignitiesService` remains the only dignity doctrine engine. The REST service
  must not recompute essential dignity, accidental dignity, sect, solar
  condition, or reception truth independently.

Response:

- Ordered list of `PlanetaryDignity` response vessels.

### 2.2 Chart-Backed Receptions

Route:

- `POST /v1/dignities/chart/receptions`

Transport stance:

- `bounded_sync`

Purpose:

- Compute formal `PlanetaryReception` relations from server-derived chart
  positions.

Engine path:

1. Follow the same chart-backed planet derivation path as
   `/v1/dignities/chart`.
2. Call `DignitiesService.calculate_receptions(...)`.

Truth boundary:

- Reception is a relation surface, not a score surface.
- Mutual and unilateral receptions must remain distinct.
- Policy-admitted reception bases must remain explicit.

Response:

- Ordered list of `PlanetaryReception` response vessels.

### 2.3 Chart-Backed Per-Planet Condition Profiles

Route:

- `POST /v1/dignities/chart/conditions`

Transport stance:

- `bounded_sync`

Purpose:

- Compute all `PlanetaryConditionProfile` results from server-derived chart
  truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/dignities/chart`.
2. Call `DignitiesService.calculate_condition_profiles(...)`.

Response:

- Ordered list of `PlanetaryConditionProfile` response vessels.

### 2.4 Chart-Backed Single Condition Profile

Route:

- `POST /v1/dignities/chart/condition`

Transport stance:

- `bounded_sync`

Purpose:

- Compute one `PlanetaryConditionProfile` from server-derived chart truth.

Required additional input:

- `planet`: one of Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn

Engine path:

1. Follow the same chart-backed derivation path as `/v1/dignities/chart`.
2. Call `DignitiesService.calculate_condition_profiles(...)`.
3. Select the requested planet from the returned profiles.

Response:

- `PlanetaryConditionProfile` only.

### 2.5 Chart-Backed Chart Condition Profile

Route:

- `POST /v1/dignities/chart/profile`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the chart-wide `ChartConditionProfile` from server-derived chart
  truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/dignities/chart`.
2. Call `DignitiesService.calculate_chart_condition_profile(...)`.

Response:

- `ChartConditionProfile` only.
- The full dignity result is not silently bundled into the profile response.

### 2.6 Chart-Backed Condition Network

Route:

- `POST /v1/dignities/chart/network`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the directed reception / condition network from server-derived chart
  truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/dignities/chart`.
2. Call `DignitiesService.calculate_condition_network_profile(...)`.

Response:

- `ConditionNetworkProfile` only.
- Nodes, directed edges, isolated planets, most-connected planets, and mutual
  versus unilateral edge counts must remain visible.

---

## 3. Deferred Direct Expert Surface

The following direct routes are intentionally not part of first admission:

- `POST /v1/dignities/direct`
- `POST /v1/dignities/direct/receptions`
- `POST /v1/dignities/direct/conditions`
- `POST /v1/dignities/direct/profile`
- `POST /v1/dignities/direct/network`

Reason:

- `DignitiesService` consumes a coherent chart bundle: classical planet
  positions, retrograde state, house cusps, and explicit doctrine policy.
- Individually valid longitudes and house cusps can still form an incoherent
  chart if they were not derived from the same time, observer, and house
  policy.
- First admission should therefore let the server own chart derivation. The
  direct expert surface can be admitted later after a strict caller-owned
  consistency contract is written.

Direct admission can be reconsidered after the chart-backed family is live and
the request contract can prove at least:

- all seven classical planets are present
- all longitudes and house cusps are finite
- each planet longitude is in `[0, 360)`
- twelve houses are present exactly once
- house cusps belong to the same declared house doctrine
- retrograde state is explicitly caller-owned
- policy is explicit and valid
- caller-owned chart truth is not mixed with server-derived support truth

---

## 4. Required Policy Semantics

The request policy must map only to `DignityComputationPolicy` and its nested
policy vessels:

- `EssentialDignityPolicy.doctrine`
- `AccidentalDignityPolicy.include_house_strength`
- `AccidentalDignityPolicy.include_motion`
- `AccidentalDignityPolicy.solar`
- `AccidentalDignityPolicy.mutual_reception`
- `AccidentalDignityPolicy.sect`
- `AccidentalDignityPolicy.include_timelord_distributions`
- `SolarConditionPolicy.include_cazimi`
- `SolarConditionPolicy.include_combust`
- `SolarConditionPolicy.include_under_sunbeams`
- `SolarConditionPolicy.include_for_luminaries`
- `MutualReceptionPolicy.include_domicile`
- `MutualReceptionPolicy.include_exaltation`
- `SectHayzPolicy.mercury_sect_model`
- `SectHayzPolicy.include_hayz`

The REST layer must reject unknown policy values rather than silently falling
back to the default doctrine.

The default request policy is omission, which means the engine default
`DignityComputationPolicy()` is used. Transport must still serialize the
effective policy in a future metadata envelope if such an envelope is admitted.

---

## 5. Required Response Semantics

`PlanetaryDignity` responses must preserve at minimum:

- `planet`
- `sign`
- `degree`
- `house`
- `essential_dignity`
- `essential_score`
- `accidental_dignities`
- `accidental_score`
- `total_score`
- `is_retrograde`
- `essential_truth`
- `accidental_truth`
- `sect_truth`
- `solar_truth`
- `all_receptions`
- `admitted_receptions`
- `scored_receptions`
- `mutual_reception_truth`
- `essential_classification`
- `accidental_classification`
- `sect_classification`
- `solar_classification`
- `reception_classification`
- `condition_profile`

`PlanetaryReception` responses must preserve:

- `receiving_planet`
- `host_planet`
- `basis`
- `mode`
- `receiving_sign`
- `host_sign`
- `host_matching_signs`
- `is_mutual`

`PlanetaryConditionProfile` responses must preserve:

- essential, accidental, sect, solar, and reception truth/classification
- `all_receptions`
- `admitted_receptions`
- `scored_receptions`
- `strengthening_count`
- `weakening_count`
- `neutral_count`
- `state`

`ChartConditionProfile` responses must preserve:

- `profiles`
- state counts
- polarity totals
- strongest and weakest planets
- essential and accidental polarity totals
- reception participation total

`ConditionNetworkProfile` responses must preserve:

- `nodes`
- `edges`
- `isolated_planets`
- `most_connected_planets`
- `mutual_edge_count`
- `unilateral_edge_count`
- derived node and edge counts

---

## 6. Explicit Non-Goals

The first P9-04 admission does not expose:

- generic `/v1/classical` umbrella routes
- one broad "score only" endpoint
- dispositorship routes
- almuten routes
- lots, triplicity, bounds, or decans
- textual interpretation
- custom dignity doctrines beyond those already implemented by
  `DignityComputationPolicy`
- direct caller-owned chart bundles

Dispositorship is adjacent to dignity doctrine, but it has its own engine
vessels and policy surface. It should be evaluated as a separate classical
route family, not hidden inside P9-04.

---

## 7. Verification Requirements For Admission

Before P9-04 can be marked admitted, implementation must verify:

- service derivation uses the injected `moira_engine` runtime path
- timezone-aware datetimes are accepted on chart-backed routes
- naive datetimes are rejected on chart-backed routes
- non-finite latitude, longitude, elevation, or house cusp support values are
  rejected
- invalid house systems are rejected
- invalid policy enum values are rejected
- all live routes preserve deterministic classical planet ordering
- `total_score == essential_score + accidental_score` for every serialized
  `PlanetaryDignity`
- scored receptions are a subset of admitted receptions
- admitted receptions are a subset of all receptions where profiles expose all
  three layers
- chart condition profile counts match its serialized profiles
- network edge counts match serialized edges
- route registration appears in startup route inventory

Suggested tests:

- `tests/server/test_server_dignities_service.py`
- `tests/server/test_server_dignities_routes.py`
- existing startup and error-mapping server tests

---

## 8. Admission State

P9-04 is admitted.

Implemented files:

- `moira_server/models/dignities.py`
- `moira_server/serializers/dignities.py`
- `moira_server/services/dignities.py`
- `moira_server/routers/dignities.py`
- `tests/server/test_server_dignities_routes.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports
- `wiki/02_services/REST_API_REFERENCE.md`

Verification:

- `python -m py_compile` over the new dignity model, serializer, service,
  router, app, and router export files
- `pytest tests/server/test_server_dignities_routes.py
  tests/server/test_server_startup.py tests/server/test_server_error_mapping.py
  -q`
