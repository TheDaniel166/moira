# VED-013 Chara and Argala implementation validation

**Date:** 12 October 2026. **Status:** All seven selected stages complete; authorized source-publication checkpoint below.
**Baseline:** engine `main`, `f8e9a615f04659c77a03713b302cb7189f4d890c`,
version 6.9.9; project `.venv`, Python 3.14.3, Windows.
**Scope:** [executed plan](../06_roadmap/VEDIC_CHARA_ARGALA_IMPLEMENTATION_PLAN_2026-10-12.md),
[source packet](../06_roadmap/VEDIC_CHARA_ARGALA_SOURCE_RESEARCH_2026-10-12.md),
[public standard](../02_standards/JAIMINI_PROFILE_ASSESSMENT_STANDARD.md).

## Delivered stages

| Stage | Local result |
| --- | --- |
| 1. Source and fixture lock | Immutable source/rule/conflict catalogue; independent printed tables, selected-rule derivations and legacy snapshots prepared before evaluators; BPHS erratum reconciled |
| 2. Input and legacy repair | Strict immutable sign/longitude/reference/projection inputs; exact participant pools; valid legacy Argala arithmetic and partial node maps preserved; invalid inputs and lineage/receipt repaired |
| 3. Chara | Three named Rangacharya recipes; twelve source-year rows including zero; optional separately identified fixed-day projection; legacy Chara unchanged |
| 4. Argala | Three named nine-body assessments; count/character/quarter/strength evidence separated; explicit source-specific comparison and uncertainty composition |
| 5. Public and REST | Curated root/facade/Vedic exports, three facade methods, catalogue plus two computation routes, strict OpenAPI contracts and full evidence serialization |
| 6. Validation and cost | Independent source/boundary tests, compatibility and hostile-input regressions, concurrent profile isolation, real application lifecycle and repeated bounded-request measurements |
| 7. Documentation | Standards, source packet, plan and register reconciled; release-facing generated references and wiki mirror checked; this closure receipt |

No native algorithm or dependency changed. Direct evaluation requires no
ephemeris, resource reader, birth-chart construction or network. Normal REST
application startup retains its existing engine lifecycle; that separate resource
cost is not attributed to the sign/degree arithmetic.

## Independent evidence and explicit conflicts

The [fixture directory](../../tests/fixtures/jaimini_profiles/README.md) owns
small numerical transcriptions, not redistributed books. Its
[source manifest](../../tests/fixtures/jaimini_profiles/sources.json) identifies
local-library files and primary author URLs. The local corpus is
`C:\dev\ASTROLOGY-BOOKS-DATABASE`. Source identity includes:

| Witness | Identity / executable coordinates |
| --- | --- |
| S08, Rangacharya manual, first edition 2007 | SHA-256 `8290bc9d8a9d5eedd5ac0724f15554c7ff70f276a26103b58cbd7e068ea5a5f8`; printed 65–70, one-based PDF 71–76 |
| S05, BPHS Santhanam Vol. I | SHA-256 `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f`; chapter 31, printed 311–314 / PDF 310–313; errata printed 483 / PDF 482; character chapter 3.11, printed 27 / PDF 26 |
| W03, PVR 2000 textbook | SHA-256 `1cafa828f34764ed5e85816882df2e8f0bc014c5c57ccdb27169416e117fd4db`; sections 10.6–10.7 and Exercise 16 |
| W04, Rath Argala article | Author URL and access date in the manifest; no falsely claimed immutable web-page hash; numerical witnesses frozen separately |

Every executable rule has its own source coordinates in discovery. Research-only
BPHS/PVR/Narayana witnesses retain their separate identities and limitations.
Hashes prove witness identity, not doctrinal correctness.

Validation distinguishes these evidence classes:

- All **24 printed method-2 sequence rows / 288 cells** are literal independent
  arrays covering every Lagna, parity and modality. Three method-1 and seven
  method-2 duration examples are source checks.
- The twelve-value female recipe fixture stores both the printed Cancer ten
  and the selected own-sign-prose twelve. Eleven printed durations agree; the
  twelfth is a disclosed source conflict, not a twelve-of-twelve published oracle.
- The BPHS Argala chart uses the publisher's erratum adding Rahu in Gemini.
  The uncorrected omission is retained as evidence. It does not resolve the
  separate BPHS Chara diagram/table conflicts in the other volume.
- PVR Exercise 16 provides the full twelve-reference/eight-position occupancy
  table. Rath provides additional pair/factor witnesses and source-stated
  judgments, not a complete ranked strength algorithm.
