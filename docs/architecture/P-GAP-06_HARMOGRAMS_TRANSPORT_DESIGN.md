# P-GAP-06 Harmograms Transport Design

Version: 0.1
Date: 2026-06-14
Status: implemented and admitted
Scope: bounded REST admission for harmogram vectors, intensity spectra,
projections, and explicit-sample traces

This design follows `wiki/02_standards/HARMOGRAMS_BACKEND_STANDARD.md`.

P-GAP-06 closes the facade/root gap for:

- `point_set_harmonic_vector`
- `zero_aries_parts_harmonic_vector`
- `intensity_function_spectrum`
- `project_harmogram_strength`
- `harmogram_trace`

It is separate from `/v1/harmonics/*`. Harmonics routes project ordinary
longitudes into harmonic charts and related aspect products. Harmograms routes
expose spectral vectors, intensity spectra, projection terms, and trace
series.

---

## 1. Route Family

Prefix:

- `/v1/harmograms`

Routes:

- `POST /v1/harmograms/vector`
- `POST /v1/harmograms/zero-aries-vector`
- `POST /v1/harmograms/intensity-spectrum`
- `POST /v1/harmograms/projection`
- `POST /v1/harmograms/trace`

---

## 2. Request Models

Shared position input:

- `name`: non-empty string, trimmed, maximum 64 characters
- `degree`: finite longitude value

Shared harmonic-domain policy:

- `harmonic_start`: integer in `[1, 128]`
- `harmonic_stop`: integer in `[1, 128]`
- width may not exceed `32`

Vector policy:

- `normalization_mode`: `raw_sum` or `mean_resultant`
- `harmonic_domain`

Parts policy:

- `pair_construction_mode`: `ordered` or `unordered`
- `self_pair_mode`: `include` or `exclude`

Intensity policy:

- `family`: one of the four admitted engine families
- `include_conjunction`
- `harmonic_domain`
- `orb_width_deg`: finite value in `(0, 90]`
- `sample_count`: integer in `[256, 8192]`
- gaussian policies require `gaussian_width_deg`

Trace policy:

- `samples`: explicit caller-supplied sample list
- `harmonic_numbers`: unique positive integers
- `trace_family`
- `output_mode`
- `point_set_policy`
- `parts_policy`
- `intensity_policy`

Trace family controls required sample fields:

- `dynamic_zero_aries_parts`: `positions`
- `transit_to_natal_zero_aries_parts`: `transit_positions`, `natal_positions`
- `directed_to_natal_zero_aries_parts`: `directed_positions`, `natal_positions`
- `progressed_to_natal_zero_aries_parts`: `progressed_positions`,
  `natal_positions`

Trace samples must be strictly increasing by `time`.

---

## 3. Bounds

The admitted synchronous limits are:

- point-set positions: `32`
- relational positions per side: `24`
- harmonic-domain width: `32`
- harmonic number: `128`
- intensity sample count: `256` to `8192`
- trace samples: `64`
- trace cells: `256`, where cells are sample count multiplied by harmonic count

These bounds are transport admission policy. They do not alter engine limits.

---

## 4. Response Models

Vector responses expose:

- source kind: `point_set` or `zero_aries_parts`
- vector policy and harmonic domain
- body/source/target names
- point or parts count
- harmonic-zero amplitude
- harmonic components with harmonic, amplitude, and phase

Intensity responses expose:

- harmonic number
- resolved intensity policy
- realization mode
- harmonic-zero amplitude
- spectral components

Projection responses expose:

- source vector
- intensity spectrum
- normalization mode
- projection realization mode
- harmonic-zero contribution
- total strength
- per-harmonic projection terms

Trace responses expose:

- resolved trace policy
- interval bounds
- sample times
- one series per harmonic number
- one intensity spectrum per series
- sample source vectors, projection terms, and strengths

---

## 5. Provenance

Every envelope records:

- `source_module`: `moira.harmograms`
- exact engine entrypoint
- `input_position_owner`: `caller_supplied`
- `chart_sampling_owner`: `not_this_route`
- `interpretation_owner`: `not_returned`
- output bounds
- stage sequence

---

## 6. Implementation Files

Implemented files:

- `moira_server/models/harmograms.py`
- `moira_server/services/harmograms.py`
- `moira_server/routers/harmograms.py`
- `tests/server/test_server_harmograms_routes.py`

Router registration:

- export router from `moira_server/routers/__init__.py`
- include router in `moira_server/app.py`
- export request/response models from `moira_server/models/__init__.py`

REST reference update:

- route group count increases by `1`
- `/v1` route count increases by `5`
- `harmograms` route group is added with five routes
- Harmograms REST Admission Boundary section is added

Gap ledger update:

- P-GAP-06 marked `admitted`
- next gap workflow becomes `P-GAP-F1` facade parity review

---

## 7. Verification Requirements

Focused server tests:

- point-set vector parity with `point_set_harmonic_vector`
- Zero-Aries vector parity with `zero_aries_parts_harmonic_vector`
- intensity spectrum parity with `intensity_function_spectrum`
- projection parity with `project_harmogram_strength`
- trace parity with `harmogram_trace`
- duplicate name rejection
- invalid gaussian policy rejection
- mismatched vector/intensity domain rejection
- oversized trace rejection
- method-boundary checks

Implementation verification:

- `.venv\Scripts\python.exe -m py_compile` for new and touched server files
- `.venv\Scripts\python.exe -m pytest tests/server/test_server_harmograms_routes.py -q`
- live route registry audit confirming the five designed routes

No new astronomy-oracle validation is required. This is adapter admission over
the existing harmogram engine.

---

## 8. Non-Goals

This design does not admit:

- chart-backed harmogram route construction
- ephemeris-backed dynamic trace generation
- arbitrary intensity functions
- unbounded sweeps
- dense map/rendering products
- async jobs
- interpretation or recommendation text
- replacement of `/v1/harmonics/*`

---

## 9. Admission Result

P-GAP-06 is implemented and admitted.

Admitted implementation surface:

- `POST /v1/harmograms/vector`
- `POST /v1/harmograms/zero-aries-vector`
- `POST /v1/harmograms/intensity-spectrum`
- `POST /v1/harmograms/projection`
- `POST /v1/harmograms/trace`

Verification performed:

- `.venv\Scripts\python.exe -m py_compile moira_server\models\harmograms.py moira_server\services\harmograms.py moira_server\routers\harmograms.py moira_server\app.py moira_server\routers\__init__.py moira_server\models\__init__.py`
- `.venv\Scripts\python.exe -m pytest tests/server/test_server_harmograms_routes.py -q`
- live route registry audit confirmed five P-GAP-06 routes, `342`
  versioned `/v1` routes, and `346` total non-documentation routes
