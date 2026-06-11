# Moira Server Route Admission Checklist

Version: 1.1
Date: 2026-06-11
Status: Active implementation checklist
Scope: Required gate before any new `moira_server` route family is admitted

This document turns the server boundary into an operational checklist.

It exists to prevent three failure modes:

- inventing transport doctrine that the engine does not own
- exposing unstable or non-read-only engine surfaces casually
- adding routes without parity and adversarial proof

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/threading.md`
- `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`

---

## 1. Required Sequence

No new route family is admitted until these steps are completed in order:

1. evaluate the engine family before transport design
2. classify the engine surface
3. decide synchronous vs batch vs async transport stance
4. define request and response models
5. define the serializer truth contract
6. bind a service adapter to the stable engine surface
7. add route handlers
8. add parity and adversarial tests
9. update architecture status docs

---

## 2. Pre-Admission Evaluation

Before a route family is shaped for REST, the underlying engine family must be
evaluated as an engine family.

This stage asks whether the substrate is complete enough, stable enough, and
truthful enough to expose. It is not yet a transport-design exercise.

Every candidate family must answer:

- What is the governing computational or doctrinal object?
- Is the family complete enough to expose, or are required public surfaces still
  missing?
- Is the doctrine stable, or are active questions still unresolved?
- Are all policy objects, result vessels, condition profiles, truth records,
  validation helpers, and public facade exports present where the family
  naturally requires them?
- Does the family already have backend-standard documentation, provenance, and
  validation evidence?
- Are there known accuracy, doctrine, naming, coverage, or ergonomics problems
  that should be improved before REST admission?
- Are there surfaces that should remain engine-only, deferred, batched, or
  excluded from ordinary public compute routes?

The output of this stage should be a short family evaluation record in the
phase ledger, with one of these statuses:

- `admit_now` - engine family is complete and doctrine-stable enough for REST
- `admit_after_minor_engine_work` - bounded engine/doc fixes should precede REST
- `defer_for_engine_completion` - transport work would expose an incomplete
  family
- `defer_for_doctrine` - doctrine is not stable enough for public transport
- `exclude_from_rest` - family does not belong on the ordinary REST compute
  surface

Fail if:

- route design begins before the family evaluation is recorded
- REST exposure is used to paper over missing engine doctrine or missing result
  vessels
- "we can expose what exists" becomes a substitute for asking whether what
  exists is actually complete enough and doctrine-stable

---

## 3. Admission Questions

Every candidate endpoint must answer all of the following.

### 3.1 Engine Ownership

- Is there a stable public engine surface already?
- Is the route calling `moira`, `moira.predictive`, `moira.vedic`, `moira.facade`, or another public package surface rather than a private helper?
- If the route must call a lower-level module function, is that because the public facade does not yet carry the needed truth without flattening it?

Fail if:

- the route would need to re-implement doctrine in the server
- the route would need to call `_facade_*`, `_export_governance/*`, or internal helper strata as if they were public doctrine

### 3.2 Read-Only Request Flow

- Is the surface read-only during request handling?
- Does the route avoid `set_kernel_path()`, `swap_reader()`, `reset_singleton()`, or equivalent lifecycle mutation?
- If a module-level engine function needs the process reader, can it be bound through `use_reader_override(...)` without mutating process state?

Fail if:

- request flow mutates kernel lifecycle state
- the route depends on on-demand kernel acquisition or reconfiguration

### 3.3 Transport Honesty

- Does the engine already expose a canonical result vessel?
- Can the server preserve the doctrinal distinctions in that vessel?
- Is the response model typed enough to keep different engine products visibly distinct?

Fail if:

- the route would collapse different doctrinal products into one vague schema
- event summaries, path products, profiles, and raw result families would be flattened together

### 3.4 Operational Stance

- Is ordinary synchronous request/response sane for this surface?
- If not, should the route be batch, bounded, paged, or async?
- Are the input bounds explicit enough to keep the server operationally honest?

Fail if:

- a heavy engine surface is exposed as naive unbounded synchronous HTTP

---

## 4. Transport Decision Matrix

Use this matrix before writing code.

### 4.1 Synchronous Direct Route

Use when all are true:

- one request maps to one bounded engine computation
- result size is modest
- the route is naturally inspectable in one response

Examples:

- chart construction
- returns
- synastry contacts
- annual profection

### 4.2 Batch Route

Use when:

- the engine already has a batch surface, or
- the same bounded computation must be repeated across many items

Requirements:

- per-item success/failure isolation
- item-local truth preservation
- no route-level masking of partial failure

### 4.3 Async Or Heavy Route

Use when:

- runtime is materially heavier than current synchronous server norms
- result size is large
- sampling, paging, or job control is needed

Examples:

- large astrocartography grids
- broad electional scans
- large catalog sweeps

---

## 5. Request-Model Checklist

Every new route family must define:

- an explicit Pydantic request model
- all required datetime/location/body/policy inputs
- route-level validation for body names, methods, and enum-like settings
- clear reversed-window or invalid-range rejection where time intervals exist

Positive example:

- method fields like `midpoint_location` or `midpoint` are validated at the request boundary before service dispatch

Anti-pattern:

- letting unsupported body names or method strings fall through into engine `KeyError` or unrelated `ValueError`

---

## 6. Response-Model Checklist

Every new route family must define:

- an explicit response model
- named typed fields for canonical engine truth
- distinct models for materially different product families

Required rule:

- transport schemas are serialized views over canonical engine result types
- they are not replacement doctrine objects

This means:

- engine vessels remain semantically primary
- response models exist to preserve and expose that truth over HTTP

Fail if:

- the easiest JSON shape wins over the canonical engine ontology

---

## 7. Serializer Checklist

Before a serializer is admitted:

- identify the exact engine vessel being serialized
- map fields explicitly
- preserve optional truth/classification/relation/profile fields where present
- preserve type distinctions across product families

Required discipline:

- do not rely on `__dict__` for slotted engine dataclasses
- do not leak internal enums or internal object identity in unstable form
- keep field naming stable and visible

Positive example:

- `SynastryAspectContact` serializes:
  - aspect
  - truth
  - classification
  - relation
  - condition profile

Anti-pattern:

- serializing only the aspect angle and dropping the synastry-specific truth layer

---

## 8. Service-Adapter Checklist

Every new service helper must:

- call the stable engine surface directly where possible
- keep request normalization out of routers
- centralize repeated chart-building logic where lawful
- preserve the stable reader model

Routers should do as little as possible beyond:

- dependency injection
- request acceptance
- response-model return

Fail if:

- route handlers begin reconstructing engine doctrine themselves

### 8.1 Sidereal Chart Derivation Gate

For chart-backed Vedic or classical routes that require sidereal longitudes,
sidereal sign indices, Lagna, nodes, or ayanamsa provenance, the route family
must use the post-Phase-9 shared derivation workflow:

- `docs/architecture/POST_PHASE9_SIDEREAL_CHART_DERIVATION_WORKFLOW.md`

Required answers before route design:

- Which bodies are required?
- Are nodes required?
- Are houses or Lagna required?
- Are planet speeds required?
- Which ayanamsa system is used?
- Which derived inputs will be returned as provenance?

Fail if:

- a route creates an ambient current ayanamsa
- a route stores request-derived sidereal positions in module-level state
- a route hides tropical-to-sidereal conversion without response provenance
- two route families implement separate, inconsistent sidereal chart
  derivation paths

---

## 9. Testing Checklist

Every new route family must add:

### 9.1 Parity Witness

- one focused live-engine parity test
- direct comparison to the real engine surface
- enough assertions to prove route truth, not just `200 OK`

### 9.2 Adversarial Witness

- invalid body/method inputs
- reversed windows where applicable
- missing required inputs
- hostile mixed batch items where batch surfaces exist

### 9.3 Structural Verification

- route module import/compile sanity
- broader server suite pass when the family is admitted

Minimum verification commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/server/test_server_<family>_routes.py -q
.venv\Scripts\python.exe -m pytest tests/server/... -q
.venv\Scripts\python.exe -m compileall moira_server
```

---

## 10. Documentation Checklist

After a route family is implemented:

- update `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`
- update `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- move the phase frontier forward only if the phase is truly complete

Fail if:

- docs still speak as if the phase is pending after code and tests are live

---

## 11. Definition Of Admission

A route family is admitted only when all are true:

- pre-admission family evaluation is recorded
- the engine surface is stable and public
- request flow is read-only
- request/response models are explicit
- serializers preserve canonical engine truth
- parity tests pass
- adversarial tests pass
- architecture docs reflect reality

If any one of those is missing, the family is still in implementation, not admitted.
