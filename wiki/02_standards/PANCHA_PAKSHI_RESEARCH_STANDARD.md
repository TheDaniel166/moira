# Pancha Pakshi Research And Admission Standard

**Subsystem:** `moira/pancha_pakshi.py` with private ingestion in
`moira/_pancha_pakshi.py`

**Computational domain:** Source-scoped five-bird timing doctrine

**Status:** Four named source-scoped public profiles; no default or universal
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
- `first_eat_bird_mapping`;
- `directed_relationships`;
- `astronomical_context`;
- `astronomical_paksha_inference`;
- `fixed_clock_materialization`;
- `fixed_clock_current_cell_selection`;
- `solar_proportional_materialization`; and
- `solar_proportional_current_cell_selection`.

It is not a natal-Moon or birth-nakshatra profile. Nominal-schedule callers
supply `purva` or `amara`, `day` or `night`, and weekday explicitly. The
separate local-solar context operation accepts an instant and location, derives
only the governing sunrise window, day/night half, and local-mean-solar
weekday, and still requires the caller to supply `purva` or `amara`. The
separate fixed-clock operation materializes the selected nominal offsets from
the local-solar half start under an explicitly modern policy. A third modern
operation selects one current fixed-clock cell only after resolving the
governing solar half, and reports an explicit unmaterialized tail when a long
solar half outlasts the fixed span. Two further modern operations
proportionally map the unchanged nominal fractions across the complete
governing solar half and select one current proportional cell. Stage 2F is a
separate location-free astronomical inference: it maps apparent geocentric
Moon-Sun phase halves to the profile's directly attested Purva or Amara label.
It does not select a schedule, supply paksha to another operation, or infer
natal identity. Every schedule, materialization, and current-cell caller still
supplies `purva` or `amara` explicitly.

Stage 2I exposes one already normalized source component of that same 1879
profile as a pure lookup: the named schedule generator's first-samam EAT seed.
It accepts explicit profile Paksha, day/night half, and weekday, and performs
no schedule materialization, temporal routing, or interpretation as a
whole-day eating bird, Padu, Adhikara/Bharana, authority bird, condition, or
score.

Stage 2J recovered a separately witnessed vinadi research object without
admitting a runtime capability. The bounded object is a five-position ordinal axis beneath
each named activity. Uromarisi-attributed witnesses require accurate vinadi
division without supplying arithmetic, while a Bogamuni-attributed editorial
witness separately supplies two incompatible selectors: weighted Sūkṣma
intervals and equal-fifths Eka Sūkṣma intervals. Neither selector is bound to
the Uromarisi ordinal outcomes, and neither is a default. Stage 2K admits only
the two Bogamuni editorial selectors through a separate profile and mandatory
caller policy selection. No admitted profile, manifest capability, public
vessel, facade method, or REST route may infer the cross-witness Uromarisi
composition.

The second public profile is
`bogamuni_chennai_2024_nakshatra_natal_identity`. It admits exactly two
capabilities:

- `nakshatra_bird_mapping`; and
- `natal_identity`.

Its source product is a complete 54-cell Purva/Amara-by-nakshatra bird table.
Its separate natal product is a fixed modern Moira composition over that table,
not a claim that the source explicitly specifies birth-Moon or ayanamsa
calculation. It supplies no aksara identity, schedule, relationship,
materialization, current cell, condition, score, or forecast, and it does not
alter the 1879 profile.

The third public profile is
`bogamuni_chennai_2024_padu_bird_mapping`. It admits exactly one capability:

- `padu_bird_mapping`.

Its product is the source's separate fourteen-cell Purva/Amara-by-weekday Padu
bird table. Callers supply both source Paksha and weekday explicitly. The table
has no day/night axis, performs no astronomical routing, and is not a schedule
or identity product. Padu remains the source-labelled death-or-inoperative
bird; it is not converted into `RULE`, `first_eat_bird`, an Adhikara bird, or a
generic authority bird. The profile supplies no natal identity, schedule,
materialization, current cell, condition, score, or forecast, and it alters
neither prior profile.

The fourth public profile is
`bogamuni_chennai_2024_sookshma_temporal_selector`. It admits exactly one
capability:

- `sookshma_temporal_selection`.

Each call supplies an explicit selector policy, parent activity, and exact
elapsed `Fraction` within one six-nazhigai samam. The weighted policy rotates
the source-attested activity-duration vector from the parent activity. The
equal-fifths policy yields five ordinal-only cells and assigns no subactivity.
Both use exact half-open intervals. The profile supplies no datetime,
astronomical context, schedule composition, Uromarisi outcome, condition,
score, electional window, or forecast. It has no default, and no human-language
reviewer is required.

Stages 2N and 2O add no fifth profile and change none of these capabilities.
They are separate modern composition operations across the named 1879
schedule profile and the named 2024 selector profile. Every policy-driving
profile, schedule or civil-time axis, subject bird, timing policy, selector
policy, and explicit or derived exact elapsed offset remains visible.

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

Machine-assisted source reading is admissible when the exact witness, rendered
page locator, text-layer uncertainty, conflicts, and nonclaims remain visible.
There is no human-language-review dependency. Independent-witness collation is
required only for `corroborated_public`; it is not required for a narrowly and
honestly labelled `source_scoped_public` product.

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
  explicitly sourced or explicitly modern-composed identity product; and
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
  before selection and preserves an explicit unmaterialized long-half tail;
- **solar-proportional materialization policy** — a separately admitted modern
  composition that maps exact nominal offset fractions over the complete
  reader-bound TT solar half without using the fixed nazhigai-second rule; and
- **solar-proportional current-cell selection policy** — a separately admitted
  modern half-open interval-membership policy over that complete proportional
  partition, with exactly one non-null selected member and no tail or
  fixed-clock fallback; and
- **astronomical paksha inference policy** â€” a separately admitted modern
  geocentric lunar-phase classifier whose exact half-open numeric boundary is
  Moira-owned and whose waxing/Purva and waning/Amara translation is owned by
  the named source profile; and
- **Padu-bird mapping** - one source-owned `(Purva|Amara, weekday) -> bird`
  table with no day/night or schedule dimension and no implicit synonymy with
  authority-day, eating-bird, Rule-activity, Adhikara, or Bharana products.

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
- machine-assisted visual reading directly maps waxing lunar phase to Purva at
  IA leaf `n16` and waning phase to Amara at `n26`; that normalized mapping is
  source-scoped, its reading uncertainty remains explicit, and it carries no
  human-review dependency;
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

The source reading is machine-assisted and has not been collated against a
genuinely independent witness. Every public result therefore carries the
profile's source-scoped status, decision identity, source identity, assembly
policy, astronomical routing status, and declared omissions. Human-language
review is not an admission dependency.

### Stage 2E modern solar-proportional current-cell selection

The additive
`solar_proportional_current_cell_half_open_solar_precedence_v1` policy is a
separate Moira-owned selector over the unchanged Stage 2D materialization. Its
governing object is `PanchaPakshiSolarProportionalCurrentCellSelection`, with an
immutable `PanchaPakshiSolarProportionalCurrentCellSelectionPolicy`. It does
not change Stage 2D materialization or either fixed-clock product.

