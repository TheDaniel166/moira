# VED-011 marriage election implementation evidence

**Date:** 10 October 2026. **Status:** selected marriage scope accepted locally.
This receipt accompanies the [selected source standard](../02_standards/MARRIAGE_ELECTION_STANDARD.md)
and [approved implementation plan](../06_roadmap/VEDIC_MARRIAGE_ELECTION_IMPLEMENTATION_PLAN_2026-10-10.md).
Both full HTTP cases and all affected follow-up checks pass. The catalogue
reports `source_scoped_public`. This does not admit a release or deployment.

## 1. Scope and evidence ownership

The finite MC Avasthi 2004 ordinary marriage astronomical timing profile has
42 rule-family contracts, nine remedy/composition contracts, M01–M30 and
F01–F09 coverage. Personal assessment and the VV/MC Godhuli composition are
separately selected. The source worksheet distinguishes textual rules,
commentary, and named Moira interpretations. Other VED-011 purposes are open.

The MC and SS scan fingerprints and independent transcriptions are retained
in `tests/fixtures/marriage_election_sources.json` and
`tests/fixtures/marriage_visibility_cases.json`. Private PDFs stay outside the
repository. Source arithmetic is tested independently of runtime output.
ERFA altitude roots independently check the frozen-horizon time-degree
construction at five northern/southern/equatorial cases, at 2e-12 degrees.
`marriage_visibility_reader_brackets.json` adds twelve real-reader input
brackets covering all six event roles/branches and both hemispheres. Every
endpoint is checked by independent ERFA altitude roots against the separately
transcribed source threshold and direction. These coordinates are generated
inputs, not a primary planetary-position or event-date oracle.
This does not establish a paired external oracle for the entire marriage
profile, nor observed physical visibility.

Serving-reader checks use the actual DE441/LE441 kernel, including its lunar
tidal identity, native bounded record accessor and loaded clock/frame data.
Raw response and diagnostic artifacts are under
`C:\dev\outputs\ved011-marriage-validation-2026-10-10`. Generated worked cases
are computation/transport evidence, not independent expected source answers.

## 2. Runtime and commands

