# Moira REST API Reference

Version: 0.1.0 transport surface
Date audited: 2026-06-12
Source of truth: `moira_server.app.create_app()` route registry

This document describes the HTTP transport surface currently registered by
`moira_server`. It is separate from `wiki/02_standards/API_REFERENCE.md`, which
documents the Python engine/import surface.

The REST layer is an access surface over the engine. It must preserve engine
truth, explicit computation policy, and request-flow read-only behavior. Route
presence here means the endpoint is registered by the live FastAPI application;
it does not imply that the corresponding engine family is complete beyond the
transport contract documented for that family.

## Current Surface Summary

- Total non-documentation routes: 263
- Operational/meta routes: 4
- Versioned `/v1` routes: 259
- OpenAPI path, when enabled by server configuration: `/openapi.json`
- Interactive docs, when enabled by server configuration: `/docs` and `/redoc`

## Present Expansion State

The REST implementation is past bootstrap.

Implemented:

- phases 1-5: operational, chart, positions, transits, returns, batch, and visibility
- phase 6: stations, void-of-course, rise/set, eclipses, occultations, heliacal events, and parans
- phase 7: synastry, composite, Davison, chart shape, patterns, and midpoints
- phase 8: progressions, profections, timelords, Vimshottari dasha, Varshaphal, and primary directions
- phase 9 opened with Panchanga direct and chart-backed instant/profile routes,
  followed by chart-backed Shadbala result/profile/network/condition routes
  direct/chart-backed Jaimini karaka/profile/condition/pair routes, and
  chart-backed Classical Dignities result/reception/condition/profile/network
  routes, followed by Classical Lots catalogue and chart-backed
  result/dependency/condition/profile/network routes, and Triplicity
  table/assignment/score routes, followed by Egyptian Bounds table, bound,
  classification, relation, condition, aggregate, and network routes, followed
  by Vedic Dignities direct and chart-backed dignity/relationship/profile routes,
  Ashtakavarga direct and chart-backed result/profile/sign-profile/
  transit-strength routes, and alternate dasha direct and chart-backed
  Ashtottari/Yogini sequence/profile plus period-profile
  routes, Varga direct and chart-backed generic/named/Shodashvarga/batch routes, and
  Decans/Decanates direct and chart-backed decanate-placement plus Hermetic
  catalog/longitude/rising/night-hour routes
- website-accelerated Phase 11 subset: fixed stars, variable stars, multiple stars, asteroids, and comets
- phase 10 opened with bounded Astrocartography line and subplanetary point
  routes, followed by bounded Local Space direct and chart-backed horizon
  position routes, and bounded Geodetic direct/chart-backed location-chart and
  equivalent-longitude routes, followed by bounded Galactic coordinate-frame
  transform, reference-point, and chart-position routes; dense maps, tiles,
  contours, grids, projection products, geographic search, relocation
  synthesis, galactic houses, and catalog sweeps remain deferred
- website support: locations, chart-wheel packets, and reduction-pipeline inspection aliases

Not yet broadly exposed as REST families:

- phase 9 umbrella aggregation modules: `/v1/vedic/*` and `/v1/classical/*`
- remaining phase 10 spatial and Earth-facing routes: `/v1/gauquelin/*`; expanded Astrocartography, Local Space, Geodetic, and Galactic map/rendering/projection products remain deferred
- phase 12 specialist analytical families: `/v1/uranian/*`, `/v1/harmonics/*`, `/v1/phase/*`, `/v1/antiscia/*`, `/v1/special/*`
- phase 13 electional/search workflow routes: `/v1/electional/*`

## Route Families

