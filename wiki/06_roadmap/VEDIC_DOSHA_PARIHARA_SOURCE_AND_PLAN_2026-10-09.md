# VED-009: Muhurta dosha and Parihara source record and implementation plan

**Date:** 9 October 2026. **Baseline:** `c33dca1961381665bd08bf61a781ce1c852cb1bf`,
version 6.9.9. The user authorized the next package, including research and
engine/REST implementation. This record separates textual facts, derived clocks,
and explicit exclusions. It does not establish predictive efficacy.

The selected package is now implemented and validated locally. Its
[admission standard](../02_standards/MUHURTA_DOSHA_STANDARD.md) and
[execution receipt](../03_validation/MUHURTA_DOSHA_VALIDATION_2026-10-09.md)
record the final public/REST contract and acceptance evidence. The source
decisions below remain authoritative for that finite scope.

## 1. Scope and decisions

Admit six independently reported restrictions: stellar Vishanadi/Tyajya,
weekday-nakshatra Yamaghanta, daytime Yamaghanta, and nakshatra, tithi and
Lagna Gandanta. Never merge the two Yamaghantas or use a fixed angular width
for a text's temporal Gandanta. The existing legacy Muhurta classification,
Shuddhi findings, Tara/Chandra results, weighted score and search remain intact.

Cancellation profiles are opt-in. Initially admit three precisely bounded
rules: KP's seven-star Tyajya exemption; MC Shubhashubha 37's urgent-work
first-half allowance; and the MC Avasthi commentary's Abhijit exemption for
Gandanta. Each result retains the detected condition, its temporal witnesses,
the named exception, and nullable evidence for every prerequisite. A missing
prerequisite is unknown, never an automatic cancellation. These rules do not
certify a complete election or override an independent source's prohibition.

## 2. Witnesses actually examined

PDF page numbers are one-based file pages, not printed pages. Private scans,
extractions and page renders are retained at
`C:/dev/outputs/ved009-research-2026-10-09/`; `source_manifest.json` pins hashes.
Public repository content consists of analysis and independently transcribed
factual tables, not copies of the source books.

