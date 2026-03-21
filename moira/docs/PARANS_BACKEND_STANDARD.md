## Moira Paran Backend Standard

### Governing Principle

The Moira paran backend is a sovereign computational subsystem. Its definitions,
identity rules, invariants, and failure doctrine are stated here and are frozen
until explicitly superseded by a revision to this document.

---

## Part I — Architecture Standard

### 1. Authoritative Computational Definition

A **paran** in Moira is:

> A pair of mundane-circle crossing events for two **distinct** bodies whose
> event times fall within a declared time orb, computed at a specific
> terrestrial location during a single 24-hour UT search window.

Every element of this definition is load-bearing:

| Element | Meaning |
|---|---|
| *two distinct bodies* | Self-parans are excluded at the engine level; no exception |
| *mundane-circle crossing* | One of `"Rising"`, `"Setting"`, `"Culminating"`, `"AntiCulminating"` |
| *event times fall within orb* | `abs(jd_a - jd_b) * 24 * 60 <= orb_minutes` |
| *declared time orb* | Caller-supplied; default 4 minutes; must be non-negative |
| *specific terrestrial location* | `(lat, lon)` in degrees; signed; east-positive |
| *single 24-hour UT search window* | `[jd_day, jd_day + 1.0)` |

This definition is **intentionally school-neutral**. It does not privilege
horizon events over meridian events, same-type pairings over mixed-type
pairings, or planets over fixed stars. Any such doctrinal narrowing is the
responsibility of the caller via `ParanPolicy`.

---

### 2. Layer Structure

The backend is organized into thirteen phases. Each phase operates only on
outputs produced by the phases below it. No phase reaches upward.

```
Phase  1 — Event truth preservation
Phase  2 — Classification (ParanSignature)
Phase  3 — Inspectability hardening (ParanCrossing on Paran)
Phase  4 — Policy layer (ParanPolicy, _policy_allows_paran)
Phase  5 — Exactness / strength (ParanStrength, Paran.strength)
Phase  6 — Perturbation stability (ParanStability, evaluate_paran_stability)
Phase  7 — Site and grid evaluation (ParanSiteResult, evaluate_paran_site,
                                      sample_paran_field)
Phase  8 — Sampled-field analysis (ParanFieldAnalysis, analyze_paran_field)
Phase  9 — Contour extraction (ParanContourExtraction,
                                extract_paran_field_contours)
Phase 10 — Contour consolidation (ParanContourPathSet,
                                   consolidate_paran_contours)
Phase 11 — Higher-order field structure (ParanFieldStructure,
                                          analyze_paran_field_structure)
Phase 12 — Doctrine and invariant hardening (validation helpers,
                                              docstring alignment)
Phase 13 — Architecture freeze and validation codex (this document)
```

#### Layer boundary rule

A function in phase N may consume results from phases 1 through N−1.
It may not:
- re-sample the field
- re-extract contours
- recompute crossings
- alter prior results in place

---

### 3. Delegated Assumptions

The paran engine delegates event-time computation to `moira.rise_set` without
redefining it:

| Event | Source | Convention |
|---|---|---|
| Rise | `find_phenomena(..., altitude=-0.5667)` | Stellar apparent horizon |
| Set | `find_phenomena(..., altitude=-0.5667)` | Stellar apparent horizon |
| MC | `get_transit(..., upper=True)` | Upper transit |
| IC | `get_transit(..., upper=False)` | Lower transit |

Bodies that fail to produce any of these events (circumpolar, never-rising,
polar transit failure) simply contribute fewer crossings. This is not an error.

---

### 4. Identity Rules

Identity rules determine when two paran records refer to the "same" paran
across different computation contexts.

#### 4.1 Perturbation identity (Phase 6)

A perturbed candidate is the same paran as the baseline when:

```
candidate.body1   == baseline.body1
candidate.body2   == baseline.body2
candidate.circle1 == baseline.circle1
candidate.circle2 == baseline.circle2
```

Tie-break: when multiple perturbed candidates match, select the one with
`abs(candidate.jd - baseline.jd)` minimized.

#### 4.2 Site identity (Phase 7)

Identical to the perturbation identity rule. The same four-field exact match
is applied across locations.

#### 4.3 Ordering of body1 / body2

