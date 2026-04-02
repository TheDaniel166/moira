## Moira Aspect Backend Standard

### Governing Principle

The Moira aspect backend is a sovereign computational subsystem. Its definitions,
layer boundaries, invariants, failure doctrine, and determinism rules are stated
here and are frozen until explicitly superseded by a revision to this document.

This document reflects current implementation truth as of Phase 12 (272 passing tests).
It does not describe aspirational future capabilities.

---

## Part I — Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Ecliptic aspect

An **ecliptic aspect** in Moira is:

> A detected angular relationship between two distinct celestial bodies whose
> angular separation along the ecliptic falls within a declared orb of a
> canonical aspect angle.

| Element | Definition |
|---|---|
| *two distinct bodies* | `body1 != body2`; no self-aspects |
| *angular separation* | `angular_distance(lon1, lon2)` → `[0, 180]` degrees, folded at 180° |
| *canonical aspect angle* | An angle from `moira.constants.Aspect.ALL` |
| *orb* | `abs(separation - angle)` |
| *within declared orb* | `orb <= allowed_orb` |
| *allowed_orb* | `default_orb * orb_factor`, or the caller-supplied override for that angle |

The admission test is fully reconstructable from the stored vessel:
```
orb        == abs(separation - angle)
orb        <= allowed_orb
separation  = angular_distance(lon1, lon2)
```

#### 1.2 Declination aspect

A **declination aspect** in Moira is:

> A parallel or contra-parallel between two distinct celestial bodies whose
> signed declinations satisfy one of the two defined relationships within a
> declared orb.

| Type | Admission test | Orb formula |
|---|---|---|
| Parallel | `abs(dec1 - dec2) <= allowed_orb` | `orb = abs(dec1 - dec2)` |
| Contra-Parallel | `abs(dec1 + dec2) <= allowed_orb` | `orb = abs(dec1 + dec2)` |

Declination aspects carry no motion data (`applying`, `stationary` are absent
from `DeclinationAspect`).

#### 1.3 Admitted aspect

An aspect is **admitted** when the admission test passes. Admission is binary:
the aspect either qualifies or it does not. There is no partial admission and
no confidence score at the detection layer.

---

### 2. Layer Structure

The backend is organized into twelve phases. Each phase operates only on
outputs produced by phases below it. No phase reaches upward.

```
Phase  1 — Core aspect detection
Phase  2 — Relational truth preservation
Phase  3 — Classification
Phase  4 — Inspectability
Phase  5 — Doctrine inputs
Phase  6 — Policy surface
Phase  7 — Geometric strength
Phase  8 — Temporal state
Phase  9 — Canonical configuration
Phase 10 — Multi-body pattern layer
Phase 11 — Relational graph / network layer
Phase 12 — Harmonic / family intelligence layer
```

#### Layer boundary rule

A function in phase N may consume results from phases 1 through N−1.
It may not:

- re-run position arithmetic
- re-compute aspect admission
- alter a vessel produced by an earlier phase in place
- introduce new doctrine inputs not present in that phase's entry point

---

### 3. Delegated Assumptions

The aspect engine delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| Angular distance arithmetic | `moira.coordinates.angular_distance` | Returns `[0, 180]`, fold at 180° |
| Canonical aspect definitions | `moira.constants.Aspect.ALL` | 22 zodiacal aspects |
| Default orb table | `moira.constants.DEFAULT_ORBS` | `{angle: max_orb}` |
| Aspect tier lists | `moira.constants.ASPECT_TIERS` | Major / Common Minor / Extended Minor |

The aspect backend does not redefine any of these. Changes to these constants
propagate automatically.

---

### 4. Canonical Aspect Set

The complete set of recognised and detectable aspect types is declared in
`CANONICAL_ASPECTS` — a module-level tuple of 24 names, frozen at import time.

| Tier | Count | Names |
|---|---|---|
| Major | 5 | Conjunction, Sextile, Square, Trine, Opposition |
| Common Minor | 6 | Semisextile, Semisquare, Sesquiquadrate, Quincunx, Quintile, Biquintile |
| Extended Minor | 11 | Septile, Biseptile, Triseptile, Novile, Binovile, Quadnovile, Decile, Tredecile, Undecile, Quindecile, Vigintile |
| Declination | 2 | Parallel, Contra-Parallel |

