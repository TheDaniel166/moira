# Changelog

All notable changes to the Moira project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.2.1] - 2026-07-23

Detailed release and migration guidance is available in
`wiki/03_release/RELEASE_NOTES_5.2.1.md` and
`wiki/03_release/COMPATIBILITY_NOTES_5.2.1.md`.

### Added
- **Frame-explicit house boundaries**: added an opt-in immutable geometry
  vessel for admitted great-circle planes and Placidus semi-arc event curves,
  with exact cusp incidences, effective-system fallback truth, sidereal label
  separation, explicit cusp-only unavailability, facade exports, and typed
  `/v1/houses` transport.

### Validation
- Exercised spatial house-boundary invariants across plane-defined families,
  Placidus event curves, southern and high-latitude cases, sidereal labels,
  effective fallback, public exports, and REST serialization.

## [5.2.0] - 2026-07-23

Detailed release and migration guidance is available in
`wiki/03_release/RELEASE_NOTES_5.2.0.md` and
`wiki/03_release/COMPATIBILITY_NOTES_5.2.0.md`.

### Added
- **First-class solar global circumstances**: added scale-explicit U1-U4
  contacts, central-line limits, greatest eclipse, independently solved
  greatest duration, equatorial and ecliptic conjunctions, geocentric body
  states, signed gamma, Besselian elements, and the existing WGS-84 footprint
  in one immutable result.
- **First-class lunar global circumstances**: added mode-pure native and
  NASA-compatibility results carrying greatest eclipse, Sun and Moon
  astrometry, shadow radii and magnitudes, signed gamma, contacts, phase
  durations, Delta T, and ephemeris identity.
- **Adaptive spherical eclipse cartography**: added NumPy-free,
  projection-independent maximum-visible magnitude and obscuration fields on
  a conforming adaptive icosphere, with antimeridian-safe flat-map segments
  and retained spherical globe topology.
- **Typed eclipse transport**: added REST endpoints for solar global
  circumstances, solar cartography, and lunar global circumstances.

### Fixed
- **Near-singular hybrid horizon topology**: retained the authoritative exact
  sunrise/sunset junction while pruning only bounded numerical micro-branches,
  repairing the 2049 hybrid incidence failure without weakening component
  invariants.
- **Polar and seam rendering topology**: contour extraction now uses shared
  spherical edge identity and explicit antimeridian splitting instead of
  projection-space chord assumptions.

### Validation
- Exercised 330 tests across 33 eclipse-related files after the initial
  implementation, including total, annular, hybrid, polar, topology,
  cartography, public API, native boundary, and REST coverage.
- Bound the new solar global vessel to NASA/GSFC Besselian rows spanning
  partial, total, hybrid, and annular events.
- Bound the new lunar global vessel to hashed NASA figure records spanning
  penumbral, partial, total, and limiting penumbral events.
- Corroborated the detailed 2027-08-02 solar and 2026-08-28 lunar products
  against separately declared EclipseWise DE405/DE430 rows. Cross-model
  agreement remains corroboration rather than an assertion of identical
  ephemeris, limb, or Delta-T models.

## [5.1.2] - 2026-07-22

Detailed release and migration guidance is available in
`wiki/03_release/RELEASE_NOTES_5.1.2.md` and
`wiki/03_release/COMPATIBILITY_NOTES_5.1.2.md`.

### Added
- **NumPy-free native solar-footprint substrate**: added bounded C++17 helpers
  for dense penumbral-clearance scanning, lawful azimuth-interval evaluation,
  and penumbral envelope-candidate discovery. Python continues to own eclipse
  doctrine, topology, ambiguity handling, fallback, and public result vessels;
  no NumPy runtime dependency was introduced.
- **Century lunar-eclipse authority corpus**: added all 229 entries from the
  official NASA/GSFC 1901-2000 lunar-eclipse catalog as validation-only facts,
  with explicit TD/TT, Danjon-shadow, source, and type-code semantics.

### Fixed
- **Solar footprint horizon topology**: repaired close horizon-root discovery
  and exact sunrise/sunset junction assembly for the affected 2027-2031 solar
  footprints. Connected penumbral components now close with their lawful two
  horizon incidences instead of raising an incidence-count error.
- **Physical lunar event geometry**: unified greatest-eclipse search,
  classification, and contacts on the Moon's physical geocentric state at the
  event TT epoch while retaining the reception-light-time solar direction for
  Earth's shadow axis. The retarded Moon remains an explicitly apparent
  diagnostic/observer product rather than the global event classifier.
- **Lunar discovery superset**: widened candidate admission to the declared
  two-degree opposition neighborhood and retained exact cone/disk geometry as
  the classifier. This restores the missed 1922-03-13 and 1940-03-23
  penumbral eclipses and corrects 1988-03-03 from partial to penumbral.

### Validation
- Classified all 229 NASA/GSFC lunar eclipses from 1901 through 2000 with the
  published type family at the catalog TD/TT maxima.
- Recovered the complete 229-event sequence, in order and with matching type
  families, through forward, backward, and bulk range-search paths; the
  greatest-eclipse TT residual stayed below 55 seconds in that corpus.
- Exercised native/Python footprint parity, topology regressions, and the
  kernel-free native parity baseline. Performance measurements remain
  benchmark evidence, not scientific validation.

## [5.1.1] - 2026-07-22

### Fixed
- **DE440 historical Delta-T clock binding**: admitted the content-identified
  `DE440`/`LE440` lunar tidal acceleration basis at
  `-25.936 arcsec/cy²`. Reader-backed charts before the 1972 atomic-clock
  boundary now translate the historical Delta-T source product onto DE440
  instead of raising `_EphemerisTimeBasisError`. Unknown and unadmitted DE/LE
  identities continue to fail closed; modern direct-EOP epochs remain
  numerically unchanged.

## [5.1.0] - 2026-07-21

Detailed release and migration guidance is available in
`wiki/03_release/RELEASE_NOTES_5.1.0.md` and
`wiki/03_release/COMPATIBILITY_NOTES_5.1.0.md`.

### Added
- **Explicit Halb and Oriental/Occidental Dignity Policies**: Added independent
  `include_halb` and `include_oriental_occidental` controls to the engine and
  all six dignity REST routes. Defaults preserve the existing condition labels,
  structured truth, and score contributions; disabling a condition removes
  only that condition without changing the underlying sect or phase geometry.
- **Native-Strengthened Bulk Eclipse Ranges**: Routed
  `EclipseCalculator.solar_eclipses_in_range()` and
  `lunar_eclipses_in_range()` through conservative native TT syzygy-candidate
  discovery when the content-identified planetary reader can cover the padded
  interval. Python retains time policy, physical refinement, classification,
  strict inclusive range semantics, deduplication, fallback, and full
  `EclipseEvent` assembly. The legacy native generic-event scanners remain
  experimental. Added DE441 native/Python parity, adversarial, GIL, public-route,
  and benchmark evidence across 1-, 10-, 100-, and 1,000-year ranges.
- **First-Class Source-Scoped Pancha Pakshi**: Added immutable public vessels,
  package-root and `moira.vedic` exports, ten kernel-free `Moira` methods, one
  kernel-backed astronomical-paksha inference method, one
  kernel-backed local-solar context method, one kernel-backed fixed-clock
  materialization method, one kernel-backed fixed-clock current-cell method,
  one kernel-backed solar-proportional materialization method, one kernel-backed
  solar-proportional current-cell method, one kernel-backed natal-Moon identity
  method, one kernel-backed civil-time Sookshma routing method, and seventeen strict
  `/v1/pancha-pakshi` routes for profile discovery, aksara identity, exact
  nominal schedules, directed relationships, source-mapped astronomical
  paksha, natal-Moon identity, source-scoped Padu and first-samam EAT-seed
  lookups, explicit Sookshma temporal selection and schedule composition,
  local-solar context,
  and fixed-clock and solar-proportional materialization plus their separately
  governed current-cell selectors and explicit civil-time Sookshma composition.
  Manifest schema 2 owns finite admission
  status, exact product capabilities, admission
  decision identity, and a permanently false default-selection flag. The
  profile schema 3 separately owns the normalized lunar-half/source-label
  mapping. The admitted `agastya_madras_1879_akshara_fixed_clock` profile is
  limited to the Agastya-attributed Madras 1879 query/name-initial fixed-clock
  product; no ambient or universal Pancha Pakshi canon is selected. Exact-rational
  nazhigai values remain `Fraction` objects in the engine and serialize as
  numerator/denominator pairs. Every public computation carries source,
  locator, assembly-policy, admission, capability, astronomical-routing, and
  omission provenance.
- **Pancha Pakshi Local-Solar Context**: Added the explicitly modern
  `local_solar_day_explicit_paksha_v1` composition policy. Given a
  timezone-aware instant normalized to UTC, location, explicit profile, and
  caller-supplied `purva` or `amara`
  source label, it derives the governing reader-backed topocentric sunrise,
  sunset, next sunrise, day/night half, and local-mean-solar weekday, then
  selects the unchanged nominal 1879 schedule. The result exposes the policy
  including its fixed `0 m` observer elevation and unrefracted-signal/
  threshold-refraction convention, and exposes UT1 boundaries without
  inferring lunar paksha, converting nominal
  nazhigai offsets into instants, or claiming a current activity. The profile
  data and profile hash are unchanged; an additive admission decision chains
  this capability to the Phase 1 source-scoped decision without asserting
  `corroborated_public` status.
- **Pancha Pakshi Fixed-Clock Materialization**: Added the explicitly modern
  `fixed_24_minute_nazhigai_from_local_solar_half_start_v1` policy. It anchors
  the selected source-owned day schedule at topocentric sunrise or night
  schedule at topocentric sunset, converts each exact rational nazhigai offset
  to fixed SI seconds, adds those offsets on reader-bound TT, and projects the
  half-open endpoints to UT1. One nazhigai is exactly `1,440 s`, so the
  thirty-nazhigai fixed span is always `43,200 s`. The materialized span is
  neither clipped nor stretched to the astronomical half; its signed
  fixed-end-minus-solar-end TT residual and `before`/`coalescent`/`after`
  topology remain visible under an explicit `0.0001 s` numerical coalescence
  policy. The result does not claim a current cell and does not admit
  solar-proportional scaling. The new decision fixture chains the unchanged
  profile and Stage 2A decision while binding the University of Madras Tamil
  Lexicon nazhigai unit, IERS TT/SI-second convention, and the existing
  JPL-Horizons-validated solar anchor within their separate authority roles.
- **Pancha Pakshi Fixed-Clock Current Cell**: Added the explicitly modern
  `fixed_clock_current_cell_half_open_solar_precedence_v1` policy. It resolves
  the governing half-open local-solar half before comparing the requested
  reader-bound TT instant with that half's admitted Stage 2B cells. Shared cell
  endpoints belong to the following cell with exactly `0.0 s` membership
  tolerance; the Stage 2B `0.0001 s` topology coalescence never changes
  ownership. At sunrise or sunset the new governing half takes precedence, so
  cells from a prior short half cannot remain current. When a long solar half
  outlasts the fixed span, the result returns
  `unmaterialized_solar_half_tail` and an explicit null current cell rather
  than clipping, wrapping, repeating, stretching, or retaining a cell. Paksha
  remains caller supplied, and lunar inference and solar-proportional scaling
  remain unperformed. Admission is chained through a new fixture without
  changing the profile data, source-scoped status, product kind, or no-default
  rule.
- **Pancha Pakshi Solar-Proportional Materialization**: Added the explicitly
  modern `solar_proportional_nominal_offsets_over_governing_half_tt_v1`
  policy. It preserves every exact nominal source offset as a reduced fraction
  of the thirty-nazhigai schedule, maps each endpoint independently across the
  complete governing solar half on reader-bound TT, projects interior
  endpoints to UT1, and returns 25 contiguous half-open cells with exact
  anchor and solar-end closure. The fixed `1,440 s` nazhigai conversion is not
  used on this route. Paksha remains caller supplied, and current-cell
  selection and astronomical paksha inference remain unperformed. The hashed
  1879 profile remains unchanged and is not credited with this proportional
  policy; route-specific provenance replaces its source-layer
  `seasonal_scaling` omission with an explicit omission of source attestation
  for the separately performed modern composition.
- **Pancha Pakshi Solar-Proportional Current Cell**: Added the separately named
  `solar_proportional_current_cell_half_open_solar_precedence_v1` selection
  policy. Stage 2A first resolves the governing sunrise or sunset half, Stage
  2D materializes its complete proportional schedule, and the requested instant
  is converted to reader-bound TT once before exact `[start, end)` membership.
  The anchor belongs to cell zero, shared endpoints belong to the following
  cell, and exact sunrise or sunset belongs to the newly governing half. Because
  the proportional schedule covers that half completely, a lawful result is
  always `selected` with one non-null cell; zero or multiple matches fail closed
  instead of introducing a fixed-clock tail, tolerance, clipping, wrapping,
  borrowing, or fallback. Paksha remains caller supplied, and lunar paksha
  inference, natal identity, and fixed-clock mixing remain unperformed.
- **Pancha Pakshi Astronomical Paksha Inference**: Added the immutable
  `PanchaPakshiAstronomicalPakshaInferencePolicy` and
  `PanchaPakshiAstronomicalPakshaInference` vessels, the low-level
  `pancha_pakshi_astronomical_paksha_at(...)` engine function,
  `Moira.pancha_pakshi_astronomical_paksha(...)`, and strict
  `POST /v1/pancha-pakshi/context/astronomical-paksha`. The fixed
  `apparent_geocentric_moon_sun_longitude_paksha_half_open_v1` policy evaluates
  apparent geocentric Sun and Moon longitudes in the true ecliptic of date on
  one reader-bound TT coordinate. Normalized Moon-minus-Sun elongation assigns
  `[0, 180)` to Shukla and `[180, 360)` to Krishna with zero tolerance or
  snapping; exact conjunction therefore belongs to Shukla and exact opposition
  to Krishna. The named 1879 profile maps waxing/Shukla to Purva from IA leaf
  `n16` and waning/Krishna to Amara from leaf `n26`. This mapping is
  source-scoped machine-assisted visual reading with explicit uncertainty and
  no human-review dependency, not a universal-canon claim. The inference accepts no location or
  caller-supplied paksha and performs no schedule selection, materialization,
  current-cell selection, automatic routing into another operation, or natal
  identity. Only normalized facts, source locators, and Moira-authored policy
  are distributed; the archival scan, PDF, OCR, page images, source expression,
  and third-party translations remain unbundled.
- **Pancha Pakshi Natal-Moon Identity**: Added the separate source-scoped
  `bogamuni_chennai_2024_nakshatra_natal_identity` profile, immutable
  `PanchaPakshiNakshatraBirdMapping`, `PanchaPakshiNatalMoonIdentityPolicy`, and
  `PanchaPakshiNatalMoonIdentity` vessels, pure
  `pancha_pakshi_nakshatra_bird_mapping(...)`, low-level
  `pancha_pakshi_natal_moon_identity_at(...)`, both `Moira` facade methods, and
  strict `POST /v1/pancha-pakshi/identity/natal-moon`. Rendered original-page
  inspection binds the complete Purva table to Bogamuni 2024 IA leaf `n52`, the
  governing Amara verse to `n64`, and the phase/Paksha binding to `n167`. The
  malformed adjacent Amara commentary duplicates Shravana and omits Revati; it
  is retained as rejected conflict evidence under the declared
  `verse_precedence_for_nakshatra_partition` policy, never silently repaired.
  The Uromarisi 1934 witness corroborates the Purva grouping and confirms a
  malformed Amara-commentary boundary, but is not imported into runtime truth.
  Because neither source explicitly specifies a birth-Moon calculation or
  ayanamsa, applying the table to apparent geocentric Moon/Sun geometry,
  reader-bound TT, Lahiri true ayanamsa, and 27 equal half-open nakshatras is
  labelled `modern_moira_policy_not_source_claim`. The request accepts only an
  explicit profile, aware instant, and exact policy ID; it rejects location,
  supplied paksha/nakshatra/bird/ayanamsa, schedule, current-cell, scoring, and
  forecast controls. The response exposes all astronomical, sidereal, mapping,
  source-locator, composition, and omission witnesses. The result vessel
  re-derives its nakshatra from the stored sidereal Moon before accepting its
  bird mapping, and the policy publishes the canonical `Lahiri` token used by
  Moira's sidereal APIs. No default canon or automatic schedule routing is
  introduced, and the 1879 aksara profile is unchanged.
- **Pancha Pakshi Padu-Bird Mapping**: Added the third source-scoped profile
  `bogamuni_chennai_2024_padu_bird_mapping`, immutable
  `PanchaPakshiPaduBirdMapping`, pure
  `pancha_pakshi_padu_bird_mapping(...)`, matching `Moira` facade method, and
  strict `POST /v1/pancha-pakshi/roles/padu`. Rendered-page inspection of the
  Bogamuni 2024 original PDF (locally verified SHA-256
  `035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`)
  binds the governing Purva and Amara weekday stanzas to IA leaves `n52` and
  `n60`, and the repeated combined table and commentary to `n157` and `n158`.
  The declared stanza-precedence policy preserves exactly fourteen
  Paksha-by-weekday cells with no day/night axis. Padu remains the source's
  death-or-inoperative bird and is never converted into schedule `RULE`,
  `first_eat_bird`, an authority-bird abstraction, or an Adhikara/Bharana
  alias. The primary witnesses distinguish an eating-bird table and authority
  days rather than presenting an `Adhikara Pakshi` table; Bharana remains
  secondary-only terminology. Uromarisi 1934 and Bogar material remain
  separately observed, unbound research context, not runtime cells or Stage 2H
  admission proof. The strict API accepts only
  explicit profile, source Paksha, and weekday and performs no astronomical or
  civil-day routing, natal identity, schedule/materialization/current-cell
  operation, condition, score, or forecast. The canonical profile, manifest,
  and admission-decision hashes are respectively
  `5de0d1e28d47fad8be6a2a1ab648f2ed71eaf742be2775d166ea44981e96ff10`,
  `eae9fc471da08eccf24515ef12cdaf59330aa1b7ad7f9d43432c7a1482704a03`, and
  `9ea7c871643bb8fc68d420223d0090ca91699154c761c67ccaf9201f401906cd`.
