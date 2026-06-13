# P11-04 Asteroids Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: bounded asteroid position, bulk position, and loaded-kernel list/search REST routes

## 1. Admission Boundary

P11-04 admits the narrow asteroid REST surface:

- `POST /v1/asteroids/position`
- `POST /v1/asteroids/bulk`
- `GET /v1/asteroids/list`

This is not full small-body REST admission. It admits selected asteroid
transport over the existing `moira.asteroids` engine surface and the server's
loaded small-body reader.

Deferred:

- asteroid families and subset routes
- centaur, TNO, main-belt, and classical-asteroid convenience families
- comet parity changes
- catalog-wide asteroid sweeps
- topocentric asteroid positions
- equatorial position transport
- magnitude, H/G, phase, or photometric transport
- rendered asteroid maps
- asteroid astrocartography
- kernel build, shard, and manifest-management routes
- full small-body migration proof beyond the loaded-reader route boundary

## 2. Governing Object

The admitted REST result is a selected `AsteroidData` position from
`moira.asteroids.asteroid_at(...)`, serialized for HTTP transport with explicit
request and kernel-availability provenance.

The transport layer does not recompute asteroid doctrine. It performs:

1. timezone-aware datetime validation
2. UTC datetime to Julian Day conversion
3. selected asteroid identity resolution through `asteroid_at`
4. loaded-reader coverage inspection by returned NAIF ID
5. response serialization with provenance

The route family must preserve the distinction between:

- a known catalog identity in `ASTEROID_NAIF`
- a body actually available in the loaded small-body reader
- a position successfully returned by the engine

`is_sovereign=true` is only asserted when the returned NAIF ID is covered by the
loaded reader. Reader presence alone is not enough.

## 3. Request Shapes

`POST /v1/asteroids/position`

- `dt`: timezone-aware datetime
- `body`: non-empty asteroid name or NAIF ID

`POST /v1/asteroids/bulk`

- `dt`: timezone-aware datetime
- `bodies`: 1 to 500 non-empty asteroid names or NAIF IDs
- `skip_missing`: boolean, default `true`

`GET /v1/asteroids/list`

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
- UT Julian Day used for `asteroid_at`
- coordinate source
- kernel source
- known catalog-entry truth
- loaded-kernel availability truth
- requested and returned body identity
- returned NAIF ID
- NAIF convention
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
- empty asteroid body names
- empty bulk lists
- empty bulk entries
- bulk lists above 500 entries
- list limits outside `1..500`

Unknown or unavailable body names remain semantic lookup failures. In bulk mode
they are collected in `missing` when `skip_missing=true`; otherwise the
underlying lookup failure is allowed to surface.

## 6. Sovereign-Kernel Semantics

The server may have an active reader that contains planetary kernels, asteroid
kernels, or both. P11-04 does not treat reader presence as asteroid availability.

The admitted transport rule is:

- `known_catalog_entry=true` means the requested body is present in
  `ASTEROID_NAIF`.
- `loaded_kernel_available=true` means the returned NAIF ID is present in
  `reader.covered_bodies()`.
- `is_sovereign=true` follows the same loaded-reader coverage truth.

This avoids overclaiming full asteroid migration when only a subset of the
small-body kernel family is loaded.

## 7. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\asteroids.py moira_server\services\asteroids.py moira_server\serializers\asteroids.py moira_server\routers\asteroids.py tests\server\test_server_small_body_list_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_small_body_list_routes.py -q
```

The focused server tests verify:

- loaded-reader list/search responses include provenance
- list limits are enforced
- single-position responses include provenance
- loaded vs known asteroid truth is not overclaimed
- naive datetime and empty body rejection
- bulk success/missing semantics
- bulk list bounds and empty-entry rejection

Route registry audit after admission:

- exactly 3 admitted asteroid routes:
  - `/v1/asteroids/position`
  - `/v1/asteroids/bulk`
  - `/v1/asteroids/list`

## 8. Completion Boundary

P11-04 is complete for the current selected asteroid REST transport subset.

It is not complete for asteroid families, asteroid subset convenience routes,
photometry, rendered maps, topocentric positions, equatorial positions,
asteroid astrocartography, or full small-body kernel migration proof.