Stage 2A resolves the governing solar half before selection. Stage 2D then
materializes all 25 proportional cells for that half with the same configured
reader. The requested UT1 instant is converted once to reader-bound TT and is
tested using exact `start_jd_tt <= requested_jd_tt < end_jd_tt` membership with
`0.0 s` tolerance. The anchor belongs to cell zero, every shared endpoint
belongs to the following cell, and the old half's final endpoint is excluded.
Exact sunrise or sunset is therefore resolved into the new governing half and
selects its first proportional cell.

Complete Stage 2D coverage makes `selected` the only lawful status and the
selected cell is always non-null. Zero or multiple matches signal corrupted
computation and fail closed. There is no unmaterialized tail, clipping,
wrapping, repetition, borrowing, fixed-clock fallback, tolerance, or cell
retention. Paksha remains caller supplied; astronomical paksha inference and
natal identity remain separate and unperformed.

Stage 2E provenance must equal the Stage 2D provenance with only its
astronomical routing status replaced by
`solar_proportional_current_cell_selection_performed_paksha_caller_supplied_no_fixed_clock_mixing_or_inference`.
The Stage 2D omission `source_attested_solar_proportional_materialization`
remains intact, because neither selection nor API admission retroactively makes
the proportional rule source-attested.

### Stage 2F source-mapped astronomical paksha inference

Stage 2F adds `PanchaPakshiAstronomicalPakshaInference` and its immutable
`PanchaPakshiAstronomicalPakshaInferencePolicy`. Machine-assisted visual reading
of the exact 1879 witness directly maps waxing to Purva at IA leaf `n16` and
waning to Amara at `n26`. This mapping belongs only to the named profile, keeps
its machine-assisted reading uncertainty visible, and carries no human-review
dependency; it is not independent-witness corroboration or a universal Pancha
Pakshi vocabulary.

The numeric classifier is the modern Moira policy
`apparent_geocentric_moon_sun_longitude_paksha_half_open_v1`. One UT1 instant
is converted once to reader-bound TT, and apparent geocentric Sun and Moon
longitudes are evaluated in the true ecliptic of date on that shared TT.
Normalized `Moon - Sun` elongation assigns `[0, 180)` to Shukla/waxing/Purva and
`[180, 360)` to Krishna/waning/Amara. Exact `0` belongs to Shukla/Purva and exact
`180` to Krishna/Amara; tolerance and snapping are both absent. A common
ayanamsa is not applied because it cancels from the longitude difference.

This product accepts no location or caller-supplied paksha. It returns only the
instantaneous astronomical half, source-mapped profile label, direct locator,
policy, UT1/TT and longitude witnesses, and provenance. It performs no schedule
selection, materialization, current-cell selection, automatic routing into
another operation, or natal identity.

### Stage 2G source table and modern natal-Moon composition

Stage 2G adds `PanchaPakshiNakshatraBirdMapping` as a pure source-table vessel
and `PanchaPakshiNatalMoonIdentity` with immutable
`PanchaPakshiNatalMoonIdentityPolicy` as a separate composition. Rendered-page
inspection of the Bogamuni-attributed 2024 Internet Archive original PDF found
the complete Purva partition at leaf `n52`, the complete Amara verse at `n64`,
and the source phase-to-Purva/Amara binding at `n167`. These mappings belong
only to `bogamuni_chennai_2024_nakshatra_natal_identity`.

The commentary adjacent to the Amara verse is malformed: it duplicates
Shravana and omits Revati. The profile declares
`verse_precedence_for_nakshatra_partition`, admits the complete verse, and
retains the commentary as rejected conflict evidence. This is text-layer
precedence, not inferred symmetry or a repaired commentary. The
Uromarisi-attributed 1934 witness corroborates the Purva grouping at leaf `n18`
and independently exhibits malformed Amara commentary at `n61`; it remains
non-executable evidence and does not supply runtime cells.

The sources attest nakshatra-bird associations and phase labels, but they do
not explicitly govern a birth-Moon computation, Lahiri ayanamsa, or the equal
27-sector numerical taxonomy. The policy therefore fixes and exposes
`composition_status="modern_moira_policy_not_source_claim"`. One explicit UT1
instant is converted once to reader-bound TT. Apparent geocentric Sun and Moon
longitudes in the true ecliptic of date determine the half-open Shukla/Krishna
phase and source Paksha. The same TT epoch governs Lahiri true ayanamsa and the
sidereal Moon. Twenty-seven equal half-open `40/3`-degree sectors assign exact
internal boundaries to the following nakshatra. A maximum-one-ULP-below
recovery is permitted only when binary representation places an exact
mathematical boundary immediately below itself; it is not a tolerance band.

The result exposes every astronomical and sidereal intermediate, the phase
locator, nakshatra placement, nested source-table bird mapping and locator,
policy, provenance, and declared omissions. It performs no schedule selection,
materialization, current-cell selection, score, or forecast. The 1879
astronomical-paksha route remains standalone and does not acquire natal
semantics.

### Stage 2H source-owned Padu-bird table

Stage 2H adds `PanchaPakshiPaduBirdMapping` and the separate
`bogamuni_chennai_2024_padu_bird_mapping` profile. Rendered-page inspection of
the exact Bogamuni 2024 Internet Archive original PDF, locally identified by
SHA-256
`035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`, found
the Purva weekday Padu stanza and commentary at leaf `n52`, the Amara material
at `n60`, the repeated combined table at `n157`, and its restating commentary
at `n158`. The declared assembly policy is
`paksha_stanzas_govern_repeated_combined_table_confirms`: the Paksha
stanzas govern, while the later combined table and commentary confirm
rather than silently replace them.

The complete source-owned mapping is:

| Paksha | Sunday | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday |
|---|---|---|---|---|---|---|---|
| Purva | Owl | Crow | Cock | Peacock | Vulture | Owl | Vulture |
| Amara | Crow | Owl | Vulture | Peacock | Cock | Peacock | Cock |

These are exactly fourteen `(profile_paksha, weekday)` cells. There is no
day/night axis. The result calls the selected value Padu and retains the
source semantics
`profile_paksha_weekday_death_or_inoperative_bird_not_schedule_rule_activity`.
It does not inspect or transform a nominal schedule, derive a weekday from an
instant, select a current cell, or reinterpret instantaneous `RULE` activity.

The source layers also distinguish an eating-bird table and authority days;
they do not state that either object is an `Adhikara Pakshi` table. Bharana is
secondary-only terminology rather than the governing primary table label.
Moira therefore admits no Adhikara/Bharana alias or product and
does not relabel the pre-existing schedule field `first_eat_bird`. Uromarisi
1934 and the separately inspected Bogar material are unbound research context
only: neither the Stage 2H profile nor its decision binds them, and they do not
contribute runtime cells, create synonymy, or prove admission.

The product is a pure explicit-label lookup. It performs no astronomical or
civil-day routing, natal identity, schedule/materialization/current-cell
operation, condition evaluation, score, or forecast. It has no default and
does not add Padu semantics to either earlier profile.

### Stage 2I source-owned first-samam EAT seed

Stage 2I adds `PanchaPakshiFirstEatBirdMapping` and the granular
`first_eat_bird_mapping` capability to the unchanged 1879 schedule profile.
The computational object is exactly
`(profile_id, profile_paksha, half, weekday) -> first_eat_bird`. Rendered-page
inspection binds the four governing source leaves: `n16` for Purva day, `n21`
for Purva night, `n26` for Amara day, and `n31` for Amara night. The schedule
grids and continuation leaves already bound to each named generator are
same-witness confirmation, not independent evidence.

