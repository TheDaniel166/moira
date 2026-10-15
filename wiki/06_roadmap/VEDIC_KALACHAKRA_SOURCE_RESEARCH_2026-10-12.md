# VED-014: Kalachakra Dasha source research

**Date:** 12 October 2026. **Status:** Research complete for the bounded
comparisons below. The subsequently authorized [implementation plan](VEDIC_KALACHAKRA_IMPLEMENTATION_PLAN_2026-10-12.md)
settles admission choices; the selected profile is [locally implemented and validated](../03_validation/VEDIC_KALACHAKRA_VALIDATION_2026-10-12.md). This packet retains
the original research evidence and its separate validation receipt.
**Baseline:** engine `8852052f317d7f3841e1e390578e303f438140a8`, Moira 6.9.9,
project Python 3.14.3. **Owner:** [remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md).

## 1. Findings and recommended first scope

Usable classical sources and worked calculations are present in the local library.
The obstacle is selecting and identifying a computation, not absence of sources.
Jataka Parijata's Sastri commentary explicitly describes two schools and computes
different starting periods from the same Moon longitude. Santhanam's BPHS and
Rao's 2000 textbook also differ on continuation and subperiod construction.

Recommend planning **one named initial profile**:
`bphs_santhanam_longitude_row_cycle_v1` (proposed identifier, not an existing API).
Its authority is the inspected Santhanam translation/commentary: chapter 46.93
for longitude balance, its worked continuation, and chapter 64's cyclic
antardasha tables. It should provide nine major-period occurrences, optional
antardashas, natal-row Deha/Jeeva, explicit source corrections, and bounded
active-period lookup. Require an explicit year basis for date projection.

The initial profile must not silently combine these with Rao's continuous
sequence, his changed Deha/Jeeva rule, or the separate navamsa-sign school.
Those are documented candidates with discriminating examples. A later profile
can reuse interval arithmetic without inheriting the first profile's doctrine.

Five findings govern the next plan:

1. **A sign is not a unique period identifier.** Several nine-sign rows repeat
   a sign; Rohini-2 has two Scorpios and two Libras. Preserve the row, occurrence,
   cycle and parent path, not just the sign or its planetary ruler.
2. **Birth balance, continuation and subperiods are independent decisions.**
   They materially change results even when the source tables agree.
3. **Printed defects are real.** Page-image checks confirm incorrect prose,
   duplicate entries and conflicting headings. Corrections need witnesses and
   a public conflict record; they must not become silent table edits.
4. **Traditional duration arithmetic is distinct from calendar projection.**
   A 3-year/7-month/24-day example uses 12 months of 30 days to express 3.65
   source years. It does not settle every school's date-conversion convention.
5. **Engine and REST need the same admission owner.** The existing alternate
   dasha transport is for eight-lord systems and cannot simply admit a new
   system string without new sign-period semantics, bounds and validation.

This packet does not implement Kalachakra, claim predictive accuracy, or certify
all traditions. No commit, push, release, generated-wiki refresh or deployment
belongs to this research checkpoint.

## 2. Sources, coordinates and evidence classes

Local paths below are relative to `C:\dev\ASTROLOGY-BOOKS-DATABASE`. PDF page
coordinates are one-based. Printed page numbers are separately identified.
Translations and commentator examples are attributed to their particular witness;
none is presented as a critical edition proving a universal ancient reading.

