# VED-011 marriage performance validation

**Date:** 10 October 2026. **Status:** optimization accepted locally; complete
native, marriage and full HTTP acceptance passed.

This receipt preserves the first native-arithmetic performance checkpoint.
The subsequent [exact-reuse pass](MARRIAGE_ELECTION_REUSE_2026-10-10.md)
records further changes and their separate acceptance; the measurements and
fingerprints below remain historical to this first pass.

This follows the source-published marriage package at engine
`03dc7e0e1f5f2668cb832de11c8e2c72250d2d4d`, generated wiki
`2ce8edc1e9d6c5c07f1e94fc7faf626d2743f123`. The
[original validation receipt](MARRIAGE_ELECTION_VALIDATION_2026-10-10.md)
retains its original measurements, failures and source fingerprints.
This work changes execution cost, not the selected classical rules or
the meaning of astronomical certification.

## 1. Measured bottleneck and implementation boundary

A warmed DE441 four-day Moon/Rahu/Venus crossing profile attributed 69.77 of
92.28 cumulative seconds to the interval-Chebyshev recurrence: approximately
76 percent of this profiled workload. It made 15,534 recurrence calls and
hundreds of millions of Python calls, largely for immutable interval and
differential operations. These profiler timings are diagnostics, not a
production latency benchmark.

The native helper translates the existing `_cheb_python` operation schedule.
Python retains the reference, serving record selection, time/coordinate
policy, light-time branch families, interval isolation, source findings,
exception targets, completeness decisions and serialization. Native code
fuses only the repeated arithmetic for one coefficient series and its
derivative. Its input/output fields remain the named differential's value,
rate, common center, radius and centered flag.

Both rounded recurrence orders, `a+b-c` and `a+(b-c)`, remain in the hull.
Every outward rounding, whole-domain primitive-error guard and centered
intersection is retained. The native translation unit disables contraction,
reassociation and link-time rewriting locally; unrelated native kernels
retain their build settings. The helper refuses non-nearest host rounding,
non-gradual underflow and invalid numeric states. It retains the existing
conditional arithmetic model; it does not establish platform-independent
formal verification or physical ephemeris accuracy.

There are no changes to tolerances, time steps, work limits, counter
accounting, supporting-history domains, public Python/REST selectors or
classical profile coverage. No new dependency or data resource is introduced.

## 2. Reproducible paired benchmark

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts/benchmark_marriage_enclosures.py --output C:/dev/outputs/ved011-marriage-performance-2026-10-10/paired-crossing-benchmark.json --repetitions 2
```

The standalone benchmark uses the same warmed serving reader with fresh
request caches, alternating Python/native execution order. All roots,
uncertainty intervals, gap records, supporting certificates and work counters
must serialize identically before a timing pair is recorded. It temporarily
selects the Python reference only inside its own single-threaded process.

| Four-day case | Python reference, seconds | Native helper, seconds | Speedup |
|---|---:|---:|---:|
| Moon, first pair | 17.349 | 4.587 | 3.782x |
| Moon, reversed pair | 17.826 | 4.604 | 3.872x |
| Rahu, first pair | 1.214 | 0.460 | 2.641x |
| Rahu, reversed pair | 1.239 | 0.451 | 2.748x |
| Venus, first pair | 3.376 | 1.208 | 2.794x |
| Venus, reversed pair | 3.576 | 1.250 | 2.861x |

These are component performance measurements and exact regression
equivalence, not an independent full-profile oracle or a universal speed
guarantee. Raw results and diagnostic profiles are retained under
`C:\dev\outputs\ved011-marriage-performance-2026-10-10`.

## 3. Numerical and native-boundary evidence

The project Python 3.14.3 rebuilt the required native extension using
`python -m pip install -e . --no-deps --no-build-isolation`; the full command
uses `.venv\Scripts\python.exe`. Version remains 6.9.9.

The initial native-primitive slice passed 23 tests with three executed DE441
resource uses and no skips. It covers:

- Exact binary-state parity, including signed zero, on centered and
  uncentered arguments, four radii, record endpoints, 0–32 degree coefficient
  series, small/large magnitudes, subnormal inputs and cancellation.
- Independent rational values and first/second derivatives of expanded T1, T2, T4 and T8
  polynomials at 33 rational arguments each; bounds must contain exact values.
- Eight actual DE441 routes at four epochs spanning the admitted 1900–2100
  domain, three endpoint/interior argument boxes and every axis, compared
  with the unchanged Python recurrence without any tolerance.
- Rejection of empty/nonfinite coefficients and invalid interval/radius
  states, plus preservation of explicit numerical-unavailability errors.

The optimized backend fingerprint is
`12b5552f993954a46e3e7c2a1e90af767ac312c3cbf9ba5765ad9cb85e1f55bb`.
The serving DE441/LE441 kernel remains
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`.

An isolated native executable also compiles the exact helper source with
MSVC 19.50.35730.0 and the same strict floating-point options. Nearest
rounding succeeds; downward, upward and toward-zero rounding are rejected.
Separately enabling x86 flush-to-zero and denormals-are-zero is rejected;
restoring the original model succeeds. The seven host-mode checks are in
`arithmetic-host-check.log`, with the standalone harness sources alongside
it. They exercise real host modes, not substituted Python exceptions, and
run outside the server/test processes.