| Family | Routes |
|---|---:|
| meta | 4 |
| ashtakavarga | 8 |
| alternate-dashas | 9 |
| astrocartography | 4 |
| asteroids | 3 |
| batch | 7 |
| chart | 2 |
| chart-shape | 1 |
| comets | 3 |
| composite | 1 |
| dasha | 5 |
| davison | 1 |
| decanates | 6 |
| dignities | 6 |
| egyptian-bounds | 7 |
| eclipses | 5 |
| galactic | 6 |
| geodetic | 4 |
| heliacal | 2 |
| hermetic-decans | 4 |
| houses | 2 |
| jaimini | 8 |
| locations | 2 |
| local-space | 2 |
| lots | 7 |
| lunar-phases | 1 |
| midpoints | 5 |
| occultations | 8 |
| panchanga | 4 |
| parans | 8 |
| patterns | 3 |
| pipeline | 3 |
| positions | 4 |
| primary-directions | 8 |
| profections | 3 |
| progressions | 17 |
| returns | 3 |
| shadbala | 4 |
| rise-set | 3 |
| stars | 12 |
| stations | 4 |
| synastry | 9 |
| timelords | 16 |
| transits | 3 |
| triplicity | 3 |
| varshaphal | 9 |
| varga | 8 |
| vedic-dignities | 7 |
| visibility | 2 |
| void-of-course | 4 |
| website | 3 |

## Operational Routes

| Method | Path | Handler |
|---|---|---|
| GET | `/health` | `health` |
| GET | `/ready` | `ready` |
| GET | `/meta/version` | `version` |
| GET | `/meta/kernel` | `kernel_meta` |

## Chart And Position Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/chart` | `chart_route` |
| POST | `/v1/chart/reduction` | `chart_reduction_route` |
| POST | `/v1/houses` | `houses_route` |
| POST | `/v1/houses/reduction` | `houses_reduction_route` |
| POST | `/v1/positions/planet` | `planet_position_route` |
| POST | `/v1/positions/planet/reduction` | `planet_position_reduction_route` |
| POST | `/v1/positions/sky` | `sky_position_route` |
| POST | `/v1/positions/sky/reduction` | `sky_position_reduction_route` |
| POST | `/v1/pipeline/chart` | `pipeline_chart_route` |
| POST | `/v1/pipeline/positions/planet` | `pipeline_planet_position_route` |
| POST | `/v1/pipeline/positions/sky` | `pipeline_sky_position_route` |

## Transits, Returns, Batch, And Visibility

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/transits/search` | `transit_search_route` |
| POST | `/v1/transits/ingresses` | `ingress_search_route` |
| POST | `/v1/transits/next-ingress` | `next_ingress_route` |
| POST | `/v1/returns/solar` | `solar_return_route` |
| POST | `/v1/returns/lunar` | `lunar_return_route` |
| POST | `/v1/returns/planet` | `planet_return_route` |
| POST | `/v1/lunar-phases` | `lunar_phase_route` |
| POST | `/v1/batch/charts` | `batch_charts_route` |
| POST | `/v1/batch/charts/reduction` | `batch_charts_reduction_route` |
| POST | `/v1/batch/transits` | `batch_transits_route` |
| POST | `/v1/batch/returns` | `batch_returns_route` |
| POST | `/v1/batch/events` | `batch_events_route` |
| POST | `/v1/batch/progressions` | `batch_progressions_route` |
| POST | `/v1/batch/progressions/reduction` | `batch_progressions_reduction_route` |
| POST | `/v1/visibility/assessment` | `visibility_assessment_route` |
| POST | `/v1/visibility/tonight` | `visibility_tonight_route` |

## Phenomena Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/stations/search` | `station_search_route` |
| POST | `/v1/stations/next` | `next_station_route` |
| POST | `/v1/stations/is-retrograde` | `station_state_route` |
| POST | `/v1/stations/retrograde-periods` | `retrograde_periods_route` |
| POST | `/v1/void-of-course/window` | `void_of_course_window_route` |
| POST | `/v1/void-of-course/next` | `next_void_of_course_route` |
| POST | `/v1/void-of-course/is-active` | `void_of_course_state_route` |
| POST | `/v1/void-of-course/range` | `void_of_course_range_route` |
| POST | `/v1/rise-set/phenomena` | `rise_set_phenomena_route` |
| POST | `/v1/rise-set/transit` | `rise_set_transit_route` |
| POST | `/v1/rise-set/twilight` | `twilight_times_route` |
| POST | `/v1/eclipses/solar/next` | `next_solar_eclipse_route` |
| POST | `/v1/eclipses/lunar/next` | `next_lunar_eclipse_route` |
| POST | `/v1/eclipses/solar/local-visible` | `next_visible_solar_eclipse_route` |
| POST | `/v1/eclipses/lunar/local` | `lunar_eclipse_local_route` |
| POST | `/v1/eclipses/solar/path` | `solar_eclipse_path_route` |
| POST | `/v1/occultations/close-approaches` | `close_approaches_route` |
| POST | `/v1/occultations/lunar` | `lunar_occultations_route` |
| POST | `/v1/occultations/lunar-star` | `lunar_star_occultations_route` |
| POST | `/v1/occultations/all-lunar` | `all_lunar_occultations_route` |
| POST | `/v1/occultations/lunar-path` | `lunar_occultation_path_route` |
| POST | `/v1/occultations/lunar-path-at` | `lunar_occultation_path_at_route` |
| POST | `/v1/occultations/lunar-star-path` | `lunar_star_occultation_path_route` |
| POST | `/v1/occultations/lunar-star-path-at` | `lunar_star_occultation_path_at_route` |
| POST | `/v1/heliacal/planet` | `planet_heliacal_event_route` |
| POST | `/v1/heliacal/visibility-event` | `general_visibility_event_route` |
| POST | `/v1/parans/search` | `paran_search_route` |
| POST | `/v1/parans/natal` | `natal_paran_search_route` |
| POST | `/v1/parans/site` | `paran_site_route` |
| POST | `/v1/parans/field/samples` | `paran_field_samples_route` |
| POST | `/v1/parans/field/analysis` | `paran_field_analysis_route` |
| POST | `/v1/parans/field/contours` | `paran_field_contours_route` |
| POST | `/v1/parans/field/paths` | `paran_field_paths_route` |
| POST | `/v1/parans/field/structure` | `paran_field_structure_route` |

