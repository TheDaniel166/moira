# VED-001 and VED-003: Chara cycles and D60 source research

**Status:** Research checkpoint and proposed implementation scope; no runtime admission in this pass.

Later checkpoints: [sign/cycle implementation](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
and [wider full-position review](D60_FULL_POSITION_SOURCE_RESEARCH_2026-10-07.md).
The decisions below retain this earlier research pass's evidence boundary.
**Date:** 7 October 2026.
**Baseline:** engine `main`, `67b66de14cde0447730b0c9b57e5e14c1edd9935`, Moira 6.9.9, project Python 3.14.3.
**Owning work items:** [VED-001 and VED-003](VEDIC_REMAINING_WORK_REGISTER.md); source/validation/documentation follow-through belongs to VED-021/022 for this package. Engine and REST ownership precede website/Urania adoption.

## 1. Research decision

Proceed toward a bounded integration of the existing Chara formulation and canonical Varga result. The proposed Chara surface admits one or two cycles, with the existing first-cycle default, explicit repetition/year/co-lord metadata and strict inputs. Two is a product admission bound supported by a published second-cycle example; it is not a claim that every tradition forbids later cycles.

D60 deity transport is a real omission. The source review also found four substantive name discrepancies and a separate numerical placement disagreement. Transport preservation, name corrections and selection of a D60 sign-placement convention are independently reviewable changes. Shipping the existing value faithfully does not establish that every current string or placement is source-correct.

The research does **not** establish a universal Chara algorithm, a fully collated Rao book edition, the complete source authority for every existing co-lord tie-break, or an interpretation of D60 as a validated predictive product. Alternative lineages and the placement question remain explicit research boundaries.

## 2. Current implementation and observed behavior

### Chara

The [engine](../../moira/jaimini_extended.py) already accepts `cycles=1` and repeats the same twelve sign/year/lord results for a second cycle. With the synthetic longitude map from `test_jaimini_extended.py`, one cycle returns 12 periods totaling 84 years; two return 24 totaling 168. This is a runtime witness, not a source chart or independent numerical authority.

The engine currently also accepts `0` and `-1` as empty successful results, accepts boolean cycle values, and permits `3` or arbitrarily large integers. Floats and strings fail incidentally in `range`. The [REST request](../../moira_server/models/vedic_extended.py) has no cycle field, so `cycles=2` is rejected as an extra input and the [route](../../moira_server/routers/vedic_extended.py) computes the default twelve periods. The canonical result/response do not identify selected/computed cycles or the fixed year length.

REST already requires seven classical bodies and strict finite longitude/epoch values. It accepts an empty node map, which silently selects the classical-lord path, and accepts a one-node map at model construction. A one-node map subsequently raises an engine `KeyError`; the generic server handler converts that to HTTP 422. This is a missing explicit preflight contract, **not an observed HTTP 500**. A complete Rahu/Ketu pair succeeds. Engine validation must enforce its own contract rather than depending on REST or a generic exception handler.

The module header still says first cycle only. The result docstring attributes PDF pages 13–14 to *Predicting Through Jaimini's Chara Dasa*. The local pages actually collated in this pass belong to an article compilation. Those two source statements need correction within implementation documentation.

### D60

The [engine's `VargaPoint`](../../moira/varga.py) already has nullable `deity`; the named `shashtiamsha` wrapper supplies it. The [REST response model](../../moira_server/models/varga.py) and [shared serializer](../../moira_server/serializers/varga.py) drop it. ASGI probes confirm the field is absent from named and Shodashvarga JSON.

Generic `calculate_varga(longitude, 60)` returns `deity=None`. It is a distinct generic calculation contract; the server must not infer a deity merely from divisor 60 or a supplied name. Other divisions also retain `None`.

Named D60 divides the input sign into sixty half-degree segments and reverses the deity list for even signs. A 720-midpoint probe covers all twelve signs and confirms the current table-index structure. That check derives from the implementation convention and is not a new source validation of the table contents or D60 sign mapping.

## 3. Sources, identity and limits

All local paths below are relative to `C:\dev\ASTROLOGY-BOOKS-DATABASE`. PDF page numbers are one-based file coordinates; printed page numbers are listed separately where identifiable. Private extractions and rendered pages are research artifacts, not republication inputs.

| ID | Source and coordinates | Authority/use in this pass |
| --- | --- | --- |
| C1 | K.N. Rao, [Chandrasekhar horoscope analysis](https://www.journalofastrology.com/article.php?article_id=315), posted 11 November 2010; embedded article dated June/July 2007. Local `Books by Authors\Jaimini\SP-jaminicharadasaknraoBW1.pdf`, PDF pp. 13–14. Cover identifies *Jaimini's Chara Dasha — My Approach, Part I*. | Primary author's published worked example; online and local versions are republications of one witness, not independent cases. |
| C2 | Yuvraj Singh, *Basics & Calculations*, `#Articles\CharaDashaPart1BW.pdf`, PDF pp. 5–9; author's name verified on the cover. | Lineage teaching summary dedicated to Rao; source for stated sequence/count/co-lord cases and subperiod discussion, not a Rao-authored book or a fully specified tie-break authority. |
| C3 | P.V.R. Narasimha Rao, [*Unlocking the Power of Parasara's Chara Dasa*](https://vedicastrologer.org/articles/pp_chara_dasa.pdf), version 1, 14 April 2014, PDF pp. 3–4. Downloaded from the author's site and visually checked. | Primary modern formulation demonstrating materially different choices. It does not supply a second-cycle rule in the reviewed text. |
| C4 | P.V.R. Narasimha Rao, [*Vedic Astrology: An Integrated Approach*](https://storage.yandexcloud.net/j108/library/rptviqw0/P.V.R._Narasimha_Rao_-_Vedic_Astrology_-_An_Integrated_Approach.pdf), mirrored primary authored text, section 18.2.2, printed p. 204 / PDF p. 212. | The located “12 minus first-cycle duration” rule governs **Narayana Dasa** in that section. Its search-keyword match does not admit it for Rao Chara. The mirror is not an independently checked author distribution. |
| C5 | *Jaimini Sutras*, Bangalore Suryanarain Rao translation, revised/annotated by B.V. Raman; front matter identifies sixth edition, 1984, IBH Prakashana. `Classics books\JaiminiSutrasCompleteEng.pdf`, sutra 1.1.28 and commentary, PDF pp. 52–54. | Historical translated/commented count-to-lord discussion; not a complete specification of the modern engine profile. Commentary and sutra must not be conflated. |
| C6 | *Brihat Parashara Hora Shastra*, R. Santhanam translation, Vol. II, `Classics books\BPHS-Santhanam-Vol-2.pdf`, Chara discussion vv. 155–167, PDF pp. 63–66 / printed pp. 553–556. | Separate translated/commented Chara formulation. Its cycle restart discussion does not identify every modern Rao or PVR convention. |
| D1 | *Brihat Parashara Hora Shastra*, R. Santhanam translation, Vol. I, `Classics books\BPHS-Santhanam-Vol-1.pdf`, chapter 6 vv. 33–41, PDF pp. 81–82 / printed pp. 82–83; commentary table PDF pp. 83–85 / printed pp. 84–86. Preface signed R. Santhanam, Vijaya Dasami 1984. | Visually collated named list, reversal and commentary example. This is a particular translation/commentary, not a critical edition resolving every variant. Complete scan imprint was not established. |
| D2 | [Online BPHS English transcription](https://vedic-astro.s3.amazonaws.com/books/bhrihat_parasara_hora_shastra.pdf), PDF p. 10, vv. 33–41. | Poor transcription with visible substitutions and corrupted names. Used to locate a copying hazard, not to overrule the printed scan or as an independent edition. |
| U1 | `#Articles\Advance Use of Jaimini Char Dasha by KN Rao Sir..pdf`, 13 pages. | Malformed PDF resources; no extracted text and rendering errors. Relevant filename only; no rule admission. |
| U2 | `Books by Authors\Jaimini\A Manual of Jaimini Astrology_Iranganti Rangacharya 2009.pdf`, 89 pages. | Scanned, no text layer; second-cycle passage/edition not collated in this pass. Extraction failure does not mean the book lacks a rule. |
| U3 | `Books by Authors\Jaimini\JaiminisCharaDasasPredictions.pdf`, 7 pages. | Supplementary narrative lead, not the governing second-cycle specification. |

Deepak Bisaria's institutional [Chara Dasha history article](https://www.journalofastrology.com/article.php?article_id=442), 2 April 2013, provides lineage/history context. It is not a substitute for a complete calculation rule or an empirical validation study. No software comparison, tertiary calculator, search snippet or model recollection is admitted as doctrinal authority here.

## 4. Chara: distinguish rule axes and evidence strength

C1 lists Aries 1927–1929 and Taurus 1929–1941 in the first cycle, then Aries 1996–1998 and Taurus 1998–2010 in the second. Their durations repeat: two and twelve years. Applying a generic twelve-minus rule would instead produce ten and zero years, contradicting this example. **Inference:** the witness supports the existing repetition convention for these periods; it does not independently prove the full repeated twelve-sign second cycle for all charts. Dates reported by year do not validate exact Julian-day endpoints.

The strongest safe source claim is therefore “existing Moira repetition policy, supported by Rao's published second-cycle example,” with the evidence limit visible. Replace “proven by book pages 13–14” and blanket “verified” wording. Obtain the actual identified book edition or further author examples before strengthening that claim.

| Rule axis | Current Moira formulation to preserve/explain | Research boundary |
| --- | --- | --- |
| Seed | Input lagna sign. | C3 instead selects among lagna, Moon and Sun using lord strength. That is a separate formulation. |
| Sign sequence | Twelve contiguous signs; direction from the ninth-from-lagna footed group. | C2's direct-lagna set is consistent with this sequence. Do not confuse sequence direction with the separate count-to-lord direction. |
| Duration | Footed-sign count to lord minus one; own sign gives twelve; no exaltation/debilitation adjustment. | C2 supports these cases. Historical commentary and other dasha families are not interchangeable. |
| Sc/Aq lord mode | No nodes uses Mars/Saturn; a complete node pair enables existing co-lord selection. | Make selected mode visible; neither absence nor `{}` should silently imply a newly sourced node doctrine. |
| Co-lord strength | Existing Moira chain: companions, dual > fixed > movable, higher degree. | C2 says stronger without fully defining this chain. C3 uses different modality ordering and a more-years tie-break. The complete existing chain remains a source-collation limit, not universal Rao proof. |
| Second cycle | Existing full repetition of sign/year/lord sequence; proposed maximum two. | C1 is a partial worked witness. C4's complementary-duration rule belongs to Narayana. Third/later cycles are not admitted by this packet. |
| Antardashas | Twelve equal spans in the implemented sequence direction, dasha sign last. | C2 discusses dasha-last sequencing and month/day fractions; the latter does not establish the engine's absolute JD dates. C3 expressly leaves antardashas out. |
| Year/epoch | Fixed `365.25` days per nominal year; supplied numeric Julian-day epoch. | Label this as a fixed Julian year, not a true tropical return or calendar anniversary. C3 recommends true tropical solar years; changing the clock is a separate admission. No timescale conversion occurs in this direct helper. |

Do not add a menu of named schools whose full rules are still uncollated. Metadata may identify the existing formulation and unresolved axes without implying implementations of every cited author.

## 5. D60: transport, names and placement are distinct

D1 confirms sixty equal half-degree deity segments, with reversed name order in even signs. Names repeat within the list; a deity string alone is not a unique segment identity. Retain ordered ordinal identity in fixtures/research and do not deduplicate the table.

Four reviewed strings differ materially from the printed list:

| One-based ordinal | Current engine string | D1 printed reading | Consequence |
| --- | --- | --- | --- |
| 6 | `Kindar` | `Kinnara` | Requires an explicit source-name correction. |
| 37 | `Suddh` | `Sudha` | Different spelling/meaning; do not normalize solely by similarity. |
| 52 | `Dhannayudh` | `Dandayudha` | Corrupted/transcribed name; document the old value if corrected. |
| 59 | `Brahman` | `Bhramana` | Commentary describes wandering; distinguish this entry from ordinal 22, Brahma. |

Other differences include abbreviation/transliteration; this pass does not authorize an indiscriminate rename of all sixty entries. An explicit alias/migration record for changed values is preferable to silently treating historical strings as synonymous. The low-quality D2 transcription carries similar corruptions and is not independent corroboration.

D1's commentary example places Venus at Capricorn 13°25′. Doubling the within-sign degrees, taking the integer modulo twelve and adding one gives the third sign from Capricorn: Pisces. Current Moira returns Gemini for that longitude, because the named wrapper delegates sign placement to its generic harmonic mapping. The deity lookup and reversal are a separate calculation.

**Decision:** record this as a named D60 placement-convention disagreement. Do not silently replace generic Varga arithmetic, alter all named divisions, or claim that deity REST transport settles the printed placement example. A later placement admission must distinguish the verse/commentary interpretation, generic D60 and named D60, specify degree semantics, and audit dependent strength/chart consumers.

## 6. Proposed bounded implementation package

### VED-001

1. Validate strict integer cycles in the engine and REST, allowed values `1` and `2`, default `1`. Reject booleans, coerced strings/floats, zero, negative and larger values before work begins. The maximum is operational/admission policy, not an invented classical lifespan limit.
2. Validate the engine's complete seven-body map, finite numeric input and epoch; reject unknown overwrite keys. Accept absent nodes or a complete finite Rahu/Ketu pair. Reject an explicit empty or partial map with a useful field-specific error, and record the selected classical/co-lord mode. Do not impose an unresearched opposite-node tolerance.
3. Add cycle and clock/policy evidence to the **canonical engine result** and serialize it through REST: requested/computed cycles, period count, repetition policy, fixed year length and selected lord mode. Consider a per-period cycle index only if required to navigate the typed result. Keep field names/compatibility decisions in the implementation contract, not server-only reconstruction.
4. Preserve admitted first-cycle arithmetic and existing second-cycle repetition. Ensure finite, ordered period/subperiod endpoints and reject epochs at which floating-point precision cannot represent the result. Replace stale header and misattributed source wording with the narrower evidence statement in section 4.
5. Preserve root/facade/Vedic identity of the existing callable/vessel. Update OpenAPI and generated REST reference through owning tooling. No new chart/website adapter or alternative-school implementation is included.

Minimum expected implementation files: `moira/jaimini_extended.py`, `moira_server/models/vedic_extended.py`, `moira_server/routers/vedic_extended.py`, their focused tests, and affected canonical standards/reference documentation. Public-export/native counterparts must be checked for actual admission; no new native counterpart is assumed from the technique name.

### VED-003

1. Add nullable `deity` to `VargaPointResponse` and copy `point.deity` in the shared serializer. Preserve it for every response containing that vessel. Generic and unenriched results must carry `null`, even for divisor 60.
2. Verify all eight placement routes: `/v1/varga/generic`, `/named`, `/shodashvarga`, `/named/batch`, `/shodashvarga/batch`, `/chart/named`, `/chart/shodashvarga`, `/chart/shodashvarga/batch`. Batch keys, chart provenance and canonical placement must survive unchanged. Vimshopaka is a different result vessel and is not counted as a ninth placement route.
3. Treat the four source-name corrections as an explicit companion change with their own compatibility receipt and independent edition fixtures. Keep them reviewable apart from transport. Do not implement a new named/generic D60 placement algorithm as an incidental fix.

Minimum transport files: `moira_server/models/varga.py`, `moira_server/serializers/varga.py`, focused server tests and canonical API documentation. Name reconciliation additionally touches `moira/varga.py` and source-owned unit fixtures. The existing `VargaPoint` already has the field; no server-owned deity table is needed.

These prospective changes implicate protected canonical result/default/REST contracts and validation evidence. Declare their exact final scope before runtime edits. This research pass changes only this document and the work register; no tests, tables, snapshots, oracle data, tolerances, dependencies, version or generated wiki are changed.

## 7. Verification completed and implementation acceptance

Completed with the project runtime:

- **140 passing** existing Chara/Varga/Shodashvarga unit tests; no failures/errors/skips in the XML receipt.
- **10 passing** selected Chara direct-input HTTP tests; the remainder of that file was deselected. These ASGI tests stub engine construction and require no ephemeris.
- Kernel-free runtime probes of cycle inputs, request/response fields, node maps, 720 D60 midpoints, nullable generic D60 and the Capricorn placement disagreement.
- ASGI probe of default/cycle-extra/node cases and named/generic/Shodashvarga field omission. Engine construction was explicitly stubbed; chart-backed routes were inspected but not exercised in this research receipt.
- Local source extraction, file hashing and visual inspection of governing Rao/BPHS pages. Zero extracted characters for a scan is a limitation, not a source conclusion.

Commands, from `C:\dev\moira`:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests\unit\test_jaimini_extended.py tests\unit\test_varga.py tests\unit\test_shodashvarga.py -m 'not external_network' -q --junitxml=C:\dev\outputs\vedic-001-003-research-2026-10-07\baseline.xml
.\.venv\Scripts\python.exe -m pytest tests\server\test_vedic_direct_input_hardening.py -k chara -m 'not external_network' -q --junitxml=C:\dev\outputs\vedic-001-003-research-2026-10-07\chara_http_baseline.xml
$env:MOIRA_NO_DOWNLOAD='1'
.\.venv\Scripts\python.exe C:\dev\outputs\vedic-001-003-research-2026-10-07\http_probe.py
```

Receipts are private local files under `C:\dev\outputs\vedic-001-003-research-2026-10-07`: `local_manifest.json`, `runtime_probe.json`, `http_probe.py`, `http_probe.json` and the two JUnit files. UTF-8 extraction/render artifacts are under `tmp\pdfs`. An initial console encoding failure occurred after the runtime JSON had been saved; the output step was repaired and completed. The HTTP witness was also corrected to use the actual `varga` request key before retaining its successful route results. Neither was an engine defect.

Baseline tests prove their original scope. They do not validate new cycle bounds, corrected names, another school's calendar, every API route or predictive accuracy. No chart reader/kernel, native parity, full-suite, release or deployment verification is claimed here.

Implementation acceptance should add independently specified cycle/lineage cases, including both sequence directions, own-sign duration and every admitted co-lord branch; hostile input rejection in both engine and HTTP; exact default parity; period-count/cycle/clock metadata consistency; and finite monotonic endpoints. The published C1 witness supplies second-cycle duration checks, not a synthetic complete chart reconstructed from guessed longitudes.

D60 acceptance should use the printed ordinal list rather than import expected names from the implementation table; exercise odd/even reversal, exact half-degree and sign boundaries, adjacent representable values and 360-degree normalization; assert generic D60 `null`; and prove nested transport across all eight routes. Real chart-backed checks need the admitted chart context and serving reader. Any future placement correction requires a separate source-backed fixture for the Capricorn example and a stated degree convention.

## 8. Source fingerprints

SHA-256 identifies the exact reviewed files, not their scholarly accuracy or licensing. No scan or full extraction is committed or supplied to the generated wiki.

| Source | SHA-256 |
| --- | --- |
| C1 local article compilation | `720978aab2354307b7cac3e98d0fae0ef90c25db1fa3042891c041cec0a947e5` |
| C2 teaching article | `398b9c57728bbf3a8bb6c825798eb3bf5e7b0784601dbd1470ab0fedfc8eafb2` |
| C3 author-site PDF | `2a6b1b224fb0f1b2bd7f1f55403f5a6f3c805277f71c5389b1ae8d14afb00fb0` |
| C5 translated/commented Jaimini | `1b1441b138093433fa594f49a7b89863bd00c0476f621f804895ec7d8c3cc6b8` |
| C6 BPHS Vol. II | `ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45` |
| D1 BPHS Vol. I | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| U1 malformed advanced-use PDF | `3c293fabf5e9656c9e9a35b251208fe8f915212fd4e1c8c0e5eefd86bdfe73dc` |
| U2 Rangacharya scan | `8290bc9d8a9d5eedd5ac0724f15554c7ff70f276a26103b58cbd7e068ea5a5f8` |
| U3 supplementary predictions PDF | `f75c7dc4fd4004cdc7bba644302e7bf77f2c41828d5c2fd20e3ec10d8506ff2a` |

The C4 and D2 web versions were read online; no local digest is claimed for them. The apparent Rao book title remains an unverified bibliographic attribution. Rangacharya, critical-edition/Sanskrit variants, complete Rao co-lord tie-break authority, exact calendar-year semantics and source-selected D60 placement are recorded limits, not silently filled defaults.

## 9. Documentation checkpoint

The work register remains open for VED-001/003. This packet changes their evidence and prospective scope, not their completion status or the total open count. Documentation verification passed: both owning documentation guards, 64 relative file links, all eight local PDF fingerprints plus the author-site PDF, 24 unique work IDs and two in-memory generated-wiki previews. The preview witness uses the owning generator's `.md` basename format; it does not assume extensionless links.

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe C:\dev\outputs\vedic-001-003-research-2026-10-07\verify_research_docs.py
git diff --check
```

The private `doc_validation.json` records the counts and XML cross-checks. The wiki preview includes the new untracked packet explicitly, without staging it or writing the generated mirror. These narrow guards are not whole-documentation lint or publication verification. Generated-wiki publication, commit/push and runtime implementation are separate operations after this checkpoint.

## Subsequent implementation receipt

The user subsequently approved this plan. The
[7 October implementation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
records the resulting bounded engine/REST admission and source-only D60
adjudication. The research/planning checkpoint above remains historical;
current executable truth belongs to the linked standards and receipt.
