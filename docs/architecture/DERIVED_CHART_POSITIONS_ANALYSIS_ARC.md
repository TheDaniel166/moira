# Derived Charts As First-Class Analysis Inputs

Version: 0.2
Date: 2026-07-14
Status: Priority 1 REST composition complete; family-specific Priority 2 design remains open

## 1. Governing Object

A derived chart may provide ecliptic positions without representing an
astronomical birth moment. Composite, harmonic, draconic, and some progressed
products therefore need analysis functions that consume supplied positions
directly instead of reconstructing a fictitious datetime and location.

The first admitted object is `LongitudeAspectAnalysis`: a validated,
deterministically ordered set of caller-supplied ecliptic longitudes evaluated
under Moira's canonical aspect definitions. It is not a `Chart`, does not claim
ephemeris provenance, and does not invent speed, retrograde, stationary,
applying, or separating truth.

## 2. Priority 1 Admission

Admitted surfaces:

- `moira.aspects.aspects_from_longitudes(...)`
- curated root and `moira.facade` exports for
  `LongitudeAspectAnalysis`, `AspectPolicy`, `find_aspects`, and
  `aspects_from_longitudes`
- `Moira.aspects_from_longitudes(...)`
- `POST /v1/aspects/from-longitudes`
- embedded `aspects` analysis in `POST /v1/composite/chart`
- embedded `aspects` analysis in `POST /v1/davison/chart`

The wrapper validates finite named inputs, normalizes all longitudes into
`[0, 360)`, sorts point names before pair construction, applies an explicit
tier and orb multiplier, optionally excludes Moira's four named node points,
and delegates detection to `find_aspects`. The existing
`moira.constants.Aspect` table remains the only default aspect-angle and orb
authority.

The REST route defaults to the existing `AspectData` shape. Its computation truth
states that the inputs are caller-supplied ecliptic longitudes and that motion
is not computed without speeds.

### Aspect strength admission

`admit_now` for the standalone supplied-longitude analysis. The read-only
`moira.aspects.aspect_strength` reducer owns geometric exactness and orb
margin for already-admitted `AspectData`. The
[aspect standard](../../wiki/02_standards/ASPECT_BACKEND_STANDARD.md)
defines the arithmetic and its positive-width domain. The existing engine
supplies the effective orb, aspect policy, and motion truth. The reduction
uses the existing bounded point and aspect sets and requires no ephemeris.

A local H32 probe with `orb_factor=5e-324` admitted an exact contact whose
allowed orb rounded to zero. The engine's geometric strength is undefined
for that window. Its orb margin remains defined as `AspectData.orb_surplus`.
Admission witnesses cover exact and boundary contacts, an interior orb,
zero-width handling, and the existing position-only response and motion
semantics.

The standalone request accepts `include_strength`. On opt-in, each event
carries the normalized exactness and the remaining margin in degrees.
Zero-width contacts carry a null exactness and a zero margin. The serializer
uses the same event order and computation truth for both responses.

### Aspect graph and harmonic-family admission

`admit_now` for the standalone supplied-longitude analysis. The read-only
`moira.aspects.build_aspect_graph` and `aspect_harmonic_profile` reducers
consume admitted `AspectData` from a single `LongitudeAspectAnalysis`.
The existing [aspect standard](../../wiki/02_standards/ASPECT_BACKEND_STANDARD.md)
defines their counts, ordering, and empty results. The normalized included
points supply graph nodes, including isolates. Each admitted aspect is an
edge, including distinct aspects on the same pair. Node aspect-name counts
and chart/body harmonic-family counts follow their respective engine vessels.
The reducers are kernel-free and fit the existing synchronous point and
aspect bounds. The pattern condition network follows its own engine contract.

The geometry witness uses six retained points, one excluded node, a
three-point component, a two-point component, and an isolate. At tier 0
and an orb factor of 0.5, it admits two conjunctions and two squares.
Additional witnesses cover parallel optional aspects, a completed empty
profile, and equality with the existing contact and strength responses.

The standalone request accepts `include_graph_profile`. It returns
`aspect_graph` and `harmonic_profile` together and can also request strength.
Graph edge and incidence arrays are zero-based references to the returned
`events`. This preserves event order and keeps the existing orb and motion
evidence attached to each edge without duplicating aspect records. Graph
isolates are singleton components. The harmonic profile contains chart-wide
counts and per-body counts for points with at least one admitted aspect.

## 3. REST Composition And Compatibility Boundary

