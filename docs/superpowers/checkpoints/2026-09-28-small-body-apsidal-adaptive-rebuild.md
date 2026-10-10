# Small-body Type 13 apsidal rebuild checkpoint

**Date:** 2026-09-28  
**Status:** RESUMED; implementation is in progress and is not release-ready.

## Objective and current decision

The goal is to make asteroid and comet Type 13 kernels accurate at perihelion and aphelion without reconstructing every catalog object at an unnecessarily dense global cadence.

A uniform 3-day base grid with a 9-node Hermite window was rejected by live Horizons oracle tests. It still missed the radial-distance gate for representative fast/high-eccentricity asteroids, including Moshup, Phaethon, Icarus, and Talos. The implementation now keeps the existing 10-day/7-node base grid and adds locally dense, exact Horizons samples around detected apsides. Each affected body is independently certified, halving the local cadence from 1 day down to a configured minimum when necessary.

Shared policy identifier: `moira-small-body-type13-apsidal-adaptive-v3`.

## Confirmed scientific result

A fresh, coherent full-span validation for Phaethon over 1600–2500 completed successfully:

- 1-day local sampling failed: worst radial witness error 3.1913903281092644 km.
- 12-hour local sampling passed all 1,255 detected extrema.
- Worst independent radial witness error: 0.0008365251123905182 km (about 0.837 m).
- Worst extremum-time error: 0.0001609325408935547 seconds.
- Worst extremum-distance error: 0.00047446414828300476 km (about 0.474 m).
- Final node count: 76,797 total; 32,872 base nodes and 43,925 adaptive nodes.

This validates the algorithm on the hardest known asteroid case tested so far. It does not yet validate the remaining catalog.

## Implementation present in the worktree

Added:

- `scripts/type13_adaptive_sampling.py` — shared detection, local sampling, independent witnesses, and adaptive certification.
- `scripts/horizons_response_cache.py` — atomic gzip JSON response cache bound to request identity and response SHA-256.
- `moira/data/asteroid_type13_adaptive_bodies.json` — the 59-body canonical adaptive roster, bound to the exhaustive audit receipt.
- Unit coverage for the adaptive policy, cache, asteroid audit, and comet integration.

Modified:

- `scripts/build_unified_asteroid_catalog.py` — uses an unambiguous `240h` base cadence, exact `TLIST` queries, the adaptive roster, receipts, and response caching.
- `scripts/build_comet_catalog.py` — uses the same shared adaptive certifier and unambiguous hourly cadence.
- Existing validation, manifest-governance, provenance, integration-test, and canonical wiki files remain modified from this work stream and earlier work.

No catalog kernels or release manifests have been admitted, published, committed, pushed, or released by this checkpoint.

## Validation completed

- Python: 3.14.3.
- `tests/KNOWN_ISSUES.yml`: empty.
- Ruff and `py_compile` passed for the directly changed implementation during development.
- Before the final coherent-request adjustment, the scoped builder suite passed: 25 tests.
- After the final coherent-request and chunking adjustment, the directly affected suite passed: 13 tests, with Ruff also passing.

The complete 25-test slice, integration suite, full test suite, and documentation consistency gates have not been rerun after the final adjustment.

## Oracle and catalog state

The exhaustive asteroid audit already partitions all 11,223 asteroid bodies:

- 126 direct-risk bodies with perihelion distance below 1.3 AU were checked against the existing 10-day/7-node kernel policy.
- 59 bodies failed the radial gate and span 40 asteroid shards.
- The other 11,097 bodies were analytically bounded; the worst estimated radial error was about 0.000173 km.

Still pending:

- Full adaptive validation of the remaining 58 asteroid roster bodies.
- Full adaptive validation of all 497 comets.
- Rebuild and admission of the 40 affected asteroid shards.
- Rebuild and admission of all 20 comet shards.
- Final manifest assembly that preserves the 409 unchanged asteroid shards.

## Horizons response caches

- `C:\dev\moira-candidate-cache\apsidal-v3-coherent` contains the coherent Phaethon validation responses and may be reused with the current policy.
- `C:\dev\moira-candidate-cache\apsidal-v3` contains exploratory responses produced before request coherence was fixed. Do **not** use it as scientific evidence or as input to an admitted build.

No Horizons requests or catalog-build processes were active when this checkpoint was written.

## Known implementation work before a catalog-wide run

1. Compact success certificates and failure messages. The current per-event records are scientifically useful but can make metadata and exceptions very large.
2. Add explicit roster-integrity and asteroid adaptive-invocation tests.
3. Align comet Horizons retry behavior with the asteroid builder before running all 497 comets.
4. Rerun the full scoped unit slice after the final request-coherence change.
5. Run the 59-body asteroid and 497-body comet oracle campaigns into a fresh canonical candidate directory.
6. Review the minimum 1/16-day refinement limit; builders must reject any body that cannot certify within it.
7. Rebuild candidate shards, assemble manifests without dropping unchanged asteroid shards, and run integration/full validation.
8. Update provenance and canonical wiki text only after the final policy and exhaustive receipts are stable.
9. Commit, push, and release only under a separate explicit instruction.

## Safe restart sequence

1. Re-read this checkpoint and inspect `git status --short`; preserve unrelated work.
2. Do not use `C:\dev\moira-candidate-cache\apsidal-v3`.
3. Finish certificate/log compaction and the missing focused unit tests.
4. Run Ruff and the complete scoped 25-test slice.
5. Run the remaining asteroid and comet validations into a fresh candidate directory, retaining all request and validation receipts.
6. Stop on any uncertified body rather than admitting a degraded shard.
7. Only after exhaustive validation, build candidate shards and proceed through manifest, provenance, integration, and release gates.

## Worktree publication state

- Commit: not created for this work.
- Push: not performed.
- Release: not performed.
- Scientific status: Phaethon proven; exhaustive catalog proof still incomplete.

## Continuation — 2026-09-29

The sections above preserve the state as it was known when the checkpoint was
first written. The active implementation has since advanced to policy
`moira-small-body-type13-apsidal-adaptive-v4`.

### Why v4 replaced v3