## Relationship And Pattern Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/synastry/aspects` | `synastry_aspects_route` |
| POST | `/v1/synastry/contacts` | `synastry_contacts_route` |
| POST | `/v1/synastry/contact-relations` | `synastry_contact_relations_route` |
| POST | `/v1/synastry/condition-profiles` | `synastry_condition_profiles_route` |
| POST | `/v1/synastry/overlay` | `synastry_directional_overlay_route` |
| POST | `/v1/synastry/overlays` | `synastry_overlays_route` |
| POST | `/v1/synastry/overlay-relations` | `synastry_overlay_relations_route` |
| POST | `/v1/synastry/chart-condition` | `synastry_chart_condition_route` |
| POST | `/v1/synastry/network` | `synastry_network_route` |
| POST | `/v1/composite/chart` | `composite_chart_route` |
| POST | `/v1/davison/chart` | `davison_chart_route` |
| POST | `/v1/chart-shape/classify` | `chart_shape_route` |
| POST | `/v1/patterns/find` | `patterns_route` |
| POST | `/v1/patterns/chart-profile` | `pattern_chart_profile_route` |
| POST | `/v1/patterns/network` | `pattern_network_route` |
| POST | `/v1/midpoints/calculate` | `midpoints_route` |
| POST | `/v1/midpoints/to-point` | `midpoints_to_point_route` |
| POST | `/v1/midpoints/pictures` | `midpoint_pictures_route` |
| POST | `/v1/midpoints/weighting` | `midpoint_weighting_route` |
| POST | `/v1/midpoints/clusters` | `midpoint_clusters_route` |

## Panchanga Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/panchanga/instant` | `panchanga_instant_route` |
| POST | `/v1/panchanga/instant/profile` | `panchanga_instant_profile_route` |
| POST | `/v1/panchanga/chart` | `panchanga_chart_route` |
| POST | `/v1/panchanga/chart/profile` | `panchanga_chart_profile_route` |

## Shadbala Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/shadbala/chart` | `shadbala_chart_route` |
| POST | `/v1/shadbala/chart/profile` | `shadbala_chart_profile_route` |
| POST | `/v1/shadbala/chart/network` | `shadbala_chart_network_route` |
| POST | `/v1/shadbala/chart/condition` | `shadbala_chart_condition_route` |

