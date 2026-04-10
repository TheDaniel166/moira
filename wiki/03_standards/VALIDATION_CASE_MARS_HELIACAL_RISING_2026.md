# Validation Case: Mars Heliacal Rising at Babylon (2026)

**Subject**: First morning visibility of Mars after solar conjunction  
**Substrate**: Moira `heliacal.planet_heliacal_rising` / JPL DE441  
**Oracle**: JPL Horizons DE441 geocentric RA/Dec + independent altitude computation  
**Criterion layer**: Schoch/Ptolemy arcus visionis table — **+1 to +2 mag branch (11°)**  
**Status**: VERIFIED — exact agreement, Moira and Horizons both predict 2026-Apr-17  
**Verified**: 2026-04-10

---

## 1. What is being tested

The same solver and the same arcus visionis branch as the [2024 Mars case](VALIDATION_CASE_MARS_HELIACAL_RISING.md),
but with a different conjunction and a different elongation geometry. This tests
that the av=11° result is stable across separate apparitions of Mars, not an
artifact of one particular geometry.

Key geometric contrast with the 2024 case:

| | 2024 case | 2026 case |
|---|---|---|
| Conjunction date | 2023-Nov-18 | **2026-Jan-09** |
| Predicted heliacal rising | 2024-Jan-07 | **2026-Apr-17** |
| Days post-conjunction | ~50 | ~97 |
| Elongation at event | −14.52° | **−21.52°** |
| Mars magnitude at event | +1.34 | +1.24 |

Mars gains elongation slowly after conjunction (~0.5°/day). The 2026 case waits
longer, reaches a larger elongation, and finds Mars at slightly higher altitude at
the threshold moment. Both cases sit in the same av=11° table bracket.

---

## 2. Moira's criterion

Identical to the 2024 case. The Schoch/Ptolemy stepped table assigns:

| Apparent mag | Base solar depression |
|---|---|
| +1 to +2 | **11.0°** |

Mars magnitude at this apparition is **+1.24**, placing it in the same bracket.
The adjustments from the default `VisibilityPolicy` (Bortle-3, k=0.25, lim_mag=6.5)
are again zero, so arcus visionis = **11.0° exactly** throughout the search window.

---

## 3. Moira's prediction

```
planet_heliacal_rising(Body.MARS, JD(2026-Jan-20), lat=32.55, lon=44.42)
```

| Field | Value |
|---|---|
| First visible date | **2026-Apr-17** |
| UT of visibility window | 01:40 |
| Planet altitude | +0.07° |
| Sun altitude at criterion | −11.00° |
| Solar elongation | −21.52° |
| Mars apparent magnitude | +1.24 |
| JD_UT | 2461147.5699 |

Mars at +0.07° is barely above the geometric horizon at event — even more marginal
than the 2024 case (+0.12°). At ~0.12°/day altitude gain, this is again a precision
threshold test.

---

## 4. Independent Horizons check

### Method

Identical to the 2024 case (see [`VALIDATION_CASE_MARS_HELIACAL_RISING.md`](VALIDATION_CASE_MARS_HELIACAL_RISING.md)):

1. Query JPL Horizons DE441 for geocentric RA/Dec of Mars (body 499) and the
   Sun (body 10) at 10-minute intervals: 2026-Feb-15 01:00 through 2026-May-15 05:00 UT.
2. Restrict to the Babylon pre-dawn window (UT 01:00–05:00) to exclude the
   evening Sun=−11° crossing.
3. Compute GMST → local sidereal time → altitude via spherical trigonometry.
4. Interpolate the morning crossing of Sun = −11°.
5. Record Mars altitude at that moment. First morning Mars alt > 0° = event date.

Script: `tmp/mars_heliacal_2026.py`

### Criterion A — matching Moira's arcus visionis (Sun = −11°, alt > 0°)

Selected per-day Mars altitude at Sun = −11° across the apparition:

| Date | Twilight UT | Mars alt |
|---|---|---|
| Feb-15 | 2.918h | −6.34° |
| Mar-01 | 2.680h | −4.88° |
| Mar-15 | 2.395h | −3.52° |
| Apr-01 | 2.016h | −1.80° |
| Apr-10 | 1.813h | −0.80° |
| Apr-14 | 1.725h | −0.32° |
| Apr-15 | 1.703h | −0.19° |
| Apr-16 | 1.682h | −0.07° |
| **Apr-17** | **1.660h** | **+0.06°** |
| Apr-18 | 1.639h | +0.19° |
| Apr-20 | 1.596h | +0.45° |
| Apr-25 | 1.494h | +1.15° |
| May-01 | 1.377h | +2.06° |
| May-13 | 1.175h | +4.18° |

