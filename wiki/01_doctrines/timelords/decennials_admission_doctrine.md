# Decennials Admission Doctrine

## Purpose

This document defines the pre-constitutional doctrine layer for Moira's
possible admission of the Hellenistic time-lord technique usually called
Decennials.

It also records the current admission verdict on the adjacent
Triacontaeteris family, because both techniques were audited together as
candidate additions to Moira's time-lord domain.

Before Moira implements Decennials, it must state clearly:

- whether a stable authoritative computational core is recoverable
- whether the technique belongs inside the current timelords constitutional
  family
- which doctrine is admitted, which doctrine is deferred, and why
- what research questions still remain open before Phase 1 work begins

This document is therefore pre-Phase-1 constitutional work. It is not an API
contract and not yet a backend standard.


## Executive Verdict

### Decennials

**Admission verdict: admitted to design research.**

Moira may proceed to a formal Phase-0 and pre-Phase-1 design pass for
Decennials.

Reason:

- the technique is a real member of the Hellenistic time-lord family
- the repository already has a natural constitutional home for it in the
  timelords domain
- the source lineage is strong enough to justify a non-speculative design pass
- the existing timelord architecture already contains the right structural
  patterns for period vessels, grouping, active-period lookup, and doctrine
  policy

### Triacontaeteris

**Admission verdict: constitutionally deferred pending source recovery.**

Moira should not implement Triacontaeteris at this time.

Reason:

- the architectural fit is plausible, but the doctrinal core is not yet stable
  enough to define one canonical engine
- the current source trail is too weak and too noisy to identify a single
  authoritative computational method without speculative reconstruction
- constitutional process forbids Phase 1 work when the governing doctrine is
  still hidden or materially ambiguous


## Why Decennials Is Admissible

### Technique Family Fit

Decennials belongs to the same broad predictive family as:

- Firdaria
- Zodiacal Releasing
- annual and monthly profections
- other chronocrator procedures already recognized in Moira's audit and
  timelord architecture

This means Decennials is not an alien subsystem requiring a new engine class.
It is a new technique within an already constitutionalized predictive family.

### Existing Moira Architectural Fit

Moira already has a constitutional timelords backend in:

- [wiki/02_standards/TIMELORDS_BACKEND_STANDARD.md](../../02_standards/TIMELORDS_BACKEND_STANDARD.md)

and a live implementation center in:

- [moira/timelords.py](../../../moira/timelords.py)

The current timelord architecture already admits the following kinds of objects:

- period truth vessels
- explicit doctrine/policy surfaces
- relational grouping over period hierarchies
- active-period lookup
- integrated condition profiles
- sequence-wide aggregates
- validation and hardening paths

Decennials appears structurally compatible with that family.

### Source Lineage Strength

The present research pass supports a real source lineage for Decennials through
serious Hellenistic-source custodians and modern source-aware witnesses.

Confirmed or near-confirmed witnesses include:

- Project Hindsight's Valens summary, which explicitly identifies a
  time-lord procedure called Decennials
- Project Hindsight's Hephaistio summary, which likewise identifies an
  exposition of the procedure later called Decennials
- the audit's prior domain-8 classification, which already treated
  Decennials as a legitimate absent technique rather than a doubtful one

This is sufficient for Moira to begin design research without pretending that
the full computational doctrine is already frozen.


## Why Triacontaeteris Is Deferred

### The Problem Is Not Desirability

Triacontaeteris may well be a real historical timing technique or family of
techniques. The problem is not whether it sounds plausible or interesting.

The problem is that Moira cannot yet state, with constitutional cleanliness:

- the canonical source text
- the exact starting rule
- the exact period arithmetic
- the exact sequencing logic
- whether one doctrine or multiple historical variants should be admitted

### Current Evidence Is Too Noisy

The additional research pass produced many results that referred to:

- calendar cycles
- chronological 30-year cycles
- general historical or mythic uses of the word

but not enough stable source-derived evidence for one clean astrological
chronocrator engine.

That is a constitutional stop sign, not a minor inconvenience.

### Constitutional Consequence

Triacontaeteris must remain on research hold until Moira can recover:

1. a primary or near-primary source witness
2. a stable rule set
3. a bounded doctrine statement that can be implemented without guesswork


## Decennials: Provisional Foundational Thesis

Pending the next design pass, Moira may treat Decennials under the following
working thesis only:

- Decennials is a planetary time-lord technique of Hellenistic lineage
- it assigns life periods to planets according to a fixed doctrinal order
- it likely depends on sect and/or the sect light as part of the starting
  condition
- it likely supports nested period structure rather than only a single flat
  sequence
- its rule set is close enough to the existing timelord family that it should
  be designed as a timelord engine rather than as a miscellaneous predictive
  helper

