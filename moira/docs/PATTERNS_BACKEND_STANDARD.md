## Moira Patterns Backend Standard

### Governing Principle

The Moira patterns backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Patterns Phase 11. It
describes the subsystem that actually exists in `moira/patterns.py`; it does
not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core pattern computation

An **aspect pattern** in Moira is:

> The authoritative result of one of the pattern detectors in
> `moira.patterns`, or of `find_all_patterns`, computed from admitted
> `AspectData` relations and, for Stellium, position clustering doctrine.

The computational core remains the authority for:

- detector admission
- orb arithmetic
- aspect-map lookup
- body ordering inside each detected pattern
- stellium centroid and spread arithmetic
- duplicate suppression

Later layers may preserve, classify, inspect, aggregate, or network this
truth. They may not recompute pattern doctrine independently.

#### 1.2 Pattern vessel

An **AspectPattern** in Moira is:

> The canonical per-pattern result vessel representing one detected
> multi-body configuration, including its pattern name, bodies, contributing
> aspects, optional apex, preserved truth, classifications, contribution
> relations, and derived condition profile.

`AspectPattern` is the authoritative local truth vessel for this subsystem.

#### 1.3 Detection truth

A **pattern detection truth** in Moira is:

> The preserved doctrinal and computational path describing which detector
> matched, whether the pattern was aspect- or position-driven, and which body
> roles the detector assigned.

This truth is carried by `AspectPattern.detection_truth`. It is descriptive
only. It does not alter detector semantics.

#### 1.4 Contribution

A **pattern contribution** in Moira is:

> One formal relational record describing how an admitted aspect participates
> inside one detected pattern.

The contribution layer distinguishes:

| Term | Definition |
|---|---|
| `all_contributions` | full preserved contribution surface for the pattern |
| `contributions` | the currently admitted contribution subset |
| `pattern_contributions(...)` | flattened admitted contribution view |
| `all_pattern_contributions(...)` | flattened full preserved contribution view |

Under the current default doctrine, `contributions == all_contributions`.

#### 1.5 Pattern condition profile

A **pattern condition profile** in Moira is:

> A backend-only integrated structural summary derived from one
> `AspectPattern`, combining classification and contribution structure into one
> per-pattern condition vessel.

`PatternConditionProfile` is derived only from lower-layer truth. It is not a
second pattern engine.

#### 1.6 Pattern chart condition profile

A **pattern chart condition profile** in Moira is:

> A deterministic chart-wide aggregation of per-pattern condition profiles,
> reporting structural counts, contribution totals, and strongest / weakest
> pattern summaries under the currently embodied ranking.

#### 1.7 Pattern condition network profile

A **pattern condition network profile** in Moira is:

> A deterministic graph projection over detected pattern instances and their
> participating bodies, derived from existing pattern and condition truth.

It includes at least:

- one node per detected pattern instance
- one node per participating body
- one directed edge per pattern-to-body participation link
- incoming / outgoing / total degree counts per node
- isolated bodies
- direct-degree connectivity summaries

This is a structural backend layer only. It is not interpretation.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```
Core      - Authoritative pattern computation (`find_all_patterns`)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Contribution formalisation
Phase  6  - Contribution inspectability / hardening
Phase  7  - Integrated per-pattern condition
Phase  8  - Chart-wide condition intelligence
Phase  9  - Pattern / condition network intelligence
Phase 10  - Full-subsystem hardening
Phase 11  - Architecture freeze / validation codex
```

#### Layer boundary rules

A layer above the core:

- may consume preserved truth from lower layers
- may classify or aggregate earlier truth
- may add invariant checks that reject internally inconsistent vessels
- may not recompute detector doctrine independently
- may not alter legacy pattern admission semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The patterns backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| aspect computation | `moira.aspects.find_aspects` | returns admitted `AspectData` instances |
| aspect vessel truth | `moira.aspects.AspectData` | authoritative aspect endpoint / angle / orb data |
| circular distance arithmetic | `moira.coordinates.angular_distance` | authoritative angular-separation helper |

