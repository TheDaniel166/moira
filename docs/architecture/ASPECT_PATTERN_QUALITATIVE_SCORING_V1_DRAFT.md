# Aspect-pattern qualitative scoring — v1 draft

Date: 2026-09-12

Status: proposed scoring doctrine, not implemented or deployed.

Policy identifier: `moira.pattern_coherence.qualitative.v1-draft`.

## Purpose

Describe how closely an already-detected aspect pattern holds together, and
preserve the instantaneous motion of its required relationships. Present a
qualitative result such as **Strong · Mixed motion**, not a percentage or a
chart-wide verdict.

Here, "strength" means geometric coherence under this named convention. It
does not mean beneficial, harmful, psychologically dominant, physically
powerful, or proven to predict an outcome. The thresholds below are proposed
policy choices, not a recovered traditional doctrine or a calibrated natural
law.

Planetary phase is excluded. There are no illumination, solar-condition,
dignity, planet-importance, apex, or body-count bonuses.

## 1. Two-part result

1. **Coherence band:** determined by the loosest required aspect relative to
   a fixed reference orb.
2. **Motion qualifier:** describes applying, exact, separating, stationary,
   or unavailable motion without changing the coherence band.

This is the initial meaning of motion as a secondary modifier: a qualifier,
not an invented numerical bonus or penalty. A separating near-exact pattern
does not lose its geometric strength merely because it has passed exactness.

Retain each contributing aspect's orb and motion state so the explanation is
auditable. Do not expose an unexplained composite number.

## 2. Scope and admission

Scoring consumes an existing detector result. It must not admit a new pattern,
widen a detector's orb, change its body membership, resurrect hidden points,
or reinterpret a detector's definition.

Initial admission covers these six same-chart, degree-based zodiacal patterns:

| Pattern | Required relationships |
| --- | --- |
| T-Square | One opposition and two squares |
| Grand Trine | Three trines |
| Grand Cross | Two oppositions and four squares |
| Yod | One sextile and two quincunxes |
| Mystic Rectangle | Two oppositions, two trines, and two sextiles |
| Kite | Three trines, two sextiles, and one opposition |

The actual body-to-body edge identities must come from the matched detector
template; these counts alone do not identify a valid pattern.

Other aspect-pattern templates can enter only after their required links are
explicitly mapped and checked against their detector. In particular, a Grand
Sextile preserves optional trines and oppositions in addition to its required
six-sextile ring. A flat list of all contributing aspects is not universally
the list of required links.

Sign/house/tight stelliums, categorical whole-sign aspects, declination
patterns, cross-chart patterns, and three-dimensional sky-separation patterns
are not assessed by this draft. They need their own definitions. Do not reuse
the categorical whole-sign `exactness = 1` value as geometric perfection.

Use positions and speeds for the same instant and declared frame/timescale.
The initial astronomical product is geocentric ecliptic longitude, with its
apparent/geometric regime recorded. Do not combine incompatible snapshots or
invent motion for fixed chart points whose rates are unavailable.

## 3. Fixed scoring reference orbs

These values are frozen for this draft, based on the relevant existing
canonical aspect definitions in `moira/constants.py`. They are scoring
references, not new detector admission ceilings.

| Aspect | Reference orb B |
| --- | --- |
| Opposition | 8 degrees |
| Square | 7 degrees |
| Trine | 7 degrees |
| Sextile | 5 degrees |
| Quincunx | 3 degrees |

For each unique required aspect:

`reference_orb_use = actual_orb / reference_orb`

Use the preserved full-precision angular deviation, not rounded display text.
The v1 reference must not track a user's display/detection orb multiplier or
silently follow later changes to engine defaults. Changing this scoring table
requires a new policy version.

A wider detection setting may admit another pattern, but cannot improve the
score of the same pattern with the same geometry. If an admitted required
aspect exceeds its scoring reference, retain its actual ratio, classify it as
Marginal, and explain that it exceeds the fixed scoring reference. Do not
silently discard or clip that evidence.

## 4. Coherence bands and aggregation

