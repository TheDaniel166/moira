# Gochara constitutional ledger

Date: 6 October 2026. Owner: Python engine in `C:/dev/moira`. Scope: the bounded seven-classical-planet Phaladeepika snapshot core, with a typed policy surface and a separately admitted research catalogue. No website, REST, native port, node implementation or dated forecast is implied.

Governing sequence: [Moira Subsystem Constitutional Process](../00_foundations/CONSTITUTIONAL_PROCESS.md). Current standard: [Gochara backend standard](../02_standards/GOCHARA_BACKEND_STANDARD.md).

The earlier file called “Phase 1” was an initial core delivery checkpoint, not a claim of constitutional Phase 1 closure. Its early eight-name exports were provisional local work. This ledger maps the real dependency sequence; package curation follows the invariant and architecture freeze.

| Gate | Object / deliverable | Evidence | Status |
| --- | --- | --- | --- |
| Core prerequisite | Source-collated, seven-body snapshot computation | 84 indications, 36 directed pairs, individual citations; initial 173 tests | Complete |
| 1 — Truth preservation | Separate baseline, indication, witnesses, exceptions, BAV and missing observations | Existing source fixture and core tests | Complete |
| 2 — Classification | Typed baseline membership, Vedha state, BAV availability and catalogue admission | `GocharaBaselineClass`, `GocharaVedhaStatus`, `GocharaBavAvailability`, `GocharaAdmissionStatus` | Complete |
| 3 — Inspectability | Active/exempt views, eligible participants, observation completeness, cited choices | Derived properties; no recomputation from narrative strings | Complete |
| 4 — Doctrine / policy | Named source plus typed evaluation/completeness/BAV scope; research catalogue | Default preservation; 30 cited entries with limitations | Complete |
| 5 — Relational formalization | Directed source-bound occupancy witness | `GocharaVedhaWitness`, `directed_pair` and source locator | Complete |
| 6 — Relational hardening | Active/exempt partition, partial observation, omitted scope | Relation classification; observation completeness independent of a proven blocker | Complete |
| 7 — Integrated local condition | Descriptive local profile preserving raw BAV separately | Five local conditions, derived from authoritative assessment | Complete |
| 8 — Aggregate intelligence | Observed state partitions with missing subjects retained | `GocharaChartSummary`; count and partition reconciliation | Complete |
| 9 — Network intelligence | Known blocker→subject graph, separate exempt edges | `GocharaVedhaNetwork`; reciprocal and degree invariants | Complete |
| 10 — Full-subsystem hardening | Cross-layer consistency, determinism and misuse resistance | All 12 scope combinations, frozen-vessel checks, pickle/determinism, unsupported-option rejection | Complete |
| 11 — Architecture / validation freeze | Written standard over actual objects and tested invariants | `GOCHARA_BACKEND_STANDARD.md`; 218 tests passed before final curation | Complete |
| 12 — Public API curation | Stable 28-name unified surface and eleven-name policy owner | Exact root snapshot and shared identity checks; final targeted run 520 passed | Complete |

This status applies to the frozen snapshot domain. Source-attested concepts in the catalogue are not automatically complete runtime domains. Expansion requires its own source admission and a revision of the governing standard.

## Verification sequence

All runs used Python 3.14.3 from the repository `.venv`, `MOIRA_TEST_MODE=1`, strict known-issue expiry and external-network exclusion. `tests/KNOWN_ISSUES.yml` is empty. Native/import smoke reports engine 6.9.9 and `moira/_moira_native.cp314-win_amd64.pyd`; numerical Gochar doctrine remains Python-governed.

The pre-edit core baseline passed 173 tests. Policy/classification/inspection gates passed 188, relation hardening 189, integration/aggregate/network 204, and full-subsystem hardening 218. The final 45-test constitutional slice passed separately before writing the architecture freeze. Ruff and scoped module/class/machine-contract docstring checks passed for both engine modules.

Final curation and surrounding command:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py tests/unit/test_api_surface_adversarial_audit.py tests/unit/test_ashtakavarga.py tests/unit/test_muhurta.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