- **Pancha Pakshi First-Samam EAT-Seed Mapping**: Added the granular
  `first_eat_bird_mapping` capability to the unchanged 1879 profile, immutable
  `PanchaPakshiFirstEatBirdMapping`, pure
  `pancha_pakshi_first_eat_bird_mapping(...)`, matching `Moira` method, and
  strict `POST /v1/pancha-pakshi/schedule/first-eat-bird`. Explicit profile
  Paksha, day/night half, and weekday select exactly one of the 28 normalized
  generator seeds bound to 1879 IA leaves `n16`, `n21`, `n26`, and `n31`; the
  result exposes the generator ID, `first_eat_bird`, complete canonical
  generator locators, and provenance without materializing a schedule. The
  seed is not a whole-day eating bird, Padu, authority/Adhikara/Bharana role,
  current activity, condition, score, electional judgment, or forecast.
  Uromarisi 1934 corroborates all 28 cells as a separate publication, while
  textual-lineage independence remains unestablished and no corroborating
  witness supplies runtime data. The profile hash remains
  `4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`;
  the Stage 2I manifest and admission-decision hashes are
  `d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8`
  and `83c9bc0a423c09ccc113007625fee4a7d6b9ee1e890827f71595c96c3f826807`.
- **Pancha Pakshi Vinadi Stage 2J Research Gate**: Recovered a source-attested
  five-position vinadi ordinal axis beneath each named activity from rendered
  review of Uromarisi-attributed 1922, 1932, and 1934 publications. Rendered
  review of a separately scoped Bogamuni-attributed 2024 editorial witness also
  recovered two incompatible selectors: weighted Sūkṣma durations `(3/2,
  5/4, 2, 3/4, 1/2)` closing exactly to six nazhigai, and separately named Eka
  Sūkṣma equal fifths. The hash-bound research decision preserves exact witness
  and page locators, selects no default, and forbids automatic binding to the
  Uromarisi outcome tables. Human-language review is not a dependency.
  Translation-backed outcomes, condition, scoring, electional judgment, and
  forecasting remain unadmitted. No runtime profile, manifest capability,
  public vessel, facade method, or REST route was added. The Stage 2J decision
  SHA-256 is
  `d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243`.
- **Pancha Pakshi Sookshma Temporal Selection Stage 2K**: Added the separate
  source-scoped `bogamuni_chennai_2024_sookshma_temporal_selector` profile,
  immutable selector-policy, interval, and selection vessels, the pure
  `pancha_pakshi_sookshma_temporal_selection(...)` engine function, matching
  `Moira` facade method, and strict
  `POST /v1/pancha-pakshi/sookshma/select`. Every call must explicitly choose
  either `bogamuni_2024_weighted_sookshma_samam_v1` or
  `bogamuni_2024_eka_sookshma_equal_fifths_v1`; there is no default or
  automatic policy selection. The weighted policy rotates the exact
  `(3/2, 5/4, 2, 3/4, 1/2)`-nazhigai activity vector from the named parent
  activity, while the equal-fifths policy returns five exact `6/5`-nazhigai
  ordinal cells and invents no subactivity assignment. Both use exact reduced
  rational input and half-open `[start, end)` ownership within one
  six-nazhigai samam. The surface performs no datetime, civil-clock,
  astronomical, schedule, Uromarisi-outcome, condition, score, electional, or
  forecasting composition. Human-language review is not a runtime or
  admission dependency. The profile, current manifest, and Stage 2K decision
  hashes are respectively
  `596c003c62ebbda913ca28aef318d77cb7b1cf42d92d3b1b7a20a44a01dd6526`,
  `584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`, and
  `10bcfbd70dda28fd399e5c95b8bfa237b8e48f3b2cb20901fc21e0261a73cf70`.
- **Pancha Pakshi Schedule-Sookshma Composition Stage 2N**: Added the explicit
  modern `explicit_schedule_samam_subject_bird_sookshma_v1` composition,
  immutable policy and result vessels, the pure
  `pancha_pakshi_schedule_sookshma_temporal_selection(...)` engine function,
  matching `Moira` method, and strict
  `POST /v1/pancha-pakshi/sookshma/schedule-select`. Every call names both the
  1879 schedule profile and 2024 selector profile, source Paksha, half,
  weekday, samam `1..5`, subject bird, one of the two Stage 2K selector
  policies, and an exact elapsed `Fraction`. The operation generates the
  named schedule, locates the subject bird's unique cell in the named samam,
  and uses only that cell's activity as the selector parent. This cross-profile
  join is labelled a modern Moira policy rather than attributed to either
  witness. It performs no clock or civil-time routing, astronomy, Uromarisi
  outcome binding, interpretation, condition, score, electional judgment, or
  forecast. The four source profiles, capabilities, and manifest remain
  unchanged; A5 acquisition is optional future corroboration rather than a
  blocker. The Stage 2N decision SHA-256 is
  `084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9`.
- **Pancha Pakshi Civil-Time Sookshma Routing Stage 2O**: Added the immutable
  `PanchaPakshiCivilTimeSookshmaSelection` and routing-policy vessels,
  `pancha_pakshi_civil_time_sookshma_selection_at(...)`, matching `Moira`
  facade method, and strict
  `POST /v1/pancha-pakshi/sookshma/civil-time-select`. Every call names both
  source profiles, an aware instant and location, source Paksha, subject bird,
  one of the existing fixed-clock or solar-proportional materialization policy
  IDs, and one of the two Stage 2K selector policy IDs. The current
  materialized cell supplies the samam; the stored binary64 requested/start/end
  TT values are lifted exactly to rational numbers and normalized over that
  samam to six nazhigai before the unchanged Stage 2N composition runs. There
  is no timing default or fallback: a fixed-clock long-half tail remains an
  explicit null-composition tail even though the proportional policy could
  cover the same instant. Astronomical paksha inference, Uromarisi outcomes,
  condition, score, electional judgment, and forecasting remain unperformed.
  All four profiles and the manifest are unchanged. The Stage 2O decision
  SHA-256 is
  `2ea686e774ba4468c0515f621771b8a142c79f04d89b69839f482e05c37b40df`.
- **Pancha Pakshi Constitutional Phase 8 Aggregate Intelligence / Eight-Phase
  Closure**: Added a private immutable structural aggregate over the `24`
  Phase 7 profiles. It preserves activity coverage `5/5/5/4/5`, all `24`
  profiles as not evaluable, relation subsets of `17` detected, `7` not
  recorded, `10` unresolved, `7` named-surface, `0` admitted, and `0` scored,
  plus blocked verse `250`. Counts are never ranks, weights, judgments, scores,
  or forecasts. The agreed eight-phase private sequence is closed with no
  automatic Phase 9 or public admission. No runtime profile, manifest, export,
  facade, REST, or native surface was added. The Phase 8 decision SHA-256 is
  `b193b3ba62d1c5eb57d526777310fa16f29c81fa999e69b813670c680ba2fd13`.
- **Pancha Pakshi Constitutional Phase 12 Public API Curation**: Added the
  immutable, kernel-free `PanchaPakshiUromarisiConstitutionStatus` and
  `pancha_pakshi_uromarisi_constitution_status()` package/facade surface. It
  exposes governance status only: SCP Phases 1-12 are complete, Uromarisi data
  remains private `research_only`, relation semantics and graph metrics remain
  unadmitted, and medical use remains forbidden. No historical record,
  network, manifest profile, REST route, score, or prognosis was admitted. The
  Phase 12 decision SHA-256 is
  `581c137bbbd0fdfe11f61dbb43bfb6cc6e1dafd420f52dd80c2413a4a59ada03`.
- **Pancha Pakshi Constitutional Phase 11 Architecture Freeze**: Added the
  formal Uromarisi backend standard and validation codex after executable
  hardening. It freezes terminology, identity, ordering, failure doctrine,
  private/public boundaries, evidence classes, and nonclaims. The Phase 11
  decision SHA-256 is
  `697eecaf22cf4e8d42ca9b7044633e6407ca8d5577dd4407180029cfc00055c0`.
- **Pancha Pakshi Constitutional Phase 10 Full-Subsystem Hardening**: Added a
  private deterministic receipt across source atoms, classification, policy,
  relations, conditions, aggregate, and network. The exact structural
  fingerprint is
  `2133ad1c72ea5209facbb83ff8f40cfd09c1efea5340df7943fe08ff599cface`;
  adversarial identity, binding, order, conflict, and edge invention fail
  closed. The Phase 10 decision SHA-256 is
  `9ef977585ad1dc9dc517316eb864a8de26f462fb852977bfef936d8756ef64a0`.
- **Pancha Pakshi Constitutional Phase 9 Network Intelligence**: Added a
  private deterministic projection of 24 local-condition nodes and 17 detected
  clause candidates. Because source endpoints and direction remain
  unestablished, admitted and scored edges are empty and topology metrics are
  explicitly not evaluable. The Phase 9 decision SHA-256 is
  `49935df6e96595b5cd365dbea12acabcf862eb81a120c3d9122d29ad4962872b`.
- **Pancha Pakshi Constitutional Phase 7 Integrated Local Condition**: Added a
  private policy-bound local-condition vessel and a complete `24`-profile
  corpus. Each profile pairs one exact Phase 2 classification with its exact
  Phase 5 relation record and source binding. Because no condition doctrine or
  relation meaning is admitted, all profiles are explicitly
  `not_evaluable_no_admitted_condition_doctrine`; favorability is unassigned,
  score is `None`, and prognosis is not performed. Cross-layer identity,
  source, ordering, policy, admission, and scoring drift fail closed. No
  runtime profile, manifest, export, facade, REST, or native surface was added.
  The Phase 7 decision SHA-256 is
  `401c90b7d7c15663427e034a527f983054800f948019cf12b404a0086b3203be`.
- **Pancha Pakshi Constitutional Phase 6 Relation Hardening/Inspectability**:
  Added derived-only identity, source-binding, presence-count, subset, activity,
  ordinal, and verse views over the private Phase 5 relation corpus. Detected
  (`17`), admitted (`0`), and scored (`0`) relations are now explicitly
  distinct; not-recorded (`7`), unresolved (`10`), and named-surface (`7`)
  subsets remain separate. Malformed record members fail closed, SLEEP ordinal
  `5` and verse `250` return no relation without fallback, and no relation
  meaning, condition, score, runtime profile, export, facade, REST, or native
  surface was added. The Phase 6 decision SHA-256 is
  `b175bcd1e537fb551cd26b18d6e6caa37f7a574b7e0a96b336d6fbb97eff9b12`.
- **Pancha Pakshi Constitutional Phase 5 Relational Formalization**: Added a
  private typed relation layer over all `24` unconflicted Uromarisi
  classifications. It preserves `17` present clauses and `7` explicitly
  not-recorded clauses; `10` EAT/WALK clauses remain unresolved, while `7`
  later clauses retain only their exact bounded surface categories. Relation
  endpoints, direction, meaning, favorability, condition, score, prognosis,
  temporal selection, and runtime behavior are not inferred. Verse `250`
  remains outside the relation corpus as an identity conflict. No profile,
  manifest, public export, facade, REST, or native surface was added. The
  Phase 5 decision SHA-256 is
  `e8e189f75418cc96bc6930e2e93d2cfcebc849cb4080001ee4b4b07b158908d1`.
- **Pancha Pakshi Constitutional Phase 4 Doctrine/Policy Closure**: Added one
  private typed policy,
  `moira_explicit_uromarisi_activity_ordinal_lookup_research_v1`, and one
  policy-required classification operation. Callers must explicitly supply the
  private corpus, policy vessel, typed activity, and ordinal `1..5`; there is no
  default or fallback. The policy is explicitly modern Moira research policy
  over source-owned activity/ordinal identities, performs no temporal
  selection, and delegates unchanged to the Phase 3 lookup. Thus SLEEP ordinal
  5 remains absent. Both Bogamuni Stage 2K selector IDs remain separately named
  but unbound cross-witness candidates: neither is source-attested or admitted
  for Uromarisi and no automatic composition exists. No condition, score,
  prognosis, advice, relation binding, runtime profile, export, facade, or REST
  surface was added. The Phase 4 decision SHA-256 is
  `4a444c91bab9a4949664e6bca4e64ad0ee341b439019db831429e4548bd2c4f9`.
- **Pancha Pakshi Constitutional Phase 3 Inspectability Closure**: Added
  derived-only convenience properties and lookups to the private Uromarisi
  classification vessels. Cell views expose stored identity, source binding,
  deterministic marker names, mortality-language presence, and stated,
  conditional, or unreconciled time-shape flags. Conflict views expose all
  three text-layer assignments without precedence. Corpus views expose exact
  verses, counts, source bindings, mortality/time subsets, activity lookup,
  classification lookup, and conflict lookup; absence returns `None` without
  fallback, so SLEEP ordinal 5 and verse `250` remain unclassified while the
  verse `250` conflict remains separately visible. Hardening now rejects mutable
  containers, wrong verse/ordinal matrices, activity/time incompatibility,
  split per-activity source bindings, and a conflict detached from the SLEEP
  source decision. Phase 3 closes privately with no new semantics, doctrine,
  selector, condition, score, prognosis, profile, export, facade, or REST
  surface. The Phase 3 decision SHA-256 is
  `2fd93585f8d2d439882ee77cdeb28e5509e916cd752357d60caaa003cc9fb2ca`.
- **Pancha Pakshi Constitutional Phase 2 Classification Closure**: Added the
  private, data-free `moira._pancha_pakshi_classification` vocabulary and a
  hash-bound closure corpus that classifies all `24` unconflicted Uromarisi
  illness-context cells across EAT/WALK/RULE/SLEEP/DIE as exact projections of
  the Stage 2Q–2U semantic atoms. The model preserves typed source-statement
  dispositions, time-expression shapes, semantic-reference presence, source
  decision identity, and per-cell uncertainty. Verse `250` remains a separate
  unclassifiable text-layer conflict with no classification payload. Invariants
  reject activity/disposition mismatch, mortality-marker inconsistency, missing
  uncertainty, incomplete or unordered coverage, duplicate identity, and
  conflict normalization. Phase 2 closes only at the private research boundary;
  Phase 3 may add derived inspectability and vessel hardening but no doctrine,
  prognosis, score, selector binding, profile, export, facade method, or REST
  route. The closure SHA-256 is
  `a5cd64696d4c040554f2c235056dfd28477fd0796fc82306f44ae43473d434e2`.
- **Pancha Pakshi Uromarisi DIE Semantics Stage 2U Research Extension**:
  Reviewed the five unconflicted DIE-period illness verses `251–255` on
  rendered PDF pages `124–126`, while carrying verse `250` only as the blocked
  Stage 2T precursor. The first cell preserves a conditional two-month upper
  bound and a separate six-month source branch; the second preserves both an
  instantaneous marker and a one-year marker without harmonizing them; the
  remaining cells state no numeric duration. Mortality, body-destruction,
  nonresolution, space/void, fate, deity, relation, and source-branch language
  remains historical and non-runtime—not prediction, diagnosis, prognosis,
  cause, symptom, score, advice, or deterministic fate. Verse `256` begins a
  separate illness-duration section and is excluded. No selector, manifest,
  engine, facade, or REST surface changed, and no human Tamil reviewer is
  required. The Stage 2U decision SHA-256 is
  `4954c13c33aa755bc0e8c6f47b7825d6ddb8346a2b6df39edf804872e81cbf70`.
- **Pancha Pakshi Uromarisi SLEEP Semantics Stage 2T Research Extension**:
  Reviewed SLEEP-period illness verses `246–250` on rendered PDF pages
  `122–124`. Verses `246–249` yield four unconflicted semantic records with
  upper-bound `8` days, upper-bound `15` days, exact `20` days, and a
  conditional three-month mortality-or-resolution branch. Verse `250` is
  blocked: its heading and verse assign DIE ordinal 5 while its commentary
  assigns SLEEP ordinal 5. Stage 2T therefore refines the earlier Stage 2P
  locator claim without mutating that hash-bound fixture. Mortality,
  recurrence, distress, harm, wind-dosha, treatment, ritual, and relation
  language remains historical and non-runtime—not prediction, diagnosis,
  advice, symptom, score, or medical truth. No selector, manifest, engine,
  facade, or REST surface changed, and no human Tamil reviewer is required.
  The Stage 2T decision SHA-256 is
  `09f7651325cdac058d9816b85b031ef528f514ae91fb8cd9636452b8d7fb302a`.
- **Pancha Pakshi Uromarisi RULE Semantics Stage 2S Research Extension**:
  Extended the machine-assisted semantic-atom method to RULE-period illness
  verses `241–245` on rendered PDF pages `120–122`. All five cells state
  resolution, with time expressions of `3` days, `5` days, within `8` days,
  `10` days, and `12` days; the upper bound remains distinct from exact days.
  Source deity titles, prescribed actions, fire-clause roles, Saturn-dosha
  references, historical effect language, and one surface no-enmity statement
  remain cell-local and uncertainty-bearing. None is accepted as a diagnosis,
  medical cause, symptom, score, or runtime relation. No selector binding,
  runtime data, or public surface was added, and no human Tamil reviewer is
  required. The Stage 2S decision SHA-256 is
  `85142480188a00ddec3de6f192a36025f282ca0eefa4643a6f1d74da4cec811d`.