Rules:

- The 22 zodiacal names correspond 1-to-1 with entries in `Aspect.ALL`.
- The 2 declination names are produced exclusively by `find_declination_aspects`.
- `CANONICAL_ASPECTS` carries no detection logic; it is a declaration only.
- No aspect not in `CANONICAL_ASPECTS` can be produced by any detection function.

---

### 5. Classification

`AspectClassification` classifies every admitted aspect on three independent axes:

| Axis | Type | Rule |
|---|---|---|
| `domain` | `AspectDomain` | `ZODIACAL` for ecliptic; `DECLINATION` for parallels |
| `tier` | `AspectTier` | Derived from `AspectDefinition.is_major` and membership in `Aspect.EXTENDED_MINOR` |
| `family` | `AspectFamily` | Derived from `_FAMILY_BY_NAME`; maps each aspect name to its harmonic family |

Classification is **descriptive only**. It describes what was detected, not
how it should be interpreted. Strength, dignity weighting, and reception scoring
are excluded from the classification layer.

#### Family grouping

Aspects in the same harmonic series share a family:

| Family | Members |
|---|---|
| `CONJUNCTION` | Conjunction |
| `OPPOSITION` | Opposition |
| `SQUARE` | Square |
| `TRINE` | Trine |
| `SEXTILE` | Sextile |
| `SEMISEXTILE` | Semisextile |
| `SEMISQUARE` | Semisquare |
| `SESQUIQUADRATE` | Sesquiquadrate |
| `QUINCUNX` | Quincunx |
| `QUINTILE` | Quintile, Biquintile |
| `SEPTILE` | Septile, Biseptile, Triseptile |
| `NOVILE` | Novile, Binovile, Quadnovile |
| `DECILE` | Decile, Tredecile |
| `UNDECILE` | Undecile |
| `QUINDECILE` | Quindecile |
| `VIGINTILE` | Vigintile |
| `DECLINATION` | Parallel, Contra-Parallel |

---

### 6. Policy Layer

`AspectPolicy` encapsulates all detection-time doctrine inputs.

| Field | Type | Default | Effect |
|---|---|---|---|
| `tier` | `int \| None` | `None` | 0=Major only, 1=Major+Common Minor, 2=All; `None` defers to `include_minor` |
| `include_minor` | `bool` | `True` | Include Common Minor when `tier` is `None` |
| `orbs` | `dict[float, float] \| None` | `None` | Custom orb table `{angle: max_orb}`; overrides `orb_factor` when set |
| `orb_factor` | `float` | `1.0` | Multiplier on all default orbs; ignored when `orbs` is set |
| `declination_orb` | `float` | `1.0` | Ceiling for Parallel and Contra-Parallel detection |

When a `policy` argument is passed to a detection function it takes full precedence
over any corresponding individual keyword arguments. Individual parameters remain
available for backward compatibility.

`DEFAULT_POLICY` reproduces the historical default behaviour of all four
detection functions.

#### Policy validation

`AspectPolicy` validates its fields at construction:

| Condition | Raises |
|---|---|
| `orb_factor <= 0` | `ValueError` |
| `declination_orb < 0` | `ValueError` |

---

### 7. Geometric Strength

`AspectStrength` is a **pure arithmetic exactness summary** derived from
`orb` and `allowed_orb` only.

```
surplus   = allowed_orb - orb
exactness = 1.0 - orb / allowed_orb
```

| Field | Definition |
|---|---|
| `orb` | Angular deviation from target angle; always non-negative |
| `allowed_orb` | Orb ceiling applied at admission |
| `surplus` | `allowed_orb - orb`; remaining headroom |
| `exactness` | `1.0 - orb / allowed_orb`; `1.0` = exact, `0.0` = at boundary |

`aspect_strength` does not interpret strength. It does not weight by aspect
family, body dignity, or orbital speed.

#### Strength validation

