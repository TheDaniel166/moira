# P8-14 Primary Directions – First Pass Design

**Date:** 2026-05  
**Status:** Phase 1 design locked and implemented; hardened test suite passing. Phase 2 planning section added below.  
**Scope:** First transport surface over the admitted primary directions engine (speculum + arc search + evaluation), with defined roadmap for subsequent increments.

## Governing Constraints

- This is the heaviest unit in Phase 8 (`heavy_sync`).
- The engine subsystem is rich: multiple methods, two spaces with strict invariants, explicit motion doctrine, time-key orthogonality, layered vessels (SpeculumEntry → PrimaryArc → Relation → RelationProfile → SignificatorProfile → Aggregate/Network), and a large `PrimaryDirectionsPolicy` object with many interdependent rules.
- The author of the primary directions engine has confirmed deep familiarity with these tensions.
- First-pass goal: useful, faithful exposure of the four ledger route groups without attempting to transport the entire policy surface or every admitted branch.

## Core Design Principle: Strong Default First

The transport layer will begin with one well-chosen, opinionated default policy that "just works" for the most common and doctrinally central use case (currently Placidian mundane with traditional converse).

The API surface for policy will then be allowed to grow incrementally over time as real usage demonstrates the need for additional controls.

This approach:
- Keeps the initial surface small and maintainable.
- Avoids prematurely freezing a large, complex policy model in transport.
- Respects the sovereignty and depth of the engine policy system.
- Provides a clear, stable path for future richness rather than trying to expose everything at once.

All documentation, models, and route descriptions will make this growth posture explicit.

## Route Surface (Locked for First Pass)

```
POST /v1/primary-directions/speculum
POST /v1/primary-directions/arcs
POST /v1/primary-directions/profile
POST /v1/primary-directions/network
```

### Responsibilities

- **speculum**: Return the equatorial/mundane speculum for a chart at a given observer latitude.
- **arcs**: Execute `find_primary_arcs` with reasonable controls and return the discovered arcs (with arc values and basic metadata).
- **profile**: Return per-significator condition profiles + aggregate profile (search + evaluate in one call for convenience).
- **network**: Return the directed promissor→significator graph view.

Convenience "search + evaluate" is favored in the first pass. Explicit "evaluate these pre-computed arcs" endpoints can be added later if real usage shows the need.

## Model Strategy

### Policy Handling – Strong Default + Incremental Growth

In line with the core principle above, the first pass will expose only a minimal set of policy controls on top of a strong, well-chosen default.

The initial `PrimaryDirectionsPolicyRequest` (if any) will be deliberately small. Most clients will simply omit it and receive a coherent, documented default behavior (Placidian mundane, traditional converse, sensible key, etc.).

Additional policy richness will be added to the transport layer over time only when there is demonstrated need, rather than attempting to model the full engine policy surface upfront.

This keeps the first release focused, honest about its limitations, and easier to evolve without accumulating technical debt in the transport models.

### Core Response Vessels (Faithful but Pragmatic)

We will create focused response models that preserve the important distinctions from the engine vessels:

- `SpeculumEntryResponse`
- `PrimaryArcResponse` (includes arc value + pre-computed years under the requested key where applicable)
- `PrimaryDirectionRelationResponse`
- `PrimaryDirectionRelationProfileResponse`
- `PrimaryDirectionsSignificatorProfileResponse`
- `PrimaryDirectionsAggregateProfileResponse`
- `PrimaryDirectionsNetworkNodeResponse`
- `PrimaryDirectionsNetworkEdgeResponse`
- `PrimaryDirectionsNetworkProfileResponse`

We will **not** attempt to mirror every internal helper, every possible target family, or every sub-policy in the first-pass responses. The goal is visibility of the main layers, not completeness of every admitted branch.

### Request Models

- `PrimaryDirectionsBaseRequest`: natal chart construction parameters + `observer_lat` + optional `obliquity`.
- `PrimaryDirectionsSearchRequest`: extends base + `max_arc`, `significators`, `promissors`, `include_converse`, and the narrow `policy` object above.
- The `/profile` and `/network` endpoints will accept the search request (convenience path). Support for sending a raw list of arcs for re-evaluation can be added in a later increment if needed.

## Deliberate Limitations (First Pass)

- No full `PrimaryDirectionsPolicy` transport.
- No support for every admitted method on day one (start with the most common: Placidian mundane, with clear path to add others).
- No advanced target families (fixed stars, antiscia, rapt parallels, etc.) in the initial policy request — these remain engine-only for now.
- No "evaluate these specific arcs under a different policy" endpoints in v1 (search + evaluate is the primary workflow).
- Time keys are limited to the four currently documented static/symbolic keys (Ptolemy, Naibod, Cardan, Solar). Dynamic keys remain out of scope for transport initially.
- Empty result handling will be explicit but minimal (empty lists / profiles with zero counts are acceptable).

These limitations are documented in the models and the route docstrings.

## Verification Requirements (Non-Negotiable)

- Parity tests against direct engine calls for all four endpoints.
- Adversarial tests for impossible searches, contradictory policy fragments, bad latitudes, unknown bodies, negative/zero max_arc, etc.
- Explicit boundary test proving the new routes perform zero kernel lifecycle mutation.
- Structural validation that the major doctrinal fields (method, space, motion, relation_kind, key, etc.) survive transport.
- Full `moira_server` app startup verification with the new router registered.

## Open Questions for This Increment (to be closed before coding begins)

These questions are now evaluated under the "strong default + allow richness to grow" principle. Preference should be given to keeping the first pass small unless there is clear justification otherwise.