- **Pancha Pakshi Uromarisi WALK Semantics Stage 2R Research Extension**:
  Extended the Stage 2Q semantic-atom method to WALK-period illness verses
  `235–239` on rendered PDF pages `118–120`. The source-stated time expressions
  remain distinct: `10` days, `15` days, within `20` days, `25` days, and
  within one month. The cells separately preserve resolution, abatement, and a
  timed progression without explicit resolution; the month is not converted
  to days. Deity titles, prescribed actions, stated mediations, water-clause
  roles, a physician reference, and a Navagraha-dosha reference remain
  cell-local and
  uncertainty-bearing. No medical truth, advice, generic label, score,
  selector binding, runtime data, or public surface was added. No human Tamil
  reviewer is required. The Stage 2R decision SHA-256 is
  `361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6`.
- **Pancha Pakshi Uromarisi EAT Semantics Stage 2Q Research Pilot**:
  Transcribed bounded semantic atoms for the five EAT-period illness cells in
  verses `230–234` of the exact Stage 2P witness. Rendered PDF pages `116–118`
  control the reading; Archive.org OCR lines are navigation aids only. The
  source-stated resolution durations are preserved as `4 or 5`, `7`, `9`,
  `13`, and `15` days, while distinct devotional-response categories,
  medicine and `prithivi` term references, and unresolved relation clauses
  remain separate with per-cell uncertainty. These records describe one
  historical witness and do not establish medical truth. No generic good/bad
  label, numeric score, diagnosis, advice, selector binding, runtime data, or
  public surface was added. No human Tamil reviewer is required. The Stage 2Q
  decision SHA-256 is
  `7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9`.
- **Pancha Pakshi Uromarisi Illness Grid Stage 2P Research Gate**: Verified
  the exact Archive.org 1934 Uromarisi-attributed PDF at SHA-256
  `e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`
  and rendered PDF pages `115–126`. Added a research-only decision indexing
  the complete illness-context structure as five parent activities by five
  explicit vinadi ordinals. The 25 cells bind verses `230–239` and `241–255`
  to repeatable PDF/printed-page locators; transition verse `240` and the
  separate illness-duration section beginning at verse `256` remain outside
  the grid. No source outcome statement is copied, translated, normalized,
  scored, or exposed. Neither Stage 2K selector is attributed to Uromarisi,
  and Stage 2O does not route into the research grid. The four profiles,
  manifest, engine, facade, and REST surface are unchanged. The Stage 2P
  decision SHA-256 is
  `449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2`.
- **Pancha Pakshi Ramadevar Candidate Disambiguation Stage 2M**: Resolved the
  catalogued candidate to the exact Commissionerate of Indian Medicine and
  Homoeopathy record: serial `859`, manuscript `A5`, titled `Ramadevar
  Panchapakshi`. The 63-page catalog supplies no leaves, transcription,
  physical description, incipit, colophon, date, computational rules, or
  copying history, so the candidate remains title-only and cannot clear the
  independent-witness gate. Separately accessible `Ramadevar Patchini` and
  `Patchani 108` records were disambiguated as yoga, philosophy, medicine,
  alchemy, or ritual works rather than the five-bird temporal product. No
  runtime data, manifest, admission status, capability, facade, or REST
  surface changed, and no human-language reviewer is required. The Stage 2M
  decision SHA-256 is
  `921e604bcd81298aa6eb903acc967e68cfcf6e743c7d1379788ff9996212c6db`.
- **Pancha Pakshi Independent-Witness Collation Stage 2L**: Added a hash-bound
  research-only collation of the Sarasvati Mahal Library 2014 sixth edition
  and the two supplied modern guides. The institutional compilation exactly
  agrees with the admitted 1879 profile on all seven Purva-day first-EAT seeds
  and the waxing-day duration vector, while preserving three materially
  different regime-specific vectors and an explicit Agastya/Bogar versus
  Uromarisi ordering conflict. The Narasimhan guide is retained only as a
  secondary comparator because it has no bibliography or primary-text
  lineage; the Canva/AI-marked guide is rejected for unrelated tarot content.
  No inspected comparable witness establishes textual-lineage independence,
  so all four profiles remain `source_scoped_public`; no runtime data,
  manifest, capability, facade, or REST change was made. No human-language
  reviewer is required. The Stage 2L decision SHA-256 is
  `5534ddde1c0b87fa5fc3332112d02fd1c48c38e0a79f45f4a75a3e3c728a4c34`.
- **Pancha Pakshi Human-Review Dependency Removed From Runtime Truth**:
  Replaced the live 1879 profile's legacy
  `pending_competent_tamil_review` derivation token with
  `machine_reconciled_source_assignment_with_declared_uncertainty`. Frozen
  historical research and admission receipts retain their original labels,
  but no human Tamil reviewer is a current runtime, admission, or maintenance
  requirement. The resulting live 1879 profile SHA-256 is
  `d80d205716eb9f24a2a23949c6df241a1aba251749efa94d3b20fa36be0258f4`.
- **Pancha Pakshi Research And Admission Evidence**: Preserved the original
  blind reading, representative-grid reading, page-image adjudication, and
  machine reconciliation as frozen historical records. The adjudication
  established the full `30/5/6` day/night scope and table axes, confirmed the
  Amara-night schedule and all twenty directed nonself relationship cells, and
  corrected the former Pūrva-night generator. A new additive admission fixture
  links the former and schema-v2 profile hashes and binds the unchanged
  computational surface of 10 identity symbols, 28 schedules, 700 cells, and 20
  directed relationships. Independent-witness collation remains a barrier to
  corroborated claims; machine-assisted source reading carries explicit
  uncertainty but no human-review dependency for these source-scoped products.
  The standing non-bundling architecture remains in
  force; archival scans, PDFs, OCR, page images, copied layouts, source prose,
  and third-party translations are not distributed, and no rights-clearance
  phase was introduced.

### Fixed
- **Bounded Meridian-Event Absence**: `find_phenomena()` now omits a
  `Transit` or `AntiTransit` key when no corresponding meridian crossing exists
  inside its documented 24-hour window, while preserving `get_transit()`'s
  explicit no-bracket failure. This is required for lunar windows because the
  interval between successive lunar meridian crossings can exceed 24 hours.
- **Release Validation Contracts**: Updated the physics-layer node reference
  test to use the reader-owned ephemeris clock, removed invalid Python 3.14
  bans on supported annotation syntax, disabled benchmark-like Hypothesis
  deadlines on kernel-backed correctness properties, restored the global
  kernel reader after the sovereign-manifest routing test, and refreshed the
  deterministic DE441 Dorotheus regression value after the admitted clock
  correction.
- **Nakshatra Boundary Ownership**: Centralized equal-27-sector classification
  so exact internal `k × 40/3`-degree boundaries belong to the following
  nakshatra across the public sidereal and Vimshottari consumers. A bounded
  maximum-one-ULP recovery corrects only binary representations of those exact
  mathematical boundaries; it is not an orb or tolerance band. TT-explicit
  internal sidereal helpers also let reader-backed compositions reuse one
  already-derived TT epoch instead of converting it a second time.
- **Panchanga Phase-Boundary Coherence**: Tithi and Karana now derive their
  shared phase coordinate by directly subtracting the tropical Moon and Sun
  longitudes. Their common ayanamsa would cancel mathematically, so avoiding
  two separately rounded sidereal conversions keeps exact conjunction,
  opposition, tithi, and half-tithi boundary ownership stable while preserving
  the published sidereal longitudes elsewhere in the Panchanga result.

### Changed
- **Shared Local Solar Day Boundary**: Extracted the existing topocentric
  sunrise-to-sunrise window selection, UTC/UT1 civil-noon anchoring, geographic
  validation, polar failure, and local-mean-solar weekday policy into the
  private `moira._local_solar_day` boundary. Planetary Hours now consumes that
  shared result while retaining its existing public vessels, method
  signatures, FastAPI schemas, Chaldean sequence, temporal-hour arithmetic,
  numerical output, and error semantics.

### Validation
- The Stage 2A astronomical boundary is checked against the offline JPL
  Horizons `sun-new-york-equinox` observer-table fixture. With the discovered,
  content-identified `DE-0441LE-0441` kernel, sunrise and sunset differed by
  `0.082 s` and `0.123 s`, respectively, within the fixture's `2 s` authority
  gate. This validates the local-solar boundary only, not the historical
  Pancha Pakshi doctrine.
- Stage 2B validation separately checks exact rational-to-SI-second
  materialization, TT-to-UT1 endpoint projection, half-open ownership,
  no-clipping behavior, and the signed fixed-end topology. The `0.0001 s`
  coalescence is numerical policy rather than historical or astronomical
  accuracy, and no external current-cell oracle is claimed because the Stage
  2B materialization deliberately selects no current cell.
- Stage 2C validation checks solar-half-first precedence, all half-open cell
  midpoints and shared endpoints, the inclusive anchor and excluded fixed end,
  explicit long-half-tail behavior, short-half post-boundary ineligibility,
  zero-tolerance membership, immutable status/cell consistency, capability
  gates, facade/REST policy strictness, and the frozen Stage 2B manifest chain.
  This is structural and physical-invariant evidence over already admitted
  intervals; it is not external current-cell parity or a new astronomical or
  historical accuracy claim.
- Stage 2D validation checks exact reduced endpoint fractions, independent
  common-anchor mapping on reader-bound TT, positive contiguous half-open cells
  for long and short day and night halves, exact TT/UT1 outer closure,
  capability gating, immutable vessels that reject fraction/endpoint drift or
  contradictory routing provenance, strict facade/REST policy admission, and
  provenance that distinguishes missing source attestation from performed
  modern composition. The existing Horizons fixture remains authority evidence
  only for the inherited solar boundaries; no external Pancha Pakshi
  proportional-timing oracle or new historical-accuracy claim is asserted.
- Stage 2E validation checks exact zero-tolerance membership at the anchor, all
  24 proportional cell boundaries, preceding representable instants, cell
  midpoints, and the excluded old-half endpoint under solar-half-first
  precedence. It also checks selected-only/non-null result semantics, immutable
  policy and provenance binding, strict facade/REST admission, and fail-closed
  rejection of zero, multiple, or foreign-cell matches. DE441 exercises the
  reader-bound TT/UT1 boundary path; it is not an external Pancha Pakshi oracle.
- Stage 2F validation binds the direct source readings at IA leaves `n16` and
  `n26`, exact `0`/`180`-degree half-open ownership, single-conversion
  UT1-to-reader-bound-TT semantics, shared-TT Sun/Moon evaluation, immutable
  policy/result/provenance consistency, capability gating, and strict
  facade/REST fields. DE441 exercises the astronomical substrate, while
  synthetic boundary cases and Panchanga coherence checks prove the declared
  partition; neither is an external Pancha Pakshi oracle or independent-witness
  corroboration.
- Stage 2G validation binds the Bogamuni source-table locators at IA leaves
  `n52` and `n64`, the phase-label locator at `n167`, all 54 exact
  Paksha/nakshatra cells, declared verse precedence, the preserved malformed
  commentary conflict, strict capability/profile separation, and immutable
  source-versus-modern-composition provenance. Mathematical tests cover every
  exact equal-sector boundary and its adjacent representable values. The
  admission decision binds both the profile and the current manifest digest,
  and Ashtottari, Yogini, Vimshottari, and Muhurta share the same canonical
  nakshatra boundary classifier. A DE441 execution smoke exercises the
  apparent geocentric reader-bound TT path.
  Source-table validation, boundary invariants, and DE441 execution are
  separate evidence classes; none is claimed as an external natal-identity
  oracle.
- Stage 2H validation binds the governing Bogamuni leaves `n52` and `n60`, the
  same-witness repetitions at `n157` and `n158`, all fourteen exact
  Paksha-by-weekday cells, three canonical locators per result, profile/
  manifest/decision hashes, immutable provenance, capability isolation, and
  strict facade/REST/OpenAPI shapes. Adversarial checks reject day/night or
  temporal fields, incomplete/duplicated/forged cells, foreign locators,
  schedule-`RULE` conversion, `first_eat_bird` or Adhikara/Bharana relabelling,
  and scoring or forecast claims. This is source-table and structural evidence,
  not a condition, electional, or forecasting oracle.
- Stage 2I validation binds all 28 first-samam EAT seeds to the four governing
  1879 leaves and complete canonical generator locator tuples. Every lookup is
  checked against the existing nominal schedule's `first_eat_bird` and first
  EAT cell; adversarial tests cover immutable vessel/provenance truth,
  capability and profile isolation, no materializer call, strict facade/REST/
  OpenAPI shapes, and exact reconstruction of the frozen Stage 2F and Stage 2H
  manifests. Uromarisi 1934 is recorded as separate-publication corroboration,
  not independent-textual-lineage proof, runtime data, or a universal canon.

## [5.0.0] - 2026-07-19

Detailed release and migration guidance is available in
`wiki/03_release/RELEASE_NOTES_5.0.0.md` and
`wiki/03_release/COMPATIBILITY_NOTES_5.0.0.md`.

### Breaking Changes
- **Relationship Results Are Immutable**: Synastry truth, classification,
  relation, condition, network, overlay, composite, and Davison vessels are
  now frozen, and their nested maps and cusp sequences are defensive immutable
  copies. Callers that mutated a returned vessel in place must construct a new
  value instead.
- **Readiness Uses HTTP Status Semantics**: `GET /ready` now returns HTTP 503
  whenever its unchanged `ReadyResponse` body reports that the worker is not
  ready. Liveness remains HTTP 200 at `GET /health`; readiness clients must no
  longer assume every readiness response has status 200.
- **Invalid Inputs Fail Explicitly**: Phenomena, planetary observer,
  planetary-hour, house, primary-direction, and related policy boundaries now
  reject unsupported, ambiguous, non-finite, or internally contradictory
  inputs that older releases could coerce or tolerate. Callers relying on those
  implicit fallbacks must validate inputs or handle the documented engine/REST
  errors.
- **Sect-Specific Chaldean Bounds Identity**: Replaced the ambiguous public
  `chaldean` doctrine and `CHALDEAN_BOUNDS` table with explicit
  `chaldean_day`/`CHALDEAN_DAY_BOUNDS` and
  `chaldean_night`/`CHALDEAN_NIGHT_BOUNDS` identities. Bounds callers must
  choose the governing sect rather than inheriting an undeclared table.
- **Ramesey Remedy Contract 1.1.0**: Replaced the public profile's
  instruction-only remedy assessment with non-erasing tri-state fulfillment
  and clause evidence. Callers bound to the `1.0.0` remedy response must admit
  the new typed fields and `profile_version="1.1.0"`.

### Added
- **Source-Scoped Topocentric Signed Primary Motion**: Added the explicit
  `topocentric_zodiacal_aspect_signed_primary_motion` preset for Makransky's
  assigned-zero, projected-perfection Topocentric zodiacal-aspect product. It
  classifies one ordered shortest circular arc: positive is direct, negative
  is converse, numerical zero is no event, and the directionally ambiguous
  `180`-degree boundary fails closed. This is a narrow signed-motion doctrine,
  not the deferred global neo-converse doctrine and not a replacement for
  traditional role-exchanged converse. REST admission is engine-search-only;
  submitted arcs are rejected because they do not preserve the raw signed-arc
  evidence needed to derive their label. Signed searches require explicit,
  non-empty significator and promissor filters so an unbounded candidate set
  cannot encounter an undeclared antipodal ambiguity. Existing facade
  signatures and all eight `/v1/primary-directions/*` paths remain unchanged.
- **Primary-Directions Evaluation Facade**: Added canonical `Moira` delegations
  for policy-preset construction, single-arc relation evaluation,
  per-significator condition, chart-wide aggregate profiles, and directed
  promissor-to-significator networks. Existing `speculum(...)` and
  `primary_directions(...)` positional calls remain intact and gain only
  keyword-only obliquity, body, solar-rate, and policy controls.
- **Advanced Primary-Directions REST Inputs**: Added typed, search-only request
  vessels for Ptolemaic antiscia and parallels, direct/converse Placidian rapt
  parallels, sovereign-catalog fixed stars, and Morinus aspect path contexts.
  The existing `arcs`, `profile`, and `network` compact/reduction routes expose
  them without adding or replacing paths. Preset compatibility, strict identity
  and scalar validation, duplicate rejection, per-list and combined bounds, and
  exact resolved-policy provenance keep transport behavior aligned with the
  existing engine vessels.
- **Provenance-Bearing Harmonic Orb Policy**: Added immutable
  `HarmonicOrbPolicy` and resolved `HarmonicOrbTruth` vessels with the admitted
  Addey inverse-harmonic relation `O_H = O_1 / H`. The configurable H1
  reference remains the limit on the projected harmonic chart, while the
  locally equivalent source-circle allowance is reported separately as `O_1/H`,
  preventing accidental double division. Non-integer use is explicitly marked
  as Moira's continuous extension of the cited rule. Conjunction-bearing REST
  provenance now exposes scaling mode, authority, source locator, formula,
  projected/source limits, request adapter mode, and extension truth.
- **VA-Informed Sampled Harmonic Transit Forecasts**: Added the independent
  `moira.harmonic_transits` module with immutable caller-supplied sample,
  origin-qualified member, complete-triple, observed-window, policy, and
  forecast vessels. It admits one-transit/two-natal and
  two-transits/one-natal configurations at requested integer harmonics using
  one minimum circular covering arc for all three members. Added
  `Moira.harmonic_transit_forecast(...)` and
  `POST /v1/harmonics/transit-forecast` with bounded bodies, samples,
  harmonics, and candidate evaluations. Window boundaries and peaks are
  supplied-sample witnesses; provenance explicitly disclaims interpolation,
  exact ingress/egress, and Sirius parity. The route rejects coercive
  longitude scalars, non-finite timestamp spans, and requests whose worst-case
  materialized pattern count exceeds the declared 25,000-evaluation budget.
