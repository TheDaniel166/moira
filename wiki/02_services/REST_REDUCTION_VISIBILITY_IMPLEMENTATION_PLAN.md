# REST Reduction Visibility Implementation Plan

Status: active implementation plan

Purpose
-------
This document defines the implementation sequence for bringing the Moira REST
surface into full alignment with the reduction-visibility contract.

It is not the contract itself.
It is not the audit ledger.

Those roles remain owned by:
- [ENGINE_VS_SERVICE_BOUNDARY.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md)
- [SERVICE_LAYER_GUIDE.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/02_services/SERVICE_LAYER_GUIDE.md)
- [REST_REDUCTION_VISIBILITY_AUDIT.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/02_services/REST_REDUCTION_VISIBILITY_AUDIT.md)

This plan governs rollout order, transport shape decisions, verification
obligations, and deferral discipline.

---

## 1. Governing Objective

The REST API must not collapse facade-visible computational truth into an
opaque final-only transport when the engine already exposes meaningful
reduction, policy, fallback, classification, or branch truth.

The implementation goal is therefore:

- preserve compact consumer-facing routes where useful
- add lawful reduction access without breaking existing callers
- keep transport truth summary-grade rather than exposing unstable internal
  implementation details
- expand route families in a controlled order, starting with foundational
  surfaces

---

## 2. Current Baseline

As of 2026-06-04:

- `positions` is the first fully remediated pilot family
  - compact routes remain:
    - `/v1/positions/planet`
    - `/v1/positions/sky`
  - sibling reduction routes now exist:
    - `/v1/positions/planet/reduction`
    - `/v1/positions/sky/reduction`
- `chart` now has a sibling reduction route:
  - `/v1/chart/reduction`
- `transits` and `relationship` already preserve substantial doctrinal truth
- `primary-directions` now has a sibling reduction route on the core arc-search surface:
  - `/v1/primary-directions/arcs/reduction`
- `primary-directions` search-derived routes now also include:
  - `/v1/primary-directions/profile/reduction`
  - `/v1/primary-directions/network/reduction`
- `progressions` chart-producing routes now have sibling reduction routes:
  - `/v1/progressions/secondary/reduction`
  - `/v1/progressions/secondary-declination/reduction`
  - `/v1/progressions/arc/reduction`
  - `/v1/progressions/time-key/reduction`
- `progressions` family completion routes now also include:
  - `/v1/progressions/house-frame/reduction`
  - `/v1/progressions/house-frame/arc/reduction`
  - `/v1/progressions/profile/reduction`
  - `/v1/progressions/network/reduction`
- several other route families are structurally healthy but inconsistent in
  how directly they expose reduction truth

This baseline is tracked in the live audit:
- [REST_REDUCTION_VISIBILITY_AUDIT.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/02_services/REST_REDUCTION_VISIBILITY_AUDIT.md)

---

## 3. Rollout Strategy

The rollout proceeds in four waves.

### Wave 1: Foundational Surface Closure

Goal:
- make the foundational entry surfaces reduction-visible

Status:
- implemented as of 2026-06-04 on the current admitted surface

Families:
- `chart`
- `houses` only as needed for symmetry with chart-level reduction transport

Primary deliverables:
- add a lawful chart reduction surface
- expose normalized datetime and Julian-day reduction
- expose observer context when present
- expose chart assembly policy actually applied
- expose per-body reduction summaries without requiring callers to reconstruct
  them body-by-body from separate endpoints

Preferred transport shape:
- sibling reduction endpoint
  - `/v1/chart/reduction`

Why:
- it preserves the current compact `/v1/chart` contract
- chart reduction is heavier than the positions reduction payload
- the chart route is foundational enough that a separate truth surface is
  easier to keep stable

Exit criteria:
- a chart reduction route exists
- compact `/v1/chart` remains backward-compatible
- chart reduction includes enough information to explain how each returned body
  reached transport form

Current state:
- satisfied by `/v1/chart/reduction`
- `houses` remains compact, with later sibling expansion left optional rather
  than required for wave closure

### Wave 2: Doctrinal Tension Closure

Goal:
- resolve families whose current transport language explicitly understates
  engine truth

Status:
- implemented as of 2026-06-04 on the current search-derived route family

Families:
- `primary-directions`

Primary deliverables:
- remove any transport posture that implies permanent omission of policy truth
- add a lawful path to fuller reduction or policy surfaces
- preserve current compact or opt-in ergonomics where possible

Preferred transport shape:
- likely sibling reduction routes or stronger expansion flags
- this family should not be widened casually on the main result routes

Exit criteria:
- no model or serializer language remains in open tension with the service
  contract
- a caller can inspect direction doctrine, policy, and branch truth without
  reading engine internals directly

Current state:
- satisfied on the search-derived route family through:
  - `/v1/primary-directions/arcs/reduction`
  - `/v1/primary-directions/profile/reduction`
  - `/v1/primary-directions/network/reduction`
- `speculum` remains compact-first and may remain so unless a later service
  decision requires a sibling truth surface

### Wave 3: Family Consistency Sweep

Goal:
- normalize partially compliant families so that similar truth domains are
  exposed through similar transport conventions

Status:
- started as of 2026-06-04 on the progression chart-producing routes

