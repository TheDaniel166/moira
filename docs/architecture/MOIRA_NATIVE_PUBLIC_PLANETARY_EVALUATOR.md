# Moira Native Public Planetary Evaluator

**Status**: Design note
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_PUBLIC_PLANETARY_EVALUATOR_SPEC.md](./MOIRA_NATIVE_PUBLIC_PLANETARY_EVALUATOR_SPEC.md)
- [MOIRA_NATIVE_PLANETARY_PATH.md](./MOIRA_NATIVE_PLANETARY_PATH.md)
- [MOIRA_NATIVE_PLANETARY_CASH_IN_PLAN.md](./MOIRA_NATIVE_PLANETARY_CASH_IN_PLAN.md)
- [MOIRA_NATIVE_PLANETARY_RETROSPECTIVE.md](./MOIRA_NATIVE_PLANETARY_RETROSPECTIVE.md)
- [MOIRA_NATIVE_PERSISTENT_KERNEL_STORE.md](./MOIRA_NATIVE_PERSISTENT_KERNEL_STORE.md)

---

## 1. Purpose

This document answers one question:

How can Moira materially improve public planetary speed without surrendering Python-readable policy and parity?

It is not a general native roadmap.

It is a design note for one specific next move:

- raise the native execution boundary
- keep Python as the visible doctrinal manuscript
- preserve exact public semantics

---

## 2. Why This Document Exists

The current state is now clear.

What we know:

- native substrate work was real
- reader and evaluator closure was worthwhile
- nearby public-path cash-in attempts were mostly exhausted
- the external public-speed gap remains materially large

What we also know:

- Moira's public outputs remain close to the tested secondary-engine comparison on the 1900-2100 slice
- the largest future lunar outlier is overwhelmingly a Delta T policy divergence, not a generic planetary failure

So the problem is no longer:

- "does native exist"
- "can the reader go faster"

The problem is:

- the current native boundary is too low
- too much of the admitted hot public path still executes in Python orchestration

---

## 3. Governing Doctrine

This next move is justified only if all of the following remain true:

1. Python remains the canonical policy manuscript
2. native execution is admitted only for specific public products
3. parity is judged against the current Python public path, not against an invented shortcut
4. no correction stage is silently weakened to manufacture speed

That means this is not a foreign flag-driven surface.

It is not:

- one generic native engine with ambient switches
- one opaque black box with undocumented correction policy

It is:

- one explicit native execution path for one explicit Moira product

---

## 4. The Product To Target

The first admitted target should be narrow.

Primary target:

- `all_planets_at(..., apparent=True, center='geocentric', frame='ecliptic')`

Secondary target:

- `planet_at(..., apparent=True, center='geocentric', frame='ecliptic')`

Why this order:

- `all_planets_at(...)` is the best cash-in surface because shared work naturally dominates there
- `planet_at(...)` should remain the correctness and regression guardrail

This avoids building a native surface that is broader than the repository can honestly certify.

---

## 5. The Core Design

### 5.1 Keep Python as doctrine

Python continues to define:

- Delta T choice
- apparent versus geometric doctrine
- aberration, gravitational deflection, and nutation policy
- public result vessel semantics
- validation expectations

Python remains the place where a human can read the admitted policy flow.

### 5.2 Move execution of the admitted hot path into native

For the admitted product only, native should execute the full repetitive body loop:

- Earth barycentric state acquisition
- body barycentric or geocentric vector assembly
- light-time iteration
- annual aberration
- gravitational deflection
- frame bias / precession / nutation rotation
- ecliptic projection
- longitudinal speed derivation

The point is not to hide policy.

The point is to stop paying Python orchestration cost for a path whose semantics are already fixed.

### 5.3 Return typed Moira-shaped payloads

The native layer should not return tuple-and-flag surfaces borrowed from another engine tradition.

It should return a minimal Moira-shaped internal payload:

- body identifier
- longitude
- latitude
- distance
- speed
- retrograde-ready sign information only if profitable, otherwise derive in Python

Public `PlanetData` vessels can still be constructed in Python if that remains the clearest public seam.

---

## 6. Recommended Object Model

### 6.1 `NativePlanetaryEvaluator`

One native-owned evaluator object should represent the admitted public planetary execution engine.

It should own:

- a live `NativeSpkKernelHandle`
- reusable evaluator/cache state
- one-JD shared Earth and deflector context
- reusable rotation/correction workspace

