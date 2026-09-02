# Compatibility Notes - Moira 6.4.1

## Upgrade Boundary

Moira 6.4.1 is backward-compatible from 6.4.0 for every valid request
body. Response shapes are unchanged. Extra request keys still 422
(`extra=forbid`).

- `find_aspect_transits_to_longitudes()` and `Moira.natal_aspect_transits()`
  keep their signatures and their `AspectTransitEvent` vessel.
- Exact event times agree with 6.4.0 and with per-target
  `find_aspect_transits()` results to within the solver tolerance
  (`1e-6` day). Only candidate-window detection changed.
- Planetary reduction, Delta-T, the wheel catalog, Hellenistic profile
  `v2`, Track A/B, and physical visibility are unchanged.

## What a client can notice

- `POST /v1/transits/natal-aspects` now accepts `body` values it rejected
  in 6.4.0: `True Node`, `Mean Node`, `Lilith`, `True Lilith`, and named
  asteroids. The `body` field description in the OpenAPI document changed
  accordingly. Clients that validated `body` against the 6.4.0 enum-like
  description should regenerate.
- An unknown mover on either transport now returns the message
  `unsupported natal-aspect mover '<name>'; supported: planets, True Node,
  Mean Node, Lilith, True Lilith, and named asteroids` (route: 422; batch
  item: `ok: false` with that `failure.message`). 6.4.0 said
  `unsupported transit body`.
- An asteroid mover on a server without a small-body shard still 422s,
  now with the kernel-availability message rather than a `TypeError`.

## Scan step policy

`_auto_step` gained `True Node` and `True Lilith` at `0.25` day. Callers
who pass `step_days` explicitly to `find_aspect_transits_to_longitudes()`
are unaffected: an explicit step is honoured and only the quarter-turn
guard can tighten it. Callers who relied on the 6.4.0 hardcoded one-day
scan for the grid now get the engine's per-body step (Moon `0.25`,
Sun/Mercury/Venus `0.5`, Mars `1.0`, Jupiter/Saturn `5.0`, Uranus/Neptune
`10.0`, Pluto `15.0`, everything else `1.0`), which is the same policy
`find_aspect_transits()` has always used.

## Native tiers

No new native bindings. The small-body tier reuses the Type 13 evaluator
each `SmallBodyKernel` segment already holds and the `ecliptic_longitude_batch`
binding from 6.4.0. If the native module is absent, every tier steps down
to resolver sampling and results are identical.

## Recommended Migration Sequence

1. Install `moira-astro==6.4.1` in staging.
2. Replay a 6.4.0 `POST /v1/transits/natal-aspects` or batch body. Expect
   the same events at the same times.
3. If you validate `body` strictly, regenerate OpenAPI clients.
4. Promote the exact staged artifact.

No database migration is required. Restart processes that import `moira`.

## Upgrade Pin

```text
moira-astro==6.4.1
moira-astro[server]==6.4.1
```

## Rollback

Pin back to `moira-astro==6.4.0` to restore planets-only admission on the
dedicated route and per-target searches for non-planet movers. 6.4.1
request bodies that use only planets remain valid on 6.4.0.
