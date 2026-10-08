# VED-007 five-name completion receipt

**Date:** 8 October 2026. **Implementation base:** engine `12ed2a1`, generated
wiki `424799f`, version 6.9.9. **State:** implemented and validated; included
in the containing authorized engine/wiki source-publication package. Runtime
release and deployment remain separate.

VED-007 now has all seven named families: the published Abhijit/Brahma
contract and the new Godhuli, Vijaya, selected Amrita, Ravi Yoga and
Sarvarthasiddhi products. Completion refers to the source-selected timing
and combination-presence contracts in the
[standard](../02_standards/NAMED_MUHURTA_STANDARD.md), not universal
auspiciousness, every historical variant, generic scoring integration or
activity-specific elections. VED-008–011 remain separate packages.

## Sources and implementation

The [source packet](../06_roadmap/VEDIC_NAMED_MUHURTA_FIVE_SOURCE_AND_PLAN_2026-10-08.md)
records inspected primary scan leaves, source disagreements, the digital
Muhurta Sadhana witness's unidentified print edition, private PDF hashes,
and the limitations of the local-library search. No scanned text is
redistributed. The governing rules were selected before implementation.

| Changed surface | Ownership and behavior |
| --- | --- |
| `moira/special_muhurta.py` | Named policy, pure solar-anchor composition, pure three-yoga classification, complete seven-family date composition, strict vessels, source evidence, partial states, root uncertainty and uncertainty-aware yoga membership. |
| `moira/__init__.py`, `moira/facade.py`, `moira/vedic.py`, `moira/_facade_vedic.py` | Eleven shared owning exports and three facade methods. Dated composition borrows the engine reader. |
| `moira_server/models/special_muhurta.py`, `serializers/special_muhurta.py`, `services/special_muhurta.py`, `routers/muhurta.py` | Three typed endpoints, strict preflight, canonical projection and existing coverage/resource error envelopes. No server-side interval arithmetic. |
| `tests/special_muhurta_support.py`, unit/server/integration suites, Vedic surface inventory | Independent analytic sky, primary-name tables, numerical/adversarial and real DE441 coverage. |
| Owning standard, source plan, register and REST reference | All five former research entries reconciled; source choice, completion and publication kept distinct. `moira.wiki` is generator-owned. |

No native/astronomical substrate, dependency, package version, existing
Abhijit/Brahma default, generic Muhurta score/search, website or Urania change
was made. The state repository's unrelated edits were preserved.

## Commands and results

All execution used `C:/dev/moira/.venv/Scripts/python.exe` (Python 3.14.3),
with `MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`. `tests/KNOWN_ISSUES.yml` is empty. Tests used
the harness's default network deny, with marked loopback only for TestClient.

