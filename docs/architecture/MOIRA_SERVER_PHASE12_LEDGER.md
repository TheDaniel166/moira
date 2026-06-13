# Moira Server Phase 12 Evaluation Ledger

Version: 0.1
Date: 2026-06-13
Status: Phase 12 specialist analytical families under evaluation
Scope: specialist analytical REST candidate evaluation

Phase 12 covers niche analytical families. These are not core chart,
phenomena, relationship, predictive, Vedic/classical doctrine, spatial, or
catalog surfaces. They are specialist analytical tools that need clear
transport boundaries so their doctrine does not disappear into a generic
`/v1/special/*` payload.

This ledger is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `wiki/02_services/REST_API_REFERENCE.md`
- `wiki/02_standards/API_REFERENCE.md`
- `wiki/02_standards/NINE_PARTS_BACKEND_STANDARD.md`
- `wiki/02_standards/SOTHIC_BACKEND_STANDARD.md`
- `wiki/02_standards/LORD_OF_THE_ORB_BACKEND_STANDARD.md`
- `wiki/02_standards/LORD_OF_THE_TURN_BACKEND_STANDARD.md`

---

## 1. Phase 12 Boundary

Candidate modules:

- `moira.uranian`
- `moira.harmonics`
- `moira.phase`
- `moira.antiscia`
- `moira.nine_parts`
- `moira.planetary_hours`
- `moira.huber`
- `moira.sothic`
- `moira.longevity`
- `moira.lord_of_the_turn`
- `moira.lord_of_the_orb`

Candidate route families:

- `/v1/uranian/*`
- `/v1/harmonics/*`
- `/v1/phase/*`
- `/v1/antiscia/*`
- `/v1/nine-parts/*`
- `/v1/planetary-hours/*`
- `/v1/huber/*`
- `/v1/sothic/*`
- `/v1/longevity/*`
- `/v1/lord-of-the-orb/*`
- `/v1/lord-of-the-turn/*`
- `/v1/special/*` only if a separate umbrella doctrine admits it

Phase 12 must distinguish:

- direct analytical primitives from chart-backed profiles
- deterministic arithmetic from doctrine-bearing interpretation
- one-instant computation from range/search workflows
- read-only analytical transport from heavy scan or research jobs
- specialist family doctrine from a generic "special" bucket

---

## 2. Evaluation Status Vocabulary

Each family receives one route-admission status:

- `admitted` - REST family is implemented, registered, tested, and documented
- `admit_after_transport_design` - backend standard and engine truth are
  sufficient; transport design should come next
- `admit_after_backend_standard` - engine candidate exists, but a backend
  standard or admission packet must exist before public transport
