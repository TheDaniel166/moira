# Lilly P4 perfection routes and chronology decisions

Date: 2026-10-30. Baseline: `60ac6a18da993b1dd1401a86a0581a58920c79ef`.
Status: **source decisions; fixture bundle and runtime admission pending**.

This tranche specifies how Lilly's 1647 general doctrine brings a matter to
perfection or prevents it: the routes, the events that interrupt them, the
order in which those events must happen, and what each one is said to do. It
changes no code. The v1 perfection classifier (`moira/classical_perfection.py`,
profile `lilly_1647_perfection_v1`), P2 reception evidence and P3 Moon
evidence keep their meanings. Read with the
[P4 source collation](LILLY_P4_SOURCE_COLLATION_2026-10-30.md), whose
passage IDs (S4-xx) are cited below, and with the open register entries in
[Rules and ambiguities](RULES_AND_AMBIGUITIES.md) (R18-R28, A07, A09,
A16-A23).

## Governing object

A **perfection-route record** for one ordered pair of principal roles
(querent's significator, quesited's significator) at an explicit question
epoch. Each record names one route candidate, its legs (directed applications
or contacts), the blocking candidates that were tested against those legs,
the source conditions and who supplied them, the coverage of the search that
produced its events, and a separate list of source-stated effects. It is
evidence for named rules, not a yes/no verdict, a probability or a timing
prediction.

Three things stay separate throughout:

- **astronomy:** contacts, stations, ingresses, applications and their
  uncertainty envelopes, as P3 already records them;
- **source conditions:** reception, dignity, house class, "good" houses,
  the Moon's sequence, each with its evidence and epoch;
- **source effects:** what Lilly says a route or blocker does (perfects
  without let, hinders and retards, never effects, a third party gains,
  perfects with regret).

## Routes

| ID | Route and source | Legs | Conditions | Effect as stated |
|---|---|---|---|---|
| P01 | Conjunction of the principals (S4-12) | One applying conjunction | No prohibition or refranation before it | Angle or first house: without let, sooner if swift and strong. Succedent: perfected, not so soon. Cadent: great delay, difficulty, struggle. |
| P02 | Sextile or trine (S4-13) | One applying aspect | Out of good houses; essentially well dignified; no malevolent aspect intervening before partile | Brought to pass |
| P03 | Square (S4-14) | One applying square | Each has dignity "in the degrees wherein they are"; apply out of proper and good houses | Brought to pass; "otherwise not" |
| P04 | Opposition (S4-15) | One applying opposition | Mutual reception by house; out of friendly houses; Moon separating from the quesited's significator and applying presently to the Lord of the Ascendant | Perfected, with regret or excess cost (completion and desirability reported separately) |
| P05 | Translation, structural reading (S4-06) | Translator separates from one principal; translator then applies to the other | Translator lighter than both | Matter brought about by a person signified by the translator |
| P06 | Translation, full reading (S4-16) | As P05 | Both principals separated from a conjunction, sextile or trine with each other; the principal it separates from receives the translator by house, triplicity or term; no conjunction or aspect with any other planet before the second leg | As P05; the translator's house rulership describes the agent |
| P07 | Collection (S4-17) | Each principal applies to the collector | Principals do not behold each other; collector heavier than both; each principal receives the collector by some essential dignity | Brought about by a third person interested in both |
| P08 | Mutual reception without, or despite, aspects (S4-08) | None | Principals in each other's essential dignity | Brought to pass without great trouble and suddenly |
| P09 | Dwelling in houses (S4-18) | Lunar translation from the quesited's significator to the Lord of the Ascendant | Quesited's significator in the Ascendant | Lilly rejects dwelling alone; only the lunar-translation form is a route, and it is evaluated as a P05/P06 translation by the Moon |

Decisions on the routes:

- **P05 and P06 are two named readings, with no default.** S4-06 is a
  structural definition; S4-16 adds principal history, reception and a
  no-intervening-contact condition, and drops the heaviness wording. A
  runtime profile must select one per call. Neither is the other's default or
  alias. The v1 classifier's mix (heaviness by speed, reception, no
  intervening contact, no principal history) is neither reading and stays a v1
  operational profile.
- **P08 is a candidate route, unadmitted as an override.** S4-08 says mutual
  reception brings the matter to pass when aspects deny it, are absent, or are
  doubtful. It does not say whether refranation or frustration are among
  "denied by the aspects". P4 records P08 as its own route; it never cancels a
  blocker on another route, and no route aggregation is admitted.