The first exhaustive v3 asteroid campaign exposed a trajectory-coherence flaw,
not an interpolation failure. Local Horizons `TLIST` integrations for chaotic
long-span objects could diverge from the full-span base integration even when
Horizons reported the same solution identifier. Hathor was the decisive case:
unanchored local integrations disagreed with the base trajectory by roughly
252 million km, while a control request containing the exact 1600 and 2500
coverage endpoints matched the base trajectory at the test epoch exactly.

Policy v4 therefore reserves two positions in every exact `TLIST` request for
the base coverage endpoints, removes those anchor rows before building the
local node series, and records the coherence rule in each certificate. The v3
candidate and exploratory caches are quarantined diagnostic evidence and must
not be admitted.

### Completed asteroid campaign

Canonical candidate:
`C:\dev\moira-candidate-small-bodies-v4\asteroids`

- 11,223 bodies built; zero failures.
- 449 of 449 shards completed.
- All 449 BSP SHA-256 receipts and all 449 metadata SHA-256 receipts verified.
- All 11,223 metadata records verified against policy v4.
- All 59 adaptive asteroid certificates passed.
- All 11,164 base-series retention certificates passed.
- Phaethon is the only asteroid that rejected the one-day level; it passed at
  the half-day level. Rejected coarser attempts remain in the certificate as
  evidence.

### Active comet campaign

Canonical candidate:
`C:\dev\moira-candidate-small-bodies-v4\comets`

The 497-comet rebuild is running as a hidden, shard-resumable process. At this
checkpoint, shards 000 and 001 are sealed (50 comets, zero failures) and shard
002 is in progress. Schwassmann-Wachmann 2 rejected its one-day level and
passed at the half-day level; all other sealed comet records accepted one day.

Operational state at the time of writing:

- Process ID: `2932` (ephemeral; verify before relying on it).
- Standard output:
  `C:\dev\moira-candidate-small-bodies-v4\comet-build-resume.stdout.log`
- Standard error:
  `C:\dev\moira-candidate-small-bodies-v4\comet-build-resume.stderr.log`
- Standard error was empty at the last health check.

If the process is no longer running, rerun the same builder command below. It
will verify and skip every sealed shard before resuming the first incomplete
one:

```powershell
.\.venv\Scripts\python.exe scripts\build_comet_catalog.py `
  C:\Users\nilad\.moira\kernels\comets\comet_master.json `
  0 497 `
  C:\dev\moira-candidate-small-bodies-v4\comets
```

### Updated validation and publication state

- Focused Ruff validation passed.
- The scoped builder and policy suite passed: 34 tests.
- Asteroid candidate validation passed as described above.
- Comet completion, final comet manifest validation, integration tests,
  documentation consistency, and final provenance/wiki updates remain pending.
- No commit, push, admission, installation, or release has been performed.

## Continuation — 2026-09-30

The overnight v4 comet process stopped without a traceback after sealing eight
shards and beginning shard 008. Inspection of every sealed metadata file found
that two of those shards were incomplete even though most progress summaries
had reported only successful records:

- 82P/Gehrels 3 failed the v4 1/16-day minimum.
- 175P/Hergenrother failed the v4 1/16-day minimum.

Both failures were reproduced directly from the retained, endpoint-anchored
Horizons responses. A diagnostic dyadic continuation established the required
cadences without changing either Stage 2 accuracy gate:

- 82P certifies at 1/32 day (45 minutes), across 116/116 detected extrema.
  Its accepted level has a 0.0000160933 km worst radial witness error,
  0.0379801 s worst event-time error, and 0.00000751019 km worst event-distance
  error.
- 175P certifies at 1/64 day (22.5 minutes), across 229/229 detected extrema.
  Its accepted level has a 0.000263929 km worst radial witness error,
  0.0815928 s worst event-time error, and 0.0000182390 km worst event-distance
  error.

The shared asteroid v4 defaults and completed asteroid candidate remain
unchanged. Comets now use the distinct policy identifier
`moira-comet-type13-apsidal-adaptive-v5`, with a fail-closed 1/128-day minimum
to leave one additional dyadic level below the hardest observed acceptance.
The shared certifier accepts an explicit policy identifier and refinement floor
while retaining its v4 defaults for asteroids.

The comet builder now also:

- accepts `--response-cache-dir` so the fresh v5 candidate can reuse the
  unchanged v4 exact-request cache;
- rejects cached shards with failures, missing/extra requested bodies, a stale
  policy, or a mismatched kernel body set;
- omits incomplete/stale shards from the loader manifest; and
- records byte counts and SHA-256 receipts for every BSP and metadata file.

Focused Ruff and unit validation pass: 49 tests. Direct production-code probes
also confirm 82P and 175P under the unmodified v5 implementation.

The full v5 campaign was then started as a hidden, shard-resumable process:

- Process ID at launch: `42088` (ephemeral; verify before relying on it).
- Standard output:
  `C:\dev\moira-candidate-small-bodies-v5\comet-build-v5.stdout.log`
- Standard error:
  `C:\dev\moira-candidate-small-bodies-v5\comet-build-v5.stderr.log`
- Standard error was empty at the first health check.

Fresh v5 candidate:
`C:\dev\moira-candidate-small-bodies-v5\comets`

Reuse cache:
`C:\dev\moira-candidate-small-bodies-v4\comets\.horizons-cache\moira-small-body-type13-apsidal-adaptive-v4`

Restart command:

```powershell
C:\dev\moira\.venv\Scripts\python.exe scripts\build_comet_catalog.py `
  C:\Users\nilad\.moira\kernels\comets\comet_master.json `
  0 497 `
  C:\dev\moira-candidate-small-bodies-v5\comets `
  --response-cache-dir `
  C:\dev\moira-candidate-small-bodies-v4\comets\.horizons-cache\moira-small-body-type13-apsidal-adaptive-v4
```

The next acceptance boundary is unchanged: all 497 comets must certify and all
20 shards plus their receipts must validate before catalog admission or release.

## Continuation — 2026-10-01

The first v5 process stopped without stderr or a traceback while processing the
unsealed shard 015. The 15 sealed shards remained intact and were independently
checked against the requested target slices, v5 policy, passing certificates,
and exact kernel body sets: 375 records, zero failures, and zero integrity
issues. The builder had not yet emitted the final master or manifest.

