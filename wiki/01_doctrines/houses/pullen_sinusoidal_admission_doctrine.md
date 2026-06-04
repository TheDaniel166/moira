# Pullen Sinusoidal Houses Admission Doctrine

## Purpose

This note governs any future admission of the house systems commonly called:

- `Pullen SD` — Pullen Sinusoidal Delta
- `Pullen SR` — Pullen Sinusoidal Ratio

It exists because these systems previously appeared in the codebase through a
ported lineage that was later removed under the repository's anti-leakage and
anti-Swiss-smell rules.

This document therefore does **not** permit restoration of any prior
implementation shape.

It defines:

- what these systems are, in source-owned terms
- what they are **not**
- the governing mathematical objects that a Moira-owned implementation must use
- the singularity and branch doctrine that must be declared before coding
- the explicit anti-lineage constraints on implementation

---

## Source Packet

Primary source descriptions recovered for this admission:

1. Walter D. Pullen, "Sinusoidal House Systems"
   - <https://www.astrolog.org/astrolog/astsine.htm>
   - Author's own description of both systems, including the defining formulas
     and the stated SD limitation / SR all-chart claim.

2. Astro.com Swiss Ephemeris house overview
   - <https://www.astro.com/swisseph/sweph_ht_i.htm>
   - Confirms naming, historical attribution, and points to the Swiss Ephemeris
     documentation sections that describe the mathematical process.

Secondary technical reference:

3. Swiss Ephemeris programmer's manual
   - <https://www.astro.com/ftp/swisseph/doc/swephprg.2.10.pdf>
   - Useful only as historical corroboration of naming and support status.
   - Not a governing executable source for Moira.

Authority rule:

- Pullen's own text is the governing source for the systems' mathematical
  intent.
- Swiss may be used as a corroborating oracle or historical cross-check.
- Swiss implementation structure must not govern Moira's implementation shape.

---

## Admission Boundary

These systems are admissible only as **ecliptic sinusoidal graduation systems**
built on the Ascendant and Midheaven anchors.

They are **not** admissible as:

- borrowed Swiss runtime structure
- undocumented "same numbers, different names" ports
- sphere-division systems with invented non-source geometry
- generic Porphyry variants justified only by software parity

The Moira admission target is:

1. obtain the angle anchors through Moira's existing spherical astronomy
   substrate
2. define the relevant ecliptic quadrant arcs explicitly
3. derive house widths from the Pullen source laws
4. accumulate cusp positions from those widths
5. validate the result against source-owned invariants before any secondary
   parity check

---

## Governing Ontology

### Common governing objects

Both Pullen systems share the same governing foundation:

1. the ecliptic Ascendant
2. the ecliptic Midheaven
3. the four ecliptic quadrant arcs between:
   - Asc -> MC
   - MC -> DSC
   - DSC -> IC
   - IC -> ASC

Because the four cardinal points occur in antipodal pairs, opposite quadrants
share equal arc size and the full figure is determined by one complementary
pair of quadrant sizes:

- `q`
- `180° - q`

These systems are therefore **quadrant-based on the ecliptic**, but their
graduation law is neither Porphyry trisection nor a space-division law.

### Classification consequence

If admitted, both systems should be treated doctrinally as:

- `HouseSystemFamily.QUADRANT`
- `HouseSystemCuspBasis.SINUSOIDAL`
- latitude-sensitive: `True`
- polar-capable: `True`, insofar as Asc/MC remain computable and the source
  laws continue to define widths even at degenerate limits

They are not to be classified as:

- equatorial-division systems
- prime-vertical systems
- semi-arc systems
- polar-projection systems
- event/root systems

---

## Pullen SD Governing Law

Pullen SD is governed by a **sinusoidal delta law** over house widths.

Let `x` be the smallest house in the compressed quadrant and `n` the delta
increment. Per Pullen's source description, the six house widths across the
compressed and expanded half-figure are:

- compressed side: `x + n`, `x`, `x + n`
- expanded side: `x + 3n`, `x + 4n`, `x + 3n`

For a compressed quadrant of size `q`, the defining equations are:

- `(x + n) + x + (x + n) = q`
- `(x + 3n) + (x + 4n) + (x + 3n) = 180 - q`

Pullen gives the closed-form solution:

- `n = (90 - q) / 4`
- `x = (q - 30) / 2`

### SD singularity doctrine

Pullen explicitly states that SD fails as a pure sinusoidal-delta model for
quadrants smaller than `30°`.

Source-owned doctrine:

- when `q >= 30°`, use the exact SD law above
- when `q < 30°`, the pure SD law is no longer physically realizable with
  positive house sizes