This thesis is admitted only as pre-constitutional research guidance. It is not
yet the implementation contract.


## Placement Doctrine

If Decennials proceeds, its natural home is presumptively:

- [moira/timelords.py](../../../moira/timelords.py)

not because all timing methods must be forced into one file, but because:

- the time-lord family is already constitutional there
- the current result-vessel patterns are reusable there
- the policy and hardening doctrine already exists there

This placement should remain provisional until the Decennials design pass
determines whether the current module can absorb one more technique without
losing doctrinal clarity.


## What the Next Research Pass Must Answer for Decennials

Before Phase 1 work begins, Moira should resolve the following explicitly:

1. What are the authoritative source witnesses for the computational method?
2. What determines the starting lord?
3. What are the exact major-period lengths?
4. Are sub-periods required for the minimum legitimate implementation?
5. What year basis is doctrinally admitted?
6. Are there multiple historical variants that must be surfaced as policy?
7. What belongs in the minimum engine, and what should be deferred?


## Research Pass Resolution

The present research pass resolves questions 1 through 7 as follows.

### 1. Authoritative source witnesses

The strongest currently recovered witnesses are:

1. **Hephaistio of Thebes, Apotelesmatica 2.29-36**
   This is the clearest recovered doctrinal exposition presently identified in
   the research pass. It explicitly describes a 129-month period, sect-light
   starting logic, and proportional internal subdivision.
2. **Vettius Valens, Anthologies**
   Valens provides practical use and computational examples, including the
   10-years-9-month major period and the 360-day distribution logic against
   ordinary 365 1/4-day life years.
3. **Firmicus Maternus, Mathesis 6.33-40**
   Firmicus confirms that Decennials was a real, established chronocrator
   procedure in the late antique Latin transmission and preserves a
   delineational tradition for when each planet becomes time-lord.

Moira's current source hierarchy for this technique should therefore be:

1. Hephaistio for the clearest recoverable method statement
2. Valens for practical computational witness and year-conversion logic
3. Firmicus for corroboration and delineational continuity

### 2. Starting lord

The minimum admitted doctrine is now:

- **start with the sect light**
- **Sun for day charts**
- **Moon for night charts**

Hephaistio's preserved wording, as quoted in the modern scholarly witness used
in this pass, explicitly says the sequence begins from the first luminary, the
one of the sect.

The sequence then proceeds by the planets encountered in zodiacal order from
that starting point.

Not yet admitted:

- alternate starting rules based on a non-luminary predominator
- fallback to the first planet after the Ascendant when the luminary is badly
  placed
- manual override as part of the canonical doctrine

Those may represent later source work or software conventions, but they are not
yet clean enough to admit as Moira doctrine.

### 3. Exact major-period lengths

The major periods are now resolved for the minimum doctrine:

- each major period is **129 months**
- that equals **10 years 9 months**
- seven major periods produce a full cycle of **903 months**
- that equals **75 years 3 months**

Within the sequence, each major lord receives the same outer period length.

The internal month-allotment pattern used for subdivision is the unequal
planet-specific pattern preserved in the tradition. In the recovered sources
and operational witnesses used here, this pattern is:

- Saturn: 30 months
- Jupiter: 12 months
- Mars: 15 months
- Venus: 8 months
- Mercury: 20 months
- Moon: 25 months
- Sun: 19 months

These sum to 129 months and define the internal proportional arithmetic.

### 4. Whether sub-periods are required

Yes, internal subdivision is required for minimum legitimate admission.

Reason:

- Hephaistio explicitly describes internal subdivision
- Valens explicitly works with major periods and their month/day breakdown
- the historical technique is not merely a flat ladder of 10-year-9-month
  planetary decades

However, Moira does **not** need to admit every possible depth level in the
first implementation.

Minimum legitimate computational core:

- **L1 major periods**
- **L2 internal sub-periods**

Deeper levels may be admitted later under explicit policy.

So the constitutional answer is:

- **major-only** is too thin
- **L1 + L2** is sufficient for minimum admission

### 5. Year-basis doctrine

The year basis is resolved as a **dual-basis doctrine**, not a single scalar.

Recovered Valens logic shows:

- ordinary lived years are reckoned against the real year
- the internal Decennial distribution arithmetic is reckoned on a **360-day**
  schematic basis

This means Moira should admit the following rule:

- **internal period arithmetic uses the 360-day distribution year**
- **projection from natal chronology into lived time must remain explicit**

In other words, the technique is not simply "365.25 everywhere" and not simply
"360 everywhere." The doctrinal core is the interaction between real elapsed
life and a schematic 360-day distribution model.

### 6. Variants and policy surfaces

