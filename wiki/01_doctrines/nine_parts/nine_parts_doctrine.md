# Nine Parts Doctrine

## Purpose

This document defines the pre-constitutional doctrine layer for Moira's Nine Parts
subsystem.

It exists because "Nine Parts" as used in the Abu Ma'shar tradition is not the
same technique as the Hellenistic nonomoiria (9-fold sign subdivision) or the
Vedic Navamsha (D9 chart), even though all three share the number nine and are
often conflated in secondary literature and software documentation.

AstroApp groups this technique as "Nine Parts (Abu Ma'shar/Vedic)." Moira
must determine whether this grouping treats two distinct techniques under a
common label, or whether it reflects a doctrinal equivalence claim that needs
to be assessed before implementation.

Before Moira implements this technique, it must state clearly:

- what Abu Ma'shar's Nine Parts actually are (not the sign subdivision)
- how they diverge from the Hellenistic lot baseline
- what Al-Sijzi's specific mechanics contribute
- what the Vedic Navamsha is and whether it belongs in the same subsystem
- where the doctrine is settled and where source confirmation is still needed

This document is therefore pre-Phase-1 constitutional work. It is not an API
contract and not yet a backend standard.


## Critical Disambiguation

### What Abu Ma'shar's Nine Parts Are Not

Abu Ma'shar's "Nine Parts" does **not** refer to the Hellenistic nonomoiria,
which divides each zodiac sign into 9 equal sub-divisions of 3°20' each. That
is a separate technique with a separate doctrinal history.

### What Abu Ma'shar's Nine Parts Are

Abu Ma'shar's Nine Parts is an **expanded lot/part system**:

- seven lots corresponding to the seven classical planets
- two additional lots corresponding to the lunar nodes
- total: nine lots (nine "parts")

Each lot is calculated as an arc from one body to another, projected from the
Ascendant — structurally identical to the Hellenistic Hermetic lots, but
expanded in scope and modified in doctrine.

The Hellenistic tradition centered on a smaller core of Hermetic lots (Fortune,
Spirit, Necessity, Eros, Courage, Victory, Nemesis — the canonical seven of
Valens and Dorotheus). Abu Ma'shar preserves this structural logic but
reorganizes and expands the set to nine, assigning one lot to each planet and
two to the nodes.

### The Vedic Navamsha

The Vedic Navamsha (D9 chart) is a 9-fold subdivision of each zodiac sign into
parts of 3°20', each governed by a sign whose assignment depends on the
elemental/modal starting point of the sign being divided. It is structurally
closer to the Hellenistic nonomoiria than to Abu Ma'shar's lot system.