- Independent exact-rational arithmetic checks degree-quarter boundaries and
  cumulative fixed-day projection. Synthetic longitudes never become claimed
  historical source degrees. All sixteen directed quarter combinations and
  144 boundary cases (twelve signs, four offsets, three adjacent floats) are
  exercised, with mixed-matrix and special-third counterexamples.
- Twenty captured pre-repair Argala results and both legacy Chara cycle counts
  establish compatibility only. Source judgment, regression and transport parity
  are different claims.

**C12 fixture correction:** The preliminary Rath fixture asserted a negative
Jupiter aspect to Gemini, an assertion absent from the article. Independent
Jaimini geometry puts Pisces, Gemini and Sagittarius in the dual group: Jupiter
in Pisces aspects both compared signs. The fixture now records both as true,
retains the article's stated winner separately, and expects an indeterminate
runtime comparison. No asymmetric aspect or arbitrary factor weight was added.

Two synthetic count tests initially put Ketu in the reference sign and thereby
activated the selected reversal. They were corrected to isolate count comparison;
separate all-sign/node/house-reference tests verify reversal itself. Neither
correction regenerated expected answers from production output.

The final boundary review also established exact binary-input Moon-phase ownership
near conjunction/opposition. Fractional arithmetic prevents subtraction from
rounding a just-bright-half input onto the dark-half boundary. Character tests
cover this alongside node-associated Mercury and sign-only uncertainty.

## Test execution

All commands use the owning `.venv` with downloads and external test networking
disabled. `tests/KNOWN_ISSUES.yml` is empty and strict expiry is enabled.

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jaimini_extended.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_vedic_chara_d60_admission.py tests/server/test_vedic_direct_input_hardening.py -m 'not external_network' -q

.\.venv\Scripts\python.exe -m pytest tests/unit/test_chara_profiles.py tests/unit/test_argala_assessment.py tests/unit/test_jaimini_profile_admission.py tests/server/test_server_jaimini_profiles.py tests/unit/test_jaimini_extended.py tests/unit/test_jaimini.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_vedic_chara_d60_admission.py tests/server/test_vedic_direct_input_hardening.py tests/server/test_server_jaimini_service.py tests/server/test_server_jaimini_routes.py tests/unit/test_api_surface_adversarial_audit.py -m 'not external_network' -q --junitxml=C:\dev\outputs\ved013-implementation-2026-10-12\targeted.xml

.\.venv\Scripts\python.exe -m pytest tests/unit/test_chara_profiles.py tests/unit/test_argala_assessment.py tests/unit/test_jaimini_profile_admission.py tests/server/test_server_jaimini_profiles.py -q --junitxml=C:\dev\outputs\ved013-implementation-2026-10-12\final-focused.xml

.\.venv\Scripts\python.exe -m pytest tests/server/test_server_jaimini_profiles.py -q -k 'not real_application_lifecycle' --junitxml=C:\dev\outputs\ved013-implementation-2026-10-12\final-transport.xml

