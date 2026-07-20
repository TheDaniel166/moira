# Pancha Pakshi Profile Ledger

This ledger records public and research Pancha Pakshi profiles by witness,
text layer, and computational product. Registration never blends witnesses and
never creates a default canon.

## Runtime Profiles

| Profile | Witness and text policy | Product and capabilities | Admission | Public surface | Validation boundary |
|---|---|---|---|---|---|
| `agastya_madras_1879_akshara_fixed_clock` | Agastya-attributed Madras 1879 print, IA `dli.rmrl.000451_images`; identified grids govern bird/activity assignments, explicit prose and verse govern chronology; local-solar context, fixed-clock materialization, fixed-clock current-cell selection, and solar-proportional materialization are separately labelled modern Moira policies | `aksara_prasna_operating_schedule`; `aksara_identity`, `nominal_schedule`, `directed_relationships`, `astronomical_context`, `fixed_clock_materialization`, `fixed_clock_current_cell_selection`, `solar_proportional_materialization` | `source_scoped_public`; no default | `moira.pancha_pakshi`, package root, `moira.vedic`, nine `Moira` methods, and nine `/v1/pancha-pakshi` routes | Profile hash/schema and exact-arithmetic integrity, 10 identity symbols, 28 schedules, 700 cells, 20 directed pairs; local-solar boundary ordering, half/weekday selection, UTC-to-UT1 adapter, and polar failure; fixed 1,440-second TT arithmetic, half-open cell closure, UT1 projection, unclipped solar-boundary topology, solar-half-first current-cell ownership, explicit unmaterialized long-half tails, exact proportional fractions, independent TT mapping, and exact governing-half closure; machine-assisted source reading, no competent-human Tamil sign-off, no independent-witness collation, no external Pancha Pakshi oracle |

## Admission Binding

- Profile schema: `2`
- Manifest schema: `2`
- Canonical manifest SHA-256:
  `6dbbf05383c7a4eb3eadebf70fdb1130ab5081ef83175bc387755ffda4db9121`
- Canonical profile SHA-256:
  `876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`
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
- Governing standard:
  [`PANCHA_PAKSHI_RESEARCH_STANDARD.md`](../02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md)
- Evidence narrative:
  [`PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md`](../05_research/PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md)

## Deliberate Nonclaims

The admitted profile does not compute natal-Moon or nakshatra identity,
astronomical or lunar paksha, source-attested or alternate proportional timing,
proportional current-cell selection, vinadi subdivisions,
Padu/Bharana/Adhikara birds, condition scores, electional windows, or
cross-witness normalized relationships. Its modern local-solar policy derives
only half and weekday from an explicit instant and location while paksha
remains caller supplied. Its separate fixed-clock policy materializes nominal
offsets from that half's solar start without clipping or stretching them to the
solar end. Its separate current-cell policy selects only within the governing
half's materialized fixed span and returns an explicit
`unmaterialized_solar_half_tail` instead of inventing coverage. It is not a
universal Pancha Pakshi canon. Its separate Stage 2D policy does proportionally
materialize exact nominal fractions across the governing solar half, but does
not attribute that policy to the source or select a current cell.

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
- The multi-pass review is machine-assisted reconciliation, not an external
  oracle or competent-human Tamil attestation.
- Later witnesses remain metadata-only until independently normalized and
  admitted as their own products; they do not corroborate or modify this
  profile merely by appearing in the conflict ledger.
