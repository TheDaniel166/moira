## Moira Dispositorship Backend Standard

### Governing Principle

The Moira dispositorship backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Dispositorship Phase
12. It describes the subsystem that actually exists in `moira/dignities.py`; it
does not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core dispositorship computation

A **dispositorship profile** in Moira is:

> The authoritative chart-level result of
> `DignitiesService.calculate_dispositorship`, computed from sign placement plus
> explicit dispositorship policy, and returned as a deterministic collection of
> per-subject dispositorship chains with chart-level terminal summaries.

The computational core remains the authority for:

- subject admission into dispositorship scope
- sign-to-ruler lookup under the active rulership policy
- per-subject chain traversal
- termination classification
- unsupported-subject handling
- chart-level final-dispositor and cycle summaries

Later layers may preserve, classify, inspect, aggregate, or network this truth.
They may not recompute dispositorship doctrine independently.

#### 1.2 Dispositorship chain

A **dispositorship chain** in Moira is:

> The authoritative traversal result for one initial subject, recording sign,
> direct dispositorship links, in-scope status, terminal classification, visited
> subjects, and any terminal subjects or cycle members reached under the active
> policy.

`DispositorshipChain` is the per-subject truth vessel.

Its primary local truth fields are:

- `initial_subject`
- `initial_sign`
- `subject_in_scope`
- `subject_has_dispositor`
- `links`
- `visited_subjects`
- `termination_kind`
- `terminal_subjects`
- `cycle_members`

#### 1.3 Termination truth

A **termination kind** in Moira is:

> The authoritative answer to the question, "what happened when this
> dispositorship chain was followed under the active policy?"

The current primary termination classes are:

| Term | Definition |
|---|---|
| `FINAL_DISPOSITOR` | the chain terminates in a self-domiciled endpoint under the active rulership policy |
| `TERMINAL_CYCLE` | the chain terminates in a closed cycle, including mutual reception as the two-node special case |
| `UNRESOLVED` | the chain does not reach a final dispositor or terminal cycle under the active policy |

`multiple_roots` is not a primary termination kind in the current subsystem. If
root language is used later, it must be defined separately as a derived
component or chart-level summary metric.

#### 1.4 Unsupported subject handling

An **unsupported subject** in Moira dispositorship is:

> A chart body or named subject provided to the computation that falls outside
> the active subject policy.

The current public handling surface is explicit:

| Handling | Current behavior |
|---|---|
| `IGNORE` | preserve unsupported subjects in `unsupported_subjects` and append out-of-scope unresolved chains |
| `REJECT` | raise rather than computing a profile |
| `SEGREGATE` | preserve unsupported subjects in `unsupported_subjects` without appending out-of-scope chains |

#### 1.5 Local condition profile

A **dispositorship condition profile** in Moira is:

> A backend-only integrated local summary derived from one
> `DispositorshipChain`, preserving scope, traversal length, termination truth,
> and a local dispositorship state without recomputing doctrine.

The current local condition states are:

- `SELF_DISPOSED`
- `RESOLVED_TO_FINAL`
- `TERMINAL_CYCLE`
- `UNRESOLVED`
- `OUT_OF_SCOPE`

`DispositorshipConditionProfile` is a consumer of chain truth, not a second
dispositorship engine.

#### 1.6 Chart condition profile

A **dispositorship chart condition profile** in Moira is:

> A deterministic chart-wide aggregation of per-subject dispositorship
> condition profiles, reporting structural counts and mixed-terminal state
> without adding interpretation.

It currently includes at least:

- ordered per-subject condition profiles
- self-disposed, resolved, cycle, unresolved, and out-of-scope counts
- final-dispositor count
- cycle count
- mixed-terminal detection

#### 1.7 Network profile

A **dispositorship network profile** in Moira is:

> A deterministic directed graph projection over direct in-scope dispositorship
> relations and the existing condition profiles.

It currently includes at least:

- one node per in-scope condition profile
- one directed edge per direct first-step in-scope dispositorship relation
- unilateral vs reciprocal edge visibility
- incoming / outgoing / reciprocal counts per node
- isolated subjects
- direct-degree connectivity summaries

This is a structural backend layer only. It is not an interpretive network.

#### 1.8 Subsystem profile

A **dispositorship subsystem profile** in Moira is:

> The Phase 10 hardening bundle that ties the authoritative dispositorship
> profile, local condition profiles, chart condition profile, and network
> profile into one invariant-checked subsystem vessel.

`DispositorshipSubsystemProfile` exists to enforce cross-layer alignment. It
does not add new dispositorship doctrine.

#### 1.9 Comparative bundle

A **dispositorship comparison bundle** in Moira is:

> A higher-order aggregation over multiple explicitly named single-policy
> dispositorship profiles, preserving doctrine separation while reporting shared
> and union terminal summaries.

