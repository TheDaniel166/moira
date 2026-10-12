# Source-defined Chara and Argala profiles

Date: 12 October 2026. Owners: `moira.chara_profiles`,
`moira.argala_assessment`, `moira.jaimini_profile_policy`. Package: VED-013.
See the [source packet](../06_roadmap/VEDIC_CHARA_ARGALA_SOURCE_RESEARCH_2026-10-12.md),
[decisions and implementation plan](../06_roadmap/VEDIC_CHARA_ARGALA_IMPLEMENTATION_PLAN_2026-10-12.md)
and [validation receipt](../03_validation/VEDIC_CHARA_ARGALA_VALIDATION_2026-10-12.md).

## Discovery and input precision

`list_jaimini_profiles()` identifies six executable bounded profiles, two legacy
operations and five research-only candidates. Each record includes its source
rules, required inputs, capabilities, limitations and applicable conflicts.
`research_required` is not an executable selector.

`JaiminiChart(basis, positions, lagna)` snapshots a body map into an immutable
canonical tuple. `basis='signs'` requires actual integers 0-11.
`basis='sidereal_longitudes'` requires finite Python numbers in `[0,360)`.
Booleans, numeric strings, nonfinite values, missing/extra bodies and mixed
representations fail. No degree is invented for a sign-only chart. These are
caller-supplied sidereal inputs; no ayanamsa, birth time or ephemeris is inferred.

Chara requires exactly the seven classical planets. Argala requires all nine
including both nodes. New Argala references are explicit Lagna, house 1-12 or
named planet; one to twenty-two distinct identities are admitted and ordered
canonically. A node and its occupied house remain different references.

## Chara arithmetic

The three profile IDs are:

- `rangacharya_2007_method1_classical7_v1`
- `rangacharya_2007_method2_male_classical7_v1`
- `rangacharya_2007_female_prose_classical7_v1`

They implement the manual's separate seed, sequence, counting direction and
duration rules. Callers select a recipe; demographic information does not.
Source authority is the 2007 manual, not an independently collated older
commentary implied by a lineage label.

`evaluate_chara_profile(chart, profile_id=..., projection=None)` returns twelve
arithmetic rows, each with lord/count/exception/dignity witnesses and cumulative
integer years. Method 1 gives own-sign twelve before dignity adjustments and
retains a zero-year result. The female recipe selects the own-sign prose rule
over the example's conflicting Cancer ten; C04 records both values.

`CharaProjection(epoch_jd)` explicitly selects
`moira_fixed_365_25_day_projection_v1`. This Moira engineering convention maps
cumulative source years to caller-owned JD with 365.25 days per year. It is not
an ancient or tropical-solar calendar attribution. Positive intervals are
half-open and reference their arithmetic row; zero rows remain in arithmetic
and are listed as unscheduled. Nonrepresentable positive spans fail.
No antardashas, node co-lords or second cycle are admitted for these recipes.

## Argala profiles and component separation

`assess_argala(chart, profile_id=..., references=...)` preserves formation,
count, character, obstruction qualification and effective assessment separately.

| Profile | Selected coverage |
| --- | --- |
| `bphs_santhanam_31_literal_assessment_v1` | Four pairs; none/limited/medium/excellent count grades; node-reference reversal; three-malefic special third; directed quarter qualification |
| `pvr_2000_argala_count_first_v1` | Four pairs; Ketu-occupied-reference reversal; unequal counts decide, equal counts require an unadmitted strength comparison |
| `rath_argala_article_assessment_v1` | Nine-body subset; six pairs including 8/6 and 7/1; Ketu reversal; own-sign and Jupiter rasi-aspect factor witnesses |

BPHS's greater-causer-count alternative is independent of strength. When that
does not decide, the literal quarter component permits only Q1/Q4 and Q2/Q3
directed causer/blocker pairs, each quarter spanning 7.5 degrees. No qualifying
pair leaves the intervention unobstructed; all-qualified pairs still require
strength, and mixed matrices preserve unresolved aggregation. Missing degrees
are explicit. No epsilon moves a binary input between half-open partitions.

PVR's count priority is not imported into BPHS. Rath factors are not an invented
numeric or lexicographic ranking. In its standard nativity, Jupiter in Pisces
casts rasi aspects to both Gemini and Sagittarius; C12 preserves the source's
winner separately from these symmetric factor witnesses. Empty signs and
upagrahas are outside this bounded planetary intervention profile.

No universal strength comparator is admitted. Equal counts/factors do not
establish equal strength, and the current result enum does not manufacture a
`balanced` outcome. Exact reason codes distinguish missing degrees, unavailable
strength, mixed quarter aggregation and unspecified factor priority. Neither
unknown nor not-assessed becomes false, zero or a deleted response row.

The separate character component is
`bphs_santhanam_3_11_root_same_sign_v1`. It includes nine-body natural character,
Moon bright/dark half and Mercury's same-sign malefic association. Its explicit
elongation intervals are `[0,180)` and `[180,360)`. Sign-only Moon phase remains
unknown; Mercury and group/special-third uncertainty are propagated. This
root-verse composition does not claim the translator's additional Moon relief
or Rangacharya's contextual Venus treatment. BPHS's special-third result
coexists with the raw third-house blocker role and preserves its distinct
source-described favourable effect.

## REST and compatibility

`GET /v1/jaimini/extended/profiles` exposes discovery.
`POST /v1/jaimini/extended/chara-dasha/profile` and
`POST /v1/jaimini/extended/argala/assessment` accept one explicit profile per
request and discriminated sign/longitude charts. Projection, when requested,
requires its explicit ID in JSON. Requests forbid unknown fields, custom scores,
unsupported cycles/antardashas and research-only selectors. Models expose bounded
identities and uncertainty through OpenAPI. HTTP invalid inputs return 422;
corrupt result invariants are internal failures, not client validation failures.

Module, root, Vedic namespace, facade methods and REST use the same owners.
Serialization adds derived counts but recomputes no source decision. All source
evidence is returned; there is no evidence-hiding response filter.

The [legacy Chara operation](CHARA_DASHA_CYCLE_STANDARD.md) retains its original
one/two cycles and antardashas. Legacy `argala` retains valid arithmetic, seven
occupants, two-malefic special threshold and optional empty/partial node maps.
Its direct API now rejects boolean Lagna/nodes, nonfinite nodes and unknown node
keys like REST. Its corrected lineage and additive `ArgalaComputation` identify
the retained Moira convention. Legacy manual positional construction remains
valid with `computation=None`; engine calls always return the receipt.

## Remaining admissions

Full BPHS Chara, PVR 2014 Chara, Rath Narayana, Rangacharya Yogada and general
Argala strength resolution retain their concrete gates in discovery and the
work register. The selected local package is complete only with its validation
receipt; source publication, release and deployment are separate events.
