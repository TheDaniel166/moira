# Moira Native Closure Program

**Status**: Proposed closure program
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_BACKEND_ARCHITECTURE.md](./MOIRA_NATIVE_BACKEND_ARCHITECTURE.md)
- [MOIRA_NATIVE_MIGRATION_TRACKER.md](./MOIRA_NATIVE_MIGRATION_TRACKER.md)
- [MOIRA_NATIVE_PLANETARY_FINISH_PROOF.md](./MOIRA_NATIVE_PLANETARY_FINISH_PROOF.md)
- [MOIRA_PYTHON_GOVERNED_NATIVE_STRENGTHENING.md](./MOIRA_PYTHON_GOVERNED_NATIVE_STRENGTHENING.md)

---

## 1. Purpose

This document defines the program required to turn the current native-backend status matrix from mixed `Partial` states into explicit `Yes` states where justified by truth, validation, and speed.

It also defines the separate native plan for harmograms.

This is not a mandate to port everything.

It is a closure program for the surfaces that already exist in one of these states:

- implemented but not broadly integrated
- integrated but not benchmark-closed
- benchmarked only through scripts
- present in Python truth form but lacking a native mirror where batch workloads justify one

The governing law remains:

- Python reference code is canonical
- native code is admitted only after parity is explicit
- public semantics must remain unchanged
- performance claims must be artifact-backed

---

## 2. What "Yes" Means

A matrix cell may only be upgraded to `Yes` when the relevant closure condition is satisfied.

### 2.1 Integrated into Python engine = `Yes`

This means:

- the public or canonical internal Python surface calls the native path in normal execution
- fallback behavior remains explicit
- the native path is not script-only or benchmark-only

### 2.2 Parity-tested = `Yes`

This means:

- direct Python-vs-native comparison exists
- edge cases are covered
- the test names the surface being compared
- tolerances are explicit

### 2.3 Benchmarked = `Yes`

This means:

- an in-repo benchmark script exists
- a checked artifact exists under `tests/artifacts/benchmarks/`
- the artifact measures the same surface the matrix row claims to represent

### 2.4 Production-routed = `Yes`

This means:

- the path is reachable from Moira's normal engine surface
- it is not limited to audit scripts, ad hoc experiments, or direct extension calls
- the route can be validated in `.venv` without special patching

---

## 3. Current Closure Gaps

From the native status matrix, the main open categories are:

1. native primitives that exist but are not broadly routed through Python engine surfaces
2. native reader paths that are integrated but not performance-closed
3. search, eclipse, evaluator, and cartography kernels that exist mainly as script-facing or experimental surfaces
4. harmograms, whose Python mathematical substrate is already mature but whose native path does not yet exist

These must not be solved by widening claims in documentation.

They must be solved by one of:

- implementation
- integration
- parity testing
- benchmark closure
- explicit decision not to native-port a surface

---

## 4. Closure Tracks

## Track A: Dispatcher and Engine Routing Closure

Goal:
- turn native surfaces that already have stable Python equivalents into real engine routes

Target rows to convert from `Partial` or mixed status:

- dispatcher framework
- geometry / interpolation / solver primitives where a canonical Python route exists

Required actions:

1. inventory all Python truth surfaces that are already safe to route through `moira.dispatch`
2. separate scalar low-value routes from bulk high-value routes
3. route only the admitted high-value surfaces
4. add dispatcher integration tests for each admitted surface
5. record which surfaces are intentionally kept Python-only

Exit condition:

- every admitted dispatch-capable surface is either:
  - native-routed with parity and fallback tests, or
  - explicitly marked Python-only with reason

Notes:

- do not route tiny scalar helpers just to increase counts
- avoid boundary-cost regressions masquerading as progress

---

## Track B: Reader Performance Closure

Goal:
- close the gap between reader sovereignty and measured reader performance

Target rows:

- native planetary segment evaluation
- native small-body reader ownership

Current blocker:

- supported planetary native segment evaluation is functionally integrated but slower than the prior path in current checked artifacts

Required actions:

1. define the exact benchmark surface to be closed
2. separate:
   - kernel open/index cost
   - payload extraction cost
   - repeated segment evaluation cost
   - public `planet_at` and public small-body surface cost