| ID | Source and inspected coordinates | Evidence and use |
| --- | --- | --- |
| L01 | `Classics books/BPHS-Santhanam-Vol-2.pdf`; PDF 39–54, printed 529–544, chapter 46.52–100; PDF 135, printed 625, chapter 51 antardasha explanation; PDF 309–313, printed 799–803, chapter 64 tables | Classical translation plus translator commentary. Page images checked for defective prose, both charts, both balance examples and representative AD tables. Governing witness for proposed first profile. |
| L02 | `Good books/vedic_astro_textbook.pdf`; PDF 223, printed 211; PDF 301–309 and 319–322, printed 289–297 and 307–310, chapter 24 | P.V.R. Narasimha Rao's 2000 textbook, with later preface. Primary modern formulation. Tables 44–47, Examples 95–97 and Exercise 34; critical table/example pages visually inspected. |
| L09 | `Classics books/Jataka-Parijata-Vol-3.pdf`; PDF 259–261, printed 965–967; PDF 266–272, printed 972–978; PDF 290–298, printed 996–1004, chapter XVII, especially 102–111 and commentary after 105 | Vaidyanatha Dikshita, V. Subramanya Sastri translation/commentary. L07 volume-1 preface, PDF 2, identifies a reprint of the 1932 edition. Two-school discussion and worked example on printed 1000–1002; AD rules on 1003–1004. Governing example and AD page images checked. |
| L11 | `Classics books/Mantreswara_Phaladeeplka.pdf`; PDF 209–218, chapter 22; especially 22.1–8 and 22.30 | G.S. Kapoor translation/commentary, a reflow rather than original typesetting. PDF 218 says this chapter is based on Sastri's translation. Useful corroboration and eligibility witness, not an independent vote where it republishes Sastri. Page 209 visually confirms conflicting direction labels and mapping. |
| L03 | `Classics books/Book. Encyclopedia of vedic astro - dasha systems.pdf`; PDF 40–56, printed 29–45 | Shanker Adawal compilation. Secondary orientation: eligibility and competing constructions; not the governing classical authority. |
| L10 | `Good books/vimsottari-and-udu-dasas.pdf`; PDF 12, 30, 111, 116 | Rath's broader dasha discussion. The 28-star/eight-petal Kalachakra material is not permission to replace this dasha's 27-star/108-pada seed. |
| W01 | Rao, [author-hosted textbook](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf), chapter 24 | Online primary counterpart of L02; not counted as an independent author. The author's [book index](https://www.vedicastrologer.org/articles/astro_books.htm) identifies publication in 2000. No byte-identity claim between online and local files. |
| W02 | Rath, [SJC Europe Conference 2005 handout](https://pdfcoffee.com/sanjay-rath-kalachakra-dasa-pdf-free.html), slides 3, 11–15 | Primary authored paper available as third-party extracted mirror; original announced `srath.com/conf/2005/K%e4lacakra%20das%e4.pdf` returned 404. Useful variant taxonomy; not a visually verified PDF or exact dated oracle. |
| W03 | Rao, [Kalachakra Dasa Demystified, part 1](https://blog.indianastrologysoftware.com/kalachakra-dasa-demystified-part1/) and [part 2](https://blog.indianastrologysoftware.com/kalachakra-dasa-demystified-part2/), April 2018 republication attributed to Modern Astrology/P.V.R. Narasimha Rao | Author-attributed modern article: distinguish from the 2000 textbook. The author's [video index](https://www.vedicastrologer.org/videos_a.htm) independently links his related interview; video contents were not transcribed or validated here. |
| W04 | Rao, [JHora 7.61 notes](https://vedicastrologer.org/jh/update_7.61.htm), [7.62 notes](https://www.vedicastrologer.org/jh/update_7.62.htm) | Primary software documentation: named variants and historical bug fixes. Discovery evidence, not a full computational specification or oracle export. |

Additional library searches indexed Jataka Parijata volumes 1/2 (L07/L08), the two
local *Crux of Vedic Astrology* volumes (L04/L05), and *Hindu Vedic Astrology 01*
(L12). They did not add a governing algorithm to this comparison. The local
Raman *Manual of Hindu Astrology* (L06) is an image-only PDF: its contents pages
were inspected visually, not treated as an empty book because extraction failed.
No complete Raman-specific Kalachakra treatment was established from that file.
These are bounded retrieval results, not claims that such teachings do not exist.

### Source fingerprints

SHA-256 of the local files actually used as principal witnesses:

| ID | SHA-256 |
| --- | --- |
| L01 | `ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45` |
| L02 | `2971851a3cda30929cf5b1ec56b88902bd4a141c8d5479599573ddf1c5f78242` |
| L09 | `e77f6300e66b5056cb85d42e617c0c33f3b1fbf1a5d614863fac912a8ce023fd` |
| L11 | `8b1a4dbb18e9a23c74870a6936b5b74f49e55d2cbfd1422d81eb5dccbaa2c898` |

Private extraction manifests, page images and arithmetic notebook are under
`C:\dev\outputs\ved014-research-2026-10-12`. Full source books and OCR are not
copied into the repository. Every rule needed for the proposed first profile
is specified below without dependence on private extraction state.

## 3. Common table substrate

Do not conflate **Kalachakra Dasha**, BPHS's preceding **Chakra Dasha**, the
28-star ritual/directional Kalachakra, or Buddhist Kalachakra material.

For the compared nine-sign methods, classify the 27 equal nakshatras into
108 equal padas, each 3 degrees 20 minutes (200 arcminutes). The complete
one-based nakshatra memberships are:

| Group | Members by one-based nakshatra index | Names |
| --- | --- | --- |
| S1, Ashwini | 1, 3, 7, 9, 13, 15, 19, 21, 25, 27 | Ashwini, Krittika, Punarvasu, Ashlesha, Hasta, Swati, Mula, Uttara Ashadha, Purva Bhadrapada, Revati |
| S2, Bharani | 2, 8, 14, 20, 26 | Bharani, Pushya, Chitra, Purva Ashadha, Uttara Bhadrapada |
| A1, Rohini | 4, 10, 16, 22 | Rohini, Magha, Vishakha, Shravana |
| A2, Mrigashira | 5, 6, 11, 12, 17, 18, 23, 24 | Mrigashira, Ardra, Purva Phalguni, Uttara Phalguni, Anuradha, Jyeshtha, Dhanishtha, Shatabhisha |

Authority: BPHS 46.58, 65, 71–72, 77; Jataka Parijata 17.102–105. Savya has
15 stars and Apasavya 12. S1/S2/A1/A2 avoid ambiguous left/right-foot terminology.

Traditional sign durations, in source years, are:

| Sign | Ar | Ta | Ge | Cn | Le | Vi | Li | Sc | Sg | Cp | Aq | Pi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Years | 7 | 16 | 9 | 21 | 5 | 9 | 16 | 7 | 10 | 4 | 4 | 10 |

Authority: BPHS 46.84, JP 17.6/106, L02 Table 48. The values are assigned
through the seven classical rulers; Rahu/Ketu co-lord substitutions are not used.

The following are the **selected, reconciled** sixteen rows. They are not an
unqualified literal transcription of every defective prose passage. Source
corrections are identified in section 5. Sign abbreviations follow zodiac order.

| Group/pada | Nine ordered occurrences | Total source years | Natal-row Deha / Jeeva |
| --- | --- | --- | --- |
| S1/1 | Ar Ta Ge Cn Le Vi Li Sc Sg | 100 | Ar / Sg |
| S1/2 | Cp Aq Pi Sc Li Vi Cn Le Ge | 85 | Cp / Ge |
| S1/3 | Ta Ar Pi Aq Cp Sg Ar Ta Ge | 83 | Ta / Ge |
| S1/4 | Cn Le Vi Li Sc Sg Cp Aq Pi | 86 | Cn / Pi |
| S2/1 | Sc Li Vi Cn Le Ge Ta Ar Pi | 100 | Sc / Pi |
| S2/2 | Aq Cp Sg Ar Ta Ge Cn Le Vi | 85 | Aq / Vi |
| S2/3 | Li Sc Sg Cp Aq Pi Sc Li Vi | 83 | Li / Vi |
| S2/4 | Cn Le Ge Ta Ar Pi Aq Cp Sg | 86 | Cn / Sg |
| A1/1 | Sg Cp Aq Pi Ar Ta Ge Le Cn | 86 | Cn / Sg |
| A1/2 | Vi Li Sc Pi Aq Cp Sg Sc Li | 83 | Li / Vi |
| A1/3 | Vi Le Cn Ge Ta Ar Sg Cp Aq | 85 | Aq / Vi |
| A1/4 | Pi Ar Ta Ge Le Cn Vi Li Sc | 100 | Sc / Pi |
| A2/1 | Pi Aq Cp Sg Sc Li Vi Le Cn | 86 | Cn / Pi |
| A2/2 | Ge Ta Ar Sg Cp Aq Pi Ar Ta | 83 | Ta / Ge |
| A2/3 | Ge Le Cn Vi Li Sc Pi Aq Cp | 85 | Cp / Ge |
| A2/4 | Sg Sc Li Vi Le Cn Ge Ta Ar | 100 | Ar / Sg |

These 144 entries were manually transcribed from L01 PDF 49–50 and L02
Tables 44–47, then compared independently with the latter's two 24-position
sequences (Table 43):

```text
Savya:   Ar Ta Ge Cn Le Vi Li Sc Sg Cp Aq Pi Sc Li Vi Cn Le Ge Ta Ar Pi Aq Cp Sg
Apasavya:Sg Cp Aq Pi Ar Ta Ge Le Cn Vi Li Sc Pi Aq Cp Sg Sc Li Vi Le Cn Ge Ta Ar
```

Successive blocks of nine produce S1's four rows then S2's four, or A1 then
A2, respectively. This is a table cross-check and the basis for Rao's continuous
method; it does not authorize replacing Santhanam's row-repetition continuation.
The 24-position ring and the nine-occurrence natal row are different objects.

## 4. Computational schools and distinguishing witnesses

### 4.1 Recommended first profile: Santhanam longitude, natal-row repetition

Let `f` be the fraction traversed within the birth pada, `R` its nine-sign row,
`w(s)` the sign duration, and `P = sum(w(s) for s in R)`.

1. Compute `E = f * P` source years elapsed along the row (BPHS 46.93).
2. Select the occurrence whose cumulative interval contains E. Proposed
   computational boundary convention is half-open: an exact ending belongs to
   the next occurrence. The text does not specify binary floating-point behavior.
3. The birth MD's full duration is `w(R[i])`; its remaining duration is the
   cumulative endpoint minus E. Retain its pre-birth origin.
4. Continue at `i+1`, wrapping to the same row after its ninth occurrence.
   This is explicitly witnessed twice in Santhanam's examples, printed 541–542.
5. For each MD, rotate the same nine-occurrence row from that MD's occurrence.
   AD duration is `MD_full_years * child_weight / P` (chapter 64 tables).
   Build the full AD axis before clipping to birth or a requested interval.
6. Natal-row Deha/Jeeva are the endpoints in section 3, with reversal for
   Apasavya (BPHS 46.94–95 and charts). Do not recalculate them from a truncated
   return list.

**BPHS 46.93 witness:** Moon 1 sign 4 degrees 50 minutes = 34 degrees 50
minutes, Krittika-3 (S1/3). Pada fraction `90/200`; `83 * 90/200 = 37.35`.
Ta+Ar+Pi+Aq account for 37 years. Cp has 0.35 elapsed and **3.65 remaining**,
displayed as 3 years 7 months 24 days. Printed nine-period sequence:

```text
Cp(3.65 remaining), Sg(10), Ar(7), Ta(16), Ge(9), Ta(16), Ar(7), Pi(10), Aq(4)
```

The nine returned durations total **82.65**, not 83 and not the 45.65 years
remaining in the original unrotated natal row. These three quantities must have
different names. A nine-period return bound must not add a tenth partial period
merely to fill 83 years from birth.

**BPHS chapter 64 witness:** Aries-amsa Taurus MD rotates to
`Ta Ge Cn Le Vi Li Sc Sg Ar`; denominator remains 100. Taurus/Taurus AD is
`16*16/100 = 2.56` source years = 2y 6m 21d 36gh. The first Aries/Aries AD
is `49/100` years = 0y 5m 26d 24gh. These are printed arithmetic witnesses,
not dates inferred from a modern software setting.

### 4.2 Rao 2000 continuous sequence: a distinct candidate

L02 chapter 24 uses whole-row balance but continues along its 24-position
sequence. After a row it takes the next pada; after pada four it changes the
subgroup within the same Savya/Apasavya family. This is not necessarily the next
physical nakshatra. Its ADs take the next nine occurrences from the parent's
position; the denominator is their weight sum. Deha/Jeeva in section 24.3.2
refer to the actual nine MDs beginning at birth, unlike the natal-row labels.

For the BPHS 34-degree-50-minute input, its continued sequence would instead
be `Cp Sg Ar Ta Ge Cn Le Vi Li`. This difference is our derivation from L02's
rule, not a printed Rao example. For Taurus in the first Savya row, its AD
sequence ends at Cp rather than Ar, sums to 97 and gives Taurus/Taurus
`256/97`, distinguishing it from Santhanam's `256/100`.

Independent printed witnesses and derived clipping checks:

| Witness | Inputs and exact result | What it tests |
| --- | --- | --- |
| Example 95, printed 293–294 | Moon 15Ta50; Rohini-2; `f=3/4`; elapsed `62.25/83`; **second Scorpio**, row index 7 zero-based; 2.25 years elapsed in Scorpio and 4.75 remaining | Occurrence identity, whole-row balance |
| Example 96, printed 294–295 | Moon 3Cn00; Punarvasu-4; `f=9/10`; elapsed 77.4; Pisces balance **8.6 years**, followed by S2/1's Sc, Li, Vi, Cn, Le, Ge, Ta, Ar | Pada-four continuation |
| Example 97, printed 295 | Leo AD signs `Le Cn Ge Ta Ar Sg Cp Aq Pi`; denominator **86**; Leo/Leo **25/86** source years | Recomputed AD denominator, not birth-row 83 |
| Exercise 34 and answer, printed 295/309 | Moon 5Aq50; Dhanishtha-4; elapsed 75; Gemini balance **2 years**, then Ta, Ar, Sg, Cp, Aq, Pi, Ar, Ta for the bounded first nine MDs | Apasavya subgroup rollover and repeated signs |
| Derived from Example 95 plus 97 | Scorpio's full AD sequence starts Sc, Li, Vi, Le; their cumulative ends are 0.49, 1.61, 2.24, 2.59 years after full MD start. Birth at 2.25 lies in **Leo AD**, with **0.34 years** left | Full-axis clipping; restarting Scorpio AD at birth is wrong |

Footnote 65 and printed 211 specify the author's preference for savana 360-day
years in this book, while acknowledging other conventions. Do not label a
Julian-year comparison as exact textbook date parity. The nine-MD Deha/Jeeva
examples are Scorpio/Sagittarius in reversed Jeeva/Deha order for Example 95,
and Pisces/Aries as Deha/Jeeva for Example 96. Natal-row labels differ.

### 4.3 Jataka Parijata's explicitly different school

L09's commentary after 17.105, printed 1000–1002, distinguishes:

- A **formula/row school**, where a pada supplies nine MDs and a fraction of
  their total locates the birth MD; ADs rotate through those row occurrences.
- A **pada-sign school**, where the sign assigned to the occupied pada itself
  supplies the MD; only that MD is fractionally elapsed. Subsequent MDs follow
  physical pada order. The nine-sign formula supplies that MD's bhuktis.

The commentator quotes Phaladipika in connection with both readings. This is
explicit commentator evidence for the distinction, not our reconstruction of
an unavailable Sanskrit critical edition.

**Published paired input:** Moon `9 signs, 14 degrees, 29 minutes, 39 seconds`
= 284 degrees 29 minutes 39 seconds. Shravana-2 has 69.65 arcminutes elapsed
out of 200; its row is `Vi Li Sc Pi Aq Cp Sg Sc Li`, P=83.

- Row school: elapsed **28.90475** years, giving first Scorpio occurrence with
  **3.09525** years remaining. The source rounds this to about three years.
- Pada-sign school: Libra is the assigned sign; `16*69.65/200 = 5.572` elapsed,
  leaving **10.428**. The source rounds to 5.57 and 10.43. Following MDs are
  Vi, Cn, Le, Ge, Ta, Ar... as in the commentary's planetary names/signs.
- Its later Leo MD has bhuktis `Pi Ar Ta Ge Le Cn Vi Li Sc`, weights totaling
  100, even though the parent is Leo. A generic “first AD always equals MD”
  assumption therefore fails for this school.

JP 17.107–111 supplies proportional subdivision rules, including deeper levels.
That establishes textual support for nested periods; it does not by itself
resolve every school's sequence-selection or fixed-calendar policy.

Rao's 2018 author-attributed article (W03) similarly makes pada-sign progression
the MD and the elaborate rows the AD. Its Hasta-3 example yields Gemini with
3.87 years remaining; one sentence says Virgo while its following schedule says
Gemini. Part 1's second-row illustration also ends with Virgo where the listed
2000 table has Gemini. Treat these as conflicts requiring reconciliation, not
as automatic updates to the 2000 identity. Its modified varga and ayanamsa
choices belong to that author's separate profile, not Moira's default D9/D20.

### 4.4 Further named variants: evidence found, admission bounded

Rath's 2005 handout (W02) contrasts whole-cycle and first-dasha fractions, then
four continuation choices: next physical pada, next pada within the same
nakshatra, repetition of the same pada, and chakra continuity. It favors the
last continuation and retains whole-cycle balance pending stronger comparisons.
Its extracted slide 11 reverses some Apasavya foot/Deha/Jeeva labels relative to
slides 3/15. Use the local corroborating sources for selected tables; obtain
the actual slide images before admitting a distinct Rath profile.

JHora's 7.61/7.62 notes identify S.M. Singh and Rao/Rath/Raghavacharya variants
and fixes to Apasavya ADs. A software label does not establish the algorithm.
Rangacharya and Raghavacharya must not be assumed to be interchangeable names.
Unverified forum descriptions are source leads only. No version-pinned JHora
export with complete settings was produced in this research pass.

## 5. Source-conflict decisions for planning

“Selected” below means a research recommendation; no runtime profile is admitted.

| ID | Conflict and witness | Selected handling / consequence |
| --- | --- | --- |
| KC-01 | L01 46.73–76, printed 533: Rohini-1 ends Libra in prose; Rohini-2 repeats Scorpio at the end and lists too many rulers. Same volume's printed 539 table and L02 Table 46 give Cancer and Libra respectively. | Use reconciled nine-entry tables; preserve exact defective passage coordinates and correction rationale. Never accept ten occurrences or overwrite all repeated signs. |
| KC-02 | L01 46.78–81, printed 534: Mrigashira-2 prose repeats a four-sign segment. Printed 539 and L02 Table 47 have nine entries. | Select `Ge Ta Ar Sg Cp Aq Pi Ar Ta`; repeated Ar and Ta are legitimate. |
| KC-03 | L02 printed 291 headings omit Revati from S1, put it in S2, and omit Uttara Bhadrapada. L01 membership prose/charts, JP 17.102–103 and W02 support S1 Revati / S2 Uttara Bhadrapada. | Explicit correction; exact coverage of all 27 stars, including both disputed ones. |
| KC-04 | L01 printed 540 repeats Cp in the second row of its lower Krittika block where the upper equivalent S1 row has Cp/Aq. | Use upper S1 row corroborated by L02 Table 44. Duplicate printed diagrams are not separate traditions. |
| KC-05 | L01 printed 799 extracts Scorpio as 17 though the stated total is 100; Virgo/Libra headings on printed 801 also conflict with row totals. These extraction flags are not all confirmed print errors. | Formula weights from 46.84 and independently checked arithmetic govern. Do not treat noisy AD tables as a wholesale exact oracle; promote individual visually checked cells only. |
| KC-06 | BPHS 46.90–91 example divides time elapsed by fixed 15 ghatikas; 46.92 divides by actual one-quarter nakshatra duration; 46.93 uses longitude fraction. | Initial profile selects 46.93. Time-based methods require different inputs and separate identities; current Moon longitude alone cannot reproduce them. |
| KC-07 | Santhanam repeats natal row; Rao 2000 advances in the larger sequence; JP records a separate pada-sign MD school. | Separate profile identities. No silent default hybrid or boolean named merely `classical`. |
| KC-08 | Santhanam chapter 64 rotates natal-row ADs with natal-row denominator; Rao recomputes nine forward occurrences and their denominator; JP's second school can start an AD in a sign different from its MD. | Period construction belongs to the profile, interval clipping is reusable. |
| KC-09 | BPHS 46.94–95/chart endpoints versus Rao 24.3.2's actual nine-MD endpoints. | Name the reference (`natal_row` or `birth_nine_md_window`) in results. Initial profile uses natal-row endpoints. |
| KC-10 | BPHS 46.99–100 English text gives Le→Cn while surrounding Savya sequence contains Cn→Le. JP 17.91 identifies the Cn/Le pair; Rao 24.3.3 explicitly distinguishes direction. | Preserve transition evidence and direction. Before promising a resolved “Markati” label in the initial profile, approve a cited correction or return an unresolved classification for the contested edge. Do not alter MD order to fit a label. |
| KC-11 | L11 22.1 calls the Aries-forward group Apasavya and the reverse group Savya; its seed list swaps Cancer/Leo versus the special mapping; 22.6 ends Bharani-3 with Sagittarius instead of Virgo. | Kapoor reflow is not the sequence authority. These remain distinct documented conflicts, not broad claims that Phaladeepika is unavailable or invalid. |
| KC-12 | Phaladeepika 22.30 requires strength of the Moon's navamsa lord; Rao printed 308 argues general applicability. Adawal gives further conditional discussion. | Initial numeric profile has no computed eligibility gate; report that status explicitly. Do not fabricate a strength threshold or infer unconditional agreement from availability of a calculation. |
| KC-13 | Traditional y/m/d arithmetic versus savana, Julian, tropical or sidereal date projections. | Explicit clock selection plus source-year durations; no unlabelled date oracle or silently customized clock. |
| KC-14 | L02 footnote 64 specifies nine MDs, but Exercise 34's answer, printed 309–310, lists ten, ending with another Gemini at age 85. | Preserve the longer printed witness. The section-4 table intentionally shows the first nine only; a nine-MD API bound is an explicit product choice, not proof that all source schedules terminate there. |

**Quantified time-balance conflict:** L01's Mrigashira-4 example gives bhabhoga
59gh31pala and bhayat 58gh15pala. Exact quarter is 14gh52pala45vipala; the
printed 14/52/44 is an arithmetic defect. Elapsed fourth quarter is
13gh36pala45vipala. Fixed-15 division yields 90.75 elapsed years and Taurus
balance **2.25**. Actual-quarter division yields Taurus balance
`5403/3571 = 1.5130215625875105` years. Both operate on time fractions; neither
may be called the longitude method without actual longitude evidence.

Paramayus is a traditional table total. In an API it must not be represented
as a factual lifespan estimate. Gati classification is likewise computational
metadata; source narratives about illness, death or fortune are not validated
event predictions or new election restrictions.

## 6. Engine and REST implications grounded in current code

### Existing reusable pieces and unsuitable assumptions

- [dasha_systems.py](../../moira/dasha_systems.py) implements Ashtottari/Yogini;
  its public system and validation branch admit those two only. Kalachakra is
  explicitly reserved in the module and [standard](../02_standards/ALTERNATE_DASHAS_BACKEND_STANDARD.md).
- `_sequence_from` selects by lord name and `_compute_dashas` fills a fixed
  total-year horizon, potentially adding a final partial occurrence. Those are
  unsuitable as the Kalachakra selection or nine-period coverage contract.
- [_dasha_intervals.py](../../moira/_dasha_intervals.py) partitions a full
  parent and clips children to visible bounds; it also checks representable
  JD subdivisions. Reuse its full/visible interval doctrine and compatible validators. The
  implementation plan refines the arithmetic choice: exact rational source
  partitions are projected from a common origin rather than subdividing rounded
  JD parents. It does not determine doctrine or occurrence identity.
- [alternate transport](../../moira_server/models/alternate_dashas.py) admits
  only two system names and bounds child lists at eight. Its generic `lord`
  and planet-oriented profile omit Kalachakra row/occurrence/Deha/Jeeva lineage.
  Widening a Literal alone would leave an invalid contract.
- [sidereal context](../../moira_server/services/sidereal_context.py) already
  derives requested Moon positions and explicit ayanamsa provenance, including
  UTC-to-UT1 handling. The implementation plan uses an engine-owned, reader-bound Moon adapter
  for both Python and REST, avoiding server imports and distinguishing the
  UTC-derived schedule origin from astronomical UT1/TT. Houses, location and
  fabricated birth times are unnecessary.
- [VED-013 models](../../moira_server/models/jaimini_profiles.py) demonstrate
  strict source-profile discovery, tagged input bases and bounded assessments.
  They are architectural examples, not vessels to relabel as Kalachakra.

### Recommended computational contract

Keep a dedicated Kalachakra owner with an immutable policy/catalogue and typed
result. Separate source-year computation from optional JD/calendar projection.
At minimum retain:

- Profile/version, source IDs, rule IDs and applied conflict decisions.
- Seed basis, sidereal Moon longitude, nakshatra, pada, group, within-pada
  fraction, row identity and row total. Standard D9 is not a substitute for
  the special Kalachakra seed mapping in the competing pada-sign school.
- Every period's sign index, classical ruler, occurrence index, cycle index,
  hierarchy path, full source-year interval and visible source-year interval.
- Exact integer weights and denominator; numerical projected endpoints; full
  versus remaining duration. No dictionary keyed only by sign/ruler.
- Deha/Jeeva and their reference scope. Gati records need source and destination
  occurrences, hierarchy level, direction, classification evidence and any
  unresolved source conflict. A cycle seam must not acquire a gati merely from
  a generic modular sign-distance rule.
- Coverage start/end, requested and generated depth, terminal/out-of-range
  status, year basis/days when projected, and supplied versus derived seed provenance.

Use exact ratios internally for source arithmetic where practical, then a single
declared conversion to binary64 JD. Do not snap caller longitudes across pada
boundaries to make examples pass. Define exact-edge ownership and test adjacent
representable floats. Date tolerance must be established from projection and
operation bounds, not inherited from a generic angular fixture.

### Recommended equally bounded REST contract

Proposed route family, **not existing endpoints**: `/v1/dasha/kalachakra`.
The next plan should cover discovery, source/sequence, chart-derived sequence,
and current/active-line queries. Exact names may follow repository conventions.

1. Catalogue responses distinguish admitted profiles from research candidates
   and expose source conflicts, supported depth, year choices and bounds.
2. A discriminated input must distinguish supplied sidereal longitude from
   tropical longitude plus epoch/ayanamsa. Date-derived requests accept aware
   civil timestamps and compute the Moon once through the shared context.
   Never apply ayanamsa twice or claim a supplied longitude was kernel-derived.
3. Engine and REST must reject booleans as numbers, numeric strings, nonfinite
   values, unknown profiles/year bases/ayanamsas, incompatible policies, extra
   fields and unsupported depths. Normalization of longitude must be specified
   once, with matching direct-engine behavior; recommend `[0,360)` admission.
4. Start with levels 1–2 and exactly nine MD occurrences including the residual
   birth MD: at most 90 period nodes before clipping. Deeper levels have source
   support but require their own sequence and resource admission. Reject unsupported
   choices before ephemeris work or recursive allocation.
5. A current query must use half-open intervals, preserve the unique parent path
   and explicitly report outside coverage. It must not silently manufacture
   extra cycles. Date-equivalent time zones must give identical results.
6. Serializers carry complete lineage and full/visible intervals. Prefer
   recomputation from bounded seed requests over accepting arbitrary uploaded
   period trees. If tree admission is later offered, enforce depth/node limits
   before recursion and validate occurrence/path/profile/partition consistency.
7. Deterministic bad input returns the established 422 validation contract;
   missing/out-of-coverage resources use existing typed server translation.
   Inspect those contracts during implementation; do not collapse kernel failure
   into invalid doctrine, substitute a source example, or leak an uncaught 500.
8. Add public exports/facade parity, OpenAPI strictness and matching direct versus
   chart-derived tests. API documentation must describe limits and candidacy.
   There is no reason to add a speculative native implementation for this small
   policy/table calculation.

## 7. Independent validation material and acceptance targets

### Research checks actually performed

The private `check_research_arithmetic.py` uses Python standard-library exact
fractions and hand-transcribed tables; it imports no Kalachakra implementation
and no Moira calculations. Its **468 assertions passed**, covering:

- Exactly 27 distinct group memberships and all 108 exact rational pada starts.
- Sixteen nine-entry rows, their expected totals, and 144 entries compared with
  independently assembled 24-position rings.
- All 144 natal-row AD rotations conserving their full parent source duration,
  plus all 144 within-row cumulative boundaries.
- The printed BPHS, Rao and paired Sastri balance witnesses above; different
  continuation/AD rules; full-axis natal clipping; fixed versus actual time division.

This is research arithmetic, not live engine coverage, floating-point boundary
validation, ephemeris accuracy, or software parity. The notebook's exact-edge
checks cannot substitute for `nextafter` tests in the future runtime.

Notebook SHA-256:
`678de2c55b384d3a3280ecfd60a7fad6e6b2d66d165ad76fce83d0d558511890`.
The receipt is `arithmetic_receipt.json` beside it. An initial handwritten
expectation for the clipped Rao AD was corrected during calculation: Virgo ends
at 2.24, before birth at 2.25; Leo is active. The final values are shown above.
No protected fixture, golden artifact or tolerance was changed.

### Fixtures to freeze during implementation

Freeze numerical source cases before writing the calculator, with source page,
printed expectation, corrected expectation where justified, units and tolerance.
The section-4 examples should each be independently entered, not generated by
the implementation under test. Include BPHS Aries/Aries and Taurus/Taurus AD
cells and JP's two-school example; retain candidate-profile examples as explicit
distinguishers rather than requiring an admitted profile to agree with them.

Required adversarial coverage includes all 108 padas and their adjacent floating
boundaries; exact MD/AD cutovers; every duplicate sign occurrence; natal clipping;
both chakra directions; each subgroup/pada rollover; nine-MD termination; active
lookup at birth and final endpoint; year conversion; strict Python/JSON admission;
projection overflow and loss of representable interval width; unknown provenance;
route discovery; OpenAPI; serializer round trips; kernel failures and request bounds.

Source conservation, implementation regression, real-kernel date composition and
external-software corroboration are separate evidence classes. A future JHora
comparison needs its exact version, selected variant, year method, ayanamsa,
seed longitude, birth time/timezone and generated MD/AD export. No such comparison
was completed here, and it is not needed to acknowledge the classical witnesses.

## 8. Admission decisions still needed in the implementation plan

The recommended numerical first profile is source-defined enough to plan now.
Remaining decisions are concrete:

1. Approve its exact identifier and the KC-01–05 source-correction ledger.
   Record commentary-derived continuation explicitly; avoid generic BPHS claims.
2. Choose the initial supported clocks and whether a profile call must supply
   its clock. Retain source-only arithmetic independently of dates.
3. Decide whether the contested Markati direction receives a named correction
   or an unresolved classification. Neither choice blocks the sequence arithmetic.
4. Confirm nine MDs and levels 1–2 as the first resource bound, then specify
   validators, source fixtures and engine/facade/REST routes together.

Candidate profiles remain separately identified: Rao 2000 continuous traversal,
Sastri's pada-sign school, Rao's later reformulation, Rath's named alternatives,
and software-listed methods lacking a complete reviewed recipe. Their status is
not evidence that classical texts are missing. VED-014 remains open until an
authorized implementation meets its selected engine and REST acceptance.

## 9. Workspace verification receipt

Only this packet and the VED-014 register entry are authored by this research
task. Concurrent natal-discovery/light-box changes remain outside scope.
No protected runtime, public contract, native substrate, source catalogue or
validation baseline was edited. Canonical wiki source is authoritative;
`moira.wiki/` was not hand-edited or regenerated.

Research command, from the engine checkout:

```powershell
.\.venv\Scripts\python.exe C:\dev\outputs\ved014-research-2026-10-12\check_research_arithmetic.py
```

Result: 468 exact research assertions passed.

Existing-engine baseline command:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_dasha_systems.py tests/unit/test_dasha_full_intervals.py tests/server/test_server_alternate_dashas_routes.py -q
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
git diff --check
```

Results: **170 tests passed**, no skips/failures; collection separately confirmed
170 selected tests. `tests/KNOWN_ISSUES.yml` is empty. Planetary resource discovery
with downloads disabled resolved `C:\Users\nilad\.moira\kernels\de441.bsp`.
The selected tests exercise existing Ashtottari/Yogini and shared full-interval
behavior, including chart/direct REST comparisons; they do not validate a new
Kalachakra engine. Documentation consistency and whitespace checks passed.
All research-packet relative file links were resolved successfully. The full
repository suite and software-export parity were not run for this research-only
change. Runtime and REST implementation remain the next authorized package.
