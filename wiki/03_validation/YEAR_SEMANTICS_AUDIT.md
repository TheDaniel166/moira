# Year Semantics Audit

Date: 2026-03-30

Purpose
-------
Audit every live use of `365.25`, `36525.0`, `JULIAN_YEAR`, `TROPICAL_YEAR`,
and `SIDEREAL_YEAR` in the `moira/` codebase so the project distinguishes:

- exact Julian-year doctrine
- tropical-year timing
- sidereal-year/orbital timing
- standard Julian-date algorithm constants
- sites that remain candidates for future refinement

Summary Verdict
---------------
Most remaining `365.25` uses are correct and should remain.

The codebase currently contains five distinct semantic classes:

1. `Julian year` by doctrine or convention: keep.
2. `Tropical year` for seasonal/solar timing: use `TROPICAL_YEAR`.
3. `Sidereal year` for orbital/stellar period timing: use `SIDEREAL_YEAR`.
4. `Julian century` (`36525.0`) in standard astronomical polynomials: keep.
5. `365.25` inside canonical calendar/JD conversion algorithms: keep.

After the latest correction pass, the main live upgrade targets that remain are
small in number. The largest genuinely ambiguous site is the annual-resolution
integration in `delta_t_physical.py`.

Class A: Keep As Exact Julian-Year Doctrine
-------------------------------------------
These are not loose approximations. They are explicit Julian-year doctrine,
historical astrological convention, or standard astronomical convention.

- `moira/constants.py`
  - `JULIAN_YEAR = 365.25`
  - Correct. Exact by definition.
- `moira/dasha.py`
  - `julian_365.25` basis and all `JULIAN_YEAR` uses
  - Correct. This is an explicit doctrinal year basis, contrasted with `savana_360`.
- `moira/timelords.py`
  - `_JULIAN_YEAR = 365.25`
  - Correct. The module explicitly says JD arithmetic uses Julian years.
- `moira/profections.py`
  - `age_years = int(elapsed_days / 365.25)`
  - Plausibly correct if the subsystem intends completed ages in fractional Julian years.
  - This is doctrinal rather than physical astronomy. Keep unless the profection doctrine is intentionally revised.
- `moira/primary_directions/keys.py`
  - `_NAIBOD_RATE = 360.0 / 365.25`
  - Correct. Naibod is a doctrinal key, not a generic solar-year approximation.
- `moira/primary_directions/__init__.py`
  - `_DEFAULT_SOLAR_RATE = 360.0 / 365.25`
  - Likely correct within primary-direction key doctrine unless the subsystem explicitly adopts a different key basis.
- `moira/stars.py`
  - proper-motion propagation: `dt_years = (jd_tt - _J2000) / 365.25`
  - light-time conversion: `_DAYS_PER_YEAR = 365.25`
  - Correct by astronomical convention. Proper motion is normally expressed per Julian year; the light-year is conventionally tied to the Julian year.
- `moira/multiple_stars.py`
  - `OrbitalElements.period_yr` is documented as Julian years
  - `t_yr = (jd - orb.epoch_jd) / 365.25`
  - Correct because the module explicitly defines orbital periods in Julian years.
- `moira/sothic.py`
  - `1460 × 365.25 = 533265`
  - `cycle_pos = ((jd_rise - epoch_jd) / 365.25) % _SOTHIC_CYCLE_YEARS`
  - Correct. The Sothic cycle identity is specifically Julian-year based.

Class B: Keep As Tropical-Year Timing
-------------------------------------
These are places where the code means seasonal or solar-cycle timing rather
than a generic Julian year.

- `moira/constants.py`
  - `TROPICAL_YEAR = 365.24219`
- `moira/harmonics.py`
  - age harmonic timing uses `TROPICAL_YEAR`
  - Correct.
- `moira/progressions.py`
  - progression age conversion uses `TROPICAL_YEAR`
  - Correct.