- `admit_after_minor_transport_hardening` - route shape is likely small, but
  request/response/provenance/bounds still need a design
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
| P12-01 | Uranian / Hamburg School bodies | `admit_after_backend_standard` | `not_website_ready` | Engine surface exists for Uranian hypothetical positions, but REST admission needs a backend standard naming ephemeris model, body set, frame, validity envelope, and non-astronomical/hypothetical-body semantics. |
| P12-02 | Harmonics | `admit_after_backend_standard` | `not_website_ready` | Engine surface is broad and tested, but public transport must distinguish single harmonic charts, age harmonics, conjunctions, sweeps, aspects, composites, and vibrational fingerprints before routes are admitted. |
| P12-03 | Phase / elongation / magnitude | `admit_after_backend_standard` | `not_website_ready` | Astronomical phase and apparent-magnitude products touch protected substrate/photometry semantics; route admission needs a standard for body support, observer frame, magnitude model, and policy boundaries. |
| P12-04 | Antiscia | `admit_after_backend_standard` | `not_website_ready` | Engine primitive is small and tested, but public transport needs a standard clarifying antiscion, contra-antiscion, orb, pair matching, and chart-backed profile boundaries. |
| P12-05 | Nine Parts | `admit_after_transport_design` | `not_website_target` | Backend standard and unit tests exist. Transport should preserve Abu Ma'shar policy, formula variants, dependency relations, historical scope, condition profiles, and aggregate truth. |
| P12-06 | Planetary Hours | `admit_after_backend_standard` | `website_good_needs_minor_hardening` | Engine and tests exist, but REST must define location/time inputs, high-latitude/sunrise failure behavior, timezone semantics, and distinction from `moira.cycles.PlanetaryHour`. |
| P12-07 | Huber | `admit_after_backend_standard` | `not_website_ready` | Engine and tests exist for house zones, age point, contacts, and dynamic intensity; admission needs a backend standard because it depends on house-cusp truth and Huber-specific doctrine. |
| P12-08 | Sothic | `admit_after_transport_design` | `not_website_target` | Backend standard and tests exist. Transport must separate Egyptian date conversion, Sothic rising ranges, epoch search, drift prediction, chart condition profiles, and network profiles, with strict range bounds. |
| P12-09 | Longevity / Hyleg-Alcocoden | `defer_for_doctrine` | `not_website_target` | Engine candidate exists, but longevity doctrine is interpretively high-stakes and depends on chart, sect, dignity, house, and testimony policy. It needs a backend standard before REST work. |
| P12-10 | Lord of the Orb | `admit_after_transport_design` | `not_website_target` | Backend standard and tests exist. Transport can be designed after preserving birth-hour source, cycle policy, sequence/profile/aggregate shapes, and validation results. |
| P12-11 | Lord of the Turn | `admit_after_transport_design` | `not_website_target` | Backend standard and tests exist. Transport can be designed after preserving Al-Qabisi vs Egyptian/Al-Sijzi method policy, blocker reasons, candidate assessments, and condition profiles. |
| P12-U1 | Specialist umbrella / `/v1/special/*` | `defer_for_doctrine` | `not_website_ready` | A generic specialist umbrella risks hiding distinct doctrine. Named families should be admitted first; any umbrella must be discovery-only unless separately justified. |

---

## 4. Already-Live REST Surface

There are no admitted Phase 12 REST route families at the time of this ledger.

`wiki/02_services/REST_API_REFERENCE.md` correctly lists Phase 12 as not yet
broadly exposed:

- `/v1/uranian/*`
- `/v1/harmonics/*`
- `/v1/phase/*`
- `/v1/antiscia/*`
- `/v1/special/*`

---

## 5. P12-01 Uranian / Hamburg School Bodies

Status: `admit_after_backend_standard`

Candidate module:

- `moira.uranian`

Governing object:

- Uranian/Hamburg School hypothetical body position at a requested epoch.

Evidence:

- Engine module exists.
- Public API reference documents `uranian_at`, `all_uranian_at`, and
  `list_uranian`.

Required pre-admission work:

- create a Uranian backend standard
- state body set and naming policy
- state position model and authority/provenance
- state frame and validity envelope
- explicitly label these as hypothetical/school bodies, not physical planets

Recommended first stance:

- design `/v1/uranian/list`
- design `/v1/uranian/position`
- design `/v1/uranian/bulk`
- defer chart profiles, midpoint trees, and cosmobiology networks

---

## 6. P12-02 Harmonics

Status: `admit_after_backend_standard`

Candidate module:

- `moira.harmonics`

Governing object:

- Harmonic transformation and harmonic pattern analysis over named ecliptic
  longitudes.

Evidence:

- Engine module exists.
- Unit tests exist: `tests/unit/test_harmonics.py`.
- Public API reference documents harmonic chart and harmonic-analysis surfaces.

Required pre-admission work:

- create a harmonics backend standard
- split simple harmonic chart transport from sweeps/fingerprints
- define maximum body count and harmonic range bounds
- preserve named harmonic preset truth

Recommended first stance:

- admit direct harmonic chart calculation first
- defer harmonic sweeps, composites, and vibrational fingerprints until bounded
  separately

---

## 7. P12-03 Phase / Elongation / Magnitude

Status: `admit_after_backend_standard`

Candidate module:

- `moira.phase`

Governing object:

- Phase angle, illuminated fraction, elongation, angular diameter, and apparent
  magnitude for supported bodies.

Evidence:

- Engine module exists.
- Unit tests exist for synodic phase behavior.

Required pre-admission work:

- create a phase/photometry backend standard
- define supported bodies per product
- state geocentric vs topocentric boundary
- state apparent-magnitude models and limitations
- define non-finite JD/body rejection rules

Recommended first stance:

- admit direct phase and elongation primitives first
- defer apparent magnitude until model/provenance language is explicit

---

## 8. P12-04 Antiscia

Status: `admit_after_backend_standard`

Candidate module:

- `moira.antiscia`

Governing object:

- Solstitial reflection points and antiscion/contra-antiscion contacts.

Evidence:

- Engine module exists.
- Tests exist in astrology adversarial and primary-direction antiscia suites.

Required pre-admission work:

- create an Antiscia backend standard
- distinguish point reflection from chart contact search
- define orb policy and pair matching semantics
- avoid conflating primary-direction antiscia with ordinary chart antiscia

Recommended first stance:

- design direct point reflection routes
- design bounded chart contact route
- defer network/profile routes

---

## 9. P12-05 Nine Parts

Status: `admit_after_transport_design`

Candidate module:

- `moira.nine_parts`

Governing object:

- Abu Ma'shar Nine Parts computation and aggregate condition profile.

Evidence:

- Backend standard: `wiki/02_standards/NINE_PARTS_BACKEND_STANDARD.md`
- Engine tests: `tests/unit/test_nine_parts.py`

Required pre-admission work:

- write P12-05 transport design
- design direct chart-input request shape
- preserve formula variants, reversal rule, historical scope, dependencies,
  condition profiles, and validation warnings

Recommended first stance:

- admit one chart-backed aggregate route
- defer longevity integration and comparison bundles

---

## 10. P12-06 Planetary Hours

Status: `admit_after_backend_standard`

Candidate module:

- `moira.planetary_hours`

Governing object:

- Day/night planetary hour schedule for a date and location.

Evidence:

- Engine module exists.
- Unit tests exist: `tests/unit/test_planetary_hours_api.py`.

Required pre-admission work:

- create a Planetary Hours backend standard
- define input shape: JD/date, latitude, longitude, timezone policy
- define polar/no-rise/no-set handling
- distinguish `moira.planetary_hours.PlanetaryHour` from
  `moira.cycles.PlanetaryHour`

Recommended first stance:

- design one schedule route and one hour-at-instant route
- defer electional scoring and daily calendars

---

## 11. P12-07 Huber

Status: `admit_after_backend_standard`

Candidate module:

- `moira.huber`

Governing object:

- Huber house-zone, age-point, contact, and dynamic-intensity analysis.

Evidence:

- Engine module exists.
- Unit tests exist: `tests/unit/test_huber.py`.

Required pre-admission work:

- create a Huber backend standard
- define house-cusp input requirements and house-system assumptions
- split house-zone, age-point, contact, and intensity products
- preserve dependence on admitted house-frame truth

Recommended first stance:

- admit direct house-zone and age-point routes first
- defer full chart intensity profile until response shape is designed

---

## 12. P12-08 Sothic

Status: `admit_after_transport_design`

Candidate module:

- `moira.sothic`

Governing object:

- Egyptian civil date, Sirius heliacal rising range, Sothic epoch search,
  drift-rate prediction, and Sothic condition profiles.

Evidence:

- Backend standard: `wiki/02_standards/SOTHIC_BACKEND_STANDARD.md`
- Unit tests: `tests/unit/test_sothic.py`
- Public API tests: `tests/unit/test_sothic_public_api.py`
- Integration tests: `tests/integration/test_sothic_research.py`,
  `tests/integration/test_sothic_extended.py`

Required pre-admission work:

- write P12-08 transport design
- split direct Egyptian date conversion from range-based heliacal searches
- define year-span bounds and timeout/async posture
- preserve calendar, heliacal, epoch, and prediction policies

Recommended first stance:

- admit Egyptian date conversion first
- admit bounded Sothic rising/epoch range routes only with strict year bounds
- defer network profile routes until a separate profile design

---

## 13. P12-09 Longevity / Hyleg-Alcocoden

Status: `defer_for_doctrine`

Candidate module:

- `moira.longevity`

Governing object:

- Traditional hyleg and alcocoden longevity analysis.

Evidence:

- Engine module exists.
- Public API reference documents `find_hyleg` and `calculate_longevity`.

Deferral reason:

- Longevity is interpretively high-stakes and doctrine-heavy.
- REST admission would require explicit chart, house, sect, dignity,
  testimony, and scoring policy.
