# Pancha Pakshi Research And Admission Standard

**Subsystem:** `moira/_pancha_pakshi.py`

**Computational domain:** Source-scoped five-bird timing doctrine

**Status:** Internal research foundation; no public engine, facade, or REST admission

## 1. Current Boundary

Pancha Pakshi is within Moira's astrological domain, but the name does not
identify one interchangeable computational canon. The inspected Tamil
witnesses disagree about identity, durations, schedule cells, relationships,
and the relation between verse and commentary. Moira therefore has no default
Pancha Pakshi canon and exposes no public Pancha Pakshi computation route.

The private implementation may load and validate a named research witness. It
must never present that witness as universal doctrine, combine it with a
different witness, or make its existence a compatibility promise.

The first internal profile is
`agastya_madras_1879_akshara_fixed_clock`. It is limited to the
query/name-letter operating-schedule product and fixed-clock timing attested
by the 1879 printed witness. It is not a natal-Moon or birth-nakshatra profile.

## 2. Governing Objects

The research layer keeps these objects distinct:

- **witness** — one identified edition or manuscript record;
- **text layer** — verse, commentary, printed table, or an explicit rule
  derived from those objects;
- **profile** — one named, internally coherent selection from one witness;
- **product kind** — for example, an aksara/prasna operating schedule rather
  than natal-bird timing;
- **regime** — Purva or Amara, separately for day and night;
- **schedule cell** — one bird, activity, samam, sequence position, exact
  duration, and source locator;
- **identity policy** — query/name initial, birth nakshatra, or another
  explicitly sourced identity product;
- **timing policy** — source-attested fixed nazhigai timing or a separately
  named modern seasonal transformation.

No object may silently acquire data from another profile. A source locator is
part of computational truth, not decorative documentation.

## 3. The 1879 Research Witness

