# VED-011 purpose elections: implementation and validation

**Status:** Selected four-area implementation and original local acceptance
completed on 11 October 2026. The subsequent adversarial review identified
four defects; all four repairs and their completed fresh verification are
recorded in section 6.
The P0–P6 evidence below records the original checkpoint. Section 7 records
the subsequent authorized source-publication package; release and deployment
remain separate actions.

**Baseline:** engine `c0c1d739c9cdf52910ff2f64aea6ac0ad88e347f`, generated wiki
`7ad434a903555679a2393afd7487138bb9d3634c`, version 6.9.9.
The governing [implementation plan](../06_roadmap/VEDIC_PURPOSE_ELECTION_IMPLEMENTATION_PLAN_2026-10-11.md),
[source research](../06_roadmap/VEDIC_PURPOSE_ELECTION_SOURCE_RESEARCH_2026-10-11.md)
and [admission standard](../02_doctrine/standards/PURPOSE_ELECTION_STANDARD.md)
define the finite scope. This is evidence for those selected interpretations,
not all prescriptions of the cited books or predictive efficacy.

## 1. Delivered source and public contracts

| Area | Selected runtime profile and scope | Public surfaces |
| --- | --- | --- |
| Residential Vastu | `mc_maniprabha_1948_residential.v1`: foundation, first entry, return entry, old-house entry and qualified extraordinary entry | `muhurta_vastu`, facade/curated exports; `/v1/muhurta/vastu/catalogue`, `/direct`, `/datetime`, `/windows` |
| Commerce | `mc_avasthi_2004_commerce.v1`: purchase, sale, first opening for trade; explicit buyer/seller/operator | `muhurta_business`, facade/curated exports; `/v1/muhurta/business/catalogue`, `/direct`, `/datetime`, `/windows`, `/compare` |
| Ordinary land travel | `mc_maniprabha_1948_ordinary_land.v1`: named departure, direction, leg and optional personal/context layer | `muhurta_travel`, facade/curated exports; `/v1/muhurta/travel/catalogue`, `/direct`, `/datetime`, `/windows` |
| KP travel components | `kp_1917_weekday_direction_release.v1` and `kp_1917_travel_modular_tests.v1`; explicitly labelled components | Same travel surfaces; no claim to a full KP travel profile |
| Additional ordinary marriage | `vv_vasantalakshmi_1935_marriage_ordinary.v1` and `kp_1917_marriage_ordinary.v1`; separate rule/remedy manifests and personal policies | Existing marriage catalogue/direct/datetime/windows surfaces and strict typed additional evidence |

The existing MC marriage defaults, personal assessment and Godhuli remain
available. The generic activity guidance now points to the named housing and
travel APIs; generic sampled-search behavior is unchanged.

### Research decisions closed at the admitted scope

| Decision | Implemented disposition |
| --- | --- |
| D01 | MC48 owns housing/travel; MC04 remains the commerce and established marriage edition. Source identities are not silently merged. |
| D02 | Unequal Abhijit astronomical adapter, 276°40′–280°53′20″, supplies the 28-star partition. Vrisha28 and Kalasha27 stay distinct. |
| D03 | Finite source manifests close MC48 12–13 and ordinary travel 11. The 11.112 imports enumerate individual MC04 rule families; no complete marriage verdict or remedy graph is imported. |
| D04 | Frozen family contexts own resident/traveller/actor, natal frame, facing/direction, anchor and exceptional facts. Missing evidence remains unknown. |
| D05 | Conflicting KP travel direction/star tables are excluded from the two admitted components. A complete KP travel profile still requires collation of those printed conflicts. |
| D06 | Each rule declares fixed/proportional ghati, ordinal basis and edge ownership. The weekday-direction release is strictly beyond the printed fixed-ghati count; travel stop context counts actual declared nights. |
| D07 | Purchase/sale/operator roles are separate. Quantified placement clauses and the finite sale tithi composition are explicit. Buyer/seller comparison retains both instant assessments and their disjoint-set conflict without averaging scores. |
| D08 | VV owns its calendar precedence, whole-star Vedha, two actual Moon traversals, bhava geometry, hora/Shadvarga, event history and protected full-Jamitra. Finite modern astronomical adapters are named. |
| D09 | KP owns its graded tithis, specific temporal permissions, angular combustion, waiting periods, general timing imports, calendar ends and finite remedy targets. |
| D10 | Raman remains outside the supported catalogue pending an identified printed edition. This does not block the selected VV/KP deliveries. |

