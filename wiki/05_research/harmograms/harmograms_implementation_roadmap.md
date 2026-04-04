# Harmograms Implementation Roadmap

Status: implementation roadmap

Purpose:
- define the correct implementation sequence for Moira's harmograms family
- preserve the mathematical strata explicitly
- prevent premature collapse of distinct objects into one vague "harmogram"
  feature

This roadmap assumes the companion research note exists:

- [harmograms_phase0_research.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki/05_research/harmograms/harmograms_phase0_research.md)

---

## 1. Core Architectural Decision

The harmograms family is not one object.

It contains at least four distinct computational strata:

1. point-set spectrum
2. parts-derived spectrum
3. intensity-function spectrum
4. projection of one spectrum against the other

Only after these are explicit should Moira expose a time-domain harmogram
trace.

Therefore the roadmap is spectrum-first, trace-later.

---

## 2. Governing Implementation Law

Moira must preserve the distinction between:
- the chart's point-set harmonic vector
- the parts-from-zero-Aries harmonic vector
- the Fourier spectrum of the intensity function
- the projected scalar strength obtained from them

Moira must not collapse these into one opaque score.

Visibility is mandatory.

### 2.1 Identity vs approximation

Moira must keep three categories distinct at all times:

1. exact algebraic identity
2. exact numerical computation under a finite closed form
3. approximation by truncated Fourier terms

This distinction is mandatory.

Later phases must not silently treat:
- a truncated spectral projection
- a finite-harmonic partial sum
- a numerically convenient closed-form reduction

as if it were the unrestricted theoretical object.

Any public or internal vessel that depends on truncation must carry that fact
explicitly in policy or metadata.

### 2.2 Policy immutability

All doctrine forks in this subsystem must be expressed through immutable policy
objects.

This includes, but is not limited to:
- pair construction mode
- self-pair inclusion
- conjunction inclusion
- orb law
- orb scaling law
- normalization mode
- harmonic domain

Policy must not be introduced as:
- ambient module state
- mutable vessel fields
- ad hoc booleans passed independently to multiple constructors

The required pattern is:
- immutable policy object supplied to the computation surface
- computation resolves under that policy
- resulting vessel stores the exact resolved policy that governed its
  construction

This is necessary to keep doctrine inspection, equality, and cross-object
comparison honest.

---

## 3. Phase H1 — Spectral Foundations

Goal:
- freeze the spectral substrate cleanly

Deliverables:

### H1.1 Point-set vessel

Implement a typed vessel for the harmonic vector of a point set:

- `PointSetHarmonicVector`
- one component per harmonic
- amplitude
- phase
- harmonic zero
- policy metadata
- harmonic domain metadata

This is the spectrum of the chart points themselves.

The vessel must carry its admitted harmonic index domain explicitly.
It is not sufficient for this to live ambiently in policy alone.

Two vectors with different admitted harmonic domains must not be treated as
structurally interchangeable without an explicit reconciliation rule.

### H1.2 Parts-from-zero-Aries construction

Implement the explicit pair-derived set:

- `parts_from_zero_aries(...)`

This must preserve doctrine forks explicitly:
- ordered pairs vs unordered pairs
- self-pairs included vs excluded

This is not a helper detail.
It is a constitutional mathematical object.

### H1.3 Parts-set vessel

Implement a typed vessel for the harmonic vector of the parts-derived set:

- preferred name: `ZeroAriesPartsHarmonicVector`

`PartsSetHarmonicVector` is acceptable internally, but the explicit
zero-Aries name is clearer and less likely to be confused with arbitrary
derived point-set families.

This should preserve:
- source point count
- resulting part count
- pair construction mode
- self-pair inclusion mode
- spectral coordinates
- harmonic domain metadata

### H1.4 Algebra relation tests

Add explicit tests for the Garcia relation:

- when self-pairs are included, the parts-set spectrum preserves the
  amplitude-squared relation described in the source
- when self-pairs are excluded, the exact identity no longer holds

This is a crucial doctrinal branch and must be tested directly.

### H1.5 Direct tally oracle

Add a non-public direct-tally route for validation:

- one route computes strength by direct geometric tally in the circle
- one route computes strength by spectral/projection machinery

This direct route may remain private or test-only.

It exists to validate the mathematical bridge, not to widen the public API.

### H1.6 Harmonic domain invariants

The subsystem must define a first-class notion of harmonic index domain.

At minimum, each spectral vessel should preserve:
- `harmonic_start`
- `harmonic_stop`
or an equivalent closed integer domain object

Projection logic in later phases must fail loudly if source spectra live on
incompatible harmonic domains and no explicit truncation/intersection rule has
been declared.

### H1.7 Public surface

At the end of H1, Moira should expose only spectral objects and construction
functions.

Do not expose a harmogram trace yet.

---

## 4. Phase H2 — Intensity Function Doctrine

Goal:
- formalize the second spectral family: the intensity function itself

Deliverables:

### H2.1 Intensity policy

Introduce:

```python
HarmogramIntensityPolicy
    family
    include_conjunction
    orb_mode
    orb_scaling_mode
    symmetry_mode
    normalization_mode
    max_harmonic
```

This policy must preserve:
- conjunction included or excluded
- harmonic orb scaling law
- whether the function has star symmetry
- normalization semantics

### H2.2 Intensity spectrum vessel

Implement:

- `IntensityFunctionSpectrum`