Final combined acceptance command, run in `C:/dev/moira`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_special_muhurta.py tests/unit/test_vedic_surface_completeness.py tests/unit/test_named_muhurta.py tests/unit/test_daily_panchanga.py tests/unit/test_muhurta.py tests/server/test_server_special_muhurta.py tests/server/test_server_named_muhurta.py tests/server/test_server_muhurta_routes.py tests/integration/test_special_muhurta_ephemeris.py tests/integration/test_named_muhurta_ephemeris.py -q --junitxml=C:/dev/outputs/ved007-five-2026-10-08/acceptance.xml
```

**383 passed, 0 failed, 0 errors, 0 skipped**, in 136.398 seconds. The harness
recorded **33 planetary-resource uses: 33 run, 0 skipped, 0 failures**, one
content probe, all DE441. The local planetary kernel resolved to
`C:/Users/nilad/.moira/kernels/de441.bsp`; result identity was
`DE-0441LE-0441`. Python doctrine/composition used the existing compiled
CPython 3.14 Windows native astronomical substrate; no speculative native
mirror was introduced.

| Selected test family | Passing tests |
| --- | ---: |
| New special-Muhurta unit | 104 |
| New special-Muhurta REST | 44 |
| New special-Muhurta real integration | 10 |
| Curated Vedic surface completeness | 17 |
| Existing named-Muhurta unit / REST / real integration | 57 / 38 / 10 |
| Daily Panchanga unit | 56 |
| Existing Muhurta unit / REST | 37 / 10 |

The initial 95-test Abhijit/Brahma baseline passed before edits. Intermediate
checks found an incorrect exception-construction test fixture, repaired
before the final clean run. A missing-next-sunrise case also exposed overly
restrictive evening selection; the implementation now preserves the first
descending crossing after the current sunrise and has a dedicated regression.

Static verification: all **14 changed/new Python files** pass Python 3.10
grammar parsing. This is not execution under Python 3.10. Ruff reports zero
new findings relative to `HEAD`; existing root 60 E402 and facade five F811
findings remain unchanged. Baseline comparison ignores moved line numbers
inside otherwise identical diagnostic messages. The other twelve files pass
the selected Ruff invocation outright. Private `static-validation.json`
records per-file results.

Documentation checks use:

```powershell
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
```

The REST inventory has **489 registered paths/operations**, including the
three additions. The generated wiki is refreshed only through
`scripts/sync_git_wiki.py`, including intent-to-add registration of the two
new canonical documentation files. Documentation consistency, REST inventory, generated-wiki consistency and
parent/nested whitespace checks all passed. Publication requires its own
receipt.

## Evidence classes and practical limits

**Source authority:** independently name-transcribed weekday fixtures test
all 189 weekday/star combinations for each Amrita profile and Sarvarthasiddhi;
Ravi covers all 729 Sun/Moon star pairs and the inclusive cyclic count.
Godhuli and Vijaya are checked against rational ±1/120 day and 10/15–11/15
daylight constructions, including unequal days and all weekdays. These prove
the selected rules, not predictive effects.

**Geometric/numerical invariants:** binary64 star boundaries and both adjacent
floats; rational single-round interval endpoints; half-open membership;
Sun-only, Moon and simultaneous/nearby crossings; zodiac wrap; whole-day
unchanged states; explicit unresolved bands; missing/ambiguous solar events;
non-finite/backward phase failure; current evening preserved when next sunrise
is absent; and reader restoration through failure. Tolerance bounds the root
bracket to 0.1 seconds by default, not atmospheric or ephemeris uncertainty.

**Real astronomical composition:** Delhi 8/10 October 2026, the PAC reference
site 22 September 2026, New York DST dates 8 March/1 November 2026, Tromso
summer/winter solstices, and the equatorial explicit/active-reader fixture
2 January 2000. Tests exercise both Godhuli horizon models, both Amrita
profiles, true Lahiri sidereal Sun/Moon, geometric centre-altitude residual
brackets, UT1 arithmetic and civil displays. Forty-eight independent time
probes per available real day plus each returned yoga cell midpoint check
presence against instantaneous engine longitudes outside uncertainty bands.

**Primary published component:** the unchanged Rashtriya Panchang gate checks
the 22 September 2026 reference sunrise within 60 seconds of the published
05:49 IST minute. It supplies no published paired five-window oracle. No
cross-engine agreement or universal observational accuracy is claimed.

**Transport/regression:** exact canonical HTTP projection, preflight rejection
before astronomy, valid empty results versus unavailability, request IDs,
resource/coverage envelopes, both startup reader configurations and reader
closure ownership. Existing named, daily and Muhurta contracts remain tested.
The full repository suite was not run and is not claimed.

**Post-correctness ownership audit:** ontology is source-selected intervals
and star combinations; derivation comes from the named texts and first-order
interval arithmetic; helper/branch structure follows solar anchors and
forward phase brackets; alternatives and missing-data behavior are explicit
policy; source tables, rational fixtures and root invariants carry the proof.
No external-engine implementation or parity result was used to define the
calculation. The new Python path delegates to the existing native substrate.

Private receipts remain under `C:/dev/outputs/ved007-five-2026-10-08/`.


## Authorized source publication

The user authorized committing and pushing this completed package. The
containing generated-wiki commit carries six scoped pages; the parent engine
commit carries the implementation, tests, canonical documentation and matching
wiki gitlink. Publish the generated wiki first, then the parent engine.

The recorded 383 passing tests and 33 successful DE441 resource uses remain
the implementation acceptance evidence. This publication step updates status
and scope prose only; it does not change arithmetic or test thresholds.
Documentation consistency, generated REST inventory, wiki synchronization,
exact staged manifests and whitespace are the publication checks. Exact
resulting local/remote commit identities are recorded in the publication
handoff after both pushes. No release/tag/deployment or website adoption is
included. VED-008 is the next recommended package, not newly implemented work.
