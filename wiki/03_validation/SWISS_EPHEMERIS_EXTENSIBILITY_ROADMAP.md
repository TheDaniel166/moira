# Swiss Ephemeris Extensibility Roadmap

This document turns the Swiss-to-Moira parity analysis into an extendible
execution roadmap.

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
| generalized heliacal / visibility model | `Defer.Design` + `Defer.Validation` | [`fixed_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_stars.py), [`STARS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/STARS_BACKEND_STANDARD.md) | heliacal behavior belongs under the unified star subsystem, not as standalone Swiss compatibility flags |
| model-basis controls (`DeltaT`, precession, nutation, tidal acceleration) | `Defer.Doctrine` | [`julian.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/julian.py), [`corrections.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/corrections.py), [`DELTA_T_HYBRID_MODEL.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/DELTA_T_HYBRID_MODEL.md) | these are foundational astronomy policy choices, not Swiss option constants |
| additional ayanamsa constants / user-defined ayanamsa | `Defer.Doctrine` | [`sidereal.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/sidereal.py) | ayanamsa expansion belongs in one coherent sidereal doctrine layer |
| eclipse / occultation path helpers | `Active.Design` + `Active.Validation` | [`eclipse.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse.py), [`ECLIPSE_MODEL_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/ECLIPSE_MODEL_STANDARD.md), [`occultations.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/occultations.py), [`ANCIENT_OCCULTATION_VALIDATION_PROGRAM.md`](c:/Users/nilad/OneDrive/Desktop/Moira/wiki/03_validation/ANCIENT_OCCULTATION_VALIDATION_PROGRAM.md) | modern/future path geometry is active and externally validated; ancient occultations belong to a separate historical-validation program |
| orbital-elements public layer | `Defer.Design` | supporting-modules track from [`REPOSITORY_ASSESSMENT.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/REPOSITORY_ASSESSMENT.md) | should be introduced as a dedicated typed subsystem, not scattered helpers |
| house dynamics / cusp-speed layer | `Defer.Doctrine` + `Defer.Validation` | [`houses.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/houses.py), [`HOUSES_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/HOUSES_BACKEND_STANDARD.md) | house speeds belong in the house doctrine itself, not a Swiss-style auxiliary tuple |

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
| generalized heliacal / visibility model | `Defer.Design` + `Defer.Validation` | needs one coherent heliacal subsystem design plus stronger oracle policy |
| model-basis controls | `Defer.Doctrine` | must not become a bag of Swiss option constants |
| additional ayanamsas | `Defer.Doctrine` | each added ayanamsa must be doctrinally named and justified |
| eclipse/occultation path helpers | `Active.Design` + `Active.Validation` | typed path/circumstance vessels exist; solar and occultation maximum geography are implemented and externally checked on the local Swiss `where` corpus |
| orbital-elements public layer | `Defer.Design` | requires a dedicated typed subsystem |
| house dynamics / cusp-speed layer | `Defer.Doctrine` + `Defer.Validation` | house-speed semantics need to be defined before exposure |

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
