# Primary Directions Truth Card: Field-Plane Directions

## Status

- doctrinal family: `partly attested, partly software-conventional`
- Moira status: `not implemented`
- role in Moira: research family requiring decomposition before admission
- likely future classification, if partially admitted before full doctrine is
  recovered: `doctrine_loss_reconstruction`

## Identity

Field-plane directions appear to be a family of latitude-bearing or
latitude-conditioned zodiacal directions rather than one uniformly defined
historical method.

Moira should therefore treat `field_plane` as a doctrine family label, not as a
single computational option.

## Mathematical Basis

### Direction Space

- `Field Plane`

This appears to denote a space that is neither:

- purely mundane
- nor purely zero-latitude zodiacal

The best current doctrinal reading is:

- zodiacal or aspectual points are directed with retained, assigned, or
  conditioned latitude

### Geometric Basis

- aspectual or zodiacal points are not reduced to bare ecliptic longitude alone
- some latitude model remains in force

### Motion Basis

- still directional and primary-motion based
- not a separate timing family

### Key Basis

- keys are still orthogonal to the direction space
- modern software commonly allows many keys here, but that does not define the
  method itself

### Latitude Basis

- latitude doctrine is the heart of the family
- without explicit latitude policy, `field_plane` has no stable meaning

## Interpretive Meaning

Field-plane directions seem to preserve zodiacal aspect meaning while refusing a
flat zero-latitude reduction.

Interpretively, that suggests a family that claims:

- zodiacal relations matter
- but the spatial or embodied condition of the point also matters

This makes field-plane directions potentially important, but only if defined
explicitly enough to avoid becoming a black-box label.

## Historical Standing

- the term is real in current software
- Kolev's discussion suggests historical roots in zodiacal aspectual directions
  with latitude
- the exact doctrinal boundaries remain unclear

This means:

- the family is not imaginary
- but the label is not yet sharp enough to admit as one method

## Distinguishing Features

Field-plane differs from zodiacal directions by:

- refusing a pure zero-latitude ecliptic reduction

Field-plane differs from mundane directions by:

- still being aspectual or zodiacal in orientation rather than purely bodily in
  the world-frame

## Main Ambiguities

### 1. What Defines the Plane

Unresolved possibilities include:

- promissor-based latitude
- significator-based latitude
- aspect-specific latitude rules
- a projected relation plane rather than a simple inherited latitude

### 2. How Aspects Acquire Latitude

Some historical discussions imply that aspects inherit or derive latitude in
specific ways. This is not a settled uniform doctrine.

### 3. Whether the Label Is Historical or Retrospective

It is not yet clear whether "field plane" names one stable inherited doctrine or
is a later umbrella label for several related practices.

## Moira Admission Policy

Moira should not implement `field_plane` as a single menu option until it has
been decomposed into explicit policy components:

- latitude source
- projection rule
- aspect latitude rule
- relation measurement rule

Only after that decomposition should Moira decide whether one or several
field-plane doctrines are admissible.

Constitutional rule:

> accepted label does not override explicit doctrine.

Moira may acknowledge historically accepted or software-accepted labels, but it
admits only the mathematically explicit subset it can define, test, and defend.

Companion rule:

> where the tradition is composite, Moira decomposes before it admits.

This is why `field_plane` is still treated as a doctrine family above the
currently admitted branches rather than as a premature runtime switch.

Current Moira boundary:

- a retained-latitude zodiacal branch is now admitted explicitly
- it uses `in_zodiaco` with `promissor_native` latitude retained
- explicit zodiacal aspect-point promissors may now also use
  `aspect_inherited` latitude
- this branch is **not** being named `field_plane`
- `field_plane` remains a distinct, unresolved doctrine family above that branch

Current doctrinal judgment:

- these admitted branches likely cover part of what some software groups under
  `field_plane`
- especially where the family means "zodiacal directions that keep latitude in
  force"
- but they still do not settle whether `field_plane` names one separate space
  doctrine or a bundle of retained-latitude zodiacal variants

If Moira ever admits a partial `field_plane` branch before the full governing
law is recovered, it should be marked explicitly as one of:

- `experimental`
- `doctrine_loss_reconstruction`

and not presented as if the whole family had been recovered intact.

## Implementation Consequences

Field-plane should be treated as a research frontier and possible place for
Moira to exceed existing software.

But the only responsible way to exceed the field is:

- by making the doctrine more explicit
- not by hardcoding a mysterious modern label
- not by guessing at the missing law because a familiar label exists

## Research Sources

- Rumen Kolev, *William Lilly and the Algorithm for His Primary Directions*:
  `https://www.babylonianastrology.com/downloads/Lilly2.pdf`
- AstroApp primary directions help:
  `https://astroapp.com/help/1/returnsW_53.html`
- AstroApp forecasting overview:
  `https://astroapp.com/de/forecast-tools-15`
- AstroWiki, Primary Direction:
  `https://www.astro.com/astrowiki/en/Primary_Direction`
