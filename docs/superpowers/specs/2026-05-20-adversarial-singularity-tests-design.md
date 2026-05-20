# Adversarial Singularity Test Suite — Design Spec

Date: 2026-05-20
Status: approved for implementation

---

## Purpose

These tests do not ask whether the engine is correct.
They ask whether the engine **stays sane at every seam where math traditionally
starts chewing the furniture**.

A test passes if the engine either:
- returns a finite, canonically normalized, structurally coherent answer, OR
- raises a named, honest exception

A test fails if the engine returns a **silently wrong value**: out-of-range
longitude, NaN, sign flip, branch-cut artifact, wrong root, or silent collapse
at a degenerate input.

---

## Files

```
tests/unit/test_adversarial_singularities.py
    Layer 1 — coordinate transform singularities
    Layer 2 — planetary geometry singularities
    Layer 3 — time system singularities
    Route equivalence attacks (cross-cutting)
    Boundary ownership doctrine attacks (cross-cutting)

tests/unit/test_adversarial_house_singularities.py
    Layer 4 — house and angular singularities
```

Each test section is labelled by doctrine layer so that a failure names which
layer of Moira's constitution cracked.

---

## Covenant Structures

Covenants are domain-specific. Do not apply the wrong invariant class to the
wrong domain.

### Spherical / vector transform covenants
- All outputs are finite (no NaN, no Inf)
- Longitude ∈ [0, 360), latitude ∈ [−90, 90], distance > 0 when defined
- **Round-trip is tested as angular vector separation**, not as lon/lat scalar
  agreement — especially near poles where longitude is semantically undefined
- At the poles: assert latitude = ±90° within tolerance; **do not assert
  longitude**; assert vector direction is recovered within angular tolerance
- Zero vector input must raise a named domain error, not proceed silently

### Ephemeris / time covenants
- All outputs are finite
- Coverage boundaries are respected (out-of-coverage raises a named exception)
- One-second continuity: result at t−1s and t+1s differs by at most the
  expected one-second motion scale for the body
- No discontinuous longitude wrap across any one-second step
- Speed scale is consistent with the body's known motion rate

### House / angular covenants
- All cusps and angles finite and in [0, 360)
- MC − IC = 180° mod 360 (opposition invariant)
- ASC − DSC = 180° mod 360 (opposition invariant)
- Cusp sequence is circularly coherent modulo 360 — no inversion when crossing 0°
- Fallback or named error at inputs beyond the valid domain (above critical
  latitude for semi-arc systems)
- Body-on-cusp house placement returns a stable, doctrine-consistent result

---

## Layer 1 — Coordinate Transform Singularities

### 1a — Ecliptic north pole
Input: unit vector pointing to the ecliptic north pole `[0, 0, 1]` in ecliptic
frame.

Covenants:
- latitude = +90° within tolerance
- longitude is finite and canonically normalized, but **not asserted for truth**
  (it is mathematically undefined)
- vector round-trip: `ecliptic_spherical → icrf → ecliptic_spherical` recovers
  the original direction within angular tolerance
- no NaN, no exception

### 1b — Ecliptic south pole
Same as 1a for `[0, 0, -1]`. Latitude = −90°. Same prohibition on asserting longitude.

### 1c — Aries point normalization
Input: unit vector along the vernal equinox `[1, 0, 0]`.

Covenants:
- longitude = 0° exactly (not 359.999…)
- latitude = 0° exactly

Twin case: call `ecliptic_to_icrf` with lon = 360°.
Covenant: result is identical to lon = 0°. The input 360° normalizes to 0°,
not preserved as 360°.

### 1d — Vector round-trip direction preservation
For a representative set of vectors (poles, cardinal ecliptic directions, high
latitudes), test:

```
v → (lon, lat, r) → v_recovered
```

Covenant: angular separation between `v` and `v_recovered` < 1e-10 degrees.
**Do not assert lon/lat scalar agreement at or near the poles.**

### 1e — Full longitude sweep round-trip
For every 1° of longitude at lat = 0°, 45°, 89°, **and −89°**:

```
ecliptic(lon, lat) → equatorial → ecliptic
```

Covenants:
- Longitude residual < 1e-10° at all latitudes
- Latitude residual < 1e-10° at all latitudes
- Special attention at lon = 0°, 90°, 180°, 270°, 359° (branch-cut exposure
  points)
- Test lat = −89° explicitly — pole-adjacent branch errors are often asymmetric

### 1f — Zero vector domain error
Input: `[0.0, 0.0, 0.0]` to any rectangular → spherical conversion.

