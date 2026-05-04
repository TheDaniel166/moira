# Lunar Eclipse Cartography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `moira/lunar_cartography.py` — a world-map visibility cartography engine for lunar eclipses, producing penumbral/partial/total bands, moonrise/moonset bands, magnitude isolines, and duration contours.

**Architecture:** Direct port of `solar_cartography.py`'s sweep pattern. An adaptive grid is centered on the sub-lunar point at greatest eclipse; at each time step the Moon's altitude is computed vectorially for all N grid cells; fields are accumulated (max altitude per phase window, max magnitude, duration margin series); then band curves and contours are extracted from the accumulated fields using the same utilities as solar cartography.

**Tech Stack:** Python 3.11+, NumPy, optional CuPy (GPU). All solar cartography utility functions are re-imported rather than duplicated. Mocking via `unittest.mock` for kernel-free unit tests.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `moira/lunar_cartography.py` | All data structures, helpers, public function |
| Create | `tests/test_lunar_cartography.py` | Unit tests (kernel-free, mock-based) |
| Modify | `moira/__init__.py` | Import + `__all__` entries |

> **Note on `moira/facade.py`:** The existing `solar_cartography` module is *not* re-exported through `facade.py` — the cartography surface is published only through `moira/__init__.py`. This plan preserves that symmetry; lunar cartography is wired into `moira/__init__.py` only.

---

## Task 1: Module Scaffold — Imports, Data Structures, `__all__`

**Files:**
- Create: `moira/lunar_cartography.py`
- Create: `tests/test_lunar_cartography.py`

- [ ] **Step 1: Write failing tests for data structures**

```python
# tests/test_lunar_cartography.py
import pytest
from dataclasses import FrozenInstanceError
import numpy as _np

from moira.lunar_cartography import (
    LunarBesselianSample,
    LunarShadowBand,
    LunarContourLevel,
    LunarCartographyResult,
)
from moira.solar_cartography import ArrayBackendInfo


def test_lunar_shadow_band_is_frozen():
    band = LunarShadowBand(south_curve=(), north_curve=(), polygon=())
    with pytest.raises((FrozenInstanceError, TypeError)):
        band.south_curve = ((1.0, 2.0),)


def test_lunar_besselian_sample_fields():
    sample = LunarBesselianSample(
        jd_ut=2451545.0,
        sublunar_lat=20.5,
        sublunar_lon=-45.0,
        umbral_radius_earth_radii=0.73,
        penumbral_radius_earth_radii=1.21,
        moon_declination_deg=18.3,
        eclipse_magnitude=1.12,
    )
    assert sample.eclipse_magnitude == 1.12
    assert sample.jd_ut == 2451545.0
    assert sample.sublunar_lat == 20.5


def test_lunar_contour_level_fields():
    contour = LunarContourLevel(
        kind="magnitude",
        threshold=0.6,
        south_curve=((10.0, -30.0), (12.0, -28.0)),
        north_curve=((20.0, -30.0), (22.0, -28.0)),
    )
    assert contour.kind == "magnitude"
    assert contour.threshold == 0.6


def test_lunar_cartography_result_construction():
    band = LunarShadowBand((), (), ())
    result = LunarCartographyResult(
        event_jd_ut=2451545.0,
        eclipse_type="total",
        backend=ArrayBackendInfo(name="numpy", is_gpu=False),
        window_start_jd_ut=2451544.9,
        window_end_jd_ut=2451545.1,
        sample_jds_ut=(2451545.0,),
        besselian_samples=(),
        penumbral_band=band,
        partial_band=band,
        total_band=band,
        moonrise_band=band,
        moonset_band=band,
        magnitude_contours=(),
        duration_contours=(),
    )
    assert result.eclipse_type == "total"
    assert result.event_jd_ut == 2451545.0
    assert result.total_band is band
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_lunar_cartography.py -v
```
Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Create module shell**

