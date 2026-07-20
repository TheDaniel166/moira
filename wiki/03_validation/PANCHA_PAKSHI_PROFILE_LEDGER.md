# Pancha Pakshi Profile Ledger

This ledger records public and research Pancha Pakshi profiles by witness,
text layer, and computational product. Registration never blends witnesses and
never creates a default canon.

## Runtime Profiles

| Profile | Witness and text policy | Product and capabilities | Admission | Public surface | Validation boundary |
|---|---|---|---|---|---|
| `agastya_madras_1879_akshara_fixed_clock` | Agastya-attributed Madras 1879 print, IA `dli.rmrl.000451_images`; identified grids govern bird/activity assignments, explicit prose and verse govern chronology; leaves `n16` and `n26` directly map waxing/Purva and waning/Amara; astronomical classification, local-solar context, fixed-clock materialization/current-cell selection, and solar-proportional materialization/current-cell selection are separately labelled modern Moira policies | `aksara_prasna_operating_schedule`; `aksara_identity`, `nominal_schedule`, `directed_relationships`, `astronomical_context`, `astronomical_paksha_inference`, `fixed_clock_materialization`, `fixed_clock_current_cell_selection`, `solar_proportional_materialization`, `solar_proportional_current_cell_selection` | `source_scoped_public`; no default | `moira.pancha_pakshi`, package root, `moira.vedic`, and the shared family of thirteen `Moira` methods and twelve `/v1/pancha-pakshi` routes; capability gates preserve its eleven admitted operations | Profile hash/schema and exact-arithmetic integrity, 10 identity symbols, 28 schedules, 700 cells, 20 directed pairs; direct lunar-half mapping locators, exact geocentric phase-half ownership, single reader-bound TT, and strict no-location/no-routing inference; local-solar boundary ordering, half/weekday selection, UTC-to-UT1 adapter, and polar failure; fixed/proportional interval invariants; machine-assisted source reading, no competent-human Tamil sign-off, no independent-witness collation, no external Pancha Pakshi oracle |
| `bogamuni_chennai_2024_nakshatra_natal_identity` | Bogamuni-attributed 2024 sixth edition, IA `acc.-no.-44757-panjapatchi-sashthiram-2024`; Purva table at `n52`, governing Amara verse at `n64`, phase binding at `n167`; malformed adjacent Amara commentary is rejected under declared verse precedence; birth-Moon application, Lahiri true ayanamsa, and equal-27-sector placement are explicitly modern Moira composition | `natal_moon_bird_identity`; `nakshatra_bird_mapping`, `natal_identity` | `source_scoped_public`; no default | Pure mapping and natal-identity engine/facade exports plus strict `POST /v1/pancha-pakshi/identity/natal-moon` within the shared thirteen-method/twelve-route family | Profile/manifest hash and exact 54-cell partition; source locator and conflict preservation; all exact/adjacent nakshatra boundaries; one reader-bound TT epoch; strict source-versus-modern provenance and REST fields; DE441 execution is substrate evidence, not a natal oracle; Tamil review is an optional confidence upgrade rather than an admission blocker |

## Admission Bindings

### 1879 Profile Lineage

- 1879 profile schema: `3`
- Manifest schema: `2`
- Stage 2F manifest SHA-256 before the additive 2024 registration:
  `a4fdceee4089c2812d9d77be763c1738152a63231b3f06847ea93383e4a3b327`
- Canonical 1879 profile SHA-256:
  `4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`
- Phase 1 admission decision:
  [`pancha_pakshi_1879_public_admission_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_public_admission_2026_07_20.json)
- Stage 2A additive capability decision:
  [`pancha_pakshi_1879_local_solar_context_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_local_solar_context_2026_07_20.json)
- Stage 2A decision SHA-256:
  `de8e40c161a327695702b9b152f89da8e848f32aafb4d0b155176d28381c9fd2`
