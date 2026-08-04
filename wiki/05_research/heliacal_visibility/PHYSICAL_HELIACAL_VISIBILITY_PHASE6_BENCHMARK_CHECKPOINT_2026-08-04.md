# Physical Heliacal Visibility Phase 6 Benchmark Checkpoint

Date: 2026-08-04
Status: In progress; baseline recorded; native work not admitted
Starting engine revision: `7e7e2886bc72dfd6e55231902ecd4a73d6b47832`
Evidence class: Performance only, not scientific validation

## Governing object

Phase 6 asks whether the already admitted physical single-epoch assessment and
visibility-margin event solver need a higher native boundary. Python continues
to own policy, manifest and validity decisions, event semantics, typed failure
states, provenance, and public result assembly. A missed timing budget is a
reason to investigate; it is not permission to move those meanings into C++.

The benchmark replays the two independently validated Phase 3 workloads:

- Jupiter, morning first rising, 30-day search from JD `2460050.5`, at
  latitude 35 degrees and longitude 35 degrees; and
- Sirius, morning first rising, 20-day search from JD `2461240.5`, at
  latitude 30 degrees and longitude -90 degrees.

Both use the same source-locked dark-sky-anchor policy and the same
visibility-margin-zero event semantics as the Phase 3 goldens.

## Reproducible harness and resources

The initial harness is
[`scripts/benchmark_physical_visibility_phase6.py`](../../../scripts/benchmark_physical_visibility_phase6.py).
The generated receipt is
[`tests/artifacts/benchmarks/physical_visibility_phase6_baseline_2026-08-04.json`](../../../tests/artifacts/benchmarks/physical_visibility_phase6_baseline_2026-08-04.json).

The measured engine checkout was a clean detached worktree at the starting
revision. Its native extension was rebuilt in that worktree from that
revision, rather than reusing the newer binary in the mixed development tree.
The receipt binds the rebuilt binary by SHA-256.

Environment and resources:

- Python `3.14.3`, 64-bit CPython;
- Microsoft Windows 11 Home `10.0.26200`, build `26200`;
- AMD Ryzen 7 8700F, 8 cores and 16 logical processors;
- 32 GiB installed physical memory;
- benchmark harness SHA-256
  `d9e7db55588d51da5f154369f44f284c984679cb0929fb583a7145bd2e88a252`;
- freshly rebuilt native binary SHA-256
  `1d83f96ed66f26b9976e5aa31541aabcd7d9b2b9b32e40ac3059db86c50cc2e3`;
- JPL DE441/LE441, content-derived summary label `DE-0441LE-0441`, with
  admitted lunar tidal acceleration `-25.936` arcseconds per century squared;
  and
- physical visibility pack `1.2.0`, manifest SHA-256
  `cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c`.

All resources were explicit and local. `MOIRA_NO_DOWNLOAD=1` was active. The
harness rejects a dirty engine checkout, a mismatched pack manifest, a missing
kernel, any fail-closed fast path, a changed result across repeats, an event
outside the Phase 3 half-second regression tolerance, or an uncertified
crossing result.

## Pre-optimization development budgets

These are reference-machine development gates for the exact workloads, not
public service-level promises:

| Workload | Budget |
|---|---:|
| First evaluated assessment in a fresh process | at most 3.0 s |
| Warm public assessment median | at most 0.5 s |
| Jupiter 30-day physical event median | at most 15.0 s |
| Sirius 20-day physical event median | at most 15.0 s |

The budgets were frozen before any Phase 6 optimization or native code was
implemented. First-call time includes initial reader and pack work and is
diagnostic; it does not by itself identify a native candidate.

## Initial clean-revision baseline

The sizing run used five warm assessment samples, three complete pack loads,
and one unprofiled sample for each expensive event workload:

| Workload | Observed | Gate |
|---|---:|---|
| First evaluated assessment | 1.940 s | Pass |
| Full pack validation median | 0.268 s | Diagnostic |
| Warm public assessment median | 0.269 s | Pass |
| Jupiter 30-day event | 36.446 s | Fail |
| Sirius 20-day event | 21.778 s | Fail |

The event samples are sufficient to size the next investigation but not to
make an admission decision. `--assert-budget` therefore requires at least
three event samples, five assessment samples, and three pack-load samples.

The Jupiter result used 28,651 scalar evaluations and returned exact admitted
JD `2460070.591375516`. The Sirius result used 20,341 scalar evaluations and
returned exact admitted JD `2461255.950317484`. Both retained
`certified_lipschitz_zero_enclosure`. These are regression protections for the
timed path, not new scientific validation claims.

## Verification

The repository-owned Phase 3 golden test was replayed separately against the
same clean worktree, exact pack, DE441 resource, and rebuilt native binary:

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_PHASE3_VISIBILITY_PACK = "<exact-1.2.0-pack-directory>"
.\.venv\Scripts\python.exe -m pytest `
  tests\integration\test_physical_visibility_phase3_goldens.py `
  -q --tb=short
```

Result: `2 passed` in 75.1 seconds, with no skip or failure. The harness
receipt identified DE441 in all four planetary-resource acquisitions. The
test's two Phase 3 event-time comparisons retain their existing 0.5-second
absolute tolerance; no fixture or tolerance was changed.

## Admission decision

No native work is admitted yet.

The event budget failures prove that investigation is justified, but they do
not prove that a new C++ kernel is the correct repair. A preliminary diagnostic
profile was deliberately not promoted into the protected receipt because it
ran before the clean-revision native binary was rebuilt. It suggested that
cost is distributed across event sampling, ephemeris/horizontal reductions,
target-profile reconstruction, spectral weighting, and already-native
nutation/SPK primitives. That distribution must be reproduced against the
revision-bound binary before it can govern implementation.

## Next bounded work

1. Repeat the profile against the clean-revision native binary and emit a
   separate profile receipt.
2. Microbenchmark repeated event-invariant target-profile resolution and
   spectral-response validation separately from geometry-dependent LUT work.
3. Determine whether event-local reuse can remove repeated invariant work
   without changing public semantics, numerical tolerances, or provenance.
4. Run the three-sample admission benchmark after any Python-only structural
   improvement.
5. Admit a native kernel only if a stable, doctrine-free numerical cluster
   still dominates the missed budget and can retain the Python implementation
   as a full differential reference.

No engine calculation, native source, public contract, policy, data pack,
fixture, tolerance, release identity, website, or deployment changed at this
checkpoint.