`aspect_strength` validates its input before computing:

| Condition | Raises |
|---|---|
| `allowed_orb <= 0` | `ValueError` |
| `orb > allowed_orb` | `ValueError` |

---

### 8. Temporal-State Doctrine

`MotionState` formalises the motion-aware truth already stored in `applying`
and `stationary`. It maps the complete decision space without ambiguity:

| Vessel type | `stationary` | `applying` | `→ MotionState` |
|---|---|---|---|
| `DeclinationAspect` | — | — | `NONE` |
| `AspectData` | `True` | any | `STATIONARY` |
| `AspectData` | `False` | `True` | `APPLYING` |
| `AspectData` | `False` | `False` | `SEPARATING` |
| `AspectData` | `False` | `None` | `INDETERMINATE` |

`STATIONARY` takes precedence over `applying` regardless of its value.
`DeclinationAspect` always yields `NONE` because declination detection
receives no speed inputs.

#### Temporal consistency rules

- `APPLYING` ↔ `is_applying is True` and `is_separating is False`
- `SEPARATING` ↔ `is_separating is True` and `is_applying is False`
- `is_applying` and `is_separating` are never simultaneously `True`
- Both are `False` when `applying is None`

---

### 9. Multi-Body Pattern Doctrine

`find_patterns` operates over an already-admitted `list[AspectData]`. It does
not re-run position arithmetic.

Implemented patterns and their structural requirements:

| Kind | Bodies | Required edges |
|---|---|---|
| `STELLIUM` | ≥3, maximal clique | Mutual Conjunction between every pair |
| `T_SQUARE` | exactly 3 | One Opposition (A–B) + Square(A–C) + Square(B–C) |
| `GRAND_TRINE` | exactly 3 | Trine(A–B) + Trine(B–C) + Trine(A–C) |
| `GRAND_CROSS` | exactly 4 | Two Oppositions + four Squares (closed cross) |
| `YOD` | exactly 3 | Sextile(B–C) + Quincunx(A–B) + Quincunx(A–C) |

#### Pattern ordering rules

- Output order: Stellia, T-Squares, Grand Trines, Grand Crosses, Yods.
- Each pattern kind is emitted at most once per unique body set (`frozenset`).
- Stellium: smaller subsets contained within a larger Stellium are suppressed.
- All other kinds are independent. A Grand Cross may also contain T-Squares;
  both are reported.
- Within each kind, patterns are ordered by sorted body-name iteration
  (outer loops always iterate over `sorted(all_bodies)`).

#### Pattern contributing-aspects ordering

The `aspects` tuple inside each `AspectPattern` is sorted by
`(body1, body2, aspect)`. This ordering is stable and independent of the input
list ordering.

#### Structural aspect counts

| Kind | `len(aspects)` |
|---|---|
| STELLIUM (3-body) | 3 |
| STELLIUM (4-body) | 6 |
| T_SQUARE | 3 |
| GRAND_TRINE | 3 |
| GRAND_CROSS | 6 |
| YOD | 3 |

---

### 10. Relational Graph Doctrine

`build_aspect_graph` expresses the chart as a deterministic aspect network.
Bodies become nodes; each admitted `AspectData` becomes an edge.

#### Graph construction rules

- Every body that appears in at least one aspect gets a node.
- Bodies supplied via `bodies=` that have no aspects get degree-0 nodes.
- `nodes` is sorted by body name.
- `edges` is sorted by `(body1, body2, aspect)`.
- `components` is sorted by `(min(component), len(component))` ascending.

#### Node invariants

| Invariant | Expression |
|---|---|
| Degree consistency | `degree == len(edges)` |
| Family count consistency | `sum(family_counts.values()) == degree` |
| Incidence | Every edge in `node.edges` has `body1 == name` or `body2 == name` |
| Edge ordering | `edges` sorted by `(body1, body2, aspect)` |

`family_counts` keys are `AspectData.aspect` strings (e.g. `"Trine"`), not
`AspectFamily` enum values. This is intentional: it preserves per-name granularity
at the graph layer (Trine vs Biquintile both count as QUINTILE family at the harmonic
layer, but remain distinct at the graph layer).

