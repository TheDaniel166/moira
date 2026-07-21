# Moira REST API Reference

Version: 0.1.0 transport surface
Date audited: 2026-07-21
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

- Total non-documentation routes: 432
- Operational/meta routes: 4
- Versioned `/v1` routes: 428
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
  routes, Church of Light natal Astrodynes doctrine/geometry/chart routes,
  followed by Classical Lots catalogue and chart-backed
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
- source-scoped Pancha Pakshi admission adds explicit-profile discovery,
  governance-only Uromarisi constitutional status, aksara and natal identity,
  a pure nakshatra-to-bird source-table lookup, exact nominal schedule,
  directed relationship, pure Padu and first-samam EAT-seed lookups, and
  bounded astronomical-paksha
  inference, local-solar
  context, fixed-clock
  materialization, and fixed-clock current-cell routes, plus separate
  solar-proportional materialization and current-cell routes; it selects no
  default, the inference route accepts neither location nor paksha, and all five
  schedule-related astronomical routes continue to require caller-supplied
  paksha
- Phase 11 admitted surfaces: fixed stars, variable stars, multiple stars,
  asteroids, comets, asteroid subsets/families, Manazil, and planetary/
  small-body nodes
- phase 10 opened with bounded Astrocartography line and subplanetary point
  routes, followed by bounded Local Space direct and chart-backed horizon
  position routes, and bounded Geodetic direct/chart-backed location-chart and
  equivalent-longitude routes, followed by bounded Galactic coordinate-frame
  transform, reference-point, and chart-position routes, followed by bounded
  Galactic Houses cusp, direct-placement, and chart-backed placement routes,
  and canonical Gauquelin direct/chart-backed sector routes; dense maps,
  tiles, contours, grids, projection products, geographic search, relocation
  synthesis, rendered galactic house charts, rendered Gauquelin wheels,
  statistical workflows, and catalog sweeps remain deferred
- website support: locations, chart-wheel packets, and reduction-pipeline inspection aliases
- phase 12 opened with bounded Uranian/Hamburg School hypothetical-body
  catalog, single-position, and bulk-position routes, followed by bounded
  Harmonics preset, direct chart, age-harmonic chart, conjunction,
  pattern-score, aspect, sweep, fingerprint, composite, and sampled
  mixed-origin transit-forecast routes over caller-supplied longitudes,
  followed by bounded Phase/Photometry illuminated
  fraction, synodic, elongation, phase-angle, angular-diameter, and
  apparent-magnitude routes, followed by bounded ordinary Antiscia direct
  reflection, pair contact, and fixed-point contact routes, followed by a
  bounded Abu Ma'shar Nine Parts aggregate route, followed by bounded
  sunrise-based Planetary Hours schedule and hour-at routes, followed by
  direct-cusp Huber dynamic intensity, house-zone, Age Point,
  intensity-at-longitude, chart intensity profile, and bounded Age Point
  contact routes, followed by caller-seeded Lord of the Orb sequence and
  current-period routes, and a caller-supplied Solar Return Lord of the Turn
  profile route
- phase 13 opened with a bounded electional predicate-profile catalogue and
  electional window, raw moment, scorer-profile catalogue, and bounded scored
  window routes over server-defined predicate and numeric scorer profiles
- post-phase gap closure P-GAP-01 admits frame-specific position products:
  heliocentric, planetocentric, Solar System Barycenter, and received-light
  position routes under `/v1/positions/frame/*`
- post-phase gap closure P-GAP-02 admits bounded Vedic Muhurta moment
  classification and raw-score routes over direct and chart-backed Panchanga
  truth under `/v1/muhurta/*`
- post-phase gap closure P-GAP-03 admits heliocentric J2000 osculating
  orbital elements and heliocentric distance-extrema routes under
  `/v1/orbits/*`
- post-phase gap closure P-GAP-04 admits bounded generic phenomena and
  solar-condition routes under `/v1/phenomena/*` and
  `/v1/solar-condition/*`
- post-phase gap closure P-GAP-05 admits mechanical sidereal and Nakshatra
  utility routes under `/v1/sidereal/*` and `/v1/nakshatra/*`
- post-phase gap closure P-GAP-06 admits bounded harmogram vector,
  Zero-Aries vector, intensity-spectrum, projection, and explicit-sample
  trace routes under `/v1/harmograms/*`
- profile-bundle admission admits composition-only Western and Vedic
  convenience endpoints under `/v1/western/chart-profile` and
  `/v1/vedic/chart-profile`; these bundle existing route-equivalent strata
  for frontend/workspace callers without adding interpretive synthesis

Not yet broadly exposed as REST families:

- broad phase 9 umbrella aggregation modules: wider `/v1/vedic/*` and
  `/v1/classical/*` families remain deferred beyond admitted
  `/v1/vedic/chart-profile`
- expanded phase 10 spatial and Earth-facing products: Astrocartography, Local Space, Geodetic, Galactic, Galactic Houses, and Gauquelin map/rendering/projection/statistical products remain deferred
- remaining phase 12 specialist analytical families: `/v1/sothic/*` is
  deliberately deferred for specialist review and public heliacal-search
  failure semantics; `/v1/longevity/*` is deliberately deferred for doctrine,
  validation, and public-language safeguards; `/v1/special/*` also remains
  unexposed
- remaining phase 13 electional/search workflow surfaces: arbitrary predicate
  routes, arbitrary scorer routes, generic Western profile search/scoring,
  additional lineage profiles, and advice/recommendation language. The bounded
  Ramesey v1 single-moment evaluation is admitted separately.
- generic Phase 11 catalog umbrella routes: `/v1/catalogs/*` remain
  intentionally absent; P11-U1 permits only a future discovery-only registry
  design, not cross-family search, member lookup, computation, or catalog
  sweeps

## Route Families

| Family | Routes |
|---|---:|
| meta | 5 |
| ashtakavarga | 8 |
| alternate-dashas | 9 |
| antiscia | 3 |
| astrocartography | 6 |
| astrodynes | 15 |
| asteroids | 9 |
| batch | 7 |
| chart | 2 |
| chart-shape | 1 |
| comets | 3 |
| aspects | 2 |
| composite | 1 |
| dasha | 5 |
| davison | 1 |
| decanates | 6 |
| dignities | 6 |
| draconic | 3 |
| egyptian-bounds | 7 |
| electional | 12 |
| eclipses | 6 |
| galactic | 6 |
| galactic-houses | 3 |
| gauquelin | 3 |
| geodetic | 4 |
| heliacal | 2 |
| harmograms | 5 |
| harmonics | 10 |
| hermetic-decans | 4 |
| houses | 2 |
| huber | 6 |
| jaimini | 8 |
| locations | 2 |
| local-space | 2 |
| lord-of-the-orb | 2 |
| lord-of-the-turn | 1 |
| lots | 7 |
| lunar-phases | 1 |
| manazil | 4 |
| midpoints | 5 |
| muhurta | 4 |
| nakshatra | 2 |
| nodes | 4 |
| nine-parts | 1 |
| occultations | 12 |
| orbits | 2 |
| pancha-pakshi | 19 |
| panchanga | 4 |
| parans | 8 |
| patterns | 3 |
| phase | 6 |
| phenomena | 3 |
| planetary-hours | 2 |
| pipeline | 3 |
| positions | 4 |
| positions-frame | 4 |
| primary-directions | 8 |
| profections | 3 |
| progressions | 17 |
| returns | 3 |
| shadbala | 4 |
| rise-set | 3 |
| sidereal | 3 |
| solar-condition | 2 |
| stars | 12 |
| stations | 4 |
| synastry | 9 |
| timelords | 16 |
| transits | 3 |
| triplicity | 3 |
| uranian | 3 |
| varshaphal | 9 |
| varga | 8 |
| vedic-dignities | 7 |
| vedic-profile | 1 |
| visibility | 2 |
| void-of-course | 4 |
| website | 3 |
| western-profile | 1 |

## Operational Routes

| Method | Path | Handler |
|---|---|---|
| GET | `/health` | `health` |
| GET | `/ready` | `ready` |
| GET | `/meta/version` | `version` |
| GET | `/meta/kernel` | `kernel_meta` |
| GET | `/v1/meta/routes` | `route_catalog` |

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
| POST | `/v1/positions/frame/heliocentric` | `frame_heliocentric_route` |
| POST | `/v1/positions/frame/planetocentric` | `frame_planetocentric_route` |
| POST | `/v1/positions/frame/ssb` | `frame_ssb_route` |
| POST | `/v1/positions/frame/received-light` | `frame_received_light_route` |
| POST | `/v1/pipeline/chart` | `pipeline_chart_route` |
| POST | `/v1/pipeline/positions/planet` | `pipeline_planet_position_route` |
| POST | `/v1/pipeline/positions/sky` | `pipeline_sky_position_route` |

## Profile Bundle Routes

