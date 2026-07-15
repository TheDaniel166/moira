# P13-U1 Western Electional Doctrine Packet

Version: 1.0
Date: 2026-07-15
Status: three Moon profiles, bounded profile-status scanning, Dorothean and Sahl matter layers, and a standalone Lilly perfection profile are public; scoring deferred
Scope: bounded Western electional doctrine beside the generic search transport

## 1. Doctrine Decision

Moira may develop Western electional judgement only through named, versioned,
source-owned profiles. A profile must bind its lineage, computational policies,
rule meanings, variants, and public language explicitly.

The existing electional search surface remains generic infrastructure. It may
scan chart states, merge qualifying scan points into windows, and attach a
declared numeric transport score. It does not become Western electional
doctrine merely because a future profile uses it.

This packet defines three bounded doctrine profiles:

`ramesey_moon_condition_v1`

`sahl_moon_condition_v1`

`dorotheus_moon_condition_v1`

`dorotheus_construction_v1`

`lilly_1647_perfection_v1`

It is a transparent evaluation of William Ramesey's ten impediments of the
Moon in *Astrologia Restaurata*, Book III, Chapter II, printed p. 127. It is
not a complete election, a recommendation, an auspiciousness score, or a
substitute for matter-specific judgement. The Sahl profile independently
evaluates Sahl bin Bishr's ten Moon impediments in *On Elections* section 22.
It does not inherit Ramesey's thresholds, rule groupings, or remedy witness.
The Dorotheus profile independently evaluates the eleven corruption clauses
in *Carmen Astrologicum* V.6.3-14 and preserves V.6.15 as a separate remedy
instruction. It does not claim the later root/outcome or matter-specific layers.

`dorotheus_rooted_context_v1` is a separate, non-scored shared context. It
preserves the Moon as work root, the Moon-sign lord as outcome, the next exact
traditional connection before sign exit, the six V.31 matter-significator
families, and explicit ephemeral/radical natal evidence. It does not claim a
complete matter judgement, advice, recommendation, or auspiciousness score.

The profile is admitted through `moira.western_electional`, the curated package
root, `moira.facade`, `Moira.ramesey_moon_condition_at(...)`, and the bounded
single-moment route
`POST /v1/electional/western/ramesey-moon-condition`. It also participates in
the dedicated bounded profile-status scanner described in section 10. It has no
generic numeric-fit predicate, scoring, website, advice, or recommendation
surface. Section 8 records the profile-specific policies. Section 13 records
the engine evidence and public-moment admission decisions.

The Sahl profile is admitted through the same public engine layers,
`Moira.sahl_moon_condition_at(...)`, and
`POST /v1/electional/western/sahl-moon-condition`. Its burnt-path and eighth-
rule textual variants remain explicit request and result policy rather than
being merged into Ramesey or hidden behind a universal default.

Sahl §§43-55 are independently admitted as six matter profiles through
`Moira.sahl_matter_profile_at(...)` and
`POST /v1/electional/western/sahl-matter-profile`: building, demolition, land,
wells/rivers, planting, and sowing. They embed the general Sahl Moon layer but
do not collapse their matter-specific combination laws. Open vocabulary such
as "in number," eastern/ascending, circle motion, cleansing, and adaptation is
preserved as typed `not_evaluable` evidence rather than silently borrowed from
a later author.

Sahl's second-house commerce sequence is additionally admitted as four
independent profiles: lending (§§29-31), investment (§§36-38), purchase (§39),
and sale (§40). Business partnership (§§32-35) remains assigned to the later
partnership family, and alchemy/repeated works (§41) is not treated as a
commerce profile. Every admitted commerce result uses the same public Sahl
matter route and preserves unresolved source vocabulary rather than inventing
a complete judgement.

