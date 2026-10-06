# Vedic Python and REST surface closure

Date: 6 October 2026. Owner: `C:/dev/moira`, engine `main`.

This first delivery closes identified exports of existing admitted Vedic products, adds Gochara REST and hardens existing direct Vedic requests. Daily Panchanga, special Lagnas and Kalachakra remain separate source-admission packages. The current repository is clean at the start; Python 3.14.3, engine 6.9.9 and the project native extension are verified. Baseline API-surface and Vedic Phase-2 route tests pass: 30 passed, no skips, DE441 exercised locally.

## Pre-admission evaluation

The governing route checklist is `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`. Evaluation precedes new transport design.

| Family | Decision | Basis and boundary |
| --- | --- | --- |
| Gochara supplied snapshot | `admit_now` | Twelve constitutional gates closed in `GOCHARA_CONSTITUTIONAL_LEDGER.md`; stable source-bound vessels, policies, local/aggregate/network profiles and admission catalogue. Seven classical subjects/blockers, natal-Moon reference, Phaladeepika 26 Sastri 1950; raw BAV remains separate testimony. No astronomical computation or resource acquisition is required. |
| Existing yoga, avastha, extended Jaimini, Muhurta, upagraha, Sade Sati and strength helpers | Existing admissions; close surface/validation drift | Preserve currently curated package-root/facade names and route semantics. Domain inputs must fail at the HTTP boundary rather than producing non-finite results, silently ignored bodies or accidental server errors. |
| Sayanadi | `defer_for_engine_completion` | Standalone module calculation exists, but current chart evaluator and curated package-root/facade do not admit this product. Its inputs and omitted chart result require separate evaluation. |
| Daily Panchanga, special Lagnas, Kalachakra, Vedic matching, Prashna, chakra transit systems | `defer_for_doctrine` | Record candidate work without inventing methods or treating existing instant, Western-horary or Gochar products as complete substitutes. |

Gochara is bounded synchronous read-only computation over at most seven positions and seven optional twelve-sign BAV tables. The service must call the public engine, preserve complete/partial/omitted observations, directed active/exempt witnesses, named source and selected policies, and expose the doctrine catalogue as evidence rather than executable alternative profiles. Supplied sidereal consistency and raw unreduced same-birth BAV provenance remain caller assertions. No dates or kernels are inferred.

## Intended validation

Use the project `.venv`, strict known-issue expiry and external-network exclusion. Test unified import identity, source fixtures and Gochar policy invariants; HTTP/direct-engine parity across all scope combinations; malformed numeric, unknown body/policy, partial observation, BAV and node requirements; real typed response/OpenAPI discovery and shared error envelopes; surrounding existing Vedic routes. Record final commands, outcomes, omissions and preservation after implementation.

## Completion receipt

Status: implemented and validated locally. The user authorized source commit/push on 6 October; package release and service deployment are outside this delivery. The initial clean checkout was `main` at `bf48e3cef501f536bc37058fbb7869cb03c97395`, equal to `origin/main`. No phase frontier beyond this bounded admission is claimed.

### Delivered behavior

- `moira.vedic` adds 84 already-curated names across Varga strength, Ashtakavarga helpers, Bhava Bala, yogas, avasthas, extended Jaimini, Muhurta, upagrahas and Sade Sati. Its 432 public names are unique and preserve owning-module object identities. The package root adds 16 existing facade-curated Varga names; its 1,169 public names are unique.
- Three Gochara operations expose the existing source-bound engine: snapshot evaluation, subsystem profile and doctrine-option discovery. The current registered REST inventory contains 476 operations: 37 GET and 439 POST. The `gochara` tag belongs to `classical-vedic` in OpenAPI and `/v1/meta/routes`.
- Transport preserves all four admitted policy axes, citations, selected catalogue records, partial observations, directed active/exempt Vedha relations and separate raw BAV testimony. Thirty admission records across sixteen topics remain inspectable with their limitations. Evidence outside the executable profile does not become an alternative computation mode.
- Direct yoga, avastha, extended Jaimini, Vimshopaka, Kakshya, Shodhya Pinda and upagraha requests now reject malformed numeric or named-body inputs at the request boundary. Classical and node maps are separate; node maps cannot overwrite classical bodies. Seven classical inputs are required where the existing evaluator requires them. The eight-karaka scheme requires Rahu; selected Jaimini co-lords require both Rahu and Ketu. Ashtakavarga references require all eight natal sign references in 0–11, and Shodhya tables require twelve integer counts in 0–8. Kalavela coordinates have explicit geographic bounds.
- The existing avastha `vriddha_fraction` choice is now available over REST, with finite values in 0–1. Omission preserves the existing `None` default rather than inventing a numeric Vriddha effect. Responses expose the actual selected fraction and relationship scheme.

Compatibility: affected existing direct requests now reject numeric strings, booleans and unknown keys that were previously coerced or ignored. Clients must send finite JSON numbers and the documented named bodies. Valid previously supported calculations retain engine behavior; the stricter selected-node requirements are intentional transport contracts.

