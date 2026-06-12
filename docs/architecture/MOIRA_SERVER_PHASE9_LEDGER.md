# Moira Server Phase 9 Ledger

Version: 0.1
Date: 2026-06-11
Status: P9-01 Panchanga, P9-02 Shadbala, P9-03 Jaimini, P9-04 Classical Dignities, P9-05 Lots, P9-06 Triplicity, P9-07 Egyptian Bounds, P9-08 Vedic Dignities, P9-09 Ashtakavarga, P9-10 Alternate Dasha Systems, P9-11 Varga, and P9-12 Decans / Decanates admitted; Phase 9 named candidate families admitted
Scope: Vedic and classical doctrine surfaces before REST transport design

This ledger governs Phase 9 of the Moira REST expansion: Vedic and classical
doctrine surfaces. It applies the pre-admission rule added to
`docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`.

No Phase 9 request models, serializers, services, or routers should be designed
until the corresponding engine family has an evaluation record here.

The question at this stage is not "what endpoint should we make?" The question
is whether the engine family is complete, doctrine-stable, validated,
documented, facade-visible, and suitable for public transport.

---

## 1. Evaluation Status Vocabulary

Each family receives one of the route-admission checklist statuses:

- `admit_now` - engine family is complete and doctrine-stable enough for REST
- `admit_after_minor_engine_work` - bounded engine/doc fixes should precede REST
- `defer_for_engine_completion` - transport work would expose an incomplete family
- `defer_for_doctrine` - doctrine is not stable enough for public transport
- `exclude_from_rest` - family does not belong on the ordinary REST compute surface

These statuses are pre-admission findings. A family marked `admit_now` still
needs the normal REST sequence: transport stance, request models, response
models, serializers, service adapter, routes, parity tests, adversarial tests,
and documentation updates.

Once that sequence is complete, this ledger may move the family to:

- `admitted` - REST family is implemented, registered, tested, and documented

---

## 2. Phase 9 Candidate Families

The Phase 9 candidate set is drawn from
`docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`.

Primary candidate modules:

- `moira.panchanga`
- `moira.shadbala`
- `moira.varga`
- `moira.ashtakavarga`
- `moira.jaimini`
- `moira.vedic_dignities`
- `moira.dasha_systems`
- `moira.dignities`
- `moira.lots`
- `moira.triplicity`
- `moira.decanates` / `moira.hermetic_decans`
- `moira.egyptian_bounds`

Umbrella modules such as `moira.vedic` and `moira.classical` are import
surfaces, not doctrine families. They should not be exposed as generic REST
catch-all endpoints. REST should expose the named doctrine families beneath
them.

---

## 3. Current Evaluation Summary

| Unit | Engine family | Status | Reason |
|---|---|---|---|
| P9-01 | Panchanga | `admitted` | Four REST routes live and tested: direct/chart-backed instant plus direct/chart-backed profile. |
| P9-02 | Shadbala | `admitted` | Four chart-backed REST routes live and tested: result, profile, network, and condition. |
| P9-03 | Jaimini | `admitted` | Eight direct/chart-backed REST routes live and tested: karakas, profile, condition, and pair. |
| P9-04 | Classical dignities | `admitted` | Six chart-backed REST routes are live and tested against the Phase 11 backend standard, public result/truth/profile surfaces, validation doctrine, and facade/root exports. |
| P9-05 | Lots | `admitted` | Catalogue plus six chart-backed REST routes are live and tested against the Phase 11 backend standard, doctrine/policy/dependency/profile surfaces, and facade/root exports. |
| P9-06 | Triplicity | `admitted` | Three direct-sync REST routes are live and tested against the Phase 11/12 backend standard, explicit doctrine/policy surfaces, and facade/root exports. |
| P9-07 | Egyptian bounds | `admitted` | Seven direct-sync REST routes are live and tested against the backend standard, table/truth/classification/relation/condition/aggregate/network surfaces, and explicit doctrine policy. |
| P9-08 | Vedic dignities | `admitted` | Four direct-sync and three chart-backed REST routes are live and tested against the backend standard, dignity/relationship/condition/chart-profile surfaces, and ayanamsa provenance policy. |
| P9-09 | Ashtakavarga | `admitted` | Four direct-sync and four chart-backed REST routes are live and tested against the backend standard, BAV/SAV result, shodhana policy, sign-strength, transit-strength, chart-profile, and Lagna derivation provenance surfaces. |
| P9-10 | Alternate dasha systems | `admitted` | Five direct-compute and four chart-backed REST routes are live and tested against the backend standard, Ashtottari/Yogini sequence/profile surfaces, period-profile projection, natal Moon derivation, and eligibility-limit truth. |
| P9-11 | Varga | `admitted` | Five direct-sync and three chart-backed REST routes are live and tested against the backend standard, generic/named VargaPoint surfaces, Shodashvarga set, and batch projections. |
| P9-12 | Decans / decanates | `admitted` | Eight direct-sync and two chart-backed REST routes are live and tested against the backend standard, decanate placement truth, body-backed Vedic drekkana/decanate set derivation, Hermetic catalog/longitude/rising lookup, and night-hour vessel serialization. |
| P9-U1 | `moira.vedic` umbrella | `exclude_from_rest` | Import aggregation surface; expose named Vedic doctrine families instead. |
| P9-U2 | `moira.classical` umbrella | `exclude_from_rest` | Import aggregation surface; expose named classical doctrine families instead. |

