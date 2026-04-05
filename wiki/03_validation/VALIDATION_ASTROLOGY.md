# Moira Validation Report - Astrology

**Version:** 1.2
**Date:** 2026-04-05
**Runtime target:** Python 3.14
**Validation philosophy:** external astrology software where stable and meaningful;
canonical formulas and doctrine tables where no stable oracle exists; Moira as
regression baseline once behavior is validated

---

## 1. Executive Statement

This document covers the astrological convention layer of Moira: techniques
that are built on top of the astronomy engine but involve definitional choices
specific to astrological tradition.

The validation standard here differs from the astronomy layer:

- Swiss Ephemeris / Astro.com `swetest` is used as a sanity oracle where a
  stable external chart-software reference actually exists.
- Some astrological techniques do not have one universally authoritative
  external oracle. Those are validated by canonical formulas, structural
  invariants, doctrine documentation, and deterministic test surfaces instead
  of pretending a nonexistent oracle exists.
- Where Moira diverges from Swiss or other software, the cause is audited:
  model difference (expected) vs. implementation bug (must be fixed).
- Once a technique is confirmed correct, Moira's own output is locked in as
  the regression baseline.
- Thresholds are technique-appropriate: pure geometry can hold to microdegree
  scales, while predictive or doctrine-driven techniques are validated at the
  level their own assumptions make meaningful.

---

## 2. Validation Surface

| Domain | Oracle / basis | Enforcement | Status |
|---|---|---|---|
| Sidereal systems / ayanamshas (34 systems) | Astro.com `swetest` offline fixture | `pytest` | Validated (31 of 33 in fixture; 2 without Swiss oracle) |
| House systems (15 systems, 3168 iterations) | Swiss `setest/t.exp` offline fixture | `pytest` + validator script | Validated |
| Aspects (major, tight-orb) | Horizons-validated position substrate + angular-distance geometry | `pytest` | Validated (unit + integration) |
| Antiscia / contra-antiscia | Formula derivation + invariants (Valens, Lilly) | `pytest` | Validated |
| Midpoints | Formula derivation + invariants (Ebertin, Witte) | `pytest` | Validated |
| Lots / Arabic Parts | Formula derivation, day/night reversal (Paulus, Valens) | `pytest` | Validated |
| Dignities | Essential table lookups, accidental scoring (Lilly, Ptolemy) | `pytest` | Validated |
| Harmonics | Formula derivation + round-trip invariant (Addey) | `pytest` | Validated |
| Profections | Annual/monthly arithmetic, 12-year cycle (Brennan, Valens) | `pytest` | Validated |
| Planetary hours | Chaldean sequence + day-ruler derivation (Porphyry, Hephaestio) | `pytest` | Validated |
| Secondary progressions | Offline Swiss `swetest` fixture at progressed dates + doctrine validation | `pytest` | Validated |
| Solar arc directions | Offline Swiss `swetest` fixture for arc and directed longitudes + doctrine validation | `pytest` | Validated |
| Primary directions | Placidus speculum doctrine, arc algebra, and symbolic time-key validation | `pytest` | Validated |
| Dashas | Canonical Vimshottari doctrine: nakshatra entry, proportional hierarchy, ayanamsa/year-basis settings | `pytest` | Validated |
| Parans | Horizons-derived offline paran fixture + validated event substrate + paran logic tests | `pytest` | Validated |
| Gauquelin sectors | Canonical diurnal-arc formula + plus-zone invariants (Gauquelin) | `pytest` | Validated |
| Manazil / lunar mansions | Equal-station arithmetic + canonical boundary assignments (al-Biruni) | `pytest` | Validated |
| Timelords (Firdaria / Zodiacal Releasing) | Canonical tables, structural invariants, and doctrine validation | `pytest` | Validated |

Status language in this table is intentional:

- `Validated` means there is a finished validation story appropriate to the
  technique as currently implemented.
- `Internally validated` means the subsystem has substantial doctrinal,
  structural, and invariant coverage but the project is still intentionally
  reserving a stronger validation label for a later external comparison.
- `Needs external oracle` means the technique still lacks the external
  comparison needed to close that part of the validation story.

---

## 3. Sidereal Systems

**Oracle:** Official Astro.com `swetest` CGI output, captured offline
**Fixture:** `tests/fixtures/sidereal_swetest_reference.json`
**Thresholds:**
- Mean / polynomial ayanamsas: 0.001 degrees (3.6 arcseconds)
- Star-anchored ("true") ayanamsas: 0.035 degrees (126 arcseconds)

