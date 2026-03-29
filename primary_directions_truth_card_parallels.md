# Parallels / Contra-Parallels Primary Directions Truth Card

## Historical Name

- `Parallel`
- `Contra-Parallel`
- later also `Rapt Parallel`

## Mathematical Basis

- parallels in primary directions are **not** yet admitted in Moira as a
  generic point-target family
- the obstacle is mathematical, not cosmetic:
  - a parallel is a relational perfection in declination
  - it does not automatically determine one unique projected promissor point
    across all direction methods
- some historical examples, especially in the Ptolemaic zodiacal family, treat
  a parallel through oblique-ascensional equivalence rather than through a
  globally reusable target point

## Current Moira Admission

- not admitted as a generic consumer-facing primary-direction target family
- names such as `Sun Parallel` and `Sun Contra-Parallel` are still
  intentionally rejected by the global target doctrine
- one narrow explicit branch is now admitted:
  - `Ptolemy / semi-arc`
  - `in_zodiaco`
  - relation doctrine `parallel` / `contra-parallel`
  - named preset surface:
    - `PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL`
  - service-supplied `PtolemaicParallelTarget`
  - declination-equivalent ecliptic projection on the branch nearest the
    source longitude
  - current runtime validation now covers both:
    - `parallel`
    - `contra-parallel`
- one further narrow explicit branch is now admitted:
  - `Placidian classic / semi-arc`
  - `in_mundo`
  - relation doctrine `rapt_parallel`
  - named preset surface:
    - `PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT`
    - `PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE`
  - service-supplied `PlacidianRaptParallelTarget`
  - current runtime admission is:
    - direct and converse, as separate explicit preset surfaces
    - promissor/significator pair-specific
    - proportional semi-arc / meridian-distance arithmetic
    - published worked-example fixture coverage for:
      - direct rapt parallel
      - converse rapt parallel
- the existing declination engine in `moira/aspects.py` remains valid for
  ordinary aspect detection, but it is **not** being re-labeled as a global
  primary-direction target law

## Boundary

- Moira does **not** treat parallels as just another zodiacal aspect-point
- Moira does **not** fabricate a generic `parallel point` without a
  method-specific governing law
- the current Ptolemaic point is a derived computational realization of a
  relation class, not evidence that parallels are globally targets
- if parallels are later admitted, they should enter through one of two
  explicit paths:
  - a method-specific relational law
  - a worked-example-backed reconstruction narrow enough to define one
    unambiguous projected target

## Epistemic Status

- `verified narrow admission`
- broader parallel doctrine still deferred pending explicit method-specific laws
- the family-level policy and branch classification now live in:
  - [primary_directions_parallel_family_matrix.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_parallel_family_matrix.md)

## Why They Are Deferred

- the present evidence suggests that parallels belong to target doctrine and
  geometry doctrine at the same time
- that means they cannot be admitted safely as a generic target class alone
- the new Ptolemaic branch is admitted precisely because its governing law is
  explicit enough to stand on its own without pretending to solve the wider
  family
