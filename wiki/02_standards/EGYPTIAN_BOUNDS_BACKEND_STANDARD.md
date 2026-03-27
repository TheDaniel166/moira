## Moira Egyptian Bounds Backend Standard

### Governing Principle

The Moira Egyptian bounds backend is a sovereign doctrinal subsystem. Its
definitions, layer boundaries, invariants, failure doctrine, and validation
surface are stated here and frozen until explicitly revised.

This document reflects current implementation truth as of Phase 11. It does
not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Egyptian bound

An **Egyptian bound** in Moira is:

> A half-open degree interval `[start, end)` within one tropical zodiac sign,
> ruled by one of the five non-luminary planets under the traditional Egyptian
> terms table.

| Element | Definition |
|---|---|
| *zodiac* | Tropical zodiac, 12 signs, 30 degrees each |
| *interval rule* | Left-closed, right-open: `[start, end)` |
| *rulers admitted* | `Mercury`, `Venus`, `Mars`, `Jupiter`, `Saturn` |
| *table cardinality* | Exactly 5 segments per sign, exactly 30 degrees covered |

#### 1.2 Bound truth

**Bound truth** is:

> The normalized longitude, sign identity, sign index, degree-within-sign, and
> the exact bound segment containing that degree.

| Field | Meaning |
|---|---|
| `longitude` | Normalized ecliptic longitude in `[0, 360)` |
| `doctrine` | Current bound doctrine identity |
| `sign` | Sign name from `moira.constants.SIGNS` |
| `sign_index` | Zero-based sign index |
| `degree_in_sign` | Degree within sign in `[0, 30)` |
| `segment` | The containing `EgyptianBoundSegment` |

#### 1.3 Bound classification

**Bound classification** is:

> The local doctrinal classification of a planet occupying one bound segment.

| Field | Meaning |
|---|---|
| `own_bound` | True when the guest planet matches the bound ruler |
| `host_nature` | `benefic`, `malefic`, or `neutral` |
| `host_in_sect` | Optional chart-sect evaluation of the host ruler |

#### 1.4 Bound relation

A **bound relation** is:

> The directed local guest-to-host relationship between a planet and the bound
> ruler of the segment it occupies.

| Relation kind | Meaning |
|---|---|
| `SELF_HOSTED` | Guest planet occupies its own bound |
| `HOSTED_BY_BENEFIC` | Guest planet is hosted by Venus or Jupiter |
| `HOSTED_BY_MALEFIC` | Guest planet is hosted by Mars or Saturn |
| `HOSTED_BY_NEUTRAL` | Guest planet is hosted by Mercury |

#### 1.5 Bound condition state

A **bound condition state** is:

> The integrated local condition derived from the classification and hardened
> relation layer.

| State | Meaning |
|---|---|
| `SELF_GOVERNED` | Planet is in its own bound |
| `SUPPORTED` | Planet is hosted by a benefic bound ruler |
| `MEDIATED` | Planet is hosted by Mercury |
| `CONSTRAINED` | Planet is hosted by a malefic bound ruler |

---

### 2. Layer Structure

The backend is organized into nine implemented computational phases plus one
hardening phase. Each phase consumes only outputs produced by lower phases.

```
Phase  1 - Truth preservation        (EgyptianBoundSegment, EgyptianBoundTruth, egyptian_bound_of)
Phase  2 - Classification            (BoundHostNature, EgyptianBoundClassification, classify_egyptian_bound)
Phase  3 - Inspectability            (result vessel properties, __post_init__ invariants)
Phase  4 - Policy surface            (EgyptianBoundsDoctrine, EgyptianBoundsPolicy)
Phase  5 - Relational formalization  (EgyptianBoundRelation, relate_planet_to_egyptian_bound)
Phase  6 - Relation hardening        (EgyptianBoundRelationProfile, evaluate_egyptian_bound_relations)
Phase  7 - Local condition           (EgyptianBoundConditionProfile, evaluate_egyptian_bound_condition)
Phase  8 - Aggregate intelligence    (EgyptianBoundsAggregateProfile, evaluate_egyptian_bounds_aggregate)
Phase  9 - Network intelligence      (EgyptianBoundsNetworkProfile, evaluate_egyptian_bounds_network)
Phase 10 - Full hardening            (table validation, cross-layer invariants, deterministic ordering)
```

