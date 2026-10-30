# Lilly P4 readings checked against Book II

Date: 2026-10-30. Companion to the
[P4 decisions](LILLY_P4_PERFECTION_DECISIONS_2026-10-30.md) and the
[P4 runtime](LILLY_P4_RUNTIME_2026-10-30.md).

Status: **source collation; no code or fixture changes**. It records how
Lilly applies the P4 mechanisms in his own Book II doctrine and worked
judgements, decision by decision, and what that implies for the readings the
runtime currently keeps open.

## What was read

- **Pages:** 181 printed pages of Book II in the Wellcome photographs (S01):
  pp.149-158, 183-242, 298-332, 358-362, 367-410 and 432-458. The ranges were
  chosen from an OCR search of the EEBO scan for the perfection vocabulary
  (translation, collection, prohibition, refranation, frustration, ponderous,
  weighty, lighter, good houses, behold); the OCR only located pages. Every
  page was read in its photograph.
- **Cases covered:** C02, C05-C10, C13-C20 and C26-C30, plus the general
  doctrine of houses 1-12 in those ranges.
- **Receipt:** [book_ii_p4/page_receipt.json](book_ii_p4/page_receipt.json)
  (URL, bytes and SHA-256 per page; the image suffix is printed page + 34 on
  every page read). Two running heads are misprinted (p.315 "215", p.318
  "218"; p.390 printed "388" and corrected by hand).
- **Readers:** four model-assisted readers, one per range, each writing a
  page-by-page log that keeps Lilly's statements apart from interpretation:
  [pp149-212](book_ii_p4/pp149-212.md), [pp213-242](book_ii_p4/pp213-242.md),
  [pp298-362](book_ii_p4/pp298-362.md), [pp367-458](book_ii_p4/pp367-458.md).
  Some later pages in two logs were noted from a single reading; the logs say
  which.
- **Checked again in the photographs for this record:** p.186 (collection
  and dwelling), p.198 (C06, Saturn ponderous yet retrograde), p.205
  (dwelling and lunar translation), p.239 (C09, collection), p.317
  (marriage: translation definition, blockers, reception) and pp.387-388
  (C13, translation and interposition).

Pages not read: the rest of Book II (other house doctrine and cases C01,
C03-C04, C11-C12, C21-C25, C31-C36). The findings below are therefore strong
where several ranges agree and provisional where one passage carries them.

## Findings by decision

### Translation (P05 / P06): Lilly uses the structural form

- **Definition in use (p.317):** "If the Significators aspect not one
  another, but some Planet transfers their influence one to another, and this
  with a benevolent aspect, then shall the matter be brought to passe by one
  signified by that Planet."
- **Worked cases:** C07 (p.200), C08 (p.220, the Moon translating Mars to
  Saturn), C13 (pp.387-388), C14 (p.390). None checks that the principals had
  separated from a good aspect, that the translator is received by the
  principal it leaves, or that the translator is lighter than both.
- **C13 goes further:** Jupiter, "still applying" to Saturn's sextile,
  receives Saturn's virtue and transfers it to the Sun, "meeting with no
  manner of prohibition, abscission or frustration untill his perfect ☌ with
  the ☉". The translator had not separated from the first principal; Lilly
  calls this "the maine occasion, without which in this Figure it could not
  have been".
- **Conditions Lilly does state** (in neither P05 nor P06):
  - the carrying aspect is benevolent (p.317), though p.205 and the C07
    figure also allow a square or opposition, with more difficulty;
  - the translator is not retrograde, combust, cadent or afflicted
    (pp.317-318, 433-434);
  - the planet that receives the translated light must not be an impeded
    infortune unless that infortune is itself received (p.186);
  - the route is undone if the receiving, heavier planet passes the light on
    to a planet with no signification in the question (p.433);
  - no prohibition, abscission or frustration before the perfect aspect
    (pp.317, 387-388).
- **Implication:** P06's three conditions (principal history, reception of
  the translator by the principal it leaves, no other contact in between) do
  not describe Lilly's practice. P05 is closer but too narrow: it requires
  separation from the first principal (C13 does not) and adds heaviness, which
  Lilly never checks for a translator.

### Prohibition (B01 / B02): an interruption from either side

