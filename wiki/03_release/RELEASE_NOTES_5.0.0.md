# Moira 5.0.0 — Astronomical Truth, Explicit Doctrine, and Public Proof

**Release date:** 2026-07-19
**Public upgrade path:** 4.2.1 to 5.0.0

Moira 5.0.0 is a major release because it changes more than the number of
available calculations. It tightens what public results mean, makes previously
implicit computational choices inspectable, rejects ambiguous inputs that were
formerly tolerated, and corrects several astronomical products at their
governing geometric or time-scale boundary.

The release adds first-class eclipse footprints, polar-safe occultation
topology, topography-conditioned lunar contact chronology, declination aspects,
real-valued harmonic charts, harmonic transit forecasts, a complete
primary-directions evaluation layer, and source-scoped Western electional
judgement. It also repairs Delta T composition, historical civil-time
conversion, planetary frame and speed semantics, eclipse classification and
contacts, planetary hours, house validation, relationship identity, and pattern
structure.

This is not a claim that every astronomical or astrological frontier is closed.
Where an authority publishes a different model, Moira names the comparison as
cross-model validation. Where only invariants or regression artifacts exist,
the release says so. Source-faithful astrological implementation is evidence of
doctrinal fidelity, not empirical proof of astrological efficacy.

## Release boundary and the unpublished 4.3.0 staging version

Version 4.3.0 existed in the repository as an internal staging version. It was
not tagged or published as a public package. Its Western electional work and
every subsequent change have therefore been folded into 5.0.0.

Consumers do not need to install or migrate through 4.3.0. For compatibility,
release-note, and semantic-versioning purposes, 5.0.0 is the direct public
successor to 4.2.1.

The major-version boundary is intentional. Most new routes and vessels are
additive, and existing facade and REST paths are broadly preserved, but several
published behaviors now fail closed or expose corrected semantics:

- relationship result vessels and their nested collections are immutable;
- `GET /ready` returns HTTP 503, rather than HTTP 200, when a worker is not
  ready;
- invalid or ambiguous scientific inputs that were formerly coerced are now
  rejected;
- the ambiguous `chaldean` bounds doctrine has been replaced by explicit day
  and night variants;
- corrected Delta T, eclipse, house, planetary-speed, and frame rules
  intentionally change affected numerical results.

## Highlights

- A coherent Delta T and civil-time contract now governs historical,
  contemporary, and scenario epochs without silently retargeting source data to
  the active ephemeris.
- Solar and lunar eclipse work now distinguishes native DE441 products,
  NASA-compatibility products, local circumstances, Besselian elements,
  central paths, and partial-visibility footprints.
- Lunar occultation paths now have intrinsic left/right topology that remains
  continuous through geographic poles, while a separate engine-only product
  models topography-conditioned stellar contacts from official LOLA relief.
- Primary directions now expose explicit method, space, motion, key, relation,
  target, condition, aggregate, and network doctrine through the engine,
  facade, and typed REST boundary.
- Harmonic calculations preserve every positive finite real harmonic, expose a
  provenance-bearing Addey orb policy, and add bounded mixed-origin harmonic
  transit forecasts.
- Declination parallels and contra-parallels are first-class aspects with
  explicit hemisphere, equator, admission, and applying/separating doctrine.
- Symmetric aspect-pattern detectors now preserve their structural roles, and
  callers may opt into cross-pattern dominance filtering.
- Western electional work now extends from source-owned Moon and matter
  profiles through inspectable complete judgement, caller-weighted candidate
  ranking, and bounded observed judgement windows.
- Runtime-dispatched AVX2 interpolation and reusable native SPK evaluators
  improve admitted hot paths without imposing AVX2 on every wheel or changing
  Python-owned doctrine.

## Astronomical foundation

### Delta T source, ephemeris, and future-policy integrity

Delta T is now composed at the layer that actually knows the ephemeris
identity.

The source-priority total remains on the HPIERS DE430/LE430 basis declared by
the data. Generic clock code no longer guesses a downstream ephemeris and
ambiently retargets that total. Reader-backed SPK calculations instead derive
a coherent DE/LE identity from kernel summary content:

- DE430/LE430 retains the source basis;
- DE441/LE441 receives the source-owned historical tidal correction;
- unmapped or conflicting historical bases fail closed;
- filenames are not accepted as kernel identity.

The physical model now includes an explicit continuous bridge from the earlier
polynomial at year -2100 to the first HPIERS row at year -2000, while -2000
remains the admitted physical-policy floor. General physical and hybrid
Julian-Day conversions use a continuous fraction-of-year coordinate. The
NASA-canon catalog path retains its declared month-midpoint policy instead of
silently sharing the general transform.

The HPIERS half-year cadence for 1950-2016 has been restored. Modern USNO
full-year and January-April aggregates are located at the mean epochs of their
contributing first-of-month samples rather than being represented as January 1
point values. Unknown duplicate conflicts fail closed; the two published
conflicts retain their explicit compatibility policy.

The final 2026 aggregate is identified as a provisional January-April mean.
Its post-handoff slope is a named scenario policy, not an observed
instantaneous derivative. Beyond 2150, values are explicitly scenario
extrapolations rather than validated forecasts. Historical C04, GRACE, AAM, and
OAM proxy artifacts are no longer presented as an admitted causal
decomposition: the compatible `core`, `cryo`, `fluid`, and `residual` fields
remain inspectable but are zero.

The computational domain is guarded at plus or minus 100,000 years and plus or
minus 40,000,000 Julian days. EOP edge corrections taper locally over one
Julian year instead of biasing remote epochs.

### Historical civil time and atomic UTC

Before 1972-01-01, timezone-normalized civil Julian days retain Moira's
established UT1-proxy interpretation. TT is derived from that same coordinate;
the former non-authoritative `TAI-UTC = 10 s` placeholder can no longer move an
ancient chart by minutes or hours.

