# Pancha Pakshi Admission Evidence — 2026-07-20

## Stage 2B Fixed-Clock Materialization Addendum

Stage 2B admits one further capability, `fixed_clock_materialization`, for the
same `source_scoped_public` profile. The profile document remains unchanged at
canonical SHA-256
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`,
and default selection remains forbidden. The chained decision is recorded in
[`pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json).
It freezes the prior Stage 2A decision at SHA-256
`de8e40c161a327695702b9b152f89da8e848f32aafb4d0b155176d28381c9fd2`,
the prior manifest at SHA-256
`4587306ded9b5760940e7f80c45b6c40132590473e910ea9350c9d7fa141a2ee`,
and binds the new manifest at SHA-256
`766f92650bc050f4c88670f8fd6307036ff49a97e812c9efc9a428fb76e53e17`.

The governing object is `PanchaPakshiFixedClockMaterialization`, with immutable
`PanchaPakshiFixedClockMaterializationPolicy` and
`PanchaPakshiFixedClockCell` vessels. Its only admitted policy is
`fixed_24_minute_nazhigai_from_local_solar_half_start_v1`, explicitly a modern
Moira composition rather than an 1879 source claim. The assembly is bounded:

- the unchanged 1879 profile supplies the exact nominal offsets, durations,
  chronology, assignments, and locators;
- the Stage 2A context supplies the selected schedule and governing solar half;
- day anchors at governing topocentric sunrise and night at governing
  topocentric sunset;
- one nazhigai is exactly 1,440 SI seconds, and 30 nazhigai is exactly 43,200
  seconds;
- exact nominal offsets are added on reader-bound TT and then projected to UT1;
- cell ownership is half-open, and the fixed end is never clipped or stretched
  to the solar end; and
- the signed topology metric is
  `fixed_end_jd_tt_minus_solar_end_jd_tt`, with `0.0001 s` numerical
  coalescence.

