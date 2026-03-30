# Lord of the Turn Roadmap

## Purpose

This document defines the implementation roadmap for Moira's Lord of the Turn
subsystem.

It assumes the companion doctrine document exists:

- [lord_of_the_turn_doctrine.md](lord_of_the_turn_doctrine.md)

This is a **source-verification-first roadmap**. The Lord of the Turn is the
least-documented of the four Medieval Time Lord techniques Moira needs to
implement. Unlike the Lord of the Orb (which has confirmed formulas and a
clean arithmetic engine), the Lord of the Turn requires source confirmation
of its sensitive-point set and dignity algorithm before Phase 1 can begin.

The Al-Qabisi and Egyptian/Al-Sijzi variants are currently at different
documentation levels:

- **Al-Qabisi** — structure documented in secondary literature (almuten
  over solar return chart points); precise sensitive-point set and weighting
  scheme need source confirmation from Burnett/Yamamoto/Yano or Dykes
- **Egyptian/Al-Sijzi** — real as a tradition family; mechanics not yet
  confirmed at implementation level; requires source disambiguation before
  any design work

Current SCP status: `P0` — pre-constitutionalization; source verification
required before P1 can begin.


## Current Moira State

Relevant implementation files:

- `moira/longevity.py` — `dignity_score_at()` function; almuten-style dignity
  scoring; Egyptian bounds, triplicity rulers, face rulers
- `moira/lots.py` — lot positions available as solar return chart inputs
- `moira/dignities.py` — dignity infrastructure

Lord of the Turn: `NOT IMPLEMENTED`.

Infrastructure available:

- `dignity_score_at(longitude, planet, chart)` in `longevity.py` — this is
  structurally what the Lord of the Turn needs applied over solar return
  chart points
- Egyptian bounds, triplicity rulers, face rulers all in `longevity.py`
- Solar return chart calculation available via `moira/progressions.py` or
  equivalent

The core dignities infrastructure is present. The gap is:
1. which chart points to score over (source confirmation needed)
2. whether to use the natal chart, solar return chart, or both as the
   evaluation frame
3. how Al-Qabisi's weighting scheme differs from the generic almuten


## Core Insight

The Lord of the Turn is an almuten-over-solar-return calculation. The
dignity-scoring infrastructure already in `longevity.py` is the right engine.
The work is:

1. confirm which sensitive points are used (source verification)
2. confirm the weighting scheme (may differ from Hyleg almuten)
3. design the solar return chart input contract
4. implement Al-Qabisi first; Egyptian/Al-Sijzi second after disambiguation

This is not a mathematically novel technique — it reuses dignity infrastructure
that already exists. The uncertainty is doctrinal, not computational.


## Truth Domain Axes

### 1. Method Variant

Governs which Lord of the Turn algorithm is applied.

Values:

- `al_qabisi` — almuten over a confirmed set of solar return chart points
  per Al-Qabisi's *Introduction*; **implement first**
- `egyptian_al_sijzi` — Egyptian tradition as transmitted/modified by Al-Sijzi;
  **deferred until source disambiguation complete**

### 2. Sensitive Points Set

Governs which chart points are scored in the almuten calculation.

Known candidates (require source confirmation for Al-Qabisi):

- solar return Ascendant degree
- solar return Midheaven degree
- solar return Sun position
- solar return Moon position
- Lot of Fortune in the solar return
- natal Ascendant degree (carried into the return frame)

**This axis must be confirmed from source before Phase 1 design is finalized.**

### 3. Dignity Weights

Governs how dignity types are weighted in the almuten scoring.

The generic almuten weights (domicile 5, exaltation 4, triplicity 3, term 2,
face 1) may or may not match Al-Qabisi's specific scheme.

**Requires source confirmation.**

### 4. Dignity Table

Governs which bounds and triplicity systems are used.

Default assumption: Egyptian bounds and Dorothaean triplicity rulers, matching
the existing `longevity.py` infrastructure. Confirm against Al-Qabisi source.

### 5. Evaluation Frame

Governs whether the natal chart, the solar return chart, or both participate
in selecting the Lord of the Turn.

Selection: likely solar return chart points only.
Interpretation: natal condition of the winning planet applies after selection.


## Pre-Phase-1 Verification Tasks

These must be completed before Phase 1 implementation begins.

### V1 — Confirm Al-Qabisi Sensitive Points

**Source:** Charles Burnett, Keiji Yamamoto, Michio Yano (trans.), *Alcabitius:
The Introduction to Astrology* (Warburg Institute, 2004).

**Target section:** Al-Qabisi's treatment of the annual revolution; Lord of
the Turn (or equivalent terminology in the translation).

**Output:** a confirmed list of sensitive points and any stated weighting
scheme.

### V2 — Confirm Egyptian/Al-Sijzi Distinction

