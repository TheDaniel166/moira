# Swiss Family Gap Ledger (2026-04-09)

Purpose:
- convert the family-level Swiss HTML audit into a concrete Moira-native gap ledger
- identify the remaining frontier work by subsystem, not by Swiss flag or function name
- distinguish between missing capability, partial public surfacing, validation debt, and intentional exclusion

Primary inputs:
- `wiki/03_validation/SWISS_HTML_FAMILY_COVERAGE_AUDIT_2026-04-09.md`
- local Swiss HTML: `C:\Users\nilad\Downloads\swisseph documentation.html`
- current runtime modules in `moira/`
- existing Swiss migration docs in `wiki/03_validation/`

This document is not a parity backlog.
It is a frontier ledger for deciding what still requires explicit Moira decisions.

## Gap Kinds

- `surface_gap`
  A legitimate domain capability is not yet exposed as a stable public Moira surface.
- `coverage_gap`
  A subsystem exists, but only covers part of the family implied by the Swiss section.
- `validation_gap`
  A subsystem exists, but its validation story is not yet broad enough for stronger claims.
- `doctrine_gap`
  The mathematics or domain is real, but the correct Moira policy surface is not yet settled.
- `intentional_exclusion`
  Swiss includes this family, but Moira should not absorb it into the main public engine.

## Priority Tiers

- `Tier 1`
  Real frontier with immediate architectural value.
- `Tier 2`
  Valid expansion area, but not yet the sharpest gap.
- `Tier 3`
  Lower-value, speculative, or intentionally segregated.

## Ledger

### 1. Heliacal and generalized visibility

Status:
- subsystem exists and is materially stronger than the initial family audit implied
- remaining work is mostly `validation_gap` plus some `coverage_gap`

Current admitted surface:
- `moira.heliacal`
- typed event taxonomy via `HeliacalEventKind`
- generalized visibility surfaces for planets, stars, and Moon
- observer-environment policy
- Yallop lunar crescent validation
- Krisciunas & Schaefer 1991 moonlight model admitted partially

Open gaps:
- `validation_gap`:
  broader stellar heliacal validation corpus beyond the narrow anchor cases
- `validation_gap`:
  live-ephemeris integration corpus for moonlight-aware visibility
- `coverage_gap`:
  terrain or horizon-profile aware visibility is still deferred
- `doctrine_gap`:
  summit-grade generalized visibility validation across criterion families is not yet closed

Tier:
- `Tier 1`

Why:
- this is already a real subsystem with strong doctrinal shape
- the remaining work is mostly closure and proof, not invention

### 2. Nodes and apsides

Status:
- strong lunar-node surface exists
- broader Swiss family still outruns the currently explicit Moira public layer

Current admitted surface:
- `moira.nodes`
- `mean_node(...)`
- `true_node(...)`
- `mean_lilith(...)`
- `true_lilith(...)`
- `next_moon_node_crossing(...)`
- `nodes_and_apsides_at(...)`

Open gaps:
- `coverage_gap`:
  broader planetary nodes and apsides family is not yet a clearly exposed public subsystem
- `surface_gap`:
  explicit named apsides products beyond the current lunar-focused surfaces may need clearer public admission
- `validation_gap`:
  no dedicated external-reference corpus is obvious for a wider nodes-and-apsides family
- `doctrine_gap`:
  if non-lunar apsides are exposed, their product semantics must remain explicit rather than Swiss-selector based

Tier:
- `Tier 1`

Why:
- Swiss gives this family significant weight
- Moira already has real infrastructure here, but the family boundary is still narrower than the Swiss section inventory

### 3. Center-relative, center-of-body, and planetary-moon products

Status:
- several important capabilities exist
- the family is fragmented across modules and still feels more specialist than first-class

Current admitted surface:
- `moira.planets.planet_relative_to(...)`
- barycentric and heliocentric support in `moira.planets`
- `moira.planetocentric`
- `moira.ssb`

Open gaps:
- `coverage_gap`:
  planetary-moon coverage is not yet a clearly documented first-class public family
- `surface_gap`:
  center-of-body and moon-family semantics are spread across relative-center helpers rather than one visible subsystem doctrine