Baseline engine is `e7107267942d1926da9bcf8ba3d1299b4205ccf9`; generated wiki
is `0c79a578942db2d46e11f203bc6a9c57e730ba27`. All repository execution uses
`.venv\Scripts\python.exe`, Python 3.14.3, Moira 6.9.9. Validation disables
downloads, enables test mode and strict known-issue expiry. Known issues are
empty. Version, dependencies and release state are unchanged.

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
$env:PYTHONUTF8='1'
$env:MOIRA_MARRIAGE_RECEIPT_DIR='C:\dev\outputs\ved011-marriage-validation-2026-10-10'
.\.venv\Scripts\python.exe -m pytest -o addopts='' -o junit_family=legacy -q tests/integration/test_muhurta_marriage_ephemeris.py
```

The two expensive HTTP cases can execute in separate processes using
`-k real_http_windows` and `-k high_latitude_snapshot`; the remaining three
deterministic resource-budget cases use `-k real_resource_budget`.
The optional receipt directory records raw requests, responses and timings.

## 3. Executed verification ledger

These slices overlap and must not be added into a fabricated total.

| Slice / saved result | Observed result | Evidence scope |
| --- | --- | --- |
| All unit/server paths matching `muhurta`, `panchanga`, `lunar_month`, or `vedic_second_pass`; `vedic-regression.xml` | 1,759 passed; 128 planetary resource uses, all executed | Broad affected Vedic regression before the final Newton repair; affected marriage tests rerun below |
| Marriage source, enclosure, windows and server suites; `root-repair.xml` | 182 passed; seven real resource uses, no skips | Includes the repaired Newton candidate, strict catalogue/limits, polar seam, source and transport cases |
| Full targeted marriage + budget slice; `targeted.xml` | 199 passed, one expensive case deselected; ten real resource uses | Earlier focused checkpoint, retained as history rather than substituted for final full acceptance |
| Public API/doctrine/discovery, native import, SPK reader and server error mappings; `public-native-errors.xml` | 95 passed, two skipped; ten real resource uses, none skipped | Existing optional comparator skips are separate from resource execution and from the new native record tests |
| Visibility and window contracts after the worked-bracket addition | 38 passed | Independent geometry for all six real event branches, complete-empty versus indeterminate-empty output, seed-budget and polar-gap regressions |
| Synthetic SPK type 2/3 bounded records | Two passed | Exact independently authored coefficients, both native file/reversed storage orders, immutable copies and bounds rejection |
| Current complete marriage unit/server and three resource-budget cases; `marriage-final-focused.xml` | 209 passed; two full HTTP cases deselected; eleven real resource uses, no skips | Final numerical/transport regression before the separately recorded public export repair |
| Marriage source/contract and public API drift; `public-identity-final.xml` | 82 passed | Includes identity parity for every owning marriage export across root, `vedic` and facade |
| Current marriage, docstring and resource-budget acceptance; `marriage-current-acceptance.xml` | 223 passed; eleven real resource uses, no skips | Precedes the polar parent-domain repair below; its affected cases are rerun separately |
| Final marriage, docstring and resource-budget acceptance; `marriage-final-acceptance.xml` | 225 passed; eleven real resource uses, no skips | Includes the required-parent versus unused-pad polar witness regressions; only the two full HTTP cases are separately selected |
| Release-hardening selection, 69 named test files; `release-hardening-current.xml` | 2,676 passed, four public-guard failures, one conditional skip | All 251 planetary and one supplemental small-body resource uses executed; the four failures are repaired and rerun below |
| Complete public guard, API drift and marriage source suite; `public-identity-current.xml` | 104 passed | All four release public-guard failures resolved; explicit 41-symbol/four-method admission and identity checks include the window types |
| Earlier six-hour HTTP windows checkpoint; `integration-dense-current.xml` | One passed; three real resource uses, no skips; 1,815.19-second test | Successful baseline before the polar-domain repair |
| Final six-hour HTTP windows case, Delhi, Godhuli, 4,096-day history cap; `integration-dense-final.xml` | One passed; three real resource uses, no skips; 1,778.74-second test | 45 certified cells, 88 gap-free supporting certificates, strict serializer, direct interior probes, personal direct HTTP parity and borrowed-reader lifetime; response exactly equals the earlier successful baseline |
| Real HTTP instant, latitude 70, Europe/Oslo; `integration-high-latitude-final.xml` | One passed; three real resource uses, no skips; 1,558.76-second test | Completed operation with explicit unavailable Lagna/visibility evidence, exact engine/HTTP parity and retained reader ownership; no eligible result inferred |

The broad slice command is:

```powershell
$testPaths=@(rg --files tests/unit tests/server | Where-Object { $_ -match '(muhurta|panchanga|lunar_month|vedic_second_pass)' })
.\.venv\Scripts\python.exe -m pytest -o addopts='' -q @testPaths
```

## 4. Adversarial findings and repairs

- Periodic interval subdivision re-enumerates physical rays when its local
  angle lift changes. A parent numeric target cannot silently exclude a
  child representation of the same crossing.
- Native record arguments enclose the serving two-stage floor/carry path;
  frame, clock, observer and finite-difference motion calculations retain
  source-derived whole-cell rounding guards and source identities.
- A real node search exposed a false Newton candidate near JD
  2461222.3226968, separate from the true descending crossing near
  2461222.3225176. The fresh interval value excludes the candidate. Every
  Newton-contracted leaf is now rechecked before retention. Independent
  analytic and real-reader regression tests pass; actual tangencies remain
  unresolved rather than discarded.
- Historical Mercury nature is evaluated at the causal event, with possible
  intermediate associations retained across uncertain bands. Both 27-star
  occupancy clearance and unequal 28-star piercing clearance require an
  actual complete Moon traversal. Missing history is not a clear finding.
- Calendar-owned brackets join the window partition; achieved uncertainty
  is preserved. A calendar bracket wider than its one-second admission
  becomes unavailable before constructing the canonical month result.
- Polar Lagna midpoint unavailability cannot certify a whole window.
  Unsupported Lagna regions retain gaps rather than sampling through `None`.
- Request caches are owned by the request, including native record caching;
  finished requests and borrowed readers are collectible. Pools retain a
  pinned reader order without transferring ownership.
- Preflight history caps cannot be silently exceeded by the fixed calendar
  parent search. Seed bisections and adaptive apparition calls share the
  request root budget. Incremental and final output accounting do not
  silently truncate results.
- Pydantic-wrapped budget exceptions retain the engine's named REST error
  and structured limit/count/stage details. Catalogue defaults and maxima
  agree with engine admission and OpenAPI.
- The final public-surface audit found four historical-evidence types absent
  from `moira.facade`. Its imports and curated exports now match root and
  `vedic`; the regression checks every owning marriage symbol by identity.
- The release docstring gate identified missing actor/vessel documentation
  in 34 new classes. Their architecture, state and resource ownership are
  now documented. `docstring-only-ast-receipt.json` confirms identical
  computational ASTs before and after these documentation edits; all 13
  docstring governance tests pass. The original failure is retained in
  `docstring-current.txt`.
- The high-latitude full HTTP attempt reached 2,000,001 reader calls at
  `Jupiter_east_appearance` after 2,397.09 test seconds. REST returned the
  expected named budget error, but the intended unavailable-result acceptance
  failed. The failed XML and raw budget response remain preserved. Its source
  history contains actual undefined horizons. Such a witness inside the
  required adjacent-event parent now records an incomplete domain and returns
  unavailable availability evidence before futile refinement. It is not a
  zero-exclusion proof, a latitude blacklist or an increased work limit.
  A gap outside the required parent does not trigger this rule. Both boundary
  cases have unit regressions. The real latitude-70 Jupiter/Venus component
  probe now finishes in 7.43 seconds, at 7,101 evaluations and 171,349 reader
  calls, retaining both unavailable-domain reasons. Both complete HTTP cases
  pass after this repair.

The earlier full HTTP run correctly returned an uncertified result and its
acceptance assertion failed on the node candidate. It is preserved in
`integration.xml` (one failure, three passes), not reported as successful
acceptance. Superseded interrupted attempts are not passing validation.
The two optional comparison skips in the public/native slice are
`test_native_daf_catalog_matches_jplephem_on_moira_written_kernel` and
`test_native_chebyshev_payload_matches_live_jplephem_segment_data`: that
development-only comparator is unavailable. No package was installed for
them. The new bounded-record tests and required serving DE441 cases execute
without it.
The release-hardening skip is the existing conditional
`test_no_aspect_voc_last_aspect_is_none`: its 30-day scan found no matching
no-aspect window. It is unrelated to marriage and is not a resource skip.

## 5. Operational measurements and closure gate

An earlier full point diagnostic completed in 1,706.73 seconds with 186,742
evaluations, 1,253,571 reader calls, 49,460 then-counted root iterations,
640 transitions and 335 historical cells. Its one numerical gap was the
subsequently repaired node candidate; it is not final admission evidence.
Its raw ordinary assessment had complete source-rule coverage. The same
raw evidence round-tripped for all five regional selections, with remedies
off and all seven enabled (ten cases). This is shared-evidence parity,
not ten independent ephemeris runs.

Two southern-hemisphere apparition-only runs retained Jupiter and both
Venus branch witnesses with no numerical gaps. Their elapsed times were
145.07 and 166.38 seconds; respectively 20,160/21,158 evaluations and
278,495/289,996 reader calls. These are component measurements, not full
marriage-request timings.

The final six-hour Delhi HTTP window calculation took 1,701.96 seconds
(the complete test, including extra interior/transport checks, took
1,778.74 seconds). It measured 188,201 evaluations, 1,286,318 reader calls,
65,877 root iterations, 705 transitions, 45 output cells and 334 historical
cells. All 88 supporting certificates are gap-free under the declared
arithmetic model; every ordinary source-rule assessment has complete
coverage. All 45 cells are restricted, so the eligible list is empty and
the indeterminate-cell list is also empty. This is a completed negative
search for this selected profile, not missing search evidence.

The result contains 46 boundary bands, 62 shared evidence parts and 613
distinct findings. Its compact response is 1,662,692 UTF-8 bytes; conservative
output accounting charges 1,885,295 bytes. The widest achieved band is
3.745665 seconds, preserved instead of being relabelled with the requested
0.1-second leaf tolerance. Supporting node/apparition domains reach 512 days
on either side of the anchor, far beyond the six-hour requested interval.
Raw request, positions, findings, bands and certificates are preserved in
`real-http-windows.json`; `real-http-personal-direct.json` records the same
evidence with an explicitly incomplete personal context.

The repaired high-latitude HTTP instant returned HTTP 200 in 1,510.44 seconds
(1,558.76 seconds for the full test). It used 167,429 evaluations,
1,113,819 reader calls, 59,056 root iterations, 584 transitions, 334
historical cells and 1,383,574 conservatively accounted output bytes.
The compact response is 1,229,746 bytes. Its known restrictions are retained
with incomplete coverage. Lagna and both planetary availability contexts
are explicitly unavailable. The Jupiter and Venus required-history records
retain 248 and 231 undefined-horizon witnesses respectively; the numerical
status is correctly `not_certified`, not an eligible or complete-coverage
claim. `real-http-high-latitude-snapshot.json` retains this full result.

Neither successful measured request required a raised evaluation, reader,
root or output limit. The supporting-history override in the dense case was
4,096 days, but its actual largest discovery radius was 512 days; its search
did not approach the default 2,048-day bound. The default 300,000 evaluations,
2,000,000 reader calls and 100,000 root iterations provide roughly 50 percent
headroom above the larger observed run. Other caps are finite operational
ceilings with independently tested exhaustion, not promises that every
admitted-duration request completes within all default budgets. The complete
table is in the source standard and the engine/REST catalogue.

## 6. Lineage and publication boundary

The governing objects are source finding, raw witness, finite named
exception, separate evidence coverage and a half-open certified partition.
Discrete tables follow their collated source; historical occurrence and
clearance have explicit state/parent ownership. Numerical helper boundaries
follow the serving SPK record, clock, frame, horizon and interval-isolation
objects. No external engine slot order, oracle-tuned threshold, quadrant
repair or copied marriage-calendar staging is used. Secondary calendar
agreement does not carry the proof burden.

The source-level numerical review closed its identified false-exclusion
defects under `binary64_RN_gradual_underflow_libm_4ulp.v1`. The conditional
arithmetic assumptions are explicit; this is not platform-independent formal
verification. Both final full composition runs pass at this declared scope.

The final current-source marriage/governance slice comprises 227 passing
tests: 225 in `marriage-final-acceptance.xml`, plus one in each final HTTP
receipt. No required resource test is skipped. The wider latest-per-node
reconciliation contains 3,901 passes and three separately disclosed skips;
overlapping runs count once. The original failed receipts remain preserved,
with the affected tests' successful follow-ups identified above.

At the implementation checkpoint this package was local and uncommitted.
The user subsequently authorized wiki-first source publication; the
[register's publication checkpoint](../06_roadmap/VEDIC_REMAINING_WORK_REGISTER.md#41-ved-011-marriage-source-publication-and-remaining-scope--10-october-2026)
records that authorization and the remaining scope. Release and website/Urania
adoption are separate. Other VED-011 purpose profiles remain open and are not
included in this marriage admission.

## 7. Final source identity and documentation checks

`source-state-final.json` records 41 runtime, test, source-fixture and workflow
files against the baseline above, hashing UTF-8 text with LF newlines.
Every fingerprint matches the accepted implementation files before the
publication-only whitespace normalization recorded in section 8. All 35 Python files in
that manifest also parse with Python 3.10 grammar. The manifest excludes
documentation, generated publication metadata and the compiled native binary;
the serving binary has its own identity below.

| Evidence object | SHA-256 |
|---|---|
| `source-state-final.json` | `2c5c8d8bce8d44897fec85419ede827d4c2a5ce68b6bea406f1867643da1e9a2` |
| `latest-results-final.json` | `96667414108de08883599c53b04c077cae1b6b68c188193f216c4ddbb018c20d` |
| Serving DE441/LE441 kernel | `9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5` |
| Numerical source tables | `b3eb6825d4bf354bbbd69832c13c63ee094cbacba0bb4844442fc97b72f7329a` |
| Active native backend | `2a39bf99dced0d2f5bf6b538f6aef2e0e6d932a005ac6dbfa1fccdff77960ff1` |

After both full HTTP runs passed, the final catalogue admission flag and
typed REST schema were checked again: `admission-final.xml` has two passes
and no skips or failures. These repeat existing cases and do not increase
the distinct-test totals above.

Final checks pass for documentation consistency, release identity,
Hellenistic generated inventories, REST route inventory, website-document
publication metadata and the generated Git wiki mirror. CI's source-lint
selection (`F401,F821,F822,F823`) and both repositories' `git diff --check`
also pass. The broader scoped Ruff comparison retains 68 unchanged legacy
diagnostics (60 root-module E402, five facade F811 and three router E402),
with no new diagnostics; `ruff-baseline-comparison.json` preserves that
comparison. No unrelated lint cleanup is claimed.

## 8. Source-publication verification

The authorized publication starts from engine `e4e9a72` and generated wiki
`9edb51f`. The intervening small-body and visibility-documentation commits
are preserved. All 41 source fingerprints, seven aggregate XML fingerprints
and the active native-backend fingerprint above still match.

On that combined checkout, the four `test_muhurta_marriage*` unit files,
marriage server tests, docstring governance and marriage integration tests
were rerun with `-k 'not real_http_windows and not high_latitude_snapshot'`:
**225 passed, two deliberately deselected, zero skipped**, in 46.74 seconds.
All eleven selected DE441 resource uses executed. The exact invocation used
the same project runtime and strict no-download environment as section 2,
plus `-o addopts='' -o junit_family=legacy -q`; its XML is
`publication-acceptance.xml` in the receipt directory.
The two expensive full HTTP receipts remain the unchanged successful runs
recorded above, rather than being reported as repeated publication tests.

The staged whitespace gate subsequently identified one terminal blank line
in `tests/unit/test_muhurta_marriage.py`, which had been untracked during the
earlier unstaged whitespace check. Publication removes that blank line.
`publication-whitespace-receipt.json` preserves both normalized-text hashes
and confirms an identical full Python AST, including source locations.
Original validation manifests remain immutable; `publication-manifest.json`
records the exact normalized files being committed.
