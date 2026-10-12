# VED-017 bounded Gochar windows validation

Date: 11 October 2026. Baseline: engine `main`, version 6.9.9,
`524a8d3caf3470634080fc930479625e0f7f29c9`. Status: LOCAL_COMPLETE for the
bounded modern whole-sign profile. The authorized 12 October source-publication
checkpoint is recorded below; release and deployment remain separate.
Owner: [window standard](../02_standards/GOCHARA_WINDOWS_STANDARD.md).
The [approved seven-stage plan](../06_roadmap/VEDIC_GOCHAR_WINDOWS_IMPLEMENTATION_PLAN_2026-10-11.md)
and [source research](../06_roadmap/VEDIC_GOCHAR_WINDOWS_SOURCE_RESEARCH_2026-10-11.md)
define the admitted source and product scope.

## Runtime and preservation

All Python execution uses `C:\dev\moira\.venv\Scripts\python.exe`, Python 3.14.3.
Base import reports 6.9.9 and `moira/_moira_native.cp314-win_amd64.pyd`.
`MOIRA_NO_DOWNLOAD=1`; pytest also uses `MOIRA_STRICT_KNOWN_ISSUES=1`.
`tests/KNOWN_ISSUES.yml` remains empty. The serving resource was discovered via
`moira._kernel_paths.find_planetary_kernel`: `C:\Users\nilad\.moira\kernels\de441.bsp`.
Harness receipts identify DE441. No ephemeris download, native rebuild, source
table rewrite, threshold widening or test suppression was performed.

The original research/plan documents and the register's research link were
present before implementation and are retained. No website/Urania, source-book,
version/dependency or unrelated application work is included. Source publication
and deployment have not been performed in this implementation turn.

At the 11 October implementation checkpoint, the `origin/main` tracking ref was three commits ahead
of this tested baseline, ending at `7a86b33` (public API hardening). Its changed
paths overlap `tests/unit/test_api_surface_adversarial_audit.py`. No fetch,
merge or publication was performed here. A subsequent publication must
reconcile that upstream guard and rerun the affected acceptance checks; the
local results below do not claim to validate an unmade merge. The 12 October
publication checkpoint below records the subsequent completed reconciliation.

## Change ownership

| Owners | Changes |
| --- | --- |
| `moira/gochara_windows.py` | Frozen admission/result/evidence contracts, engine/civil entry points, capabilities, exact stdlib wire encoding and coverage invariants. |
| `_gochara_window_astronomy.py` | All twelve serving sidereal systems, five live anchor propagations, clock-domain intersection and resource identity receipts. |
| `_gochara_window_search.py`, `_gochara_window_partition.py` | Complete seven-stream isolation, exclusion records, conservative event classification, atomic partition and finite allocation/work bounds. |
| `moira/_event_search/` | Shared arithmetic, frames, clocks, astronomy, isolation, budgets and request-owned reader loans; original marriage module aliases preserve consumers. |
| `pyproject.toml` | Add the new private package to explicit distribution discovery; dependency classes and native build configuration remain unchanged. |
| `.gitattributes` | Fix specification LF bytes and preserve raw evidence files across Windows/POSIX checkouts so publication cannot invalidate retained digests. |
| `gochara_dated.py`, `gochara_policy.py` | Shared once-per-request natal/BAV derivation and bounded forecast catalogue admission; existing snapshot choices remain unchanged. |
| Root/facade/Vedic exports and `_facade_vedic.py` | Twenty curated additive names and reader-bound calculation methods. |
| `moira_server/models/gochara_windows.py`, Gochar router/service/serializer and errors | Strict epoch/civil requests, typed success/error schemas, resource-free capabilities and byte-identical engine/HTTP encoding. |
| Tests and validation/benchmark scripts | Independent analytic/source cases, serving/ERFA/Horizons checks, concurrency, limits, memory and latency receipts. |
| Canonical wiki, generated reference/inventories and wiki mirror | Exact source admission, semantics, evidence, package reconciliation and generated API discovery. |

## Source and adversarial evidence