| Context | Sunday | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday |
|---|---|---|---|---|---|---|---|
| Purva day | Vulture | Owl | Vulture | Owl | Crow | Cock | Peacock |
| Purva night | Crow | Cock | Crow | Cock | Peacock | Vulture | Owl |
| Amara day | Cock | Peacock | Cock | Crow | Owl | Vulture | Peacock |
| Amara night | Vulture | Cock | Vulture | Owl | Crow | Peacock | Cock |

These are exactly 28 first-samam seeds. The bird begins the selected
generator's first samam in EAT; later samams advance under that generator's
separate progression rule. The result therefore does not describe an ambient
or whole-day eating bird. It exposes the generator ID, exact input axes,
`first_eat_bird`, canonical generator locators, and profile provenance without
materializing the 25-cell schedule.

The Uromarisi 1934 publication is a physically separate artifact and
corroborates all 28 cells at leaves `n6` and `n36`-`n37`. Its textual-lineage
independence from the related teaching tradition is not established, so it is
separate-publication corroboration rather than runtime data, a universal-canon
proof, or grounds for `corroborated_public` status. The earlier blind reading's
Amara-night vector is explicitly superseded by the later `n31`-`n35`
adjudication; the canonical profile contains the corrected vector above.

The source phrase `adhikara nalil` does not supply a separate authority-bird
table or prove synonymy. Stage 2I therefore admits no Padu, authority,
Adhikara/Bharana, condition, strength, scoring, electional, or forecasting
semantics and composes none of the four profiles.

### Stage 2J research-only vinadi recovery

Stage 2J records the source-owned object
`(activity, explicit vinadi ordinal 1..5, named context)` from rendered review
of Uromarisi-attributed 1922, 1932, and 1934 publications. These witnesses
preserve governing verses 228 and 229 and organize contextual outcomes by
first through fifth vinadi positions beneath EAT, WALK, RULE, SLEEP, and DIE.
The 1922 Karunanidhi Pillai commentary reiterates that the nazhigai must be
divided accurately but supplies no arithmetic selector. The 1932 contents also
expose distinct birth/natal, illness, journey, and house-foundation context
families. Separate publication does not establish independent textual lineage.

Rendered review of the Bogamuni-attributed 2024 editorial witness recovers two
separately named and incompatible temporal selectors for one six-nazhigai
samam:

- provisional policy `bogamuni_2024_weighted_sookshma_samam_v1` uses activity
  durations EAT `3/2`, WALK `5/4`, RULE `2`, SLEEP `3/4`, and DIE `1/2`
  nazhigai, which close exactly to six, with cyclic order beginning at the
  named activity; and
- provisional policy `bogamuni_2024_eka_sookshma_equal_fifths_v1` divides the
  samam's nazhigai into five equal parts.

These policies are not synonyms and may not be blended or silently selected.
Neither is automatically bound to the Uromarisi ordinal outcome tables; that
would be a cross-witness composition requiring its own explicit admission.
Machine-assisted reading also does not support normalizing or translating the
context-specific prognostic statements. Stage 2J therefore remains
`research_only` because selector choice and witness composition are unadmitted,
not because no source-attested formula exists. There is no human-language-review
dependency. Uromarisi clock routing, source-outcome normalization, automatic
composition, and Uromarisi-linked public exposure continue to fail closed.

### Stage 2K explicit Sookshma temporal-selector admission

Stage 2K converts only the two Bogamuni 2024 editorial selector candidates
into one separate source-scoped public profile. The caller must select exactly
one policy on every call:

- `bogamuni_2024_weighted_sookshma_samam_v1` rotates EAT `3/2`, WALK `5/4`,
  RULE `2`, SLEEP `3/4`, and DIE `1/2` nazhigai from the named parent
  activity; and
- `bogamuni_2024_eka_sookshma_equal_fifths_v1` divides the six-nazhigai samam
  into five exact `6/5`-nazhigai ordinal cells without assigning activities.

`elapsed_nazhigai` is an exact reduced rational in `[0, 6)`. Interval ownership
is `[start, end)`, so every lawful offset has exactly one match. The selected
policy and all five intervals are returned. There is no default, automatic
policy choice, clock or civil-time routing, astronomy, schedule composition,
or Uromarisi-outcome binding. Outcome interpretation, condition, scoring,
electional search, and forecasting remain unadmitted. Human-language review is
not an admission or maintenance dependency.

### Stage 2L independent-witness collation gate

Stage 2L is a completed research collation and a non-admission decision. It
inspects the exact 574-page Sarasvati Mahal Library 2014 sixth edition of
*Valaiyarul Patinen Siddhargal Panchapakshi Sastram*, the 89-page G. R.
Narasimhan secondary guide supplied for review, and a second 21-page supplied
guide that is rejected for unrelated tarot contamination. No artifact enters
the package.

The Sarasvati editor states that the verses derive chiefly from library
palm-leaf manuscripts and a minor share of printed books, while the
explanations, mathematical notes, and tables include editorial contributions.
The source inventory names Agastya manuscript `777`, Kumbamuni manuscript
`7015`, and Bogar and Uromarisi material. The editor also explicitly records
different activity-order doctrines between Agastya/Bogar and Uromarisi and
selects Agastya/Bogar for most of the compilation. This makes the volume a
strong multi-source conflict comparator, but not a textually independent
witness: no stemma or copying history establishes independence from the
already admitted witnesses.

The collation preserves both agreement and disagreement:

- all seven Purva-day first-EAT seeds agree with the 1879 profile;
- the waxing-day EAT/WALK/RULE/SLEEP/DIE vector agrees exactly at
  `(5/4, 3/2, 2, 3/4, 1/2)` nazhigai;
- the compilation and Narasimhan guide instead use waxing-night
  `(5/4, 5/4, 1, 1, 3/2)`, waning-day
  `(2, 3/2, 3/4, 1/2, 5/4)`, and waning-night
  `(7/4, 7/4, 3/4, 3/4, 1)` vectors; and
- the secondary guide supplies natal-star tables as well as aksara methods,
  which cannot reinterpret the admitted 1879 aksara/query product.

Publication separation, institutional custody, exact row agreement, and a
modern guide's repeated tables do not individually establish textual
independence. The Stage 2L decision therefore remains `research_only`, leaves
all four public profiles `source_scoped_public`, and changes no profile,
manifest, capability, engine, facade, or REST surface. No human-language
reviewer is required. A future corroboration attempt must obtain an accessible
candidate such as the catalogued Ramadevar manuscript, establish its copying
history, and collate one named product with repeatable locators before any
separate admission decision.

### Stage 2M Ramadevar candidate identity and access gate

Stage 2M resolves the catalog identity without inferring manuscript content.
The Commissionerate of Indian Medicine and Homoeopathy catalog identifies
serial `859`, manuscript `A5`, as `Ramadevar Panchapakshi` on PDF page 52.
The catalog provides no item-level leaf images, transcription, physical
description, date, incipit, explicit, colophon, provenance chain, copying
history, or computational rules. The candidate is therefore exactly
identified but remains `catalog_title_only`; product comparability and textual
independence are `not_assessable`.

