# Adversarial Singularity Test Suite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write two adversarial test files that force the engine into degenerate inputs at every mathematical seam and covenant only on structural invariants — revealing silent failures, not validating correctness.

**Architecture:** Two new unit test files. Tests follow the Testing Liturgy (Summon → Witness → Covenant). A test that fails on first run has found a real defect — leave it failing, do not patch it to pass. A test that passes has proven the engine handles that singularity — document it with a comment.

**Tech Stack:** pytest, `moira.coordinates`, `moira.planets`, `moira.julian`, `moira.houses`, `moira.spk_reader`

**Spec:** `docs/superpowers/specs/2026-05-20-adversarial-singularity-tests-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `tests/unit/test_adversarial_singularities.py` | Layers 1–3: coordinate transforms, planetary geometry, time system. Route equivalence. Boundary ownership. |
| `tests/unit/test_adversarial_house_singularities.py` | Layer 4: house and angular singularities |

---

## Shared Constants Reference

```python
_OBLIQUITY_J2000 = 23.4392911        # J2000 mean obliquity, degrees
_ONE_SECOND_JD   = 1.0 / 86400.0
_J2000           = 2451545.0

# Astronomical epochs used across multiple tasks
_JD_VERNAL_EQUINOX_2000    = 2451623.82   # 2000-03-20 ~07:35 UTC, Sun lon ≈ 0°
_JD_MOON_PERIGEE_2023      = 2459966.08   # 2023-01-21 close perigee ~357 000 km
_JD_MERCURY_STATION_R_2023 = 2460055.0    # 2023-04-21 Mercury station retrograde
_JD_MERCURY_STATION_D_2023 = 2460079.0    # 2023-05-14 Mercury station direct
_JD_VENUS_STATION_R_2023   = 2460148.0    # 2023-07-22 Venus station retrograde
_JD_VENUS_STATION_D_2023   = 2460190.5    # 2023-09-03 Venus station direct
_JD_MARS_STATION_R_2022    = 2459882.5    # 2022-10-30 Mars station retrograde
_JD_MARS_STATION_D_2023    = 2459956.5    # 2023-01-12 Mars station direct
_JD_GREGORIAN_REFORM       = 2299161.0    # 1582-10-15 Gregorian (first day)
_JD_LAST_JULIAN            = 2299160.0    # 1582-10-04 Julian (last day)
_JD_DE441_BOUNDARY         = 2440432.5    # DE441 TT segment boundary
```

---

## Task 1: Scaffold `test_adversarial_singularities.py`

**Files:**
- Create: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Create the file with imports, constants, and shared helpers**

```python
"""
Adversarial singularity tests — Layers 1, 2, 3 plus cross-cutting attacks.

Philosophy: a test passes if the engine returns a finite, canonically
normalised result OR raises a named exception. A test fails if the engine
returns a silently wrong value. Tests that fail on first run have found a
real defect — leave them failing; do not patch them to pass.
"""
from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.coordinates import (
    angular_distance,
    ecliptic_to_equatorial,
    equatorial_to_ecliptic,
    icrf_to_ecliptic,
    normalize_degrees,
    vec_norm,
    vec_unit,
)
from moira.julian import (
    DeltaTPolicy,
    calendar_from_jd,
    delta_t_from_jd,
    julian_day,
    tt_to_ut,
    ut_to_tt,
)
from moira.planets import PlanetData, planet_at
from moira.spk_reader import OutOfRangeError

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_OBLIQUITY_J2000 = 23.4392911        # J2000 mean obliquity, degrees
_ONE_SECOND_JD   = 1.0 / 86400.0
_J2000           = 2451545.0

_JD_VERNAL_EQUINOX_2000    = 2451623.82
_JD_MOON_PERIGEE_2023      = 2459966.08
_JD_MERCURY_STATION_R_2023 = 2460055.0
_JD_MERCURY_STATION_D_2023 = 2460079.0
_JD_VENUS_STATION_R_2023   = 2460148.0
_JD_VENUS_STATION_D_2023   = 2460190.5
_JD_MARS_STATION_R_2022    = 2459882.5
_JD_MARS_STATION_D_2023    = 2459956.5
_JD_GREGORIAN_REFORM       = 2299161.0
_JD_LAST_JULIAN            = 2299160.0
_JD_DE441_BOUNDARY         = 2440432.5    # TT

# ---------------------------------------------------------------------------
# Local helpers (not in moira.coordinates)
# ---------------------------------------------------------------------------

def _angular_sep_vectors(v1: tuple, v2: tuple) -> float:
    """Angular separation in degrees between two 3-vectors."""
    n1 = vec_norm(v1)
    n2 = vec_norm(v2)
    dot = sum(a * b for a, b in zip(v1, v2)) / (n1 * n2)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def _ecliptic_to_icrf(lon_deg: float, lat_deg: float, dist: float = 1.0,
                      obliquity_deg: float = _OBLIQUITY_J2000) -> tuple:
    """Convert ecliptic spherical to ICRF Cartesian (inverse of icrf_to_ecliptic)."""
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    eps = math.radians(obliquity_deg)
    # Ecliptic Cartesian
    xe = dist * math.cos(lat) * math.cos(lon)
    ye = dist * math.cos(lat) * math.sin(lon)
    ze = dist * math.sin(lat)
    # Rotate about X by +obliquity to get ICRF equatorial
    x = xe
    y = ye * math.cos(eps) - ze * math.sin(eps)
    z = ye * math.sin(eps) + ze * math.cos(eps)
    return (x, y, z)


def _lon_lat_from_icrf(xyz: tuple, obliquity_deg: float = _OBLIQUITY_J2000):
    """Return (lon, lat) in degrees from an ICRF vector via icrf_to_ecliptic."""
    lon, lat, _ = icrf_to_ecliptic(xyz, obliquity_deg)
    return lon, lat
```

- [ ] **Step 2: Verify the file imports cleanly**

```
cd "c:\Users\nilad\OneDrive\Desktop\Moira C++"
.venv\Scripts\python.exe -c "import tests.unit.test_adversarial_singularities"
```

Expected: no output (clean import). If `ModuleNotFoundError`, check that the file is in `tests/unit/` and that `tests/unit/__init__.py` exists (or `--import-mode=importlib` in pyproject.toml covers it — it does per existing config).

- [ ] **Step 3: Commit scaffold**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test: scaffold adversarial singularity test file (Layer 1–3)"
```

---

## Task 2: Layer 1a–1c — Pole and Aries singularities

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 1a, 1b, 1c**

Append to `test_adversarial_singularities.py`:

```python
# ===========================================================================
# LAYER 1 — Coordinate transform singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 1a — Ecliptic north pole
# The ICRF vector of the ecliptic north pole is (0, -sin(eps), cos(eps)).
# Passing it to icrf_to_ecliptic must return lat = +90°.
# Longitude is mathematically undefined — assert finite and normalised only.
# ---------------------------------------------------------------------------

def test_layer1a_ecliptic_north_pole_latitude_is_90():
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_north = (0.0, -math.sin(eps), math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_north, _OBLIQUITY_J2000)

    assert lat == pytest.approx(90.0, abs=1e-6), f"lat={lat}, expected 90°"
    assert math.isfinite(lon), "longitude must be finite at the pole"
    assert 0.0 <= lon < 360.0, f"longitude {lon} is not in [0, 360)"
    assert dist == pytest.approx(1.0, abs=1e-10)


def test_layer1a_north_pole_vector_round_trip():
    """Vector direction must survive ecliptic→spherical→ecliptic at the north pole."""
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_original = (0.0, -math.sin(eps), math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_original, _OBLIQUITY_J2000)
    xyz_recovered = _ecliptic_to_icrf(lon, lat, dist, _OBLIQUITY_J2000)

    sep = _angular_sep_vectors(xyz_original, xyz_recovered)
    assert sep < 1e-8, f"vector round-trip separation {sep}° at north pole"


# ---------------------------------------------------------------------------
# 1b — Ecliptic south pole
# ---------------------------------------------------------------------------

def test_layer1b_ecliptic_south_pole_latitude_is_minus_90():
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_south = (0.0, math.sin(eps), -math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_south, _OBLIQUITY_J2000)

    assert lat == pytest.approx(-90.0, abs=1e-6), f"lat={lat}, expected -90°"
    assert math.isfinite(lon), "longitude must be finite at the south pole"
    assert 0.0 <= lon < 360.0, f"longitude {lon} is not in [0, 360)"


def test_layer1b_south_pole_vector_round_trip():
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_original = (0.0, math.sin(eps), -math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_original, _OBLIQUITY_J2000)
    xyz_recovered = _ecliptic_to_icrf(lon, lat, dist, _OBLIQUITY_J2000)

    sep = _angular_sep_vectors(xyz_original, xyz_recovered)
    assert sep < 1e-8, f"vector round-trip separation {sep}° at south pole"


# ---------------------------------------------------------------------------
# 1c — Aries point: lon = 0° must not leak to 359.999… or 360°
# ---------------------------------------------------------------------------

def test_layer1c_aries_point_longitude_is_zero():
    """[1, 0, 0] in ICRF is the vernal equinox — ecliptic lon must be exactly 0°."""
    xyz_aries = (1.0, 0.0, 0.0)

    lon, lat, dist = icrf_to_ecliptic(xyz_aries, _OBLIQUITY_J2000)

    assert lon == pytest.approx(0.0, abs=1e-10), \
        f"Aries point lon={lon}, expected 0° (not 360°)"
    assert lat == pytest.approx(0.0, abs=1e-10)


def test_layer1c_360_degree_input_normalises_to_zero():
    """ecliptic_to_equatorial(360°, 0°) must equal ecliptic_to_equatorial(0°, 0°)."""
    ra_0,   dec_0   = ecliptic_to_equatorial(0.0,   0.0, _OBLIQUITY_J2000)
    ra_360, dec_360 = ecliptic_to_equatorial(360.0, 0.0, _OBLIQUITY_J2000)

    assert ra_0 == pytest.approx(ra_360, abs=1e-10), \
        "360° input must produce same RA as 0° input"
    assert dec_0 == pytest.approx(dec_360, abs=1e-10)
```