#### Layer boundary rules

A phase-N function:

- may consume any vessel from phases 1 through N-1
- may not mutate earlier vessels
- may not silently switch doctrine
- may not bypass the table truth owned by `EGYPTIAN_BOUNDS`
- may not recompute lower-layer semantics ad hoc when a lower-layer vessel already exists

---

### 3. Doctrine and Policy Surface

#### 3.1 Admitted doctrine

Current doctrine surface:

| Type | Member |
|---|---|
| `EgyptianBoundsDoctrine` | `EGYPTIAN` |

No alternate term table is currently admitted.

#### 3.2 Policy

`EgyptianBoundsPolicy` currently exposes:

| Field | Default | Meaning |
|---|---|---|
| `doctrine` | `EgyptianBoundsDoctrine.EGYPTIAN` | Selects the admitted bounds table |

Unsupported doctrine values are rejected at construction time.

---

### 4. Public Surface

All public names are declared in `moira/egyptian_bounds.py`.

#### Enumerations

| Name | Members |
|---|---|
| `BoundHostNature` | `BENEFIC`, `MALEFIC`, `NEUTRAL` |
| `EgyptianBoundsDoctrine` | `EGYPTIAN` |
| `EgyptianBoundRelationKind` | `SELF_HOSTED`, `HOSTED_BY_BENEFIC`, `HOSTED_BY_MALEFIC`, `HOSTED_BY_NEUTRAL` |
| `EgyptianBoundConditionState` | `SELF_GOVERNED`, `SUPPORTED`, `MEDIATED`, `CONSTRAINED` |
| `EgyptianBoundNetworkMode` | `UNILATERAL`, `MUTUAL` |

#### Frozen dataclass vessels

| Vessel | Phase | Primary fields |
|---|---|---|
| `EgyptianBoundsPolicy` | 4 | `doctrine` |
| `EgyptianBoundSegment` | 1 | `sign`, `ruler`, `start_degree`, `end_degree` |
| `EgyptianBoundTruth` | 1 | `longitude`, `doctrine`, `sign`, `sign_index`, `degree_in_sign`, `segment` |
| `EgyptianBoundClassification` | 2 | `planet`, `truth`, `own_bound`, `host_nature`, `host_in_sect` |
| `EgyptianBoundRelation` | 5 | `guest_planet`, `host_ruler`, `truth`, `relation_kind`, `host_nature`, `host_in_sect` |
| `EgyptianBoundRelationProfile` | 6 | `planet`, `truth`, `detected_relation`, `admitted_relations`, `scored_relations` |
| `EgyptianBoundConditionProfile` | 7 | `planet`, `truth`, `classification`, `relation_profile`, polarity counts, `state` |
| `EgyptianBoundsAggregateProfile` | 8 | `profiles`, state counts, polarity totals, `strongest_planets`, `weakest_planets` |
| `EgyptianBoundsNetworkNode` | 9 | `planet`, `profile`, degree counts |
| `EgyptianBoundsNetworkEdge` | 9 | `source_planet`, `target_planet`, `relation_kind`, `mode` |
| `EgyptianBoundsNetworkProfile` | 9 | `nodes`, `edges`, `isolated_planets`, `most_connected_planets`, edge counts |

#### Computation functions