Similar names must remain separate objects. G.O.M.L. `R.8978 Ramadevar
Patchini` is catalogued as a gnana, breath, and yoga work. British Library EAP
`EAP1217/1/2851`, Tamil University reference `TU_TAMIL_2058-01_2661`, is an
eighteenth-century 108-poem work on philosophy and ashtanga yoga. The same
Commissionerate catalog lists a different `Ramadevar Patchani - 108` inside
manuscript `27`, and the 1991 Sarasvati Mahal *Ramadevar Sutiram: Ashtanga
Patchini, Valai Pujai* governs medicine, alchemy, yoga, and ritual. None is the
five-bird temporal product merely because it shares a Ramadevar attribution,
`Patchani` wording, or a 108-poem count.

The required acquisition object is specifically Commissionerate manuscript
`A5`: a complete facsimile or critical transcription plus item-level physical,
scribal, custodial, and copying-history metadata. Only after one named Pancha
Pakshi computational product can be collated cell by cell with repeatable leaf
locators may a separate admission decision be considered. Stage 2M changes no
profile, manifest, capability, engine, facade, or REST surface and creates no
human-language-review dependency.

### Stage 2N explicit schedule-to-Sookshma composition

Stage 2N is the separate composition decision required by the earlier
no-blending rule. The caller names the admitted 1879 schedule profile, admitted
Bogamuni 2024 selector profile, source Paksha, half, weekday, samam `1..5`,
subject bird, selector policy, and exact elapsed `Fraction` within the samam.
Moira generates the schedule, requires exactly one cell for that subject bird
in that samam, and uses the cell's activity as the Stage 2K parent activity.

The composition policy is
`explicit_schedule_samam_subject_bird_sookshma_v1` and is explicitly
`modern_moira_policy_not_source_claim`. Neither source is credited with the
cross-profile join. Both source provenances remain present in the nested
result. There is still no default, clock or civil-time routing, astronomical
routing, Uromarisi outcome binding, translation, condition, scoring,
electional search, or forecasting. The profile documents, capabilities, and
manifest are unchanged. The decision fixture SHA-256 is
`084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9`.

### Stage 2O explicit civil-time-to-Sookshma routing

Stage 2O is a separate modern routing decision layered on Stage 2N. The caller
must name both profiles, aware civil instant, location, source Paksha, subject
bird, timing policy, and selector policy. Timing is exactly one of the already
admitted fixed-clock or solar-proportional materializations; neither is a
default and no fallback is allowed.

The current materialized cell determines the samam. Moira lifts the stored
binary64 requested, samam-start, and samam-end reader-bound TT values exactly
to `Fraction`, computes `(requested - start) / (end - start) * 6`, and supplies
that exact offset to Stage 2N. Shared boundaries remain half-open and therefore
belong to the following samam. A fixed-clock long-half tail returns the
existing `unmaterialized_solar_half_tail` with null samam, offset, and
composition; it is never silently filled by the proportional route.

The routing policy is
`civil_time_materialized_samam_to_stage2n_v1` and is explicitly
`modern_moira_policy_not_source_claim`. Paksha remains caller supplied. No
astronomical paksha inference, Uromarisi outcome binding, translation,
condition, scoring, electional search, or forecasting occurs. Profiles,
capabilities, and manifest remain unchanged. The decision fixture SHA-256 is
`2ea686e774ba4468c0515f621771b8a142c79f04d89b69839f482e05c37b40df`.

### Stage 2P research-only Uromarisi illness-grid recovery

Stage 2P selects one Stage 2J context family for structural recovery without
admitting its outcome semantics. The primary witness is the exact 166-page
1934 Uromarisi-attributed *Vinadi Pancha Pakshi Mulamum Uraiyum* PDF, locally
verified at SHA-256
`e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`.
Rendered review of PDF pages `115–126` established a provisional 25-locator
illness grid. Stage 2T later refines verse `250`: its heading and verse assign
DIE ordinal 5 while its commentary assigns SLEEP ordinal 5, so it is a blocked
identity-conflict candidate rather than an unconflicted SLEEP cell.

The 25 cell locators are verses `230–239` and `241–255`. Verse `240` is an
intervening transition rather than an ordinal cell heading. Verse `256` begins
a separate illness-duration section after the grid. Each cell records only its
activity, ordinal, verse, and PDF/printed-page span. Stage 2T preserves the
verse `250` layer conflict without mutating the historical Stage 2P fixture.
Tamil source expression, translations, and normalized outcome payloads are not
distributed or admitted.

This grid does not supply selector arithmetic and does not establish that
either Stage 2K Bogamuni policy belongs to the Uromarisi lineage. Stage 2O
therefore cannot route into it. Outcome labels, condition mapping, numeric
scores, medical advice, prognosis, electional judgment, and forecasting remain
forbidden. The manifest and all public surfaces are unchanged. No human-language
reviewer is an admission dependency. The research decision SHA-256 is
`449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2`.

### Stage 2Q research-only EAT-cell semantic-atom pilot

Stage 2Q applies a bounded source-owned vocabulary to only the five EAT cells
from the Stage 2P illness grid. The governing object is a cell-local record of
what the historical witness states: resolution, stated duration, distinct
prescribed-response categories, medicine and `prithivi` term references,
unresolved relation clauses, and uncertainty. It is not a generic favorable or
unfavorable label and is not a condition or numeric score.

Rendered PDF pages `116–118` control the reading. Archive.org OCR line spans
are retained only as navigation aids. The source-stated durations are `4 or
5`, `7`, `9`, `13`, and `15` days for ordinals one through five. Each cell is
machine-checked by its exact activity, ordinal, verse, page tuple, OCR
navigation span, semantic atoms, and canonical fixture hash. Tamil source
expression and full translations remain outside the distributed artifact.

This pilot describes a historical text; it neither validates its medical
claims nor offers diagnosis, prognosis, advice, or treatment. Disputed
relation clauses remain present with null semantics. No selector is bound, no
Stage 2O result is routed to an outcome, and no runtime profile, data,
capability, engine, facade, or REST surface changes. No human-language reviewer
is required. The research decision SHA-256 is
`7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9`.

### Stage 2R research-only WALK-cell semantic-atom extension

Stage 2R applies the same cell-local method to WALK verses `235–239` while
extending the ontology only where the text requires it. Ordinals one and four
state resolution; ordinals two and three state abatement; ordinal five gives a
timed progression without an explicit resolution statement. These dispositions
must not be collapsed into one generic outcome.

The time expressions are exactly `10` days, `15` days, within `20` days, `25`
days, and within one month. Exact and upper-bound forms remain distinct, and a
month is never silently converted into days. Source deity titles and their
stated relations, explicit response categories, medicine or physician
references, water-clause roles, the Navagraha-dosha reference, and unresolved
activity relations remain cell-local and uncertainty-bearing.

Rendered PDF pages `118–120` control the reading; Archive.org OCR lines are
navigation aids only. This is a historical-text record, not medical
validation, diagnosis, prognosis, advice, treatment, condition scoring, or
forecasting. No selector, Stage 2O routing, runtime profile, manifest,
capability, engine, facade, or REST surface changes. No human-language reviewer
is required. The research decision SHA-256 is
`361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6`.

### Stage 2S research-only RULE-cell semantic-atom extension

Stage 2S applies the cell-local method to RULE verses `241–245`. All five
cells state resolution, with time expressions of `3` days, `5` days, within
`8` days, `10` days, and `12` days. The third cell remains an upper bound and
must not be rewritten as an exact eighth-day event.

The source adds fire-clause roles, Saturn-dosha references, bounded historical
effect language, and one surface no-enmity statement. These remain separate
from source deity titles and explicit actions. No fire or dosha clause becomes
a medical cause, no effect phrase becomes a symptom or score, and the relation
statement is not bound to runtime doctrine.