These routes are convenience composition surfaces. They preserve the underlying
route-equivalent sections as named response fields instead of returning a
single interpretive synthesis.

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/western/chart-profile` | `western_chart_profile_route` |
| POST | `/v1/vedic/chart-profile` | `vedic_chart_profile_route` |

### Website Planet Pipeline Reduction Contract

`POST /v1/pipeline/positions/planet` is an alias over the planetary reduction
surface with an added physical reduction breakdown for website inspection. The
request is the ordinary `PlanetPositionRequest`: `dt`, `body`, optional
`observer_lat`, `observer_lon`, `observer_elev_m`, and the correction flags
`apparent`, `aberration`, `grav_deflection`, and `nutation`.

The response preserves `result` and the existing `reduction.stage_sequence`.
For ordinary planets and admitted asteroids, `reduction` also includes:

- `stages`: ordered stage records `{num, name, note, delta, enabled, ref_pos?}`
- `total_delta_arcsec`: enabled stage deltas summed in arcseconds
- `stage_longitudes`: compatibility map for HTTP clients that compute deltas
  from intermediate longitudes
- `geocentric_longitude`: pre-topocentric ecliptic longitude

The canonical physical stage order is:

- `0` Geometric geocentric
- `1` Light-time iteration
- `2` Gravitational deflection
- `3` Annual aberration
- `4` IAU 2006 frame bias
- `5` IAU 2006 precession
- `6` IAU 2000A nutation
- `7` Topocentric parallax

Stages 0-4 are projected in the fixed J2000 ecliptic. Stage 5 is projected in
the mean equator/ecliptic of date. Stages 6-7 are projected in the true
equator/ecliptic of date, and the nutation stage reports `delta` as nutation
in longitude (`dpsi`) rather than as a re-projected longitude residual.

Comets remain outside this planetary breakdown contract because their admitted
small-body path is heliocentric-kernel routed and needs a separate reduction
contract before Moira can expose comparable stage truth.

### Frame-Specific Positions REST Admission Boundary

The admitted P-GAP-01 frame-specific position surface is the bounded
`/v1/positions/frame/*` route family. It exposes heliocentric, planetocentric,
Solar System Barycenter, and received-light products that were already public
through the Python `Moira` facade.

These routes are transport adapters over existing engine computations. They do
not build charts, mutate kernel paths, perform searches, generate dense
ephemeris tables, or reinterpret the ordinary geocentric/topocentric
`/v1/positions/*` routes.

All four responses preserve request echo, time reduction, center/frame truth,
body bounds, validation truth, and provenance. Received-light responses also
preserve the apparent position, same-time geometric comparison, emission Julian
day, and one-way light-travel duration.

Admitted products:

- `/v1/positions/frame/heliocentric`: Sun-centered true-of-date ecliptic
  positions for admitted planets except Sun and Moon
- `/v1/positions/frame/planetocentric`: true-of-date ecliptic positions from a
  named observer body center, with observer-target identity rejected
- `/v1/positions/frame/ssb`: geometric Solar System Barycenter positions,
  including the Sun where requested
- `/v1/positions/frame/received-light`: Earth received-light positions for
  admitted physical planets, with nonphysical points rejected

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
| POST | `/v1/eclipses/solar/footprint` | `solar_eclipse_footprint_route` |
| POST | `/v1/occultations/close-approaches` | `close_approaches_route` |
| POST | `/v1/occultations/lunar` | `lunar_occultations_route` |
| POST | `/v1/occultations/lunar-star` | `lunar_star_occultations_route` |
| POST | `/v1/occultations/all-lunar` | `all_lunar_occultations_route` |
| POST | `/v1/occultations/lunar-path` | `lunar_occultation_path_route` |
| POST | `/v1/occultations/lunar-path-at` | `lunar_occultation_path_at_route` |
| POST | `/v1/occultations/lunar-star-path` | `lunar_star_occultation_path_route` |
| POST | `/v1/occultations/lunar-star-path-at` | `lunar_star_occultation_path_at_route` |
| POST | `/v1/occultations/lunar-path-topology` | `lunar_occultation_path_topology_route` |
| POST | `/v1/occultations/lunar-path-topology-at` | `lunar_occultation_path_topology_at_route` |
| POST | `/v1/occultations/lunar-star-path-topology` | `lunar_star_occultation_path_topology_route` |
| POST | `/v1/occultations/lunar-star-path-topology-at` | `lunar_star_occultation_path_topology_at_route` |
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

### Polar-Safe Occultation Path Topology Contract

The four `*-path-topology` routes are additive detailed surfaces. The existing
`lunar-path`, `lunar-path-at`, `lunar-star-path`, and
`lunar-star-path-at` request and response schemas remain unchanged.

Detailed topology requests default to `sample_count=65` and admit integer
counts from 9 through 721. Their response preserves the legacy
`OccultationPathGeometry` shape under `summary`, then exposes one shared UT1
epoch lattice through `centers` and the ordered `left` and `right` boundary
tracks. Left and right are intrinsic sides relative to increasing UT1 along
the center track; they are not aliases for geographic north and south. The two
greatest cross-track distances sum to `summary.path_width_km`.
`summary.duration_at_greatest_s` is the fixed-observer occultation duration at
the reported greatest latitude and longitude; it is not the longer lifetime
of the moving global footprint.
All UT-labeled Julian-day fields remain UT1; companion UTC datetime strings
are produced by the explicit UT1-to-UTC result conversion.

Range requests treat `step_days` as a maximum coarse-cell width and admit
`0 < step_days <= 0.25`, a span no greater than 400 days, and at most 4096
coarse cells. These are explicit bounded search-policy limits. The engine
constructs exact start/end cells before evaluating the parallax-aware
candidate envelope, refines the first and last cells as well as interior
maxima, and solves pole contacts on a fixed internal lattice independent of
the requested presentation `sample_count`. Returned events have an
unconstrained greatest instant inside `(jd_start, jd_end)` by more than the
solver time tolerance `max(4e-8 d, 8 binary64 ULP)`; at modern Julian Days its
minimum term is about `3.456 ms`. An optimum at, or numerically
indistinguishable from, either global request boundary is only a constrained
range result and is not emitted as a solved event greatest. Multiple optimizer
witnesses are one
event only when their open exact-positive temporal supports overlap beyond
solver uncertainty; a zero-clearance touch alone does not join them. A
connected component need not be unimodal: its greatest is selected from a
private at-most-30-minute support lattice, independently refined lattice-local
maxima, edge cells, and original candidate witnesses under a 128-cell
fail-closed budget. The final greatest must satisfy that same solver-time
boundary rule.

Exact geographic-pole contacts are reported separately in `pole_crossings` as
`north` or `south` and `ingress` or `egress`. Exact poles use canonical
longitude zero; ordinary track points retain their spherical longitude across
polar passage. A crossing's `boundary_side` may be null when no single
left/right branch can be assigned honestly.

The detailed product declares `observer_geometry="WGS84_GEODETIC"`,
`width_metric="SPHERICAL_GREAT_CIRCLE_R6378_137_KM"`, `time_scale="UT1"`,
`atmospheric_refraction=false`, and `saturn_rings_included=false`. Lunar-limb
and target-radius doctrine remain visible through `lunar_limb_model` and
`target_model`. `observer_elevation_m` records the exact requested
`observer_elev_m` used to solve the boundary, so a nonzero-elevation width is
not mislabeled as sea-level geometry. Requests require
`observer_elev_m >= -6378.137 * (1 - 1/298.257223563) * 1000`, approximately
`-6356752.314 m`. This negative WGS 84 semi-minor-axis floor is a computational
condition for the parallax envelope, not an endorsement of such a location as
an observational site. Positive heights have no arbitrary cap; once the
observer radius reaches a body's geocentric distance, candidate admission uses
a conservative `180 degree` parallax bound rather than the exterior-observer
`asin(R/d)` formula. `lunar_limb_model` is fixed to
`"SPHERICAL_MEAN_LIMB"`: arbitrary limb-profile providers can create
multi-contact or disconnected micro-topology and are not admitted into this
two-sided nominal band. Existing profile-conditioned graze APIs are separate
and unchanged.

Planetary topology targets exclude the Sun. Solar occultation geometry belongs
to the first-class `/v1/eclipses/*` surfaces, and admitting it here would also
mislabel Moira's separately sourced solar radius as a JPL planetary
solid-body-radius product. The existing legacy occultation routes retain their
prior target contract.
Fixed-star topology labels must be nonblank, have no surrounding whitespace,
and must not use a canonical Solar System body identity.

### Topographic Lunar-Contact Engine Boundary

Topography-conditioned lunar contact chronology is intentionally an
engine-only, direct-import product. Its immutable vessels and solver are
available from `moira.lunar_occultation_contacts`, while event-specific lunar
limb profiles are prepared through `moira.lunar_limb`. There is no `Moira`
facade method, FastAPI route, OpenAPI operation, or request/response schema for
this product.

The three related products retain separate meanings:

- the existing occultation topology routes return nominal spherical
  mean-limb path and limit geometry;
- the engine-only contact solver returns a predicted disappearance,
  reappearance, or tangency chronology conditioned on a prepared lunar
  topography profile; and
- frozen IOTA event reductions preserve observed contact timings as authority
  evidence rather than relabeling them as model output.

The Moira-derived LOLA RDR profile path uses a content-identified DE441/LE441 physical
Moon-to-observer light cone, the NAIF DE440_ME421 lunar orientation resources,
and official USGS LOLA topography. Its finite-distance tangent circle and
perspective-equivalent radii avoid an orthographic surface approximation.
The direct-only profile is a declared half-open-bin-maximum, centre-sample
linear reconstruction and makes no exact sub-bin topography claim.
Physical contact admission is airless and excludes observer-motion aberration
and atmospheric refraction; its stellar ray uses the contact-private
Klioner-equation deflection policy recorded in engine provenance. No
topographic-contact comparison tolerance or
numerical validation result is part of the REST contract. The separately
admitted two-site IOTA/LOLA engine validation does not create a facade method,
route, schema, or transport-level accuracy promise.

### Lunar Eclipse Compatibility REST Contract

`POST /v1/eclipses/lunar/local` retains its existing request and response
schemas. Its request accepts `mode="native"` or `mode="nasa_compat"`; native
remains the default. In NASA-compatible mode, the response now reports
`canon_method="nasa_shadow_axis_apparent_sun_moon"`, and `source_model`
describes the same repaired reduction.

That compatibility method obtains one reception-epoch Earth state, applies
reception light-time and then annual aberration to both the Sun and Moon, and
does not apply gravitational deflection, topocentric parallax, or atmospheric
refraction to the canon contact geometry. The older geometric and retarded
canon policies remain explicit engine method identifiers; the REST request
does not silently select them.

This is an intentional numerical and provenance-label change within the
existing contract. No route was added or renamed, and no request or response
field changed. `POST /v1/eclipses/lunar/next` remains the existing native
search surface.

### Solar Partial-Visibility Footprint REST Contract

`POST /v1/eclipses/solar/footprint` is the additive transport surface for
`Moira.solar_eclipse_footprint(...)`. Its request accepts `jd_start`, optional
`kind` and `backward` search policy, and `sample_count`, which defaults to
`181` and is constrained to the inclusive range `9..721`. `kind` is a closed
enum: `any`, `total`, `annular`, `partial`, `central`, or `hybrid`.

The response preserves the searched event, greatest-footprint point, P1/P4 and
optional P2/P3 contacts, topology, and named boundary-track components. Track
kinds distinguish north/south penumbral envelopes from geometric sunrise and
sunset boundaries. Component identifiers are local to each kind; segment
identifiers are local to each connected component and identify its strictly
time-ordered branches across any shared temporal fold. Each penumbral kind
admitted by the topology has exactly one connected component and therefore
uses `component_id=0`. Its segment identifiers are contiguous `0..n-1`; two
segments meeting at a temporal fold share the refined endpoint. Boundary
`kind`, contact `kind` (`p1` through `p4`), and `topology`
(`one_limit_connected` or `two_limit_two_loop`) are closed response enums.
The two-limit topology also requires disjoint north/south horizon-incidence
sets rather than two labels on one degenerate boundary. It is valid only for a
central global eclipse, and each sunrise/sunset track remains wholly within
P1-P2 or P3-P4 rather than crossing the internal P2-P3 interval. Provenance fields
declare content-identified DE441/LE441, zero-elevation WGS 84, the
spherical physical mean-limb convention, UT1 point epochs, and the absence of
atmospheric refraction.

`sample_count` changes interior point density only. It does not change the
returned `(kind, component_id, segment_id)` graph or its refined contacts,
horizon incidences, and fold endpoints. The DE441 fold-regression slice checks
this contract at `9`, `99`, `181`, `257`, and `721` requested samples.

Every footprint `datetime_utc` field is a UTC string. Modern dates retain the
ordinary Python-datetime ISO form; epochs outside Python's datetime range fall
back to Moira's BCE-safe proleptic-Gregorian ISO form with astronomical year
numbering, including year `0000` and signed negative years.

This endpoint does not add observer elevation or terrain, lunar-limb
topography, magnitude or obscuration contours, local apparent circumstances,
or rendered map products. `POST /v1/eclipses/solar/path` and its
`SolarEclipsePath` response remain unchanged.

## Relationship And Pattern Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/aspects/motion-witness` | `aspect_motion_witness_route` |
| POST | `/v1/aspects/moon-connection-flow` | `moon_connection_flow_route` |
| POST | `/v1/aspects/from-longitudes` | `aspects_from_longitudes_route` |
| POST | `/v1/aspects/from-declinations` | `declination_aspects_from_declinations_route` |
| POST | `/v1/aspects/declination-motion-witness` | `declination_aspect_motion_witness_route` |
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

### Pattern Search And Dominance Policy

The shared `PatternRequest` for `/v1/patterns/find`,
`/v1/patterns/chart-profile`, and `/v1/patterns/network` accepts `chart`,
`include_nodes`, finite `orb_factor` in `(0, 10]`, optional detector-name
`include`, and `dominant_only` (default `false`). The three routes use the same
filtered pattern set so their events, chart condition, and network views cannot
drift. `dominant_only` must be an actual JSON boolean, and `orb_factor` must be
a JSON number; coercive strings and booleans are rejected.

`dominant_only=true` retains maximal structural aspect patterns. A candidate is
contained only when its bodies and full preserved aspect signatures are both
subsets of another admitted aspect-sourced pattern, with at least one strict
inclusion. Thus a Grand Trine inside a Kite and a same-body Trapeze edge-subgraph
inside a Cradle are suppressed, while a pattern with a different relation, an
equal-body equal-edge overlap, or a position-based Stellium is retained.
Selection happens first: an excluded Kite cannot hide an explicitly requested
Grand Trine.

Pattern response `condition_profile.state` is role-resolution completeness,
not applying/separating motion or astrological strength. The structured role
repair means canonical Grand Trine, Minor Grand Trine, Cradle, and Trapeze
responses no longer report `mixed` solely because their detectors lacked role
labels.

### Positions-In Aspect REST Admission Boundary

`POST /v1/aspects/from-longitudes` is the additive, kernel-free analysis route
for composite, Davison, harmonic, progressed, draconic, and other derived chart
positions. It accepts between 2 and 64 named finite ecliptic longitudes, an
explicit aspect `tier` (`0`, `1`, or `2`), a positive bounded `orb_factor`, and
an `include_nodes` flag. Known engine node names are filtered only when that
flag is false.

The route delegates through `Moira.aspects_from_longitudes(...)` to
`moira.aspects.aspects_from_longitudes(...)`, which normalizes the supplied
longitudes, orders points by name for deterministic pair identity, and applies
the canonical `moira.constants.Aspect` definitions through `find_aspects`.
Responses use the existing `AspectData` transport shape and expose actual
separation, target angle, orb, applied orb ceiling, classification, direction,
and sign degrees.

These are caller-supplied positions, not a reconstructed birth moment.
No ephemeris reduction, speed, retrograde state, applying/separating state,
stationary state, house frame, score, or interpretation is fabricated. The
response computation truth records normalized inputs, effective tier and orb
factor, node exclusions, counts, engine/facade entry points, and
`motion_semantics: not_computed_without_speeds`.

### Declination-Aspect REST Admission Boundary

`POST /v1/aspects/from-declinations` is the kernel-free analysis route for
caller-supplied equatorial declinations. It accepts between 2 and 64 named
finite values in `[-90°, +90°]` and a bounded non-negative orb. The route
also requires caller-declared `reference_frame` and `timescale` strings. It
delegates through `Moira.declination_aspects_from_declinations(...)` to the
first-class `moira.declination_aspects` engine while preserving the historical
`moira.aspects` compatibility entrypoint. It returns classified Parallel and
Contra-Parallel vessels with reconstructable orb admission truth.

Parallel requires the same nonzero hemisphere; Contra-Parallel requires
opposite nonzero hemispheres. Two points exactly on the equator form one exact
Parallel, while one equatorial and one non-equatorial point are unclassified.
Computation truth exposes that ambiguity policy, normalized point order, the
effective orb, counts, and the engine/facade entry points.
The response records the declared frame, timescale, and
`provenance: caller_supplied_declinations`; it does not infer an astronomical
reduction product from the numbers alone.

### Declination-Aspect Motion Witness

`POST /v1/aspects/declination-motion-witness` is the kernel-free,
instantaneous motion surface for one caller-selected Parallel or
Contra-Parallel. It requires two signed declinations in `[-90°, +90°]`,
optional declination speeds in degrees/day, the relationship name, orb and
motion tolerances, and caller-declared frame/timescale provenance.

For a Parallel, signed error and relative rate are respectively
`declination1 - declination2` and `speed1 - speed2`. For a Contra-Parallel,
they are `declination1 + declination2` and `speed1 + speed2`. Away from exact,
the sign-adjusted error rate is the orb rate: negative is `applying`, positive
is `separating`, and a rate inside the declared tolerance is `stationary`.
Exactness takes precedence; missing or partial speeds produce
`indeterminate`. An individual zero declination speed does not by itself make
the relationship stationary when the relative error is still changing.

The route enforces the same hemisphere and equator doctrine as detection and
returns the shared declination classification plus the signed error, relative
speed, orb rate, admission truth, policies, provenance, and evaluation scope.
It does not search for a later perfection or prove that a currently applying
relationship will perfect before reversing.

### Signed Aspect-Motion Witness

`POST /v1/aspects/motion-witness` is the kernel-free, instantaneous motion
surface for one caller-selected canonical longitude aspect. It accepts two
named longitudes, optional daily speeds, the canonical aspect name, an orb
factor, exact and relative-rate tolerances, and required caller-declared frame
and timescale provenance.

The response preserves the shortest directed separation, selected signed
aspect branch, directed error, relative speed (`speed2 - speed1`), orb rate,
canonical scaled orb, admission truth, body-specific stationary thresholds,
station flags and reasons, and one of `applying`, `exact`, `separating`,
`stationary`, or `indeterminate`. Missing or partial speeds never fabricate
motion. A non-conjunction aspect requested at zero separation has equally near
positive and negative branches, so the branch and motion state remain
explicitly indeterminate.

This endpoint does not cast a chart, search for a future perfection or station,
or supply Dorothean interpretation. It is the first-class geometry witness
required by later lunar-flow and classical-perfection doctrine.

### Lunar Connection-Flow Witness

`POST /v1/aspects/moon-connection-flow` is the kernel-bound, interpretation-
free exact-event surface for lunar flow. It requires a finite `jd_ut` and an
explicit `previous_window_policy`: `current_sign`, which rejects a lookback,
or `fixed_lookback`, which requires a positive `previous_lookback_days` value
bounded to 30 days at REST. The optional `modern` flag changes the considered
body set explicitly.

The response preserves current tropical sign ingress and egress, both search
intervals, the last exact directional major aspect in the selected previous
window, its signed error and instantaneous motion state at the query, and the
first exact connection before current-sign egress. Event absence carries a
typed reason rather than a fabricated body or aspect. Computation truth names
the apparent geocentric true-ecliptic-of-date position product, UT1 input with
internal TT ephemeris conversion, the canonical `planet_at` geocentric
astrometric longitude-rate product used for motion, engine/facade entry points, and
`none_geometry_only` interpretation semantics.

`POST /v1/composite/chart` and `POST /v1/davison/chart` also return this same
analysis under their required `aspects` member. Their existing `tier`,
`orb_factor`, and `include_nodes` request fields govern the nested analysis;
omitted or null values resolve to tier `1`, orb factor `1.0`, and node
inclusion. The composite and Davison chart vessels remain distinct, but REST
consumers no longer need a second request to analyze the positions returned by
those relationship-chart routes.

## Panchanga Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/panchanga/instant` | `panchanga_instant_route` |
| POST | `/v1/panchanga/instant/profile` | `panchanga_instant_profile_route` |
| POST | `/v1/panchanga/chart` | `panchanga_chart_route` |
| POST | `/v1/panchanga/chart/profile` | `panchanga_chart_profile_route` |
| GET | `/v1/sidereal/ayanamsa-systems` | `sidereal_ayanamsa_systems_route` |
| POST | `/v1/sidereal/ayanamsa` | `sidereal_ayanamsa_route` |
| POST | `/v1/sidereal/convert` | `sidereal_convert_route` |
| POST | `/v1/nakshatra/position` | `nakshatra_position_route` |
| POST | `/v1/nakshatra/bulk` | `nakshatra_bulk_route` |
| POST | `/v1/muhurta/direct/classification` | `muhurta_direct_classification_route` |
| POST | `/v1/muhurta/direct/score` | `muhurta_direct_score_route` |
| POST | `/v1/muhurta/chart/classification` | `muhurta_chart_classification_route` |
| POST | `/v1/muhurta/chart/score` | `muhurta_chart_score_route` |

### Pancha Pakshi Source-Scoped Routes

| Method | Path | Handler |
|---|---|---|
| GET | `/v1/pancha-pakshi/profiles` | `pancha_pakshi_profiles_route` |
| GET | `/v1/pancha-pakshi/profiles/{profile_id}` | `pancha_pakshi_profile_route` |
| GET | `/v1/pancha-pakshi/constitution/uromarisi` | `pancha_pakshi_uromarisi_constitution_status_route` |
| POST | `/v1/pancha-pakshi/identity/aksara` | `pancha_pakshi_aksara_identity_route` |
| POST | `/v1/pancha-pakshi/identity/natal-moon` | `pancha_pakshi_natal_moon_identity_route` |
| POST | `/v1/pancha-pakshi/mappings/nakshatra-bird` | `pancha_pakshi_nakshatra_bird_mapping_route` |
| POST | `/v1/pancha-pakshi/roles/padu` | `pancha_pakshi_padu_bird_mapping_route` |
| POST | `/v1/pancha-pakshi/schedule/nominal` | `pancha_pakshi_nominal_schedule_route` |
| POST | `/v1/pancha-pakshi/schedule/first-eat-bird` | `pancha_pakshi_first_eat_bird_mapping_route` |
| POST | `/v1/pancha-pakshi/sookshma/select` | `pancha_pakshi_sookshma_temporal_selection_route` |
| POST | `/v1/pancha-pakshi/sookshma/schedule-select` | `pancha_pakshi_schedule_sookshma_temporal_selection_route` |
| POST | `/v1/pancha-pakshi/sookshma/civil-time-select` | `pancha_pakshi_civil_time_sookshma_selection_route` |
| POST | `/v1/pancha-pakshi/context/astronomical-paksha` | `pancha_pakshi_astronomical_paksha_route` |
| POST | `/v1/pancha-pakshi/context/local-solar` | `pancha_pakshi_local_solar_context_route` |
| POST | `/v1/pancha-pakshi/schedule/fixed-clock` | `pancha_pakshi_fixed_clock_materialization_route` |
| POST | `/v1/pancha-pakshi/schedule/fixed-clock/current-cell` | `pancha_pakshi_fixed_clock_current_cell_route` |
| POST | `/v1/pancha-pakshi/schedule/solar-proportional` | `pancha_pakshi_solar_proportional_materialization_route` |
| POST | `/v1/pancha-pakshi/schedule/solar-proportional/current-cell` | `pancha_pakshi_solar_proportional_current_cell_route` |
| POST | `/v1/pancha-pakshi/relationships/directed` | `pancha_pakshi_directed_relationship_route` |

The Stage 2O civil-time request requires both profile IDs, aware `dt`,
latitude, longitude, caller-supplied source Paksha, subject bird, one of the
existing fixed-clock or solar-proportional materialization policy IDs, and one
Stage 2K selector policy ID. There are no defaults. The response preserves the
selected current-cell vessel, explicit routing policy, derived samam and exact
rational elapsed nazhigai, and nested Stage 2N composition. A fixed-clock
`unmaterialized_solar_half_tail` instead carries null samam, elapsed offset,
and composition and is never replaced by proportional fallback. The request
accepts no astronomical-paksha inference, outcome, condition, score, election,
or forecast control.

Every computation request requires an explicitly named profile ID or profile
IDs; no route selects a default.
The kernel-free nakshatra mapping route accepts only `profile_id`, explicit
source `profile_paksha`, and a zero-based `nakshatra_index` in `[0, 26]`; it
does not infer a natal Moon, ayanamsa, instant, condition, score, or forecast.
The Uromarisi constitution route exposes immutable SCP closure and admission
metadata only. Historical cells, classifications, candidate relations, graph
data, condition values, prognosis, and medical interpretation remain private
and are not transport fields.
The first admitted profile,
`agastya_madras_1879_akshara_fixed_clock`, binds the named 1879
aksara/query-or-name-initial and operating-schedule source substrate. Its
capability-gated products expose identity, nominal schedule, first-samam EAT
seed, directed relationships, and separately labelled astronomical,
local-solar, fixed-clock, and solar-proportional policies. They do not admit
Padu, natal identity, condition, scoring, or forecasting semantics. Schedule
inputs remain explicit source labels: `purva` or `amara`, `day` or `night`, and
weekday.

The additive Stage 2F request contains only `profile_id`, aware `dt`, and the
required literal
`policy_id="apparent_geocentric_moon_sun_longitude_paksha_half_open_v1"`.
It accepts no latitude, longitude, observer elevation, caller-supplied paksha,
ayanamsa, correction switch, schedule selector, or natal input. The aware
datetime is normalized to UTC, crosses the facade boundary to UT1 once, and is
converted once to the reader-bound TT used by both body evaluations.

The `PanchaPakshiAstronomicalPakshaResponse` publishes requested UT1 and TT,
apparent geocentric Sun and Moon longitudes in the true ecliptic of date,
normalized Moon-minus-Sun elongation, the `shukla` or `krishna` astronomical
half, the source-mapped `purva` or `amara` profile label, exactly one mapping
locator, the immutable policy, and provenance. The policy owns exact half-open
classification with no tolerance or snapping: `[0, 180)` is
Shukla/waxing/Purva and `[180, 360)` is Krishna/waning/Amara. Exact `0` and
`180` degrees therefore belong to Shukla/Purva and Krishna/Amara respectively.
No ayanamsa is applied because a common longitude offset cancels from the phase
difference.

The Purva mapping is directly attested at IA leaf `n16`, and the Amara mapping
at `n26`, for this named 1879 profile. Their reading status remains
machine-assisted visual reading with explicit uncertainty and no human-review
dependency; the route does not claim an independently corroborated or universal vocabulary. It
performs no schedule selection, materialization, current-cell selection,
automatic routing into another request, or natal identity. No source scan,
PDF, OCR, page image, copied expression, or translation is bundled.

The separate Stage 2G route requires
`profile_id="bogamuni_chennai_2024_nakshatra_natal_identity"`, an aware `dt`,
and the exact literal
`policy_id="bogamuni_2024_apparent_lahiri_natal_moon_identity_v1"`. Those are
the only request fields. Location, supplied paksha, nakshatra or bird,
caller-selected ayanamsa, correction switches, schedule/current-cell controls,
scoring, and forecast controls are rejected. The aware datetime is normalized
to UTC, crosses to UT1 once, and derives one reader-bound TT epoch shared by the
apparent geocentric Sun/Moon evaluation and the Lahiri-true sidereal Moon.
The response policy spells the interoperable ayanamsa token exactly as
`ayanamsa_system="Lahiri"`, matching the existing sidereal request surface.

`PanchaPakshiNatalMoonIdentityResponse` exposes requested UT1/TT, tropical Sun
and Moon longitudes, Moon-minus-Sun elongation, astronomical and source Paksha,
the phase-mapping locator, Lahiri ayanamsa, sidereal Moon longitude, 0-based
nakshatra index and name, degrees within the sector, the nested source-table
bird mapping and locator, the complete immutable policy, and provenance. The
policy states that applying the source table to a birth Moon, selecting Lahiri
true ayanamsa, and using 27 equal half-open `40/3`-degree sectors are a modern
Moira composition, not claims found in the source. Exact internal boundaries
belong to the following nakshatra; the bounded one-ULP recovery only restores a
mathematically exact boundary after binary representation.

The named Bogamuni 2024 source attests the Purva table at IA leaf `n52`, the
complete Amara verse at `n64`, and the phase/Paksha binding at `n167`. The
adjacent Amara commentary duplicates Shravana and omits Revati, so the declared
`verse_precedence_for_nakshatra_partition` policy retains it as rejected
conflict evidence instead of repairing or mixing it. The Uromarisi 1934 witness
corroborates the Purva grouping and exhibits a related malformed Amara
commentary but is not imported into the runtime table. Neither archival source
artifact, OCR, rendered page, source prose, copied layout, nor translation is
bundled.

The separate Stage 2H route requires
`profile_id="bogamuni_chennai_2024_padu_bird_mapping"`, an explicit
`profile_paksha` (`purva` or `amara`), and an explicit weekday. Those are its
only request fields. The strict request rejects datetime, location, day/night
half, schedule or activity fields, natal inputs, policy IDs, Adhikara/Bharana
aliases, condition, score, and forecast controls.

`PanchaPakshiPaduBirdMappingResponse` returns the explicit profile Paksha and
weekday, one bird, `mapping_status="direct_source_attested"`, the exact
death-or-inoperative source-table semantics, the stanza-precedence assembly
policy, three canonical source locators, and profile provenance. Purva cells
cite the governing Bogamuni leaf `n52`; Amara cells cite `n60`; all cells also
cite the repeated combined table and commentary at `n157` and `n158`. The
table has exactly fourteen cells and no day/night axis.

Padu is not converted to the schedule's `RULE` activity, a current-time role,
an authority bird, or the separately labelled eating bird. The primary
witnesses label an eating-bird table and authority days rather than an
`Adhikara Pakshi` table, while Bharana is secondary-only terminology. The API
therefore admits neither alias nor product and does not relabel
`first_eat_bird`. Uromarisi 1934 and Bogar material remain separately observed,
unbound research context and supply no REST/runtime cell or Stage 2H admission
proof.

The Stage 2I route requires
`profile_id="agastya_madras_1879_akshara_fixed_clock"`, explicit
`profile_paksha` (`purva` or `amara`), explicit `half` (`day` or `night`), and
an explicit weekday. Those are its only request fields. The strict request
rejects datetime, location, inferred Paksha, Padu or authority aliases,
schedule/materialization controls, natal inputs, condition, score, and forecast
fields.

`PanchaPakshiFirstEatBirdMappingResponse` returns the named generator ID, exact
input axes, `first_eat_bird`, `mapping_status="direct_source_attested"`, fixed
source-table semantics, the complete canonical generator locator tuple, and
profile provenance. The 28 possible cells bind the governing 1879 leaves
`n16`, `n21`, `n26`, and `n31`; the other returned locators are same-witness
generator confirmation. The operation does not materialize the 25-cell
schedule. Its bird is only that generator's first-samam EAT seed, not an
ambient whole-day eating bird, Padu, an authority/Adhikara/Bharana bird,
current activity, condition, score, electional judgment, or forecast.

The Stage 2K selector route requires
`profile_id="bogamuni_chennai_2024_sookshma_temporal_selector"`, one explicit
`policy_id`, one `parent_activity`, and an exact reduced
`elapsed_nazhigai={numerator, denominator}` in `[0, 6)`. The only policy IDs
are `bogamuni_2024_weighted_sookshma_samam_v1` and
`bogamuni_2024_eka_sookshma_equal_fifths_v1`; neither is a default. The
weighted response rotates the exact activity-duration vector from the parent
activity. The equal-fifths response contains five exact ordinal cells with
`activity=null`, because no subactivity assignment is attested. The response
echoes the selected policy, all five exact half-open intervals, the unique
selected ordinal and interval, two source locators, and provenance. The strict
request rejects floating-point offsets, unreduced fractions, datetime,
location, schedule, Uromarisi outcome, condition, score, electional, and
forecast fields. No human-language reviewer is required.

The additive local-solar context request contains `profile_id`, aware `dt`,
`latitude`, `longitude`, caller-supplied `paksha`, and the required literal
`policy_id="local_solar_day_explicit_paksha_v1"`. It derives the governing
topocentric sunrise, sunset, next sunrise, day/night half, and
local-mean-solar weekday, then selects the existing nominal schedule. The
response exposes `requested_jd_ut1`, the three solar-event UT1 JDs, location,
paksha, half, weekday, the complete fixed policy vessel, nominal schedule, and
provenance.

The policy vessel makes the horizon convention explicit: observer elevation
is fixed at `0 m`, the solar-altitude signal is unrefracted, and the
`-0.833`-degree threshold incorporates conventional standard refraction and
solar semidiameter. The route does not accept an ambient elevation or weather
model.

The additive fixed-clock request contains the same `profile_id`, aware `dt`,
`latitude`, `longitude`, and caller-supplied `paksha`, plus the required literal
`policy_id="fixed_24_minute_nazhigai_from_local_solar_half_start_v1"`. It
anchors day at governing sunrise or night at governing sunset, applies each
exact nominal offset as `1440` SI seconds per nazhigai on reader-bound TT, and
projects every endpoint to UT1. The response includes the Stage 2A context,
complete fixed policy, TT and UT1 anchor/end fields, signed
`fixed_end_jd_tt_minus_solar_end_jd_tt` topology, boundary relation, all
half-open materialized cells, and provenance. The fixed end is never clipped or
stretched to the solar end; `0.0001 s` is only the numerical topology
coalescence threshold.

The additive current-cell request contains the same `profile_id`, aware `dt`,
`latitude`, `longitude`, and caller-supplied `paksha`, plus the required literal
`policy_id="fixed_clock_current_cell_half_open_solar_precedence_v1"`. It first
resolves the governing half-open local-solar half, then applies exact
zero-tolerance membership on reader-bound TT to that half's admitted Stage 2B
cells. The response includes profile, requested UT1/TT, location, paksha, half,
weekday, immutable selection policy, TT/UT1 anchor and end witnesses, signed
solar-end residual and topology, finite `selection_status`, selected
materialized `current_cell` or explicit null, and provenance. The complete
materialization remains the governing engine object without being duplicated
as a nested transport payload.

The status is `selected` when exactly one cell satisfies
`start_jd_tt <= requested_jd_tt < end_jd_tt`. Shared endpoints belong to the
following cell and the fixed end is excluded. At exact sunset or sunrise, the
new governing half takes precedence; cells extending past the prior half's
solar end are never eligible. When a long solar half continues after the fixed
span, the route returns `unmaterialized_solar_half_tail` and
`current_cell=null`. It never clips, wraps, repeats, stretches, or retains a
cell, and the Stage 2B `0.0001 s` topology coalescence does not affect
membership.

The additive Stage 2D request contains `profile_id`, aware `dt`, `latitude`,
`longitude`, caller-supplied `paksha`, and the required literal
`policy_id="solar_proportional_nominal_offsets_over_governing_half_tt_v1"`.
It resolves the Stage 2A governing solar half, preserves every exact nominal
offset as a rational fraction of the full 30-nazhigai schedule, and maps each
distinct endpoint independently across that actual half on reader-bound TT.
Interior endpoints are projected to UT1 through the same reader; the first and
last endpoints close exactly on the TT and UT1 anchor and governing solar-half
end.

The `PanchaPakshiSolarProportionalMaterializationResponse` result contains the
local-solar context, the complete
`PanchaPakshiSolarProportionalMaterializationPolicyResponse`, TT/UT1 outer
bounds, `solar_half_duration_seconds_tt`, exactly 25 contiguous half-open
`PanchaPakshiSolarProportionalCellResponse` values, and provenance. Each cell
retains its unchanged nominal cell, exact start/end/span fractions, TT and UT1
endpoints, and TT duration. This explicit modern Moira policy does not use the
Stage 2B fixed 1,440-second nazhigai, does not select a current cell, and does
not infer paksha from the Moon. The named 1879 witness attests the nominal
schedule and exact rational offsets, but it does not attest proportional
sunrise-to-sunset timing.

The additive Stage 2E current-cell request uses the same explicit profile,
aware `dt`, bounded location, and caller-supplied paksha, plus the required
literal
`policy_id="solar_proportional_current_cell_half_open_solar_precedence_v1"`.
It resolves the governing solar half first, constructs the unchanged Stage 2D
materialization with the same reader, converts the requested instant to
reader-bound TT once, and applies exact zero-tolerance half-open membership.
The anchor belongs to cell zero, shared endpoints belong to the following cell,
and exact sunrise or sunset belongs to the newly governing half.

`PanchaPakshiSolarProportionalCurrentCellResponse` is deliberately compact. It
contains profile, requested UT1/TT, location, paksha, half, weekday, the complete
13-field selection policy, TT/UT1 governing bounds, TT half duration,
`selection_status="selected"`, one non-null proportional cell, and provenance;
it does not duplicate the complete 25-cell materialization. Stage 2D covers the
entire governing solar half, so the route exposes no null cell or fixed-clock
tail status. Zero or multiple matches fail closed rather than invoking
tolerance, clipping, wrapping, borrowing, fixed-clock fallback, or inference.

Responses preserve admission status, capabilities, decision identity, source
and locator provenance, assembly policy, astronomical-routing status, and
declared omissions. Exact nazhigai values serialize as integer
`numerator`/`denominator` objects rather than binary floats.

The astronomical-paksha and natal-Moon routes accept a datetime but no location
and return only their respective instantaneous products. The local-solar context,
fixed-clock materialization, fixed-clock current-cell, solar-proportional
materialization, and solar-proportional current-cell routes accept both a
datetime and location and continue to require caller-supplied paksha. No result
is ambiently inserted into another operation. The family does not accept a
caller-supplied natal Moon longitude, paksha/nakshatra/bird override on the
natal route, caller-supplied sunrise, timezone policy, scoring rule, or inferred
name. Natal identity occurs only on the explicit Stage 2G route. The family
performs no implicit seasonal scaling, vinadi or Uromarisi-outcome routing, Bharana/Adhikara
computation, condition scoring, window search, or cross-witness normalization.
Padu lookup occurs only on the explicit Stage 2H pure-table route and never
supplies an input to another operation. First-EAT lookup occurs only on the
explicit Stage 2I pure-table route and never materializes or selects a current
schedule. Fixed 1,440-second
nominal-offset materialization occurs only on the explicit Stage 2B route;
proportional full-half materialization occurs only on the explicit Stage 2D
route under its distinct modern policy, and proportional current-cell selection
occurs only on the explicit Stage 2E route. The Stage 2A context route alone
still returns no materialized interval, and Stage 2F never selects a schedule.
Fixed-clock current-cell selection occurs only on the explicit Stage 2C route
under its separate required policy and applies only to the Stage 2B fixed-clock
cells. Stage 2G likewise never selects or materializes a schedule, current cell,
score, or forecast. Stage 2H accepts no instant or location and never selects a
schedule, current cell, identity, condition, score, or forecast. Stage 2I also
accepts no instant or location and returns only one source-scoped generator
seed.
Stage 2K performs only explicit exact Sookshma selection within one samam; it
never supplies a clock, schedule, Uromarisi outcome, condition, score, or
forecast to another operation.

### Sidereal And Nakshatra Utility REST Admission Boundary

The admitted P-GAP-05 utility surface is the bounded synchronous
`/v1/sidereal/*` and `/v1/nakshatra/*` route family:

- `GET /v1/sidereal/ayanamsa-systems`
- `POST /v1/sidereal/ayanamsa`
- `POST /v1/sidereal/convert`
- `POST /v1/nakshatra/position`
- `POST /v1/nakshatra/bulk`

`/v1/sidereal/ayanamsa-systems` exposes the built-in ayanamsa registry and
J2000 reference values. `/v1/sidereal/ayanamsa` exposes one date-specific
ayanamsa value for an admitted named system and mode. `/v1/sidereal/convert`
converts one longitude between tropical and sidereal frames.

`/v1/nakshatra/position` and `/v1/nakshatra/bulk` expose mechanical placement
into Moira's current 27-equal-Nakshatra taxonomy. Responses preserve
Nakshatra name, 0-based index, 1-based number, lord, pada, degrees elapsed,
degrees remaining, and sidereal longitude.

This admission does not expose Panchanga judgement, Muhurta classification,
Dasha balance, chart-backed Moon derivation, chart-backed sidereal houses,
Varga projection, Manazil, Abhijit Nakshatra, user-defined ayanamsa REST
payloads, mutable global sidereal mode, interpretation text, recommendations,
dense tables, async sweeps, or kernel path mutation.

### Muhurta REST Admission Boundary

The admitted P-GAP-02 Muhurta REST surface is the bounded synchronous
`/v1/muhurta/*` route family. It exposes Vedic Muhurta moment classification
and raw engine scoring over Panchanga truth.

Direct routes reuse the direct Panchanga derivation path: caller-supplied Sun
longitude, Moon longitude, JD, and ayanamsa policy. Chart-backed routes reuse
the chart-backed Panchanga derivation path: `Moira.chart` derives Sun/Moon
truth, then `moira.panchanga.panchanga_at` supplies the five Panchanga limbs.

The admitted routes are:

- `POST /v1/muhurta/direct/classification`
- `POST /v1/muhurta/direct/score`
- `POST /v1/muhurta/chart/classification`
- `POST /v1/muhurta/chart/score`

Responses preserve request echo, Panchanga source limbs, exposed Muhurta
policy weights, classification labels, reasons, and provenance. Score
responses preserve the raw unbounded engine score, score breakdown, score
scale, and score direction.

This admission does not expose Muhurta search windows, activity-specific
guidance, Abhijit/Brahma Muhurta routes, Tara Bala inputs, recommendation
language, Western electional search/scoring, arbitrary predicates, arbitrary
scorers, or async search jobs. The separate Ramesey v1 single-moment route is
not a Muhurta product or a search route.

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

## Church of Light Astrodynes Routes

| Method | Path | Handler | Kernel |
|---|---|---|---|
| GET | `/v1/astrodynes/doctrine` | `astrodynes_doctrine_route` | No |
| POST | `/v1/astrodynes/geometry` | `astrodynes_geometry_route` | No |
| POST | `/v1/astrodynes/chart` | `astrodynes_chart_route` | Yes |

Progressed Astrodynes accepts explicit, kernel-free doctrinal inputs and one
kernel-backed chart product. Doctrine and practical responses disclose the
source publication discrepancies; executable values follow the manual's stated
formulas.

| Method | Path | Handler | Kernel |
|---|---|---|---|
| GET | `/v1/astrodynes/progressed/doctrine` | `progressed_astrodynes_doctrine_route` | No |
| POST | `/v1/astrodynes/progressed/normal` | `progressed_astrodynes_normal_route` | No |
| POST | `/v1/astrodynes/progressed/dated-aspect` | `progressed_astrodynes_dated_aspect_route` | No |
| POST | `/v1/astrodynes/progressed/major-relation` | `progressed_astrodynes_major_relation_route` | No |
| POST | `/v1/astrodynes/progressed/accessory-relation` | `progressed_astrodynes_accessory_relation_route` | No |
| POST | `/v1/astrodynes/progressed/reenforcement` | `progressed_astrodynes_reenforcement_route` | No |
| POST | `/v1/astrodynes/progressed/practical` | `progressed_astrodynes_practical_route` | No |
| POST | `/v1/astrodynes/progressed/total-influence` | `progressed_astrodynes_total_influence_route` | No |
| POST | `/v1/astrodynes/progressed/compound-total-influence` | `progressed_astrodynes_compound_total_influence_route` | No |
| POST | `/v1/astrodynes/progressed/chart` | `progressed_astrodynes_chart_backed_route` | Yes |
| POST | `/v1/astrodynes/progressed/search` | `progressed_astrodynes_search_route` | Yes |
| POST | `/v1/astrodynes/progressed/integrate` | `progressed_astrodynes_integrate_route` | Yes |

`/progressed/chart` accepts timezone-aware natal and target datetimes,
latitude, longitude, house system, and an explicit fallback opt-in. It derives
the Church of Light Limiting Date, major ephemeris date, Minor Ephemeris Date,
transit date, progressed M.C./Ascendant, four terminal tiers, the natal and
normal calculations, accessory relations, reenforcements, and practical
distribution. The response preserves the selected time keys, geocentric
apparent frame, angle method, natal house frame, requested/effective house
systems, and fallback truth.

`/progressed/search` returns bounded one-degree entry and exit contacts, exact
perfections or named closest approaches, optional minor reenforcement power,
clipped-boundary truth, and the sampling/refinement policy. Requests are
bounded by `max_samples`.

`/progressed/integrate` applies composite trapezoidal quadrature to the actual
ephemeris-varying instantaneous power/harmony/discord curve. Results are in
astrodyne-, harmodyne-, and discordyne-days. The manual's constant-rate
`0.75 * peak * duration` result remains visible only as a comparator; method,
step, sample count, coarse comparison, and error estimate are explicit. The
comparator is `null` for a partial interval whose endpoints are not both the
one-degree limits.
The integration request requires `max_samples >= 3`. The engine uses an even
fine-interval count with a nested 2:1 coarse mesh; `sample_count` is the actual
number of unique chronology evaluations and never exceeds `max_samples`.

`/geometry` requires exactly the ten Astrodyne planets, declinations for those
planets plus `M.C.` and `Asc.`, twelve cusps forming one ordered zodiacal
circuit, and explicit M.C./Asc. values matching cusps 10/1. It normalizes
longitudes and returns the complete calculation without engine or kernel access.

`/chart` requires a timezone-aware datetime, latitude, longitude, and house
system. Planetary positions and declinations are geocentric apparent; latitude
and longitude govern the houses only. House fallback is rejected by default.
When `allow_house_fallback` is true, the response records requested/effective
systems and the fallback reason. A fallback figure that places more than two
cusps in one sign is rejected explicitly because that allocation lies outside
the bounded aggregate doctrine currently validated by the engine.

Both calculation responses expose normalized geometry, fixed policy, all
detected relations with distinct admitted and scored flags, derivation truth,
body profiles, sign/house checksum truth, Class 5 summary families, relation
network, invariant failures, and provenance. Chart-backed geometry also retains
the requested datetime/location, Julian date, and true obliquity used for the
declination conversion. The fixed Church of Light doctrine
is not caller-selectable or blended with conventional dignity tables.

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

The bounds doctrine selector admits `egyptian`, `ptolemaic`,
`chaldean_day`, and `chaldean_night`. Chaldaean bounds are sect-dependent;
the ambiguous value `chaldean` is rejected. Table and bound-truth responses
include the primary-source citation for the selected variant.

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
| POST | `/v1/astrocartography/chart/subjects/lines` | `astrocartography_subject_chart_lines_route` |
| POST | `/v1/astrocartography/chart/subjects/subplanetary` | `astrocartography_subject_chart_subplanetary_route` |

Body-class truth:

- Direct Astrocartography routes are caller-owned coordinate routes. Their
  labels may name selected planets, minor bodies, fixed stars, or other
  apparent RA/Dec subjects when the caller supplies valid RA/Dec and sidereal
  time.
- Chart-backed Astrocartography line routes admit selected chart planets and
  selected asteroids when the public apparent topocentric RA/Dec path supports
  the subject. Chart-backed comet lines remain deferred.
- Chart-backed Astrocartography subplanetary routes admit selected chart
  planets plus selected asteroids and comets through the geocentric
  ecliptic-to-equatorial path.
- Mixed-subject chart routes accept typed `subjects` entries for admitted
  planets, admitted asteroids/comets, fixed stars from the sovereign star
  registry, lots computed through the Lots engine, caller-supplied ecliptic
  points, and caller-supplied RA/Dec points. Every subject is resolved into
  RA/Dec before ACG geometry is computed.
- Lot subjects require explicit observer latitude/longitude because the Lots
  engine derives ASC, houses, and day/night truth from the chart site.
- Catalog-wide fixed-star, asteroid, comet, and small-body sweeps remain
  deferred; mixed-subject routes are explicit-selection surfaces.
- Astrocartography provenance includes a `subjects` list carrying subject
  class, canonical name, NAIF ID when applicable, and position source.

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

## Galactic Houses Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/galactic-houses/cusps` | `galactic_house_cusps_route` |
| POST | `/v1/galactic-houses/placement` | `galactic_house_placement_route` |
| POST | `/v1/galactic-houses/chart/placements` | `galactic_house_chart_placements_route` |

## Gauquelin Routes

| Method | Path | Handler |
|---|---|---|
| POST | `/v1/gauquelin/sector` | `gauquelin_sector_route` |
| POST | `/v1/gauquelin/sectors` | `gauquelin_sectors_route` |
| POST | `/v1/gauquelin/chart/sectors` | `gauquelin_chart_sectors_route` |

## Progressions, Timelords, Dasha, Varshaphal, And Primary Directions

### Progression method menus

Three progression endpoints are method-dispatched: the `method` field selects
the technique. The accepted keys are enumerated in the OpenAPI schema (they are
`Literal` types on the request models) and are the single source of truth for
the runtime dispatch registries in `moira_server/models/progressions.py`. Every
technique also accepts `converse: bool` (default `false`) for the converse
direction.

`POST /v1/progressions/arc` — `method`, one of:

| Key | Doctrinal name |
|---|---|
| `solar_arc` | Solar Arc (Sun's arc applied to all bodies) |
| `solar_arc_right_ascension` | Solar Arc in Right Ascension |
| `naibod_longitude` | Naibod in Longitude |
| `naibod_right_ascension` | Naibod in Right Ascension |
| `mean_solar_arc_longitude` | Mean Solar Arc in Longitude (Naibod rate) |
| `mean_solar_arc_right_ascension` | Mean Solar Arc in Right Ascension |
| `one_degree_longitude` | One Degree in Longitude |
| `one_degree_right_ascension` | One Degree in Right Ascension |
| `planetary_arc` | Planetary Arc (requires `arc_body`, the reference planet) |

`POST /v1/progressions/time-key` — `method`, one of:

| Key | Doctrinal name |
|---|---|
| `tertiary` | Tertiary (synodic month = one year) |
| `tertiary_ii` | Tertiary II (tropical-month variant) |
| `minor` | Minor (solar year / synodic month) |
| `duodenary` | Duodenary (Carter, 2h05m per year) |
| `quotidian_solar` | Quotidian Solar (secondary day-for-day) |
| `quotidian_lunar` | Quotidian Lunar (lunar-month day-for-day) |

`POST /v1/progressions/house-frame/arc` — `method`, one of:

| Key | Doctrinal name |
|---|---|
| `ascendant_arc` | Ascendant Arc (the natal ascendant's daily arc) |
| `vertex_arc` | Vertex Arc (the natal vertex's daily arc) |

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

### Primary-directions transport contract

The eight paths above are stable. The compact and reduction variants share the
same engine computation; reduction responses add resolved preset/policy, key,
search-mode, requested observer, and effective house-system truth.

Policy resolution is enum-backed. Canonical preset names are preferred;
recognized historical aliases remain adapters and the reduction truth preserves
both requested and canonical identity. A supplied preset may not conflict with
an explicit method or space. An unqualified Ptolemy `in_zodiaco` request is
ambiguous and is rejected; clients must choose the aspect, antiscia, or
parallel preset that names the intended doctrine. The solar key requires an
explicit positive natal solar rate. `PLACIDUS_MUNDANE` and
`PLACIDIAN_CLASSIC_SEMI_ARC` reject `in_zodiaco` because those runtime methods
are mundane-only. Fixed-star targets require conjunction admission, and
rapt-parallel direct/converse motion remains specific to the configured rapt
relation and target rather than widening the ordinary policy.

The canonical
`topocentric_zodiacal_aspect_signed_primary_motion` preset is the explicit
source-scoped exception to ordinary role-exchanged converse. It computes one
ordered Topocentric zodiacal-aspect arc with assigned-zero aspect latitude and
zodiacal projected perfection, then wraps that arc to `(-180, 180)` degrees:
positive is direct, negative is converse, numerical zero is no event, and the
directionally ambiguous `180`-degree boundary fails closed. It requires
`include_converse=true`; under this doctrine the flag admits either label from
the single ordered construction rather than asking for a role-exchanged second
arc. It also requires explicit, non-empty `significators` and `promissors`;
the unrestricted candidate set contains the antipodal MC/IC pair and therefore
cannot carry one deterministic signed label. The ordinary
`topocentric_zodiacal_aspect` preset remains unchanged.

Signed-primary-motion is available only when the transport performs
`engine_search`. The submitted-only `relations` path and every request carrying
`submitted_arcs` reject that preset because submitted arcs contain a positive
magnitude and label, not the ordered raw arc required to derive the sign.
Reduction responses identify the signed doctrine and canonical preset exactly.
No path or established response field is added or replaced. This narrow preset
is not the separately deferred global `neo-converse` doctrine.

The six engine-search paths (`arcs`, `profile`, and `network`, including their
reduction siblings) also accept these additive, typed target/context lists on
the search request:

- `antiscia_targets`: `{source_name, kind}` where `kind` is `antiscion` or
  `contra_antiscion`
- `ptolemaic_parallel_targets`: `{source_name, relation}` where `relation` is
  `parallel` or `contra_parallel`
- `placidian_rapt_parallel_targets`: `{source_name}`; direct versus converse is
  owned by the selected rapt-parallel preset
- `fixed_star_targets`: `{star_name}` resolved through Moira's sovereign star
  catalog
- `morinus_aspect_contexts`:
  `{source_name, maximum_latitude, moving_toward_maximum}`

Each list and their combined materialized total are bounded to 256 items.
Duplicate derived identities or duplicate Morinus source contexts fail closed.
These lists are search materialization inputs, so they cannot accompany
`submitted_arcs` and are not accepted by the submitted-only `relations`
request. Antiscia requires `ptolemy_zodiacal_antiscia`, Ptolemaic parallels
require `ptolemy_zodiacal_parallel`, rapt targets require the corresponding
direct or converse rapt preset, and Morinus contexts require
`morinus_zodiacal_aspect`. Fixed stars compose with any preset whose resolved
relation/target policy admits their conjunction branch. Reduction responses
preserve the exact resolved target/context vessels and rapt motion; they do not
collapse a Morinus path context to its source name.

`profile` and `network` accept either engine search inputs or a bounded
submitted-arc list; `relations` is submitted-only. Submitted items are validated
and reconstructed as real `PrimaryArc` vessels; no transport duck type or hidden
conversion fallback is used. On the search-capable routes, omission means
`engine_search`. An explicitly supplied empty list means `submitted_arcs` with
no items and returns a valid empty transport response. Lists are bounded to
4,096 items. In an empty profile response, `profiles=[]`,
all counts are zero, and `strongest_significator` / `weakest_significator` are
`null`; `nearest_arc=0.0` and `farthest_arc=0.0` are transport compatibility
sentinels only and do not represent measured arcs. An empty network response
uses `nodes=[]`, `edges=[]`, `isolated=[]`, and `most_connected=null`; that
vessel has no numeric arc extrema.

Natal latitude/longitude construct the natal chart. `observer_lat` and
`observer_lon` construct directional houses and own the geographic latitude
used by primary-direction geometry. Zero is a lawful longitude and is retained.
`include_relations` controls response depth only; it does not change or mutate
the engine profile. Arc responses preserve positional `relational_kind`
separately from the compatibility perfection-kind `relation_kind` field.
`solar_rate_explicit` distinguishes a generated or submitted natal solar rate
from the numeric compatibility rate retained on a non-solar submitted arc;
only the former can support solar-key conversion.

For every `/v1/varshaphal/*` request, the timezone offset supplied on
`natal_dt` owns the doctrinal civil birth date and therefore the birth year
used by Muntha and Mudda progression. The offset is not transport-only
metadata: two representations of the same instant may lawfully name different
local civil birth dates. The natal, query, and focus instants are independently
reduced from UTC to UT1 before astronomical computation.

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
| GET | `/v1/asteroids/subsets` | `asteroid_subsets` |
| GET | `/v1/asteroids/subsets/{subset}/list` | `asteroid_subset_list` |
| POST | `/v1/asteroids/subsets/{subset}/positions` | `asteroid_subset_positions` |
| GET | `/v1/asteroids/families/by-number/{number}` | `asteroid_family_by_number` |
| GET | `/v1/asteroids/families/{family_name}/members` | `asteroid_family_members` |
| POST | `/v1/asteroids/families/chart` | `asteroid_families_in_chart` |
| POST | `/v1/asteroids/families/chart/resonance-network` | `asteroid_family_resonance_network` |
| POST | `/v1/comets/position` | `comet_position` |
| POST | `/v1/comets/bulk` | `comets_bulk` |
| GET | `/v1/comets/list` | `list_comets` |
| GET | `/v1/manazil/catalog` | `manazil_catalog_route` |
| POST | `/v1/manazil/position` | `manazil_position_route` |
| POST | `/v1/manazil/bulk` | `manazil_bulk_route` |
| GET | `/v1/manazil/traditions/{tradition}/mansions/{mansion_index}` | `manazil_tradition_lookup_route` |
| GET | `/v1/nodes/catalog` | `node_catalog_route` |
| POST | `/v1/nodes/planetary/mean` | `mean_planetary_node_route` |
| POST | `/v1/nodes/planetary/mean/bulk` | `mean_planetary_nodes_bulk_route` |
| POST | `/v1/nodes/geometric` | `geometric_node_route` |
| POST | `/v1/orbits/elements` | `orbital_elements_route` |
| POST | `/v1/orbits/distance-extremes` | `distance_extremes_route` |
| POST | `/v1/phenomena/planet` | `planet_phenomena_route` |
| POST | `/v1/phenomena/orbital-events` | `orbital_phenomena_events_route` |
| POST | `/v1/phenomena/proximity` | `proximity_events_route` |
| POST | `/v1/solar-condition/instant` | `solar_condition_instant_route` |
| POST | `/v1/solar-condition/events` | `solar_condition_events_route` |
| GET | `/v1/uranian/catalog` | `uranian_catalog_route` |
| POST | `/v1/uranian/position` | `uranian_position_route` |
| POST | `/v1/uranian/bulk` | `uranian_bulk_route` |
| GET | `/v1/harmonics/presets` | `harmonic_presets_route` |
| POST | `/v1/harmonics/chart` | `harmonic_chart_route` |
| POST | `/v1/harmonics/age-chart` | `harmonic_age_chart_route` |
| POST | `/v1/harmonics/conjunctions` | `harmonic_conjunctions_route` |
| POST | `/v1/harmonics/pattern-score` | `harmonic_pattern_score_route` |
| POST | `/v1/harmonics/aspects` | `harmonic_aspects_route` |
| POST | `/v1/harmonics/sweep` | `harmonic_sweep_route` |
| POST | `/v1/harmonics/fingerprint` | `harmonic_fingerprint_route` |
| POST | `/v1/harmonics/composite` | `harmonic_composite_route` |
| POST | `/v1/harmonics/transit-forecast` | `harmonic_transit_forecast_route` |
| POST | `/v1/harmograms/vector` | `harmogram_vector_route` |
| POST | `/v1/harmograms/zero-aries-vector` | `harmogram_zero_aries_vector_route` |
| POST | `/v1/harmograms/intensity-spectrum` | `harmogram_intensity_spectrum_route` |
| POST | `/v1/harmograms/projection` | `harmogram_projection_route` |
| POST | `/v1/harmograms/trace` | `harmogram_trace_route` |
| POST | `/v1/phase/illuminated-fraction` | `illuminated_fraction_route` |
| POST | `/v1/phase/synodic` | `synodic_phase_route` |
| POST | `/v1/phase/elongation` | `elongation_route` |
| POST | `/v1/phase/angle` | `phase_angle_route` |
| POST | `/v1/phase/angular-diameter` | `angular_diameter_route` |
| POST | `/v1/phase/apparent-magnitude` | `apparent_magnitude_route` |
| POST | `/v1/antiscia/reflect` | `antiscia_reflect_route` |
| POST | `/v1/antiscia/contacts` | `antiscia_contacts_route` |
| POST | `/v1/antiscia/to-point` | `antiscia_to_point_route` |
| POST | `/v1/draconic/longitude` | `draconic_longitude_route` |
| POST | `/v1/draconic/positions` | `draconic_positions_route` |
| POST | `/v1/draconic/chart` | `draconic_chart_route` |
| POST | `/v1/nine-parts/abu-mashar` | `abu_mashar_nine_parts_route` |
| POST | `/v1/planetary-hours/schedule` | `planetary_hours_schedule_route` |
| POST | `/v1/planetary-hours/hour-at` | `planetary_hours_hour_at_route` |
| POST | `/v1/huber/dynamic-intensity` | `huber_dynamic_intensity_route` |
| POST | `/v1/huber/house-zones` | `huber_house_zones_route` |
| POST | `/v1/huber/age-point` | `huber_age_point_route` |
| POST | `/v1/huber/intensity-at` | `huber_intensity_at_route` |
| POST | `/v1/huber/chart-intensity-profile` | `huber_chart_intensity_profile_route` |
| POST | `/v1/huber/age-point-contacts` | `huber_age_point_contacts_route` |
| POST | `/v1/lord-of-the-orb/sequence` | `lord_of_the_orb_sequence_route` |
| POST | `/v1/lord-of-the-orb/current` | `lord_of_the_orb_current_route` |
| POST | `/v1/lord-of-the-turn/profile` | `lord_of_the_turn_profile_route` |
| GET | `/v1/electional/predicate-profiles` | `electional_predicate_profiles_route` |
| GET | `/v1/electional/scorer-profiles` | `electional_scorer_profiles_route` |
| POST | `/v1/electional/windows` | `electional_windows_route` |
| POST | `/v1/electional/moments` | `electional_moments_route` |
| POST | `/v1/electional/scored` | `electional_scored_route` |
| POST | `/v1/electional/western/lunar-ecliptic-direction` | `lunar_ecliptic_direction_route` |
| POST | `/v1/electional/western/ramesey-moon-condition` | `ramesey_moon_condition_route` |
| POST | `/v1/electional/western/sahl-moon-condition` | `sahl_moon_condition_route` |
| POST | `/v1/electional/western/sahl-matter-profile` | `sahl_matter_profile_route` |
| POST | `/v1/electional/western/classical-perfection` | `lilly_perfection_route` |
| POST | `/v1/electional/western/dorotheus-moon-condition` | `dorotheus_moon_condition_route` |
| POST | `/v1/electional/western/dorotheus-rooted-context` | `dorotheus_rooted_context_route` |
| POST | `/v1/electional/western/dorotheus-construction` | `dorotheus_construction_route` |
| POST | `/v1/electional/western/dorotheus-matter-profile` | `dorotheus_matter_profile_route` |
| POST | `/v1/electional/western/profile-windows` | `western_profile_windows_route` |
| GET | `/v1/locations/search` | `location_search_route` |
| POST | `/v1/locations/timezone/validate` | `timezone_validate_route` |
| GET | `/v1/website/chart-wheel/presets` | `chart_wheel_presets_route` |
| POST | `/v1/website/chart-wheel/validate` | `chart_wheel_validate_route` |
| POST | `/v1/website/chart-wheel/packet` | `chart_wheel_packet_route` |

### Fixed-Star REST Admission Boundary

The admitted fixed-star REST surface is the bounded synchronous
`/v1/stars/position`, `/v1/stars/bulk`, and `/v1/stars/list` family.

`/v1/stars/position` and `/v1/stars/bulk` return fixed-star longitude,
latitude, magnitude, zodiac sign fields, and an explicit `provenance` object
derived from the live `FixedStar` vessel truth/classification/relation fields.
The provenance records the requested datetime, normalized UTC datetime, TT
Julian Day, lookup/source/merge state, observer mode, relation basis, condition
state, and transport stage sequence.

This admission does not expose heliacal event search, star condition networks,
catalog-wide heavy sweeps, or rendered star maps. Explicit selected fixed-star
Astrocartography is admitted under `/v1/astrocartography/chart/subjects/*`;
catalog-wide fixed-star Astrocartography sweeps remain deferred.

### Variable-Star REST Admission Boundary

The admitted variable-star REST surface is the bounded synchronous
`/v1/stars/variable/*` family:

- `GET /v1/stars/variable/list`
- `GET /v1/stars/variable/{name}`
- `POST /v1/stars/variable/state`
- `POST /v1/stars/variable/range`
- `POST /v1/stars/variable/catalog-profile`
- `POST /v1/stars/variable/pair`

Catalog responses include catalog-source provenance over the curated Variable
Star Oracle. State, range, catalog-profile, and pair responses include
computation provenance recording the Julian Day or datetime context, requested
and returned stars, eclipse-threshold policy, phase convention, catalog sources,
and stage sequence.

This admission does not expose real-time AAVSO/VSX observation refresh,
exhaustive GCVS catalog search, rendered light curves, variable-star positional
overlays, secondary-eclipse dedicated products, or multi-period semi-regular
models beyond the current dominant-period engine.

### Multiple-Star REST Admission Boundary

The admitted multiple-star REST surface is the bounded synchronous
`/v1/stars/multiple/*` family:

- `GET /v1/stars/multiple/list`
- `GET /v1/stars/multiple/{name}`
- `POST /v1/stars/multiple/state`

Catalog and state responses include provenance derived from the Multiple Star
Systems Oracle: catalog sources, system type, orbit model, orbital doctrine,
Dawes-limit aperture policy, combined-magnitude doctrine, primary-orbit label,
period uncertainty, requested aperture, computed Dawes limit, and stage
sequence.

This admission does not expose catalog-wide state sweeps, rendered orbit
diagrams, multi-aperture observing plans, arbitrary seeing policies, new catalog
ingestion, or exhaustive WDS/INT4 exposure.

### Asteroid REST Admission Boundary

The admitted asteroid REST surface is the bounded synchronous
`/v1/asteroids/*` family:

- `POST /v1/asteroids/position`
- `POST /v1/asteroids/bulk`
- `GET /v1/asteroids/list`

Position and bulk responses include geocentric tropical ecliptic longitude,
latitude, distance, speed, retrograde state, zodiac sign fields, and explicit
provenance. The provenance records the requested datetime, normalized UTC
datetime, UT Julian Day, requested and returned asteroid identity, returned
NAIF ID, kernel source, known-catalog truth, loaded-kernel availability, NAIF
convention, frame, and transport stage sequence.

The route family distinguishes a known asteroid identity in `ASTEROID_NAIF`
from a body actually covered by the loaded small-body reader. `is_sovereign` is
only asserted when the returned NAIF ID is present in `reader.covered_bodies()`;
reader presence alone is not treated as asteroid coverage.

This admission does not expose asteroid families, centaur/TNO/main-belt subset
routes, catalog-wide asteroid sweeps, topocentric positions, equatorial
positions, asteroid photometry, rendered maps, kernel manifest management, or
full small-body migration proof. Explicit selected-asteroid Astrocartography is
admitted under `/v1/astrocartography/chart/subjects/*`; catalog-wide asteroid
Astrocartography sweeps remain deferred.

### Asteroid Subset And Family REST Admission Boundary

The admitted asteroid subset and family REST surface is the bounded synchronous
P11-06 extension under `/v1/asteroids/*`:

- `GET /v1/asteroids/subsets`
- `GET /v1/asteroids/subsets/{subset}/list`
- `POST /v1/asteroids/subsets/{subset}/positions`
- `GET /v1/asteroids/families/by-number/{number}`
- `GET /v1/asteroids/families/{family_name}/members`
- `POST /v1/asteroids/families/chart`
- `POST /v1/asteroids/families/chart/resonance-network`

Subset routes expose curated Moira identity sets: `classical`, `main_belt`,
`centaurs`, and `tnos`. Subset list responses include body names, NAIF IDs,
loaded-kernel availability by returned NAIF ID, subset source module, catalog
source, query/limit truth, and stage sequence. Subset position responses
delegate to the admitted asteroid position transport and add subset provenance.

Family routes expose Nesvorny/PDS dynamical-family catalog membership. Lookup,
member, and chart-grouping views use MPC catalog numbers and Nesvorny family
names, not NAIF IDs. Responses record
`NASA_PDS_ast_nesvorny_families_v2_2015`, `MPC_catalog_number`,
`moira.asteroid_families`, and transport stage sequence.

The chart resonance-network route accepts either `numbers` as MPC catalog
numbers or `bodies` as asteroid names / small-body NAIF IDs. It computes only
the explicitly requested chart bodies, detects admitted ecliptic aspects,
filters them through `find_resonant_aspects()`, groups them with
`resonance_network()`, and returns resolved nodes, resonant edges, per-family
network buckets, missing requested identities, and aspect policy provenance.

This admission preserves catalog labels exactly. Similar family labels such as
`Koronis`, `Koronis(2)`, and `Karin` remain distinct.

This admission does not expose family-wide position sweeps, rendered family
maps, asteroid-family astrocartography, arbitrary family catalog search,
photometry, topocentric/equatorial subset products, kernel manifest management,
or edits to the bundled family catalog.

### Comet REST Admission Boundary

The admitted comet REST surface is the bounded synchronous `/v1/comets/*`
family:

- `POST /v1/comets/position`
- `POST /v1/comets/bulk`
- `GET /v1/comets/list`

Position and bulk responses include geocentric tropical ecliptic longitude,
latitude, distance, speed, retrograde state, zodiac sign fields, and explicit
provenance. The provenance records the requested datetime, normalized UTC
datetime, UT Julian Day, requested comet identity, resolved engine comet name,
returned comet identity, returned NAIF ID, kernel source, known-catalog truth,
loaded-kernel availability, periodic-comet NAIF convention, frame, and
transport stage sequence.

The route family distinguishes a known comet identity in `COMET_NAIF` from a
body actually covered by the loaded small-body reader. REST requests may use
known comet names or known comet NAIF IDs; numeric IDs are resolved to the
engine comet name before `comet_at(...)` is called. `is_sovereign` is only
asserted when the returned NAIF ID is present in `reader.covered_bodies()`;
reader presence alone is not treated as comet coverage.

This admission does not expose non-periodic comet expansion, comet family or
dynamical-class routes, catalog-wide comet sweeps, topocentric positions,
equatorial positions, comet photometry, rendered maps, kernel manifest
management, or full small-body migration proof. Explicit selected-comet
Astrocartography is admitted under `/v1/astrocartography/chart/subjects/*`;
catalog-wide comet Astrocartography sweeps remain deferred.

### Manazil REST Admission Boundary

The admitted Arabic lunar mansion REST surface is the bounded synchronous
`/v1/manazil/*` family:

- `GET /v1/manazil/catalog`
- `POST /v1/manazil/position`
- `POST /v1/manazil/bulk`
- `GET /v1/manazil/traditions/{tradition}/mansions/{mansion_index}`

Catalog responses expose the 28 equal Arabic lunar mansions, the `360 / 28`
span, and admitted traditions. Position responses accept direct ecliptic
longitude and explicit `tropical` or `sidereal` mode. Sidereal mode requires
`jd_ut` and records ayanamsa system/mode in provenance. Bulk responses accept 1
to 500 named longitudes. Tradition lookup responses expose the selected
nature/signification for one mansion in one admitted tradition.

The route family preserves Arabic Manazil doctrine separately from Vedic
nakshatra doctrine. Variant traditions alter textual attribution only; they do
not alter the 28 equal mansion boundaries.

This admission does not expose chart-backed Moon mansion routes, natal mansion
profiles, electional scoring, mansion condition networks, heliacal/fixed-star
mansion variants, Vedic nakshatra routes, or alternate non-equal mansion
boundary systems.

### Planetary And Small-Body Nodes REST Admission Boundary

The admitted node REST surface is the bounded synchronous `/v1/nodes/*`
family:

- `GET /v1/nodes/catalog`
- `POST /v1/nodes/planetary/mean`
- `POST /v1/nodes/planetary/mean/bulk`
- `POST /v1/nodes/geometric`

Mean planetary routes expose kernel-free Meeus / Simon mean orbital element
nodes and apsides for Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and
Neptune. Responses include ascending node, descending node, perihelion,
aphelion, inclination, eccentricity, semi-major axis, method, JD scale, frame,
kernel requirement, source module, validity note, and stage sequence.

The geometric route exposes a single reader-backed osculating heliocentric node
and apsides record using angular-momentum and eccentricity-vector geometry from
the active reader state vectors. It records the active-reader dependency in
provenance and does not imply small-body availability from catalog identity.

This admission does not expose lunar true/mean node REST routes, chart-backed
node profiles, nodal aspect networks, catalog-wide small-body node sweeps,
rendered node maps, asteroid/comet route changes, or small-body kernel manifest
management.

### Orbital Elements REST Admission Boundary

The admitted P-GAP-03 orbital REST surface is the bounded synchronous
`/v1/orbits/*` family:

- `POST /v1/orbits/elements`
- `POST /v1/orbits/distance-extremes`

`/v1/orbits/elements` exposes one epoch's heliocentric J2000 ecliptic/equinox
osculating Keplerian elements for an admitted major body. Responses include
semi-major axis, eccentricity, inclination, longitude of ascending node,
argument of perihelion, mean anomaly, mean motion, orbital period, and the
derived perihelion/aphelion distances of the osculating ellipse.

`/v1/orbits/distance-extremes` exposes the next heliocentric perihelion and
aphelion events after `jd_ut` on the live heliocentric distance curve. The
response records that the events are semantic extrema, not a forced
chronological pair and not merely algebra from one epoch's osculating ellipse.

Both routes accept one admitted body and one finite `jd_ut`. The response
provenance records `moira.orbits`, the engine entrypoint, Sun center, J2000
ecliptic/equinox frame, osculating element type, DE-series state source, no
apparent correction, no light-time correction, and no mean-element table.

This admission does not expose mean element tables, geocentric lunar elements,
comet elements, asteroid elements, Uranian mean elements, visual-binary
Campbell elements, arbitrary centers/reference planes, apparent or
light-time-corrected element products, dense ephemeris tables, or kernel path
mutation.

### Generic Phenomena And Solar Conditions REST Admission Boundary

The admitted P-GAP-04 REST surface is the bounded synchronous generic
phenomena and solar-condition surface:

- `POST /v1/phenomena/planet`
- `POST /v1/phenomena/orbital-events`
- `POST /v1/phenomena/proximity`
- `POST /v1/solar-condition/instant`
- `POST /v1/solar-condition/events`

`/v1/phenomena/planet` exposes one instant's physical/photometric state for
an admitted body: phase angle, illuminated fraction, elongation, angular
diameter, and apparent magnitude.

`/v1/phenomena/orbital-events` exposes a bounded event search over admitted
event kinds: greatest eastern/western elongation for Mercury and Venus, and
perihelion/aphelion for admitted major bodies. Event responses label both the
event kind and the value unit.

`/v1/phenomena/proximity` exposes angular threshold ingress/egress crossings
for an admitted body pair. The response preserves the caller threshold,
signed event threshold, event direction, longitudes, latitude, retrograde
state, and event label.

`/v1/solar-condition/instant` exposes classical solar-condition truth at one
instant. Sun and Moon inputs are accepted and return absent truth, matching
engine behavior. `/v1/solar-condition/events` exposes bounded cazimi,
combust, and under-sunbeams threshold crossings for admitted non-luminary
major bodies.

This admission does not expose a catch-all `/v1/events` route, arbitrary
phenomenon predicates, aspect searches, station/lunar-phase/rise-set/
heliacal/eclipse/occultation replacements, dense event tables, small-body
proximity sweeps, interpretation text, recommendations, or kernel path
mutation.

### Uranian REST Admission Boundary

The admitted Uranian / Hamburg School REST surface is the bounded synchronous
P12-01 `/v1/uranian/*` family:

- `GET /v1/uranian/catalog`
- `POST /v1/uranian/position`
- `POST /v1/uranian/bulk`

Catalog responses expose the current nine-name table from `moira.uranian`,
including `Transpluto`. Position and bulk responses expose tropical ecliptic
longitude, sign fields, constant mean daily speed, `body_kind` value
`hypothetical_body`, and provenance identifying the source module, engine
entrypoint, Hamburg/Uranian school, linear mean-motion table model, J2000
epoch, tropical frame, no physical ephemeris, and no SPK kernel usage.

This admission does not expose Uranian midpoint trees, dial products,
cosmobiology networks, chart interpretation, physical body substitution,
kernel-backed Transpluto/TNO computation, or any claim that these hypothetical
mean points are JPL/NAIF physical-body states.

### Harmonics REST Admission Boundary

The admitted Harmonics REST surface is the bounded P12-02
`/v1/harmonics/*` family:

- `GET /v1/harmonics/presets`
- `POST /v1/harmonics/chart`
- `POST /v1/harmonics/age-chart`
- `POST /v1/harmonics/conjunctions`
- `POST /v1/harmonics/pattern-score`
- `POST /v1/harmonics/aspects`
- `POST /v1/harmonics/sweep`
- `POST /v1/harmonics/fingerprint`
- `POST /v1/harmonics/composite`
- `POST /v1/harmonics/transit-forecast`

These routes accept caller-supplied named ecliptic longitude maps. Longitude
scalars and orb values must be JSON numbers; booleans and numeric strings are
rejected rather than coerced. They do not
construct charts, derive ephemeris positions, use houses, apply ayanamsa, or
generate transit samples. Direct chart, conjunction, pattern-score, and
composite requests admit positive finite real `harmonic` values in the REST
range `1..128`; `5.5` remains `5.5` and is not truncated to `5`. Integer values
are ordinary cyclic harmonics. Non-integer values are explicit
zero-Aries-anchored continuous multipliers computed from each input's canonical
`[0, 360)` representative. Responses preserve the requested/effective value,
input count, sorted positions, integer-preset metadata when known, and
provenance identifying `moira.harmonics`, the engine entrypoint, caller-owned
longitudes, and `(normalized_longitude * harmonic) mod 360`.

Age-harmonic responses preserve the derived decimal harmonic, `jd_birth`,
`jd_now`, and the basis `(jd_now - jd_birth) / tropical_year`. Age harmonic is
not the transport adapter for an arbitrary fractional harmonic request.

Pattern-analysis routes expose one-harmonic conjunctions, one-harmonic pattern
scores, harmonic aspect decoding, bounded sweeps, bounded vibrational
fingerprints, and bounded composite harmonic comparison. Sweep and fingerprint
provenance explicitly labels scores as pattern-density measures rather than
interpretive judgments. Aspects, sweeps, and fingerprints retain integer
harmonic ranges.

Conjunction-bearing requests retain the compatibility `orb` field as the
configurable H1-reference and projected-chart threshold. Optional
`orb_policy={"scaling_mode":"addey_inverse_harmonic"}` makes the admitted
policy selection explicit. Provenance reports the projected limit `O_1`, its
locally equivalent source-circle allowance `O_1/H`, authority, formula,
adapter mode, and the continuous-extension flag. Clients must not divide the
projected threshold by H again.

`POST /v1/harmonics/transit-forecast` evaluates only caller-supplied,
strictly time-ordered samples at explicitly requested integer harmonics. It
admits complete triples in either `one_transit_two_natal` or
`two_transits_one_natal` mode when all three projected positions fit within one
minimum circular covering arc no wider than the resolved projected orb. It
returns consecutive *observed windows* whose first, peak, and last times are
supplied sample witnesses. It performs no interpolation and makes no exact
ingress, perfection, egress, or Sirius-parity claim. Forecast transport is
bounded to 12 bodies per origin, 512 samples, 16 requested harmonics, and
25,000 candidate evaluations. Timestamp sequences must also have finite
adjacent gaps and a finite total span.

This admission does not expose unbounded harmonic sweeps, automatic chart
construction, ephemeris sampling, fractional-H forecasting, progression
harmonic search, interpolated or exact transit-event solving,
harmogram/spectral-analysis products, chart rendering, or interpretive
narrative text.

### Harmograms REST Admission Boundary

The admitted P-GAP-06 Harmograms REST surface is the bounded
`/v1/harmograms/*` family:

- `POST /v1/harmograms/vector`
- `POST /v1/harmograms/zero-aries-vector`
- `POST /v1/harmograms/intensity-spectrum`
- `POST /v1/harmograms/projection`
- `POST /v1/harmograms/trace`

These routes accept caller-supplied named ecliptic longitudes and
caller-supplied explicit trace samples. They expose `moira.harmograms`
point-set vectors, Zero-Aries-parts vectors, intensity spectra, projections,
and trace series without constructing charts or generating ephemeris samples.

The transport boundary is deliberately bounded: position counts, harmonic
domain width, intensity sample count, trace sample count, and trace cell count
are all capped by `moira_server.models.harmograms`. Trace responses preserve
series intensity spectra, source vectors, projection terms, and strengths, but
do not add judgement language.

This admission does not expose chart-backed harmogram generation, dynamic
ephemeris sampling, arbitrary intensity functions, unbounded sweeps, dense
rendering meshes, async jobs, harmonic interpretation, recommendation text, or
replacement of `/v1/harmonics/*`.

### Phase And Photometry REST Admission Boundary

The admitted Phase / Elongation / Magnitude REST surface is the bounded P12-03
`/v1/phase/*` family:

- `POST /v1/phase/illuminated-fraction`
- `POST /v1/phase/synodic`
- `POST /v1/phase/elongation`
- `POST /v1/phase/angle`
- `POST /v1/phase/angular-diameter`
- `POST /v1/phase/apparent-magnitude`

`/v1/phase/illuminated-fraction` is pure scalar mathematics over a supplied
phase angle and does not require a kernel. Synodic phase, elongation,
phase-angle, angular-diameter, and apparent-magnitude routes are direct
one-epoch products over engine-supported bodies and preserve product-specific
basis and kernel requirement truth in provenance.

Angular diameter is admitted only for the engine radius-table support set:
Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto.
Apparent V magnitude is admitted only for Moon, Mercury, Venus, Mars, Jupiter,
Saturn, Uranus, Neptune, with model-family provenance for Schaefer 1993 lunar
phase law or Mallama/Hilton 2018 planetary magnitude models. Sun, Pluto,
dwarf planets, asteroids, comets, fixed stars, and variable stars remain
excluded from this apparent-magnitude route.

This admission does not expose topocentric phase or magnitude, atmospheric
extinction, visual limiting magnitude, visibility scoring, heliacal
visibility, eclipse darkening, moon-phase or conjunction event searches,
minor-body photometry, fixed-star or variable-star photometry, interpretive
astrological phase text, or sky rendering.

### Antiscia REST Admission Boundary

The admitted ordinary Antiscia REST surface is the bounded P12-04
`/v1/antiscia/*` family:

- `POST /v1/antiscia/reflect`
- `POST /v1/antiscia/contacts`
- `POST /v1/antiscia/to-point`

`/v1/antiscia/reflect` computes direct antiscion and/or contra-antiscion
reflections of a caller-supplied finite longitude. Contact routes accept
caller-supplied named longitude maps only; they do not construct charts,
derive ephemeris positions, use houses, or compute chart motion.

Responses preserve the engine labels `Antiscion` and `Contra-Antiscion`,
the `body1` body whose reflected point forms a contact, the reflected
`shadow`, explicit `orb`, and increasing-orb ordering. Provenance records
`moira.antiscia`, `ordinary_antiscia`, the two reflection formulae,
`not_primary_direction_antiscia`, no chart motion, and no ephemeris use.

This admission does not expose primary-direction antiscia, directed arcs,
transits, progressions, chart construction, house derivation, antiscia
networks, scoring profiles, or interpretive narrative text.

### Draconic REST Admission Boundary

The admitted draconic REST surface is the bounded `/v1/draconic/*` family:

- `POST /v1/draconic/longitude`
- `POST /v1/draconic/positions`
- `POST /v1/draconic/chart`

`/v1/draconic/longitude` rotates one caller-supplied finite longitude by a
caller-supplied anchor longitude under the fixed doctrine formula
`normalize_degrees(source_longitude - anchor_longitude)`. It claims no node
policy and uses no ephemeris.

`/v1/draconic/positions` materializes a full draconic chart vessel from a
caller-supplied named longitude map, an explicit `node_mode` (`mean` or
`true`), and a caller-supplied anchor longitude. The caller owns the anchor
truth; the route does not construct charts or derive node positions.

`/v1/draconic/chart` builds an engine tropical chart for a timezone-aware
datetime (with optional bodies and topocentric observer), extracts the
North Node selected by `node_mode` as the anchor, and rotates all chart
longitudes into the draconic frame. The source chart is always built
node-bearing so the anchor exists; the request `include_nodes` flag governs
only whether node points appear among the transformed output positions.

Responses preserve the engine vessel truth: the anchor block (`node_mode`,
`node_name`, `longitude`, `rotation_degrees`, `source`, `source_zodiac`,
`formula`), per-body source and draconic longitudes with sign decomposition,
`frame` (`draconic`), `source_zodiac` (`tropical`), `interpretation_scope`
(`longitude_frame_transform_only`), and `anchor_residual` (distance of the
included anchor node from 0 Aries, `null` when the node is not among the
output positions). Provenance records `moira.draconic`, the engine
entrypoint, the rotation doctrine and formula, anchor ownership, chart
construction ownership, and ephemeris use.

This admission does not expose draconic houses, draconic-to-tropical
synastry or contact searches, sidereal source zodiacs, South Node or
arbitrary-point anchors, node event searches, or interpretive narrative
text.

### Nine Parts REST Admission Boundary

The admitted Abu Ma'shar Nine Parts REST surface is the bounded P12-05
`/v1/nine-parts/*` family:

- `POST /v1/nine-parts/abu-mashar`

This route accepts a caller-supplied Ascendant longitude, required planetary
longitudes, and caller-supplied `is_night_chart` truth. It does not construct a
chart, derive the Ascendant, determine sect, compute houses, or infer night
status.

The response preserves the complete `NinePartsAggregate` shape: nine parts in
canonical Abu Ma'shar order, computation truth for each part, dependency
relations, condition profiles, aggregate summaries, effective policy, validation
results from `validate_nine_parts_output`, and provenance. Sword and Node
remain `admitted_extension` records with `planet_association: null`; they are
not collapsed into ordinary planetary lots.

Only the `full_reversal` reversal rule and
`evidenced_core_plus_admitted_extension` historical scope are admitted. This
admission does not expose solar-return integration, Al-Sijzi Transfer of
Management, longevity integration, comparison bundles against `moira.lots`,
Hellenistic nonomoiria, Vedic Navamsha or D9 routes, or interpretive narrative
text.

### Planetary Hours REST Admission Boundary

The admitted Planetary Hours REST surface is the bounded P12-06
`/v1/planetary-hours/*` family:

- `POST /v1/planetary-hours/schedule`
- `POST /v1/planetary-hours/hour-at`

These routes accept a caller-supplied Julian Day UT and numeric geographic
latitude/longitude. They do not perform timezone lookup, location-name lookup,
geocoding, chart construction, or civil-day calendar expansion.

Responses preserve the dedicated `moira.planetary_hours.PlanetaryHour` vessel
fields: `hour_number`, `ruler`, `jd_start`, `jd_end`, and `is_daytime`.
Provenance explicitly distinguishes this vessel from
`moira.cycles.PlanetaryHour`, records the Chaldean-order and weekday-rulership
basis, records reader policy, and states that ISO timestamps, when included,
are UTC output only.

The route family surfaces sunrise/sunset resolution failure as a visible
validation error. It does not invent sunrise or sunset values, does not use a
fixed six-to-six fallback, and does not replace the sunrise-based doctrine with
civil-clock approximation.

This admission does not expose `moira.cycles` planetary-day profiles,
electional scoring, recommendation text, annual time-lord techniques, Lord of
the Orb calculation, or automatic birth planetary-hour derivation for other
lordship systems.

### Huber REST Admission Boundary

The admitted Huber REST surface is the direct-cusp P12-07 `/v1/huber/*`
family:

- `POST /v1/huber/dynamic-intensity`
- `POST /v1/huber/house-zones`
- `POST /v1/huber/age-point`
- `POST /v1/huber/intensity-at`
- `POST /v1/huber/chart-intensity-profile`
- `POST /v1/huber/age-point-contacts`

These routes expose `moira.huber` computations over caller-supplied house
frames. The Huber transport layer does not calculate houses, construct charts,
derive locations, derive timezones, or substitute house systems. Direct house
frames require exactly 12 finite cusp longitudes plus caller-supplied
Ascendant, MC, and ARMC anchors required to construct Moira's `HouseCusps`
vessel.

Responses record `house_frame_source: caller_supplied`,
`cusp_derivation_owner: caller_supplied`, requested/effective house-system
truth, fallback truth, whether the effective frame is Koch, and the Huber
doctrine preference for Koch houses. Non-Koch direct frames are accepted as
computational inputs but are reported as not doctrinally complete Huber house
fidelity.

The route family preserves the Dynamic Intensity Curve basis as
`piecewise_half_cosine_reconstruction` and keeps the limitation that the
primary-text exact formula has not been independently verified. Age Point
contact scans are bounded by maximum point count, maximum age span, minimum
step size, and maximum orb.

This admission does not expose chart-backed Huber house derivation,
independent house calculation inside Huber transport, psychological
interpretation text, counseling, health or clinical claims, chart rendering,
unbounded Age Point searches, transit/progression timing outside Age Point
mechanics, or generic `/v1/special/*` computation.

### Lord Of The Orb REST Admission Boundary

The admitted Lord of the Orb REST surface is the bounded P12-10
`/v1/lord-of-the-orb/*` family:

- `POST /v1/lord-of-the-orb/sequence`
- `POST /v1/lord-of-the-orb/current`

These routes expose `moira.lord_of_the_orb` over a caller-supplied
`birth_planet`, understood as the ruler of the birth planetary hour. The
transport layer does not calculate planetary hours, does not construct charts,
does not derive the birth-hour ruler, and does not orchestrate Abu Ma'shar's
full annual hierarchy.

Sequence responses preserve ordered period records, condition profiles,
aggregate benefic/malefic and planet-count summaries, effective cycle policy,
validation output, and provenance. Current-period responses map completed age
to year of life (`age 0` is year 1) and return the active period plus its
condition profile.

The admitted cycle variants are `continuous_loop` and `single_cycle`. Sequence
requests are bounded to at most 252 years, and current-period requests are
bounded to ages 0 through 251. Provenance records the caller-supplied birth
planet source, the fact that planetary-hour derivation is not owned by this
route, Chaldean-order cycle basis, twelve-house modular cycle basis, hierarchy
rank 6, and the distinction from `moira.lord_of_the_turn`.

This admission does not expose birth planetary-hour derivation, chart
construction, annual hierarchy orchestration, profections or firdaria
integration, natal or solar-return dignity scoring, comparison bundles,
interpretive narrative text, or generic `/v1/special/*` computation.

### Lord Of The Turn REST Admission Boundary

The admitted Lord of the Turn REST surface is the bounded P12-11
`/v1/lord-of-the-turn/*` family:

- `POST /v1/lord-of-the-turn/profile`

This route exposes `moira.lord_of_the_turn.lord_of_turn` over caller-supplied
Solar Return chart data. It accepts natal Ascendant longitude, completed age,
method policy, combust-orb policy, and an SR chart vessel containing SR
Ascendant, classical planet longitudes, optional house placements,
caller-supplied sect flag, optional retrograde planet list, and optional SR Lot
of Fortune longitude.

Responses preserve the integrated condition profile, selected result,
profection truth, candidate assessments, method policy, validation output, and
provenance. Candidate assessments expose candidate role, SR house, combustion
state, retrograde state, blocker reasons, witnessing truth, and binary
testimony count. Provenance explicitly records that Solar Return construction,
house calculation, ephemeris derivation, automatic sect calculation, and annual
hierarchy orchestration are not owned by this route.

The admitted method variants are `al_qabisi` and `egyptian_al_sijzi`.
Transport provenance preserves Al-Qabisi sequential succession as
`sequential_succession_no_simultaneous_tiebreak` and Egyptian/Al-Sijzi
testimony as `binary_dignity_type_count_not_weighted_almuten`. When house
placements are omitted, the response exposes the engine's `DOMICILE_ONLY`
mode rather than implying a full SR condition assessment.

This admission does not expose Solar Return chart construction, house
calculation, ephemeris derivation, automatic sect calculation, automatic SR
Lot of Fortune calculation, annual hierarchy orchestration, combined annual
timing dashboards, interpretive narrative text, or generic `/v1/special/*`
computation.

### Electional REST Admission Boundary

The admitted Phase 13 electional REST surface has two deliberately separate
products: the bounded generic search subset and one source-owned Western
single-moment profile.

The bounded generic search subset is:

- `GET /v1/electional/predicate-profiles`
- `GET /v1/electional/scorer-profiles`
- `POST /v1/electional/windows`
- `POST /v1/electional/moments`
- `POST /v1/electional/scored`

`/v1/electional/predicate-profiles` exposes the server-defined predicate
catalogue admitted for REST use. `/v1/electional/windows` calls
`moira.electional.find_electional_windows` through that catalogue and returns
merged scan-witness windows over discrete chart snapshots.
`/v1/electional/moments` calls `moira.electional.find_electional_moments`
through the same catalogue and returns raw qualifying scan-point JDs.
`/v1/electional/scorer-profiles` exposes the server-defined numeric scorer
catalogue admitted for REST use. `/v1/electional/scored` calls
`moira.electional.find_scored_windows` through the admitted predicate and
scorer catalogues and returns scored merged windows.

The admitted predicate profiles are:

- `body_longitude_range_v1`
- `body_house_membership_v1`
- `body_angular_separation_range_v1`

The admitted scorer profiles are:

- `body_longitude_target_closeness_v1`
- `body_angular_separation_target_closeness_v1`

Responses preserve predicate, policy, scan, validation, bounds, and provenance
truth. Window responses preserve merged scan-witness windows. Moment responses
preserve raw qualifying scan points. Scored responses preserve the declared
scorer profile, finite `[0.0, 1.0]` numeric-fit scores, returned-window
`score_rank`, and `peak_jd` as the highest-scored qualifying scan point inside
the returned window. Provenance states that these are discrete sampled chart
states; these routes do not claim continuous truth, exact event-boundary
solving, or exact score-peak solving.

The generic-search REST bounds are intentionally narrow: maximum 31-day search span,
15-minute minimum cadence, maximum 1000 computed scan points, maximum 64
returned windows, maximum 1000 returned raw moments, maximum 12 requested
bodies, and at most 8 optional boundary refinement steps for the window route.
Boundary refinement, when requested for windows, is bracket evidence, not exact
root truth. The raw-moment route requires `boundary_refine_steps` to be `0`
and disables window-count early exit so raw scan points are not truncated by
the window grouping helper.
For scored windows, `max_windows` remains chronological early exit; score
ranks are over the returned windows only and are not a global optimum claim.

The separately admitted Western doctrine routes are:

- `POST /v1/electional/western/lunar-ecliptic-direction`
- `POST /v1/electional/western/ramesey-moon-condition`
- `POST /v1/electional/western/sahl-moon-condition`
- `POST /v1/electional/western/sahl-matter-profile`
- `POST /v1/electional/western/classical-perfection`
- `POST /v1/electional/western/dorotheus-moon-condition`
- `POST /v1/electional/western/dorotheus-rooted-context`
- `POST /v1/electional/western/dorotheus-construction`
- `POST /v1/electional/western/dorotheus-matter-profile`
- `POST /v1/electional/western/profile-windows`

The classical-perfection route is a bounded, kernel-backed event analysis
under the fixed `lilly_1647_perfection_v1` profile. Requests select two
distinct traditional planets, a strict day/night boolean, and an increasing
UT1 Julian-day interval no longer than 31 days. The profile id is an exact
literal; arbitrary bodies, generic lineage names, scoring fields, and advice
fields are rejected.

The response preserves initial longitudes and speeds for all seven traditional
planets, a deterministic chronological trace of exact Ptolemaic aspects,
stations, and sign ingresses, and separate witnesses for direct perfection,
translation, collection, prohibition, refranation, and frustration. Each
witness exposes its actors, supporting event ids, reception bases, source page,
and `present`, `absent`, or `indeterminate` state. Transport provenance names
`lilly_perfection_at`, `Moira.lilly_perfection_at`, and the exclusions of Sahl,
Bonatti, and reflection. The response always declares that it supplies no
score, advice, or complete electional judgement. Its policy vessel also names
UT1 input/internal TT conversion, apparent geocentric true-ecliptic-of-date
longitude, astrometric geocentric longitude rate, canonical Lilly moieties,
Egyptian bounds, and sect-active Dorothean triplicity.

The lunar-ecliptic-direction route is a neutral astronomical product rather
than a historical doctrine verdict. It accepts one finite `jd_ut` and returns
the Moon's apparent geocentric ecliptic latitude and latitude rate, independent
hemisphere and motion classifications, previous/next/nearest exact
sign-changing node crossings, their UT1 times and directions, numerical policy,
frame, timescale, and an explicit no-doctrinal-region scope.

The single-moment routes accept one finite `jd_ut`, latitude, longitude, an
explicit known house-system code, the fixed profile id for the selected route,
and an optional strict boolean `unavoidable_time_urgency` context where the
selected profile admits it. They delegate through the corresponding `Moira`
facade method and return typed source-ordered evaluations: clause and
measurement witnesses, triggered and
not-evaluable rule identities, the separate non-erasing remedy witness,
requested/effective house-system truth, fallback status, reader provenance, and
the profile's non-complete-judgement language.

The Sahl matter route requires one exact admitted profile id from the
source-specific building, land, planting, sowing, lending, investment,
purchase, sale, or business-partnership families. This includes the independent
`sahl_business_partnership_v1` profile for §§32–35; it is not a Dorothean
partnership alias. The route also requires the explicit Sahl burnt-path variant
used by its nested general Moon layer. The response contains that complete Moon
layer plus every matter clause, role, state, measurement, policy id, citation,
triggered gate, unresolved clause, and numerical-completeness flag. It provides
no score, ranking, advice, recommendation, or generic house-topic judgement.

The Ramesey remedy witness exposes urgent applicability and tri-state
fulfillment separately. Its typed clauses preserve Moon cadence/Ascendant
relation, Jupiter/Venus placement or good aspect, Ascendant-cusp
fortification, Ascendant-lord fortification, and planetary-hour-lord
fortification. Unresolved fortification predicates remain `indeterminate` and
never clear a triggered impediment.

The construction response carries all inherited V.2-V.6 and V.31 layers plus
the six V.7 clauses. Its increasing-in-calculation witness exposes the true and
IERS 2010 mean lunar longitudes, signed equation, and added/subtracted direction.
Its nested rooted context exposes evaluated V.31 bad-place booleans for
whole-sign places 3, 6, 8, and 12, plus source-ordered under-rays,
made-unfortunate, Ascendant-relation, and bad-place testimonies. The rooted
context also exposes distinct V.6.29 ninth-part, Lot-of-Fortune-lord, and next
connection indicators; they are not interchangeable outcome-ruler choices.
The ecliptic-crossing clause remains
`not_evaluable` because the primary text supplies no crossing region or
tolerance. The profile-window route is a bounded discrete scan of explicitly
selected statuses, not an exact-transition solver.

The matter-profile route admits the named Dorothean Book V ids from V.8–V.11,
V.20–V.22, V.24–V.26, V.43, and V.44: this includes
`dorotheus_ship_construction_v1`, `dorotheus_ship_launch_v1`,
`dorotheus_land_travel_v1`, `dorotheus_sea_travel_v1`,
`dorotheus_partnership_v1`, `dorotheus_debt_and_payment_v1`, and
`dorotheus_writing_a_will_v1` in addition to the earlier profiles. It exposes
source-ordered clauses, named whole-sign angular topics, applicable
planetary-strength witnesses, inherited Moon conditions, and an explicit
policy vessel. Rooted context is present only where the cited source lawfully
supplies it: V.20 partnership and V.21 debt/payment retain their Mercurial
root, while V.22, V.24, V.25, V.26, and V.43 return `rooted_context: null`.
V.26 alone accepts a complete radical chart for its named Saturn overlay.
Land and sea travel requests require `sign_nature_variant`. The
`source_text_unresolved_no_dry_sign_table` choice keeps Dorotheus's
unenumerated dry-sign class explicit and indeterminate; the separately
attributed `lilly_1647_elemental_qualities` choice applies Lilly 1647's named
table. The sea water-sign gate remains Dorotheus-owned. Every remaining
source-open sign class, connection interval, compound predicate, and ambiguous
passage remains `not_evaluable`; no route returns a score or recommendation.

The Phase 8 judgement, Phase 9 ranking, and Phase 10 judgement-window routes
accept the same policy as `dorotheus_sign_nature_variant` for these two matter
profiles and return it in each judgement selection. It is required for land or
sea travel and rejected for every other matter profile, so no authority choice
is hidden or silently discarded.

Leasing additionally requires `moon_flow_policy`, selecting either the
current-sign or a bounded fixed-lookback previous-event interval, and the
response embeds the resulting `moon_connection_flow`. Leasing remains
`numerically_complete: false`: the event geometry is now complete, but V.9's
surviving text does not assign separation and connection to its four leasing
stakes. No profile produces a score or recommendation.

Each single-moment transport names its route semantics, engine and facade entry
points, and reports `scoring: not_provided`,
`generic_search_integration: not_admitted`,
`recommendation_language: not_provided`, and
`remedy_fulfillment_assessment: tri_state_non_erasing` for Ramesey. None of these
routes is a generic predicate adapter, and none ranks or recommends a time.

These admissions do not expose arbitrary executable predicates or scorers,
generic numeric Western scoring, additional lineage profiles,
auspicious/inauspicious labels, recommendation text, unbounded scans, async
search jobs, or electional advice language.

### Catalog Umbrella Boundary

There is no admitted `/v1/catalogs/*` route family.

The P11-U1 doctrine decision keeps a future catalog umbrella deferred and
restricts any later candidate to discovery-only registry metadata. It may point
clients to admitted family-native route prefixes and doctrine documents, but it
must not return catalog member records, perform cross-family search, compute
positions, expose loaded-kernel coverage lists, join catalog identities, or run
catalog-wide sweeps.

## Documentation Boundary

Use this document for HTTP route presence and family status.

Use `wiki/02_standards/API_REFERENCE.md` for Python import surfaces, engine
classes, engine functions, and canonical result vessels.

Use `docs/architecture/MOIRA_SERVER_BOUNDARY.md` for the governing rule that the
server transports truth and the engine computes truth.

Use `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md` before adding
or widening a route family.