The Dorotheus profile is likewise admitted through the engine, facade, and
`Moira.dorotheus_moon_condition_at(...)`, with
`POST /v1/electional/western/dorotheus-moon-condition` as its typed REST
surface. Its eleven source-ordered rules, measured unknowns, and separate
remedy instruction remain visible in the response.

The rooted context is admitted through `Moira.dorotheus_rooted_context_at(...)`
and `POST /v1/electional/western/dorotheus-rooted-context`. Radical requests
must supply a complete natal moment, location, and house-system bundle;
ephemeral requests reject natal fields.

The first complete matter profile is admitted as
`dorotheus_construction_v1` through
`Moira.dorotheus_construction_at(...)` and
`POST /v1/electional/western/dorotheus-construction`. It composes Dorotheus
V.2-V.6, V.31, and every V.7 construction clause. Complete means that every
source layer and clause is represented; it does not mean every clause is
numerically resolved. Increasing in calculation and being on the ecliptic
while rising north remain measured, visible `not_evaluable` witnesses because
the source does not state the missing lunar equation and crossing-region
semantics. The profile supplies no score, advice, or recommendation.

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
language. Sahl and Dorotheus now own distinct admitted profiles.

### 2.3 Sahl governing witness

Primary authority for `sahl_moon_condition_v1`:

- Sahl bin Bishr, *On Elections*, section 22b-g, in Benjamin Dykes,
  *Choices & Inceptions: Traditional Electional Astrology*, printed pp. 99-101
  (PDF pp. 115-117 in the held 449-page witness).
- Dykes's glossary, printed pp. 409-415 and 426, supplies the anthology's
  explicit definitions of whole-sign aspects, twelfth-parts, medieval
  emptiness of course, cadency, and the two named burnt-path spans.
- Section 22 and the supporting glossary pages were rendered and visually
  checked on 2026-07-14/15. The check preserves note 69's uncertainty and note
  70's Latin/Arabic eighth-rule conflict.

### 2.4 Dorotheus governing witness

Primary authority for `dorotheus_moon_condition_v1`:

- Dorotheus of Sidon, *Carmen Astrologicum*, the ʿUmar al-Ṭabarī translation,
  2nd edition, Benjamin Dykes trans. and ed., Book V.6, printed pp. 233-235
  (PDF pp. 251-253 in the held 412-page witness).
- Dykes's glossary, printed pp. 353-376, supplies the edition-owned meanings
  of whole-sign configuration, twelfth-parts, and the 15-degree under-rays
  interpretation. Dykes's introduction, printed p. 36, identifies the bounds
  used by Dorotheus as Egyptian.
- V.6.3-15 and the relevant glossary entries were rendered and visually
  checked on 2026-07-15. The check does not invent a region for V.6.7 or a
  connection interval/latitude criterion for V.6.10.

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
and the lord of the hour. It now returns clause-level fulfillment evidence.
Moon cadence/whole-sign relation and Jupiter/Venus first-house or whole-sign
sextile/trine truth are evaluated; the planetary-hour lord is resolved. The
three fortification commands remain typed `indeterminate` source gates because
the passage supplies no closed predicate. No generic dignity score fills that
gap.

The remedy has no numeric weight, never changes a rule state, and never flips a
triggered profile to clear. Applicability and fulfillment are separate:
applicability follows urgent-time context, while fulfillment is
`fulfilled`, `not_fulfilled`, or `indeterminate` from the visible clauses.

### 7.6 Second profile: `sahl_moon_condition_v1`

The Sahl profile evaluates section 22's ten impediments in source order and
preserves compound clauses. It has no remedy vessel, numeric total, ranking,
or matter-specific judgement.

