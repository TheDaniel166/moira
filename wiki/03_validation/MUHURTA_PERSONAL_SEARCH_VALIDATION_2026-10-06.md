# Personalized Muhurta repair: validation and source-publication receipt

Date: 6 October 2026. Decision: VED-004 and VED-006 are **locally complete for
the bounded existing-profile, sampled/JD-weekday contract**. The user subsequently
authorized Git source publication of this package. Release, deployment, full
classical authority validation, predictive validity, exact transitions and
sunrise-owned search remain outside this receipt.

The [owning standard](../02_standards/MUHURTA_PERSONAL_SEARCH_STANDARD.md) defines
the object, selected policy, evidence, compatibility changes and exclusions.

## Runtime, scope and files

- Checkout `C:\dev\moira`, branch `main`, starting commit
  `cbb4abcbd74e1ae5bf09c87ff3ee7006e620e471`; initially clean.
- Project `.venv\Scripts\python.exe`: Python 3.14.3, Moira 6.9.9,
  `moira/_moira_native.cp314-win_amd64.pyd` loaded. No native numerical or build
  files were changed, so no rebuild was needed.
- `tests/KNOWN_ISSUES.yml` was empty. Selected tests used strict expiry,
  deny-by-default network policy and marked loopback HTTP test clients.
- Planetary resource was discovered with `MOIRA_NO_DOWNLOAD=1` through
  `find_planetary_kernel()`: the installed user-cache `de441.bsp`. Harness
  content probes confirmed DE441. No kernel download or external network test
  was used.

| File group | Change |
| --- | --- |
| `moira/muhurta.py` | Seven-weight/overflow validation, fixed reserved flag, named existing profile, strict natal inputs, repaired scalar and tuple adapters; generic rule tables and score coefficients retained |
| `moira/muhurta_search.py` | Frozen inspectable moment/window/search vessels, explicit reader clocks and true frames, typed resource/coverage failures, complete capped grid, threshold runs and stable ranking |
| `moira/panchanga.py` | Existing limb arithmetic extracted into one shared private reducer; public instant arithmetic retained |
| Root, `facade`, `vedic`, `_facade_vedic` | Eight shared-identity exports, two reader-bound methods, UTC/UT1 chart adaptation and sanitized reader failure |
| Muhurta/Panchanga server models and services, new search models/service | Strict numbers/timestamps, actual policy receipts, effective ayanamsa frame coherence, typed canonical search transport |
| Muhurta router, error mapping, OpenAPI/model exports | `POST /v1/muhurta/search`, specific 422 coverage/503 resource envelopes, discoverable classical-vedic metadata |
| Unit/integration/server tests | Hostile input, composition, reader, window, cap, export and HTTP contracts |
| Standards, initial transport design, API/REST reference, work register, Home, changelog | Current admission and remaining boundaries; June design marked historical; generated wiki synchronized through its owning tool |

No other Vedic family, website, Urania, kernel, classical table, scientific
constant, golden/snapshot artifact or numerical acceptance tolerance was
modified. The full repository test suite and repository-wide lint were not
run; the selections below own this receipt.

## Verified evidence

| Contract | Evidence and limit |
| --- | --- |
| Existing judgment | Existing generic/Tara/Chandra tests remain green, including nine-Tara, twelve-house Chandra, Chandrashtama and one-ulp Nakshatra cases. These are implementation/structural checks, not new edition collation. |
| Policy and numeric boundary | Seven weights reject bool/string/nonfinite/negative/overflow input; zero/custom weights preserve engine/HTTP results. Reserved flag changes reject instead of being ignored. Moment/chart numbers and numeric timestamps are strict. |
| Effective frame | Nested Panchanga policy owns the generic score and both personalized overlays. Generic/classification receipts disclose unapplied natal weights and the fixed rule profile. |
| Reader and clock | Explicit reader and context restoration checked on success/coverage failure; missing facade reader cannot borrow an ambient kernel. ChartContext UT1/TT and public Chart civil-UTC/Delta-T ownership are handled explicitly. Invalid dates and sample caps preflight before search resource access. |
| Installed ephemeris | All 12 named ayanamsas at two 6 October 2026 samples; 1600, 1900, 2000 and 2100 clock cases. Sun/Moon longitudes and ayanamsa compare with the existing owning engine using absolute `1e-10` degree tolerance; clock coordinates/receipts and personal scores agree exactly. This is shared-engine composition consistency, not independent JPL/IAU or external-engine validation. |
| Resource semantics | Actual DE441-uncovered epochs yield coverage errors; injected missing kernel/live-anchor cases yield resource failures. A missing live anchor does not use a polynomial fallback. Failures never yield a partial/empty success. |
| Sample selection | Both endpoints exactly once, clipped final step, exact 4096 budget including endpoint, rejected-point splits, singleton-capable spans, earliest peak ties, later stronger run retained before top cap, adjacent brackets, successful empty selection and explicit truncation. Synthetic scan fixtures are not astronomical source fixtures. |
| Legacy compatibility | Named natal Nakshatra without Moon rejects, contradictory natal inputs reject, supplied ElectionalEvaluation unwraps its tropical chart, incompatible legacy body/frame/gap/refinement settings reject, and the tuple view matches the canonical personal search. |
| HTTP | Installed-engine result parity for fields/order/peak/score/clocks, hostile scope rejected before compute, structured 422/503/request-ID behavior, GET rejection, 12-ayanamsa and cap OpenAPI schemas, and discovery family. |
| Exports/discovery | Root/facade/Vedic share identity; static public/method inventory passes. The earlier published dated-Gochar eleven names/two methods were explicitly added to the stale static guard. Gochar tag ordering was reconciled to the existing metadata/core-first test; no Gochar runtime behavior changed. |

