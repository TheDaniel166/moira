## Moira Primary Directions Backend Standard

**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional on the current admitted recoverable surface

### Governing Principle

The Moira primary-directions backend is a sovereign doctrinal subsystem.

Its authoritative computational surface is the currently admitted recoverable
surface, not the older Placidian-only narrow branch.

This standard therefore describes the subsystem as it actually exists now:

- multiple admitted geometry families
- `In Mundo` and `In Zodiaco`
- direct and traditional converse
- explicit relation doctrine
- explicit preset doctrine
- validated narrow target-family expansions

It does not freeze deferred or unresolved frontiers such as:

- `field_plane`
- `neo-converse`
- midpoint directions
- generic mundane aspects as a family
- wider non-sovereign frontier branches

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Speculum entry

A **speculum entry** in Moira is:

> The authoritative directional state of one natal body, angle, star, or
> derived directed point under an admitted primary-direction branch, including
> the equatorial and directional quantities required by that branch.

For the currently admitted recoverable surface, this includes the Placidian
mundane substrate and the projected/equatorial or under-the-pole quantities
required by the admitted geometry families.

#### 1.2 Primary arc

A **primary arc** in Moira is:

> A positive directional arc measuring the amount of primary motion required
> for the admitted promissor to perfect the admitted relation to the admitted
> significator under one explicit method, space, motion doctrine, and key.

#### 1.3 Relation

A **primary-direction relation** is:

> The typed doctrinal interpretation of one `PrimaryArc` under explicit method,
> space, relation, motion, latitude, and key doctrine.

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

The backend is organized into the following implemented phases:

```text
Phase  1 - Truth preservation        (SpeculumEntry, PrimaryArc, speculum, find_primary_arcs)
Phase  2 - Classification            (typed method/space/motion/key/relation doctrine)
Phase  3 - Inspectability            (vessel invariants and helper properties)
Phase  4 - Policy surface            (PrimaryDirectionsPolicy, presets, target/relation gating)
Phase  5 - Relational formalization  (PrimaryDirectionRelation, relate_primary_arc)
Phase  6 - Relation hardening        (PrimaryDirectionRelationProfile, evaluate_primary_direction_relations)
Phase  7 - Local condition           (PrimaryDirectionsSignificatorProfile, evaluate_primary_direction_condition)
Phase  8 - Aggregate intelligence    (PrimaryDirectionsAggregateProfile, evaluate_primary_directions_aggregate)
Phase  9 - Network intelligence      (PrimaryDirectionsNetworkProfile, evaluate_primary_directions_network)
Phase 10 - Full hardening            (cross-layer invariants, deterministic ordering, failure contracts)
Phase 11 - Backend standard          (this document, once final packet freeze is complete)
Phase 12 - Public API curation       (module-owned API with explicit public-surface verification)
```

Layer boundary rules:

- later phases may consume lower-phase vessels
- later phases may not silently mutate lower-phase vessels
- later phases may not switch doctrine implicitly
- later phases may not widen beyond the admitted recoverable surface without
  explicit constitutional revision

---

### 3. Current Doctrine Surface

#### 3.1 Admitted methods

Current runtime-admitted methods:

- `PLACIDUS_MUNDANE`
- `PTOLEMY_SEMI_ARC`
- `PLACIDIAN_CLASSIC_SEMI_ARC`
- `MERIDIAN`
- `MORINUS`
- `REGIOMONTANUS`
- `CAMPANUS`
- `TOPOCENTRIC`

Important qualifier:

- `MORINUS` is admitted with an explicit doctrinal limit
  - the aspect-plane branch is distinct and source-backed when the required
    context is supplied
  - the conjunction-style branch remains shared with the equatorial family on
    current evidence

#### 3.2 Admitted spaces

Current runtime-admitted spaces:

- `IN_MUNDO`
- `IN_ZODIACO`

Not admitted:

- `FIELD_PLANE`

#### 3.3 Motion doctrine

Current admitted motion doctrines:

- `DIRECT`
- `TRADITIONAL_CONVERSE`

Not admitted:

- `NEO_CONVERSE`

#### 3.4 Time-key doctrine

Current admitted keys:

- `PTOLEMY`
- `NAIBOD`
- `CARDAN`
- `SOLAR`

Keys remain orthogonal to method and space.

#### 3.5 Relation doctrine

Current explicit relation classes:

- `conjunction`
- `opposition`
- `zodiacal_aspect`
- `parallel`
- `contra_parallel`
- `rapt_parallel`
- `antiscion`
- `contra_antiscion`

#### 3.6 Target doctrine

Current base target families:

- planets
- nodes
- angles
- house cusps

Current narrow admitted derived or expanded families:

- zodiacal aspect-point promissors
- Ptolemaic zodiacal parallels / contra-parallels
- Placidian direct and converse rapt parallels
- catalog-backed fixed-star conjunctions to angles and planets
- Ptolemaic zodiacal antiscia / contra-antiscia

---

### 4. Public Surface

Current owning public module:

- `moira.primary_directions`

Current curated public surface includes:

- doctrine enums and policy types
- `SpeculumEntry`
- `PrimaryArc`
- relation/profile/aggregate/network vessels
- branch preset types and preset builders
- narrow target wrapper types for admitted derived families
- `speculum`
- `find_primary_arcs`
- relation/profile/aggregate/network evaluation helpers

The thin root package `moira` does **not** re-export these internals.

---

## Part II - Invariants and Failure Doctrine

### 5. Structural invariants

The governing invariant register for this subsystem is:

- [primary_directions_invariant_register.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\02_standards\primary_directions\primary_directions_invariant_register.md)

`SpeculumEntry` invariants:

- normalized angular quantities remain normalized
- declination remains within `[-90, 90]`
- semi-arc structure remains internally consistent where applicable
- branch-specific directional quantities must agree with the active geometry
  law

`PrimaryArc` invariants:

- non-empty significator and promissor
- no self-directions
- positive arc
- positive solar rate
- `direction` agrees with motion doctrine
- admitted method and space only
- relation kind must be compatible with the requested promissor family
- target family must be compatible with the active branch preset and target
  policy

Cross-layer invariants:

- lower-layer ownership consistency is enforced
- aggregate counts must equal profile-derived counts
- network edges may not dangle
- node names must be unique
- branch presets may not silently widen relation or target doctrine
- derived target families must be realized only through the method-specific law
  that admits them

### 6. Failure doctrine

Current policy:

- invalid doctrine raises `ValueError`
- invalid vessel state raises `ValueError`
- invalid preset-target or preset-relation combinations raise `ValueError`
- empty aggregate/network/profile requests raise `ValueError`

No silent fallback is allowed for unsupported method, space, motion doctrine,
target family, or relation family.

---

## Part III - Determinism and Validation

### 7. Determinism

Current deterministic guarantees:

- `find_primary_arcs()` sorts by `(arc, significator, promissor, direction)`
- significator profiles sort by `(significator, nearest_arc)`
- network nodes sort by `name`
- network edges sort by `(nearest_arc, promissor, significator)`
- fixture-backed narrow families preserve exact reconstruction and published
  rounded values separately where needed

### 8. Validation codex

The governing validation codex for this subsystem is:

- [primary_directions_validation_codex.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\02_standards\primary_directions\primary_directions_validation_codex.md)

Minimum verification for the currently admitted recoverable surface should
include:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\primary_directions.py moira\primary_direction_geometry.py moira\primary_direction_relations.py moira\primary_direction_ptolemy.py moira\primary_direction_placidus.py moira\primary_direction_fixed_stars.py moira\primary_direction_antiscia.py tests\unit\test_primary_directions.py tests\unit\test_primary_directions_public_api.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_primary_directions.py tests\unit\test_primary_directions_public_api.py tests\unit\test_primary_direction_relations.py tests\unit\test_primary_direction_presets.py tests\unit\test_primary_direction_ptolemy.py tests\unit\test_primary_direction_placidus.py tests\unit\test_primary_direction_fixed_stars.py tests\unit\test_primary_direction_antiscia.py -q
```

These checks are expected to verify:

- core speculum arithmetic
- geometry-law routing
- doctrine and preset invariants
- relation and target-family gating
- relation/profile/aggregate/network layers
- admitted narrow-family fixture validations
- curated public API surface

---

## Part IV - Frontier Boundary

### 9. What remains outside the current freeze

The following remain outside this backend standard:

- `FIELD_PLANE`
- `NEO_CONVERSE`
- midpoint directions
- generic mundane aspects as a family
- fixed-star opposition and wider star aspects
- wider non-Placidian parallel families
- wider non-Ptolemaic reflected doctrine
- unresolved method-specific frontier branches documented in the remaining
  frontier packet

These belong to later doctrinal admission work, not to the current frozen
recoverable surface.

