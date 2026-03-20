# Moira Engine — Feature Roadmap & Mathematical Accuracy Register

**Engine version**: post-Phase α (sub-arcsecond accuracy certified)
**Date**: 2026-03-16
**Purpose**: Canonical record of missing features and mathematical improvement opportunities.

---

## Part I — Missing Features

Organised by priority: P1 = high-value / widely expected, P2 = important but less urgent, P3 = specialist / niche.

---

### 1. Vertex and Anti-Vertex  `P1` — `moira/houses.py`

**What it is**: The Vertex is a sensitive angle derived from the intersection of the prime vertical with the ecliptic in the western hemisphere of the chart. The Anti-Vertex is its exact opposite (Vertex + 180°). It appears in every serious house calculation package. The `HouseCusps` dataclass already has a `vertex` field — it is just never populated.

**Formula**:
```
Vertex RA = ARMC + 90°   (prime vertical intersects west horizon)
Vertex = ecliptic longitude corresponding to that RA at latitude φ

cos(lon_V) = −sin(ARMC) · cos(ε) · cos(lat) − sin(ε) · sin(lat)
            ────────────────────────────────────────────────────
                         cos(lat) · sin(ARMC) ...  [full Meeus Ch.24]
```

**Implementation note**: The vertex is already derivable from `_asc_from_armc` by calling it with `lat = −lat` and `armc = armc + 90°` then adding 180°. One extra call in `calculate_houses()`.

---

### 2. Antiscia & Contra-Antiscia  `P1` — new `moira/antiscia.py`

**What it is**: The antiscion of a planet is its mirror image across the 0°Cancer–0°Capricorn axis (solstice axis). The contra-antiscion mirrors across the 0°Aries–0°Libra axis (equinox axis). Antiscia are used in Uranian astrology (Hamburg School), traditional Hellenistic work, and modern European schools. They function as hidden aspects — two planets in antiscion are considered in a 0° relationship.

**Formulas**:
```
Antiscion(lon)         = (180° − lon) mod 360°
Contra-antiscion(lon)  = (360° − lon) mod 360°   [= −lon mod 360]
```

**Degree equivalences** (same declination):
| Planet at | Antiscion at |
|-----------|-------------|
|  0° Aries |  0° Libra   |
| 15° Taurus | 15° Leo   |
| 29° Gemini | 1° Cancer |

**Aspect check**: Two bodies A and B are in antiscion-aspect when `antiscion(lon_A) ≈ lon_B` within orb.

---

### 3. Declination: Parallels & Contra-Parallels  `P1` — `moira/aspects.py`

**What it is**: A parallel occurs when two bodies share the same declination (north or south). A contra-parallel occurs when one is at +δ and the other at −δ. Both function like a conjunction in strength. Swiss Ephemeris supports these; Moira currently ignores the declination axis entirely for aspects.

**Declination** is already computed in `PlanetData.declination` (via `sky_position_at`). The gap is purely in the aspect engine.

**Formula**:
```
Parallel:       |dec_A − dec_B| ≤ orb    (typical orb: 1°)
Contra-parallel: |dec_A + dec_B| ≤ orb   (signs opposite)
```

**Implementation note**: `AspectData` would need a `is_declination_aspect: bool` field. A new `find_declination_aspects()` function alongside `find_aspects()`, then merged in `Moira.chart()`.

---

### 4. Parans (Paranatellonta)  `P1` — new `moira/parans.py`

**What it is**: A paran occurs when two bodies are simultaneously on the same horizon or meridian circle — one rising while the other is setting, transiting, or anti-transiting. Parans are the primary way fixed stars influence a chart. Bernadette Brady's *Brady's Book of Fixed Stars* and Ptolemy's *Tetrabiblos* both rely on parans. Most serious software (Solar Fire, Janus, Sirius) includes paran calculation.

**The four mundane circles** for parans:
- **Rising** (on the Ascendant / east horizon)
- **Setting** (on the Descendant / west horizon)
- **Culminating** (on the MC / upper meridian)
- **Anti-Culminating** (on the IC / lower meridian)

