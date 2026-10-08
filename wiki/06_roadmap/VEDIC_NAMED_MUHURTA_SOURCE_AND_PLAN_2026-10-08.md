# VED-007 named Muhurta: source decision and execution plan

**Date:** 8 October 2026. **Baseline:** engine `acf5851c3b2369a9dd5630921437dc31c7064b4d`, version 6.9.9, wiki `447768124157bc8df4d8be9347506da2d831b98d`.
**Authorization:** proceed with VED-007 after publishing the completed Sayanadi package.
**Scope:** Abhijit and Brahma intervals, explicit source/compatibility policies, engine/facade/public and REST. Other named windows require separate source admission.
**Execution:** all four finite steps below are complete; see the [owning standard](../02_standards/NAMED_MUHURTA_STANDARD.md) and [224-test execution receipt](../03_validation/NAMED_MUHURTA_VALIDATION_2026-10-08.md). This implementation is included in the containing authorized engine/wiki source-publication package; release and deployment are separate.

**Subsequent completion:** the five names left open by this historical two-window
checkpoint are implemented in the [five-name source package](VEDIC_NAMED_MUHURTA_FIVE_SOURCE_AND_PLAN_2026-10-08.md).
Their current status is in register section 27 and the [extension receipt](../03_validation/SPECIAL_MUHURTA_VALIDATION_2026-10-08.md).

## Source collation