Whether AstroApp's "Nine Parts (Abu Ma'shar/Vedic)" groups these because they
share a mathematical surface (the number nine, 3°20' parts) or because they
are doctrinally related in some way is an **unresolved question** for Moira
until the AstroApp implementation is verified.

**Moira's working hypothesis:** these are two distinct techniques being offered
under a common heading for organizational convenience. They should be
implemented separately.


## Abu Ma'shar's Nine Parts: Doctrine

### Foundational Concept

In Abu Ma'shar's system, the Parts are not merely points of fate on the
ecliptic. Each Part is a **representative of a planet's essence** in the chart:

- its position shows where that planet's nature manifests most concretely in
  the native's life
- the condition of its dispositor (the lord of the sign the Part falls in)
  determines how well or badly that planetary nature operates
- the Part and its lord together constitute a compound signifier

This is a significant doctrinal expansion beyond the Hellenistic baseline,
where lots were primarily positional fate-points rather than planetary
representatives.

### The Nine Lots: Confirmed Arc Formulas

Source: Benjamin Dykes, *Introductions to Traditional Astrology* and
*Persian Nativities Vol. II*.

All lots are projected from the Ascendant. The general formula is:

`Part = Ascendant + Point_B − Point_A`

For night births, Point_A and Point_B swap (see reversal section below).

| # | Part | Planet | Day Formula | Night Formula |
|---|---|---|---|---|
| 1 | Fortune | Moon (Body/Success) | Asc + Moon − Sun | Asc + Sun − Moon |
| 2 | Spirit | Sun (Soul/Intellect) | Asc + Sun − Moon | Asc + Moon − Sun |
| 3 | Love | Venus (Desire) | Asc + Spirit − Fortune | Asc + Fortune − Spirit |
| 4 | Necessity | Mercury (Constraint) | Asc + Fortune − Spirit | Asc + Spirit − Fortune |
| 5 | Courage | Mars (Boldness) | Asc + Fortune − Mars | Asc + Mars − Fortune |
| 6 | Victory | Jupiter (Ease) | Asc + Jupiter − Spirit | Asc + Spirit − Jupiter |
| 7 | Nemesis | Saturn (Weight) | Asc + Fortune − Saturn | Asc + Saturn − Fortune |
| 8 | The Sword | Nodes (Conflict) | Asc + Mars − Saturn | Asc + Saturn − Mars |
| 9 | The Node | Nodes (Fate/Hidden) | Asc + Node − Moon | Asc + Moon − Node |

Note that Parts 3 and 4 (Love and Necessity) are derived from Fortune and
Spirit, not from the raw planetary positions directly. Fortune and Spirit must
be computed first.

Note that Parts 8 and 9 (Sword and Node) do not have a single "associated
planet" in the same sense as the first seven — they are nodal and malefic-gap
calculations respectively. The Sword computes the arc between the two malefics;
the Node anchors the lunar node to the sect light.

### Diurnal/Nocturnal Reversal: Confirmed Rule

**Abu Ma'shar applies full reversal for all nine parts for night births.**

Night is defined as: the Sun is below the horizon (Sun in houses 1–6, i.e.,
Sun's house number ≤ 6 using whole-sign or the relevant house system).

This is the Persian standard confirmed by Dykes from the *Greater Introduction*
of Abu Ma'shar. It aligns with the Dorothaean reversal tradition for Fortune
and extends it uniformly to all nine parts.

**Historical disambiguation — Part of Fortune:**
Some medieval editors, following a misreading of Ptolemy, stopped reversing
Fortune for night births. Dykes confirms this is an error: Abu Ma'shar and
the Persian core do reverse Fortune. Moira follows Abu Ma'shar.

**The Sword (Part 8):**
The night reversal is mandatory. The day formula computes the "malefic gap"
(Mars − Saturn); the night formula inverts the arc to start from the nocturnal
malefic pole. Failure to reverse produces a symmetrically wrong result.

**The Node (Part 9):**
The night reversal is mandatory. The Moon is the nocturnal sect light. The
reversal keeps the Node anchored to the sect light. Failure to reverse breaks
the sect logic of the formula.

**The Al-Sijzi nuance:**
Al-Sijzi distinguishes between the arc calculation and the **management** of
the Part. If a Part falls in a feminine sign at night, the management of the
Part changes (the lord's condition is interpreted differently), but the arc
calculation itself still uses the night reversal formula. These are two
separate operations. Phase 1 implements the arc calculation only; the
management condition is a Phase 2 concern.

### Calculation Logic Summary

```
is_night = sun_house <= 6  # Sun below horizon

def compute_part(asc, point_a_day, point_b_day, is_night):
    if is_night:
        return (asc + point_b_day - point_a_day) % 360
    else:
        return (asc + point_a_day - point_b_day) % 360
```

Fortune and Spirit must be computed before Love and Necessity, since Love and
Necessity use Fortune and Spirit as their arc endpoints.


## Al-Sijzi's Specific Mechanics

### The Transfer of Management

Al-Sijzi's key contribution to Nine Parts doctrine is the concept of the
**Transfer of Management** (*naql al-tadbīr*):

- it is not sufficient to locate where a Part falls in the chart
- the **lord of the Part** (dispositor of the Part's sign) must be tracked
  through its condition and motion
- specifically, the lord's applications (*itissāl*) — what planets it applies
  to — and the profection of the Part (*tasyīr*) are both active mechanics

This means the Part itself is a static point, but its management passes
dynamically through the lord's itissāl chain and the tasyīr (direction/
profection) of the Part over time.

**Itissāl** (application): the applying aspect from the lord of the Part to
another planet; the receiving planet participates in the management of the
Part's domain.

**Tasyīr** (profection/direction): the annual or directional advance of the
Part along the ecliptic; the bound lord(s) the Part passes through become
successive managers.

### Parts as Testimony Checkpoints

Al-Sijzi uses the Nine Parts as **mathematical checkpoints** for determining
which planet holds the most testimony over a specific area of life:

- for a given topic (longevity, wealth, marriage, etc.), examine which Part
  governs it
- determine which planets have testimony over that Part (by position, dignity,
  rulership, aspect)
- the planet with the most testimony becomes the primary significator for that
  topic

This is a refinement of the Hellenistic *oikodespotes* (chart-ruler) concept,
applied topically per Part rather than globally per chart. Al-Sijzi's approach
is more granular and interrogational (closer to Persian horary method) than
the Hellenistic natal interpretation tradition.

### Connection to Hyleg and Alcocoden

Al-Sijzi is particularly detailed on the Part of the Hyleg — the Part that
functions as a mathematical checkpoint for the longevity calculation:

- the Hyleg determination uses the Parts as candidate points
- the planet with the most testimony over the relevant Part becomes the
  Alcocoden (giver of years)
- this is a Persian refinement of the Bonatti/Hellenistic Hyleg method already
  implemented in Moira's `longevity.py`

**Implication for Moira:** Al-Sijzi's Nine Parts mechanics are not isolated in
a separate module — they intersect with the Hyleg calculation in `longevity.py`.
Any Nine Parts implementation must be doctrinely compatible with the longevity
subsystem.


## The Vedic Navamsha: Doctrine

### Foundational Concept

The Navamsha (D9, ninth divisional chart) divides each zodiac sign (30°) into
nine equal parts of 3°20' each. Each part is assigned a ruling sign by an
element-based starting rule:

- Fire signs (Aries, Leo, Sagittarius): parts 1–9 begin from Aries
- Earth signs (Taurus, Virgo, Capricorn): parts 1–9 begin from Capricorn
- Air signs (Gemini, Libra, Aquarius): parts 1–9 begin from Libra
- Water signs (Cancer, Scorpio, Pisces): parts 1–9 begin from Cancer

Each planet is replotted into its navamsha sign, producing a complete secondary
chart (the D9) used for natal delineation — particularly marriage, dharma,
spiritual life, and the inherent strength of planets.

### Ruler Assignment Formula

For a planet at longitude L within sign S (0-indexed, 0 = Aries):

```
position_within_sign = L mod 30°
part_index = floor(position_within_sign / (10/3))  # 0-indexed, 0–8
element_start = {fire: 0, earth: 9, air: 6, water: 3}[element_of(S)]
navamsha_sign = (element_start + part_index) mod 12
```

### Interpretive Use

The Navamsha is primarily a delineation chart, not a sequential time-lord
system in the standard Jyotish sense. Its primary uses are:

- qualifying the natal promise of planets
- assessing the deeper nature and inherent strength of planets
- delineating marriage and partnership (7th navamsha lord)
- assessing spiritual disposition

In advanced Jyotish, navamsha lords participate in dasha timing through
secondary chart analysis, but the D9 itself is not a sequential period
generator in the way dashas are.

### Relationship to Hellenistic Nonomoiria

The Hellenistic nonomoiria uses a simpler rule: each sign's nine parts begin
from that sign itself and proceed in zodiacal order. The mathematical structure
is the same (9 × 3°20') but the ruler assignment produces different results
for the majority of signs:

| Sign | Nonomoiria Part 1 | Navamsha Part 1 |
|---|---|---|
| Aries | Aries | Aries (fire, same) |
| Taurus | Taurus | Capricorn (earth start) |
| Gemini | Gemini | Libra (air start) |
| Cancer | Cancer | Cancer (water, same) |
| Leo | Leo | Aries (fire start) |
| ... | ... | ... |

The two traditions converge for the four cardinal signs and diverge for the
rest.


## Core Doctrinal Axes

### 1. Technique Family

This answers:

- whether a Nine Parts calculation is Abu Ma'shar lots or a 9-fold sign
  subdivision

Known families:

- `abu_mashar_lots` — nine Hermetic-style lots (7 planetary + 2 nodal)
- `navamsha` — Vedic 9-fold sign subdivision with element-cardinal starting
  rule
- `nonomoiria` — Hellenistic 9-fold sign subdivision starting from the sign
  itself

These are three distinct techniques that must not share a computation path.

### 2. Diurnal/Nocturnal Reversal (abu_mashar_lots only)

This answers:

- which lots use the reversal formula for night births and which are fixed

This is a per-lot parameter, not a global chart parameter.

### 3. Transfer of Management (abu_mashar_lots only)

This answers:

- whether the implementation includes Al-Sijzi's dynamic management mechanics
  (itissāl, tasyīr) or only the static lot position

Known modes:

- `static` — compute lot position only
- `dynamic` — include lord tracking, itissāl chain, and tasyīr profection

### 4. Ruler Assignment Rule (subdivision variants only)

This answers:

- which starting sign governs each sign's nine-part sequence

Known variants:

- `from_sign` — Hellenistic, starts from the sign itself
- `from_element_cardinal` — Vedic, starts from the cardinal sign of the
  element


## Ambiguity Registry

### 1. AstroApp Grouping Intent

Ambiguity: it is not confirmed whether "Nine Parts (Abu Ma'shar/Vedic)" in
AstroApp means one combined implementation or two distinct offerings.

Moira stance: implement as separate named techniques; confirm grouping intent
before any shared API surface is designed.

### 2. Specific Lot Formulas

**RESOLVED.** All nine arc formulas confirmed from Dykes, *Introductions to
Traditional Astrology* and *Persian Nativities Vol. II*. See the formula table
in the Abu Ma'shar section above. Note the dependency order: Fortune and Spirit
must be computed before Love and Necessity.

### 3. Per-Lot Reversal Rules

**RESOLVED.** Abu Ma'shar applies full reversal for all nine parts at night
(Sun in houses 1–6). No per-lot exceptions in the Abu Ma'shar core. The
Al-Sijzi feminine-sign nuance affects Part management (Phase 2), not the arc
formula itself.

### 4. Al-Sijzi Dynamic Mechanics Scope

Ambiguity: whether itissāl and tasyīr of the Part are a mandatory part of the
Nine Parts subsystem or optional extensions is a product decision as much as a
doctrinal one.

Moira stance: implement static lot position as Phase 1; dynamic management
mechanics as a later extension once the static layer is constitutionalized.

### 5. Longevity.py Intersection

Ambiguity: Al-Sijzi's Part-based Hyleg refinement touches the existing Hyleg
implementation. The interface between Nine Parts and longevity.py is not yet
defined.

Moira stance: do not modify longevity.py during Nine Parts Phase 1; document
the intersection point; design the interface in a separate doctrinal note
before Phase 2.


## Admission Categories

### Historically Attested

- Abu Ma'shar Nine Lots — documented in Dykes translations (*Persian Nativities
  Vol. II*, *Introductions to Traditional Astrology*)
- Vedic Navamsha — classical Jyotish corpus, unambiguous
- Hellenistic Nonomoiria — Paulus Alexandrinus, Firmicus Maternus

### Historically Grounded but Requiring Verification

- Al-Sijzi's Transfer of Management mechanics — documented in *Book of Nine
  Judges* and Al-Sijzi's *Introduction*; specific mechanics require source
  confirmation before implementation
- Per-lot reversal rules in Abu Ma'shar — documented in secondary literature;
  exact per-lot assignments need verification

### Not Admitted

- Any conflation of Abu Ma'shar lots with the nonomoiria or navamsha
- Any global diurnal/nocturnal reversal toggle applied uniformly to all nine
  lots


## Moira Policy Before Expansion

Before implementing the Nine Parts, Moira should:

1. ~~confirm the arc formula for each lot~~ — **RESOLVED**: formulas confirmed,
   see table above; note Fortune/Spirit must be computed before Love/Necessity
2. ~~confirm per-lot reversal rules~~ — **RESOLVED**: full reversal for all
   nine at night (Sun in houses 1–6); no per-lot exceptions in Abu Ma'shar
3. confirm whether AstroApp's grouping means one implementation or two —
   still open; implement as separate named techniques pending confirmation
4. implement lot position (static) before any dynamic management mechanics
5. design the longevity.py intersection interface before Phase 2 of Nine Parts
6. keep `abu_mashar_lots`, `navamsha`, and `nonomoiria` as separate named
   techniques in the data model with no shared computation path


## Research Sources

- Benjamin N. Dykes (trans.), *Persian Nativities Vol. II: Abu Ma'shar,
  The Abbreviation of the Introduction to Astrology* (Cazimi Press, 2010) —
  primary source for the nine lots and their formulas
- Benjamin N. Dykes (trans.), *Introductions to Traditional Astrology:
  Abu Ma'shar and Al-Qabisi* (Cazimi Press, 2010) — curated comparison of
  Hellenistic baseline and Persian developments; explicit coverage of lot
  divergences
- Benjamin N. Dykes (trans.), *The Book of Nine Judges* (Cazimi Press, 2011) —
  Al-Sijzi's influence documented in footnotes and commentary; itissāl and
  tasyīr mechanics in context
- Al-Sijzi, *Introduction to the Book of the Indications of the Celestial
  Signs* — primary source for Transfer of Management and Part-based testimony;
  translation status: partial, via Dykes commentary
- Vettius Valens, *Anthologies* — canonical Hellenistic lot baseline
- Dorotheus of Sidon, *Carmen Astrologicum* — diurnal/nocturnal reversal
  doctrine in the Hellenistic tradition
- Parashara, *Brihat Parashara Hora Shastra* — Vedic Navamsha doctrine
- AstroApp help documentation — starting point for doctrinal disambiguation of
  the "Nine Parts (Abu Ma'shar/Vedic)" grouping

