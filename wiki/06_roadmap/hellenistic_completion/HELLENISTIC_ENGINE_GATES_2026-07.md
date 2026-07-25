# Hellenistic Engine Gate Roadmap

Date: 2026-07-25
Scope: `moira/` engine truth first; transport, product composition, and website
work only at their named later gates.

This is the current six-gate Hellenistic roadmap. It supersedes the phase
numbering in the older additive completion roadmap for current work. In
particular, “Phase 2” here means doctrine decisions, not the historical
“Bounds Expansion and Halb” phase.

## Gate Status

| Phase | Gate | Status | Boundary |
|---|---|---|---|
| 1 | False-output containment | Complete | Incorrect or unadmitted Hellenistic outputs fail closed; Decennial L3/L4 and Hermetic public surfaces remain quarantined. |
| 2 | Doctrine decisions | Complete | The disputed profection, Decennial, Halb/Hayz, ZR, lot, and Hermetic-catalog rules have explicit source or policy decisions. |
| 3 | Typed truth composition | Pending | Replace collapsed labels/defaults with typed component and `not_evaluable` truth. |
| 4 | Contract parity | Pending | Audit effective policy and provenance parity across exports, facade, serializers, REST models, and OpenAPI. Existing partial transport is not a parity receipt. |
| 5 | Unified Hellenistic profile | Pending | Compose a non-interpretive chart profile only from atomic admitted receipts. |
| 6 | Validation and documentation regeneration | Pending | Add independent source-owned goldens, regenerate inventories/matrices, archive stale completion claims, and only then update website documentation. |

## Phase 2 Closure Receipt

### Profection anniversary semantics

Annual profection schedules use completed civil anniversaries in the natal
timezone. February 29 births require an explicit February 28 or March 1 policy.
Elapsed fractional Julian years are not used as civil age.

### Decennial projection semantics

Decennials preserves two coordinates instead of collapsing them:

- a 30-day-month / 360-day-year distribution coordinate
- an elapsed-Julian-day projection from `sequence_origin_jd`

Projected JDs are not represented as civil-month anniversaries. L3/L4 and both
named deep-subdivision candidates remain quarantined.

### Halb and Hayz

Halb uses the admitted al-Qabisi/Bonatti sect-relative hemisphere rule. Hayz
adds the planet's own sign gender. Mars is feminine; Mercury is neutral and
requires explicit sect-phase truth rather than a fabricated default.

### Zodiacal Releasing

Valens, *Anthologies* IV.4 governs two source fixtures:

- when Spirit and Fortune are in the same sign, Spirit's activity sequence
  begins in the following sign
- a long-sign subordinate sequence transfers to the opposite sign at the exact
  211-month circuit boundary

The Gemini fixture reaches Sagittarius after 211 months, remains there for 12
months, and uses the final 17 months in Capricorn. The source prose and
explanatory note govern; the inconsistent intervening numerical table does not.

Engine receipt: `tests/fixtures/hellenistic_zr_valens_iv4.json`.

### Conflicted lots

`PartDefinition` now carries an explicit projector and directed-versus-shortest
arc policy. Computation truth preserves both.

- `Theft (Valens)` projects Mercury→Mars from Saturn by day and reverses the
  operands at night.
- `Basis (Valens)` projects the shorter Fortune/Spirit interval from the
  Ascendant.
- `Debt (Valens)` and `Debt (Abu Mashar via al-Biruni)` remain distinct
  source-named formulas.
- The al-Bīrūnī glyph/continuation-mark conflicts for Illness and the two
  Valens marriage lots are resolved without inventing reversals.
- `Knowledge, True or False (Abu Mashar via al-Biruni)` is the source-specific
  Jupiter→Moon formula without night reversal.

Research receipt:
`wiki/05_research/lots/LOTS_SOURCE_VERIFICATION.md`.

### Hermetic catalog reconstruction

The 36-name catalog has been reconstructed from Wilhelm Gundel,
*Dekane und Dekansternbilder* (1936), pp. 379-383, “Die lateinische
Dekanliste des Hermes Trismegistos,” transcribing British Library Harley
MS 3731, ff. 1r-50r.

The engine preserves each entry's sign, ordinal, name, planetary face, edition
page, and source identifier. The identified edition does not supply the former
fixed-star assignments, so those accessors fail closed. Modern lookup, rising,
and night-hour geometry remain research-quarantined pending later gates.

Engine receipt: `moira/hermetic_decans.py`.
Standard: `wiki/02_standards/DECANS_BACKEND_STANDARD.md`.

## Phase 2 Exit Criteria

Phase 2 is closed only because:

1. every named doctrine conflict above has an explicit source or policy
   decision;
2. the engine no longer fabricates the disputed result;
3. focused tests and the ZR source-locked fixture cover the corrected behavior;
4. quarantined material remains unavailable through curated public surfaces;
5. no Phase 3 composition, Phase 4 parity claim, Phase 5 profile, or website
   admission is implied.

The next authorized gate is Phase 3, typed truth composition.