`body1` and `body2` on a `Paran` produced by `find_parans` are ordered by
`itertools.combinations` iteration order over the caller-supplied `bodies`
list. The engine does not normalize to alphabetical or canonical order. Callers
must preserve the original list order when comparing across calls if identity
matching is required.

---

### 5. Classification

`ParanSignature` classifies a matched paran on three independent axes:

| Axis | Values | Rule |
|---|---|---|
| `event_family` | `"rise-rise"`, `"rise-set"`, `"rise-mc"`, `"rise-ic"`, `"set-set"`, `"set-mc"`, `"set-ic"`, `"mc-mc"`, `"mc-ic"`, `"ic-ic"` | Alphabetically sorted normalized pair |
| `axis_family` | `"horizon-horizon"`, `"horizon-meridian"`, `"meridian-meridian"` | Alphabetically sorted normalized pair |
| `body_family` | `"planet-planet"`, `"planet-star"`, `"star-star"`, `"other"` | Alphabetically sorted; degrades to `"other"` when either body is unclassified |

Classification is **descriptive only**. It does not alter matching, inclusion,
strength, or ranking.

---

### 6. Policy Layer

`ParanPolicy` operates after classification and before strength computation.
It does not alter event generation or the core coincidence matcher.

Default policy (`DEFAULT_PARAN_POLICY`) is **fully permissive**: all event
families, axis families, body families, and star involvements are admitted.
No narrowing is applied unless the caller passes an explicit policy.

Policy fields:

| Field | Type | Default | Effect |
|---|---|---|---|
| `allow_same_event_family` | `bool` | `True` | Admit `"mc-mc"`, `"rise-rise"`, etc. |
| `allow_same_axis_family` | `bool` | `True` | Admit `"horizon-horizon"`, `"meridian-meridian"` |
| `allowed_body_families` | `frozenset[str] \| None` | `None` | Allow-list; `None` = no restriction |
| `include_stars` | `bool` | `True` | When `False`, reject any candidate involving a named fixed star |
| `allowed_named_stars` | `frozenset[str] \| None` | `None` | Per-name allow-list for star bodies |

---

### 7. Strength

`ParanStrength` is a **pure geometric exactness summary** derived from
`orb_min` only.

```
exactness_score = 1.0 / (1.0 + orb_minutes)
```

`orb_minutes` on `Paran` is the actual event separation in minutes, not the
orb limit. `exactness_score` is in `(0, 1]`. It approaches 1.0 as the
separation approaches 0. It does not weight event families, axis families,
body families, or traditional significance.

`Paran.delta_minutes` is an alias for `Paran.orb_min`.

---

### 8. Perturbation Stability

`evaluate_paran_stability` evaluates how the paran survives small time-anchor
perturbations.

Current method: `"time_anchor_perturbation"`.
- For each offset in `time_offsets_minutes`, shift `jd_day` by that amount.
- Recompute `find_parans` for the same body pair.
- Re-identify by the Phase 6 identity rule.
- Report survival, orb degradation, and exactness degradation per perturbation.

Empty-offsets convention: `time_offsets_minutes=()` produces
`survival_rate=1.0`, `stable_across_window=True`, all degradation fields
`None`. This is a **vacuously stable** result, not a meaningful measurement.

---

### 9. Site and Grid Evaluation

`evaluate_paran_site` evaluates whether a target paran exists at one specific
`(lat, lon)` by recomputing `find_parans` there and applying the Phase 7
identity rule.

`sample_paran_field` is a thin loop over `evaluate_paran_site` across a
caller-supplied rectangular lat/lon grid. It produces a `list[ParanFieldSample]`
in lat-major, lon-minor order matching the grid iteration.

---

### 10. Field Analysis

`analyze_paran_field` operates on an already-sampled rectangular grid.

**Threshold rule**: a sample is active when `metric_value >= threshold`.

**Supported metrics**:

| Metric | Source |
|---|---|
| `"match_presence"` | `1.0` if matched, `0.0` otherwise |
| `"exactness_score"` | `ParanStrength.exactness_score` or `0.0` if unmatched |
| `"survival_rate"` | `ParanStability.survival_rate` or `0.0` if unavailable |

**Adjacency rule**: orthogonal only (N, S, E, W). Diagonal adjacency is
excluded from regions, peaks, and threshold crossings.

**Rectangular-grid precondition**: `len(samples)` must equal
`len(unique_latitudes) * len(unique_longitudes)`. Violation raises `ValueError`
with the expected and actual counts.