- **First-Class Declination Aspects**: Added the governing
  `moira.declination_aspects` module with explicit Parallel/Contra-Parallel
  kinds, admission policy, hemisphere/equator doctrine, immutable analysis
  vessels, and an instantaneous signed-error motion witness. Added
  `Moira.declination_aspect_motion_witness(...)` and
  `POST /v1/aspects/declination-motion-witness` without changing the existing
  declination-analysis route.
- **Opt-In Server Prewarm**: Added `MOIRA_SERVER_PREWARM=1` for one bounded,
  per-worker J2000 all-planet warmup before computational traffic is admitted.
  The warmup excludes lunar nodes, supplemental small-body kernels, and the
  HTTP chart-result cache; it is disabled by default because every worker pays
  its own native memory cost.
- **Runtime-Dispatched AVX2 Interpolation**: Added a separately compiled AVX2
  implementation for three-component Type 2 Chebyshev position and derivative
  evaluation. Capable x86 hosts select it at runtime, while unsupported CPUs
  and builds retain the portable scalar implementation rather than acquiring a
  wheel-wide AVX2 requirement.
- **First-Class Instantaneous Solar Besselian Elements**: Added the frozen
  `SolarBesselianElements` engine vessel and
  `EclipseCalculator.solar_besselian_elements(jd_ut1)`. The method evaluates
  exactly the supplied instant rather than hiding an eclipse search or
  polynomial fit. It projects the DE441 Earth-reception light-time Sun/Moon
  center-of-mass shadow line, without stellar aberration, into the true equator
  and equinox of date: `x` is east-positive, `y` north-positive, `x`, `y`,
  `l1`, and `l2` use Earth equatorial radii, `d` and `mu` use degrees, and the
  cone tangents are dimensionless and come from the exact common-tangent cone
  geometry rather than a small-angle radius ratio. `mu` is the TT/TDT ephemeris
  hour angle, not physical UT1 GAST. Moira's physical mean-limb radii remain governing, while
  `l2` uses the NASA fundamental-plane sign convention (negative umbral,
  positive antumbral); global hybrid classification still belongs to the
  separate Earth-surface geometry. The method fails closed unless its reader
  is content-identified as DE441/LE441.
- **First-Class Solar Partial-Visibility Footprints**: Added immutable solar
  footprint points, penumbral contacts, named limit-track components and
  time-monotone segments, topology, and aggregate visibility-footprint
  vessels, exposed through
  `Moira.solar_eclipse_footprint(...)` and
  `POST /v1/eclipses/solar/footprint`. The governing product sweeps the exact
  common-tangent, physical mean-limb penumbral cone from content-identified
  DE441/LE441 Earth-reception states across zero-elevation WGS 84. It reports
  P1/P4 and optional P2/P3 contacts, north/south penumbral-envelope components,
  geometric sunrise/sunset components, and explicit
  `one_limit_connected` or `two_limit_two_loop` topology in UT1. The default
  sampling count is `181`, bounded to `9..721`; it changes interior density,
  not solved boundary-graph structure. Each admitted penumbral kind is the
  single `component_id=0`; folds are emitted as contiguous, strictly
  time-ordered `segment_id` values sharing refined endpoints, and two-limit
  north/south components require disjoint horizon incidences. Two-limit
  products are restricted to central global eclipses, and their geometric
  horizon tracks remain wholly within P1-P2 or P3-P4 rather than crossing the
  internal P2-P3 interval.
- **First-Class Polar-Safe Occultation Path Topology**: Added immutable center
  points, intrinsic left/right boundary tracks, greatest-limit points, exact
  geographic-pole ingress/egress contacts, and a two-sided-band topology
  vessel for planetary and fixed-star lunar occultations. Four additive
  `Moira` methods and `/v1/occultations/*-path-topology*` routes preserve the
  compatibility geometry under `summary` while exposing the complete shared
  UT1 track lattice. The nominal product admits only a spherical mean lunar
  limb; profile-conditioned graze products remain separate. Planetary target
  disks use JPL equatorial solid-body radii, fixed stars remain point sources,
  the Sun remains on the eclipse surfaces, and Saturn's rings are excluded.
  Topocentric observers are WGS 84 geodetic,
  while half-widths and total width explicitly use spherical great-circle
  distance with radius `6378.137 km`. The observer-height domain has a
  source-derived computational floor at the negative WGS 84 semi-minor axis;
  this protects the parallax envelope and is not an observational-validity
  claim. No arbitrary positive-height ceiling is imposed: if an observer
  radius reaches a body's geocentric distance, the conservative parallax bound
  becomes `180 degrees` rather than incorrectly clamping at `90 degrees`.
- **First-Class Topographic Lunar Contact Chronology**: Added the direct-import
  `moira.lunar_occultation_contacts` engine module with immutable contact,
  visibility, named ICRS astrometric-target, search-policy, profile, and
  sequence vessels for lunar-stellar disappearance, reappearance, and
  tangency events. Sovereign-registry directions are proper-motion propagated
  to an event-owned TT epoch; positive catalog parallax is applied from the
  complete reception-epoch observer SSB position, and gravitational
  deflectors are observer-relative. Event-specific, finite-resolution limb
  profiles are prepared before solving, so contact
  searches perform no profile I/O. Content-identified DE441/LE441 supplies the
  physical Moon-to-observer light cone, NAIF DE440_ME421 resources supply lunar
  orientation, and official USGS LOLA relief supplies the limb topography.
  Finite-distance tangent-circle geometry and perspective-equivalent radii
  replace the former orthographic surface shortcut. Physical contact admission
  uses a contact-private Klioner equation-70 stellar-deflection path with
  DE441 deflector states, closest-passage backtracking, and declared SOFA
  `Ldn` limiters while retaining the Moon as the retarded
  geometric blocker; it is airless and excludes observer-motion aberration and
  atmospheric refraction. The modeled chronology remains distinct from
  nominal mean-limb path limits and from observed IOTA contact records.

### Fixed
- **Primary-Directions Evidence Semantics**: Corrected the Sepharial Saturn
  fixture to preserve its published south declination as a parallel-equivalent
  point instead of manufacturing a positive declination and labeling it an
  externally attested contra-parallel. Added source-scoped Campanus,
  Topocentric, fixed-star, reflected-point, parallel, rapt-parallel, and
  Morinus worked-example corpora with explicit evidence classes, printed-input
  tolerances, rights notes, and non-evaluable boundaries. The Topocentric
  corpus now exposes the source's signed converse label through its separate
  signed-primary-motion preset while preserving the established
  role-exchanged Topocentric preset unchanged.
- **Primary-Directions Geometry, Identity, And Boundary Integrity**: Made
  Placidian mundane position continuous through all four quadrants, restored
  signed Ptolemaic OA/OD behavior, and expressed Regiomontanus, Campanus,
  Topocentric, and Morinus pole/projection work through explicit spherical
  geometry. No-real circumpolar, limiting-tangent, and inverse-trigonometric
  domains now fail closed instead of being broadly clamped or repaired after
  the fact. Primary-direction vessels now reject coercive, non-finite, and
  contradictory state; preserve defensive immutable collections; and enforce
  aggregate and directed-network conservation. Generated arcs carry their
  actual conjunction, opposition, aspect, parallel, rapt, or reflected
  `relational_kind`, distinct from perfection-kind compatibility fields.
  Fixed-star aliases retain caller identity, zodiacal suppression is applied
  before star-speculum construction, Ptolemy is truthfully classified as both
  mundane and zodiacal capable, and target recognition no longer admits
  arbitrary names merely because they end in `Node` or contain `Lilith`.
  Placidian-classic endpoint geometry now receives the actual horizon
  coordinate `OA(ASC) = (ARMC + 90 degrees) mod 360`, rather than the right
  ascension of the ecliptic Ascendant. Method capability is enforced at policy,
  arc, and geometry boundaries, so `PLACIDUS_MUNDANE` and
  `PLACIDIAN_CLASSIC_SEMI_ARC` reject `in_zodiaco`. House-cusp-sourced
  aspectual promissors materialize their named source cusp before projection,
  and supplied Morinus aspect contexts have normalized, unique, exact source
  identities.
  Solar-key conversion now requires an explicit positive natal solar rate and
  is classified as a static-rate conversion rather than silently falling back
  to Naibod. `PrimaryArc.solar_rate_explicit` distinguishes that usable natal
  rate from the numeric compatibility rate retained on older constructed arcs.
  Fixed-star targets require conjunction admission. Rapt-parallel motion is
  admitted for the configured rapt relation only, and composing a rapt preset
  with fixed stars admits only those named stars rather than widening ordinary
  conjunction targets. Relation vessels enforce space/perfection agreement;
  relation and significator profiles preserve the exact owning arc and order.
  Ordered method, perfection, relation, and target transition networks must be
  realizable as one connected directed Euler path (or a lawfully linearized
  circuit), not merely satisfy aggregate counts.
- **Positive-Real Harmonic Identity**: Direct harmonic chart, conjunction,
  pattern-score, and composite calculations now preserve every positive finite
  real H instead of silently coercing `5.5` to `5`. Inputs are normalized to
  the canonical zero-Aries `[0, 360)` branch before multiplication, making the
  non-integer continuous-multiplier semantics explicit. Integer range/sweep
  and forecast products remain integer by doctrine. Urania Workspace can now
  delegate fractional H directly and no longer manufactures a synthetic
  age-harmonic Julian Day to bypass the former truncation. Harmonic REST
  longitude and orb scalars now reject booleans and numeric strings rather
  than silently coercing scientific inputs.
- **Pattern Role And Structural-Containment Doctrine**: Grand Trine now carries
  explicit cycle-member/cycle-link truth; Minor Grand Trine preserves
  base/support structure; and Cradle and Trapeze preserve their opposition
  axes and support bodies. Grand Cross, Mystic Rectangle, and Septile Triangle
  also preserve their detector-proved edge orbits rather than falling through
  to generic member links. Structural condition state is now invariant-checked
  and describes role completeness, not motion or interpretive strength.
  Cradle, Trapeze, Mystic Rectangle, and Septile Triangle searches no longer
  depend on incidental body-name orientation, and Trapeze's admitted
  three-sextile-chain graph is now stated coherently. Added opt-in
  `dominant_only` policy to
  `find_all_patterns(...)`, `Moira.patterns(...)`, and the shared
  `/v1/patterns/*` request, using strict body-and-aspect subgraph containment so
  a Grand Trine inside an admitted Kite can be hidden without erasing
  unrelated smaller patterns or position-based Stelliums; same-body strict edge
  subgraphs are also suppressed. The default remains unfiltered. Restored the
  documented direct `include` and `orb_factor` behavior, which had been silently
  overwritten by an implicit default policy. The facade now applies orb scaling
  during initial aspect admission as well as pattern admission, and engine/REST
  policy rejects non-finite orb factors. REST policy scalars no longer coerce
  booleans, numbers, or strings into a different computation choice.
- **Bounded Occultation Topology Search**: Treats the requested scan step as a
  maximum cell width, admits at most `0.25 d`, 400 days, and 4096 cells, and
  rejects excess work before candidate-envelope evaluation. Boundary cells
  are refined unconditionally, while a constrained maximum at, or numerically
  indistinguishable from, the global request boundary is not mislabeled as an
  event greatest. Candidate maxima
  are coalesced only when their exact-positive temporal supports genuinely
  overlap; zero-clearance tangency alone does not merge events. Each connected
  component is re-solved on a private at-most-30-minute lattice with a
  128-cell fail-closed budget; every resolved local maximum, both edge cells,
  and the original peak witnesses participate before the strongest/earliest
  greatest is selected and checked against the requested interval.
  Greatest-width tangents now refine from one shared center anchor without
  cache-history dependence, and exact-pole contacts use a fixed internal
  lattice independent of output sampling. The compatibility summary now
  reports fixed-site duration at the greatest location rather than global
  footprint lifetime. Detailed fixed-star labels reject surrounding whitespace
  and Solar System body identities before computation.
- **Topographic Lunar Contact And LOLA Robustness**: Event-profile acquisition
  now covers the complete declared `+/-12 km` relief shell, maps every
  intersecting 15-degree USGS STAC cell with exact pole/dateline topology, and
  fails closed on a missing cell, out-of-shell radius, noncanonical reference
  radius, malformed COPC node, or exceeded slice/tile/point/projection budget.
  One tile is streamed through all event slices and released before the next;
  the native reducer enforces half-open PA bins, a bounded bin count, finite
  perspective results, and overflow-safe scaled arithmetic without changing
  ordinary finite-path rounding. Contact search now distinguishes shallow
  unique tangencies from true plateaus through a two-sided variation witness,
  never probes outside its local/search window, rejects hidden sub-scan
  crossing pairs instead of relabeling them as tangencies, and applies its
  residual, bracket, containment, and chronology contracts again when the
  immutable result sequence is constructed.
- **Eclipse Geometry, Visibility, And Clock Integrity**: Defined native solar
  greatest eclipse by the DE441 Earth-reception lunar-shadow axis rather than
  angular conjunction, brought four modern event classes within one published
  second of NASA Solar Eclipse Search UT labels, and made
  spherical separation stable at coincident and antipodal limits. Hardened
  native and NASA-compatibility contact scans against invalid bounds,
  non-advancing steps, duplicate roots, and non-finite objectives; exhausted
  deterministic path solvers now fail explicitly instead of returning partial
  scientific results. Penumbral lunar eclipses are now first-class eclipse
  events, NASA-compatible lunar gamma is north-positive/south-negative, and
  NASA-compatible event data uses its declared catalog time basis coherently.
  Observer-local solar searches now require actual topocentric disk overlap
  with the Sun above the horizon; their event type, magnitude, radii, time, and
  kind filter all describe that same local maximum. Global central
  classification now uses the actual shadow-ray surface intersection, so
  annular events are no longer promoted to hybrid by a fictitious near-side
  observer, and rare-kind searches continue to the kernel coverage boundary
  instead of stopping after an undocumented 180 lunations. Solar path
  magnitude, width, greatest
  location, and local central-contact duration are bound to the solved site and
  validated against named NASA/GSFC total, hybrid, and annular products from
  1999, 2031, and 2032. Eclipse datetime
  inputs now cross UTC to UT1 once, while event and contact serialization
  convert UT1 back to UTC. Existing facade method signatures, the
  `EclipseEvent` field shape, FastAPI endpoint paths, and request/response
  schemas remain unchanged.
- **Eclipse Contact And Geographic Boundary Robustness**: Replaced positional
  lunar-contact assembly with a private signed-clearance pair solver that
  recovers phases shorter than the coarse scan, preserves truncated ingress or
  egress honestly, and represents a mean-limb limiting tangent in both phase
  fields under an explicit one-millimetre numerical coalescence policy. Native
  and NASA-compatibility contact models use the same physical threshold in
  their respective units. Geographic offsets now move on the Earth sphere,
  cross poles without clamping at `89.5` degrees, and canonicalize longitude
  only at an exact pole; solar greatest-location refinement uses that same
  tangent-plane topology. Stellar-graze searches never evaluate outside legal
  latitude, choose the nearest lawful public root, and derive occultation path
  north/south boundaries directionally from the known interior. Added named
  NASA evidence for the 2000 partial solar maximum and four lunar
  contact-duration products, including a separately bounded limiting
  penumbral case. The facade, public result vessels, FastAPI routes, and
  request/response schemas are unchanged.
- **NASA Lunar-Compatibility Apparent Reduction**: Corrected the
  NASA-facing lunar canon after executable intermediate-coordinate evidence
  showed that the omitted apparent reduction, rather than the DE441 versus
  VSOP87/ELP2000-85 ephemeris difference, dominated the former contact-time
  residual. The new default method,
  `nasa_shadow_axis_apparent_sun_moon`, evaluates both the Sun and Moon on one
  Earth-reception state, applies reception light-time and then annual
  aberration to each, and intentionally omits gravitational deflection,
  topocentric parallax, and atmospheric refraction. The historical geometric
  and retarded method identifiers remain explicit experiments. Named modern
  NASA/GSFC catalog maxima are now bounded at `10 s` with gamma bounded at
  `2e-4` Earth radii; ordinary detailed-figure contacts are bounded at `10 s`,
  and the limiting 2027 penumbral contacts retain a separate `30 s`
  robustness gate. Native lunar contacts retain their distinct `120 s` and
  `240 s` gates. Existing facade signatures, FastAPI paths, and
  request/response schemas are unchanged; NASA-compatible `canon_method`,
  `source_model`, and numerical values intentionally report the repaired
  model.
- **Polar Central-Path Geometry And Width**: Replaced the observer-local proxy
  for central-path geography with the forward DE441 reception-time shadow-axis
  intersection on WGS 84, rotated through true-of-date, physical UT1 GAST, and
  admitted polar motion. Central-line endpoints now solve the axis/ellipsoid
  tangencies, and greatest width is the full cross-track support span of the
  closed umbral or antumbral cone footprint rather than a centered spherical
  chord. Spherical-classification/WGS 84 divergence and incomplete one-limit
  footprints fail explicitly instead of emitting contradictory path data or
  publishing an open cone-arc span as physical width. Existing facade methods,
  `SolarEclipsePath` fields, FastAPI routes, and request/response schemas are
  unchanged.