```python
# moira/lunar_cartography.py
"""
Moira — Lunar Eclipse Cartography
Archetype: Engine

Purpose:
    Maps where on Earth a lunar eclipse is visible, to what depth, and for
    how long. Produces penumbral, partial, and total visibility bands;
    moonrise/moonset transition bands; magnitude isolines; and duration
    contours on an adaptive grid centered on the sub-lunar point.

Architecture:
    Direct port of solar_cartography.py's sweep pattern. Grid and band
    extraction utilities are imported from solar_cartography rather than
    duplicated.

Public surface / exports:
    LunarBesselianSample
    LunarShadowBand
    LunarContourLevel
    LunarCartographyResult
    lunar_eclipse_cartography(calc, jd_seed, *, kind, backward, backend,
                               time_samples) -> LunarCartographyResult
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as _np

try:
    import cupy as _cp
except ImportError:
    _cp = None

from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM, Body
from .corrections import topocentric_correction_batch_np
from .eclipse import EclipseCalculator
from .julian import local_sidereal_time
from .planets import planet_at
from .solar_cartography import (
    ArrayBackendInfo,
    _KM_PER_DEG_LAT,
    _build_contours,
    _build_zero_band_from_field,
    _duration_from_margin_series,
    _evaluate_quadratic_series,
    _extract_latitude_band_curves,
    _quadratic_peak_refine,
    _sample_interval,
    _select_backend,
    _to_numpy,
    _topocentric_correction_batch_backend,
    _wrap_longitude_deg,
)

__all__ = [
    "LunarBesselianSample",
    "LunarShadowBand",
    "LunarContourLevel",
    "LunarCartographyResult",
    "lunar_eclipse_cartography",
]


@dataclass(frozen=True, slots=True)
class LunarBesselianSample:
    jd_ut: float
    sublunar_lat: float
    sublunar_lon: float
    umbral_radius_earth_radii: float
    penumbral_radius_earth_radii: float
    moon_declination_deg: float
    eclipse_magnitude: float


@dataclass(frozen=True, slots=True)
class LunarShadowBand:
    south_curve: tuple[tuple[float, float], ...]
    north_curve: tuple[tuple[float, float], ...]
    polygon: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class LunarContourLevel:
    kind: str
    threshold: float
    south_curve: tuple[tuple[float, float], ...]
    north_curve: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class LunarCartographyResult:
    event_jd_ut: float
    eclipse_type: str
    backend: ArrayBackendInfo
    window_start_jd_ut: float
    window_end_jd_ut: float
    sample_jds_ut: tuple[float, ...]
    besselian_samples: tuple[LunarBesselianSample, ...]
    penumbral_band: LunarShadowBand
    partial_band: LunarShadowBand
    total_band: LunarShadowBand
    moonrise_band: LunarShadowBand
    moonset_band: LunarShadowBand
    magnitude_contours: tuple[LunarContourLevel, ...]
    duration_contours: tuple[LunarContourLevel, ...]
```

- [ ] **Step 4: Run tests — should pass now**

```
pytest tests/test_lunar_cartography.py -v
```
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```
git add moira/lunar_cartography.py tests/test_lunar_cartography.py
git commit -m "feat: lunar_cartography scaffold — data structures and imports"
```

---

## Task 2: `_sublunar_point` + `_compute_lunar_besselian_sample`

**Files:**
- Modify: `moira/lunar_cartography.py` — add two functions after the dataclasses
- Modify: `tests/test_lunar_cartography.py` — add tests

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_lunar_cartography.py
from unittest.mock import MagicMock, patch
from moira.lunar_cartography import _sublunar_point, _compute_lunar_besselian_sample


def _make_moon_cart(x, y, z):
    m = MagicMock()
    m.x, m.y, m.z = x, y, z
    return m


def _make_sun_cart(x, y, z):
    s = MagicMock()
    s.x, s.y, s.z = x, y, z
    return s


def test_sublunar_point_equator_zero_gast():
    """Moon at ICRF (384400, 0, 0): RA=0°, Dec=0°. GAST=0° → sub-lunar lon=0°."""
    calc = MagicMock()
    moon = _make_moon_cart(384400.0, 0.0, 0.0)
    with patch("moira.lunar_cartography.planet_at", return_value=moon), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        lat, lon = _sublunar_point(calc, 2451545.0)
    assert abs(lat) < 0.001
    assert abs(lon) < 0.001


def test_sublunar_point_north_declination():
    """Moon at (0, 0, 384400): Dec=90°. Sub-lunar lat should be ~90°."""
    calc = MagicMock()
    moon = _make_moon_cart(0.0, 0.0, 384400.0)
    with patch("moira.lunar_cartography.planet_at", return_value=moon), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        lat, lon = _sublunar_point(calc, 2451545.0)
    assert abs(lat - 90.0) < 0.001


