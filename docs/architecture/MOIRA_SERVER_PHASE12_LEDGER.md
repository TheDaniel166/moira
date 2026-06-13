# Moira Server Phase 12 Evaluation Ledger

Version: 1.2
Date: 2026-06-13
Status: Admitted named Phase 12 route families complete; Sothic, Longevity, and umbrella routes deferred
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
- `wiki/02_standards/URANIAN_BACKEND_STANDARD.md`
- `wiki/02_standards/HARMONICS_BACKEND_STANDARD.md`
- `wiki/02_standards/PHASE_PHOTOMETRY_BACKEND_STANDARD.md`
- `wiki/02_standards/ANTISCIA_BACKEND_STANDARD.md`
- `wiki/02_standards/PLANETARY_HOURS_BACKEND_STANDARD.md`
- `wiki/02_standards/HUBER_BACKEND_STANDARD.md`
- `wiki/02_standards/LONGEVITY_BACKEND_STANDARD.md`
- `docs/architecture/P12-01_URANIAN_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-02_HARMONICS_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-03_PHASE_PHOTOMETRY_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-04_ANTISCIA_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-05_NINE_PARTS_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-06_PLANETARY_HOURS_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-07_HUBER_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-08_SOTHIC_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-10_LORD_OF_THE_ORB_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-11_LORD_OF_THE_TURN_TRANSPORT_DESIGN.md`
- `docs/architecture/P12-U1_SPECIALIST_UMBRELLA_DOCTRINE_DECISION.md`

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
- `stage_1_admitted` - initial bounded route subset is implemented,
  registered, tested, and documented; wider family products remain deferred
- `transport_design_complete` - backend standard and REST transport design are
  complete; implementation is the next step, but no route is admitted yet
- `admit_after_transport_design` - backend standard and engine truth are
  sufficient; transport design should come next
- `admit_after_backend_standard` - engine candidate exists, but a backend
  standard or admission packet must exist before public transport
- `admit_after_minor_transport_hardening` - route shape is likely small, but
  request/response/provenance/bounds still need a design
