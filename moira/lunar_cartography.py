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
