# P12-07 Huber Transport Design

Version: 0.2
Date: 2026-06-13
Status: admitted_direct_cusp_stage
Scope: Huber house-zone, Age Point, contact, and dynamic-intensity REST admission plan

## 1. Admission Boundary

P12-07 admits Huber transport in a direct-cusp stage.

Admitted direct-cusp routes:

- `POST /v1/huber/dynamic-intensity`
- `POST /v1/huber/house-zones`
- `POST /v1/huber/age-point`
- `POST /v1/huber/intensity-at`
- `POST /v1/huber/chart-intensity-profile`
- `POST /v1/huber/age-point-contacts`

Deferred:

- chart-backed house-frame derivation
- psychological interpretation text
- counseling, health, or clinical claims
- unbounded Age Point searches
- hidden house-system substitution
- independent house calculation inside Huber transport
- chart rendering
- transit or progression timing outside Age Point mechanics
- generic `/v1/special/*` exposure

## 2. Governing Object

The governing object is Huber house-frame analysis over an admitted house cusp
frame:

- golden-section zone division of each house
- 72-year Age Point cycle
- six years per house
- Dynamic Intensity Curve reconstruction
- intensity scores for named chart points
- bounded contact scan between Age Point and chart points

Huber doctrine prefers Koch houses. The engine accepts any `HouseCusps`
object, so the REST layer must preserve house-frame provenance rather than
pretending every supplied frame is doctrinally complete.

## 3. House-Frame Admission

Huber routes currently support one admitted house-frame source.

Direct cusp input:

- caller supplies 12 finite cusp longitudes
- caller supplies Ascendant, MC, and ARMC anchors required to construct
  Moira's `HouseCusps` vessel
- route marks `house_frame_source` as `caller_supplied`
- route does not claim Moira derived the houses

Future chart-backed house input:

- route derives houses through the already admitted server house adapter
- route records requested system, effective system, fallback status, and
  fallback reason
- route does not introduce a second house derivation path

The admitted implementation uses direct cusp input only. Chart-backed Huber is
deferred until it is bound through the already admitted server house adapter
without introducing a second house derivation path.

## 4. Request Shapes

`POST /v1/huber/dynamic-intensity`

Required fields:

- `house`: integer in `[1, 12]`
- `fraction`: finite fraction in `[0, 1]`

`POST /v1/huber/house-zones`

Required fields:

- `house_frame`: direct cusp frame only

`POST /v1/huber/age-point`

Required fields:

- `age_years`: non-negative finite number
- `house_frame`: direct cusp frame only

`POST /v1/huber/intensity-at`

Required fields:

- `longitude`: finite ecliptic longitude
- `house_frame`: direct cusp frame only

`POST /v1/huber/chart-intensity-profile`

Required fields:

- `points`: object mapping point names to finite ecliptic longitudes
- `house_frame`: direct cusp frame only

`POST /v1/huber/age-point-contacts`

Required fields:

- `points`: object mapping point names to finite ecliptic longitudes
- `house_frame`: direct cusp frame only

Optional fields:

- `orb`: non-negative finite degrees, default `2.0`
- `start_age`: non-negative finite years, default `0.0`
- `end_age`: finite years greater than or equal to `start_age`, default `72.0`
- `step_years`: positive finite years, default `1.0 / 12.0`

## 5. Bounds And Runtime Policy

Admitted route bounds:

- maximum point count for chart-intensity routes: 64
- maximum contact scan age span: 144 years
- minimum `step_years`: `1.0 / 52.0`
- maximum `orb`: 15 degrees

Contact scans remain synchronous only within these limits. Broader or
finer scans require a separate heavy-workflow design.

The public route rejects out-of-range dynamic-intensity fractions rather than
relying on the engine's internal clamping. Responses still report both
requested and effective fractions.

## 6. Response Shape

Dynamic-intensity responses contain:

- `house`
- `requested_fraction`
- `effective_fraction`
- `intensity`
- `zone`
- `curve_basis`
- `provenance`

House-zone responses contain:

- `zones`: 12 ordered zone records
- `house_frame`
- `house_frame_provenance`
- `huber_doctrine`
- `provenance`

Age Point responses contain:

- `age_years`
- `cycle`
- `house`
- `fraction_through_house`
- `longitude`
- `zone`
- `years_into_house`
- `intensity`
- `house_frame_provenance`
- `provenance`

Intensity-at responses contain:

- `longitude`
- `house`
- `fraction`
- `intensity`
- `zone`
- `house_frame_provenance`
- `provenance`

Chart-intensity responses contain:

- `scores`
- `high_intensity`
- `low_intensity`
- `mean_intensity`
- `point_count`
- `house_frame_provenance`
- `provenance`

Age Point contact responses contain:

- `contacts`
- `orb`
- `start_age`
- `end_age`
- `step_years`
- `scan_bounds`
- `house_frame_provenance`
- `provenance`

Each zone record preserves:

- `house`
- `cusp_longitude`
- `next_cusp_longitude`
- `house_size`
- `balance_point_longitude`
- `low_point_longitude`
- `balance_point_fraction`
- `low_point_fraction`

Each point score preserves:

- `name`
- `longitude`
- `house`
- `fraction`
- `intensity`
- `zone`
- `near_cusp`
- `near_low_point`

## 7. Validation Rules

The route family should reject:

- malformed house frames
- house frames without exactly 12 cusps
- non-finite cusp longitudes
- non-finite ages
- negative ages
- invalid house numbers
- fractions outside `[0, 1]` unless effective clamping is explicitly reported
- non-finite point longitudes
- empty point names
- oversized point maps
- non-finite or negative contact orbs
- oversized contact orbs
- reversed contact scan ranges
- negative `start_age`
- non-positive or too-small `step_years`
- contact scan spans above the transport maximum

The route must not silently relabel non-Koch houses as doctrinally Huber
complete. Non-Koch frames may be allowed as computational inputs only when the
response reports that they are not the Huber-preferred house system.

## 8. Provenance Rules

Every response preserves:

- `source_module`: `moira.huber`
- engine entrypoint
- `house_frame_source`: `caller_supplied` or `server_chart_backed`
- requested house system when chart-backed
- effective house system when chart-backed
- fallback state and fallback reason when present
- `is_koch_effective`
- `koch_doctrine_preferred`: true
- `curve_basis`: `piecewise_half_cosine_reconstruction`
- `curve_verification_note`: primary-text exact formula not independently
  verified
- route-level bounds applied
- `stage_sequence`: input validation, house-frame binding, engine computation,
  serialization

Direct cusp routes should state that cusp derivation is owned by the caller.
Chart-backed routes should state that house derivation is owned by the admitted
house adapter, not by Huber transport.

## 9. Verification Requirements For Admission

Route admission added focused server tests for:

- dynamic-intensity cusp, Low Point, and next-cusp values
- dynamic-intensity invalid house rejection
- dynamic-intensity out-of-range fraction rejection or effective-fraction
  reporting
- house-zone count and golden-section fractions
- direct cusp frame provenance
- chart-backed house-frame provenance, if admitted
- non-Koch frame reporting
- Age Point ages 0, 18, 36, 54, and 72
- negative-age rejection
- intensity-at result range and house assignment
- chart-intensity point-name preservation
- high and low intensity list preservation
- bounded contact scan with deterministic ordering
- rejection of malformed house frames and non-finite cusps
- rejection of oversized point maps
- rejection of invalid contact scan bounds

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\huber.py moira_server\services\huber.py moira_server\routers\huber.py tests\server\test_server_huber_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_huber_routes.py tests\unit\test_huber.py -q
```

If chart-backed Huber routes are implemented, include the admitted houses
server test slice because Huber must not invent an independent house derivation
path.

## 10. Completion Boundary

P12-07 is admitted as a direct-cusp Huber route family.

Completion covers direct dynamic-intensity, house-zone, Age Point,
intensity-at-longitude, chart-intensity-profile, and bounded Age Point contact
transport over a caller-supplied house frame. The route family does not derive
houses, does not perform chart construction, and does not expose chart-backed
Huber until that path is bound through the admitted house adapter.

## 11. Admission Record

Implemented files:

- `moira_server/models/huber.py`
- `moira_server/services/huber.py`
- `moira_server/routers/huber.py`
- `tests/server/test_server_huber_routes.py`

Registered routes:

- `POST /v1/huber/dynamic-intensity`
- `POST /v1/huber/house-zones`
- `POST /v1/huber/age-point`
- `POST /v1/huber/intensity-at`
- `POST /v1/huber/chart-intensity-profile`
- `POST /v1/huber/age-point-contacts`

Admission constraints:

- all house frames are caller-supplied direct cusp frames
- direct frames require 12 finite cusps plus caller-supplied Ascendant, MC,
  and ARMC anchors
- non-Koch frames are accepted as computational inputs but reported as not
  doctrinally complete Huber house fidelity
- chart-backed house derivation remains deferred
- psychological, counseling, health, clinical, rendering, and generic
  `/v1/special/*` outputs remain deferred

Verification performed:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\huber.py moira_server\services\huber.py moira_server\routers\huber.py moira_server\routers\__init__.py moira_server\app.py tests\server\test_server_huber_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_huber_routes.py tests\unit\test_huber.py -q
```

Result:

- focused Huber pytest set passed
- collected test count: `15` server tests plus `55` unit tests

Live route audit after admission:

- total non-documentation routes: `313`
- versioned `/v1` routes: `309`
- `/v1/huber/*` routes: `6`