---

## 4. Family Evaluation Records

### P9-01 Panchanga

Status: `admitted`

Governing object:

- A five-limb Vedic almanac instant: Tithi, Vara, Nakshatra, Yoga, and Karana.

Evidence:

- Backend standard: `wiki/02_standards/PANCHANGA_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-01_PANCHANGA_TRANSPORT_DESIGN.md`
- Engine module: `moira/panchanga.py`
- Public surfaces include `PanchangaResult`, `PanchangaPolicy`,
  `tithi_condition_profile`, `panchanga_profile`, and
  `validate_panchanga_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_panchanga.py`

REST admission notes:

- Transport must preserve the five limbs separately.
- Nakshatra remains delegated to the sidereal/nakshatra subsystem and should
  be serialized as the richer `NakshatraPosition` vessel, not flattened into a
  bare name. Required transport fields include at least `nakshatra`,
  `nakshatra_index`, `nakshatra_lord`, `pada`, `degrees_in`, and
  `sidereal_lon`.
- Both route forms are needed:
  - a direct calculation route accepting already-derived Sun/Moon tropical
    longitudes plus JD/policy
  - a chart-backed convenience route deriving Sun/Moon from birth/event
    datetime and optional observer/chart context
- Keep the two route forms distinct so caller-supplied derived truth is not
  confused with server-derived chart truth.

Next action:

- P9-01 is admitted.
- Live routes:
  - `POST /v1/panchanga/instant`
  - `POST /v1/panchanga/instant/profile`
  - `POST /v1/panchanga/chart`
  - `POST /v1/panchanga/chart/profile`
- Verification:
  - `tests/server/test_server_panchanga_service.py`
  - `tests/server/test_server_panchanga_routes.py`

### P9-02 Shadbala

Status: `admitted`

Governing object:

- Sixfold Vedic planetary strength, including component strength, policy,
  profile, chart aggregate, and network intelligence surfaces.

Evidence:

- Backend standard: `wiki/02_standards/SHADBALA_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-02_SHADBALA_TRANSPORT_DESIGN.md`
- Engine module: `moira/shadbala.py`
- Public surfaces include `ShadbalaResult`, `ShadbalaPolicy`,
  `shadbala_condition_profile`, `shadbala_chart_profile`,
  `shadbala_network_profile`, and `validate_shadbala_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_shadbala.py`

REST admission notes:

- Shadbala has more input dependencies than Panchanga. A chart-backed service
  adapter is the first admitted route stance; direct caller-supplied Shadbala
  bundles are deferred until a strict consistency contract exists.
- Transport must keep component strengths visible; do not expose only a final
  score.
