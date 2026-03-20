# Moira Validation Report — Astrology

**Version:** 1.0
**Date:** 2026-03-20
**Runtime target:** Python 3.14
**Validation philosophy:** Swiss/Astro.com as sanity oracle; Moira as regression baseline

---

## 1. Executive Statement

This document covers the astrological convention layer of Moira: techniques
that are built on top of the astronomy engine but involve definitional choices
specific to astrological tradition.

The validation standard here differs from the astronomy layer:

- Swiss Ephemeris / Astro.com `swetest` is used as a **sanity oracle** to
  confirm correct implementation, not as the final authority
- Where Moira diverges from Swiss, the cause is audited: model difference
  (expected) vs. implementation bug (must be fixed)
- Once a technique is confirmed correct, Moira's own output is locked in as
  the regression baseline
- Thresholds are technique-appropriate: geometry techniques hold to 0.001°;
  predictive techniques allow 0.01°; time-based searches allow seconds to
  fractions of a day

---

## 2. Validation Surface

| Domain | Oracle | Enforcement | Status |
|---|---|---|---|
| Sidereal systems / ayanamshas (30 systems) | Astro.com `swetest` offline fixture | `pytest` | ✅ Validated |
| House systems (15 systems, 3168 iterations) | Swiss `setest/t.exp` offline fixture | `pytest` + validator script | ✅ Validated |
| Aspects (major, tight-orb) | Moira planet_at() pipeline (Horizons-validated) + angular_distance geometry | `pytest` | ✅ Validated |
| Antiscia / contra-antiscia | Formula derivation + invariants (Valens, Lilly) | `pytest` | ✅ Validated |
| Midpoints | Formula derivation + invariants (Ebertin, Witte) | `pytest` | ✅ Validated |
| Lots / Arabic Parts | Formula derivation, day/night reversal (Paulus, Valens) | `pytest` | ✅ Validated |
| Dignities | Essential table lookups, accidental scoring (Lilly, Ptolemy) | `pytest` | ✅ Validated |
| Harmonics | Formula derivation + round-trip invariant (Addey) | `pytest` | ✅ Validated |
| Profections | Annual/monthly arithmetic, 12-year cycle (Brennan, Valens) | `pytest` | ✅ Validated |
| Planetary hours | Chaldean sequence + day-ruler derivation (Porphyry, Hephaestio) | `pytest` | ✅ Validated |
| Primary directions | — | None yet | ❌ Needs oracle |
| Secondary progressions | — | None yet | ❌ Needs oracle |
| Solar arc directions | — | None yet | ❌ Needs oracle |
| Dashas | — | None yet | ❌ Needs oracle |
| Parans | Self-consistency only | `pytest` | ⚠️ Needs external oracle |
| Gauquelin sectors | Mentioned as validated, no detail | `pytest` | ⚠️ Needs documentation |
| Manazil / lunar mansions | — | None yet | ❌ Needs oracle |

---

## 3. Sidereal Systems

**Oracle:** Official Astro.com `swetest` CGI output, captured offline
**Fixture:** `tests/fixtures/sidereal_swetest_reference.json`
**Threshold:** 0.001° (3.6 arcseconds)
**Test file:** `tests/integration/test_sidereal_external_reference.py` — **121 passed**

30 ayanamsha systems exposed. 29 have direct Swiss-mappable validation.
1 (`Galactic Center 5 Sag`) validated by invariant: = `Galactic Center 0 Sag` + 5°.

Validated systems include: Lahiri, Fagan-Bradley, Krishnamurti, Raman,
Yukteshwar, Djwhal Khul, Hipparchos, Suryasiddhanta, Aryabhata, SS Revati,
SS Citra, True Chitrapaksha, True Revati, True Pushya, Aldebaran (15 Tau),
Babylonian variants, Galactic Center (0 Sag), Galactic Center (Cochrane),
Galactic Center (RGB), and others.

Fixture covers 2 epochs × 29 systems × 2 modes (mean/true) = 116 direct
comparisons, plus invariant and coverage guards.

---

## 4. House Systems

