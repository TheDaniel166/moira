"""
Moira - solar_cartography.py

Solar eclipse cartography subsystem with optional GPU-backed array operations.

This module computes Besselian-style fundamental-plane samples for a searched
solar eclipse and derives event-wide partial and central shadow envelopes by
sweeping a topocentric grid across the eclipse window. GPU acceleration is
optional: when CuPy is installed and a CUDA device is available, the array
portion of the cartography sweep can run on the GPU; otherwise it falls back
to NumPy on the CPU.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as _np

try:
    import cupy as _cp
except ImportError:  # pragma: no cover - optional dependency
    _cp = None

from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM, Body
from .corrections import topocentric_correction_batch_np
from .eclipse import (
    EclipseCalculator,
    _bisection_root,
    _solve_solar_central_interval,
    _solve_solar_greatest_location,
    _topocentric_solar_geometry,
)
from .julian import local_sidereal_time
from .planets import planet_at

__all__ = [
    "ArrayBackendInfo",
    "SolarBesselianSample",
    "SolarContourLevel",
    "SolarShadowBand",
    "SolarCartographyResult",
    "solar_eclipse_cartography",
]

_KM_PER_DEG_LAT = 111.32
_SOLAR_PATH_SEED_EPSILON_DAYS = 0.001


@dataclass(frozen=True, slots=True)
class ArrayBackendInfo:
    """Vessel: Information about the selected array computation backend."""
    name: str
    is_gpu: bool


@dataclass(frozen=True, slots=True)
class SolarBesselianSample:
    """Vessel: Besselian elements for a specific instant in a solar eclipse."""
    jd_ut: float
    x: float
    y: float
    d_deg: float
    mu_deg: float
    l1_earth_radii: float
    l2_earth_radii: float
    tan_f1: float
    tan_f2: float
    subsolar_lat: float
    subsolar_lon: float
    sublunar_lat: float
    sublunar_lon: float


@dataclass(frozen=True, slots=True)
class SolarShadowBand:
    """Vessel: Geometric definition of a shadow band on the Earth's surface."""
    south_curve: tuple[tuple[float, float], ...]
    north_curve: tuple[tuple[float, float], ...]
    polygon: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class SolarContourLevel:
    """Vessel: Geometric definition of a magnitude or duration contour."""
    kind: str
    threshold: float
    south_curve: tuple[tuple[float, float], ...]
    north_curve: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class SolarCartographyResult:
    """Vessel: Comprehensive result of a solar eclipse cartography computation."""
    event_jd_ut: float
    backend: ArrayBackendInfo
    window_start_jd_ut: float
    window_end_jd_ut: float
    sample_jds_ut: tuple[float, ...]
    besselian_samples: tuple[SolarBesselianSample, ...]
    partial_band: SolarShadowBand
    central_band: SolarShadowBand
    sunrise_band: SolarShadowBand
    sunset_band: SolarShadowBand
    magnitude_contours: tuple[SolarContourLevel, ...]
    duration_contours: tuple[SolarContourLevel, ...]


def _wrap_longitude_deg(value: float) -> float:
    wrapped = ((value + 180.0) % 360.0) - 180.0
    if wrapped == -180.0:
        return 180.0
    return wrapped


def _unwrap_longitudes(values: list[float]) -> list[float]:
    if not values:
        return []
    unwrapped = [float(values[0])]
    for value in values[1:]:
        candidate = float(value)
        previous = unwrapped[-1]
        while candidate - previous > 180.0:
            candidate -= 360.0
        while candidate - previous < -180.0:
            candidate += 360.0
        unwrapped.append(candidate)
    return unwrapped


def _sample_interval(start_jd: float, end_jd: float, count: int) -> tuple[float, ...]:
    if count <= 1 or end_jd <= start_jd:
        return (start_jd,)
    step = (end_jd - start_jd) / (count - 1)
    return tuple(start_jd + (step * index) for index in range(count))