- Named often, worked through rarely: pp.301, 305 ("frustrates their aspect,
  or prohibits them, or interjects his Rayes"), 317, 402, 433, 445.
- **C13 (p.388):** "♂ was neerer ♀ then ♄, and so interposed his influence,
  or kept off ♄". The interposer is simply nearer one principal.
- No passage requires the interposer to touch both principals or to be
  swifter. **The record supports `interposition_to_either`.**
- The hindering planet is described as an "evill" planet whose house shows
  who hinders (pp.305-306, 311).

### Refranation and frustration (B03 / B04)

- **Frustration applies to aspects, not only the conjunction:** "frustrates
  their aspect" (p.305); "the application of the Significators frustrated"
  (p.305); a trine in C08 checked for "abscission or frustation ere the
  perfect aspect" (p.220); the tenth lord frustrating a conjunction means
  agreement only after going to law (p.373), so delay rather than denial. On
  p.409 "perfect ☌ ... whether by body or aspect" uses "conjunction" for
  perfection by aspect too. **B04's conjunction-only scope is too narrow.**
- **Refranation is never named in Book II.** The operative idea is
  "Retrogradation of the principall Significators intervening" before the
  perfect aspect (p.317), which blocks the match. "Principall Significators"
  is plural: a retrograde station of either principal intervenes. In C06
  (p.198) a retrograde Saturn applying by retrogradation gives sudden news,
  so retrograde application itself is valid; it is a station intervening
  before perfection that breaks it.
- **Implication:** B03 should not exempt a station of the heavier principal;
  the current `station_of_heavier_not_refranation` note follows p.111's
  example too literally.

### Heaviness (H01): a fixed quality, kept apart from who applies

- **C06 (p.198):** "♄ though a ponderous Planet, yet being Retrograde and in
  more degrees of the Signe then ♀, doth by Retrogradation apply to meet her".
  Saturn keeps "ponderous" while retrograde; motion decides who applies.
- Saturn is "a ponderous Planet, and of slow motion" (p.242); Jupiter "a slow
  and ponderous Planet" (p.439); "more weighty" and "superiour Planet" are
  synonyms in one sentence (p.372).
- The heavier planet is the **receiver of the disposition** (pp.225, 229,
  433, 447, 449). Comparisons ("the lighter Planet", "more weighty then either
  of them") are never computed from instantaneous speed.
- **Implication:** the record supports `traditional_order` for heaviness and
  does not support `instantaneous_speed`. Who applies is a separate question
  answered by motion, as the runtime already does through the relation at the
  query; the heaviness reading should not decide which principal applies.

### Collection (P07): the collector receives, and is heavier

- p.225: the collector is "more ponderous then themselves" and "the receiver
  of their disposition"; p.304 and p.448 likewise ("more weighty then either
  of them").
- **Direction of reception:** p.186 says an infortune collector "destroyes the
  matter ... unlesse himselfe receive both the Significators; if he receive
  one onely of them, it matters not, the matter will not be performed". C09
  (p.239) would have been helped by a collection where "that Planet so
  collecting had received ♄ or ☿". Lilly's Book II practice runs **collector
  receives the principals**; p.126's wording runs the other way (both
  principals receive him). This is a genuine textual tension, not a
  misreading.
- p.446: collection "by any aspect, with or with no Reception", the collector
  "not Retrograde, Combust or Cadent, or goe out of that Signe" before the
  conjunctions; pp.433-434 the same.
- **"Do not behold"** is never used as a test between the principals; in C09
  collection is offered although the principals were applying by opposition.
  Neither P07 beholding reading is confirmed.

### Good, proper and friendly houses (Q01): topic-specific lists only

| Page | Context | Houses named |
|---|---|---|
| 229 | children (fifth) | second, eleventh, ninth |
| 234 | fifth-house question | tenth, eleventh, fifth, third, ninth, first, second |
| 317 | marriage | ☌ in the first, eleventh or tenth ("hardly in the seventh"); ⚹/△ out of the 1st-11th, 9th-7th or 7th-5th |
| 448 | office (tenth) | tenth, eleventh or fifth |
| 190, 193, 212, 379 | general | sixth, eighth and twelfth are ill |

There is no single list. **Q01's decision stands:** good houses are evidence
supplied for the question, not a Moira default; a future helper could offer
these source lists by topic, attributed.

### Reception (P08): it changes the aspect, not the blockers

- With reception a square or opposition perfects "with a little difficulty";
  without it "there's onely hopes" (p.317), or "never" (pp.330, 385). A square
  or opposition with mutual reception equals a sextile or trine without it
  (p.372).
- Some rules perfect by reception or reception plus house with no aspect
  (pp.210, 315, 445, 446, 449, 458); C27 (p.441) has "Reception ... but no
  aspect" and is judged negative; reception after separation leaves "nought
  but opportunity" (p.315).
- p.317 keeps the blockers "with or without Reception": "no prohibition,
  frustration or abscission, or Retrogradation of the principall Significators
  intervening".
- **Implication:** P08 as its own route is supported, and reception should
  also be able to qualify a square or opposition on the direct route. No
  passage lets reception override prohibition, frustration or retrogradation;
  the current "never overrides" rule stands.

### Dwelling in houses (P09): Book II treats it as a route

- p.186: "if the Significator of the thing demanded be found in the
  Ascendant, or hastening to the ☌ of the Significator of the Querent, it
  imports the matter enquired of, or thing desired shall come to the Querent,
  receptions notwithstanding".
- p.205 (purchase): "But if this dwelling in houses be not, yet if the ☽
  transferre the vertue ... the Bargaine will be concluded".
- p.444: the lighter tenth lord in the first attains the office "though no
  aspect be betwixt them".
- **Implication:** this conflicts with pp.126-127, where Lilly says the
  Ancients' dwelling rule "holds not true" unless the Moon also translates.
  Book II uses dwelling as a positive testimony in its own right. P09 should
  keep both: the p.126-127 rejection as one reading and the Book II route as
  another, each attributed.

### Malevolent aspect (B05), conjunction and house class (P01)

- "Malevolent/evill" is used of the malefics (pp.191, 210, 226), of the lords
  of the sixth, eighth and twelfth (pp.156, 227), and of the square and
  opposition (pp.185, 210, 212). The hindering contacts in practice pair a
  malefic or evil-house lord with a square or opposition, without reception
  (pp.227, 409, 433, 446).
- **Implication:** neither B05 reading matches alone. A third reading,
  **square or opposition from a malefic or from the lord of the sixth, eighth
  or twelfth, without reception**, fits the most passages.
- The conjunction is "not properly an aspect" (p.222) and "best of all
  performes" (p.217). House class changes speed and ease (pp.303, 433, 446);
  p.433 is harsher for cadent houses ("destroyes", rarely sudden) than p.446
  ("backward and backward, yet at last is performed"). P01's qualifiers stand;
  the cadent case has two source wordings.

### Precedence and timing (K04, T01)

- Routes are alternatives tried in turn ("if none of these happen", p.304;
  the fallback order on p.225; p.444), never ranked so that one cancels
  another. C13 judges a translation decisive while a direct sextile was also
  pending; C08 stacks several routes. **K04 stands.**
- Timing comes from the perfecting contact (C06: the exact trine the same
  afternoon, p.198; C08: six weeks from six degrees, p.221; C13: the 29th of
  June conjunction, p.388). Symbolic conversion stays outside the core (T01).

## What this means for the runtime

Applied 2026-10-30 (see the Book II section of LILLY_P4_RUNTIME_2026-10-30.md).
The table keeps the proposal as written before that tranche; "Current
runtime" describes the runtime at the time of the collation.

| Decision | Current runtime | Book II evidence | Proposal |
|---|---|---|---|
| P05/P06 | two readings, no default | structural use, translator condition, receiver condition | add a `book_ii_practice` translation reading: translator separating **or still applying** to the first principal, no heaviness or principal-history test, translator not retrograde, combust or cadent, receiving infortune must be received |
| B01/B02 | two readings | interposition from either side (C13) | keep both; record `interposition_to_either` as the Book II-attested reading |
| B03 | applying principal only | either principal's retrogradation intervening (p.317) | add a reading counting a station of either principal |
| B04 | conjunction only | frustration of aspects (pp.220, 305, 373) | allow aspects under a Book II reading |
| H01 | three readings | fixed ponderousness (p.198) | record `traditional_order` as the Book II-attested reading; keep heaviness out of the applying test |
| P07 | principals receive collector | collector receives (p.186, C09); collector not retrograde, combust, cadent | add the reverse reception direction as a reading, and the collector's condition |
| P08 | separate route, never overrides | reception upgrades □/☍; never overrides blockers | let reception qualify □/☍ on the direct route as evidence; keep "never overrides" |
| P09 | rejected except lunar translation | positive route in Book II (pp.186, 205, 444) | add the Book II dwelling route as a second, attributed reading |
| B05 | malefic planet / hard aspect | malefic or evil-house lord by □/☍ without reception | add this third reading |
| Q01 | caller-supplied | topic-specific lists | keep caller-supplied; optionally offer attributed topic lists |

Where Book II settles a question across several ranges (structural
translation, interposition from either side, aspect frustration, fixed
heaviness, reception not overriding blockers), a default could now be
justified on source evidence. That choice changes runtime behaviour and is
left for explicit approval.