#### Derived properties

| Property | Definition |
|---|---|
| `hubs` | Nodes with maximum degree; empty tuple when all nodes are isolated |
| `isolated` | Nodes with degree 0, sorted by name |

---

### 11. Harmonic Intelligence Doctrine

`aspect_harmonic_profile` derives the family distribution of admitted aspects
at both the chart level and per body.

#### Profile construction rules

- `chart` covers all aspects in the input list.
- `by_body` has one entry per body that appears in at least one aspect.
- `by_body` keys are in sorted body-name order.
- A body with no aspects has no entry in `by_body`.

#### Family resolution order (when `classification` is absent)

1. `a.classification.family` when `classification` is not `None` (normal case).
2. `_FAMILY_BY_NAME[a.aspect]` when `classification` is `None` and the name
   is a known zodiacal name.
3. `AspectFamily.DECLINATION` as the fallback for any unrecognised name
   (covers "Parallel", "Contra-Parallel", or custom names).

#### `AspectFamilyProfile` invariants

| Invariant | Expression |
|---|---|
| Total | `sum(counts.values()) == total` |
| Proportions count | `len(proportions) == len(counts)` |
| Proportions sum | `abs(sum(proportions.values()) - 1.0) < 1e-9` when `total > 0` |
| Dominant membership | Every member of `dominant` is a key in `counts` |
| Proportion range | All proportions in `[0.0, 1.0]` |
| Key ordering | `counts` and `proportions` keys follow `AspectFamily` declaration order |
| Dominant ordering | `dominant` sorted by `AspectFamily.value` (alphabetical) |

---

### 12. Non-Goals

The following concerns are **explicitly outside the scope** of the current
aspect backend:

| Excluded concern | Reason |
|---|---|
| Interpretation (e.g. "this aspect is challenging") | Doctrine-specific; belongs above the engine |
| Dignity weighting or reception scoring | Requires a separate dignity model |
| Body-specific orb weights | Not in current `AspectPolicy` |
| Sinister/dexter distinction | Requires directional awareness not yet in scope |
| Antiscion contacts | A separate geometric computation |
| Cross-chart (synastry) relational policies | Multi-chart context not yet in scope |
| Kite, Mystic Rectangle, Grand Quintile | Require oriented topology or 5-body matching |
| UI rendering or serialization | Belongs above the engine |
| Harmonic chart generation | Separate from aspect detection |

---

## Part II — Validation Codex

### 1. Validation Environment

| Property | Value |
|---|---|
| Authoritative runtime | `.venv` in the project root |
| Python version | 3.14.x (as resolved by `.venv`) |
| Test runner | `pytest` via `.venv\Scripts\python.exe -m pytest` |
| Test file | `tests/unit/test_aspects.py` |
| Baseline | 272 tests, all passing |
| Acceptable result | 0 failures, 0 errors |

No test in `test_aspects.py` may be modified to make the implementation pass.
A failing test is always treated as an implementation defect, not a test defect,
unless the test itself is proven incorrect.

---

### 2. Invariant Register

This register is the normative source of truth for all subsystem invariants.
Each invariant is identified by a short code for traceable reference.

#### INV-TRUTH — Truth preservation

| Code | Invariant |
|---|---|
| T-1 | `orb == abs(separation - angle)` to floating-point precision |
| T-2 | `orb <= allowed_orb` for every admitted `AspectData` |
| T-3 | `orb_surplus == allowed_orb - orb >= 0` |
| T-4 | `separation` is in `[0, 180]` degrees |
| T-5 | For a Parallel: `orb == abs(dec1 - dec2)` |
| T-6 | For a Contra-Parallel: `orb == abs(dec1 + dec2)` |
| T-7 | `dec1` and `dec2` are in `[-90, +90]` |

#### INV-CLASS — Classification

