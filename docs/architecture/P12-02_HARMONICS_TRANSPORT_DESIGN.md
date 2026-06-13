# P12-02 Harmonics Transport Design

Version: 0.3
Date: 2026-06-13
Status: admitted
Scope: harmonic chart, age harmonic, pattern, sweep, and fingerprint REST admission record

## 1. Admission Boundary

P12-02 admits harmonic transport in stages.

Stage 1 is admitted as pure direct routes:

- `GET /v1/harmonics/presets`
- `POST /v1/harmonics/chart`
- `POST /v1/harmonics/age-chart`

Stage 2 is admitted for bounded pattern-analysis routes:

- `POST /v1/harmonics/conjunctions`
- `POST /v1/harmonics/pattern-score`
- `POST /v1/harmonics/aspects`

Stage 3 is admitted for bounded heavier routes:

- `POST /v1/harmonics/sweep`
- `POST /v1/harmonics/fingerprint`
- `POST /v1/harmonics/composite`

Deferred:

- unbounded harmonic sweeps
- unbounded body maps
- automatic chart construction
- transit or progression harmonic searches
- harmogram or spectral-analysis routes
- chart rendering
- interpretive narrative text
- generic `/v1/special/*` exposure

## 2. Governing Object

The governing object is harmonic transformation over caller-supplied ecliptic
longitudes:

```text
harmonic_longitude = (natal_longitude * harmonic) mod 360
```

The REST layer must not derive chart positions, houses, signs, or event times.
It receives named longitude maps, validates them, calls `moira.harmonics`, and
serializes the engine result vessels.

The route family must preserve the difference between:

- integer harmonic projection
- decimal age harmonic projection
- one-harmonic conjunction or pattern scoring
- range-based sweep and fingerprint materialization
- cross-chart composite harmonic comparison

## 3. Request Shapes

`GET /v1/harmonics/presets`

- no request body

`POST /v1/harmonics/chart`

Required fields:

- `longitudes`: object mapping body names to finite ecliptic longitudes
- `harmonic`: integer in the admitted transport range

`POST /v1/harmonics/age-chart`

Required fields:

- `longitudes`: object mapping body names to finite ecliptic longitudes
- `jd_birth`: finite Julian Day
- `jd_now`: finite Julian Day greater than or equal to `jd_birth`

`POST /v1/harmonics/conjunctions`

Required fields:

- `longitudes`
- `harmonic`

Optional fields:

- `orb`: non-negative finite degrees, default `1.0`

`POST /v1/harmonics/pattern-score`

- same request shape as `/v1/harmonics/conjunctions`

`POST /v1/harmonics/aspects`

Required fields:

- `longitudes`

Optional fields:

- `orb`: non-negative finite degrees, default `1.0`
- `max_harmonic`: integer in the admitted transport range, default `32`

`POST /v1/harmonics/sweep`

Required fields:

- `longitudes`

Optional fields:

- `max_harmonic`: integer in the admitted transport range, default `32`
- `orb`: non-negative finite degrees, default `1.0`

`POST /v1/harmonics/fingerprint`

- same request shape as `/v1/harmonics/sweep`

`POST /v1/harmonics/composite`

Required fields:

- `longitudes_a`: object mapping body names to finite ecliptic longitudes
- `longitudes_b`: object mapping body names to finite ecliptic longitudes
- `harmonic`: integer in the admitted transport range

Optional fields:

- `orb`: non-negative finite degrees, default `1.0`
- `label_a`: non-empty chart label, default `A`
- `label_b`: non-empty chart label, default `B`

## 4. Bounds And Runtime Policy

Recommended initial route bounds:

- maximum body count per single chart: 64
- maximum body count per composite chart: 32 per side
- maximum admitted harmonic: 128
- default `max_harmonic`: 32
- maximum `max_harmonic`: 128
- maximum `orb`: 30 degrees
- maximum label length: 64 characters

These are transport bounds, not harmonic doctrine.

The public transport layer should reject invalid harmonic values before calling
the engine. The engine currently coerces some values to minimum valid internal
values; public REST must not hide that correction from users. Either the route
rejects the request or it reports both requested and effective harmonic values.

## 5. Response Shape

Preset responses should contain:

- `presets`: ordered records keyed by harmonic number
- `provenance`

Harmonic chart and age-chart responses should contain:

- `positions`: ordered harmonic-position records
- `requested_harmonic`
- `effective_harmonic`
- `harmonic_kind`: `integer` or `age_decimal`
- `input_count`
- `provenance`

Each harmonic-position record should preserve:

- `body`
- `natal_longitude`
- `harmonic_longitude`
- `harmonic`
- `sign`
- `sign_symbol`
- `sign_degree`

Conjunction responses should contain:

- `conjunctions`
- `requested_harmonic`
- `effective_harmonic`
- `orb`
- `input_count`
- `provenance`

Pattern-score responses should contain:

- `pattern_score`
- `conjunctions`
- `cluster_sizes`
- `score`
- `requested_harmonic`
- `effective_harmonic`
- `orb`
- `provenance`

Sweep responses should contain:

- `entries`
- `max_harmonic`
- `orb`
- `input_count`
- `bounds`
- `provenance`

Fingerprint responses should contain:

- `sweep`
- `dominant`
- `total_score`
- `peak_harmonic`
- `peak_score`
- `max_harmonic`
- `orb`
- `bounds`
- `provenance`

Composite responses should contain:

- `conjunctions`
- `requested_harmonic`
- `effective_harmonic`
- `orb`
- `label_a`
- `label_b`
- `input_count_a`
- `input_count_b`
- `provenance`

## 6. Validation Rules

The route family should reject:

- empty longitude maps
- non-object longitude maps
- empty body names
- duplicate body names after transport normalization
- non-finite longitudes
- non-finite JDs
- `jd_now < jd_birth`
- harmonic values below 1
- non-integer harmonics for integer-harmonic routes
- `max_harmonic < 1`
- `max_harmonic` above the transport maximum
- negative, non-finite, or oversized orbs
- body maps above the transport maximum
- empty composite labels
- composite labels containing the route separator `:`

Longitudes may be outside `[0, 360)` at input only if the route explicitly
normalizes and reports the submitted value and normalized value. The simpler
first admission should require finite numbers and preserve the engine's
modulo-reduced output.

## 7. Provenance Rules

Every response should preserve:

- `source_module`: `moira.harmonics`
- engine entrypoint
- `input_longitude_owner`: `caller_supplied`
- `chart_construction_owner`: `not_this_route`
- `formula_basis`: `(longitude * harmonic) mod 360`
- `harmonic_kind`: `integer`, `age_decimal`, `range_sweep`, or `composite`
- `preset_name` and `preset_description` when available
- `bounds` for body count, harmonic maximum, and orb maximum
- `stage_sequence`: input validation, engine computation, serialization

Age-harmonic responses should also preserve:

- `jd_birth`
- `jd_now`
- `age_harmonic_basis`: `(jd_now - jd_birth) / tropical_year`

Sweep and fingerprint responses must state that the scoring is a pattern
density measure, not an interpretive judgment.

## 8. Verification Record

Route admission added focused server tests for:

- preset catalogue serialization
- direct H1 identity over a small fixture
- direct H5 formula truth
- output sorting by harmonic longitude
- age-harmonic decimal harmonic preservation
- `jd_now < jd_birth` rejection
- rejection of non-finite longitudes
- rejection of empty body maps
- rejection of duplicate body names after trimming
- rejection of invalid harmonics
- rejection of oversized body maps
- one-harmonic conjunction detection
- pattern-score cluster preservation
- harmonic-aspect dual-path equivalence against conjunctions
- bounded sweep ordering and count
- fingerprint peak and total-score invariants
- composite labels and no same-chart pair leakage
- rejection of oversized sweeps
- rejection of invalid or oversized orbs
- rejection of invalid composite labels and oversized composite maps

Verification run for admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\harmonics.py moira_server\services\harmonics.py moira_server\routers\harmonics.py moira_server\app.py moira_server\routers\__init__.py tests\server\test_server_harmonics_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_harmonics_routes.py tests\unit\test_harmonics.py -q
```

Result: 106 focused server and unit tests passed.

## 9. Completion Boundary

P12-02 completion covers preset discovery, direct harmonic projection,
age-harmonic projection, one-harmonic conjunctions, pattern scoring,
harmonic-aspect decoding, bounded harmonic sweeps, bounded vibrational
fingerprints, and bounded composite harmonic comparison over caller-supplied
longitudes.

It does not include unbounded sweeps, automatic chart construction, transit or
progression harmonic searches, harmogram or spectral-analysis routes, chart
rendering, interpretive narrative text, or generic `/v1/special/*` exposure.