The source roles remain separate. The 1879 leaves named in the decision fixture
govern the nominal schedule only. The University of Madras
[*Tamil Lexicon*, page 2231](https://dsal.uchicago.edu/cgi-bin/app/tamil-lex_query.py?qs=%E0%AE%A8%E0%AE%BE%E0%AE%B4%E0%AE%BF%E0%AE%95%E0%AF%88&searchhws=yes&matchtype=exact)
defines a nazhigai as sixty vinadi or twenty-four minutes. The
[IERS TT convention](https://www.iers.org/SharedDocs/Glossareintraege/EN/T/tt)
and [IERS Technical Note 29](https://www.iers.org/SharedDocs/Publikationen/EN/IERS/Publications/tn/TechnNote29/tn29.pdf?__blob=publicationFile&v=1)
govern TT's conventional realization and SI-second basis. The Stage 2A
Horizons comparison governs only the local-solar anchor. No one source is
presented as attesting the full modern composition.

The low-level engine, facade, and REST surfaces are respectively
`pancha_pakshi_fixed_clock_materialization_at(...)`,
`Moira.pancha_pakshi_fixed_clock_materialization(...)`, and
`POST /v1/pancha-pakshi/schedule/fixed-clock`. The provenance routing status is
`fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell`.
The result exposes every materialized cell and the fixed-versus-solar boundary
topology, but deliberately contains no current-cell selection and performs no
solar-proportional scaling.

## Stage 2A Local-Solar Context Addendum

Stage 2A admits one additional capability, `astronomical_context`, for the
existing `agastya_madras_1879_akshara_fixed_clock` profile. Admission remains
`source_scoped_public`, default selection remains forbidden, and the profile
document is unchanged at canonical SHA-256
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`.
The additive decision is recorded in
[`pancha_pakshi_1879_local_solar_context_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_local_solar_context_2026_07_20.json).
It hash-binds the frozen Phase 1 decision and the manifest transition rather
than modifying the historical fixture.

The admitted governing object is `PanchaPakshiLocalSolarContext` with its
embedded immutable `PanchaPakshiLocalSolarContextPolicy`. The policy ID is
`local_solar_day_explicit_paksha_v1`. It is explicitly a modern Moira
composition policy, not a source-attested reading from the 1879 print.

The low-level engine accepts a UT1 instant, location, explicit profile, and a
caller-supplied Purva or Amara source label. Datetime-facing facade and REST
surfaces accept a timezone-aware datetime, normalize it to UTC, and preserve
the established UTC civil-anchor conversion into UT1. The existing
local-solar-day boundary then:

- resolves the governing configured-reader-backed topocentric
  `-0.833`-degree sunrise, sunset, and next sunrise;
- classifies sunrise-inclusive/sunset-exclusive day and
  sunset-inclusive/next-sunrise-exclusive night;
- obtains weekday from local mean solar time at the governing sunrise; and
- selects the unchanged nominal 1879 schedule from caller-supplied paksha plus
  derived half and weekday.

The result exposes requested and solar-event UT1 JDs, location, derived half
and weekday, explicit paksha, policy, nominal schedule, and source-scoped
provenance. Its routing status is
`local_solar_half_and_weekday_performed_paksha_caller_supplied`. Polar geometry
without lawful bounds fails explicitly.

Stage 2A does **not** infer paksha from the Moon, accept natal identity, scale
nominal durations, materialize nazhigai offsets as instants, claim a current
activity, add subdivisions or authority birds, score conditions, search
windows, collate witnesses, or raise the profile to `corroborated_public`.
Those boundaries remain separate work.

The Phase 1 computational-semantics digest remains unchanged because it covers
the source profile's identity, nominal schedule, durations, and relationships;
it does not validate the additive context policy. Stage 2A evidence instead
consists of policy identity, profile/manifest admission chaining, established
local-solar boundary tests, context assembly invariants, facade/REST UTC
normalization, and explicit failure behavior. No external Pancha Pakshi oracle
is claimed for this modern composition.

The astronomical boundary itself has a narrower primary-authority check. The
offline JPL Horizons `sun-new-york-equinox` observer-table fixture permits
`2 s`; the content-identified `DE-0441LE-0441` validation run differed by
`0.082 s` at sunrise and `0.123 s` at sunset. The Stage 2A decision fixture
hash-binds that authority fixture and records the comparison semantics. This
supports only the topocentric local-solar boundary, not the historical schedule
or any broader Pancha Pakshi doctrine.

The comparison is not presented as identical-threshold parity: Moira uses its
declared `-0.833`-degree crossing, while the authority fixture was derived at
`-0.8333` degrees and labels time as UT. Both differences are explicit inside
the `2 s` gate.

## Source-Scoped Public Admission Addendum

Phase 0 replaced the former private-or-universal admission binary with finite
profile states: `research_only`, `source_scoped_public`, and
`corroborated_public`. No state authorizes a default; manifest schema 2 rejects
`default_selection_allowed=true`.

Phase 1 admits `agastya_madras_1879_akshara_fixed_clock` as
`source_scoped_public`. The exact public claim is the Agastya-attributed Madras
1879 aksara/query-or-name-initial fixed-clock Pancha Pakshi operating schedule
and directed relationship matrix. Its admitted capabilities are
`aksara_identity`, `nominal_schedule`, and `directed_relationships`.

This decision does not convert the machine reading into competent-human Tamil
review or independent-witness consensus. Those gaps remain explicit and
prevent a corroborated, generalized, natal, or default-canon claim. They do not
prevent publication of this narrowly named witness product with its provenance
and omissions attached to every result.

The additive
[`public admission fixture`](../../tests/fixtures/pancha_pakshi_1879_public_admission_2026_07_20.json)
preserves the former profile SHA-256
`02f1252cbcff10f680148b0213021d30db043c0ecc7387be727ad5d60de04e98`,
binds schema-v2 profile SHA-256
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`,
and records the unchanged computational projection across 10 identity symbols,
28 schedules, 700 cells, and 20 directed relationships. Admission and
provenance metadata are excluded from that projection because this migration
intentionally changes them. The original
blind, grid-reading, adjudication, and reconciliation records remain frozen in
their historical private state.

At the Phase 1 decision, public access was additive through
`moira.pancha_pakshi`, package-root and `moira.vedic` exports, five kernel-free
`Moira` methods, and five explicit-profile REST routes under
`/v1/pancha-pakshi`. There was no native path or astronomical routing in that
Phase 1 product. The Stage 2A addendum above preserves those operations and
adds one separately governed kernel-backed context operation.

The non-bundling policy is unchanged: Moira distributes no archival scan,
derivative PDF, OCR, page image, copied layout, source prose, or third-party
translation. That architectural boundary is not a rights-clearance phase.

## Historical Machine-Reconciliation Decision

The remainder of this document records the state immediately before the
source-scoped public decision above. Statements that the profile was private
or that transport was deferred are retained as historical evidence and are
superseded by this addendum and the live admission standard.

At that historical checkpoint, the
`agastya_madras_1879_akshara_fixed_clock` profile was private and
`research_only`. A multi-pass page-image adjudication resolved the six
material disagreements preserved by the original blind and representative-grid
records. It established the complete `30/5/6` day/night scope, paired-weekday
semantics, and table axes; confirmed the Amara-night schedule and all twenty
directed nonself relationship cells; and proved that the existing Pūrva-night
generator was wrong. The profile record then acquired the corrected
Pūrva-night step and offsets.

This was machine-assisted resolution for the then-private profile, not
competent-human Tamil sign-off, independent-witness consensus, or public
doctrine. That historical reconciliation itself added no package-root export,
`Moira` facade method, FastAPI route, OpenAPI schema, or native path; the later
Phase 1, Stage 2A, and Stage 2B decisions above admitted the bounded public
surfaces separately.

The machine-readable evidence consists of four distinct records:

- the frozen
  [`blind reading`](../../tests/fixtures/pancha_pakshi_1879_blind_reading_2026_07_20.json);
- the frozen
  [`representative-grid reading`](../../tests/fixtures/pancha_pakshi_1879_grid_reading_2026_07_20.json);
- the frozen follow-up
  [`page-image adjudication`](../../tests/fixtures/pancha_pakshi_1879_adjudication_2026_07_20.json); and
- their hash-bound
  [`reconciliation`](../../tests/fixtures/pancha_pakshi_1879_independent_review.json).

The versioned reconciliation remains marked
`private_executable_machine_reconciled` because it records that historical
checkpoint. It binds the corrected profile and preserves the earlier records
without rewriting them. That record is not an external oracle and does not by
itself authorize admission; the later additive decisions do.

## Governing Witness And Method

The source remains the 1879 Madras print at
[`dli.rmrl.000451_images`](https://archive.org/details/dli.rmrl.000451_images).
The locally inspected Internet Archive derivative PDF has SHA-256
`ed52945ee141faa3f6967b8f043077b95abef9ff674ffb83eaba633417c669c9`.
Internet Archive metadata distinguishes that derivative PDF from the original
image ZIP; both file identities and archive hashes are retained in the profile
provenance.

Two initial read-only reviews were kept separate and frozen before the first
reconciliation:

1. a blind extraction that did not inspect Moira's profile, JSON, tests, or
   doctrine documents before freezing its reading; and
2. a separate visual reading of representative printed schedule grids.

The later adjudication split temporal, fraction, schedule/table-axis, and
relationship questions into independent page-image tasks. Blind tasks did not
inspect the profile before freezing their readings. Each record names its
reviewer identity, protocol, witness hashes, timestamp, and per-reading leaves.
The reconciliation binds all three record hashes and the corrected profile
hash. OCR was used only to locate leaves; page images governed every recorded
reading. This is independently produced machine-assisted evidence, not
competent-human Tamil sign-off.

## Machine-Adjudicated Readings

The follow-up page-image adjudication records these normalized facts for the
then-private, now source-scoped-public profile:

- both day and night contain five six-nazhigai samams within a fixed
  thirty-nazhigai half;
- activity durations are Eat `5/4`, Walk `3/2`, Rule `2`, Sleep `3/4`, and
  Die `1/2` nazhigai;
- paired weekday headings name discrete alternatives sharing one table;
- the identified grids assign birds to activities, while explicit prose and
  verse govern chronological order;
- Pūrva-night advances its Eat bird by one place per samam and uses offsets
  Eat `0`, Walk `2`, Rule `-1`, Sleep `1`, and Die `-2` in bird order
  Vulture, Owl, Crow, Cock, Peacock;
- the existing Amara-night seed vector and schedule assembly are confirmed;
  and
- the existing complete directed relationship matrix is confirmed, including
  its asymmetric Owl-outward pairs.

These readings are asserted against the source-scoped profile by focused
data-integrity tests. They remain machine-read source evidence, not a claim
that the profile is a universal Pancha Pakshi canon.

## Resolved Machine Findings

| Finding | Historical machine-reconciliation result | Remaining boundary |
|---|---|---|
| Temporal-model scope | IA leaves n6 and n15 establish the fixed `30/5/6` structure for both day and night. | Competent-human Tamil confirmation remains necessary for a corroborated or universal claim, not for the bounded source-scoped product. |
| Paired headings and table axes | Paired names are weekday alternatives. Vākkiya grids select weekday assignments; Eḻuttu and Toḻil grids expose samam/activity/bird assignments under their identified axes. | Visual grid order is never chronological authority. |
| Pūrva-night assembly | The prior generator was wrong. Sunday/Tuesday begins `Crow-Eat, Owl-Rule, Vulture-Die, Peacock-Walk, Cock-Sleep`; step and offsets are corrected in the profile. | The corrected 175-cell surface is public only as part of the named source-bound product. |
| Amara-night seeds and assembly | Sun–Sat seeds remain `Vulture, Cock, Vulture, Owl, Crow, Peacock, Cock`; the existing step, offsets, chronology, and assignments are confirmed. | No universal doctrine is inferred. |
| Directed relationships | IA leaf n52 directly defines all twenty ordered nonself cells; direction is subject-to-target and reciprocity is never inferred. | Independent-witness collation remains incomplete. |
| Activity synonyms | Alternate Eat and Sleep lexemes are computational synonyms within the same five-state scheme. | No additional state is manufactured from lexical variation. |

The earlier disagreements were substantive and remain visible in their frozen
records. The later adjudication resolves them by identifying the governing
axes, grammar, and text layer; it does not pretend that the earlier readings
always agreed.

## Source Artifact Boundary

The 1879 print and all later witnesses are research references, never package
assets. Moira distributes its own code, schema, prose, and independently
normalized symbolic profile; archive files and copied source expression remain
outside the product.

The standing boundary is therefore architectural rather than a clearance
exercise:

- included: Moira-authored code, schema, explanatory prose, independently
  normalized symbolic rules, bibliographic facts, hashes, and locators;
- never bundled: archive image ZIPs, derivative PDFs, OCR, page images, copied
  table layouts, source prose, and third-party translations; and
- admission effect: archive license metadata and contributor biography do not
  govern public admission because no source artifact or copied expression is
  distributed.

## Competent Tamil Review Packet

The next competent reviewer should inspect the exact hashed witness and
confirm or reject these machine readings in writing, with leaf locators and a
signed reconciliation table:

1. n6, n10, n18, and n50–n51 assign `1 1/4, 1 1/2, 2, 3/4, 1/2`
   nazhigai to Eat, Walk, Rule, Sleep, and Die respectively.
2. Paired weekday headings denote two discrete alternatives sharing one
   complete table.
3. The identified table axes assign birds and activities; explicit prose and
   verse, not visual grid order, govern chronology.
4. Pūrva-night uses step `1`, offsets Eat `0`, Walk `2`, Rule `-1`, Sleep `1`,
   Die `-2`, and chronology Eat, Rule, Die, Walk, Sleep.
5. Wednesday, Thursday, and Saturday Amara-night first-Eat birds are Owl,
   Crow, and Cock.
6. IA leaf n52 defines every ordered nonself relationship directly under
   subject-to-target grammar.
7. Alternate Eat and Sleep terms are lexical synonyms within the same five
   computational activities.

Priority visual leaves are n5–n6, n10, n16–n18, n21–n25, n26–n35, n41–n42,
n50–n52. The archive PDF page `P` corresponds to IA leaf `n(P-1)` in the
inspected file.

## Historical Admission Gate Ledger

This table records the pre-admission checkpoint; the addenda above state the
current bounded public status.

| Gate | State at the historical checkpoint |
|---|---|
| Machine-assisted transcription and adjudication | Completed for the then-private profile; all six prior findings resolved without rewriting the frozen records. |
| Competent Tamil review | Not completed. |
| Independent-witness collation | Not completed; the 1867 parallel relationship reading is provisional only. |
| Assignment/chronology precedence | Resolved for the named source profile: identified grids govern assignments; explicit prose and verse govern chronology. |
| Source-artifact policy | Satisfied: witnesses are reference-only and never bundled; this is not an admission gate. |
| Identity product | Satisfied for the named aksara/query-or-name-initial product; explicitly not natal Moon identity. |
| Source-owned examples | Resolved into a complete source-owned Pūrva-night assignment oracle and confirmed Amara-night examples. |
| Public vessels and transport | Deferred at this checkpoint; admitted later by the Phase 1, Stage 2A, and Stage 2B decisions above. |

## Validation Receipt

The corrected checkpoint was verified on 2026-07-20 with the project Python
3.14.3 `.venv`, `MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`, and
downloads disabled:

- the two Pancha Pakshi modules passed `26` focused tests;
- the combined local-solar-day, Planetary Hours API, facade clock-boundary,
  Pancha Pakshi internal, and Pancha Pakshi data-integrity slice passed `67`
  tests;
- the source-owned Pūrva-night oracle checked every weekday and all five
  samams, independently of the generic bijection invariant;
- the three Python modules compiled and parsed under Python 3.10 grammar;
- the profile, manifest, three source records, and reconciliation all parsed as
  JSON, and every canonical SHA-256 binding matched profile digest
  `02f1252cbcff10f680148b0213021d30db043c0ecc7387be727ad5d60de04e98`;
- documentation consistency, tracked-diff whitespace, package import/native
  identity, and the no-public-surface search passed; and
- the loaded package/native identity was `5.0.0` with the Python 3.14 Windows
  native extension.

This historical receipt proves the then-private schema/hash integrity,
fail-closed loading, the
corrected source-owned Pūrva-night assignments, generic schedule invariants,
and preservation of the shared Python solar-day boundary. The two real
solar-window tests used the discovered DE441 resource; no Pancha Pakshi native
path exists. The adjudication remains machine-assisted research evidence, so
no competent-human Tamil attestation, external-oracle parity, universal-
doctrine claim, or admission beyond the later explicitly bounded decisions is
asserted.

## Remaining Research Sequence

1. Obtain competent-human Tamil confirmation using the packet above.
2. Collate the normalized rules against at least one genuinely independent
   Pancha Pakshi witness rather than an adjacent omen or compatibility system.
3. Preserve any disagreement by witness and text layer; do not merge doctrines
   or repair them by symmetry.
4. Admit any current-cell selection, solar-proportional timing, or broader
   doctrine only through a separately named policy and evidence decision.

The present resting place is the corrected, tested, source-scoped public
profile plus the separately named Stage 2A and Stage 2B modern compositions.
It is not a universal canon, and the unresolved research above must not be
silently inferred through the public API.
