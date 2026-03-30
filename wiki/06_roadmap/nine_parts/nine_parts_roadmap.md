# Nine Parts Roadmap

## Purpose

This document defines the implementation roadmap for Moira's Nine Parts
subsystem.

It assumes the companion doctrine document exists:

- [nine_parts_doctrine.md](nine_parts_doctrine.md)

This is an **additive roadmap**, not a refactor-first roadmap. The lot engine
in `moira/lots.py` already provides the full arc-formula infrastructure. The
work is scoped to: cataloguing the seven externally evidenced Abu Ma'shar lots
as the historical core, preserving the Sword and Node as admitted extensions,
and providing a dedicated query surface.

The Vedic Navamsha is treated as a separate implementation track within this
same roadmap because it shares only the number nine with the Abu Ma'shar lots
— not the formula engine.


## Current Moira State

Relevant implementation file: `moira/lots.py`

Current admitted capability relevant to Nine Parts:

- `~430+` named lots in `PARTS_DEFINITIONS`
- Full arc-formula engine: `Asc + A − B mod 360°`
- Automatic day/night reversal per `PartDefinition.reversible` flag
- Fortune and Spirit pre-computed before derived lots (dependency order
  already handled)
- `ArabicPartsService` — service class for computing lots from a chart
- `calculate_lots()` — module-level convenience wrapper

Lots from Abu Ma'shar's Nine Parts already in the catalogue:

| Abu Ma'shar Part | Existing Entry | Formula Match | Reversal |
|---|---|---|---|
| Fortune | `"Fortune"` | Moon − Sun | ✓ |
| Spirit | `"Spirit"` | Sun − Moon | ✓ |
| Love | `"Eros (Valens)"` | Spirit − Fortune | ✓ |
| Necessity | `"Necessity (Valens)"` | Fortune − Spirit | ✓ |
| Courage | `"Courage"` | Fortune − Mars | ✓ |
| Victory | `"Victory"` | Jupiter − Spirit | ✓ |
| Nemesis | `"Nemesis"` | Fortune − Saturn | ✓ |
| The Sword | not named "Sword" | Mars − Saturn | ✓ (via other entries) |
| The Node | not present | Node − Moon | — |

Gap summary:

- `The Sword` — the Mars − Saturn formula exists under other names
  (e.g., `"Death (Persian)"`, `"Enemies (Ancients/Olympiodorus A)"`); no
  entry named with Abu Ma'shar's intent
- `The Node` — the formula `Asc + Node − Moon` (reversible) is not yet in
  the catalogue
- No named group or tag identifies the Abu Ma'shar Nine Parts as a set
- No dedicated `nine_parts_abu_mashar()` query function exists

Current SCP status for Nine Parts: `P0` — pre-constitutionalization.


## Core Insight

The lot engine does not need to change. The Nine Parts work is:

1. add two missing `PartDefinition` entries to `PARTS_DEFINITIONS`
2. tag or group the nine Abu Ma'shar entries so they can be queried as a set
3. add a convenience function that returns the nine parts for a chart
4. hold the Vedic Navamsha as a separate implementation track (different
   module, different data model)


## Truth Domain Axes

Historical scope note:

- The seven planetary lots are the evidenced Abu Ma'shar core supported by the
  currently secured Dykes-facing source trail.
- `The Sword` and `The Node` are retained as admitted extensions within the
  same computational family, but not claimed at the same evidentiary level.

### 1. Technique Family

Governs which Nine Parts system is being computed.

Values:

- `abu_mashar` — nine Hermetic lots (7 planetary + 2 nodal) per Abu Ma'shar /
  Dykes; uses the existing `lots.py` arc engine
- `navamsha` — Vedic 9-fold sign subdivision; does not use the arc engine;
  separate module

These must not share a computation path.

### 2. Reversal Rule (abu_mashar only)

Governs which formula column is used.

Value (confirmed, no ambiguity):

- `full_reversal` — all nine parts reverse for night births; night = Sun in
  houses 1–6; no per-lot exceptions in Abu Ma'shar

### 3. Dependency Order (abu_mashar only)

Fortune and Spirit must be computed before Love and Necessity. This is already
handled by `lots.py`'s pre-computation block.

### 4. Ruler Assignment Rule (navamsha only)

Governs which sign begins each sign's nine-part sequence.

Values:

- `from_element_cardinal` — Vedic standard: fire → Aries, earth → Capricorn,
  air → Libra, water → Cancer


## Implementation Phases

### Phase 1 — Abu Ma'shar Nine Parts (lots.py extension)

**Scope:** add the two missing entries and a named-set query surface.

**Tasks:**

1. Add `PartDefinition("The Sword", "Mars", "Saturn", True, "abu_mashar")` to
   `PARTS_DEFINITIONS`
