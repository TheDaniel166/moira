# Adversarial Singularity Defect Ledger

Version: 1.1
Date: 2026-05-21
Branch at discovery: fix/facade-core-chart-timescale

---

## Purpose

This is a living document. It records every defect and test-design finding
produced by the adversarial singularity test suite. Each entry states the
test that finds it, what the engine does, and what correct behaviour looks
like. When a defect is fixed, the entry is moved to the **Resolved** section
with the fix commit and the corrected test result.

The suite does not validate correctness. It attacks mathematical seams,
boundary conditions, and degenerate inputs to find where the engine lies or
collapses silently. A test that fails on first run has found a real defect.
A test that passes has proven the engine handles that singularity.

---

## Test Files

| File | Layer | Focus |
|---|---|---|
| `tests/unit/test_adversarial_singularities.py` | 1–3 + cross-cutting | Coordinate transforms, planetary geometry, time system, route equivalence, boundary ownership |
| `tests/unit/test_adversarial_house_singularities.py` | 4 | House cusps, angular singularities, opposition invariants, cusp ordering |

Run command:
```
python -m pytest tests/unit/test_adversarial_singularities.py tests/unit/test_adversarial_house_singularities.py -v
```

Suite result as of 2026-05-21 (after DEF-001/002/003 fix): **108 collected — 59 pass, 11 fail, 2 skip (Layers 1–3); 52 pass, 0 fail, 1 skip (Layer 4).**

---

## Resolved Defects

### DEF-001 — `ecliptic_to_equatorial` does not normalise RA output at 360°

- **Test:** `test_layer1c_360_degree_input_normalises_to_zero`
- **Layer:** 1c
- **What happened:** `ecliptic_to_equatorial(360.0, 0.0, obliquity)` returned RA = 360.0°
  instead of 0.0°. Input 360° is mathematically 0°, but the `atan2 * RAD2DEG % 360`
  expression produced a tiny-negative intermediate value whose IEEE 754 addition
  to 360.0 did not underflow the representable floor, yielding 360.0.
- **Fix:** Changed `math.atan2(y, x) * RAD2DEG % 360.0` to
  `normalize_degrees(math.atan2(y, x) * RAD2DEG)` in `ecliptic_to_equatorial`.
- **Fix commit:** see PR `fix/coordinate-normalize-boundary`
- **Verified:** 2026-05-21 — test passes; killer suite 42/42.

---

### DEF-002 — `icrf_to_ecliptic` accepts zero-vector input silently

- **Test:** `test_layer1f_icrf_to_ecliptic_zero_vector`
- **Layer:** 1f
- **What happened:** `icrf_to_ecliptic((0.0, 0.0, 0.0), obliquity)` returned
  `(0.0, 0.0, 0.0)` — distance 0, but finite longitude and latitude — with no
  exception raised.
- **Fix:** Added `if distance == 0.0: raise ValueError(...)` immediately after
  computing the magnitude in `icrf_to_ecliptic`. Also applied `normalize_degrees`
  to the longitude output for consistency.
- **Fix commit:** see PR `fix/coordinate-normalize-boundary`
- **Verified:** 2026-05-21 — test passes; killer suite 42/42.

---

### DEF-003 — `normalize_degrees(-1e-15)` returns 360.0

- **Test:** `test_layer1h_negative_epsilon_normalises_near_zero`
- **Layer:** 1h
- **What happened:** `normalize_degrees(-1e-15)` returned 360.0. `(-1e-15) % 360.0`
  computes `360.0 - 1e-15`, but `1e-15` is smaller than the ULP of 360.0
  (~5.7e-14 in float64), so the subtraction is a no-op and the result is 360.0.
- **Fix:** Added a clamp after the modulo: `return 0.0 if result >= 360.0 else result`.
- **Fix commit:** see PR `fix/coordinate-normalize-boundary`
- **Verified:** 2026-05-21 — test passes; killer suite 42/42.

---

## Open Defects

### DEF-004 — Year-zero calendar round-trip is broken

- **Test:** `test_layer3b_year_zero_calendar_round_trip`
- **Layer:** 3b
- **What happens:** `calendar_from_jd(julian_day(0, 1, 1))` returns
  `year = 1` instead of `year = 0`. The engine does not use astronomical
  year numbering (where 1 BCE = year 0) consistently. The round-trip
  `julian_day → calendar_from_jd` does not recover year 0.
- **Correct behaviour:** The proleptic Julian calendar using astronomical year
  numbering has year 0 (= 1 BCE). `julian_day(0, 1, 1)` and `calendar_from_jd`
  must agree on this convention. `calendar_from_jd(julian_day(0, 1, 1))`
  must recover `(year=0, month=1, day=1)`.
- **Affected modules:** `moira/julian.py` — `julian_day` and/or `calendar_from_jd`
- **Priority:** Medium — incorrect year returned for BCE epochs near zero.
- **Status:** Open

---

### DEF-005 — Out-of-coverage JD raises `KeyError` instead of `OutOfRangeError`

- **Tests:**
  - `test_layer3c_jd_zero_raises_named_exception` — JD = 0.0 does not raise
    at all; the engine returns a position silently.
  - `test_layer3c_deeply_negative_jd_raises_named_exception` — JD = −1 000 000
    raises `KeyError("No kernel in pool covers …")` instead of `OutOfRangeError`.
  - `test_boundary_ownership_out_of_coverage_raises_not_silence` — JD = −4 000 000
    raises `KeyError` for the same reason.
