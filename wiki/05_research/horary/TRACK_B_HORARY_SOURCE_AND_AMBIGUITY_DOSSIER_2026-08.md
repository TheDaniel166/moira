# Track B Horary Source and Ambiguity Dossier

Status: **source-locked; bounded atomic, Python, and REST admission verified in the Track B checkpoint**
Date: 2026-08-11
Baseline: `24e90f9fa4cdbe9692d6f70469df7863f4b15d36`
Lineage id: `lilly_1647_ca_books_i_ii_v1`
Implementation checkpoint: branch `codex/track-b-western-research-20260811`;
the admission commit containing this dossier is not a release, publication, or deployment

## 1. Purpose and boundary

This dossier identifies the historical authority, finite computational contract,
known conflicts, and validation fixtures for Moira's first Horary surface. It does
not authorize a universal Horary interpreter.

The admitted product is evidence, not judgement. It may expose:

- the question-time and chart-policy receipts supplied by the caller;
- the radical and turned house selected by the caller;
- principal querent, co-significator, and quesited assignments;
- separately typed considerations before judgement;
- reception witnesses already preserved inside `ClassicalPerfectionAnalysis`;
- the existing Lilly perfection analysis for the principal pair; and
- explicit exclusions, unresolved policies, and not-evaluable reasons.

It must not emit a yes/no answer, confidence score, advice, timing prose, outcome
prediction, inferred question topic, or synthetic ranking.

## 2. Governing source hierarchy

### 2.1 Normative witness

William Lilly, *Christian Astrology, Modestly Treated of in Three Books*, first
edition, London: Tho. Brudenell for John Partridge and Humphrey Blunden, 1647,
Books I and II.

