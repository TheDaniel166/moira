# Primary Directions Ambiguity Ledger

## Purpose

This ledger records the main ambiguity zones in the doctrine of primary
directions.

Its purpose is not to eliminate ambiguity by assertion. Its purpose is to make
ambiguity visible so Moira can:

- separate doctrine from policy
- separate historical attestation from modern convention
- avoid smuggling unresolved disputes into code as if they were settled facts

## Severity Levels

- `High`: ambiguity changes the mathematical identity of the method
- `Medium`: ambiguity changes admissible targets or interpretive framing
- `Low`: ambiguity affects naming, defaults, or secondary options

## Ledger

### 1. Meaning of "Field Plane"

- severity: `High`
- type: direction-space ambiguity

#### Problem

`Field Plane` appears in modern software, but it is not yet a sharply
standardized doctrine.

#### What Seems Stable

- it is not purely `In Mundo`
- it is not purely zero-latitude `In Zodiaco`
- it is associated with zodiacal or aspectual directions retaining some latitude
  doctrine

#### What Is Unsettled

- what defines the plane
- whose latitude controls it
- whether the term names one method or a family

#### Moira Policy

- do not implement as a single opaque mode
- do not treat accepted software naming as sufficient mathematical definition

### 2. Zodiacal Latitude Treatment

- severity: `High`
- type: mathematical ambiguity

#### Problem

Historical and modern practice differ on whether zodiacal directions:

- suppress latitude
- retain bodily latitude
- assign aspect latitude

#### Moira Policy

- every zodiacal branch must declare its latitude doctrine explicitly

### 3. Converse Doctrine

- severity: `High`
- type: motion ambiguity

#### Problem

`Converse` is used for more than one concept in later literature and software.

#### Stable Distinction

- traditional converse
- neo-converse

#### Moira Policy

- converse may never remain a bare boolean in the final subsystem

### 4. Promissor and Significator Scope

- severity: `High`
- type: target-doctrine ambiguity

#### Problem

Traditions differ on what may function as:

- promissors
- significators

Disputed classes include:

- all planets as significators
- house cusps
- aspects
- fixed stars
- parallels
- antiscia

#### Moira Policy

- target classes must be admitted per method family, not globally by accident

### 5. Aspect Layout Doctrine

- severity: `High`
- type: mathematical and interpretive ambiguity

#### Problem

Astrologers disagreed on how aspects are laid out in directions:

- zodiacally
- equatorially
- through latitude-bearing models
- through mundane models

#### Moira Policy

- aspect layout must be a declared doctrine when aspectual directions are
  admitted

### 6. Naming Drift in Placidian Families

- severity: `Medium`
- type: naming ambiguity

#### Problem

Labels such as:

- `Placidus`
- `Placidus mundane`
- `Placidus under the pole`
- `Placidian semi-arc`

are not used consistently across software and literature.

#### Moira Policy

- define exact mathematical identity, not just inherited label

### 7. Campanus vs Regiomontanus Distinctness

- severity: `High`
- type: method-family ambiguity

#### Problem

Campanus and Regiomontanus are clearly distinct as full doctrinal families, but
their distinctness does not emerge uniformly on every primary-direction branch.

#### What Seems Stable

- the shared admitted under-the-pole speculum law is defensible on the current
  narrow surface:
  - `pole = arcsin(sin(phi) * sin(ZD))`
  - `O = arcsin(tan(D) * tan(pole))`
  - `W = RA +/- O` by quadrant
- several technical sources indicate that the sharper divergence appears in
  wider branches such as:
  - house-cusp directions
  - midpoint directions
  - certain mundane aspectual directions

#### What Is Unsettled

- whether a distinct Campanian directional pole law should replace the current
  shared law for any broader branch Moira has not yet admitted

#### Moira Policy

- treat the current Campanus branch as a verified narrow admission
- do not force artificial distinctness where sources do not require it
- only widen Campanian distinctness when a branch-specific governing law is
  explicit
### 8. Historical vs Modern Software Expansion

- severity: `High`
- type: historical ambiguity

#### Problem

Modern software often combines:

- historically attested methods
- reconstructions
- experimental extensions

under one interface.

#### Moira Policy

- classify every admitted branch by standing:
  - historically attested
  - historically grounded reconstruction
  - software-conventional
  - experimental