- **P09 is recorded as rejected.** A record may report the placement (the
  quesited's significator in the Ascendant), attributed to "the Ancients" and
  marked rejected by Lilly. The only positive form is the Moon's translation,
  evaluated under P05 or P06 with the Moon as translator.
- **The present relation is testimony, not perfection (S4-19).** Whether the
  principals are applying or separating at the question epoch is reported
  with each record. It does not by itself complete or deny a route.

## Blocking events

| ID | Blocker and source | Pattern | Applies to | Stated effect |
|---|---|---|---|---|
| B01 | Bodily prohibition (S4-02, S4-03) | A third planet interposes its body before the principals perfect (in the example, one swifter than the applying principal) | Any applying leg | Hindered and retarded |
| B02 | Prohibition by aspect (S4-02, S4-04) | As B01, by sextile, square, trine or opposition | Any applying leg | Hindered and retarded |
| B03 | Refranation (S4-05) | The applying planet stations retrograde before perfection and refrains | Any applying leg | Never effected |
| B04 | Frustration (S4-09) | Before a lighter planet's conjunction with a heavier, the heavier planet conjoins a third | Bodily (conjunction) legs | A third party gains |
| B05 | Malevolent intervention (S4-13) | A "malevolent aspect" intervenes before a sextile or trine is partile | P02 only, as worded | Condition of P02 unmet |

Decisions on the blockers:

- **B01/B02 have two named readings.** The definition (S4-02) says another
  planet "interposeth either his body or aspect", without naming which
  principal it touches. Both printed examples (S4-03, S4-04) show the
  interposer contacting **both** principals in order, the applying one first.
  The readings are `interposition_to_either` and `successive_to_both`. No
  default; v1's rule (swifter than both, applying to both, both contacts before
  perfection) corresponds to `successive_to_both` with speed heaviness.
- **Translation versus prohibition is decided by the third planet's relation
  to the applying principal at the start, not by the later contact.** In the
  translation example (S4-06) Mercury has already separated from Mars and
  then reaches Saturn before Mars does. In the prohibition example (S4-03) the
  Sun is still behind Mars and first "impedites" it. The same later contact
  with the heavier principal is a translation leg in the first case and a
  prohibiting contact in the second. This is an inference from the two
  examples, recorded as such; a record keeps the third planet's initial
  relation explicitly so the two cannot be confused.
- **B03 needs an intended application, not a future exact contact (A19).**
  Refranation is the station of the applying planet during an established
  application episode, before exactitude. Its example has no later exact
  contact at all. A station of the heavier principal alone is not
  refranation by this definition; it is recorded as a station that ends or
  alters the application.
- **B04 is conjunction-specific and the intercepting contact belongs to the
  heavier principal.** Frustration is not generalized to aspects. Unlike
  B01/B02, the third planet need not be swifter: in the example the heavier
  principal (Mars) applies to an even heavier planet (Jupiter).
- **B05 is held open.** "Malevolent aspect" can mean an aspect from a malefic
  (Saturn or Mars) or a square or opposition from any planet. Both readings are
  named; neither is assumed. B05 is not imported into P01, P03 or P04.
- **Effects stay distinct.** "Hindered and retarded" (B01/B02) is not the same
  claim as "never effected" (B03). Records carry each blocker's stated effect;
  no common "denied" outcome is derived.

## Chronology

| ID | Decision | Consequence |
|---|---|---|
| K01 | A blocker counts only when its event lies wholly before the completing contact of the leg it blocks. | Use P3's interval rule: definite when the blocker's envelope ends before the contact's begins; overlap is unresolved. No one-second tie constant is inherited. |
| K02 | A route is complete only when every leg completes in order. | Translation: the separation precedes the second-leg contact, and, under P06, no contact of the translator with another planet lies between. Collection: both applications complete; their relative order is reported, not required. |
| K03 | Every candidate route and blocker is kept. | No first-candidate truncation (A21). Several translators, collectors or blockers can coexist; each gets its own record. |
| K04 | No precedence or aggregation across routes. | Lilly gives no ranking among routes. The earliest completing route can be reported as a fact; it is not a verdict, and a blocked direct route does not erase a completed translation, nor the reverse. |
| K05 | Sign ingress is recorded, not treated as a blocker. | These pages give no rule that an ingress breaks an application. v1's "prior ingress makes application indeterminate" stays a v1 policy; P4 records the ingress and leaves its effect as an explicit, selectable policy. |
| K06 | Coverage follows P3. | Absence of a route or blocker needs complete coverage of the relevant event kinds up to the completing contact. Partial coverage gives unresolved, never negative. |
| K07 | Continuation carries state across search windows. | A window boundary passes on open applications, separated-but-not-yet-applied translators, pending collection legs and unresolved envelopes. A later window cannot complete a route whose earlier state was discarded. The 31-day v1 cap remains a v1 resource limit only. |

## Heaviness, epochs and conditions

