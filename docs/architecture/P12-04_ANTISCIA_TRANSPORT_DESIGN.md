# P12-04 Antiscia Transport Design

Version: 0.2
Date: 2026-06-13
Status: admitted
Scope: ordinary antiscia and contra-antiscia REST admission plan

## 1. Admission Boundary

P12-04 admits three bounded REST routes for the existing `moira.antiscia`
engine:

- `POST /v1/antiscia/reflect`
- `POST /v1/antiscia/contacts`
- `POST /v1/antiscia/to-point`

These routes expose ordinary solstitial and equinoctial longitude reflection.
They do not expose primary-direction antiscia, directed arcs, chart motion,
ephemeris computation, house calculation, antiscia networks, scoring profiles,
or interpretive text.

## 2. Governing Object

The governing objects are:

- antiscion point: `(180 - longitude) mod 360`
- contra-antiscion point: `(360 - longitude) mod 360`
- antiscia contact: one `AntisciaAspect` emitted by the engine

Ordinary antiscia is not primary-direction antiscia. The primary-direction
subsystem may use the same reflection formula for target projection, but its
governing object is a directed arc target, not an ordinary chart contact.

## 3. Request Shapes

`POST /v1/antiscia/reflect`

Required fields:

- `longitude`: finite ecliptic longitude in degrees

Optional fields:

- `kind`: `antiscion`, `contra_antiscion`, or `both`; default `both`

`POST /v1/antiscia/contacts`

Required fields:

- `positions`: object mapping unique non-empty body names to finite longitudes

Optional fields:

- `orb`: finite non-negative degrees, default `1.0`

`POST /v1/antiscia/to-point`

Required fields:

- `point_longitude`: finite ecliptic longitude in degrees
- `positions`: object mapping unique non-empty body names to finite longitudes

Optional fields:

- `point_name`: non-empty string, default `Point`
- `orb`: finite non-negative degrees, default `1.0`

## 4. Response Shape

Reflection responses should contain:

- `longitude`
- `antiscion` when requested
- `contra_antiscion` when requested
- `provenance`

Contact responses should contain:

- `contacts`
- `count`
- `orb`
- `provenance`

Each contact record should preserve:

- `body1`
- `body2`
- `aspect`
- `lon1`
- `lon2`
- `shadow`
- `orb`

The `aspect` values must remain the engine labels:

- `Antiscion`
- `Contra-Antiscion`

The `body1` field must remain the body whose reflected point forms the contact.

## 5. Validation Rules

The route family should reject:

- non-finite longitudes
- non-object `positions`
- empty position maps for contact routes
- duplicate or empty body names
- non-finite position values
- negative or non-finite `orb`
- orb values above the admitted transport maximum
- unsupported reflection kinds

Recommended initial transport bounds:

- maximum `positions` size: 64
- maximum `orb`: 30 degrees

Longitudes may be accepted as arbitrary finite degrees and normalized by the
engine formula. The response should document normalized output in `[0, 360)`.

## 6. Provenance Rules

Every response should preserve:

- `source_module`: `moira.antiscia`
- engine entrypoint
- `doctrine`: `ordinary_antiscia`
- `antiscion_formula`: `(180 - longitude) mod 360`
- `contra_antiscion_formula`: `(360 - longitude) mod 360`
- `primary_direction_boundary`: `not_primary_direction_antiscia`
- `chart_motion`: `not_computed`
- `ephemeris`: `not_used`
- route-level input bounds applied
- `stage_sequence`: input validation, reflection or contact search,
  result ordering, serialization

Contact responses must state that results are sorted by increasing orb.

## 7. Verification Requirements For Admission

Route admission should add focused server tests for:

- direct antiscion reflection
- direct contra-antiscion reflection
- both-reflection response
- reflection involution at boundary values
- pair contact search preserves `body1`, `shadow`, `aspect`, and sorted orb
- point contact search preserves `point_name`
- duplicate body-name rejection
- non-finite longitude rejection
- invalid orb rejection
- oversized chart/contact request rejection
- provenance explicitly separates ordinary antiscia from primary directions

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\antiscia.py moira_server\services\antiscia.py moira_server\routers\antiscia.py tests\server\test_server_antiscia_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_antiscia_routes.py tests\unit\test_astrology_adversarial_gauntlet.py tests\unit\test_primary_direction_antiscia.py -q
```

## 8. Completion Boundary

P12-04 is admitted as a bounded ordinary antiscia route family.

Completion covers only ordinary direct reflection, bounded chart contact
search, and bounded point contact search. It does not include
primary-direction arcs, transits, progressions, chart construction, house
derivation, antiscia networks, or interpretation.

## 9. Admission Record

Implemented files:

- `moira_server/models/antiscia.py`
- `moira_server/services/antiscia.py`
- `moira_server/routers/antiscia.py`
- `tests/server/test_server_antiscia_routes.py`

Registered routes:

- `POST /v1/antiscia/reflect`
- `POST /v1/antiscia/contacts`
- `POST /v1/antiscia/to-point`

Verification performed:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\antiscia.py moira_server\services\antiscia.py moira_server\routers\antiscia.py tests\server\test_server_antiscia_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_antiscia_routes.py tests\unit\test_astrology_adversarial_gauntlet.py tests\unit\test_primary_direction_antiscia.py -q
```

Result:

- `32 passed`

Live route audit after admission:

- total non-documentation routes: `304`
- versioned `/v1` routes: `300`
- `/v1/antiscia/*` routes: `3`
