## Moira Eclipse Model Standard

### Governing Principle

Moira computes eclipses from a single coherent `DE441`-based physical geometry
in `TT`. Compatibility outputs are translations, not truth.

This document defines the permanent standard for eclipse work in Moira. Its
purpose is to end model drift and to prevent the native engine from being
implicitly redefined by external catalogs.

### 1. Authority And Scope

- `native` is the authoritative Moira eclipse model.
- `nasa_compat` and any future compatibility mode are secondary translation
  layers for comparison or interoperability.
- External publications are benchmarks, not governing truth.

### 2. Time Policy

- Eclipse geometry is solved in `TT`.
- `UT1` is a reporting layer, not an optimization layer.
- Event definitions must not be stated in `UT1` space except as final user-facing
  output.

### 3. Lunar Greatest Eclipse Definition

For the native lunar model, greatest eclipse is defined as:

- the minimum perpendicular distance from the Moon's center to the Earth's
  umbral-shadow axis

This scalar is the primary event objective for native lunar event centering.
Catalog-specific proxies may exist in compatibility layers, but they do not
replace the native definition.

### 3.1 Solar Greatest Eclipse Definition

For the native solar model, greatest eclipse is defined as:

- the minimum perpendicular distance from Earth's center to the physical line
  through the Moon directed away from the Sun

The line is derived from DE441 Sun and Moon states on one Earth-reception light
cone at a TT arrival instant. Each target is evaluated at the emission epoch
whose photons arrive at the geocentre at that instant, following the NAIF
one-way reception-light-time object. Stellar aberration, observer parallax,
altitude, and local disk overlap do not define the global event instant.

### 4. Native Geometry Policy

Each native eclipse product must use one explicit and internally consistent
vector policy. Solar and lunar eclipses govern different physical objects, so
their policies are named separately rather than forced into one apparent-state
construction. For the current Moira standard:

- ephemeris basis: `DE441`
- event-solving timescale: `TT`
- lunar shadow-axis definition: the line through Earth opposite the incoming
  reception-light-time-corrected DE441 solar direction
- lunar Moon state: the physical geocentric DE441 Moon center at the event TT
  epoch; an Earth-observer light-time-retarded Moon is an apparent product and
  does not define intersection with Earth's shadow at that epoch
- lunar centering, classification, and contacts: one shared physical-Moon
  policy for penumbral, partial, and total event families
- solar centering: Earth-reception light-time Sun/Moon shadow-axis policy
- celestial frame: true equator and equinox of date
- stellar aberration: omitted from the physical shadow-line definition

For a central event, global annular/total classification is evaluated at the
first intersection of that shadow ray with Earth rather than at a fictitious
nearest-side observer. A total surface intersection with an annular geocentric
radius relation identifies a hybrid cone crossing; an annular surface
intersection remains annular.

This choice is not justified by NASA-catalog agreement. It is justified by
internal coherence with Moira's own physical event model.

The apparent retarded-Moon lunar objective remains available only inside named
diagnostic and compatibility comparisons. It is not a native event-family
selector. In particular, event type may not change merely because a search asks
for an umbral rather than penumbral family.

### 4.1 Instantaneous Solar Besselian Elements

`SolarBesselianElements` is the first-class native vessel for the fundamental-
plane representation of the solar shadow at one instant.
`EclipseCalculator.solar_besselian_elements(jd_ut1)` accepts a UT1 Julian Day,
derives the reader-bound TT epoch, and evaluates that instant directly. It does
not search for an eclipse, select a nearby event, or hide a polynomial fit. The
reader must be content-identified as DE441/LE441; another or indeterminate
ephemeris identity fails closed.

The governing conventions are:

- the fundamental plane passes through Earth's center and is perpendicular to
  the DE441 Earth-reception Sun/Moon center-of-mass shadow line;
- the Sun and Moon are light-time retarded to the same Earth-reception instant,
  with no stellar aberration applied to the physical shadow line;
- the axes use the true equator and equinox of date, with `x` positive east and
  `y` positive north;
