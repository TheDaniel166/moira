# Pancha Pakshi Profile Ledger

This ledger records public and research Pancha Pakshi profiles by witness,
text layer, and computational product. Registration never blends witnesses and
never creates a default canon.

## Runtime Profiles

| Profile | Witness and text policy | Product and capabilities | Admission | Public surface | Validation boundary |
|---|---|---|---|---|---|
| `agastya_madras_1879_akshara_fixed_clock` | Agastya-attributed Madras 1879 print, IA `dli.rmrl.000451_images`; identified grids govern bird/activity assignments, explicit prose and verse govern chronology; leaves `n16`, `n21`, `n26`, and `n31` govern the four first-samam EAT-seed rows, while `n16` and `n26` also map waxing/Purva and waning/Amara; astronomical classification, local-solar context, both timing materializations/current-cell selectors, and the Stage 2N/2O cross-profile joins are separately labelled modern Moira policies | `aksara_prasna_operating_schedule`; `aksara_identity`, `nominal_schedule`, `first_eat_bird_mapping`, `directed_relationships`, `astronomical_context`, `astronomical_paksha_inference`, `fixed_clock_materialization`, `fixed_clock_current_cell_selection`, `solar_proportional_materialization`, `solar_proportional_current_cell_selection` | `source_scoped_public`; no default | `moira.pancha_pakshi`, package root, `moira.vedic`, and the shared family of eighteen `Moira` methods and seventeen `/v1/pancha-pakshi` routes; ten capability-gated computations plus the two shared discovery/info methods and the two separate cross-profile compositions | Profile hash/schema and exact-arithmetic integrity, 10 identity symbols, 28 first-EAT seeds, 28 schedules, 700 cells, 20 directed pairs; exact seed/schedule parity and canonical locator binding; direct lunar-half mapping locators, exact geocentric phase-half ownership, single reader-bound TT, and strict no-location/no-routing inference; local-solar boundary ordering, half/weekday selection, UTC-to-UT1 adapter, and polar failure; fixed/proportional interval invariants; Stage 2N all-samam subject-bird uniqueness; Stage 2O explicit timing selection, exact TT normalization, boundary ownership, and fixed-tail preservation; machine-assisted source reading with explicit uncertainty and no human-review dependency, separate-publication Uromarisi corroboration with unestablished textual-lineage independence, no external Pancha Pakshi oracle |
| `bogamuni_chennai_2024_nakshatra_natal_identity` | Bogamuni-attributed 2024 sixth edition, IA `acc.-no.-44757-panjapatchi-sashthiram-2024`; Purva table at `n52`, governing Amara verse at `n64`, phase binding at `n167`; malformed adjacent Amara commentary is rejected under declared verse precedence; birth-Moon application, Lahiri true ayanamsa, and equal-27-sector placement are explicitly modern Moira composition | `natal_moon_bird_identity`; `nakshatra_bird_mapping`, `natal_identity` | `source_scoped_public`; no default | Pure mapping and natal-identity engine/facade exports plus strict `POST /v1/pancha-pakshi/identity/natal-moon` within the shared eighteen-method/seventeen-route family | Profile/manifest hash and exact 54-cell partition; source locator and conflict preservation; all exact/adjacent nakshatra boundaries; one reader-bound TT epoch; strict source-versus-modern provenance and REST fields; DE441 execution is substrate evidence, not a natal oracle; machine-assisted source reading has no human-review dependency |
| `bogamuni_chennai_2024_padu_bird_mapping` | Bogamuni-attributed 2024 sixth edition; governing Purva weekday stanza at `n52`, governing Amara material at `n60`, internally repeated combined table at `n157`, and restating commentary at `n158`; Paksha stanzas govern and the repeated layers confirm | `padu_bird_mapping`; `padu_bird_mapping` only | `source_scoped_public`; no default | Pure engine/package/facade lookup plus strict `POST /v1/pancha-pakshi/roles/padu` within the shared eighteen-method/seventeen-route family | Exact 14-cell Paksha-by-weekday table, no day/night axis, three canonical locators per result, immutable source semantics/provenance, and strict rejection of temporal, schedule, `RULE`, `first_eat_bird`, Adhikara/Bharana, condition, score, and forecast semantics; Uromarisi/Bogar material is unbound research context, not runtime or decision input |
| `bogamuni_chennai_2024_sookshma_temporal_selector` | Bogamuni-attributed 2024 editorial layers; six-nazhigai samam context at `n156`, weighted Sookshma vector and cyclic rows at `n157`, and distinct Eka Sookshma equal-fifths rule at `n168` | `sookshma_temporal_selector`; `sookshma_temporal_selection` only | `source_scoped_public`; no default and automatic policy selection forbidden | Pure exact selector through engine/package/facade plus strict `POST /v1/pancha-pakshi/sookshma/select` | Mandatory explicit policy; exact `Fraction` input in `[0, 6)`; weighted rotations close exactly to six; equal fifths are exact `6/5` ordinal-only cells with no invented activity; strict half-open uniqueness; no datetime, astronomy, schedule, Uromarisi outcome, condition, score, window, or forecast composition |

