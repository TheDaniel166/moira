# Eclipse implementation: provisional acceptance record

This is a provisional acceptance record, not release admission. It preserves
the distinction between an event candidate, a constructive witness, and a
complete certified result. The P2–P5 acceptance gates identified below remain
open, so P7 cannot be declared complete under the agreed plan.

**Historical snapshot:** the source fingerprint and catalog comparisons in
this record predate the subsequent eclipse search-ordering repair. References
below to the old next/previous defect describe the frozen catalog run, not
the later implementation. See `docs/ECLIPSE_EVENT_ORDERING.md` for the current
ordering contract and remaining coverage and completeness limitations. The
catalogs in this record have not been regenerated under that later source.

## Source and reproducibility

The isolated Moira 6.14.1 checkout is based on commit
`783e5af1593520eecfa284952b51dd698e6272dc`. The separately acquired DE441
kernel SHA-256 is
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`.
The 2026-11-16 provisional discovery run recorded scientific source/resource
fingerprint `fea25903a04ab882532d89ad4819387db58feb8e8e5b0df5d9b10aa9f706e865`.
That fingerprint covers the engine package, native sources, built extension,
`pyproject.toml`, and discovery runner; it is not the entire checkout. Retain
the full source diff and untracked inventory separately. The original user's
checkout was not changed.

The solar detail receipt records package digest `ab16c1cc53d35af18fe978db04c8e55ab94234f5b3832c394d53cf2bd5922e36`
using `scripts/eclipse_catalog/solar_generate.py`, which hashes all non-cache
package files and resources. The older research runner's `package_digest`
hashes only `.py`, `.pyd` and `.dll` files and produces
`868c64778383698ce71b578e4bea5e0a2ee5390d404bfc1e4aa012edf6bba150` on the
same current package. These digests are from different algorithms and cannot
be directly compared. Both the new solar digest and the discovery fingerprint
were independently recomputed and matched their respective receipts.

`scripts/eclipse_catalog/README.md` documents the reproducible discovery,
detail, supplement and comparison workflows. All outputs are provisional and
carry receipts. The interval is TT `[990923.5, 2817152.5)`, or astronomical
years -1999 through 3000 using the mixed Julian/Gregorian calendar. Native,
NASA-compatible, reference catalog and candidate model conventions differ.

## Acceptance by stage

| Stage | Status | Evidence and remaining gate |
| --- | --- | --- |
| P0: Baseline and contracts | Partial | The previous 118-test focused baseline and version/kernel/source receipts are retained. Per-product policies are explicit; a complete pass/fail/unresolved ledger for every plan fixture remains to be reconciled. |
| P1: Split-epoch precision | Focused gate passed; full release acceptance not claimed | Time, SPK and eclipse changes passed a 136-test focused suite, 151 broader eclipse tests and 19 independent raw-DE441 precision tests. The seven-case engineering seed-spread check was below 0.016 s, not a physical accuracy bound. Python-only unsupported segments and mixed/legacy fallback are explicitly limited. |
| P2: Lunar observables | Partial | Two opt-in angular/cone models and local candidate/contact paths passed 88 focused tests, including 26 historical cases under both models, five-event contact-step checks per model and real DE441 controls. Axis-distance, angular-opposition and overlap extrema are distinct candidate epochs. Searches do not prove absence, exhaustive contacts or global maxima. |
| P3: Solar path-wide hybrids | Partial | 50 focused tests plus existing regressions verify constructive daylight witnesses, including very short near-ingress examples. A sampled sign search is not exhaustive zero/extremum/tangency isolation, and H2/H3 direction remains unresolved. |
| P4: Grazing occurrence | Partial | 45 focused tests and solar regressions cover same-ray disc/horizon geometry and bounded local witness search. Negative samples do not establish global absence or exhaustive event-wide optimization. |
| P5: Solar boundaries and width | Partial | The 92-case survey covers 1,104 interior samples and 552 inside/exact/outside endpoint checks; 132 legacy path/noncentral/width regressions and 21 swept-interior tests passed. Exact-contact and full periodic topology, published time-stamped limits, the event-wide swept boundary, and a source-defined catalog width remain open. The 92 legacy widths are not admitted. |
| P6: API and compatibility | Partial | 32 distinct ASGI/OpenAPI cases and four exact/adjacent phase-boundary checks exercise the diagnostic routes. The legacy previous/next search defect below is deliberately not repaired in the legacy API; candidate completeness remains explicit. |
| P7: Rebuild and review | Partial | Native and NASA-compatible discovery/detail catalogs, candidate supplements and provisional cross-source joins have been regenerated. Important P2–P5 acceptance gates remain open, and the full output is not release-admitted. |

The count labels above refer to the selected recorded suites. They are not a
claim that every repository test, real HTTP transport environment, interval
proof, or source-defined catalog-width contract passed. Test commands must be
run with the checkout's `.venv`, downloads disabled, and the strict known-issues
policy. Examples:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_eclipse_split_epoch_precision.py tests\unit\test_tt_tdb_split_precision.py tests\unit\test_spk_time_precision.py -ra -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_lunar_shadow_models.py tests\unit\test_lunar_shadow_events.py tests\integration\test_lunar_shadow_candidates.py tests\integration\test_lunar_shadow_research26.py -ra -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_solar_hybrid_root_isolation.py tests\integration\test_solar_hybrid_path.py tests\unit\test_solar_disc_visibility.py tests\unit\test_solar_visibility_refine.py tests\unit\test_solar_visibility_witness.py tests\integration\test_solar_visibility_witness.py -ra -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests\unit\test_solar_clipped_p5_contract.py tests\integration\test_solar_clipped_p5.py tests\integration\test_solar_clipped_p5_survey.py tests\unit\test_solar_swept_witness.py tests\integration\test_solar_swept_interior_witness.py -ra -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests\server\test_eclipse_diagnostics_api.py tests\integration\test_eclipse_diagnostic_event_selection.py -ra -p no:cacheprovider
```