- Policy fields must remain explicit.
- Hora strength must remain visibly policy-bound because `hora_lord_at(...)`
  requires sunrise JD and is not derivable from datetime alone.
- Live routes:
  - `POST /v1/shadbala/chart`
  - `POST /v1/shadbala/chart/profile`
  - `POST /v1/shadbala/chart/network`
  - `POST /v1/shadbala/chart/condition`
- Verification:
  - `tests/server/test_server_shadbala_service.py`
  - `tests/server/test_server_shadbala_routes.py`

Next action:

- P9-02 is admitted.

### P9-03 Jaimini

Status: `admitted`

Governing object:

- Jaimini Chara Karaka assignment over seven classical planets, optionally
  including Rahu.

Evidence:

- Backend standard: `wiki/02_standards/JAIMINI_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-03_JAIMINI_TRANSPORT_DESIGN.md`
- Engine module: `moira/jaimini.py`
- Public surfaces include `JaiminiKarakaResult`, `JaiminiPolicy`,
  `karaka_condition_profile`, `jaimini_chart_profile`, `karaka_pair`, and
  `validate_jaimini_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_jaimini.py`

REST admission notes:

- The 7-karaka vs. 8-karaka policy must remain visible.
- Tie warnings are astronomical/doctrinal truth and must not be omitted.
- Direct sidereal input is admissible because the caller-owned input contract is
  narrow: planet name to sidereal longitude plus explicit scheme/policy.
- Chart-backed input is also admissible. Scheme 8 must source Rahu from the
  true lunar node and must not admit Ketu as a karaka candidate.
- Live routes:
  - `POST /v1/jaimini/karakas`
  - `POST /v1/jaimini/karakas/profile`
  - `POST /v1/jaimini/karakas/condition`
  - `POST /v1/jaimini/karakas/pair`
  - `POST /v1/jaimini/chart/karakas`
  - `POST /v1/jaimini/chart/profile`
  - `POST /v1/jaimini/chart/condition`
  - `POST /v1/jaimini/chart/pair`
- Verification:
  - `tests/server/test_server_jaimini_service.py`
  - `tests/server/test_server_jaimini_routes.py`

Next action:

- P9-03 is admitted.

### P9-04 Classical Dignities

Status: `admitted`

Governing object:

- Classical dignity, debility, reception, condition, and chart/network dignity
  analysis.

Evidence:

- Backend standard: `wiki/02_standards/DIGNITIES_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-04_CLASSICAL_DIGNITIES_TRANSPORT_DESIGN.md`
- Engine module: `moira/dignities.py`
- Public exports are present through `moira`, `moira.classical`, and
  `moira.facade`.
- Unit tests exist for public API and dignity/lots behavior.
- Server route tests exist: `tests/server/test_server_dignities_routes.py`

REST admission notes:

- Dignity truth, classification, condition profiles, and reception/network
  products are distinct surfaces. Do not collapse them into one generic
  "dignity score" endpoint.
- First admission is chart-backed. The server owns planet, house, sect, solar
  condition, and reception derivation through `DignitiesService`.
- Direct caller-owned dignity bundles are deferred until a strict consistency
  contract exists for positions, retrograde state, houses, and policy.
- Live chart-backed routes:
  - `POST /v1/dignities/chart`
  - `POST /v1/dignities/chart/receptions`
  - `POST /v1/dignities/chart/conditions`
  - `POST /v1/dignities/chart/condition`
  - `POST /v1/dignities/chart/profile`
  - `POST /v1/dignities/chart/network`
