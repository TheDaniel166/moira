# P9-05 Lots Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-05 route family designed; implementation pending
Scope: Phase 9 Classical Lots REST admission design

This document declares the REST route shapes admitted for the Classical Lots
family before model and router work begins.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/LOTS_BACKEND_STANDARD.md`

The governing engine object is Arabic Part / Lot computation truth:

- catalogue lot definitions
- lot longitude and sign placement
- effective formula operands
- day/night reversal truth
- reference resolution truth
- dependency truth
- per-lot condition profiles
- chart-wide lot condition aggregation
- dependency / condition network projection

The authoritative engine service is `moira.lots.ArabicPartsService`.

---

## 1. Route Family

Router prefix:

- `/v1/lots`

Route tag:

- `lots`

This family is not live yet. The admitted paths in this document become
documentation-facing only after implementation, route registration, and
verification.

---

## 2. Initial Route Shapes

### 2.1 Lot Catalogue

Route:

- `GET /v1/lots/catalog`

Transport stance:

- `direct_sync`

Purpose:

- Expose the stable `PARTS_DEFINITIONS` catalogue as doctrine data.

Engine path:

1. Read `PARTS_DEFINITIONS`.
2. Serialize each `PartDefinition` with name, day operands, reversal rule,
   category, and description.

Truth boundary:

- The route is a catalogue surface only. It must not compute lot longitudes.
- Catalogue order should remain deterministic.

Response:

- Ordered list of `PartDefinition` response vessels.

### 2.2 Chart-Backed Lot Result

Route:

- `POST /v1/lots/chart`

Transport stance:

- `bounded_sync`

Purpose:

- Compute all currently resolvable `ArabicPart` results from a
  timezone-aware chart request, deriving planet positions, node positions,
  house cusps, and day/night state through Moira.

Required input doctrine:

- timezone-aware datetime
- observer latitude
- observer longitude
- optional observer elevation
- house system
- optional explicit `LotsComputationPolicy`
- optional external support longitudes:
  - `syzygy`
  - `prenatal_new_moon`
  - `prenatal_full_moon`
  - `lord_of_hour`

Engine path:

1. Build a planet/node `Chart` through the stable injected `Moira` instance.
2. Build houses through the same injected `Moira` instance.
3. Materialize engine `planet_longitudes` from the chart planets and nodes.
4. Materialize engine `house_cusps` as a complete 1-indexed house cusp map.
5. Derive `is_day_chart` from chart-backed Sun and Ascendant truth.
6. Build `LotsComputationPolicy` only from explicit transport policy.
7. Pass optional external longitudes only when supplied by the caller.
8. Call `ArabicPartsService.calculate_parts(...)`.

Truth boundary:

- The server owns chart-backed planets, nodes, houses, and day/night
  derivation.
- Optional externals are caller-owned support truth; the route must not derive
  or invent prenatal lunations, Syzygy, or Lord of Hour.
- The REST service must not recompute formulas, dependency truth, condition
  profiles, or network truth independently.

Response:

- Ordered list of `ArabicPart` response vessels.

### 2.3 Chart-Backed Lot Dependencies

Route:

- `POST /v1/lots/chart/dependencies`

Transport stance:

- `bounded_sync`

Purpose:

- Compute formal `LotDependency` relations for the currently computable lots
  from server-derived chart truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/lots/chart`.
2. Call `ArabicPartsService.calculate_dependencies(...)`.

Truth boundary:

- Dependency truth is relational truth, not interpretation.
- Add and subtract operand roles must remain visible.
- Direct, inter-lot, external, and other reference kinds must remain visible.

Response:

- Ordered list of `LotDependency` response vessels.

### 2.4 Chart-Backed Per-Lot Condition Profiles

Route:

- `POST /v1/lots/chart/conditions`

Transport stance:

- `bounded_sync`

Purpose:

- Compute all `LotConditionProfile` results from server-derived chart truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/lots/chart`.
2. Call `ArabicPartsService.calculate_condition_profiles(...)`.

Response:

- Ordered list of `LotConditionProfile` response vessels.

### 2.5 Chart-Backed Single Lot Condition Profile

Route:

- `POST /v1/lots/chart/condition`

Transport stance:

- `bounded_sync`

Purpose:

- Compute one `LotConditionProfile` from server-derived chart truth.

Required additional input:

- `part_name`

Engine path:

1. Follow the same chart-backed derivation path as `/v1/lots/chart`.
2. Call `ArabicPartsService.calculate_condition_profiles(...)`.
3. Select the requested `part_name` exactly from the returned profiles.

Response:

- `LotConditionProfile` only.

### 2.6 Chart-Backed Chart Condition Profile

Route:

- `POST /v1/lots/chart/profile`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the chart-wide `LotChartConditionProfile` from server-derived chart
  truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/lots/chart`.
2. Call `ArabicPartsService.calculate_chart_condition_profile(...)`.

Response:

- `LotChartConditionProfile` only.
- The full lot result is not silently bundled into the profile response.

### 2.7 Chart-Backed Lot Dependency Network

Route:

- `POST /v1/lots/chart/network`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the directed dependency / condition network from server-derived
  chart truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/lots/chart`.
2. Call `ArabicPartsService.calculate_condition_network_profile(...)`.

Response:

- `LotConditionNetworkProfile` only.
- Nodes, directed edges, isolated lots, most-connected lots, and reciprocal
  versus unilateral edge counts must remain visible.

---

## 3. Deferred Direct Expert Surface

The following direct routes are intentionally not part of first admission:

- `POST /v1/lots/direct`
- `POST /v1/lots/direct/dependencies`
- `POST /v1/lots/direct/conditions`
- `POST /v1/lots/direct/condition`
- `POST /v1/lots/direct/profile`
- `POST /v1/lots/direct/network`

Reason:

- `ArabicPartsService` consumes a coherent chart bundle: planet and node
  longitudes, house cusps, day/night state, optional external longitudes, and
  explicit lots policy.
- Individually valid longitudes and house cusps can still form an incoherent
  chart if they were not derived from the same time, observer, and house
  policy.
- First admission should therefore let the server own chart derivation. The
  direct expert surface can be admitted later after a strict caller-owned
  consistency contract is written.

Direct admission can be reconsidered after the chart-backed family is live and
the request contract can prove at least:

- required classical planets are present
- node aliases are explicit where node-dependent lots are expected
- all longitudes and house cusps are finite
- each longitude is normalized or clearly caller-owned before normalization
- twelve houses are present exactly once
- `is_day_chart` is explicitly caller-owned and not recomputed silently
- optional externals are explicitly caller-owned
- policy is explicit and valid
- caller-owned chart truth is not mixed with server-derived support truth

---

## 4. Required Policy Semantics

The request policy must map only to `LotsComputationPolicy` and its nested
policy vessels:

- `LotsComputationPolicy.unresolved_reference_mode`
- `LotsComputationPolicy.derived`
- `LotsComputationPolicy.external`
- `LotsDerivedReferencePolicy.include_fortune`
- `LotsDerivedReferencePolicy.include_spirit`
- `LotsDerivedReferencePolicy.include_eros_valens`
- `LotsExternalReferencePolicy.include_syzygy`
- `LotsExternalReferencePolicy.include_prenatal_new_moon`
- `LotsExternalReferencePolicy.include_prenatal_full_moon`
- `LotsExternalReferencePolicy.include_lord_of_hour`

The REST layer must reject unknown policy values rather than silently falling
back to the default doctrine.

The default request policy is omission, which means the engine default
`LotsComputationPolicy()` is used.

---

## 5. Required Response Semantics

`PartDefinition` responses must preserve:

- `name`
- `day_add`
- `day_sub`
- `reverse_at_night`
- `category`
- `description`

`ArabicPart` responses must preserve at minimum:

- `name`
- `longitude`
- `formula`
- `category`
- `description`
- `computation_truth`
- `classification`
- `all_dependencies`
- `dependencies`
- `condition_profile`
- `sign`
- `sign_symbol`
- `sign_degree`
- `longitude_dms`
- `category_tags`
- `primary_category`
- `reversal_kind`
- `is_reversed`
- `add_reference_kind`
- `sub_reference_kind`
- `dependency_count`
- `all_dependency_count`
- `inter_lot_dependencies`
- `external_dependencies`
- `condition_state`

`LotDependency` responses must preserve:

- `part_name`
- `role`
- `requested_key`
- `effective_key`
- `reference_kind`
- `reference_longitude`
- `detail`
- `is_inter_lot`
- `is_external`
- `is_indirect`

`LotConditionProfile` responses must preserve:

- `part_name`
- `category_tags`
- `primary_category`
- `reversal`
- `all_dependencies`
- `dependencies`
- dependency counts
- `state`
- `has_inter_lot_dependency`
- `has_external_dependency`

`LotChartConditionProfile` responses must preserve:

- `profiles`
- state counts
- dependency totals
- strongest and weakest parts
- profile, strongest, and weakest counts

`LotConditionNetworkProfile` responses must preserve:

- `nodes`
- `edges`
- `isolated_parts`
- `most_connected_parts`
- `reciprocal_edge_count`
- `unilateral_edge_count`
- node and edge counts

---

## 6. Explicit Non-Goals

The first P9-05 admission does not expose:

- generic `/v1/classical` umbrella routes
- single-lot interpretive meanings
- textual judgment or recommendation logic
- direct caller-owned chart bundles
- prenatal lunation derivation
- planetary hour derivation
- lot filtering/search beyond catalogue exposure
- lots hidden inside dignity or triplicity routes

---

## 7. Verification Requirements For Admission

Before P9-05 can be marked admitted, implementation must verify:

- catalogue route preserves deterministic `PartDefinition` data
- service derivation uses the injected `moira_engine` runtime path
- timezone-aware datetimes are accepted on chart-backed routes
- naive datetimes are rejected on chart-backed routes
- non-finite latitude, longitude, elevation, or optional external support
  longitudes are rejected
- invalid house systems are rejected
- invalid policy enum values are rejected
- all live result routes preserve deterministic lot ordering
- `ArabicPart.formula == computation_truth.formula` whenever truth is present
- `dependencies` are a subset of `all_dependencies`
- condition profile counts match serialized dependencies
- chart condition profile counts match serialized profiles
- network edge counts match serialized edges
- route registration appears in startup route inventory

Suggested tests:

- `tests/server/test_server_lots_service.py`
- `tests/server/test_server_lots_routes.py`
- existing startup and error-mapping server tests

---

## 8. Admission State

P9-05 is designed, not implemented.

Next implementation files are expected to be:

- `moira_server/models/lots.py`
- `moira_server/serializers/lots.py`
- `moira_server/services/lots.py`
- `moira_server/routers/lots.py`
- updates to `moira_server/app.py`
- updates to package `__init__.py` exports
- updates to `wiki/02_services/REST_API_REFERENCE.md` after routes are live