- **Layer:** 3c, cross-cutting
- **What happens:** When a query falls outside DE441 coverage, the kernel pool
  raises a raw `KeyError` rather than a named `moira.spk_reader.OutOfRangeError`.
  Additionally, JD = 0.0 falls within some segment's coverage and returns a
  position rather than raising — the coverage guard is not strict enough.
- **Correct behaviour:** Any JD outside the engine's declared coverage must
  raise `OutOfRangeError`. No raw `KeyError` should escape from the public
  `planet_at` surface.
- **Affected modules:** `moira/spk_reader.py` (KernelPool), `moira/planets.py`
  (coverage guard upstream of the kernel call)
- **Priority:** High — the public contract for out-of-range behaviour is broken.
  Callers cannot reliably catch coverage failures by name.
- **Status:** Open

---

### DEF-006 — Deep historical calendar round-trip error of 26–38 days

- **Tests:**
  - `test_layer3g_deep_historical_calendar_round_trip[1.0]` — error 37.5 days
  - `test_layer3g_deep_historical_calendar_round_trip[500000.0]` — error 26.5 days
  - `test_layer3g_deep_historical_calendar_round_trip[-100000.0]` — error 38.5 days
- **Layer:** 3g
- **What happens:** `calendar_from_jd → julian_day` round-trips at deep
  historical JDs (before the Gregorian reform epoch) return errors of 26–38
  days. The fractional part of each error is 0.5, suggesting a consistent
  Julian-noon vs. calendar-midnight origin mismatch compounded by a
  Julian/Gregorian epoch confusion at pre-reform dates.
- **Correct behaviour:** `calendar_from_jd(jd) → (y, m, d, h)`, then
  `julian_day(y, m, d) + (d - int(d))` must recover the original `jd` within
  less than 1 day for any JD in the proleptic Julian calendar. Errors of
  tens of days indicate a systematic calendar-switch or epoch-offset error.
- **Affected modules:** `moira/julian.py` — `calendar_from_jd` and/or `julian_day`
  at pre-reform JDs.
- **Priority:** Medium — affects historical chart computation for BCE epochs.
- **Status:** Open

---

## Test-Design Findings

These are not engine defects. The tests have found that their own hardcoded
constants are too imprecise to make the intended assertion. The tests remain
failing as a reminder that more accurate constants are needed.

---

### TDF-001 — Station R/D JD constants are off by more than 1 hour

- **Tests:** `test_layer2c_retrograde_station_speed_sign_change[Mercury/Venus/Mars]`
- **Layer:** 2c
- **What the test does:** Asserts that 1 hour after the hardcoded station R JD,
  the planet's longitudinal speed is negative (retrograde), and 1 hour before
  the station D JD, the speed is still negative.
- **What happens:** All three planets still show positive speed 1 hour after
  the hardcoded station R epoch. The actual station R is later than the
  hardcoded JD.
- **Constants in question:**
  - `_JD_MERCURY_STATION_R_2023 = 2460055.0` (2023-04-21 noon TT)
  - `_JD_VENUS_STATION_R_2023   = 2460148.0` (2023-07-22 noon TT)
  - `_JD_MARS_STATION_R_2022    = 2459882.5` (2022-10-30 noon TT)
- **Resolution needed:** Replace with more accurate station JDs (sub-hour
  precision), or widen the speed-sign bracket to ±4 hours to tolerate
  day-granularity constants.
- **Status:** Open (test design)

---

### TDF-002 — Moon perigee JD is too early for the ±6-hour bracket

- **Test:** `test_layer2j_moon_distance_local_minimum_near_perigee`
- **Layer:** 2j
- **What the test does:** Samples Moon distance at ±6 hours around
  `_JD_MOON_PERIGEE_2023 = 2459966.08` and checks that the minimum is in the
  interior of the bracket.
- **What happens:** The minimum distance falls at the last sample (+6 h edge),
  meaning the actual perigee is later than the hardcoded JD by more than 6
  hours.
- **Resolution needed:** Identify the correct 2023 perigee epoch to sub-hour
  precision and update the constant, or widen the bracket to ±12 hours.
- **Status:** Open (test design)

---

## Layer 4 — House Singularities

All 52 executable Layer 4 tests pass as of 2026-05-20.

One test is permanently skipped: `test_layer4k_body_on_cusp_placement_is_stable_and_deterministic`
— `house_of()` is not yet implemented in `moira.houses`. When it is
implemented, this skip will lift and the test will run.

| Attack | Result |
|---|---|
| ASC near 0° Aries — no 360° leak | Pass |
| Observer at equator (all systems) | Pass |
| RAMC at 0°, 90°, 180°, 270° | Pass |
| MC near 0° — no 360° leak | Pass |
| Just below critical latitude — no fallback | Pass |
| Just above critical latitude — fallback or named error | Pass |
| 89° latitude — fallback or named error, no hang | Pass |
| MC/IC opposition invariant (all systems, 3 epochs) | Pass |
| ASC/DSC opposition invariant (all systems) | Pass |
| Circular cusp ordering (quadrant systems) | Pass |
| ASC near 359° — no negative or inverted cusps | Pass |
| Extreme latitudes (85°, 87°, 89.9°) — no hang | Pass |
| MC continuity over 24-hour cycle | Pass |

---

## How to Update This Document

When a defect is fixed:
1. Move the entry from **Open Defects** to a new **Resolved** section.
2. Add a `Fix:` line naming the commit SHA and the module(s) changed.
3. Add a `Verified:` line stating which test now passes and the date.

When a test-design finding is corrected:
1. Update the constant in the test file.
2. Note the correction in the TDF entry and mark it Resolved.

When a new adversarial attack is added to the suite:
1. Run the full suite and update the summary counts at the top.
2. Add any new failures as new DEF or TDF entries.
