# Physical Heliacal Visibility Phase 6 Profile and Census Checkpoint

Date: 2026-08-04
Status: Complete diagnostic checkpoint; native work still not admitted
Measured engine revision: `d5f8630f4221d129733c6bab29077ea05b5b478e`
Evidence class: Performance attribution only, not scientific validation

## Question

The Phase 6 baseline showed that the admitted Jupiter and Sirius event
workloads missed their 15-second development budgets. This checkpoint asks
where that time is spent, whether exact-input event-local caching can remove
it, and whether the remaining work forms a stable numerical kernel. It does
not change event doctrine, policy, provenance, public results, fixtures,
tolerances, or a release identity.

All measurements used a clean detached checkout at the revision above, a
freshly rebuilt native extension from that checkout, explicit DE441/LE441,
physical-visibility pack `1.2.0`, and `MOIRA_NO_DOWNLOAD=1`. Both instrumented
event runs returned the exact Phase 3 event JDs with zero residual and retained
`certified_lipschitz_zero_enclosure`.

## Formal Jupiter profile

The reproducible profiler is
[`scripts/profile_physical_visibility_phase6.py`](../../../scripts/profile_physical_visibility_phase6.py),
and its receipt is
[`tests/artifacts/benchmarks/physical_visibility_phase6_profile_jupiter_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_profile_jupiter_2026-08-04.json).

The deterministic profile observed 231,955,642 calls and 84.314 seconds of
profiled internal time. Profiler overhead makes that wall time unsuitable for
the unprofiled performance gate. The non-overlapping internal-time attribution
was:

| Cluster | Internal time | Share |
|---|---:|---:|
| Spectral target and data-pack numerics | 31.517 s | 37.38% |
| Astronomical geometry | 19.138 s | 22.70% |
| Other Python/runtime work | 15.075 s | 17.88% |
| Already-native substrate | 14.813 s | 17.57% |
| Physical-visibility orchestration | 3.114 s | 3.69% |
| Event-solver implementation | 0.656 s | 0.78% |

The event solver owns cumulative downstream time but not the dominant
self-time. Porting the solver state machine would therefore move Python-owned
event semantics without attacking the measured numerical work and is rejected.

The principal spectral loops were dynamic target-color resolution, response
weight construction, response validation, direct-extinction interpolation,
and target transmission integration. The largest existing native primitive
was IAU 2000A nutation, with 220,956 calls and 11.543 seconds of profiled
internal time; this confirms that a blanket statement such as "move it to
C++" is not an admission design.

## Exact-input call census

The call-census harness is
[`scripts/census_physical_visibility_phase6.py`](../../../scripts/census_physical_visibility_phase6.py).
Its Jupiter and Sirius receipts are:

- [`physical_visibility_phase6_census_jupiter_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_census_jupiter_2026-08-04.json); and
- [`physical_visibility_phase6_census_sirius_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_census_sirius_2026-08-04.json).

The census wraps selected Python call boundaries without changing return
values or exceptions. Wrapper wall time is diagnostic only.

| Boundary | Jupiter calls / unique inputs | Sirius calls / unique inputs | Decision |
|---|---:|---:|---|
| True horizontal geometry | 53,886 / 53,863 | 37,423 / 37,411 | Exact-input caching rejected |
| Dynamic planetary target profile | 16,145 / 16,145 | 0 / 0 | Genuinely geometry dependent |
| Invariant stellar target profile | 0 / 0 | 10,436 / 1 | Reusable, but individually cheap |
| Direct-extinction spectrum | 16,145 / 16,145 | 10,436 / 10,436 | Genuinely geometry dependent |
| Response-weight validation | 32,290 calls | 20,872 calls | Duplicate validated-pack walk |

Only 23 Jupiter and 12 Sirius horizontal calls repeated an exact input. An
event-local geometry cache would add state and memory while eliminating less
than 0.05% of those calls, so it is rejected. Jupiter's target profile and
direct spectrum were unique for every evaluated assessment. Approximate
binning is also rejected because it would change admitted numerical truth.

Sirius did repeat one exact source-bound profile, but the microbenchmark below
measured its resolution at only about 2.9 microseconds per call. The repeated
800-value validation walk, not catalog identity resolution, is the material
structural duplication.

## Candidate microbenchmarks

The candidate harness is
[`scripts/microbenchmark_physical_visibility_phase6.py`](../../../scripts/microbenchmark_physical_visibility_phase6.py),
and its clean-revision receipt is
[`physical_visibility_phase6_microbenchmarks_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_microbenchmarks_2026-08-04.json).
Each sample executed 2,000 operations; five samples were recorded.

| Numerical boundary | Median per operation |
|---|---:|
| Jupiter dynamic target-profile resolution | 277.8 microseconds |
| Sirius invariant target-profile resolution | 2.9 microseconds |
| Direct-extinction spectrum interpolation | 92.2 microseconds |
| Response-weight validation pair | 118.9 microseconds |
| Full internal target-profile construction | 125.5 microseconds |
| Condition-target spectral integration | 70.1 microseconds |

These measurements identify two different next actions:

1. remove the second response-array validation walk only where the values came
   from the already validated immutable pack, while preserving the validating
   constructor for independent inputs; and
2. pilot a doctrine-free dense numerical boundary for dynamic color response,
   direct-extinction interpolation, and response-weighted target transmission.

The first is a Python trust-boundary repair. The second is only a native
candidate; it is not admitted by this checkpoint.

## Closed hypotheses

- Do not port the event solver: it owns less than 1% of profiled internal time.
- Do not add an exact-input geometry cache: almost every geometry input is
  unique.
- Do not cache or bin Jupiter profiles approximately: every measured context
  is distinct and approximate reuse would alter truth.
- Do not treat cProfile wall time as an event-budget result.
- Do not use performance evidence as scientific validation.

## Next gate

The next bounded gate is a Python-only trust-boundary pilot followed by an
unprofiled event replay. If a stable spectral numerical cluster still
dominates, a native pilot must retain the Python implementation as the
differential oracle, cover the complete admitted environmental and planetary
domains, preserve deterministic concurrency, and leave manifest, policy,
domain, failure, provenance, event, and result-construction semantics in
Python.