## Admission Bindings

### 1879 Profile Lineage

- 1879 profile schema: `3`
- Manifest schema: `2`
- Stage 2F manifest SHA-256 before the additive 2024 registration:
  `a4fdceee4089c2812d9d77be763c1738152a63231b3f06847ea93383e4a3b327`
- Current canonical 1879 profile SHA-256 after removing the legacy human-review
  dependency token:
  `d80d205716eb9f24a2a23949c6df241a1aba251749efa94d3b20fa36be0258f4`
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
- Canonical Stage 2G manifest SHA-256:
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

### 2024 Padu Profile And Stage 2H Binding

- Padu profile schema: `1`
- Canonical Padu profile SHA-256:
  `5de0d1e28d47fad8be6a2a1ab648f2ed71eaf742be2775d166ea44981e96ff10`
- Canonical Stage 2H manifest SHA-256:
  `eae9fc471da08eccf24515ef12cdaf59330aa1b7ad7f9d43432c7a1482704a03`
- Internet Archive original PDF MD5:
  `abe489a832ac38a0270335b7429776f3`
- Internet Archive original PDF SHA-1:
  `6ddad8f2577883f6859829f534e8ee7b8330ade8`
- Locally verified PDF SHA-256:
  `035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`
- Stage 2H admission decision:
  [`pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20.json)
- Stage 2H decision SHA-256:
  `9ea7c871643bb8fc68d420223d0090ca91699154c761c67ccaf9201f401906cd`

### 1879 First-EAT Capability And Stage 2I Binding

- Canonical 1879 profile SHA-256, unchanged:
  `4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`
- Prior Stage 2H manifest SHA-256:
  `eae9fc471da08eccf24515ef12cdaf59330aa1b7ad7f9d43432c7a1482704a03`
- Canonical Stage 2I manifest SHA-256:
  `d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8`
- Governing 1879 leaves: Purva day `n16`, Purva night `n21`, Amara day
  `n26`, and Amara night `n31`
- Stage 2I admission decision:
  [`pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20.json)
- Stage 2I decision SHA-256:
  `83c9bc0a423c09ccc113007625fee4a7d6b9ee1e890827f71595c96c3f826807`
- Uromarisi 1934 role: all-28-cell separate-publication corroboration at
  `n6` and `n36`-`n37`; textual-lineage independence is not established and
  the publication supplies no runtime cell

### Stage 2J Vinadi Research Binding

- Admission status: `research_only`; no profile or capability admitted
- Stage 2J research decision:
  [`pancha_pakshi_uromarisi_vinadi_stage2j_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_uromarisi_vinadi_stage2j_research_2026_07_21.json)
- Stage 2J decision SHA-256:
  `d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243`
- Bound Stage 2I manifest SHA-256, unchanged:
  `d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8`
- Recovered object: five explicit vinadi ordinal positions beneath each of
  EAT, WALK, RULE, SLEEP, and DIE
- 1922 witness SHA-256 and governing locators:
  `51b4b34890412fd57011aebe0c1ab22ab1800e5035a84bbbb9330ea0f6597741`;
  PDF pages 115 and 116
- 1932 witness SHA-256 and governing locators:
  `dbd12d7e26f39ca7f9650a17311b5483eb478844144544a2cbb11aac7c3d6243`;
  PDF pages 5, 88, and 89
- 1934 witness SHA-256 and governing locators:
  `e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`;
  PDF pages 115 through 117
- 2024 editorial comparator SHA-256 and governing locators:
  `035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`;
  PDF pages 157, 158, and 169
- Temporal selector candidates: exact weighted Sūkṣma vector
  `(3/2, 5/4, 2, 3/4, 1/2)` closing to six nazhigai, and separately named
  Eka Sūkṣma equal fifths
- Selector default, binding to Uromarisi outcomes, outcome normalization,
  runtime composition, and public exposure: not admitted; no human-language
  reviewer is required

### 2024 Sookshma Selector Profile And Stage 2K Binding

- Admission status: `source_scoped_public`; no default
- Profile: `bogamuni_chennai_2024_sookshma_temporal_selector`
- Canonical profile SHA-256:
  `596c003c62ebbda913ca28aef318d77cb7b1cf42d92d3b1b7a20a44a01dd6526`
- Canonical current manifest SHA-256:
  `584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`
- Stage 2K admission decision:
  [`pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_2026_07_21.json)