| Code | Invariant |
|---|---|
| C-1 | `classification.domain == ZODIACAL` for every `AspectData` produced by detection |
| C-2 | `classification.domain == DECLINATION` for every `DeclinationAspect` |
| C-3 | `classification.family == _FAMILY_BY_NAME[aspect]` for every zodiacal aspect |
| C-4 | `classification.family == AspectFamily.DECLINATION` for every `DeclinationAspect` |
| C-5 | `classification.tier == MAJOR` for every aspect in `{"Conjunction","Sextile","Square","Trine","Opposition"}` |
| C-6 | Classification is identical for the same aspect name across all calls |

#### INV-STR — Geometric strength

| Code | Invariant |
|---|---|
| S-1 | `0.0 <= orb <= allowed_orb` for any vessel passed to `aspect_strength` |
| S-2 | `surplus == allowed_orb - orb` |
| S-3 | `0.0 <= exactness <= 1.0` |
| S-4 | `exactness == 1.0 - orb / allowed_orb` |
| S-5 | `aspect_strength` raises `ValueError` when `allowed_orb <= 0` |
| S-6 | `aspect_strength` raises `ValueError` when `orb > allowed_orb` |

#### INV-MOT — Temporal state

| Code | Invariant |
|---|---|
| M-1 | `APPLYING` ↔ `is_applying is True` and `is_separating is False` |
| M-2 | `SEPARATING` ↔ `is_separating is True` and `is_applying is False` |
| M-3 | `STATIONARY` when `stationary is True`, regardless of `applying` value |
| M-4 | `INDETERMINATE` when `applying is None` and `stationary is False` |
| M-5 | `DeclinationAspect` always yields `MotionState.NONE` |
| M-6 | `is_applying` and `is_separating` are never simultaneously `True` |

#### INV-PAT — Pattern layer

| Code | Invariant |
|---|---|
| P-1 | Every body in `pattern.bodies` appears in at least one aspect in `pattern.aspects` |
| P-2 | `pattern.aspects` is sorted by `(body1, body2, aspect)` |
| P-3 | No pattern body-set is emitted more than once per kind |
| P-4 | Stellium sub-cliques contained in a larger Stellium are suppressed |
| P-5 | T_SQUARE has exactly 3 contributing aspects |
| P-6 | GRAND_TRINE has exactly 3 contributing aspects |
| P-7 | GRAND_CROSS has exactly 6 contributing aspects |
| P-8 | YOD has exactly 3 contributing aspects |
| P-9 | STELLIUM (3-body) has exactly 3; (4-body) has exactly 6 contributing aspects |
| P-10 | Output order: Stellia, T-Squares, Grand Trines, Grand Crosses, Yods |
| P-11 | `find_patterns` does not mutate the input list |

#### INV-GRAPH — Relational graph

| Code | Invariant |
|---|---|
| G-1 | `degree == len(edges)` for every node |
| G-2 | `sum(family_counts.values()) == degree` for every node |
| G-3 | Every edge in `node.edges` involves that node as `body1` or `body2` |
| G-4 | `node.edges` sorted by `(body1, body2, aspect)` |
| G-5 | `graph.nodes` sorted by body name |
| G-6 | `graph.edges` sorted by `(body1, body2, aspect)` |
| G-7 | `graph.components` sorted by `(min(c), len(c))` ascending |
| G-8 | `build_aspect_graph` does not mutate the input list |

#### INV-HARM — Harmonic layer

| Code | Invariant |
|---|---|
| H-1 | `sum(counts.values()) == total` |
| H-2 | `len(proportions) == len(counts)` |
| H-3 | `abs(sum(proportions.values()) - 1.0) < 1e-9` when `total > 0` |
| H-4 | Every member of `dominant` is a key in `counts` |
| H-5 | All proportions are in `[0.0, 1.0]` |
| H-6 | `chart.total == len(aspects)` |
| H-7 | `by_body[name].total` equals the number of aspects in which `name` participates |
| H-8 | `by_body` keys are in sorted body-name order |
| H-9 | `aspect_harmonic_profile` does not mutate the input list |

#### INV-POL — Policy

| Code | Invariant |
|---|---|
| PO-1 | `AspectPolicy` raises `ValueError` when `orb_factor <= 0` |
| PO-2 | `AspectPolicy` raises `ValueError` when `declination_orb < 0` |
| PO-3 | `DEFAULT_POLICY` is a valid, constructable `AspectPolicy` |