A monotonic smoothstep over the final civil day joins the historical proxy to
the atomic rule, and the private inverse solves the same boundary. Positive
leap-second formatting no longer smears the leap across the preceding civil
day. Low-level atomic helpers implement the IAU SOFA 1960-1971 offset-and-drift
segments and reject earlier UTC-to-TAI conversion rather than inventing atomic
history.

BCE-safe calendar decomposition also carries a rounded `24:00:00` into the
next proleptic-Gregorian civil date instead of returning an invalid hour.

### Planetary frames, observers, and published rates

Geocentric, heliocentric, planetocentric, Solar System barycentric,
received-light, and admitted asteroid products now share the true-of-date
ecliptic transformation. Geometric mode removes physical light-path
corrections without silently changing the declared output frame. Topocentric
observer position and velocity are formed in the same frame as the body vector
they modify.

`planet_at(...)`, `all_planets_at(...)`, and reduction surfaces require
topocentric latitude, longitude, and elevation as one all-or-none observer
vessel. Invalid centers, incomplete observer coordinates, and ambiguous
combinations fail explicitly. Aware UTC facade and REST inputs cross to UT1
before evaluation and report coherent UT1/TT metadata.

`PlanetData.speed` is now the TT-day derivative of the same corrected
geocentric ecliptic longitude returned to the caller. Central differences
govern ordinary coverage; second-order one-sided differences preserve lawful
evaluation at a kernel boundary. Retrograde truth is derived from this
published rate in both the Python and admitted native bulk paths.

## Eclipse and occultation geometry

### Eclipse event and contact integrity

Native solar greatest eclipse is now the minimum separation of the DE441
Earth-reception lunar-shadow axis, not merely an angular Sun-Moon conjunction.
Global central classification uses the actual shadow-ray intersection with the
Earth. This prevents annular eclipses from being promoted to hybrid by a
fictitious near-side observer.

Observer-local solar searches require real topocentric disk overlap with the
Sun above the horizon. Local event type, magnitude, radii, time, and kind
filter now describe the same local maximum. Rare-kind searches continue to the
kernel coverage boundary rather than stopping after an undocumented fixed
number of lunations.

Penumbral lunar eclipses are first-class events. Lunar contacts are assembled
by a signed-clearance pair solver that can recover phases shorter than the
coarse scan, preserve a truncated ingress or egress honestly, and represent a
mean-limb limiting tangent in both phase fields under an explicit one-millimetre
coalescence policy.

Contact scans reject invalid bounds, non-advancing steps, duplicate roots, and
non-finite objectives. A deterministic path solver that exhausts its lawful
search now fails explicitly instead of returning a partial scientific result.
Eclipse datetime inputs cross UTC to UT1 exactly once, and serialized event and
contact times convert UT1 back to UTC.

### NASA lunar-compatibility model

The NASA-facing lunar canon now applies one coherent apparent geocentric
reduction:

1. evaluate the Sun and Moon from the same Earth-reception state;
2. apply reception light time;
3. apply annual aberration to each body;
4. intentionally omit gravitational deflection, topocentric parallax, and
   atmospheric refraction.

The default identifier is
`nasa_shadow_axis_apparent_sun_moon`. Historical geometric and retarded
identifiers remain available as explicit experiments. NASA-compatible
`canon_method`, `source_model`, gamma, and numerical results intentionally
change; native DE441 eclipse semantics remain a separate product.

### Instantaneous Besselian elements

`SolarBesselianElements` and
`EclipseCalculator.solar_besselian_elements(jd_ut1)` expose an immutable
instantaneous product. The method evaluates exactly the supplied instant; it
does not hide an eclipse search or a polynomial fit.

The product projects the DE441 Earth-reception light-time Sun/Moon
center-of-mass shadow line into the true equator and equinox of date:

- `x` is east-positive and `y` north-positive;
- `x`, `y`, `l1`, and `l2` are in Earth equatorial radii;
- `d` and `mu` are in degrees;
- the cone tangents are dimensionless and derive from exact common-tangent
  cone geometry;
- `l2` follows the NASA fundamental-plane sign convention;
- `mu` is the TT/TDT ephemeris hour angle, not physical-UT1 GAST.

The method admits only a reader whose content identity is DE441/LE441. This
surface is engine-only and does not add a `Moira` facade method or REST route.

### Solar partial-visibility footprints

`Moira.solar_eclipse_footprint(...)` and
`POST /v1/eclipses/solar/footprint` add immutable footprint points, penumbral
contacts, named limit-track components, time-monotone segments, topology, and
an aggregate visibility-footprint vessel.

The governing product sweeps the exact physical mean-limb penumbral cone from
DE441/LE441 Earth-reception states across zero-elevation WGS 84. It reports P1
and P4, optional P2 and P3, north/south penumbral envelopes, geometric
sunrise/sunset components, and either `one_limit_connected` or
`two_limit_two_loop` topology in UT1.

Sampling is bounded from 9 to 721 points, with a default of 181. The requested
count changes interior density, not the solved boundary graph. Folded
components are emitted as contiguous, strictly time-ordered segments with
shared refined endpoints. Two-limit products are restricted to central global
eclipses, and their horizon components stay in the P1-P2 or P3-P4 intervals.

This is a zero-elevation geometric mean-limb product. It does not claim
atmospheric refraction, observer-height effects, magnitude contours, or local
apparent circumstances.

### Polar central paths

Central-path geography now uses the forward DE441 reception-time shadow-axis
intersection on WGS 84, rotated through true-of-date, physical-UT1 GAST, and
admitted polar motion. Endpoints solve axis/ellipsoid tangency.

Greatest width is the full cross-track support span of the closed umbral or
antumbral cone footprint, not a centered spherical chord. A
spherical-classification/WGS-84 divergence or an incomplete one-limit footprint
fails explicitly instead of publishing contradictory path data. The existing
`SolarEclipsePath` vessel, facade method, and REST schema are retained.

### Polar-safe lunar occultation topology

