# Moira 4.2.0 — Electional Doctrine and Derived-Chart Analysis

Moira 4.2.0 admits the first bounded Western electional doctrine profile,
makes supplied chart positions first-class analysis inputs, and corrects
Davison planetary time-scale handling. It also strengthens native SPK coverage
law, asteroid observation-arc provenance, Gauquelin singularity semantics, and
progressed-integration mesh validation.

## Highlights

### Western electional doctrine

The new `ramesey_moon_condition_v1` profile evaluates William Ramesey's ten
impediments of the Moon from *Astrologia Restaurata*, Book III, Chapter II.
Each result preserves the named rule, observed chart evidence, trigger state,
and the explicit policies required to turn historical language into a bounded
computational object.

Public access is available through:

- `moira.western_electional.compute_ramesey_moon_condition(...)`
- `Moira.ramesey_moon_condition_at(...)`
- `POST /v1/electional/western/ramesey-moon-condition`

This is a single-moment condition evaluation. It is not a complete election,
generic search predicate, auspiciousness score, or recommendation engine.

### Derived charts as first-class analysis inputs

Composite, Davison, harmonic, draconic, and other derived products may own
ecliptic positions without representing an astronomical birth moment. Version
4.2.0 therefore adds a position-in aspect surface that consumes named
longitudes directly instead of reconstructing a fictitious datetime and
location:

- `moira.aspects.aspects_from_longitudes(...)`
- `Moira.aspects_from_longitudes(...)`
- `POST /v1/aspects/from-longitudes`

`LongitudeAspectAnalysis` records normalized, deterministically ordered input
positions and delegates aspect detection to Moira's canonical aspect table.
Without supplied speeds, it explicitly reports that motion semantics were not
computed: no retrograde, stationary, applying, or separating truth is
invented.

The existing composite and Davison REST envelopes remain unchanged and
distinct. Midpoint-composite truth now fills its existing common house-system
and midpoint-MC fields when both source frames lawfully provide them.

### Davison time-scale correction

All five Davison variants now cast their planets at the same declared instant
as the chart vessel. The former implementation converted the midpoint to TT
before calling a planetary function whose contract accepts UT1 and performs
its own TT conversion. That advanced planetary evaluation by approximately 58
seconds while leaving nodes, houses, obliquity, Delta T, and metadata at the
declared instant.

The corrected paths are:

- midpoint-location Davison;
- uncorrected arithmetic-location Davison;
- reference-place Davison;
- spherical-midpoint Davison;
- corrected-time Davison.

Request and response shapes are unchanged. Planetary longitudes now agree with
a canonical chart cast at each result's declared used instant.

### Gauquelin correctness and explicit horizon policy

The Gauquelin engine now defaults to a 0-degree geometric center crossing. The
available primary sources establish rise-anchored sectoring but do not establish
a hidden refraction or limb threshold, so nonzero thresholds are caller-owned
policy.

Bodies without an ordinary rise/set pair no longer receive fabricated sectors.
Circumpolar, never-rising, and horizon-coincident results expose their status
and leave `sector`, `zone`, `diurnal_position`, and `degree_in_sector`
undefined.

Migration notes:

- callers that require the former threshold must pass
  `horizon_altitude=-0.5667` explicitly;
- REST consumers must accept nullable sector-derived fields for non-rising
  geometries.

### Native SPK and asteroid-catalog strengthening

Native SPK segment evaluation now carries descriptor coverage bounds and
rejects epochs outside the admitted interval. Adversarial tests exercise the
Python/native boundary and prevent a segment from silently evaluating beyond
its source coverage.

The unified asteroid builder now respects observation-arc limits for bodies
whose JPL solutions do not lawfully support the catalog's nominal full span.
The packaged manifest and master metadata record those exceptions, cached
records are checked against current solution identity, and transient JPL
responses use bounded retry handling.

Planetary reduction visibility is also promoted through the curated public
API with `PlanetReductionStage`, `PlanetReductionBreakdown`, and
`planet_reduction_breakdown_at`.

## Compatibility

This minor release classifies the changed Gauquelin, progressed-integration,
and Davison behavior as correctness corrections:

- Gauquelin's default horizon changes to 0 degrees and sector-derived fields
  may be null when rise/set geometry is undefined;
- progressed-integration requests require `max_samples >= 3`;
- Davison planetary longitudes change to the correctly cast instant.

The Western electional and derived-position analysis surfaces are additive.
No existing composite or Davison REST route or envelope was removed or renamed.

## Validation

Release evidence uses the project `.venv` on Python 3.14 with downloads
disabled and strict known-issue expiry. The validation corpus includes:

- DE441-backed Western electional regression cases, source-owned rule
  invariants, facade delegation, REST serialization, and invalid-policy tests;
- longitude wrap, exact-orb boundary, deterministic ordering, node-filtering,
  absent-motion, facade, and REST tests for position-only aspect analysis;
- all five Davison variants compared with canonical chart casts at their
  declared used instants;
- Gauquelin horizon singularities, exact sector boundaries, immutable result
  vessels, and REST nullable-field behavior;
- native DAF/SPK descriptor coverage, ERFA-facing astronomy slices, asteroid
  catalog construction, manifest provenance, and release-surface consistency.

These checks establish regression, invariant, and named authority evidence
only for their stated products. They do not turn electional rule evaluation or
Gauquelin sector classification into empirical proof of astrological claims.