The full command above was restarted. At launch the replacement hidden process
was PID `36268`, with logs at:

- `C:\dev\moira-candidate-small-bodies-v5\comet-build-v5-resume-20261001.stdout.log`
- `C:\dev\moira-candidate-small-bodies-v5\comet-build-v5-resume-20261001.stderr.log`

The restart verified and skipped shards 000 through 014, began rebuilding shard
015 from the retained exact-response cache, and had empty stderr at its first
health check.

## Completion — 2026-10-01

The v5 comet campaign and its post-build authority work are complete as a local
candidate. No release admission, installation, commit, push, tag, publication,
or deployment has been performed.

Final candidate:
`C:\dev\moira-candidate-small-bodies-v5-final\comets`

- 497 of 497 numbered periodic comets built; zero failures.
- 20 of 20 shards present and openable with exact rosters.
- Every BSP and metadata SHA-256 receipt verified.
- Every adaptive sampling certificate passed.
- Maximum recorded Type-13 node round-trip error:
  `4.0978193283081055e-08 km`.
- Final manifest SHA-256:
  `c3c65f3cab24079a494b6ff9abacbc10bb7063dcc69918087133aba44d171a18`.
- Final master SHA-256:
  `1602e0fd72fa9ec773a70a88e55b7bc127c1afe17fa8408964153a027fed2d0f`.

Accepted local refinement cadences are 483 bodies at one day, two at one-half
day, three at one-quarter day, three at one-eighth day, four at one-sixteenth
day, 82P at one-thirty-second day, and 175P at one-sixty-fourth day.

### Source-solution freshness and refresh integrity

A new fail-closed solution-freshness auditor compares the exact Horizons
VECTORS target-source field retained by the catalog, not the distinct object
record `soln ref.` field. The first complete census found 23 changed solutions
across 14 shards. Only those 23 bodies were fetched and recertified; the other
474 raw node tables were proven exactly equal across the refresh. A complete
post-refresh census then returned 497 matches, zero stale bodies, and zero
query errors.

Horizons updated Encke once more during final validation, from `JPL#K273/19`
to `JPL#K273/20`. A receipted one-body delta audit detected it, Encke alone was
rebuilt, and all other 496 raw node tables were again proven exactly equal.
The final Encke delta audit matches `JPL#K273/20`.

This is necessarily a timestamped release receipt, not a permanent assertion
that JPL will never publish a newer fit. The official Horizons manual states
that small-body trajectories are numerically integrated on demand, use the
latest orbit solution, and that previously generated small-body SPKs can be
superseded as new observations are incorporated:
`https://ssd.jpl.nasa.gov/horizons/manual.html`.

### Request-span coherence and direct apsidal oracle

Encke exposed why a solution label alone is insufficient. A short local
Horizons request and the catalog's 1600–2500 request can return different
numerical trajectories while both identify the same JPL solution. They are not
interchangeable authority products. The v5 catalog's declared rule is therefore
also the oracle rule: every exact request contains the two coverage endpoints,
JD(TDB) `2305447.5` and `2634157.5`.

An independent safeguarded root search on exact endpoint-anchored Horizons
radial-velocity states passed the unchanged Stage 2 gates:

- Halley `JPL#75` perihelion: `0.0006437302 s` time delta and zero distance
  delta.
- Encke `JPL#K273/20` perihelion: `-0.0007644296 s` time delta and
  `5.551115123125783e-17 AU` distance delta.
- Encke `JPL#K273/20` aphelion: `-0.0008448958 s` time delta and zero distance
  delta.

The gates remain 8.64 seconds and `1e-9 AU`; neither was widened. The persistent
candidate receipt is
`tests/artifacts/oracle/comet_type13_catalog_candidate_admission_2026-10-01.json`.

### Size result

The final BSP set is `1,062,366,208` bytes (`1,013.15 MiB`). The installed
30-day/5-node release is `305,499,136` bytes, so the v5 candidate adds
`756,867,072` bytes (`721.80 MiB`), is `3.4775x` as large, and represents a
`247.75%` increase.

### Remaining boundary

The scientific build and local candidate validation are complete. Preparing an
immutable catalog release, changing the installed runtime catalog, updating the
packaged manifest/identity release, committing, pushing, tagging, or publishing
remain separate operations requiring explicit authorization.

### Final code-validation receipt

- Ruff passed for every changed Python implementation and test file.
- `py_compile` passed for all four builder/audit/refresh modules.
- The directly changed and release-helper slice passed: 51 tests.
- The broader comet, small-body, Type-13, and apsidal unit slice passed after
  excluding one known pre-existing historical admission-receipt failure.
- `git diff --check` passed.

The 15,702-test repository-wide run was sampled rather than allowed to occupy
hours after it reproduced pre-existing harness/admission failures within its
first one percent. Bounded first-failure reruns isolated two untouched issues:

- `tests/harness_meta/test_configuration_policy.py` cannot complete its nested
  pytest session because that isolated pytester project cannot import
  `support.small_body_resource_policy` while rendering the terminal summary.
- The relevant small-body unit slice reaches an existing historical receipt
  mismatch in `tests/unit/test_small_body_orbital_catalog_admission.py`:

- recorded fixture SHA-256:
  `1e0b5fa423a87087c084f00f4e4e2be377a96f30602c1b3ca8b2374871f33395`
- actual fixture SHA-256:
  `2f7b6708405f0fcbb3b2dc81b780d374d3235d092e1e4f211ee1631c4471b5d2`

That historical artifact and fixture are untouched by this work. Updating an
old admission receipt without re-admitting its source material would be
scientifically improper, so it remains a separate cleanup boundary rather than
being masked here.

## Test-blocker repair — 2026-10-03

The two failures described above were reproduced and repaired after the user
authorized this follow-up. The historical receipt itself remains unchanged.

- The configuration, Hypothesis, baseline, network, and planetary-resource
  pytester mini-projects now include the real
  `support.small_body_resource_policy` module required by the harness terminal
  summary. The successful-budget regression also checks the nested pytest exit
  code, not only its reported outcomes. Production harness policy is unchanged.
