# P11-05 Comets Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: bounded comet position, bulk position, and loaded-kernel list/search REST routes

## 1. Admission Boundary

P11-05 admits the narrow comet REST surface:

- `POST /v1/comets/position`
- `POST /v1/comets/bulk`
- `GET /v1/comets/list`

This is not full small-body REST admission. It admits selected periodic-comet
transport over the existing `moira.comets` engine surface and the server's
loaded small-body reader.

Deferred:

- non-periodic comet expansion beyond `COMET_NAIF`
- comet family or dynamical-class routes
- catalog-wide comet sweeps
- topocentric comet positions
- equatorial position transport
- magnitude, coma, tail, phase, or photometric transport
- rendered comet maps
- comet astrocartography
- kernel build, shard, and manifest-management routes
- full small-body migration proof beyond the loaded-reader route boundary

## 2. Governing Object

The admitted REST result is a selected `CometData` position from
`moira.comets.comet_at(...)`, serialized for HTTP transport with explicit
request and kernel-availability provenance.

The transport layer does not recompute comet doctrine. It performs:

1. timezone-aware datetime validation
2. UTC datetime to Julian Day conversion
3. selected comet identity resolution against `COMET_NAIF`
4. loaded-reader coverage inspection by returned NAIF ID
5. response serialization with provenance

The route family must preserve the distinction between:

- a known catalog identity in `COMET_NAIF`
- a body actually available in the loaded small-body reader
- a position successfully returned by the engine

`is_sovereign=true` is only asserted when the returned NAIF ID is covered by the
loaded reader. Reader presence alone is not enough.

## 3. Request Shapes

`POST /v1/comets/position`

- `dt`: timezone-aware datetime
- `body`: non-empty comet name or NAIF ID

`POST /v1/comets/bulk`

- `dt`: timezone-aware datetime
- `bodies`: 1 to 500 non-empty comet names or NAIF IDs
- `skip_missing`: boolean, default `true`

`GET /v1/comets/list`

- `q`: optional name or NAIF contains filter
- `limit`: integer bounded to `1 <= limit <= 500`

## 4. Response Shape

Position responses preserve the existing website fields:

- `name`
- `naif_id`
- `longitude`
- `latitude`
- `distance`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`
- `is_sovereign`

They also include `provenance`.

The position provenance object records:

- requested datetime and normalized UTC datetime
- UT Julian Day used for `comet_at`
- coordinate source
- kernel source
- known catalog-entry truth
- loaded-kernel availability truth
- requested body identity
- resolved engine body name
- returned body identity
- returned NAIF ID
- comet NAIF convention
- frame
- transport stage sequence

Bulk responses include per-body position provenance plus a bulk provenance
object recording requested bodies, returned bodies, missing bodies, kernel
source, and loaded-reader availability.

List responses include provenance recording the identity catalog, availability
source, loaded-reader availability, requested query, limit, returned count, and
stage sequence.

## 5. Validation Rules

The admitted surface rejects:

- naive datetimes
- empty comet body names
- empty bulk lists
- empty bulk entries
- bulk lists above 500 entries
- list limits outside `1..500`

Unknown or unavailable body names remain semantic lookup failures. In bulk mode
they are collected in `missing` when `skip_missing=true`; otherwise the
underlying lookup failure is allowed to surface.

## 6. NAIF And Kernel Semantics

The engine `comet_at(...)` accepts known comet names. The REST transport accepts
known comet names and known comet NAIF IDs, resolving numeric IDs to the engine
name before calling `comet_at(...)`.

The admitted transport rule is:

- `known_catalog_entry=true` means the requested body is present in
  `COMET_NAIF`, either by name or NAIF ID.
- `loaded_kernel_available=true` means the returned NAIF ID is present in
  `reader.covered_bodies()`.
- `is_sovereign=true` follows the same loaded-reader coverage truth.

This avoids overclaiming full comet migration when only a subset of the
small-body kernel family is loaded.

## 7. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\comets.py moira_server\services\comets.py moira_server\serializers\comets.py moira_server\routers\comets.py tests\server\test_server_small_body_list_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_small_body_list_routes.py -q
```

The focused server tests verify:

- loaded-reader list/search responses include provenance
- list limits are enforced
- single-position responses include provenance
- datetime requests are converted to JD before engine calls
- numeric-string NAIF IDs resolve to engine comet names
- loaded vs known comet truth is not overclaimed
- naive datetime and empty body rejection
- bulk success/missing semantics
- bulk list bounds and empty-entry rejection

Route registry audit after admission:

- exactly 3 admitted comet routes:
  - `/v1/comets/position`
  - `/v1/comets/bulk`
  - `/v1/comets/list`

## 8. Completion Boundary

P11-05 is complete for the current selected comet REST transport subset.

It is not complete for non-periodic comet expansion, comet family routes,
photometry, rendered maps, topocentric positions, equatorial positions, comet
astrocartography, or full small-body kernel migration proof.