## Commands and receipts

All test commands were prefixed with:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
```

The broad final selection:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_muhurta.py tests\unit\test_muhurta_search.py tests\unit\test_panchanga.py tests\unit\test_daily_panchanga.py tests\unit\test_electional.py tests\unit\test_vedic_surface_completeness.py tests\unit\test_api_surface_adversarial_audit.py tests\integration\test_muhurta_search.py tests\server\test_server_muhurta_search.py tests\server\test_server_muhurta_routes.py tests\server\test_server_panchanga_routes.py tests\server\test_server_panchanga_service.py tests\server\test_server_vedic_phase2_routes.py tests\server\test_server_route_discoverability.py tests\server\test_server_error_mapping.py -m "not external_network" -q --junitxml=C:\dev\outputs\muhurta-personal-search-2026-10-06\targeted.xml
```

Result: **630 passed**, zero failed/errors/skips, 91.107 seconds. Harness:
111 successful planetary-resource receipts, one DE441 content probe.

The final chart/cap/HTTP slice after explicit civil-chart adaptation and date
bounds:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_muhurta_search.py tests\integration\test_muhurta_search.py tests\server\test_server_muhurta_search.py -q --junitxml=C:\dev\outputs\muhurta-personal-search-2026-10-06\final-search.xml
```

Result: **143 passed**, zero failed/errors/skips, 30.991 seconds; 81 successful
resource receipts and one DE441 probe.

Final reader/preflight slice after sanitized facade resource handling:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_muhurta_search.py tests\integration\test_muhurta_search.py -q --junitxml=C:\dev\outputs\muhurta-personal-search-2026-10-06\final-reader.xml
```

Result: **87 passed**, zero failed/errors/skips, 6.392 seconds; 23 successful
resource receipts and one DE441 probe. The union of JUnit `(classname, name)`
keys is **635 distinct passing cases**, not the sum of repeated runs. XML
attributes and the union were checked with the project runtime and saved to
`C:\dev\outputs\muhurta-personal-search-2026-10-06\summary.json`.

The saved standard's executable example also ran against the installed engine:
25 reader-bound samples, one returned run, identity `DE-0441LE-0441`.
Assertions verified exact start/end, TDB presence, personal mode, threshold
qualification and peak membership. This was a real-kernel contract smoke.

Scoped lint and documentation checks:

```powershell
.venv\Scripts\ruff.exe check moira\muhurta.py moira\muhurta_search.py moira\panchanga.py moira\_facade_vedic.py moira_server\models\muhurta.py moira_server\models\muhurta_search.py moira_server\models\panchanga.py moira_server\services\muhurta.py moira_server\services\muhurta_search.py moira_server\routers\muhurta.py moira_server\errors.py moira_server\openapi.py tests\unit\test_muhurta_search.py tests\integration\test_muhurta_search.py tests\server\test_server_muhurta_search.py --no-fix
.venv\Scripts\python.exe scripts\sync_rest_api_reference.py --check
.venv\Scripts\python.exe scripts\check_doc_consistency.py
.venv\Scripts\python.exe scripts\sync_git_wiki.py
.venv\Scripts\python.exe scripts\sync_git_wiki.py --check
git diff --check
```

All final checks passed. Python 3.10 grammar was also checked for the new module,
models, service and affected facade/scoring/reducer files; other Python runtime
versions were not executed. Local wiki synchronization uses intent-to-add
entries for the two new canonical Markdown pages because the generator discovers
tracked files. At that validation checkpoint no file content was staged, and
no commit/push had been performed.

The initial strict-number assertion mismatch, historical tag ordering and stale
export guard were resolved explicitly; no golden data or numerical tolerance
was regenerated to make a test pass. There are no unresolved failures in the
selected final receipts.

## Source-publication scope, 6 October 2026

The subsequent instruction was "please commit and push these changes". The
publication package contains the existing Muhurta engine/public/REST changes,
their tests and canonical/generated documentation, plus the parent wiki gitlink.
The nested wiki is committed and pushed before the parent engine. The engine
remains version 6.9.9; no release tag, package publication or deployment is part
of this operation.

The saved test receipts above remain the numerical and behavioral evidence.
Only this receipt and the work-register publication wording were edited after
those checks. Publication checks use the project runtime for REST inventory,
documentation consistency and generated-wiki consistency, alongside scoped
lint, whitespace checks, staged manifests and exact local/remote branch-head
comparison. The containing source commits carry this publication package; their
identities are reported in the publication completion message.
