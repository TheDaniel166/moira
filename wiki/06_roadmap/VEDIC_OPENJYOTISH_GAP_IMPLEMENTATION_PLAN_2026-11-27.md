# Vedic engine implementation plan from the OpenJyotish gap scan

27 November 2026

Proposed work packages for the engine, Python facade and REST API. Coverage follows
[section 64 of the Vedic remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md#64-openjyotish-gap-scan---26-november-2026).
The [OpenJyotish snapshot](https://github.com/velteyn/OpenJyotish/tree/6615bb54c054bc9d9e6eb28e731ea339dc062b76)
identified features to investigate. Each Moira profile takes its rules from the
identified primary text or the originating author's published method. The engine
source reviewed for this plan is `fd4e155a3c03d4db90d3817700155eb7266344a7`.

## Order of work

| Wave | Packages | Dependencies |
| --- | --- | --- |
| 1 | Special Lagnas (VED-016) and Pushkara Navamsa/Bhaga | Parallel source and fixture work. Special Lagnas uses solar-event and sidereal primitives. Pushkara uses Varga geometry and independently collated rules. |
| 2 | 64th Navamsa and 22nd Drekkana, Prashna sphutas (C-02), Choghadiya | Separate source decisions. The numbered divisions can reuse the Varga result conventions from Wave 1. Choghadiya and Special Lagnas can share solar-anchor infrastructure where their policies agree. |
| 3 | Tithi Pravesha, monthly Tajika (C-04), Rath Narayana (VED-013 follow-through) | Three independent timing packages. Source collation can start in Wave 1. The return packages involve separate selection rules. Narayana advances once its sequence and duration tables are transcribed. |
| 4 | Ashtakoota and Porutham (C-01), KP astrology (C-03) | Two independent programmes. Admit each matching tradition separately. For KP, validate the planet and cusp chains before significators or period interpretation. |

Start each package with a source packet containing the edition and relevant
passages, rule inputs, decisions on variants, and independently reconstructed
worked cases. Freeze exact synthetic boundary cases with those examples. Name the
profile before assigning defaults and carry its identity through results. A
variant with unresolved source rules stays in research while other packages
advance.

## 1. Special Lagnas

- Collate the Bhava, Hora and Ghati definitions in the selected *Brihat Parashara
  Hora Shastra* edition and compare the distinct modern witness in chapter 5 of
  Rao's *Vedic Astrology: An Integrated Approach*. Reconcile prose, worked
  arithmetic and units in the chosen profile, including any inconsistency in its
  examples. [Rao's author-hosted book](https://mail.vedicastrologer.org/articles/astro_books.htm)
- Define the geocentric sidereal solar seed, sunrise definition and event
  ownership for a birth before, at or after local sunrise. Define elapsed time
  on the chosen time scale and the outcome when the applicable sunrise is
  unavailable or ambiguous.
- Implement a pure calculation from resolved sunrise evidence, then the
  reader-bound birth-time composition. Reuse the solar-event and time conversion
  work in [daily_panchanga.py](../../moira/daily_panchanga.py) and the existing
  sidereal transform. Return each longitude with the source profile, Sun at
  sunrise, elapsed quantity, and selected astronomy conventions. Expose it through
  the Vedic facade and a typed birth calculation.
- Accept only after the three points agree with independent arithmetic from the
  selected source and at sunrise all equal the selected solar seed. Cover the
  prior sunrise, exact rollover, DST, high latitudes, missing events and angular
  wrap. Exercise date/location composition against a real ephemeris.

## 2. Pushkara and numbered Varga divisions

- Obtain the relevant passages and tables for Pushkara Navamsa and Pushkara Bhaga,
  starting with the *Jataka Parijata* source lead. Verify the edition, the
  mapping across all twelve signs, angular units, and how a printed degree or
  ordinal corresponds to an interval. Collate the 64th Navamsa and 22nd
  Drekkana separately. Record each reference point, counting origin and whether
  the text reports a division, sign, lord or a combination.
- Reuse the exact D-9 and D-3 partitions in [varga.py](../../moira/varga.py).
  Keep the named rules in their own typed assessments. Return profile, reference
  identity, source interval and the exact observed division or degree evidence.
  Provide longitude-mode and chart-mode evaluation with an additive Varga API.
- Complete Pushkara first. Validate every published interval and degree table,
  half-open boundary ownership, values immediately to either side, the
  0°/360° seam and sign/ordinal consistency. Then validate the numbered divisions
  with independent inclusive counts and worked examples for every admitted
  reference point. Run the existing Varga and exact-partition regressions.

## 3. Prashna Marga sphutas

- Collate the passages for Tri-, Chatus- and Pancha-sphuta from the named
  *Prasna Marga* edition. Freeze the computation order, bodies, node convention
  and required Gulika convention. Record the operands of the chain so each
  result can be traced to its inputs.
- Implement the pure longitude evaluator first. Add a chart-bound evaluator
  that resolves the needed positions in one sidereal frame and passes explicitly
  selected Gulika evidence from [upagrahas.py](../../moira/upagrahas.py).
  Surface unavailable Gulika or chart geometry as such. Add typed direct and
  chart-composed calls under the Prashna ownership.
- Verify a printed worked example, 0°/360° arithmetic, propagation through the
  three calculations, matched node/frame policies and reader-bound/HTTP parity.

## 4. Choghadiya

- Obtain a primary printed or published calendar source that gives the whole
  weekday ordering, both day and night tables, and the governing solar day.
  Collate the 56 daylight and 56 nighttime entries and resolve how the night
  schedule is assigned across civil midnight. Keep regional alternatives as
  named profiles if supported by complete tables.
- Define a pure schedule builder for sunrise, sunset and next sunrise, then
  compose it with the existing timezone and solar-event primitives used by
  [Named Muhurta](../../moira/named_muhurta.py). Return eight daylight and eight
  nighttime intervals with their source labels and observable anchors. Agree the
  treatment of missing or non-unique solar events in the result contract.
- Validate the full weekly table against independent transcription. Verify exact
  partitioning of unequal daylight and night, lookup at joins and next sunrise,
  DST and midnight, and unavailable sunrises. Cover the pure, dated and REST
  surfaces with the same approved fixtures.

## 5. Annual Tithi Pravesha

- Begin with Rao's 2014 tropical conjunction-sign profile and collate the
  sidereal comparison as a separately named source profile. Determine what
  defines the target return year, what matches the natal lunation, and how
  duplicated or absent month identities are handled. Freeze source examples that
  distinguish the lunation choice, including the August 22 and September 20,
  1992 results in example 1. [Rao's paper](https://www.vedicastrologer.org/articles/pp_tp.pdf)
- Resolve natal geocentric Sun–Moon elongation and the source-defined natal
  lunation identity. Enumerate the bounded return-year candidate lunations using
  solved conjunctions. Solve the exact elongation inside each eligible lunation,
  retaining the candidate IDs, bracket and residual. Share the astronomy and
  event-solving primitives in [lunar_month.py](../../moira/lunar_month.py) where
  their contracts match. Derive month identity under the selected Tithi Pravesha
  rule and expose ambiguity when the source leaves it unresolved.
- Build the return chart at the solved instant with declared chart frame and
  reference location. Keep the event solution and chart settings individually
  inspectable. Add a typed date/return-year request and explicit profile.
- Verify each published case for both the selected lunation and the angular
  residual. Derive timing tolerances from printed precision and the ephemeris
  comparison. Cover phase wrap, month boundary, repeated or missing candidate
  months, birth-year/return-year bounds and missing ephemeris. Prove the chart
  uses the event instant and that return location affects local geometry.

## 6. Monthly Tajika

- Collate *Hayanaratna* sections 8.1–8.3 in Gansten's critical edition. Reconstruct
  the monthly rule and Shāh Shujāʿ worked example, including month numbering,
  mean and true solar quantities, time corrections and historical units. Decide
  which parts constitute a historical computation and which support a named
  modern projection with Moira's ephemeris. [Hayanaratna chapter 8](https://brill.com/display/book/9789004433717/BP000010.pdf)
- Implement the sourced monthly moment first, then cast its chart. Reuse the
  [annual Varshaphal](../../moira/varshaphal.py) anchor and any chart/house
  components whose definitions match. Give the monthly result its own profile
  and parent annual return, month index, time basis, and event evidence.
- Accept after reproducing the published intermediate quantities to their stated
  precision or documenting each justified difference for the selected profile.
  Verify the first and last admitted month, annual turnover, increasing instants,
  month index and year rejection, and preservation of existing annual results.
  Add the monthly chart as an independent Varshaphal REST surface.

## 7. Rath Narayana Dasha

- Extend the existing [Jaimini source packet](VEDIC_CHARA_ARGALA_SOURCE_RESEARCH_2026-10-12.md#36-rath-narayana-researched-separately-named)
  with the decision order from Rath's book and exact fixtures for tables 10–14.
  Resolve seed and co-lord strength, modality sequences and Saturn/Ketu
  exceptions, duration rules, antardashas and the complementary second cycle.
  Keep source-year arithmetic and calendar clock projection explicit. [Rath's book](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf)
- Implement one named natal D-1 profile. First expose the sign order, decision
  trace and exact durations. Then compose its projected periods and active
  lookup using [the common interval rules](../../moira/_dasha_intervals.py)
  where appropriate. Define representation for a source duration of zero before
  projection. Add Narayana discovery and calculation to the Jaimini facade and
  REST ownership.
- Compare complete first and second cycles and antardashas with the source
  tables. Verify ties and each exception, interval boundaries and year-basis
  differences. Run the existing Chara and Argala regressions.

## 8. Kuta matching

- Select a primary Ashtakoota lineage and an independently documented Porutham
  lineage. Obtain each full matrix, input roles, exception and cancellation
  precedence, and worked pairs. Keep the direction of a factor explicit. Decide
  which rules are evaluated from two Moon positions and which require further
  chart evidence.
- Implement a typed direct two-person evaluation first, with an optional
  birth-to-Moon composition using one declared sidereal and nakshatra policy.
  Return factors, raw and applied results, source of each exception, and a total
  only where the selected tradition defines one. Report any factor whose required
  chart evidence is unavailable.
- Validate every factor table and independent worked scores. Test swapped inputs,
  directional and symmetric factors, sign/nakshatra/pada boundaries, contradictory
  exceptions and missing evidence. Add a separate profile selector for each
  admitted tradition through Python and REST.

## 9. KP astrology

- Collate Krishnamurti's original readers and their printed tables for the
  chosen KP edition. Establish the house system, ayanamsa and node policies,
  star/sub/sub-sub allocation order, and sign/cusp boundary conventions.
  Identify the source and supported input domains for each additional result.
- Build one exact, pure sign/star/sub/sub-sub partition and use it for both
  planetary longitudes and cusps. Compose engine house geometry and sidereal
  positions at the chart instant. Return the chain, bounds and applied profile.
  Handle unsupported cusps explicitly and preserve the actual house system
  used. Expose the chart calculation through facade and typed REST.
- Verify printed tabular examples, every exact endpoint with neighboring inputs,
  wraparound and nesting. Test cusp and planet parity and high-latitude
  availability. Add ranked significators, ruling planets, and any period
  interpretation in separately validated increments after the chain. Preserve
  the existing dasha timing contract when the KP source adds annotations.

## Code ownership

New modules and routes below describe the implementation boundaries. Confirm
names during source admission and use the existing model, service, serializer,
and router layout in `moira_server`.

| Package | Proposed engine owner | Transport family |
| --- | --- | --- |
| Special Lagnas | `moira/special_lagnas.py` | Vedic birth calculation |
| Pushkara and numbered divisions | `moira/varga.py` and source-specific assessment code | `/v1/varga` |
| Prashna sphutas | `moira/prashna.py` | Prashna direct and chart |
| Choghadiya | `moira/choghadiya.py` | `/v1/muhurta` dated schedule |
| Tithi Pravesha | `moira/tithi_pravesha.py` | Annual return calculation and profile discovery |
| Monthly Tajika | Monthly composition alongside `moira/varshaphal.py` | `/v1/varshaphal` |
| Narayana | Source profile alongside the Jaimini dasha implementation | Jaimini profile discovery, sequence and active lookup |
| Kuta | `moira/kuta.py` | Matching profiles and two-person evaluation |
| KP | `moira/kp.py` | KP profiles and natal chart calculation |

Expose admitted operations through `moira/vedic.py` and the reader-owning
methods in `moira/_facade_vedic.py` where applicable. Reuse existing
`moira_server/app.py` registration patterns for newly owned route families.

## Delivery and verification

For each package, close a named primary-source packet, a computation result and
an acceptance receipt. Include the supported input contract and precise reasons
for unavailable or unresolved results. Use [the Vedic REST admission standard](../02_standards/VEDIC_REST_ADMISSION_STANDARD.md)
for profile selection, strict numbers and dates, typed serialization, caller-owned
reader binding, and Python/facade/HTTP parity. Prefer additive routes and curated
exports. Stage direct arithmetic tests first, then public and HTTP contracts and
real ephemeris/reader checks for chart-bound work. Use the project `.venv` and
record source inputs, fixture attribution, tolerances, and the actual runtime.
Apply each package's focused regression suite before release consideration.
Use existing regressions such as `tests/unit/test_daily_panchanga.py`,
`tests/unit/test_varga_exact_partition.py`, `tests/server/test_vedic_rest_admission.py`,
`tests/server/test_server_jaimini_profiles.py`, and
`tests/server/test_server_phase8_varshaphal_routes.py` with the relevant new
fixtures. Run the selected suites with `.\.venv\Scripts\python.exe -m pytest`.

## Dasha timestamp support for the website

Treat this transport prerequisite as its own small engine change. The dasha
service constructs period boundaries in UT1. Its serializer currently formats
`period.start_dt` through a JD calendar decomposition, which emits an ISO string
with a UTC offset without a scale conversion. A kernel-free probe confirmed an
8.651 ms difference for 2024-01-01 at 12:34:56.123456 UTC when compared with
`utc_datetime_from_ut1()`. The raw period boundary remains the authority.
See [dasha service](../../moira_server/services/dasha.py),
[dasha serializer](../../moira_server/serializers/dasha.py) and
[clock conversions](../../moira/julian.py).

Verify the serving response and existing transport options. If the chart
calculator still requires a UTC instant and the response supplies no
scale-correct instant, expose an additive, explicitly named UTC start field
derived from `start_jd` with the engine converter. Preserve the established period
fields and mark unrepresentable civil instants explicitly. Validate round trips
through the chart time parser at the precision supported by both transports
and separately cover birth-clipped starts and historical time support. The
site can use the same released contract independently of the Vedic research waves.

## Continuation checkpoint — 27 November 2026

**Wave 1 is published.** GitHub `origin/main` was checked at
[`2a3938b`](https://github.com/TheDaniel166/moira/commit/2a3938bab627b2b53b93b5c2f03f715a9b210a1a).
That commit contains Special Lagnas and both Pushkara assessments. Its
rebased validation passed 298 focused tests.

Wave 2 includes the Moon's inclusive 64th Navamsa, Lagna's inclusive 22nd
Drekkana, Raman's Tri-, Chatus- and Pancha-sphutas, and the Sirohi Choghadiya
day and night schedules. Python, the Moira facade and six REST routes are in
place. The [source standard](../02_standards/VEDIC_DIVISIONS_PRASHNA_CHOGHADIYA_STANDARD.md)
records the source readings, worked examples and modern materialization
choices. It documents why the numbered divisions preserve the in-sign
ordinal, why Raman's profile uses the Māndi clock for Gulika, and why the
night retains the sunrise weekday through midnight.

**Verification recorded.** Python 3.14.8 and DE441 ran the initial focused
suite with 450 passes and zero skips. The route inventory and REST
capability map checks passed with 71 reviewed decisions and 1,109 baseline
IDs still awaiting mapping. Ruff and docstring comparisons found no
new findings against the Wave 1 commit. Existing findings on touched files
at the baseline were 75 Ruff and 70 docstring findings.

Replay the focused suite from the isolated worktree if the diff changes.

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
$wave2Tests = @(
    'tests/unit/test_vedic_wave2.py',
    'tests/unit/test_varga.py',
    'tests/unit/test_varga_exact_partition.py',
    'tests/unit/test_shodashvarga.py',
    'tests/unit/test_upagrahas.py',
    'tests/unit/test_sayanadi_dated.py',
    'tests/unit/test_named_muhurta.py',
    'tests/unit/test_daily_panchanga.py',
    'tests/unit/test_rest_capability_map.py',
    'tests/server/test_server_vedic_wave2.py',
    'tests/server/test_server_varga_routes.py',
    'tests/server/test_server_named_muhurta.py',
    'tests/server/test_server_special_lagnas_pushkara.py',
    'tests/integration/test_sayanadi_ephemeris.py'
)
.\.venv\Scripts\python.exe -m pytest -o addopts= -q @wave2Tests
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/check_rest_capability_map.py
git diff --check
```

The Wave 2 review corrected the Khara chart path to use a geocentric Moon
and a local Lagna. The reconstructed Charak chart agrees within one
arcminute of the printed Moon and reproduces both projected lords. The
expanded focused suite passed 464 tests with zero skips, including the shared
sidereal chart context.

Wave 3 begins with the primary texts and worked cases in sections 5–7.

Wave 3 evidence and implementation decisions are recorded in the
[primary-source checkpoint](VEDIC_WAVE_3_PRIMARY_SOURCE_CHECKPOINT.md).

Wave 3 is published at [`9e74335`](https://github.com/TheDaniel166/moira/commit/9e743359e19a386068ba346b4bd3b5f6048ec550).
Wave 4 implements Charak Ashtakoota, Iyer Porutham, and the first KP chart
profile. The [Wave 4 checkpoint](VEDIC_WAVE_4_PRIMARY_SOURCE_CHECKPOINT.md)
records the verified examples, source ambiguities, and Python and REST contracts.