Comparison is a derived layer over separate doctrine-specific truths. It is not
a merged doctrine graph.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```
Core      - Authoritative dispositorship computation (`calculate_dispositorship`)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Relation formalisation
Phase  6  - Relation inspectability / hardening
Phase  7  - Integrated local dispositorship condition
Phase  8  - Chart-wide dispositorship intelligence
Phase  9  - Dispositorship network intelligence
Phase 10  - Full-subsystem hardening
Phase 11  - Architecture freeze / validation codex
```

#### Layer boundary rules

A layer above the core:

- may consume preserved truth from lower layers
- may classify or aggregate earlier truth
- may add invariant checks that reject internally inconsistent vessels
- may not recompute dispositorship doctrine independently
- may not mutate an earlier-layer vessel in place
- may not collapse policy-specific results into an ambient blended doctrine
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The dispositorship backend delegates to adjacent modules without redefining
them:

| Concern | Delegated to | Convention |
|---|---|---|
| zodiac sign ordering | `moira.constants.SIGNS` | ordered list of 12 sign names |
| sign derivation | existing dignity sign normalization in `moira/dignities.py` | normalized sign names derived from provided positions |
| classical planet order | `_PLANET_ORDER` in `moira/dignities.py` | deterministic dignity-consistent ordering |
| domicile rulership table | `DOMICILE` in `moira/dignities.py` | current traditional sign-ruler mapping |

Changes to those delegated sources propagate into the dispositorship subsystem.
This document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Subject doctrine

The current implemented subject doctrine is narrow and explicit:

- `DispositorshipSubjectSet.CLASSIC_7`

No broader subject family is implemented in the core dispositorship engine at
this time.

#### 4.2 Rulership doctrine

The current implemented rulership doctrine is narrow and explicit:

- `DispositorshipRulership.TRADITIONAL_DOMICILE`

No modern, hybrid, or dual-rulership computation is implemented in the core
dispositorship engine at this time.

#### 4.3 Basis doctrine

The current implemented dispositorship basis is:

- sign-based domicile rulership

Extended essential-dignity dispositorship is not implemented in the current
core.

#### 4.4 Termination doctrine

The current termination doctrine is:

- a final dispositor exists only when the chain reaches a self-domiciled
  terminal subject
- terminal cycles, including mutual receptions, are terminal cycles and not
  final dispositors
- unresolved chains remain unresolved under the active policy

#### 4.5 Unsupported-subject doctrine

Unsupported-subject handling is explicit through:

- `DispositorshipUnsupportedSubjectPolicy`
- `UnsupportedSubjectHandling`

The default handling is:

- `IGNORE`

#### 4.6 Ordering doctrine

The dispositorship backend currently has two ordering truths:

- `DispositorshipProfile` respects `DispositorshipOrderingPolicy`, including
  `use_dignity_order=False` for profile-level in-scope chain order and
  `final_dispositors` order
- `DispositorshipChartConditionProfile` and `DispositorshipNetworkProfile`
  currently freeze to deterministic dignity ordering over in-scope Classic 7
  subjects

This asymmetry is part of current implementation truth and is therefore frozen
here until explicitly revised.

---

### 5. Public Surface

The current curated dispositorship backend public surface is exposed from
`moira.dignities`.

#### 5.1 Classification enums

- `DispositorshipSubjectSet`
- `DispositorshipRulership`
- `DispositorshipTerminationKind`
- `UnsupportedSubjectHandling`
- `DispositorshipConditionState`
- `DispositorshipNetworkEdgeMode`

#### 5.2 Policy vessels

- `DispositorshipSubjectPolicy`
- `DispositorshipRulershipPolicy`
- `DispositorshipTerminationPolicy`
- `DispositorshipUnsupportedSubjectPolicy`
- `DispositorshipOrderingPolicy`
- `DispositorshipComputationPolicy`

#### 5.3 Result vessels

- `DispositorLink`
- `DispositorshipChain`
- `DispositorshipProfile`
- `DispositorshipConditionProfile`
- `DispositorshipChartConditionProfile`
- `DispositorshipNetworkNode`
- `DispositorshipNetworkEdge`
- `DispositorshipNetworkProfile`
- `DispositorshipSubsystemProfile`
- `DispositorshipComparisonItem`
- `DispositorshipComparisonBundle`

#### 5.4 Entry points

- `calculate_dispositorship`
- `calculate_dispositorship_condition_profiles`
- `calculate_dispositorship_chart_condition_profile`
- `calculate_dispositorship_network_profile`
- `calculate_dispositorship_subsystem_profile`
- `compare_dispositorship`

The curated `moira.dignities` export surface currently exposes 76 names in
total under the module API contract test. Dispositorship is one subsystem inside
that curated module surface; this document freezes only the dispositorship
portion.

---

### 6. Terminology and Failure Doctrine

#### 6.1 Terminology discipline

The following distinctions are mandatory in the current subsystem:

- a **termination kind** is per-subject traversal truth
- a **condition state** is a derived local classification over chain truth
- a **chart condition profile** is a chart-level aggregation over local
  condition profiles
- a **network profile** is a graph projection over direct dispositorship
  relations
