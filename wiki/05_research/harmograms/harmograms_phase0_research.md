# Harmograms Phase 0 Research Note

Status: pre-Phase 1 research

Purpose:
- establish that harmograms are a supportable computational family in Moira
- separate the computable substrate from unresolved doctrine choices
- define the first narrow policy family Moira should freeze

---

## 1. Core Decision

What remains open is not whether harmograms are computable.

That part is clear.

What remains open is which explicit policy family Moira should adopt first.

Moira should therefore not begin with a vague "harmogram engine."
It should begin with one narrow, declared mathematical family whose rules are
visible in policy and whose output vessels are semantically explicit.

---

## 2. Recommended Subsystem Boundary

Recommended home:

`moira/harmograms/`

The subsystem should be split into two related but distinct computational
objects:

1. `harmonic_vector`
   A chart-at-an-instant spectral object.

2. `harmogram`
   A time-varying intensity trace over an interval.

This separation is important.

The harmonic vector is the cleaner first object mathematically.
The harmogram should be treated as a later time-domain projection built on top
of a frozen spectral or intensity doctrine.

---

## 3. First Freeze Recommendation

Moira should freeze `harmonic_vector` before `harmogram`.

Reason:
- it is the narrowest and clearest mathematical object
- it avoids prematurely freezing a time-trace doctrine
- it provides a stable substrate for later harmogram work
- it is easier to validate structurally than a full interval trace family

Recommended first family:
- one Garcia-style mathematical family
- amplitude-first surface
- no interpretive overlay
- no blended doctrine families

---

## 4. Policy Surface

Minimal first policy:

```python
HarmonicVectorPolicy
    basis_family
    pairing_mode
    self_pair_mode
    normalization_mode
    max_harmonic
```

Recommended later time-domain policy:

```python
HarmogramPolicy
    intensity_family
    harmonic_basis
    include_conjunction
    orb_mode
    normalization_mode
    self_pair_mode
    pairing_mode
    phase_mode
    max_harmonic
```

Policy notes:
- `basis_family` identifies the governing mathematical family explicitly.
- `pairing_mode` preserves whether the computation uses ordered pairs,
  unordered pairs, self-inclusive pairs, or a parts-derived construction.
- `self_pair_mode` is a doctrine choice, not an implementation detail.
- `normalization_mode` must remain explicit because scaling meaning changes the
  semantics of cross-chart comparison.
- `phase_mode` should not be hidden if Moira later supports amplitude-only
  versus amplitude-plus-phase products.

---

## 5. Proposed Computational Objects

### 5.1 Harmonic Vector

A harmonic vector in Moira should preserve:
- governing policy
- harmonic index
- amplitude
- optional phase
- normalization basis
- whether self-pair inclusion is active

This object is a mathematical analysis vessel, not an interpretive score.

### 5.2 Harmogram

A harmogram in Moira should preserve:
- governing policy
- sampled times or interval definition
- one trace per admitted harmonic
- the exact intensity family used
- whether conjunction is included
- normalization basis

This object is a time-domain analytic surface, not a hidden aspect summary.

---

## 6. Existing Moira Substrate

Moira already has the core substrate required for a harmograms family:
- authoritative planetary positions
- deterministic aspect geometry
- harmonic chart support
- explicit policy-first subsystem patterns
- typed result vessels and condition/relation layers in adjacent modules

This means the mathematical family is structurally supportable without bending
the repository architecture.

---

## 7. What Must Remain Explicit

Moira must not hide the following forks:
- whether conjunction belongs to the admitted intensity family
- whether orb is hard-gated, tapered, or otherwise modeled
- whether self-pairs are included
- whether pair order matters
- whether output is amplitude-only or amplitude-plus-phase
- whether the result is normalized and against what basis

These are doctrine-level choices.
They must not be buried as implicit defaults.

---

## 8. What Must Remain Deferred

The following should remain deferred beyond the first freeze:
- blended or user-averaged harmogram doctrines
- interpretive "number meaning" overlays
- collapsing harmonic-vector and harmogram products into one vessel
- claiming parity with a published harmogram school before one narrow family is
  actually implemented and validated

---

## 9. Validation Direction

Initial validation should be structural before comparative:
- deterministic repeatability
- ordering and normalization invariants
- expected behavior under trivial synthetic charts
- policy-sensitive output changes under conjunction/self-pair toggles

Comparative validation should wait until one explicit mathematical family is
frozen and the comparison object is named.

---

## 10. Recommended Phase Order

Phase order:

1. Freeze one `HarmonicVectorPolicy` family.
2. Define typed harmonic-vector vessels.
3. Implement structural validation for that family.
4. Only then define one `HarmogramPolicy` family.
5. Build the time-domain trace surface on top of the frozen family.

This keeps the doctrine honest and avoids widening the subsystem before the
governing law is explicit.

---

## 11. Current Decision

Current recommendation:
- admit harmograms as a valid research frontier
- do not begin with a generic harmogram engine
- begin with a narrow harmonic-vector family first
- defer interpretive overlays until the mathematical family is stable
