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
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

_requests_exc = None
try:
    import requests
    _HAS_REQUESTS = True
except ImportError as exc:
    requests = None
    _HAS_REQUESTS = False
    _requests_exc = exc
_laspy_exc = None
try:
    import laspy
    from laspy.copc import Bounds, CopcReader
    _HAS_LASPY = True
except ImportError as exc:
    laspy = None
    Bounds = None
    CopcReader = None
    _HAS_LASPY = False
    _laspy_exc = exc

_spiceypy_exc = None
try:
    import spiceypy as sp
    _HAS_SPICEYPY = True
except ImportError as exc:
    sp = None
    _HAS_SPICEYPY = False
    _spiceypy_exc = exc

from .constants import MOON_RADIUS_KM
try:
    from . import _moira_native as moira_native
except ImportError:
    moira_native = None

from typing import Sequence

__all__ = [
    "official_lunar_limb_profile_adjustment",
]


def _require_lunar_extra() -> None:
    missing: list[str] = []
    causes: list[str] = []
    if not _HAS_SPICEYPY:
        missing.append("spiceypy")
        if _spiceypy_exc is not None:
            causes.append(f"spiceypy: {_spiceypy_exc}")
    if not _HAS_LASPY:
        missing.append("laspy[lazrs]")
        if _laspy_exc is not None:
            causes.append(f"laspy: {_laspy_exc}")
    if not _HAS_REQUESTS:
        missing.append("requests")
        if _requests_exc is not None:
            causes.append(f"requests: {_requests_exc}")
    if not missing:
        return

    detail = f" Missing dependencies: {', '.join(missing)}."
    if causes:
        detail += " Import errors: " + "; ".join(causes) + "."
    raise ImportError(
        "Official lunar limb / graze support requires the optional "
        "`moira-astro[lunar]` extra." + detail
    )


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
_NATIVE_LSK_MIN_JD_UTC = 2441317.5
_MIN_LOLA_QUERY_HALF_WIDTH_KM = 250.0
_DEFAULT_LOLA_QUERY_HALF_WIDTH_KM = 250.0


def _stac_tile_cache_path(cache_root: Path) -> Path:
    return cache_root / "stac_tile_cache.json"


def _load_stac_tile_cache(cache_root: Path) -> dict[str, str]:
    cache_path = _stac_tile_cache_path(cache_root)
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _store_stac_tile_cache(cache_root: Path, cache: dict[str, str]) -> None:
    cache_path = _stac_tile_cache_path(cache_root)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


@dataclass(frozen=True, slots=True)
class _LolaTile:
    """Vessel: Cached LOLA point-cloud tile with native substrate storage."""
    point_cloud: "moira_native.LolaPointCloud"


@dataclass(frozen=True, slots=True)
class _ObserverLimbContext:
    """Vessel: Ephemeris and orientation context for a specific lunar-limb observer epoch."""
    subobserver_lon_deg: float
    subobserver_lat_deg: float
    los_j2000: Sequence[float]
    observer_dir_moon: Sequence[float]
    sky_north_moon: Sequence[float]
    sky_east_moon: Sequence[float]


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
    _require_lunar_extra()
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
            if filename == "naif0012.tls" and moira_native is not None and hasattr(moira_native, "load_naif_lsk"):
                moira_native.load_naif_lsk(str(path))
        _KERNELS_LOADED = True


def _jd_ut_to_et(jd_ut: float) -> float:
    """
    Admit the lunar-limb epoch as a UTC-style Julian Day, matching the historic
    `sp.str2et(f"JD {jd_ut}")` production path.

    This preserves the existing SPICE semantics for bare `JD` admission rather
    than reinterpreting the input as a generic Delta-T-adjusted UT1 timescale.
    The current native admitted regime begins at 1972-01-01 UTC, which is the
    first epoch explicitly covered by the loaded NAIF leap-second schedule.
    """
    if (
        moira_native is not None
        and hasattr(moira_native, "jd_utc_to_et_seconds_past_j2000")
        and jd_ut >= _NATIVE_LSK_MIN_JD_UTC
    ):
        return float(moira_native.jd_utc_to_et_seconds_past_j2000(jd_ut))
    _require_lunar_extra()
    return sp.str2et(f"JD {jd_ut}")


def _normalize_lon_deg(lon_deg: float) -> float:
    return ((lon_deg + 180.0) % 360.0) - 180.0


