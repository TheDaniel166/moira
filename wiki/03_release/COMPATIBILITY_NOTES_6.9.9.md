# Compatibility Notes - Moira 6.9.9

## Upgrade Boundary

Moira 6.9.9 follows 6.9.8. It restores behaviour that 6.9.8 broke and makes a
small number of results honest where they were confidently wrong. The changes
below are the ones a caller can observe.

## Restored

- `/v1/patterns/coherence`, `/v1/patterns/chart-profile` and
  `/v1/patterns/network` return results again (6.9.8 returned HTTP 500).
- `/v1/composite/chart` without `reference_latitude` returns a chart again
  (6.9.8 returned HTTP 422). The houses are cast at the mean latitude of the
  two birthplaces, reported in `computation_truth.reference_latitude`. An
  explicit `reference_latitude` is used unchanged. The retired `midpoint`
  method is still rejected.
- `/v1/manazil/position` and `/bulk` default to the `agrippa` tradition, so a
  request with only a longitude works again. The star-based `al_biruni`
  tradition must be requested explicitly and needs `jd_ut`.

## Changed Results

- **Solar condition.** Combust begins at 8°30′ from the Sun (Lilly), not 8°,
  in `solar_condition_at` and `solar_condition_events_in_range`, matching the
  dignity scoring. The Moon is evaluated like any other body; only the Sun is
  excluded.
- **Heliacal setting.** For Mars, Jupiter and Saturn the planet heliacal
  setting returns `None` where it used to return the opposition date.
- **Visibility.** Under the default limiting-magnitude criterion,
  `observable` is `false` while the Sun is above the horizon, with
  `criterion_reason = "daylight_sun_above_horizon"`.
- **Galactic chart positions.** Without `observer_lat`/`observer_lon` the
  positions are geocentric (formerly topocentric at 0 N 0 E). Give both
  observer fields for topocentric positions; giving only one is a 422.
- **Draconic origin.** A draconic chart requested with an observer reports
  `origin: "topocentric"` (formerly mislabelled `geocentric`).
- **Composite and Davison aspects** leave out the Mean Node, True Lilith and
  Mean Lilith, as synastry does.
- **Lord of the turn.** `is_well_placed` is `null` for a candidate without a
  solar-return house.
- **Mansion provenance** names each tradition's own basis and authority; the
  `al_biruni` catalog reports `span_degrees: null`.

## Newly Rejected Requests

- Midpoint `planet_set` values other than `classic`, `modern` and `extended`
  (engine `ValueError`; REST 422).
- Davison requests whose two people name different house systems, or that
  carry per-person `bodies`.
- `bodies` on the single-body decanate chart routes.
- Draconic `latitude` without `longitude`, or the reverse.

## Newly Accepted Requests

- Synastry aspects and contacts with `time_unknown` on either person, and a
  one-way overlay into the chart of a person whose time is known.
- Draconic `latitude`, `longitude` and `house_system`, which add the rotated
  natal cusps and angles and a `house_system` field to the response.

## Recommended Migration Sequence

```text
pip install --upgrade moira-astro==6.9.9
```

For services running `moira_server`:

```text
pip install --upgrade "moira-astro[server]==6.9.9"
```

Restart long-running engine and API processes after upgrading so the new
native extension and transport schemas are loaded together.
