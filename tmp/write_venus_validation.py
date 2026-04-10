from pathlib import Path

content = """\
# Validation Case: Sun-Venus Conjunctions (2026-2032)

**Subject**: Geocentric apparent Sun-Venus conjunctions  
**Substrate**: Moira / JPL DE441  
**Oracle**: JPL Horizons (geocenter, DE441, apparent ecliptic lon/lat, quantity 31)  
**Status**: VERIFIED -- all events within 0.06 arcmin of Horizons  
**Verified**: 2026-04-10

## 1. What is being tested

`moira.phenomena.conjunctions_in_range(Body.SUN, Body.VENUS, ...)` finds the exact UTC moment at which Venus and the Sun share the same apparent geocentric ecliptic longitude. The test covers nine consecutive synodic conjunctions spanning one complete Venus pentagonal cycle (2026-2032), encompassing both inferior and superior types.

This is a modern, delta-T-free comparison. All events fall within JPL Horizons' EOP data coverage, so there is no epoch-uncertainty ambiguity.

## 2. Methodology

Moira uses a two-stage bisection:

1. **Geometric pass** -- coarse scan on astrometric (light-time uncorrected) vectors to find the longitude zero-crossing
2. **Apparent refinement** -- fine bisection on the full apparent pipeline (light-time, aberration, frame bias, precession, nutation) to sub-second precision

The oracle query used JPL Horizons API (`EPHEM_TYPE=OBSERVER`, `CENTER=500@399`, `QUANTITIES=31`, `CSV_FORMAT=YES`) for both Venus (299) and the Sun (10) at +/-10 minutes around each Moira conjunction time in 5-minute steps. The column reported is `ObsEcLon` -- the apparent geocentric ecliptic longitude of the target (J2000 ecliptic frame). The Venus-Sun separation at Moira's predicted time is the residual.

## 3. Results

| Moira UTC time | Type | Moira lon (deg) | Venus@t (deg) | Sun@t (deg) | Sep (arcmin) |
|---|---|---|---|---|---|
| 2026-01-06 16:35:59 | Inferior | 286.3675 | 286.3667 | 286.3668 | -0.010 |
| 2026-10-24 03:44:06 | Inferior | 210.7507 | 210.7508 | 210.7506 | +0.008 |
| 2027-08-12 00:20:52 | Superior | 139.1111 | 139.1103 | 139.1105 | -0.010 |
| 2028-06-01 10:00:17 | Inferior |  71.4388 |  71.4389 |  71.4385 | +0.020 |
| 2029-03-23 20:11:53 | Superior |   3.4815 |   3.4807 |   3.4809 | -0.009 |
| 2030-01-06 13:17:37 | Inferior | 286.2653 | 286.2656 | 286.2649 | +0.043 |
| 2030-10-20 11:12:26 | Superior | 207.1067 | 207.1063 | 207.1064 | -0.005 |
| 2031-08-11 03:00:49 | Inferior | 138.2870 | 138.2873 | 138.2864 | +0.055 |
| 2032-06-02 09:07:27 | Superior |  72.3922 |  72.3918 |  72.3919 | -0.005 |

Maximum residual: **+0.055 arcmin** (2031-08-11). All nine events are within 0.06 arcmin of Horizons DE441 at Moira's predicted time.

A residual of 0.055 arcmin corresponds to roughly 2-3 minutes of time error at Venus's conjunction angular speed (~0.02 deg/hour relative to the Sun). The alternating sign confirms there is no systematic offset.

## 4. What this validates

- The conjunction solver correctly finds apparent geocentric longitude equality for an inner planet across both inferior and superior geometries.
- The apparent pipeline (light-time, aberration, nutation) is being applied correctly -- astrometric-only positions would diverge by tens of arcminutes.
- Moira's DE441 kernel is producing the same ephemeris as the Horizons DE441 server for Venus at this epoch.

## 5. What this does not validate

- Topocentric corrections (this is geocenter only)
- Heliacal events or visibility thresholds
- Bodies other than Venus and the Sun

## 6. Verification script

`tmp/venus_horizons_check.py` -- queries Horizons live and prints the residual table above. Reproducible against the Horizons API as long as the target dates remain within the EOP prediction window.
"""

path = Path(r"c:\Users\nilad\OneDrive\Desktop\Moira\wiki\03_standards\VALIDATION_CASE_VENUS_STAR.md")
path.write_text(content, encoding="utf-8")
print("written", len(content), "bytes")
