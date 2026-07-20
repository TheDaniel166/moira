# Pancha Pakshi Admission Evidence — 2026-07-20

## Stage 2G Natal-Moon Identity Addendum

Stage 2G admits the separate
`bogamuni_chennai_2024_nakshatra_natal_identity` profile with product kind
`natal_moon_bird_identity`, capabilities `nakshatra_bird_mapping` and
`natal_identity`, `source_scoped_public` status, and no default. The
[`Stage 2G admission decision`](../../tests/fixtures/pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20.json)
has canonical SHA-256
`3da998bc78c6c1fc4ec1c71629dc6b3872725ef25f73965474d5e894deec1575`.
It binds profile SHA-256
`e3642f61756ed7b8c413ddfbde2844769aea1994d4e69ae27594b2059b549b6a`
and manifest SHA-256
`979bb6df8a31d0ff9603ef396b0f569f17ecca6f6dc21def220ad682a425eb61`.

The primary witness is the Bogamuni-attributed 2024 sixth edition catalogued by
Internet Archive as
[`acc.-no.-44757-panjapatchi-sashthiram-2024`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024).
The inspected original PDF is `Acc.No.44757-PanjapatchiSashthiram-2024.pdf`,
archive MD5 `abe489a832ac38a0270335b7429776f3`, archive SHA-1
`6ddad8f2577883f6859829f534e8ee7b8330ade8`, and locally verified SHA-256
`035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`.
Rendered original-page inspection—not OCR alone—established the complete Purva
nakshatra-bird table at IA leaf `n52`, the complete Amara verse at `n64`, and
the source phase-to-Purva/Amara binding at `n167`.

The commentary adjacent to the Amara verse is internally malformed: it
duplicates Shravana and omits Revati. Stage 2G declares
`verse_precedence_for_nakshatra_partition`, uses the complete verse for the
27-cell Amara partition, and preserves the commentary at `n64` as rejected
conflict evidence. It does not infer the omitted cell, repair the commentary by
symmetry, or blend text layers. The Uromarisi-attributed 1934 witness at
[`kvc-0354-vinaadi-pajasapatchi-mulamum-1934`](https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934)
corroborates the Purva grouping at leaf `n18` and independently exhibits
malformed Amara commentary at `n61`. That bounded corroboration does not govern
the runtime table or raise the entire profile to `corroborated_public`.

`PanchaPakshiNakshatraBirdMapping` preserves the pure 2-by-27 source table and
states `nakshatra_bird_table_not_explicitly_natal_moon`. The source witnesses
attest phase labels and nakshatra birds; they do not explicitly prescribe a
birth-Moon calculation, Lahiri ayanamsa, or an equal-27-sector numerical
taxonomy. `PanchaPakshiNatalMoonIdentityPolicy` therefore exposes
`composition_status="modern_moira_policy_not_source_claim"` and the sole policy
ID `bogamuni_2024_apparent_lahiri_natal_moon_identity_v1`.

The modern composition converts one explicit UT1 instant once to reader-bound
TT. Apparent geocentric Sun and Moon longitudes in the true ecliptic of date
determine the half-open Shukla/Krishna phase and source Paksha. The same TT epoch
governs Lahiri true ayanamsa and the sidereal Moon. Twenty-seven equal half-open
`40/3`-degree sectors assign exact internal boundaries to the following
nakshatra. A maximum-one-ULP-below recovery exists only to recover the binary
representation of an exact mathematical boundary and is not a tolerance band.

The public surfaces are the kernel-free pure mapping function and facade method,
the kernel-backed `pancha_pakshi_natal_moon_identity_at(...)` and
`Moira.pancha_pakshi_natal_moon_identity(...)`, and strict
`POST /v1/pancha-pakshi/identity/natal-moon`. REST accepts only `profile_id`,
aware `dt`, and the exact policy ID. It rejects location, supplied
paksha/nakshatra/bird/ayanamsa, schedule/current-cell controls, scoring, and
forecast inputs. The result exposes every astronomical and sidereal
intermediate, phase and bird mappings, locators, modern composition status,
provenance, and omissions; no schedule routing occurs.

Validation keeps its evidence classes separate. The named pages and exact
54-cell projection are source-table evidence. Exact-boundary and
adjacent-representable tests are mathematical invariants. DE441 executes the
apparent geocentric reader-bound TT path, but is not a Pancha Pakshi or
natal-identity oracle. Facade, serializer, REST, OpenAPI, export, profile/hash,
capability, and immutable-vessel tests protect the public contract. Competent
human Tamil review remains a welcome confidence upgrade, not a blocker to this
narrow source-scoped admission or a prerequisite for publishing the API.

