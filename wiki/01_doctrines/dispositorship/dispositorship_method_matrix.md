# Dispositorship Method Matrix

## Purpose

This document defines the pre-constitutional method matrix and result ontology
for Moira's dispositorship subsystem.

It exists to prevent later dispositorship phases from drifting into category
confusion, especially around:

- what counts as a method family
- what counts as a traversal termination
- what counts as a component-level structure
- what counts as a chart-level summary

Before Moira expands dispositorship beyond its current Phase 1 implementation,
it must state clearly:

- how many method families are currently real
- which method families are plausible later candidates
- which combinations are legitimate, incoherent, or deferred
- which result classes belong to local traversal truth
- which belong to higher-order structural summary

This document is therefore pre-constitutional architecture doctrine. It is not
an API contract and not yet a backend standard.


## Foundational Thesis

The dispositorship subsystem must distinguish four different kinds of thing:

1. method families
2. policy axes
3. traversal result classes
4. higher-order structural summaries

If Moira mixes those categories, the subsystem will become difficult to extend
without semantic drift.

The key discipline is:

- methods define *what kind of dispositorship is being computed*
- policy axes define *how one method family is parameterized*
- termination kinds define *what happened to one traversal*
- summary layers define *what the graph looks like as a whole*


## Current Practical Count

### Implemented Method Family Count

Moira currently has:

- **1 implemented method family**

That family is:

- `domicile_sign_rulership`

This corresponds to:

- sign-based dispositorship
- traditional domicile rulership
- `CLASSIC_7` subject scope
- explicit terminal classification

### Plausible Long-Term Method Family Count

Moira may eventually support:

- **3 major method families**

They are:

- `domicile_sign_rulership`
- `extended_essential_dignity`
- `modern_or_dual_rulership`

This is the practical count at the level of method families, not the count of
all possible policy combinations.


## Method Family Definitions

### 1. `domicile_sign_rulership`

This is the current foundational family.

Definition:

- dispositorship is derived from sign occupancy
- the ruler is determined by domicile rulership

Phase 1 current implementation:

- subject set: `CLASSIC_7`
- rulership doctrine: traditional domicile
- basis: domicile only

This family is:

- legitimate
- implemented
- architecturally foundational

### 2. `extended_essential_dignity`

This is the family where dispositorship expands beyond domicile sign rulership
into explicitly named essential-dignity bases.

Potential members may include:

- exaltation dispositorship
- triplicity dispositorship
- term/bound dispositorship
- face/decan dispositorship
- named combinations of these

This family is:

- potentially legitimate
- not yet implemented
- constitutionally deferred until each basis is defined explicitly

It must not be introduced as a vague "expanded dispositorship" toggle.

### 3. `modern_or_dual_rulership`

This is the family where subject participation and/or rulership topology expand
beyond the classical traditional system.

Potential members may include:

- modern domicile rulership
- hybrid domicile rulership
- dual-rulership doctrines

This family is:

- potentially legitimate
- not yet implemented
- constitutionally deferred until each doctrine is named and bounded

It must not be introduced through ambient outer-planet admission.


## Policy Axes

Method families are not the same thing as policy axes.

Policy axes are the dimensions along which a given family may be parameterized.

### Axis 1: `subject_policy`

Defines:

- who may participate as graph subjects

Examples:

- classical only
- classical plus outers
- broader mixed body sets

### Axis 2: `rulership_policy`

Defines:

- who rules what sign under the active method

Examples:

- traditional domicile
- modern domicile
- hybrid domicile

### Axis 3: `basis_policy`

Defines:

- which dispositorship basis is being computed

Examples:

- domicile
- exaltation
- triplicity
- term
- face

### Axis 4: `termination_policy`

Defines:

- what counts as final, cyclic, or unresolved under the method

Phase 1 stance:

- final dispositor requires self-domicile
- cycles are terminal

### Axis 5: `unsupported_subject_policy`

Defines:

- how out-of-scope bodies are treated

Examples:

- ignore
- reject
- segregate

These axes are real, but they do **not** each define a new method family by
themselves.


## Structural Modes

The subsystem also has structural modes that are not themselves method
families.

### 1. Single-Profile Mode

Computes:

- one dispositorship profile under one selected doctrine policy

### 2. Comparative-Bundle Mode

Computes:

- multiple doctrine-specific dispositorship profiles side by side

These are computation modes, not doctrine families.


## Method Matrix

The practical method matrix can be described as follows.

