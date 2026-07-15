# Changelog

All notable changes to the Moira project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.3.0] - 2026-07-15

### Added
- **Sahl Moon Condition**: Added the source-owned, non-scored
  `sahl_moon_condition_v1` profile through the engine, facade, and
  `POST /v1/electional/western/sahl-moon-condition`, preserving the burnt-path
  and Arabic/Latin eighth-rule variants explicitly.
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
- **Named Western Profile Windows**: Added
  `scan_western_electional_profile(...)`,
  `Moira.western_electional_profile_windows(...)`, and
  `POST /v1/electional/western/profile-windows` for bounded, discrete status
  scanning of the Ramesey, Sahl, and Dorotheus Moon profiles.
- **Scan Evidence**: Every scan point now reports its status, qualification
  truth, triggered rule IDs, and not-evaluable rule IDs.

### Changed
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
  and construction REST responses. Broader "made unfortunate" semantics remain
  uncomputed.

### Compatibility
- Bounds callers using the incorrect `chaldean` doctrine value must select
  `chaldean_day` or `chaldean_night`. This intentional correction prevents a
  sect-dependent table from being exposed under an ambiguous identifier. The
  ambiguous `CHALDEAN_BOUNDS` constant is replaced by
  `CHALDEAN_DAY_BOUNDS` and `CHALDEAN_NIGHT_BOUNDS`.
- All new electional routes and engine objects are additive relative to 4.2.1.
- `qualification_statuses` is required on the new, previously unreleased
  `/v1/electional/western/profile-windows` request.
- The previously unreleased construction response replaces the misleading
  `complete_electional_judgement=true` value with
  `complete_matter_profile=true` and `complete_electional_judgement=false`.
- No score, rank, advice, recommendation, or continuous-boundary claim is
  introduced.

### Validation
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
