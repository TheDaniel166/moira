# Planetary Hours Backend Standard

**Subsystem:** `moira/planetary_hours.py`
**Computational Domain:** Sunrise-based traditional planetary hours
**Status:** Backend standard for Phase 12 REST admission

---

## 1. Scope

This standard governs the dedicated planetary-hours engine in:

- `moira/planetary_hours.py`

Current public surface:

- `PlanetaryHour`
- `PlanetaryHoursDay`
- `planetary_hours(jd, latitude, longitude, reader=None)`

This subsystem resolves the sunrise-based local planetary-hours day containing
one input instant, then divides the daylight and nighttime arcs into twelve
unequal hours each. It is location-dependent and delegates solar event truth to
Moira's solar and SPK reader layers.

## 2. Authority And Provenance

The doctrinal sequence is the traditional Chaldean order:

```text
Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon
```

The day ruler is selected from weekday rulership:

| Weekday | First hour ruler |
|---|---|
| Sunday | Sun |
| Monday | Moon |
| Tuesday | Mars |
| Wednesday | Mercury |
| Thursday | Jupiter |
| Friday | Venus |
| Saturday | Saturn |

The astronomical boundaries are delegated:

- Julian Day conversion: `moira.julian`
- sunrise/sunset approximation: `moira._solar._sunrise_sunset`
- sunrise/sunset refinement: `moira._solar._refine_sunrise`
- SPK resource access: `moira.spk_reader`

Refinement is governed by the topocentric geometric Sun-altitude crossing at
`-0.833` degrees. The threshold incorporates conventional solar semidiameter
and standard horizon refraction; the altitude signal itself is unrefracted.
This standard does not otherwise redefine those lower layers.

## 3. Governing Objects

### 3.1 Planetary-hours day

A `PlanetaryHoursDay` is the sunrise-to-next-sunrise local window containing
the requested Julian Day at the requested geographic latitude and longitude.
It preserves:

- input `date_jd`
- `latitude`
- `longitude`
- refined `sunrise_jd`
- refined `sunset_jd`
- exactly 24 `PlanetaryHour` values

The first 12 hours are daytime hours from sunrise to sunset. The final 12 hours
are nighttime hours from sunset to next sunrise.

### 3.2 Planetary hour

A `moira.planetary_hours.PlanetaryHour` is one immutable hour in the
sunrise-based day. It preserves:

- `hour_number` in `[1, 24]`
- `ruler`
- `jd_start`
- `jd_end`
- `is_daytime`

It also exposes UTC datetime and calendar views through read-only properties.

### 3.3 Distinction From `moira.cycles.PlanetaryHour`

`moira.planetary_hours.PlanetaryHour` and `moira.cycles.PlanetaryHour` are
different vessels.

| Surface | Owner | Fields |
|---|---|---|
| `moira.planetary_hours.PlanetaryHour` | `planetary_hours()` | `hour_number`, `ruler`, `jd_start`, `jd_end`, `is_daytime` |
| `moira.cycles.PlanetaryHour` | `planetary_hours_for_day()` | `hour_number`, `ruler`, `start_jd`, `end_jd`, `is_day_hour` |

The first owns location-based sunrise resolution for the enclosing local day.
The second owns cycle-profile construction when sunrise/sunset boundaries are
already supplied. REST documentation must not conflate these surfaces.

## 4. Admitted Computations

### 4.1 Enclosing day schedule

`planetary_hours(jd, latitude, longitude, reader=None)` returns all 24 hours
for the sunrise-based local day that contains `jd`.

Current behavior:

- if `reader` is omitted, `get_reader()` is used
- explicit readers bypass the singleton reader
- when `jd` is before today's sunrise, the previous sunrise window is used
- when `jd` is after today's sunrise, the current sunrise window is used
- the weekday is resolved from local mean solar time because this surface has
  coordinates but no civil-timezone input
- day and night arcs are each divided into 12 equal temporal hours
- hour rulers advance through the Chaldean sequence
- invalid coordinates, non-finite inputs, missing solar crossings, unordered
  solar bounds, and windows that do not contain the requested JD fail explicitly

### 4.2 Hour lookup

`PlanetaryHoursDay.hour_at(jd)` returns the hour containing a JD or `None`
outside the 24-hour window.

`PlanetaryHoursDay.lord_of_hour(jd)` returns the ruler of that hour or `None`
outside the window.

## 5. Required Transport Invariants

Any REST admission for `/v1/planetary-hours/*` must preserve these invariants:

- reject non-finite `jd`, `latitude`, and `longitude`
- reject latitude outside `[-90, 90]`
- reject longitude outside `[-180, 180]` unless a documented wrap policy is
  admitted
- require timezone-aware datetimes if a datetime input shape is offered
- document that all returned JD and ISO timestamps are UTC
- expose the requested instant separately from the resolved sunrise window
- return exactly 24 hours for successful schedules
- preserve hour numbers `1` through `24`
- preserve `is_daytime` exactly as the backend vessel names it
- preserve day and night duration truth separately
- expose whether the route used an explicit server reader or ambient singleton
  reader policy
- surface sunrise/sunset failures clearly

Transport must not invent fallback sunrise or sunset values. If the solar
layer cannot resolve a day because of polar/no-rise/no-set conditions or reader
failure, the REST layer must fail explicitly or return a documented blocked
state. Silent substitution is forbidden.

## 6. Polar And High-Latitude Policy

The current engine delegates sunrise and sunset resolution to `_solar`.
The engine fails explicitly when the requested local solar day has no sunrise
or no sunset altitude crossing. Transport preserves that failure without
inventing a schedule.

Minimum acceptable public policy:

- no silent synthetic sunrise
- no fixed six-to-six fallback
- no timezone-based civil-day replacement for the sunrise day
- failure responses must preserve the requested location and instant
- successful responses must include the resolved sunrise, sunset, and next
  sunrise window

## 7. Validation Requirements

Minimum validation for transport admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\planetary_hours.py tests\unit\test_planetary_hours_api.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_planetary_hours_api.py -q
```

The transport test suite must additionally cover:

- explicit reader path does not call the singleton reader
- immutable response vessels are serialized without mutation
- before-sunrise input resolves to the previous sunrise window
- after-sunrise input resolves to the current sunrise window
- exactly 24 returned hours
- first 12 hours are daytime and last 12 hours are nighttime
- hour boundaries are ordered and non-overlapping
- non-finite input rejection
- invalid latitude and longitude rejection
- blocked or failed sunrise/sunset behavior

## 8. Non-Goals

This subsystem does not provide:

- planetary day profiles from `moira.cycles`
- civil-calendar daily calendars
- electional scoring
- recommendation text
- annual time-lord techniques
- Lord of the Orb calculation
- timezone lookup
- location-name geocoding
- house or chart computation

Those products require separate standards or transport designs.

## 9. Change Policy

The following are doctrine-sensitive and require explicit review before change:

- Chaldean order
- weekday-to-first-hour-ruler mapping
- sunrise-based day selection
- division of day and night arcs into 12 equal temporal hours each
- the distinction between `moira.planetary_hours.PlanetaryHour` and
  `moira.cycles.PlanetaryHour`
- polar/no-rise/no-set public failure policy

The REST layer may validate, serialize, and document the current backend. It
must not replace the sunrise-based doctrine with a civil-clock approximation.
