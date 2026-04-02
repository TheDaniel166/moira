# Primary Directions Roadmap

## Purpose

This document defines the refactor and expansion roadmap for Moira's primary
directions subsystem.

The governing idea is simple:

- primary directions are a single mathematical family
- the currently implemented Placidus-mundane engine is only one narrow member of that family
- expansion should happen by constitutionalizing the subsystem first, then admitting
  new doctrinal variants through explicit truth domains

This is therefore a **refactor-first roadmap**, not an additive feature checklist.

This roadmap assumes the companion constitutional doctrine packet exists:

- [primary_directions_doctrine.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\01_doctrines\primary_directions\primary_directions_doctrine.md)
- [primary_directions_direction_space_doctrine.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\01_doctrines\primary_directions\primary_directions_direction_space_doctrine.md)
- [primary_directions_time_key_doctrine.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\01_doctrines\primary_directions\primary_directions_time_key_doctrine.md)
- [primary_directions_ambiguity_ledger.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\01_doctrines\primary_directions\primary_directions_ambiguity_ledger.md)
- [primary_directions_phase10_audit.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\06_roadmap\primary_directions\primary_directions_phase10_audit.md)
- [primary_directions_constitutional_alignment.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\06_roadmap\primary_directions\primary_directions_constitutional_alignment.md)
- [primary_directions_invariant_register.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\02_standards\primary_directions\primary_directions_invariant_register.md)
- [primary_directions_validation_codex.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\02_standards\primary_directions\primary_directions_validation_codex.md)


## Current Moira State

Current implementation file:

- `moira/primary_directions.py`
- `moira/primary_direction_geometry.py`

Current admitted capability:

- `8` runtime-admitted direction methods:
  - `Placidus mundane`
  - `Ptolemy / semi-arc`
  - `Placidian classic / semi-arc`
  - `Meridian`
  - `Morinus`
  - `Regiomontanus`
  - `Campanus`
  - `Topocentric`
- `2` direction spaces:
  - `In Mundo`
  - `In Zodiaco`
- `2` motion modes:
  - `Direct`
  - `Traditional converse`
- `4` time keys: `Ptolemy`, `Naibod`, `Cardan`, `Solar`
- explicit latitude doctrines:
  - `mundane_preserved`
  - `zodiacal_suppressed`
  - `zodiacal_promissor_retained`
  - `zodiacal_significator_conditioned`
- explicit latitude sources:
  - `promissor_native`
  - `assigned_zero`
  - `aspect_inherited`
  - `significator_native`
- explicit perfection kinds:
  - `mundane_position_perfection`
  - `zodiacal_longitude_perfection`
  - `zodiacal_projected_perfection`
- explicit target surface:
  - planets
  - nodes
  - angles
  - house cusps
  - explicit zodiacal aspect-point promissors
  - sovereign catalog-backed fixed-star promissors on the current
    fixture-backed angle-and-planet branch

Current constitutional status:

- top-level primary-directions branch:
  - constitutionally closed through `P12` on the current admitted recoverable
    surface
  - governing freeze packet:
    - [primary_directions_constitutional_alignment.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\06_roadmap\primary_directions\primary_directions_constitutional_alignment.md)
    - [primary_directions_invariant_register.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\02_standards\primary_directions\primary_directions_invariant_register.md)
    - [primary_directions_validation_codex.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\02_standards\primary_directions\primary_directions_validation_codex.md)
- major internal doctrine owners:
  - methods: through `P10`
  - keys: through `P10`
  - spaces: through `P10`
  - converse: through `P10`
  - relations: through `P10`
  - presets: through `P10`
  - targets: through `P10`
  - perfections: through `P10`
  - latitudes: through `P10`
  - latitude sources: through `P10`

Interpretation:

- the subsystem's baseline admitted surface is now frozen
- further work should be frontier research or explicit constitutional revision,
  not unfinished baseline closure

Current narrow branch notes:

- `Ptolemy / semi-arc` is admitted as an explicit narrow semi-arc branch
  - on the currently admitted runtime surface it uses explicit historical
    sub-laws:
    - `MC/IC` by `RA`
    - `ASC/DSC` by `OA/OD`
    - non-angular points by proportional semi-arcs
- `Meridian` is admitted as an explicit narrow equatorial branch
  - on the currently admitted runtime surface it perfects by equatorial
    right-ascension difference
- `Morinus` is admitted as an explicit narrow equatorial branch
  - on the currently admitted runtime surface it perfects by equatorial
    right-ascension difference
  - an explicit Morinian aspect-plane branch is now admitted when the service
    layer supplies the required path context (`delta_max`, motion sense, handed
    aspect)
  - the current doctrinal resolution is explicit:
    - aspectual Morinus distinctness is real
    - conjunction-style Morinus remains shared with the equatorial branch
      unless a source-safe distinct formula is recovered
- `Campanus` is admitted as an explicit narrow under-the-pole branch
  - on the currently admitted runtime surface it uses the verified shared
    Campanus-Regiomontanus speculum law
  - sharper Campanian divergence is still expected to emerge in wider mundane
    branches such as cusps, midpoints, and certain mundane aspects
- `Topocentric` is admitted as an explicit narrow under-the-pole branch
  - it uses its own pole law:
    - `tan(pole) = (MD / SA) * tan(latitude)`

Mathematical sovereignty status:

- sovereign runtime laws:
  - `Placidus mundane`
  - `Ptolemy / semi-arc`
  - `Placidian classic / semi-arc`
  - `Meridian`
  - `Regiomontanus`
  - `Campanus`
  - `Topocentric`
- shared narrow laws, not yet fully sovereign:
  - `Morinus`


Constitutional rule:

- a method is not treated as fully Phase-1-complete until it stands on its own
  explicit governing math


## Research Summary

The external references below were checked on `2026-03-29`.

Current external references show that mature primary-direction software treats
the domain as a combination of several independent axes, not as one monolithic
"method" toggle.

### AstroApp

AstroApp currently advertises:

- `11` primary-direction methods
- `25` time conversion keys
- `In Mundo`, `In Zodiaco`, and `Field Plane`
- `traditional converse` and `neo-converse`

Sources:

- `https://astroapp.com/en/astrology-software-all/astroapp-overview`
- `https://astroapp.com/help/1/returnsW_53.html`
- `https://astroapp.com/images/astroapp_booklet_final.pdf`

Methods explicitly advertised in their help/booklet material include:

1. `Placidus`
2. `Campanus (under the pole)`
3. `Regiomontanus (under the pole)`
4. `Meridian`
5. `Morinus`
6. `Porphyry`
7. `Alcabitius`
8. `Equal Houses (ecliptic)`
9. `Equal Houses (hour circle)`
10. `Edmund Jones`
11. `Along Ecliptic`

### Mastro

Mastro documents a smaller but still broader core than Moira currently has:

- `Ptolemy (semi-arc)`
- `Placidus (under the pole)`
- `Regiomontanus`
- `In Mundo`
- `In Zodiaco`
- `Direct`
- `Converse`
- keys such as `Ptolemy`, `Naibod`, `Cardan`

Source:

- `https://mastroapp.com/files/documentation_en.pdf`

### Astrodienst / AstroWiki

AstroWiki confirms the major doctrinal axes:

- domification / geometry method
- promissors and significators
- zodiacal vs mundane directions
- circle of aspects / aspect layout model
- static vs dynamic keys
- motion doctrine

Source:

- `https://www.astro.com/astrowiki/en/Primary_Directions`

### Halloran / Kolev Ecosystem

Halloran's software summaries and Kolev-related materials confirm that the wider
primary-directions tradition is commonly broken out by:

- Placidian classic / semi-arc
- under-the-pole variants
- Regiomontanus
- Campanus
- Topocentric
- zodiacal and mundane modes
- multiple key families

