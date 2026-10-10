# Compatibility Notes - Moira 6.9.9

## Upgrade Boundary

Moira 6.9.9 follows 6.9.8. It restores behaviour that 6.9.8 broke, makes each
named doctrine follow its own source by default, and adopts the standard
heliacal phase names. Many default results change. The changes below are the
ones a caller can observe.

## Restored

- `/v1/patterns/coherence`, `/v1/patterns/chart-profile` and
  `/v1/patterns/network` return results again (6.9.8 returned HTTP 500).
- `/v1/composite/chart` without `reference_latitude` returns a chart again
  (6.9.8 returned HTTP 422). The houses are cast at the mean latitude of the
  two birthplaces, reported in `computation_truth.reference_latitude`. An
  explicit `reference_latitude` is used unchanged. The retired `midpoint`
  method is still rejected.
- `/v1/manazil/position` and `/bulk` default to the `agrippa` tradition, so a
  request with only a longitude works again.

## Changed Defaults

- **Relationship aspects.** `/v1/synastry/*`, `Moira.synastry_aspects` and
  `SynastryAspectPolicy()` default to tier 0, the five major aspects
  (previously 2, every aspect). Composite and Davison embedded aspects default
  to tier 0 (previously 1). Send `tier: 1` or `tier: 2` to keep the minor
  aspects.
- **Dignities.** `william_lilly_1647` scoring (the default) uses Lilly's
  triplicity table: Mars rules the water triplicity by day and night, so
  scores change for planets in Cancer, Scorpio and Pisces. It also uses
  Lilly's own terms (p. 104), which differ from Robbins' Ptolemaic terms in
  these ranges (degrees within the sign; Robbins ruler to Lilly ruler):

  | Sign | Degrees | Term ruler |
  |---|---|---|
  | Taurus | 24-26 | Mars to Saturn |
  | Gemini | 13-14 | Venus to Jupiter |
  | Gemini | 20-21 | Mars to Venus |
  | Gemini | 21-25 | Mars to Saturn |
  | Gemini | 26-30 | Saturn to Mars |
  | Leo | 0-6 | Jupiter to Saturn |
  | Leo | 13-19 | Saturn to Venus |
  | Leo | 19-25 | Venus to Jupiter |
  | Libra | 11-16 | Mercury to Jupiter |
  | Libra | 19-24 | Jupiter to Mercury |
  | Scorpio | 6-13 | Venus to Jupiter |
  | Scorpio | 14-21 | Jupiter to Venus |
  | Capricorn | 19-25 | Saturn to Mars |
  | Capricorn | 25-30 | Mars to Saturn |
  | Pisces | 25-26 | Saturn to Mars |

  `EssentialDignityPolicy().triplicity_doctrine` and the REST term table
  default to the scoring mode's own table; pass a table explicitly to keep an
  older one. An explicit table is no longer rejected under Lilly scoring.
  `TriplicityAssignment.participating_ruler` may be `None`. The Hellenistic
  profile keeps its Ptolemaic terms, and `HellenisticProfilePolicy` rejects a
  dignity policy whose triplicity table differs from its own.
- **Perfection.** Lilly's perfection reception uses his triplicity and terms;
  the policy literals are `william_lilly_1647` and
  `william_lilly_1647_sect_active`.
- **Planetary years.** `PTOLEMAIC_YEARS` mean years for Saturn (43.5),
  Jupiter (45), Mars (40), Sun (69) and Moon (66) follow Lilly, which changes
  `calculate_longevity` granted years.
- **Nine parts and Paulus lots.** The default returns the 7 Hermetic lots
  instead of 9; `planets` must include Mercury and Venus; "North Node" is
  required only for the extension scope; `meaning` is null; REST
  `historical_scope` defaults to `hermetic_seven`. Necessity (Paulus) and Eros
  (Paulus) values change (Paulus ch. 23, reversed by night).
- **Harmonics.** Conjunction, aspect, sweep, fingerprint and cross-chart
  requests default to `orb: 12` (previously 1). `provenance.preset_description`
  is `null` in computed payloads; the cross-chart payload reports
  `harmonic_kind: "cross_chart"`.
