# Moira 4.0.1 — Fixed-Star Paran Product Surface

Moira 4.0.1 turns the existing fixed-star paran capability into a complete,
inspectable product surface for Urania Workspace and other API consumers.
The astronomical computation was already capable of planet-star and star-star
parans; this release adds the engine-owned selection doctrine, diagnostics,
field proof, policy sharing, and transport contracts required to use that
truth without client-side invention.

## Highlights

### Engine-owned paran star canon

The new paran canon provides one deterministic working set with membership
tags for Royal, Behenian, Ptolemaic, and working-canon stars. It delegates all
identity, position, proper-motion, magnitude, and provenance truth to Moira's
sovereign star registry.

Available through:

- `moira.paran_stars`
- `moira.facade`
- `GET /v1/parans/star-canon`

The REST endpoint returns the 51 working-canon identities currently resolved
by the packaged sovereign catalog, with stable tier membership suitable for
building a picker.

### Honest crossing inventories

Detailed paran searches can now report all four mundane circles for every
requested body and distinguish:

- `found`
- `always_above_horizon`
- `always_below_horizon`
- `solver_failure`

This makes it possible for clients to distinguish an ordinary empty paran list
from a star that never crosses the adopted horizon at the requested latitude.
The diagnostic envelope uses the same geometric altitude signal and
`-0.5667` degree stellar horizon used by the paran event search.

### Birth-moment angular contacts

`natal_angular_contacts()` and
`POST /v1/parans/natal-angular-contacts` expose individual planet or fixed-star
crossings within a declared time orb of the birth moment.

This remains explicitly separate from `natal_parans()`, which continues to
search the full birth day for two-body paran relationships.

### Shared policy presets

The engine and REST surface now share immutable named presets:

- `permissive` — existing default behavior
- `star_planet_only` — admits planet-star pairs while excluding planet-planet
  and star-star results

Policy selection propagates through search, natal, site, stability, field,
analysis, contours, paths, structure, and website packet computation.

### Fixed-star map pipeline

A live Regulus Setting / Capella AntiCulminating target is now regression-pinned
through the complete geographic pipeline:

```text
site → grid → analysis → contour segments → paths → field structure → REST
```

The star-only path remains kernel-free and reports orphan contour segments
explicitly rather than discarding them.

### Urania Workspace packet

`POST /v1/website/parans/packet` composes selected canon, paran events,
crossing inventories, natal angular contacts, and optional heliacal events into
one bounded website response. Large geographic grids remain on the dedicated
field endpoints.

Heliacal star computation requires planetary-kernel access because its solar
ephemeris is part of the astronomical truth. If that resource is unavailable,
the packet reports the prerequisite instead of substituting an approximation.

## Fixes

- Restored field threshold-crossing serialization for REST grids that actually
  cross their requested metric threshold.
- Corrected paran documentation so fixed-star inputs, time-orb units, field
  signatures, policy selection, and kernel boundaries match runtime truth.
- Expanded README and LLM-facing documentation for the broader 4.0 Vedic API
  suite already present on `main` after the 4.0.0 tag.

## Compatibility

Moira 4.0.1 is additive:

- `find_parans()` still returns `list[Paran]`.
- `natal_parans()` still searches the complete birth day.
- The default paran policy remains permissive.
- Existing event times and planetary paran matching are unchanged.
- The full 1,809-name star catalog remains separate from the smaller paran
  working canon.

## Validation

Validation used the project `.venv` on Python 3.14 with strict known-issue
expiry checking. It covered:

- complete paran, public-surface, rise/set, and canon unit slices;
- kernel-free website packet and fixed-star field REST routes;
- OpenAPI route and tag discoverability;
- focused existing phenomena routes;
- Python compilation and release-facing documentation consistency;
- three offline JPL Horizons paran reference cases with a 5-second event-time
  tolerance.

The fixed-star tests establish deterministic catalog-to-crossing-to-paran and
field-pipeline regression truth. No new independent external fixed-star event
oracle is claimed by this release.
