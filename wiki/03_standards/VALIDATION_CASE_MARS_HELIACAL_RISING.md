# Validation Case: Mars Heliacal Rising at Babylon (2024)

**Subject**: First morning visibility of Mars after solar conjunction  
**Substrate**: Moira `heliacal.planet_heliacal_rising` / JPL DE441  
**Oracle**: JPL Horizons DE441 geocentric RA/Dec + independent altitude computation  
**Criterion layer**: Schoch/Ptolemy arcus visionis table — **+1 to +2 mag branch (11°)**  
**Status**: VERIFIED — exact agreement, Moira and Horizons both predict 2024-Jan-07  
**Verified**: 2026-04-10

---

## 1. What is being tested

`moira.heliacal.planet_heliacal_rising(Body.MARS, jd_start, lat, lon)` predicts the
first morning when Mars is geometrically observable after solar conjunction.

This case deliberately targets a different region of the arcus visionis table than
the companion Venus case. Venus near heliacal rising is magnitude −4, placing it in
the 5° solar-depression bracket. Mars near heliacal rising is magnitude +1.3,
placing it in the **11° bracket** — requiring the Sun to be nearly halfway to
nautical twilight before Mars is detectable. The deeper twilight demand makes
Mars a more exacting test of the solver's threshold logic.

The test targets the **2024 Mars morning apparition** at Babylon (32.55°N, 44.42°E):

- Solar conjunction: 2023-Nov-18 (Mars ecliptic longitude ≈ 235.6°)
- Search start: 2023-Nov-20
- Observer site: Babylon (ancient mean site, sea-level equivalent assumed)

---

## 2. Moira's criterion

The default `VisibilityPolicy` uses the Schoch/Ptolemy stepped arcus visionis table.
For Mars at +1.3 magnitude:

| Apparent mag | Base solar depression |
|---|---|
| ... | ... |
| 0 to +1 | 10.0° |
| **+1 to +2** | **11.0°** |
| +2 to +3 | 12.0° |
| ... | ... |

Mars magnitude at this apparition remains **+1.3 to +1.4** throughout the search
window (Dec 2023 – Jan 2024), placing it solidly in the 11° bracket with no
table-boundary crossings. This is a clean, single-plateau criterion case.

With the default model (Bortle-3, k = 0.25, lim_mag = 6.5), the adjustments
to the base value are:

- `(6.5 − 6.5) × 0.8 = 0` (limiting-magnitude correction)
- `(0.25 − 0.25) × 4.0 = 0` (extinction correction)

arcus visionis = **11.0° exactly** for every day in the search window.

---

## 3. Moira's prediction

```
planet_heliacal_rising(Body.MARS, JD(2023-Nov-20), lat=32.55, lon=44.42)
```

| Field | Value |
|---|---|
| First visible date | **2024-Jan-07** |
| UT of visibility window | 03:13 |
| Planet altitude | +0.12° |
| Sun altitude at criterion | −11.00° |
| Solar elongation | −14.52° |
| Mars apparent magnitude | +1.34 |
| JD_UT | 2460316.633691 |

Mars rises just barely above the geometric horizon at the moment the Sun reaches
its arcus-visionis depression. The progression is slow — Mars gains only ~0.15° in
altitude per day at the Sun=-11° moment, making this a precision test of the
solver's threshold detection.

---

## 4. Independent Horizons check

### Method

Identical to the Venus case (see [`VALIDATION_CASE_VENUS_HELIACAL_RISING.md`](VALIDATION_CASE_VENUS_HELIACAL_RISING.md)):

1. Query JPL Horizons DE441 for geocentric RA/Dec of Mars (body 499) and the
   Sun (body 10) at 10-minute intervals: 2023-Dec-20 00:00 through 2024-Jan-25 06:00 UT.
2. Restrict to the Babylon pre-dawn window (UT 01:30–05:00) to exclude the
   corresponding evening Sun=-11° crossing (~14–16h UT at Babylon in January).
3. Compute GMST → local sidereal time → altitude via spherical trigonometry.
4. Interpolate the morning crossing of Sun = −11°.
5. Record Mars altitude at that moment. First morning Mars alt > 0° = event date.

No Moira code is used in the altitude computation.

Script: `tmp/mars_heliacal_horizons.py`

### Criterion A — matching Moira's arcus visionis (Sun = −11°, alt > 0°)

Per-day Mars altitude at Sun = −11° for Dec-20 to Jan-25:

| Date | Twilight UT | Mars alt |
|---|---|---|
| Dec-20 | 3.083h | −3.04° |
| Dec-25 | 3.124h | −2.05° |
| Dec-31 | 3.161h | −0.97° |
| Jan-04 | 3.178h | −0.32° |
| Jan-05 | 3.181h | −0.17° |
| Jan-06 | 3.184h | −0.01° |
| **Jan-07** | **3.186h** | **+0.14°** |
| Jan-08 | 3.188h | +0.28° |
| Jan-10 | 3.191h | +0.57° |
| Jan-15 | 3.189h | +1.22° |
| Jan-20 | 3.176h | +1.81° |
| Jan-25 | 3.150h | +2.33° |

**Horizons-derived heliacal rising: 2024-Jan-07.**

The twilight UT column (3.18–3.19h) matches Moira's predicted event time (3.21h)
to within the 10-minute Horizons interpolation step. Mars altitude at the
criterion crossing rises at ~0.13°/day — a slow, gradual emergence confirming
that the solver is correctly resolving a precise geometric threshold.

### Criterion B — astronomical twilight (Sun = −18°, alt ≥ 5°)

| Date | Mars alt at Sun=−18° |
|---|---|
| Dec-20 through Jan-25 | −9.8° → −4.1° |

Mars remains 4–10° below the geometric horizon at astronomical twilight throughout
the entire search window. It never becomes visible under this criterion.

This result has a direct physical interpretation: Mars at elongation 14.5° in a
faint mag +1.34 state is simply too close to the Sun and too dim to be seen before
the sky is fully dark. The arcus visionis model (Sun = −11°) correctly identifies
the early twilight window as the only viable detection opportunity.

---

## 5. Arcus visionis table coverage: Venus vs. Mars

| Planet | Mag at event | av bracket | Solar dep | Wiki doc |
|---|---|---|---|---|
| Venus (2023 Aug) | −4.00 | ≤ −4.0 | 5° | [`VALIDATION_CASE_VENUS_HELIACAL_RISING.md`](VALIDATION_CASE_VENUS_HELIACAL_RISING.md) |
| Mars (2024 Jan) | +1.34 | +1 to +2 | **11°** | This document |
| Mars (2026 Apr) | +1.24 | +1 to +2 | 11° | [`VALIDATION_CASE_MARS_HELIACAL_RISING_2026.md`](VALIDATION_CASE_MARS_HELIACAL_RISING_2026.md) |

Venus tests the shallow-twilight end (av=5°); Mars tests the deep-twilight end (av=11°).
The +1 to +2 magnitude branch is confirmed by two independent Mars apparitions separated
by 2.5 years and 7° of event elongation.

---

## 6. What this validates

- `planet_heliacal_rising` correctly locates the first morning where Mars
  altitude exceeds the geometric horizon at the 11° arcus visionis depression.
- The arcus visionis table is applied consistently in the +1 to +2 magnitude
  bracket with no table-boundary effects.
- The positional substrate for an outer planet (Mars, NAIF body 499)
  in the months following solar conjunction is geometrically consistent with
  JPL Horizons DE441 geometry to within the 10-minute interpolation step.
- The solver handles the slow outer-planet elongation growth correctly
  (Mars gains elongation ~0.5°/day vs. Venus's ~3°/day near inferior conjunction).

---

## 7. What this does not validate

- The criterion against physical observation. This is a criterion-consistency
  check, not an observation-based one.
- Bodies other than Mars and Venus, or apparitions at other latitudes.
- Modern Mars apparitions near opposition (when Mars is bright, magnitude
  may cross into the +0 to +1 or even −1 to 0 bracket — untested here).

---

## 8. Relationship to the Venus validation

The companion document on the [Venus heliacal rising](VALIDATION_CASE_VENUS_HELIACAL_RISING.md)
covers the bright-planet, shallow-twilight branch of the table (av = 5°) and
includes a phase-dependent magnitude-boundary diagnostic.

This document covers the faint outer-planet, deep-twilight branch (av = 11°)
and confirms the solver's behavior when Mars altitude gains are slow and the
threshold is deep in nautical twilight.

Both cases confirm Moira's arcus visionis implementation against independent
Horizons geometry. Neither constitutes observational validation against historical
or modern observer records.

---

## 9. Verification scripts

`tmp/mars_heliacal_horizons.py` — queries Horizons live, computes local altitude
at Babylon, and prints the per-day Mars altitude table for both criteria (2024 apparition).

`tmp/mars_heliacal_2026.py` — same method for the 2026 apparition
(see [`VALIDATION_CASE_MARS_HELIACAL_RISING_2026.md`](VALIDATION_CASE_MARS_HELIACAL_RISING_2026.md)).

Run with:
```
.venv/Scripts/python.exe tmp/mars_heliacal_horizons.py
```