- Stage 2B additive capability decision:
  [`pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json)
- Stage 2B decision SHA-256:
  `67cd0ac7cae74556dce702deb29708a5e99a4d19c79184444e3a81d903934449`
- Stage 2C additive capability decision:
  [`pancha_pakshi_1879_fixed_clock_current_cell_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_fixed_clock_current_cell_2026_07_20.json)
- Stage 2C decision SHA-256:
  `b0698a4163a12dc6049cb30907d6e9dfebad790b35cc3661a41d77df89482976`
- Stage 2D additive capability decision:
  [`pancha_pakshi_1879_solar_proportional_materialization_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_solar_proportional_materialization_2026_07_20.json)
- Stage 2D decision SHA-256:
  `e31e0664090b9a38bdcd52b660c04998a0412eab223f4a84fe745b9e54d25383`
- Stage 2E additive capability decision:
  [`pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json)
- Stage 2E decision SHA-256:
  `4ddf0a5fa5b680fa83a7bb3052ecbc5d1a9c2f685c466290f22121dd02724d18`
- Stage 2F source-mapping reading:
  [`pancha_pakshi_1879_lunar_paksha_mapping_reading_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_lunar_paksha_mapping_reading_2026_07_20.json)
- Stage 2F source-mapping evidence SHA-256:
  `9ce3686a90a41af916a370b8d4ec04637f22a1d32f872180c6d8a1b790e25a0e`
- Stage 2F additive capability decision:
  [`pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20.json)
- Stage 2F decision SHA-256:
  `1020b28d5da8d0e823cadd352ea2236c69cbb636660a573eb5d74b8c131bc5d8`

### 2024 Profile And Stage 2G Binding

- 2024 profile schema: `1`
- Canonical 2024 profile SHA-256:
  `e3642f61756ed7b8c413ddfbde2844769aea1994d4e69ae27594b2059b549b6a`
- Canonical current manifest SHA-256:
  `979bb6df8a31d0ff9603ef396b0f569f17ecca6f6dc21def220ad682a425eb61`
- Internet Archive original PDF MD5:
  `abe489a832ac38a0270335b7429776f3`
- Internet Archive original PDF SHA-1:
  `6ddad8f2577883f6859829f534e8ee7b8330ade8`
- Locally verified PDF SHA-256:
  `035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`
