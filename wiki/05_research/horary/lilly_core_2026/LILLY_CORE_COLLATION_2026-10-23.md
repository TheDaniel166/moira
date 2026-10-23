# Lilly core photograph collation and fixture provenance

Date: 2026-10-23. See [decisions](LILLY_CORE_DECISIONS_2026-10-23.md) and
[machine-readable source/fixture bundle](../../../../tests/fixtures/horary/lilly_core_decisions_2026_10_23.json).

## What was checked

The parent researcher visually inspected the selected passages and both title
photographs. A separate model pass first transcribed p.104 without consulting
runtime tables, then compared an alternate photograph cell by cell. A further
read-only source pass collated the teaching passages. Analysis crops retained
original pixels and stayed outside the repository.

This is model-assisted photograph collation. It is not independent human review,
a critical edition, a complete bibliographic determination of printing states,
or independent corroboration of Lilly's reported outcomes.

The [Wellcome title photograph](https://iiif.wellcomecollection.org/image/b30338724_0013.jp2/full/2000,/0/default.jpg)
and alternate title photograph both visibly print the London1647 imprint.
The edition metadata alone was not used to settle that question. The alternate
source retains the identifier
`bim_early-english-books-1641-1700_christian-astrology-_lilly-william_1647`.
Shared edition identity does not resolve the observed passage variants into
a single authoritative typesetting state.

The bundle records 27 used images: eleven core pages in each witness,
Wellcome context pp.102,105,115, and the two title photographs. Each entry has
the exact requested URL, byte count, SHA-256, source identity, checked printed
page, and local acquisition-cache filename. Source originals remain under
`C:\dev\outputs\lilly-core-decisions-20261023\`; they are not bundled with
the engine. Unused acquisitions and diagnostic images do not become authority
merely because their files exist.

## Locator correction

The alternate scandata and BookReader metadata both label leaf131 as p.104,
but the photographed page actually reads102. The actual p.104 table is
leaf133, labelled106 by that metadata. The corresponding checked leaves for
the selected pages are recorded individually:

| Actual photographed page | Alternate leaf / image suffix | Metadata page label |
|---|---:|---:|
| 104 | 133 | 106 |
| 107 | 136 | 109 |
| 110 | 139 | 112 |
| 111 | 140 | 113 |
| 112 | 141 | 114 |
| 113 | 142 | 115 |
| 114 | 143 | 116 |
| 121 | 150 | 123 |
| 122 | 151 | 124 |
| 125 | 154 | 127 |
| 126 | 155 | 128 |

These are visually checked local mappings, not a global offset formula. The
full BookReader image URI is retained for each. Earlier scratch files named
`eebo_pNNN.jpg` are the rejected metadata-based lookup attempts; corrected
`s02_pNNN_check.jpg` files are the inspected images. The old packet acquired
alternate metadata/OCR but did not claim visual collation of these alternate
pages, so its original inspection receipt is left intact.

## P.104 printed table and apparent added layers

The two photographs agree on all checked Classic7 domicile, exaltation,
sect-triplicity, term, face, detriment and fall readings, including all 60 term
segments and 36 face segments. Taurus's Saturn endpoint26 and the Sagittarius
Venus14/Mercury19 distinction were checked in enlarged comparison crops.
Damaged strokes in one image were compared with the other image and glyphs
within the same table, rather than resolved from engine output.

| Sign | House; raw marker | Exaltation; raw degree | Triplicity day/night | Term rulers and raw terminal degrees |
|---|---|---|---|---|
| Aries | Mars; D | Sun19 | Sun/Jupiter | Jupiter6, Venus14, Mercury21, Mars26, Saturn30 |
| Taurus | Venus; N | Moon3 | Venus/Moon | Venus8, Mercury15, Jupiter22, Saturn26, Mars30 |
| Gemini | Mercury; D | NorthNode3 | Saturn/Mercury | Mercury7, Jupiter14, Venus21, Saturn25, Mars30 |
| Cancer | Moon; N,D | Jupiter15 | Mars/Mars | Mars6, Jupiter13, Mercury20, Venus27, Saturn30 |
| Leo | Sun; N,D | blank | Sun/Jupiter | Saturn6, Mercury13, Venus19, Jupiter25, Mars30 |
| Virgo | Mercury; N | Mercury15 | Venus/Moon | Mercury7, Venus13, Jupiter18, Saturn24, Mars30 |
| Libra | Venus; D | Saturn21 | Saturn/Mercury | Saturn6, Venus11, Jupiter19, Mercury24, Mars30 |
| Scorpio | Mars; N | blank | Mars/Mars | Mars6, Jupiter14, Venus21, Mercury27, Saturn30 |
| Sagittarius | Jupiter; D | SouthNode3 | Sun/Jupiter | Jupiter8, Venus14, Mercury19, Saturn25, Mars30 |
| Capricorn | Saturn; N | Mars28 | Venus/Moon | Venus6, Mercury12, Jupiter19, Mars25, Saturn30 |
| Aquarius | Saturn; D | blank | Saturn/Mercury | Saturn6, Mercury12, Venus20, Jupiter25, Mars30 |
| Pisces | Jupiter; N | Venus27 | Mars/Mars | Venus8, Jupiter14, Mercury20, Mars26, Saturn30 |

The full face, detriment and fall transcription is in the bundle. The raw
terminal numbers above are documentary data; their interval interpretation is
specified separately in DG02.

| Location | Observation | Treatment |
|---|---|---|
| Gemini/Sagittarius exaltations | Both witnesses print the node glyphs and degree3 | Preserve as printed documentary cells, even though the candidate reception scope is Classic7 |
| Gemini/Sagittarius fall | Alternate cells are blank; Wellcome has apparent added opposing-node glyphs | Printed-table fields remain blank; retain the Wellcome marks as an apparent added layer |
| Bottom dignity-magnitude row | Wellcome has apparent added5/4/3/2/1/5/4; alternate lacks that row | Not used as printed authority; scores come from the independently inspected printed p.115 table |
| Alternate lower border | Apparent added column enumeration1-14 | Documentary annotation only |
| Wellcome folio104 | Apparent added folio correction | Retain checked page identity; do not confuse the added number with a secure shared typeset cell |

Annotation attribution is a visual assessment. A complete bibliographic account
of possible corrections or printing-state differences remains open. None of
these apparent additions is allowed to silently populate an operational table.

## Teaching passages: variants and quarantined assertions

| Source location | Wellcome | Alternate photograph | Fixture disposition |
|---|---|---|---|
| P.110 Jupiter half-orb | 4 degrees30 minutes | 4 degrees33 minutes | Preserve both; alternate sum is9:03 although its full-orb statements and claimed total give9:00. The inconsistent assertion is not a positive numeric oracle. |
| P.111 aspectual prohibition | Saturn15Aries | Saturn13Aries | Separate D02 witness cases; retain the same explicitly narrated two-contact prohibition sequence. |
| P.111 refranation station phrase | Aries glyph in approximate tenth/eleventh-degree phrase | NorthNode-shaped glyph at that point | Retain the reading difference; exact station longitude is null. Do not repair it to a chosen sign. |
| P.112 term reception | Venus24Aries; Mars16Gemini | Same planet/coordinate reading | Reciprocal term directions are secure; the intervening mark after Mars does not license replacing the following readable Gemini coordinate. |
| P.113 combustion example | Sun18Aries; Jupiter28Aries, called combust | Same | The10-degree gap conflicts with the nearby8:30 definition in both. Keep the source assertion and contrary arithmetic; do not change either coordinate or the threshold. |
| P.126 reception direction | Source receives translator; both principals receive collector | Same | Preserve role-qualified directed edges; no reversed collector-host substitution. |

Source conflicts remain active data, not skipped tests or silently corrected
goldens. The source-fixture tests verify the contradictions and exclude them
from positive numeric-oracle status.

## Missing-input discipline

- D01's later Jupiter position is supplied, but the later Saturn position is
  not. Six minutes can describe the narrative/advance from the initial
  reference; it cannot prove an actual later separation with a frozen Saturn.
- D02-D06 provide narrated event order and some relative motion descriptions.
  They do not provide numerical rates, exact event times, a complete seven-body
  trace or independently observed outcomes.
- D05's house/triplicity examples omit exact degrees. Their determinate bases
  remain usable while degree-dependent bases may remain unresolved.
- D08 starts with an asserted hour lord. It does not contain the time and
  locality needed to calculate a planetary hour from astronomy.
- D07's interior8-degree and5-minute examples do not decide every exact solar
  threshold endpoint. The requested tranche preserves those source limits and
  the same-sign condition without admitting a full new solar-condition API.

No historical dates, speeds or event timestamps were filled from modern
ephemerides, source-implementation agreement or inference from planet order.
The tests explicitly distinguish source examples from synthetic controls.

## Remaining review

The source fixtures and finite decisions are ready for the next implementation
tranche. Full mechanism epoch/precedence rules, Moon/VOC, symbolic timing,
historical chart reconstruction, bibliographic explanation of witness variants
and independent human source review remain separate admissions. Existing v1
behavior and validation history have not been rewritten to absorb these findings.