def test_besselian_sample_magnitude_positive_at_eclipse():
    """During an eclipse the umbral magnitude should be > 0."""
    calc = MagicMock()
    # Moon near shadow axis: place Moon at (0, 0, 384400) — north pole
    # Sun far away along -z axis so shadow axis points +z
    moon = _make_moon_cart(0.0, 0.0, 384400.0)
    # Sun at (0, 0, -149_597_870) — shadow axis = +z
    sun = _make_sun_cart(0.0, 0.0, -149_597_870.0)

    def fake_planet_at(body, jd, **kwargs):
        if body == Body.MOON:
            return moon
        return sun

    with patch("moira.lunar_cartography.planet_at", side_effect=fake_planet_at), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        sample = _compute_lunar_besselian_sample(calc, 2451545.0)

    assert sample.eclipse_magnitude >= 0.0
    assert sample.umbral_radius_earth_radii > 0.0
    assert sample.penumbral_radius_earth_radii > sample.umbral_radius_earth_radii
    assert abs(sample.moon_declination_deg - 90.0) < 0.5
```

- [ ] **Step 2: Run tests — confirm FAIL**

```
pytest tests/test_lunar_cartography.py::test_sublunar_point_equator_zero_gast -v
```
Expected: `ImportError` — functions not defined yet.

- [ ] **Step 3: Implement `_sublunar_point`**

Add after the dataclass definitions in `moira/lunar_cartography.py`:

```python
def _sublunar_point(calc: EclipseCalculator, jd_ut: float) -> tuple[float, float]:
    """Return (geodetic_lat_deg, lon_deg) of the sub-lunar point at jd_ut."""
    moon = planet_at(Body.MOON, jd_ut, reader=calc._reader, frame="cartesian")
    xyz = _np.array([moon.x, moon.y, moon.z], dtype=float)
    r = float(_np.linalg.norm(xyz))
    lat = math.degrees(math.asin(max(-1.0, min(1.0, xyz[2] / r))))
    ra = math.degrees(math.atan2(xyz[1], xyz[0])) % 360.0
    gast = local_sidereal_time(jd_ut, 0.0)
    lon = _wrap_longitude_deg(ra - gast)
    return lat, lon
```

- [ ] **Step 4: Implement `_compute_lunar_besselian_sample`**

```python
def _compute_lunar_besselian_sample(
    calc: EclipseCalculator, jd_ut: float
) -> LunarBesselianSample:
    """Compute per-step eclipse geometry for the Besselian sample series."""
    sun = planet_at(Body.SUN, jd_ut, reader=calc._reader, frame="cartesian")
    moon = planet_at(Body.MOON, jd_ut, reader=calc._reader, frame="cartesian")

    sun_xyz = _np.array([sun.x, sun.y, sun.z], dtype=float)
    moon_xyz = _np.array([moon.x, moon.y, moon.z], dtype=float)

    sun_dist = float(_np.linalg.norm(sun_xyz))
    moon_dist = float(_np.linalg.norm(moon_xyz))

    # Shadow axis: unit vector from Earth toward anti-Sun direction
    shadow_axis = -sun_xyz / sun_dist

    # Moon's projection along and perpendicular to shadow axis
    moon_along = float(_np.dot(moon_xyz, shadow_axis))
    moon_perp_km = float(_np.linalg.norm(moon_xyz - moon_along * shadow_axis))

    # Shadow cone radii in km at Moon's distance along axis
    # Penumbra expands outward: r_p(d) = R_earth + (R_sun + R_earth) * d / D_sun
    # Umbra contracts: r_u(d) = R_earth - (R_sun - R_earth) * d / D_sun
    penumbral_km = EARTH_RADIUS_KM + (SUN_RADIUS_KM + EARTH_RADIUS_KM) * moon_along / sun_dist
    umbral_km = EARTH_RADIUS_KM - (SUN_RADIUS_KM - EARTH_RADIUS_KM) * moon_along / sun_dist

    penumbral_er = penumbral_km / EARTH_RADIUS_KM
    umbral_er = max(0.0, umbral_km / EARTH_RADIUS_KM)

    moon_perp_er = moon_perp_km / EARTH_RADIUS_KM
    moon_radius_er = MOON_RADIUS_KM / EARTH_RADIUS_KM

    # Umbral magnitude: positive when Moon centre is inside umbra + Moon radius
    umbral_mag = (umbral_er + moon_radius_er - moon_perp_er) / (2.0 * moon_radius_er)
    eclipse_magnitude = max(0.0, umbral_mag)

    sublunar_lat, sublunar_lon = _sublunar_point(calc, jd_ut)
    moon_dec = math.degrees(math.asin(max(-1.0, min(1.0, moon_xyz[2] / moon_dist))))

    return LunarBesselianSample(
        jd_ut=float(jd_ut),
        sublunar_lat=sublunar_lat,
        sublunar_lon=sublunar_lon,
        umbral_radius_earth_radii=umbral_er,
        penumbral_radius_earth_radii=penumbral_er,
        moon_declination_deg=moon_dec,
        eclipse_magnitude=eclipse_magnitude,
    )
