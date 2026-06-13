# P12-06 Planetary Hours Transport Design

Version: 0.2
Date: 2026-06-13
Status: admitted
Scope: sunrise-based planetary-hours REST admission plan

## 1. Admission Boundary

P12-06 admits two bounded REST routes for the existing
`moira.planetary_hours` engine:

- `POST /v1/planetary-hours/schedule`
- `POST /v1/planetary-hours/hour-at`

These routes expose the dedicated sunrise-based planetary-hours vessel from
`moira.planetary_hours`. They do not expose `moira.cycles.PlanetaryHour`, civil
clock planetary-hour approximations, electional scoring, timezone lookup,
geocoding, daily calendar products, or annual lordship systems.

## 2. Governing Object

The governing object is a `PlanetaryHoursDay`:

- requested Julian Day
- geographic latitude and longitude
- resolved sunrise
- resolved sunset
- 24 immutable `moira.planetary_hours.PlanetaryHour` records

Each hour preserves:

- `hour_number`
- `ruler`
- `jd_start`
- `jd_end`
- `is_daytime`

This route family must not serialize or document the field names of
`moira.cycles.PlanetaryHour` as if they belong to this engine. In particular,
the dedicated vessel uses `jd_start`, `jd_end`, and `is_daytime`, not
`start_jd`, `end_jd`, or `is_day_hour`.

## 3. Request Shapes

`POST /v1/planetary-hours/schedule`

Required fields:

- `jd`: finite Julian Day UT
- `latitude`: finite degrees in `[-90, 90]`
- `longitude`: finite degrees in `[-180, 180]`

Optional fields:

- `include_iso_utc`: boolean, default `true`

`POST /v1/planetary-hours/hour-at`

Required fields:

- `jd`: finite Julian Day UT
- `latitude`: finite degrees in `[-90, 90]`
- `longitude`: finite degrees in `[-180, 180]`

Optional fields:

- `include_schedule`: boolean, default `false`
- `include_iso_utc`: boolean, default `true`

Datetime input may be added later, but the first admission should use Julian
Day only. If datetime input is later admitted, it must require timezone-aware
datetimes and serialize all returned instants as UTC.

## 4. Response Shape

Schedule responses contain:

- `requested_jd`
- `latitude`
- `longitude`
- `sunrise_jd`
- `sunset_jd`
- `next_sunrise_jd`
- `day_duration_days`
- `night_duration_days`
- `hours`
- `provenance`

Hour-at responses contain:

- `requested_jd`
- `hour`: the matching hour or `null`
- `schedule_window`
- `provenance`

Each hour record should preserve:

- `hour_number`
- `ruler`
- `jd_start`
- `jd_end`
- `is_daytime`
- optional `start_utc`
- optional `end_utc`

The schedule must return exactly 24 hours on success.

## 5. Validation Rules

The route family rejects:

- non-finite `jd`
- non-finite `latitude`
- non-finite `longitude`
- latitude outside `[-90, 90]`
- longitude outside `[-180, 180]`
- malformed boolean options

The REST layer must not invent sunrise or sunset values. If `_solar` or the
reader layer cannot resolve the requested window, the route surfaces a clear
client-visible error preserving the requested instant and location.

Admission stance:

- use the server engine's explicit reader when available
- do not expose client-selectable reader policy
- do not add timezone or location-name lookup

## 6. Provenance Rules

Every response should preserve:

- `source_module`: `moira.planetary_hours`
- `engine_entrypoint`: `planetary_hours`
- `vessel`: `moira.planetary_hours.PlanetaryHour`
- `not_vessel`: `moira.cycles.PlanetaryHour`
- `sequence_basis`: `Chaldean_order`
- `day_ruler_basis`: `weekday_rulership`
- `day_window_basis`: `sunrise_to_next_sunrise`
- `solar_event_source`: `moira._solar`
- `reader_policy`: server explicit reader or backend default
- `timezone_policy`: `utc_output_only`
- `stage_sequence`: input validation, reader binding, sunrise/sunset
  resolution, day/night division, hour lookup when requested, serialization

The provenance must state that returned ISO timestamps, if included, are UTC.

## 7. Verification Requirements For Admission

Route admission added focused server tests for:

- successful schedule returns exactly 24 hours
- first 12 hours are daytime and final 12 are nighttime
- hour numbers are `1` through `24`
- hour boundaries are ordered and non-overlapping
- day and night duration fields match serialized boundaries
- hour-at returns the containing hour
- hour-at outside the resolved window returns `null`
- before-sunrise input resolves to the previous sunrise window
- explicit reader path avoids the singleton when the server engine provides one
- non-finite input rejection
- invalid latitude and longitude rejection
- blocked sunrise/sunset behavior is surfaced without fallback values
- provenance distinguishes this vessel from `moira.cycles.PlanetaryHour`

Verification command set:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\planetary_hours.py moira_server\services\planetary_hours.py moira_server\routers\planetary_hours.py tests\server\test_server_planetary_hours_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_planetary_hours_routes.py tests\unit\test_planetary_hours_api.py -q
```

## 8. Completion Boundary

P12-06 is admitted as a bounded sunrise-based planetary-hours route family.

Completion covers only schedule serialization and hour lookup for a supplied
Julian Day and geographic coordinates. It does not include timezone lookup,
location lookup, civil-day calendars, electional scoring, `moira.cycles`
profiles, or automatic birth planetary-hour derivation for other lordship
systems.

## 9. Admission Record

Implemented files:

- `moira_server/models/planetary_hours.py`
- `moira_server/services/planetary_hours.py`
- `moira_server/routers/planetary_hours.py`
- `tests/server/test_server_planetary_hours_routes.py`

Registered routes:

- `POST /v1/planetary-hours/schedule`
- `POST /v1/planetary-hours/hour-at`

Verification performed:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\planetary_hours.py moira_server\services\planetary_hours.py moira_server\routers\planetary_hours.py tests\server\test_server_planetary_hours_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_planetary_hours_routes.py tests\unit\test_planetary_hours_api.py -q
```

Result:

- `14 passed`

Live route audit after admission:

- total non-documentation routes: `307`
- versioned `/v1` routes: `303`
- `/v1/planetary-hours/*` routes: `2`
