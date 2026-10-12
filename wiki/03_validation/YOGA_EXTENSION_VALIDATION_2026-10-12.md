# VED-012 execution and validation receipt

Date: 12 October 2026. Scope: all seven stages of the authorized
[implementation plan](../06_roadmap/VEDIC_YOGA_EXTENSION_IMPLEMENTATION_PLAN_2026-10-12.md).
Selected package is locally complete; no commit, push, tag, release or
deployment was performed by this implementation run. Version remains 6.9.9.
Starting engine revision: `5049a525f482dbfc60b5fde5001a39c034627f58`.

Subsequent publication authorization and refreshed gates are recorded in
the publication checkpoint below; the earlier implementation record is
retained as historical evidence.

The delivered [standard](../02_standards/YOGA_EXTENSION_STANDARD.md) governs
the 21 source rule entries, four explicit profiles, Python/facade/REST
contracts and legacy migration. BPHS 39.35 is discoverable but non-executable.

## Stage closure

| Stage | Delivered evidence |
| --- | --- |
| 1 — source admission | Immutable source/profile/rule catalogue; scan hashes and page locators; 44 independent cases and separately transcribed Raman Chart 122 signs |
| 2 — legacy repairs | Shared admission for all public families/classifier; strict doctrine/transport booleans; missing-motion state, indeterminate formation and applied-policy transport |
| 3 — Navamsa | Two distinct profiles, immutable call-local context, canonical D9 owner, frame and self-dispositor cases, exact binary boundary checks |
| 4 — wealth/Raja | All fourteen wealth rows and five selected royal entries; all required supporters, roles and branch directions retained |
| 5 — public/REST | Identical root/facade/Vedic exports, thin facade method, typed discovery/evaluation, schema example, source-corpus parity through actual ASGI HTTP |
| 6 — validation/cost | 573 passing selected tests; 144-chart legacy comparison; reproducible 132-request warm engine/HTTP measurements; normal production engine factory startup |
| 7 — documentation | Standard, Python/REST references, fixture provenance, this receipt, executed plan and register; release-facing consistency and generated-inventory guards |

Two implementation refinements avoid unnecessary work without changing
semantics: D9 Lagna is not calculated because no selected rule uses it, and
the seven-body context uses bounded direct sign-aspect predicates rather
than precomputing an unused full matrix. Evaluated clauses have two truth
states; no-candidate applicability belongs to the rule, and unevaluated
interpretive context belongs to a typed qualification. This makes those
distinct concepts explicit without introducing unsupported formation states.

## Evidence classes and acceptance

**Primary source / selected interpretation:** the
[research packet](../06_roadmap/VEDIC_YOGA_EXTENSION_SOURCE_RESEARCH_2026-10-12.md)
and `tests/fixtures/yoga_extensions/README.md` identify JP/Sastri 7.14,
Raman no. 252/Chart 122 and BPHS/Santhanam 41.2–15 and 39.33–39. The JSON
fixture contains 44 manually derived positive/counterexample cases, with
every executable ID represented. Expected states were not generated from
the evaluator. Published Chart 122 D1/D9 signs are distinct from the
synthetic degrees used to exercise the API. No historical birth ephemeris
or predictive accuracy is claimed.

**Independent geometry:** all twelve ascendants of the H5 wealth tables;
every named supporter separately; all twelve source signs for every
supporter in both own-sign H1 variants; 2,688 royal-rule charts checked
branch-by-branch against a separate sign/lord/aspect oracle. JP tests separate
natal/D9 frames, D1 Lagna-lord identity, both movable gates and valid
self-dispositor placement. Identity aliases do not create self-conjunctions.

D9 tests use rational arithmetic for all 108 partition starts and their
adjacent representable values, 108 modality-defined interior positions,
and the representable neighbor below 360 degrees. Results and discrete
doctrine states require exact equality: no epsilon snapping or relaxed
tolerances. BPHS 39.35 has the separate 84-case demonstration that no one
full-graha source can reach both opposite H4/H10 targets.

**Regression:** 144 deterministic charts captured before legacy edits were
compared field-by-field afterward, across twelve Lagna signs and doctrine
variants. Zero differences in existing computed fields. Exactly 75 source
strings received the intended JP “separately available” wording update.
New evidence-state fields were additive and excluded only because the old
schema did not contain them; booleans, ordering and suppression were compared.
This is regression evidence, not a primary authority oracle.

Private capture: `C:/dev/outputs/ved012-research-2026-10-12/legacy_before.json`,
SHA-256 `fc69926a20938ecc95116a53d0730a3d8ea38d43331b71d63945d15a9facb5bd`.
Comparison receipt: sibling `legacy_comparison.json`.

**Transport:** all 44 cases run through defining module, root, facade,
Vedic namespace, method, service and HTTP. Full source/role/frame/branch,
state and policy payloads compare exactly. Tests cover filtering (including
empty filtered results), complete counts, canonical profile ordering,
concurrent request independence, model curation, OpenAPI, extra/missing
inputs, invalid selections, wrong scalar types and non-finite values.
The service revalidates deliberately forged request models; contradictory
state/observation vessels fail at construction or serialization.

Legacy HTTP tests verify strict booleans, applied policy, retained
indeterminate results and the distinction between absent speed, observed
direct speed and retrograde speed. Existing yoga/varga/Vedic hardening and
public-surface audit tests pass in the same run.

## Executed commands and runtime

