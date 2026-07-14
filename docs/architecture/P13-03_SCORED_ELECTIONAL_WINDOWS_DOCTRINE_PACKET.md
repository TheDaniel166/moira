# P13-03 Scored Electional Windows Doctrine Packet

Version: 0.1
Date: 2026-06-13
Status: doctrine_packet_complete
Scope: public scoring doctrine for bounded electional search transport

## 1. Doctrine Decision

P13-03 may proceed to REST transport design only as bounded scored search
infrastructure.

The admitted concept is:

- a scan-derived electional window
- qualified by a server-defined predicate profile
- scored by a server-defined numeric scorer profile
- ranked or annotated only within the declared scorer's numeric meaning

The admitted concept is not:

- Western electional judgement
- an auspicious or inauspicious declaration
- advice language
- a recommendation engine
- a proof that one time is absolutely best
- a public route for arbitrary caller-owned scoring code

The engine's `find_scored_windows` accepts Python callables for both predicate
and scorer. REST must not expose that callable surface. REST may expose only
versioned, server-defined scorer profiles with explicit parameters, explicit
score scale, and explicit provenance.

## 2. Governing Object

The governing object remains `ElectionalScoredWindow`:

- `window`
- `score`
- `peak_jd`

The contained `window` remains the P13-01 scan-derived merged witness:

- it is produced from qualifying discrete scan points
- it is not proof of continuous truth between sampled points
- boundary brackets, when present, are transition witnesses, not exact roots

The added `score` is a finite numeric measurement attached to qualifying scan
points and summarized at the highest-scoring scan point inside the window.

The added `peak_jd` is the qualifying scan point within the window where that
score was highest. It is not an exact peak between scan points.

## 3. Score Ontology

The REST score ontology is numeric closeness or numeric fitness to a named
transport profile.

Allowed score language:

- `score`
- `score_profile`
- `score_scale`
- `score_direction`
- `peak_scan_point`
- `highest_scored_scan_point`
- `rank_by_declared_score`
- `numeric_fit`

Forbidden score language:

- `best time`
- `auspicious`
- `inauspicious`
- `favorable` unless it appears only as quoted engine docstring context and
  is rejected by the public transport
- `good election`
- `bad election`
- `recommendation`
- `advice`
- `judgement`
- `quality` unless qualified as the engine's caller-owned scalar convention
  and not exposed as public doctrine language

The public score must not be described as Moira's electional judgement. It is a
declared numeric ordering measure.

## 4. Scorer Ownership

REST scorer ownership must be `server_defined`.

Forbidden over REST:

- arbitrary executable scorer functions
- user-supplied Python code
- user-supplied expressions evaluated by the server
- unconstrained formula strings
- hidden weights
- unversioned score profiles
- caller-defined score direction

Allowed after transport design:

- scorer profile identifiers
- scorer profile versions
- bounded numeric parameters
- finite output scores
- explicit score scale and direction
- explicit score provenance

The first transport design should use a small fixed scorer catalogue, matching
the P13-01 predicate-catalogue strategy.

## 5. Admissible Stage 1 Scorer Families

Stage 1 may admit only transparent numeric scorer profiles.

Recommended first scorer families:

`body_longitude_target_closeness_v1`

- Scores how close one subject's longitude is to a caller-supplied target
  longitude.
- Required parameters:
  - `subject`
  - `target_longitude`
  - `max_orb`
- Score scale:
  - `1.0` at exact target
  - linearly decreases to `0.0` at `max_orb`
  - never negative
- Doctrine status:
  - numeric zodiacal closeness only
  - not electional judgement

`body_angular_separation_target_closeness_v1`

- Scores how close the shortest angular separation between two subjects is to
  a caller-supplied target angle.
- Required parameters:
  - `subject_a`
  - `subject_b`
  - `target_angle`
  - `max_orb`
- Score scale:
  - `1.0` at exact target angle
  - linearly decreases to `0.0` at `max_orb`
  - never negative
- Doctrine status:
  - numeric angular closeness only
  - not aspect doctrine
  - not electional judgement

These profiles are intentionally geometric and scalar. They do not combine
benefic/malefic doctrine, dignity, reception, sect, planetary hours, mansions,
or house-ruler condition.

## 6. Deferred Scorer Families

Deferred until separate doctrine:

- dignity scoring
- reception scoring
- sect scoring
- benefic/malefic scoring
- planetary-hour scoring
- mansion scoring
- house-ruler scoring
- void-of-course scoring
- rule-stack or weighted-composite scoring
- public "best election" ranking
- Western electional profile scoring
- Vedic `muhurta` comparison