**Paran types**: A × B paran — body A and body B occupy the same mundane circle on the same day (within ±30 min of each other, typically).

**Implementation approach**: For each latitude, compute the times when each body is on each of the four circles. Two bodies form a paran if their circle-crossing times coincide within the orb. `rise_set.py` already has the infrastructure (`get_transit`, `find_phenomena`).

---

### 5. Generic Planet Return  `P1` — `moira/transits.py`

**What it is**: `solar_return()` and `lunar_return()` already exist. But Venus return, Mars return, Jupiter return, Saturn return etc. are commonly used predictive tools. The architecture is identical — find when planet P returns to its natal longitude.

**Implementation note**: A single `planet_return(body: str, natal_lon: float, jd_start: float, ...)` function replacing the current duplication. `solar_return` and `lunar_return` should become thin wrappers around it.

---

### 6. Heliacal Rising & Setting of Fixed Stars  `P2` — `moira/fixed_stars.py`

**What it is**: The first and last visible rising/setting of a star near the Sun. Used in ancient Egyptian, Babylonian, and Hellenistic astrology. The heliacal rising of Sirius marked the Egyptian new year. Brady's *Starlight* software is built around this.

**Key parameter**: **Arcus Visionis** — the minimum solar depression angle for a star to be visible given its magnitude and sky conditions. Typical values: bright stars (~1 mag) need ~10°; faint stars need ~13–15°.

**Formula (simplified)**:
```
Heliacal Rising: Sun altitude ≈ −(arcus_visionis) and star is on eastern horizon at civil twilight
Heliacal Setting: last evening when star sets after the Sun while Sun is still above −(arcus_visionis)
```

---

### 7. Annual Profections  `P2` — new `moira/profections.py`

**What it is**: One of the simplest and most powerful Hellenistic timing techniques. Each year of life, the chart "profects" to the next house — Year 0–1 = 1st house, Year 1–2 = 2nd house, ..., Year 12–13 = 1st house again. The profected house lord becomes the "Lord of the Year" and is activated.

**Formula**:
```
profected_house = (age_in_years mod 12) + 1
profected_asc   = natal_asc + (age_in_years × 30°)  [tropical]
lord_of_year    = domicile ruler of the profected house sign
```

**What to return**: profected Ascendant degree, profected house number, lord of the year, and which natal planets are activated (conjunct the profected Ascendant within orb).

---

### 8. Firdaria  `P2` — new `moira/profections.py` or `moira/timelords.py`

**What it is**: A Persian/Arabic time-lord system adopted from Hellenistic sources. Divides life into major planetary periods. For a diurnal birth the sequence is Sun (10y) → Venus (8y) → Mercury (13y) → Moon (9y) → Saturn (11y) → Jupiter (12y) → Mars (7y) → then North Node (3y) → South Node (2y) → repeat. Each major period is divided into 7 sub-periods.

**Is-day determination**: Same as the Lots — `is_day = sun_longitude > asc_longitude` (considering horizon, not simply Sun above 0° Aries). The precise test uses the Sun's house position.

---

### 9. Vimshottari Dasha  `P2` — new `moira/dasha.py`

**What it is**: The primary Vedic predictive system. 120-year cycle divided among 9 planets (grahas) in a fixed sequence: Ketu (7y) → Venus (20y) → Sun (6y) → Moon (10y) → Mars (7y) → Rahu (18y) → Jupiter (16y) → Saturn (19y) → Mercury (17y). The starting point is determined by the Moon's nakshatra at birth.

**Nakshatras**: 27 lunar mansions of 13°20' each. Moon's nakshatra determines which planetary lord starts the dasha and how far into it the native was born.

**Formula**:
```
nakshatra_index = floor(moon_sidereal_longitude / (360/27))
nakshatra_lord  = NAKSHATRA_LORDS[nakshatra_index]
elapsed_fraction = (moon_sidereal_longitude mod 13.333°) / 13.333°
remaining_years  = (1 - elapsed_fraction) × dasha_years[nakshatra_lord]
```