## Jaimini Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/jaimini/karakas` | `jaimini_karakas_route` |
| POST | `/v1/jaimini/karakas/profile` | `jaimini_karakas_profile_route` |
| POST | `/v1/jaimini/karakas/condition` | `jaimini_karakas_condition_route` |
| POST | `/v1/jaimini/karakas/pair` | `jaimini_karakas_pair_route` |
| POST | `/v1/jaimini/chart/karakas` | `jaimini_chart_karakas_route` |
| POST | `/v1/jaimini/chart/profile` | `jaimini_chart_profile_route` |
| POST | `/v1/jaimini/chart/condition` | `jaimini_chart_condition_route` |
| POST | `/v1/jaimini/chart/pair` | `jaimini_chart_pair_route` |

## Classical Dignities Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/dignities/chart` | `dignities_chart_route` |
| POST | `/v1/dignities/chart/receptions` | `dignities_chart_receptions_route` |
| POST | `/v1/dignities/chart/conditions` | `dignities_chart_conditions_route` |
| POST | `/v1/dignities/chart/condition` | `dignities_chart_condition_route` |
| POST | `/v1/dignities/chart/profile` | `dignities_chart_profile_route` |
| POST | `/v1/dignities/chart/network` | `dignities_chart_network_route` |

## Classical Lots Routes

| Method | Path | Handler |
|---|---|---|
| GET | `/v1/lots/catalog` | `lots_catalog_route` |
| POST | `/v1/lots/chart` | `lots_chart_route` |
| POST | `/v1/lots/chart/dependencies` | `lots_chart_dependencies_route` |
| POST | `/v1/lots/chart/conditions` | `lots_chart_conditions_route` |
| POST | `/v1/lots/chart/condition` | `lots_chart_condition_route` |
| POST | `/v1/lots/chart/profile` | `lots_chart_profile_route` |
| POST | `/v1/lots/chart/network` | `lots_chart_network_route` |

## Triplicity Routes

| Method | Path | Handler |
|---|---|---|
| GET | `/v1/triplicity/table` | `triplicity_table_route` |
| POST | `/v1/triplicity/assignment` | `triplicity_assignment_route` |
| POST | `/v1/triplicity/score` | `triplicity_score_route` |

## Egyptian Bounds Routes

| Method | Path | Handler |
|---|---|---|
| GET | `/v1/egyptian-bounds/table` | `egyptian_bounds_table_route` |
| POST | `/v1/egyptian-bounds/bound` | `egyptian_bound_route` |
| POST | `/v1/egyptian-bounds/classification` | `egyptian_bound_classification_route` |
| POST | `/v1/egyptian-bounds/relation` | `egyptian_bound_relation_route` |
| POST | `/v1/egyptian-bounds/condition` | `egyptian_bound_condition_route` |
| POST | `/v1/egyptian-bounds/aggregate` | `egyptian_bounds_aggregate_route` |
| POST | `/v1/egyptian-bounds/network` | `egyptian_bounds_network_route` |

## Vedic Dignities Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/vedic-dignities/dignity` | `vedic_dignity_route` |
| POST | `/v1/vedic-dignities/relationships` | `vedic_dignity_relationships_route` |
| POST | `/v1/vedic-dignities/condition` | `vedic_dignity_condition_route` |
| POST | `/v1/vedic-dignities/chart-profile` | `vedic_dignity_chart_profile_route` |
| POST | `/v1/vedic-dignities/chart/dignity` | `vedic_dignity_chart_backed_route` |
| POST | `/v1/vedic-dignities/chart/relationships` | `vedic_dignity_chart_backed_relationships_route` |
| POST | `/v1/vedic-dignities/chart/profile` | `vedic_dignity_chart_backed_profile_route` |