These are not transport problems. They require doctrine ownership before any
public route can name them.

## 7. Ranking Semantics

The engine returns scored windows in chronological order.

Transport may expose:

- chronological window order
- `score_rank` values derived from score descending
- optional separate ranked view if the transport design admits it

Transport must not expose:

- `best`
- `recommended`
- `selected`
- `ideal`
- `auspicious`

If ranks are exposed, the rank must mean only:

- rank within this response
- according to this named scorer profile
- using discrete qualifying scan-point scores

Ties must be deterministic. Recommended tie order:

1. higher score
2. earlier `peak_jd`
3. earlier `window.jd_start`

## 8. Peak Truth

`peak_jd` is the highest-scored qualifying scan point inside a returned
window.

It is not:

- an exact mathematical maximum
- an interpolated maximum
- a refined root
- a recommendation timestamp

Transport provenance must use language such as:

- `peak_semantics: highest_scored_qualifying_scan_point`
- `exact_peak_claimed: false`

## 9. Boundary Policy

P13-03 may reuse P13-01 window boundary refinement, but it must keep score
truth separate from boundary truth.

Boundary refinement:

- refines true/false predicate transition brackets
- does not refine score maxima
- does not change `peak_jd`
- does not prove exact score-peak timing

If boundary brackets are included, provenance must state:

- `boundary_semantics: optional_true_false_brackets_not_exact_roots`
- `score_peak_refinement: not_applied`

## 10. Bounds

P13-03 transport design should inherit P13-01 public bounds unless it proves a
stricter bound is required:

- maximum search span: `31` days
- minimum `step_days`: `1 / 96` day, 15 minutes
- maximum `step_days`: `1` day
- maximum computed scan points: `1000`
- maximum returned scored windows: `64`
- maximum `boundary_refine_steps`: `8`
- maximum body subset count: `12`

Each scorer profile must also define:

- accepted subjects
- finite numeric parameter ranges
- finite score output guarantee
- score range
- score direction

## 11. Response Provenance Requirements

Every scored response must state:

- `source_module`: `moira.electional`
- `engine_entrypoint`: `find_scored_windows`
- `predicate_owner`: `server_defined`
- `predicate_profile`
- `predicate_profile_version`
- `scorer_owner`: `server_defined`
- `scorer_profile`
- `scorer_profile_version`
- `score_scale`
- `score_direction`
- `score_semantics`
- `peak_semantics`: `highest_scored_qualifying_scan_point`
- `exact_peak_claimed`: `false`
- `chart_construction_owner`: `moira.chart.create_chart`
- `reader_owner`
- `scan_semantics`: `discrete_sampled_chart_states`
- `window_semantics`: `merged_qualifying_scan_points`
- `western_electional_doctrine`: `not_admitted`
- `advice_language`: `not_provided`
- `recommendation_language`: `not_provided`
- `stage_sequence`

Required stage sequence:

- `input_validation`
- `predicate_profile_binding`
- `scorer_profile_binding`
- `search_policy_binding`
- `chart_scan`
- `predicate_evaluation`
- `scorer_evaluation`
- `window_merge`
- `score_peak_selection`
- `boundary_refinement` when enabled
- `response_serialization`

## 12. Transport Design Readiness

P13-03 may proceed to REST transport design under this packet if the design:

- uses server-defined predicate profiles
- uses server-defined scorer profiles
- rejects arbitrary executable scorers
- exposes score as numeric fit only
- preserves chronological and optional score-rank semantics explicitly
- preserves peak-JD scan-point truth
- avoids recommendation and auspiciousness language
- keeps its numeric-fit scorer separate from any admitted Western profile;
  Ramesey v1 single-moment evaluation supplies no score

## 13. Non-Goals

This doctrine packet does not:

- admit `/v1/electional/scored` by itself
- implement route models
- implement a scorer catalogue
- create Western electional doctrine
- define electional advice
- rank times as best or auspicious
- change chart construction
- change house calculation
- change sidereal reduction
- change kernel/resource binding
- create async job infrastructure

## 14. Ledger Decision

P13-03 should move from `admit_after_doctrine_packet` to
`admit_after_transport_design`.

The next step is a transport design for `/v1/electional/scored` that implements
this packet's scorer-ownership, score-semantics, ranking, bounds, and
provenance requirements.
