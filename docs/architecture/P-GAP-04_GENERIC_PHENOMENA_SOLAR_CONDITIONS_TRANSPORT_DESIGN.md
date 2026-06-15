# P-GAP-04 Generic Phenomena And Solar Conditions Transport Design

Version: 0.2
Date: 2026-06-14
Status: implemented and admitted
Scope: bounded REST admission plan for generic planetary phenomena, proximity
threshold crossings, and classical solar-condition truth

This design follows
`wiki/02_standards/GENERIC_PHENOMENA_SOLAR_CONDITIONS_BACKEND_STANDARD.md`.

P-GAP-04 evaluates the facade/root surfaces:

- `planet_phenomena_at`
- `Moira.phenomena`
- `proximity_events_in_range`
- `Moira.proximity_events`
- `solar_condition_at`
- `Moira.solar_condition_at`
- `solar_condition_events_in_range`
- `Moira.solar_condition_events`

These are not one product. The transport design keeps instant phenomena,
orbital event search, proximity threshold crossing, and classical
solar-condition truth visibly separate.

---

## 1. Route Family

Prefixes:

- `/v1/phenomena`
- `/v1/solar-condition`

Routes:

- `POST /v1/phenomena/planet`
- `POST /v1/phenomena/orbital-events`
- `POST /v1/phenomena/proximity`
- `POST /v1/solar-condition/instant`
- `POST /v1/solar-condition/events`

Route naming doctrine:

- `planet` means one instant's physical/photometric phenomena snapshot.
- `orbital-events` means bounded search for admitted elongation/apside events.
- `proximity` means angular threshold ingress/egress crossings.
- `solar-condition` keeps classical cazimi/combust/under-sunbeams doctrine
  distinct from generic events.

---

## 2. Request Models

`PlanetPhenomenaRequest`:

- `body`: string
- `jd_ut`: float

Validation:

- body must be non-empty
- `jd_ut` must be finite
- extra fields rejected

`OrbitalPhenomenaEventsRequest`:

- `body`: string
- `jd_start`: float
- `jd_end`: float
- `event_kinds`: list of strings, optional

Admitted event kinds:

- `greatest_eastern_elongation`
- `greatest_western_elongation`
- `perihelion`
- `aphelion`

Validation:

- body must be non-empty
- all JD values finite
- `jd_end >= jd_start`
- span must be <= `5000` days
- event kinds must be non-empty after trimming
- event kinds must be admitted
- greatest elongation kinds are valid only for Mercury and Venus

Default `event_kinds`:

- for Mercury/Venus: all four admitted event kinds
- for other admitted planets: `perihelion`, `aphelion`

`ProximityEventsRequest`:

- `body1`: string
- `body2`: string
- `jd_start`: float
- `jd_end`: float
- `threshold_deg`: float

Validation:

- bodies must be non-empty
- bodies must differ
- all numeric values finite
- `jd_end >= jd_start`
- span must be <= `1200` days
- `threshold_deg` must be in `(0, 30]`

`SolarConditionInstantRequest`:

- `body`: string
- `jd_ut`: float

Validation:

- body must be non-empty
- `jd_ut` must be finite

Luminary policy:

- Sun and Moon are accepted and return absent truth, matching the engine.

`SolarConditionEventsRequest`:

- `body`: string
- `jd_start`: float
- `jd_end`: float
- `condition`: string, default `cazimi`

Admitted conditions:

- `cazimi`
- `combust`
- `under_sunbeams`

Validation:

- body must be non-empty
- body must not be Sun or Moon
- all JD values finite
- `jd_end >= jd_start`
- span must be <= `1200` days
- condition must be admitted

---

## 3. Response Models

`PlanetPhenomenaResponse`:

- `body`
- `jd_ut`
- `phase_angle_deg`
- `illuminated_fraction`
- `elongation_deg`
- `angular_diameter_arcsec`
- `apparent_magnitude`

`PhenomenonEventResponse`:

- `body`
- `event_kind`
- `label`
- `jd_ut`
- `datetime_utc`
- `value`
- `value_unit`

`ProximityEventResponse`:

- `body1`
- `body2`
- `jd_ut`
- `datetime_utc`
- `threshold_deg`
- `threshold_abs_deg`
- `body1_longitude`
- `body2_longitude`
- `body2_latitude`
- `body2_retrograde`
- `is_ingress`
- `label`

`SolarConditionTruthResponse`:

- `body`
- `jd_ut`
- `present`
- `condition`
- `label`
- `score`
- `distance_from_sun`
- `distance_unit`: `degrees`

Envelope responses:

- `PlanetPhenomenaEnvelopeResponse`
- `OrbitalPhenomenaEventsEnvelopeResponse`
- `ProximityEventsEnvelopeResponse`
- `SolarConditionInstantEnvelopeResponse`
- `SolarConditionEventsEnvelopeResponse`

Every envelope contains:

- `request`
- result block
- `provenance`

---

## 4. Service Design

Expected service file:

- `moira_server/services/generic_phenomena.py`

Service functions:

- `compute_planet_phenomena`
- `compute_orbital_phenomena_events`
- `compute_proximity_events`
- `compute_solar_condition_instant`
- `compute_solar_condition_events`

Service responsibilities:

- bind the existing engine reader from the request dependency context where
  the engine function accepts a reader
- call existing engine/facade functions without reimplementing search logic
- map event labels to canonical `event_kind` values
- attach explicit value units
- preserve solar-condition threshold policy
- avoid route-through side effects in unrelated route families