- Stage 2K decision SHA-256:
  `10bcfbd70dda28fd399e5c95b8bfa237b8e48f3b2cb20901fc21e0261a73cf70`
- Policies: explicit weighted Sookshma and explicit Eka Sookshma equal fifths;
  neither is a default or an automatic substitute for the other
- Uromarisi outcome binding, outcome interpretation, civil-clock routing,
  astronomy, schedule composition, condition, scoring, electional search, and
  forecasting: not performed
- Human-language reviewer dependency: none

### Stage 2L Independent-Witness Collation Gate

- Admission status: `research_only`; no profile or capability admitted
- Stage 2L research decision:
  [`pancha_pakshi_independent_witness_stage2l_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_independent_witness_stage2l_research_2026_07_21.json)
- Stage 2L decision SHA-256:
  `5534ddde1c0b87fa5fc3332112d02fd1c48c38e0a79f45f4a75a3e3c728a4c34`
- Bound Stage 2K manifest SHA-256, unchanged:
  `584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`
- Sarasvati Mahal 2014 sixth-edition PDF SHA-256 and governing locators:
  `894f88c3381f026aa1963861dd30e1f74039aa32a89fd84015efb3a098dc5366`;
  PDF pages 2, 4, 30, 31, 33, 37, 88, 89, 136, 209, and 302
- Narasimhan 2018 secondary-guide PDF SHA-256:
  `1694ca303d5f49a13b9269fe9ee1e39607e1709df756ff6bbdf137bc1c589243`;
  no bibliography or primary-text lineage found
- Rejected Canva/AI-marked guide SHA-256:
  `3498501cf3fd43ec2b0f2b8dab497b6c431713af1373f229a496bb8c7f6b7b9d`;
  unrelated tarot material occurs on rendered pages 6 and 10
- Exact agreement: all seven Purva-day first-EAT seeds and the waxing-day
  duration vector
- Preserved conflict: the institutional compilation and secondary guide use
  three additional regime-specific vectors that disagree with the 1879
  profile's uniform vector
- Textual-lineage independence and `corroborated_public`: not established;
  runtime and manifest unchanged; no human-language reviewer required

### Stage 2M Ramadevar Candidate Identity And Access Gate

- Admission status: `research_only`; no profile or capability admitted
- Stage 2M research decision:
  [`pancha_pakshi_ramadevar_candidate_stage2m_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_ramadevar_candidate_stage2m_research_2026_07_21.json)
- Stage 2M decision SHA-256:
  `921e604bcd81298aa6eb903acc967e68cfcf6e743c7d1379788ff9996212c6db`
- Bound Stage 2L decision SHA-256, unchanged:
  `5534ddde1c0b87fa5fc3332112d02fd1c48c38e0a79f45f4a75a3e3c728a4c34`
- Bound Stage 2K manifest SHA-256, unchanged:
  `584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`
- Commissionerate catalog PDF SHA-256:
  `8bf4541aa46e3526d3218b1c35ae7bf174298ff6e29e86d9e10e7389dd5b5e4b`;
  PDF pages 1, 2, and 52 identify the holding collection and exact serial
  `859`, manuscript `A5`, title `Ramadevar Panchapakshi`
- G.O.M.L. 1999 descriptive catalog PDF SHA-256:
  `4ff7f72891c6d53c3eaac502f1f1217a0cb950b60611524bfaff854d38b03ec4`;
  PDF pages 93-94 classify `R.8978 Ramadevar Patchini` as gnana, breath, and
  yoga rather than Pancha Pakshi computation
- British Library EAP `EAP1217/1/2851` is an eighteenth-century 108-poem
  philosophy and ashtanga-yoga Patchani witness, not the `A5` candidate
