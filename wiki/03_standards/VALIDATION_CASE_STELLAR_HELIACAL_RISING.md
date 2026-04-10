# Validation Case: Stellar Heliacal Rising — Sirius and the Four Royal Stars (Babylon 2025)

**Subject**: First morning visibility (heliacal rising) of five fixed stars  
**Stars**: Sirius, Aldebaran, Regulus, Antares, Fomalhaut (classical Royal Stars + Sirius)  
**Substrate**: Moira `stars.heliacal_rising_event` / DE441 (Sun) / ICRS J2000 + Hipparcos proper motion (star)  
**Oracle**: astropy 7.2.0 / ERFA IAU 2006 — fully independent solar and stellar pipelines  
**Criterion layer**: Schoch/Ptolemy arcus visionis stepped table  
**Status**: VERIFIED — 20/20 exact across four years (2023–2026)  
**Verified**: 2026-03-25 (baseline); 2026-04-10 (multi-year + elongation guard fix)

---

## 1. What is being tested

`moira.stars.heliacal_rising_event(name, jd_start, lat, lon)` predicts the first morning
on which a fixed star becomes geometrically visible above the apparent horizon at the
moment of morning twilight (Sun at −av° geometric altitude).

This is a **completely separate code path** from the planetary heliacal solver tested in
the Mars and Venus cases. The stellar pipeline uses:

1. ICRS J2000 catalog coordinates (Hipparcos) + proper motion propagation (`_propagate_icrs_vector`)
2. Moira's own precession engine (`icrf_to_true_ecliptic` → ecliptic of date)
3. `ecliptic_to_equatorial` using `true_obliquity`
4. Local Apparent Sidereal Time via `apparent_sidereal_time` (GAST + longitude, IAU 2006)
5. Geometric altitude formula (no atmospheric refraction in the body-check path)
6. The solar twilight finder `_find_sun_at_alt` (DE441-based); morning-sky guard (`se >= 0.0` skip)

The oracle exercises an entirely separate coordinate chain using only astropy/ERFA:

1. Same Hipparcos ICRS J2000 catalog inputs
2. `astropy SkyCoord.apply_space_motion()` for proper motion to epoch
3. ERFA IAU 2006 precession/nutation via astropy's `AltAz` transform
4. `pressure=0` to suppress refraction (geometric altitude matching Moira's convention)
5. `get_body('sun', time, BABYLON)` with ERFA full apparent solar position for twilight

**The two pipelines share only the raw Hipparcos catalog coordinates.**

---

## 2. Observer and epoch

- **Site**: Babylon — 32.55°N, 44.42°E, height 0 m  
- **Epoch**: 2025 apparitions (modern scientific validation)  
- **Horizon threshold**: geometric altitude −0.5667° = apparent altitude 0° (standard refraction 34′)

---

## 3. Arcus visionis assignments

From Moira's `_default_arcus_for_star()` (Schoch/Ptolemy stepped table):

| Star | HIP | V mag | Mag branch | av (°) |
|------|-----|-------|-----------|--------|
| Sirius | 32349 | −1.46 | ≤ −1.0 | **7.5** |
| Aldebaran | 21421 | +0.86 | ≤ +1.0 | **10.0** |
| Regulus | 49669 | +1.40 | ≤ +2.0 | **11.0** |
| Antares | 80763 | +0.91 | ≤ +1.0 | **10.0** |
| Fomalhaut | 113368 | +1.16 | ≤ +2.0 | **11.0** |

---

## 4. Star catalog provenance

All five stars use SIMBAD/Hipparcos ICRS J2000 coordinates, PM, and parallax from
Moira's sovereign catalog. The astropy oracle uses identical catalog inputs (same HIP
RA/Dec/pm_ra_cosdec/pm_dec/parallax values), so any coordinate agreement or residual
reflects the comparison between **Moira's precession/nutation/GAST engine** and
**ERFA's IAU 2006 pipeline** given the same catalog source.

---

## 5. Elongation guard

Moira's `heliacal_rising_event` applies a morning-sky guard:

```python
se = _heliacal_signed_elongation(name, jd_midnight + 0.5)
if se >= 0.0:
    continue
```

`se = star.longitude − sun.longitude` (signed ecliptic elongation, degrees).  
The `se >= 0.0` check skips days when the star is in the evening sky (conjunction not yet
past, or star west of Sun). No further elongation magnitude filter is applied — the arcus
visionis altitude check (`star_alt > −0.5667°` at the `−av°` twilight) is the sole
visibility criterion.