**Implementation note**: Requires `tropical_to_sidereal()` from `sidereal.py` (Lahiri ayanamsa for standard KP/traditional use).

---

### 10. Nakshatra Positions  `P2` — `moira/sidereal.py`

**What it is**: The 27 (or 28 with Abhijit) lunar mansions used in Vedic astrology. Each spans 13°20' of the sidereal zodiac. Needed for Dasha calculation and Vedic interpretation.

**Formula**:
```
sidereal_lon = tropical_to_sidereal(lon, jd, Ayanamsa.LAHIRI)
nakshatra_index = int(sidereal_lon / (360/27))
pada = int((sidereal_lon mod 13.333°) / 3.333°) + 1   # 1–4
```

---

### 11. Zodiacal Releasing  `P3` — new `moira/timelords.py`

**What it is**: A Hellenistic time-lord system from Vettius Valens (*Anthology*, 2nd century AD). Periods are derived from the Lot of Fortune (or Spirit) and release through the zodiac. Each sign corresponds to a period length based on its "minor years" (the Ptolemaic minor years: Aries 15, Taurus 8, Gemini 20 …). Each major period contains sub-periods, then sub-sub-periods.

**Reference**: Demetra George, *Ancient Astrology in Theory and Practice*, Vol. II; Chris Brennan, *Hellenistic Astrology* Ch.10.

---

### 12. Hyleg and Alcocoden (Longevity Technique)  `P3` — new `moira/longevity.py`

**What it is**: Medieval Arabic/Hellenistic longevity calculation. The Hyleg ("giver of life") is the sect light or its substitute under specific conditions. The Alcocoden ("giver of years") is the planet with the most dignities at the Hyleg's degree. The Alcocoden grants its planetary years (major, middle, or minor) to estimate lifespan.

---

### 13. Hayz / In Sect Conditions  `P3` — `moira/dignities.py`

**What it is**: A planet is in hayz when it is in its preferred sect (day/night), in its preferred half of the chart (above/below horizon), and in a sign of its preferred gender (masculine/feminine). It is an essential dignity in Hellenistic and medieval astrology.

**Sect**:
- Diurnal planets (Sun, Jupiter, Saturn): prefer day charts, above-horizon placement, masculine signs
- Nocturnal planets (Moon, Venus, Mars): prefer night charts, below-horizon placement, feminine signs
- Mercury: changes sect based on whether it rises before or after the Sun

---

### 14. Astrocartography / ACG Lines  `P3` — new `moira/astrocartography.py`

**What it is**: For each planet, computes the geographic lines where that planet would be on the MC, IC, ASC, or DSC at the birth time. These four lines per planet = 40 lines across the globe for a standard chart. Jim Lewis's *Astro*Carto*Graphy* (1976) is the foundational work; today's AstroMaps are in every major software.

**Formula** (MC line for planet P):
```
MC line: all longitudes where ARMC = RA_P  →  geographic longitude = RA_P − GMST
ASC/DSC line: solve for geographic latitude where sin(lat) = sin(dec_P)/cos(ARMC−RA_P)/tan(ε) ... [full formula Meeus]
```

---

### 15. Local Space Chart  `P3` — new `moira/local_space.py`

**What it is**: Plots planets by their azimuth and altitude from the observer's location rather than by ecliptic longitude. Lines extend from the observer outward across the Earth's surface in the direction of each planet. Used for relocation and Feng Shui-adjacent work.

---

### 16. 90° Dial / Uranian Midpoint Trees  `P3` — `moira/midpoints.py`

**What it is**: The Hamburg School's primary tool. All longitudes are mapped onto a 90° dial (multiply by 4 mod 90), collapsing all four quadrants onto one. Midpoints that are invisible on the 360° wheel suddenly cluster. The "midpoint tree" lists all bodies equidistant from a focus point on the dial.

---

---

## Part II — Mathematical Accuracy Improvements

These are areas where Moira's current implementation is correct but could be made more rigorous.

---

### A. Ayanamsa: Linear Precession Model vs. Full P03  `HIGH IMPACT`