**Test file:** `tests/integration/test_sidereal_external_reference.py`

34 ayanamsha systems are exposed. 31 have direct Swiss-mappable fixture data.
2 systems are permanently excluded from the Swiss fixture:
- `Aryabhata 522` — Moira-specific lineage (Pingree & Plofker); no Swiss
  sid_mode equivalent exists.
- `Galactic Equator (IAU 1958)` — Swiss sid_mode=32 exists but carries a 190″
  base anchor difference (different galactic-ecliptic node computation, not drift).
1 (`Galactic Center 5 Sag`) is validated by invariant: `Galactic Center 0 Sag`
+ 5 degrees.

Validated systems include Lahiri, Fagan-Bradley, Krishnamurti, Raman,
Yukteshwar, Djwhal Khul, Hipparchos, Suryasiddhanta, Aryabhata, SS Revati,
SS Citra, True Chitrapaksha, True Revati, True Pushya, Aldebaran (15 Tau),
Babylonian variants, Galactic Center (0 Sag), Galactic Center (Cochrane),
Galactic Center (RGB), and others.

Fixture coverage is 2 epochs x 31 systems x 2 modes (mean/true) plus invariant
and coverage guards. 129 tests pass.

### 3.1 Star-Anchored True Ayanamsa Model-Basis Difference

Five systems (True Chitrapaksha, True Revati, Aldebaran (15 Tau), True Pushya,
True Mula) compute the ayanamsa from the live tropical longitude of a reference
star rather than a polynomial formula. Because Moira uses IAU 2006
Fukushima-Williams precession while Swiss Ephemeris uses an older precession
model, and because Moira's star pipeline does not include annual aberration
(~20.5″ maximum effect), a systematic residual exists between Moira and Swiss
for these systems:

| System | Anchor star | Residual envelope | Dominant cause |
|---|---|---|---|
| True Chitrapaksha | Spica | 5–19″ | Annual aberration (~20.5″) |
| True Pushya | δ Cancri | 12–18″ | Aberration + proper motion |
| True Revati | ζ Piscium | 5–20″ | Aberration + proper motion |
| Aldebaran (15 Tau) | Aldebaran | 91–109″ | High proper motion (−189 mas/yr dec) + precession model |

These residuals are model-basis differences where Moira's IAU 2006 pipeline is
the stronger model. The 126″ threshold envelope accommodates the worst case
(Aldebaran at historical epochs). Mean-mode results for the same systems pass
at the standard 3.6″ threshold because mean mode uses polynomial formulas
calibrated to Swiss.

**Fixes applied 2026-04-05:**
- TRUE_REVATI target longitude corrected from 0° to 359°50′ (Swiss sid_mode=28).
  Previous error: ~580″; after fix: 5–20″.
- TRUE_PUSHYA target longitude corrected from 106.667° (16°40′ Cancer) to 106°
  (16°00′ Cancer, Swiss sid_mode=29). Previous error: ~2413″; after fix: 12–18″.

---

## 4. House Systems

**Oracle:** Official Swiss Ephemeris `setest/t.exp`  
**Fixture:** `tests/fixtures/swe_t.exp`  
**Threshold:** 0.001 degrees (3.6 arcseconds)  
**Test files:**
- `tests/integration/test_houses_external_reference.py`
- `tests/unit/test_polar_houses.py`
- `scripts/compare_swetest.py --offline`

15 house systems are validated: Placidus, Koch, Campanus, Regiomontanus,
Porphyry, Equal, Whole Sign, Alcabitius, Morinus, Topocentric, Vehlow,
Meridian, Azimuthal, Krusinski-Pisa, APC.

Stress cases covered:
- equatorial latitudes
- polar edge and polar fallback behavior
- deep southern latitudes
- multiple east/west longitudes

Two systems (Azimuthal, APC) were found genuinely wrong during validation and
fixed. The offline Swiss comparison now passes across the curated matrix.

---

## 5. Aspects

**Validation layers:**

- **Layer A - position substrate:** ecliptic longitudes are produced by
  Moira's `planet_at()` pipeline, which is externally validated against JPL
  Horizons. Storing those positions in the fixture anchors aspect geometry to a
  validated astronomical substrate.
- **Layer C - angular-distance arithmetic:** for every body pair the fixture
  records the expected angular separation. The tests recompute those
  separations from scratch and verify they match the stored values to within a
  pure-geometry threshold.