## Legacy phase-boundary defect

In the existing previous-eclipse search, requesting JD UT1 `2460409.26325`
returns the 2023 eclipse at JD `2460232.2496690527` and skips the nearer
2024 eclipse at JD `2460409.2620393815` because the phase and eclipse maximum
straddle the query. The new diagnostic route checks the adjacent phase, but
the original API is deliberately unchanged. This remains a known behavioral
defect, not a completed legacy-search repair. See
`docs/eclipse-diagnostic-api.md`.

## Five-millennium comparison

Native solar discovery and detail both found 11,898 events; the earlier native
discovery had the same identities, broad types and Saros labels. Native lunar
discovery and detail both found 12,068 events, with no native discovery
identity/type/Saros changes relative to the previous 6.14.1 scan.

Four native solar discovery epochs shifted by more than one second relative to
the earlier scan (maximum 1.572 s). In an independent 70-digit raw-DE441
same-model evaluation of those four, each new result lay within 0.006 s of a
locally refined minimum, and sampled split-objective differences from the raw
evaluation were at most 0.022 mm in axis distance. This supports reduced
numerical noise in these cases, not a bound on physical timing accuracy or an
explanation of cross-catalog differences. The prior source replay used a native
binary whose identity in the original index run was not established, so it is
not a byte-identical reproduction. The detailed review is
`P7_FOUR_SOLAR_PRECISION_REVIEW.md` in the accompanying evidence bundle.

The independently discovered NASA-compatible lunar scan and its detailed
catalog each have 12,069 events, with no detailed-row errors. All 12,064 NASA
lunations are represented, plus five compatibility-only events. Among shared
NASA events, there are five broad-type disagreements
under the compatibility policy versus 14 under native. NASA compatibility
does not imply identical physical model or validated physical accuracy. On
four of the five compatibility disagreements, native and Skyfield agree with
NASA; on the fifth (1553-07-25), both Moira modes and Skyfield label the event
penumbral while NASA lists partial. Different model policies and incomplete
independent authority prevent treating one label as automatically correct.
The independently refined compatibility detail epochs differ from their
discovery epochs by at most 0.0321 seconds, with identical lunation, broad
type and Saros labels across those two Moira runs. Both paths retain Moira's
full-moon and eclipse-season gates, so this agreement is not proof of complete
discovery.

The following rows record the five NASA/compatibility type disputes and the
nine native/compatibility membership differences. “Compatibility only” and
“native only” refer to the difference between the two Moira modes; they do not
mean absent from NASA or Skyfield. `N` = penumbral,
`P` = partial, and `—` means absent from that catalog, not proven physically
absent. Dates are astronomical-year TT calendar dates; NASA dates are
published dates, while otherwise the Moira TT epoch was converted using the
historical Julian/Gregorian calendar. The derived CSV and its receipt are
provided separately in the accompanying evidence bundle; their source workspace
directory is `p7_lunar_compat_disagreement_report_final`.