- `defer_for_doctrine` - doctrine is not stable enough for public transport
- `defer_for_specialist_review` - backend and design may exist, but the family
  is specialist enough, or its public failure semantics subtle enough, that it
  should not be admitted without a separate review decision
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
| P12-01 | Uranian / Hamburg School bodies | `admitted` | `website_good` | Bounded catalog, single-position, and bulk-position routes are implemented, registered, tested, and documented. The route family preserves the nine-name current table including Transpluto and explicitly labels the bodies as hypothetical/Hamburg School mean points, not physical planets. |
| P12-02 | Harmonics | `admitted` | `website_good` | Bounded harmonic routes are implemented, registered, tested, and documented: presets, direct harmonic chart, age-harmonic chart, conjunctions, pattern score, aspects, sweep, fingerprint, and composite over caller-supplied longitudes. Unbounded sweeps, chart construction, rendering, and interpretation remain deferred. |
| P12-03 | Phase / elongation / magnitude | `admitted` | `website_good` | Bounded direct phase and photometry routes are implemented, registered, tested, and documented: illuminated fraction, synodic, elongation, phase angle, angular diameter, and apparent magnitude. Topocentric, atmospheric, visibility, event-search, minor-body, fixed-star, and variable-star photometry remain deferred. |
| P12-04 | Antiscia | `admitted` | `website_good` | Bounded ordinary antiscia routes are implemented, registered, tested, and documented: direct reflection, pair contact search, and fixed-point contact search over caller-supplied longitudes. Primary-direction antiscia, directed arcs, chart motion, networks, scoring, and interpretation remain deferred. |
| P12-05 | Nine Parts | `admitted` | `not_website_target` | Single bounded Abu Ma'shar aggregate route is implemented, registered, tested, and documented. It preserves canonical nine-part order, full-reversal night policy, derived dependencies, condition profiles, validation truth, and Sword/Node admitted-extension status. Chart construction, sect derivation, Al-Sijzi management, longevity integration, comparison bundles, and interpretation remain deferred. |
| P12-06 | Planetary Hours | `admitted` | `website_good` | Bounded sunrise-based schedule and hour-at routes are implemented, registered, tested, and documented. They preserve the dedicated `moira.planetary_hours.PlanetaryHour` vessel, explicit reader policy, UTC timestamp policy, and visible sunrise/sunset failure behavior without location lookup or fallback civil-clock substitution. |
| P12-07 | Huber | `admitted_direct_cusp_stage` | `not_website_ready` | Direct-cusp Huber routes are implemented, registered, tested, and documented. They expose dynamic intensity, house zones, Age Point, intensity-at-longitude, chart intensity profile, and bounded Age Point contact scan over caller-supplied house frames, while chart-backed house derivation remains deferred. |
| P12-08 | Sothic | `defer_for_specialist_review` | `not_website_target` | Backend standard, transport design, and tests exist, but Sothic is a specialist module and is not admitted at this time. Public heliacal-search routes would need explicit failure semantics before they could avoid overstating truth. |
| P12-09 | Longevity / Hyleg-Alcocoden | `defer_for_doctrine` | `not_website_target` | Backend standard and structural unit coverage exist, but the family remains deliberately deferred. It is interpretively high-stakes, lacks a dedicated admission validation suite, and must not expose life-expectancy-style public claims. |
| P12-10 | Lord of the Orb | `admitted` | `not_website_target` | Caller-seeded sequence and current-period routes are implemented, registered, tested, and documented. The route family preserves birth-planet source policy, cycle variant, period/profile/aggregate truth, validation output, and the distinction from Lord of the Turn. |
| P12-11 | Lord of the Turn | `admitted` | `not_website_target` | Caller-supplied Solar Return profile route is implemented, registered, tested, and documented. The route family preserves Al-Qabisi vs Egyptian/Al-Sijzi method policy, profection truth, blocker reasons, candidate assessments, testimony count policy, validation output, and the boundary that SR chart construction remains caller-owned. |
| P12-U1 | Specialist umbrella / `/v1/special/*` | `defer_for_doctrine` | `not_website_ready` | Doctrine decision complete: no umbrella routes now. A future umbrella may only be discovery-only registry metadata; computation and cross-family specialist workflows remain excluded. |

---

## 4. Already-Live REST Surface

P12-01 is admitted as the first Phase 12 REST route family:

- `GET /v1/uranian/catalog`
- `POST /v1/uranian/position`
- `POST /v1/uranian/bulk`

P12-02 is also admitted:

- `GET /v1/harmonics/presets`
- `POST /v1/harmonics/chart`
- `POST /v1/harmonics/age-chart`
- `POST /v1/harmonics/conjunctions`
- `POST /v1/harmonics/pattern-score`
- `POST /v1/harmonics/aspects`
- `POST /v1/harmonics/sweep`
- `POST /v1/harmonics/fingerprint`
- `POST /v1/harmonics/composite`

P12-03 is also admitted:

- `POST /v1/phase/illuminated-fraction`
- `POST /v1/phase/synodic`
- `POST /v1/phase/elongation`
- `POST /v1/phase/angle`
- `POST /v1/phase/angular-diameter`
- `POST /v1/phase/apparent-magnitude`

P12-04 is also admitted:

- `POST /v1/antiscia/reflect`
- `POST /v1/antiscia/contacts`
- `POST /v1/antiscia/to-point`

P12-05 is also admitted:

- `POST /v1/nine-parts/abu-mashar`

P12-06 is also admitted:

- `POST /v1/planetary-hours/schedule`
- `POST /v1/planetary-hours/hour-at`

P12-07 is also admitted as a direct-cusp route family:

- `POST /v1/huber/dynamic-intensity`
- `POST /v1/huber/house-zones`
- `POST /v1/huber/age-point`
- `POST /v1/huber/intensity-at`
- `POST /v1/huber/chart-intensity-profile`
- `POST /v1/huber/age-point-contacts`

