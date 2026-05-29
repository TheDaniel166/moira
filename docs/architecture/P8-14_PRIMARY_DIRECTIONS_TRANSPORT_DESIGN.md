# P8-14 Primary Directions – Complete Transport Design & Roadmap

**Document Status:** Authoritative design for P8-14 implementation  
**Version:** 1.0  
**Date:** 2026-05  
**Owner:** Design agreed with repository author

## 1. Purpose and Scope

This document defines the complete, phased plan for exposing Moira’s primary directions engine through the REST server (`moira_server`).

It replaces earlier first-pass notes and serves as the single source of truth for all future work on P8-14.

**Goal**: Deliver a production-grade, maintainable, and evolvable transport surface over one of the richest and most complex subsystems in the engine, while strictly following Moira Server architectural principles.

## 2. Core Design Principles (Non-Negotiable)

These principles govern every decision in this document and all future increments:

1. **Strong Default First, Richness on Demand**  
   The transport layer always presents a coherent, safe, well-documented default experience. Additional policy controls, target families, and evaluation modes are added only when real usage demonstrates the need.

2. **Preserve Layered Doctrine**  
   The engine’s explicit layering (SpeculumEntry → PrimaryArc → Relation → RelationProfile → SignificatorProfile → Aggregate → Network) must remain visible and usable in the transport models. Do not collapse layers for convenience.

3. **Server is Transport Only**  
   No doctrine is invented or simplified in the server layer. All computational truth comes from the engine. The server’s job is honest serialization, convenient workflows, and clear error mapping.

4. **Demand-Driven Policy Growth**  
   The `PrimaryDirectionsPolicy` object in the engine is extremely rich and contains many interdependent invariants. The transport surface must grow this capability incrementally and safely.

5. **Extreme Hardening is Table Stakes**  
   Every increment must meet the same verification standard established in Phase 1: parity, adversarial, boundary (no kernel mutation), empty-result handling, and structural validation.

6. **Sustainable Evolution**  
   Designs must remain maintainable as the engine itself continues to evolve. Avoid freezing large, complex policy models too early.

## 3. Current State (Phase 1 – Complete & Hardened; Phase 2 Relation Depth started)

**Phase 1 Status**: Fully implemented and extremely hardened (18/18 tests passing).

