# P9-12 Decans / Decanates Transport Design

Version: 0.1
Date: 2026-06-11
Status: P9-12 admitted; eight direct-sync and two chart-backed decans/decanates routes live and tested
Scope: Phase 9 decans/decanates REST admission design

This document declares the REST route shapes admitted for `moira.decanates`
and `moira.hermetic_decans`.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/DECANS_BACKEND_STANDARD.md`

---

## 1. Route Families

Decanate router prefix:

- `/v1/decanates`

Hermetic decan router prefix:

- `/v1/hermetic-decans`

Reason:

- Decanate placement and Hermetic decan-hour computation are related but not
  the same computational product.
- A generic `/v1/classical` endpoint is not admitted.

---

## 2. Transport Stance

The first admission was direct-sync. Post-Phase-9 hardening adds chart-backed
body routes for the Decanates family through the shared
`SiderealChartContext` workflow.

Decanate routes consume:

- caller-supplied longitude
- optional JD and ayanamsa policy for Vedic drekkana

Hermetic routes consume:

- tropical longitude for catalog/longitude lookup
- explicit JD/location for rising decan and night hours

Transport must reject:

- non-finite longitudes
- non-finite Julian dates
- non-finite observer coordinates
- invalid latitude ranges for location-backed routes
- unknown Hermetic decan names where a name is supplied

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

### 3.5 Hermetic Catalog

Route:

- `GET /v1/hermetic-decans/catalog`

Purpose:

- Return the 36 Hermetic decan names in ecliptic order and their ruling-star
  assignments.

Response:

- ordered entries with `index`, `name`, and `ruling_star`

### 3.6 Hermetic Longitude Lookup

Route:

- `POST /v1/hermetic-decans/longitude`

Purpose:

- Resolve the Hermetic decan containing a tropical longitude.

Input:

- `longitude`

Response:

- `longitude`
- `normalized_longitude`
- `index`
- `name`
- `ruling_star`

### 3.7 Hermetic Rising Decan

Route:

- `POST /v1/hermetic-decans/rising`

Purpose:

- Resolve the Hermetic decan containing the Ascendant at an instant/location.

Input:

- `jd`
- `latitude`
- `longitude`

Response:

- input echo plus decan lookup fields

### 3.8 Hermetic Night Hours

Route:

- `POST /v1/hermetic-decans/night-hours`

Purpose:

- Resolve the twelve Hermetic decan hours for the night containing the given
  JD at the observer location.

Input:

- `jd`
- `latitude`
- `longitude`

Response:

- night boundary fields plus twelve `DecanHour` entries

### 3.9 Chart-Backed Vedic Drekkana

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

### 3.10 Chart-Backed Decanate Set

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

Hermetic decan lookup responses preserve:

- source longitude when applicable
- normalized tropical longitude
- decan index
- decan name
- ruling-star assignment

Night-hour responses preserve exact JD boundaries; they do not convert JD
intervals into civil times.

---

## 5. Explicit Non-Goals

P9-12 does not expose:

- interpretive decan meanings
- fixed-star position lookup for ruling stars
- sidereal Egyptian decan star-clock reconstruction
- generic `/v1/classical` umbrella routes

---

## 6. Verification Requirements For Admission

Implementation must verify:

- each decanate route matches the engine function result
- decanate set preserves all three doctrine keys
- Hermetic catalog returns 36 ordered entries
- Hermetic longitude lookup matches `decan_for_longitude(...)`
- Hermetic rising route matches `decan_at(...)`
- Hermetic night-hour route serializes `DecanHoursNight` without flattening
  hour boundaries
- non-finite longitude/JD/location inputs are rejected
- invalid latitudes are rejected
- route registration appears in startup route inventory

Verification files to add:

- `tests/server/test_server_decans_routes.py`

Existing engine verification slice:

- `tests/unit/test_decanates.py`
- `tests/unit/test_hermetic_decans.py`

---

## 7. Admission State

P9-12 is admitted.

Implemented files:

- `moira_server/models/decans.py`
- `moira_server/serializers/decans.py`
- `moira_server/services/decans.py`
- `moira_server/routers/decans.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_decans_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md` route inventory updates