Project `.venv`, Python 3.14.3 on Windows 11. `tests/KNOWN_ISSUES.yml` contains
no exemptions. Downloads disabled; external network denied by the test
harness. HTTP tests use its loopback capability. No native/astronomical
implementation or package dependency changed.

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_yoga_extensions.py tests/unit/test_yoga_extension_admission.py tests/unit/test_yogas.py tests/unit/test_varga_exact_partition.py tests/unit/test_api_surface_adversarial_audit.py tests/server/test_server_yoga_extensions.py tests/server/test_vedic_direct_input_hardening.py -q -rA --junitxml=C:/dev/outputs/ved012-research-2026-10-12/acceptance.xml
```

Result: **573 tests, zero failures, errors or skips**, 50.209 seconds in the
JUnit receipt. Normal unmocked engine creation ran through the FastAPI
lifespan. Most contract cases use a deliberately minimal engine fixture;
the separate lifecycle test establishes actual startup. The evaluator is
resource-free; the application's ordinary startup still discovers and opens
configured resources. The local performance run reported 471 ready readers.
No-download discovery resolved the existing planetary kernel to
`C:/Users/nilad/.moira/kernels/de441.bsp`.

After the final catalogue metadata and export edits, a second run of
`test_server_yoga_extensions.py`, `test_yoga_extensions.py` and
`test_api_surface_adversarial_audit.py` passed **307 tests**, zero
failures/errors/skips, in 41.560 seconds (`final_transport.xml` alongside the
first receipt). These are repeated members of the 573-test selection, not
307 additional distinct tests.

Additional executed gates:

- Full configured Ruff rules pass for the 14 changed owner/service/test/tool
  files outside aggregate export modules. Aggregate modules pass the release
  gate's F401/F821/F822/F823 selection; their existing E402/F811 debt remains
  separate from this package.
- Docstring preflight passes for all eight changed engine Python files.
- Documentation consistency, release identity 6.9.9, REST generated route
  inventory and Hellenistic generated inventories pass. Generators were run;
  the Hellenistic content remained unchanged.
- `git diff --check` passes. The YAML adds this yoga slice as a release gate;
  remote CI was not run or claimed.

The repository-wide docstring preflight initially reported **23 MC-001
issues in untouched `moira/houses.py`** under a concurrently edited
governance checker. The eight-file VED-012 preflight passed. Other concurrent
governance, event-search/Gochar and light-box work was preserved; no unrelated
repair or broad green-CI claim is part of this receipt. Generated
`moira.wiki` synchronization is reserved for the separately authorized
publication step, as the plan specifies.

## Cost and resource receipt

Reproduce with:

```powershell
.\.venv\Scripts\python.exe tests/tools/benchmark_yoga_extensions.py --output C:/dev/outputs/ved012-research-2026-10-12/performance.json
```

Corpus SHA-256:
`8f11e0b6485c1ee796ff3b7d545d793083a3eaf69eef34f2e4f0a91dce7b8be6`.
44 source cases, all four profiles / 21 rules per request, three repetitions
(132 warm calls for each path). Every measured HTTP response compares to
the full canonical engine evidence. No clauses or validation cases are
skipped to obtain the timings.

| Measurement | Observed milliseconds |
| --- | ---: |
| First engine call after imports | 1.257 |
| Warm engine median / p95 / max | 1.103 / 1.646 / 1.888 |
| Normal app creation and lifespan startup, prewarm off | 25,627.117 |
| First HTTP call after startup | 12.283 |
| Warm in-process HTTP median / p95 / max | 6.100 / 8.154 / 72.427 |

JSON payloads: 86,642–93,599 bytes; median 86,739.5 bytes. Full branch and
source evidence is deliberately retained. These are local observations,
not latency guarantees or TCP/production benchmarks. Application resource
startup is measured separately from the supplied-longitude calculation.

Instrumented tests establish seven D9 calls for all-profile evaluation,
zero for wealth/Raja-only requests, and no calls to planetary evaluation,
kernel discovery, reader acquisition or kernel opening during evaluation.
The test harness denies external network. There is no global chart cache.

## Remaining boundaries

BPHS 39.35 needs a cited resolution of aspect targets/type and a positive
satisfiable source witness before a future admission. Other chapter-specific
extensions and additional source traditions retain their separate scope.
The delivered package evaluates selected formation, not strength/dasha,
historical outcomes, natal interpretation, or date-derived yoga searches.

## Authorized source-publication checkpoint — 12 October 2026

The user authorized committing and pushing VED-012. The refreshed checkout
includes the separately published docstring-governance/house repairs through
`a399faa`; the full docstring preflight now passes **366 engine Python files**.
The earlier 23-house-class report is resolved by that separate work.

The same seven-file acceptance command was rerun with its JUnit output at
`C:/dev/outputs/ved012-research-2026-10-12/publication.xml`: **573 tests pass,
zero failures, errors or skips**. The 14-file scoped Ruff check and aggregate
F401/F821/F822/F823 gate pass, as do documentation consistency, release
identity 6.9.9, Hellenistic inventory and REST reference checks.

Publication support also passes **40 tests** via
`python -m pytest tests/unit/test_git_wiki_sync.py tests/unit/test_public_api_drift.py tests/unit/test_public_api_contract.py -q`
using the same project interpreter and strict no-download test environment.
Its JUnit receipt is `publication-support.xml` beside `publication.xml`.
The generator synchronized seven intended wiki pages with no deletions;
`scripts/sync_git_wiki.py --check` and both repositories' whitespace checks pass.

The source package comprises the VED-012 engine/public/REST changes, source
fixtures and tests, benchmark tool, its release-hardening step, canonical
documentation and generated Git-wiki mirror. The wiki is published before
the parent engine commit records its gitlink. The engine commit containing
this checkpoint and its `moira.wiki` gitlink identify the pair without a
self-referential commit hash in either source document. Concurrent light-box
scripts, tests and artifacts are excluded. No tag, package release,
deployment or new VED-013 implementation is included.