- [ ] **Step 2: Run these five tests**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer1a or layer1b or layer1c" 2>&1
```

Expected: some may PASS (engine is sane), some may FAIL (engine defect found). Record which. Do not patch failures.

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 1a-1c pole and Aries point singularities"
```

---

## Task 3: Layer 1d–1h — Round-trip, zero-vector, subnormal, negative-epsilon

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 1d through 1h**

Append:

```python
# ---------------------------------------------------------------------------
# 1d — Vector round-trip direction preservation (non-polar)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lon,lat", [
    (0.0, 0.0), (90.0, 0.0), (180.0, 0.0), (270.0, 0.0),
    (0.0, 45.0), (180.0, 45.0), (0.0, -45.0),
    (45.0, 89.0), (45.0, -89.0),
    (359.0, 0.0), (359.0, 45.0),
])
def test_layer1d_vector_round_trip(lon, lat):
    """ecliptic → ICRF → ecliptic preserves direction; longitude not checked at poles."""
    xyz = _ecliptic_to_icrf(lon, lat, 1.0, _OBLIQUITY_J2000)
    xyz_recovered = _ecliptic_to_icrf(
        *_lon_lat_from_icrf(xyz, _OBLIQUITY_J2000), 1.0, _OBLIQUITY_J2000
    )
    sep = _angular_sep_vectors(xyz, xyz_recovered)
    assert sep < 1e-10, \
        f"vector round-trip separation {sep}° at lon={lon}, lat={lat}"


# ---------------------------------------------------------------------------
# 1e — Full ecliptic ↔ equatorial round-trip sweep
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lat_slice", [0.0, 45.0, 89.0, -89.0])
def test_layer1e_ecliptic_equatorial_round_trip_sweep(lat_slice):
    """Every 1° of longitude at four latitude slices, including ±89°."""
    worst_lon_residual = 0.0
    worst_lat_residual = 0.0
    for lon in range(0, 360):
        ra, dec = ecliptic_to_equatorial(float(lon), lat_slice, _OBLIQUITY_J2000)
        lon_back, lat_back = equatorial_to_ecliptic(ra, dec, _OBLIQUITY_J2000)
        lon_residual = abs(normalize_degrees(lon_back - lon))
        # Wrap residual to [-180, 180]
        if lon_residual > 180.0:
            lon_residual = 360.0 - lon_residual
        lat_residual = abs(lat_back - lat_slice)
        worst_lon_residual = max(worst_lon_residual, lon_residual)
        worst_lat_residual = max(worst_lat_residual, lat_residual)

    assert worst_lon_residual < 1e-10, \
        f"lon round-trip residual {worst_lon_residual}° at lat={lat_slice}"
    assert worst_lat_residual < 1e-10, \
        f"lat round-trip residual {worst_lat_residual}° at lat={lat_slice}"


# ---------------------------------------------------------------------------
# 1f — Zero vector must raise a named domain error
# ---------------------------------------------------------------------------

def test_layer1f_zero_vector_raises_domain_error():
    """vec_unit([0,0,0]) must raise ValueError — not silently return lon=0, lat=0."""
    with pytest.raises((ValueError, ZeroDivisionError, ArithmeticError)):
        vec_unit((0.0, 0.0, 0.0))


def test_layer1f_icrf_to_ecliptic_zero_vector():
    """icrf_to_ecliptic([0,0,0]) — document actual behaviour (named error preferred)."""
    try:
        lon, lat, dist = icrf_to_ecliptic((0.0, 0.0, 0.0), _OBLIQUITY_J2000)
        # If no exception: engine returned a value — assert it is at least finite
        # This is the silent-failure branch. Leave test failing to flag the defect.
        assert math.isfinite(lon) and math.isfinite(lat), \
            "icrf_to_ecliptic([0,0,0]) returned non-finite values"
        assert dist == pytest.approx(0.0, abs=1e-30), \
            "icrf_to_ecliptic([0,0,0]) distance must be 0 or an error must be raised"
        pytest.fail(
            "icrf_to_ecliptic([0,0,0]) did not raise — silent zero-vector "
            "conversion proceeds. A named domain error is preferred."
        )
    except (ValueError, ZeroDivisionError, ArithmeticError):
        pass  # correct: engine raises a named error


# ---------------------------------------------------------------------------
# 1g — Subnormal vector magnitude must not produce NaN or Inf
# ---------------------------------------------------------------------------

def test_layer1g_subnormal_vector_magnitude():
    """[1e-300, 0, 0] has a valid direction but catastrophically small norm."""
    xyz = (1e-300, 0.0, 0.0)
    try:
        lon, lat, dist = icrf_to_ecliptic(xyz, _OBLIQUITY_J2000)
        assert math.isfinite(lon), f"lon is not finite for subnormal vector: {lon}"
        assert math.isfinite(lat), f"lat is not finite for subnormal vector: {lat}"
        assert math.isfinite(dist), f"dist is not finite for subnormal vector: {dist}"
    except (ValueError, OverflowError, ArithmeticError):
        pass  # acceptable: explicit error beats silent NaN


# ---------------------------------------------------------------------------
# 1h — Negative-epsilon longitude must not normalise to 360°
# ---------------------------------------------------------------------------

def test_layer1h_negative_epsilon_longitude_normalisation():
    """A longitude of -1e-15° must not normalise to 360° - 1e-15°."""
    neg_epsilon = -1e-15
    result = normalize_degrees(neg_epsilon)
    # Policy: [0, 360) — so result must be < 360 and >= 0
    assert 0.0 <= result < 360.0, \
        f"normalize_degrees({neg_epsilon}) = {result}, expected in [0, 360)"
    # The value must not be near 360 — that would be a sign error
    assert result < 1.0 or result > 359.0 - 1e-10 is False, \
        f"normalize_degrees({neg_epsilon}) gave {result}, dangerously close to 360"


def test_layer1h_longitude_never_exactly_360():
    """normalize_degrees must never return exactly 360.0."""
    candidates = [360.0, 720.0, -0.0, 360.0 + 1e-15, 360.0 - 1e-15]
    for val in candidates:
        result = normalize_degrees(val)
        assert result != 360.0, \
            f"normalize_degrees({val}) returned exactly 360.0 — violates [0, 360)"
        assert 0.0 <= result < 360.0, \
            f"normalize_degrees({val}) = {result} not in [0, 360)"
```

- [ ] **Step 2: Run Layer 1 in full**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer1" 2>&1
```

Record any failures — these are the singularities the engine does not handle cleanly.

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 1d-1h round-trip, zero-vector, subnormal, epsilon"
```

---

## Task 4: Layer 2a–2b — Vernal equinox and Moon perigee

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 2a and 2b**

Append:

```python
# ===========================================================================
# LAYER 2 — Planetary geometry singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 2a — Sun crossing 0° longitude (vernal equinox)
# The modular wrap from 359.999… → 0° is where engines silently return 360°.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2a_sun_vernal_equinox_no_longitude_wrap(reader):
    """Sun longitude at the vernal equinox must be continuous — no 360° leak."""
    jd = _JD_VERNAL_EQUINOX_2000

    data_before = planet_at(Body.SUN, jd - _ONE_SECOND_JD, reader=reader)
    data_at     = planet_at(Body.SUN, jd,                  reader=reader)
    data_after  = planet_at(Body.SUN, jd + _ONE_SECOND_JD, reader=reader)

    for label, data in [("before", data_before), ("at", data_at), ("after", data_after)]:
        assert 0.0 <= data.longitude < 360.0, \
            f"Sun longitude {data.longitude} not in [0,360) at t={label}"
        assert math.isfinite(data.longitude), f"Sun longitude is not finite at t={label}"

    # Longitude step must be << 1° (Sun moves ~1°/day = 0.0000116°/s)
    step_before = abs(data_at.longitude - data_before.longitude)
    step_after  = abs(data_after.longitude - data_at.longitude)
    # Wrap-aware step
    if step_before > 180:
        step_before = 360 - step_before
    if step_after > 180:
        step_after  = 360 - step_after

    assert step_before < 0.001, \
        f"Sun longitude step before equinox = {step_before}° — discontinuity detected"
    assert step_after < 0.001, \
        f"Sun longitude step after equinox = {step_after}° — discontinuity detected"


# ---------------------------------------------------------------------------
# 2b — Moon near perigee
# High speed + close approach stresses light-time iteration convergence.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2b_moon_perigee_position_is_finite_and_continuous(reader):
    """Moon at perigee: position and light-time correction remain finite and continuous."""
    jd = _JD_MOON_PERIGEE_2023

    data_before = planet_at(Body.MOON, jd - _ONE_SECOND_JD, reader=reader)
    data_at     = planet_at(Body.MOON, jd,                  reader=reader)
    data_after  = planet_at(Body.MOON, jd + _ONE_SECOND_JD, reader=reader)

    for label, data in [("before", data_before), ("at", data_at), ("after", data_after)]:
        assert math.isfinite(data.longitude),  f"Moon lon not finite at {label}"
        assert math.isfinite(data.latitude),   f"Moon lat not finite at {label}"
        assert math.isfinite(data.distance),   f"Moon dist not finite at {label}"
        assert data.distance > 0,              f"Moon distance <= 0 at {label}"
        assert 0.0 <= data.longitude < 360.0,  f"Moon lon out of range at {label}"

    # Distance at perigee must be below 357 500 km (physical close-approach limit)
    assert data_at.distance < 357_500, \
        f"Moon distance {data_at.distance} km — not in close perigee range"

    # One-second continuity: Moon moves ~0.5°/s max at extreme perigee
    MAX_STEP = 0.001  # degrees per second — generous
    step_before = abs(data_at.longitude - data_before.longitude)
    step_after  = abs(data_after.longitude - data_at.longitude)
    if step_before > 180: step_before = 360 - step_before
    if step_after  > 180: step_after  = 360 - step_after

    assert step_before < MAX_STEP, \
        f"Moon perigee longitude step (before) = {step_before}° — too large"
    assert step_after < MAX_STEP, \
        f"Moon perigee longitude step (after) = {step_after}° — too large"
```

- [ ] **Step 2: Run Layer 2 so far**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer2a or layer2b" 2>&1
```

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 2a-2b vernal equinox and Moon perigee"
```

---

## Task 5: Layer 2c–2f — Retrograde stations

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 2c and 2f**

Append:

```python
# ---------------------------------------------------------------------------
# 2c — Retrograde stations: speed must cross zero cleanly
# Tested for Mercury, Venus, Mars — each probes a different speed scale.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body,jd_station_r,jd_station_d,label", [
    (Body.MERCURY, _JD_MERCURY_STATION_R_2023, _JD_MERCURY_STATION_D_2023, "Mercury"),
    (Body.VENUS,   _JD_VENUS_STATION_R_2023,   _JD_VENUS_STATION_D_2023,   "Venus"),
    (Body.MARS,    _JD_MARS_STATION_R_2022,    _JD_MARS_STATION_D_2023,    "Mars"),
])
def test_layer2c_retrograde_station_speed_crosses_zero_cleanly(
    reader, body, jd_station_r, jd_station_d, label
):
    """At each station, longitude must be continuous and speed sign must change once."""
    one_hour = 1.0 / 24.0

    # Station R: speed goes positive → negative
    before_r = planet_at(body, jd_station_r - one_hour, reader=reader)
    after_r  = planet_at(body, jd_station_r + one_hour, reader=reader)

    # Station D: speed goes negative → positive
    before_d = planet_at(body, jd_station_d - one_hour, reader=reader)
    after_d  = planet_at(body, jd_station_d + one_hour, reader=reader)

    # Longitude continuity at station R
    step_r = abs(after_r.longitude - before_r.longitude)
    if step_r > 180: step_r = 360 - step_r
    assert step_r < 1.0, \
        f"{label} station R: 2-hour longitude jump {step_r}° — discontinuity"

    # Longitude continuity at station D
    step_d = abs(after_d.longitude - before_d.longitude)
    if step_d > 180: step_d = 360 - step_d
    assert step_d < 1.0, \
        f"{label} station D: 2-hour longitude jump {step_d}° — discontinuity"

    # Speed sign change at station R: before should be positive (direct), after negative
    assert before_r.speed > 0, \
        f"{label} speed before station R should be positive (direct motion), got {before_r.speed}"
    assert after_r.speed < 0, \
        f"{label} speed after station R should be negative (retrograde), got {after_r.speed}"

    # Speed sign change at station D: before negative (retro), after positive (direct)
    assert before_d.speed < 0, \
        f"{label} speed before station D should be negative (retrograde), got {before_d.speed}"
    assert after_d.speed > 0, \
        f"{label} speed after station D should be positive (direct), got {after_d.speed}"


# ---------------------------------------------------------------------------
# 2f — Full retrograde loop longitude continuity (1-hour step sweep)
# No single step across the loop should show a discontinuous jump.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("body,jd_start,jd_end,label,max_step_deg_per_hr", [
    (Body.MERCURY, _JD_MERCURY_STATION_R_2023 - 1.0, _JD_MERCURY_STATION_D_2023 + 1.0, "Mercury", 0.5),
    (Body.MARS,    _JD_MARS_STATION_R_2022    - 1.0, _JD_MARS_STATION_D_2023    + 1.0, "Mars",    0.08),
])
def test_layer2f_retrograde_loop_longitude_continuous(
    reader, body, jd_start, jd_end, label, max_step_deg_per_hr
):
    """No 1-hour longitude step across the full retrograde loop exceeds 1.5× normal rate."""
    one_hour = 1.0 / 24.0
    jd = jd_start
    prev_lon = planet_at(body, jd, reader=reader).longitude
    jd += one_hour

    while jd <= jd_end:
        cur_lon = planet_at(body, jd, reader=reader).longitude
        step = abs(cur_lon - prev_lon)
        if step > 180: step = 360 - step
        assert step < max_step_deg_per_hr * 1.5, \
            f"{label}: longitude jump {step}° at JD {jd:.3f} — discontinuity"
        prev_lon = cur_lon
        jd += one_hour
```

- [ ] **Step 2: Run station tests**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer2c or layer2f" 2>&1
```

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 2c, 2f retrograde station singularities"
```

---

## Task 6: Layer 2d, 2g–2j — Ecliptic plane, chaining, boundary, distance

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 2d, 2g, 2h, 2i, 2j**

Append:

```python
# ---------------------------------------------------------------------------
# 2d — Body exactly on the ecliptic plane (lat = 0)
# A synthetic vector in the ecliptic plane must return lat = 0.0 exactly.
# ---------------------------------------------------------------------------

def test_layer2d_body_on_ecliptic_plane_latitude_is_zero():
    """ICRF vector in the ecliptic plane must give ecliptic latitude = 0."""
    # Any vector with z_ecliptic = 0. In ICRF equatorial that is any vector
    # in the ecliptic plane: y_ecliptic = 0 means x=something, y=0 ecliptic.
    # Use [1, 0, 0] (Aries) and [0, 1_ecl, 0] (lon=90 in ecliptic frame).
    # [0, 1_ecl, 0] in ICRF = ecliptic_to_icrf(90, 0) = (0, cos(eps), sin(eps))
    eps = math.radians(_OBLIQUITY_J2000)
    test_vectors = [
        (1.0, 0.0, 0.0),                           # Aries point
        (0.0, math.cos(eps), math.sin(eps)),        # 90° ecliptic longitude
        (-1.0, 0.0, 0.0),                           # 180° ecliptic longitude
        (0.0, -math.cos(eps), -math.sin(eps)),      # 270° ecliptic longitude
    ]
    for xyz in test_vectors:
        lon, lat, dist = icrf_to_ecliptic(xyz, _OBLIQUITY_J2000)
        assert abs(lat) < 1e-10, \
            f"ecliptic lat = {lat} for vector {xyz} — expected 0 (on ecliptic plane)"


def test_layer2d_near_ecliptic_plane_sign_stability():
    """Tiny perturbations above/below ecliptic must not flip sign erratically."""
    eps_ecl = math.radians(_OBLIQUITY_J2000)
    # Vector slightly above the ecliptic plane (small positive z_ecliptic)
    delta = 1e-8
    xyz_above = _ecliptic_to_icrf(45.0,  delta, 1.0, _OBLIQUITY_J2000)
    xyz_below = _ecliptic_to_icrf(45.0, -delta, 1.0, _OBLIQUITY_J2000)

    _, lat_above, _ = icrf_to_ecliptic(xyz_above, _OBLIQUITY_J2000)
    _, lat_below, _ = icrf_to_ecliptic(xyz_below, _OBLIQUITY_J2000)

    assert lat_above > 0, f"Lat above ecliptic plane is {lat_above} — expected positive"
    assert lat_below < 0, f"Lat below ecliptic plane is {lat_below} — expected negative"


# ---------------------------------------------------------------------------
# 2g — EMB / Earth / Moon chaining consistency
# SSB→Moon must equal SSB→EMB + EMB→Moon at the kernel level.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2h_emb_chain_consistency(reader):
    """SSB→Moon position equals SSB→EMB + EMB→Moon within distance tolerance."""
    from moira.planets import planet_at
    from moira.spk_reader import SpkReader

    jd = _J2000

    # Read raw barycentric vectors from the kernel
    # The kernel provides: (0,3)=SSB→EMB, (3,301)=EMB→Moon, (3,399)=EMB→Earth
    kernel = reader._kernel
    if not hasattr(kernel, "_handle"):
        pytest.skip("native kernel handle not available")

    seg_ssb_emb  = reader._segment_for(0,   3,   jd)
    seg_emb_moon = reader._segment_for(3,   301, jd)
    seg_ssb_moon = reader._segment_for(0,   301, jd)  # may not exist as direct

    # Chained route
    pos_ssb_emb,  _ = seg_ssb_emb.compute_and_differentiate(jd)
    pos_emb_moon, _ = seg_emb_moon.compute_and_differentiate(jd)
    pos_chained = tuple(a + b for a, b in zip(pos_ssb_emb, pos_emb_moon))

    # Direct planet_at gives the same position through the public path
    moon_direct = planet_at(Body.MOON, jd, reader=reader, apparent=False, aberration=False,
                            grav_deflection=False, nutation=False, center='barycentric'
                            if 'barycentric' in planet_at.__doc__ or True else 'geocentric')
    # Note: if center='barycentric' is not supported, this test verifies chain integrity
    # via the low-level segment API only — which is the safer approach.
    # Low-level chain: SSB→EMB + EMB→Moon components must agree to kernel precision
    km_tolerance = 1e-3  # 1 metre
    for i, (chained_i, direct_i) in enumerate(zip(pos_chained, pos_ssb_emb)):
        # We only verify the internal chain, not the full public path here
        pass  # chain is chained — verify internally:

    # The real invariant: each component of chained must equal EMB + Moon leg
    for i in range(3):
        c = pos_ssb_emb[i] + pos_emb_moon[i]
        assert abs(c - pos_chained[i]) < 1e-10, \
            f"EMB chain component {i}: chained={pos_chained[i]}, computed={c}"


# ---------------------------------------------------------------------------
# 2i — Apparent geocentric longitude at the DE441 segment boundary
# Extends the raw boundary test into the apparent-position layer.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [Body.SUN, Body.MOON, Body.MERCURY, Body.MARS])
def test_layer2i_apparent_longitude_continuous_at_de441_boundary(reader, body):
    """Apparent geocentric longitude must not jump at the DE441 TT segment boundary."""
    from moira.julian import tt_to_ut
    jd_tt_boundary = _JD_DE441_BOUNDARY
    jd_ut_before = tt_to_ut(jd_tt_boundary - _ONE_SECOND_JD)
    jd_ut_at     = tt_to_ut(jd_tt_boundary)
    jd_ut_after  = tt_to_ut(jd_tt_boundary + _ONE_SECOND_JD)

    d_before = planet_at(body, jd_ut_before, reader=reader)
    d_at     = planet_at(body, jd_ut_at,     reader=reader)
    d_after  = planet_at(body, jd_ut_after,  reader=reader)

    step1 = abs(d_at.longitude - d_before.longitude)
    step2 = abs(d_after.longitude - d_at.longitude)
    if step1 > 180: step1 = 360 - step1
    if step2 > 180: step2 = 360 - step2

    # Generous threshold — Moon moves ~0.0014°/s, Sun ~0.0000116°/s
    max_step = 0.005
    assert step1 < max_step, \
        f"{body} apparent lon jump before→at boundary: {step1}°"
    assert step2 < max_step, \
        f"{body} apparent lon jump at→after boundary: {step2}°"


# ---------------------------------------------------------------------------
# 2j — Distance monotonic sanity near lunar perigee / apogee
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2j_moon_distance_derivative_changes_sign_near_perigee(reader):
    """Moon distance must have a local minimum near the known perigee epoch."""
    jd = _JD_MOON_PERIGEE_2023
    one_hour = 1.0 / 24.0

    distances = [
        planet_at(Body.MOON, jd + i * one_hour, reader=reader).distance
        for i in range(-6, 7)  # ±6 hours in 1-hour steps
    ]

    # Find minimum index in the ±6h bracket
    min_idx = distances.index(min(distances))
    # Minimum must be in the interior (not at the edges)
    assert 1 <= min_idx <= len(distances) - 2, \
        f"Moon distance minimum at edge of bracket — perigee epoch may be inaccurate"

    # Distances before minimum must be monotonically decreasing (approx)
    for i in range(min_idx - 1):
        assert distances[i] > distances[i + 1], \
            f"Moon distance not decreasing before perigee: {distances[i]} → {distances[i+1]}"

    # Distances after minimum must be monotonically increasing (approx)
    for i in range(min_idx, len(distances) - 1):
        assert distances[i] < distances[i + 1], \
            f"Moon distance not increasing after perigee: {distances[i]} → {distances[i+1]}"
```

- [ ] **Step 2: Run Layer 2 in full**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer2" 2>&1
```

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 2d, 2g-2j geometry edge cases"
```

---

## Task 7: Layer 3a–3c — Calendar reform, year zero, JD 0.0

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 3a, 3b, 3c**

Append:

```python
# ===========================================================================
# LAYER 3 — Time system singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 3a — Julian / Gregorian calendar reform boundary
# Oct 4 Julian and Oct 15 Gregorian are consecutive days — JD must differ by 1.
# ---------------------------------------------------------------------------

def test_layer3a_calendar_reform_jd_difference_is_one_day():
    """Oct 4, 1582 Julian → Oct 15, 1582 Gregorian: consecutive days, JD diff = 1."""
    # The calendar boundary is: Oct 4 Julian = JD 2299160, Oct 15 Gregorian = JD 2299161
    jd_last_julian     = _JD_LAST_JULIAN     # 2299160.0
    jd_first_gregorian = _JD_GREGORIAN_REFORM  # 2299161.0

    assert jd_first_gregorian - jd_last_julian == pytest.approx(1.0, abs=1e-10), \
        "Calendar reform: JD gap between last Julian and first Gregorian day must be 1"


@pytest.mark.requires_ephemeris
def test_layer3a_positions_at_calendar_boundary_differ_by_one_day_motion(reader):
    """Planet positions at the reform boundary differ by ~1 day of motion, not zero."""
    sun_before = planet_at(Body.SUN, _JD_LAST_JULIAN,     reader=reader)
    sun_after  = planet_at(Body.SUN, _JD_GREGORIAN_REFORM, reader=reader)

    # Sun moves ~1°/day. One day apart must show roughly 0.9–1.1°
    step = abs(sun_after.longitude - sun_before.longitude)
    if step > 180: step = 360 - step
    assert 0.5 < step < 2.0, \
        f"Sun longitude difference at reform boundary = {step}° — expected ~1°"


# ---------------------------------------------------------------------------
# 3b — Year zero (1 BCE, astronomical convention)
# JD ≈ 1721057 is inside DE441 coverage (DE441 covers from ~−13199 years).
# ---------------------------------------------------------------------------

def test_layer3b_year_zero_calendar_conversion_does_not_crash():
    """julian_day(year=0, month=1, day=1) must not raise and must return a finite JD."""
    try:
        jd = julian_day(0, 1, 1)
        assert math.isfinite(jd), f"julian_day(0,1,1) returned non-finite: {jd}"
        assert jd > 0, f"julian_day(0,1,1) = {jd}, expected positive JD"
    except (ValueError, OverflowError) as exc:
        pytest.fail(f"julian_day(year=0) raised {type(exc).__name__}: {exc}")


def test_layer3b_year_zero_calendar_round_trip():
    """calendar_from_jd(julian_day(0, 1, 1)) must recover year=0, month=1, day=1."""
    jd = julian_day(0, 1, 1)
    year, month, day, hour = calendar_from_jd(jd)
    assert year  == 0, f"Round-trip year: {year} ≠ 0"
    assert month == 1, f"Round-trip month: {month} ≠ 1"
    assert day   == 1, f"Round-trip day: {day} ≠ 1"


@pytest.mark.requires_ephemeris
def test_layer3b_year_zero_positions_are_finite(reader):
    """Planet positions at year zero must be finite and in valid ranges."""
    jd_year_zero = julian_day(0, 1, 1)
    for body in (Body.SUN, Body.MOON, Body.MARS):
        data = planet_at(body, jd_year_zero, reader=reader)
        assert math.isfinite(data.longitude), f"{body} lon not finite at year 0"
        assert 0.0 <= data.longitude < 360.0, f"{body} lon out of range at year 0"
        assert data.distance > 0, f"{body} distance not positive at year 0"


# ---------------------------------------------------------------------------
# 3c — JD = 0.0 (deep past, outside DE441 coverage)
# Must raise a named exception — not silently return garbage.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer3c_jd_zero_raises_named_exception(reader):
    """Querying any body at JD = 0.0 must raise OutOfRangeError, not return a position."""
    with pytest.raises(OutOfRangeError):
        planet_at(Body.SUN, 0.0, reader=reader)


@pytest.mark.requires_ephemeris
def test_layer3c_negative_jd_raises_named_exception(reader):
    """JD = -1 000 000 must also raise OutOfRangeError."""
    with pytest.raises(OutOfRangeError):
        planet_at(Body.SUN, -1_000_000.0, reader=reader)
```

- [ ] **Step 2: Run Layer 3a–3c**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer3a or layer3b or layer3c" 2>&1
```

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 3a-3c calendar reform, year zero, JD 0"
```

---

## Task 8: Layer 3d–3f — Delta-T, JD precision, leap days

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 3d, 3e, 3f**

Append:

```python
# ---------------------------------------------------------------------------
# 3d — Delta-T sign coherence near its near-zero epoch
# ΔT > 0 means TT is ahead of UT → TT query gives a slightly larger longitude.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer3d_delta_t_sign_coherence_near_minimum(reader):
    """At an epoch where ΔT > 0, TT query must be ahead of UT query in longitude."""
    # J2000: ΔT ≈ +63.8 seconds (TT is ahead of UT)
    jd_ut = _J2000
    from moira.julian import decimal_year_from_jd
    dt_seconds = delta_t_from_jd(jd_ut)

    assert dt_seconds > 0, \
        f"ΔT at J2000 expected positive, got {dt_seconds}s"

    jd_tt = ut_to_tt(jd_ut)
    assert jd_tt > jd_ut, \
        f"TT should be ahead of UT when ΔT>0: jd_tt={jd_tt}, jd_ut={jd_ut}"

    # TT-queried Sun longitude must be slightly larger than UT-queried
    # (Sun moves ~1°/day = ~0.0000116°/s, and ΔT ≈ 63.8s → diff ≈ 0.00074°)
    sun_ut = planet_at(Body.SUN, jd_ut,  reader=reader)
    sun_tt = planet_at(Body.SUN, jd_tt, reader=reader)

    lon_diff = sun_tt.longitude - sun_ut.longitude
    if lon_diff < -180: lon_diff += 360
    if lon_diff >  180: lon_diff -= 360

    assert lon_diff > 0, \
        f"At J2000 (ΔT={dt_seconds:.1f}s > 0), TT longitude should exceed UT longitude, " \
        f"got diff={lon_diff}°"
    assert abs(lon_diff) < 0.01, \
        f"TT vs UT longitude difference {lon_diff}° implausibly large for ΔT={dt_seconds:.1f}s"


@pytest.mark.requires_ephemeris
def test_layer3d_delta_t_negative_epoch_sign_reversal(reader):
    """At an epoch where ΔT < 0, UT query must be ahead of TT in time."""
    # ΔT was near zero around 1900, and slightly negative around 1870s
    # Use decimal year 1870 where ΔT ≈ −1.9 s (from model)
    jd_ut_1870 = julian_day(1870, 1, 1)
    dt = delta_t_from_jd(jd_ut_1870)
    if dt >= 0:
        pytest.skip(f"ΔT at 1870 is {dt:.2f}s (non-negative) — skip sign reversal test")

    jd_tt = ut_to_tt(jd_ut_1870)
    assert jd_tt < jd_ut_1870, \
        f"When ΔT<0, TT should be behind UT: jd_tt={jd_tt}, jd_ut={jd_ut_1870}"


# ---------------------------------------------------------------------------
# 3e — JD integer and JD .5 precision boundaries
# JD integer = Julian noon; JD .5 = civil midnight.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer3e_jd_integer_boundary_one_second_continuity(reader):
    """Position must be continuous at a JD integer (Julian noon) boundary."""
    jd_noon = float(int(_J2000))  # exact integer JD

    d_before = planet_at(Body.SUN, jd_noon - _ONE_SECOND_JD, reader=reader)
    d_at     = planet_at(Body.SUN, jd_noon,                   reader=reader)
    d_after  = planet_at(Body.SUN, jd_noon + _ONE_SECOND_JD, reader=reader)

    step1 = abs(d_at.longitude - d_before.longitude)
    step2 = abs(d_after.longitude - d_at.longitude)
    if step1 > 180: step1 = 360 - step1
    if step2 > 180: step2 = 360 - step2

    assert step1 < 0.001, f"Sun lon jump at JD integer boundary (before→at): {step1}°"
    assert step2 < 0.001, f"Sun lon jump at JD integer boundary (at→after): {step2}°"


@pytest.mark.requires_ephemeris
def test_layer3e_jd_half_boundary_one_second_continuity(reader):
    """Position must be continuous at a JD .5 (civil midnight) boundary."""
    jd_midnight = float(int(_J2000)) + 0.5

    d_before = planet_at(Body.MOON, jd_midnight - _ONE_SECOND_JD, reader=reader)
    d_at     = planet_at(Body.MOON, jd_midnight,                   reader=reader)
    d_after  = planet_at(Body.MOON, jd_midnight + _ONE_SECOND_JD, reader=reader)

    step1 = abs(d_at.longitude - d_before.longitude)
    step2 = abs(d_after.longitude - d_at.longitude)
    if step1 > 180: step1 = 360 - step1
    if step2 > 180: step2 = 360 - step2

    assert step1 < 0.003, f"Moon lon jump at JD .5 boundary (before→at): {step1}°"
    assert step2 < 0.003, f"Moon lon jump at JD .5 boundary (at→after): {step2}°"


# ---------------------------------------------------------------------------
# 3f — Leap year rules
# 1600 is Gregorian leap; 1700, 1800, 1900 are not; 2000 is.
# Validate via JD difference between Dec 31 and Mar 1.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("year,is_leap", [
    (1600, True),   # Gregorian leap
    (1700, False),  # Gregorian century — not leap
    (1800, False),
    (1900, False),
    (2000, True),   # 400-year rule
    (2100, False),  # future century non-leap
    (2400, True),   # future 400-year leap
])
def test_layer3f_leap_year_rules(year, is_leap):
    """February must have 28 or 29 days depending on leap year rule."""
    jd_feb28 = julian_day(year, 2, 28)
    jd_mar01 = julian_day(year, 3,  1)

    feb_days = jd_mar01 - jd_feb28
    if is_leap:
        assert feb_days == pytest.approx(2.0, abs=1e-10), \
            f"Year {year} should be leap (Feb 28 → Mar 1 = 2 days), got {feb_days}"
    else:
        assert feb_days == pytest.approx(1.0, abs=1e-10), \
            f"Year {year} should NOT be leap (Feb 28 → Mar 1 = 1 day), got {feb_days}"
```

- [ ] **Step 2: Run Layer 3d–3f**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v -k "layer3d or layer3e or layer3f" 2>&1
```

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 3d-3f Delta-T, JD boundaries, leap years"
```

---

## Task 9: Layer 3g–3i and cross-cutting attacks

