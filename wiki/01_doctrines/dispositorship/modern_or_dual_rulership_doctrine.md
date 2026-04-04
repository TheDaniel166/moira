# Modern Or Dual Rulership Doctrine

## Purpose

This document defines the pre-constitutional doctrine layer for the
`modern_or_dual_rulership` family within Moira's dispositorship subsystem.

It exists because dispositorship becomes substantially more inclusive once
outer-planet rulership or dual-rulership systems are admitted, but that
inclusivity also introduces a more fragile graph topology than the narrow
Phase 1 traditional model.

Before Moira implements this family, it must state clearly:

- whether outer planets are admitted only as subjects, or also as rulers
- whether modern rulership replaces traditional rulership or coexists with it
- whether "dual rulership" means parallel doctrines or one combined doctrine
- how mixed traditional/modern results are named and kept separate

This document is therefore pre-constitutional work for a deferred doctrine
family. It is not an API contract and not yet a backend standard.


## Foundational Thesis

`modern_or_dual_rulership` is a distinct dispositorship family, not a minor
variant of traditional domicile dispositorship.

Why:

- it changes the sign-rulership topology of the graph
- it usually changes the participating subject set
- it changes which chains terminate where
- it can alter whether a chart has a final dispositor, a cycle, or no final
  dispositorship at all

Moira must therefore treat this family as doctrine-bearing, not as a cosmetic
extension.


## What This Family Covers

This family includes doctrines such as:

- modern domicile rulership
- hybrid domicile rulership
- dual-rulership systems

Typical examples in contemporary astrology include assigning:

- Uranus to Aquarius
- Neptune to Pisces
- Pluto to Scorpio

But Moira must not assume that all modern practitioners use the same system,
or that all hybrid systems mean the same thing.


## Why Outer-Planet Admission Is Not Enough

There are at least three materially different possibilities:

1. admit outer planets as **subjects only**
2. admit outer planets as **subjects and rulers** under a modern doctrine
3. admit outer planets into a **hybrid or dual-rulership** doctrine

These are not equivalent.

For example:

- including Uranus in a chart while Saturn still rules Aquarius is one system
- including Uranus and making Uranus the ruler of Aquarius is another
- including both Saturn and Uranus in a dual-rulership doctrine is a third

Therefore:

- subject admission must remain distinct from rulership doctrine
- "include outers" must not silently imply "modern rulership"


## Core Doctrinal Questions

### 1. Replacement vs Coexistence

This answers:

- does modern rulership replace the traditional ruler
- or does the sign carry both a traditional and modern ruler

The distinction is decisive.

If modern rulership replaces traditional rulership, the graph is single-valued.

If both coexist, then Moira must decide whether it is doing:

- two separate doctrine runs in parallel
- or one explicit dual-rulership doctrine with its own graph semantics

Those are different computational acts.

### 2. Dual Rulership Meaning

This answers:

- what "dual" means in practice

Possible meanings include:

- a comparative bundle over two separate doctrines
- one doctrine that allows two rulers per sign
- one doctrine that prioritizes one ruler and preserves the other as secondary

Moira should not use the phrase "dual rulership" unless one of those meanings
is fixed explicitly.

### 3. Subject Scope

This answers:

- which bodies may participate as dispositorship subjects

Possible future scopes include:

- classical plus Uranus, Neptune, Pluto
- a broader modern planetary subject set
- a mixed set with selected points

This must still remain independent from the rulership rule itself.

### 4. Termination Semantics

This answers:

- how final dispositors and cycles are recognized once outer-planet rulership
  is active

Moira should preserve the same termination ontology unless a doctrine requires
otherwise:

- `final_dispositor`
- `terminal_cycle`
- `unresolved`

But the distribution of those results may change radically when the rulership
graph changes.


## Recommended Constitutional Stance

Moira should not implement one vague "modernized dispositorship" mode.

Instead, it should admit named sub-doctrines within this family, such as:

- `modern_domicile`
- `hybrid_domicile`
- later, perhaps additional named dual-rulership doctrines

Each sub-doctrine should:

- declare its subject policy
- declare its rulership policy
- declare whether rulership is single or dual-valued
- preserve a visible policy receipt in every result


## Comparative Implication

This family is especially well suited to the comparative-bundle layer.

Why:

- traditional and modern outputs may differ sharply
- the same chart may show radically different final dispositors under each
  doctrine
- callers often need to compare rather than collapse the results

So Moira should treat comparative presentation as a first-class companion to
this family, rather than forcing users to infer differences manually.


## What Must Be Avoided

Moira should avoid:

- ambient outer-planet admission
- hidden replacement of Saturn/Jupiter/Mars by Uranus/Neptune/Pluto
- calling a result "dual" when it is really a silent blend
- one merged graph that hides which doctrine produced which edge

These would make the subsystem more inclusive in appearance but less exact in
truth.


## Deferred Implementation Recommendation

This family should remain deferred until Moira freezes at least one explicit
sub-doctrine under it.

The cleanest first candidate would likely be:

- `modern_domicile`

implemented as:

- a named single-doctrine profile
- explicitly paired with the comparative-bundle layer so it can be compared
  against traditional domicile dispositorship

Only after that should Moira consider a truly dual-rulership doctrine.


## Final Recommendation

Moira should treat `modern_or_dual_rulership` as a legitimate long-term
dispositorship family, but only if it is implemented through explicit named
sub-doctrines.

It should preserve:

- separation of subject scope and rulership doctrine
- explicit declaration of replacement vs coexistence
- compatibility with comparative bundles
- the existing termination ontology

It should avoid:

- silent modernization
- hidden dual-rulership blending
- ambiguous graph identity

The family is appropriate for Moira, but only as a governed expansion of
doctrine, not as a broad permissive switch.
