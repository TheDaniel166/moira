# Lord of the Turn Doctrine

## Purpose

This document defines the pre-SCP doctrine layer for Moira's Lord of the Turn
subsystem.

It exists because "Lord of the Turn" is a term that appears in medieval
astrological literature under significant naming ambiguity, and because the two
variants Moira needs to implement — Al-Qabisi and Egyptian/Al-Sijzi — have not
yet been fully distinguished from each other or from the Lord of the Orb
family.

Before Moira implements this technique, it must state clearly:

- what the Lord of the Turn is and what it is based on
- what the Al-Qabisi and Egyptian/Al-Sijzi variants are doing
- how this technique relates to and differs from the Lord of the Orb
- where the doctrine is settled and where it is uncertain

This document is therefore pre-Phase-1 constitutional work. It is not an API
contract and not yet a backend standard.


## Foundational Thesis

The Lord of the Turn is an annual solar revolution technique for determining
the dominant planetary governor of a given year of life.

Its core logic is:

1. at the solar return for a given year, examine specific sensitive points
   or conditions in the return chart
2. apply a rulership or dignity algorithm to those points
3. the planet that emerges is the Lord of the Turn for that year
4. that planet acts as a primary signifier for the year's events

The "turn" (*conversio*, *revolutio*) refers to the solar revolution — the
sun's annual return to its natal position. The technique identifies which
planet governs that turn.

This technique is structurally different from the Lord of the Orb. The Lord of
the Orb is seeded from the birth planetary hour and advances through the
Chaldean sequence year by year. The Lord of the Turn is determined freshly from
the solar return chart for each year. However, in historical sources the names
"Lord of the Turn," "Lord of the Orb," and "Lord of the Circle" are often used
interchangeably, creating a documentation hazard.

**Naming hazard:** Moira must not assume that any use of "Lord of the Turn" in
a historical source necessarily refers to this technique. The same phrase in
Abu Ma'shar often refers to the planetary-hour technique documented in the Lord
of the Orb doctrine. The techniques Moira treats as "Lord of the Turn" here
are specifically the Al-Qabisi and Egyptian/Al-Sijzi variants, which appear to
operate through solar return chart analysis rather than natal hour advancement.


## Shared Mathematical Foundations

The techniques grouped under Lord of the Turn share:

- the solar return chart as the primary working frame
- a set of sensitive points examined in the solar return chart
- a dignity or rulership algorithm applied to those points
- output: a single planetary governor for the year (or a ranked set)

The major doctrinal questions are:

1. Which sensitive points in the solar return chart are examined?
2. What dignity algorithm is applied to determine the winner?
3. Is the natal chart also consulted?
4. Is the output a single planet or a hierarchy?
5. How does the Lord of the Turn interact with the Lord of the Year
   (profection lord) and other annual indicators?


## Method Variants

### Al-Qabisi (Alcabitius)

**Author:** Abu al-Saqr 'Abd al-'Aziz ibn 'Uthman al-Qabisi (d. 967 CE).
Known in Latin as Alcabitius. Primary work: *Al-Madkhal ila Sina'at Ahkam
al-Nujum* (Introduction to the Art of Astrology). Modern translation: Charles
Burnett, Keiji Yamamoto, and Michio Yano, *Alcabitius: The Introduction to
Astrology* (Warburg Institute, 2004).

**Foundational concept:**

Al-Qabisi's Lord of the Turn is determined by examining the solar return chart
and identifying the planet with the most dignified claim over a set of key
chart points. The candidate points typically include the solar return Ascendant,
its degree, and possibly the solar return Midheaven and/or the position of the
solar return Sun.

**Dignity algorithm:**

Al-Qabisi uses an almuten-style calculation: for each sensitive point, identify
which planets hold dignity there (domicile, exaltation, triplicity, bound/term,
face) and weight those dignities. The planet accumulating the most dignity
across the relevant points becomes the Lord of the Turn.

This is analogous to the almuten figuris calculation applied to the natal chart,
but executed over the solar return chart and restricted to the relevant annual
sensitive points.

**Inputs:**

- solar return chart for the year (requires accurate natal birth data and
  geographic location of the solar return)
- standard medieval dignity tables (Egyptian bounds, triplicity rulers, etc.)
- possibly the natal chart for comparison or additional testimony

**Interpretive meaning:**

The Lord of the Turn governs the overall quality and direction of the year. Its
natal and revolutionary condition describes what the year promises and whether
those promises are well- or ill-formed. It functions as a primary annual
significator rather than a house-by-house secondary signifier.

**Doctrinal status:** The exact set of sensitive points Al-Qabisi uses and the
precise weighting scheme require verification against the translated text. The
broad almuten-over-return-chart structure is documented in secondary literature
but the detailed mechanics need source confirmation before Moira fixes an
implementation.


### Egyptian / Al-Sijzi

**Author attribution:** "Egyptian" in this context refers to the Egyptian
astrological tradition as transmitted through Arabic sources — not a single
named author, but a doctrinal lineage referenced by medieval writers as
"according to the Egyptians." Al-Sijzi (Ahmad ibn Muhammad ibn 'Abd al-Jalil
al-Sijzi, c. 945–1020 CE) is a Persian mathematician and astrologer whose
works transmitted and in some cases modified Egyptian-tradition techniques.

**Foundational concept:**

The Egyptian/Al-Sijzi method for the Lord of the Turn likely uses a different
set of chart points than Al-Qabisi and possibly a different dignity weighting
scheme or a different algorithmic structure for identifying the governor.

Common Egyptian-tradition approaches in annual work emphasize:

- the Lot of Fortune and its lord in the solar return chart
- the solar return Moon's placement and its aspects
- the solar return Ascendant ruler
- distribution through bounds as a secondary timing layer within the year