**Horizons-derived heliacal rising: 2026-Apr-17.**

The twilight UT column shows the Babylon pre-dawn moving earlier as spring progresses
(sunrise advances). Moira's predicted UT of 01:40 (1.677h) agrees with Horizons'
1.660h to within 1 minute — consistent with the 10-minute interpolation step.

### Criterion B — astronomical twilight (Sun = −18°, alt ≥ 5°)

| Date | Mars alt at Sun=−18° |
|---|---|
| Feb-15 | −13.19° |
| Mar-15 | −10.52° |
| Apr-01 | −9.05° |
| Apr-12 | −8.02° |
| May-13 (end of table) | not reached |

Mars never approaches 5° above the geometric horizon at astronomical twilight across
the entire Feb–May search window. The elongation of −21.5° at event is still too
small for Mars to be well-placed at the darker threshold.

Criterion B returns **None** — consistent with the 2024 case.

---

## 5. Elongation geometry comparison

The 2026 case provides a useful cross-check of the outer-planet slow-elongation model:

| Date | Elongation | Mars alt at Sun=−11° |
|---|---|---|
| Feb-15 (Horizons) | ~5° | −6.3° |
| Apr-01 | ~15° | −1.8° |
| **Apr-17 (event)** | **~21.5°** | **+0.06°** |
| Apr-25 | ~24° | +1.2° |
| May-13 | ~31° | +4.2° |

The altitude grows steadily from deep negative in February to positive in April.
The arcus visionis solver must integrate this gradual gain correctly; neither a
coarse date-stepping approach nor an early-termination heuristic would find
the threshold cleanly. The exact match confirms that the solver's numerical
search is resolving the Mars emergence with day-level precision across a
97-day post-conjunction window.

---

## 6. What this validates

- `planet_heliacal_rising` returns the correct date for a separate Mars apparition
  with a different elongation geometry and a longer post-conjunction latency.
- The av=11° criterion is applied consistently between the 2024 and 2026 apparitions.
- The positional substrate for Mars at body 499 in DE441 is geometrically consistent
  with Horizons across two separate apparition windows.
- The solver does not fail for a long search window (~97 days post-conjunction)
  or for a marginal event altitude (+0.07°).

---

## 7. What this does not validate

- Other av table branches (the +0 to +1 or brighter Mars brackets are untested;
  they require Mars near opposition, magnitude −2 to 0).
- Observers at latitudes other than Babylon (32.55°N).
- Acronychal rising or heliacal setting for Mars.
- Observational correspondence with ancient or modern records.

---

## 8. Relationship to the 2024 Mars case

| | [2024 case](VALIDATION_CASE_MARS_HELIACAL_RISING.md) | This document |
|---|---|---|
| Conjunction | 2023-Nov-18 | 2026-Jan-09 |
| Event date | 2024-Jan-07 | **2026-Apr-17** |
| Post-conjunction days | ~50 | ~97 |
| Elongation | −14.5° | −21.5° |
| Mars alt at event | +0.12° | +0.07° |
| av applied | 11.0° | 11.0° |
| Match | ✓ exact | ✓ **exact** |

Both cases confirm the same branch of the arcus visionis table, from different
geometric configurations and across a 2.5-year span. The solver's threshold
detection is stable.

---

## 9. Arcus visionis table coverage: three confirmed cases

| Planet | Mag at event | av bracket | Solar dep | Wiki doc |
|---|---|---|---|---|
| Venus (2023 Aug) | −4.00 | ≤ −4.0 | 5° | [`VALIDATION_CASE_VENUS_HELIACAL_RISING.md`](VALIDATION_CASE_VENUS_HELIACAL_RISING.md) |
| Mars (2024 Jan) | +1.34 | +1 to +2 | 11° | [`VALIDATION_CASE_MARS_HELIACAL_RISING.md`](VALIDATION_CASE_MARS_HELIACAL_RISING.md) |
| Mars (2026 Apr) | +1.24 | +1 to +2 | **11°** | This document |

The +1 to +2 mag branch is now confirmed by two independent Mars apparitions separated
by 2.5 years and 7° of event elongation. The 5° (Venus) and 11° (Mars) table branches
are verified; the intermediate branches (6°, 7°, 8°, 9°, 10°) remain untested.

---

## 10. Verification script

`tmp/mars_heliacal_2026.py` — queries Horizons live, computes local altitude at
Babylon, and prints the per-day Mars altitude table for both criteria.

Run with:
```
.venv/Scripts/python.exe tmp/mars_heliacal_2026.py
```
