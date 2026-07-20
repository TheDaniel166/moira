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
- `astronomical_context`; and
- `fixed_clock_materialization`.

It is not a natal-Moon or birth-nakshatra profile. Nominal-schedule callers
supply `purva` or `amara`, `day` or `night`, and weekday explicitly. The
separate local-solar context operation accepts an instant and location, derives
only the governing sunrise window, day/night half, and local-mean-solar
weekday, and still requires the caller to supply `purva` or `amara`. The
separate fixed-clock operation materializes the selected nominal offsets from
the local-solar half start under an explicitly modern policy. No operation
infers lunar paksha, proportionally rescales the source schedule, or selects a
current cell.

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
  relation to its astronomical half.

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
solar-proportional scaling is admitted. The provenance routing status is
`fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell`.

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
`0.0001 s` coalescence policy. No current cell may be claimed.

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

All computations require `profile_id`. Public results are immutable and carry
profile-owned provenance and omissions. Exact nazhigai values remain rational
in the engine and serialize as `{numerator, denominator}` at the transport
boundary.

Only the two Stage 2 operations accept a datetime and location. No operation
accepts a natal Moon, nakshatra, score, inferred name, caller-supplied sunrise,
or timezone policy. Both require explicit paksha. The context operation returns
only the selected nominal schedule; the fixed-clock operation returns all
materialized half-open cell intervals and their solar-half topology, but makes
no current-activity judgment and performs no solar-proportional scaling.

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
current-cell selection; seasonal, sunrise-scaled, or other solar-proportional
timing; Padu, Bharana, and Adhikara birds; vinadi subdivision;
condition/scoring; and electional window search. Nominal-offset
materialization is admitted only through the explicit Stage 2B policy and
surface above; it must not be inferred from the source-scoped profile or from
the Stage 2A local-solar context alone.