- **Delta-T Source, Domain, And Time-Scale Truth**: Restored source-priority
  total Delta T through the 2026 handoff while preserving the raw HPIERS
  DE430/LE430 source basis; generic clock policy no longer guesses a downstream
  ephemeris and ambiently retargets that total to DE441. Reader-backed SPK
  computations now perform that separate composition only after deriving a
  coherent DE/LE identity from kernel summary content: DE430/LE430 remains on
  its declared basis, DE441/LE441 receives the source-owned historical tidal
  correction, and unmapped or conflicting historical bases fail closed.
  Modern direct-EOP values and explicit fixed, NASA-canon, and physical
  policies remain unchanged. Kernel filenames are not used as identity.
  Added an explicit
  100-year C0 bridge from the earlier polynomial at `-2100` to the first
  HPIERS row at `-2000`, while retaining `-2000` as the physical-policy floor.
  Hybrid/physical JD conversion now uses an exact private fraction-of-year
  coordinate. NASA-canon catalog paths retain their explicit month-midpoint
  rule, while general no-hint NASA transforms use the continuous coordinate
  and fail closed at non-invertible raw-polynomial boundary intervals.
  Planetary, node, eclipse, phase, sidereal, barycentric, and planetocentric
  callers now leave that year-coordinate choice to the named clock policy,
  removing ancient month-boundary reversals from their UT1-to-TT paths.
  EOP edge corrections taper to zero locally over one Julian year instead of
  biasing remote epochs, and admitted rows are no longer all described as
  measured. Computational guards are explicit at ±100,000 years and
  ±40,000,000 JD. These changes preserve facade method names and `/v1`
  response schemas.
- **Delta-T Epoch Integrity**: Restored the HPIERS-declared half-year cadence
  for 1950–2016 instead of collapsing its rounded HTML DATE labels. Modern
  USNO full-year and Jan–Apr aggregate means now sit at the mean epochs of
  their contributing first-of-month samples, rather than masquerading as
  January 1 point values. Unknown conflicting duplicate epochs fail closed;
  the two published conflicts retain explicit compatibility policy. The
  bridge/aggregate uncertainty scale is now `0.06 s`, covering the verified
  `0.052808 s` maximum daily residual against the bundled EOP snapshot.
- **Provisional Delta-T Boundary Semantics**: Recorded that the final `2026`
  aggregate product is a Jan–Apr partial mean. The slope derived from its
  representative epoch and the preceding aggregate epoch is provisional
  scenario policy, not an observed instantaneous derivative. The post-handoff
  mean preserves that admitted boundary value and slope before applying the declared
  `28 s/cy²` scenario curvature. `DeltaTBreakdown.era` remains a compatibility
  category rather than source-row provenance.
- **Delta-T Attribution And Provenance Honesty**: Quarantined the historical
  C04, GRACE, AAM, and OAM proxy artifacts from the admitted causal
  decomposition. Public `core`, `cryo`, `fluid`, and `residual` fields remain
  compatible and inspectable but are zero. Added source-owned HPIERS
  uncertainty handling, an explicitly uncalibrated future policy scale, a machine-readable
  data manifest, and corrected public doctrine and API documentation. Values
  beyond 2150 are explicitly scenario extrapolations, not validated forecasts.
- **Historical Civil-Time Coherence**: Before the admitted atomic UTC era
  begins on 1972-01-01, timezone-normalized civil Julian Days retain Moira's
  established UT1-proxy interpretation and TT is derived from that same
  coordinate. The non-authoritative pre-1972 `TAI-UTC = 10 s` compatibility
  placeholder can no longer displace ancient chart instants by minutes or
  hours. A monotonic smoothstep over the final civil day joins that proxy to
  the atomic rule, and the private inverse solves the same handoff by
  bisection. Private UT1-to-UTC result formatting now inverts the within-day
  UT1-TAI relation without smearing a positive leap second across the prior
  civil day. The low-level atomic helpers now implement the IAU SOFA
  1960-1971 UTC offset-and-drift segments and reject earlier UTC-to-TAI
  conversion rather than inventing atomic history.
  BCE-safe calendar decomposition now also carries a rounded `24:00:00`
  result into the next proleptic-Gregorian civil date instead of returning an
  invalid hour field.
- **Synastry And Davison Invariants**: Corrected relationship-network identity
  so pair and body nodes preserve caller-supplied chart labels instead of
  collapsing into hard-coded `A`/`B` or unqualified body names. Corrected
  Davison MC refinement so the circular `+180`/`-180` discontinuity cannot be
  mistaken for a root, made non-convergence explicit, and rejected antipodal
  or near-antipodal spherical locations where no unique geographic midpoint
  exists.
- **Synastry Truth Consistency**: Added validation tying result kind,
  condition state, relation kind, relation basis, method, correction mode, and
  policy flags together. Custom aspect-orb provenance now records a normalized,
  deterministic orb table rather than only a boolean marker.
- **Phenomena Search Geometry**: Greatest elongation now maximizes true
  great-circle planet-Sun separation, including ecliptic latitude, while east
  and west remain explicit branch policy. Perihelion and aphelion searches use
  bounded physical turning-point refinement, and invalid bodies, directions,
  non-finite epochs, and invalid search windows fail explicitly.
- **Phenomena Range And Threshold Safety**: Conjunction searches no longer
  return polished events outside the requested interval. Proximity searches
  refine the signed `-threshold` and `+threshold` crossings independently,
  reject the opposition wrap as a false bracket, retain slow-body crossings,
  de-duplicate boundary events, and share the exact cazimi, combust, and
  under-sunbeams thresholds with point-in-time solar-condition truth. Bounded
  resonance approximation now uses the closest lawful fraction and rejects
  identical-period bodies.
- **Planetary-Hour Solar Boundaries**: Replaced the declination-only refinement
  with the governing topocentric geometric solar-altitude crossing at
  `-0.833` degrees. Refinement now reaches 0.1-second time tolerance, rejects a
  crossing that escapes its local day, and fails explicitly when polar
  geometry supplies no sunrise or sunset instead of inventing a schedule.
- **Planetary-Hour Calendar And Window Policy**: The planetary weekday now
  follows local mean solar time at sunrise, including longitude and BCE-safe
  floor behavior. Engine inputs and sunrise/sunset/next-sunrise ordering are
  validated, temporal-hour boundaries are assembled contiguously from their
  shared endpoints, facade consumers use the canonical `hour_at(...)` lookup,
  and REST ISO timestamps serialize through Moira's BCE-safe calendar vessel.
- **House Geometry And Policy Enforcement**: House calculations now reject
  non-real, non-finite, and out-of-range location inputs; the REST house schema
  rejects latitude outside `[-90, 90]` and longitude outside `[-180, 180]`.
  Azimuthal geometry must produce exactly one ordered ecliptic cusp cycle, and
  Carter/high-latitude, polar-degeneracy, unordered-cycle, unknown-system, and
  configured fallback paths now preserve explicit policy and failure reasons.
  REST house calculations now pass UT1, rather than raw UTC JD, into the engine.
- **Planetary Frame Coherence**: Geocentric, heliocentric, planetocentric,
  Solar System barycentric, received-light, and admitted asteroid products now
  share the true-of-date ecliptic transformation. Geometric mode omits physical
  light-path corrections without silently changing output-frame meaning, and
  topocentric observer position and velocity are formed in the same declared
  frame as the corrected body vector.
- **Planetary Observer And Time Contracts**: `planet_at(...)`,
  `all_planets_at(...)`, and reduction surfaces now require the topocentric
  observer arguments as an all-or-none vessel and reject invalid centers or
  ambiguous coordinates. Astronomy facade and frame-position REST calls now
  convert aware UTC datetimes to UT1 before evaluation and report consistent
  UT1/TT metadata.
- **Published Planetary Speed Semantics**: `PlanetData.speed` is now the TT-day
  derivative of the same corrected geocentric ecliptic longitude that is
  returned to the caller, rather than a projection of an earlier raw state
  vector. Central differences govern normal coverage; second-order one-sided
  differences preserve lawful evaluation at kernel boundaries. Retrograde
  truth is derived from that published rate in both Python and admitted native
  bulk paths.
- **Native Payload Hardening**: Chebyshev, Type 13, smoothing-spline, and
  planetary evaluator entry points now reject empty, mismatched, non-finite,
  unordered, or otherwise unsafe payload shapes before native evaluation.
  Nutation evaluation releases the GIL around the full native series while
  retaining Python-owned readiness of the immutable coefficient tables.

### Changed
- **Release Artifact Admission**: Tag builds now fail before compilation when
  the tag, project version, public runtime version, dated changelog boundary,
  or release documents disagree. Every cibuildwheel artifact receives an
  installed native-import/version smoke, while the sdist receives Twine,
  forbidden-kernel-content, isolated-build, native-import, and version checks
  before the publish job can run.
- **Primary-Directions Transport Truth**: Kept all eight existing REST paths
  while replacing raw-string, duck-typed, and fallback-prone service behavior
  with canonical typed preset/policy/key resolution and real `PrimaryArc`
  reconstruction. Conflicting policies and ambiguous generic Ptolemy zodiacal
  requests fail closed. Omitted submitted arcs mean engine search; an explicit
  empty list means a lawful empty submitted evaluation; payloads are bounded
  to 4,096 arcs. Natal coordinates now construct the natal chart, observer
  coordinates own directional houses and geographic latitude, and zero
  longitude is preserved. Compact and reduction responses reuse one resolved
  calculation, `include_relations` gates serialization without mutating frozen
  profiles, and reduction provenance records requested/canonical policy, key,
  search mode, observer, and effective-house truth. Arc responses expose
  `solar_rate_explicit`; an empty profile retains `0.0` only as the transport
  compatibility sentinel for both arc extrema, while its zero counts and empty
  profile list remain the governing no-result truth.
- **Immutable Relationship Results**: Synastry truth, classification,
  relation, condition, network, overlay, composite, and Davison result vessels
  are frozen after validation. Composite planet/node maps, overlay placements,
  and custom-orb policy maps are defensive immutable copies; composite cusps
  are exposed as an immutable tuple.
- **Native Planetary Evaluation Lifetime**: The admitted default bulk
  planetary calculation resolves its required SPK segment evaluators once per
  public calculation and reuses them through Earth-state construction and
  light-time iteration, avoiding repeated mutex/LRU lookup while leaving cache
  ownership bounded by the kernel handle.
- **Operational Readiness Semantics**: `/health` remains an HTTP 200 liveness
  signal after a prewarm failure. `/ready` preserves its existing response body
  but now returns HTTP 503 whenever the planetary kernel or enabled prewarm is
  not ready, and HTTP 200 only when the worker can receive computational
  traffic.
- **Runtime Documentation**: Updated the native planetary-path and server
  boundary documentation to match the live Python-governed/native-strengthened
  architecture, and removed the stale README claim that SciPy is a required
  base runtime dependency.

### Performance
- Runtime dispatch selects the optimized AVX2 three-component Chebyshev kernel
  on capable hosts while scalar parity remains the correctness gate. Reusing
  resolved segment evaluators removes repeated native cache synchronization
  inside one bulk planetary calculation.
- In one fresh-process Windows/DE441 in-process `TestClient` smoke, opt-in
  prewarm moved the first full-chart cost into worker startup: startup changed
  from `0.286 s` to `2.626 s`, the first chart from `2.450 s` to `0.0083 s`,
  and an identical HTTP-cached chart remained about `0.0024-0.0028 s`. The
  observed private working set after prewarm was approximately `1.65 GiB` per
  worker. These figures are scoped performance evidence, not astronomical
  validation, and exclude TCP, TLS, reverse-proxy, and public-network latency.

### Compatibility
- Existing `Moira.speculum(...)` and `Moira.primary_directions(...)` positional
  parameters, all eight `/v1/primary-directions/*` paths, and established REST
  response fields are retained. New facade methods and truth fields are
  additive. Advanced search target/context lists and their reduction fields are
  additive; `speculum` and submitted-only `relations` request schemas remain
  scoped to their existing computational products. Recognized historical preset
  names remain explicit aliases;
  unsupported, conflicting, ambiguous, or scientifically invalid inputs that
  were previously coerced may now raise engine errors or return REST validation
  responses.
- The Topocentric signed-primary-motion preset is additive and search-only.
  Existing submitted-arc evaluation remains available under established
  doctrines, while signed-primary-motion requests containing submitted arcs
  fail explicitly because those vessels cannot attest the governing raw-arc
  sign.
- Existing `/v1/harmonics/*` paths and the age-harmonic route remain available.
  Single-H request schemas are widened compatibly from integer to real
  `harmonic`; range, sweep, and transit-forecast harmonic lists remain strict
  integers. The existing `orb` field remains the H1-reference/projected limit
  and is adapted to `HarmonicOrbPolicy`; the explicit `orb_policy` object and
  `/v1/harmonics/transit-forecast` route are additive.
- Historical `moira.aspects` declination imports, package-root exports,
  `Moira.declination_aspects_from_declinations(...)`, and
  `POST /v1/aspects/from-declinations` remain available. The legacy
  `AspectPolicy.declination_orb` input is adapted to the first-class
  `DeclinationAspectPolicy`.
- Existing facade method names, `/v1` computation-route paths, chart request
  models, and chart response payloads are retained. The server-prewarm change
  is operational and opt-in.
- The instantaneous solar Besselian admission is engine-only. It does not add
  a `Moira` facade method or FastAPI route and does not change existing eclipse
  event/path vessels, request/response schemas, or the native C++ substrate.
- Polar central-path repair preserves the existing `SolarEclipsePath` vessel,
  facade method, and REST schema. A central geometry with no closed two-limit
  footprint now fails explicitly instead of publishing an incomplete width.
- The solar visibility-footprint surface is additive. The existing
  `SolarEclipsePath`, `EclipseCalculator.solar_eclipse_path(...)`, and
  `POST /v1/eclipses/solar/path` contracts are unchanged. The new footprint is
  a zero-elevation, geometric mean-limb product; it does not claim atmospheric
  refraction, observer elevation, magnitude contours, or local apparent
  circumstances. Its REST enum domains are explicit, and its UTC timestamp
  strings retain BCE-safe astronomical year numbering outside Python's
  `datetime` range.
- The NASA lunar-compatibility repair changes no contact vessel, numerical
  solver, facade method, FastAPI route, request/response schema, native C++
  path, or kernel resource. It intentionally changes NASA-compatible
  `canon_method`, `source_model`, and numerical results; native eclipse
  semantics remain unchanged.
- The four detailed occultation-topology surfaces are additive. The existing
  four event-route and four path-summary-route paths, facade method signatures,
  and response-vessel field shapes remain unchanged. Existing profile-aware
  lunar-graze APIs continue
  to own arbitrary limb providers; those providers are intentionally excluded
  from the nominal two-sided topology because they can produce disconnected
  micro-topology. Left/right means intrinsic side relative to increasing UT1,
  not north/south latitude, and exact poles use canonical longitude zero.
- The topographic lunar-contact surface is additive and engine-only through
  direct imports from `moira.lunar_occultation_contacts` and
  `moira.lunar_limb`. It adds no `Moira` facade method, FastAPI route, OpenAPI
  operation, or request/response schema, and leaves the existing nominal
  occultation path and graze contracts unchanged.
- Code that mutates the relationship result vessels or their nested maps must
  switch to constructing a new value. Invalid phenomena, planetary observer,
  planetary-hour, and house inputs that were previously tolerated may now
  raise explicit engine errors or return REST validation responses.
- Readiness clients must treat HTTP 503 with the existing `ReadyResponse` body
  as "not ready". This corrects the previous HTTP 200/`ready=false` mismatch.

### Validation
- Added hash-chain and manifest-transition coverage for the additive Pancha
  Pakshi context decision, plus configured-reader, exact-sunset boundary,
  capability/admission gate, explicit-paksha, immutable-policy, aware-datetime
  adapter, service, REST, OpenAPI, and no-offset-materialization tests. These
  establish composition and transport integrity; they are not an external
  Pancha Pakshi oracle or independent-witness corroboration.
- Restored the complete sidereal external-reference fixture to the hosted
  acceptance lane, including the 1625 epoch under its documented
  `0.01`-degree cross-engine corroboration envelope; the obsolete deselection
  and narrower stale comment were removed.
- Added complete primary-directions engine, facade, and REST coverage for
  quadrant continuity, spherical-plane and inverse-domain behavior, immutable
  vessel and enum contracts, all canonical presets, target/relation/perfection
  identity, OA-Ascendant wiring, method/space capability, relation-specific
  rapt motion and target containment, explicit solar-rate provenance,
  house-cusp-derived aspect materialization, Morinus context identity,
  relation/profile arc ownership, ordered-network path realizability,
  submitted-versus-search mode, empty transport results, zero-longitude
  ownership, policy conflict rejection, reduction provenance, and preservation
  of all eight route paths. Historical
  evidence is classified honestly: Morin's rounded Hemminga Mars-to-Jupiter
  example is checked at `0.06 degree` with a current residual of about
  `0.11 arcminute`; Makransky's shared Campanus-Regiomontanus conjunction and
  Topocentric under-the-pole examples are checked at `0.03` and `0.02 degree`,
  respectively; Polich's named-pole oblique ascension is checked separately;
  the signed-primary-motion public preset emits the Makransky Topocentric
  product as one converse arc within the same `0.02 degree` gate while the
  traditional role-exchange result remains covered as a compatibility
  invariant;
  and Lilly's Vega and Jupiter-antiscion rows constrain only their historical
  zero-latitude zodiacal products. Bundled catalog fixtures remain regression
  evidence, and rounded Ptolemaic/Morinus examples remain scoped corroboration
  rather than whole-family authority proof. Added kernel-free and DE441-backed
  request-to-engine parity for all five advanced REST input families, including
  strict OpenAPI and resolved-provenance witnesses.