| Method family | Core idea | Current status | Notes |
|---|---|---|---|
| `domicile_sign_rulership` | sign-based dispositorship by domicile rulership | implemented | current Phase 1 family |
| `extended_essential_dignity` | dispositorship by non-domicile essential dignities or named dignity combinations | deferred | requires explicit doctrine per basis |
| `modern_or_dual_rulership` | dispositorship under modern, hybrid, or dual sign-rulership topologies | deferred | requires named rulership doctrines |


## Legitimacy Classes

Not every future combination is equally acceptable.

Moira should classify candidate combinations into:

- legitimate
- incoherent
- deferred

### Legitimate

A combination is legitimate when it is:

- internally coherent
- doctrine-nameable
- computationally explicit
- inspectable without ambiguity

Examples:

- classical subject set + traditional domicile rulership + domicile basis
- broader modern subject set + modern domicile rulership + domicile basis
- doctrine-specific comparative bundle over two already-legitimate profiles

### Incoherent

A combination is incoherent when it:

- silently mixes incompatible assumptions
- allows one policy choice to imply another implicitly
- produces a graph whose doctrinal identity is unclear

Examples:

- "include outers" while leaving rulership doctrine ambient
- hidden switching between traditional and modern rulers in one traversal
- one result surface combining domicile and exaltation dispositorship without
  naming the method

### Deferred

A combination is deferred when it:

- might be legitimate later
- but has not yet been doctrinally frozen

Examples:

- full dignity-stack dispositorship
- hybrid dual-rulership systems without a named doctrine
- non-planetary mixed dispositorship families


## Result Ontology

The dispositorship subsystem must keep local traversal truth separate from
higher-order graph structure.

This is the core ontological rule of the subsystem.


## Per-Subject Layer

This is the level of one dispositorship traversal from one initial subject.

The key field here is:

- `termination_kind`

### Allowed `termination_kind` values

- `final_dispositor`
- `terminal_cycle`
- `unresolved`

These answer the question:

- what happened when this chain was followed?

They are local traversal outcomes.

They are **not** chart-level graph summaries.


## Per-Component Layer

This is the level of one connected dispositorship component under the active
policy.

The key field here should be something like:

- `terminal_signature`

This answers questions such as:

- does this component terminate in one final dispositor?
- does it terminate in a cycle?
- is it mixed or unresolved?

This is where terminal attractor structure belongs if Moira later chooses to
formalize components explicitly.


## Chart-Wide Layer

This is the level of the chart-wide dispositorship structure.

The chart-wide layer should preserve explicit summary metrics rather than
inventing new pseudo-termination kinds.

Recommended chart-wide summary fields include:

- `final_dispositor_count`
- `cycle_count`
- `unresolved_count`
- `component_count`
- `has_mixed_terminals`

These answer:

- what is the global shape of dispositorship in this chart?

This is where "multiple" language properly belongs.


## Why `multiple_roots` Is Not A Primary Termination Kind

`multiple_roots` is not naturally a peer to:

- `final_dispositor`
- `terminal_cycle`
- `unresolved`

Why:

- those three describe the outcome of one traversal
- `multiple_roots` usually describes a global graph condition

So unless Moira first defines **root** very strictly in graph-theoretic terms,
`multiple_roots` should not appear as a sibling in the primary termination
enum.

If Moira later defines:

- root = terminal attractor of a dispositorship component under the active
  policy

then it may derive chart-wide summary metrics such as:

- `one_root`
- `multiple_roots`
- `zero_roots`

But even then, those should remain summary metrics, not primary traversal
termination kinds.


## Recommended Vocabulary

Moira should prefer the following layered vocabulary.

### For one subject

- `termination_kind`

### For one component

- `terminal_signature`

### For one chart

- `final_dispositor_count`
- `cycle_count`
- `unresolved_count`
- `component_count`
- `has_mixed_terminals`

If Moira ever needs a "multiple" phrase, better options are:

- multiple terminal endpoints
- multiple terminal components
- mixed terminal structure

These are cleaner than using `multiple_roots` loosely.


## Recommended Architectural Count

The practical architectural count for Moira is therefore:

- **method families now:** 1
- **probable long-term method families:** 3
- **primary termination kinds:** 3
- **higher-order summary layers:** 2
  - component-level
  - chart-level

This is the cleanest count that preserves ontological separation.


## Final Recommendation

Moira should freeze the dispositorship method matrix and result ontology as
follows:

- treat `domicile_sign_rulership` as the sole implemented method family
- treat `extended_essential_dignity` and `modern_or_dual_rulership` as later
  doctrine families, not loose feature toggles
- keep `termination_kind` strictly local to one traversal
- keep component structure separate from chart-wide summary
- forbid loose use of `multiple_roots` as a peer termination class

If Moira holds this distinction firmly now, later dispositorship phases can
expand substantially without becoming semantically unstable.