| Witness | Identity and inspected scope | Admission consequence |
| --- | --- | --- |
| [Muhurta Chintamani scan](https://archive.org/details/muhurta-chintamani-hindi) | Cover identifies Daivajna Rama, commentary by Pandit Ramlal Avasthi, editor Chandika Prasad Avasthi, Tejkumar Book Depot, Lucknow, tenth edition 2004. PDF pages 135-136, printed 126-127, Vivaha-prakarana vv.52-54 were rendered and visually checked. | The commentary explicitly divides actual daylight by fifteen; Abhijit is the eighth. Verse 54 excludes Abhijit on Wednesday. Preserve the window and report the selected exclusion separately. This is not a complete marriage or universal auspiciousness evaluator. |
| [Ashtanga Hridaya, Sutrasthana 2.1 with commentaries](https://www.wisdomlib.org/hinduism/book/ashtanga-hridaya-samhita-sanskrit/d/doc724713.html) | Digital Sanskrit witness identifies Arunadatta's Sarvangasundara and Hemadri's Ayurvedarasayana. The base verse names rising in Brahma Muhurta; the precise timing is commentarial. | Arunadatta identifies the fourteenth muhurta at equinox and then specifies four ghatis remaining in every season. Admit the fixed two-ghati interval from 96 to 48 minutes before sunrise under that named reading. Hemadri's shorter penultimate-muhurta gloss does not independently resolve seasonal scaling. No medical effect is computed. |
| [B. V. Raman, Muhurtha](https://storage.yandexcloud.net/j108/library/tuwzcd7e/B.V._Raman_-_Muhurtha_%28Electional_Astrology%29.pdf) | Reflowed transcription, PDF 21 and 109 visually checked; edition identity is not established by the transcription. | Corroborates proportional day/night divisions and the daylight midpoint. Its sample 06:10-18:45 is incorrectly described as 12h30m: the true span is 12h35m, midpoint 12:27:30. Use this only as a discrepancy witness, never copy its incorrect numerical expectation. |
| Local `Books by Authors/BV Raman/Scientific-hindu-astrology.pdf` | SHA256 `e82c5936775a5d3577433bb88271667ef18580bf449505b5bffa6fd12fa54bdf`; PDF 20, printed 25, visually checked. Scan begins without an identifying title leaf; folder placement does not establish authorship. | Mentions Brahma before sunrise and Abhijit at the meridian, but supplies no exact interval. It cannot establish either formula or equality of meridian transit and sunrise/sunset midpoint. |
| Local `#Articles/NotesMarkingsonYogisDestinyAndWheelOfTimePart1BW.pdf` | Searchable text describes a particular initiation preference using 48 minutes before sunrise. | Context-specific modern testimony, not proof of a universal Brahma formula. No new executing profile is inferred from it. |

The publisher-listing page used to locate the Chintamani scan misidentifies
its author/edition. The scanned cover controls. The selected downloaded PDF
SHA256 is `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777`;
Raman transcription SHA256 is
`8ab2c1fc0a4ca0e0f7145434b4c02f8efa97ce48d27fc03732cd632d6a3f9256`.
Private scans, page images and manifests are in
`C:/dev/outputs/ved007-named-muhurta-2026-10-08/`; they are not republished in
the engine/wiki. The Ashtanga commentary was accessible through the web
reader; a separate raw-HTML request returned 403 and no local HTML hash is
claimed.

The local corpus pass searched 219 previously extracted text files and
inventoried relevant filenames. The earlier extraction covered 185 PDFs,
22,113 pages, including 6,097 low-text pages; 32 non-PDF conversions were then
pending. This is not a fresh complete OCR of every page and establishes no
whole-corpus absence claim. The directly inspected classical Chintamani
scan was acquired online, not misrepresented as a local-library discovery.

## Engine and route pre-admission decision

The existing `is_abhijit_muhurta` and `is_brahma_muhurta` helpers return only
booleans. Their valid arithmetic is retained. The second computes night
fractions but attributes that computation too broadly to the Ayurveda text;
correct its attribution and expose it as an explicit legacy compatibility
profile. The existing Abhijit comment incorrectly equates the daylight
midpoint with actual meridian transit; correct the wording.

Decision: `admit_after_minor_engine_work`. Add canonical typed intervals and
provenance before transport. One direct request uses supplied UT1 solar
anchors and an explicit weekday. One date request uses a civil date, location,
timezone and the serving reader, with at most three local civil dates of
solar discovery. This bounded read-only calculation is synchronous. The
server projects canonical results and performs no interval arithmetic.

## Finite implementation and acceptance

1. Admit a fixed Abhijit geometry and selectable Wednesday-rule application;
   named Brahma fixed-ghati and legacy night-fraction profiles. Return source,
   status, source anchors, interval endpoints and separate rule eligibility.
   Geometry remains visible when a weekday rule excludes its use.
2. Compose real date/location solar events through existing daily Panchanga
   discovery. Retain numerical root brackets and propagate endpoint bounds.
   Missing/ambiguous roots yield per-window unavailable states; one available
   window must survive failure of an anchor only the other needs. Date
   ownership is the requested sunrise date, including its preceding Brahma
   interval. Do not clip at civil midnight or substitute fixed sunrise times.
3. Curate owning symbols and facade methods; add strict direct/day REST
   requests and typed responses. Reject coercions, unsupported profiles,
   unordered anchors and invalid civil dates before astronomy. Distinguish
   unavailable astronomy from resource/coverage errors.
4. Verify independent rational fixtures, unequal days/nights, half-open
   endpoints, all weekdays, source versus compatibility modes, source
   discrepancy arithmetic, hostile inputs, DST/skipped civil dates, polar
   absence, reader restoration, real DE441 composition and canonical HTTP
   parity. Preserve other Muhurta scoring/search behavior. Update the owning
   standard, reference, register and execution receipt.

Baseline command: project `.venv` pytest over `tests/unit/test_muhurta.py`,
`tests/unit/test_daily_panchanga.py` and
`tests/server/test_server_muhurta_routes.py`, strict known-issue checking and
downloads/network disabled: **103 passed, no failures/errors/skips**
(`baseline.xml`). Baseline is regression evidence, not classical authority.

Godhuli, Vijaya, Amrita, Ravi Yoga, Sarvarthasiddhi, general Durmuhurta,
purpose-specific cancellation, predictive efficacy and website adoption are
outside this two-window implementation. VED-007 retains those separately
recorded source additions after its existing-helper integration closes.

Godhuli, Vijaya, Amrita, Ravi Yoga and Sarvarthasiddhi remain outstanding
parts of VED-007, not completed features. This research packet collated
Abhijit and Brahma; it has not yet resolved the other five into exact
source-selected calculations. Their `SOURCE_RESEARCH` status records work
still to do, not a finding that classical texts are unavailable. Each needs
its relevant definitions, variants, time boundaries and applicable exceptions
reviewed before engine/REST implementation and validation. This is why
VED-007 as a whole remains `BOUNDED_ADMISSION`.