| # | Stable rule id | Admitted computation |
|---|---|---|
| 1 | `moon_burned_by_sun_12deg` | shortest Sun-Moon separation `<= 12 degrees`; applying/separating phase visible |
| 2 | `moon_in_degree_of_fall` | ordinal third degree Scorpio, `[2, 3)` |
| 3 | `moon_opposition_sun` | whole-sign opposition |
| 4 | `moon_joined_or_hard_ray_malefic` | bodily Mars/Saturn joining by Perso-Arabic combined moieties; square/opposition by whole-sign ray |
| 5 | `moon_near_lunar_node_12deg` | true node and opposition, inclusive 12-degree separation |
| 6 | `moon_in_terminal_malefic_bound` | terminal segment of the explicitly selected Egyptian bounds table |
| 7 | `moon_cadent_or_burnt_path` | quadrant houses 3/6/9/12 OR the selected named burnt-path interpretation |
| 8 | `moon_twelfth_part_or_opposed_or_averse_house` | Arabic/al-Rijal twelfth-part reading by default, or separately labeled Latin reading; opposition/aversion to Cancer preserved |
| 9 | `moon_slow_below_12deg_per_day` | instantaneous geocentric longitude rate strictly below 12 degrees/day |
| 10 | `moon_empty_in_course` | no exact traditional-planet connection completes before sign exit |

Sahl gives only “the end of Libra and the beginning of Scorpio” for the burnt
path. Public callers must therefore select a named policy explicitly. The
source-faithful `sahl_text_indeterminate_no_numeric_endpoints` selection makes
the clause `not_evaluable`; the Dykes-glossary fall-degree interval is encoded
as `[199, 213)`, and the later fifteen-degree convention as `[195, 225)`.
Neither computational interval is relabeled as Sahl's missing numeric wording.

For rule 8, Dykes recommends the Arabic/al-Rijal twelfth-part reading; the
conflicting Latin twelfth-sign reading remains a selectable named variant. A
confirmed Sahl impediment determines a triggered summary even when another
compound clause is unresolved. If no rule is confirmed and any rule remains
`not_evaluable`, the overall status is indeterminate.

### 7.7 Third profile: `dorotheus_moon_condition_v1`

The Dorotheus profile evaluates the eleven distinct corruption clauses in
V.6.3-14. It preserves V.6.15 as one separate, non-erasing remedy instruction.

| # | Stable rule id | Admitted computation |
|---|---|---|
| 1 | `moon_eclipsed` | Moira geometric lunar-eclipse contact state; natal-Moon sign/trine intensifier remains uncomputed |
| 2 | `moon_under_solar_rays` | shortest Sun-Moon separation `<= 15 degrees`, bound to this edition's under-rays glossary |
| 3 | `moon_in_malefic_twelfth_part` | Moon's 2.5-degree twelfth-part falls in a traditional Mars or Saturn domicile |
| 4 | `moon_on_ecliptic_descending_south` | measured lunar latitude retained; source supplies no region/tolerance, so v1 is `not_evaluable` |
| 5 | `moon_opposition_sun` | whole-sign opposition under the edition glossary |
| 6 | `moon_with_or_looking_at_infortune` | same-sign presence or whole-sign sextile, square, trine, or opposition to Mars/Saturn |
| 7 | `moon_disengaging_from_sun` | longitude separation/rate and lunar latitude retained; missing interval/latitude semantics remain `not_evaluable` |
| 8 | `moon_slow_below_12deg_per_day` | instantaneous geocentric longitude rate strictly below 12 degrees/day |
| 9 | `moon_in_burned_path` | whole tropical Libra and Scorpio, `[180, 240)` |
| 10 | `moon_in_terminal_malefic_bound` | terminal Egyptian bound ending at 30 degrees and ruled by Mars/Saturn |
| 11 | `moon_ninth_cadent_from_midheaven` | explicit quadrant ninth place; not generic cadency |

The unresolved fourth and seventh clauses prevent a false all-clear when no
other gate triggers. A confirmed gate still determines the summary as
triggered. The V.6.15 remedy becomes applicable only when a gate is confirmed
and the caller explicitly declares that the time cannot be postponed; the
profile does not claim that Jupiter/Venus placement has been fulfilled.