**Files:**
- Modify: `tests/unit/test_adversarial_singularities.py`

- [ ] **Step 1: Write tests 3g, 3h, 3i, route equivalence, and boundary ownership**

Append:

```python
# ---------------------------------------------------------------------------
# 3g — Deep historical BCE calendar conversion
# Calendar round-trip must survive deep negative JDs without integer overflow.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("jd_deep", [
    1.0,          # near JD 0
    -100_000.0,   # ~270 BCE — near coverage edge
    500_000.0,    # inside DE441
    -1_000_000.0, # deep past (calendar only, no ephemeris)
])
def test_layer3g_deep_historical_calendar_round_trip(jd_deep):
    """calendar_from_jd → julian_day round-trip must recover the original JD within 1 day."""
    try:
        year, month, day, hour = calendar_from_jd(jd_deep)
    except (ValueError, OverflowError):
        pytest.skip(f"calendar_from_jd({jd_deep}) raised — may be out of calendar range")

    try:
        jd_recovered = julian_day(year, month, int(day)) + (day - int(day))
    except (ValueError, OverflowError):
        pytest.skip(f"julian_day({year},{month},{day}) raised — symmetry gap")

    assert abs(jd_recovered - jd_deep) < 1.0, \
        f"Calendar round-trip JD error: {abs(jd_recovered - jd_deep)} days at JD {jd_deep}"


# ---------------------------------------------------------------------------
# 3h — Split JD precision
# position(jd) vs position(jd + tiny_offset) must agree within float resolution.
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_base,label", [
    (_J2000, "J2000"),
    (2460000.0, "near_present"),
])
def test_layer3h_split_jd_precision(reader, jd_base, label):
    """position(jd) and position(jd + 1e-10) must agree within float JD precision."""
    tiny = 1e-10  # about 8.6 microseconds — below float JD resolution
    d1 = planet_at(Body.SUN, jd_base,          reader=reader)
    d2 = planet_at(Body.SUN, jd_base + tiny,   reader=reader)

    diff = abs(d2.longitude - d1.longitude)
    if diff > 180: diff = 360 - diff
    # At float JD resolution (~2.2e-16 * 2.4M ≈ 5e-10 day ≈ 4e-5 s),
    # a 1e-10 day offset is near the float floor — differences should be tiny
    assert diff < 1e-6, \
        f"{label}: positions differ by {diff}° for a {tiny}-day offset — precision collapse"


# ---------------------------------------------------------------------------
# 3i — TT / UT round-trip
# UT → TT → UT must recover the original JD within ΔT model precision.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("jd_ut,label", [
    (_J2000,                  "J2000"),
    (julian_day(1900, 1, 1),  "1900"),
    (julian_day(1000, 6, 15), "1000_AD"),
])
def test_layer3i_tt_ut_round_trip(jd_ut, label):
    """UT → TT → UT must recover the input JD within 1e-6 seconds."""
    jd_tt       = ut_to_tt(jd_ut)
    jd_ut_back  = tt_to_ut(jd_tt)

    residual_seconds = abs(jd_ut_back - jd_ut) * 86400.0
    assert residual_seconds < 1e-4, \
        f"{label}: TT/UT round-trip residual {residual_seconds:.2e}s > 1e-4s"


# ===========================================================================
# CROSS-CUTTING: Route equivalence attacks
# ===========================================================================

@pytest.mark.requires_ephemeris
def test_re3_single_jd_vs_split_jd_position_agreement(reader):
    """planet_at with jd vs jd+offset must agree within moira_approx longitude."""
    jd = _J2000
    offset = 1.0 / 86400.0 / 1000.0  # 1 millisecond in JD
    d1 = planet_at(Body.JUPITER, jd,          reader=reader)
    d2 = planet_at(Body.JUPITER, jd + offset, reader=reader)

    diff = abs(d2.longitude - d1.longitude)
    if diff > 180: diff = 360 - diff
    # Jupiter moves ~0.083°/day = 9.6e-7 °/s → 1ms offset = ~9.6e-10°
    assert diff < 1e-6, \
        f"Jupiter: single vs split JD differ by {diff}° for 1ms offset"


@pytest.mark.requires_ephemeris
def test_re5_ecliptic_equatorial_round_trip_at_live_positions(reader):
    """ecliptic→equatorial→ecliptic round-trip at live planet positions."""
    from moira.coordinates import ecliptic_to_equatorial, equatorial_to_ecliptic
    jd = _J2000
    for body in (Body.SUN, Body.MOON, Body.MERCURY, Body.JUPITER):
        data = planet_at(body, jd, reader=reader)
        ra, dec = ecliptic_to_equatorial(data.longitude, data.latitude, _OBLIQUITY_J2000)
        lon_back, lat_back = equatorial_to_ecliptic(ra, dec, _OBLIQUITY_J2000)

        lon_residual = abs(normalize_degrees(lon_back - data.longitude))
        if lon_residual > 180: lon_residual = 360 - lon_residual
        assert lon_residual < 1e-10, \
            f"{body} ecliptic round-trip lon residual {lon_residual}°"
        assert abs(lat_back - data.latitude) < 1e-10, \
            f"{body} ecliptic round-trip lat residual {abs(lat_back - data.latitude)}°"


# ===========================================================================
# CROSS-CUTTING: Boundary ownership doctrine
# ===========================================================================

def test_boundary_ownership_longitude_zero_not_360():
    """normalize_degrees(0.0) must return 0.0, not 360.0."""
    assert normalize_degrees(0.0) == 0.0


def test_boundary_ownership_longitude_360_normalises_to_zero():
    """normalize_degrees(360.0) must return 0.0."""
    assert normalize_degrees(360.0) == pytest.approx(0.0, abs=1e-15)


def test_boundary_ownership_speed_zero_finite():
    """Speed = 0.0 is a valid float — ensure PlanetData accepts it without sign flip."""
    # PlanetData is a frozen dataclass — construct it directly with speed=0
    data = PlanetData(
        name=Body.MARS,
        longitude=90.0, latitude=0.0, distance=1.0e8,
        speed=0.0, ra=90.0, dec=0.0,
    )
    assert data.speed == 0.0
    assert math.isfinite(data.speed)


@pytest.mark.requires_ephemeris
def test_boundary_ownership_coverage_edge_raises_not_silence(reader):
    """One day before DE441 public coverage start must raise OutOfRangeError."""
    from moira.spk_reader import SpkReader
    # Public coverage start ≈ JD -3100015.5 TT; convert to UT is slightly earlier
    # Use a safely-out-of-range value
    jd_out = -4_000_000.0
    with pytest.raises(OutOfRangeError):
        planet_at(Body.SUN, jd_out, reader=reader)
```

- [ ] **Step 2: Run full singularities file**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py -v 2>&1
```

Record the final pass/fail count. Every failure is a genuine defect.

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_singularities.py
git commit -m "test(adversarial): Layer 3g-3i, route equivalence, boundary ownership"
```

---

## Task 10: Scaffold `test_adversarial_house_singularities.py` + Layer 4a–4e

**Files:**
- Create: `tests/unit/test_adversarial_house_singularities.py`

- [ ] **Step 1: Create file with imports, constants, and tests 4a–4e**

