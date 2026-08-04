# Physical Heliacal Visibility Phase 6 Closure

Date: 2026-08-04
Status: Complete; two bounded native kernels admitted; event budgets remain red
Baseline implementation revision: `7e7e2886bc72dfd6e55231902ecd4a73d6b47832`
Final measured implementation revision: `35c1f26b3fb5e44dd31bed168e1b30449ddc7a44`
Evidence class: Numerical differential and performance evidence, not new scientific validation

## Decision

Phase 6 admits exactly two doctrine-free dense numerical kernels:

1. `physical_visibility_response_weights_v1`, which evaluates the fixed
   piecewise-linear spectral color warp, normalized photopic and scotopic
   response weights, and their S/P ratio from Python-owned inputs; and
2. `physical_visibility_direct_extinction_v1`, which evaluates one already
   bracketed direct-extinction LUT row interpolation and its spectral
   transmission.

The event solver, event ownership, model identifiers, color-law selection,
manifest and pack admission, validity-domain decisions, typed failure reasons,
policy, provenance, receipts, and result construction remain in Python. The
native bindings are private implementation details. The Python numerical
implementations remain executable differential oracles.

No geometry cache, approximate profile binning, solver port, policy port, or
public API expansion is admitted.

## Why these kernels

The baseline and profiling receipts are:

- [Phase 6 benchmark checkpoint](PHYSICAL_HELIACAL_VISIBILITY_PHASE6_BENCHMARK_CHECKPOINT_2026-08-04.md);
- [Phase 6 profile and census checkpoint](PHYSICAL_HELIACAL_VISIBILITY_PHASE6_PROFILE_CENSUS_CHECKPOINT_2026-08-04.md);
- [baseline benchmark artifact](../../../tests/artifacts/benchmarks/physical_visibility_phase6_baseline_2026-08-04.json); and
- [formal profile artifact](../../../tests/artifacts/benchmarks/physical_visibility_phase6_profile_jupiter_2026-08-04.json).

The formal profile attributed only 0.78% of non-overlapping internal time to
the event-solver implementation. Exact-input census runs found only 23 repeated
horizontal inputs among 53,886 Jupiter calls and 12 among 37,423 Sirius calls.
All 16,145 Jupiter target-profile contexts and direct-extinction altitudes were
distinct. Those results rejected a solver port, exact-input geometry cache,
and approximate profile reuse.

The profile did identify dense 400-bin spectral loops. Before native work, the
microbenchmark measured about 277.8 microseconds per Jupiter dynamic profile
resolution and 92.2 microseconds per direct-extinction interpolation. It also
identified an unnecessary second 800-value validation walk after the immutable
pack had already validated and generated the arrays. Phase 6 removed only that
duplicate walk; the independently constructible `TargetSpectralProfile`
continues to validate every supplied weight.

## Exact differential admission

The admission harness is
[`scripts/validate_physical_visibility_phase6_native.py`](../../../scripts/validate_physical_visibility_phase6_native.py).
Its exact receipt is
[`physical_visibility_phase6_native_validation_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_native_validation_2026-08-04.json),
SHA-256
`5ce3eb7a5100c15e8322e625da17624489a0ef874895f466e4cd749441c8e11e`.

The clean final revision used a freshly rebuilt native binary with SHA-256
`ef5fedf3fc0c98b4343af02f63d966e9e3cc94f9f46805f57d1b98a18e7ddd4a`,
explicit DE441/LE441, and physical-visibility pack `1.2.0` with manifest
SHA-256
`cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c`.
Normal execution remained offline under `MOIRA_NO_DOWNLOAD=1`.

The boundary-inclusive differential matrix contained:

- 14,205 target-response cases across Mercury, Venus, Mars, Jupiter, and
  Saturn;
- 1,001 phase points for each non-Saturn target;
- a 101 by 101 phase-angle and effective ring-latitude grid for Saturn;
- 2,001 target-altitude points across the complete 0.25 through 45 degree
  direct-extinction domain;
- 512 response and 256 direct cases repeated under eight-thread concurrency;
  and
- five 2,000-operation timing samples per Python/native kernel pair.

All checks passed. Observed maximum absolute differences were:

| Quantity | Observed maximum | Admission tolerance |
|---|---:|---:|
| S/P ratio | `8.881784197001252e-16` | `5e-15` |
| Photopic response weight | `1.734723475976807e-18` | `5e-18` |
| Scotopic response weight | `1.734723475976807e-18` | `5e-18` |
| Response normalization residual | `1.1102230246251565e-16` | `2e-15` |
| Direct-extinction magnitude | `0` | `2e-15` |
| Direct transmission | `0` | `2e-15` |

Serial and concurrent fingerprints were identical. The response-weight kernel
was 6.945 times faster than its Python oracle at the median, and the direct-
extinction kernel was 5.078 times faster. These are kernel-only measurements,
not public service-level promises.

## End-to-end performance gate

The final three-sample receipt is
[`physical_visibility_phase6_native_admission_benchmark_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_native_admission_benchmark_2026-08-04.json),
SHA-256
`ec79280ebfd3653c81aaaf8eb566a12504539b5da9e0db34dbba6228213f28ad`.
It cryptographically binds the passing native-admission receipt, clean
revision, rebuilt binary, and exact pack.