### Changed-file manifest

All 26 implementation paths belong to this delivery. Source publication additionally updates the parent `moira.wiki` gitlink after synchronizing and publishing the generated mirror:

| Path | Change |
| --- | --- |
| `moira/vedic.py` | Complete existing curated Vedic imports and public-name list. |
| `moira/__init__.py` | Add the sixteen existing facade-curated Varga exports. |
| `moira_server/models/_vedic_inputs.py` | Shared strict finite numbers, named bodies, bounded sign/count types and completeness validators. |
| `moira_server/models/gochara.py` | Explicit bounded requests and canonical-vessel response views. |
| `moira_server/models/ashtakavarga.py` | Validate Kakshya and Shodhya bodies, complete sign references and table shape. |
| `moira_server/models/varga.py` | Strict named finite Vimshopaka inputs. |
| `moira_server/models/vedic_extended.py` | Strict inputs, geographic bounds, selected-node requirements and avastha policy fields. |
| `moira_server/models/yogas.py` | Strict named finite longitudes, Lagna and optional speeds. |
| `moira_server/models/__init__.py` | Export the fifteen public Gochara transport models. |
| `moira_server/services/gochara.py` | Read-only public-engine adapters and raw BAV vessel construction. |
| `moira_server/serializers/gochara.py` | Typed named-attribute projections of snapshot and subsystem profile. |
| `moira_server/routers/gochara.py` | Three thin synchronous routes. |
| `moira_server/routers/vedic_extended.py` | Forward and return the selected avastha policy. |
| `moira_server/routers/__init__.py` | Register the Gochara router export. |
| `moira_server/app.py` | Include the router in the application. |
| `moira_server/openapi.py` | Add the Gochara tag and family metadata. |
| `tests/unit/test_vedic_surface_completeness.py` | Curated family identity, root/facade parity and unique/star-import witnesses. |
| `tests/unit/test_api_surface_adversarial_audit.py` | Explicit additive expected-root contract for existing Varga names. |
| `tests/server/test_server_gochara.py` | Engine/HTTP parity, independent source-fixture pairs, policy combinations, malformed inputs and discovery. |
| `tests/server/test_vedic_direct_input_hardening.py` | Strict-input rejection and valid direct helper/policy behavior. |
| `wiki/02_standards/GOCHARA_REST_STANDARD.md` | Transport contract, executable example, source distinctions and caller assumptions. |
| `wiki/02_standards/API_REFERENCE.md` | Current unified Vedic coverage and remaining admission boundary. |
| `wiki/02_services/REST_API_REFERENCE.md` | Owning-generator inventory refresh and contract notices. |
| `wiki/06_roadmap/VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md` | Pre-admission decisions and this completion receipt. |
| `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md` | Record bounded Gochara admission and existing direct-input hardening. |
| `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md` | Correct stale Vedic absence claims and record admission/remaining scope. |

### Verification

Prerequisites: project Python 3.14.3, engine 6.9.9, Pydantic 2.13.3, local `_moira_native.cp314-win_amd64.pyd`, and existing `C:/Users/nilad/.moira/kernels/de441.bsp`. Kernel discovery and native identity were checked; no resource was downloaded. All executed pytest slices used `MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`, `-m 'not external_network'` and `-o addopts='--import-mode=importlib'`. Harness receipts confirm denied external networking, marked-only loopback, deterministic CI Hypothesis and no resource skips/failures.

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vedic_surface_completeness.py tests/unit/test_api_surface_adversarial_audit.py tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py tests/server/test_server_gochara.py tests/server/test_vedic_direct_input_hardening.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

Final focused result: **397 passed in 41.77s**, no failures or skips. These include the existing Gochara engine/source invariants, all twelve REST policy combinations, all 36 independent source-fixture Vedha pairs, directed/exempt graph reconciliation, typed discovery, public export identities and hostile input envelopes. New supplied-position Gochar routes are kernel-free; the test application deliberately has no usable engine resource.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vedic_surface_completeness.py tests/server/test_server_gochara.py tests/server/test_vedic_direct_input_hardening.py tests/server/test_server_vedic_phase2_routes.py tests/server/test_server_varga_routes.py tests/server/test_server_ashtakavarga_routes.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

Changed-family and surrounding regression result: **193 passed in 585.45s**, no failures or skips; DE441 receipts 11/run 11. This run started before the final additive avastha policy-receipt and meta-discovery assertions, which are covered by the final focused run above. Calculation and input changes were already present.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_jaimini_routes.py tests/server/test_server_shadbala_routes.py tests/server/test_server_muhurta_routes.py tests/server/test_server_panchanga_routes.py tests/server/test_server_alternate_dashas_routes.py tests/server/test_server_profile_bundle_routes.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

Neighboring Vedic regression result: **72 passed in 253.11s**, no failures or skips; DE441 receipts 58/run 58. These real chart/kernel tests exercise existing Jaimini, Shadbala, Muhurta, Panchanga, alternate dasha and profile-bundle routes after registration. The slices overlap and their counts must not be added as a unique-test total. They are scoped validation, not a full 476-operation server certification.