- `x`, `y`, `l1`, and `l2` are expressed in Earth equatorial radii;
- `d` and `mu` are expressed in degrees;
- `mu` is the TT/TDT ephemeris hour angle of the shadow axis, not physical UT1
  Greenwich apparent sidereal time;
- the penumbral and central cone radii use Moira's physical mean-limb Sun and
  Moon radii and exact common-tangent cone geometry rather than a small-angle
  radius-over-distance substitution;
- `l2` follows the NASA fundamental-plane sign convention: negative is umbral
  and positive is antumbral at that plane; global hybrid classification still
  belongs to the separate Earth-surface geometry; and
- `tan_f1` and `tan_f2` are dimensionless cone-angle tangents.

This is an engine-level geometry surface. Its admission does not add a `Moira`
facade method or FastAPI route, and it does not alter `EclipseData`,
`EclipseEvent`, `SolarEclipsePath`, or the native C++ substrate.

### 4.2 Geographic Central-Path Geometry

The governing central-line point at one UT1 reporting epoch is the first
lawful intersection of the forward DE441 reception-time lunar-shadow axis with
the WGS 84 reference ellipsoid. The celestial shadow state is rotated to the
terrestrial frame with the true equator and equinox of date, physical GAST at
that UT1 epoch, and the admitted polar-motion matrix. Geographic latitude is
WGS 84 geodetic latitude; longitude is east-positive.

The first and last public central-line samples are the two times at which that
axis becomes tangent to the ellipsoid. They are not U1/U4 cone contacts,
observer-local visibility boundaries, or atmospheric horizon events. At a
central greatest-eclipse site, `umbral_width_km` is the full cross-track
support span of the closed instantaneous umbral or antumbral cone footprint on
the ellipsoid. It is not a centered spherical chord and is not derived from a
local angular-diameter shortcut.

The historical event classifier still begins from an equatorial-radius sphere.
If that classifier labels a high-latitude grazing event central while the
governing WGS 84 axis has no lawful intersection, path construction fails
explicitly. It must not return a partial-shaped zero-width vessel carrying a
central eclipse type.

Some grazing geometries have only one lawful central-shadow limit on the
ellipsoid because the other boundary closes against the terrestrial
terminator. A complete path-width product then requires a separately governed
terminator-closure construction. The ordinary closed-footprint solver fails
explicitly for that topology rather than returning the span of an incomplete
cone arc as a physical width. Refraction, observer elevation, and local
visibility remain observational products and do not redefine this physical
central path.

If the project ever changes the native vector policy, it must be changed here
first and then applied consistently across:

- event centering
- geometry derivation
- contact solving
- documentation
- regression expectations

### 4.3 Solar Partial-Visibility Footprint

`EclipseCalculator.solar_eclipse_footprint(jd_start, *, kind="any",
backward=False, sample_count=181)` is the first-class engine product for the
complete mean-limb geographic boundary of a searched solar eclipse.
`Moira.solar_eclipse_footprint(...)` delegates to that same signature, and
`POST /v1/eclipses/solar/footprint` exposes the additive transport surface. It
is separate from the central-line and central-width semantics of
`SolarEclipsePath`.

The governing construction is:

- reader identity: content-identified DE441/LE441, failing closed for another
  or indeterminate ephemeris identity;
- shadow state: the exact common-tangent penumbral cone derived from the
  Earth-reception light-time Sun and Moon center-of-mass states;
- limb convention: Moira's physical spherical mean-limb Sun and Moon radii;
- terrestrial surface: the zero-elevation WGS 84 reference ellipsoid;
- boundary epochs and public point timescale: UT1, with the corresponding
  reader-bound TT state derived at each epoch; and
- longitude convention: true, east-positive geographic longitude.

