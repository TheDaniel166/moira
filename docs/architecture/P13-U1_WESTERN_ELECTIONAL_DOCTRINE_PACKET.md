# P13-U1 Western Electional Doctrine Packet

Version: 0.1
Date: 2026-07-14
Status: doctrine_packet_draft; first profile defined; runtime admission blocked
Scope: Western electional doctrine above the admitted bounded search transport

## 1. Doctrine Decision

Moira may develop Western electional judgement only through named, versioned,
source-owned profiles. A profile must bind its lineage, computational policies,
rule meanings, variants, and public language explicitly.

The existing electional search surface remains generic infrastructure. It may
scan chart states, merge qualifying scan points into windows, and attach a
declared numeric transport score. It does not become Western electional
doctrine merely because a future profile uses it.

This packet defines the first bounded doctrine candidate:

`ramesey_moon_condition_v1`

It is a transparent evaluation of William Ramesey's ten impediments of the
Moon in *Astrologia Restaurata*, Book III, Chapter II, printed p. 127. It is
not a complete election, a recommendation, an auspiciousness score, or a
substitute for matter-specific judgement.

No runtime or REST admission is authorized by this packet. The unresolved
policies in section 8 must be closed and the validation gates in section 13
must pass first.

## 2. Authority and Page Confirmation

### 2.1 Governing witness

Primary authority for `ramesey_moon_condition_v1`:

- William Ramesey, *Astrologia Restaurata; or, Astrologie Restored* (London,
  1654), Book III, Chapter II, printed pp. 126-127.
