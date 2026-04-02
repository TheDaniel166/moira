## Moira Synastry Backend Standard

### Governing Principle

The Moira synastry backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Synastry Phase 11. It
describes the subsystem that actually exists in `moira/synastry.py`; it does
not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core synastry computation

A **synastry result** in Moira is:

> The authoritative output of one of the direct relationship-technique
> entrypoints in `moira.synastry`, computed either as cross-chart aspect
> comparison, directional house overlay, midpoint composite construction, or
> one of the supported Davison chart methods.

The computational core remains the authority for:

- inter-chart aspect comparison
- overlay house assignment
- midpoint composite longitude construction
- reference-place composite house construction
- Davison midpoint time and place resolution
- corrected Davison MC-preserving search

Later layers may preserve, classify, inspect, aggregate, or network this
truth. They may not recompute synastry doctrine independently.

#### 1.2 Direct synastry contact

A **synastry contact** in Moira is:

> The authoritative per-contact result of comparing one body from chart A to
> one body from chart B through the admitted aspect engine.

`synastry_aspects(...)` remains the legacy raw aspect surface.  
`SynastryAspectContact` is the richer constitutionalized vessel over that same
contact truth.

#### 1.3 House overlay

A **house overlay** in Moira is:

> The authoritative directional result of assigning one chart's selected bodies
> and nodes into another chart's house frame under the existing house
> membership doctrine.

`SynastryHouseOverlay` preserves this directional truth.  
`MutualHouseOverlay` is a two-direction container only. It is not an
independent engine.

#### 1.4 Composite chart

A **composite chart** in Moira is:

> The authoritative relationship-chart result built from midpoint planetary and
> nodal longitudes, with either midpoint-derived houses or reference-place
> houses depending on the current method.

The supported composite doctrine family is:

- midpoint composite
- reference-place composite

`CompositeChart` is the authoritative composite vessel.

#### 1.5 Davison chart

A **Davison chart** in Moira is:

> The authoritative relationship chart cast for a real midpoint moment and one
> of the currently supported midpoint-place doctrines.

The supported Davison doctrine family is:

- midpoint-location
- uncorrected
- reference-place
- spherical-midpoint
- corrected

`DavisonInfo` preserves the midpoint doctrine truth.  
`DavisonChart` is the authoritative chart-plus-house vessel.

#### 1.6 Relation

A **synastry relation** in Moira is:

> The first-class relational truth describing what kind of synastry link one
> result embodies and on what basis it exists.

The current relation layer distinguishes:

| Kind | Basis set |
|---|---|
| `cross_chart_contact` | `aspect` |
| `house_overlay` | `house_membership` |
| `relationship_chart` | `midpoint_composite`, `reference_place_composite`, `midpoint_location_davison`, `uncorrected_davison`, `reference_place_davison`, `spherical_midpoint_davison`, `corrected_davison` |

#### 1.7 Condition profile

A **synastry condition profile** in Moira is:

> A backend-only integrated structural summary derived from one synastry
> result vessel, consuming existing truth, classification, and relation state.

The current structural states are:

- `contact`
- `overlay`
- `relationship_chart`

`SynastryConditionProfile` is derived only from lower-layer truth. It is not a
second synastry engine.

#### 1.8 Chart condition profile

A **synastry chart condition profile** in Moira is:

> A deterministic aggregate of per-result synastry condition profiles,
> reporting structural counts and strongest / weakest profile summaries under
> the currently embodied ranking.

It includes at least:

- ordered per-result condition profiles
- contact / overlay / relationship-chart counts
- strongest / weakest profile summaries

#### 1.9 Condition network profile

A **synastry condition network profile** in Moira is:

> A deterministic directed graph projection over already-preserved synastry
> relations and condition profiles.

It includes at least:

- pair nodes
- body nodes
- relationship-chart nodes
- directed edges from contacts, overlays, composite, and Davison relations
- per-node incoming / outgoing / total degree
- isolated nodes
- direct-degree connectivity summaries

This graph is structural only. It is not interpretive or advisory.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```
Core      - Authoritative synastry computation (`synastry_aspects`,
            `house_overlay`, `composite_chart`, Davison methods)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Relation formalisation
Phase  6  - Relation inspectability / hardening
Phase  7  - Integrated per-result condition
Phase  8  - Chart-wide condition intelligence
Phase  9  - Relation / condition network intelligence
Phase 10  - Full-subsystem hardening
Phase 11  - Architecture freeze / validation codex
```

#### Layer boundary rules

A layer above the core:

- may consume preserved truth from lower layers
- may classify or aggregate earlier truth
- may add invariant checks that reject internally inconsistent vessels
- may not recompute synastry doctrine independently
- may not alter valid contact, overlay, composite, or Davison semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The synastry backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| aspect computation | `moira.aspects.aspects_between` | authoritative inter-body aspect detector |
| midpoint arithmetic | `moira.midpoints._midpoint` | authoritative shorter-arc midpoint helper |
| planet positions | `moira.planets.all_planets_at` | authoritative relationship-chart planet source |
| node positions | `moira.nodes` | authoritative node and Lilith source |
| house computation | `moira.houses` | authoritative house-frame and house-assignment doctrine |
| Julian Day conversion | `moira.julian` | authoritative datetime / JD conversion |
| obliquity and coordinate conversion | `moira.obliquity`, `moira.coordinates` | authoritative reference-place house inputs |

Changes to those delegated sources propagate into the synastry subsystem. This
document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Direct synastry doctrine

Direct synastry doctrine is now explicit through:

- `SynastryAspectPolicy`
- `SynastryOverlayPolicy`
- `SynastryComputationPolicy`

The current default doctrine governs:

- aspect tier
- orb table admission
- orb factor scaling
- node inclusion in cross-chart contact search
- node inclusion in overlays

#### 4.2 Composite doctrine

Composite doctrine currently includes:

- midpoint composite
- reference-place composite

`SynastryCompositePolicy` governs only the explicit doctrine already embodied
by the engine: the default house system used for reference-place composite
houses.

#### 4.3 Davison doctrine

Davison doctrine currently includes:

- midpoint-location
- uncorrected
- reference-place
- spherical-midpoint
- corrected

`SynastryDavisonPolicy` governs only the explicit doctrine already embodied by
the engine: the default house-system code used across Davison methods.

#### 4.4 Normative default policy

The normative default is:

> `SynastryComputationPolicy()` must preserve the current historical subsystem
> behavior exactly.

---

### 5. Classification

The current classification layer is descriptive only. It classifies:

- cross-chart contact mode
- overlay mode
- composite method
- Davison method and correction state

Classification describes preserved truth. It does not change contact detection,
house assignment, midpoint arithmetic, or relationship-chart semantics.

---

### 6. Inspectability

The current inspectability layer is derived only. It includes, among others:

- on contacts:
  - `contact_mode`
  - `pair_mode`
  - `includes_nodes`
  - `uses_custom_orbs`
  - `has_source_speed`
  - `has_target_speed`
  - `relation_kind`
  - `relation_basis`
  - `condition_state`
- on overlays:
  - `overlay_mode`
  - `pair_mode`
  - `includes_nodes`
  - `target_house_system`
  - `target_effective_house_system`
  - `has_house_fallback`
  - `relation_kind`
  - `relation_basis`
  - `condition_state`
- on composite:
  - `chart_mode`
  - `method`
  - `includes_house_frame`
  - `reference_latitude`
  - `source_house_system`
  - `source_effective_house_system`
  - `relation_kind`
  - `relation_basis`
  - `relation_method`
  - `condition_state`
- on Davison info/chart:
  - `chart_mode`
  - `method`
  - `latitude_mode`
  - `longitude_mode`
  - `correction_mode`
  - `is_corrected`
  - `relation_kind`
  - `relation_basis`
  - `relation_method`
  - `condition_state`

These are derived only. They do not add doctrine.

---

### 7. Failure Doctrine

#### 7.1 Input failure behavior

Malformed public inputs must fail clearly and deterministically before
computation proceeds.

Current explicit failures include:

- empty source/target labels
- invalid synastry aspect tier
- non-positive or non-finite orb factors
- malformed orb tables
- non-boolean overlay `include_nodes`
- one-sided composite house input
- empty house-system codes
- non-finite coordinates for composite reference-place or Davison methods

#### 7.2 Internal inconsistency behavior

If a vessel is constructed with internally inconsistent truth, classification,
relation, condition, chart, or network state, it must fail loudly with
`ValueError`.

Silent internal drift is prohibited.

---

### 8. Determinism Guarantees

For identical validated inputs and policy, the subsystem guarantees:

- deterministic contact ordering
- deterministic overlay placement ordering
- deterministic relationship-chart truth
- deterministic classification
- deterministic relation formation
- deterministic condition profiles
- deterministic chart aggregate ordering
- deterministic network node ordering
- deterministic network edge ordering

No public result vessel may depend on hash order or incidental iteration order.

---

## Part II - Invariant Register

### 9. Vessel Invariants

The following invariants are normative.

