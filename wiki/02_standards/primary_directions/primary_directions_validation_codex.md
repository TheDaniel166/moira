# Primary Directions Validation Codex

## Purpose

This document defines the validation doctrine for Moira's primary-directions
subsystem on the current admitted recoverable surface.

It is the Phase 11 validation codex used to support constitutional freeze.


## Governing Rule

Primary directions may not claim constitutional closure on breadth alone.

The subsystem must preserve:

- core arithmetic truth
- doctrine and gating invariants
- deterministic ordering
- narrow-family validation where those families are admitted
- curated public API boundaries


## Minimum Constitutional Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\primary_directions.py moira\primary_direction_geometry.py moira\primary_direction_relations.py moira\primary_direction_ptolemy.py moira\primary_direction_placidus.py moira\primary_direction_fixed_stars.py moira\primary_direction_antiscia.py tests\unit\test_primary_directions.py tests\unit\test_primary_directions_public_api.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_primary_directions.py tests\unit\test_primary_directions_public_api.py tests\unit\test_primary_direction_relations.py tests\unit\test_primary_direction_presets.py tests\unit\test_primary_direction_ptolemy.py tests\unit\test_primary_direction_placidus.py tests\unit\test_primary_direction_fixed_stars.py tests\unit\test_primary_direction_antiscia.py -q
```


## What These Checks Must Preserve

### Core Arithmetic

- core speculum arithmetic
- geometry-law routing
- arc computation
- key conversion behavior

### Doctrine and Policy

- admitted method, space, motion, and key boundaries
- relation gating
- target-family gating
- preset integrity

### Higher Layers

- relation formalization
- significator condition profiles
- aggregate profiles
- network profiles

### Narrow Family Proof

- Ptolemaic parallels / contra-parallels
- Placidian rapt parallels
- fixed stars
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

### Public API

- curated `moira.primary_directions` surface
- thin root `moira` package boundary


## Stronger Verification When Touching Specific Areas

### If geometry laws change

Run the targeted geometry and runtime tests that touch:

- `moira/primary_direction_geometry.py`
- `moira/primary_directions.py`
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

- the admitted recoverable surface remains constitutionally stable

Passing the codex does **not** mean:

- deferred frontiers are validated
- research-only branches are admitted
- future doctrine has been settled in advance


## Freeze Rule

No change should be described as preserving primary-directions constitutional
closure unless it preserves this codex or replaces it explicitly.