.\.venv\Scripts\python.exe -m pytest tests/unit/test_jaimini_profile_admission.py tests/unit/test_api_surface_adversarial_audit.py -q --junitxml=C:\dev\outputs\ved013-implementation-2026-10-12\final-exports.xml
```

| Passing run | Tests | Failures / errors / skips | Scope |
| --- | ---: | --- | --- |
| Pre-edit compatibility baseline | 251 | 0 / 0 / 0 | Existing selected Chara/Argala/admission behavior |
| Combined feature and regression slice | 828 | 0 / 0 / 0 | Four new modules, shared Jaimini and legacy/API guards |
| Final focused slice | 412 | 0 / 0 / 0 | Latest exact Moon-phase boundary, all-sign reversal, concurrency and result-integrity cases |
| Final transport slice | 77 | 0 / 0 / 0 | Serializer error-classification repair and four injected-defect HTTP cases; lifecycle deliberately deselected, already passed above |
| Final exports/admission slice | 119 | 0 / 0 / 0 | Public curation and callable-facade regression after consolidating imports into the existing export owner |

Deduplicating JUnit `(classname, name)` identities across the last four runs
gives **847 distinct passing tests**. The runs overlap; their totals must not
be added as distinct coverage. This is a targeted package/shared-owner receipt,
not a full repository or all-Vedic suite run.

Source fixtures cross owning modules, `moira`, `moira.facade`, `moira.vedic`,
`Moira` methods, thin services and real in-process HTTP. Responses are compared
including evidence, reasons and receipts. Hostile cases cover boolean/string/
nonfinite/huge numbers, missing and extra bodies, wrong precision, unknown IDs,
unsupported switches, duplicate/excess references, projection overflow and
forged input/request/result objects. Six-profile concurrent execution remains
deterministic. The direct path is guarded against resource/network evaluation.

The real application lifecycle test explicitly restores the unpatched engine
factory, checks the created `Moira` object, and exercises discovery and both new
POST routes. The combined run recorded 29 executed resource checks using the
available DE441 substrate; none of its tests skipped. Direct arithmetic tests
and the benchmark do not require that kernel. The final transport subset excludes
the already-passed lifecycle test by selection, not by a skip or degraded result.

Malformed engine result types, failed result invariants and invalid response
contracts are internal failures. Injected defects return HTTP 500; they are not
misclassified by the application's generic ValueError-to-422 handler. Actual
invalid inputs retain explicit engine rejection and HTTP 422.

## Bounded cost

The [benchmark tool](../../tests/tools/benchmark_jaimini_profiles.py) records
first-call and thirty warm repetitions, full response sizes, pair counts and
implementation hashes in the [performance receipt](../../tests/artifacts/benchmarks/jaimini_profiles_2026-10-12/receipt.json).
Every iteration preserves exact engine/HTTP output equality. It uses a deliberately
reader-free application factory; startup cost is covered separately above.

```powershell
.\.venv\Scripts\python.exe -m tests.tools.benchmark_jaimini_profiles --output tests/artifacts/benchmarks/jaimini_profiles_2026-10-12/receipt.json
```

| Profile | Engine median ms | In-process HTTP median ms | JSON bytes |
| --- | ---: | ---: | ---: |
| Rangacharya method 1 | 0.074 | 1.651 | 4,398 |
| Rangacharya method 2 male | 0.074 | 1.687 | 4,486 |
| Rangacharya female prose | 0.077 | 1.641 | 4,492 |
| BPHS Argala | 1.953 | 6.211 | 56,973 |
| PVR Argala | 1.361 | 5.436 | 50,140 |
| Rath Argala | 3.510 | 10.094 | 91,215 |

The fixture uses the maximum 22 references, with a populated 4-by-5 contested
occupancy split; this is a bounded stress example, not an exhaustive maximum
over every chart. BPHS/PVR emit 88 pair summaries; Rath emits 132. Chara always
returns twelve rows and at most twelve intervals. The request cannot introduce
an unbounded body/reference product. No global caches, output pruning or
tolerance relaxation were introduced. These machine-specific measurements
are cost evidence, not source or predictive validation.

## Documentation and local closure

The full engine docstring preflight passes 370 Python files. Scoped Ruff passes
the sixteen other owned Python files. The two broad export owners retain their
pre-existing lint debt: `moira/__init__.py` has 60 E402 findings and
`moira/facade.py` has five F811 findings, matching their Git-baseline counts;
no global lint-clean claim is made. Python 3.10 grammar admission passes all
eighteen owned new/changed Python files.
Documentation consistency, unchanged release identity 6.9.9, generated
Hellenistic inventory, generated REST reference and wiki mirror guards pass:

```powershell
.\.venv\Scripts\ruff.exe check moira/_jaimini_profile_inputs.py moira/jaimini_profile_policy.py moira/chara_profiles.py moira/argala_assessment.py moira/_facade_vedic.py moira/jaimini_extended.py moira/vedic.py moira_server/models/jaimini_profiles.py moira_server/services/jaimini_profiles.py moira_server/models/vedic_extended.py moira_server/routers/vedic_extended.py tests/unit/test_chara_profiles.py tests/unit/test_argala_assessment.py tests/unit/test_jaimini_profile_admission.py tests/server/test_server_jaimini_profiles.py tests/tools/benchmark_jaimini_profiles.py --no-fix
.\.venv\Scripts\python.exe tests/unit/test_docstring_governance.py
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe scripts/generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
```

The canonical authoring tree is `wiki/`. The four new canonical pages were first
registered with scoped Git intent-to-add for tracked-file discovery, then included
in the authorized publication manifest below. The generated mirror is written
only by `scripts/sync_git_wiki.py --no-prune`. No unrelated light-box
files are registered, edited or removed. Generated Hellenistic owners were
refreshed and checked; their final contents do not differ from the baseline.

Full BPHS Chara, PVR 2014 Chara, Rath Narayana, Rangacharya Yogada and general
Argala strength comparison remain the five discovery-only candidates, each
with a concrete source/algorithm/fixture gate. They do not weaken the selected
six-profile closure and are never accepted as executable selectors. No missing
strength, unavailable quarter composition or source conflict is silently filled.

## Authorized source-publication checkpoint - 12 October 2026

The user subsequently requested commit/push followed by an adversarial review.
The publication manifest includes only VED-013 engine/public/REST code, independent
fixtures, tests, benchmark evidence, canonical documentation and its generated
mirror. Concurrent light-box and natal-discovery work is excluded. The complete
847-test selected acceptance slice passed as one refreshed run, with zero
failures/errors/skips, strict known-issue handling and downloads disabled.
The command is the combined feature/regression invocation above with
`--junitxml=C:\dev\outputs\ved013-implementation-2026-10-12\publication.xml`.
All 29 DE441 resource receipts executed. Full engine docstrings, documentation
consistency, release identity, Hellenistic inventory and wiki synchronization
also pass.

During publication, a concurrent edit to `moira_server/app.py` registered three
natal-discovery routes. The whole-worktree REST inventory check therefore became
stale. That unrelated file and its routes are excluded from this commit. The
REST guard passes against the exact staged server snapshot, exported with
`git ls-files -- moira_server` and `git show :<path>` into
`C:\dev\outputs\ved013-publication-2026-10-12\server-index`, imported ahead of
the working tree, and checked with the unchanged
`scripts/sync_rest_api_reference.py --check`. No route was deleted, filtered or
silenced inside the generator; the published candidate has 523 paths.

The generated wiki is committed and pushed first. The parent engine commit
containing this checkpoint records the exact wiki gitlink. Version remains 6.9.9;
source publication is separate from release, deployment and website adoption.
The requested subsequent adversarial review is a distinct evidence pass, not
preemptively claimed clean by this publication checkpoint.

## Adversarial repair closure - 12 October 2026

The review of published engine `573570b51de85ebd012eb246b93eafee57114caf`
found three result-integrity/error-boundary defects. The user authorized their
repair. All three are repaired locally; this checkpoint does not publish the
new changes or reopen the five source-admission candidates.

1. `moira/chara_profiles.py` now binds seed/direction and all twelve sequence
   positions to the recipe and Lagna. Count direction, inclusive count, base,
   exception and dignity evidence are derived from the same owned source-rule
   helpers for computation and result validation. Reordered but arithmetically
   consistent rows and false derivation labels are rejected.
2. `moira/argala_assessment.py` now binds per-body character and reasons, group
   character, exact within-sign degrees, effect/reason/comparison state,
   special-third evidence and Rath's two side-specific factors to the actual
   chart/profile. Other profiles cannot carry even one Rath factor. The
   original forged unobstructed verdict and Venus 31-degree/4-degree witness
   both fail. Missing source strength remains indeterminate.
3. `moira/_jaimini_profile_results.py` provides a confined post-admission
   `JaiminiInvariantError` (`RuntimeError`) boundary. Construction failures
   (`ValueError`, `TypeError`, `KeyError`) now become HTTP 500 even before
   serialization. The Jaimini service uses the same failure type for corrupt
   results and response contracts. Request admission remains outside that
   boundary. A nonrepresentable caller epoch still raises `ValueError`/422,
   after valid source arithmetic is established. Manual invalid vessel
   construction continues to raise `ValueError`. No global exception handler,
   route, response schema, numerical policy or default changed.

New negative tests in `tests/unit/test_jaimini_profile_result_invariants.py`
substitute evidence that is valid in isolation but contradicts the result's
chart or profile. Server regressions cover seven result-construction locations,
three exception classes, and four corrupted-result transports. Internal error
details are not exposed. Existing hostile input tests still assert 422.

### Executed acceptance

Project Python 3.14.3; downloads disabled, network-excluding selection, strict
known issues (empty register). From `C:\dev\moira`:

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jaimini_profile_result_invariants.py tests/unit/test_chara_profiles.py tests/unit/test_argala_assessment.py tests/unit/test_jaimini_profile_admission.py tests/server/test_server_jaimini_profiles.py tests/unit/test_jaimini_extended.py tests/unit/test_jaimini.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_vedic_chara_d60_admission.py tests/server/test_vedic_direct_input_hardening.py tests/server/test_server_jaimini_service.py tests/server/test_server_jaimini_routes.py tests/unit/test_api_surface_adversarial_audit.py -m 'not external_network' -q --junitxml=C:/dev/outputs/ved013-repair-2026-10-12/acceptance.xml
```