## Ashtakavarga Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/ashtakavarga/result` | `ashtakavarga_result_route` |
| POST | `/v1/ashtakavarga/profile` | `ashtakavarga_profile_route` |
| POST | `/v1/ashtakavarga/sign-profile` | `ashtakavarga_sign_profile_route` |
| POST | `/v1/ashtakavarga/transit-strength` | `ashtakavarga_transit_strength_route` |
| POST | `/v1/ashtakavarga/chart/result` | `ashtakavarga_chart_result_route` |
| POST | `/v1/ashtakavarga/chart/profile` | `ashtakavarga_chart_profile_route` |
| POST | `/v1/ashtakavarga/chart/sign-profile` | `ashtakavarga_chart_sign_profile_route` |
| POST | `/v1/ashtakavarga/chart/transit-strength` | `ashtakavarga_chart_transit_strength_route` |

## Varga Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/varga/generic` | `varga_generic_route` |
| POST | `/v1/varga/named` | `varga_named_route` |
| POST | `/v1/varga/shodashvarga` | `varga_shodashvarga_route` |
| POST | `/v1/varga/named/batch` | `varga_named_batch_route` |
| POST | `/v1/varga/shodashvarga/batch` | `varga_shodashvarga_batch_route` |
| POST | `/v1/varga/chart/named` | `varga_chart_named_route` |
| POST | `/v1/varga/chart/shodashvarga` | `varga_chart_shodashvarga_route` |
| POST | `/v1/varga/chart/shodashvarga/batch` | `varga_chart_shodashvarga_batch_route` |

## Decans And Decanates Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/decanates/chaldean-face` | `chaldean_face_route` |
| POST | `/v1/decanates/triplicity` | `triplicity_decan_route` |
| POST | `/v1/decanates/vedic-drekkana` | `vedic_drekkana_route` |
| POST | `/v1/decanates/set` | `decanate_set_route` |
| POST | `/v1/decanates/chart/vedic-drekkana` | `vedic_drekkana_chart_route` |
| POST | `/v1/decanates/chart/set` | `decanate_set_chart_route` |
| GET | `/v1/hermetic-decans/catalog` | `hermetic_decan_catalog_route` |
| POST | `/v1/hermetic-decans/longitude` | `hermetic_decan_longitude_route` |
| POST | `/v1/hermetic-decans/rising` | `hermetic_rising_decan_route` |
| POST | `/v1/hermetic-decans/night-hours` | `hermetic_decan_night_hours_route` |

## Astrocartography Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/astrocartography/lines` | `astrocartography_lines_route` |
| POST | `/v1/astrocartography/chart/lines` | `astrocartography_chart_lines_route` |
| POST | `/v1/astrocartography/subplanetary` | `astrocartography_subplanetary_route` |
| POST | `/v1/astrocartography/chart/subplanetary` | `astrocartography_chart_subplanetary_route` |

## Local Space Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/local-space/positions` | `local_space_positions_route` |
| POST | `/v1/local-space/chart/positions` | `local_space_chart_positions_route` |

## Geodetic Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/geodetic/location-chart` | `geodetic_location_chart_route` |
| POST | `/v1/geodetic/chart/location-chart` | `geodetic_chart_location_chart_route` |
| POST | `/v1/geodetic/equivalents` | `geodetic_equivalents_route` |
| POST | `/v1/geodetic/chart/equivalents` | `geodetic_chart_equivalents_route` |

## Galactic Coordinates Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/galactic/equatorial-to-galactic` | `equatorial_to_galactic_route` |
| POST | `/v1/galactic/galactic-to-equatorial` | `galactic_to_equatorial_route` |
| POST | `/v1/galactic/ecliptic-to-galactic` | `ecliptic_to_galactic_route` |
| POST | `/v1/galactic/galactic-to-ecliptic` | `galactic_to_ecliptic_route` |
| POST | `/v1/galactic/reference-points` | `galactic_reference_points_route` |
| POST | `/v1/galactic/chart/positions` | `galactic_chart_positions_route` |