## 8. Bound Policies for Runtime Admission

The nine former Ramesey blockers are closed as follows. These are profile
doctrine, not universal Western defaults:

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

### 8.1 Sahl-specific bound policies

1. **Aspect scope**: square, opposition, and other rays are whole-sign;
   bodily joining uses the early Perso-Arabic combined moieties and may cross
   a sign boundary.
2. **Node model**: the profile explicitly binds Sahl's Head/Tail language to
   the true ecliptic ascending node and its opposition.
3. **Bounds**: Sahl does not name a table. The profile visibly selects Moira's
   Egyptian bounds and tests only the terminal segment ending at 30 degrees.
4. **Cadency**: caller-declared quadrant houses 3, 6, 9, and 12; missing or
   non-quadrant figures remain `not_evaluable`.
5. **Burnt path**: unresolved source wording is the default. The two
   glossary-supported intervals are explicit optional variants using tropical
   half-open endpoints.
6. **Twelfth-part**: each sign is divided into twelve 2.5-degree parts. The
   Arabic/al-Rijal reading tests whether Mars or Saturn occupies the sign named
   by the Moon's twelfth-part; the Latin reading is separate.
7. **Void**: the anthology's medieval definition is sign-bounded—no exact
   connection completes before the Moon leaves its sign.
8. **Speed product**: the strict 12-degree/day comparison uses the same
   explicitly attested apparent-longitude/astrometric-rate chart product as the
   Ramesey evaluator, without transferring Ramesey's threshold.

### 8.2 Dorotheus-specific bound policies

1. **Under rays**: V.6.4's visibility wording is bound to this edition's
   glossary definition of 15 degrees from the Sun; equality is included.
2. **Aspect scope**: opposition and “looking at” are whole-sign
   configurations. “With” is same-sign presence. No later moiety table is
   imported into V.6.8-9.
3. **Twelfth-parts**: 2.5-degree dodecatemoria map to signs; a Mars or Saturn
   twelfth-part means one of their traditional domiciles, not their bodily
   occupancy.
4. **Burned path**: V.6.12 names Libra and Scorpio, so the interval is the two
   whole tropical signs `[180, 240)`, not a later narrowed span.
5. **Bounds**: V.6.13 uses the terminal Egyptian bound when its ruler is Mars
   or Saturn. The binding follows Dykes's identification of Dorotheus's bounds.
6. **Cadency**: V.6.14 is specifically the quadrant ninth place falling from
   the Midheaven. It is not generalized to all cadent houses.
7. **Unknowns**: V.6.7 and V.6.10 remain `not_evaluable`; measured latitude
   and separation evidence is visible, but no node orb, crossing tolerance,
   or connection interval is fabricated.

## 9. Named Lineage Variants

These variants are separate profile parameters, not choices to average:

1. Void of course: Hellenistic 30°; medieval sign-bounded; Lilly moiety;
   modern Ward-orb; Ramesey wording requires its own confirmed binding.
2. Moon/Sun condition: Ramesey 12° Moon-specific combustion; Sahl 12° burned
   before/after; Dorotheus V.6.4 uses visibility wording bound by the edition's
   15° under-rays glossary entry;
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

The admitted doctrine implementations supply single-moment facade and REST
adapters. The three Moon-condition profiles also supply a separate,
doctrine-owned status adapter to the bounded profile scanner. This admission
does not place them in the generic numeric-fit search or scoring engine. The
layers remain:

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

A returned window means only that its sampled chart states met the caller's
explicitly named qualifying statuses. It retains the existing discrete-scan
and boundary-truth limitations.

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
- for Ramesey only, separate remedy applicability and tri-state fulfillment,
  triggering rule identities, source instructions, typed clause evidence, and
  named unresolved fortification gates
- for Sahl, the selected burnt-path and eighth-rule variants; matter results
  additionally expose the exact profile id, every source-ordered clause,
  triggered gates, unresolved terms, and numerical completeness
