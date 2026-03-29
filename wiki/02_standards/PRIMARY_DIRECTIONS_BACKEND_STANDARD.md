## Moira Primary Directions Backend Standard

### Governing Principle

The Moira primary-directions backend is a sovereign doctrinal subsystem. Its
definitions, layer boundaries, invariants, failure doctrine, and validation
surface are stated here and frozen until explicitly revised.

This document reflects current implementation truth for the **currently admitted
branch only**:

- `PrimaryDirectionMethod.PLACIDUS_MUNDANE`
- `PrimaryDirectionSpace.IN_MUNDO`
- `PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE` or `DIRECT_ONLY`

It does not describe future Regiomontanian, zodiacal, or field-plane behavior.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Speculum entry

A **speculum entry** in Moira is:

> The authoritative Placidian mundane state of one natal body or angle,
> including normalized ecliptic longitude, equatorial coordinates, hour angle,
> semi-arcs, hemisphere state, and mundane fraction.

#### 1.2 Primary arc

A **primary arc** in Moira is:

> A positive forward arc measuring how far the natal ARMC must advance or
> retreat for one promissor to perfect the significator's mundane position.

For the current branch, perfection means:

- `PrimaryDirectionRelationKind.MUNDANE_POSITION_PERFECTION`

#### 1.3 Relation

A **primary-direction relation** is:

> The typed doctrinal interpretation of one `PrimaryArc` under the admitted
> current method, space, motion doctrine, and key policy.

#### 1.4 Local condition

A **local condition profile** is:

> The integrated per-significator view of all admitted primary arcs directed to
> that significator within one computed result set.

#### 1.5 Aggregate profile

An **aggregate profile** is:

> The chart-wide summary over all per-significator primary-direction profiles.

#### 1.6 Network profile

A **network profile** is:

> The directed promissor-to-significator graph induced by the current arc set.

---

### 2. Layer Structure

The backend is organized into the following implemented phases for the current
branch:

```
Phase  1 - Truth preservation        (SpeculumEntry, PrimaryArc, speculum, find_primary_arcs)
Phase  2 - Classification            (typed method/space/motion/key doctrine)
Phase  3 - Inspectability            (vessel invariants and helper properties)
Phase  4 - Policy surface            (PrimaryDirectionsPolicy, PrimaryDirectionKeyPolicy)
Phase  5 - Relational formalization  (PrimaryDirectionRelation, relate_primary_arc)
Phase  6 - Relation hardening        (PrimaryDirectionRelationProfile, evaluate_primary_direction_relations)
Phase  7 - Local condition           (PrimaryDirectionsSignificatorProfile, evaluate_primary_direction_condition)
Phase  8 - Aggregate intelligence    (PrimaryDirectionsAggregateProfile, evaluate_primary_directions_aggregate)
Phase  9 - Network intelligence      (PrimaryDirectionsNetworkProfile, evaluate_primary_directions_network)
Phase 10 - Full hardening            (cross-layer invariants, deterministic ordering, failure contracts)
Phase 11 - Backend standard          (this document)
Phase 12 - Public API curation       (module-owned API with explicit public-surface verification)
```

Layer boundary rules:

- later phases may consume lower-phase vessels
- later phases may not silently mutate lower-phase vessels
- later phases may not switch doctrine implicitly
- later phases may not widen beyond the current admitted branch

---

### 3. Current Doctrine Surface

#### 3.1 Admitted method and space

Current admitted doctrine:

| Type | Admitted member |
|---|---|
| `PrimaryDirectionMethod` | `PLACIDUS_MUNDANE` |
| `PrimaryDirectionSpace` | `IN_MUNDO` |

No alternate method or space is currently admitted.

#### 3.2 Motion doctrine

Current admitted motion doctrines:

| Type | Admitted members |
|---|---|
| `PrimaryDirectionConverseDoctrine` | `DIRECT_ONLY`, `TRADITIONAL_CONVERSE` |

`NEO_CONVERSE` is not yet implemented or admitted.

#### 3.3 Time-key doctrine

Current admitted keys:

| Key | Family |
|---|---|
| `PTOLEMY` | `STATIC` |
| `NAIBOD` | `STATIC` |
| `SOLAR` | `DYNAMIC` |

Keys remain orthogonal to method and space.

---

### 4. Public Surface

Current owning public module:

- `moira.primary_directions`

Current curated exports:

- doctrine enums and policies
- `SpeculumEntry`
- `PrimaryArc`
- relation/profile/aggregate/network vessels
- `speculum`
- `find_primary_arcs`
- relation/profile/aggregate/network evaluation helpers

The thin root package `moira` does **not** re-export these internals.

---

## Part II - Invariants and Failure Doctrine

### 5. Structural invariants

`SpeculumEntry` invariants:

- `lon` and `ra` normalized to `[0, 360)`
- `dec` in `[-90, 90]`
- `ha` in `[-180, 180]`
- `dsa + nsa == 180` within tolerance
- `f` in `[-2, 2]`
- `upper` agrees with `ha` and `dsa`

`PrimaryArc` invariants:

- non-empty significator and promissor
- no self-directions
- positive arc
- positive solar rate
- `direction` agrees with `motion`
- admitted method and space only

Profile invariants:

- lower-layer ownership consistency is enforced
- aggregate counts must equal profile-derived counts
- network edges may not dangle
- node names must be unique

### 6. Failure doctrine

Current policy:

- invalid doctrine raises `ValueError`
- invalid vessel state raises `ValueError`
- empty aggregate/network/profile requests raise `ValueError`

No silent fallback is allowed for unsupported method, space, or converse doctrine.

---

## Part III - Determinism and Validation

### 7. Determinism

Current deterministic guarantees:

- `find_primary_arcs()` sorts by `(arc, significator, promissor, direction)`
- significator profiles sort by `(significator, nearest_arc)`
- network nodes sort by `name`
- network edges sort by `(nearest_arc, promissor, significator)`

### 8. Validation codex

Minimum verification for the current branch:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\primary_directions.py tests\unit\test_primary_directions.py tests\unit\test_primary_directions_public_api.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_primary_directions.py tests\unit\test_primary_directions_public_api.py -q
```

These checks verify:

- core speculum arithmetic
- arc computation
- typed policy and doctrine invariants
- relation/profile/aggregate/network layers
- public API curation

---

## Part IV - Frontier

### 9. What remains outside the current freeze

The following are explicitly outside this backend standard:

- Placidian classic / semi-arc as a separate admitted branch
- Regiomontanus
- zodiacal directions
- field-plane directions
- symbolic-key families beyond the currently admitted trio
- neo-converse doctrine

Those belong to later doctrinal admission work, not to the current frozen branch.
