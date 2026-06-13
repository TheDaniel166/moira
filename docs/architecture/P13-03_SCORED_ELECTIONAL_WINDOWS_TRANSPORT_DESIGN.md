# P13-03 Scored Electional Windows Transport Design

Version: 0.1
Date: 2026-06-13
Status: transport_design_complete
Scope: bounded scored electional-window REST admission plan

## 1. Admission Boundary

P13-03 admits a transport design for bounded scored electional-window searches
over the existing `moira.electional` engine.

Candidate routes:

- `GET /v1/electional/scorer-profiles`
- `POST /v1/electional/scored`

The compute route exposes `find_scored_windows` through:

- the P13-01/P13-02 server-defined predicate catalogue
- a new server-defined scorer catalogue

The route does not expose arbitrary Python predicates, arbitrary Python
scorers, arbitrary expressions, arbitrary weighted rule stacks, Western
electional judgement, electional advice, recommendation language, or
auspicious/inauspicious labels.

This design does not admit:

- caller-owned executable scorers
- free-form scoring formula strings
- dignity/reception/sect scoring
- benefic/malefic scoring
- planetary-hour scoring
- mansion scoring
- house-ruler scoring
- void-of-course scoring
- public "best election" ranking
- Western electional doctrine
- Vedic `muhurta` comparison
- async search jobs
- unbounded date-range scans
- exact score-peak claims

## 2. Governing Object

The governing object is a scan-derived `ElectionalScoredWindow`:

- `window`
- `score`
- `peak_jd`

The contained `window` remains a P13-01 merged scan witness. The `score` is a
finite numeric fit to a declared scorer profile. The `peak_jd` is the
highest-scored qualifying scan point inside that returned window.

The route must not imply:

- exact score maxima between scan points
- continuous score truth between scan points
- a recommended electional time
- Moira-owned Western electional judgement

## 3. Predicate Model

P13-03 reuses the admitted P13-01 predicate profiles:

- `body_longitude_range_v1`
- `body_house_membership_v1`
- `body_angular_separation_range_v1`

Predicate semantics, subject admission, body-subset policy, tropical/sidereal
policy, and house-membership restrictions remain unchanged.

The scorer is applied only at scan points where the predicate returns true.

## 4. Scorer Model

The request supplies:

- `scorer_profile`
- `scorer_parameters`

The server binds that pair to a known scorer function. No user-supplied code,
expression, formula string, or arbitrary weighting table is accepted.

All Stage 1 scorer profiles return finite scores in `[0.0, 1.0]`.

Score direction:

- higher score is a closer numeric fit to the declared scorer profile
- higher score is not public electional judgement
- higher score is not advice or recommendation language

### 4.1 Admitted Scorer Profiles

`body_longitude_target_closeness_v1`

- Purpose: score how close one subject's longitude is to a caller-supplied
  target longitude.
- Required parameters:
  - `subject`: admitted body name
  - `target_longitude`: finite degrees, normalized by transport to `[0, 360)`
  - `max_orb`: finite degrees in `(0, 180]`
- Computation:
  - compute shortest zodiacal distance between subject longitude and target
  - `score = max(0, 1 - distance / max_orb)`
- Score scale:
  - `1.0` at exact target
  - linearly decreases to `0.0` at `max_orb`
  - never negative
- Doctrine status:
  - numeric zodiacal closeness only
  - not electional judgement

`body_angular_separation_target_closeness_v1`

- Purpose: score how close the shortest angular separation between two
  subjects is to a caller-supplied target angle.
- Required parameters:
  - `subject_a`: admitted body name
  - `subject_b`: admitted body name
  - `target_angle`: finite degrees in `[0, 180]`
  - `max_orb`: finite degrees in `(0, 180]`
- Validation:
  - `subject_a != subject_b`
- Computation:
  - compute shortest angular separation between `subject_a` and `subject_b`
  - compute absolute distance from `target_angle`
  - `score = max(0, 1 - distance / max_orb)`
- Score scale:
  - `1.0` at exact target angle
  - linearly decreases to `0.0` at `max_orb`
  - never negative
- Doctrine status:
  - numeric angular closeness only
  - not aspect doctrine
  - not electional judgement

### 4.2 Deferred Scorer Models

Deferred:

- arbitrary JSON expression trees
- weighted composite rule profiles
- dignity, reception, sect, or planetary-condition scoring
- benefic/malefic scoring
- planetary-hour scoring
- mansion scoring
- void-of-course scoring
- house-ruler scoring
- text-described scorers
- scorer profiles that produce public advice labels

Those can be admitted only through later standards or doctrine packets.

## 5. Request Shape

`GET /v1/electional/scorer-profiles`

No request body.

Response lists:

- scorer profile identifiers
- version
- description
- required parameters
- required chart fields
- supported frames
- score scale
- score direction
- doctrine status
- non-goals
- route bounds

`POST /v1/electional/scored`

Required fields:

- `jd_start`: finite Julian Day UT
- `jd_end`: finite Julian Day UT, strictly greater than `jd_start`
- `latitude`: finite degrees in `[-90, 90]`
- `longitude`: finite degrees in `[-180, 180]`
- `predicate_profile`: one admitted predicate profile identifier
- `predicate_parameters`: object matching that predicate profile
- `scorer_profile`: one admitted scorer profile identifier
- `scorer_parameters`: object matching that scorer profile

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
- `include_score_rank`: boolean, default `true`

## 6. Bounds

Stage 1 route bounds:

- maximum search span: `31` days
- minimum `step_days`: `1 / 96` day, 15 minutes
- maximum `step_days`: `1` day
- maximum computed scan points: `1000`
- maximum returned scored windows: `64`
- maximum `boundary_refine_steps`: `8`
- maximum body subset count: `12`
- score range: `[0.0, 1.0]`
- maximum returned qualifying JDs per response: bounded by maximum computed
  scan points

The transport layer must compute:

```text
scan_point_count = floor((jd_end - jd_start) / step_days) + 1
```

and reject any request where `scan_point_count > 1000`.

If `max_windows` is supplied, it must be in `[1, 64]`. If omitted, the
effective value is `64`.

Important ordering truth:

- engine `max_windows` early-exit is chronological
- score ranks are therefore over the returned scored windows
- score ranks are not a global proof that no later omitted window would score
  higher

The response and provenance must state this.

## 7. Subject And Body Policy

Stage 1 admitted subjects remain:

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

The effective `bodies` list must include every subject required by both the
predicate profile and the scorer profile. If the caller supplies
`policy.bodies`, the route must reject missing required subjects rather than
silently expand the list.

Node and asteroid predicates/scorers are deferred.

## 8. Frame And House Policy

Tropical evaluation:

- predicate and scorer receive the chart payload from `moira.electional`
- longitudes are tropical chart longitudes

Sidereal evaluation:

- predicate and scorer receive `ElectionalEvaluation`
- longitudes are sidereal-adjusted by the selected ayanamsa policy
- the original chart remains unchanged

House-dependent predicates:

- remain tropical-only in Stage 1
- use the requested `house_system`
- must report requested and effective house-system truth when available

Stage 1 scorer profiles are longitude/separation scorers and support tropical
or sidereal evaluation. No house-dependent scorer profile is admitted.

## 9. Response Shape

`GET /v1/electional/scorer-profiles`

Response:

- `profiles`
- `bounds`
- `provenance`

`POST /v1/electional/scored`

Response:

- `predicate`
- `scorer`
- `policy`
- `scan`
- `scored_windows`
- `score_summary`
- `bounds`
- `validation`
- `provenance`

`predicate` preserves:

- `profile_id`
- `profile_version`
- `parameters`
- `owner`: `server_defined`
- `doctrine_status`: `scan_predicate_not_electional_judgement`

`scorer` preserves:

- `profile_id`
- `profile_version`
- `parameters`
- `owner`: `server_defined`
- `score_scale`: `[0.0, 1.0]`
- `score_direction`: `higher_is_closer_numeric_fit`
- `doctrine_status`: `numeric_fit_not_electional_judgement`

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
- `max_windows_semantics`: `chronological_early_exit`

`scan` preserves:

- `jd_start`
- `jd_end`
- `span_days`
- `scan_point_count`
- `discrete_scan`: `true`
- `continuous_truth_claimed`: `false`
- `exact_boundary_claimed`: `false`
- `exact_peak_claimed`: `false`

Each scored window preserves:

- `jd_start`
- `jd_end`
- `duration_hours`
- `qualifying_count`
- `qualifying_jds`, when requested
- `entry_bracket`, when present and requested
- `exit_bracket`, when present and requested
- `window_kind`: `merged_scan_witness`
- `score`
- `peak_jd`
- `score_rank`, when requested
- `peak_kind`: `highest_scored_qualifying_scan_point`

`score_summary` preserves:

- `count`
- `highest_score`
- `lowest_score`
- `score_rank_basis`: `score_desc_peak_jd_asc_window_start_asc`
- `rank_scope`: `returned_windows_only`
- `global_best_claimed`: `false`

If there are no matches:

- `scored_windows`: `[]`
- `score_summary.count`: `0`
- `highest_score`: `null`
- `lowest_score`: `null`

`validation` preserves:

- `included`
- `passed`
- `failures`

There is no doctrine validation for electional judgement in this route.

## 10. Ranking Semantics

Engine output is chronological. Transport may add `score_rank` values without
reordering `scored_windows`.

Rank ordering:

1. score descending
2. `peak_jd` ascending
3. `window.jd_start` ascending

Rank scope:

- returned windows only
- according to the named scorer profile
- using discrete qualifying scan-point scores

Transport must not describe rank `1` as:

- best
- recommended
- selected
- auspicious
- ideal

## 11. Provenance Requirements

Every scored response must state:

- `source_module`: `moira.electional`
- `engine_entrypoint`: `find_scored_windows`
- `predicate_owner`: `server_defined`
- `predicate_profile`
- `predicate_profile_version`
- `scorer_owner`: `server_defined`
- `scorer_profile`
- `scorer_profile_version`
- `chart_construction_owner`: `moira.chart.create_chart`
- `reader_owner`
- `scan_semantics`: `discrete_sampled_chart_states`
- `window_semantics`: `merged_qualifying_scan_points`
- `boundary_semantics`: `optional_true_false_brackets_not_exact_roots`
- `score_semantics`: `numeric_fit_to_declared_scorer_profile`
- `score_scale`: `[0.0, 1.0]`
- `score_direction`: `higher_is_closer_numeric_fit`
- `score_rank_semantics`: `returned_windows_only`
- `peak_semantics`: `highest_scored_qualifying_scan_point`
- `exact_peak_claimed`: `false`
- `score_peak_refinement`: `not_applied`
- `max_windows_semantics`: `chronological_early_exit`
- `western_electional_doctrine`: `not_admitted`
- `advice_language`: `not_provided`
- `recommendation_language`: `not_provided`
- `scoring_doctrine`: `transport_numeric_fit_not_western_judgement`
- `stage_sequence`

Stage sequence:

- `input_validation`
- `predicate_profile_binding`
- `scorer_profile_binding`
- `search_policy_binding`
- `chart_scan`
- `predicate_evaluation`
- `scorer_evaluation`
- `window_merge`
- `score_peak_selection`
- `score_rank_assignment`
- `boundary_refinement` when enabled
- `response_serialization`

## 12. Error Semantics

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
- unknown scorer profile
- malformed scorer parameters
- unsupported subject names
- duplicate body names
- unsupported body names
- body subset count over `12`
- missing predicate-required or scorer-required subjects in explicit body
  subsets
- invalid house-system code
- invalid zodiac frame
- invalid ayanamsa system or mode
- zero, negative, non-finite, too-small, or too-large `step_days`
- negative or non-finite `merge_gap_days`
- invalid `max_windows`
- invalid `boundary_refine_steps`
- `boundary_refine_steps > 0` when boundary brackets are disabled
- non-boolean output controls
- non-finite scorer output
- scorer output outside `[0.0, 1.0]`

These should surface through the standard `422` validation envelope.

## 13. Verification Requirements For Admission

Server tests must cover:

- scorer profile catalogue route
- route registration
- successful longitude target closeness scored search
- successful angular separation target closeness scored search
- predicate/scorer subject union in effective body requirements
- empty-result response
- requested/effective policy echo
- provenance fields and stage sequence
- discrete-scan and exact-peak flags
- score scale and direction
- score-rank tie ordering
- chronological response order preserved
- rank scope documented as returned windows only
- inclusion and omission of qualifying JDs
- boundary-refinement bracket behavior
- invalid/reversed/equal JD windows
- oversized span
- scan-count overflow
- invalid latitude and longitude
- invalid predicate profile
- invalid scorer profile
- malformed predicate parameters
- malformed scorer parameters
- unsupported subjects
- missing required subjects from explicit body subsets
- invalid `step_days`, `merge_gap_days`, `max_windows`,
  `boundary_refine_steps`
- invalid frame, ayanamsa, and house-system values
- validation-envelope shape

Engine-focused hardening should cover, if not already covered:

- finite-score rejection in `ElectionalScoredWindow`
- `peak_jd` must be one of the scored window's qualifying JDs
- `find_scored_windows` chronological order
- `max_windows` early exit semantics
- boundary refinement preserving score peak scan-point truth

## 14. Documentation Updates Required On Implementation

When implemented:

- update `wiki/02_services/REST_API_REFERENCE.md` route counts
- update the electional route family count from `3` to `5`
- add `GET /v1/electional/scorer-profiles`
- add `POST /v1/electional/scored`
- update the Phase 13 deferred REST-reference line to remove scored routes
  only
- extend the Electional Search REST admission boundary with scored-window
  semantics
- update `docs/architecture/MOIRA_SERVER_PHASE13_LEDGER.md` to `admitted`
  for P13-03 only

Do not mark P13-U1 Western Electional Doctrine admitted.

## 15. Non-Goals

P13-03 transport does not:

- implement routes by itself
- expose arbitrary predicates
- expose arbitrary scorers
- create Western electional doctrine
- produce recommendations
- call any result auspicious or inauspicious
- call any result best
- claim exact score peaks
- change chart construction
- change house calculation
- change sidereal reduction
- change kernel/resource binding
- create async job infrastructure

## 16. Implementation Readiness

After this design is accepted, P13-03 may proceed to implementation with:

- `GET /v1/electional/scorer-profiles`
- `POST /v1/electional/scored`

Implementation must remain transport-only around `moira.electional` and must
not admit arbitrary scorers, Western electional doctrine, or advice language.
