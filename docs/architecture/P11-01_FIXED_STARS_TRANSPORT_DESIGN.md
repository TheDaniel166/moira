# P11-01 Fixed Stars Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: bounded fixed-star position, bulk position, and list/search REST routes

## 1. Admission Boundary

P11-01 admits the narrow fixed-star REST surface:

- `POST /v1/stars/position`
- `POST /v1/stars/bulk`
- `GET /v1/stars/list`

This is not full unified-star backend exposure. It admits fixed-star lookup and
position transport for selected objects and bounded catalog discovery.

Deferred:

- heliacal rising and setting routes
- star condition profile and condition network routes
- catalog-wide position sweeps
- rendered star maps
- fixed-star astrocartography
- Gaia search/proximity/magnitude expansion beyond the current list/search
  behavior

## 2. Governing Object

The admitted REST result is a selected `FixedStar` position from
`moira.stars.star_at(...)`, serialized for HTTP transport with explicit
provenance from the live `FixedStar` vessel.

The transport layer does not recompute fixed-star doctrine. It performs:

1. timezone-aware datetime validation
2. UTC datetime to Julian Day conversion
3. UT to TT conversion
4. selected fixed-star lookup through `star_at`
5. response serialization with provenance

## 3. Request Shapes

`POST /v1/stars/position`

- `dt`: timezone-aware datetime
- `star`: non-empty fixed-star name, designation, or common name

`POST /v1/stars/bulk`

- `dt`: timezone-aware datetime
- `stars`: 1 to 500 non-empty fixed-star names/designations
- `skip_missing`: boolean, default `true`

`GET /v1/stars/list`

- `q`: optional search term
- `limit`: bounded by the router at 500

## 4. Response Shape

Position responses preserve the existing website fields:

- `name`
- `designation`
- `longitude`
- `latitude`
- `distance`
- `magnitude`
- `sign`
- `sign_symbol`
- `sign_degree`
- `is_variable`

They also include `provenance`.

The provenance object records:

- requested datetime and normalized UTC datetime
- TT Julian Day used for `star_at`
- coordinate source: `sovereign_star_registry`
- source mode, source kind, merge state, observer mode
- lookup kind and matched Hipparcos/native name where available
- Gaia match fields where available
- topocentric/true-position/dedup truth
- relation kind and basis
- condition result kind and condition state
- transport stage sequence

## 5. Validation Rules

The admitted surface rejects:

- naive datetimes
- empty star names
- empty bulk lists
- empty bulk entries
- bulk lists above 500 entries

Unknown star names remain semantic lookup failures. In bulk mode they are
collected in `missing` when `skip_missing=true`; otherwise the underlying
lookup failure is allowed to surface.

## 6. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\stars.py moira_server\services\stars.py moira_server\serializers\stars.py tests\server\test_server_stars_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_stars_routes.py -q
```

Route registry audit after admission:

- 269 non-documentation routes
- 265 versioned `/v1` routes
- 12 `/v1/stars/*` routes
- exactly 3 admitted fixed-star routes:
  - `/v1/stars/position`
  - `/v1/stars/bulk`
  - `/v1/stars/list`

The route tests verify:

- route registration
- datetime to JD TT conversion parity against `star_at`
- fixed-star provenance preservation
- bulk result and missing-name behavior
- adversarial request rejection for datetime, names, and bulk bounds

## 7. Admission Verdict

P11-01 is admitted as a bounded synchronous fixed-star position/list family.

Later fixed-star work is explicit expansion, not implicit widening of this
admitted surface.
