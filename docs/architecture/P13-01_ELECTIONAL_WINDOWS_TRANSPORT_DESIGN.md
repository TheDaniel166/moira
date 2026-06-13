# P13-01 Electional Windows Transport Design

Version: 0.1
Date: 2026-06-13
Status: transport_design_complete
Scope: bounded electional window REST admission plan

## 1. Admission Boundary

P13-01 admits a Stage 1 transport design for bounded electional window
searches over the existing `moira.electional` engine.

Candidate routes:

- `GET /v1/electional/predicate-profiles`
- `POST /v1/electional/windows`

The compute route exposes `find_electional_windows` through a route-safe,
server-defined predicate catalogue. It does not expose arbitrary Python
predicates, arbitrary expressions, arbitrary scorers, Western electional
judgement, electional advice, or recommendation language.

This design does not admit:

- `/v1/electional/moments`
- `/v1/electional/scored`
- arbitrary executable predicates over HTTP
- arbitrary executable scorers over HTTP
- structured free-form rule grammars
- Western electional doctrine
- "best time", "auspicious", or "inauspicious" labels
- async search jobs
- unbounded date-range scans
- exact event-boundary claims

## 2. Governing Object

The governing object is a scan-derived `ElectionalWindow`:

- `jd_start`
- `jd_end`
- `duration_hours`
- ordered `qualifying_jds`
- optional `entry_bracket`
- optional `exit_bracket`

An electional window is a merged witness of sampled chart states where the
admitted predicate returned true. It is not proof of continuous truth between
scan points, and it is not an exact electional event boundary.

## 3. Predicate Model

Stage 1 chooses a small fixed predicate catalogue.

The request supplies:

- `predicate_profile`
- `predicate_parameters`

The server binds that pair to a known predicate function. No user-supplied code
or expression is accepted.

### 3.1 Admitted Predicate Profiles

`body_longitude_range_v1`

- Purpose: match scan points where one subject longitude lies within a
  caller-supplied zodiacal arc.
- Required parameters:
  - `subject`: admitted body name
  - `start_longitude`: finite degrees
  - `end_longitude`: finite degrees
- Wrap policy:
  - if `start_longitude <= end_longitude`, match the closed interval
    `[start_longitude, end_longitude]`
  - if `start_longitude > end_longitude`, match the wrapped interval through
    `0 Aries`
- Doctrine status:
  - geometric/numeric predicate only
  - no electional judgement

`body_house_membership_v1`

- Purpose: match scan points where one subject occupies one of the requested
  houses in the selected house frame.
- Required parameters:
  - `subject`: admitted body name
  - `houses`: one or more integers in `[1, 12]`
- Computation:
  - use `moira.houses.house_of(subject_longitude, chart.houses)`
- Doctrine status:
  - house-position predicate only
  - no condition, dignity, strength, or electional judgement

`body_angular_separation_range_v1`

- Purpose: match scan points where the absolute shortest angular separation
  between two subjects falls within a caller-supplied range.
- Required parameters:
  - `subject_a`: admitted body name
  - `subject_b`: admitted body name
  - `min_angle`: finite degrees in `[0, 180]`
  - `max_angle`: finite degrees in `[0, 180]`
- Validation:
  - `min_angle <= max_angle`
  - `subject_a != subject_b`
- Doctrine status:
  - numeric separation predicate only
  - not an aspect doctrine or electional aspect judgement

### 3.2 Deferred Predicate Models

Deferred:

- arbitrary JSON expression trees
- nested boolean predicate grammars
- dignity, reception, sect, condition, or malefic/benefic predicates
- void-of-course, planetary-hour, or mansion electional predicates
- house-ruler predicates
- scoring predicates
- text-described predicates

Those can be admitted only through later standards or doctrine packets.

## 4. Request Shape

`GET /v1/electional/predicate-profiles`

No request body.

Response lists:

- predicate profile identifiers
- version
- description
- required parameters
- required chart fields
- supported frames
- doctrine status
- non-goals
- route bounds

`POST /v1/electional/windows`

Required fields:

- `jd_start`: finite Julian Day UT
- `jd_end`: finite Julian Day UT, strictly greater than `jd_start`
- `latitude`: finite degrees in `[-90, 90]`
- `longitude`: finite degrees in `[-180, 180]`
- `predicate_profile`: one admitted profile identifier
- `predicate_parameters`: object matching that profile

Optional `policy` fields:

- `step_days`: finite days, default `1 / 24`
- `merge_gap_days`: finite non-negative days or `null`, default `null`
- `house_system`: admitted house-system code, default `Placidus`
- `bodies`: optional list of admitted body names
- `zodiac_frame`: `tropical` or `sidereal`, default `tropical`
- `ayanamsa_system`: default `lahiri`
- `ayanamsa_mode`: `true` or `mean`, default `true`
- `boundary_refine_steps`: integer, default `0`
- `max_windows`: integer, default route maximum

Optional output controls:

- `include_qualifying_jds`: boolean, default `true`
- `include_boundary_brackets`: boolean, default `true`

## 5. Bounds

Stage 1 route bounds:

- maximum search span: `31` days
- minimum `step_days`: `1 / 96` day, 15 minutes
- maximum `step_days`: `1` day
- maximum computed scan points: `1000`
- maximum returned windows: `64`
- maximum `boundary_refine_steps`: `8`
- maximum body subset count: `12`
- maximum returned qualifying JDs per response: bounded by maximum computed
  scan points

The transport layer must compute:

```text
scan_point_count = floor((jd_end - jd_start) / step_days) + 1
```

and reject any request where `scan_point_count > 1000`.

If `max_windows` is supplied, it must be in `[1, 64]`. If omitted, the
effective value is `64`.

`boundary_refine_steps > 0` is allowed only when
`include_boundary_brackets == true`.

## 6. Subject And Body Policy

Stage 1 admitted subjects:

- `Sun`
- `Moon`
- `Mercury`
- `Venus`
- `Mars`
- `Jupiter`
- `Saturn`
- `Uranus`
- `Neptune`
- `Pluto`

Node and asteroid predicates are deferred.

The effective `bodies` list must include every subject required by the
predicate profile. If the caller supplies `policy.bodies`, the route must
either:

- add the predicate-required subjects to the effective body list and report
  that addition in provenance, or
- reject the request as missing required subjects

Stage 1 should prefer rejection rather than silent expansion.

## 7. Frame And House Policy

Tropical evaluation:

- predicate receives the chart payload from `moira.electional`
- longitudes are tropical chart longitudes

Sidereal evaluation:

- predicate receives `ElectionalEvaluation`
- longitudes are sidereal-adjusted by the selected ayanamsa policy
- the original chart remains unchanged

House-dependent predicates:

- require a chart with houses
- use the requested `house_system`
- must report requested and effective house-system truth in provenance when
  available from the chart/houses layer

This route does not alter house calculation policy or high-latitude fallback
behavior.

## 8. Response Shape

`GET /v1/electional/predicate-profiles`

Response:

- `profiles`
- `bounds`
- `provenance`

`POST /v1/electional/windows`

Response:

- `predicate`
- `policy`
- `scan`
- `windows`
- `bounds`
- `validation`
- `provenance`

`predicate` preserves:

- `profile_id`
- `profile_version`
- `parameters`
- `owner`: `server_defined`
- `doctrine_status`: `scan_predicate_not_electional_judgement`

`policy` preserves:

- requested and effective `step_days`
- requested and effective `merge_gap_days`
- requested and effective `house_system`
- requested and effective `bodies`
- requested and effective `zodiac_frame`
- requested and effective `ayanamsa_system`
- requested and effective `ayanamsa_mode`
- requested and effective `boundary_refine_steps`
- requested and effective `max_windows`

`scan` preserves:

- `jd_start`
- `jd_end`
- `span_days`
- `scan_point_count`
- `discrete_scan`: `true`
- `continuous_truth_claimed`: `false`
- `exact_boundary_claimed`: `false`

Each window preserves:

- `jd_start`
- `jd_end`
- `duration_hours`
- `qualifying_count`
- `qualifying_jds`, when requested
- `entry_bracket`, when present and requested
- `exit_bracket`, when present and requested
- `window_kind`: `merged_scan_witness`

`validation` preserves:

- `included`
- `passed`
- `failures`

The first implementation may set validation to transport/structural
validation only. There is no doctrine validation for electional judgement in
this route.

## 9. Provenance Requirements

Every response must state:

- `source_module`: `moira.electional`
- `engine_entrypoint`: `find_electional_windows`
- `predicate_owner`: `server_defined`
- `predicate_profile`
- `predicate_profile_version`
- `chart_construction_owner`: `moira.chart.create_chart`
- `reader_owner`
- `scan_semantics`: `discrete_sampled_chart_states`
- `window_semantics`: `merged_qualifying_scan_points`
- `boundary_semantics`: `optional_true_false_brackets_not_exact_roots`
- `western_electional_doctrine`: `not_admitted`
- `advice_language`: `not_provided`
- `scoring`: `not_admitted`
- `moments_route`: `not_admitted_for_p13_01`
- `stage_sequence`

Stage sequence:

- `input_validation`
- `predicate_profile_binding`
- `search_policy_binding`
- `chart_scan`
- `predicate_evaluation`
- `window_merge`
- `boundary_refinement` when enabled
- `response_serialization`

## 10. Error Semantics

The route must reject:

- non-finite `jd_start` or `jd_end`
- `jd_end <= jd_start`
- span over `31` days
- scan count over `1000`
- non-finite `latitude` or `longitude`
- latitude outside `[-90, 90]`
- longitude outside `[-180, 180]`
- unknown predicate profile
- malformed predicate parameters
- unsupported subject names
- duplicate body names
- unsupported body names
- body subset count over `12`
- missing predicate-required subjects in explicit body subsets
- invalid house-system code
- invalid zodiac frame
- invalid ayanamsa system or mode
- zero, negative, non-finite, too-small, or too-large `step_days`
- negative or non-finite `merge_gap_days`
- invalid `max_windows`
- invalid `boundary_refine_steps`
- `boundary_refine_steps > 0` when boundary brackets are disabled

These should surface through the standard `422` validation envelope.

## 11. Verification Requirements For Admission

Server tests must cover:

- predicate profile catalogue route
- route registration
- successful longitude-range window search
- successful house-membership window search
- successful angular-separation range window search
- empty-result response
- requested/effective policy echo
- provenance fields and stage sequence
- discrete-scan flags
- inclusion and omission of qualifying JDs
- boundary-refinement bracket behavior
- invalid/reversed/equal JD windows
- oversized span
- scan-count overflow
- invalid latitude and longitude
- invalid predicate profile
- malformed predicate parameters
- unsupported subjects
- missing required subjects from explicit body subsets
- invalid `step_days`, `merge_gap_days`, `max_windows`,
  `boundary_refine_steps`
- invalid frame, ayanamsa, and house-system values
- validation-envelope shape

Engine-focused hardening should cover, if not already covered:

- `max_windows` early exit
- `boundary_refine_steps` entry and exit brackets
- invalid policy fields
- equality-range rejection

## 12. Documentation Updates Required On Implementation

When implemented:

- update `wiki/02_services/REST_API_REFERENCE.md` route counts
- add `electional` route family count
- add `GET /v1/electional/predicate-profiles`
- add `POST /v1/electional/windows`
- replace the Phase 13 deferred REST-reference line only for the admitted
  windows subset
- update `docs/architecture/MOIRA_SERVER_PHASE13_LEDGER.md` to `admitted`
  for P13-01 only

Do not mark P13-02, P13-03, or P13-U1 admitted.

## 13. Non-Goals

P13-01 transport does not:

- implement routes by itself
- expose raw moments
- expose scored windows
- expose arbitrary predicates
- expose arbitrary scorers
- create Western electional doctrine
- produce recommendations
- rank windows
- call any result auspicious or inauspicious
- change chart construction
- change house calculation
- change sidereal reduction
- change kernel/resource binding
- create async job infrastructure

## 14. Implementation Readiness

After this design is accepted, P13-01 may proceed to implementation with the
bounded Stage 1 predicate catalogue described here.

Implementation must remain transport-only around `moira.electional`; any
change to the electional engine itself should be limited to test-driven
hardening for already-existing policy and result-vessel behavior.