---

### 3. Determinism Register

The following ordering guarantees are normative. Any permutation of an input
list must produce identical output on all of these:

| Context | Determinism guarantee |
|---|---|
| `find_aspects` result order | Sorted by `orb` ascending |
| `find_declination_aspects` result order | Sorted by `orb` ascending |
| `find_patterns` — pattern order | Stellia, T-Squares, Grand Trines, Grand Crosses, Yods |
| `find_patterns` — body-set per pattern | `frozenset` (order-independent identity) |
| `find_patterns` — `aspects` tuple | Sorted by `(body1, body2, aspect)` |
| `build_aspect_graph` — `nodes` | Sorted by body name |
| `build_aspect_graph` — `edges` | Sorted by `(body1, body2, aspect)` |
| `build_aspect_graph` — `components` | Sorted by `(min(c), len(c))` |
| `build_aspect_graph` — `node.edges` | Sorted by `(body1, body2, aspect)` |
| `aspect_harmonic_profile` — `by_body` keys | Sorted body-name order |
| `aspect_harmonic_profile` — `counts` keys | `AspectFamily` declaration order |
| `aspect_harmonic_profile` — `dominant` | Sorted by `AspectFamily.value` (alphabetical) |

---

### 4. Failure Doctrine

The following table lists every condition that raises an exception, the
exception type, and the diagnostic guarantee:

| Function / constructor | Condition | Exception | Diagnostic guarantee |
|---|---|---|---|
| `aspect_strength` | `allowed_orb <= 0` | `ValueError` | Message includes `"allowed_orb"` and the offending value |
| `aspect_strength` | `orb > allowed_orb` | `ValueError` | Message includes `"orb"` and both values |
| `AspectPolicy` | `orb_factor <= 0` | `ValueError` | Message includes `"orb_factor"` |
| `AspectPolicy` | `declination_orb < 0` | `ValueError` | Message includes `"declination_orb"` |

All other functions in the backend are pure computations over valid inputs.
They do not raise on empty lists; they return empty results.

#### Behaviour on empty input

| Function | Input | Returns |
|---|---|---|
| `find_aspects` | `{}` | `[]` |
| `find_declination_aspects` | `{}` | `[]` |
| `find_patterns` | `[]` | `[]` |
| `build_aspect_graph` | `[]` | `AspectGraph(nodes=(), edges=(), components=())` |
| `aspect_harmonic_profile` | `[]` | `AspectHarmonicProfile(chart=empty, by_body={})` |

---

### 5. No-Mutation Guarantee

Every public function beyond the detection layer accepts its inputs by value
and does not mutate them:

| Function | Guarantee |
|---|---|
| `find_patterns(aspects)` | Does not alter `aspects` or any element of it |
| `build_aspect_graph(aspects, ...)` | Does not alter `aspects` or any element of it |
| `aspect_harmonic_profile(aspects)` | Does not alter `aspects` or any element of it |
| `aspect_strength(aspect)` | Does not alter `aspect` |
| `aspect_motion_state(aspect)` | Does not alter `aspect` |

---

### 6. Cross-Layer Consistency Rules

These rules govern the logical relationship between layers. Each rule must
hold on any output produced by the detection layer.

| Rule | Expression |
|---|---|
| Classification–family | `a.classification.family == _FAMILY_BY_NAME[a.aspect]` for all zodiacal `AspectData` |
| Classification–domain | `a.classification.domain == ZODIACAL` for all `AspectData` |
| Strength–surplus | `a.orb_surplus == aspect_strength(a).surplus` |
| Graph–harmonic | `sum(node.family_counts.values()) == hp.by_body[node.name].total` for every node |
| Harmonic–total | `hp.chart.total == len(aspects)` |
| Motion–is_applying | `aspect_motion_state(a) == APPLYING` ↔ `a.is_applying is True` |
| Motion–is_separating | `aspect_motion_state(a) == SEPARATING` ↔ `a.is_separating is True` |
| is_major–is_minor | `a.is_major != a.is_minor` for any classified `AspectData` |

