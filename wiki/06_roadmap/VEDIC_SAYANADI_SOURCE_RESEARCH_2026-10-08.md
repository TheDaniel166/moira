# VED-002 Sayanadi source research and admission decision

**Status:** Source audit complete for the selected BPHS Navamsa-ordinal profile; subsequent [implementation/public/REST admission is complete locally](../03_validation/SAYANADI_VALIDATION_2026-10-08.md). The unmodified-engine findings and research checkpoint below retain their dated scope.
**Date:** 8 October 2026.
**Baseline:** engine `main`, `77d34158cef7c936fdf6613f9be18ba5e8fad5aa`, Moira 6.9.9; generated wiki `293979c942b4083f59569f58a0e7b0d697bdbe39`.
**Owners:** [remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md), VED-002 with VED-021/022; [implementation plan](VEDIC_SAYANADI_IMPLEMENTATION_PLAN_2026-10-08.md).

## 1. Decision and research scope

Proceed with a named **BPHS within-sign Navamsa-ordinal** calculation profile, based on the collated Santhanam and Sharma translations. Its inputs, integer stages and printed Sun example are established sufficiently to repair and admit the calculation. The existing helper's assertion that Santhanam's substate arithmetic is inconsistent is incorrect. A competing degree-based reading exists and must remain separately identified; it does not prevent admitting the selected profile.

The research combined online sources, direct visual review of classical scans and the user's local books database. Existing extracted texts from the 7 October D60 library audit were searched for Sayanadi/Shayanadi references, followed by targeted page rendering and inspection. This is a finite collation, not a fresh complete OCR/search of every book. The earlier extraction inventory includes 6,097 low-text PDF pages and 32 non-PDF files awaiting conversion. No claim of absence from the whole corpus is justified.

Private working evidence is in `C:/dev/outputs/ved002-sayanadi-research-2026-10-08/`: page images/text, `source_manifest.json`, `runtime_audit.py`, `runtime-audit.json` and `baseline.xml`. Books and screenshots are research inputs, not engine dependencies or material to republish in the generated wiki. The source locators and hashes below allow another reviewer to identify the exact witnesses.

## 2. Source and edition matrix

PDF page numbers below are one-based file pages; printed page numbers are the book's own numbering.

