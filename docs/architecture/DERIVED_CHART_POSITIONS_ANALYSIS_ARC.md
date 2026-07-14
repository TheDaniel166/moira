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

The REST route returns the existing `AspectData` shape. Its computation truth
states that the inputs are caller-supplied ecliptic longitudes and that motion
is not computed without speeds.

## 3. REST Composition And Compatibility Boundary

- The standalone route remains available for arbitrary position-owned
  products.
- `/v1/composite/chart` and `/v1/davison/chart` now return an additive,
  required `aspects` member using the same `AspectsFromLongitudesResponse`
  contract as the standalone route.
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
| Declination | `find_declination_aspects(...)` consumes declinations | supplied declinations or a source-owned 3D/equatorial transform | Longitude-only input is insufficient; define a separate coordinate vessel |
| Fixed stars | star positions are epoch- and frame-dependent | reference epoch/time, star catalogue identity, correction/frame policy | A composite `jd_mean` is only reference metadata until doctrine admits its use |

## 5. Future Shared Vessel

A later shared `DerivedChartAnalysisInput` may be admitted only after its
optional strata remain explicit:

- required named ecliptic longitudes and zodiac-frame identity
- optional nodes with named node policy
- optional 12-cusp house frame, ASC, MC, requested/effective system, and
  construction provenance
- optional declinations or equatorial/3D coordinates with frame provenance
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