- a **comparison bundle** preserves multiple doctrine-bounded results side by
  side

The subsystem must not use chart-shape language such as `multiple_roots` as a
primary sibling of `FINAL_DISPOSITOR`, `TERMINAL_CYCLE`, and `UNRESOLVED`
without an explicit future doctrine revision.

#### 6.2 Failure doctrine

The current dispositorship backend may fail by:

- rejecting invalid policy combinations during policy validation
- raising on unsupported subjects when `UnsupportedSubjectHandling.REJECT` is
  active
- raising when invariant-checked result vessels are internally inconsistent

It must not fail by silently changing doctrine or by silently admitting
unsupported subjects into in-scope computation.

---

### 7. Determinism Doctrine

The dispositorship backend is deterministic under fixed inputs and fixed policy.

Determinism currently requires:

- normalized subject naming
- explicit subject-set and rulership policy
- explicit unsupported-subject handling
- deterministic ordering of in-scope Classic 7 subjects
- deterministic terminal-cycle preservation
- deterministic comparison-bundle item order and first-appearance summary order

No ambient state or hidden doctrine switching is allowed.

---

## Part II - Validation Codex

### 8. Validation Environment

The authoritative runtime and validation environment is the project `.venv`.

The canonical targeted validation slice for the current dispositorship subsystem
is:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\unit\test_dignities_public_api.py .\tests\unit\test_moira_dignities_and_lots.py -q
```

No claim of dispositorship correctness or public-surface stability should be
made without validation in the project `.venv`.

### 9. Test Surface Register

The current dispositorship validation surface is primarily carried by:

- `tests/unit/test_dignities_public_api.py`
- `tests/unit/test_moira_dignities_and_lots.py`

Those tests currently cover at least:

- curated public API exposure
- classic-7 traditional domicile dispositorship computation
- final dispositor and cycle semantics
- unsupported-subject handling differences across `IGNORE`, `REJECT`, and
  `SEGREGATE`
- ordering-policy behavior at the profile level
- comparison-bundle behavior and bundle-level summary ordering
- local condition profile derivation
- chart condition profile aggregation
- network-profile structure
- cross-layer subsystem hardening invariants

### 10. Invariant Register

The dispositorship subsystem currently freezes these invariant families:

- `DispositorshipProfile`
  - in-scope chain order must follow the active profile ordering policy
  - `final_dispositors` must match final chain terminations under that policy
  - `terminal_cycles` must match unique cycle terminations

- `DispositorshipConditionProfile`
  - local state must match derived chain truth
  - `chain_length` must match `visited_subjects`
  - cycle terminations must keep `terminal_subjects` aligned with
    `cycle_members`

- `DispositorshipChartConditionProfile`
  - state counts must match aggregated profile states
  - final-dispositor and cycle counts must match profile terminals
  - `has_mixed_terminals` must match derived chart state
  - profiles must remain in deterministic dignity order

- `DispositorshipNetworkProfile`
  - nodes and edges must remain in deterministic dignity order
  - edge counts and reciprocal classifications must match derived edges
  - node degree fields must match the edge set
  - isolated and most-connected summaries must match node truth

- `DispositorshipSubsystemProfile`
  - condition profiles must align one-to-one with chains
  - chart profile must match condition profiles exactly
  - network nodes must align with in-scope condition profiles
  - network edges must match direct in-scope first-step dispositorship relations

### 11. Validation Doctrine

The smallest relevant validation should be preferred:

- targeted unit tests for public-surface or logic changes
- focused invariant checks through existing result vessels
- wider repository validation only when dispositorship changes expand into
  adjacent subsystems

Documentation-only changes to this standard do not require computational test
runs unless they claim new implementation truth.

### 12. Stable Public Semantics

Until explicitly revised, the following semantic commitments are frozen:

- Phase 1 dispositorship means classic-7, traditional domicile, sign-based
  dispositorship only
- final dispositors are self-domiciled endpoints only
- terminal cycles are not final dispositors
- unsupported-subject handling remains policy-explicit
- comparison preserves doctrine separation rather than merging doctrine graphs
- chart/network structural layers remain non-interpretive backend projections

Any future expansion into modern or dual-rulership families, extended
essential-dignity families, or additional subject families must be added as
explicit doctrine revisions rather than implied by this standard.

### 13. Public API Curation

Dispositorship Phase 12 is complete.

The stable constitutional surface is now publicly curated through the owning
`moira.dignities` module surface:

- dispositorship public names are explicitly exported through `moira.dignities.__all__`
- helper machinery remains internal and is excluded from the curated surface
- the curated module agreement is validated by
  `tests/unit/test_dignities_public_api.py`
- dispositorship behavior and invariant truth are validated by
  `tests/unit/test_moira_dignities_and_lots.py`

Phase 12 for this subsystem did not require widening the API. The public
surface already existed, was already curated, and was already under test. Phase
12 therefore consists of constitutional closure: explicitly freezing that
surface as the dispositorship subsystem's stable public boundary.
