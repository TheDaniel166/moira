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
from .eclipse import EclipseCalculator
from .julian import local_sidereal_time
from .planets import planet_at
from .solar_cartography import (
    ArrayBackendInfo,
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