### 8a. Morinus Conjunction vs Morinus Aspect Distinctness

- severity: `High`
- type: method-family ambiguity

#### Problem

Morinus has a real and explicit formula trail for the circle of aspects, but
that does not automatically imply a distinct conjunction-style directional law.

#### What Seems Stable

- the Morinian aspect plane is explicit and computable when the service layer
  supplies:
  - `delta_max`
  - motion sense on the current node-to-node path segment
  - handed aspect angle
- this aspect-plane branch is the clearest source-safe Morinian distinctness

#### What Is Unsettled

- whether conjunction-style Morinus has a distinct governing law beyond the
  equatorial branch
- whether later sources merely reuse the equatorial relation for conjunctions
  while reserving Morinian distinctness for aspects

#### Moira Policy

- admit explicit Morinian aspect geometry where its formulas are recoverable
- do not invent a separate conjunction law without a source-safe derivation
- treat the current conjunction branch as intentionally shared with the
  equatorial family unless stronger evidence emerges

### 8b. Parallels and Rapt Parallels as Primary-Direction Targets

- severity: `High`
- type: target-and-geometry ambiguity

#### Problem

Parallels and rapt parallels look like target families, but the available
evidence suggests that they are not generic point-targets in the same sense as
zodiacal aspect-points.

#### What Seems Stable

- ordinary declination parallels and contra-parallels are already explicit in
  the standalone aspect engine
- some primary-direction traditions, especially Ptolemaic zodiacal examples,
  appear to handle parallels through method-specific ascensional equivalence
  rather than through one reusable projected target point

#### What Is Unsettled

- whether a parallel in primary directions should be represented as:
  - a projected point
  - a direct declination relation
  - an oblique-ascensional equivalent
  - or a method-specific perfection rule that changes from family to family

#### Moira Policy

- do not admit a generic `parallel point` target class
- keep parallels out of the consumer-facing primary-direction target vocabulary
  until a method-specific governing law is explicit
- prefer worked-example-backed narrow admissions over synthetic global target
  classes
- current narrow exception:
  - Ptolemaic zodiacal declination-equivalence may be admitted through
    explicit service-supplied relational targets without changing the global
    target doctrine

### 9. Apparent vs True Positions

- severity: `Medium`
- type: astronomical policy ambiguity

#### Problem

Some software exposes apparent versus true position choices, while others hide
them.

#### Moira Policy

- any such choice must remain explicit and auditable

### 10. Lunar Parallax

- severity: `Medium`
- type: astronomical policy ambiguity

#### Problem

Some systems expose lunar parallax correction within primary directions.

#### Moira Policy

- if admitted, parallax must be an explicit astronomical policy, not a hidden
  convenience option

### 11. Uniform Motion vs Actual Planetary Motion

- severity: `High`
- type: core-family ambiguity

#### Problem

Some descriptions preserve the classical idea that planets keep radical places
and are transported by primary motion, while others move toward
primary-progression style reasoning with actual motion.

#### Moira Policy

- distinguish true primary directions from direction-like progression families

## Decision Rule

Where ambiguity is high and the tradition is not settled, Moira should prefer:

1. narrower admission
2. explicit policy
3. documented uncertainty
4. decomposition before naming parity

over:

- broad feature parity
- hidden defaults
- synthetic black-box behavior
- guessing at a governing law that has not yet been made explicit

## Research Sources

- Martin Gansten, *Primary Directions* chapter excerpt:
  `https://astrology.martingansten.com/wp-content/uploads/2020/08/PrimaryDirectionsChapter.pdf`
- AstroWiki, Primary Direction:
  `https://www.astro.com/astrowiki/en/Primary_Direction`
- AstroApp primary directions help:
  `https://astroapp.com/help/1/returnsW_53.html`
- Mastro manual:
  `https://mastroapp.com/files/documentation_en.pdf`
- Rumen Kolev, *William Lilly and the Algorithm for His Primary Directions*:
  `https://www.babylonianastrology.com/downloads/Lilly2.pdf`
- Bob Makransky, *Primary Directions 1*:
  `https://www.scribd.com/document/48191844/Bob-Markansky-Primary-Directions-1`
- PyMorinus program notes:
  `https://sites.google.com/site/pymorinus/morinus-free-astrological-program-written-in-python-using-the-swiss-ephemeris`
