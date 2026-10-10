# VED-011 marriage exact-reuse performance validation

**Date:** 10 October 2026. **Status:** accepted locally; focused, broader and
both full real-kernel HTTP cases pass, with exact response equivalence.

This pass follows the [native arithmetic optimization](MARRIAGE_ELECTION_PERFORMANCE_2026-10-10.md).
Both passes remain local and uncommitted, on engine `03dc7e0` with the unchanged
version 6.9.9 and required native binary. The earlier receipt retains the first
pass's fingerprints and measurements as historical evidence.

## Implementation and reuse boundary

The warmed four-day profile after native arithmetic optimization attributes
5.85 cumulative seconds to 2,794 repeated TT/TDB transformations, 2.66 seconds
to 4,890 record-argument calculations, 2.07 seconds to 909 frame-angle
calculations and 2.65 seconds to frame rotations. These are nested profiler
times, not additive contributions or production latencies. The initial paired
experiment showed that single-body cases benefit differently; a complete
request is also measured before asserting practical improvement.

The [bounded reuse standard](../02_standards/BOUNDED_COMPUTATION_REUSE_STANDARD.md)
defines the governing deterministic computation, source/owner boundaries and
admission contract. One private, standard-library helper is independent of
marriage. Five request-owned memos reuse clock conversion, record arguments,
frame polynomials, complete frame angles and trigonometric pairs.

There is no rounded epoch key, interpolation, cross-request shared state,
cached exception or cached mutable result. Exact key fields include the
complete differential and coarse/precise mode where relevant. Storage is
bounded and creation-thread ownership is enforced. Numerical/source policy,
all existing tolerance and resource limits, and the public engine/REST
contracts are unchanged. No native source or build change is made in this pass.

Source-bound admission and work counters remain outside the new pure memos.
Their hit statistics measure removed arithmetic; they do not redefine public
evaluation, reader or root-iteration counts. Code decomposition follows the
existing Moira differential state and explicit frame polynomial/trigonometric
objects; no secondary engine supplies a formula or execution pattern.

## Validation plan and retained diagnostics

Receipt directory: `C:\dev\outputs\ved011-marriage-reuse-2026-10-10`.
All execution uses the project Python 3.14.3 with downloads disabled, strict
known-issue expiry and the existing discovered DE441/LE441 resource. The native
binary and kernel remain those identified in the first performance receipt.

Focused checks cover exact adjacent-epoch/signed-zero keys, every differential
field, zero/finite capacity and eviction, failure recovery, mutable payload
rejection, separate dependency scopes, invalidation, cross-thread rejection,
garbage-collection of finished scopes, and an actual non-marriage NAIF clock
consumer. Marriage checks compare the original frame arithmetic schedule
across the admitted date range and coarse/precise modes, compare all nine
bodies and combined signals with reuse disabled, and retain source and work
accounting. A warmed record-argument memo must not bypass a reader budget.

The existing rational derivative, real serving-record, frame, observer,
source-seam and full-composition tests remain applicable. Both full HTTP cases
ran again, including unavailable evidence at high latitude. Complete
worked-case payloads were compared with the preceding accepted implementation;
the native fingerprint is unchanged, and no response-field normalization was
performed in this pass.

The first added non-marriage test used a nonexistent `tt_to_tdb_jd` name; it was
corrected to the actual `tt_to_tdb` API. An initial cache-statistic assertion
expected twelve polynomial hits where six are correct: the outer angle memo
serves the repeated calls. Both are test-authoring repairs; no numerical
tolerance, expected scientific result or existing fixture was changed. Initial
failed receipts remain alongside subsequent acceptance evidence.

## Complete baseline telemetry and paired timing

The unchanged first-pass implementation completed the full six-hour HTTP test
again before this pass's acceptance. Its complete window and personal-direct
responses exactly match the first performance receipt, without normalizing
any response field. Telemetry retained an 8,192-entry observation window for
each operation and counted exact repeated keys:

| Operation | Calls | Repeated exact inputs | Time spent recomputing those inputs |
|---|---:|---:|---:|
| TT/TDB differential | 182,729 | 62,265 | 36.04 seconds |
| Record arguments | 277,220 | 60,814 | 9.91 seconds |
| Frame angles | 74,158 | 18,140 | 12.18 seconds |

