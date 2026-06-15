# Harmograms Backend Standard

Version: 0.1
Date: 2026-06-14
Status: admitted for bounded transport
Scope: public backend standard for caller-supplied harmogram vector,
intensity-spectrum, projection, and trace products

## 1. Computational Ownership

The admitted backend owner is `moira.harmograms`.

Admitted engine entrypoints:

- `point_set_harmonic_vector`
- `zero_aries_parts_harmonic_vector`
- `intensity_function_spectrum`
- `project_harmogram_strength`
- `harmogram_trace`

The REST server is a transport adapter only. It must not reimplement Fourier
components, intensity sampling, Zero-Aries parts construction, projection
terms, or trace series.

## 2. Input Ownership

P-GAP-06 accepts caller-supplied named longitudes and caller-supplied trace
samples.

It does not:

- construct natal charts
- generate dynamic ephemeris samples
- derive transit, directed, or progressed positions
- apply ayanamsa or house policy
- infer body identities from a catalogue

Every longitude is a finite ecliptic degree value owned by the caller and
normalized by the engine.

## 3. Admitted Products

Admitted products:

- point-set harmonic vectors
- Zero-Aries-parts harmonic vectors
- intensity-function spectra for admitted harmonic aspect families
- projections of source vectors onto intensity spectra
- bounded harmogram traces over explicit time samples

Trace families admitted at transport:

- `dynamic_zero_aries_parts`
- `transit_to_natal_zero_aries_parts`
- `directed_to_natal_zero_aries_parts`
- `progressed_to_natal_zero_aries_parts`

The route family exposes computation, not interpretation. Strength values,
components, phases, projection terms, and provenance are returned; judgement,
advice, recommendation language, and doctrine scoring are not.

## 4. Policy Semantics

The transport boundary admits only policy combinations that map directly to
existing engine policy vessels.

Intensity family determines orb mode:

- `cosine_bell_harmonic_aspects` -> `cosine_bell`
- `top_hat_harmonic_aspects` -> `top_hat`
- `triangular_harmonic_aspects` -> `triangular`
- `gaussian_harmonic_aspects` -> `gaussian`

Conjunction inclusion determines symmetry:

- `include_conjunction=true` -> `star_symmetric`
- `include_conjunction=false` -> `conjunction_excluded`

Trace family determines chart domain:

- `dynamic_zero_aries_parts` -> `dynamic_sky_only_trace`
- `transit_to_natal_zero_aries_parts` -> `transit_to_natal_trace`
- `directed_to_natal_zero_aries_parts` -> `directed_or_progressed_trace`
- `progressed_to_natal_zero_aries_parts` -> `directed_or_progressed_trace`

The point-set policy and intensity policy must share the same harmonic domain.

## 5. Bounds

Public transport must be synchronous and bounded.

Admitted limits:

- maximum point-set positions: `32`
- maximum relational positions per side: `24`
- maximum harmonic number: `128`
- maximum harmonic-domain width: `32`
- minimum intensity sample count: `256`
- maximum intensity sample count: `8192`
- maximum orb width: `90` degrees
- maximum trace samples: `64`
- maximum trace cells, defined as `len(samples) * len(harmonic_numbers)`: `256`

The server must reject requests that exceed these limits with the standard
validation envelope.

## 6. Response Truth

Responses must expose:

- source vector kind
- vector policy and harmonic domain
- source/body names
- harmonic-zero amplitude
- harmonic components
- intensity policy and realization mode
- projection terms and total strength
- trace sample times and series strengths
- provenance naming `moira.harmograms` and the exact engine entrypoint

Trace responses may use compact serialization, but must preserve the sample
source vector and projection terms for each sample.

## 7. Non-Goals

This standard does not admit:

- chart-backed harmogram generation
- ephemeris-backed dynamic sampling
- arbitrary user-defined intensity functions
- unbounded sweeps
- async jobs
- dense rendering meshes
- harmonic interpretation text
- recommendation language
- chart condition profiles or electional scoring

Future chart-backed or rendering surfaces require separate admission work.
