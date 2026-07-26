# Compatibility Notes - Moira 6.0.0

## Upgrade Boundary

This document covers the public upgrade from `5.2.3` to `6.0.0`.

The major version is required because formerly curated Hermetic Python symbols
have been removed. Several Hellenistic behaviors also now fail closed where
older releases emitted an ambiguous default.

## Removed Curated Python Imports

The following names are no longer available from `moira`,
`moira.classical`, or `moira.facade`:

```text
DecanHour
DecanHoursNight
DECAN_NAMES
DECAN_RULING_STARS
list_decans
available_decans
decan_for_longitude
decan_at
decan_hours
```

Migration:

- Remove all use of `decan_hours`, `DecanHour`, and `DecanHoursNight`; there is
  no supported replacement because the algorithm was not source-admitted.
- Do not substitute ordinary planetary faces or a modern fixed-star table for
  the removed ruling-star assignments.
- Source researchers may import the remaining catalog/geometry objects
  directly from `moira.hermetic_decans`, but that module is explicitly
  quarantined and is not part of the curated product contract.

## Removed Dormant Server Symbols

The unregistered Hermetic catalog, longitude, rising, and night-hour transport
models, services, serializers, and router definitions have been deleted.
`create_app()` did not register those routes in 5.2.3, so no live REST endpoint
is being withdrawn; code that imported the internal server scaffolding must
remove those imports.

Every path under `/v1/hermetic-decans` remains absent and returns `404`.

## Corrected Behavioral Semantics

### Profections

Annual age uses completed civil anniversaries in the natal timezone. It is no
longer derived from elapsed fractional Julian years. February 29 charts must
choose the supported anniversary policy explicitly where the API requires it.

### Triplicity and lots

Dorothean water-triplicity ordering and the two verified lot reversals are
corrected. Callers with stored regression snapshots should expect those
affected outputs to change.

Lot results now distinguish:

- formula computation truth;
- dependency completeness;
- astrological condition status; and
- typed `not_evaluable` entries.

Do not interpret an empty evaluated result and missing dependencies as the same
state.

### Planetary condition

Solar phase, solar proximity, and besieging use typed boundary and dependency
truth. Exact conjunction/opposition, incomplete classical-planet inputs, and
ambiguous neighbour geometry may now be `not_evaluable` instead of becoming a
fabricated label or `False`.

### Decennials

Only L1/L2 are admitted. Requests above level 2 fail validation; no
deep-subdivision method selector is exposed.

The sequence preserves both source distribution coordinates and
elapsed-Julian-day projection. Do not reinterpret projected JDs as civil-month
anniversaries.

### Zodiacal Releasing

Current-period ownership is half-open at transition boundaries. Missing
Fortune produces typed non-evaluability rather than a raw negative peak claim.
Stored results at the same-sign start shift or exact 211-month circuit boundary
should be regenerated.

## New Unified Profile

The new engine composition is available as:

```python
from moira import Moira, hellenistic_chart_profile
```

The new REST route is:

```text
POST /v1/hellenistic/chart-profile
```

The profile is deliberately strict. It requires the complete Classic 7,
finite speeds, valid Whole Sign cusps, actual Ascendant/Midheaven angles, and
timezone-aware natal/current datetimes. Missing or unsupported inputs remain
visible through typed status and provenance.

The profile does not contain Firdaria, medieval almutens, later electional
rules, unscoped primary directions, Decennial L3/L4, Hermetic geometry, Valens
distribution interpretation, or a synthetic overall score.

## REST And OpenAPI Clients

Existing admitted routes remain available. Several response models gain
explicit typed receipt fields. Clients using strict generated models should
regenerate from the 6.0.0 OpenAPI document.

In particular:

- lots chart responses preserve `not_evaluable` entries;
- dignity responses expose typed essential and accidental component truth;
- profection, Decennial, and Zodiacal Releasing responses expose their
  governing assembly receipts; and
- whole-sign aspect responses expose typed Hellenistic superiority.

Compatibility scalar fields remain projections, but new code should use the
typed receipts as the governing truth.

Moira 6.0.0 constrains the optional server stack to `FastAPI>=0.115,<0.137`
and `Starlette>=0.46,<1.3`. Later FastAPI releases changed route-table
internals, while Starlette 1.3 changed the test-client transport contract,
after the 6.0.0 validation baseline. Those new framework contracts are not
admitted by this release. Install `moira-astro[server]==6.0.0` rather than
overriding the declared constraints.

## Recommended Migration Sequence

1. Remove imports of the nine removed Hermetic curated symbols.
2. Delete all use of the unsupported night-hour algorithm.
3. Regenerate REST/OpenAPI clients.
4. Update deserializers to preserve typed `not_evaluable` and provenance
   fields.
5. Refresh stored profection, affected lot, Decennial, and Zodiacal Releasing
   snapshots.
6. Reject Decennial levels above 2 in caller-side controls.
7. Run application tests against `moira-astro==6.0.0`.

## Unchanged Boundaries

This release does not change the planetary-kernel format, native extension
ABI policy, supported Python range, astronomical frame definitions, or
small-body resource installation model.

## Upgrade Pin

```text
moira-astro==6.0.0
```
