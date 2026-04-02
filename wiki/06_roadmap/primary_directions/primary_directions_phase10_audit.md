# Primary Directions Phase 10 Audit

## Purpose

This document audits the current constitutional state of Moira's primary-directions
subsystem against the governing constitutional doctrine.

It exists because the primary-directions packet now contains a real mismatch:

- the implementation and feature surface have widened substantially
- the roadmap claims top-level completion through `P12`
- but the doctrine packet and backend standard still preserve an older,
  narrower constitutional story

That mismatch had to be resolved before Moira could honestly treat the
subsystem as walked through Phase 10 and beyond.


## Governing Constitutional Standard

From [wiki/00_foundations/CONSTITUTIONAL_PROCESS.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki/00_foundations/CONSTITUTIONAL_PROCESS.md):

- `Phase 10 - Full-Subsystem Hardening`
  - freeze cross-layer invariants
  - freeze deterministic ordering
  - freeze failure behavior
  - freeze misuse resistance across the whole subsystem
- `Phase 11 - Architecture Freeze and Validation Codex`
  - write the backend standard for the subsystem as it actually exists
- `Phase 12 - Public API Curation`
  - expose only the stable constitutional surface publicly

This means:

- `P10` is not satisfied merely because many features exist
- `P10` requires cross-layer consistency across the actual admitted subsystem
- `P11` and `P12` cannot honestly outrun a stale or narrower `P10` story


## Current Evidence

Current implementation truth, as reflected across the runtime and doctrine
packet, includes:

- `8` runtime-admitted geometry families
- `2` admitted spaces:
  - `In Mundo`
  - `In Zodiaco`
- `2` admitted motion doctrines:
  - `Direct`
  - `Traditional converse`
- explicit relation doctrine
- explicit preset doctrine
- validated narrow target families:
  - zodiacal aspect-points
  - Ptolemaic parallels / contra-parallels
  - Placidian rapt parallels
  - fixed stars
  - antiscia / contra-antiscia

This is materially broader than the current backend standard in
[PRIMARY_DIRECTIONS_BACKEND_STANDARD.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki/02_standards/PRIMARY_DIRECTIONS_BACKEND_STANDARD.md),
which still declares itself authoritative only for:

- `Placidus mundane`
- `In Mundo`
- `Traditional converse` or `Direct only`

The doctrine packet in
[primary_directions_doctrine.md](c:/Users/nilad/OneDrive/Desktop/Moira/wiki\01_doctrines\primary_directions\primary_directions_doctrine.md)
formerly named itself as a `pre-constitutional doctrine layer`; the current alignment pass
corrects that older packet language.


## Audit Judgment

### What is true already

The subsystem appears to satisfy a large portion of Phase 10 in substance:

- cross-layer doctrine owners now exist
- deterministic ordering is stated in the older backend standard and exercised
  through the runtime
- failure behavior is explicit in many runtime entry points
- misuse resistance is materially better because branch presets, relation
  doctrine, and target gating now exist

### What is not yet true enough

The subsystem is not yet *constitutionally clean* at Phase 10+ because the
packet is inconsistent about what the subsystem actually is.

Current contradictions:

- the roadmap says top-level `P1` through `P12` are complete
- the doctrine packet says constitutional process should only continue after the current packet
- the backend standard freezes only an older narrow branch
- the feature list describes a much larger admitted subsystem

That means the main deficit is no longer missing feature code.

The main deficit was:

- stale constitutional documents
- stale freeze boundary
- stale validation codex scope


## Phase 10 Status

### Top-level judgment

The constitutional alignment pass has now produced:

- a rewritten backend standard for the actual admitted surface
- an explicit subsystem alignment ledger
- an invariant register
- a validation codex

Primary directions may now be treated as constitutionally closed through the
current freeze surface.

### Why this matters

If the standard and doctrine remain narrower than the admitted runtime, then:

- invariants are only partially frozen
- failure doctrine is only partially frozen
- public API curation is only partially justified

That is exactly the kind of epistemic mismatch constitutional process is designed to prevent.


## Work Required For Honest Phase 10+ Closure

This work was packet hardening, not family expansion.

Required steps:

1. rewrite the primary-directions backend standard so it describes the current
   admitted subsystem rather than the old Placidian-only narrow branch
2. explicitly restate the cross-layer invariants for the current admitted
   surface:
   - method/space/preset ownership
   - relation gating
   - target-family gating
   - deterministic ordering
   - failure contracts
3. rewrite the validation codex so it names the actual targeted verification
   expected for the current subsystem
4. re-check the public API curation against the broadened admitted surface
5. update the doctrine packet so it no longer calls itself merely `pre-constitutional`
   where that is no longer true


## Policy Line

The correct current policy is:

> The primary-directions subsystem is now baseline-complete on the currently
> recoverable doctrinal surface, but it should not be treated as fully frozen
> through Constitutional Phase 10 and beyond until the constitutional packet is updated to
> match the admitted runtime truth.


## Immediate Recommendation

Primary directions may now rest at the current recoverable constitutional
surface.

Any future widening should proceed only as:

- frontier research
- or explicit constitutional revision

