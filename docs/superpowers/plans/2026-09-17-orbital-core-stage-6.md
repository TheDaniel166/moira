# Orbital Core Stage 6 Implementation Plan & Checkpoint

> **Execution boundary:** Implement and validate Stage 6 on top of the
> Stage 1 through Stage 5 worktree.

**Date:** 2026-09-17

**Status:** Implementation complete and verified

**Governing spec:**
`docs/superpowers/specs/2026-09-15-orbital-core-design.md`, line 1093.

**Goal:** Execute Stage 6 (admission of small bodies to `moira_server` under `/v1/orbits/*`
and introduction of dedicated single and batch REST endpoints for JPL SBDB osculating
asteroid orbit classification).

---

## 1. Architectural Surface

1. **Broadened Small Body Admission**:
   - `_OrbitBaseRequest`: Body validation broadened from `ADMITTED_ORBIT_BODIES` (the 9 historical planets)
     to arbitrary non-empty trimmed strings. Strict types enforced (`jd_ut` rejects booleans and NaNs).
   - `POST /v1/orbits/elements`: Admits asteroids and comets alongside major planets.
   - `POST /v1/orbits/distance-extremes`: Admits asteroids and comets alongside major planets.
     Unavailable passages (e.g. open conics or events beyond interval) raise `OrbitalPassageUnavailableError`,
     mapped cleanly to HTTP 422 (`orbital_event_availability`).

2. **Nullable Open-Conic Elements Transport**:
   - `OrbitalElementsResponse`: To maintain strict backward compatibility with existing 12-element consumers,
     elliptic orbits retain their exact schema.
   - For parabolic and hyperbolic trajectories ($e \ge 1.0$), open-conic fields are nullable (`float | None = None`):
     - `semi_major_axis_au`
     - `aphelion_distance_au`
     - `orbital_period_days`
     - `mean_anomaly_deg`
     - `mean_motion_deg_per_day`
   - Parabolic/hyperbolic trajectories serialize these as `null`.

3. **New JPL SBDB Orbit Classification REST Endpoints**:
   - `POST /v1/orbits/class` (`orbit_class_route`):
     - Single body query taking `body` and `jd_ut`.
     - Returns assigned `OrbitClassCode` (`IEO`, `ATE`, `APO`, `AMO`, `MCA`, `IMB`, `MBA`, `OMB`, `TJN`, `AST`),
       display title, description, and diagnostic boundary margins (`q`, `Q`, `a`, `T_j`).
     - Provenance envelope including complete underlying osculating elements, time conversion, gravity, and SPK legs.
   - `POST /v1/orbits/class/batch` (`orbit_class_batch_route`):
     - Batch evaluation over up to 128 bodies at a single epoch.
     - Individual item error isolation: invalid or unresolvable targets return structured error objects
       without failing the entire request.
     - Strict path redaction on all error messages.
     - Echoes batch request metadata and returns list of successful results and item errors.

---

## 2. Verification Receipts

- `tests/server/test_server_orbits_routes.py`: 14 passed (100% route and model verification).
- `tests/server/test_server_route_discoverability.py`: 4 passed (OpenAPI tag groups and route catalog).
- `scripts/sync_rest_api_reference.py --check`: Passed with 460 registered paths and operations.
- `scripts/sync_git_wiki.py`: Synchronized 2 modified wiki documents.
- `scripts/build_website_docs_bundle.py`: Updated `website_docs/publication.json`.
