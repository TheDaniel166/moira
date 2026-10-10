# D60 full-position validation receipt

Date: 7 October 2026. Outcome: the named modern `pvr_textbook_linear` profile
is locally implemented and validated. Classical continuous-degree attribution
and a qualified published planetary full-D60 oracle remain unestablished.
The [completed broader comparison](D60_CROSS_ENGINE_VALIDATION_2026-10-07.md)
adds 24,432 independent-software comparisons, frozen external coordinates,
all-shape REST checks and sixteen real-reader chart batches. Modern computational
validation is complete within that declared scope; historical source admission
remains a separate frontier. Earlier runs below retain their original scope.
The completed follow-up [evidence adjudication](../06_roadmap/D60_EVIDENCE_ADJUDICATION_2026-10-07.md)
adds independent source signs and one conditional rounded arudha-point pair;
its execution is recorded separately at the end of this receipt.
The [source/admission packet](../06_roadmap/D60_FULL_POSITION_SOURCE_RESEARCH_2026-10-07.md)
and [owning standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md) govern
the composed profile and evidence limits.

## Environment and ownership

Checkout `C:\dev\moira`, branch `main`, starting HEAD
`67b66de14cde0447730b0c9b57e5e14c1edd9935`, version 6.9.9. Executions use the
project `.venv\Scripts\python.exe` (Python 3.14.3) and the installed
`moira/_moira_native.cp314-win_amd64.pyd`. The Varga doctrine has no admitted
native counterpart; no native port or rebuild was required. Reader integration
uses installed `C:\Users\nilad\.moira\kernels\de441.bsp` with downloads
disabled. Real-chart tests confirm engine-to-REST consistency in the returned
sidereal frame; they are not external astronomical accuracy comparisons.

The earlier locally verified Chara/sign/deity package is preserved. This
extension edits the Varga doctrine, Vedic facade, Varga models/services/shared
serializer, focused tests, owning standards/references/register/Home/changelog
and adds this receipt and source packet. No other doctrine family, website,
Urania, build/harness policy, known-issues exemption, golden/snapshot baseline,
validation tolerance or generated `moira.wiki` is changed. The current package
remains uncommitted/unpushed; release and deployment are separate authorization.

## Implemented contract and evidence

| Surface | Verification |
| --- | --- |
| `moira/varga.py` | Strict enum and finite inputs for the opt-in profile, shared circular normalization, natal-sign sequence, linear within-part degree mapping and independent deity reversal. Both positional authorities returned by canonical point/strength properties. |
| Vedic facade | Scalar/named, chart, Shodashvarga and Shodashvarga chart methods apply the selected method; unrelated divisions and sign-only selections fail before chart/resource work. |
| Seven REST request shapes | Scalar/batch, Shodashvarga/batch and three chart shapes apply the same profile and source receipts. OpenAPI declares exactly harmonic/PVR full-position methods. Invalid, null, sign-only and inapplicable selections give the validation envelope before chart work. |
| Strict new-profile transport | Bool, numeric string, NaN, infinity and overflowing integer cases rejected in direct scalar/batch requests. Legacy harmonic and generic request contracts preserved. |
| Generic and non-D60 | Generic D60 stays harmonic with `deity=null`. Non-D60 results have no applied D60 method and empty authority arrays. Shodashvarga changes only D60. |
| Vimshopaka | PVR and Santhanam sign methods give identical sign-dependent entries while retaining different actual authority receipts. Hand-derived Venus contribution delta is `-11*weight/20`, with D60 weights 5/4 retained. |

`tests/unit/test_d60_full_position.py` uses a `Fraction` oracle independent of
engine helpers for all **720 half-degree segments**, testing exact starts,
the representable point after each start, midpoints, the representable point
before each end, and exact ends with circular wrap: **3,600 positions**. It
checks sign, degree, mapped-domain containment, deity parity and method receipt.
Additional literal fixtures cover parity and zodiac wrap, normalization and
invalid values, facade preflight and strength consequences. Harmonic numeric
defaults are checked over all 720 midpoints and by existing regression tests.

Source evidence is deliberately separated. The textbook's Jupiter-to-Sagittarius
sign is published; its mapped 28-degree result is independently derived. The
2013 article's D9 worked numeral is inconsistent with its stated multiplication:
the law gives 12 degrees 45 minutes, versus printed 13 degrees 45 minutes.
The test preserves that discrepancy and follows exact arithmetic, with the
article's consistent D24 reverse example as corroboration. Published D60
coordinates without natal D1 pairs are contextual evidence, not replayed
oracles. No assertion of a classical D60 degree verse, current JHora agreement,
predictive effectiveness or whole-literature completeness follows.