**Phase 2 Progress** (as of latest work):
- **Relation Depth Expansion** (Priority #1) is now partially live.
- Re-evaluation ("submitted arcs") and basic policy presets implemented and hardened.
- **Condition Surface** (user-prioritized Phase 3 item): completed (28/28 at the time).
- Subsequent Option A increment (user-directed after evaluation of remaining Phase 2 items):
  - All three listed items (deeper presets, method/space exposure, richer time-key) were assessed as already substantially present at the Phase 2 "first controlled expansion" level.
  - The chosen minimal justified increment was Combined Policy Surface Hardening + Ergonomic Key Polish.
  - Router now supplies conventional keys for all seven shipped presets.
  - New adversarial coverage added; two complex combined paths documented as still capable of 422 (honest outcome after hardening attempt).
  - Final suite: 30/30 clean under `.venv`. Phase 2 policy/relations/condition band now has clearer closure documentation.

**Implemented and verified:**

- Four core route groups:
  - `POST /v1/primary-directions/speculum`
  - `POST /v1/primary-directions/arcs`
  - `POST /v1/primary-directions/profile`
  - `POST /v1/primary-directions/network`

- Narrow first-pass policy surface (method, space, include_converse, basic key selection).
- Strong default policy (Placidian mundane + traditional converse).
- Clean empty-result handling (always 200 with valid empty structures).
- Full extreme hardening test suite (18 tests, all passing as of last verified run).
- Consistent direction/motion normalization ("DIRECT" / "CONVERSE").

**Explicit limitations accepted in Phase 1:**
- No "evaluate these pre-computed arcs" capability.
- Very limited policy controls.
- No advanced target families.
- Relation depth is minimal.
- Time-key support is basic (primarily Naibod years).

## 4. Phased Roadmap

### Phase 2 – Relation Fidelity + Re-evaluation Capability

**Primary Goal**: Make the existing route groups significantly more powerful without adding many new top-level paths.

**Priority Order**

#### 2.1 Relation Depth
- Expose full `PrimaryDirectionRelationProfile` (including `admitted_relations` and `scored_relations`).
- Add support for `relate_primary_arc` and `evaluate_primary_direction_relations`.
- Expand `PrimaryDirectionRelationProfileResponse` and wire it into the `/profile` responses (initially opt-in via `include_relations=true`).

#### 2.2 Re-evaluation / Arc Submission
- Add support for clients to submit a list of arcs directly to `/profile` and `/network`.
- When the `arcs` array is present in the request body, skip arc discovery and evaluate the submitted arcs.
- Add a lightweight dedicated endpoint if needed: `POST /v1/primary-directions/relations`.

#### 2.3 Policy Surface – First Controlled Expansion
- Add time-key selection (Ptolemy, Naibod, Cardan, Solar) as a first-class field.
- Introduce a small number of named presets (e.g. `"placidian_mundane"`, `"ptolemy_semiarc"`).
- Begin exposing basic target family controls (fixed stars, antiscia) behind explicit flags.

**Exit Criteria for Phase 2**
- Clients can discover arcs once and then re-evaluate them under different (still-limited) policies.
- Full admitted/scored relation information is available.
- All new capability meets the extreme hardening standard.

### Phase 3 – Condition Surfaces + Policy Maturity

**Focus Areas**
- Dedicated access to `evaluate_primary_direction_condition` (rich per-significator condition profiles).
- Further policy growth (latitude policy, relation policy, more methods).
- Consistent, high-quality years computation across all keys on both arcs and relations.
- Richer network metadata (most_connected, isolated, basic strength/centrality metrics).

### Phase 4 – Advanced Target Families & Full Method Support

- Systematic support for the remaining admitted target families and methods.
- Full (or near-full) transport of the policy surface, now that usage patterns are well understood.
- Optional advanced evaluation modes (different policies per evaluation, etc.).

### Phase 5 – Polish, Presets, and Long-Term Stability

- Named branch presets as first-class, documented conveniences.
- Mature error surfaces and validation for policy combinations.
- Performance and payload optimizations for heavy responses.
- Clear deprecation and evolution strategy for the transport models.

## 5. Detailed Design Decisions (Locked)

### 5.1 Policy Strategy (Applies to All Phases)

- Always start from a strong, safe default.
- New policy fields are added only when justified by usage.
- Every new policy dimension must include clear validation and helpful error messages.
- Named presets are the preferred way to offer complex but common configurations.

### 5.2 "Evaluate These Arcs" Pattern

This is the preferred mechanism for re-evaluation.  
Preferred implementation order:
1. Add an `arcs` array to the existing `/profile` and `/network` request bodies (Phase 2).
2. Add a dedicated lightweight relations endpoint if the above becomes cumbersome.

### 5.3 Direction & Motion Strings

All responses must normalize to the uppercase full forms:
- `direction`: `"DIRECT"` or `"CONVERSE"`
- `motion`: `"DIRECT"` or `"CONVERSE"`

The serializer layer is responsible for normalization.

### 5.4 Empty and Edge Result Handling

All routes must return HTTP 200 with structurally valid (even if empty) response bodies when no results are found.  
Never return 422 or 500 for legitimate "no arcs matched" scenarios.

### 5.5 Time Keys

Phase 1 exposes Naibod years by default.  
Phase 2 introduces explicit time-key selection on arcs and relations.  
All four currently admitted static/symbolic keys (Ptolemy, Naibod, Cardan, Solar) must be supported.

### 5.6 Versioning & Evolution

- New fields may be added to existing response models.
- New optional request fields are acceptable.
- Breaking changes to existing fields require a new API version (`/v2/...`).
- Named presets provide a stable way to evolve complex policy combinations without breaking clients.

## 6. Verification & Hardening Standard (Applies to Every Increment)

Every piece of work on P8-14 must satisfy:

- Parity tests against direct engine calls.
- Adversarial tests (invalid latitudes, contradictory policy, bad bodies, extreme arc windows, etc.).
- Explicit boundary tests proving zero kernel lifecycle mutation.
- Empty-result and edge-case handling (always 200 + valid structure).
- Structural validation of doctrinal fields (method, space, motion, relation_kind, key, etc.).
- Full application startup verification after changes.

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|----------|
| Policy invariants are complex and easy to violate in transport | Demand-driven growth + strong validation + named presets |
| Large response payloads (especially network + full relation profiles) | Optional expansion flags (`include_relations`, `include_condition`, etc.) |
| Clients expect exact parity with raw engine calls | Clear documentation of first-pass limitations + phased roadmap |
| Future engine changes break transport assumptions | Maintain thin service layer + comprehensive parity tests |

## 8. Open Questions (to be resolved before starting each increment)

- Exact shape and naming of the "evaluate these arcs" request field.
- When (and whether) to introduce a dedicated `/relations` endpoint.
- Prioritization order between deeper relation profiles vs. time-key selection vs. first named presets.
- Whether to support per-arc policy overrides in Phase 2 or defer to Phase 3.

These should be closed with the repository author before implementation of the relevant increment begins.

---

**This document is now the complete, interruption-free guide for all future P8-14 work.**

Phase 1 is complete and hardened.  
All subsequent work should be planned and executed against the roadmap and principles defined above.