The research pass supports one immediately admissible future policy distinction
and two deferred ones.

Phase-4 policy candidate now admitted:

- **deep-subdivision method**: `valens` vs `hephaistio`

Reason:

- modern operational witnesses consistently report that Valens and Hephaistio
  agree on the first internal layer but diverge once deeper day/hour-style
  subdivision is pursued
- the present source pass supports a sharper admission boundary:
  - `valens`: admissible for day and hour subdivision
  - `hephaistio`: admissible for day subdivision, but not yet for hour
    subdivision

Policy surfaces still deferred:

- alternate starting-lord doctrine
- alternate calendar projection conventions beyond the explicit dual-basis core

So the minimum constitutional stance is:

- admit one canonical sect-light start
- admit L1 + L2 as the minimum engine
- admit `valens|hephaistio` as the one clean policy branch for future deeper
  implementation
- admit `valens` for `L3 + L4`
- admit `hephaistio` for `L3` only
- keep `hephaistio L4` deferred pending a stronger direct witness
- keep that branch dormant unless deeper subdivision is actually implemented

### 7. Minimum engine vs deferred work

The minimum admitted engine should include:

- a Decennials core computation in the timelords family
- explicit `is_day_chart` input for sect
- natal longitudes for the seven classical planets sufficient to determine the
  zodiacal sequence from the sect light
- L1 major-period generation
- L2 sub-period generation
- active-period lookup for a target date or age
- truth-preservation vessels for Decennial periods
- validation of sequence ordering, containment, and cycle arithmetic

What should be deferred:

- all runtime implementation of L3 and L4 until a dedicated design pass occurs
- `hephaistio` hour-level (`L4`) subdivision
- alternate starting-lord doctrine
- delineation libraries for each planetary period
- aggregate and network layers until the Phase-1 and Phase-2 core is stable

So the smallest constitutionally honest Decennials engine is:

- one admitted source-derived starting rule
- one admitted major-period arithmetic
- one admitted L2 subdivision layer
- one explicit dual-basis time model

That is enough to begin Phase 1 work without pretending that every historical
variant has already been recovered.


## Decennials Admission Packet

The research pass therefore admits the following Decennials doctrine packet:

- **family:** Hellenistic planetary chronocrator technique
- **starting lord:** sect light only
- **sequence rule:** planets encountered in zodiacal order from the sect light
- **major period length:** 129 months for each major lord
- **cycle length:** 75 years 3 months across seven major lords
- **minimum depth:** L1 + L2
- **internal arithmetic basis:** 360-day distribution logic
- **projection doctrine:** explicit conversion from lived chronology to
  schematic distribution time
- **admitted future policy branch:** `valens|hephaistio` for deeper
  subdivision only
- **admitted deeper-boundary:** `valens` supports `L3 + L4`; `hephaistio`
  supports `L3` only on current evidence
- **deferred variants:** alternate start doctrine, alternate calendar
  projection doctrine, `hephaistio L4`, richer delineational and aggregate
  layers


## Admission Boundary

The following statement is now admitted:

> Decennials is constitutionally eligible for Moira pre-implementation design
> research inside the timelords family.

The following statement is not yet admitted:

> Triacontaeteris has a sufficiently recovered doctrine to justify Phase 1
> implementation work.


## Sources Used For This Admission Verdict

- [wiki/00_foundations/CONSTITUTIONAL_PROCESS.md](../../00_foundations/CONSTITUTIONAL_PROCESS.md)
- [wiki/02_standards/TIMELORDS_BACKEND_STANDARD.md](../../02_standards/TIMELORDS_BACKEND_STANDARD.md)
- [wiki/07_audit/FEATURE_AUDIT_2026.md](../../07_audit/FEATURE_AUDIT_2026.md)
- Michael Zellmann-Rohrer, "The Chronokratores in Greek Astrology, in Light of
  a New Papyrus Text":
  https://refubium.fu-berlin.de/bitstream/handle/fub188/40514/The%20Chronokratores%20in%20Greek%20Astrology.pdf?isAllowed=y&save=y&sequence=1
- Vettius Valens, *Anthologies* (Mark T. Riley translation):
  https://www.skyscript.co.uk/pdf/pubs/texts/valens/griscti/docs/Valens-Anthologies.pdf
- Project Hindsight Valens summary:
  https://www.projecthindsight.com/products/greek%20summaries/valens.html
- Project Hindsight Hephaistio summary:
  https://projecthindsight.com/products/greek%20summaries/hephaistio.html
- AstroApp operational note on Decennials:
  https://astroapp.com/help/1/decennials.html
- operational modern Decennials witness for method-shape only:
  https://sirauysal.com/en/tools/decennials/