| Function | Signature | Phase |
|---|---|---|
| `egyptian_bound_of` | `(longitude, *, policy=None) -> EgyptianBoundTruth` | 1, 4 |
| `bound_ruler` | `(longitude, *, policy=None) -> str` | 1, 4 |
| `is_in_own_egyptian_bound` | `(planet, longitude, *, policy=None) -> bool` | 2, 4 |
| `classify_egyptian_bound` | `(planet, longitude, *, policy=None, is_day_chart=None, mercury_rises_before_sun=False) -> EgyptianBoundClassification` | 2, 4 |
| `relate_planet_to_egyptian_bound` | `(planet, longitude, *, policy=None, is_day_chart=None, mercury_rises_before_sun=False) -> EgyptianBoundRelation` | 5 |
| `evaluate_egyptian_bound_relations` | `(planet, longitude, *, policy=None, is_day_chart=None, mercury_rises_before_sun=False) -> EgyptianBoundRelationProfile` | 6 |
| `evaluate_egyptian_bound_condition` | `(planet, longitude, *, policy=None, is_day_chart=None, mercury_rises_before_sun=False) -> EgyptianBoundConditionProfile` | 7 |
| `evaluate_egyptian_bounds_aggregate` | `(profiles) -> EgyptianBoundsAggregateProfile` | 8 |
| `evaluate_egyptian_bounds_network` | `(aggregate_profile) -> EgyptianBoundsNetworkProfile` | 9 |

#### Constants

| Name | Meaning |
|---|---|
| `EGYPTIAN_BOUNDS` | Authoritative Egyptian terms table |
| `BOUND_RULERS` | Admitted bound rulers |

---

### 5. Determinism and Failure Doctrine

#### 5.1 Determinism

- Longitudes are normalized mod 360 before lookup.
- Bound segments use half-open interval semantics `[start, end)`.
- Aggregate and network layers are ordered by the classic-planet order:
  `Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn`.
- Strongest/weakest and most-connected summaries are derived deterministically
  from profile and node state, not from insertion order.

#### 5.2 Failure doctrine

The subsystem fails loudly on:

- unsupported doctrine values
- malformed table structure
- invalid sign names or rulers
- non-normalized truth vessels
- inconsistent cross-layer summaries
- duplicate planets in aggregate/network structures
- self-loop network edges
- dangling network edges that reference undeclared nodes

No silent fallback doctrine exists inside this subsystem.

---

### 6. Network Doctrine

The network projection is a structural graph over guest-to-host relations.

Rules:

- self-hosted relations remain local condition truth and do not become self-loop edges
- an edge is `MUTUAL` only when two planets host each other reciprocally in the current local relation layer
- otherwise the edge is `UNILATERAL`
- isolated planets are nodes with total degree `0`

---

## Part II - Validation Codex

### 7. Validation Scope

The Egyptian bounds backend is currently validated through:

- dedicated subsystem tests in `tests/unit/test_egyptian_bounds.py`
- legacy table-integrity and dignity-score checks in `tests/unit/test_experimental_validation.py`

### 8. Validation Claims

The following claims are currently verified:

1. The table defines exactly 12 signs.
2. Each sign has exactly 5 contiguous segments covering exactly 30 degrees.
3. Lookup is left-closed/right-open and longitude-normalized.
4. Truth, classification, relation, condition, aggregate, and network vessels enforce invariants.
5. Policy rejects unsupported doctrine.
6. Aggregate and network layers preserve deterministic ordering and consistent summaries.
7. Existing longevity dignity scoring remains intact under the extracted doctrinal owner.

### 9. Validation Commands

The minimum verification slice used for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\egyptian_bounds.py tests\unit\test_egyptian_bounds.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_egyptian_bounds.py tests\unit\test_experimental_validation.py -k "EgyptianBounds or DignityScoreAt" -q
```

### 10. Current Frontier

Phases complete: `P1` through `P12`.

Current frontier:

- `P11 COMPLETE` with this document
- `P12 COMPLETE`: the subsystem remains module-owned in `moira.egyptian_bounds`; the thin root package does not re-export Egyptian-bounds internals

### 11. External Doctrine Basis

The subsystem is grounded in the traditional Egyptian terms/bounds doctrine as
researched from:

- Skyscript / Deborah Houlding on Dorotheus and the Egyptian terms:
  `https://www.skyscript.co.uk/dorotheus3notes.pdf`
- The Astrology Podcast transcript on bounds/terms and their standard Egyptian
  five-planet structure:
  `https://theastrologypodcast.com/transcripts/ep-156-transcript-essential-dignities-and-debilities-with-charles-obert/`

These sources justify the admitted doctrine. The implementation details above
state what Moira currently computes from that doctrine.