The service must not synthesize a generic catch-all event model that obscures
which engine function produced the result.

---

## 5. Provenance

Shared provenance fields:

- `source_module`: `moira.phenomena`
- `engine_entrypoint`
- `reader_owner`
- `time_scale`: `UT_JD`
- `product_kind`
- `event_taxonomy`
- `stage_sequence`

Planet phenomena provenance:

- `engine_entrypoint`: `planet_phenomena_at`
- `product_kind`: `instantaneous_planet_phenomena_snapshot`
- `search_performed`: `false`
- `phase_photometry_source`: `moira.phase`

Orbital events provenance:

- `engine_entrypoint`: `Moira.phenomena`
- `product_kind`: `bounded_orbital_event_search`
- `admitted_event_kinds`
- `value_units_by_kind`
- `search_span_days`

Proximity provenance:

- `engine_entrypoint`: `proximity_events_in_range`
- `product_kind`: `angular_proximity_threshold_crossing`
- `threshold_unit`: `degrees`
- `event_direction_model`: `ingress_when_separation_decreasing`

Solar condition instant provenance:

- `engine_entrypoint`: `solar_condition_at`
- `product_kind`: `classical_solar_condition_truth`
- `thresholds_deg`
- `luminary_policy`: `Sun and Moon return absent truth`
- `dignity_interpretation`: `not_returned`
- `recommendation_language`: `not_returned`

Solar condition events provenance:

- `engine_entrypoint`: `solar_condition_events_in_range`
- all solar-condition threshold fields above
- `product_kind`: `classical_solar_condition_threshold_crossings`

---

## 6. Error Semantics

The routes must reject through the standard `422` validation envelope:

- non-finite JD values
- reversed JD windows
- oversized search windows
- empty body names
- equal proximity body names
- non-positive proximity thresholds
- proximity thresholds greater than `30` degrees
- unsupported event kinds
- greatest elongation requested for non-inner planets
- invalid solar condition names
- Sun or Moon supplied to solar-condition event search
- extra request fields

Kernel absence should use the existing server error envelope for missing
ephemeris/kernel resources. The route must not repair that by changing kernel
paths.

---

## 7. Implementation Files

Implemented files:

- `moira_server/models/generic_phenomena.py`
- `moira_server/services/generic_phenomena.py`
- `moira_server/routers/generic_phenomena.py`
- `tests/server/test_server_generic_phenomena_routes.py`

Router registration:

- export router from `moira_server/routers/__init__.py`
- include router in `moira_server/app.py`
- export response/request models from `moira_server/models/__init__.py`

REST reference update:

- route group count increases by `2`
- `/v1` route count increases by `5`
- `phenomena` family count increases for three new routes
- `solar-condition` family row added with two routes
- route table rows added
- Generic Phenomena And Solar Conditions REST Admission Boundary section added

Gap ledger update:

- P-GAP-04 marked `admitted`
- next candidate becomes `P-GAP-05` Sidereal/Nakshatra Utility Primitives

---

## 8. Verification Requirements

Focused server tests:

- successful planet phenomena instant route
- planet phenomena parity with `planet_phenomena_at`
- successful orbital events route for Mercury/Venus including elongation
- successful orbital events route for a non-inner planet with apsides only
- greatest elongation rejection for non-inner planet
- proximity route parity with `proximity_events_in_range`
- proximity equal-body rejection
- proximity threshold bounds rejection
- solar condition instant parity with `solar_condition_at`
- solar condition instant luminary absent-truth behavior
- solar condition events parity with `solar_condition_events_in_range`
- invalid solar condition rejection
- Sun/Moon solar-condition event rejection
- non-finite JD rejection
- reversed range rejection
- oversized range rejection
- extra field rejection
- provenance truth for each product kind
- route registry audit confirming the admitted route set

Implementation verification:

- `python -m py_compile` for new and touched server files
- `python -m pytest tests/server/test_server_generic_phenomena_routes.py -q`
- route registry audit confirming the five designed routes

No new astronomy-oracle validation is required for REST admission. The route
tests prove adapter truth over existing engine functions.

---

## 9. Non-Goals

This design does not admit:

- `/v1/events`
- generic catch-all event search
- arbitrary phenomenon names
- arbitrary predicates or scorers
- recommendation/advice language
- dignity condition profiles or networks
- aspect searches
- conjunction route families
- heliocentric conjunction route families
- station/lunar phase/rise-set/heliacal/eclipse/occultation replacements
- dense event tables
- async jobs
- small-body proximity sweeps
- kernel path mutation

---

## 10. Admission Result

P-GAP-04 is implemented and admitted.

Admitted implementation surface:

- `POST /v1/phenomena/planet`
- `POST /v1/phenomena/orbital-events`
- `POST /v1/phenomena/proximity`
- `POST /v1/solar-condition/instant`
- `POST /v1/solar-condition/events`

Verification performed:

- `.venv\Scripts\python.exe -m py_compile moira_server\models\generic_phenomena.py moira_server\services\generic_phenomena.py moira_server\routers\generic_phenomena.py moira_server\app.py moira_server\models\__init__.py`
- `.venv\Scripts\python.exe -m pytest tests/server/test_server_generic_phenomena_routes.py -q`
- live route registry audit confirmed five P-GAP-04 routes, `332`
  versioned `/v1` routes, and `336` total non-documentation routes