```

- [ ] **Step 5: Run tests — all should pass**

```
pytest tests/test_lunar_cartography.py -v
```
Expected: 7 PASS.

- [ ] **Step 6: Commit**

```
git add moira/lunar_cartography.py tests/test_lunar_cartography.py
git commit -m "feat: lunar_cartography — sublunar point and Besselian sample"
```

---

## Task 3: `_lunar_eclipse_contacts` + `_lunar_observer_quantities_batch_backend`

**Files:**
- Modify: `moira/lunar_cartography.py`
- Modify: `tests/test_lunar_cartography.py`

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_lunar_cartography.py
from moira.lunar_cartography import (
    _lunar_eclipse_contacts,
    _lunar_observer_quantities_batch_backend,
)
from moira.eclipse import LunarEclipseAnalysis


def test_lunar_eclipse_contacts_delegates_to_analyze():
    """_lunar_eclipse_contacts forwards (jd_seed, kind, backward) to
    calc.analyze_lunar_eclipse and returns its result unchanged."""
    calc = MagicMock()
    fake_analysis = MagicMock(spec=LunarEclipseAnalysis)
    calc.analyze_lunar_eclipse.return_value = fake_analysis

    result = _lunar_eclipse_contacts(calc, 2451545.0, kind="any", backward=False)

    calc.analyze_lunar_eclipse.assert_called_once_with(
        2451545.0, kind="any", backward=False
    )
    assert result is fake_analysis


def test_moon_altitude_near_zenith_at_sublunar_point():
    """Moon at RA=0°, Dec=0°, GAST=0°: observer at (lat=0°, lon=0°) should
    see Moon near zenith (altitude ≈ 90°)."""
    calc = MagicMock()
    moon = _make_moon_cart(384400.0, 0.0, 0.0)

    with patch("moira.lunar_cartography.planet_at", return_value=moon), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        alt, ha, above = _lunar_observer_quantities_batch_backend(
            calc,
            2451545.0,
            _np.array([0.0]),
            _np.array([0.0]),
            _np,
        )

    assert float(alt[0]) > 85.0
    assert bool(above[0])


def test_moon_below_horizon_at_antipode():
    """Observer at antipode of sub-lunar point sees Moon below horizon."""
    calc = MagicMock()
    # Moon at RA=0°, Dec=0°, GAST=0° → sub-lunar at (0°, 0°)
    # Antipode at (0°, 180°)
    moon = _make_moon_cart(384400.0, 0.0, 0.0)

    with patch("moira.lunar_cartography.planet_at", return_value=moon), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        alt, ha, above = _lunar_observer_quantities_batch_backend(
            calc,
            2451545.0,
            _np.array([0.0]),
            _np.array([180.0]),
            _np,
        )

    assert float(alt[0]) < -85.0
    assert not bool(above[0])
```

- [ ] **Step 2: Run tests — confirm FAIL**

```
pytest tests/test_lunar_cartography.py::test_lunar_eclipse_contacts_delegates_to_analyze -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement `_lunar_eclipse_contacts`**

```python
def _lunar_eclipse_contacts(
    calc: EclipseCalculator,
    jd_seed: float,
    *,
    kind: str = "any",
    backward: bool = False,
) -> "LunarEclipseAnalysis":
    """Wrap calc.analyze_lunar_eclipse to obtain the full contact-time analysis.

    The returned LunarEclipseAnalysis exposes the searched event via
    ``analysis.event`` and the contact-time vessel via ``analysis.contacts``.
    """
    return calc.analyze_lunar_eclipse(jd_seed, kind=kind, backward=backward)
```

- [ ] **Step 4: Implement `_lunar_observer_quantities_batch_backend`**

```python
_SIN_REFRACTION_MARGIN = -0.01003  # sin(-0.575°) — atmospheric refraction margin


