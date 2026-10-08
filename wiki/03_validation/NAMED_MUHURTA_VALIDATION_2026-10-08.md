# VED-007 named Muhurta execution and validation receipt

**Date:** 8 October 2026. **Runtime:** Moira 6.9.9, project Python 3.14.3.
**Implementation base:** engine `acf5851c3b2369a9dd5630921437dc31c7064b4d`;
published wiki `447768124157bc8df4d8be9347506da2d831b98d`.
**Contract:** [named interval standard](../02_standards/NAMED_MUHURTA_STANDARD.md).
**Authority:** [source decision and executed plan](../06_roadmap/VEDIC_NAMED_MUHURTA_SOURCE_AND_PLAN_2026-10-08.md).

## Result and ownership

Abhijit/Brahma existing-helper integration is complete locally through source
policies, supplied-anchor and civil-date calculation, public exports, facade
and typed REST. VED-007 is `BOUNDED_ADMISSION`: its separately listed new
names remain source-research additions. VED-021/022 follow-through is complete
for these two windows. This implementation is included in the containing
authorized engine/wiki source-publication package. The baseline Sayanadi
package was published before it began; release and deployment remain separate.

| Files | Change |
| --- | --- |
| `moira/named_muhurta.py` | Canonical policy/anchor/interval/result/day vessels, independent source and compatibility readings, exact affine expressions, endpoint bounds, civil-date ownership, bounded solar discovery/refinement and reader/resource handling. |
| `moira/muhurta.py` | Corrected existing predicate attribution and scope; boolean arithmetic retained. |
| Root, `facade`, `vedic`, `_facade_vedic` | Seven owning exports with shared identity and two facade methods. |
| `moira_server/models/named_muhurta.py`, serializer, service and Muhurta router | Strict direct/day admission, canonical projection, startup reader binding and two typed routes. Existing Muhurta exception envelopes reused. |
| Named-Muhurta unit/server/integration tests and analytic support | Source formulas, boundaries, policy choice, hostile inputs, controlled event failures, civil/reader behavior and real DE441/HTTP evidence. Vedic curation test includes the new family. |
| Canonical source/standard/receipt/register/REST reference and generated wiki | Current source boundaries, completed contract and remaining additions. |

No astronomical or native substrate, dependency, version, golden fixture,
tolerance, test harness or known-issue policy was modified. Website/Urania,
release/deployment and unrelated state-repository changes are outside scope.

## Source and numerical evidence

The reviewed Chintamani cover and Vivaha 52-54 identify the edition,
eighth-daylight-part rule and Wednesday exclusion. Arunadatta's digital
Sanskrit commentary supports the fixed-ghati reading; the base verse and
Hemadri commentary do not independently provide that entire numerical rule.
The local corpus witness identifies broad periods but supplies no exact
formula or secure author title leaf. Source presence is not treated as proof
of uninspected claims.

Eight independent rational cases cross both Brahma readings with day/night
lengths 12/12, 15/9, 8/16 and 1/23 hours. Seven weekdays verify the selected
exclusion separately from unchanged geometry. Exact binary64 endpoints and
adjacent representable instants test half-open ownership. The Raman
transcription's 06:10-18:45 discrepancy is retained as a counterexample:
independent arithmetic gives midpoint 12:27:30 and daylight-muhurta length
50m20s, checked within 0.1 milliseconds for JD rounding. Its erroneous
12:25 expectation is not admitted as an oracle.

Analytic crossings deliberately offset coarse witnesses by 0.2 seconds.
Tests verify root brackets, endpoint uncertainty, missing/multiple roots,
nonfinite refinement, partially available pairs, midnight ownership,
preceding-date Brahma, invalid/skipped dates and reader restoration on
success/resource/coverage errors. The fixture controls UTC/UT1 mapping;
these are composition invariants, not independent astronomical observations.

## Real-resource and REST evidence

The executed resource is discovered `de441.bsp`, identity DE441, using the
existing native-backed project installation. The test harness recorded
**23 planetary resource uses, 23 run, zero skip/failure**, across the new
integration slice and existing regression routes.

