# Moira NumPy / SpiceyPy Dependency Map

Status date: 2026-05-10

Purpose:
This document records the exact remaining `NumPy` and `spiceypy` dependency
surface in the current repository, with special attention to whether a site
is part of the governing planetary calculation path.

The distinction that matters is:

- planetary path
- production Python runtime
- native binding surfaces
- tests, scripts, scratch, and documentation

This is a tracking document, not a doctrine note.

## Governing Conclusion

For the active planetary calculation path:

- `planet_at(...)`: no `NumPy`, no `spiceypy`
- `all_planets_at(...)`: no `NumPy`, no `spiceypy`

For the broader production Python runtime:

- no live `NumPy` usage remains under `moira/`
- `spiceypy` remains only in `moira/lunar_limb.py`

What remains outside that Python runtime:

- `_moira_native` array-oriented binding surfaces
- tests, scripts, scratch, and historical docs

## 1. Active Planetary Path

These are the files governing the benchmarked public planetary path.

### 1.1 `NumPy`

- [moira/planets.py](../../moira/planets.py#L1401)
  - only a stale internal comment mentions `numpy`
  - there is no active `NumPy` import or execution path

- [moira/nutation_2000a.py](../../moira/nutation_2000a.py)
  - no `NumPy` usage

- [moira/corrections.py](../../moira/corrections.py)
  - no `NumPy` usage on the active planetary correction path

- [moira/spk_reader.py](../../moira/spk_reader.py#L75)
  - no `NumPy` import
  - planetary Chebyshev fallback path is tuple/scalar-owned

- [moira/lunar_limb.py](../../moira/lunar_limb.py)
  - no `NumPy` import
  - utilizes native `LolaPointCloud` substrate

- [moira/_spk_body_kernel.py](../../moira/_spk_body_kernel.py#L62)
  - no `NumPy` import
  - native payload readers are used, but not `NumPy` directly

### 1.2 `spiceypy`

- no `spiceypy` usage in the active planetary path

## 2. Production Python Runtime Outside the Planetary Path

### 2.1 `NumPy`

- [moira/astrocartography.py](../../moira/astrocartography.py)
  - NumPy removed 2026-05-10
  - ASC/DSC sampling now uses scalar math only

- [moira/daf_writer.py](../../moira/daf_writer.py)
  - NumPy removed 2026-05-10
  - Type-13 payload assembly and serialization now use stdlib only

- [moira/lunar_limb.py](../../moira/lunar_limb.py)
  - migrated to native substrate earlier in the same closure cycle

Repository scan result for `moira/`:

- no live `import numpy`
- no live `from numpy`
- no live `np.` or `_np.` production call sites

### 2.2 `spiceypy`

All current production `spiceypy` usage is concentrated in:

- [moira/lunar_limb.py](../../moira/lunar_limb.py#L40)
  - hard `spiceypy` import

- [moira/lunar_limb.py](../../moira/lunar_limb.py#L124)
  - kernel loading via `sp.furnsh(...)`

- [moira/lunar_limb.py](../../moira/lunar_limb.py#L129)
  - residual fallback ET conversion via `sp.str2et(...)` for pre-1972 epochs

- [moira/lunar_limb.py](../../moira/lunar_limb.py#L190)
  - apparent Moon state for a topocentric observer via `sp.spkcpo(...)`

- [moira/lunar_limb.py](../../moira/lunar_limb.py#L213)
  - body-frame rotation lookup via `sp.pxform(...)`

There are no other current production `spiceypy` sites in the repository scan.

## 3. Native Binding Surface Still Using NumPy

These sites are not the governing planetary manuscript, but they still keep
`_moira_native` coupled to `NumPy` array types.

### 3.1 Binding-level NumPy header

- [src/native/bindings/moira_native.cpp](../../src/native/bindings/moira_native.cpp#L4)
  - `#include <pybind11/numpy.h>`

### 3.2 Array-oriented binding APIs

- `py::array_t<double>` cartography entry points
- `py::array_t<double>` batch evaluator entry points
- array-returning helper surfaces in the non-planetary native bridge

These are the real remaining runtime-coupled NumPy surfaces.

## 4. Tests

### 4.1 `NumPy`

- [tests/unit/test_spk_reader.py](../../tests/unit/test_spk_reader.py#L5)
- [tests/unit/test_topocentric_jitter.py](../../tests/unit/test_topocentric_jitter.py#L99)
- [tests/unit/test_planetary_native_ownership_snapshot.py](../../tests/unit/test_planetary_native_ownership_snapshot.py#L15)

These do not govern runtime dependency, but they still track or exercise
NumPy-related surfaces.

### 4.2 `spiceypy`

- no test-side `spiceypy` sites were found in the direct repo scan

## 5. Scripts

### 5.1 `NumPy`

- [scripts/validate_phase4_events.py](../../scripts/validate_phase4_events.py#L1)
- [scripts/validate_native_solvers.py](../../scripts/validate_native_solvers.py#L1)
- [scripts/validate_delta_t_hybrid.py](../../scripts/validate_delta_t_hybrid.py#L405)
- [scripts/stress_test_phase3.py](../../scripts/stress_test_phase3.py#L1)
- [scripts/build_tier2_substrate.py](../../scripts/build_tier2_substrate.py#L3)
- [scripts/build_sovereign_substrate.py](../../scripts/build_sovereign_substrate.py#L13)
- [scripts/benchmark_native_eclipse.py](../../scripts/benchmark_native_eclipse.py#L2)
- [scripts/audit_phase4_edge_cases.py](../../scripts/audit_phase4_edge_cases.py#L1)
- [scripts/audit_phase3_search.py](../../scripts/audit_phase3_search.py#L1)

These are off the production runtime path.

### 5.2 `spiceypy`

- no script-side `spiceypy` sites were found in the direct repo scan

## 6. Scratch / Tmp / Historical Docs

These contain many `NumPy` references, but they are not governing runtime
surfaces:

- `scratch/`
- `tmp/`
- `docs/superpowers/plans/`

They should not be treated as live dependency authority.

## 7. Tracking Summary

### 7.1 Planetary Path

- `NumPy`: removed
- `spiceypy`: absent

### 7.2 Production Python Runtime

- `NumPy`: removed
- `spiceypy`: `moira/lunar_limb.py` only

### 7.3 Remaining Work

1. `_moira_native` NumPy-facing array/binding surfaces
2. test and script cleanup where worth doing
3. the remaining `spiceypy` work in `moira/lunar_limb.py`
