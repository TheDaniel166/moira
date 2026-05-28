# Moira Server Full Engine Exposure Plan

Version: 1.4
Date: 2026-05-28
Status: Governing expansion plan after phases 1-7; remaining expansion begins at phase 8
Scope: Full public engine exposure through REST, subject to server-boundary law

This document defines the remaining work required to expose the full
transport-admissible Moira engine through `moira_server`.

It sits downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/threading.md`
- `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`

---

## 1. Core Rule

"Full engine exposure" does not mean "HTTP-wrap every file in the repository."

It means:

- expose the full stable public computational surface
- preserve canonical engine truth in transport
- classify non-transport-worthy surfaces honestly
- keep forbidden lifecycle and admin behavior out of request flow

The server must expose:

- stable public engine computations
- typed public result families
- policy-bearing truth where the engine already exposes it

The server must not expose, through normal request flow:

- kernel lifecycle mutation
- UI modules
- internal helper modules
- export-governance internals
- native binding internals as a separate public doctrine layer
- request-triggered data acquisition or kernel download orchestration

---

## 2. Present State

The implemented server already exposes these route families:

- operational health and kernel readiness
- chart construction and houses
- single-body and sky positions
- transit search and ingresses
- solar, lunar, and planetary returns
- lunar phase convenience
- batch charts, transits, returns, events, and progressions
- visibility assessment and `visibility_tonight`
- stations, void-of-course, rise/set, eclipse summaries and local
  circumstances, solar eclipse path geometry, occultation summaries,
  occultation path geometry, heliacal event search, paran core search, and
  paran site/field/contour/structure products
- annual, monthly, and schedule-based profections

This is the completed first wave.

The remaining work is expansion, not bootstrap.

---

## 3. Exposure Target Set

The target is the full public computational engine, classified into three
transport stances.

## 3.1 Direct REST Candidates

These are admissible as ordinary request/response endpoints:

- event searches
- chart-comparison and relationship computation
- progression and direction techniques
- Vedic and classical doctrine outputs
- spatial mapping outputs
- catalog-backed body and star computation
- specialist analytical surfaces

## 3.2 Heavy Or Async REST Candidates

These are admissible, but should be exposed either with:

- explicit batch forms
- asynchronous job forms
- bounded input windows
- paging or sampling controls

Examples:

- large occultation path products
- paran field sampling and contour extraction
- astrocartography grids
- catalog-wide star or small-body scans
- large electional scans

## 3.3 Not Part Of Ordinary Public Compute Routes

These must remain out of ordinary request flow, or belong to a separate
admin/offline plane:

- `set_kernel_path`, `swap_reader`, `reset_singleton`
- `download_kernels.py`
- `kernel_manager_ui.py`
- `daf_writer_ui.py`
- `_facade_*` private layers
- `_export_governance/*`
- direct native binding exposure as a separate public surface

Conditional case:

- `daf_writer.py` is computationally real, but it is an artifact-authoring
  workflow rather than a normal read-only truth route. If exposed at all, it
  belongs in a separate authenticated admin or offline job plane, not the
  current read-only public compute plane.

---

## 4. Admission Rule For Remaining Surface

Every remaining public engine family must be classified before route work
begins.

Each family must answer:

1. Is this a stable public computational surface?
2. Is it read-only during request flow?
3. Does it have a canonical public result vessel already?
4. Can transport preserve doctrinal distinctions honestly?
5. Is synchronous request/response operationally sane, or does it require
   async or batch treatment?

No family should be exposed by improvising route shapes first.

---

## 5. Remaining Engine Families

The remaining public engine families should be exposed in the order below.

## Phase 6: Event And Sky Phenomena Expansion

Current status:

- implemented:
  - `/v1/stations/*`
  - `/v1/void-of-course/*`
  - `/v1/rise-set/*`
  - `/v1/eclipses/*` summary, local-circumstance, and solar-path routes
  - `/v1/occultations/*` summary and path routes
  - `/v1/heliacal/*` event routes
  - `/v1/parans/*` core search, site, field, contour, and structure routes

Modules:

- `moira.stations`
- `moira.void_of_course`
- `moira.rise_set`
- `moira.phenomena`
- `moira.eclipse`
- `moira.eclipse_contacts`
- `moira.occultations`
- `moira.heliacal`
- `moira.parans`

Proposed route groups:

- `/v1/stations/*`
- `/v1/void-of-course/*`
- `/v1/rise-set/*`
- `/v1/phenomena/*`
- `/v1/eclipses/*`
- `/v1/occultations/*`
- `/v1/heliacal/*`
- `/v1/parans/*`

Required transport discipline:

- preserve event classification and computation truth
- preserve observer-specific vs global-event distinctions
- separate path products from event-summary products
- do not collapse lunar, solar, planetary, stellar, and local-circumstance
  products into one vague "event" schema

Subsequence:

1. stations
2. void of course
3. rise/set and generic phenomena
4. eclipse event summaries
5. eclipse contacts and local circumstances
6. occultation event summaries
7. heliacal event search
8. parans core search
9. parans field-analysis products

Special handling:

- `parans` field sampling, contour extraction, and structure analysis should be
  treated as heavy surfaces and may require async or explicit sampling bounds
- occultation and eclipse path geometry should have separate route families
  from event-summary endpoints

## Phase 7: Relationship And Inter-Chart Computation

Current status:

- implemented:
  - `/v1/synastry/aspects`
  - `/v1/synastry/contacts`
  - `/v1/synastry/overlays`
  - `/v1/synastry/chart-condition`
  - `/v1/synastry/network`
  - `/v1/composite/chart`
  - `/v1/davison/chart`
  - `/v1/chart-shape/classify`
  - `/v1/patterns/find`
  - `/v1/patterns/chart-profile`
  - `/v1/patterns/network`
  - `/v1/midpoints/calculate`
  - `/v1/midpoints/to-point`
  - `/v1/midpoints/pictures`
  - `/v1/midpoints/weighting`
  - `/v1/midpoints/clusters`

Modules:

- `moira.synastry`
- `moira.aspects`
- `moira.midpoints`
- `moira.chart_shape`
- `moira.patterns`

Proposed route groups:

- `/v1/synastry/*`
- `/v1/composite/*`
- `/v1/davison/*`
- `/v1/midpoints/*`
- `/v1/chart-shape/*`
- `/v1/patterns/*`

Required transport discipline:

- preserve cross-chart condition, relation, and network truth where already
  public
- distinguish composite from Davison explicitly
- avoid flattening synastry contacts into ordinary single-chart aspects

Subsequence:

1. synastry aspects and contacts
2. house overlays
3. composite charts
4. Davison charts
5. condition and network profiles
6. chart shape and patterns
7. midpoints

## Phase 8: Progressions, Directions, And Time-Lord Surfaces

Modules:

- `moira.progressions`
- `moira.profections`
- `moira.timelords`
- `moira.dasha`
- `moira.varshaphal`
- `moira.primary_directions`

Proposed route groups:

- `/v1/progressions/*`
- `/v1/profections/*`
- `/v1/timelords/*`
- `/v1/dasha/*`
- `/v1/varshaphal/*`
- `/v1/primary-directions/*`

Required transport discipline:

- distinguish progressed chart products from directed-arc products
- preserve doctrine, computation truth, relation, and condition-profile fields
- do not collapse converse and direct techniques into hidden flags
- treat large direction searches as bounded or async where necessary

Subsequence:

1. first-class progression routes
2. profections and simple timelord surfaces
3. Vimshottari dasha routes
4. Varshaphal annual chart and verdict routes
5. primary-direction speculum and arc-search routes

Special handling:

- `primary_directions.find_primary_arcs` may require explicit caps or async job
  treatment depending on target-set width
- `varshaphal` should be exposed as a doctrine-preserving family, not a single
  flattened annual verdict endpoint

## Phase 9: Vedic And Classical Doctrine Surfaces

Modules:

- `moira.panchanga`
- `moira.shadbala`
- `moira.varga`
- `moira.ashtakavarga`
- `moira.jaimini`
- `moira.vedic_dignities`
- `moira.dasha_systems`
- `moira.classical`
- `moira.lots`
- `moira.triplicity`
- `moira.decanates`
- `moira.egyptian_bounds`

Proposed route groups:

- `/v1/panchanga/*`
- `/v1/shadbala/*`
- `/v1/varga/*`
- `/v1/ashtakavarga/*`
- `/v1/jaimini/*`
- `/v1/vedic/*`
- `/v1/classical/*`

Required transport discipline:

- keep doctrinal families explicit
- do not merge Vedic and classical outputs into one generic "astrology"
  endpoint
- preserve policy-bearing truth such as ayanamsa, year basis, or doctrine mode

Subsequence:

1. panchanga
2. shadbala and vedic dignities
3. varga and ashtakavarga
4. Vimshottari-adjacent and other dasha system surfaces
5. Jaimini
6. classical lots and dignity-adjacent products

## Phase 10: Spatial And Earth-Facing Mapping Surfaces

Modules:

- `moira.astrocartography`
- `moira.local_space`
- `moira.geodetic`
- `moira.galactic`
- `moira.galactic_houses`
- `moira.gauquelin`

Proposed route groups:

- `/v1/astrocartography/*`
- `/v1/local-space/*`
- `/v1/geodetic/*`
- `/v1/galactic/*`
- `/v1/gauquelin/*`

Required transport discipline:

- distinguish sampled curves, line families, and summary objects
- preserve frame semantics
- treat dense map products as heavy outputs

Subsequence:

1. astrocartography line products
2. local-space and geodetic products
3. galactic position and galactic-house products
4. Gauquelin sectors

## Phase 11: Catalog, Stars, And Small-Body Surfaces

Modules:

- `moira.stars`
- `moira.multiple_stars`
- `moira.variable_stars`
- `moira.asteroids`
- `moira.comets`
- `moira.asteroid_families`
- `moira.manazil`
- `moira.planetary_nodes`
- `moira.classical_asteroids`

Proposed route groups:

- `/v1/stars/*`
- `/v1/asteroids/*`
- `/v1/comets/*`
- `/v1/catalogs/*`

Required transport discipline:

- preserve object identity and provenance
- separate one-object lookup from catalog search
- add paging or bounded filters for catalog-wide calls

Subsequence:

1. single-object lookup surfaces
2. bounded multi-object range surfaces
3. catalog search and listing surfaces
4. family/group views

## Phase 12: Specialist Analytical Surfaces

Modules:

- `moira.uranian`
- `moira.harmonics`
- `moira.phase`
- `moira.antiscia`
- `moira.nine_parts`
- `moira.planetary_hours`
- `moira.huber`
- `moira.sothic`
- `moira.longevity`
- `moira.lord_of_the_turn`
- `moira.lord_of_the_orb`

Proposed route groups:

- `/v1/uranian/*`
- `/v1/harmonics/*`
- `/v1/phase/*`
- `/v1/antiscia/*`
- `/v1/special/*`

Required transport discipline:

- keep niche doctrine families separate
- do not hide specialist outputs inside generic chart payloads

This is the lowest-priority direct public-compute band.

## Phase 13: Electional And Search Workflow Surfaces

Modules:

- `moira.electional`

Proposed route groups:

- `/v1/electional/windows`
- `/v1/electional/moments`
- `/v1/electional/scored`

Required transport discipline:

- preserve search policy explicitly
- cap windows and scan cadence
- treat large scans as heavy surfaces

This phase comes late because electional search is operationally heavy even
though the module itself is public and stable.

---

## 6. Excluded Or Deferred Families

These are not part of the normal public compute expansion target:

- `moira.download_kernels`
- `moira.kernel_manager_ui`
- `moira.daf_writer_ui`
- `moira._export_governance.*`
- `moira._facade_*`
- `moira.moira_native`

Deferred to separate operational planes if ever needed:

- `moira.daf_writer`

Reason:

- these are admin, UI, internal, or artifact-authoring concerns
- exposing them naively would violate the read-only compute boundary

---

## 7. Required Server Package Growth

The current `moira_server` package must grow by route family, not by ad hoc
single files.

For each new family, add:

- `moira_server/models/<family>.py`
- `moira_server/serializers/<family>.py`
- `moira_server/services/<family>.py`
- `moira_server/routers/<family>.py`
- `tests/server/test_server_<family>_routes.py`
- `tests/server/test_server_<family>_adversarial.py` when the family is
  non-trivial

Heavy families may also require:

- async job models
- polling routes
- explicit job-result serializers

---

## 8. Verification Rule For Each New Family

No family is admitted until all of the following are true:

1. route parity exists against direct engine output for representative cases
2. doctrinal distinctions remain visible in transport
3. adversarial route tests exist
4. batch or async behavior is explicit where heavy computation requires it
5. request flow remains read-only with respect to kernel lifecycle

Heavy-family additions must also prove:

6. bounded request sizes or scan windows
7. honest timeout or job-state behavior

---

## 9. Recommended Expansion Sequence

The remaining expansion should proceed in this exact order:

1. phase 6 event and sky phenomena
2. phase 7 relationship and inter-chart computation
3. phase 8 progressions, directions, and time-lord surfaces
4. phase 9 Vedic and classical doctrine surfaces
5. phase 10 spatial and Earth-facing mapping
6. phase 11 catalog, stars, and small-body surfaces
7. phase 12 specialist analytical surfaces
8. phase 13 electional and search workflow surfaces

Reason:

- event and relationship families are the highest-value missing public compute
  surfaces
- progression, direction, and annual doctrine are already structurally mature
  in the engine and should follow next
- electional should come late because it is scan-heavy and operationally easy
  to misuse

---

## 10. Definition Of Done

The engine is "fully exposed through REST" only when all of the following are
true:

- every transport-admissible stable public compute family has a route surface
- excluded families are documented honestly rather than forgotten
- heavy families have explicit async or bounded transport treatment
- canonical engine semantics survive serialization
- server tests cover both nominal and adversarial behavior for every admitted
  family
- no request path violates `docs/threading.md` or
  `docs/architecture/MOIRA_SERVER_BOUNDARY.md`

That is the closure standard for full-engine REST exposure.
