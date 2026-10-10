# VED-011: marriage-election source research

**Research checkpoint:** 10 October 2026. Research authorized; implementation
not started. This packet selects marriage as the first VED-011 purpose family.
Construction/Vastu, travel, business, website and Urania remain separate work.
**Inspected baseline:** engine `e7107267942d1926da9bcf8ba3d1299b4205ccf9`,
generated wiki `0c79a578942db2d46e11f203bc6a9c57e730ba27`, version 6.9.9.
**Authority boundary:** edition-owned traditional timing rules and their
computational implementation. Agreement with a text is not validation of its
predictions about a marriage.

## 1. Findings and admission recommendation

There is substantial usable source material, including in the local library.
A complete marriage election is a composition of calendar eligibility,
Panchanga restrictions, planetary conditions, wedding Lagna, personal
conditions and explicitly scoped exceptions. The existing Muhurta products
supply several of these components; neither a generic score nor a list of
eleven stars supplies the complete composition.

The recommended first implementation is an **ordinary marriage astronomical
timing profile owned by the 2004 Avasthi edition of Muhurta Chintamani (MC)**,
with an explicit manifest of required rules. Personal eligibility is a
separate, composable layer. An astronomical-only result must not claim to
have evaluated the couple. Godhuli needs its own exception profile and cannot
be an unconditional override. These are proposed contracts, not admitted
profile identifiers or newly available endpoints.

Six consequential findings govern that implementation:

1. MC, Vivaha Vrindavana (VV), Kalaprakasika (KP) and P.V.R. Narasimha Rao
   (PVR) agree on an eleven-star wedding set which differs from Moira's
   legacy guidance. The legacy tithi lists also contradict one another.
2. Source differences affect outcomes: lunar dates, weekdays, forbidden
   quarters, Mars in the eighth, permissible months and Godhuli remedies
   cannot be collapsed into one supposedly universal policy.
3. MC requires additional calculations, including five/seven-line vedha,
   Latta, star-history restrictions, Jamitra and distinct Bana formulae.
   Existing Panchaka, Gandanta and Lagna checks do not cover all of them.
4. Jupiter/Venus asta, balya and vriddha have numerical source support.
   Surya Siddhanta (SS) IX defines visibility using degrees of time and
   directional events. Moira's current longitude-orb combustion predicate
   is a different named convention, not an implementation of that recipe.
5. The ceremony's evaluated instant and the roles assigned to personal
   conditions must be declared. The source does not authorize silently
   treating a whole event booking, one partner's birth star or compatibility
   scoring as the wedding election.
6. A published wedding calendar is only an oracle for its published rule
   subset. Drik Panchang expressly omits several checks Moira intends to
   expose. Matching its dates would not establish full-profile correctness.

**Decision:** proceed to an implementation plan for this finite family using
the rule inventory, policy decisions and acceptance gates below. The research
packet is complete as a source/contract investigation; VED-011 remains open
until the selected engine, public Python and REST contract is implemented and
validated. No claim of exhaustive agreement among marriage traditions is made.

## 2. Research method and source identity

The local corpus was searched by filename and extracted text, followed by
inspection of rendered pages at the relevant loci. Image-only books were
handled as scans: the Brihat Samhita file has useful extracted text on only
one of 1,105 pages, and the 155-page Raman Manual has no extracted text.
An empty search result in those files is not evidence that a rule is absent.

Seven local-library PDFs and five additional source PDFs were fingerprinted.
Relevant passages were collated; this was not a cover-to-cover review of all
twelve volumes. The four electional scans reused from the 8 October research
were identified again by their title pages and hashes; online catalogues,
digital texts, the PVR author site and the published Drik calculation policy
were checked during this pass. A fresh SS scan was downloaded and its
heliacal chapter inspected visually.

Private working evidence is under
`C:\dev\outputs\ved011-marriage-research-2026-10-10`: `source_manifest.json`,
page-indexed extraction JSON, rendered page images, and the research probe
and its receipt. PDF page numbers in this document are **one-based**; printed
page numbers and chapter/verse identifiers are separately stated. Source
PDFs and whole-book extracted text are not added to the repository.

