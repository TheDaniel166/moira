# P-GAP-01 Frame-Specific Positions Transport Design

Version: 0.1
Date: 2026-06-14
Status: implemented and admitted
Scope: bounded REST admission plan for heliocentric, planetocentric, SSB, and
received-light position products

This design follows
`wiki/02_standards/FRAME_SPECIFIC_POSITIONS_BACKEND_STANDARD.md`.

P-GAP-01 admits a transport design for specialized position centers and
light-cone products that are already public through the Python facade:

- `Moira.heliocentric`
- `Moira.planetocentric`
- `Moira.ssb_chart`
- `Moira.received_light`

The existing `/v1/positions/planet` and `/v1/positions/sky` routes remain the
ordinary geocentric/topocentric position surfaces. P-GAP-01 adds explicit
frame-specific products; it does not reinterpret the existing routes.

---

## 1. Route Family

Prefix:

- `/v1/positions/frame`

Routes:

- `POST /v1/positions/frame/heliocentric`
- `POST /v1/positions/frame/planetocentric`
- `POST /v1/positions/frame/ssb`
- `POST /v1/positions/frame/received-light`

Route naming doctrine:

- `frame` marks that these are center/frame-specific products.
- `heliocentric` means Sun-centered true-of-date ecliptic position.
- `planetocentric` means target measured from a named observer body center.
- `ssb` means Solar System Barycenter origin.
- `received-light` means apparent received-light position plus same-time
  geometric comparison.

---

## 2. Shared Bounds

Initial transport bounds:

- maximum bodies per request: `12`
- datetimes must be timezone-aware
- all scalar outputs must be finite
- body names must be non-empty strings after trimming
- duplicate requested bodies are rejected
- bulk output order follows request order when bodies are supplied
- default output order follows the owning engine's default body order

No route in this family performs:

- date-range search
- dense ephemeris tables
- async jobs
- rendering
- location lookup
- kernel path mutation

---

## 3. Shared Request Shape

### Heliocentric Request

`FrameHeliocentricRequest`:

- `dt`: timezone-aware datetime
- `bodies`: optional list of body names, maximum `12`

Validation:

- reject naive datetimes
- reject duplicate bodies
- reject Sun
- reject Moon
- reject any body the engine rejects

### Planetocentric Request

`FramePlanetocentricRequest`:

- `dt`: timezone-aware datetime
- `observer`: body name
- `bodies`: optional list of target body names, maximum `12`

Validation:

- reject naive datetimes
- reject invalid observer
- reject duplicate target bodies
- reject target equal to observer
- reject any body the engine rejects

### SSB Request

`FrameSSBRequest`:

- `dt`: timezone-aware datetime
- `bodies`: optional list of body names, maximum `12`

Validation:

- reject naive datetimes
- reject duplicate bodies
- reject any body outside `SSB_BODIES`

### Received-Light Request

`FrameReceivedLightRequest`:

- `dt`: timezone-aware datetime
- `bodies`: optional list of body names, maximum `12`

Validation:

- reject naive datetimes
- reject duplicate bodies
- reject nodes, Lilith, lots, stars, asteroids, comets, or other nonphysical
  points unless the engine later admits them explicitly
- reject any body outside `RECEIVED_LIGHT_BODIES`

---

## 4. Shared Response Shape

Every route response contains:

- `positions`
- `request`
- `time`
- `frame`
- `bounds`
- `validation`
- `provenance`

`time` preserves:

- `requested_datetime`
- `normalized_datetime_utc`
- `jd_ut`
- `jd_tt`
- `delta_t_seconds`

`bounds` preserves:

- `max_bodies`
- `body_count`

`validation` preserves:

- `included`
- `passed`
- `failures`

---

## 5. Position Records

### Heliocentric Position Record

Fields:

- `name`
- `longitude`
- `latitude`
- `distance_km`
- `distance_au`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

Frame metadata:

- `center`: `sun`
- `frame`: `true_of_date_ecliptic`
- `product_kind`: `geometric_heliocentric_position`

### Planetocentric Position Record

Fields:

- `observer`
- `name`
- `longitude`
- `latitude`
- `distance_km`
- `distance_au`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

Frame metadata:

- `center`: requested observer body
- `frame`: `true_of_date_ecliptic`
- `product_kind`: `geometric_planetocentric_position`

### SSB Position Record

Fields:

- `name`
- `longitude`
- `latitude`
- `distance_km`
- `distance_au`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

Frame metadata:

- `center`: `solar_system_barycenter`
- `frame`: `true_of_date_ecliptic`
- `product_kind`: `geometric_barycentric_position`

### Received-Light Position Record

Fields:

- `name`
- `apparent_longitude`
- `apparent_latitude`
- `geometric_longitude`
- `geometric_latitude`
- `longitude_displacement`
- `distance_km`
- `distance_au`
- `light_travel_days`
- `light_travel_minutes`
- `emission_jd`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

Frame metadata:

- `center`: `earth`
- `frame`: `true_of_date_ecliptic`
- `product_kind`: `received_light_position`
- `geometric_comparison_included`: `true`

---

## 6. Provenance

Every response must include:

- `source_module`
- `engine_entrypoint`
- `reader_owner`
- `chart_construction`: `not_used`
- `kernel_mutation`: `not_performed`
- `center`
- `frame`
- `orientation`
- `correction_model`
- `light_time_corrected`
- `apparent_sky_corrected`
- `geometric_comparison_included`
- `stage_sequence`

Route-specific provenance:

Heliocentric:

- `source_module`: `moira.planets`
- `engine_entrypoint`: `all_heliocentric_at`
- `center`: `sun`
- `correction_model`: `geometric_heliocentric_precession_nutation`
- `light_time_corrected`: `false`
- `apparent_sky_corrected`: `false`
- `geometric_comparison_included`: `false`

Planetocentric:

- `source_module`: `moira.planetocentric`
- `engine_entrypoint`: `all_planetocentric_at`
- `center`: requested observer
- `correction_model`: `geometric_planetocentric_precession_nutation`
- `light_time_corrected`: `false`
- `apparent_sky_corrected`: `false`
- `geometric_comparison_included`: `false`

SSB:

- `source_module`: `moira.ssb`
- `engine_entrypoint`: `all_ssb_positions_at`
- `center`: `solar_system_barycenter`
- `correction_model`: `geometric_barycentric_precession_nutation`
- `light_time_corrected`: `false`
- `apparent_sky_corrected`: `false`
- `geometric_comparison_included`: `false`

Received light:

- `source_module`: `moira.light_cone`
- `engine_entrypoint`: `all_received_light_at`
- `center`: `earth`
- `correction_model`:
  `apparent_received_light_compared_to_same_time_geometric`
- `light_time_corrected`: `true`
- `apparent_sky_corrected`: `true`
- `geometric_comparison_included`: `true`

Shared stage sequence:

- `input_validation`
- `datetime_normalization`
- `reader_binding`
- `engine_call`
- `position_serialization`
- `provenance_serialization`

---

## 7. Error Semantics

The routes must reject through the standard `422` validation envelope:

- naive datetimes
- non-finite output values
- non-list `bodies` values
- empty body names
- duplicate body names
- body count over `12`
- heliocentric Sun or Moon requests
- invalid planetocentric observer
- planetocentric target equal to observer
- invalid SSB body
- invalid received-light body
- extra request fields

Kernel absence should use the existing server error envelope for missing
ephemeris/kernel resources. The route must not attempt to repair that by
changing kernel paths.

---

## 8. Implementation Files

Implemented files:

- `moira_server/models/frame_positions.py`
- `moira_server/services/frame_positions.py`
- `moira_server/routers/frame_positions.py`
- `tests/server/test_server_frame_positions_routes.py`

Router registration:

- router is exported from `moira_server/routers/__init__.py`
- router is included in `moira_server/app.py`

REST reference update:

- route family count increased by `4`
- `/v1` route count increased by `4`
- `positions-frame` family row added
- four route table rows added
- Frame-Specific Positions REST Admission Boundary section added

Gap ledger update:

- P-GAP-01 is marked `admitted` after implementation, tests, route registry
  audit, and REST reference update.

---

## 9. Verification Requirements

Focused server tests:

- `GET` is not admitted for compute routes
- successful heliocentric route with default bodies
- successful heliocentric route with explicit bounded body list
- successful planetocentric route with observer Mars and target Jupiter
- successful SSB route including Sun
- successful received-light route for an outer planet
- body order preservation for explicit body lists
- duplicate body rejection
- body cap rejection
- naive datetime rejection
- heliocentric Sun rejection
- heliocentric Moon rejection
- planetocentric observer equals target rejection
- received-light nonphysical point rejection
- provenance truth for center/frame/correction model
- no route mutates kernel configuration

Implementation verification:

- `python -m py_compile` for new and touched server files
- `python -m pytest tests/server/test_server_frame_positions_routes.py -q`
- route registry audit confirming four new `/v1/positions/frame/*` routes

---

## 10. Non-Goals

This transport design does not admit:

- `/v1/positions/frame/search`
- heliocentric transit or conjunction search
- arbitrary observer centers outside `VALID_OBSERVER_BODIES`
- topocentric frame-specific positions
- sky projection from non-Earth observers
- dense ephemeris tables
- chart rendering
- small-body frame products unless the owning engine admits them
- kernel path changes

---

## 11. Admission Result

P-GAP-01 is admitted through:

- `POST /v1/positions/frame/heliocentric`
- `POST /v1/positions/frame/planetocentric`
- `POST /v1/positions/frame/ssb`
- `POST /v1/positions/frame/received-light`

Implementation remains a transport layer over existing engine functions.
It does not change `moira.planets`, `moira.planetocentric`, `moira.ssb`, or
`moira.light_cone`.
