# VED-013: Chara Dasha variants and Argala grading research

**Date:** 12 October 2026. **Status:** Research complete for the comparisons below;
the original research checkpoint preceded implementation. The selected profiles
now have an [implementation receipt](../03_validation/VEDIC_CHARA_ARGALA_VALIDATION_2026-10-12.md)
and [standard](../02_standards/JAIMINI_PROFILE_ASSESSMENT_STANDARD.md).
**Baseline:** engine `f8e9a615f04659c77a03713b302cb7189f4d890c`, version 6.9.9,
project Python 3.14.3. **Owner:** [VED-013](VEDIC_REMAINING_WORK_REGISTER.md).

## 1. Findings and recommended scope

There is substantial usable source material. The local library contains explicit
Argala grades, obstruction qualifications, two Rangacharya Chara methods, a
separate female-chart calculation, and worked examples. Several files are scans;
empty text extraction did not mean missing doctrine. The manual whose filename
says 2009 identifies its first edition and copyright as **2007** on PDF page 3.

The next implementation plan should distinguish five concerns:

1. Preserve the admitted Rao-compatible computation under its existing identity.
   Other methods change the seed, sequence, counting direction, duration,
   co-lord selection, subperiods and clock. A single additional boolean cannot
   identify those differences.
2. Make **Argala count grade**, **obstruction outcome**, **benefic/malefic
   character**, and **Yogada/Argala yoga classification** separate outputs.
   A strong intervention is not necessarily beneficial or unobstructed.
3. Start additional Chara admission with the precisely named Rangacharya manual
   methods. The second method's 24 published sequence rows and seven male-chart
   durations reproduce independently. Its female example has one identifiable
   conflict. The first method also requires an explicit zero-duration decision.
4. Prioritize BPHS count grades and explicit obstruction evidence. Define node
   participation, reference ownership, the three-malefic threshold and quarter
   qualifications in each selected profile. Do not describe the existing
   seven-body count algorithm as a complete classical or Rath/PVR implementation.
5. Repair direct-engine/REST admission differences alongside new contracts.
   Missing source/context must remain visible, rather than becoming a fabricated
   strength score or a confident obstruction verdict.

This packet recommends scope for planning. It does not implement any profile,
certify predictive accuracy, or claim that every named tradition is fully specified.

## 2. Source ledger and method

Local paths are relative to `C:\dev\ASTROLOGY-BOOKS-DATABASE`. PDF coordinates
are one-based; printed page numbers are separate. Local translations are witnesses
to particular readings, not a critical edition of an uncontested ancient text.
Related reflows/republications are not independent witnesses.