- **Lunar mansions.** Every tradition uses 28 equal divisions. For
  `al_biruni`, `jd_ut` is no longer needed, `span_degrees` is 12.857...,
  provenance is `equal_division_360_by_28` / `equal_28_mansion_assignment`,
  and the index for a longitude can differ from 6.9.8 (Moon at 254.526 deg is
  now #20, not #18). `mansion_of(..., jd=)` accepts and ignores `jd`. Latin
  names change for Agrippa (for example #3 Athoray to Achaomazon) and
  Picatrix. Agrippa's significations and 11 natures change. The always-null
  `MansionInfoResponse.ruling_star` is removed; use `marker_stars`.
- **Gauquelin.** Positions add `effect_status`. Bodies other than the Moon,
  Venus, Mars, Jupiter and Saturn report `zone: "Not Classified"` and
  `is_plus_zone: false`.
- **Huber.** `AgePointPosition.intensity` and the REST age-point `intensity`
  are `null` unless `include_intensity=true`.
- **Lord of the orb.** `house_signification` is null.
- **Davison `corrected`** reports `longitude_mode: "shorter_arc_midpoint"`;
  its place moves for pairs straddling the antimeridian.
- **Relationship transits.** Up to 10 moving bodies are accepted.

## Changed Meanings

- **Heliacal setting** (`HeliacalEventKind.HELIACAL_SETTING`,
  `planet_heliacal_setting`, REST `kind`) is the evening last visibility. The
  event 6.9.8 returned, the last morning sighting, is `MORNING_LAST` /
  `planet_morning_last`.
- **Acronychal rising** is the evening rising near opposition. The event 6.9.8
  returned, the first evening sighting, is `EVENING_FIRST` /
  `planet_evening_first`. The Yallop lunar-crescent search takes
  `EVENING_FIRST` where it took `ACRONYCHAL_RISING`.
- **Fixed stars.** `stars.heliacal_setting_event` / `heliacal_setting` and
  `heliacal_catalog_batch("heliacal_setting", ...)` return the evening last
  visibility, typically months from the old result. The old event is
  `last_morning_visibility_event` / `last_morning_visibility` and the batch
  kind `"last_morning_visibility"`. A catalogue-wide setting batch no longer
  uses the native fast path and is slower.
- `acronychal_setting` remains a deprecated synonym of `heliacal_setting`.
  Every wire string that existed before still parses. A kind that does not
  occur for a body returns `None`.
- For Moon morning records under Yallop, the kept fields `sunset_jd_ut` and
  `moonset_jd_ut` hold sunrise and moonrise; `observation_window` says which.
- A superior planet's morning apparition that ends at opposition has no
  morning last visibility (6.9.8 returned the opposition date).

## Other Changed Results

- **Solar condition.** Combust begins at 8°30′ from the Sun (Lilly), not 8°,
  in `solar_condition_at` and `solar_condition_events_in_range`. The Moon is
  evaluated like any other body; only the Sun is excluded.
- **Visibility.** Under the default limiting-magnitude criterion,
  `observable` is `false` while the Sun is above the horizon, with
  `criterion_reason = "daylight_sun_above_horizon"`.
- **Galactic chart positions.** Without `observer_lat`/`observer_lon` the
  positions are geocentric (formerly topocentric at 0 N 0 E).
- **Draconic origin.** A draconic chart requested with an observer reports
  `origin: "topocentric"`.
- **Composite and Davison aspects** leave out the Mean Node, True Lilith and
  Mean Lilith, as synastry does.
- **Lord of the turn.** `is_well_placed` is `null` for a candidate without a
  solar-return house.
- **Almuten.** `/v1/almuten/*` default to Lilly 1647; `almuten` can be null
  (a tie or an unevaluable testimony), and provenance adds `doctrine_source`
  and `not_computed`. The default `/v1/almuten/figuris` doctrine needs
  `speeds`, `north_node_longitude` and `fixed_star_longitudes` (422 without
  them); `day_ruler`, `hour_ruler` and `prenatal_syzygy_longitude` are
  accepted only with `doctrine=moira_legacy_v1`. Tallies gain
  `accidental_points` and the response gains `reason`. `almuten_of_degree`
  and `almuten_figuris` (engine functions) keep the legacy count by default.
- **Facade almuten.** `Moira.almuten_figuris` raises instead of silently
  skipping unresolved day and hour rulers; pass `geo_latitude` /
  `geo_longitude` or explicit rulers. `strict` has no effect.
- **Hyleg.** `/v1/hyleg/lilly-1647` selects in cases it previously did not
  evaluate, and may name a planet, the Ascendant or the Part of Fortune.
- **Offices.** `/v1/hellenistic/offices` `predominator` is a string, `reason`
  can be null, and `house_master_reason` and `predominator_determination` are
  new.

## Newly Rejected Requests

- Midpoint `planet_set` values other than `classic`, `modern` and `extended`
  (engine `ValueError`; REST 422).
- Davison requests whose two people name different house systems, or that
  carry per-person `bodies`.
- `bodies` on the single-body decanate chart routes.
- Draconic `latitude` without `longitude`, or the reverse.
- Galactic chart requests with only one of `observer_lat` / `observer_lon`.
- Paran packet heliacal kinds that do not apply to stars.

## Newly Accepted Requests

- Synastry aspects and contacts with `time_unknown` on either person, and a
  one-way overlay into the chart of a person whose time is known.
- Draconic `latitude`, `longitude` and `house_system`.
- Every standard heliacal kind on `/v1/heliacal/planet`, and the star kinds
  on the paran packet.

## Recommended Migration Sequence

```text
pip install --upgrade moira-astro==6.9.9
```

For services running `moira_server`:

```text
pip install --upgrade "moira-astro[server]==6.9.9"
```

Callers that want 6.9.8's relationship aspects should send `tier` explicitly
(`2` for synastry, `1` for composite and Davison). Restart long-running engine
and API processes after upgrading so the new native extension and transport
schemas are loaded together.
