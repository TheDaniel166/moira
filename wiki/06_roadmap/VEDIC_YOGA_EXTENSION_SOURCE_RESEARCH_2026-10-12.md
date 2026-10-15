# VED-012: extended yoga source research

Date: 12 October 2026. Status: completed research checkpoint preceding
implementation. The subsequently authorized 21-entry package is now locally
complete; see the [execution receipt](../03_validation/YOGA_EXTENSION_VALIDATION_2026-10-12.md).
The research observations below retain their original checkpoint scope.

Owning checkout: `C:\dev\moira`, inspected at
`d0111260c58d9f5d6a4f817b11411c51f504bbf7` (6.9.9). That authorized work was
online/local-book research and an implementation plan. The companion
[plan](VEDIC_YOGA_EXTENSION_IMPLEMENTATION_PLAN_2026-10-12.md) proposes 21
source rule entries, plus a non-executable record for an unresolved reading.
This is not certification of every yoga in the cited books.

## 1. Decisions

1. **Admit for implementation planning:** JP 7.14 under Sastri's translation,
   and Raman's *Three Hundred Important Combinations* no. 252 as two separate
   Navamsa rules. Neither is a synonym for all Neecha Bhanga doctrine.
2. **Admit for implementation planning:** all fourteen BPHS 41.2-15 wealth
   clauses, preserving every named planet and the direction of each aspect.
3. **Admit for implementation planning:** five BPHS royal-birth entries:
   39.33-34, 39.36, 39.37, 39.38 and 39.39. Several overlap the existing
   Kendra/Trikona family; source witnesses must not become additive strength
   votes.
4. **Defer one interpretation:** BPHS 39.35. The source is available, but
   the aspect targets need a defensible reading. An all-to-all full-aspect
   reading is impossible. Keep that issue explicit in the catalogue.
5. **Correct the old source lead:** *How to Judge a Horoscope*, Volume II,
   exists locally and online. The bare historical label "Raman Part II"
   does not identify a title, edition or passage. It must not become either
   an invented authority or a blanket claim that the book is unavailable.
6. **Include contract repairs:** direct Python input admission currently
   differs from REST, and missing speed evidence is encoded as false in a
   legacy condition. Resolve those specific issues in the implementation
   plan without merging new source rules into existing defaults.

## 2. Source identities and inspection

Local paths below are relative to `C:\dev\ASTROLOGY-BOOKS-DATABASE`.
PDF page numbers are one-based, distinct from printed page numbers.
Relevant scanned clauses and the Chart 122 diagram were visually inspected
after text extraction. Full books and page images are not redistributed in
the repository. Local working files are under
`C:\dev\outputs\ved012-research-2026-10-12`.

| Witness | Local file | Passage and inspection | Attribution limits |
| --- | --- | --- | --- |
| BPHS-S | `Classics books/BPHS-Santhanam-Vol-1.pdf` | R. Santhanam, Ranjan Publications; 482 PDF pages. Ch. 39, printed 395-396 / PDF 394-395; ch. 41, printed 402-406 / PDF 401-405. Verse text and commentary distinguished. | The inspected title identifies translator/publisher; exact printing year is not established by the local title pages. Repository accession dates are not edition dates. |
| JP-S | `Classics books/Jataka-Parijata-Vol-2.pdf` | Vaidyanatha Dikshita, V. Subrahmanya Sastri translation, Ranjan; 392 PDF pages. 7.13-14, printed 386-387 / PDF 70-71. | This scan is from a three-volume split. Other editions' volume/page numbers must not be substituted. Exact local printing year unestablished. |
| R300 | `Books by Authors/BV Raman/300 Important Combinations.pdf` | B. V. Raman, Motilal Banarsidass; 350 PDF pages. No. 252, printed 245 / PDF 255; Chart 122, printed 248 / PDF 258. No. 250 commentary, printed 243-244 / PDF 253-254, is a separate variant discussion. | Exact printing year absent from the inspected local front matter. The original preface date does not identify this printing. |
| RJ2 | `Books by Authors/BV Raman/How to judge horoscope 2.pdf` | B. V. Raman and Gayatri Devi Vasudev, *How to Judge a Horoscope*, Volume Two, VII-XII Houses. 483 PDF pages. Title/edition/contents at PDF 2-4: fifth edition 1995, reprints through 2003. | This local file is a re-typeset electronic witness, not a facsimile of every printed page. Used here to resolve availability and identity, not as the authority for the 21 rules. |
| PD-context | `Classics books/Mantreswara_Phaladeeplka.pdf` | Ch. 7.26-30, PDF 89-91, inspected as context for the existing engine's cancellation citations. | No replacement of the existing edition-owned Neecha Bhanga policy is admitted by this research. |

