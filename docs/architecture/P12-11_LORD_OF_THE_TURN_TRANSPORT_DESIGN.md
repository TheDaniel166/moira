# P12-11 Lord Of The Turn Transport Design

Version: 0.1
Date: 2026-06-13
Status: transport_design_complete
Scope: Lord of the Turn REST admission plan

## 1. Admission Boundary

P12-11 should admit one direct Solar Return chart-input route:

- `POST /v1/lord-of-the-turn/profile`

This route exposes `moira.lord_of_the_turn.lord_of_turn(...)` over a caller
supplied `LordOfTurnSRChart` shape.

Deferred:

- Solar Return chart construction
- house calculation
- ephemeris position derivation
- automatic sect calculation
- SR Lot of Fortune calculation
- annual hierarchy orchestration
- combined annual timing dashboards
- interpretive narrative text

## 2. Governing Object

The governing object is a `LordOfTurnConditionProfile` containing:

- profected natal Ascendant
- method-specific candidate assessment
- selected lord
- selection reason
- blocker reasons
- witnessing truth
- SR condition summary
- validation results from `validate_lord_of_turn_output(...)`

The route must preserve the distinction between:

- Al-Qabisi succession hierarchy
- Egyptian / Al-Sijzi testimony method
- DOMICILE_ONLY degenerate mode when house placements are omitted

## 3. Request Shape

`POST /v1/lord-of-the-turn/profile`

Required fields:

- `natal_asc`: finite natal Ascendant longitude
- `age`: integer >= 0
- `sr_chart`: object matching the `LordOfTurnSRChart` input vessel

`sr_chart` fields:

- `sr_asc`: finite Solar Return Ascendant longitude
- `planets`: object mapping planet names to finite SR longitudes
- `house_placements`: optional object mapping planet names to houses 1-12
- `is_night`: boolean, default false
- `retrograde_planets`: optional list of planet names
- `sr_lot_fortune`: optional finite longitude

Optional policy fields:

- `method`: `al_qabisi` or `egyptian_al_sijzi`, default `al_qabisi`
- `combust_orb`: positive finite number, default `8.5`
- `include_validation`: boolean, default `true`

## 4. Response Shape

The response should contain:

- `profile`
- `result`
- `profection`
- `candidates`
- `policy`
- `validation`
- `provenance`

The profection record should preserve:

- `natal_asc`
- `age`
- `profected_longitude`
- `profected_sign`
- `profected_degree_in_sign`
- `profected_sign_index`

Each candidate record should preserve:

- `planet`
- `role`
- `sr_house`
- `is_combust`
- `is_retrograde`
- `is_well_placed`
- `blocker_reasons`
- `witnesses_target`
- `testimony_count`

The result record should preserve:

- `lord`
- `method`
- `selection_reason`
- `sign_of_year`
- `blocked_candidates`
- `is_fallback`

The profile record should preserve:

- `sr_is_night`
- `sect_light`
- `lord_witnesses_sr_asc`
- `lord_sr_house`

## 5. Validation Rules

The route should reject:

- non-finite `natal_asc`
- `age < 0`
- non-integer `age`
- non-finite `sr_chart.sr_asc`
- non-object `sr_chart.planets`
- non-finite planet longitudes
- house placements outside 1-12
- non-finite `sr_lot_fortune`
- unsupported methods
- non-positive or non-finite `combust_orb`
- malformed retrograde planet lists

The route may allow empty `house_placements`, but must report that
`DOMICILE_ONLY` mode was used when the engine selects that path.

The response should include validation output:

- `passed`: true when `validate_lord_of_turn_output(...)` returns no failures
- `failures`: exact failure strings, if any

## 6. Provenance Rules

Every response should preserve:

- `source_module`: `moira.lord_of_the_turn`
- `engine_entrypoint`: `lord_of_turn`
- `validation_entrypoint`: `validate_lord_of_turn_output`
- `method`: effective method
- `combust_orb`: effective combust orb
- `sr_chart_owner`: `caller_supplied`
- `solar_return_construction_owner`: `not_this_route`
- `house_calculation_owner`: `not_this_route`
- `sect_owner`: `caller_supplied_sr_is_night`
- `witnessing_target`: `sr_asc_or_sect_light`
- `stage_sequence`: input validation, SR chart vessel construction, engine
  computation, engine validation, serialization

For Egyptian / Al-Sijzi mode, provenance must preserve that testimony count is
the current binary-count Moira formalization. It must not be described as a
weighted almuten score.

For Al-Qabisi mode, provenance must preserve sequential succession. The route
must not imply a tiebreaker among simultaneously qualified candidates.

## 7. Verification Requirements For Admission

Route admission should add focused server tests for:

- Al-Qabisi DOMICILE_ONLY profile
- Al-Qabisi domicile well-placed selection
- Al-Qabisi exaltation fallback
- Al-Qabisi triplicity fallback
- Al-Qabisi bound fallback
- Egyptian / Al-Sijzi bound-primary witnessing
- Egyptian / Al-Sijzi testimony-winner witnessing
- Egyptian / Al-Sijzi bound fallback
- blocker preservation for cadent, combust, and retrograde candidates
- SR ASC or sect-light witnessing preservation
- rejection of invalid natal Ascendant
- rejection of negative age
- rejection of invalid SR chart longitudes
- rejection of invalid house placements
- rejection of invalid method and combust orb
- validation block returned for valid profiles

Minimum verification after route implementation:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\lord_of_the_turn.py moira_server\services\lord_of_the_turn.py moira_server\routers\lord_of_the_turn.py tests\server\test_server_lord_of_the_turn_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_lord_of_the_turn_routes.py tests\unit\test_lord_of_the_turn.py -q
```

## 8. Completion Boundary

P12-11 is ready for implementation after this transport design.

Completion covers only direct caller-supplied SR chart profile transport. It
does not include Solar Return construction, house derivation, annual hierarchy
integration, dashboards, or interpretation.