How Al-Sijzi specifically modifies or transmits the Egyptian approach for the
Lord of the Turn is not yet confirmed in Moira's pre-SCP research.

**Doctrinal status:** This is the most under-documented of the four medieval
time-lord variants Moira needs to implement. The distinction between the
Egyptian tradition and Al-Sijzi's own contributions, and between both of those
and Al-Qabisi's method, requires direct source work before implementation.


## Core Doctrinal Axes

### 1. Sensitive Points Examined

This answers:

- which points in the solar return chart are used as inputs to the dignity
  algorithm

Known candidates:

- solar return Ascendant degree
- solar return Midheaven degree
- solar return Sun position
- solar return Moon position
- Lot of Fortune in the solar return chart
- natal Ascendant degree (carried into the return frame)

Interpretive implication:

- different point sets produce different lords; the point set is not a minor
  option but a core doctrinal choice

### 2. Dignity Algorithm

This answers:

- how the winning planet is selected from dignity claims over the sensitive
  points

Known families:

- `almuten` — weighted sum of essential dignity scores across points
- `plurality` — planet with the most dignity types across points
- `first claim` — planet with the single strongest individual dignity at the
  most important point

### 3. Dignity Table Used

This answers:

- which bound and triplicity systems are applied

Known families:

- Egyptian bounds (standard in the Arabic tradition)
- Ptolemaic bounds
- Egyptian triplicity rulers vs. Dorothaean triplicity rulers

### 4. Natal Chart Role

This answers:

- whether the natal chart participates in selecting the Lord of the Turn or
  only in interpreting it once selected

### 5. Output Structure

This answers:

- whether the output is a single planet or an ordered hierarchy (primary lord,
  participator, etc.)


## Relationship to Lord of the Orb

The Lord of the Turn and the Lord of the Orb share historical naming but
are structurally distinct techniques:

| Dimension | Lord of the Turn | Lord of the Orb |
|---|---|---|
| Seeding | solar return chart analysis | natal birth planetary hour |
| Year-to-year change | recalculated fresh each year from the SR chart | advances mechanically through Chaldean sequence |
| Doctrinal axis | dignity algorithm over SR sensitive points | cycle variant (single vs. continuous loop) |
| Authors (Moira scope) | Al-Qabisi, Egyptian/Al-Sijzi | Abu Ma'shar, Torres |
| Interpretive weight | primary annual governor | sixth of eight annual indicators (Abu Ma'shar) |

Moira should maintain these as separate subsystems even though they appear
under related names in historical sources.


## Ambiguity Registry

### 1. Naming Collision

Ambiguity: "Lord of the Turn" (*dominus conversionis*) is used in some sources
as a synonym for the Lord of the Orb (planetary-hour technique) and in other
sources as a label for the solar-return almuten technique described here.

Moira stance: treat these as distinct techniques, documented separately,
linked by a cross-reference note in both doctrine documents.

### 2. Al-Sijzi vs. Egyptian Attribution

Ambiguity: it is not yet clear whether "Egyptian/Al-Sijzi" names one method
(Al-Sijzi transmitting the Egyptian tradition) or two distinguishable
methods that happen to be grouped together.

Moira stance: flag this as unresolved; do not implement until the source
distinction is confirmed.

### 3. Al-Qabisi Sensitive Points

Ambiguity: the precise set of solar return chart points Al-Qabisi examines
for his Lord of the Turn algorithm is not yet confirmed at the level of
detail Moira needs for implementation.

Moira stance: source verification required before Phase 1 begins.

### 4. Interaction with Other Annual Indicators

Ambiguity: how the Lord of the Turn ranks relative to Lord of the Year,
Fardār lord, and Lord of the Orb is not consistently stated across sources.

Moira stance: expose the Lord of the Turn as a named annual indicator;
do not hardcode its rank; let the caller compose the annual hierarchy.


## Admission Categories

### Historically Attested

- Lord of the Turn as a solar return–based annual governor technique — broadly
  attested across Arabic and early Latin sources

### Historically Grounded but Requiring Verification

- Al-Qabisi's specific algorithm — structure is documented in secondary
  literature; precise mechanics require source confirmation
- Egyptian/Al-Sijzi variant — real as a tradition family but under-documented
  for implementation purposes

### Not Admitted

- Any conflation of Lord of the Turn with Lord of the Orb as a single
  implementation


## Moira Policy Before Expansion

Before implementing the Lord of the Turn, Moira should:

1. confirm the sensitive point set Al-Qabisi uses from a direct translation
   reference (Burnett/Yamamoto/Yano or Dykes)
2. confirm whether Egyptian/Al-Sijzi is one method or two
3. formalize the almuten algorithm as a shared dignity utility (it is likely
   needed by multiple subsystems including the Hyleg)
4. treat the dignity table as a parameter, not a hardcoded constant
5. keep Lord of the Turn and Lord of the Orb as separate implementations
   sharing no computation path, even though they share naming in sources


## Research Sources

- Charles Burnett, Keiji Yamamoto, Michio Yano (trans.), *Alcabitius: The
  Introduction to Astrology* (Warburg Institute, 2004) — primary source for
  Al-Qabisi's methods
- Benjamin N. Dykes, *Persian Nativities III* and *IV* (Cazimi Press, 2010,
  2019) — Abu Ma'shar's annual revolution system; contextualizes the Lord of
  the Turn within the eight-indicator framework
- Benjamin N. Dykes, *Works of Sahl and Masha'allah* (Cazimi Press, 2008) —
  related annual techniques in the Arabic transmission
- Project Hindsight translations — background on Egyptian doctrinal tradition
  as transmitted into Arabic and Latin
- AstroApp help documentation — names Al-Qabisi and Egyptian/Al-Sijzi as
  distinct variants; starting point for source disambiguation
