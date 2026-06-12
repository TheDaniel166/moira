# P9-08 Vedic Dignities Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-08 admitted; four direct-sync and three chart-backed Vedic Dignities routes live and tested
Scope: Phase 9 Vedic Dignities REST admission design

This document declares the REST route shapes admitted for the Vedic Dignities
family and records the implemented transport admission state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/VEDIC_DIGNITIES_BACKEND_STANDARD.md`

The governing engine object is Parashari dignity and planetary relationship
truth over caller-supplied sidereal longitudes:

- dignity rank
- exaltation/debilitation flags
- Mulatrikona and own-sign flags
- exaltation score
- local dignity condition tier
- directed Panchadha Maitri relationships
- chart-level dignity profile
- ayanamsa provenance policy

The authoritative engine functions are:

- `moira.vedic_dignities.vedic_dignity(...)`
- `moira.vedic_dignities.planetary_relationships(...)`
- `moira.vedic_dignities.dignity_condition_profile(...)`
- `moira.vedic_dignities.chart_dignity_profile(...)`
- `moira.vedic_dignities.validate_dignity_output(...)`

---

## 1. Route Family

Router prefix:

- `/v1/vedic-dignities`

Route tag:

- `vedic-dignities`

This family is live. The admitted paths in this document are registered by the
FastAPI application and documented in `wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Dignity Result

Route:

- `POST /v1/vedic-dignities/dignity`

Transport stance:

- `direct_sync`

Purpose:

- Resolve one `VedicDignityResult` for a classical planet at a caller-supplied
  sidereal longitude.

Required input doctrine:

- `planet`
- `sidereal_longitude`
- optional `policy.ayanamsa_system`, default `Lahiri`

Engine path:

1. Validate non-empty planet, finite longitude, and non-empty ayanamsa label.
2. Call `vedic_dignity(planet, sidereal_longitude)`.
3. Serialize the result with the policy provenance label.

Truth boundary:

- This route consumes sidereal longitude.
- The server must not imply that the engine performed ayanamsa conversion.
- The response must preserve both normalized sidereal longitude and the
  caller/server-declared ayanamsa provenance label.

Response:

- One `VedicDignityResult` response vessel.

### 2.2 Relationships

Route:

- `POST /v1/vedic-dignities/relationships`

Transport stance:

- `direct_sync`

Purpose:

- Resolve directed Panchadha Maitri relationships among the classical planets
  present in a caller-supplied sidereal longitude map.

Required input doctrine:

- `sidereal_longitudes`
- optional `policy.ayanamsa_system`, default `Lahiri`

Engine path:

1. Validate mapping is non-empty.
2. Validate every supplied longitude is finite.
3. Call `planetary_relationships(sidereal_longitudes)`.

Truth boundary:

- The engine silently ignores non-classical keys in
  `planetary_relationships(...)`. REST should preserve that engine behavior
  unless a future transport policy explicitly rejects unknown keys.
- The response must preserve directional relation truth. Do not collapse
  relations into an undirected friendship matrix.

Response:

- Ordered list of `PlanetaryRelationship` response vessels.

### 2.3 Dignity Condition

Route:

- `POST /v1/vedic-dignities/condition`

Transport stance:

- `direct_sync`

Purpose:

- Resolve the local dignity condition tier for one planet/sidereal longitude
  pair.

Required input doctrine:

- `planet`
- `sidereal_longitude`
- optional `policy.ayanamsa_system`, default `Lahiri`

Engine path:

1. Call `vedic_dignity(...)`.
2. Call `dignity_condition_profile(result)`.
3. Serialize both the dignity result and condition profile truth.

Response:

- One `DignityConditionProfile` response vessel with the source dignity result
  included or adjacent in the response.

### 2.4 Chart Dignity Profile

Route:

- `POST /v1/vedic-dignities/chart-profile`

Transport stance:

- `direct_sync`

Purpose:

- Resolve a chart-level Vedic dignity profile from caller-supplied sidereal
  longitudes.

Required input doctrine:

- `sidereal_longitudes`
- optional `policy.ayanamsa_system`, default `Lahiri`

Engine path:

1. Validate mapping is non-empty.
2. Validate every supplied longitude is finite.
3. Build a dignity result for each classical planet present in the map.
4. Call `validate_dignity_output(results)`.
5. Call `chart_dignity_profile(results)`.

