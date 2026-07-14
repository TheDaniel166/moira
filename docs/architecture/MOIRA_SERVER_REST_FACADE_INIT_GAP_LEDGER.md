# Moira Server REST / Facade / Init Gap Ledger

Version: 1.0
Date: 2026-06-15
Status: code-truth comparison updated through P-GAP-F1D utility parity cleanup
Scope: live FastAPI route registry compared against `Moira` facade methods and
root `moira.__all__` exports

This ledger is a code-truth audit. It compares runtime surfaces, not the REST
reference prose:

- FastAPI routes registered by `moira_server.app.create_app()`
- public callable methods on `moira.facade.Moira`
- root exports declared by `moira.__all__`

The comparison does not assume that every facade method or root export should
become a REST route. Root exports include constants, policy vessels, response
vessels, classes, low-level astronomy helpers, and validation helpers. Those
must remain engine/import truth unless they have a clear public transport
contract.

---

## 1. Runtime Inventory

Observed through `.venv` on 2026-06-15:

- registered `/v1` routes: `342`
- documented route groups: `71`
- public `Moira` facade methods: `182`
- root `moira.__all__` exports: `364`
- root function exports: `136`
- root class exports: `183`
- other root exports: `45`

Documented route-group count:

| Family | Routes |
|---|---:|
| antiscia | 3 |
| ashtakavarga | 8 |
| asteroids | 9 |
| astrocartography | 4 |
| batch | 7 |
| chart | 2 |
| chart-shape | 1 |
| comets | 3 |
| composite | 1 |
| dasha | 14 |
| davison | 1 |
| decanates | 6 |
| dignities | 6 |
| eclipses | 5 |
| egyptian-bounds | 7 |
| electional | 6 |
| galactic | 6 |
| galactic-houses | 3 |
| gauquelin | 3 |
| geodetic | 4 |
| harmograms | 5 |
| harmonics | 9 |
| heliacal | 2 |
| hermetic-decans | 4 |
| houses | 2 |
| huber | 6 |
| jaimini | 8 |
| local-space | 2 |
| locations | 2 |
| lord-of-the-orb | 2 |
| lord-of-the-turn | 1 |
| lots | 7 |
| lunar-phases | 1 |
| manazil | 4 |
| midpoints | 5 |
| muhurta | 4 |
| nakshatra | 2 |
| nine-parts | 1 |
| nodes | 4 |
| occultations | 8 |
| orbits | 2 |
| panchanga | 4 |
| parans | 8 |
| patterns | 3 |
| phase | 6 |
| phenomena | 3 |
| pipeline | 3 |
| planetary-hours | 2 |
| positions | 4 |
| positions-frame | 4 |
| primary-directions | 8 |
| profections | 3 |
| progressions | 17 |
| returns | 3 |
| rise-set | 3 |
| shadbala | 4 |
| sidereal | 3 |
| solar-condition | 2 |
| stars | 12 |
| stations | 4 |
| synastry | 9 |
| timelords | 16 |
| transits | 3 |
| triplicity | 3 |
| uranian | 3 |
| varga | 8 |
| varshaphal | 9 |
| vedic-dignities | 7 |
| visibility | 2 |
| void-of-course | 4 |
| website | 3 |

---

## 2. Classification Rules

Every mismatch is classified as one of:

- `rest_candidate` - facade or root computation appears stable enough to
  evaluate for public transport.
- `rest_candidate_after_standard` - computation exists, but needs a backend
  standard or transport design before route work.
- `defer_for_doctrine` - public semantics could overstate doctrine or expose
  high-stakes interpretive material.
- `defer_for_specialist_review` - computation is specialist enough that route
  admission needs explicit review.
- `engine_only` - root export or facade helper should remain Python/import
  surface rather than HTTP.
- `facade_gap` - REST family is live, but there is no matching high-level
  `Moira` convenience method.
- `documentation_only` - mismatch is caused by route aliases, naming, or
  reference wording rather than missing runtime behavior.

---

## 3. Highest-Signal REST Candidates

These are the cleanest candidates if the next work is to close gaps from
facade/root computation into REST.