Rendered PDF pages `120–122` control the reading; Archive.org OCR lines are
navigation aids only. This is a historical-text record, not medical
validation, diagnosis, prognosis, advice, treatment, condition scoring, or
forecasting. No selector, Stage 2O routing, runtime profile, manifest,
capability, engine, facade, or REST surface changes. No human-language reviewer
is required. The research decision SHA-256 is
`85142480188a00ddec3de6f192a36025f282ca0eefa4643a6f1d74da4cec811d`.

### Stage 2T research-only SLEEP semantic atoms and identity conflict

Stage 2T reviews SLEEP verses `246–250` but produces only four unconflicted
semantic records. Verses `246–249` preserve resolution difficulty, recurrence,
an exact 20-day expression, two upper-bound day expressions, and a conditional
three-month mortality-or-resolution branch. Mortality, recurrence, distress,
harm, wind-dosha, treatment, ritual, and activity-relation language remain
historical atoms rather than prediction, diagnosis, cause, symptom, score,
advice, or runtime doctrine.

Verse `250` is blocked by text-layer identity conflict. Its heading and verse
assign DIE ordinal 5, while its commentary assigns SLEEP ordinal 5. No layer
is silently preferred, and neither its mortality language nor its candidate
five-day commentary expression is normalized into a cell payload. The Stage
2P fixture remains unchanged as historical locator evidence; current truth is
four unconflicted SLEEP cells plus one blocked candidate.

Rendered PDF pages `122–124` control the reading; Archive.org OCR lines are
navigation aids only. No selector, Stage 2O routing, runtime profile, manifest,
capability, engine, facade, or REST surface changes. No human-language reviewer
is required. The research decision SHA-256 is
`09f7651325cdac058d9816b85b031ef528f514ae91fb8cd9636452b8d7fb302a`.

### Stage 2U research-only DIE semantic atoms

Stage 2U records five unconflicted DIE ordinals from verses `251–255`. Verse
`250` is not used as a sixth ordinal or silently repaired: it remains only the
blocked Stage 2T precursor whose heading and verse say DIE ordinal 5 while its
commentary says SLEEP ordinal 5.

The first DIE cell preserves a conditional mortality upper bound of two months
and a separate six-month source `tanmai` branch whose meaning is not normalized.
The second preserves both an instantaneous marker and a one-year marker without
harmonizing them. The other three cells contain no numeric time expression.
Mortality, life-departure, body-destruction, nonresolution, space/void, fate,
deity, activity-relation, and unclear source-branch clauses are bounded
historical atoms, not prediction, diagnosis, prognosis, cause, symptom, score,
advice, deterministic fate, or runtime doctrine.

Rendered PDF pages `124–126` control the reading; Archive.org OCR lines are
navigation aids only. Verse `256` begins a separate illness-duration section
and terminates Stage 2U scope. No selector, Stage 2O routing, runtime profile,
manifest, capability, engine, facade, or REST surface changes. No human-language
reviewer is required. The research decision SHA-256 is
`4954c13c33aa755bc0e8c6f47b7825d6ddb8346a2b6df39edf804872e81cbf70`.

### Constitutional Phase 2 classification closure

Phase 2 closes at the private research boundary over the `24` unconflicted
illness-context records. The data-free internal module
`moira._pancha_pakshi_classification` owns the typed descriptive model:

- `PanchaPakshiHistoricalDisposition` preserves exact source-statement classes
  rather than favorable/unfavorable labels;
- `PanchaPakshiHistoricalTimeClass` distinguishes exact, upper-bound,
  conditional, multiple, unreconciled, and unstated time shapes without
  selecting a temporal policy;
- `PanchaPakshiHistoricalSemanticMarker` records only the presence of named
  response, mediation, elemental/dosha, deity/fate, effect, activity-relation,
  mortality, and source-branch atoms;
- `PanchaPakshiHistoricalCellClassification` binds those classes to one
  activity, ordinal, verse, source decision/hash, and nonempty uncertainty;
- `PanchaPakshiHistoricalIdentityConflict` carries disagreeing text-layer
  identities without a classification payload; and
- `PanchaPakshiUromarisiPhase2ClassificationCorpus` enforces exact
  `5/5/5/4/5` coverage, uniqueness, deterministic order, and the blocked verse
  `250` identity.

Every closure row is machine-derived from the exact Stage 2Q–2U semantic atom:
EAT uses its resolution and duration fields, WALK/RULE/SLEEP use their
disposition and time-expression fields, and DIE uses mortality form and
time-expression fields. Presence markers and uncertainty counts are likewise
projected from the source record. Construction fails on inconsistent
activity/disposition, mortality marker, uncertainty, coverage, order, identity,
or conflict state.

This closure opens Phase 3 only for private derived convenience views and
vessel consistency/malformed-construction hardening. Phase 3 may not add
doctrine, interpretation, generic judgment, condition, score, prognosis,
medical advice, temporal policy, Uromarisi selector binding, runtime profile,
public export, facade method, or REST route. Selector doctrine belongs to
constitutional Phase 4. Human Tamil review is not required; Commissionerate
`A5` acquisition gates only a future `corroborated_public` claim; and verse
`256` begins a separately scoped product. The Phase 2 closure SHA-256 is
`a5cd64696d4c040554f2c235056dfd28477fd0796fc82306f44ae43473d434e2`.

### Constitutional Phase 3 inspectability closure

Phase 3 consumes only the frozen private Phase 2 vessels. It adds no source
record or classification. Its cell properties expose:

- `(activity, ordinal)` identity and `(decision ID, SHA-256)` source binding;
- deterministic lexical semantic-marker values;
- exact stored presence of mortality language; and
- whether the existing time class is stated, conditional, or explicitly
  unreconciled.

Conflict properties expose heading, verse, and commentary assignments, their
distinct activities, heading/verse agreement, and source binding without
selecting a governing layer. Corpus properties expose classified and blocked
verses, activity counts, unique source bindings, mortality-language cells, and
unstated-time cells. Typed lookups return cells by activity or identity and
return classifications and conflicts by verse. Absence returns `None`; no
adjacent, symmetric, or cross-activity fallback exists.

Phase 3 hardens immutable tuple containers, exact EAT `230–234`, WALK
`235–239`, RULE `241–245`, SLEEP `246–249`, and DIE `251–255` identity
matrices, activity-specific Phase 2 time classes, one source binding per
activity, and the Stage 2T source binding of the verse `250` conflict. Thus
`classification_at(SLEEP, 5)` and `classification_for_verse(250)` are absent,
while `conflict_for_verse(250)` remains present.

These are derived views and consistency rules only. They are not prediction,
prognosis, condition, score, advice, outcome selection, temporal policy, or
runtime admission. No package, facade, REST, manifest, or profile surface
changes. Phase 3 completion permits Phase 4 to make one explicit doctrine or
policy decision, but supplies no default or inherited Uromarisi selector
binding. The Phase 3 decision SHA-256 is
`2fd93585f8d2d439882ee77cdeb28e5509e916cd752357d60caaa003cc9fb2ca`.

### Constitutional Phase 4 doctrine and policy closure

Phase 4 admits one private research policy:
`moira_explicit_uromarisi_activity_ordinal_lookup_research_v1`. The typed
`PanchaPakshiHistoricalClassificationPolicy` requires
`PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL` and
exposes these fixed boundaries:

- the policy is a modern Moira research rule over source-owned ordinals;
- activity and ordinal are caller supplied explicitly;
- no temporal selector is source-attested or admitted;
- Stage 2K composition is not admitted;
- outcome interpretation is not performed;
- medical use is forbidden; and
- admission remains `research_only`.

`pancha_pakshi_uromarisi_classification_under_policy` requires corpus, policy,
typed activity, and ordinal with no default. It delegates exactly to the Phase
3 activity/ordinal lookup and preserves `None` without fallback. It accepts no
instant, clock, elapsed duration, samam offset, or selector policy. SLEEP
ordinal 5 therefore remains absent and verse `250` remains only a conflict.

The Bogamuni 2024 weighted-Sookshma and Eka-Sookshma equal-fifths policy IDs
remain visible as separate unadmitted cross-witness candidates. Neither is
attributed to the Uromarisi witness, selected automatically, or routed into the
historical classifications. A future composition would require its own
explicit governing object, provenance, non-medical semantics, and admission
decision.

Phase 4 adds no relation doctrine, condition, score, prognosis, advice,
runtime profile, manifest entry, package export, facade method, or REST route.
Its completion permits Phase 5 relational formalization only; no unresolved
activity-relation clause is silently resolved. The Phase 4 decision SHA-256 is
`4a444c91bab9a4949664e6bca4e64ad0ee341b439019db831429e4548bd2c4f9`.

### Constitutional Phase 5 relational formalization

Phase 5 creates a private typed `PanchaPakshiHistoricalRelationRecord` for each
of the `24` unconflicted Phase 2 classifications and binds them in
`PanchaPakshiUromarisiPhase5RelationCorpus`. A record is owned by the classified
activity, ordinal, and verse and must retain that classification's exact source
decision identity and digest.

Relation presence projects only the Phase 2 `activity_relation_clause` marker.
The complete corpus contains `17` present and `7` explicitly not-recorded
clauses. Ten EAT/WALK records retain `unresolved_clause` plus their stated high
or medium confidence. Seven RULE/SLEEP/DIE records preserve only an exact
bounded surface category: `no_enmity`, `rule_enmity_disallowed`,
`rule_enmity_branch`, `earth_rule_enmity_disallowed`, or
`rule_enmity_required`. Because those bounded atoms state no relation-specific
confidence, the typed record must use `not_stated`; it may not invent one.

Neither presence nor a surface category establishes relation endpoints,
direction, normalized meaning, favorability, condition, score, prognosis, or
runtime semantics. A not-recorded clause cannot be rewritten as present, an
unresolved clause cannot be normalized, and verse `250` remains outside the
relation corpus as an identity conflict. The corpus must match all Phase 2
cells in canonical order, preserve source bindings exactly, and fail closed on
any marker, ordering, or binding mismatch.

Phase 5 adds no selector binding, runtime profile, manifest entry, package
export, facade method, REST route, prediction, diagnosis, advice, condition,
score, or medical-truth claim. Its completion permits Phase 6 relational
hardening and inspectability only. The Phase 5 decision SHA-256 is
`e8e189f75418cc96bc6930e2e93d2cfcebc849cb4080001ee4b4b07b158908d1`.

### Constitutional Phase 6 relation hardening and inspectability

Phase 6 adds derived-only views to the Phase 5 vessels. A relation record may
expose its exact activity/ordinal/verse identity, source binding, detection,
admission, scoring, unresolved-clause status, and named-surface status. These
properties must read stored Phase 5 state and must not reconstruct or normalize
source semantics.

The corpus may expose deterministic record identities and source bindings;
separate present and not-recorded counts; exact detected, not-recorded,
unresolved, named-surface, admitted, and scored subsets; typed activity
filtering; and exact activity/ordinal and verse lookup. Detected means only
`presence == present`. It does not imply semantic admission. Admission does not
imply scoring. At this boundary the detected subset contains `17` records while
the admitted and scored subsets are both empty.

Missing lookup returns `None` without fallback. SLEEP ordinal `5` remains
absent, verse `250` remains the blocked classification conflict, and neither may
be repaired into a relation record. Invalid activity types, ordinals, verses,
containers, and member types fail explicitly. Derived collections are immutable
tuples and preserve canonical Phase 5 ordering.

Phase 6 adds no source truth, relation meaning, endpoint, direction, condition,
score, selector binding, runtime profile, manifest entry, package export,
facade method, REST route, prediction, diagnosis, advice, or medical-truth
claim. Its completion permits Phase 7 integrated-local-condition work only;
Phase 7 inherits no favorable/unfavorable or scoring doctrine. The Phase 6
decision SHA-256 is
`b175bcd1e537fb551cd26b18d6e6caa37f7a574b7e0a96b336d6fbb97eff9b12`.

## 5. Conflicts That Forbid Blending Or A Default

The following are different computational doctrines or unresolved editorial
defects, not values that may be averaged or repaired by symmetry.

| Area | Evidence | Required policy |
|---|---|---|
| Identity ontology | The 1879 opening uses query/name initials; later presentations use birth nakshatra and Moon paksha. | Never label the 1879 mapping as natal identity. |
| Amara nakshatra partition | The Bogamuni 2024 verse is complete while its adjacent commentary duplicates Shravana and omits Revati. | The named 2024 profile declares verse precedence and rejects the malformed commentary; never blend or repair the layers. |
| Duration vectors | The 1879 witness has one vector; later witnesses contain regime-specific or non-closing vectors. | Durations belong to the named witness and text layer. |
| Vinadi temporal selectors | The 2024 editorial witness separately names a weighted Sūkṣma selector and an equal-fifths Eka Sūkṣma selector; Uromarisi ordinal witnesses supply no arithmetic binding. | Preserve both named policies, select neither by default, and do not attach either to Uromarisi outcomes without an explicit cross-witness composition decision. |
| Ramadevar title identity | Catalogs separately identify `Panchapakshi`, `Patchini`, `Patchani 108`, and `Ashtanga Patchini` works under Ramadevar attribution. | Never merge by attribution, spelling similarity, or poem count; require exact manuscript identity and product-level content. |
| Schedule cells | A later edition contains a verse/commentary mismatch that duplicates one bird and omits another. | Fail the affected layer; do not infer the missing bird. |
| Relationships | The 1879 table is directed and nonuniform; later tables use different assignments. | No reciprocity, symmetry inference, or cross-witness merge. |
| Timing | The inspected 1879 source attests fixed thirty-nazhigai halves, not proportional sunrise-to-sunset scaling. | Seasonal scaling, if admitted, is a separate policy and capability. |
| Padu, first-EAT, and authority vocabulary | The Bogamuni weekday Padu table and the 1879 first-samam EAT seeds are separately complete; primary layers mention authority days without supplying an `Adhikara Pakshi` table, and Bharana is secondary-only terminology. | Preserve the Padu and first-samam EAT objects as separate source-scoped lookups. Do not manufacture an Adhikara/Bharana alias or derive a day ruler from either lookup or instantaneous Rule activity. |
| Vinadi ordinal routing | Uromarisi-attributed 1922, 1932, and 1934 publications attest first through fifth vinadi result positions beneath activities without arithmetic; the 2024 editorial comparator separately attests weighted and equal-fifths selectors. | Preserve the ordinal axis and both selector candidates. Stage 2N permits only its separately decided modern schedule composition; do not infer Uromarisi binding, choose a default, normalize prognostic prose, or attach outcomes. |
| Verse 250 parent activity | The heading and verse assign DIE ordinal 5 while the commentary assigns SLEEP ordinal 5. | Preserve all layers, block semantic normalization, and do not assign the candidate to either parent activity at runtime. |

