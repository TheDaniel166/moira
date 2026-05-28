# Moira Server Implementation Plan

Version: 1.5
Date: 2026-05-28
Status: Phases 1-7 complete; remaining expansion begins at phase 8
Scope: REST access surface over the existing Moira engine

This document defines the concrete implementation sequence for a future REST
server built on top of Moira.

Current implementation state:

- phases 1 through 5 are implemented
- phase 6 now exposes stations, void-of-course, rise/set, eclipse summaries,
  solar eclipse path geometry, eclipse local circumstances, occultation
  summaries, occultation path geometry, heliacal event search, paran core
  search, and paran site/field/contour/structure products
- phase 7 now exposes synastry aspects, contacts, overlays, condition and
  network profiles, composite charts, Davison charts, chart-shape
  classification, pattern detection and pattern profiles, and midpoint
  calculation, targeting, pictures, weighting, and clustering
- phase 8 has now begun with profection routes and the first shared
  transport-helper extraction for chart-backed route families
- the server now exposes the operational, chart, position, transit, return,
  batch, visibility, full phase-6 phenomena, and full phase-7 relationship
  surfaces defined in this document
- adversarial transport tests exist for the currently admitted route families

What this document now governs:

- the implemented base architecture and admission rules
- the first completed rollout wave
- the sequencing logic future route families must still obey

It assumes and inherits:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/threading.md`
- `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_SHARED_PRIMITIVES.md`
- `docs/architecture/MOIRA_SERVER_PHASE8_LEDGER.md`

The purpose of this plan is to make the service layer buildable without
guessing:

- what package structure to use
- what endpoints ship first
- how startup and kernel lifecycle must work
- how schemas relate to canonical engine result types
- what verification is required before each phase is considered complete

---

## 1. Core Implementation Rule

The REST layer is an access shell over Moira's existing audited engine.

It must:

- call stable engine surfaces
- serialize engine truth honestly
- remain read-only during request handling

It must not:

- create a second doctrine layer
- move astronomy or astrology into route handlers
- mutate shared kernel lifecycle state after startup

---

## 2. Packaging Decision

## 2.1 Recommended Package Shape

Implement the server as a separate top-level package in the same repository:

- `moira_server/`

Do not embed HTTP handlers into `moira/`.

Reason:

- `moira/` remains the engine
- `moira_server/` is visibly transport and orchestration
- import boundaries stay legible
- future extraction into a separate distribution remains possible

## 2.2 Initial Package Layout

Recommended initial structure:

```text
moira_server/
  __init__.py
  app.py
  config.py
  dependencies.py
  errors.py
  lifecycle.py
  models/
    __init__.py
    common.py
    chart.py
    positions.py
    transits.py
    returns.py
    batch.py
    visibility.py
    phenomena.py
    relationship.py
  routers/
    __init__.py
    health.py
    chart.py
    positions.py
    transits.py
    returns.py
    batch.py
    visibility.py
    phenomena.py
    relationship.py
  serializers/
    __init__.py
    chart.py
    positions.py
    transits.py
    returns.py
    batch.py
    visibility.py
    phenomena.py
    relationship.py
  services/
    __init__.py
    chart.py
    positions.py
    transits.py
    returns.py
    batch.py
    visibility.py
    phenomena.py
    relationship.py
```

Supporting files:

```text
tests/server/
  test_server_startup.py
  test_server_error_mapping.py
  test_server_chart_routes.py
  test_server_transit_routes.py
  test_server_batch_routes.py
  test_server_visibility_routes.py
  test_server_phenomena_routes.py
  test_server_relationship_routes.py
```

Optional deployment files later:

```text
docker/
  moira-server.Dockerfile