- Edition record: [Open Library OL26480475M](https://openlibrary.org/books/OL26480475M/Christian_astrology_..._in_three_books._The_first_containing_the_use_of_an_ephemeris_..._The_second_)
- Public-domain scan: [Internet Archive / Wellcome item b30338724](https://archive.org/details/b30338724)
- Direct scan PDF: [b30338724.pdf](https://archive.org/download/b30338724/b30338724.pdf)
- Clearer EEBO-derived page images of the same 1647 edition:
  [Internet Archive item bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647)

The photographed 1647 pages govern whenever a transcription, modernization, or
secondary account conflicts with them.

### 2.2 Page map for the admitted contract

| Printed pages | Original-scan anchor | Contract use |
|---|---|---|
| 47-56 | 1647 scan, Book I | twelve-house structure and the house ruler as significator of the thing asked |
| 57-58 | [p.57](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n84/mode/1up), [p.58](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n85/mode/1up) | Saturn: Air triplicity by day; cold and dry |
| 62 | [p.62](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n89/mode/1up) | Jupiter: Fire triplicity by night; hot and moist |
| 65-66 | [p.65](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n92/mode/1up), [p.66](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n93/mode/1up) | Mars: Water triplicity wholly, by day and night; hot and dry |
| 69-70 | [p.69](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n96/mode/1up), [p.70](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n97/mode/1up) | Sun: Fire triplicity by day; hot and dry, more temperate than Mars |
| 73 | [p.73](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n100/mode/1up) | Venus: Earth triplicity by day; cold and moist |
| 76-77 | [p.76](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n103/mode/1up), [p.77](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n104/mode/1up) | Mercury: Air triplicity by night; own nature cold and dry |
| 80-81 | [p.80](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n107/mode/1up), [p.81](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n108/mode/1up) | Moon: Earth triplicity by night; cold and moist |
| 110-113 | 1647 scan, Book I | application, prohibition, refranation, translation, and related perfection vocabulary |
| 121-122 | [p.121](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n150/mode/1up), [p.122](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n151/mode/1up) | hour agreement and Lilly's Water/Aries/Leo examples that control the lookup semantics |
| 125-126 | 1647 scan, Book I | perfection by conjunction/aspect, translation, and collection |
| 491 | [p.491](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n522/mode/1up) | exact Regiomontanus is required for nativities but described as more scrupulous than necessary for ordinary questions |
| 519-523 | [p.519](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n550/mode/1up), [p.520](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n551/mode/1up), [p.521](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n552/mode/1up), [p.522](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n553/mode/1up), [p.523](https://archive.org/details/bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647/page/n554/mode/1up) | Book III chapter CI, exact construction by the Tables of Regiomontanus |
| 442-445 | 1647 scan, Book II | source-owned worked question suitable for assignment evidence |

The already admitted six-form perfection engine has its detailed scan audit in
`wiki/03_validation/WESTERN_ELECTIONAL_PHASE6_LILLY_PERFECTION_VALIDATION_2026-07-15.md`.

These citations close historical-source admission only. Executable admission
is recorded separately in section 12 and depends on the named tests and runtime
contracts; the citations do not prove the implementation by themselves.

### 2.3 Navigation and ambiguity witnesses

The following are lookup or comparison witnesses, not replacement authorities:

- Deborah Houlding's indexed [Christian Astrology Books I-II](https://www.skyscript.co.uk/CA/);
- Houlding's [Considerations before Judgement](https://www.skyscript.co.uk/considerations.pdf);
- Houlding's [Hour Agreement and Radical Questions](https://www.skyscript.co.uk/hour_agreement.pdf); and
- the [Skyscript house excerpt](https://www.skyscript.co.uk/lilly_houses.html).

Moira must not copy or redistribute the modern retyped edition. Compact factual
fixtures and citations must resolve back to the public-domain 1647 scan.

## 3. Named doctrine boundary

The v1 profile is the **Lilly 1647 English Horary synthesis**, not a generic
"traditional Horary" mode.

| Axis | Admitted v1 policy |
|---|---|
| Zodiac | tropical |
| Planets | Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn |
| Houses | explicit caller policy; no fallback; exact Regiomontanus may be selected through a separately named deterministic Lilly-compatible policy, but is not a universal Lilly mandate for ordinary questions |
| Sign rulers | Lilly's classical domicile rulers |
| Aspects | conjunction, sextile, square, trine, opposition |
| Perfection | `lilly_1647_perfection_v1`, composed without reimplementation |
| Question topic | explicit caller-supplied radical house; no text classification |
| Outcome | excluded |

Outer planets, asteroids, modern sign rulers, minor aspects, modern psychological
topics, and cross-author synthesis are outside this lineage.

## 4. Finite v1 input contract

### 4.1 Question identity

The public adapter caller must provide:

- a stable question id or label;
- a timezone-aware instant;
- latitude and east-positive longitude;
- an explicit calendar receipt when the fixture is historical;
- the source-grounded `question_proposed_and_figure_erected` time basis; and
- an explicit radical topic house from 1 through 12; and
- the exact caller-selected house-system id under the admitted strict
  no-fallback policy.

The public adapter computes the provenance-bearing `HouseCusps` receipt on its
owned reader. The lower-level atomic composer consumes that receipt together
with the exact house-system and strict policy receipts, and requires all three
to match. No transport caller may submit a preassembled house receipt bag.

The cited CA passage supports the time of proposing the question and erecting the
figure. Later practices based on when an astrologer understands a question, opens
a letter, or reaches settled self-perplexity are not admitted by this dossier.
They may be retained only as caller metadata and must make the Lilly-dependent
question-time receipt `not_evaluable`. The engine does not infer which event in a
conversation counts as the question.

### 4.2 Turned-house input

The caller may provide an ordered `perspective_path` plus one terminal
`topic_house`. Each perspective item is a 1-based house counted from the preceding
perspective; the topic house is counted once from the final perspective:

```text
perspective_path=(7), topic_house=1 -> radical 7
perspective_path=(7), topic_house=2 -> radical 8
perspective_path=(7), topic_house=3 -> radical 9
```

Starting from radical house 1, each conversion is
`((current + requested - 2) % 12) + 1`. The receipt retains every perspective
step, the terminal topic house, and the resolved radical house. An empty
perspective path resolves directly to the terminal topic house. The engine must
never encode the displayed 7/8/9 examples as three sequential turns.

## 5. Significator evidence

The bounded assignment contract is:

- principal querent: classical domicile ruler of the Ascendant sign;
- querent co-significator: Moon, retained as a distinct role;
- principal quesited: classical domicile ruler of the resolved topic-house cusp;
- optional descriptive witnesses are deferred. Lilly's text distinguishes planets
  in the Ascendant from planets aspecting the Moon or Ascendant lord; v1 does not
  replace that rule with a generic "aspecting the Ascendant" shortcut.

If the principal querent and quesited resolve to the same body, assignment remains
evaluated but pairwise perfection is `not_evaluable` with reason
`principal_significators_are_same_body`. The engine must not invent a replacement
significator.

Gendered natural significators, marriage-specific Moon separation/application,
human-description exceptions, and topic-specific overrides are deferred. They
conflict with a safe generic assignment rule and require their own source profiles.

## 6. Radicality and considerations

### 6.1 Hour agreement

The source-locked policy returns matched rule paths rather than one opaque
Boolean:

1. `same_planet`: hour ruler equals the Ascendant ruler;
2. `triplicity`: the hour ruler governs the triplicity of the **rising sign**
   under Lilly's day/night table; or
3. `same_nature`: the hour ruler and Ascendant ruler share Lilly's primary
   hot/cold and moist/dry nature pair.

Lilly's worked examples on pp.121-122 control the ambiguous phrase "of one
Triplicity." Mars hour with a Water sign rising qualifies because Mars governs
the Water triplicity; Mars hour with Aries qualifies through the same-planet
path; Mars hour with Leo qualifies because Sun and Mars are both hot and dry.
The v1 triplicity table is therefore Fire Sun/Jupiter, Earth Venus/Moon, Air
Saturn/Mercury by day/night respectively, and Water Mars by day and night. The
v1 nature groups are hot/dry Sun and Mars, hot/moist Jupiter, cold/dry Saturn
and Mercury, and cold/moist Venus and Moon.

This policy does not admit participating rulers, outer planets, a generic
same-element comparison, or Bonatti's alternative sign-occupation comparison.
Mercury's variable gender or beneficence is irrelevant here; Lilly's stated own
nature, cold and dry, governs this one lookup. A failed match is typed evidence,
not automatic rejection of the chart. The planetary-hour receipt must still
state the sunrise/sunset and local-time algorithm used. If that receipt is
missing, hour agreement is `not_evaluable`.

Source admission of the triplicity and same-nature paths does not mark their
engine implementation, fixtures, exports, or public API complete.

### 6.2 Regiomontanus construction policy

CA Book III chapter CI, pp.519-523, provides a deterministic construction from
right ascension, house-position pole elevations, 30-degree equatorial
increments, and oblique-ascension tables with proportional interpolation. CA
p.491 supplies the controlling qualification: Lilly calls that punctilious
method proper for a nativity and more scrupulous than necessary for ordinary
questions.

Moira may therefore admit an explicit named Regiomontanus option as a
deterministic **Lilly-compatible** Horary house policy. It must not be a hidden
default and must not be described as Lilly's mandatory house construction for
every ordinary question. The caller must continue to supply a provenance-bearing
house receipt and strict no-fallback policy. Source admission here does not mark
house computation, profile wiring, or any public contract complete.

### 6.3 Consideration states

Every consideration is independently typed as `satisfied`, `caution`,
`not_applicable`, or `not_evaluable`. No collection of considerations fabricates
`radical=false`.

Atomic v1 evaluates only finite geometry and preserves unresolved qualifications:

- Ascendant below 3 degrees of its sign;
- Ascendant at or above 27 degrees of its sign;
- Moon in the Via Combusta under the explicitly named computational interval
  `[15 Libra, 15 Scorpio)`; endpoint convention is policy, not a claim that Lilly
  supplied interval notation;
- Saturn in the first house;
- Saturn in the seventh house;
- combust first-house ruler only when a separately admitted solar-proximity receipt
  is supplied.

The early/late Ascendant witnesses expose the boundary fact and mark Lilly's
contextual exception or qualification as unresolved. "Moon in late degrees," the
void-of-course sign mitigations, seventh-cusp/lord impediment, and evenly balanced
testimonies are excluded from evaluated atomic v1 until their thresholds and input
schemas are source-locked. Inputs insufficient to establish an admitted condition
yield `not_evaluable`, never an assumed absence.

## 7. Reception, disposition, and perfection composition

Atomic v1 does not independently recompute reception. It retains only reception
witnesses already owned by `LILLY_1647_PERFECTION_V1` inside the supplied
`ClassicalPerfectionAnalysis`. Any future dispositor surface must use a separately
named classical domicile-only policy; it must not invoke a generic dignity default.
This evidence remains separate from:

- a static domicile-dispositor chain;
- translation of light;
- transfer of virtue; and
- any interpretive claim about willingness or outcome.

The profile delegates its principal-pair perfection computation to
`moira.classical_perfection.lilly_perfection_at`. That engine already owns one
ordered event stream and the admitted witnesses for:

- direct perfection;
- translation;
- collection;
- prohibition;
- refranation; and
- frustration.

Track B must not fork those calculations. It wraps the returned
`ClassicalPerfectionAnalysis` with question/significator receipts and propagates
its indeterminate states.

Two source distinctions remain visible:

- structural translation is not identical to Lilly's stricter qualifying
  translation; and
- Lilly's narrow bodily-conjunction frustration must not be generalized to every
  aspect by the Horary wrapper.

## 8. Ambiguity ledger and explicit deferrals

| Question | v1 decision |
|---|---|
| What time begins a question? | explicit named basis; never inferred |
| Which house describes free text? | caller supplies the house |
| Which house system? | explicit caller policy; no fallback; named Regiomontanus is an optional deterministic Lilly-compatible policy, not a universal Lilly mandate |
| What if house calculation falls back? | profile is not evaluable; no fallback |
| What if both principals are the same body? | assignments evaluated; pair perfection not evaluable |
| Is failed hour agreement fatal? | no; evidence only |
| Are considerations refusal rules? | no; separate cautions/evidence |
| Which author resolves a conflict? | Lilly 1647 scan within this profile; other authors require other profiles |
| How are degrees converted to time? | deferred |
| Can the engine answer yes/no? | excluded |
| Can it infer a topic or describe a person? | excluded |
| Can generic and stricter translation be collapsed? | no |
| Can one-way reception be labeled mutual? | no |

## 9. Source-owned validation fixtures

### 9.1 Primary assignment fixture

Lilly, CA printed pp. 442-445, "If Attaine the Philosopher's Stone?", is admitted
for assignment evidence. The fixture must use compact facts checked against the
scan:

- Ascendant and its classical ruler represent the querent;
- the explicitly selected ninth house and its ruler represent the relevant
  knowledge or art in Lilly's worked judgement; and
- the printed chart's cusp-placement ambiguity is preserved rather than repaired.

The fixture validates house/ruler assignment and traceability, not Lilly's prose
outcome.

### 9.2 Independent reconstruction fixture

Lilly's 1644 question "A Gentlewoman desired to know if she should have an aged
man" remains a **research comparison only**, outside the named CA 1647 lineage:

- 14 June 1644 Old Style / 24 June 1644 Gregorian;
- a modern reproduction labels the chart 10:30 GMT, which must not be treated as
  the unqualified historical clock basis;
- Mercury as first-house ruler and Jupiter as seventh-house ruler;
- Venus day and Jupiter hour;
- a reported airy-triplicity radicality interpretation, not yet an engine golden; and
- the turned eighth as the other person's second.

It is not an atomic-v1 numerical golden. Admission requires a source-locked 1644
edition/scan plus an explicit calendar, clock, longitude, and time-conversion
receipt. The original printed longitudes and a modern ephemeris reconstruction
must remain separate provenance modes.

Navigation witnesses:

- [Skyscript worked chart](https://www.skyscript.co.uk/aged.html)
- [independent modern discussion](https://tonylouis.wordpress.com/2017/11/30/should-i-questions-in-horary-astrology/)

## 10. Adversarial cases governing public admission

- early and late Ascendant boundaries at exactly 3 and 27 degrees;
- Via Combusta start/end boundaries;
- missing planetary-hour receipt;
- same-body principal collision;
- single and multi-step turns, including wrap from house 12 to 1;
- invalid zero/negative/greater-than-12 turn steps;
- explicit house-policy high-latitude failure with no fallback;
- historical Julian/Gregorian mismatch;
- generic versus qualifying translation kept distinct;
- simultaneous or tied blocker events propagated from the perfection engine; and
- unavailable Moon/VOC or reception dependencies yielding typed not-evaluable
  results.

## 11. Research-gate decision

The Horary source gate admits the narrowed atomic profile: explicit strict house
geometry, formal turned-house arithmetic, classical ruler assignments, all
three source-locked Lilly hour-agreement paths, finite geometric considerations,
and composition of the already admitted perfection receipt. The public adapter
uses an explicit caller-selected house policy; Regiomontanus remains a named
Lilly-compatible option with the p.491 qualification rather than a hidden
universal default.

Contextual considerations and the 1644 historical reconstruction remain open
fixture or doctrine work. The gate does not pass for topic inference, universal
judgement, historical timing conversion, medical/legal/financial advice, or a
cross-author Horary synthesis.

## 12. Executable admission receipt

The Track B checkpoint implements and verifies the admitted calculation-only
surface through:

- `moira.horary` atomic vessels, pure evidence composition, and the reader-bound
  `horary_evidence_at` adapter;
- five curated root/facade exports, with detailed input and evidence receipts
  remaining module-owned;
- `Moira.horary_evidence_at`, bound to the facade's existing reader;
- one strict `POST /v1/horary/evidence-profile` transport; and
- dedicated public-contract, route, OpenAPI, mismatch, forgery, and typed
  not-evaluable tests.

The focused engine/public slice passed 160 tests; the dedicated Horary
route/OpenAPI slice passed 19 tests, with the shared route-registration,
startup, Hellenistic OpenAPI, and adversarial-server regressions also green.
Those are regression and contract receipts, while the 1647 page witnesses above
govern doctrine. The implementation preserves explicit question time, location,
house policy, turned context, planetary hour, significators, considerations,
sect, and optional bounded perfection evidence. It still emits no answer,
outcome, score, confidence, advice, inferred topic, or timing prose.
