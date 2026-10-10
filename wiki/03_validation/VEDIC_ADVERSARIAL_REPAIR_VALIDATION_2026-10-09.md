# Vedic adversarial repair validation — 9 October 2026

**Status: LOCAL_COMPLETE. All eleven repairs closed.** This receipt governs VA-01 through VA-11
from the review of engine `b578ec89b90f709c8e64d5d9405ca06d29fcc69c`.
The [approved plan](../06_roadmap/VEDIC_ADVERSARIAL_REPAIR_PLAN_2026-10-09.md)
retains all five packages. Implementation and documentation are local; no
commit, push, tag, package publication or deployment is included.

## Source packet and admission decisions

Primary witnesses are the user's local editions, inspected as page images
where OCR obscured numbers. PDF page numbers below are one-based file pages;
printed page numbers are identified separately. The source files remain in
`C:/dev/ASTROLOGY-BOOKS-DATABASE`; no scans are copied into the engine package.

| Edition | Local path suffix | SHA256 |
|---|---|---|
| Raman, Bhava and Graha Balas, 1996 | Books by Authors/BV Raman/Bhava and Graha Balas 1996.pdf | `727c8063f64816a0c1c7f6bc577c249629854e980bf860bf4cfd8de16ec9bab2` |
| BPHS, Santhanam I | Classics books/BPHS-Santhanam-Vol-1.pdf | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| BPHS, Santhanam II | Classics books/BPHS-Santhanam-Vol-2.pdf | `ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45` |

Source/source-derived fixtures are in `tests/unit/test_shadbala_source_repairs.py`
and `tests/unit/test_dasha_full_intervals.py`. They are distinct from modern
DE441 chart regression cases. The original audit's extracted pages, renders,
source manifest and failing probes are preserved in
`C:/dev/outputs/vedic-adversarial-review-2026-10-09`. New repair outputs are in
`C:/dev/outputs/vedic-adversarial-repair-2026-10-09`.

| Subject | Inspected source and admitted reading | Independent witness |
|---|---|---|
| Full-parent Dasha | BPHS II Ch46/51 proportional subperiod rules; full interval precedes birth/horizon intersection | Rational Ketu/Rahu and Yogini Bhramari/Siddha; half-open adjacency through five levels |
| Temporary relationships | Raman 1996 article 25: inclusive houses2,3,4,10,11,12 | All 144 origin/distance combinations; same-sign is enemy |
| Saptavargaja | Raman PDF 27–28, printed 22–23, article 30; BPHS I PDF 264, printed 265,27.2–4 | Raman Sun seven awards7.5,30,7.5,7.5,7.5,7.5,22.5 sum90; alternative scale10,30,10,10,10,10,20 |
| Division assignment | BPHS I Ch6: Hora, Drekkana, Saptamsa, Navamsa, Dvadasamsa and unequal Trimsamsa | Odd/even D7 start, own-sign D12, all selected D30 boundaries; separate from generic harmonics |
| Ojayugma | BPHS I PDF 264,27.4½: Moon/Venus even, others odd in D1 and D9 | Mercury1 degrees → 30;31 degrees → 0; two mixed parity cases→ 15 |
| Nathonnatha | Raman PDF 40–42: linear distance from apparent local noon/midnight | Six exact solar fractions, opposite observer longitudes |
| Paksha | Raman PDF 43–44: continuous elongation, Moon doubling, nature qualification |179.9 degrees →119.933333333333 Sha; new/full phase neighbors |
| Tribhaga | Raman PDF 45–46: actual day/night thirds, Jupiter always 60 | Six exact boundaries; Mercury/Sun/Saturn day and Moon/Venus/Mars night |
| Ayana | Raman PDF 64–65, article 75 and Example 33 | Signed24-degree formula; Sun×2, Mercury absolute, Moon/Saturn sign reversal |
| Planetary war | Raman PDF 65–66, printed 60–61, articles 76–77 | Strict<1 degree, lesser longitude, fixed-disc quotient, equal debit/credit, unchanged Chesta |
| War alternative | BPHS I PDF 283, printed 284,27.20 | Distinct two-body Shadbala-difference wording; not silently merged into Raman's quotient |
| Precession fixture | ERFA `p06e` general precession at Einstein TT; retained tropical Moon/true-frame composition | Existing1e-9 balance tolerance unchanged; nutation independently checked at0.001 arcsecond |

