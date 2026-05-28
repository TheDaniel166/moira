# Moira Server Route Admission Checklist

Version: 1.0
Date: 2026-05-28
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

1. classify the engine surface
2. decide synchronous vs batch vs async transport stance
3. define request and response models
4. define the serializer truth contract
5. bind a service adapter to the stable engine surface
6. add route handlers
7. add parity and adversarial tests
8. update architecture status docs

---

## 2. Admission Questions

Every candidate endpoint must answer all of the following.

### 2.1 Engine Ownership

- Is there a stable public engine surface already?
- Is the route calling `moira`, `moira.predictive`, `moira.vedic`, `moira.facade`, or another public package surface rather than a private helper?
- If the route must call a lower-level module function, is that because the public facade does not yet carry the needed truth without flattening it?

Fail if:

- the route would need to re-implement doctrine in the server
- the route would need to call `_facade_*`, `_export_governance/*`, or internal helper strata as if they were public doctrine

### 2.2 Read-Only Request Flow

- Is the surface read-only during request handling?
- Does the route avoid `set_kernel_path()`, `swap_reader()`, `reset_singleton()`, or equivalent lifecycle mutation?
- If a module-level engine function needs the process reader, can it be bound through `use_reader_override(...)` without mutating process state?

Fail if:

- request flow mutates kernel lifecycle state
- the route depends on on-demand kernel acquisition or reconfiguration

### 2.3 Transport Honesty

- Does the engine already expose a canonical result vessel?
- Can the server preserve the doctrinal distinctions in that vessel?
- Is the response model typed enough to keep different engine products visibly distinct?

Fail if:

- the route would collapse different doctrinal products into one vague schema
- event summaries, path products, profiles, and raw result families would be flattened together

### 2.4 Operational Stance

- Is ordinary synchronous request/response sane for this surface?
- If not, should the route be batch, bounded, paged, or async?
- Are the input bounds explicit enough to keep the server operationally honest?

Fail if:

- a heavy engine surface is exposed as naive unbounded synchronous HTTP

---

## 3. Transport Decision Matrix

Use this matrix before writing code.

### 3.1 Synchronous Direct Route

Use when all are true:

- one request maps to one bounded engine computation
- result size is modest
- the route is naturally inspectable in one response

Examples:

- chart construction
- returns
- synastry contacts
- annual profection

### 3.2 Batch Route

Use when:

- the engine already has a batch surface, or
- the same bounded computation must be repeated across many items

Requirements:

- per-item success/failure isolation
- item-local truth preservation
- no route-level masking of partial failure

### 3.3 Async Or Heavy Route

Use when:

- runtime is materially heavier than current synchronous server norms
- result size is large
- sampling, paging, or job control is needed

Examples:

- large astrocartography grids
- broad electional scans
- large catalog sweeps

---

## 4. Request-Model Checklist

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

## 5. Response-Model Checklist

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

## 6. Serializer Checklist

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

## 7. Service-Adapter Checklist

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

---

## 8. Testing Checklist

Every new route family must add:

### 8.1 Parity Witness

- one focused live-engine parity test
- direct comparison to the real engine surface
- enough assertions to prove route truth, not just `200 OK`

### 8.2 Adversarial Witness

- invalid body/method inputs
- reversed windows where applicable
- missing required inputs
- hostile mixed batch items where batch surfaces exist

### 8.3 Structural Verification

- route module import/compile sanity
- broader server suite pass when the family is admitted

Minimum verification commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/server/test_server_<family>_routes.py -q
.venv\Scripts\python.exe -m pytest tests/server/... -q
.venv\Scripts\python.exe -m compileall moira_server
```

---

## 9. Documentation Checklist

After a route family is implemented:

- update `docs/architecture/MOIRA_SERVER_IMPLEMENTATION_PLAN.md`
- update `docs/architecture/MOIRA_SERVER_FULL_ENGINE_EXPOSURE_PLAN.md`
- move the phase frontier forward only if the phase is truly complete

Fail if:

- docs still speak as if the phase is pending after code and tests are live

---

## 10. Definition Of Admission

A route family is admitted only when all are true:

- the engine surface is stable and public
- request flow is read-only
- request/response models are explicit
- serializers preserve canonical engine truth
- parity tests pass
- adversarial tests pass
- architecture docs reflect reality

If any one of those is missing, the family is still in implementation, not admitted.
