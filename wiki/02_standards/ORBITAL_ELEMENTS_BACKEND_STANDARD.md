# Orbital Elements Backend Standard

Version: 0.1
Date: 2026-06-14
Status: implemented backend standard for P-GAP-03 REST admission
Scope: heliocentric osculating orbital elements and heliocentric distance extrema

This standard governs the orbital-elements surfaces that are public through
the Python engine and candidates for P-GAP-03 REST admission:

- `moira.orbits.KeplerianElements`
- `moira.orbits.DistanceExtremes`
- `moira.orbits.orbital_elements_at`
- `moira.orbits.distance_extremes_at`

This standard does not govern the Phase 11 planetary-node route family, visual
binary Campbell elements, Uranian mean elements, comet catalog elements, or
small-body catalog ingestion. Those are distinct products with different
centers, frames, provenance, and validation requirements.

---

## 1. Governing Objects

P-GAP-03 has two governing objects.

### Heliocentric Osculating Elements

Owned by:

- `moira.orbits.KeplerianElements`
- `moira.orbits.orbital_elements_at`

Meaning:

- instantaneous Keplerian osculating elements at one requested epoch
- heliocentric center
- J2000.0 ecliptic and equinox reference plane/orientation
- derived from the live DE-series heliocentric state vector
- not a mean-element table
- not an apparent geocentric astrology position

Admitted fields:

- `name`
- `epoch_jd`
- `semi_major_axis_au`
- `eccentricity`
- `inclination_deg`
- `lon_ascending_node_deg`
- `arg_perihelion_deg`
- `mean_anomaly_deg`
- `mean_motion_deg_per_day`
- `orbital_period_days`
- `perihelion_distance_au`
- `aphelion_distance_au`

### Heliocentric Distance Extrema

Owned by:

- `moira.orbits.DistanceExtremes`
- `moira.orbits.distance_extremes_at`

Meaning:

- next perihelion and next aphelion after the requested start JD
- events are found on the live heliocentric distance curve
- search delegates to the existing phenomena perihelion/aphelion surfaces
- result order is semantic, not chronological; aphelion may occur before
  perihelion for some start epochs

Admitted fields:

- `name`
- `perihelion_jd`
- `perihelion_distance_au`
- `aphelion_jd`
- `aphelion_distance_au`

---

## 2. Body Admission

Stage 1 REST admission should expose only the bodies admitted by the live
engine for these surfaces:

- Mercury
- Venus
- Earth
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto

The transport layer must reject:

- Sun, because it is the heliocentric reference center
- Moon, because the current engine explicitly does not admit heliocentric
  osculating lunar elements as meaningful for this surface
- nodes, Lilith, lots, stars, asteroids, comets, Uranian points, or other
  non-admitted bodies

No route should silently reinterpret a rejected body into a different center,
catalog, or mean-element product.

---

## 3. Time And Scale Policy

The engine entrypoints accept `jd_ut`.

Transport must preserve this explicitly:

- request field: `jd_ut`
- input time scale: UT Julian Day
- state evaluation: engine converts internally to TT through `ut_to_tt`
- response field `epoch_jd` follows the live `KeplerianElements.epoch_jd`
  engine field

Stage 1 should not admit timezone-aware datetime convenience fields. That can
be added later if the route family needs a chart-adjacent convenience layer,
but the first admission should keep the astronomical substrate surface
unambiguous.

All request and response numeric values must be finite except where the engine
has an explicit non-finite doctrine. Stage 1 does not admit hyperbolic or
parabolic element products, so no non-finite orbital period should be returned
by the public REST surface.

---

## 4. Frame And Element Truth

Every response must state:

- `center`: `sun`
- `frame`: `J2000_ecliptic_and_equinox`
- `element_type`: `osculating`
- `position_basis`: `heliocentric_state_vector`
- `state_source`: `DE_series_kernel`
- `orientation`: `fixed_J2000_ecliptic`
- `apparent_corrections`: `not_applied`
- `light_time_correction`: `not_applied`
- `mean_element_table`: `not_used`

Transport must not call these:

- tropical zodiac positions
- sidereal zodiac positions
- apparent positions
- chart positions
- mean elements
- generic orbital facts detached from epoch

---

## 5. Distance-Extrema Truth

Distance extrema must be described as curve events, not as simple algebraic
properties of the one-epoch osculating ellipse.

Every distance-extrema response must state:

- `event_basis`: `live_heliocentric_distance_curve`
- `search_direction`: `forward_from_jd_ut`
- `search_owner`: `moira.phenomena`
- `perihelion_event`: `next_local_minimum`
- `aphelion_event`: `next_local_maximum`
- `chronological_order_forced`: `false`

The `perihelion_distance_au` and `aphelion_distance_au` properties on
`KeplerianElements` remain valid derived distances of the osculating ellipse
at the element epoch. They are not a substitute for `distance_extremes_at`.

---

## 6. Source Authority And Validation

The admitted authority posture is:

- computation source: Moira-owned extraction from DE-series heliocentric state
  vectors
- validation oracle for elements: JPL Horizons `EPHEM_TYPE=ELEMENTS`
- validation oracle for extrema: JPL Horizons `EPHEM_TYPE=VECTORS` distance
  curves refined around local extrema

Current validation evidence:

- `tests/unit/test_orbital_elements.py`
- `tests/integration/test_horizons_orbits.py`
- `wiki/03_validation/VALIDATION_ASTRONOMY.md`, sections 4.4 and 4.5

P-GAP-03 transport tests do not need to re-run live Horizons. They must prove
that the REST adapter preserves the already validated engine truth, rejects
invalid transport states, and serializes provenance without semantic collapse.

---

## 7. Route Admission Boundary

P-GAP-03 may admit a bounded synchronous REST family under:

- `/v1/orbits/*`

Stage 1 routes should be limited to:

- `POST /v1/orbits/elements`
- `POST /v1/orbits/distance-extremes`

Each route accepts:

- one body
- one finite `jd_ut`

Bulk vectors, date ranges, dense element tables, and search jobs are not
admitted in Stage 1.

---

## 8. Non-Goals

P-GAP-03 does not admit:

- mean planetary element tables
- geocentric lunar elements
- comet orbital elements
- asteroid orbital elements
- Uranian mean elements
- visual-binary Campbell elements
- arbitrary reference centers
- arbitrary reference planes
- apparent or light-time-corrected element products
- topocentric orbit products
- dense ephemeris tables
- perihelion/aphelion searches for non-admitted bodies
- kernel path mutation or manifest loading

---

## 9. Verification Requirements

Before REST admission, tests must cover:

- successful orbital-elements route for at least one inner planet
- successful orbital-elements route for at least one outer planet
- successful distance-extrema route
- REST response parity with `orbital_elements_at`
- REST response parity with `distance_extremes_at`
- Sun rejection
- Moon rejection
- unsupported body rejection
- non-finite `jd_ut` rejection
- extra request field rejection
- provenance truth for center, frame, element type, state source, and
  correction model
- no route registration under `/v1/positions/*`, `/v1/nodes/*`, or
  `/v1/phenomena/*`
- no kernel mutation

The focused route tests may use the existing `moira_engine`/reader fixture and
must not construct ad hoc global reader state.

---

## 10. Admission Decision

P-GAP-03 is admitted through the bounded `/v1/orbits/*` REST family.

Recommended status:

- `admitted`

Reason:

- the engine surface is already typed and validated
- the product semantics are scientifically specific
- the main admission risk is transport naming and provenance collapse, not
  missing computation
