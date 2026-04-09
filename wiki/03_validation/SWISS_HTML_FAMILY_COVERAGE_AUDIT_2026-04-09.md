# Swiss HTML Family Coverage Audit (2026-04-09)

Purpose:
- use the newly available local Swiss Ephemeris HTML documentation as a family-level coverage map
- confirm which major Swiss capability areas Moira already covers
- identify which areas are partial, deferred, or intentionally out of scope

Non-goal:
- this is not a parity promise
- this is not a directive to copy Swiss formulas, flags, or API shape
- this is not a replacement for primary astronomical authorities

Primary source used for this audit:
- local file: `C:\Users\nilad\Downloads\swisseph documentation.html`

Supporting Moira sources:
- `wiki/03_validation/SWISS_EPHEMERIS_SYMBOL_TABLE.md`
- `wiki/03_validation/SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md`
- `wiki/03_validation/SWISS_EPHEMERIS_EXTENSIBILITY_ROADMAP.md`
- `wiki/01_doctrines/BEYOND_SWISS_EPHEMERIS.md`

## Decision Labels

- `covered`:
  Moira already has a real public or documented subsystem covering the same general area.
- `partial`:
  Moira covers important parts of the family, but not the whole Swiss family surface.
- `defer`:
  The area is legitimate, but Moira should only expand it through a typed Moira-native design.
- `out_of_scope`:
  The Swiss area is internal, obsolete, hypothetical, or contrary to Moira's design.

## Section Inventory from the Swiss HTML

The HTML clusters into these major families:

1. Planetary and lunar ephemerides
2. Lunar and planetary nodes and apsides
3. Asteroids
4. Planetary centers of body and planetary moons
5. Comets and interstellar objects
6. Fixed stars and Galactic Center
7. Hypothetical bodies
8. Sidereal ephemerides / ayanamsha
9. Apparent versus true planetary positions
10. Geocentric / topocentric / heliocentric / barycentric / planetocentric positions
11. Heliacal events, eclipses, occultations, risings, settings, and related phenomena
12. Sidereal time, houses, angles, vertex, and house position
13. Delta T
14. Programming environment / initialization / API utilities

## Family-Level Coverage

### 1. Planetary and lunar ephemerides

Status: `covered`

Current Moira surfaces:
- `moira.planets`
- `moira.chart`
- `moira.facade`
- validation against Horizons and related external references in `tests/integration`

Notes:
- This is a core covered family.
- Moira is not using Swiss as the summit authority here; the stronger validation anchor is JPL/Horizons and Moira's own substrate tests.

### 2. Lunar and planetary nodes and apsides

Status: `partial`

Current Moira surfaces:
- `moira.nodes`
- chart integration via `moira.chart`
- public support for mean node, true node, and Lilith-related surfaces already present in the repo

Notes:
- The family is clearly present.
- Swiss's full apsides and node-selector surface is broader than the currently exposed Moira surface.
- Expansion here should remain body- and doctrine-explicit rather than adopting Swiss numeric selector idioms.

### 3. Asteroids

Status: `covered`

Current Moira surfaces:
- `moira.asteroids`
- `moira.classical_asteroids`
- `moira.main_belt`
- bundled kernel-backed named-body registry

Notes:
- Moira already exceeds Swiss default convenience coverage in some respects by exposing many named bodies directly.
- This remains a Moira-native named-body/kernel architecture, not a Swiss offset model.

### 4. Planetary centers of body and planetary moons

Status: `partial`

Current Moira surfaces:
- barycentric, heliocentric, and relative-center work already exists in the planetary layer
- `planet_relative_to(...)` is already called out in the none-support report as an implemented surface

Notes:
- Relative-center and center-of-body semantics are present in part.
- Swiss's moon and center-of-body comparison families are broader than the currently obvious Moira public layer.
- This is a real coverage frontier if fuller body-center and moon support is desired.

### 5. Comets and interstellar objects

Status: `partial`

Current Moira surfaces:
- documented doctrine interest in interstellar objects in `BEYOND_SWISS_EPHEMERIS`
- asteroid/minor-body architecture suggests a natural extension path

Notes:
- This is not yet a broad, explicit public family on the same footing as planets or stars.
- The area is valid, but it should be implemented from proper orbital and kernel provenance, not from Swiss-style selectors.

### 6. Fixed stars and Galactic Center

Status: `covered`

Current Moira surfaces:
- `moira.stars`
- `moira.variable_stars`
- `moira.multiple_stars`
- `moira.galactic`
- sovereign star registry under `moira/data`
- extensive external validation in star-related integration tests

Notes:
- This is one of Moira's strongest covered areas.
- Moira's star doctrine is already more explicit than Swiss here because provenance and catalog identity are first-class.

### 7. Hypothetical bodies

Status: `partial`