Changes to those delegated sources propagate into the patterns subsystem. This
document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Detector doctrine

Pattern doctrine begins with the detector set embodied in `moira/patterns.py`.
The current subsystem includes:

- classical and mainstream pattern detectors
- extended geometric / Huber-recognized detectors already implemented
- harmonic 5th- and 7th-harmonic detectors already implemented
- stellium position clustering doctrine

No additional detector doctrine is implied by this document.

#### 4.2 Orb doctrine

Pattern orb doctrine is embodied by:

- detector-specific fixed base orbs
- the caller-visible `orb_factor`
- current Stellium `orb` and `min_bodies` doctrine

The default policy preserves historical behavior exactly.

#### 4.3 Policy doctrine

`PatternComputationPolicy` makes current doctrine explicit without changing the
default result.

| Policy area | Type | Current default |
|---|---|---|
| named detector selection | `PatternSelectionPolicy` | all registered patterns admitted |
| Stellium doctrine | `StelliumPolicy` | `min_bodies=3`, `orb=8.0` |
| global orb scaling | `PatternComputationPolicy.orb_factor` | `1.0` |

The normative default is:

> `PatternComputationPolicy()` must preserve the current historical subsystem
> behavior exactly.

---

### 5. Classification

`PatternClassification` is descriptive only. It classifies:

- source kind
- symmetry kind
- body count
- apex presence
- typed body roles

`PatternAspectRoleKind` classifies contribution roles descriptively only.

Classification describes preserved truth. It does not affect detector
admission, orb arithmetic, or pattern semantics.

---

### 6. Inspectability

`AspectPattern` exposes derived inspectability helpers so callers do not need
to reconstruct structure from nested truth:

- `detector`
- `source_kind`
- `symmetry_kind`
- `body_role_kinds`
- `is_position_based`
- `is_apex_bearing`
- `contribution_roles`
- `admitted_contributions`
- `all_contribution_roles`
- `contribution_count`
- `all_contribution_count`
- `has_contributions`
- `condition_state`

The chart and network layers also expose small derived inspectability helpers:

- `PatternChartConditionProfile.profile_count`
- `PatternChartConditionProfile.strongest_count`
- `PatternChartConditionProfile.weakest_count`
- `PatternConditionNetworkProfile.node_count`
- `PatternConditionNetworkProfile.edge_count`

These properties are derived only. They do not change doctrine.

---

### 7. Failure Doctrine

#### 7.1 Input failure behavior

Malformed raw inputs must fail clearly and deterministically before pattern
computation proceeds.

Current explicit failures include:

- empty body names in `positions`
- non-finite position longitudes
- malformed aspect endpoints
- self-aspects in supplied `aspects`
- non-finite aspect angles or orbs
- negative aspect orbs
- invalid `min_bodies`
- invalid Stellium orb values
- invalid global `orb_factor`
- malformed policy objects
- repeated selection names
- unsupported selection names

#### 7.2 Internal inconsistency behavior

If a vessel is constructed with internally inconsistent truth, classification,
contribution, condition, chart, or network state, it must fail loudly with
`ValueError`.

Silent internal drift is prohibited.

---

### 8. Determinism Guarantees

For identical validated inputs and policy, the subsystem guarantees:

- deterministic pattern inclusion / omission
- deterministic pattern ordering
- deterministic body-role preservation
- deterministic contribution ordering
- deterministic condition-profile ordering
- deterministic chart strongest / weakest summaries
- deterministic network node ordering
- deterministic network edge ordering
- deterministic isolated / most-connected summaries

No public result vessel may depend on hash order or incidental iteration order.

---

## Part II - Invariant Register

### 9. Vessel Invariants

The following invariants are normative.

#### 9.1 `PatternDetectionTruth`

- `source_kind` must be one of the currently supported detector sources
- `body_roles` must not be empty
- `body_roles` must not repeat bodies
- position-based truth must preserve centroid, spread, and orb limit

#### 9.2 `PatternClassification`

- `body_count` must match `body_roles`
- `body_roles` must not repeat bodies
- `has_apex` must agree with body roles

