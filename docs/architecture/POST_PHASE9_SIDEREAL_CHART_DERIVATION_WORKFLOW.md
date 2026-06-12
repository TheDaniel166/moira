# Post-Phase-9 Sidereal Chart Derivation Workflow

Version: 0.1
Date: 2026-06-11
Status: Complete; shared adapter and named post-Phase-9 consumers live
Scope: Shared server-owned derivation layer for deferred chart-backed Vedic and classical routes

Phase 9 admitted the named Vedic and classical doctrine families. Several
families were deliberately admitted as direct-sync routes because their engines
consume caller-supplied sidereal or chart-derived truth. The next workflow is
to make that derivation server-owned, visible, request-scoped, and reusable.

This document is not a new doctrine family. It is a post-Phase-9 transport
workflow for admitting chart-backed convenience routes without introducing
global state or hidden sidereal policy.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`

---

## 1. Governing Object

The governing object is a request-scoped **SiderealChartContext**:

> A frozen server-derived context that records tropical chart truth, ayanamsa
> policy, sidereal reduction, and optional house/Lagna/node truth for one
> request.

It is a transport/service adapter object, not an engine doctrine object.

It must make visible:

- timezone-aware source datetime
- Julian Day used for derivation
- observer latitude/longitude/elevation when required
- requested body set
- tropical longitudes produced by the chart engine
- planet speeds where required by a consuming family
- house cusps and Ascendant when requested
- tropical Lagna and sidereal Lagna when requested
- node policy and Rahu/Ketu truth when requested
- ayanamsa system
- ayanamsa offset value
- sidereal longitudes produced by reduction
- reduction provenance

---

## 2. Non-Global-State Law

The adapter must be pure from the caller's perspective.

It must not introduce:

- module-level mutable chart caches
- ambient current ayanamsa
- ambient current observer
- ambient current chart
- remembered sidereal positions between requests
- mutation of engine policy from one route to another
- process-global fallback state for Lagna, node, or house policy

The existing app-lifespan `Moira` instance may remain shared infrastructure.
All derived chart truth must be local to the request and returned as a frozen
context object.

---

## 3. Proposed Package Shape

Add the shared derivation adapter as a server service module:

```text
moira_server/
  models/
    sidereal_context.py
  services/
    sidereal_context.py
  serializers/
    sidereal_context.py