Families:
- `progressions`
- `timelords`
- `returns`
- `varshaphal`
- `visibility`
- `phenomena`

Primary deliverables:
- route-by-route audit against the now-stabilized pattern
- add reduction flags or sibling reduction routes where real gaps remain
- align field naming for:
  - computation truth
  - classification
  - relation
  - condition profile
  - observer context
  - policy actually applied

Exit criteria:
- no major family remains merely "accidentally partial"
- comparable route families use comparable truth vocabulary

Current state:
- `progressions` is now functionally closed at the family level
- `house-frame/cusps` remains intentionally compact
- `timelords`, `returns`, `varshaphal`, `visibility`, and `phenomena` remain
  unswept in Wave 3 terms

### Wave 4: Aggregate Surface Integrity

Goal:
- ensure aggregate routes do not erase per-item reduction truth

Status:
- started as of 2026-06-04 on `batch/charts` and `batch/progressions`

Families:
- `batch`
- any multi-result wrappers introduced later

Primary deliverables:
- preserve or embed per-result reduction where the wrapped family already has
  a lawful truth surface
- define when aggregate routes may intentionally omit reduction for payload
  economy and how the caller recovers it

Exit criteria:
- aggregation does not silently black-box already-compliant route families

Current state:
- `/v1/batch/charts/reduction` now preserves per-item chart reduction truth
- `/v1/batch/progressions/reduction` now preserves per-item progression reduction truth
- compact `batch/transits` and transit/ingress-style `batch/events` already
  preserve embedded wrapped-family truth through their event payloads
- `batch/returns` remains bounded by the weaker direct `returns` family
- heterogeneous `batch/events` remain mixed because not every event subtype has
  the same admitted reduction depth
- Wave 4 is therefore started but not closed

---

## 4. Transport Shape Rules

This plan freezes the following implementation preferences.

### 4.1 Compact Base Routes Stay Compact

Do not widen every existing response with large optional reduction fields by
default.

Reason:
- backward-compatibility
- payload economy
- easier client migration

### 4.2 Prefer Sibling Reduction Endpoints For Heavy Foundational Routes

Preferred examples:
- `/v1/chart/reduction`
- `/v1/positions/planet/reduction`
- `/v1/positions/sky/reduction`

Use sibling reduction endpoints when:
- the reduction payload is large
- the family is foundational
- the same request body can be reused cleanly

### 4.3 Use Expansion Flags Only When The Truth Surface Is Modestly Additive

Use `include_*` style expansions when:
- the payload increase is small
- the route already uses opt-in enrichment
- the truth being added is structurally subordinate to the main result

Likely candidates:
- parts of `primary-directions`
- selective `progressions` enrichments

### 4.4 Do Not Expose Unstable Internal Implementation State

Reduction transport should preserve:
- admitted stage sequence
- applied policy
- branch/fallback/classification truth
- normalized inputs
- observer context

Reduction transport should not promise:
- volatile helper-level internals
- debug-only intermediate vectors
- unstable substrate-private caches

---

## 5. Implementation Order

The concrete next steps are:

1. Audit whether `houses` needs a sibling reduction endpoint or only chart-level
   embedding.
2. Decide whether `primary-directions/speculum` should remain compact-only or
   gain a sibling reduction route.
3. Sweep `timelords`.
4. Sweep `varshaphal`, `visibility`, and `phenomena`. (returns direct family now complete with embedded reduction contract + controls.)
5. Update `batch/returns` now that direct returns has a family-level reduction contract (embedded computation_truth).
6. Revisit heterogeneous `batch/events` only after the weaker event subtypes
   have stronger family-level truth surfaces.

Sequencing law:
- do not start broad family consistency work until `chart` is closed
- do not widen aggregate routes before the embedded families stabilize

---

## 6. Verification Liturgy

Each implementation wave must satisfy both transport and behavioral checks.

### 6.1 Transport Checks

For each remediated route family:

- server route tests must verify compact-route backward compatibility
- server route tests must verify reduction-route truth presence
- validation-envelope behavior must remain unchanged for malformed input
- response models must remain strict (`extra="forbid"`)

### 6.2 Truth Checks

Reduction-route tests should verify, where relevant:

- normalized datetime and Julian-day truth
- observer context
- policy actually applied
- fallback or effective-system truth
- classification truth
- admitted stage sequence
- result/reduction agreement

### 6.3 Deferral Honesty

If a family is judged too underdetermined for immediate remediation:

- record the reason in the audit
- do not mark the family compliant prematurely
- do not hide the gap behind "future expansion" language

---

## 7. Non-Goals

This plan does not authorize:

- replacing the engine-facing facade with REST-first semantics
- exposing raw debug internals as if they were stable public doctrine
- refactoring unrelated route families for aesthetic uniformity
- breaking existing compact-route clients unless a separate compatibility
  decision is made explicitly

---

## 8. Completion Standard

This roadmap is complete only when:

- every foundational family has a lawful reduction path
- every partially compliant family has been either remediated or explicitly
  deferred with a stated reason
- no service-layer document still frames transport opacity as an intended
  endpoint
- batch and aggregate routes preserve, rather than erase, already-admitted
  reduction truth

Until then, the audit remains the live state ledger and this plan remains the
governing rollout sequence.
