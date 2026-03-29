# Primary Directions Doctrine

## Purpose

This document defines the pre-SCP doctrine layer for Moira's primary-directions
subsystem.

It exists because primary directions are not a single settled technique. They
are a doctrinal family with substantial historical and mathematical ambiguity.

Before Moira expands its implementation breadth, it must state clearly:

- what primary directions are based on
- what each major method family is mathematically doing
- what each method family claims interpretively
- where the historical tradition is ambiguous
- what Moira should admit, defer, or reject

This document is therefore **pre-Phase-1 constitutional work**. It is not an
API contract and not yet a backend standard.


## Foundational Thesis

Primary directions are based on the apparent daily rotation of the celestial
sphere.

Their common logic is:

1. a promissor is moved by primary motion
2. a significator defines a target relation
3. the arc required for perfection is measured
4. that arc is converted into life-time by a key

Everything beyond that common substrate is doctrinal variation.


## Shared Mathematical Foundations

Across the historical family, primary directions generally presuppose:

- a natal astronomical figure
- a promissor
- a significator
- a directional relation between them
- a directional arc
- a time key converting arc to years, months, or other symbolic time

The major mathematical questions are:

1. What exactly is being moved?
2. In what space is it being moved?
3. What target relation counts as perfection?
4. How is latitude treated?
5. How is converse motion defined?
6. How is arc converted into time?


## Shared Interpretive Foundations

Primary directions are traditionally treated as perfection-based timing
techniques.

The common interpretive claim is:

- when the promissor perfects its directed relation to the significator, a
  corresponding period, event, condition, or activation is indicated in life

The exact meaning depends on:

- what the promissor signifies
- what the significator signifies
- what relation perfects
- what doctrine governs that method

So interpretation is not separable from the mathematical construction. Different
constructions imply different kinds of meaning.


## Core Doctrinal Axes

These are the major axes Moira should formalize before widening implementation.

### 1. Geometry Method

This answers:

- how the directional arc is constructed geometrically

Examples:

- Placidus mundane
- Placidian classic / semi-arc
- Regiomontanus
- Campanus
- Topocentric
- Morinus
- Porphyry
- Alcabitius
- Along Ecliptic

Interpretive implication:

- the geometry chosen defines what kind of perfection is being treated as
  meaningful

### 2. Direction Space

This answers:

- where the directional relation lives

Known families:

- `In Mundo`
- `In Zodiaco`
- `Field Plane`

Interpretive implication:

- `In Mundo` emphasizes actual bodily placement in the rotating sphere
- `In Zodiaco` emphasizes zodiacal relations and sign-based aspectual logic
- `Field Plane` appears to treat zodiacal points with latitude-bearing or
  latitude-conditioned projection, but the doctrine is historically ambiguous

### 3. Motion Doctrine

This answers:

- how direct and converse motion are defined

Known families:

- `Direct`
- `Traditional converse`
- `Neo-converse`

Interpretive implication:

- converse is not merely a software toggle; it changes how the symbolic
  direction of perfection is understood

### 4. Time Key Doctrine

This answers:

- how measured arc is converted into time

Known families:

- static keys
- dynamic keys
- symbolic keys

Interpretive implication:

- the key does not change the geometry of the direction
- it changes the temporal doctrine of manifestation

### 5. Target Doctrine

This answers:

- what may serve as promissors and significators

Known classes:

- planets
- nodes
- angles
- house cusps
- fixed stars
- zodiacal aspects
- mundane aspects
- parallels / rapt parallels
- antiscia / contra-antiscia

Interpretive implication:

- what a system admits as a valid target is part of the doctrine, not a minor
  option

### 6. Latitude / Projection Doctrine

This answers:

- whether and how latitude is retained, suppressed, projected, or assigned

Interpretive implication:

- many disputes in primary directions are actually disputes about latitude and
  projection, not about the abstract idea of directions itself


## Method Families

