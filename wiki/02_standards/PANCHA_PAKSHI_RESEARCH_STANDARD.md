# Pancha Pakshi Research And Admission Standard

**Subsystem:** `moira/pancha_pakshi.py` with private ingestion in
`moira/_pancha_pakshi.py`

**Computational domain:** Source-scoped five-bird timing doctrine

**Status:** One named source-scoped public profile; no default or universal
canon

## 1. Current Boundary

Pancha Pakshi is within Moira's astrological domain, but the name does not
identify one interchangeable computational canon. Inspected Tamil witnesses
disagree about identity, durations, schedule cells, relationships, and the
relation between verse and commentary. Moira therefore admits independently
named products and never selects an ambient Pancha Pakshi default.

The first public profile is
`agastya_madras_1879_akshara_fixed_clock`. Its public claim is limited to the
Agastya-attributed Madras 1879 aksara/query-or-name-initial fixed-clock
operating schedule and directed relationship matrix. It admits exactly these
capabilities:

- `aksara_identity`;
- `nominal_schedule`;
- `directed_relationships`;
- `astronomical_context`;
- `fixed_clock_materialization`; and
- `fixed_clock_current_cell_selection`.

It is not a natal-Moon or birth-nakshatra profile. Nominal-schedule callers
supply `purva` or `amara`, `day` or `night`, and weekday explicitly. The
separate local-solar context operation accepts an instant and location, derives
only the governing sunrise window, day/night half, and local-mean-solar
weekday, and still requires the caller to supply `purva` or `amara`. The
separate fixed-clock operation materializes the selected nominal offsets from
the local-solar half start under an explicitly modern policy. A third modern
operation selects one current fixed-clock cell only after resolving the
governing solar half, and reports an explicit unmaterialized tail when a long
solar half outlasts the fixed span. No operation infers lunar paksha or
proportionally rescales the source schedule.

## 2. Admission Tiers

Admission belongs to a named profile and product, not to Pancha Pakshi as a
whole.

| Status | Meaning | Public computation | Default selection |
|---|---|---:|---:|
| `research_only` | Incomplete, unresolved, or non-admitted witness work. | No | No |
| `source_scoped_public` | One named witness and declared text-layer policy, with limitations carried in every result. | Yes | No |
| `corroborated_public` | A public named profile with documented independent-witness corroboration; disagreements remain distinct. | Yes | No |

There is no `universal_default` status. The schema rejects
`default_selection_allowed=true`. Adding a default would require a new
doctrinal and schema decision rather than an unnoticed manifest edit.

Competent-human Tamil review and independent-witness collation strengthen the
evidence tier. They are required before a corroborated, generalized, or
default-canon claim, but their absence does not prevent a narrowly and honestly
labelled `source_scoped_public` product.

## 3. Governing Objects

The implementation keeps these objects distinct:

- **witness** — one identified edition or manuscript record;
- **text layer** — verse, commentary, printed table, or an explicit rule
  derived from those objects;
- **profile** — one named, internally coherent selection from one witness;
- **product kind** — for example, an aksara/prasna operating schedule rather
  than natal-bird timing;
- **capability** — an independently admitted computation within a profile;
- **regime** — Purva or Amara, separately for day and night;
- **schedule cell** — one bird, activity, samam, sequence position, exact
  duration, and source locator;
- **identity policy** — query/name initial, birth nakshatra, or another
  explicitly sourced identity product; and
- **timing policy** — source-attested fixed nazhigai timing or a separately
  named modern seasonal transformation; and
- **local-solar context policy** — a separately admitted modern composition
  that derives astronomical context without altering the source schedule or
  pretending that the composition is source-attested; and
- **fixed-clock materialization policy** — a separately admitted modern
  composition that binds a sourced fixed nazhigai unit to reader-bound TT,
  publishes UT1 intervals, and preserves the fixed schedule's unclipped
  relation to its astronomical half; and
- **fixed-clock current-cell selection policy** — a separately admitted modern
  half-open interval-membership policy that resolves the governing solar half
  before selection and preserves an explicit unmaterialized long-half tail.