- The fixture checksum discrepancy was entirely Windows checkout line-ending
  conversion, not stale scientific data. Its 542 CRLF line endings accounted
  for all 542 extra bytes. Restoring LF gives exactly the original 19,914-byte
  fixture and SHA-256
  `1e0b5fa423a87087c084f00f4e4e2be377a96f30602c1b3ca8b2374871f33395`.
  `.gitattributes` now pins this exact fixture to `text eol=lf`; a fresh
  `git -c core.autocrlf=true checkout-index` into an isolated temporary directory
  reproduced that same byte count and checksum.

No authority records, orbital values, receipt hashes, acceptance gates, runtime
catalogs, or numerical implementation were changed by this repair. The original
failure pair and the complete three-test orbital admission module pass.

### Repair verification receipt

Runtime: the existing engine project environment at
`C:\dev\moira\.venv\Scripts\python.exe`, Python 3.14.3. All pytest runs used
`MOIRA_TEST_MODE=1` and `MOIRA_STRICT_KNOWN_ISSUES=1`; the known-issue list was
empty and external access remained denied. The related unit slice admitted the
local DE441 resource through the harness (12 run receipts, one content probe).

Commands and final outcomes:

```powershell
C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/harness_meta/test_configuration_policy.py::test_budget_accepts_finite_nonnegative_values tests/unit/test_small_body_orbital_catalog_admission.py -q --tb=short -o addopts=
# 4 passed; includes all three historical orbital-admission contracts.

C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/harness_meta tests/unit/test_small_body_orbital_catalog_admission.py -m 'not external_network' -q --tb=short -o addopts=
# 394 passed, 2 skipped in 227.46 seconds.

C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/unit/test_apsidal_passages.py tests/unit/test_comets.py tests/unit/test_build_comet_kernel.py tests/unit/test_comet_solution_freshness_audit.py tests/unit/test_comet_identity_catalog.py tests/unit/test_comet_catalog_adaptive_sampling.py tests/unit/test_asteroid_type13_apsidal_audit.py tests/unit/test_kernel_paths_small_body_manifests.py tests/unit/test_type13_adaptive_sampling_policy.py tests/unit/test_small_body_release_loader_gate.py tests/unit/test_small_body_packaged_manifest_receipts.py tests/unit/test_small_body_orbital_catalog_admission.py tests/unit/test_small_body_identity_resolution.py tests/unit/test_small_body_catalog_release.py tests/unit/test_small_body_catalog_builder_manifests.py tests/unit/test_refresh_comet_catalog_solutions.py -m 'not external_network' -q --tb=short -o addopts=
# 112 passed, no skips in 8.46 seconds.

C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/harness_meta/test_network_policy.py -k sendmsg -q -rs -o addopts=
# 2 skipped, 64 deselected; socket.sendmsg is unavailable on this Windows runtime.

C:\dev\moira\.venv\Scripts\ruff.exe check tests/harness_meta/test_configuration_policy.py tests/harness_meta/test_hypothesis_policy.py tests/harness_meta/test_baseline_policy.py tests/harness_meta/test_network_policy.py tests/harness_meta/test_resource_policy.py --no-fix
# All checks passed.

git diff --check
# Passed.
```

The historical fixture, its six JPL authority records, declared orbital-element
gates, and old sealed catalog identities were checked without changing them.
These are validation-plumbing and regression checks, not a new full-catalog
authority admission. The full configured engine suite was not rerun in this
bounded repair. Existing adaptive-rebuild changes were preserved; nothing was
committed, pushed, installed, tagged, or published.

## Release-bound candidate integration — 2026-10-03

The user authorized the integration-check step, not catalog publication. Both
rebuilt candidates have now passed explicit release-bound integration through
the production checksum/receipt loader and native SPK readers.

### Validation-only storage and identities

Raw builder manifests do not contain the release checksum ledgers required by
these checks, while the historical full-catalog tests are pinned to old release
versions. Rather than test those installed bytes and mislabel the result, a
dedicated candidate suite accepts two explicit validation manifests and rejects
ambient catalog substitution through exact provenance checks for every body.

Local views are under
`C:\dev\moira-small-body-integration-validation-20261003`, with the deliberately
unpublished version `2026.10.03.validation1`. The existing release preparer
generated and verified all ledgers. A small, tested storage adapter hard-links
only the BSP files because duplicating the roughly 22 GB kernel set would have
nearly exhausted the available disk space; metadata and evidence files are
copied. These views share storage with their candidates and are **not suitable
for immutable publication**. They must only be used while source bytes remain
unchanged. Final verification rehashed every declared byte after the tests.

| Catalog | Bodies / shards | Source manifest SHA-256 | Validation-view manifest SHA-256 |
|---|---:|---|---|
| Asteroids | 11,223 / 449 | `91f1ef2d129135cba2ea669c9c3ba32b88914f008ff0f4c48feae27cf1946bf8` | `416e1a7ae6166f935c2c346d31848e6ac7ae87f6b4f06d7250297f214972efe6` |
| Comets | 497 / 20 | `c3c65f3cab24079a494b6ff9abacbc10bb7063dcc69918087133aba44d171a18` | `0f436a14b4606703d2ee329ff66f5dcff8378a03ef698f0b6b96c0d98e695604` |

The native backend was the project environment's
`_moira_native.cp314-win_amd64.pyd`, SHA-256
`1ddd0ea3926353634934078b3a5dec0bf386b8002e4e4809bd4f526cbc99a847`.
Python was 3.14.3, with Moira 6.9.8 and local DE441. No computational source or
native extension was changed during this step.

### Source-product mismatch isolated and corrected

The first candidate run had nine passes and three failures when asteroid
apsides were compared to historical, unanchored Horizons integrations:

- Chiron perihelion differed by roughly 0.332 km; its aphelion control differs
  by roughly 0.531 km.
- Sedna perihelion differed by roughly 2.864 km.
- Eris perihelion differed by roughly 6.121 km and 20.707 seconds.

Independent roots were then solved directly on official Horizons ICRF
geometric states with the catalog's actual first/last base-grid epochs in
**every** exact request: JD(TDB) `2305447.5` and `2634157.5`. Each root has
opposite-sign two-sided radial-velocity witnesses. The same-day unanchored
control queries reproduced the historical reference distances exactly, with
unchanged orbit labels: Eros `JPL#659`, Chiron `JPL#171`, Sedna `JPL#51`, and
Eris `JPL#103`. This establishes different integration-span products, rather
than an interpolation failure or a newly changed orbit solution.