SHA-256 identities of the computational source witnesses:

| Witness | SHA-256 |
| --- | --- |
| BPHS-S | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |
| JP-S | `898de4c6f212c46e4376a64c3fd341bc64c8d11d6ace504a3acc25142a00b2dd` |
| R300 | `3d511f6237659d72ea590324fcc7c41c4403d2ac9266715872315b3d930646cc` |
| RJ2 | `69977c20be91da983f9eb48e7950d209e595dd045171c1a7d2d383eefe6f2174` |

Online inspection on 12 October 2026:

- S-VYASA's [JP catalogue](https://elibraryofyoga.com/items/5586d137-1723-4564-81b3-84a5db5f2945)
  identifies Sastri/Ranjan and all three volumes. The
  [Volume II file](https://elibraryofyoga.com/server/api/core/bitstreams/486903ef-2b77-453c-a7c2-85e4127af8fd/content)
  was accessible during research; subsequent fetches intermittently timed
  out. Local rendered pages own the verse inspection.
- S-VYASA's [BPHS catalogue](https://elibraryofyoga.com/items/13b2600f-95fd-4bb5-86b4-a18396c68993)
  identifies Santhanam/Ranjan and both volumes. The online Volume I exceeds
  the web reader's size limit. This does not make the local source missing.
- S-VYASA's [Raman catalogue](https://elibraryofyoga.com/items/337f87a9-f973-4261-9695-39e086bd602d/full)
  and [Volume II file](https://elibraryofyoga.com/bitstreams/c0aa84c8-2bb0-48f7-a02e-d319cfd7ed32/download)
  are accessible. The online PDF has 482 pages, the local file 483: these
  are not asserted to be byte-identical witnesses.
- An [online reproduction of Raman's book](https://studylib.net/doc/27411399/300-important-combinations-b.v.-raman)
  gives tenth edition 1991 / reprint 1994 and agrees on no. 252 and Chart
  122. This is the author's text on a third-party host, not that host's
  independent validation. Do not assign its edition year to the local PDF.
- [Parul University's Sanskrit BPHS](https://www.paruluniversity.ac.in/wp-content/uploads/2025/12/Parashara_Hora_Shastra.pdf),
  [Sanskrit Documents' chapter collection](https://sanskritdocuments.org/doc_z_misc_sociology_astrology/horaashaastraEng34-45.pdf)
  and the [Subodhini witness, page 204](https://sa.wikisource.org/wiki/पृष्ठम्:श्रीमद्बृहत्पाराशरहोराशास्त्रम्_(सुबोधिनीटीकासहितम्).pdf/२०४)
  were consulted for the 39.35 difficulty. Different numbering and wording
  exist; an unproofread transcription is not a resolved aspect-target rule.

Search-result blogs, modern summaries and software agreement were not
promoted to governing doctrine. Exact publication-year uncertainty does not
prevent identifying a passage by its named translation, scan hash and page.

## 3. Navamsa: two different computational objects

### JP 7.14

The selected Sastri reading is, for each debilitated D1 planet `p`:

```text
debilitated_D1(p)
AND house_D1(lord(sign_D9(p)), D1_lagna) in {1, 4, 5, 7, 9, 10}
AND (movable(D1_lagna_sign) OR movable(sign_D9(D1_lagna_lord)))
```

The printed translation supplies the Navamsa lord, kendra/trikona and
movable-sign clauses. Locating that lord in the natal whole-sign chart from
the natal Lagna is the declared computational reading. It is not a Moon
reference or a house counted in D9. The second movable branch uses the D9
sign of the D1 Lagna's lord, not the D9 ascendant.

Keep the clause tree as `A AND B AND (C OR D)` and retain every body witness.
At least one qualifying debilitated planet establishes this source rule.
A chart with no debilitated planets cannot pass by vacuous truth. Exaltation
of `p` in D9 is neither required nor a substitute for the printed clauses.

### Raman no. 252

This is the separate D1-debilitation / D9-exaltation rule. The definition is
plural; the commentary to Chart 122 explicitly discusses all debilitated
planets in that chart. The proposed first profile therefore requires a
nonempty set of D1-debilitated classical planets and D9 exaltation for every
member. Keep per-planet relief witnesses, but do not silently weaken the
chart rule to "any one planet". This quantifier is a disclosed selected
reading, not a claim that every practitioner uses it.

Chart 122 gives a useful independent sign fixture:

| Body | Printed D1 sign | Printed D9 sign |
| --- | --- | --- |
| Sun | Libra | Aries |
| Moon | Virgo | Cancer |
| Mars | Cancer | Capricorn |
| Mercury | Libra | Libra |
| Jupiter | Aquarius | Gemini |
| Venus | Scorpio | Leo |
| Saturn | Gemini | Taurus |
| Lagna | Capricorn | Capricorn |

The relevant debilitated bodies are Sun and Mars. The printed birth details
are 5 November 1915, 11:30 a.m. IST, 15 N, 77 E. The diagram supplies signs,
not exact planetary longitudes or a fully specified astronomical pipeline.
Do not present an arbitrary representative degree as the published degree.

A research-only adapter check used synthetic interior longitudes
`Sun=201, Moon=171, Mars=111, Mercury=181, Jupiter=328, Venus=214, Saturn=84,
Lagna=271` degrees. Existing `moira.varga.navamsa` reproduces those paired
signs. This checks the sign-fixture adapter; it is not a reconstruction of
the birth ephemeris. Independent tests must retain the printed sign table
separately from these constructed inputs.

Raman no. 250 also discusses an alternative to the existing
"lord of the exaltation sign" cancellation clause. That disagreement must
remain catalogued separately; no. 252 does not authorize replacing the
legacy Phaladeepika/Sastri choice. A formed relief rule also does not change
the planet's underlying D1 dignity or mean the relief rule is itself
`cancelled`.

## 4. BPHS 41.2-15: fourteen wealth clauses

All houses below are natal whole-sign houses. Each row is its own rule.
Named planets joined by commas are conjunctive requirements, not options.
BPHS-S printed 402-405 / PDF 401-404 governs this table.

| Verse | Planet in its own sign in H5 | Required occupants of H11 | Implied Lagna(s) |
| --- | --- | --- | --- |
| 41.2 | Venus | Mars | Gemini, Capricorn |
| 41.3 | Mercury | Moon, Mars, Jupiter | Taurus, Aquarius |
| 41.4 | Sun | Saturn, Moon, Jupiter | Aries |
| 41.5 | Saturn | Sun, Moon | Virgo, Libra |
| 41.6 | Jupiter | Mercury | Leo, Scorpio |
| 41.7 | Mars | Venus | Cancer, Sagittarius |
| 41.8 | Moon | Saturn | Pisces |

These seven templates cover twelve ascendants. The commentary's compressed
summary must not remove the additional planets in verses 41.3-5.

For 41.9-15, the resident planet is in its own sign in H1. Every supporting
planet must join it or cast an aspect on it:

| Verse | Resident Lagna lord | Required supporters |
| --- | --- | --- |
| 41.9 | Sun | Mars, Jupiter |
| 41.10 | Moon | Mercury, Jupiter |
| 41.11 | Mars | Mercury, Venus, Saturn |
| 41.12 | Mercury | Saturn, Jupiter |
| 41.13 | Jupiter | Mercury, Mars |
| 41.14 | Venus | Saturn, Mercury |
| 41.15 | Saturn | Mars, Jupiter |

Selected executable reading: `ALL supporters (same_sign(supporter, resident)
OR full_graha_aspect(supporter -> resident))`. Different supporters may
satisfy different branches. This distribution of the alternatives must be
named in the profile; it is not replaced with generic sambandha, exchange,
reverse-only aspect, or "at least one supporter". Preserve both witnesses
if a later source profile admits overlapping relations.

Verse 41.17 explicitly qualifies interpretation by favorable/unfavorable
disposition and planetary strength. Formation alone does not establish
realized wealth. Return that contextual qualification as not assessed;
do not invent a Shadbala threshold or make missing strength evidence mean
the formation is absent. Verse 41.16 concerns dasha context, and 41.18
onward divisional dignity; neither becomes a hidden condition of 41.2-15.

## 5. Selected BPHS chapter 39 rules

The five proposed entries use BPHS-S printed 395-396 / PDF 394-395.
`Lh` below means the lord of natal house h.

| Source entry | Formation and branches | Required distinction |
| --- | --- | --- |
| 39.33-34 | L5 and L9 mutually aspect; or conjunct; or occupy opposite signs | Keep verse/branch witnesses. The royal-lineage premise attached to the latter outcome is historical interpretation context, not inferred chart data. |
| 39.36 | L5, L10, L4 and L1 all occupy H9 | One physical planet can hold multiple roles; do not require four distinct bodies. |
| 39.37 | A conjunction of one of L4/L10 with one of L5/L9 | Four alternatives; retain all satisfied pairs. Same planet holding both roles is not a conjunction with itself. |
| 39.38 | L5 occupies H1/H4/H10 and joins L9 or L1 | The two companion branches are explicit; no self-conjunction. |
| 39.39 | Jupiter owns and occupies H9 and joins Venus or L5 | H9 ownership restricts the Lagna to Aries/Cancer. A generic benefic association is insufficient. |

No caste or royal ancestry input is needed to detect these geometries.
Source outcome conditions remain attributed, unevaluated context. Do not
claim royal birth, political power or life outcomes from the returned match.
Shared witnesses with existing Raja rules are cross-references, not grounds
for suppressing source evidence or accumulating a new score.

### Why 39.35 is separately deferred

The verse places L4 in H10 and L10 in H4, then refers to aspects of L5 and
L9. The English sentence does not unambiguously assign those aspects to
both occupants, just the latter, or a distributed pairing. The printed
Sanskrit and the additional witnesses require editorial collation before
selecting one of those target readings.

There is a concrete trap: requiring each supporter to cast a full graha
aspect on both opposite H4/H10 positions is impossible. For all twelve
source signs, none of the seven admitted aspect-distance sets contains
both targets. A read-only 7 x 12 enumeration confirmed zero witnesses.
This is a model-specific impossibility, not evidence that the verse is
meaningless; fractional or rasi aspects are different doctrines.

Admission requires a named primary translation/commentary resolving the
targets and aspect type, then a satisfiable positive case and negatives for
the rival readings. Do not silently change "and" to "or", introduce partial
aspects, or ship an always-false rule. The initial catalogue should report
`research_required`, with this exact reason.

The rest of chapter 39 is not an undifferentiated missing feature: it mixes
ordinary natal combinations, Jaimini/Arudha/Karakamsa references, special
Lagnas, six-varga references, strength conditions and birth-time windows.
Special-Lagna definitions remain VED-016. Later 39.40-48 candidates need
their own time/strength/quantifier and reachability decisions; they are not
included in the 21-entry package.

## 6. Existing engine and REST findings

Inspected owners: `moira/yogas.py`, `moira/varga.py`, curated exports in
`moira/__init__.py`, `moira/facade.py`, `moira/vedic.py`, and the yoga
models/service/router under `moira_server/`.

- The current engine has six proof-bearing families, whole-sign houses,
  seven classical bodies and full graha aspects. Its aggregate accepts
  sidereal longitudes; it does not receive a D9 chart. D9 can be derived
  with the existing exact-partition `navamsa` owner, without ephemeris calls.
- `_sambandha` admits conjunction, exchange and mutual aspect. It is not
  the directed relation required by 41.9-15 and cannot implement those
  clauses unchanged.
- The existing JP 7.14 citation explicitly says the Navamsa rule is not
  implemented. It must not become an assertion that no JP-backed method
  exists after the separate extension is delivered.
- REST already rejects missing/unknown bodies and non-finite or boolean
  longitudes. Direct `evaluate_yogas` currently accepts missing Mars,
  an extra Pluto key, a boolean Sun longitude and a boolean Lagna. The
  identical inputs were probed through both engine and request model.
- `YogaPolicy(budhaditya_combustion_cancel='false')` accepts a truthy
  string, while the REST model coerces it to false. `include_absent`
  similarly accepts coercible strings/integers in REST. Actual booleans
  need consistent admission.
- A missing speed makes a retrograde condition `satisfied=False` with
  `observed='speeds not supplied'`. This is a documented legacy convention,
  not evidence that the planet is direct. The plan adds machine-readable
  non-evaluation while preserving existing satisfied/present meanings.
- The current REST response omits the selected policy object even though
  the engine result contains it. Extension provenance and applied-policy
  receipts must survive serialization; no server-owned doctrine logic.

## 7. Research validation receipt

Runtime: project `.venv`, Python 3.14.3. `tests/KNOWN_ISSUES.yml` is empty.
The checkout was clean at the start of research. With
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1` and
`MOIRA_STRICT_KNOWN_ISSUES=1`, this baseline command passed all 195 selected
tests, with no failures or skips:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_yogas.py tests\unit\test_varga_exact_partition.py tests\server\test_vedic_direct_input_hardening.py -q
```

It covers existing yoga behavior, exact varga partition tests and current
direct-input HTTP hardening. It does not validate the proposed 21 new rules.
The separate stdin probes recorded the input discrepancies above and the
Chart 122 synthetic sign adapter in
`C:\dev\outputs\ved012-research-2026-10-12\runtime_probes.json`.
The aspect enumeration is a geometric invariant under the named aspect
model, not a primary-text interpretation.

No runtime code, public contract, dependency, native substrate, kernel,
golden artifact or test tolerance was changed. The plan specifies source
fixtures, boundary checks, hostile inputs and engine/REST parity as required
implementation work. The research does not claim predictive validation.

Documentation checks: `.\.venv\Scripts\python.exe
scripts\check_doc_consistency.py` passed; the scoped `git diff --check`
passed; all relative file links in the two new documents and the register
resolve, and their code fences are balanced. The only files authored by this
research task are the two documents and the register. Concurrent website
publication/light-box inventory and workflow changes appeared during the
session and were left untouched. No commit or push was performed.
