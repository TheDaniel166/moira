# VED-009 implementation and validation receipt

**Date:** 9 October 2026. **Baseline:** engine `c33dca1`, generated wiki
`37681cb`, version 6.9.9. **State:** implemented and validated; included in the
containing authorized engine/wiki source-publication package. This receipt covers the selected six-detector/three-exception
package. Release, deployment and website adoption remain separate.

The [source packet](../06_roadmap/VEDIC_DOSHA_PARIHARA_SOURCE_AND_PLAN_2026-10-09.md)
and [admission standard](../02_standards/MUHURTA_DOSHA_STANDARD.md) own the
finite scope, exact profiles, inspected editions and explicit exclusions.

## 1. Evidence and implemented surfaces

| Evidence class | What was verified |
| --- | --- |
| Textual/source arithmetic | All 27 MC/KP offsets, KP dual Mula, both clocks, the Rohini worked example, both seven-row Yamaghanta tables, both Gandanta width profiles and three scoped exceptions. Independent fixture transcription from identified pages; production constants are not imported as expected answers. |
| Pure boundary and admission | Rational starts/widths, every relevant Gandanta parent, half-open boundaries, short-Lagna clipping, previous-star carryover, nullable prerequisites, opt-in/source exclusions and hostile input rejection. |
| Analytical day | Independent linear sky and analytic altitude, off-midpoint cell states, sunrise weekday ownership, complete parent context, merged root bands, a derived uncertainty band whose midpoint precedes sunrise, bounded invalid/nonmonotonic failures and reader cleanup on exceptions. |
| Real astronomy | Six DE441 date/frame cases, independent solar and phase residuals on both sides of roots, dense/off-midpoint states, DST, polar absence/partial Lagna and active/explicit reader parity. These use the existing astronomical substrate; they are not external astrological oracle comparisons. |
| Public/REST | Fifteen exact curated export identities and three facade methods; strict nested request/response schemas, canonical error envelopes, full lossless engine/HTTP projection and both configured/discovered serving readers. |
| Compatibility/release | Existing named Muhurta and Panchanga Shuddhi tests; all pytest file groups selected by the Release Hardening workflow, exact public API snapshots, class docstrings, generated inventories and publication manifest. |

The source fixture is `tests/fixtures/muhurta_dosha_sources.json`. The full
source matrix exercises three tables, two clocks and three parent durations;
Gandanta tests visit all 27/30/12 parents for both profiles and six edge probes.
Every weekday/star combination is checked, together with the boundaries of
the necessary-work half-window. Cancellation retains source restrictions,
parent identity and prerequisite evidence, including source exclusions.

The six real date cases cover Delhi 9/10 October 2026, New York 8 March and
1 November 2026, equator/UTC 2 January 2000 and latitude 65.99 degrees on
22 September 2026. Each day is probed at 48 interior grid points and two
off-midpoint positions in every cell. Solar altitude and full parent phase
roots are independently re-evaluated at their lower/upper brackets. Root
tolerance remains 0.1 seconds; no threshold was relaxed to pass.

Tromso summer/winter solar absence returns unavailable; its equinox day
retains non-Lagna results with explicit partial status. Configured and
discovered FastAPI startups use their own reader and match the canonical
engine result exactly. Readers remain caller-owned and active contexts restore
on success, coverage failure, missing resource and unexpected exceptions.

## 2. Execution receipts

