# Lilly dignity, orb and reception decisions

Date: 2026-10-23. Parent packet: [Lilly core admission](README.md).
Candidate contract: `lilly_1647_core_candidate_2026_10_23`.
Status: **selected source data and operational decisions specified and fixture-checked;
new production profile not implemented or runtime-admitted**.

This tranche completes the requested dignity-table, orb-policy and directed
reception decisions, together with teaching-example fixtures. It does not
change existing v1 semantics. The machine-readable authority data and source
readings are in
[the fixture bundle](../../../../tests/fixtures/horary/lilly_core_decisions_2026_10_23.json),
with checks in
[the source-fixture tests](../../../../tests/unit/test_lilly_core_source_fixtures.py).
The [collation record](LILLY_CORE_COLLATION_2026-10-23.md) explains witness
differences, annotations and what was actually inspected.

## Dignity decisions

| ID | Decision | Source and reason | Limit / compatibility |
|---|---|---|---|
| DG01 | Use the photographed p.104 table as a named table, including its own terms and sect-active triplicity rulers. | Both checked witnesses agree on the Classic7 cells, 60 term segments and 36 face segments. | A generic Ptolemaic, Egyptian or Dorothean label is insufficient to select these data. |
| DG02 | Interpret terminal numbers as lower-inclusive, upper-exclusive intervals in continuous sign longitude. Normalize finite longitude modulo360. A sign ends at30 and the next begins at0. | P.105 explains the first six degrees of Aries and the succeeding six-to-fourteen interval; faces similarly run first ten, ten-to-twenty, twenty-to-thirty. | Exact mathematical endpoint handling is an explicit operational convention. It agrees with existing v1; ordinal wording is preserved separately from coordinates. |
| DG03 | Exaltation dignity applies throughout the exaltation sign; retain the printed exaltation degree as documentary data. | P.102 expressly allows exaltation whether near its particular degree or not. | The degree is neither a width nor a requirement to hit that exact coordinate. |
| DG04 | Use one sect-active triplicity ruler, without a participating ruler. Mars rules water by both day and night. | Pp.102,104-105. | Unknown sect leaves that basis unresolved where the two rulers differ; it does not erase known domicile, exaltation, term or face evidence. Water's identical rulers remain determinate. |
| DG05 | Treat D/N in the house column as labels of planetary domiciles. | P.104's table explanation. | Those labels do not disable a domicile because the chart has the opposite sect. |
| DG06 | Keep positive dignities, detriment, fall and peregrinity as distinct evidence. | P.112's Saturn10Aries versus Saturn27/28Aries examples. | A planet can lack positive essential dignity while being in fall. Neither condition creates a negative reception or a statement of dislike. |
| DG07 | Preserve the printed node exaltations in the documentary transcription; the candidate reception host/guest universe is the seven classical planets. | Both p.104 photographs print NorthNode/Gemini3 and SouthNode/Sagittarius3. | This explicit operational scope is not a claim that Lilly omitted nodes. Apparent node-fall additions in Wellcome are stored in the annotation layer. |
| DG08 | Take individual dignity point values from printed p.115: house5, exaltation4, triplicity3, term2, face1. | The separate printed fortitude table, corroborated by the prose. | Do not use the apparent added bottom row of the Wellcome p.104 copy as printed authority. No universal success score, probability or reception-intensity scale is admitted. |

The complete documentary table is in the fixture bundle, including house
markers, exaltation degrees, day/night triplicity, term and face terminal
numbers, detriment and printed fall cells. It was transcribed from photographs
before comparison with engine tables. The additional checks compare existing
v1 dignity results against those independent source data across both sects,
all seven planets and every sign, with term/face transitions tested on both
sides. Agreement supports this bounded table claim; it does not establish
horary's predictive accuracy.

## Orb decisions