---

### 7. Public Surface Register

Complete public surface of `moira.aspects` as of Phase 12:

#### Enumerations

| Name | Values |
|---|---|
| `AspectDomain` | `ZODIACAL`, `DECLINATION` |
| `AspectTier` | `MAJOR`, `COMMON_MINOR`, `EXTENDED_MINOR` |
| `AspectFamily` | 17 members (see Section 5, Family grouping) |
| `MotionState` | `APPLYING`, `SEPARATING`, `STATIONARY`, `INDETERMINATE`, `NONE` |
| `AspectPatternKind` | `STELLIUM`, `T_SQUARE`, `GRAND_TRINE`, `GRAND_CROSS`, `YOD` |

#### Frozen dataclasses

| Name | Fields |
|---|---|
| `AspectClassification` | `domain`, `tier`, `family` |
| `AspectPolicy` | `tier`, `include_minor`, `orbs`, `orb_factor`, `declination_orb` |
| `AspectStrength` | `orb`, `allowed_orb`, `surplus`, `exactness` |
| `AspectPattern` | `kind`, `bodies`, `aspects` |
| `AspectGraphNode` | `name`, `degree`, `edges`, `family_counts` |
| `AspectGraph` | `nodes`, `edges`, `components`; properties `hubs`, `isolated` |
| `AspectFamilyProfile` | `counts`, `total`, `proportions`, `dominant` |
| `AspectHarmonicProfile` | `chart`, `by_body` |

#### Mutable dataclasses (intentionally not frozen)

| Name | Rationale |
|---|---|
| `AspectData` | Detection functions populate fields after construction |
| `DeclinationAspect` | Detection functions populate fields after construction |

Both vessels are **terminal** (not designed for subclassing) and document their
structural invariants explicitly in their class docstrings.

#### Module-level constants

| Name | Type | Content |
|---|---|---|
| `CANONICAL_ASPECTS` | `tuple[str, ...]` | 24 canonical aspect names |
| `DEFAULT_POLICY` | `AspectPolicy` | Policy matching historical detection defaults |

#### Detection functions

| Name | Signature | Returns |
|---|---|---|
| `find_aspects` | `(positions, *, include_minor, tier, orbs, orb_factor, policy)` | `list[AspectData]` |
| `aspects_between` | `(body1, lon1, speed1, body2, lon2, speed2, ...)` | `list[AspectData]` |
| `aspects_to_point` | `(positions, point_name, point_lon, ...)` | `list[AspectData]` |
| `find_declination_aspects` | `(declinations, *, orb, policy)` | `list[DeclinationAspect]` |

#### Derived-layer functions

| Name | Input | Returns |
|---|---|---|
| `aspect_strength` | `AspectData \| DeclinationAspect` | `AspectStrength` |
| `aspect_motion_state` | `AspectData \| DeclinationAspect` | `MotionState` |
| `find_patterns` | `list[AspectData]` | `list[AspectPattern]` |
| `build_aspect_graph` | `list[AspectData], bodies=None` | `AspectGraph` |
| `aspect_harmonic_profile` | `list[AspectData]` | `AspectHarmonicProfile` |

---

### 8. Validation Baseline

As of Phase 12:

```
272 tests passing
0 failures
0 errors
Runtime: ~0.7 seconds
```

Test categories by phase:

| Phase | Subject | Approximate test count |
|---|---|---|
| 1–4 | Detection, truth preservation, classification, inspectability | ~45 |
| 5–6 | Policy, strength | ~20 |
| 7–8 | Temporal state, strength invariants | ~20 |
| 9 | Canonical aspects | ~22 |
| 10 | Pattern detection | ~24 |
| 11 | Pattern hardening, permutation invariance | ~28 |
| 12–13 | Graph layer | ~36 |
| 14 | Harmonic layer | ~36 |
| 15 | Subsystem hardening, cross-layer consistency | ~31 |
| **Total** | | **272** |

All tests validate against the authoritative `.venv` runtime. No test may be
modified to accommodate an implementation change; implementation must satisfy
the tests as written.