**Prior behaviour (removed 2026-04-10):** An earlier version also skipped days with
`abs(se) < 12.0°`, a performance shortcut intended to avoid computing twilight near
conjunction. Because Regulus's arcus visionis (11°) is smaller than this fixed threshold,
the guard blocked the first valid rising day every year — a systematic +1-day offset
fully explained by the threshold, not a coordinate error. The guard was redundant with
the altitude check and has been removed from the rising solver. The setting solver retains
its own elongation logic, which is semantically distinct.

---

## 6. Validation results

Each oracle step finds the morning JD when `sun_geometric_altitude = −av°` (astropy
ERFA apparent Sun), then evaluates the star's geometric altitude at that JD.
First day with star altitude > −0.5667° is the oracle's heliacal rising date.

### 6.1 Sirius — av = 7.5°

| Date | Twilight UT | Astropy alt | Moira alt |
|------|-------------|-------------|-----------|
| 2025-Jul-26 | 1.622h | −7.943° | −7.949° |
| 2025-Jul-27 | 1.635h | −6.988° | −6.994° |
| 2025-Jul-28 | 1.647h | −6.035° | −6.041° |
| 2025-Jul-29 | 1.660h | −5.086° | −5.091° |
| 2025-Jul-30 | 1.672h | −4.137° | −4.143° |
| 2025-Jul-31 | 1.685h | −3.192° | −3.197° |
| 2025-Aug-01 | 1.698h | −2.249° | −2.255° |
| 2025-Aug-02 | 1.710h | −1.310° | −1.316° |
| **2025-Aug-03** | **1.723h** | **−0.375°** | **−0.381°** | ← FIRST visible |
| 2025-Aug-04 | 1.736h | +0.556° | +0.551° |

**Oracle: 2025-Aug-03 = Moira: 2025-Aug-03 → EXACT**  
Altitude agreement at event JD: 0.006° (astropy vs Moira)

---

### 6.2 Aldebaran — av = 10.0°

| Date | Twilight UT | Astropy alt | Moira alt |
|------|-------------|-------------|-----------|
| 2025-Jun-15 | 1.049h | −3.671° | −3.675° |
| 2025-Jun-16 | 1.050h | −2.887° | −2.891° |
| 2025-Jun-17 | 1.052h | −2.097° | −2.101° |
| 2025-Jun-18 | 1.054h | −1.298° | −1.302° |
| **2025-Jun-19** | **1.056h** | **−0.490°** | **−0.494°** | ← FIRST visible |
| 2025-Jun-20 | 1.059h | +0.327° | +0.322° |

**Oracle: 2025-Jun-19 = Moira: 2025-Jun-19 → EXACT**  
Altitude agreement at event JD: 0.004°

---

### 6.3 Regulus — av = 11.0°

| Date | Twilight UT | Astropy alt | Moira alt |
|------|-------------|-------------|----------|
| 2025-Sep-01 | 1.792h | −2.526° | −2.531° |
| 2025-Sep-02 | 1.804h | −1.572° | −1.577° |
| **2025-Sep-03** | **1.816h** | **−0.508°** | **−0.513°** | ← FIRST visible |
| 2025-Sep-04 | 1.828h | +0.446° | +0.440° |
| 2025-Sep-05 | 1.840h | +1.403° | +1.397° |

**Oracle: 2025-Sep-03 = Moira: 2025-Sep-03 → EXACT**  
Altitude agreement at event JD: 0.005° (astropy vs Moira)

Regulus's altitude on Sep-03 (−0.508°) clears the −0.5667° apparent-horizon threshold.
Prior to 2026-04-10 a 12° elongation magnitude guard in the rising solver blocked this
day (Sep-03 elongation −11.06° < 12°), producing a systematic +1-day offset. That guard
has been removed; see §5.

---

### 6.4 Antares — av = 10.0°

| Date | Twilight UT | Astropy alt | Moira alt |
|------|-------------|-------------|-----------|
| 2025-Dec-12 | 3.116h | −2.929° | −2.934° |
| 2025-Dec-13 | 3.127h | −2.090° | −2.096° |
| 2025-Dec-14 | 3.138h | −1.259° | −1.264° |
| **2025-Dec-15** | **3.149h** | **−0.437°** | **−0.442°** | ← FIRST visible |
| 2025-Dec-16 | 3.159h | +0.377° | +0.372° |

**Oracle: 2025-Dec-15 = Moira: 2025-Dec-15 → EXACT**  
Altitude agreement at event JD: 0.005°

---

### 6.5 Fomalhaut — av = 11.0°

