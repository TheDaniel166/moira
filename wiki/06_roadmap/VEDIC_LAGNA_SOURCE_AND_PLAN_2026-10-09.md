# VED-010: Muhurta Lagna, strength and Navamsa source record

**Date:** 9 October 2026. **Baseline:** engine `571788a1fe705b096d5a69911f30be583c7c45d7`,
wiki `ed68937510e6ce162da82420b4f42415c0480161`, version 6.9.9.
The user authorized publishing VED-009 and then implementing VED-010.
VED-011 complete purpose elections remain a separate package.

## 1. Source witnesses and reproducibility

Private scans, rendered pages, source manifest and execution receipts are in
`C:/dev/outputs/ved010-research-2026-10-09/`. Books are not redistributed.
Public fixtures contain independently transcribed factual tables and worked
examples, with derived test cases distinguished from printed examples.

| Witness | Inspected locus | Role |
| --- | --- | --- |
| Daivajna Rama, *Muhurta Chintamani*, Ramlal Avasthi Hindi commentary, Chandika Prasad Avasthi editor, Tejkumar Book Depot, tenth edition 2004; [primary scan](https://archive.org/details/muhurta-chintamani-hindi) | Nakshatra 44, printed 46 / PDF 55; Vivaha 75-78, printed 140-143 / PDF 149-152; 84-92, printed 145-148 / PDF 154-157 | Governing purpose, quarter-aspect, Navamsa, placement-score and selected exception rules; Sanskrit, anvaya and commentary visually inspected. |
| *Brihat Parashara Hora Shastra*, R. Santhanam I; local `C:/dev/ASTROLOGY-BOOKS-DATABASE/Classics books/BPHS-Santhanam-Vol-1.pdf` | 3.11, printed 27-28 / PDF 26-27; 3.55 table, printed 40 / PDF39; 6.12, printed72 / PDF71; dignity discussion printed39 / PDF38 | Explicit nature interpretation, complete directional natural-relationship table and D9 partition authority. Printing identified by hash; no unverified date assigned. |
| N.P. Subramania Iyer, *Kalaprakasika*, AES1982; [primary scan](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf) | Printed195-199 / PDF232-236 | Collation of stronger/broader exceptions. Distinguishes rising-sign Tyajya from the stellar Tyajya admitted by VED-009. |
| B.V. Raman, *Bhava and Graha Balas*, 1996; local `Books by Authors/BV Raman/Bhava and Graha Balas 1996.pdf` | Printed109 / PDF114, minimum-strength table, visually inspected | Independent threshold witness. It prints Sun 300 shashtiamsas, unlike the current canonical Shadbala owner's 390. This is a recorded discrepancy, not silently substituted into Muhurta. |
| B.V. Raman, *Muhurtha*, online reflowed transcription; [file](https://storage.yandexcloud.net/j108/library/tuwzcd7e/B.V._Raman_-_Muhurtha_%28Electional_Astrology%29.pdf) | PDF21-23 | Corroboration and differing language about sixth Venus/eighth Mars; edition not established, so it does not override the inspected MC verse88. |

Online discovery also examined the BharatKosha transcription of MC's Vivaha
passages. Its chapter navigation/metadata does not control edition attribution;
the locally inspected scan does. No secondary software is runtime authority.
The local database search found the BPHS and Balas witnesses; absence of an
additional matching filename does not establish absence of classical support.

| Witness | SHA-256 |
| --- | --- |
| MC | `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777` |
| BPHS I | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| KP | `d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074` |
| Balas1996 | `727c8063f64816a0c1c7f6bc577c249629854e980bf860bf4cfd8de16ec9bab2` |
| Raman transcription | `8ab2c1fc0a4ca0e0f7145434b4c02f8efa97ce48d27fc03732cd632d6a3f9256` |

## 2. Finite purpose profiles

`mc_nakshatra_44.v1` evaluates four independent requirements: empty eighth and
twelfth houses; election Lagna in3/6/10/11 from either supplied natal Moon or
natal Lagna; benefic occupancy/aspect of Lagna; Moon in3/6/10/11 from Lagna.
Missing references remain unknown. Every house is a whole sign counted from
the sidereal rising sign. This is a general Lagna component, not all auspicious
undertaking requirements.

`mc_vivaha_75_78_84_88_92.v1` evaluates the finite marriage components below.
The general profile allows Moon in the sixth while the marriage placement
profile restricts it. These source-specific rules are therefore not merged.
Neither profile declares an entire activity suitable.

## 3. Navamsa and aspect choices

MC 84 lists Sagittarius, Libra, Virgo and Gemini; Pisces is optional in the
verse, while Avasthi reports an older rejection. Both readings are named:
`mc_avasthi_vivaha_84_four.v1` (default) and
`mc_vivaha_84_optional_pisces.v1`. MC 85 separately excludes the ninth Navamsa
unless vargottama, and the combination of movable Lagna/movable Navamsa with
Moon in Libra or Capricorn. The Aries/Sagittarius and Taurus/Virgo last-segment
examples are printed examples; the Gemini/Gemini exception fixture is derived.

MC 75 assigns all planets quarter aspects to3/10, half to5/9, three-quarter
to4/8 and full to7, with Saturn3/10, Jupiter5/9 and Mars4/8 full. Any positive
share counts in the selected support tests. MC 76's printed Mercury and Jupiter
examples explicitly use partial aspects. D1 planet positions are compared to
D1 and D9 **sign labels**; D9 planetary positions are not substituted.

MC 76 permits the D9 lord to occupy or aspect either target. MC 77 permits the
pair of own-target aspects or the pair of cross-target aspects, without adding
occupancy to that verse. Both apply separately to Lagna and seventh targets.
MC 78 uses an aspecting benefic who is a friend of the corresponding D9 lord.
The declared direction is **D9 lord toward the potential supporting planet**,
using BPHS natural friendship rather than temporary/compound friendship.
The general profile explicitly composes MC 44 with this MC 75 aspect convention.
These are named interpretations, not a claim that every aspect school agrees.

The nature convention uses BPHS 3.11's verse: Sun/Mars/Saturn/nodes malefic,
Jupiter/Venus benefic, waxing Moon benefic, Mercury malefic when associated
with a malefic. Operational boundaries are declared: waxing is elongation
`0 < Moon-Sun <=180`; association is the same D1 sign. Santhanam's further
commentary alternatives (waning-Moon benefic association, paired Moon/Mercury,
and Yavana phase-strength regions) are not silently included. Missing Mercury
association evidence remains unknown where it could change the result.

## 4. Lagna Vimshopaka is not Shadbala or Varga Vimshopaka

MC 87 supplies the favorable houses; MC 92 supplies weights:

| Planet | Favorable houses | Weight |
| --- | --- | --- |
| Sun | 3,6,8,11 | 3.5 |
| Moon | 2,3,11 | 5 |
| Mars | 3,6,11 | 1.5 |
| Mercury, Jupiter | 1,2,3,4,5,6,9,10,11 | 2,3 respectively |
| Venus | 1,2,4,5,9,10,11 | 2 |
| Saturn, Rahu, Ketu | 3,6,8,11 | 1.5 each |

These nominal weights sum to 21.5, but the favorable-house set never includes
an opposite pair. The nodes are antipodal, so at most one contributes: the
attainable maximum is 20. Direct inputs reject inconsistent node geometry,
including nearly opposite angles that fall into non-opposite signs. Each
planet's full weight is awarded in its listed houses and zero elsewhere;
missing inputs remain null. The total is null until all nine placements and
Lagna are supplied; known contributions remain visible without renormalizing.

Avasthi's commentary gives less than 5 prohibited,5-10 inauspicious,10-15
middling and 15-20 auspicious. At10 and 15 both adjacent bands are retained.
This avoids inventing a non-overlapping endpoint convention absent from the
wording. These source labels concern this component only.

## 5. Placement restrictions and bounded exceptions

MC 86 is encoded by planet and prohibited house: Saturn 12, Mars 10, Venus 3,
Moon and malefics1; Lagna lord/Venus/Moon 6; Moon/Lagna lord/benefics/Mars 8;
all planets7. Moon 12 is additionally witnessed by88. Role predicates,
position evidence, raw detection and exception evidence remain separate.

Optional `mc_vivaha_88_natural_avasthas_orb.v1` admits:

- Venus 6: enemy sign or debilitated sign.
- Mars 8: enemy sign, debilitated sign or combustion.
- Moon 6/8/12: debilitated sign or debilitated Navamsa.

Enemy means the existing BPHS natural relationship from planet to sign lord.
Mars combustion reuses `moira.avasthas._is_combust`, with the explicit numerical
policy of shortest solar elongation strictly less than 17 degrees. MC 88 says
combust but does not specify this orb; the orb is declared composition policy,
not attributed to its verse. No retrograde-orb variant is relevant for Mars.
A missing Sun is unknown for combustion unless another sufficient exception
is already established. Exceptions are off by default and never delete the
raw restriction. They do not cancel the distinct VED-009 temporal detectors.

The Kartari part of88 needs its own detector and source-treatment of the
commentary ambiguity; it is not inferred from these placement checks. Broad
89-91 remedies, KP's differing dignity/aspect remedies and rising-sign Tyajya
are explicitly excluded. Source availability is established; universal scope
and automatic cross-source application are not.

## 6. Shared-owner corrections justified by this audit

BPHS 6.12's3-degree20-minute divisions require exact rational boundaries.
Floor division by the rounded float `30/9` misassigned exact10/30-degree
inputs to the preceding Navamsa. The shared Varga owner now partitions the
supplied binary angle against rational10/3 using integer ratios. The generic
D9 call, named Navamsa, sign-index accessor, Shadbala parity share and Avastha
D9 helper agree. Tests independently use Fraction at all 109 zodiac endpoints
and both neighboring floats. Other Varga methods are unchanged.

BPHS 3.55's visibly inspected table places Moon among **Venus's enemies**;
the existing table incorrectly placed it among neutrals. Its defining rule
also yields this result: Cancer is tenth from Venus's Libra mulatrikona.
The shared dignity owner is corrected, with all 42 directional relationships
pinned in a source fixture. The reverse Moon-to-Venus relation remains neutral.
This affects dignity in Cancer, compound relations and their existing Varga,
Shadbala, Avastha and yoga consumers. It is disclosed as a compatibility change,
not hidden in a new local copy of the relationship table.

## 7. Shadbala evidence and astronomical composition

A supplied ShadbalaResult must have the same UT1 epoch and named ayanamsa,
all seven planets, finite components, canonical thresholds, consistent
component/grand totals and sufficiency. The result stores immutable per-planet
vessels, preserving the full breakdown. Caller-supplied data is not certified
as ephemeris-derived just because its arithmetic is consistent.

Dated composition uses the serving reader, resolved UT1/TT/TDB, apparent
geocentric true-ecliptic-of-date longitudes, true ayanamsa, true geometric
nodes and canonical house-owner Ascendant. Polar/degenerate Lagna stays
unavailable. Optional Shadbala uses its existing owner with Porphyry houses,
JD weekday, geometric day/night, actual speeds/latitudes and optional explicit
hora lord. No hora contribution is invented when the caller omits it.
This is an instantaneous product; it does not guarantee duration or solve
continuous strength thresholds. The source disagreement in the Raman minimum
strength table is retained; this package does not revise Shadbala's thresholds
or pretend that its sufficiency boolean is a classical Muhurta cancellation.

## 8. Delivery and admission gates

The implementation spans the engine, eleven curated exports, three facade
methods and three strict REST routes. Verification requires source tables,
printed examples, exact/adjacent boundaries, partial truth, opt-in exception
scope, malformed input rejection, canonical serialization, real-reader
lifecycle/HTTP parity, shared-owner regressions and release artifact checks.
See the [standard](../02_standards/MUHURTA_LAGNA_STANDARD.md) and
[execution receipt](../03_validation/MUHURTA_LAGNA_VALIDATION_2026-10-09.md).
This closes the selected VED-010 composition package; complete purpose-policy
coverage remains VED-011, with named exclusions available for subsequent scope.
