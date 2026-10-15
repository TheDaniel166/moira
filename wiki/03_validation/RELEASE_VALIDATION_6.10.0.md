# Moira 6.10.0 release validation

**Date:** 12 October 2026. **Release scope:** completed engine work through
the selected VED-014 profile; Vedic feature expansion pauses at this boundary.
**Starting commit:** `a3a2dabbf2e9f9dbee0cacdd036b6f399188dfe1`.
**Release checkout:** `C:\dev\moira-release-6-10-0`.
**Runtime:** its project `.venv`, Python 3.14.3, rebuilt native extension and
editable distribution reporting 6.10.0. `tests/KNOWN_ISSUES.yml` remains empty.
The local REST/test environment uses FastAPI 0.136.3, Pydantic 2.14.1,
Starlette 1.2.1, HTTPX 0.28.1 and pytest 9.1.1.

The user authorized review, repairs, release validation, wiki/engine publication
and the 6.10.0 package release. The separate natal-discovery and light-box work
was explicitly excluded and preserved in `C:\dev\moira`. The release checkout
contains neither those files nor their shared app/OpenAPI registration hunks.
No website application deployment is part of this release.

## Code Review

**Verdict:** APPROVE after the repairs below. **Confidence:** HIGH for the
reviewed Kalachakra change; this is not a claim that every engine family was
adversarially reviewed in this pass.

The review followed source row membership and balance into full-parent MD/AD
construction, exact/projection boundary ownership, current lookup, immutable
result validation, reader/frame receipts, facade admission, REST schemas,
serialization and sanitized errors. Frozen independent fixtures and all
fourteen source decisions remain authoritative at their stated scopes.

| Priority | Finding | Repair and regression |
| --- | --- | --- |
| P2 | `IndexError` inherits `LookupError`; a generated astronomy indexing defect was incorrectly translated to resource-unavailable 503. | Catch indexing defects before resource lookup errors. A real HTTP regression first failed with 503, then passed with sanitized `kalachakra_internal_invariant` 500. |
| P2 | The frozen Kalachakra fixture hash changed under Git checkout with `core.autocrlf=true`. | Pin this one fixture to LF. Real temporary-repository clean/checkout tests exercise both Windows and POSIX settings; the numerical data and recorded digest are unchanged. |
| P1 release gate | Existing main CI compared the September apsidal audit against the newly packaged October manifest. | Bind the historical audit to the byte-exact archived September manifest. Preserve its original hash and identity, all scientific evidence and all tolerances. Separate current-packaged-manifest tests still enforce October bytes. |

The first defect changes error classification only. The second repairs test
provenance; it changes no catalog, ephemeris or numerical calculation. A stale
current API-reference sentence reserving Kalachakra was also reconciled.

