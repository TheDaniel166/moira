# Nutation 2000A — NumPy Acceleration Benchmark

## Summary

The numpy-vectorized path in `moira/nutation_2000a.py` delivers a **~79x median
speedup** over the pure Python path with **numerically identical results**
(max difference < 3×10⁻¹⁶ degrees, well within the stated 1×10⁻¹⁵ tolerance).

---

## Environment

| Field | Value |
| :--- | :--- |
| Python | 3.14.3 |
| NumPy | 2.4.3 |
| Platform | AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD |
| OS | Windows 11 |

---

## Results

| Epoch | Python median | Python p95 | NumPy median | NumPy p95 | Speedup |
| :--- | ---: | ---: | ---: | ---: | ---: |
| year 1900 | 2.739 ms | 2.984 ms | 0.0348 ms | 0.0458 ms | 78.8× |
| year 1950 | 2.716 ms | 2.904 ms | 0.0347 ms | 0.0388 ms | 78.2× |
| J2000.0   | 2.734 ms | 2.974 ms | 0.0345 ms | 0.0426 ms | 79.3× |
| year 2020 | 2.749 ms | 2.953 ms | 0.0347 ms | 0.0397 ms | 79.3× |
| year 2100 | 2.731 ms | 2.930 ms | 0.0345 ms | 0.0446 ms | 79.1× |

**Overall median speedup: 78.8×**

Methodology: pure Python — 30 samples × 5 calls; NumPy — 200 samples × 50 calls;
median and 95th-percentile reported.  Warmup applied before timing in both cases.

---

## Accuracy

| Metric | Value |
| :--- | :--- |
| Max Δψ difference across all epochs | < 3×10⁻¹⁶ degrees |
| Max Δε difference across all epochs | < 3×10⁻¹⁶ degrees |
| Stated tolerance | < 1×10⁻¹⁵ degrees |
| Result | **PASS** — paths are numerically identical to floating-point precision |

The difference arises from floating-point associativity (order of summation differs
between the scalar loop and vectorised dot products), not from any algorithmic
divergence.  Both paths operate on identical 64-bit IEEE 754 double values.

---

## Implementation Notes

The numpy path replaces four inner loops (2,414 IERS terms total) with four
matrix multiplications and vectorised `sin`/`cos`:

```
args = N @ fa_arr[:k]                          # (n_terms,) argument vector
contrib = dot(c1, sin(args)) + dot(c2, cos(args))  # scalar accumulation
```

Coefficient matrices (`c1`, `c2`, `N`) are built once at module import time from
the cached IERS tables.  No per-call allocation of the tables occurs.

The pure Python path is preserved unchanged as the canonical, auditable
implementation per the **Light Box doctrine**.  The numpy path is an acceleration
layer only — it is not the reference.

---

## Dispatch Behaviour

```
nutation_2000a(jd_tt)
  └── numpy available?  → _nutation_numpy(T, fa)   (~0.035 ms)
  └── numpy absent?     → _nutation_python(T, fa)  (~2.7 ms)
```

The public function dispatches silently.  No configuration required.
numpy is not a runtime dependency — it is an optional accelerator listed under
`[project.optional-dependencies]` in `pyproject.toml`.

---

## Impact on Downstream Callers

`nutation_2000a` is called inside `moira.obliquity.nutation()`, which is itself
called by:

- `planet_at` (every position computation)
- `gaia_stars_near` / `gaia_stars_by_magnitude` (once per batch call)
- `fixed_star_at` / `all_stars_at`
- `eclipse` and `occultation` pipeline functions

A 79× reduction in nutation cost materially improves throughput for any workload
that computes multiple positions at different epochs (transits, progressions,
solar arc directions, eclipse searches).