- Added engine, facade, REST, and OpenAPI regression coverage for fractional-H
  non-truncation, zero-Aries canonical-branch truth, strict numeric rejection,
  integer range doctrine, Addey projected/source orb equivalence, explicit and
  legacy policy provenance, and composite identity. Added sampled forecast
  coverage for both mixed-origin modes, complete-arc rejection of pairwise
  chains, immutable inputs/results, cross-origin body identity, window
  splitting, duration filtering, deterministic peak selection, request work
  bounds, serialization, and the no-parity/no-exact-contact claim boundary.
- Added individual primary-authority lunar-contact comparisons for every
  applicable P1, U1, U2, U3, U4, and P4 instant in named NASA/GSFC 2023
  penumbral, 2024 partial, 2025 total, and limiting 2027 penumbral figures.
  The fixture preserves the official figure URL and SHA-256 digest, published
  UT, adopted Delta T, and the figure-owned `VSOP87/ELP2000-85` plus `CdT
  (Danjon)` lineage. Comparisons occur on common TT: native UT1 crosses the
  content-identified DE441 clock and NASA-compatibility contacts use their
  stored TT fields. The repaired compatibility default is also checked against
  the 2025 figure's printed apparent geocentric Sun/Moon right ascension and
  declination, independently proving the light-time-then-annual-aberration
  reduction before contact solving. Ordinary per-instant cross-model ceilings
  are `120 s` native and `10 s` compatibility; the `0.0014`-magnitude 2027 row
  uses separate `240 s` native and `30 s` compatibility robustness ceilings
  while retaining its independent P4-P1 duration gate. Greatest eclipse uses
  a `10 s` compatibility gate. These are regression envelopes, not source
  precision, uncertainty estimates, UTC claims, or exact-model parity.
- Added a coherent NASA/GSFC 2015-03-20 polar central-path fixture pairing the
  official DE405 WGS 84 path table with its Besselian page. The executable
  DE441 comparison covers searched greatest time (`1 s`), greatest, five named
  central-line rows, and both tangency endpoints (`3 km`), greatest width
  (`3 km`), local central durations (`3 s`), magnitude (`0.005`), and physical
  cone clearance at available published limits (`3 km`). These are cross-model
  regression envelopes, not uncertainty estimates or full-atlas parity.
- Added NASA/GSFC Table 2 anchor comparisons for the 2003 one-limit-connected
  and 2006 two-limit/two-loop partial-visibility products. Contact and named
  north/south boundary anchors are compared on a common TT scale under honest
  `5 s` and `40 km` cross-model ceilings. Those bounds cover NASA's
  DE200/LE200 plus published `k1` convention versus Moira's DE441 physical
  mean-limb model; they are not uncertainty estimates. Both NASA rows are
  total solar eclipses whose penumbral footprints exercise the admitted
  topologies; an actually partial event's greatest point is invariant-backed,
  not externally anchored by those rows. NASA does not publish a dense
  numerical penumbral-track corpus for these products, so dense-track parity
  is not claimed. Independent unit and integration checks enforce contact
  ordering, immutable vessel contracts, closure of each penumbral component,
  and both admitted topology classes. Added a 1991 DE441 folded-envelope
  regression and a 1992 sub-minute polar-reversal regression proving stable
  component/segment graph identity at requested sample counts `9`, `99`,
  `181`, `257`, and `721`, shared fold incidence, continuous fixed-site maximum
  admission, and the absence of spatial splices.
- Added a bounded JPL Horizons authority fixture for the 2026-10-05 lunar
  occultation of Mars at the geographic North Pole. Airless topocentric
  apparent directions, equatorial angular diameters, and `UT1-UTC` establish
  outside/inside containment and place ingress and egress in separate `0.5 s`
  source brackets. Moira's DE441 contacts are admitted under a distinct `2 s`
  cross-model regression gate. The fixture records that Horizons used
  predictive EOP at retrieval and requires a post-event refresh; neither gate
  is an uncertainty estimate. Independent spherical invariants, rather than
  an unavailable external dense-track corpus, enforce boundary zero
  clearance, epoch/branch ordering, center-to-limit half-widths, total width,
  and polar continuity. Full external left/right track and width parity is not
  claimed, and existing IOTA ordinary-graze evidence remains separate. Added
  synthetic regressions for transitive connected-support coalescence,
  non-coalescing tangent-only support, cache-independent greatest tangents,
  multimodal component-global greatest selection and range suppression, and
  no more than `0.02 km` width change across two equivalent greatest witnesses
  `0.160973 s` apart.
- Added a frozen IOTA authority corpus for the observed 2024 Spica lunar-graze
  contact chronologies at two observing sites. The fixture preserves the
  reported disappearance/reappearance ordering, GPS-referenced UTC timings,
  site coordinates and heights, source timing-error semantics, source URLs,
  document lengths, and SHA-256 identities; a network-marked check detects
  authority-document drift. A separate network-marked DE441/LE441 and official
  LOLA-RDR comparison refreshes the STAC mapping, pre-admits sixteen exact COPC
  byte identities, and finds a unique optimum under the declared monotone
  same-kind matcher for all ten Dunham1 and all eight Dunham2
  observed contacts. Maximum absolute residuals are `0.381008 s` and
  `0.337355 s`, inside a Moira-owned `0.5 s` cross-model regression envelope.
  Dunham1 has no model-only contacts; Dunham2 retains and requires a leading
  model-only disappearance/reappearance pair about `1.529 ms` wide because it
  exceeds the declared `1 ms` scan feature guarantee. The
  envelope is not source uncertainty, absolute accuracy, or GRAZPREP/LUNLIMB
  parity.
- Added primary-authority per-field cross-model validation for instantaneous
  solar Besselian elements using named NASA/GSFC partial, total, hybrid, and
  annular rows at five TT epochs per event. The admitted residual envelopes
  are `1.0e-4` Earth equatorial radii for `x`, `y`, `l1`, and `l2`; `0.003`
  degrees for `d`; `0.007` degrees circular for `mu`; and `3.0e-6` for each
  dimensionless cone tangent. These compare NASA's VSOP87/ELP2000-82 and
  published `k1`/`k2` convention with DE441 and Moira's mean-limb physical
  radii; they are cross-model regression bounds, not exact parity or
  uncertainties.
- Added direct engine/facade/REST/OpenAPI coverage for Parallel and
  Contra-Parallel applying, exact, separating, stationary, and indeterminate
  motion, including signed-error formulas, equator/hemisphere rejection,
  immutable policy, provenance, and legacy import identity.
- Added focused regression coverage for synastry immutability and network
  identity, corrected-Davison wrap rejection and MC residual, antipodal
  midpoint ambiguity, spherical greatest elongation, conjunction range bounds,
  proximity threshold/wrap behavior, shared solar thresholds, planetary-hour
  solar-altitude and BCE behavior, house policy/ordering/input validation,
  planetary frame/rate/topocentric contracts, and server prewarm success and
  failure states.
- Added adversarial native constructor and payload tests plus AVX2/scalar
  Chebyshev parity at `1e-14` absolute tolerance. Existing DE441 engine/REST
  parity, house external-comparator, OpenAPI, cache, route-discovery, import,
  documentation-consistency, and native-boundary slices remain part of the
  focused verification posture.

### Western Electional Foundation

The following work was staged under the internal `4.3.0` version during
development but was never tagged or published. It is folded into and released
as part of `5.0.0`; public upgrade comparisons therefore begin at `4.2.1`.

#### Added
- **Lilly Classical Perfection**: Added the source-owned
  `lilly_1647_perfection_v1` event analysis through
  `lilly_perfection_at(...)`, `Moira.lilly_perfection_at(...)`, and
  `POST /v1/electional/western/classical-perfection`. The bounded response
  preserves exact-aspect, station, and sign-ingress chronology plus separate
  direct, translation, collection, prohibition, refranation, and frustration
  witnesses without scoring or complete-judgement claims.
- **Neutral Lunar Ecliptic Direction**: Added
  `LunarEclipticDirectionWitness` through
  `lunar_ecliptic_direction_at(...)`, the `Moira` facade, and
  `POST /v1/electional/western/lunar-ecliptic-direction`. The witness exposes
  latitude, latitude rate, independent hemisphere/motion states, adjacent
  exact sign-changing node crossings, event direction and UT1 time, and the
  nearest crossing relation without supplying a doctrinal node orb.
- **Neutral Lunar Connection Flow**: Added `MoonConnectionFlow` through
  `moon_connection_flow_at(...)`, the `Moira` facade, and
  `POST /v1/aspects/moon-connection-flow`. Callers explicitly select the
  previous-event window; results expose exact prior separation, current signed
  motion, next sign-bounded connection, event times, signed residuals, sign
  bounds, and no-event reasons without astrological interpretation.
- **Signed Aspect Motion Witness**: Added immutable, kernel-free
  `AspectMotionWitness` analysis through `aspect_motion_witness(...)`, the
  `Moira` facade, and `POST /v1/aspects/motion-witness`. Results expose the
  signed branch error, relative speed, orb rate, exactness, stationary reasons,
  orb policy, and caller-declared frame/timescale without claiming a future
  perfection search.
- **Sahl Moon Condition**: Added the source-owned, non-scored
  `sahl_moon_condition_v1` profile through the engine, facade, and
  `POST /v1/electional/western/sahl-moon-condition`, preserving the burnt-path
  and Arabic/Latin eighth-rule variants explicitly.
- **Sahl Fourth-House Matter Profiles**: Added separate building, demolition,
  land, wells/rivers, planting, and sowing profiles for *On Elections*
  §§43-55 through `sahl_matter_profile_at(...)`, the `Moira` facade, and
  `POST /v1/electional/western/sahl-matter-profile`. Responses preserve every
  source clause and typed indeterminacy without scoring or recommendation.
- **Dorotheus Moon Condition**: Added the eleven-clause
  `dorotheus_moon_condition_v1` profile and separate V.6.15 remedy witness
  through engine, facade, and REST.
- **Dorotheus Rooted Context**: Added `dorotheus_rooted_context_v1`, including
  Moon-as-root, Moon-sign-lord-as-outcome, the sign-bounded next connection,
  six V.31 matter families, and explicit ephemeral/radical natal contracts.
- **Dorotheus Construction Profile**: Added the first source-complete matter
  profile, `dorotheus_construction_v1`, covering V.2-V.7 through
  `POST /v1/electional/western/dorotheus-construction`.
- **Dorothean Matter Profiles**: Added named V.8 demolition, V.9 leasing, and
  V.11 land-purchase profiles through `dorotheus_matter_profile_at(...)`, the
  `Moira` facade, and
  `POST /v1/electional/western/dorotheus-matter-profile`. Results preserve
  source-ordered clauses and angular topics without scoring or recommendation.
- **Expanded Sahl Matter Registry**: Added independent lending, investment,
  purchase, sale, and business-partnership profiles beside the fourth-house
  sequence. Each profile retains its own source-ordered stakes, explicit
  inputs, unresolved vocabulary, and non-scored result rather than collapsing
  Sahl's subjects into one generic election.
- **Expanded Dorothean Matter Registry**: Added buying/selling, lunar-price
  timing, travel, ship acquisition/construction/launch, land/sea travel,
  partnership, debt/payment, and will-writing profiles. Sign-nature,
  Moon-flow, radical-context, and previous-event-window policies remain
  explicit wherever the source or computation requires them.
- **Western Electional Judgement**: Added
  `western_electional_judgement_v1` through the engine, `Moira` facade, and
  `POST /v1/electional/western/judgement`. It composes exactly one admitted
  matter profile with its Moon, rooted-context, perfection, remedy,
  fortification, unresolved-requirement, authority, and provenance evidence;
  the summary precedence is inspectable and never erases component truth.
- **Caller-Weighted Electional Ranking**: Added
  `western_electional_ranking_v1` and
  `POST /v1/electional/western/ranking` for 2–64 caller-supplied candidate
  instants. Only complete-under-profile results are scored, weights are
  explicit finite nonzero inputs, and impeded or indeterminate candidates
  remain in a separate evidence-bearing partition. No hidden historical
  weights, advice, or recommendation are introduced.
- **Observed Judgement Windows**: Added
  `western_electional_judgement_windows_v1` and
  `POST /v1/electional/western/judgement-windows` with explicit span, sample,
  evaluation, refinement, event-seed, window, transition, and cadence bounds.
  Event hints may seed partial refinement, but only an observed full judgement
  change is reported as a transition; the sampled product does not claim exact
  or continuously true boundaries.
- **Named Western Profile Windows**: Added
  `scan_western_electional_profile(...)`,
  `Moira.western_electional_profile_windows(...)`, and
  `POST /v1/electional/western/profile-windows` for bounded, discrete status
  scanning of the Ramesey, Sahl, and Dorotheus Moon profiles.
- **Scan Evidence**: Every scan point now reports its status, qualification
  truth, triggered rule IDs, and not-evaluable rule IDs.

#### Changed
- Dorotheus V.6 southern descent and V.7 northward crossing now consume the
  same neutral lunar geometry under separate source policies. Solar
  disengagement exposes both signed Sun-Moon conjunction motion and independent
  latitude evidence. All three clauses remain indeterminate where the primary
  wording supplies no interval or combination law.
- Sahl moment and profile-scan callers must explicitly select a burnt-path
  policy. The source-faithful selection performs no interval test; the two
  computational alternatives expose cited half-open `[199, 213)` and
  `[195, 225)` intervals.
- V.9 leasing requests now require an explicit lunar-flow previous-window
  policy and REST responses embed the complete neutral flow. The V.9 clause
  remains indeterminate because the surviving source does not assign the two
  events to its four leasing stakes.
- **Bounds Doctrine Correction**: Replaced the duplicated Ptolemaic table with
  the source-transmitted Ptolemaic terms and replaced the unsupported
  `chaldean` table with explicit `chaldean_day` and `chaldean_night` variants.
  Bounds table and lookup REST responses now carry their primary-source
  citation.
- Scan callers must explicitly provide `qualification_statuses`; Moira no
  longer assumes an all-clear predicate that some source-incomplete profiles
  cannot satisfy.
- Ramesey and Sahl scans reuse range-level void-of-course windows instead of
  rebuilding the same sign-level search at every sampled instant.
- The construction result now distinguishes `complete_matter_profile=true`
  from `complete_electional_judgement=false`. It remains
  `source_complete=true` and `numerically_complete=false` while unresolved
  source clauses remain visible.
- Dorotheus V.7 increasing-in-calculation now uses a visible signed lunar
  equation derived from the IERS 2010 mean lunar longitude; the existing REST
  construction clause exposes both longitudes and the equation direction.
- Dorotheus V.31 bad places now use the source-defined whole-sign places 3, 6,
  8, and 12 and are serialized as evaluated booleans through the rooted-context
  and construction REST responses. V.31 now exposes under-rays,
  made-unfortunate, Ascendant-relation, and bad-place testimonies separately;
  the non-exclusive "made unfortunate" phrase remains a typed source gate.
- Dorotheus V.6.29 now exposes the editorial ninth-part lord, sect-aware
  Lot-of-Fortune lord for inception, and next lunar connection for outcome as
  distinct REST witnesses. The Moon-sign lord remains the primary V.6.22
  outcome indicator; there is no selector or fallback between them.
- Ramesey's urgent-time remedy now reports non-erasing tri-state fulfillment
  with clause evidence. Moon/Ascendant and fortune/Ascendant conditions are
  evaluated, the planetary-hour lord is identified, and the source-undefined
  fortification predicates remain explicitly indeterminate.

#### Compatibility
- The Ramesey profile version is now `1.1.0`. Its remedy response replaces the
  instruction-only assessment literal with typed tri-state fulfillment fields.
  This intentionally corrects a currently unconsumed provisional electional
  contract.
- The previously unreleased Dorotheus rooted-context profile version is now
  `1.2.0` and its REST response adds fortification and supplementary-indicator
  witnesses.
- Bounds callers using the incorrect `chaldean` doctrine value must select
  `chaldean_day` or `chaldean_night`. This intentional correction prevents a
  sect-dependent table from being exposed under an ambiguous identifier. The
  ambiguous `CHALDEAN_BOUNDS` constant is replaced by
  `CHALDEAN_DAY_BOUNDS` and `CHALDEAN_NIGHT_BOUNDS`.
- All new electional routes and engine objects are additive relative to 4.2.1.
- `qualification_statuses` is required on the new, previously unreleased
  `/v1/electional/western/profile-windows` request.
- `moon_flow_policy` is required on the new, previously unreleased V.9 leasing
  matter-profile request so the prior-event window cannot be implicit.
- `burnt_path_variant` is required on the previously unreleased Sahl moment
  and Sahl scan requests. Provisional enum values were replaced by names that
  distinguish Sahl's indeterminate wording, the Dykes glossary/fall-degree
  interpretation, and the later fifteen-degree convention.
- The previously unreleased construction response replaces the misleading
  `complete_electional_judgement=true` value with
  `complete_matter_profile=true` and `complete_electional_judgement=false`.
- No score, rank, advice, recommendation, or continuous-boundary claim is
  introduced.

#### Validation
- Added synthetic-root and DE441 sign-change evidence, Dorotheus clause
  integration, public-export/facade governance, REST serialization, and OpenAPI
  coverage for lunar ecliptic direction.
- Added lunar-flow policy, event-order, signed-motion, no-event, DE441,
  leasing-embedding, facade, REST, and OpenAPI coverage.
- Added signed-aspect wrap, exactness, station, relative-standstill,
  missing-speed, branch-ambiguity, facade, REST, and OpenAPI coverage.
- Added primary-source rule, ambiguity-policy, public-export, facade, REST,
  OpenAPI, and DE441 integration coverage for all admitted electional objects.
