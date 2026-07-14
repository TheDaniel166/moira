# Moira Server Phase 13 Evaluation Ledger

Version: 0.2
Date: 2026-06-14
Status: Phase 13 bounded electional transport complete; Western electional doctrine deferred
Scope: electional and search-workflow REST candidate evaluation

Phase 13 covers electional search workflow surfaces. This phase is not a
general electional doctrine admission. The live engine currently provides a
generic predicate-based scanner; it does not yet provide a Western-owned
electional judgement system, built-in electional rulesets, or interpretive
recommendation language.

This ledger is downstream of:

- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_SHARED_PRIMITIVES.md`
- `docs/architecture/P13-01_ELECTIONAL_WINDOWS_TRANSPORT_DESIGN.md`
- `docs/architecture/P13-02_ELECTIONAL_MOMENTS_TRANSPORT_DESIGN.md`
- `docs/architecture/P13-03_SCORED_ELECTIONAL_WINDOWS_DOCTRINE_PACKET.md`
- `docs/architecture/P13-03_SCORED_ELECTIONAL_WINDOWS_TRANSPORT_DESIGN.md`
- `wiki/02_services/REST_API_REFERENCE.md`
- `wiki/02_standards/ELECTIONAL_SEARCH_BACKEND_STANDARD.md`
- `wiki/02_standards/API_REFERENCE.md`
- `wiki/07_audit/WESTERN_V2_UPDATE_2026-06.md`
- `moira/electional.py`
- `tests/unit/test_electional.py`

---

## 1. Phase 13 Scope

Candidate module:

- `moira.electional`

Roadmap route families:

- `/v1/electional/windows`
- `/v1/electional/moments`
- `/v1/electional/scored`

Live engine objects:

- `ElectionalPolicy`
- `ElectionalEvaluation`
- `ElectionalWindow`
- `ElectionalScoredWindow`
- `find_electional_windows`
- `find_electional_moments`
- `find_scored_windows`

Phase 13 must distinguish:

- predicate-based search from doctrine-owned electional judgement
- raw matching moments from merged windows
- scored search from built-in electional scoring doctrine
- discrete scan cadence from exact event-boundary truth
- synchronous bounded scans from heavy or async research workflows
- caller-supplied predicates/scorers from server-defined rule profiles

---

## 2. Evaluation Status Vocabulary

Each family receives one route-admission status:

- `admitted` - REST family is implemented, registered, tested, and documented
- `stage_1_admitted` - initial bounded route subset is implemented,
  registered, tested, and documented; wider products remain deferred
- `transport_design_complete` - backend standard and REST transport design are
  complete; implementation is the next step, but no route is admitted yet
- `admit_after_transport_design` - backend standard and engine truth are
  sufficient; transport design should come next
- `admit_after_backend_standard` - engine candidate exists, but a backend
  standard or admission packet must exist before public transport
- `admit_after_doctrine_packet` - computation exists, but public semantics need
  a doctrine decision before route design
- `defer_for_doctrine` - doctrine is not stable enough for public transport
- `defer_for_heavy_workflow_design` - computation may be stable, but public
  transport needs async/bounds/window policy before admission
- `exclude_from_rest` - family does not belong on the ordinary REST compute
  surface

Website readiness is tracked separately:

- `website_good` - bounded routes are ready for website use
- `website_good_needs_minor_hardening` - useful soon, but needs a narrow
  validation or provenance hardening pass
- `not_website_ready` - should not be used by the website yet
- `not_website_target` - useful engine family, but not a website-facing
  priority

---

## 3. Current Evaluation Summary

| Unit | Engine family | Phase status | Website verdict | Reason |
|---|---|---|---|---|
| P13-01 | Electional Windows | `admitted` | `website_good_needs_minor_hardening` | Stage 1 is implemented, registered, tested, and documented. The admitted surface is a profile catalogue plus bounded window route over a small server-defined predicate catalogue; arbitrary predicates, arbitrary scorers, Western doctrine, and advice language remain deferred. |
| P13-02 | Electional Moments | `admitted` | `website_good_needs_minor_hardening` | Implemented, registered, tested, and documented. The route reuses the P13-01 predicate catalogue and scan bounds, returns raw qualifying scan points only, and explicitly rejects exact-boundary, scoring, doctrine, and advice semantics. |
| P13-03 | Scored Electional Windows | `admitted` | `website_good_needs_minor_hardening` | Implemented, registered, tested, and documented. The admitted surface is a scorer-profile catalogue plus bounded scored-window route using server-defined numeric scorer profiles only; arbitrary scorers, Western judgement, advice language, auspiciousness labels, and recommendation semantics remain deferred. |
| P13-U1 | Western Electional Doctrine | `defer_for_doctrine` | `not_website_ready` | A draft doctrine packet now defines the source-owned profile model and the pre-admission `ramesey_moon_condition_v1` rule map. Its unresolved orb, node, house, degree, speed, and VOC policies still block engine and REST admission; recommendation language remains excluded. |

---

## 4. Already-Live REST Surface

The admitted Phase 13 REST surface is the bounded electional search subset:

- `GET /v1/electional/predicate-profiles`
- `GET /v1/electional/scorer-profiles`
- `POST /v1/electional/windows`
- `POST /v1/electional/moments`
- `POST /v1/electional/scored`

The Python engine/import surface is public separately through
`wiki/02_standards/API_REFERENCE.md`, which documents `electional_windows`,
`find_electional_windows`, `find_electional_moments`, and
`find_scored_windows`.

---

## 5. P13-01 Electional Windows

Status: `admitted`

Candidate module:

- `moira.electional`

Candidate engine entrypoint:

- `find_electional_windows`

Governing object:

- A bounded Julian-Day scan that returns merged qualifying windows where a
  caller-owned predicate holds at discrete chart snapshots.

Evidence:

- Engine function exists in `moira/electional.py`.
- Unit coverage exists in `tests/unit/test_electional.py`.
- Python public surface is documented in `wiki/02_standards/API_REFERENCE.md`.
- Backend standard:
  `wiki/02_standards/ELECTIONAL_SEARCH_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P13-01_ELECTIONAL_WINDOWS_TRANSPORT_DESIGN.md`
- Runtime implementation:
  `moira_server/models/electional.py`,
  `moira_server/services/electional.py`,
  `moira_server/routers/electional.py`
- Route admission tests:
  `tests/server/test_server_electional_routes.py`
- REST documentation:
  `wiki/02_services/REST_API_REFERENCE.md`

Backend-standard coverage:

- route-safe predicate admission requirements
- maximum search span and scan-point count requirements
- minimum and maximum `step_days` requirements
- `boundary_refine_steps` requirements
- `max_windows` requirements
- latitude/longitude validation requirements
- body-subset bounds and allowed body-name requirements
- tropical and sidereal evaluation payload truth
- response provenance and explicit discrete-scan semantics

Transport design decisions:

- route family: `GET /v1/electional/predicate-profiles` and
  `POST /v1/electional/windows`
- predicate model: small server-defined predicate catalogue
- admitted predicate profiles: body longitude range, body house membership,
  and body angular separation range
- scan bounds: maximum 31 days, minimum 15-minute cadence, maximum 1000
  computed scan points, maximum 64 returned windows
- boundary refinement: capped at 8 bisection steps and explicitly bracketed,
  not exact root solving

Admitted REST boundary:

- `GET /v1/electional/predicate-profiles` exposes the admitted Stage 1
  server-defined predicate catalogue.
- `POST /v1/electional/windows` executes bounded discrete scans through
  `moira.electional.find_electional_windows`.
- The route admits only body longitude range, body house membership, and body
  angular separation range predicate profiles.
- Responses preserve predicate, policy, scan, validation, bounds, window, and
  provenance truth.
- Window truth is explicitly merged scan-witness truth, not exact electional
  event-boundary truth.

Verification:

- `python -m py_compile moira_server/models/electional.py
  moira_server/services/electional.py moira_server/routers/electional.py
  moira_server/routers/__init__.py moira_server/app.py
  tests/server/test_server_electional_routes.py`
- `python -m pytest tests/server/test_server_electional_routes.py
  tests/unit/test_electional.py -q`
- Initial P13-01 route registry audit: 318 non-documentation routes, 314
  `/v1` routes, and the two P13-01 `/v1/electional/*` routes.

Deferred:

- arbitrary code predicates
- unbounded date-range scans
- asynchronous long-running searches
- built-in electional judgement
- recommendation text
- doctrine-owned Western electional scoring

---

## 6. P13-02 Electional Moments

Status: `admitted`

Candidate module:

- `moira.electional`

Candidate engine entrypoint:

- `find_electional_moments`

Governing object:

- A bounded Julian-Day scan that returns raw qualifying scan-point JDs where a
  caller-owned predicate holds.

Evidence:

- Engine function exists in `moira/electional.py`.
- Unit coverage exists in `tests/unit/test_electional.py`.
- Python public surface is documented in `wiki/02_standards/API_REFERENCE.md`.
- Shared backend standard:
  `wiki/02_standards/ELECTIONAL_SEARCH_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P13-02_ELECTIONAL_MOMENTS_TRANSPORT_DESIGN.md`
- Runtime implementation:
  `moira_server/models/electional.py`,
  `moira_server/services/electional.py`,
  `moira_server/routers/electional.py`
- Route admission tests:
  `tests/server/test_server_electional_routes.py`
- REST documentation:
  `wiki/02_services/REST_API_REFERENCE.md`

Backend-standard coverage:

- route-safe predicate admission requirements
- maximum search span and scan-point count requirements
- minimum and maximum `step_days` requirements
- maximum returned raw moment requirements
- latitude/longitude validation requirements
- body-subset bounds and allowed body-name requirements
- tropical and sidereal evaluation payload truth
- response provenance and explicit discrete-scan semantics

Transport design decisions:

- route family: `POST /v1/electional/moments`
- predicate model: reuse the P13-01 server-defined predicate catalogue
- admitted predicate profiles: body longitude range, body house membership,
  and body angular separation range
- scan bounds: maximum 31 days, minimum 15-minute cadence, maximum 1000
  computed scan points, maximum 1000 returned raw moments
- no boundary refinement for raw moments; `boundary_refine_steps` must be `0`
- raw moments are qualifying scan-point witnesses, not exact event roots

Admitted REST boundary:

- `POST /v1/electional/moments` executes bounded discrete scans through
  `moira.electional.find_electional_moments`.
- The route admits only the same predicate profiles as P13-01.
- Responses preserve predicate, policy, scan, validation, bounds, raw moment,
  and provenance truth.
- Moment truth is explicitly raw qualifying scan-point truth, not exact
  electional event-boundary truth.
- `max_windows` is disabled at engine-policy binding for this route so raw
  scan points are not truncated by the window early-exit mechanism.

Verification:

- `python -m py_compile moira_server/models/electional.py
  moira_server/services/electional.py moira_server/routers/electional.py
  tests/server/test_server_electional_routes.py`
- `python -m pytest tests/server/test_server_electional_routes.py
  tests/unit/test_electional.py -q`
- Route registry audit: 319 non-documentation routes, 315 `/v1` routes, and
  the three `/v1/electional/*` routes listed above.

Deferred:

- exact root finding
- ingress/aspect event solvers
- electional interpretation
- raw dense scans for client-side scoring

---

## 7. P13-03 Scored Electional Windows

Status: `admitted`

Candidate module:

- `moira.electional`

Candidate engine entrypoint:

- `find_scored_windows`

Governing object:

- A bounded window search whose qualifying windows carry a finite score and
  peak scan-point JD from a caller-owned scorer.

Evidence:

- `ElectionalScoredWindow` exists in `moira/electional.py`.
- `find_scored_windows` exists in `moira/electional.py`.
- Doctrine packet:
  `docs/architecture/P13-03_SCORED_ELECTIONAL_WINDOWS_DOCTRINE_PACKET.md`
- Transport design:
  `docs/architecture/P13-03_SCORED_ELECTIONAL_WINDOWS_TRANSPORT_DESIGN.md`
- Runtime implementation:
  `moira_server/models/electional.py`,
  `moira_server/services/electional.py`,
  `moira_server/routers/electional.py`
- Server route coverage:
  `tests/server/test_server_electional_routes.py`

Admission concern:

- The engine score is a caller-supplied scalar convention. It is not, by
  itself, a Moira-owned Western electional judgement doctrine.

Doctrine decision:

- REST scoring may proceed only as bounded scored search infrastructure.
- REST must use server-defined scorer profiles, not caller-owned executable
  scorers.
- Public scores mean numeric fit to a declared scorer profile, not Moira-owned
  electional judgement.
- `peak_jd` means the highest-scored qualifying scan point inside a returned
  window, not an exact mathematical peak or recommendation timestamp.
- Ranking language must be `score_rank` or equivalent profile-bound language,
  never "best", "auspicious", "recommended", or "advice".

Transport design decisions:

- route family: `GET /v1/electional/scorer-profiles` and
  `POST /v1/electional/scored`
- predicate model: reuse the P13-01/P13-02 server-defined predicate catalogue
- scorer model: small server-defined scorer catalogue
- admitted scorer profiles: body longitude target closeness and body angular
  separation target closeness
- score scale: finite `[0.0, 1.0]`
- score direction: higher is closer numeric fit to the declared scorer profile
- scan bounds: maximum 31 days, minimum 15-minute cadence, maximum 1000
  computed scan points, maximum 64 returned scored windows
- score ranks, if returned, are over returned windows only
- `peak_jd` is the highest-scored qualifying scan point inside a returned
  window, not an exact score maximum

Deferred:

- built-in electional quality ranking
- Western electional rule profiles
- recommendation text
- auspicious/inauspicious public labels
- comparison to Vedic `muhurta`

Verification:

- `python -m py_compile moira_server/models/electional.py
  moira_server/services/electional.py moira_server/routers/electional.py
  tests/server/test_server_electional_routes.py`
- `python -m pytest tests/server/test_server_electional_routes.py
  tests/unit/test_electional.py -q`
- route registry check confirmed 321 non-documentation routes, 317 versioned
  `/v1` routes, and the five admitted `/v1/electional/*` routes listed above.

---

## 8. P13-U1 Western Electional Doctrine

Status: `defer_for_doctrine`

Candidate surface:

- future doctrine-owned Western electional subsystem

Reason:

- The Western audit states that the current electional engine is a generic
  predicate engine, not a Western doctrine subsystem.
- There is no built-in Western electional ruleset/profile family.
- There is no first-class Western electional scoring or judgement surface
  comparable to Vedic `muhurta`.

Defined by the draft doctrine packet:

- doctrine note for Western electional scope
- rule/profile vocabulary
- judgement boundaries and public-language policy
- validation strategy and prohibition on an unsourced built-in score
- separation between search infrastructure and electional doctrine

Still required before admission:

- close the first profile's explicit ambiguity-policy ledger from source
- implement the profile as visible rule witnesses in the engine
- pass source-boundary, compound-rule, substrate, integration, and sovereignty
  validation
- make a separate facade and REST admission decision, if requested

Research and doctrine foundation (2026-07-14):

- `docs/architecture/P13-U1_WESTERN_ELECTIONAL_DOCTRINE_RESEARCH_DOSSIER.md`
  (v0.7) supplies the primary-source rule inventory, named-lineage citation
  base, and the register of doctrinal variants that must be preserved. Primary
  texts in hand include Dorotheus Book V (*Carmen*, Dykes) and Sahl
  *On Elections* (Dykes *Choices & Inceptions*). Complete companion inventories:
  `P13-U1_DOROTHEUS_BOOK_V_RULE_INVENTORY.md` and
  `P13-U1_SAHL_ON_ELECTIONS_RULE_INVENTORY.md`.
- `docs/architecture/P13-U1_WESTERN_ELECTIONAL_DOCTRINE_PACKET.md` (v0.1)
  defines governing objects, rule vocabulary, election classes, public
  language, the page-confirmed Ramesey ten-rule map, named variants, and
  admission gates. It remains a draft: the profile-specific policy questions
  in §8 deliberately block runtime admission.

Recommended stance:

- keep doctrine-owned electional off the REST route plan until the first
  profile is implemented and validated
- resolve the doctrine packet's ambiguity-policy ledger before engine work

---

## 9. Recommended Implementation Order

Recommended Phase 13 sequence:

1. P13 backend standard for electional search. `complete`
2. P13-01 Electional Windows transport design. `complete`
3. P13-01 implementation. `complete`
4. P13-02 Electional Moments transport design. `complete`
5. P13-02 implementation. `complete`
6. P13-03 Scored Electional Windows doctrine packet. `complete`
7. P13-03 transport design under server-defined scorer profiles. `complete`
8. P13-03 implementation. `complete`
9. P13-U1 draft doctrine packet and page-confirmed first profile map.
   `complete`; runtime profile admission remains blocked.

Reason:

- Windows are the most user-legible output and preserve the engine's merged
  witness vessel.
- Moments are lower-level scan points and should inherit the same predicate and
  bounds discipline.
- Scored windows are more semantically dangerous because score language can
  look like doctrine-owned electional judgement.
- Western electional doctrine is a separate product layer, not an automatic
  consequence of exposing a search engine.

---

## 10. Phase 13 Non-Goals

Phase 13 planning does not implicitly:

- add REST routes
- accept arbitrary executable predicates over HTTP
- expose arbitrary executable scorers over HTTP
- create a Western electional doctrine system
- provide electional advice or recommendation text
- expose unbounded scans
- create async job infrastructure
- change chart construction
- change kernel lifecycle semantics
- change house, zodiac-frame, or ayanamsa computation
- replace Vedic `muhurta` or compare Western electional scoring to it

---

## 11. Immediate Next Step

Phase 13 transport admission is complete for the bounded electional search
subset. P13-U1 now has a separate draft doctrine packet, but remains deferred
for runtime admission. The next step is to resolve the nine explicit policy
questions in that packet's §8 from the held sources, then implement and
validate `ramesey_moon_condition_v1` in the engine before considering facade or
REST exposure.

No next implementation step should treat the admitted scored route as advice,
recommendation, auspiciousness, or Western electional judgement.
