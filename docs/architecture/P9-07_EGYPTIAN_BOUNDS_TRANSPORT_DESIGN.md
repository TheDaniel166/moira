# P9-07 Egyptian Bounds Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-07 admitted; seven direct-sync Egyptian Bounds routes live and tested
Scope: Phase 9 Egyptian Bounds REST admission design

This document declares the REST route shapes admitted for the Egyptian Bounds
family and records the implemented transport admission state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/EGYPTIAN_BOUNDS_BACKEND_STANDARD.md`

The governing engine object is bound/term doctrine over tropical sign
subdivisions:

- doctrine-bound table segments
- normalized longitude truth
- bound ruler
- guest-to-host classification
- local relation profile
- local condition profile
- aggregate condition profile
- directed guest/host network profile

The authoritative engine functions are:

- `moira.egyptian_bounds.egyptian_bound_of(...)`
- `moira.egyptian_bounds.classify_egyptian_bound(...)`
- `moira.egyptian_bounds.relate_planet_to_egyptian_bound(...)`
- `moira.egyptian_bounds.evaluate_egyptian_bound_relations(...)`
- `moira.egyptian_bounds.evaluate_egyptian_bound_condition(...)`
- `moira.egyptian_bounds.evaluate_egyptian_bounds_aggregate(...)`
- `moira.egyptian_bounds.evaluate_egyptian_bounds_network(...)`

---

## 1. Route Family

Router prefix:

- `/v1/egyptian-bounds`

Route tag:

- `egyptian-bounds`

This family is live. The admitted paths in this document are registered by the
FastAPI application and documented in `wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Bounds Table

Route:

- `GET /v1/egyptian-bounds/table`

Transport stance:

- `direct_sync`

Purpose:

- Expose the selected bounds doctrine table as deterministic segment data.

Query inputs:

- `doctrine`, default `egyptian`

Response:

- One table vessel preserving doctrine, sign order, and five segment vessels
  per sign.

### 2.2 Bound Truth

Route:

- `POST /v1/egyptian-bounds/bound`

Transport stance:

- `direct_sync`

Purpose:

- Resolve normalized longitude, sign identity, degree within sign, and
  containing bound segment for one longitude.

Required input doctrine:

- `longitude`
- optional `policy.doctrine`

Response:

- One `EgyptianBoundTruth` response vessel.

### 2.3 Classification

Route:

- `POST /v1/egyptian-bounds/classification`

Transport stance:

- `direct_sync`

Purpose:

- Classify a planet's local bound ruler relationship at a caller-supplied
  longitude.

Required input doctrine:

- `planet`
- `longitude`
- optional `policy.doctrine`
- optional `is_day_chart`
- optional `mercury_rises_before_sun`

Response:

- One `EgyptianBoundClassification` response vessel.

### 2.4 Relation

Route:

- `POST /v1/egyptian-bounds/relation`

Transport stance:

- `direct_sync`

Purpose:

- Resolve the directed guest-to-host relation for a planet in a bound.

Response:

- One `EgyptianBoundRelationProfile` response vessel, preserving detected,
  admitted, and scored relation truth.

### 2.5 Condition

Route:

- `POST /v1/egyptian-bounds/condition`

Transport stance:

- `direct_sync`

Purpose:

- Resolve the integrated local condition profile for one planet/longitude pair.

Response:

- One `EgyptianBoundConditionProfile` response vessel.

### 2.6 Aggregate

Route:

- `POST /v1/egyptian-bounds/aggregate`

Transport stance:

- `direct_sync`

Purpose:

- Aggregate multiple local condition profiles from caller-supplied
  planet/longitude pairs.

Response:

- One `EgyptianBoundsAggregateProfile` response vessel.

### 2.7 Network

Route:

- `POST /v1/egyptian-bounds/network`

Transport stance:

- `direct_sync`

Purpose:

- Project an aggregate condition profile into the directed guest/host bounds
  network.

Response:

- One `EgyptianBoundsNetworkProfile` response vessel.

---

## 3. Deferred Chart-Backed Surface

The first P9-07 admission does not expose chart-backed routes.

Reason:

- `moira.egyptian_bounds` is a chart-free doctrine subsystem.
- Chart-backed derivation would require the server to own planetary longitude
  acquisition and sect/Mercury context derivation before calling this module.
- That convenience belongs in a future adapter or a chart-owning condition
  service, not in the table owner itself.

---

## 4. Required Response Semantics

Transport must preserve:

- doctrine value
- normalized longitude truth
- sign and sign index
- degree within sign
- segment start/end/width
- bound ruler
- own-bound truth
- host nature and optional host sect truth
- relation kind and profile membership
- condition state and polarity counts
- aggregate state totals and strongest/weakest summaries
- network nodes, edges, isolated planets, most-connected planets, and edge
  counts

---

## 5. Explicit Non-Goals

The first P9-07 admission does not expose:

- chart-backed longitudes
- automatic sect derivation
- automatic Mercury morning/evening derivation
- dignity totals
- lord-of-the-turn logic
- generic `/v1/classical` umbrella routes
- interpretive meanings

---

## 6. Verification Requirements For Admission

P9-07 admission verified:

- table route returns 12 signs in deterministic sign order with 5 segments
  each
- bound route preserves left-closed/right-open segment truth
- classification route preserves own-bound and host nature truth
- relation route preserves detected/admitted/scored relation truth
- condition route preserves state and polarity counts
- aggregate route preserves deterministic ordering and state totals
- network route preserves node, edge, mutual/unilateral, and isolation truth
- invalid doctrine values are rejected by transport validation
- malformed/non-finite longitude inputs are rejected by transport validation
- duplicate aggregate planets surface as validation errors through the server
  error envelope
- route registration appears in startup route inventory

Verification files:

- `tests/server/test_server_egyptian_bounds_routes.py`
- existing startup and error-mapping server tests

---

## 7. Admission State

P9-07 is admitted.

Implemented files:

- `moira_server/models/egyptian_bounds.py`
- `moira_server/serializers/egyptian_bounds.py`
- `moira_server/services/egyptian_bounds.py`
- `moira_server/routers/egyptian_bounds.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_egyptian_bounds_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md`