Sources:

- `https://www.halloran.com/placidus.htm`
- `https://www.halloran.com/allsoft.htm`


## Core Insight

Primary directions are best modeled not as a list of unrelated methods, but as a
family generated by a handful of mathematical and doctrinal axes.

That means expansion should not start with "add method #2".

It should start by making the truth domain explicit.

For this subsystem, accepted label does not override explicit doctrine.

So the roadmap is not "match every familiar menu label as quickly as possible."
It is:

- decompose the doctrine first
- admit only the explicit branch that can be defined and validated
- refuse to guess at missing mathematical law


## Truth Domain Axes

The subsystem should eventually formalize these axes explicitly.

### 1. Geometry Method

How the direction is geometrically constructed.

Examples:

- `Placidus mundane`
- `Placidian classic / semi-arc`
- `Regiomontanus`
- `Campanus`
- `Topocentric`
- `Morinus`
- `Porphyry`
- `Alcabitius`
- `Equal ecliptic`
- `Equal hour-circle`
- `Along ecliptic`

### 2. Direction Space

In which reference space the direction is performed.

Examples:

- `In Mundo`
- `In Zodiaco`
- `Field Plane`

### 3. Motion Doctrine

How the direction proceeds in temporal or motional logic.

Examples:

- `Direct`
- `Traditional converse`
- `Neo-converse`

### 4. Time Key Family

How arc is converted into time.

Families:

- `Static`
- `Dynamic`
- `Symbolic`

Examples:

- `Ptolemy`
- `Naibod`
- `Cardan`
- `Placidus`
- `Kepler`
- `Ascendant Arc`
- `Vertical Arc`
- `Symbolic Degree`
- `Symbolic Year`
- `Symbolic Month`

### 5. Target Doctrine

What may serve as promissors and significators.

Examples:

- planets
- nodes
- angles
- house cusps
- aspects
- fixed stars
- parallels / rapt parallels
- antiscia / reflections

### 6. Latitude / Projection Doctrine

How latitude and projection are handled.

Examples:

- true latitude respected
- latitude suppressed
- under-the-pole handling
- apparent vs true position choices
- lunar parallax handling


## Refactor Thesis

The subsystem should be rebuilt so that current Placidus-mundane behavior becomes
one specific doctrinal configuration inside a wider formal engine.

This means:

- not replacing the current engine
- not discarding validated arithmetic
- but lifting the current implementation into a typed doctrine framework

The correct mental model is:

- one `primary_directions` subsystem
- many admitted doctrinal variants inside it

Not:

- many separate mini-engines for each method


## Proposed Subsystem Architecture

### Phase A. Constitutional Refactor

Complete constitutional process for the current subsystem before expanding breadth.

Immediate goals:

1. finish `P3` inspectability
2. build `P4` doctrine/policy surface
3. build `P5-P6` explicit relation layers
4. build `P7-P9` local, aggregate, and network intelligence
5. build `P10-P12` hardening, backend standard, and API curation

### Phase B. Key Engine Extraction

Extract time-key conversion into its own formal doctrine layer.

Why first:

- keys are orthogonal to geometry method
- current `PrimaryArc.years()` string switch is too narrow
- many later expansions depend on a proper key surface

Target outputs:

- `PrimaryDirectionKeyFamily`
- `PrimaryDirectionKey`
- `PrimaryDirectionKeyPolicy`
- `PrimaryDirectionKeyTruth`
- `convert_arc_to_time(...)`

### Phase C. Direction Space Formalization

Separate:

- `In Mundo`
- `In Zodiaco`
- `Field Plane`

Current Moira should become:

- `method = placidus_mundane`
- `space = in_mundo`

### Phase D. Geometry Method Expansion

Add new methods one at a time under the refactored doctrine framework.

Recommended order:

1. `Placidian classic / semi-arc`
2. `Regiomontanus`
3. `In Zodiaco` support on the existing framework
4. `Campanus`
5. `Topocentric`
6. broader equal/ecliptic variants

