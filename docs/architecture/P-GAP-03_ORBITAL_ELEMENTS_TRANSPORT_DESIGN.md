# P-GAP-03 Orbital Elements Transport Design

Version: 0.2
Date: 2026-06-14
Status: implemented and admitted
Scope: bounded REST admission plan for heliocentric osculating elements and
heliocentric distance extrema

This design follows `wiki/02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md`.

P-GAP-03 evaluates the root-exported orbital surfaces:

- `orbital_elements_at`
- `distance_extremes_at`
- `KeplerianElements`
- `DistanceExtremes`

These are astronomical substrate products. They are not chart positions,
zodiacal positions, mean element tables, or interpretive astrology surfaces.

---

## 1. Route Family

Prefix:

- `/v1/orbits`

Routes:

- `POST /v1/orbits/elements`
- `POST /v1/orbits/distance-extremes`

Route naming doctrine:

- `orbits` marks the family as orbital-state derived products.
- `elements` returns one epoch's heliocentric J2000 osculating Keplerian
  elements.
- `distance-extremes` returns the next heliocentric perihelion and aphelion
  events after the requested start epoch.

---

## 2. Request Models

`OrbitalElementsRequest`:

- `body`: string
- `jd_ut`: float

Validation:

- `body` must be non-empty after trimming
- `body` must be one of the admitted engine bodies
- `jd_ut` must be finite
- extra fields are rejected

`DistanceExtremesRequest`:

- `body`: string
- `jd_ut`: float

Validation:

- same body and finite-JD rules as `OrbitalElementsRequest`

Admitted bodies:

- `Mercury`
- `Venus`
- `Earth`
- `Mars`
- `Jupiter`
- `Saturn`
- `Uranus`
- `Neptune`
- `Pluto`

Rejected bodies:

- `Sun`
- `Moon`
- nodes, Lilith, lots, stars, asteroids, comets, Uranian points, and any
  other body not admitted by `moira.orbits`

Stage 1 intentionally accepts `jd_ut` rather than a datetime field. This keeps
the route aligned with the engine entrypoints and avoids hiding the time-scale
boundary.

---

## 3. Response Models

`OrbitalElementsResponse`:

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

`DistanceExtremesResponse`:

- `name`
- `perihelion_jd`
- `perihelion_distance_au`
- `aphelion_jd`
- `aphelion_distance_au`

`OrbitRequestEchoResponse`:

- `body`
- `jd_ut`

`OrbitTimeResponse`:

- `input_time_scale`: `UT_JD`
- `state_evaluation_scale`: `TT_internal`
- `delta_t_policy`: `engine_default`

`OrbitProvenanceResponse`:

- `source_module`
- `engine_entrypoint`
- `reader_owner`
- `center`
- `frame`
- `orientation`
- `element_type`
- `state_source`
- `position_basis`
- `apparent_corrections`
- `light_time_correction`
- `mean_element_table`
- `event_basis`, only for distance-extrema routes
- `search_direction`, only for distance-extrema routes
- `chronological_order_forced`, only for distance-extrema routes
- `stage_sequence`

Envelope responses:

- `OrbitalElementsEnvelopeResponse`
- `DistanceExtremesEnvelopeResponse`

Every envelope contains:

- `request`
- `time`
- result block (`elements` or `distance_extremes`)
- `provenance`

---

## 4. Service Design

Expected service file:

- `moira_server/services/orbits.py`

Service functions:

- `compute_orbital_elements`
- `compute_distance_extremes`

Service responsibilities:

- bind the existing engine reader from the request dependency context
- call `orbital_elements_at(body, jd_ut, reader)`
- call `distance_extremes_at(body, jd_ut, reader)`
- serialize dataclass vessels into response models
- add explicit provenance
- do not create or mutate kernel paths
- do not synthesize alternate orbital element products

The service should not route through `/v1/positions/*`, `/v1/nodes/*`, or
generic phenomena transport. Distance extrema may use the engine's existing
`distance_extremes_at` function, which already delegates to phenomena
internally.

---

## 5. Provenance

Orbital-elements route provenance:

- `source_module`: `moira.orbits`
- `engine_entrypoint`: `orbital_elements_at`
- `reader_owner`: `Moira engine instance`
- `center`: `sun`
- `frame`: `J2000_ecliptic_and_equinox`
- `orientation`: `fixed_J2000_ecliptic`
- `element_type`: `osculating`
- `state_source`: `DE_series_kernel`
- `position_basis`: `heliocentric_state_vector`
- `apparent_corrections`: `not_applied`
- `light_time_correction`: `not_applied`
- `mean_element_table`: `not_used`

Distance-extrema route provenance:

- `source_module`: `moira.orbits`
- `engine_entrypoint`: `distance_extremes_at`
- all shared center/frame/source fields above
- `event_basis`: `live_heliocentric_distance_curve`
- `search_direction`: `forward_from_jd_ut`
- `search_owner`: `moira.phenomena`
- `perihelion_event`: `next_local_minimum`
- `aphelion_event`: `next_local_maximum`
- `chronological_order_forced`: `false`

Stage sequence for `elements`:

- `input_validation`
- `reader_binding`
- `engine_call`
- `elements_serialization`
- `provenance_serialization`

Stage sequence for `distance-extremes`:

- `input_validation`
- `reader_binding`
- `engine_call`
- `distance_extrema_serialization`
- `provenance_serialization`

---

## 6. Error Semantics

The routes must reject through the standard `422` validation envelope:

- non-finite `jd_ut`
- empty body names
- unsupported body names
- Sun
- Moon
- extra request fields

Engine-raised `ValueError` for rejected bodies should be converted into the
same validation-style client error used by adjacent server adapters.

Kernel absence should use the existing server error envelope for missing
ephemeris/kernel resources. The route must not repair that by changing kernel
paths.

---

## 7. Implementation Files

Implemented files:

- `moira_server/models/orbits.py`
- `moira_server/services/orbits.py`
- `moira_server/routers/orbits.py`
- `tests/server/test_server_orbits_routes.py`

Router registration:

- export router from `moira_server/routers/__init__.py`
- include router in `moira_server/app.py`
- export response/request models from `moira_server/models/__init__.py`

REST reference update:

- route family count increases by `2`
- `/v1` route count increases by `2`
- `orbits` family row added
- two route table rows added
- Orbital Elements REST Admission Boundary section added

Gap ledger update:

- P-GAP-03 marked `admitted`
- next candidate becomes `P-GAP-04` Generic Phenomena And Solar Conditions

---

## 8. Verification Requirements

Focused server tests:

- successful `POST /v1/orbits/elements` for Earth
- successful `POST /v1/orbits/elements` for Jupiter or Pluto
- successful `POST /v1/orbits/distance-extremes`
- elements response parity with `orbital_elements_at`
- distance-extrema response parity with `distance_extremes_at`
- response includes derived perihelion/aphelion distances for elements
- Sun rejection
- Moon rejection
- unsupported body rejection
- non-finite `jd_ut` rejection
- extra field rejection
- provenance truth for center/frame/element type/state source/correction model
- distance-extrema provenance truth for curve-event semantics
- route registry audit confirming exactly two new `/v1/orbits/*` routes

Implementation verification:

- `python -m py_compile` for new and touched server files
- `python -m pytest tests/server/test_server_orbits_routes.py -q`
- route registry audit confirming two `/v1/orbits/*` routes

No live Horizons network validation is required for REST admission because the
engine subsystem already carries Horizons validation in
`tests/integration/test_horizons_orbits.py`.

---

## 9. Non-Goals

This design does not admit:

- `/v1/orbits/elements/bulk`
- `/v1/orbits/elements/range`
- `/v1/orbits/table`
- datetime convenience requests
- mean element tables
- geocentric lunar elements
- comet orbital elements
- asteroid orbital elements
- Uranian mean elements
- visual-binary Campbell elements
- arbitrary centers or reference planes
- apparent or light-time corrected orbital elements
- kernel path mutation

---

## 10. Admission Result

P-GAP-03 is admitted through:

- `POST /v1/orbits/elements`
- `POST /v1/orbits/distance-extremes`

Recommended status:

- `admitted`
