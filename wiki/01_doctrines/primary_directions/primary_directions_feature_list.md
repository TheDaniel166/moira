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
- catalog-backed fixed-star conjunctions to angles and planets
- Ptolemaic zodiacal antiscia / contra-antiscia
- Egyptian, Ptolemaic, and Chaldean term/bound boundaries for timeline
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


## Explicit Omissions

Not currently admitted:

- `field_plane`
- fixed-star opposition
- wider non-Placidian parallel families
- wider non-Ptolemaic reflected doctrine
- wider mundane-aspect laws outside the admitted Placidian and Ptolemaic
  branches
- wider midpoint doctrine beyond the admitted shortest-arc target construction


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

