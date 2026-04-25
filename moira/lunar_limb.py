"""
Official lunar limb and topography support for profile-aware graze work.

This module binds authoritative external sources rather than inventing a local
profile model:

- NAIF/SPICE lunar orientation kernels
- USGS Astrogeology / LOLA cloud-optimized point-cloud tiles

The current implementation is the first sovereign substrate slice. It solves
the lunar limb point corresponding to a sky-plane position angle using the
official lunar body frame and samples official LOLA topography near that limb
point to derive an apparent-radius correction.

Boundary
--------
Owns:
    - official-kernel cache and loading
    - official LOLA tile lookup, download, cache, and sampling
    - position-angle to selenographic limb-point projection
    - profile correction in angular degrees for occultation work

Delegates:
    - topocentric apparent Moon geometry to moira.planets / occultations
    - occultation event search to moira.occultations

Import-time side effects: none
"""

import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

import laspy
import numpy as np
import requests
import spiceypy as sp

from .constants import MOON_RADIUS_KM

__all__ = [
    "official_lunar_limb_profile_adjustment",
]


_CACHE_LOCK = Lock()
_KERNELS_LOADED = False

_NAIF_KERNELS: dict[str, str] = {
    "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
    "pck00011.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc",
    "moon_pa_de440_200625.bpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de440_200625.bpc",
    "moon_assoc_me.tf": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_assoc_me.tf",
    "moon_de440_250416.tf": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_de440_250416.tf",
    "de440.bsp": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp",
}

_STAC_SEARCH_URL = "https://stac.astrogeology.usgs.gov/api/search"
_LOLA_COLLECTION = "lunar_orbiter_laser_altimeter"
_LOLA_MEAN_RADIUS_M = MOON_RADIUS_KM * 1000.0
_LOLA_TILE_STEP_DEG = 15
_LIMB_TILE_EXTENT = 1
_LIMB_PA_WINDOW_DEG = 10.0
_LIMB_RADIAL_FLOOR_KM = MOON_RADIUS_KM - 1.0
_LIMB_BIN_WIDTH_DEG = 0.1


@dataclass(frozen=True, slots=True)
class _LolaTile:
    lon_deg: np.ndarray
    lat_deg: np.ndarray
    radius_m: np.ndarray


@dataclass(frozen=True, slots=True)
class _ObserverLimbContext:
    subobserver_lon_deg: float
    subobserver_lat_deg: float
    los_j2000: np.ndarray
    observer_dir_moon: np.ndarray
    sky_north_moon: np.ndarray
    sky_east_moon: np.ndarray


def _default_cache_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Moira" / "lunar_limb"
    return Path.home() / ".cache" / "moira" / "lunar_limb"


