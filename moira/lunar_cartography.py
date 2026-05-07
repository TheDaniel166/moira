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
from .eclipse import EclipseCalculator, LunarEclipseAnalysis
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
    """Vessel: Geometric sample of lunar eclipse conditions at a specific epoch."""
    jd_ut: float
    sublunar_lat: float
    sublunar_lon: float
    umbral_radius_earth_radii: float
    penumbral_radius_earth_radii: float
    moon_declination_deg: float
    eclipse_magnitude: float


@dataclass(frozen=True, slots=True)
class LunarShadowBand:
    """Vessel: Geometric representation of a lunar shadow or visibility band."""
    south_curve: tuple[tuple[float, float], ...]
    north_curve: tuple[tuple[float, float], ...]
    polygon: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class LunarContourLevel:
    """Vessel: Representation of an isoline or contour in lunar cartography."""
    kind: str
    threshold: float
    south_curve: tuple[tuple[float, float], ...]
    north_curve: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class LunarCartographyResult:
    """Vessel: Complete cartographic model for a lunar eclipse event."""
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


_SIN_REFRACTION_MARGIN = -0.01003  # sin(-0.575°) — atmospheric refraction margin


def _lunar_eclipse_contacts(
    calc: EclipseCalculator,
    jd_seed: float,
    *,
    kind: str = "any",
    backward: bool = False,
) -> LunarEclipseAnalysis:
    """Wrap calc.analyze_lunar_eclipse to obtain the full contact-time analysis.

    The returned LunarEclipseAnalysis exposes the searched event via
    ``analysis.event`` and the contact-time vessel via ``analysis.contacts``.
    """
    return calc.analyze_lunar_eclipse(jd_seed, kind=kind, backward=backward)


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



_EMPTY_BAND = LunarShadowBand((), (), ())
_MAGNITUDE_THRESHOLDS = (0.2, 0.4, 0.6, 0.8)
_DURATION_THRESHOLDS = (600.0, 1200.0, 1800.0, 2700.0, 3600.0)


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
    """
    xp, backend_info = _select_backend(backend)

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

    if p1 is not None and p4 is not None:
        window_start = p1 - 30.0 / 1440.0
        window_end = p4 + 30.0 / 1440.0
    else:
        window_start = event.jd_ut - 2.0 / 24.0
        window_end = event.jd_ut + 2.0 / 24.0

    sample_jds = _sample_interval(window_start, window_end, time_samples)

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

    # Native Fast Path
    if backend_info.name == "moira-native":
        try:
            from . import moira_native
            
            # Prepare arrays
            jd_arr = _np.array(sample_jds, dtype=float)
            gast_arr = _np.array([local_sidereal_time(jd, 0.0) for jd in sample_jds], dtype=float)
            
            # Compute magnitudes (geocentric) for each JD
            mag_base_arr = _np.array([
                _compute_lunar_besselian_sample(calc, jd).eclipse_magnitude 
                for jd in sample_jds
            ], dtype=float)
            
            lat_arr = lat_grid.ravel().astype(float)
            lon_arr = lon_grid.ravel().astype(float)
            
            # Allocate results
            penumbral_max_arr = _np.full(lat_arr.shape, -1e18, dtype=float)
            partial_max_arr = _np.full(lat_arr.shape, -1e18, dtype=float)
            total_max_arr = _np.full(lat_arr.shape, -1e18, dtype=float)
            magnitude_max_arr = _np.zeros(lat_arr.shape, dtype=float)

            u1_u4 = _np.array([u1, u4], dtype=float) if u1 is not None else None
            u2_u3 = _np.array([u2, u3], dtype=float) if u2 is not None else None

            # Get native evaluators
            sun_eval = calc._reader.evaluator(Body.SUN, frame="cartesian")
            moon_eval = calc._reader.evaluator(Body.MOON, frame="cartesian")
            
            moira_native.lunar_cartography_grid_sweep(
                sun_eval, moon_eval, jd_arr, gast_arr, mag_base_arr,
                lat_arr, lon_arr,
                penumbral_max_arr, partial_max_arr, total_max_arr, magnitude_max_arr,
                u1_u4, u2_u3
            )
            
            penumbral_max = penumbral_max_arr.reshape(lat_grid.shape)
            partial_max = partial_max_arr.reshape(lat_grid.shape)
            total_max = total_max_arr.reshape(lat_grid.shape)
            magnitude_max = magnitude_max_arr.reshape(lat_grid.shape)
        except (ImportError, AttributeError):
            pass

    penumbral_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    partial_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    total_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    magnitude_max = xp.zeros(lat_grid.shape, dtype=xp.float64)

    altitude_series: list = []
    hour_angle_series: list = []
    duration_margin_series: list = []

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

        penumbral_max = xp.maximum(penumbral_max, alt_grid)

        if u1 is not None and u4 is not None and u1 <= jd_ut <= u4:
            partial_max = xp.maximum(partial_max, alt_grid)

        if u2 is not None and u3 is not None and u2 <= jd_ut <= u3:
            total_max = xp.maximum(total_max, alt_grid)

        mag_grid = xp.where(above_grid, sample.eclipse_magnitude, 0.0)
        magnitude_max = xp.maximum(magnitude_max, mag_grid)

        if u1 is not None and u4 is not None and u1 <= jd_ut <= u4:
            sin_alt = xp.sin(xp.radians(alt_grid))
            margin = (sin_alt - _SIN_REFRACTION_MARGIN).reshape(lat_grid.shape)
        else:
            margin = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
        duration_margin_series.append(_to_numpy(xp, margin))

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