Outcome: **520 passed in 28.90 seconds**, no failures or skips. This selected run includes 239 Gochar cases after public-surface expansion, the complete API-surface audit, surrounding Ashtakavarga and Muhurta tests. It is not a full repository run. The initial core's earlier broader run exposed one pre-existing Shadbala reader-context failure, reproduced with unchanged HEAD source; see its checkpoint receipt. That unchanged Vedic facade suite was not selected again for this final run. No test suppression, known-issue addition or unrelated Shadbala/reader change was made.

```powershell
.\.venv\Scripts\ruff.exe check moira/gochara.py moira/gochara_policy.py moira/vedic.py tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py tests/unit/test_api_surface_adversarial_audit.py --no-fix --output-format concise
git diff --check
```

Both pass. Ruff JSON comparison of current root/facade source against `git show HEAD:<path>`, with the same stdin filename and UTF-8 bytes, gives 59 root findings before/after and five facade findings before/after, with no introduced findings. These are existing audit debt, not a claim of repository-wide clean lint.

Scoped `check_module_docstrings`, `check_class_docstrings` and `check_machine_contracts` each give zero violations for both new engine modules. The initial checkpoint's Python example and both backend-standard Python examples execute successfully in the project runtime. All thirteen local/downloaded source hashes still match the research inventory; the books repository is clean. No astronomical authority corpus, forecast dates or predictive accuracy study was exercised.

The post-correctness lineage audit inspected helper structure, branch handling, assembly and proof framing in both modules. The policy catalogue owns explicit evidence/status records; omission/completeness branches follow named input scope; relation and graph assembly preserve typed source witnesses and their declared direction. The fixed planet order and sign arithmetic come from the named domain, with source tables kept private. No external-engine shape, ephemeris dependency, array-slot compatibility scheme, hidden score or software parity oracle was introduced. This is a scoped technique inspection, not a repository-wide sovereignty certification.

## Change and preservation receipt

| File | Work |
| --- | --- |
| `moira/gochara.py` | Preserve the core; add policy stamps, typed classifications, relation views, local profiles, summary, network and curated surface. |
| `moira/gochara_policy.py` | Typed source/scope controls, fixed assumptions and thirty cited admission records. |
| `moira/__init__.py`, `moira/facade.py`, `moira/vedic.py` | Curate the same 28 names with shared identity. No new `Moira` method. |
| `tests/fixtures/gochara_phaladeepika_26.json` | Retain the initial independent source corpus unchanged. |
| `tests/unit/test_gochara.py` | Retain source cases and verify the expanded export identities. |
| `tests/unit/test_gochara_constitutional.py` | Policy, admission, relation, integration, aggregate/network, hardening and curation contracts. |
| `tests/unit/test_api_surface_adversarial_audit.py` | Explicit 28-name additive root expectation. |
| `wiki/01_doctrines/GOCHARA_PHASE1_DOCTRINE.md` | Identify the earlier delivery checkpoint and point to the constitutional standard. |
| `wiki/02_standards/GOCHARA_BACKEND_STANDARD.md` | Freeze authority, ambiguity policy, stable semantics, invariant register and validation codex. |
| `wiki/06_roadmap/GOCHARA_CONSTITUTIONAL_LEDGER.md` | Record the ordered gate closure, verified scope and preserved boundaries. |

The user authorized committing and pushing this completed work to engine `main` on 6 October 2026; release and deployment remain separate actions. Earlier Gochar work and the separate REST-fix branch/commits are preserved. Astronomy, native code, dependencies, existing BAV/Muhurta/Sade Sati conventions, source books, test policy, REST, website/Workspace and generated `moira.wiki` are unchanged. Validation used Python 3.14.3 only; other supported Python versions were not run. Caller-supplied sidereal consistency and BAV birth/reduction provenance remain explicit assumptions.

## Boundaries and future admission

The 30 catalogue entries cover sixteen topics. Executable scope controls do not pretend to implement alternative textual schools. The source profile, natal-Moon reference and conservative classical participant universe remain inseparable. Attestation, disagreement, unknown provenance and product scope are visible status categories.

Future source profiles must carry a complete favorable/indication/relation corpus. Nodal baseline, blocker participation, Ketu narrative, exemptions and mean/true astronomy must be considered separately. Counter-Vedha needs explicit relief examples and overlap handling. Strength, dasha and dignity context must retain distinct testimony. Forecasts require a real sidereal ingress solver partitioned on subject and blocker events, including retrograde re-entry. No invented score closes any of these admissions.