The standard records the relevant source conflicts and computational
compositions. Machine catalogues retain source hashes, rule contracts,
transition dependencies, required inputs, missing-data behavior, remedy
targets, fixture pointers and exclusions. Independent manual transcriptions
live in `tests/fixtures/vastu_election_sources.json`,
`business_election_sources.json`, `travel_election_sources.json` and
`marriage_additional_tradition_sources.json`; expected tables are not generated
by importing their implementation constants.

## 2. Implementation ownership and compatibility

The new `muhurta_election` vessels and private `_muhurta_election_*` modules
share evidence assembly and bounded dated execution. Each family's source
tables, evaluator and remedies remain separate. Demand-driven dependencies
avoid calendar, Lagna, history or visibility searches when the selected rule
does not use them. Exact memo ownership, reader borrowing, work metering and
unresolved numerical bands retain the existing contracts.

VV/KP add private geometry, historical evidence and policy evaluators under
`_muhurta_marriage_*`. Additional history extends the established star-history
vessel. VV adds raw midheaven evidence. REST unions retain these raw vessels
and reject foreign-profile evidence, forged completion fields and incompatible
remedies; serializers do not recompute doctrine. No native implementation or
planetary/event owner is changed.

Three complete MC responses were compared against the published reuse
checkpoint with **no response normalization**. Requests and HTTP status also
match. All response values, sources, certificates and counters are identical:

| Response | SHA-256 of canonical complete response JSON |
| --- | --- |
| Six-hour windows | `4f9f3f7ed629ff3e6fdef1fd356597d6854db2a0ecb3f48fa10a2d67a05f6c24` |
| Personal direct assessment | `10c09ebfb15c6f8e58ce1951629f8e47513a9efbf81d378c6bb90eba07d1198c` |
| Polar snapshot | `dd0e2960f5d4f7a338c502cc29029c33e1b5c491412ca1f135fa025edf1e77e9` |

This is regression equivalence, not independent classical or astronomical
authority validation. Whole raw receipt hashes additionally preserve their
outer execution metadata.

## 3. Executed validation and limits of the evidence

