# Primary Directions Validation Codex

## Purpose

This document defines the validation doctrine for Moira's primary-directions
subsystem on the current admitted recoverable surface.

It is the runtime validation codex for the admitted engine, facade, and REST
surface. It does not turn regression artifacts into external authority.


## Governing Rule

Primary directions may not claim constitutional closure on breadth alone.

The subsystem must preserve:

- core arithmetic truth
- doctrine and gating invariants
- deterministic ordering
- narrow-family validation where those families are admitted
- curated public API boundaries
- engine/facade/REST identity and empty-result semantics
- explicit evidence classification and unresolved validation limits


## Minimum Constitutional Verification

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m compileall -q moira\primary_directions moira\_facade_special.py moira_server\models\primary_directions.py moira_server\services\primary_directions.py moira_server\serializers\primary_directions.py moira_server\routers\primary_directions.py
$tests = Get-ChildItem tests\unit -Filter 'test_primary_direction*.py' | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m pytest $tests -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_phase8_primary_directions_routes.py -q
```


## What These Checks Must Preserve

### Core Arithmetic

- core speculum arithmetic
- geometry-law routing
- arc computation
- key conversion behavior
- continuous four-quadrant mundane-position behavior
- real-domain failure at circumpolar, tangent, and inverse-trigonometric limits

### Doctrine and Policy

- admitted method, space, motion, and key boundaries
- method/space capability rejection, including mundane-only Placidian methods
- Placidian-classic `OA(ASC) = (ARMC + 90 degrees) mod 360` wiring
- relation gating
- target-family gating
- preset integrity
- finite/range/type validation and immutable, defensive result vessels
- positional relation truth distinct from perfection-kind compatibility fields
- relation/perfection space agreement and profile arc ownership/order
- explicit-versus-compatibility solar-rate provenance
- named house-cusp source materialization for aspectual points
- strict supplied Morinus-context source identity and impossible-context
  rejection

### Higher Layers

- relation formalization
- significator condition profiles
- aggregate profiles
- network profiles
- direct/converse and incoming/outgoing count conservation
- ordered method/perfection/relation/target transition networks proven
  realizable as one connected directed Euler path or linearized circuit

### Narrow Family Proof

- Ptolemaic parallels / contra-parallels
- Placidian rapt parallels
- relation-specific Placidian rapt motion and target containment
- fixed stars, including conjunction-policy admission
- antiscia / contra-antiscia
- Morinus conjunction geometry against Morin's own worked arc
  (Astrologia Gallica Book 22, Appendix 5; Hemminga Mars-to-Jupiter, 25 deg 46')
  via `test_morinus_arc_matches_morin_book22_hemminga_oracle`
- Traditional converse as role exchange, not arc negation
  (Astrologia Gallica Book 22, Section I, Chapter 7): converse of
  significator-to-promissor equals the direct arc of promissor-to-significator.
  Proven by `test_converse_is_the_direct_arc_with_roles_exchanged` for the
  asymmetric families and `test_converse_reduces_to_arc_negation_for_symmetric_meridian_law`
  for the symmetric (equatorial) family

### Evidence Classification

- **Historical-authority comparison:** the Morin Book 22 Hemminga
  Mars-to-Jupiter worked arc. The printed source inputs are rounded; the test
  therefore uses a declared `0.06 degree` tolerance, with the current residual
  about `0.11 arcminute`.
- **Cross-source corroboration:** the rounded Ptolemaic examples in
  `primary_directions_ptolemy_examples.json`. They are useful branch checks,
  but are not primary-authority proof of the whole family.
- **Regression and invariant evidence:** the fixed-star and antiscia fixtures,
  exact catalog/formula reconstruction, spherical-plane sweeps, ordered network
  conservation, and engine/facade/REST parity.

Campanus beyond the shared narrow plane law, topocentric worked examples,
wider fixed-star doctrine, and wider reflected-point doctrine remain external-
authority validation gaps. Passing this codex must not be reported as closing
those gaps.

### Public API

- curated `moira.primary_directions` surface
- thin root `moira` package boundary
- established `Moira.speculum(...)` and `Moira.primary_directions(...)`
  positional compatibility
- additive facade evaluation methods
- all eight stable `/v1/primary-directions/*` paths, including reduction
  siblings and submitted-arc evaluation


## Stronger Verification When Touching Specific Areas

### If geometry laws change

Run the targeted geometry and runtime tests that touch:

- `moira/primary_directions/geometry.py`
- `moira/primary_directions/__init__.py`
- method-specific geometry owners

### If narrow target families change

Run the corresponding fixture-backed families:

- `test_primary_direction_ptolemy.py`
- `test_primary_direction_placidus.py`
- `test_primary_direction_fixed_stars.py`
- `test_primary_direction_antiscia.py`

### If presets or relation doctrine change

Run:

- `test_primary_direction_relations.py`
- `test_primary_direction_presets.py`
- affected `test_primary_directions.py` branches


## Verification Interpretation

Passing the codex means:

- the named admitted runtime contracts and tested branches remain stable

Passing the codex does **not** mean:

- deferred frontiers are validated
- research-only branches are admitted
- future doctrine has been settled in advance
- every admitted branch has a primary-authority oracle
- DE441 validates primary-direction doctrine; it supplies chart positions only


## Freeze Rule

No change should be described as preserving primary-directions runtime
admission unless it preserves this codex or replaces it explicitly.

