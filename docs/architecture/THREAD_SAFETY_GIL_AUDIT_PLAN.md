# Thread Safety And GIL Audit Closure Record

## Purpose

This document records the exact closure sequence that was used to complete
Moira's thread-safety and GIL-audit work.

It is intentionally narrower than a general concurrency roadmap.
The native and reader substrate already contains meaningful concurrency work:

- `SpkReader` already declares concurrent read semantics
- native evaluators already use mutex-guarded cache protection
- native SPK handle lifecycle already has serialized close behavior
- many long-running native bindings already use `py::gil_scoped_release`

At planning time, the remaining gap was primarily:

1. public contract publication
2. full native binding GIL classification
3. regression-proof audit coverage
4. deployment guidance for threaded services

That closure condition has now been satisfied. This document remains as the
completion record and audit scaffold for future maintenance, not as an open
work plan.

---

## Current Status

The substantive closure work described below is complete:

- the public threading contract exists in `docs/threading.md`
- `SpkReader` and facade threading prose were aligned to that contract
- major long-running pure-native bindings now have explicit GIL-release
  coverage where safe
- audit coverage now includes source audits, runtime verification, and
  adversarial verification across native and public wrapper paths
- the competitive analysis document was narrowed accordingly

What remains is ordinary maintenance:

- keep the contract accurate as code changes
- keep GIL-audit tests aligned with native bindings
- apply the documented deployment model in future REST/service work

---

## Milestone 1: Publish The Threading Contract `COMPLETE`

### Objective

Create one canonical public document for thread-safety semantics.

### Files

- `docs/threading.md` or `docs/thread_safety.md`
- optional link from `README.md` or docs index if one exists

### Required Content

#### `SpkReader`

- Concurrent read calls on an already-open instance: `admitted`
- `close()` during in-flight reads: `not admitted`
- Replacing the global singleton during active computation: `not admitted`

#### `KernelPool`

- Concurrent read routing across contained readers: `admitted`
- Pool mutation after publication to worker threads: `not admitted`

#### `Moira`

- Pure read-only computational calls on a stable initialized instance:
  `admitted`
- Mutating kernel or session configuration during concurrent requests:
  `not admitted`

#### Singleton Helpers

- `get_reader()`: safe for established read access
- `set_kernel_path()`, `swap_reader()`, `reset_singleton()`: startup/test
  lifecycle only

#### Deployment Guidance

- Initialize once at process startup
- Do not hot-swap kernel state in a live threaded server
- Prefer worker processes if stronger isolation is needed

### Acceptance

A reader can answer "what is safe, what is conditionally safe, what is
forbidden" without reading source code.

---

## Milestone 2: Reconcile Internal Contracts With Public Wording `COMPLETE`

### Objective

Make code docstrings and machine contracts match the public contract exactly.

### Files

- `moira/spk_reader.py`
- `moira/_facade_kernel.py`
- any other `_facade_*` mixins with `concurrency` fields found during audit

### Required Edits

- Make `SpkReader` docstring explicitly state:
  - concurrent reads are supported
  - lifecycle mutation is serialized at module level, not generally
    request-safe
- Make `KernelFacadeMixin` explicitly state:
  - read routing is safe
  - it does not make global kernel mutation safe under concurrent service
    traffic
- Align `MACHINE_CONTRACT` `concurrency` notes with prose
- Ensure no docstring claims broader safety than tests prove

### Acceptance

There is no contradiction between machine contracts, prose docstrings, and the
public thread-safety document.

---

## Milestone 3: Inventory Every Native Binding For GIL Policy `COMPLETE`

### Objective

Classify every binding in `src/native/bindings/moira_native.cpp`.

### Files

- `src/native/bindings/moira_native.cpp`

### Deliverable

A binding inventory table, either in:

- a temporary audit note, or
- grouped comments in the file or audit tests

### Required Classification

Each binding must be placed in exactly one category:

- `release_gil_required`
- `release_gil_intentional`
- `retain_gil_intentional`

### Classification Heuristics

- Pure compute or batch compute: usually release
- File I/O or kernel payload loads: usually release
- Short scalar wrappers: may retain
- Python-callback-driven solvers: retain unless proven safe otherwise