```

The first implementation should avoid a public route. This context is an
internal server adapter used by chart-backed doctrine routes. A diagnostic
route may be considered later only if it has a clear reduction/provenance
purpose and passes the route admission checklist as its own family.

---

## 4. Request Model Shape

Use a shared request fragment for chart-backed Vedic/classical routes that
need sidereal derivation.

Required base fields:

- `dt`: timezone-aware datetime
- `ayanamsa_system`: explicit string, defaulting only where the consuming
  doctrine already has a documented default

Optional request fields, admitted only when needed:

- `observer_lat`
- `observer_lon`
- `observer_elev_m`
- `bodies`
- `include_nodes`
- `node_policy`
- `house_system`
- `require_houses`
- `require_lagna`
- `require_speeds`

Validation rules:

- reject naive datetimes
- reject non-finite observer values
- reject invalid latitude/longitude ranges
- reject empty ayanamsa labels
- reject empty body sets
- reject missing observer fields when houses/Lagna are required
- reject unsupported node/house policy values at the request boundary

---

## 5. Service Adapter Responsibilities

The shared service should expose one narrow entry point, conceptually:

```python
derive_sidereal_chart_context(engine, request, requirements) -> SiderealChartContext
```

The `requirements` object should be explicit and route-owned:

- required bodies
- whether nodes are required
- whether houses are required
- whether Lagna is required
- whether speeds are required
- whether observer coordinates are mandatory

The service adapter should:

1. Validate aware datetime.
2. Build the tropical chart through the injected `Moira` instance.
3. Compute or read the Julian Day used by the chart.
4. Compute the ayanamsa offset for the declared system.
5. Reduce requested tropical longitudes to sidereal longitudes.
6. Derive sidereal sign indices where required.
7. Derive houses and Lagna only when required.
8. Return a frozen `SiderealChartContext`.

It should not:

- call route handlers
- know doctrine-family semantics such as Varga, Ashtakavarga, or dignity
  scoring
- silently expand body sets beyond declared route requirements
- hide ayanamsa or house policy defaults

---

## 6. Response Provenance

Chart-backed routes that consume this adapter should include a compact
provenance block unless the family already has a stronger reduction-response
shape.

Minimum provenance fields:

- `dt`
- `jd`
- `ayanamsa_system`
- `ayanamsa_offset`
- `observer` when used
- `bodies`
- `sidereal_longitudes`

When Lagna is used:

- `tropical_lagna`
- `sidereal_lagna`
- `sidereal_lagna_sign_index`

When houses are used:

- `house_system`
- `ascendant`
- house cusp summary or a link to an existing house response model if reused

---

## 7. First Admission Order

Admit chart-backed variants in the lowest-risk order:

1. **Vedic dignities chart-backed convenience**
   - Inputs: datetime, ayanamsa, bodies.
   - Needs sidereal longitudes only.
   - Best first proof of direct-vs-chart equivalence.

2. **Varga chart-backed convenience**
   - Inputs: datetime, ayanamsa, bodies, varga selector.
   - Needs sidereal longitudes only.
   - Proves batch/body-key preservation through derived context.

3. **Alternate dasha chart-backed convenience**
   - Inputs: natal datetime, ayanamsa, dasha policy.
   - Needs Moon longitude and natal JD.
   - Must preserve Ashtottari eligibility truth.
   - Status: live.

4. **Ashtakavarga chart-backed convenience**
   - Inputs: datetime, ayanamsa, required planets, Lagna.
   - Needs sidereal signs and sidereal Lagna.
   - Higher risk because Lagna/observer requirements become mandatory.
   - Status: live.

5. **Vedic drekkana/decanate chart-backed convenience**
   - Inputs: datetime, ayanamsa, selected body.
   - Needs body longitude, JD, and policy provenance.
   - Status: live for Decanates body-backed Vedic drekkana and decanate set.

Do not admit all chart-backed variants at once. Each family should have its own
transport design update, parity tests, adversarial tests, and REST reference
update.

---

## 8. Required Tests

Shared adapter tests:

- rejects naive datetime
- rejects non-finite observer values
- rejects missing observer when Lagna/houses are required
- rejects empty ayanamsa labels
- produces deterministic sidereal longitudes from tropical longitudes plus
  ayanamsa
- preserves requested body keys
- derives sidereal Lagna only when requested
- does not mutate module-level or app-level state

Per-family chart-backed tests:

- chart-backed route result equals direct route result when direct route is
  supplied the adapter-derived sidereal truth
- response provenance records ayanamsa and derived sidereal inputs
- family-specific missing-body failures are explicit
- family-specific policy values are validated at the request boundary

---

## 9. Definition Of Completion

This post-Phase-9 workflow is complete when:

- the shared context models/services/serializers exist
- adapter tests pass
- at least Vedic dignities and Varga chart-backed variants use the shared
  adapter
- no route computes its own one-off sidereal context when the shared adapter
  can supply it
- route documentation clearly distinguishes direct caller-owned truth from
  server-derived chart truth
- no `/v1/vedic` or `/v1/classical` umbrella route is introduced

Completion of this workflow is not required to keep Phase 9 admitted. It is the
next transport hardening step after Phase 9.

---

## 10. Implementation Plan

This workflow should be implemented as its own bounded server-infrastructure
unit before any deferred chart-backed Vedic/classical route is admitted.

The work is divided into gates. Do not advance to a later gate until the
earlier gate compiles, has focused tests, and preserves request-scoped state.

### Gate 0 - Existing Surface Audit

Purpose:

- confirm the exact chart, house, sidereal, and ayanamsa primitives the adapter
  may lawfully call
- avoid duplicating already-existing server helpers

Files to read before coding:

- `moira_server/services/_shared.py`
- `moira_server/models/chart.py`
- `moira_server/services/chart.py`
- `moira_server/serializers/chart.py`
- `moira/sidereal.py`
- `moira/facade.py`
- `moira/vedic.py`
- current direct-sync route modules for Vedic dignities, Varga, Ashtakavarga,
  alternate dashas, and decans

Gate output:

- no code required
- short implementation note in the PR/commit message identifying which public
  engine functions are used for ayanamsa and tropical-to-sidereal reduction

### Gate 1 - Shared Models

Add:

- `moira_server/models/sidereal_context.py`

Request fragment models:

- `SiderealChartBaseRequest`
- `SiderealObserverRequest`
- `SiderealHousePolicyRequest`, only if existing house policy models cannot be
  reused cleanly

Response/provenance models:

- `SiderealObserverResponse`
- `SiderealHouseContextResponse`
- `SiderealChartProvenanceResponse`
- `SiderealChartContextResponse`

Internal frozen dataclasses may live in the service module, but transport
response models must remain Pydantic models.

Validation requirements:

- `dt` must be timezone-aware
- `ayanamsa_system` must be non-empty
- body lists must be non-empty when supplied
- body names must be validated using the existing supported-body helper
- observer longitude must be finite and in `[-180, 180]`
- observer latitude must be finite and in `(-90, 90)` when houses or Lagna are
  required
- elevation must be finite when supplied

Do not add route-family-specific fields here. A Varga selector, Ashtakavarga
shodhana option, or dasha level belongs to the consuming route model.

### Gate 2 - Requirement Contract

Add to `moira_server/services/sidereal_context.py`:

```python
@dataclass(frozen=True, slots=True)
class SiderealChartRequirements:
    required_bodies: tuple[str, ...]
    include_nodes: bool = False
    require_houses: bool = False
    require_lagna: bool = False
    require_speeds: bool = False
    observer_required: bool = False
