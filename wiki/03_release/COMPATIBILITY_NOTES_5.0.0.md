# Compatibility Notes — Moira 5.0.0

Date: 2026-07-19

This document covers the caller-visible upgrade boundary from the last public
release, `4.2.1`, to `5.0.0`. The internal `4.3.0` version was never tagged or
published; its Western electional work is included in `5.0.0`.

## Changes that can break callers

### Relationship results are immutable

Synastry truth, classification, relation, condition, network, overlay,
composite, and Davison result vessels are frozen. Nested planet, node,
placement, and custom-orb maps are defensive read-only mappings, and composite
cusps are tuples.

Code that previously changed returned objects in place must construct a new
value instead. For dataclass fields, `dataclasses.replace(...)` is often the
smallest migration:

```python
from dataclasses import replace

updated = replace(result, method="alternate_method")
```

Copy a nested mapping when deriving application-owned mutable state:

```python
editable_planets = dict(composite.planets)
```

The REST response shapes remain JSON-compatible; this change affects Python
callers that mutate engine vessels.

### Readiness now uses HTTP 503

`GET /ready` keeps the existing `ReadyResponse` body but returns:

- HTTP 200 only when the worker can accept computational traffic;
- HTTP 503 when the planetary kernel or enabled startup prewarm is not ready.

`GET /health` remains an HTTP 200 liveness signal. Load balancers, deployment
probes, and clients must accept and decode the readiness body on HTTP 503 rather
than treating every non-200 response as an unstructured transport failure.

### Invalid inputs no longer receive implicit repair

Several engine boundaries now reject inputs that older releases tolerated or
coerced:

- planetary observer latitude, longitude, and elevation must be supplied as
  one complete topocentric vessel;
- invalid centers, non-finite epochs, coordinates, windows, bodies, harmonic
  values, and contradictory policies fail explicitly;
- house coordinates must remain within their physical latitude/longitude
  domains, and configured house fallbacks preserve an explicit reason;
- planetary-hour computation fails when polar geometry has no lawful sunrise
  or sunset instead of inventing a schedule;
- phenomena searches reject invalid direction, threshold, interval, body, and
  resonance inputs;
- advanced primary-direction searches reject ambiguous, unsupported, or
  scientifically incomplete contexts; signed-primary-motion searches require
  explicit non-empty significator and promissor filters.

REST callers should expect the corresponding validation response. Direct
engine callers should validate user input or handle the documented
`ValueError`/domain-specific failure at their input boundary.

### Chaldean bounds require an explicit sect

The ambiguous `EgyptianBoundsDoctrine.CHALDEAN`/`"chaldean"` selector and
`CHALDEAN_BOUNDS` table have been replaced by:

- `EgyptianBoundsDoctrine.CHALDEAN_DAY`, `"chaldean_day"`, and
  `CHALDEAN_DAY_BOUNDS`;
- `EgyptianBoundsDoctrine.CHALDEAN_NIGHT`, `"chaldean_night"`, and
  `CHALDEAN_NIGHT_BOUNDS`.

Choose the day or night table from the chart's sect explicitly. There is no
compatibility alias because retaining one would preserve the ambiguity the
repair removes.

### The Ramesey remedy response is version 1.1.0

The public `ramesey_moon_condition_v1` profile now reports non-erasing
tri-state remedy fulfillment with clause evidence. Its `profile_version`
changes from `1.0.0` to `1.1.0`, and the instruction-only assessment literal
is replaced by the typed fulfillment fields. Update strict response models and
do not treat an indeterminate source predicate as false or as erasing an
otherwise applicable impediment.

## Numerical products that intentionally change

The following corrections preserve their public method and route identities
but can change computed values. Rebaseline application snapshots that relied
on `4.2.1` output:

- Delta T, historical civil-time conversion, pre-1972 atomic offsets, and
  UT1/TT/UTC boundary behavior;
- apparent, geometric, topocentric, heliocentric, planetocentric, received-
  light, and Solar System barycentric planetary frame reductions;
- published planetary longitude speed and retrograde truth;
- solar and lunar eclipse maxima, contacts, local visibility, global central
  classification, paths, widths, and NASA-compatibility products;
- greatest elongation, perihelion/aphelion, conjunction-window, proximity, and
  resonance searches;
- sunrise/sunset boundaries and local-mean-solar weekday assignment for
  planetary hours;
- house UT1 routing, high-latitude policy, and invalid-input behavior;
- synastry identity/provenance and Davison midpoint/MC failure behavior.

These are model and correctness changes, not claims that every corrected field
is exact to an external catalog. The release notes and validation entries name
the authority, model differences, and regression envelopes actually exercised.

## Compatible additions

No established `/v1` computation path is removed or renamed. Important
additive surfaces include:

- first-class Parallel and Contra-Parallel analysis and motion witnesses;
- fractional positive-real single-harmonic calculations, explicit Addey orb
  policy, and sampled harmonic-transit forecasts;
- structured pattern roles and cross-detector `dominant_only` containment;
- advanced primary-direction request contexts and facade evaluation methods;
- solar Besselian elements, partial-visibility footprints, polar-safe
  occultation topology, and topography-conditioned lunar contacts under their
  documented engine/facade/REST admission boundaries;
- source-owned Western electional profiles staged during 4.3 development.

The age-harmonic route and integer harmonic range/sweep semantics remain
available. Existing declination-aspect imports and the original analysis route
remain available. Existing eclipse event/path and occultation summary vessels
retain their established shapes where the changelog says so.

## Operational changes

`MOIRA_SERVER_PREWARM=1` is opt-in and paid independently by every server
worker. The measured Windows/DE441 smoke moved first-chart work into startup
but used approximately `1.65 GiB` of private working set per prewarmed worker.
Capacity planning must multiply that cost by the configured worker count.

The native extension now performs runtime AVX2 dispatch on capable x86 hosts;
unsupported processors keep the scalar path. Published wheels do not acquire a
global AVX2 requirement.

## Upgrade checklist

1. Replace in-place relationship-result mutation with construction or copied
   application state.
2. Update readiness probes to treat HTTP 503 plus `ReadyResponse` as a normal
   not-ready result.
3. Replace ambiguous Chaldean-bounds imports/selectors with the explicit day or
   night identity, and update strict Ramesey response models to version 1.1.0.
4. Validate external inputs before calling newly strict engine boundaries and
   expose REST validation failures clearly to clients.
5. Rebaseline numerical snapshots only after checking each product's declared
   frame, time scale, correction regime, observer semantics, and validation
   envelope.
6. Keep prewarm disabled until per-worker DE441 memory has been budgeted.
7. Regenerate typed REST clients from the 5.0.0 OpenAPI document if they consume
   newly additive request or response members.
