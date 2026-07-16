# Moon Connection Flow Validation — 2026-07-15

## Product under test

This ledger covers the neutral `MoonConnectionFlow` geometry exposed by:

- `moira.aspect_events.moon_connection_flow_at(...)`;
- `Moira.moon_connection_flow_at(...)`;
- `POST /v1/aspects/moon-connection-flow`;
- the nested `moon_connection_flow` member of Dorotheus V.9 leasing results.

It does not validate an astrological outcome, a fortune/infortune assignment,
or a complete leasing judgement.

## Computational semantics

- Positions are apparent geocentric longitudes in the true ecliptic and
  equinox of date from Moira's planetary pipeline.
- Input epochs are UT1 Julian days; the planetary pipeline performs its own TT
  conversion.
- Exact events are the established eight directional forms of the five major
  aspects.
- The prior search window is caller-declared as either the current tropical
  sign or a positive bounded fixed lookback.
- The next search is bounded by the Moon's current tropical-sign egress.
- Previous and next events are strictly before and after the query instant.
- Current motion delegates to the signed `AspectMotionWitness`; no event
  absence or stationary state is flattened into applying/separating truth.
- Motion speeds are the canonical `PlanetData.speed` product: derivatives of
  corrected geocentric ecliptic longitude. Existing REST compatibility
  identifiers still contain the historical word `astrometric`; this
  substrate correction does not change those response literals or models.

## Source boundary

Dorotheus, *Carmen Astrologicum* V.9.8 states that the Moon's flow-away and
connection indicate the leasing matters described in V.9. V.6.27-31 supports
the general prior/root and next/outcome sequence. V.10 and V.29 show that
matter chapters may assign these events to particular parties or temporal
roles. The surviving V.9 passage does not assign them to its four named
leasing stakes. Consequently the geometry is transported in full while the
V.9 clause remains `not_evaluable` pending the fuller Theophilus/Hephaistion
parallel.

## Evidence classes

- Invariant tests prove policy coherence, strict event ordering, exact search
  bounds, last-prior/first-next selection, signed time direction, and explicit
  no-event reasons.
- DE441 regression evidence at JD 2451545.0 traces the current-sign previous
  event, instantaneous motion, and next current-sign connection through engine
  and leasing vessels.
- REST tests prove every policy, event, motion, provenance, and boundary field
  survives serialization and appears in OpenAPI.
- Public-surface tests prove root, facade, and module admission.

DE441 regression is regression and invariant evidence for the named product;
it is not an external doctrinal oracle or empirical proof of astrology.
