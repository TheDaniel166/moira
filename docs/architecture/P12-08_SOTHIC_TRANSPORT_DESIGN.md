# P12-08 Sothic Transport Design

Version: 0.1
Date: 2026-06-13
Status: defer_for_specialist_review
Scope: Sothic calendar, rising, epoch, prediction, and profile REST evaluation plan

## 1. Admission Boundary

P12-08 is not admitted at this time.

Sothic remains a specialist module. The backend standard and this transport
design describe a possible route boundary, but they do not authorize public
REST exposure in the current Phase 12 sequence. The main hold is semantic:
public heliacal-search routes must not silently collapse valid no-event
results, delegated search exhaustion, missing catalog or ephemeris
infrastructure, and delegated internal failures into the same empty response.

If a later review reopens admission, the route family should only be considered
in stages.

Stage 1, low-cost direct routes:

- `POST /v1/sothic/egyptian-date`
- `POST /v1/sothic/predict-epoch`

Stage 2, bounded annual search routes:

- `POST /v1/sothic/rising`
- `POST /v1/sothic/epochs`
- `POST /v1/sothic/drift-rate`

Stage 3, profile routes after the lower routes are implemented:

- `POST /v1/sothic/condition-profile`
- `POST /v1/sothic/network-profile`

Deferred:

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
- `policy`: optional Sothic policy, default omitted

`POST /v1/sothic/predict-epoch`

- `known_epoch_year`: integer
- `n_cycles`: integer
- `cycle_length_years`: optional positive finite number
- `policy`: optional Sothic policy

`POST /v1/sothic/rising`

- `latitude`: finite degrees in [-90, 90]
- `longitude`: finite degrees in [-180, 180]
- `year_start`: integer
- `year_end`: integer greater than or equal to `year_start`
- `epoch_jd`: optional finite Julian Day
- `arcus_visionis`: optional positive finite number
- `policy`: optional Sothic policy

`POST /v1/sothic/epochs`

- same as `/v1/sothic/rising`
- `tolerance_days`: optional non-negative finite number

`POST /v1/sothic/drift-rate`

- `entries`: serialized `SothicEntry`-compatible records from the route family,
  minimum five entries

`POST /v1/sothic/condition-profile`

- `egyptian_dates`: optional list of admitted Egyptian date records
- `entries`: optional list of admitted Sothic entry records
- `epochs`: optional list of admitted Sothic epoch records

`POST /v1/sothic/network-profile`

- same input shape as `/v1/sothic/condition-profile`

## 4. Bounds And Runtime Policy

Annual search routes must be bounded before admission.

Recommended initial limits:

- maximum `year_end - year_start + 1`: 200 years
- maximum profile input count per vessel family: 500
- no async route until a separate heavy-workflow design exists

The route should reject requests above these limits with explicit messages.
These bounds are transport policy, not Sothic doctrine.

## 5. Response Shape

Egyptian date responses should preserve:

- civil date fields
- epagomenal birth
- computation truth
- classification
- relation
- condition profile
- provenance

Rising responses should preserve:

- ordered `entries`
- count
- requested year range
- search exhaustion note when no entries are found
- provenance

Epoch responses should preserve:

- ordered `epochs`
- count
- requested year range
- tolerance policy
- search exhaustion note when no epochs are found
- provenance

Prediction responses should preserve:

- known epoch year
- cycle offset
- cycle length
- predicted year
- provenance

Profile responses should preserve the full aggregate or network shape without
collapsing node or relation kinds into generic labels.

## 6. Validation Rules

The route family should reject:

- non-finite `jd`
- non-finite `epoch_jd`
- invalid latitude or longitude
- reversed year ranges
- annual search ranges over the transport maximum
- non-positive `arcus_visionis`
- negative `tolerance_days`
- non-positive `cycle_length_years`
- malformed policy objects
- drift-rate input with fewer than five entries
- non-finite drift values
- profile inputs that do not preserve supported condition states

Valid annual searches that find no event should return an empty list with a
search-exhaustion note. They should not be treated as server errors.

## 7. Provenance Rules

Every response should preserve:

- `source_module`: `moira.sothic`
- engine entrypoint
- policy values used
- `anchor`: `censorinus_139_epoch`
- `calendar_basis`: `egyptian_civil_mod_365`
- `star_name`: `Sirius` for rising and epoch routes
- `heliacal_basis`: `delegated_heliacal_rising`
- `delegated_source`: `moira.fixed_stars.heliacal_rising`
- `stage_sequence`
- route-level bounds applied

Profile and network responses must preserve relation kinds:

- `egyptian_calendar`
- `sothic_rising`
- `sothic_epoch`

## 8. Verification Requirements For Admission

Route admission should add focused server tests for:

- Egyptian date conversion at the admitted epoch anchor
- epagomenal boundary serialization
- prediction with positive and negative cycle offsets
- rising route with monkeypatched heliacal search
- epoch route with tolerance preservation
- empty annual search result as successful empty response
- rejection of invalid coordinates
- rejection of reversed and oversized year ranges
- rejection of invalid policy values
- drift-rate minimum-entry rejection
- condition-profile deterministic ordering
- network-profile node and edge kind preservation

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\sothic.py moira_server\services\sothic.py moira_server\routers\sothic.py tests\server\test_server_sothic_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_sothic_routes.py tests\unit\test_sothic.py tests\unit\test_sothic_public_api.py -q
```

Integration Sothic suites should be run before any admission that changes
heliacal search behavior or range-search policy.

## 9. Completion Boundary

P12-08 is not ready for implementation after this transport design.

This document is retained as the shape of a possible future admission. A later
specialist review must decide whether even the Stage 1 direct routes should be
exposed. Stage 2 and Stage 3 require a stronger public failure taxonomy before
route implementation, because they introduce delegated heliacal search,
bounded range scanning, and profile materialization.