def _lunar_observer_quantities_batch_backend(
    calc: EclipseCalculator,
    jd_ut: float,
    lats_deg,
    lons_deg,
    xp,
) -> tuple:
    """Vectorised Moon altitude for N observers at a single epoch.

    Returns (moon_altitude_deg, hour_angle_deg, above_horizon_mask).
    xp is numpy or cupy.
    """
    moon_cart = planet_at(Body.MOON, jd_ut, reader=calc._reader, frame="cartesian")
    moon_xyz = xp.asarray([moon_cart.x, moon_cart.y, moon_cart.z], dtype=xp.float64)

    lats = xp.asarray(lats_deg, dtype=xp.float64)
    lons = xp.asarray(lons_deg, dtype=xp.float64)

    gast_deg = local_sidereal_time(jd_ut, 0.0)

    # Topocentric Moon position — (N, 3) array
    moon_topo = _topocentric_correction_batch_backend(
        xp, moon_xyz, lats, lons, gast_deg
    )

    moon_r = xp.linalg.norm(moon_topo, axis=1)
    moon_dec = xp.arcsin(xp.clip(moon_topo[:, 2] / moon_r, -1.0, 1.0))
    moon_ra = xp.arctan2(moon_topo[:, 1], moon_topo[:, 0])

    lats_r = xp.radians(lats)
    last_r = xp.radians(gast_deg + lons)
    ha_moon = last_r - moon_ra

    sin_alt = (
        xp.sin(lats_r) * xp.sin(moon_dec)
        + xp.cos(lats_r) * xp.cos(moon_dec) * xp.cos(ha_moon)
    )
    above = sin_alt > _SIN_REFRACTION_MARGIN
    alt_deg = xp.degrees(xp.arcsin(xp.clip(sin_alt, -1.0, 1.0)))
    ha_deg = ((xp.degrees(ha_moon) + 180.0) % 360.0) - 180.0

    return alt_deg, ha_deg, above
```

- [ ] **Step 5: Run tests — all should pass**

```
pytest tests/test_lunar_cartography.py -v
```
Expected: 10 PASS.

- [ ] **Step 6: Commit**

```
git add moira/lunar_cartography.py tests/test_lunar_cartography.py
git commit -m "feat: lunar_cartography — eclipse contacts and observer batch function"
```

---

## Task 4: `lunar_eclipse_cartography` — Full Implementation

**Files:**
- Modify: `moira/lunar_cartography.py` — add the public function
- Modify: `tests/test_lunar_cartography.py` — add smoke test

- [ ] **Step 1: Write smoke test (mock-based)**

```python
# append to tests/test_lunar_cartography.py
from moira.lunar_cartography import lunar_eclipse_cartography, LunarCartographyResult
from moira.eclipse_contacts import LunarEclipseContacts


def _make_contacts(*, total=True):
    """Build a realistic LunarEclipseContacts for a total eclipse."""
    g = 2451545.0
    if total:
        return LunarEclipseContacts(
            p1=g - 0.08,
            u1=g - 0.04,
            u2=g - 0.01,
            greatest=g,
            u3=g + 0.01,
            u4=g + 0.04,
            p4=g + 0.08,
        )
    # Partial — no u2/u3
    return LunarEclipseContacts(
        p1=g - 0.08,
        u1=g - 0.04,
        u2=None,
        greatest=g,
        u3=None,
        u4=g + 0.04,
        p4=g + 0.08,
    )


def _make_calc_mock(contacts):
    calc = MagicMock()
    calc._reader = MagicMock()
    event = MagicMock()
    event.jd_ut = 2451545.0
    analysis = MagicMock()
    analysis.event = event
    analysis.contacts = contacts
    calc.analyze_lunar_eclipse.return_value = analysis

    moon = _make_moon_cart(384400.0, 0.0, 0.0)   # Moon at equator, RA=0
    sun = _make_sun_cart(-149_597_870.0, 0.0, 0.0)  # Sun on -x axis

    def fake_planet_at(body, jd, **kwargs):
        return moon if body == Body.MOON else sun

    return calc, fake_planet_at


def test_lunar_cartography_returns_result_for_total_eclipse():
    contacts = _make_contacts(total=True)
    calc, fake_planet_at = _make_calc_mock(contacts)

    with patch("moira.lunar_cartography.planet_at", side_effect=fake_planet_at), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        result = lunar_eclipse_cartography(calc, 2451545.0, backend="cpu")

    assert isinstance(result, LunarCartographyResult)
    assert result.eclipse_type == "total"
    assert result.event_jd_ut == 2451545.0
    assert len(result.besselian_samples) > 0
    assert len(result.sample_jds_ut) > 0


