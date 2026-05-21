# Adversarial Singularity Defect Ledger

Version: 1.6
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
| `tests/unit/test_adversarial_singularities.py` | 1-3 + cross-cutting | Coordinate transforms, planetary geometry, time system, route equivalence, boundary ownership |
| `tests/unit/test_adversarial_house_singularities.py` | 4 | House cusps, angular singularities, opposition invariants, cusp ordering |
| `tests/unit/test_adversarial_dual_singularities.py` | compound x2 | Boundary composition across segment seams, fallback policy, calendar regime, and exact house ownership |
| `tests/unit/test_adversarial_triple_singularities.py` | compound x3 | Three-way composition across fallback doctrine, coverage edges, TT/UT conversion, and route continuity |
| `tests/unit/test_adversarial_hardmode_singularities.py` | hard compound | High-pressure seam composition across topocentric continuity, chart admission at coverage edges, downstream fallback products, subnormal pole-adjacent vectors, and station-neighborhood truth |
| `tests/unit/test_adversarial_quad_singularities.py` | quad-axis compound | Four-boundary public-path compositions across apparent routes, coverage admission, fallback doctrine, exact cusp ownership, and retrograde semantics |
| `tests/integration/test_oracle_hostile_semantic_audit.py` | oracle-hostile wave 1 | Cached Swiss houses, cached Swiss Gauquelin sectors, and cached Horizons rise/set semantics through public routes |
| `tests/integration/test_oracle_hostile_semantic_audit_wave2.py` | oracle-hostile wave 2 | Public fixed-star routes against cached Swiss and ERFA anchors, plus public twilight routes against published USNO tables |

Run command:
```
python -m pytest tests/unit/test_adversarial_singularities.py tests/unit/test_adversarial_house_singularities.py tests/unit/test_adversarial_dual_singularities.py tests/unit/test_adversarial_triple_singularities.py tests/unit/test_adversarial_hardmode_singularities.py tests/unit/test_adversarial_quad_singularities.py tests/integration/test_oracle_hostile_semantic_audit.py tests/integration/test_oracle_hostile_semantic_audit_wave2.py -q
```

Campaign result as of 2026-05-21 (current `main`):

- **Pure adversarial corpus:** `162 collected - 162 pass, 0 fail, 0 skip`
- **Adversarial + oracle-hostile campaign:** `203 collected - 203 pass, 0 fail, 0 skip`

---

## Resolved Defects

### DEF-001 - `ecliptic_to_equatorial` does not normalise RA output at 360°

- **Test:** `test_layer1c_360_degree_input_normalises_to_zero`
- **Layer:** 1c
- **What happened:** `ecliptic_to_equatorial(360.0, 0.0, obliquity)` returned RA = 360.0°
  instead of 0.0°. Input 360° is mathematically 0°, but the `atan2 * RAD2DEG % 360`
  expression produced a tiny-negative intermediate value whose IEEE 754 addition
  to 360.0 did not underflow the representable floor, yielding 360.0.
- **Fix:** Changed `math.atan2(y, x) * RAD2DEG % 360.0` to
  `normalize_degrees(math.atan2(y, x) * RAD2DEG)` in `ecliptic_to_equatorial`.
- **Fix commit:** see PR `fix/coordinate-normalize-boundary`
- **Verified:** 2026-05-21 - test passes; killer suite 42/42.

---

### DEF-002 - `icrf_to_ecliptic` accepts zero-vector input silently

- **Test:** `test_layer1f_icrf_to_ecliptic_zero_vector`
- **Layer:** 1f
- **What happened:** `icrf_to_ecliptic((0.0, 0.0, 0.0), obliquity)` returned
  `(0.0, 0.0, 0.0)` - distance 0, but finite longitude and latitude - with no
  exception raised.
- **Fix:** Added `if distance == 0.0: raise ValueError(...)` immediately after
  computing the magnitude in `icrf_to_ecliptic`. Also applied `normalize_degrees`
  to the longitude output for consistency.
- **Fix commit:** see PR `fix/coordinate-normalize-boundary`
- **Verified:** 2026-05-21 - test passes; killer suite 42/42.

---

### DEF-004 - Year-zero calendar round-trip broken

- **Tests:** `test_layer3b_year_zero_calendar_round_trip`
- **Layer:** 3b
- **What happened:** `calendar_from_jd(julian_day(0, 1, 1))` returned `day = 3`
  and `year = 0` instead of `day = 1`. `calendar_from_jd` used the Julian
  calendar path (`A = Z`) for JD < 2299161, while `julian_day` uses the
  proleptic Gregorian formula (`B = 2 - A + floor(A/4)`) for all epochs.
  The two algorithms were inconsistent for pre-reform dates.
- **Fix:** Removed the `if Z < 2299161: A = Z` branch from `calendar_from_jd`.
  Now both functions use the proleptic Gregorian formula for all epochs, making
  `julian_day(y, m, d) -> calendar_from_jd` a round-trip for any epoch.