- The standalone route remains available for arbitrary position-owned
  products.
- `/v1/composite/chart` and `/v1/davison/chart` now return an additive,
  required `aspects` member using the same `AspectsFromLongitudesResponse`
  contract as the standalone route's default response.
- The existing relationship request fields `tier`, `orb_factor`, and
  `include_nodes` govern the embedded analysis. Their omitted or null values
  resolve explicitly to tier `1`, orb factor `1.0`, and node inclusion.
- `Moira.aspects(chart, ...)` now accepts position-only chart-like objects such
  as `CompositeChart`; it uses speeds only when the object actually supplies a
  callable `speeds()` method.
- Midpoint-composite house truth now fills the existing `house_system` and
  `composite_mc` fields when a common source house system and midpoint MC
  exist. `reference_latitude` and `composite_armc` remain null because the pure
  midpoint method does not use a reference-place ARMC construction.
- Composite and Davison retain their distinct chart vessels while sharing the
  same nested aspect-analysis contract. Website consumers no longer need to
  extract longitudes and orchestrate a second REST request.

## 4. Priority 2 Capability Matrix

The remaining analysis families do not share one lawful input minimum.
"Longitudes plus cusps" must not become a hidden substitute for missing
astronomical or doctrinal inputs.

| Family | Current engine truth | Minimum derived-chart input | Next transport decision |
|---|---|---|---|
| Midpoints | `calculate_midpoints(...)` already consumes a longitude map | longitudes; explicit planet-set policy | Admit a positions-in route without rebuilding a natal chart |
| Antiscia | contact functions already consume longitude maps | longitudes; explicit orb | Admit a map-level route or reuse existing direct primitives |
| Essential dignities | `calculate_dignities(...)` consumes planet records | longitudes plus explicit zodiac/dignity policy | Separate essential-only truth from unavailable accidental conditions |
| Accidental dignities | existing service expects houses and motion flags | longitudes, house placements/cusps, explicit motion availability | Preserve `unknown` where speed, sect, or other conditions are absent |
| Lots | `calculate_lots(...)` already consumes positions and house cusps | named positions, 12 cusps, explicit sect, optional source dependencies | Never infer sect or prenatal dependencies from a synthetic moment |
| House placement | assignment is geometric over longitude and cusps | longitudes, complete cusp frame, effective system provenance | Admit as a reusable derived-house-frame product |
| Lunar mansions | tropical map functions already consume longitudes | longitudes; explicit tropical variant | Sidereal variants additionally require a reference JD and ayanamsa policy |
| Declination | `moira.declination_aspects` owns normalized analysis plus an instantaneous signed-motion witness | supplied declinations; declination rates are additionally required for applying/separating truth | Admitted at `POST /v1/aspects/from-declinations` and `POST /v1/aspects/declination-motion-witness`; longitude-only input remains insufficient |
| Fixed stars | star positions are epoch- and frame-dependent | reference epoch/time, star catalogue identity, correction/frame policy | A composite `jd_mean` is only reference metadata until doctrine admits its use |

## 5. Future Shared Vessel

A later shared `DerivedChartAnalysisInput` may be admitted only after its
optional strata remain explicit:

- required named ecliptic longitudes and zodiac-frame identity
- optional nodes with named node policy
- optional 12-cusp house frame, ASC, MC, requested/effective system, and
  construction provenance
- optional declinations or equatorial coordinates with frame provenance;
  these describe a direction on the celestial sphere, not full distance-aware
  Cartesian 3D geometry
- optional speeds with a declared derivation source
- optional reference JD whose role is named (`physical_moment`,
  `catalog_epoch_reference`, or another admitted meaning)
- explicit sect rather than a fabricated sunrise-based inference

Consumers must be able to distinguish "not supplied", "not computable", and
"not applicable". A shared envelope is an assembly contract, not permission
for every analytical family to consume every partial input.

## 6. Validation Covenant

Priority 1 is proven by:

- the 355°/5° wrap case producing a 10° separation
- inclusive admission at the exact applied orb boundary and rejection just
  outside it
- deterministic name ordering and normalized input echo
- explicit known-node filtering
- `applying=None` and `motion_semantics=not_computed_without_speeds`
- facade delegation and REST response parity with the engine object
- OpenAPI-required embedded `aspects` fields on composite and Davison
- policy propagation and embedded analysis for both composite methods and all
  five Davison methods

These are engine-doctrine regression and geometric-invariant checks. They do
not constitute empirical validation of astrological interpretation.
