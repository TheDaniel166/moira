# Moira NumPy Removal Audit Report

Date: 2026-05-10
Status: production Python runtime verified NumPy-free

## Scope

This audit records the current NumPy state after the lunar-limb migration and
the follow-on removal of the remaining Python production NumPy paths.

It covers:

- the production planetary path
- `moira/lunar_limb.py`
- remaining production Python modules
- the still-open native binding and test/script surfaces

## Verified Findings

The following production files were checked for `import numpy`, `from numpy`,
`np.`, `_np.`, `np.ndarray`, and `np.asarray` usage:

- `moira/planets.py`
- `moira/corrections.py`
- `moira/spk_reader.py`
- `moira/_spk_body_kernel.py`
- `moira/nutation_2000a.py`
- `moira/lunar_limb.py`
- `moira/astrocartography.py`
- `moira/daf_writer.py`

Result:

- No active NumPy import remains in `moira/lunar_limb.py`.
- No active NumPy import remains in `moira/astrocartography.py`.
- No active NumPy import remains in `moira/daf_writer.py`.
- The active planetary path remains NumPy-free.
- The current production Python runtime scan found no live NumPy sites under `moira/`.

## Performance Verification

Benchmark executed from the project `.venv`:

```powershell
.\.venv\Scripts\python.exe tests\benchmark_lola_filters.py
```

Observed result on 2026-05-10:

- Sequential average: `1.1456 ms`
- Combined average: `0.2447 ms`
- Speedup: `4.68x`
- Time reduction: `78.64%`

Phase 6 performance target status:

- Required improvement: greater than `15%`
- Observed improvement: `78.64%`
- Verdict: satisfied

The benchmark also reported size parity between the sequential and combined
filter paths for its benchmark case.

## Remaining NumPy Surfaces

These are outside the now-clean Python production runtime:

- `src/native/bindings/moira_native.cpp`
  - binding-level NumPy header and array-oriented helper surfaces
- selected tests and validation scripts
  - acceptable comparison and analysis usage
- scratch and historical planning material

## Documentation Alignment

The following documents now match the verified state:

- `docs/architecture/MOIRA_NUMPY_SPICE_DEPENDENCY_MAP.md`
- `.kiro/specs/numpy-free-lunar-limb/tasks.md`

## Audit Verdict

The Python production runtime is now NumPy-free.

What is complete:

- `moira/lunar_limb.py` no longer depends on NumPy
- `moira/astrocartography.py` no longer depends on NumPy
- `moira/daf_writer.py` no longer depends on NumPy
- the active planetary path remains NumPy-free
- the Phase 6 benchmark mandate is met with measured margin

What is not claimed:

- repository-wide NumPy removal
- removal of NumPy-oriented native binding helpers
- removal of NumPy from tests, scripts, or historical documentation
