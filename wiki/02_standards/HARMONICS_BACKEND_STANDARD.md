# Harmonics Backend Standard

Version: 0.1
Date: 2026-06-13
Status: backend standard for Phase 12 evaluation

## Scope

This standard governs the harmonic-analysis engine surface:

- `moira.harmonics`

It covers:

- direct harmonic chart projection
- age-harmonic projection
- harmonic conjunction detection
- harmonic pattern scoring
- harmonic series sweeps
- natal aspect decoding as harmonic conjunctions
- cross-chart composite harmonic conjunctions
- vibrational fingerprint summaries
- the `HARMONIC_PRESETS` catalogue

It does not govern:

- `moira.harmograms`
- ordinary aspect doctrine
- chart construction
- transit, progression, or event search
- interpretive narrative text

## Authority And Provenance

The engine documents the harmonic tradition through:

- John Addey, *Harmonics in Astrology*
- David Hamblin, *Harmonic Charts*
- David Cochrane, harmonic pattern and vibrational astrology materials

The computational core is arithmetic, not ephemeris work. It consumes named
ecliptic longitudes supplied by a caller and projects them through:

```text
harmonic_longitude = (natal_longitude * harmonic) mod 360
```

The backend owns the harmonic transformation and derived analysis over supplied
longitudes. It does not own the astronomical derivation of those input
longitudes.

## Governing Objects

The admitted backend objects are:

- `HarmonicPosition`
- `HarmonicConjunction`
- `HarmonicPatternScore`
- `HarmonicSweepEntry`
- `HarmonicAspect`
- `VibrationFingerprint`
- `HarmonicsService`

The admitted constants are:

- `HARMONIC_PRESETS`

The preset catalogue is descriptive. It is not a transport permission to expose
unbounded sweeps or interpretive claims.

## Admitted Computations

The current backend admits:

- `calculate_harmonic(planet_longitudes, harmonic)`
- `age_harmonic(planet_longitudes, jd_birth, jd_now)`
- `harmonic_conjunctions(planet_longitudes, harmonic, orb=1.0)`
- `harmonic_pattern_score(planet_longitudes, harmonic, orb=1.0)`
- `harmonic_sweep(planet_longitudes, max_harmonic=32, orb=1.0)`
- `harmonic_aspects(planet_longitudes, orb=1.0, max_harmonic=32)`
- `composite_harmonic(lons_a, lons_b, harmonic, orb=1.0, label_a="A", label_b="B")`
- `vibrational_fingerprint(planet_longitudes, max_harmonic=32, orb=1.0)`

These functions are pure computations over dictionaries of body names and
longitudes. No kernel, location, house, ayanamsa, or time-zone state is owned by
this module.

## Required Transport Invariants

Any REST transport for harmonics must preserve:

- requested harmonic number or harmonic range
- whether the harmonic value is an integer harmonic or an age-derived decimal
  harmonic
- input body names as provided, plus normalized result body labels
- input longitudes used for each body
- computed harmonic longitudes
- result ordering rule
- orb policy for conjunction and aspect products
- maximum body count
- maximum harmonic number
- whether the result is single-chart, age-harmonic, cross-chart, sweep, or
  fingerprint
- preset name and description when a requested harmonic is in
  `HARMONIC_PRESETS`

Transport must reject:

- non-finite longitudes
- non-finite JDs for age harmonics
- `jd_now < jd_birth` for age harmonics
- empty body maps
- empty body names
- non-finite or negative orbs
- unbounded harmonic ranges
- unbounded body counts

Transport must not silently clamp user inputs in a way that hides user intent.
The engine currently clamps some harmonic values internally; public transport
must either reject invalid public values before the engine call or explicitly
report the effective harmonic used.

## Validation Requirements

The minimum backend validation corpus is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_harmonics.py -q
```

The validation corpus must continue to cover:

- `__all__` surface completeness
- formula truth for `(lon * H) mod 360`
- output longitude range `[0, 360)`
- H1 identity with natal longitudes
- age-harmonic decimal age derivation
- negative-age rejection
- conjunction orb bounds
- pattern-score cluster invariant
- sweep ordering
- aspect/conjunction dual-path equivalence
- composite chart label isolation
- vibrational fingerprint peak and total-score invariants

Route admission must add adversarial transport tests for malformed body maps,
non-finite numbers, oversized sweeps, and invalid orbs.

## REST Admission Guidance

The first admissible transport target is a direct, bounded harmonic projection
route.

Recommended sequence:

1. Direct harmonic chart projection.
2. Age harmonic projection.
3. Harmonic conjunctions for one harmonic.
4. Harmonic pattern score for one harmonic.
5. Bounded harmonic sweep.
6. Vibrational fingerprint.
7. Cross-chart composite harmonics.

Sweeps and fingerprints must be bounded separately from direct projection
because they can scale by body-pair count and harmonic range.

## Non-Goals

This standard does not admit:

- interpretive readings of harmonic meaning
- unbounded harmonic sweeps
- automatic chart construction
- transit or progression harmonic searches
- harmonic event prediction
- harmogram spectral analysis
- background jobs
- chart image rendering
- generic `/v1/special/*` exposure
