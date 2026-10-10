# VED-002 Sayanadi execution and validation receipt

**Date:** 8 October 2026.
**Baseline:** engine `77d34158cef7c936fdf6613f9be18ba5e8fad5aa`, Moira 6.9.9; the validated implementation is included in the containing authorized source-publication package.
**Contract:** [Sayanadi admission standard](../02_standards/SAYANADI_ADMISSION_STANDARD.md).
**Authority:** [source research](../06_roadmap/VEDIC_SAYANADI_SOURCE_RESEARCH_2026-10-08.md) and [executed plan](../06_roadmap/VEDIC_SAYANADI_IMPLEMENTATION_PLAN_2026-10-08.md).

## 1. Result and implementation ownership

The selected BPHS within-sign Navamsa-ordinal profile is complete locally
through standalone calculation, strict name/clock inputs, optional chart
composition, nine source-defined bodies, curated Python/facade and typed REST,
including reader-bound birth/sunrise composition. VED-002 is `LOCAL_COMPLETE`
for that contract; VED-021/022 follow-through is complete at this package's
validation/documentation scope. Publication/release/deployment are separate.

| Owner | Changes |
| --- | --- |
| `moira/avasthas.py` | Exact binary64 cell ownership; strict bodies, required Moon, typed names/ghati/policy/context; consistent intermediate trace; explicit optional chart evaluation and separate node results; preserved legacy construction with unknown provenance. |
| `moira/sayanadi_dated.py` | Aware birth/location preflight, previous/next sunrise discovery and root brackets, uncertain/unavailable outcomes, reader-bound epoch/Lagna/true-node composition and typed resource/coverage errors. |
| `moira/sayanadi_effects.py` | Reconciled attribution prose: legacy conditional summaries are not source-certified quotations or evaluated rules. Existing strings retained. |
| Root, `facade`, `vedic`, `_facade_vedic` | Fifteen source-owned exports with shared identity and three facade methods; borrowed serving reader used for birth composition. |
| Server models/router/service/serializer/errors | Discriminated strict clocks; direct/chart/birth requests and typed status/trace/source views; canonical projection and normal preflight/resource/coverage envelopes. |
| Focused unit/server/integration tests | Corrected primary fixture, independent rational boundaries, name/body/clock/input/omission coverage, analytical uncertainty, real DE441 frames and reader lifecycles, export/HTTP parity and OpenAPI. |
| Canonical standards/reference/register and generated wiki | Selected contract, migration, dated source limits, executed plan and closure status; generated through owning scripts. |

No astronomical/native algorithm, dependency, version, golden fixture,
tolerance, test harness or known-issue policy changed. Website/Urania and
unrelated state-repository work remain outside the implementation. The plan
admitted one executing BPHS profile; the degree-based variant remains its
identified optional research frontier, not an unfinished implementation gate.

## 2. Numerical and source evidence

The Santhanam Sun fixture now uses 7 degrees 12 minutes Taurus and Sa=4,
with source Moon-star/Lagna-sign categories represented by visibly synthetic
exact longitudes. It asserts total 51, index 3, first remainder 1, second
remainder 0, Netrapani/Vicheshta. The old 38-degree/name-1 case is separately
synthetic: first remainder 10, same final substate. The unsupported assertion
that the printed arithmetic needed correction is removed.

Independent component cases include Hora Ratnam's Navamsa-commentary Mars
main sum 57/index 9 **only**, Rao's Mercury within-sign Navamsa ordinal 7,
and source ghati rounding 20g2v -> 21, 30g33v -> 31, 42g30v -> 43. The
degree-based Sun example is not used as a Navamsa oracle. All 35 literal
sound-table tokens, all five name values and all nine body constants are
checked against independently specified expectations.

The exact rational boundary test covers nine subjects times 108 global
Navamsa boundaries times lower/base/upper representable inputs times five
name values: **14,580 cases, zero component/state/substate disagreements**.
The unmodified baseline had 1,015 state/substate disagreements in that scope.
The reference uses `Fraction.from_float` of the actual supplied value;
Moon-subject cases also account for Moon owning the birth star. Integer
trace stages, exact 10-degree ownership, wrap behavior, zero state remainder,
ghati-second endpoints and hostile inputs are covered. No epsilon or relaxed
tolerance was introduced. This is source-formula/invariant verification,
not an external-software or predictive oracle.

## 3. Composition, transport and real-resource evidence

Analytical tests isolate previous-sunrise day/night and exact-zero ownership,
ordinal ambiguity across a sunrise root bracket, typed polar/missing outcomes,
offset/zone identity, nonexistent ZoneInfo wall times, independent node
evaluation/affliction controls and reader-override restoration. HTTP cases
exercise canonical direct/chart/birth parity, all three clock shapes, hostile
coercions/identities/partial contexts, unavailable output and distinct resource
and coverage errors. OpenAPI retains discriminated clocks and nullable
trace/status fields.