**Region IDs**: 1-based, assigned in discovery order (lat-major, lon-minor
scan).

---

### 11. Contour Extraction

`extract_paran_field_contours` applies marching-squares to a rectangular
sampled field.

**Corner bit assignment**:
```
bottom_left = 1,  bottom_right = 2,  top_right = 4,  top_left = 8
```
Membership: `value >= threshold`.

**Interpolation**: linear along each cell edge. Equal-value edge → midpoint
(prevents division by zero, documented fallback).

**Ambiguous cases**: cases 5 and 10 are reported explicitly in
`ParanContourExtraction.ambiguous_cells`. They are resolved with a fixed
deterministic pairing table, not a saddle-point heuristic.

| Case | Pairing |
|---|---|
| 5 | `("left", "top"), ("bottom", "right")` |
| 10 | `("left", "bottom"), ("top", "right")` |

Cases 0 and 15 produce no segments.

---

### 12. Contour Consolidation

`consolidate_paran_contours` stitches `ParanContourExtraction.segments` into
ordered paths.

**Matching rule**: exact floating-point endpoint matching via
`_contour_point_key`. No tolerance. Shared cell edges in the extractor always
produce identical coordinates, so tolerance is unnecessary.

**Preferred-start rule**: segments with a degree-1 endpoint (open chain
termini) are seeded first, ensuring open paths start from their true endpoints.

**Closure rule**: a path is closed when `len(points) >= 3` and
`points[0] == points[-1]` after full bidirectional extension.

**Orphan rule**: a lone isolated segment (both endpoints shared with no other
segment) cannot form a multi-segment path. It is reported in
`orphan_segments`, never silently discarded.

**`segment_count` invariant**: for every stitched path,
`path.segment_count == len(path.points) - 1`. This holds for both open and
closed paths.

---

### 13. Higher-Order Field Structure

`analyze_paran_field_structure` derives structural relationships from Phase 8
and Phase 10 results only. It does not re-sample, re-extract, or alter any
prior result.

**Dominant path**: path with the most points. Ties broken by lowest index.
`None` when path set is empty.

**Containment rule** (`"centroid_in_polygon"`): path B is inside closed path A
when:
1. A's bounding box strictly contains B's bounding box (area and all four
   bounds), AND
2. B's centroid passes a ray-casting point-in-polygon test against A's
   ordered points.

The bounding-box pre-filter prevents symmetric false containment when two
paths' centroids happen to fall inside each other's polygon.

**Parent selection**: when multiple closed paths enclose B, the immediate
parent is the one with the smallest bounding-box area (tightest enclosure).

**Depth**: number of closed ancestors (0 = outermost or open).

**Region association**: centroid proximity to region cell centers. The closest
region cell centroid determines `region_id`.

**Peak association**: a peak is associated when it lies within a path's
bounding box and (for closed paths) also passes the point-in-polygon test.

---

## Part II — Validation Codex

### 14. Authoritative Validation Environment

The project `.venv` is the **sole authoritative runtime and validation
environment**. All implementation decisions answer to `.venv`, not to system
Python, not to CI images, not to external runtimes.

Current runtime: Python 3.14 (as installed in `.venv`).

Validation command:
```
.venv\Scripts\python.exe -m pytest tests\unit\test_parans.py -q
```

Expected result: **all tests pass, zero failures**.

---

### 15. Test Inventory by Phase

| Phase | Test count | Scope |
|---|---|---|
| 1 — Event truth | 2 (slow) | Live `find_parans`; `_crossing_times` against `rise_set` |
| 2 — Classification | 3 | Signature families, body-family classification |
| 3 — Inspectability | 1 | `crossing1`/`crossing2` preserved on `Paran` |
| 4 — Policy | 5 | Permissive default; same-event, same-axis, body-family, star exclusion, named-star filter |
| 5 — Strength | 3 | Inverse-minute formula; tighter orb → stronger; equal orb → equal |
| 6 — Stability | 5 | Perturbation recomputation; survival rate; degradation metrics |
| 7 — Site / grid | 4 | Deterministic site eval; stability on site; unmatched site; grid consistency |
| 8 — Field analysis | 6 | Threshold regions; peak detection; threshold crossings; survival-rate metric |
| 9 — Contour extraction | 5 | Linear interpolation; cell extraction; fragment collection; ambiguous cases; ambiguous cell reporting |
| 10 — Consolidation | 5 | Chain stitching; closed loop; open path; orphan reporting; ambiguity propagation |
| 11 — Field structure | 9 | Dominant path; empty set; containment; open path depth; sibling paths; peak in/out; region association; determinism |
| 12 — Hardening | 22 | Validator helpers; `find_parans` orb guard; `_classify_paran` circle guard; field-function metric and grid guards; `segment_count` invariant; lone orphan; empty-offsets stability |