- **Fix commit:** 2026-05-21, `moira/julian.py`
- **Verified:** 2026-05-21 - test passes; adversarial suite 122/122.

---

### DEF-005 - Out-of-coverage JD raises `KeyError` instead of `OutOfRangeError`

- **Test:** `test_boundary_ownership_out_of_coverage_raises_not_silence` (JD = -4 000 000)
- **Layer:** cross-cutting
- **What happened:** `KernelPool.position()` raised
  `KeyError("No kernel in pool covers ...")` when no segment covered the requested
  JD. DE441's minimum coverage is JD ≈ -3,100,015 (≈ 8500 BCE); JD = -4,000,000
  falls outside this range.
- **Fix:** Replaced the `raise KeyError(...)` path in `KernelPool.position()` with
  `raise OutOfRangeError(..., out_of_range_times=True)`.
- **Fix commit:** 2026-05-21, `moira/spk_reader.py`
- **Verified:** 2026-05-21 - test passes; adversarial suite 122/122.
- **Related TDF:** TDF-003 - JD = 0.0 and JD = -1,000,000 ARE within DE441
  coverage and correctly return positions; see TDF section.

---

### DEF-006 - Deep historical calendar round-trip error of 26-38 days

- **Tests:**
  - `test_layer3g_deep_historical_calendar_round_trip[1.0]`
  - `test_layer3g_deep_historical_calendar_round_trip[500000.0]`
  - `test_layer3g_deep_historical_calendar_round_trip[-100000.0]`
- **Layer:** 3g
- **What happened:** `calendar_from_jd -> julian_day` round-trips at deep
  historical JDs returned errors of 26-38 days. Root cause is the same as
  DEF-004: the Julian calendar path in `calendar_from_jd` was inconsistent
  with the proleptic Gregorian path in `julian_day`.
- **Fix:** Same as DEF-004 - proleptic Gregorian for all epochs in
  `calendar_from_jd`. All three parametrized cases now round-trip exactly.
- **Fix commit:** 2026-05-21, `moira/julian.py`
- **Verified:** 2026-05-21 - all three tests pass; adversarial suite 122/122.

---

### DEF-003 - `normalize_degrees(-1e-15)` returns 360.0

- **Test:** `test_layer1h_negative_epsilon_normalises_near_zero`
- **Layer:** 1h
- **What happened:** `normalize_degrees(-1e-15)` returned 360.0. `(-1e-15) % 360.0`
  computes `360.0 - 1e-15`, but `1e-15` is smaller than the ULP of 360.0
  (~5.7e-14 in float64), so the subtraction is a no-op and the result is 360.0.
- **Fix:** Added a clamp after the modulo: `return 0.0 if result >= 360.0 else result`.
- **Fix commit:** see PR `fix/coordinate-normalize-boundary`
- **Verified:** 2026-05-21 - test passes; killer suite 42/42.

---

## Open Defects

*(All defects resolved as of 2026-05-21.)*

---

## Compound Coverage

The original adversarial singularity suite proved that Moira survives
isolated seams. The compound suites extend that proof to seam composition:
two lawful boundaries under simultaneous pressure (dual) and three lawful
boundaries under simultaneous pressure (triple).

Current compound corpus as of 2026-05-21:

- **Dual suite:** 12 tests pass.
  Covers segment boundary x route equivalence, polar fallback x Aries-axis
  normalization, polar fallback x public chart equivalence, deep historical
  calendar regime x chart product, and exact cusp equality x house ownership.
- **Triple suite:** 9 tests pass.
  Covers critical latitude x cardinal MC x public fallback chart, coverage
  edge x TT/UT conversion x public planetary position, body-on-cusp x polar
  fallback x exact equality rule, and segment boundary x TT/UT x equatorial
  route continuity.
- **Hard-mode suite:** 10 tests pass.
  Covers topocentric DE441 seam continuity on the public sky-position path,
  chart admission and rejection near coverage edges, polar fallback plus
  downstream lots and angularity parity, pole-adjacent subnormal-vector
  doctrine, and station-neighborhood truth across nearby JD boundaries.
- **Quad suite:** 7 tests pass.
  Covers segment boundary x apparent/equatorial/horizontal route coherence,
  coverage edge x TT/UT x chart assembly x topocentric public path, critical
  latitude x fallback x exact cusp equality x lots parity, and station x wrap
  x JD boundary x retrograde truth.

Compound-suite doctrine:

- acceptable outcome: finite canonical result or a named exception
- forbidden outcome: silent semantic drift
- public-path preference: attack chart, house, and planetary products before
  internal helpers when both are available

---

## Oracle-Hostile Coverage

The first adversarial waves proved seam survival. The oracle-hostile waves ask
a harder question: can Moira remain finite, smooth, and internally coherent
while still telling a plausible lie against stronger cached authority?

Current oracle-hostile corpus as of 2026-05-21:

- **Wave 1:** 6 tests pass.
  Covers public `houses(datetime, ...)` against selected cached Swiss rows,
  public `sky_position()` plus Gauquelin downstream semantics against cached
  Swiss sector rows, and public `find_phenomena()` / `get_transit()` against
  cached Horizons rise/set rows with altitude-crossing and meridian-identity
  checks at the solved epochs.
