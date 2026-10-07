# Classical-derived D60 source adjudication

Date: 7 October 2026. Owner: `moira.varga`, VED-003.
Decision: admit `classical_derived_linear` as a full-position policy with
explicit Moira derivation. Its classical basis is established at the scopes
below; a directly prescribed classical D60 degree algorithm is not claimed.

This reconciliation supersedes the earlier refusal to admit a derived
classical profile in [the narrower adjudication](D60_EVIDENCE_ADJUDICATION_2026-10-07.md).
That review could not support a collection-wide absence claim. The modern
`pvr_textbook_linear` profile retains its separate authorship and locators.
The [source standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md) governs
the public policy; [validation](../03_validation/D60_CLASSICAL_DERIVED_VALIDATION_2026-10-07.md)
records the implemented and exercised surfaces.

## Reviewed sources and authority roles

All local book paths below are relative to
`C:\dev\ASTROLOGY-BOOKS-DATABASE\Classics books`. All PDF locators are
one-based. Printed and PDF page numbers are distinguished deliberately.

| Source | Reviewed locator | Computational role | Boundary |
| --- | --- | --- | --- |
| BPHS, R. Santhanam, Vol. I | 6.33-41 and commentary; printed 83 / PDF 82 | 60 half-degree subdivisions; destination signs counted forward from the natal sign; even-sign deity reversal | No continuous D60 degrees in that passage |
| Kalyana Varma, Saravali | III.18; local English electronic PDF 8; university Sanskrit transcription | General subdivision coordinate: arcminutes times subdivision count divided by 1800 | Does not prescribe a mapped 0-30 degree D60 longitude or its destination-sign sequence |
| Vaidyanatha Dikshita, Jataka Parijata; translation/notes V. Subramanya Sastri | III.43; printed 139 / PDF 139; publisher describes a reprint of the 1932 edition | Fraction of a D12 subdivision traversed by the Moon corresponds to the same fraction of a later whole sign | Immediate object is a birth-timing technique, not a D60 chart |
| Prasna Marga, translation/notes B. V. Raman | Notes following V.27-28; printed 171-173 / facsimile PDF 200-202 | Explicit continuous Navamsa longitude: multiply natal within-sign degrees by 9 and retain the angular remainder after division by 30 | Formulation is in Raman's NOTES, not the literal Sanskrit stanzas; it concerns D9 |
| Moira derivation, version 1 | This admission, proportional construction below | Extend fractional subdivision progress to a full coordinate inside the separately assigned D60 sign | Derived classical support, not a claimed direct classical D60 degree verse |

