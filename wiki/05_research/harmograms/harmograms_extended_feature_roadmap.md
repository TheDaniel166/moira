## Harmograms Extended Feature Roadmap

Status:
- core H1-H5 substrate implemented
- this document governs the next deferred frontier

Purpose:
- define the post-foundation roadmap for harmograms
- rank deferred work by mathematical risk, doctrinal risk, and architectural cleanliness
- preserve the distinction between research tooling and public product surfaces

---

## 1. Current Baseline

Moira now has:
- point-set harmonic vectors
- zero-Aries parts construction and parts-set vectors
- intensity-function spectra
- explicit spectral projection
- time-domain trace vessels over supplied snapshots
- research-facing comparison and inspection helpers

This means the mathematical substrate is no longer the blocker.

The remaining questions are now policy, scope, and product semantics.

---

## 2. Decision Law

Deferred harmogram work should now be prioritized by this order:

1. preserve mathematical visibility
2. preserve named chart-domain taxonomy
3. preserve doctrine explicitness
4. avoid interpretive drift
5. avoid facade-first widening before the family boundary is stable

If a candidate feature pressures the subsystem toward hidden doctrine blending,
interpretive scoring, or semantic collapse, it should be delayed.

---

## 3. Recommended Expansion Order

### E1. Additional Named Trace Families

Priority:
- highest

Why first:
- this extends the existing mathematical substrate without weakening it
- it adds useful scope while preserving explicit family naming
- it does not require interpretive doctrine

Recommended candidates:
- `transit_to_natal_zero_aries_parts`
- `directed_zero_aries_parts`
- `progressed_zero_aries_parts`

Requirements:
- each family must have its own explicit policy and vessel semantics
- family names must remain distinct
- no convenience surface that silently blends sky-only and relational traces

Risk:
- moderate

Main risk:
- semantic collapse between chart-domain families

Admitted candidate trace families:
- `dynamic_zero_aries_parts`
  - already implemented
  - moving point set per sample
  - chart domain: `dynamic_sky_only_trace`
- `transit_to_natal_zero_aries_parts`
  - moving transit positions against fixed natal positions
  - construction: `transit_body - natal_body`
  - chart domain: `transit_to_natal_trace`
- `directed_to_natal_zero_aries_parts`
  - moving directed positions against fixed natal positions
  - construction: `directed_body - natal_body`
  - chart domain: `directed_or_progressed_trace`
- `progressed_to_natal_zero_aries_parts`
  - moving progressed positions against fixed natal positions
  - construction: `progressed_body - natal_body`
  - chart domain: `directed_or_progressed_trace`
- `dynamic_point_set_trace`
  - moving point-set trace without parts construction
  - chart domain: `dynamic_sky_only_trace`
  - lower priority because it moves away from the current parts-centered foundation

Recommended first additional trace family:
- `transit_to_natal_zero_aries_parts`

Reason:
- preserves the existing parts-derived mathematics
- exercises the chart-domain taxonomy honestly
- stays mathematically explicit without pulling astronomy generation into `moira.harmograms`

---

### E2. Additional Intensity Families

Priority:
- high

Why second:
- the comparison framework now exists
- the subsystem can truthfully compare doctrines without collapsing them

Requirements:
- each admitted family must be named explicitly
- each family must declare its own conjunction policy, orb law, normalization law, and realization mode
- no blended preset should be introduced at this stage

Risk:
- moderate to high

Main risk:
- unexamined mathematical divergence between nominally similar intensity families

Admitted candidate intensity families:
- `cosine_bell_harmonic_aspects`
  - already implemented
  - compact-support smooth bell
- `top_hat_harmonic_aspects`
  - flat within orb, zero outside
  - simplest discontinuous comparison family
- `triangular_harmonic_aspects`
  - linear falloff from peak to orb edge
  - compact-support and easy to validate against direct tally
- `gaussian_harmonic_aspects`
  - smooth infinite-support bell
  - lower priority because truncation and normalization semantics become more delicate

Recommended first additional intensity family:
- `triangular_harmonic_aspects`

Reason:
- materially distinct from the current cosine-bell family
- still compact-support and numerically well-behaved
- well suited to spectrum, projection, and trace comparison tests

---

### E3. Snapshot-Generation Bridges

