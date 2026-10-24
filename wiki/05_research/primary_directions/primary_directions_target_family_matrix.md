# Primary Directions Target Family Matrix

## Purpose

This document turns the remaining primary-direction target families into an
explicit Moira policy surface.

It answers three questions:

1. which target families are already mathematically real in Moira
2. which families are deferred because their governing law is still
   method-specific or incomplete
3. which family should be next, if target work resumes


## Current Audit Rule

A target family is not considered live merely because the repo contains a
related mathematical substrate elsewhere.

For primary directions, a target family is only counted as live when it has:

1. explicit doctrine
2. explicit runtime realization
3. explicit policy or preset path
4. explicit validation


## Family Matrix

| Family | Current Directional Role | Governing Law Status | Moira Status | Notes |
| --- | --- | --- | --- | --- |
| `planets` | base promissors and significators | explicit | `implemented_validated` | sovereign baseline family |
| `nodes` | base promissors and significators | explicit | `implemented_validated` | limited to admitted node surface |
| `angles` | base promissors and significators | explicit | `implemented_validated` | central across current branches |
| `house cusps` | significators and explicit projected targets | explicit | `implemented_validated` | admitted as projected cusp entries |
| `zodiacal aspect-points` | derived promissors | explicit, relation-gated | `implemented_validated` | active on admitted zodiacal aspect branches |
| `parallels / contra-parallels` | relation-first branch | explicit across Ptolemaic and Placidian | `implemented_validated` | admitted on Ptolemaic declination and Placidian mundane reflection branches |
| `rapt parallels` | relation-first branch | explicit but method-bound | `implemented_validated_narrow_family` | closed for now on admitted Placidian branches |
| `fixed stars` | sovereign catalog-backed targets | explicit, conjunction-only | `implemented_validated_narrow_family` | angle/planet and explicitly configured typed-derived significators; nodes/cusps and wider stellar relations remain excluded |
| `antiscia / contra-antiscia` | reflected targets | explicit on the current narrow Ptolemaic zodiacal branch | `implemented_validated_narrow_family` | closed for now on the current recoverable Ptolemaic branch; wider non-Ptolemaic doctrine still deferred |
| `mundane aspects` | proportional semi-arc aspect points | explicit on Placidus and Ptolemy semi-arc branches | `implemented_validated` | admitted under `PLACIDUS_MUNDANE_ASPECT` and `PTOLEMY_MUNDANE_ASPECT` |
| `midpoints` | derived sensitive points (A/B) | shortest-arc circular midpoint perfection | `implemented_validated` | admitted across all 8 directional methods, direct/converse/neo-converse, and life timeline integration |
| `Fortune` | typed derived significator | explicit Ptolemaic or separately selected sect-reversed formula; zero ecliptic latitude | `implemented_validated_narrow_family` | opt-in across all eight methods and 28 presets; no Fortune promissor or derived-source admission |
| `existing predominator` | typed composition retaining selected identity | existing Ptolemy determination, checked against natal coordinates | `implemented_validated_narrow_family` | all eight methods; selected planet retains native latitude; ASC/Fortune remain explicit; unresolved office raises with original reason |
| `catalogue lots` | typed derived significators | existing lots recipes, projectors, arc/reversal and dependency policies | `implemented_validated_narrow_family` | all eight methods and 28 presets; zero ecliptic latitude; namespaced identity; selected batch evaluation; missing ingredients fail explicitly |
| `generic folklore stars` | loose named targets | no sovereign doctrine | `rejected` | violates provenance law |


## Current Mathematical Core

The currently closed and verified target families are:

- planets
- nodes
- angles
- house cusps
- zodiacal aspect-points
- parallels / contra-parallels (zodiacal declination and Placidian mundane reflections)
- rapt parallels on the admitted Placidian branches
- fixed stars on the admitted narrow conjunction branches
- antiscia / contra-antiscia on the admitted Ptolemaic branch
- mundane aspects (Placidus mundane and Ptolemaic proportional semi-arc)
- zodiacal midpoints across all 8 projection systems

These are bounded runtime admissions, not closure of every historical target
family. Fortune and existing-predominator composition now have an explicit
admission packet in `primary_directions_derived_points.md`.


## Remaining Research Candidates

Further target research includes established historical families as well as
new mathematical proposals:

- wider lot roles, other derived-point families and custom-formula admission,
  each requiring explicit source and latitude contracts
- broader Fortune/lot roles and source-based historical validation beyond the
  current mathematical significator composition
- a wider non-Ptolemaic reflected family only if a rigorous non-zodiacal antiscia doctrine appears
- 3D spatial skew-direction promissors outside standard semi-arc and quadrant systems


## Present Declaration

Moira validates the named admitted branches. The target inventory does not
establish completeness across all historical schools or mathematical branches.
