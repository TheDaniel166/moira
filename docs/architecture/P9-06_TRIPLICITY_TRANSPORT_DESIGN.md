# P9-06 Triplicity Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-06 admitted; three direct-sync Triplicity routes live and tested
Scope: Phase 9 Triplicity REST admission design

This document declares the REST route shapes admitted for the Triplicity family
and records the implemented transport admission state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/TRIPLICITY_BACKEND_STANDARD.md`

The governing engine object is Dorothean triplicity doctrine:

- supported doctrine registry
- sign-to-triplicity ruler table
- day ruler
- night ruler
- participating ruler
- active ruler under explicit sect context
- participating-ruler scoring policy

The authoritative engine functions are:

- `moira.triplicity.triplicity_assignment_for(...)`
- `moira.triplicity.triplicity_score(...)`

---

## 1. Route Family

Router prefix:

- `/v1/triplicity`

Route tag:

- `triplicity`

This family is live. The admitted paths in this document are registered by the
FastAPI application and documented in `wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Triplicity Table

Route:

- `GET /v1/triplicity/table`

Transport stance:

- `direct_sync`

Purpose:

- Expose the supported doctrine table as deterministic doctrine data.

Query inputs:

- `doctrine`, default `dorothean_pingree_1976`
- `is_day_chart`, default `true`

Engine path:

1. Iterate the 12 tropical signs in `moira.constants.SIGNS` order.
2. Call `triplicity_assignment_for(sign, is_day_chart=..., doctrine=...)`.
3. Serialize each `TriplicityAssignment`.

Truth boundary:

- This is a table/datum-provider route, not a chart route.
- The route must not derive sect from a datetime or chart.
- The response must preserve the doctrine and supplied sect context.

Response:

- Ordered list of `TriplicityAssignment` response vessels.

### 2.2 Triplicity Assignment

Route:

- `POST /v1/triplicity/assignment`

Transport stance:

- `direct_sync`

Purpose:

- Resolve one `TriplicityAssignment` for a sign under explicit doctrine and
  sect context.

Required input doctrine:

- `sign`
- `is_day_chart`
- optional `doctrine`

Engine path:

1. Validate transport enum and boolean fields.
2. Call `triplicity_assignment_for(...)`.

Response:

- One `TriplicityAssignment` response vessel.

### 2.3 Triplicity Score

Route:

- `POST /v1/triplicity/score`

Transport stance:

- `direct_sync`

Purpose:

- Compute the triplicity score for one planet/sign pair under explicit doctrine,
  sect context, participating-ruler policy, and scoring weights.

Required input doctrine:

- `planet`
- `sign`
- `is_day_chart`
- optional `doctrine`
- optional `participating_policy`
- optional `primary_score`
- optional `participating_score`

Engine path:

1. Validate transport enum, boolean, and score fields.
2. Call `triplicity_score(...)`.

Truth boundary:

- `triplicity_score(...)` intentionally returns `0` for unknown signs or
  non-ruling planets. The REST layer should not reinterpret that into a
  validation failure unless transport fields themselves are malformed.
- Participating-ruler policy must remain visible.

Response:

- `TriplicityScoreResponse`, including the returned score and a serialized
  assignment when the sign resolves.

---

## 3. Deferred Chart-Backed Surface

The following route is intentionally not part of first admission:

- `POST /v1/triplicity/chart/assignment`

Reason:

- `moira.triplicity` is explicitly chart-free and receives `is_day_chart` as a
  caller-supplied parameter.
- Chart-backed sect derivation already belongs to chart-owning service layers,
  such as dignities and lots.
- Adding a chart-backed route here would obscure the module boundary and make
  the REST surface imply astronomical behavior the backend does not own.

If chart-backed triplicity convenience is later admitted, it should be designed
as a server adapter that clearly derives sect through Moira and still calls the
same triplicity utility functions.

---

## 4. Required Response Semantics

`TriplicityAssignment` responses must preserve:

- `sign`
- `doctrine`
- `is_day_chart`
- `day_ruler`
- `night_ruler`
- `participating_ruler`
- `active_ruler`
- `signs`
- `element`
- `inactive_ruler`
- `has_participating_overlap`

`TriplicityScoreResponse` must preserve:

- `planet`
- `sign`
- `doctrine`
- `is_day_chart`
- `participating_policy`
- `primary_score`
- `participating_score`
- `score`
- `assignment` when available

---

## 5. Explicit Non-Goals

The first P9-06 admission does not expose:

- generic `/v1/classical` umbrella routes
- chart-backed sect derivation
- dignity totals
- almuten or lord-of-the-turn logic
- triplicity decans
- Vedic drekkana logic
- interpretive meanings
- multi-doctrine comparison
- profile or network routes not present in the backend

---

## 6. Verification Requirements For Admission

P9-06 admission verified:

- table route returns 12 assignments in deterministic sign order
- assignment route preserves active ruler and inactive ruler truth for day and
  night contexts
- score route preserves participating-ruler policy behavior
- invalid doctrine and policy values are rejected by transport validation
- malformed non-boolean `is_day_chart` is rejected
- score route preserves the engine's `0` behavior for unknown signs and
  non-ruling planets
- route registration appears in startup route inventory

Verification files:

- `tests/server/test_server_triplicity_routes.py`
- existing startup and error-mapping server tests

---

## 7. Admission State

P9-06 is admitted.

Implemented files:

- `moira_server/models/triplicity.py`
- `moira_server/serializers/triplicity.py`
- `moira_server/services/triplicity.py`
- `moira_server/routers/triplicity.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_triplicity_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md`
