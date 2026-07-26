# P9-12 Decans / Decanates Transport Design

Version: 0.3
Date: 2026-07-26
Status: P9-12 Decanates routes admitted; all Hermetic transport removed
Scope: Phase 9 decans/decanates REST admission design

This document records the admitted REST route shapes for `moira.decanates` and
the containment boundary for the research-only `moira.hermetic_decans`.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/DECANS_BACKEND_STANDARD.md`

---

## 1. Route Families

Decanate router prefix:

- `/v1/decanates`

Reason:

- Decanate placement and the source-reconstructed Hermetic catalog are distinct
  products with different admission states.
- No `/v1/hermetic-decans` router, transport model, service, or serializer is
  retained while the direct engine module remains in research quarantine.
- A generic `/v1/classical` endpoint is not admitted.

---

## 2. Transport Stance

The first admission was direct-sync. Post-Phase-9 hardening adds chart-backed
body routes for the Decanates family through the shared
`SiderealChartContext` workflow.

Decanate routes consume:

- caller-supplied longitude
- optional JD and ayanamsa policy for Vedic drekkana

Transport must reject:

- non-finite longitudes
- non-finite Julian dates

---

## 3. Initial Route Shapes

### 3.1 Chaldean Face

Route:

- `POST /v1/decanates/chaldean-face`

Purpose:

- Resolve a `DecanatePosition` from `chaldean_face(...)`.

Input:

- `longitude`

Response:

- `DecanatePosition`

### 3.2 Triplicity Decan

Route:

- `POST /v1/decanates/triplicity`

Purpose:

- Resolve a `DecanatePosition` from `triplicity_decan(...)`.

Input:

- `longitude`

Response:

- `DecanatePosition`

### 3.3 Vedic Drekkana

Route:

- `POST /v1/decanates/vedic-drekkana`

Purpose:

- Resolve a `DecanatePosition` from `vedic_drekkana(...)`.

Input:

- `longitude`
- `jd`
- optional `ayanamsa_system`

Response:

- `DecanatePosition`

### 3.4 Decanate Set

Route:

- `POST /v1/decanates/set`

Purpose:

- Resolve all three currently implemented decanate systems for one longitude.

Input:

- `longitude`
- `jd`
- optional `ayanamsa_system`

Response:

- `chaldean_face`
- `triplicity`
- `vedic_drekkana`

### 3.5 Hermetic Transport Non-Admission

The former candidate routes were removed on 2026-07-26:

- `GET /v1/hermetic-decans/catalog`
- `POST /v1/hermetic-decans/longitude`
- `POST /v1/hermetic-decans/rising`
- `POST /v1/hermetic-decans/night-hours`

The catalog and projection policies remain direct-module research material,
not a public REST contract. The fixed-star assignments required by the former
response models are not present in the identified Gundel/Harley witness. The
night-hour experiment likewise lacked an identified authority for its
sunset-Midheaven plus twelve equal temporal-hour composition.

Any future stellar decanal-clock proposal is a new product requiring its own
table family, epoch, observer, rising-versus-transit semantics, visibility
policy, and validation contract.

### 3.6 Chart-Backed Vedic Drekkana

Route:

- `POST /v1/decanates/chart/vedic-drekkana`

Purpose:

- Derive one chart body's tropical longitude and JD, then resolve
  `vedic_drekkana(...)`.

Input:

- `dt`
- `body`
- optional `ayanamsa_system`

Response:

- `body`
- `result`
- derived `tropical_longitude`
- derived `jd`
- sidereal chart provenance

### 3.7 Chart-Backed Decanate Set

Route:

- `POST /v1/decanates/chart/set`

Purpose:

- Derive one chart body's tropical longitude and JD, then resolve the
  Chaldean face, triplicity decan, and Vedic drekkana for that body.

Input:

- `dt`
- `body`
- optional `ayanamsa_system`

Response:

- `body`
- `result`
- derived `tropical_longitude`
- derived `jd`
- sidereal chart provenance

---

## 4. Response Semantics

`DecanatePosition` responses preserve all engine vessel fields:

- `system`
- `decan_number`
- `ruling_planet`
- `ruling_sign`
- `sign`
- `sign_symbol`
- `degree_in_decan`
- `longitude_used`

## 5. Explicit Non-Goals

P9-12 does not expose:

- any Hermetic catalog, longitude, rising, or night-hour transport
- interpretive decan meanings
- fixed-star position lookup for ruling stars
- sidereal Egyptian decan star-clock reconstruction
- zodiacal catalog labels projected onto equal sunset-to-sunrise intervals
- generic `/v1/classical` umbrella routes

---

## 6. Verification Requirements For Admission

Implementation must verify:

- each decanate route matches the engine function result
- decanate set preserves all three doctrine keys
- every `/v1/hermetic-decans` path is absent from the application and OpenAPI
- Hermetic transport models, services, serializers, and routers remain absent
- unsupported night-hour engine symbols remain absent
- non-finite longitude and JD inputs are rejected
- route registration appears in startup route inventory

Verification files to add:

- `tests/server/test_server_decans_routes.py`

Existing engine verification slice:

- `tests/unit/test_decanates.py`
- `tests/unit/test_hermetic_decans.py`

---

## 7. Admission State

P9-12 Decanates transport is admitted. Hermetic catalog, longitude, rising,
and night-hour transport code is absent; `create_app()` and OpenAPI expose no
`/v1/hermetic-decans` path.

Implemented files:

- `moira_server/models/decans.py`
- `moira_server/serializers/decans.py`
- `moira_server/services/decans.py`
- `moira_server/routers/decans.py`
- Decanates-only route registration in `moira_server/app.py`
- package `__init__.py` exports for the admitted Decanates transport
- `tests/server/test_server_decans_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md` route inventory updates
