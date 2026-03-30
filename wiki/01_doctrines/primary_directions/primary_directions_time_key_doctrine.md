# Primary Directions Time-Key Doctrine

## Purpose

This note defines the doctrine of time keys in primary directions.

A time key does not define the geometry of a direction. It defines how a
measured directional arc is converted into lived time.

## Core Thesis

Time-key doctrine must remain orthogonal to:

- geometry method
- direction space
- promissor/significator doctrine

If these are conflated, the subsystem becomes impossible to reason about.

## Shared Meaning of a Key

A key is a mapping from directional arc to time.

It answers:

- once the arc is known, how many years, months, or symbolic intervals does that
  arc signify?

It does **not** answer:

- what counts as perfection
- where the relation is measured
- which method family is being used

## Major Key Families

### 1. Static Keys

#### Definition

Static keys use a uniform conversion rate.

Examples named in traditional or modern literature:

- `Ptolemy`
- `Naibod`
- `Cardan`

#### Doctrine

- one unit of arc corresponds to a fixed unit of life-time
- the rate does not vary by the actual astronomical condition of the later time

#### Interpretive Effect

- favors regular symbolic mapping
- makes method comparison cleaner

### 2. Dynamic Keys

#### Definition

Dynamic keys vary the mapping according to astronomical motion or another
non-uniform temporal model.

Examples named in current software ecosystems:

- `Placidus`
- `Simmonite`
- `Ascendant Arc`
- `Vertical Arc`
- `Symbolic Solar Arc`
- `Kepler` in some doctrinal discussions

#### Doctrine

- the key depends on a changing or derived astronomical measure
- the temporal equivalence is not uniform

#### Interpretive Effect

- timing doctrine becomes more individually conditioned
- but the key becomes harder to compare across methods and harder to validate

### 3. Symbolic Keys

#### Definition

Symbolic keys use declared symbolic intervals rather than historically central
static keying.

Examples from current software:

- `Symbolic Degree`
- `Symbolic Year`
- `Symbolic Month`
- `Symbolic Week`
- `Duodenary`
- `Sub-duodenary`
- `Quarterly`
- `Quinary`
- `Septenary`
- `Novenary`
- `Symbolic Moon`
- `Meyer's self-measure`

#### Doctrine

- the conversion is explicitly symbolic or conventional
- these keys may be mathematically coherent without sharing the historical
  standing of the classical keys

#### Interpretive Effect

- often useful as experimental or modern practice
- should not be conflated with the core historical doctrine of primaries

## Important Classical Keys

### Ptolemy

- the basic one-degree-to-one-year family
- historically foundational

### Naibod

- a refinement of the Ptolemaic key
- widely treated as one of the most important classical keys

### Cardan

- historically important in later traditional and software practice
- should be admitted as a classical static-key peer, not as a miscellaneous
  modern option
- current admitted Moira rate:
  - `1 year = 59′12″ of arc`
  - equivalently `0.986666... degrees per year`

## Why Keys Must Be Separate

The same arc can be read under multiple keys.

Therefore:

- key is not the method
- key is not the space
- key is not the motion doctrine

A mature subsystem should be able to say:

- same geometry
- same direction space
- same promissor/significator relation
- different time key

without ambiguity.

## Moira Policy

Moira should eventually formalize:

- `PrimaryDirectionKeyFamily`
- `PrimaryDirectionKey`
- `PrimaryDirectionKeyPolicy`
- `PrimaryDirectionKeyTruth`

And each admitted key should be classified as:

- historically attested
- historically grounded reconstruction
- software-conventional
- experimental

## Validation Implications

Key validation should be separate from geometry validation.

The validation questions are:

1. Is the arc correct?
2. Is the key mapping correct?
3. Are software comparisons using the same key doctrine?

Without this separation, disagreements will be misdiagnosed.

## Research Sources

- AstroApp primary directions help:
  `https://astroapp.com/help/1/returnsW_53.html`
- Mastro manual:
  `https://mastroapp.com/files/documentation_en.pdf`
- AstroWiki, Primary Direction:
  `https://www.astro.com/astrowiki/en/Primary_Direction`
- AstroWiki, Naibod Key:
  `https://www.astro.com/astrowiki/en/Naibod_Key`
