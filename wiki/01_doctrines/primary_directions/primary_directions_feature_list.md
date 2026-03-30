# Primary Directions Feature List

## Purpose

This document lists the current feature surface of Moira's primary-directions
subsystem in practical terms.

It is not a roadmap and not a research ledger.

It answers one question:

- what primary directions can Moira actually do now?


## Core Engine

- speculum construction for the admitted primary-direction families
- direct and traditional converse motion
- explicit branch selection through `PrimaryDirectionsPreset` and
  `primary_directions_policy_preset(...)`
- policy-aware runtime surfaces for method, space, relation, latitude, source,
  perfection, and targets
- symbolic time conversion through explicit key doctrine


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
  the equatorial family while its aspect branch is the clearest distinct
  surface


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

Not admitted:

- `Neo-converse`


## Time Keys

- `Ptolemy`
- `Naibod`
- `Cardan`
- `Solar`


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


## Explicit Omissions

Not currently admitted:

- `field_plane`
- `neo-converse`
- midpoint directions
- generic mundane aspects as a family
- fixed-star opposition
- wider non-Placidian parallel families
- wider non-Ptolemaic reflected doctrine


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