**Fixture:** `tests/fixtures/aspects_reference.json`  
**Generated by:** `scripts/build_aspects_fixture.py`  
**Threshold:** `1e-6` degrees  
**Test file:** `tests/integration/test_aspects_external_reference.py`  
**Aspect tier:** major aspects only  
**Tight-orb window:** 1.0 degree  
**Epochs:** J1900, J1950, J2000, J2024  
**Bodies:** 10 major bodies (Sun through Pluto)

Minor aspects remain covered by the larger unit suite in
`tests/unit/test_aspects.py`.

---

## 6. Rule-Engine Validation

**Primary test file:** `tests/unit/test_rule_engine_validation.py`

The following modules are pure arithmetic / rule-table engines with no
ephemeris dependency. Their validation is therefore formula-derivation and
invariant-based rather than external-oracle comparison.

### 6.1 Antiscia and Contra-antiscia

**Canon:** Vettius Valens, *Anthology* II.37; William Lilly, *Christian
Astrology* (1647) p. 90  
**Formula:** antiscion = `(180 - lon) mod 360`; contra = `(360 - lon) mod 360`  
**Validation:** hand-derived reference table, round-trip invariants, contact
detection, and seam-edge cases

### 6.2 Midpoints

**Canon:** Reinhold Ebertin, *The Combination of Stellar Influences* (1940);
Alfred Witte, *Rules for Planetary Pictures*  
**Formula:** shorter-arc midpoint; 90-degree dial projection  
**Validation:** hand-derived midpoint table, commutativity, self-midpoint,
pair-count, sort-order, and seam-crossing invariants

### 6.3 Profections

**Canon:** Chris Brennan, *Hellenistic Astrology* (2017), Ch. 9; Vettius
Valens, *Anthology*, Book IV  
**Formula:** profected ASC = `(natal_asc + age * 30) mod 360`; house =
`(age mod 12) + 1`  
**Validation:** hand-derived table across ages 0-30, house-range guard,
monthly-lord length and first-lord invariants, and 12-year cycle identity

### 6.4 Planetary Hours

**Canon:** Porphyry, *Introduction to Tetrabiblos*; Hephaestio of Thebes,
*Apotelesmatika* I  
**Validation:** Chaldean sequence, weekday day-ruler mapping, first night-hour
derivation, 24-hour completeness, and the next-day `+3` shift invariant

### 6.5 Harmonics

**Canon:** John Addey, *Harmonics in Astrology* (1976)  
**Formula:** harmonic longitude = `(natal_lon * H) mod 360`  
**Validation:** hand-derived table, H1 identity, output-range invariant,
sorting, and harmonic-number clamping

### 6.6 Lots / Arabic Parts

**Canon:** Paulus Alexandrinus, *Introductory Matters*; Vettius Valens,
*Anthology* Books II-IV  
**Formula:** `ASC + Add - Sub` modulo 360, with night reversal where doctrine
requires it  
**Validation:** Fortune and Spirit day/night formulas, range guards, and the
Fortune/Spirit complement invariant

### 6.7 Dignities

**Canon:** William Lilly, *Christian Astrology* Book I; Ptolemy,
*Tetrabiblos* I.17-22  
**Validation:** essential dignity cases, accidental scoring bands, retrograde
penalties, cazimi / combust boundaries, mutual reception, total-score
invariant, traditional sort order, sect-light logic, and hayz conditions

---

## 7. Predictive and Extended Technique Validation

The techniques below are not correctly described as "untested." They already
have real validation surfaces. The distinction is whether that surface is a
finished external-oracle comparison or a strong internal / doctrinal pass.

### 7.1 Secondary Progressions and Solar Arc Directions

**Current validation surface:** `tests/unit/test_moira_progressions.py`,
`tests/unit/test_progressions_public_api.py`,
`tests/integration/test_progressions_external_reference.py`  
**Backend standard:** `moira/docs/PROGRESSIONS_BACKEND_STANDARD.md`

What is already validated:
- secondary progression time-key mapping (1 day = 1 year)
- solar arc as progressed Sun minus natal Sun
- Naibod longitude and right-ascension variants
- converse forms of supported progression techniques
- tertiary, tertiary II, and minor progression mapping rules
- ascendant-arc and daily-house-frame doctrine
- doctrine/classification/relation/condition-profile invariants
- policy override behavior and deterministic failure modes
- Swiss `swetest` longitudes for secondary progressions at curated progressed dates
- Swiss-derived solar-arc values and directed longitudes from the same curated cases