The result carries external penumbral contacts P1 and P4. A two-limit event
also carries internal contacts P2 and P3; they are absent for a one-limit
event. Because P2/P3 are internal contacts of a fully intersecting penumbral
generator family, `two_limit_two_loop` is admitted only for a central global
solar eclipse, never for a globally partial event. Named track components
preserve the north and south penumbral envelopes
and the geometric sunrise and sunset portions of the boundary. Component
identity is local to its boundary kind. Each admitted penumbral kind has one
connected component, identified by `component_id=0`, and exactly two
incidences on the geometric sunrise/sunset graph. That penumbral component may
fold in UT1, so contiguous `segment_id` values `0..n-1` identify its strictly
time-ordered portions; two segments meeting at a fold share the solver-refined
endpoint. This graph contract avoids either splicing simultaneous roots or
pretending that the folded portions are disconnected.
In a two-limit product, the north and south horizon-incidence sets are
disjoint. Each sunrise or sunset track lies wholly in either the P1-P2 ingress
interval or the P3-P4 egress interval; no horizon track crosses the P2-P3
interval where both penumbral limits exist.

The two admitted topology labels are:

- `one_limit_connected`: one penumbral-limit family closes through the
  geometric horizon into one connected boundary; and
- `two_limit_two_loop`: north and south penumbral limits participate in two
  closed boundary loops with disjoint horizon incidences, with P2 and P3
  marking the internal contacts.

`sample_count` controls only the requested interior temporal sampling density.
It defaults to `181` and is bounded to the inclusive range `9..721`. A fixed
internal solve, geometric endpoint clustering, exact horizon incidences, and
temporal-fold refinement govern `(kind, component_id, segment_id)` structure;
contacts, folds, and boundary transitions remain solver products rather than
rounded sample-bin substitutions. The admitted regression checks this
presentation-only contract at requested counts `9`, `99`, `181`, `257`, and
`721`.

This is a physical, geometric mean-limb footprint. It does not include
atmospheric refraction, observer elevation or terrain, lunar-limb topography,
magnitude or obscuration contours, local apparent contact circumstances, or a
rendered map projection. Those are distinct observational or presentation
products and must not be inferred from the footprint vessel.

### 5. Layer Separation

Moira separates eclipse work into two layers.

Physical layer:

- event centering
- eclipse classification
- shadow-axis distance
- gamma and related eclipse geometry
- contact solving

Observational layer:

- local visibility
- topocentric altitude/azimuth
- observer-specific circumstances
- presentation-facing apparent conditions

Observer-facing apparent effects must not be mixed into the native physical
event definition unless the standard itself is intentionally revised.

Observer-local solar visibility requires both a positive solar altitude and
positive topocentric disk-overlap margin. Daylight during a global eclipse is
not, by itself, a locally visible eclipse.

The location-search `kind` selector is local for `partial`, `annular`, `total`,
and `central`; the returned event data is rebuilt from that same local instant,
separation, and apparent radii. `hybrid` is necessarily the one global-path
selector: it chooses a globally hybrid event, while the returned site data says
whether that observer sees a partial, annular, or total phase.

For a central solar path, `duration_at_max_s` means the local interval between
second and third central contacts at the solved greatest-eclipse site. It does
not mean the elapsed time during which a central shadow exists somewhere on
Earth.

Central-path geography follows the WGS 84 axis/ellipsoid construction in
section 4.2. The separate observer-location optimizer used for partial and
local products treats geographic positions with pole-safe closed-surface
topology. Its refinement may cross a pole and must not clamp a lawful solution
to an artificial latitude such as `89.5` degrees. Longitude is canonicalized
only at an exact pole, where it has no geometric meaning.

A partial solar eclipse has no umbral or antumbral central line. The existing
shape-stable `SolarEclipsePath` contract continues to represent that path
product as the single solved point of greatest eclipse with zero central width
and zero central duration. It still does not encode penumbral limits. The
separate `SolarEclipseVisibilityFootprint` contract in section 4.3 carries the
full sampled mean-limb visibility boundary without changing those path
semantics.

### 5.1 Mean-Limb Contact Policy

Each lunar phase contact is a zero of one signed mean-limb clearance:

- positive clearance means separation;
- negative clearance means phase overlap; and
- zero clearance means tangency.

