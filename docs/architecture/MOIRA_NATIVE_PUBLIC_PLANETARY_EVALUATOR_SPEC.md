# Moira Native Public Planetary Evaluator Spec

**Status**: NPE-1 specification
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_PUBLIC_PLANETARY_EVALUATOR.md](./MOIRA_NATIVE_PUBLIC_PLANETARY_EVALUATOR.md)
- [MOIRA_NATIVE_PLANETARY_PATH.md](./MOIRA_NATIVE_PLANETARY_PATH.md)
- [MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md](./MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md)
- [MOIRA_NATIVE_PLANETARY_RETROSPECTIVE.md](./MOIRA_NATIVE_PLANETARY_RETROSPECTIVE.md)

---

## 1. Purpose

This document executes `NPE-1`.

It freezes:

- the first admitted native public planetary product
- the exact unsupported surface around it
- the parity corpus that must govern certification

This is the contract that must exist before `NPE-2` begins.

---

## 2. Admitted Product

The first admitted native public product is:

- `all_planets_at(jd_ut, bodies=..., reader=..., apparent=True, aberration=True, grav_deflection=True, nutation=True, center='geocentric', observer_lat=None, observer_lon=None, observer_elev_m=0.0, lst_deg=None, delta_t_policy=None)`

with these additional constraints:

- output product is the current `PlanetData` map
- frame is the existing public ecliptic `PlanetData` product
- no topocentric correction is active
- no caller-supplied alternate `jd_tt` entry point is admitted at this layer
- no unsupported bodies are widened into scope

The first native evaluator is therefore a native execution path for the existing canonical apparent geocentric ecliptic chart-style planetary surface.

It is not a new API.

It is not a generalized planetary engine.

It is one admitted fast path behind one existing Moira product.

---

## 3. Product Semantics To Preserve

For the admitted product, the native route must preserve all of the following exactly in public meaning:

- body identity resolution
- use of `jd_ut` as the public time input
- default `delta_t_policy=None` behavior
- apparent pipeline semantics
- geocentric reference center
- ecliptic output interpretation
- existing `PlanetData` field meanings
- sign, sign symbol, sign degree, and retrograde behavior
- current error behavior for unsupported or disallowed modes

The evaluator is allowed to change execution location.

It is not allowed to change what the product means.

---

## 4. Explicitly Unsupported In NPE-1

The following remain outside the first native public evaluator:

- `planet_at(...)` single-body routing
- `sky_position_at(...)`
- `frame='cartesian'`
- `center='barycentric'`
- `apparent=False`
- `aberration=False`
- `grav_deflection=False`
- `nutation=False`
- any topocentric mode using `observer_lat`, `observer_lon`, or `lst_deg`
- explicit `Body.CHIRON`
- heliocentric products
- relative-body products
- any future product with non-default `delta_t_policy`

These are not denied forever.

They are simply not admitted into the first closure surface.

Unsupported combinations must continue to stay on the current Python route.

---

## 5. Body Set For First Admission

The first parity-backed admitted body set is:

- `Sun`
- `Moon`
- `Mercury`
- `Venus`
- `Mars`
- `Jupiter`
- `Saturn`
- `Uranus`
- `Neptune`
- `Pluto`

This body set matches:

- the current Phase 2 public benchmarks
- the current Horizons apparent integration coverage
- the existing public planetary performance discussion

This is the correct first scope because it closes the canonical chart bodies before widening to special bodies.

---

## 6. Python Oracle Law

For `NPE-1`, the governing parity oracle is the current Python `all_planets_at(...)` implementation in the repo `.venv`.

That means:

- native parity is first judged against Python public truth
- external engines are secondary comparison layers only
- policy divergences already accepted by doctrine are not evaluator failures

This is crucial.

The first native public evaluator must prove:

- "I execute Moira's admitted product faster"

not:

- "I approximately resemble some other engine"

For this specification, the admitted product is the multi-body chart workload.
`planet_at(...)` remains a correctness control surface outside the first native evaluator claim.

---

## 7. Parity Corpus

The parity corpus for `NPE-1` should have four layers.

### 7.1 Core public benchmark body/date slice

This is the execution-admission slice because it matches the existing workload shape:

- bodies: the ten-body canonical set above
- dates: 24 representative JDs
- date span: the same public benchmark span currently used for Phase 2 planetary workloads

Purpose:

- certify the exact workload we are trying to accelerate

### 7.2 Modern apparent validation slice

Use the existing apparent validation surface already represented by:

- [test_horizons_planet_apparent.py](../../tests/integration/test_horizons_planet_apparent.py)

This gives:

- 10 bodies
- 12 named epochs from 1900 through 2025
- explicit apparent sky-position comparison against Horizons-derived references

Purpose:

- ensure the native evaluator does not silently drift from the current public apparent doctrine

Important reading:

- this is a doctrine-facing validation layer
- it is not the primary native-parity oracle
- it remains essential because it protects against a native route that matches Python only because both drifted

### 7.3 Stress-consistency slice

Use the existing public planetary stress tests already in the repo for:

- time-neighbor stability
- broad body coverage
- public result continuity expectations

Purpose:

- ensure native execution preserves the current stability and continuity behavior of the public planetary product

### 7.4 Future-policy slice

Add or designate a named future slice specifically containing:

- Moon
- Mercury
- at least one date near `2100-01-01`
- default Moira Delta T doctrine

Purpose:

- prevent future-policy cases from being misread as evaluator defects
- ensure native execution matches current Python future-policy behavior exactly

This slice is Python-parity only.

It is not judged against an external engine when the repository already knows doctrine diverges there.

---

## 8. Tolerance Law

There are two tolerance regimes, and they must not be confused.

### 8.1 Native-to-Python parity tolerance

For the admitted product, native-to-Python parity should be treated as extremely tight.

The target should be:

- effectively machine-close for returned scalar fields

Operationally:

- longitude, latitude, distance, and speed should match to a level where any residual is attributable only to floating-point execution-order differences
- any systematic or body-dependent residual pattern is a failure until explained

This is stricter than external validation tolerance because the evaluator is not implementing a different doctrine.

It is executing the same doctrine.

### 8.2 External doctrine-facing tolerance

Existing Horizons-backed tolerances remain what they already are for the current public product.

Those thresholds are not loosened merely because the route becomes native.

The native evaluator inherits the current doctrine-facing expectations.

---

## 9. Certification Gates

The first native public evaluator may be admitted only if all of these are true.

### Gate 1: Route gate

The native route activates only for the exact admitted product and body set.

### Gate 2: Python parity gate

On the parity corpus, native and Python outputs remain within the strict native-to-Python parity tolerance.

### Gate 3: Validation inheritance gate

Existing public apparent validation slices remain green without relaxing thresholds.

### Gate 4: Explicit fallback gate

Any call outside the admitted surface continues to use the current Python route explicitly and safely.

### Gate 5: Benchmark gate

The admitted `all_planets_at(...)` workload shows a material and stable positive gain over the Python route on the current benchmark slice.

This gate is intentionally about `all_planets_at(...)`.
It does not require `planet_at(...)` to become an equally strong speed surface for `NPE-1` to count as successful.

---

## 10. Rejection Conditions

The evaluator must not be admitted if any of the following occur:

- it requires widening the public mode surface before the narrow surface is certified
- it changes `PlanetData` meaning or packaging rules
- it passes benchmark goals only by weakening correction policy
- it introduces hidden mode switching not visible from Python
- it matches Python on some bodies but drifts systematically on Moon or Mercury
- it forces the repository to explain the product through native internals rather than Python doctrine

---

## 11. Implementation Boundary For NPE-2

When `NPE-2` begins, the native evaluator should be allowed to assume only this input contract:

- one `jd_ut`
- one `jd_tt` already resolved by Python doctrine
- one explicit body list limited to the admitted set
- one explicit default-policy bundle

It should return only:

- one compact per-body payload sufficient to construct current `PlanetData` vessels

That boundary is narrow on purpose.

It keeps doctrine above the line and repetitive execution below it.

---

## 12. Final Reading

`NPE-1` means the repository now has a frozen answer to two questions:

1. what exact public planetary product is being accelerated
2. what exact corpus must prove that the acceleration still means the same thing

That is the minimum lawful start for a native public evaluator in Moira.

Without this spec, implementation would drift.

With it, `NPE-2` can begin under a clear doctrinal contract.
