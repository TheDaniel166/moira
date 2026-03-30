# Lord of the Orb Doctrine

## Purpose

This document defines the pre-SCP doctrine layer for Moira's Lord of the Orb
subsystem.

It exists because the Lord of the Orb has two historically documented method
variants — Abu Ma'shar and Diego de Torres — that differ in a specific and
consequential way.

Before Moira implements this technique, it must state clearly:

- what the Lord of the Orb is and what it is based on
- what the Abu Ma'shar and Torres variants are mathematically doing
- where the ambiguity lies and how it should be handled
- what Moira should admit, defer, or reject

This document is therefore pre-Phase-1 constitutional work. It is not an API
contract and not yet a backend standard.


## Foundational Thesis

The Lord of the Orb is a planetary hour–based annual time-lord technique.

Its core logic is:

1. identify the planetary hour at the moment of birth
2. that planet becomes the Lord of the Orb for year 1 of life, governing the
   significations of the 1st house
3. each subsequent year, the next planet in the Chaldean order becomes Lord of
   the Orb, governing the next house
4. the two cycles — the 7-planet Chaldean sequence and the 12-house sequence —
   advance independently, creating a combined pattern

The "orb" is not an aspect orb. It derives from Latin *orbis* (circle, sphere,
orbit) and refers here to the cycle of the planetary hours. The Lord of the Orb
is the planet that governs the birth hour, promoted to an annual signifier.

In medieval Latin and early modern sources the technique appears under several
names used interchangeably: Lord of the Orb, Lord of the Turn (*dominus
conversionis*), and Lord of the Circle (*dominus circuli*). The naming
ambiguity is historical, not a Moira problem.


## Shared Mathematical Foundations

All variants of the Lord of the Orb share the following:

- the Chaldean planetary order: Saturn → Jupiter → Mars → Sun → Venus →
  Mercury → Moon → (repeat)
- the 12-house sequence: house 1 for year 1, house 2 for year 2, through house
  12 for year 12, then reset
- the birth planetary hour as the starting point
- evaluation of the Lord of the Orb in both the natal chart and the solar
  return chart for the year under analysis

The technique operates within annual solar return delineation. It produces a
participating signifier that acts alongside — not instead of — other annual
lords such as the Lord of the Year (via profections) and the Fardār lord.


## Placement in the Annual Hierarchy

Abu Ma'shar ranks the Lord of the Orb sixth among eight annual indicators:

1. Lord of the Year (ruler of profected Ascendant sign)
2. Distributor of the natal Ascendant (bound-lord of the directed ASC)
3. Distributor of the longevity releaser
4. Partners/participants of indicators 2 and 3
5. Lord of the Fardār
6. **Lord of the Orb**
7. Planet the solar return Moon first applies to (or lord of Moon's sign if
   void)
8. First lord of the solar return Ascendant

If one planet holds more testimonies across the eight than any other, its
indications take priority for the year.


## Method Variants

### Abu Ma'shar

**Source:** *Kitāb taḥāwil sinī al-mawālīd* (Book of the Revolutions of the
Years of Nativities). Modern translation: Benjamin Dykes, *Persian Nativities
IV* (Cazimi Press, 2019). Key pages: 126, 128.

**Mechanic:**

- Year 1: birth-hour planet → house 1 significations
- Year 2: next Chaldean planet → house 2 significations
- ...through year 7 → house 7
- Year 8: Chaldean sequence wraps to starting planet; house assignment
  continues to house 8
- Year 13: house cycle resets to house 1; planetary sequence continues
  independently

**Ambiguity:** Dykes explicitly flags that Abu Ma'shar's Arabic text supports
two interpretations:

- **Single Cycle:** after 12 years, both the house cycle and the planetary
  sequence reset together — the Year 13 planet is identical to the Year 1
  planet
- **Continuous Loop:** the house cycle resets every 12 years but the planetary
  sequence advances independently, never resetting; the full combined pattern
  repeats only at LCM(7, 12) = 84 years

Dykes does not resolve which reading is correct from the source. This is a
genuine textual ambiguity.

