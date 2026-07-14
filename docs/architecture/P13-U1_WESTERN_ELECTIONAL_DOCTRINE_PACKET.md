# P13-U1 Western Electional Doctrine Packet

Version: 0.4
Date: 2026-07-14
Status: first-profile public moment evaluation admitted; generic search/scoring deferred
Scope: bounded Western electional doctrine beside the generic search transport

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

The profile is admitted through `moira.western_electional`, the curated package
root, `moira.facade`, `Moira.ramesey_moon_condition_at(...)`, and the bounded
single-moment route
`POST /v1/electional/western/ramesey-moon-condition`. It has no generic
search-predicate, scoring, website, advice, or recommendation surface. Section
8 records the policies bound from Ramesey's text. Section 13 records the engine
evidence and public-moment admission decision.

## 2. Authority and Page Confirmation

### 2.1 Governing witness

Primary authority for `ramesey_moon_condition_v1`:

- William Ramesey, *Astrologia Restaurata; or, Astrologie Restored* (London,
  1654), Book III, Chapter II, printed pp. 126-128.
- Original facsimile witness: [Internet Archive item
  `b30323149_0001`](https://archive.org/download/b30323149_0001/b30323149_0001.pdf),
  PDF pages 184-186 in the downloaded scan.
- Printed p. 126 supplies the chapter title and context.
- Printed p. 127 supplies the complete ten-item Moon-impediment list and begins
  the contingency instruction; printed p. 128 completes the urgent-time
  arrangement.
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
| 1 | `moon_combust_sun_12deg` | Moon within 12° of the Sun, applying or separating; applying is more afflicted | shortest geocentric ecliptic Sun-Moon separation; applying/separating state; inclusive 12° boundary | Admitted |
| 2 | `moon_in_third_degree_scorpio` | Moon in the degree of her fall, the third degree of Scorpio | ordinal half-open interval `[2°, 3°)` in Scorpio | Admitted |
| 3 | `moon_opposition_sun` | Moon in opposition to the Sun | Ramesey combined moieties: Moon 6° + Sun 7.5° = 13.5° | Admitted |
| 4 | `moon_joined_or_hard_aspect_malefic` | Moon joined with an infortune, or in quartile or opposition to one | conjunction, square, or opposition to Saturn/Mars under Ramesey combined moieties | Admitted |
| 5 | `moon_near_lunar_node_12deg` | Moon within 12° of the Head or Tail of the Dragon | true ascending ecliptic-crossing node and its opposition; inclusive 12° | Admitted |
| 6 | `moon_latter_degrees_with_infortune` | Moon in the latter degrees of a sign wherein there is an infortune | Ramesey's terminal malefic term from Book II pp. 71-72; Leo excepted | Admitted |
| 7 | `moon_cadent_or_via_combusta` | Moon cadent from angles **or** in the last 15° of Libra / first 15° of Scorpio | caller-declared effective quadrant houses; houses 3/6/9/12; tropical `[195°, 225°)`; preserve OR | Admitted |
| 8 | `moon_detriment_or_not_beholding_cancer` | Moon in Capricorn, or quartile to her own house, or not beholding it by sextile or trine | whole-sign Cancer relationship; bodily, sextile, and trine are favorable beholding | Admitted |
| 9 | `moon_slow_below_ramesey_mean` | Moon moves less than 13°10′36″ in 24 hours | `PlanetData.speed`: astrometric geocentric instantaneous longitude rate; strict less-than | Admitted |
| 10 | `moon_void_ramesey_sign_bound` | Moon in a sign and beholds no planet until entering another sign | exact Ptolemaic perfection to a traditional planet before sign ingress | Admitted through existing VOC substrate |

### 7.3 Numeric boundary doctrine already established

The first profile binds only what the primary page states plainly:

- Rule 1 uses an inclusive 12° angular boundary because Ramesey includes the
  Moon “even when” twelve degrees distant.
- Rule 5 likewise uses an inclusive 12° boundary once the node model is
  selected.
- Rule 7's via-combusta interval is the final 15° of Libra through the first
  15° of Scorpio, encoded as `[Libra 15°, Scorpio 15°)`.
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

Ramesey follows the list with a contingency arrangement and continues it onto
printed p. 128 for a business so urgent that its time cannot be deferred. The
profile now preserves one separate `RameseyRemedyWitness`. Its applicability
derives only from confirmed impediments and the caller's explicit
`unavoidable_time_urgency` context.

The witness preserves three instructions: keep the impeded Moon cadent and
without bodily or aspectual relation to the Ascendant; place a fortune in the
Ascendant or in good aspect with it; and fortify the Ascendant cusp, its lord,
and the lord of the hour. It is an instruction witness, not a fulfillment
assessment. The current profile does not invent the missing angle-aspect,
benefic-placement, ruler, hour-lord, or fortification policies. Those
uncomputed requirements remain visible in the result.

The remedy has no numeric weight, never changes a rule state, and never flips a
triggered profile to clear. If the urgent-time context is absent, applicability
is `indeterminate`; if explicitly false, the instruction is `not_applicable`.

## 8. Bound Policies for Runtime Admission

The nine former blockers are closed as follows. These are profile doctrine,
not universal Western defaults:

1. **Third-degree convention**: ordinal degrees use zero-based half-open
   computational intervals; the third degree of Scorpio is `[2°, 3°)`.
2. **Ramesey aspect orbs**: Book II's planetary chapters give full orbs of
   Saturn 9°, Jupiter 9°, Mars 7°, Sun 15°, Venus 7°, Mercury 7°, and Moon
   12°. Book II's aspect chapter combines their half-orbs. Thus Sun opposition
   uses 13.5°, Moon-Saturn hard aspects 10.5°, and Moon-Mars 9.5°.
3. **Node model**: Book II p. 76 defines the Head and Tail as the places where
   the Moon cuts the ecliptic. That ontology does not uniquely identify a
   historical numerical node algorithm; the profile makes the explicit Moira
   geometric choice of the true ascending node and the point 180° opposite it,
   not the mean node.
4. **Latter degrees**: Book II pp. 71-72 defines terms/bounds, prints the term
   widths, and assigns the last term to an infortune in every sign except Leo,
   where Jupiter is last. The implementation carries a profile-local terminal
   segment table rather than reusing Moira's currently mislabeled
   `PTOLEMAIC_BOUNDS` constant.
5. **Cadency policy**: Book II's house doctrine divides the local figure by
   horizon and meridian and then into houses. The profile requires a
   caller-declared quadrant house system and evaluates cadency as houses
   3/6/9/12. Requested, effective, and fallback system truth remain visible.
   A non-quadrant or missing figure makes the cadency clause `not_evaluable`;
   it does not silently choose a different system.
6. **Beholding Cancer**: “her own house” is Cancer and the source names sign
   relationships. The profile uses whole-sign bodily, sextile, and trine
   beholding; Capricorn, whole-sign squares, and signs lacking those favorable
   relationships preserve separate clauses.
7. **Speed product**: the chart longitude is Moira's apparent geocentric
   ecliptic product, while `PlanetData.speed` is explicitly the astrometric
   geocentric instantaneous longitude rate in degrees/day. The profile names
   both rather than collapsing their correction regimes. A prebuilt chart must
   explicitly attest this combined product; topocentric inputs are rejected.
8. **Ramesey void**: Book II p. 111 defines void as separation followed by no
   application during the planet's continuation in the sign, while the same
   chapter also discusses application and separation through planetary rays
   and combined moieties. The text therefore does not force one modern search
   algorithm. This profile explicitly selects the existing traditional-planet,
   Ptolemaic-aspect, exact-perfection, sign-bounded forward search. It does not
   silently claim that choice for Lilly or other lineages. A snapshot without
   that product is `not_evaluable`, never clear.
9. **Endpoint policy**: Rule 7 is `[195°, 225°)` in tropical longitude: exact
   15° Libra is included and exact 15° Scorpio is excluded.

The governing pages were rendered and visually checked against the original
facsimile on 2026-07-14. OCR and modern transcriptions were navigation aids,
not the final authority.

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

The admitted doctrine implementation supplies a single-moment facade and REST
adapter. It may supply a separate predicate adapter to the bounded search
engine only after a later search-admission decision. The layers remain:

1. astronomical and chart substrate
2. doctrine profile evaluation
3. bounded scan and window assembly
4. bounded single-moment facade and REST serialization

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

Every admitted profile evaluation exposes:

- profile id, version, status, and lineage
- authority citation down to book/chapter/page or section/page
- chart time, location, zodiac frame, and house policy where used
- ephemeris reader provenance and correction regime
- node model
- aspect, orb, application, and VOC policies
- speed semantics
- one visible witness per source rule
- the separate remedy applicability, triggering rule identities, source
  instructions, and uncomputed fulfillment requirements
- `complete_electional_judgement: false` for this profile
- `advice_language: not_provided`
- `recommendation_language: not_provided`
- transport provenance naming the engine entry point, facade entry point,
  single-moment semantics, lack of scoring, lack of generic-search integration,
  and deliberately uncomputed remedy fulfillment

## 12. Failure and Indeterminacy Policy

- Non-finite or missing astronomical inputs fail evaluation; they do not clear
  a rule.
- A missing required input yields `not_evaluable` for that rule and
  `indeterminate` overall.
- Unsupported election class or matter scope is rejected before evaluation.
- Unknown profile ids or versions are rejected.
- A profile version is immutable after public admission; changed doctrine
  requires a new version.
- No fallback may substitute a Robson, Sahl, Dorotheus, Lilly, or generic
  library rule for a missing Ramesey rule.

## 13. Validation and Admission Gates

Engine-module admission completed:

1. All nine policies in section 8 are bound from named Ramesey passages or an
   explicit Moira computational product.
2. Focused unit fixtures cover exact, inside, and outside boundaries for the
   12° distances, ordinal degree, aspect moieties, terminal terms, via
   combusta, and speed threshold.
3. Compound Rule 7 and Rule 8 clauses remain individually visible and their
   three-valued OR behavior is tested.
4. Missing VOC or incompatible house inputs become `not_evaluable`; geometric
   product substitution and topocentric input are rejected rather than hidden.
5. Module-level public names are sealed and their package-root and facade
   identities are governed by exact public-surface snapshots.
6. A J2000 London integration regression opens the discovered `de441.bsp`
   explicitly, records its file provenance, uses Regiomontanus without
   fallback, and asserts the complete triggered-rule identity tuple.
7. The same DE441 case compares Rule 9's `PlanetData.speed` against an
   independently sampled central finite difference of geometric lunar
   longitude (`dt=1e-4` day, absolute tolerance `1e-4°/day`). This is a
   numerical invariant check, not an external-authority comparison.
8. Four DE441 probes straddling the final Mars-square perfection and the next
   lunar sign ingress compare Rule 10 with an independent 15-minute forward
   geometry scan and 50-iteration bisection path. Both void and non-void states
   agree; the root and ingress tolerance is `2e-5` day (about 1.7 seconds).
9. Generative tests sweep finite lunar longitudes and speeds across the full
   zodiac, assert deterministic results, finite measurements, unique ordered
   rule identity, remedy/gate identity agreement, and normalized-longitude
   invariance. Explicit fixtures exercise both sides of all twelve sign
   boundaries.
10. The p. 127-128 contingency is a separate typed witness. Tests prove that
    true, false, missing, and indeterminate context never erases a gate or
    changes the ten-rule status.
11. Facade delegation preserves the `Moira` reader and explicit house policy;
    REST contract tests prove strict request validation and full serialization
    of all ten rules, clauses, measurements, remedy context, reader/house
    provenance, and the non-score/non-recommendation boundary.

### 13.1 Wider-surface admission decision

Decision on 2026-07-14: admit the profile's named public types and evaluator at
the package root and facade, add `Moira.ramesey_moon_condition_at(...)`, and
admit the bounded single-moment REST route
`POST /v1/electional/western/ramesey-moon-condition`.

Generic search, scoring, website, advice, and recommendation-language admission
remain deferred. The generic scanner does not yet carry variant-aware
forward-aspect provenance, urgent-time context, or the distinction between
remedy applicability and fulfillment. Repeated forward VOC searches also need
an explicit caching/performance contract before a broad scan is admitted. The
REST route therefore accepts one `jd_ut`, requires an explicit house-system
code, preserves the optional urgency context, returns the complete typed
evaluation, and reports `generic_search_integration: not_admitted`, scoring and
recommendation language as not provided, and remedy fulfillment as not
computed. This admission does not authorize generic scored-window language.

### 13.2 Five-axis sovereignty audit

Audit performed against the implementation and tests on 2026-07-14:

| Axis | Result | Evidence |
|---|---|---|
| Ontology ownership | Pass | The object is explicitly a bounded ten-gate Moon-condition profile, not a score, complete election, or recommendation. |
| Derivation ownership | Pass | Rule identity and thresholds derive from Ramesey's facsimile; Moira choices for true node, house system input, correction products, endpoints, and exact-perfection VOC are labeled as choices rather than attributed falsely to the source. |
| Structural ownership | Pass | Assembly uses named immutable rule/clause/measurement witnesses and a separate remedy vessel; source order is citation metadata, not a legacy positional result array. |
| Policy ownership | Pass | `RameseyMoonConditionPolicy` is frozen and rejects caller substitution; missing inputs remain `not_evaluable`; remedy applicability derives from visible gate and urgency context while unowned fulfillment policies remain uncomputed. |
| Validation ownership | Pass for public moment admission | Primary-page boundary fixtures, full-zodiac properties, Moira-owned invariants, an independent DE441 forward-geometry covenant, exact public-surface snapshots, facade delegation tests, and strict REST contract tests carry the proof. Kernel regression is not presented as historical or empirical validation of astrology. |

Provenance honesty also passes: no Swiss or other external astrology engine is
used as implementation authority or numerical proof. The known VOC
interpretive choice and the remedy's deliberately uncomputed fulfillment
requirements remain visible rather than being concealed.

No weighted score can be admitted from these ten rules without a separate
source-backed scoring doctrine. Boolean counting is not a neutral default.

## 14. Non-Goals

This packet and admitted public-moment batch do not:

- admit generic Western profile scanning, scoring, ranking, or advice
- define a complete election for any matter
- merge Ramesey with Robson, Sahl, Dorotheus, Lilly, or Bonatti
- create a historical-outcome dataset
- claim empirical validation of electional astrology
- alter the existing generic electional search or scored-window semantics

## 15. Ledger Decision

P13-U1 is `ramesey_v1_public_moment_admitted; generic_search_scoring_and_recommendation_deferred`.

`ramesey_moon_condition_v1` now exists as an engine-owned, non-scored condition
profile with a separate non-erasing contingency witness. Its named types and
evaluator are public at the package root and facade, `Moira` owns the reader-
backed convenience method, and the REST route exposes exactly one moment with
explicit transport provenance. Any generic search, scoring, website, advice,
recommendation, or additional lineage-profile surface requires a new doctrine,
transport, and public-semantics admission task; none is implied here.
