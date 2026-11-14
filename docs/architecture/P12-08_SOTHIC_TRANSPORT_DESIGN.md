# P12-08 Sothic Transport Design

Version: 1.2
Date: 2026-11-10
Status: bounded_direct_surface_admitted
Scope: Sothic calendar, prediction, exhaustive annual rising, and annual drift REST contracts

## 1. Admission Boundary

P12-08 admits four bounded routes.

- `POST /v1/sothic/egyptian-date`
- `POST /v1/sothic/predict-epoch`
- `POST /v1/sothic/rising`
- `POST /v1/sothic/drift-rate`

The previous semantic hold is closed by the engine-owned
`SothicRisingSeries`: every requested year has exactly one `found` or
`not_found_within_window` outcome. Missing catalog or ephemeris resources,
coverage failures, and delegated internal errors propagate and cannot become
empty success.

Still deferred:

- `POST /v1/sothic/epochs`
- `POST /v1/sothic/condition-profile`
- `POST /v1/sothic/network-profile`
- unbounded epoch searches
- async research jobs
- broad historical commentary
- autonomous heliacal-visibility doctrine
- alternate Egyptian calendars
- multi-star Sothic analogues
- automatic observer-location lookup
- interpretive narrative text

## 2. Governing Object

The governing object is the existing `moira.sothic` result family:

- `SothicAnchor`
- `SothicEpochPrediction`
- `SothicYearOutcome`
- `SothicRisingSeries`
- `SothicDriftFit` and its `SothicDriftSample` rows
- `EgyptianDate`
- `SothicEntry`
- `SothicEpoch`
- `SothicChartConditionProfile`
- `SothicConditionNetworkProfile`

The transport layer must preserve the backend layer order:

1. Egyptian civil calendar arithmetic
2. delegated Sirius heliacal-rising search
3. drift and epoch classification
4. relation preservation
5. condition profile aggregation
6. network projection

The REST layer must not redefine Sirius heliacal rising. It delegates that
truth to the Sothic engine, which delegates heliacal detection to the fixed-star
engine.

## 3. Request Shapes

`POST /v1/sothic/egyptian-date`

- `jd`: finite Julian Day
- `epoch_jd`: optional finite Julian Day

`POST /v1/sothic/predict-epoch`

- `known_epoch_year`: integer
- `n_cycles`: integer in [-1000, 1000]
- `cycle_length_years`: optional positive finite number

`POST /v1/sothic/rising` and `POST /v1/sothic/drift-rate`

- `latitude_deg`: finite degrees in [-90, 90]
- `longitude_deg`: finite degrees in [-180, 180]
- `year_start`: integer
- `year_end`: integer greater than or equal to `year_start`
- `epoch_jd`: optional finite Julian Day
- `arcus_visionis_deg`: optional finite number in [6, 12], default 10

Both annual routes use the same bounded engine policy with a 400-day
search window per requested year. Callers choose the site, year interval,
calendar anchor, and arcus visionis through the request fields above.

## 4. Bounds And Runtime Policy

Annual search routes must be bounded before admission.

Admitted limits:

- maximum `year_end - year_start + 1`: 200 years
- `arcus_visionis_deg`: 6 through 12 degrees
- `n_cycles`: -1000 through 1000
- per-year heliacal search window: 400 days
- no async route until a separate heavy-workflow design exists

The route should reject requests above these limits with explicit messages.
These bounds are transport policy, not Sothic doctrine.

## 5. Response Shape

Egyptian date responses preserve:

- request JD
- resolved default or caller-supplied calendar anchor
- civil month, day, season, day-of-year, and epagomenal birth fields
- provenance

Rising responses preserve:

- one ordered outcome per requested astronomical year
- exhaustive `found` or `not_found_within_window` status
- delegated typed heliacal-event truth for each outcome
- an entry only for found outcomes
- found and bounded-exhaustion counts
- requested year range
- provenance

Drift responses embed the complete rising response under `rising` and
the engine's least-squares fit under `fit`. The engine uses only found
years, preserving their actual astronomical year numbers and skipping
missing years without imputation. It unwraps the 365-day offset with the
shortest signed step between successive found years. An exact half-cycle
step retains its sign. Across a gap, the wrap uses only the two found
endpoints, so the result makes no inference about additional full cycles
in the gap. The response carries raw and unwrapped offsets and the slope
in civil days per year.

A valid series with fewer than five found years returns
`insufficient_found_years`, a null slope, and no fit samples. Its full
annual evidence remains available under `rising`.

Prediction responses preserve:

- known epoch year
- cycle offset
- cycle length
- predicted year
- astronomical year numbering
- explicit schematic/custom model identity
- `schematic_projection` evidence kind
- provenance

## 6. Validation Rules

The route family should reject:

- non-finite `jd`
- non-finite `epoch_jd`
- invalid latitude or longitude
- reversed year ranges
- annual search ranges over the transport maximum
- `arcus_visionis_deg` outside [6, 12]
- `n_cycles` outside [-1000, 1000]
- non-positive `cycle_length_years`
- unknown request fields

Valid annual searches that find no event return a
`not_found_within_window` outcome. They are not server errors and do not imply
that no event exists outside the bounded window. Infrastructure, coverage,
catalog, and delegated internal failures remain exceptions and must not be
serialized as search exhaustion.

## 7. Provenance Rules

Every response preserves the applicable members of the typed provenance
contract:

- `source_module`: `moira.sothic`
- engine entrypoint
- `calendar_basis`: `egyptian_civil_mod_365`
- `output_calendar`: `proleptic_gregorian`
- `year_numbering`: `astronomical`
- `stage_sequence`

The rising response additionally records
`delegated_source: moira.stars.heliacal_rising_event`,
`route_max_years: 200`, and
`cycle_model: schematic_1460_julian_year_cycle_position_only`. The resolved
anchor is a top-level typed object labelled either
`censorinus_139_calendar_anchor` or `caller_supplied_epoch_jd`; Sirius identity
and heliacal truth are carried by each outcome's event object.

## 8. Verification Requirements For Admission

Route admission includes focused server tests for:

- Egyptian date conversion at the admitted epoch anchor
- explicit Julian/proleptic-Gregorian anchor serialization
- schematic prediction labels and astronomical year numbering
- rising route with found and bounded-exhaustion outcomes
- missing-kernel propagation as HTTP 503
- rejection of reversed and oversized year ranges
- rejection of arcus values outside the admitted 6-12 degree model domain
- forward and backward calendar wrap across missing years
- signed half-cycle ties and a valid zero slope
- explicit insufficient-sample results and DE441 annual-series parity
- typed OpenAPI registration for all four routes

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\sothic.py moira_server\models\sothic.py moira_server\services\sothic.py moira_server\routers\sothic.py tests\server\test_server_sothic_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_sothic_routes.py tests\unit\test_sothic.py tests\unit\test_sothic_public_api.py tests\oracle\test_sothic_oracle.py -q -m "not external_network"
```

Integration Sothic suites should be run before any admission that changes
heliacal search behavior or range-search policy.

## 9. Completion Boundary

The four bounded routes are admitted and registered. Epoch search,
condition profiles, and network profiles have separate admission
requirements. Each annual request runs at most 200 searches.
