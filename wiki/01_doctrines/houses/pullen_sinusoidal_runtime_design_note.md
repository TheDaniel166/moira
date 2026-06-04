# Pullen Sinusoidal Houses Runtime Design Note

## Status

Implemented in the live houses runtime.

This note translates the governing doctrine in
[pullen_sinusoidal_admission_doctrine.md](./pullen_sinusoidal_admission_doctrine.md)
into a concrete runtime design for Moira's houses Pillar.

It is intentionally narrower than a roadmap and more executable than the
admission note. Its role is to define:

- where SD/SR would enter the current house architecture
- what helpers are allowed
- what helpers are forbidden
- how the implementation must be staged to remain Moira-owned

---

## Governing Design Rule

The implementation must be explainable in this order:

1. compute the ecliptic angle anchors already owned by the houses Pillar
2. derive the four ecliptic quadrant arcs
3. reduce those to the compressed / expanded quadrant pair
4. derive the three house widths for each quadrant from the source law
5. assemble the 12 cusp sequence by accumulation from the anchors
6. finalize and validate via the existing cusp hardening path

If the code is best explained as "ported Pullen support from Swiss," the
design has failed even before implementation begins.

---

## Intended Public Identity

### New `HouseSystem` codes

This design assumes two new canonical codes will eventually be added in
[moira/constants.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/constants.py):

- `HouseSystem.PULLEN_SD`
- `HouseSystem.PULLEN_SR`

The exact string tokens should be chosen only once and then frozen.

Suggested naming:

- `PSD` or `SD` for Pullen Sinusoidal Delta
- `PSR` or `SR` for Pullen Sinusoidal Ratio

Constraint:

- choose codes that do not collide with existing semantic uses elsewhere in
  the repository
- once chosen, update `HOUSE_SYSTEM_NAMES`

### Classification

Both systems should classify as:

- family: `HouseSystemFamily.QUADRANT`
- cusp basis: `HouseSystemCuspBasis.SINUSOIDAL`
- latitude-sensitive: `True`
- polar-capable: `True`

That classification must be added to `_CLASSIFICATIONS` and `_KNOWN_SYSTEMS`.

They must **not** be added to `_POLAR_SYSTEMS`, because their governing law is
not blocked by the same singularity class as Koch / Regiomontanus /
Topocentric / Campanus.

---

## Existing Runtime Anchors To Reuse

The present extension seam in
[moira/houses.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/houses.py)
already computes:

- `mc = _mc_from_armc(armc, obliquity, lat)`
- `asc = _asc_from_armc(armc, obliquity, lat)`

inside `houses_from_armc(...)`.

Those anchors are sufficient.

The Pullen systems must **not** introduce a parallel derivation of Ascendant or
Midheaven.

They also do not need:

- equatorial-sector helpers
- semi-arc helpers
- pole-height helpers
- local-horizon vector families
- root-search engines

Their runtime implementation should sit near the other ecliptic/quadrant
assembly helpers, not near Placidus/Koch/Regio families.

---

## Runtime File Map

### Files to change at implementation time

1. [moira/constants.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/constants.py)
   - add the two `HouseSystem` codes
   - add display names to `HOUSE_SYSTEM_NAMES`

2. [moira/houses.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/houses.py)
   - add `_CLASSIFICATIONS` entries
   - add `_KNOWN_SYSTEMS` entries
   - add two private computation helpers
   - add dispatch branches inside `houses_from_armc(...)`

3. [tests/unit/test_house_classification.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/tests/unit/test_house_classification.py)
   - family, basis, latitude-sensitive, polar-capable assertions

4. new focused house tests
   - Pullen law tests
   - degeneracy tests
   - ordered-figure / invariant tests

5. [wiki/02_standards/HOUSES_BACKEND_STANDARD.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/02_standards/HOUSES_BACKEND_STANDARD.md)
   - only after runtime admission is real

---

## Private Helper Design

The implementation should be built from a very small helper surface.

### 1. Quadrant extraction helper

Suggested helper:

`_ecliptic_quadrant_arcs(asc: float, mc: float) -> tuple[float, float, float, float]`

Responsibilities:

- compute the forward ecliptic arcs:
  - Asc -> MC
  - MC -> DSC
  - DSC -> IC
  - IC -> ASC
- preserve the actual directional arcs
- avoid hidden symmetry assumptions at the helper boundary

Rationale:

- the governing object is the actual quadrant arcs
- later helpers may reduce these to a compressed/expanded pair, but should not
  re-derive them ad hoc

### 2. Compressed-pair selector

Suggested helper:

`_compressed_expanded_quadrants(asc: float, mc: float) -> tuple[float, float, bool]`

Returns:

- compressed quadrant size `q`
- expanded quadrant size `180 - q`
- orientation flag indicating which half-figure is compressed

Responsibilities:

- choose the smaller of the complementary quadrants as the source-law `q`
- declare, not hide, which houses belong to the compressed side

This avoids Swiss-shaped "if quadrant < other quadrant then rotate slot fill"
behavior.

### 3. SD width-law helper

Suggested helper:

`_pullen_sd_widths(q: float) -> tuple[float, float, float, float, float, float]`

Responsibilities:

- compute the six doctrinal widths from the source equations
- apply the explicit `q < 30°` degeneracy branch if admitted
- return widths in named doctrinal order:
  - compressed flank
  - compressed middle
  - compressed flank
  - expanded flank
  - expanded middle
  - expanded flank

This helper must not know anything about cusp indices.

### 4. SR width-law helper

Suggested helper:

`_pullen_sr_widths(q: float) -> tuple[float, float, float, float, float, float]`

Responsibilities:

- solve for `r` deterministically from the source relation
- derive `x`
- return the six doctrinal widths in the same named order as SD

Solver doctrine:

- deterministic bracketed numeric solve
- fixed iteration budget or convergence tolerance
- no adaptive heuristic shaped by parity to an external engine

### 5. Cusp assembly helper

Suggested helper:

`_assemble_pullen_cusps(asc: float, mc: float, widths: tuple[float, ...], compressed_is_upper: bool) -> list[float]`

Responsibilities:

- map doctrinal widths onto the actual ecliptic circuit
- accumulate cusps from the anchor set in transparent order
- preserve anchor truth:
  - cusp 1 opens at Asc
  - cusp 10 opens at MC
  - cusp 7 opens at DSC
  - cusp 4 opens at IC

This helper is where implementation ownership matters most.

It must be written as named anchor-to-anchor accumulation, not legacy slot
filling with offset tables.

---

## Final Runtime Helper Shape

At the system level, the intended private functions are:

- `_pullen_sd(asc: float, mc: float) -> list[float]`
- `_pullen_sr(asc: float, mc: float) -> list[float]`

Each should do only this:

1. derive compressed/expanded quadrant doctrine
2. derive widths from the correct law
3. assemble cusps from anchors
4. return `_finalize_cusps(...)`

They should not contain:

- policy logic
- fallback logic
- classification logic
- direct interaction with `HouseCusps`

That remains with the existing runtime shell.

---

## `houses_from_armc(...)` Admission Shape

Implementation slot:

add two new branches in the direct system dispatch alongside other concrete
systems, for example after the ecliptic equal-family helpers or near Porphyry.

Conceptual shape:

```text
elif effective_system == HouseSystem.PULLEN_SD:
    cusps = _pullen_sd(asc, mc)
elif effective_system == HouseSystem.PULLEN_SR:
    cusps = _pullen_sr(asc, mc)
```

Important:

- no polar pre-emption branch
- no experimental-search detour
- no fallback semantics beyond existing unknown-system doctrine

If runtime implementation later reveals a real singularity beyond the source
packet, admission must pause and doctrine must be revised first.

---

## Assembly Doctrine

The cusp sequence must be assembled from the four cardinal anchors explicitly.

### Required anchor truths

- House 1 cusp = Asc
- House 10 cusp = MC
- House 7 cusp = DSC = Asc + 180°
- House 4 cusp = IC = MC + 180°

### Required assembly pattern

The implementation must treat each quadrant as a three-house span:

- Asc -> MC contains houses 12, 11, 10 or 1, 12, 11 depending on the chosen
  accumulation convention
- MC -> DSC contains the next three houses
- DSC -> IC the next three
- IC -> ASC the final three

The convention may be whichever is most natural in current `houses.py`, but it
must be documented explicitly in code comments.

### Forbidden assembly pattern

Do not:

- build a list of 12 placeholder slots and patch values by remembered
  positional choreography
- rotate a pre-filled array until the anchors appear correct
- apply index-based repairs after the fact

Those are exactly the lineage smells this design is meant to prevent.

---

## Numeric Doctrine

### SD

When `q >= 30°`:

- use the exact closed-form source equations

When `q < 30°`:

- only the source-declared zero-middle-house extension is admissible
- if that branch is implemented, it must be visible in code comments and tests

### SR

`r` must be solved from the governing source relation.

Allowed:

- deterministic bisection
- deterministic Newton/bisection hybrid if bracket safety is preserved

Preferred:

- pure bisection first, because it is easiest to explain and smell-audit

Not allowed:

- heuristic seed tuned to match Swiss outputs
- branch logic justified only by software parity

---

## Test Design

The first implementation pass should be admitted only with focused tests that
prove doctrine, not just snapshots.

### Classification tests

- both systems classify as `QUADRANT`
- both systems classify as `SINUSOIDAL`
- both are latitude-sensitive
- both are polar-capable

### Anchor tests

For both systems:

- cusp 1 equals Asc
- cusp 10 equals MC
- cusp 7 equals Asc + 180°
- cusp 4 equals MC + 180°

### Width-law tests

For SD:

- when `q >= 30°`, width differences satisfy the source delta law exactly

For SR:

- widths satisfy the declared ratio / power law within explicit numeric
  tolerance

### Degeneracy tests

For SD:

- one narrow-quadrant case with `q < 30°`
- prove the middle house width is `0°`
- prove the flanking widths bisect the remaining quadrant

For SR:

- one extreme narrow-quadrant case
- prove ordered, finite cusps

### Circular integrity tests

- all 12 cusps normalize into `[0, 360)`
- all forward spans are non-negative
- the total span sums to `360°`

---

## Smell-Audit Checklist

Before merge, the implementation must be reviewed against these questions:

1. Is the code organized around ecliptic quadrants and source width laws?
2. Are SD/SR widths computed from named doctrinal quantities rather than
   remembered software decomposition?
3. Is cusp assembly anchor-first and transparent?
4. Is the SD narrow-quadrant branch explicit doctrine rather than repair?
5. Does the SR solver exist because the source requires it, rather than because
   Swiss-like code used a similar numeric staging?
6. Would another engineer recognize this as Moira-native code on first read?

If any answer is "no", the implementation should be rewritten before admission.

---

## Implementation Order

When coding begins, the order should be:

1. add codes and names in `constants.py`
2. add classifications in `houses.py`
3. write failing classification tests
4. write failing doctrinal width-law tests
5. implement shared quadrant helpers
6. implement `_pullen_sd`
7. implement `_pullen_sr`
8. wire `houses_from_armc(...)`
9. run correctness audit
10. run smell audit
11. only then update the frozen houses standard

This order preserves ownership and keeps the proof burden where it belongs.
