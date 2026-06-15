# Generic Phenomena And Solar Conditions Backend Standard

Version: 0.2
Date: 2026-06-14
Status: implemented backend standard for P-GAP-04 REST admission
Scope: generic planetary phenomena, proximity threshold events, and classical
solar-condition truth

This standard governs the generic phenomena and solar-condition surfaces that
are public through the Python engine and candidates for P-GAP-04 REST
admission:

- `moira.phenomena.PhenomenonEvent`
- `moira.phenomena.PlanetPhenomena`
- `moira.phenomena.ProximityEvent`
- `moira.phenomena.planet_phenomena_at`
- `moira.phenomena.greatest_elongation`
- `moira.phenomena.perihelion`
- `moira.phenomena.aphelion`
- `moira.phenomena.proximity_events_in_range`
- `moira.phenomena.solar_condition_at`
- `moira.phenomena.solar_condition_events_in_range`
- `Moira.phenomena`
- `Moira.proximity_events`
- `Moira.solar_condition_at`
- `Moira.solar_condition_events`

This standard does not govern rise/set phenomena, heliacal visibility,
eclipses, occultations, lunar phases, stations, transits, orbital elements, or
dignity profile interpretation. Those are already owned by their own route
families or backend standards.

---

## 1. Governing Objects

P-GAP-04 has four distinct governing objects.

### Planet Phenomena Snapshot

Owned by:

- `moira.phenomena.PlanetPhenomena`
- `moira.phenomena.planet_phenomena_at`

Meaning:

- instantaneous photometric/geometric state for one body at one `jd_ut`
- includes phase angle, illuminated fraction, elongation, angular diameter,
  and apparent magnitude
- does not search for events
- does not return rise/set, heliacal visibility, station, or transit status

Admitted fields:

- `body`
- `jd_ut`
- `phase_angle_deg`
- `illuminated_fraction`
- `elongation_deg`
- `angular_diameter_arcsec`
- `apparent_magnitude`

### Generic Orbital Phenomenon Event

Owned by:

- `moira.phenomena.PhenomenonEvent`
- `moira.phenomena.greatest_elongation`
- `moira.phenomena.perihelion`
- `moira.phenomena.aphelion`
- `Moira.phenomena`

Meaning:

- discrete heliocentric or geocentric orbital event in a bounded date range
- greatest elongation is admitted only for Mercury and Venus
- perihelion and aphelion are heliocentric distance-curve events
- event `value` semantics depend on event kind and must be labeled

Admitted event kinds:

- `greatest_eastern_elongation`
- `greatest_western_elongation`
- `perihelion`
- `aphelion`

Admitted event fields:

- `body`
- `event_kind`
- `label`
- `jd_ut`
- `datetime_utc`
- `value`
- `value_unit`

### Proximity Threshold Event

Owned by:

- `moira.phenomena.ProximityEvent`
- `moira.phenomena.proximity_events_in_range`
- `Moira.proximity_events`

Meaning:

- ingress/egress crossing of an angular separation threshold between two
  bodies around conjunctions
- threshold is caller supplied and explicit
- event direction is ingress when separation is decreasing at the crossing
- this is not an aspect search, transit interpretation, or recommendation

Admitted fields:

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

### Solar Condition Truth

Owned by:

- `moira.dignities_types.SolarConditionTruth`
- `moira.phenomena.solar_condition_at`
- `moira.phenomena.solar_condition_events_in_range`
- `Moira.solar_condition_at`
- `Moira.solar_condition_events`

Meaning:

- classical solar proximity condition for one non-luminary planet
- conditions are threshold bands around the Sun
- luminaries return absent truth for instant checks
- event search returns ingress/egress threshold crossings for one named band

Admitted solar condition bands:

- `cazimi`: `17 / 60` degrees
- `combust`: `8` degrees
- `under_sunbeams`: `17` degrees

Admitted instant fields:

- `body`
- `jd_ut`
- `present`
- `condition`
- `label`
- `score`
- `distance_from_sun`

Admitted event fields:

- same fields as proximity events, with condition label and threshold policy
  preserved

---

## 2. Route Admission Boundary

P-GAP-04 admits a bounded synchronous REST family under two explicit
prefixes:

- `/v1/phenomena/*`
- `/v1/solar-condition/*`

Stage 1 routes are limited to:

- `POST /v1/phenomena/planet`
- `POST /v1/phenomena/orbital-events`
- `POST /v1/phenomena/proximity`
- `POST /v1/solar-condition/instant`
- `POST /v1/solar-condition/events`

The split is intentional:

- `/v1/phenomena/planet` is an instantaneous physical snapshot.
- `/v1/phenomena/orbital-events` is a bounded event search over admitted event
  kinds.
- `/v1/phenomena/proximity` is a generic threshold-crossing search.
- `/v1/solar-condition/*` is classical solar-condition doctrine and should not
  be hidden inside a vague generic event label.

---

## 3. Body Admission

Planet phenomena snapshot:

- admit bodies supported by `planet_phenomena_at`
- reject empty body names
- reject unsupported body names through the engine/server validation path

Orbital event search:

- `greatest_eastern_elongation` and `greatest_western_elongation`: Mercury
  and Venus only
- `perihelion` and `aphelion`: major planets admitted by the live engine
- reject Sun and Moon for perihelion/aphelion public transport
- reject small bodies unless a separate small-body orbital event standard is
  admitted

Proximity events:

- Stage 1 should admit major planetary bodies and luminaries supported by the
  ordinary `planet_at` path
- reject empty body names
- reject equal body pairs
- reject unsupported small-body/catalog identities

Solar condition:

- instant route accepts named bodies but returns absent truth for Sun and Moon,
  matching engine truth
- event route rejects Sun and Moon because solar-condition ingress/egress is
  not meaningful for luminaries
- event route admits non-luminary major planets supported by the live engine

---

## 4. Time And Search Bounds

Every Stage 1 request uses `jd_ut`, matching the engine entrypoints.

Transport must validate:

- all JD values are finite
- `jd_end >= jd_start`
- bounded event/proximity/search span
- positive finite `max_days`, where exposed
- positive finite proximity threshold

Initial public bounds:

- maximum orbital-event search span: `5000` days
- maximum proximity search span: `1200` days
- maximum solar-condition event search span: `1200` days
- proximity threshold range: `(0, 30]` degrees

The span limits protect synchronous REST behavior. Larger ephemeris sweeps
require a separate async or batch admission packet.

---

## 5. Event Taxonomy And Value Semantics

Transport must not return an unlabeled `value` field without a unit.

Generic orbital event values:

- greatest elongation: `value_unit = "degrees"`
- perihelion: `value_unit = "AU"`
- aphelion: `value_unit = "AU"`

Proximity values:

- `threshold_deg` preserves signed threshold truth from the engine event
- `threshold_abs_deg` preserves the caller's positive threshold magnitude
- ingress/egress is explicit through `is_ingress`

Solar condition:

- instant `distance_from_sun` is in degrees
- event threshold is in degrees
- `score` is the engine's current classical dignity score contribution, not a
  recommendation or probability

---

## 6. Provenance Requirements

Every response must state:

- `source_module`: `moira.phenomena`
- `engine_entrypoint`
- `reader_owner`
- `time_scale`: `UT_JD`
- `event_taxonomy`
- `stage_sequence`

Planet snapshot provenance must state:

- `product_kind`: `instantaneous_planet_phenomena_snapshot`
- `search_performed`: `false`
- `phase_photometry_source`: `moira.phase`

Orbital event provenance must state:

- `product_kind`: `bounded_orbital_event_search`
- `admitted_event_kinds`
- `value_units_by_kind`
- `search_span_days`

Proximity provenance must state:

- `product_kind`: `angular_proximity_threshold_crossing`
- `threshold_unit`: `degrees`
- `event_direction_model`: `ingress_when_separation_decreasing`
- `conjunction_search_owner`: `moira.phenomena`

Solar condition provenance must state:

- `product_kind`: `classical_solar_condition_truth`
- `thresholds_deg`
- `luminary_policy`
- `dignity_interpretation`: `not_returned`
- `recommendation_language`: `not_returned`

---

## 7. Non-Goals

P-GAP-04 does not admit:

- catch-all `/v1/events` routes
- arbitrary phenomenon names
- arbitrary predicates or scorers
- astrological recommendations
- dignity profile/network outputs
- aspect searches
- station searches
- lunar phase routes
- rise/set or heliacal visibility routes
- eclipse or occultation routes
- conjunction routes beyond proximity's internal ownership
- heliocentric conjunction routes
- dense ephemeris/event tables
- async jobs
- small-body proximity sweeps
- catalog-wide searches
- kernel path mutation

---

## 8. Verification Requirements

Before REST admission, tests must cover:

- planet phenomena instant route parity with `planet_phenomena_at`
- orbital event route parity with `Moira.phenomena` or direct admitted engine
  calls
- proximity route parity with `proximity_events_in_range`
- solar-condition instant route parity with `solar_condition_at`
- solar-condition events route parity with `solar_condition_events_in_range`
- invalid event kind rejection
- unsupported greatest-elongation body rejection
- invalid solar condition rejection
- non-finite JD rejection
- reversed range rejection
- oversized range rejection
- non-positive threshold rejection
- equal proximity body rejection
- provenance truth for product kind, event taxonomy, thresholds, and
  non-recommendation boundary
- route registry audit confirming the admitted route set

---

## 9. Admission Decision

P-GAP-04 is admitted through:

- `POST /v1/phenomena/planet`
- `POST /v1/phenomena/orbital-events`
- `POST /v1/phenomena/proximity`
- `POST /v1/solar-condition/instant`
- `POST /v1/solar-condition/events`

Reason:

- the engine surfaces already exist
- facade methods expose the key searches and instant solar-condition query
- the transport keeps instant phenomena, orbital events, proximity events, and
  solar-condition truth separate
- focused server tests cover adapter truth, validation rejection, provenance,
  and route method boundaries

The admitted status does not broaden the engine doctrine. Dense sweeps,
small-body proximity searches, catch-all event routes, interpretive text, and
recommendation language remain outside this standard.