| Workload | Baseline sizing sample | Final three-sample median | Budget | Result |
|---|---:|---:|---:|---|
| First evaluated assessment | 1.940 s | 2.599 s | 3.0 s | Pass |
| Warm assessment | 0.269 s | 0.325 s | 0.5 s | Pass |
| Jupiter 30-day event | 36.446 s | 28.106 s | 15.0 s | Fail |
| Sirius 20-day event | 21.778 s | 18.911 s | 15.0 s | Fail |

The baseline event values were one-sample sizing measurements, so the apparent
22.9% Jupiter and 13.2% Sirius reductions are directional rather than a formal
cross-revision statistical estimate. A same-process diagnostic A/B also
preserved the exact Jupiter result fingerprint while reducing the native path
from 35.723 seconds to 29.289 seconds. The final gate deliberately exited
nonzero because the two event budgets remain unmet.

The missed budgets are recorded performance limitations, not hidden failures.
Phase 6 is an optional measured strengthening phase; its exit gate requires a
truthful admission decision, complete differential evidence, and preservation
of Python semantics, not arbitrary migration until a timing target turns
green. Further large gains would require a separately justified attack on
astronomical geometry or certified-search evaluation count. Neither is
admitted by this phase.

## Regression verification

The exact Phase 3 external-pack goldens passed at the final implementation:

```text
2 passed in 55.1s
Jupiter exact event JD: 2460070.591375516
Sirius exact event JD: 2461255.950317484
Planetary resource identity: DE441 in all four acquisitions
```

A focused regression collection then passed 314 tests covering the pack and
LUT, planetary and stellar targets, spectral composition, event behavior,
public contracts, legacy policy, native import/runtime verification, physical
REST routes, and general phenomena routes. It recorded 84 successful DE441
planetary-resource acquisitions, no skips, and no failures.

The final event benchmark retained the exact pre-Phase-6 result fingerprints:

- Jupiter: `2222fc44a89a23db2bf8f23fecdcd08e8bb07106b616c49ae6cf633463c8e863`;
  and
- Sirius: `8f584f41084943ccaf1068a02c37561eeb469c7219b053709d3c41b8fdb9639e`.

## Exit gate

- [x] Representative Python baselines and the benchmark environment are
  recorded.
- [x] The native admission decision is recorded.
- [x] Only profiled, doctrine-free numerical kernels moved to C++.
- [x] Manifest, policy, domain, failure, provenance, event, and result
  semantics remain in Python.
- [x] Python differential references remain executable.
- [x] Boundary-inclusive admitted-domain differential grids pass.
- [x] Invalid-domain behavior remains Python-owned and regression protected.
- [x] Deterministic concurrency passes.
- [x] Numerical tolerances and performance evidence remain separate.
- [x] Authoritative event goldens and focused public/REST regressions pass.
- [x] The still-red event budgets are explicit.

Phase 6 is closed. Phase 7 is the next implementation phase.

The implementation-plan status row and checkboxes require a narrow mechanical
sync after the protected in-progress Phase 4/5 edits to that shared roadmap
file are committed. This closure does not overwrite or absorb those unrelated
working-tree edits.
