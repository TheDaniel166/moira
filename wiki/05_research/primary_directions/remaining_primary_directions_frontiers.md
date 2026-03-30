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
| `midpoints in primary directions` | low-to-medium | partial | high | likely engine only for narrow explicit branch | `research_only` |
| `mundane aspects as a family` | medium in places, but uneven | partial and method-bound | very high | engine only by method-specific branch | `defer` |
| `wider fixed-star doctrine beyond conjunction` | medium | low-to-partial | medium-to-high | engine only if conjunction-first discipline is preserved | `defer` |
| `wider parallel families beyond current closures` | medium in narrow branches, weak globally | partial and method-bound | high | engine only by method-specific branch | `defer` |
| `neo-converse` | medium | partial | medium | engine if governing law is recovered cleanly | `research_only` |
| `field_plane` | low as a single unified doctrine | low | very high | research-only until decomposed law is explicit | `last_and_defer` |


## Frontier Notes

### 1. Wider Non-Ptolemaic Reflected Doctrine

What is known:

- Moira now has a first narrow reflected branch:
  - Ptolemaic zodiacal antiscia / contra-antiscia
- the mathematical substrate for reflection is explicit

What is not known:

- whether other method families admit reflected points by the same directional
  law
- whether reflected doctrine should remain zodiacal-only in some families

Risk:

- easy to overgeneralize from one narrow branch

Current policy:

- defer until a branch-specific law appears


### 2. Midpoints in Primary Directions

What is known:

- midpoint mathematics in the repo is strong
- midpoint doctrine in primary directions is historically real in some later
  software and derived families

What is not known:

- one source-safe governing primary-direction law that makes midpoint targets
  admissible without ambiguity

Risk:

- very high risk of importing midpoint substrate into primary directions without
  a real directional doctrine

Current policy:

- research only

The governing research packet now lives in:

- [primary_directions_midpoint_family_matrix.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_midpoint_family_matrix.md)


### 3. Mundane Aspects as a Family

What is known:

- several geometry families become genuinely distinct in wider mundane aspect
  doctrine
- Campanus / Regiomontanus and Morinus especially point toward this

What is not known:

- one global mundane-aspect doctrine

Risk:

- extremely high
- this is where many method families stop looking interchangeable and start
  demanding distinct branch laws

Current policy:

- do not admit generically
- only admit method-specific mundane-aspect branches if their laws are explicit


### 4. Wider Fixed-Star Doctrine

What is known:

- conjunction to angles and planets is now explicit and validated
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

What is not known:

- a sufficiently explicit and source-safe governing law for admission

Risk:

- medium
- lower than `field_plane`, but still high enough to require a dedicated
  research pass first

Current policy:

- research only

The governing research packet now lives in:

- [primary_directions_neo_converse_research.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\05_research\primary_directions\primary_directions_neo_converse_research.md)


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

- method-specific mundane aspects
- a narrow midpoint branch
- a narrow non-Ptolemaic reflected branch
- neo-converse

### Research-Only for Now

These should remain research-first, not implementation-first:

- field plane
- any global widening of reflected doctrine
- any global widening of parallels

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

1. documentation and validation consolidation
2. dedicated research packet for `neo-converse`
3. dedicated research packet for `midpoints in primary directions`
4. only then reassess whether any method-specific mundane-aspect branch is
   recoverable
5. leave `field_plane` last


## Present Declaration

Moira is now past the most recoverable primary-directions families.

The remaining frontier is not "more branches."

It is:

- careful research
- branch-specific recoverability judgment
- and refusal to widen doctrine faster than mathematics can support it
