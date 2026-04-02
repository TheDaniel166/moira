# Moira Subsystem Constitutional Process

## Governing Principle

The Moira Subsystem Constitutional Process is the canonical
method by which a computational subsystem is transformed into a governed backend
domain.

It is not a stylistic checklist. It is a directed sequence of epistemological
dependencies. Each phase becomes possible only because earlier phases have made
its claims knowable, testable, and stable.

This document is intended to be the first doctrine document in `moira/docs`
because it explains why the backend standards, validation codices, and public
API freezes exist, and why they were built in the order they were built.

---

## 1. Definition

A subsystem is **constitutionalized** when:

- its computational core is treated as authoritative
- the truth produced by that core is explicitly preserved
- that truth is typed, inspectable, and policy-bounded
- its relations and aggregates are derived rather than improvised
- its invariants and failure behavior are explicit
- its architecture and validation doctrine are frozen in writing
- its public API is deliberately curated

The output of constitutional process is not merely "working code." The output is a backend
subsystem with constitutional order.

---

## 2. Why This Process Exists

Moira does not treat backend maturity as "feature complete." It treats backend
maturity as the point at which:

- doctrine is explicit rather than hidden in control flow
- truth is preserved rather than flattened
- later layers do not need to reconstruct logic from strings
- invariants can be stated because the objects they govern are already real
- validation becomes constitutional rather than ad hoc

Without constitutional process, a subsystem can appear complete while remaining epistemically weak:
hard to inspect, easy to misuse, difficult to validate, and impossible to freeze
without ambiguity.

---

## 3. Core Thesis

The constitutional phase order is not arbitrary.

It is a **directed acyclic graph of epistemological dependencies expressed as a
phase sequence**.

This means:

- a later phase may consume earlier truth
- a later phase may formalize or constrain earlier truth
- a later phase may not invent the preconditions it depends on

Examples:

- Phase 11 cannot be meaningful until Phase 10 has frozen the invariants and
  failure behavior it is documenting.
- Phase 10 cannot be completed until cross-layer consistency exists across the
  reception, condition, chart-wide, and network layers built in Phases 6-9.
- Phase 8 cannot exist until Phase 7 has already produced integrated
  per-planet condition profiles.
- Phase 7 cannot exist until the prior layers have already preserved,
  classified, and formalized the local truths it integrates.

The sequence is linear in execution, but the reason for the sequence is the DAG
of dependency beneath it.

---

## 4. Constitutional Vocabulary

The following terms are normative in constitutional process:

| Term | Meaning |
|---|---|
| computational core | the authoritative engine that performs the actual domain computation |
| truth preservation | additive preservation of doctrinal/computational facts already computed by the core |
| classification | typed descriptive structure over preserved truth |
| inspectability | derived convenience access that exposes already-known truth more clearly |
| policy | explicit control over admitted doctrine already supported by the engine |
| formalization | turning implicit relational logic into explicit result vessels |
| integration | combining existing local truths into a coherent higher-order profile |
| aggregate intelligence | chart-wide or subsystem-wide summaries derived from local integrated truth |
| network intelligence | structural graph projection over already-formalized relations |
| hardening | explicit invariants, failure behavior, determinism, and misuse resistance |
| constitution | the written backend standard and validation codex that freezes the subsystem |
| public API curation | deliberate exposure of the stable surface while keeping helpers internal |

---

## 5. The Phase Graph

constitutional process currently consists of twelve phases.

### Phase 1 - Truth Preservation

Purpose:
Preserve richer doctrinal and computational truth from the authoritative core
without changing semantics.

Dependency:
Requires a real computational core to already exist.

Without it:
Later layers must reconstruct hidden logic from flattened labels or scores.

### Phase 2 - Classification

Purpose:
Add typed descriptive structure to preserved truth.

Dependency:
Requires structured truth to already exist.

Without it:
Classification would either be lossy, invented, or forced to classify legacy
flattened outputs directly.

### Phase 3 - Inspectability

Purpose:
Expose derived convenience views and harden vessel consistency.

Dependency:
Requires preserved truth and classification to already exist.

Without it:
Inspectability helpers either duplicate logic or expose unstable half-formed
concepts.

### Phase 4 - Doctrine / Policy Surface

Purpose:
Make doctrinal choices explicit and governable without changing default
behavior.

Dependency:
Requires the existing doctrine to be observable in preserved truth and
classification.

Without it:
Policy becomes speculative and disconnected from the engine it claims to govern.

### Phase 5 - Relational Formalization

Purpose:
Turn previously implicit relational logic into explicit backend result vessels.

Dependency:
Requires policy-bounded local truth to already exist.

Without it:
Relations are inferred ad hoc instead of derived from authoritative doctrine.

### Phase 6 - Relational Hardening / Inspectability

Purpose:
Harden the newly formalized relation layer and distinguish detected, admitted,
and scored subsets explicitly.

