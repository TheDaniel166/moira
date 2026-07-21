# Compatibility Notes — Moira 5.1.0

Date: 2026-07-21

This document covers the caller-visible upgrade from `5.0.0` to `5.1.0`.
The release is primarily additive. Existing default dignity results are
preserved, and Pancha Pakshi requires explicit profile and timing policy
selection.

## New public surfaces

### Pancha Pakshi

Moira now exports immutable Pancha Pakshi policy, provenance, schedule,
selection, relation, condition, aggregate, network, and constitution-status
vessels. Corresponding facade methods and typed `/v1/pancha-pakshi` routes are
available.

Callers must not assume an ambient canon or default profile. Supply a profile
identifier and the timing/selector policy required by the chosen product.
Unsupported capabilities, conflicting evidence, and missing policies fail
explicitly.

REST consumers should regenerate strict client models because the OpenAPI
document includes the new routes and schemas. Exact rational durations are
encoded as numerator/denominator objects rather than binary floating-point
values.

### Dignity inclusion controls

The shared dignity policy now includes:

- `accidental.sect.include_halb`;
- `accidental.include_oriental_occidental`.

`accidental.sect.include_hayz` remains independently available. All three
default to `true`, so callers that omit them retain 5.0.0 behavior. A disabled
condition is absent from labels, structured accidental truth, and its score
contribution.

Strict REST request models should accept the two new optional Boolean fields.
Unknown dignity policy fields continue to receive a validation error.

## Behavioral correction

`find_phenomena()` may now omit `Transit` or `AntiTransit` when that event does
not occur in the requested 24-hour interval. Previously, the no-bracket error
could escape and abort an otherwise valid rise/set result. Consumers must
already treat event keys as optional according to the documented result shape.

Direct `get_transit()` behavior is unchanged: it raises when no requested
meridian crossing can be bracketed inside the 24-hour window.

## No scoring migration

Pancha Pakshi does not add a generic numerical strength score. Existing source
classes, conflicts, and relation/condition objects remain discrete,
inspectable results. Applications may present those facts but should not infer
an undocumented good/bad scale from their ordering.

## Upgrade checklist

1. Upgrade the package and regenerate REST/OpenAPI clients if used.
2. Select a Pancha Pakshi profile and timing policy explicitly.
3. Keep the new dignity flags omitted or `true` to preserve 5.0.0 output.
4. Treat `Transit` and `AntiTransit` as optional keys in `find_phenomena()`.
5. Do not rely on a default Pancha Pakshi profile or an inferred numerical
   score.
