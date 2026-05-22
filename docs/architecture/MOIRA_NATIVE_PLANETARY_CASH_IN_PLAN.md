# Moira Native Planetary Cash-In Plan

**Status**: Execution plan
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md](./MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md)
- [MOIRA_NATIVE_PLANETARY_PATH.md](./MOIRA_NATIVE_PLANETARY_PATH.md)
- [MOIRA_NATIVE_PERSISTENT_KERNEL_STORE.md](./MOIRA_NATIVE_PERSISTENT_KERNEL_STORE.md)

---

## 1. Purpose

This document answers one question:

How do we convert the real native substrate gains into visible public-product gains?

It is not a general native roadmap.

It is a conversion program for:

- `all_planets_at(...)`
- and the minimal single-body surfaces needed to keep that bulk route honest

The standard is strict:

- substrate wins are not enough
- reader-local speedups are not enough
- only public-surface gains count as true cash-in

---

## 2. Current Truth

What is already real:

- native SPK segment evaluation is materially faster
- persistent native kernel ownership is real
- evaluator reuse is real
- shared vector caching in the Python planetary path is real

What is not yet real:

- a strong public `planet_at(...)` speedup
- a strong public `all_planets_at(...)` speedup

Current benchmark reading:

- `planet_at(...)`: only weakly positive overall and slightly negative in warm steady-state
- `all_planets_at(...)`: now materially positive in warm steady-state once the admitted native evaluator is active, while cold-reader totals remain near parity

So the bottleneck has moved.

It is no longer mainly:

- segment math
- payload reuse

It is now mainly:

- public-path orchestration
- repeated apparent-pipeline work
- per-body Python overhead above the reader boundary

---

## 3. Cash-In Doctrine

The next work must follow these rules:

1. optimize only where the public products spend time
2. preserve exact planetary semantics
3. measure only public products when judging success
4. stop widening native depth if it does not move the bulk chart workload materially

This means:

- no more small reader micro-tuning unless it clearly lifts public artifacts
- no native work justified only by helper-level wins
- no closure claim stronger than the public benchmarks

---

## 4. Best Conversion Targets

### 4.1 `all_planets_at(...)` is the primary cash-in surface

This is the best target because:

- it naturally shares work across bodies
- it already has a shared vector cache
- it is closer to chart reality than isolated single-body calls

If native investment is going to become visible, this is the most likely place.

### 4.2 `planet_at(...)` is the control surface

This is still important, but mainly as a guardrail:

- keep semantics exact
- prevent regressions
- confirm any `all_planets_at(...)` optimization is not cheating by bypassing canonical logic
- do not mistake it for an equally promising native cash-in surface unless a separate benchmark story proves otherwise

---

## 5. Highest-Yield Changes

### CI-1 Shared apparent-context object per JD

Build one internal context object for a single `jd_tt` carrying:

- Earth barycentric position and velocity
- nutation terms
- obliquity
- precomposed rotation matrix
- Sun geocentric vector
- Jupiter geocentric vector
- Saturn geocentric vector
- shared vector cache

Goal:

- stop recomputing and re-threading these pieces per body
- make the public path explicit about one-JD shared state

Expected value:

- moderate
- mostly on `all_planets_at(...)`

Risk:

- low if kept internal and semantics-preserving

### CI-2 Multi-body apparent pipeline helper

Add an internal helper dedicated to the common `all_planets_at(...)` case:

- accepts one JD and many bodies
- reuses one apparent-context object
- performs the existing pipeline without re-entering the full public `planet_at(...)` wrapper each time

This is still Python-owned unless a later native wrapper is justified.

Goal:

- remove repeated public-call overhead
- keep one canonical pipeline manuscript

Expected value:

- high

Risk:

- medium, because duplication pressure must be controlled

Rule:

- do not fork semantics
- factor the canonical inner pipeline, do not create a second truth

### CI-3 Shared astrometric speed-state path

The current speed field still requires per-body geocentric state assembly.

For `all_planets_at(...)`, make speed derivation reuse the same body-state work already assembled for position whenever possible.

Goal:

- reduce repeated geocentric-state work

Expected value:

- moderate

Risk:

- medium, because speed semantics must remain exact

### CI-4 Optional native-assisted batch vector fetch

Only if `CI-1` through `CI-3` do not move the public artifacts enough.

This would mean:

- one admitted native helper that evaluates several requested body vectors for one JD
- Python still owns correction policy and result vessels

Goal:

- cash in the native reader substrate at the one-JD multi-body level

Expected value:

- potentially high

Risk:

- higher than the Python orchestration path
- should not be attempted until the cheaper Python restructuring has been measured

---

## 6. Recommended Order

The correct order is:

1. `CI-1` shared apparent-context object
2. `CI-2` multi-body apparent pipeline helper
3. `CI-3` shared speed-state path
4. re-benchmark `planet_at(...)` and `all_planets_at(...)`
5. only then consider `CI-4` native-assisted batch fetch

This order is disciplined because it spends the cheap structural gains first.

If those do not cash out enough, then the justification for a deeper native public wrapper becomes much stronger.

---

## 7. Success Standard

This program counts as successful only if it changes the public artifacts materially.

Minimum success:

- `all_planets_at(...)` moves from parity to a stable positive win
- `planet_at(...)` does not regress

Strong success:

- `all_planets_at(...)` becomes the first clearly positive engine-level planetary surface

Failure condition:

- helper-level improvements continue
- public artifacts remain flat

If that happens, the repository should stop claiming that native closure is near and instead admit that another deeper public-path design move is required.

---

## 8. Execution Note

`CI-1` has now been implemented in the planetary path.

What it changed:

- introduced a one-JD internal apparent-context object
- unified shared Earth-state, nutation, obliquity, rotation, and deflector ownership
- routed `all_planets_at(...)` through that context while preserving canonical `planet_at(...)` semantics

What the first measurement says:

- semantics remained intact on the planetary validation slice
- public benchmarks remained effectively parity and in the current run were slightly negative overall

So the honest reading is:

- `CI-1` was structurally correct
- `CI-1` did not cash in the native substrate enough by itself

The next correct move is `CI-2`.

That is now the smallest justified cash-in step because:

- the shared state object exists
- the remaining overhead is still public-call and per-body orchestration cost
- further reader-local polishing is less defensible than a multi-body apparent helper

`CI-2` has now also been implemented.

What it changed:

- extracted one canonical internal planetary core
- kept `planet_at(...)` as the public wrapper
- routed `all_planets_at(...)` through the shared inner pipeline directly instead of re-entering the full public wrapper per body

What the first `CI-2` measurement says:

- `all_planets_at(...)` is the first surface to show a real warm-reader engine-level gain under the admitted native evaluator
- `planet_at(...)` remains a control surface whose current warm benchmark is still slightly negative

This is the first public multi-body result that is materially on the right side without changing planetary semantics.

The repository should now read the two surfaces asymmetrically:

- `all_planets_at(...)` is the legitimate native cash-in surface
- `planet_at(...)` is the semantic guardrail and should not be over-sold as a speed target

`CI-3` was then attempted as a shared astrometric speed-state preload for the multi-body workload.

Result:

- semantics remained intact
- public benchmarks worsened
- the preload/state-sharing variant was reverted

So the correct reading is:

- `CI-3` is not currently a justified cash-in path
- it should remain rejected unless a different speed-state design is proposed and measured separately