Priority:
- medium

What this means:
- helper surfaces that generate the supplied snapshots needed by `harmogram_trace(...)`
- still separate from the trace computation itself

Examples:
- sky-only ephemeris snapshot generator
- transit-to-natal snapshot generator
- directed/progressed snapshot generator

Requirements:
- astronomy remains outside `moira.harmograms`
- snapshot provenance must be explicit
- the trace engine must still accept plain supplied snapshots as its truth surface

Risk:
- moderate

Main risk:
- leaking astronomical generation concerns into the harmograms subsystem

---

### E4. Public-Surface Widening

Priority:
- medium

What this means:
- selective export from `moira.__init__`
- possible facade exposure only after the public semantics stabilize

Recommended order:
1. export selected harmograms types/functions from `moira.__init__`
2. delay facade helpers until multiple trace families and intensity families are stable

Risk:
- medium

Main risk:
- freezing immature semantics too early

---

### E5. Corpus and Research Tooling

Priority:
- medium to low

Examples:
- inferred intensity spectra from a labeled corpus
- family-comparison batches over a research set
- dominance summaries over many traces

Requirements:
- remain clearly research-facing
- never masquerade as source doctrine
- record provenance of any corpus or fitted output

Risk:
- high

Main risk:
- accidental promotion of empirical fit into doctrine

---

### E6. Interpretive Overlays

Priority:
- low

Examples:
- number-meaning glosses
- narrative summaries of dominant harmonics
- ranking labels like supportive, difficult, emphatic

Why late:
- these are not mathematical necessities
- they pressure the subsystem toward hidden doctrine and semantic inflation

Requirements if ever admitted:
- must sit above the mathematical layer
- must be clearly labeled as interpretive
- must not overwrite or rename the underlying quantitative truth objects

Risk:
- very high

Main risk:
- collapsing research mathematics into astrology prose without declared doctrine

---

### E7. Blended Presets and Auto-Selection

Priority:
- lowest

Examples:
- averaged doctrine presets
- automatic family selection
- adaptive conjunction policy based on data

Why last:
- these weaken provenance and doctrine visibility
- they are convenience-first rather than truth-first

Recommendation:
- keep deferred until there is a very strong reason and a documented doctrine boundary

Risk:
- extreme

---

## 4. Recommended First Post-Roadmap Track

The cleanest next expansion is:

1. add one additional named trace family
2. add one additional intensity family
3. only then reconsider public export widening

Concrete recommendation:
1. `transit_to_natal_zero_aries_parts`
2. `triangular_harmonic_aspects`
3. only then reconsider selective `moira.__init__` exports

That order keeps the subsystem:
- mathematical
- explicit
- comparative
- structurally honest

It also avoids jumping straight from research substrate to interpretive packaging.

---

## 5. Candidate Near-Term Deliverables

### Track A: Family Expansion

Deliver:
- one additional chart-domain trace family
- dedicated policy validation
- comparison tests against existing sky-only traces

Good fit when:
- the goal is broader mathematical coverage

### Track B: Intensity Expansion

Deliver:
- one second admitted intensity family
- spectrum comparison tests
- projection-difference tests

Good fit when:
- the goal is doctrinal comparison

### Track C: Public Promotion

Deliver:
- selective `moira.__init__` exports
- minimal documentation updates

Good fit when:
- the goal is usability, not new mathematics

---

## 6. Validation Rules For Every Future Expansion

Every post-H5 feature should state:
- the named family or doctrine being admitted
- whether the result is exact, finite closed-form, or truncated
- the harmonic-domain contract
- the chart-domain taxonomy it belongs to

Every expansion should verify:
- domain alignment
- stable policy preservation
- no silent family blending
- no hidden widening of astronomical responsibility into `moira.harmograms`

---

## 7. Explicit Non-Goals

This roadmap does not authorize:
- vague "better harmogram" heuristics
- opaque convenience scores
- collapsing multiple trace families into one generic label
- interpretive overlays presented as mathematical facts
- public parity claims against unnamed external systems

---

## 8. Recommended Next Move

If a single next step is chosen now, it should be:

- implement one additional named trace family

Reason:
- it builds directly on H4
- it is mathematically clean
- it exercises the chart-domain taxonomy
- it strengthens the subsystem without forcing interpretation