def _offset_point(lat_deg: float, lon_deg: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    angular_distance = distance_km / EARTH_RADIUS_KM
    lat1 = math.radians(lat_deg)
    lon1 = math.radians(lon_deg)
    bearing = math.radians(bearing_deg)

    sin_lat2 = (
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lat2 = math.asin(max(-1.0, min(1.0, sin_lat2)))
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), _wrap_longitude_deg(math.degrees(lon2))


def _bearing_deg(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    lat1 = math.radians(point_a[0])
    lat2 = math.radians(point_b[0])
    dlon = math.radians(point_b[1] - point_a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(y, x)) % 360.0


def _select_backend(preference: str) -> tuple[object, ArrayBackendInfo]:
    mode = preference.strip().lower()
    if mode not in {"auto", "cpu", "gpu"}:
        raise ValueError(f"Unsupported solar cartography backend: {preference!r}")
    if mode in {"auto", "gpu"} and _cp is not None:
        try:  # pragma: no branch
            if int(_cp.cuda.runtime.getDeviceCount()) > 0:
                return _cp, ArrayBackendInfo(name="cupy", is_gpu=True)
        except Exception:
            if mode == "gpu":
                raise RuntimeError("GPU backend requested but no CUDA device is available.")
    if mode == "gpu":
        raise RuntimeError("GPU backend requested but CuPy is not installed.")
    return _np, ArrayBackendInfo(name="numpy", is_gpu=False)


def _to_numpy(xp, values):
    if xp is _np:
        return values
    return _cp.asnumpy(values)


def _topocentric_correction_batch_backend(xp, xyz_geo, lats_deg, lons_deg, gast_deg: float, elevation_m: float = 0.0):
    if xp is _np:
        return topocentric_correction_batch_np(xyz_geo, lats_deg, lons_deg, gast_deg, elevation_m=elevation_m)

    xyz = xp.asarray(xyz_geo, dtype=xp.float64)
    lats = xp.clip(xp.asarray(lats_deg, dtype=xp.float64), -90.0, 90.0)
    lons = xp.asarray(lons_deg, dtype=xp.float64)
    lat_r = xp.radians(lats)
    last_r = xp.radians(gast_deg + lons)

    f = 1.0 / 298.257223563
    a = EARTH_RADIUS_KM
    h = elevation_m / 1000.0
    cos_lat = xp.cos(lat_r)
    sin_lat = xp.sin(lat_r)
    C = 1.0 / xp.sqrt(cos_lat ** 2 + (1.0 - f) ** 2 * sin_lat ** 2)
    S = (1.0 - f) ** 2 * C

    obs_x = (a * C + h) * cos_lat * xp.cos(last_r)
    obs_y = (a * C + h) * cos_lat * xp.sin(last_r)
    obs_z = (a * S + h) * sin_lat
    obs = xp.stack([obs_x, obs_y, obs_z], axis=1)
    return xyz[xp.newaxis, :] - obs


def _topocentric_solar_observer_quantities_batch_backend(
    calc: EclipseCalculator,
    jd_ut: float,
    lats_deg,
    lons_deg,
    xp,
    *,
    mask_below_horizon: bool = True,
):
    sun_cart = planet_at(Body.SUN, jd_ut, reader=calc._reader, frame="cartesian")
    moon_cart = planet_at(Body.MOON, jd_ut, reader=calc._reader, frame="cartesian")

    sun_xyz = xp.asarray([sun_cart.x, sun_cart.y, sun_cart.z], dtype=xp.float64)
    moon_xyz = xp.asarray([moon_cart.x, moon_cart.y, moon_cart.z], dtype=xp.float64)
    lats = xp.asarray(lats_deg, dtype=xp.float64)
    lons = xp.asarray(lons_deg, dtype=xp.float64)

    gast_deg = local_sidereal_time(jd_ut, 0.0)
    sun_topo = _topocentric_correction_batch_backend(xp, sun_xyz, lats, lons, gast_deg)
    moon_topo = _topocentric_correction_batch_backend(xp, moon_xyz, lats, lons, gast_deg)

    sun_r = xp.linalg.norm(sun_topo, axis=1)
    moon_r = xp.linalg.norm(moon_topo, axis=1)

    sun_dec = xp.arcsin(xp.clip(sun_topo[:, 2] / sun_r, -1.0, 1.0))
    sun_ra = xp.arctan2(sun_topo[:, 1], sun_topo[:, 0])
    moon_dec = xp.arcsin(xp.clip(moon_topo[:, 2] / moon_r, -1.0, 1.0))
    moon_ra = xp.arctan2(moon_topo[:, 1], moon_topo[:, 0])

    sun_radius = xp.degrees(xp.arcsin(xp.clip(SUN_RADIUS_KM / sun_r, -1.0, 1.0)))
    moon_radius = xp.degrees(xp.arcsin(xp.clip(MOON_RADIUS_KM / moon_r, -1.0, 1.0)))

    lats_r = xp.radians(lats)
    last_r = xp.radians(gast_deg + lons)
    ha_sun = last_r - sun_ra
    sin_alt = xp.sin(lats_r) * xp.sin(sun_dec) + xp.cos(lats_r) * xp.cos(sun_dec) * xp.cos(ha_sun)
    sun_above = sin_alt > -0.01003
    sun_altitude_deg = xp.degrees(xp.arcsin(xp.clip(sin_alt, -1.0, 1.0)))
    hour_angle_deg = ((xp.degrees(ha_sun) + 180.0) % 360.0) - 180.0

    cos_sep = (
        xp.sin(sun_dec) * xp.sin(moon_dec)
        + xp.cos(sun_dec) * xp.cos(moon_dec) * xp.cos(sun_ra - moon_ra)
    )
    separations = xp.degrees(xp.arccos(xp.clip(cos_sep, -1.0, 1.0)))
    overlap_margin = (sun_radius + moon_radius) - separations
    central_margin = xp.abs(moon_radius - sun_radius) - separations
    magnitude = (sun_radius + moon_radius - separations) / xp.maximum(2.0 * sun_radius, 1e-9)
    magnitude = xp.maximum(magnitude, 0.0)
    if mask_below_horizon:
        inf = xp.asarray(xp.inf, dtype=xp.float64)
        overlap_margin = xp.where(sun_above, overlap_margin, -inf)
        central_margin = xp.where(sun_above, central_margin, -inf)
        magnitude = xp.where(sun_above, magnitude, 0.0)
    return overlap_margin, central_margin, magnitude, sun_altitude_deg, hour_angle_deg


def _topocentric_solar_geometry_batch_backend(calc: EclipseCalculator, jd_ut: float, lats_deg, lons_deg, xp):
    overlap_margin, central_margin, magnitude, _, _ = _topocentric_solar_observer_quantities_batch_backend(
        calc,
        jd_ut,
        lats_deg,
        lons_deg,
        xp,
    )
    return overlap_margin, central_margin, magnitude


def _extract_latitude_band_curves(lat_values: _np.ndarray, lon_values: _np.ndarray, field: _np.ndarray) -> SolarShadowBand:
    south: list[tuple[float, float]] = []
    north: list[tuple[float, float]] = []

    for lon_index, lon in enumerate(lon_values):
        column = field[:, lon_index]
        intervals: list[tuple[float, float]] = []
        active_start: float | None = None

        for lat_index in range(len(lat_values) - 1):
            lat_a = float(lat_values[lat_index])
            lat_b = float(lat_values[lat_index + 1])
            value_a = float(column[lat_index])
            value_b = float(column[lat_index + 1])

            if value_a >= 0.0 and active_start is None:
                active_start = lat_a
            if value_a < 0.0 <= value_b:
                blend = 0.0 if value_b == value_a else (0.0 - value_a) / (value_b - value_a)
                crossing = lat_a + ((lat_b - lat_a) * blend)
                if active_start is None:
                    active_start = crossing
            elif value_a >= 0.0 > value_b:
                blend = 0.0 if value_b == value_a else (0.0 - value_a) / (value_b - value_a)
                crossing = lat_a + ((lat_b - lat_a) * blend)
                intervals.append((active_start if active_start is not None else lat_a, crossing))
                active_start = None

        if active_start is not None:
            intervals.append((active_start, float(lat_values[-1])))

        if not intervals:
            continue

        start_lat, end_lat = max(intervals, key=lambda interval: interval[1] - interval[0])
        south.append((start_lat, _wrap_longitude_deg(float(lon))))
        north.append((end_lat, _wrap_longitude_deg(float(lon))))

    polygon = tuple(north + list(reversed(south))) if len(south) >= 2 and len(north) >= 2 else tuple()
    return SolarShadowBand(
        south_curve=tuple(south),
        north_curve=tuple(north),
        polygon=polygon,
    )


def _extract_threshold_curves(
    lat_values: _np.ndarray,
    lon_values: _np.ndarray,
    field: _np.ndarray,
    threshold: float,
) -> tuple[tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]:
    shifted = field - threshold
    band = _extract_latitude_band_curves(lat_values, lon_values, shifted)
    return band.south_curve, band.north_curve


def _build_contours(
    kind: str,
    lat_values: _np.ndarray,
    lon_values: _np.ndarray,
    field: _np.ndarray,
    thresholds: tuple[float, ...],
) -> tuple[SolarContourLevel, ...]:
    contours: list[SolarContourLevel] = []
    finite_field = field[_np.isfinite(field)]
    if finite_field.size == 0:
        return tuple()
    field_max = float(finite_field.max())
    for threshold in thresholds:
        if threshold > field_max:
            continue
        south_curve, north_curve = _extract_threshold_curves(lat_values, lon_values, field, threshold)
        if len(south_curve) < 2 or len(north_curve) < 2:
            continue
        contours.append(
            SolarContourLevel(
                kind=kind,
                threshold=float(threshold),
                south_curve=south_curve,
                north_curve=north_curve,
            )
        )
    return tuple(contours)


def _build_zero_band_from_field(
    lat_values: _np.ndarray,
    lon_values: _np.ndarray,
    field: _np.ndarray,
) -> SolarShadowBand:
    south_curve, north_curve = _extract_threshold_curves(lat_values, lon_values, field, 0.0)
    if len(south_curve) < 2 or len(north_curve) < 2:
        return SolarShadowBand((), (), ())
    return SolarShadowBand(
        south_curve=south_curve,
        north_curve=north_curve,
        polygon=tuple(),
    )


def _duration_from_margin_series(sample_jds: tuple[float, ...], margin_series: _np.ndarray) -> _np.ndarray:
    if len(sample_jds) < 2:
        return _np.zeros(margin_series.shape[1:], dtype=float)

    duration = _np.zeros(margin_series.shape[1:], dtype=float)
    for index in range(len(sample_jds) - 1):
        margin_a = margin_series[index]
        margin_b = margin_series[index + 1]
        dt_seconds = (sample_jds[index + 1] - sample_jds[index]) * 86400.0

        finite_pair = _np.isfinite(margin_a) & _np.isfinite(margin_b)
        both_positive = finite_pair & (margin_a >= 0.0) & (margin_b >= 0.0)
        exit_mask = finite_pair & (margin_a >= 0.0) & (margin_b < 0.0)
        entry_mask = finite_pair & (margin_a < 0.0) & (margin_b >= 0.0)

        duration = duration + (both_positive * dt_seconds)

        exit_fraction = _np.zeros(margin_a.shape, dtype=float)
        entry_crossing = _np.zeros(margin_a.shape, dtype=float)

        if _np.any(exit_mask):
            exit_denominator = _np.maximum(margin_a[exit_mask] - margin_b[exit_mask], 1e-9)
            exit_fraction[exit_mask] = margin_a[exit_mask] / exit_denominator
        if _np.any(entry_mask):
            entry_denominator = _np.maximum(margin_b[entry_mask] - margin_a[entry_mask], 1e-9)
            entry_crossing[entry_mask] = (-margin_a[entry_mask]) / entry_denominator

        duration = duration + (exit_mask * dt_seconds * exit_fraction)
        duration = duration + (entry_mask * dt_seconds * (1.0 - entry_crossing))
    return duration


def _quadratic_peak_refine(sample_jds: tuple[float, ...], value_series: _np.ndarray) -> tuple[_np.ndarray, _np.ndarray]:
    peak_index = _np.argmax(value_series, axis=0)
    peak_value = _np.take_along_axis(value_series, peak_index[_np.newaxis, ...], axis=0)[0]
    if len(sample_jds) < 3:
        return peak_index.astype(float), peak_value

    prev_index = _np.clip(peak_index - 1, 0, len(sample_jds) - 1)
    next_index = _np.clip(peak_index + 1, 0, len(sample_jds) - 1)
    prev_value = _np.take_along_axis(value_series, prev_index[_np.newaxis, ...], axis=0)[0]
    next_value = _np.take_along_axis(value_series, next_index[_np.newaxis, ...], axis=0)[0]

    denominator = prev_value - (2.0 * peak_value) + next_value
    interior_mask = (peak_index > 0) & (peak_index < len(sample_jds) - 1) & _np.isfinite(denominator) & (_np.abs(denominator) > 1e-12)
    delta = _np.zeros(peak_index.shape, dtype=float)
    delta[interior_mask] = 0.5 * (prev_value[interior_mask] - next_value[interior_mask]) / denominator[interior_mask]
    delta = _np.clip(delta, -1.0, 1.0)
    return peak_index.astype(float) + delta, peak_value


def _evaluate_quadratic_series(series: _np.ndarray, peak_position: _np.ndarray) -> _np.ndarray:
    peak_index = _np.rint(peak_position).astype(int)
    peak_index = _np.clip(peak_index, 0, series.shape[0] - 1)
    peak_value = _np.take_along_axis(series, peak_index[_np.newaxis, ...], axis=0)[0]
    if series.shape[0] < 3:
        return peak_value

    prev_index = _np.clip(peak_index - 1, 0, series.shape[0] - 1)
    next_index = _np.clip(peak_index + 1, 0, series.shape[0] - 1)
    prev_value = _np.take_along_axis(series, prev_index[_np.newaxis, ...], axis=0)[0]
    next_value = _np.take_along_axis(series, next_index[_np.newaxis, ...], axis=0)[0]
    delta = peak_position - peak_index.astype(float)
    interior_mask = (peak_index > 0) & (peak_index < series.shape[0] - 1)

    refined = peak_value.copy()
    refined[interior_mask] = (
        peak_value[interior_mask]
        + (0.5 * delta[interior_mask] * (next_value[interior_mask] - prev_value[interior_mask]))
        + (0.5 * delta[interior_mask] * delta[interior_mask] * (prev_value[interior_mask] - (2.0 * peak_value[interior_mask]) + next_value[interior_mask]))
    )
    return refined


def _solve_cross_track_limit(
    calc: EclipseCalculator,
    jd_ut: float,
    center_lat: float,
    center_lon: float,
    normal_bearing_deg: float,
    *,
    margin_kind: str,
    max_distance_km: float,
) -> tuple[float, float] | None:
    def margin_at(distance_km: float) -> float:
        lat, lon = _offset_point(center_lat, center_lon, normal_bearing_deg, distance_km)
        _, overlap_margin, central_margin = _topocentric_solar_geometry(calc, jd_ut, lat, lon)
        return overlap_margin if margin_kind == "partial" else central_margin

    margin_center = margin_at(0.0)
    if not math.isfinite(margin_center) or margin_center < 0.0:
        return None

    left = 0.0
    right = min(max_distance_km, 40.0)
    margin_right = margin_at(right)
    while math.isfinite(margin_right) and margin_right >= 0.0 and right < max_distance_km:
        left = right
        right = min(max_distance_km, right * 1.7)
        margin_right = margin_at(right)

    if not math.isfinite(margin_right):
        probe = right
        for _ in range(6):
            probe = (left + probe) / 2.0
            margin_probe = margin_at(probe)
            if math.isfinite(margin_probe):
                right = probe
                margin_right = margin_probe
                break
        else:
            return None

    if margin_right > 0.0:
        return None

    root_distance = _bisection_root(margin_at, left, right, iterations=40)
    return _offset_point(center_lat, center_lon, normal_bearing_deg, root_distance)


def _solve_cross_track_magnitude_threshold(
    calc: EclipseCalculator,
    jd_ut: float,
    center_lat: float,
    center_lon: float,
    normal_bearing_deg: float,
    *,
    threshold: float,
    max_distance_km: float,
) -> tuple[float, float] | None:
    def magnitude_at(distance_km: float) -> float:
        lat, lon = _offset_point(center_lat, center_lon, normal_bearing_deg, distance_km)
        _, _, magnitude = _topocentric_solar_geometry_batch_backend(
            calc,
            jd_ut,
            _np.array([lat], dtype=float),
            _np.array([lon], dtype=float),
            _np,
        )
        return float(magnitude[0])

    magnitude_center = magnitude_at(0.0)
    if not math.isfinite(magnitude_center) or magnitude_center < threshold:
        return None

    left = 0.0
    right = min(max_distance_km, 40.0)
    magnitude_right = magnitude_at(right)
    while math.isfinite(magnitude_right) and magnitude_right >= threshold and right < max_distance_km:
        left = right
        right = min(max_distance_km, right * 1.7)
        magnitude_right = magnitude_at(right)

    if not math.isfinite(magnitude_right):
        probe = right
        for _ in range(6):
            probe = (left + probe) / 2.0
            magnitude_probe = magnitude_at(probe)
            if math.isfinite(magnitude_probe):
                right = probe
                magnitude_right = magnitude_probe
                break
        else:
            return None

    if magnitude_right > threshold:
        return None

    root_distance = _bisection_root(lambda distance_km: magnitude_at(distance_km) - threshold, left, right, iterations=40)
    return _offset_point(center_lat, center_lon, normal_bearing_deg, root_distance)


def _solve_limit_band_from_centerline(
    calc: EclipseCalculator,
    sample_jds: tuple[float, ...],
    centerline: tuple[tuple[float, float], ...],
    *,
    margin_kind: str,
    max_distance_km: float,
) -> SolarShadowBand:
    if len(centerline) < 2 or len(sample_jds) != len(centerline):
        return SolarShadowBand((), (), ())

    south_curve: list[tuple[float, float]] = []
    north_curve: list[tuple[float, float]] = []

    for index, (jd_ut, point) in enumerate(zip(sample_jds, centerline, strict=False)):
        if index == 0:
            forward = centerline[index + 1]
            backward = point
        elif index == len(centerline) - 1:
            forward = point
            backward = centerline[index - 1]
        else:
            forward = centerline[index + 1]
            backward = centerline[index - 1]

        track_bearing = _bearing_deg(backward, forward)
        left_normal = (track_bearing - 90.0) % 360.0
        right_normal = (track_bearing + 90.0) % 360.0

        north_point = _solve_cross_track_limit(
            calc,
            jd_ut,
            point[0],
            point[1],
            left_normal,
            margin_kind=margin_kind,
            max_distance_km=max_distance_km,
        )
        south_point = _solve_cross_track_limit(
            calc,
            jd_ut,
            point[0],
            point[1],
            right_normal,
            margin_kind=margin_kind,
            max_distance_km=max_distance_km,
        )
        if north_point is not None and south_point is not None:
            north_curve.append(north_point)
            south_curve.append(south_point)

    polygon = tuple(north_curve + list(reversed(south_curve))) if len(north_curve) >= 2 and len(south_curve) >= 2 else tuple()
    return SolarShadowBand(
        south_curve=tuple(south_curve),
        north_curve=tuple(north_curve),
        polygon=polygon,
    )


def _solve_magnitude_contours_from_centerline(
    calc: EclipseCalculator,
    sample_jds: tuple[float, ...],
    centerline: tuple[tuple[float, float], ...],
    thresholds: tuple[float, ...],
    *,
    max_distance_km: float,
) -> tuple[SolarContourLevel, ...]:
    if len(centerline) < 2 or len(sample_jds) != len(centerline):
        return tuple()

    contours: list[SolarContourLevel] = []
    for threshold in thresholds:
        south_curve: list[tuple[float, float]] = []
        north_curve: list[tuple[float, float]] = []
        for index, (jd_ut, point) in enumerate(zip(sample_jds, centerline, strict=False)):
            if index == 0:
                forward = centerline[index + 1]
                backward = point
            elif index == len(centerline) - 1:
                forward = point
                backward = centerline[index - 1]
            else:
                forward = centerline[index + 1]
                backward = centerline[index - 1]

            track_bearing = _bearing_deg(backward, forward)
            left_normal = (track_bearing - 90.0) % 360.0
            right_normal = (track_bearing + 90.0) % 360.0

            north_point = _solve_cross_track_magnitude_threshold(
                calc,
                jd_ut,
                point[0],
                point[1],
                left_normal,
                threshold=threshold,
                max_distance_km=max_distance_km,
            )
            south_point = _solve_cross_track_magnitude_threshold(
                calc,
                jd_ut,
                point[0],
                point[1],
                right_normal,
                threshold=threshold,
                max_distance_km=max_distance_km,
            )
            if north_point is not None and south_point is not None:
                north_curve.append(north_point)
                south_curve.append(south_point)

        if len(north_curve) >= 8 and len(south_curve) >= 8:
            contours.append(
                SolarContourLevel(
                    kind="magnitude",
                    threshold=float(threshold),
                    south_curve=tuple(south_curve),
                    north_curve=tuple(north_curve),
                )
            )
    return tuple(contours)


def _compute_besselian_sample(calc: EclipseCalculator, jd_ut: float) -> SolarBesselianSample:
    sun = planet_at(Body.SUN, jd_ut, reader=calc._reader, frame="cartesian")
    moon = planet_at(Body.MOON, jd_ut, reader=calc._reader, frame="cartesian")

    sun_xyz = _np.array([sun.x, sun.y, sun.z], dtype=float)
    moon_xyz = _np.array([moon.x, moon.y, moon.z], dtype=float)
    axis = moon_xyz - sun_xyz
    axis /= _np.linalg.norm(axis)

    north_pole = _np.array([0.0, 0.0, 1.0], dtype=float)
    east = _np.cross(north_pole, axis)
    east_norm = _np.linalg.norm(east)
    if east_norm < 1e-12:
        east = _np.array([1.0, 0.0, 0.0], dtype=float)
    else:
        east /= east_norm
    north = _np.cross(axis, east)
    north /= _np.linalg.norm(north)

    distance_to_plane = -float(_np.dot(moon_xyz, axis))
    plane_point = moon_xyz + (distance_to_plane * axis)
    x = float(_np.dot(plane_point, east) / EARTH_RADIUS_KM)
    y = float(_np.dot(plane_point, north) / EARTH_RADIUS_KM)

    axis_ra = math.degrees(math.atan2(axis[1], axis[0])) % 360.0
    axis_dec = math.degrees(math.asin(max(-1.0, min(1.0, axis[2]))))
    mu = (local_sidereal_time(jd_ut, 0.0) - axis_ra) % 360.0

    sun_moon_distance = float(_np.linalg.norm(sun_xyz - moon_xyz))
    tan_f1 = (SUN_RADIUS_KM + MOON_RADIUS_KM) / sun_moon_distance
    tan_f2 = (SUN_RADIUS_KM - MOON_RADIUS_KM) / sun_moon_distance
    penumbra_radius = (MOON_RADIUS_KM + (distance_to_plane * tan_f1)) / EARTH_RADIUS_KM
    umbra_radius = (MOON_RADIUS_KM - (distance_to_plane * tan_f2)) / EARTH_RADIUS_KM

    def subpoint(xyz: _np.ndarray) -> tuple[float, float]:
        radius = float(_np.linalg.norm(xyz))
        dec = math.degrees(math.asin(max(-1.0, min(1.0, xyz[2] / radius))))
        ra = math.degrees(math.atan2(xyz[1], xyz[0])) % 360.0
        lon = _wrap_longitude_deg(ra - local_sidereal_time(jd_ut, 0.0))
        return dec, lon

    subsolar_lat, subsolar_lon = subpoint(sun_xyz)
    sublunar_lat, sublunar_lon = subpoint(moon_xyz)
    return SolarBesselianSample(
        jd_ut=float(jd_ut),
        x=x,
        y=y,
        d_deg=axis_dec,
        mu_deg=mu,
        l1_earth_radii=penumbra_radius,
        l2_earth_radii=umbra_radius,
        tan_f1=tan_f1,
        tan_f2=tan_f2,
        subsolar_lat=subsolar_lat,
        subsolar_lon=subsolar_lon,
        sublunar_lat=sublunar_lat,
        sublunar_lon=sublunar_lon,
    )


def solar_eclipse_cartography(
    calc: EclipseCalculator,
    jd_seed: float,
    *,
    kind: str = "any",
    backward: bool = False,
    backend: str = "auto",
    time_samples: int = 17,
) -> SolarCartographyResult:
    xp, backend_info = _select_backend(backend)
    event = calc._search_solar_eclipse(jd_seed, kind=kind, backward=backward)
    path = calc.solar_eclipse_path(event.jd_ut - _SOLAR_PATH_SEED_EPSILON_DAYS)

    track_lats = [float(value) for value in getattr(path, "central_line_lats", ())] or [float(getattr(path, "max_eclipse_lat", 0.0))]
    track_lons = [float(value) for value in getattr(path, "central_line_lons", ())] or [float(getattr(path, "max_eclipse_lon", 0.0))]
    track_lons_unwrapped = _unwrap_longitudes(track_lons)
    mean_lat = sum(track_lats) / len(track_lats)
    km_per_deg_lon = max(8.0, _KM_PER_DEG_LAT * max(0.18, abs(math.cos(math.radians(mean_lat)))))
    umbral_width_km = float(getattr(path, "umbral_width_km", 0.0))

    partial_padding_km = max(4200.0, umbral_width_km * 6.0 + 1400.0)
    lat_padding = partial_padding_km / _KM_PER_DEG_LAT
    lon_padding = partial_padding_km / km_per_deg_lon
    lat_min = max(-89.0, min(track_lats) - lat_padding)
    lat_max = min(89.0, max(track_lats) + lat_padding)
    lon_min = min(track_lons_unwrapped) - lon_padding
    lon_max = max(track_lons_unwrapped) + lon_padding

    lat_span = max(2.0, lat_max - lat_min)
    lon_span = max(2.0, lon_max - lon_min)
    lat_count = max(81, min(161, int(round(lat_span / 0.6)) + 1))
    lon_count = max(121, min(281, int(round(lon_span / 0.6)) + 1))
    lat_values = _np.linspace(lat_min, lat_max, lat_count)
    lon_values = _np.linspace(lon_min, lon_max, lon_count)
    lat_grid, lon_grid = _np.meshgrid(lat_values, lon_values, indexing="ij")

    central_window_half_days = max((float(getattr(path, "duration_at_max_s", 0.0)) / 86400.0) * 1.8, 4.5 / 24.0)
    partial_window_half_days = max(central_window_half_days, 5.0 / 24.0)
    sample_jds = _sample_interval(event.jd_ut - partial_window_half_days, event.jd_ut + partial_window_half_days, time_samples)

    axis_track_samples = _sample_interval(sample_jds[0], sample_jds[-1], max(31, time_samples * 4))
    axis_centerline = tuple(
        _solve_solar_greatest_location(calc, sample_jd)[:2]
        for sample_jd in axis_track_samples
    )

    partial_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    central_max = xp.full(lat_grid.shape, -xp.inf, dtype=xp.float64)
    magnitude_max = xp.zeros(lat_grid.shape, dtype=xp.float64)
    raw_overlap_series: list[_np.ndarray] = []
    altitude_series: list[_np.ndarray] = []
    hour_angle_series: list[_np.ndarray] = []

    for jd_ut in sample_jds:
        overlap_margin, central_margin, magnitude = _topocentric_solar_geometry_batch_backend(
            calc,
            jd_ut,
            lat_grid.ravel(),
            lon_grid.ravel(),
            xp,
        )
        raw_overlap_margin, _, _, sun_altitude_deg, hour_angle_deg = _topocentric_solar_observer_quantities_batch_backend(
            calc,
            jd_ut,
            lat_grid.ravel(),
            lon_grid.ravel(),
            xp,
            mask_below_horizon=False,
        )
        raw_overlap_grid = raw_overlap_margin.reshape(lat_grid.shape)
        raw_overlap_series.append(_to_numpy(xp, raw_overlap_grid))
        altitude_series.append(_to_numpy(xp, sun_altitude_deg.reshape(lat_grid.shape)))
        hour_angle_series.append(_to_numpy(xp, hour_angle_deg.reshape(lat_grid.shape)))
        partial_max = xp.maximum(partial_max, overlap_margin.reshape(lat_grid.shape))
        central_max = xp.maximum(central_max, central_margin.reshape(lat_grid.shape))
        magnitude_max = xp.maximum(magnitude_max, magnitude.reshape(lat_grid.shape))

    partial_field = _to_numpy(xp, partial_max)
    magnitude_field = _to_numpy(xp, magnitude_max)
    raw_overlap_field_series = _np.stack(raw_overlap_series, axis=0)
    altitude_field_series = _np.stack(altitude_series, axis=0)
    hour_angle_field_series = _np.stack(hour_angle_series, axis=0)
    peak_position, peak_overlap_field = _quadratic_peak_refine(sample_jds, raw_overlap_field_series)
    peak_altitude_field = _evaluate_quadratic_series(altitude_field_series, peak_position)
    peak_hour_angle_field = _evaluate_quadratic_series(hour_angle_field_series, peak_position)
    partial_band = _extract_latitude_band_curves(lat_values, lon_values, partial_field)
    magnitude_contours = _build_contours(
        "magnitude",
        lat_values,
        lon_values,
        magnitude_field,
        (0.2, 0.4, 0.6, 0.8),
    )
    visible_peak_mask = (
        (peak_overlap_field > 0.0)
        & _np.isfinite(peak_altitude_field)
        & _np.isfinite(peak_hour_angle_field)
    )
    sunrise_field = _np.where(visible_peak_mask & (peak_hour_angle_field <= 0.0), peak_altitude_field, _np.nan)
    sunset_field = _np.where(visible_peak_mask & (peak_hour_angle_field >= 0.0), peak_altitude_field, _np.nan)
    sunrise_band = _build_zero_band_from_field(lat_values, lon_values, sunrise_field)
    sunset_band = _build_zero_band_from_field(lat_values, lon_values, sunset_field)
    solved_partial_band = _solve_limit_band_from_centerline(
        calc,
        axis_track_samples,
        axis_centerline,
        margin_kind="partial",
        max_distance_km=partial_padding_km,
    )
    solved_axis_magnitude_contours = _solve_magnitude_contours_from_centerline(
        calc,
        axis_track_samples,
        axis_centerline,
        (0.2, 0.4),
        max_distance_km=max(2400.0, partial_padding_km * 0.72),
    )
    if len(solved_partial_band.north_curve) >= 8 and len(solved_partial_band.south_curve) >= 8:
        partial_band = solved_partial_band
    if solved_axis_magnitude_contours:
        solved_by_threshold = {float(level.threshold): level for level in solved_axis_magnitude_contours}
        merged_magnitude_contours: list[SolarContourLevel] = []
        for level in magnitude_contours:
            merged_magnitude_contours.append(solved_by_threshold.pop(float(level.threshold), level))
        merged_magnitude_contours.extend(sorted(solved_by_threshold.values(), key=lambda level: level.threshold))
        magnitude_contours = tuple(merged_magnitude_contours)

    if umbral_width_km > 0.0:
        central_jd_start, central_jd_end = _solve_solar_central_interval(calc, event.jd_ut)
        central_track_samples = _sample_interval(central_jd_start, central_jd_end, max(25, time_samples * 3))
        centerline = tuple(
            _solve_solar_greatest_location(calc, sample_jd)[:2]
            for sample_jd in central_track_samples
        )
        solved_magnitude_contours = _solve_magnitude_contours_from_centerline(
            calc,
            central_track_samples,
            centerline,
            (0.6, 0.8),
            max_distance_km=max(1800.0, umbral_width_km * 6.5),
        )
        central_padding_km = max(1200.0, umbral_width_km * 2.5 + 500.0)
        central_lat_padding = central_padding_km / _KM_PER_DEG_LAT
        central_lon_padding = central_padding_km / km_per_deg_lon
        central_lat_min = max(-89.0, min(track_lats) - central_lat_padding)
        central_lat_max = min(89.0, max(track_lats) + central_lat_padding)
        central_lon_min = min(track_lons_unwrapped) - central_lon_padding
        central_lon_max = max(track_lons_unwrapped) + central_lon_padding
        central_lat_span = max(2.0, central_lat_max - central_lat_min)
        central_lon_span = max(2.0, central_lon_max - central_lon_min)
        central_lat_count = max(101, min(241, int(round(central_lat_span / 0.22)) + 1))
        central_lon_count = max(141, min(361, int(round(central_lon_span / 0.22)) + 1))
        central_lat_values = _np.linspace(central_lat_min, central_lat_max, central_lat_count)
        central_lon_values = _np.linspace(central_lon_min, central_lon_max, central_lon_count)
        central_lat_grid, central_lon_grid = _np.meshgrid(central_lat_values, central_lon_values, indexing="ij")
        central_band_max = xp.full(central_lat_grid.shape, -xp.inf, dtype=xp.float64)
        central_margin_series: list[_np.ndarray] = []
        for jd_ut in sample_jds:
            _, central_margin, _ = _topocentric_solar_geometry_batch_backend(
                calc,
                jd_ut,
                central_lat_grid.ravel(),
                central_lon_grid.ravel(),
                xp,
            )
            central_margin_grid = central_margin.reshape(central_lat_grid.shape)
            central_band_max = xp.maximum(central_band_max, central_margin_grid)
            central_margin_series.append(_to_numpy(xp, central_margin_grid))
        central_field = _to_numpy(xp, central_band_max)
        solved_central_band = _solve_limit_band_from_centerline(
            calc,
            central_track_samples,
            centerline,
            margin_kind="central",
            max_distance_km=max(600.0, umbral_width_km * 1.8),
        )
        central_band = (
            solved_central_band
            if len(solved_central_band.north_curve) >= 8 and len(solved_central_band.south_curve) >= 8
            else _extract_latitude_band_curves(central_lat_values, central_lon_values, central_field)
        )
        duration_field = _duration_from_margin_series(sample_jds, _np.stack(central_margin_series, axis=0))
        duration_contours = _build_contours(
            "duration",
            central_lat_values,
            central_lon_values,
            duration_field,
            (60.0, 120.0, 180.0, 240.0, 300.0),
        )
        if solved_magnitude_contours:
            solved_by_threshold = {float(level.threshold): level for level in solved_magnitude_contours}
            merged_magnitude_contours: list[SolarContourLevel] = []
            for level in magnitude_contours:
                merged_magnitude_contours.append(solved_by_threshold.pop(float(level.threshold), level))
            merged_magnitude_contours.extend(sorted(solved_by_threshold.values(), key=lambda level: level.threshold))
            magnitude_contours = tuple(merged_magnitude_contours)
    else:
        central_band = SolarShadowBand((), (), ())
        duration_contours = tuple()

    besselian_samples = tuple(_compute_besselian_sample(calc, jd_ut) for jd_ut in sample_jds)
    return SolarCartographyResult(
        event_jd_ut=float(event.jd_ut),
        backend=backend_info,
        window_start_jd_ut=float(sample_jds[0]),
        window_end_jd_ut=float(sample_jds[-1]),
        sample_jds_ut=tuple(float(value) for value in sample_jds),
        besselian_samples=besselian_samples,
        partial_band=partial_band,
        central_band=central_band,
        sunrise_band=sunrise_band,
        sunset_band=sunset_band,
        magnitude_contours=magnitude_contours,
        duration_contours=duration_contours,
    )