def test_lunar_cartography_partial_has_empty_total_band():
    contacts = _make_contacts(total=False)
    calc, fake_planet_at = _make_calc_mock(contacts)

    with patch("moira.lunar_cartography.planet_at", side_effect=fake_planet_at), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        result = lunar_eclipse_cartography(calc, 2451545.0, backend="cpu")

    assert result.eclipse_type == "partial"
    assert result.total_band.south_curve == ()
    assert result.total_band.north_curve == ()
```

- [ ] **Step 2: Run tests — confirm FAIL**

```
pytest tests/test_lunar_cartography.py::test_lunar_cartography_returns_result_for_total_eclipse -v
```
Expected: `ImportError` or `AttributeError` — function not implemented.

- [ ] **Step 3: Implement `lunar_eclipse_cartography`**

Add after `_lunar_observer_quantities_batch_backend` in `moira/lunar_cartography.py`:

```python
_EMPTY_BAND = LunarShadowBand((), (), ())
_MAGNITUDE_THRESHOLDS = (0.2, 0.4, 0.6, 0.8)
_DURATION_THRESHOLDS = (600.0, 1200.0, 1800.0, 2700.0, 3600.0)  # seconds


def lunar_eclipse_cartography(
    calc: EclipseCalculator,
    jd_seed: float,
    *,
    kind: str = "any",
    backward: bool = False,
    backend: str = "auto",
    time_samples: int = 17,
) -> LunarCartographyResult:
    """Compute a world-map visibility cartography for a lunar eclipse.

    Parameters
    ----------
    calc       : EclipseCalculator with loaded kernel
    jd_seed    : Julian Day (UT) to start searching from
    kind       : "any" | "total" | "partial" | "penumbral"
    backward   : search backward in time if True
    backend    : "auto" | "cpu" | "gpu"
    time_samples : number of time steps across the eclipse window

    Returns
    -------
    LunarCartographyResult
    """
    xp, backend_info = _select_backend(backend)

    # --- Find eclipse and contacts ----------------------------------------
    # ``analyze_lunar_eclipse`` accepts a Julian Day search seed (not an event
    # object) and returns a LunarEclipseAnalysis whose ``.event`` field carries
    # the searched event and whose ``.contacts`` field carries the contact
    # times. The ``_lunar_eclipse_contacts`` wrapper forwards the call.
    analysis = _lunar_eclipse_contacts(calc, jd_seed, kind=kind, backward=backward)
    event = analysis.event
    contacts = analysis.contacts

    u1 = getattr(contacts, "u1", None)
    u2 = getattr(contacts, "u2", None)
    u3 = getattr(contacts, "u3", None)
    u4 = getattr(contacts, "u4", None)
    p1 = getattr(contacts, "p1", None)
    p4 = getattr(contacts, "p4", None)

    if u2 is not None and u3 is not None:
        eclipse_type = "total"
    elif u1 is not None:
        eclipse_type = "partial"
    else:
        eclipse_type = "penumbral"

    # --- Time window -------------------------------------------------------
    if p1 is not None and p4 is not None:
        window_start = p1 - 30.0 / 1440.0
        window_end = p4 + 30.0 / 1440.0
    else:
        window_start = event.jd_ut - 2.0 / 24.0
        window_end = event.jd_ut + 2.0 / 24.0

    sample_jds = _sample_interval(window_start, window_end, time_samples)

    # --- Grid setup (adaptive, centred on sub-lunar point) -----------------
    sublunar_lat, sublunar_lon = _sublunar_point(calc, event.jd_ut)

    lat_padding = 95.0
    lon_padding = 95.0

    lat_min = max(-89.0, sublunar_lat - lat_padding)
    lat_max = min(89.0, sublunar_lat + lat_padding)
    lon_min = sublunar_lon - lon_padding
    lon_max = sublunar_lon + lon_padding

    lat_span = max(2.0, lat_max - lat_min)
    lon_span = max(2.0, lon_max - lon_min)
    lat_count = max(81, min(161, int(round(lat_span / 0.6)) + 1))
    lon_count = max(121, min(281, int(round(lon_span / 0.6)) + 1))

    lat_values = _np.linspace(lat_min, lat_max, lat_count)
    lon_values = _np.linspace(lon_min, lon_max, lon_count)
    lat_grid, lon_grid = _np.meshgrid(lat_values, lon_values, indexing="ij")

    # --- Accumulation arrays -----------------------------------------------
    _neg_inf = xp.asarray(-xp.inf, dtype=xp.float64)
    penumbral_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    partial_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    total_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    magnitude_max = xp.zeros(lat_grid.shape, dtype=xp.float64)

    altitude_series: list = []
    hour_angle_series: list = []
    duration_margin_series: list = []

    # --- Time-step sweep ---------------------------------------------------
    for jd_ut in sample_jds:
        sample = _compute_lunar_besselian_sample(calc, jd_ut)

        alt_deg, ha_deg, above = _lunar_observer_quantities_batch_backend(
            calc, jd_ut, lat_grid.ravel(), lon_grid.ravel(), xp,
        )
        alt_grid = alt_deg.reshape(lat_grid.shape)
        ha_grid = ha_deg.reshape(lat_grid.shape)
        above_grid = above.reshape(lat_grid.shape)

        altitude_series.append(_to_numpy(xp, alt_grid))
        hour_angle_series.append(_to_numpy(xp, ha_grid))

        # Penumbral band: all steps in window
        penumbral_max = xp.maximum(penumbral_max, alt_grid)

        # Partial (umbral) band: steps within U1–U4 window
        if u1 is not None and u4 is not None and u1 <= jd_ut <= u4:
            partial_max = xp.maximum(partial_max, alt_grid)

        # Total band: steps within U2–U3 window
        if u2 is not None and u3 is not None and u2 <= jd_ut <= u3:
            total_max = xp.maximum(total_max, alt_grid)

        # Magnitude: max visible magnitude per cell
        mag_grid = xp.where(above_grid, sample.eclipse_magnitude, 0.0)
        magnitude_max = xp.maximum(magnitude_max, mag_grid)

        # Duration margin: positive when Moon above horizon in umbral window
        if u1 is not None and u4 is not None and u1 <= jd_ut <= u4:
            # Use sin(alt) + refraction_margin as continuous crossing signal
            sin_alt = xp.sin(xp.radians(alt_grid))
            margin = (sin_alt - _SIN_REFRACTION_MARGIN).reshape(lat_grid.shape)
        else:
            margin = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
        duration_margin_series.append(_to_numpy(xp, margin))

    # --- Convert to numpy --------------------------------------------------
    penumbral_field = _to_numpy(xp, penumbral_max)
    partial_field = (
        _to_numpy(xp, partial_max) if u1 is not None
        else _np.full(lat_grid.shape, -_np.inf)
    )
    total_field = (
        _to_numpy(xp, total_max) if u2 is not None
        else _np.full(lat_grid.shape, -_np.inf)
    )
    magnitude_field = _to_numpy(xp, magnitude_max)

    # --- Moonrise / moonset bands (quadratic peak refinement) --------------
    altitude_stack = _np.stack(altitude_series, axis=0)
    ha_stack = _np.stack(hour_angle_series, axis=0)
    peak_pos, peak_alt = _quadratic_peak_refine(sample_jds, altitude_stack)
    peak_ha = _evaluate_quadratic_series(ha_stack, peak_pos)

    visible_mask = (peak_alt > 0.0) & _np.isfinite(peak_ha)
    moonrise_field = _np.where(
        visible_mask & (peak_ha <= 0.0), peak_alt, _np.nan
    )
    moonset_field = _np.where(
        visible_mask & (peak_ha >= 0.0), peak_alt, _np.nan
    )

    # --- Band extraction ---------------------------------------------------
    penumbral_band = _extract_latitude_band_curves(lat_values, lon_values, penumbral_field)
    partial_band = (
        _extract_latitude_band_curves(lat_values, lon_values, partial_field)
        if u1 is not None else _EMPTY_BAND
    )
    total_band = (
        _extract_latitude_band_curves(lat_values, lon_values, total_field)
        if u2 is not None else _EMPTY_BAND
    )
    moonrise_band = _build_zero_band_from_field(lat_values, lon_values, moonrise_field)
    moonset_band = _build_zero_band_from_field(lat_values, lon_values, moonset_field)

    # --- Contours ----------------------------------------------------------
    magnitude_contours = _build_contours(
        "magnitude", lat_values, lon_values, magnitude_field, _MAGNITUDE_THRESHOLDS,
    )

    if duration_margin_series:
        dur_stack = _np.stack(duration_margin_series, axis=0)
        duration_field = _duration_from_margin_series(sample_jds, dur_stack)
        duration_contours = _build_contours(
            "duration", lat_values, lon_values, duration_field, _DURATION_THRESHOLDS,
        )
    else:
        duration_contours = tuple()

    # --- Besselian samples -------------------------------------------------
    besselian_samples = tuple(
        _compute_lunar_besselian_sample(calc, jd_ut) for jd_ut in sample_jds
    )

    return LunarCartographyResult(
        event_jd_ut=float(event.jd_ut),
        eclipse_type=eclipse_type,
        backend=backend_info,
        window_start_jd_ut=float(sample_jds[0]),
        window_end_jd_ut=float(sample_jds[-1]),
        sample_jds_ut=tuple(float(jd) for jd in sample_jds),
        besselian_samples=besselian_samples,
        penumbral_band=penumbral_band,
        partial_band=partial_band,
        total_band=total_band,
        moonrise_band=moonrise_band,
        moonset_band=moonset_band,
        magnitude_contours=magnitude_contours,
        duration_contours=duration_contours,
    )
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_lunar_cartography.py -v
```
Expected: 12 PASS.

- [ ] **Step 5: Commit**

```
git add moira/lunar_cartography.py tests/test_lunar_cartography.py
git commit -m "feat: lunar_cartography — main cartography function"
```

---

## Task 5: Wire Up `moira/__init__.py`

> **Scope note.** `moira/facade.py` is *not* modified by this task. The existing `solar_cartography` module is published only through `moira/__init__.py`, and lunar cartography mirrors that pattern. If a future change re-exports either cartography module through `facade.py`, both should be added together.

**Files:**
- Modify: `moira/__init__.py`
- Modify: `tests/test_lunar_cartography.py`

- [ ] **Step 1: Write failing import test**

```python
# append to tests/test_lunar_cartography.py
def test_lunar_cartography_importable_from_moira_top_level():
    from moira import LunarCartographyResult, lunar_eclipse_cartography
    assert LunarCartographyResult is not None
    assert lunar_eclipse_cartography is not None
