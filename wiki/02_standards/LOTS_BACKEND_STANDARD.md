## Moira Lots Backend Standard

### Governing Principle

The Moira lots backend is a sovereign computational subsystem. Its definitions,
layer boundaries, terminology, invariants, failure doctrine, and determinism
rules are stated here and are frozen until explicitly superseded by a revision
to this document.

This document reflects current implementation truth as of Lots Phase 11. It
describes the subsystem that actually exists in `moira/lots.py`; it does not
describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core lot computation

An **Arabic Part** in Moira is:

> The authoritative result of `ArabicPartsService.calculate_parts`, computed
> from the doctrinal formula `Asc + Add - Subtract (mod 360)` after reference
> resolution and day/night reversal where the catalogue definition requires it.

The computational core remains the authority for:

- lot longitude
- effective formula operands
- day/night reversal behavior
- reference resolution
- lot admission or omission under the current policy

Later layers may preserve, classify, inspect, aggregate, or network this truth.
They may not recompute lot doctrine independently.

#### 1.2 Part definition

A **part definition** in Moira is:

> One immutable doctrinal catalogue entry represented by `PartDefinition`,
> declaring the lot name, day operands, reversal rule, category string, and
> optional description.

`PARTS_DEFINITIONS` is the authoritative lot catalogue.

#### 1.3 Computation truth

An **Arabic part computation truth** in Moira is:

> The preserved doctrinal and computational path that records which operand
> keys were requested, which keys actually resolved, whether reversal applied,
> and which structured references were used for the returned longitude.

This truth is carried by `ArabicPart.computation_truth`. It is descriptive
only. It does not change the formula or result.

#### 1.4 Dependency

A **lot dependency** in Moira is:

> One formal operand relation derived from preserved computation truth,
> expressing whether a lot depends on a given add or subtract operand and how
> that operand was resolved.

The dependency layer distinguishes:

| Term | Definition |
|---|---|
| `all_dependencies` | all doctrinal operand dependencies preserved on the lot |
| `dependencies` | the currently admitted dependency subset |
| `inter_lot_dependencies` | admitted dependencies whose reference kind is `DERIVED_LOT` |
| `external_dependencies` | admitted dependencies whose reference kind is `EXTERNAL` |

Under the current default policy, `dependencies == all_dependencies`.

#### 1.5 Lot condition profile

A **lot condition profile** in Moira is:

> A backend-only integrated structural summary derived from one `ArabicPart`,
> combining lot category, reversal state, and dependency composition into a
> single per-lot condition vessel.

`LotConditionProfile` is derived only from lower-layer truth. It is not a
second lot engine.

#### 1.6 Chart condition profile

A **lot chart condition profile** in Moira is:

> A deterministic chart-wide aggregation of per-lot condition profiles,
> reporting structural counts, dependency totals, and strongest / weakest lots
> under the currently embodied ranking.

#### 1.7 Lot condition network profile

A **lot condition network profile** in Moira is:

> A deterministic directed graph projection over admitted inter-lot dependency
> truth and the existing per-lot condition profiles.

It includes at least:

- one node per computed lot profile
- one directed edge per admitted inter-lot dependency
- unilateral vs reciprocal edge visibility
- incoming / outgoing / reciprocal counts per node
- isolated lots
- direct-degree connectivity summaries

This is a structural backend layer only. It is not an interpretive network.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```
Core      - Authoritative lot computation (`calculate_parts`)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Dependency formalisation
Phase  6  - Dependency inspectability / hardening
Phase  7  - Integrated per-lot condition
Phase  8  - Chart-wide condition intelligence
Phase  9  - Dependency / condition network intelligence
Phase 10  - Full-subsystem hardening
Phase 11  - Architecture freeze / validation codex
```

#### Layer boundary rules

A layer above the core:

- may consume preserved truth from lower layers
- may classify or aggregate earlier truth
- may add invariant checks that reject internally inconsistent vessels
- may not recompute lot doctrine independently
- may not alter legacy lot longitude or formula semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The lots backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| zodiac sign ordering | `moira.constants.SIGNS` | ordered list of 12 sign names |
| sign derivation | `moira.constants.sign_of` | returns sign name, glyph, and in-sign degree |
| chart access | `moira.chart.ChartContext` | exposes planet longitudes, nodes, houses, and day-chart state |

Changes to those delegated sources propagate into the lots subsystem. This
document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Catalogue doctrine