Total as of Phase 13: **69 tests**.

---

### 16. Invariant Register

The following invariants are guaranteed by the engine and tested in Phase 12.

| Invariant | Guarantee | Enforcement point |
|---|---|---|
| `Paran.orb_min >= 0` | Always non-negative | `find_parans` via `_validate_orb_non_negative` |
| `ParanCrossing.circle in CIRCLE_TYPES` | Validated before classification | `_classify_paran` via `_validate_circle` |
| Field metric is a supported name | Fails immediately at call boundary | `analyze_paran_field`, `extract_paran_field_contours` via `_validate_metric` |
| Samples form a complete rectangular grid | Fails with expected vs actual counts | `analyze_paran_field`, `extract_paran_field_contours` |
| `path.segment_count == len(path.points) - 1` | Holds for all stitched paths | Stitcher construction |
| `closed path: points[0] == points[-1]` | Holds when `path.closed is True` | Stitcher closure check |
| No segment is silently discarded | Orphans reported in `orphan_segments` | Stitcher orphan collection |
| `find_parans` sorts by `orb_min` ascending | Tightest paran first | `find_parans` sort step |
| `region_id` is 1-based | Region IDs start at 1 | `analyze_paran_field` region assignment |
| `survival_rate = 1.0` on empty offsets | Vacuously stable; not a measurement | `evaluate_paran_stability` |

---

### 17. Guaranteed Failure Conditions

The following inputs produce `ValueError` with explicit messages. These are
**not** implementation accidents — they are documented failure conditions.

| Condition | Raised by | Message pattern |
|---|---|---|
| `orb_minutes < 0` | `find_parans` | `"orb_minutes must be non-negative"` |
| Unknown circle string | `_classify_paran` | `"Unknown circle type"` |
| Unsupported metric name | `analyze_paran_field`, `extract_paran_field_contours` | `"Unsupported field metric"` |
| Non-rectangular sample grid | `analyze_paran_field`, `extract_paran_field_contours` | `"rectangular grid"`, expected vs actual counts |

Near-polar transit failures in `_crossing_times` are **not** `ValueError` —
they are silently skipped. This is a deliberate edge-case stance inherited
from `moira.rise_set`.

---

### 18. Non-Goals

The following concerns are **explicitly excluded** from the paran backend.
They are not missing features; they are out of scope by design.

| Excluded concern | Reason |
|---|---|
| Rendering, projection, styling | UI/rendering layer responsibility |
| Smoothing or simplification of contour paths | Interpretation layer responsibility |
| Multi-day paran reconciliation | Outside the 24-hour window doctrine |
| Doctrinal ranking of event families (e.g. Rising preferred over Culminating) | School-specific; not imposed by the engine |
| Self-parans | Excluded at the engine level |
| Approximate endpoint matching in contour stitching | Deterministic extractor makes tolerance unnecessary |
| Location perturbation stability | Not yet implemented; out of current phase scope |
| External ephemeris validation | Delegated to `moira.rise_set` and its own standards |

---

### 19. Implementation Alignment Changes (Phase 13)

The following narrow changes were made to align implementation with this
frozen doctrine. No semantic changes were made.

| Change | File | Justification |
|---|---|---|
| Updated module docstring public surface | `parans.py` | The existing surface listed only Phases 1–2 items; all Phase 3–12 public names were absent |

No other implementation changes were required. All invariants, failure
conditions, and doctrine described in this document were already correctly
implemented as of Phase 12.

---

### 20. Revision Policy

This document is the **architecture freeze record** for the paran backend.

Changes to invariants, identity rules, layer boundaries, or failure doctrine
require:
1. An explicit update to this document.
2. A corresponding test update in `tests/unit/test_parans.py`.
3. Validation in `.venv` confirming zero failures.

Cosmetic documentation improvements do not require a revision entry.