| ID | Decision | Source and reason | Limit / compatibility |
|---|---|---|---|
| OR01 | Select p.107's second set for this candidate contract. | P.110 explicitly uses nine-degree full orbs for both Saturn/Jupiter and halves of7:30 and6:00 for Sun/Moon. | Lilly permits both sets. This is a versioned computational choice, not a claim that the first set is spurious. |
| OR02 | Store full orbs; combine a pair as `(fullA + fullB) / 2`. Keep exact arcminute arithmetic in the fixtures. | Pp.107,110. | The source units are not already halved moieties. |
| OR03 | Distinguish strict interior, exact boundary and exterior. Use strict interior for the candidate's active orb membership; a separating pair is fully separated at or beyond the boundary. | P.110 describes full separation when fully nine degrees distant. | The mathematical endpoint choice is explicit. Existing v1 retains its current inclusive membership rule. No historical arc threshold replaces numerical root tolerance. |
| OR04 | Each historical teaching example uses the table expressly instantiated in its passage. | P.107's Venus/Saturn example uses halves4+5, hence the first set; p.110 uses the second. | No automatic table switching to obtain a favorable answer. The candidate's selected table remains fixed and visible. |
| OR05 | Preserve the current v1 orb table and profile identity. | Existing admitted operational contract. | No shared constant, constructor default, native path, public export or server field changes in this tranche. |

Full orbs, degrees:

| Body | First printed set | Selected second set | Existing v1, unchanged |
|---|---:|---:|---:|
| Saturn | 10 | 9 | 10 |
| Jupiter | 12 | 9 | 12 |
| Mars | 7.5 | 7 | 7 |
| Sun | 17 | 15 | 15 |
| Venus | 8 | 7 | 7 |
| Mercury | 7 | 7 | 7 |
| Moon | 12.5 | 12 | 12 |

Thus Saturn/Jupiter has a nine-degree allowance in the selected candidate and
an eleven-degree allowance in existing v1. The fixture tests preserve both
identities. P.107's eight-degree Venus/Saturn trine is inside its expressly
used nine-degree allowance; under the second set it would sit exactly on an
eight-degree boundary. That passage therefore cannot be used to prove a
universal endpoint rule for the other table.

The p.110 six-arcminute discussion is stored as narrated separation. Its later
Saturn position is not supplied; the fixture does not invent a stationary
Saturn or claim to compute the actual later separation from incomplete data.

## Reception decisions

| ID | Decision | Source and reason | Limit / compatibility |
|---|---|---|---|
| RC01 | An edge says: host H rules a positive dignity at guest G's position. Preserve host, guest, basis, table, sect and snapshot. | P.112's reciprocal examples and p.126's receiving roles. | Dignity membership is separate from application, contact, strength, ability, willingness or a predicted result. |
| RC02 | Derive each direction independently across house, exaltation, triplicity, term and face. | P.112 allows essential dignity bases generally; its three numeric/sign examples distinguish them. | Same-basis mutual reception and mixed-basis reciprocal edges are separately reportable. A reverse edge is never implied by the first edge. Mixed-basis evidence is not automatically granted every mechanism's judgement force. |
| RC03 | A raw dignity edge needs no aspect. Preserve p.112's favorable reception-without-aspect testimony. | The passage explicitly discusses adverse or absent aspects. | It is not an unconditional yes/no route. A complete outcome rule still needs its own context, conditions, precedence and cases. |
| RC04 | Require an explicit snapshot epoch tag. Keep source-unspecified epochs unspecified; never silently transport question-time evidence to a contact. | The source does not formalize every evaluation epoch; dignity/sect can change. | This tranche specifies snapshot evidence. Full translation/collection epoch selection and precedence remain a later mechanism-admission gate. No date is manufactured for a didactic example. |
| RC05 | Translation reception: source principal receives translator by house, triplicity or term. | P.126's full translation passage. | Exaltation or face alone does not meet this particular requirement. The structural p.111 example does not supply every p.126 condition. |
| RC06 | Collection reception: principal A receives collector C, and principal B receives C. | P.126 explicitly says both principals receive him in essential dignities. | Reversing both edges changes the doctrine. Reception alone does not establish weight, non-beholding, both contacts or uninterrupted chronology. |
| RC07 | Separate self dignity from reception between distinct planets. | P.112 defines a relation between two planets. | The candidate edge excludes self edges; existing internal v1 helpers are not altered. |
| RC08 | Preserve unknown degree/sect as missing input at the affected basis. | House and exaltation can be known from a sign when term/face cannot. | Do not invent0 degrees, day sect or a missing event time. A known basis may coexist with other unresolved bases. |

Example direction receipts:

- Sun in Aries / Mars in Leo: Mars receives Sun by house; Sun receives Mars by
  house. Neither planet's exact degree is supplied.
- Venus in Aries / Sun in Taurus by day: Sun receives Venus by triplicity;
  Venus receives Sun by triplicity. Other supported dignity edges can coexist.
