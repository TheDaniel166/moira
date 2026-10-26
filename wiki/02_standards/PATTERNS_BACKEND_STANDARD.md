## Moira Patterns Backend Standard

### Governing Principle

The Moira patterns backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document includes the 2026-10-26 source-qualified geometric repairs,
Huber additions, alias reconciliation, exact harmonic template admission, and
the ten approved mathematical constructions. It
describes the subsystem that actually exists in `moira/patterns.py`; it does
not describe aspirational future capabilities.

The separate `moira.stelliums.analyze_stelliums` product now owns planet-first
Strict/Broad sign, house and total-span concentration evidence. See
[STELLIUM_ANALYSIS_STANDARD.md](STELLIUM_ANALYSIS_STANDARD.md). This document's
legacy centroid-based Stellium, default count, aspect-contribution and condition
semantics are unchanged; they must not be silently presented as the new product.

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
- opt-in cross-detector structural-containment filtering

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

Its state names describe role-resolution completeness only:

| State | Structural meaning |
|---|---|
| `reinforced` | every preserved contributing aspect has a detector-owned structural role |
| `mixed` | at least one preserved contribution remains the generic `member_link` |
| `weakened` | the pattern has no aspect contributions, as with the position-based Stellium |

These states do not measure harmony, exactness, applying/separating motion, or
interpretive strength. `AspectData.applying` is not an input to this profile.

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
- harmonic 5th- and 7th-harmonic named detectors
- explicit exact geometric templates and harmonic presets
- stellium position clustering doctrine

There are **37 canonical named patterns**: the 27 below and the ten mathematical
constructions in the following section. Aliases select the same detector and
never create another result name. Default searches cover the 35 names whose
targets are standard; enabling H13 additionally admits its two Spectrum layouts.
Geometric presets remain independent opt-ins.

| Canonical pattern | Required angles in degrees, unless indicated |
|---|---|
| T-Square | 90, 90, 180 |
| Grand Trine | 120, 120, 120 |
| Grand Cross | four 90 and two 180 |
| Yod | 60, 150, 150 |
| Mystic Rectangle | two each of 60, 120, 180 |
| Kite | two 60, three 120, one 180 |
| Stellium | Legacy centroid cluster: at least three bodies within 8 degrees of centroid |
| Minor Grand Trine | 60, 60, 120 |
| Grand Sextile | Six cyclic 60 edges; admitted implied trines/oppositions are also preserved |
| Thor's Hammer | 90, 135, 135 |
| Boomerang Yod | Yod plus opposition to its apex |
| Wedge | 60, 120, 180 |
| Cradle | Three 60, two 120, one 180 |
| Trapeze | 60, 90, 90, 120, 150, 150 |
| Eye | 30, 30, 60 |
| Irritation Triangle | 30, 150, 180 |
| Hard Wedge | 45, 135, 180 |
| Dominant Triangle | 90, 120, 150 |
| Grand Quintile | Five 72 and five 144: the complete regular-pentagon pair ledger |
| Quintile Triangle | 72, 144, 144 |
| Septile Triangle | Exact turn fractions 1/7, 2/7, 3/7 |
| Sextile Chain | Three-sextile chain plus opposition between its endpoints |
| Small Learning Triangle | 30, 60, 90 |
| Medium Learning Triangle | 30, 90, 120 |
| Large Learning Triangle | 60, 90, 150 |
| Search Triangle | 30, 120, 150 |
| Irritation Rectangle | Two each of 30, 150, 180 |

