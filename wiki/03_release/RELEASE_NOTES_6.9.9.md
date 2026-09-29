# Moira 6.9.9 - Relationship and Visibility Corrections

Release date: 2026-09-29. Upgrade path: 6.9.8 to 6.9.9.

Moira 6.9.9 repairs defects found by running consumer tools against 6.9.8:
three pattern routes that failed on every call, a composite default that
rejected every existing caller, and several routes that returned a confident
answer where the engine had not actually judged anything. It also brings the
solar-condition surface into agreement with the dignity scoring.

## Key Changes

### Routes That Failed

- `/v1/patterns/coherence`, `/v1/patterns/chart-profile` and
  `/v1/patterns/network` work again (HTTP 500 in 6.9.8).
- A composite request without `reference_latitude` works again: the houses
  are cast at the mean latitude of the two birthplaces.
- Lunar-mansion requests with only a longitude work again (default tradition
  `agrippa`).
- Release Hardening now rejects undefined names, the class of error behind
  the pattern-route failures.

### Honest Answers

- Superior planets have no heliacal setting at opposition; the search no
  longer returns the opposition date.
- The dark-sky limiting-magnitude criterion is not applied in daylight.
- Galactic chart positions default to geocentric.
- A draconic chart computed with an observer says it is topocentric.
- Lord of the turn reports placement as not judged when no house is given.
- Davison, decanate and midpoint requests reject settings they would have
  ignored.

### Relationship Charts and Unknown Birth Times

- Synastry aspects and contacts, and one-way house overlays into a known
  chart, work when a birth time is unknown; routes that need the unknown
  person's houses say so by name.
- Composite and Davison aspects use one node and one Lilith, as synastry does.

### Solar Condition and Draconic Houses

- `solar_condition_at` follows the dignity scoring: combust within 8°30′
  (Lilly), the Moon evaluated like every other body, only the Sun excluded.
- The draconic route can return the natal cusps and angles rotated by the
  node, with the house system used.

## Compatibility Highlights

- Combust now begins at 8°30′ from the Sun in `solar_condition_at` and its
  event search (formerly 8°), and the Moon can be cazimi, combust or under
  the beams.
- Unknown midpoint `planet_set` values raise `ValueError` (REST: 422)
  instead of silently using `classic`.
- `LordOfTheTurnCandidateResponse.is_well_placed` may be `null`.
- Draconic responses gain `house_system`; draconic requests accept
  `latitude`, `longitude` and `house_system`.

## Install

```text
pip install --upgrade moira-astro==6.9.9
```

For the optional REST service:

```text
pip install --upgrade "moira-astro[server]==6.9.9"
```