- `complete_electional_judgement: false` for each profile
- for `dorotheus_construction_v1`, `source_complete: true`,
  `complete_matter_profile: true`, and `numerically_complete: false`
- `advice_language: not_provided`
- `recommendation_language: not_provided`
- single-moment transport provenance naming the engine entry point, facade
  entry point, lack of scoring, and non-erasing tri-state remedy fulfillment
- scan transport provenance naming its engine, facade, and REST entry points,
  exact qualification statuses, compact per-sample witnesses, and lack of
  generic numeric-fit search integration

## 12. Failure and Indeterminacy Policy

- Non-finite or missing astronomical inputs fail evaluation; they do not clear
  a rule.
- A missing required input yields `not_evaluable` for that rule. Ramesey v1 is
  indeterminate if any rule is not evaluable; Sahl v1 remains triggered when a
  different impediment is confirmed and is otherwise indeterminate.
- Unsupported election class or matter scope is rejected before evaluation.
- Unknown profile ids or versions are rejected.
- A profile version is immutable after public admission; changed doctrine
  requires a new version.
- No fallback may substitute one lineage, translation, or generic library rule
  for a missing Ramesey or Sahl rule.

## 13. Validation and Admission Gates

Ramesey engine-module admission completed:

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

Sahl engine-module admission completed:

1. Unit fixtures cover all ten rules, strict 12-degree/day motion, inclusive
   12-degree solar/node boundaries, whole-sign rays, body-specific combined
   moieties, terminal Egyptian bounds, both eighth-rule readings, and both
   selectable burnt-path intervals.
2. The unresolved burnt-path default is tested as `not_evaluable`; a confirmed
   cadency or other impediment remains decisive without converting unknown
   evidence into clear evidence.
3. Facade tests prove reader and variant delegation; strict REST tests preserve
   ten rule witnesses, selected variants, non-score semantics, and explicit
   transport provenance.
4. OpenAPI contains the Sahl request, response, and both variant fields.
5. J2000 London DE441 regressions exercise the real reader and compare the
   Rule 9 rate with an independently sampled central finite difference at
   absolute tolerance `1e-4 degrees/day`.
6. Curated root/facade snapshots and the doctrine-surface audit admit the new
   public types and `Moira.sahl_moon_condition_at(...)` method exactly.

Sahl §§43-55 matter-profile admission completed:

1. Six distinct enum values preserve building, demolition, land, wells/rivers,
   planting, and sowing rather than a generic fourth-house profile.
2. Per-clause fixtures cover closed sign, house, dignity, bound, light, join,
   and configuration predicates plus explicit malefic gates.
3. Every open source term is a typed `not_evaluable` clause; compound tests
   prove that unknown evidence cannot fabricate a trigger.
4. REST round trips all six values, embeds the complete Sahl Moon layer, and
   OpenAPI publishes the exact six-value request enum.
5. A DE441 J2000 integration case executes every profile through the shared
   reader and preserves source and reader provenance.

Dorotheus engine-module admission completed:

1. Unit fixtures cover all eleven clauses, the 15-degree under-rays boundary,
   dodecatemoria, whole-sign configurations, strict 12-degree/day motion, the
   two-sign burned path, terminal Egyptian bounds, and the specific quadrant
   ninth-place clause.
2. V.6.7 and V.6.10 preserve measured latitude/separation evidence as
   `not_evaluable`; tests prove that confirmed gates still dominate without
   converting unknown evidence into clear evidence.
3. The present eclipse clause consumes Moira's geometric lunar-eclipse
   classification. The natal-Moon sign/trine intensifier remains a visible
   uncomputed modifier rather than an invented ephemeral result.
4. Facade and REST tests preserve all eleven rules, the separate remedy
   instruction, strict request validation, transport provenance, and the
   non-score/non-recommendation boundary. OpenAPI contains the dedicated route
   and Dorotheus request/response schemas.