This order is recommended because:

- it stays closest to the currently validated Moira math
- it covers the most historically central doctrinal branches first
- it yields broad capability gains without requiring all 11 methods immediately

### Phase E. Converse Doctrine

Current converse handling is mathematically simple but under-formalized.

Formalize:

- `Direct`
- `Traditional converse`
- `Neo-converse`

This should be an explicit doctrine axis, not a boolean flag.

### Phase F. Promissor / Significator Expansion

After method and space formalization:

- add aspects
- add house cusps explicitly
- add parallels / rapt parallels
- add fixed stars
- add other doctrinally supported point classes


## Build Order

This is the recommended build order for actual implementation work.

### Sequencing Rule

Before the **top-level primary-directions suite** enters final `P11` and `P12`
freeze, the major internal doctrine-owning subsystems should each reach `P10`.

Current internal subsystem sequence:

1. core primary-directions engine
2. primary-direction keys
3. primary-direction spaces
4. primary-direction converse doctrine
5. target-doctrine / promissor-significator admission layer

This means:

- working doctrine notes may exist early
- subsystem-local implementation and hardening may proceed independently
- the final top-level backend standard and final top-level public API curation
  should wait until those major internal owners are constitutionally stable

### Stage 1. Finish constitutional process for Current Engine

1. `P3` Inspectability
2. `P4` Policy surface
3. `P5` Relational formalization
4. `P6` Relational hardening
5. `P7` Local condition
6. `P8` Aggregate intelligence
7. `P9` Network intelligence
8. `P10` Full hardening
9. `P11` Backend standard
10. `P12` Public API curation

### Stage 2. Extract the Key Subsystem

11. formal key-family model
12. key conversion truth / classification / policy
13. validation for each admitted key

### Stage 3. Extract the Direction-Space Subsystem

14. formal direction-space truth / classification / policy layer
15. keep current admitted implementation narrow: `in_mundo`
16. defer `in_zodiaco` and `field_plane` admission until space doctrine reaches
    hardening maturity

### Stage 4. Add the Second Method

17. `Placidian classic / semi-arc`

Why this first:

- closest kin to current implementation
- historically central
- validates the geometry-method abstraction without immediately jumping families

Status:

- complete on a narrow admitted surface

### Stage 5. Add the Second Space

18. `In Zodiaco`

Why here:

- direction space is a more fundamental axis than the long method list
- adding only more `in mundo` methods leaves a major doctrinal gap unresolved

Status:

- complete on an explicit narrow admitted family:
  - `assigned_zero`
  - `promissor_native`
  - `aspect_inherited`
  - `zodiacal_longitude_perfection`
  - `zodiacal_projected_perfection`

### Stage 6. Add Regiomontanus

19. `Regiomontanus`

This is the next major historical branch and a meaningful divergence from the
Placidian family.

Status:

- admitted on a narrow explicit surface

### Stage 7. Add Converse Doctrine Proper

20. `Traditional converse`
21. `Neo-converse`

Status:

- `Traditional converse` admitted
- `Neo-converse` not yet implemented

### Stage 8. Widen the Method Catalog

22. `Campanus`
23. `Topocentric`
24. `Porphyry`
25. `Alcabitius`
26. `Morinus`
27. `Equal Houses (ecliptic)`
28. `Equal Houses (hour-circle)`
29. `Along Ecliptic`
30. `Edmund Jones`

### Stage 9. Promissor / Significator Expansion

31. aspects
32. parallels / rapt parallels
33. fixed stars
34. additional sensitive points

Status:

- explicit zodiacal aspect-point promissors admitted
- house cusps, fixed stars, parallels / rapt parallels, and wider reflected
  target families remain to be implemented


## Validation Strategy

This subsystem cannot be credibly expanded by code alone.

Each admitted doctrinal variant should have:

- unit invariants
- analytic edge-case tests
- historical worked-example fixtures where available
- software oracle comparison where appropriate