- `A5` content, product comparability, copying history, textual independence,
  and `corroborated_public`: not assessable or established
- Runtime and manifest unchanged; no human-language reviewer required

### Stage 2N Explicit Schedule-To-Sookshma Composition

- Admission kind: explicit modern cross-profile composition; no new profile or
  profile capability
- Stage 2N decision:
  [`pancha_pakshi_schedule_sookshma_composition_stage2n_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_schedule_sookshma_composition_stage2n_2026_07_21.json)
- Stage 2N decision SHA-256:
  `084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9`
- Bound 1879 schedule profile SHA-256, unchanged:
  `d80d205716eb9f24a2a23949c6df241a1aba251749efa94d3b20fa36be0258f4`
- Bound 2024 selector profile SHA-256, unchanged:
  `596c003c62ebbda913ca28aef318d77cb7b1cf42d92d3b1b7a20a44a01dd6526`
- Bound manifest SHA-256, unchanged:
  `584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`
- Policy: `explicit_schedule_samam_subject_bird_sookshma_v1`, explicitly
  `modern_moira_policy_not_source_claim`
- Mandatory axes: both profile IDs, source Paksha, half, weekday, samam
  `1..5`, subject bird, one Stage 2K selector policy, and exact elapsed
  nazhigai `Fraction`
- Structural coverage: all four Paksha/half regimes, seven weekdays, five
  samams, and five subject birds; each selected samam must contain exactly one
  parent cell for that bird
- Clock/civil-time routing, astronomy, Uromarisi outcome binding, outcome
  interpretation, condition, score, electional search, and forecasting: not
  performed
- A5 acquisition remains optional future corroboration; no human-language
  reviewer required

### Stage 2O Explicit Civil-Time-To-Sookshma Routing

- Admission kind: explicit modern routing composition; no new profile or
  profile capability
- Stage 2O decision:
  [`pancha_pakshi_civil_time_sookshma_selection_stage2o_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_civil_time_sookshma_selection_stage2o_2026_07_21.json)
- Stage 2O decision SHA-256:
  `2ea686e774ba4468c0515f621771b8a142c79f04d89b69839f482e05c37b40df`
- Bound Stage 2N decision SHA-256:
  `084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9`
- Bound manifest SHA-256, unchanged:
  `584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`
- Policy: `civil_time_materialized_samam_to_stage2n_v1`, explicitly
  `modern_moira_policy_not_source_claim`
- Mandatory axes: both profile IDs, aware instant, latitude, longitude,
  source Paksha, subject bird, one timing policy, and one Stage 2K selector
  policy
- Derivation: current materialized cell supplies samam; stored requested,
  samam-start, and samam-end reader-bound TT values are lifted exactly to
  rationals and normalized to six nazhigai
- Fixed-clock long-half tail remains explicit with null composition; automatic
  proportional fallback is forbidden
- Astronomical paksha inference, Uromarisi outcome binding, condition, score,
  electional search, and forecasting: not performed
- Four profiles, their capabilities, and manifest: unchanged; no
  human-language reviewer required

### Stage 2P Research-Only Uromarisi Illness Grid

- Admission kind: research-only structural locator recovery; no profile or
  capability
- Stage 2P decision:
  [`pancha_pakshi_uromarisi_illness_grid_stage2p_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_uromarisi_illness_grid_stage2p_research_2026_07_21.json)
- Stage 2P decision SHA-256:
  `449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2`
- Primary 1934 Uromarisi PDF SHA-256:
  `e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`
- Inspected range: rendered PDF pages `115–126`, printed pages `113–124`
- Recovered object: illness context, five parent activities by five explicit
  vinadi ordinals, exactly 25 unique locator cells
- Cell verses: `230–239` and `241–255`; verse `240` is an intervening
  transition and verse `256` begins the separate illness-duration section
- Payload boundary: activity, ordinal, verse, and page spans only; no copied
  Tamil expression, translation, normalized outcome, condition, score,
  medical advice, electional judgment, or forecast
- Selector boundary: neither Stage 2K policy is attributed to Uromarisi and
  Stage 2O routing remains unbound
- Four profiles, manifest, engine, facade, and REST surface: unchanged; no
  human-language reviewer required

### Stage 2Q Research-Only Uromarisi EAT Semantic Atoms

- Admission kind: research-only five-cell semantic-transcription pilot; no
  profile or capability
- Stage 2Q decision:
  [`pancha_pakshi_uromarisi_eat_semantics_stage2q_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_uromarisi_eat_semantics_stage2q_research_2026_07_21.json)