5. DE441 integration covers J2000 London, compares the measured Moon rate with
   a central finite difference at `1e-4 degrees/day`, and confirms that an
   engine-found lunar-eclipse maximum triggers the present-eclipse gate.
6. Curated root/facade snapshots and the doctrine-surface audit admit the new
   public types and `Moira.dorotheus_moon_condition_at(...)` method exactly.

### 13.1 Wider-surface admission decision

Decisions on 2026-07-14/15: admit all three profiles' named public types and
evaluators at the package root and facade, add
`Moira.ramesey_moon_condition_at(...)` and
`Moira.sahl_moon_condition_at(...)` and
`Moira.dorotheus_moon_condition_at(...)`, and admit the bounded single-moment REST
routes `/v1/electional/western/ramesey-moon-condition` and
`/v1/electional/western/sahl-moon-condition` and
`/v1/electional/western/dorotheus-moon-condition`.

Generic scoring, website, advice, and recommendation-language admission remain
deferred. The three Moon profiles additionally admit a dedicated status
scanner through `scan_western_electional_profile(...)`,
`Moira.western_electional_profile_windows(...)`, and
`POST /v1/electional/western/profile-windows`. Qualification is exact
membership in a caller-visible status set, defaulting to
`clear_of_profile_impediments`; every scan returns all three status counts.
REST limits cadence to at least one hour and at most 256 points. Merged windows
describe qualifying samples only and make no continuous-boundary claim.
The single-moment routes continue to accept one `jd_ut`, require an explicit
house-system code, and return the complete typed evaluation.
Ramesey and Dorotheus preserve optional urgency context and uncomputed remedy
fulfillment; Sahl preserves its explicit textual variants. This admission does
not authorize generic scored-window language, construction-profile scanning,
or rooted-context qualification.

### 13.2 Ramesey five-axis sovereignty audit

Audit performed against the implementation and tests on 2026-07-14:

| Axis | Result | Evidence |
|---|---|---|
| Ontology ownership | Pass | The object is explicitly a bounded ten-gate Moon-condition profile, not a score, complete election, or recommendation. |
| Derivation ownership | Pass | Rule identity and thresholds derive from Ramesey's facsimile; Moira choices for true node, house system input, correction products, endpoints, and exact-perfection VOC are labeled as choices rather than attributed falsely to the source. |
| Structural ownership | Pass | Assembly uses named immutable rule/clause/measurement witnesses and a separate remedy vessel; source order is citation metadata, not a legacy positional result array. |
| Policy ownership | Pass | `RameseyMoonConditionPolicy` is frozen and rejects caller substitution; missing inputs remain `not_evaluable`; remedy applicability derives from visible gate and urgency context, fulfillment derives from typed clauses, and the unowned fortification predicates remain source gates. |
| Validation ownership | Pass for public moment admission | Primary-page boundary fixtures, full-zodiac properties, Moira-owned invariants, an independent DE441 forward-geometry covenant, exact public-surface snapshots, facade delegation tests, and strict REST contract tests carry the proof. Kernel regression is not presented as historical or empirical validation of astrology. |

Provenance honesty also passes: no Swiss or other external astrology engine is
used as implementation authority or numerical proof. The known VOC
interpretive choice and the remedy's indeterminate fortification clauses remain
visible rather than being concealed.

### 13.3 Sahl five-axis sovereignty audit

Audit performed against the implementation and tests on 2026-07-15:

| Axis | Result | Evidence |
|---|---|---|
| Ontology ownership | Pass | The object is Sahl section 22's bounded ten-impediment condition, not a blended medieval checklist or complete election. |
| Derivation ownership | Pass | Rule order and numeric thresholds come from the held Dykes witness; glossary definitions and Moira bindings are labeled separately. |
| Structural ownership | Pass | Immutable Sahl-owned rule, clause, measurement, policy, and evaluation vessels preserve compound logic without positional arrays. |
| Policy ownership | Pass | Burnt-path ambiguity and the Latin/Arabic eighth-rule conflict are selectable, visible policies; unknown source wording remains `not_evaluable`. |
| Validation ownership | Pass for public moment admission | Primary-page checks, boundary invariants, DE441 integration, real facade/REST execution, OpenAPI assertions, and public-surface governance carry the proof. |

Provenance honesty passes with an explicit limitation: Egyptian bounds are a
Moira profile binding because Sahl does not name the bound table. Neither
selectable burnt-path span is falsely presented as Sahl's own numeric wording.

No weighted score can be admitted from any of these source lists without a
separate source-backed scoring doctrine. Boolean counting is not a neutral
default.

### 13.4 Dorotheus five-axis sovereignty audit

Audit performed against the implementation and tests on 2026-07-15:

| Axis | Result | Evidence |
|---|---|---|
| Ontology ownership | Pass | The object is Dorotheus V.6's bounded eleven-clause corruption-of-the-Moon profile plus a separate remedy instruction, not a later ten-impediment blend or complete election. |
| Derivation ownership | Pass | Rule order and wording derive from the rendered primary pages; glossary meanings and Moira astronomical bindings are identified separately. |
| Structural ownership | Pass | Immutable Dorotheus-owned rule, clause, measurement, remedy, policy, and evaluation vessels preserve source order without positional result arrays. |
| Policy ownership | Pass | The two underdetermined clauses remain visibly `not_evaluable`; later node or connection orbs are not imported, and the whole-sign/bounds/rays choices are explicit. |
| Validation ownership | Pass for public moment admission | Primary-page checks, boundary invariants, DE441 integration, eclipse-path exercise, exact facade/REST execution, OpenAPI assertions, and public-surface governance carry the proof. |

Provenance honesty passes with explicit limitations: the natal intensifier and
source-undefined Ramesey fortification predicates are not computed, and kernel
regression is not presented as historical or empirical proof of astrology.

### 13.5 Lilly perfection profile and five-axis sovereignty audit

`lilly_1647_perfection_v1` is a standalone, bounded event analysis rather than
a complete election. It admits the six forms explicitly closed by the 1647
facsimile at printed pp. 110-113 and 125-126: direct perfection, translation
of light, collection of light, bodily/aspectual prohibition, refranation, and
frustration. The neutral trace preserves every exact traditional-planet
aspect, station, and sign ingress in the selected interval.

The fixed policy uses tropical zodiacal Ptolemaic aspects, the canonical Lilly
planetary moieties, seven traditional planets, one-second tie semantics, and a
31-day maximum trace. It names UT1 input with internal TT conversion, apparent
geocentric true-ecliptic-of-date longitude, and Moira's canonical astrometric
geocentric longitude rate explicitly. Translation requires reception by house, active
triplicity, or term and no intervening planetary contact. Collection requires
significators that do not behold one another by sign, application to one
slower collector, and reception of that collector by each significator in an
essential dignity. Sign ingress and exact ties remain indeterminate instead
of acquiring an invented break law.

| Axis | Result | Evidence |
|---|---|---|
| Ontology ownership | Pass | The result is a named Lilly event trace and six doctrine witnesses, not a generic traditional success flag. |
| Derivation ownership | Pass | Each predicate maps to the supplied 1647 facsimile pages; the canonical Moira moiety, bounds, triplicity, and dignity objects supply named computational inputs. |
| Structural ownership | Pass | Immutable body-state, event, policy, witness, and analysis vessels expose chronology and reception rather than legacy slot arrays. |
| Policy ownership | Pass | Planet set, aspect scope, moieties, reception, ingress, tie, interval, scoring, and advice semantics are explicit. |
| Validation ownership | Pass for Lilly v1 admission | Synthetic doctrine isolation, canonical-moiety regression, DE441 chronology, root/facade governance, REST serialization, and OpenAPI schema checks carry the proof. |

