# Swiss Ephemeris Extensibility Roadmap

This document turns the Swiss-to-Moira parity analysis into an extendible
execution roadmap.

Last reviewed:
- 2026-04-04 (Phase 5 / V6-partial complete)

Inputs:
- [`SWISS_EPHEMERIS_SYMBOL_TABLE.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SWISS_EPHEMERIS_SYMBOL_TABLE.md)
- [`SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md)
- [`REPOSITORY_ASSESSMENT.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/REPOSITORY_ASSESSMENT.md)
- [`00_SUBSYSTEM_CONSTITUTIONALIZATION_PROCESS.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/00_SUBSYSTEM_CONSTITUTIONALIZATION_PROCESS.md)

This is not a parity promise. It is a doctrine for deciding which Swiss
surfaces should become first-class Moira surfaces, which should wait for a
better subsystem design, and which should remain out of scope permanently.

## Why Now

This work is worth doing now for four reasons:

- The Swiss symbol accounting is finally explicit.
  We now know exactly which Swiss surfaces are already covered, which are only
  API-shape equivalents, and which still have no public Moira surface.

- Validation maturity is high enough to support careful expansion.
  Astronomy and astrology validation are no longer vague enough that every new
  surface would be built on sand. The remaining work is selective extension, not
  basic legitimacy.

- The migration story is currently strongest at the inventory layer, not the
  implementation layer.
  We can now say what is missing. The next useful step is to decide what should
  be added first and under what doctrine.

- The repository already has constitutional entry points for the deferred families.
  We no longer need to guess where these additions belong architecturally.

## Current Totals