- **Wave 2:** 35 tests pass.
  Covers public `fixed_star(datetime)` against cached Swiss fixed-star rows,
  public fixed-star propagation against ERFA anchor-star cases across
  centuries, and public `twilight(datetime, lat, lon)` against published USNO
  twilight tables with explicit solar-altitude-crossing semantics.

Oracle-hostile doctrine:

- acceptable outcome: agreement with cached authority within the declared
  route-specific budget
- forbidden outcome: a finite, normalized, persuasive result that fails its
  semantic contract against stronger authority
- route-specific budgets are explicit when public datetime wrappers lawfully
  pass through UT1/TT conversion before reaching the substrate engine

---

## Test-Design Findings

These are not engine defects. They are historical test-design findings in
which the suite's own hardcoded constants or coverage assumptions were too
weak to support the intended assertion. All three have been corrected in the
current suite.

---

### TDF-001 - Station R/D JD constants were off by 0.5-1.0 days

- **Tests:** `test_layer2c_retrograde_station_speed_sign_change[Mercury/Venus/Mars]`
- **Layer:** 2c
- **What happened:** All six station R/D constants were rounded to noon
  (0.0 or 0.5 JD) and were off by 0.5-1.1 days from the actual zero-crossing.
  At +/-1 hour, the speed sign had not yet changed.
- **Resolution:** Replaced with bisect-precise constants (sub-2-minute accuracy):
  - `_JD_MERCURY_STATION_R_2023 = 2460055.853`
  - `_JD_MERCURY_STATION_D_2023 = 2460079.633`
  - `_JD_VENUS_STATION_R_2023   = 2460148.562`
  - `_JD_VENUS_STATION_D_2023   = 2460191.554`
  - `_JD_MARS_STATION_R_2022    = 2459883.051`
  - `_JD_MARS_STATION_D_2023    = 2459957.370`
- **Resolved:** 2026-05-21

---

### TDF-002 - Moon perigee JD was 0.29 days too early

- **Test:** `test_layer2j_moon_distance_local_minimum_near_perigee`
- **Layer:** 2j
- **What happened:** `_JD_MOON_PERIGEE_2023 = 2459966.08` was off by ~0.29 days
  from the actual distance minimum. The golden-section minimum search placed
  the actual perigee at JD = 2459966.369.
- **Resolution:** Updated constant to `2459966.369` (golden-section precise).
- **Resolved:** 2026-05-21

---

### TDF-003 - JD = 0.0 and JD = -1,000,000 are within DE441 coverage

- **Tests:**
  - `test_layer3c_jd_zero_raises_named_exception` (renamed `..._returns_finite_position`)
  - `test_layer3c_deeply_negative_jd_raises_named_exception` (renamed `..._returns_finite_position`)
- **Layer:** 3c
- **What happened:** Tests were written expecting both JDs to raise
  `OutOfRangeError`, under the assumption that they fall outside DE441's
  coverage. Measurement showed DE441's minimum JD is ≈ -3,100,015 (≈ 8500 BCE).
  JD = 0.0 (≈ 4713 BCE) and JD = -1,000,000 (≈ 7451 BCE) are both inside the
  kernel range; the engine correctly returns finite positions.
- **Resolution:** Tests were inverted to assert that the engine returns a
  finite, in-range position for both JDs. This proves the engine handles
  deep-ancient epochs correctly rather than failing silently.
- **Resolved:** 2026-05-21

---

## Layer 4 - House Singularities

All 53 Layer 4 tests pass as of 2026-05-21.

`test_layer4k_body_on_cusp_placement_is_stable_and_deterministic` is now
executable: `house_of()` has been implemented in `moira.houses`, so the
former skip has lifted and the test passes on current `main`.

| Attack | Result |
|---|---|
| ASC near 0° Aries - no 360° leak | Pass |
| Observer at equator (all systems) | Pass |
| RAMC at 0°, 90°, 180°, 270° | Pass |
| MC near 0° - no 360° leak | Pass |
| Just below critical latitude - no fallback | Pass |
| Just above critical latitude - fallback or named error | Pass |
| 89° latitude - fallback or named error, no hang | Pass |
| MC/IC opposition invariant (all systems, 3 epochs) | Pass |
| ASC/DSC opposition invariant (all systems) | Pass |
| Circular cusp ordering (quadrant systems) | Pass |
| ASC near 359° - no negative or inverted cusps | Pass |
| Extreme latitudes (85°, 87°, 89.9°) - no hang | Pass |
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

When a new oracle-hostile audit is added:
1. State the authority surface explicitly (Swiss, ERFA, Horizons, USNO, etc.).
2. State whether the attack is on a direct substrate route or a public datetime path.
3. Declare any route-specific tolerance budget before interpreting a mismatch as an engine defect.
4. Re-run the combined campaign and update both the adversarial and full-campaign counts at the top.