Four interval cases cover 22 September 2026 at the Rashtriya/PAC reference
location, 21 June at Delhi, and the New York DST transitions on 8 March and
1 November 2026. The three sunrise definitions and both Brahma readings are
exercised. Returned anchors meet the original 0.1-second numerical bracket
width, and endpoints equal independently assembled rational expressions on
those anchors. Tromso's summer/winter solstice cases preserve missing sunrise
without fabricated windows.

The reused PAC 2026-27, 31 Bhadra sunrise witness (05:49 IST, latitude
23 degrees 11 minutes north, longitude 82.5 east) passes its unchanged
60-second published-minute gate. This is institutional **sunrise component**
evidence. It is not a published paired Abhijit/Brahma interval oracle,
external software parity or predictive validation.

Explicit-reader and active-context entrypoints agree. Both actual server
startup paths (automatically discovered and explicitly configured kernel)
return exact canonical facade/HTTP JSON parity. Composition leaves borrowed
readers open; the tests close only the engines/readers they own. They do not
claim that application shutdown gained new reader-lifecycle behavior.

Loopback cases cover every Brahma/weekday policy combination, typed partial
and unavailable responses, 27 hostile request forms, unchanged 422/503
resource envelopes, request IDs and registered OpenAPI response/profile
identities. Invalid requests reach no analytic astronomy calls.

## Executed commands and outcome

All pytest commands used the project `.venv`, with `MOIRA_TEST_MODE=1`,
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_STRICT_KNOWN_ISSUES=1` and
`-m "not external_network" -q --tb=short`. Network was denied except marked
loopback. Existing known-issue exclusions were not added or changed.

| Test selection | Result | XML |
| --- | --- | --- |
| `tests/unit/test_named_muhurta.py tests/unit/test_vedic_surface_completeness.py tests/server/test_server_named_muhurta.py` | 111 passed; zero failures/errors/skips | `contract.xml` |
| `tests/integration/test_named_muhurta_ephemeris.py tests/unit/test_muhurta.py tests/unit/test_daily_panchanga.py tests/server/test_server_muhurta_routes.py` | 113 passed; zero failures/errors/skips | `ephemeris-regression.xml` |
| Pre-edit three-file existing Muhurta/Panchanga slice | 103 passed; contained within the later regression selection, not counted twice | `baseline.xml` |

**224 distinct passing tests** in the two completed acceptance selections.
The private XML, scans and source manifests are under
`C:/dev/outputs/ved007-named-muhurta-2026-10-08/`.
An initial unit collection used the wrong `OutOfRangeError` constructor;
the fixture was corrected to the existing two-argument contract and the
entire contract selection passed. No threshold was changed to absorb a
failure. Exploratory reader smoke calls were corrected to use the existing
`SpkReader(kernel_path)`/active-context API; no fallback discovery was added.

Mechanical checks also passed:

- `scripts/check_doc_consistency.py`;
- `scripts/sync_rest_api_reference.py` and `--check`: 486 registered paths
  and operations, including the two new POST routes;
- `scripts/sync_git_wiki.py` and `--check`;
- root and nested-wiki `git diff --check`;
- scoped Ruff for all fifteen changed/new Python files, compared with their
  `HEAD` sources: zero new diagnostics; existing root 60 E402 and facade
  five F811 findings remain unchanged;
- Python 3.10 grammar parsing of all fifteen files and runtime resolution
  of the two new facade methods' public type annotations.

The grammar check is not execution on a Python 3.10 interpreter. No full
repository suite or native rebuild was needed for this composition package.
At the local validation checkpoint, new canonical pages were exposed to the
wiki generator with intent-to-add. The later authorized publication commits
the generated wiki first, then the engine with its matching wiki gitlink.

## Limits and remaining work

The endpoint bracket is numerical evidence under the selected solar model,
not observational accuracy. No terrain, elevation or atmospheric uncertainty
model is admitted. Fixed-ghati UT1 intervals and civil clock displays have
separate semantics. The three-date discovery limit can legitimately leave
high-latitude windows unavailable. No whole-supported-epoch-range precision
claim follows from four dated cases.

Godhuli, Vijaya, Amrita, Ravi Yoga and Sarvarthasiddhi, purpose-specific
cancellations, integration into generic scoring/search and predictive
efficacy are not part of this admitted two-window contract. The standard and
register keep those scopes explicit; their absence does not leave these
two source-selected interval products partially implemented.
