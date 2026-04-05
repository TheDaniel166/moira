# Hellenistic Astrology Completion Roadmap

## Purpose

This is an **additive roadmap** governing the closure of partial and absent
Hellenistic astrology features in Moira.

Moira already implements the structural pillars of Hellenistic technique: sect,
lots, whole sign houses, zodiacal releasing, profections, firdaria, antiscia,
essential dignities (domicile/exaltation), fixed stars with parans and heliacal
visibility, and degree-based Ptolemaic aspects.  What remains are doctrinal
refinements and small subsystems that complete the Hellenistic apparatus to the
level where the tradition can be practised without silent gaps.

The work is grouped into four phases of increasing interpretive depth.  Each
phase is independently shippable and testable.

Companion documents:

- [DIGNITIES_BACKEND_STANDARD](../../02_standards/DIGNITIES_BACKEND_STANDARD.md)
- [EGYPTIAN_BOUNDS_BACKEND_STANDARD](../../02_standards/EGYPTIAN_BOUNDS_BACKEND_STANDARD.md)
- [TIMELORDS_BACKEND_STANDARD](../../02_standards/TIMELORDS_BACKEND_STANDARD.md)
- [VALIDATION_ASTROLOGY](../../03_validation/VALIDATION_ASTROLOGY.md)

---

## Current Moira State

### Fully implemented

| Feature | Module |
|---------|--------|
| Sect (diurnal/nocturnal, sect light, hayz) | `moira/dignities.py` |
| Lots (~430 named, day/night reversal) | `moira/lots.py`, `moira/nine_parts.py` |
| Whole Sign Houses | `moira/houses.py` |
| Essential dignities (domicile, exaltation, detriment, fall, peregrine) | `moira/dignities.py` |
| Triplicity rulers (Dorotheus, scored in longevity) | `moira/longevity.py` |
| Face/decan rulers (Chaldean, scored in longevity) | `moira/longevity.py` |
| Egyptian bounds (full table, profiling, network) | `moira/egyptian_bounds.py` |
| Profections (annual + monthly, classical rulers) | `moira/profections.py` |
| Zodiacal releasing (Fortune, Spirit, Eros, Necessity) | `moira/timelords.py` |
| Firdaria (diurnal, nocturnal, Bonatti) | `moira/timelords.py` |
| Antiscia + contra-antiscia | `moira/antiscia.py` |
| Aspects (Ptolemaic five, applying/separating, patterns) | `moira/aspects.py` |
| Fixed stars (Behenian, Royal, parans, heliacal, Hermetic decans) | multiple modules |
| Solar condition (cazimi, combust, under the beams) | `moira/dignities.py` |
| Mutual reception (domicile + exaltation) | `moira/dignities.py` |

### Partial

| Feature | What exists | What is missing |
|---------|-------------|-----------------|
| Bounds/terms | Egyptian bounds only | Ptolemaic terms, Chaldean terms |
| Essential dignity enum | Domicile, exaltation, detriment, fall, peregrine | Triplicity, bound, face as first-class `EssentialDignityKind` members |
| Hayz | `is_in_hayz()` | Halb (the nocturnal partial-hayz) |
| Planetary condition | Cazimi, combust, under the beams | Oriental/occidental (morning/evening star), besieging |
| Aspect direction | Sinister/dexter exists in primary directions | Not in the general aspect engine |

### Absent

| Feature | Doctrinal significance |
|---------|----------------------|
| Planetary joys | Foundational to Hellenistic house rationale |
| Overcoming (katarchein) | The zodiacal-superiority doctrine |
| Whole-sign aspects | Sign-based aspect mode distinct from degree-based |
| Besieging (enclosure) | Malefic enclosure condition |

---

## Truth Domain Axes

### 1. Bounds Doctrine

Admitted values:

- **Egyptian** (Ptolemy's preferred table, already implemented)
- **Ptolemaic** (Ptolemy's own alternative table, Tetrabiblos I.21)
- **Chaldean** (from the Yavanajataka / pre-Ptolemaic tradition)

The bounds doctrine axis determines which table is used for bound rulership
lookup.  All three systems assign the same five rulers (Mercury, Venus, Mars,
Jupiter, Saturn) across the same 30-degree sign span, but in different
segment arrangements.

### 2. Triplicity Scheme

Admitted values:

- **Dorotheus** (day/night/participating, already implemented in `longevity.py`)
- **Ptolemy** (day/night only, no participating ruler)
- **Morinus** (alternative assignment)
- **Lilly** (early modern variant)

The triplicity scheme axis is relevant once triplicity becomes a first-class
essential dignity rather than a scoring-only concept.

### 3. Aspect Geometry

Admitted values:

- **Degree-based** (current implementation, exact longitude separation with orb)
- **Sign-based / whole-sign** (sign-count determines aspect type, no orb)

Both modes yield the same five Ptolemaic aspects.  The distinction is whether
planets in the same sign are conjunct regardless of degree separation and
whether a planet at 29 degrees Aries and 1 degree Leo form a trine.

### 4. Oriental / Occidental Definition

Admitted values:

- **Classical / Ptolemaic** (based on rising before/after the Sun)
- **Bonatti** (adds sign-based nuance)

The oriental/occidental axis is relevant for planetary condition and
accidental dignity scoring.

---

## Implementation Phases

### Phase 1 -- Essential Dignity Completion and Planetary Joys

**Scope:** Promote triplicity, bound, and face to first-class essential
dignity kinds, and implement planetary joys as an accidental condition.

**Modules:** `moira/dignities.py`, `moira/longevity.py`

**Tasks:**

1. Extend `EssentialDignityKind` with `TRIPLICITY = "triplicity"`,
   `BOUND = "bound"`, `FACE = "face"`.

2. Add scoring constants `SCORE_TRIPLICITY = 3`, `SCORE_BOUND = 2`,
   `SCORE_FACE = 1` to `moira/dignities.py` (migrated from `longevity.py`
   inline values).

3. Add `PLANETARY_JOYS` lookup dict to `moira/dignities.py`:
   ```python
   PLANETARY_JOYS: dict[str, int] = {
       "Mercury": 1, "Moon": 3, "Venus": 5,
       "Mars": 6, "Sun": 9, "Jupiter": 11, "Saturn": 12,
   }
   ```

4. Add `is_in_joy(planet: str, house: int) -> bool` function.

5. Add `JOY = "joy"` to `AccidentalConditionKind` with
   `SCORE_JOY = 3` and polarity `STRENGTHENING`.

6. Wire triplicity/bound/face detection into `calculate_dignities()` so the
   result vessel reports the full five-level essential dignity state.

7. Ensure `dignity_score_at()` in `longevity.py` delegates to the same
   constants rather than hardcoding weights.

**Acceptance criteria:**

- `calculate_dignities(Body.JUPITER, lon=15.0, ...)` for Jupiter at 15
  degrees Aries reports `TRIPLICITY` as an essential dignity (Jupiter is
  day triplicity ruler of fire signs in the Dorotheus scheme).
- `is_in_joy("Mars", 6)` returns `True`.
- `is_in_joy("Mars", 5)` returns `False`.
- All existing dignity and longevity tests continue to pass.

**Constitutional target:** P1 for planetary joys; existing dignity
subsystem remains at its current constitutional level.

**Do not:** Modify `egyptian_bounds.py`, `aspects.py`, or `timelords.py`
during this phase.

---

### Phase 2 -- Bounds Expansion and Halb

**Scope:** Add Ptolemaic and Chaldean term tables alongside the existing
Egyptian bounds, and implement the halb condition.

**Modules:** `moira/egyptian_bounds.py` (renamed or generalized),
`moira/dignities.py`

**Tasks:**

1. Add `PTOLEMAIC = "ptolemaic"` and `CHALDEAN = "chaldean"` to
   `EgyptianBoundsDoctrine` (consider renaming to `BoundsDoctrine`).

2. Add `PTOLEMAIC_BOUNDS` table (Tetrabiblos I.21):
   ```
   Aries:   Jupiter 0-6, Venus 6-14, Mercury 14-21, Mars 21-26, Saturn 26-30
   Taurus:  Venus 0-8, Mercury 8-15, Jupiter 15-22, Saturn 22-26, Mars 26-30
   ...
   ```

3. Add `CHALDEAN_BOUNDS` table (Yavanajataka / Rhetorius tradition).

4. Relax `EgyptianBoundsPolicy.__post_init__` to accept all three
   doctrines.

5. Route `egyptian_bound_of()` and `bound_ruler()` through the policy
   doctrine to select the correct table.

6. Implement `is_in_halb()` in `moira/dignities.py`:
   Halb is satisfied when a planet meets two of the three hayz conditions
   (sect + hemisphere, sect + sign gender, or hemisphere + sign gender)
   but not all three.

7. Add `HALB = "halb"` to `AccidentalConditionKind` with
   `SCORE_HALB = 1` and polarity `STRENGTHENING`.

8. Add `IN_HALB` to `SectStateKind`.

**Acceptance criteria:**

- `egyptian_bound_of(15.0, policy=BoundsPolicy(doctrine=PTOLEMAIC))`
  returns Venus for 15 degrees Aries (Ptolemaic: Venus rules 6-14).
- `egyptian_bound_of(15.0, policy=BoundsPolicy(doctrine=EGYPTIAN))`
  returns Mercury for 15 degrees Aries (Egyptian: Mercury rules 12-20).
- `is_in_halb("Moon", ...)` returns `True` when Moon is in sect and in
  a feminine sign but in the upper hemisphere (two of three conditions met).
- All existing Egyptian bounds tests pass without modification.

**Constitutional target:** P1 for Ptolemaic and Chaldean bounds.

**Do not:** Modify `aspects.py` or `timelords.py` during this phase.

---

### Phase 3 -- Planetary Condition Expansion

**Scope:** Add oriental/occidental classification, besieging detection,
and sinister/dexter aspect direction to the general aspect engine.

**Modules:** `moira/dignities.py`, `moira/aspects.py`

**Tasks:**

1. Implement `oriental_occidental(planet: str, planet_lon: float, sun_lon: float, planet_speed: float) -> str`:
   - Superior planets (Mars, Jupiter, Saturn): oriental when rising before
     the Sun (planet longitude < sun longitude in zodiacal order), occidental
     when rising after.
   - Inferior planets (Mercury, Venus): oriental when morning star (heliacal
     rising precedes the Sun), occidental when evening star.
   - Luminaries: not applicable.

2. Add `ORIENTAL = "oriental"` and `OCCIDENTAL = "occidental"` to
   `AccidentalConditionKind` with scores: `SCORE_ORIENTAL = 2` (for
   superior planets when oriental, inferior when occidental) and
   `SCORE_OCCIDENTAL = -2` (reverse).

3. Implement `is_besieged(planet_lon: float, chart_positions: dict, orb: float = 12.0) -> bool | tuple[str, str]`:
   - A planet is besieged when its nearest neighbours by ecliptic longitude
     on both sides are malefics (Mars, Saturn) within the specified orb.
   - Return the pair of besieging malefics, or False.

4. Add `BESIEGED = "besieged"` to `AccidentalConditionKind` with
   `SCORE_BESIEGED = -5` and polarity `WEAKENING`.

5. Add `AspectDirection(StrEnum)` to `moira/aspects.py`:
   ```python
   class AspectDirection(StrEnum):
       SINISTER = "sinister"    # forward in zodiacal order
       DEXTER = "dexter"        # backward in zodiacal order
   ```

6. Add `direction: AspectDirection | None` field to `AspectData`.

7. Compute direction at detection time: if body1 is zodiacally behind
   body2, the aspect is dexter from body1's perspective (the ray is cast
   backward).

8. Add `overcoming(body1_lon: float, body2_lon: float) -> str | None`:
   - A planet overcomes another when it is in the 10th-sign position
     relative to it (i.e., it casts a dexter square).
   - Returns the name of the overcoming relationship or None.

**Acceptance criteria:**

- Jupiter at 100 degrees with Sun at 120 degrees: oriental (rising before
  the Sun).
- Venus as morning star (longitude less than Sun, positive speed toward
  Sun): oriental.
- Mars at 15 degrees Aries, Moon at 17 degrees Aries, Saturn at 13 degrees
  Aries: Moon is besieged between Mars and Saturn.
- Aspect between planet at 10 degrees Aries and planet at 10 degrees Leo:
  dexter trine from the perspective of the Leo planet, sinister from the
  Aries planet.
- Planet at 10 degrees Cancer overcomes a planet at 10 degrees Aries
  (10th-sign square).
- All existing aspect tests pass.

**Constitutional target:** P1 for oriental/occidental, besieging, and
aspect direction.

**Do not:** Modify `egyptian_bounds.py`, `timelords.py`, or house
computation during this phase.

---

### Phase 4 -- Whole-Sign Aspects

**Scope:** Add a whole-sign (sign-based) aspect detection mode as an
alternative geometry alongside degree-based detection.

**Module:** `moira/aspects.py`

**Tasks:**

1. Add `WHOLE_SIGN = "whole_sign"` to `AspectDomain`.

2. Implement `find_whole_sign_aspects(positions: dict) -> list[AspectData]`:
   - Compute the sign index (0-11) for each body.
   - Determine aspect by sign-count difference:
     - 0 signs: conjunction
     - 2 or 10 signs: sextile
     - 3 or 9 signs: square
     - 4 or 8 signs: trine
     - 6 signs: opposition
   - Aversion (1, 5, 7, 11 signs apart): no Ptolemaic aspect.

3. Whole-sign aspects have no orb -- they are either present or absent.
   Set `orb = 0.0` and `exactness = 1.0` on the result vessel.

4. Whole-sign aspects still carry sinister/dexter direction (from Phase 3).

5. Add `whole_sign: bool = False` parameter to `AspectPolicy` to enable
   whole-sign mode as an alternative to degree-based detection.

**Acceptance criteria:**

- Mars at 29 degrees Aries and Jupiter at 1 degree Leo: whole-sign trine
  (4 signs apart), but no degree-based trine within standard orb.
- Sun at 1 degree Aries and Moon at 29 degrees Aries: whole-sign
  conjunction.
- Venus at 15 degrees Taurus and Saturn at 15 degrees Cancer: whole-sign
  sextile (2 signs apart).
- Venus at 15 degrees Taurus and Mars at 15 degrees Gemini: aversion
  (1 sign apart), no whole-sign aspect.
- All existing degree-based aspect tests pass unchanged.

**Constitutional target:** P1 for whole-sign aspects.

---

## Dependency Map

| Phase | Depends on | Touches |
|-------|-----------|---------|
| Phase 1 | None | `dignities.py`, `longevity.py` |
| Phase 2 | None | `egyptian_bounds.py`, `dignities.py` |
| Phase 3 | Phase 1 (for enum patterns) | `dignities.py`, `aspects.py` |
| Phase 4 | Phase 3 (sinister/dexter) | `aspects.py` |

Phases 1 and 2 are independent and can be implemented in parallel.
Phase 3 requires Phase 1 for enum extension patterns.
Phase 4 requires Phase 3 for aspect direction infrastructure.

---

## Validation Strategy

### Phase 1

- Unit tests: domicile/exaltation/triplicity/bound/face lookup for all
  12 signs, 7 classical planets.
- Joy table: exhaustive 7-planet x 12-house matrix.
- Regression: all existing `test_dignities.py` and `test_longevity.py`
  tests must pass.

### Phase 2

- Ptolemaic bounds: tabular test against Tetrabiblos I.21 (Hephaistion
  reconstruction, Robbins translation).
- Chaldean bounds: tabular test against Pingree, Yavanajataka (1978).
- Halb: combinatorial tests of the three-condition partial match.
- Regression: all existing `test_egyptian_bounds.py` tests must pass.

### Phase 3

- Oriental/occidental: test against ephemeris data for known morning/
  evening star configurations (e.g., Venus as morning star on a known date).
- Besieging: synthetic chart positions with known malefic enclosures.
- Sinister/dexter: verify direction for aspects in all four quadrants.
- Overcoming: verify 10th-sign square detection.
- Regression: all existing `test_aspects.py` tests must pass.

### Phase 4

- Whole-sign: synthetic tests for all five Ptolemaic aspects by sign count.
- Aversion: 1, 5, 7, 11 sign separations yield no aspect.
- Edge cases: bodies at 0 and 29 degrees of same sign (conjunction),
  bodies at 29 degrees and 1 degree of adjacent signs (no conjunction).
- Regression: all existing degree-based aspect tests must pass.

---

## Open Questions

1. Should `EgyptianBoundsDoctrine` be renamed to `BoundsDoctrine` (or
   `TermsDoctrine`) when Ptolemaic and Chaldean are added, or should the
   Egyptian prefix be kept for backward compatibility?

2. Should `dignity_score_at()` remain in `longevity.py` or migrate to
   `dignities.py` now that the scoring constants are being formalized there?

3. Should oriental/occidental for inferior planets (Mercury, Venus) use
   elongation-based classification (> 0 degrees elongation = morning star)
   or heliacal-event-based classification (has the planet had its last
   heliacal rising)?

4. Should whole-sign aspects produce the same `AspectData` vessel as
   degree-based aspects, or a distinct `WholeSignAspectData` vessel?

5. What score should be assigned to overcoming?  Classical sources treat
   it as a qualitative relational condition rather than a point-based
   dignity.  It may belong in a relational layer rather than the
   accidental condition enum.

6. Should Dorotheus-style triplicity be the only scheme at Phase 1, or
   should the triplicity axis be parameterized from the start?

---

## Research Sources

- Ptolemy, *Tetrabiblos*, trans. F. E. Robbins (Loeb Classical Library, 1940).
  Bounds tables: I.20-21.  Triplicity: I.18.  Oriental/occidental: I.24.
- Dorotheus of Sidon, *Carmen Astrologicum*, trans. D. Pingree (1976).
  Triplicity rulers (day/night/participating): I.1.
- Vettius Valens, *Anthology*, trans. M. Riley (2010).
  Zodiacal releasing: IV.4.  Antiscia: II.37.  Overcoming: multiple.
- Hephaistion of Thebes, *Apotelesmatics*, Book I.
  Egyptian bounds reconstruction.
- Chris Brennan, *Hellenistic Astrology: The Study of Fate and Fortune*
  (Amor Fati, 2017).  Planetary joys: Ch. 5.  Profections: Ch. 9.
  Sect: Ch. 7.  Overcoming: Ch. 11.  Whole-sign aspects: Ch. 11.
- D. Pingree, *The Yavanajataka of Sphujidhvaja* (Harvard, 1978).
  Chaldean bounds.
- Robert Hand, "Whole Sign Houses: The Oldest House System" (ARHAT, 2000).
  Whole-sign aspect rationale.
- Existing Moira modules: `moira/dignities.py`, `moira/longevity.py`,
  `moira/egyptian_bounds.py`, `moira/aspects.py`.