Dependency:
Requires a formal relation layer to already exist.

Without it:
Cross-layer consistency involving relations cannot be stated clearly.

### Phase 7 - Integrated Local Condition

Purpose:
Integrate per-entity truth into a coherent local condition profile.

Dependency:
Requires preserved, classified, inspectable, policy-bounded, and relation-aware
local truth.

Without it:
Any higher-order condition layer is forced to recompute doctrine or skip
important dimensions.

### Phase 8 - Aggregate Intelligence

Purpose:
Build chart-wide or subsystem-wide structural intelligence from integrated local
profiles.

Dependency:
Requires Phase 7.

Without it:
Aggregate intelligence has no authoritative local unit to aggregate.

### Phase 9 - Network Intelligence

Purpose:
Project relation and condition truth into a structural network.

Dependency:
Requires formalized relations and integrated local profiles, and therefore
depends on Phases 5-8.

Without it:
Network summaries are disconnected from the condition model and become a second
independent system.

### Phase 10 - Full-Subsystem Hardening

Purpose:
Freeze cross-layer invariants, deterministic ordering, failure behavior, and
misuse resistance across the whole subsystem.

Dependency:
Requires the major layers to already exist, especially the relation,
integration, aggregate, and network layers.

Without it:
There is no full subsystem to harden, only isolated components.

### Phase 11 - Architecture Freeze and Validation Codex

Purpose:
Write the formal backend standard and validation doctrine for the subsystem as
it actually exists.

Dependency:
Requires the subsystem invariants, terminology, boundaries, and failure
behavior to already be explicit.

Without it:
The standard would be aspirational prose rather than a constitutional document.

### Phase 12 - Public API Curation

Purpose:
Expose the stable constitutional surface publicly and keep helpers internal.

Dependency:
Requires the subsystem's stable constitutional surface to already be known.

Without it:
The package exports leak implementation detail because stability has not yet
been established.

---

## 6. Dependency Doctrine

The constitutional dependency rule is:

> A phase may only formalize, aggregate, freeze, or expose truths that have
> already become explicit in earlier phases.

Corollaries:

- No phase may rely on hidden doctrine.
- No phase may use a later abstraction to justify an earlier design.
- No standard document may freeze semantics that have not yet been hardened.
- No public API should expose a surface whose invariants are not yet known.

This is why the process is constitutional rather than incremental. It is not
just adding capabilities. It is making each layer legitimate before the next
layer is allowed to exist.

---

## 7. Why Phase 11 Must Follow Phase 10

Phase 11 is not "write the docs."

Phase 11 is:

> write the constitution of a subsystem whose constitutional facts are already
> explicit

That requires at least:

- frozen terminology
- explicit boundaries
- stated invariants
- deterministic ordering guarantees
- consistent failure doctrine
- cross-layer agreement

If those are not already real in code and tests, then the backend standard is
not a constitution. It is only an intention.

---

## 8. Why Phase 12 Must Follow Phase 11

Phase 12 is not merely "export more names."

It is:

> expose the stable constitutional surface after the subsystem has already
> declared what is stable, what is internal, and what guarantees attach to the
> public surface

This is why public API curation belongs at the end of the process rather than
near the beginning.

---

## 9. Constitutional Deliverables

When constitutional process is correctly completed for a subsystem, the repository should contain:

- the hardened subsystem implementation
- focused tests proving semantic preservation and invariant behavior
- a backend standard document
- a validation codex within that standard
- a curated package-level public surface

The backend standard is not supplemental. It is a deliverable of the process.

---

## 10. Repository Placement Doctrine

`00_SUBSYSTEM_CONSTITUTIONALIZATION_PROCESS.md` belongs at the top of
`moira/docs` because it explains the governing logic under which the subsystem
standards were produced.

The order is intentional:

1. constitutional process
2. subsystem constitutions such as houses, aspects, parans, dignities
3. validation reports
4. roadmap and domain-specific research/model notes

Validation reports show that the code works.

This process explains how Moira decides what it means for a backend subsystem to become
constitutional in the first place.

---

## 11. Applicability

This process is the default doctrine for any Moira backend subsystem that:

- has a real computational core
- is expected to become stable and reusable
- benefits from explicit doctrine, invariants, and validation

It is especially applicable to subsystems that evolve from:

- single-function calculations
- flattened result payloads
- implicit doctrinal choices
- ad hoc helper growth

into:

- layered result vessels
- policy-bounded computation
- deterministic aggregates
- constitutional public APIs

---

## 12. Freeze Rule

Any future backend subsystem standard should be interpretable as an instance of
this process unless explicitly declared otherwise.

Any future Moira subsystem that departs materially from this process should
state:

- why this process does not apply
- which dependency rule is being changed
- what replaces the constitutional guarantees this process would normally require

Absent such a declaration, this process is the default constitutional doctrine of backend
development in Moira.