| ID | Source, edition and access | Inspected loci and evidential use |
| --- | --- | --- |
| MC | Rama Daivajna, *Muhurta Chintamani*, Ramlal Avasthi commentary, Chandika Prasad Avasthi editor, Tejkumar Book Depot, Lucknow, tenth edition 2004; 207-page scan. [Archive catalogue](https://archive.org/details/muhurta-chintamani-hindi); [digital Sanskrit witness](https://www.ebharatisampat.in/read_chapter.php?bookid=MjQwNjAyMzE4NTQyMDYy). | Samskara 26–28, printed 85–86/PDF 94–95; Vivaha 12–16, printed 104–106/PDF 113–115; wedding-star and vedha rules 55–58, printed 127–130/PDF 136–139; detailed restrictions 59–74, printed 131–140/PDF 140–149; Lagna/exception rules 75–101, printed 140–153/PDF 149–162. Main proposed authority; verse, commentary and implementation convention must remain distinguishable. |
| VV | Keshava, *Vivaha Vrindavana*, Sitarama Jha's Vasantalakshmi Sanskrit/Hindi commentary, Master Khelari Lal & Sons, Benares; cover says first edition Samvat 1991; Archive catalogue dates it 1935; 138 pages. [Catalogue](https://archive.org/details/in.ernet.dli.2015.329463). | Nakshatra-shuddhi 1.3–4, printed 2–3/PDF 15–16, including explicit Pushya/Purva Phalguni objection; Chandra-bala discussion printed 45/PDF 58, verses 7–8 argues for the groom's Moon as well. Godhuli locus is also owned by the earlier named-window research; its numerical interval is not attributed to BS. |
| KP | N. P. Subramania Iyer, *Kalaprakasika*, Sanskrit/English, Asian Educational Services 1982 reprint; introduction dated January 1917; 490 pages. [Source PDF](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf). | Chapter XIV, printed 79–87/PDF 116–124. Independent marriage rule collection with explicit best/middling/avoid distinctions and conflicting placements. Online PDF retrieval timed out in this pass; the previously downloaded, fingerprinted scan was inspected locally. |
| R | B. V. Raman, *Muhurtha*, 110-page reflowed transcription, underlying printing not established. [Available copy](https://storage.yandexcloud.net/j108/library/tuwzcd7e/B.V._Raman_-_Muhurtha_%28Electional_Astrology%29.pdf). | Marriage passage PDF 64–65. Useful modern witness and variant lead; not sufficient to lock an edition-specific production profile until a printed edition is collated. |
| BS | *Brihat Samhita*, V. Subrahmanya Sastri and M. Ramakrishna Bhat, V. B. Soobbiah & Sons, 1946; local `Classics books/brihatsamhita.pdf`, 1,105 pages. [Independent 1884 Iyer translation](https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc229367.html). | Chapter 103, printed 764–768/PDF 781–785: wedding house placements and Godhuli. The 1946 chapter heading explicitly says **“of Vindhyavasin”**. Cite the chapter as presented in this edition, rather than making unqualified authorship claims for every verse. PDF offsets elsewhere in the volume differ. |
| PVR | P. V. R. Narasimha Rao, *Vedic Astrology: An Integrated Approach*, local `Good books/vedic_astro_textbook.pdf`, 515 pages. Author's [book page](https://www.vedicastrologer.org/articles/astro_books.htm) identifies publication in 2000; [author-hosted PDF](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf). | Chapter 36, printed 472/PDF 484 on the ritual anchor; Table 79, printed 474/PDF 486 on wedding limbs; printed 475/PDF 487 qualifies the empty-seventh guideline. Modern author's stated practice, not automatically a classical verse. |
| PS | **P. S. Sastri**, *Text Book of Scientific Hindu Astrology*, Ranjan Publications; exact printing not established; local `Books by Authors/BV Raman/Scientific-hindu-astrology.pdf`, 521 pages. | Printed 100/PDF 95 and adjoining discussion: general Muhurta guidance. The folder's Raman label is not the book's authorship. General rules are not automatically wedding rules. |
| MANUAL | B. V. Raman, *A Manual of Hindu Astrology*, local `Books by Authors/BV Raman/A Manual of Hindu Astrology by BV Raman.pdf`, 155-page image-only scan. | Front matter/contents inspected; not used as a wedding-rule authority and not declared exhaustively searched. |
| UK | Local `Classics books/Uttara-kalamrita-kalidas.pdf`, 166 pages. | Marriage-related passages located around PDF 123–128 concern kinship/social/ritual context; not used to manufacture numerical election rules. No whole-book absence claim. |
| BPHS1/2 | Santhanam BPHS local `Classics books/BPHS-Santhanam-Vol-1.pdf` and `BPHS-Santhanam-Vol-2.pdf`, 482/552 pages. | Targeted text search and existing owned dignity/Navamsa/strength standards. Natal marriage indications or Dasha timing do not by themselves prescribe a marriage election. No claim of a complete wedding policy derived from these searches. |
| SS | Ebenezer Burgess, *Translation of the Surya-Siddhanta*, American Oriental Society, 1860; 393-page scan. [Source PDF](https://www.wilbourhall.org/pdfs/Translation_of_the_S__rya_Siddh__nta.pdf). | Chapter IX.1–11, printed 221–224/PDF 237–240. Primary astronomical definition and thresholds for heliacal disappearance/reappearance. Chapter VIII commentary printed 210/PDF 226 also discusses the unequal Abhijit insertion. |

Two collation hazards were caught by checking page images. PVR Table 79's
row for placing idols has a different tithi/weekday list immediately below
the wedding row; extracted row order must not transfer it to weddings. In
MC's seven-line vedha, the actual pairs include **Dhanishtha–Vishakha** and
**Chitra–Purva Bhadrapada**. Merely checking that a table contains 28 unique
stars would not catch swapping those partners.

## 3. The shared wedding-star set and the legacy defect

MC Vivaha 55, VV 1.3, KP XIV and PVR Table 79 support these eleven:

| Star | One-based ordinary 27-star ordinal |
| --- | --- |
| Rohini | 4 |
| Mrigashira | 5 |
| Magha | 10 |
| Uttara Phalguni | 12 |
| Hasta | 13 |
| Swati | 15 |
| Anuradha | 17 |
| Mula | 19 |
| Uttara Ashadha | 21 |
| Uttara Bhadrapada | 26 |
| Revati | 27 |

This is a necessary list condition in those passages, not sufficient election
eligibility. MC also requires freedom from vedha; other sources attach
different quarter exclusions. VV 1.4 explicitly argues against treating
Pushya or Purva Phalguni as generally acceptable wedding stars.

At the inspected baseline, [legacy guidance](../../moira/muhurta.py) contains:

- `good_nakshatras`: Pushya and Shravana instead of Magha and Mula;
- `avoid_nakshatras`: Mula, despite its inclusion in the collated eleven;
- `good_tithis`: `[1,2,3,4,6,7,9,10,11,12,13]`;
- `preferred_tithis`: `[2,3,5,7,10,11,13]`;
- `avoid_tithis`: `[0,3,8,13,29]`, with a zero-based comment.

Raw values **3 and 13 appear in both good and avoid** irrespective of how an
index convention is subsequently interpreted. “Preferred” contains 5, which
is absent from “good”. The source comment does not resolve these conflicts.
`get_muhurta_guidance_for_activity` returns this dictionary directly.

This is a real legacy data/documentation defect. Existing REST provenance
explicitly reports `activity_guidance="not_admitted"`, so it is not evidence
that an already-admitted complete wedding endpoint is returning these rules.
The implementation plan should replace or explicitly deprecate this guidance
under a documented compatibility decision, with a fixture for the exact
eleven-star set and a single explicit tithi representation. This research
pass records the defect and does not silently change the legacy API.

## 4. Disagreements that must survive composition

| Axis | Evidence | Required treatment |
| --- | --- | --- |
| Tithi | MC 55 excludes Rikta 4/9/14 and Amavasya at this locus. KP distinguishes best 2/3/5/7/10/11/13 from middling dates, and separately rejects the dark half after its eighth. PVR wedding row includes 12 and 15. Raman's transcription rejects 6/8/12 and dark 11 through Amavasya. | Separate paksha-aware profiles; do not present the MC locus alone as the exhaustive tithi doctrine or import PVR's 12 into Raman. Resolve broader prohibitions before positive preferences within each profile. |
| Weekday | MC Avasthi's explanation of 55 and PVR list Monday, Wednesday, Thursday, Friday. KP rejects Sunday/Saturday/Tuesday. Raman grades Sunday/Saturday middling. | Best/middling/forbidden are distinct; no universal four-day filter claimed for every source. |
| Star quarters | Raman excludes first Magha/Mula quarters and last Revati quarter. MC's selected Gandanta calculation has its own precise intervals. | A whole pada is not the same object as a ghati-based junction restriction. Preserve both only when the selected profile requires both. |
| Solar/lunar calendar | MC Vivaha 13 names Sun in Aries, Taurus, Gemini, Scorpio, Capricorn, Aquarius and specific lunar-month qualifications, including the opening Ashadha portion through Shukla Dashami with Gemini Sun. MC Samskara 26 has a general Dakshinayana restriction. KP calls Dakshinayana middling. | MC's specific Scorpio permission and its general restriction require a disclosed precedence rule. Six solar signs alone do not implement the lunar clauses. Do not apply a modern Chaturmas switch as if it were an identical verse. |
| Mars in eighth | KP chapter XIV's eighth-house result is favorable to Mars. BS 103.8, Raman and the selected MC restrictions treat it adversely, subject to their own exceptions. | Preserve the disagreement. Do not rewrite the shared planet-house detector or import a cancellation across sources. |
| Seventh house | MC includes Jamitra from Lagna and Moon and a more precise Navamsa treatment. PVR gives an empty-seventh guideline, then qualifies it for strong benefic configurations. | Existing Lagna seventh occupancy is only part of MC Jamitra. PVR's qualitative qualification does not define an arbitrary Shadbala threshold. |
| Karanas | PS's general guidance rejects the final five including Kinstughna. Drik's marriage policy rejects Vishti, Shakuni, Chatushpada and Nagava and explicitly allows Kinstughna. Existing Bhadra checks address Vishti. | A Vishti-only result must not claim full marriage Karana eligibility; a modern site's choice is not a silently universal classical rule. |
| Birth context | MC 12 assigns Jupiter to the bride, Sun to the groom and Moon to both. VV argues for the groom's Moon as well. MC 14 and KP differ over first-born birth-period restrictions. | Require explicit roles and needed birth/context data. Missing partner evidence is unavailable, not favorable. Family status cannot be inferred from ephemerides. |
| Godhuli | BS 103.13 gives a twilight remedy without a minute formula. MC 99–101 combines broad relief, seasonal descriptions and retained planetary/weekday qualifications. VV owns the existing half-ghati each side of half-set geometry. | Name both temporal and exception authorities. An existing Godhuli window does not automatically waive every wedding rule. |
| Regional and extraordinary context | MC 69 and commentary distinguish regional handling; MC Samskara's Ketu/utpata context includes extraordinary omens. | Do not infer a school from longitude or reinterpret every historical “Ketu” occurrence as the calculated lunar node. Explicitly exclude non-ephemeris omen judgments from the first astronomical profile. |

Historical social classifications, age prescriptions, kinship eligibility,
family ritual spacing and predicted personal misfortunes are not proposed
as numerical marriage-eligibility outputs. Their presence in a chapter is
recorded; the first product's object is the timing calculation. Compatibility
matching remains [candidate C-01](VEDIC_REMAINING_WORK_REGISTER.md), a different
object from natal-to-election Tara/Chandra strength.

## 5. MC rule inventory and engine ownership

“New” below means not supplied by the presently admitted marriage composition,
not that no arithmetic helper anywhere in Moira could be reused. The final
implementation manifest must identify every required rule and every explicit
exclusion. Passing a subset must not be relabelled “complete MC Vivaha”.

| MC locus | Governing object | Existing component / required work |
| --- | --- | --- |
| Samskara 26–28 | Guru/Shukra asta, balya, vriddha; variants and event context | New marriage availability layer over a named astronomical event definition. See section 7. |
| Vivaha 12 | Bride Jupiter, groom Sun, both Moons relative to birth context | Reuse canonical sidereal positions and inclusive sign arithmetic; add source-specific role rules and personal completeness. Do not reuse a Moon-only Gochar verdict for the Sun/Jupiter roles. |
| 13 | Solar signs and lunar-month qualifications | Reuse [lunar-month owner](../../moira/lunar_month.py); add marriage predicates and declared month/ayanamsa/precedence policy. Exceptional unavailable calendar evidence must propagate. |
| 14–16 | First-born/birth-period and family ceremony context | Optional separately declared personal/context extension; not inferred from a chart. Keep source-specific first-born differences. |
| 21 onward, especially 24 | Couple matching, including Tara Kuta | Separate from election Tara Bala; excluded from ordinary astronomical-only assessment. |
| 55 | Eleven permitted wedding stars, tithi and related qualifications | New typed purpose rule; reuse Panchanga identities, not the contradictory legacy dictionary. |
| 56 | Pancha-shalaka vedha and opposing padas | New edition-owned star-pair/pada relation; unequal Abhijit partition. |
| 57–58 | Sapta-shalaka vedha, planet nature, occupied/pierced/passed stars and Moon clearance | New relation plus event-history evidence. Single-epoch longitudes cannot settle the history clauses. |
| 59 | Planet-specific forward/backward Latta | New counted-star rule with explicit origin inclusion and 27/28 counting selection from its own locus; do not silently reuse the seven-line grid. |
| 60 | Pata and quoted alternative prescriptions | New named rule variants; ending a yoga and its affected star require event context. |
| 61 | Krantisamya sign-pair prescription | New source relation. A similar English name does not authorize replacing it with physical declination equality. |
| 62 | Ekargala under selected yogas and odd star separation | New rule using its expressly Abhijit-inclusive count and source yoga list. |
| 63–64 | Upagraha and pada qualification; adverse eighth of daylight | New source rules; full daylight parent and source weekday convention needed. “Upagraha” here must not alias an unrelated calculated point by name alone. |
| 65 | Kulika by day/night fifteenths | Reuse solar-day parents; add source segment indices and Saturday's additional qualification. Distinct from Gulika upagraha longitude. |
| 66 | Dagdha tithis by solar sign | New small, source-fixtured mapping. |
| 67–68 | Jamitra from Lagna/Moon; 55th Navamsa; specific relief | VED-010 covers selected Lagna occupancy, not all these source conditions. Preserve the precise and broader formulations as named rules. |
| 69–71 | Regional treatment, Sun/Moon nakshatra combinations and scoped relief | New source-specific composition. Source relief must target the named detected restrictions. |
| 72–74 | Two Bana calculations and their contextual applicability | New rules; neither is the existing Panchaka sum. Day/night and purpose applicability remain part of each finding. |
| 75–78, 84–88, 92 | Aspects, Navamsa, placements, selected exceptions, source placement score | Reuse [VED-010 Lagna owner](../../moira/muhurta_lagna.py) and dated owner. It already exposes four/five-Navamsa choice and optional source exceptions. Its placement score is not the aggregate wedding verdict. |
| 79–83 | Additional Lagna qualities and restrictions | New admission and fixtures required before a broad chapter-completion claim. The passage is located; source availability is not the obstacle. |
| 88–91 | Kartari and wider cancellation prescriptions | Existing Lagna catalogue explicitly excludes Kartari and broad 89–91 relief. Add them as individually sourced rules, or name their exclusion and limit the profile claim. |
| 93–95 | Strength/context and special marriage-form qualifications | Do not convert prose into an unexplained numeric cutoff or universal exception. First profile should state the selected ordinary-ceremony boundary. |
| 96–98 | Preparatory acts/mandapa | Separate event targets; not automatically evaluated at the wedding anchor. |
| 99–101 | Godhuli timing and exceptions | Reuse named-window geometry where source-compatible; build a separate exception policy with retained restrictions. |

The related [Panchanga Shuddhi](VEDIC_PANCHANGA_SHUDDHI_SOURCE_RESEARCH_2026-10-08.md),
[named-window](VEDIC_NAMED_MUHURTA_FIVE_SOURCE_AND_PLAN_2026-10-08.md) and
[Lagna](VEDIC_LAGNA_SOURCE_AND_PLAN_2026-10-09.md) research remain the owners
of their admitted components. VED-011 should compose their canonical results
rather than rebuilding them in a server serializer.

## 6. Concrete arithmetic fixtures recovered from the source

These transcriptions are research fixtures for a forthcoming implementation;
their arithmetic checks do not certify a production evaluator.

### 6.1 Abhijit and seven-line vedha

MC 55's commentary defines Abhijit from the final quarter of Uttara Ashadha
through the first fifteenth of Shravana. Under the ordinary equal-angle
27-star sidereal partition, this yields **276°40′ through 280°53′20″**.
This conversion is arithmetic derived from the specified portions, not a
claim that Abhijit is an equal twenty-eighth star. Boundary ownership must be
declared (recommended half-open intervals). Count-grid identity and physical
longitude membership must both be visible in evidence.

MC 57, printed 129/PDF 138, gives these fourteen reciprocal pairs:

| First star | Pierced counterpart |
| --- | --- |
| Jyeshtha | Pushya |
| Shatabhisha | Swati |
| Purva Ashadha | Ardra |
| Revati | Uttara Phalguni |
| Dhanishtha | Vishakha |
| Uttara Ashadha | Mrigashira |
| Ashwini | Purva Phalguni |
| Ashlesha | Anuradha |
| Hasta | Uttara Bhadrapada |
| Rohini | Abhijit |
| Mula | Punarvasu |
| Chitra | Purva Bhadrapada |
| Bharani | Magha |
| Krittika | Shravana |

MC 56's five-line rule has its own pairs and opposing pada qualification:
Rohini–Abhijit, Bharani–Anuradha, Uttara Ashadha–Mrigashira,
Shravana–Magha, Hasta–Uttara Bhadrapada, Swati–Shatabhisha,
Mula–Punarvasu, Uttara Phalguni–Revati; pada 1 opposes 4 and 2 opposes 3.
Do not merge this table with the seven-line table into an unlabeled union.
MC 57–58 distinguishes cruel/benefic effects and time-history conditions;
the named planet-nature profile must be recorded rather than assumed.

### 6.2 Latta and Bana are not generic Panchaka

MC 59 and the selected Avasthi commentary prescribe forward counts for Sun 12,
Saturn 8, Jupiter 6, Mars 3, and Rahu 9; backward counts for Mercury 7,
full Moon 22 and Venus 5. The Rahu direction follows the commentary's explicit
qualification and is not a generic reversal for retrograde motion. Every fixture
must state whether the occupied star counts as one and which grid is used.
Changing direction merely because a planet is retrograde requires its own
source rule; it is not inferred from the word “backward”.

MC 72's southern Bana rule combines **elapsed tithi and Lagna**, modulo nine:
remainders 8 illness, 2 fire, 4 royal, 6 theft, 1 death (printed 139, PDF 148).
This corrects the initial research transcription. It differs from the
existing [Panchaka](../../moira/panchanga_shuddhi.py) input sum of running
tithi, weekday, nakshatra and Lagna. Elapsed versus running tithi changes
boundary outcomes and must be transcribed into a worked fixture before
admission.

MC 73 uses elapsed whole degrees within the Sun's sign, separately adding
6/3/1/8/4 and checking remainder 5 modulo nine for those five Bana types.
MC 74 qualifies the applicability by night/day, weekday and activity; these
are not five unconditional all-day wedding vetoes. Its commentary identifies
Saturday royal, Wednesday death, Tuesday fire and theft, and Sunday
illness associations (printed 140, PDF 149) and distinguishes purpose-specific
prohibitions. These correct the initial weekday transcription.

### 6.3 Source-sized temporal partitions

MC 64's adverse daylight eighths by Sunday through Saturday are
**4, 7, 2, 5, 8, 3, 6**. MC 65's daylight Kulika fifteenths are
**14, 12, 10, 8, 6, 4, 2**, with preceding night fifteenths
**13, 11, 9, 7, 5, 3, 1** and an additional Saturday final-night qualification.
The relevant full day/night must be determined before clipping to a request.

MC 66's Dagdha pairs are Sagittarius/Pisces → 2, Taurus/Aquarius → 4,
Cancer/Aries → 6, Virgo/Gemini → 8, Leo/Scorpio → 10,
Capricorn/Libra → 12. These are tithi identities, not zero-based array indices.

The private research probe checks the eleven-star transcription against the
legacy AST, the seven-line pair coverage/reciprocity, these small mappings
and the rational Abhijit conversion. Visual collation is still the authority
for the table: uniqueness alone cannot establish the correct pairs.

## 7. Jupiter/Venus availability: a source-backed computational route

### 7.1 Event definition

SS IX.1–5, Burgess printed 221–222/PDF 237–238, distinguishes heliacal
disappearance/reappearance from ordinary daily horizon crossings. It uses
the ascensional interval at sunset/sunrise, with the planet's apparent-place
correction, converted to **degrees of time (kalabhaga)**. The commentary
explicitly distinguishes this from longitude separation.

SS IX.6–9, printed 223/PDF 239, supplies:

| Planet/event branch | Threshold in degrees of time |
| --- | --- |
| Jupiter | 11 |
| Venus setting in the west or rising in the east | 8 |
| Venus setting in the east or rising in the west | 10 |

The chapter also gives Mars 17, Saturn 15 and Mercury 12/14 with its branch
qualification. Those are corroborating context, not a request to extend
the first marriage availability feature to every planet. IX.10–11 describes
finding the time of the event from the interval's rate of change.

This answers the source-availability question: the thresholds and underlying
astronomical quantity are available. Implementation still needs a declared
adapter. Reproducing the historical SS ephemeris and using modern Moira
positions in source-derived rising/setting geometry are distinct policies.
The recommended first modern adapter must disclose that derivation, its
coordinate/horizon conventions, event equality handling and polar limits.
Independent worked examples must verify the translation from SS's units.

Moira's [avastha combustion predicate](../../moira/avasthas.py) currently
uses Sun-relative longitude orbs; Venus has a fixed 10° direct-orb
convention. Numerically sharing Jupiter's number 11 does not make the two
quantities identical. The general [heliacal owner](../../moira/heliacal.py)
has astronomical machinery and modern physical visibility models, but those
models must not be relabelled SS IX either. An adapter must name the model
it actually executes and preserve the event evidence.

### 7.2 Waiting periods

MC Samskara 27, printed 86/PDF 95, distinguishes:

| Body and direction | Balya after appearance | Vriddha before disappearance |
| --- | --- | --- |
| Venus in eastern sky | 3 days | 15 days |
| Venus in western sky | 10 days | 5 days |
| Jupiter | 15 days | 15 days |

Samskara 28 reports further 10-day, 7-day and urgent 3-day alternatives.
They are variants, not permission for the implementation to choose the
shortest interval automatically. KP XIV instead specifies a week after
Venus's rise, eight days after Jupiter's rise and fifteen before Jupiter's
setting; its “just prior” Venus wording does not supply a numeric interval.
Do not invent a duration and present it as KP's number.

Implementation must distinguish the actual invisible interval from the
before/after buffer, retain event direction, and resolve adjacent events
outside the requested date range. A buffer may affect the requested day
even when the heliacal event lies outside it. Fixed elapsed days versus
local sunrise-counted days is an additional explicit computational choice;
the passage does not independently settle that modern boundary convention.
The first profile should name one convention and test both edges, rather
than hiding it inside a date comparison.

## 8. Ceremony, partners and exception policy

PVR printed 472 acknowledges ambiguity about the wedding's exact moment
and proposes the tying of mangalasutra in the described practice. This is
the modern author's proposal. Moira should accept an explicit **ritual
anchor label** and evaluate that instant or the candidate range for that
anchor. A start time, contractual booking interval, vows and preparatory
rituals are different targets. Requiring an entire ceremony to fit inside
an eligible interval should be a separately explicit query mode.

The personal layer should accept two participant records plus explicit
traditional role assignments where the selected rule needs bride/groom
roles. No role should be inferred from a name. The first implementation
can evaluate ordinary astronomical timing without birth data, but must
return `personal_assessment_unavailable` rather than an overall personal
pass. If personal assessment is requested, neither missing participant nor
missing birth-month/first-born context may silently disappear from coverage.

MC Vivaha 12's bride-Jupiter, groom-Sun and both-Moon conditions must remain
individually inspectable. Election Tara Bala and couple-to-couple Tara Kuta
must have different input/result identities. The shared Tara profile's
existing purpose-dependent Janma uncertainty is not resolved by simply
renaming the current result “marriage”.

For cancellation, preserve:

- the detected restriction and the source evidence that detected it;
- the named exception, its exact target rule IDs and prerequisites;
- whether every prerequisite was evaluated and satisfied;
- the remaining effective restriction and any unavailable prerequisites.

A named auspicious yoga, Godhuli presence or a high placement/Shadbala score
must not erase all raw findings. PVR's benefic-seventh qualification, MC's
specific placement remedies, and BS's Godhuli verse belong to different
authorities. Combining a VV temporal window with an MC exception is an
explicit derived composition, not a falsely single-source profile.

## 9. Proposed engine, public Python and REST contract

The engine should own three objects: a discoverable profile catalogue,
an instant assessment, and a bounded dated interval assessment. The public
facade and typed REST transport should preserve those same objects. Exact
function/route names belong in the implementation plan; none are admitted
by this research document.

Each result needs the profile/version, source loci, ephemeris/frame/time
receipt, ritual anchor, participant coverage and per-rule findings.
Aggregate decisions should distinguish **passes selected profile**,
**restricted**, and **indeterminate**. Coverage completeness is a separate
field: a known restriction can establish “restricted” even when another
required condition is unavailable, but incomplete evidence cannot establish
a pass. Excluded optional layers must remain visible without being called
evaluated. No “marriage suitability percentage” is justified by this packet.

The first profile should lock these axes instead of accepting an arbitrary
bag of favorable switches:

| Axis | Proposed decision or explicit admission question |
| --- | --- |
| Governing edition | MC Avasthi 2004 for the ordinary marriage timing profile. Other books remain separately named variants. |
| Calendar precedence | Prefer the marriage-specific Vivaha 13 prescription over the general Samskara prohibition where they conflict; label this as the composition decision, not a new textual quotation. A conservative intersection would be a different profile. |
| Astronomical conventions | Explicit ayanamsa, node model, coordinate frame, solar-event horizon and resource provenance, consistent across component receipts. |
| Star grids | Rule-owned ordinary 27-star versus unequal Abhijit-inclusive 28-star identity; never a global switch applied indiscriminately. |
| Weekday/time | Sunrise-owned traditional weekday for rules that require it; preserve UTC/JD weekday in existing Shadbala evidence where that owner requires it. A civil midnight must not silently change the traditional day. |
| Asta and buffers | Source-derived SS event adapter and the selected MC 27 buffer variant, with an explicit day-count convention. Fixed-orb compatibility must be separately named if offered. |
| Lagna/Navamsa | Reuse the existing MC source profile and its explicit four/five-Navamsa choice; extend missing required wedding restrictions rather than implying they already exist. |
| Personal assessment | Explicitly requested layer with both participants and role/context completeness. No matching-score substitution. |
| Remedies | Individually opt-in or fixed by the selected named profile; finite target lists, no score-based global cancellation. |
| Godhuli | Separate temporal/exception profile; keep the ordinary-profile result available for comparison. |
| Context exclusions | Explicit ordinary astronomical timing scope; matching, social eligibility, non-ephemeris omens and other ritual events outside this first contract. |

The dated evaluator must split on every transition that can change a
selected rule: Panchanga limbs, star/pada boundaries, all participating
planetary star/vedha changes, Sun ingress, Lagna/D9/aspect transitions,
solar day/night boundaries, lunar-month boundaries, heliacal events and
their buffer edges. History-dependent conditions need a bounded lookback
or an unavailable result. Compute complete parents before request clipping.
Midnight, DST changes and longitude wrap must not corrupt event ordering.

The existing [Muhurta search](../../moira/muhurta_search.py) explicitly owns
a bounded sampled-score product. It does not already supply this continuous
intersection, sunrise-owned calendar or complete marriage policy. A sampled
mode could remain available with its sample provenance, but must not export
unverified spans between samples as exact eligible intervals.

Set work limits after profiling the actual selected transition inventory.
Report horizon unavailability, unsupported calendar branch, missing kernel,
budget exhaustion and no eligible interval as different outcomes. Reuse
the serving ephemeris reader; retain borrowed-reader ownership and avoid
silent resource fallback. REST must strictly validate finite numbers,
booleans-as-numbers, unknown profiles/fields, contradictory receipts and
unsupported partial contexts. Server code must not repair, score or override
canonical engine findings.

## 10. Validation and independent comparison

Acceptance requires source fixtures plus computational and transport checks;
neither internal consistency nor a commercial calendar is sufficient alone.

| Test family | Required evidence |
| --- | --- |
| Source transcription | Exact eleven stars; paksha-aware tithi identities; all fourteen seven-line pairs including Dhanishtha–Vishakha and Chitra–Purva Bhadrapada; independent five-line table; every numerical mapping traceable to page/verse. |
| Boundary partitions | Rational Abhijit endpoints, both adjacent stars/padas, 0°/360°, all applicable half-open edges; no equal-28 partition. |
| Distinct formulae | MC Latta direction/count fixtures; MC 72 elapsed-tithi Bana versus running-tithi Panchaka; MC 73 solar-degree Bana; daylight eighths versus fifteenths; opposite test outcomes where formula substitution would look plausible. |
| Calendar precedence | Scorpio under the chosen MC-specific precedence; Gemini/Ashadha Dashami boundary; ingress inside a lunar date; adhika/kshaya and unsupported month cases; no six-sign-only false completeness. |
| Asta model | Source-owned worked time-degree examples, both Venus branches and Jupiter; equality/just-inside/just-outside tests; geographic latitude effects; explicit divergence from fixed longitude-orb combustion; event direction and buffer crossings. |
| Personal completeness | Both participants; swapped roles; missing Moon/Sun/Jupiter or birth context; Tara Bala versus Tara Kuta; unknown prerequisite must never produce a personal pass. |
| Exceptions | Raw findings retained, exact target mapping, missing prerequisite, competing restrictions, Godhuli with a retained prohibition; a high generic score cannot neutralize them. |
| Source disagreements | The same synthetic case may legitimately pass one named policy and fail another: Sunday, tithi 12, Mars eighth, Pushya, and quarter/Gandanta cases must have explicit expected policy-specific outcomes. |
| Dated composition | Every governing event class, full parents before clipping, negative timezones, DST, before sunrise, polar conditions and event-history limits; dense sampling is a useful additional witness, not the definition of exact intervals. |
| Engine/HTTP/resources | Direct/facade/HTTP equality of all findings and receipts; strict hostile input tests, reproducible bounds and serving-reader proof; unavailable versus empty interval distinguished. |

Drik's [published wedding calculation policy](https://www.drikpanchang.com/shubh-dates/info/choosing-auspicious-marriage-date.html?lang=en)
is useful specifically because it states exclusions: its published wedding
dates do not incorporate tithi, weekday or Lagna selection, and it excludes
Simhastha Guru and Holashtak checks from that calculation. It also documents
its own solar/month and Karana choices. A future external fixture must carry
location, timezone, source date/version and the exact shared rule subset.
Differences outside that subset are not automatically Moira defects.

No full paired external marriage-election oracle was established in this
research pass. That does not block source-owned arithmetic fixtures and
independent astronomical comparisons. It does prevent claiming that a whole
profile has already been externally certified. Before implementation closure,
assemble worked cases that expose both the input positions and the source
decisions, with disagreements classified rather than edited away.

## 11. Next implementation package and closure boundary

The next plan should cover these coherent units, with one final end-to-end
acceptance gate:

1. **Profile and legacy repair:** exact source manifest, rule coverage,
   strict typed catalogue, one tithi representation and an explicit migration
   for the legacy guidance defect.
2. **Missing wedding calculations:** unequal star grids, vedha/Latta and
   associated doshas, distinct Bana/Kulika/Dagdha rules, source calendar
   predicates and the remaining selected Lagna restrictions.
3. **Jupiter/Venus availability:** declared SS-derived event geometry,
   directional MC buffers and independent astronomical fixtures. This is a
   real source-backed dependency, not “classical evidence unavailable”.
4. **Composition and personal scope:** ordinary astronomical assessment,
   optional complete personal layer and finite cancellation targets;
   separately named Godhuli behavior.
5. **Bounded dated service and parity:** transition-owned intervals,
   resource/work limits, public/facade/REST identity, adversarial acceptance,
   owning standard and validation receipt.

Before code changes, the plan must turn every “new” or partially covered row
in section 5 into either a concrete required rule or an explicit exclusion
that narrows the product's name and completeness claim. No required but
unimplemented rule may be silently converted into an optional omission.
Literal historical astronomy versus modern source-derived geometry, time
buffer counting and qualitative cancellation prerequisites require named
decisions and worked fixtures; the relevant source passages are available.

This packet does not require a mechanical twelve-phase programme. It does
require a complete selected contract, including REST and evidence, before
calling that selected marriage-election profile done. VED-011 as a wider
purpose-election family can retain other named activities as separate work.

## 12. Research verification receipt

This pass changes only this canonical research document and the remaining
work register. Runtime, tests, protected validation fixtures, dependencies,
version and generated publication outputs are unchanged. The source evidence
was inspected with the project's Python 3.14.3 environment and PDF rendering;
no production election evaluator was executed because none was added.

The private probe passed: twelve source files were rehashed; the legacy
AST contradictions, source-table consistency and rational Abhijit boundaries
were verified; 111 local document links resolved. An in-memory preview
through the owning Git-wiki generator passed for both changed pages,
explicitly including this new untracked page. The preview verifies link
rewriting without changing the generated mirror.

| Executed check | Result |
| --- | --- |
| Private `research_probe.py` | Pass; receipt in `research_probe_receipt.json` |
| `scripts/check_doc_consistency.py` | Pass |
| `scripts/check_release_identity.py` | Pass for 6.9.9 |
| `scripts/generate_hellenistic_inventory.py --check` | Pass; inventories current |
| `scripts/sync_rest_api_reference.py --check` | Pass; route inventory current |
| `git diff --check` and explicit new-page whitespace check | Pass |

All Python checks used the project `.venv`, with UTF-8 output and
`MOIRA_NO_DOWNLOAD=1`. Runtime regression suites were not rerun for this
documentation-only research. This receipt does not inherit the previous
repair package's test count as a new run. Actual generated-wiki synchronization
and its check belong to the later publication preparation; only the in-memory
preview was used here. This research does not stage, commit or push the packet.

### Source fingerprints

The following SHA-256 values identify the inspected PDFs, not a claim that
every page was read. Paths for local-library witnesses are given in section
2; remaining cached paths are in the private source manifest.

| ID | SHA-256 |
| --- | --- |
| MC | `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777` |
| KP | `d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074` |
| VV | `793cc3c454a0c383bb3784886cd19e702d310b67aa39a597748b148da02cdfc0` |
| R | `8ab2c1fc0a4ca0e0f7145434b4c02f8efa97ce48d27fc03732cd632d6a3f9256` |
| BS | `30345203af3be094776ef67f7a9ad2ae8da8392513c72ac7d24a791eb7b19302` |
| PS | `e82c5936775a5d3577433bb88271667ef18580bf449505b5bffa6fd12fa54bdf` |
| MANUAL | `439f877fd4a52f309f67e9e427a912daff7241cfdfb180605e6e6eba9af5b60a` |
| PVR | `2971851a3cda30929cf5b1ec56b88902bd4a141c8d5479599573ddf1c5f78242` |
| UK | `38dac73790e3c21d289bddb4cefcf558e3944b5b0e691bfad037de8c06979386` |
| BPHS1 | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| BPHS2 | `ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45` |
| SS | `2eb5c967bb5363e4e5d3e8c9a0e51fc92855af3b6d023166dcc0526ec25b930b` |