```

---

## 3. Dependency And Runtime Policy

## 3.1 Server Dependencies

Add server dependencies as an optional extra rather than a core engine
dependency.

Recommended future `pyproject.toml` extra:

```toml
[project.optional-dependencies]
server = [
  "fastapi>=0.115",
  "uvicorn>=0.30",
  "pydantic>=2.8",
]
```

Optional later additions:

- `orjson` for fast JSON serialization
- `slowapi` or equivalent for rate limiting
- `httpx` for server tests

## 3.2 Runtime Environment

Server development and verification must use the repository `.venv`.

The server must inherit the same kernel-availability truth as the engine.

The server must not download kernels automatically during request handling.

---

## 4. Startup And Lifecycle Design

## 4.1 Startup Rule

At service startup:

1. resolve kernel path configuration
2. validate kernel readiness or fail clearly
3. create one stable `Moira` instance per process
4. publish that instance through dependency injection

## 4.2 Dependency Injection Rule

Use a single dependency provider, for example:

- `get_engine() -> Moira`

That provider must return the stable startup-created instance.

It must not:

- construct a new `Moira()` per request
- call `set_kernel_path()` per request
- call `swap_reader()` or `reset_singleton()` per request

## 4.3 Startup Failure Policy

If no kernel is available:

- startup should fail with a clear operational message for production mode

Optional future development mode:

- allow startup with a degraded surface only if the route set is explicitly
  restricted to kernel-free endpoints

Default recommendation:

- fail startup if the configured route set includes kernel-dependent endpoints

---

## 5. API Surface Rollout Order

The first server release should expose only stable, already-audited engine
products.

## Phase 1: Minimal Operational Surface

Endpoints:

- `GET /health`
- `GET /ready`
- `GET /meta/version`
- `GET /meta/kernel`

Purpose:

- operational readiness
- engine version visibility
- kernel readiness visibility

Engine dependencies:

- `Moira`
- `m.is_kernel_available()`
- `m.get_kernel_status()`
- package version metadata

Acceptance:

- service starts cleanly
- readiness reports kernel truth honestly
- no request path mutates lifecycle state

## Phase 2: Positions And Chart Surface

Endpoints:

- `POST /v1/chart`
- `POST /v1/positions/planet`
- `POST /v1/positions/sky`
- `POST /v1/houses`

Engine surfaces:

- `Moira.chart(...)`
- `planet_at(...)` or facade equivalent
- `Moira.sky_position(...)`
- `Moira.houses(...)`

Purpose:

- expose the most fundamental read-only truth products first

Acceptance:

- transport schema preserves core chart and position semantics
- geometric vs apparent distinctions remain visible where applicable

## Phase 3: Transit And Return Surface

Endpoints:

- `POST /v1/transits/search`
- `POST /v1/transits/ingresses`
- `POST /v1/transits/next-ingress`
- `POST /v1/returns/solar`
- `POST /v1/returns/lunar`
- `POST /v1/returns/planet`
- `POST /v1/lunar-phases`

Engine surfaces:

- `find_transits(...)`
- `find_ingresses(...)`
- `next_ingress(...)`
- `solar_return(...)`
- `lunar_return(...)`
- `planet_return(...)`
- `find_lunar_phases(...)`

Acceptance:

- event schemas preserve relation, classification, and truth fields where those
  are part of public engine semantics

## Phase 4: Batch Surface

Endpoints:

- `POST /v1/batch/charts`
- `POST /v1/batch/transits`
- `POST /v1/batch/returns`
- `POST /v1/batch/progressions`
- `POST /v1/batch/events`

Engine surfaces:

- `moira.batch.*`

Acceptance:

- per-request failure isolation remains visible
- batch failure semantics are not flattened into one generic server error

## Phase 5: Visibility Surface

Endpoints:

- `POST /v1/visibility/assessment`
- `POST /v1/visibility/tonight`

Engine surfaces:

- `visibility_assessment(...)`
- `visibility_tonight(...)`
- `is_visible_tonight(...)`

Acceptance:

- observer-environment inputs remain explicit
- visibility criterion family remains visible

---

## 6. Endpoint Design Rules

## 6.1 Use POST For Computation

Use `POST` for most computation endpoints, even when they are read-only.

Reason:

- many requests have structured bodies
- request payloads may be too large or too nested for clean query-string usage
- doctrinal and policy objects serialize more cleanly in JSON bodies

Use `GET` only for:

- health and readiness
- metadata
- possibly simple status resources later

## 6.2 Version Prefix

Prefix computational routes with `/v1/`.

Example:

- `/v1/chart`
- `/v1/transits/search`

This keeps transport evolution explicit without implying engine semantic drift.

## 6.3 Route Shape

Prefer noun-plus-action clarity over RPC sprawl.

Good:

- `/v1/chart`
- `/v1/transits/search`
- `/v1/returns/solar`

Avoid:

- `/computeEverything`
- `/doTransit`
- `/api/calc`

---

## 7. Request And Response Model Strategy

## 7.1 Model Layer Separation

Keep three layers distinct:

1. engine result vessels
2. internal serializer mapping
3. transport schema models

Do not use engine dataclasses directly as FastAPI response models.

Reason:

- engine vessels are canonical semantic objects
- transport models are versioned serialized views
- mapping must remain explicit

## 7.2 Serializer Rule

Each endpoint family should have explicit serializer functions, for example:

- `serialize_chart(...)`
- `serialize_transit_event(...)`
- `serialize_visibility_assessment(...)`

These serializers must be thin and declarative.

They must not compute new doctrine.

## 7.3 Canonical Truth Preservation

Where the engine exposes meaningful public truth fields, the first transport
version should preserve them unless there is a strong reason not to.

Examples:

- `TransitEvent.relation`
- `TransitEvent.classification`
- `TransitEvent.computation_truth`
- `VisibilityAssessment.criterion_family`

If a reduced response profile is offered, it must be explicit and versioned.

---

## 8. Error Envelope Design

## 8.1 Error Categories

Map errors into at least these transport categories:

- input validation failure
- missing kernel readiness
- unsupported doctrine or feature
- internal server failure

## 8.2 Recommended HTTP Mapping

- client validation errors -> `422`
- missing kernel readiness -> `503`
- unsupported doctrine -> `400` or `501`, depending on whether the request is
  malformed or the feature is intentionally unavailable
- internal failure -> `500`

## 8.3 Error Envelope Fields

Recommended fields:

- `error_code`
- `message`
- `request_id`
- `category`
- optional `details`

Do not expose stack traces to clients in production responses.

Do log enough internal detail for diagnosis.

---

## 9. Configuration Plan

Create a small typed config layer:

- host
- port
- log level
- kernel path override
- docs enabled/disabled
- request size limits

Recommended source order:

1. environment variables
2. explicit startup config object

Do not introduce database, queue, or auth config in phase 1 unless it is
actually implemented.

---

## 10. Authentication And Rate Limiting

Not required for phase 1 local/server bring-up.

Phase 2 or later:

- simple API key auth
- per-key rate limits

These belong entirely in the server layer.

They must not leak into engine signatures or engine modules.

---

## 11. Logging And Observability

The server should log:

- startup configuration summary, minus secrets
- kernel readiness outcome
- request ID
- route name
- duration
- error category on failure

The server should not log:

- full sensitive request payloads by default
- raw stack traces to client responses

Future observability additions:

- metrics endpoint
- request timing histograms
- structured JSON logs

---

## 12. Testing Plan

## 12.1 Server Test Bands

Add a distinct server test band under:

- `tests/server/`

## 12.2 Minimum Test Inventory

Phase 1:

- startup succeeds with configured kernel
- readiness endpoint reports correct kernel state
- startup fails clearly when required kernel is missing

Phase 2:

- chart route matches direct engine output for selected fields
- position route preserves apparent/geometric semantics
- validation failures map to `422`

Phase 3:

- transit route preserves event ordering and key truth fields
- ingress route preserves sign and direction semantics
- lunar-phase route preserves phase type and JD

Phase 4:

- batch route preserves per-item failure isolation
- large-request validation fails cleanly

Phase 5:

- visibility route preserves criterion family and observability verdict
- facade/module parity is maintained through transport mapping

## 12.3 Adversarial Server Tests

Required adversarial cases:

- invalid latitude/longitude
- non-finite JD inputs
- reversed date windows
- missing kernel readiness
- unsupported sign names or body targets
- oversized request bodies if limits are enabled

## 12.4 Boundary Tests

Add explicit tests to prove forbidden behaviors stay forbidden:

- no request path calls kernel lifecycle mutators
- no per-request `Moira()` construction if stable singleton injection is the
  selected design
- serializer output does not collapse distinct engine truth fields

---

## 13. Verification Gates

No server phase is complete until all of the following are true for that phase:

1. route behavior is covered by focused tests
2. engine truth is not flattened or redefined
3. startup lifecycle follows `docs/threading.md`
4. error mapping is explicit and honest
5. no request-flow kernel mutation exists

---

## 14. Non-Goals For Initial Server Work

Do not include in the first implementation wave:

- user account systems
- billing
- chart database persistence
- workflow-heavy report generation
- kernel download orchestration via request flow
- live kernel switching
- server-side interpretive synthesis

These can be added later if needed, but they are not required to prove the REST
access surface.

---

## 15. Recommended Implementation Sequence

1. add optional `server` dependencies
2. scaffold `moira_server/` package
3. implement config and startup lifecycle
4. implement health/ready/meta routes
5. implement chart and positions routes
6. implement transit and return routes
7. implement batch routes
8. implement visibility routes
9. add rate limiting and auth if needed
10. add Docker packaging last

This order ensures the stable-reader and serialization boundary are proven
before the larger transport surface is exposed.

---

## 16. Definition Of Done

The first REST implementation is successful when:

- the server lives outside `moira/`
- startup creates one stable initialized engine surface per process
- request handlers are read-only with respect to kernel lifecycle state
- the first transport schemas preserve canonical engine meaning
- tests prove route correctness, error honesty, and boundary compliance
- the server is operationally deployable without redefining Moira's identity

That target is now met for the first admitted rollout wave.

The remaining question is not whether `moira-server` exists, but how the
rest of the public engine should be exposed without violating the same
boundary. That broader expansion program is governed by
`docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`.
