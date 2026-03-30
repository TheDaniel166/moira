# Primary Directions Fixed Star Family Matrix

## Purpose

This document turns the fixed-star question in primary directions into explicit
Moira policy.

It does not assume that "fixed stars" are one uniform directional family.
It classifies the recoverable fixed-star branches by:

- target ontology
- geometry family
- relation scope
- governing law status
- source quality
- Moira policy status
- next action


## Governing Policy

### Constitutional Rule

In primary directions, a fixed star is admitted first as a **target identity**,
not as an interpretive folklore label.

That means Moira requires:

- catalog-backed star identity
- explicit coordinate provenance
- a clear projection into the active directional geometry
- a narrow admitted relation surface

### Source Rule

For a fixed-star branch to be admitted, Moira requires:

1. a source-safe star identity
2. an explicit coordinate/projection law
3. an explicit relation law
4. validation material strong enough to test

If one of these is missing, the branch is deferred.


## Existing Moira Substrate

Moira already has unusually strong fixed-star substrate compared with the
current primary-directions layer.

The existing star engine provides:

- sovereign registry-backed star identity in [stars.py](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
- local data provenance in:
  - [star_registry.csv](c:/Users/nilad/OneDrive/Desktop/Moira/moira/data/star_registry.csv)
  - [star_lore.json](c:/Users/nilad/OneDrive/Desktop/Moira/moira/data/star_lore.json)
  - [star_provenance.json](c:/Users/nilad/OneDrive/Desktop/Moira/moira/data/star_provenance.json)
- geocentric true-position computation through `star_at(...)`
- catalog listing and name-resolution helpers:
  - `list_stars()`
  - `list_named_stars()`
  - `star_name_resolves()`

So the fixed-star problem in primary directions is **not** star identity.
It is the directional doctrine layered on top of an already strong star
substrate.


## Branch Matrix

| Branch | Target Ontology | Geometry Family | Relation Surface | Governing Law in Hand | Source Quality | Moira Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `catalog-backed fixed star conjunction to angles` | named sovereign star target | cross-family, starting with currently admitted methods | `conjunction` | **Yes, narrowly**. Compute the star's true geocentric longitude/latitude by `star_at(...)`, project it into the active speculum like any other explicit point, then measure the arc by the chosen method's existing conjunction law | strong enough for narrow admission | `implemented_validated_branch` | widen to planet significators only after keeping the same sovereign target discipline |
| `catalog-backed fixed star conjunction to planets` | named sovereign star target | cross-family, starting narrowly | `conjunction` | **Yes, narrowly**. Same as above, but with planet significators instead of angles | moderate-to-strong | `implemented_validated_branch` | keep the branch narrow and defer opposition/aspect widening |
| `catalog-backed fixed star opposition` | named sovereign star target | cross-family | `opposition` | **Partially**. The geometrical endpoint is explicit, but historical importance appears much weaker than conjunction, and source practice is less central | moderate | `deferred_narrowly` | admit only after conjunction branch proves stable |
| `fixed stars as zodiacal aspect targets` | named sovereign star target plus aspect doctrine | `in_zodiaco` families | `zodiacal_aspect` | **Not yet as a family**. The star point itself is explicit, but the wider aspect doctrine should not be admitted before the plain conjunction surface is proven | weak-to-moderate | `deferred` | do not widen until conjunction branch is validated |
| `fixed stars in mundo / projected mundane stars` | named sovereign star target | `in_mundo` families | likely `conjunction` first | **Partially**. The star engine gives longitude/latitude, and the primary engine can project explicit points, but the exact mundane-star doctrine must be stated carefully per method | moderate | `research_candidate` | start with simple projected speculum treatment only if branch scope remains narrow |
| `fixed stars by election-style ASC/MC contact` | named sovereign star target | angle-directed family | `conjunction` to `ASC/MC` | **Yes, conceptually**. Current software ecosystems clearly use exact star-to-angle conjunction logic, but this is better treated as supporting evidence for the angle-conjunction branch than as a separate primary-direction family | moderate | `supporting_pattern` | use as supporting doctrine, not a separate first implementation |
| `fixed stars as generic folklore targets` | star names without sovereign identity/provenance discipline | none | any | **No**. This violates Moira's provenance law | strong enough to reject | `rejected` | keep rejected |


## Concrete Moira Policy

### Declared Implementable First

The first fixed-star branch Moira should implement is:

- `catalog-backed fixed star conjunction to angles`

This branch is now admitted narrowly in runtime.

Why:

- star identity and projection substrate already exist
- conjunction is the cleanest relation surface
- angles are the most defensible first significators
- this avoids opening a broad star-aspect doctrine too early

### Declared Implementable Second

After the first branch validates cleanly:

- `catalog-backed fixed star conjunction to planets`

This branch is now admitted narrowly in runtime and fixture-backed.

Why:

- it uses the same star target ontology
- it still stays inside the simplest relation surface
- it widens target participation without changing star identity doctrine

### Declared Deferred

These remain deferred:

- fixed-star opposition
- fixed-star zodiacal aspect doctrine
- wider mundane-star families

Reason:

- the coordinate substrate is explicit
- the broader directional doctrine is not yet the best next admission

### Declared Rejected

This remains rejected:

- consumer-facing fixed-star support without sovereign catalog identity and
  provenance


## Implementation Order

The fixed-star family should proceed in this order:

1. admit catalog-backed fixed stars as a primary-direction target identity
2. implement conjunction to angles
3. validate the branch with catalog-backed fixture examples
4. implement conjunction to planets
5. reassess whether opposition or wider star doctrine is actually warranted

Current standing:

- steps `1`, `2`, `3`, and `4` are complete on the current admitted branch
- step `5` is next

The stop rule is explicit:

- if the next branch adds folklore faster than math, stop


## Mathematical Notes

### Star Identity and Coordinates

The fixed-star coordinate law already exists in Moira:

1. resolve a star name through the sovereign registry
2. compute its true geocentric longitude/latitude at `jd_tt`
3. treat that explicit point as the star's directional location

This is much stronger than most software simply because the identity and
provenance layers are already explicit.

### Primary-Direction Realization

The narrow first realization should be:

1. compute the natal fixed-star point with `star_at(...)`
2. project that point into the active primary-direction speculum
3. measure conjunction arc to `ASC`, `MC`, `DSC`, or `IC` through the method's
   existing conjunction law

This keeps the first fixed-star branch fully inside already admitted geometry.


## Sources Used

### Strongest Current Sources

- Moira sovereign fixed-star engine and registry:
  - [stars.py](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
  - [star_registry.csv](c:/Users/nilad/OneDrive/Desktop/Moira/moira/data/star_registry.csv)
  - [star_provenance.json](c:/Users/nilad/OneDrive/Desktop/Moira/moira/data/star_provenance.json)
- Astrodienst Astrowiki, `Fixed Star`:
  emphasizes that fixed stars are usually treated primarily by conjunction,
  especially to luminaries and angles, with very small orbs
  `https://www.astro.com/astrowiki/en/Fixed_Star`
- Halloran / Kolev software summary:
  confirms that mature primary-direction software ecosystems do expose
  directions involving stars and the wider celestial sphere, though software
  presence is supporting evidence rather than a governing law
  `https://www.halloran.com/placidus.htm`
- AstroApp booklet / forecasting overview:
  confirms that fixed stars are treated as a live predictive family in current
  software ecosystems
  `https://astroapp.com/images/astroapp_booklet_final.pdf`
  `https://astroapp.com/de/forecast-tools-15`

### Supporting Evidence

- AstroApp fixed-star elections:
  supports the angle-conjunction pattern (`ASC/MC conjunction`) as a modern
  operational use of stars that matches the narrow branch Moira should admit
  first
  `https://astroapp.com/help/1/returnsW_48.html`


## Present Declaration

Moira now has a concrete fixed-star family policy:

- fixed stars should enter as catalog-backed target identities
- the first runtime branch is conjunction to angles
- the second runtime branch is conjunction to planets
- wider star doctrine remains deferred until the narrow branch is validated