- `moira/transits.py`
  - `solar_return()` search seed now uses `TROPICAL_YEAR`
  - Correct. The solar return is seasonal/solar, not Julian-year doctrine.

Class C: Keep As Sidereal-Year / Orbital Timing
-----------------------------------------------
These are places where the code means orbital period or sidereal cycle timing.

- `moira/constants.py`
  - `SIDEREAL_YEAR = 365.256363`
  - `Body.SIDEREAL_PERIODS[EARTH] = SIDEREAL_YEAR`
  - Correct.
- `moira/phenomena.py`
  - perihelion/aphelion fallback search windows now use `SIDEREAL_YEAR`
  - Correct. These are orbital search heuristics, not seasonal year lengths.

Class D: Keep As Julian-Century Polynomial Time
-----------------------------------------------
These are standard astronomical polynomial scales. They are not “approximate
years” in the sense at issue here.

- `moira/constants.py`
  - `JULIAN_CENTURY = 36525.0`
- `moira/coordinates.py`
  - `T = (jd_tt - 2451545.0) / 36525.0`
- `moira/eclipse.py`
  - `centuries = delta_days / 36525.0`
- `moira/hermetic_decans.py`
  - `T = (jd - 2451545.0) / 36525.0`
- `moira/nodes.py`
  - rates divided by `36525.0`
- `moira/precession.py`
  - `T * 36525.0`

These should remain exactly as they are unless the underlying polynomial model
itself changes.

Class E: Keep As Canonical JD/Calendar Algorithm Terms
------------------------------------------------------
These uses occur inside standard Meeus-style or related calendar/JD conversion
formulae. They are algorithm constants, not physical year approximations.

- `moira/julian.py`
  - `math.floor(365.25 * (year + 4716))`
  - `(B - 122.1) / 365.25`
  - `D = math.floor(365.25 * C)`
- `moira/planets.py`
  - inverse calendar/JD helper with the same constants

These should not be rewritten as tropical or sidereal years.

Class F: Genuine Remaining Audit Candidate
------------------------------------------
This is the main live site that still merits a model-level decision.

- `moira/delta_t_physical.py`
  - `dt_days = (y1 - y0) * 365.25`

Assessment:
- The code integrates an annual-resolution LOD anomaly series expressed in
  decimal years.
- `365.25` is serviceable, but this is not as doctrinally locked as the
  Julian-year, light-year, Naibod, or JD algorithm cases.
- A better choice might be:
  - `TROPICAL_YEAR` if the decimal years are interpreted as mean civil/seasonal spacing
  - a file-driven exact epoch delta if the source timestamps are actual annual epochs
  - leave as `JULIAN_YEAR` if the series is intended as a uniform year axis

Recommendation:
- Do not change this site blindly.
- Resolve it only after checking the source-data convention for the LOD files.

Low-Priority Cosmetic Improvements
----------------------------------
These are not correctness bugs, but could be made more explicit over time.

- `moira/profections.py`
  - could import `JULIAN_YEAR` instead of spelling `365.25`
- `moira/stars.py`
  - could import `JULIAN_YEAR` instead of local `_DAYS_PER_YEAR = 365.25`
- `moira/timelords.py`
  - could import `JULIAN_YEAR` instead of local `_JULIAN_YEAR = 365.25`
- `moira/multiple_stars.py`
  - could import `JULIAN_YEAR` for consistency with its “Julian years” doctrine

These are semantic-clarity refactors, not accuracy fixes.

Recommended Next Steps
----------------------
1. Leave all Class A, C, D, and E sites untouched.
2. Optionally normalize explicit Julian-year imports in Class A for consistency.
3. Do a source-convention check on `moira/data/core_angular_momentum.txt` and
   related ΔT files before changing `moira/delta_t_physical.py`.
4. If desired, annotate key modules with “Julian year”, “tropical year”, or
   “sidereal year” comments at the constant declaration points to prevent future drift.