Covenant: raises a named domain error. Must not silently return lon=0, lat=0,
distance=0 and proceed.

### 1g — Subnormal vector magnitude
Input: `[1e-300, 0.0, 0.0]` — valid direction, catastrophically small norm.

Covenants:
- Does not produce NaN or Inf from divide-by-norm underflow
- Either normalizes correctly to lon=0, lat=0, or raises a documented error

### 1h — Negative-epsilon longitude normalization
A computed or supplied longitude of −1e-15° should normalize to near 0° (not
to 360° − 1e-15°). Assert canonical policy: longitude ∈ [0, 360) means the
value is never exactly 360 and never negative.

---

## Layer 2 — Planetary Geometry Singularities

### 2a — Sun crossing 0° longitude (vernal equinox)
Find or construct the epoch closest to the vernal equinox (Sun lon ≈ 0°).
Query at t−1s, t, t+1s.

Covenants:
- Longitude is continuous across the 0° crossing — no wrap to 360°
- `assert_longitude` passes at all three epochs
- Speed sign and magnitude are consistent with forward motion

### 2b — Moon near perigee
Find a known perigee epoch. Query apparent position and light-time.

Covenants:
- Distance is finite and within the physical perigee range (< 357,000 km)
- Light-time correction is finite and convergent
- Position is continuous at t−1s, t, t+1s — no jump larger than the Moon's
  one-second angular rate

Framing: this is a **high-speed / close-distance stressor**, not a root
divergence probe. Assert finiteness and continuity, not correctness of
convergence mechanism.

### 2c — Retrograde station: Mercury, Venus, Mars
For a known retrograde station of each body:
- Query longitude and speed at t−1hr, station epoch, t+1hr (1-hour steps
  across the loop)

Covenants:
- Longitude is continuous across all steps — no jump
- Speed sign changes exactly once across the loop
- Retrograde flag (if exposed) changes only when signed speed crosses zero
- No NaN or domain error

### 2d — Body with ecliptic latitude exactly zero
Construct a synthetic ICRF vector whose ecliptic latitude component is exactly
0.0 (lying precisely in the ecliptic plane).

Covenants:
- Returned latitude = 0.0 exactly or within floating-point noise
- No sign instability — latitude does not flip between +ε and −ε on adjacent
  calls with the same input

### 2e — Mercury at superior conjunction
Find a known superior conjunction epoch for Mercury (body behind Sun).

Covenants:
- Position is finite
- Gravitational deflection (if active) does not produce NaN or Inf when source
  and deflector share a near-identical direction
- Mark deflection sub-test as **future-facing** if the gravitational deflection
  layer is not yet independently testable

### 2f — Speed continuity across the full retrograde loop
For Mercury, Venus, and Mars, sample longitude at 1-hour steps across a full
retrograde loop (pre-station to post-station).

Covenant: no step shows a longitude discontinuity larger than `body_speed_deg_per_hour × 1.5`.
The factor 1.5 is a generous allowance; actual steps should be much smaller.

### 2g — Zero-vector forbidden case (relative position)
If the engine can be asked for a body's position relative to itself, or if an
internal chaining step produces a zero relative vector, assert that no silent
spherical conversion of `[0,0,0]` proceeds.

Covenant: named error raised, or the condition is structurally impossible and
documented as such.

### 2h — EMB / Earth / Moon chaining consistency
Assert that:

```
position(SSB → Moon) == position(SSB → EMB) + position(EMB → Moon)
```

within tolerance `moira_approx(kind="distance")`.

This probes kernel chain integrity, not just individual segment correctness.

### 2i — Apparent geocentric longitude at the DE441 segment boundary
The DE441 segment boundary is at JD 2440432.5 TT. Query apparent geocentric
longitude of Sun, Moon, Mercury, and Mars at:

```
boundary − 1 s, boundary, boundary + 1 s
```

Covenant: no longitude discontinuity larger than the expected one-second rate.
This extends the existing raw boundary test into the apparent-position layer.

### 2j — Distance monotonic sanity near perigee / apogee
Over a narrow bracket (±1 hour) around a known lunar perigee and apogee:
- Compute distance at each point
- Assert that the distance derivative changes sign exactly once within the bracket
- Assert no distance jump

---

## Layer 3 — Time System Singularities

### 3a — Julian / Gregorian calendar boundary
Julian date Oct 4, 1582 and Gregorian date Oct 15, 1582 are consecutive days.
Assert their JD values differ by exactly 1.0.
Assert positions at those two epochs differ by approximately one day's planetary
motion, not zero (same day) and not orders of magnitude more (wrong JD).