Ingress and egress are solved independently around the phase-clearance
minimum. A phase shorter than the coarse scan interval must remain detectable.
If the refined minimum lies within `1e-6 km` (one millimetre) of zero in the
native model, the limiting phase is numerically coalesced to one instant and
that same instant occupies both begin and end fields. The NASA-compatibility
solver uses the physically equivalent tolerance in Earth radii. This threshold
is numerical classification inside the declared mean-limb model; it is not a
claim about lunar topography, Baily's Beads, atmospheric visibility, or
observational timing uncertainty.

### 6. Compatibility Modes

Compatibility modes are allowed, but they follow strict rules:

- they must declare their source model explicitly
- they must not silently redefine native semantics
- they must be validated against the external authority they target
- they must be documented as compatibility surfaces, not as superior truth

For the current codebase:

- `native` = Moira's own DE441-first eclipse model
- `nasa_compat` = NASA-facing catalog-compatibility path

The default lunar NASA-compatibility method is
`nasa_shadow_axis_apparent_sun_moon`. At one TT reception epoch it derives the
Earth barycentric position and velocity once, evaluates both the Sun and Moon
with reception light-time against that same Earth state, and then applies
annual aberration to both directions. It does not apply gravitational
deflection, topocentric parallax, observer elevation, or atmospheric
refraction. This is a compatibility product definition, not a change to the
native physical shadow-line doctrine. The earlier geometric-Sun/geometric-Moon
and geometric-Sun/retarded-Moon method identifiers remain available as
explicit historical experiments; neither is the default.

### 7. Validation Philosophy

Moira validates eclipse behavior against external references, but validation is
used to measure the model, not to dictate it.

Native validation priorities:

- internal consistency of time scale and vector policy
- smoothness and stability of the event objective
- contact ordering and classification correctness
- broad agreement with external astronomical references

Compatibility validation priorities:

- agreement with the target catalog's published fields
- explicit residual measurement
- clear statement of what is and is not being matched

The runtime Besselian validation compares `x`, `y`, `d`, `mu`, `l1`, `l2`,
`tan_f1`, and `tan_f2` with NASA/GSFC rows for representative partial, total,
hybrid, and annular eclipses at five TT epochs per event. This is
primary-authority per-field cross-model validation, not exact model parity:
the NASA rows use VSOP87/ELP2000-82 and their published `k1`/`k2` lunar-radius
conventions, while Moira retains DE441 and its physical mean-limb radii.
The admitted absolute envelopes are `1.0e-4` Earth equatorial radii for `x`,
`y`, `l1`, and `l2`; `0.003` degrees for `d`; `0.007` degrees circular for
`mu`; and `3.0e-6` for each dimensionless cone tangent. They are regression
bounds between the declared models, not physical uncertainties.

The paired 2015 polar fixture applies the same per-field Besselian envelopes at
five TT epochs while separately validating the named WGS 84 central-path
product under its geographic tolerances. That additional event does not widen
the claim to atlas-wide temporal or path coverage.

The partial-visibility footprint has a separately bounded primary-authority
comparison against NASA/GSFC Table 2 products for the 2003
one-limit-connected and 2006 two-limit/two-loop events. Both authority rows are
the penumbral visibility footprints of total solar eclipses; they are not
external footprint validation for an event whose global class is partial.
Published contact and north/south boundary anchors are compared on a common TT
scale under `5 s` and `40 km` cross-model ceilings. NASA's products use
DE200/LE200 and their stated `k1` convention; Moira retains content-identified
DE441/LE441 and physical mean-limb radii. The ceilings are therefore
cross-model regression bounds, not physical uncertainties. NASA does not
supply dense numerical coordinates for the complete penumbral tracks, so the
validation does not claim dense-track or atlas-wide parity. Independent
invariant tests carry the proof burden for contact ordering, closure of each
penumbral component, the two topology classes, and the greatest point for an
actually partial event.