Current Moira surfaces:
- `moira.uranian`

Notes:
- Uranian bodies are admitted.
- Much of the wider Swiss hypothetical-body family remains intentionally excluded.
- Obsolete or physically unsupported hypotheticals should remain segregated from the astronomical substrate.

### 8. Sidereal ephemerides / ayanamsha

Status: `covered`

Current Moira surfaces:
- `moira.sidereal`
- Vedic and related doctrine layers that consume sidereal positions
- Swiss-related sidereal fixtures already present in `tests/fixtures/sidereal_swetest_reference.json`

Notes:
- This is a covered family.
- Additional ayanamsha proliferation remains a doctrinal packaging question, not a parity obligation.

### 9. Apparent versus true planetary positions

Status: `covered`

Current Moira surfaces:
- `planet_at(..., apparent=False)`
- explicit switches for aberration, gravitational deflection, and nutation
- tests in `tests/unit/test_planet_position_switches.py`

Notes:
- This family was already recognized and implemented as typed switches rather than Swiss flags.

### 10. Geocentric / topocentric / heliocentric / barycentric / planetocentric positions

Status: `covered`

Current Moira surfaces:
- geocentric and topocentric planetary work in `moira.planets`
- heliocentric support
- barycentric support
- relative-center support via implemented specialist helpers
- dedicated coordinate and transformation modules

Notes:
- This is a well-covered family.
- Planetocentric and center-relative semantics should continue to be exposed through named, typed surfaces rather than flag bundles.

### 11. Heliacal events, eclipses, occultations, risings, settings, and related phenomena

Status: `partial`

Current Moira surfaces:
- `moira.heliacal`
- `moira.eclipse`
- `moira.eclipse_contacts`
- `moira.eclipse_geometry`
- `moira.occultations`
- `moira.rise_set`
- `moira.phenomena`

Notes:
- Eclipses, occultations, rise/set, and related phenomena are strongly present.
- Heliacal work is present, but the Swiss generalized heliacal option matrix still maps to a deferred typed-family design problem in the existing roadmap.
- This remains one of the major live frontier areas.

### 12. Sidereal time, houses, angles, vertex, and house position

Status: `covered`

Current Moira surfaces:
- sidereal time functions in `moira.julian`
- `moira.houses`
- `moira.gauquelin`
- house dynamics and ARMC-related helpers already called implemented in the none-support report
- chart and progression layers that consume house outputs

Notes:
- This family is broad, but it is substantively covered.
- Polar and edge-case house behavior is already explicitly tested in the repo.

### 13. Delta T

Status: `covered`

Current Moira surfaces:
- `moira.delta_t_physical`
- `moira.julian`
- standards documentation in `DELTA_T_HYBRID_MODEL.md`
- multiple unit and integration validation files

Notes:
- This is another area where Moira intentionally moves beyond Swiss rather than following it.
- Swiss documentation remains useful here as a comparison target, not as the governing model.

### 14. Programming environment / initialization / API utilities

Status: `partial`

Current Moira surfaces:
- constructor and kernel-path setup
- Julian conversion helpers
- coordinate and auxiliary helpers
- a broad public API already exists across modules

Notes:
- Moira intentionally does not mirror Swiss's global mutable setup and flag-heavy C API.
- Coverage should be judged by domain capability, not by utility-function count or flag equivalence.

## Main Conclusions

The newly available Swiss HTML confirms that Moira already covers most of the major Swiss domain families at the subsystem level.

The most important remaining family-level frontiers are:
- generalized heliacal and visibility doctrine
- fuller nodes and apsides coverage
- broader relative-center / center-of-body / planetary-moon surfaces
- comet and interstellar-object public surfaces

The main families that should not be allowed to distort Moira's design are:
- Swiss internal setup and backend controls
- numeric selector and offset idioms
- broad hypothetical-body sprawl without a clear physical or doctrinal basis

## Recommended Next Use of the Swiss HTML

Use the HTML in this order:

1. As a section-level checklist to verify that every major Swiss family has an explicit Moira decision.
2. As a row-discovery aid for symbols or subfamilies that may have been undercounted in the earlier draft work.
3. As a prompt for targeted Moira-native design only where a real family gap remains.

Do not use it:

- as the authority for core astronomical math when stronger primary sources exist
- as a reason to add Swiss-shaped flags or global-state patterns
- as evidence of correctness without validation against the proper oracle for each subsystem

## Immediate Follow-Up Candidates

- reconcile the Swiss HTML family headings against the existing symbol table to see whether any entire subfamily was missed in the earlier audit
- isolate the heliacal subsection of the HTML and compare its event taxonomy against `moira.heliacal`
- isolate the nodes/apsides subsection and compare its admitted semantic products against `moira.nodes`
- isolate the centers-of-body / moons subsection and compare it against current relative-center helpers