- Verification:
  - `tests/server/test_server_dignities_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-04 is admitted.

### P9-05 Lots

Status: `admitted`

Governing object:

- Classical Lots as doctrine-bound derived points, including dependency truth,
  local condition, chart profile, and dependency/network intelligence.

Evidence:

- Backend standard: `wiki/02_standards/LOTS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-05_LOTS_TRANSPORT_DESIGN.md`
- Engine module: `moira/lots.py`
- Public exports are present through `moira`, `moira.classical`, and
  `moira.facade`.
- Unit tests exist for public API and dignity/lots behavior.
- Server route tests exist: `tests/server/test_server_lots_routes.py`

REST admission notes:

- Lot formula doctrine and day/night reversal policy must remain explicit.
- Dependency truth should be preserved where exposed by the engine.
- Catalogue truth is a stable surface and should be exposed separately from
  computed chart results.
- First admission is chart-backed. The server owns planet, node, house, and
  day/night derivation through `ArabicPartsService`.
- Optional external support longitudes such as Syzygy, prenatal lunations, and
  Lord of Hour are caller-owned support truth in the first admission.
- Direct caller-owned lot bundles are deferred until a strict consistency
  contract exists for positions, houses, day/night state, externals, and
  policy.
- Live routes:
  - `GET /v1/lots/catalog`
  - `POST /v1/lots/chart`
  - `POST /v1/lots/chart/dependencies`
  - `POST /v1/lots/chart/conditions`
  - `POST /v1/lots/chart/condition`
  - `POST /v1/lots/chart/profile`
  - `POST /v1/lots/chart/network`
- Verification:
  - `tests/server/test_server_lots_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-05 is admitted.

### P9-06 Triplicity

Status: `admitted`

Governing object:

- Explicit triplicity doctrine and ruler assignment policy.

Evidence:

- Backend standard: `wiki/02_standards/TRIPLICITY_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-06_TRIPLICITY_TRANSPORT_DESIGN.md`
- Engine module: `moira/triplicity.py`
- Public exports are present through `moira`, `moira.classical`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_triplicity.py`
- Server route tests exist: `tests/server/test_server_triplicity_routes.py`

REST admission notes:

- This is a small direct-sync family.
- Participating-ruler policy and doctrine selection must be visible.
- Triplicity is a chart-free datum-provider module. First admission is
  direct-sync only and requires callers to supply `is_day_chart` explicitly.
- Live routes:
  - `GET /v1/triplicity/table`
  - `POST /v1/triplicity/assignment`
  - `POST /v1/triplicity/score`
- Verification:
  - `tests/server/test_server_triplicity_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-06 is admitted.

### P9-07 Egyptian Bounds

Status: `admitted`

Governing object:

- Egyptian bounds/terms as doctrine-bound sign subdivisions with host,
  classification, relation, condition, aggregate, and network surfaces.

Evidence:

- Backend standard: `wiki/02_standards/EGYPTIAN_BOUNDS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-07_EGYPTIAN_BOUNDS_TRANSPORT_DESIGN.md`
- Engine module: `moira/egyptian_bounds.py`
- Standard records phases P1-P12 complete.
- Unit tests exist for engine and public API behavior.
- Server route tests exist: `tests/server/test_server_egyptian_bounds_routes.py`

REST admission notes:

- This family should preserve segment truth separately from relation/profile
  products.
- Doctrine/policy selection must be explicit.
- First admission is direct-sync. The server consumes caller-supplied
  longitudes and optional sect/Mercury context; it does not derive chart
  positions.
- Live routes:
  - `GET /v1/egyptian-bounds/table`
  - `POST /v1/egyptian-bounds/bound`
  - `POST /v1/egyptian-bounds/classification`
  - `POST /v1/egyptian-bounds/relation`
  - `POST /v1/egyptian-bounds/condition`
  - `POST /v1/egyptian-bounds/aggregate`
  - `POST /v1/egyptian-bounds/network`
