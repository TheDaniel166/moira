# Natal Aspect Grid: One Series Per Mover — Design Spec

**Date:** 2026-09-02
**Repo:** moira (engine), `main` after 6.4.0
**Status:** Approved — implement
**Release:** 6.4.1 (no public shape changes; performance and admission widening)

## Problem

`find_aspect_transits_to_longitudes()` scans one native longitude series
per mover and refines every `(longitude, angle)` pair from it, but only
for the ten planets. Every other mover the transit resolver admits
(True Node, Mean Node, Lilith, True Lilith, named asteroids) falls back
to one full-window `find_aspect_transits()` search per pair. Measured on
the production box for one year, 12 natal points, 5 aspects:

| Mover | Seconds |
|---|---|
| Saturn | 0.19 |
| Sun | 0.86 |
| True Node | 13.05 |
| Moon | 23.65 |

The True Node alone is about 90 % of a default Urania Time Map compute.
Asteroids and Liliths pay the same 60-search cost the moment a user
selects one. The grid search also hardcodes a one-day scan step, ignoring
the engine's per-body step policy (`_auto_step`), which says the Moon
needs a quarter day.

## Governing object

The computational object is unchanged: aspect hits of one moving body
against frozen ecliptic longitudes, with exact times from the existing
bisection on the apparent resolver. This spec changes only how candidate
windows are found. Event times, vessel shape, and ordering are identical
to per-target searches.

## Design

### 1. Series provider

A private function in `moira/transits_aspects.py`:

```
_longitude_series(body, jd_start, jd_end, step_days, reader) -> LongitudeSeries | None
```

`LongitudeSeries` is a small frozen dataclass: `jd_start`, `step_days`,
`values` (tuple of floats, degrees 0–360). It returns `None` only when the
body cannot be positioned at all; every tier failure steps down, never
fails the search.

Tiers, tried in order:

1. **Native planetary route** — the existing `_native_ecliptic_longitude_series`
   path (planet route + Earth route, `ecliptic_longitude_batch`).
2. **Native small-body route** — for names in `ASTEROID_NAIF`: locate the
   Type 13 segment covering the window through the reader's small-body
   pool, take its native evaluator (`_Type13Segment._load_native_evaluator`),
   and if the segment center is the Sun (10) rather than the SSB (0), sum
   it with the planetary SSB→Sun evaluator via `SumEvaluator`. Evaluate
   against the Earth evaluator with `ecliptic_longitude_batch`. If the
   window spans more than one segment, or any piece is unavailable, step
   down.
3. **Resolver sampling** — every other admitted mover (nodes, Liliths,
   anything `_resolve_longitude` admits now or later): sample
   `_resolve_longitude(body, jd, reader)` at each step in Python.

Search code above the provider does not know which tier produced the
series. Adding a body type is a provider concern, never a search concern.

The native series is geometric (no light time, no aberration). It picks
windows only. Light time on a main-belt asteroid is tens of minutes,
far inside any window, and refinement uses the apparent resolver.

### 2. Step policy and guard

- The scan step is `policy.transit.step_days_override or _auto_step(body)`.
  The hardcoded `scan_step = 1.0` goes.
- `_auto_step` gains entries for `True Node` and `True Lilith`
  (0.25 day). Both are osculating points that can move several degrees a
  day near their swings. Mean Node and Mean Lilith keep the 1.0 default.
- **Quarter-turn guard.** After sampling, if any consecutive pair of
  values differs by more than 90° (circular), halve the step and resample,
  up to four halvings. This is generic: a fast near-Earth asteroid or a
  True Lilith swing is caught without per-body knowledge. If the guard
  still trips after four halvings, return `None` and let the caller fall
  back to per-target searches (correctness over speed).

### 3. Window detection and refinement

`_windows_from_longitude_series` is reused unchanged for each
`(longitude, angle)` pair. Each window is refined by `_process_aspect_hit`
exactly as today. `find_aspect_transits_to_longitudes` keeps its
signature and its per-target fallback when the provider returns `None`.

### 4. One admitted mover set

`moira_server/services/transits.py::compute_natal_aspect_transits`
currently admits `Body.ALL_PLANETS` only while the batch kind admits
anything the resolver does. Both admit the same set: the planets, the
four lunar points, and `ASTEROID_NAIF` names. The check is a shared
helper so the two transports cannot drift again. The REST field
description for `body` is updated to match.

## Not in scope

- A native (C++) node or Lilith series. The provider boundary admits one
  later without touching the search.
- Sharing one series across batch items for the same mover.
- Any change to `find_aspect_transits()` single-target behaviour.
- Workspace UI changes (default movers stay a product decision).

## Testing

Per the Testing Liturgy: Summon, Witness, Covenant.

- **Dual-path equivalence (Covenant):** for Saturn, True Node, True
  Lilith, and one packaged asteroid (a `sb441_type13` shard that ships in
  the wheel), `find_aspect_transits_to_longitudes` equals the union of
  per-target `find_aspect_transits` results: same count, `jd_exact`
  within `1e-6` day, same `is_retrograde_hit`. One year window, six
  natal longitudes, five aspects, orbs as the Time Map default.
- **Tier isolation:** monkeypatch each native tier off in turn and assert
  identical events from the next tier down; assert the tier actually used
  via a test-only hook (the provider records `tier` on the series).
- **Step guard:** a synthetic mover (monkeypatched resolver) that jumps
  100° between daily samples triggers halving; one that jumps 100° at any
  step returns `None` and the search still returns the per-target result.
- **Timing covenant:** True Node grid over one year completes in under
  2 s on the CI baseline (generous; measured expectation is well under 1 s).
- **Transport parity:** the dedicated route and the batch kind both accept
  `True Node`, `True Lilith`, and an asteroid name; both 422 an unknown
  body with the same message.
- Existing goldens and snapshots are read-only and untouched.

## Files

- `moira/transits_aspects.py` — provider, guard, step, dataclass.
- `moira/transits.py` — `_auto_step` entries.
- `moira_server/services/transits.py`, `moira_server/models/transits.py` —
  shared admitted-mover helper and field description.
- `tests/unit/test_transits_aspects_native_numeric.py` — extended.
- `tests/server/test_server_natal_aspect_routes.py` — transport parity.
- `CHANGELOG.md` Unreleased; release/compat notes for 6.4.1 at cut time.
