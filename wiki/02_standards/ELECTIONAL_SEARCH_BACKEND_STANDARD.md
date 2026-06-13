# Electional Search Backend Standard

Version: 0.1
Date: 2026-06-13
Status: backend standard for Phase 13 REST evaluation

## Scope

This standard governs the generic electional-search engine surface:

- `moira.electional`

It covers:

- discrete Julian-Day electional scans
- merged qualifying windows
- raw qualifying scan-point moments
- scored qualifying windows as a caller-owned scoring mechanism
- explicit search policy
- tropical and sidereal evaluation views
- boundary-refinement brackets as scan-adjacent witness data

It does not govern:

- Western electional doctrine
- built-in electional rule profiles
- electional advice or recommendation text
- auspicious/inauspicious judgement language
- Vedic `muhurta`
- chart construction doctrine
- house-system doctrine
- kernel lifecycle policy
- arbitrary executable predicates or scorers over REST

## Authority And Provenance

The electional-search backend is infrastructure. Its authority is the live
Moira chart construction and astronomical substrate used at each sampled
Julian Day.

The backend delegates:

- chart construction to `moira.chart.create_chart`
- SPK reader acquisition to `moira.spk_reader`
- house-system calculation to the chart construction layer
- tropical-to-sidereal reduction to `moira.sidereal`
- datetime/JD conversion, where needed by facade helpers, to `moira.julian`

The backend owns:

- search cadence policy
- merge-gap policy
- optional boundary-refinement brackets
- optional maximum-window early exit
- payload selection for tropical chart predicates versus sidereal evaluation
  predicates
- the immutable result vessels used to preserve scan witness truth

This standard does not convert the generic predicate engine into a Western
electional doctrine subsystem. The Western audit records that such a doctrine
layer is still missing.

## Governing Objects

### ElectionalPolicy

`ElectionalPolicy` is the frozen search-policy vessel. It preserves:

- `step_days`
- `merge_gap_days`
- `house_system`
- `bodies`
- `zodiac_frame`
- `ayanamsa_system`
- `ayanamsa_mode`
- `boundary_refine_steps`
- `max_windows`

Policy invariants:

- `step_days > 0`
- `merge_gap_days is None or merge_gap_days >= 0`
- `bodies is None or tuple[str, ...]`
- `zodiac_frame in {"tropical", "sidereal"}`
- `ayanamsa_mode in {"true", "mean"}`
- sidereal policy requires a non-empty `ayanamsa_system`
- `boundary_refine_steps >= 0`
- `max_windows is None or max_windows > 0`

For REST admission, these engine-level invariants are necessary but not
sufficient. Transport must add public bounds for search span, scan-point count,
cadence, body subset size, and returned result count.

### ElectionalEvaluation

`ElectionalEvaluation` is the explicit frame-aware predicate payload used when
policy requests sidereal evaluation. It preserves:

- original chart object
- `zodiac_frame`
- `ayanamsa_system`
- `ayanamsa_mode`
- `ayanamsa_value`
- sidereal-adjusted `planet_longitudes`
- sidereal-adjusted `node_longitudes`
- sidereal-adjusted `house_cusps`
- combined `longitudes`

The underlying chart remains the astronomical truth carrier. Sidereal
evaluation is a view over that chart; it must not mutate the chart.

### ElectionalWindow

`ElectionalWindow` is one merged span of qualifying scan points. It preserves:

- `jd_start`
- `jd_end`
- `duration_hours`
- ordered `qualifying_jds`
- optional `entry_bracket`
- optional `exit_bracket`

Window invariants:

- `jd_start <= jd_end`
- at least one qualifying JD exists
- first qualifying JD equals `jd_start`
- last qualifying JD equals `jd_end`
- `duration_hours == (jd_end - jd_start) * 24`

An electional window is a scan witness. It is not proof that the predicate held
continuously between sampled points unless the predicate and cadence doctrine
make that claim separately.

