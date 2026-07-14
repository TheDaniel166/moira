# Gauquelin C.U.R.A. Source Inventory

- **Date:** 2026-07-14
- **Status:** Research inventory; no dataset admitted to Moira
- **Scope:** Gauquelin-sector method, historical corpora, validation potential,
  and licensing constraints in the C.U.R.A. archive

## Executive finding

C.U.R.A. preserves two materially different kinds of evidence for Moira:

1. reproductions of Gauquelin-authored introductions and laboratory
   publications, which are historical primary sources for the intended sector
   method; and
2. later C.U.R.A. transcriptions, corrections, and combined database editions,
   which are useful editorial products but are not automatically primary
   astronomical authority.

The reproduced Series A and B introductions support the central computational
shape currently used by Moira: 36 sectors numbered from rising in the direction
of diurnal motion, with the above-horizon and below-horizon arcs each divided
into 18 equal **time** intervals. They do not settle the horizon-event model
(limb, refraction, or adopted altitude), polar/circumpolar policy, modern time
scale conversion, or the exact formulas behind the historical lookup tables.

The archive databases are not open data. C.U.R.A. expressly reserves rights
and prohibits reproduction without written permission. The subscription page
describes a separate professional licence for software integration. Therefore
this inventory records URLs, scope, and prospective validation value only. No
record-level data was copied or added to Moira.

## Evidence classes

| Class | Meaning in this inventory | Permitted evidentiary role |
|---|---|---|
| **P — historical primary** | Gauquelin-authored method prose, volume introductions, or original laboratory publication metadata reproduced by C.U.R.A. | Establishes historical technique intent and identifies further primary sources. |
| **E — editorial archive** | C.U.R.A.-assembled, corrected, normalized, or combined editions of Gauquelin records | Candidate regression corpus after licensing and provenance review; not independent astronomical truth. |
| **O — open reconstruction** | A separately maintained, openly licensed reconstruction that records its source lineage | Candidate input corpus after edition, schema, attribution, and licence review; not a substitute for the original publication or an astronomical oracle. |
| **S — secondary analysis** | Later commentary, criticism, reanalysis, or non-Gauquelin collections | Research context or independent corroboration, with its own authority assessment. |
| **L — bibliographic lead** | A citation or index entry for material not inspected in full | Acquisition target only; no substantive claim should rely on it yet. |

Historical primary authority is product-specific here. It can govern what
Gauquelin meant by a sector, but it does not supersede modern astronomical
authority for rise/set geometry, Earth orientation, time scales, or planetary
positions.

## Access and preservation notes

- The inventory was verified on 2026-07-14 against the legacy C.U.R.A. host at
  `http://cura.free.fr/`. In this environment the HTTP pages were reachable,
  while HTTPS requests timed out.
- Search-engine indexes were used only to discover or corroborate pages that
  were difficult to navigate. A source is marked as an indexed lead when its
  full page was not inspected directly.
- The site is a legacy archive. Future research should preserve retrieval
  dates, page titles, URLs, and checksums of any lawfully acquired files.
- The site's contact page renders `cura2@free.fr` as an image rather than a
  clickable address. Patrice Guinard, the named editor and licensor of the
  2020 edition, died in 2021. No successor or present rights administrator was
  identified on the C.U.R.A. site during this review.
- This inventory does not reproduce database rows, downloadable tables, or
  substantial passages from the source pages.

## Core source inventory