## Commands and outcomes

All pytest commands ran with `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, `MOIRA_NO_DOWNLOAD=1`, the unchanged
deny-by-default network harness and `-m 'not external_network'`. Marked server
tests permit loopback; no external-network tests were selected.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_d60_full_position.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_d60_full_position.py tests/server/test_vedic_chara_d60_admission.py -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-full-position-2026-10-07/focused.xml
.\.venv\Scripts\python.exe -m pytest tests/unit/test_varga.py tests/unit/test_shodashvarga.py tests/unit/test_d60_deities.py tests/unit/test_vedic_facade.py tests/server/test_server_varga_routes.py -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-full-position-2026-10-07/regression.xml
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_vedic_phase2_routes.py -k vimshopaka -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-full-position-2026-10-07/strength_regression.xml
```

Results: **964 focused + 155 regression + 3 strength regression = 1,122 distinct
tests passed**, zero failures/errors/skips in those final runs. Focused harness
receipts recorded nine resource uses, all successful, content-probed DE441.
The new profile includes three real-reader chart shapes; separate stubbed
contexts isolate transport and preflight. This is focused acceptance and
regression coverage, not the whole repository suite or native Varga parity.

The initial 846-test unit run had two failures: the source arithmetic error
above and a missing `_reader_obj=None` setup in a pure-facade test fixture.
Both were adjudicated explicitly; the final focused run re-executed those
nodes successfully. No harness policy, baseline or threshold was weakened.

```powershell
.\.venv\Scripts\python.exe -m ruff check --output-format=json moira/varga.py moira/_facade_vedic.py moira_server/models/varga.py moira_server/services/varga.py moira_server/serializers/varga.py tests/unit/test_d60_full_position.py tests/server/test_d60_full_position.py tests/server/test_vedic_chara_d60_admission.py
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
git diff --check
```

Lint: zero diagnostics in this extension's runtime/test files. Documentation
guard, generated REST inventory, whitespace, executable API snippet and
in-memory owning wiki render/link checks are recorded in the private
`document_validation.json`. Generated wiki files are not written by this check.
The earlier package's unrelated root/facade baseline lint findings remain
outside this extension and were not concealed by a whole-repository clean claim.

## Bounded evidence follow-up

The agreed finite review is complete with no new classical full-degree
admission or runtime repair. The governing computational object remains
`pvr_textbook_linear`, an explicit Moira composition of two dated prescriptions.
The inspected second BPHS edition is Girish Chand Sharma's 1999 reprint;
its D60 passage is chapter 7.33-41. Private source hashes, page identities,
visual review and ambiguity decisions are in the linked adjudication.

This pass adds `tests/unit/test_d60_published_evidence.py` and
`wiki/06_roadmap/D60_EVIDENCE_ADJUDICATION_2026-10-07.md`; updates the D60
source standard, full-position research packet, Vedic work register, Home,
changelog and this protected validation receipt. The earlier engine/facade/REST
package, harness, known issues, goldens, snapshots and generated wiki are
preserved. Sources remain private; no commit, push, release or deployment.

The new tests contain **75 cases**: 72 comparisons against three literal
published Sharma table rows over twelve natal signs and two admitted sign
methods, two comparisons against its worked Gemini-to-Scorpio example, and
one conditional rounded arudha-point comparison. Table samples are interior
test inputs, not additional source-published coordinates. The point fixture
preserves the exact printed-center mismatch of 23 D60 arcminutes, proves
interval compatibility only under nearest-minute rounding, and records that
truncation would fail. These are precision-derived intervals, not a changed
engine tolerance or an exact planetary oracle. No ephemeris/resource is used.

With the same environment flags and network selection above:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_d60_published_evidence.py tests/unit/test_d60_full_position.py tests/unit/test_vedic_chara_d60_admission.py -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-evidence-pass-2026-10-07/units.xml
.\.venv\Scripts\python.exe -m ruff check tests/unit/test_d60_published_evidence.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-d60-evidence-pass-2026-10-07/verify.py
```

**921 unit cases passed**, zero failures/errors/skips: 75 new evidence cases
and 846 re-executed admission/profile cases. The earlier 1,122-test checkpoint
is retained as historical execution evidence; the 75 new nodes bring its
distinct verified-node union to **1,197**, not 2,043. Server/reader tests were
not rerun for this source/test/document-only follow-up. Lint, document guard,
REST inventory, whitespace and in-memory owning wiki render/link checks are
recorded in private `verification.json`. The package remains locally verified
and uncommitted; no classical, current-software or predictive validation claim
is inferred from passing these tests.