It should expose a narrow pybind surface such as:

- `evaluate_planet_apparent_geocentric_ecliptic(...)`
- `evaluate_all_planets_apparent_geocentric_ecliptic(...)`

### 6.2 Python wrapper law

Python wrappers should remain explicit and small:

- validate requested mode
- reject unsupported combinations plainly
- pass explicit policy inputs into native
- convert the returned payload into `PlanetData`

This preserves visible doctrine while minimizing Python work on the hot path.

---

## 7. What Native Must Not Own

This is as important as what it does own.

Native must not become the hidden author of:

- ambient Delta T doctrine
- silent fallback behavior
- product semantics not visible in Python
- broad option matrices not yet parity-tested

If the repository cannot explain a correction or mode from Python-facing policy, it should not be admitted into this evaluator.

---

## 8. Why This Is Different From CI-4

`CI-4` attempted a native-assisted batch vector fetch.

That failed because it still left the main public apparent pipeline above the boundary.

This design is different.

It does not merely batch vector acquisition.

It moves the whole admitted repetitive public assembly into one native transaction.

That matters because the remaining cost now lives in:

- repeated correction orchestration
- repeated per-body Python dispatch
- repeated packaging flow around already-admitted policy

So this is a qualitatively higher boundary, not another nearby micro-optimization.

---

## 9. Phase Sequence

### NPE-1 Define the admitted product exactly

Freeze the first native public product as:

- apparent
- geocentric
- ecliptic
- default correction stack
- normal `planet_at(...)` / `all_planets_at(...)` semantics

Do not widen surface area yet.

### NPE-2 Build one native multi-body evaluator

Implement the admitted `all_planets_at(...)` shape first.

The evaluator should accept:

- one `jd_ut`
- one `jd_tt`
- one explicit policy bundle
- one explicit body list

and return one compact payload for all requested bodies.

### NPE-3 Wrap through Python

Route `all_planets_at(...)` to the native evaluator only when the request exactly matches the admitted mode.

All other modes stay on the current Python path.

### NPE-4 Prove parity to the Python public path

Before any performance claim:

- compare native evaluator results to current Python `all_planets_at(...)`
- use fixed body/date slices
- include Moon and Mercury deliberately
- include modern and future slices
- separate policy divergences from engine defects

### NPE-5 Benchmark public gain

Only after parity gates pass:

- benchmark `all_planets_at(...)`
- then benchmark `planet_at(...)` if a single-body wrapper is added

Success is judged only at the public surface.

---

## 10. Verification Gates

This design should not be considered real until it clears all of these:

### Gate A: Python-parity gate

For the admitted mode, native output must match Python output within declared tolerances on a fixed validation corpus.

### Gate B: policy-explicitness gate

Every admitted correction policy must still be legible from Python and documented by name.

### Gate C: benchmark gate

`all_planets_at(...)` must show a material and stable positive gain, not one-run noise.

### Gate D: doctrine gate

Unsupported modes must stay explicit.

No silent widening.

No hidden fallback into "close enough" products.

---

## 11. Risks

### 11.1 Hidden semantic drift

The greatest risk is that a native evaluator quietly diverges from the Python manuscript while still looking fast.

That would be a doctrinal failure.

### 11.2 Premature breadth

If the evaluator tries to absorb too many modes at once, the validation surface will outrun the repository's ability to certify it.

### 11.3 Black-box temptation

If native starts owning policy rather than execution, Moira loses visibility.

That would trade speed for doctrinal opacity.

---

## 12. Success Standard

This path is worth taking only if it produces a public result that the current architecture could not.

Minimum success:

- `all_planets_at(...)` becomes clearly and stably positive
- Python parity remains intact

Strong success:

- the public multi-body path moves materially closer to the performance level required by Moira's own execution goals while preserving doctrine

Failure condition:

- native implementation complexity rises
- public benchmarks stay near parity
- parity burden grows faster than performance return

If that happens, the repository should stop and admit that the current readable-Python doctrine is also the performance ceiling.

---

## 13. Final Reading

The next performance move should not be:

- more reader tuning
- more wrapper shaving
- more partial batch helpers

It should be:

- one explicit native evaluator for one explicit public planetary product

Python should remain the keeper of doctrine.

Native should become the executor of the admitted hot path.

That is the cleanest remaining path toward materially better planetary speed without surrendering Moira's visible computational truth.