2. Add `PartDefinition("The Node", "North Node", "Moon", True, "abu_mashar")`
   to `PARTS_DEFINITIONS`
3. Add `"abu_mashar"` as a source tag on the existing seven lots that form the
   Nine Parts set (Fortune, Spirit, Eros/Love, Necessity (Valens), Courage,
   Victory, Nemesis) — or add an explicit alias list
4. Add `nine_parts_abu_mashar(chart) -> list[ArabicPart]` to `lots.py`
   returning the nine parts in canonical order

**Naming note for "Love":**
Abu Ma'shar's Part of Love corresponds to the Eros (Valens) formula
(Spirit − Fortune). Do not rename the existing `"Eros (Valens)"` entry.
The `nine_parts_abu_mashar()` function should return it under Abu Ma'shar's
name `"Love"` via an alias field or by mapping in the function output.

**Acceptance criteria:**

- `nine_parts_abu_mashar(chart)` returns exactly 9 `ArabicPart` results
- all 9 use the night formula when Sun is in houses 1–6
- Fortune and Spirit are computed before Love and Necessity (already
  guaranteed by existing pre-computation logic)
- The Sword and The Node are present with correct formulas and reversal

**SCP target:** P1 COMPLETE after this phase.

**No changes to:** the arc engine, the reversal logic, or any other lot
entries. Purely additive.

---

### Phase 2 — Al-Sijzi Transfer of Management

**Scope:** dynamic management mechanics on top of the static lot positions.

**Prerequisite:** Phase 1 complete; longevity.py intersection interface
designed (see below).

**Tasks:**

1. Define the `LotManagement` vessel: lord of the part, itissāl chain,
   tasyīr position for a given year
2. Add `lot_management(part, chart, date) -> LotManagement` function
3. Define the feminine-sign condition: if the Part falls in a feminine sign
   at night, flag the management condition (Al-Sijzi nuance — affects
   interpretation, not the arc calculation)
4. Document the longevity.py intersection point: Al-Sijzi's Part-based
   Hyleg refinement touches `find_hyleg()` in `longevity.py`; the interface
   should be additive, not a modification of the existing Hyleg logic

**SCP target:** P2 COMPLETE after this phase.

---

### Phase 3 — Vedic Navamsha

**Scope:** separate 9-fold sign subdivision implementation.

**Module:** new file `moira/navamsha.py` or extension of `moira/varga.py`
(check whether varga.py already handles D9).

**Tasks:**

1. Check `moira/varga.py` — if D9 is already implemented there, this phase
   may already be done
2. If not: implement `navamsha_sign(longitude) -> str` using the
   `from_element_cardinal` rule
3. Implement `navamsha_chart(chart) -> dict[str, str]` mapping each planet
   to its navamsha sign
4. Expose as a named technique distinct from `abu_mashar` in any shared
   API surface

**SCP target:** P3 COMPLETE after this phase (if not already handled by
varga.py).

---

### Phase 4 — Hellenistic Nonomoiria (deferred)

**Scope:** 9-fold sign subdivision using the `from_sign` rule (Paulus
Alexandrinus, Firmicus Maternus).

**Prerequisite:** Phase 3 complete (shares module structure).

**Note:** Lower priority than Phases 1–3. The Hellenistic nonomoiria is not
listed in AstroApp's Medieval Time Lords section; it is a delineation
refinement tool, not a time-lord technique.


## Longevity.py Intersection

Al-Sijzi's Part-based Hyleg refinement (Phase 2) intersects with
`moira/longevity.py`.

**Policy:** do not modify `longevity.py` during Phase 1. Design the
intersection interface in Phase 2 before touching either module. The interface
should be additive — Nine Parts provides a `lot_management()` function;
longevity.py calls it as an optional input, not a required dependency.


## Open Questions

1. Does `moira/varga.py` already implement D9 Navamsha? If yes, Phase 3 is
   a verification task, not an implementation task.
2. Should "Love" be added as a distinct `PartDefinition` entry (Abu Ma'shar
   alias for Eros Valens) or mapped only in the query function output?
3. Should the `"abu_mashar"` source tag be added to existing entries or
   handled via an explicit Nine Parts alias list in the query function?


## Research Sources

- Benjamin N. Dykes, *Introductions to Traditional Astrology* (Cazimi Press,
  2010) — confirmed arc formulas and full-reversal rule
- Benjamin N. Dykes, *Persian Nativities Vol. II* (Cazimi Press, 2010) —
  Abu Ma'shar's lot system
- Benjamin N. Dykes, *The Book of Nine Judges* (Cazimi Press, 2011) —
  Al-Sijzi's Transfer of Management mechanics
- `moira/lots.py` — existing infrastructure; ~430 entries; pre-computation
  of Fortune and Spirit confirmed at line 2029