The following are the major families Moira should recognize doctrinally.

They are not yet implementation commitments.

### A. Mundane Directions

#### Mathematical Basis

- the actual body or point is treated in the rotating celestial sphere
- perfection is measured mundanely, not merely by zodiacal longitude
- house circles, semi-arcs, declination, and right ascension are central

#### Interpretive Meaning

- events arise from the perfected relation of actual celestial placement and
  bodily presence in the world-frame
- this is usually considered the most concrete or physically grounded family

#### Historical Standing

- strongly attested
- central to the traditional literature

#### Doctrinal Notes

- conjunctions and oppositions between bodies are historically native here
- wider aspect doctrine is more disputed

### B. Zodiacal Directions

#### Mathematical Basis

- the promissor is treated as a zodiacal point
- perfection is measured in zodiacal relation rather than only in bodily sphere
- longitude and zodiacal aspect structure become primary

#### Interpretive Meaning

- events arise from perfected zodiacal relationship, often closer to sign and
  aspect symbolism than to bodily mundane contact

#### Historical Standing

- strongly attested, but implemented differently across traditions

#### Doctrinal Notes

- one major ambiguity is whether zodiacal points are treated with latitude zero
  or with some retained/assigned latitude

### C. Field-Plane Directions

#### Mathematical Basis

- best understood as a latitude-bearing or latitude-conditioned zodiacal
  direction family
- neither purely mundane nor purely zero-latitude zodiacal
- often connected to zodiacal aspects directed with non-zero latitude or
  latitude rules

#### Interpretive Meaning

- likely intended to preserve zodiacal aspect meaning while retaining a more
  embodied or spatially conditioned relation than plain longitude alone

#### Historical Standing

- real as a family label in later software and in retrospective historical
  discussion
- not cleanly standardized

#### Doctrinal Notes

- this is currently one of the largest ambiguity zones
- Moira should not implement `field_plane` as a single opaque mode
- it should eventually be decomposed into explicit sub-doctrines:
  - latitude source
  - projection rule
  - aspect latitude rule
  - relation measurement rule


## Geometry Families

These are the major geometric lineages Moira is likely to encounter.

### Placidus Mundane

#### Mathematical Basis

- directions are constructed through the Placidian mundane framework now
  implemented in Moira
- the current engine uses right ascension, declination, semi-arc structure,
  mundane fraction, and directional arc

#### Interpretive Meaning

- perfection of mundane relation within the Placidian framework

#### Standing in Moira

- already implemented
- presently the only admitted method

### Placidian Classic / Semi-Arc

#### Mathematical Basis

- historically central Placidian family using semi-arc logic
- closely related to the existing Moira implementation, but not identical to
  the present narrowed engine

#### Interpretive Meaning

- still fundamentally mundane, but with broader traditional Placidian doctrine

#### Standing in Moira

- likely the best second method to admit

### Regiomontanus

#### Mathematical Basis

- directions are constructed through house circles and under-the-pole logic
- significantly different from Placidian construction

#### Interpretive Meaning

- perfected relation under a Regiomontanian spatial doctrine

#### Standing in Moira

- historically central
- a major branch, not a minor variant

### Campanus / Topocentric / Other Under-the-Pole Families

#### Mathematical Basis

- share some structural kinship as under-the-pole or alternate house-circle
  families
- differ in how the pole and derived chart quantities are defined

#### Interpretive Meaning

- similar perfection logic, but through a different geometrical doctrine

#### Standing in Moira

- later-stage admissions after Placidian and Regiomontanian branches are
  constitutionalized

### Along Ecliptic and Equalized Families

#### Mathematical Basis

- simplify or reframe direction by using ecliptic or equal-house style
  structures

#### Interpretive Meaning

- generally more schematic and less sphere-native than mundane families

#### Standing in Moira

- lower priority than the historically central branches


## Ambiguity Registry

These are the major ambiguity zones Moira must track explicitly.

