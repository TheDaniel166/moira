# VED-005 REST admission and policy validation — 8 October 2026

**Outcome:** locally complete for the selected 30-route admission, reader and
policy repair. Source publication, package release, deployment and product
adoption are separate actions. This receipt describes the validated repair
from engine `main` baseline `cdd83ecaff6daa75012080c50207fed6cdb4467d`,
version 6.9.9, and generated wiki baseline
`44ee813066241ff5884406d80b0206251032da5a`.

The [owning standard](../02_standards/VEDIC_REST_ADMISSION_STANDARD.md)
defines the admitted contract and compatibility changes. Engine registries,
computation policies and reader ownership govern this repair. No classical
rule, source table, formula, numerical acceptance budget, native code,
dependency or version was changed.

## Evidence before implementation

The read-only audit inventoried five Vimshottari, nine Ashtottari/Yogini,
six Shadbala, seven Vedic dignity, two Sade Sati and one Vedic profile route.
It exercised 124 model probes, 29 traced HTTP requests and ten real-lifecycle
requests. The existing seven-suite baseline passed 83 tests with no failures
or skips. Those passes did not establish production reader ownership: the
test harness's ambient reader masked the following startup defect.

Private pre-change artifacts are preserved under
`C:/dev/outputs/ved005-audit-2026-10-08/`, including `AUDIT.md`, probe scripts,
JSON results and baseline JUnit XML. Repair artifacts are separately stored
under `C:/dev/outputs/ved005-repair-2026-10-08/`.

| Reproduced defect | Repair and regression evidence |
| --- | --- |
| Valid Shadbala and default Vedic profile failed with HTTP 500 when startup discovered the planetary kernel but no global reader was configured. | Call existing `engine.shadbala` under its owning facade reader; all six Shadbala routes and the bundle run in an empty reader context, with ownership checked. Real app startup also succeeds without factory substitution. |
| Numeric/Boolean/string coercion and numeric timestamps crossed remaining request boundaries, including profile composition. | Strict finite numbers, integer/Boolean fields and aware civil timestamp admission; hostile input returns the existing 422 envelope before astronomy dispatch. Numeric timestamp strings are also rejected by the shared Panchanga chart boundary. |
| Unknown period lords, foreign systems, invalid levels and malformed child intervals were admitted by alternate-dasha period-profile input. | Registry-owned lords, levels 1–4, positive finite duration, same-system next-level ordered children, containment and eight-child limit. |
| Invalid selected ayanamsa/year policies or profile inputs could fail after chart/Panchanga work. | Validate identities in request models; preflight selected profile children and bodies before dispatch. Invalid supplied Hora identity is rejected even when its component is omitted. |
| Dignity relationship routes silently skipped unknown planet keys; Shadbala silently defaulted unknown house names. | Reject non-classical keys and unsupported house identities, while preserving valid partial seven-body maps and supported code/name aliases. |
| An omitted chart alternate-dasha policy produced Lahiri periods while Raman chart provenance was returned. | Select the requested chart frame in the omitted policy; compare returned sequence/profile against the direct engine-backed route for both Ashtottari and Yogini. The regression failed before the fix. |
| Mixed component frames and house fallback were not explicitly summarized. | Add Shadbala applied-policy receipts and a Vedic bundle receipt; preserve intentional mixed frames and disclose the actual polar house fallback and omitted-component inputs. |

The earlier exact child-containment draft rejected 15 of 16 generated trees
because binary64 endpoints accumulate rounding. Admission now uses the
existing alternate-dasha interval-validation tolerance, `1e-6` Julian day.
No endpoint is rewritten. Tests cover both sides of this existing tolerance,
overlap, foreign systems and overflowing duration. Each level-1 input tree
has at most 585 nodes; partial trees remain admitted.

## Runtime and verification

All commands used `C:/dev/moira/.venv/Scripts/python.exe`, Python 3.14.3.
The planetary resolver selected
`C:/Users/nilad/.moira/kernels/de441.bsp` with downloads disabled. Tests used
strict known-issue expiry and the standard denied-network harness. No known
issue waiver or tolerance relaxation was added.

The family run covered these files:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest `
  tests/server/test_vedic_rest_admission.py `
  tests/server/test_vedic_rest_models.py `
  tests/server/test_server_phase8_dasha_routes.py `
  tests/server/test_server_alternate_dashas_routes.py `
  tests/server/test_server_shadbala_routes.py `
  tests/server/test_server_shadbala_service.py `
  tests/server/test_server_vedic_dignities_routes.py `
  tests/server/test_server_vedic_phase2_routes.py `
  tests/server/test_server_profile_bundle_routes.py `
  tests/server/test_server_time_scale_adapters.py `
  tests/server/test_server_panchanga_routes.py `
  tests/server/test_server_panchanga_service.py `
  -m 'not external_network' -q --tb=short `
  --junitxml=C:/dev/outputs/ved005-repair-2026-10-08/verification.xml
