# P9-11 Varga Transport Design

Version: 0.1
Date: 2026-06-11
Status: P9-11 admitted; five direct-sync and three chart-backed Varga routes live and tested
Scope: Phase 9 Varga REST admission design

This document declares the REST route shapes admitted for Vedic
divisional-chart placement implemented in `moira.varga` and records the
implemented transport admission state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/VARGA_BACKEND_STANDARD.md`

The governing engine object is Varga placement truth over caller-supplied
sidereal longitude:

- source sidereal longitude
- varga division number
- varga display name
- mapped varga longitude
- mapped varga sign
- mapped varga sign symbol
- degree within mapped varga sign

The authoritative engine functions are:

- `moira.varga.calculate_varga(...)`
- `moira.varga.navamsa(...)`
- `moira.varga.saptamsa(...)`
- `moira.varga.dashamansa(...)`
- `moira.varga.dwadashamsa(...)`
- `moira.varga.trimshamsa(...)`
- `moira.varga.hora(...)`
- `moira.varga.chaturthamsha(...)`
- `moira.varga.shashthamsha(...)`
- `moira.varga.ashtamsha(...)`
- `moira.varga.shodashamsha(...)`
- `moira.varga.vimshamsha(...)`
- `moira.varga.chaturvimshamsha(...)`
- `moira.varga.saptavimshamsha(...)`
- `moira.varga.khavedamsha(...)`
- `moira.varga.akshavedamsha(...)`
- `moira.varga.shashtiamsha(...)`

---

## 1. Route Family

Router prefix:

- `/v1/varga`

Route tag:

- `varga`

Reason:

- Varga is a named Vedic doctrine family, not an umbrella route.
- A generic `/v1/vedic` endpoint is not admitted.
- The route family should remain direct-sync until the server owns a shared
  sidereal chart reduction adapter.

---

## 2. Initial Transport Stance

The first admission is direct-sync.

Required base input:

- `sidereal_longitude`

Transport must reject:

- non-finite `sidereal_longitude`
- invalid generic divisor values
- unknown named varga keys
- empty batch payloads
- duplicate body keys in object-map batch forms, if map forms are admitted

The engine currently normalizes longitude modulo 360. Transport should preserve
that behavior in responses by returning the normalized `VargaPoint.longitude`.

---

## 3. Varga Selector Vocabulary

Transport should admit a stable selector vocabulary rather than exposing Python
function names as the primary public contract.

Named Shodashvarga selectors:

| Selector | Function | Division |
|---|---|---:|
| `hora` | `hora` | 2 |
| `chaturthamsha` | `chaturthamsha` | 4 |
| `shashthamsha` | `shashthamsha` | 6 |
| `saptamsa` | `saptamsa` | 7 |
| `ashtamsha` | `ashtamsha` | 8 |
| `navamsa` | `navamsa` | 9 |
| `dashamansa` | `dashamansa` | 10 |
| `dwadashamsa` | `dwadashamsa` | 12 |
| `shodashamsha` | `shodashamsha` | 16 |
| `vimshamsha` | `vimshamsha` | 20 |
| `chaturvimshamsha` | `chaturvimshamsha` | 24 |
| `saptavimshamsha` | `saptavimshamsha` | 27 |
| `trimshamsa` | `trimshamsa` | 30 |
| `khavedamsha` | `khavedamsha` | 40 |
| `akshavedamsha` | `akshavedamsha` | 45 |
| `shashtiamsha` | `shashtiamsha` | 60 |

Generic route divisors should be accepted only as positive integers. First
admission should use a conservative range, `1 <= divisor <= 60`, because the
public surface is oriented around Shodashvarga and D60 is the highest named
division currently exposed.

---

## 4. Initial Route Shapes

### 4.1 Generic Varga

Route:

- `POST /v1/varga/generic`

Transport stance:

- `direct_sync`

Purpose:

- Resolve a `VargaPoint` using `calculate_varga(...)` for a caller-supplied
  sidereal longitude and divisor.

Required input:

- `sidereal_longitude`
- `divisor`
- optional `name`

Engine path:

1. Validate finite `sidereal_longitude`.
2. Validate `divisor` in `[1, 60]`.
3. Call `calculate_varga(sidereal_longitude, divisor, name or "")`.
4. Serialize `VargaPoint`.

Response:

- one `VargaPoint` response vessel.

### 4.2 Named Varga

Route:

- `POST /v1/varga/named`

Transport stance:

- `direct_sync`

Purpose:

- Resolve one named Shodashvarga wrapper for a caller-supplied sidereal
  longitude.

Required input:

- `sidereal_longitude`
- `varga`

Engine path:

1. Validate finite `sidereal_longitude`.
2. Validate `varga` against the selector vocabulary.
3. Dispatch to the named wrapper function.
4. Serialize `VargaPoint`.

Response:

- one `VargaPoint` response vessel.

### 4.3 Shodashvarga Set

Route:

- `POST /v1/varga/shodashvarga`

Transport stance:

- `direct_sync`

Purpose:

- Resolve all 16 named Shodashvarga placements for one caller-supplied
  sidereal longitude.

Required input:

- `sidereal_longitude`

Engine path:

1. Validate finite `sidereal_longitude`.
2. Call all named Shodashvarga wrapper functions.
3. Serialize a selector-keyed map of `VargaPoint` responses.

Response:

- `sidereal_longitude`
- `vargas`: map from selector to `VargaPoint`

### 4.4 Named Batch

Route:

- `POST /v1/varga/named/batch`

Transport stance:

- `direct_sync`

Purpose:

- Resolve one named varga for multiple caller-supplied bodies or points.

Required input:

- `varga`
- `longitudes`: object map from body/point key to sidereal longitude

Engine path:

1. Validate non-empty `longitudes`.
2. Validate all keys are non-empty.
3. Validate all longitudes are finite.
4. Validate `varga` against the selector vocabulary.
5. Dispatch once per item.
6. Serialize a key-preserving result map.

Response:

- `varga`
- `results`: map from caller key to `VargaPoint`

### 4.5 Shodashvarga Batch

Route:

- `POST /v1/varga/shodashvarga/batch`

Transport stance:

- `direct_sync`

Purpose:

- Resolve all 16 named Shodashvarga placements for multiple caller-supplied
  bodies or points.

Required input:

- `longitudes`: object map from body/point key to sidereal longitude

Engine path:

1. Validate non-empty `longitudes`.
2. Validate all keys are non-empty.
3. Validate all longitudes are finite.
4. For each item, compute the Shodashvarga set.
5. Serialize a nested result map.

Response:

- `results`: map from caller key to selector-keyed `VargaPoint` map.

---

## 5. Response Semantics

`VargaPoint` responses must preserve:

- `varga_name`
- `varga_number`
- `longitude`
- `varga_longitude`
- `sign`
- `sign_symbol`
- `sign_degree`

Batch responses must preserve caller-supplied keys exactly after validation.
The transport layer should not reinterpret keys as planet doctrine. A key may
represent a planet, asteroid, point, Lot, or other caller-owned position.

---

## 6. Chart-Backed Surface

Chart-backed Varga routes are admitted after the post-Phase-9 shared
`SiderealChartContext` workflow.

Live shapes:

- `POST /v1/varga/chart/named`
- `POST /v1/varga/chart/shodashvarga`
- `POST /v1/varga/chart/shodashvarga/batch`

Reason:

- `moira.varga` consumes sidereal longitudes.
- It does not compute tropical positions.
- It does not compute ayanamsa reduction.
- A chart-backed route must make tropical-to-sidereal reduction and ayanamsa
  policy provenance visible.

Implementation:

- Chart-backed Varga routes use
  `docs/architecture/POST_PHASE9_SIDEREAL_CHART_DERIVATION_WORKFLOW.md`.
- Responses embed compact sidereal chart provenance.
- Direct-vs-chart parity is verified in `tests/server/test_server_varga_routes.py`.

---

## 7. Explicit Non-Goals

The first P9-11 admission does not expose:

- tropical-to-sidereal conversion
- chart-backed datetime/location computation
- interpretive chart meanings
- Varga dignity scoring
- Shadbala Saptavargaja Bala integration
- school-specific alternate varga schemes beyond the current engine wrappers
- generic `/v1/vedic` umbrella routes

---

## 8. Verification Requirements For Admission

Implementation must verify:

- generic route preserves `calculate_varga(...)` result truth
- named route preserves each named wrapper's result truth for representative
  samples
- Shodashvarga route returns all 16 selectors
- named batch route preserves caller keys and per-key result truth
- Shodashvarga batch route preserves nested key/selector truth
- non-finite longitude inputs are rejected
- invalid divisors are rejected
- unknown named varga selectors are rejected
- empty batch maps are rejected
- empty batch keys are rejected
- route registration appears in startup route inventory

Verification files to add:

- `tests/server/test_server_varga_routes.py`

Existing engine verification slice:

- `tests/unit/test_varga.py`
- `tests/unit/test_shodashvarga.py`
- `tests/unit/test_public_doctrine_surfaces.py`
- `tests/unit/test_api_surface_adversarial_audit.py`

---

## 9. Admission State

P9-11 is admitted.

Implemented files:

- `moira_server/models/varga.py`
- `moira_server/serializers/varga.py`
- `moira_server/services/varga.py`
- `moira_server/routers/varga.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_varga_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md` route inventory updates
