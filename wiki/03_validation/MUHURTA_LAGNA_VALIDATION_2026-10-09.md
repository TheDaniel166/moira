# Muhurta Lagna validation receipt - 9 October 2026

**State:** selected VED-010 package complete and included in the authorized
wiki-first source-publication package.
Baseline engine `571788a1fe705b096d5a69911f30be583c7c45d7` / generated wiki
`ed68937510e6ce162da82420b4f42415c0480161` is the published VED-009 package.
That baseline's hosted Release Hardening and Acceptance Matrix passed. The
results below are local verification of the subsequent VED-010 work.

The [source record](../06_roadmap/VEDIC_LAGNA_SOURCE_AND_PLAN_2026-10-09.md)
identifies five scan hashes, inspected pages, source variants and declared
numerical choices. The [standard](../02_standards/MUHURTA_LAGNA_STANDARD.md)
defines the admitted public/REST contract and compatibility changes.

## 1. Implementation and source evidence

- `moira/muhurta_lagna.py`: separate general and marriage Lagna policies; both MC Navamsa readings; fractional-aspect support; MC87/92 placement score; raw restrictions with optional MC88 exceptions; complete nullable prerequisite evidence and optional full Shadbala context.
- `moira/muhurta_lagna_dated.py`: serving-reader instantaneous composition with UT1/TT/TDB receipt, true ayanamsa and nodes, canonical house-owner Lagna, optional Porphyry Shadbala and explicit unavailable polar geometry. Caller and reader-derived input provenance are distinguished.
- Curated root/facade/Vedic exports: eleven owning names, three facade methods. Three strict REST routes under `/v1/muhurta/lagna/` preserve the canonical evidence and resource identity.
- Shared Varga owner and its Shadbala/Avastha consumers: rational D9 boundaries. Shared Vedic dignity table: Venus-to-Moon enemy correction, preserving the reverse neutral direction. Both corrections are source-backed and separately tested.
- Public API snapshots, REST inventory, canonical/generated documentation and publication manifest are reconciled. The two kernel-free feature test files are now part of Release Hardening.

`tests/fixtures/muhurta_lagna_sources.json` independently transcribes all nine
house/weight rows, MC76's four printed fractional-aspect examples, MC85's two
printed last-Navamsa examples plus a clearly labeled derived vargottama case,
and all 42 directional BPHS3.55 relationships. All five private scan hashes
were checked against the canonical source record. This is source validation;
no external astrology program was treated as doctrinal authority.

## 2. Executed verification

Only project `.venv` Python **3.14.3** was used. Every pytest command ran with
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1` and
`MOIRA_STRICT_KNOWN_ISSUES=1`. Private XML and deduplication receipts are in
`C:/dev/outputs/ved010-research-2026-10-09/`.

| Evidence set | Final outcomes and receipt |
| --- | --- |
| New source/engine/boundary tests | **315 passed**, `unit-final.xml`. All 108 source house/weight cases; all 109 D9 endpoints with both adjacent floats; node-opposition edges; shared consumers; purpose disagreements; grade endpoints; all fixed-role restrictions; opt-in exception/combustion cases; nullable truth; directional friendship; malformed/stale/nonfinite/negative strength receipts; resource/coverage mapping and context restoration. |
| New REST tests | **41 passed**, included in `feature-accepted.xml`. Kernel-free catalogue/direct parity, strict admission, partial results, typed OpenAPI, full Shadbala transport, error envelopes and facade reader preservation. |
| New DE441 integration tests | **7 passed**, included in `feature-accepted.xml`. Independent planetary and canonical house-angle checks; two ayanamsas, both hemispheres and poles; direct/dated/HTTP parity; configured/discovered/borrowed readers and lifecycle. All 10 requested planetary resource uses ran against content identity **DE-0441LE-0441**. |
| Existing affected Vedic regressions | **881 passed**, deduplicated from `acceptance-feature.xml` and `consumer-regressions.xml`, excluding their new-feature cases. Varga/Shodashvarga, Shadbala, Avastha, dignity, yoga, Sayanadi, dosha, Shuddhi and corresponding service/REST consumers. No existing regression failed. |
| Release Hardening original four groups | **1,612 passed, one existing skip**, `release-gates.xml`, 804.874 seconds. All 55 original workflow files ran; the two newly added workflow files are covered by the feature receipts above. `acceptance-summary.json` verifies membership for all **57 current workflow files across four groups**. All 216 DE441 resource uses and the one supplemental small-body resource check ran successfully. |

The final deduplicated outcome is **2,856 passed, one existing skip, zero
unresolved failures/errors** across 2,857 test IDs. The new feature accounts
for **363** of the passing tests. Repeated executions are not added to the
total. Earlier development runs contained test-fixture mistakes (enum naming
and a supposed negative case that actually had valid cross-aspects); the
corrected fixtures passed without relaxing the assertions. The latest test
result for every ID is recorded in `acceptance-summary.json`.

The sole skip is the existing
`tests/unit/test_void_of_course.py::test_no_aspect_voc_last_aspect_is_none`:
its 30-day scan found no qualifying no-aspect window, so RULE-06 was not
exercised. It is not a VED-010 skip or a missing-resource skip.

Representative exact command set (using the environment above):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_muhurta_lagna.py tests/server/test_server_muhurta_lagna.py tests/integration/test_muhurta_lagna_ephemeris.py -q --junitxml=C:\dev\outputs\ved010-research-2026-10-09\feature-accepted.xml
.\.venv\Scripts\python.exe -m pytest tests/unit/test_muhurta_lagna.py -q --junitxml=C:\dev\outputs\ved010-research-2026-10-09\unit-final.xml
.\.venv\Scripts\python.exe C:\dev\outputs\ved010-research-2026-10-09\run_release_tests.py
.\.venv\Scripts\python.exe -m ruff check moira moira_server scripts --select F401,F821,F822,F823 --no-fix
```

The release helper records its expanded file list in
`release-test-selection.json`. The affected-family file selections and all
individual results are recoverable from their XML; repeated new-feature IDs
are superseded by the final passing receipts. All **18 changed Python files**
parse under Python3.10 grammar. This is a grammar check, not a claim that the
local suite ran on a Python3.10 interpreter.

All six release-facing artifact checks pass: documentation consistency,
release identity, Hellenistic inventories, REST reference, generated Git wiki
and website publication manifest. The REST registry has **498 paths/operations**
(GET40, POST458). Exact public snapshot/docstring governance, full scoped Ruff
and whitespace checks pass. Generated Hellenistic family content is unchanged.

## 3. Admission and remaining boundaries

VED-010 is complete for its named instantaneous composition contract. This
does not establish predictive efficacy or universal source agreement. Broader
Kartari/general cancellation/KP remedies and continuous strength windows are
explicit exclusions, and complete purpose elections remain VED-011. Source
availability is not denied. The Raman Sun-minimum discrepancy is recorded;
canonical Shadbala thresholds are reused as context, never silently promoted
into a Muhurta override.

The legacy Muhurta score/search, Tara/Chandra policy and VED-009 temporal
contracts retain their behavior. The shared D9 and Venus/Moon corrections
are disclosed compatibility changes. No native substrate, dependency, version,
release tag, deployment, website or Urania change is included. Version remains
6.9.9. Existing unrelated state-repository work is preserved; its appended
local diary receipt does not publish that repository. The authorized VED-010
source publication includes the generated wiki before the parent gitlink.
The results above are local acceptance evidence; hosted checks for the new
commit are a separate publication receipt.