- Venus24Aries / Mars16Gemini: Mars receives Venus by term; Venus receives Mars
  by term. These interior positions do not alone settle terminal boundaries.

Generic reception vocabulary and the perfection helper's host/guest convention
must have an explicit adapter when the future runtime surface is implemented.
This task adds no adapter or new public reception API.

## Teaching-fixture admission

The bundle contains **eight groups / 27 subcases**. All retain null historical
epochs, no invented numerical speeds or event timestamps, and no predictive
admission. Contact order is source-narrated evidence where full motion is not
provided. Two inconsistent numeric assertions are explicitly quarantined.

| Group | Included evidence | What the checks establish |
|---|---|---|
| D01 | Platick trine; exact and narrated separating conjunction; full orb boundary; Sun/Moon sum; alternate arithmetic conflict | Named table, arithmetic and source-data boundaries, not a reconstructed trajectory |
| D02 | Bodily prohibition; two witness-specific aspectual versions | Both interposing contacts and role direction, with Saturn15/13 retained separately |
| D03 | Refranation with no later exact pair event supplied | The intended-contact/blocking fixture does not demand a completed event; precise station longitude remains null |
| D04 | Mercury's structural translation from Mars to Saturn | Role direction and derivable domicile reception; full p.126 success is not established |
| D05 | House/triplicity/term mutual reception; Saturn and Sun peregrinity examples | Directed bases, sect, partial inputs and separation of positive dignity from fall |
| D06 | Mercury/Mars/Jupiter frustration | The heavier intended partner's prior bodily contact, without inventing event times |
| D07 | Interior combustion/cazimi; shared ten-degree combustion inconsistency | Arithmetic and same-sign qualification; no false positive oracle from contradictory print |
| D08 | Mars hour with three water signs, Aries identity and Leo common nature | Three different agreement routes, not calculation of an actual planetary hour |

Clearly labelled synthetic controls supplement these source cases: changed
sect, missing degree/epoch, mixed reciprocity, reversed collection direction,
disallowed translation bases, dignity change between snapshots, orb edges and
equal solar distance across a sign boundary. They are not added historical
examples or observed outcomes.

The test-only reference predicates check this finite specification. Existing
production dignity functions are separately compared with the photographed
table. The existing v1 horary/perfection/doctrine suites remain the compatibility
check. This is not a new production judgement interpreter or a completed
astronomical reconstruction of the teaching narratives.

## Ambiguity disposition and remaining gates

- **A04:** selected table and Classic7 cell collation resolved for this tranche;
  full bibliographic printing-state determination remains open.
- **A05-A06:** candidate table and exact mathematical orb boundary selected;
  both historical alternatives and v1 policy remain preserved.
- **A08:** host/guest direction, five bases, mutuality representation and
  mechanism-specific receiving roles specified.
- **A09:** absence of an aspect does not suppress raw reception evidence;
  complete reception-only outcome admission remains open.
- **A13:** the ten-degree combustion inconsistency is confirmed in both
  photographs and quarantined, rather than silently repaired.
- **A17-A18:** reception direction/bases are specified; full mechanism epochs,
  principal history, heavier/lighter definition and precedence remain open.

The next implementation package can consume these table and reception
specifications. Moon/VOC, all-candidate chronology, no-exact blocker handling,
ties, symbolic timing and complete historical worked-case reconstruction remain
separate work. No runtime admission follows merely from this document.

## Verification receipt

Use the project `.venv` with downloads disabled and strict known-issue checking:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lilly_core_source_fixtures.py tests\unit\test_lilly_1647_doctrine.py tests\unit\test_classical_perfection.py tests\unit\test_horary.py -q
```

Local validation on 2026-10-23 passed **422 tests: 214 new source-fixture
checks and 208 existing compatibility checks**, with no failures, errors or
skips. The 27 source images used by the new fixture bundle were checked against
their cached byte counts and SHA-256 hashes. The original packet validator
also passed, including its 87 cached hashes and 26 local Markdown links.
Ruff and whitespace checks passed for the changed files. A separate read-only
source-to-artifact review found no concrete discrepancies; this is not an
independent human review or a completed bibliographic printing-state assessment.

Runtime modules, native code, v1 defaults, existing tests and historical
validation baselines are unchanged. Publication refreshes the required generated
documentation discovery metadata and synchronizes the wiki mirror; it does not
change runtime admission or historical execution evidence.