Conflict-ledger witnesses and rejected text layers are not executable merely
because they are recorded. The named 2024 profile admits only its declared
governing verse and source mappings; Uromarisi evidence and the rejected
commentary do not silently broaden either public profile.

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

For the additive proportional current-cell capability, the profile must also
admit `solar_proportional_current_cell_selection`; the complete Stage 2D
materialization and caller-supplied paksha remain governing inputs; Stage 2A
solar-half ownership must be resolved before selection; and the requested
instant must be converted to reader-bound TT exactly once. Membership must use
exact half-open comparisons with `0.0 s` tolerance and produce exactly one
matching member of the materialization. The only lawful status is `selected`
and its current cell is non-null. Zero matches, overlaps, a foreign or copied
cell, an unmaterialized-tail status, fixed-clock mixing, fallback, clipping,
wrapping, repetition, borrowing, or paksha inference are errors.

For astronomical paksha inference, the profile must admit
`astronomical_paksha_inference` and contain exactly the source-owned
waxing/Purva/`n16` and waning/Amara/`n26` mappings. One finite UT1 instant must
produce one reader-bound TT used by both geocentric body evaluations.
Longitudes and normalized elongation must lie in `[0, 360)`; exact half-open
classification must agree with the astronomical enum, profile label, and its
single locator. Location, tolerance, snapping, ambient ayanamsa, schedule
selection, materialization, current-cell selection, automatic routing, and
natal identity are prohibited.

For the Stage 2G profile, `nakshatra_bird_mapping` must contain exactly one
entry for every `(purva|amara, 0..26)` pair, use canonical nakshatra names, and
resolve each cell to exactly one bird and one governing locator. The complete
Amara verse must govern while the malformed commentary remains rejected
conflict evidence. Natal identity requires the matching capability, exact fixed
policy, one reader-bound TT epoch, consistent tropical/ayanamsa/sidereal
longitudes, mathematically coherent half-open phase and nakshatra ownership,
one phase locator, and a nested mapping whose profile, Paksha, nakshatra, bird,
and provenance equal the direct identity fields. Schedule, current-cell,
scoring, and forecast claims are errors.

For the Stage 2H profile, `padu_bird_mapping` must contain exactly one entry for
every `(purva|amara, Sunday..Saturday)` pair and no day/night key. Every result
must equal the canonical profile cell, carry the three source locators for its
Paksha stanza plus the repeated combined table and commentary, retain the
declared stanza-precedence assembly policy, and report astronomical routing as
`not_performed`. Schedule inspection, `RULE`-activity conversion,
`first_eat_bird` relabelling, Adhikara/Bharana aliasing, natal identity,
current-cell selection, scoring, and forecasting are errors.

For the Stage 2I capability, the unchanged 1879 profile must contain exactly
one first-EAT seed for every `(purva|amara, day|night, Sunday..Saturday)`
combination. Every result must equal the canonical generator's weekday seed,
carry that generator ID and its complete ordered source-locator tuple, and
match both `PanchaPakshiSchedule.first_eat_bird` and the first samam's EAT
cell. Datetime or location routing, inferred Paksha, schedule materialization,
Padu or authority aliasing, whole-day semantics, natal identity, condition,
scoring, and forecasting are errors.

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

Stage 2E adds the separately governed kernel-backed
`pancha_pakshi_solar_proportional_current_cell_at(...)`,
`Moira.pancha_pakshi_solar_proportional_current_cell(...)`, and
`POST /v1/pancha-pakshi/schedule/solar-proportional/current-cell` surfaces.
They accept the same explicit profile, aware datetime or UT1 instant, location,
and caller-supplied paksha, plus only the named Stage 2E policy. The engine
result retains its complete governing Stage 2D materialization and returns the
requested TT witness, immutable selection policy, one non-null selected cell,
and transformed provenance. The compact REST result publishes the governing
bounds and selected cell without duplicating all 25 cells.

Stage 2F adds the separately governed kernel-backed
`pancha_pakshi_astronomical_paksha_at(...)`,
`Moira.pancha_pakshi_astronomical_paksha(...)`, and
`POST /v1/pancha-pakshi/context/astronomical-paksha` surfaces. The engine takes
an explicit profile and UT1 JD; facade and REST take an explicit profile and
aware datetime. The REST request also requires the exact Stage 2F policy ID.
No form accepts a location or caller-supplied paksha, and no inferred label is
passed to a schedule operation.

Stage 2G adds the kernel-free pure-table
`pancha_pakshi_nakshatra_bird_mapping(...)` and
`Moira.pancha_pakshi_nakshatra_bird_mapping(...)` surfaces, plus the
kernel-backed `pancha_pakshi_natal_moon_identity_at(...)`,
`Moira.pancha_pakshi_natal_moon_identity(...)`, and
`POST /v1/pancha-pakshi/identity/natal-moon` surfaces. The natal engine takes
an explicit profile and UT1 JD; facade and REST take an explicit profile and
aware datetime. REST additionally requires the exact Stage 2G policy ID. No
form accepts location, caller-supplied paksha/nakshatra/bird/ayanamsa,
schedule/current-cell controls, scoring, or forecast policy.

Stage 2H adds the kernel-free pure-table
`pancha_pakshi_padu_bird_mapping(...)`,
`Moira.pancha_pakshi_padu_bird_mapping(...)`, and
`POST /v1/pancha-pakshi/roles/padu` surfaces. Each accepts an explicit profile,
`profile_paksha`, and weekday only. No form accepts an instant, location,
day/night half, schedule, activity, natal identity, Adhikara/Bharana alias,
condition, score, or forecast input.

Stage 2I adds the kernel-free pure-table
`pancha_pakshi_first_eat_bird_mapping(...)`,
`Moira.pancha_pakshi_first_eat_bird_mapping(...)`, and
`POST /v1/pancha-pakshi/schedule/first-eat-bird` surfaces. Each accepts only an
explicit profile, `profile_paksha`, day/night half, and weekday. No form accepts
an instant, location, inferred Paksha, Padu or authority role, schedule
materialization, natal identity, condition, score, or forecast input.

All computations require `profile_id`. Public results are immutable and carry
profile-owned provenance and omissions. Exact nazhigai values remain rational
in the engine and serialize as `{numerator, denominator}` at the transport
boundary. The current family contains four profiles, seventeen `Moira` methods
(ten kernel-free and eight kernel-backed), and seventeen REST routes.

Stage 2F accepts a datetime but no location and performs only instantaneous
astronomical-paksha inference. The five location-bearing Stage 2A-E operations
all require explicit paksha. No operation accepts a caller-supplied natal-Moon
longitude, nakshatra, score, inferred name, sunrise, or timezone policy as an
override. Stage 2G alone computes natal-Moon identity from the supplied instant
under its fixed policy. The context operation returns
only the selected nominal schedule; the fixed-clock operation returns all
materialized half-open cell intervals and their solar-half topology without a
current-activity judgment; and the current-cell operation returns only the
unique cell under its named fixed-clock policy or the explicit unmaterialized
tail status. The proportional materialization operation separately maps exact
nominal fractions across the governing half, while its separately named
selector returns the unique current proportional cell. Neither proportional
operation borrows fixed-clock semantics. Stage 2H remains separate from every
temporal product: it performs one pure Padu-table lookup and never routes that
bird into a schedule, identity, condition, or forecast. Stage 2I likewise
returns only one named generator's first-samam EAT seed and never materializes
the schedule or promotes that seed into a whole-day or authority role.

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

