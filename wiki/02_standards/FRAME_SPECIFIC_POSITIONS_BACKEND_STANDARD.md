# Frame-Specific Positions Backend Standard

Version: 0.1
Date: 2026-06-14
Status: implemented backend standard for P-GAP-01 REST admission
Scope: heliocentric, planetocentric, SSB, and received-light position products

This standard governs the non-geocentric position products that are public in
the Python engine, `Moira` facade, and admitted P-GAP-01 REST routes:

- `moira.planets.heliocentric_planet_at`
- `moira.planets.all_heliocentric_at`
- `moira.planetocentric.planetocentric_at`
- `moira.planetocentric.all_planetocentric_at`
- `moira.ssb.ssb_position_at`
- `moira.ssb.all_ssb_positions_at`
- `moira.light_cone.received_light_at`
- `moira.light_cone.all_received_light_at`

The existing `/v1/positions/*` REST family is geocentric/topocentric and sky
projection oriented. It must not be silently stretched to mean all possible
position centers. P-GAP-01 exists because these frame-specific products have
different centers, correction semantics, and result vessels.

---

## 1. Governing Objects

Frame-specific position transport must preserve four distinct governing
objects.

### Heliocentric Position

Owned by:

- `moira.planets.HeliocentricData`
- `moira.planets.heliocentric_planet_at`
- `moira.planets.all_heliocentric_at`

Meaning:

- body position measured from the Sun
- true-of-date ecliptic orientation
- precession and nutation applied
- no geocentric observer
- not meaningful for Sun or Moon

Admitted result fields:

- `name`
- `longitude`
- `latitude`
- `distance`
- `distance_au`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

### Planetocentric Position

Owned by:

- `moira.planetocentric.PlanetocentricData`
- `moira.planetocentric.planetocentric_at`
- `moira.planetocentric.all_planetocentric_at`

Meaning:

- target position measured from the center of a named observer body
- geometric ecliptic position
- true-of-date ecliptic orientation
- precession and nutation applied
- light-time not corrected
- observer and target must differ

Admitted result fields:

- `observer`
- `name`
- `longitude`
- `latitude`
- `distance`
- `distance_au`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

### SSB Position

Owned by:

- `moira.ssb.SSBPosition`
- `moira.ssb.ssb_position_at`
- `moira.ssb.all_ssb_positions_at`

Meaning:

- body position measured from the Solar System Barycenter
- BCRS/SSB-origin product projected into true-of-date ecliptic orientation
- geometric product
- light-time not corrected
- Sun has non-zero SSB position

Admitted result fields:

- `name`
- `longitude`
- `latitude`
- `distance`
- `distance_au`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

### Received-Light Position

Owned by:

- `moira.light_cone.ReceivedLightPosition`
- `moira.light_cone.received_light_at`
- `moira.light_cone.all_received_light_at`

Meaning:

- explicit light-cone comparison at Earth receipt time
- apparent ecliptic position from the ordinary apparent pipeline
- geometric ecliptic position at the same JD
- light-travel duration and emission JD preserved
- physical bodies only

Admitted result fields:

- `name`
- `apparent_longitude`
- `apparent_latitude`
- `geometric_longitude`
- `geometric_latitude`
- `longitude_displacement`
- `distance_km`
- `distance_au`
- `light_travel_days`
- `light_travel_minutes`
- `emission_jd`
- `speed`
- `retrograde`
- `sign`
- `sign_symbol`
- `sign_degree`

---

## 2. Body Admission

REST transport must preserve each engine surface's native body policy.

Heliocentric:

- default body list excludes Sun and Moon
- requests for Sun or Moon must be rejected

Planetocentric:

- observer must be in `VALID_OBSERVER_BODIES`
- target must be in `VALID_OBSERVER_BODIES`
- observer and target must differ
- default target list excludes the observer

SSB:

- body must be in `SSB_BODIES`
- Sun and Earth are meaningful products here when kernel support exists

Received light:

- body must be in `RECEIVED_LIGHT_BODIES`
- computed points such as nodes and Lilith are not admitted