### ElectionalScoredWindow

`ElectionalScoredWindow` pairs an `ElectionalWindow` with:

- finite `score`
- `peak_jd`

Scored-window invariants:

- score is finite
- `peak_jd` is one of the window's qualifying JDs

The score is caller-owned in the engine. It is not Moira-owned Western
electional judgement unless a future doctrine packet admits a named scoring
profile.

## Admitted Engine Computations

The backend admits these Python computations:

- `find_electional_windows(jd_start, jd_end, latitude, longitude, predicate, policy=None, reader=None)`
- `find_electional_moments(jd_start, jd_end, latitude, longitude, predicate, policy=None, reader=None)`
- `find_scored_windows(jd_start, jd_end, latitude, longitude, predicate, scorer, policy=None, reader=None)`

These are Python engine surfaces. They are not automatically REST-admitted
because their governing predicate and scorer inputs are Python callables.

## REST Admission Boundary

REST admission may only expose route-safe predicate and scorer semantics.

Forbidden over REST:

- arbitrary executable predicates
- arbitrary executable scorers
- user-supplied Python code
- user-supplied expressions evaluated by the server
- unbounded date ranges
- unbounded scan-point counts
- unbounded result lists
- public claims of exact event boundaries from discrete scan witnesses
- public judgement language such as "best", "auspicious", "inauspicious",
  "advice", or "recommendation" unless a doctrine packet admits it

Allowed after transport design:

- server-defined predicate identifiers
- versioned server-defined predicate profiles
- explicit route policy vessels
- bounded scan ranges
- bounded cadence
- explicit requested/effective policy echo
- explicit provenance for predicate ownership, chart construction, reader
  ownership, and evaluation frame

## Required REST Bounds

Any Phase 13 transport design must define:

- maximum search span in days
- minimum `step_days`
- maximum `step_days`, if a cadence ceiling is needed for product truth
- maximum computed scan points
- maximum returned windows
- maximum returned raw moments
- maximum `boundary_refine_steps`
- maximum body subset count
- accepted body identifiers
- accepted house systems
- accepted zodiac frames
- accepted ayanamsa systems and modes
- latitude and longitude ranges

The transport layer must reject any request whose effective scan count exceeds
the admitted bound, even when each individual input field is otherwise valid.

## Discrete Scan Semantics

The electional engine samples chart states at discrete Julian Days:

```text
jd_start, jd_start + step_days, ..., jd_end
```

A qualifying moment means:

- the admitted predicate returned true at that sampled Julian Day

A qualifying window means:

- one or more adjacent qualifying scan points were merged under
  `effective_merge_gap`

Boundary refinement means:

- optional bisection brackets around a true/false transition adjacent to a
  sampled window boundary

Boundary refinement does not mean:

- exact root solving
- exact ingress/aspect/event solving
- continuous proof that the predicate held across the full interior of the
  window

REST responses must use language such as:

- qualifying scan point
- scan-derived window
- merged witness window
- boundary bracket

REST responses must avoid unqualified language such as:

- exact electional moment
- exact beginning
- exact ending
- best time

## Predicate Policy

The current engine accepts Python callables. REST cannot.

Before `/v1/electional/windows` or `/v1/electional/moments` may be admitted,
transport design must choose one of these safe predicate models:

1. No REST predicate admission yet.
2. A small fixed predicate catalogue with explicit names and versions.
3. A structured rule-profile grammar whose operators, operands, and
   thresholds are all admitted and bounded.

The first admitted transport should prefer a small fixed predicate catalogue
unless a structured grammar is separately designed and reviewed.

Each admitted predicate must define:

- identifier
- version
- required chart fields
- tropical or sidereal evaluation support
- required bodies
- house-system dependency, if any
- failure semantics when required data is absent
- public description that avoids interpretive judgement

## Scoring Policy