Four facade methods and four additive REST routes now expose complete
two-sided-band topology for planetary and fixed-star lunar occultations:

- `Moira.lunar_occultation_path_topology(...)`
- `Moira.lunar_occultation_path_topology_at(...)`
- `Moira.lunar_star_occultation_path_topology(...)`
- `Moira.lunar_star_occultation_path_topology_at(...)`
- `POST /v1/occultations/lunar-path-topology`
- `POST /v1/occultations/lunar-path-topology-at`
- `POST /v1/occultations/lunar-star-path-topology`
- `POST /v1/occultations/lunar-star-path-topology-at`

The result preserves the established summary geometry and adds center points,
intrinsic left/right boundary tracks, greatest-limit points, exact
geographic-pole ingress/egress contacts, and a shared time lattice. Left and
right are intrinsic sides relative to increasing UT1, not north and south
latitude.

The nominal topology uses a spherical mean lunar limb. Planetary target disks
use JPL equatorial solid-body radii; fixed stars remain point sources; Saturn's
rings are excluded; and the Sun remains on the eclipse surfaces. Topocentric
observers are WGS 84 geodetic, while reported path widths use spherical
great-circle distance with radius 6378.137 km.

Search work is bounded before candidate evaluation. Boundary cells are always
refined, connected support determines event coalescence, and greatest-width
tangents share one center anchor so results do not depend on cache history.
The compatibility summary now reports fixed-site duration at the greatest
location rather than the lifetime of the global footprint.

### Topography-conditioned lunar stellar contacts

The direct-import `moira.lunar_occultation_contacts` module adds immutable
disappearance, reappearance, tangency, visibility, policy, profile, and
sequence vessels for stellar contacts.

The product combines:

- content-identified DE441/LE441 for the Moon-to-observer light cone;
- NAIF DE440_ME421 orientation resources;
- official USGS LOLA relief;
- proper-motion-propagated sovereign-registry star directions;
- finite-distance tangent-circle and perspective-equivalent-radius geometry;
- a contact-private Klioner equation-70 stellar-deflection path with declared
  SOFA `Ldn` limiters.

The model is airless and intentionally excludes atmospheric refraction and
observer-motion aberration. It remains distinct from nominal mean-limb path
limits and from observed IOTA contact records.

LOLA acquisition now covers the complete declared plus or minus 12 km relief
shell, maps every intersecting 15-degree STAC cell with pole/dateline-safe
topology, streams one tile through all event slices, and fails closed on
missing or malformed resources and exceeded work budgets. Contact solving
distinguishes shallow unique tangencies from true plateaus and rejects hidden
sub-scan crossing pairs.

This surface is engine-only through direct imports. It does not add a
`Moira` facade method or FastAPI route and requires the separately declared
`lunar-graze` optional dependency and data boundary.

## Primary directions

### One explicit computational ontology

Primary directions now expose the result ladder as named objects:

- speculum entry;
- primary arc;
- typed relation;
- per-significator local condition;
- chart-wide aggregate profile;
- directed promissor-to-significator network.

The admitted methods are `PLACIDUS_MUNDANE`, `PTOLEMY_SEMI_ARC`,
`PLACIDIAN_CLASSIC_SEMI_ARC`, `MERIDIAN`, `MORINUS`,
`REGIOMONTANUS`, `CAMPANUS`, and `TOPOCENTRIC`. Method capability is
enforced: mundane-only Placidian methods cannot be relabeled as zodiacal.
`FIELD_PLANE` remains outside the admitted space.

The time-key surface includes Ptolemy, Naibod, Cardan, and Solar. Solar-key
conversion requires an explicit positive natal solar rate and identifies
itself as a static-rate conversion. It no longer silently falls back to Naibod.

### Geometry, identity, and failure doctrine

Placidian mundane position is continuous through all four quadrants, and
Ptolemaic oblique ascension/descension preserves signed behavior.
Regiomontanus, Campanus, Topocentric, and Morinus pole/projection work is
expressed through explicit spherical geometry. Circumpolar no-real domains,
limiting tangencies, and invalid inverse-trigonometric domains fail closed
instead of being broadly clamped or repaired after the calculation.

The Placidian-classic horizon endpoint now receives the actual
`OA(ASC) = (ARMC + 90 degrees) mod 360` coordinate. House-cusp-sourced
aspectual promissors materialize the named cusp before projection. Fixed-star
aliases retain caller identity. Target recognition no longer accepts arbitrary
names merely because they contain node-like text.

Arcs distinguish their true relational kind—conjunction, opposition,
zodiacal aspect, parallel, rapt parallel, or reflected point—from compatible
perfection-kind fields. Immutable vessels reject contradictory or non-finite
state, aggregate counts conserve their members, and transition networks must
form one realizable connected directed Euler path or a lawfully linearized
circuit.

### Facade and typed transport

The `Moira` facade adds canonical delegation for:

- policy-preset construction;
- single-arc relation evaluation;
- per-significator condition;
- aggregate profile;
- directed network.

Established `Moira.speculum(...)` and
`Moira.primary_directions(...)` positional calls remain valid and gain only
keyword-only doctrine controls.

The REST family now has eight paths. Version 5.0.0 adds reduction forms for
arcs, profiles, and networks plus submitted-arc relation evaluation:

- `POST /v1/primary-directions/arcs/reduction`
- `POST /v1/primary-directions/profile/reduction`
- `POST /v1/primary-directions/network/reduction`
- `POST /v1/primary-directions/relations`

Raw strings, duck-typed arc payloads, and fallback-prone resolution have been
replaced by typed preset, policy, key, and `PrimaryArc` reconstruction.
Omitted submitted arcs mean engine search; an explicit empty list means a
lawful empty submitted evaluation. Payloads are bounded to 4,096 arcs.
Reduction responses report the exact requested and canonical policy, key,
search mode, observer, and effective-house truth.

Search-only typed vessels admit:

- Ptolemaic antiscia and contra-antiscia;
- Ptolemaic zodiacal parallels and contra-parallels;
- direct and converse Placidian rapt parallels;
- sovereign-catalog fixed stars;
- Morinus aspect-path contexts.

These targets are materialized during search and are therefore not accepted by
submitted-only relation evaluation.

### Source-scoped signed primary motion

The
`topocentric_zodiacal_aspect_signed_primary_motion` preset exposes
Makransky's assigned-zero, projected-perfection Topocentric zodiacal-aspect
product without changing traditional role-exchanged converse.

It constructs one ordered shortest circular arc:

- positive is direct;
- negative is converse;
- numerical zero is no event;
- an exact or tolerance-coalesced 180-degree boundary is directionally
  ambiguous and fails closed.

The preset is search-only because a submitted `PrimaryArc` retains a positive
magnitude and an existing label, not the raw signed displacement required to
derive that label. Signed searches require explicit non-empty significator and
promissor filters. This doctrine is narrow; it is not the deferred global
neo-converse doctrine.

### Primary-directions evidence boundary

The external-authority ledger now classifies each example by what it can
actually prove. Named Morin, Makransky/Polich, Lilly/Kolev, Sepharial, Leo/
Griscti, and Borealis material constrains specific method laws or special
targets under printed-input tolerances.

It does not establish whole-family parity across all methods, targets, epochs,
latitudes, or historical schools. Bundled catalog fixtures remain regression
evidence, and rounded or modern-adaptation examples remain scoped
corroboration where the original source does not expose the required
intermediate object.

## Aspects, relationships, and pattern structure

### First-class declination aspects

`moira.declination_aspects` now owns parallel and contra-parallel doctrine.
Immutable policy and result vessels preserve:

- aspect kind;
- signed error;
- orb admission;
- same- or opposite-hemisphere law;
- equator ambiguity;
- applying, exact, separating, stationary, or indeterminate motion;
- provenance for the selected policy.

Public access includes `Moira.declination_aspect_motion_witness(...)` and
`POST /v1/aspects/declination-motion-witness`. Historical
`moira.aspects` imports, package-root exports,
`Moira.declination_aspects_from_declinations(...)`, and
`POST /v1/aspects/from-declinations` remain available.

The longitude counterpart, `AspectMotionWitness`, is also public through
`POST /v1/aspects/motion-witness`. It reports signed branch error, relative
speed, orb rate, exactness, station reasons, orb policy, and caller-declared
frame/timescale without claiming a future perfection search.

### Pattern roles and dominance

Grand Trine, Minor Grand Trine, Cradle, Trapeze, Grand Cross, Mystic Rectangle,
and Septile Triangle detectors now preserve the edge or support roles proven by
their detector. Structural condition state describes role completeness, not
motion, strength, or interpretation.

Cradle, Trapeze, Mystic Rectangle, and Septile Triangle detection no longer
depends on incidental body-name orientation. The documented direct `include`
and `orb_factor` behavior has been restored, and orb scaling is applied during
initial aspect admission as well as final pattern admission.

`find_all_patterns(...)`, `Moira.patterns(...)`, and shared pattern REST
requests add opt-in `dominant_only`. It uses strict body-and-aspect subgraph
containment, allowing a Grand Trine contained in a Kite to be hidden without
erasing unrelated smaller patterns or position-based Stelliums. The default
remains unfiltered.

### Synastry and Davison truth

Relationship networks preserve caller-supplied chart labels for pair and body
nodes. Result kind, condition state, relation kind, basis, method, correction
mode, and policy flags are validated as one coherent truth. Custom orb
provenance includes a normalized deterministic table rather than a boolean
marker.

Davison MC refinement no longer accepts the circular positive/negative
180-degree discontinuity as a root. Non-convergence is explicit, and antipodal
or near-antipodal locations are rejected because no unique spherical midpoint
exists.

Synastry truth, classification, relation, condition, network, overlay,
composite, and Davison vessels are frozen. Nested maps are defensive immutable
copies, and composite cusps are tuples.

## Harmonics

### Positive-real harmonic identity

Direct harmonic charts, conjunctions, pattern scores, and composites preserve
every positive finite real harmonic. An input such as `H = 5.5` is no longer
silently truncated to 5.

Source longitudes are first normalized to the canonical zero-Aries
`[0, 360)` branch and then multiplied. This makes non-integer H an explicit
continuous-multiplier product. Range, sweep, and transit-forecast harmonic
lists remain integer by doctrine.

The single-H REST schemas now accept real harmonics. The existing age-harmonic
route remains available, but clients no longer need to manufacture a synthetic
age-harmonic epoch merely to request fractional H.

### Addey inverse-harmonic orb policy

Immutable `HarmonicOrbPolicy` and resolved `HarmonicOrbTruth` vessels expose
the admitted relation

`O_H = O_1 / H`

with authority, source locator, formula, scaling mode, projected limit,
source-circle equivalent, request-adapter mode, and continuous-extension truth.
The configured H1 reference is the limit on the projected harmonic chart. The
source-circle allowance is reported separately, preventing an accidental
second division.

The existing REST `orb` field remains compatible and is interpreted as the H1
reference/projected limit. The explicit `orb_policy` object is additive.

### Mixed-origin harmonic transit forecasting

`moira.harmonic_transits` adds immutable sampled forecasts for:

- one transit plus two natal members;
- two transit members plus one natal member.

`Moira.harmonic_transit_forecast(...)` and
`POST /v1/harmonics/transit-forecast` evaluate requested integer harmonics
using one minimum circular covering arc for all three members. Results preserve
origin-qualified members, complete triples, observed windows, duration policy,
deterministic peaks, and complete provenance.

Boundaries and peaks are witnesses from the supplied sample lattice. The
product does not interpolate exact ingress or egress and does not claim Sirius
parity. REST requests are bounded by bodies, sample count, harmonics, and a
25,000-evaluation materialization budget.

## Phenomena, planetary hours, and houses