**Current state**: `sidereal.py` uses a single fixed `_AYANAMSA_AT_J2000` offset plus `general_precession_in_longitude()` (which is the P03 general precession polynomial). This is accurate to within ~1" for recent centuries.

**Issue**: The "true" ayanamsa of star-anchored systems (Lahiri, True Chitrapaksha, True Revati) should be computed from the actual star's position with proper motion applied, not from a fixed epoch offset. The Lahiri Commission's definition anchors the ayanamsa to the star Spica (α Virginis) being at exactly 0°00'00" sidereal Virgo. As Spica has proper motion (+0.05"/yr in RA, −0.03"/yr in Dec), the ayanamsa drifts slightly from a purely precessional model over centuries.

**Fix**: For `TRUE_CHITRAPAKSHA` and `LAHIRI` in particular, use the actual computed position of Spica (from `fixed_stars.py` with proper motion) to define 0° Virgo sidereal, then compute the ayanamsa as `tropical_lon(Spica) − 180°`. This matches Swiss Ephemeris's "true" star-anchored ayanamsa computation.

---

### B. Vertex Calculation  `HIGH IMPACT`

**Current state**: `HouseCusps.vertex` is always `None` — never calculated.

**Formula** (exact, from Meeus *Astronomical Algorithms*, §24):
```python
# Vertex is the western intersection of the prime vertical with the ecliptic
# Equivalent: ASC formula with latitude negated AND ARMC shifted +90°
vertex = _asc_from_armc(armc=(armc + 90.0) % 360.0, obliquity=obliquity, lat=-lat)
anti_vertex = (vertex + 180.0) % 360.0
```
This one-liner fills the always-null field with a geometrically correct value.

---

### C. Topocentric Correction: Full WGS-84 vs. Simplified Radius  `MEDIUM IMPACT`

**Current state** (`corrections.py`): Uses the correct WGS-84 flattening constants but applies a simplified radius formula that slightly conflates geodetic and geocentric latitude in the C/S reduction.

**Standard formula** (Meeus §11, USNO Circular 179):
```python
# C and S from geodetic latitude φ (geodetic, not geocentric)
phi = geodetic_lat_rad
C = 1.0 / sqrt(cos(phi)**2 + (1-f)**2 * sin(phi)**2)
S = (1-f)**2 * C
# Observer position components
rho_sin_phi_prime = S * sin(phi) + (h_km / a_km) * sin(phi)
rho_cos_phi_prime = C * cos(phi) + (h_km / a_km) * cos(phi)
```
where `a_km = 6378.137` (WGS-84 equatorial radius) and `h_km` is elevation. The current implementation already does this correctly — but the elevation term should use `a_km` as denominator, not add raw `h` to the spherical radius.

**Actual fix**: Replace `r_km = EARTH_RADIUS_KM + elevation_m / 1000.0` with the proper separation of `rho_sin` and `rho_cos` components using the equatorial radius as the scale factor. Impact is <0.001" for typical elevations but matters for mountain observatories (>3000m).

---

### D. Apparent Sidereal Time: Full IAU 2006 GAST  `MEDIUM IMPACT`

**Current state** (`julian.py` — `apparent_sidereal_time`): Computes GAST as GMST + equation of the equinoxes (Δψ·cos ε). This is the IAU 1982 formula, accurate to ~0.1".

**IAU 2006 improvement**: The full Capitaine et al. (2003) GAST formula adds the "complementary terms" (CT) — a series of periodic terms in the fundamental arguments that account for the effect of nutation on the origin of the equinox. The correction reaches up to ~0.04" peak-to-peak.

```
GAST = θ_ERA + ψ_A·cos(ε_A) + Σ(periodic_CT_terms)
```
where `θ_ERA` is the Earth Rotation Angle (exact linear function of UT1). For sub-arcsecond ephemeris work, this is the standard.

---

### E. Delta-T: IERS Bulletins vs. Polynomial Extrapolation  `MEDIUM IMPACT`

**Current state**: Uses a piecewise polynomial fit (Espenak & Meeus 2006), with an observed lookup table from 1955–2025. This is accurate for historical dates.