- The current Phase 12 ledger does not identify a backend standard for this
  family.

Recommended first stance:

- create a longevity backend standard before transport
- keep this off public REST until doctrine and verification are explicit

---

## 14. P12-10 Lord Of The Orb

Status: `admit_after_transport_design`

Candidate module:

- `moira.lord_of_the_orb`

Governing object:

- Lord of the Orb sequence, current period, condition profile, and aggregate.

Evidence:

- Backend standard: `wiki/02_standards/LORD_OF_THE_ORB_BACKEND_STANDARD.md`
- Unit tests: `tests/unit/test_lord_of_the_orb.py`

Required pre-admission work:

- write P12-10 transport design
- preserve birth planet/source policy
- preserve cycle kind, period fields, sequence profile, aggregate, and
  validation results

Recommended first stance:

- admit sequence and current-period routes first
- defer comparison bundles and interpretive narrative

---

## 15. P12-11 Lord Of The Turn

Status: `admit_after_transport_design`

Candidate module:

- `moira.lord_of_the_turn`

Governing object:

- Lord of the Turn candidate assessment, selected lord, blockers, and
  condition profile.

Evidence:

- Backend standard: `wiki/02_standards/LORD_OF_THE_TURN_BACKEND_STANDARD.md`
- Unit tests: `tests/unit/test_lord_of_the_turn.py`

Required pre-admission work:

- write P12-11 transport design
- preserve method policy: Al-Qabisi vs Egyptian/Al-Sijzi
- preserve profection, sect-light, candidate roles, blockers, testimony, and
  fallback truth

Recommended first stance:

- admit one direct result/profile route after model design
- defer combined annual timing dashboards

---

## 16. P12-U1 Specialist Umbrella

Status: `defer_for_doctrine`

Candidate route family:

- `/v1/special/*`

Reason:

- A generic specialist umbrella would hide the distinct doctrine and input
  requirements of Uranian, harmonics, phase, antiscia, Nine Parts, planetary
  hours, Huber, Sothic, longevity, and lordship systems.

Recommended stance:

- no `/v1/special/*` routes yet
- admit named family routes first
- if an umbrella is ever admitted, it should be discovery-only unless a
  separate doctrine decision proves otherwise

---

## 17. Recommended Evaluation Order

Recommended Phase 12 sequence:

1. P12-05 Nine Parts.
2. P12-10 Lord of the Orb.
3. P12-11 Lord of the Turn.
4. P12-08 Sothic.
5. P12-04 Antiscia.
6. P12-06 Planetary Hours.
7. P12-02 Harmonics.
8. P12-03 Phase / Elongation / Magnitude.
9. P12-07 Huber.
10. P12-01 Uranian / Hamburg School Bodies.
11. P12-09 Longevity / Hyleg-Alcocoden.
12. P12-U1 Specialist Umbrella.

Reason:

- Nine Parts, Lord of the Orb, Lord of the Turn, and Sothic already have
  backend standards.
- Antiscia and Planetary Hours are compact enough to standardize early.
- Harmonics and Phase have larger product surfaces and need careful route
  slicing.
- Huber depends on house-cusp truth and needs house-frame policy review.
- Uranian needs hypothetical-body provenance before public transport.
- Longevity should wait for doctrine because of its interpretive stakes.
- The specialist umbrella should wait until named families prove their own
  route boundaries.

---

## 18. Phase 12 Non-Goals

Phase 12 evaluation does not implicitly:

- add REST routes
- create new request or response models
- introduce async research jobs
- expose unbounded harmonic or Sothic sweeps
- add interpretive narrative text
- change astronomical engine computation
- change house derivation, location lookup, or kernel lifecycle semantics
- hide specialist family doctrine inside `/v1/special/*`

---

## 19. Immediate Next Step

The next Phase 12 readiness target should be P12-05 Nine Parts because it
already has a backend standard and focused unit tests.

The next task should be:

- read `wiki/02_standards/NINE_PARTS_BACKEND_STANDARD.md`
- read `moira/nine_parts.py`
- read `tests/unit/test_nine_parts.py`
- write `docs/architecture/P12-05_NINE_PARTS_TRANSPORT_DESIGN.md`

Do not implement Phase 12 routes before the per-family transport design exists.