All execution uses `C:\dev\moira\.venv\Scripts\python.exe` (Python 3.14.3),
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1` and strict known-issue expiry.
Real astronomical tests discover DE441 through the owner and use the actual
serving reader; HTTP uses the admitted loopback harness. No new failure is
hidden by a skip, xfail, known-issue entry or widened tolerance.

| Acceptance slice | Completed result |
| --- | --- |
| Source, boundary, adversarial, reuse, engine and strict REST slice | 422 passed in 135.30 s |
| Housing foundation HTTP instant and six-hour window | 1 passed in 62.51 s |
| First-entry three-hour window, polar missing solar evidence and two real budget-failure cases | 3 passed in 120.25 s |
| Commerce unit/REST and real two-day purchase / three-hour opening windows | 13 passed in 47.30 s |
| KP travel component unit/REST and real release/modular windows | 13 passed in 49.69 s |
| VV bhava, solar/lunar shadow contacts, both additional histories, four real lunar/solar calendar pairs | 9 passed in 128.24 s |
| Signed apparent declination enclosure against native point directions | 1 passed in 5.60 s |
| Public export/doctrine, legacy guidance and final VV/KP unit/REST checks | 103 passed in 49.38 s |
| Documentation ownership, publication line-ending semantics and class contracts | 15 passed in 6.40 s |
| Final VV HTTP instant/direct/30-minute window | 1 passed in 1,093.09 s |
| Final KP HTTP instant/direct/30-minute window | 1 passed in 1,230.68 s |
| Final MC marriage window/polar and MC travel instant/30-minute window | 3 passed in 1,529.51 s |

**501 distinct test cases passed, zero failures and zero skips**
across these retained acceptance slices. Counts overlap across slices; they
must not be added as distinct cases.
`acceptance-index.json` deduplicates node identities and records exact XML and
raw HTTP hashes. Expensive request durations include concurrent validation
load and are not isolated performance comparisons.

### Source and boundary coverage

Independent finite-domain assertions cover the distinct 27/28-star chakras,
direction counts and ghati clocks, buyer/seller quantifiers, VV versus KP
tables, two-Moon-traversal clearance, retained cancellation targets and
protected Jamitra. Classical unequal D30 and self-counted D12 are checked
across all twelve signs. KP's solar Navamsa wait retains its entry uncertainty
and one-day boundary. Eclipse raw witnesses reject fabricated state changes;
VV's seven-day continuation retains contact uncertainty.

Real windows verify every returned stable cell and uncertain transition band,
not just one favorable sample. HTTP payloads are compared to the captured
engine/facade result. Hostile tests include malformed/foreign policies,
missing context, stale evidence, boolean/non-finite/coercion inputs, missing
resources, polar solar unavailability, bounded work/output failures and reader
lifecycle. Existing memo tests cover exact binary64 keys, eviction,
cross-request isolation and unchanged recomputation.

### Numerical evidence boundary

Bhava/midheaven and signed declination enclosures contain independently
evaluated native point results at the specified epochs, including point and
one-second enclosing intervals. Solar 8 April 2024 and umbral lunar
14 March 2025 cases resolve ordered start/end contacts and retain raw shadow
vectors. Five event-centered epochs with point and ±1-second intervals test
containment; the extra-history cases check bounded extent, caching and strict
transport. These are matching-model numerical/invariant checks. They do not
claim NASA timing agreement or formal platform verification.

The eclipse adapter explicitly uses global occurrence, a spherical Earth for
solar contacts and the existing 1.01 Earth-shadow convention for lunar umbral
contacts. Observer visibility and penumbral-only lunar events are outside the
selected interpretation. Root completeness remains conditional on the named
binary64 arithmetic model; unavailable bands never become favorable cells.

## 4. Performance and operational contract

`exact-scope-performance.json` measures a fresh request context and exact
same-context repetition with Python allocation tracing. All four measured
evidence payloads are identical on repetition, with **zero additional kernel
reads**. Memo sizes/hits/misses, inferred evictions, counters, source identity
and dependency sets are retained. No cross-request result cache was added.

| Measured evidence build | Cold context / warm same context | Peak traced Python allocation |
| --- | --- | --- |
| Housing foundation dependency set | 11.147 s / 0.000511 s | 22,449,271 bytes |
| Purchase dependency set | 0.937 s / 0.000058 s | 7,247,392 bytes |
| KP weekday travel component | 8.799 s / 0.000278 s | 14,288,998 bytes |
| Shared marriage positions and Lagna only | 0.952 s / 0.000149 s | 7,247,200 bytes |

These are evidence-build measurements, not full HTTP latency or whole-marriage
benchmarks. Allocation tracing starts after opening the kernel and excludes
native buffers. Separate process observations include the runtime, kernel and
test harness; they are not equivalent to retained request memory.

KP's first full attempt exhausted the unchanged two-million-reader-call
budget while searching Venus motion across the entire long history. The repair
searches motion only in the certified 8–10-degree orb domain where its branch
can affect combustion, including orb-root uncertainty bands. It does not
raise reader/evaluation limits, shorten required history or coarsen epochs.

The final KP instant/window use 1,647,011 / 1,666,797 reader calls; its window
contains 12 certified stable cells. VV uses 1,520,394 / 1,568,162 reader calls
and returns 14 certified stable cells. Both retain complete event certificates
under the declared model and fit within the unchanged work/output budgets.

Default limits remain seven requested days, 300,000 evaluations, 2,000,000
reader calls, 2,048 cells, 8,192 transitions, 8 MB serialized output and the
existing bounded historical/root limits. These maxima are admission bounds,
not promises every permitted request finishes within them. The VV/KP real
tests explicitly allow 4,096 historical days while retaining default reader,
evaluation and output limits. Tested complete windows are six hours for
housing foundation/established MC marriage, three hours for first-entry and
opening, two days for purchase, four hours for the KP weekday component,
36 hours for its modular component and 30 minutes for MC travel/VV/KP
marriage. Long searches remain minute-scale; budget errors are explicit.

## 5. Reproducibility, documentation and publication boundary

Local raw evidence is retained in
`C:\dev\outputs\ved011-four-area-research-2026-10-11\implementation`.
`acceptance-index.json`, `marriage-final-exact-equivalence.json`,
`exact-scope-performance.json`, `static-audit.json`, `publication-checks.json`
and the individual XML/HTTP files preserve the actual observations.

The exact test node names are in the XML files. Representative commands:

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_muhurta_marriage_traditions_ephemeris.py -q -o addopts=
.\.venv\Scripts\python.exe -m pytest tests/integration/test_muhurta_marriage_ephemeris.py tests/integration/test_muhurta_purpose_elections_ephemeris.py -q -o addopts=
.\.venv\Scripts\python.exe -m pytest tests/integration/test_marriage_tradition_geometry.py -q -o addopts=
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe scripts/generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/build_website_docs_bundle.py --check
```