```powershell
.\.venv\Scripts\ruff.exe check moira/vedic.py moira_server/app.py moira_server/models/_vedic_inputs.py moira_server/models/gochara.py moira_server/models/ashtakavarga.py moira_server/models/varga.py moira_server/models/vedic_extended.py moira_server/models/yogas.py moira_server/openapi.py moira_server/routers/__init__.py moira_server/routers/gochara.py moira_server/routers/vedic_extended.py moira_server/services/gochara.py moira_server/serializers/gochara.py tests/unit/test_vedic_surface_completeness.py tests/unit/test_api_surface_adversarial_audit.py tests/server/test_server_gochara.py tests/server/test_vedic_direct_input_hardening.py --no-fix --output-format concise
.\.venv\Scripts\python.exe -m compileall -q moira_server
$env:MOIRA_NO_DOWNLOAD='1'
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
git diff --check
```

All listed checks pass. Additional Ruff audits of public export registries retain pre-existing debt: root `moira/__init__.py` preserves 59 findings, and `moira_server/models/__init__.py` preserves one F811 finding for the already-repeated `SolarConditionTruthResponse`. Each initial-HEAD/current-file comparison used `ruff check --stdin-filename <path> --output-format json -`, compared diagnostic kind/message multiplicities and found no introduced diagnostics. A direct `ruff check moira_server/models/__init__.py --no-fix --output-format concise` reports that existing finding; these comparisons do not claim either registry is lint-clean. The saved JSON example in `GOCHARA_REST_STANDARD.md` was extracted and executed against the real service, verifying both blocked subjects and reciprocal active edges. The route inventory was refreshed through `scripts/sync_rest_api_reference.py`, then checked through its owning generator.

During development, one new test incorrectly expected an empty snapshot to be accepted. The unchanged engine requires at least one supplied transit. That expectation was corrected and the schema now rejects empty input with 422. No waiver, xfail, tolerance expansion or known-issue entry was used.

### Authority, preservation and limits

The computational authority remains the existing Phaladeepika chapter-26 Sastri-1950 Gochara profile and independent source fixture. Source tables, engine vessels, admissible profile/policy defaults, numerical tolerances and evidence files are unchanged. HTTP source-fixture witnesses and direct-engine parity establish transport fidelity; they are not a new classical-edition collation or predictive-accuracy study.

Astronomy, time scales, frames, native substrate, dispatch, readers, kernel lifecycle, dependencies, engine version, facade implementation, test policy, `KNOWN_ISSUES.yml`, golden/oracle data and source-book corpus are untouched. No unrelated dirty paths were present initially. The separate stars-search work, website repositories and deployment state remain outside this delivery. The generated `moira.wiki` mirror is synchronized only through its owning generator for source publication.

Scoped post-correctness inspection found no duplicated numerical doctrine, inferred epoch/ayanamsa, kernel mutation, hidden fallback or composite interpretive score in the new adapters. They call stable public engine functions, construct the existing raw BAV vessel, and project explicit named response fields. Repeated engine snapshot back-references are represented once at profile root without dropping per-edge witnesses or local assessments. This inspection is scoped to the changed export/transport boundary, not a whole-repository lineage certification.

Remaining assumptions: caller positions share one sidereal frame and epoch; raw BAV is unreduced and same-birth. Missing observations remain explicit. Standalone Sayanadi, uncurated named-time Muhurta helpers, a daily sunrise almanac, special Lagnas, Kalachakra, matching, Prashna, chakra systems and dated Gochar forecasts still need their own admission work. This delivery closes the identified curated-export gaps and bounded Gochar transport admission; it does not claim complete Vedic coverage.

### Source-publication follow-up

Before publication, both repository branches were fetched and verified at zero ahead/behind: engine `main` and wiki `master`. The engine change set contained exactly the 26 paths above; the wiki working tree was clean. The generator's pre-publication check identified three prior Gochara core pages awaiting mirroring, alongside the current API-reference edits. These related core pages are included with the current two new pages so that the public documentation accompanies the whole Gochara package.

The seven generated publication paths are `GOCHARA_PHASE1_DOCTRINE.md`, `GOCHARA_BACKEND_STANDARD.md`, `GOCHARA_CONSTITUTIONAL_LEDGER.md`, `GOCHARA_REST_STANDARD.md`, `VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md`, `API_REFERENCE.md` and `REST_API_REFERENCE.md`. Stage the canonical new pages before running the generator, because it discovers sources through `git ls-files`. The publication sequence is generated wiki commit/push first, followed by the engine commit/push carrying canonical sources and the updated gitlink. Actual commit identities belong to Git history and the final publication receipt.

```powershell
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --repo-ref main
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check --repo-ref main
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
git diff --cached --check
```

No numerical source or implementation changes were introduced during publication. The preceding successful test receipts remain the validation for this package; these publication checks verify documentation generation, staged whitespace and scope.