#### 9.1 `SynastryAspectContact`

- `truth.source_body == aspect.body1`
- `truth.target_body == aspect.body2`
- classification, when present, agrees with truth
- relation, when present, is `cross_chart_contact` on `aspect`
- relation endpoints agree with preserved truth
- condition profile, when present, agrees with classification and relation

#### 9.2 `SynastryHouseOverlay`

- source and target labels are non-empty
- preserved point count matches placements
- classification, when present, agrees with overlay truth
- relation, when present, is `house_overlay` on `house_membership`
- condition profile, when present, agrees with overlay truth and relation

#### 9.3 `CompositeChart`

- `computation_truth.jd_mean == jd_mean`
- `includes_house_frame` agrees with cusp/angle presence
- classification, when present, agrees with truth
- relation, when present, is `relationship_chart` and matches the composite method
- condition profile, when present, agrees with classification, relation, and house-frame truth

#### 9.4 `DavisonInfo`

- `computation_truth.used_jd == jd_midpoint`
- midpoint latitude and longitude agree with preserved truth
- classification, when present, agrees with truth
- relation, when present, is `relationship_chart` and matches the Davison method
- condition profile, when present, agrees with classification, relation, and method truth

#### 9.5 `DavisonChart`

- `chart.jd_ut == info.jd_midpoint`
- if houses are present, `houses.system == info.computation_truth.house_system`

#### 9.6 `SynastryChartConditionProfile`

- profile ordering is deterministic
- state counts match profile states
- strongest / weakest summaries match the derived structural ranking
- strongest / weakest summaries are deterministically ordered

#### 9.7 `SynastryConditionNetworkProfile`

- nodes are deterministically ordered
- edges are deterministically ordered
- node ids are unique
- edges reference existing nodes
- node degree counts match edges
- isolated nodes match zero-degree nodes
- most-connected summaries match degree ranking
- edge relation kinds and condition states remain aligned

---

## Part III - Public Surface and Validation Codex

### 10. Stable Public Surface

The stable synastry backend surface is the combination of:

- result vessels:
  - `SynastryAspectContact`
  - `SynastryHouseOverlay`
  - `MutualHouseOverlay`
  - `CompositeChart`
  - `DavisonInfo`
  - `DavisonChart`
  - `SynastryRelation`
  - `SynastryConditionState`
  - `SynastryConditionProfile`
  - `SynastryChartConditionProfile`
  - `SynastryConditionNetworkNode`
  - `SynastryConditionNetworkEdge`
  - `SynastryConditionNetworkProfile`
- truth vessels:
  - `SynastryAspectTruth`
  - `SynastryOverlayTruth`
  - `CompositeComputationTruth`
  - `DavisonComputationTruth`
- classification vessels:
  - `SynastryAspectClassification`
  - `SynastryOverlayClassification`
  - `CompositeClassification`
  - `DavisonClassification`
- policy types:
  - `SynastryAspectPolicy`
  - `SynastryOverlayPolicy`
  - `SynastryCompositePolicy`
  - `SynastryDavisonPolicy`
  - `SynastryComputationPolicy`
- module entrypoints:
  - `synastry_aspects`
  - `synastry_contacts`
  - `house_overlay`
  - `mutual_house_overlays`
  - `composite_chart`
  - `composite_chart_reference_place`
  - `davison_chart`
  - `davison_chart_uncorrected`
  - `davison_chart_reference_place`
  - `davison_chart_spherical_midpoint`
  - `davison_chart_corrected`
  - `synastry_contact_relations`
  - `mutual_overlay_relations`
  - `synastry_condition_profiles`
  - `synastry_chart_condition_profile`
  - `synastry_condition_network_profile`

Internal helpers remain implementation detail unless explicitly exported later.

---

### 11. Minimum Validation Codex

Any substantive change to `moira/synastry.py` must, at minimum, preserve:

1. direct contact semantics
2. overlay semantics
3. composite semantics
4. Davison semantics
5. truth/classification consistency
6. relation consistency
7. condition-profile consistency
8. chart-profile consistency
9. network consistency
10. deterministic failure behavior

Minimum validation commands:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\synastry.py tests\unit\test_synastry.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_synastry.py -q
```

If package exposure changes later, the matching public-API test must also be
included in the minimum validation set.

---

### 12. Non-Goals Frozen By This Standard

The current synastry backend does **not** include:

- prose interpretation
- compatibility scoring
- recommendation logic
- declination synastry
- group or multi-composite doctrine
- UI or rendering concerns

Those concerns belong to later layers or different subsystems. They are not
part of the current constitutional backend.