The unchanged `tests/fixtures/gochara_phaladeepika_26.json` remains the
independent doctrinal fixture. Window tests exercise all 36 directed Vedha
pairs under twelve zodiac rotations and each of six potential blockers (2,592
evaluations within 432 parameterized cases), including active/exempt witnesses.
Other cases cover baseline-only omission, raw BAV indexed by transit sign,
blocker-only changes and subject projection without participant removal.

Analytic signals provide independent expected direct, retrograde, double and
triple crossings, 0/360 wraparound, both tangent types, exact point sign
ownership, endpoint clipping, overlapping candidates, source seams and gaps.
Width alone cannot establish existence. Narrow contacts retain unknown count.
Partition tests establish closed request coverage, unique endpoint ownership,
sample/state consistency and conservative uncertainty. Real split queries
agree away from boundary enclosures. No sampled grid supplies completeness.

Both BAV choices and both Vedha modes are transported for all twelve systems
(48 combinations). Invalid numeric/civil/policy values, mutated nested limits,
counter exhaustion, exact JSON cap, strict unresolved rejection, numeric error
details, resource-free discovery and curated exports are exercised. Each
measured work cap is checked immediately below, at and above its needed value;
reader-cap tests first warm the serving owner's cache to expose bypasses.

## Astronomical evidence

The corpus specification was frozen before selecting candidates:
[`gochara_windows_validation_spec.json`](../../tests/fixtures/gochara_windows_validation_spec.json).
It separates four evidence classes: analytic completeness, classical source
fixtures, serving-model containment and primary astronomical comparison.

| Corpus | Cases | Outcome and meaning |
| --- | ---: | --- |
| Serving DE441 point containment | 48 system/epoch combinations, seven bodies at three points each | All twelve ayanamsas at epochs near 1900, J2000, 2025 and 2100. Source-record joins subdivide explicitly; this is internal containment, not an external oracle. |
| ERFA/SOFA frames and anchors | 48 | Seven reference/precession/nutation systems and five sovereign anchor records at four TT epochs. |
| Horizons body/system ingress matrix | 84 | Every one of seven classical bodies under every named ayanamsa, with a retained crossing and matched astronomical comparison. |
| Horizons retrograde/re-entry extension | 15 | Same-ray direct–retrograde–direct sequences for Jupiter, Mars, Mercury, Venus and Saturn. |
| Horizons zero-ray extension | 2 | Sun and Moon 360-to-0 crossings under Lahiri. |

The 101 external comparisons retain raw responses, exact requests, hashes,
candidate brackets, event evidence, coverage and serving identities under
[`tests/artifacts/oracle/gochara_windows_2026-10-11`](../../tests/artifacts/oracle/gochara_windows_2026-10-11).
Candidate daily scans choose fixtures only; the interval engine must separately
retain and classify each selected crossing. The final 84/15 reruns replay
checksum-verified responses from this session when exact query parameters
match; these are retained external observations, not additional independent
network observations. The two wraparound references were fetched live.

Horizons uses geocentric `500@399`, exact TT and observer quantities 2/20.
Targets are Sun 10, Moon 301, Mars 4, Mercury 199, Jupiter 5, Venus 299 and
Saturn 6, preserving planetary-system barycentres where Moira uses them.
Comparison is apparent equatorial direction and distance at each event-band
midpoint. Horizons' IAU 1976/1980/EOP observer frame and Moira's IAU 2006/2000A
frame differ; this is explicitly retained within the unchanged existing
0.35 arcsecond / 0.1 km authority envelope.

| External batch | Maximum direction residual | Maximum distance residual |
| --- | ---: | ---: |
| 84 body/system cases | 0.051057893 arcsec | 0.016590715 km |
| 15 retrograde sequence cases | 0.051532480 arcsec | 0.012198389 km |
| 2 wraparound cases | 0.050513366 arcsec | 0.000373153 km |