- in that regime, Pullen's own recommendation is to:
  - keep the middle house of the narrow quadrant at `0°`
  - bisect the remaining narrow quadrant between the flanking houses

Moira may adopt this degeneracy branch **only if it is coded as explicit
doctrine**, not as a post hoc repair.

If adopted, the implementation must state plainly that:

- this branch is still Pullen-derived
- the result no longer satisfies the ideal sinusoidal-delta law
- it remains the source-preferred extension rather than a Moira invention

---

## Pullen SR Governing Law

Pullen SR is governed by a **sinusoidal ratio law** over house widths.

Let `x` be the smallest house in the compressed quadrant and `r` the ratio
factor. Per Pullen's source description, the six house widths are:

- compressed side: `r x`, `x`, `r x`
- expanded side: `x r^3`, `x r^4`, `x r^3`

For compressed quadrant size `q`, the defining equations are:

- `r x + x + r x = q`
- `x r^3 + x r^4 + x r^3 = 180 - q`

Pullen gives:

- `x = q / (2r + 1)`

and recommends solving `r` numerically from the second equation, for example by
binary search.

### SR singularity doctrine

Pullen's source states that SR works for all charts and quadrant sizes.

Source-owned limiting behavior:

- as the compressed quadrant approaches `0°`, `x -> 0`
- `r -> infinity`
- the largest house approaches `180°`
- the compressed houses collapse accordingly

Moira may therefore admit SR as the stronger all-chart sinusoidal system,
provided the numeric solver and limiting behavior are expressed explicitly and
deterministically.

---

## Spherical Astronomy Boundary

The user's requirement that the work "must use spherical trig" is admissible
only in the following sense:

- spherical astronomy may be used to obtain the Ascendant, MC, and the
  underlying ecliptic quadrant arcs
- spherical astronomy may be used to validate that the anchors are true
  ecliptic angle points

However, the governing graduation law of Pullen SD/SR is not itself a
spherical-trigonometric house-family law. It is an **ecliptic sinusoidal
width law**.

Therefore a source-faithful Moira implementation must:

- use spherical astronomy for the anchors
- use original Moira-owned derivation for the sinusoidal graduation
- not pretend the systems are something deeper or different than their source
  definition

This preserves both truth and ownership.

---

## Anti-Lineage Constraints

Because these systems previously entered the repository through a disputed
ported lineage, any future implementation must satisfy the strictest possible
clean-room rule.

### Forbidden implementation behaviors

The implementation must not:

- consult or recreate prior removed runtime code
- mirror Swiss helper boundaries or switch-branch staging
- assemble cusps by remembered legacy slot choreography
- justify branch behavior by "that's how Swiss/Astro.com does it"
- use parity against Swiss as the main proof of legitimacy

### Required implementation sequence

The implementation must:

1. define the compressed and expanded ecliptic quadrants explicitly
2. define the width law explicitly from source
3. define the degeneracy policy explicitly before coding
4. assemble house widths from named doctrinal quantities
5. accumulate cusp positions from the angle anchors in a transparent order
6. run a smell audit after numerical validation

If the best explanation of the code is still "this is a cleaned-up Swiss
translation", the admission fails even if the numbers are correct.

---

## Proof Obligations Before Runtime Admission

Before either system is admitted into `moira/houses.py`, the implementation
must prove:

1. **Anchor truth**
   - cusp 1 is anchored to the Ascendant
   - cusp 10 is anchored to the Midheaven
   - opposite cardinal anchors remain consistent

2. **Width-law truth**
   - SD: house-width differences satisfy the declared delta relations whenever
     `q >= 30°`
   - SR: house-width ratios satisfy the declared power-of-`r` relations

3. **Complementarity**
   - opposite quadrants sum correctly
   - the full twelve-house circuit sums to `360°`

4. **Degeneracy truth**
   - SD narrow-quadrant branch behaves exactly as the doctrine states
   - SR limiting cases remain finite, ordered, and deterministic

5. **Ownership truth**
   - the implementation can be explained from this doctrine and the source
     packet without any appeal to inherited software shape

Secondary parity against external engines may be used only after these primary
proofs are satisfied.

---

## Current Admission Status

Current status: **runtime admitted**

The source packet, governing mathematical objects, and clean-room runtime path
are now admitted in the live houses Pillar.

The active implementation remains bound by this doctrine:

- spherical astronomy only for Asc/MC anchor recovery
- ecliptic sinusoidal graduation as the governing law
- explicit SD narrow-quadrant branch doctrine
- deterministic SR numeric solve
- no Swiss-shaped restoration of prior implementation structure
