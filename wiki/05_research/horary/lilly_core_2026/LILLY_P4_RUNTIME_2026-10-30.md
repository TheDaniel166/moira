# Lilly P4 perfection routes runtime

Date: 2026-10-30. Governing specification:
[P4 decisions](LILLY_P4_PERFECTION_DECISIONS_2026-10-30.md) and
[photograph collation](LILLY_P4_SOURCE_COLLATION_2026-10-30.md).

Status: **additive engine runtime implemented** in
[horary_perfection_routes.py](../../../../moira/horary_perfection_routes.py),
fixed profile `lilly_1647_perfection_routes_v1`. It is evidence for the named
rules: route records and blocker records, never a yes/no verdict, a
probability or a timing prediction (`verdict` is always `None`). The v1
classifier (`classical_perfection`, `lilly_1647_perfection_v1`), the P2/P3
evidence layers, native code, facade and REST are unchanged. The packet's
historical admission flags remain unchanged.

## Evaluators (typed evidence in, records out)

Each decision is one function. Every textual alternative is a required
argument with no default.

| Surface | Decision | Notes |
|---|---|---|
| `lilly_conjunction_route` | P01 | House-class qualifier only on completion; ingress reported as `ingress_recorded_not_blocking` (K05) |
| `lilly_sextile_trine_route` | P02, B05 | `LillyMalevolentReading`: `MALEFIC_PLANET` or `HARD_ASPECT` |
| `lilly_square_route` | P03 | Conditions are a gate ("otherwise not") |
| `lilly_opposition_route` | P04, Q02 | `desirability="regret_reported"` only on completion |
| `lilly_translation_route` | P05, P06 | `LillyTranslationReading`; P06 reception uses P2 bases (domicile, triplicity, term) |
| `lilly_collection_route` | P07, K02 | `LillyBeholdingReading`; leg order reported as the qualifier |
| `lilly_reception_route` | P08 | A route of its own; `never_overrides_another_route` |
| `lilly_dwelling_route` | P09 | Placement attributed `reported_rejected_by_lilly`; only the lunar-translation form completes |
| `lilly_prohibition` | B01, B02 | `LillyProhibitionReading`; a third planet separating from the applying principal is a `translator_candidate` |
| `lilly_refranation` | B03 | Needs an established application, not a later exact contact |
| `lilly_frustration` | B04 | Conjunction only |
| `lilly_heavier` | H01 | `LillyHeavinessReading`; `None` when unresolved |
| `lilly_route_summary` | K03, K04 | All route IDs and the earliest completions; ties kept together |
| `lilly_continuation` | K07 | A later window completes a route only with the carried frontier and complete coverage of both windows |
| `LillyEpochValues.at` | E01 | A value at one epoch is never transported to another |

All of them share one ordering (K01, K06): a missing leg is absent under complete
coverage and unresolved otherwise; an unmet condition comes next; a blocker
whose envelope ends before the leg's begins blocks; an overlap, an unknown
condition or partial coverage leaves the route unresolved; otherwise the route
is complete. A known condition must cite evidence IDs (Q01). Blockers carry
their own stated effects (`hindered_and_retarded`, `never_effected`,
`third_party_gains`).

The 149 fixtures of the
[P4 bundle](../../../../tests/fixtures/horary/lilly_p4_perfection_routes_2026_10_30.json)
run through these production evaluators in
`tests/unit/test_horary_perfection_routes.py`; every hand-written expectation
is reproduced.

## Trace and derivation

`trace_lilly_perfection` takes a normalized-longitude callable `(body, jd_ut1)`,
an explicit provenance record, a dated `LillySnapshotContext` and a
`LillyPerfectionSearchPolicy` (default 30 days before and after the query,
0.125-day step; resource choices, not astrological durations). It finds, for
the seven planets:

- every exact contact of every pair at the eight directed classical targets,
  with the P3 bounded scanner;
- every station, as a verified sign change of the longitude rate (roots that
  fall on a grid knot are confirmed from both sides);
- every sign ingress.

Coverage is complete only when every scan completes; budget exhaustion keeps
earlier evidence and marks it partial. `lilly_perfection_routes_at` binds the trace to
an explicitly opened `SpkReader` through `planet_at`, exactly as the P3 lunar
trace does, and records kernel identity, SHA-256 and the UT1/TT query epochs.
`lilly_merge_perfection_traces` joins contiguous windows of one product and
records the K07 continuation receipt.