### Minimum Inventory Scope

- all `.def(...)` bindings
- all `m.def(...)` bindings

### Acceptance

Every native public binding has an explicit GIL policy decision.

---

## Milestone 4: Close The Remaining GIL Gaps `COMPLETE`

### Objective

Add `py::gil_scoped_release` where the inventory says it is required and safe.

### Files

- `src/native/bindings/moira_native.cpp`

### Edit Rules

- Only annotate bindings that do not touch Python objects while executing
  native work
- Do not release the GIL around code paths that call Python callbacks or depend
  on Python-owned iteration during the released section
- If a binding intentionally keeps the GIL, leave a short reason in audit notes
  or tests

### Priority Targets

- long-running batch evaluators
- event and search functions
- file, catalog, and payload loaders
- bulk geometry and vector transforms
- native segment and kernel handle operations

### Acceptance

No obviously long-running pure-native binding remains unclassified or
accidentally unannotated.

---

## Milestone 5: Expand Audit Tests `COMPLETE`

### Objective

Make the GIL and threading policy regression-proof.

### Files

- `tests/unit/test_native_gil_release_audit.py`
- `tests/unit/test_native_second_wave_gil_release_audit.py`
- `tests/unit/test_native_evaluator_thread_safety_audit.py`
- `tests/unit/test_spk_reader.py`
- optionally `tests/unit/test_threading_contract_audit.py`

### Required Coverage

- Assert that all classified long-running native bindings have GIL release
- Assert that native handle close path remains serialized
- Preserve evaluator cache mutex audit
- Preserve singleton first-access concurrency witness
- Add explicit contract witnesses for admitted behavior
- Avoid asserting undefined behavior as if it were supported

### Acceptance

Removal of a required GIL release or a stated thread-safety invariant causes a
test failure.

---

## Milestone 6: Add Service Deployment Guidance `COMPLETE`

### Objective

Make production usage operationally clear.

### Files

- same thread-safety doc from Milestone 1
- optionally `README.md` or service documentation if present

### Required Content

- recommended startup pattern
- forbidden live-mutation pattern
- recommended worker model for REST deployment
- note that thread-safe reads do not imply hot-reload-safe kernel mutation

### Acceptance

A REST implementer can deploy Moira without guessing the concurrency model.

---

## Milestone 7: Update The Competitive Paper `COMPLETE`

### Objective

Make the gap ledger factually correct after the work is done.

### Files

- `MOIRA_COMPETITIVE_ANALYSIS.md`

### Required Edits

- Change broad "partially addressed" wording to a narrower statement
- State that:
  - native GIL release coverage exists
  - evaluator and native handle synchronization exists
  - public thread-safety documentation is present
  - remaining concern, if any, is deployment pattern choice rather than missing
    substrate

### Acceptance

The paper no longer frames this as a foundational concurrency deficit.

---

## Verification Checklist

Run at minimum:

1. `.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_docstring_governance.py -q`
2. `.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_native_gil_release_audit.py tests\\unit\\test_native_second_wave_gil_release_audit.py tests\\unit\\test_native_evaluator_thread_safety_audit.py -q`
3. `.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_spk_reader.py -k "concurrent_first_access or singleton_safe" -q`
4. any new threading-contract audit test
5. any relevant facade surface audit if contract prose changes widen

### Verification Note

The broader `tests/unit/test_spk_reader.py` suite currently contains unrelated
unsupported-kernel fallback failures in some environments. Those failures
should be handled separately and must not be misreported as thread-safety
regressions.

---

## Definition Of Done

This gap was considered closed only when all of the following became true:

- public thread-safety document exists
- `SpkReader` and facade docstrings match it
- every native binding has an explicit GIL policy
- required GIL releases are present
- audit tests enforce the policy
- deployment guidance exists
- `MOIRA_COMPETITIVE_ANALYSIS.md` is updated accordingly

These conditions are now satisfied. The thread-safety and GIL-audit item is no
longer an open engine gap; it is a closed infrastructure concern with ongoing
maintenance obligations.