def _download_file(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                handle.write(chunk)
    tmp.replace(dest)
    return dest


def _ensure_kernels_loaded(cache_root: Path) -> None:
    global _KERNELS_LOADED
    if _KERNELS_LOADED:
        return
    with _CACHE_LOCK:
        if _KERNELS_LOADED:
            return
        kernels_dir = cache_root / "kernels"
        for filename, url in _NAIF_KERNELS.items():
            path = _download_file(url, kernels_dir / filename)
            sp.furnsh(str(path))
        _KERNELS_LOADED = True


def _jd_ut_to_et(jd_ut: float) -> float:
    return sp.str2et(f"JD {jd_ut}")


def _normalize_lon_deg(lon_deg: float) -> float:
    return ((lon_deg + 180.0) % 360.0) - 180.0


def _norm(vec: np.ndarray) -> np.ndarray:
    return vec / np.linalg.norm(vec)


def _project_onto_sky(vec: np.ndarray, los: np.ndarray) -> np.ndarray:
    return vec - np.dot(vec, los) * los


def _earth_observer_position_km(
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
) -> np.ndarray:
    _, radii = sp.bodvrd("EARTH", "RADII", 3)
    equatorial_radius_km = float(radii[0])
    polar_radius_km = float(radii[2])
    flattening = (equatorial_radius_km - polar_radius_km) / equatorial_radius_km
    return np.array(
        sp.georec(
            math.radians(observer_lon),
            math.radians(observer_lat),
            observer_elev_m / 1000.0,
            equatorial_radius_km,
            flattening,
        ),
        dtype=float,
    )


def _observer_limb_context(
    et: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
) -> _ObserverLimbContext:
    observer_pos_iau_earth = _earth_observer_position_km(
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    moon_state_j2000, _ = sp.spkcpo(
        "MOON",
        et,
        "J2000",
        "OBSERVER",
        "LT+S",
        observer_pos_iau_earth,
        "EARTH",
        "IAU_EARTH",
    )
    observer_to_moon_j2000 = np.array(moon_state_j2000[:3], dtype=float)
    los_j2000 = _norm(observer_to_moon_j2000)
    moon_to_observer_j2000 = -observer_to_moon_j2000
    j2000_to_moon = sp.pxform("J2000", "MOON_ME", et)
    moon_to_observer_moon = np.array(sp.mxv(j2000_to_moon, moon_to_observer_j2000), dtype=float)
    moon_to_observer_moon = _norm(moon_to_observer_moon)
    _, lon_rad, lat_rad = sp.reclat(moon_to_observer_moon)
    moon_to_j2000 = sp.pxform("MOON_ME", "J2000", et)
    moon_north_j2000 = np.array(sp.mxv(moon_to_j2000, [0.0, 0.0, 1.0]), dtype=float)
    celestial_north_j2000 = np.array([0.0, 0.0, 1.0], dtype=float)
    sky_north_j2000 = _norm(_project_onto_sky(celestial_north_j2000, los_j2000))
    sky_east_j2000 = _norm(np.cross(los_j2000, sky_north_j2000))
    sky_north_moon = _norm(np.array(sp.mxv(j2000_to_moon, sky_north_j2000), dtype=float))
    sky_east_moon = _norm(np.array(sp.mxv(j2000_to_moon, sky_east_j2000), dtype=float))
    return _ObserverLimbContext(
        subobserver_lon_deg=lon_rad * sp.dpr(),
        subobserver_lat_deg=lat_rad * sp.dpr(),
        los_j2000=los_j2000,
        observer_dir_moon=moon_to_observer_moon,
        sky_north_moon=sky_north_moon,
        sky_east_moon=sky_east_moon,
    )


def _limb_point_lon_lat_deg(
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
) -> tuple[float, float]:
    et = _jd_ut_to_et(jd_ut)
    context = _observer_limb_context(
        et,
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    # The smooth-limb point at a given apparent position angle is the
    # sky-plane unit vector itself, expressed in the lunar body frame. This
    # is the correct spherical baseline before topography perturbs the limb.
    pa_rad = math.radians(position_angle_deg)
    limb_vec_moon = (
        math.cos(pa_rad) * context.sky_north_moon
        + math.sin(pa_rad) * context.sky_east_moon
    )
    limb_vec_moon = _norm(limb_vec_moon)
    _, lon_rad, lat_rad = sp.reclat(limb_vec_moon)
    return _normalize_lon_deg(lon_rad * sp.dpr()), lat_rad * sp.dpr()


@lru_cache(maxsize=128)
def _lola_tile_asset_url(lon_bin: int, lat_bin: int) -> str:
    bbox = [lon_bin - 0.01, lat_bin - 0.01, lon_bin + 0.01, lat_bin + 0.01]
    response = requests.post(
        _STAC_SEARCH_URL,
        json={
            "collections": [_LOLA_COLLECTION],
            "bbox": bbox,
            "limit": 1,
        },
        timeout=30,
    )
    response.raise_for_status()
    features = response.json().get("features", [])
    if not features:
        raise FileNotFoundError(f"No official LOLA tile found for lon={lon_bin}, lat={lat_bin}")
    return str(features[0]["assets"]["data"]["href"])


@lru_cache(maxsize=16)
def _load_lola_tile(url: str, cache_root_str: str) -> _LolaTile:
    cache_root = Path(cache_root_str)
    tile_path = _download_file(url, cache_root / "lola_tiles" / Path(url).name)
    las = laspy.read(tile_path)
    x = np.asarray(las.x, dtype=float)
    y = np.asarray(las.y, dtype=float)
    z = np.asarray(las.z, dtype=float)
    radius_m = np.sqrt(x * x + y * y + z * z)
    lon_deg = np.degrees(np.arctan2(y, x))
    lat_deg = np.degrees(np.arcsin(z / radius_m))
    return _LolaTile(
        lon_deg=lon_deg,
        lat_deg=lat_deg,
        radius_m=radius_m,
    )


def _lola_neighbor_tile_urls(lon_deg: float, lat_deg: float) -> tuple[str, ...]:
    lon_bin = int(math.floor(lon_deg / _LOLA_TILE_STEP_DEG) * _LOLA_TILE_STEP_DEG)
    lat_bin = int(math.floor(lat_deg / _LOLA_TILE_STEP_DEG) * _LOLA_TILE_STEP_DEG)
    seen: set[str] = set()
    urls: list[str] = []
    for lon_offset in range(
        -_LIMB_TILE_EXTENT * _LOLA_TILE_STEP_DEG,
        (_LIMB_TILE_EXTENT + 1) * _LOLA_TILE_STEP_DEG,
        _LOLA_TILE_STEP_DEG,
    ):
        for lat_offset in range(
            -_LIMB_TILE_EXTENT * _LOLA_TILE_STEP_DEG,
            (_LIMB_TILE_EXTENT + 1) * _LOLA_TILE_STEP_DEG,
            _LOLA_TILE_STEP_DEG,
        ):
            try:
                url = _lola_tile_asset_url(lon_bin + lon_offset, lat_bin + lat_offset)
            except FileNotFoundError:
                continue
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return tuple(urls)


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    unique_points = sorted(set(points))
    if len(unique_points) <= 1:
        return unique_points

    lower: list[tuple[float, float]] = []
    for point in unique_points:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)

    upper: list[tuple[float, float]] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _ray_intersection_radius_km(
    hull: list[tuple[float, float]],
    position_angle_deg: float,
) -> float:
    if not hull:
        return MOON_RADIUS_KM

    pa_rad = math.radians(position_angle_deg)
    ray_x = math.sin(pa_rad)
    ray_y = math.cos(pa_rad)
    best_t: float | None = None
    closed_hull = hull + [hull[0]]
    for start, end in zip(closed_hull[:-1], closed_hull[1:]):
        edge_x = end[0] - start[0]
        edge_y = end[1] - start[1]
        det = ray_x * (-edge_y) - ray_y * (-edge_x)
        if abs(det) < 1e-12:
            continue

        rhs_x = start[0]
        rhs_y = start[1]
        t = (rhs_x * (-edge_y) - rhs_y * (-edge_x)) / det
        u = (ray_x * rhs_y - ray_y * rhs_x) / det
        if t >= 0.0 and 0.0 <= u <= 1.0:
            if best_t is None or t > best_t:
                best_t = t

    return best_t if best_t is not None else MOON_RADIUS_KM


def _sample_lola_limb_elevation_m(
    lon_deg: float,
    lat_deg: float,
    observer_context: _ObserverLimbContext,
    position_angle_deg: float,
    cache_root: Path,
) -> float:
    best_by_bin: dict[int, tuple[float, float, float]] = {}
    observer_dir = observer_context.observer_dir_moon
    sky_east = observer_context.sky_east_moon
    sky_north = observer_context.sky_north_moon
    for tile_url in _lola_neighbor_tile_urls(lon_deg, lat_deg):
        tile = _load_lola_tile(tile_url, str(cache_root))
        lon_rad = np.radians(tile.lon_deg)
        lat_rad = np.radians(tile.lat_deg)
        radius_km = tile.radius_m / 1000.0
        cos_lat = np.cos(lat_rad)
        x = radius_km * cos_lat * np.cos(lon_rad)
        y = radius_km * cos_lat * np.sin(lon_rad)
        z = radius_km * np.sin(lat_rad)

        visible = (x * observer_dir[0] + y * observer_dir[1] + z * observer_dir[2]) > 0.0
        if not np.any(visible):
            continue

        proj_east_km = x[visible] * sky_east[0] + y[visible] * sky_east[1] + z[visible] * sky_east[2]
        proj_north_km = x[visible] * sky_north[0] + y[visible] * sky_north[1] + z[visible] * sky_north[2]
        proj_radius_km = np.sqrt(proj_east_km * proj_east_km + proj_north_km * proj_north_km)
        point_pa_deg = (np.degrees(np.arctan2(proj_east_km, proj_north_km)) + 360.0) % 360.0
        pa_error_deg = np.abs(((point_pa_deg - position_angle_deg + 180.0) % 360.0) - 180.0)

        candidate_mask = (pa_error_deg <= _LIMB_PA_WINDOW_DEG) & (proj_radius_km >= _LIMB_RADIAL_FLOOR_KM)
        if not np.any(candidate_mask):
            continue

        candidate_east = proj_east_km[candidate_mask]
        candidate_north = proj_north_km[candidate_mask]
        candidate_radius = proj_radius_km[candidate_mask]
        candidate_pa = point_pa_deg[candidate_mask]
        rel_pa = ((candidate_pa - position_angle_deg + 180.0) % 360.0) - 180.0
        bin_idx = np.rint(rel_pa / _LIMB_BIN_WIDTH_DEG).astype(int)
        order = np.lexsort((candidate_radius, bin_idx))
        sorted_bins = bin_idx[order]
        keep_mask = np.empty(sorted_bins.shape, dtype=bool)
        keep_mask[:-1] = sorted_bins[1:] != sorted_bins[:-1]
        keep_mask[-1] = True
        best_order = order[keep_mask]

        for idx, east, north, radius in zip(
            bin_idx[best_order],
            candidate_east[best_order],
            candidate_north[best_order],
            candidate_radius[best_order],
        ):
            current = best_by_bin.get(int(idx))
            if current is None or radius > current[2]:
                best_by_bin[int(idx)] = (float(east), float(north), float(radius))

    if not best_by_bin:
        return 0.0

    hull = _convex_hull([(east, north) for east, north, _ in best_by_bin.values()])
    silhouette_radius_km = _ray_intersection_radius_km(hull, position_angle_deg)
    return silhouette_radius_km * 1000.0 - _LOLA_MEAN_RADIUS_M


def official_lunar_limb_profile_adjustment(
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
    moon_distance_km: float,
) -> float:
    """
    Return an official-source lunar-limb correction in angular degrees.

    The current implementation uses:
    - NAIF lunar orientation kernels for body-frame geometry
    - official USGS/LOLA COPC tiles for limb topography

    """
    cache_root = _default_cache_root()
    _ensure_kernels_loaded(cache_root)

    observer_context = _observer_limb_context(
        _jd_ut_to_et(jd_ut),
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    limb_lon_deg, limb_lat_deg = _limb_point_lon_lat_deg(
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        position_angle_deg,
    )
    elevation_m = _sample_lola_limb_elevation_m(
        limb_lon_deg,
        limb_lat_deg,
        observer_context,
        position_angle_deg,
        cache_root,
    )

    base_radius_deg = math.degrees(math.asin(max(-1.0, min(1.0, MOON_RADIUS_KM / moon_distance_km))))
    adjusted_radius_deg = math.degrees(
        math.asin(
            max(
                -1.0,
                min(1.0, (MOON_RADIUS_KM + elevation_m / 1000.0) / moon_distance_km),
            )
        )
    )
    return adjusted_radius_deg - base_radius_deg