- Stage 2Q decision SHA-256:
  `7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9`
- Bound predecessor: exact Stage 2P decision SHA-256
  `449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2`
- Reviewed cells: EAT ordinals `1–5`, verses `230–234`, rendered PDF pages
  `116–118`, printed pages `114–116`
- Source-stated duration atoms: `4 or 5`, `7`, `9`, `13`, and `15` days
- Preserved distinctions: separate devotional-response categories, medicine
  and `prithivi` references, unresolved relation clauses, and cell-local
  uncertainty
- Nonclaims: no medical-truth validation, diagnosis, prognosis, advice,
  generic good/bad label, condition or numeric score, or full translation
- Selector and runtime boundary: no Stage 2K attribution, Stage 2O routing,
  profile, manifest, engine, facade, or REST change; no human-language reviewer
  required

### Stage 2R Research-Only Uromarisi WALK Semantic Atoms

- Admission kind: research-only five-cell semantic-transcription extension;
  no profile or capability
- Stage 2R decision:
  [`pancha_pakshi_uromarisi_walk_semantics_stage2r_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_uromarisi_walk_semantics_stage2r_research_2026_07_21.json)
- Stage 2R decision SHA-256:
  `361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6`
- Bound predecessor: exact Stage 2Q decision SHA-256
  `7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9`
- Reviewed cells: WALK ordinals `1–5`, verses `235–239`, rendered PDF pages
  `118–120`, printed pages `116–118`
- Source-stated time atoms: `10` days, `15` days, within `20` days, `25` days,
  and within one month; no month-to-day conversion
- Dispositions: resolution, abatement, and timed progression without explicit
  resolution remain distinct
- Preserved distinctions: source deity titles, prescribed actions and stated
  mediations, medicine or physician and Navagraha-dosha references,
  water-clause roles,
  unresolved relations, and cell-local uncertainty
- Nonclaims: no medical-truth validation, diagnosis, prognosis, advice,
  generic good/bad label, condition or numeric score, or full translation
- Selector and runtime boundary: no Stage 2K attribution, Stage 2O routing,
  profile, manifest, engine, facade, or REST change; no human-language reviewer
  required

### Stage 2S Research-Only Uromarisi RULE Semantic Atoms

- Admission kind: research-only five-cell semantic-transcription extension;
  no profile or capability
- Stage 2S decision:
  [`pancha_pakshi_uromarisi_rule_semantics_stage2s_research_2026_07_21.json`](../../tests/fixtures/pancha_pakshi_uromarisi_rule_semantics_stage2s_research_2026_07_21.json)
- Stage 2S decision SHA-256:
  `85142480188a00ddec3de6f192a36025f282ca0eefa4643a6f1d74da4cec811d`
- Bound predecessor: exact Stage 2R decision SHA-256
  `361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6`
- Reviewed cells: RULE ordinals `1–5`, verses `241–245`, rendered PDF pages
  `120–122`, printed pages `118–120`
- Source-stated time atoms: `3` days, `5` days, within `8` days, `10` days,
  and `12` days; the upper bound is not rewritten as exact
- Disposition: all five state resolution
- Preserved distinctions: source deity titles, prescribed actions,
  fire-clause roles, Saturn-dosha references, effect language, one surface
  no-enmity statement, and cell-local uncertainty
- Nonclaims: no medical-truth validation, diagnosis, cause, symptom, advice,
  generic good/bad label, condition or numeric score, or full translation
- Selector and runtime boundary: no Stage 2K attribution, Stage 2O routing,
  activity-relation binding, profile, manifest, engine, facade, or REST change;
  no human-language reviewer required

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
Its Stage 2I lookup exposes only the selected generator's first-samam EAT seed.
It does not materialize a schedule, describe a whole day, or create Padu,
authority, Adhikara/Bharana, condition, score, or forecast semantics.

Stage 2J did not add vinadi semantics to an admitted profile. Its recovered
axis accepts explicit ordinal labels as research evidence, while its weighted
Sūkṣma and equal-fifths Eka Sūkṣma selectors remain distinct, unbound research
candidates at that research stage. Stage 2K now admits those two Bogamuni
selectors only as explicit, separate temporal policies; it does not admit a
default, Uromarisi binding, translation-backed outcome, current-cell
composition, condition, score, electional judgment, or forecast. Stage 2N
separately admits only an explicit nominal-schedule join at a caller-supplied
samam offset; it still performs no clock routing or outcome interpretation.

The admitted 2024 profile does not compute an aksara identity, nominal or
materialized schedule, directed relationship, current cell, authority bird,
vinadi subdivision, condition, score, or electional window. Its source table is
not relabelled as an explicit birth-Moon rule: the birth-instant, apparent
geocentric, Lahiri-true, and equal-27-sector composition remains visibly
Moira-owned. Its malformed Amara commentary and the Uromarisi witness remain
non-runtime evidence, and no default or cross-witness normalized canon is
claimed.

The admitted Padu profile computes only one explicit Paksha-by-weekday lookup.
It has no day/night axis and does not infer Paksha or weekday from an instant.
It does not compute an identity, schedule, current cell, authority bird,
condition, score, or electional window. Padu is not the schedule's `RULE`
activity and is not relabelled as `first_eat_bird`, Adhikara, or Bharana. The
primary witnesses' eating-bird and authority-day labels remain distinct.
Separately observed Uromarisi/Bogar material is not bound by the Stage 2H
profile or decision and does not expand the runtime product.

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
  machine-assisted with its uncertainty visible and no human-review dependency.
- Stage 2G source evidence consists of the rendered Bogamuni original pages at
  `n52`, `n64`, and `n167`; the normalized profile binds all 54 cells and
  preserves the malformed-commentary rejection. Equal-sector exact-boundary
  and adjacent-representable tests are mathematical invariants. DE441 exercises
  the shared-TT apparent geocentric path. These evidence classes are reported
  separately and none is an external natal-identity oracle.
- Stage 2H source evidence consists of the rendered Bogamuni original pages at
  `n52`, `n60`, `n157`, and `n158` and the normalized 14-cell projection. Exact
  one-cell-per-Paksha/weekday completeness, no-day/night shape, canonical
  locator binding, immutability, capability isolation, and strict request
  shape are structural invariants. Separately observed Uromarisi/Bogar material
  is not fixture-bound or imported into the runtime table, and none of this
  evidence validates a
  condition, scoring, or electional product.
- Stage 2I source evidence consists of the rendered 1879 leaves `n16`, `n21`,
  `n26`, and `n31` and the already normalized 28-cell generator seed table.
  Same-witness grids confirm the mapping; exact completeness, canonical
  locator binding, parity with the existing schedule's first-EAT field and
  first EAT cell, immutability, capability isolation, and strict request shape
  are structural invariants. Uromarisi 1934 corroborates all cells as a
  separate publication, but its textual-lineage independence is not
  established and it contributes no runtime data or universal-canon proof.
- Stage 2J source evidence consists of rendered inspection of the
  Uromarisi-attributed 1922 PDF pages 115 and 116, 1932 PDF pages 5, 88, and 89,
  and separate 1934 PDF pages 115 through 117. Cross-edition verse numbering
  and first-through-fifth organization corroborate a five-position ordinal
  axis. The 2024 editorial comparator at PDF pages 157, 158, and 169 separately
  attests weighted Sūkṣma and equal-fifths Eka Sūkṣma selectors. Their conflict,
  any Uromarisi binding, textual-lineage independence, and normalized outcomes
  remain unadmitted. Hash, exact-rational, and surface-absence tests are
  regression and structural evidence only; they are not a prognostic oracle or
  public capability.
- Stage 2L source evidence consists of rendered inspection of the Sarasvati
  Mahal 2014 sixth-edition PDF at pages 2, 4, 30, 31, 33, 37, 88, 89, 136,
  209, and 302, plus the two supplied modern guides. Exact seven-cell and
  rational-vector comparisons preserve both agreement and conflict. Hash,
  manifest-absence, and surface-absence checks are regression and structural
  evidence. The collation establishes neither textual-lineage independence
  nor `corroborated_public`; the rejected Canva guide contributes no doctrine.
- The multi-pass review is machine-assisted reconciliation with explicit
  uncertainty and no human-review dependency; it is not an external oracle or
  linguistic-authority claim.
- Unadmitted witnesses and rejected text layers remain non-executable until
  independently normalized and admitted as their own products; they do not
  modify any admitted profile merely by appearing in a conflict ledger.
