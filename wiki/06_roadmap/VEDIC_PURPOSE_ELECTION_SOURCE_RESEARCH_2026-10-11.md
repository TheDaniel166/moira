# VED-011: construction, travel, business and additional marriage research

**Status:** Research and proposed admission decisions, 11 October 2026.
This packet supports the [implementation plan](VEDIC_PURPOSE_ELECTION_IMPLEMENTATION_PLAN_2026-10-11.md).
It does not admit new runtime profiles or extend an existing completion claim.
**Baseline:** engine `c0c1d739c9cdf52910ff2f64aea6ac0ad88e347f`, generated wiki
`7ad434a903555679a2393afd7487138bb9d3634c`, version 6.9.9; both checkouts
were clean when research began. Both marriage performance passes are published.
**Scope:** source-defined election timing in Moira and its REST API. Website,
Urania, compatibility matching and architectural design are separate work.

## 1. Findings and recommended decisions

There is enough source material to plan substantive implementations in all
four areas. The obstacle is not a general absence of classical texts. The
important work is defining each action, selecting a particular edition and
keeping its rules, exceptions and computational interpretations together.

| Area | Recommended first deliverable | Consequential finding |
| --- | --- | --- |
| Construction / Vastu | MC Maniprabha 1948 foundation commencement and house-entry timing, with distinct first-entry, return and extraordinary-entry scopes | Chapters 12 and 13 are present in complete scans. Foundation, entry, door placement and site layout are different objects. The foundation Vrisha chakra has 28 positions; the entry Kalasha chakra has 27. |
| Travel | MC Maniprabha 1948 ordinary departure timing; separately named KP directional/time components | Direction, departure anchor, personal context and exception scope matter. MC 11.112 imports wedding restrictions, requiring an explicit dependency inventory. KP contains a printed directional contradiction. |
| Business | MC Avasthi 2004 purchase, sale and `vipani` trading-operation profiles | Purchase and sale have different preferred stars. Shop/trading activity is not automatically company incorporation, contract execution or borrowing. |
| Additional marriage traditions | VV Vasantalakshmi ordinary astronomical timing, then a separately collated KP ordinary profile | Existing VV-derived Godhuli geometry does not implement ordinary VV marriage. VV calendar precedence and non-cancellable Jamitra differ from a generic application of MC remedies. |

These are proposed finite profiles, not claims that every rule in every book
has been settled. Section 7 names the remaining interpretation decisions and
the evidence needed to settle each one before its affected profile is admitted.

## 2. Corpus, source identity and inspection method

The search covered `C:\dev\ASTROLOGY-BOOKS-DATABASE`, the existing VED-007/011
research downloads, public scans and an online Sanskrit transcription.
Twelve PDFs were fingerprinted: six in the user's library, four previously
downloaded online witnesses and two complete MC scans acquired in this pass.
Relevant passages were extracted by PDF page and selected scans were rendered
and visually read. OCR was used for navigation, never to settle a disputed
reading without looking at the page. This is targeted chapter research, not
a claim to have read every page of all twelve books.

PDF page numbers below are **one-based file pages**. Printed page numbers
are supplied where verified; they are not interchangeable across editions.
The Sanskrit and English portions of one KP edition are two readings of the
same witness, not independent corroborating authorities.