No object may silently acquire data from another profile. A source locator is
part of computational truth, not decorative documentation. Admission status,
capabilities, decision identity, and no-default policy belong to the manifest;
normalized source facts remain in the profile document.

## 4. The 1879 Source-Scoped Profile

The governing source is the Tamil print catalogued by Internet Archive as
[`dli.rmrl.000451_images`](https://archive.org/details/dli.rmrl.000451_images),
published in Madras in 1879 and traditionally attributed to Agastya. The
traditional attribution is bibliographic metadata, not a verified historical
authorship claim.

The admitted reading is deliberately narrow:

- the opening ontology is aksara/prasna: one explicitly listed initial vowel
  maps to a bird;
- Purva-day, Purva-night, Amara-day, and Amara-night remain four distinct
  regimes;
- each fixed half contains five samams of six nazhigai, totalling thirty
  nazhigai;
- activity durations are exact: Eat `5/4`, Walk `3/2`, Rule `2`, Sleep `3/4`,
  and Die `1/2` nazhigai;
- the schedule follows the machine-reconciled first-bird and assembly rules,
  including the corrected Purva-night assignment;
- identified printed-grid axes govern bird/activity assignments, while
  explicit prose and verse govern chronology; visual grid order is never
  chronological authority;
- the relationship product contains all twenty ordered non-self pairs,
  stores direction explicitly, and never infers reciprocity; and
- every generated cell retains governing temporal, assembly, chronology, and
  duration locators.

### Stage 2A modern local-solar composition

The additive `local_solar_day_explicit_paksha_v1` policy is Moira-owned modern
composition policy, not a translated rule from the 1879 witness. Its governing
object is `PanchaPakshiLocalSolarContext` with an embedded immutable
`PanchaPakshiLocalSolarContextPolicy`.

The low-level engine receives an explicit profile, UT1 instant, latitude,
longitude, and caller-supplied Purva or Amara label. Facade and REST callers
instead provide a timezone-aware datetime that is normalized to UTC and
crosses the established UTC civil-anchor boundary to UT1 once. The shared
local-solar-day resolver then:

1. resolves configured-reader-backed topocentric sunrise, sunset, and next
   sunrise for the fixed sea-level observer elevation (`0 m`) using an
   unrefracted altitude signal and the existing `-0.833`-degree threshold that
   incorporates conventional standard refraction and solar semidiameter;
2. classifies `[sunrise, sunset)` as day and `[sunset, next sunrise)` as night;
3. derives the weekday from local mean solar time at the governing sunrise;
   and
4. selects the unchanged nominal source schedule from the explicit paksha plus
   derived half and weekday.

Polar geometry without lawful solar bounds fails explicitly. The context
result exposes its UT1 boundaries and policy. Its provenance routing status is
`local_solar_half_and_weekday_performed_paksha_caller_supplied`. It does not
infer the paksha, scale source durations, convert nominal offsets to event
instants, or identify a current schedule cell.

### Stage 2B modern fixed-clock materialization

The additive
`fixed_24_minute_nazhigai_from_local_solar_half_start_v1` policy is also
Moira-owned modern composition policy. It does not rewrite the unchanged 1879
profile or attribute its clock and astronomical assembly to that witness. Its
governing object is `PanchaPakshiFixedClockMaterialization` with immutable
`PanchaPakshiFixedClockMaterializationPolicy` and
`PanchaPakshiFixedClockCell` members.

The policy composes four separately owned layers:

1. the named 1879 profile supplies the exact nominal thirty-nazhigai schedule,
   rational cell offsets, and source locators;
2. the University of Madras
   [*Tamil Lexicon*, page 2231](https://dsal.uchicago.edu/cgi-bin/app/tamil-lex_query.py?qs=%E0%AE%A8%E0%AE%BE%E0%AE%B4%E0%AE%BF%E0%AE%95%E0%AF%88&searchhws=yes&matchtype=exact)
   defines one nazhigai as sixty vinadi or twenty-four minutes;
3. the Stage 2A local-solar context supplies the containing half, weekday,
   selected nominal schedule, and astronomical half boundaries; and
4. the [IERS TT convention](https://www.iers.org/SharedDocs/Glossareintraege/EN/T/tt)
   and [IERS Technical Note 29](https://www.iers.org/SharedDocs/Publikationen/EN/IERS/Publications/tn/TechnNote29/tn29.pdf?__blob=publicationFile&v=1)
   govern the TT/SI-second time-scale basis.

Day materialization anchors at the governing topocentric sunrise; night
materialization anchors at the governing topocentric sunset. Every exact
nominal offset is multiplied by `1,440 SI seconds/nazhigai`, added on the
configured reader's TT path, and projected back to UT1 for publication. Thus
thirty nazhigai always spans exactly `43,200` SI seconds on TT. Materialized
cell intervals are half-open.

The fixed span is never clipped or stretched to the astronomical sunset or
next sunrise. The result instead exposes
`fixed_end_jd_tt - solar_end_jd_tt` as a signed-second residual and classifies
it as `before`, `coalescent`, or `after`; absolute residuals no greater than
`0.0001 s` are coalescent under numerical policy. This topology is necessary
because a twelve-hour fixed span can end before or after a seasonally unequal
solar half. It is not an accuracy tolerance or historical assertion.

The result does not identify a current cell. The requested instant can remain
inside the governing astronomical half while lying outside the materialized
fixed span. No precedence is invented for that condition, and no
solar-proportional scaling is performed or admitted by this fixed-clock result.
The provenance routing status is
`fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell`.

### Stage 2C modern fixed-clock current-cell selection

The additive `fixed_clock_current_cell_half_open_solar_precedence_v1` policy
performs one bounded operation over the admitted Stage 2B materialization. Its
governing object is `PanchaPakshiFixedClockCurrentCellSelection`, with immutable
`PanchaPakshiFixedClockCurrentCellSelectionPolicy` and the finite
`PanchaPakshiCurrentCellSelectionStatus` values `selected` and
`unmaterialized_solar_half_tail`.

Selection order is doctrine, not an implementation accident. Stage 2A first
resolves the half-open governing local-solar half. Stage 2B then materializes
that half's fixed schedule. Only then is the requested instant converted once
to reader-bound TT and compared with the materialized TT cells. A cell owns the
instant exactly when
`start_jd_tt <= requested_jd_tt < end_jd_tt`; shared endpoints belong to the
following cell and the final fixed endpoint is excluded. Membership tolerance
is exactly `0.0 s`. The Stage 2B `0.0001 s` topology coalescence remains a
classification policy and never changes current-cell ownership.

Solar-half precedence resolves seasonal overlap honestly. At exact sunset or
sunrise, the newly governing half is selected before cell membership is
evaluated. Cells from a prior short solar half that extend beyond its solar end
remain inspectable in that prior materialization but are ineligible to become
current. Conversely, when a long solar half continues after the fixed span,
the interval from the excluded fixed end to the excluded solar-half end has
status `unmaterialized_solar_half_tail` and `current_cell=None`. The selector
does not clip, wrap, repeat, stretch, borrow, or retain a cell to conceal that
tail.

Paksha remains caller supplied. Solar-proportional scaling and astronomical
paksha inference remain `not_performed`. The provenance routing status is
`fixed_clock_current_cell_selection_performed_paksha_caller_supplied_no_scaling_or_inference`.
This is a modern deterministic interval-membership claim, not an assertion
that the 1879 witness specified Moira's astronomical or time-scale composition.

### Stage 2D modern solar-proportional materialization

The additive
`solar_proportional_nominal_offsets_over_governing_half_tt_v1` policy is a
separate Moira-owned composition. Its governing object is
`PanchaPakshiSolarProportionalMaterialization`, with immutable
`PanchaPakshiSolarProportionalMaterializationPolicy` and
`PanchaPakshiSolarProportionalCell` members. It does not change the fixed-clock
Stage 2B or Stage 2C products.

Stage 2A supplies the governing half, astronomical bounds, weekday, and
unchanged nominal schedule. For every exact nominal endpoint `n` in the
thirty-nazhigai span `N`, Stage 2D retains the reduced fraction `f = n / N`.
The governing anchor and solar-half end are converted through the same reader
to TT. Every interior endpoint is computed independently as
`anchor_jd_tt + float(f) * (solar_end_jd_tt - anchor_jd_tt)`, rather than by
accumulating cell durations, and is then projected to UT1. The zero endpoint
and final endpoint are set exactly to the governing TT and UT1 bounds. All 25
cells are positive, contiguous, and half-open; the solar-half end is excluded.

The fixed `1,440 s` nazhigai conversion is not used. Because the normalized
fractions close on the complete governing half, no clipping, wrapping,
repetition, borrowing, or tail fabrication occurs. Paksha remains caller
supplied. Current-cell selection and astronomical paksha inference remain
`not_performed`. The provenance routing status is
`solar_proportional_materialization_performed_paksha_caller_supplied_no_current_cell_or_inference`.

The 1879 witness governs the nominal schedule and exact rational offsets, not
the proportional sunrise-to-sunset mapping. Route-specific provenance therefore
replaces the raw profile omission `seasonal_scaling` with
`source_attested_solar_proportional_materialization`: the result states both
that modern materialization was performed and that the source did not attest
that policy, without making contradictory claims or rewriting earlier results.

The source reading is machine-assisted. It has not received competent-human
Tamil sign-off and has not been collated against a genuinely independent
witness. Every public result therefore carries the profile's source-scoped
status, decision identity, source identity, assembly policy, astronomical
routing status, and declared omissions.

## 5. Conflicts That Forbid Blending Or A Default

The following are different computational doctrines or unresolved editorial
defects, not values that may be averaged or repaired by symmetry.

| Area | Evidence | Required policy |
|---|---|---|
| Identity ontology | The 1879 opening uses query/name initials; later presentations use birth nakshatra and Moon paksha. | Never label the 1879 mapping as natal identity. |
| Amara natal partition | A later Bogar-attributed edition's verse and commentary disagree; one layer overlaps Shravana and omits Revati. | No natal profile until text-layer precedence is declared and the partition is complete. |
| Duration vectors | The 1879 witness has one vector; later witnesses contain regime-specific or non-closing vectors. | Durations belong to the named witness and text layer. |
| Schedule cells | A later edition contains a verse/commentary mismatch that duplicates one bird and omits another. | Fail the affected layer; do not infer the missing bird. |
| Relationships | The 1879 table is directed and nonuniform; later tables use different assignments. | No reciprocity, symmetry inference, or cross-witness merge. |
| Timing | The inspected 1879 source attests fixed thirty-nazhigai halves, not proportional sunrise-to-sunset scaling. | Seasonal scaling, if admitted, is a separate policy and capability. |
| Padu and adhikara | Padu tables occur in later witnesses; no independent adhikara/bharana table was established. | Do not manufacture a day ruler from instantaneous Rule activity. |

Metadata-only conflict records are not executable profiles. The presence of a
witness in the research ledger never admits its facts or silently broadens the
1879 product.

## 6. Fail-Closed Invariants

A loadable profile must satisfy all applicable invariants exactly:

- known profile and manifest schema versions and matching canonical SHA-256;
- finite admission-status, product-kind, and capability registries;
- a nonempty admission-decision ID and `default_selection_allowed=false`;
- capabilities exactly consistent with the declared product kind;
- explicit profile ID, witness, derivation state, and assembly policy;
- four complete paksha/day-night regimes for this operating-schedule product;
- exactly seven weekday first-bird assignments per regime;
- exactly five known birds and five known activities;
- five samams per half;
- every samam contains every bird and activity exactly once;
- every half assigns every bird/activity pair exactly once;
- exact positive reduced rational durations totalling six nazhigai per samam
  and thirty nazhigai per half;
- nonempty source locators for every generated cell;
- no unknown, duplicated, overlapping, or omitted identity symbol;
- exactly one stored relationship for every ordered non-self pair, with no
  reciprocal inference; and
- no source component from a different profile.

For the additive local-solar context capability, the profile must also admit
`astronomical_context`; paksha must remain an explicit source label; the
instant and coordinates must be finite and lawful; the solved bounds must
satisfy `sunrise < sunset < next sunrise` and contain the requested instant;
the derived half and weekday must select one existing nominal schedule; and no
offset materialization may occur.

For the additive fixed-clock capability, the profile must also admit
`fixed_clock_materialization`; the Stage 2A context and explicit paksha rules
remain governing inputs; day must anchor at sunrise and night at sunset; one
nazhigai must remain exactly `1,440` SI seconds on reader-bound TT; every
published endpoint must be the corresponding TT endpoint projected to UT1;
all 25 intervals must be contiguous and half-open; the fixed span must remain
exactly `43,200` TT seconds; no interval may be clipped or proportionally
scaled to the solar end; and the signed TT end residual must obey the declared
`0.0001 s` coalescence policy. The Stage 2B result may claim no current cell.

For the additive fixed-clock current-cell capability, the profile must also
admit `fixed_clock_current_cell_selection`; the complete Stage 2B
materialization and caller-supplied paksha remain governing inputs; the
requested instant must be converted to reader-bound TT once; membership must
use exact half-open TT comparisons with `0.0 s` tolerance; and the governing
solar half must be resolved before selection. A selected result must carry one
cell from that materialization. An `unmaterialized_solar_half_tail` result must
carry no cell and must lie from the excluded fixed end to the excluded end of a
longer governing solar half. No prior-half cell, clipping, wrapping, repeating,
stretching, proportional scaling, or paksha inference is permitted.

For the additive solar-proportional capability, the profile must also admit
`solar_proportional_materialization`; the complete Stage 2A context, unchanged
nominal schedule, and caller-supplied paksha remain governing inputs; every
nominal endpoint fraction must remain exact, reduced, ordered, and bounded by
zero and one; and every TT endpoint must be derived independently from the
common anchor and complete governing-half TT span. The first and final TT and
UT1 endpoints must equal the governing solar-half bounds exactly. All 25 cells
must be positive, contiguous, and half-open. The fixed nazhigai-second rule,
current-cell selection, clipping, wrapping, repetition, tail fabrication, and
paksha inference are prohibited. Result provenance must distinguish performed
modern composition from absent source attestation.

The detached public result can prove its exact fraction-to-TT mapping, outer
UT1 closure, and UT1 ordering/contiguity from its own fields. It cannot replay
the reader-dependent inverse for an interior TT endpoint after the configured
reader has been detached. Interior TT-to-UT1 truth therefore belongs to the
governing factory path and its reader-bound tests; it is not presented as a
self-contained vessel invariant.

Unknown values, hash mismatches, incomplete tables, mixed profiles, capability
drift, and unresolved verse/commentary conflicts are errors. They are not
warnings or fallback opportunities.

## 7. Public Contract

The stable engine surface is `moira.pancha_pakshi`, with package-root and
`moira.vedic` exports and `Moira` delegation. The REST family is
`/v1/pancha-pakshi`.

The five Phase 1 operations remain kernel-free. Stage 2A adds the kernel-backed
`pancha_pakshi_local_solar_context_at(...)`,
`Moira.pancha_pakshi_local_solar_context(...)`, and
`POST /v1/pancha-pakshi/context/local-solar` surfaces. The low-level function
accepts UT1 JD; facade and REST inputs use a timezone-aware datetime normalized
to UTC and expose the resolved UT1 values in the result.

Stage 2B adds the separately governed kernel-backed
`pancha_pakshi_fixed_clock_materialization_at(...)`,
`Moira.pancha_pakshi_fixed_clock_materialization(...)`, and
`POST /v1/pancha-pakshi/schedule/fixed-clock` surfaces. This operation accepts
the same explicit profile, aware datetime or UT1 instant, location, and
caller-supplied paksha boundary as Stage 2A. It materializes the selected
source-owned nominal schedule only under
`fixed_24_minute_nazhigai_from_local_solar_half_start_v1`; no ambient or
alternate timing policy is accepted.

Stage 2C adds the separately governed kernel-backed
`pancha_pakshi_fixed_clock_current_cell_at(...)`,
`Moira.pancha_pakshi_fixed_clock_current_cell(...)`, and
`POST /v1/pancha-pakshi/schedule/fixed-clock/current-cell` surfaces. It accepts
the same explicit profile, aware datetime or UT1 instant, location, and
caller-supplied paksha, and only the
`fixed_clock_current_cell_half_open_solar_precedence_v1` policy. The result
contains the complete Stage 2B materialization, requested TT witness, finite
selection status, selected materialized cell or explicit null, and provenance.

Stage 2D adds the separately governed kernel-backed
`pancha_pakshi_solar_proportional_materialization_at(...)`,
`Moira.pancha_pakshi_solar_proportional_materialization(...)`, and
`POST /v1/pancha-pakshi/schedule/solar-proportional` surfaces. They accept the
same explicit profile, aware datetime or UT1 instant, location, and
caller-supplied paksha. The result contains the complete Stage 2A context,
policy, governing TT/UT1 anchor and end, TT half duration, 25 proportionally
materialized cells with exact nominal fractions, and route-specific
provenance. It does not select a current cell.

All computations require `profile_id`. Public results are immutable and carry
profile-owned provenance and omissions. Exact nazhigai values remain rational
in the engine and serialize as `{numerator, denominator}` at the transport
boundary.

Only the four Stage 2 operations accept a datetime and location. No operation
accepts a natal Moon, nakshatra, score, inferred name, caller-supplied sunrise,
or timezone policy. All four require explicit paksha. The context operation returns
only the selected nominal schedule; the fixed-clock operation returns all
materialized half-open cell intervals and their solar-half topology without a
current-activity judgment; and the current-cell operation returns only the
unique cell under its named fixed-clock policy or the explicit unmaterialized
tail status. The proportional operation separately maps exact nominal fractions
across the governing half and returns no current-cell judgment.

## 8. Evidence And Validation

The frozen blind reading, representative-grid reading, page-image
adjudication, and machine reconciliation remain historical evidence. Public
admission does not rewrite their earlier private status. The additive
[`public admission decision`](../../tests/fixtures/pancha_pakshi_1879_public_admission_2026_07_20.json)
links the former and current profile hashes, names the exact public claim and
nonclaims, binds the evidence records, and records a computational projection
over 10 identity symbols, 28 schedules, 700 cells, and 20 directed
relationships. Admission and provenance metadata are intentionally excluded
because the migration changes them.

The additive
[`Stage 2A admission decision`](../../tests/fixtures/pancha_pakshi_1879_local_solar_context_2026_07_20.json)
binds the unchanged profile hash and the frozen Phase 1 decision, records the
manifest-only capability transition, and names the modern composition policy,
assembly doctrine, authority boundary, and public nonclaims. It does not
rewrite the Phase 1 fixture or recast modern astronomical policy as historical
source evidence.

The chained
[`Stage 2B admission decision`](../../tests/fixtures/pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json)
binds the unchanged profile hash, the frozen Stage 2A decision and manifest,
and the manifest-only addition of `fixed_clock_materialization`. It records the
exact fixed-clock policy, the 1879 nominal-offset source leaves, the University
of Madras *Tamil Lexicon* nazhigai definition, the IERS TT/SI-second convention,
and the Stage 2A solar-anchor boundary without claiming that their composition
is an 1879 rule.

The chained
[`Stage 2C admission decision`](../../tests/fixtures/pancha_pakshi_1879_fixed_clock_current_cell_2026_07_20.json)
binds the unchanged profile hash, frozen Stage 2B decision and manifest, and
the manifest-only addition of `fixed_clock_current_cell_selection`. It records
the exact solar-half-first, half-open TT membership policy and the explicit
unmaterialized-tail result without presenting deterministic selection as an
external Pancha Pakshi oracle or independent-witness corroboration.

The chained
[`Stage 2D admission decision`](../../tests/fixtures/pancha_pakshi_1879_solar_proportional_materialization_2026_07_20.json)
binds the unchanged profile hash, frozen Stage 2C decision and manifest, and
manifest-only addition of `solar_proportional_materialization`. It records the
exact fraction-over-governing-half TT policy, independent endpoint derivation,
outer closure, and route-specific omission resolution without attributing the
modern composition to the 1879 witness.

Stage 2A validation proves policy immutability, capability gating, solar-bound
ordering, half-open boundary ownership, weekday and nominal-schedule selection,
UTC-to-UT1 adapter behavior, strict transport fields, and explicit polar
failure. The solar boundary is additionally authority-validated against the
offline JPL Horizons `sun-new-york-equinox` observer-table fixture: the
content-identified `DE-0441LE-0441` validation run differed by `0.082 s` at
sunrise and `0.123 s` at sunset under the fixture's `2 s` gate. That comparison
names the `-0.833`-degree Moira versus `-0.8333`-degree fixture thresholds and
UT1-versus-UT labels rather than claiming identical-threshold parity. It
validates the astronomical boundary only; it is not an external Pancha Pakshi
oracle or corroboration of the 1879 witness.

Stage 2B validation reconstructs and verifies the frozen Stage 2A manifest
before checking the current manifest, then proves exact 1,440-second nazhigai
arithmetic on reader-bound TT, 30-nazhigai/43,200-second closure, contiguous
half-open cells, TT-to-UT1 endpoint projection, unclipped topology reporting,
the `0.0001 s` coalescence policy, immutable vessels, strict facade/transport
policy admission, and the absence of current-cell selection or proportional
solar scaling. The Stage 2A Horizons evidence continues to govern only the
solar anchor; it is not an oracle for the fixed-clock composition.

Stage 2C validation reconstructs and verifies the frozen Stage 2B manifest,
then proves selection at all cell midpoints and shared boundaries, inclusive
anchor and excluded fixed-end ownership, exact sunset/sunrise solar-half
precedence, explicit long-half tail behavior, ineligibility of prior-half cells
after a short-half boundary, zero-tolerance membership, immutable status/cell
consistency, strict facade/transport policy admission, and the absence of
clipping, wrapping, repeating, scaling, or paksha inference. This is structural
and physical-invariant evidence over admitted inputs; no external current-cell
oracle or new astronomical-accuracy claim is made.

Stage 2D validation reconstructs and verifies the frozen Stage 2C manifest,
then proves reduced fraction ordering and unit closure, independent
common-anchor TT endpoint mapping, exact TT/UT1 outer closure, 25 positive
contiguous half-open cells across long and short day and night halves,
capability gating, immutable vessels, strict facade/transport policy admission,
rejection of fraction/endpoint drift and contradictory routing provenance, and
honest route-specific provenance. The inherited Horizons comparison still
governs only the solar anchor. No external Pancha Pakshi proportional-timing
oracle or new historical-accuracy claim is made.

Schema/hash/source checks are regression integrity; exact closure, bijection,
partition, immutability, and no-default checks are structural invariants; the
named leaf readings are source-specific evidence. None is an external oracle
or proof of a universal, historically original, or most widely practised
Pancha Pakshi canon.

## 9. Source-Artifact Boundary

Moira distributes its own code, schemas, prose, and independently normalized
symbolic facts. It does not bundle archival scans, derivative PDFs, OCR, page
images, copied table layouts, source prose, or third-party translations.
Archive rights and license labels remain bibliographic metadata rather than
runtime inputs. This is a standing non-bundling architecture, not a separate
rights-clearance phase or a public-admission blocker.

## 10. Deferred Products

The following require separately named sources, policies, capabilities, and
tests: astronomical or lunar inference of Purva/Amara; natal-Moon identity;
source-attested or alternate solar-proportional doctrines and proportional
current-cell selection; Padu, Bharana, and Adhikara birds; vinadi subdivision;
condition/scoring; and electional window search. Fixed-clock materialization,
fixed-clock current-cell selection, and solar-proportional materialization are
admitted only through their explicit Stage 2B, Stage 2C, and Stage 2D policies
and surfaces above; none may be inferred from the source-scoped profile or from
the Stage 2A local-solar context alone.