Let `R` be the largest `reference_orb_use` among the required aspects.

| R | Pattern coherence | Plain-language meaning |
| --- | --- | --- |
| 0 through 0.10 | Very strong | Every required relationship is very close to exact |
| Greater than 0.10 through 0.25 | Strong | Every required relationship is close to exact |
| Greater than 0.25 through 0.50 | Moderate | The pattern holds together with noticeable angular spread |
| Greater than 0.50 through 0.75 | Loose | At least one required relationship is broad |
| Greater than 0.75 | Marginal | At least one required relationship is near or beyond its reference limit |

Boundary values belong to the tighter band. Compare unrounded values; do not
round a result across a boundary. Exactness remains a separately reported
engine state, not another orb band or an extra scoring bonus.

This is a weakest-required-link aggregation, not an average or a sum. All
required links must meet a band for the whole pattern to receive that band.
An exact opposition cannot conceal two broad squares in a T-Square. More
bodies or edges provide no automatic bonus; equally tight required links
produce the same band in differently sized patterns.

This deliberately does not estimate the total amount of "influence" in a
larger pattern. It also does not claim that equal bands in different pattern
families imply equal importance or effects.

Count an edge once per pattern by its canonical body pair, aspect identity,
and measurement domain. Duplicate contributions must not create extra weight;
conflicting duplicates are invalid input. Supplemental relationships remain
separate context and cannot rescue or weaken the required-link rating.

Show the limiting aspect or aspects and the full required-link ledger. Two
patterns can share a band while having different internal distributions; the
band is intentionally a summary, not a replacement for those details.

## 5. Motion qualifier

Use Moira's preserved instantaneous motion state, preferably the signed
motion witness when source longitudes and speeds are available. Preserve
exact/stationary tolerances and provenance. A scorer must not apply its own
alternative definition or derive exactness from a displayed `0°00′`.

After validating a complete required-link geometry set, evaluate these rules
in order:

| Condition | Qualifier |
| --- | --- |
| All required states are indeterminate | Motion unavailable |
| Some, but not all, required states are indeterminate | Partial motion |
| Any required state is stationary | Station-sensitive |
| All required states are exact | Exact |
| All required states are applying | Applying |
| All required states are separating | Separating |
| Any other complete combination of applying/exact/separating | Mixed motion |

Always retain counts of every state. For example, **Mixed motion** can be
explained as "2 applying · 1 exact" or "1 applying · 2 separating". For partial
motion, retain any known stationary information as well.

"Station-sensitive" does not mean that the whole pattern has stopped: Moira
can report a stationary aspect when either participating body meets its
station threshold, even when their relative angular rate is nonzero.

These qualifiers describe the links at the supplied instant. They do not
guarantee that an applying aspect will perfect, predict a future pattern-wide
peak, or establish a single aggregate tightening rate. Mixed configurations
must not be forced into a single applying/separating label by majority vote.

Do not rank the motion qualifiers as another universal strength ladder.
Introducing such a ranking would be a separate, explicit policy change.

## 6. Missing information and explanations

- Missing motion does not erase a valid geometric band or count as weakness.
- Missing any required edge's geometry, invalid numeric values, conflicting
  edge identities, or incompatible source frames prevent a whole-pattern
  band. Report **Not assessed** and a specific reason; preserve valid details.
- An unsupported template/domain is **Not assessed**, not Marginal.
- Empty required-link sets are not Very strong or Exact.
- Hidden or unavailable chart factors stay absent; the scorer does not
  change the upstream eligibility policy.
- Patterns sharing an aspect retain their own local assessments. Do not add
  their grades together into a chart-wide strength score.

Suggested compact presentation:

> T-Square — Strong · Mixed motion
>
> All three required aspects are within the inner quarter of their fixed
> reference orbs. Limiting relationship: Sun opposite Jupiter, orb 2°00′.
> Motion: 1 applying · 2 separating.

Only show such an example as an actual result when its underlying geometry
and motion evidence support it. Keep the policy identifier and numerical
derivation in inspectable details, not a permanent wall of technical text.