P12-10 is also admitted as a caller-seeded Lord of the Orb route family:

- `POST /v1/lord-of-the-orb/sequence`
- `POST /v1/lord-of-the-orb/current`

P12-11 is also admitted as a caller-supplied Lord of the Turn route family:

- `POST /v1/lord-of-the-turn/profile`

`wiki/02_services/REST_API_REFERENCE.md` now lists those live routes and keeps
the remaining Phase 12 families out of the broadly exposed surface:

- `/v1/sothic/*`
- `/v1/special/*`

---

## 5. P12-01 Uranian / Hamburg School Bodies

Status: `admitted`

Candidate module:

- `moira.uranian`

Governing object:

- Uranian/Hamburg School hypothetical body position at a requested epoch.

Evidence:

- Engine module exists.
- Public API reference documents `uranian_at`, `all_uranian_at`, and
  `list_uranian`.
- Backend standard: `wiki/02_standards/URANIAN_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P12-01_URANIAN_TRANSPORT_DESIGN.md`
- Live models: `moira_server/models/uranian.py`
- Live service: `moira_server/services/uranian.py`
- Live router: `moira_server/routers/uranian.py`
- Route tests: `tests/server/test_server_uranian_routes.py`

Admission record:

- Routes implemented and registered in `moira_server/app.py`.
- REST reference updated.
- Focused route tests verify catalog truth, all nine admitted names, single
  position, bulk all-name and subset behavior, provenance, and adversarial
  rejection for unknown names, case mismatches, duplicate bulk names, empty
  names, oversized bulk names, and non-finite `jd_ut`.

Admitted boundary:

- `GET /v1/uranian/catalog`
- `POST /v1/uranian/position`
- `POST /v1/uranian/bulk`

Deferred:

- chart profiles
- midpoint trees
- dial products
- cosmobiology networks
- physical body substitution
- kernel-backed Transpluto/TNO computation

---

## 6. P12-02 Harmonics

Status: `admitted`

Candidate module:

- `moira.harmonics`

Governing object:

- Harmonic transformation and harmonic pattern analysis over named ecliptic
  longitudes.

Evidence:

- Engine module exists.
- Unit tests exist: `tests/unit/test_harmonics.py`.
- Public API reference documents harmonic chart and harmonic-analysis surfaces.
- Backend standard: `wiki/02_standards/HARMONICS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P12-02_HARMONICS_TRANSPORT_DESIGN.md`
- Live models: `moira_server/models/harmonics.py`
- Live service: `moira_server/services/harmonics.py`
- Live router: `moira_server/routers/harmonics.py`
- Route tests: `tests/server/test_server_harmonics_routes.py`

Admission record:

- Routes implemented and registered in `moira_server/app.py`.
- REST reference updated.
- Focused route tests verify preset catalog truth, H1 identity, H5 formula
  truth, output sorting, age-decimal harmonic preservation, conjunction
  truth, pattern-score cluster invariants, aspect/conjunction dual-path
  equivalence, bounded sweep ordering/count, fingerprint peak/total-score
  invariants, composite labels/cross-chart isolation, route registration, and
  adversarial rejection for empty body maps, empty body names, duplicate names
  after trimming, non-finite longitudes, invalid harmonics, oversized body
  maps, negative age windows, non-finite JDs, invalid or oversized orbs,
  oversized sweeps, invalid composite labels, and oversized composite maps.

Admitted boundary:

- `GET /v1/harmonics/presets`
- `POST /v1/harmonics/chart`
- `POST /v1/harmonics/age-chart`
- `POST /v1/harmonics/conjunctions`
- `POST /v1/harmonics/pattern-score`
- `POST /v1/harmonics/aspects`
- `POST /v1/harmonics/sweep`
- `POST /v1/harmonics/fingerprint`
- `POST /v1/harmonics/composite`

Deferred:

- unbounded harmonic sweeps
- automatic chart construction
- transit or progression harmonic searches
- harmogram/spectral-analysis routes
- chart rendering
- interpretive narrative text