3. reduce Python/native marshaling overhead before claiming reader-path closure
4. add a real pre-migration or comparison baseline for small-body workloads
5. update the tracker only from artifact-backed results

Exit condition:

- benchmark artifacts exist for:
  - planetary repeated segment evaluation
  - representative small-body evaluation
  - public body-position surfaces that depend on the reader
- the closure note states honestly whether the native reader path is:
  - faster
  - equal but sovereignty-justified
  - slower and therefore not yet performance-closed

Important:

- this track may end with `Integrated = Yes`, `Parity-tested = Yes`, `Benchmarked = Yes`, and `Production-routed = Yes` while performance remains below the architecture mandate
- if so, the document must say so plainly

---

## Track C: Evaluator and Search Closure

Goal:
- convert evaluator and search primitives from extension-side capability into engine-side capability

Target rows:

- persistent evaluator classes
- search pool / native event search primitives

Required actions:

1. define canonical Python wrappers over:
   - `ChebyshevEvaluator`
   - `RelativeEvaluator`
   - `TopocentricEvaluator`
   - `SearchPool`
2. keep evaluator construction policy visible in Python
3. expose only the high-value bulk-search routes that actually benefit from the native substrate
4. add parity tests against the Python search manuscript
5. record benchmarks for the exact wrapped routes rather than raw extension calls only

Exit condition:

- evaluator/search surfaces are callable from normal Python engine routes
- parity tests exist on named corpora
- benchmark artifacts exist for the same admitted surfaces

Non-goal:

- do not expose raw native classes as the public truth surface

---

## Track D: Eclipse and Event-Assembly Closure

Goal:
- move native eclipse and event kernels from script-side experiments to validated engine-side products

Target rows:

- native eclipse discovery
- search pool / native event search primitives

Required actions:

1. identify the narrowest high-value Python eclipse surfaces suitable for native routing
2. preserve semantic distinctions explicitly:
   - apparent vs geometric
   - local vs geocentric
   - contact solving vs discovery
   - nominal vs corrected products
3. compare native event discovery against current Python manuscript behavior
4. compare admitted products against existing external validation corpora where available
5. add engine-level tests that prove normal Python eclipse calls can reach the native route without semantic drift

Exit condition:

- at least one canonical eclipse/event surface is:
  - Python-truth mirrored
  - native-routed
  - parity-tested
  - benchmarked
  - semantically audited

Important:

- direct extension success is not sufficient
- audit scripts do not count as production routing

---

## Track E: Cartography Closure

Goal:
- stabilize the cartography story before deciding whether the native functions deserve `Yes`

Target row:

- cartography helpers

Current blocker:

- the repository is in flux around the Python cartography surfaces, so native existence is ahead of settled public semantics

Required actions:

1. freeze the canonical Python cartography surfaces first
2. decide which products are admitted:
   - grid sweep
   - centerline solve
   - observer quantities
   - cross-track limit bands
3. restore or replace the validation surfaces needed for those products
4. then route the admitted surfaces into native helpers
5. benchmark the engine-level call path

Exit condition:

- cartography semantics are stable
- the admitted products have parity tests
- normal Python cartography calls reach the native route where justified

---

## Track F: Documentation and Evidence Closure

Goal:
- make the tracker, architecture note, tests, and artifacts agree

Required actions:

1. every tracker performance claim must map to a checked artifact
2. every artifact must describe the actual measured surface
3. script-only experimental wins must be labeled as experimental
4. architecture notes must distinguish:
   - exists
   - integrated
   - benchmarked
   - production-routed

Exit condition:

- documentation no longer overstates native closure
- every `Yes` in the matrix can be defended from code plus artifact plus tests

---

## 5. Harmograms Native Program

## 5.1 Harmograms Baseline

Harmograms are not in the same state as the old roadmap implied.

The repository already has a substantial Python truth substrate:

- point-set harmonic vectors
- zero-Aries parts construction
- zero-Aries parts harmonic vectors
- multiple admitted intensity families
- explicit spectral projection
- multiple named trace families
- bridge builders for dynamic, transit-to-natal, directed-to-natal, and progressed-to-natal sample generation
- unit and public-API coverage

Therefore the native harmograms problem is not "invent the subsystem."

It is:

- preserve the current Python manuscript
- identify the computational hotspots
- mirror those hotspots in native code
- keep astronomical generation and doctrine policy explicit in Python

## 5.2 Harmograms Native Boundary Law

The following must remain Python-owned:

- policy objects
- trace-family taxonomy
- astronomical sample generation
- bridge assembly from charts/progressions into harmogram snapshots
- public vessel semantics

The following are admissible native targets:

- batch harmonic component accumulation
- zero-Aries parts angle generation over large sample sets
- intensity spectrum coefficient synthesis
- projection over many harmonics and many samples
- bulk trace-series evaluation for supplied snapshots

This preserves the correct order:

- astronomy in Python
- doctrine in Python
- math kernels in native code

## 5.3 Harmograms Native Phases

### HN1: Native Spectral Kernels

Goal:
- port the low-level spectral loops used by:
  - `point_set_harmonic_vector`
  - `zero_aries_parts_harmonic_vector`

Scope:

- harmonic component accumulation over supplied longitude arrays
- batch support over multiple samples

Required validation:

- exact parity against Python truth over synthetic charts
- Garcia identity tests still pass through the routed surface
- harmonic-domain mismatch rules remain Python-enforced

Exit condition:

- point-set and parts-vector compute paths can be natively evaluated from Python-owned policies and inputs

### HN2: Native Intensity Spectrum Synthesis

Goal:
- port the Fourier coefficient synthesis used by `intensity_function_spectrum`

Scope:

- cosine-bell
- top-hat
- triangular
- gaussian

Required validation:

- family-specific parity against current Python outputs
- conjunction-inclusion divergence still visible
- symmetry and domain invariants preserved

Exit condition:

- all admitted intensity families have native synthesis kernels with parity tests

### HN3: Native Projection and Trace Core

Goal:
- port the projection and repeated trace evaluation loops

Scope:

- `project_harmogram_strength`
- batch projection across many harmonics and many samples
- trace-series strength evaluation for supplied snapshots

Required validation:

- projection equality against the current Python manuscript
- trace samples still match standalone projections
- multi-family trace tests still pass unchanged at the Python public surface

Exit condition:

- trace evaluation over supplied snapshots is natively accelerated without changing vessels or policy semantics

### HN4: Engine-Facing Harmograms Routing

Goal:
- move native harmograms from hidden kernels to normal Python-owned surfaces

Scope:

- route `moira.harmograms.compute` through native kernels where available
- keep `moira.bridges.harmograms` Python-owned

Required validation:

- public API remains unchanged
- fallback behavior is explicit
- targeted benchmark artifacts exist for:
  - static spectral computation
  - intensity family synthesis
  - multi-sample trace evaluation

Exit condition:

- harmograms native row can truthfully read:
  - implementation exists = Yes
  - integrated into Python engine = Yes
  - parity-tested = Yes
  - benchmarked = Yes
  - production-routed = Yes

## 5.4 Harmograms Non-Goals

This program does not authorize:

- native ownership of astrology doctrine
- native ownership of chart generation
- opaque convenience scores replacing projections and trace vessels
- collapse of multiple trace families into one hidden fast path

---

## 6. Recommended Execution Order

The smallest correct order is:

1. documentation and evidence closure
2. reader performance closure
3. evaluator/search Python wrapper closure
4. one admitted eclipse/event engine route
5. cartography stabilization
6. harmograms HN1
7. harmograms HN2
8. harmograms HN3
9. harmograms HN4

Reason:

- the repository first needs agreement on what is already true
- then it needs closure of native surfaces that are already partially integrated
- only then should a new native subsystem program begin for harmograms

---

## 7. Success Criteria

This closure program is complete only when:

1. every current `Partial` row is either converted to `Yes` or explicitly retired from the native target set
2. every surviving `Yes` claim is backed by code, tests, and a checked artifact where benchmarking is claimed
3. harmograms have a native path only for the mathematical kernels that justify acceleration
4. Python remains the visible source of truth for doctrine, policy, and public semantics

---

## 8. Immediate Next Move

The immediate next move should be to create a work-queue tracker derived from this program with one row per closure target:

- subsystem
- current state
- desired state
- blocking gap
- required tests
- required artifact
- owner phase

That tracker should be the execution ledger for converting the matrix from mixed status to honest closure.