**Ranking in system:** sixth of eight annual indicators (explicit in Abu
Ma'shar).

**Interpretive meaning:** the Lord of the Orb signifies the domain of the
corresponding house for that year of life; its natal dignity and aspects
describe the quality of outcomes promised; its solar return condition qualifies
what will actually manifest.


### Diego de Torres

**Source:** manuscript of lecture notes in Old Castilian, University of
Salamanca, late 1480s–1490s. Untitled; referenced in secondary literature as
*Opus Astrologicum*. Not yet published in a modern critical edition.

**Mechanic:**

Torres uses and documents the **Continuous Loop** variant explicitly. His notes
include a worked example table for 42 years assuming Venus as the birth-hour
planet:

- Venus recurs as Lord of the Orb at years 1, 8, 15, 22, 29, 36 (every 7
  years)
- The house assignment advances independently every year regardless of when the
  planetary sequence resets
- Full combined cycle: 84 years (LCM of 7 and 12)

His table headings use the phrase *conpliste revolución* ("the completed
revolution"), confirming the solar revolution context.

**Torres's own definition (from manuscript, translated):**
> "The lord of the hour of the time of birth is called the 'lord of the orb'
> for the first year of life, and by it one shall judge the life and disposition
> of the native with regard to habits, health and illnesses and other
> significations of the 1st house during the 1st year of life."

**Corroborating source:** Francesco Giuntini (Junctinus of Florence, 16th c.)
documented the same continuous loop method in *Speculum Astrologiae* with
tables extending to age 60, confirming the Torres reading as the standard
late-medieval and Renaissance interpretation.


## Core Doctrinal Axes

These are the axes Moira must formalize before implementation.

### 1. Cycle Variant

This answers:

- whether the planetary sequence and house cycle reset together (single cycle)
  or run as independent loops (continuous loop)

Known variants:

- `single_cycle` — both cycles reset at year 13; the 84-year LCM is never
  reached; historically ambiguous in Abu Ma'shar
- `continuous_loop` — planetary sequence runs independently of house cycle;
  full pattern repeats at 84 years; documented in Torres and Giuntini

Interpretive implication:

- the cycle variant changes which planet governs every year from year 13
  onward; the two variants diverge increasingly over time
- `continuous_loop` is the better-attested variant in the surviving literature

### 2. Starting Planet

This answers:

- what determines the Lord of the Orb for year 1

The starting planet is always the planet governing the birth hour, calculated
from the Chaldean planetary hour sequence. Accurate birth time is required.

### 3. House Signification

This answers:

- what interpretive domain the Lord of the Orb governs in a given year

The house-year coupling is:

- year N → house ((N − 1) mod 12) + 1

The significations of that house govern the domain of the Lord of the Orb for
that year.

### 4. Evaluation Frame

This answers:

- in what context the Lord of the Orb is interpreted

Evaluation requires:

- the natal chart condition of the planet (dignity, house placement, aspects)
- the solar return chart condition of the planet for the year under analysis


## Ambiguity Registry

### 1. Cycle Variant in Abu Ma'shar

Ambiguity: the Arabic text supports both single cycle and continuous loop.

Moira stance: implement both as named variants; default to `continuous_loop`
as the more clearly documented reading (Torres, Giuntini).

### 2. Naming Overlap with Lord of the Turn

Ambiguity: in historical Latin and early modern sources the terms "Lord of the
Orb," "Lord of the Turn," and "Lord of the Circle" are used interchangeably for
this same planetary-hour technique. However, some software (including AstroApp)
lists "Lord of the Turn" and "Lord of the Orb" as separate entries under
different authors, implying a doctrinal distinction.

Moira stance: treat this as a documentation hazard, not a resolved distinction.
See the Lord of the Turn doctrine document for the separate method family.

### 3. Birth Time Precision

Ambiguity: planetary hours are time-sensitive; an error of minutes around a
planetary hour boundary changes the Lord of the Orb for the entire life.

Moira stance: no special handling; accuracy is the caller's responsibility.
Moira should expose which planetary hour governs the birth time so the user can
verify it.


## Admission Categories

### Historically Attested

- Lord of the Orb (continuous loop variant) — Torres, Giuntini, Abu Ma'shar
  (with variant ambiguity)

### Historically Grounded but Ambiguous

- Lord of the Orb (single cycle variant) — defensible from Abu Ma'shar's text
  but not confirmed in worked examples

### Not Admitted

- Any variant that does not use the birth planetary hour as the starting point


## Moira Policy Before Expansion

Before implementing the Lord of the Orb, Moira should:

1. implement the Chaldean planetary hour calculation as a shared utility (if
   not already available from `planetary_hours.py`)
2. formalize the two cycle variants as named enum values, not a boolean
3. implement house signification mapping as a lookup, not hard-coded
   conditionals
4. expose the Lord of the Orb planet for each year in both cycle variants so
   callers can compare them
5. do not conflate Lord of the Orb with Lord of the Turn until the doctrinal
   distinction (or equivalence) is confirmed


## Research Sources

- Benjamin N. Dykes, *Persian Nativities IV: On the Revolutions of the Years
  of Nativities* (Cazimi Press, 2019) — primary Arabic source; pages 126–128
  are the key locus for the two-variant discussion
- Benjamin N. Dykes, *Persian Nativities III: Abu Ma'shar on Solar Revolutions*
  (Cazimi Press, 2010) — Latin/Greek transmission
- Anthony Louis, "The Lord of the Orb (aka Turn or Circle) in Solar Returns"
  (blog, 2019) — ranking list, basic doctrine
- Anthony Louis, "Lord of the Orb in Annual Revolutions" (blog, 2021) — Torres
  manuscript, continuous loop, worked example
- Francesco Giuntini (Junctinus), *Speculum Astrologiae* (16th c.) — tables
  to age 60 corroborating continuous loop
- AstroApp help documentation — names both variants explicitly
