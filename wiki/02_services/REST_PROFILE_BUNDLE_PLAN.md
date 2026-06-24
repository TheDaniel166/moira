# REST Profile Bundle Plan

Date opened: 2026-06-23
Authority layer: REST transport planning
Implemented MVP routes:

- `POST /v1/western/chart-profile`
- `POST /v1/vedic/chart-profile`

This document is the planning companion to
`wiki/02_services/REST_API_REFERENCE.md`. The reference document records live
registered route truth. This document records the shape and admission rules for
larger convenience bundles.

## Governing Boundary

Profile bundles are composition surfaces. They collect existing route-equivalent
computational strata into one response for frontend and workspace callers.

They must not:

- introduce interpretive synthesis language
- merge Western and Vedic doctrine into one hidden profile
- weaken request validation from the underlying route families
- hide chart, house, dignity, Panchanga, Shadbala, or dasha provenance
- replace engine-family routes as the canonical public computation surface

## Implemented MVP Shape

### Western Chart Profile

Route: `POST /v1/western/chart-profile`

Default sections:

- chart result and chart reduction truth
- houses result and houses reduction truth
- classical dignity result
- classical dignity chart-condition profile

Inputs preserve:

- timezone-aware natal datetime
- observer latitude, longitude, and elevation
- house-system selection
- optional chart body selection and node inclusion
- optional house policy
- optional dignity computation policy

### Vedic Chart Profile

Route: `POST /v1/vedic/chart-profile`

Default sections:

- chart result and chart reduction truth
- Panchanga result
- Panchanga profile
- Shadbala result
- Shadbala chart profile

Opt-in sections:

- Vimshottari current active line
- Vimshottari lord-pair snapshot

Dasha sections require `current_dt` because they are not natal-only products.

## Next Admission Candidates

Western next candidates:

- lots chart result and lot profile
- triplicity assignments or score
- Egyptian bounds and decanate placement
- timelord snapshot surfaces where the required query time is explicit

Vedic next candidates:

- Varga named chart bundle
- Ashtakavarga chart result and sign profile
- Jaimini chart profile
- Vedic dignity chart-backed profile
- Muhurta classification only when the request is clearly electional, not natal

## Deferred Shape

A future workspace convenience wrapper may combine both layers:

- `POST /v1/workspace/chart-profile`

That route should return:

- `western`: a Western chart-profile response
- `vedic`: a Vedic chart-profile response

It should remain a wrapper over the two layer-native endpoints, not a third
doctrine.

## Verification Rule

Every added bundle section should have a focused server test proving that the
section equals the existing underlying route response for the same request
contract. If a section cannot be compared this way, the route admission should
state why before implementation.