| Gap | Source surface | Current REST truth | Status | Admission note |
|---|---|---|---|---|
| Frame-specific position products | `Moira.heliocentric`, `Moira.planetocentric`, `Moira.ssb_chart`, `Moira.received_light` | `/v1/positions/frame/*` now exposes heliocentric, planetocentric, SSB, and received-light products | `admitted` | Implemented as a transport adapter over existing engine/facade computations; no engine modules changed. |
| Muhurta | `classify_muhurta`, `score_muhurta` in `moira.__all__` | `/v1/muhurta/*` now exposes direct/chart-backed classification and raw-score routes | `admitted` | Implemented after local Nakshatra classification hardening; transport exposes only honored score-weight policy fields and remains distinct from `/v1/electional/*`. |
| Orbital elements and distance extrema | `orbital_elements_at`, `distance_extremes_at` | `/v1/orbits/*` now exposes orbital elements and distance extrema | `admitted` | Implemented as a transport adapter preserving heliocentric J2000 osculating semantics, distance-extrema curve-event semantics, and Horizons validation authority. |
| Generic phenomena and proximity events | `Moira.phenomena`, `Moira.proximity_events`, `planet_phenomena_at`, `proximity_events_in_range` | `/v1/phenomena/*` now exposes instant planet phenomena, bounded orbital events, and proximity threshold events | `admitted` | Implemented as a bounded transport adapter that preserves instant snapshot, orbital-event, and proximity-threshold semantics without flattening them into a catch-all event route. |
| Solar condition direct/events | `Moira.solar_condition_at`, `Moira.solar_condition_events`, root solar-condition helpers | `/v1/solar-condition/*` now exposes instant solar-condition truth and bounded solar-condition threshold events | `admitted` | Implemented as a bounded transport adapter that keeps classical solar-condition threshold truth separate from dignity interpretation and recommendation language. |
| Sidereal utilities / Nakshatra primitives | `Moira.ayanamsa`, `Moira.tropical_to_sidereal`, `Moira.sidereal_to_tropical`, `Moira.list_ayanamsa_systems`, `Moira.nakshatras`, root Nakshatra helpers | `/v1/sidereal/*` and `/v1/nakshatra/*` now expose ayanamsa registry/value, longitude conversion, and Nakshatra lookup primitives | `admitted` | Implemented as a mechanical primitive layer for ayanamsa, zodiac conversion, and Nakshatra lookup without duplicating Panchanga or Varga doctrine; facade utility parity is now admitted for direct ayanamsa and conversion helpers. |
| Harmograms | `point_set_harmonic_vector`, `zero_aries_parts_harmonic_vector`, `intensity_function_spectrum`, `project_harmogram_strength`, `harmogram_trace` | `/v1/harmograms/*` now exposes bounded vector, Zero-Aries vector, intensity-spectrum, projection, and explicit-sample trace routes | `admitted` | Implemented as a bounded transport adapter over `moira.harmograms`; chart-backed sample generation, arbitrary intensity functions, unbounded sweeps, and interpretation remain out of scope. |
| Ramesey Western electional moment | `ramesey_moon_condition_at`, `Moira.ramesey_moon_condition_at` | `/v1/electional/western/ramesey-moon-condition` exposes one typed ten-rule evaluation | `admitted_bounded_moment` | Preserves full rule, clause, measurement, remedy, house, and reader provenance; generic search/scoring, advice, recommendation, and remedy-fulfillment assessment remain out of scope. |

---

## 4. Deliberate Holds

These are real facade/root gaps, but should not be admitted merely because the
code exists.

| Gap | Source surface | Status | Reason |
|---|---|---|---|
| Longevity / Hyleg-Alcocoden | `Moira.longevity`, longevity root surfaces | `defer_for_doctrine` | High-stakes interpretive family; public route must not imply life-expectancy prediction or advice. |
| Sothic and Egyptian civil date | `Moira.sothic_cycle`, `Moira.sothic_epoch_finder`, `Moira.egyptian_date` | `defer_for_specialist_review` | Specialist surface; previous Phase 12 decision deliberately withheld REST admission. |
| Western electional generic search/scoring | P13-U1 | `defer_for_transport_and_doctrine` | The Ramesey v1 single-moment route is admitted; generic profile scanning, scoring, ranking, advice, recommendation, and later profiles require separate admission. |
| Arbitrary executable electional predicates/scorers | facade `electional_windows` accepts Python predicate | `engine_only` | REST must use server-defined profile catalogues only. |
| Kernel mutation and downloads | `configure_kernel_path`, `download_missing_kernels`, `load_small_body_manifest` | `engine_only` | Operational mutation should not become ordinary public compute transport. |

---

## 5. Facade Parity Gaps

These route families are live in REST. Some now have high-level `Moira`
facade convenience methods; the remainder are still facade ergonomics gaps if
the Python facade is intended to mirror admitted REST families.