| Date | Twilight UT | Astropy alt | Moira alt |
|------|-------------|-------------|-----------|
| 2025-Apr-15 | 1.715h | −1.586° | −1.589° |
| 2025-Apr-16 | 1.693h | −1.128° | −1.132° |
| 2025-Apr-17 | 1.671h | −0.671° | −0.674° |
| **2025-Apr-18** | **1.650h** | **−0.214°** | **−0.217°** | ← FIRST visible |
| 2025-Apr-19 | 1.629h | +0.242° | +0.239° |

**Oracle: 2025-Apr-18 = Moira: 2025-Apr-18 → EXACT**  
Altitude agreement at event JD: 0.003°

---

## 7. Summary table

| Star | HIP | V mag | av | Moira | Oracle | Match |
|------|-----|-------|----|-------|--------|-------|
| Sirius | 32349 | −1.46 | 7.5° | 2025-Aug-03 | 2025-Aug-03 | **EXACT** |
| Aldebaran | 21421 | +0.86 | 10.0° | 2025-Jun-19 | 2025-Jun-19 | **EXACT** |
| Regulus | 49669 | +1.40 | 11.0° | 2025-Sep-03 | 2025-Sep-03 | **EXACT** |
| Antares | 80763 | +0.91 | 10.0° | 2025-Dec-15 | 2025-Dec-15 | **EXACT** |
| Fomalhaut | 113368 | +1.16 | 11.0° | 2025-Apr-18 | 2025-Apr-18 | **EXACT** |

---

## 8. Oracle pipeline architecture

```
Catalog input (Hipparcos ICRS J2000):
  ra_j2000, dec_j2000, pmra, pmdec, parallax
            │
            ▼
  astropy SkyCoord (frame='icrs', obstime=J2000.0)
  → apply_space_motion(new_obstime = twilight_JD)
  → SkyCoord at epoch of observation
            │
            ▼ (each star)
  AltAz(obstime=t, location=BABYLON, pressure=0)     ← geometric altitude
  → .alt.deg

Sun twilight:
  For each date, bisect Sun geometric altitude = −av°
  using get_body('sun', t, BABYLON) → AltAz(pressure=0)
  (ERFA/SOFA full apparent position: precession + nutation + aberration)
  Convergence: 1-second (30 bisection iterations)
```

---

## 9. Prior oracle error: J2000 astrometric vs epoch-of-date apparent Sun