**Oracle:** Official Swiss Ephemeris `setest/t.exp`
**Fixture:** `tests/fixtures/swe_t.exp`
**Threshold:** 0.001° (3.6 arcseconds)
**Test files:**
- `tests/integration/test_houses_external_reference.py` — **1 passed** (integration guard)
- `tests/unit/test_polar_houses.py` — **3 passed** (Arctic/Antarctic fallback guard)
- `scripts/compare_swetest.py --offline` — **3168 iterations, 0 failures**

15 house systems validated: Placidus, Koch, Campanus, Regiomontanus, Porphyry,
Equal, Whole Sign, Alcabitius, Morinus, Topocentric, Vehlow, Meridian,
Azimuthal, Krusinski-Pisa, APC.

**Stress cases covered:**
- **Equatorial**: lat=0.0
- **Polar Edge**: lat=±90.0 and fallback threshold |lat| >= 75.0 (verified fallback to Porphyry)
- **Deep South**: lat=-89.90
- **Longitudinal**: Multiple east/west longitudes.

Two systems (Azimuthal, APC) were found genuinely wrong during validation and
fixed. All 3168 iterations now pass. The 'Test of the Arctic Circle' has confirmed
that the engine's mathematical safety valves are active and correct.

---

## 5. Aspects

**Validation layers:**

- **Layer A — position substrate:** ecliptic longitudes are produced by
  Moira's `planet_at()` pipeline, which is externally validated against JPL
  Horizons (`test_horizons_planet_apparent.py`, 120 cases, worst error 0.576″).
  Storing those positions in the fixture anchors the aspect geometry to a
  validated astronomical substrate.

- **Layer C — angular_distance arithmetic:** for every body pair the fixture
  records the expected angular separation. The test recomputes it from scratch
  via `angular_distance()` and verifies it matches the stored value to < 1e-6°.

**Fixture:** `tests/fixtures/aspects_reference.json`  
**Generated by:** `scripts/build_aspects_fixture.py`  
**Threshold:** 1e-6° (pure geometry — no model uncertainty)  
**Test file:** `tests/integration/test_aspects_external_reference.py`  
**Aspect tier:** 0 (major only: Conjunction, Sextile, Square, Trine, Opposition)  
**Tight-orb window:** 1.0° (aspects within 1° of exact only — stable across builds)  
**Epochs:** J1900, J1950, J2000, J2024  
**Bodies:** 10 major bodies (Sun through Pluto)

Minor aspects (Common Minor, Extended Minor) remain covered by the unit test
suite (`tests/unit/test_aspects.py`).

---

## 6. Rule Engine Validation

**Test file:** `tests/unit/test_rule_engine_validation.py` — **57 passed**

The following seven modules are pure arithmetic / rule-table engines with no
ephemeris dependency. Their validation is therefore formula-derivation and
invariant-based rather than oracle-comparison. All expected values were derived
by hand from the cited primary sources.

### 6.1 Antiscia and Contra-antiscia

**Canon:** Vettius Valens, Anthology II.37; William Lilly, Christian Astrology (1647) p. 90  
**Formula:** antiscion = (180° − lon) mod 360°; contra = (360° − lon) mod 360°  
**Validation:** hand-derived table for 7 longitude values; round-trip invariant;
contact detection with orb inclusion/exclusion; zero-crossing edge cases

### 6.2 Midpoints

**Canon:** Reinhold Ebertin, The Combination of Stellar Influences (1940);
Alfred Witte, Rules for Planetary Pictures (Hamburg School)  
**Formula:** shorter-arc midpoint; 90° dial projection (lon × 4 mod 90)  
**Validation:** hand-derived table for 5 body pairs; commutativity invariant;
self-midpoint invariant; pair count (C(7,2)=21); sort order; seam crossing at 0°/360°

### 6.3 Profections

**Canon:** Chris Brennan, Hellenistic Astrology (2017), Ch. 9;
Vettius Valens, Anthology, Book IV  
**Formula:** profected ASC = (natal_asc + age × 30°) mod 360°; house = (age mod 12) + 1  
**Validation:** hand-derived table for 9 cases across ages 0–30; house range guard;
monthly lords length; first monthly lord matches lord of year; 12-year cycle identity