### 3b — Year zero (1 BCE in astronomical convention)
Astronomical year 0 = 1 BCE. JD ≈ 1721057 (Jan 1, year 0).
This is inside DE441 coverage.

Covenants:
- Calendar → JD conversion does not bomb on `year = 0`
- Positions are finite and in valid ranges
- Inverse: JD back to calendar gives year = 0, month = 1, day = 1 within
  rounding

### 3c — JD = 0.0 (out of coverage)
Assert that querying any public planetary body at JD = 0.0 raises a named
exception (`OutOfRangeError`, `MissingKernelError`, or equivalent).
Must not silently return a position.

### 3d — Delta-T near its model zero-crossing
Identify the epoch where the active ΔT model yields ΔT ≈ 0 (near-zero, not
necessarily exact zero). Do not hardcode "1900" — derive it from the model
policy or declare it explicitly in the test.

Covenants:
- At that epoch, UT and TT queries give nearly identical positions (difference
  < one-second motion of the body)
- Sign of ΔT correction: at an epoch where ΔT > 0, TT is ahead of UT, so
  TT-based position is slightly ahead of UT-based position in longitude
- Assert sign coherence explicitly

### 3e — JD integer and JD .5 precision boundaries
Test positions at:
- A JD integer value (Julian noon, not civil midnight)
- The same value + 0.5 (civil midnight)
- Each ± 1 second

Covenants:
- No precision collapse at the integer/half-integer boundary
- One-second continuity holds at both boundary types
- Note explicitly in the test: JD integers are Julian noon, JD .5 is civil
  midnight — this is a classic documentation trapdoor

### 3f — Leap day rules
Test that calendar arithmetic correctly handles:
- 1600: leap year under Gregorian rules
- 1700, 1800, 1900: not leap years under Gregorian (but are under Julian)
- 2000: leap year
- Any year divisible by 4 in the Julian calendar

Covenant: the day count between Dec 31 and Mar 1 of each test year is correct
(28 or 29 days in February). Assert via JD differences.

### 3g — Deep historical BCE calendar conversion
For several epochs well before JD 0 (e.g., −1000000 JD), assert:
- Calendar → JD → calendar round-trips within 1 day
- No integer overflow or sign error in year arithmetic

This is separate from ephemeris coverage. The calendar can be valid at epochs
the ephemeris does not cover.

### 3h — Split JD precision
Compare a position computed from a single JD float against one computed from
`jd1 + jd2` where `jd2` is a sub-second offset.

Test around J2000 and a far-future epoch. Covenant: results agree to within
the expected floating-point precision of a single JD representation.

### 3i — TT / UT round-trip
Starting from a UT Julian Day, convert to TT and back.

Covenant: round-trip residual < 1e-6 seconds (well within the ΔT model
precision). Test at J2000, ~1900 (near-zero ΔT), and a deep historical epoch.

---

## Layer 4 — House and Angular Singularities

### 4a — ASC near 0° Aries
Find or construct an epoch + observer where the computed ASC ≈ 0°.
Query houses for Placidus, Whole Sign, and Porphyry.

Covenant: all cusps finite and in [0, 360). ASC = 0°, not 360°.

### 4b — Observer at exactly 0° latitude (equator)
Compute houses for all supported systems at lat = 0°, lon = 0°, for J2000.

Covenants:
- No division by sin(lat) blow-up
- All cusps finite and in [0, 360)
- Opposition invariants hold

### 4c-4d — RAMC at 0°, 90°, 180°, 270°
For each cardinal RAMC value, find or construct a matching observer + epoch.

Covenants:
- All cusps finite and in [0, 360)
- No zero-crossing artifact in RAMC-dependent cusp formulas
- MC direction coherent with RAMC value

### 4e — MC = 0° exactly
Find or construct an epoch + observer where MC ≈ 0°.

Covenant: MC returned as 0° (not 360°). Opposition invariant: IC = 180°.

### 4f — Observer latitude near critical latitude
Three sub-cases per system (Placidus, Koch):
- Observer just below the derived critical latitude for the given epoch
- Observer just above the derived critical latitude for the given epoch
- Observer at 89° (likely beyond semi-arc validity for most epochs)

Covenants (per sub-case):
- Below: system computes normally, cusps valid
- Above: fallback activates or named error raised — no silent wrong cusps
- 89°: may be beyond critical, behavior must match fallback doctrine

