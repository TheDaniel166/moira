# VED-008: Panchanga Shuddhi source research and admission proposal

**Date:** 8 October 2026. **State:** research complete for the decisions below.
The user subsequently approved the named profiles together; the 9 October
[implementation standard](../02_standards/PANCHANGA_SHUDDHI_STANDARD.md) and
[validation receipt](../03_validation/PANCHANGA_SHUDDHI_VALIDATION_2026-10-09.md)
record their engine/REST admission. Proposal language below preserves the
research decision sequence, not current implementation status.
**Baseline:** engine `c647363a342a7756d85a5b012ff0e9004ba2ce80`, version 6.9.9;
generated wiki `2e74b0b6241c8db52a368d89274050a123b795da`.
**Owner:** [Vedic remaining work register](VEDIC_REMAINING_WORK_REGISTER.md),
VED-008. VED-009/010/011 retain general cancellation, strength and complete
purpose-election scope. Website adoption is separate.

## 1. Decision

Proceed to a finite engine/public/REST package with separately named rules for:

1. Panchaka Rahita arithmetic and date-derived inputs, including the full
   thirty-tithi convention and the ascendant at the evaluated instant.
2. Tara cycle distinctions, with the Chintamani quarter reading and the
   different P. S. Sastri cycle rule exposed as alternatives.
3. The nine adverse Nitya Yogas, distinguishing whole-event prohibitions,
   initial ghatis and the first half of Parigha.
4. Karana-specific evidence from Brihat Samhita, and independently reported
   Bhadra occurrence, residence, day/night exceptions and mouth/tail windows.

There is substantive classical support. The obstacle is choosing and naming
the exact reading and clock, not a general absence of texts. Preserve existing
`tara_bala`, `chandra_bala` and weighted-score behavior; add an inspectable
source-owned assessment. Do not silently reinterpret their existing booleans.

The recommended clocks for fractional intervals below are explicitly derived
computational policies. Approval of this package would admit those named
derivations, not establish that a verse directly specifies a modern algorithm.
Conflicting readings and activity exceptions remain visible in results.

## 2. Sources actually examined

PDF page numbers here are **one-based file pages**, distinct from printed pages.
Source PDFs and page renders remain in private research storage. Only this
analysis, factual rule tables and small evidence receipts belong in the repo.

