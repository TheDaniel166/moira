# Asteroid Families And Subsets Backend Standard

Version: 0.2
Date: 2026-07-01
Status: admitted backend standard for Phase 11 REST transport

## Scope

This standard governs Moira's asteroid subset and dynamical-family surfaces:

- `moira.classical_asteroids`
- `moira.main_belt`
- `moira.centaurs`
- `moira.tno`
- `moira.asteroid_families`

It does not govern the core asteroid position engine itself. Selected asteroid
position transport is governed by `moira.asteroids` and the P11-04 asteroid REST
admission.

## Authority Layers

Named asteroid subsets are curated Moira identity groupings over bodies already
present in `ASTEROID_NAIF`.

The dynamical-family layer is a catalog lookup over MPC asteroid numbers from:

- Nesvorny, D. et al. 2015
- NASA PDS `ast.nesvorny.families` V2.0
- bundled dataset: `moira/data/asteroid_families.csv`

The two surfaces must not be collapsed:

- Subset routes use asteroid names and NAIF IDs.
- Family routes use MPC catalog numbers and Nesvorny family names.

## Governing Objects

Named subset surfaces govern stable curated identity sets:

- classical asteroids: Ceres, Pallas, Juno, Vesta
- main-belt subset: the named Moira main-belt body set
- centaurs: the named Moira centaur body set
- TNOs: the named Moira trans-Neptunian body set

Dynamical-family surfaces govern catalog membership:

- one asteroid number to one family name, or no family
- one family name to bounded MPC-number membership
- one supplied chart list to grouped family membership
- one supplied chart asteroid set to a family-qualified aspect network

Family membership is physical-origin catalog truth. It is not a zodiacal,
aspectual, house, or interpretive grouping.

## Required Transport Invariants

REST transport must preserve:

- subset slug
- subset source module
- subset catalog source
- asteroid name and NAIF ID for subset routes
- loaded-kernel availability by NAIF ID when exposed
- MPC catalog number semantics for family routes
- Nesvorny/PDS provenance for family routes
- bounded list/member output
- chart resonance nodes, edges, and per-family network buckets when requested
- explicit stage sequence

REST transport must not:

- infer dynamical family membership from asteroid names alone
- silently convert MPC numbers into NAIF IDs
- treat family membership as a position computation
- treat subset membership as proof of loaded-kernel availability
- expose unbounded 143k-member catalog sweeps
- claim photometry, topocentric position, or rendered-map support

## Admitted Family Surfaces

The backend supports three low-risk family catalog views:

- lookup family by MPC number
- list members of a named family with offset/limit bounds
- group a supplied list of MPC numbers by family

The backend also supports one bounded chart resonance-network view:

- compute positions for explicitly requested asteroid bodies or MPC numbers
- detect admitted ecliptic aspects with `moira.aspects.find_aspects`
- filter those aspects through `find_resonant_aspects(...)`
- group them through `resonance_network(...)`

This route must expose the resolved asteroid node identities, the full aspect
admission vessel for each resonant edge, the shared Nesvorny family qualifier,
and the per-family network buckets. It must not turn resonance into an
interpretive score or family-wide catalog sweep.

## Admitted Subset Surfaces

The backend supports three low-risk subset views:

- list admitted subset registries
- list/search members of one subset with loaded-kernel truth
- compute positions for all or selected members of one subset by delegating to
  the admitted asteroid position transport

The subset position surface is convenience transport. It does not create a new
position doctrine.

## Validation Requirements

Transport admission must verify:

- unknown subset slugs are rejected
- list/member limits are bounded
- subset position datetimes are timezone-aware
- subset position body entries are non-empty
- out-of-subset bodies are reported as missing when `skip_missing=true`
- family-number inputs are positive MPC catalog numbers
- chart-grouping inputs are non-empty, positive, and bounded
- resonance-network inputs provide exactly one identity source: `bodies` or
  `numbers`
- resonance-network `numbers` are positive MPC catalog numbers
- resonance-network `bodies` are asteroid names or small-body NAIF IDs, not
  MPC catalog numbers
- resonance-network aspect policy inputs are bounded to the admitted
  `find_aspects` tier/orb-factor surface
- live catalog distinctions are preserved, including distinct Nesvorny family
  names such as `Koronis`, `Koronis(2)`, and `Karin`

## Non-Goals

This standard does not admit:

- asteroid-family position sweeps
- rendered family maps
- family astrocartography
- photometry
- topocentric or equatorial asteroid subset products
- kernel build or manifest-management routes
- edits to the bundled Nesvorny/PDS catalog
