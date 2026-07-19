# Harmonics Backend Standard

Version: 0.2
Date: 2026-07-19
Status: admitted backend standard

## Scope

This standard governs the caller-supplied-longitude harmonic surfaces:

- `moira.harmonics`
- `moira.harmonic_transits`

It covers:

- direct harmonic chart projection
- age-harmonic projection
- harmonic conjunction detection and pattern scoring
- harmonic series sweeps and vibrational fingerprints
- natal aspect decoding as harmonic conjunctions
- cross-chart composite harmonic conjunctions
- explicit harmonic-orb scaling policy and resolved provenance
- sampled mixed-origin harmonic transit configurations
- the `HARMONIC_PRESETS` catalogue

It does not govern `moira.harmograms`, ordinary aspect doctrine, chart or
ephemeris construction, progression search, interpretive narrative, or exact
harmonic transit ingress/egress solving.

## Authority And Provenance

The engine documents the harmonic tradition through:

- John Addey, *Harmonics in Astrology*, Chapter 14
- David Hamblin, *Harmonic Charts*
- David Cochrane's harmonic-pattern and vibrational-astrology materials

The VA-informed forecast boundary additionally records:

- [Sirius: Methods for Vibrational Astrology](https://www.astrosoftware.com/cpnew/m/software/sirius/methods_vibrational_astrology.html)
- [Gisele Terry, Forecasting with Vibrational Astrology, UAC 2018 handout](https://hosted-files.sched.co/uac2018/f2/handout%20for%20Forecasting%20with%20Vibrational%20Astrology.pdf)

These sources inform the admitted mixed-origin cardinalities and the idea of
activating natal harmonic configurations. They do not establish numerical
parity with Sirius or supply Moira's sampled-window geometry.

The computational core is arithmetic over longitudes supplied by a caller. It
does not own the astronomical derivation of those longitudes.

## Governing Harmonic Transformation

Every input longitude is first reduced to Moira's canonical zero-Aries branch:

```text
lambda_0 = longitude mod 360, where lambda_0 is in [0, 360)
lambda_H = (lambda_0 * H) mod 360
```

`H` must be a positive finite real number on a single-harmonic surface. An
integer `H` is the ordinary cyclic harmonic projection. A non-integer `H` is
an explicitly zero-Aries-anchored continuous multiplier: it is evaluated from
the canonical `[0, 360)` representative and must not be described as an
origin-free circle endomorphism.

This branch rule makes `H=5.5` a first-class value. The engine must not coerce,
truncate, round, or clamp it to `H=5`.

Integer-range products remain integer by doctrine:

- `harmonic_sweep`
- `harmonic_aspects`
- `vibrational_fingerprint`
- `MixedOriginHarmonicTransitForecastPolicy.harmonics`

`age_harmonic` remains the distinct time-derived surface whose multiplier is
`(jd_now - jd_birth) / tropical_year`, subject to its established `1e-6`
positive floor at the exact birth instant. It is not an adapter for arbitrary
fractional harmonic requests.

## Harmonic-Orb Doctrine

`HarmonicOrbPolicy` is the immutable, provenance-bearing conjunction-orb
policy. The admitted scaling mode is
`HarmonicOrbScalingMode.ADDEY_INVERSE_HARMONIC`, expressed as:

```text
O_H = O_1 / H
```

`reference_orb_deg` is the caller-configurable H1 reference `O_1`. Resolution
for one harmonic produces `HarmonicOrbTruth` with two deliberately distinct
limits:

- `projected_orb_limit_deg = O_1`: the threshold applied after projection on
  the 360-degree harmonic chart
- `source_orb_limit_deg = O_1 / H`: the locally equivalent allowance on the
  source zodiacal circle

The existing `orb` argument and REST field continue to mean the projected
threshold/H1 reference. Applying `O_1/H` again on the projected chart would
produce an unintended `1/H^2` source scaling and is prohibited.

For non-integer `H`, the same arithmetic relation is exposed with
`noninteger_extension=true` (`continuous_extension=true` over REST). That is
an explicit Moira continuous extension of the cited integer-harmonic rule, not
an attribution of fractional doctrine to the source.

Callers may use the legacy `orb` argument or `orb_policy`, but not both in the
same engine call. The default reference orb remains `1.0` degree.

## Governing Objects

The admitted `moira.harmonics` objects are:

- `HarmonicPosition`
- `HarmonicConjunction`
- `HarmonicPatternScore`
- `HarmonicSweepEntry`
- `HarmonicAspect`
- `VibrationFingerprint`
- `HarmonicOrbScalingMode`
- `HarmonicOrbPolicy`
- `HarmonicOrbTruth`
- `HarmonicsService`
- `HARMONIC_PRESETS`

The admitted `moira.harmonic_transits` objects are:

- `HarmonicTransitMemberOrigin`
- `MixedOriginHarmonicTransitMode`
- `HarmonicTransitSample`
- `HarmonicTransitMember`
- `HarmonicTransitPatternSample`
- `HarmonicTransitWindow`
- `HarmonicTransitForecast`
- `MixedOriginHarmonicTransitForecastPolicy`

The preset catalogue is descriptive. It is not permission to expose unbounded
sweeps or interpretive claims.

## Admitted Computations

The harmonic backend admits:

- `calculate_harmonic(planet_longitudes, harmonic)`
- `age_harmonic(planet_longitudes, jd_birth, jd_now)`
- `harmonic_conjunctions(..., harmonic, orb=None, *, orb_policy=None)`
- `harmonic_pattern_score(..., harmonic, orb=None, *, orb_policy=None)`
- `harmonic_sweep(..., max_harmonic=32, orb=None, *, orb_policy=None)`
- `harmonic_aspects(..., orb=None, max_harmonic=32, *, orb_policy=None)`
- `composite_harmonic(..., harmonic, orb=None, ..., *, orb_policy=None)`
- `vibrational_fingerprint(..., max_harmonic=32, orb=None, *, orb_policy=None)`
- `mixed_origin_harmonic_transit_forecast(natal_longitudes, transit_samples, policy)`

All are pure computations over caller-owned longitudes. They do not own a
kernel, location, house, ayanamsa, time zone, chart builder, or ephemeris.

The transit forecast is governed separately by
`HARMONIC_TRANSIT_FORECAST_STANDARD.md`.

## Required Transport Invariants

Any REST transport for harmonics must preserve:

- requested and effective harmonic values without integer truncation
- harmonic kind: `integer`, `continuous_multiplier`, `age_decimal`,
  `range_sweep`, or the forecast family's explicit provenance
- the zero-Aries `[0, 360)` input branch and projection formula
- caller-supplied longitude ownership, the normalized source longitude used,
  and engine-normalized result body labels
- computed harmonic longitudes and deterministic ordering
- the H1 reference orb, projected limit, source-circle limit, scaling mode,
  formula, authority, and continuous-extension truth where applicable
- maximum body, sample, harmonic, and work bounds for the requested product
- preset name and description only for integer harmonics in
  `HARMONIC_PRESETS`

Transport must reject non-finite values, empty or duplicate-trimmed body
identity, invalid harmonics, invalid policy selectors, unbounded
ranges, and requests above the product-specific work limits. It must not
silently clamp or coerce user intent.

## Validation Requirements

The focused backend corpus is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_harmonics.py tests\unit\test_harmonic_transits.py -q
```

It must continue to cover:

- public surface completeness
- formula truth and output range
- fractional `H` distinct from its truncated integer
- zero-Aries canonical-branch equivalence for out-of-range input longitudes
- positive-finite-real harmonic rejection policy
- projected/source orb-limit equivalence and no double scaling
- integer range doctrine for sweep, aspects, fingerprint, and forecast
- conjunction, cluster, composite-label, and fingerprint invariants
- immutable forecast policy, input maps, and result vessels
- complete-three-member minimum-circular-arc admission
- both mixed-origin modes
- sampled window splitting, peak selection, duration filtering, and provenance

REST admission additionally requires adversarial bounds, OpenAPI float-vs-int
schema, malformed identity, and route serialization coverage.

## Non-Goals

This standard does not admit:

- interpretive readings of harmonic meaning
- unbounded harmonic sweeps or forecast work
- automatic chart or ephemeris construction
- progression harmonic search
- interpolation between supplied transit samples
- exact transit ingress, egress, or event-time claims
- numerical or feature parity with Sirius
- harmogram spectral analysis
- background jobs or chart rendering
- generic `/v1/special/*` exposure