ERFA uses `p06e`, `nut06a`, `pnm06a`, `obl06` and `pmsafe` with the sovereign
reference/catalogue inputs. Thresholds remain 1e-8 degrees for polynomial
composition and 0.0004 degrees for the existing star-propagation comparison.
Those are angular/frame/model tests, not independent historical endorsement
of every named ayanamsa. No one-second external event-time claim is made.

The Raman Mercury case at UT1 JD 2460313.5–2460314.5 proves a directed crossing
but retains a **1.024536788-second** band at a requested one-second target.
Its explicit width qualification survives engine/REST; strict mode rejects
unaccepted width. This is expected numerical uncertainty, not a waived test
or an increased tolerance. Near-station evidence is compared in angular units.

## Focused review and repairs

**Verdict: APPROVE. Confidence: HIGH within the declared profile and numerical
model.** The focused code-review pass and subsequent repair checks leave no
unresolved P0/P1 findings. The review covered numerical exclusion/existence,
mutable evidence, resource borrowing, budgets, Pydantic/OpenAPI, synchronous
concurrency and generated discovery. It is a scoped review, not whole-engine
certification. Repaired findings and their verification follow.

| Issue exposed during development/review | Repair and independent check |
| --- | --- |
| Coarse and precise angular evaluations can choose different lifts at a sign ray. | Rebase periodic targets again after precision refinement; analytic +180/−180 regression and full real corpus. |
| Fresh endpoint calls can discard full-interval rounding/early-stop branches. | Prove brackets from the complete interval's center/rate family; a deliberately wide-family regression rejects the false proof. |
| A prewarmed owner's point cache can bypass borrowed-reader work accounting. | Create private point-cache state on every metered proxy; warm-owner cap, no-cache parity, concurrent engine and REST tests. |
| A proved crossing wider than the request was conflated with unknown existence. | Keep crossing evidence and independently mark unacceptable width/unresolved ownership; Raman real case and strict transport tests. |
| Nested evidence could contain boolean IDs or mutable reason/reference lists. | Reject inconsistent event/region/result construction and missing evidence reasons. |
| An open positive gap can have no representable binary64 interior timestamp. | Retain the gap as uncertainty, preserving individual events; use an owned request endpoint for a certain edge region. Adjacent-float boundary regression and final engine/REST run. |
| Response-model reordering changed exact JSON bytes used for output admission. | Validate typed projection then emit the shared engine encoding; engine/HTTP byte equality and exact cap checks. |
| Pydantic accepted numeric strings as Unix civil timestamps. | Require an explicit ISO calendar date/time prefix before aware-datetime validation; integer, signed, padded and decimal-string cases fail before astronomy. |
| Existing discovery guards expected five Gochar routes. | Reconcile the guards to the additive eight-route contract and explicit new root exports. |
| Explicit setuptools discovery omitted the newly created shared package. | Register `moira._event_search` and inspect the actual `build_py` output before admission. |
| Platform checkout normalization could change the byte-hashed corpus specification. | Pin its LF representation and retain raw evidence bytes through scoped Git attributes; repeat the retained-reference integrity check. |

The certificate is conditional on the declared rounded continuous surrogate
family, including its libm error assumption. It does not count floating-point
micro-oscillations inside an uncertainty band. Exact contacts and unresolved
event order remain conservative. Frozen-vessel validation cannot authenticate
a fabricated SPK computation. These are product qualifications, not hidden
validation substitutions.

## Commands and acceptance

All commands below use the project runtime, downloads disabled and strict known
issues. The initial existing Gochar unit/server baseline passed 349 cases.
Intermediate failures above were repaired and retained as regressions; an
earlier failed run is not counted as acceptance. Final command outcomes and
performance measurements follow.