**Issue**: The near-future polynomial `69.36 + 0.08·t + 0.003·t²` (for 2020–2050) is a rough extrapolation. The IERS issues Bulletin A weekly with predicted ΔT values for the next year, and Bulletin B monthly with definitive values.

**Recommendation**: Add a `_DELTA_T_IERS` table that can be updated from IERS Bulletin B data (freely downloadable at `maia.usno.navy.mil/ser7/finals2000A.all`). The current code architecture supports this — just extend `_DELTA_T_OBSERVED_5Y` with finer-grained recent data. For the current epoch (2024–2026), ΔT ≈ 69.2s, not the ~69.4s the polynomial gives.

---

### F. Lunar Parallax in Aspects  `MEDIUM IMPACT`

**Current state**: When `observer_lat/lon` is supplied, `planet_at()` applies topocentric correction to the Moon's *position* correctly. However, `find_aspects()` and all aspect functions accept raw longitudes — they do not distinguish topocentric vs. geocentric Moon. If the caller passes topocentric Moon longitude into `find_aspects`, aspects are topocentric-correct. But the `Moira.chart()` output needs to make this explicit.

**Recommendation**: `Chart.positions` should tag each body with `is_topocentric: bool` so consumers know whether the Moon longitude already has parallax applied.

---

### G. Fixed Star Proper Motion: Epoch and Reference Frame  `LOW IMPACT`

**Current state** (`fixed_stars.py`): Applies proper motion as a simple linear extrapolation from J2000.0. This is standard and correct for most purposes.

**Rigor improvement**: Proper motion in right ascension is tabulated as `μ_α* = μ_α · cos(δ)` (the "reduced" form) in all modern catalogs (Hipparcos, Tycho-2, Gaia DR3). If the catalog stores the unreduced `μ_α`, the cosine of declination must be applied. Gaia DR3 also includes **parallax** for bright stars (Sirius: π = 379 mas → 8.6 ly), meaning the star's distance changes the apparent position by a tiny but computable amount for extreme precision.

**Also**: Stars brighter than ~6 mag should use the Hipparcos epoch (J1991.25), not J2000.0, as their proper motion reference epoch. The current implementation assumes all stars are epoch J2000.0.

---

### H. Obliquity: IAU 2006 P03 vs. Low-Degree Polynomial  `LOW IMPACT`

**Current state** (`obliquity.py`): Uses Laskar (1986) / IAU 1980 polynomial for mean obliquity — accurate to about ±1" over ±1000 years.

**IAU 2006 standard**: The P03 polynomial (Capitaine, Wallace & Chapront 2003) is:
```
ε_A = 84381.406  −  46.836769·T  −  0.0001831·T²  +  0.00200340·T³
    −  0.000000576·T⁴  −  0.0000000434·T⁵   [arcseconds, T in Julian centuries from J2000]
```
`precession.py` already has `mean_obliquity_p03()` — but `obliquity.py::mean_obliquity()` uses a different, older polynomial. **These two functions should be unified** to use the same P03 formula throughout.

---

### I. Nutation: Δψ Longitude Term in House Calculations  `LOW IMPACT`

**Current state**: `houses.py` calls `true_obliquity()` (which includes Δε) and `nutation()` for Δψ, then passes both to ARMC/Sidereal Time. The chain is correct in principle.

**Subtle issue**: The `apparent_sidereal_time()` in `julian.py` uses `dpsi * cos(eps)` as the equation of the equinoxes. However, the full equation of the equinoxes at the IAU 2000A level is:
```
EE = Δψ · cos(ε_A) + 0.00264096" · sin(Ω) + 0.00006352" · sin(2Ω) + ...
```
(Capitaine & Gontier 1993; IERS Conventions 2010 §5.4). The periodic correction terms sum to at most ~0.002" — negligible for most work, but documenting it is valuable.

---

### J. Aspects: Speed-Weighted Applying/Separating  `LOW IMPACT`

**Current state** (`aspects.py`): The `_applying()` function correctly detects applying/separating from the relative speed and angular separation. However, it does not account for **stationary planets** (speed ≈ 0) or for the fact that a planet just past station may be technically separating but at near-zero speed (functionally still "at peak intensity").