The source-artifact boundary remains unchanged. The PDFs and rendered research
pages are not bundled; Moira distributes only independently normalized symbolic
rules, source identities and locators, Moira-authored policy/schema/prose, and
validation metadata. The 1879 aksara profile remains distinct and unchanged.

## Stage 2F Astronomical Paksha Inference Addendum

Stage 2F admits `astronomical_paksha_inference` for the same explicitly named
`source_scoped_public` profile. Unlike Stages 2A-E, it adds a normalized source
fact to the profile: machine-assisted visual reading of the exact 1879 witness
directly maps waxing to Purva at IA leaf `n16` and waning to Amara at `n26`.
The frozen
[`source-reading record`](../../tests/fixtures/pancha_pakshi_1879_lunar_paksha_mapping_reading_2026_07_20.json)
has canonical SHA-256
`9ce3686a90a41af916a370b8d4ec04637f22a1d32f872180c6d8a1b790e25a0e`.
Its status remains
`machine_assisted_visual_reading_pending_competent_tamil_review`; it does not
claim independent-witness corroboration or a universal Pancha Pakshi vocabulary.

The chained
[`Stage 2F admission decision`](../../tests/fixtures/pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20.json)
has canonical SHA-256
`1020b28d5da8d0e823cadd352ea2236c69cbb636660a573eb5d74b8c131bc5d8`.
It freezes the Stage 2E decision at
`4ddf0a5fa5b680fa83a7bb3052ecbc5d1a9c2f685c466290f22121dd02724d18`,
the prior manifest at
`d2b5f8f1ae7e067d257eeb24b533be1d33349446d56d361ea59f4a71472eca70`,
and the prior profile at
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`.
The schema-3 profile digest becomes
`4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`
and the schema-2 manifest digest becomes
`a4fdceee4089c2812d9d77be763c1738152a63231b3f06847ea93383e4a3b327`.
Admission status, product kind, and `default_selection_allowed=false` remain
unchanged.

The governing objects are `PanchaPakshiAstronomicalPakshaInference`, the
`PanchaPakshiAstronomicalPaksha` enum, and immutable
`PanchaPakshiAstronomicalPakshaInferencePolicy`. The only admitted policy is
`apparent_geocentric_moon_sun_longitude_paksha_half_open_v1`. It converts the
explicit UT1 instant once to reader-bound TT and evaluates apparent geocentric
Sun and Moon longitudes in the true ecliptic of date on that same coordinate.
Normalized `Moon - Sun` longitude assigns `[0, 180)` to Shukla/waxing/Purva and
`[180, 360)` to Krishna/waning/Amara. Exact `0` belongs to Shukla/Purva and exact
`180` to Krishna/Amara; tolerance, snapping, civil-day override, and
topocentric override are absent. Ayanamsa has no role because a common longitude
offset cancels from the phase difference.

The low-level engine, facade, and REST surfaces are
`pancha_pakshi_astronomical_paksha_at(...)`,
`Moira.pancha_pakshi_astronomical_paksha(...)`, and
`POST /v1/pancha-pakshi/context/astronomical-paksha`. The transport request
accepts only explicit `profile_id`, aware `dt`, and the exact policy ID. There is
no location or caller-supplied paksha. The result publishes UT1/TT, both
longitudes, normalized elongation, astronomical half, source-mapped profile
label, exactly one direct mapping locator, policy, and provenance. It does not
select or materialize a schedule, choose a current cell, route its result into
another operation, or infer natal identity.

Stage 2F validation is intentionally partitioned. The leaf readings establish
only the source-label mapping. Synthetic `0`/`180` and adjacent-representable
cases establish the modern half-open classifier; DE441 exercises the actual
reader-bound astronomical path; and Panchanga coherence checks confirm that
tithi and karana use the direct tropical Moon-Sun difference, where common
ayanamsa cancels, rather than separately rounded sidereal operands. Facade,
transport, OpenAPI, capability, immutable-vessel, schema/hash, and locator
checks protect the public contract. None of this is an external Pancha Pakshi
oracle, a new phase-event timing accuracy claim, competent-human Tamil sign-off,
or independent-witness collation.

The standing source-artifact boundary is unchanged. Stage 2F distributes only
normalized facts, locators, Moira-authored policy, and validation metadata. It
does not package an archival scan, PDF, OCR, page image, copied source
expression, or third-party translation.

## Stage 2E Solar-Proportional Current-Cell Addendum

Stage 2E admits one further capability,
`solar_proportional_current_cell_selection`, for the same
`source_scoped_public` profile. The profile document remains unchanged at
canonical SHA-256
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`,
and default selection remains forbidden. The chained decision is recorded in
[`pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json),
whose canonical SHA-256 is
`4ddf0a5fa5b680fa83a7bb3052ecbc5d1a9c2f685c466290f22121dd02724d18`.
It freezes the Stage 2D decision at SHA-256
`e31e0664090b9a38bdcd52b660c04998a0412eab223f4a84fe745b9e54d25383`,
the prior manifest at SHA-256
`6dbbf05383c7a4eb3eadebf70fdb1130ab5081ef83175bc387755ffda4db9121`,
and binds the new manifest at SHA-256
`d2b5f8f1ae7e067d257eeb24b533be1d33349446d56d361ea59f4a71472eca70`.

The governing object is
`PanchaPakshiSolarProportionalCurrentCellSelection`, with immutable
`PanchaPakshiSolarProportionalCurrentCellSelectionPolicy`. Its only admitted
policy is
`solar_proportional_current_cell_half_open_solar_precedence_v1`, explicitly a
modern deterministic Moira selection policy rather than an 1879 source claim.

Stage 2A first resolves the governing half-open solar half. Stage 2D then
materializes that half's complete 25-cell proportional partition with the same
configured reader. The requested UT1 instant is converted once to reader-bound
TT and tested by exact `start_jd_tt <= requested_jd_tt < end_jd_tt` membership
with `0.0 s` tolerance. The anchor belongs to cell zero, every shared endpoint
belongs to the following cell, and exact sunrise or sunset is routed into the
new governing half before selection.

Complete Stage 2D coverage makes `selected` the only lawful status and requires
one non-null tuple member. Zero or multiple matches fail closed. Stage 2E has no
fixed-clock tail state and performs no clipping, wrapping, repetition,
borrowing, fixed-clock mixing, fallback, paksha inference, or natal identity.
Paksha remains an explicit caller-supplied source label.

The low-level engine, facade, and REST surfaces are respectively
`pancha_pakshi_solar_proportional_current_cell_at(...)`,
`Moira.pancha_pakshi_solar_proportional_current_cell(...)`, and
`POST /v1/pancha-pakshi/schedule/solar-proportional/current-cell`. The compact
REST response publishes one non-null cell and governing bounds without
duplicating the complete Stage 2D materialization. Result provenance equals the
Stage 2D provenance with only its routing status changed to
`solar_proportional_current_cell_selection_performed_paksha_caller_supplied_no_fixed_clock_mixing_or_inference`;
the omission `source_attested_solar_proportional_materialization` remains
unchanged.

Validation is bounded to solar-half-first routing, exact TT interval ownership,
complete-coverage and exactly-one-match invariants, policy/result immutability,
provenance identity, admission/hash integrity, facade/transport strictness, and
failure of gap, overlap, foreign-cell, tail-state, or mixed-policy vessels. The
configured content-identified `DE-0441LE-0441` reader exercises the published
UT1-to-TT boundary path. This is not an external Pancha Pakshi current-cell
oracle, independent-witness corroboration, or a new historical-accuracy claim.

### Stage 2E Implementation Verification

The admitted implementation was verified on 2026-07-20 with the project
Python 3.14.3 `.venv`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, and downloads disabled:

- `249` focused Stage 2A through Stage 2E engine, shared-solar-boundary,
  Planetary Hours regression, admission/hash, public-contract/facade,
  adversarial-export, and Pancha Pakshi FastAPI service/route-registration/
  OpenAPI tests passed with no skips;
- `4` dedicated live route-catalog and OpenAPI discoverability tests passed;
- the configured content-identified `DE-0441LE-0441` reader exercised all `96`
  published interior proportional boundaries across day and night halves at two
  seasonal epochs; every UT1 boundary round-tripped to its stored TT boundary
  and selected the following cell without tolerance or snapping;
- a real in-process `TestClient` request through the configured engine returned
  HTTP `200`, `selection_status="selected"`, one non-null cell, `0.0 s`
  membership tolerance, the declared routing status, and no duplicated
  materialization or 25-cell payload;
- the live registry contained `423` non-documentation routes, `419` `/v1`
  routes, and exactly `10` `/v1/pancha-pakshi` routes;
- canonical SHA-256 recomputation produced manifest digest
  `d2b5f8f1ae7e067d257eeb24b533be1d33349446d56d361ea59f4a71472eca70`
  and Stage 2E decision digest
  `4ddf0a5fa5b680fa83a7bb3052ecbc5d1a9c2f685c466290f22121dd02724d18`;
  and
- documentation consistency, changed-module compilation, Python 3.10 grammar,
  package/native import identity, and tracked-diff whitespace checks passed.

This receipt validates the deterministic policy, public contract, and
reader-bound numerical behavior. It does not turn DE441, structural interval
invariants, or the inherited Horizons solar-boundary fixture into an external
Pancha Pakshi current-cell oracle.

## Stage 2D Solar-Proportional Materialization Addendum

Stage 2D admits one further capability,
`solar_proportional_materialization`, for the same `source_scoped_public`
profile. The profile document remains unchanged at canonical SHA-256
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`,
and default selection remains forbidden. The chained decision is recorded in
[`pancha_pakshi_1879_solar_proportional_materialization_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_solar_proportional_materialization_2026_07_20.json),
whose canonical SHA-256 is
`e31e0664090b9a38bdcd52b660c04998a0412eab223f4a84fe745b9e54d25383`.
It freezes the Stage 2C decision at SHA-256
`b0698a4163a12dc6049cb30907d6e9dfebad790b35cc3661a41d77df89482976`,
the prior manifest at SHA-256
`366f13deb4b213267b7a6e937b776cd3c3908178e11b29ba238fb3ed47f25e44`,
and binds the new manifest at SHA-256
`6dbbf05383c7a4eb3eadebf70fdb1130ab5081ef83175bc387755ffda4db9121`.

The governing object is `PanchaPakshiSolarProportionalMaterialization`, with
immutable `PanchaPakshiSolarProportionalMaterializationPolicy` and
`PanchaPakshiSolarProportionalCell` vessels. Its only admitted policy is
`solar_proportional_nominal_offsets_over_governing_half_tt_v1`, explicitly a
modern Moira composition rather than an 1879 source claim.

Stage 2A supplies the governing local-solar half and unchanged nominal
schedule. Every exact nominal endpoint is retained as a reduced fraction of
the full thirty-nazhigai schedule. The anchor and solar-half end are converted
through the same configured reader to TT; interior endpoints are derived
independently from the common anchor and complete TT span, then projected to
UT1. The outer TT and UT1 endpoints are exactly the governing solar bounds.
The result contains 25 positive contiguous half-open cells and performs no
fixed-second conversion, clipping, wrapping, repetition, tail fabrication, or
duration accumulation.

The low-level engine, facade, and REST surfaces are respectively
`pancha_pakshi_solar_proportional_materialization_at(...)`,
`Moira.pancha_pakshi_solar_proportional_materialization(...)`, and
`POST /v1/pancha-pakshi/schedule/solar-proportional`. Paksha remains caller
supplied; current-cell selection and astronomical paksha inference remain
`not_performed`. The provenance routing status is
`solar_proportional_materialization_performed_paksha_caller_supplied_no_current_cell_or_inference`.

The raw profile's `seasonal_scaling` omission remains honest source-layer
metadata: the 1879 witness does not attest the proportional rule. The Stage 2D
result avoids claiming the same operation both omitted and performed by
replacing that item with
`source_attested_solar_proportional_materialization`, preserving the historical
non-attestation while naming the separately performed modern composition.
Earlier public results and the hashed profile are unchanged.

Validation is bounded to exact-fraction, independent-mapping, TT/UT1 closure,
half-open topology, capability, immutability, facade/transport, and provenance
invariants, including rejection of forged fraction/endpoint mappings and
contradictory Stage 2D routing provenance. The existing JPL Horizons comparison
remains authority evidence only for the inherited topocentric solar anchor. No
external Pancha Pakshi proportional-timing oracle, independent-witness
corroboration, current-cell claim, or new astronomical or historical accuracy
claim is asserted.

The detached result validates fraction-to-TT mapping, outer UT1 closure, and
UT1 ordering/contiguity from its fields. Reader-dependent interior TT-to-UT1
inverse truth is validated on the factory path, where the configured reader is
available; the focused linear-clock test checks every interior endpoint rather
than treating a detached vessel as an astronomical oracle.

### Stage 2D Implementation Verification

The admitted implementation was verified on 2026-07-20 with the project
Python 3.14.3 `.venv`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, and downloads disabled:

- `202` combined Stage 2A through Stage 2D engine, admission/hash,
  public-contract/facade, adversarial-export, FastAPI service/route/OpenAPI, and
  route-discovery tests passed;
- the configured content-identified `DE-0441LE-0441` reader exercised the
  Stage 2D TT/UT1 structural invariants and the inherited offline Horizons
  solar-boundary gate;
- a real in-process `TestClient` request through the configured engine returned
  HTTP `200`, all `25` cells, exact zero-to-one outer fractions, no
  `current_cell`, and the declared Stage 2D routing status;
- documentation consistency, changed-module compilation, Python 3.10 grammar
  parsing, canonical manifest/decision hashes, native import identity, and
  tracked-diff whitespace checks passed.

This receipt validates the implemented policy and transport contract. It does
not turn DE441, the internal structural invariants, or the inherited Horizons
solar-boundary fixture into an external Pancha Pakshi proportional-timing
oracle.

## Stage 2C Fixed-Clock Current-Cell Addendum

Stage 2C admits one further capability,
`fixed_clock_current_cell_selection`, for the same `source_scoped_public`
profile. The profile document remains unchanged at canonical SHA-256
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`,
and default selection remains forbidden. The chained decision is recorded in
[`pancha_pakshi_1879_fixed_clock_current_cell_2026_07_20.json`](../../tests/fixtures/pancha_pakshi_1879_fixed_clock_current_cell_2026_07_20.json),
whose canonical SHA-256 is
`b0698a4163a12dc6049cb30907d6e9dfebad790b35cc3661a41d77df89482976`.
It freezes the Stage 2B decision at SHA-256
`67cd0ac7cae74556dce702deb29708a5e99a4d19c79184444e3a81d903934449`,
the prior manifest at SHA-256
`766f92650bc050f4c88670f8fd6307036ff49a97e812c9efc9a428fb76e53e17`,
and binds the new manifest at SHA-256
`366f13deb4b213267b7a6e937b776cd3c3908178e11b29ba238fb3ed47f25e44`.

The governing object is `PanchaPakshiFixedClockCurrentCellSelection`, with the
immutable `PanchaPakshiFixedClockCurrentCellSelectionPolicy` and finite
`PanchaPakshiCurrentCellSelectionStatus` values `selected` and
`unmaterialized_solar_half_tail`. Its only admitted policy is
`fixed_clock_current_cell_half_open_solar_precedence_v1`. This is explicitly a
modern Moira interval-membership policy, not an additional rule attributed to
the 1879 witness.

The policy resolves the governing half-open local-solar half before selecting
from that half's Stage 2B materialization. The requested instant is converted
once to reader-bound TT and belongs to a cell exactly when
`start_jd_tt <= requested_jd_tt < end_jd_tt`. Membership tolerance is `0.0 s`:
shared endpoints belong to the following cell, the fixed end is excluded, and
the Stage 2B `0.0001 s` topology coalescence cannot alter current-cell
ownership. At exact sunset or sunrise, the newly governing solar half wins;
post-boundary cells from the previous short half remain inspectable but cannot
remain current.

When a long solar half outlasts its fixed span, the result reports
`unmaterialized_solar_half_tail` and `current_cell=None`. It never clips, wraps,
repeats, stretches, borrows, or retains a cell. Paksha remains caller supplied;
astronomical paksha inference and solar-proportional scaling remain
`not_performed`.

The low-level engine, facade, and REST surfaces are respectively
`pancha_pakshi_fixed_clock_current_cell_at(...)`,
`Moira.pancha_pakshi_fixed_clock_current_cell(...)`, and
`POST /v1/pancha-pakshi/schedule/fixed-clock/current-cell`. The provenance
routing status is
`fixed_clock_current_cell_selection_performed_paksha_caller_supplied_no_scaling_or_inference`.
Validation is limited to structural and physical invariants over the already
admitted Stage 2B cells: midpoint and boundary membership, solar-half
precedence, explicit tail behavior, capability gating, immutable result
consistency, and strict facade/transport policy. No external current-cell
oracle, independent-witness corroboration, or new astronomical or historical
accuracy claim is asserted.

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
| Public vessels and transport | Deferred at this checkpoint; admitted later by the Phase 1 and Stage 2A through Stage 2G decisions above. |

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
4. Treat the admitted Stage 2D proportional materialization and Stage 2E
   current-cell selection as modern policies; source-attested or alternate
   proportional doctrines and alternate natal identities require separate
   evidence and admission. Stage 2F lunar-paksha inference remains its own modern numeric
   policy plus source-scoped mapping and may not be routed into a schedule
   automatically.

The present resting place is two tested, source-scoped public profiles: the
corrected 1879 aksara schedule with the separately named Stage 2A through Stage
2E modern compositions and Stage 2F source-mapped astronomical inference, plus
the separate 2024 source table and Stage 2G modern natal-Moon composition.
Neither is a universal canon, and unresolved or alternate doctrine must not be
silently inferred through the public API.
