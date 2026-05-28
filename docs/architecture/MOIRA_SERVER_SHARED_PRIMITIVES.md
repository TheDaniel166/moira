# Moira Server Shared Primitives Map

Version: 1.0
Date: 2026-05-28
Status: Active implementation aid
Scope: Shared transport and service primitives that reduce duplication in phases 8+

This document identifies the repeated patterns already visible in `moira_server`
and turns them into a deliberate reuse map.

Its purpose is not abstraction for its own sake.

Its purpose is to keep future phases smaller, more consistent, and less likely
to drift away from the engine boundary.

---

## 1. Governing Rule

Shared primitives are justified only when they reduce repeated transport work
without obscuring computational truth.

They must not:

- become a second doctrine layer
- hide engine distinctions behind generic wrappers
- collapse unlike route families into one over-abstract surface

---

## 2. Existing Repetition Bands

The current server already repeats the same structural work in several phases.

### 2.1 Chart Construction Band

Recurring tasks:

- parse request datetime
- normalize latitude/longitude/system inputs
- compute chart
- compute houses when needed
- preserve the stable engine reader

Current location:

- chart services
- relationship services
- phenomena services where topocentric/event work needs bound reader context

Recommended shared primitive shape:

- single-chart builder
- single-chart-plus-houses builder
- paired-chart builder
- paired-chart-plus-houses builder

Use when:

- a route needs one or two fully built chart contexts before calling the engine

Do not use when:

- the engine surface already accepts raw JD/location inputs directly and the
  server would only be rebuilding chart state needlessly

### 2.2 Time Window Validation Band

Recurring tasks:

- ensure `start <= end`
- reject reversed windows at the transport boundary
- normalize optional bounds and step-like inputs

Recommended shared primitive shape:

- window validator for JD windows
- window validator for datetime windows

### 2.3 Body And Method Validation Band

Recurring tasks:

- validate public body names
- validate method strings
- reject unsupported policy knobs early

Recommended shared primitive shape:

- supported-body validator
- supported-method validator
- constrained enum-like validation helper

### 2.4 Reader-Bound Module Invocation Band

Recurring tasks:

- call module-level engine functions that are not instance methods
- preserve the request's stable engine reader

Current lawful mechanism:

- `use_reader_override(...)`

Recommended shared primitive shape:

- a thin service helper pattern for module calls under reader override

This should remain explicit.

Do not hide all module dispatch behind one generic black-box executor.

### 2.5 Event Search Response Band

Recurring tasks:

- return `events=[...]`
- preserve per-event classification/truth/profile
- keep event families typed

Recommended shared primitive shape:

- shared search-response model conventions
- shared serializer naming conventions

Do not over-merge event models that are doctrinally distinct.

### 2.6 Profile / Network Band

Recurring tasks:

- serialize condition profiles
- serialize aggregate profiles
- serialize network nodes and edges

This pattern now appears in:

- transits
- relationship surfaces
- phase-8 candidates such as progressions, timelords, dasha, and varshaphal

Recommended shared primitive shape:

- a documented serializer pattern library

The goal is not one universal base class.

The goal is stable field naming and route-family consistency.

---

## 3. Recommended Concrete Shared Helpers

These are the highest-value helpers to consolidate next.

### 3.1 Service Helpers

Recommended additions or consolidations under `moira_server/services/`:

- `_build_chart_context(...)`
- `_build_chart_with_houses_context(...)`
- `_build_pair_context(...)`
- `_build_pair_with_houses_context(...)`
- `_validate_time_window(...)`
- `_validate_supported_body(...)`
- `_validate_supported_method(...)`

These should remain small, explicit, and local to server transport work.

### 3.2 Serializer Conventions

Recommended stable naming:

- `serialize_*_truth`
- `serialize_*_classification`
- `serialize_*_relation`
- `serialize_*_condition_profile`
- `serialize_*_network`

This convention is already working well in phases 6 and 7.

### 3.3 Test Fixtures

Recommended additions under `tests/server/`:

- canonical single-chart request payload
- canonical pair request payload
- canonical event window payload
- canonical visibility payload
- standard error-envelope assertion helper

These would reduce duplicated literal payloads and validation-envelope checks.

---

## 4. What Not To Abstract

The following should remain route-family-specific:

- doctrinal field selection
- event-family response models
- annual doctrine serialization
- primary-direction policy exposure
- electional screening surfaces

If two families differ in doctrine, the transport layer should show that
difference rather than hiding it.

---

## 5. Priority Order For Reuse Work

If only a small amount of cleanup is done before phase 8, do this order:

1. chart/pair context builders
2. time-window validation helpers
3. supported-body/method validators
4. canonical server test payload fixtures
5. profile/network serializer conventions review

That gives the largest reduction in repeated work for the smallest touch.

---

## 6. Definition Of Success

This shared-primitives map is successful if phases 8+ can be implemented by:

- following the same request/service/serializer/test rhythm
- reusing chart and validation helpers instead of rewriting them
- keeping doctrinal differences visible in transport
- reducing route-family implementation to small, explicit deltas

If reuse begins to obscure engine truth, it has gone too far.
