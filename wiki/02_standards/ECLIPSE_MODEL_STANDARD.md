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
- `UT` is a reporting layer, not an optimization layer.
- Event definitions must not be stated in `UT` space except as final user-facing
  output.

### 3. Lunar Greatest Eclipse Definition

For the native lunar model, greatest eclipse is defined as:

- the minimum perpendicular distance from the Moon's center to the Earth's
  umbral-shadow axis

This scalar is the primary event objective for native lunar event centering.
Catalog-specific proxies may exist in compatibility layers, but they do not
replace the native definition.

### 4. Native Geometry Policy

The native eclipse model must use one explicit and internally consistent vector
policy. For the current Moira standard:

- ephemeris basis: `DE441`
- event-solving timescale: `TT`
- shadow-axis definition: physical Earth-Sun geometry used by the native model
- lunar umbral centering: the current native retarded-Moon policy

This choice is not justified by NASA-catalog agreement. It is justified by
internal coherence with Moira's own physical event model.

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

### 8. Required Result Labeling

Any public-facing eclipse result that exposes a greatest-eclipse instant should
identify which model produced it.

Minimum required distinction:

- `native`
- `nasa_compat`

Where practical, code and docs should also expose the concrete compatibility
method identifier used by the non-native path.

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