The Raman standard horoscope positions used for the seven-award Sun witness
are from PDF 7: Sun 180°53′55″, Moon 311°17′19″, Mars 229°30′34″,
Mercury 181°31′34″, Jupiter 84°00′49″, Venus 171°09′56″, Saturn 124°22′41″.
Inputs are transcribed sexagesimal values, not fitted from present ephemerides.
The component arithmetic tolerance is1e-12 Sha; whole-result sum validation
uses the existing1e-6 Sha representation tolerance.

The `bphs_santhanam_27` selector names an **award scale**, not a complete BPHS
Shadbala implementation. It shares the explicitly selected Raman D1-only
Moolatrikona prerequisite. Both use actual D1 degrees and D1 compound relations.
No one-degree probe determines dignity. Complete worked-chart agreement is
not claimed: retained osculating Chesta, sign-based Drig, ingress-based
Abda/Masa and required Rupas are separately identified conventions. Sun's
minimum remains6.5 Rupas; no threshold was adjusted to fit repaired scores.

Raman Example 33 contains visible arithmetic/rounding discrepancies. At printed
Mars declination−22.45 degrees, the stated formula gives1.9375 Sha, while the
printed result is1.84. Venus−4.96 gives23.8, while the print says23.75. Sun's
38.125 is printed 38.12. Tests follow the stated algebra at the printed input
precision and disclose these differences; they do not widen a tolerance to
turn the printed chart into an oracle. Actual true declinations can exceed
24 degrees; signed algebra is preserved and requires its context receipt.

Moon nature uses a named half-open interpretation of the eighth-bright to
eighth-dark tithi interval, [84,264) degrees. Mercury association uses the
explicit same-D1-sign malefic convention, with optional supplied benefic or
malefic classification. Neither boundary/association rule is presented as
the only classical reading.

The targeted war search inspected Raman articles 76–77, BPHS27.20 and their
surrounding strength passages. These witnesses prescribe two-body behavior;
no simultaneous multi-party allocation was established there. The admitted
`moira_simultaneous_raman_raw_pairs_v1` therefore computes each pair once
against immutable pre-war bases, sums credits/debits, preserves signed nets
and leaves Chesta unchanged. Exact longitude ties use a stable pair label and
zero amount. This is an explicit Moira composition, not a claim that no other
source could discuss multi-way wars. Fixed disc values9.4,6.6,190.4,16.6,158.0
arcseconds are the inspected table, not modern astronomical disc diameters.