- **Heaviness (A07) has three named readings, selected per mechanism:**
  - `traditional_order`: Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon,
    heaviest first;
  - `instantaneous_speed`: absolute longitude rate at the evaluation epoch
    (v1's choice);
  - `superior_inferior`: the p.113 classes (S4-10), which do not rank within a
    class or place the Sun, and therefore leave many comparisons unresolved.

  Every printed example agrees with all three. A record states which reading
  it used, and the fixtures must include stations and slow inner planets where
  the readings disagree.
- **Condition epochs are explicit.** Reception, dignity, house class and the
  Moon's sequence are evaluated at a named epoch: the question, the start of
  the leg, or the completing contact. The pages do not settle this: P03's
  "dignity in the degrees wherein they are" and "apply out of" read most
  naturally at the application, and P01's "this conjunction ... in a succedent
  house" at the contact. No epoch is defaulted; a condition known at one epoch
  is not transported to another.
- **Undefined qualities are qualitative evidence.** "Good", "proper",
  "friendly" houses, "essentially well dignified", "swift" and "accidentally
  strong" are not defined on these pages. They enter as P3-style
  `LillyQualitativeEvidence`: bound to subjects, epoch, source and supporting
  evidence. A dignity score or a house list chosen by Moira cannot establish
  them. P2 can supply specific dignity facts (for P03, whether a planet has
  term or face at its degree) without deciding "well dignified".
- **Opposition's Moon condition reuses P3.** "The Moon separating from the
  quesited's significator and applying presently to the Lord of the
  Ascendant" is evaluated from the P3 lunar sequence, with P3's coverage
  rules. "Presently" receives no numerical meaning.
- **Timing stays qualitative (A23).** P01's house-class speed and S4-01's
  sign-quality and degree statements are reported as qualifiers. No conversion
  of degrees into weeks, months or years is admitted.

## Relation to v1

The v1 classifier and its tests are unchanged. Its known seams (from the
original packet) are now specified, not repaired:

| v1 behavior | P4 decision |
|---|---|
| Direct perfection needs a later exact pair event (A19) | B03 and blocked applications use the application episode, not a future exact contact |
| Prior events within one second are filtered before the tie test (A20) | K01 envelope ordering replaces the constant |
| `translations[0]` and `collections[0]` only (A21) | K03 keeps every candidate |
| Heaviness by absolute speed | Named readings; v1 speed is one of three |
| Translation mixes S4-06 and S4-16 conditions | P05 and P06 kept apart |
| 31-day cap | K07 continuation; the cap stays v1 |

A P4 runtime will be additive, like P2 and P3, under a new fixed profile
(proposed `lilly_1647_perfection_routes_v1`).

## Fixture plan

The next step is a fixture bundle and read-only validator in the P3 format:
source references by provenance only, documentary examples with null epochs
and speeds, and clearly synthetic controls.

| Family | Documentary fixtures | Synthetic controls |
|---|---|---|
| Conjunction (P01) | none dated | angle, succedent and cadent qualifiers; prohibition and refranation before and after the contact |
| Sextile/trine (P02) | none dated | good-house and dignity evidence present, absent, unknown; B05 under both readings |
| Square (P03) | none dated | degree dignity present or absent; "otherwise not" |
| Opposition (P04) | none dated | each of the three conditions removed in turn; completion and regret reported separately |
| Translation (P05/P06) | p.111 Mercury-Mars-Saturn | reading disagreement; missing principal history; reverse reception; intervening contact; several translators |
| Collection (P07) | none dated | sign-aversion versus no-current-aspect; one leg incomplete; collector not heavier; reception by one principal only |
| Prohibition (B01/B02) | p.111 bodily; p.111 aspectual with Saturn 15 and with Saturn 13 | interposition to one principal only; translation-versus-prohibition pair with the same later contact |
| Refranation (B03) | p.111 | no later exact contact; station of the heavier principal; station after perfection |
| Frustration (B04) | pp.112-113 Mercury-Mars-Jupiter | aspect instead of conjunction; frustrating contact after the intended one |
| Reception route (P08) | none dated | coexisting refranation, recorded but not overridden |
| Dwelling (P09) | none dated | placement alone (rejected); lunar translation present |
| Heaviness (A07) | none | station, slow Mercury or Venus, Sun versus inner planets |
| Chronology (K01-K07) | none | envelope overlap, partial coverage, cross-window continuation |

Undated printed examples assert an ordering; their fixtures record that
ordering as the source's premise, not as a computed ephemeris result.

## Open questions this tranche does not settle

- Which translation reading (P05 or P06), prohibition reading and heaviness
  reading Lilly uses in his Book II judgements. The worked cases are the
  evidence; they are catalogued but not yet collated for these mechanisms.
- Whether mutual reception (P08) overcomes refranation or frustration.
- The house class of a conjunction when the two principals sit in different
  houses, and the epoch at which it is read.
- What counts as a "good", "proper" or "friendly" house, and as a
  "malevolent aspect".

These need the Book II judgements, not more definitions; Moira will not
supply defaults for them.
