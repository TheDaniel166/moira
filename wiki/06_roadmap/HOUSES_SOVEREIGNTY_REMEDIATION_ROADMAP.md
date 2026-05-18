# Houses Sovereignty Remediation Roadmap

## Purpose

This document defines the exact path from the current `moira/houses.py`
implementation to an absolutely Moira-owned house Pillar in the strictest
clean-room and anti-lineage sense.

It does not describe current implementation truth. That remains frozen in
[HOUSES_BACKEND_STANDARD.md](../02_standards/HOUSES_BACKEND_STANDARD.md).

This document describes:

- the remaining sovereignty failures in `moira/houses.py`
- the exact architectural target for an absolute clean-room implementation
- the order of operations required to reach that target without losing
  validated numerical behavior
- the proof obligations each rewrite must satisfy before admission

---

## Governing Rule

The houses Pillar is not sovereign enough merely because:

- the numbers are correct
- the formulas are mathematically lawful
- the code is not verbatim copied
- the validation corpus matches Swiss Ephemeris

The Pillar is sovereign only when all of the following are true:

1. the governing computational object is Moira-owned
2. the derivation is explainable without inherited implementation staging
3. the executable structure is recognizably Moira-native
4. branch and singularity behavior are doctrine-shaped rather than repair-shaped
5. source-owned invariants carry the primary proof burden

---

## Present State

The current `moira/houses.py` state is mixed:

- validation sovereignty is substantially repaired
- some structural Swiss fingerprints have been removed
- some branch doctrine has been improved
- the file is still not fully Moira-native in ontology, derivation, or shared
  geometric language

The remaining failure is no longer primarily "copied Swiss code."

The deeper failure is that the houses Pillar still thinks too much in
classical angle-table staging and too little in explicit geometric objects.

---

## Remediation Matrix

| Target | Ownership axis failure | Severity | Exact remaining issue | Correct remediation class |
|---|---|---:|---|---|
| Module boundary (`calculate_houses`, `houses_from_armc`, file identity) | Ontology | Critical | House computation is still declared and mentally staged as `ARMC + obliquity + latitude -> cusps` | Re-found module identity around explicit frame and object construction |
| Shared projection substrate (`_project_ra_with_pole`) | Derivation | Major | Geometrized, but still psychologically anchored to the inherited closed form | Demote closed-form equivalence to secondary proof beneath object-first doctrine |
| Koch | Ontology | Critical | Governed by `DSA`, `AD`, `OA` staging | Rebuild from equatorial-sector geometry rather than oblique-ascension intermediates |
| Alcabitius | Ontology | Major | Governed by Ascendant declination and semi-arc staging | Rebuild from object-first semi-arc geometry |
| Campanus | Policy / Structure | Critical | Still uses `mc_shifted` plus post hoc cusp flipping; still carries a local vector mini-engine | Rewrite branch doctrine and move fully onto shared substrate |
| Azimuthal | Structure | Major | Duplicates a local vector mini-engine | Move to shared local-horizon substrate |
| Meridian | Structure | Major | Uses slot-rotation choreography rather than named doctrinal assembly | Replace with named assembly rule |
| Regiomontanus | Policy | Major | `mc_swapped` still governs branch resolution | Replace with generalized visible-branch doctrine |
| Topocentric | Policy | Major | Same as Regiomontanus | Same fix |
| APC | Policy / Ontology | Critical | Still uses `mc_shifted` repair logic and angular small-circle staging | Re-found on explicit curve doctrine and branch doctrine |
| Placidus | Ontology | Major | Still governed by semi-arc residual solving as primary ontology | Recast as event/root geometry; keep solving only as implementation method |
| Morinus / Carter / Krusinski | Mixed | Minor to Major | Partially clean mathematically, but not yet unified under one substrate language | Rebuild family-by-family after substrate hardening |

---

## Absolute Clean-Room Target