## Progressions, Timelords, Dasha, Varshaphal, And Primary Directions

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/progressions/secondary` | `secondary_progression_route` |
| POST | `/v1/progressions/secondary/reduction` | `secondary_progression_reduction_route` |
| POST | `/v1/progressions/secondary-declination` | `secondary_declination_route` |
| POST | `/v1/progressions/secondary-declination/reduction` | `secondary_declination_reduction_route` |
| POST | `/v1/progressions/arc` | `arc_progression_route` |
| POST | `/v1/progressions/arc/reduction` | `arc_progression_reduction_route` |
| POST | `/v1/progressions/time-key` | `time_key_progression_route` |
| POST | `/v1/progressions/time-key/reduction` | `time_key_progression_reduction_route` |
| POST | `/v1/progressions/house-frame` | `house_frame_route` |
| POST | `/v1/progressions/house-frame/reduction` | `house_frame_reduction_route` |
| POST | `/v1/progressions/house-frame/cusps` | `daily_houses_route` |
| POST | `/v1/progressions/house-frame/arc` | `house_frame_arc_route` |
| POST | `/v1/progressions/house-frame/arc/reduction` | `house_frame_arc_reduction_route` |
| POST | `/v1/progressions/profile` | `progression_profile_route` |
| POST | `/v1/progressions/profile/reduction` | `progression_profile_reduction_route` |
| POST | `/v1/progressions/network` | `progression_network_route` |
| POST | `/v1/progressions/network/reduction` | `progression_network_reduction_route` |
| POST | `/v1/profections/annual` | `annual_profection_route` |
| POST | `/v1/profections/monthly` | `monthly_profection_route` |
| POST | `/v1/profections/schedule` | `profection_schedule_route` |
| POST | `/v1/timelords/firdaria/sequence` | `firdaria_sequence_route` |
| POST | `/v1/timelords/firdaria/groups` | `firdaria_groups_route` |
| POST | `/v1/timelords/firdaria/current` | `firdaria_current_route` |
| POST | `/v1/timelords/firdaria/profile` | `firdaria_profile_route` |
| POST | `/v1/timelords/firdaria/active-pair` | `firdaria_active_pair_route` |
| POST | `/v1/timelords/decennials/sequence` | `decennials_sequence_route` |
| POST | `/v1/timelords/decennials/groups` | `decennials_groups_route` |
| POST | `/v1/timelords/decennials/current` | `decennials_current_route` |
| POST | `/v1/timelords/decennials/profile` | `decennials_profile_route` |
| POST | `/v1/timelords/decennials/active-pair` | `decennials_active_pair_route` |
| POST | `/v1/timelords/decennials/active-path` | `decennials_active_path_route` |
| POST | `/v1/timelords/zodiacal-releasing/sequence` | `zr_sequence_route` |
| POST | `/v1/timelords/zodiacal-releasing/groups` | `zr_groups_route` |
| POST | `/v1/timelords/zodiacal-releasing/current` | `zr_current_route` |
| POST | `/v1/timelords/zodiacal-releasing/profile` | `zr_profile_route` |
| POST | `/v1/timelords/zodiacal-releasing/level-pair` | `zr_level_pair_route` |
| POST | `/v1/dasha/vimshottari/sequence` | `dasha_sequence_route` |
| POST | `/v1/dasha/vimshottari/balance` | `dasha_balance_route` |
| POST | `/v1/dasha/vimshottari/current` | `dasha_current_route` |
| POST | `/v1/dasha/vimshottari/profile` | `dasha_profile_route` |
| POST | `/v1/dasha/vimshottari/lord-pair` | `dasha_lord_pair_route` |
| POST | `/v1/dasha/alternate/ashtottari/sequence` | `ashtottari_sequence_route` |
| POST | `/v1/dasha/alternate/ashtottari/profile` | `ashtottari_profile_route` |
| POST | `/v1/dasha/alternate/ashtottari/chart/sequence` | `ashtottari_chart_sequence_route` |
| POST | `/v1/dasha/alternate/ashtottari/chart/profile` | `ashtottari_chart_profile_route` |
| POST | `/v1/dasha/alternate/yogini/sequence` | `yogini_sequence_route` |
| POST | `/v1/dasha/alternate/yogini/profile` | `yogini_profile_route` |
| POST | `/v1/dasha/alternate/yogini/chart/sequence` | `yogini_chart_sequence_route` |
| POST | `/v1/dasha/alternate/yogini/chart/profile` | `yogini_chart_profile_route` |
| POST | `/v1/dasha/alternate/period-profile` | `alternate_period_profile_route` |
| POST | `/v1/varshaphal/chart` | `varshaphal_chart_route` |
| POST | `/v1/varshaphal/judgement/profile` | `varshaphal_judgement_profile_route` |
| POST | `/v1/varshaphal/judgement/year` | `varshaphal_year_judgement_route` |
| POST | `/v1/varshaphal/summary` | `varshaphal_year_summary_route` |
| POST | `/v1/varshaphal/topics` | `varshaphal_topics_route` |
| POST | `/v1/varshaphal/topics/windows` | `varshaphal_topic_windows_route` |
| POST | `/v1/varshaphal/mudda/active` | `varshaphal_mudda_active_route` |
| POST | `/v1/varshaphal/mudda/judgement` | `varshaphal_mudda_judgement_route` |
| POST | `/v1/varshaphal/tasira/active` | `varshaphal_tasira_active_route` |
| POST | `/v1/primary-directions/speculum` | `primary_directions_speculum_route` |
| POST | `/v1/primary-directions/arcs` | `primary_directions_arcs_route` |
| POST | `/v1/primary-directions/arcs/reduction` | `primary_directions_arcs_reduction_route` |
| POST | `/v1/primary-directions/relations` | `primary_directions_relations_route` |
| POST | `/v1/primary-directions/profile` | `primary_directions_profile_route` |
| POST | `/v1/primary-directions/profile/reduction` | `primary_directions_profile_reduction_route` |
| POST | `/v1/primary-directions/network` | `primary_directions_network_route` |
| POST | `/v1/primary-directions/network/reduction` | `primary_directions_network_reduction_route` |

## Catalog, Star, Small-Body, And Website Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/stars/position` | `star_position` |
| POST | `/v1/stars/bulk` | `stars_bulk` |
| GET | `/v1/stars/list` | `list_stars` |
| GET | `/v1/stars/variable/list` | `list_variable_stars_route` |
| GET | `/v1/stars/variable/{name}` | `variable_star_catalog_route` |
| POST | `/v1/stars/variable/state` | `variable_star_state_route` |
| POST | `/v1/stars/variable/range` | `variable_star_range_route` |
| POST | `/v1/stars/variable/catalog-profile` | `variable_star_catalog_profile_route` |
| POST | `/v1/stars/variable/pair` | `variable_star_pair_route` |
| GET | `/v1/stars/multiple/list` | `list_multiple_stars_route` |
| GET | `/v1/stars/multiple/{name}` | `multiple_star_catalog_route` |
| POST | `/v1/stars/multiple/state` | `multiple_star_state_route` |
| POST | `/v1/asteroids/position` | `asteroid_position` |
| POST | `/v1/asteroids/bulk` | `asteroids_bulk` |
| GET | `/v1/asteroids/list` | `list_asteroids` |
| POST | `/v1/comets/position` | `comet_position` |
| POST | `/v1/comets/bulk` | `comets_bulk` |
| GET | `/v1/comets/list` | `list_comets` |
| GET | `/v1/locations/search` | `location_search_route` |
| POST | `/v1/locations/timezone/validate` | `timezone_validate_route` |
| GET | `/v1/website/chart-wheel/presets` | `chart_wheel_presets_route` |
| POST | `/v1/website/chart-wheel/validate` | `chart_wheel_validate_route` |
| POST | `/v1/website/chart-wheel/packet` | `chart_wheel_packet_route` |

## Documentation Boundary

Use this document for HTTP route presence and family status.

Use `wiki/02_standards/API_REFERENCE.md` for Python import surfaces, engine
classes, engine functions, and canonical result vessels.

Use `docs/architecture/MOIRA_SERVER_BOUNDARY.md` for the governing rule that the
server transports truth and the engine computes truth.

Use `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md` before adding
or widening a route family.
