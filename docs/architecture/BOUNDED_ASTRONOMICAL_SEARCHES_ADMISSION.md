# Bounded astronomical searches

This ledger records Section 4 decisions under the server route admission
checklist. The serving reader owns astronomical state. Numerical policies
continue to belong to the engine reducers.

| Product | Admission decision and proof |
|---|---|
| Exact-epoch eclipse geometry | `admit_now`. The native eclipse model in `EclipseCalculator.calculate_jd` owns instantaneous classification and geometry. Compare eclipse and ordinary epochs against the same DE441 reader. |
| Natal eclipse contacts | `admit_after_minor_engine_work`. The contact reducer already owns angular matching. Require a bounded native candidate scan with its existing endpoint padding. Keep coverage and unresolved refinement distinct from a completed empty search. |
| Multi-body void-of-course | `admit_after_minor_engine_work`. The batch reducer owns sign transits and traditional/modern major aspects. Correct its initial window's overlap test and verify ordered per-mover results, local failures, and the matched lunar doctrine. |
| Paran selectors | `admit_after_minor_engine_work`. The engine classifies crossings before policy selection. Add pair and axis restrictions to the same policy stage. Verify existing defaults and request orientation against identical crossing inventories. |
| Location-free great conjunctions | `admit_after_minor_engine_work`. The fixed Jupiter–Saturn product belongs to `great_conjunctions`. DE441 reproduced the missing start-boundary root at UT1 JD 2459205.264318665. Use an opt-in engine bracket beyond both endpoints and retain only in-range roots. Verify the 2020 conjunction and a clustered historical sequence against mundane and apparent-longitude witnesses. |
| Named-star and lunar visibility | `admit_after_minor_engine_work`. Distinguish fixed-star arcus-visionis dusk and dawn policies from generic visibility. Admit the engine's Yallop lunar evening-first and morning-last variants. Preserve usable and unavailable observation evidence alongside bounded results. |
| Stellar visibility catalogue | `admit_after_minor_engine_work`. Admit only an explicit bounded subset with the same criteria, source and observation vocabulary as the single-target route. Preserve catalogue rejection reasons and a per-request star-day budget. |
| General geocentric conjunction receipt | `admit_after_minor_engine_work`. A three-day endpoint sign gate missed two crossings inside one cell. Add bounded interval isolation and existence and uniqueness witnesses for the apparent roots. Preserve unresolved intervals and distinguish coverage and work failures. |

### Conjunction repair evaluation

`admit_after_minor_engine_work` for a source-bounded apparent-geocentric
receipt. The serving planetary reader, its Type 2 records, the existing
1900–2100 clock/frame enclosure, and the canonical apparent-longitude
reducer are the authorities. A local DE441 probe enclosed the December 2020
Jupiter–Saturn root with the existing interval isolator. The engine must
retain every possible crossing or report an unresolved interval. It must
prove existence and uniqueness before polishing a representative UT1 epoch.
The numerical compatibility search retains its historic date domain.
Transport admission follows synthetic clustered-root, endpoint, coverage,
and exact-reader checks.

## Local disposition

All eight products listed above are admitted in the local REST
implementation. The [REST reference](../../wiki/02_services/REST_API_REFERENCE.md#bounded-astronomical-searches)
records their limits and outcome types. Kernel tests use the serving DE441
reader. The eclipse range uses the existing native candidate scan and Python
refinement. The explicitly selected stellar criteria use the sovereign
catalogue and Python scans that retain observation receipts.

The sampled conjunction reducer now looks for a turning point inside a
same-sign cell, brackets against observed apparent signs, and restarts at the
represented root plus `1e-6` days (0.0864 seconds). The controlled separation
`(t - 100.75) * (t - 101.25)` over `[100, 103]` now returns both roots.
This path retains the sampled search's historical date domain.

The verified reducer isolates zeroes of periodic apparent geocentric
longitude difference directly, using Type 2 record enclosures and the
1900–2100 clock and frame model. A crossing requires strict opposite
endpoint signs and a one-sign rate across its proof bracket. This path has
no post-event advance. It carries unresolved cells for possible tangencies,
unproved multiplicity, and ambiguous boundary ownership. The 0.25-second
isolation tolerance controls subdivision. The per-root witness carries the
actual bracket. Inclusive ownership applies to the represented UT1 epoch.
The engine admits up to 366 days subject to work limits. The synchronous
REST route admits up to 32 days, with boundary witnesses requiring coverage
at both ends. A completed empty result carries zero proved roots and zero
unresolved intervals. Source hashes identify the exercised ephemeris records'
kernel files without a filesystem location.

The clustered synthetic cases resolve crossings in one coarse cell at both
12-hour and two-second spacings. A 360-degree lift preserves their roots,
an opposition is excluded, and a tangency remains unresolved. The December
2020 Jupiter–Saturn root is represented at UT1 JD `2459205.264318665` using
DE441 (SHA-256
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`).
The engine preserves that root at either inclusive endpoint and the REST
test checks its signed and rate witnesses against the same serving reader.

## Verification

Use the project Python 3.14.8 environment with `MOIRA_TEST_MODE=1`,
`MOIRA_NO_DOWNLOAD=1`, and `MOIRA_STRICT_KNOWN_ISSUES=1`. The contract suite
passed 101 tests with 40 DE441 resource receipts. The eclipse, batch,
visibility, and fixed-pair engine suite passed 86 tests with 34 DE441
resource receipts. Both runs completed without skips.

```powershell
.\.venv\Scripts\python.exe -m pytest -m 'not external_network' tests/server/test_server_bounded_astronomical_searches.py tests/server/test_server_paran_packet.py tests/server/test_server_phenomena_routes.py tests/server/test_server_heliacal_eclipse_phase_routes.py tests/server/test_error_mapping.py tests/unit/test_phenomena_regressions.py tests/unit/test_batch.py::test_void_periods_all_planets_excludes_a_first_window_starting_at_range_end
.\.venv\Scripts\python.exe -m pytest -m 'not external_network' tests/unit/test_eclipse_hits.py tests/unit/test_batch.py tests/unit/test_heliacal_standard_kinds.py tests/unit/test_cycles.py::TestGreatConjunctions
.\.venv\Scripts\python.exe -m pytest -m 'not external_network' tests/unit/test_geocentric_conjunction_search.py tests/server/test_server_bounded_astronomical_searches.py
.\.venv\Scripts\python.exe tests/unit/test_docstring_governance.py moira/batch.py moira/cycles.py moira/eclipse.py moira/heliacal.py moira/parans.py moira/phenomena.py moira/star_types.py moira/stars.py
.\.venv\Scripts\python.exe scripts/check_rest_capability_map.py
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
git diff --check
```
