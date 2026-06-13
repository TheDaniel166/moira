# P11-02 Variable Stars Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: bounded variable-star catalog, state, range, aggregate profile, and pair
REST routes

## 1. Admission Boundary

P11-02 admits the narrow variable-star REST surface:

- `GET /v1/stars/variable/list`
- `GET /v1/stars/variable/{name}`
- `POST /v1/stars/variable/state`
- `POST /v1/stars/variable/range`
- `POST /v1/stars/variable/catalog-profile`
- `POST /v1/stars/variable/pair`

This is not exhaustive GCVS or live observational variable-star exposure. It
admits HTTP transport over Moira's curated Variable Star Oracle.

Deferred:

- real-time AAVSO/VSX observation refresh
- exhaustive GCVS catalog search
- variable-star positional overlays
- rendered light-curve products
- secondary-eclipse dedicated products
- multi-period semi-regular modeling beyond the current dominant-period engine

## 2. Governing Object

The admitted REST result is derived from `moira.variable_stars`.

The transport layer does not recompute variable-star doctrine. It performs:

1. request validation
2. datetime to Julian Day conversion where a datetime is supplied
3. catalog resolution through `variable_star`
4. selected computation through the admitted engine functions
5. response serialization with explicit provenance

## 3. Request Shapes

`GET /v1/stars/variable/list`

- `q`: optional search term
- `var_type`: optional GCVS variability type filter
- `limit`: bounded by the router at 500

`GET /v1/stars/variable/{name}`

- `name`: variable-star name or designation

`POST /v1/stars/variable/state`

- `dt`: timezone-aware datetime
- `star`: non-empty variable-star name or designation
- `eclipse_threshold`: optional, finite, `0.0 <= value <= 5.0`

`POST /v1/stars/variable/range`

- `star`: non-empty variable-star name or designation
- `jd_start`: finite Julian Day
- `jd_end`: finite Julian Day, greater than or equal to `jd_start`
- range span: at most 366 days

`POST /v1/stars/variable/catalog-profile`

- `dt`: timezone-aware datetime
- `eclipse_threshold`: optional, finite, `0.0 <= value <= 5.0`

`POST /v1/stars/variable/pair`

- `dt`: timezone-aware datetime
- `primary`: non-empty variable-star name or designation
- `secondary`: non-empty variable-star name or designation
- `eclipse_threshold`: optional, finite, `0.0 <= value <= 5.0`

## 4. Response Shape

Catalog responses preserve:

- variable-star name and designation
- GCVS type
- epoch, period, and epoch phase convention
- magnitude bounds and eclipse width
- classical quality and derived type flags
- catalog note
- provenance

State/profile/pair/range responses preserve the existing computed fields and
add top-level provenance.

The provenance object records:

- requested datetime and normalized UTC datetime when applicable
- Julian Day used for computation when applicable
- computation source: `variable_star_oracle`
- catalog sources: GCVS, AAVSO VSX, published linear ephemerides
- requested and returned stars
- eclipse-threshold policy
- phase convention
- transport stage sequence

## 5. Validation Rules

The admitted surface rejects:

- naive datetimes on datetime-backed routes
- empty variable-star names
- non-finite JD range inputs
- reversed JD windows
- range windows above 366 days
- eclipse thresholds outside `[0.0, 5.0]`

Unknown variable-star names remain semantic lookup failures from the underlying
Variable Star Oracle.

## 6. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\stars.py moira_server\services\stars.py moira_server\serializers\stars.py tests\server\test_server_stars_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_stars_routes.py -q
```

Route registry audit after admission:

- 269 non-documentation routes
- 265 versioned `/v1` routes
- 12 `/v1/stars/*` routes
- exactly 6 admitted variable-star routes:
  - `/v1/stars/variable/list`
  - `/v1/stars/variable/{name}`
  - `/v1/stars/variable/state`
  - `/v1/stars/variable/range`
  - `/v1/stars/variable/catalog-profile`
  - `/v1/stars/variable/pair`

The route tests verify:

- route registration
- catalog-record fidelity
- state parity against `star_condition_profile`, `next_minimum`, and
  `next_maximum`
- extrema range parity against `minima_in_range` and `maxima_in_range`
- catalog-profile parity against `catalog_profile`
- pair parity against `star_state_pair`
- provenance preservation
- adversarial request rejection for datetime, names, thresholds, and range
  bounds

## 7. Admission Verdict

P11-02 is admitted as a bounded synchronous variable-star catalog/state/profile
REST family.

Later variable-star work is explicit expansion, not implicit widening of this
admitted surface.