Online primary-text corroboration included the available
[BPHS transcription](https://vedic-astro.s3.amazonaws.com/books/bhrihat_parasara_hora_shastra.pdf)
and [Raman 1996 book transcription](https://studylib.net/doc/28274582/bhava-and-graha-balas-b.v.raman-1996).
The hashed local editions and inspected page images govern the admitted rules.

## Compatibility and operational contracts

- Dasha period responses add full interval endpoints; alternate periods add
  explicit year metadata. The first visible child is the active child on the
  original full axis, not a newly restarted child of the birth balance.
- Generic Varga partition uses exact binary-input integer ratios. The 65,880
  D1–D60 boundary corpus has zero wrong signs and zero label/coordinate
  disagreements; 4,320 explicit D60 profile checks retain zero disagreements.
  Tiny negative cyclic inputs remain immediately below360 and no longer crash.
- Full Shadbala and standalone Kala require an explicit context; standalone
  Sthana requires complete D1 positions. Dated callers derive context once.
  Synthetic inputs never silently borrow unrelated ephemeris positions.
- REST Shadbala positions are apparent geocentric; observer coordinates govern
  houses and solar geometry. This repairs the previously mixed topocentric
  chart/geocentric context. Source/geometry/policy receipts travel through
  chart/full/network/Bhava and Lagna. Direct Lagna input uses the dataclass
  shape and preserves complete strength evidence.
- Canonical war amounts are Kala adjustments. REST retains its existing
  `shashtiamsas_transferred` name with explicit `adjustment_component`.
  Deprecated `chesta_transferred` is unpopulated by new engine calculation.
- Output validation checks component sums, thresholds, frame/epoch, source
  entries and ledger derivation. Corrupted external input rejects; internal
  invariant failure is 500. Polar full strength is typed unavailable; Lagna
  preserves independent evidence without inventing a full strength.
- Kalavela borrows the supplied reader across every dependency and restores
  the previous reader on success/failure. It never closes that reader.
- Sade Sati validates the range, finite positive advancing step (at most 5 days)
  and budget before ephemeris access, then counts every sample/refinement.
  `SadeSatiBudgetError`/HTTP422 `sade_sati_budget_exceeded` returns no partial
  complete result. The default 10,000 and maximum 20,000 evaluations are work
  limits, not a hidden year cap. Smaller steps consume more budget.

Measured DE441 searches from J2000 at 5-day sampling:12 years uses 1,034
evaluations,30 years 2,557,100 years 8,450. At 1-day sampling,12 years uses 4,504;
the 3 matched windows differ by at most 0.00048828125 days at their boundaries,
within the 0.001-day bisection tolerance. This supports the default budget;
it does not prove detection of every substep retrograde excursion. The response
names that sampling limitation explicitly. Both direct/facade exports and REST
use the same bounded owner. Whole-REST operational budgeting remains VED-023.

## Eleven-row completion ledger

| Finding | Owning repair | Acceptance witnesses | State |
|---|---|---|---|
| VA-01 | dasha.py, dasha_systems.py, _dasha_intervals.py | Full-parent rational trees, alternate horizon, J2000 HTTP Rahu/Mars | Closed |
| VA-02 | shadbala_context.py, _shadbala_components.py | Four Kala components, observer/season/timezone/polar, real HTTP | Closed |
| VA-03 | _shadbala_components.py, vedic_dignities.py | Two scales, Sun 90, Moola prerequisite, source divisions,144 friendship cases | Closed |
| VA-04 | shadbala.py WarResolution | Independent quotient, graph cases, permutation/conservation, May2000 Lagna | Closed |
| VA-05 | strength models/serializers/network | December2020 actual amounts, full/direct Lagna roundtrip, corrupted ledger rejection | Closed |
| VA-06 | shadbala.py Ojayugma | Four Mercury D1/D9 parity combinations | Closed |
| VA-07 | varga.py exact partition |65,880 rational cases, extended divisors, all 8 HTTP surfaces | Closed |
| VA-08 | varga.py shared finite normalization | Tiny negative Shodashvarga, named/batch paths, circle consistency | Closed |
| VA-09 | upagrahas.py reader scope | No ambient reader, distinct outer reader, nested success/error restoration | Closed |
| VA-10 | sade_sati.py bounds and counter | Non-advancing step before access, preflight/runtime exhaustion, measured searches | Closed |
| VA-11 | alternate Dasha historical fixture | Independent general-precession/frame reconciliation at original tolerance | Closed |

## Execution receipts

The original failing review artifacts are preserved and are not overwritten.
The first repair checkpoint outcome is **6,276 passed, one explained skip, zero
unresolved failures/errors**, covering **173 distinct test files**. This is
an indexed reconciliation of the runs below, not a claim that the repository's
entire test suite was executed. `acceptance-summary.json` retains each test's
latest receipt and maps all five initial broad-run failures to passing reruns.

| Run | Scope | Result |
|---|---|---|
| Broad Vedic regression | 118 files; includes every original112-file selection, new repair tests and facade clock consumer | 4,661 passed,5 failed initially; all 5 subsequently resolved |
| Release Hardening | All 62 files selected from the current workflow, including added source/Einstein guards | 2,353 passed,1 existing skip,0 failures/errors |
| Strength/resource supplement | Real borrowed readers, geometry, source/graph tests, HTTP consumers | 255 passed |
| Boundary/context completion | All alternate clocks, strict metadata, direct/HTTP source evidence | 247 passed |
| Final reconciliation | 23 affected files, all 5 broad-run failures, exact root/facade/Vedic exports, docstring guards | 1,215 passed,0 failures/errors/skips |
| Final normalization follow-through | Strength source/legacy unit tests and retained real HTTP cases | 375 passed,0 failures/errors/skips |

The five initial failures were two missing curated Vedic exports, two Lagna
roundtrip fixtures that omitted new context/ledger evidence, and one winter
polar fixture that expected a full strength without sunrise. Exports now agree;
roundtrips send complete receipts and retain exact equality. The polar test
checks both equinox Porphyry fallback with full strength and winter typed
unavailability. No arithmetic tolerance or validator was weakened.

Across these invocations all 835 DE441 resource receipts ran with zero resource
skips/failures. Release tests also exercised2 supplemental small-body receipts
covering3 manifests,940 shards and11,720 bodies. The single existing skip is
`test_void_of_course.py:526`: no qualifying no-aspect example was found in its
30-day scan, so RULE-06 was not exercised. It is unrelated to the Vedic repairs.

Reproducible project-runtime commands (PowerShell, from `C:/dev/moira`):

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-adversarial-repair-2026-10-09/run_review_tests.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-adversarial-repair-2026-10-09/run_release_tests.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-adversarial-repair-2026-10-09/run_reconciliation.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_shadbala_source_repairs.py tests/unit/test_shadbala.py tests/server/test_server_vedic_repair_acceptance.py -q
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-adversarial-repair-2026-10-09/probe_boundaries.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-adversarial-repair-2026-10-09/measure_search.py
.\.venv\Scripts\python.exe -m ruff check moira moira_server scripts --select F401,F821,F822,F823 --no-fix
```

The saved manifests and XML preserve the executed selections; the broad
runner discovers any future matching tests, so its future collection count
can increase. Source arithmetic fixtures use independently transcribed or
rational expectations. Corpus checks are invariants, DE441 HTTP checks are
integration/regression evidence, and ERFA precession is separate astronomical
authority corroboration. No new native implementation or parity claim is made.

Runtime: project `.venv`, Python 3.14.3, discovered DE441 at
`C:/Users/nilad/.moira/kernels/de441.bsp`; downloads disabled and strict empty
KNOWN_ISSUES ledger. All 46 changed Python files pass 3.10 grammar; this is grammar
compatibility, not a second 3.10 runtime execution. Source Ruff and whitespace
checks pass. Exact exports and existing docstring governance pass. REST remains
498 operations; models and receipts are additive where described above.

Generated artifacts are synchronized in order: REST reference, Hellenistic
inventory, Git wiki, version-pinned website publication manifest. All six
release-facing documentation checks passed at the final local checkpoint;
`documentation-gates.log` records all ten generator/check exit codes as zero. Neither the website
application nor Urania source was changed. No native code, dependency or
release version was changed. Version remains 6.9.9. Source publication remains
uncommitted/unpushed; VED-011 is the next separately authorized package.


Strength uses normalized context positions as the authoritative receipt after
same-frame comparison within 1e-9 degrees. This prevents a tolerated rounding
difference from selecting opposite sides of a discrete Varga boundary.

## Second adversarial pass repairs — 9 October 2026

The second review found five additional composition/admission defects after
the eleven repairs above. The user authorized all five repairs. Original
failing witnesses remain in `C:/dev/outputs/vedic-adversarial-second-pass-2026-10-09`;
new receipts are separate in `C:/dev/outputs/vedic-second-pass-repair-2026-10-09`.

| Finding | Repair and targeted evidence |
|---|---|
| VA2-01: UTC/UT1 weekday mismatch | Derived context declares civil UTC midnight and carries its UTC JD. Both negative-DUT1 midnight dates, a positive-DUT1 date just before midnight, and a timezone-equivalent instant pass all six HTTP Shadbala products, facade and dated Lagna. Contradictory UTC/lord evidence rejects. |
| VA2-02: tolerated angles cross Lagna boundaries | Context positions govern Lagna before all discrete decisions, with D1/D9 nextafter tests, score/receipt equality, preserved missing bodies and rejected incompatible positions. Bhava receives the same composition repair. |
| VA2-03: balanced component corruption | Context-backed Uchcha, Ojayugma, Drekkana and Drig are recomputed through existing formula owners; ranges/discrete awards are checked. All seven planets reject balanced HTTP mutations under the real May 2000 war context while unchanged receipts round-trip. |
| VA2-04: full interval/year provenance | Shared engine child validation checks full containment and exact clipping at unchanged tolerances. Recursive REST admission uses the owner validator with explicit partial-child-list mode; generated trees still require complete coverage. Both modes enforce uniform year labels/lengths. Valid birth/horizon clips and unknown legacy provenance remain admitted. |
| VA2-05: Sade Sati sign 12 | Status and sampled Saturn signs share finite half-open angle normalization with windows; result vessels reject invalid sign indices. Tiny negatives, signed zero and equivalent turns agree across classification and windows; HTTP emits valid signs. |

The original focused witnesses reproduced the defects before repair. The
initial focused new-test selection passed **65 tests**, with all 33 DE441
resource receipts run; the final reconciliation also passes the added partial-
tree regression, for **66 new tests**. Two new files are included in Release Hardening. Original probe
replay rejects every previously accepted balanced component mutation and
foreign full interval; midnight facade/HTTP calls now succeed. The unchanged
independent generated corpus validates **250 trees / 166,118 nodes**. The
time owner's UT1/UTC inverse round-trips exactly across 10,000 deterministic
modern samples. These are numerical consistency and integration checks,
not additional classical attribution or independent ephemeris authority.

Explicit limits: the UTC weekday is a Moira convention, not a classical
sunrise-day claim. Supplied contexts remain caller evidence. Without house
geometry, the validator checks Kendradi membership and Dig range rather
than reconstructing their exact values. Context-free legacy strengths retain
structural validation. Unknown full Dasha endpoints remain unknown; parent
full containment is checked only when both full intervals are declared.
Sade Sati retains its previously documented sampled-search limitation.

All five findings are closed locally. The indexed final outcome is
**6,342 distinct passes, zero unresolved failures/errors and one explained
skip**, across **175 test files**. This reconciles the completed runs below;
it does not claim a single clean full-repository invocation. The original
failure outputs are preserved, with every failure mapped to a final passing
receipt in `acceptance-summary.json`.

| Run | Completed scope | Outcome |
|---|---|---|
| Broad Vedic | 121 files, including every prior adversarial selection | 4,792 passed; 3 compatibility regressions subsequently repaired |
| Release Hardening | All 64 files selected by the current workflow | 2,471 passed; same Dasha diagnostic regression subsequently repaired; 1 existing skip |
| Final reconciliation | 17 affected files, including every failing test/file | 1,104 passed; no failures, errors or skips |

The compatibility regressions were one changed Dasha diagnostic precedence
and two existing partial-child-list REST admission contracts. Diagnostic
precedence was restored in the engine. The shared alternate-tree validator
now exposes explicit complete/partial coverage modes; both modes retain
full-interval and year checks. Existing test assertions and numerical
tolerances were not weakened. Across these three runs all **814 DE441
resource receipts ran**, with zero resource skips/failures. Release coverage
also ran two supplemental small-body receipts covering three manifests,
940 shards and 11,720 bodies. The one skip remains
`test_void_of_course.py:526`, whose 30-day scan found no no-aspect example
for RULE-06; it is unrelated to these repairs.

Commands use `C:/dev/moira/.venv/Scripts/python.exe`, from `C:/dev/moira`,
with `MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`:

```powershell
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/run_review_tests.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/run_release_tests.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/run_reconciliation.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/verify_properties.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/probe_review.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/probe_lagna_boundary.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/probe_transport_followup.py
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/finalize.py
.\.venv\Scripts\python.exe -m ruff check moira moira_server scripts --select F401,F821,F822,F823 --no-fix
.\.venv\Scripts\python.exe C:/dev/outputs/vedic-second-pass-repair-2026-10-09/documentation_gates.py
git diff --check
git -C moira.wiki diff --check
```

The saved JSON manifests and JUnit XML record exact test selections. The
48 changed Python files pass Python 3.10 grammar checks. All six final
release-facing document checks pass after canonical generation; Ruff and
parent/nested-wiki whitespace checks pass. No source oracle, arithmetic
tolerance or native parity expectation was changed. REST remains 498
operations with additive weekday context evidence; version remains 6.9.9.

Changed owners in this second repair pass:

- `moira/shadbala_context.py`, `_facade_vedic.py`, `muhurta_lagna_dated.py`,
  `moira_server/services/shadbala.py`, and the Shadbala/Lagna transport models:
  UTC Vara basis, epoch evidence and consistent dated propagation.
- `moira/_shadbala_components.py`, `shadbala.py`, `muhurta_lagna.py`: shared
  positional formulas, component receipt checks and canonical consumer angles.
- `moira/_dasha_intervals.py`, `dasha.py`, `dasha_systems.py`, and alternate
  Dasha transport model/service: shared full provenance, year consistency,
  explicit partial-list mode and preserved diagnostic precedence.
- `moira/sade_sati.py`: shared longitude normalization and valid sign vessels.
- `tests/unit/test_vedic_second_pass_repairs.py`,
  `tests/server/test_server_vedic_second_pass_repairs.py`, and
  `.github/workflows/release-hardening.yml`: regression witnesses and CI selection.
- Four owning standards, this validation record and the remaining-work
  register, followed by canonical documentation generators and their outputs.

The prior eleven-repair work remains intact. The native implementation,
astronomical time substrate, dependencies, release identity, website/Urania
applications, unrelated work and VED-011 were not changed by this pass.
This is a local repair checkpoint; no commit, push, release or deployment
is included. Python 3.10 validation is grammar-only; execution uses the
project Python 3.14.3 runtime and discovered DE441, with downloads disabled
and the strict empty known-issues ledger.