Real integration used the actually discovered DE441 SPK, explicit borrowed
SPK readers and discovered/configured server startup engines. Four date/frame
cases cover India and both US daylight-saving transition dates, Lahiri/Raman
ayanamsas, all three named sunrise definitions and optional true-node subjects.
Reader-bound UT1/TT/TDB, kernel/ayanamsa receipts, independent rational ghati
bounds and direct-state parity pass. The existing VED-015 PAC 22 September
2026 central-station sunrise comparison retains its original **60-second**
minute-resolution gate and yields ghati ordinal 7 for the selected birth
component case. This is not a published full Sayanadi chart.

Tromso's 21 June polar sunrise absence yields typed unavailability, no epoch
and no fabricated chart. Explicit readers stay open while borrowed and close
under their owning context; startup-engine readers stay open through HTTP
and close in the owning test's teardown. No new reader-ownership lifecycle
was introduced by composition. The prior active reader context is restored.

## 4. Actual execution receipts

All execution used `C:/dev/moira/.venv/Scripts/python.exe`, Python 3.14.3,
Moira 6.9.9; native import resolved
`C:/dev/moira/moira/_moira_native.cp314-win_amd64.pyd`. Test flags:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
```

The known-issue registry is empty. The test harness denied external network;
HTTP tests were marked loopback. Commands and XML receipts:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_sayanadi.py tests/unit/test_sayanadi_admission.py tests/unit/test_sayanadi_dated.py tests/unit/test_avasthas.py tests/unit/test_vedic_surface_completeness.py tests/server/test_server_sayanadi.py tests/server/test_vedic_direct_input_hardening.py -m "not external_network" -q --tb=short --junitxml=C:/dev/outputs/ved002-sayanadi-research-2026-10-08/final-focused.xml
.\.venv\Scripts\python.exe -m pytest tests/integration/test_sayanadi_ephemeris.py -m "not external_network" -q --tb=short --junitxml=C:/dev/outputs/ved002-sayanadi-research-2026-10-08/integration.xml
```

**269 focused passes plus nine integration passes: 278 distinct latest
passing tests, zero failures/errors/skips.** Scoped export/offset checks were
repeated after final import curation; they overlap the total and are not
counted again. The integration resource receipt reports 12 admitted planetary
resource uses, zero skips/failures and DE441 content identity.

Initial implementation tests exposed a misconfigured synthetic altitude
fixture and an incorrectly constructed synthetic coverage exception; those
fixtures were corrected to the existing substrate contracts. The old export
test explicitly excluding unadmitted Sayanadi was updated to verify its newly
admitted owning identity. No numerical acceptance budget was changed to pass.

Private receipts/scripts are in
`C:/dev/outputs/ved002-sayanadi-research-2026-10-08/`. The standard's supplied
JSON request was extracted and executed through the actual HTTP route: 200,
Netrapani/Vicheshta, total 51 and remainders 1/0, with exact facade-response
parity (`standard-json-smoke.json`). The final export/offset rerun passed all
17 overlapping tests with no failures/errors/skips (`export-check.xml`).

Documentation completion commands passed:

```powershell
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
git -C moira.wiki diff --check
```

The REST reference now records 484 registered paths/operations. An independent
project-Python link/register check passed 159 local file/anchor links across
eight canonical documents, 24 stable work IDs, seven closed and 17 open/bounded
packages, and five optional candidates (`completion-documentation-check.json`).
All 20 changed/new Python files pass Python 3.10 source grammar. Differential
Ruff checks against the unchanged HEAD source found zero new diagnostics;
66 pre-existing diagnostics remain: 60 E402 in root imports, five F811 in the
facade and one F841 in another avastha family (`lint-grammar.json`). No unrelated
lint cleanup was applied. These are scoped verification receipts, not a
full-suite or whole-engine certification.

## 5. Limits and completion meaning

The selected source recipe and engineering admission are complete locally.
The competing degree-lineage quantization/source questions, complete textual
certification of the retained effect summaries, mean-node birth composition,
terrain/observational sunrise accuracy and predictive-effectiveness studies
are outside this bounded contract. Their absence does not conceal unfinished
work in the admitted calculation/transport. The output labels legacy prose
as `not_source_certified` with `conditions_evaluated=false`.

Strict invalid-input rejection, corrected partition-boundary outputs and
additive JSON metadata are intentional compatibility changes. Valid existing
four-family results and no-Sayanadi omission behavior are preserved. After
local validation the user authorized committing/pushing the generated wiki
first and the parent engine package second; see register section 24. Package
release, deployed endpoints and website adoption remain separate actions.