Recommended external comparison sources:

- AstroApp
- Mastro
- Kolev / Halloran Placidian and Regiomontanian examples
- published worked examples from Gansten / Houlding / Rusborn where reproducible

Validation principle:

- external software is an audit oracle, not a runtime dependency


## Why This Should Be Treated as a Refactor

Because otherwise the subsystem will become a switchboard:

- one boolean for converse
- one string for key
- one branch for Regiomontanus
- another branch for zodiacal
- another branch for Campanus

That path produces:

- weak doctrine visibility
- unclear invariants
- validation drift
- fragile public semantics

The better path is:

- refactor the subsystem into explicit doctrinal axes
- then admit new variants as combinations of those axes

That is how Moira can exceed the current software landscape:

- clearer doctrine than black-box tools
- more inspectable truth than menu-driven software
- stronger validation story than "software X also says so"


## Recommended Immediate Path Forward

Do **not** guess at `field_plane` or other composite labels.

Do this next:

1. preserve and document the current explicit branches:
   - `in_mundo`
   - `in_zodiaco` + `assigned_zero`
   - `in_zodiaco` + `promissor_native`
   - `in_zodiaco` + `aspect_inherited`
   - `in_zodiaco` + `significator_native`
   - named `PrimaryDirectionsPreset` selectors for the documented live surfaces
2. pause geometry-family widening unless a new formula-grade source appears
3. mature orthogonal subsystems in this order:
   - more time keys
   - more target families
   - more worked-example validation fixtures
4. postpone any standalone `field_plane` runtime space until its law is explicit

Current next practical candidates:

- `Cardan` as the next explicit time key
- fixed stars after target doctrine and validation plans are written tightly
  enough
- first narrow parallel branch now admitted only on the Ptolemaic zodiacal
  surface through explicit declination-equivalence targets
- direct Placidian mundane rapt parallels are now admitted as an explicit
  direct-only branch
- converse Placidian mundane rapt parallels are now also admitted as an
  explicit converse-only branch
- wider non-Placidian parallel families still require additional
  method-specific governing laws
- the governing branch policy for the wider parallel family now lives in:
  - [primary_directions_parallel_family_matrix.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_parallel_family_matrix.md)
- the governing branch policy for fixed stars now lives in:
  - [primary_directions_fixed_star_family_matrix.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_fixed_star_family_matrix.md)
- the governing target-family audit now lives in:
  - [primary_directions_target_family_matrix.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_target_family_matrix.md)
- the first reflected-family truth card now lives in:
  - [primary_directions_truth_card_antiscia.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\01_doctrines\primary_directions\primary_directions_truth_card_antiscia.md)
- the remaining-frontier governance packet now lives in:
  - [remaining_primary_directions_frontiers.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\remaining_primary_directions_frontiers.md)
- the dedicated `neo-converse` research packet now lives in:
  - [primary_directions_neo_converse_research.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_neo_converse_research.md)
- the dedicated midpoint research packet now lives in:
  - [primary_directions_midpoint_family_matrix.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_midpoint_family_matrix.md)

Current branch-selection surface:

- callers may now select documented runtime branches through
  `PrimaryDirectionsPreset` + `primary_directions_policy_preset(...)`
- this keeps branch identity visible instead of rebuilding it ad hoc from
  low-level policy parts


## Research Sources

- AstroApp overview: `https://astroapp.com/en/astrology-software-all/astroapp-overview`
- AstroApp primary directions help: `https://astroapp.com/help/1/returnsW_53.html`
- AstroApp booklet: `https://astroapp.com/images/astroapp_booklet_final.pdf`
- Mastro manual: `https://mastroapp.com/files/documentation_en.pdf`
- Astrodienst AstroWiki: `https://www.astro.com/astrowiki/en/Primary_Directions`
- Halloran / Kolev software summary: `https://www.halloran.com/placidus.htm`
- Halloran software index: `https://www.halloran.com/allsoft.htm`

