## Moira Primary Directions Backend Standard

**Constitutional Phase:** 12 - Public API curation and transport hardening
**Status:** Admitted runtime standard; external authority validation remains
product- and branch-scoped

### Governing Principle

The Moira primary-directions backend is a Moira-owned doctrinal subsystem.

Its authoritative computational surface is the currently admitted recoverable
surface, not the older Placidian-only narrow branch.

This standard therefore describes the subsystem as it actually exists now:

- multiple admitted geometry families
- `In Mundo` and `In Zodiaco`
- direct and traditional converse
- explicit relation doctrine
- explicit preset doctrine
- validated narrow target-family expansions

This is an implementation and compatibility standard, not a claim that every
historical branch has primary-authority validation. It does not freeze deferred
or unresolved frontiers such as:

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

The arc also carries its actual positional relation kind. A bodily promissor is
`conjunction`; an explicitly derived opposition, aspect, parallel, reflected
point, or rapt-parallel carries that distinct relation kind.

#### 1.3 Relation

A **primary-direction relation** is:

> The typed doctrinal interpretation of one `PrimaryArc` under explicit method,
> space, relation, motion, latitude, and key doctrine.

`relational_kind` names the positional relation. The compatibility
`relation_kind` field names the perfection kind; `perfection_kind` is its
explicit alias. These are separate public truths and must not be conflated.

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

The separate method, perfection, relation, and target transition-network
vessels summarize one ordered input sequence. Their aggregate edges must be
realizable as one connected directed Euler trail after adjacent self-
transitions are suppressed; a balanced circuit must have enough node
occurrences to be linearized. Count conservation alone is not sufficient.

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
Phase 11 - Backend standard          (runtime standard and scoped validation codex)
Phase 12 - Public API curation       (engine, facade, and stable transport verification)
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

- `PLACIDUS_MUNDANE` and `PLACIDIAN_CLASSIC_SEMI_ARC` are mundane-only runtime
  methods. Policy construction, `PrimaryArc`, and geometry dispatch reject an
  `IN_ZODIACO` pairing instead of labeling mundane geometry as zodiacal.
- `PTOLEMY_SEMI_ARC` remains both mundane- and zodiacal-capable under its named
  branch policies.
- `MORINUS` is admitted with an explicit doctrinal limit
  - the aspect-plane branch is distinct and source-backed when the required
    context is supplied
  - the conjunction-style branch follows Morin's circle-of-position treatment
    and currently shares the Regiomontanus under-the-pole runtime law
  - supplied aspect contexts use normalized, non-empty `source_name` identity,
    must be unique by that exact source identity, and fail closed on invalid or
    impossible path context

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

The `SOLAR` key is a static conversion using one explicit positive natal solar
rate. It is not a dynamic solar-arc integration, and it fails closed when that
rate is unavailable. `PrimaryArc` retains a positive numeric compatibility
rate for arcs constructed without a rate, but `solar_rate_explicit=False`
marks that value as unavailable to solar-key conversion; generated arcs and
explicitly supplied natal rates report `solar_rate_explicit=True`. The
low-level key resolver retains its historical,
inspectable unknown-string-to-Naibod adapter; typed facade and REST policy
surfaces reject unsupported or ambiguous key values.

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

Configured fixed stars are admitted only when conjunction is admitted. Rapt
parallel motion is relation-specific: its explicit direct or converse motion
applies to the configured rapt targets and does not widen the ambient policy's
ordinary motions or conjunction targets. When a named aspectual promissor is
sourced from a house cusp, the source cusp is materialized as a directional
entry before the aspect point is projected.

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

The `Moira` facade preserves the established `speculum(...)` and
`primary_directions(...)` positional calls and adds keyword-only doctrine
inputs plus policy-preset, relation, condition, aggregate-profile, and network
delegations. The eight existing `/v1/primary-directions/*` paths are transport
surfaces over these engine meanings; route code does not own doctrine.

