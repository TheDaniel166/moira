# Native DAF Reader Adversarial Validation

**Version:** 1.0  
**Date:** 2026-05-21  
**Runtime target:** Python 3.14  
**Scope:** native DAF/SPK reader substrate, not the higher planetary facade

---

## 1. Purpose

This document records the dedicated adversarial validation surface for Moira's
native DAF/SPK reader path.

It is narrower than the general astronomy and native-path documents. The goal
here is not broad orbital parity. The goal is hostile reader-truth testing:

- malformed or unsupported native admission
- exact coverage-boundary ownership
- split-segment catalog truth
- boundary-near segment extraction
- native reader refusal behavior outside coverage

The forbidden outcome is silent semantic drift in the native reader substrate.

---

## 2. Governing Test Surface

Primary suite:

- [tests/unit/test_adversarial_native_daf_reader.py](../../tests/unit/test_adversarial_native_daf_reader.py)

Related supporting surfaces already present in the repo:

- [tests/unit/test_spk_reader.py](../../tests/unit/test_spk_reader.py)
- [tests/integration/test_small_body_native_reader_killer.py](../../tests/integration/test_small_body_native_reader_killer.py)

Those older suites already established parity and integration truth. The new
adversarial suite exists to force the native reader itself through hostile edge
conditions under a named validation doctrine.

---

## 3. Validation Doctrine

The suite is designed around reader-owned invariants, not downstream chart
products.

Governing doctrine:

- descriptor truth must survive native catalog parsing
- unsupported segment types must be rejected before partial admission
- exact coverage boundaries must be inclusive when the segment claims they are
- one tick outside coverage must fail cleanly
- split segments for the same `(center, target)` pair must union lawfully in
  coverage reporting
- native support predicates must reject mixed supported/unsupported catalogs
- exact end-of-record evaluation must remain stable at the last lawful instant
  and must fail immediately after that instant

Acceptable outcomes:

- finite canonical result
- explicit `KeyError`
- explicit `RuntimeError`
- explicit `OutOfRangeError`

Forbidden outcomes:

- partial admission of unsupported kernels
- uncovered epochs returning fabricated vectors
- descriptor drift
- native/fallback ambiguity hidden behind a plausible result

---

## 4. Adversarial Cases

The current suite contains 7 doctrinal adversarial tests.

### 4.1 Synthetic native catalog truth

The suite writes a synthetic type-13 kernel with `write_spk_type13(...)` and
asserts that the native catalog reader preserves:

- `locidw`
- `nd`
- `ni`
- summary count
- descriptor ordering
- `(target, center, frame, data_type, start_i, end_i)` truth

This proves the native DAF summary reader is not merely returning a usable
shape, but the correct semantic summary.

### 4.2 Exact coverage-boundary admission

The native small-body reader is forced to evaluate exactly at the start and end
coverage JDs reported by its own coverage map.

Expected invariant:

- exact start and exact end are admitted
- both return finite vectors

### 4.3 One-second-outside refusal

The same kernel is then queried one second before the start and one second
after the end of the reported coverage.

Expected invariant:

- both requests fail cleanly with `KeyError`
- no fabricated position is returned outside owned coverage

### 4.4 Unsupported segment admission guard

A hostile native catalog with SPK type `9` is injected.

Expected invariant:

- `SmallBodyKernel(...)` refuses construction
- the refusal is explicit and occurs before any partial live reader object is
  admitted

### 4.5 Split-segment coverage union

A synthetic catalog with two disjoint segments for the same body pair is
injected.

Expected invariant:

- `coverage()` unions the pair's outer bounds correctly
- `list_naif_ids()` remains truthful

This tests catalog ownership doctrine rather than interpolation.

### 4.6 Mixed-support catalog rejection

A catalog containing both a supported type-13 summary and an unsupported
type-9 summary is passed through the native support predicate.

Expected invariant:

- support is rejected for the catalog as a whole
- Moira does not silently admit the supported subset and ignore the hostile
  remainder

### 4.7 Exact-end Chebyshev boundary behavior

A native-backed synthetic type-2 segment is forced through:

- exact segment end
- one second after segment end

Expected invariant:

- exact end remains inclusive and finite
- the next tick raises `OutOfRangeError`

This is the most direct reader-boundary singularity in the suite.

---

## 5. Verification Receipt

Command run:

```bash
python -m pytest tests/unit/test_adversarial_native_daf_reader.py -q
python -m pytest tests/unit/test_adversarial_native_daf_reader.py --collect-only -q
```

Local Windows `.venv` equivalent used in the verifying environment:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\test_adversarial_native_daf_reader.py -q
.\.venv\Scripts\python -m pytest tests\unit\test_adversarial_native_daf_reader.py --collect-only -q
```

Recorded result on 2026-05-21:

- `7 collected`
- `7 passed`

No skips were recorded in this suite on the verifying run.

---

## 6. What This Proves

This suite proves that the native DAF/SPK reader now has an explicit
adversarial validation layer in the same spirit as the singularity campaign.

It does prove:

- hostile reader-boundary cases are being exercised directly
- native admission/refusal behavior is explicit on the audited cases
- exact boundary ownership and outside-coverage refusal behave lawfully on the
  audited synthetic kernels

It does not prove:

- full planetary-path closure above the reader boundary
- broad performance closure
- correctness of every unsupported or future SPK segment class
- chart-layer semantic truth

Those belong to other validation programs.

---

## 7. Relationship to the Wider Native Program

This document should be read alongside:

- [docs/architecture/MOIRA_NATIVE_BACKEND_ARCHITECTURE.md](../../docs/architecture/MOIRA_NATIVE_BACKEND_ARCHITECTURE.md)
- [docs/architecture/MOIRA_NATIVE_PLANETARY_PATH.md](../../docs/architecture/MOIRA_NATIVE_PLANETARY_PATH.md)
- [docs/architecture/MOIRA_NATIVE_MIGRATION_TRACKER.md](../../docs/architecture/MOIRA_NATIVE_MIGRATION_TRACKER.md)

Those documents describe ownership, closure state, and migration history.
This document records the hostile validation proof surface for the reader
substrate itself.
