# Multi-Doctrine Dispositorship Doctrine

## Purpose

This document defines the next pre-constitutional doctrine layer for Moira's
dispositorship subsystem after the narrow Phase 1 traditional implementation.

It exists because once Moira decides to be inclusive across astrological
schools, dispositorship can no longer be treated as a single fixed graph.
It becomes a family of policy-bounded graphs whose results may be computed
individually or compared side by side.

Before Moira expands dispositorship beyond Phase 1, it must state clearly:

- how multiple doctrine families are admitted without blurring them
- how subject-set policy and rulership policy remain separate concerns
- how a single-doctrine computation differs from a comparative computation
- how comparison is layered on top of doctrine-specific truth
- how Moira avoids silently mixing incompatible dispositorship systems

This document is therefore pre-Phase-2 constitutional work. It is not an API
contract and not yet a backend standard.


## Foundational Thesis

Inclusive dispositorship in Moira does **not** mean one maximally permissive
graph.

It means:

1. multiple named doctrine policies may be supported
2. each doctrine policy computes its own dispositorship graph
3. each graph remains internally coherent under its own subject and rulership
   assumptions
4. comparative views are derived only after those separate computations exist

Moira must not treat inclusivity as permission to merge doctrines into a single
ambient default.

If two schools disagree about who may participate or who rules a sign, Moira
must preserve both as separate computational truths rather than flattening them
into a synthetic compromise unless such a synthesis is itself made explicit as
a named doctrine.


## Why Expansion Changes The Problem

Phase 1 dispositorship is a narrow relation layer because:

- the subject set is fixed
- the sign-rulership doctrine is fixed
- termination semantics are fixed

Once Moira expands to broader astrological inclusivity, at least three kinds of
variation appear:

- subject-set variation
- sign-rulership variation
- dispositorship-basis variation

These are not cosmetic options. Each one changes the structure of the graph and
therefore the meaning of the output.

For example:

- a traditional graph may place Saturn as the ruler of Aquarius
- a modern graph may place Uranus as the ruler of Aquarius
- a hybrid graph may admit both Saturn and Uranus through a named doctrine

These are three different dispositorship systems, not three display formats
over one underlying truth.


## Core Constitutional Principle

Moira should expand dispositorship by **adding doctrine-specific computation
surfaces**, not by loosening the meaning of the existing one.

That means:

- the Phase 1 engine remains narrow and intact
- later doctrine families are admitted as explicit policy modes
- comparative outputs are higher-order aggregates over separate policy-bound
  results

This preserves separation of concerns:

- doctrine selection belongs to policy
- dispositorship computation belongs to the relation layer
- cross-doctrine comparison belongs to an aggregation layer
- presentation belongs to the reporting layer


## Core Doctrinal Axes For Multi-Doctrine Support

### 1. Subject Policy

This answers:

- which bodies may participate as graph subjects under a given doctrine

This must remain distinct from rulership policy.

Why:

- one doctrine may admit outer planets as participants while still using
  traditional sign rulership
- another may admit outer planets and also assign them sign rulership
- a third may keep outers out of scope entirely

These are separate choices.

Moira must not let:

- "include outers"

silently imply:

- "use modern rulership"

Subject admission and rulership assignment are coupled in consequences, but
they are not the same concern.

### 2. Rulership Policy

This answers:

- who rules what sign under the active doctrine

Potential future doctrine families may include:

- `traditional_domicile`
- `modern_domicile`
- `hybrid_domicile`
- later, possibly dignity-stack systems if they are admitted explicitly

Each of these defines a different graph topology.

Moira should therefore treat rulership doctrine as a first-class explicit
policy surface rather than a hidden consequence of subject selection.

### 3. Basis Policy

This answers:

- what kind of dispositorship relation is being computed

Phase 1 is:

- sign dispositorship by domicile

Future possibilities include:

- sign dispositorship by exaltation
- sign dispositorship by triplicity
- sign dispositorship by term/bound
- sign dispositorship by face/decan
- combined dignity dispositorship under a named doctrine

These must not be collapsed into one unlabelled "expanded dispositorship"
result.

### 4. Termination Policy

This answers:

- what counts as a legitimate dispositorship termination within the doctrine

At minimum the termination classes remain:

- final dispositor
- terminal cycle
- unresolved

Even if the doctrine family changes, Moira should preserve these classes unless
it explicitly defines a different doctrinal termination model.

### 5. Unsupported-Subject Policy

This answers:

- what happens when the chart contains bodies outside the selected doctrine's
  subject scope

This remains independent of doctrine selection.

For example:

- a traditional computation may ignore Pluto
- a strict traditional computation may reject Pluto
- a comparative bundle may include Pluto in one doctrine result and exclude it
  from another

Moira should preserve this explicitly rather than hiding it in caller
convenience behavior.


## Single-Doctrine Mode

### Definition

A **single-doctrine dispositorship computation** is one dispositorship run
performed under one explicitly selected doctrine policy.

It should answer:

- under this one named doctrine, what is the dispositorship structure of the
  chart?

### Properties

Single-doctrine mode should remain:

- deterministic
- policy-bounded
- fully inspectable
- internally coherent

It should not:

- silently compare itself to other doctrines
- merge incompatible doctrine families
- return ambiguous blended statements

### Why It Must Remain Separate

Single-doctrine mode is the atomic computational truth.

Comparative output is only as trustworthy as the individual doctrine-specific
computations underneath it.

If Moira blurs these two layers, callers will lose the ability to ask a clean
question such as:

- "what is the dispositorship structure under traditional rulership only?"


## Comparative-Bundle Mode

### Definition