| Case | Lunation | TT date | NASA | Native | Compatibility | Skyfield |
| --- | ---: | --- | --- | --- | --- | --- |
| Type | -48881 | -1953-12-23 | N | N | P | N |
| Compatibility only | -48417 | -1915-06-28 | — | — | N | — |
| Type | -43147 | -1489-07-28 | N | N | P | N |
| Compatibility only | -36656 | -0964-05-14 | — | — | N | — |
| Type | -35101 | -0838-02-03 | N | N | P | N |
| Compatibility only | -33751 | -0729-03-30 | — | — | N | — |
| Type | -31152 | -0519-05-15 | P | P | N | P |
| Native only | -24004 | +0059-04-16 | — | N | — | N |
| Compatibility only | -14108 | +0859-05-20 | N | — | N | — |
| Native only | -8434 | +1318-02-16 | — | N | — | — |
| Type | -5522 | +1553-07-25 | P | N | N | N |
| Native only | -5300 | +1571-07-07 | — | N | — | N |
| Native only | 8615 | +2696-08-05 | — | N | — | — |
| Compatibility only | 9784 | +2791-02-11 | N | — | N | — |

For 12,068 native lunar identities, the angular candidate pass produced
12,066 local detections and two unresolved results; the static finite-cone
pass at Earth-radius scale 1.0 produced 11,987 detections and 81 unresolved.
These 83 rows cover 81 unique identities and are non-detections by bounded
numerical search, not proof of absence. NASA-only lunations were not evaluated
by these native-indexed candidate passes. The historical 26-case cone fixture
used scale 1.01; its values are not the same model configuration.

All 11,898 native solar detail rows succeeded. Relative to the frozen earlier
run, width statuses remain 7,517 available, 4,289 not applicable and 92 not
admitted. Maximum absolute TT change is about 1.120 s. The earlier frozen
source predates a later isolated constructor correction. An independent
review identified 80 site shifts over 1 km: 79 partial and one annular. Of
the 79 partial shifts, 64 are within 0.02 km of a single 0.05-degree search
step or its diagonal; the existing geographic search ends at this coarse
step. At the same new epoch, 75 of the 79 new partial sites have smaller
center separation than their old sites, while four are worse by
0.000343–0.000702 arcseconds. On those four, independently seeded local
refinements improve both sites, but do not prove a global optimum. The annular
outlier moves 1.044 km with a 1.079-second epoch change; re-evaluating the
current axis at its old epoch recovers the old site within about 0.2 m. The
existing partial-location search uses an apparent, refracted Sun-center
horizon and minimizes apparent center separation; newer visibility and
clipped-boundary diagnostics use a geometric horizon. These differences are
not established physical accuracy gains. The independently produced
`P7_SOLAR_GREATEST_SITE_REVIEW.md` and `p7_site_all_outliers_results.json`
are provided separately in the accompanying evidence bundle.

The full separate solar supplement examined 11,898 native events, reporting
569 constructive hybrid results and 11,329 unresolved; 7,147 instantaneous
cap candidates and 4,751 unresolved. All 92 previously unadmitted width cases
produced a bounded two-crossing instantaneous candidate at greatest eclipse,
each with `complete=false`; their legacy widths remain not admitted, and all
92 hybrid assessments remain unresolved. Twelve of the 15 NASA-hybrid/native
total-or-annular disputes have opposite-sign daylight witnesses in this
native model; the other three are unresolved. The +0919 NASA-total/native-
hybrid control also has witnesses. These results neither establish exhaustive
topology nor provide an event-wide swept boundary or a source-defined width.

Among the 569 constructive native-model hybrid results, NASA and EclipseWise
both label 566 hybrid and three total; the native instantaneous catalog
labels 555 hybrid, 13 total and one annular. Three additional NASA/EclipseWise
hybrids are unresolved by the native witness diagnostic. No witness event
lacks either external identity. The three external-total cases are
-1590-12-14 (native total), +0919-02-03 (native hybrid), and +0985-07-20
(native total). All 569 annular witnesses have geometric solar-center altitude
below 0.1 degrees; the minimum computed value is 0.010699 degrees. The smallest
absolute signed-radius witness is 0.012397 km and the smallest absolute
disc-radius-ratio margin is 7.1178e-6; five events have a weaker sign witness
below 0.1 km and 46 below 1 km. Thresholds and computed altitude are not
certified error bounds. Near-horizon geometry, limb and model sensitivity
matter, so these witnesses do not prove the external sources wrong.