Sahl and Bonatti perfection profiles, abscission, and reflection remain
unadmitted. They cannot be inferred from the Lilly implementation or exposed
under a generic lineage label.

## 14. Non-Goals

This packet and admitted public-moment batch do not:

- admit Western profile scoring, ranking, advice, or continuous-boundary claims
- define a scored or recommended election for any matter
- merge the distinct Ramesey, Sahl, and Dorotheus objects with each other or
  with Robson, Lilly, or Bonatti; the standalone Lilly perfection profile does
  not alter those Moon-condition or matter profiles
- create a historical-outcome dataset
- claim empirical validation of electional astrology
- alter the existing generic electional search or scored-window semantics

## 15. Ledger Decision

P13-U1 is `three_moon_profiles_status_scan_matter_layers_and_lilly_perfection_public; scoring_and_recommendation_deferred`.

`ramesey_moon_condition_v1` now exists as an engine-owned, non-scored condition
profile with a separate non-erasing contingency witness. Its named types and
evaluator are public at the package root and facade, `Moira` owns the reader-
backed convenience method, and the REST route exposes exactly one moment with
explicit transport provenance. Any generic search, scoring, website, advice,
recommendation, or additional lineage-profile surface requires a new doctrine,
transport, and public-semantics admission task; none is implied here.

`sahl_moon_condition_v1` separately exists as an engine-owned, non-scored
condition profile with visible burnt-path and eighth-rule variants. Its named
types, facade method, and REST route expose one moment with explicit transport
provenance. It does not inherit Ramesey's remedy, aspect, bounds, speed, or
summary-status policy.

`dorotheus_moon_condition_v1` separately exists as an engine-owned,
non-scored eleven-clause condition profile with a separate non-erasing remedy
instruction. Its named types, facade method, and REST route expose one moment
with explicit transport provenance. The two unresolved source clauses remain
indeterminate, and V.6 admission does not imply the root/outcome,
matter-significator, natal-overlay, or complete matter layers.

`dorotheus_rooted_context_v1` separately admits the shared root/outcome,
sign-bounded next-connection, matter-significator, and natal-evidence vessel.
It deliberately leaves the undefined V.31 bad-place set, broader accidental
misfortune semantics, and chapter-owned houses outside admitted matter profiles
uncomputed. It is evidence, not an admitted scan predicate.

`dorotheus_construction_v1` is the first source-complete matter profile. Its
engine object, facade method, and typed REST route preserve V.2-V.6, V.31, and
all six V.7 computational clauses. Two clauses remain explicitly
`not_evaluable`; therefore the result reports `source_complete=true`,
`complete_matter_profile=true`, `numerically_complete=false`, and
`complete_electional_judgement=false`. No weighted score, advice, ranking, or
recommendation is inferred from the historical text.

`lilly_1647_perfection_v1` separately admits a bounded event trace and six
source-owned perfection witnesses. Its engine object, curated exports, facade
method, and typed REST route expose the complete fixed policy and explicitly
exclude Sahl, Bonatti, abscission, reflection, scoring, and complete judgement.

The three Moon-condition profiles are scan-admitted through a separate bounded
status predicate. Callers must provide the exact qualifying-status set; there
is no implicit clear-status policy. The result records one compact witness per
sample with status, qualification, triggered rule ids, and not-evaluable rule
ids, merges qualifying samples under an explicit gap, and returns complete
status counts. The construction profile is excluded because its two unresolved
clauses make default clear-window semantics structurally unavailable. The scan
surface provides no score, rank, advice, recommendation, or exact-transition
claim and does not alter the generic electional numeric-fit transport. Ramesey
and Sahl scans reuse one range-level void-of-course computation while retaining
single-moment rule semantics at each sampled instant.