- Verification:
  - `tests/server/test_server_egyptian_bounds_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-07 is admitted.

### P9-08 Vedic Dignities

Status: `admitted`

Governing object:

- Vedic planetary dignity and planetary relationship condition profiles.

Evidence:

- Engine module: `moira/vedic_dignities.py`
- Backend standard: `wiki/02_standards/VEDIC_DIGNITIES_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-08_VEDIC_DIGNITIES_TRANSPORT_DESIGN.md`
- Public surfaces include `VedicDignityResult`, `VedicDignityPolicy`,
  `DignityConditionProfile`, `ChartDignityProfile`, and
  `validate_dignity_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_vedic_dignities.py`
- Server route tests exist: `tests/server/test_server_vedic_dignities_routes.py`

REST admission notes:

- First admission is direct-sync because `moira.vedic_dignities`
  consumes caller-supplied sidereal longitudes.
- The `ayanamsa_system` policy field records provenance for upstream sidereal
  reduction; the engine does not perform tropical-to-sidereal conversion.
- Chart-backed convenience routes are live after the post-Phase-9 shared
  adapter explicitly owns sidereal reduction and ayanamsa policy truth.
- Live routes:
  - `POST /v1/vedic-dignities/dignity`
  - `POST /v1/vedic-dignities/relationships`
  - `POST /v1/vedic-dignities/condition`
  - `POST /v1/vedic-dignities/chart-profile`
  - `POST /v1/vedic-dignities/chart/dignity`
  - `POST /v1/vedic-dignities/chart/relationships`
  - `POST /v1/vedic-dignities/chart/profile`
- Verification:
  - `tests/server/test_server_vedic_dignities_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-08 is admitted.

### P9-09 Ashtakavarga

Status: `admitted`

Governing object:

- Parashari Ashtakavarga rekha distribution, shodhana policy, sign strength,
  and chart profile.

Evidence:

- Engine module: `moira/ashtakavarga.py`
- Backend standard: `wiki/02_standards/ASHTAKAVARGA_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-09_ASHTAKAVARGA_TRANSPORT_DESIGN.md`
- Module docstring states Phase 12 public API curation and all twelve phases
  complete.
- Public surfaces include `AshtakavargaPolicy`, `BhinnashtakavargaResult`,
  `AshtakavargaResult`, `SignStrengthProfile`,
  `AshtakavargaChartProfile`, and `validate_ashtakavarga_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_ashtakavarga.py`

REST admission notes:

- First admission is direct-sync because `moira.ashtakavarga` consumes
  caller-supplied sidereal longitudes or sign indices.
- The `ayanamsa_system` policy field records provenance for upstream sidereal
  reduction; the engine does not perform tropical-to-sidereal conversion.
- Chart-backed convenience routes are live after the post-Phase-9 shared
  adapter explicitly owns sidereal reduction, Lagna derivation, and ayanamsa
  policy truth.
- Live routes:
  - `POST /v1/ashtakavarga/result`
  - `POST /v1/ashtakavarga/profile`
  - `POST /v1/ashtakavarga/sign-profile`
  - `POST /v1/ashtakavarga/transit-strength`
  - `POST /v1/ashtakavarga/chart/result`
  - `POST /v1/ashtakavarga/chart/profile`
  - `POST /v1/ashtakavarga/chart/sign-profile`
  - `POST /v1/ashtakavarga/chart/transit-strength`
- Verification:
  - `tests/server/test_server_ashtakavarga_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-09 is admitted.

### P9-10 Alternate Dasha Systems

Status: `admitted`

Governing object:

- Alternate dasha timing systems currently represented by Ashtottari and
  Yogini sequences, policies, period profiles, and sequence profiles.

Evidence:

- Engine module: `moira/dasha_systems.py`
- Backend standard: `wiki/02_standards/ALTERNATE_DASHAS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-10_ALTERNATE_DASHAS_TRANSPORT_DESIGN.md`
- Public surfaces include `ashtottari`, `yogini_dasha`,
  `AshtottariPolicy`, `YoginiPolicy`, `AlternateDashaPeriod`,
  `alternate_period_profile`, and `alternate_sequence_profile`.
- Public exports are present through `moira.vedic` and `moira.facade`.
- Unit test file exists: `tests/unit/test_dasha_systems.py`

REST admission notes:

- The current `wiki/02_standards/DASHA_BACKEND_STANDARD.md` remains
  Vimshottari-centered by design; alternate systems now have their own standard.
- First admission is direct computation from caller-supplied
  `moon_tropical_lon`, `natal_jd`, `levels`, and explicit policy.
- Chart-backed convenience routes are live after the post-Phase-9 shared
  adapter explicitly owns natal Moon derivation and policy provenance.
- Ashtottari transport must preserve current eligibility truth: full
  Rahu/Lagna eligibility checking is not implemented, so first admission should
  either require `bypass_eligibility=True` or expose the engine rejection for
  `lagna_sign_index` without bypass.
- Live routes:
  - `POST /v1/dasha/alternate/ashtottari/sequence`
  - `POST /v1/dasha/alternate/ashtottari/profile`
  - `POST /v1/dasha/alternate/ashtottari/chart/sequence`
  - `POST /v1/dasha/alternate/ashtottari/chart/profile`
  - `POST /v1/dasha/alternate/yogini/sequence`
  - `POST /v1/dasha/alternate/yogini/profile`
  - `POST /v1/dasha/alternate/yogini/chart/sequence`
  - `POST /v1/dasha/alternate/yogini/chart/profile`
  - `POST /v1/dasha/alternate/period-profile`
- Verification:
  - `tests/server/test_server_alternate_dashas_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-10 is admitted.