- Added DE441 parity between optimized range-level VOC scanning and the
  independent single-moment Ramesey and Sahl evaluators.
- Added compact sample-witness and explicit-qualification contract tests.

## [4.2.1] - 2026-07-14

### Fixed
- **Relationship REST Completion**: `POST /v1/composite/chart` and
  `POST /v1/davison/chart` now embed position-owned aspect analysis under a
  required `aspects` member. Website consumers no longer need to extract the
  returned longitudes and make a second `/v1/aspects/from-longitudes` request.
- **Derived-Chart Policy Wiring**: The existing `tier`, `orb_factor`, and
  `include_nodes` relationship request fields now govern composite and Davison
  aspect analysis instead of being ignored by those two routes. Omitted or
  null values resolve to tier `1`, orb factor `1.0`, and node inclusion.

### Compatibility
- Existing composite and Davison chart, house, computation-truth,
  classification, relation, and condition-profile fields are unchanged.
- The response addition is intentional and additive. Strict REST consumers
  that reject unknown response members must admit the new `aspects` member.
- The standalone `POST /v1/aspects/from-longitudes` route remains available
  for arbitrary supplied-position products.
- Embedded analysis remains position-only: `applying` is null and no speed,
  stationary, retrograde, or applying/separating state is fabricated.

### Validation
- Added OpenAPI assertions that both relationship responses require the shared
  `AspectsFromLongitudesResponse` schema.
- Added REST policy-propagation and engine-parity checks for both composite
  methods and all five Davison methods, plus invalid-policy rejection.

## [4.2.0] - 2026-07-14

### Added
- **Western Electional Moon Condition**: Added the source-owned
  `ramesey_moon_condition_v1` profile through the engine, facade, and
  `POST /v1/electional/western/ramesey-moon-condition`. The result evaluates
  William Ramesey's ten impediments of the Moon as visible rule evidence; it
  is not a generic auspiciousness score or recommendation engine.
- **First-Class Derived-Position Analysis**: Added
  `aspects_from_longitudes(...)`, `Moira.aspects_from_longitudes(...)`, and
  `POST /v1/aspects/from-longitudes` for composite, Davison, harmonic,
  draconic, and other position-only products. The route does not fabricate a
  birth moment, speeds, applying/separating state, or ephemeris provenance.
- **Planet Reduction Visibility**: Promoted `PlanetReductionBreakdown`,
  `PlanetReductionStage`, and `planet_reduction_breakdown_at` through the
  curated public package surfaces.

### Fixed
- **Davison Planetary Time Scale**: Corrected every Davison variant to pass
  UT1 to the planetary evaluator. The previous path passed TT into a UT1
  parameter that performs its own TT conversion, shifting planetary positions
  by approximately 58 seconds of motion while leaving the declared chart
  instant unchanged.
- **Native SPK Coverage Enforcement**: Added explicit descriptor coverage
  metadata and bounded evaluation checks so out-of-coverage epochs do not
  silently enter native Type 13 evaluation.
- **Asteroid Observation Arcs**: Bound limited-arc bodies such as Icarus and
  Apollo to their actual observation intervals during unified-catalog builds,
  with retry handling for transient JPL responses and recorded provenance.

### Changed
- **Gauquelin Geometric Default**: The default horizon is now the explicit
  geometric center crossing at 0 degrees. Non-rising, circumpolar, and
  horizon-coincident geometries no longer emit invented numbered sectors;
  their sector-derived fields are `None` and their horizon status remains
  visible.
- **Progressed Integration Mesh**: `max_samples` now requires at least three
  samples so numerical integration cannot admit a degenerate mesh.
- **Composite Truth Completion**: Midpoint composites now populate the
  existing common house-system and midpoint-MC truth fields when those values
  are lawfully available.

### Compatibility
- Existing callers that intentionally require the former Gauquelin
  refraction-only threshold must now pass `horizon_altitude=-0.5667`
  explicitly. REST clients must allow nullable sector fields for bodies
  without ordinary rise/set geometry.
- Progressed-integration requests with `max_samples` below three are rejected.
- Davison longitudes change to the correctly cast midpoint or corrected
  instant; request and response shapes are unchanged.
- All other additions are additive. Existing composite and Davison REST
  envelopes remain distinct and retain their established routes.

### Validation
- Added DE441-backed Western electional regression cases plus kernel-free rule,
  facade, REST, and adversarial policy coverage.
- Added direct and REST position-only aspect tests for normalization, wrap
  geometry, exact orb boundaries, deterministic ordering, node filtering, and
  absent motion semantics.
- Added all-variant Davison invariants against canonical chart casts at each
  declared used instant, plus relationship REST parity.
- Added Gauquelin pole, boundary, immutability, undefined-sector, and explicit
  horizon-policy coverage; native DAF/SPK coverage tests; asteroid build and
  provenance tests; and strict release-surface checks.

## [4.1.0] - 2026-07-12

### Added
- **Church of Light Natal Astrodynes**: Added source-owned dignity, house-power,
  aspect, parallel, harmony/discord, mutual-reception, aggregation, summary,
  network, facade, and strict REST/OpenAPI products, validated against three
  captured Church of Light reports under explicit-geometry semantics.
- **Church of Light Progressed Astrodynes**: Added fixed carry, aspect-power,
  terminal, practical-distribution, minor/transit, reenforcement, and total-
  influence doctrine with exact and manual-staged arithmetic kept distinct.
- **Chart-Backed Progression Geometry**: Added Limiting Date, major and Minor
  Ephemeris Date, progressed M.C./Ascendant, radical/major/minor/transit
  terminal derivation, and complete chart assembly through the facade and
  `POST /v1/astrodynes/progressed/chart`.
- **Progressed Contact Search and Integration**: Added bounded one-degree
  entry/perfection/closest-approach/exit search, named minor reenforcement
  peaks, and explicitly Moira-owned variable-rate quadrature at
  `POST /v1/astrodynes/progressed/{search,integrate}`. Numerical policy,
  clipping, sample limits, convergence evidence, and the source constant-rate
  comparator remain visible.

### Fixed
- **Primary-Publication Discrepancy Honesty**: Recorded six inconsistent dated
  rows and three arithmetically inconsistent aggregate statements in the
  worked manual example. Executable results follow the declared formulas
  rather than reproducing publication errors.
- **Paran Crossing Work Duplication**: Removed repeated nutation evaluation and
  duplicate MC/IC solves, and added request-scoped immutable crossing reuse with
  active-reader identity retained for planetary truth.
- **Native Heliacal Parity**: Replaced the mislabeled five-term native nutation
  approximation with the packaged IERS 2000_R06 series, aligned fixed-star
  elongation, twilight, altitude, rising, setting, custom disappearance policy,
  Delta-T drift, and metadata with the Python doctrine, and made the validated
  native search the default fixed-star accelerator.

### Changed
- **Paran Performance**: Meridian searches now use verified Newton estimates
  with scan fallback; stellar and planetary horizon searches use analytic
  estimates followed by exact altitude refinement; latitude-independent fixed-
  star meridian truth is reused within bounded packet/field scopes. Public
  paran and rise/set contracts are unchanged.
- **Heliacal Performance**: Native catalogue searches use an explicit
  request-scoped nutation cache and a policy-owned eight-worker default. The
  Python manuscript remains selectable with `use_native_heliacal=False` for
  audit and differential validation.

### Validation
- The focused natal/progressed/facade/parity/adapter/search/REST acceptance set
  passes 177 tests under strict known-issue expiry. Documentation consistency,
  compilation, native import, OpenAPI registration, and diff checks also pass.
- The protected paran/rise-set/heliacal/native/server acceptance set passes 455
  tests. Full two-degree planet and star latitude sweeps agree with the original
  scan event sets and remain below 0.5 seconds timing tolerance; the opt-in
  local performance smoke passes all recorded budgets.
- Native R06/scalar/ERFA, initialization, concurrency, observable, single-star,
  catalogue, custom-policy, adversarial, and packet slices pass. A five-star
  setting search improved from 5.31 s to 0.97 s locally; a 175-star native
  search completes in 20.69 s while the Python comparator exceeded 120 s.

## [4.0.1] - 2026-07-12

### Added
- **Engine-Owned Paran Star Canon**: Added a deterministic working fixed-star profile for paran consumers, with Royal, Behenian, Ptolemaic, and working-canon membership tags exposed through the facade and `GET /v1/parans/star-canon`. The profile reuses sovereign catalog identities rather than duplicating coordinates or provenance.
- **Crossing Availability Diagnostics**: Added opt-in four-circle inventories that distinguish found crossings, always-above-horizon stars, always-below-horizon stars, and solver failures. Existing `find_parans()` and `natal_parans()` list-returning contracts remain unchanged; detailed callers use the new inventory surfaces or `include_crossing_inventory=true` over REST.
- **Natal Angular Contacts**: Added `natal_angular_contacts()` and `POST /v1/parans/natal-angular-contacts` as a distinct birth-moment product. It does not redefine the existing full-birth-day paran search.
- **Named Paran Policies**: Added immutable `permissive` and `star_planet_only` presets and propagated explicit policy selection through search, natal, site, field, contour, path, structure, and website packet requests.
- **Workspace Paran Packet**: Added `POST /v1/website/parans/packet`, composing selected canon, paran, crossing-inventory, natal-angular-contact, and optional heliacal truth without moving doctrine into transport.
- **Fixed-Star Field Proof**: Added live kernel-free Regulus-Capella coverage through site evaluation, grid sampling, field analysis, contour extraction, path consolidation, higher-order structure, and REST serialization.

### Fixed
- **Paran Field Threshold Serialization**: Restored threshold-crossing REST serialization by importing the response vessel used when a sampled field actually crosses its declared threshold.
- **Circumpolar Empty-State Honesty**: Paran consumers can now distinguish no match from a body that remains above or below the adopted stellar horizon throughout the search day.

### Changed
- **Documentation and Workspace Discoverability**: Expanded the README/LLM-facing Vedic API documentation and updated the paran, star, API-reference, OpenAPI, and implementation-checklist documentation for the admitted fixed-star surfaces.

### Compatibility
- This is an additive patch release. Default paran matching remains permissive, `find_parans()` still returns `list[Paran]`, and `natal_parans()` still searches the complete birth day.
- Star-star paran computation remains kernel-free. Optional heliacal packet content requires planetary-kernel access for solar ephemeris truth and reports an explicit warning when that prerequisite is unavailable.

### Validation
- The project `.venv` on Python 3.14 passed the complete paran/public-surface/rise-set/canon slice, kernel-free packet and fixed-star field routes, OpenAPI route discoverability, focused existing phenomena routes, documentation consistency, compilation checks, and all three offline JPL Horizons paran reference cases at the fixture's 5-second event-time tolerance.

## [4.0.0] - 2026-07-08

### Breaking Changes
- **Native-Only Kernel Reader**: The jplephem runtime fallback has been removed from `moira.spk_reader`. SPK segment types not supported by Moira's native reader now raise a sovereign error instead of silently falling back; jplephem is no longer a runtime dependency (it remains an optional dev-only parity oracle whose tests skip when absent).
- **Small-Body Kernel Loading**: The single-file supplemental kernels (`comets.bsp`, `centaurs.bsp`, `minor_bodies.bsp`) no longer auto-load; existing installs carrying those files stop using them. All small bodies now load from sharded Type-13 manifests (`moira/kernels/asteroids/manifest.json`, `moira/kernels/comets/manifest.json`) discovered under every kernel search root. The shard sets are distributed via website download rather than shipped in the wheel; `available_kernels` now reports planetary kernels only.
- **Canonical Comet Identity**: The canonical comet name in REST responses is now the standard numbered designation (`"1P/Halley"`, not `"Halley"`); curated short aliases remain accepted as inputs. The comet list route's `catalog_scope` is now `numbered_periodic_comet_identity_mapping`.

### Added
- **Yoga Engine** (`moira.yogas`, `POST /v1/yogas/evaluate`): 60 classical yogas per chart across six families — Pancha Mahapurusha (BPHS 75.1-2), Chandra (7, incl. the Parashara-strict Gajakesari gates and the full Kemadruma bhanga catalog), Surya (4), all 32 Nabhasa (BPHS Ch. 35 / Brihat Jataka Ch. 12 with Bhattotpala's precedence doctrine), Raja core (Kendra-Trikona with the 34.15 dilution, Yogakaraka, Dharma-Karmadhipati, Viparita with all three conflicting primary formulations as policy, Neecha Bhanga per Phaladeepika 7.26-30), and Dhana core (2-11, the Uttara Kalamrita IV.28 network with dusthana contamination, Lakshmi, Maha/Khala/Dainya Parivartana). Every yoga returns as a proof object: formation conditions with observed evidence, cancellation (bhanga) clauses evaluated first-class, per-yoga primary-source citations, and Nabhasa precedence suppression made visible.
- **Shadbala Completion**: Bhava Bala (house strength, Raman Part II — Bhavadhipati/Bhava Dig/Bhava Drishti per house with rank, no invented pass/fail threshold), inline Ishta/Kashta Phala on every planet (BPHS Ch. 27, derived from the displayed Uchcha and Chesta), Graha Yuddha transfer disclosure (`shashtiamsas_transferred`), the exact `ayanamsa_degrees` used, and the single-call `POST /v1/shadbala/chart/full` envelope (chart + profile + network + bhava from one support-truth derivation).
- **Upagrahas** (`moira.upagrahas`, `POST /v1/upagrahas/*`): the five kalavelas (Gulika, Kala, Mrityu, Ardhaprahara, Yamaghantaka — BPHS 3.66-70 eight-fold day/night division with ascendant materialization) with portion-point, Mandi-mode, and lord-sequence lineage policies, plus the five Sun-derived upagrahas (BPHS 3.61-64) with the verse-stated self-check (Upaketu + 30° ≡ Sun) enforced as an invariant.
- **Avasthas** (`moira.avasthas`, `POST /v1/avasthas/evaluate`): Baladi (with Vriddha honestly unnumbered), Jagradadi, Deeptadi as four per-source rule tables (BPHS-9 / Saravali-9 / Jataka-Parijata-10 / Phaladeepika-11 — never merged), and the six non-exclusive Lajjitadi flags with evidence strings.
- **Jaimini Extended** (`moira.jaimini_extended`, `POST /v1/jaimini/extended/*`): rasi drishti, arudha padas A1-A12 (Rath/JHora exception default, Raman variant as policy; classical-seven vs Jaimini co-lords lordship), argala with virodha pairs and the Ketu reversal, karakamsa with both lineage readings named (Rath D9 vs K.N. Rao D1 — never collapsed), and first-cycle Chara Dasha in K.N. Rao's named lineage.
- **Ashtakavarga Refinements**: kakshya-level transit evaluation (`kakshya_transit`, JP II.71 Saturn-first lord order; favorability tests the specific kakshya lord's contribution) and Shodhya Pinda (`shodhya_pinda`, BPHS Ch. 69 Rasi+Graha Pinda with verified multiplier tables), validated exactly against BPHS's own worked example (Sun 148, Moon 158) and Patel's Standard Horoscope; served at `POST /v1/ashtakavarga/{kakshya-transit,shodhya-pinda}`.
- **Vimshopaka Bala + Vargottama** (`POST /v1/varga/vimshopaka`): the BPHS 20-point varga-dignity strength over all four classical groups with per-division vargavishwa breakdown, plus vargottama detection.
- **Tara Bala + Chandra Bala** (`POST /v1/muhurta/personal/score`): the nine-tara cycle and Chandra Shuddhi (with Chandrashtama flagged and double-weighted) as a natal-personalized muhurta overlay; the long-dormant Tara placeholder in `_classify_nakshatra` now computes.
- **Sade Sati** (`moira.sade_sati`, `POST /v1/sade-sati/{status,windows}`): phase classification (rising/peak/setting) with Ashtama and Kantaka Shani flags, and kernel-timed phase windows via Saturn sidereal sign-ingress bisection with retrograde re-entries as separate honest windows.
- **Numbered Periodic Comet Catalog**: 497 comets (1P-516P) from JPL Horizons as sharded Type-13 kernels (1600-2500, sub-mas interpolation fidelity, apparition-dependent accuracy honestly recorded in the manifest), with a data-driven `COMET_NAIF` registry.
- **Unified Asteroid Catalog**: 1,382 asteroids (up from 369) covering all 119 asteroid families, rebuilt from JPL Horizons at 1600-2500 as 56 Type-13 shards with generic multi-manifest discovery.

### Fixed
- **Primary Directions**: Morinus directions corrected to Morin's Book 22 law; converse directions computed by role exchange rather than arc negation; raw requested-key tokens preserved verbatim.

### Changed
- **Progressions OpenAPI Depth**: the full dispatched progression method menu is advertised as enums in the OpenAPI schema.
- **Port Compliance**: `comets.py`, `shadbala.py`, and `ashtakavarga.py` no longer carry `from __future__ import annotations` (Python 3.14 port standard).

### Validation
- Every new Vedic engine was implemented from primary-source research passes (BPHS Santhanam, Brihat Jataka, Saravali, Phaladeepika, Uttara Kalamrita, Jataka Parijata, Jaimini Upadesa Sutras across editions, Patel & Aiyar 1957, Raman) with per-rule citations; source disagreements are policy switches or recorded notes, never silent choices. Shodhya Pinda reproduces BPHS Ch. 69's own worked example to the digit. The comet and asteroid catalogs verify at sub-mas interpolation fidelity against fresh Horizons queries. ~400 new unit and route tests pass in the project virtual environment.

## [3.4.3] - 2026-07-04

### Added
- **Draconic Chart Frame**: Added the node-anchored `moira.draconic` module (`draconic_longitude`, `draconic_positions`, `draconic_chart`, `draconic_chart_from_positions`, and the `DraconicAnchor` / `DraconicChart` / `DraconicPosition` vessels) exposed through the facade, plus a bounded `/v1/draconic/*` REST family — longitude rotation, caller-supplied positions, and engine-backed chart — for mean- and true-node draconic frames.
- **Chart-Shape Handle Identity**: Added an authoritative `handle_bodies` frozenset to the `ChartShape` vessel and its `ChartShapeResponse`, separating the display label (`handle_planet`, e.g. `"Neptune/Pluto"`) from the actual handle body set, enforced by real `__post_init__` invariants (non-empty, subset of `clusters[1]`, disjoint from `clusters[0]`).

### Fixed
- **Draconic Longitude Precision**: `draconic_longitude` now reduces both operands to `[0, 360)` before subtraction, so multi-revolution longitudes reach the rotation by one exact floating-point path.
- **Seesaw Seam Classification**: Fixed `chart_shape` Seesaw detection so a clean two-cluster chart with one cluster crossing the 0/360 longitude seam is no longer misclassified as Splash (VALIDATION CODEX RULE-20).

### Changed
- **Chart-Shape Doctrine Docs**: Synced the frozen chart-shape docstrings and VALIDATION CODEX to the implemented behavior — bowl-core Bucket metrics, the strict `> 60` handle threshold, tight conjunction-pair handles, unconditional Splash fallback, and seam-safe Seesaw.

### Validation
- Draconic and chart-shape engine unit tests, docstring governance, and the draconic and relationship REST route tests pass in the project virtual environment. The new public surface is additive; existing facade and REST semantics are unchanged.

## [3.4.2] - 2026-06-27

### Added
- **Website Planet Pipeline Visibility**: Added first-class per-stage planetary reduction breakdowns to the REST pipeline surface, including ordered physical stages, arcsecond longitude deltas, compatibility intermediate longitudes, and pre-topocentric geocentric longitude.

### Validation
- This is a REST transport and visibility patch release. It exposes already-owned apparent-reduction truth for HTTP clients and does not intentionally change final planetary position semantics.

## [3.4.0] - 2026-06-24

### Added
- **Profile Bundle REST Routes**: Added REST profile-bundle routes composing Western and Vedic chart profiles for frontend and workspace consumers.
- **Mixed-Subject Astrocartography Routes**: Added mixed-subject astrocartography REST routes.
- **Modern-Planet Dignities**: Extended dignity computation to include modern planets and additional policies.

### Changed
- **Solar Event Approximation**: Refined solar-event approximation with supporting tests.

### Validation
- Release cut with Git LFS checkout skipped during the PyPI release workflow.

## [3.3.4] - 2026-06-15

### Fixed
- **PyPI macOS Wheel Runners**: Replaced the retired `macos-13` Intel runner with the supported `macos-26-intel` label and moved the arm64 macOS wheel job to `macos-26`.

### Validation
- This is a packaging and release-workflow patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.3] - 2026-06-15

### Fixed
- **PyPI Wheel Matrix Scope**: Constrained Linux and Windows release wheels to 64-bit architectures and updated cibuildwheel to `4.1.0` so the release workflow can build the intended CPython 3.10-3.14 wheel set without entering unsupported 32-bit native-extension targets.

### Validation
- This is a packaging and release-workflow patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.2] - 2026-06-15

