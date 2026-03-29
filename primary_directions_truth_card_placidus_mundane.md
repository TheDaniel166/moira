# Primary Directions Truth Card: Placidus Mundane

## Status

- doctrinal family: `historically attested`
- Moira status: `implemented`
- role in Moira: current anchor method for the subsystem

## Identity

Placidus mundane primary directions treat the direction as a perfection in the
rotating celestial sphere under a Placidian mundane framework.

This is not merely "Placidus" as a menu label. It is a specific claim about:

- what is being directed
- where the relation lives
- how the arc is measured

## Mathematical Basis

### Direction Space

- `In Mundo`

The promissor is treated as a body or point in the actual rotating sphere, not
merely as a zodiacal longitude.

### Geometric Basis

- Placidian mundane geometry
- right ascension, declination, hour angle, and semi-arc structure are central
- the perfected relation is measured by a directional arc within the mundane
  framework

### Motion Basis

- direct motion is native
- converse motion may be admitted, but it should be treated as an explicit
  doctrine choice rather than a hidden toggle

### Key Basis

- the key is external to the geometry
- Ptolemy, Naibod, and solar-style keying may be layered on top of the same arc

### Latitude Basis

- latitude belongs intrinsically to the bodily placement of the promissor
- this is one reason mundane directions are often treated as more sphere-native
  than purely zodiacal ones

## Interpretive Meaning

Placidus mundane directions claim that events arise when a natal point, carried
by primary motion, perfects a meaningful relation in the actual world-frame of
the nativity.

The interpretive emphasis is therefore:

- bodily presence rather than abstract zodiacal position alone
- concrete activation of natal significations
- strong sensitivity to angles, houses, and accurately timed birth data

The promissor supplies the active quality of the event.
The significator supplies the area of life or topic affected.

## Historical Standing

- strongly rooted in the traditional and early modern family of primary
  directions
- close to the stream of practice that later software often calls Placidian,
  Placidian mundane, or under-the-pole Placidian in related contexts

The exact boundaries between Placidian subfamilies are not always named
consistently in later software, so Moira should be explicit about the exact
mathematical construction it uses.

## Distinguishing Features

Placidus mundane is distinguished from other families by:

- mundane, not merely zodiacal, perfection
- centrality of semi-arc structure
- preservation of the body's sphere-position rather than ecliptic reduction

It should not be conflated with:

- symbolic solar arc directions
- simple zodiacal directions by longitude
- under-the-pole variants that use different pole or house-circle doctrine

## Main Ambiguities

### 1. Scope of Admitted Targets

Historically native:

- bodies
- angles
- some fixed stars

More disputed:

- full aspectual families
- parallels
- rapt parallels

### 2. Converse Doctrine

There is no single modern meaning of "converse" across software. Moira should
separate:

- direct
- traditional converse
- neo-converse

### 3. Apparent vs True Positions

Modern software often exposes this choice. The method identity should not hide
which position doctrine is being used.

## Moira Admission Policy

Moira should keep this family as:

- the current reference implementation
- the validation anchor for later expansions
- the doctrinal baseline against which additional families are compared

Moira should not broaden it carelessly by treating every later Placidian option
as the same thing.

## Implementation Consequences

When Moira says `placidus_mundane`, it should mean:

- a specific direction space: `in_mundo`
- a specific geometry family: `placidian mundane`
- an explicit motion doctrine
- an explicit key policy
- explicit latitude and position policy

That precision is what allows later expansion without doctrinal drift.

## Research Sources

- Martin Gansten, *Primary Directions* chapter excerpt:
  `https://astrology.martingansten.com/wp-content/uploads/2020/08/PrimaryDirectionsChapter.pdf`
- AstroWiki, Primary Direction:
  `https://www.astro.com/astrowiki/en/Primary_Direction`
- AstroApp primary directions help:
  `https://astroapp.com/help/1/returnsW_53.html`
- Mastro manual:
  `https://mastroapp.com/files/documentation_en.pdf`