### P9-11 Varga

Status: `admitted`

Governing object:

- Vedic divisional chart placement for the Shodashvarga set.

Evidence:

- Engine module: `moira/varga.py`
- Backend standard: `wiki/02_standards/VARGA_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-11_VARGA_TRANSPORT_DESIGN.md`
- Public surfaces include `VargaPoint`, `calculate_varga`, and the named
  varga helpers.
- Public exports are present through `moira.vedic`, `moira.classical`, and
  `moira.facade`.
- Unit test files exist: `tests/unit/test_varga.py` and
  `tests/unit/test_shodashvarga.py`

REST admission notes:

- First admission is direct-sync because `moira.varga` consumes
  caller-supplied sidereal longitudes.
- REST must reject non-finite longitudes before calling the engine.
- The backend standard records that no dedicated `validate_varga_output(...)`
  helper is currently exposed; validation coverage is by vessel immutability,
  range tests, boundary tests, and wrapper-specific rule tests.
- Chart-backed convenience routes are live after the post-Phase-9 shared
  adapter explicitly owns tropical-to-sidereal reduction and ayanamsa policy
  truth.
- Live routes:
  - `POST /v1/varga/generic`
  - `POST /v1/varga/named`
  - `POST /v1/varga/shodashvarga`
  - `POST /v1/varga/named/batch`
  - `POST /v1/varga/shodashvarga/batch`
  - `POST /v1/varga/chart/named`
  - `POST /v1/varga/chart/shodashvarga`
  - `POST /v1/varga/chart/shodashvarga/batch`