| REST family | Routes | Status | Note |
|---|---:|---|---|
| `panchanga` | 4 | `facade_admitted` | Implemented in `VedicFacadeMixin`; direct root computation and chart-backed convenience remain distinct. |
| `shadbala` | 4 | `facade_admitted` | Implemented in `VedicFacadeMixin`; result/profile wrappers delegate without duplicating Shadbala doctrine. |
| `jaimini` | 8 | `facade_admitted` | Implemented in `VedicFacadeMixin`; karaka/profile/pair convenience wrappers delegate to existing root functions. |
| `ashtakavarga` | 8 | `facade_admitted` | Implemented in `VedicFacadeMixin`; result/profile/sign/transit wrappers delegate without route envelopes. |
| `varga` | 8 | `facade_admitted` | Implemented in `VedicFacadeMixin`; generic/named/Shodashvarga convenience wrappers avoid route-envelope return types. |
| `huber` | 6 | `facade_admitted` | Implemented in `ClassicalFacadeMixin` as direct-cusp `huber_*` wrappers; chart-backed house derivation remains out of scope. |
| `nine-parts` | 1 | `facade_admitted` | Implemented in `ClassicalFacadeMixin` as `nine_parts(...)`, delegating to `nine_parts_abu_mashar`. |
| `lord-of-the-orb` | 2 | `facade_admitted` | Implemented in `AnnualLordFacadeMixin` as `lord_of_orb(...)` and `current_lord_of_orb(...)`; birth planetary-hour ruler truth remains caller-supplied. |
| `lord-of-the-turn` | 1 | `defer_for_api_design` | Annual-lord facade admission should be reviewed with Varshaphal/Tajika policy truth. |
| `sidereal` / `nakshatra` utilities | 5 total | `facade_admitted` | Direct ayanamsa registry/value and sidereal conversion utilities are implemented in `VedicFacadeMixin`; `Moira.nakshatras(chart)` already existed for chart-backed Nakshatra lookup. |
| `pipeline` | 3 | `rest_only` | REST-only reduction/pipeline inspection aliases; not a high-level `Moira` method obligation. |
| `website` | 3 | `rest_only` | Website chart-wheel packet support; not an engine-level convenience method. |
| `locations` | 2 | `rest_only` | Server/UI lookup support; do not import location data authority into the core facade casually. |
| `asteroids` / `comets` selected routes | 12 total | `partial_facade_gap` | Engine/root exports exist; REST has website-oriented list/bulk/subset/family shapes beyond facade convenience. |

---

## 6. Root Export Categories That Should Stay Engine-Only

The following root export categories should not become REST routes without a
specific admission packet:

- constants and doctrine tables
- dataclasses and response vessels
- policy classes
- validation helpers such as `validate_*_output`
- direct mathematical primitives whose only safe public use is inside a
  higher-level admitted route
- package operational helpers that mutate kernel state or local resources
- low-level time-scale conversions unless a dedicated utility route family is
  explicitly admitted

Examples:

- `julian_day`, `datetime_from_jd`, `delta_t_from_jd`, and sidereal-time
  helpers are valid root exports but not automatically public REST products.
- dignity helpers like `is_in_sect`, `is_in_hayz`, `is_in_joy`, and
  `is_besieged` are better exposed through dignity/profile/condition routes
  unless a direct classical-primitive route family is designed.
- `validate_*_output` helpers are verification tools, not public compute
  products.

---

## 7. Candidate Follow-Up Order

Recommended order if we continue closing code-truth gaps:

1. `P-GAP-01` Frame-Specific Positions
   - heliocentric, planetocentric, SSB, and received-light position products
   - backend standard: `wiki/02_standards/FRAME_SPECIFIC_POSITIONS_BACKEND_STANDARD.md`
   - transport design: `docs/architecture/P-GAP-01_FRAME_SPECIFIC_POSITIONS_TRANSPORT_DESIGN.md`
   - status: admitted through `/v1/positions/frame/*`
   - verification: focused server route tests, compile check, and route
     registry audit

2. `P-GAP-02` Muhurta
   - direct classification and score surface
   - must remain distinct from Western electional search/scoring
   - backend standard: `wiki/02_standards/MUHURTA_BACKEND_STANDARD.md`
   - transport design: `docs/architecture/P-GAP-02_MUHURTA_TRANSPORT_DESIGN.md`
   - status: admitted through `/v1/muhurta/*`
   - verification: Muhurta unit tests, focused server route tests, compile
     check, and route registry audit