The owning wiki generator is invoked through the pre-publication helper
`verify_and_sync_docs.py`, which includes untracked canonical Markdown without
staging or altering the Git index. It runs both generation and `--check`.
Once the canonical additions are tracked, ordinary `sync_git_wiki.py --check`
discovers the same files. Generated files are never hand-edited.

Release-facing doc consistency, release identity, Hellenistic inventory, REST
inventory, tagged website documentation manifest and generated wiki checks
all pass. The CI source lint selection `F401,F821,F822,F823` also passes.

All 62 changed Python files parse under the Python 3.10 grammar; this is not a
Python 3.10 runtime test. Scoped Ruff has 68 pre-existing findings and zero new
findings after line relocation is accounted for. The existing root/facade and
router debt is not represented as a green repository-wide Ruff gate.

Remaining extensions have explicit boundaries: door installation and Vastu
design/site rules; lending/borrowing and other commercial acts; military,
marine and further travel traditions; a full conflict-resolved KP travel
profile; standalone BS/Raman/PVR marriage profiles, regional ritual variants,
full natal compatibility and whole-ceremony duration. None is silently exposed
as a supported completed profile. Website/Urania adoption is separate work.

The implementation checkpoint also preserves the preceding research/plan
documents. Version 6.9.9 is unchanged. The subsequent source-publication
authorization and wiki-first sequence are recorded in section 7.

## 6. Focused adversarial repair checkpoint

The review receipts remain unchanged in
`C:\dev\outputs\ved011-review-2026-10-11`. Fresh repair evidence is stored
separately in `C:\dev\outputs\ved011-repairs-2026-10-11`.

| Review finding | Repair and regression contract |
| --- | --- |
| R1: KP tithi/nakshatra Thyajyam could disappear when its parent ended | Union fixed-clock exclusions from consecutive preceding parents. Retain context throughout the current parent, expose carryover edges to window partitioning, preserve bright-parent scope and uncertainty, and report incomplete history explicitly. |
| R2: Purpose APIs accepted KP angular apparition evidence under SS rules | Canonical purpose admission rejects incompatible geometry for both Jupiter and Venus across housing, commerce and travel. The owning KP marriage profile still admits it. REST returns 422 through the same engine validation. |
| R3: Degenerate raw eclipse vectors could raise an unhandled arithmetic error | Admit only finite derived distances, separated spheres and finite cone signals. Engine raises `ValueError`; REST returns a typed validation error instead of 500. Ordinary solar/lunar contact arithmetic is unchanged. |
| R4: Insufficient VV supplemental-history budgets failed after expensive work | Share the exact profile/range calculation between preflight and history assembly. Reject insufficient history and impossible 90-day vessel extents before borrowing a reader; REST preserves budget kind, count and stage. |