- Verification:
  - `tests/server/test_server_varga_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-11 is admitted.

### P9-12 Decans / Decanates

Status: `admitted`

Governing object:

- Decan/decanate placement and related decan-hour/ruling-star surfaces.

Evidence:

- Backend standard: `wiki/02_standards/DECANS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P9-12_DECANS_TRANSPORT_DESIGN.md`
- Engine modules: `moira/decanates.py` and `moira/hermetic_decans.py`
- Public exports are present through `moira`, `moira.classical`, and
  `moira.facade`.
- Unit tests exist for decanates and Hermetic decans.

REST admission notes:

- Decanate placement and Hermetic decan-hour computation are distinct route
  families and must not be flattened into one generic decan product.
- First admission is direct-sync. Decanate routes consume caller-supplied
  longitude; Vedic drekkana additionally consumes JD and ayanamsa policy.
- Hermetic routes expose catalog, tropical longitude lookup, rising decan, and
  night-hour products.
- Chart-backed Decanates routes are live after the post-Phase-9 shared adapter
  owns body longitude derivation, sidereal reduction provenance, and chart
  policy truth. Hermetic routes remain direct because they are location/JD
  observational products rather than body-backed sidereal chart conveniences.
- Live routes:
  - `POST /v1/decanates/chaldean-face`
  - `POST /v1/decanates/triplicity`
  - `POST /v1/decanates/vedic-drekkana`
  - `POST /v1/decanates/set`
  - `POST /v1/decanates/chart/vedic-drekkana`
  - `POST /v1/decanates/chart/set`
  - `GET /v1/hermetic-decans/catalog`
  - `POST /v1/hermetic-decans/longitude`
  - `POST /v1/hermetic-decans/rising`
  - `POST /v1/hermetic-decans/night-hours`
- Verification:
  - `tests/server/test_server_decans_routes.py`
  - `tests/server/test_server_startup.py`
  - `tests/server/test_server_error_mapping.py`

Next action:

- P9-12 is admitted.

### P9-U1 Vedic Umbrella

Status: `exclude_from_rest`

Governing object:

- `moira.vedic` is a Python import aggregation surface over multiple Vedic
  doctrine families. It is not a single computational object.

Reason:

- `moira.vedic` is an import aggregation surface. Exposing it as one generic
  REST endpoint would collapse distinct doctrine families.
- Its exports include families with different input contracts: direct
  sidereal longitude surfaces, chart-backed surfaces, timing sequences,
  profile surfaces, and policy-bound strength calculations.
- A `/v1/vedic` route would either become an unsafe catch-all or would need to
  invent a new composite product not owned by the engine.

Required REST posture:

- Expose named families: Panchanga, Varga, Vedic dignities, Jaimini,
  Ashtakavarga, Shadbala, and alternate dasha systems.
- Preserve each named family's own route prefix, input contract, policy fields,
  and validation doctrine.
- Do not register:
  - `GET /v1/vedic`
  - `POST /v1/vedic`
  - any catch-all route under `/v1/vedic/*`

Verification:

- `tests/server/test_server_phase9_umbrella_exclusions.py`

### P9-U2 Classical Umbrella

Status: `exclude_from_rest`

Governing object:

- `moira.classical` is a Python import aggregation surface over traditional
  and classical astrology modules. It is not a single computational object.

Reason:

- `moira.classical` is an import aggregation surface. Exposing it as one
  generic REST endpoint would hide doctrine distinctions.
- Its exports span many different contracts: houses, aspects, dignities, lots,
  midpoints, antiscia, fixed stars, mansions, profections, planetary hours,
  longevity, time-lords, Vimshottari dasha, Varga, cycles, and Huber surfaces.
- A `/v1/classical` route would either become an unsafe catch-all or would
  invent a composite product not owned by the engine.

Required REST posture:

- Expose named families: Dignities, Lots, Triplicity, Egyptian bounds,
  decans/decanates, and other admitted classical subsurfaces.
- Preserve each named family's own route prefix, input contract, policy fields,
  and validation doctrine.
- Do not register:
  - `GET /v1/classical`
  - `POST /v1/classical`
  - any catch-all route under `/v1/classical/*`

Verification:

- `tests/server/test_server_phase9_umbrella_exclusions.py`

---

## 5. Recommended Phase 9 Order

Recommended order after this initial evaluation:

1. Panchanga - smallest high-value doctrinal route family with complete standard
2. Triplicity - small direct-sync classical route family to prove classical pattern
3. Shadbala - larger chart-backed Vedic family
4. Jaimini - bounded chart-backed Vedic family
5. Classical dignities and Lots - likely share chart-backed inputs
6. Egyptian bounds - explicit doctrine and condition/profile family
7. Minor-engine-work families after remediation:
   - Vedic dignities
   - Ashtakavarga
   - Varga
   - alternate dasha systems
   - decans/decanates

This order is not a claim of doctrine importance. It is a transport-risk order:
start with bounded families whose standards are already complete, then widen to
larger or less documented surfaces.

---

## 6. Immediate Next Step

All named Phase 9 candidate families in this ledger are admitted.

Remaining Phase 9 umbrella modules, `moira.vedic` and `moira.classical`, remain
excluded from REST as aggregation surfaces. Future route work should proceed
from a new candidate ledger or the next numbered server phase rather than
creating generic umbrella endpoints.

Post-Phase-9 workflow addition:

- `docs/architecture/POST_PHASE9_SIDEREAL_CHART_DERIVATION_WORKFLOW.md`

This workflow should precede deferred chart-backed convenience variants for
direct-sync Vedic/classical families. It defines the request-scoped
`SiderealChartContext` adapter needed for the server to own sidereal reduction,
Lagna derivation, node truth, and ayanamsa provenance without global state.