### 1. Field Plane

Ambiguity:

- not one universally defined method
- often used as a label for latitude-bearing zodiacal aspectual directions

Moira stance:

- treat as a doctrine family, not a single method toggle

### 2. Zodiacal Aspects with Latitude

Ambiguity:

- some traditions suppress latitude
- others assign or retain latitude to aspectual points

Moira stance:

- treat latitude treatment as explicit doctrine, not an ambient default

### 3. Converse Doctrine

Ambiguity:

- traditional converse and neo-converse are not the same

Moira stance:

- treat converse doctrine as a first-class axis

### 4. Promissor / Significator Scope

Ambiguity:

- historical systems differ on what targets are admitted

Moira stance:

- define admissible target classes per method family

### 5. Apparent vs True Position

Ambiguity:

- different software may expose or hide these assumptions

Moira stance:

- keep policy explicit

### 6. Historical vs Modern Experimental Extensions

Ambiguity:

- some modern software expands directions beyond what was historically
  practiced

Moira stance:

- separate historically attested doctrine from modern experimental extensions


## Admission Categories

Moira should classify primary-direction doctrines into these buckets.

### Historically Attested

- clearly documented in traditional or early modern practice

### Historically Grounded Reconstruction

- not directly preserved as a turnkey modern procedure, but reconstructible from
  doctrine and sources

### Modern Software-Conventional

- real in contemporary software ecosystems, but not clearly identical with a
  stable historical doctrine

### Experimental / Research

- mathematically coherent, but interpretively or historically unsettled

### Rejected

- too ambiguous, internally incoherent, or insufficiently documented for
  admission


## Moira Policy Before Expansion

Before implementing additional primary-direction capabilities, Moira should:

1. define each admitted method in both mathematical and interpretive terms
2. classify each method by historical/doctrinal standing
3. expose ambiguity rather than hiding it
4. treat direction space as a decomposed truth domain, not a menu label
5. keep time keys orthogonal to geometry method
6. distinguish historical doctrine from experimental research


## Doctrine Packet Produced

The first pre-SCP doctrine packet now exists in the following companion
documents:

1. [primary_directions_truth_card_placidus_mundane.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_truth_card_placidus_mundane.md)
2. [primary_directions_truth_card_placidian_classic_semi_arc.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_truth_card_placidian_classic_semi_arc.md)
3. [primary_directions_truth_card_regiomontanus.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_truth_card_regiomontanus.md)
4. [primary_directions_truth_card_zodiacal_directions.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_truth_card_zodiacal_directions.md)
5. [primary_directions_truth_card_field_plane_directions.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_truth_card_field_plane_directions.md)
6. [primary_directions_direction_space_doctrine.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_direction_space_doctrine.md)
7. [primary_directions_time_key_doctrine.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_time_key_doctrine.md)
8. [primary_directions_ambiguity_ledger.md](c:/Users/nilad/OneDrive/Desktop/Moira/primary_directions_ambiguity_ledger.md)

Only after this layer should SCP continue in earnest.


## Research Sources

- AstroWiki, Primary Direction:
  `https://www.astro.com/astrowiki/en/Primary_Direction`
- Martin Gansten, Primary Directions:
  `https://astrology.martingansten.com/primary-directions/`
- AstroApp overview:
  `https://astroapp.com/en/astrology-software-all/astroapp-overview`
- AstroApp primary directions help:
  `https://astroapp.com/help/1/returnsW_53.html`
- AstroApp booklet:
  `https://astroapp.com/images/astroapp_booklet_final.pdf`
- Mastro manual:
  `https://mastroapp.com/files/documentation_en.pdf`
- Rumen Kolev, William Lilly and the Algorithm for His Primary Directions:
  `https://www.babylonianastrology.com/downloads/Lilly2.pdf`
- Halloran primary-directions material:
  `https://www.halloran.com/placidus.htm`
  `https://www.halloran.com/allsoft.htm`