def _norm(vec: Sequence[float]) -> tuple[float, float, float]:
    m = math.sqrt(sum(x*x for x in vec))
    if m == 0:
        return (vec[0], vec[1], vec[2])
    return (vec[0] / m, vec[1] / m, vec[2] / m)


def _dot(v1: Sequence[float], v2: Sequence[float]) -> float:
    return sum(x*y for x, y in zip(v1, v2))


def _project_onto_sky(vec: Sequence[float], los: Sequence[float]) -> tuple[float, float, float]:
    d = _dot(vec, los)
    return (vec[0] - d * los[0], vec[1] - d * los[1], vec[2] - d * los[2])


def _add(v1: Sequence[float], v2: Sequence[float]) -> tuple[float, float, float]:
    return (v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2])


def _scale(vec: Sequence[float], s: float) -> tuple[float, float, float]:
    return (vec[0] * s, vec[1] * s, vec[2] * s)


def _earth_observer_position_km(
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
) -> tuple[float, float, float]:
    if moira_native is not None and hasattr(moira_native, "geodetic_to_cartesian_wgs84"):
        pos = moira_native.geodetic_to_cartesian_wgs84(
            observer_lon,
            observer_lat,
            observer_elev_m,
        )
        return (float(pos.x), float(pos.y), float(pos.z))

    _, radii = sp.bodvrd("EARTH", "RADII", 3)
    equatorial_radius_km = float(radii[0])
    polar_radius_km = float(radii[2])
    flattening = (equatorial_radius_km - polar_radius_km) / equatorial_radius_km
    pos = sp.georec(
        math.radians(observer_lon),
        math.radians(observer_lat),
        observer_elev_m / 1000.0,
        equatorial_radius_km,
        flattening,
    )
    return (float(pos[0]), float(pos[1]), float(pos[2]))


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
    moon_state_j2000, _ = sp.spkcpo(
        "MOON",
        et,
        "J2000",
        "OBSERVER",
        "LT+S",
        list(observer_pos_iau_earth),
        "EARTH",
        "IAU_EARTH",
    )
    observer_to_moon_j2000 = (float(moon_state_j2000[0]), float(moon_state_j2000[1]), float(moon_state_j2000[2]))
    los_j2000 = _norm(observer_to_moon_j2000)
    moon_to_observer_j2000 = (-observer_to_moon_j2000[0], -observer_to_moon_j2000[1], -observer_to_moon_j2000[2])
    j2000_to_moon = sp.pxform("J2000", "MOON_ME", et)
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        m_obs_moon_raw = moira_native.rotation_matrix_apply(j2000_to_moon, moon_to_observer_j2000)
    else:
        m_obs_moon_raw = sp.mxv(j2000_to_moon, list(moon_to_observer_j2000))
    moon_to_observer_moon = _norm((float(m_obs_moon_raw[0]), float(m_obs_moon_raw[1]), float(m_obs_moon_raw[2])))
    
    if moira_native is not None and hasattr(moira_native, "vec3_to_lonlat_signed"):
        lon_deg, lat_deg, _ = moira_native.vec3_to_lonlat_signed(moira_native.Vec3(*moon_to_observer_moon))
    else:
        _, lon_rad, lat_rad = sp.reclat(list(moon_to_observer_moon))
        lon_deg = lon_rad * sp.dpr()
        lat_deg = lat_rad * sp.dpr()
    moon_to_j2000 = sp.pxform("MOON_ME", "J2000", et)
    
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        m_north_j2000_raw = moira_native.rotation_matrix_apply(moon_to_j2000, (0.0, 0.0, 1.0))
    else:
        m_north_j2000_raw = sp.mxv(moon_to_j2000, [0.0, 0.0, 1.0])
    moon_north_j2000 = _norm((float(m_north_j2000_raw[0]), float(m_north_j2000_raw[1]), float(m_north_j2000_raw[2])))
    
    celestial_north_j2000 = (0.0, 0.0, 1.0)
    sky_north_j2000 = _norm(_project_onto_sky(celestial_north_j2000, los_j2000))
    
    cross_raw = (
        los_j2000[1]*sky_north_j2000[2] - los_j2000[2]*sky_north_j2000[1],
        los_j2000[2]*sky_north_j2000[0] - los_j2000[0]*sky_north_j2000[2],
        los_j2000[0]*sky_north_j2000[1] - los_j2000[1]*sky_north_j2000[0]
    )
    sky_east_j2000 = _norm(cross_raw)
    
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        s_north_moon_raw = moira_native.rotation_matrix_apply(j2000_to_moon, sky_north_j2000)
    else:
        s_north_moon_raw = sp.mxv(j2000_to_moon, list(sky_north_j2000))
    sky_north_moon = _norm((float(s_north_moon_raw[0]), float(s_north_moon_raw[1]), float(s_north_moon_raw[2])))
    
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        s_east_moon_raw = moira_native.rotation_matrix_apply(j2000_to_moon, sky_east_j2000)
    else:
        s_east_moon_raw = sp.mxv(j2000_to_moon, list(sky_east_j2000))
    sky_east_moon = _norm((float(s_east_moon_raw[0]), float(s_east_moon_raw[1]), float(s_east_moon_raw[2])))
    
    return _ObserverLimbContext(
        subobserver_lon_deg=float(lon_deg),
        subobserver_lat_deg=float(lat_deg),
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
    limb_vec_moon = _add(
        _scale(context.sky_north_moon, math.cos(pa_rad)),
        _scale(context.sky_east_moon, math.sin(pa_rad))
    )
    limb_vec_moon = _norm(limb_vec_moon)
    if moira_native is not None and hasattr(moira_native, "vec3_to_lonlat_signed"):
        lon_deg, lat_deg, _ = moira_native.vec3_to_lonlat_signed(moira_native.Vec3(*limb_vec_moon))
        return _normalize_lon_deg(float(lon_deg)), float(lat_deg)

    _, lon_rad, lat_rad = sp.reclat(limb_vec_moon)
    return _normalize_lon_deg(lon_rad * sp.dpr()), lat_rad * sp.dpr()


@lru_cache(maxsize=128)
def _lola_tile_asset_url(lon_bin: int, lat_bin: int, cache_root_str: str) -> str:
    cache_root = Path(cache_root_str)
    cache_key = f"{lon_bin},{lat_bin}"
    cache = _load_stac_tile_cache(cache_root)
    cached_url = cache.get(cache_key)
    if cached_url:
        return cached_url

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
    url = str(features[0]["assets"]["data"]["href"])
    with _CACHE_LOCK:
        cache = _load_stac_tile_cache(cache_root)
        cache[cache_key] = url
        _store_stac_tile_cache(cache_root, cache)
    return url


@lru_cache(maxsize=16)
def _load_lola_tile(url: str, cache_root_str: str) -> _LolaTile:
    _require_lunar_extra()
    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")
    
    cache_root = Path(cache_root_str)
    tile_path = _download_file(url, cache_root / "lola_tiles" / Path(url).name)
    if tile_path.suffixes[-2:] == [".copc", ".laz"]:
        reader = CopcReader.open(tile_path)
        bounds = Bounds(reader.header.mins, reader.header.maxs)
        las = reader.query(bounds=bounds)
    else:
        las = laspy.read(tile_path)
    
    # Initialize native point cloud directly from LAS coordinates (converted to KM)
    pc = moira_native.LolaPointCloud(
        [float(x) / 1000.0 for x in las.x],
        [float(y) / 1000.0 for y in las.y],
        [float(z) / 1000.0 for z in las.z]
    )
    
    return _LolaTile(point_cloud=pc)


@lru_cache(maxsize=64)
def _load_lola_tile_region(
    url: str,
    cache_root_str: str,
    center_lon_deg: float,
    center_lat_deg: float,
    half_width_km: float,
) -> _LolaTile:
    """
    Load only a bounded COPC region around the requested limb point when possible.

    The oracle and production path only need a small neighborhood around the
    smooth-limb target, not every point in each 15-degree LOLA tile. Querying
    the COPC octree directly avoids whole-file decode costs while preserving the
    final silhouette solve.
    """
    _require_lunar_extra()
    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")

    cache_root = Path(cache_root_str)
    tile_path = _download_file(url, cache_root / "lola_tiles" / Path(url).name)

    if tile_path.suffixes[-2:] != [".copc", ".laz"]:
        return _load_lola_tile(url, cache_root_str)

    center = moira_native.lonlat_to_vec3(center_lon_deg, center_lat_deg, MOON_RADIUS_KM)
    half_width_m = half_width_km * 1000.0
    bounds = Bounds(
        (center.x * 1000.0 - half_width_m, center.y * 1000.0 - half_width_m, center.z * 1000.0 - half_width_m),
        (center.x * 1000.0 + half_width_m, center.y * 1000.0 + half_width_m, center.z * 1000.0 + half_width_m),
    )

    reader = CopcReader.open(tile_path)
    las = reader.query(bounds=bounds)

    pc = moira_native.LolaPointCloud(
        [float(x) / 1000.0 for x in las.x],
        [float(y) / 1000.0 for y in las.y],
        [float(z) / 1000.0 for z in las.z]
    )

    return _LolaTile(point_cloud=pc)


def _lola_neighbor_tile_urls(lon_deg: float, lat_deg: float, cache_root: Path) -> tuple[str, ...]:
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
                url = _lola_tile_asset_url(lon_bin + lon_offset, lat_bin + lat_offset, str(cache_root))
            except FileNotFoundError:
                continue
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return tuple(urls)




def _sample_lola_limb_elevation_m(
    lon_deg: float,
    lat_deg: float,
    observer_context: _ObserverLimbContext,
    position_angle_deg: float,
    cache_root: Path,
    query_half_width_km: float,
) -> float:
    """
    Sample LOLA elevation near the limb using native substrate kernels.
    """
    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")

    all_east: list[float] = []
    all_north: list[float] = []
    all_radius: list[float] = []
    all_pa: list[float] = []
    
    obs_vec = moira_native.Vec3(*observer_context.observer_dir_moon)
    east_vec = moira_native.Vec3(*observer_context.sky_east_moon)
    north_vec = moira_native.Vec3(*observer_context.sky_north_moon)
    
    for tile_url in _lola_neighbor_tile_urls(lon_deg, lat_deg, cache_root):
        tile = _load_lola_tile_region(
            tile_url,
            str(cache_root),
            lon_deg,
            lat_deg,
            query_half_width_km,
        )
        
        # 1. Combined Filter (Visibility, PA window, Radius floor)
        filtered_pc = tile.point_cloud.filter_combined(
            obs_vec, east_vec, north_vec, 
            position_angle_deg, _LIMB_PA_WINDOW_DEG, _LIMB_RADIAL_FLOOR_KM
        )
        
        if filtered_pc.size() == 0:
            continue
            
        # 2. Bulk Projection
        proj = filtered_pc.project_to_sky_plane(obs_vec, east_vec, north_vec)
        all_east.extend(proj.east_km)
        all_north.extend(proj.north_km)
        all_radius.extend(proj.radius_km)
        all_pa.extend(proj.pa_deg)
        
    if not all_east:
        return 0.0
        
    # 3. Global Binning
    bins = moira_native.bin_by_position_angle(all_pa, position_angle_deg, _LIMB_BIN_WIDTH_DEG)
    
    # 4. Lexsort and selection of max radius per bin
    indices = moira_native.lexsort_by_bin_and_radius(bins, all_radius)
    
    # Extract the point with maximum radius for each bin
    # Since lexsort is (bin, radius) ascending, the last occurrence of each bin is the max
    best_indices = []
    if len(indices) > 0:
        for i in range(len(indices) - 1):
            if bins[indices[i]] != bins[indices[i+1]]:
                best_indices.append(indices[i])
        best_indices.append(indices[-1])
        
    hull_pts = [moira_native.Point2D(all_east[i], all_north[i]) for i in best_indices]
    
    # 5. Native Convex Hull
    hull = moira_native.convex_hull_2d(hull_pts)
    
    # 6. Native Ray-Hull Intersection
    silhouette_radius_km = moira_native.ray_hull_intersection(hull, position_angle_deg, MOON_RADIUS_KM)
    
    return silhouette_radius_km * 1000.0 - _LOLA_MEAN_RADIUS_M


def official_lunar_limb_profile_adjustment(
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
    moon_distance_km: float,
    *,
    lola_query_half_width_km: float = _DEFAULT_LOLA_QUERY_HALF_WIDTH_KM,
) -> float:
    """
    Return an official-source lunar-limb correction in angular degrees.

    The current implementation uses:
    - NAIF lunar orientation kernels for body-frame geometry
    - official USGS/LOLA COPC tiles for limb topography

    Runtime policy:
    - `lola_query_half_width_km` controls the bounded COPC neighborhood sampled
      around the smooth-limb target. This is an explicit performance policy, not
      a hidden astronomical model change.
    - widths below `250 km` are not admitted because narrower windows failed the
      oracle safety sweep on the current validation corpus.

    """
    if lola_query_half_width_km < _MIN_LOLA_QUERY_HALF_WIDTH_KM:
        raise ValueError(
            f"lola_query_half_width_km must be at least {_MIN_LOLA_QUERY_HALF_WIDTH_KM} km."
        )

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
        lola_query_half_width_km,
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