The new six-event, four-body primary-source reference is retained separately
under `tests/fixtures/horizons_asteroid_apsidal_anchored_2026_10_03/`, including
raw responses, request/response hashes, the historical input snapshot,
generator captures, controls, and an explicit source-review receipt. The
historical apsidal fixture and its old receipts were not rewritten. New fixture
bytes are pinned against checkout conversion in `.gitattributes`.

The largest measured candidate radial-distance error in the independent
anchored-state probe was `0.00037655244750194327 km` (about 0.377 metres). The
unchanged gates are `0.0001 day` (8.64 seconds) and `1e-9 AU`
(`0.1495978707 km`, about 149.6 metres). No tolerance was widened.

### Verification results and reproducible entry points

- Candidate integration: **12 passed, zero failed/skipped**, 178.39 seconds.
  Both all-body cases ran: every one of the 11,720 bodies produced finite J2000
  elements and true-date geometric nodes at a representative covered epoch,
  carrying the exact candidate version, manifest hash, shard hash and byte
  count. Native descriptors also matched the exact manifest rosters, Sun
  center, ICRF frame and Type-13 format.
- The four asteroid orbital-element primary holdouts passed. All six anchored
  asteroid apsidal events and the three existing endpoint-anchored
  Halley/Encke oracle events passed through the public apsidal search.
- Planetary regression: **34 passed, zero skipped**, 12.92 seconds, covering
  frozen exact-TDB elements, planetary apsides, true-date node adapters,
  coverage endpoints/model boundaries, and service receipt serialization.
- Storage/source-review unit slice: **15 passed, zero skipped**. It proves the
  hard-link adapter leaves real integrity verification active and checks the
  complete retained source evidence, unchanged gates and controls.
- Follow-up on the final source guards: **10 passed, two all-body cases
  deselected**, 21.40 seconds. The all-body numerical path was unchanged by the
  added source-hash guards; those guards and authority comparisons were rerun
  against the final test source.
- Both complete validation packages passed `verify_release` again after the
  tests. Scoped Ruff and `git diff --check` passed.