```powershell
# Final targeted engine, REST, source, native-record and real-kernel slice.
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara_windows.py tests/server/test_server_gochara_windows.py tests/integration/test_gochara_windows_ephemeris.py tests/integration/test_gochara_windows_reference.py tests/integration/test_gochara_windows_artifacts.py tests/unit/test_api_surface_adversarial_audit.py tests/unit/test_muhurta_marriage.py tests/unit/test_muhurta_marriage_windows.py tests/unit/test_muhurta_marriage_visibility.py tests/unit/test_muhurta_marriage_traditions.py tests/unit/test_muhurta_marriage_reuse.py tests/unit/test_muhurta_marriage_enclosure.py tests/unit/test_muhurta_purpose_dated.py tests/unit/test_muhurta_election_repairs.py tests/server/test_server_muhurta_marriage.py tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py tests/unit/test_gochara_dated.py tests/server/test_server_gochara.py tests/server/test_server_gochara_dated.py tests/integration/test_gochara_dated_ephemeris.py -o addopts='--import-mode=importlib' -o junit_family=legacy --junitxml=C:/dev/outputs/ved017-final-targeted-pass2.xml -q

# Final explicit duration and byte-cap neighbors.
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara_windows.py -k 'duration_below or exact_size' -o addopts='--import-mode=importlib' -q

# Real shared-owner composition after extraction.
.\.venv\Scripts\python.exe -m pytest tests/integration/test_muhurta_marriage_ephemeris.py tests/integration/test_muhurta_election_repairs_ephemeris.py tests/integration/test_muhurta_marriage_traditions_ephemeris.py -o addopts='--import-mode=importlib' -q

# Finish the independent historical profiles in parallel workers.
.\.venv\Scripts\python.exe -m pytest tests/integration/test_muhurta_election_repairs_ephemeris.py -o addopts='--import-mode=importlib' --junitxml=C:/dev/outputs/ved017-shared-carryover.xml -q
.\.venv\Scripts\python.exe -m pytest 'tests/integration/test_muhurta_marriage_traditions_ephemeris.py::test_real_tradition_http_instant_and_windows[vv_vasantalakshmi_1935_marriage_ordinary.v1]' -o addopts='--import-mode=importlib' --junitxml=C:/dev/outputs/ved017-shared-vv-final.xml -q
.\.venv\Scripts\python.exe -m pytest 'tests/integration/test_muhurta_marriage_traditions_ephemeris.py::test_real_tradition_http_instant_and_windows[kp_1917_marriage_ordinary.v1]' -o addopts='--import-mode=importlib' --junitxml=C:/dev/outputs/ved017-shared-kp-final.xml -q

# Primary corpus tools. Fresh output directories are required on every run.
.\.venv\Scripts\python.exe scripts/validate_gochara_windows.py --external --output C:/dev/outputs/ved017-window-validation-2026-10-11-run1
.\.venv\Scripts\python.exe scripts/validate_gochara_windows.py --external --candidates C:/dev/outputs/ved017-window-validation-2026-10-11-run2/candidates.json --reuse-references C:/dev/outputs/ved017-window-validation-2026-10-11-run2 --output C:/dev/outputs/ved017-window-validation-2026-10-11-run3
.\.venv\Scripts\python.exe scripts/validate_gochara_windows.py --external --retro-only --candidates C:/dev/outputs/ved017-window-validation-2026-10-11-retro1/candidates.json --reuse-references C:/dev/outputs/ved017-window-validation-2026-10-11-retro1 --output C:/dev/outputs/ved017-window-validation-2026-10-11-retro2
.\.venv\Scripts\python.exe scripts/validate_gochara_windows.py --external --wrap-only --output C:/dev/outputs/ved017-window-validation-2026-10-11-wrap1
```

The final targeted run passes **1,426 tests in 341.74 seconds**, with no failures
or skips and all 87 required planetary-resource cases executed. The additional
duration/byte-cap slice passes four cases in 3.14 seconds. A prior broad run
found three stale root/method export expectations, including 44 root exports
and thirteen methods already present in the published VED-011 baseline; these
were verified against HEAD and reconciled without changing those products.
The focused export/REST rerun passes 94 cases, and the final broad run above
includes their repaired guards. Three new duration cases were added alongside
the byte-cap rerun after broad collection, giving 1,429 distinct accepted cases
across the broad and cap slices.