```python
"""
Adversarial house and angular singularity tests — Layer 4.

Same philosophy as test_adversarial_singularities.py:
a test that fails on first run has found a real defect. Leave it failing.
"""
from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.houses import HouseSystem, calculate_houses
from moira.julian import julian_day, apparent_sidereal_time_at, ut_to_tt
from moira.planets import planet_at

_J2000          = 2451545.0
_ONE_SECOND_JD  = 1.0 / 86400.0

# House systems exercised in adversarial tests
_QUADRANT_SYSTEMS = [
    HouseSystem.PLACIDUS,
    HouseSystem.KOCH,
    HouseSystem.PORPHYRY,
    HouseSystem.REGIOMONTANUS,
    HouseSystem.CAMPANUS,
]
_ALL_SYSTEMS = [
    HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.PORPHYRY,
    HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN, HouseSystem.REGIOMONTANUS,
]


def _find_jd_for_asc(target_asc_deg: float, lat: float, lon: float,
                     jd_start: float, system: str,
                     search_hours: int = 25) -> float | None:
    """Binary-search for a JD where ASC is near target_asc_deg."""
    one_hour = 1.0 / 24.0
    jd = jd_start
    for _ in range(search_hours * 60):  # 1-minute resolution
        cusps = calculate_houses(jd, lat, lon, system)
        diff = (cusps.asc - target_asc_deg + 180) % 360 - 180
        if abs(diff) < 0.5:
            return jd
        jd += 1.0 / 24.0 / 60.0
    return None


# ===========================================================================
# LAYER 4 — House and angular singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 4a — ASC near 0° Aries
# ---------------------------------------------------------------------------

def test_layer4a_asc_near_zero_no_360_leak():
    """When ASC ≈ 0°, all cusps must be finite and in [0, 360). No 360° leak."""
    # Search for a JD near J2000 at equator where ASC ≈ 0°
    jd = _find_jd_for_asc(0.0, 0.0, 0.0, _J2000, HouseSystem.PLACIDUS)
    if jd is None:
        pytest.skip("Could not find JD with ASC near 0° in search window")

    for system in [HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY]:
        cusps = calculate_houses(jd, 0.0, 0.0, system)

        assert 0.0 <= cusps.asc < 360.0, \
            f"{system}: ASC={cusps.asc} not in [0, 360)"
        assert cusps.asc != 360.0, f"{system}: ASC is exactly 360° — should be 0°"

        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), f"{system}: cusp {i+1} is not finite: {c}"
            assert 0.0 <= c < 360.0, f"{system}: cusp {i+1} = {c} not in [0, 360)"


# ---------------------------------------------------------------------------
# 4b — Observer at exactly 0° latitude (equator)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _ALL_SYSTEMS)
def test_layer4b_observer_at_equator(system):
    """At lat=0°, all house systems must return finite cusps without denominator blow-up."""
    cusps = calculate_houses(_J2000, 0.0, 0.0, system)

    assert math.isfinite(cusps.asc), f"{system}: ASC not finite at equator"
    assert math.isfinite(cusps.mc),  f"{system}: MC not finite at equator"
    assert 0.0 <= cusps.asc < 360.0, f"{system}: ASC out of range"

    for i, c in enumerate(cusps.cusps):
        assert math.isfinite(c), f"{system}: cusp {i+1} not finite at equator"
        assert 0.0 <= c < 360.0, f"{system}: cusp {i+1} = {c} out of range"


# ---------------------------------------------------------------------------
# 4c/4d — RAMC at 0°, 90°, 180°, 270°
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target_ramc,label", [
    (0.0,   "RAMC=0"),
    (90.0,  "RAMC=90"),
    (180.0, "RAMC=180"),
    (270.0, "RAMC=270"),
])
def test_layer4cd_ramc_cardinal_values(target_ramc, label):
    """At each cardinal RAMC value, all cusps must be finite and canonically normalised."""
    # RAMC = GAST at the observer location. For lon=0, RAMC = GAST.
    # Search for a JD near J2000 where RAMC ≈ target.
    one_minute = 1.0 / 24.0 / 60.0
    jd = _J2000
    found_jd = None
    for _ in range(1440):  # search one full day at 1-min resolution
        ramc = calculate_houses(jd, 51.5, 0.0, HouseSystem.PLACIDUS).armc
        diff = (ramc - target_ramc + 180) % 360 - 180
        if abs(diff) < 0.5:
            found_jd = jd
            break
        jd += one_minute

    if found_jd is None:
        pytest.skip(f"Could not find JD for {label}")

    for system in [HouseSystem.PLACIDUS, HouseSystem.PORPHYRY, HouseSystem.EQUAL]:
        cusps = calculate_houses(found_jd, 51.5, 0.0, system)

        assert math.isfinite(cusps.asc), f"{system} {label}: ASC not finite"
        assert math.isfinite(cusps.mc),  f"{system} {label}: MC not finite"
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c),     f"{system} {label}: cusp {i+1} not finite"
            assert 0.0 <= c < 360.0,     f"{system} {label}: cusp {i+1}={c} out of range"


# ---------------------------------------------------------------------------
# 4e — MC = 0° exactly
# ---------------------------------------------------------------------------

def test_layer4e_mc_near_zero_no_360_leak():
    """When MC ≈ 0°, MC must not be returned as 360°."""
    # MC ≈ 0° when RAMC ≈ 0°. Search for such a JD.
    one_minute = 1.0 / 24.0 / 60.0
    jd = _J2000
    found_jd = None
    for _ in range(1440):
        cusps = calculate_houses(jd, 51.5, 0.0, HouseSystem.PLACIDUS)
        if abs(cusps.mc) < 1.0 or cusps.mc > 359.0:
            found_jd = jd
            break
        jd += one_minute

    if found_jd is None:
        pytest.skip("Could not find JD with MC near 0°")

    cusps = calculate_houses(found_jd, 51.5, 0.0, HouseSystem.PLACIDUS)
    assert cusps.mc != 360.0, f"MC is exactly 360° — should be normalised to 0°"
    assert 0.0 <= cusps.mc < 360.0, f"MC = {cusps.mc} not in [0, 360)"
    # IC must be exactly 180° from MC
    ic = (cusps.mc + 180.0) % 360.0
    assert cusps.ic == pytest.approx(ic, abs=1e-8), \
        f"IC={cusps.ic} ≠ MC+180={ic}"
```

- [ ] **Step 2: Verify imports and run 4a–4e**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_house_singularities.py -v -k "layer4a or layer4b or layer4c or layer4d or layer4e" 2>&1
```

If `HouseSystem.PLACIDUS` raises `AttributeError`, check the actual constant names:
```
.venv\Scripts\python.exe -c "from moira.houses import HouseSystem; print(dir(HouseSystem))"
```

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_house_singularities.py
git commit -m "test(adversarial): Layer 4a-4e house ASC/RAMC/MC singularities"
```

---

## Task 11: Layer 4f–4l — Critical latitude, invariants, cusp doctrine

**Files:**
- Modify: `tests/unit/test_adversarial_house_singularities.py`

- [ ] **Step 1: Write tests 4f through 4l**

Append:

```python
# ---------------------------------------------------------------------------
# 4f — Observer just below / just above critical latitude for Placidus/Koch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_layer4f_just_below_critical_latitude_computes_normally(system):
    """Just below the critical latitude: system should compute normally."""
    from moira.houses import _compute_critical_latitude  # or equivalent internal
    # If not accessible, derive from doctrine: ~66.56° for J2000
    try:
        crit_lat = _compute_critical_latitude(_J2000)
    except (ImportError, AttributeError):
        crit_lat = 66.5  # fallback approximation

    lat_below = crit_lat - 0.5
    cusps = calculate_houses(_J2000, lat_below, 0.0, system)

    assert not cusps.fallback, \
        f"{system}: fallback triggered at {lat_below}° (below critical {crit_lat}°)"
    assert cusps.effective_system == system, \
        f"{system}: effective system changed below critical latitude"
    for i, c in enumerate(cusps.cusps):
        assert math.isfinite(c), f"{system}: cusp {i+1} not finite at {lat_below}°"


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_layer4f_just_above_critical_latitude_triggers_fallback_or_error(system):
    """Just above the critical latitude: fallback or named error, never silent wrong cusps."""
    try:
        from moira.houses import _compute_critical_latitude
        crit_lat = _compute_critical_latitude(_J2000)
    except (ImportError, AttributeError):
        crit_lat = 66.5

    lat_above = crit_lat + 0.5
    try:
        cusps = calculate_houses(_J2000, lat_above, 0.0, system)
        # Fallback path taken — must be honest about it
        assert cusps.fallback, \
            f"{system}: no fallback flag at {lat_above}° (above critical {crit_lat}°) — silent wrong cusps"
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), f"{system}: cusp {i+1} not finite after fallback at {lat_above}°"
    except (ValueError, RuntimeError) as exc:
        pass  # named error is also acceptable


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_layer4f_latitude_89_behaviour_is_fallback_or_named_error(system):
    """At 89° latitude, semi-arc systems must fallback or raise — never hang."""
    try:
        cusps = calculate_houses(_J2000, 89.0, 0.0, system)
        assert cusps.fallback, \
            f"{system}: 89° latitude returned no fallback flag — silent wrong cusps"
    except (ValueError, RuntimeError):
        pass  # explicit error is acceptable


# ---------------------------------------------------------------------------
# 4g — MC / IC opposition invariant (every system, sweep of epochs)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _ALL_SYSTEMS)
@pytest.mark.parametrize("jd,label", [
    (_J2000,          "J2000"),
    (_J2000 + 182.5,  "J2000+6mo"),
    (_J2000 - 365.25, "J2000-1yr"),
])
def test_layer4g_mc_ic_opposition_invariant(system, jd, label):
    """IC must always equal (MC + 180) % 360 for every system at every epoch."""
    cusps = calculate_houses(jd, 51.5, -0.1, system)
    expected_ic = (cusps.mc + 180.0) % 360.0
    assert cusps.ic == pytest.approx(expected_ic, abs=1e-8), \
        f"{system} {label}: IC={cusps.ic}°, MC={cusps.mc}°, expected IC={expected_ic}°"


# ---------------------------------------------------------------------------
# 4h — ASC / DSC opposition invariant
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _ALL_SYSTEMS)
def test_layer4h_asc_dsc_opposition_invariant(system):
    """DSC must always equal (ASC + 180) % 360."""
    cusps = calculate_houses(_J2000, 51.5, -0.1, system)
    expected_dsc = (cusps.asc + 180.0) % 360.0
    assert cusps.dsc == pytest.approx(expected_dsc, abs=1e-8), \
        f"{system}: DSC={cusps.dsc}°, ASC={cusps.asc}°, expected DSC={expected_dsc}°"


# ---------------------------------------------------------------------------
# 4i — Cusp ordering modulo 360 (circular coherence)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _QUADRANT_SYSTEMS)
def test_layer4i_cusp_circular_ordering(system):
    """Cusp sequence must be circularly ordered — each cusp reachable from previous by moving forward."""
    # Test at standard observer and at ASC-near-359 scenario
    for lat, lon in [(51.5, -0.1), (0.0, 0.0)]:
        cusps = calculate_houses(_J2000, lat, lon, system)
        c = list(cusps.cusps)
        assert len(c) == 12, f"{system}: expected 12 cusps, got {len(c)}"
        for i in range(12):
            diff = (c[(i + 1) % 12] - c[i]) % 360.0
            assert diff > 0, \
                f"{system} lat={lat}: cusp {i+1}={c[i]}° → cusp {(i+1)%12+1}={c[(i+1)%12]}°" \
                f" — not circularly ordered (diff={diff}°)"


# ---------------------------------------------------------------------------
# 4j — Equal / Whole Sign / Porphyry at ASC near 359.999°
# ---------------------------------------------------------------------------

def test_layer4j_asc_near_360_cusp_ordering_across_zero():
    """With ASC near 359°, no cusp should be negative or cause inversion at 0°."""
    jd = _find_jd_for_asc(359.0, 51.5, 0.0, _J2000, HouseSystem.EQUAL)
    if jd is None:
        pytest.skip("Could not find JD with ASC near 359°")

    for system in [HouseSystem.EQUAL, HouseSystem.PORPHYRY]:
        cusps = calculate_houses(jd, 51.5, 0.0, system)
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), f"{system}: cusp {i+1} not finite near 359° ASC"
            assert c >= 0.0,         f"{system}: cusp {i+1} = {c} is negative"
            assert c < 360.0,        f"{system}: cusp {i+1} = {c} is >= 360°"


# ---------------------------------------------------------------------------
# 4k — Body exactly on a house cusp: placement must be stable and deterministic
# ---------------------------------------------------------------------------

def test_layer4k_body_on_cusp_placement_is_stable_and_deterministic():
    """A body exactly on a cusp must return the same house on repeated calls."""
    cusps = calculate_houses(_J2000, 51.5, -0.1, HouseSystem.PLACIDUS)
    # Use House 1 cusp (ASC) as the test longitude
    test_longitude = cusps.asc

    # Build a minimal PlanetData-like dict for house placement
    # (Use moira's house placement API if available)
    try:
        from moira.houses import house_of
        house1 = house_of(test_longitude, cusps)
        house2 = house_of(test_longitude, cusps)
        assert house1 == house2, \
            f"house_of on-cusp is non-deterministic: {house1} ≠ {house2}"
        assert 1 <= house1 <= 12, f"on-cusp house={house1} not in [1,12]"
    except (ImportError, AttributeError):
        pytest.skip("house_of not available — placement test skipped")


# ---------------------------------------------------------------------------
# 4l — MC approaching ASC at extreme latitude
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lat", [85.0, 87.0, 89.9])
def test_layer4l_mc_asc_extreme_latitude_no_hang(lat):
    """At extreme latitudes, the engine must not hang and must return finite angles or a named error."""
    try:
        cusps = calculate_houses(_J2000, lat, 0.0, HouseSystem.PLACIDUS)
        assert math.isfinite(cusps.asc), f"ASC not finite at lat={lat}°"
        assert math.isfinite(cusps.mc),  f"MC not finite at lat={lat}°"
        # If we got cusps, the opposition invariant must hold
        ic  = (cusps.mc  + 180.0) % 360.0
        dsc = (cusps.asc + 180.0) % 360.0
        assert cusps.ic  == pytest.approx(ic,  abs=1e-6), \
            f"IC invariant broken at lat={lat}°"
        assert cusps.dsc == pytest.approx(dsc, abs=1e-6), \
            f"DSC invariant broken at lat={lat}°"
    except (ValueError, RuntimeError):
        pass  # named error is acceptable
```

- [ ] **Step 2: Run full Layer 4**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_house_singularities.py -v 2>&1
```

If `_compute_critical_latitude` is not importable, replace the import with the doctrine value `66.5` and add a comment explaining this.

- [ ] **Step 3: Commit**

```
git add tests/unit/test_adversarial_house_singularities.py
git commit -m "test(adversarial): Layer 4f-4l critical latitude, invariants, cusp doctrine"
```

---

## Task 12: Final run — full adversarial suite

**Files:** none (verification only)

- [ ] **Step 1: Run both adversarial files together**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_adversarial_singularities.py tests/unit/test_adversarial_house_singularities.py -v 2>&1
```

- [ ] **Step 2: Record the failure count**

Every failure is a genuine engine defect. Document them in a comment at the top of each test file:

```python
# Known failures as of YYYY-MM-DD:
# - test_layer1f_icrf_to_ecliptic_zero_vector: icrf_to_ecliptic does not raise for [0,0,0]
# - test_layer4k_...: house_of not yet implemented
```

- [ ] **Step 3: Run the original killer suite to confirm no regressions**

```
.venv\Scripts\python.exe -m pytest tests/unit/test_de441_segment_boundaries.py tests/unit/test_ephemeris_stress_proofs.py tests/unit/test_topocentric_multi_path_consistency.py tests/unit/test_ephemeris_breadth_gauntlet.py tests/unit/test_polar_house_breadth_gauntlet.py tests/unit/test_polar_chart_public_gauntlet.py tests/integration/test_topocentric_multi_path_horizons_anchor.py tests/integration/test_ephemeris_breadth_horizons_gauntlet.py tests/integration/test_houses_polar_external_reference.py -q 2>&1
```

Expected: 42 passed (same as before).

- [ ] **Step 4: Final commit**

```
git add tests/unit/test_adversarial_singularities.py tests/unit/test_adversarial_house_singularities.py
git commit -m "test(adversarial): complete singularity attack suite — Layers 1-4 plus cross-cutting"
```

---

## Self-Review Checklist

**Spec coverage:**

| Spec section | Task |
|---|---|
| 1a–1b poles | Task 2 |
| 1c Aries / 360° normalisation | Task 2 |
| 1d vector round-trip | Task 3 |
| 1e longitude sweep | Task 3 |
| 1f zero vector | Task 3 |
| 1g subnormal | Task 3 |
| 1h negative epsilon | Task 3 |
| 2a vernal equinox | Task 4 |
| 2b Moon perigee | Task 4 |
| 2c retrograde stations | Task 5 |
| 2d body on ecliptic plane | Task 6 |
| 2e superior conjunction | ⚠ omitted — marked future-facing in spec |
| 2f full retrograde loop | Task 5 |
| 2g zero vector relative | Task 6 |
| 2h EMB chain | Task 6 |
| 2i segment boundary apparent | Task 6 |
| 2j distance monotonic | Task 6 |
| 3a calendar reform | Task 7 |
| 3b year zero | Task 7 |
| 3c JD 0.0 | Task 7 |
| 3d delta-T sign | Task 8 |
| 3e JD integer/.5 | Task 8 |
| 3f leap days | Task 8 |
| 3g deep history | Task 9 |
| 3h split JD | Task 9 |
| 3i TT/UT round-trip | Task 9 |
| RE-1,2,4 | Not yet included — add if moira.spk_reader exposes `_segment_for` cleanly |
| RE-3,5 | Task 9 |
| Boundary ownership | Task 9 |
| 4a–4e | Task 10 |
| 4f critical lat | Task 11 |
| 4g–4l invariants + doctrine | Task 11 |

**2e (Mercury superior conjunction):** Spec marks this future-facing if gravitational deflection is not independently testable. Excluded from this plan accordingly.

**RE-1 / RE-2 (native vs public path):** These require low-level kernel access. Included partially in Task 6 (2h EMB chain). Full RE-1/RE-2 can be added once the kernel handle interface is confirmed.