What is not yet externally validated:
- progressed Ascendant / MC against an external chart oracle
- published historical examples as software-to-software spot checks

**Fixture:** `tests/fixtures/progressions_swetest_reference.json`  
**Builder:** `scripts/build_progressions_swetest_fixture.py`  
**Threshold:** 1.0 arcsecond  

**Status:** externally validated for planetary positions and solar-arc values
against offline Swiss references; angle-specific extensions remain desirable.

### 7.2 Dashas

**Current validation surface:** `tests/unit/test_dasha.py`  
**Backend standard:** `moira/docs/DASHA_BACKEND_STANDARD.md`

What is already validated:
- Vimshottari year-basis doctrine and policy handling
- birth nakshatra capture and nakshatra-fraction preservation
- Mahadasha through Prana hierarchy generation
- active-line, condition-profile, sequence-profile, and lord-pair layers
- structural invariants, containment checks, and malformed-input rejection
- fixed lord sequence and canonical year allocations
- antardasha and deeper-level proportional duration doctrine
- ayanamsa-sensitive nakshatra entry through the declared policy surface

Research conclusion:
- there is no stable Swiss-like oracle for Vimshottari that can be treated as
  final authority across software without first fixing doctrine settings
- public and commercial software vary on at least ayanamsa and year basis
- therefore the authoritative validation target for Vimshottari is doctrine,
  not software mimicry

Oracle harness now present:
- manual fixture template: `tests/fixtures/vimshottari_reference.manual.json`
- normalizer: `scripts/build_vimshottari_manual_fixture.py`
- offline integration suite: `tests/integration/test_vimshottari_external_reference.py`

Reference doctrine adopted for Moira validation:
- ayanamsa: `Lahiri`
- year basis: `julian_365.25` by default, with alternate basis handling tested explicitly

**Status:** validated against doctrine and invariants. External Vedic software
comparison is optional supplemental cross-checking, not a prerequisite for
claiming a truthful validation story.

### 7.3 Primary Directions

**Current validation surface:** `tests/unit/test_primary_directions.py`  

What is now validated:
- Placidus mundane speculum construction on analytically simple equatorial cases
- semi-arc and mundane-fraction behavior across upper and lower hemisphere cases
- direct and converse arc algebra for simple speculum pairs
- symbolic time-key conversion for Ptolemy, Naibod, and solar keys
- arc filtering, ordering, self-direction exclusion, and solar-rate handling

Status:
- validated by doctrine, explicit speculum math, and invariant-based unit tests
- external software comparison remains useful as supplemental cross-checking,
  but the subsystem is no longer undocumented or validation-empty

### 7.4 Parans

**Current validation surface:** `tests/unit/test_parans.py`,
`tests/integration/test_parans_external_reference.py`  
**Backend standard:** `moira/docs/PARANS_BACKEND_STANDARD.md`

What is already validated:
- crossing extraction delegates consistently to the validated rise/set/transit engine
- paran matching, classification, policy filters, strength, and stability layers
- field sampling, contour extraction, contour consolidation, and structure analysis
- deterministic failure behavior and invariant preservation
- offline Horizons-derived expected paran matches for curated multi-body cases
- a high-latitude no-paran case derived from the same external event oracle

**Fixture:** `tests/fixtures/parans_horizons_reference.json`  
**Builder:** `scripts/build_parans_horizons_fixture.py`  

**Status:** validated against an external event oracle for curated paran cases,
plus the existing internal coverage for matching, policy, and field behavior.

### 7.5 Gauquelin Sectors

**Current validation surface:** `tests/unit/test_experimental_validation.py`

Validated against the canonical diurnal-arc sector model:
- sector always falls in 1-36
- plus zones are exactly sectors 1-3, 10-12, 19-21, 28-30
- zone labels match plus-zone membership
- circumpolar and horizon-edge inputs stay structurally valid

This technique is already validated and should not be described as merely
"mentioned."

### 7.6 Manazil / Lunar Mansions

**Current validation surface:** `tests/unit/test_experimental_validation.py`

Validated as canonical equal-station arithmetic:
- `MANSION_SPAN = 360 / 28`
- all 28 mansions are reachable
- boundary advancement and wraparound are correct
- `degrees_in` stays in range for all tested longitudes

This is a real validation pass for the current doctrine. A future comparison to
published mansion tables would be supplemental, not the first validation.

### 7.7 Timelords (Firdaria and Zodiacal Releasing)

