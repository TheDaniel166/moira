# Remaining Primary Directions Frontiers

## Purpose

This document defines the remaining frontier zones in Moira's
primary-directions program now that the most recoverable geometry, relation, and
target families have been admitted narrowly and validated.

It exists for one reason:

- to stop further expansion from drifting into doctrine that is not yet trusted

This is a research-governance document, not an implementation checklist.


## Current Position

Moira now has a substantial primary-directions core:

- major recoverable geometry families
- explicit direction spaces
- explicit time keys
- explicit relation doctrine
- explicit narrow target families
- admitted shortest-arc midpoint, method-scoped mundane-aspect, Placidian
  mundane-parallel, and neo-converse branches
- chronological timelines with explicit static/dynamic keys and distributor
  periods
- branch presets
- worked-example and fixture-backed validation on the most recoverable surfaces

That means the next work is no longer "add another branch because software has
it."

The next work is:

- frontier ranking
- recoverability judgment
- doctrinal risk management


## Ranking Rule

Every remaining frontier should be judged on four axes:

1. `source_quality`
   - are there explicit, formula-grade sources?
2. `mathematical_recoverability`
   - can Moira derive a real governing law?
3. `implementation_risk`
   - how likely is false unification or doctrinal drift?
4. `layer_fit`
   - should this live in the engine, a service layer, or remain research-only?


## Frontier Matrix

| Frontier | Source Quality | Mathematical Recoverability | Implementation Risk | Layer Fit | Current Judgment |
| --- | --- | --- | --- | --- | --- |
| `wider non-Ptolemaic reflected doctrine` | low-to-medium | partial | high | engine only if branch law appears | `defer` |
| `wider midpoint doctrines beyond shortest-arc targets` | low-to-medium | partial | high | engine only if a distinct branch law appears | `defer` |
| `wider mundane aspects beyond Placidian and Ptolemaic branches` | medium in places, but uneven | partial and method-bound | very high | engine only by method-specific branch | `defer` |
| `wider fixed-star doctrine beyond conjunction` | medium | low-to-partial | medium-to-high | engine only if conjunction-first discipline is preserved | `defer` |
| `wider parallel families beyond current closures` | medium in narrow branches, weak globally | partial and method-bound | high | engine only by method-specific branch | `defer` |
| `historical external numeric validation for neo-converse` | medium | partial | medium | validation evidence, not a new runtime switch | `research_only` |
| `field_plane` | low as a single unified doctrine | low | very high | research-only until decomposed law is explicit | `last_and_defer` |


## Frontier Notes

### 1. Wider Non-Ptolemaic Reflected Doctrine

What is known:

- Moira now has a first narrow reflected branch:
  - Ptolemaic zodiacal antiscia / contra-antiscia
- the mathematical substrate for reflection is explicit
- Lilly's zero-latitude Jupiter antiscion-to-Ascendant row supplies one
  historical external product for the planet-source antiscion branch

What is not known:

- whether other method families admit reflected points by the same directional
  law
- whether reflected doctrine should remain zodiacal-only in some families
- external numeric authority for node/angle sources and for the admitted
  contra-antiscion extension

Risk:

- easy to overgeneralize from one narrow branch

Current policy:

- defer until a branch-specific law appears


### 2. Midpoints in Primary Directions

What is known:

- midpoint mathematics in the repo is strong
- midpoint doctrine in primary directions is historically real in some later
  software and derived families

Current narrow admission:

- Moira admits a shortest-arc circular midpoint promissor constructed from two
  explicitly named sources
- the midpoint remains a derived target; it does not create a universal
  midpoint-direction doctrine

What is not known:

- whether other midpoint constructions or historical midpoint schools require
  distinct directional laws

Risk:

- very high risk of importing midpoint substrate into primary directions without
  a real directional doctrine

Current policy:

- preserve the admitted shortest-arc target
- defer any wider midpoint doctrine until its own governing law is explicit

The governing research packet now lives in:

- [primary_directions_midpoint_family_matrix.md](./primary_directions_midpoint_family_matrix.md)


### 3. Mundane Aspects as a Family

What is known:

- several geometry families become genuinely distinct in wider mundane aspect
  doctrine
- Campanus / Regiomontanus and Morinus especially point toward this
- Moira now admits explicit mundane-aspect targets for the Placidian and
  Ptolemaic semi-arc branches

What is not known:

- one global mundane-aspect doctrine

Risk:

- extremely high
- this is where many method families stop looking interchangeable and start
  demanding distinct branch laws

Current policy:

- retain the admitted Placidian and Ptolemaic branches
- do not generalize them to other methods without a method-specific law


### 4. Wider Fixed-Star Doctrine

What is known:

- conjunction to angles and planets is now explicit and regression-validated
- one Lilly zero-latitude zodiacal Vega-to-Ascendant row supplies an external
  historical product, but it does not validate true-latitude in-mundo or
  star-to-planet products
- opposition does not currently deserve admission

What is not known:

- whether aspects, wider mundane doctrine, or other star relations should be
  admitted at all

Risk:

- moderate if the conjunction-first discipline is preserved
- high if widened by folklore pressure

Current policy:

- fixed stars are closed for now on the current recoverable surface


### 5. Wider Parallel Families

What is known:

- Ptolemaic zodiacal parallels / contra-parallels are real
- Placidian direct and converse rapt parallels are real
- Placidian mundane parallels / contra-parallels are admitted as explicit
  target families

What is not known:

- whether additional families deserve admission without fresh governing laws

Risk:

- high risk of pretending the family is more uniform than it is

Current policy:

- closed for now


### 6. Neo-Converse

What is known:

- the label is live in modern software
- converse doctrine is already an explicit axis in Moira
- Moira now admits `neo_converse` as an explicit opt-in counter-diurnal
  circle-complement law, separately from traditional role exchange and signed
  primary motion

What is not known:

- a broad corpus of historical, externally reproducible numerical examples
  across every asymmetric method family

Risk:

- medium for historical interpretation and cross-school naming
- low for runtime ambiguity because the policy is explicit and opt-in

Current policy:

- retain the explicit admitted runtime doctrine
- keep broader historical claims and external numerical parity research-scoped

The governing research packet now lives in:

- [primary_directions_neo_converse_research.md](./primary_directions_neo_converse_research.md)


### 7. Field Plane

What is known:

- it is a composite ambiguity zone
- it likely decomposes into:
  - space doctrine
  - latitude doctrine
  - projected-plane doctrine
  - naming drift

What is not known:

- whether it is one thing at all

Risk:

- highest in the entire subsystem

Current policy:

- leave for last
- do not implement as a single opaque switch


## Engine vs Service-Layer Guidance

### Engine Candidates

These may eventually belong in the engine if a governing law becomes explicit:

- mundane-aspect methods beyond the admitted Placidian and Ptolemaic branches
- midpoint constructions beyond the admitted shortest-arc target
- a narrow non-Ptolemaic reflected branch

### Research-Only for Now

These should remain research-first, not implementation-first:

- field plane
- any global widening of reflected doctrine
- any global widening of parallels
- broad historical parity claims for neo-converse

### Not a Service-Layer Escape Hatch

Moira should not move a frontier to the service layer merely because the engine
law is unclear.

If the law is unclear, the honest status is:

- `research`
- `deferred`
- or `rejected`

not:

- "hide it one layer up"


## Recommended Next Order

If work continues after the current pause, the clean order is:

1. external numerical validation for the admitted neo-converse doctrine
2. source work for midpoint constructions beyond shortest-arc targets
3. reassess additional method-specific mundane-aspect branches only when their
   laws are recoverable
4. leave `field_plane` last


## Present Declaration

Moira is now past the most recoverable primary-directions families.

The remaining frontier is not "more branches."

It is:

- careful research
- branch-specific recoverability judgment
- and refusal to widen doctrine faster than mathematics can support it