**Recommendation**: Add a `STATIONARY` state to `AspectData.applying` (currently `bool | None`). When `|speed| < 0.01°/day`, the planet is stationary and neither applying nor separating in any meaningful sense. This matches Swiss Ephemeris's behavior.

---

---

## Part III — Summary Priority Table

| # | Feature / Improvement | Type | Priority | New file? |
|---|---|---|---|---|
| 1 | Vertex / Anti-Vertex | Feature | P1 | no — fix `houses.py` |
| 2 | Antiscia & Contra-antiscia | Feature | P1 | new `antiscia.py` |
| 3 | Parallel & Contra-parallel aspects | Feature | P1 | extend `aspects.py` |
| 4 | Parans (fixed star parans) | Feature | P1 | new `parans.py` |
| 5 | Generic planet return | Feature | P1 | extend `transits.py` |
| 6 | Heliacal rising/setting | Feature | P2 | extend `fixed_stars.py` |
| 7 | Annual profections | Feature | P2 | new `profections.py` |
| 8 | Firdaria | Feature | P2 | new `timelords.py` |
| 9 | Vimshottari dasha | Feature | P2 | new `dasha.py` |
| 10 | Nakshatra positions | Feature | P2 | extend `sidereal.py` |
| 11 | Zodiacal releasing | Feature | P3 | new `timelords.py` |
| 12 | Hyleg / Alcocoden | Feature | P3 | new `longevity.py` |
| 13 | Hayz / In sect | Feature | P3 | extend `dignities.py` |
| 14 | Astrocartography / ACG | Feature | P3 | new `astrocartography.py` |
| 15 | Local space chart | Feature | P3 | new `local_space.py` |
| 16 | 90° dial / Uranian | Feature | P3 | extend `midpoints.py` |
| A | Ayanamsa: star-anchored Lahiri | Math | HIGH | fix `sidereal.py` |
| B | Vertex formula (fill the null) | Math | HIGH | fix `houses.py` |
| C | Topocentric: WGS-84 elevation | Math | MED | fix `corrections.py` |
| D | Apparent sidereal time: IAU 2006 GAST | Math | MED | fix `julian.py` |
| E | Delta-T: IERS Bulletin data | Math | MED | fix `julian.py` |
| F | Topocentric tag on Chart positions | Math | MED | fix `__init__.py` |
| G | Fixed star proper motion: epoch + parallax | Math | LOW | fix `fixed_stars.py` |
| H | Obliquity: unify P03 throughout | Math | LOW | fix `obliquity.py` |
| I | Equation of the equinoxes: full periodic | Math | LOW | fix `julian.py` |
| J | Stationary aspect state | Math | LOW | fix `aspects.py` |

---

## Part IV — What Moira Already Has That Swiss Ephemeris Lacks

For reference, capabilities where Moira exceeds the standard Swiss Ephemeris distribution:

- **IAU 2000A full nutation** (1365-term series) — SwissEph uses a truncated version in its default mode
- **Hermetic decans** with all 36 Egyptian decan ruling stars and their computed positions
- **Centaur SPK kernels** (Pholus, Chariklo, Asbolus, Hylonome) — SwissEph has fewer
- **TNO kernel support** (Quaoar, Varuna, Ixion, Orcus) via SPK Type 13
- **499 Arabic parts / Lots** — SwissEph ships far fewer
- **Primary directions** (Placidus semi-arc, mundane) — SwissEph requires the `swe_dirhut()` C function
- **Hermetic / Ptolemaic 36-decan hour system** with sunrise/sunset computation
- **Tertiary progressions** alongside secondary and solar arc
- **Relativistic aberration and deflection** applied uniformly to all bodies
- **Constellations directory** (34 constellation star groups)
- **Planetary hours** with full day/night cycle and decan hours
- **Royal stars**, **Behenian stars**, **Pleiades / Hyades** as named groups
- **Eclipse Saros classification** with heptagonal vertex labelling
