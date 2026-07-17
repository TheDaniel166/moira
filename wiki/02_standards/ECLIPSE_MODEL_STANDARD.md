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

The native eclipse model must use one explicit and internally consistent vector
policy. For the current Moira standard:

- ephemeris basis: `DE441`
- event-solving timescale: `TT`
- shadow-axis definition: the line through the DE441 Sun and Moon
  center-of-mass states on one Earth-reception light cone
- lunar umbral centering: the current native retarded-Moon policy
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

A partial solar eclipse has no umbral or antumbral central line. The current
shape-stable `SolarEclipsePath` contract represents that product as the single
solved point of greatest eclipse with zero central width and zero central
duration. It does not claim to encode the northern/southern penumbral limits or
a complete partial-eclipse visibility footprint.

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
and entry points. Existing REST routes expose native results only unless their
request/response contract already names a compatibility mode.

### 9. Non-Goals

The Moira eclipse standard does not require:

- exact reproduction of the NASA Five Millennium catalog
- choosing the mathematically best model for every external authority
- replacing `DE441` with a shorter-range ephemeris just to improve catalog fit

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