#### 9.3 `PatternAspectContribution`

- contribution endpoints must differ
- contribution endpoints must match the bound aspect endpoints
- `aspect_name` must match `aspect.aspect`
- `aspect_angle` must match `aspect.angle`

#### 9.4 `PatternConditionProfile`

- `body_count` must be positive
- contribution counts must be non-negative
- `contribution_count` must not exceed `all_contribution_count`
- structured and generic counts must cover `all_contributions`
- `has_apex` must match `symmetry`
- `state` must match the derived contribution structure

#### 9.5 `AspectPattern`

- `bodies` must not be empty
- `apex`, when present, must be one of the bodies
- preserved truth must agree with the pattern name and body set
- classification must agree with preserved truth
- `all_contributions` must match pattern aspects exactly
- `contributions` must be a subset of `all_contributions`
- under the current doctrine, `contributions` must match `all_contributions`
- contribution relations must not repeat the same aspect relation
- `condition_profile` must agree with classification and contribution truth

#### 9.6 `PatternChartConditionProfile`

- state counts must match profile states
- contribution totals must match profile totals
- `profiles` must be in deterministic order
- `strongest_patterns` must match the derived strongest ranking
- `weakest_patterns` must match the derived weakest ranking

#### 9.7 `PatternConditionNetworkNode`

- kind must be one of the currently supported node kinds
- total degree must equal incoming plus outgoing degree

#### 9.8 `PatternConditionNetworkEdge`

- source and target ids must differ

#### 9.9 `PatternConditionNetworkProfile`

- nodes must be in deterministic order
- edges must be in deterministic order
- node ids must be unique
- edges must reference existing nodes
- node incoming and outgoing counts must match the edges
- `isolated_bodies` must match body nodes with zero degree
- `most_connected_nodes` must match the highest total degree

---

## Part III - Public Surface and Validation Codex

### 10. Stable Public Surface

The stable patterns backend surface is the combination of:

- result vessels:
  - `AspectPattern`
  - `PatternBodyRoleTruth`
  - `PatternDetectionTruth`
  - `PatternBodyRoleClassification`
  - `PatternClassification`
  - `PatternAspectContribution`
  - `PatternConditionProfile`
  - `PatternChartConditionProfile`
  - `PatternConditionNetworkNode`
  - `PatternConditionNetworkEdge`
  - `PatternConditionNetworkProfile`
- enums:
  - `PatternSourceKind`
  - `PatternSymmetryKind`
  - `PatternBodyRoleKind`
  - `PatternAspectRoleKind`
  - `PatternConditionState`
- policy types:
  - `PatternSelectionPolicy`
  - `StelliumPolicy`
  - `PatternComputationPolicy`
- module entrypoints:
  - `find_all_patterns`
  - `find_stelliums`
  - `pattern_contributions`
  - `all_pattern_contributions`
  - `pattern_condition_profiles`
  - `pattern_chart_condition_profile`
  - `pattern_condition_network_profile`

Internal helpers remain implementation detail unless explicitly exported later.

---

### 11. Minimum Validation Codex

Any substantive change to `moira/patterns.py` must, at minimum, preserve:

1. detector admission and pattern semantics
2. structured truth consistency
3. classification consistency
4. contribution consistency
5. condition-profile consistency
6. chart-profile consistency
7. network consistency
8. deterministic failure behavior

Minimum validation commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_patterns.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_aspects.py -q -k "find_patterns or public_api"
.\.venv\Scripts\python.exe -m py_compile moira\patterns.py tests\unit\test_patterns.py
```

If the public package surface changes later, the matching API-freeze test must
also be included in the minimum validation set.

---

### 12. Non-Goals Frozen By This Standard

The current patterns backend does **not** include:

- interpretation of pattern meaning
- recommendation or judgment logic
- chart-wide interpretive synthesis
- UI or rendering concerns
- probabilistic confidence scoring
- pattern-to-pattern doctrinal inference beyond the current structural layers

Those concerns belong to later layers or different subsystems. They are not
part of the current constitutional backend.