- Original facsimile witness: [Internet Archive item
  `b30323149_0001`](https://archive.org/download/b30323149_0001/b30323149_0001.pdf),
  PDF pages 184-185 in the downloaded scan.
- Printed p. 126 supplies the chapter title and context.
- Printed p. 127 supplies the complete ten-item Moon-impediment list and the
  immediate remedy language.
- [Christopher Warnock's
  transcription](https://www.renaissanceastrology.com/electionalrameseymoon.html)
  is a readable secondary witness, not the governing facsimile.

Page confirmation performed 2026-07-14 by rendering and visually inspecting
the original facsimile pages. The profile below follows the printed list rather
than the earlier Ramesey/Robson synthesis in the research dossier.

### 2.2 Named comparison witnesses

These sources corroborate the rule family but do not silently modify the
Ramesey profile:

- Sahl bin Bishr, *On Elections*, §22, in Benjamin Dykes, *Choices &
  Inceptions*, printed pp. 99-101, PDF pages 115-117. Visually confirmed
  2026-07-14.
- Dorotheus of Sidon, *Carmen Astrologicum*, Book V.6, in the Dykes
  ʿUmar al-Ṭabarī translation, printed pp. 234-235, PDF pages 252-253.
  Visually confirmed 2026-07-14.

Sahl and Dorotheus preserve different thresholds, rule groupings, and
language. They require their own future profiles.

## 3. Governing Objects

### 3.1 `WesternElectionalProfile`

A future profile vessel must declare at least:

- stable `profile_id` and `profile_version`
- lineage and bibliographic authority
- election class
- supported matter scope
- ordered rule definitions
- all bound computational policies
- required astronomical and chart inputs
- output and public-language policy
- validation receipt and profile status

Profiles are data-backed doctrine owned by Moira. They are not arbitrary
caller expressions or executable code supplied over REST.

### 3.2 `WesternElectionalEvaluation`

A future evaluation vessel must preserve:

- evaluated Julian day and chart-construction provenance
- profile identity and version
- election class and matter scope
- one witness per rule
- whether each rule is `clear`, `triggered`, or `not_evaluable`
- the exact measured value and threshold where numeric
- the named policy used for every ambiguous computation
- separate mitigations or remedies
- an overall status derived without hidden weights

For the first profile, the lawful overall statuses are:

- `clear_of_profile_impediments`
- `one_or_more_profile_impediments`
- `indeterminate`

`indeterminate` is required if a profile rule cannot be evaluated under its
declared policy. Missing inputs must never be treated as a clear rule.

## 4. Rule Vocabulary and Assembly Doctrine

The doctrine layer uses these distinct objects:

- **Gate**: a source-defined condition that is either clear, triggered, or not
  evaluable.
- **Modifier**: source language that changes severity or interpretation but
  does not create a second hidden gate.
- **Mitigation**: a source-defined condition that may temper a triggered gate.
- **Remedy**: a source-defined alternative arrangement when the original gate
  cannot be avoided. It does not erase the triggering witness.
- **Context requirement**: an input such as matter type, nativity, house
  policy, or location required before a rule can be judged.
- **Witness**: the visible derivation for one rule, including inputs, policy,
  measurement, threshold, and result.

The result is assembled by rule identity, never by legacy array position. A
profile's source order remains visible for citation and explanation, but order
does not imply numeric weight.

## 5. Election Classes

The doctrine layer preserves three classes:

- `ephemeral`: evaluates a chosen moment without a natal root.
- `radical`: requires a nativity or another declared root and evaluates the
  election in relation to it.
- `mundane`: evaluates a public or collective inception under its own declared
  significators and scope.

`ramesey_moon_condition_v1` is an `ephemeral` condition profile. This means
only that its ten Moon rules can be evaluated at an event moment. It does not
assert that every Ramesey election is complete without a nativity, nor does it
override Sahl's rootedness doctrine in §§1-9.

## 6. Public Meaning and Language

Allowed public descriptions for the first profile:

- `Moon-condition profile`
- `profile rule triggered`
- `profile rule clear`
- `not evaluable under the selected policy`
- `measured value`
- `source-defined threshold`
- `clear of these ten profile impediments`

Forbidden unless a later packet separately admits them:

- `best time`
- `good election` or `bad election`
- `auspicious` or `inauspicious`
- `recommended`
- `guaranteed outcome`
- `complete Western electional judgement`
- an unlabeled composite score

The historical source may be quoted or paraphrased in a citation field, but
the API must not convert its claims into modern factual guarantees.

## 7. First Profile: `ramesey_moon_condition_v1`

### 7.1 Scope

The profile evaluates the ten impediments in Ramesey's printed order. Several
items are compound rules. Their internal clauses must remain visible; they may
not be split, dropped, or rearranged merely to resemble a later checklist.

The profile has no numeric total and no rank. Overall status is the transparent
logical summary described in section 3.2.

### 7.2 Source-faithful rule map

| # | Stable rule id | Ramesey rule | Required computation | Admission state |
|---|---|---|---|---|
| 1 | `moon_combust_sun_12deg` | Moon within 12° of the Sun, applying or separating; applying is more afflicted | shortest geocentric ecliptic Sun-Moon separation; applying/separating state; inclusive 12° boundary | Defined |
| 2 | `moon_in_third_degree_scorpio` | Moon in the degree of her fall, the third degree of Scorpio | zodiac sign and an explicit ordinal-degree interval policy | Policy unresolved |
| 3 | `moon_opposition_sun` | Moon in opposition to the Sun | opposition detection under a named aspect/orb policy | Orb policy unresolved |
| 4 | `moon_joined_or_hard_aspect_malefic` | Moon joined with an infortune, or in quartile or opposition to one | Moon conjunction, square, or opposition with Saturn or Mars under a named orb policy | Orb policy unresolved |
| 5 | `moon_near_lunar_node_12deg` | Moon within 12° of the Head or Tail of the Dragon | lunar-node longitude model and shortest longitudinal separation; inclusive 12° boundary | Node model unresolved |
| 6 | `moon_latter_degrees_with_infortune` | Moon in the latter degrees of a sign wherein there is an infortune | latter-degree boundary; same-sign malefic presence; malefic identity | Boundary unresolved |
| 7 | `moon_cadent_or_via_combusta` | Moon cadent from angles **or** in the last 15° of Libra / first 15° of Scorpio | house/angle policy plus tropical longitude interval; preserve the source OR | House policy unresolved; zodiac interval defined |
| 8 | `moon_detriment_or_not_beholding_cancer` | Moon in Capricorn, or quartile to her own house, or not beholding it by sextile or trine | tropical sign; explicit sign/degree aspect scope for Cancer; preserve the source OR | Aspect scope unresolved |
| 9 | `moon_slow_below_ramesey_mean` | Moon moves less than 13°10′36″ in 24 hours | declared geocentric ecliptic speed product; strict less-than threshold | Numeric threshold defined; speed product must be bound |
| 10 | `moon_void_ramesey_sign_bound` | Moon in a sign and beholds no planet until entering another sign | forward aspect search, planet/aspect set, sign boundary, and explicit meaning of “beholds” | Perfection doctrine unresolved |

### 7.3 Numeric boundary doctrine already established

The first profile binds only what the primary page states plainly:

- Rule 1 uses an inclusive 12° angular boundary because Ramesey includes the
  Moon “even when” twelve degrees distant.
- Rule 5 likewise uses an inclusive 12° boundary once the node model is
  selected.
- Rule 7's via-combusta interval is the final 15° of Libra through the first
  15° of Scorpio. A future implementation must declare endpoint convention;
  the recommended half-open encoding is `[Libra 15°, Scorpio 15°)`.
- Rule 9 triggers only below 13°10′36″ per 24 hours, numerically
  `13.1766666667°/day`; equality is clear because the source says “less then.”

The packet does not infer a 12° orb for Rule 3. That value entered the prior
dossier through a Ramesey/Robson synthesis, not Ramesey's printed item.

### 7.4 Directional and severity modifiers

- Rule 1 records `applying` as more afflicted than `separating`.
- Rule 7 records Ramesey's statement that the via-combusta condition is the
  worst impediment, especially for marriage, matters concerning women,
  buying, selling, and travel. This is source metadata, not a numeric weight.
- No other relative weight is admitted.

### 7.5 Immediate remedy witness

Ramesey follows the list with mitigation/remedy instructions. These are not
part of the ten-rule clear/triggered total and must remain separate witnesses.
At minimum, future research must model his instruction for an unavoidable
impeded Moon separately from the profile's gate results. The profile must not
silently flip a triggered rule to clear because a remedy is present.

## 8. Unresolved Policies Blocking Runtime Admission

The following decisions require direct source derivation or an explicitly
named Moira policy before `ramesey_moon_condition_v1` can be implemented:

1. **Third-degree convention**: whether “third degree of Scorpio” is encoded
   as the ordinal interval `[2°, 3°)` or as another historical convention.
2. **Ramesey aspect orbs**: the admissible orb and application doctrine for
   opposition, conjunction, square, and the house-beholding clauses.
3. **Node model**: mean node, true node, or another historically justified
   dragon-head/tail product; the public result must name it.
4. **Latter degrees**: the exact boundary and the meaning of “wherein there is
   an infortune” in Rule 6.
5. **Cadency policy**: house system, angle ownership, and whether cadency is
   whole-house, quadrant, or another source-owned concept.
6. **Beholding Cancer**: whole-sign versus degree/orb aspect scope for Rule 8.
7. **Speed product**: the exact frame, correction regime, sampling/derivative
   method, and sign convention used for lunar daily motion.
8. **Ramesey void**: whether “beholds not any Planet” means no exact perfection,
   no in-orb application, or another sign-bounded condition; also define the
   planet and aspect sets.
9. **Endpoint policy**: confirm the via-combusta boundary behavior at exactly
   15° Libra and 15° Scorpio.

Until these are bound, affected rules return `not_evaluable`; no ambient
library default may fill the gap.

## 9. Named Lineage Variants

These variants are separate profile parameters, not choices to average:

1. Void of course: Hellenistic 30°; medieval sign-bounded; Lilly moiety;
   modern Ward-orb; Ramesey wording requires its own confirmed binding.
2. Moon/Sun condition: Ramesey 12° Moon-specific combustion; Sahl 12° burned
   before/after; Dorotheus under-rays language without a numeric orb in V.6.4;
   general planetary combustion/under-beams/cazimi systems remain separate.
3. Via combusta: Ramesey 15° Libra to 15° Scorpio; Sahl “end of Libra and
   beginning of Scorpio”; Dorotheus V.6.12 names Libra and Scorpio.
4. Slow Moon: Ramesey 13°10′36″; Robson 13°11′; Sahl and Dorotheus 12°.
5. Lunar-node proximity: Ramesey and Sahl 12°; Dorotheus uses materially
   different latitude/node language.
6. Aspect scope and orbs: whole-sign, degree-based, and moiety-based doctrines
   remain named and source-owned.
7. Terms/bounds: Egyptian and Ptolemaic schemes remain separate.
8. Election class/rootedness: ephemeral, radical, and mundane remain explicit.

## 10. Separation from Search Transport

A future doctrine implementation may supply a server-owned predicate adapter
to the admitted bounded search engine only after the profile itself is
admitted. The layers remain:

1. astronomical and chart substrate
2. doctrine profile evaluation
3. bounded scan and window assembly
4. optional REST serialization

Search transport must not own:

- historical rule definitions
- default orb doctrine
- node or house policy
- result judgement language
- rule weights
- remedies or matter-specific interpretation

A returned window would mean only that its sampled chart states met the named
profile predicate. It would retain the existing discrete-scan and boundary
truth limitations.

## 11. Required Provenance

Every future profile evaluation must expose:

- profile id, version, status, and lineage
- authority citation down to book/chapter/page or section/page
- chart time, location, zodiac frame, and house policy where used
- ephemeris reader and correction regime
- node model
- aspect, orb, application, and VOC policies
- speed semantics
- one visible witness per source rule
- any mitigation/remedy witnesses
- `complete_electional_judgement: false` for this profile
- `advice_language: not_provided`
- `recommendation_language: not_provided`

## 12. Failure and Indeterminacy Policy

- Non-finite or missing astronomical inputs fail evaluation; they do not clear
  a rule.
- A required but unbound doctrine policy yields `not_evaluable` for that rule
  and `indeterminate` overall.
- Unsupported election class or matter scope is rejected before evaluation.
- Unknown profile ids or versions are rejected.
- A profile version is immutable after public admission; changed doctrine
  requires a new version.
- No fallback may substitute a Robson, Sahl, Dorotheus, Lilly, or generic
  library rule for a missing Ramesey rule.

## 13. Validation and Admission Gates

Runtime admission requires all of the following:

1. Close every policy in section 8 with a cited derivation.
2. Add source-backed boundary fixtures for all numeric rules, including exact
   threshold, just-inside, and just-outside cases.
3. Add compound-rule truth tables for Rules 7 and 8.
4. Validate the speed and forward-aspect substrate independently of the
   doctrine evaluator.
5. Add real-ephemeris integration cases with fixed kernel provenance.
6. Add property tests for finite outputs, deterministic policy binding, sign
   boundaries, and rule-order independence.
7. Add facade tests only if the profile is admitted to the public engine.
8. Add REST tests only after a separate transport admission decision.
9. Audit the implementation against Moira's five sovereignty axes; numerical
   parity with another astrology engine is corroboration only.
10. Update public standards and validation documentation with the exact
    authority, corpus, interval, semantics, and limitations actually tested.

No weighted score can be admitted from these ten rules without a separate
source-backed scoring doctrine. Boolean counting is not a neutral default.

## 14. Non-Goals

This packet does not:

- implement `ramesey_moon_condition_v1`
- admit a facade method or REST route
- define a complete election for any matter
- bind unresolved orbs, node models, house systems, or VOC semantics
- merge Ramesey with Robson, Sahl, Dorotheus, Lilly, or Bonatti
- create a historical-outcome dataset
- claim empirical validation of electional astrology
- alter the existing generic electional search or scored-window semantics

## 15. Ledger Decision

P13-U1 remains `defer_for_doctrine` for runtime and website admission.

The missing doctrine artifact now exists, but its first profile is explicitly
pre-admission. The next lawful step is to resolve the nine policy questions in
section 8 from the held sources, then implement and validate the profile in the
engine before considering facade or REST exposure.