| ID | Witness and identity | Reviewed locus | Evidential use |
| --- | --- | --- | --- |
| MC | Daivajna Rama, *Muhurta Chintamani*, Hindi commentary by Pandit Ramlal Avasthi, edited by Chandika Prasad Avasthi; Tejkumar Book Depot, Lucknow, tenth edition 2004. [Scan](https://archive.org/details/muhurta-chintamani-hindi). | Shubhashubha 34–35, 42–45: PDF 25–26, 29–30 / printed 16–17, 20–21. Gochara 11–13: PDF 79–80 / printed 70–71. | Printed Sanskrit, anvaya and commentary collated. Yoga, Bhadra and Tara authority; commentary discrepancy recorded below. |
| KP | *Kalaprakasika*, Sanskrit with English translation by N. P. Subramania Iyer; Asian Educational Services, New Delhi, 1982. [Scan](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf). | Panchakam in travel: PDF 188–189 / printed **151–152**. Exceptions: PDF 230 / printed 193. | Independent printed Panchaka formulation and noon-exception witness. OCR incorrectly reads printed 151/152 as 161/162; images control. |
| PS | P. S. Sastri, *Text Book of Scientific Hindu Astrology*, Ranjan Publications; exact printing date not present in reviewed front matter. Local file `Books by Authors/BV Raman/Scientific-hindu-astrology.pdf`. | PDF 1 title, PDF 5 / printed 8 signed preface; PDF 268 / printed 273, “Constellations — Nature.” | A distinct cycle rule. **Author is Sastri, not Raman**: verified signed preface. Edition remains identified by scan hash; no date guessed from a bookseller. |
| BS | Varahamihira, *Brihat Samhita*, English translation/notes by V. Subrahmanya Sastri and M. Ramakrishna Bhat; V. B. Soobbiah & Sons, Bangalore, 1946. Local `Classics books/brihatsamhita.pdf`. | Title PDF 1; signed introduction PDF 11; chapter **100**, verses 1–5, PDF 767–769 / printed 748–750. | Direct local scanned primary witness for all eleven Karana identities and activity distinctions. Text search fails because these pages are image-only; bookmarks and visual reading located the chapter. |
| R | B. V. Raman, *Muhurtha*, online reflowed transcription; printing/edition not established. [File](https://storage.yandexcloud.net/j108/library/tuwzcd7e/B.V._Raman_-_Muhurtha_%28Electional_Astrology%29.pdf). | Chapter III, PDF 13–16. | Corroborates quarter reading and Panchaka; also preserves author-specific caution and an internal ghati/example discrepancy. Not treated as an edition-locked classical text. |
| MP | *Darwin, NT Panchang*, 2025; Hindu Council of Australia / myPanchang; calculations credited to Pandit Mahesh Shastri, editor Pandit Vishal Sharma. [Published calendar](https://mypanchang.com/2025pdfs/au/2025DarwinNorthernTerritoryAustralia.pdf?v=20241229164100). | PDF 1 acknowledgements; PDF 2, “Panchaka Rahita Vidhi for Muhurtha.” | Domain-primary operational authority explicitly specifying thirty tithis, sunrise-owned weekdays and a worked dark-fortnight case. This convention is attributed to this publication. |

Digital corroboration:

- [E-Bharatisampat, Chintamani](https://www.ebharatisampat.in/read_chapter.php?bookid=MjQwNjAyMzE4NTQyMDYy)
  supplies searchable Sanskrit. Its online text is a corroborating witness;
  the named printed MC scan owns the edition used here.
- [Brihat Samhita, Iyer translation chapter 99](https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc229362.html)
  combines tithi and Karana material. Its verses 4–8 correspond to Karana 1–5
  in the local 1946 chapter 100. [Digital Sanskrit](https://www.wisdomlib.org/hinduism/book/brihat-samhita-sanskrit/d/doc1218132.html)
  labels the Karana chapter 99. Do not cite a bare chapter number across editions.
- *Muhurta Sadhana*, [Samjna 45–63](https://www.transliteral.org/pages/z130601001637/view),
  records Bhadra body divisions and alternative exceptions. Author/print edition
  is not identified there; it is a variant witness, not the default authority.
- [Gochara 13–25](https://www.transliteral.org/pages/z130607054404/view)
  demonstrates that Janma and paksha-conditioned Chandra interpretations vary;
  it does not authorize changing the existing Chandra function in this package.

### Local-corpus search limits

Searched the prior local extraction cache for Panchaka Rahita, paryaya and
Tara Bala spellings; checked relevant matches in the Sastri textbook,
Uttara Kalamrita and the modern Vedic textbook. The Uttara Kalamrita hit
concerns birth-time verification, not this electional rule. The latter
textbook's nine-tara table is a general transit baseline, not proof of cycle
exceptions. Filename searches for Muhurta/electional/Panchanga titles did not
locate a dedicated manual in this corpus; that is not an absence claim about
rules embedded in other volumes. The local Raman *Manual of Hindu Astrology*
had no relevant extracted-text match. Image-only pages cannot be cleared by
text search: the local Brihat Samhita is the concrete counterexample.

Private audit directory: `C:/dev/outputs/ved008-research-2026-10-08/`.
`source_manifest.json` records paths, hashes and reviewed pages;
page PNGs permit visual rechecking. Supporting PDFs from the previous VED-007
research are reused without pretending they were found inside the local corpus.

| ID | SHA-256 of reviewed PDF |
| --- | --- |
| MC | `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777` |
| KP | `d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074` |
| PS | `e82c5936775a5d3577433bb88271667ef18580bf449505b5bffa6fd12fa54bdf` |
| BS | `30345203af3be094776ef67f7a9ad2ae8da8392513c72ac7d24a791eb7b19302` |
| R | `8ab2c1fc0a4ca0e0f7145434b4c02f8efa97ce48d27fc03732cd632d6a3f9256` |
| MP | `81615141f0c729387304ba80bae4b3157d2b62c79030bec5a125f5ed3efbdccb` |

## 3. Panchaka Rahita: formula and counting policy

With one-based inputs, let `S = tithi + weekday + nakshatra + lagna`.

| `S % 9` | Classification |
| --- | --- |
| 0, 3, 5, 7 | Rahita: this Panchaka restriction is absent |
| 1 | Mrityu |
| 2 | Agni |
| 4 | Raja |
| 6 | Chora |
| 8 | Roga |

KP states five offset tests: add respectively 15, 12, 10, 8 or 4 to S;
remainder 5 indicates respectively illness, fire, royalty, thieves or disaster.
These are **algebraically equivalent** to the table, not five conflicting
algorithms. Its rising sign is explicitly at departure, not frozen at sunrise.
R gives the direct table and a worked `13 + 9 + 1 + 6 = 29`, remainder 2 case.

MP resolves the dark-fortnight input explicitly: Shukla 1–15, Krishna 16–30;
Sunday 1 through Saturday 7; Ashwini 1 through Revati 27; Aries 1 through
Pisces 12. Its printed example is `17 + 7 + 19 + 11 = 54`, remainder 0.
The weekday continues through midnight until the next local sunrise.

**Proposed profile:** `mypanchang_2025_panchaka_30_tithi.v1`, with the KP
remainder equivalence recorded as classical corroboration. Do not label
the entire modern counting contract “universally classical.” A fortnight-reset
convention is not admitted merely because it is easy to offer as a toggle.
Keep the late-Dhanishtha-to-Revati usage of “Panchak” a
separate product; it is not this four-input arithmetic.

Research-only enumeration checked **68,040** input combinations, with zero
disagreements between the direct and offset formulas. Incorrectly resetting
Krishna tithis to 1–15 changes the category in **30,240/34,020** dark-half
combinations and the Rahita boolean in **22,680/34,020**. These are combinatorial
counts, not frequencies over real dates. Both printed examples were checked.

R also distinguishes purpose exceptions and explicitly calls some permissions
its own inference. Preserve the five detected labels. Do not interpret Rahita
as complete suitability, or automatically ignore Raja for a wedding.

## 4. Tara: keep three questions separate

For zero-based natal and target stars:

`count = (target - natal) % 27 + 1`

`tara = (count - 1) % 9 + 1; cycle = (count - 1) // 9 + 1`

This uses 27 equal nakshatras, inclusive counting and no inserted Abhijit.
The base tara identity, the cycle-specific restriction, and a broader personal
judgment are different outputs.

### MC Gochara 13: proposed quarter profile

| Cycle | Vipat (3) | Pratyari (5) | Vadha (7) |
| --- | --- | --- | --- |
| 1: counts 1–9 | Whole star restricted | Whole star restricted | Whole star restricted |
| 2: counts 10–18 | First quarter restricted | Fourth quarter restricted | Third quarter restricted |
| 3: counts 19–27 | Restriction lifted by this rule | Restriction lifted by this rule | Restriction lifted by this rule |

**Textual discrepancy:** the printed Sanskrit/anvaya gives first, last and
third portions; R explicitly interprets these as quarters 1, 4, 3. The MC Hindi
paragraph instead describes three successive twenty-of-sixty portions. It
does not match its own Sanskrit order for Pratyari. Record that reading as a
commentarial discrepancy, not an interchangeable quarter implementation.

**Recommended decision:** admit `mc_gochara_13_quarters.v1`, citing the printed
Sanskrit and R's corroborating interpretation; declare a quarter to be one
3°20′ sidereal lunar arc, with exact ingress roots for dated windows. This
is an explicit interpretation of *amshaka*, not a claim that the Hindi
paragraph says the same thing. Do not introduce the thirds profile without
an internally reconciled witness and an identified time/arc basis.

The verse's cycle cancellation refers to the three named adverse taras.
It does not make Janma unconditionally favorable. Keep existing Janma caution
and report Janma purpose exceptions as unevaluated unless separately selected.
R's personal advice to avoid Vipat/Vadha for important undertakings even in
cycle 3 is a distinct conservative application, not grounds to erase the
verse's cancellation. Its “fifty per cent” language is not a calibrated score.

### PS printed 273: a real alternative

PS singles out Janma in cycle 1, Vipat in cycle 2, Pratyari in cycle 3,
and Vadha in every cycle. This gives restricted inclusive counts
**{1, 7, 12, 16, 23, 25}**, without quarter restrictions.

Admit as `ps_sastri_scientific_273_navaka.v1`, scan-owned and explicitly modern
scholarly testimony. It disagrees with MC: count 25 is restricted here but
lifted by MC's cycle rule; count 14, quarter 4 is restricted by MC but is not
singled out by this PS rule. Neither is “the universal Tara exception.”
Not singled out by a rule does not certify the whole election as favorable.

R's separate initial-ghati rule lists 7/3/8/6 for Janma/Vipat/Pratyak/Naidhana,
then its Pushya-to-Magha example says seven for Vipat. The inspected reflow is
internally inconsistent. **Defer that specific initial-ghati profile** until a
printed edition or independent primary witness resolves 3 versus 7. This
does not block either of the above complete cycle profiles.

## 5. Nitya Yoga: partial periods, not whole-day labels

MC Shubhashubha 34–35 and the Hindi explanation give:

| Nitya Yoga | One-based index | Excluded portion |
| --- | --- | --- |
| Vishkumbha | 1 | Initial 3 ghatis |
| Atiganda | 6 | Initial 6 ghatis |
| Shula | 9 | Initial 5 ghatis |
| Ganda | 10 | Initial 6 ghatis |
| Vyaghata | 13 | Initial 9 ghatis |
| Vajra | 15 | Initial 3 ghatis |
| Vyatipata | 17 | Entire Yoga occurrence |
| Parigha | 19 | First half of the Yoga occurrence |
| Vaidhriti | 27 | Entire Yoga occurrence |

**Proposed clock:** fixed 24-minute ghatis for the explicitly numbered initial
periods; actual solved start/end times for a whole occurrence; temporal midpoint
of the solved occurrence for Parigha. Name this
`mc_34_35_fixed_ghati_temporal_half.v1`. The midpoint conversion is an explicit
derived choice. A 60%-long or 40%-long calendar display segment is not enough
to establish the event start. Do not replace a whole occurrence by 24 hours,
Parigha's half by a fixed 12 hours, or elapsed time by angular progress without
declaring a different clock policy.

Intervals start at the true Yoga ingress, even if it preceded sunrise or the
requested civil date. Initial-ghati intervals must be bounded by the actual
Yoga end. Use `[start, end)` ownership and preserve root uncertainty.

The 27 longitudinal-sum Nitya Yogas are distinct from weekday/star Anandadi
Yogas, named auspicious windows, upagrahas and declination-based Mahapata.
KP printed 193 and MC commentary at 42 contain noon exceptions; those are
separate cancellation rules. The base profile above does not silently apply
an after-noon override or a strong-Lagna override.

## 6. Karana and Bhadra

### BS chapter 100.1–5: finite Karana evidence

Propose a named, eleven-entry catalogue of supported **activity tags**, with
verse references. It reports what this rule supports, not a complete election:

| Karana | Source-supported character/activity, paraphrased |
| --- | --- |
| Bava | Auspicious, temporary or lasting acts; nourishment |
| Balava | Religious/meritorious acts; assistance to Brahmins |
| Kaulava | Affection and friendship |
| Taitila | Prosperity/popularity, shelter and household matters |
| Gara | Cultivation, sowing, house/shelter work |
| Vanija | Lasting undertakings and commerce |
| Vishti | Auspicious acts prohibited; hostile acts mentioned historically |
| Shakuni | Nourishment, medicines/roots and mantra work |
| Chatushpada | Cattle, Brahmins, ancestors and royal affairs |
| Naga | Lasting and fierce acts; coercive acts mentioned historically |
| Kimstughna | Meritorious, nourishing and auspicious acts |

These are historical textual categories, not medical or practical advice.
In particular, the four fixed Karanas cannot all receive one universal adverse
flag under this source. VED-011 owns complete purpose-specific elections;
these narrow tags and explicit prohibitions can be useful before that work.

### MC 43–45: Bhadra occurrence, residence and exceptions

Vishti occupies these tithi halves: Shukla 4 latter, 8 former, 11 latter,
15 former; Krishna 3 latter, 7 former, 10 latter, 14 former. In the existing
zero-based monthly Karana sequence these are **{7,14,21,28,35,42,49,56}**.

Residence is determined by the **current sidereal Moon sign**:

| Residence | Signs |
| --- | --- |
| Earth | Cancer, Leo, Aquarius, Pisces |
| Heaven | Aries, Taurus, Gemini, Scorpio |
| Underworld | Virgo, Libra, Sagittarius, Capricorn |

The text locates the effect in that residence. Return the residence and
earth-applicability explicitly; do not delete the detected Vishti identity
when the Moon is outside the Earth group.

MC 44 also permits latter-half-origin Bhadra during daytime and
former-half-origin Bhadra during nighttime. The Sadhana witness expressly
limits its corresponding exception to necessary work. Select a named source
and preserve that condition; do not silently merge the qualifications.
Day and night need actual local sunrise/sunset, not 06:00/18:00 constants.

### MC 44: mouth/tail tables and a declared derived clock

| Tithi | Mouth: beginning of eighth-part number | Tail: end of eighth-part number |
| --- | --- | --- |
| Shukla 4 | 5 | 8 |
| Shukla 8 | 2 | 1 |
| Shukla 11 | 7 | 6 |
| Shukla 15 | 4 | 3 |
| Krishna 3 | 8 | 7 |
| Krishna 7 | 3 | 2 |
| Krishna 10 | 6 | 5 |
| Krishna 14 | 1 | 4 |

The specified mouth is the initial five ghatis of its named yama; the tail is
the final three ghatis of its named yama. They are **not always the first and
last portions of the Karana**. MC calls the mouth adverse and tail favorable.

Recommended derived profile: `mc_44_tithi_eighths_normalized.v1`. For actual
tithi duration `D` and start `A`, let one nominal tithi-ghati be `D/60` and an
eighth be `D/8`. Then:

- mouth: `[A + (m-1)D/8, A + (m-1)D/8 + D/12)`;
- tail: `[A + qD/8 - D/20, A + qD/8)`.

This normalization is a **proposed computation derived from the table**,
not a directly verified universal time-conversion instruction. It must be
named in policy/provenance. Intersect the resulting interval with the actual
solved Vishti occurrence and retain both original and clipped bounds: equal
time halves of a tithi do not exactly equal the two 6° Karana intervals when
lunar speed changes. Validate unequal-duration cases, not only a 24-hour tithi.
Do not quietly mix these normalized ghatis with the fixed Yoga clock.

Sadhana's sequential 30-part body scheme and its alternative snake/scorpion
tail prohibitions are genuinely different readings. Retain them in the source
registry as unselected; do not combine them with MC's tithi-position table.
The named MC derived profile can be implemented without waiting for every
body-anatomy variant to be admitted.

**Precedence recommendation:** first return detection, mouth/tail membership,
residence and each applicable exception as separate source facts. Where a
mouth restriction and another exception overlap, report the simultaneous
claims; the inspected passage does not establish a universal precedence
ordering. An optional conservative “mouth takes priority” selector would be
a Moira application policy, not an invented classical consensus. No generic
favorable boolean should hide this unresolved precedence.

## 7. Current Moira behavior and proposed contracts

| Existing surface | Verified limitation | Proposed addition |
| --- | --- | --- |
| [tara_bala](../../moira/muhurta.py) | Inclusive count and nine-tara polarity; no cycle/pada exception evaluator | Separate source-policy assessment retaining base identity/polarity |
| [chandra_bala and personal score](../../moira/muhurta.py) | Existing bounded rule/weight profile | Preserve compatibility; expose the new assessment separately |
| [Panchanga Yoga classification](../../moira/panchanga.py) | Adverse indices `{5,8,9,16,26}` zero-based; five entire Yoga labels | New nine-Yoga timing profile with start/end evidence; no silent replacement of shared constants |
| [Karana classifier](../../moira/muhurta.py) | Vishti adverse; every other Karana neutral | Source-owned eleven-entry evidence and Bhadra components |
| [Daily Panchanga](../../moira/daily_panchanga.py) | Sunrise-owned day, phase transitions and uncertainty already exist | Reuse solver/reader/frame policy; obtain preceding and following event bounds where fractional rules require them |
| [Muhurta REST models](../../moira_server/models/muhurta.py) and [router](../../moira_server/routers/muhurta.py) | Strict current personal score; no VED-008 source-policy result | New typed direct and dated assessment; catalogue/policy discovery; canonical serialization |

Suggested new owning module: `moira/panchanga_shuddhi.py`. Its data structures
should distinguish `detected`, `restricted`, `exception_applies`, `not_applicable`,
`unavailable` and `not_evaluated`, together with stable source/rule IDs. A
conflict is not success; unavailable astronomy is not a negative finding.
Each result needs selected policy, applied policy, actual inputs, raw finding,
exception evidence and any remaining restriction. Policy receipt fields must
describe execution rather than echoing unimplemented options.

Proposed REST scope: typed policy/catalogue discovery, direct component
assessment and date/location assessment. Exact route names are implementation
design, but all three must arrive with engine exports/facade and tests. A
bounded one-day interval result is preferable to silently widening generic
sampled Muhurta search. Keep new rules out of weighted search until its
composition/weight policy is separately selected.

Input requirements:

- Strict integer ranges and explicit zero/one-based adapters. Reject booleans,
  strings, unknown profiles, extra fields and contradictory redundant inputs.
- Natal star for Tara; lunar longitude/pada when the selected quarter rule
  needs it. Missing natal data must not suppress unrelated evaluations.
- A single coherent ayanamsa/frame for Moon, Sun, nakshatra and ascendant.
  Reuse the actual serving reader; do not compute an unrelated chart behind
  the response or substitute a different ayanamsa at one stage.
- Location/time zone and real solar anchors for dated weekday/day-night rules;
  current Lagna for Panchaka. Sunrise determines the weekday, not the Lagna.
  Handle polar absence and ascendant singularities explicitly.
- Actual predecessor/successor boundaries for Yoga, tithi and Karana. A clipped
  sunrise-day segment cannot stand in for the full event duration.
- Bound requests, solver horizons, transitions and response sizes. Preserve
  coincident-boundary reasons and uncertainty bands; do not fabricate precision.

The new nine-Yoga contract and BS Karana catalogue expose limitations in the
legacy classifier. Keep that compatibility behavior identified and documented;
a future migration can change defaults explicitly. Broad BPHS chapter-85
comments in the legacy module are not edition-collated authority for the new
rules. Cite the precise MC/BS loci instead.

## 8. Admission, deferral and validation plan

| Item | Research decision |
| --- | --- |
| Panchaka direct remainder rule; MP thirty-tithi/date convention | Admit for implementation as a named operational profile, with KP corroboration |
| MC Tara quarter rule; PS alternative cycle rule | Admit separately; keep Janma and broader purpose judgments distinct |
| MC nine-Yoga initial/whole/half table | Admit with explicitly selected fixed-ghati/temporal-half clock |
| BS eleven-Karana activity evidence | Admit catalogue and bounded rule evaluation; complete purpose elections remain VED-011 |
| MC Bhadra residence, origin-half/day-night, mouth/tail table | Admit component facts; normalized mouth/tail clock is a named derived policy |
| One universal precedence among Bhadra exceptions | Exclude as unsupported; expose overlaps or choose a separately named application policy |
| MC Hindi thirds; R 7-versus-3 Vipat initial-ghati example | Defer these particular readings; exact discrepancy and resolution evidence identified above |
| Sadhana anatomical/scorpion variants | Document as alternatives; edition and complete clock/precedence required before selection |
| Noon, strong-Lagna, benefic-aspect and ritual-remedy cancellations | Retain references; finite separately selected VED-009/010/011 rules, not an automatic override |

Implementation sequence should be one reviewable package with three internal
milestones, not twelve mandatory phases:

1. Freeze named policy IDs, source tables and typed component results. Write
   independently transcribed source fixtures and compatibility checks first.
2. Implement pure evaluators and date/day composition with real phase/solar/
   ascendant boundaries. Complete all selected profiles, including missing-data
   and conflicting-exception states.
3. Finish exports/facade and REST together, execute focused source/boundary/
   resource/HTTP validation, reconcile standard/reference/register and generate
   documentation. Publication requires its own user instruction.

Minimum acceptance cases:

- Both printed Panchaka examples; every remainder; all 68,040 direct input
  combinations against KP's offset formulation. Krishna Pratipada/Amavasya,
  midnight-versus-sunrise, and Lagna ingress cases must detect counting errors.
- All 27×27 natal/target combinations, all four padas, wraparound and exact
  pada boundaries. Explicit disagreement fixtures: count 14/pada 4 and count
  25 between MC and PS; count 12/pada 2 and count 16/pada 4. Janma remains
  visibly outside MC's three-tara cancellation scope.
- Every one of the nine Yoga rules, immediately before/at/after exclusion end,
  pre-sunrise starts, month/360° wrap, and non-24-hour Yoga occurrences. A
  20-hour Parigha occurrence has a 10-hour excluded temporal half under the
  selected clock; this is a synthetic arithmetic fixture, not a published event.
- All 60 Karana positions, all eleven catalogue entries, all eight Vishti
  occurrences, all twelve residence signs and all eight mouth/tail rows.
  For a synthetic 24-hour Shukla Ashtami: mouth 03:00–05:00 from tithi start;
  tail 01:48–03:00. Recheck with non-24-hour duration and nonuniform lunar speed.
- Residence change during Vishti; sunrise/sunset splits; tail followed by mouth;
  exception/restriction overlap; clipping and exact endpoint ownership. Missing
  event start, natal star or solar anchor must yield the correct component state.
- Independent root/bracket checks, real serving-reader and startup lifecycles,
  ordinary/DST/polar dates, finite operational budgets, typed response validation
  and direct/HTTP equality. Test both configured and discovered kernel paths.
- Regression of existing Tara/Chandra, score, sampled search, daily Panchanga
  and named Muhurta contracts. No silent changes to their existing policy IDs.

No astronomical or predictive accuracy claim follows from agreeing with these
rule tables. Source fidelity, arithmetic, event solving, transport and predictive
validity are distinct evidence classes.

## 9. Research receipt

Executed with `C:/dev/moira/.venv/Scripts/python.exe` (Python 3.14.3): source
extraction, bookmark lookup, rendering, SHA-256 manifests and the private
`check_research_arithmetic.py` enumeration. Result: **68,040 formula agreements,
zero disagreements, two source examples checked**. No runtime implementation,
kernel event validation or new REST behavior is claimed by that script.

Documentation verification: canonical consistency, relative-link resolution,
in-memory rendering through the owning wiki generator and `git diff --check`.
The generated checkout is left for the next authorized synchronization/publication;
no source PDFs are copied into either repository. Runtime, tests, dependencies,
version and existing source-publication commits remain unchanged.