---

## 7. P12-03 Phase / Elongation / Magnitude

Status: `admitted`

Candidate module:

- `moira.phase`

Governing object:

- Phase angle, illuminated fraction, elongation, angular diameter, and apparent
  magnitude for supported bodies.

Evidence:

- Engine module exists.
- Unit tests exist for synodic phase behavior.
- Backend standard: `wiki/02_standards/PHASE_PHOTOMETRY_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P12-03_PHASE_PHOTOMETRY_TRANSPORT_DESIGN.md`
- Live models: `moira_server/models/phase.py`
- Live service: `moira_server/services/phase.py`
- Live router: `moira_server/routers/phase.py`
- Route tests: `tests/server/test_server_phase_routes.py`

Admission record:

- Routes implemented and registered in `moira_server/app.py`.
- REST reference updated.
- Focused route tests verify illuminated-fraction boundaries, synodic angle
  and state policy, optional state omission, elongation basis/range,
  phase-angle vector basis/range, angular-diameter support-set acceptance and
  rejection, apparent-magnitude supported-body acceptance with model
  provenance, apparent-magnitude model-detail suppression, unsupported
  apparent-magnitude rejection for Sun, Pluto, asteroid-style, and fixed-star
  style bodies, non-finite JD/angle rejection, empty body rejection, route
  registration, explicit body-resolution failure mapping, and synodic unit
  fixture truth.

Admitted boundary:

- `POST /v1/phase/illuminated-fraction`
- `POST /v1/phase/synodic`
- `POST /v1/phase/elongation`
- `POST /v1/phase/angle`
- `POST /v1/phase/angular-diameter`
- `POST /v1/phase/apparent-magnitude`

Deferred:

- topocentric phase or magnitude
- atmospheric extinction
- visual limiting magnitude
- visibility scoring
- heliacal visibility
- eclipse darkening
- moon-phase or conjunction event searches
- minor-body photometry
- fixed-star or variable-star photometry
- interpretive astrological phase text
- sky rendering

---

## 8. P12-04 Antiscia

Status: `admitted`

Candidate module:

- `moira.antiscia`

Governing object:

- Solstitial reflection points and antiscion/contra-antiscion contacts.

Evidence:

- Engine module exists.
- Tests exist in astrology adversarial and primary-direction antiscia suites.
- Backend standard: `wiki/02_standards/ANTISCIA_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P12-04_ANTISCIA_TRANSPORT_DESIGN.md`
- Transport implementation:
  - `moira_server/models/antiscia.py`
  - `moira_server/services/antiscia.py`
  - `moira_server/routers/antiscia.py`
  - `tests/server/test_server_antiscia_routes.py`

Admitted route boundary:

- `POST /v1/antiscia/reflect`
- `POST /v1/antiscia/contacts`
- `POST /v1/antiscia/to-point`

Admission record:

- direct antiscion, direct contra-antiscion, and both-reflection responses
  preserve the engine formulae and `[0, 360)` output policy
- contact responses preserve `body1`, `body2`, `aspect`, `lon1`, `lon2`,
  `shadow`, `orb`, and increasing-orb ordering
- provenance records `moira.antiscia`, `ordinary_antiscia`,
  `not_primary_direction_antiscia`, no chart motion, and no ephemeris use
- request bounds are enforced: maximum 64 positions and maximum 30-degree orb

Deferred:

- primary-direction arcs
- transits, progressions, chart construction, and house derivation
- antiscia networks, scoring profiles, and interpretive text

Verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\antiscia.py moira_server\services\antiscia.py moira_server\routers\antiscia.py tests\server\test_server_antiscia_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_antiscia_routes.py tests\unit\test_astrology_adversarial_gauntlet.py tests\unit\test_primary_direction_antiscia.py -q
```

Result:

- `32 passed`

---

## 9. P12-05 Nine Parts

Status: `admitted`

Candidate module:

- `moira.nine_parts`

Governing object:

- Abu Ma'shar Nine Parts computation and aggregate condition profile.

Evidence:

- Backend standard: `wiki/02_standards/NINE_PARTS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P12-05_NINE_PARTS_TRANSPORT_DESIGN.md`
- Engine tests: `tests/unit/test_nine_parts.py`
- Transport implementation:
  - `moira_server/models/nine_parts.py`
  - `moira_server/services/nine_parts.py`
  - `moira_server/routers/nine_parts.py`
  - `tests/server/test_server_nine_parts_routes.py`

Admitted route boundary:

- `POST /v1/nine-parts/abu-mashar`

Admission record:

- response preserves the nine canonical parts in Abu Ma'shar order
- response preserves formula variant, full-reversal night policy,
  computation truth, dependency relations, condition profiles, aggregate
  summaries, effective policy, and validation result truth
- Sword and Node remain `admitted_extension` parts with
  `planet_association: null`, not ordinary planetary lots
- provenance records `moira.nine_parts`, `nine_parts_abu_mashar`,
  `validate_nine_parts_output`, caller-supplied night status, caller-supplied
  Ascendant, no chart construction, no house placement, and no sect
  determination

Deferred:

- automatic night or sect determination from chart houses
- Ascendant derivation and chart construction
- solar-return integration
- Al-Sijzi Transfer of Management
- longevity integration
- comparison bundles against `moira.lots`
- Hellenistic nonomoiria
- Vedic Navamsha or any D9 route
- interpretive narrative text

Verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\nine_parts.py moira_server\services\nine_parts.py moira_server\routers\nine_parts.py tests\server\test_server_nine_parts_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_nine_parts_routes.py tests\unit\test_nine_parts.py -q
```

Result:

- `93 passed`

---

## 10. P12-06 Planetary Hours

Status: `admitted`

Candidate module:

- `moira.planetary_hours`

Governing object:

- Day/night planetary hour schedule for a date and location.

Evidence:

- Engine module exists.
- Unit tests exist: `tests/unit/test_planetary_hours_api.py`.
- Backend standard: `wiki/02_standards/PLANETARY_HOURS_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P12-06_PLANETARY_HOURS_TRANSPORT_DESIGN.md`
- Transport implementation:
  - `moira_server/models/planetary_hours.py`
  - `moira_server/services/planetary_hours.py`
  - `moira_server/routers/planetary_hours.py`
  - `tests/server/test_server_planetary_hours_routes.py`

Admitted route boundary:

- `POST /v1/planetary-hours/schedule`
- `POST /v1/planetary-hours/hour-at`

Admission record:

- schedule responses serialize exactly 24
  `moira.planetary_hours.PlanetaryHour` records with `jd_start`, `jd_end`,
  and `is_daytime`
- hour-at responses return the containing hour or `null` outside the resolved
  sunrise-to-next-sunrise window
- provenance distinguishes this vessel from `moira.cycles.PlanetaryHour`,
  records reader policy, and states UTC-only timestamp output
- sunrise/sunset resolution failure is surfaced as a visible validation error;
  the route does not invent fallback sunrise or sunset values

Deferred:

- timezone lookup
- location-name lookup or geocoding
- civil-day calendars
- electional scoring
- `moira.cycles` profiles
- annual lordship systems
- automatic birth planetary-hour derivation for other lordship systems

Verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\planetary_hours.py moira_server\services\planetary_hours.py moira_server\routers\planetary_hours.py tests\server\test_server_planetary_hours_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_planetary_hours_routes.py tests\unit\test_planetary_hours_api.py -q
```

Result:

- `14 passed`

---

## 11. P12-07 Huber

Status: `admitted_direct_cusp_stage`

Candidate module:

- `moira.huber`

Governing object:

- Huber house-zone, age-point, contact, and dynamic-intensity analysis.

Evidence:

- Engine module exists.
- Unit tests exist: `tests/unit/test_huber.py`.
- Backend standard: `wiki/02_standards/HUBER_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P12-07_HUBER_TRANSPORT_DESIGN.md`
- Transport implementation:
  - `moira_server/models/huber.py`
  - `moira_server/services/huber.py`
  - `moira_server/routers/huber.py`
  - `tests/server/test_server_huber_routes.py`

Admitted route boundary:

- `POST /v1/huber/dynamic-intensity`
- `POST /v1/huber/house-zones`
- `POST /v1/huber/age-point`
- `POST /v1/huber/intensity-at`
- `POST /v1/huber/chart-intensity-profile`
- `POST /v1/huber/age-point-contacts`

Admission record:

- all house frames are caller-supplied direct cusp frames
- direct frames require 12 finite cusps plus caller-supplied Ascendant, MC,
  and ARMC anchors; Huber transport does not invent angular-anchor truth
- provenance records `caller_supplied` cusp ownership, effective system,
  fallback truth, Koch doctrine preference, and whether the effective frame is
  Koch
- non-Koch frames are allowed as computational inputs but reported as not
  doctrinally complete Huber house fidelity
- Dynamic Intensity Curve provenance preserves the
  `piecewise_half_cosine_reconstruction` basis and the primary-text formula
  verification limitation
- bounded Age Point contact scans enforce maximum span, minimum step, maximum
  orb, and maximum point count

Deferred:

- chart-backed house-frame derivation through the admitted house adapter
- independent house calculation inside Huber transport
- psychological interpretation text
- counseling, health, or clinical claims
- chart rendering
- unbounded Age Point searches
- transit/progression timing outside Age Point mechanics
- generic `/v1/special/*` exposure

Verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\huber.py moira_server\services\huber.py moira_server\routers\huber.py moira_server\routers\__init__.py moira_server\app.py tests\server\test_server_huber_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_huber_routes.py tests\unit\test_huber.py -q
```

Result:

- focused Huber pytest set passed
- collected test count: `15` server tests plus `55` unit tests

---

## 12. P12-08 Sothic

Status: `defer_for_specialist_review`

Candidate module:

- `moira.sothic`

Governing object:

- Egyptian civil date, Sirius heliacal rising range, Sothic epoch search,
  drift-rate prediction, and Sothic condition profiles.

Evidence:

- Backend standard: `wiki/02_standards/SOTHIC_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P12-08_SOTHIC_TRANSPORT_DESIGN.md`
- Unit tests: `tests/unit/test_sothic.py`
- Public API tests: `tests/unit/test_sothic_public_api.py`
- Integration tests: `tests/integration/test_sothic_research.py`,
  `tests/integration/test_sothic_extended.py`

Remaining pre-admission work:

- keep the route family out of REST for now
- preserve the transport design as a reference, not an admission directive
- define public failure semantics before any future heliacal rising or epoch
  search route is reconsidered
- distinguish valid no-event results from delegated heliacal-search exhaustion,
  missing catalog or ephemeris infrastructure, and delegated internal failures
- keep any future first-pass admission limited to direct Egyptian date and
  prediction routes unless a later review explicitly admits search routes

Recommended first stance:

- do not admit Sothic routes in Phase 12
- treat Sothic as a specialist module that needs a later intentional review
- do not expose `/v1/sothic/*` until the public API can report search truth
  without silently collapsing error, exhaustion, and no-event states

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
- Backend standard: `wiki/02_standards/LONGEVITY_BACKEND_STANDARD.md`
- Existing structural coverage lives inside
  `tests/unit/test_experimental_validation.py`, not a dedicated longevity
  admission suite.

Deferral reason:

- Longevity is interpretively high-stakes and doctrine-heavy.
- The current backend standard explicitly says it does not admit public REST
  routes.
- REST admission would require explicit chart, house, sect, Lot of Fortune,
  dignity, testimony, tie-break, and scoring policy.
- The public language would need safeguards against medical, actuarial,
  counseling, death-prediction, or life-expectancy framing.
- The backend standard is present, but route design remains deferred until a
  dedicated doctrine packet and focused admission tests exist.

Recommended first stance:

- do not design `/v1/longevity/*` routes in Phase 12
- create a longevity doctrine packet before transport
- add a dedicated longevity validation suite before route admission
- keep this off public REST until doctrine, verification, and public-language
  safeguards are explicit

---

## 14. P12-10 Lord Of The Orb

Status: `admitted`

Candidate module:

- `moira.lord_of_the_orb`

Governing object:

- Lord of the Orb sequence, current period, condition profile, and aggregate.

Evidence:

- Backend standard: `wiki/02_standards/LORD_OF_THE_ORB_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P12-10_LORD_OF_THE_ORB_TRANSPORT_DESIGN.md`
- Unit tests: `tests/unit/test_lord_of_the_orb.py`
- Live models: `moira_server/models/lord_of_the_orb.py`
- Live service: `moira_server/services/lord_of_the_orb.py`
- Live router: `moira_server/routers/lord_of_the_orb.py`
- Route tests: `tests/server/test_server_lord_of_the_orb_routes.py`

Admission record:

- Routes implemented and registered in `moira_server/app.py`.
- REST reference updated.
- Focused route tests verify continuous-loop sequence truth, single-cycle
  variant truth, Torres Venus recurrence, current-period age-to-year mapping,
  optional validation omission, route registration, and adversarial rejection
  for invalid birth planets, empty birth planets, invalid years/age, unsupported
  cycle kinds, oversized spans, and malformed booleans.

Admitted boundary:

- `POST /v1/lord-of-the-orb/sequence`
- `POST /v1/lord-of-the-orb/current`

Deferred:

- birth planetary-hour derivation
- chart construction
- annual hierarchy orchestration
- integration with profections or firdaria
- natal or solar-return dignity scoring
- comparison bundles
- interpretive narrative text
- `/v1/special/*` exposure

---

## 15. P12-11 Lord Of The Turn

Status: `admitted`

Candidate module:

- `moira.lord_of_the_turn`

Governing object:

- Lord of the Turn candidate assessment, selected lord, blockers, and
  condition profile.

Evidence:

- Backend standard: `wiki/02_standards/LORD_OF_THE_TURN_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P12-11_LORD_OF_THE_TURN_TRANSPORT_DESIGN.md`
- Unit tests: `tests/unit/test_lord_of_the_turn.py`
- Transport models: `moira_server/models/lord_of_the_turn.py`
- Service adapter: `moira_server/services/lord_of_the_turn.py`
- Router: `moira_server/routers/lord_of_the_turn.py`
- Route tests: `tests/server/test_server_lord_of_the_turn_routes.py`
- REST reference: `wiki/02_services/REST_API_REFERENCE.md`

Admitted REST boundary:

- `POST /v1/lord-of-the-turn/profile`
- accepts caller-supplied natal ASC, completed age, method policy, combust
  orb, and `LordOfTurnSRChart`-shaped Solar Return data
- returns condition profile, result, profection truth, candidate assessments,
  method policy, optional engine validation, and provenance

Admission notes:

- preserves Al-Qabisi sequential succession without simultaneous tiebreaker
  language
- preserves Egyptian/Al-Sijzi witnessing and binary testimony-count policy
- preserves `DOMICILE_ONLY` mode when house placements are absent
- rejects non-finite longitudes, non-classical planets, invalid houses,
  malformed method/policy values, and SR condition references for planets not
  included in the supplied SR chart

Verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\lord_of_the_turn.py moira_server\services\lord_of_the_turn.py moira_server\routers\lord_of_the_turn.py moira_server\routers\__init__.py moira_server\app.py tests\server\test_server_lord_of_the_turn_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_lord_of_the_turn_routes.py tests\unit\test_lord_of_the_turn.py -q`
- result: `103 passed`

Deferred:

- Solar Return chart construction
- house calculation
- ephemeris derivation
- automatic sect calculation
- automatic SR Lot of Fortune calculation
- annual hierarchy orchestration
- combined annual timing dashboards
- interpretive narrative text

---

## 16. P12-U1 Specialist Umbrella

Status: `defer_for_doctrine`

Candidate route family:

- `/v1/special/*`

Reason:

- A generic specialist umbrella would hide the distinct doctrine and input
  requirements of Uranian, harmonics, phase, antiscia, Nine Parts, planetary
  hours, Huber, Sothic, longevity, and lordship systems.
- Doctrine decision:
  `docs/architecture/P12-U1_SPECIALIST_UMBRELLA_DOCTRINE_DECISION.md`

Recommended stance:

- no `/v1/special/*` routes yet
- admit named family routes first
- if an umbrella is ever admitted, it should be discovery-only unless a
  separate doctrine decision proves otherwise

---

## 17. Recommended Implementation Order

Recommended Phase 12 implementation sequence:

1. P12-01 Uranian / Hamburg School Bodies. `complete`
2. P12-02 Harmonics. `complete`
3. P12-03 Phase / Elongation / Magnitude. `complete`
4. P12-04 Antiscia. `complete`
5. P12-05 Nine Parts. `complete`
6. P12-06 Planetary Hours. `complete`
7. P12-07 Huber. `complete`
8. P12-08 Sothic.
9. P12-10 Lord of the Orb.
10. P12-11 Lord of the Turn.
11. P12-09 Longevity / Hyleg-Alcocoden.
12. P12-U1 Specialist Umbrella.

Reason:

- The user selected strict numeric Phase 12 admission order.
- P12-01 is complete.
- P12-02 is complete within the bounded transport design. Unbounded sweeps,
  chart construction, rendering, interpretation, and `/v1/special/*`
  exposure remain outside the admission boundary.
- P12-03 is complete within the bounded transport design. Topocentric,
  atmospheric, visibility, event-search, and non-admitted photometry products
  remain outside the admission boundary.
- P12-04 is complete within the bounded ordinary antiscia transport design.
  Primary-direction arcs, chart motion, antiscia networks, scoring, and
  interpretation remain outside the admission boundary.
- P12-05 is complete within the single Abu Ma'shar aggregate route boundary.
  Chart construction, sect derivation, Al-Sijzi management, longevity
  integration, comparison bundles, D9/Navamsha, and interpretation remain
  outside the admission boundary.
- P12-06 is complete within the bounded sunrise-based schedule/hour-at
  boundary. Location lookup, timezone lookup, civil calendars, electional
  scoring, `moira.cycles` profiles, and fallback sunrise substitution remain
  outside the admission boundary.
- P12-07 is complete within the direct-cusp Huber route boundary. Chart-backed
  Huber remains deferred until it is bound through the admitted house adapter;
  Huber transport does not derive houses independently.
- Sothic is deliberately deferred despite its transport design because it is a
  specialist module and its public heliacal-search semantics need a separate
  truth review before admission.
- P12-10 is complete within the caller-seeded Lord of the Orb route boundary.
  Birth-hour derivation, chart construction, annual hierarchy orchestration,
  dignity scoring, comparison bundles, and interpretation remain outside the
  admission boundary.
- P12-11 is complete within the caller-supplied Solar Return chart route
  boundary. Solar Return construction, house calculation, ephemeris derivation,
  automatic sect calculation, SR Lot of Fortune derivation, annual hierarchy
  orchestration, combined annual dashboards, and interpretation remain outside
  the admission boundary.
- Longevity still waits for additional doctrine and focused tests because of
  its interpretive stakes.
- The specialist umbrella should wait until named families prove their own
  route boundaries.

---

## 18. Phase 12 Non-Goals

Phase 12 planning does not implicitly:

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

Do not implement P12-08 Sothic routes in the current Phase 12 sequence.

The named Phase 12 implementation sequence is now complete for the families
admitted in this phase. P12-08 Sothic and P12-09 Longevity remain deliberate
holds, and P12-U1 remains a deferred umbrella decision rather than an
implementation target.

Before Sothic can return to the implementation queue, add a specialist review
packet that decides whether any Stage 1 direct routes are worth exposing and
defines public search/failure semantics for heliacal rising and epoch routes.
