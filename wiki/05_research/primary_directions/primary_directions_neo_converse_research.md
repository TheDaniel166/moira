# Primary Directions Research Packet -- Neo-Converse

## Purpose

This document records the current research state of `neo-converse` in Moira's
primary-directions program.

It does **not** admit the branch.

It answers four questions:

1. what `neo-converse` appears to mean in current sources
2. how it differs from traditional converse
3. what evidence is strong enough to trust
4. whether Moira should implement it now


## Current Definition Boundary

The clearest current distinction is:

- `traditional converse`
  - the significator is carried by the **same** diurnal rotation to the place
    of the promissor
- `neo-converse`
  - a later modern converse doctrine in which the direction is defined
    **against** the diurnal rotation

This is the most explicit statement currently in hand from technical software
documentation.


## Strongest Sources Currently in Hand

### 1. Martin Gansten on Traditional Converse

The most stable traditional definition available in current evidence is Martin
Gansten's formulation:

- direct direction:
  the promissor is carried by the east-to-west primary motion to the place of
  the significator
- converse direction:
  the significator is carried by the **same motion** to the place of the
  promissor

Source:

- [The Basics: What are Primary Directions?](https://www.martingansten.com/pdf/PrimaryDirectionsChapter.pdf)

This gives Moira a clear traditional baseline.


### 2. Delphic Oracle Release Notes

The most explicit `neo-converse` statement currently found is from Delphic
Oracle's release notes:

- neo-converse directions are "defined as directions against the diurnal
  rotation"
- traditional converse directions are those where the significator is moved
  with the diurnal rotation
- the option was added to match Morinus software values

Source:

- [Delphic Oracle release notes](https://t.astrology-x-files.com/delphicoracle-readme.html)

This is strong as a **software-technical definition**, but it is still not the
same as a fully published governing law.


### 3. Delphic Oracle Product Documentation

Delphic Oracle also states:

- it distinguishes traditional converse from neo-converse
- it follows conventions attributed to Martin Gansten's course
- it uses `neo-converse` as a separate direction mode in the UI

Sources:

- [Primary Directions in Delphic Oracle](https://www.astrology-x-files.com/software/primarydirections.html)
- [Advanced Medieval Module](https://astrology-x-files.com/software/medieval.html)
- [FAQ](https://www.astrology-x-files.com/faq.html)

These sources support the claim that `neo-converse` is a live modern doctrine
label, not a hallucinated term.


### 4. AstroApp as Software-Landscape Confirmation

AstroApp confirms that:

- both `traditional converse` and `neo-converse` are exposed as separate
  primary-direction options in current software

Sources:

- [AstroApp overview](https://astroapp.com/en/astrology-software/astroapp-overview-en)
- [AstroApp primary directions help](https://astroapp.com/help/1/returnsW_53.html)

This is useful landscape evidence, but not a governing formula.


## What Seems Stable

The following now look stable enough to state:

1. `neo-converse` is a real modern primary-directions label
2. it is not identical with traditional converse
3. the core conceptual distinction is:
   - traditional converse: same diurnal rotation, moving the significator
   - neo-converse: direction against the diurnal rotation
4. some software treats `neo-converse` as the mode needed to match Morinus-style
   modern values


## What Is Still Missing

The following are still missing for Moira admission:

1. a formula-grade branch law
   - how exactly does "against the diurnal rotation" alter the arc in each
     method family?
2. branch scope
   - is neo-converse one law across methods, or a family of method-specific
     converse laws?
3. source hierarchy
   - do we have only software documentation, or a stronger textual derivation?
4. validation material
   - worked examples or reproducible comparison cases


## Risk Assessment

### Source Quality

- current standing: `medium`

Why:

- the concept is clearly documented in active software
- the traditional baseline is clear
- but the modern mathematical law is not yet recovered in a source-safe,
  formula-grade packet


### Mathematical Recoverability

- current standing: `partial`

Why:

- the conceptual difference is explicit
- the computational transformation is still not sufficiently specified


### Implementation Risk

- current standing: `medium`

Why:

- lower risk than `field_plane`
- but still high enough that a premature implementation could smuggle in a
  software convention as if it were mathematically settled doctrine


## Moira Policy

Current policy should be:

- keep `traditional converse` as the only admitted converse doctrine
- classify `neo-converse` as:
  - `research_only`
  - `modern_software_documented`
  - `not yet source-safe for admission`

Moira should **not** implement `neo-converse` yet.


## Admission Bar

For `neo-converse` to be admitted, Moira should require:

1. a formula-grade governing law
2. explicit statement of whether that law is:
   - cross-method
   - or method-specific
3. at least one worked example or reproducible oracle comparison
4. a narrow branch admission first, not a global converse toggle


## Recommended Next Research Step

The next proper step is:

- a dedicated formula search for the mathematical law of
  `direction against the diurnal rotation`

That search should aim to answer:

1. how the direct and traditional converse arcs are transformed
2. whether neo-converse is simply a sign reversal, a role reversal, or a
   deeper motion-law change
3. whether the law differs by method family


## Present Declaration

Moira now has a clean research position on `neo-converse`:

- real as a modern doctrine label
- distinct from traditional converse
- not yet source-safe enough for implementation