Every pytest invocation used `MOIRA_TEST_MODE=1` and
`MOIRA_STRICT_KNOWN_ISSUES=1`, with external access denied. The bounded source
probes intentionally ran outside pytest against official Horizons; no
unmarked test gained network access.

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
$env:MOIRA_TEST_ASTEROID_CANDIDATE_RELEASE='C:\dev\moira-small-body-integration-validation-20261003\asteroids'
$env:MOIRA_TEST_COMET_CANDIDATE_RELEASE='C:\dev\moira-small-body-integration-validation-20261003\comets'
C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/integration/test_small_body_candidate_release_integration.py -vv -ra --tb=short -o addopts= -o junit_family=xunit1 --junitxml=C:\dev\moira-small-body-integration-validation-20261003\candidate-integration-anchored.xml
C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/integration/test_small_body_candidate_release_integration.py -k 'not every_candidate_body' -q -ra --tb=short -o addopts= --junitxml=C:\dev\moira-small-body-integration-validation-20261003\candidate-source-guards.xml
C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/integration/test_apsidal_passages_kernels.py::test_planetary_apsidal_passages_match_frozen_horizons tests/integration/test_orbital_elements_kernels.py::test_frozen_horizons_planet_holdouts_at_identical_tdb tests/integration/test_orbital_elements_kernels.py::test_real_kernel_coverage_endpoints_are_inclusive tests/integration/test_geometric_nodes_kernels.py::test_planetary_geometric_nodes_are_exact_true_date_core_adapters tests/integration/test_geometric_nodes_kernels.py::test_geometric_node_fails_explicitly_outside_true_date_model tests/integration/test_geometric_nodes_kernels.py::test_geometric_node_service_serializes_the_real_core_receipt -q -ra --tb=short -o addopts= --junitxml=C:\dev\moira-small-body-integration-validation-20261003\planetary-regression.xml
C:\dev\moira\.venv\Scripts\python.exe -m pytest tests/unit/test_anchored_asteroid_apsidal_reference.py tests/unit/test_small_body_validation_view.py tests/unit/test_small_body_catalog_release.py -q -ra --tb=short -o addopts=
C:\dev\moira\.venv\Scripts\python.exe -m moira.small_body_catalog_release verify C:\dev\moira-small-body-integration-validation-20261003\asteroids
C:\dev\moira\.venv\Scripts\python.exe -m moira.small_body_catalog_release verify C:\dev\moira-small-body-integration-validation-20261003\comets
C:\dev\moira\.venv\Scripts\ruff.exe check scripts/prepare_small_body_validation_view.py tests/unit/test_small_body_validation_view.py tests/unit/test_anchored_asteroid_apsidal_reference.py tests/integration/test_small_body_candidate_release_integration.py --no-fix
git diff --check
```

Machine-readable receipt:
`tests/artifacts/oracle/small_body_candidate_release_integration_2026-10-03.json`.
JUnit reports remain in the validation workspace and their hashes are retained
in that receipt.

### Remaining release boundary

This completes the requested release-bound **candidate integration** step.
All-body structural/provenance coverage is not independent Horizons validation
for every body or every time. The literal complete engine suite still has not
been run, and the comet freshness census remains the earlier dated snapshot;
repeat the fail-closed freshness check before publication.

Installed discovery was checked after validation and still resolves the old
full asteroid release `2026.09.18.1`, comet release `2026.07.28.1`, and existing
wheel catalog `2026.08.14.1`. Final versioning, stable builder provenance,
immutable release preparation (with independent copies, not these hard links),
packaged identity/docs, installation smoke, commit/push, tagging and publishing
remain separate steps. Existing unrelated work was preserved. None of those
publication/installation operations was performed here.

## 2026-10-03 — Full-suite rerun and process memory boundary

After the user's connection interruption, no full-suite pytest process was
still running. A fresh literal configured run collected **15,720 tests**,
using the existing project Python 3.14.3 runtime, strict known-issue checking,
no downloads, and both explicit sealed candidate catalogs. Its local log is
`C:/dev/moira-small-body-integration-validation-20261003/full-suite-rerun-20261003.log`.

That single-process attempt was deliberately stopped, not admitted as a
completed run. The existing `small_body_reader_pool` is session-scoped and
retained the installed catalog generation while the dedicated candidate module
opened its independent candidate generation. The pytest process reached
49,318,219,776 private bytes (about 45.93 GiB) on a roughly 32 GiB machine;
only 669,708 KiB of virtual-memory headroom remained. Only the process whose
verified command line matched this full-suite attempt was stopped. Its first
candidate asteroid all-body case had passed, but its candidate comet case and
session teardown were incomplete. No complete JUnit report was produced.
This is a process-resource boundary, not evidence that the ephemeris files need
another rebuild.

The replacement verification uses the same configured selection in two
**sequential** processes: the main suite ignores only the dedicated 12-case
candidate module (**15,708 collected**), then that exact module runs separately.
This must be reported as partitioned full-selection coverage, not a completed
literal single-process full-suite gate. Network access remains denied and no
oracle baselines, acceptance thresholds, engine implementation, installation,
or publication state were altered for the rerun.

Both replacement partitions subsequently completed. Logs and JUnit reports
are retained outside the repository in the same validation workspace. Final
results and named failure/skip categories are recorded below.

Separate read-only release guards also exposed existing checkout/release
prerequisites: `moira.wiki` is uninitialized at its recorded gitlink,
`6.9.8` lacks dated changelog/release/compatibility documents, the Hellenistic
generated inventory is stale, and the REST route inventory is stale. No source
files owned by those guards were modified in this task. These guards are not
being represented as green or silently regenerated.

### Branch-alignment finding during the rerun

The primary checkout at `C:/dev/moira` is clean and at
`ed531cd6b0b727759b6e81637badf16ca58855c0` (the 2026-09-30 REST audit repair),
nine commits beyond this worktree's `24b6964...` base. It already includes
the 6.9.8 release documents, the 6.9.9 release/default corrections, and newer
REST repairs. Thus the missing release documents and some failing route
expectations in this older worktree must not be attributed to the current
primary checkout. For example, `ed531cd` adds the antiscia motion fields to
the route-test expectations and removes an obsolete Hellenistic
`doctrine_not_admitted` ray expectation.

The complete `src/native/` trees have no difference between these two commit
IDs. The shared native binary's checksum remains recorded in the candidate
integration receipt; this branch gap does not imply a different native
interpolation implementation. No branch merge, source substitution, commit,
or push was performed. Results of this run apply to the named adaptive
worktree/source version, not automatically to the newer primary checkout.
Alignment with the current primary branch and verification of the resulting
combined source remain a separate required release step.

### Completed partitioned rerun — release gate remains red

Source identity: `wip/small-body-apsidal-adaptive` at
`24b6964ed6de56da3f963316b8f6cb341c5c428a`, with the existing uncommitted
adaptive rebuild work, engine version **6.9.8**, Python **3.14.3**. This is not
a test result for the newer 6.9.9 primary checkout.

| Process | Selected | Passed | Failed | Skipped | Errors | Pytest elapsed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Main selection, excluding only the dedicated candidate module | 15,708 | 15,192 | 79 | 437 | 0 | 6,408.44 s |
| Dedicated candidate module, fresh process | 12 | 12 | 0 | 0 | 0 | 124.52 s |
| Combined configured selection | **15,720** | **15,204** | **79** | **437** | **0** | Two sequential processes |

The main process exited 1 and reported 17 warnings. The candidate process
exited 0. No selected test outside the candidate module was excluded to obtain
these totals. Skips are not passes; external-network tests did not run.

All **11,720 candidate bodies** again passed the finite-elements/geometric-node
and exact-provenance checks. The four asteroid element holdouts, six anchored
asteroid apsidal events and three anchored comet events passed unchanged. The
candidate integration source SHA-256 is
`5e8cd38d8a2a0fc87554594cbd3f2c772eaef067ff787ea1119d3d0c88533667`.
Post-run candidate manifest and native binary hashes still match the preceding
receipt. Neither a rebuilt catalog failure nor a need for another catalog
rebuild was demonstrated by this rerun.

#### Failure accounting and bounded diagnosis

The complete **79 named failures**, assertions and traces are retained in
`C:/dev/moira-small-body-integration-validation-20261003/full-suite-base-20261003.xml`
and its matching log. They comprise:

- **31 historical visibility receipt/integrity failures**: direct geometry
  (22), elevated site (4), environment contract (2), named spectral direct (2),
  reference lab (1). Representative checks expose raw-byte SHA-256 receipts
  made from LF source versus this checkout's CRLF bytes. For example the LUT
  builder is 56,158 bytes locally (54,764 after CRLF-to-LF conversion); its raw
  hash is `45a90978441381ff2c5c25ec942fa348d5dde0365c71fb8f436fbbce3dea992c`,
  while the stored expectation is
  `d19344218140e143bb2011e50cea1cada1f4ed310c276281398d60bd3ab4d6a1`,
  exactly the LF-byte hash. `sha256_file()` hashes raw bytes; it does not
  normalize line endings. These are integrity failures, not completed
  scientific revalidations. No historical receipt was regenerated or admitted.
- **5 synthetic Type-13 writer round-trip failures**, reproduced in isolation.
  The tests query TDB-written synthetic epochs through `position()`, whose
  public input is TT. A representative quadratic exact-node probe has a
  0.0016495585-second TT-to-TDB shift and 0.458227-km error at the deliberately
  large synthetic velocity. `position_tdb()` at that node reproduces the
  analytic vector with zero error. This diagnoses a time-scale mismatch in
  that representative test, not interpolation corruption. All five original
  assertions remain failed; they were not rewritten or marked as passed.
- **12 REST failures** across antiscia (2), forecasting (1), Hellenistic atoms
  (1), Hellenistic profile (1), natal aspects (1), pattern coherence (3), and
  relationships (3). Some expectations and route defects are already repaired
  on the newer primary branch; the full set still needs verification after
  source alignment. Missing serializer names and a missing layered-synastry
  route are among this worktree's reported failures.
- **3 integration failures**: the 2049 hybrid footprint expects two northern
  tracks but produces three (also reproduced in a fresh isolated process);
  sovereign routing references an unavailable old research shard through a
  duplicated manifest-relative path; stellar heliacal fixture `SHR-002`
  differs by about 299.97 days. None was silently rebaselined.
- **28 other unit failures**: doctrine/release identity, generated inventories
  and integrity receipts, docstring governance, changed API/default or error
  contracts, house/polar expectations, synastry, midpoint dial expectations,
  and numerical ephemeris/physics/topocentric/transit assertions. Their exact
  node IDs and evidence remain in the main report. These require triage after
  branch alignment; this rerun does not establish that they are all stale or
  that they all remain on current primary.

Isolated evidence is retained as `hybrid-junction-isolated-20261003.xml` and
`type13-writer-isolated-20261003.xml` in the same validation workspace.

#### Skip accounting

The **437 skips** are: 397 external-network cases disabled by the explicit
network policy; 18 missing external visibility packs (Phase 7: 16, Phase 3: 2);
6 old installed-catalog Stage 2 admission gaps (Eros, Chiron, Sedna, Eris,
Halley, Encke); 2 Windows `socket.sendmsg` limitations; and 14 other skips.
Those remaining 14 are missing `centaurs.bsp` (2), missing `sb441-n373s.bsp`
(1), missing `minor_bodies.bsp` (1), missing Toutatis Type-13 artifact (1),
missing Swiss site-packages (1), missing jplephem comparisons (2), deferred
Horizons comparisons (2), no VOC window in the scan (1), no tight J1900 aspect
(1), an empty parameter row (1), and the baseline computational subprocess
timing out (1). The timeout is
`tests/unit/test_preservation_property_docstring_governance.py::test_run_baseline_computational_tests`;
it is explicitly unverified, not a pass. The six named candidate bodies are
independently exercised by the passing dedicated candidate module, but that
does not turn the installed-catalog skips into passes.

#### Reproduction and retained report hashes

From the named adaptive worktree, use these environment settings and commands;
the two processes must be sequential so the installed readers are released
before the independent candidate readers open:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_ARTIFACTS='0'
$env:MOIRA_TEST_ASTEROID_CANDIDATE_RELEASE='C:\dev\moira-small-body-integration-validation-20261003\asteroids'
$env:MOIRA_TEST_COMET_CANDIDATE_RELEASE='C:\dev\moira-small-body-integration-validation-20261003\comets'
$env:MOIRA_TEST_RUN_ID='full-suite-base-20261003'
C:\dev\moira\.venv\Scripts\python.exe -u -m pytest --ignore=tests/integration/test_small_body_candidate_release_integration.py -vv --tb=short --durations=25 --junitxml=C:\dev\moira-small-body-integration-validation-20261003\full-suite-base-20261003.xml
$env:MOIRA_TEST_RUN_ID='full-suite-candidates-20261003'
C:\dev\moira\.venv\Scripts\python.exe -u -m pytest tests/integration/test_small_body_candidate_release_integration.py -vv --tb=short --durations=5 -o junit_family=xunit1 --junitxml=C:\dev\moira-small-body-integration-validation-20261003\full-suite-candidates-20261003.xml
```