## 7. Source-grounded examples

These are synthetic longitude configurations, not ephemeris observations or
astrological outcome validation. Use Sun at 0 degrees, Mars at the listed
longitude, and Jupiter at the listed longitude to obtain a T-Square.

| Mars | Jupiter | Square orbs | Opposition orb | R | Band |
| --- | --- | --- | --- | --- | --- |
| 90.3 | 180.6 | 0.3, 0.3 degrees | 0.6 degrees | 0.075 | Very strong |
| 91 | 182 | 1, 1 degrees | 2 degrees | 0.25 | Strong |
| 92 | 184 | 2, 2 degrees | 4 degrees | 0.50 | Moderate |
| 93 | 186 | 3, 3 degrees | 6 degrees | 0.75 | Loose |
| 94 | 188 | 4, 4 degrees | 8 degrees | 1.00 | Marginal |
| 96 | 180 | 6, 6 degrees | 0 degrees | 6/7 | Marginal |

For the first configuration, synthetic daily longitude speeds of Sun +1,
Mars +0.5, and Jupiter -0.1 degrees/day yield Applying on all three links.
Reflecting its offsets to Mars 89.7 and Jupiter 179.4 with those same speeds
yields Separating on all three links, without changing the coherence band.

No measurement of real-world influence follows from these synthetic checks.

## 8. Implementation boundary and acceptance requirements

Current engine source already provides aspect orbs, allowed orbs, signed
motion witnesses, and pattern contribution records. Its existing
`PatternConditionProfile` labels are structural classifications, not this
qualitative scoring system. Do not relabel or repurpose them silently.

Authoritative evidence is in `moira/aspects.py` (`aspect_strength`,
`aspect_motion_witness`), `moira/patterns.py` (`AspectPattern`, the six admitted
detectors, and `find_grand_sextiles`), and `moira/constants.py` (`Aspect`).

Before runtime implementation is called complete, require tests for:

1. All band boundaries, immediately above/below them, and unrounded input.
2. Frozen-reference behavior under changing admission/display orb settings.
3. All six admitted templates and required versus supplemental edge mapping.
4. Weak-link limiting, duplicate/order invariance, and no body-count bonus.
5. All motion qualifier rules, exact contacts, partial/missing speeds, and
   stationary body versus stalled relative-motion cases.
6. Reversing motion without changing the geometric band; no prediction of
   future perfection from an instantaneous applying state.
7. Incompatible frames, missing geometry, unsupported domains/templates,
   non-finite inputs, empty edge sets, and out-of-reference but admitted links.
8. Hidden-factor filtering, unchanged detector membership, and no stellar,
   planetary-phase, dignity, apex, or body-importance weighting.

This document does not add runtime functions, public API fields, UI controls,
or a release. Numerical thresholds and the conservative weakest-link rule
remain reviewable draft policy until explicitly adopted.

## 9. Draft verification receipt

On 2026-09-12, a one-off inline probe run with
`.\.venv\Scripts\python.exe -c` (Python 3.14.3) passed 47 assertions against
engine source `29dd164c80c2a6788aa598a832eff3d4fd8e727a`:

- The five frozen reference orbs match the current canonical definitions.
- Each band cut and its immediately adjacent representable values follow
  the specified inclusion rule.
- All six T-Square geometry examples produce their stated bands.
- All seven motion qualifiers are exercised using engine motion witnesses;
  the corresponding very-close geometries retain their coherence band.
- Exact examples of the six initially admitted templates contain the stated
  contributing aspect types/counts and receive the same geometric band.
- Doubling detection orbs leaves the same pattern's score unchanged; a
  separately admitted out-of-reference example remains Marginal.

The probe used existing `find_aspects`, `find_all_patterns`, and
`aspect_motion_witness` with synthetic positions/speeds. It needed no kernel,
used no downloads, and changed no runtime source. This is source-contract and
policy-arithmetic evidence, not the future scorer's full acceptance suite,
ephemeris accuracy evidence, a production check, or outcome validation.