The Huber geometries are transcribed from the 30-degree tick diagrams in the
[APA Diploma Course, Figure 2.3.41, printed p. 93](https://astrologicalpsychology.org/wp-content/uploads/2023/12/33ea1-figures_2.3.40-43_aspect_figures.pdf).
The three learning-size names follow the revised edition described on the
[publisher's Aspect Pattern Astrology page](https://astrologicalpsychology.org/books/huber-books/aspect-pattern-astrology-2/).
These are geometric detectors over caller-selected points. They do not claim
to implement the full Huber interpretation method, its planet-only eligibility,
or its planet-specific orb system. Moira's declared geometric orb policy applies.

#### Name reconciliation and migration

`PATTERN_ALIASES` is immutable; `resolve_pattern` accepts canonical names and
declared aliases, ignoring case, ASCII spaces, hyphens and underscores. Leading
or trailing whitespace and unknown names are rejected. Selecting both an alias
and its canonical name is rejected as duplicate selection.

| Alias | Canonical detector |
|---|---|
| Ear; Information Triangle; Cosmic Eye | Eye |
| Ambivalence Triangle; Single Ambivalence Figure; Arrowhead | Wedge |
| Projection Triangle; Finger of God | Yod |
| Star of David | Grand Sextile |
| God's Fist; Thors Hammer | Thor's Hammer |
| Small Talent Triangle | Minor Grand Trine |
| Large Talent Triangle | Grand Trine |
| Efficiency Triangle; Achievement Triangle | T-Square |
| Efficiency Square; Achievement Square | Grand Cross |
| Righteousness Rectangle; Righteous Rectangle | Mystic Rectangle |
| Huber Trapeze | Trapeze |
| Legacy Trapeze; Trapeze (legacy) | Sextile Chain |

This intentionally supersedes the former non-closing Eye (120/150/150),
Irritation Triangle (180/150/150), and Dominant Triangle (90/150/180) definitions.
The former all-mutual-72 Grand Quintile requirement is replaced by a realizable
pentagon. `find_trapezes` now detects the distinct Huber figure. Callers relying
on the old three-sextile-chain definition must select `Sextile Chain` or its
legacy alias, or call `find_sextile_chains`.

#### Mathematical constructions

`MATHEMATICAL_PATTERN_TEMPLATES` is the immutable registry of these ten exact
layouts. Names are Moira geometric labels; they assert neither historical
astrological tradition nor an assigned psychological interpretation.
Every pair of vertices is required, including all diagonals.

Notation `(a,b,c)/H` means phases `a/H`, `b/H`, `c/H` of one turn; degrees are
`360 * phase`. The exact fractions govern repeating decimals shown approximately.

| Canonical name | Exact phases in turns | Longitudes in degrees | Required optional set |
|---|---|---|---|
| H13 Spectrum A | `(0,1,3,9)/13` | approximately 0, 27.692308, 83.076923, 249.230769 | H13 |
| H13 Spectrum B | `(0,2,5,6)/13` | approximately 0, 55.384615, 138.461538, 166.153846 | H13 |
| H11 Balanced Spectrum | `(0,2,3,4,8)/11` | approximately 0, 65.454545, 98.181818, 130.909091, 261.818182 | None |
| Interval Prism A | `(0,1,4,6)/12` | 0, 30, 120, 180 | None |
| Interval Prism B | `(0,1,3,7)/12` | 0, 30, 90, 210 | None |
| Fibonacci Fan | `(0,1,2,4,7)/12` | 0, 30, 60, 120, 210 | None |
| Fibonacci Crown | `(0,1,2,4,7,12)/20` | 0, 18, 36, 72, 126, 216 | None |
| Triadic Braid | `(0,1,5,6,10,11)/15` | 0, 24, 120, 144, 240, 264 | None |
| Split Cross | `(0,1,4,5,8,9,12,13)/16` | 0, 22.5, 90, 112.5, 180, 202.5, 270, 292.5 | None |
| Harmonic Bridge | `(0,2,5)/30` | 0, 24, 60 | None |

Their mathematical definitions are independently testable:

- The H13 Spectra each use all six minor H13 intervals exactly once. Their
  twelve directed differences cover every nonzero residue modulo 13 once.
  Exhaustive four-point enumeration yields exactly these two geometries modulo
  rotation and reflection; their identical interval inventories do not merge them.
- H11 Balanced Spectrum uses each of the five H11 minor intervals exactly twice.
  Its shifted `(11,5,2)` difference set comes from the flat interval distribution
  example in section 4.3 of [Amiot and Sethares, An Algebra for Periodic Rhythms
  and Scales (2009)](https://sethares.engr.wisc.edu/paperspdf/AlgofScales.pdf).
- The Prisms each contain 30, 60, 90, 120, 150 and 180 exactly once, but their
  arrangements differ. They adapt the homometric pair in that paper's Example 9.
  Full pair assignments, not angle counts alone, determine admission.
- Fibonacci Fan has cyclic gap steps `1,1,2,3,5` on H12; Crown has
  `1,1,2,3,5,8` on H20. Crown contains every minor H20 angle, with its repeated
  interval steps exactly `1,2,3,5,8`.
- Triadic Braid superposes two regular triangles offset by 24 degrees;
  Split Cross superposes two squares offset by 22.5 degrees.
- Harmonic Bridge closes with intervals `2/30,3/30,5/30` turns: 24, 36, 60
  degrees. The incomplete H30 grid needs no new aspect target or full H30 preset.

Default edge orbs are those of the existing catalog, scaled by `orb_factor`.
H13 links use `12/13` degrees; H11 links use 1 degree. Prism and Fan links use
the standard 30/60/90/120/150/180 defaults. Crown uses all ten H20 angle types
with their existing individual defaults. Braid's 24/96/120/144 links use
1/1/7/2 degrees; Split Cross's 22.5/67.5/90/112.5/157.5/180 links use
1/1/7/1/1/8 degrees; Bridge's 24/36/60 links use 1/1.5/5 degrees.
No separate interpretive strength or orb scale is invented for these names.

| Additional alias | Canonical construction |
|---|---|
| H13 Perfect Spectrum A | H13 Spectrum A |
| H13 Perfect Spectrum B | H13 Spectrum B |
| Undecile Balanced Spectrum | H11 Balanced Spectrum |
| Prism A; Prism B | Interval Prism A; Interval Prism B, respectively |
| Fibonacci Gap Fan; Fibonacci Gap Crown | Fibonacci Fan; Fibonacci Crown, respectively |
| Quindecile-Trine Braid | Triadic Braid |
| Hexadecile Split Cross | Split Cross |
| H30 Bridge | Harmonic Bridge |

Use `find_all_patterns(..., include=[name])`, the shared facade/REST selector,
or `find_mathematical_patterns(positions, *, include=None, optional_sets=(),
orb_factor=1.0, aspects=None, dominant_only=False)`. The dedicated finder selects
only mathematical constructions and accepts their registered aliases. Its
default covers the eight standard constructions; H13 selection adds both
Spectra. Explicitly requesting an H13 name without `optional_sets=("H13",)`
raises `ValueError` (HTTP 422) before chart access, including with precomputed
H13 aspects. `include=[]` selects none in this dedicated finder.

Registered templates may also be passed directly to `find_geometric_patterns`;
their exact registered definitions are accepted. Altered custom templates
cannot replace a registered name. Reusing the same registered definition in
named and explicit-template search returns one result per name/body set.
`GeometricPatternTemplate.required_optional_sets` exposes required catalog
membership without silently enabling a set. Geometry responses preserve this
property alongside their fractions, vertex assignment, source and orientation.

#### 4.2 Orb doctrine

Pattern orb doctrine is embodied by:

- detector-specific fixed base orbs
- the caller-visible `orb_factor`
- current Stellium `orb` and `min_bodies` doctrine

The default policy selects all available named detectors, with cross-detector
containment disabled. Optional targets remain explicitly selected.

#### 4.3 Policy doctrine

`PatternComputationPolicy` makes current doctrine explicit without changing the
default result.

| Policy area | Type | Current default |
|---|---|---|
| named detector selection | `PatternSelectionPolicy` | all available names; 35 with standard targets |
| Stellium doctrine | `StelliumPolicy` | `min_bodies=3`, `orb=8.0` |
| global orb scaling | `PatternComputationPolicy.orb_factor` | `1.0` |
| cross-detector containment | `PatternComputationPolicy.dominant_only` | `False` |
| optional longitude targets | `optional_sets` | `()` |
| caller-supplied exact layouts | `templates` | `()` |
| harmonic geometric families | `harmonic_presets` | `()` |

The normative default is:

> `PatternComputationPolicy()` selects the 35 standard-target names, with no
> optional targets, harmonic presets, or custom templates. H13 selection adds
> its two Spectrum names. This revision includes the four repairs, five Huber
> additions, and ten mathematical constructions.

#### 4.4 Dominant-containment doctrine

When `dominant_only=True`, a detected aspect pattern is omitted only when it is
a strict structural subgraph of another admitted aspect pattern. This requires:

- both patterns to be aspect-sourced
- inclusion of the smaller pattern's body set in the container's body set
- at least one contribution in the smaller pattern
- inclusion of every smaller-pattern aspect signature in the larger pattern's
  full preserved aspect surface
- strict inclusion in at least one dimension: bodies or aspect signatures

Body count alone is not containment. Equal-body patterns remain present when
their aspect surfaces are equal or incomparable, but an equal-body strict edge
subgraph such as Sextile Chain inside Cradle is omitted. Position-sourced Stelliums
remain incomparable with aspect patterns and retain their detector-local
maximal-group rule. Dominance is evaluated only among detectors admitted by the
current selection policy, so an excluded container cannot hide a requested
subpattern.

---

#### 4.5 Exact geometric layouts and harmonic families

`GeometricPatternTemplate(name, phases, apex_index=None, source=...)` declares
3–40 distinct vertices in strictly increasing exact fractions of a turn,
starting at zero and ending below one. Phases accept `Fraction` values,
integers, or integer `(numerator, denominator)` pairs; floats are rejected.
Every unordered vertex pair is required. Its target is
`min(abs(phase_i - phase_j), 1 - abs(phase_i - phase_j))` turns. Non-closing
collections of edges cannot be represented by a layout.

`triangle_template(name, (aspect_name, aspect_name, aspect_name))` resolves
canonical aspect names or registered aspect aliases and constructs a layout
only when those three minor angles close on a longitude circle. Quindecile
remains 24 degrees and Tao remains 165 degrees.

`find_geometric_patterns(positions, templates, *, aspects=None,
optional_sets=(), orb_factor=1.0)` requires every pair to be admitted within
the selected catalog's default orb multiplied by `orb_factor`, and within
the supplied aspect's `allowed_orb`. Precomputed separations must agree with
the supplied positions. Unknown edge fractions and optional edges without
their explicit set selection raise `ValueError`; they are not silently dropped.

For the repaired/new named layouts, default edge ceilings are: semisextile
2 degrees, sextile 5, square/trine 7, quincunx 3, opposition 8, and
quintile/biquintile 2. Generic templates use the complete
[aspect catalog's defaults](ASPECT_CATALOG.md), including `12/H` degrees for
the optional primitive harmonic targets. These are Moira orb policies.

`harmonic_pattern_templates(H, shapes=("triangle",))` generates all distinct
triangle layouts on that grid. `shapes` may additionally select
`"opposition_rectangle"` and `"polygon"`. Rectangles require two oppositions
and the complementary `alpha` / `180-alpha` pairs; unavailable complementary
targets are excluded. The regular polygon requires every diagonal as well as
the perimeter. Reducible layouts use their primitive grid name.

`HARMONIC_PATTERN_PRESETS` contains H3, H4, H5, H6, H7, H8, H9, H10, H11,
H12, H13, H14, H15, H16, H18, H20, H24, H32, H36 and H40. Passing a key in
`harmonic_presets` requests all three shape categories. Overlapping preset
geometry is collapsed by exact cyclic-gap identity modulo rotation/reflection.
Custom names must not override a registered name or alias. Explicit templates
and preset geometry are independent of `include`, which selects named detectors.
Use `include=[]` to request geometry alone. A deliberately requested geometric
template can describe the same shape as a named detector; the two remain
separately identified by name and source.

H13, H32, H36 and H40 require the matching `optional_sets` entry. Selecting a
set makes its registered named constructions available; generic harmonic
presets still require `harmonic_presets`. Mixed-family triangles can
be supplied through `triangle_template` without requiring a complete harmonic
grid. The matcher supports all 174 exact standard-catalog triangle geometries,
or 436 with every optional set. These are unlabelled mathematical shapes,
excluding conjunctions and ignoring body identity/orbs, not additional named
astrological traditions.

`AspectPattern.geometry` preserves the exact template, the body assignment in
vertex order, and orientation. `forward` and `reflected` refer to increasing
longitude relative to that template; they are not planetary motion states.
`symmetric` identifies an ideal layout with reflection symmetry; `ambiguous`
retains broad-orb orientation ambiguity. Individual aspect-list detectors have
no position witness and therefore report orientation as `None`. Results,
contributions, structural condition, dominance and networks use the existing
`AspectPattern` pipeline. No new qualitative grading is introduced.
For non-apex layouts, perimeter edges are `cycle_link`, opposition diagonals
are `axis_link`, and other diagonals are `support_link`; apex layouts retain
the existing apex/base roles. Thus a pentagon preserves its five biquintile
diagonals without mislabelling them as perimeter edges.

```python
from fractions import Fraction
from moira.patterns import (
    GeometricPatternTemplate, find_all_patterns, find_geometric_patterns,
    harmonic_pattern_templates, triangle_template,
)

two_quintiles = triangle_template(
    "Two quintiles", ("Quintile", "Quintile", "Biquintile"),
)
tao_rectangle = GeometricPatternTemplate(
    "Untion-Tao rectangle", (Fraction(0), Fraction(1, 24), Fraction(1, 2), Fraction(13, 24)),
)
matches = find_geometric_patterns(longitudes, (two_quintiles, tao_rectangle))
h7_triangles = harmonic_pattern_templates(7)  # four distinct geometries
optional_matches = find_all_patterns(
    longitudes, include=[], harmonic_presets=("H13", "H32", "H36", "H40"),
    optional_sets=("H13", "H32", "H36", "H40"),
)
```

### 5. Classification

`PatternClassification` is descriptive only. It classifies:

- source kind
- symmetry kind
- body count
- apex presence
- typed body roles

`PatternAspectRoleKind` classifies contribution roles descriptively only.

Detector-owned symmetric topology is preserved without arbitrary left/right
labels:

- Grand Trine bodies are `cycle_member`; all three trines are `cycle_link`.
- Minor Grand Trine preserves its public symmetric/no-apex contract: the trine
  endpoints are `base`, the two-sextile focus is `support`, and its links are
  one `base_link` plus two `support_link` records.
- Cradle and Sextile Chain opposition endpoints are `axis`; the remaining bodies are
  `support`, producing one `axis_link` and structured support links.
  The admitted Sextile Chain graph is specifically a three-sextile chain with its
  two end bodies in opposition; it is not the six-edge Cradle graph.
- Grand Cross and Mystic Rectangle bodies are `cycle_member`; opposition
  diagonals are `axis_link` and perimeter relations are `cycle_link`.
- Septile Triangle bodies and its three harmonic boundary relations are
  `cycle_member` and `cycle_link` respectively.

These assignments follow detector-proved graph roles. There is no blanket rule
that relabels every no-apex pattern as structured.

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
- non-boolean dominant-only policy

#### 7.2 Internal inconsistency behavior

If a vessel is constructed with internally inconsistent truth, classification,
contribution, condition, chart, or network state, it must fail loudly with
`ValueError`.

Silent internal drift is prohibited.

---

### 8. Determinism Guarantees

For identical validated inputs and policy, the subsystem guarantees:

- deterministic pattern inclusion / omission
- deterministic maximal structural-containment filtering when requested
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
.\.venv\Scripts\python.exe -m pytest tests\unit\test_pattern_facade.py tests\server\test_server_patterns_policy.py -q
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
- pattern-to-pattern doctrinal inference beyond the explicit optional
  structural-containment filter

Those concerns belong to later layers or different subsystems. They are not
part of the current constitutional backend.

