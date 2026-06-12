# P9-09 Ashtakavarga Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-09 admitted; four direct-sync and four chart-backed Ashtakavarga routes live and tested
Scope: Phase 9 Ashtakavarga REST admission design

This document declares the REST route shapes admitted for the Ashtakavarga
family and records the implemented transport admission state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/ASHTAKAVARGA_BACKEND_STANDARD.md`

The governing engine object is Parashari Ashtakavarga truth over caller-supplied
sidereal longitudes or sign indices:

- seven planetary Bhinnashtakavarga tables
- Sarvashtakavarga aggregate table
- optional Trikona and Ekadhipatya Shodhana reductions
- local sign-strength profile
- transit-strength lookup
- chart-level aggregate profile
- ayanamsa provenance policy

The authoritative engine functions are:

- `moira.ashtakavarga.ashtakavarga(...)`
- `moira.ashtakavarga.sign_strength_profile(...)`
- `moira.ashtakavarga.transit_strength(...)`
- `moira.ashtakavarga.ashtakavarga_chart_profile(...)`
- `moira.ashtakavarga.validate_ashtakavarga_output(...)`

---

## 1. Route Family

Router prefix:

- `/v1/ashtakavarga`

Route tag:

- `ashtakavarga`

This family is live. The admitted paths in this document are registered by the
FastAPI application and documented in `wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Input Stance

The first admission is direct-sync.

Each computation route accepts exactly one input form:

- `sidereal_longitudes`: mapping of body/reference name to sidereal longitude
- `sign_indices`: mapping of body/reference name to sidereal sign index

Required references:

- `Sun`
- `Moon`
- `Mars`
- `Mercury`
- `Jupiter`
- `Venus`
- `Saturn`
- `Lagna`

The server does not derive those values from a datetime/location chart in this
first admission.

Policy fields:

- `ayanamsa_system`, default `Lahiri`
- `strong_threshold`, default `4`, admitted range `[1, 8]`
- `apply_trikona_shodhana`, default `false`
- `apply_ekadhipatya_shodhana`, default `false`

`apply_ekadhipatya_shodhana` requires `apply_trikona_shodhana`.

---

## 3. Initial Route Shapes

### 3.1 Full Result

Route:

- `POST /v1/ashtakavarga/result`

Transport stance:

- `direct_sync`

Purpose:

- Resolve the full `AshtakavargaResult` from caller-supplied sidereal/sign
  truth.

Response preserves:

- `ayanamsa_system`
- per-planet `BhinnashtakavargaResult`
- `sarvashtakavarga`
- optional `shodhana_bhinnashtakavarga`
- optional `shodhana_sarvashtakavarga`

### 3.2 Chart Profile

Route:

- `POST /v1/ashtakavarga/profile`

Transport stance:

- `direct_sync`

Purpose:

- Resolve the chart-level aggregate profile from a full Ashtakavarga result.

Response preserves:

- full source result
- `sarva_total`
- `sarva_max`
- `sarva_max_sign_idx`
- `sarva_min`
- `sarva_min_sign_idx`
- `strong_planet_sign_counts`

### 3.3 Sign Profile

Route:

- `POST /v1/ashtakavarga/sign-profile`

Transport stance:

- `direct_sync`

Purpose:

- Resolve one `SignStrengthProfile` for a planet and sign from a computed
  Bhinnashtakavarga table.

Required extra input:

- `planet`
- `sign_index`

Response preserves:

- `planet`
- `sign_idx`
- `rekha_count`
- `tier`
- `ayanamsa_system`

### 3.4 Transit Strength

Route:

- `POST /v1/ashtakavarga/transit-strength`

Transport stance:

- `direct_sync`

Purpose:

- Resolve the rekha count for a planet transiting a supplied sidereal sign.

Required extra input:

- `planet`
- `transit_sign_index`

Response preserves:

- `planet`
- `transit_sign_index`
- `rekha_count`
- `tier`
- `ayanamsa_system`

---

## 4. Chart-Backed Surface

Chart-backed Ashtakavarga is admitted after the post-Phase-9 shared
`SiderealChartContext` workflow.

Live shapes:

- `POST /v1/ashtakavarga/chart/result`
- `POST /v1/ashtakavarga/chart/profile`
- `POST /v1/ashtakavarga/chart/sign-profile`
- `POST /v1/ashtakavarga/chart/transit-strength`

Reason:

- `moira.ashtakavarga` consumes sidereal longitudes or sign indices.
- It does not compute tropical positions.
- It does not compute ayanamsa reduction.
- It does not derive Lagna from datetime/location/houses.

The chart-backed route family uses the shared post-Phase-9 adapter to visibly
perform:

- tropical planetary derivation
- explicit ayanamsa reduction
- sidereal Lagna derivation
- reduction provenance serialization

Implementation:

- Chart-backed requests require observer latitude and longitude because Lagna
  is a required Ashtakavarga reference.
- Responses embed compact sidereal chart provenance.
- Direct-vs-chart parity is verified in
  `tests/server/test_server_ashtakavarga_routes.py`.

---

## 5. Explicit Non-Goals

P9-09 does not expose:

- interpretive prediction text
- Varga integration
- Shadbala integration
- generic `/v1/vedic` umbrella routes

---

## 6. Verification Requirements For Admission

P9-09 admission verified:

- result route preserves Bhinnashtakavarga and Sarvashtakavarga truth
- sign-index input form produces the same engine truth as equivalent sign-start
  sidereal longitudes
- shodhana policy is preserved and validated
- profile route preserves aggregate profile truth and source result truth
- sign-profile route preserves local strength tier truth
- transit-strength route preserves direct rekha-count truth
- missing `Lagna` is rejected
- dual input forms are rejected
- empty `ayanamsa_system` is rejected
- invalid shodhana policy is rejected
- invalid sign indices are rejected
- route registration appears in startup route inventory

Verification files:

- `tests/server/test_server_ashtakavarga_routes.py`
- existing startup and error-mapping server tests
- existing engine standard slice:
  - `tests/unit/test_ashtakavarga.py`
  - `tests/unit/test_public_doctrine_surfaces.py`
  - `tests/unit/test_api_surface_adversarial_audit.py`

---

## 7. Admission State

P9-09 is admitted.

Implemented files:

- `moira_server/models/ashtakavarga.py`
- `moira_server/serializers/ashtakavarga.py`
- `moira_server/services/ashtakavarga.py`
- `moira_server/routers/ashtakavarga.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_ashtakavarga_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md`