1. Should `/arcs` always return pre-computed Naibod years (in addition to the raw arc value), or only years under the key chosen through the (still-minimal) policy surface?
2. Should we offer a small number of named presets (e.g. `"placidian_mundane"`) as an ergonomic option on top of the default behavior, even in v1?
3. For the network response, do we include `most_connected` and `isolated` immediately, or defer them to a later increment?

---

**Next step after approval of this document**: Phase 1 implementation is complete. Future work on P8-14 should follow the Phase 2 increments outlined above, maintaining the "strong default first, grow richness based on demand" principle.

This phased approach respects both the depth of the primary directions engine and the need for a sustainable, evolvable transport surface.

---

## Phase 2 / Subsequent Increments

### Guiding Principle for Phase 2

Phase 1 established the four core route groups (`speculum`, `arcs`, `profile`, `network`) with a deliberately narrow policy surface and convenience "search + evaluate" workflows.

Phase 2 should focus on **increasing the fidelity and flexibility of the existing route groups** rather than adding many new top-level endpoints. The emphasis is on:

- Exposing more of the layered doctrine already present in the engine (especially relations and condition).
- Supporting the common real-world pattern of "search once, evaluate many ways."
- Gradually widening the policy surface only where client demand and operational stability justify it.

New top-level routes should be added sparingly. Most new capability should appear as additional response depth, optional query parameters, or new sub-resources under the existing four families.

### Priority Areas for Phase 2 (in suggested order)

#### 1. Relation Depth Expansion (Highest immediate value)

**Goal**: Move beyond the thin `detected_relation` currently returned inside profiles.

**Engine surfaces to expose more fully**:
- `relate_primary_arc`
- `evaluate_primary_direction_relations` (full `PrimaryDirectionRelationProfile` including `admitted_relations` and `scored_relations`)

**Possible increments**:
- Expand `PrimaryDirectionRelationProfileResponse` in the existing `/profile` responses to include admitted and scored relations (behind an optional `include_relations=true` flag or always for the first increment).
- Add a dedicated `POST /v1/primary-directions/relations` or `POST /v1/primary-directions/arcs/relate` endpoint that accepts one or more arcs and returns rich relation profiles.
- Allow clients to request relation evaluation under a different (still narrow) policy than the one used for arc discovery.

**Why first**: This is the most frequently requested "missing" layer once people start using the arcs endpoint seriously.

#### 2. Re-evaluation / Arc Submission Workflows

**Goal**: Let clients submit previously computed arcs for fresh evaluation.

**Current gap**: The only way to get relations, condition, aggregate, or network views is to run a search at the same time.

**Possible increments**:
- Add an optional `arcs` array field to the `/profile` and `/network` request bodies. When present, the server skips arc discovery and evaluates the submitted arcs instead.
- Add a lightweight `POST /v1/primary-directions/relations` that accepts a list of arcs + optional narrow policy and returns the corresponding relation profiles.
- Support sending arcs that were originally discovered under one policy and re-evaluating them under another (within the still-limited policy surface of Phase 2).

**Why important**: This is the dominant professional workflow with primary directions and is currently blocked.

#### 3. Policy Surface Growth (Gradual and Demand-Driven)

Continue the Phase 1 principle, but begin exposing more controls only when real usage demonstrates the need.

**Likely Phase 2 expansions** (in rough order of usefulness):
- Full time-key selection on arcs and relations (beyond just Naibod years).
- A small number of named presets (e.g. `"placidian_mundane"`, `"ptolemy_semiarc"`, `"topocentric"`) that expand to known-good policy combinations.
- Basic support for additional methods beyond the default (e.g. Ptolemy semi-arc, Regiomontanus) with clear documentation of their limitations.
- Initial exposure of a few common target families (fixed stars, antiscia) behind explicit opt-in flags.

**Constraints**:
- Every new policy field added must be accompanied by clear validation and error messages.
- The server must continue to reject (or safely default) combinations that violate engine invariants.

#### 4. Dedicated Condition / Per-Significator Surfaces

**Goal**: Allow clients to request the `PrimaryDirectionsSignificatorProfile` (local condition) layer independently or with richer detail.

**Current state**: Condition information is embedded inside the aggregate profile.

**Possible increments**:
- Add a `POST /v1/primary-directions/profile/condition` (or query parameter `view=condition`) that returns only the per-significator condition profiles.
- Expand the `PrimaryDirectionsSignificatorProfileResponse` to optionally include the full `relation_profiles` array (currently stubbed as future work).

#### 5. Convenience and Polish

Lower-priority but high-ergonomics items:
- Proper, consistent years computation across multiple keys on both arcs and relations (not just Naibod).
- Richer `most_connected` and `isolated` data on the network response, plus basic centrality or strength metrics if the engine provides them.
- Support for sending house cusps or custom points as significators/promissors in a clean way.
- Optional `include_fixed_stars`, `include_antiscia`, etc. flags that map to the corresponding policy target families (once those are admitted in the policy surface).

### Cross-Cutting Rules for All Phase 2 Work

- Every new capability must still be testable with the existing extreme hardening standards established in Phase 1 (parity, adversarial, boundary, empty-result handling).
- Policy growth must remain demand-driven. Do not model the entire `PrimaryDirectionsPolicy` just because it exists in the engine.
- New routes or major response expansions should be documented in an updated version of this document (or a Phase 2 companion note) before implementation begins.
- The "evaluate these arcs" pattern should be preferred over creating many new narrow-purpose endpoints.

### Out of Scope (Even for Phase 2)

- Full transport of the entire `PrimaryDirectionsPolicy` object.
- Support for every admitted method, space, and target family.
- Field-plane, neo-converse, midpoint directions, or other deferred frontiers.
- Asynchronous or heavy job-style endpoints for very large searches (those belong in a later phase or separate async surface).

---

This structure keeps Phase 2 focused, disciplined, and aligned with the original design philosophy while giving a clear roadmap for the next wave of useful capability.