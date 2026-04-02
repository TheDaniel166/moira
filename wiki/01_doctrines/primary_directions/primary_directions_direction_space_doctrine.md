# Primary Directions Direction-Space Doctrine

## Purpose

This note defines direction space as its own doctrine layer inside primary
directions.

Direction space should not be treated as a presentation option. It answers a
fundamental question:

- where does the perfected directional relation live?

## Core Thesis

In primary directions, geometry method and direction space are related, but not
identical.

- geometry method answers: how is the arc constructed?
- direction space answers: where is the relation defined?

That distinction is necessary if Moira is to exceed menu-driven software while
remaining doctrinally explicit.

## Known Direction-Space Families

### 1. In Mundo

#### Definition

The relation is defined in the actual rotating celestial sphere.

#### Mathematical Signature

- bodily placement matters
- right ascension, declination, meridian, horizon, house circles, and related
  quantities are structurally relevant

#### Interpretive Signature

- tends to be treated as more concrete, bodily, and event-specific

### 2. In Zodiaco

#### Definition

The relation is defined through zodiacal position and zodiacal aspect structure.

#### Mathematical Signature

- ecliptic or zodiacal relation is central
- the point may be treated as pure longitude or as a more complex zodiacal point

#### Interpretive Signature

- emphasizes zodiacal and aspectual significance

### 3. Field Plane

#### Definition

An apparent intermediate family in which zodiacal or aspectual points are
directed with latitude-bearing or latitude-conditioned treatment.

#### Mathematical Signature

- not purely mundane
- not purely zero-latitude zodiacal

#### Interpretive Signature

- preserves zodiacal meaning while refusing a wholly flattened ecliptic model

## Why Direction Space Matters

If direction space is hidden inside method names, the subsystem becomes muddy.

For example:

- `Regiomontanus in mundo`
- `Regiomontanus in zodiaco`

These are not the same thing merely because they share a geometry family.

Likewise:

- `Placidian semi-arc in zodiaco`
- `Placidus mundane`

should not collapse into one method bucket.

## Direction Space as a Generative Axis

Moira should treat direction space as one of the most generative axes in the
entire subsystem.

That means it may become a place where Moira exceeds current software by being
more explicit than existing tools.

Possible future decompositions:

- pure ecliptic space
- zodiacal-with-latitude space
- world-frame space
- projected hybrid spaces
- explicit aspect-field spaces

These should remain research categories until doctrine and validation justify
admission.

## Required Policy Questions

Every admitted direction space should answer:

1. What coordinates define the moving point?
2. What coordinates define the fixed target?
3. What relation constitutes perfection?
4. Is latitude preserved, suppressed, assigned, or projected?
5. Are aspectual points native to this space or derived artifacts?

## Moira Policy

Moira should:

- keep direction space explicit in doctrine and code
- never hide it inside a method label
- admit narrow, explicit space definitions first
- treat `field_plane` as a family requiring decomposition

## Research Sources

- AstroApp primary directions help:
  `https://astroapp.com/help/1/returnsW_53.html`
- Mastro manual:
  `https://mastroapp.com/files/documentation_en.pdf`
- AstroWiki, Primary Direction:
  `https://www.astro.com/astrowiki/en/Primary_Direction`
- Rumen Kolev, *William Lilly and the Algorithm for His Primary Directions*:
  `https://www.babylonianastrology.com/downloads/Lilly2.pdf`