There is more than one valid mathematical attack on house geometry.

Moira must choose the attack that gives the strongest ownership, the clearest
proof surface, and the least residual lineage smell.

That target is:

1. define each house family by explicit geometric objects
2. represent those objects in a shared 3D or frame-explicit substrate
3. derive cusp candidates from those objects
4. choose visible branches from doctrine, not repairs
5. assemble the twelve-house figure from named structural parts
6. only then derive trig reductions as optional optimized forms

This order is non-negotiable.

If a closed form is used before the object is explicit, the subsystem is not
yet clean-room enough.

---

## Canonical House Geometry Architecture

### 1. Frame Layer

The houses Pillar must own a small explicit frame substrate:

- equatorial frame
- ecliptic frame
- local horizon frame
- explicit transforms between them

`ARMC`, obliquity, and geographic latitude belong here as frame parameters.
They must not remain the primary ontology of the full Pillar.

### 2. Primitive Object Layer

The Pillar should compute with a small canonical vocabulary:

- direction vector
- plane normal / great-circle normal
- small-circle or constrained-curve object
- ecliptic intersection candidate pair
- branch selector
- cardinal anchor assembler
- house-figure assembler

No family should define its own local mini-engine once these primitives exist.

### 3. Family Layer

Every supported house system should belong to one explicit geometric family.

#### A. Arc-on-ecliptic family

Systems:

- Whole Sign
- Equal
- Vehlow
- Porphyry
- Solar Sign
- Sunshine

Governing object:

- ecliptic arcs or sign sectors

#### B. Equatorial-division family

Systems:

- Morinus
- Meridian
- Carter

Governing object:

- equal equatorial sectors or right-ascension divisions projected to the
  ecliptic

#### C. Equatorial-sector / pole-height family

Systems:

- Regiomontanus
- Topocentric
- Koch
- Alcabitius

Governing object:

- cusp-defining equatorial sectors or temporal sectors represented as planes or
  equivalent geometric entities whose ecliptic intersections yield the cusps

#### D. Local-horizon / vertical-circle family

Systems:

- Campanus
- Azimuthal
- Krusinski

Governing object:

- vertical circles, prime-vertical sectors, zenith-anchored circles, or
  equivalent local-horizon great circles

#### E. Event/root family

Systems:

- Placidus
- APC

Governing object:

- a diurnal or nocturnal event condition whose solution on the celestial sphere
  yields the cusp

Root-finding may remain the implementation method, but must not remain the
primary ontology.

---

## Mandatory Clean-Room Admission Questions

Before any rewritten house system is admitted, the implementation must answer:

1. What is the governing geometric object?
2. In which frame does that object live?
3. How is the cusp candidate obtained from that object?
4. Why do two antipodal candidates arise, if they do?
5. How is the visible branch chosen without post hoc repair?
6. How is the final twelve-house figure assembled?
7. Which trigonometric formulas are derived reductions rather than governing
   ontology?

If these answers are not explicit, the rewrite is not complete.

---

## Phase Order

### Phase A - First Sovereign Rewrite: Campanus

Campanus is the first target because it still contains an unambiguous
repair-shaped branch regime and a duplicated local vector engine.

Required end state:

- no `mc_shifted` repair pass
- no local `_cross`, `_dot`, `_norm`, `_normalize`, `_ecliptic_longitude`
  mini-engine
- branch selection occurs per candidate before assembly
- final cusp figure is built through shared doctrinal assembly

This phase should establish the canonical local-horizon substrate for the
family, not just clean one function.

### Phase B - Local-Horizon Family Unification

Targets:

- Azimuthal
- Krusinski
- Campanus follow-through

Required end state:

- one shared local-horizon geometry substrate
- no duplicated vector mini-engines
- no post hoc visible-branch repair logic

### Phase C - Equatorial-Division Family Unification

Targets:

- Meridian
- Morinus
- Carter

Required end state:

- one shared equatorial-division doctrine
- named assembly rather than slot rotation or hand-filled cusp choreography
- cardinal anchor rules explicit

### Phase D - Pole-Height Family Re-foundation

Targets:

- Regiomontanus
- Topocentric
- Koch
- Alcabitius

Required end state:

- family identity expressed in equatorial-sector geometry
- branch doctrine does not depend on `mc_swapped` as the governing switch
- Koch and Alcabitius no longer begin from `OA`, `AD`, `DSA`, or equivalent
  as their primary ontology

### Phase E - Event/Root Family Re-foundation

Targets:

- APC
- Placidus

Required end state:

- event geometry stated explicitly
- root-solving retained only as execution method
- no repair-shaped latitude corrections
- branch and singularity doctrine explicit at the object level

This is the hardest phase and should be last.

---

## Exact Attack Path for Campanus

Campanus should be attacked as a local-horizon geometry problem, not as a cusp
array problem.

### Step 1

State the governing object:

- equal sectors on the prime vertical
- each sector defines a vertical great circle
- each vertical circle intersects the ecliptic in two antipodal candidates

### Step 2

Represent the vertical circle in the shared local-horizon substrate:

- define east, north, zenith explicitly
- define the sector pole or plane normal explicitly
- intersect with the ecliptic plane

### Step 3

Choose the candidate branch at construction time:

- not by `mc_shifted`
- not by flipping hardcoded cusp indices afterward
- but by a general visible-arc or horizon-facing doctrine

### Step 4

Assemble the house figure from:

- cardinal anchors
- upper intermediates
- lower intermediates
- opposite houses by stated antipodal doctrine, where applicable

### Step 5

Prove the result by invariants:

- each cusp lies on the intended vertical circle
- each cusp lies on the ecliptic
- selected candidates satisfy the visible-branch doctrine
- opposite houses remain antipodal where doctrinally required
- the reconstructed figure preserves validated outputs

Only after these are true should Swiss parity be consulted as a regression
oracle.

---

## Proof Obligations by Rewrite Class

### A. Ontology rewrite

Must prove:

- the governing object is explicit
- the object is not merely a thin restatement of an inherited angle recipe
- the code can be explained from the object without appealing to Swiss-like
  software staging

### B. Policy rewrite

Must prove:

- no branch ambiguity is resolved by a post hoc repair pass
- no hardcoded cusp-index mutation remains as the governing singularity regime
- branch choice is stable across critical-latitude sweeps

### C. Structural rewrite

Must prove:

- family members share one geometric substrate
- duplicated mini-engines are removed
- assembly is expressed through named doctrine rather than slot choreography

### D. Reduction proof

Must prove:

- any retained trig closed form agrees with the object-first implementation
- the reduced form is documented as a reduction, not the governing identity

---

## Verification Doctrine

Every rewrite phase must satisfy this proof order:

1. geometric object invariants
2. branch and singularity invariants
3. assembly invariants
4. dual-path equivalence between object-first and reduced forms
5. external parity checks against Swiss as secondary oracle only

The phase fails if steps 1 through 4 are weak but step 5 passes.

---

## Non-Negotiable Rejection Rules

A house rewrite must be rejected if any of the following remain true:

- the implementation still begins from `OA`, `AD`, `DSA`, `phi_h`, or similar
  as its governing identity when a deeper object is required
- branch behavior is still encoded as a repair loop
- the family still carries duplicated local vector algebra
- the code is best explained as "how a legacy ephemeris engine would do it"
- Swiss parity is still carrying most of the proof burden

---

## Final Standard

`moira/houses.py` will be constitutionally sovereign only when another engineer
can read the code and conclude:

- this subsystem is governed by Moira's own geometric objects
- its branch doctrine is explicit
- its assembly doctrine is explicit
- its reductions are subordinate to its ontology
- its proof does not depend on inherited engine authority

Until then, numerical correctness alone is not enough.
