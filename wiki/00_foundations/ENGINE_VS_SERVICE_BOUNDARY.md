# Engine vs Service Boundary

Version: 1.0
Date: 2026-03-24
Runtime target: Python 3.14

This document defines the architectural boundary between the **Moira engine**
and any surrounding **service layer**.

It exists to keep the engine coherent as Moira becomes more publicly exposed and
feature requests expand beyond pure computation.

---

## 1. Core Rule

Use this distinction:

- Engine: **what is true?**
- Service layer: **what do we do with it?**

Equivalent phrasing:

- Engine = computation and domain truth
- Service layer = orchestration and applied workflow

This is the primary boundary rule.

---

## 2. Engine Responsibilities

The engine owns canonical computation.

That includes:

- astronomy, astrology, and mathematical truth
- typed result vessels and stable domain APIs
- transformations between domain representations
- deterministic search and solver logic
- canonical domain file-format primitives when those primitives are part of the
  computational substrate
- explicit doctrine and policy surfaces when they affect computed truth

The engine should answer questions like:

- where is this body?
- what is the next ingress?
- what is the eclipse classification?
- what is the angular separation?
- what are the house cusps?
- how do I write this validated state series into a BSP kernel?

Examples that belong in the engine:

- `planet_at(...)`
- `sky_position_at(...)`
- `next_solar_eclipse(...)`
- `find_phenomena(...)`
- `angular_separation_at(...)`
- `write_spk_type13(...)`

---

## 3. Service Responsibilities

The service layer owns workflow.

That includes:

- orchestration across multiple engine subsystems
- file acquisition, persistence, caching, and manifests
- external-system coordination
- retries, batching, progress reporting, and job control
- user-meaningful workflows built from engine primitives
- policy choices that are about application behavior rather than mathematical truth

The service layer should answer questions like:

- how do we fetch source states for these bodies?
- how do we build a user-custom ephemeris from those states?
- how do we store, index, or cache the result?
- how do we report progress back to the UI?
- how do we retry failed external fetches?

Examples that belong in the service layer:

- `build_custom_ephemeris_from_horizons(...)`
- `prepare_minor_body_kernel(...)`
- `refresh_gaia_cache(...)`
- `generate_chart_report(...)`
- `import_user_body_state_table(...)`

---

## 4. Practical Decision Test

When deciding where a feature belongs, ask these questions in order:

1. Is this function primarily computing canonical domain truth?
2. Would it still make sense in a pure research notebook with no UI, network,
   cache, database, or user session?
3. Is the output a stable domain result rather than an application workflow artifact?

If the answer is mostly yes, it probably belongs in the engine.

Then ask:

1. Is this coordinating multiple steps across boundaries?
2. Is it handling persistence, downloads, retries, batching, or progress?
3. Is it answering a user workflow question rather than a pure truth question?

If the answer is mostly yes, it probably belongs in the service layer.

---

## 5. DAF / BSP Example

This distinction matters for the ephemeris-writing story.

Engine:

- SPK/DAF encoding rules
- type-13 payload construction
- state validation required by the file format
- the writer primitive itself

That is why `daf_writer.py` belongs in the engine.

Service:

- fetch states from Horizons or another source
- choose sampling cadence
- assign NAIF IDs for user-created bodies
- build manifests and provenance records
- decide output locations
- report progress and failures to a UI or job runner

That is why a future `create_custom_ephemeris(...)` workflow belongs in a
service layer, not in the core engine.

---

## 6. What the Engine Must Not Own

The engine should not own:

- UI logic
- user sessions
- progress bars
- job queues
- web handlers
- download orchestration
- cache invalidation policy
- database persistence
- account, permission, or billing behavior
- application-specific report assembly unless the report is itself a canonical
  domain object

These things may call the engine, but they should not be embedded into it.

---

## 7. Validation Artifacts

Validation artifacts conceptually belong with the engine, even when their
execution harness lives in `tests/`.

This includes:

- oracle descriptions
- fixture provenance notes
- external-reference corpus definitions
- declared tolerances and residual policies
- doctrine tables used to define correctness

Why:

- they define what the engine means by truth
- they bound the engine's claims
- they are part of the engine's constitutional legitimacy, not merely test plumbing

So the rule is:

- test runners and harness code may live in `tests/`
- but the truth basis they encode is part of the engine's own contract

---

## 8. Borderline Cases

Some features look like services but actually belong in the engine.

Examples:

- low-level file-format writers
- coordinate transforms
- doctrine policies that change computed truth
- search primitives that can be reused in many contexts

The deciding question is not:

- does this feel advanced?

The deciding question is:

- is this a reusable truth primitive?

If yes, it belongs in the engine.

Likewise, some features look computational but still belong in services.

Examples:

- downloading ephemeris source data
- choosing where generated files live
- retrying failed external requests
- maintaining caches or indexes across runs

These are application behaviors, not computational truths.

---

## 9. Anti-Pattern Example

The following kind of function must not live in the engine:

- `build_custom_ephemeris_from_horizons(...)`

Why it is a service-layer anti-pattern in the engine:

- it coordinates an external source
- it chooses sampling and workflow policy
- it handles acquisition and likely retries/failures
- it bundles multiple computational primitives into one user workflow
- it produces an operational artifact rather than a single canonical truth step

What belongs in the engine instead:

- state validation
- SPK/DAF encoding primitives
- low-level writer functions
- deterministic interpolation and search math

What belongs in the service layer:

- fetching Horizons states
- deciding which bodies to include
- deciding cadence and export policy
- assembling provenance manifests
- storing or publishing the generated file

If this anti-pattern enters the engine, the engine stops being a truth layer
and starts becoming an application workflow layer. That is exactly the boundary
this document is meant to prevent.

---

## 10. Public Feature Triage Rule

When a user requests a feature, classify it first:

- Engine feature
- Service-layer feature
- UI feature
- Out of scope

Moira should only absorb the feature into the engine if it strengthens the
engine's role as a provider of canonical truth primitives.

If the feature is mainly about applying, packaging, delivering, caching, or
operationalizing those primitives, it belongs outside the engine.

This is a valid and intentional answer:

> That is a service-layer feature, not a Moira engine feature.

That answer is correct when the request is about workflow rather than truth.

---

## 11. Constitutional Summary

Moira the engine computes truth.

Services decide how that truth is acquired, composed, persisted, and delivered.

If a proposed addition does not improve Moira as a domain-truth engine, it
should not enter the engine by default.