**951 tests passed, zero failures/errors/skips**, including the real unpatched
application lifecycle and 29 executed DE441 resource checks. This is the prior
847-test selection plus 104 new cases, not a full-engine certification.
The new independent sign-walk sweep checks 3,024 charts / 36,288 duration rows;
the count/quarter sweep checks 2,640 Argala cases. These independently implement
the admitted decisions and do not establish additional classical authority.
Printed source fixtures, exact binary boundary tests and legacy regression
comparisons also pass. All six source/compatibility fixture files are unchanged
from the published commit; no expected answers or tolerances were regenerated.

The initial focused run passed 396 cases and failed 14 new assertions that
incorrectly expected JSON from the server's generic HTTP 500 response. All
fourteen already returned 500, not 422. The tests were corrected to check the
actual status and absence of internal details, without changing the shared
error envelope. The subsequent focused run passed 175 cases; the complete
951-test run above supersedes both. Raw XML remains under
`C:\dev\outputs\ved013-repair-2026-10-12`.

### Cost and documentation guards

The existing benchmark tool now hashes the new internal error-boundary owner.
The new [repair performance receipt](../../tests/artifacts/benchmarks/jaimini_profiles_repair_2026-10-12/receipt.json)
preserves the prior benchmark artifact and uses the same six-profile workload,
maximum 22 Argala references and thirty warm repetitions. Every repetition
retains full engine/HTTP equality and unchanged response sizes.