The final civil-string repair is followed by all 76 Gochar-window REST tests
passing in 49.70 seconds, including four new invalid timestamp-string cases.
This brings the distinct broad/cap/REST acceptance set to **1,433 cases**.
Its command is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_gochara_windows.py -o addopts='--import-mode=importlib' --junitxml=C:/dev/outputs/ved017-final-rest.xml -q
.\.venv\Scripts\ruff.exe check moira_server/models/gochara_windows.py tests/server/test_server_gochara_windows.py --no-fix
```

The final representable-gap repair adds one independent boundary case. The
complete Gochar-window unit and REST rerun passes **622 tests in 47.77 seconds**,
with no failures or skips, bringing this acceptance set to **1,434 distinct
cases**. Repeated tests are not added again to that count.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara_windows.py tests/server/test_server_gochara_windows.py -o addopts='--import-mode=importlib' --junitxml=C:/dev/outputs/ved017-final-boundaries.xml -q
```

After that final partition change, the complete window ephemeris, ERFA and
retained-reference integrity files pass **109 tests in 87.07 seconds**, with
all 63 required serving-resource cases run and no failures or skips. This
rerun includes all twelve point-enclosure systems, real re-entry and split
queries, cache-disabled parity, concurrent REST and reader-budget isolation.
These repeated cases add nothing to the distinct count. The accepted Horizons
corpus predates this final edge-only repair; the analytic adjacent-float test
and this real regression run verify the repaired partition.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_gochara_windows_ephemeris.py tests/integration/test_gochara_windows_reference.py tests/integration/test_gochara_windows_artifacts.py -o addopts='--import-mode=importlib' -o junit_family=legacy --junitxml=C:/dev/outputs/ved017-final-astronomy.xml -q
.\.venv\Scripts\ruff.exe check moira/_gochara_window_partition.py tests/unit/test_gochara_windows.py --no-fix
```

The initial combined real-history command completed the full MC window,
high-latitude snapshot, all three deterministic budget/reader-lifetime cases,
and the phase-carryover point case. After six passing progress records and no
failures, it was deliberately interrupted to avoid duplicating the remaining
profiles already running independently. Its interrupted process is not counted
as a clean full-suite exit. The five legacy MC cases had all completed; the
remaining files have separate complete-run receipts. Initial exploratory `-k`
selectors matching no cases are not acceptance evidence; exact profile node
IDs above were then executed.

The isolated carryover file passes **2 tests in 787.14 seconds**, the VV
instant/direct/window profile passes **1 test in 1,120.59 seconds**, and the KP
profile passes **1 test in 1,261.96 seconds**, with no failures or skips. They
retain their direct/HTTP projection, certified-cell, supporting-history and
reader-lifetime assertions. With the five completed legacy MC cases, all nine
distinct shared-owner real regressions are accounted for. This brings the
combined acceptance set to **1,443 distinct tests**; the MC progress receipt and
the complete-run JUnit files preserve the different execution evidence.

The initial run1 stopped on the width/existence conflation after 22 cases.
Run2 completed 84/84 after that repair; final run3 verifies the later full-family
endpoint proof and cache ownership repair. Accepted artifacts contain run3,
retro2 and wrap1; no failed run is presented as a completed corpus.

Python 3.10 syntax parsing succeeds for all 43 changed Python files, and a fresh
base import leaves Pydantic absent from `sys.modules`. Actual runtime execution
here is Python 3.14.3 only; no Python 3.10 runtime/ABI execution is claimed.
Scoped Ruff has no introduced findings: the baseline 60 root, five facade and
one server-model-init findings remain unchanged. No repository-wide clean-lint
or full-suite claim is made.

The standard's complete Python example executes against installed DE441 and
passes its participant, event and dated-sample assertions. Generated surfaces
are refreshed by their owning scripts. The following guards pass:

```powershell
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe scripts/generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
git -C moira.wiki diff --check
```

New canonical documents were registered with `git add -N` for the wiki
generator's tracked-file discovery; no source commit/push was performed.

Distribution inclusion is also checked by `setup.py build_py --build-lib
C:/dev/outputs/ved017-python-package-2026-10-11`. The isolated output contains
the new shared package. A copy of the unchanged installed CP314 native extension
is used only for its import smoke: from that output directory, the base engine
imports without Pydantic, a real strict Gochar window computes successfully,
and the optional REST result model validates it. This is a Python-package
layout/import check, not a freshly compiled wheel or a release. No native
source or native build option changed. All twenty new curated exports also
share object identity across their owning module, root, facade and Vedic API.

## Performance and synchronous transport

The final benchmark matrix contains **26 completed requests**: cold/warm
1-, 30- and 366-day requests for Lahiri and True Chitrapaksha, each with BAV
omitted/computed (24), plus two adverse near-station Raman/BAV requests.
The four matrix processes ran concurrently on this Windows host, alongside
intermittent validation jobs. These are contended-host measurements, not
isolated latency or a service SLA. Warm means a reused process/serving reader
with fresh request-owned caches. It need not be faster under host contention.

| System / BAV | 1 day cold / warm | 30 days cold / warm | 366 days cold / warm |
| --- | ---: | ---: | ---: |
| Lahiri / omit | 2.812 / 0.604 s | 15.582 / 15.636 s | 212.107 / 243.525 s |
| Lahiri / computed | 2.790 / 0.612 s | 15.502 / 15.534 s | 211.723 / 242.778 s |
| True Chitrapaksha / omit | 2.953 / 0.631 s | 16.979 / 16.571 s | 238.600 / 278.229 s |
| True Chitrapaksha / computed | 2.900 / 0.633 s | 16.814 / 16.144 s | 232.429 / 272.556 s |

The regular matrix starts at UT1 JD 2460676.5, with natal JD 2451545 and
28.6 N, 77.2 E for computed BAV. All 24 searches report resolved events under
their selected model. Annual requests have 209 merged events, 419 regions,
210 samples, at most 39,835 evaluations, 208,356 reader calls, 17,316 isolation
iterations, 6,968 subdivisions, 240 retained candidates and 10,662 evidence
units. Final payloads range from 5,037,619 to 5,129,863 bytes.

The Raman adverse request starts at 2460313.5 and takes 3.865 / 1.435 seconds,
retains two events/five regions, and honestly reports unresolved width. Its
payload is 51,280 bytes. A narrower requested width was not substituted.

Per-process peak resident working set is 1,748,803,584–1,754,513,408 bytes for
the regular matrix, about 1.63 GiB. This cumulative Windows process measurement
includes mapped/shared kernel pages and startup resource verification; it is
not an estimate of Python cache allocation or additive concurrent RAM. The
receipts also retain before/after resident size. Cache entries remain bounded:
4,096 for most exact-input stores, 8,192 for pair/record-argument stores,
1,024 for clock jets and 256 for the clock base cache. Every row includes
actual hit/miss/current-size measurements. Disabling caches preserves natal,
state, sample, event, region, exclusion and coverage values exactly.

Real synchronous REST workers are also measured using the serving DE441
engine, both Lahiri and True Chitrapaksha one-day requests. A recorded run
takes 1.787 seconds sequentially and 2.623 seconds concurrently for the two
requests. Both byte streams equal their corresponding engine results. This
tests worker/context isolation; it does not promise throughput scaling.
A separate real Uvicorn loopback timeout/disconnect test confirms that the
bounded worker finishes, restores context and leaves the reader usable for
the next request. Server concurrency was not benchmarked with annual payloads.

Raw performance receipts are retained under
[`tests/artifacts/benchmarks/gochara_windows_2026-10-11`](../../tests/artifacts/benchmarks/gochara_windows_2026-10-11).
They were rerun after the cache-ownership and full-family bracket repairs.
Earlier exploratory timings do not govern the published limits.

```powershell
# Executed for each system below, once without --bav and once with --bav.
.\.venv\Scripts\python.exe scripts/benchmark_gochara_windows.py --system Lahiri --concurrent-processes 4 --output C:/dev/outputs/ved017-windows-benchmarks-2026-10-11-final/lahiri-omit.json
.\.venv\Scripts\python.exe scripts/benchmark_gochara_windows.py --system Lahiri --bav --concurrent-processes 4 --output C:/dev/outputs/ved017-windows-benchmarks-2026-10-11-final/lahiri-bav.json
.\.venv\Scripts\python.exe scripts/benchmark_gochara_windows.py --system 'True Chitrapaksha' --concurrent-processes 4 --output C:/dev/outputs/ved017-windows-benchmarks-2026-10-11-final/spica-omit.json
.\.venv\Scripts\python.exe scripts/benchmark_gochara_windows.py --system 'True Chitrapaksha' --bav --concurrent-processes 4 --output C:/dev/outputs/ved017-windows-benchmarks-2026-10-11-final/spica-bav.json
.\.venv\Scripts\python.exe scripts/benchmark_gochara_windows.py --system Raman --bav --start-jd 2460313.5 --days 1 --concurrent-processes 4 --output C:/dev/outputs/ved017-windows-benchmarks-2026-10-11-final/raman-near-station.json
```

## Authorized source-publication checkpoint — 12 October 2026

The user authorized commit and push of the complete VED-017 package. Both
remotes were fetched, and engine `main` was fast-forwarded to
`7a86b33940bef0923d61fa1ed7bb210d9cb85139`. The upstream additive public-API
guard supersedes the local additions to the old exact-name inventories.
The upstream guard is retained unchanged: it checks all current declarations,
bindings, identities and methods while preserving historical compatibility
floors. No floor was regenerated or scientific test weakened to accommodate
the feature. The two other upstream commits are retained in history.

Before reconciliation, 181 changed files were hashed and the overlapping test
was backed up outside the repository. All other 180 files retained their exact
bytes after the fast-forward. This includes the complete VED-017 runtime,
source fixtures, original primary-reference evidence and performance receipts.
Subsequent publication edits are documentation and the new execution receipt,
plus removal of one extra end-of-file blank line in each of the new shared
`isolation.py` and `resources.py` modules caught by the staged whitespace check.
Before/after ASTs are identical and both files pass scoped Ruff; no executable
expression changed.

The combined publication test run passes **803 tests in 109.66 seconds**, with
**29/29 required DE441 resource cases executed**, no failures and no skips.
It includes the upstream API-guard self-tests and changed void-of-course test,
all window unit/REST cases, existing Gochar REST cases, retained-oracle integrity,
real split-query consistency and simultaneous serving-engine/REST requests.
These are a fresh publication slice, not 803 additions to the earlier distinct
feature count. Python 3.14.3 and the original no-download/strict-issues policy
remain in force.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_surface_adversarial_audit.py tests/unit/test_public_api_contract.py tests/unit/test_public_api_drift.py tests/unit/test_void_of_course.py tests/unit/test_gochara_windows.py tests/server/test_server_gochara_windows.py tests/server/test_server_gochara.py tests/server/test_server_gochara_dated.py tests/integration/test_gochara_windows_artifacts.py tests/integration/test_gochara_windows_ephemeris.py::test_split_queries_agree_away_from_boundary_bands tests/integration/test_gochara_windows_ephemeris.py::test_real_synchronous_rest_workers_match_engine_and_keep_reader -o addopts='--import-mode=importlib' -o junit_family=legacy --junitxml=C:/dev/outputs/ved017-publication-2026-10-12/tests.xml -q
```

The JUnit result is retained as
`tests/artifacts/oracle/gochara_windows_2026-10-11/publication-tests-2026-10-12.xml`.
The original external comparisons and expensive shared-history regressions are
retained evidence against unchanged code; they were not rerun for publication.
Documentation consistency, release identity, generated REST/Hellenistic
inventories, generated wiki synchronization and both repositories' whitespace
checks pass on the reconciled package.

Publication order is the generated wiki on `master`, then the parent engine on
`main` with that wiki gitlink. The commits include all source, canonical and
generated documentation, fixtures, tests, validation scripts and evidence;
their exact identities belong to the two Git histories. Version 6.9.9, native
code, dependencies, source books and the VED-018/019 admission boundaries are
unchanged. This is source publication; no release tag, package upload, website
change or deployment is included.