These measurements include the full test's additional interior validation;
they are telemetry, not a claim that every repeated key survives the final
cache capacities. The instrumented HTTP calculation took 553.27 seconds;
the full test took 604.69 seconds. The earlier uninstrumented first-pass HTTP
measurement remains 497.29 seconds. Concurrent focused validation and
instrumentation prevent treating the newer baseline as a controlled latency
comparison.

The reproducible paired benchmark runs the same warmed reader, fresh request
scopes and alternating execution order, disabling only the new memos for its
reference. It requires identical evidence, sources and public work counters
before recording a timing. The final shared-sky workload uses 32 epochs and
all nine bodies, both precision modes, plus combined solar/lunar signals.
The first four-epoch diagnostic was too short for stable timing and is retained
as an exploratory run, not the principal measurement.

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts/benchmark_marriage_reuse.py --output C:/dev/outputs/ved011-marriage-reuse-2026-10-10/paired-reuse-final.json --repetitions 3
```

`paired-reuse-final.json` contains all twelve successful pairs, exact evidence
hashes, per-operation hits/misses/capacities and both execution orders.
`commands.json` records the exact broader validation and full HTTP invocations.

| Case | Median reference seconds | Median reuse seconds | Median paired speedup |
|---|---:|---:|---:|
| Four-day Moon crossings | 3.926 | 3.681 | 1.067x |
| Four-day Rahu crossings | 0.403 | 0.366 | 1.088x |
| Four-day Venus crossings | 1.094 | 0.929 | 1.171x |
| Shared sky, 32 epochs | 2.365 | 1.796 | 1.326x |

These are observed component timings; single-body search benefits less than
multi-body composition. They do not predict one universal full-request gain.

## Broader regression acceptance

The combined slice passes **372 tests**, with **26/26 DE441 resource uses**
executed. It includes 29 new reusable-helper and marriage-admission checks,
the existing complete marriage unit/server corpus, real geometry and budget
checks, native parity/nutation/import, SPK/DAF, public-surface and docstring
governance tests. All arithmetic and scientific thresholds remain unchanged.

Six unrelated optional checks skip: two legacy `jplephem` comparisons and four
small-body file checks requiring `centaurs.bsp`, `sb441-n373s.bsp` or
`minor_bodies.bsp`. No missing dependency or kernel was installed to run those
unrelated checks. Both long real HTTP cases are selected separately.

Ruff and Python 3.10 grammar pass for all six computational/test/benchmark
Python files in this pass. The final runtime/source state is fingerprinted
before full HTTP acceptance. The benchmark workload was strengthened after
the earlier exploratory measurements; numerical runtime code is unchanged.

## Full HTTP acceptance

The six-hour Delhi window calculation completes in **409.195 seconds**, versus
**497.286 seconds** at the preceding accepted native checkpoint: **1.215x**
faster, or **17.7 percent less elapsed time**, from 8.3 to 6.8 minutes.
The complete canonical JSON response matches exactly, with no fields removed
or normalized. The personal direct request/response also matches exactly.
The 45 cells, 46 bands, 62 evidence parts, 613 findings, 88 supporting
certificates and all public work counters are preserved. This is regression
equivalence under the same declared numerical model, not a new independent
full-profile astronomical oracle.

The high-latitude HTTP assessment completes in **347.893 seconds**, versus
**442.404 seconds** previously: **1.272x** faster, or **21.4 percent less elapsed
time**, from 7.4 to 5.8 minutes. Its complete response also matches exactly.
Unavailable Lagna and planetary apparition evidence, the original reasons,
raw witnesses and `not_certified` status remain intact. The 167,429 evaluations,
1,113,819 reader calls and 59,056 root iterations are unchanged.

Both full tests pass in 821.33 seconds overall, with **4/4 DE441 resource uses**
executed and no skips. The individual tests take 459.00 and 357.93 seconds,
including assertions beyond the timed HTTP calls. The personal direct worked
case is byte-identical to its predecessor. `full-response-equivalence.json`
records all three comparisons, raw receipt fingerprints and timings; its
normalization lists are empty.

The validation runner reads cache statistics only when the ordinary request
receipt is built. It does not instrument individual numerical evaluations.
`full-reuse-statistics.json` retains these observations. Multiple receipt
builds from the same request are repeated observations, not independent runs;
the following table uses the final state of each request once:

| Reused computation | Window-request hits | High-latitude-request hits |
|---|---:|---:|
| TT/TDB differential | 60,789 | 51,359 |
| Record arguments | 60,814 | 53,874 |
| Frame polynomials | 21,293 | 19,963 |
| Frame angles | 14,282 | 9,852 |
| Cosine/sine pairs | 214,244 | 178,353 |

These are 371,422 and 313,401 successful memo hits, respectively. Each cache
remains within its declared capacity, with 24,576 entries total across the five
new memos at the end of each full request. Entry count does not imply a fixed
process-memory byte bound. The original numerical and resource counters remain
unchanged despite the eliminated helper computations.

These are observed whole-request timings on this host. The earlier baseline
is historical and machine load is not controlled; brief documentation checks
also overlapped the new window run. Paired same-process component measurements
provide separate corroboration. Full synchronous calculations still take
minutes; no interactive latency or service-level guarantee is implied.

## Changed owners and lineage check

| Owner | This pass's change |
|---|---|
| `moira/_bounded_memo.py` | Private bounded, thread-owned reuse with exact byte keys, immutable payload validation, failure retry and inspectable statistics. |
| `moira/_muhurta_marriage_astronomy.py` | Request-local TT/TDB and record-argument reuse; supplies the frame owner's cached trigonometric pairs to the original rotations. |
| `moira/_muhurta_marriage_frames.py` | Explicit differential key, shared precession polynomials, cached frame angles and cosine/sine pairs; preserves arithmetic order. |
| `tests/unit/test_bounded_memo.py` | Adversarial reusable-helper contracts and a non-marriage NAIF clock consumer. |
| `tests/unit/test_muhurta_marriage_reuse.py` | Original-schedule exact-bit comparisons, scope/reader lifetime, all-body composition, source isolation and budget-boundary checks. |
| `scripts/benchmark_marriage_reuse.py` | Reproducible alternating-order benchmark with exact evidence/source/counter admission. |
| Reuse standard and this receipt | Governing reuse contract, measurements, provenance, limitations and acceptance. |
| Marriage standard, prior performance receipt, implementation plan and remaining-work register | Link current implementation/acceptance while preserving historical checkpoints. |

The implementation starts from the named immutable computational object and
exact input identity. Keys contain every numerical state field rather than
inferring equivalence from a sampled output. Frame decomposition follows the
precession polynomials and trigonometric pairs already present in Moira's
operation schedule. Reader admission, source boundaries, doctrine and event
assembly stay in their existing owners. Inspection found no new external-engine
formula, index convention, branch repair or secondary-parity authority claim.

The earlier native optimization, its tests and build settings are preserved.
This pass adds no dependency, public selector, REST schema, version change,
new VED-011 purpose, background service or website implementation. Source
publication remains a separate action; these changes are local and uncommitted.

## Final acceptance and fingerprints

The final latest-per-test reconciliation contains **374 distinct passes**,
six disclosed unrelated skips and no unresolved failures. The combined
regression and full HTTP XML receipts own that count; repeated diagnostic and
focused runs do not inflate it. Every selected real-kernel resource use ran.

The six computational/test/benchmark files and native binary match the source
state frozen before full HTTP validation. Source fingerprints normalize UTF-8
text to LF; binary and evidence receipts use their actual byte fingerprints.

| Receipt | SHA-256 |
|---|---|
| `source-state-final.json` | `d77fa50fa83ee1de7841ca60391f61be32857773fc77bb080cef69ae22fa4727` |
| `latest-results-final.json` | `d5d1540cef81c48a99a59256f1089b8d6e644f740c444fc8403df483be492735` |
| `full-response-equivalence.json` | `74631e00781a79bb187619a37e6124fc2fb14ebdc6d91f4a07fc5b08249dea1d` |
| `full-reuse-statistics.json` | `544fc68ace1eb6cb1d10a5c82e254404b57ce1424bb05206ce7fa1446ca892a9` |
| `paired-reuse-final.json` | `1099665ba9a537ed3bed41e170b62508d08bfe120e88fe3351ad53a6afbef97d` |

The original scientific fixtures and tolerances, required native binary and
DE441/LE441 resource are unchanged. Final static gates cover scoped Ruff,
Python 3.10 grammar, changed-line whitespace, release-facing documentation,
release identity, Hellenistic and REST inventories, website publication
metadata and canonical-to-generated wiki synchronization.