- Stage 2G admission decision:
  [`pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20.json)
- Stage 2G decision SHA-256:
  `3da998bc78c6c1fc4ec1c71629dc6b3872725ef25f73965474d5e894deec1575`

- Governing standard:
  [`PANCHA_PAKSHI_RESEARCH_STANDARD.md`](../02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md)
- Evidence narrative:
  [`PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md`](../05_research/PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md)

## Deliberate Nonclaims

The admitted 1879 profile does not compute natal-Moon or nakshatra identity,
source-attested or alternate proportional timing, vinadi subdivisions,
Padu/Bharana/Adhikara birds, condition scores, electional windows, or
cross-witness normalized relationships. Its modern local-solar policy derives
only half and weekday from an explicit instant and location while paksha
remains caller supplied. Its separate fixed-clock policy materializes nominal
offsets from that half's solar start without clipping or stretching them to the
solar end. Its separate current-cell policy selects only within the governing
half's materialized fixed span and returns an explicit
`unmaterialized_solar_half_tail` instead of inventing coverage. It is not a
universal Pancha Pakshi canon. Its separate Stage 2D policy does proportionally
materialize exact nominal fractions across the governing solar half without
attributing that policy to the source. Its Stage 2E selector returns the unique
current proportional cell under exact half-open TT ownership; it does not infer
paksha, create natal identity, or borrow the fixed-clock tail policy. Its
separate Stage 2F product classifies apparent geocentric Moon-Sun elongation and
maps Shukla/waxing to Purva or Krishna/waning to Amara from the named source
locators. It accepts no location and never selects or materializes a schedule,
routes its result into another operation, or claims a universal mapping.

The admitted 2024 profile does not compute an aksara identity, nominal or
materialized schedule, directed relationship, current cell, authority bird,
vinadi subdivision, condition, score, or electional window. Its source table is
not relabelled as an explicit birth-Moon rule: the birth-instant, apparent
geocentric, Lahiri-true, and equal-27-sector composition remains visibly
Moira-owned. Its malformed Amara commentary and the Uromarisi witness remain
non-runtime evidence, and no default or cross-witness normalized canon is
claimed.

## Evidence Classification

- Profile/manifest/evidence-record SHA-256 checks are regression integrity.
- Exact rational closure, schedule bijection, identity partition,
  immutability, source-locator retention, and no-default checks are physical or
  structural invariants of the declared computational object.
- Named 1879 leaf readings are source-specific evidence.
- Local-solar context is a modern Moira composition. Its solar boundary is
  authority-validated against the offline JPL Horizons
  `sun-new-york-equinox` fixture (`0.082 s` sunrise and `0.123 s` sunset
  residuals under a `2 s` gate); this is not a newly discovered 1879 rule or
  an external Pancha Pakshi oracle.
- Fixed-clock materialization is a separately named modern composition. The
  1879 witness governs nominal offsets, the University of Madras *Tamil
  Lexicon* governs the twenty-four-minute nazhigai definition, IERS governs the
  reader-bound TT/SI-second basis, and Stage 2A governs the solar anchor. Exact
  1,440-second offset arithmetic, 43,200-second closure, TT/UT1 endpoint
  coherence, half-open ownership, unclipped topology, and the absence of a
  current-cell judgment are structural invariants, not an external Pancha
  Pakshi oracle.
- Fixed-clock current-cell selection is a separately named modern composition.
  It resolves the governing solar half before applying zero-tolerance,
  half-open membership on reader-bound TT. Cell midpoint and shared-boundary
  ownership, exact sunrise/sunset precedence, prior-half ineligibility, and the
  explicit unmaterialized long-half tail are structural invariants over the
  admitted Stage 2B intervals, not external current-cell parity or a new
  historical or astronomical accuracy claim.
- Solar-proportional materialization is a separately named modern composition.
  It preserves exact nominal endpoint fractions, derives each endpoint from a
  common reader-bound TT anchor and full solar-half span, closes exactly on the
  governing TT/UT1 bounds, and returns 25 positive contiguous half-open cells.
  The route-specific omission distinguishes performed modern composition from
  missing 1879 source attestation. These are structural invariants with
  inherited solar-anchor authority, not external proportional-timing parity or
  a new historical or astronomical accuracy claim.
- Solar-proportional current-cell selection is a separately named modern
  composition over the complete Stage 2D materialization. Solar-half-first
  routing, exact zero-tolerance shared-boundary ownership, one selected non-null
  materialization member, and fail-closed gap/overlap handling are structural
  invariants. DE441 exercises the reader-bound clock path; it is not external
  Pancha Pakshi current-cell parity or a new historical accuracy claim.
- Astronomical paksha inference combines two separately identified evidence
  roles: the 1879 leaves `n16` and `n26` directly attest the profile-label
  mapping, while exact `[0, 180)`/`[180, 360)` ownership is modern Moira policy.
  Synthetic boundary and Panchanga-coherence tests are structural evidence;
  DE441 exercises the shared reader-bound TT and apparent geocentric longitude
  path. This is not an external Pancha Pakshi oracle, phase-event timing claim,
  independent-witness collation, or universal canon. The source reading remains
  machine-assisted pending competent-human Tamil review.
- Stage 2G source evidence consists of the rendered Bogamuni original pages at
  `n52`, `n64`, and `n167`; the normalized profile binds all 54 cells and
  preserves the malformed-commentary rejection. Equal-sector exact-boundary
  and adjacent-representable tests are mathematical invariants. DE441 exercises
  the shared-TT apparent geocentric path. These evidence classes are reported
  separately and none is an external natal-identity oracle.
- The multi-pass review is machine-assisted reconciliation, not an external
  oracle or competent-human Tamil attestation.
- Unadmitted witnesses and rejected text layers remain non-executable until
  independently normalized and admitted as their own products; they do not
  modify either profile merely by appearing in a conflict ledger.