The combined marriage, public-surface, native parity, nutation, SPK and DAF
regression slice passes **343 tests**, with **24/24 DE441 resource uses**
executed. Six unrelated checks skip: two optional `jplephem` comparisons and
four legacy small-body file checks (`centaurs.bsp`, `sb441-n373s.bsp`,
`minor_bodies.bsp`). No dependency or kernel was installed for those checks.
The two full HTTP tests are deliberately selected separately. The XML and
log are retained in `combined-regression.xml` and `combined-regression.log`;
`commands.json` records the exact build, benchmark and test invocations,
selected files, interpreter, working directory and environment.

## 4. Full composition acceptance

The original six-hour Delhi HTTP window calculation completes in **497.29
seconds**, versus **1,701.96 seconds** in the pre-change receipt: an observed
**3.42x** speedup, from 28.4 to 8.3 minutes. Its complete response is identical
after changing only `search_receipt.native_backend_sha256` to the previous
identity for comparison. It retains all 45 cells, 46 bands, 62 evidence parts,
613 findings and 88 supporting certificates. The 188,201 evaluations,
1,286,318 reader calls and 65,877 root iterations are unchanged; the widest
band remains 3.745664656 seconds. The result remains a completed restricted
search with no eligible or indeterminate cells.

The high-latitude HTTP instant completes in **442.40 seconds**, versus
**1,510.44 seconds** previously: **3.41x** faster, from 25.2 to 7.4 minutes.
Its complete response also matches after substituting only the native
backend fingerprint. Lagna and both planetary availability contexts retain
their unavailable states, with the exact original Jupiter/Venus
undefined-horizon reasons and all raw witnesses. It retains 167,429
evaluations, 1,113,819 reader calls and 59,056 root iterations; incomplete
coverage remains explicitly `not_certified`.

Both full HTTP tests pass: the complete tests took 565.53 and 457.31 seconds
respectively, including their assertions beyond the measured HTTP call.
All four selected DE441 resource uses executed, with no skips. The personal
direct request/response worked-case file is byte-identical to its original.
`full-response-equivalence.json` retains the exact comparisons and hashes
for all three worked cases. Elapsed timing lives outside the calculation
responses. End-to-end timings compare the archived run with this validation
run, whose machine load is not controlled. The paired component benchmark
above provides same-process, alternating-order corroboration of the speed gain.

Full calculations still take minutes on this host; this is a measured
optimization of the complete synchronous calculation, not a background-job
service or a latency guarantee for every admitted request.

## 5. Changed owners and scope

| Owner | Change |
|---|---|
| `moira/_muhurta_marriage_astronomy.py` | Retains the Python recurrence and delegates its exact operation schedule through the private native bridge. |
| `src/native/include/marriage_enclosure.hpp`, `src/native/src/marriage_enclosure.cpp` | Defines the named differential-state transport and executes the fused outward-rounded recurrence with host-model guards. |
| `src/native/bindings/moira_native.cpp` | Binds the private primitive; curated public engine/REST contracts are unchanged. |
| `CMakeLists.txt` | Adds the numerical translation unit with locally strict floating-point and no-LTO settings. |
| `tests/unit/test_muhurta_marriage_enclosure.py` | Adds bit-exact Python-reference parity, independent rational derivatives, actual serving-record and invalid-state checks. |
| `scripts/benchmark_marriage_enclosures.py` | Provides the reproducible paired benchmark with complete-result/counter equality as an admission condition. |
| Source standard, this receipt and remaining-work register | Document ownership, measurements, acceptance and operational limits. |

The governing object is the existing named differential state. The native
schedule follows its explicit Moira reference and keeps both rounding-order
branches; its compact transport follows those declared state fields. Source
policy and astronomical assembly stay in their existing Python owners.
Independent rational arithmetic and serving-coefficient evidence support
correctness; timing and archived-payload equality have their separate
performance/regression roles. No secondary astrology engine supplies this
implementation's formulas or thresholds.

This checkpoint is local implementation work. No commit, push, release,
deployment, website adoption or additional VED-011 purpose is included.

## 6. Final acceptance and fingerprints

The latest-per-test reconciliation has **345 distinct passes**, six disclosed
unrelated skips and no unresolved failures. Repeated primitive and rational
cases count once. The four strengthened second-derivative cases also pass
in `rational-second-derivative.xml`. The computational source and native
backend stayed fixed throughout full HTTP acceptance; the stronger test
assertions do not change that executable path.

| Receipt | SHA-256 |
|---|---|
| `source-state-final.json` | `bb30f3b0d5808061f6dbae326248a201b96651f33c1865e8649300b5d8342c02` |
| `latest-results-final.json` | `1405f0316b9af388b9bbf889fee7b99d8a3844692ea0d3b0aea949106e12a0f9` |
| `full-response-equivalence.json` | `617d926871ec130ac9c1d1ec8ccd174b3beb70bdae744f44cfb5963ace23b699` |

The source manifest fingerprints all seven changed runtime/build/test/benchmark
files using normalized UTF-8/LF text, and separately identifies the serving
native binary. Scoped Ruff, Python 3.10 grammar, changed-line whitespace,
documentation consistency, release identity, Hellenistic generated inventories,
REST inventory, website publication metadata and generated-wiki synchronization
all pass as the final static/documentation gates. Original scientific baselines and
their tolerances remain unchanged.