The thin root package `moira` does **not** re-export these internals.

---

## Part II - Invariants and Failure Doctrine

### 5. Structural invariants

The governing invariant register for this subsystem is:

- [primary_directions_invariant_register.md](./primary_directions/primary_directions_invariant_register.md)

`SpeculumEntry` invariants:

- all scalar fields are finite real values, not booleans or coercive strings
- normalized angular quantities remain normalized
- declination remains within `[-90, 90]`
- semi-arc structure remains internally consistent where applicable
- a zero-semi-arc limiting tangent and a no-real rise/set geometry fail closed
- branch-specific directional quantities must agree with the active geometry
  law

`PrimaryArc` invariants:

- non-empty significator and promissor
- no self-directions
- positive arc
- positive stored solar rate plus explicit provenance distinguishing a usable
  natal solar rate from the compatibility value
- `direction` agrees with motion doctrine
- admitted method and space only, including method/space capability agreement
- a typed positional `relational_kind`
- relation kind must be compatible with the requested promissor family
- target family must be compatible with the active branch preset and target
  policy

Cross-layer invariants:

- lower-layer ownership consistency is enforced
- `OA(ASC)` supplied to Placidian-classic endpoint geometry is the equatorial
  horizon coordinate `(ARMC + 90 degrees) mod 360`, not the right ascension of
  the ecliptic Ascendant
- relation perfection kind agrees with the arc's space; detected, admitted,
  and scored relations belong to the profile's owning arc; significator
  relation profiles preserve arc order and identity
- aggregate counts must equal profile-derived counts
- network edges may not dangle
- node names must be unique
- branch presets may not silently widen relation or target doctrine
- derived target families must be realized only through the method-specific law
  that admits them
- ordered method/perfection/relation/target transition counts must describe one
  connected, degree-valid directed path or lawfully linearizable circuit

### 6. Failure doctrine

Current policy:

- invalid doctrine raises `ValueError`
- invalid vessel state raises `ValueError`
- invalid preset-target or preset-relation combinations raise `ValueError`
- method/space combinations outside a method's declared capability raise
  `ValueError`
- empty engine aggregate/network/profile requests raise `ValueError`; REST
  search routes represent a lawful no-match result with transport-owned empty
  response vessels rather than constructing invalid engine vessels

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

The runtime spherical laws preserve quadrant continuity. Inverse-trigonometric
branches accept only round-off-sized excursions beyond their real domain and
otherwise fail closed; there are no post-hoc quadrant flips or fabricated
polar solutions.

### 8. Validation codex

The governing validation codex for this subsystem is:

- [primary_directions_validation_codex.md](./primary_directions/primary_directions_validation_codex.md)

Minimum verification for the currently admitted recoverable surface should
include:

```powershell
.\.venv\Scripts\python.exe -m compileall -q moira\primary_directions moira\_facade_special.py moira_server\models\primary_directions.py moira_server\services\primary_directions.py moira_server\serializers\primary_directions.py moira_server\routers\primary_directions.py
$tests = Get-ChildItem tests\unit -Filter 'test_primary_direction*.py' | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m pytest $tests -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_phase8_primary_directions_routes.py -q
```

These checks are expected to verify:

- core speculum arithmetic
- geometry-law routing
- doctrine and preset invariants
- relation and target-family gating
- relation/profile/aggregate/network layers
- admitted narrow-family fixture validations
- curated public API surface
- stable route discovery, submitted-arc reconstruction, empty transport
  responses, and engine/REST doctrine parity

The evidence classes must remain explicit. The Hemminga Mars-to-Jupiter
example is a named historical-authority comparison. The bundled fixed-star and
antiscia fixtures are regression/invariant evidence. Rounded Ptolemaic examples
are scoped cross-source corroboration. None of those narrower artifacts proves
all methods, targets, epochs, latitudes, or historical schools.

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

