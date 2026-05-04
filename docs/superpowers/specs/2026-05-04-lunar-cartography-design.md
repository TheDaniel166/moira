# Lunar Eclipse Cartography — Design Spec
**Date:** 2026-05-04  
**Module:** `moira/lunar_cartography.py`  
**Template:** `moira/solar_cartography.py` (Approach A — direct port of sweep pattern)

---

## Overview

`lunar_cartography.py` maps where on Earth a lunar eclipse is visible, to what depth, and for how long. Unlike solar eclipse cartography (which maps where a shadow falls on Earth's surface), lunar cartography maps observer visibility: the eclipse geometry is identical for all observers; what varies is whether the Moon is above the horizon, and during which phases.

The module produces a `LunarCartographyResult` containing visibility bands for penumbral, partial, and total phases; moonrise/moonset transition bands; magnitude isolines; and duration contours.

---

## Data Structures

All dataclasses are `frozen=True, slots=True`. `ArrayBackendInfo` is imported directly from `solar_cartography`.

### `LunarBesselianSample`
Per time-step geometry snapshot.

| Field | Type | Description |
|---|---|---|
| `jd_ut` | `float` | Julian Day (UT) of sample |
| `sublunar_lat` | `float` | Geodetic latitude of sub-lunar point (degrees) |
| `sublunar_lon` | `float` | East longitude of sub-lunar point (degrees) |
| `umbral_radius_earth_radii` | `float` | Umbral shadow radius in Earth radii |
| `penumbral_radius_earth_radii` | `float` | Penumbral shadow radius in Earth radii |
| `moon_declination_deg` | `float` | Moon's declination at this step |
| `eclipse_magnitude` | `float` | Umbral eclipse magnitude (0 = no umbral contact) |

### `LunarShadowBand`
Identical structure to `SolarShadowBand`.

| Field | Type | Description |
|---|---|---|
| `south_curve` | `tuple[tuple[float, float], ...]` | (lat, lon) points on southern boundary |
| `north_curve` | `tuple[tuple[float, float], ...]` | (lat, lon) points on northern boundary |
| `polygon` | `tuple[tuple[float, float], ...]` | Closed polygon (north + reversed south) |

### `LunarContourLevel`
Identical structure to `SolarContourLevel`.

| Field | Type | Description |
|---|---|---|
| `kind` | `str` | `"magnitude"` or `"duration"` |
| `threshold` | `float` | Magnitude (0–1) or duration (seconds) threshold |
| `south_curve` | `tuple[tuple[float, float], ...]` | Southern isoline |
| `north_curve` | `tuple[tuple[float, float], ...]` | Northern isoline |

### `LunarCartographyResult`
Top-level output vessel.

| Field | Type | Description |
|---|---|---|
| `event_jd_ut` | `float` | JD of greatest eclipse |
| `eclipse_type` | `str` | `"penumbral"`, `"partial"`, or `"total"` |
| `backend` | `ArrayBackendInfo` | CPU or GPU backend used |
| `window_start_jd_ut` | `float` | Start of time window swept |
| `window_end_jd_ut` | `float` | End of time window swept |
| `sample_jds_ut` | `tuple[float, ...]` | All sampled Julian Days |
| `besselian_samples` | `tuple[LunarBesselianSample, ...]` | Per-step geometry |
| `penumbral_band` | `LunarShadowBand` | Moon above horizon during P1–P4 |
| `partial_band` | `LunarShadowBand` | Moon above horizon during U1–U4 |
| `total_band` | `LunarShadowBand` | Moon above horizon during U2–U3 (total eclipses only; empty otherwise) |
| `moonrise_band` | `LunarShadowBand` | Eclipse already underway at moonrise |
| `moonset_band` | `LunarShadowBand` | Eclipse still active at moonset |
| `magnitude_contours` | `tuple[LunarContourLevel, ...]` | Max visible umbral magnitude isolines |
| `duration_contours` | `tuple[LunarContourLevel, ...]` | Seconds of umbral visibility isolines |

---

## Grid & Sweep Architecture

### Grid Center
Sub-lunar point at greatest eclipse — where the Moon is at zenith. Natural center of the visibility hemisphere.

### Grid Bounds
**Partial/penumbral grid:**
- Bounds: sub-lunar lat/lon ± 95° (90° visibility radius + 5° moonrise/moonset margin)
- Clamped to ±89° latitude
- Resolution: ~0.6° → approximately 130 lat × 260 lon points
- Longitude padding adjusted for cos(lat) of mean track latitude

**Total grid (total eclipses only):**
- Bounds: sub-lunar lat/lon ± 45°
- Resolution: ~0.22° → approximately 180 lat × 360 lon points
- Computed only when eclipse type is `"total"`

### Time Window
- Start: P1 − 30 minutes (or event − 2 hours for penumbral-only)
- End: P4 + 30 minutes (or event + 2 hours for penumbral-only)
- Default: 17 time samples uniformly distributed across window

### Metric Per Grid Point Per Time Step
Moon altitude computed via:
```
sin(alt) = sin(lat)·sin(dec) + cos(lat)·cos(dec)·cos(HA)
```
Vectorized over N grid points using `topocentric_correction_batch_np` → RA/Dec → hour angle → altitude. Refraction margin: `sin(alt) > -0.01003` (same as solar, equivalent to ~0.575° below geometric horizon).

### Accumulated Fields
| Field | Content |
|---|---|
| `penumbral_max` | Max Moon altitude across all time steps within P1–P4 window |
| `partial_max` | Max Moon altitude across time steps within U1–U4 window |
| `total_max` | Max Moon altitude across time steps within U2–U3 window |
| `magnitude_max` | Max (eclipse_magnitude × moon_above_horizon) across all steps |
| `duration_field` | Total seconds Moon above horizon AND eclipse active (via margin series integration) |

### Band Extraction
- Visibility bands: `field > 0` threshold, same `_extract_latitude_band_curves` logic as solar
- Moonrise band: peak hour angle ≤ 0 AND Moon above horizon (eclipse occurs in eastern sky — Moon rising)
- Moonset band: peak hour angle ≥ 0 AND Moon above horizon (eclipse occurs in western sky — Moon setting)
- Magnitude contour thresholds: 0.2, 0.4, 0.6, 0.8
- Duration contour thresholds: 600, 1200, 1800, 2700, 3600 seconds (10, 20, 30, 45, 60 min) — lunar totality can reach ~107 min; these thresholds cover the meaningful range

---

## Public API

```python
def lunar_eclipse_cartography(
    calc: EclipseCalculator,
    jd_seed: float,
    *,
    kind: str = "any",       # "total" | "partial" | "penumbral" | "any"
    backward: bool = False,
    backend: str = "auto",   # "auto" | "cpu" | "gpu"
    time_samples: int = 17,
) -> LunarCartographyResult:
```

Mirrors `solar_eclipse_cartography` signature exactly.

---

## Private Function Decomposition

### `_sublunar_point(calc, jd_ut) -> tuple[float, float]`
Computes (lat, lon) where Moon is at zenith.  
Uses `planet_at(Body.MOON, jd_ut, frame='cartesian')` → RA/Dec → subtract GAST for longitude.

### `_lunar_eclipse_contacts(calc, event) -> LunarEclipseAnalysis`
Wraps `calc.analyze_lunar_eclipse(event)`. Returns the full analysis with all contact times. Handles gracefully:
- Penumbral-only: no U contacts (U1/U2/U3/U4 = None)
- Partial: no U2/U3 (no totality)
- Total: all contacts present

### `_lunar_observer_quantities_batch_backend(calc, jd_ut, lats, lons, xp) -> tuple[ndarray, ndarray, ndarray]`
Vectorized over N observers. Returns `(moon_altitude_deg, hour_angle_deg, above_horizon_mask)`.  
Uses `topocentric_correction_batch_np` (CPU) or inline CuPy WGS-84 math (GPU), identical pattern to `_topocentric_solar_observer_quantities_batch_backend`. Eclipse magnitude is a scalar per time step accumulated separately in the sweep loop — not a per-observer quantity and not a parameter here.

### `_compute_lunar_besselian_sample(calc, jd_ut) -> LunarBesselianSample`
Computes per-step geometry: sub-lunar point via `_sublunar_point`, umbral/penumbral shadow radii from Moon–Earth–Sun cone geometry using `MOON_RADIUS_KM`, `EARTH_RADIUS_KM`, `SUN_RADIUS_KM`. Eclipse magnitude computed per step as `(penumbral_radius - moon_distance_to_axis) / (2 × moon_angular_radius)` clamped to [0, ∞) — same formula used by `EclipseCalculator._calculate_jd_internal`. This gives a continuous magnitude field across the time window, not just at greatest.

### `_select_backend`
Imported directly from `solar_cartography` — no duplication. This cross-module private import is consistent with Moira's established pattern (solar_cartography itself imports `_search_solar_eclipse`, `_bisection_root`, etc. from eclipse.py).

---

## Dependencies

| Source | Symbols |
|---|---|
| `.eclipse` | `EclipseCalculator`, `_search_lunar_eclipse` |
| `.corrections` | `topocentric_correction_batch_np` |
| `.constants` | `EARTH_RADIUS_KM`, `MOON_RADIUS_KM`, `SUN_RADIUS_KM`, `Body` |
| `.julian` | `local_sidereal_time` |
| `.planets` | `planet_at` |
| `solar_cartography` | `ArrayBackendInfo`, `_select_backend`, `_to_numpy`, `_wrap_longitude_deg`, `_unwrap_longitudes`, `_sample_interval`, `_extract_latitude_band_curves`, `_build_contours`, `_build_zero_band_from_field`, `_duration_from_margin_series`, `_quadratic_peak_refine`, `_evaluate_quadratic_series` |

The reuse of solar_cartography private helpers is intentional — they are pure geometric/statistical utilities with no solar-specific logic.

---

## `__all__`
```python
__all__ = [
    "LunarBesselianSample",
    "LunarShadowBand",
    "LunarContourLevel",
    "LunarCartographyResult",
    "lunar_eclipse_cartography",
]
```

---

## Wire-up (after implementation)
- `moira/__init__.py` — import and add to `__all__`
- `moira/facade.py` — import and add to `__all__`
