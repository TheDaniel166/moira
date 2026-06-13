# P13-02 Electional Moments Transport Design

Version: 0.1
Date: 2026-06-13
Status: transport_design_complete
Scope: bounded electional raw-moment REST admission plan

## 1. Admission Boundary

P13-02 admits a transport design for bounded raw electional scan-point
searches over the existing `moira.electional` engine.

Candidate route:

- `POST /v1/electional/moments`

The route exposes `find_electional_moments` through the same route-safe,
server-defined predicate catalogue admitted by P13-01. It does not expose
arbitrary Python predicates, arbitrary expressions, arbitrary scorers, Western
electional judgement, electional advice, recommendation language, or exact
event-boundary claims.

This design does not admit:

- `/v1/electional/scored`
- arbitrary executable predicates over HTTP
- arbitrary executable scorers over HTTP
- structured free-form rule grammars
- Western electional doctrine
- "best time", "auspicious", or "inauspicious" labels
- async search jobs
- unbounded date-range scans
- exact ingress, aspect, or boundary solving

## 2. Governing Object

The governing object is an ordered list of qualifying Julian Day scan points.

A qualifying moment is a sampled chart state where the admitted predicate
returned true. It is not:

- proof of continuous truth before or after the sampled instant
- an exact event root
- an exact beginning or ending of a condition
- an electional recommendation
- a ranked or scored electional choice

The route should name its result items as scan points, not exact moments, in
every response and documentation layer.

## 3. Relationship To P13-01

P13-02 inherits these P13-01 decisions:

- the predicate catalogue route remains `GET /v1/electional/predicate-profiles`
- the admitted predicate profiles remain:
  - `body_longitude_range_v1`
  - `body_house_membership_v1`
  - `body_angular_separation_range_v1`
- the subject list remains Sun through Pluto
- explicit `policy.bodies` must include predicate-required subjects
- tropical and sidereal frame policy remains unchanged
- house-membership predicates remain tropical-only
- no arbitrary executable predicates are admitted

P13-02 differs from P13-01 in one essential way:

- it returns raw qualifying scan-point JDs and skips the window-merge vessel

There is no boundary refinement for raw moments in Stage 1. Boundary brackets
belong to the window product, where true/false transitions around a merged
span can be witnessed.

## 4. Request Shape

`POST /v1/electional/moments`

Required fields:

- `jd_start`: finite Julian Day UT
- `jd_end`: finite Julian Day UT, strictly greater than `jd_start`
- `latitude`: finite degrees in `[-90, 90]`
- `longitude`: finite degrees in `[-180, 180]`
- `predicate_profile`: one admitted profile identifier
- `predicate_parameters`: object matching that profile

Optional `policy` fields:

- `step_days`: finite days, default `1 / 24`
- `merge_gap_days`: finite non-negative days or `null`, accepted for shared
  policy symmetry but not used by the raw-moment response
- `house_system`: admitted house-system code, default `Placidus`
- `bodies`: optional list of admitted body names
- `zodiac_frame`: `tropical` or `sidereal`, default `tropical`
- `ayanamsa_system`: default `lahiri`
- `ayanamsa_mode`: `true` or `mean`, default `true`
- `boundary_refine_steps`: must be `0` for moments
- `max_windows`: accepted only as inherited policy shape but ignored by the
  raw-moment route; the response should report it as not applicable

Optional output controls:

- `include_moments`: boolean, default `true`

When `include_moments` is false, the response returns counts and provenance
without the raw JD list. This allows clients to test predicate density without
receiving up to the full scan-point payload.

## 5. Bounds

Stage 1 route bounds:

- maximum search span: `31` days
- minimum `step_days`: `1 / 96` day, 15 minutes
- maximum `step_days`: `1` day
- maximum computed scan points: `1000`
- maximum returned raw moments: `1000`
- maximum body subset count: `12`
- `boundary_refine_steps`: exactly `0`

The transport layer must compute:

```text
scan_point_count = floor((jd_end - jd_start) / step_days) + 1
```

and reject any request where `scan_point_count > 1000`.

P13-02 does not need a separate truncation limit because the returned raw
moment count is bounded by the scan-point cap. The first implementation should
not silently truncate the raw moment list.

## 6. Response Shape

Response:

- `predicate`
- `policy`
- `scan`
- `moments`
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
- requested and effective `house_system`
- requested and effective `bodies`
- requested and effective `zodiac_frame`
- requested and effective `ayanamsa_system`
- requested and effective `ayanamsa_mode`
- `merge_gap_days_applicable`: `false`
- `boundary_refinement_applicable`: `false`
- `max_windows_applicable`: `false`

`scan` preserves:

- `jd_start`
- `jd_end`
- `span_days`
- `scan_point_count`
- `discrete_scan`: `true`
- `continuous_truth_claimed`: `false`
- `exact_boundary_claimed`: `false`

`moments` preserves:

- `count`
- `jds`, when requested
- `first_jd`
- `last_jd`
- `moment_kind`: `qualifying_scan_point`
- `sorted_temporally`: `true`

If there are no matches:

- `count`: `0`
- `jds`: `[]` when requested, otherwise `null`
- `first_jd`: `null`
- `last_jd`: `null`

`validation` preserves:

- `included`
- `passed`
- `failures`

The first implementation may set validation to transport/structural validation
only. There is no doctrine validation for electional judgement in this route.

## 7. Provenance Requirements

Every response must state:

- `source_module`: `moira.electional`
- `engine_entrypoint`: `find_electional_moments`
- `predicate_owner`: `server_defined`
- `predicate_profile`
- `predicate_profile_version`
- `chart_construction_owner`: `moira.chart.create_chart`
- `reader_owner`
- `scan_semantics`: `discrete_sampled_chart_states`
- `moment_semantics`: `raw_qualifying_scan_points`
- `window_merge`: `not_applied`
- `boundary_semantics`: `not_applicable_to_raw_moments`
- `western_electional_doctrine`: `not_admitted`
- `advice_language`: `not_provided`
- `scoring`: `not_admitted`
- `stage_sequence`

Stage sequence:

- `input_validation`
- `predicate_profile_binding`
- `search_policy_binding`
- `chart_scan`
- `predicate_evaluation`
- `raw_moment_collection`
- `response_serialization`

## 8. Error Semantics

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
- `boundary_refine_steps` other than `0`
- non-boolean `include_moments`

These should surface through the standard `422` validation envelope.

## 9. Verification Requirements For Admission

Server tests must cover:

- route registration
- successful longitude-range raw moment search
- successful house-membership raw moment search
- successful angular-separation raw moment search
- empty-result response
- requested/effective policy echo
- provenance fields and stage sequence
- discrete-scan flags
- inclusion and omission of raw moment JDs
- sorted temporal output
- invalid/reversed/equal JD windows
- oversized span
- scan-count overflow
- invalid latitude and longitude
- invalid predicate profile
- malformed predicate parameters
- unsupported subjects
- missing required subjects from explicit body subsets
- invalid `step_days`, `merge_gap_days`, and `boundary_refine_steps`
- invalid frame, ayanamsa, and house-system values
- validation-envelope shape

Engine-focused tests already cover `find_electional_moments`; route admission
should run those tests with the new server tests.

## 10. Documentation Updates Required On Implementation

When implemented:

- update `wiki/02_services/REST_API_REFERENCE.md` route counts
- update the electional route family count from `2` to `3`
- add `POST /v1/electional/moments`
- update the Phase 13 deferred REST-reference line to remove moments only
- add an Electional Moments REST admission boundary or extend the existing
  electional boundary with a separate moments subsection
- update `docs/architecture/MOIRA_SERVER_PHASE13_LEDGER.md` to `admitted`
  for P13-02 only

Do not mark P13-03 or P13-U1 admitted.

## 11. Non-Goals

P13-02 transport does not:

- implement routes by itself
- expose scored windows
- expose arbitrary predicates
- expose arbitrary scorers
- create Western electional doctrine
- produce recommendations
- rank scan points
- call any result auspicious or inauspicious
- claim exact root/event truth
- change chart construction
- change house calculation
- change sidereal reduction
- change kernel/resource binding
- create async job infrastructure

## 12. Implementation Readiness

After this design is accepted, P13-02 may proceed to implementation as a
transport-only extension of the P13-01 predicate catalogue and policy model.

The implementation should reuse the existing P13-01 predicate binding,
reader-selection, policy serialization, scan-count validation, and provenance
style wherever possible, while keeping raw moments semantically separate from
merged windows.
