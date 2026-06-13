# P12-01 Uranian Transport Design

Version: 0.2
Date: 2026-06-13
Status: admitted
Scope: Uranian / Hamburg School hypothetical-body REST admission record

## 1. Admission Boundary

P12-01 admits three bounded REST routes for the existing `moira.uranian`
engine:

- `GET /v1/uranian/catalog`
- `POST /v1/uranian/position`
- `POST /v1/uranian/bulk`

These routes expose linear mean positions for the current Uranian table only.
They do not expose physical planet ephemerides, SPK-backed bodies, discovered
TNOs, fixed stars, asteroids, midpoint trees, dial interpretation, or
cosmobiology networks.

## 2. Governing Object

The governing object is a Uranian hypothetical-body position:

- canonical body name
- tropical ecliptic longitude in `[0, 360)`
- sign fields derived by `moira.constants.sign_of`
- constant mean daily speed
- model provenance for the internal linear mean-motion table

The current name set has nine entries:

- `Cupido`
- `Hades`
- `Zeus`
- `Kronos`
- `Apollon`
- `Admetos`
- `Vulkanus`
- `Poseidon`
- `Transpluto`

The transport layer must not describe this as "all eight" unless Transpluto is
explicitly excluded, which this first admission should not do.

## 3. Request Shapes

`GET /v1/uranian/catalog`

- no request body

`POST /v1/uranian/position`

Required fields:

- `name`: one canonical Uranian body name, case-sensitive
- `jd_ut`: finite Julian Day UT

`POST /v1/uranian/bulk`

Required fields:

- `jd_ut`: finite Julian Day UT

Optional fields:

- `names`: optional list of canonical names; omitted means all nine names in
  engine order

## 4. Response Shape

Catalog responses should contain:

- `names`
- `count`
- `model`
- `frame`
- `epoch`
- `provenance`

Position responses should contain:

- `position`
- `provenance`

Bulk responses should contain:

- `positions`
- `count`
- `requested_names`
- `provenance`

Each position record should preserve:

- `name`
- `longitude`
- `sign`
- `sign_symbol`
- `sign_degree`
- `speed`
- `body_kind`: `hypothetical_body`

## 5. Validation Rules

The route family rejects:

- non-finite `jd_ut`
- unknown body names
- empty body-name strings
- duplicate names in bulk requests
- non-list `names` values
- attempts to request physical bodies, asteroids, fixed stars, or arbitrary
  strings through this route family

Name matching should remain case-sensitive because the engine table is
case-sensitive. Transport may return a helpful list of valid names, but it must
not silently normalize or substitute names.

## 6. Provenance Rules

Every response preserves:

- `source_module`: `moira.uranian`
- `engine_entrypoint`: `list_uranian`, `uranian_at`, or `all_uranian_at`
- `body_kind`: `hypothetical_body`
- `school`: `Hamburg_Uranian`
- `model`: `linear_mean_motion_table`
- `formula_basis`: `longitude = longitude_at_J2000 + daily_motion * (jd_ut - J2000)`
- `frame`: `tropical_ecliptic_longitude`
- `epoch`: `J2000`
- `physical_ephemeris`: `none`
- `spk_kernel_used`: `false`
- `stage_sequence`: input validation, table lookup, linear mean-position
  computation, sign derivation, serialization

The provenance must explicitly say that these are not JPL/NAIF physical-body
states and are not discovered TNO positions.

## 7. Verification Record

Route admission added focused server tests for:

- catalog returns exactly nine names including `Transpluto`
- catalog order matches `list_uranian()`
- single-position success for each admitted name
- returned longitudes are in `[0, 360)`
- returned sign fields match the engine vessel
- bulk omitted names returns all nine positions
- bulk subset preserves requested canonical names
- unknown names fail clearly
- non-finite `jd_ut` fails before engine invocation
- provenance labels each result as hypothetical and table-based

Verification run for admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\uranian.py moira_server\services\uranian.py moira_server\routers\uranian.py moira_server\app.py moira_server\routers\__init__.py tests\server\test_server_uranian_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_uranian_routes.py -q
```

Result: 15 focused server tests passed.

The server tests carry this transport admission proof. The engine itself was
not changed in this admission pass.

## 8. Completion Boundary

P12-01 is admitted for catalog, single-position, and bounded bulk-position
transport for the nine current names. It does not include midpoint structures,
Uranian dial products, chart interpretation, physical body substitution,
kernel-backed Transpluto/TNO computation, or any claim that these points are
JPL/NAIF physical bodies.
