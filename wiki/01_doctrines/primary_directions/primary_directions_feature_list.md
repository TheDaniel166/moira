# Primary Directions Feature List

## Purpose

This document lists the current feature surface of Moira's primary-directions
subsystem in practical terms.

It is not a roadmap and not a research ledger.

It answers one question:

- what primary directions can Moira actually do now?


## Core Engine

- speculum construction for the admitted primary-direction families
- direct, traditional role-exchanged converse, opt-in neo-converse, and the
  narrow Topocentric signed-primary-motion classifier
- explicit branch selection through `PrimaryDirectionsPreset` and
  `primary_directions_policy_preset(...)`
- policy-aware runtime surfaces for method, space, relation, latitude, source,
  perfection, and targets
- symbolic time conversion through explicit static or dynamic key doctrine
- integrated chronological timelines with terms/bounds, distributors, and
  participators

Term targets and distributor segments use the selected bounds owner's table,
including Lilly's printed terms. Direct crossings enter the segment beginning
at the boundary; converse crossings enter the preceding segment, including
the Pisces/Aries wrap and an exact natal boundary. Chronological intervals
remain distinct even when a ruler or bound identity repeats.

Timeline event filters do not remove the structural bound crossings used by
distributor chronology. Supplied bound targets must match the complete canonical
table selected by `bound_doctrine`; mixed, partial or conflicting tables are
rejected. Relation-specific direct/converse rapt events use the matching motion
of the existing ordinary bound law. Configured direct fixed-star events retain
their own direct chronology. Missing converse context never borrows a direct
period.

Automatic timeline horizons use the selected key's forward law, including
ephemeris solar progress for dynamic keys. Automatic requests beyond one
primary rotation are rejected; an explicit `max_arc` remains the caller's
bounded search domain. Requested coordinate dependencies are materialized before
semi-arc checks, so an unrelated circumpolar object cannot invalidate a valid
filtered pair. A requested object with no real semi-arcs still fails closed.

Direction calculations and returned Julian dates use UT1; calendar strings use
the engine's UTC conversion. Facade `Chart` snapshots carry civil UTC in their
legacy `jd_ut` field and are normalized internally. Explicit UT1/TT direction
snapshots keep their declared clocks, and TT-only fixed-star snapshots remain
supported. Delta-T is applied only to UT1, never added to civil UTC.

Meridian and the admitted under-the-pole methods retain their existing
circumpolar allowance through derived targets and timeline assembly. This does
not supply rise/set semi-arcs where none exist, or relax the requirements of
semi-arc methods or the standalone semi-arc speculum endpoint.


## Geometry Families

Runtime-admitted methods:

- `Placidus mundane`
- `Ptolemy / semi-arc`
- `Placidian classic / semi-arc`
- `Meridian`
- `Morinus`
- `Regiomontanus`
- `Campanus`
- `Topocentric`

Important qualifier:

- `Morinus` is admitted, but its conjunction-style branch remains shared with
  the Regiomontanus under-the-pole law while its aspect branch is the clearest
  distinct surface


## Direction Spaces

- `In Mundo`
- `In Zodiaco`

Explicit zodiacal latitude branches:

- `zodiacal_suppressed`
- `zodiacal_promissor_retained`
- `zodiacal_significator_conditioned`


## Motion Doctrine

- `Direct`
- `Traditional converse`
- `Neo-converse`, as an explicit opt-in counter-diurnal circle-complement law
- `Signed primary motion`, only through
  `topocentric_zodiacal_aspect_signed_primary_motion` with explicit target
  filters


## Time Keys

- `Ptolemy`
- `Naibod`
- `Cardan`
- `Solar`, using an explicit natal solar rate
- `Solar RA dynamic`, using ephemeris inversion in right ascension
- `Solar longitude dynamic`, using ephemeris inversion in ecliptic longitude

Dynamic keys require a natal Julian date and usable planetary reader. Inversion
failure raises; it is never relabeled while silently using a static rate.


## Perfection and Relation Doctrine

Perfection kinds:

- `mundane_position_perfection`
- `zodiacal_longitude_perfection`
- `zodiacal_projected_perfection`

Relation classes now explicit in the subsystem:

- `conjunction`
- `opposition`
- `zodiacal_aspect`
- `parallel`
- `contra_parallel`
- `rapt_parallel`
- `antiscion`
- `contra_antiscion`
- `term_bound`
- `mundane_aspect`
- `mundane_parallel`
- `mundane_contra_parallel`
- `midpoint`


## Promissors and Significators

Base target families:

- planets
- nodes
- angles
- house cusps

Derived or narrow admitted families:

- zodiacal aspect-point promissors
- Ptolemaic zodiacal parallels / contra-parallels
- Placidian direct and converse rapt parallels
- catalog-backed fixed-star conjunctions to angles, planets and explicitly
  configured typed derived significators
- Ptolemaic zodiacal antiscia / contra-antiscia
- Egyptian, Ptolemaic, Chaldean day/night, and William Lilly 1647 term/bound boundaries for timeline
  chronology
- method-scoped Placidian and Ptolemaic mundane aspect points
- Placidian mundane parallels / contra-parallels
- shortest-arc circular midpoint promissors


## Fixed Stars

Current admitted fixed-star branch:

- sovereign catalog-backed star identity
- explicit star projection through the active speculum
- conjunction to angles
- conjunction to planets
- conjunction to explicitly configured typed Fortune/lot significators

Deferred:

- opposition
- wider star aspects
- broader star doctrine


## Reflected Families

Current admitted reflected branch:

- `Ptolemaic zodiacal antiscia / contra-antiscia`

Deferred:

- non-Ptolemaic reflected doctrine
- broader reflected-family widening


## Validation Surface

The subsystem now includes:

- unit invariants
- targeted numerical proofs
- branch-specific fixture-backed validation on the narrow recoverable families
- curated public API checks

Validated narrow families include:

- Ptolemaic parallels
- Placidian rapt parallels
- fixed stars
- antiscia / contra-antiscia
- term/bound distributor chronology
- Placidian and Ptolemaic mundane aspects
- Placidian mundane parallels / contra-parallels
- shortest-arc midpoint targets
- neo-converse and dynamic solar-key invariants


## Typed Fortune and existing predominator

The engine admits opt-in typed Fortune significators across all eight existing
methods and 28 presets, with separate Ptolemaic and sect-reversed formula choices. The
Ptolemaic formula remains unreversed at night. An existing selected Ptolemy
predominator can be composed as a typed target, preserving planet/ASC/Fortune
identity and native planetary latitude; unresolved determinations keep their
original reason and do not select a fallback.

Typed targets retain coordinate-source checks through the complete bound
chronology and all six time keys. No arbitrary point coordinates or new REST
fields are admitted. Scope, examples, source binding and validation limits are
in `wiki/05_research/primary_directions/primary_directions_derived_points.md`.

Catalogue lots now use the same typed system through
`PrimaryDirectionLotTarget`. Existing formula variants, projectors, shortest
arcs, sect reversal and dependency policy remain with the lots owner. Targets
are evaluated from the current figure in context-specific batches and retain
complete bound chronology under all six keys. Roles remain significators with
zero ecliptic latitude. Method-specific space, motion and domain restrictions
remain explicit. See
`wiki/05_research/primary_directions/primary_directions_catalogue_lots.md`.
The cross-method contract is in
`wiki/05_research/primary_directions/primary_directions_derived_method_admission.md`.

## Explicit Omissions

Not currently admitted:

- `field_plane`
- fixed-star opposition
- wider non-Placidian parallel families
- wider non-Ptolemaic reflected doctrine
- wider mundane-aspect laws outside the admitted Placidian and Ptolemaic
  branches
- wider midpoint doctrine beyond the admitted shortest-arc target construction
- arbitrary custom formulas or custom derived points
- Fortune/lot promissors, Fortune/lot-derived aspect/reflection/parallel/midpoint
  sources


## Present Summary

Moira's primary-directions subsystem now provides:

- a broad and mathematically explicit core
- multiple geometry families
- explicit doctrine surfaces
- narrow validated target-family expansions

The subsystem is baseline-complete on the currently recoverable doctrinal
surface.

The remaining work is mostly:

- carefully governed frontier research
- or explicit constitutional revision if the admitted surface changes