```

That run collected 172 tests: 170 passed and two obsolete error-wording
assertions failed after dictionary keys became typed classical identities.
Those assertions were corrected to check both the validation message and
the `sidereal_longitudes.Pluto` error location, then both passed. The final
admission rerun passed 63 tests; the final model rerun passed 24, including
three additional regressions beyond the family run's collection. Deduplicating
by JUnit class/name and taking each test's latest result gives **175 distinct
passes, zero remaining failures, errors or skips**. This is not a sum of reruns.

The exact result inputs are `verification.xml`, `final-admission.xml`,
`dignity-key-errors.xml` and `final-models-fixed.xml` in the repair directory.
The broad run recorded 59 successful resource receipts and one DE441 content
probe; the final admission run recorded seven resource receipts and one
content probe. Repeated resource use is not an independent numerical oracle.

Permanent tests additionally cover:

- all 30 valid HTTP contracts under a clean context with the serving engine's
  reader; route inputs cannot dispatch astronomy when malformed;
- all currently registered ayanamsas, supported house names/codes, finite
  longitude wrapping and valid partial classical maps;
- sixteen engine-generated alternate period trees across two systems, two
  year bases and four Moon inputs;
- UTC/UT1 adapter semantics, existing numerical/component-route parity and
  omission states;
- polar Placidus fallback receipts matching the actual engine result;
- mixed Panchanga/Shadbala frames, inactive policy inputs and a receipt
  that follows the engine's selected default Vimshottari year policy.

`lifecycle-probes.json` records ten requests through real application
lifespans without a substituted engine factory. Discovered-kernel startup
passed Shadbala chart, full response and default Vedic profile. Explicitly
configured-kernel startup passed those three plus a full house name and a
mixed-frame profile; Boolean latitude and unknown house identity returned
422. All ten matched their intended status.

## Documentation and shape review

Canonical REST reference and dasha, alternate-dasha, Shadbala and dignity
standards were reconciled with the new admission contract. The remaining-work
register closes VED-005 at this finite scope and carries VED-021/022 receipts;
Sayanadi remains a separate VED-002 evidence/admission package. Generated
wiki pages are derived only through `scripts/sync_git_wiki.py`.

Final structural and documentation checks passed:

| Check | Result |
| --- | --- |
| Scoped `.venv` Ruff over the changed Python files | All 19 files passed. |
| `ast.parse(..., feature_version=(3, 10))` over those files | All 19 passed grammar compatibility; this is not a Python 3.10 runtime test. |
| `create_app().openapi()` | 482 paths constructed; both new receipt schemas present. |
| `scripts/check_doc_consistency.py` | Passed. |
| `scripts/sync_rest_api_reference.py --check` | Route inventory current. |
| Changed canonical documentation relative file links | 89 existing destinations verified. |
| `scripts/sync_git_wiki.py` and `--check` | Eight derived pages written; remaining 351 unchanged; mirror in sync. |
| Engine and nested wiki `git diff --check` | Passed. |

The generator inventories canonical documents through Git. The two new
canonical documents were registered with `git add --intent-to-add` so the
owning generator could include them during local validation. Validation
artifacts remain private local evidence rather than
runtime dependencies.

The shape review preserves existing numerical service return types and
independent serializer calls. Reader binding belongs to the existing engine
facade; transport receipts expose that engine's truth. REST models import
engine identity registries rather than introducing a second numerical
backend. No engine/native implementation or website ownership was changed.

## Explicit limits

These checks establish admission, lifecycle and transport fidelity for the
selected routes. They do not certify historical authority for every Vedic
component, predictive outcomes or all other Vedic endpoints. Previously
coerced JSON values, unknown dignity keys, malformed period trees and unknown
house systems now require client correction. Existing valid partial dignity
maps and intentional component frame overrides remain supported.

Sade Sati's HTTP span cap and execution/response budgets for existing deep
Vimshottari generation remain a separately scoped operational frontier.
This package preserves current date coverage and depth rather than admitting
an unreviewed budget policy. Publication, release and website adoption are
not implied by local closure.

## Authorized source publication

The user approved beginning the next move on 8 October 2026, including
commit/push of VED-005 before VED-002 research. The generated wiki is published
first and the parent engine then records its gitlink with this scoped repair.
Publication does not change the version, validation thresholds or admitted
technique rules and does not imply release, deployment or website adoption.