The failing baseline was [Release Hardening run 38293347900](https://github.com/TheDaniel166/moira/actions/runs/38293347900),
job `114958556151`. The targeted repair run passed **12 tests**. Its initial
red run had one expected new-regression failure and 11 passing catalog checks.

## Integrated validation

Validation is run with `MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1` and `HYPOTHESIS_PROFILE=moira-ci`.
Network denial remains active; marked HTTP tests use loopback only.
The isolated Windows environment has no OS IANA database. After preflight
identified that missing prerequisite, the final runs explicitly set
`PYTHONTZPATH=C:\dev\moira\.venv\Lib\site-packages\tzdata\zoneinfo` to the
existing local timezone data (`tzdata` 2026.3, IANA 2026c). The interrupted unconfigured runs do not count
as acceptance; no timezone fallback, numerical tolerance or dependency was changed.
Resource discovery resolves `C:\Users\nilad\.moira\kernels\de441.bsp`;
the harness performs its own content/capability admission.

The selected release suites cover all Vedic unit/server/integration filenames
matching the delivered families, the Release Hardening and Release Acceptance
workflow selections, native/frame checks and the documented local astronomical
acceptance cases. The exact file selections and JUnit receipts are retained at
`C:\dev\outputs\release-6-10-0\test-selection.json`, `kernel-free.xml` and
`resourced.xml`. This is an integrated release selection, not the literal full
repository suite or a new all-body/all-epoch external accuracy certification.

The first combined collection exposed six pre-existing duplicate test basenames
across unit/server/integration directories. `--import-mode=importlib` permits
their joint collection without renaming tests or changing runtime code.
The final kernel-free run uses four isolated pytest workers with
`--dist=loadfile`; no selected file declares a serial marker, and each file's
tests remain together. The real-ephemeris selection runs serially.

The completed kernel-free selection passed **8,861 tests** in **1,007.69
seconds**, with no failures, errors or skips. Its eight warnings are the same
two optional test-client deprecations repeated across four workers; no runtime
dependency or numerical behavior was changed to suppress them. This includes
250 Kalachakra cases; its two real-resource cases belong to the second selection.

The exact final invocations, after setting the environment above, are:

```powershell
$selection = Get-Content C:\dev\outputs\release-6-10-0\test-selection.json | ConvertFrom-Json
$paths = $selection.kernel_free
.\.venv\Scripts\python.exe -m pytest @paths --import-mode=importlib -n 4 --dist=loadfile -m 'not requires_ephemeris and not external_network' -o addopts=-ra -v --tb=short --maxfail=10 --junitxml=C:/dev/outputs/release-6-10-0/kernel-free.xml
$paths = $selection.resourced
.\.venv\Scripts\python.exe -m pytest @paths --import-mode=importlib -m 'requires_ephemeris and not external_network' -o addopts=-ra -vv --tb=short --maxfail=10 --junitxml=C:/dev/outputs/release-6-10-0/resourced.xml
```

The real-resource selection passed **548 tests** in **7,067.06 seconds**
(1:57:47), with 7,210 cases deselected by its complementary marker expression,
no failures, errors or skips. The harness admitted and executed **551/551 DE441
resource uses**, with one content probe and zero resource failures or skips.
The twelve warnings comprise the two test-client deprecations, three existing
JUnit `record_property` compatibility notices and seven existing class-scoped
fixture deprecations. None was suppressed or converted into an accepted failure.

The two selections contain **9,409 unique passing tests**; a JUnit node-identity
check confirms no overlap. This includes **252 Kalachakra tests**, including
the real-kernel astronomy and chart/direct HTTP cases. Full marriage, VV/KP,
housing, business and travel acceptance ran to completion with their existing
boundaries, source rules and validation thresholds. Timings describe this
integrated run and are not a latency guarantee or a controlled benchmark.

The JUnit SHA-256 fingerprints are:

- `kernel-free.xml`: `bb0ffff96401de0dc3ac2ad5f4a2937386c67f66b50a6c2cdf8cc4e6b307a49e`
- `resourced.xml`: `43119003e5e257ce658cf8953578ca76c2ef6582d3e772aa24bf882845aa4d2a`

The release check selection also covers the existing offline eclipse comparison
and NASA cases, houses, sidereal and progressions references, and occultation
structural checks under their owning tolerances. Secondary-engine corroboration
remains distinct from primary-source validation.

The 375-file engine docstring preflight, scoped changed-file Ruff, source
correctness lint (`F401,F821,F822,F823`), release identity, doc consistency,
Hellenistic inventory, REST reference, generated wiki and publication-candidate
checks passed. This is not a claim of a clean repository-wide Ruff audit.
Candidate publication contains 26 documentation entries and 26 release entries.

## Hosted candidate checks

The reviewed source candidate `fd3496195c4a4f9fb3987f3d4b116153ab98538e`
was pushed after wiki `171e194`. Its
[Release Hardening](https://github.com/TheDaniel166/moira/actions/runs/38305930191)
and [Release Acceptance Matrix](https://github.com/TheDaniel166/moira/actions/runs/38305930149)
both passed. Hardening includes actual Python 3.10 server/OpenAPI compatibility,
the Kalachakra feature slice, generated documentation and the repaired historical
catalog check. These CI kernel-free gates supplement local real-ephemeris checks.

Publication requires the final receipt commit's hosted gates to pass before
tagging. Exact-tag publication and the downloaded PyPI artifacts receive
separate verification: PyPI's 20-wheel/one-source-distribution inventory,
downloaded Windows wheel and source-archive hashes, actual Windows CPython 3.14 native import,
Kalachakra engine/projection/current lookup and real HTTP success/rejection
parity. Deferred natal-discovery/light-box additions must be absent.
The [tagged release record](https://github.com/TheDaniel166/moira/releases/tag/v6.10.0)
records those final CI and publication outcomes. Candidate artifacts are not
relabelled as exact-tag release evidence.

## Preserved evidence and next work

The [Kalachakra implementation receipt](VEDIC_KALACHAKRA_VALIDATION_2026-10-12.md)
retains the earlier 794-test package checkpoint. Overlapping preliminary and
repair runs must not be added to the integrated release test total.
Its source fixture SHA-256 remains
`f646f4ab82907988da8cdff128785a62e0c9502a66019c15c70885505952f823`.
Historical asteroid audit/support bytes and archived manifest hashes remain
unchanged. Publication does not rewrite them to assert new scientific scope.

The [remaining-work register](../06_roadmap/VEDIC_REMAINING_WORK_REGISTER.md)
retains sixteen selected delivery checkpoints and eight open/bounded packages.
Special Lagnas and further research can resume after the break; source conflicts,
unsupported Kalachakra traditions, deeper levels and unevaluated eligibility
remain explicit. No new Vedic feature scope is opened by release preparation.
