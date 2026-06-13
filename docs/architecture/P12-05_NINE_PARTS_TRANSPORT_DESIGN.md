# P12-05 Nine Parts Transport Design

Version: 0.2
Date: 2026-06-13
Status: admitted
Scope: Abu Ma'shar Nine Parts REST admission plan

## 1. Admission Boundary

P12-05 admits one bounded chart-input REST surface for the existing
`moira.nine_parts` engine:

- `POST /v1/nine-parts/abu-mashar`

This route should expose the complete `NinePartsAggregate` produced by
`nine_parts_abu_mashar(...)`.

Deferred:

- automatic night/sect determination from chart houses
- Ascendant derivation
- chart construction
- solar-return integration
- Al-Sijzi Transfer of Management
- longevity integration
- comparison bundles against `moira.lots`
- Hellenistic nonomoiria
- Vedic Navamsha or any D9 route
- interpretive narrative text

## 2. Governing Object

The governing object is Abu Ma'shar's Nine Parts aggregate:

- nine canonical parts in order
- full-reversal night policy
- direct and derived dependency relations
- per-part computation truth
- condition profiles
- aggregate intelligence
- validation results from `validate_nine_parts_output(...)`

The transport layer must not recompute formula doctrine. It should call
`nine_parts_abu_mashar(...)` and serialize the resulting engine vessels.

## 3. Request Shape

`POST /v1/nine-parts/abu-mashar`

Required fields:

- `asc`: finite Ascendant longitude in degrees
- `planets`: object mapping required body keys to finite longitudes
- `is_night_chart`: boolean supplied by the caller

Required `planets` keys:

- `Sun`
- `Moon`
- `Mars`
- `Jupiter`
- `Saturn`
- `North Node`

Optional fields:

- `policy`: omitted by default
- `include_validation`: boolean, default `true`

Policy admission should be narrow:

- `reversal_rule`: only `full_reversal`
- `historical_scope`: only
  `evidenced_core_plus_admitted_extension`

The route should reject unknown policy values rather than silently falling back.

## 4. Response Shape

The response should contain:

- `parts`: nine part records in canonical order
- `dependency_relations`: nine dependency records in canonical order
- `condition_profiles`: nine condition records in canonical order
- `aggregate`: aggregate summaries
- `policy`: effective policy
- `validation`: validation result list and pass/fail boolean
- `provenance`: computation provenance

Each part record should preserve:

- `name`
- `planet_association`
- `historical_status`
- `meaning`
- `longitude`
- `sign`
- `sign_degree`
- `sign_symbol`
- `dependency_kind`
- `computation`

Each computation record should preserve:

- `asc_longitude`
- `add_key`
- `sub_key`
- `add_longitude`
- `sub_longitude`
- `is_night_chart`
- `formula_reversed`
- `formula_variant`
- `formula`

The response must not collapse Sword and Node into ordinary planetary lots.
They should remain admitted extension parts.

## 5. Validation Rules

The route should reject:

- non-finite `asc`
- non-object `planets`
- missing required planet keys
- non-finite planet longitudes
- non-boolean `is_night_chart`
- unsupported policy objects
- unsupported reversal rules
- unsupported historical scopes

The route should return a validation block even when engine construction
succeeds:

- `passed`: true when `validate_nine_parts_output(...)` returns no failures
- `failures`: exact failure strings, if any

Internal validation failures after successful construction should be surfaced as
server validation errors, not hidden or repaired.

## 6. Provenance Rules

Every response should preserve:

- `source_module`: `moira.nine_parts`
- `engine_entrypoint`: `nine_parts_abu_mashar`
- `validation_entrypoint`: `validate_nine_parts_output`
- `doctrine`: `Abu_Mashar_Nine_Parts`
- `reversal_rule`: `full_reversal`
- `historical_scope`: effective policy value
- `night_determination_owner`: `caller_supplied`
- `ascendant_derivation_owner`: `caller_supplied`
- `formula_basis`: `Asc + Add - Sub mod 360`
- `stage_sequence`: input validation, engine computation, engine validation,
  serialization

The provenance must explicitly state that this route does not compute night
status, house placement, or Ascendant.

## 7. Verification Requirements For Admission

Route admission should add focused server tests for:

- successful day chart computation
- successful night chart computation with all parts reversed
- canonical nine-part order
- derived dependency preservation for Love, Necessity, and Victory
- Sword and Node historical status as admitted extensions
- validation block returned with no failures for a valid fixture
- rejection of missing `Sun`, `Moon`, and `North Node`
- rejection of non-finite Ascendant and planet longitudes
- rejection of non-boolean `is_night_chart`
- rejection of unsupported policy values

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\nine_parts.py moira_server\services\nine_parts.py moira_server\routers\nine_parts.py tests\server\test_server_nine_parts_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_nine_parts_routes.py tests\unit\test_nine_parts.py -q
```

## 8. Completion Boundary

P12-05 is admitted as a single aggregate route.

The first completion target is the single aggregate route only. The family is
not complete for chart construction, sect derivation, solar-return integration,
longevity integration, Al-Sijzi management, or comparative lot bundles.

## 9. Admission Record

Implemented files:

- `moira_server/models/nine_parts.py`
- `moira_server/services/nine_parts.py`
- `moira_server/routers/nine_parts.py`
- `tests/server/test_server_nine_parts_routes.py`

Registered route:

- `POST /v1/nine-parts/abu-mashar`

Verification performed:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\nine_parts.py moira_server\services\nine_parts.py moira_server\routers\nine_parts.py tests\server\test_server_nine_parts_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_nine_parts_routes.py tests\unit\test_nine_parts.py -q
```

Result:

- `93 passed`

Live route audit after admission:

- total non-documentation routes: `305`
- versioned `/v1` routes: `301`
- `/v1/nine-parts/*` routes: `1`