### Phenomena searches

Greatest elongation maximizes true great-circle planet-Sun separation,
including ecliptic latitude, while east and west remain explicit branch
policy. Perihelion and aphelion searches use bounded physical turning-point
refinement.

Conjunction searches cannot return polished events outside the requested
interval. Proximity searches refine negative- and positive-threshold crossings
independently, reject the opposition wrap as a false bracket, retain slow-body
crossings, and de-duplicate boundary events. Cazimi, combust, and
under-sunbeams searches share their exact thresholds with point-in-time
solar-condition truth. Resonance approximation selects the closest lawful
bounded fraction and rejects identical-period bodies.

### Planetary hours

Sunrise and sunset refinement now solves the governing topocentric geometric
solar-altitude crossing at -0.833 degrees to a 0.1-second time tolerance. A
crossing that escapes its local day is rejected, and polar no-rise/no-set
geometry fails explicitly rather than generating a fictional schedule.

The planetary weekday follows local mean solar time at sunrise, including
longitude and BCE-safe floor behavior. Temporal-hour boundaries share exact
endpoints and are contiguous; facade consumers use the canonical
`hour_at(...)` lookup. REST timestamps serialize through Moira's BCE-safe
calendar vessel.

### Houses

House calculations reject non-real, non-finite, and out-of-range locations.
The REST schema enforces latitude in `[-90, 90]` and longitude in
`[-180, 180]`.

Azimuthal geometry must yield exactly one ordered ecliptic cusp cycle. Carter
and high-latitude branches, polar degeneracy, unordered cycles, unknown
systems, and configured fallback paths preserve explicit policy and failure
reasons. REST house calculations now pass UT1, rather than raw UTC Julian day,
to the engine.

## Source-owned Western electional work

### Source profiles and neutral witnesses

The release adds source-owned profiles from Sahl bin Bishr's `On Elections`,
Dorotheus's `Carmen Astrologicum` Book V, and Lilly's 1647
`Christian Astrology`. Distinct historical lineages remain distinct; they are
not collapsed into one generic traditional-election algorithm.

Public neutral or source-scoped building blocks include:

- `sahl_moon_condition_v1`;
- `dorotheus_moon_condition_v1`;
- `dorotheus_rooted_context_v1`;
- `dorotheus_construction_v1`;
- `lilly_1647_perfection_v1`;
- `LunarEclipticDirectionWitness`;
- `MoonConnectionFlow`;
- `AspectMotionWitness`.

Sahl's burnt-path endpoints and Arabic/Latin eighth-rule variants remain
explicit policy. Dorothean clauses whose source supplies no interval,
combination law, sign table, or closed predicate remain `not_evaluable` even
when Moira can expose the underlying astronomical measurements.

Lilly's classical-perfection product returns a bounded, time-ordered trace of
exact aspects, stations, and sign ingresses plus separate direct perfection,
translation, collection, prohibition, refranation, and frustration witnesses.
It is not a generic traditional mode and does not silently add Sahl, Bonatti,
abscission, or reflection doctrine.

The existing Ramesey urgent-time remedy now exposes non-erasing, clause-level
tri-state fulfillment. Moon cadence, whole-sign Moon/Ascendant relation,
fortune/Ascendant placement or configuration, and the planetary-hour lord are
reported separately. The source does not close the predicates for fortifying
the Ascendant cusp, Ascendant lord, or hour lord, so those clauses remain
`indeterminate` and cannot be erased by the evaluated testimony.

### Neutral lunar geometry and connection flow

`LunarEclipticDirectionWitness` separates the Moon's north/south position
from northward/southward motion. It reports adjacent exact sign-changing node
crossings, their directions and UT1 times, the nearest-crossing relation, and
the latitude residual. Its root tolerance is numerical solver policy, not an
astrological node orb.

Dorotheus's southern-descent and northward-crossing clauses consume the same
neutral geometry under separate source policies. Where the text supplies no
crossing interval or longitude/latitude combination law, the clause remains
indeterminate even though the measurable geometry is complete.

`MoonConnectionFlow` preserves the previous exact separation, current signed
motion, next sign-bounded lunar connection, event epochs, sign bounds, signed
residuals, and explicit no-event reasons. The caller selects the previous-event
window. The result does not silently assign those events to the historical
stakes of a matter profile when the source leaves that assignment open.

### Dorothean construction and sampled Moon-profile windows

`dorotheus_construction_v1` composes the admitted V.2-V.7 and V.31 source
layers. Its completeness fields distinguish a source-complete matter profile
from a complete electional judgement:

- `source_complete = true`;
- `complete_matter_profile = true`;
- `numerically_complete = false` while source-open clauses remain;
- `complete_electional_judgement = false`.

The increasing-in-calculation witness compares the Moon's true orbital
longitude in the mean ecliptic/equinox of date with the IERS 2010 TT mean lunar
longitude. Both values, the signed equation, and the addition/subtraction
direction remain visible.

The separate `western_electional_profile_windows` product performs bounded,
discrete status scanning for the Ramesey, Sahl, and Dorotheus Moon profiles.
Callers explicitly name qualifying statuses. Each sample returns its status,
qualification truth, triggered rule ids, and not-evaluable rule ids. Adjacent
samples may merge under declared gap policy, but the product does not claim
truth is continuous between samples or that it has solved an exact transition.

### Current matter-profile registry

Sahl matter profiles are independent source-ordered products:

- `sahl_lending_v1`
- `sahl_investment_v1`
- `sahl_purchase_v1`
- `sahl_sale_v1`
- `sahl_business_partnership_v1`
- `sahl_building_v1`
- `sahl_demolition_v1`
- `sahl_land_v1`
- `sahl_wells_and_rivers_v1`
- `sahl_planting_v1`
- `sahl_sowing_v1`

Dorothean matter profiles are likewise independent:

- `dorotheus_demolition_v1`
- `dorotheus_leasing_v1`
- `dorotheus_buying_and_selling_v1`
- `dorotheus_lunar_price_timing_v1`
- `dorotheus_land_purchase_v1`
- `dorotheus_travel_v1`
- `dorotheus_ship_acquisition_v1`
- `dorotheus_ship_construction_v1`
- `dorotheus_ship_launch_v1`
- `dorotheus_land_travel_v1`
- `dorotheus_sea_travel_v1`
- `dorotheus_partnership_v1`
- `dorotheus_debt_and_payment_v1`
- `dorotheus_writing_a_will_v1`

Each profile retains its source-owned inputs, house or whole-sign stakes,
significators, clause order, explicit gates, and unresolved vocabulary.
Dorothean land/sea travel requires an explicit source-faithful or separately
attributed sign-nature policy. Flow-dependent profiles require a declared
previous-event window. Radical overlays require the complete natal bundle
owned by that profile.

No historical profile emits a numeric score or recommendation.

### Bounds-table correction

The previously labeled Ptolemaic bounds duplicated the Egyptian table. The
former Chaldaean table implemented neither Ptolemy's stated triplicity sequence
nor its sect-dependent Saturn/Mercury ordering. Version 5.0.0 replaces both
with source-transmitted tables from `Tetrabiblos` I.20-I.21.

The admitted identifiers are now `egyptian`, `ptolemaic`,
`chaldean_day`, and `chaldean_night`. Ptolemaic planetary totals and all 60
segments are invariant-checked. The Chaldaean variants use the stated
8-degree, 7-degree, 6-degree, 5-degree, and 4-degree sequence and reverse
Saturn/Mercury precedence by sect. Bounds lookup and table REST responses carry
the selected primary-source citation.

### Phase 8: complete judgement under one profile

`western_electional_judgement_v1` composes one admitted Sahl or Dorotheus
matter profile with the matching Moon condition, an applicable Dorothean
rooted context, a bounded Lilly perfection path, natal/radical context where
required, fortification/remedy witnesses, unresolved requirements, exclusions,
authorities, and reader provenance.

The serialized precedence law is:

1. an explicit component impediment yields `impeded`;
2. otherwise an indeterminate component or blocking unresolved requirement
   yields `indeterminate`;
3. only complete required components with an admitted constructive perfection
   yield `complete_under_profile`.

The summary state never replaces the component evidence. Sahl profiles mark
Dorothean rooted or radical context `not_applicable` rather than fabricating
it. Public access is through
`Moira.western_electional_judgement_at(...)` and
`POST /v1/electional/western/judgement`.

### Phase 9: caller-weighted decision support

`western_electional_ranking_v1` accepts 2-64 distinct caller-supplied
candidate instants evaluated under one identical Phase 8 selection.

The fixed contribution vocabulary is limited to visible direct perfection,
translation of light, and collection of light. Callers supply unique finite
nonzero weights. Moira provides no hidden or historical default weights. The
score is the weighted sum divided by the sum of absolute weights and is bounded
to `[-1, 1]`.

Only `complete_under_profile` judgements are ranked. Impeded and
indeterminate candidates remain in a separate partition with their complete
Phase 8 evidence; they are not converted to numeric zero. The deterministic
tie-break is score descending, Julian day ascending, then input index
ascending.

This is explicitly Moira-owned numeric decision support, not historical
doctrine or empirical proof. Advice and recommendation remain unadmitted.
Public access is through `Moira.western_electional_ranking_at(...)` and
`POST /v1/electional/western/ranking`.

### Phase 10: bounded observed judgement windows

`western_electional_judgement_windows_v1` scans complete Phase 8 signatures
in either sampled or partially event-refined mode. It preserves judgement,
Moon, matter, rooted-context, perfection, component, and unresolved-requirement
states.

Known Lilly perfection, rooted next-connection, and matter Moon-flow events may
seed partial refinement when visible in the sampled evaluation. They are
reported as candidate seeds, not asserted causes. Only an observed Phase 8
output change is returned as a transition cause.

The v1 resource policy caps:

- span at 31 days;
- initial samples at 64;
- total evaluations at 256;
- refinement iterations at 24;
- candidate event seeds at 128;
- windows at 64;
- transitions at 63;
- initial cadence at no less than one hour.

Because v1 does not contain an exhaustive inventory of every sign, house, orb,
node, station, sunrise, planetary-hour, dignity, and source-threshold boundary,
it never labels its output exact or continuously true. Equal sampled endpoint
signatures may conceal an interior transition.

Public access is through
`Moira.western_electional_judgement_windows(...)` and
`POST /v1/electional/western/judgement-windows`. Ranking remains a separate
request and is never applied implicitly.

### Electional public routes added since 4.2.1

- `POST /v1/electional/western/lunar-ecliptic-direction`
- `POST /v1/electional/western/profile-windows`
- `POST /v1/electional/western/dorotheus-construction`
- `POST /v1/electional/western/dorotheus-matter-profile`
- `POST /v1/electional/western/dorotheus-rooted-context`
- `POST /v1/electional/western/dorotheus-moon-condition`
- `POST /v1/electional/western/sahl-moon-condition`
- `POST /v1/electional/western/sahl-matter-profile`
- `POST /v1/electional/western/classical-perfection`
- `POST /v1/electional/western/judgement`
- `POST /v1/electional/western/ranking`
- `POST /v1/electional/western/judgement-windows`
- `POST /v1/aspects/moon-connection-flow`
- `POST /v1/aspects/motion-witness`

All source-profile, judgement, ranking, and window responses preserve the
non-empirical boundary. They do not provide generated advice, mystical prose,
an uninspectable auspiciousness score, or a guarantee that an election will
produce a real-world outcome.

## Runtime, native substrate, and server readiness

### Native hardening

Chebyshev, Type 13, smoothing-spline, and planetary native entry points reject
empty, mismatched, non-finite, unordered, or unsafe payload shapes before
evaluation. Nutation releases the GIL around the complete native series while
Python-owned coefficient tables remain alive and immutable.