Lot doctrine begins with `PARTS_DEFINITIONS`. Each lot’s:

- `day_add`
- `day_sub`
- `reverse_at_night`
- `category`

is authoritative unless the catalogue itself is revised.

#### 4.2 Reference doctrine

The current engine supports the following reference classes where resolvable:

- direct planets and chart nodes
- angles (`Asc`, `Dsc`, `MC`, `IC`)
- house cusps (`H1` ... `H12`)
- house rulers (`Ruler H1` ... `Ruler H12`)
- angle-ruler aliases
- planet-sign rulers (`Ruler Sun`, etc.)
- fixed-degree constants
- optional externals (`Syzygy`, prenatal lunations, `Lord of Hour`)
- derived lots currently embodied in the engine:
  - `Fortune`
  - `Spirit`
  - `Eros (Valens)`

No additional reference doctrine is implied by this document.

#### 4.3 Reversal doctrine

Day/night reversal doctrine is embodied directly by each `PartDefinition`’s
`reverse_at_night` field. Reversal applies only when:

- `reverse_at_night` is `True`
- the chart is not a day chart

#### 4.4 Policy doctrine

`LotsComputationPolicy` makes current doctrine explicit without changing the
default result.

| Policy area | Type | Current default |
|---|---|---|
| unresolved reference handling | `LotsReferenceFailureMode` | `SKIP` |
| derived-lot admissibility | `LotsDerivedReferencePolicy` | all supported derived lots enabled |
| external-reference admissibility | `LotsExternalReferencePolicy` | all supported external references enabled |

The normative default is:

> `LotsComputationPolicy()` must preserve the current historical subsystem
> behavior exactly.

---

### 5. Classification

`ArabicPartClassification` is descriptive only. It classifies:

- deterministic category tags
- deterministic primary category
- reversal state
- add-reference kind
- sub-reference kind

Classification describes preserved truth. It does not affect lot longitude,
formula semantics, or admission logic.

---

### 6. Inspectability

`ArabicPart` exposes derived inspectability helpers so callers do not need to
reconstruct structure from nested truth:

- `category_tags`
- `primary_category`
- `reversal_kind`
- `is_reversed`
- `add_reference_kind`
- `sub_reference_kind`
- `dependency_count`
- `all_dependency_count`
- `inter_lot_dependencies`
- `external_dependencies`
- `condition_state`

The chart and network layers also expose small derived inspectability helpers:

- `LotChartConditionProfile.profile_count`
- `LotChartConditionProfile.strongest_count`
- `LotChartConditionProfile.weakest_count`
- `LotConditionNetworkNode.degree_count`
- `LotConditionNetworkNode.is_isolated`
- `LotConditionNetworkProfile.node_count`
- `LotConditionNetworkProfile.edge_count`

These properties are derived only. They do not change doctrine.

---

### 7. Failure Doctrine

#### 7.1 Input failure behavior

Malformed raw inputs must fail clearly and deterministically before lot
computation proceeds.

Current explicit failures include:

- duplicate normalized planet names
- empty normalized planet names
- non-finite planet longitudes
- house cusp lists not containing exactly 12 entries
- non-integer house cusp numbers
- house cusp numbers outside `1..12`
- missing house cusp numbers
- non-finite house cusp values
- unsupported policy enum values
- malformed nested policy objects
- non-boolean nested policy flags

#### 7.2 Unresolved reference behavior

Unresolved doctrinal references are governed by policy:

| Mode | Behavior |
|---|---|
| `SKIP` | omit the lot silently from the returned result set |
| `RAISE` | raise `ValueError("Unresolved lot ingredient reference: ...")` |

This doctrine applies only after input validation and policy validation have
already succeeded.

#### 7.3 Internal inconsistency behavior

If a vessel is constructed with internally inconsistent truth, classification,
dependency, chart, or network state, it must fail loudly with `ValueError`.

Silent internal drift is prohibited.

---

### 8. Determinism Guarantees

For identical validated inputs and policy, the subsystem guarantees:

- deterministic lot inclusion / omission
- deterministic lot ordering
- deterministic category parsing
- deterministic dependency ordering
- deterministic condition-profile ordering
- deterministic chart strongest / weakest sets
- deterministic network node ordering
- deterministic network edge ordering
- deterministic isolated / most-connected summaries

No public result vessel may depend on hash order or incidental iteration order.

---

## Part II - Invariant Register

### 9. Vessel Invariants

