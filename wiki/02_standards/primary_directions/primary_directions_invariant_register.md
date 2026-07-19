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

- every scalar is a finite real value; booleans and coercive strings are not
  coordinates
- normalized angular quantities remain normalized
- declination remains within `[-90, 90]`
- branch-specific directional quantities must agree with the active geometry law
- semi-arc structures remain internally coherent where that doctrine applies
- no-real rise/set geometry and zero-semi-arc limiting tangencies fail closed

### Primary Arc

- significator and promissor names are non-empty
- self-directions are not admitted
- arc values are positive
- the stored solar rate is positive, and `solar_rate_explicit` records whether
  it is a generated/explicit natal rate or the compatibility value
- motion and direction labels agree
- method and space must be admitted and capability-compatible;
  `PLACIDUS_MUNDANE` and `PLACIDIAN_CLASSIC_SEMI_ARC` reject `In Zodiaco`
- positional `relational_kind` is typed and preserves the actual generated
  conjunction, opposition, aspect, parallel, reflected, or rapt relation


## Doctrine Invariants

### Method / Space / Motion

- runtime methods are limited to the admitted recoverable set
- spaces are limited to `In Mundo` and `In Zodiaco`
- motion doctrine is limited to `Direct` and `Traditional converse`
- `Neo-converse` remains outside the admitted surface
- rapt-parallel motion is admitted against the rapt relation and its configured
  target only; it does not widen ordinary direct/converse motion admission
- Placidian-classic endpoint geometry receives
  `OA(ASC) = (ARMC + 90 degrees) mod 360`, not ecliptic-Ascendant right
  ascension

### Key Orthogonality

- time keys do not silently redefine geometry, space, or relation doctrine
- key choice remains orthogonal to method and space

### Key Doctrine

- the low-level historical string adapter may coerce an unrecognized key token
  to Naibod, and that coercion is inspectable through
  `PrimaryDirectionKeyTruth.fallback_applied` and `.requested_key`
- typed policy, facade, and REST surfaces reject unsupported key values
- `SOLAR` requires one explicit positive finite natal solar rate and is
  classified as a static rate conversion, not a dynamic integration
- the compatibility numeric rate on an implicitly constructed `PrimaryArc`
  remains inspectable but is not usable as natal solar-rate provenance

### Relation Gating

- derived promissor families may require explicit admitted relation kinds
- relation doctrine may not be widened ambiently by loose policy fragments
- branch presets must declare the relation surface they admit
- positional `relational_kind` and perfection-kind `relation_kind` are distinct
  truths; the compatibility `perfection_kind` alias must agree with the latter
- the perfection kind must agree with the owning arc's mundane or zodiacal
  space

### Target Gating

- base target families remain explicit
- derived target families are admitted only through method-specific law
- no derived target family may appear globally merely because one branch can
  compute it
- fixed-star targets require conjunction admission
- combining fixed-star and rapt targets admits only the configured named
  targets; it does not widen all ordinary conjunction promissors
- a house-cusp-sourced aspectual point materializes its named source cusp before
  projection
- supplied Morinus aspect contexts have normalized non-empty source identity,
  are unique by exact `source_name`, and reject impossible path context


## Preset Invariants

- a preset names a validated runtime surface, not a convenience bundle
- presets may not silently widen relation doctrine
- presets may not silently widen target doctrine
- narrow families must remain narrow at the preset boundary


## Cross-Layer Invariants

- lower-layer vessel ownership remains consistent through relation, condition,
  aggregate, and network layers
- detected, admitted, and scored relations belong to their profile's owning
  arc; significator relation profiles preserve the arc sequence one-for-one
- aggregate counts equal what the underlying profiles imply
- network edges do not dangle
- network node names remain unique
- network incoming/outgoing and direct/converse counts equal their underlying
  directed arcs
- ordered method, perfection, relation, and target transition networks form one
  weakly connected, degree-valid directed Euler path after adjacent
  self-transition suppression; a circuit must have sufficient node occurrences
  to be linearized
- deterministic ordering is preserved across:
  - raw arcs
  - significator profiles
  - network nodes
  - network edges


## Failure Invariants

- invalid doctrine raises `ValueError`
- invalid vessel state raises `ValueError`
- invalid preset-target or preset-relation combinations raise `ValueError`
- method/space capability mismatches raise `ValueError`
- empty aggregate, network, or profile requests raise `ValueError`
- no silent fallback occurs for unsupported doctrine
- inverse-trigonometric arguments outside a round-off-sized real-domain margin
  raise `ValueError`; they are not broadly clamped into a fabricated solution

At the REST boundary, a valid search with no matches is a successful empty
transport result. It must not be represented by constructing an invalid empty
engine aggregate or network vessel.


## Admitted Narrow-Family Invariants

### Parallels

- parallels are relation doctrine first, not a global target family
- the admitted Ptolemaic branch remains narrow and method-bound
- Placidian rapt parallels remain narrow and method-bound

### Fixed Stars

- fixed stars enter only as catalog-backed star identities
- the admitted branch remains conjunction-only
- configured fixed-star targets require conjunction admission in the active
  relation policy
- the admitted branch remains limited to angles and planets

### Antiscia

- antiscia / contra-antiscia remain narrow reflected branches
- the admitted branch remains Ptolemaic and zodiacal on the current surface


## Freeze Rule

Any future change that breaks one of these invariants is not a routine feature
addition.

It is a constitutional revision and must be treated as such.