The governing source is the Tamil print catalogued by Internet Archive as
[`dli.rmrl.000451_images`](https://archive.org/details/dli.rmrl.000451_images),
published in Madras in 1879 and traditionally attributed to Agastya. The
traditional attribution is bibliographic metadata, not a verified historical
authorship claim.

The admitted research reading is deliberately narrow:

- the opening ontology is aksara/prasna: the relevant initial vowel maps to a
  bird;
- Purva-day, Purva-night, Amara-day, and Amara-night remain four distinct
  regimes;
- each half contains five samams of six nazhigai;
- day and night are each assigned thirty nazhigai;
- the activity durations are exact and uniform across the four regimes:
  Eat `5/4`, Walk `3/2`, Rule `2`, Sleep `3/4`, and Die `1/2` nazhigai;
- the private schedule is generated from the current reading of the witness's
  first-bird and rotation/assembly rules; printed grids remain non-executable
  review evidence because the independent 2026-07-20 review did not reconcile
  the
  Pūrva-night and Amara-night grid semantics, so this reading is not admitted
  public doctrine;
- the private relationship product currently models a complete directed
  matrix attributed to IA leaf n52; reciprocal status is stored independently
  and never inferred, but independent review could not certify every 1879 edge
  and therefore leaves the matrix contested; and
- every generated cell retains the locators for the governing first-bird,
  assembly, chronology, and duration evidence.

The print is a research witness, not a package asset. Moira stores only
independently normalized computational facts, bibliographic metadata,
checksums, and locators. Its standing source-artifact policy forbids bundling
archival scans, PDFs, OCR, page images, copied layouts, source prose, or
third-party translations. Archive license metadata and contributor biography
therefore do not govern public admission.

The independent source review is recorded in
[`PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md`](../05_research/PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md)
and its non-executable machine-readable companions. Both frozen source records
agree with the profile on the duration facts and the numeric `30/5/6`
structure of the displayed Pūrva-day half; the grid record does not establish
that the latter governs every day/night regime. The blind record alone also
matches the profile's full temporal model, vowel identity, Pūrva-day,
Pūrva-night seed, and Amara-day seed facts. Those one-record matches are not
independent consensus. Six material disagreements are preserved rather than
silently resolved, and they block public admission.

## 4. Conflicts That Forbid A Default

The following are different computational doctrines or unresolved editorial
defects, not values that may be averaged or repaired by symmetry.

| Area | Evidence | Required policy |
|---|---|---|
| Identity ontology | The 1879 opening uses query/name initials; later presentations use birth nakshatra and Moon paksha. | Never label the 1879 mapping as natal identity. |
| Amara natal partition | The 2024 Bogar-attributed edition's verse and commentary disagree at printed p.55 / IA leaf n64; the commentary overlaps Shravana and omits Revati. | No natal profile until text-layer precedence is declared and independently reviewed. |
| Duration vectors | The 1879 witness has one vector; the 2024 Bogar-attributed edition has four regime-specific vectors; a 1934 commentary contains vectors that do not total six nazhigai. | Durations belong to the named witness and text layer. |
| Schedule cell | The 2024 edition at printed p.30 / IA leaf n39 contains a verse/commentary mismatch that duplicates one bird and omits another. | Fail the affected commentary profile; do not infer the missing bird. |
| Relationships | The 1879 relationship table is directed and nonuniform; later tables use different two-friend/two-enemy assignments. | No reciprocity or symmetry inference; no cross-witness merge. |
| Timing | The inspected primary witnesses attest fixed thirty-nazhigai halves, not proportional sunrise-to-sunset scaling. | Seasonal scaling, if later admitted, is a named modern policy. |
| Padu and adhikara | Padu tables occur in later witnesses; no independent adhikara/bharana table was established. `Arasu-pakshi` is the instantaneous Rule activity. | Do not manufacture a day ruler from the Rule state. |

The metadata-only conflict ledger also records:

- the 2024 Bogar-attributed edition at
  [`acc.-no.-44757-panjapatchi-sashthiram-2024`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024);
- the 1934 Uromarisi-attributed edition at
  [`kvc-0354-vinaadi-pajasapatchi-mulamum-1934`](https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934);
- Sarasvati Mahal Library series 213 in the
  [Tamil Digital Library](https://tamildigitallibrary.in/book-detail.php?id=jZY9lup2kZl6TuXGlZQdjZpekJh1),
  whose official catalog says sixth edition/2014 while the inspected internal
  title page says fifth edition/September 2011.

Those records are research evidence only. Archive rights and license labels
remain bibliographic metadata rather than runtime inputs or admission gates.
Moira imports no modern scan, prose, layout, or table transcription.

## 5. Fail-Closed Invariants

A loadable research profile must satisfy all applicable invariants exactly:

- known schema version and matching SHA-256 manifest;
- explicit profile ID, product kind, admission status, witness, and text layer;
- four complete paksha/day-night regimes when an operating schedule claims
  full coverage;
- exactly seven weekday first-bird assignments per regime;
- exactly five known birds and five known activities;
- five samams per half;
- each samam contains every bird and every activity exactly once;
- across five samams, every bird receives every activity exactly once;
- exact positive rational durations whose sum is six nazhigai per samam;
- an exact thirty-nazhigai half;
- nonempty source locators for every generated cell;
- no unknown, duplicated, overlapping, or omitted identity member;
- exactly one explicit relationship status for every ordered non-self bird
  pair when a profile admits relationships, with no reciprocal inference; and
- no source component from a different profile.

Unknown values, hash mismatches, incomplete tables, mixed profiles, and
unresolved verse/commentary conflicts are errors. They are not warnings or
fallback opportunities.

## 6. Public Admission Gate

Public exports, facade methods, FastAPI routes, scoring, and natal analysis
remain deferred. A profile may cross that boundary only after all of the
following are recorded:

1. independent double transcription of the governing cells and rules;
2. review by a competent Tamil reader;
3. collation against at least one independent witness;
4. explicit verse-versus-commentary precedence;
5. a named identity product with no ontology blending;
6. external examples or source-owned worked cases plus structural invariants;
7. immutable public vessels, explicit policy, and additive transport design.

Until then, `moira/_pancha_pakshi.py` and its data are private research
machinery. The root package, `moira.vedic`, `Moira`, and `/v1` intentionally
expose nothing from it.

## 7. Validation Scope

The internal validation slice proves schema, hash, exact arithmetic,
completeness, provenance retention, schedule rotation, and fail-closed
behavior. It is regression and invariant evidence. It is not a claim that the
1879 research profile is the universal, historically original, or most widely
practised Pancha Pakshi canon.

The blind and representative-grid readings are frozen as separate hash-bound
records. Their reconciliation separately checks only the machine-read facts on
which those records and the profile agree. It is marked
`non_executable_unreconciled`, binds the reviewed profile hash, records the
conflicting night and relationship readings, and cannot be used as an
authority oracle. A complete structural schedule remains insufficient proof
when the source table axes themselves are unresolved.

The shared `moira/_local_solar_day.py` boundary is separately regression-tested
against Planetary Hours. Pancha Pakshi does not yet consume it publicly, and
the source-attested fixed thirty-nazhigai policy must not be confused with the
seasonal temporal hours used by Planetary Hours.