| ID | Witness and provenance | Inspected scope and admission use |
| --- | --- | --- |
| MC04 | Rama Daivajna, *Muhurta Chintamani*, Avasthi Hindi edition, Tejkumar, 2004; [catalogue](https://archive.org/details/muhurta-chintamani-hindi); prior download `outputs/ved007-named-muhurta-2026-10-08/chintamani.pdf`, 207 PDF pages | Existing marriage authority; Nakshatra 2.16–17, printed 33–34 / PDF 42–43, for commerce. **The file is incomplete:** it stops in Yatra around verses 83–85, printed 198 / PDF 207. It cannot establish the book's final travel, Vastu or entry rules. |
| MC48 | Rama Daivajna, *Muhurtachintamani*, Kapileshvara Shastri's Maniprabha Hindi commentary, Haridas Sanskrit Series 135, Chowkhamba, Banaras, **1948**; [catalogue](https://archive.org/details/fclt-muhurta-chintamani-maniprabha-by-ramadaivagya-edit), 372 pages | Title and imprint visually verified at PDF 5–6. Complete travel, Vastu and entry chapters; Vastu 12.13–19 at PDF 348–353; entry 13.1–7 at PDF 359–366, printed 341–348. Recommended new edition owner. |
| MC-F | Complete Avasthi-attributed scan, [catalogue](https://archive.org/details/vpvq-muhurta-chintamani-chandrika-prasad-awasthi), 242 pages | Travel conclusion and Vastu at PDF 218 onward; entry PDF 236–239. Useful collation witness. Its edition/date has **not** been established; do not silently substitute its fingerprint for MC04 or label it 2004. |
| MC-D | [E-Bharati Sampat Sanskrit transcription](https://www.ebharatisampat.in/read_chapter.php?bookid=MjQwNjAyMzE4NTQyMDYy) | Chapters 11–13 include 112, 29 and 7 numbered verses respectively. Used to locate passages, checked against scans. Typographic/numbering faults prevent treating this as a critical edition or sole table authority. |
| KP | *Kalaprakasika*, N. P. Subramania Iyer translation, introductory date January 1917, Asian Educational Services 1982 reprint; [scan](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf), 490 pages | Marriage XIV, PDF 116–124; transactions XXI, PDF 146–150; foundation XXV, PDF 156–167; entry XXVI, PDF 167–168; travel XXIX, PDF 176–195. Printed contradictions documented below. |
| VV | Keshava/Keshavarka, *Vivaha Vrindavana*, Sitarama Jha's Vasantalakshmi Sanskrit/Hindi commentary, Master Khelari Lal & Sons, Benares; cover Samvat 1991, [archive record dated 1935](https://archive.org/details/in.ernet.dli.2015.329463), 138 pages | Chapters 1, 4–6, 8–13 and their contents; visual checks include PDF 45, 54, 56, 88, 106–107. Ordinary timing is a separate undertaking from the admitted Godhuli composition. |
| BS | Varahamihira, *Brihat Samhita*, Sastri/Bhat 1946, local `Classics books/brihatsamhita.pdf`, 1,105 image pages | Chapter 53 building architecture, including printed 421 / PDF 440 and printed 439–440 / PDF 458–459; earlier marriage research covers this edition's chapter 103. Architecture is not by itself a complete election algorithm. Attribution and chapter numbering remain edition-specific. |
| PVR | P. V. R. Narasimha Rao, *Vedic Astrology: An Integrated Approach*, first published 2000, distributed with a 2010 update; local `Good books/vedic_astro_textbook.pdf` and [author's PDF](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf), 515 pages | Chapter 36, printed 472–475 / PDF 484–487, supplies modern guidelines and distinguishes the event's actual commencement. Table 79 is explicitly guidance. Qualitative strength descriptions do not establish numerical thresholds. |
| R | B. V. Raman, *Muhurtha*, [reflowed online transcription](https://storage.yandexcloud.net/j108/library/tuwzcd7e/B.V._Raman_-_Muhurtha_%28Electional_Astrology%29.pdf), 110 pages | Commerce PDF 68–70, housing 73–82, travel 90–93 and earlier marriage passages. Useful variant lead, but the printed edition behind this transcription is unidentified. No new edition-owned Raman profile is admitted from it. |
| VASTU | Local `#Articles/SaralVastuShastra-Hindi.pdf`, 96 pages | Visual checks at PDF 88–90: election tables and entry categories. Author/date not established; a printed planetary-placement sentence conflicts with the primary witnesses. A discovery aid, not primary rule authority. |
| PS / MANUAL / UK | Local P. S. Sastri *Text Book of Scientific Hindu Astrology*, Raman *A Manual of Hindu Astrology* and *Uttara Kalamrita* | Bibliographic/search leads. PS is filed in the Raman directory, but the folder does not establish authorship. These files were fingerprinted; no new purpose-specific production rule is inferred from their mere presence. |

The six library files remain in the user's database. The other PDFs are
research downloads outside that database. That distinction matters when
describing what the local collection itself establishes.

### 2.1 Reproduction and fingerprints

Research files are in
`C:\dev\outputs\ved011-four-area-research-2026-10-11`:
`source_manifest.json`, `additional_manifest.json`, page-indexed JSON,
`mc-digital.html`, `mc-digital.txt` and rendered page PNGs. The manifests retain
absolute source paths and the two new download URLs. Earlier online scans
remain in their original research directories; they were rehashed here.

| ID | SHA-256 of PDF |
| --- | --- |
| MC04 | `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777` |
| MC48 | `d972964e36fff6311c2fe1be91b0be0943f58f49108451d5e18d7fef05140bde` |
| MC-F | `b82ca8a3d78c49669f92ff75af81ebfef4e9309f7be3889540c87c11e8f769a0` |
| KP | `d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074` |
| VV | `793cc3c454a0c383bb3784886cd19e702d310b67aa39a597748b148da02cdfc0` |
| BS | `30345203af3be094776ef67f7a9ad2ae8da8392513c72ac7d24a791eb7b19302` |
| PVR | `2971851a3cda30929cf5b1ec56b88902bd4a141c8d5479599573ddf1c5f78242` |
| R | `8ab2c1fc0a4ca0e0f7145434b4c02f8efa97ce48d27fc03732cd632d6a3f9256` |
| VASTU | `cf8db53fa0ec518095019f8aa9530af890adf18549623d2a3041c55749419f55` |
| PS | `e82c5936775a5d3577433bb88271667ef18580bf449505b5bffa6fd12fa54bdf` |
| MANUAL | `439f877fd4a52f309f67e9e427a912daff7241cfdfb180605e6e6eba9af5b60a` |
| UK | `38dac73790e3c21d289bddb4cefcf558e3944b5b0e691bfad037de8c06979386` |

## 3. Construction and Vastu

### 3.1 Separate the actions before assigning rules

At least five distinct objects appear: foundation commencement, first entry
into a new dwelling, return to an existing dwelling, entry after damage or
under extraordinary circumstances, and door installation. Site selection,
building dimensions, deity grids and water placement are additional Vastu
subjects. They must not be represented by a single `construction=true` switch.

MC48 13 begins by distinguishing first entry, return from travel and entry
into an old house. Its second verse permits additional months/stars and
relaxes planetary-availability consideration for specified old-house and
extraordinary-entry circumstances. This is **not** a universal waiver for
every newly built house. Context must be explicit, not inferred from a date.

### 3.2 Timing inventory

| ID | Source locus | Computational object and required distinction |
| --- | --- | --- |
| C01 | MC48 12.13–14, PDF 348–349 | Vrisha/Vastu chakra: inclusive Sun-star to Moon-star count; body segments `3,4,4,3,4,3,4,3`, totaling **28**. The summarized disposition is first 7 adverse, next 11 favorable, last 10 adverse. Own the 28-star identity/partition explicitly. |
| C02 | MC48 12.15–16, PDF 349–351 | Solar-sign, building-facing and lunar-month prescriptions with particular structure exceptions. Calendar mode and precedence cannot be replaced by a generic favorable-month list. |
| C03 | MC48 12.17–18, PDF 351–352 | Facing-specific tithi restrictions; commencement weekday, tithi, movable Lagna, Panchaka and planet-house requirements. Freeze the commentary's complete exclusions, including its Pratipada/Ashtami treatment. |
| C04 | MC48 12.19, PDF 353 | Purpose-specific excavation-sector rule associated with Rahu. Its symbolic sector is a different object from the physical azimuth of the lunar node. |
| C05 | MC48 12.29, PDF 358–359 | Door-placement chakra: `4,8,8,3,4` totals **27**, with alternating favorable/adverse groups. A separate action, not an automatic foundation filter. |
| H01 | MC48 13.1, PDF 359 | First-entry calendar, fixed Lagna, natal-relative support and facing-sensitive star selection. Recommended initial ordinary scope is residential entry. |
| H02 | MC48 13.2, PDF 359–360 | Old-house/extraordinary-entry additions and availability relaxation. Preserve the underlying finding, the qualifying context and the exact waived targets. |
| H03 | MC48 13.3–4, PDF 360–361 | Vastu worship has its own star prescription. Entry has Lagna/planet-house, natal eighth, weekday/tithi/month and personal qualification rules; worship and entry need separate anchors. |
| H04 | MC48 13.5, PDF 363–364 | Vama Ravi and facing-specific tithi classes; use the declared front-door direction and election Lagna. |
| H05 | MC48 13.6, PDF 364–365 | Kalasha chakra: inclusive count in **27** stars; groups `1,4,4,4,4,4,3,3`. Preserve individual group meanings and the favorable/adverse assessment separately. |
| H06 | MC48 13.7, PDF 365–366 | Ritual preparations and honors. Record as non-computational scope; an ephemeris cannot verify their performance. |

For H04, the Sun's favorable whole-sign houses from the election Lagna are:

| Door faces | Sun houses | Tithi class |
| --- | --- | --- |
| East | 8, 9, 10, 11, 12 | Purna: 5, 10, 15 |
| South | 5, 6, 7, 8, 9 | Nanda: 1, 6, 11 |
| West | 2, 3, 4, 5, 6 | Bhadra: 2, 7, 12 |
| North | 11, 12, 1, 2, 3 | Jaya: 3, 8, 13 |

The separate Amavasya prohibition still applies; class membership cannot
erase paksha-specific restrictions. H05's favorable inclusive counts are
6–13 and 22–27. The remaining groups retain their adverse finding rather
than being absorbed into a favorable aggregate score.

### 3.3 Variants and printed conflicts

KP foundation, printed 120 / PDF 157, puts **Chitra in both its best and
middling lists**. The same page calls Taurus through Virgo “six signs”,
although the inclusive sequence contains five. These are visible on the
printed page, not merely OCR errors. Neither a set union nor a guessed end
sign is an acceptable silent correction. MC48 can own the first implementation
while KP remains an explicitly unresolved alternative at these loci.

The local PVR chapter gives different construction/entry star and tithi
guidelines and distinguishes relevant divisional-chart significators.
It does not turn an unspecified “strong” planet into a chosen Shadbala cutoff.
BS chapter 53 supplies architectural doctrine, not proof of a complete
first-entry date filter. The anonymous VASTU compilation is weaker evidence
than either source and contains its own placement inconsistency.

## 4. Travel

### 4.1 Define what starts, where and in which direction

The proposed ordinary profile elects an explicitly declared departure act.
MC 11.93 discusses more than one meaning of departure; leaving a room,
leaving a residence and crossing a settlement boundary are not equivalent
timestamps. A return leg is a separate action. An earlier symbolic departure
requires a recorded actual act and its applicable validity rule; the engine
must not invent one retrospectively to rescue an unfavorable time.

MC's chapter contains royal/military, enemy-related, omen and ordinary travel
material. Extract an ordinary astronomical manifest with an explicit exclusion
ledger. Do not apply royal victory rules indiscriminately to modern travel.
Direction must be supplied under a named cardinal/intercardinal convention;
it cannot be guessed from a destination name or silently equated with a
great-circle initial bearing.

### 4.2 Rule families and dependencies

| ID | Source | Required treatment |
| --- | --- | --- |
| T01 | MC 11.1 onward; KP XXIX, PDF 176–179 | Travel-specific stars, tithis, weekdays, Lagna/planet placements and general temporal prohibitions. Do not import the marriage star list. |
| T02 | MC 11.10; KP printed 143 and 148 / PDF 180 and 185 | Directional star, weekday and tithi restrictions are separate detectors. MC's four main star/weekday combinations are tabulated below. |
| T03 | KP printed 148 / PDF 185 | Weekday direction restriction expires only after the named number of ghatis from sunrise. An exact edge and sunrise availability are required. |
| T04 | KP printed 140 / PDF 177 | Star-specific early portions to avoid. These are not interchangeable with the existing Vishanadi/Varjyam table. |
| T05 | KP printed 145–147 / PDF 182–184 | Yogini directions, including vertical categories, and the traveller's zodiac/time divisions. Do not collapse sky/earth into eight compass directions or substitute variable daylight eighths for an explicitly fixed clock. |
| T06 | KP printed 150–152 / PDF 187–189 | Three modular tests, Sun-to-Moon star count and shifted Panchakam. Preserve one-based ordinals and each denominator/offset. |
| T07 | MC travel; KP printed 153–156 / PDF 190–193 | Venus-facing, distance, special-person and necessity exceptions. Each exception targets its own restriction; it is not general permission to cancel every dosha. |
| T08 | MC 11.80–81, 93, 108–109 | Short/return journeys and departure definitions require context-specific scoping. Read the actor and purpose before generalizing a royal rule to commuting. |
| T09 | MC 11.110–112; complete scan MC-F PDF 218 | Closing prohibitions include marriage-defined doshas. Enumerate the import set, edition and travel qualifications rather than calling the entire current marriage assessment. |
| T10 | R PDF 92–93 | Modern ordinary, pilgrimage and business travel distinctions. Mercury retrograde is explicitly favorable in the business-travel passage, unlike KP's general retrograde avoidance; retain as an edition-unlocked variant lead. |

MC 11.10's main directional combinations:

| Direction | Star restriction | Weekday restriction |
| --- | --- | --- |
| East | Jyeshtha | Monday, Saturday |
| South | Purva Bhadrapada | Thursday |
| West | Rohini | Sunday, Friday |
| North | Uttara Phalguni | Tuesday, Wednesday |

KP PDF 185 removes the corresponding weekday restriction **beyond** 8, 22,
15 and 12 ghatis after sunrise respectively. A named fixed-24-minute-ghati
composition would make these 192, 528, 360 and 288 minutes. That clock choice
must be visible; “after sunrise” is not after civil midnight. The word
“beyond” also needs explicit exact-edge ownership and uncertainty handling.

KP's worked example at printed 151 / PDF 188 uses Friday=6, Pushya=8 and
Panchami=5. Its three remainders are `(2*5)%6=4`, `(3*6)%8=2`,
`(4*8)%6=2`. The following Panchakam uses shifts **15,12,10,8,4**, each
tested modulo 9 against remainder 5. It is not a license to reuse a similarly
named generic Panchaka formula with different constants.

### 4.3 Conflict and exception handling

KP printed 143 / PDF 180 assigns Jyeshtha/Shravana to **westward** travel
and also assigns Rohini/Pushya westward. The duplicate is visible in the
scan; MC's East/Jyeshtha rule does not authorize silently editing KP. Collate
KP's Sanskrit locus or another identified printing before admitting that table.

Distance exceptions use historical krosa/yojana definitions. If admitted,
retain source units or an explicit versioned conversion, not an unexplained
kilometre threshold. Traveller status and extraordinary circumstances are
declared context. Weather/omen observations cannot be manufactured from
planetary longitudes. Emergency travel must not require finding a favorable
window before it can proceed; the product reports the selected tradition's
conditions rather than directing emergency conduct.

## 5. Business and transactions

### 5.1 Source-supported distinctions

MC04 Nakshatra **2.16–17**, printed 33–34 / PDF 42–43, explicitly distinguishes
buyer and seller. Its commentary even discusses why an actual exchange cannot
satisfy opposing preferred times simultaneously. This is direct evidence
against a universal transaction score which quietly combines both roles.

| ID | Action | Source prescription / interpretation boundary |
| --- | --- | --- |
| B01 | Purchase | Six preferred stars: Revati, Shatabhisha, Ashwini, Swati, Shravana, Chitra. Define whether the selected act is acceptance/exchange; do not silently substitute payment settlement. |
| B02 | Sale | Seven preferred stars: Purva Phalguni, Purva Ashadha, Purva Bhadrapada, Vishakha, Krittika, Ashlesha, Bharani. Additional Lagna/planet placement clauses belong to the sale prescription. |
| B03 | Vipani / trading operation | Mridu, Dhruva and Kshipra groups, expanded by the commentary to eleven named stars; exclusions include Rikta, Tuesday and Aquarius Lagna. The commentary requires Moon **and** Venus in Lagna, not either one. Malefic eighth/twelfth and benefic placement clauses need explicit quantifiers. |
| B04 | Lending / borrowing | MC04 2.27, printed 38–39 / PDF 47–48, and R PDF 69 distinguish financial roles. A later finite profile must preserve the lender/borrower distinction. It does not follow automatically from B01/B02. |
| B05 | Commodity / employment activities | Neighboring MC passages distinguish animals, goods and service entry. These are independent extensions, not synonyms for incorporation or starting any business. |

B03's eleven stars are Chitra, Anuradha, Mrigashira, Revati, Rohini,
Uttara Phalguni, Uttara Ashadha, Uttara Bhadrapada, Ashwini, Pushya and Hasta.
Do not add Abhijit because another source puts it in a similarly named group.
The purchase and sale preferred sets are disjoint. A multi-party response
should preserve each role's assessment and any conflict; an average score
would conceal the central source distinction.

`Vipani` supports a trading/shop activity. Mapping it to the first opening
for trade is a reasonable **declared modern anchor composition**, not evidence
that the verse prescribes a modern incorporation filing, electronic signature
or stock-market opening. The first API should expose the narrower anchor.

KP XXI provides another transaction classification; its table is not proof
that MC's buyer/seller distinction should be removed. A Raman business profile
needs an identified printed edition before the reflowed transcription can own
production rules. No source result establishes a financial-return guarantee.

## 6. Additional marriage traditions

The [earlier marriage research](VEDIC_MARRIAGE_ELECTION_SOURCE_RESEARCH_2026-10-10.md)
established many disagreements; this pass rechecked the proposed expansion
against VV and KP rather than treating them as aliases of the implemented MC
profile. Existing MC and Godhuli behavior remains its own accepted contract.

| ID | Tradition and locus | Difference with implementation consequences |
| --- | --- | --- |
| M01 | VV 1, star purification | Ordinary VV requires its own star/vedha qualifications, not just the existing Godhuli interval. |
| M02 | VV 4, Navamsa; PDF 43–50 | Argument and qualifications around admissible Navamsas must be reduced to the author's concluded rule, preserving competing opinions as provenance. Do not treat every quoted opinion as simultaneously operative. |
| M03 | VV 5.7–9, PDF 54–55 | Kartari/Jamitra and Jupiter/Venus appearance or disappearance intervals. Reuse event computation only after matching the actual visibility definition and waiting-period semantics. |
| M04 | VV 6.1–2, printed 43 / PDF 56 | Explicit argument for considering the groom's Moon as well. A one-partner shortcut must not count as a full personal assessment. |
| M05 | VV 8–9, PDF 71–86 | Shadvarga, boundaries and Godhuli context. Already implemented temporal geometry is reusable evidence only for its own component. |
| M06 | VV 10.1–4, printed 73–75 / PDF 86–88 | Lunar-month precedence: Phalguna with Pisces Sun and Vaisakha with Aries Sun are discussed as admissible; Chaitra remains rejected under either. This cannot be represented by reusing MC's allowed solar-sign set. |
| M07 | VV 11–13, especially 13.12–13, printed 94 / PDF 107 | The defined full Jamitra and the following argument against its cancellation require a protected restriction in VV's remedy graph. Broad MC favorable-factor remedies cannot erase it. |
| M08 | KP XIV, printed 79–80 / PDF 116–117 | Best versus middling tithis, dark-half restrictions, graded ayana, Lagna choices and distinct post-appearance waiting periods. Preserve preference versus prohibition. |
| M09 | KP XIV planet-house section | Its favorable eighth-house Mars testimony conflicts with MC/BS adverse treatment. Store testimony separately from complete-profile eligibility; a favorable row alone is not a global waiver. |
| M10 | KP XIV, PDF 122–124 | Additional temporal/stellar restrictions, first-born context and broad favorable-factor statements. General phrases need finite target sets and explicit strength definitions. |
| M11 | BS chapter 103 in the 1946 edition | Valuable wedding/Godhuli testimony, with edition-specific attribution. It does not by itself settle every requirement of a standalone comprehensive profile. |
| M12 | PVR chapter 36; R marriage passages | Modern guidance and an edition-unlocked transcription respectively. They remain distinct from a source-complete classical ordinary profile. |
| M13 | VV 17, PDF 127–133, including printed 118 / PDF 131 | Lagna purification recapitulates timing restrictions and includes historical practical Sun/rising-time arithmetic. Separate astrological rule intent from the numerical substrate; the sign-rate approximation is not a replacement for Moira's admitted ephemeris. |

VV chapter 3 compatibility, bodily/character descriptions, horary marriage
questions, historical age/social prescriptions and family ritual scheduling
are not part of the proposed astronomical timing contract. Their exclusion
must be visible in the catalogue, not silently presented as “all VV”.
Likewise, a modern strength guideline is not classical authority for an
invented numeric threshold. No new profile may borrow a remedy merely because
it has the same human-readable dosha name as a rule in another tradition.

## 7. Admission decisions and bounded unresolved questions

These are specific source or modelling decisions, not a request to stop the
entire programme. The first implementation package closes them for each
selected profile and records the accepted interpretation before coding it.

| Decision | Evidence now available | Required closure / recommended disposition |
| --- | --- | --- |
| D01: complete MC edition | MC48 title, imprint and complete final chapters; MC-F collation | Use MC48 for new housing/travel. Preserve MC04 marriage/business identity. Never silently repair the old source fingerprint. |
| D02: 28-star foundation identity | MC48's 28-position table is clear; ordinal table alone does not specify longitude boundaries | Bind a separately named astronomical 28-star partition with documented provenance and fixtures, or obtain the edition's explicit definition. Label any computational composition; do not convert 28 to 27. |
| D03: MC48 scope and cross-references | Complete chapters now available | Produce verse-by-verse coverage for 12–13 and ordinary portions of 11, including the 11.112 marriage import closure. Reconcile general versus specific calendar and placement clauses; name ayana and amanta/purnimanta semantics instead of inheriting marriage defaults. |
| D04: personal/context vocabulary | Entry natal-relative conditions and travel role/anchor distinctions are explicit | Define the required person, natal frame, front-door direction, actual action and exception facts. Qualitative personal predicates need a named interpretation, not an arbitrary compatibility rule. |
| D05: KP printed conflicts | Chitra best/middling duplication; five-versus-six sign range; duplicate westward direction, visually confirmed | Collate Sanskrit or a second printing. If unresolved, keep the affected KP table unavailable; MC alternatives remain independently implementable. Do not majority-vote across unrelated traditions. |
| D06: clock, ordinal and distance conventions | KP worked arithmetic and sunrise offsets are concrete | Lock fixed/proportional ghati, one-based counts, strict/inclusive boundary and unit conversions per rule. Existing similarly named functions require formula comparison before reuse. |
| D07: commerce semantics | MC04 2.16–17 and commentary explicit | Freeze buyer/seller roles, the meaning of `vipani`, AND/OR and placement quantifiers; enumerate general restrictions imported by “good tithi”. |
| D08: VV ordinary profile | Direct Sanskrit/commentarial discussion and contrasting calendar/remedy passages | Collate complete selected timing loci, including chapter 17 Lagna purification; distinguish concluded doctrine from rebutted alternatives. Freeze non-cancellable rules and personal coverage. |
| D09: KP ordinary marriage | Printed chapter and general cross-references available | Resolve broad prohibitions versus graded preferences, event definitions, remedies and ambiguity at temporal “ends”; admit an explicitly bounded timing manifest, not the entire social chapter. |
| D10: Raman edition identity | Reflowed text has useful leads but no verified printed edition | Acquire and fingerprint an identified printing before a named Raman runtime profile. This is a specific source-acquisition task, not evidence that Raman's works are unavailable. |

Recommended first admission set: MC48 housing; MC04 purchase/sale/vipani;
MC48 ordinary travel; VV ordinary marriage and, after its own closure, KP
ordinary marriage. KP travel components can be added individually where
their source contract is closed; they do not imply a complete KP travel
profile. Door installation, lending/borrowing, commodity-specific commerce,
full Vastu design and additional modern lineages are explicitly subsequent
extensions, with no blanket claim that researching these four areas implements
every possible election.

## 8. Engine implications confirmed against current code

Current marriage has a finite source manifest, named remedy targets, strict
policy/evidence vessels, direct assessment, reader-derived instant assessment
and certified bounded windows. Public curation is in `moira/vedic.py` and
`moira/facade.py`; REST owns transport under `moira_server/`, not doctrine.
The policy currently admits one ordinary MC profile, so adding a new profile
requires genuine source dispatch and contract fixtures, not another enum alias.

`moira/_bounded_memo.py` already provides exact immutable bounded reuse.
The marriage frame, history, enclosure and certification modules contain
potentially reusable numerical work, but are attached to marriage dependency
selection. A new family must request its own necessary astronomy and history;
it must not inherit every expensive marriage computation by default.

`moira/muhurta.py` still contains coarse house/travel activity guidance.
Those lists are not admitted complete elections. `moira/muhurta_search.py`
is a separate sampled search contract. Neither establishes continuous
source-complete windows for the proposed profiles. The implementation plan
therefore keeps categorical restrictions, preferences, source coverage and
certification distinct from generic scoring.

## 9. Research verification and limits

The research uses the project Python 3.14.3 environment for extraction and
arithmetic. `research_probe.py` in the output directory independently checks
the manually transcribed source arithmetic: three chakra totals and their
complete cyclic mappings, Vama Ravi wraparound, transaction-role sets, KP's
worked modular example and weekday release offsets. Its JSON receipt binds
all twelve PDF hashes and the digital text hash. These are transcription and
arithmetic checks, **not engine validation or an independent astronomical oracle**.

The probe passed **3,563 assertions**, verified all twelve PDF hashes/page
counts and retained hash receipts for 21 visually inspected page images.
The representative command is:

```powershell
$env:PYTHONUTF8='1'
$env:MOIRA_NO_DOWNLOAD='1'
.\.venv\Scripts\python.exe C:\dev\outputs\ved011-four-area-research-2026-10-11\research_probe.py
```

No chart, release artifact, runtime policy, frozen fixture or production API
has been changed by this research. New source profiles still require the
implementation plan's source manifest, boundary certification, engine/REST
parity and actual real-resource acceptance. The work register remains open
for those implementations; research completion does not change feature counts.

Documentation verification passed `check_doc_consistency.py`,
`check_release_identity.py`, `generate_hellenistic_inventory.py --check` and
`sync_rest_api_reference.py --check`, all through the project interpreter.
`verify_and_sync_docs.py` in the output directory checks 118 relative file/anchor
links and invokes the owning `sync_git_wiki.py` generator with the two new,
untracked pages explicitly included. It verifies the generated result without
changing the Git index. Both repositories pass `git diff --check`. This
pre-publication preview does not stage, commit or push the documents.