SHA-256 identities in the validation workspace:

| Artifact | SHA-256 |
| --- | --- |
| `full-suite-base-20261003.xml` | `766c3268cb2364fa69d3c579bef7fdcacfb677581844d917a9f81fbc84172ad5` |
| `full-suite-base-20261003.log` | `21fb7c1c90786507945b850c2c75b7b93fbd3d7d7c0e991bc42cbebaa7953c34` |
| `full-suite-candidates-20261003.xml` | `973acaa83a2c3d223dbc9102f720c5c489cc3f6f22d33b92be34a4b520971cea` |
| `full-suite-candidates-20261003.log` | `9dd357a29c1da10bcb1e27365e0563ca34603ed6b5026751b0c61fd0c2de4a13` |

No pytest process remained after completion. The primary checkout remained
clean at the previously recorded commit. No engine or test implementation,
acceptance gate, protected scientific fixture/receipt, installed catalog,
branch alignment, commit/push, tag or publication was changed during this
rerun. Only this checkpoint was updated. Current-primary alignment, remaining
failure/skip closure, a renewed comet freshness census and the previously
listed immutable release/installation/publication checks remain outstanding.

## 2026-10-10 — current-main alignment and known-failure closure

This entry supersedes the previous known-failure status for the **aligned,
repaired source**, not the historical full-suite result above. It is a local
verification checkpoint, not catalog publication or a new engine release.

### Source identity and preservation

- Primary and fetched `origin/main`: `e7107267942d1926da9bcf8ba3d1299b4205ccf9`
  (6.9.9). The adaptive branch was 26 main commits behind before alignment.
- Owned checkout: `C:/dev/moira-small-body-apsides`, branch
  `wip/small-body-apsidal-adaptive`; local merge commit
  `505470361830b7b4cf0c8042e292978e5ef04be2`. Main is an ancestor of this HEAD.
- Existing work was saved in recovery stash
  `0f3a469cbbf92822df23a7d9a682837ff08b431e`, then restored after the
  conflict-free merge. The stash remains available. A secondary untracked
  archive is retained in the output directory below.
- Python 3.14.3, shared project interpreter
  `C:/dev/moira/.venv/Scripts/python.exe`; Python source imports resolve to
  the owned adaptive checkout. The unchanged native binary resolves to
  `C:/dev/moira/moira/_moira_native.cp314-win_amd64.pyd`, SHA-256
  `1ddd0ea3926353634934078b3a5dec0bf386b8002e4e4809bd4f526cbc99a847`.
- Existing adaptive builders, candidate catalogs and historical scientific
  receipts were preserved. No BSP rebuild or installation was necessary.
  Concurrent Vedic research/roadmap documentation in primary was not touched.

### Reviewed repairs

1. Restored original LF bytes for receipt-bound visibility tooling and the
   Stage 4 governing specification, and pinned their checkout line endings.
   Historical scientific hashes and admission thresholds were not refreshed.
2. Synthetic Type-13 tests now query their explicitly TDB-written node times
   through `position_tdb()`. A separate assertion still verifies the TT
   adapter; analytic vectors and numerical tolerances are unchanged.