The default bulk planetary calculation resolves required SPK segment
evaluators once per public computation and reuses them during Earth-state
construction and light-time iteration. Cache ownership remains bounded by the
kernel handle.

### Runtime-dispatched AVX2

Capable x86 hosts select a separately compiled AVX2 implementation for
three-component Type 2 Chebyshev position and derivative evaluation.
Unsupported CPUs and builds retain the scalar implementation. The wheel does
not acquire a universal AVX2 requirement.

AVX2/scalar agreement at 1e-14 absolute tolerance is an implementation-parity
gate. It is not external astronomical validation.

### Optional prewarm and readiness

`MOIRA_SERVER_PREWARM=1` performs one bounded per-worker J2000 all-planet
warmup before computational traffic is admitted. It excludes lunar nodes,
supplemental small-body kernels, and the HTTP chart-result cache.

Prewarm is disabled by default because every worker pays its own native memory
cost. In one scoped Windows/DE441 in-process smoke:

- startup changed from 0.286 s to 2.626 s;
- the first full chart changed from 2.450 s to 0.0083 s;
- an identical HTTP-cached chart remained approximately 0.0024-0.0028 s;
- observed private working set after prewarm was approximately 1.65 GiB per
  worker.

These values are performance evidence from one environment, not astronomical
validation or a deployment guarantee. They exclude TCP, TLS, reverse-proxy,
and public-network latency.

`GET /health` remains an HTTP 200 liveness signal after a prewarm failure.
`GET /ready` keeps its response body but returns HTTP 503 whenever the
planetary kernel or enabled prewarm is not ready. It returns HTTP 200 only when
the worker can accept computational traffic.

The published base runtime remains the standard library plus the required
compiled `moira._moira_native` extension. SciPy is not a base dependency.

### Release artifact admission

The tag workflow now verifies that the pushed tag, `pyproject.toml`, public
runtime version, dated changelog boundary, and release-document names all
identify one release before building. Each CPython 3.10–3.14 platform wheel is
installed by cibuildwheel and must import the native backend with matching
distribution/runtime versions. The sdist must pass Twine metadata validation,
exclude `.bsp` kernels, build in isolation, and pass the same native import and
version smoke before publication is admitted.

## Compatibility and migration guide

### Required caller changes

| Area | 4.2.1-era behavior | 5.0.0 action |
|---|---|---|
| Relationship results | Some result vessels and nested maps could be mutated. | Treat synastry, overlay, composite, Davison, classification, condition, relation, and network results as immutable. Construct a new value instead of mutating one. |
| Readiness probes | `/ready` could return HTTP 200 with `ready=false`. | Accept HTTP 503 with the existing response body as the canonical not-ready result. Keep `/health` for liveness. |
| Bounds doctrine | `chaldean` and `CHALDEAN_BOUNDS` hid a sect-dependent ambiguity. | Select `chaldean_day` or `chaldean_night` and use `CHALDEAN_DAY_BOUNDS` or `CHALDEAN_NIGHT_BOUNDS`. |
| Ramesey remedy result | The provisional result exposed instruction metadata without complete fulfillment truth. | Consume the version 1.1.0 tri-state clause witnesses and aggregate fulfillment instead of the former instruction-only assessment literal. |
| Scientific scalars | Some booleans, numeric strings, non-finite values, or out-of-range values were coerced. | Send correctly typed finite values. Handle engine exceptions or REST validation responses for invalid input. |
| Topocentric observers | Partial latitude/longitude/elevation combinations could be tolerated. | Supply all observer fields together or omit all of them. |
| Primary-directions policies | Unknown, conflicting, or ambiguous policy/key/preset combinations could fall through compatibility logic. | Use a canonical admitted preset, method, space, motion doctrine, and key. Supply an explicit positive natal solar rate for the Solar key. |
| Signed Topocentric primary motion | No source-scoped public preset existed. | Use the new search-only signed preset with explicit non-empty significator and promissor filters. Do not submit pre-labeled arcs to it. |
| Harmonic identity | A real H could be truncated to an integer. | Treat single-H results as positive-real continuous multipliers. Keep range, sweep, and transit-forecast harmonic lists integral. |
| Harmonic orb | `orb` lacked complete scaling provenance. | Existing `orb` remains valid as the H1 reference/projected limit; use `orb_policy` when explicit provenance is required. |
| Pattern reduction | Detector roles and containment were incomplete. | Consume named structural roles. Request `dominant_only=true` only when strict contained patterns should be suppressed. |
| Eclipse compatibility | NASA-compatible metadata and values reflected an incomplete apparent reduction. | Expect corrected `canon_method`, `source_model`, contact values, and gamma. Do not compare native and NASA-compatible products as identical models. |
| Historical/future Delta T | Boundary interpolation and attribution could imply unsupported source or forecast truth. | Expect corrected values and provenance. Treat post-2150 output as scenario extrapolation, not forecast. |
| Houses, phenomena, planetary hours | Invalid geometry could be tolerated or approximated. | Handle explicit failures for invalid locations, windows, thresholds, polar no-rise/no-set days, and unsupported branches. |

### Preserved public surfaces

- Existing 4.2.1 facade names and established computation-route paths remain
  available unless the migration table names a corrected doctrine value.
- Existing chart request and response envelopes remain intact.
- `Moira.speculum(...)` and `Moira.primary_directions(...)` preserve their
  positional arguments.
- The age-harmonic route remains available.
- Historical declination imports through `moira.aspects` remain available.
- Existing `SolarEclipsePath` and nominal occultation summary vessels retain
  their field shapes.
- Existing NASA lunar-contact facade and REST schemas remain structurally
  unchanged; their declared method metadata and numerical content are
  corrected.
- Server prewarm is opt-in.

## Validation and evidence

Moira 5.0.0 deliberately separates four evidence classes.

### Primary-authority and institutional-source validation