| Fresh repair acceptance slice | Result |
| --- | --- |
| Carryover/uncertainty, profile geometry, degenerate/overflowed shadow input and preflight engine/REST regressions | 42 passed in 13.540 s |
| Existing marriage, housing, commerce, travel and dated engine/REST regressions | 299 passed in 146.159 s |
| Real solar/lunar shadow enclosure and directed contact cases | 2 passed in 7.295 s |
| Valid VV/KP additional-history assembly and strict transport | 2 passed in 50.854 s |
| Public exports/doctrine, OpenAPI discovery and publication-bundle contracts | 24 passed in 22.541 s |
| Two missed real phase intervals and complete KP HTTP carryover window/direct route | 2 passed in 809.529 s |

**371 distinct cases passed, zero failures and zero skips.** The initial
40-case repair run is superseded by the 42-case run after two additional
derived-signal overflow cases were added; it is not counted twice.

The real KP window covers 20 February 2026, 09:07–10:07 UTC, at28.6°N/77.2°E
with the `Asia/Kolkata` civil zone. It returns13 certified stable cells and14
transition bands, including the previously omitted carryover edges. A fresh
reader context recomputes phase evidence at10% and90% of every cell and
confirms the retained Thyajyam state. Root-band instants return no categorical
assessment. The complete HTTP window equals serialization of the captured
engine result, and a retained full witness round-trips through `/direct`.
The second original missed interval is independently reproduced from serving
phase roots at JD UT1 2461121.322320754; it is not a second full HTTP window.

The window receipt records1,757,148 reader calls,241,718 evaluations,13 cells
and1,653,233 output bytes. The request explicitly admits4,096 historical
days and a32 MB output ceiling; all other limits are defaults. It reports
complete crossing coverage under the declared arithmetic model and no
unavailable numerical reasons. Its776.162-second full HTTP test includes
cell probes and direct-route validation and is not an isolated latency
benchmark. The surrounding two-test suite took809.529 seconds.

Release-facing doc consistency, release identity, Hellenistic inventory, REST
reference and website publication-manifest checks pass. The owning Git-wiki
generator and its check include the untracked canonical additions without
staging them. All ten Python files touched by this repair pass the configured
Ruff checks and parse under the Python3.10 grammar; this is not a3.10 runtime
claim. Whitespace checks pass in both repositories. Sixty-three other files
in the original73-file package retain their pre-review hashes.

`acceptance.json` binds the final repair-file hashes, original package and
review hashes, XML receipts and raw window/direct JSON. The reproduction
commands for the new tests and affected numerical owners are:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_muhurta_election_repairs.py tests/server/test_server_election_repairs.py
.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_muhurta_election_repairs_ephemeris.py
.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_marriage_tradition_geometry.py -k 'shadow_signal_contains_native_reference or complete_extra_history'
```

The numerical checks use the same Python 3.14.3 environment, strict harness,
no-download policy and owner-discovered DE441 resource as the original
checkpoint. No source fixture, tolerance, root algorithm, native substrate
or historical review receipt is rewritten to obtain agreement.
The lineage review found the repair structure owned by the declared
fixed-clock intervals, geometric input domain and existing history extents;
no secondary-engine algorithm or computational staging was introduced.
This closes R1–R4 at the tested scope, without a claim of new external eclipse
timing authority, predictive validation or exhaustive validation of all dates.

## 7. Source publication package

The user authorized commit and push after the focused repairs passed. This
publication includes the complete selected housing, commerce, ordinary travel
and VV/KP marriage implementation, source fixtures, engine/facade/REST
surfaces, research/plan documents and all four review repairs.

Before publication, all76 pending engine-repository files matched the final
repair acceptance hashes, with no unrelated pending files. Publication-only
edits reconcile this record, the plan and the remaining-work register; tested
Python code and source fixtures retain their validated bytes. The original
501-case implementation checkpoint and371-case repair checkpoint remain
separate evidence sets and are not summed as distinct tests.

The generated wiki is committed and pushed first, followed by the engine
commit containing its exact wiki reference. The repository histories own the
final commit identities. Release-facing documentation and inventory checks
run against the staged canonical documents using the ordinary wiki generator,
which now discovers the new tracked files. Version6.9.9 is unchanged; this
package creates no release tag and performs no website/Urania deployment.