The local Saravali electronic English file has no dependable translator/title
attribution. None is guessed. Its underlying Sanskrit arithmetic was checked
against [Central Sanskrit University Lucknow, Saravali chapter 3, verse 18](https://www.csu-lucknow.edu.in/e-books/saravali/p4.html).
That transcription corroborates the arithmetic, not a D60-specific extension.

The Prasna Marga Word extraction was checked against a
[printed facsimile of Raman's Part I](https://storage.yandexcloud.net/j108/library/touvip7g/Panangadu_Nambudhiri_-_Prasna_Marga_%28Part_I%29.pdf).
The Sanskrit stanzas and translation occupy printed 170-171 / PDF 199-200;
the separately headed notes contain the degree arithmetic and examples.
Governing facsimile pages, the Jataka Parijata passage and BPHS page were
visually checked. A converted Word text alone does not establish page layout
or the distinction between stanza and commentary.

## File identity receipts

| File | SHA-256 |
| --- | --- |
| `BPHS-Santhanam-Vol-1.pdf` | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| `Kalyana Varmas Saravali.pdf` | `39c2ba173fa4c9ca019b47aee35eb3d9c19f61e61f5cfea2f54eb50e0d244f58` |
| `Jataka-Parijata-Vol-1.pdf` | `392d1b15e86824f78339ddda0a9c358372f7be69d9f6aeece24d8d0e7c782dc1` |
| `PRASNA MARGA.doc` | `35d6a063e55e91574c136b7ebb40afea81a868cb6a3955eb1f08b837c95838ed` |
| Retrieved Raman Part I facsimile | `484bbce4a10a01bf51ec6891597107ac04208661cabb219821be4369807e0bd6` |

No complete copyrighted text or external implementation is added to runtime
or the public repository. The public record contains bibliographic locators,
identities, factual paraphrases and arithmetic examples. Private research
receipts remain at `C:\dev\outputs\vedic-d60-library-audit-2026-10-07`:
`FINDINGS.md`, inventory, Word extraction manifest, selected renders and online
retrieval receipts.

## Proportional construction and policy

For normalized sidereal longitude `L`, natal sign `s=floor(L/30)`, and
within-sign degrees `d=L-30*s`, Saravali's subdivision coordinate for `N`
parts is:

```text
u = (60*d)*N / 1800 = N*d/30
k = floor(u)
progress = u-k
```

For `N=60`, `u=2*d`. BPHS Santhanam separately selects destination sign
`j=(s+k)%12`. Moira maps the fraction traversed within the subdivision onto
the fraction traversed within that destination sign:

```text
degree = 30*progress = 60*(d-0.5*k)
mapped_longitude = 30*j + degree
```

Saravali supplies the subdivision arithmetic. Jataka Parijata supplies a
classical fractional correspondence in its stated D12 technique. Raman's
notes give explicit full Navamsa degree arithmetic. **Extending this
coordinate interpretation to D60 is the Moira inference.** It is not inferred
from Vimshopaka weights or claimed as a sentence in BPHS, Saravali, Jataka
Parijata or Prasna Marga that prescribes D60 degrees.

Both natal parities count signs forward. Only the selected deity sequence
reverses in even natal signs. Each interval is half-open: its start maps to
zero, its excluded end belongs to the next subdivision, including natal-sign
and zodiac wraps. Finite direct numbers normalize circularly; coercion and
unknown/inapplicable selectors fail explicitly. Representable left limits
stay in their selected sign when longitude addition rounds to the next sign.
The existing source-profile numerical handling is shared, not copied from a
comparator or replaced with global harmonic sign assignment.

The two full source profiles intentionally have equal coordinates under this
declared forward/proportional policy. The modern profile has a different
admitted authority chain. No frame, ayanamsa, ephemeris or default is changed.

## Published examples and errata

| Example | Source evidence | Use in validation |
| --- | --- | --- |
| Capricorn 13 degrees 25 minutes -> Pisces | Santhanam 6.33 commentary publishes the destination sign | Source sign witness; 25 degrees inside Pisces is independently derived, not published there |
| Sun at Cancer 24 degrees 25 minutes -> Aquarius 9 degrees 45 minutes in D9 | Raman's notes publish both input and full Navamsa coordinate | Primary commentarial degree example; exact rational arithmetic and existing Navamsa path agree |
| Moon at Taurus 25 degrees 11 minutes -> Leo 16 degrees 39 minutes in D9 | Raman's notes publish both input and full Navamsa coordinate | Second primary commentarial example under a different natal/sign condition |

Raman's Gulika example starts from 12 degrees 44 minutes, but a later line
prints 12 degrees 40 minutes while retaining the product 114 degrees 36
minutes. The product agrees with 12 degrees 44 minutes. Preserve that erratum;
the inconsistent line is not an independent numerical oracle.

These D9 examples support the stated commentarial degree construction. They
do not become published D60 examples by changing a label. The D60 coordinate
construction is checked independently using rational arithmetic and the
existing frozen secondary-engine corpus. Software agreement supports the
declared mapping; it does not manufacture historical attribution.

## Search coverage and admission boundary

The wider inventory contains 220 files: 185 PDFs, 32 legacy Word documents and
three HTML/text files. Embedded text was extracted from 22,113 PDF pages;
16,016 met the conservative 80-alphanumeric-character threshold and 6,097
did not. Low-text pages are individually recorded and are not searched
negatives. All 32 Word documents decoded successfully. Automated triage
produced 870 candidate PDF pages; manual review concentrated on the strongest
relevant passages, rather than reading every candidate line by line.
Nineteen selected page images were OCRed for retrieval/title verification.
Governing passages above were visually checked. Image-only Deva Keralam and
Brihat Jataka facsimiles were not completely OCRed; no exhaustive absence
claim is made. The `Deva-keralam.pdf` title page identifies Book II.

The finite admission task is complete: the classical-derived policy supplies
full degrees with precise provenance and tested behavior. A direct classical
D60 degree prescription and an exact primary-published planetary D1/full-D60
pair remain unclaimed evidence frontiers. They do not block this derived
policy or imply unfinished computational validation. Predictive validity and
current PVR Jagannatha Hora equivalence are also outside this admission.