A **comparative dispositorship bundle** is a higher-order result containing two
or more separate dispositorship profiles, each computed under its own named
doctrine policy.

It should answer:

- how do the dispositorship results differ across the selected doctrines?

### What It Is Not

It is not:

- a merged graph
- a compromise doctrine
- a hidden side effect of single-doctrine computation

It is a comparison layer over already-separate truths.

### Comparative Responsibilities

Comparative mode may:

- collect multiple doctrine-specific dispositorship profiles
- preserve the policy receipt for each profile
- identify agreements and divergences across profiles
- expose stable summary helpers for comparison

Comparative mode may not:

- rewrite doctrine-specific results
- infer a synthetic "best" doctrine by default
- claim that all compared results are simultaneously true under one doctrine


## Recommended Layer Decomposition

The expansion should be structured into three distinct layers.

### Layer 1: Doctrine-Bounded Dispositorship Computation

This layer owns:

- one policy
- one dispositorship graph
- one dispositorship profile

Output:

- a single dispositorship result with explicit policy provenance

### Layer 2: Comparative Bundle

This layer owns:

- a collection of named doctrine-specific dispositorship profiles

Output:

- a bundle preserving one-to-one association between doctrine label and result

### Layer 3: Comparative Summary / Inspectability

This layer owns:

- derived comparisons over the bundle

Examples:

- doctrines that agree on a final dispositor
- doctrines that differ on whether a terminal cycle exists
- doctrines that change a given body's dispositor

This layer is descriptive only. It must not replace the underlying results.


## Recommended Result Families

Moira will likely need three distinct result families if this expansion is
implemented cleanly.

### 1. Single-Doctrine Profile

This is the existing or extended dispositorship profile for one doctrine.

It should preserve:

- policy receipt
- per-subject chains
- final dispositors
- terminal cycles
- unsupported subjects

### 2. Comparative Bundle

This should preserve:

- ordered named doctrine results
- policy receipt for each doctrine
- stable doctrine identifiers

The bundle should not flatten doctrine identity.

### 3. Comparative Summary

This should preserve derived comparison truths such as:

- shared final dispositors across all doctrines
- doctrine-specific final dispositors
- shared cycle structures
- doctrine-specific cycle structures
- per-subject divergence tables

This should remain an inspectability layer, not a computational rewrite.


## Inclusivity Without Doctrinal Collapse

If Moira wants to be as inclusive as possible, it should do so by widening the
set of named doctrine policies it can compute, not by widening the default
until it becomes ambiguous.

That means inclusivity should look like:

- many supported doctrines
- explicit selection of doctrine
- optional parallel comparison of doctrines

It should not look like:

- one silent default that mixes traditional and modern rulership
- one graph containing contradictory rulership assumptions
- one summary that hides which doctrine produced it

Inclusivity is breadth of admitted doctrine, not erosion of doctrinal
boundaries.


## Potential Doctrine Families

The following families are plausible future candidates, but none should be
admitted without explicit doctrine definition.

### Subject-set families

- classical only
- classical plus outers
- classical plus outers plus selected points

### Rulership families

- traditional domicile
- modern domicile
- hybrid domicile

### Basis families

- domicile only
- exaltation only
- domicile plus exaltation
- full dignity stack under a named doctrine

### Scope families

- planetary dispositorship only
- planetary plus lot dispositorship
- planetary plus house-ruler dispositorship
- planetary plus topical-point dispositorship

Each of these changes the computation materially.


## Comparison Rules

If Moira implements comparative bundles, the following rules should hold.

### 1. Comparison Must Be Receipt-Aware

Every comparative result must retain:

- which doctrine was used
- which policy choices formed that doctrine

No comparative statement should exist without traceable provenance.

### 2. Comparison Must Be Derived, Not Recomputed

The comparative layer should consume already-computed doctrine-specific
profiles.

It should not rebuild dispositorship logic independently.

### 3. Comparison Must Distinguish Agreement From Coincidence

If two doctrines return the same final dispositor, that is a derived agreement
across two distinct computational paths.

Moira should preserve the fact that the agreement is cross-doctrinal rather
than pretending there was only one dispositorship truth all along.

### 4. Comparison Must Not Synthesize A Winner By Default

The comparative bundle may expose divergences.

It should not by default decide:

- which doctrine is right
- which doctrine is authoritative
- which doctrine should replace the others

That belongs to caller choice or a later explicit interpretive layer.


## Architectural Recommendation

Moira should support both of the following:

- single-profile mode
- comparative-bundle mode

But they must remain separate concerns.

The clean architecture is:

- one low-level doctrine-bounded engine entry point
- one higher-level comparative wrapper over multiple policy runs

This permits both:

- exact doctrinal computation
- inclusive cross-doctrine comparison

without sacrificing clarity.


## Deferred Questions

The following questions should remain open until later constitutional work:

- which modern or hybrid rulership systems Moira will officially admit
- whether comparison bundles are caller-built or engine-provided
- whether comparative summaries should include consensus helpers
- whether non-planetary subjects belong in the same subsystem
- whether dignity-stack dispositorship should remain one subsystem or split by
  basis family
- whether cross-doctrine comparison should expose differences only, or also
  common structural intersections


## Final Recommendation

Moira should treat multi-doctrine dispositorship as a layered expansion, not as
an expansion of ambiguity.

The subsystem should preserve:

- doctrinal separation
- explicit policy receipts
- single-doctrine exactness
- comparative-bundle clarity
- comparison as a derived layer

It should avoid:

- blended default graphs
- hidden doctrine switching
- subject-policy and rulership-policy collapse
- comparative output that replaces doctrinal output

Moira can be highly inclusive here, but only by computing more doctrines
cleanly, not by making doctrine less exact.