Transport must cap bulk requests. Initial REST admission should allow at most
`12` bodies per request, matching the existing server tendency for bounded
chart/position products.

---

## 3. Time And Reader Policy

All P-GAP-01 requests must use timezone-aware datetimes at the REST boundary.

Transport must report:

- requested datetime
- normalized UTC datetime
- `jd_ut`
- `jd_tt`
- `delta_t_seconds`
- source module
- engine entrypoint
- reader owner

The server should use the existing engine reader binding from the application
dependency context. It must not create a new global kernel state or mutate
kernel paths.

---

## 4. Frame And Correction Truth

Every response must state its center and correction semantics.

Heliocentric:

- center: `sun`
- frame: `true_of_date_ecliptic`
- correction model: `geometric_heliocentric_precession_nutation`
- light-time corrected: `false`
- apparent-sky corrected: `false`

Planetocentric:

- center: requested observer body
- frame: `true_of_date_ecliptic`
- correction model: `geometric_planetocentric_precession_nutation`
- light-time corrected: `false`
- apparent-sky corrected: `false`

SSB:

- center: `solar_system_barycenter`
- frame: `true_of_date_ecliptic`
- correction model: `geometric_barycentric_precession_nutation`
- light-time corrected: `false`
- apparent-sky corrected: `false`

Received light:

- center: `earth`
- frame: `true_of_date_ecliptic`
- correction model:
  `apparent_received_light_compared_to_same_time_geometric`
- light-time corrected: `true`
- apparent-sky corrected: `true` for apparent fields
- geometric comparison included: `true`

Transport must not describe heliocentric, planetocentric, or SSB products as
observed/apparent positions. Transport must not describe received-light output
as simply "geometric" because its primary apparent fields come from the
ordinary apparent pipeline.

---

## 5. Route Admission Boundary

P-GAP-01 admits a bounded synchronous REST family under:

- `/v1/positions/frame/*`

The route family should include:

- `POST /v1/positions/frame/heliocentric`
- `POST /v1/positions/frame/planetocentric`
- `POST /v1/positions/frame/ssb`
- `POST /v1/positions/frame/received-light`

Each route should accept:

- one timezone-aware datetime
- optional bounded body list, except planetocentric also requires `observer`
- output controls limited to fields that do not change computation semantics

Route names must not imply that these are replacements for:

- `/v1/positions/planet`
- `/v1/positions/sky`
- `/v1/chart`

They are specialized frame products.

---

## 6. Non-Goals

P-GAP-01 does not admit:

- arbitrary centers beyond the named engine support
- topocentric planetocentric observation
- light-time iteration for planetocentric products
- occultation/eclipsing products from non-Earth observers
- rendered charts
- dense ephemeris tables
- transit/search products such as heliocentric conjunctions
- kernel path mutation or manifest loading
- small-body expansion beyond what the owning engine functions support

---

## 7. Verification Requirements

Before REST admission, tests must cover:

- route registration
- successful heliocentric request
- successful planetocentric request
- successful SSB request
- successful received-light request
- bulk body cap
- timezone-aware datetime rejection for all routes
- heliocentric rejection of Sun and Moon
- planetocentric rejection of invalid observer
- planetocentric rejection of observer equal to target
- SSB rejection of unsupported body
- received-light rejection of nodes or nonphysical points
- provenance and frame/correction truth for every route
- no hidden kernel mutation

At least one test should assert that received-light output preserves both
apparent and geometric longitudes and the light-travel fields.

---

## 8. Admission Decision

P-GAP-01 is admitted through the bounded `/v1/positions/frame/*` REST family.

Recommended status:

- `admitted`

Reason:

- the engine surfaces are already explicit and facade-visible
- the computational vessels preserve center/frame truth
- the main risk is transport semantic collapse, not missing computation

The transport implementation is named in
`docs/architecture/P-GAP-01_FRAME_SPECIFIC_POSITIONS_TRANSPORT_DESIGN.md`.
It remains a server adapter over existing engine/facade computations.