Note: critical latitude is epoch-dependent and obliquity-dependent. Derive it
from the engine's own `_compute_critical_latitude` or equivalent, not from a
hardcoded constant.

### 4g — MC / IC opposition invariant (universal)
For every house system, for a sweep of observer positions and epochs:

Covenant: `(IC - MC) mod 360 == 180°` within floating-point tolerance.

### 4h — ASC / DSC opposition invariant (universal)
Same sweep.

Covenant: `(DSC - ASC) mod 360 == 180°` within floating-point tolerance.

### 4i — Cusp ordering modulo 360
For every house system, assert that the cusp sequence is circularly coherent:
each cusp is reachable from the previous one by moving forward in longitude,
modulo 360°. Test explicitly with ASC near 359°.

### 4j — Whole Sign / Equal / Porphyry at ASC near 359.999°
Construct an observer + epoch yielding ASC = 359.99°.

Covenants:
- Whole Sign: House 1 starts at 330° (the Pisces sign boundary), not at 359.99°
  and not at 0°. The sign containing the ASC governs House 1; ASC itself is not
  the cusp.
- Equal / Porphyry: House 1 starts at 359.99° (ASC-anchored); House 2 at
  359.99° + 30° = 29.99°, which must normalize correctly across the 0° boundary
- No cusp returned as a negative value
- No cusp inversion across the 0° boundary

### 4k — Body exactly on a house cusp
Construct a case where a body's longitude matches a cusp longitude within
floating-point resolution.

Covenant: house placement returns a stable, doctrine-consistent result. The
test does not dictate which house — it asserts the result is non-NaN,
non-negative, and within [1, 12], and that the same call with the same input
returns the same house.

### 4l — MC approaching ASC at extreme latitude
At very high observer latitude, some systems produce angles that crowd or
coincide.

Covenants:
- Engine does not hang or produce NaN
- Either returns finite coherent angles with opposition invariants intact, or
  raises a named error with doctrine-consistent behavior

---

## Cross-Cutting: Route Equivalence Attacks

These attacks assert that multiple independent paths to the same result agree.

| Attack | Paths compared |
|--------|---------------|
| RE-1 | Direct kernel segment vs chained route (e.g., SSB→Mercury vs SSB→1→199) |
| RE-2 | Native C++ evaluator vs public `SpkReader` Python path |
| RE-3 | Single JD float vs split `jd1 + jd2` with sub-second `jd2` |
| RE-4 | Geocentric → topocentric composition vs direct topocentric call |
| RE-5 | `ecliptic → equatorial → ecliptic` round-trip at non-degenerate positions |

Tolerance for all route equivalence tests: `moira_approx(kind="longitude")`.

---

## Cross-Cutting: Boundary Ownership Doctrine

These attacks assert that the engine has a **constitution** at exact boundaries,
not just vibes.

| Boundary | Covenant |
|----------|---------|
| Longitude = 0° exactly | Returned as 0°, not 360° |
| Longitude = 360° input | Normalized to 0° |
| House cusp == body longitude | Placement doctrine stable and repeatable |
| Speed = 0 exactly | No sign-flip artifact; retrograde flag does not flicker |
| Latitude = +90° | Returns +90°; longitude not asserted |
| Latitude = −90° | Returns −90°; longitude not asserted |
| Distance = 0 (invalid) | Named domain error; no silent spherical conversion |
| JD at segment start/end | Position continuous; no discontinuous jump |
| JD at calendar reform boundary | Calendar arithmetic coherent; JD difference = 1 day |

---

## Testing Liturgy Compliance

All tests must comply with the Moira Testing Liturgy (CLAUDE.md §19):

- Use `moira_engine` session-scoped fixture; never construct `Moira()` inside a
  test function
- Use `moira_approx(kind=...)` for tolerances, never hardcoded floats
- Use `assert_longitude` for all [0, 360) range assertions
- Use `golden` / `snapshot` only for regression baselines, not as primary proof
- Follow the three-phase structure: **Summon → Witness → Covenant**

Where an attack requires a synthetic vector rather than a live ephemeris query,
the test may construct the vector directly; it does not require `moira_engine`.

---

## Success Criteria

The suite is complete when:
1. Every attack in every layer has a corresponding test
2. Each test has explicit covenants matching the domain-specific covenant structure
3. Any new failures discovered are logged as issues against the relevant engine layer
4. Tests that reveal real breaks are left failing until the underlying defect is
   fixed — they are not patched to pass