```powershell
.\.venv\Scripts\python.exe -m tests.tools.benchmark_jaimini_profiles --output tests/artifacts/benchmarks/jaimini_profiles_repair_2026-10-12/receipt.json
```

| Profile | Engine median ms | In-process HTTP median ms | JSON bytes |
| --- | ---: | ---: | ---: |
| Rangacharya method 1 | 0.112 | 1.568 | 4,398 |
| Rangacharya method 2 male | 0.109 | 1.602 | 4,486 |
| Rangacharya female prose | 0.113 | 1.630 | 4,492 |
| BPHS Argala | 1.893 | 6.623 | 56,973 |
| PVR Argala | 1.512 | 6.116 | 50,140 |
| Rath Argala | 4.550 | 12.458 | 91,215 |

Stronger evidence validation has measurable cost, especially for Rath's 132
pair summaries; no unchanged-performance claim is made. These local timings
are neither a service latency guarantee nor accuracy evidence. No evidence
pruning, caching or tolerance relaxation was used to obtain them.

Full engine docstring preflight passes **371 files**. Scoped Ruff and Python
3.10 AST grammar checks pass all seven owned Python files. Documentation and
release identity guards pass (still 6.9.9). Hellenistic and REST inventories
pass against the published server tree with only the repaired Jaimini service
overlaid, using `C:\dev\outputs\ved013-repair-2026-10-12\check_candidate.py`.
The exact snapshot and receipt are saved beside that script. This accounts
for the concurrent natal-discovery additions in `app.py`/`openapi.py` without
altering them or incorporating their routes into the VED-013 documentation.

```powershell
.\.venv\Scripts\ruff.exe check moira/_jaimini_profile_results.py moira/chara_profiles.py moira/argala_assessment.py moira_server/services/jaimini_profiles.py tests/unit/test_jaimini_profile_result_invariants.py tests/server/test_server_jaimini_profiles.py tests/tools/benchmark_jaimini_profiles.py --no-fix
.\.venv\Scripts\python.exe tests/unit/test_docstring_governance.py
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe C:/dev/outputs/ved013-repair-2026-10-12/check_candidate.py
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --no-prune
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
```

The standard, this receipt and the work register record the repair; their Git
wiki mirror is generated locally. Concurrent natal-discovery/light-box files
remain outside the repair. No commit, push, release, deployment or website work
is part of this repair checkpoint.

## Authorized repair publication - 12 October 2026

The user subsequently authorized committing and pushing the three repairs.
The seven recorded engine/REST source hashes still match the repair benchmark
receipt, and the retained acceptance XML confirms 951 tests with zero
failures/errors/skips. No engine or test implementation changed after that
acceptance run; it was not needlessly repeated for publication.

Full 371-file engine docstring preflight, scoped seven-file Ruff, release
identity, documentation and generated-wiki checks pass. The unchanged
candidate-check script is rerun from
`C:\dev\outputs\ved013-repair-publication-2026-10-12\check_candidate.py`;
its private server snapshot excludes the unrelated natal-discovery edits and
checks the Hellenistic and REST inventories without modifying the generator.
Source/compatibility fixtures remain unchanged, and Python 3.10 grammar
admission still passes the seven owned Python files.

The publication manifest is the two repaired evaluators, internal invariant
error boundary, Jaimini serializer, new adversarial unit tests, expanded HTTP
tests, benchmark tool/receipt, three canonical documents and generated wiki.
The wiki is committed and pushed first; the containing engine commit records
its exact gitlink. Concurrent natal-discovery and light-box files are excluded.
This supersedes the preceding checkpoint's unpublished status. Version remains
6.9.9; no release, deployment, website work or new source profile is included.
