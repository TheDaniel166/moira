# Primary Directions Invariant Register

## Purpose

This document freezes the cross-layer invariants for Moira's primary-directions
subsystem on the current admitted recoverable surface.

It is the Phase 10 invariant register for primary directions.


## Scope

This register applies to the current admitted surface only:

- admitted methods
- admitted spaces
- admitted motion doctrine
- admitted keys
- admitted relation classes
- admitted narrow target-family expansions
- admitted presets and policy gates

It does not apply to deferred frontiers such as:

- `field_plane`
- `neo-converse`
- midpoint directions
- generic mundane aspects
- wider frontier families not yet admitted


## Truth-Preservation Invariants

### Speculum Entry

- normalized angular quantities remain normalized
- declination remains within `[-90, 90]`
- branch-specific directional quantities must agree with the active geometry law
- semi-arc structures remain internally coherent where that doctrine applies

### Primary Arc

- significator and promissor names are non-empty
- self-directions are not admitted
- arc values are positive
- solar rate is positive
- motion and direction labels agree
- method and space must be admitted


## Doctrine Invariants

### Method / Space / Motion

- runtime methods are limited to the admitted recoverable set
- spaces are limited to `In Mundo` and `In Zodiaco`
- motion doctrine is limited to `Direct` and `Traditional converse`
- `Neo-converse` remains outside the admitted surface

### Key Orthogonality

- time keys do not silently redefine geometry, space, or relation doctrine
- key choice remains orthogonal to method and space

### Relation Gating

- derived promissor families may require explicit admitted relation kinds
- relation doctrine may not be widened ambiently by loose policy fragments
- branch presets must declare the relation surface they admit

### Target Gating

- base target families remain explicit
- derived target families are admitted only through method-specific law
- no derived target family may appear globally merely because one branch can
  compute it


## Preset Invariants

- a preset names a validated runtime surface, not a convenience bundle
- presets may not silently widen relation doctrine
- presets may not silently widen target doctrine
- narrow families must remain narrow at the preset boundary


## Cross-Layer Invariants

- lower-layer vessel ownership remains consistent through relation, condition,
  aggregate, and network layers
- aggregate counts equal what the underlying profiles imply
- network edges do not dangle
- network node names remain unique
- deterministic ordering is preserved across:
  - raw arcs
  - significator profiles
  - network nodes
  - network edges


## Failure Invariants

- invalid doctrine raises `ValueError`
- invalid vessel state raises `ValueError`
- invalid preset-target or preset-relation combinations raise `ValueError`
- empty aggregate, network, or profile requests raise `ValueError`
- no silent fallback occurs for unsupported doctrine


## Admitted Narrow-Family Invariants

### Parallels

- parallels are relation doctrine first, not a global target family
- the admitted Ptolemaic branch remains narrow and method-bound
- Placidian rapt parallels remain narrow and method-bound

### Fixed Stars

- fixed stars enter only as catalog-backed star identities
- the admitted branch remains conjunction-only
- the admitted branch remains limited to angles and planets

### Antiscia

- antiscia / contra-antiscia remain narrow reflected branches
- the admitted branch remains Ptolemaic and zodiacal on the current surface


## Freeze Rule

Any future change that breaks one of these invariants is not a routine feature
addition.

It is a constitutional revision and must be treated as such.