Runtime: `C:/dev/moira/.venv/Scripts/python.exe`, Python 3.14.3.
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`; no known-issue waiver. Tests deny network access
except marked loopback. The discovered planetary kernel is
`C:/Users/nilad/.moira/kernels/de441.bsp`, content identity `DE-0441LE-0441`.

Private machine-readable receipts are under
`C:/dev/outputs/ved009-research-2026-10-09/`. The feature and compatibility
acceptance contains **387 distinct passing tests, zero failures/errors/skips**:

- **153 new cases:** 77 source/pure boundary cases, 21 analytical/lifecycle/
  public cases, 43 REST cases and 12 DE441 integration cases.
- **234 existing regression cases:** 57 named-Muhurta, 104 special-Muhurta
  and 73 Panchanga Shuddhi cases.
- The final complete 150-case feature run took 108.30 s and recorded 15
  successful DE441 resource uses, no resource skips/failures. Three additional
  uncertain-versus-missing-prerequisite cases were then added; the complete
  141-case unit/analytic/REST slice passed in 22.92 s after that state-label
  refinement. The final 234-case compatibility run passed in 2.57 s.

Owning XMLs: `final-dosha.xml`, `final-contracts.xml`,
`final-regression.xml`; `feature-acceptance.json` deduplicates their test IDs.
Earlier exploratory runs are not added to these totals. In particular, a
test-only uninitialized facade fixture was corrected before the passing final
runs; the earlier failed fixture run is not the acceptance receipt.

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests/unit/test_muhurta_dosha.py tests/unit/test_muhurta_dosha_day_contract.py tests/server/test_server_muhurta_dosha.py tests/integration/test_muhurta_dosha_ephemeris.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_named_muhurta.py tests/unit/test_special_muhurta.py tests/unit/test_panchanga_shuddhi.py -q
```

The private `run_release_tests.py` reads the current
`.github/workflows/release-hardening.yml` and selects all 55 distinct pytest
files from its four release groups, including route discoverability. It runs
them in one process with the same strict environment and network exclusion;
the selected filenames are saved in `release-test-selection.json`.
This is local Python 3.14 execution, not a new hosted Python 3.10 CI result.
Python 3.10 grammar admission is checked separately for changed Python files.

Sixteen changed Python files pass Python 3.10 grammar checks. The standard's
Python example executes successfully. Full new-file Ruff and the complete CI
source check (`F401,F821,F822,F823`) pass. No test policy, threshold or exact
API assertion was weakened.

### Final Release Hardening result

All 55 selected files completed in **718.91 s: 1,612 passed, one skipped,
zero failures/errors** (`release-gates.xml`). The existing
`test_no_aspect_voc_last_aspect_is_none` skipped because its 30-day scan found
no qualifying no-aspect window; RULE-06 was not exercised. This is not a
VED-009 skip or a missing-kernel skip. All **216 DE441 resource uses** and
the one supplemental small-body resource check ran successfully.

The deduplicated combined result is **1,999 passed, one existing skip,
zero failures/errors** across 2,000 distinct test IDs, recorded in
`acceptance-summary.json`. Feature plus release runs used DE441 successfully
231 times. Repeated feature/contract runs are not added to either total.

All six release-facing artifact checks pass: documentation consistency,
release identity, Hellenistic generated inventories, REST reference,
generated Git wiki and website publication manifest. The REST inventory has
**495 paths/operations**. Hellenistic generated content is unchanged.
Canonical and generated pages are synchronized, including the final receipt.
Whitespace checks pass. These are local execution results; subsequent source
publication does not convert them into a hosted CI receipt.

## 3. Publication and limits

The REST reference, generated wiki and `website_docs/publication.json` must
be refreshed in that order after source/doc edits. The publication manifest
retains the existing immutable v6.9.9 release identity and document allowlist;
refreshing hashes is not a new release. New API snapshot entries are explicit
admissions; exact equality guards remain enabled. Generated Hellenistic
inventory content must not acquire unrelated Vedic route-count changes.

Completion means the finite named computation and transport package is
implemented and verified. It does not establish predictive efficacy, universal
source agreement, all twenty-one doshas, all remedies or complete purpose
elections. The source record explicitly assigns strength/aspect/Navamsa
exceptions to VED-010 and activity elections to VED-011. Other Tyajya and
Gandanta variants remain separately identified research extensions; classical
availability is not denied. No native substrate, dependency, version, legacy
score/search default, website or Urania code changed.