3. Reconciled REST vessel expectations with current admitted motion/ray
   fields; admitted house exports with the existing 49-name surface; and
   polar tests with genuine branch-capable systems rather than blanket
   automatic fallback. Koch remains the fallback-only fixture.
4. Corrected the real Mundane compatibility defect: provenance verification
   now accepts KernelPool's canonical tuple storage, not an obsolete list.
   Genuine pool equivalence, replaced mutable storage, forged dispatch and
   active-kernel-content guards pass. Only after that review was the exact
   module identity updated from `f417daa618b69e3c43f668c9ae98d1c258fe1eafe6aa1f0dab3eb0928771e71d`
   to `2afc22735b751c6d5a15d053b9ea61121abc0bbd4da587f6392ceac12ffe000f`.
   The original `test_mundane.py` byte identity is unchanged.
5. Natal-aspect transport now identifies a missing segment for the actual
   admitted asteroid and returns the required-resource validation message.
   Unrelated KeyErrors, different target IDs and unsupported mover families
   remain rejected/preserved; no search algorithm was changed.
6. Sovereign routing is tested with a distinct configured copy of the
   complete packaged wheel, including the actual native child-reader path.
   No unavailable historical research shard is silently substituted.
7. Removed duplicate frame-bias application from the manual topocentric
   test chain. Transit parity compares exact target/angle identities and
   solver-bounded epoch differences, not arbitrary rounded-JD bins.
8. Classified new lunar/PCK/Uranian consumers explicitly in the fail-closed
   orbital inventory. Regenerated that inventory and the two physical
   visibility inventory views; synchronized only their two wiki mirrors.
   The migration guide retains its honest historical verification version.
9. The 2049 hybrid northern boundary has two time-reversal folds and **three**
   monotone-time segments. The regression now checks the connected graph,
   exact fold sharing, two horizon incidences and both time extrema, retaining
   sparse/dense equivalence. All 62 footprint/native/NASA-reference tests pass.
10. The ephemeris symmetry test measures actual represented SPK clock spacing.
    At JD(TT) -2661850, nominal one-second probes become 1.00006103515625 and
    0.99993896484375 ET seconds. Geometric and apparent grids are both tested.
    The original per-body motion tolerances remain; the apparent test adds a
    separately derived half-ULP emission-clock rounding allowance propagated
    through target velocity and projected distance. This corrects an invalid
    exact-symmetry assumption, not an external-oracle threshold. Both coverage
    edges also check their actual native/wrapper exception contracts.

The additional builder/harness sweep exposed three raw-evidence integrity
failures after archive/checkout recovery converted text line endings. Each
of the 26 raw Horizons responses and two captured generators was restored
only after its LF bytes matched the original recorded SHA-256. The review
file was also restored to its original recovery blob. All **32 fixture files**
then matched their pre-alignment Git blobs exactly, including the deliberately
CRLF JSON files. No raw response, review assertion or expected digest was
regenerated. The original failed report is retained separately.

### Verification scope and retained artifacts

Outputs: `C:/dev/outputs/small-body-main-alignment-20261010`.
`test-selection.json` records exact complete-module selections; the external
`run_release_checks.py` reproduces the current workflow selections and the
37 modules owning every original failed class. Candidate verification runs
in its own process, after other catalog readers have closed.

| Selection | Passed | Failed | Skipped | Errors |
| --- | ---: | ---: | ---: | ---: |
| Current release-hardening workflow, 64 complete modules | 2,474 | 0 | 1 | 0 |
| Acceptance workflow plus four local DE441 reference slices | 245 | 0 | 1 | 0 |
| All 37 modules owning the original 79 failures | 845 | 0 | 5 | 0 |
| Footprint/native/fold/junction/NASA regression suites | 62 | 0 | 0 | 0 |
| Dedicated candidate catalog integration | 12 | 0 | 0 | 0 |
| Adaptive builders, source integrity, harness and native boundaries | 490 | 0 | 2 | 0 |

Counts are per selection; overlapping tests must not be added as distinct
coverage. Candidate integration passed all **11,720 bodies** (11,223 asteroids
and 497 comets), four frozen asteroid element holdouts, six anchored asteroid
apsides and three anchored comet events. This is not independent Horizons
oracle coverage of every body's entire trajectory. Accuracy gates remain
**0.0001 day (8.64 s)** and **1e-9 AU (149.5978707 m)**. Its test-source SHA-256
remains `5e8cd38d8a2a0fc87554594cbd3f2c772eaef067ff787ea1119d3d0c88533667`.

All six release identity/documentation checks pass: doc consistency, release
identity, Hellenistic inventories, REST reference, Git wiki synchronization,
and the tagged website documentation bundle. Source undefined-name/unused-
import checks and scoped changed-test Ruff checks pass; `git diff --check`
passes. The initial external hardening log wrapper encountered a Windows
encoding error while echoing the final skip summary **after all 2,475 tests
completed**; its complete JUnit report has zero failures/errors. The wrapper
was corrected to UTF-8 before subsequent groups. This was not an engine or
test failure and is retained in the machine-readable closure notes.

Final result: **all selected local gates have zero test failures or errors**.
`release-checks-summary.json` records the final report hashes, exact working-
tree file hashes, unchanged candidate/native identities, all explicit skips,
and fresh exit-zero results for the six release identity/documentation checks.
The full-suite and pre-publication boundaries below remain applicable.

### Remaining boundaries

- The complete 16,000-plus configured suite was **not** rerun in this turn.
  The older full-suite receipt remains historical, not a fresh whole-suite pass.
- Explicit skips are not passes. Existing optional old BSP comparisons,
  an empty visibility parameter row, a no-aspect VOC scan without a suitable
  window, disabled external NASA network coverage and Windows `sendmsg`
  limitations remain separately identified in the final reports.
- Python 3.10 is unavailable locally; its compatibility job remains CI-only.
- A renewed full comet-solution freshness census and immutable, publishable
  catalog copies/receipts are still required before installation/publication.
  Existing validation views remain hardlinks, not immutable release copies.
- Apart from the requested local alignment merge, repair changes remain
  uncommitted. Nothing was pushed, tagged, installed or published.
