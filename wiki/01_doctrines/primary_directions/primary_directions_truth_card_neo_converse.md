# Neo-Converse Primary Directions Truth Card

## Historical Name

- `neo-converse`
- also described in modern software as directions "against the diurnal rotation"
- distinguished in modern usage from `traditional converse`

## Governing Object

- a **motion doctrine**, not a geometry method or a time key
- it belongs on the same axis as the currently admitted converse doctrines in
  [converse.py](../../../moira/primary_directions/converse.py):
  - `DIRECT_ONLY`
  - `TRADITIONAL_CONVERSE`
  - `NEO_CONVERSE`
  - `SIGNED_PRIMARY_MOTION`
- `NEO_CONVERSE` is an admitted explicit opt-in member of
  `PrimaryDirectionConverseDoctrine`

## Mathematical Basis

Moira's admitted mathematical law is the counter-diurnal circle complement:

`neo_converse_arc = (360 degrees - direct_arc) mod 360 degrees`

Conceptual definition (from the in-repo research packet
[primary_directions_neo_converse_research.md](../../05_research/primary_directions/primary_directions_neo_converse_research.md)):

- `traditional converse` (Gansten baseline, confirmed):
  the significator is carried by the **same** east-to-west diurnal rotation to
  the place of the promissor
- `neo-converse` (Delphic Oracle release notes):
  a direction defined **against** the diurnal rotation, added specifically to
  match Morinus-software values

In Moira's current engine, traditional converse is realized as **role
exchange**: the converse arc of significator-to-promissor is the direct arc of
promissor-to-significator, computed in the preceding terminus's circle of
position (see
[geometry.py](../../../moira/primary_directions/geometry.py),
`compute_primary_direction_arcs`). For the symmetric method families this
reduces to `converse = -direct`; for the asymmetric families it does not.
Neo-converse keeps the original ordered roles and applies the circle-complement
motion law, so it remains distinct from role exchange wherever the geometry is
asymmetric.

## Book 22 Assessment (2026-07-05)

Morin's own directional treatise, *Astrologia Gallica* Book 22
(*De Directionibus*, Holden trans.), was examined directly for this branch.
**It does not supply neo-converse, and this negative result should be
recorded so the source is not re-chased.**

- Book 22 Section I, Chapter 7 defines Morin's converse as proceeding *"by the
  **same** motion of the primum mobile… entirely as in the first direction"* —
  it is **against the succession of the signs**, not **against the diurnal
  rotation**. These are different reference frames.
- Morin never reverses the primary motion; he argues the primum mobile has a
  single motion and that direct/converse are one arc-finding operation with the
  significator/promissor roles swapped ("one and the same total effect").
- Therefore Book 22 recovers Morin's converse in the **traditional-converse
  lineage** (same diurnal motion, role reversal), which Moira already admits —
  **not** the modern "against the diurnal rotation" construction this card is
  about. It therefore does not provide historical authority for Moira's modern,
  explicitly labeled neo-converse law.

Collateral finding — now **corrected** (belongs to the *traditional* converse
doctrine, not this card): Morin computes the arc in the **preceding terminus's**
circle of position, so converse-of-A-to-B equals direct-of-B-to-A — role
reversal under the other body's pole, not arc-negation. Moira formerly realized
`converse = -direct`, which is exact only for the symmetric method families. As
of the traditional-converse refinement, `compute_primary_direction_arcs`
computes converse by exchanging the significator/promissor roles through the
same geometry law, so the under-pole and semi-arc families now carry Morin's
true converse arc while the symmetric families are unchanged. This correction is
independent of the admitted neo-converse policy.

## Resolved Ambiguity

The three earlier candidates were sign reversal, role reversal, and a distinct
counter-diurnal motion law. Moira resolved the runtime identity as the third
case, represented by the circle complement of the direct ordered arc. It does
not rename traditional role exchange and it does not reuse the signed-primary-
motion classifier.

## Current Moira Admission

- **admitted as an explicit opt-in doctrine**
- `TRADITIONAL_CONVERSE` remains the default cross-preset converse doctrine
  alongside `DIRECT_ONLY`
- `SIGNED_PRIMARY_MOTION` is separately admitted only by the source-scoped
  `TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION` preset; it classifies the
  sign of one ordered arc and is not neo-converse
- `NEO_CONVERSE` is selectable through engine policy and the typed REST
  `converse_doctrine` field
- Python and native solvers preserve the same named motion law

## Remaining Validation Bar

The runtime law and branch identity are explicit. What remains open is stronger
external numerical validation across historical schools and asymmetric method
families. Until that exists, Moira must describe neo-converse as a modern,
explicit computational doctrine rather than a universal historical standard.

## Boundary

- this card admits only the named circle-complement law
- it does not reinterpret Morin's traditional converse as neo-converse
- it does not claim universal historical agreement

## Epistemic Status

- `admitted_explicit_opt_in`
- `modern_software_documented`
- `historical_universality_not_established`

## Recommended Next Step

- Morin (Book 22) has now been checked and does **not** govern this branch —
  see the Book 22 Assessment above. The primary-source route for
  "against the diurnal rotation" is exhausted for Morin.
- seek reproducible worked examples or independent numerical comparisons for
  asymmetric method families
- keep those comparisons separate from the already explicit runtime law