- `validation_gap`:
  the Swiss appendix emphasizes moon and center-of-body comparison cases; Moira does not yet appear to have a named validation program for this whole family
- `doctrine_gap`:
  a public “body-center” family needs tighter product semantics before expansion

Tier:
- `Tier 1`

Why:
- the underlying substrate is already largely present
- what is missing is coherent public family definition and validation framing

### 4. Comets and interstellar objects

Status:
- architecturally plausible, but not yet a broad public subsystem

Current admitted surface:
- partial doctrinal treatment in `wiki/01_doctrines/BEYOND_SWISS_EPHEMERIS.md`
- related minor-body architecture in asteroid and orbit layers

Open gaps:
- `surface_gap`:
  no clearly admitted public comet surface is visible
- `surface_gap`:
  no clearly admitted public interstellar-object surface is visible
- `validation_gap`:
  no obvious external-reference suite is established for these families
- `doctrine_gap`:
  product boundaries for newly discovered objects need explicit provenance and kernel policy

Tier:
- `Tier 2`

Why:
- this is strategically important, but less foundational than closing already-active families

### 5. Hypothetical bodies beyond the admitted Uranian layer

Status:
- mostly intentional non-expansion

Current admitted surface:
- `moira.uranian`

Open gaps:
- `intentional_exclusion`:
  obsolete or physically unsupported hypothetical bodies should not be folded into the astronomical substrate by default
- `doctrine_gap`:
  if any additional hypothetical family is ever admitted, it must be isolated doctrinally from physical-body computation

Tier:
- `Tier 3`

Why:
- Swiss includes a broad hypothetical family, but most of it is not a desirable Moira expansion target

### 6. API and utility equivalence pressure

Status:
- mostly intentional non-equivalence

Current admitted surface:
- constructor and kernel-path setup
- typed helpers across `moira.julian`, `moira.coordinates`, `moira.planets`, `moira.houses`, and related modules

Open gaps:
- `intentional_exclusion`:
  Swiss global mutable setup and flag bundles should not be mirrored
- `intentional_exclusion`:
  Swiss numeric selectors, file-path constants, and backend constants should remain out of the public Moira surface

Tier:
- `Tier 3`

Why:
- these are not real Moira deficits
- they only appear as gaps if Swiss API shape is mistaken for domain coverage

## Ranked Frontier Summary

The strongest real frontier families, in order:

1. Heliacal and generalized visibility closure
2. Nodes and apsides family expansion
3. Center-relative / center-of-body / planetary-moon family consolidation
4. Comets and interstellar objects

The strongest false-gap families, which should not drive design:

1. Swiss API utility/count equivalence
2. Swiss internal flags and backend controls
3. Swiss hypothetical-body sprawl beyond clearly admitted doctrine

## Recommended Next Passes

### Pass A: Heliacal closure audit

Goal:
- separate remaining validation debt from true missing capability

Concrete questions:
- which Swiss heliacal event semantics are already covered by `HeliacalEventKind`?
- which Swiss option families are already replaced by `VisibilityPolicy` and `VisibilitySearchPolicy`?
- what exact validation corpora are still missing for stronger confidence claims?

### Pass B: Nodes and apsides semantic inventory

Goal:
- define exactly what products belong in a Moira-native nodes-and-apsides family

Concrete questions:
- which current `moira.nodes` outputs are lunar-only?
- which Swiss products imply non-lunar nodes or apsides that Moira does not yet expose?
- what authoritative oracle should govern each admitted product class?

### Pass C: Center-relative and planetary-moon family audit

Goal:
- decide whether the existing relative-center substrate is sufficient, or whether a unified public doctrine layer is needed

Concrete questions:
- what is already covered by `planet_relative_to(...)`, `moira.planetocentric`, and `moira.ssb`?
- what Swiss center-of-body and moon products still lack a visible Moira family surface?
- what validation program would make this family trustworthy?

## Immediate Conclusion

The first step after the family audit is not code expansion.

It is to turn the three real frontier families into sharper subsystem audits:
- heliacal
- nodes and apsides
- center-relative / planetary-moon

That preserves Moira's doctrine:
- family coverage first
- typed design second
- implementation third
- validation-backed claims last
