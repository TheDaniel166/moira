# P12-10 Lord Of The Orb Transport Design

Version: 0.1
Date: 2026-06-13
Status: transport_design_complete
Scope: Abu Ma'shar Lord of the Orb REST admission plan

## 1. Admission Boundary

P12-10 should admit two bounded REST routes:

- `POST /v1/lord-of-the-orb/sequence`
- `POST /v1/lord-of-the-orb/current`

These routes expose the existing `moira.lord_of_the_orb` engine. They do not
compute the birth planetary hour.

Deferred:

- birth planetary-hour derivation
- chart construction
- annual hierarchy orchestration
- integration with profections or firdaria
- natal or solar-return dignity scoring
- comparison bundles
- interpretive narrative text

## 2. Governing Object

The governing object is the Lord of the Orb sequence:

- Chaldean-order planet cycle
- 12-house cycle
- selected cycle variant
- period records
- condition profiles
- aggregate intelligence
- validation results from `validate_lord_of_orb_output(...)`

The birth planet is caller-supplied. It should be described as the ruler of the
birth planetary hour, but the route must not derive it.

## 3. Request Shapes

`POST /v1/lord-of-the-orb/sequence`

Required fields:

- `birth_planet`: one of `Saturn`, `Jupiter`, `Mars`, `Sun`, `Venus`,
  `Mercury`, `Moon`
- `years`: integer >= 1

Optional fields:

- `cycle_kind`: `continuous_loop` or `single_cycle`, default
  `continuous_loop`
- `include_validation`: boolean, default `true`

`POST /v1/lord-of-the-orb/current`

Required fields:

- `birth_planet`: one admitted Chaldean planet
- `age`: integer >= 0

Optional fields:

- `cycle_kind`: `continuous_loop` or `single_cycle`, default
  `continuous_loop`
- `include_validation`: boolean, default `true`

The current-period route should internally compute only enough sequence truth to
validate the selected year.

## 4. Response Shape

Sequence responses should contain:

- `sequence`
- `periods`
- `condition_profiles`
- `aggregate`
- `policy`
- `validation`
- `provenance`

Current-period responses should contain:

- `period`
- `condition_profile`
- `age`
- `year_of_life`
- `policy`
- `validation`
- `provenance`

Each period record should preserve:

- `year`
- `planet`
- `house`
- `chaldean_index`
- `cycle_kind`
- `house_signification`
- derived inspectability fields where useful

Aggregate records should preserve:

- `benefic_years`
- `malefic_years`
- `planet_year_counts`
- `cycle_coincidence_years`

## 5. Validation Rules

The route family should reject:

- invalid birth planets
- empty birth planet strings
- `years < 1`
- `age < 0`
- non-integer `years`
- non-integer `age`
- unsupported cycle kinds
- excessive sequence spans

Recommended initial transport span limit:

- maximum `years`: 252

This permits three complete 84-year combined cycles while preventing the REST
surface from becoming an unbounded sequence generator.

The response should include validation output:

- `passed`: true when `validate_lord_of_orb_output(...)` returns no failures
- `failures`: exact failure strings, if any

## 6. Provenance Rules

Every response should preserve:

- `source_module`: `moira.lord_of_the_orb`
- `engine_entrypoint`: `lord_of_orb` or `current_lord_of_orb`
- `validation_entrypoint`: `validate_lord_of_orb_output`
- `birth_planet_source`: `caller_supplied_birth_planetary_hour_ruler`
- `planetary_hour_derivation_owner`: `not_this_route`
- `cycle_kind`: effective cycle kind
- `cycle_basis`: `Chaldean_order`
- `house_cycle_basis`: `twelve_house_modular_cycle`
- `hierarchy_rank`: 6
- `stage_sequence`: input validation, engine computation, engine validation,
  serialization

The provenance must distinguish the Lord of the Orb from the Lord of the Turn.
They are historically name-confusable but computationally distinct in Moira.

## 7. Verification Requirements For Admission

Route admission should add focused server tests for:

- successful 84-year continuous-loop sequence
- successful single-cycle sequence
- Torres Venus recurrence preservation
- current route age 0 maps to year 1
- current route age 7 maps to year 8
- rejection of invalid birth planets
- rejection of `years < 1`
- rejection of `age < 0`
- rejection of unsupported cycle kinds
- rejection of sequences beyond the transport maximum
- validation block returned for valid results

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\lord_of_the_orb.py moira_server\services\lord_of_the_orb.py moira_server\routers\lord_of_the_orb.py tests\server\test_server_lord_of_the_orb_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_lord_of_the_orb_routes.py tests\unit\test_lord_of_the_orb.py -q
```

## 8. Completion Boundary

P12-10 is ready for implementation after this transport design.

Completion covers only caller-seeded Lord of the Orb sequence and current-period
transport. It does not include birth-hour calculation, annual hierarchy
orchestration, dignity scoring, or interpretation.