```

Rules:

- route services construct requirements explicitly
- requirements are immutable
- requirements may narrow or extend requested bodies, but only visibly
- if a route needs the Moon, Sun, Rahu, or Lagna, that requirement must be
  declared here before derivation
- if `require_houses` or `require_lagna` is true, observer coordinates are
  mandatory

Failure doctrine:

- unsupported body names fail before `engine.chart(...)`
- missing observer context fails before house/Lagna derivation
- empty required body sets fail at construction

### Gate 3 - Frozen Context Vessel

Add an internal service vessel:

```python
@dataclass(frozen=True, slots=True)
class SiderealChartContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    ayanamsa_system: str
    ayanamsa_offset: float
    requested_bodies: tuple[str, ...]
    returned_bodies: tuple[str, ...]
    tropical_longitudes: Mapping[str, float]
    sidereal_longitudes: Mapping[str, float]
    sidereal_sign_indices: Mapping[str, int]
    speeds: Mapping[str, float] | None
    observer: SiderealObserverContext | None
    houses: SiderealHouseContext | None
    tropical_lagna: float | None
    sidereal_lagna: float | None
    sidereal_lagna_sign_index: int | None
    stage_sequence: tuple[str, ...]
```

Implementation detail:

- use immutable copies of dictionaries internally, or at minimum copy incoming
  dictionaries before storing them in the frozen vessel
- never expose the mutable `chart.planets` mapping directly
- never store the engine, chart object, or request object inside the context

Required stage sequence:

```text
datetime_validation
chart_body_validation
tropical_chart_derivation
ayanamsa_resolution
tropical_to_sidereal_reduction
optional_house_derivation
optional_lagna_reduction
context_materialization
```

### Gate 4 - Derivation Service

Implement:

```python
derive_sidereal_chart_context(
    engine: Moira,
    request: SiderealChartBaseRequest,
    requirements: SiderealChartRequirements,
) -> SiderealChartContext
```

Required algorithm:

1. Validate aware datetime using `require_aware_datetime(...)`.
2. Validate requested and required bodies using
   `require_supported_chart_bodies(...)`.
3. Merge route-required bodies with caller-requested bodies deterministically.
4. Call `engine.chart(...)` through existing chart-building logic where
   possible.
5. Resolve `jd_ut` from the chart object if available; otherwise use
   `jd_from_datetime(...)`.
6. Resolve ayanamsa offset through the public sidereal API.
7. Reduce every returned tropical longitude to sidereal longitude.
8. Compute sidereal sign indices as `int(lon % 360 // 30)`.
9. If speeds are required, copy planet speeds from the chart vessel.
10. If houses or Lagna are required, call existing house context helpers and
    reduce Ascendant/Lagna through the same ayanamsa offset.
11. Materialize and return the frozen context.

Determinism rules:

- preserve caller body keys where supplied
- preserve engine-returned canonical body names
- sort or tuple-normalize internal requirement sets before derivation
- do not rely on dictionary insertion order for response summaries unless it
  has been explicitly created by the service

### Gate 5 - Serializer

Add:

- `moira_server/serializers/sidereal_context.py`

Serializers:

- `serialize_sidereal_observer_context(...)`
- `serialize_sidereal_house_context(...)`
- `serialize_sidereal_chart_provenance(...)`
- `serialize_sidereal_chart_context(...)`

Serializer rules:

- serialize explicit fields only
- do not serialize private chart/engine objects
- preserve both tropical and sidereal longitudes when the route exposes full
  context
- allow consuming route serializers to embed only the provenance subset when a
  compact response is preferable

### Gate 6 - Shared Adapter Tests

Add:

- `tests/server/test_server_sidereal_context.py`

Required tests:

- rejects naive datetime
- rejects empty ayanamsa label
- rejects unsupported body names
- rejects empty required body set
- rejects missing observer when Lagna is required
- rejects non-finite observer values
- derives sidereal longitudes equal to tropical longitudes minus ayanamsa
  offset modulo 360
- computes sidereal sign indices from derived sidereal longitudes
- preserves requested body keys
- includes required bodies even when the caller body list omits them
- derives speeds only when `require_speeds=True`
- derives Lagna only when `require_lagna=True`
- context is frozen
- mutating an input dictionary after derivation does not alter context truth
- repeated requests with different ayanamsa systems do not contaminate each
  other

Suggested test strategy:

- use the real `Moira` fixture or app-lifespan engine where existing tests do
  so
- use small representative body sets such as `("Sun", "Moon")`
- use one fixed aware datetime, such as J2000 noon UTC, for structural parity
- avoid broad numerical oracle claims; this gate proves transport derivation
  integrity, not new astronomical precision

### Gate 7 - First Consumer: Vedic Dignities

Update P9-08 transport design before coding.

Add chart-backed routes only after Gates 1-6 pass:

- `POST /v1/vedic-dignities/chart/dignity`
- `POST /v1/vedic-dignities/chart/relationships`
- `POST /v1/vedic-dignities/chart/profile`

Admission proof:

- chart route derives context
- direct route supplied with the same derived sidereal longitude produces the
  same dignity result
- response includes provenance with ayanamsa offset and sidereal inputs
- no Vedic-dignity service performs ad hoc sidereal conversion

### Gate 8 - Second Consumer: Varga

Update P9-11 transport design before coding.

Add chart-backed routes:

- `POST /v1/varga/chart/named`
- `POST /v1/varga/chart/shodashvarga`
- `POST /v1/varga/chart/shodashvarga/batch`

Admission proof:

- chart route derives context
- direct named/Shodashvarga routes supplied with the same derived sidereal
  longitudes produce matching `VargaPoint` results
- caller body keys and engine body names remain distinct and visible
- response provenance records ayanamsa and body derivation truth

### Gate 9 - Later Consumers

Admitted after Vedic dignities and Varga proved the adapter:

- alternate dasha chart-backed routes
- Ashtakavarga chart-backed routes
- Vedic drekkana/decanate chart-backed routes

Each later family updated its own P9 transport design and added focused server
route tests before REST reference changes.

### Gate 10 - Documentation And Route Inventory

For each consumer family:

- update that family transport design
- update `wiki/02_services/REST_API_REFERENCE.md`
- update route counts from the live app registry
- update the implementation plan only when a material frontier moves
- keep Phase 9 ledger complete; this is post-Phase-9 hardening, not reopening
  Phase 9 admission

### Gate 11 - Regression Ritual

Minimum commands for the shared adapter gate:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\sidereal_context.py moira_server\services\sidereal_context.py moira_server\serializers\sidereal_context.py tests\server\test_server_sidereal_context.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_sidereal_context.py -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_startup.py tests\server\test_server_error_mapping.py -q
```

Minimum commands for each consumer:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_<family>_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_sidereal_context.py tests\server\test_server_<family>_routes.py -q
```

Before declaring the workflow complete:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_sidereal_context.py tests\server\test_server_vedic_dignities_routes.py tests\server\test_server_varga_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_phase9_umbrella_exclusions.py -q
```

---

## 11. Implementation Risks And Controls

| Risk | Control |
|---|---|
| Hidden global ayanamsa state | Ayanamsa lives only on request/context vessels |
| Route-specific duplicate derivation | Route admission checklist now requires shared adapter |
| Mutable context maps inside frozen dataclass | Copy or freeze mappings at context construction |
| Silent body expansion | Requirements object declares every required body |
| Lagna without observer truth | Requirements reject missing observer before computation |
| Provenance omitted from convenience routes | Consumer response models must embed compact provenance |
| Reopening Phase 9 scope | Treat this as post-Phase-9 workflow, not new Phase 9 admission |
| Umbrella route drift | Keep `/v1/vedic` and `/v1/classical` exclusion tests live |

---

## 12. Work Breakdown Checklist

- [x] Gate 0: audit existing chart/sidereal/house surfaces
- [x] Gate 1: add shared request/provenance models
- [x] Gate 2: add immutable requirements contract
- [x] Gate 3: add frozen context vessels
- [x] Gate 4: implement derivation service
- [x] Gate 5: add serializers
- [x] Gate 6: add shared adapter tests
- [x] Gate 7: admit Vedic dignities chart-backed routes
- [x] Gate 8: admit Varga chart-backed routes
- [x] Gate 9: admit later consumers
- [x] Gate 10: update docs and route inventory per consumer
- [x] Gate 11: run regression ritual