The chained
[`Stage 2E admission decision`](../../tests/fixtures/pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json)
binds the unchanged profile hash, frozen Stage 2D decision and manifest, and
manifest-only addition of `solar_proportional_current_cell_selection`. It
records exact solar-half-first, half-open TT membership, selected-only/non-null
semantics, and unchanged Stage 2D omission provenance without presenting the
selector as source-attested doctrine or external current-cell parity.

The chained
[`Stage 2F admission decision`](../../tests/fixtures/pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20.json)
binds the frozen Stage 2E decision and prior manifest, the source-reading record
at SHA-256
`9ce3686a90a41af916a370b8d4ec04637f22a1d32f872180c6d8a1b790e25a0e`,
profile transition from
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`
to `4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`,
and manifest transition from
`d2b5f8f1ae7e067d257eeb24b533be1d33349446d56d361ea59f4a71472eca70`
to `a4fdceee4089c2812d9d77be763c1738152a63231b3f06847ea93383e4a3b327`.
The decision digest is
`1020b28d5da8d0e823cadd352ea2236c69cbb636660a573eb5d74b8c131bc5d8`.
It records both the source-scoped mapping and the distinct modern numeric
boundary policy without raising admission above `source_scoped_public`.

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

Stage 2E validation reconstructs and verifies the frozen Stage 2D manifest,
then proves exact selection at all 25 cell midpoints, the anchor, all 24 shared
endpoints, immediately preceding representable instants, and the excluded
old-half endpoint under solar-half-first precedence. It checks representative
long and short day and night halves, zero-tolerance TT membership, exactly one
non-null materialization member, immutable policy/provenance binding,
capability gates, strict facade/transport admission, and fail-closed rejection
of gaps, overlaps, copied cells, tail states, fixed-clock mixing, and inference.
DE441 exercises the reader-bound TT/UT1 path; it is not an external Pancha
Pakshi current-cell oracle or new historical-accuracy claim.

Stage 2F validation verifies both direct mapping locators, schema/hash/admission
chain, exact `0` and `180`-degree ownership, normalized `360` behavior,
immediately adjacent representable values, one UT1-to-TT conversion shared by
both body evaluations, source-label and locator consistency, immutable vessels,
capability gates, and strict facade/REST input and response shapes. DE441
exercises the reader-bound astronomical path; synthetic boundary and Panchanga
coherence tests establish the declared partition. No external Pancha Pakshi
oracle, phase-event timing accuracy, independent witness, or universal canon is
claimed.

Stage 2G validation separately verifies the Bogamuni leaf `n52` Purva mapping,
leaf `n64` governing Amara verse and rejected commentary conflict, leaf `n167`
phase binding, all 54 exact mapping cells, profile/manifest hash integrity,
capability separation, immutable source and composition vessels, and strict
facade/REST/OpenAPI contracts. Mathematical invariants test all exact
nakshatra boundaries and their adjacent representable values. A discovered,
content-identified DE441 kernel exercises the apparent geocentric and
reader-bound TT execution path. These are respectively source-table evidence,
mathematical boundary evidence, and astronomical execution evidence; none is
an external natal-identity oracle or a universal-canon proof.

Stage 2H validation separately verifies the Bogamuni `n52` and `n60` governing
Paksha stanzas, the `n157` and `n158` internal repetitions, all fourteen exact
Paksha-by-weekday cells, profile/manifest/decision hash integrity, immutable
provenance, capability isolation, and strict facade/REST/OpenAPI contracts.
Adversarial checks reject a day/night dimension, foreign locators, incomplete
or duplicated cells, forged birds, `RULE` equivalence, `first_eat_bird` or
Adhikara/Bharana relabelling, and temporal or scoring fields. These are
source-table and structural-contract evidence, not an external condition,
electional, or forecasting oracle.

The chained
[`Stage 2I admission decision`](../../tests/fixtures/pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20.json)
binds the unchanged 1879 profile at SHA-256
`4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`,
the frozen Stage 2H decision at SHA-256
`9ea7c871643bb8fc68d420223d0090ca91699154c761c67ccaf9201f401906cd`,
and the manifest transition from
`eae9fc471da08eccf24515ef12cdaf59330aa1b7ad7f9d43432c7a1482704a03`
to `d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8`.
Its decision digest is
`83c9bc0a423c09ccc113007625fee4a7d6b9ee1e890827f71595c96c3f826807`.
Stage 2I validation checks all 28 cells, the four governing 1879 leaves,
same-witness locator retention, parity with the existing nominal schedule's
first-EAT field and initial EAT cell, immutable canonical provenance,
capability isolation, and strict facade/REST/OpenAPI shapes. Uromarisi 1934 is
recorded only as separate-publication corroboration with unestablished textual
lineage independence; it supplies no runtime cell or universal-canon proof.

The
[`Stage 2J research decision`](../../tests/fixtures/pancha_pakshi_uromarisi_vinadi_stage2j_research_2026_07_21.json)
has canonical SHA-256
`d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243`.
It binds the unchanged Stage 2I manifest and decision, four inspected PDF
hashes and exact page locators, the recovered five-position ordinal axis, the
two exact rational selector candidates, and the fail-closed no-default and
no-cross-witness-binding policy. Its regression tests also prove that no
vinadi token entered the manifest, package exports, facade, or REST routes.
This is source-specific structural and policy-conflict research evidence, not
translation authority, external prognostic parity, or public admission.

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
tests: source-attested or alternate solar-proportional doctrines and any
selectors belonging to those unadmitted doctrines; alternate Padu doctrines;
Bharana or Adhikara bird products; alternate Sookshma selector doctrines,
any cross-witness binding of Stage 2K selectors to Uromarisi ordinal outcomes,
vinadi clock routing, and semantic outcome products beyond the Stage 2J axis,
Stage 2P research-only illness locator grid, Stage 2Q five-cell EAT pilot,
Stage 2R five-cell WALK extension, Stage 2S five-cell RULE extension, and Stage
2T four-cell SLEEP extension with verse `250` blocked by identity conflict;
condition/scoring; and electional window search.
Fixed-clock materialization, fixed-clock current-cell selection,
solar-proportional materialization, and solar-proportional current-cell
selection are admitted only through their explicit Stage 2B, Stage 2C, Stage
2D, and Stage 2E policies and surfaces above; none may be inferred from the
source-scoped profile or from the Stage 2A local-solar context alone.
Astronomical paksha inference is admitted only through the separate Stage 2F
policy and never supplies paksha to those operations automatically. Natal-Moon
identity is admitted only through the separate Stage 2G Bogamuni profile and
fixed modern composition; alternate natal doctrines remain separate future
profiles rather than overrides to this one. Padu-bird lookup is admitted only
through the separate Stage 2H profile and its explicit Paksha-by-weekday table;
it does not supply any schedule, identity, Adhikara/Bharana alias, condition,
score, or forecast.
First-samam EAT lookup is admitted only through the Stage 2I capability on the
1879 profile. It does not materialize a schedule or supply an ambient eating,
Padu, authority, Adhikara/Bharana, condition, score, or forecast role.