Individual lunar contact instants have a separate primary-authority gate
against NASA/GSFC's detailed 2023, 2024, 2025, and limiting 2027 lunar-eclipse
figures. These figure products publish UT contacts to one second and declare
`VSOP87/ELP2000-85`, `CdT (Danjon)`, and an event-owned Delta T; they are a
different source lineage from the century catalog's rounded phase durations.
Each source contact is placed on TT by adding the figure's declared Delta T.
Native UT1 contacts cross through the content-identified DE441 ephemeris clock,
while NASA-compatibility contacts are compared in their stored TT coordinate.
The default compatibility reduction is independently checked against the 2025
figure's printed apparent geocentric right ascension and declination for both
the Sun and Moon before its eclipse roots are admitted. That intermediate
evidence identified omitted apparent reduction as the dominant defect in the
former compatibility path. The bounded remainder includes DE441/LE441 versus
VSOP87/ELP2000-85, constants, and source-algorithm differences.

For the ordinary penumbral, partial, and total rows, the admitted per-instant
cross-model envelopes are `120 s` for native DE441 and `10 s` for the
NASA-compatibility path. The `0.0014`-magnitude 2027 penumbral row has separate
`240 s` native and `30 s` compatibility ceilings and remains solver-robustness
evidence rather than a close-timing claim; its existing P4-P1 duration gate
remains independently enforced. NASA-compatible greatest eclipse is bounded
at `10 s`. The ten-row modern catalog comparison separately bounds greatest
timing at `10 s` and signed gamma at `2e-4` Earth radii. These ceilings are not
publication precision, uncertainty estimates, or exact-model parity. Greatest
eclipse remains a separate event instant, not a seventh contact.

The physical-Moon native policy has an additional adversarial classification
gate. Across the fifteen admitted NASA catalog maxima spanning years -1801
through 2801 and all three lunar event classes, its TT greatest-eclipse residual
must remain lower than the explicitly diagnostic Earth-observer retarded-Moon
comparator. A separate static primary-authority corpus classifies all 229 NASA
catalog maxima from 1901 through 2000 on their published TD/TT basis: 83
penumbral, 65 partial, and 81 total events. NASA's Danjon/Chauvenet boundary
tables supply another public-search corpus: seven post-Gregorian events that
must remain penumbral rather than flip to partial, plus nine shallow candidates
that the Danjon model must skip entirely. The limiting 1988 Mar 03 row
additionally requires search, snapshot classification, and contact-family
identity to agree. These are century-scale classification plus selected cross-
model and boundary regressions, not Five Millennium full-catalog validation.

### 8. Required Result Labeling

Any model-selecting eclipse analysis or compatibility vessel that exposes a
greatest-eclipse instant should identify which model produced it. The generic
shape-stable event vessel inherits that identity from its explicitly named
entry point.

Minimum required distinction:

- `native`
- `nasa_compat`

Where practical, code and docs should also expose the concrete compatibility
method identifier used by the non-native path.

The exported `EclipseEvent` vessel remains unchanged. Model identity is carried
by the existing `LunarEclipseAnalysis.mode`, `.source_model`, and
`.canon_method` fields, and by the separately named NASA-compatibility vessels
and entry points. The repaired default intentionally changes compatibility
numerics plus the reported `canon_method` and `source_model`; it does not change
facade signatures, REST paths, or request/response schemas. Existing REST
routes expose native results only unless their request/response contract
already names a compatibility mode.

### 9. Non-Goals

The Moira eclipse standard does not require:

- exact reproduction of the NASA Five Millennium catalog
- choosing the mathematically best model for every external authority
- replacing `DE441` with a shorter-range ephemeris just to improve catalog fit
- inferring dense partial-footprint parity from sparse published map anchors

Moira is not trying to become a mirror of an external publication. It is trying
to maintain one coherent mathematical reality of its own.

### 10. Working Rule For Future Changes

When evaluating any proposed eclipse change, ask these questions in order:

1. Does this improve the native model's internal coherence?
2. Does it preserve the native model's explicit time and vector policy?
3. Is it really a native improvement, or is it only a catalog-compatibility
   adjustment?
4. If it is compatibility-only, can it be isolated to a compatibility layer?

If a change only improves agreement with an external catalog and weakens native
coherence, it does not belong in the native model.

### 11. Project Standard Sentence

Use this sentence when the project needs a short statement of doctrine:

> Moira computes eclipses from a single coherent DE441-based physical geometry
> in TT; compatibility outputs are translations, not truth.