The following invariants are normative.

#### 9.1 `ArabicPartComputationTruth`

- `formula` must match the effective operand keys
- `reversed_for_chart` requires `reversed_at_night`
- `add_reference.key` must match `effective_add_key`
- `sub_reference.key` must match `effective_sub_key`

#### 9.2 `ArabicPartClassification`

- `category_tags` must not be empty
- `primary_category` must be contained in `category_tags`

#### 9.3 `LotDependency`

- each dependency must have a non-empty `effective_key`
- `source_part` and `target_part` are not permitted to collapse into a self-edge later in the network layer

#### 9.4 `LotConditionProfile`

- `primary_category` must be contained in `category_tags`
- `dependencies` must be a subset of `all_dependencies`
- direct / indirect / inter-lot / external counts must match `dependencies`
- `state` must match the derived dependency polarity

#### 9.5 `ArabicPart`

- `longitude` must be in `[0, 360)`
- `formula` must match `computation_truth.formula` when truth is present
- classification must agree with category ordering and reversal truth
- dependencies must agree with preserved computation truth
- `dependencies` must be a subset of `all_dependencies`
- `condition_profile` must agree with lot classification and dependencies

#### 9.6 `LotChartConditionProfile`

- state counts must match profile states
- dependency totals must match profile totals
- `profiles` must be in deterministic order
- `strongest_parts` must match the derived strongest ranking
- `weakest_parts` must match the derived weakest ranking

#### 9.7 `LotConditionNetworkNode`

- `reciprocal_count` may not exceed either incoming or outgoing count

#### 9.8 `LotConditionNetworkEdge`

- `source_part` and `target_part` must differ

#### 9.9 `LotConditionNetworkProfile`

- nodes must be in deterministic order
- edges must be in deterministic order
- reciprocal and unilateral edge counts must match the edges
- reciprocal edges must have reverse partners
- unilateral edges must not have reverse partners
- node incoming / outgoing / reciprocal counts must match the edges
- `isolated_parts` must match the nodes
- `most_connected_parts` must match node degree counts

---

## Part III - Public Surface and Validation Codex

### 10. Stable Public Surface

The stable lots backend surface is the combination of:

- result vessels:
  - `PartDefinition`
  - `ArabicPart`
  - `LotReferenceTruth`
  - `ArabicPartComputationTruth`
  - `LotReferenceClassification`
  - `ArabicPartClassification`
  - `LotDependency`
  - `LotConditionProfile`
  - `LotChartConditionProfile`
  - `LotConditionNetworkNode`
  - `LotConditionNetworkEdge`
  - `LotConditionNetworkProfile`
- enums:
  - `LotReferenceKind`
  - `LotReversalKind`
  - `LotDependencyRole`
  - `LotConditionState`
  - `LotConditionNetworkEdgeMode`
  - `LotsReferenceFailureMode`
- policy types:
  - `LotsDerivedReferencePolicy`
  - `LotsExternalReferencePolicy`
  - `LotsComputationPolicy`
- service:
  - `ArabicPartsService`
- module entrypoints:
  - `calculate_lots`
  - `calculate_lot_dependencies`
  - `calculate_all_lot_dependencies`
  - `calculate_lot_condition_profiles`
  - `calculate_lot_chart_condition_profile`
  - `calculate_lot_condition_network_profile`
  - `list_parts`

Internal helpers remain implementation detail unless explicitly exported later.

---

### 11. Minimum Validation Codex

Any substantive change to `moira/lots.py` must, at minimum, preserve:

1. lot formula and longitude semantics
2. structured truth consistency
3. classification consistency
4. dependency consistency
5. condition-profile consistency
6. chart-profile consistency
7. network consistency
8. deterministic failure behavior

Minimum validation commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_dignities_and_lots.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_rule_engine_validation.py -q -k lots
.\.venv\Scripts\python.exe -m py_compile moira\lots.py tests\unit\test_dignities_and_lots.py
```

If the public package surface changes later, the matching API-freeze test must
also be included in the minimum validation set.

---

### 12. Non-Goals Frozen By This Standard

The current lots backend does **not** include:

- interpretive meanings for lots
- recommendation or judgment logic
- chart-wide interpretive synthesis
- UI or rendering concerns
- probabilistic confidence scoring
- external doctrine beyond the currently embodied reference set

Those concerns belong to later layers or different subsystems. They are not part
of the current constitutional backend.