`find_scored_windows` exists, but REST scoring is not admitted by this
standard alone.

The P13-03 doctrine packet
`docs/architecture/P13-03_SCORED_ELECTIONAL_WINDOWS_DOCTRINE_PACKET.md`
decides that scored REST transport may proceed only as bounded scored search
infrastructure under server-defined numeric scorer profiles.

The packet rejects:

- arbitrary executable scorers over REST
- caller-owned score functions
- hidden or unversioned score weights
- Western electional judgement
- advice or recommendation language
- public "best", "auspicious", or "inauspicious" labels

`docs/architecture/P13-03_SCORED_ELECTIONAL_WINDOWS_TRANSPORT_DESIGN.md`
defines that public transport boundary, and the server admits only:

- `GET /v1/electional/scorer-profiles`
- `POST /v1/electional/scored`

The admitted scored route preserves:

- server-defined scorer catalogue
- finite `[0.0, 1.0]` score scale and
  `higher_is_closer_numeric_fit` direction
- score component provenance
- finite-score rejection
- score-rank semantics
- peak-JD scan-point truth
- how `max_windows` interacts with scoring and early exit

This admission does not create Western electional scoring doctrine. Scores are
numeric fit to the declared scorer profile. `peak_jd` is the highest-scored
qualifying scan point inside a returned window, not an exact peak or
recommendation timestamp. `score_rank` is scoped to returned windows only
because `max_windows` remains chronological early exit.

## Provenance Requirements

Every admitted REST response must state:

- source module: `moira.electional`
- engine entrypoint
- predicate owner
- predicate identifier and version, if server-defined
- scorer owner and scorer identifier, if scoring is ever admitted
- chart construction owner: `moira.chart.create_chart`
- reader owner
- requested and effective `step_days`
- requested and effective `merge_gap_days`
- requested and effective `max_windows`
- requested and effective `boundary_refine_steps`
- requested `house_system`
- requested body subset
- requested `zodiac_frame`
- requested `ayanamsa_system`
- requested `ayanamsa_mode`
- scan span
- computed scan-point count
- result count
- whether boundary brackets are present
- stage sequence

Stage sequence should include, at minimum:

- `input_validation`
- `predicate_profile_binding`
- `search_policy_binding`
- `chart_scan`
- `predicate_evaluation`
- `window_merge` for window routes
- `boundary_refinement` when enabled
- `response_serialization`

## Validation Requirements

Before REST admission, tests must cover:

- reversed and equal search ranges
- non-finite JDs
- invalid latitude and longitude
- zero, negative, non-finite, and too-small `step_days`
- negative `merge_gap_days`
- invalid house systems
- invalid zodiac frames
- invalid ayanamsa systems or modes
- empty, duplicate, unsupported, and oversized body subsets
- invalid predicate identifiers
- scan-count overflow
- result-count caps
- boundary-refinement caps
- empty-result behavior
- sorted temporal output
- validation-envelope behavior for Pydantic and service errors
- provenance content and stage sequence

Additional engine hardening should cover:

- `find_scored_windows`
- `ElectionalScoredWindow`
- `boundary_refine_steps`
- entry and exit brackets
- `max_windows` early exit
- policy invalid-field cases not already covered
- facade `Moira.electional_windows`

## Non-Goals

This standard does not:

- admit REST routes by itself
- create route models
- create a predicate catalogue
- create a scorer catalogue
- create Western electional doctrine
- define electional advice
- change chart construction
- change house calculation
- change sidereal reduction
- change kernel/resource binding
- expose async search jobs

## Admission Decision

P13-01 Electional Windows may proceed to transport design only after this
standard is accepted as the governing boundary.

P13-02 Electional Moments should share this standard and wait for the P13-01
predicate and bounds model.

P13-03 Scored Electional Windows has a completed scoring doctrine packet and
may proceed to transport design. It remains unadmitted as REST until that
design is implemented, registered, tested, and documented.