`lilly_perfection_routes(trace, querent, quesited, readings=..., conditions=...)`
requires a `LillyPerfectionReadings` naming all five readings. It derives:

- **Direct route:** when the principals apply within their combined moiety
  (P2 orb policy), the next exact contact at that directed angle. Applying and
  heavier principals follow the heaviness reading; when it is unresolved, the
  blocker search counts as incomplete and the route is unresolved.
- **Blockers:** retrograde stations of either principal (refranation for the
  applying one; a recorded non-refranation for the heavier); for each third
  planet, its contacts with the principals before the intended contact
  (prohibition, with the third's approach or separation at the query deciding
  prohibitor versus translator); for conjunctions, the heavier principal's
  conjunction with a planet heavier still (frustration). A blocker whose own
  record is unresolved can leave the route unresolved but never blocks it. An
  application that ends in a station or interception with no later contact is
  reported as blocked (`application_ended_without_contact`), not absent.
- **Translation:** each third planet separating at the query from one principal
  (from their last contact in the study) whose next meeting with either
  principal is the other. P06's principal history comes from the principals'
  last contact; intervening contacts and the translator's stations come from the
  trace; reception comes from P2 at the question epoch.
- **Collection:** each third planet that both principals approach, with sign and
  current-aspect beholding, H01 heaviness and P2 reception by each principal.
- **Mutual reception** always; **dwelling** when the caller supplies the
  placement.

Conditions the trace cannot decide (house class, good/proper/friendly houses,
essential well-dignity, dignity in the degrees, the opposition's Moon
condition, the dwelling placement) come from `LillyRouteConditions` and remain
unknown otherwise. Absence means absence within the declared study.

## Validation

- `tests/unit/test_horary_perfection_routes.py` (157 tests): the full fixture
  bundle through the evaluators, plus analytic trajectories that reproduce
  Lilly's printed examples through the trace and derivation: the p.111
  translation (complete under P05, unmet under P06), bodily prohibition,
  refranation (a quadratic Mars stationing at 8 Aries) and the pp.112-113
  frustration; continuation across two merged windows; unresolved heaviness.
- `tests/integration/test_horary_perfection_routes_de441.py` (8 tests, DE441,
  J2000 and 2024-01-01): complete coverage; every contact re-verified from the
  independently projected equatorial Cartesian product, worst residual 0.0004
  arcsec over 61-62 contacts per epoch (tolerance 0.01 arcsec); every station
  changes rate sign in the independent projection; route legs refer to trace
  events. These are geometric/search invariants, not an external-engine
  comparison or certification of unsampled roots.

## Public surfaces

- **Package and facade:** the curated P4 names (readings, conditions, records,
  trace and derivation functions) are importable from `moira` and
  `moira.facade` with the same object identity as their owning module.
- **Facade method:** `Moira.lilly_perfection_routes_at(jd_ut, querent, quesited,
  *, is_day_chart, readings, conditions=None, policy=None, epoch=None)` binds
  the engine's own reader (an `SpkReader` or a `KernelPool`, whose primary
  planetary kernel is named in the provenance) and a dated snapshot context.
  A missing kernel raises `MissingEphemerisKernelError`.
- **REST:** `POST /v1/horary/perfection-routes` (strict request and response
  models in `moira_server/models/horary_perfection.py`). All five readings are
  required with no default; conditions are typed and must cite evidence when
  known; the search window is at most 90 days each side; the response carries
  every route, blocker and trace event and `verdict: null`. Errors: `422` for
  invalid input, `503 kernel_not_ready` without a kernel.
- `tests/server/test_server_horary_perfection_routes.py` (19 tests): genuine
  route records through the transport on analytic trajectories, condition
  mapping, thirteen rejected requests, the `503` mapping, the OpenAPI contract
  (required readings without defaults), and one DE441 end-to-end request.

Still separate admissions: which reading Lilly applies in Book II, whether
reception overcomes refranation, house class of a split conjunction, the
meanings of good houses and malevolent aspect, symbolic timing, historical
chart reconstruction, and any root/facade/REST exposure.
