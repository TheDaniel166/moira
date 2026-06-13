# Moira Server Phase 11 Evaluation Ledger

Version: 1.0
Date: 2026-06-13
Status: P11-01 through P11-08 admitted; P11-U1 deferred by doctrine decision
Scope: Catalog, fixed-star, variable-star, multiple-star, and small-body REST
candidate evaluation

Phase 11 covers catalog-bearing celestial identity surfaces. These families
are not ordinary chart calculation helpers. They expose named objects,
catalog records, orbital or stellar provenance, and bounded catalog search.
REST admission must preserve identity truth, catalog/source provenance,
position-frame semantics, and result-size boundaries.

This ledger records the current Phase 11 truth after the website-accelerated
subset was admitted before a formal phase ledger existed. It should govern all
remaining Phase 11 expansion.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`
- `wiki/02_services/REST_API_REFERENCE.md`
- `wiki/02_standards/STARS_BACKEND_STANDARD.md`
- `wiki/02_standards/VARIABLE_STARS_BACKEND_STANDARD.md`
- `wiki/02_standards/ASTEROID_FAMILIES_BACKEND_STANDARD.md`
- `wiki/02_standards/MANAZIL_BACKEND_STANDARD.md`
- `wiki/02_standards/PLANETARY_NODES_BACKEND_STANDARD.md`
- `docs/architecture/P11-U1_CATALOG_UMBRELLA_DOCTRINE_DECISION.md`
- `docs/architecture/MOIRA_SOVEREIGN_SMALL_BODY_KERNEL_PLAN.md`

---

## 1. Phase 11 Boundary

Candidate modules:

- `moira.stars`
- `moira.variable_stars`
- `moira.multiple_stars`
- `moira.asteroids`
- `moira.comets`
- `moira.asteroid_families`
- `moira.classical_asteroids`
- `moira.main_belt`
- `moira.centaurs`
- `moira.tno`
- `moira.manazil`
- `moira.planetary_nodes`

Candidate route families:

- `/v1/stars/*`
- `/v1/asteroids/*`
- `/v1/comets/*`
- `/v1/nodes/*`
- `/v1/catalogs/*`
- later named family routes only after transport design

Phase 11 must distinguish:

- object identity from computed position
- catalog lookup from catalog-wide sweep
- fixed-star position from variable-star photometric state
- multiple-star catalog record from resolvability state
- asteroid, comet, centaur, TNO, and asteroid-family semantics
- loaded-kernel availability from known catalog identity
- website convenience surfaces from complete REST admission

---

## 2. Evaluation Status Vocabulary

Each family receives one of the route-admission checklist statuses:

- `admitted` - REST family is implemented, registered, tested, and documented
- `admitted_website_subset` - bounded routes are live for website support, but
  the family still needs phase-level hardening before it can be called complete
- `admit_after_minor_transport_hardening` - existing engine truth is suitable,
  but request/response/provenance/bounds should be hardened before expansion
- `admit_after_backend_standard` - engine surface appears suitable, but a
  backend standard or admission packet must exist before transport expansion
- `defer_for_engine_completion` - transport work would expose incomplete
  computation or provenance
- `defer_for_doctrine` - doctrine is not stable enough for public transport
- `exclude_from_rest` - family does not belong on the ordinary REST compute
  surface

Website readiness is tracked separately from phase admission:

- `website_good` - current routes are acceptable for the website use case and
  have focused route tests covering the principal behavior.
- `website_good_needs_minor_hardening` - current routes are acceptable for the
  website use case, but a narrow validation, provenance, or bounds cleanup
  should happen before the family is called phase-complete.
- `website_partial` - some useful website routes are live, but part of the
  live route family is not yet sufficiently verified or semantically hardened.
- `not_website_ready` - the family should not be used by the website yet.

---

## 3. Current Evaluation Summary

| Unit | Engine family | Phase status | Website verdict | Reason |
|---|---|---|---|---|
| P11-01 | Fixed stars | `admitted` | `website_good` | Single position, bulk position, and bounded list/search are live, route-tested, provenance-bearing, and reject naive datetimes, empty star names, empty bulk lists, empty bulk entries, and oversized bulk lists. Heliacal events, condition networks, rendered maps, catalog-wide sweeps, and fixed-star ACG remain deferred expansion. |
| P11-02 | Variable stars | `admitted` | `website_good` | Catalog list, catalog record, state, range, catalog-profile, and pair routes are live, route-tested, provenance-bearing, and bounded for datetime, star-name, eclipse-threshold, and JD-range inputs. Real-time observations, exhaustive GCVS exposure, rendered curves, and positional overlays remain deferred expansion. |
| P11-03 | Multiple stars | `admitted` | `website_good` | List, catalog record, and selected-system state/resolvability routes are live, route-tested, provenance-bearing, and bounded for datetime, system-name, aperture, and list-limit inputs. Catalog-wide sweeps, rendered orbit diagrams, observing plans, and exhaustive WDS/INT4 exposure remain deferred expansion. |
| P11-04 | Asteroids | `admitted` | `website_good` | Position, bulk, and loaded-kernel list/search routes are live, route-tested, provenance-bearing, and bounded for timezone-aware datetime, non-empty body identity, bulk size, and list-limit inputs. Known catalog identity is explicitly distinguished from loaded-kernel availability. Asteroid families, subset routes, photometry, rendered maps, topocentric positions, ACG, and full small-body migration proof remain deferred. |
| P11-05 | Comets | `admitted` | `website_good` | Position, bulk, and loaded-kernel list/search routes are live, route-tested, provenance-bearing, and bounded for timezone-aware datetime, non-empty body identity, bulk size, and list-limit inputs. Known comet identity is explicitly distinguished from loaded-kernel availability, and REST NAIF IDs resolve to engine comet names before computation. Non-periodic comet expansion, photometry, rendered maps, topocentric positions, ACG, and full small-body migration proof remain deferred. |
| P11-06 | Asteroid families and asteroid subsets | `admitted` | `website_good` | Subset registry/list/position routes and Nesvorny family lookup/member/chart-group routes are live, route-tested, provenance-bearing, and bounded. Subset routes preserve name/NAIF identity and loaded-kernel truth; family routes preserve MPC-number and Nesvorny/PDS catalog semantics. Resonance/aspect-network transport, family-wide position sweeps, rendered maps, photometry, topocentric products, and family ACG remain deferred. |
| P11-07 | Manazil / lunar mansions | `admitted` | `website_good` | Direct catalog, position, bulk, and tradition lookup routes are live, route-tested, provenance-bearing, and bounded. Tropical vs sidereal mode is explicit, sidereal mode requires `jd_ut`, and textual traditions change attribution only, not the 28 equal mansion boundaries. Chart-backed Moon mansion routes, natal mansion profiles, electional scoring, condition networks, Vedic nakshatra transport, and alternate boundary systems remain deferred. |
| P11-08 | Planetary and small-body nodes | `admitted` | `website_good` | Mean planetary node catalog/single/bulk routes and a single-body geometric osculating node route are live, route-tested, provenance-bearing, and bounded. Mean-element and reader-backed geometric methods remain visibly distinct. Lunar nodes, chart-backed node profiles, nodal aspect networks, catalog-wide small-body node sweeps, rendered maps, and kernel manifest management remain deferred. |
| P11-U1 | Catalog umbrella / `/v1/catalogs/*` | `defer_for_doctrine` | `not_website_ready` | Doctrine decision complete: a future umbrella may only be discovery-only registry metadata. Cross-family search, member lookup, computation, position requests, kernel coverage lists, and catalog sweeps remain excluded because they flatten distinct provenance and availability rules. |

---

## 4. Already-Live Website-Accelerated Surface

The following routes are registered in the live server and documented in
`wiki/02_services/REST_API_REFERENCE.md`.

### Fixed-star routes

- `POST /v1/stars/position`
- `POST /v1/stars/bulk`
- `GET /v1/stars/list`

Current transport stance:

- synchronous
- compact website response shape
- selected-object and bounded list/search only

Known hardening needs:

- expose or document catalog/provenance truth more explicitly
- clarify TT conversion and apparent/observed star-position policy in REST
- distinguish response compactness from full backend standard completeness
- adversarial tests for invalid list limits

### Variable-star routes

- `GET /v1/stars/variable/list`
- `GET /v1/stars/variable/{name}`
- `POST /v1/stars/variable/state`
- `POST /v1/stars/variable/range`
- `POST /v1/stars/variable/catalog-profile`
- `POST /v1/stars/variable/pair`

Current transport stance:

- synchronous
- catalog/state/profile views over the admitted variable-star backend
- provenance-bearing admitted response shapes

Known hardening needs:

- real-time observation refresh remains out of scope
- exhaustive GCVS/VSX catalog exposure remains out of scope
- rendered light curves and positional overlays remain out of scope

### Multiple-star routes

- `GET /v1/stars/multiple/list`
- `GET /v1/stars/multiple/{name}`
- `POST /v1/stars/multiple/state`

Current transport stance:

- synchronous
- selected-system catalog record and selected-system resolvability state
- provenance-bearing admitted response shapes

Known hardening needs:

- catalog-wide state sweeps remain out of scope
- rendered orbit diagrams remain out of scope
- exhaustive WDS/INT4 exposure remains out of scope

### Asteroid routes

- `POST /v1/asteroids/position`
- `POST /v1/asteroids/bulk`
- `GET /v1/asteroids/list`

Current transport stance:

- synchronous
- selected asteroid positions and loaded-kernel list/search
- native Type 13 reader used when loaded through the server engine
- provenance-bearing admitted response shapes

Known hardening needs:

- asteroid families and named subset routes remain out of scope
- photometry, topocentric positions, rendered maps, asteroid ACG, and
  catalog-wide sweeps remain out of scope
- full small-body migration proof remains governed by
  `docs/architecture/MOIRA_SOVEREIGN_SMALL_BODY_KERNEL_PLAN.md`

### Comet routes

- `POST /v1/comets/position`
- `POST /v1/comets/bulk`
- `GET /v1/comets/list`

Current transport stance:

- synchronous
- selected comet positions and loaded-kernel list/search
- native small-body reader used when loaded through the server engine
- provenance-bearing admitted response shapes

Known hardening needs:

- non-periodic comet expansion remains out of scope
- photometry, topocentric positions, rendered maps, comet ACG, and
  catalog-wide sweeps remain out of scope
- full small-body migration proof remains governed by
  `docs/architecture/MOIRA_SOVEREIGN_SMALL_BODY_KERNEL_PLAN.md`

### Node routes

- `GET /v1/nodes/catalog`
- `POST /v1/nodes/planetary/mean`
- `POST /v1/nodes/planetary/mean/bulk`
- `POST /v1/nodes/geometric`

Current transport stance:

- synchronous
- mean planetary node single/bulk routes are kernel-free
- geometric node route is reader-backed and single-body only
- provenance-bearing admitted response shapes

Known hardening needs:

- lunar true/mean node routes remain out of scope
- chart-backed node profiles remain out of scope
- catalog-wide small-body node sweeps remain out of scope
- rendered node maps and nodal aspect networks remain out of scope

---

## 5. P11-01 Fixed Stars

Status: `admitted`

Governing object:

- Fixed-star catalog identity and position at a requested epoch.

Evidence:

- Engine modules: `moira/stars.py`, `moira/star_types.py`
- Backend standard: `wiki/02_standards/STARS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P11-01_FIXED_STARS_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/stars.py`,
  `moira_server/services/stars.py`, `moira_server/serializers/stars.py`,
  `moira_server/routers/stars.py`
- Route tests: `tests/server/test_server_stars_routes.py`
- Live routes:
  - `POST /v1/stars/position`
  - `POST /v1/stars/bulk`
  - `GET /v1/stars/list`

Readiness:

- Single and bulk fixed-star position surfaces are live.
- The public response is bounded, typed, and provenance-bearing.
- Website verdict: `website_good`.
- Fixed-star position and bulk request hardening is complete for the current
  website subset: naive datetimes, empty star names, empty bulk lists, empty
  bulk entries, and oversized bulk lists are rejected.
- P11-01 admission is narrow: it admits position, bulk, and list/search routes
  only.

Recommended next stance:

- keep current routes
- treat heliacal events, condition networks, rendered maps, catalog-wide sweeps,
  and fixed-star ACG as separate expansion designs
- do not add catalog-wide heavy products or ACG star derivation here; those
  belong to explicit expansion designs

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\stars.py moira_server\services\stars.py moira_server\serializers\stars.py tests\server\test_server_stars_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_stars_routes.py -q`
- Route registry audit after admission: 269 non-documentation routes, 265
  versioned `/v1` routes, 12 `/v1/stars/*` routes, and exactly 3 admitted
  fixed-star routes.

---

## 6. P11-02 Variable Stars

Status: `admitted`

Governing object:

- Variable-star catalog records, phase/magnitude state, extrema ranges, catalog
  profile, and pair relation.

Evidence:

- Engine module: `moira/variable_stars.py`
- Backend standard: `wiki/02_standards/VARIABLE_STARS_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P11-02_VARIABLE_STARS_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/stars.py`,
  `moira_server/services/stars.py`, `moira_server/serializers/stars.py`,
  `moira_server/routers/stars.py`
- Route tests: `tests/server/test_server_stars_routes.py`
- Live routes:
  - `GET /v1/stars/variable/list`
  - `GET /v1/stars/variable/{name}`
  - `POST /v1/stars/variable/state`
  - `POST /v1/stars/variable/range`
  - `POST /v1/stars/variable/catalog-profile`
  - `POST /v1/stars/variable/pair`

Readiness:

- The route surface is admitted as a bounded synchronous variable-star
  catalog/state/profile family.
- Website verdict: `website_good`.
- Catalog, state, range, catalog-profile, and pair responses preserve explicit
  catalog/computation provenance.
- Datetime-backed routes reject naive datetimes.
- State/profile/pair routes bound `eclipse_threshold`.
- Range routes require finite JDs, ordered windows, and a maximum span of 366
  days.

Recommended next stance:

- keep current routes
- treat real-time observation refresh, exhaustive GCVS exposure, rendered light
  curves, positional overlays, and secondary-eclipse products as separate
  expansion designs
- avoid claiming real-time observational updates; the engine uses curated
  catalog ephemerides and light-curve models

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\stars.py moira_server\services\stars.py moira_server\serializers\stars.py tests\server\test_server_stars_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_stars_routes.py -q`
- Route registry audit after admission: 269 non-documentation routes, 265
  versioned `/v1` routes, 12 `/v1/stars/*` routes, and exactly 6 admitted
  variable-star routes.

---

## 7. P11-03 Multiple Stars

Status: `admitted`

Governing object:

- Multiple-star catalog record and selected-system resolvability state.

Evidence:

- Engine module: `moira/multiple_stars.py`
- Transport design: `docs/architecture/P11-03_MULTIPLE_STARS_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/stars.py`,
  `moira_server/services/stars.py`, `moira_server/serializers/stars.py`,
  `moira_server/routers/stars.py`
- Route tests: `tests/server/test_server_stars_routes.py`
- Live routes:
  - `GET /v1/stars/multiple/list`
  - `GET /v1/stars/multiple/{name}`
  - `POST /v1/stars/multiple/state`

Readiness:

- The route surface is admitted as a bounded synchronous multiple-star
  catalog/state family.
- Website verdict: `website_good`.
- Catalog, list, and state responses preserve explicit catalog/orbital/aperture
  provenance.
- State routes reject naive datetimes, empty system names, non-positive
  apertures, non-finite apertures, and apertures above 10000 mm.
- List routes require `1 <= limit <= 500`.

Recommended next stance:

- keep synchronous selected-system routes
- treat catalog-wide state sweeps, rendered orbit diagrams, multi-aperture
  observing plans, custom seeing policies, and exhaustive WDS/INT4 exposure as
  separate expansion designs

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\stars.py moira_server\services\stars.py moira_server\serializers\stars.py moira_server\routers\stars.py tests\server\test_server_stars_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_stars_routes.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_multiple_stars.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\integration\test_multiple_stars_external_reference.py -q`
- Route registry audit after admission: 269 non-documentation routes, 265
  versioned `/v1` routes, 12 `/v1/stars/*` routes, and exactly 3 admitted
  multiple-star routes.

---

## 8. P11-04 Asteroids

Status: `admitted`

Governing object:

- Selected asteroid geocentric apparent ecliptic position and loaded-kernel
  catalog search.

Evidence:

- Engine module: `moira/asteroids.py`
- Small-body kernel doctrine: `docs/architecture/MOIRA_SOVEREIGN_SMALL_BODY_KERNEL_PLAN.md`
- Transport design: `docs/architecture/P11-04_ASTEROIDS_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/asteroids.py`,
  `moira_server/services/asteroids.py`, `moira_server/serializers/asteroids.py`,
  `moira_server/routers/asteroids.py`
- Route tests: `tests/server/test_server_small_body_list_routes.py`
- Live routes:
  - `POST /v1/asteroids/position`
  - `POST /v1/asteroids/bulk`
  - `GET /v1/asteroids/list`

Readiness:

- The route surface is admitted as a bounded synchronous asteroid position,
  bulk, and loaded-reader list/search family.
- Website verdict: `website_good`.
- Position, bulk, and list responses preserve explicit transport provenance.
- Position and bulk routes reject naive datetimes and empty body names.
- Bulk routes require 1 to 500 body identifiers.
- List routes require `1 <= limit <= 500`.
- Known catalog identity is not treated as loaded-kernel availability.
- `is_sovereign=true` only when the returned NAIF ID is covered by the loaded
  reader.

Recommended next stance:

- keep current synchronous selected-asteroid routes
- preserve known-catalog vs loaded-kernel distinction
- keep family/group routes governed by the separate P11-06 admission boundary
- treat photometry, rendered maps, topocentric/equatorial asteroid products,
  asteroid ACG, and full small-body migration proof as separate expansion work

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\asteroids.py moira_server\services\asteroids.py moira_server\serializers\asteroids.py moira_server\routers\asteroids.py tests\server\test_server_small_body_list_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_small_body_list_routes.py -q`
- Route registry audit after admission: exactly 3 admitted asteroid routes.

---

## 9. P11-05 Comets

Status: `admitted`

Governing object:

- Selected comet geocentric apparent ecliptic position and loaded-kernel
  catalog search.

Evidence:

- Engine module: `moira/comets.py`
- Small-body kernel doctrine: `docs/architecture/MOIRA_SOVEREIGN_SMALL_BODY_KERNEL_PLAN.md`
- Transport design: `docs/architecture/P11-05_COMETS_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/comets.py`,
  `moira_server/services/comets.py`, `moira_server/serializers/comets.py`,
  `moira_server/routers/comets.py`
- Route tests: `tests/server/test_server_small_body_list_routes.py`
- Live routes:
  - `POST /v1/comets/position`
  - `POST /v1/comets/bulk`
  - `GET /v1/comets/list`

Readiness:

- The route surface is admitted as a bounded synchronous comet position, bulk,
  and loaded-reader list/search family.
- Website verdict: `website_good`.
- Position, bulk, and list responses preserve explicit transport provenance.
- Position and bulk routes reject naive datetimes and empty body names.
- Bulk routes require 1 to 500 body identifiers.
- List routes require `1 <= limit <= 500`.
- REST NAIF IDs resolve to engine comet names before calling `comet_at(...)`.
- Known comet identity is not treated as loaded-kernel availability.
- `is_sovereign=true` only when the returned NAIF ID is covered by the loaded
  reader.

Recommended next stance:

- keep current synchronous selected-comet routes
- preserve JPL/Horizons NAIF ID convention in docs
- avoid comet topocentric or ACG line expansion until its coordinate path is
  separately admitted
- treat photometry, rendered maps, non-periodic expansion, and full small-body
  migration proof as separate expansion work

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\comets.py moira_server\services\comets.py moira_server\serializers\comets.py moira_server\routers\comets.py tests\server\test_server_small_body_list_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_small_body_list_routes.py -q`
- Route registry audit after admission: exactly 3 admitted comet routes.

---

## 10. P11-06 Asteroid Families And Subsets

Status: `admitted`

Candidate modules:

- `moira.asteroid_families`
- `moira.classical_asteroids`
- `moira.main_belt`
- `moira.centaurs`
- `moira.tno`

Governing object:

- Catalog subset identity, family/group membership, and selected-body position
  views over already-admitted asteroid computation.

Readiness:

- The route surface is admitted as bounded subset convenience and family
  membership transport.
- Website verdict: `website_good`.
- Backend standard: `wiki/02_standards/ASTEROID_FAMILIES_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P11-06_ASTEROID_FAMILIES_SUBSETS_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/asteroids.py`,
  `moira_server/services/asteroids.py`, `moira_server/routers/asteroids.py`
- Route tests: `tests/server/test_server_small_body_list_routes.py`
- Live routes:
  - `GET /v1/asteroids/subsets`
  - `GET /v1/asteroids/subsets/{subset}/list`
  - `POST /v1/asteroids/subsets/{subset}/positions`
  - `GET /v1/asteroids/families/by-number/{number}`
  - `GET /v1/asteroids/families/{family_name}/members`
  - `POST /v1/asteroids/families/chart`
- Subset routes preserve subset source module, catalog source, asteroid name,
  NAIF ID, and loaded-kernel availability truth.
- Subset position routes delegate to the admitted P11-04 asteroid position
  transport.
- Family routes preserve MPC catalog-number semantics and Nesvorny/PDS
  provenance.
- Family chart grouping preserves live catalog distinctions such as `Koronis`,
  `Koronis(2)`, and `Karin`.

Recommended first stance:

- keep the admitted subset and family catalog routes
- treat resonance/aspect-network transport as a separate design
- do not add family-wide position sweeps without async/job or stricter bounds
- keep family routes MPC-number based; do not silently conflate MPC numbers
  with NAIF IDs

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\asteroids.py moira_server\services\asteroids.py moira_server\routers\asteroids.py tests\server\test_server_small_body_list_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_small_body_list_routes.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asteroid_api.py -q`
- Route registry audit after admission: exactly 9 admitted asteroid routes.

---

## 11. P11-07 Manazil / Lunar Mansions

Status: `admitted`

Candidate module:

- `moira.manazil`

Governing object:

- Direct Arabic lunar mansion catalog, position, bulk, and tradition lookup
  surface.

Readiness:

- The route surface is admitted as bounded direct Manazil transport.
- Website verdict: `website_good`.
- Backend standard: `wiki/02_standards/MANAZIL_BACKEND_STANDARD.md`
- Transport design: `docs/architecture/P11-07_MANAZIL_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/manazil.py`,
  `moira_server/services/manazil.py`, `moira_server/routers/manazil.py`
- Route tests: `tests/server/test_server_manazil_routes.py`
- Engine tests: `tests/unit/test_manazil.py`
- Live routes:
  - `GET /v1/manazil/catalog`
  - `POST /v1/manazil/position`
  - `POST /v1/manazil/bulk`
  - `GET /v1/manazil/traditions/{tradition}/mansions/{mansion_index}`
- Tropical vs sidereal computation mode is explicit.
- Sidereal mode requires `jd_ut`.
- Textual tradition changes attribution only; mansion boundaries remain the
  admitted 28 equal stations.

Recommended first stance:

- keep the admitted direct longitude routes
- defer chart-backed Moon mansion routes until chart derivation and mansion
  profile semantics are separately designed
- do not collapse Arabic Manazil into Vedic nakshatra transport

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\manazil.py moira_server\services\manazil.py moira_server\routers\manazil.py tests\server\test_server_manazil_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_manazil_routes.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_manazil.py -q`
- Route registry audit after admission: exactly 4 admitted Manazil routes.

---

## 12. P11-08 Planetary And Small-Body Nodes

Status: `admitted`

Candidate module:

- `moira.planetary_nodes`

Governing object:

- Orbital node and apsides records for mean planetary elements and selected
  reader-backed osculating bodies.

Readiness:

- The route surface is admitted as bounded node transport.
- Website verdict: `website_good`.
- Backend standard: `wiki/02_standards/PLANETARY_NODES_BACKEND_STANDARD.md`
- Transport design:
  `docs/architecture/P11-08_PLANETARY_NODES_TRANSPORT_DESIGN.md`
- Live transport files: `moira_server/models/nodes.py`,
  `moira_server/services/nodes.py`, `moira_server/routers/nodes.py`
- Route tests: `tests/server/test_server_nodes_routes.py`
- Live routes:
  - `GET /v1/nodes/catalog`
  - `POST /v1/nodes/planetary/mean`
  - `POST /v1/nodes/planetary/mean/bulk`
  - `POST /v1/nodes/geometric`
- Mean planetary routes preserve the kernel-free Meeus / Simon mean-element
  basis and the engine's approximate 2000 BCE to 3000 CE validity note.
- Geometric routes preserve reader-backed osculating state-vector provenance.
- Sun and Moon are rejected as geometric heliocentric-node targets.
- Lunar true/mean nodes are intentionally outside this admission.

Recommended first stance:

- keep mean-element and geometric node methods separate
- avoid catalog-wide small-body node sweeps without a separate async/bounds
  design
- do not merge this route family into asteroid/comet position transport
- do not expose lunar-node or chart-backed node profiles here

Admission verification:

- `.\.venv\Scripts\python.exe -m py_compile moira_server\models\nodes.py moira_server\services\nodes.py moira_server\routers\nodes.py moira_server\app.py moira_server\routers\__init__.py tests\server\test_server_nodes_routes.py`
- `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_nodes_routes.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_chart_metadata_truth.py::test_moira_planetary_node_delegates_to_singular_wrapper tests\unit\test_api_surface_adversarial_audit.py -q`
- Route registry audit after admission: exactly 4 admitted node routes.

---

## 13. P11-U1 Catalog Umbrella

Status: `defer_for_doctrine`

Candidate route family:

- `/v1/catalogs/*`

Reason:

- A generic catalog umbrella could collapse fixed-star, variable-star,
  multiple-star, asteroid, comet, mansion, and node provenance into one vague
  access pattern.
- The admitted Phase 11 families now prove that catalog-bearing surfaces have
  different identity, availability, and provenance laws.
- Doctrine decision:
  `docs/architecture/P11-U1_CATALOG_UMBRELLA_DOCTRINE_DECISION.md`

Recommended stance:

- no generic catalog routes yet
- use named family route surfaces
- if later admitted, make `/v1/catalogs/*` discovery-only registry metadata
- do not admit cross-family search, object member lookup, computed positions,
  bulk computation, kernel coverage lists, cross-reference joins, or catalog
  sweeps under the umbrella
- keep family-native catalog routes authoritative for object records and
  computation

Admissible future route shape:

- `GET /v1/catalogs`
- `GET /v1/catalogs/{family}`

Rejected route shapes:

- `GET /v1/catalogs/search`
- `GET /v1/catalogs/{family}/items`
- `GET /v1/catalogs/{family}/items/{id}`
- `POST /v1/catalogs/positions`
- `POST /v1/catalogs/bulk`
- `POST /v1/catalogs/cross-reference`
- `POST /v1/catalogs/sweep`

---

## 14. Recommended Evaluation Order

Recommended Phase 11 sequence:

1. P11-01 Fixed Stars.
2. P11-02 Variable Stars.
3. P11-03 Multiple Stars.
4. P11-04 Asteroids.
5. P11-05 Comets.
6. P11-06 Asteroid Families And Subsets.
7. P11-07 Manazil / Lunar Mansions.
8. P11-08 Planetary And Small-Body Nodes.
9. P11-U1 Catalog Umbrella.

Reason:

- The first five units already have live REST routes and should be hardened
  before new Phase 11 families are admitted.
- Stars should be audited before variable/multiple star convenience expansion
  because they share route family and catalog identity concerns.
- Asteroids and comets should be audited before subset/family/node expansion
  because they own small-body kernel and identity semantics.
- The catalog umbrella should wait until named families establish their own
  provenance rules.

---

## 15. Phase 11 Non-Goals

Phase 11 evaluation does not implicitly:

- add REST routes
- create new request or response models
- introduce async catalog jobs
- expose unbounded catalog-wide sweeps
- add rendered star maps or asteroid maps
- change astronomical engine computation
- change small-body kernel loading semantics
- collapse catalog provenance into generic labels

---

## 16. Immediate Next Step

P11-01 through P11-08 are admitted for their current bounded REST subsets.

P11-U1 is evaluated and remains deferred. Phase 11 is complete for current
admitted route work and umbrella doctrine.

The next task should be either:

- a final Phase 11 documentation truth sweep, or
- Phase 12 evaluation scoping.

Do not add `/v1/catalogs/*` routes unless a later discovery-only registry
design is explicitly requested and passes the P11-U1 doctrine gate.
