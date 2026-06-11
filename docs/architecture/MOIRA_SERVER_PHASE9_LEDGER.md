# Moira Server Phase 9 Ledger

Version: 0.1
Date: 2026-06-11
Status: P9-01 Panchanga, P9-02 Shadbala, P9-03 Jaimini, and P9-04 Classical Dignities admitted; remaining Phase 9 families under evaluation
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
| P9-05 | Lots | `designed` | Phase 11 backend standard, doctrine/policy/dependency/profile surfaces, facade/root exports, tests, and a chart-backed transport design exist. |
| P9-06 | Triplicity | `admit_now` | Phase 11/12 backend standard, explicit doctrine and policy surfaces, facade/root exports, and tests exist. |
| P9-07 | Egyptian bounds | `admit_now` | Backend standard says phases P1-P12 complete, public vessels/functions and tests exist. |
| P9-08 | Vedic dignities | `admit_after_minor_engine_work` | Engine surface, policy/profile vessels, validation helper, exports, and tests exist; a dedicated backend-standard document is not present. |
| P9-09 | Ashtakavarga | `admit_after_minor_engine_work` | Engine docstring says Phase 12 complete with policy/profile/validation surfaces; tests and exports exist; a dedicated backend-standard document is not present. |
| P9-10 | Alternate dasha systems | `admit_after_minor_engine_work` | Ashtottari/Yogini surfaces, policies, profiles, exports, and tests exist; the current Dasha standard is Vimshottari-centered and does not yet provide a dedicated alternate-dasha REST admission standard. |
| P9-11 | Varga | `admit_after_minor_engine_work` | Engine and tests exist, but no backend-standard document is present and `VargaPoint` declares immutable state in its machine contract while the dataclass is not frozen. |
| P9-12 | Decans / decanates | `admit_after_minor_engine_work` | Public engine surfaces and tests exist, but no dedicated backend-standard document was found for decan transport admission. |
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

Status: `designed`

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
- Planned routes:
  - `GET /v1/lots/catalog`
  - `POST /v1/lots/chart`
  - `POST /v1/lots/chart/dependencies`
  - `POST /v1/lots/chart/conditions`
  - `POST /v1/lots/chart/condition`
  - `POST /v1/lots/chart/profile`
  - `POST /v1/lots/chart/network`

Next action:

- Implement the chart-backed P9-05 service, models, serializers, router, tests,
  and REST reference entries.

### P9-06 Triplicity

Status: `admit_now`

Governing object:

- Explicit triplicity doctrine and ruler assignment policy.

Evidence:

- Backend standard: `wiki/02_standards/TRIPLICITY_BACKEND_STANDARD.md`
- Engine module: `moira/triplicity.py`
- Public exports are present through `moira`, `moira.classical`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_triplicity.py`

REST admission notes:

- This is a small direct-sync family.
- Participating-ruler policy and doctrine selection must be visible.

Next action:

- Good candidate for a small Phase 9 route after Panchanga proves the pattern.

### P9-07 Egyptian Bounds

Status: `admit_now`

Governing object:

- Egyptian bounds/terms as doctrine-bound sign subdivisions with host,
  classification, relation, condition, aggregate, and network surfaces.

Evidence:

- Backend standard: `wiki/02_standards/EGYPTIAN_BOUNDS_BACKEND_STANDARD.md`
- Engine module: `moira/egyptian_bounds.py`
- Standard records phases P1-P12 complete.
- Unit tests exist for engine and public API behavior.

REST admission notes:

- This family should preserve segment truth separately from relation/profile
  products.
- Doctrine/policy selection must be explicit.

Next action:

- Admit after the smaller direct-sync route pattern is established.

### P9-08 Vedic Dignities

Status: `admit_after_minor_engine_work`

Governing object:

- Vedic planetary dignity and planetary relationship condition profiles.

Evidence:

- Engine module: `moira/vedic_dignities.py`
- Public surfaces include `VedicDignityResult`, `VedicDignityPolicy`,
  `DignityConditionProfile`, `ChartDignityProfile`, and
  `validate_dignity_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_vedic_dignities.py`

Gap:

- No dedicated `wiki/02_standards/*VEDIC_DIGNITIES*_BACKEND_STANDARD.md` file
  was found.

Required minor work before REST:

- Add a backend-standard document or explicitly admit Vedic dignities under an
  existing Vedic standard.
- Reconfirm validation commands and public surface freeze in that document.

### P9-09 Ashtakavarga

Status: `admit_after_minor_engine_work`

Governing object:

- Parashari Ashtakavarga rekha distribution, shodhana policy, sign strength,
  and chart profile.

Evidence:

- Engine module: `moira/ashtakavarga.py`
- Module docstring states Phase 12 public API curation and all twelve phases
  complete.
- Public surfaces include `AshtakavargaPolicy`, `BhinnashtakavargaResult`,
  `AshtakavargaResult`, `SignStrengthProfile`,
  `AshtakavargaChartProfile`, and `validate_ashtakavarga_output`.
- Public exports are present through `moira`, `moira.vedic`, and
  `moira.facade`.
- Unit test file exists: `tests/unit/test_ashtakavarga.py`

Gap:

- No dedicated backend-standard document was found in `wiki/02_standards`.

Required minor work before REST:

- Add `ASHTAKAVARGA_BACKEND_STANDARD.md` or equivalent standard record before
  route design.

### P9-10 Alternate Dasha Systems

Status: `admit_after_minor_engine_work`

Governing object:

- Alternate dasha timing systems currently represented by Ashtottari and
  Yogini sequences, policies, period profiles, and sequence profiles.

Evidence:

- Engine module: `moira/dasha_systems.py`
- Public surfaces include `ashtottari`, `yogini_dasha`,
  `AshtottariPolicy`, `YoginiPolicy`, `AlternateDashaPeriod`,
  `alternate_period_profile`, and `alternate_sequence_profile`.
- Public exports are present through `moira.vedic` and `moira.facade`.
- Unit test file exists: `tests/unit/test_dasha_systems.py`

Gap:

- The current `wiki/02_standards/DASHA_BACKEND_STANDARD.md` is centered on
  Vimshottari. It does not yet act as a clear admission standard for the
  alternate systems.

Required minor work before REST:

- Add an alternate-dasha standard section or separate backend-standard document
  before exposing `/v1/dasha/ashtottari/*` or `/v1/dasha/yogini/*`.

### P9-11 Varga

Status: `admit_after_minor_engine_work`

Governing object:

- Vedic divisional chart placement for the Shodashvarga set.

Evidence:

- Engine module: `moira/varga.py`
- Public surfaces include `VargaPoint`, `calculate_varga`, and the named
  varga helpers.
- Public exports are present through `moira.vedic`, `moira.classical`, and
  `moira.facade`.
- Unit test files exist: `tests/unit/test_varga.py` and
  `tests/unit/test_shodashvarga.py`

Gaps:

- No dedicated backend-standard document was found in `wiki/02_standards`.
- `VargaPoint` declares immutable state in its machine contract, but the
  dataclass is not declared `frozen=True`.
- No dedicated validation helper was found in the first audit pass.

Required minor work before REST:

- Make the vessel contract and dataclass mutability agree.
- Add a backend-standard document.
- Decide whether a validation helper is required before public transport.

### P9-12 Decans / Decanates

Status: `admit_after_minor_engine_work`

Governing object:

- Decan/decanate placement and related decan-hour/ruling-star surfaces.

Evidence:

- Engine modules: `moira/decanates.py` and `moira/hermetic_decans.py`
- Public exports are present through `moira`, `moira.classical`, and
  `moira.facade`.
- Unit tests exist for decanates and Hermetic decans.

Gap:

- No dedicated backend-standard document was found for REST admission.

Required minor work before REST:

- Add or locate the backend standard before deciding route shape.

### P9-U1 Vedic Umbrella

Status: `exclude_from_rest`

Reason:

- `moira.vedic` is an import aggregation surface. Exposing it as one generic
  REST endpoint would collapse distinct doctrine families.

Required REST posture:

- Expose named families: Panchanga, Varga, Vedic dignities, Jaimini,
  Ashtakavarga, Shadbala, and alternate dasha systems.

### P9-U2 Classical Umbrella

Status: `exclude_from_rest`

Reason:

- `moira.classical` is an import aggregation surface. Exposing it as one
  generic REST endpoint would hide doctrine distinctions.

Required REST posture:

- Expose named families: Dignities, Lots, Triplicity, Egyptian bounds,
  decans/decanates, and other admitted classical subsurfaces.

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

Begin P9-01 Panchanga REST design only if the user confirms that Panchanga is
the desired first Phase 9 route family.

If the user wants the cleanest pre-admission closure first, perform the minor
engine/doc hardening for P9-11 Varga before any route work, because the
machine-contract immutability mismatch is a concrete truth issue.