| Witness | Exact locator | What it establishes | Evidence boundary |
| --- | --- | --- | --- |
| BPHS, R. Santhanam, volume 1; local scan with a 1984 preface | `Classics books/BPHS-Santhanam-Vol-1.pdf`; chapter 45, verses 30-39; PDF 453-455, printed 454-456 | Within-sign Navamsa ordinal; nine planet numbers; Moon birth star; birth ghati ordinal; Lagna sign; two-stage substate; printed Sun witness | English translation/commentary and accompanying Sanskrit. Its Hora Ratna commentary requires the separate reconciliation below. |
| BPHS, Girish Chand Sharma, volume 1; 1999 reprint of the 1994 translation | [Identified scan](https://archive.org/details/brihatparasarahorasastrawithenglishtranslationgirishchandsharmavolume1_547_G); cached `C:/dev/outputs/vedic-d60-evidence-pass-2026-10-07/sources/bphs_sharma1.pdf`; chapter 47, verses 30-39; PDF 629-633, printed 623-627 | Independent translation collation: Navamsa ordinal, previous-sunrise Ishtaghati, upward treatment of remaining vighatis, complete name table and planet addends | Chapter numbering differs from Santhanam. A printed clock-conversion factor is ambiguous and is not adopted as a conversion specification. |
| P. V. R. Narasimha Rao, *Vedic Astrology: An Integrated Approach* | `Good books/vedic_astro_textbook.pdf`; section 15.4.4, PDF 204-205, printed 192-193; table 37 | Modern author explanation of the Navamsa ordinal, 24-minute ghati and ordinal rounding, name groups and two-stage substate | Modern corroboration, not an independent ancient text. |
| *Sanketanidhi*, unidentified English translation/retypeset witness | `#Articles/Sanketanidhi.pdf`; Sanketa Five, verses 3-5, PDF 30; Sanketa One, verse 6, PDF 1; [online text lead](https://lakshminarayanlenasia.com/articles/SANKETANIDHI.pdf) | A degree-within-sign multiplier; previous-sunrise clock; ghati/vighati definition | Translation edition is not identified. Fractional-degree treatment and a paired numerical example are not supplied by the inspected passage. Do not blend it into the BPHS profile. |
| *Hora Ratnam*, R. Santhanam translation, online indexed text | [Translation](https://www.scribd.com/document/718093861/Hora-Ratnam-Santhanam); chapter 3, verses 170-177, printed 495-499 | A conflict between Bala Bhadra's degree-based worked example and Santhanam's Navamsa-based commentary | Accessible indexed translation was inspected; a local raster witness was not independently reviewed. Preserve text/commentary ownership. |
| Santhanam-lineage BPHS online republication | [Chapters 34-45](https://sanskritdocuments.org/doc_z_misc_sociology_astrology/horaashaastraEng34-45.html), chapter 45 calculation and Sun example | Accessible corroboration of the local Sun arithmetic and time/name values | Same translation lineage, not a second independent edition. OCR name-table glyphs must not govern the character map. |

SHA-256 identities of the actual PDF inputs:

| Source | SHA-256 |
| --- | --- |
| Santhanam BPHS | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| Sharma BPHS | `3c63c1a22d5fec46624dd0f865e4cf35c2ac63e61b84485622f81b4a8175c3af` |
| Rao textbook | `2971851a3cda30929cf5b1ec56b88902bd4a141c8d5479599573ddf1c5f78242` |
| Sanketanidhi | `24b543008103fc1e80f0bb3eab9eb65097a0db8135c9b2c453af47934f026e74` |

## 3. Five findings that govern the repair

### 3.1 The printed Sun calculation is consistent; the existing test misstates it

Santhanam gives Sun at **7 degrees 12 minutes in Taurus**, Krittika, the third Navamsa within Taurus; birth star Krittika; **30 ghatis 33 vighatis**, taken as ghati ordinal 31; Scorpio Lagna, sign 8; initial **Sa, value 4**.

| Stage | Source-owned value |
| --- | --- |
| Planet star / planet number / Navamsa ordinal | 3 / 1 / 3 |
| Moon star / birth ghati / Lagna sign | 3 / 31 / 8 |
| Main sum | `3 * 1 * 3 + 3 + 31 + 8 = 51` |
| State index | `51 % 12 = 3`, Netrapani |
| Substate stage 1 | `(3 * 3 + 4) % 12 = 1` |
| Substate stage 2 | `(1 + 5) % 3 = 0`, Vicheshta |

The source supplies the Moon's star and Lagna sign, not exact degrees for either. A test may choose representative longitudes inside those cells, but must label them as synthetic coordinates implementing source-specified categories. The Sun longitude itself is given exactly by the printed degree/minute value.

[The current test](../../tests/unit/test_sayanadi.py) uses Sun 38 degrees and syllable value 1, incorrectly labels 1 as Sa, misquotes the vighatis and describes a third Navamsa interval that is actually the ninth. Its final state/substate nevertheless match: name values 1 and 4 produce different first remainders but the same final remainder modulo 3. A final-label assertion therefore hides the source error. The new fixture must assert each intermediate value. Remove the helper's unsupported claim that it corrected a printed arithmetic inconsistency.

### 3.2 Amsa is a real lineage difference

The collated BPHS profile multiplies by the **ordinal 1-9 within the natal sign**. It does not use the D9 sign number, a continuous D9 longitude or the planet's whole-circle degree. The Sanketanidhi witness instead prescribes degree within sign. Those are distinct methods.

In [Hora Ratnam](https://www.scribd.com/document/718093861/Hora-Ratnam-Santhanam), Santhanam's commentary calculates Mars at 14 degrees Aries using Navamsa ordinal 5: `2 * 3 * 5 + 5 + 16 + 6 = 57`, giving Bhojana. The printed Mars passage does not supply a name/substate witness. Bala Bhadra's Sun example instead uses Magha, the seventh **degree** of Leo, Anuradha birth star, ghati 45 and Taurus Lagna: `10 * 1 * 7 + 17 + 45 + 2 = 134`, giving Upavesana; Ha=5 then yields Cheshta. Santhanam's BPHS note calling this Sun example a seventh Navamsa conflicts with that reading. Do not cite it as an independent Navamsa oracle.

**Admission:** implement the collated BPHS Navamsa-ordinal profile. Record the degree-based reading as `source_research`, requiring identified-edition review and fractional-degree/remainder semantics before execution. The selected profile can be completed without pretending to settle every textual lineage.

### 3.3 Birth ghati is sunrise-owned, with explicit ordinal treatment

Santhanam's `20 ghatis 2 vighatis -> 21` and `30 ghatis 33 vighatis -> 31`, Sharma's previous-sunrise explanation, and Rao's 42.5 elapsed ghatis -> ordinal 43 agree. One ghati is 24 minutes; one vighati is 24 seconds. A supplied integer ordinal is not interchangeable with decimal elapsed ghatis or clock hours since midnight.

The integer-input path must say **caller-supplied ghati ordinal**. An elapsed-time or birth-date composition must retain previous-sunrise identity, time basis, elapsed value and rounding policy. Use a ceiling rule for positive elapsed ghatis. The exact-sunrise convention is an explicit Moira boundary decision: select ordinal 1 at zero elapsed, rather than attributing an unspecified endpoint rule to the classical witnesses.

Automatic composition must use the last actual local sunrise at or before birth, including the preceding civil date for pre-sunrise births, and disclose the horizon/refraction policy. A civil midnight, fixed 06:00 sunrise or arbitrarily substituted location is inadmissible. Missing sunrise produces an unavailable result. The elapsed previous-to-next-sunrise interval is not assumed to be exactly 60 fixed ghatis; do not impose an unexplained traditional-looking cap of 60 on that astronomical interval.

### 3.4 Name and planet tables can be made explicit

The Sharma raster table and Rao table 37 agree on these canonical initial sounds:

| Value | Canonical Devanagari initial sounds |
| --- | --- |
| 1 | अ क छ ड ध भ व |
| 2 | इ ख ज ढ न म श |
| 3 | उ ग झ त प य ष |
| 4 | ए घ ट थ फ र स |
| 5 | ओ च ठ द ब ल ह |

Sa (`स`) has value 4 and Ha (`ह`) value 5. The three sibilants have distinct values. Plain English strings such as `sa` or `sha` must not silently choose among them. Admit a strict numeric value 1-5 and an explicit canonical sound selector with a visible table; keep personal-name choice caller-owned. Long vowels, conjuncts, nukta letters and full-name extraction require a separate normalization contract and must not be guessed.

| Body | Main multiplier | Substate addend |
| --- | --- | --- |
| Sun | 1 | 5 |
| Moon | 2 | 2 |
| Mars | 3 | 2 |
| Mercury | 4 | 3 |
| Jupiter | 5 | 5 |
| Venus | 6 | 3 |
| Saturn | 7 | 3 |
| Rahu | 8 | 4 |
| Ketu | 9 | 4 |

Nine-body Sayanadi support does not admit Baladi/dignity or other seven-body avastha systems for nodes. Preserve their domains. The supplied Moon remains mandatory even when the subject is another planet; an unknown subject must not fall back to Sun's number or a generic addend.

### 3.5 There is an actual calculation defect beyond the fixture prose

[The helper](../../moira/avasthas.py) computes a Navamsa ordinal using floating-point floor division by `30 / 9`. At exactly **10 degrees**, `10.0 // (30.0 / 9)` is 2, producing ordinal 3 where the source partition assigns ordinal 4. Replacing it with another unexamined floating-point expression is not a sufficient repair.

An independent private audit used `Fraction.from_float` to classify the actual supplied binary64 value exactly. It covered nine subjects, 108 global Navamsa boundaries, each boundary's lower/base/upper representable values, and all five name values: **14,580 cases; 1,015 current state/substate disagreements**. Moon subject cases independently account for Moon also owning the birth star. This is exact source-formula classification, not external-software agreement or predictive validation.

Other unmodified-engine probes accepted a missing Moon, Pluto, boolean ghati/name values, negative ghati, and name values 0 and 100. Decimal ghati fails later with `TypeError`; NaN fails through incidental conversion. These need deliberate admission errors before arithmetic. The top-level evaluator leaves all seven `sayanadi` slots `None`; public curation and the typed REST response omit the family.

## 4. Exact calculation object to admit

For the selected profile, let `N` be the planet's nakshatra ordinal 1-27, `P` its source multiplier, `V` its within-sign Navamsa ordinal 1-9, `J` the Moon's nakshatra ordinal, `G` the supplied/derived birth-ghati ordinal and `L` the Lagna sign ordinal 1-12.

```text
total = N * P * V + J + G + L
state_remainder = total mod 12
A = 12 if state_remainder == 0 else state_remainder
stage1 = (A * A + name_value) mod 12
stage2 = (stage1 + planet_addend) mod 3
substate = {1: Drishti, 2: Cheshta, 0: Vicheshta}[stage2]
```

All integer inputs and every intermediate result must be inspectable. Freeze a source/policy receipt specifying the selected edition, ordinal partition, time input basis, name input basis and actual node frame where applicable. Alternative readings are source records until implemented and verified; do not expose an enum choice that has no executing policy.

The twelve state names and historical effects remain edition-owned. Existing [effect strings](../../moira/sayanadi_effects.py) are conditional traditional prose, not evaluated conclusions about dignity, houses, lunar phase, health or outcomes. Their source coordinates and unevaluated conditions need auditing before a response labels them as attributed text. No new interpretive scoring or numerical prediction-strength bands are authorized by the arithmetic evidence.

## 5. Verification performed and limits

Runtime: project `.venv`, Python 3.14.3, unmodified Moira 6.9.9 at the baseline above. Downloads disabled; selected pytest slice denied external network and used strict known-issue expiry checking. The known-issue registry was empty.

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_sayanadi.py tests/unit/test_avasthas.py -m "not external_network" -q --tb=short --junitxml=C:/dev/outputs/ved002-sayanadi-research-2026-10-08/baseline.xml
.\.venv\Scripts\python.exe C:/dev/outputs/ved002-sayanadi-research-2026-10-08/runtime_audit.py
```

The selected baseline produced **34 passes, zero failures/errors/skips**. The rational probe intentionally demonstrated the existing 1,015 disagreements; it is a discovery receipt, not a passing implementation gate. No corrected runtime, source-located full effect catalogue, chart/sunrise composition, facade/export admission or HTTP Sayanadi contract has been tested yet. No kernel/native computation was needed for these supplied-position probes. No independent software or predictive-effectiveness claim is made.

**Research exit:** admit the selected BPHS recipe for implementation, defer the degree-based variant with its explicit source questions, and execute the linked four-slice plan. The register remains open for VED-002 until that plan's engine/public/REST acceptance criteria pass.

## 6. Documentation checkpoint

Canonical changes are this source packet, its linked implementation plan and the remaining-work register. The generated wiki was updated only through its owning generator. A narrow publication receipt was appended to `C:/dev/moira-state/GENERAL.md`, preserving that repository's unrelated dirty work and divergence; the state repository was not published.

Project-runtime checks passed: `scripts/check_doc_consistency.py`, `scripts/sync_rest_api_reference.py --check`, `scripts/sync_git_wiki.py --check`, 88 local relative-link targets, 24 unique stable register IDs, and parent/generated-wiki `git diff --check`. XML and JSON receipt checks confirmed the 34-pass baseline and the 14,580/1,015 discovery counts. The Moira change manifest contains only these three canonical pages and generated-wiki changes. No VED-002 engine/tests, protected runtime/REST surfaces, numerical tolerances, dependencies or version changed. These research documents remain local; only the earlier VED-005 package was committed and pushed.
