# Classical-derived D60 execution receipt

Date: 7 October 2026. Engine owner: `moira.varga`; VED-003.
Outcome: the explicit classical-derived full-position policy is implemented
and locally validated. Its source chain and generalisation are disclosed;
direct classical D60 degree prescription is not claimed.

## Implemented contract and changed files

- `moira/varga.py`: adds `D60Method.CLASSICAL_DERIVED_LINEAR`, the reviewed
  source/derivation chain and `VargaPoint.d60_degree_attribution`. Shares the
  existing forward/proportional source-profile coordinate calculation.
  Source-profile strength normalizes inputs before other divisions and D1
  relationships.
- `moira/_facade_vedic.py`: source-profile Shodashvarga composition uses the
  same canonical circular input before evaluating its other divisions.
  Existing named/chart delegation carries the new enum without new exports.
- `moira_server/models/varga.py`: all seven named/batch/chart full-position
  selectors advertise the new policy; strict source-profile numeric preflight
  applies to both full source profiles. Responses type the degree-attribution
  category.
- `moira_server/serializers/varga.py`: copies the canonical degree-attribution
  property. All eight placement responses use this serializer.
- `moira_server/services/varga.py`: source-profile composition shares circular
  normalization; strength and vargottama flags receive consistent inputs.
- Unit and server D60 tests: new source-scope/rational checks, both-profile
  external-witness checks, receipt/applicability/OpenAPI assertions and tiny
  negative composition regressions. Existing Chara admission checks retain
  their behavior and acknowledge the expanded D60 selector.
- Standards, API/REST references, the work register, Home and changelog:
  reconcile current admission and historical claims. The new
  [source adjudication](../06_roadmap/D60_CLASSICAL_DERIVED_ADMISSION_2026-10-07.md)
  records the wider search and source identities. The earlier negative
  admission decision is explicitly superseded for the derived category.

The governing degree object is proportional progress in a selected D60
subdivision. BPHS Santhanam governs half-degree partitions, destination signs
and deity ordering. Saravali, Jataka Parijata and Raman's Prasna Marga notes
support separately scoped arithmetic/correspondence. The extension to D60
degrees belongs to Moira. The stricter direct-classical-attribution criterion
is retained in the [source standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md).

No Chara arithmetic, deity spelling, ephemeris/frame/ayanamsa default, other
division sign doctrine, harmonic default or modern PVR source locator is
changed by this reconciliation. Existing dirty Chara/D60 work is preserved.
No comparator implementation becomes a runtime dependency. No oracle,
snapshot or baseline tolerance is rewritten. Website work, release and
publication are separate from this local execution.

## Authority checks and arithmetic invariants

All 720 half-degree subdivisions across 12 natal signs are checked at their
starts, representable right/left neighbours, interiors and excluded ends,
including natal-sign and zodiac wrap. The independent oracle uses exact
`Fraction` arithmetic over the actual binary input: source sign index must
agree exactly, degree must equal the rationally derived float, and mapped
longitude must remain inside the selected half-open sign. Even-sign deity
reversal is checked separately.

The source-published Capricorn 13 degrees 25 minutes -> Pisces sign is retained
as a sign witness. Its derived 25-degree coordinate is not relabelled as a
published coordinate. The test accounts exactly for conversion of that
decimal input to binary64 rather than introducing a wider oracle tolerance.

Raman's notes provide two primary **commentarial D9** full-position examples:
Cancer 24 degrees 25 minutes -> Aquarius 9 degrees 45 minutes, and Taurus
25 degrees 11 minutes -> Leo 16 degrees 39 minutes. Exact rational arithmetic
and the existing Navamsa implementation agree within `1e-12` degrees after
binary input conversion. The inconsistent Gulika line is recorded as an
erratum and excluded. These D9 examples are corroboration of the stated
degree construction, not published D60 coordinates.

## External conditioned mapping corpus

The existing immutable 4,552-case
[`d60_cross_engine_2026-10-07.json`](../../tests/artifacts/oracle/d60_cross_engine_2026-10-07.json)
is now exercised against both named full source profiles. Its recorded
profile identity remains the original modern profile; this does not rewrite
the evidence's provenance. The new policy shares its declared numeric
mapping, and must meet those same independent expected values and thresholds.

Fresh evaluation of `classical_derived_linear` also checked all **24,432**
inputs against the previously recorded independent-function outputs:

| Corpus stratum | Inputs |
| --- | ---: |
| Three interiors in every half-degree subdivision | 2,160 |
| Exact and adjacent subdivision boundaries | 2,160 |
| Seeded random longitudes | 20,000 |
| Seven DE441-derived planetary inputs in sixteen date/frame charts | 112 |

Rational disagreements: **0**. Secondary-comparator sign disagreements: **0**.
Degree disagreements exceeding the unchanged predeclared budget: **0**.
Absolute degree tolerance remains `8*ulp(2160.0)` =
`3.637978807091713e-12` degrees, with no sign tolerance.
Maximum degree residual is `1.1368683772161603e-13` against PyJHora full
positions and `2.2737367544323206e-13` against Maitreya's instrumented
intermediate. Maitreya's returned product is a sign; its intermediate is not
misrepresented as a published full-position API.

Pinned comparator identities, extraction/build scope and the original corpus
generation are owned by the [broader validation receipt](D60_CROSS_ENGINE_VALIDATION_2026-10-07.md)
and [`scripts/d60_cross_engine_sources.json`](../../scripts/d60_cross_engine_sources.json).
The new run verifies those source checksums, corpus identity/order/count,
exact rational invariants and the new policy, recording hashes of consumed
input/output files. It consumes the prior comparator outputs, rather than
claiming a new full-application comparator run. Private receipts are
`C:\dev\outputs\vedic-d60-library-audit-2026-10-07\validate_classical_derived.py`
and `classical_derived_corpus_validation.json`.