### 6.4 Planetary Hours

**Canon:** Porphyry, Introduction to Tetrabiblos;
Hephaestio of Thebes, Apotelesmatika I  
**Tables validated:** Chaldean sequence (Saturn through Moon), day-ruler index
for all 7 weekdays, night-hour-1 derivation for Sunday, 24-hour completeness  
**Key invariant:** (start_idx + 24) mod 7 = next day's start_idx (the "+3 shift" property)

### 6.5 Harmonics

**Canon:** John Addey, Harmonics in Astrology (1976)  
**Formula:** harmonic_lon = (natal_lon × H) mod 360°  
**Validation:** hand-derived table for 9 cases; H1 identity invariant; output in [0,360) invariant;
sorted output; harmonic clamped to ≥ 1

### 6.6 Lots / Arabic Parts

**Canon:** Paulus Alexandrinus, Introductory Matters (~375 CE);
Vettius Valens, Anthology, Books II–IV  
**Formula:** Lot = (ASC + Add − Sub) mod 360°; night reversal where specified  
**Validation:** Part of Fortune day and night formulas; Part of Spirit day and night;
all longitudes in [0,360); Fortune + Spirit = 2 × ASC complement invariant

### 6.7 Dignities

**Canon:** William Lilly, Christian Astrology (1647), Book I;
Ptolemy, Tetrabiblos I.17–22  
**Validation:** 12 essential dignity cases (domicile, exaltation, detriment, fall,
peregrine) across all 7 classic planets; angular/cadent house bonuses; retrograde
penalty; cazimi and combust boundaries; mutual reception detection;
total_score = essential + accidental invariant; traditional planet sort order;
sect light day/night; hayz conditions

---

## 7. Outstanding Astrology Validation Roadmap

### 7.1 Aspects

**Recommended oracle:** Astro.com chart output or Solar Fire
**Threshold:** 0.001°
**What to validate:**
- Aspect angle accuracy (conjunction, sextile, square, trine, opposition,
  minor aspects)
- Applying vs. separating determination
- Partile detection
- Sign boundary behavior (out-of-sign aspects)
- Orb calculation consistency

### 7.2 Primary Directions

**Recommended oracle:** Solar Fire or Janus (with explicit model declaration)
**Threshold:** 0.01° (technique has inherent model variation)
**What to validate — must declare model explicitly:**
- Placidus semi-arc directions (mundane)
- Regiomontanus directions (mundane)
- Ptolemaic (in mundo) directions
- Topocentric directions
- With and without latitude
- Converse directions
- Known historical examples (e.g., Lilly's own chart)

### 7.3 Secondary Progressions

**Recommended oracle:** Astro.com progressed chart
**Threshold:** 0.01°
**What to validate:**
- Day-for-a-year progression
- Progressed Ascendant and MC
- Progressed lunation cycle
- Known historical examples

### 7.4 Solar Arc Directions

**Recommended oracle:** Astro.com solar arc chart
**Threshold:** 0.01°
**What to validate:**
- Solar arc rate calculation
- All body positions at known solar arc dates
- Converse solar arcs

### 7.5 Dashas

**Recommended oracle:** Astro.com Vedic chart (Vimshottari dasha)
**Threshold:** 1 day (dasha boundaries)
**What to validate:**
- Vimshottari dasha start dates for known charts
- Sub-dasha (antardasha) boundaries
- Correct Moon nakshatra detection at birth

### 7.6 Parans

**Current state:** Self-consistency only (cross-checked against Moira
rise/set-transit engine). This is not external oracle validation.

**Recommended oracle:** Solar Fire paran report or Astro.com
**What to validate:**
- Paran detection for known star/planet pairs
- Latitude sensitivity
- Orb behavior

### 7.7 Manazil / Lunar Mansions

**Recommended oracle:** Published lunar mansion tables (Ibn Arabi, Picatrix)
**What to validate:**
- Mansion boundary calculation
- Moon mansion assignment for known dates
- Arabic and Sanskrit name mapping consistency
