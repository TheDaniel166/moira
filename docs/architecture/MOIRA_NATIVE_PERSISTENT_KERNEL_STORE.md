# Moira Native Persistent Kernel Store

**Status**: Proposed substrate design
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_PLANETARY_PATH.md](./MOIRA_NATIVE_PLANETARY_PATH.md)
- [MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md](./MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md)
- [MOIRA_NATIVE_CLOSURE_PROGRAM.md](./MOIRA_NATIVE_CLOSURE_PROGRAM.md)

---

## 1. Purpose

This document defines the next substrate step for planetary native closure:

- a persistent native kernel store
- a persistent native segment store
- explicit segment evaluator caching

It exists because the current planetary native path is no longer bottlenecked mainly by steady-state Chebyshev evaluation.

The current choke point is first-load payload acquisition and setup.

That is a substrate problem, not a public-API problem.

---

## 2. Governing Finding

The present benchmark and timing evidence implies:

1. steady-state native segment evaluation is already strong
2. first-use native segment cost is still materially high
3. the remaining cost is concentrated in payload acquisition and first segment setup
4. additional micro-optimizations in scalar evaluator math are no longer the highest-value next move

Therefore the next correct optimization target is:

- persistent native ownership of kernel file context and segment payload state

not:

- wider public routing first
- more Python-side orchestration edits first
- more tiny evaluator-loop tuning first

---

## 3. Problem Statement

Right now the supported native reader path still behaves too much like this:

1. Python asks for a segment
2. native code opens or re-enters the file-level payload path
3. payload bytes are read and transformed into evaluator-owned coefficient storage
4. the evaluator is used

Even after the recent native-owned segment evaluator work, the main one-time cost remains tied to payload acquisition.

The system needs a stronger substrate with these properties:

- kernel-level native lifetime
- segment-level native cache
- explicit reuse across repeated calls
- no hidden semantic drift

---

## 4. Design Goals

The persistent store must:

- reduce first-use segment load cost
- preserve current `SpkReader` and `KernelPool` semantics
- keep Python policy and routing visible
- keep fallback behavior explicit
- remain parity-auditable against current Python truth

The persistent store must not:

- change public result vessels
- bypass current coverage and segment-selection semantics
- collapse supported and unsupported segment handling into one opaque path
- force all kernel reading into native code regardless of support boundaries

---

## 5. Proposed Object Model

The proposed native substrate should add two persistent native objects.

### 5.1 `NativeSpkKernelHandle`

Responsibility:

- own the open native kernel file context
- own the native DAF/SPK catalog for that file
- provide stable access to segment descriptors and payload reads

Minimum identity:

- canonical kernel path
- file format / endianness metadata
- native summary catalog

Minimum lifetime:

- survives for the lifetime of the owning Python `SpkReader`
- closes explicitly when the Python reader closes

### 5.2 `NativeSpkSegmentStore`

Responsibility:

- cache native segment evaluators keyed by segment identity
- return existing evaluators on repeat access
- prevent repeated payload materialization for the same segment

Minimum key:

- kernel path
- `start_i`
- `end_i`
- `data_type`

Optional extended key:

- `target`
- `center`

if needed for diagnostics only

---

## 6. Python Boundary Shape

Python should not become the owner of bulk coefficient payloads.

The preferred Python-facing shape is:

1. `SpkReader` creates or receives a native kernel handle at construction
2. segment objects retain a reference to that kernel handle
3. on first evaluation, the segment asks the handle/store for a native evaluator
4. subsequent evaluations reuse the same native evaluator

The preferred pybind surface is therefore not:

- `read_spk_chebyshev_segment_payload(...) -> dict`

as the primary fast route.

The preferred fast route is:

- `open_spk_kernel(path) -> NativeSpkKernelHandle`
- `kernel_handle.load_segment_evaluator(start_i, end_i, data_type) -> SpkSegmentEvaluator`

or:

- `kernel_handle.get_segment_evaluator(start_i, end_i, data_type)`

where `get` is allowed to return a cached evaluator.

The existing payload-dict route should remain only as:

- compatibility path
- parity test aid
- fallback debug surface

---

## 7. Lifecycle Law

The lifecycle should be:

1. Python `SpkReader(path)` is constructed
2. native DAF catalog is read once
3. a `NativeSpkKernelHandle` is created and kept alive
4. Python segment wrappers are built from the catalog
5. first request for a supported segment loads one native evaluator into the segment store
6. repeated requests for that segment reuse the cached evaluator
7. `SpkReader.close()` releases the native kernel handle and its segment cache

