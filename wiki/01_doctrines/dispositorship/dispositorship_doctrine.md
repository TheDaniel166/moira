# Dispositorship Doctrine

## Purpose

This document defines the pre-constitutional doctrine layer for Moira's
dispositorship subsystem.

It exists because dispositorship is one of those techniques that appears
superficially simple while hiding consequential doctrinal choices inside what
many software packages treat as defaults.

Before Moira implements this technique, it must state clearly:

- what a dispositor is in the narrow computational sense
- what a dispositorship chain is and how it is traversed
- what qualifies as a final dispositor
- how cycles differ from final dispositors
- what subject set and rulership doctrine Phase 1 will admit
- how unsupported bodies are handled

This document is therefore pre-Phase-1 constitutional work. It is not an API
contract and not yet a backend standard.


## Foundational Thesis

Dispositorship in Moira is a **derived rulership relation**.

Its core logic is:

1. determine the sign occupied by a subject body
2. determine the ruler of that sign under an explicit rulership doctrine
3. that ruler is the body's dispositor
4. repeat the process over successive dispositors to produce a directed chain
5. classify the chain's termination as a final dispositor, a terminal cycle,
   or an unresolved termination

The technique is simple only if all of its underlying doctrine is already
fixed. It is not simple when the following remain ambient:

- which bodies are allowed to participate
- which rulership system is active
- what counts as a legitimate terminal condition
- how unsupported subjects are treated

Moira must not allow those choices to enter the engine as unstated defaults.


## Computational Definition

### What a Dispositor Is

A **dispositor** is the planet that rules the sign occupied by another subject,
under the active rulership policy.

For example:

- Venus in Aries is disposed by Mars under traditional domicile rulership
- Saturn in Aquarius is disposed by Saturn under traditional domicile rulership

In the second case, the subject disposes itself because it occupies one of its
own domiciles.

### What a Dispositorship Chain Is

A **dispositorship chain** is the directed sequence produced by repeated
dispositor lookup from an initial subject:

`subject -> dispositor -> dispositor of dispositor -> ...`

The chain is not interpretive language. It is a deterministic traversal over a
rulership graph.

### What a Final Dispositor Is

A **final dispositor** exists only when a dispositorship chain terminates in a
subject that is in its own domicile under the active rulership policy.

This is a narrow definition.

A final dispositor is not merely any endpoint where traversal happened to stop.
It is a terminal self-domiciled sovereignty condition.

### What a Terminal Cycle Is

A **terminal cycle** exists when dispositorship traversal enters a closed loop
that does not terminate in a self-domiciled endpoint.

Examples:

- two-node loop: mutual reception by domicile
- larger loop: three or more subjects disposing one another in a closed cycle

A terminal cycle is not a final dispositor. Both halt traversal, but they are
not doctrinally equivalent.

### What an Unresolved Termination Is

An **unresolved termination** exists when traversal cannot continue to a valid
next subject under the active policy and no legitimate final dispositorship or
terminal cycle classification has been reached.

Phase 1 should minimize unresolved terminations by constraining scope tightly,
but the termination class must still exist as a formal outcome.


## Why This Needs Explicit Policy

Dispositorship is not just a graph-walking convenience layer.

Changing any of the following changes the actual topology of the relation:

- the participating subject set
- the sign-rulership doctrine
- the handling of unsupported bodies

This means implementation choices that many systems treat as convenience flags
are in fact doctrinal acts.

For example:

- admitting Uranus as a participant without changing rulership tables produces
  one graph
- admitting Uranus and also replacing Aquarius' ruler with Uranus produces a
  different graph
- admitting Uranus while silently mapping it through Saturn produces yet a
  third graph

These are not equivalent results under a shared mathematical surface.

Therefore Moira must separate:

- who may participate
- who rules what
- what counts as a valid termination
- how unsupported subjects are treated
- how results are ordered for deterministic presentation


## Core Doctrinal Axes

### 1. Subject Set

This answers:

- which bodies are allowed to participate as graph subjects

Phase 1 Moira stance:

- the canonical subject set is `CLASSIC_7` only

Rationale:

- dispositorship is historically and computationally stable under the
  traditional seven-planet rulership scheme
- including outer planets is not a harmless enlargement of inputs; it changes
  the graph only if paired with a compatible rulership doctrine
- later admission of outer planets must be a deliberate policy act, not an
  ambient extension

### 2. Rulership Doctrine

This answers:

- which subject rules each sign for dispositorship purposes

Phase 1 Moira stance:

- dispositorship uses traditional domicile rulership only

That means:

- Aries, Scorpio -> Mars
- Taurus, Libra -> Venus
- Gemini, Virgo -> Mercury
- Cancer -> Moon
- Leo -> Sun
- Sagittarius, Pisces -> Jupiter
- Capricorn, Aquarius -> Saturn

Phase 1 excludes:

- modern outer-planet sign rulerships
- exaltation dispositors
- triplicity dispositors
- term/bound dispositors
- face/decan dispositors
- house dispositors

Those may become later named policies, but they must not be smuggled into the
baseline feature.

### 3. Chain Termination Semantics

This answers:

- what kinds of traversal outcomes are formally recognized

Phase 1 Moira stance:

- `final_dispositor` means termination in a self-domiciled endpoint
- `terminal_cycle` means entry into a closed loop, including mutual reception
- `unresolved` means traversal could not continue to a policy-valid next step

These classes are disjoint.

Mutual reception is not a final dispositor.
It is the two-node special case of terminal cycle.

### 4. Unsupported Subjects

This answers:

- what happens when the caller supplies bodies outside policy scope

Phase 1 Moira stance:

- unsupported subjects are ignored by default

Reason:

- rejection is too strict for the default mode when a mixed chart is supplied
- silent coercion or surrogate mapping is doctrinally dishonest
- ignoring out-of-scope subjects while exposing scope receipt is explicit,
  deterministic, and testable

Later policy may add:

- `reject` mode for strict validation
- `segregate` mode for reporting unsupported subjects without computing them

Phase 1 should not silently map unsupported subjects through borrowed rulers.

### 5. Ordering

This answers:

- how dispositorship summaries are presented deterministically

Phase 1 Moira stance:

- returned summaries should use the engine's established dignity-consistent
  planetary ordering rather than introducing a special dispositorship-only
  ordering

Ordering is a presentation stability policy, not doctrinal meaning.


## Phase 1 Scope Decision

Moira dispositorship Phase 1 should be deliberately narrow.

It should include:

- classical seven planets only
- sign derivation from existing longitude state
- traditional domicile ruler lookup
- deterministic dispositorship-chain traversal
- final-dispositor detection
- terminal-cycle detection
- explicit unresolved termination class

It should not include:

- interpretive scoring
- dignity weighting
- house rulership substitution
- outer-planet doctrine
- mixed rulership systems
- accidental condition synthesis
- chart-ruler or almuten claims

Phase 1 is about formalizing the relation cleanly, not exhausting every
possible interpretive use.


## Relationship To Existing Moira Subsystems

### Dignities

Dispositorship is adjacent to `dignities.py` because both depend on explicit
rulership doctrine.

However, dispositorship is not identical to:

- essential dignity
- mutual reception scoring
- condition-network scoring

Reception and dispositorship are related but not interchangeable:

- reception concerns a relation between planets across dignity ownership and,
  in formal historical usage, often involves aspectual awareness
- dispositorship concerns directed sign-rulership dependency regardless of
  aspect

Moira should not collapse the two into one layer merely because they share
rulership tables.

### Nine Parts

`nine_parts.py` already uses the local concept of a part's lord: the ruler of
the sign in which a Part falls.

That is compatible with dispositorship doctrine, but it is a localized use of
sign lordship inside one subsystem. It does not by itself constitute a general
dispositorship engine.

### Profections and Time Lords

`profections.py` and related timelord code already use sign-ruler logic for
annual lordship.

That logic is adjacent infrastructure, not dispositorship. A lord of a
profected sign is not the same object as the dispositor chain of the natal
planet occupying a sign.


## Recommended Policy Decomposition

Moira should keep the policy surface decomposed rather than collapsing multiple
meanings into one flag.

The conceptual policy families are:

- `subject_policy`
  defines who may participate in the graph
- `rulership_policy`
  defines who rules what
- `termination_policy`
  defines what counts as final, cyclic, or unresolved
- `unsupported_subject_policy`
  defines ignore, reject, or segregate behavior
- `ordering_policy`
  defines deterministic presentation order only

This separation matters because:

- admitting outer planets should not automatically imply modern sign rulership
- cycle detection should not imply final dispositorship
- presentation ordering should not affect computational truth


## Recommended Result Truth

Moira should preserve exact structural truth rather than forcing callers to
infer meaning from prose summaries.

The result model should distinguish at least:

- `subject_in_scope`
- `subject_has_dispositor`
- `termination_kind`
- `terminal_subjects`
- `cycle_members`

Additional useful distinctions may include:

- `initial_subject`
- `visited_subjects`
- `chain_length`
- `is_self_disposed`
- `ignored_subjects`

This keeps the engine exact while allowing higher layers to phrase the result
more naturally for users.


## Term Registry

Moira should use the following meanings consistently:

| Term | Meaning |
|---|---|
| dispositor | ruler of the sign occupied by a subject under active policy |
| dispositorship chain | repeated directed lookup of dispositors from an initial subject |
| final dispositor | self-domiciled terminal endpoint under active rulership policy |
| terminal cycle | closed dispositorship loop that halts traversal without yielding a final dispositor |
| mutual reception | the two-node special case of terminal cycle under domicile rulership |
| unsupported subject | body supplied to the computation but excluded by subject policy |
| unresolved termination | traversal outcome with no policy-valid continuation and no recognized final or cyclic termination |


## Phase 1 Ratified Working Stance

If Moira implements dispositorship in Phase 1, the governing doctrine should
be stated as follows:

- Moira dispositorship Phase 1 operates on `CLASSIC_7` only.
- A final dispositor exists only when a chain terminates in a self-domiciled
  endpoint under the active rulership policy.
- Detected cycles, including mutual reception, are terminal cycles and are not
  final dispositors.
- Unsupported subjects are ignored by default in Phase 1 unless a stricter
  policy is explicitly requested.
- Returned summaries use the engine's established dignity ordering for
  deterministic consistency.


## Deferred Questions

The following are intentionally deferred beyond Phase 1:

- whether outer planets may ever participate as subjects
- whether modern sign rulerships should be admitted at all
- whether exaltation, triplicity, term, or face dispositorship should exist as
  separate named doctrines
- whether house dispositors belong in the same subsystem or in a separate
  topical-rulership layer
- whether dispositorship should integrate with condition-network intelligence
- whether chart-wide summaries such as "dominant dispositing planet" are
  doctrinally justified or merely software conveniences

These are later policy and architecture questions, not Phase 1 prerequisites.


## Final Recommendation

Moira should implement dispositorship only after freezing it as an explicit
policy-bounded rulership relation.

The engine should prefer:

- narrow scope
- explicit rulership doctrine
- explicit termination classes
- visible unsupported-subject handling
- deterministic ordering
- structured result truth

It should avoid:

- ambient outer-planet admission
- silent ruler substitution
- treating cycles as final dispositors
- inferring computational truth from display strings
- interpretive inflation at the foundational layer

Dispositorship is suitable for Moira, but only if implemented as a governed
relation layer rather than a casual convenience feature.