An earlier version of this validation script used JPL Horizons `QUANTITIES="1"` (which
returns J2000 ICRF **astrometric** RA/Dec — no precession, nutation, or annual aberration
applied) combined with an IAU 1982 GMST formula. This produced a systematic solar altitude
bias of approximately **+0.33°** at 2025 dates, caused by the ~26′ ecliptic-longitude
precession offset between J2000 and 2025.6. The resulting ~1.75-minute twilight time shift
was large enough to flip the date for rapidly-rising stars (Sirius, Aldebaran, Antares
rise at ~11°/hr near Babylon's horizon) but not for slowly-rising ones (Regulus, Fomalhaut).

The corrected oracle uses `astropy.coordinates.get_body('sun')`, which applies the full
apparent position pipeline (ERFA IAU 2006 precession/nutation/aberration), eliminating
this bias and producing results consistent with Moira's `sky_position_at()` pipeline.

---

## 10. Coordinate agreement between Moira and astropy/ERFA

At each twilight JD, the table above shows both astropy and Moira stellar altitude.
The consistent **0.003°–0.007° agreement** reflects the comparison of:

- Moira: ICRF J2000 → `_propagate_icrs_vector` proper motion → `icrf_to_true_ecliptic` (Moira
  precession) → `ecliptic_to_equatorial` (true obliquity) → IAU 2006 GAST altitude
- Oracle: ICRF J2000 → `apply_space_motion` → ERFA IAU 2006 precession/nutation → `AltAz`

The residual (∼0.005°) is consistent with expected numerical differences between
Moira's precession series and ERFA's full IAU 2006 model, and is well within any
practical observational margin.

---

## 11. Validation script

`tmp/stellar_heliacal_validation.py`

Key parameters:
- Observer: Babylon 32.55°N 44.42°E
- Time scale: UTC (both Moira and astropy)
- Morning window searched: UT 01:00 – 06:30 per day
- Solar twilight bisection: 30 iterations, 1-second convergence
- Star coordinate epoch: J2000.0 proper motion propagated to observation date
- Atmospheric refraction: suppressed (`pressure=0`) in both pipelines

---

## 12. Multi-year coverage — 2023, 2024, 2026

Validation was extended to three additional apparition years (2023, 2024, 2026) using
the same astropy/ERFA oracle, same observer (Babylon), and same five stars. This
provides a 4-year sample (including the 2025 baseline) per star — 20 cases total.

Script: `tmp/stellar_heliacal_multiyear.py`

### 12.1 Results

| Star | Year | av | Moira | Oracle | Match |
|------|------|----|-------|--------|-------|
| Sirius | 2023 | 7.5° | 2023-Aug-04 | 2023-Aug-04 | **EXACT** |
| Sirius | 2024 | 7.5° | 2024-Aug-03 | 2024-Aug-03 | **EXACT** |
| Sirius | 2026 | 7.5° | 2026-Aug-04 | 2026-Aug-04 | **EXACT** |
| Aldebaran | 2023 | 10.0° | 2023-Jun-20 | 2023-Jun-20 | **EXACT** |
| Aldebaran | 2024 | 10.0° | 2024-Jun-19 | 2024-Jun-19 | **EXACT** |
| Aldebaran | 2026 | 10.0° | 2026-Jun-20 | 2026-Jun-20 | **EXACT** |
| Regulus | 2023 | 11.0° | 2023-Sep-04 | 2023-Sep-04 | **EXACT** |
| Regulus | 2024 | 11.0° | 2024-Sep-03 | 2024-Sep-03 | **EXACT** |
| Regulus | 2026 | 11.0° | 2026-Sep-04 | 2026-Sep-04 | **EXACT** |
| Antares | 2023 | 10.0° | 2023-Dec-16 | 2023-Dec-16 | **EXACT** |
| Antares | 2024 | 10.0° | 2024-Dec-15 | 2024-Dec-15 | **EXACT** |
| Antares | 2026 | 10.0° | 2026-Dec-16 | 2026-Dec-16 | **EXACT** |
| Fomalhaut | 2023 | 11.0° | 2023-Apr-18 | 2023-Apr-18 | **EXACT** |
| Fomalhaut | 2024 | 11.0° | 2024-Apr-17 | 2024-Apr-17 | **EXACT** |
| Fomalhaut | 2026 | 11.0° | 2026-Apr-18 | 2026-Apr-18 | **EXACT** |

**15 of 15 EXACT.**

---

### 12.2 Regulus — elongation guard removal

Prior to 2026-04-10, `heliacal_rising_event` skipped days with `abs(se) < 12.0°`.
Because Regulus's arcus visionis (11°) is below that threshold, the guard blocked the
first altitude-valid day every year, producing a systematic +1-day offset. After removing
the redundant guard (see §5), all four Regulus years are now exact:

| Year | Oracle | Moira (fixed) | Regulus elongation at event date |
|------|--------|---------------|-----------------------------------|
| 2023 | Sep-04 | Sep-04 | ≈ −11.1° |
| 2024 | Sep-03 | Sep-03 | ≈ −11.0° |
| 2025 | Sep-03 | Sep-03 | −11.06° (measured; see §6.3) |
| 2026 | Sep-04 | Sep-04 | ≈ −11.1° |

The altitude agreement between Moira and astropy at the event twilight JD is
0.005°–0.007° in all four years — identical to before the fix, confirming the
change is isolated to the elongation guard logic only.

---

### 12.3 Four-year combined summary (2023–2026)

Including the 2025 baseline from §7:

| Star | 2023 | 2024 | 2025 | 2026 | Exact / 4 |
|------|------|------|------|------|-----------|
| Sirius | Aug-04 ✓ | Aug-03 ✓ | Aug-03 ✓ | Aug-04 ✓ | **4 / 4** |
| Aldebaran | Jun-20 ✓ | Jun-19 ✓ | Jun-19 ✓ | Jun-20 ✓ | **4 / 4** |
| Regulus | Sep-04 ✓ | Sep-03 ✓ | Sep-03 ✓ | Sep-04 ✓ | **4 / 4** |
| Antares | Dec-16 ✓ | Dec-15 ✓ | Dec-15 ✓ | Dec-16 ✓ | **4 / 4** |
| Fomalhaut | Apr-18 ✓ | Apr-17 ✓ | Apr-18 ✓ | Apr-18 ✓ | **4 / 4** |

**20 of 20 exact across four years.**

All five stars match the astropy/ERFA oracle exactly across every tested year.
The Regulus offset documented in earlier sessions was caused by a redundant elongation
magnitude guard in `heliacal_rising_event`; that guard has been removed. See §5 and §12.2.