This keeps ownership aligned with current reader semantics.

It avoids introducing an ambient global singleton in native code.

---

## 8. Cache Law

The segment cache must be:

- deterministic
- per-kernel-handle by default
- explicit in lifetime

The cache must not:

- silently survive after the owning reader closes
- become a hidden process-global store unless a later design explicitly authorizes that

The default rule should be:

- cache segment evaluators inside the owning `NativeSpkKernelHandle`

This keeps invalidation simple:

- when the handle dies, the cache dies

---

## 9. Supported Surface Scope

The first admitted scope should remain narrow.

Phase-one persistent store support should cover:

- planetary SPK type-2 segments
- planetary SPK type-3 segments

It should not immediately widen to:

- all small-body paths
- type-13
- unrelated evaluator families

Those can be added only after the planetary kernel path proves the model.

---

## 10. Internal Native Responsibilities

The native kernel handle should own:

- file open and close
- summary catalog retention
- segment payload reading
- endianness-aware decoding
- cached evaluator construction

The Python reader should continue to own:

- coverage semantics
- segment selection by `(center, target, jd)`
- fallback selection between supported native and unsupported legacy paths
- exception semantics at the architectural boundary

This preserves visibility where it belongs.

---

## 11. Why This Is Better Than More `daf.hpp` Tuning

Further `daf.hpp` micro-optimizations alone are unlikely to be the summit move because:

- the main cost is broader first-load setup, not just one decode loop
- repeated segment access wants ownership and reuse, not repeated materialization
- the current design still rebuilds evaluator state in a way that is too local to each first request

A persistent store addresses the correct class of problem:

- repeated acquisition cost
- repeated setup cost
- repeated cache miss cost

not only:

- one inner byte-to-double conversion path

---

## 12. Proposed Implementation Phases

### PK-1: Native Kernel Handle

Add a pybind-exposed kernel handle that:

- opens a supported SPK file once
- reads and retains the native catalog
- can manufacture segment evaluators on demand

Exit condition:

- Python `SpkReader` can hold a live native kernel handle

### PK-2: Segment Evaluator Cache

Move supported segment evaluator caching into the kernel handle.

Exit condition:

- repeated access to the same supported segment reuses the same native evaluator

### PK-3: Reader Integration

Route `_NativeChebyshevSegment` to the kernel handle instead of payload-dict materialization for the primary fast path.

Exit condition:

- supported `position(...)` and `position_and_velocity(...)` calls use the persistent native substrate in normal execution

### PK-4: Benchmark Closure

Re-run:

- first-use load timing
- repeated segment benchmark
- ephemeris slice benchmark

Exit condition:

- the artifact set shows whether the persistent substrate reduced warmup cost meaningfully

---

## 13. Verification Gates

This design may only be considered successful if all of the following are checked.

### 13.1 Correctness Gate

- current SPK reader unit tests still pass
- native-vs-jplephem parity on supported type-2/type-3 segments still passes
- coverage and segment-selection semantics remain unchanged

### 13.2 Performance Gate

Must measure:

- first evaluator load cost for a supported planetary segment
- first public `reader.position(...)` cost on a fresh reader
- repeated `reader.position(...)` and `reader.position_and_velocity(...)` cost

### 13.3 Architectural Gate

Must prove:

- the cache lifetime is explicit
- close semantics release native resources
- unsupported segments still fall back plainly

---

## 14. Risks

The main risks are:

- hidden resource lifetime bugs
- stale cached evaluators after close or replacement
- accidental semantic drift in segment-selection rules
- over-widening the native fast path into unsupported kernel territory

The design therefore must remain:

- reader-owned
- explicit
- narrow in scope

---

## 15. Non-Goals

This design does not authorize:

- bypassing Python `SpkReader` semantics
- immediate native ownership of barycentric route chaining
- immediate native ownership of correction or coordinate layers
- process-global caching with unclear invalidation

Those belong later, if the substrate closes cleanly first.

---

## 16. Success Criteria

This substrate design is successful only when:

1. supported segment first-load cost is materially lower than the current measured path
2. repeated segment evaluation remains parity-clean
3. reader close semantics remain explicit and safe
4. the resulting benchmark artifacts improve `PP-06` honestly

If those conditions are not met, this design should be revised before higher planetary routing continues.

---

## 17. Immediate Next Move

The immediate implementation target derived from this design is:

- add `NativeSpkKernelHandle`
- move supported segment evaluator caching under that handle
- route `_NativeChebyshevSegment` through the handle-owned cache

That is the smallest correct next substrate step.