Truth boundary:

- The REST service should preserve the per-planet dignity results alongside
  the aggregate profile. The aggregate alone is not enough proof of chart
  dignity truth.
- The chart profile should not fabricate missing planets. It should operate on
  the participating classical planets supplied by the caller.

Response:

- One chart dignity profile response containing:
  - policy provenance
  - per-planet dignity results
  - aggregate `ChartDignityProfile`

---

## 3. Chart-Backed Surface

The following route shapes are admitted after the post-Phase-9 shared
`SiderealChartContext` workflow:

- `POST /v1/vedic-dignities/chart/dignity`
- `POST /v1/vedic-dignities/chart/relationships`
- `POST /v1/vedic-dignities/chart/profile`

Reason:

- `moira.vedic_dignities` expects sidereal longitudes.
- It does not compute tropical positions or ayanamsa reduction.
- Chart-backed routes require a server adapter that visibly owns
  tropical-to-sidereal derivation, ayanamsa choice, and planetary inclusion
  policy before calling this module.

Implementation:

- Chart-backed Vedic Dignities routes use
  `docs/architecture/POST_PHASE9_SIDEREAL_CHART_DERIVATION_WORKFLOW.md`.
- Responses embed compact sidereal chart provenance.
- Direct-vs-chart parity is verified in
  `tests/server/test_server_vedic_dignities_routes.py`.

---

## 4. Required Response Semantics

`VedicDignityResult` responses must preserve:

- `planet`
- `sidereal_longitude`
- `sign_index`
- `sign`
- `dignity_rank`
- `is_exalted`
- `is_debilitated`
- `is_mulatrikona`
- `is_own_sign`
- `is_strong`
- `is_weak`
- `exaltation_score`
- `ayanamsa_system`

`PlanetaryRelationship` responses must preserve:

- `from_planet`
- `to_planet`
- `natural`
- `temporary`
- `compound`
- `is_friendly`
- `is_hostile`

`DignityConditionProfile` responses must preserve:

- `planet`
- `dignity_rank`
- `tier`
- `exaltation_score`
- `sign_index`
- `sign`
- source dignity result
- `ayanamsa_system`

`ChartDignityProfile` responses must preserve:

- `strong_count`
- `neutral_count`
- `weak_count`
- `strongest_planet`
- `weakest_planet`
- `planet_tiers`
- `exaltation_scores`
- per-planet dignity results
- `ayanamsa_system`

---

## 5. Explicit Non-Goals

The first P9-08 admission does not expose:

- tropical-to-sidereal conversion
- chart-backed derivation
- Rahu/Ketu dignity
- outer planet dignity
- Shadbala integration
- Varga-derived dignity
- interpretive meanings
- generic `/v1/vedic` umbrella routes
- generic `/v1/classical` dignity aggregation

---

## 6. Verification Requirements For Admission

P9-08 admission verified:

- dignity route preserves each `VedicDignityResult` field and inspectability
  flag for at least exaltation, debilitation, Mulatrikona, own-sign,
  friend-sign, neutral-sign, and enemy-sign examples
- Mercury Virgo overlap resolves to exaltation
- longitude wrapping is preserved in the response
- relationships route preserves directional natural, temporary, and compound
  relationship truth
- condition route preserves strong/neutral/weak tier truth
- chart-profile route preserves aggregate counts and strongest/weakest planet
  truth
- invalid planets are rejected through the server error envelope
- malformed or non-finite longitude inputs are rejected by transport
  validation
- empty chart-profile maps are rejected
- non-empty `ayanamsa_system` is enforced
- route registration appears in startup route inventory

Verification files:

- `tests/server/test_server_vedic_dignities_routes.py`
- existing startup and error-mapping server tests
- existing engine standard slice:
  - `tests/unit/test_vedic_dignities.py`
  - `tests/unit/test_public_doctrine_surfaces.py`
  - `tests/unit/test_api_surface_adversarial_audit.py`

---

## 7. Admission State

P9-08 is admitted.

Implemented files:

- `moira_server/models/vedic_dignities.py`
- `moira_server/serializers/vedic_dignities.py`
- `moira_server/services/vedic_dignities.py`
- `moira_server/routers/vedic_dignities.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_vedic_dignities_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md`
