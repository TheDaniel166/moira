# Moira NumPy / SpiceyPy Dependency Map

Status date: 2026-05-09

Purpose:
This document records the exact remaining `NumPy` and `spiceypy` dependency
surface in the current repository, with special attention to whether a site
is part of the governing planetary calculation path.

The distinction that matters is:

- planetary path
- production code outside the planetary path
- native binding surfaces
- tests, scripts, scratch, and documentation

This is a tracking document, not a doctrine note.

## Governing Conclusion

For the active planetary calculation path:

- `planet_at(...)`: no `NumPy`, no `spiceypy`
- `all_planets_at(...)`: no `NumPy`, no `spiceypy`

The governing planetary manuscript is therefore free of both dependencies.

What remains is outside that path:

- array-oriented native binding surfaces
- cartography / writer / limb systems
- tests, scripts, scratch, and historical docs

## 1. Active Planetary Path

These are the files governing the benchmarked public planetary path.

### 1.1 `NumPy`

- [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:1401)
  - only a stale internal comment mentions `numpy`
  - there is no active `NumPy` import or execution path

- [moira/nutation_2000a.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/nutation_2000a.py)
  - no `NumPy` usage

- [moira/corrections.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/corrections.py)
  - no `NumPy` usage on the active planetary correction path

- [moira/spk_reader.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/spk_reader.py:75)
  - no `NumPy` import
  - planetary Chebyshev fallback path is tuple/scalar-owned

- [moira/_spk_body_kernel.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/_spk_body_kernel.py:62)
  - no `NumPy` import
  - native payload readers are used, but not `NumPy` directly

### 1.2 `spiceypy`

- no `spiceypy` usage in the active planetary path

## 2. Native Binding Surface Still Using NumPy

These sites are not the governing planetary manuscript, but they still keep
`_moira_native` coupled to `NumPy` array types.

### 2.1 Binding-level NumPy header

- [src/native/bindings/moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:4)
  - `#include <pybind11/numpy.h>`

### 2.2 Legacy evaluator / interpolation array APIs

- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:325)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:346)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:377)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:405)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:440)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:1256)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:1265)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:1281)

These are legacy / helper array APIs, not the governing planetary hot path.

### 2.3 Type-13 payload still NumPy-shaped

- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:604)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:607)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:610)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:620)

This remains relevant for small-body / type-13 surfaces, but not for the
current planetary path closure.

### 2.4 Non-planetary batch / cartography array APIs

- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:630)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:659)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:720)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:739)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:769)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:810)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:853)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:887)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:943)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:977)
- [moira_native.cpp](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/src/native/bindings/moira_native.cpp:1043)

These are off the active planetary path.

## 3. Production Code Outside the Planetary Path

### 3.1 `NumPy`

#### Optional vectorized production code

- [moira/astrocartography.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/astrocartography.py:44)
  - optional `NumPy` vectorized path

- [moira/daf_writer.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/daf_writer.py:54)
  - optional `NumPy` writer path

#### Hard production dependency

- [moira/lunar_limb.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/lunar_limb.py:38)
  - hard `NumPy` dependency

### 3.2 `spiceypy`

All current production `spiceypy` usage is concentrated in:

- [moira/lunar_limb.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/lunar_limb.py:40)
  - hard `spiceypy` import

- [moira/lunar_limb.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/lunar_limb.py:121)
  - `sp.furnsh(...)`

- [moira/lunar_limb.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/lunar_limb.py:126)
  - `sp.str2et(...)`

There are no other current production `spiceypy` sites in the repository scan.

## 4. Tests

### 4.1 `NumPy`

- [tests/unit/test_spk_reader.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/tests/unit/test_spk_reader.py:5)
- [tests/unit/test_topocentric_jitter.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/tests/unit/test_topocentric_jitter.py:99)
- [tests/unit/test_planetary_native_ownership_snapshot.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/tests/unit/test_planetary_native_ownership_snapshot.py:15)

These do not govern runtime dependency, but they still track or exercise
NumPy-related surfaces.

### 4.2 `spiceypy`

- no test-side `spiceypy` sites were found in the direct repo scan

## 5. Scripts

### 5.1 `NumPy`

- [scripts/validate_phase4_events.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/validate_phase4_events.py:1)
- [scripts/validate_native_solvers.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/validate_native_solvers.py:1)
- [scripts/validate_delta_t_hybrid.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/validate_delta_t_hybrid.py:405)
- [scripts/stress_test_phase3.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/stress_test_phase3.py:1)
- [scripts/build_tier2_substrate.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/build_tier2_substrate.py:3)
- [scripts/build_sovereign_substrate.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/build_sovereign_substrate.py:13)
- [scripts/benchmark_native_eclipse.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/benchmark_native_eclipse.py:2)
- [scripts/audit_phase4_edge_cases.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/audit_phase4_edge_cases.py:1)
- [scripts/audit_phase3_search.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/scripts/audit_phase3_search.py:1)

These are off the active planetary runtime path.

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

### 7.2 Remaining Production Work

- `NumPy`
  - `moira/astrocartography.py`
  - `moira/daf_writer.py`
  - `moira/lunar_limb.py`
  - array-oriented surfaces in `src/native/bindings/moira_native.cpp`

- `spiceypy`
  - `moira/lunar_limb.py` only

### 7.3 Next Logical Removal Order

If the repository later wants broader dependency reduction beyond the
planetary path, the next sensible order is:

1. `_moira_native` NumPy-facing non-planetary helper surfaces
2. `moira/astrocartography.py`
3. `moira/daf_writer.py`
4. `moira/lunar_limb.py` NumPy/spiceypy program

