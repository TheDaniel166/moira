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
- the object under consideration is a *third* member of
  `PrimaryDirectionConverseDoctrine`, tentatively `NEO_CONVERSE`

## Mathematical Basis

The mathematical law is **not yet recovered in a source-safe, formula-grade
form.** Only a conceptual definition is currently in hand.

Conceptual definition (from the in-repo research packet
[primary_directions_neo_converse_research.md](../../05_research/primary_directions/primary_directions_neo_converse_research.md)):

- `traditional converse` (Gansten baseline, confirmed):
  the significator is carried by the **same** east-to-west diurnal rotation to
  the place of the promissor
- `neo-converse` (Delphic Oracle release notes):
  a direction defined **against** the diurnal rotation, added specifically to
  match Morinus-software values

In Moira's current engine, traditional converse is realized as a pure sign
negation of the direct arc (`converse = -direct`, see
[geometry.py](../../../moira/primary_directions/geometry.py)). The open question
is whether "against the diurnal rotation" is the *same* operation under a
different name, or a genuinely different construction.

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
  about. Neo-converse remains unsourced and gated.

Collateral finding (belongs to the *traditional* converse doctrine, not this
card): Morin computes the arc in the **preceding terminus's** circle of
position, so converse-of-A-to-B equals direct-of-B-to-A — role reversal under
the other body's pole, not arc-negation. Moira's `converse = -direct` is exact
only for the symmetric method families and is an approximation for the
under-pole and semi-arc families. Correcting that is a separate, method-family
substrate question.

## Ambiguity Ledger (unresolved — must be closed before admission)

Per the anti-leakage law (AGENTS.md §10A), the branch-selection doctrine must be
declared before any code. Three candidate interpretations remain open, and the
research packet explicitly refuses to choose among them:

1. **Sign reversal.** Neo-converse is identical to Moira's existing
   `converse = -direct` and the label is purely nominal. If true, admission
   would add a *name* with no new math, which would be semantic dishonesty
   unless the equivalence is itself the source-verified finding.
2. **Role reversal.** Neo-converse swaps the significator/promissor roles rather
   than negating the arc, yielding a numerically distinct result in the
   asymmetric method families (semi-arc, under-the-pole).
3. **Deeper motion-law change.** Neo-converse re-derives the arc under a reversed
   primary-motion sense at the geometry level, potentially method-specific.

These are not equivalent. Selecting one without a governing source would smuggle
a software convention in as settled doctrine — the precise failure §10A warns
against ("match Morinus values" is a software anchor, not a governing law).

## Current Moira Admission

- **not admitted**
- `TRADITIONAL_CONVERSE` remains the only admitted converse doctrine alongside
  `DIRECT_ONLY`
- no `NEO_CONVERSE` member exists in `PrimaryDirectionConverseDoctrine`
- no policy, preset, or geometry path references neo-converse

## Admission Bar (unmet)

Carried verbatim from the research packet; all four remain open:

1. a formula-grade governing law for "direction against the diurnal rotation"
2. an explicit statement of whether that law is cross-method or method-specific
3. at least one worked example or reproducible oracle comparison
4. a narrow branch admission first, not a global converse toggle

## Boundary

- this card does **not** admit neo-converse
- it does **not** assert that any of the three candidate interpretations is
  correct
- it converts the prior free-form research packet into the formal truth-card
  register so the branch has a governed, inspectable non-admission position

## Epistemic Status

- `research_only`
- `modern_software_documented`
- `not source-safe for admission`

## Recommended Next Step

- Morin (Book 22) has now been checked and does **not** govern this branch —
  see the Book 22 Assessment above. The primary-source route for
  "against the diurnal rotation" is exhausted for Morin.
- the remaining route is the specific modern software convention: the actual
  Morinus-program directional algorithm, or a reproducible worked example /
  oracle comparison that pins the numerical definition of neo-converse
- software UI documentation alone remains insufficient (§10A): "match Morinus
  values" is a software anchor, not a governing law