3. `P-GAP-03` Orbital Elements
   - orbital elements and distance extrema
   - astronomical substrate surface; provenance and element semantics must be
     explicit
   - backend standard: `wiki/02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md`
   - transport design: `docs/architecture/P-GAP-03_ORBITAL_ELEMENTS_TRANSPORT_DESIGN.md`
   - status: admitted through `/v1/orbits/*`
   - verification: focused server route tests, compile check, and route
     registry audit

4. `P-GAP-04` Generic Phenomena And Solar Conditions
   - greatest elongation/perihelion/aphelion/proximity/solar condition
   - requires careful event taxonomy
   - backend standard: `wiki/02_standards/GENERIC_PHENOMENA_SOLAR_CONDITIONS_BACKEND_STANDARD.md`
   - transport design: `docs/architecture/P-GAP-04_GENERIC_PHENOMENA_SOLAR_CONDITIONS_TRANSPORT_DESIGN.md`
   - status: admitted through `/v1/phenomena/*` and `/v1/solar-condition/*`
   - verification: focused server route tests, compile check, and route
     registry audit

5. `P-GAP-05` Sidereal/Nakshatra Utility Primitives
   - ayanamsa, zodiac conversion, nakshatra lookup
   - should remain mechanical and not duplicate Panchanga judgement
   - backend standard: `wiki/02_standards/SIDEREAL_NAKSHATRA_UTILITY_BACKEND_STANDARD.md`
   - transport design: `docs/architecture/P-GAP-05_SIDEREAL_NAKSHATRA_UTILITY_TRANSPORT_DESIGN.md`
   - status: admitted through `/v1/sidereal/*` and `/v1/nakshatra/*`
   - verification: focused server route tests, compile check, and route
     registry audit

6. `P-GAP-06` Harmograms
   - bounded trace/intensity products
   - backend standard: `wiki/02_standards/HARMOGRAMS_BACKEND_STANDARD.md`
   - transport design: `docs/architecture/P-GAP-06_HARMOGRAMS_TRANSPORT_DESIGN.md`
   - status: admitted through `/v1/harmograms/*`
   - verification: focused server route tests, compile check, and route
     registry audit

7. `P-GAP-F1` Facade Parity Review
   - decide whether REST-admitted families should receive `Moira` convenience
     methods, especially Panchanga, Shadbala, Jaimini, Varga, Ashtakavarga,
     Huber, Lord of the Orb, and specialist annual-lord routes
   - review document: `docs/architecture/P-GAP-F1_FACADE_PARITY_REVIEW.md`
   - status: decision complete; P-GAP-F1A Vedic, P-GAP-F1B
     classical/modern, P-GAP-F1C annual-lord specialist, and P-GAP-F1D
     utility parity bundles implemented
   - no additional facade bundle is currently recommended without a new
     explicit admission decision

---

## 8. Non-Goals

This ledger does not:

- admit any additional route beyond the named admitted gap bundles and the
  P13-U1 Ramesey v1 single-moment route
- widen `moira.__all__` beyond the explicitly admitted Ramesey v1 surface
- reopen remaining facade bundles without explicit API-change approval
- admit Lord of the Turn into the facade without separate annual-chart API
  design
- imply that root exports are route obligations
- reopen Sothic, Longevity, or generic Western electional search/scoring
- turn operational kernel mutation into HTTP compute
- replace family-specific route designs with a generic catch-all route

---

## 9. Immediate Next Step

`P-GAP-01` Frame-Specific Positions, `P-GAP-02` Muhurta, `P-GAP-03`
Orbital Elements, `P-GAP-04` Generic Phenomena And Solar Conditions,
`P-GAP-05` Sidereal/Nakshatra Utility Primitives, `P-GAP-06` Harmograms,
`P-GAP-F1A` Vedic facade convenience, `P-GAP-F1B` Classical/modern facade
convenience, `P-GAP-F1C` Annual-lord specialist facade convenience, and
`P-GAP-F1D` Utility parity cleanup are admitted. P13-U1 separately admits the
Ramesey v1 bounded single-moment root/facade/REST surface.

There is no remaining automatic implementation candidate from P-GAP-F1.
The review is complete in
`docs/architecture/P-GAP-F1_FACADE_PARITY_REVIEW.md`; P-GAP-F1A added
Panchanga, Shadbala, Jaimini, Ashtakavarga, and Varga convenience methods,
P-GAP-F1B added direct-cusp Huber and Nine Parts convenience methods, and
P-GAP-F1C added Lord of the Orb convenience methods while preserving the
caller-supplied birth planetary-hour ruler boundary. P-GAP-F1D added direct
ayanamsa and sidereal conversion utilities. Website, locations, pipeline
support, rendering support, and Lord of the Turn remain outside this facade
admission.