- NASA/GSFC figure and catalog products provide named eclipse maxima,
  individual lunar-contact instants, Besselian elements, central-path rows,
  widths, durations, and partial-footprint anchors.
- JPL Horizons supplies a bounded authority fixture for the 2026-10-05 lunar
  occultation of Mars at the geographic North Pole.
- IOTA observed 2024 Spica graze chronologies, paired with official USGS LOLA
  relief and DE441/LE441, constrain the modeled topographic contact sequence.
- IAU SOFA rules govern the 1960-1971 atomic UTC segments, and ERFA/SOFA
  comparison constrains the mean-lunar-longitude implementation used by the
  Dorothean equation witness.
- Original or method-origin primary-directions examples constrain named
  Campanus, Topocentric, Morinus, fixed-star, reflected-point, parallel, and
  rapt-parallel laws.
- Primary historical texts govern the admitted Sahl, Dorotheus, Lilly, and
  Ptolemaic bounds doctrine.

Historical-text validation establishes that software preserves the selected
source rule and its ambiguity boundary. It does not establish empirical
astrological efficacy.

### Cross-model regression envelopes

Many astronomical fixtures compare different physical or catalog models:

- NASA VSOP87/ELP2000-based products versus Moira's DE441/LE441 and physical
  mean-limb radii;
- older NASA DE200/DE405 path conventions versus DE441/WGS-84 geometry;
- Horizons predictive-EOP circumstances versus Moira's admitted clock and
  reduction policy;
- observed IOTA timings versus a modeled DE441/LOLA chronology.

Their published tolerances are regression envelopes that accommodate those
declared model differences. They are not source uncertainties, absolute
accuracy guarantees, or claims of exact-model parity.

Representative admitted ceilings include:

- NASA-compatible lunar contacts: 10 seconds for ordinary events and 30
  seconds for the limiting 2027 penumbral event;
- native lunar contacts: 120 seconds for ordinary events and 240 seconds for
  that limiting case;
- NASA-compatible greatest eclipse: 10 seconds;
- instantaneous Besselian `x`, `y`, `l1`, and `l2`: 1e-4 Earth
  equatorial radii; `d`: 0.003 degrees; circular `mu`: 0.007 degrees;
  cone tangents: 3e-6;
- the 2015 polar central path: 1 second for searched greatest, 3 km for named
  central-line and limit geometry, and 3 seconds for local central duration;
- partial-footprint anchors: 5 seconds and 40 km;
- the Horizons North-Pole Mars contacts: 2 seconds against separate
  half-second source brackets;
- the two IOTA/LOLA Spica site chronologies: maximum residuals of 0.381008
  seconds and 0.337355 seconds within a 0.5-second cross-model envelope.

The IOTA/LOLA refresh and authority-document drift checks are network-marked;
they are not implied by an ordinary offline test run.

### Physical and geometric invariants

Independent invariants enforce:

- monotone and bounded eclipse/contact chronology;
- closed penumbral footprint components and stable fold incidence;
- polar-safe sphere and ellipsoid navigation;
- zero-clearance occultation boundaries and center-to-limit width
  conservation;
- immutable policy and result vessels;
- primary-directions method/space capability and network conservation;
- aspect signed-error and condition-state identities;
- pattern-role completeness and strict subgraph containment;
- harmonic minimum-covering-arc completeness;
- house cusp ordering and temporal-hour contiguity;
- native payload shape and finite-value safety.

These are strong structural checks. They do not replace a product-relevant
external authority where one exists.

### Regression and transport parity

The repository adds focused engine, facade, REST, serializer, and OpenAPI
coverage for the new public products. DE441 fixtures protect selected numerical
behavior. Python/native and scalar/AVX2 comparisons protect implementation
agreement.

Those comparisons detect drift between Moira layers. They do not by themselves
prove external astronomical truth.

## Deliberate boundaries

The following claims are not made by 5.0.0:

- no universal primary-directions method-family parity;
- no global neo-converse doctrine;
- no admitted primary-directions field-plane space;
- no dense external oracle for every eclipse or occultation path point;
- no topographic occultation product hidden inside the nominal mean-limb
  topology;
- no atmospheric or observer-elevation semantics in the solar
  partial-visibility footprint;
- no exact continuous boundaries in sampled harmonic-transit or Western
  judgement-window products;
- no interpolation or exact-contact claim for sampled harmonic forecasts;
- no empirical validation of astrological doctrine;
- no Western electional advice or recommendation endpoint;
- no validated Delta T forecast beyond the admitted observational handoff and
  bounded model domain;
- no claim that performance measurements establish scientific accuracy.

These boundaries are part of the public contract. They identify where Moira
has a first-class, inspectable product and where further authority, doctrine,
data, or validation is still required.

## Further reading

- [Changelog](../../CHANGELOG.md)
- [Eclipse model standard](../02_standards/ECLIPSE_MODEL_STANDARD.md)
- [Eclipse oracle ledger](../03_validation/ECLIPSE_ORACLE_LEDGER_2026-05-04.md)
- [Primary directions backend standard](../02_standards/PRIMARY_DIRECTIONS_BACKEND_STANDARD.md)
- [Primary directions external-authority ledger](../03_validation/PRIMARY_DIRECTIONS_EXTERNAL_AUTHORITY_LEDGER_2026-07-19.md)
- [Harmonics backend standard](../02_standards/HARMONICS_BACKEND_STANDARD.md)
- [Harmonic transit forecast standard](../02_standards/HARMONIC_TRANSIT_FORECAST_STANDARD.md)
- [Delta T hybrid model](../02_standards/DELTA_T_HYBRID_MODEL.md)
- [Western electional implementation plan](../../docs/architecture/P13-U1_WESTERN_ELECTIONAL_ISSUES_01_16_IMPLEMENTATION_PLAN.md)
- [Python-governed/native-strengthened architecture](../../docs/architecture/MOIRA_PYTHON_GOVERNED_NATIVE_STRENGTHENING.md)