This should preserve:
- exact immutable policy instance used for construction
- Fourier coefficient amplitudes
- Fourier coefficient phase/sign law
- normalization basis
- policy metadata

Conjunction inclusion belongs here.

It is an intensity-function doctrine fork, not a generic harmonic-vector fork.
It must therefore live on the immutable intensity policy object and be carried
forward by all downstream intensity-spectrum and projection vessels.

### H2.3 Admitted initial family

Freeze one initial intensity family only.

Recommended first freeze:
- one symmetric family
- one explicit orb law
- one explicit normalization rule

Reason:
- symmetric families admit the clean Parseval-style reduction
- this keeps the first bridge mathematically legible

### H2.4 Source-safe conjunction fork

Conjunction inclusion must be explicit and tested.

The literature makes clear this is not a decorative setting.
It changes:
- the intensity spectrum
- the admissible subharmonics
- the simplicity or distortion of the spectral representation

---

## 5. Phase H3 — Projection Layer

Goal:
- compute harmogram strength as an explicit projection, not a hidden score

Deliverables:

### H3.1 Projection vessel

Implement:

- `HarmogramProjection`

This should preserve:
- source spectral vessel
- intensity spectrum identity
- total projected strength
- contributing harmonic terms
- normalization basis
- whether the result is exact, closed-form finite, or truncated

### H3.2 Parseval projection surface

Implement:

- `project_harmogram_strength(...)`

This should support:
- the symmetric-family reduction
- sign handling for 180-degree-phase coefficients where applicable
- exact accounting of term-zero behavior
- explicit harmonic-domain agreement checks
- explicit truncation metadata when partial sums are used

### H3.3 K&O correspondence mode

If Moira later exposes a Kollerstrom & O'Neill correspondence mode, it must
be explicit.

The Garcia paper notes that to reproduce a K&O-style tally from the Parseval
side, one must:
- add sufficiently many Fourier terms
- treat term zero correctly
- adjust for self-pair treatment

That correspondence should never be implied silently.

### H3.4 Validation

At this phase, validation should include:
- synthetic exact symmetries
- pair/self-pair adjustment cases
- projection equality between direct tally and Parseval-style routes for the
  admitted family
- explicit divergence tests between exact and truncated projections where
  truncation is admitted

---

## 6. Phase H4 — Time-Domain Harmogram Surface

Goal:
- expose the actual trace object only after the spectral bridge is explicit

Deliverables:

### H4.1 Trace policy

Introduce:

```python
HarmogramPolicy
    point_set_policy
    parts_policy
    intensity_policy
    sampling_policy
    output_mode
```

### H4.2 Time trace vessel

Implement:

- `HarmogramTrace`

This should preserve:
- interval definition
- sample times
- one trace per admitted number
- governing policy
- whether the output is full-spectrum, single-harmonic, or selected-harmonic

### H4.3 Sampling policy

Sampling policy must be explicit:
- sample count
- fixed step vs adaptive step
- interpolation policy if any

### H4.4 Scope limit

Do not blend:
- sky-only traces
- natal-against-transit traces
- pair-only traces

Each trace family must be named explicitly.

### H4.5 Chart-domain taxonomy

The subsystem should name its chart/trace taxonomy explicitly.

Minimum taxonomy:
- static chart strength
- dynamic sky-only trace
- transit-to-natal trace
- directed/progressed trace
- single-harmonic trace
- multi-harmonic family trace

These are not interchangeable and should not be allowed to drift together
under one convenience label.

---

## 7. Phase H5 — Comparative and Research Surfaces

Goal:
- add comparative/research tooling only after the core mathematical family is
  frozen

Possible deliverables:
- compare two intensity families
- compare conjunction-included vs conjunction-excluded spectra
- inspect dominant harmonic contributors
- derive inferred intensity spectra from a corpus

This phase should remain research-facing, not public-facade-first.

---

## 8. Explicit Deferred Frontiers

These should remain deferred until the preceding phases are stable:
- interpretive "number meaning" overlays
- blended or averaged doctrine presets
- auto-selection of intensity family from data
- collapsing point-set and parts-set vectors into one vessel
- collapsing spectral projection and time-trace output into one API

---

## 9. Recommended Initial Public Shape

The recommended public order is:

1. `point_set_harmonic_vector(...)`
2. `parts_from_zero_aries(...)`
3. `parts_set_harmonic_vector(...)`
4. `intensity_function_spectrum(...)`
5. `project_harmogram_strength(...)`
6. only later `harmogram_trace(...)`

This order mirrors the mathematics.

---

## 10. Validation Program

Minimum validation gates per phase:

### H1
- exact vector identities for synthetic charts
- self-pair inclusion/exclusion divergence
- contiguous harmonic indexing

### H2
- spectrum symmetry tests
- conjunction-inclusion divergence
- orb-scaling sensitivity

### H3
- direct tally vs projection correspondence
- term-zero accounting
- normalization invariants

### H4
- deterministic trace reproduction
- sensitivity to sampling policy
- stable behavior on trivial and symmetric cases

---

## 11. Immediate Next Move

The immediate next move should be:

1. revise the current narrow Phase 1 implementation so it no longer implies
   that the point-set harmonic vector alone is the whole subsystem
2. add the parts-from-zero-Aries construction and its spectral vessel
3. freeze the spectral boundary before any trace API is added

That is the smallest correct path forward.