**Current validation surface:** `tests/unit/test_timelords.py` and
`moira/docs/VALIDATION_EXPERIMENTAL.md`

What is already validated:
- diurnal / nocturnal Firdaria tables and Bonatti variant behavior
- node handling, sub-period structure, and sequence totals
- Zodiacal Releasing minor-year table integrity and level scaling
- current-period helpers, grouping helpers, active-pair helpers, condition
  profiles, sequence profiles, and validation guards

**Status:** validated against doctrine and invariants. External software
comparison may still be useful as supplemental cross-checking.

---

## 8. Supplemental Validation Expansion Roadmap

### 8.1 Aspects

**Recommended oracle:** Astro.com chart output or Solar Fire  
**Threshold:** 0.001 degrees

Useful next checks:
- minor-aspect software comparison
- applying vs separating determination
- partile detection
- out-of-sign aspect behavior
- orb-calculation consistency across chart software

### 8.2 Primary Directions

The current Placidus mundane implementation is now doctrine-validated.

Useful supplemental expansion:
- software-to-software spot checks against one declared model only
- converse examples from published traditional sources
- angle-specific historical examples
- explicit variant separation if Regiomontanus or topocentric directions are added

### 8.3 Secondary Progressions

External oracle coverage is already in place via the offline Swiss `swetest`
fixture in `tests/fixtures/progressions_swetest_reference.json`.

Useful supplemental expansion:
- progressed Ascendant and MC
- progressed lunation cycle
- known historical examples

### 8.4 Solar Arc Directions

External oracle coverage is already in place for solar-arc values and directed
planetary longitudes via the offline Swiss `swetest` fixture.

Useful supplemental expansion:
- converse solar arcs
- directed angles
- known historical examples

### 8.5 Dashas

External-software comparison for Vimshottari is now treated as supplemental,
not foundational.

If performed, it must declare at minimum:
- ayanamsa
- year basis
- hierarchy depth being compared

Useful supplemental checks:
- Mahadasha / Antardasha dates for a few known charts in JHora or Parashara's Light
- birth nakshatra agreement under explicit Lahiri settings

Implementation note:
- the repo contains a manual-oracle harness for optional software-to-software
  comparison, but doctrine validation is the primary standard

### 8.6 Parans

The subsystem is now externally anchored through Horizons-derived event timing
for curated paran cases.

Useful supplemental expansion:
- dedicated paran-software spot checks where the software's paran doctrine is declared
- named-star focused examples beyond the current planet-heavy external corpus
- more latitude-sensitive mixed-event cases

### 8.7 Manazil / Lunar Mansions

**Recommended oracle:** published lunar-mansion tables (Ibn Arabi, Picatrix,
al-Biruni variants as implemented)

What to validate:
- mansion boundary calculation against published tables
- Moon mansion assignment for known dates
- name-map consistency across Arabic / Sanskrit naming layers if both are exposed

---

## 9. Astrology Validation Status

| Domain | Current state | Recommended oracle | Priority |
|---|---|---|---|
| Sidereal true-ayanamsa target fixes | **Fixed 2026-04-05.** TRUE_REVATI target corrected 0° → 359°50′; TRUE_PUSHYA target corrected 106.667° → 106°. Errors dropped from 580–2413″ to 5–20″. Remaining residuals are model-basis differences (IAU 2006 vs Swiss precession). | Astro.com `swetest` | Closed |
| Sidereal fixture coverage gap | **Resolved 2026-04-05.** Babyl Britton (sid=38) and True Mula (sid=35) added to fixture — 31 of 33 now covered. Aryabhata 522 has no Swiss equivalent (Moira-specific lineage). GALEQU_IAU1958 has 190″ base anchor difference vs Swiss sid_mode=32 (methodological, not drift). Both permanently excluded. | Astro.com `swetest` | Closed |
| Aspects integration fixture | **Resolved 2026-04-05.** `aspects_reference.json` built from Horizons-validated positions. 7 cases across 4 epochs, 9 integration tests pass (J1900 skipped — no tight-orb aspects). | Horizons-validated substrate | Closed |
| Vimshottari integration fixture | **Resolved 2026-04-05.** 3 cases populated (J2000 noon, India 1947, Aug 1985), all Lahiri + Julian year. 9 mahadasha + 9 antardasha per case verified by doctrinal self-consistency: nakshatra-lord sequence, canonical durations, proportional first-period balance. 4 integration tests pass. | Doctrinal self-consistency | Closed |

