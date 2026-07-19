# Harmonic Transit Forecast Standard

Version: 0.1
Date: 2026-07-19
Status: admitted sampled forecast standard

## Scope

This standard governs `moira.harmonic_transits` and the additive
`POST /v1/harmonics/transit-forecast` transport. It defines one bounded
product: sampled mixed-origin, three-member harmonic configurations over
caller-supplied natal longitudes and timestamped transit-longitude samples.

This is a VA-informed forecast surface. It is not a claim of numerical,
algorithmic, ranking, or feature parity with Sirius.

## Source Boundary

The admitted family is informed by two published descriptions:

- [Sirius: Methods for Vibrational Astrology](https://www.astrosoftware.com/cpnew/m/software/sirius/methods_vibrational_astrology.html),
  which describes forecast patterns containing exactly one transit and two
  natal points or two transits and one natal point, with orb and duration
  controls.
- [Gisele Terry, Forecasting with Vibrational Astrology, UAC 2018 handout](https://hosted-files.sched.co/uac2018/f2/handout%20for%20Forecasting%20with%20Vibrational%20Astrology.pdf),
  which describes activation of natal harmonic patterns through resonance and
  harmonic synastry.

Those sources govern the broad mixed-origin product idea. They do not publish
a complete algorithm for triple admission, ranking, sampling, or defaults.
Moira therefore owns and exposes the following computational doctrine instead
of implying hidden equivalence.

## Governing Object

At each supplied sample and admitted integer harmonic `H`, Moira projects every
candidate member from the canonical zero-Aries branch:

```text
lambda_0 = longitude mod 360
lambda_H = (lambda_0 * H) mod 360
```

The only admitted cardinalities are:

- `one_transit_two_natal`: two natal members and one transit member
- `two_transits_one_natal`: one natal member and two transit members

Natal and transit identity domains remain separate. A natal `Mars` and a
transiting `Mars` are lawful distinct members because identity is the pair
`(origin, body)`.

Every candidate is a complete triple. Its `projected_spread_deg` is the
minimum circular covering arc containing all three projected positions. The
triple is admitted only when:

```text
projected_spread_deg <= projected_orb_limit_deg
```

At the floating-point boundary, admission uses an absolute `1e-12` degree
coalescence tolerance so an exact wrap-crossing arc is not rejected by binary
round-off.

Pairwise adjacency or graph connectivity is insufficient; a two-edge chain
whose complete covering arc exceeds the limit must be rejected.

`source_residual_spread_deg` equals `projected_spread_deg / H`. The resolved
orb limits come from `HarmonicOrbPolicy`: the projected limit is the configured
H1 reference orb and the local source-circle limit is that reference divided by
`H`. The projected values must never be divided by `H` a second time.

## Input Ownership And Time Semantics

The engine receives:

- one natal body-to-longitude mapping
- one strictly increasing sequence of `HarmonicTransitSample`
- one `MixedOriginHarmonicTransitForecastPolicy`

Each sample contains `jd_ut` and a complete transit body-to-longitude mapping.
Transit body identity must remain constant across the sequence; mapping order
does not define identity. All longitudes and timestamps, every adjacent
timestamp gap, and the complete timestamp span must be finite.

`jd_ut` is caller-supplied labeling. This module does not derive, convert, or
validate an astronomical time scale beyond finiteness and strict ordering. It
does not open a kernel, construct a chart, sample an ephemeris, or interpolate
positions between samples.

## Policy

`MixedOriginHarmonicTransitForecastPolicy` owns:

- `harmonics`: a non-empty, unique tuple of positive integers
- `modes`: a non-empty, unique tuple of admitted mixed-origin modes; both are
  enabled by default
- `orb_policy`: a `HarmonicOrbPolicy`
- `minimum_observed_duration_days`: non-negative sampled-duration threshold
- `maximum_sample_gap_days`: positive maximum gap permitted within one window

Forecast harmonics remain integer even though direct single-harmonic chart,
conjunction, score, and composite surfaces admit positive finite real `H`.
Fractional forecast harmonics require a separate doctrine and are not silently
borrowed from the direct continuous-multiplier surface.

## Sample And Window Semantics

`HarmonicTransitPatternSample` records one admitted complete triple at one
supplied timestamp, including member origins, source and projected longitudes,
complete projected spread, equivalent source residual, and both orb limits.

`HarmonicTransitWindow` groups observations only when all of the following are
true:

- harmonic, mode, and member identities are unchanged
- sample indices are consecutive
- timestamps advance strictly
- each time gap is at most `maximum_sample_gap_days`

The window's first and last timestamps are the first and last supplied samples
at which that triple is admitted. `observed_duration_days` is their difference.
A one-sample window therefore has observed duration zero. The minimum-duration
filter is conservative over these observed boundaries.

The peak sample is the supplied sample with the smallest complete projected
spread. Equal spreads resolve to the earliest timestamp and then the earliest
sample index. No parabola, spline, ephemeris interpolation, or root solve is
implied.

Consequently, these products are *observed windows*, not exact event windows:

- `first_sampled_jd_ut` is not an ingress instant
- `peak_sampled_jd_ut` is not an exact perfection instant
- `last_sampled_jd_ut` is not an egress instant

Sampling density and the caller's position-generation regime bound the result.

## Result And Provenance Contract

`HarmonicTransitForecast` is immutable and preserves:

- normalized defensive copies of natal and transit inputs
- the resolved policy
- deterministic natal/transit body order
- every observed window and sample
- source locators
- `input_provenance=caller_supplied_natal_longitudes_and_timestamped_transit_samples`
- `evaluation_scope=sampled_complete_mixed_origin_triples_without_interpolation`
- the explicit claim boundary: VA-informed, no Sirius parity, and no exact
  ingress or egress claim

The REST response must retain this scope and claim boundary. It must also
report the transport bounds that governed the request.

## REST Bounds

`POST /v1/harmonics/transit-forecast` admits:

- at most 12 natal bodies
- at most 12 transit bodies
- at most 512 samples
- at most 16 requested harmonic values
- harmonic values from 1 through 128
- orb from 0 through 30 projected degrees
- at most 25,000 candidate evaluations

Candidate evaluations are bounded before engine computation from the admitted
mode combinations, body counts, harmonic count, and sample count. These are
transport resource limits, not astrological doctrine.

## Validation Requirements

The minimum engine validation is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_harmonic_transits.py -q
```

The transport validation is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_harmonics_routes.py -q
```

Coverage must include both mixed-origin modes, complete-arc rejection of a
pairwise chain, same-name cross-origin identity, immutable inputs/results,
integer-harmonic enforcement, coercive-scalar rejection, non-finite and
non-advancing input rejection, finite timestamp-span enforcement,
identity consistency, window splitting, conservative duration filtering,
deterministic peak selection, work bounds, serialization, and claim-boundary
provenance.

## Non-Goals

This admission does not provide:

- ephemeris or chart generation
- automatic transit sampling
- interpolation between samples
- exact ingress, perfection, or egress solving
- fractional-H forecasting
- progressed or directed harmonic forecasting
- composites, midpoints, same-phase families, or other VA techniques
- interpretive ranking or narrative
- Sirius numerical, algorithmic, or feature parity
- background jobs or unbounded searches