| Source | Class | What it contains | Relevance to Moira | Admission status |
|---|---:|---|---|---|
| [Archives Gauquelin: 149,000 Birth & Death Data](http://cura.free.fr/gauq/17archg.html) | E/P index | Master archive index, series descriptions, stated record totals, and links to original volume introductions and later editions. | Starting point for corpus provenance and volume-level reconciliation. | Metadata only. Database reproduction requires written permission. |
| [Series A introduction](http://cura.free.fr/gauq/11gdcura.html) | P | Gauquelin-authored explanation of professional samples and the 36-sector diurnal method. | Direct historical evidence for numbering, direction, and equal-time division of the two semiarcs. | Method prose may inform doctrine with attribution; data remain restricted. |
| [Series B introduction](http://cura.free.fr/gauq/13gdcura.html) | P | Gauquelin-authored explanation of ordinary-person birth samples and the same sector construction. | Independent primary restatement of the method and important legal-time caveats. | Method prose may inform doctrine with attribution; data remain restricted. |
| [Professional Complete Database, 50th Anniversary Edition](http://cura.free.fr/gauq/202011ggdbintro.html) | E | Patrice Guinard's 2020 combined and corrected professional database edition. It states 22,747 rows and 22,372 distinct persons after duplicates are accounted for. | Potential historical regression corpus and identity-cleaning reference. Corrections mean it must be treated as an editorial edition, not an untouched original. | Not admitted. Requires an appropriate licence, edition capture, checksum, and schema audit. |
| [How to obtain the professional database](http://cura.free.fr/gauq/howtogetggdb.html) | E/licensing | Individual and professional subscription terms; the professional option describes software inclusion and required attribution. | Governs whether Moira may distribute or integrate the curated database. | Obtain written professional permission before acquisition, integration, redistribution, or fixture derivation. |
| [G-letter database preview](http://cura.free.fr/gauq/gletterggdb.html) | E | A limited preview of the combined professional database and an explicit restriction on copying or modification. | Useful only for understanding the edition's surface and licence posture. | Do not copy into tests, fixtures, documentation, or package data. |
| [Series E1 table](http://cura.free.fr/gauq/902gdE1.html) | P/E, indexed lead | Search indexing describes a historical table with 36-sector values for the Moon, Venus, Mars, Jupiter, and Saturn, plus a normalized download. | Candidate case-level comparison after lawful acquisition. Legacy tokens require a schema-specific audit rather than an assumed `01..36` parser. | Not inspected as a complete dataset and not admitted. |
| [LERRCP bibliography and journal contents](http://cura.free.fr/gauq/902gdG.html) | P/L | Publication list for the Gauquelin laboratory and contents of *Astro-Psychological Problems*. | Identifies the missing technical articles and method book needed for deeper derivation. | Bibliographic evidence only until the cited works are acquired and read. |
| [Open Gauquelin Database](https://opengauquelin.org/) ([sources](https://opengauquelin.org/sources), [downloads](https://opengauquelin.org/downloads), [licence/contact](https://opengauquelin.org/about)) | O | Thierry Graff's active reconstruction of historical Gauquelin and related datasets. It documents its lineage, provides downloadable historical CSV files, and publishes the database under CC BY-SA 4.0. It uses C.U.R.A. version 5 material and expressly excludes the closed post-November-2020 version 6 additions. | Viable open input corpus for reproducible stress and provenance testing. It does not grant rights to C.U.R.A. v6 and does not make historical rows an astronomical oracle. | Candidate only. No Open Gauquelin records are committed to Moira by this review. |

## Archive series map

The figures below are the archive's own volume descriptions. They are useful
for reconciliation, not yet validation fixtures.

| Series | Archive-stated scope | Volumes listed by the archive |
|---|---:|---|
| A | 15,909 professional notabilities | A1: 2,088 sports champions; A2: 3,644 scientists and physicians; A3: 3,047 military figures; A4: 1,473 painters and 1,248 musicians; A5: 1,409 actors and 1,003 politicians; A6: 2,027 writers and journalists. |
| B | 24,938 ordinary births on the master archive page | B1: 5,018 Paris births; B2: 4,818 Paris; B3: 3,898 Seine; B4: 3,761 Seine; B5: 3,745 Seine; B6: 3,710 Seine. |
| D | 8,783 new groups | D6: 450 European sports champions; D9a: 623 people convicted of murder; D9b: 4,526 psychiatric patients; D9c: 1,794 people identified as alcoholic; D10: 1,398 successful Americans. |
| E | 18,825 new birth records | E1: 2,154 French physicians, military leaders, and executives; E2a: 8,219 heredity records; E2b: 6,918 heredity records; E3: 1,540 French cultural and political notabilities. |
| E bis | 68,856 previously unpublished heredity records | E2c: 13,105; E2d: 17,131; E2e: 11,370; E2f: 11,242; E2g: 13,404; E2h: 2,612. |
| F | 10,448 miscellaneous or unpublished records | F1: 9,272 birth/death records, mainly Paris infants; F2: 1,180 Resistance and military records. |
| G | 1,241 additional records attributed to Michel Gauquelin's 1955 work | G1: 880 French priests; G2: 361 lesser-known French painters. |

### Count discrepancies to resolve before any corpus use

- The Series A heading states 15,909 records, while its listed category
  subtotals sum to 15,939.
- The Series B master entry states 24,938 records, while its linked
  introduction states 24,940. The listed B1–B6 subtotals sum to 24,950.
- The Series D heading states 8,783 records, while its listed volumes sum to
  8,791.
- The Series E heading states 18,825 records, while its listed volumes sum to
  18,831.
- The Series E bis heading states 68,856 records, while its listed volumes sum
  to 68,864.
- The Series F heading states 10,448 records, while its two listed volumes sum
  to 10,452.
- The professional combined edition distinguishes row count from unique-person
  count because it retains duplicate appearances across source groups.

These discrepancies do not prove defects. They may reflect edition changes,
exclusions, transcription choices, or mistakes. They do mean that a licence
alone is insufficient: Moira would also need an edition-specific reconciliation
record before using the material as a regression corpus.

## Method findings relevant to `moira/gauquelin.py`

The Series A and B introductions provide historical support for the following
interpretation:

1. Construct the body's daily apparent path relative to the local horizon.
2. Use rising and setting to separate the diurnal and nocturnal arcs.
3. Divide each arc into 18 equal intervals of elapsed time, producing 36
   sectors whose clock durations may differ above and below the horizon.
4. Number sectors from the rise event, proceeding in the direction of diurnal
   motion; sector 19 starts at setting.
5. Permit aggregation of the 36 sectors into coarser 18- or 12-sector products
   without redefining the underlying event geometry.

This supports unequal semiarc normalization and a half-open event convention
in which the rise instant begins sector 1 and the set instant begins sector 19.
It does **not** by itself establish:

- which apparent-altitude threshold or limb was used by the historical
  almanacs for rise and set;
- whether atmospheric refraction was included and, if so, under which model;
- how a modern implementation should handle circumpolar or grazing cases;
- the exact historical table interpolation and rounding rules;
- how historical civil-time, daylight-saving, locality, and calendar records
  should be normalized; or
- that recomputing a historical sector with a modern ephemeris must reproduce
  every printed sector code.

The primary introductions say the source rise/set times came from contemporary
French astronomical almanacs, including the Bureau des Longitudes publications
and Flammarion's annual. Those almanacs, and the Gauquelins' 1957 methods book,
must be inspected before assigning a historically faithful horizon policy.

The introductions also describe duplicate computation and independent checking
within the original laboratory. That is useful provenance for the historical
tables, but it is not an external astronomical oracle for Moira.

## Time and metadata risks

The Series B introduction expressly discusses French legal time and
daylight-saving irregularities. It reports that recorded birth times did not
always follow the assumed legal-time rule. Consequently, a future validation
corpus must preserve at least:

- original recorded civil time and stated precision;
- birthplace text, jurisdiction, and resolved coordinates;
- source volume, row identity, edition, and any editorial correction;
- the historical legal-time interpretation and uncertainty;
- the printed historical sector, where licensed; and
- Moira's independently recomputed event times, policy, and sector.

Silently converting a historical birth time with a modern timezone database
would create false precision. Disagreement must first be stratified into source
transcription, civil-time interpretation, location, ephemeris, horizon-event
semantics, and sector-boundary rounding.

## Licensing and provenance boundary

| Proposed use | Current decision |
|---|---|
| Link to archive pages and record bibliographic metadata | Allowed for research documentation with attribution. |
| Use the method introductions to refine a source-derived doctrine | Allowed after precise citation and quotation review. |
| Copy records into repository fixtures, snapshots, package data, or tests | Prohibited without written permission covering that use. |
| Download a database for local analysis | Do not proceed until the user obtains the applicable subscription/licence and supplies its terms. |
| Redistribute a derived or normalized corpus | Do not proceed without explicit written permission covering redistribution and derivative forms. |
| Compare a small, lawfully supplied set of cases | Potentially admissible after provenance, licence, privacy, and fixture review. |

Any future permission record should identify the licensor, named edition,
permitted users, local-analysis rights, fixture/quotation allowance,
redistribution terms, required attribution, modification rights, and whether
derived coordinates or sector results may be published.

## Posthumous licensing decision and open-data fallback

The 2020 C.U.R.A. professional-edition page names Patrice Guinard as editor and
describes a software-integration licence, but neither that page nor the contact
page identifies a successor. Because Guinard died in 2021, the displayed
`cura2@free.fr` address is at most an inquiry route; a reply would have to
identify the respondent's authority to license the named edition. Silence or
continued web availability cannot supply permission.

Moira therefore defers C.U.R.A. version 6 indefinitely unless a current rights
administrator provides written terms. This is not a blocker for the present
Gauquelin implementation.

The Open Gauquelin Database is the practical fallback for future corpus work:

- its project page identifies Thierry Graff as the maintainer and publishes a
  current contact address;
- its licence page states CC BY-SA 4.0 for the data;
- its source ledger separates original LERRCP booklets, C.U.R.A. version 5,
  later corrections, and other historical datasets; and
- its historical download page provides separate A1-A6, D6, D10, E1, and E3
  CSV archives as well as independent skeptic and later-research collections.

A direct inspection of the downloadable Open Gauquelin E1 ISO CSV on
2026-07-14 found identity, civil and UTC time, place, coordinates, timezone,
and occupation fields, but no historical planetary-sector output columns.
That file can exercise Moira's computation across real historical inputs; by
itself it cannot prove agreement with the Gauquelins' printed sector values.
Any committed fixture would also need explicit CC BY-SA attribution and a
repository-level decision about share-alike obligations. No such fixture is
admitted by this note.

## Validation admission plan

If the appropriate licence and source files are obtained, admission should be
staged rather than treating the complete archive as an immediate test oracle:

1. **Freeze the edition.** Record filenames, checksums, retrieval date,
   licence, attribution, and source-series mapping without modifying the source
   files.
2. **Audit the schema.** Catalogue every field and legacy token, distinguish
   missing values from encoded values, and reconcile series totals and
   duplicate identities.
3. **Preserve raw civil evidence.** Keep original time/place strings separate
   from normalized coordinates and UTC interpretations.
4. **Build a stratified research sample.** Include ordinary, professional,
   heredity, boundary-adjacent, high-latitude, duplicate, and corrected cases.
5. **Recompute independently.** Use Moira's declared planetary, rise/set, and
   sector policies. Do not import printed sectors into the computation path.
6. **Classify residuals by stratum.** Separate time-record, location,
   ephemeris, horizon-event, rounding, and edition differences before changing
   implementation.
7. **Admit only bounded evidence.** A historical printed-sector comparison is
   regression/corpus evidence for Gauquelin-method reproduction. Modern
   astronomical validation must use the appropriate primary astronomical
   authorities and independent invariants.

## Priority acquisition list

1. Michel and Françoise Gauquelin, *Méthodes pour étudier la répartition des
   astres dans le mouvement diurne* (Paris, 1957). This is the highest-priority
   missing primary derivation.
2. Paul Hewit, “The Gauquelin Sectors,” *Astro-Psychological Problems* 3(3),
   1985.
3. Françoise Gauquelin, “More Precisions about the Gauquelin Sectors,”
   *Astro-Psychological Problems* 4(1), 1986.
4. Mark Pottenger, “Diurnal Sector Calculations,” *Astro-Psychological
   Problems* 6(2), 1988.
5. The September 1992 issue of *Astro-Psychological Problems*, especially
   Francis Santoni, “The 36 G. Sectors: Program Prepared for Aureas
   Informatique,” p. 32, and Mark Pottenger, “Rise/Set Sector Calculations with
   the CCRS Program,” pp. 33-35. These titles and pages are identified by a
   later transcription and must still be verified from the journal itself.
6. Françoise Gauquelin's 1993 two-part work on birth-time registration
   accuracy.
7. Mark Pottenger's 1995 article on expected Gauquelin-sector frequencies.
8. The relevant editions and explanatory matter of the historical rise/set
   almanacs cited by the Gauquelins.

These are acquisition leads, not yet implementation authorities. Formulae or
summaries on third-party websites should not substitute for the primary texts.

## Current conclusion

C.U.R.A. materially strengthens the historical basis for Moira's 36-sector
interpretation, especially the independent normalization of the above- and
below-horizon time arcs. It does not close the remaining astronomical policy
questions. The next defensible method step is to acquire and read the 1957
methods book and the identified technical articles. C.U.R.A. version 6 is
deferred unless a current rights administrator is identified; openly licensed
Open Gauquelin data may support a separately attributed input corpus, but its
current E1 export does not provide historical sector outputs for direct parity.