From [`SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md):

- Total `none` rows: `239`
- `Implement`: `26`
- `Defer`: `134`
- `Reject`: `79`

## Current Repository Context

Since the initial drafting of this roadmap, Moira has added several
Moira-native layers that affect extensibility decisions even though they are
not Swiss-parity targets in themselves:

- a full `moira.harmograms` subsystem with explicit spectral, intensity,
  projection, and trace strata
- a `moira.bridges.harmograms` adaptation layer for native chart/progression
  inputs, body filtering, and datetime-range sampling
- selective root-level exports from `moira.__init__` for stable harmograms
  computation surfaces

This matters here for one reason:

- Swiss parity work must not flatten Moira-native engine layering back into
  Swiss-shaped convenience surfaces.

In particular, when a family already has:
- an explicit mathematical engine layer
- an adaptation or bridge layer
- and a selective package-root surface

this roadmap should treat that as a sign of architectural maturity, not as an
invitation to add facade-first or service-first parity wrappers.

## Decision Model

- `Implement`
  The capability is worth adding to Moira in a typed, Moira-shaped form.

- `Defer.Design`
  The domain is real, but the correct Moira-shaped subsystem or policy surface
  does not exist yet.

- `Defer.Validation`
  The domain is real, but the public surface should wait until an oracle or
  stronger validation story exists.

- `Defer.Doctrine`
  The domain is real, but the doctrinal/model-basis choice is not yet locked.

- `Reject`
  The symbol is Swiss-internal, low-value, or contrary to Moira API design.

## Design Rules

- Do not mirror Swiss integer flags when a typed option object is clearer.
- Do not mirror Swiss global mutable state.
- Do not expose Swiss file-path, backend, or library-control constants.
- Prefer typed policies over compatibility booleans.
- Prefer one mathematically explicit helper over many selector constants.
- Add migration notes, not Swiss-shaped API debt.
- When a deferred family already has an constitutional process parent subsystem, route the work
  through that subsystem instead of creating a detached helper API.
- Do not let Swiss parity pressure Moira-native engine/bridge layering into a
  workflow or service surface when the engine itself does not require one.

## Real Blockers

These are the actual blockers, not vague "future work" language.

### Blocker A: missing typed policy surfaces

Examples:
- rise/set doctrine selectors
- position-computation switches
- model-basis controls

Consequence:
- if implemented too early, these become Swiss-style flag clutter rather than
  stable Moira doctrine.

### Blocker B: missing public low-level helper surfaces

Examples:
- reverse horizontal transforms
- speed-aware coordinate transforms
- ARMC house helpers
- relative-center position helpers

Consequence:
- migration gaps remain even when the underlying math already exists in the
  codebase.

### Blocker C: missing validation story for a public surface

Examples:
- generalized heliacal/visibility options
- eclipse or occultation path helpers
- orbital-elements public layer

Consequence:
- public API would appear more mature than its validation basis.

### Blocker D: unresolved doctrinal packaging

Examples:
- user-defined and additional ayanamsas
- tidal acceleration / precession / nutation policy exposure
- house dynamics / cusp speeds

Consequence:
- we would expose Swiss-like knobs without first deciding what Moira believes
  those knobs mean.

## Constitutional Entry Points For Deferred Families

These families should not be treated as isolated helper additions. They already
have natural entry points in the repo.

| Deferred family | Defer kind | constitutional entry point | Reason |
| --- | --- | --- | --- |
| generalized heliacal / visibility model | `Implemented.V0–V5` + `Active.V6` | [`moira/heliacal.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/heliacal.py), [`moira/stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py), [`STARS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/STARS_BACKEND_STANDARD.md) | V0–V5 complete: observer-environment policy, generalized event search, Yallop corpus (295/295), public surface widened; V6 partial: K&S 1991 moonlight and stellar catalog batch admitted |
| model-basis controls (`DeltaT`, precession, nutation, tidal acceleration) | `Defer.Doctrine` | [`julian.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/julian.py), [`corrections.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/corrections.py), [`DELTA_T_HYBRID_MODEL.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/DELTA_T_HYBRID_MODEL.md) | these are foundational astronomy policy choices, not Swiss option constants |
| additional ayanamsa constants / user-defined ayanamsa | `Defer.Doctrine` | [`sidereal.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/sidereal.py) | ayanamsa expansion belongs in one coherent sidereal doctrine layer |
| eclipse / occultation path helpers | `Active.Design` + `Active.Validation` | [`eclipse.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse.py), [`ECLIPSE_MODEL_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/ECLIPSE_MODEL_STANDARD.md), [`occultations.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/occultations.py), [`ANCIENT_OCCULTATION_VALIDATION_PROGRAM.md`](c:/Users/nilad/OneDrive/Desktop/Moira/wiki/03_validation/ANCIENT_OCCULTATION_VALIDATION_PROGRAM.md) | modern/future path geometry is active and externally validated; ancient occultations belong to a separate historical-validation program |
| orbital-elements public layer | `Implemented` | [`moira/orbits.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/orbits.py), [`moira/__init__.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/__init__.py) | `KeplerianElements`, `DistanceExtremes`, `orbital_elements_at`, `distance_extremes_at` implemented Phase 4; wired into top-level namespace |
| house dynamics / cusp-speed layer | `Implemented` | [`houses.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/houses.py), [`HOUSES_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/HOUSES_BACKEND_STANDARD.md) | implemented in Moira form as `HouseDynamics`, including both `cusp_speeds_at(...)` and `house_dynamics_from_armc(...)` rather than Swiss-style auxiliary tuples |

## Scope Boundary

This roadmap governs:
- Swiss-to-Moira capability migration
- deferred family constitutionalization where Swiss parity reveals a real gap
- public engine surfaces that should exist regardless of Swiss naming

This roadmap does not govern:
- Moira-native service or workflow orchestration
- facade-first convenience layers added only to imitate Swiss usage style
- product ergonomics that are not required for engine truth or migration value

If a candidate addition primarily answers:
- "how should a user orchestrate this workflow?"

rather than:
- "what engine capability is missing or not yet typed?"

it belongs outside this document.

## Phase 1

### Goal

Close the highest-value astronomy migration gaps with low API ambiguity.

### Why now

- these are the most migration-relevant missing astronomy surfaces
- they do not require a brand-new subsystem constitution
- most of them already sit on top of existing validated math

### Real blockers

- typed option surfaces are still missing
- some underlying computations exist but are not publicly exposed

### Atomic backlog

#### Position switches

- [x] Add `planet_at(..., apparent=False)` as the public astrometric / true-position switch
- [x] Add `planet_at(..., aberration=False)`
- [x] Add `planet_at(..., grav_deflection=False)`
- [x] Add `planet_at(..., nutation=False)`
- [x] Add `planet_at(..., center='barycentric')`
- [x] Add `planet_at(..., frame='cartesian')`
- [x] Add facade plumbing for the same controls (`sky_position_at`, `all_planets_at`)
- [x] Add direct tests for each exposed switch (`tests/unit/test_planet_position_switches.py`)
- [x] Update `SWISS_EPHEMERIS_SYMBOL_TABLE.md` rows for `FLG_ASTROMETRIC`, `FLG_TRUEPOS`, `FLG_NOABERR`, `FLG_NOGDEFL`, `FLG_NONUT`, `FLG_BARYCTR`, `FLG_XYZ`

#### Delta-T override

- [x] Design a typed `DeltaTPolicy` public surface (`moira.julian.DeltaTPolicy`)
- [x] Wire it into `ut_to_tt`, `tt_to_ut`, `planet_at`, `sky_position_at`, `all_planets_at`
- [x] Add validation/regression coverage (`tests/unit/test_delta_t_policy.py`)
- [x] Update the `set_delta_t_userdef` row

#### Rise/set doctrine selectors

- [x] Design `RiseSetPolicy` (typed, immutable, frozen dataclass)
- [x] Add disc reference selection (`center` / `limb` / `bottom`)
- [x] Add fixed-disc-size option
- [x] Add Hindu rising option
- [x] Add explicit refraction toggle as public doctrine
- [x] Add validation cases for each exposed doctrine (`tests/unit/test_low_level_helpers.py`)
- [x] Update the `BIT_DISC_*`, `BIT_HINDU_RISING`, and `BIT_NO_REFRACTION` rows

#### Low-level astronomy helpers

- [x] Add reverse horizontal transform helper — `horizontal_to_equatorial` (`azalt_rev` analogue)
- [x] Add speed-aware coordinate transform helper — `cotrans_sp` (`cotrans_sp` analogue)
- [x] Add public atmospheric refraction helper — `atmospheric_refraction`
- [x] Add public extended atmospheric refraction helper — `atmospheric_refraction_extended`
- [x] Add public equation-of-time helper — `equation_of_time`
- [x] Add direct low-level tests for each helper (`tests/unit/test_low_level_helpers.py`)

### Exit criteria

- all Phase 1 APIs are typed and documented
- no Swiss-style integer flags are added
- each new public surface has direct tests
- corresponding `none` rows are reclassified in the symbol table and support report

## Phase 2

### Goal

Add advanced low-level specialist helpers that fit Moira's engine model.

### Why now

- these are legitimate migration gaps
- they do not require a new full subsystem, but they do require careful public shaping

### Real blockers

- helper surfaces exist only implicitly or internally
- return types and doctrine need to be locked before exposure

### Atomic backlog

- [x] Add `planet_relative_to(...)` for `calc_pctr`-class use
- [x] Add `body_house_position(...)`
- [x] Add `houses_from_armc(...)`
- [x] Add `next_heliocentric_transit(...)`
- [x] Add `next_moon_node_crossing(...)`
- [x] Add validation/invariant tests for each helper (`tests/unit/test_phase2_helpers.py`)
- [x] Update corresponding Swiss rows from `none`

### Exit criteria

- each helper has a typed return contract
- each helper has direct validation or strong invariants
- no Swiss numeric selector idioms are introduced

## Phase 3

### Goal

Design the deferred-but-valid subsystem families.

### Why now

- after Phases 1 and 2, the remaining gaps are no longer helper-sized
- pushing them directly into implementation would create API debt

### Deferment map

| Family | Defer kind | Why |
| --- | --- | --- |
| generalized heliacal / visibility model | `Implemented.V0–V5` + `Active.V6` | V0–V5 complete; V6 partial: K&S 1991 moonlight model, `ExtinctionCoefficient` holders, `heliacal_catalog_batch` |
| model-basis controls | `Defer.Doctrine` | must not become a bag of Swiss option constants |
| additional ayanamsas | `Defer.Doctrine` | each added ayanamsa must be doctrinally named and justified |
| eclipse/occultation path helpers | `Active.Design` + `Active.Validation` | typed path/circumstance vessels exist; solar and occultation maximum geography are implemented and externally checked on the local Swiss `where` corpus |
| orbital-elements public layer | `Implemented` | `KeplerianElements`, `DistanceExtremes`, `orbital_elements_at`, `distance_extremes_at` in `moira/orbits.py` (Phase 4) |
| house dynamics / cusp-speed layer | `Implemented` | doctrine and validation are now embodied in `HouseDynamics`, `cusp_speeds_at(...)`, and `house_dynamics_from_armc(...)` |

### Atomic backlog

#### Heliacal family

- [x] write a heliacal subsystem constitution entry (`moira/heliacal.py` module docstring)
- [x] define `HeliacalEventKind`
- [x] define `HeliacalPolicy`
- [x] define `VisibilityModel`
- [x] define validation plan before public parity work (documented in `heliacal.py`)

#### Model-basis controls

- [x] decide whether `DeltaTPolicy` is the only public model policy in the near term
      → Yes. `DeltaTPolicy` covers ΔT. Precession/nutation controls remain internal.
- [x] decide whether precession/nutation controls should ever be public
      → Defer. Precession model selection belongs in a future `moira.precession` policy
        layer alongside `DeltaTPolicy`, not as separate boolean switches.
- [x] decide whether tidal acceleration belongs in public API or specialist/internal API only
      → Internal only for now. Tidal acceleration affects ΔT computation internally via
        `DeltaTPolicy.model='nasa_canon'`; no separate public surface until a validation
        story exists.

#### Ayanamsa expansion

- [x] add `UserDefinedAyanamsa` (`moira/sidereal.py`)
- [x] audit additional `SIDM_*` candidates individually
      → Acceptance criteria documented in `UserDefinedAyanamsa` docstring.
        Candidates not meeting all five criteria remain `UserDefinedAyanamsa` use-cases.
- [x] document acceptance criteria for future ayanamsa additions
      → Documented in `UserDefinedAyanamsa` docstring (5 criteria).

#### Path/where geometry

- [x] define `SolarEclipsePath` (`moira/eclipse.py`)
- [x] define occultation path/circumstance vessel shape (`OccultationPathGeometry` in `moira/occultations.py`)
- [x] define validation corpus expectations before implementation (in `SolarEclipsePath` docstring)

#### Orbital layer

- [x] decide whether `moira.orbits` should exist as a public module → Yes (`moira/orbits.py`)
- [x] define orbital-element vessel shape (`KeplerianElements` in `moira/orbits.py`)
- [x] define distance-extremes vessel shape (`DistanceExtremes` in `moira/orbits.py`)

#### House dynamics

- [x] define what cusp speed means doctrinally in Moira (`CuspSpeed` docstring in `houses.py`)
- [x] decide whether angle speeds and cusp speeds belong together
      → Yes. `HouseDynamics` carries both. Decision documented in `HouseDynamics` docstring.
- [x] define validation expectations before exposure (in `CuspSpeed` docstring)
- [x] implement `cusp_speeds_at(jd_ut, lat, lon, system, *, policy, dt)` → `HouseDynamics`
      → centred finite difference over ±dt (default 1 minute) on `calculate_houses`
- [x] implement `house_dynamics_from_armc(armc, obliquity, lat, system, *, policy, sun_longitude, darmc_deg)` → `HouseDynamics`
      → centred finite difference over `ARMC ± darmc_deg` on `houses_from_armc`, converted to degrees/day with the sidereal rotation rate
- [x] add direct tests (`tests/unit/test_house_dynamics.py`, 23 tests, all passing)

### Exit criteria

- deferred families have constitutions or subsystem design documents first
- validation strategy is written before “done” status
- no direct Swiss bitfield cloning

## Phase 4

### Goal

Implement the Phase 3 subsystem constitutions as working public surfaces.

### Why now

- Phase 3 locked doctrine, vessel shapes, and validation plans for heliacal and
  orbital families — implementation is now safe
- both families have strong validation anchors (known apparition dates, Kepler
  III sanity checks, Earth reference perihelion/aphelion)
- no Swiss flag clutter introduced; all surfaces are typed and doctrine-controlled

### Atomic backlog

#### Orbital layer — implementation

- [x] implement `orbital_elements_at(body, jd_ut) → KeplerianElements` (`moira/orbits.py`)
- [x] implement `distance_extremes_at(body, jd_ut) → DistanceExtremes` (`moira/orbits.py`)
- [x] wire both into `moira/__init__.py` with `__all__` entries
- [x] add full validation suite (`tests/unit/test_distance_extremes.py`, 51 tests, all passing)
      - physical constraints for all 8 planets (perihelion < aphelion, distances positive, JDs finite)
      - Earth reference: perihelion JD window [2451537.5, 2451559.5], distance ~0.9833 AU
      - Kepler III semi-major axis sanity
      - error handling for SUN and MOON

#### Heliacal planet computation — implementation

- [x] implement `planet_heliacal_rising(body, jd_start, lat, lon, *, policy, search_days) → PlanetHeliacalEvent | None`
- [x] implement `planet_heliacal_setting(body, jd_start, lat, lon, *, policy, search_days) → PlanetHeliacalEvent | None`
- [x] implement `planet_acronychal_rising(body, jd_start, lat, lon, *, policy, search_days) → PlanetHeliacalEvent | None`
- [x] implement `planet_acronychal_setting(body, jd_start, lat, lon, *, policy, search_days) → PlanetHeliacalEvent | None`
- [x] wire all four into `moira/__init__.py` with `__all__` entries
- [x] add full validation suite (`tests/unit/test_planet_heliacal.py`, 54 tests, all passing)
      - return type and structure (body, kind, jd_ut, elongation_deg, planet_altitude_deg,
        sun_altitude_deg, apparent_magnitude)
      - physical plausibility for all 5 fixtures (planet above horizon, sun below horizon,
        sun in twilight range −20° to 0°, magnitude finite)
      - elongation sign: HELIACAL_* < 0 (morning sky); ACRONYCHAL_* > 0 (evening sky)
      - reference windows: Venus heliacal rising 2020 [JD 2459004–2459044],
        Jupiter heliacal rising 2023 [JD 2460050–2460110],
        Venus acronychal rising 2021 [JD 2459310–2459360],
        Venus heliacal setting 2021 [JD 2459220–2459290]
      - policy customisation (stricter conditions delay or prevent event)
      - error handling (SUN, MOON, invalid lat, invalid search_days)
      - top-level moira import

### Exit criteria

- [x] all Phase 4 APIs typed, doctrine-controlled, and tested
- [x] no Swiss-style integer flags introduced
- [x] each surface wired into top-level `moira` namespace

## Phase 5

### Goal

Widen the admitted heliacal/visibility subsystem through its full V0–V5
public surface and admit the first V6 optional enhancements.

### Why now

- Phase 3 constitutional work and Phase 4 narrow planetary helpers established
  the doctrine foundation and validation anchor (Sothic/Sirius 139 AD)
- Yallop lunar crescent corpus provided 295-entry oracle for the criterion-family
  pathway, enabling V4 validation completion
- V5 public widening was safe only after both V4 paths (planetary apparitions
  and Yallop corpus) were verified
- V6 optional enhancements (moonlight, catalog batch) do not change core doctrine
  truth; they extend the admitted policy surface with clearly bounded additions

### Atomic backlog

#### V1 — Observer environment policy

- [x] define `LightPollutionClass` (Bortle 1–9 typed scale)
- [x] define `LightPollutionDerivationMode` (table vs linear)
- [x] define `ObserverAid` (naked eye / binoculars / telescope)
- [x] define `ObserverVisibilityEnvironment` (full observer environment vessel)
      — fields: `light_pollution_class`, `limiting_magnitude`,
        `local_horizon_altitude_deg`, `temperature_c`, `pressure_mbar`,
        `relative_humidity`, `observer_altitude_m`, `observing_aid`
- [x] add `VisibilityModel.to_observer_environment()` bridge for V0 backward compat

#### V2 — Visibility criterion family and policy

- [x] define `VisibilityCriterionFamily` (`LIMITING_MAGNITUDE_THRESHOLD`, `YALLOP_LUNAR_CRESCENT`)
- [x] define `VisibilityExtinctionModel` and `VisibilityTwilightModel` named slots
- [x] define `MoonlightPolicy` (`IGNORE`, `KRISCIUNAS_SCHAEFER_1991`)
- [x] define `VisibilityPolicy` (unified admitted policy vessel)
- [x] define `VisibilitySearchPolicy` (search-window and step-size control)
- [x] implement `_effective_limiting_magnitude(policy)` with explicit Bortle precedence law
- [x] implement `_policy_limiting_magnitude` Bortle table and linear fallback

#### V3 — Generalized event search surface

- [x] implement `visibility_assessment(body, jd_ut, lat, lon, *, policy) → VisibilityAssessment`
- [x] implement `visibility_event(body, event_kind, jd_start, lat, lon, *, ...) → GeneralVisibilityEvent | None`
      — routes `PLANET`, `STAR`, `MOON` target kinds
      — routes `YALLOP_LUNAR_CRESCENT` and `LIMITING_MAGNITUDE_THRESHOLD` criterion families
      — routes `HELIACAL_RISING`, `HELIACAL_SETTING`, `ACRONYCHAL_RISING`,
        `ACRONYCHAL_SETTING`, `COSMIC_RISING`, `COSMIC_SETTING` event kinds
- [x] define `LunarCrescentVisibilityClass` (A–F) and `LunarCrescentDetails` vessel
- [x] implement `_lunar_crescent_details_for_evening` and `_lunar_crescent_details_for_morning`

#### V4 — Validation corpus

- [x] obtain Yallop (1997) Table 4 reference corpus (295 entries)
- [x] implement `test_yallop_corpus_q_value_accuracy` integration test
      — 293/295 within ±0.03 q-value, 295/295 within ±0.05
      — mean residual 0.0077, max 0.0315
      — 5 UTC-vs-local fixture date corrections applied and documented
- [x] implement `test_generalized_stellar_visibility_event_matches_sothic_anchor_slice`
      — Sirius heliacal rising 139 AD, Alexandria, within 5 days of Sothic anchor

#### V5 — Public surface widening

- [x] promote 18 names to `moira/__init__.py` and `moira/facade.py`:
      `HeliacalEventKind`, `VisibilityTargetKind`, `LightPollutionClass`,
      `LightPollutionDerivationMode`, `ObserverAid`, `ObserverVisibilityEnvironment`,
      `VisibilityCriterionFamily`, `VisibilityExtinctionModel`, `VisibilityTwilightModel`,
      `MoonlightPolicy`, `VisibilityPolicy`, `VisibilitySearchPolicy`,
      `LunarCrescentVisibilityClass`, `LunarCrescentDetails`, `VisibilityAssessment`,
      `GeneralVisibilityEvent`, `visibility_assessment`, `visibility_event`

#### V6 partial — Optional enhancements

- [x] implement K&S 1991 moonlight sky-brightness model (`moira/heliacal.py`):
      — `_ks1991_moon_magnitude` (Eq. 9)
      — `_ks1991_scattering_function` (Eq. 3)
      — `_ks1991_moonlight_nanolamberts` (Eqs. 20–21)
      — `_ks1991_dark_sky_nanolamberts` (Bortle SQM → nanolamberts)
      — `_ks1991_limiting_magnitude_penalty` (Δm_L penalty)
      — `VisibilityAssessment.moonlight_sky_nanolamberts` diagnostic field
- [x] add `ExtinctionCoefficient` namespace with named reference holders:
      `MAUNA_KEA` (0.172), `GOOD_DARK_SITE` (0.20), `TYPICAL` (0.25), `HAZY` (0.30)
- [x] expose `extinction_coefficient_k: float = 0.20` on `VisibilityPolicy`
- [x] add `ExtinctionCoefficient` to `moira/__init__.py` and `moira/facade.py`
- [x] implement `heliacal_catalog_batch(event_kind, jd_start, lat, lon, *, ...)` (`moira/stars.py`):
      — pre-filter 1: magnitude threshold (skips without ephemeris)
      — pre-filter 2: latitude-limit from `lat_limit_deg` registry column
      — per-star `arc_vis_deg` used directly as arcus visionis
      — result in `HeliacalBatchResult` vessel with `found`, `not_found`,
        `skipped_latitude`, `skipped_magnitude` and three property accessors
- [x] define `HeliacalBatchResult` in `moira/star_types.py`
- [x] promote `HeliacalBatchResult` and `heliacal_catalog_batch` to `moira/facade.py`
- [x] implement `visual_limiting_magnitude(jd_ut, lat, lon, *, policy) -> float` (`moira/heliacal.py`):
      — Bortle sky limit via `_effective_limiting_magnitude`
      — K&S 1991 moonlight penalty when `MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991`
      — closes Swiss `vis_limit_mag` parity gap
- [x] promote `visual_limiting_magnitude` to `moira/__init__.py` and `moira/facade.py`
- [x] add unit tests: 16 K&S 1991 tests + 8 batch tests (all passing)

### Exit criteria

- [x] V0–V5 generalized visibility subsystem typed, doctrine-controlled, tested
- [x] Yallop corpus 295/295 within ±0.05; mean 0.0077; max 0.0315
- [x] K&S 1991 moonlight model unit-tested against paper equations
- [x] `heliacal_catalog_batch` with pre-filtering and `HeliacalBatchResult` vessel
- [x] all new public names in `moira/__init__.py` and `moira/facade.py`
- [x] `moira/heliacal.py` header docstring reflects actual implementation state
- [x] `visual_limiting_magnitude` implemented and promoted; closes `vis_limit_mag` Swiss gap

### Open V6 items (deferred)

- Live-ephemeris integration test for K&S 1991 moonlight under known bright-moon conditions
- Stellar heliacal batch validation corpus beyond Sothic/Sirius anchor
  (Spica, Arcturus, Antares, Regulus, Aldebaran from primary sources)
- Terrain/horizon profile integration
- Observer-experience scaling
- Wavelength-specific visibility refinements
- Research comparison across multiple visibility doctrines

## Constitutionally Rejected Classes

These should remain out of Moira unless project goals change materially.

- Swiss backend selectors
- Swiss library/file/path constants
- Swiss internal size/range constants
- centisecond formatting utilities
- hypothetical/obsolete bodies not part of Moira's supported model
- Swiss numeric offset selector idioms

Examples:
- `FLG_SWIEPH`, `FLG_MOSEPH`, `FLG_JPLEPH`
- `FNAME_*`, `EPHE_PATH`, `SE_FNAME_DE431`
- `NPLANETS`, `NFICT_ELEM`, `NSIDM_PREDEF`
- `difcs2n`, `difcsn`, `csnorm`
- `NIBIRU`, `VULCAN`, `WALDEMATH`
- `COMET_OFFSET`, `PLMOON_OFFSET`, `FLG_CENTER_BODY`

## Tracking Template

### Candidate

- Symbol / family:
- Current decision:
- Defer kind:
- constitutional entry point:
- Proposed Moira surface:
- Why now:
- Real blocker:
- Validation authority:
- Validation plan:
- Dependencies:
- Status:

## Update Rule

When a symbol or family changes state:
1. update [`SWISS_EPHEMERIS_SYMBOL_TABLE.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SWISS_EPHEMERIS_SYMBOL_TABLE.md)
2. update [`SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md)
3. update this roadmap
4. add or update validation coverage
5. if the work is a deferred family, update the relevant constitutional entry-point docs