| ID | Witness | Locus and use |
| --- | --- | --- |
| MC | Daivajna Rama, *Muhurta Chintamani*, Hindi commentary by Pandit Ramlal Avasthi, edited by Chandika Prasad Avasthi; Tejkumar Book Depot, tenth edition 2004. [Archive scan](https://archive.org/details/muhurta-chintamani-hindi). | Shubhashubha 9: PDF 15 / printed 6; 37: PDF 26-27 / printed 17-18. Vivaha 43: PDF 130-131 / printed 121-122; 49-51: PDF 133-135 / printed 124-126. Scanned Sanskrit, anvaya, tables and commentary control the admission. |
| KP | *Kalaprakasika*, Sanskrit and English translation by N. P. Subramania Iyer, Asian Educational Services 1982. [Scan](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf). | Chapter XXXIII, PDF 222-223 / printed 185-186: stellar, weekday, tithi and sign Tyajya; chapter XXXIV, PDF 232-233 / printed 195-196: exceptions. PDF 49 / printed 12 supplies a distinct Gandanta description in the birth discussion. |
| BP | *Brihat Parashara Hora Shastra*, R. Santhanam, volume II, local `Classics books/BPHS-Santhanam-Vol-2.pdf`. | Chapter 92.1-4, PDF 536-537 / printed 1026-1027. Direct local scan provides one independent named Gandanta-width alternative. The precise printing is identified by hash; no unverified publication date is assigned. |
| R | B. V. Raman, *Muhurtha*, online reflowed transcription, edition not established. [File](https://storage.yandexcloud.net/j108/library/tuwzcd7e/B.V._Raman_-_Muhurtha_%28Electional_Astrology%29.pdf). | PDF 12, 21-23: variant Tyajya values, angular Gandanta and neutralization claims. The transcription is not used to override the inspected MC/KP tables. |

| ID | SHA-256 |
| --- | --- |
| MC | `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777` |
| KP | `d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074` |
| BP | `ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45` |
| R | `8ab2c1fc0a4ca0e0f7145434b4c02f8efa97ce48d27fc03732cd632d6a3f9256` |

The local library was searched by filename and the existing extraction cache
for Gandanta/Gandantha, Tyajya/Thyajyam, Vishanadi and Yamaghanta variants.
BPHS chapter 92 is substantive local evidence. Its chapter 92.1 explicitly
mentions travel and auspicious functions as well as birth. Ritual remedies
in later verses are not computable astronomical cancellations. A search miss
in an image-only page is not evidence that a classical rule is absent.

Online corroboration includes the [MC page 131 transcription](https://bharatkosha.org/hi/granth/muhurta-chintamani-daivajna-rama-hindi/131),
the [MC page 134 scan/transcription](https://bharatkosha.org/hi/granth/muhurta-chintamani-daivajna-rama-hindi/134),
[Ernst Wilhelm's author-published yoga tables](https://www.vedic-astrology.net/Articles/Muhurta-Yogas.pdf),
and [Drik Panchang's own Tyajya table](https://www.drikpanchang.com/tutorials/panchang-utilities/nakshatra-thyajyam.html).
The latter confirms the naming and 27-star context, not a classical edition.
Its Mula start-time column is inconsistent with its stated ghati/degree columns;
do not use that column as an external numerical oracle. BharatKosha's page
metadata names a different commentator: edition identity here comes from the
inspected PDF front matter recorded in the earlier source packets.

## 3. Vishanadi: table and clock are separate policies

Each offset is elapsed nominal ghatis from the start, not a one-based ordinal.
The following table was transcribed from MC Vivaha 49-51 and KP printed 185.

| Nakshatra | MC offset | KP offset |
| --- | ---: | ---: |
| Ashwini | 50 | 50 |
| Bharani | 24 | 24 |
| Krittika | 30 | 30 |
| Rohini | 40 | 40 |
| Mrigashira | 14 | 14 |
| Ardra | 21 | 21 |
| Punarvasu | 30 | 30 |
| Pushya | 20 | 20 |
| Ashlesha | 32 | 32 |
| Magha | 30 | 30 |
| Purva Phalguni | 20 | 20 |
| Uttara Phalguni | 18 | 18 |
| Hasta | 21 | 21 |
| Chitra | 20 | 20 |
| Swati | 14 | 14 |
| Vishakha | 14 | 14 |
| Anuradha | 10 | 10 |
| Jyeshtha | 14 | 14 |
| Mula | 56 | 20 |
| Purva Ashadha | 24 | 24 |
| Uttara Ashadha | 20 | 20 |
| Shravana | 10 | 10 |
| Dhanishtha | 10 | 10 |
| Shatabhisha | 18 | 18 |
| Purva Bhadrapada | 16 | 6 |
| Uttara Bhadrapada | 24 | 24 |
| Revati | 30 | 30 |

KP's footnote attributes a second Mula interval at 56 to some astrologers.
Expose the printed single-Mula and footnoted dual-Mula tables separately.
Neither permits silently replacing KP's printed Purva Bhadrapada 6 with MC's 16.

For full nakshatra interval `[A,B)`, duration D, and offset q:

- `mc_avasthi_scaled_start_fixed_width.v1`: start `A + q*D/60`, end start plus
  four fixed ghatis (96 minutes). This follows the inspected commentary's
  wording and worked Rohini example. It is the initial default clock.
- `normalized_nakshatra_sixtieths.v1`: start `A + q*D/60`, end
  `A + (q+4)*D/60`. This is the explicitly named proportional reading of the
  nominal sixty-part system. Do not attribute the scaled width to Avasthi's
  worked example, which continues to say four ghatis after scaling the offset.

The three table profiles and two clocks are independent selections. Applying
one of these clocks to KP's table is an explicit Moira composition; KP's terse
table alone does not resolve the clock. Raw windows retain the parent star and
may cross its end under the fixed-width clock. Such carryover must not disappear
when the current nakshatra changes. Direct inputs need enough preceding parent
context to distinguish absence from missing carryover evidence.

MC's example: Rohini duration 56 ghatis 18 palas; start after 37 ghatis 32 palas.
The fixed-width result lasts four ghatis; proportional width is 3 ghatis 45.2
palas. Test both independently. These clocks coincide for a 60-ghati star and
diverge for a nonuniform-duration event.

## 4. Two Yamaghantas

MC Shubhashubha 9 gives Sunday-first star numbers **10,16,6,19,3,4,13**:
Magha, Vishakha, Ardra, Mula, Krittika, Rohini, Hasta. This is a conjunction
of weekday and current nakshatra, with actual ingress/egress transitions;
the source emphasizes journeys. It is not a daily Yamaganda time slot.

MC Shubhashubha 37 and the commentary/table on printed 17-18 give the
Sunday-first daytime slice ordinals **10,8,6,4,2,14,12** in a **sixteen-part
daylight**. The formula is twice the inclusive count from the weekday to
Thursday. For ordinal n and sunrise R, sunset S, the interval is
`[R+(n-1)(S-R)/16, R+n(S-R)/16)`. The commentary expressly uses one sixteenth,
and says the fault does not operate at night. Do not substitute the familiar
eight-part Yamaganda or the fifteen-part named-Muhurta clock.

The necessary-work allowance says to reject the latter half: when explicitly
selected and necessary work is affirmatively supplied, only the first temporal
half of this detected daytime window is neutralized. It does not cancel the
separate weekday-star Yamaghanta. Missing necessity evidence stays unknown.

## 5. Gandanta widths and units

| Profile | Nakshatra at water/fire joins | Tithi Purna/Nanda joins | Lagna water/fire joins |
| --- | --- | --- | --- |
| MC Vivaha 43 | last/first 2 ghatis | last/first 1 ghati | last/first 0.5 ghati |
| BPHS Santhanam II 92.2-4 | last/first 2 ghatis | last/first 2 ghatis | last/first 0.5 ghati |

Nakshatra joins are Ashlesha/Magha, Jyeshtha/Mula, Revati/Ashwini. Tithi joins
occur at every fifth tithi, including both full/new-moon transitions; Lagna
joins are Cancer/Leo, Scorpio/Sagittarius, Pisces/Aries. The initial temporal
interpretation uses one fixed ghati = 24 minutes. It is stated in policy and
applied to solved events, not estimated from linear longitude progress.
The limited first/last portion belongs to its parent event; clip a width that
would exceed an exceptionally short parent, retaining the raw window too.

KP's birth discussion gives last Navamsas/first Navamsas for sign Gandanta and
only terminal tithi ghatis. Raman's reflow gives another angular rule and a
damaged-looking nakshatra sentence. Record these distinct readings; do not
quietly merge them into the two admitted temporal profiles. Abhukta Mula is
also distinct from ordinary Gandanta and is excluded from this initial family.

The Abhijit cancellation is specifically **Avasthi's commentary** on MC 43,
not part of that Sanskrit verse. Reuse the geometrical eighth of fifteen
daylight Muhurtas `[R+7(S-R)/15, R+8(S-R)/15)`. Its scope is the MC Gandanta
findings. It neither cancels BPHS-profile findings nor changes the separate
Wednesday restriction in the existing named-Abhijit product. Geometry and
independent eligibility claims remain different facts.

## 6. KP exemption and exclusions

KP printed 195 explicitly exempts Ardra, Shravana, Mrigashira, Swati,
Uttara Ashadha, Rohini and Anuradha from Tyajya. Preserve the raw table-derived
window, and annotate it with this optional exception. Apply it only to a KP
table, using the witness's parent star even during carryover. It does not
erase MC's independently sourced restriction.

Other KP remedies depend on benefic aspects, dignity, strength, Navamsa or
ambiguous conjunctive prose. Those require the separately registered VED-010
composition policy. MC's broader auspicious-yoga/noon claims, weekday/tithi/sign
Tyajya, regional restrictions, ritual performance and the remaining 21-dosha
catalogue are explicit exclusions, not silently inferred neutralizations.
This finite package does not claim that the underlying classical material is
unavailable or that every Muhurta restriction has been implemented.

## 7. Engineering and acceptance

1. Canonical immutable policy, full-parent spans, independent findings and
   named prerequisite evidence; catalogue, direct assessment and reader-bound
   sunrise-day composition. Reuse existing boundary brackets and bounded
   circular-root discovery, with explicit fail-closed component availability.
2. Strict public/facade/REST parity: `/v1/muhurta/doshas/catalogue`, `/direct`,
   `/day`. Validate input types, solar ordering, span indices/continuity,
   finite numeric values, source profiles and civil dates before resource work.
3. Fixtures transcribed independently from the inspected scans: all star rows,
   both weekday tables, both tithi widths, all three exemptions, rational
   source examples and disagreement cases. Test every boundary and nullable
   prerequisite, midnight/sunrise ownership, carryover, merged uncertainty,
   DST, polar limitations and both server reader configurations.
4. Add class docstrings and exact approved API snapshot entries in the same
   package. Run relevant regression slices and all Release Hardening groups,
   regenerate affected REST/wiki/publication artifacts, and record skips and
   resource identity separately. No release/version or website work is implied.