**Source:** Benjamin N. Dykes, *Works of Sahl and Masha'allah* (Cazimi Press,
2008); *The Book of Nine Judges* (Cazimi Press, 2011).

**Question:** is "Egyptian/Al-Sijzi" one method (Al-Sijzi transmitting the
Egyptian tradition) or two distinguishable methods?

**Output:** a confirmed answer + the sensitive-point set for the Egyptian
variant.

### V3 — Confirm Dignity Weights

**Question:** does Al-Qabisi use the standard almuten weights or a modified
scheme for the Lord of the Turn?

**Output:** confirmed weight values or confirmation that standard weights apply.


## Implementation Phases

### Phase 1 — Al-Qabisi Lord of the Turn

**Prerequisite:** V1 and V3 complete.

**Scope:** compute the Lord of the Turn for a given year using Al-Qabisi's
confirmed algorithm.

**Module:** `moira/timelords.py` or a new `moira/annual_indicators.py`
(decision deferred to SCP module boundary work)

**Tasks:**

1. Define `LordOfTurnMethod` enum: `AL_QABISI`, `EGYPTIAN_AL_SIJZI`
2. Define `LordOfTurnResult` data vessel:
   - `planet: str`
   - `method: LordOfTurnMethod`
   - `score: float` (dignity score of the winning planet)
   - `scores: dict[str, float]` (all candidate scores for transparency)
3. Add `lord_of_turn_al_qabisi(natal_chart, solar_return_chart) -> LordOfTurnResult`
4. Reuse `dignity_score_at()` from `longevity.py` as the scoring engine;
   do not duplicate the dignity logic

**Acceptance criteria:**

- returns a single winning planet with its dignity score
- exposes all candidate scores so the caller can inspect the result
- uses confirmed sensitive points from V1
- uses Egyptian bounds and confirmed triplicity rulers
- does not modify `longevity.py`

**SCP target:** P1 COMPLETE after this phase.

---

### Phase 2 — Egyptian/Al-Sijzi Variant

**Prerequisite:** Phase 1 complete; V2 complete.

**Scope:** add the Egyptian/Al-Sijzi variant as a second named method.

**Tasks:**

1. Implement `lord_of_turn_egyptian_al_sijzi(natal_chart, solar_return_chart)`
   using the confirmed sensitive-point set from V2
2. Add `EGYPTIAN_AL_SIJZI` to `LordOfTurnMethod`
3. If the two methods share the same algorithm with different point sets,
   unify under a single parameterized function; if they differ structurally,
   keep them as separate implementations

**SCP target:** P2 COMPLETE after this phase.

---

### Phase 3 — Annual Hierarchy Integration

**Scope:** integrate Lord of the Turn alongside Lord of the Orb and other
annual indicators in the Abu Ma'shar eight-indicator hierarchy.

**Prerequisite:** Phase 1 complete; Lord of the Orb Phase 2 complete.

**Note:** the Lord of the Turn is not explicitly ranked in Abu Ma'shar's
eight-indicator list (which names Lord of the Orb as indicator #6). The
Lord of the Turn may be a separate tradition's primary governor or may map
to a different position in the hierarchy. Do not assign a rank without
source confirmation.


## Relationship to Other Subsystems

| Subsystem | Relationship |
|---|---|
| `longevity.py` | `dignity_score_at()` is the scoring engine; do not modify |
| `timelords.py` | natural home for annual indicators |
| Lord of the Orb | separate technique; shares annual timing context |
| Nine Parts | Al-Sijzi's Part mechanics intersect; coordinate Phase 2 of both |

The Lord of the Turn is the only Medieval Time Lord technique that requires
a solar return chart as input. The solar return chart input contract should
be designed to match whatever solar return chart interface Moira establishes
elsewhere.


## Open Questions

1. Should `lord_of_turn()` and `lord_of_orb()` share a module, or should
   annual indicators be split into their own file?
2. Is there a solar return chart type already in Moira (via `progressions.py`
   or `chart.py`)? This determines the input contract for Phase 1.
3. Does Al-Qabisi's Lord of the Turn map to Abu Ma'shar's ranked hierarchy,
   or is it a parallel tradition's equivalent concept?


## Research Sources

- Charles Burnett, Keiji Yamamoto, Michio Yano (trans.), *Alcabitius: The
  Introduction to Astrology* (Warburg Institute, 2004) — primary source for
  V1 verification
- Benjamin N. Dykes, *Persian Nativities III* (Cazimi Press, 2010) — annual
  revolution system context
- Benjamin N. Dykes, *Works of Sahl and Masha'allah* (Cazimi Press, 2008) —
  related annual techniques; Egyptian tradition context
- Benjamin N. Dykes, *The Book of Nine Judges* (Cazimi Press, 2011) —
  Al-Sijzi context
- `moira/longevity.py` — `dignity_score_at()`, `EGYPTIAN_BOUNDS`,
  `TRIPLICITY_RULERS` — existing scoring infrastructure