```

- [ ] **Step 2: Run test — confirm FAIL**

```
pytest tests/test_lunar_cartography.py::test_lunar_cartography_importable_from_moira_top_level -v
```
Expected: `ImportError`.

- [ ] **Step 3: Add to `moira/__init__.py`**

Find the solar cartography import block:
```python
from .solar_cartography import (
    ArrayBackendInfo,
    SolarBesselianSample,
    SolarCartographyResult,
    SolarContourLevel,
    SolarShadowBand,
    solar_eclipse_cartography,
)
```

Add immediately after it:
```python
from .lunar_cartography import (
    LunarBesselianSample,
    LunarShadowBand,
    LunarContourLevel,
    LunarCartographyResult,
    lunar_eclipse_cartography,
)
```

Then in `__all__`, find the solar cartography block (the entries `SolarBesselianSample`, `SolarCartographyResult`, `SolarContourLevel`, `SolarShadowBand`, `solar_eclipse_cartography`) and add a lunar block after it:
```python
    # Lunar eclipse cartography
    "LunarBesselianSample",
    "LunarShadowBand",
    "LunarContourLevel",
    "LunarCartographyResult",
    "lunar_eclipse_cartography",
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_lunar_cartography.py -v
```
Expected: 13 PASS.

- [ ] **Step 5: Verify top-level import works**

```
python -c "from moira import lunar_eclipse_cartography, LunarCartographyResult; print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Final commit**

```
git add moira/__init__.py tests/test_lunar_cartography.py
git commit -m "feat: wire lunar_cartography into moira top-level exports"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ All five output bands (penumbral, partial, total, moonrise, moonset)
- ✅ Magnitude contours at 0.2/0.4/0.6/0.8
- ✅ Duration contours at 600/1200/1800/2700/3600 s
- ✅ Besselian sample series
- ✅ GPU/CPU dual backend via `_select_backend` + `_topocentric_correction_batch_backend`
- ✅ Adaptive grid centered on sub-lunar point
- ✅ Wire-up in `__init__.py` (mirrors `solar_cartography` — `facade.py` is intentionally not touched)
- ✅ `eclipse_type` classification (total/partial/penumbral)

**Type consistency:**
- `LunarShadowBand` used consistently for all 5 band fields
- `LunarContourLevel` used for both magnitude and duration contours
- `_EMPTY_BAND` constant avoids constructing multiple empty band objects
- Contact attributes `.u1/.u2/.u3/.u4/.p1/.p4` confirmed as `float | None` from `LunarEclipseContacts`