### Fixed
- **PyPI Wheel Matrix Build Constraints**: Updated the PyPI release workflow to use current cibuildwheel dependency constraints so isolated wheel builds can satisfy the `packaging>=24.2` build requirement on macOS and other runners.

### Validation
- This is a packaging and release-workflow patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.1] - 2026-06-15

### Fixed
- **PyPI Wheel Build Isolation**: Declared `packaging>=24.2` in the build-system requirements so isolated wheel builds satisfy modern setuptools license-expression normalization on GitHub Actions.

### Validation
- This is a packaging-only patch release. No runtime computation, REST route, or facade semantics changed from `3.3.0`.

## [3.3.0] - 2026-06-15

### Added
- **Expanded FastAPI Surface**: Admitted a large set of typed REST route families for Vedic, classical, spatial, catalog, specialist, electional, orbital, phenomena, sidereal utility, and harmonic products.
- **Server Transport Standards**: Added backend standards and transport design records for the newly admitted route families, including explicit deferrals for doctrine-heavy or specialist surfaces.
- **Facade Convenience Parity**: Added `Moira` convenience wrappers for admitted Vedic, Huber, Nine Parts, Lord of the Orb, and sidereal utility surfaces while preserving owner-module doctrine.
- **Astrocartography Rendering Support**: Added a rendering-adapter workflow and server support for map-oriented astrocartography consumers.

### Changed
- **REST Reference Truth**: Updated the REST reference and architecture ledgers to reflect the live server route registry and facade/init gap audit.
- **Route Admission Discipline**: Formalized post-Phase-9 and post-Phase-10 workflow boundaries for sidereal chart derivation, small-body/star astrocartography admission, and rendering support.

### Validation
- This release expands public transport, facade, standards, and documentation surfaces. The changes are additive and route-supporting; no intentional breaking public API changes were made.

## [3.2.4] - 2026-06-08

### Fixed
- **Release Lineage**: Reconciled the `v3.2.1` release branch into `main` so the release tag is contained in current history.
- **House Boundary Membership**: Preserved the documented half-open interval rule for `assign_house()`, so longitudes strictly below a closing cusp remain in the prior house while exact cusp hits enter the opening house.
- **Package Data Policy**: Made wheel builds obey the declared package-data policy so `.bsp` kernels are not silently bundled into PyPI artifacts.
- **Version Truth**: Aligned runtime metadata and release-facing doctrine tests with the `3.2.4` package version.

## [3.2.3] - 2026-05-30

### Added
- **Primary Directions REST Surface (P8-14)**: Completed the dedicated per-significator condition surface with a first-class typed `PrimaryDirectionsConditionResponse`, exposing `evaluate_primary_direction_condition` results through the `/profile` endpoint when `include_condition=true`.
- **Policy Ergonomics**: Extended conventional time-key derivation (`_get_chosen_key`) to all seven supported presets in the primary directions router, with explicit client key override always taking precedence.

### Changed
- Improved hardening and documentation around combined policy + submitted-arcs + enrichment paths in the primary directions transport layer (P8-14). Remaining 422 cases on the richest combinations are now explicitly documented rather than masked.

## [3.2.2] - 2026-05-23

### Added
- **High-Latitude House Solver**: Added experimental branch-aware Placidus solver (`experimental_placidus`) to search for unique ordered cusp cycles under polar conditions.
- **Supplemental Kernel Diagnostics**: Enhanced engine initialization to handle optional supplemental kernels and report missing ones gracefully.

## [3.2.1] - 2026-05-18

### Fixed
- **Adversarial House Singularities**: Corrected coordinate normalization at 360-degree bounds, zero-vector inputs, and resolved julian day/SPK evaluation edge cases (DEF-004/005/006 and TDF-001/002/003).

## [3.2.0] - 2026-05-15

### Added
- **Native Planetary Evaluator**: Introduced C++ `NativePlanetaryEvaluator` executing center chaining, rotation matrix operations, and light-time iterations natively.
- **SPK Kernel Compiler (GUI)**: Added Tkinter-based custom SPK Type 13 builder utility (`moira-daf-writer`).
- **Aspect Properties**: Added `is_partile` and `is_platic` properties to `AspectData`.
- **Zodiacal Helpers**: Added `house_of` function in `moira.houses`.
- **Sovereign Shards**: Bundled Git LFS-tracked Type 13 asteroid kernels (`sb441_type13`) for license-independent asteroid fleet calculations.

### Changed
- **Asteroid Pipeline**: Routed asteroid evaluations through the shared apparent reduction pipeline (`_apparent_geocentric_ecliptic`).

## [3.1.0] - 2026-05-10

### Added
- **Native House Engine**: Integrated C++ native house system engine bindings.

## [3.0.0] - 2026-05-08

### Changed
- **Immutable Result Semantics**: Frozen dataclass structures across all primary coordinate and chart outputs to enforce immutability.

## [2.2.0] - 2026-05-04

### Added
- **Sovereign Star Registry**: Full implementation of a license-independent, Gaia DR3-anchored registry of 1,809 named stars with sub-arcsecond epoch propagation.
- **Harmograms Engine**: Mathematically explicit research engine for planetary intensity spectra (Strata H1-H5), including zero-Aries parts and spectral projection.
- **Astrocartography (ACG)**: Planetary lines (MC, IC, ASC, DSC) and zenith-nadir calculations with full topocentric support.
- **Multiple Star Systems**: Keplerian orbital mechanics for visually resolvable binaries (Sirius AB, Alpha Centauri AB) across VISUAL, WIDE, SPECTROSCOPIC, and OPTICAL types.
- **Solar/Lunar Eclipse Cartography**: Besselian sample-based shadow band and contour extraction.
- **Void of Course Moon**: Integrated window detection and last-aspect analysis.
- **Jones Chart Shapes**: Automatic temperament type classification (all 7 Jones shapes).

### Changed
- **Facade Refactor**: Introduced `CoreFacadeMixin` and a unified constants library to modularize astronomical calculations.
- **Registry Performance**: Optimized star lookup speeds through binary-mapped substrate headers.

## [2.1.3] - 2026-04-25

### Added
- **Galactic Porphyry Houses**: Implemented the Galactic Porphyry house system with tests.
- **Triplicity Backend**: Added the triplicity computation backend with tests and documentation.
- **Electional Scoring**: Added scoring for electional windows with refined boundary handling.
- **Facade Mixins**: Introduced internal facade mixins (kernel, predictive, relationships, spatial, special topics).
- **Docstring Governance**: Added docstring-governance tests and behavior-preservation checks.

### Changed
- **Placidus Cusps**: Enhanced Placidus cusp calculation with a Newton-Raphson solver.
- **APC Houses**: Completed the APC primary-source re-derivation and oracle campaign.
- **Delta T Hybrid Model**: Refined physical Delta T accuracy and uncertainty; added tests.
- **SPK Reader**: Refactored SPK reader integration onto the KernelReader protocol.

### Fixed
- **README**: Corrected the DOI badge link format.

## [2.1.2] - 2026-04-16

### Changed
- **Code Cleanup**: General code and test cleanup across modules.

## [2.1.1] - 2026-04-16

### Added
- **Swiss Ephemeris Attribution**: Added source attribution for Swiss Ephemeris-derived code in `houses.py`.

## [2.1.0] - 2026-04-16

### Added
- **Traditional Dignities**: Complete Hellenistic and Medieval dignity suite including Sect, Hayz, Domicile, Exaltation, Triplicity, Terms, and Face.
- **Predictive Techniques**: High-fidelity implementations of Firdaria, Zodiacal Releasing (Valens method), and Annual/Monthly Profections.
- **Vedic Suite**: Comprehensive Jyotish tools including Vimshottari Dasha, Varga/divisional charts (D9, D10, D12, etc.), Shadbala, Ashtakavarga, and Panchanga.
- **Longevity Engine**: Hyleg and Alcocoden calculation with explicit planetary condition profiling.
- **Ayanamsa Systems**: Implementation of 40+ sidereal systems including star-anchored "True" ayanamsas.
- **Primary Directions**: Placidus semi-arc and mundane directions with speculum computation.
- **Heliacal Phenomena**: General visibility surface (V5) for rising/setting, acronychal events, and lunar crescent visibility.
- **Fixed Star Lore**: Integration of 499 Arabic Parts (Lots) and 36 Hermetic decans with ruling stars.

## [2.0.4] - 2026-04-15

### Added
- **Comet SPK Kernel Builder**: Added a script to build comet SPK kernels from JPL Horizons data.

### Changed
- **License Remediation**: Refined the license-remediation log and removed Swiss Ephemeris references from documentation.

## [2.0.3] - 2026-04-10

### Changed
- **Release Maintenance**: Version bump to 2.0.3 (release/CI maintenance; no distinct runtime changes).

## [2.0.2] - 2026-04-10

### Fixed
- **CI Hardening Gate**: Stabilized the hardening gate so it runs without kernels.

## [2.0.1] - 2026-04-10

### Fixed
- **CI Workflows**: Fixed acceptance and hardening workflow failures.

## [2.0.0] - 2026-04-10

### Added
- **Phase α Accuracy Certification**: Transition to a sub-arcsecond accurate substrate grounded in IAU ERFA/SOFA standards.
- **JPL DE441 Support**: Integration of high-precision long-term planetary ephemerides.
- **IAU 2006 Standards**: Implementation of the full IAU 2000A/2006 precession and nutation models.
- **Relativistic Reduction Pipeline**: Geometric positions corrected for light-time, gravitational deflection, annual aberration, and frame bias.
- **Unified Facade**: Introduction of the `Moira` class and `Chart` objects as the stable public surface.

## [1.2.1] - 2026-04-06

### Fixed
- **Facade Bugs**: Fixed latent facade bugs.

### Changed
- **Galactic Positions**: Refactored galactic position calculation to convert Julian date from UT.

## [1.2.0] - 2026-04-06

### Added
- **Classical Framework Modules**: Added the essentials, classical, and predictive astrology framework modules.
- **Quadrant / Huber / Manazil**: Added Rudhyar quadrant emphasis, the diurnal quadrant framework, the Huber engine, and the Manazil engine, with tests.
- **API Drift Guards**: Added public-API drift tests and facade duplicate-entry detection scripts.
- **Eclipse Convenience**: Added a module-level `next_solar_eclipse_at_location` wrapper.

### Changed
- **Kernel Safety**: Improved error handling in `daf_writer` and hardened `download_kernels`.

## [1.0.3] - 2026-04-05

### Added
- **Synodic Phase Detection**: Added phase detection for synodic phases.
- **Dispositorship**: Added modern and multi-doctrine dispositorship foundations and handling.
- **Kernel Management GUI**: Added a Tkinter kernel-management GUI and auto-discovery of planetary kernels.
- **Apparent Magnitude**: Added apparent-magnitude calculations with tests.
- **Repository Hygiene**: Added issue/PR templates and fixed cross-repo pytest collection bleed.

### Changed
- **Ephemeris Handling**: Refactored ephemeris handling and expanded kernel documentation.

_(Version 1.0.2 was skipped.)_

## [1.0.1] - 2026-04-01

### Fixed
- **Kernel Download Links**: Corrected the JPL DE441 kernel download links in the README and `download_kernels.py`.

### Changed
- **README**: Updated to reflect stable status and improved kernel handling.

## [1.0.0] - 2026-04-01

### Added
- **Initial Stable Release**: Core planetary positions, house systems (17 systems), and zodiacal aspects.
- **Kernel Management**: Integrated CLI and GUI tools for JPL kernel acquisition and configuration.

## [0.4.0] - 2026-03-27 — ACCIDENTAL TAG

- This tag was cut from a commit reporting "No code changes detected; skipping commit" and is out of sequence with the surrounding `0.1.x` development line. It introduced no changes and should be treated as an accidental tag; recorded here only for provenance.

## [0.1.7] - 2026-04-01

### Added
- **Kernel Path Resolution**: Added kernel path resolution and download functionality.

### Changed
- **Delta T**: Delta T refinements.

## [0.1.6] - 2026-03-30

- Release/version marker tagged immediately after 0.1.5 with no distinct code changes.

## [0.1.5] - 2026-03-30

### Added
- **Primary Directions Subsystem**: Added the primary-directions subsystem — roadmap, doctrine, core classes, presets, and Placidus rapt-parallel logic — with tests.
- **Physical Delta T**: Added planetary, stellar, and physical Delta T modules, including a physics-based hybrid computation with OAM/AAM proxy data and validation.

## [0.1.4] - 2026-03-27

### Added
- **Star Catalog**: Added a comprehensive star catalog with Gaia DR3 integration and constellation-specific APIs.
- **Egyptian Bounds**: Added the Egyptian bounds subsystem with tests.
- **Variable-Star Condition Profile**: Added `VarStarConditionProfile` and related void-of-course snapshots.

### Changed
- **Dependency Removal**: Removed executable dependence on Gaia loaders and Swiss star files; constellation modules now resolve by star name.
- **Corrections**: Enhanced atmospheric refraction and geocentric corrections.

## [0.1.3] - 2026-03-25

### Added
- **Multi-Body Deflection & Refraction**: Enhanced gravitational deflection with multi-body support and added atmospheric refraction.
- **Void-of-Course Tests**: Added comprehensive void-of-course tests covering all VALIDATION CODEX rules.

### Changed
- **Performance**: Added NumPy support for rotation-matrix composition; improved lazy loading and chart calculation.

## [0.1.2] - 2026-03-24

### Added
- **NumPy Nutation Acceleration**: Added NumPy acceleration for nutation calculations.

### Changed
- **Packaging**: Configured the PyPI publishing workflow and set the package name to `moira-astro`.

_(Version 0.1.1 was skipped.)_

## [0.1.0] - 2026-03-24

### Added
- **Initial Public Release**: First public release of the Moira astronomy-first astrology engine, establishing the public API and foundational modules (orbits, stars, planets, phenomena).
- **Gaia DR3 Integration**: Added Gaia DR3 star-catalog download and processing and the Light Box Doctrine for transparent computation.
- **Core Subsystems**: House systems, parans, synastry, void-of-course Moon, variable stars, and an eclipse catalog, with extensive unit and integration tests.
- **Packaging**: GitHub Actions workflow for PyPI publishing.

---

_Entries for versions 0.1.0 through 2.1.3 (and 3.4.0) were reconstructed from git commit history and may be less detailed than contemporaneously written entries. Version tags 0.4.0 and 0.1.6 are recorded as accidental/marker tags._