These are conditioned D1-to-D60 checks: the planetary inputs originate in
Moira DE441 and are not independent ephemeris truth. Software agreement
corroborates the admitted coordinate mapping, not historical authorship or
predictive validity.

## Execution commands and outcomes

Every Python execution uses `C:\dev\moira\.venv\Scripts\python.exe`
(Python 3.14.3). Imports resolve to this checkout and its CPython 3.14 native
extension. Varga mapping is Python arithmetic; the native extension is not
claimed to supply a separate D60 implementation.

Tests set `MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`, with external-network tests excluded. The known
issue register is empty. The project resource resolver selects
`C:\Users\nilad\.moira\kernels\de441.bsp`; no download is enabled.

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_d60_classical_derived.py `
  tests\unit\test_d60_full_position.py `
  tests\unit\test_d60_cross_engine.py `
  tests\unit\test_d60_published_evidence.py `
  tests\unit\test_vedic_chara_d60_admission.py `
  tests\server\test_d60_full_position.py `
  tests\server\test_d60_cross_engine.py `
  tests\server\test_vedic_chara_d60_admission.py `
  -q -m "not external_network" `
  --junitxml=C:\dev\outputs\vedic-d60-library-audit-2026-10-07\classical_derived_tests.xml

.\.venv\Scripts\python.exe C:\dev\outputs\vedic-d60-library-audit-2026-10-07\validate_classical_derived.py
```

The main focused run passed **1,528 tests**, with zero failures, errors or
skips. Its resource receipt records **44 real-reader tests**, all run with
DE441, one content probe and zero resource failures/skips. This includes both
full profiles across all seven REST shapes, sixteen external-witness
date/frame chart batches per profile, two strength groups, input rejection
before resource work, and preservation of modern/harmonic receipts.
Two additional REST strength left-wrap regression cases were subsequently
added. The supplementary run passed **132 tests** (110 full-position REST
tests and 22 public API adversarial checks), with zero failures/errors/skips
and nine successful DE441 resource receipts. Across both final runs, **1,552
distinct test cases pass**; overlapping cases are counted once.

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\server\test_d60_full_position.py `
  tests\unit\test_api_surface_adversarial_audit.py `
  -q -m "not external_network" `
  --junitxml=C:\dev\outputs\vedic-d60-library-audit-2026-10-07\classical_derived_supplementary.xml

.\.venv\Scripts\python.exe -m ruff check `
  moira\varga.py moira\_facade_vedic.py `
  moira_server\models\varga.py moira_server\services\varga.py `
  moira_server\serializers\varga.py `
  tests\unit\test_d60_classical_derived.py tests\unit\test_d60_cross_engine.py `
  tests\server\test_d60_full_position.py tests\server\test_d60_cross_engine.py `
  tests\server\test_vedic_chara_d60_admission.py

.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe C:\dev\outputs\vedic-d60-library-audit-2026-10-07\verify_policy_docs.py
git diff --check
```

All these checks pass. The API example executes and returns Cancer 7.5
degrees with the classical-derived receipt. All nine touched canonical wiki
pages' local links and fences pass, and **357 canonical pages** render through
the actual wiki generator in memory, including the new untracked pages. No
mirror file is written or published. The tracked-only publishing script
would omit untracked pages before staging. Private receipts retain XML test
results and the documentation-check JSON. Live SHA-256 checks confirm all
five book/facsimile identities in the source adjudication.

Publication review additionally runs Ruff across the full pending Chara/D60
package. The 20 changed implementation/test/validator files outside the two
curation modules pass. `moira/__init__.py` has 60 diagnostics and
`moira/facade.py` has five; a stdin-based comparison against `git show HEAD:<path>`
confirms exactly the same rule/message multiset in the baseline and working
copy, with **zero newly introduced diagnostics**. Line-number references are
normalised for comparison. Existing curation lint debt is not represented as
a successful whole-package lint run or repaired by this publication.
The doc and REST inventory checks, the executable API example and all nine
touched pages' local-link checks also pass after the closure update.

## Boundary repair and provenance review

The first new tests exposed a pre-existing raw-input composition fault:
`-1e-300 % 360` rounds to 360 in another division and can produce an invalid
sign index. Both opted-in full source profiles now normalize the shared
input before composing the other divisions and strength relationships. The
harmonic compatibility path is unchanged; this is not a general rewrite of
legacy Varga normalization. Direct D60, composed facade/REST results and
strength are covered for the repaired source-profile boundary.

The exact-input example test initially used an undersized decimal/binary
comparison budget, and a facade test omitted its reader slot. Both test
assumptions were corrected. No source coordinate, frozen fixture or numerical
baseline was changed to obtain a pass.

The implementation uses the declared subdivision/sign/progress objects and
the existing source-profile arithmetic; it contains no comparator branch,
external slot ordering, copied helper, or output-driven adjustment. The
representable left-limit guard follows the selected half-open domain.
Provenance properties distinguish equal coordinates from equal authority.
Rational/source-scope checks provide the derivational evidence; secondary
software is corroboration rather than the historical admission authority.

The finite derived-profile implementation and validation are complete.
Direct classical D60 degree prescription, exact primary-publication planetary
pairs and predictive validity remain separately unclaimed. Their absence
does not leave the admitted product's engineering validation unfinished.