| ID | Source and inspected coordinates | Use and evidence class |
| --- | --- | --- |
| S05 | `Classics books/BPHS-Santhanam-Vol-1.pdf`, PDF 310–315, printed 311–316, chapter 31, especially 2–9½ and 10 | Classical translation and translator commentary: Argala formation, grades, strength, nodes, quarters. Governing scans visually checked. |
| S06 | `Classics books/BPHS-Santhanam-Vol-2.pdf`, PDF 63–66, printed 553–556, 46.155–167; PDF 132–134, printed 622–624, 51.3–12 and example | Chara duration/co-lords, ninth-sign direction and distinct rasi subperiod rules. Diagram and duration table visually checked. |
| S07 | `Classics books/JaiminiSutrasCompleteEng.pdf`, PDF 1, 25, 30–32, 53–57, 185–188 | Reflow attributed to Bangalore Suryanarain Rao, revised by B.V. Raman, sixth edition 1984. Sutras 1.1.5–10 and commentary; sign strength in 2.3. This is not an image of the original typesetting. |
| S11 | `Books by Authors/Jaimini/JAIMINISUTRAS (1).pdf`, PDF 8–11 | Overlapping reflow of S07's Argala material; corroborates extraction, not independent doctrinal authority. |
| S08 | `Books by Authors/Jaimini/A Manual of Jaimini Astrology_Iranganti Rangacharya 2009.pdf`, PDF 1–9, 18–25, 71–83; printed 1–3, 12–19, 65–77 where applicable | Primary modern author's manual, first edition 2007. Scan recovered with Windows OCR; critical pages and all method-2 sequence tables visually checked. |
| S12 | `Books by Authors/Jaimini/SP-jaminicharadasaknraoBW1.pdf`, PDF 6–7, 13–14 | K.N. Rao article compilation; explicit rejection of exaltation/debilitation duration adjustments and partial second-cycle witness. Not the full Rao book. |
| S02 | `#Articles/CharaDashaPart1BW.pdf`, PDF 5–9 | Yuvraj Singh's teaching article, secondary lineage exposition: direction, co-lords, subperiods. Does not establish the complete co-lord strength chain. |
| S09 | `Books by Authors/Jaimini/jaimini-maharishis-upadesa-sutras.pdf`, 9 PDF pages | Rath book cover/front matter and opening sutra only: final scanned spread starts 1.1.1. This particular local file does not contain the Argala clauses. |
| W01 | P.V.R. Narasimha Rao, [*Unlocking the Power of Parasara's Chara Dasa*](https://www.vedicastrologer.org/articles/pp_chara_dasa.pdf), 14 April 2014, v1, PDF 3–4, 6–7, 23, 28, 39, 46 | Author-hosted primary modern formulation. See section 3.5 for its bounded assessment. |
| W02 | Sanjay Rath, [*Narayana Dasa*](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf), inspected PDF 42–54 | Primary authored book hosted by a third party; distinct dasa family, not evidence for changing Rao's second cycle. |
| W03 | P.V.R. Narasimha Rao, [*Vedic Astrology: An Integrated Approach*](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf), PDF 117–118, 122–123, 214–216; printed 105–106, 110–111, 202–204 | Author-hosted textbook; sections 10.6–10.7, Exercise 16 and 15.5. Separately identified from W01. |
| W04 | Sanjay Rath, [*Argala: Planetary Intervention*](https://srath.com/jyoti%E1%B9%A3a/amateur/argala-planetary-intervention/) | Primary author explanation and worked comparisons; see section 4.4. |
| W05 | Iranganti Rangacharya, [*Timing Marriage According to Jaimini*](https://saptarishisshop.com/timing-marriage-according-to-jaimini-by-iranganti-rangacharya/) | Author-attributed publisher article distinguishing Neelakanta and RB-NS methods. Chart 1's marriage date conflicts between 29 April and 29 May 1959; unsuitable as an exact dated oracle without reconciliation. |

Online searches also located Shanmukha's RB-NS exposition and references to
*Jataka Sara Sangraha*, *Sutrartha Prakasika* and *Jaimini Sutramritam*. These
are acquisition/collation leads. The manual supplies primary evidence for
**Rangacharya's published formulation**; an uncollated older commentary is not
silently substituted as its exact authority. No claim of general source absence
is made. Search-result snippets, retailers and other software were not used as
the computational authority.

Twelve relevant local PDFs were indexed and fingerprinted; not every indexed
article was fully collated. Text extraction, per-page OCR, rendered witnesses,
downloads and probes are private research artifacts under
`C:\dev\outputs\ved013-research-2026-10-12`. Only paraphrased findings,
coordinates, fingerprints and limited numerical witnesses belong in this packet.

## 3. Chara variants: what actually changes

### 3.1 Existing Rao-compatible Moira profile

The [cycle standard](../02_standards/CHARA_DASHA_CYCLE_STANDARD.md) remains the
authority for `moira_kn_rao_existing_v1`. It starts at Lagna, traverses adjacent
signs according to the ninth sign's footed group, and calculates durations using
the dasha sign's own footed group. It subtracts one from the inclusive lord count,
uses twelve for an own-sign lord, and makes no dignity adjustment. Its subperiods
divide the period equally and put the dasha sign last. The second cycle repeats
the first; the clock is an explicit fixed 365.25-day year.

S12 page 6 directly explains Rao's rejection of adjustments, including Sagittarius
with Jupiter in Capricorn producing zero years under subtraction. His rationale
does not erase the other tradition. S02's direction and duration rules are
different tables, and must not share one parity flag.

Moira's optional co-lord chain remains its retained convention: classical-body
companions, dual over fixed over movable, then ordinary within-sign degree and a
primary-lord exact tie. The complete chain is not established by S02's instruction
to choose the stronger lord. Preserve the existing receipt and compatibility;
do not rename it as fully collated Rao, BPHS, PVR or Rath authority.

### 3.2 BPHS Santhanam Chara

S06 46.155–167 supports the footed groups and ninth-from-Lagna direction, dual
Scorpio/Aquarius lordship, occupancy/number/modality comparisons and
exaltation/debilitation adjustment. In its comparison, dual signs outrank fixed
signs, which outrank movable signs. The remaining tie refers to the larger
duration; the exalted-lord instruction also needs its precedence stated explicitly.
The existing degree tie-break is not that instruction.

The prose's inclusive count needs to be read with examples and the one-year
reduction tradition; it is not sufficient to copy one translated sentence in
isolation. S07 PDF 55 itself preserves competing counts and examples, and is not
an independent, ambiguity-free implementation specification.

**Published witness:** S06 printed 556 gives Aquarius through Capricorn durations
`8, 1, 1, 9, 8, 1, 7, 7, 4, 6, 2, 5`. The preceding diagram puts the Lagna,
Mercury, Jupiter and Venus in Aquarius; Sun in Capricorn; Mars in Taurus;
Moon/Rahu in Gemini; Saturn in Scorpio; Ketu in Leo. The paragraph explicitly
selects Rahu for Aquarius, yielding eight years, and gives Aries one year.
However, the diagram's nodes are not opposite. Its Scorpio entry also does not
follow a straightforward equal-occupancy/equal-modality/larger-duration reading
(Mars gives six; Ketu nine). Preserve the printed diagram and table as conflicting
evidence. Do not invent corrected node positions or degrees to obtain a full
oracle. The two explicitly explained durations remain usable bounded witnesses.

**Subperiods:** S06 51.5–12 divides a period by twelve, considers the stronger
dasha sign/seventh, and gives modality-dependent sequences. These are not the
current adjacent-sign, dasha-sign-last subperiods. The displayed fixed-sign
example at printed 623–624 is a separate fixture candidate. A BPHS profile must
resolve seed/strength and sequence composition together, or explicitly admit
mahadashas only.

**Admission decisions still needed:** exact co-lord precedence/ties; selected
node dignities if used; treatment of zero years; own/exalted duration precedence;
subperiod composition; year basis; and second-cycle duration. The sentence that
Aquarius starts again does not independently settle every later duration.

### 3.3 Rangacharya manual: method 1

S08 printed 65–66 starts at Lagna and follows the ninth sign's footed group.
Its duration direction follows the dasha sign's footed group. For a non-own-sign
lord, subtract one from the inclusive count, then add/subtract one for
exaltation/debilitation. Own-sign duration is stated as twelve. The selected
passage works with ordinary sign lords; a node co-lord chain must not be borrowed
from another chapter or school without an explicit admission decision.

For the manual's example, Scorpio Lagna, Mars/Venus in Gemini and Mercury in
Taurus give Scorpio **7**, Libra **8**, Virgo **4** years. Sequence direction is
reverse although Scorpio's duration count is forward.

This is a useful named candidate, not just another label for the existing default.
Sagittarius/Jupiter-in-Capricorn produces **0 years** under the stated adjustment.
This has a real interval-contract consequence: a zero duration cannot produce
twelve strictly increasing subperiod endpoints. The plan must preserve the source
arithmetic and explicitly choose how zero periods are represented/scheduled;
silently clamping them to one or twelve is unsupported. Likewise, make the
own-sign exception's precedence over exaltation explicit.

### 3.4 Rangacharya manual: method 2 and female-chart branch

The names below identify the **manual's** recipes. W05 supports the broader
lineage distinction, but does not turn every manual detail into an independently
collated ancient RB-NS rule.

| Component | Method 2, male-chart recipe: printed 66–68 | Female-chart recipe: printed 68–70 |
| --- | --- | --- |
| Seed | Lagna | Fourth from Lagna by prakriti reckoning: zodiacal for odd Lagna, reverse for even Lagna |
| Direction | Ordinary odd/even Lagna; not the ninth sign's footed group | Published tables agree with ordinary natal-Lagna parity; equivalent to the stated vikriti reversal at the shifted seed |
| Sequence | Movable: adjacent; fixed: every sixth; dual: trinal triplets followed by the next sign's triplet | Same modality patterns from the shifted seed |
| Duration direction | From lord **to dasha sign**, controlled by the **lord's sign** parity | From lord **to dasha sign**, controlled by the **dasha sign** parity |
| Subtraction | Inclusive count, **no subtraction** | Inclusive count **minus one** |
| Exceptions | Own-sign lord: twelve | Own-sign lord: twelve; lord opposite dasha sign: ten |
| Dignity adjustment | None | None |

Use ordinary sign numbers 1–12 for this parity. In zero-based arithmetic, a
modality-independent dual sequence is generated by offsets
`[0,4,8,1,5,9,2,6,10,3,7,11]`, multiplied by the chosen direction. Fixed signs
use successive five-step offsets. These are **derived encodings** of the printed
tables, not quotations or already-admitted engine algorithms.

Independent research calculation matches **all 24 male/female sequence rows,
288 sign cells**. Examples that discriminate methods include:

- Gemini male seed: Gemini, Libra, Aquarius, **Cancer**, Scorpio, Pisces, ... .
  Do not substitute another family's post-trine jump.
- Taurus female seed: Aquarius, Virgo, Aries, Scorpio, Gemini, Capricorn, ... .
- Aries with Mars in Taurus: method-2 duration **2**, versus **1** under the
  unadjusted footed count-minus-one formulation. Mars in Gemini gives method 2
  **11**, versus **2** under that formulation.

For the manual's Chart 1, the seven printed method-2 periods reproduce exactly:
Scorpio 6, Gemini 12, Capricorn 11, Leo 10, Pisces 12, Libra 5, Taurus 12.
The classical sign map is Sun/Mercury Taurus; Mars/Venus Gemini; Moon Capricorn;
Jupiter Pisces; Saturn Scorpio. Lagna is Scorpio. No invented degrees are needed.

For printed 70's Indira Gandhi example, the map is Sun/Mercury Scorpio, Mars Leo,
Venus Sagittarius, Moon/Saturn Cancer, Jupiter Taurus, with Cancer Lagna. Applying
the female prose gives, in sequence:

`Aries 8, Pisces 2, Aquarius 7, Capricorn 10, Sagittarius 7, Scorpio 9,
Libra 10, Virgo 2, Leo 9, Cancer 12, Gemini 7, Taurus 7`.

The page prints **Cancer 10**, despite placing Moon in Cancer and explicitly
giving twelve for an own-sign lord. Thus **11/12** durations agree. This is a
visually confirmed source conflict, not an OCR repair or a reason to alter the
formula secretly. A prose-selected profile can identify the rejected table entry
and preserve both readings in its source fixture.

No fully specified antardasha/year/second-cycle rule was established for these
manual recipes in the inspected sections. Do not fill those fields from Rao.
The source's male/female branches should be caller-selected calculation recipes;
do not infer a branch from a name, account data or the astronomical chart.

### 3.5 PVR 2014: distinct candidate, explicit unresolved rules

W01 selects Lagna/Moon/Sun by lord strength, permits vargas, uses ninth-sign
footed direction and no dignity-year adjustment. Its co-lord
modality order is **movable > fixed > dual**, followed by longer duration.
Seed comparison uses dignity, companions, placement, degree and parity, with
weakness exceptions. Antardashas are omitted; true tropical solar years recommended.

Example 1 supplies sign-level co-lord witnesses. But Example 33, PDF 39, chooses
Sun with four companions over an exalted Jupiter, overriding the apparent
dignity-first priority. Example 22's prose says reverse while its table advances.
Example 17 identifies quarter-degree combustion, without defining every weakness
cutoff. Resolve priority, thresholds, remaining ties and clock before admission.

### 3.6 Rath Narayana: researched, separately named

W02 starts from the stronger Lagna/seventh and supplies modality-dependent
sequences, Saturn/Ketu exceptions, dignity-adjusted periods, co-lord decisions,
subperiods and a complementary second cycle: twelve minus the first duration.
Its movable branch is also called Chara, but that does not make the whole family
identical to Rao Chara or the manual's method 2. In particular, its dual sequence
uses a different post-trine jump. Tables 10–14 and the first/second-cycle worked
tables are useful future witnesses. Preserve a separate Narayana identity and
admission package; do not import its complement cycle into the existing endpoint.

## 4. Argala: grading is more than one strength number

### 4.1 BPHS count grade and qualification

S05 chapter 31 specifies primary positions 2/4/11 and corresponding blockers
12/10/3, plus 5/9. Its one-, two-, and more-than-two-planet distinction gives
limited, medium and excellent effects respectively. This supports an ordinal
**count grade**. Mapping those categories to a universal numeric weight, percentage
or Shadbala threshold would be a new convention.

The chapter separately says a stronger causer can prevail, and a greater number
can prevail. It does not supply a general multi-planet strength aggregation
algorithm. In particular, summing raw Shadbala, summing normalized strengths,
comparing maxima and counting stronger pairs are different policies. The text
does not choose one here. A count grade can be established while effective
obstruction remains unresolved.

For the special third-house intervention, S05 printed 312 requires **three or
more malefics**. S07 PDF 30 explicitly explains more than two; S08 printed 12–13
agrees. The current engine's threshold of two needs a legacy identity or an
explicitly versioned repair. A vague multi-malefic phrase in another source does
not prove the exact two-planet threshold.

S05's translation refers to retrograde **nodes**, and printed 313 demonstrates
reverse reckoning from Rahu. This is not identical to reversing every reference
sign occupied by Ketu. Node reference selection, node occupancy, counting direction,
and classification must be distinct policy fields. The printed example's prose
includes Moon/Rahu in the third, while the diagram labels only Moon. Planning
subsequently found and visually verified the publisher's erratum: printed 483 /
PDF 482 adds Rahu in Gemini to printed 313's chart. Apply that correction and
retain both witnesses. It does not resolve the separate Vol. II Chara conflict.

Benefic, malefic and mixed intervention are separately discussed at 31.11–17.
Do not rename an excellent count grade as universally auspicious. The current
classification helper's Moon/Mercury rules also need an explicit admitted scope;
they do not automatically implement every author's contextual classification.

### 4.2 BPHS degree-quarter qualification

At 31.10, printed 314 / PDF 313, the translated rule and commentary specify
causer quarter 1 obstructed by blocker quarter 4, and causer quarter 2 by blocker
quarter 3. Quarters are 7°30′ wide. The commentary expressly describes these
two circumstances. It does **not** explicitly add reverse pairs 3→2 and 4→1.

A profile selecting this literal edition reading must say so. A symmetric
four-pair interpretation would require its own source or a disclosed derived
policy. This is not a nakshatra-pada test.

The eventual contract must identify actual causer/blocker pairs, the reference
and relative houses, normalized within-sign degrees, quarter indices and the
qualification result. For multiple occupants, preserve pair evidence before
applying any separately admitted aggregation. Decide endpoint ownership for
0°, 7.5°, 15°, 22.5° and 30°/next-sign explicitly and test adjacent floats.
Floating-point boundary ownership is an engineering convention, not an ancient
statement about binary numbers.

The current engine marks equal single-planet counts obstructed whether Venus
is at 1° Taurus with Sun at 5° Pisces, or with Sun at 25° Pisces. Those placements
distinguish the quarter rule; current outputs intentionally have no such field.

### 4.3 PVR textbook: count-first comparison and real node witnesses

W03 10.6–10.7 compares counts first, then strengths on an equal count; Ketu's
reference sign reverses. Exercise 16 explicitly includes both nodes as occupants.
For Scorpio Lagna it lists Ketu in the fourth and Rahu as the tenth-house
obstructor. For its Aquarius/Ketu reference, the reversed second contains Venus,
and fourth Mars/Saturn. These are useful published transport fixtures.

Section 15.5 distinguishes lord selection for dasa duration from arudha selection:
the former uses longer duration at the final tie, the latter degree advancement,
with reversed advancement for nodes. It is not a universal Argala Shadbala recipe.
Its strength hierarchy must also be kept separate from W01's later formulation.
The textbook's multi-malefic wording does not fix an exact threshold of two.

### 4.4 Rath article: a richer intervention family

W04 includes nodes, adds secondary 8/6 and special 7/1 pairs, and compares sign
strength beyond occupant counts. Its worked fourth/tenth comparison uses
Rahu/Ketu, then Jupiter's sign aspect; its seventh/first comparison uses Jupiter's
own-sign placement. Equal strength retains a meaningful balance/bondage reading.
Ketu reverses reference reckoning. These examples support a richer named product,
but the article does not define every tie, multi-occupant aggregation or numerical
strength scale. Copying just its name onto the existing four-pair boolean result
would overstate coverage. Its wider inclusion of signs/upagrahas also needs a
declared computational scope rather than silently treating absent bodies as zero.

Implementation validation exposed an additional qualification to the article's
fourth/tenth comparison: Jupiter in Pisces casts standard Jaimini rasi drishti
to both Gemini and Sagittarius. Its aspect alone therefore cannot reproduce the
article's chosen Sagittarius/Ketu winner. C12 preserves the source judgment and
the symmetric geometry separately; no asymmetric aspect or unsourced factor
priority is admitted. The initial fixture assumption that Gemini was unaspected
was not stated by the article and was corrected from independent sign geometry.

The new natural-character component separately uses S05 3.11, printed 27 /
PDF 26, visually checked during planning: nodes are natural malefics, Moon's
character is conditional, and Mercury associates with malefics. The selected
root-verse/same-sign reading and exact half-cycle boundary convention are explicit
in the profile standard; translator additions are not silently included.

### 4.5 Rangacharya: aspecting-planet and Yogada product

S08 printed 12–19 anchors subhargala assessment to an **aspecting planet**.
It includes reciprocal 5/9 and 9/5 secondary relationships, contextual
benefic/exalted-malefic eligibility, and the three-malefic special rule. It does
not give Rahu/Ketu the same contribution semantics as the other witnesses:
printed 13 excludes them as contributors to subhargala yoga and treats their
association as adverse.

Printed 13–14 grades potential along several axes: aspecting-planet order,
merits/demerits, benefic/malefic mixture, planet count, and occupied Argala
positions. It lists superior/medium/ordinary categories, but does not define
how competing category triggers collapse into one scalar score. Printed 14's
reckoning text juxtaposes regular reckoning and reversal for an even-sign
aspecting planet; the Nehru example on printed 19 explicitly uses reversal.
Keep this as its own named direction reading.

The six aspecting-planet orders on printed 2–3 involve Lagna, Moon/lord and
Navamsa/Drekkana Lagna relationships. The latter require the manual's divisional
conventions; its Jaimini Navamsa is explicitly described on printed 3. Generic
D9/D3 defaults cannot be substituted silently. Poornargala, Tripadargala,
Ardhargala and Padargala on printed 16–17 further depend on Yogada/Kevala,
modality and participating positions. They are not aliases for the BPHS
one/two/three-planet count grades.

Published B.V. Raman, Bachchan, Gandhi, Nehru and Vivekananda illustrations are
available for targeted source fixtures. For example, printed 15 explicitly treats
debilitated Venus as malefic in its Bachchan discussion; the current generic
natural-character helper is not that rule. Full Yogada grading should be scoped
as an additional composition, with per-condition evidence and unresolved
conflicts, rather than promised as an incidental Argala count enhancement.

## 5. Current engine and REST findings

Inspected owners:
[engine](../../moira/jaimini_extended.py),
[request/result models](../../moira_server/models/vedic_extended.py),
[routes](../../moira_server/routers/vedic_extended.py), and public exports in
`moira/__init__.py`, `moira/facade.py`, `moira/vedic.py`.

| Surface | Current behavior | Consequence for the plan |
| --- | --- | --- |
| Chara Python/REST | One formulation, strict seven bodies, optional complete node pair, one/two cycles; fixed clock and receipt | Add named identities without changing the default or inventing subperiods for a source that does not specify them. |
| Chara result | Integer years, mandatory subperiod arrays; increasing endpoints; receipt has fixed literal formulation/clock | Zero spans, alternate clocks and mahadasha-only admission need deliberate result/transport design. |
| Argala Python/REST | Four pairs; seven classical occupants; Ketu only controls reversal; two-malefic special threshold | Nodes, grades, strength comparisons, quarters and richer pairs need source-scoped additions. |
| Argala result | `unobstructed` boolean, no structured policy/grade/uncertainty receipt | Equal-count failure currently means a count convention, not a completed source-strength judgment. |
| Special third-house role | Special-field occupants remain in the eleventh pair's blocker tuple | Preserve raw roles and explicitly decide coexistence versus replacement; the docstring's word "instead" does not describe removal in code. |
| Direct Argala validation | Accepts boolean Lagna, boolean Ketu, ignored boolean Rahu and unknown node key | REST rejects those four cases with 422. Shared engine admission must be repaired. |
| Optional nodes | Empty, Rahu-only and Ketu-only maps accepted by both Argala paths | This is current compatibility, not automatically an error. A nine-body profile must require its actual needed inputs; omitted nodes must not masquerade as absent planets. |
| REST wiring | Routes call the owning engine; response copies legacy fields | Preserve this ownership when adding typed receipts; no server-owned competing doctrine. |

Research probes confirm that exactly Mars and Saturn in the third produce the
special field in both engine and HTTP. Nodes in causal positions do not appear
in occupant tuples. Ketu-only reversal works. Those are observations of the
current code, not validation of the source attributions.

The docstring saying strength grading belongs to Shadbala should be replaced
during the repair with an accurate statement of the selected computation. A
source-owned Shadbala integration would need comparable units, a planet pool,
node handling, aggregation, ties, missing context and an explicit claim boundary.
The collated material does not authorize silently summing Moira's Shadbala values.

## 6. Admission disposition and acceptance inputs

| Candidate | Research disposition | Exact decision before execution |
| --- | --- | --- |
| Existing Rao-compatible Chara | Retain; already admitted under bounded identity | Preserve default parity and existing cycle evidence limits. |
| Rangacharya method 1 | Plan candidate with complete sign-duration recipe | Select ordinary lords, own/dignity precedence, zero-span behavior, calendar and subperiod scope. |
| Rangacharya method 2 | Strongest immediate alternate-sequence candidate | Select the manual recipe and explicit branch; declare calendar/subperiod/cycle scope. |
| Rangacharya female recipe | Plan candidate with one documented table conflict | Prose-selected own-sign twelve versus printed Cancer ten; retain conflict fixture and migration explanation. |
| BPHS Chara | Source-backed candidate requiring narrower decisions | Resolve the listed co-lord/subperiod/clock issues; do not certify the whole conflicting diagram/table. |
| W01 | Conditional candidate | Resolve the issues in section 3.5 or expose the unresolved decisions explicitly. |
| Narayana | Independently named future package | Its complete profile and source fixtures require separate scope from Rao Chara. |
| BPHS Argala count grades | Ready for a bounded component specification | Define participant pool, reference and formation/effect distinction. |
| BPHS quarter qualification | Ready for a named literal-reading component | Preserve directed pairs and define multiple-occupant composition and boundaries. |
| PVR/Rath strength-aware Argala | Plan as named assessment profiles | Separate count/strength outcomes; identify admissible comparison rules and unresolved ties. |
| Rangacharya Yogada/Argala potential | Additional composition identified | Admit aspecting-planet classification, its varga conventions and multidimensional grading before one overall verdict. |

The implementation plan should turn these decisions into versioned profiles and
independent source fixtures. Minimum discriminating cases are:

- All twelve seeds and both parity/group systems; all 24 method-2 sequence rows;
  own, adjacent, opposite and zero-adjusted duration cases; the 7/7 and 11/12
  printed-duration comparisons; all selected co-lord branches and exact ties.
- Calendar/JD conversion separated from sign/year arithmetic. A published
  sign-only chart is not a source for fabricated longitudes or timestamp precision.
- Argala 0/1/2/3-plus occupants, empty/equal/unequal blockers, two versus three
  malefics, optional/required nodes, node reference versus occupied sign, all
  admitted pairs, quarter endpoints and mixed eligible/ineligible blockers.
- Full evidence survives Python, facade, curated exports, REST and OpenAPI;
  unknown profile, coerced scalar, partial required context and nonfinite input
  fail at the owning boundary. Unknown strength is neither zero nor false.
- Bounded execution and result sizes, immutable evidence where promised,
  deterministic rule traces, complete default regression and real chart-context
  checks for any newly admitted clock/strength composition.

No new predictive outcome claim follows from matching a published arithmetic
example. A documented source conflict can be resolved by an explicitly selected
reading without pretending that the conflicting witness never existed.

## 7. Verification performed in this research pass

The unchanged implementation passes **251 tests, zero failures/errors/skips**:

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jaimini_extended.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_vedic_chara_d60_admission.py tests/server/test_vedic_direct_input_hardening.py -m 'not external_network' -q --junitxml=C:\dev\outputs\ved013-research-2026-10-12\baseline.xml
```

This is an existing-contract baseline, including the earlier combined Chara/D60
package. Its harness records six successful DE441 resource receipts. It does not
validate new VED-013 profiles. Separate direct/ASGI probes use a stubbed server
engine constructor; they exercise the direct endpoints, not a new chart-backed
product. Twelve probe cases are saved in `runtime_http_probes.json`.

`source_arithmetic.json` records the seven male and twelve female duration
comparisons, BPHS diagram conflict and zero-year case.
`rangacharya_sequences.json` records 24 independently transcribed sequence rows
and all 288 reproduced cells. These private research calculations do not import
Moira's period algorithm to generate expected source values. They are fixture
candidates, not a substitute for committed implementation acceptance tests.

Only this packet and the work register change. Runtime, test baselines,
dependencies, version, generated wiki and unrelated light-box work are untouched.
No commit, push, release or deployment is part of this research checkpoint.

## 8. Fingerprints

SHA-256 identifies the exact inspected digital witness, not its historical
authenticity. The private manifests also retain ancillary indexed files.

| ID | PDF pages | SHA-256 |
| --- | ---: | --- |
| S05 | 482 | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| S06 | 552 | `ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45` |
| S07 | 221 | `1b1441b138093433fa594f49a7b89863bd00c0476f621f804895ec7d8c3cc6b8` |
| S08 | 89 | `8290bc9d8a9d5eedd5ac0724f15554c7ff70f276a26103b58cbd7e068ea5a5f8` |
| S09 | 9 | `6c5b78ad0f70d0b1501966e5655ad37c0d0b1c8f409d8eb6a583c9ba085bffc3` |
| S11 | 99 | `6dac872537f07e65da92b3936ae17ef18a7cbe8064201a1ea55c6f0f3af4a19b` |
| S12 | 22 | `720978aab2354307b7cac3e98d0fae0ef90c25db1fa3042891c041cec0a947e5` |
| S02 | 10 | `398b9c57728bbf3a8bb6c825798eb3bf5e7b0784601dbd1470ab0fedfc8eafb2` |
| W01 | 46 | `2a6b1b224fb0f1b2bd7f1f55403f5a6f3c805277f71c5389b1ae8d14afb00fb0` |
| W02 | 206 | `8ed7732034092828dca800cdc6aa9422c742c498517700c0a0654ec4926d1206` |
| W03 | 515 | `1cafa828f34764ed5e85816882df2e8f0bc014c5c57ccdb27169416e117fd4db` |
