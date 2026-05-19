"""
Moira — planets.py
The Planetary Oracle: governs geocentric ecliptic position computation for all
major bodies using DE441 barycentric state vectors.

Boundary: owns the full pipeline from raw SPK state vectors to final PlanetData
result vessels. Delegates kernel I/O to spk_reader, coordinate transforms to
coordinates, and time conversion to julian. Does not own house calculations,
aspect detection, or any display formatting.

Public surface:
    PlanetData, SkyPosition, HeliocentricData, CartesianPosition,
    planet_at(), sky_position_at(), all_planets_at(),
    heliocentric_planet_at(), all_heliocentric_at(), sun_longitude(),
    planet_relative_to(), next_heliocentric_transit()

    DeltaTPolicy is imported from moira.julian and threaded through planet_at()
    and sky_position_at() via the delta_t_policy= kwarg.

Import-time side effects: None

External dependency assumptions:
    - jplephem must be importable (via spk_reader).
    - DE441 kernel must exist at kernels/de441.bsp (accessed lazily on first call).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from collections import OrderedDict

try:
    from . import moira_native as _moira_native
except ImportError:
    _moira_native = None

from .constants import (
    Body, NAIF, NAIF_ROUTES, EARTH_ROUTE,
    DEG2RAD, RAD2DEG, sign_of, KM_PER_AU,
)
from .coordinates import (
    Vec3, vec_add, vec_sub, vec_norm, mat_vec_mul, mat_mul,
    icrf_to_ecliptic, icrf_to_equatorial, equatorial_to_horizontal,
    normalize_degrees, precession_matrix_equatorial, nutation_matrix_equatorial,
    icrf_to_true_ecliptic, nutation_matrix_from_terms,
)
from .obliquity import mean_obliquity, true_obliquity, nutation as _nutation
from .julian import ut_to_tt, centuries_from_j2000, local_sidereal_time, decimal_year, DeltaTPolicy
from .spk_reader import get_active_reader, get_reader, KernelReader, SpkReader, MissingKernelError
from .corrections import (
    apply_light_time, apply_aberration, apply_deflection, apply_frame_bias,
    apply_refraction, SCHWARZSCHILD_RADII,
    topocentric_correction, apply_diurnal_aberration, C_KM_PER_DAY,
)
from .precession import general_precession_in_longitude

__all__ = [
    "PlanetData",
    "SkyPosition",
    "HeliocentricData",
    "CartesianPosition",
    "planet_at",
    "sky_position_at",
    "all_planets_at",
    "heliocentric_planet_at",
    "all_heliocentric_at",
    "sun_longitude",
    "planet_relative_to",
    "next_heliocentric_transit",
    "approx_year",
]

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class PlanetData:
    """
    RITE: The Planetary Data Vessel

    THEOREM: PlanetData serves as the read-only result vessel for a single
        geocentric ecliptic position computation, carrying longitude, latitude,
        distance, speed, and derived sign data for one celestial body.

    RITE OF PURPOSE:
        PlanetData is the canonical output type of planet_at() and
        all_planets_at(). It exists to give callers a single, self-contained
        object that encodes every piece of positional information they need —
        raw ecliptic coordinates, daily motion, retrograde flag, and
        pre-computed zodiacal sign — without requiring them to call any
        further computation functions.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the geocentric ecliptic longitude, latitude, distance,
              and daily speed for one body at one instant.
            - Derive and store the zodiacal sign, sign symbol, and degree
              within sign via __post_init__.
            - Expose longitude_dms and distance_au as convenience properties.
        Non-responsibilities:
            - Does not compute positions; it only stores them.
            - Does not perform coordinate transforms or time conversions.
            - Does not validate that longitude is in [0, 360) — callers
              are responsible for normalisation before construction.
        Dependencies:
            - sign_of() from constants must be importable at construction time.
        Structural invariants:
            - sign, sign_symbol, and sign_degree are always consistent with
              longitude after __post_init__ completes.
            - retrograde is always True iff speed < 0.
        Behavioral invariants:
            - All fields are set at construction time and never mutated
              after __post_init__ returns.
        Failure behavior:
            - Raises whatever sign_of() raises if longitude is out of range.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planets.PlanetData",
      "risk": "high",
      "api": {
        "frozen": ["longitude", "latitude", "distance", "speed", "retrograde",
                   "is_topocentric", "sign", "sign_symbol", "sign_degree",
                   "longitude_dms", "distance_au"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["PlanetData"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    name:           str
    longitude:      float          # ecliptic longitude, degrees [0, 360)
    latitude:       float          # ecliptic latitude, degrees
    distance:       float          # distance from Earth, km
    speed:          float          # daily motion in longitude, degrees/day (always geocentric rate)
    retrograde:     bool           # True when speed < 0
    is_topocentric: bool = False   # True when topocentric parallax has been applied
    sign:           str  = field(init=False)
    sign_symbol:    str  = field(init=False)
    sign_degree:    float= field(init=False)

    def __post_init__(self) -> None:
        sign, sign_symbol, sign_degree = sign_of(self.longitude)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "sign_symbol", sign_symbol)
        object.__setattr__(self, "sign_degree", sign_degree)

    @property
    def longitude_dms(self) -> tuple[int, int, float]:
        """Longitude within sign as (degrees, minutes, seconds)."""
        d = self.sign_degree
        deg = int(d)
        m   = int((d - deg) * 60)
        s   = ((d - deg) * 60 - m) * 60
        return deg, m, s

    @property
    def distance_au(self) -> float:
        """Distance from Earth in Astronomical Units (AU)."""
        return self.distance / KM_PER_AU

    def __repr__(self) -> str:
        r = "℞" if self.retrograde else ""
        deg, m, s = self.longitude_dms
        return (f"{self.name}: {deg}°{m:02d}′{s:04.1f}″ {self.sign} {self.sign_symbol}"
                f"  ({self.longitude:.4f}°) {r}  Δ={self.speed:+.4f}°/d")


@dataclass(slots=True, frozen=True)
class SkyPosition:
    """
    RITE: The Sky Position Vessel

    THEOREM: SkyPosition serves as the read-only result vessel for a
        topocentric apparent sky position, carrying right ascension,
        declination, azimuth, altitude, and distance for one body as seen
        from a specific terrestrial observer.

    RITE OF PURPOSE:
        SkyPosition is the canonical output type of sky_position_at(). It
        exists to give callers a single, self-contained object that encodes
        the full apparent position of a body in both equatorial and horizontal
        coordinate systems, as computed after the complete 7-step apparent
        position pipeline (light-time, deflection, aberration, frame bias,
        precession, nutation, topocentric correction).

    LAW OF OPERATION:
        Responsibilities:
            - Hold the topocentric right ascension, declination, azimuth,
              altitude, and distance for one body at one instant.
        Non-responsibilities:
            - Does not compute positions; it only stores them.
            - Does not perform coordinate transforms or time conversions.
            - Does not validate that azimuth is in [0, 360) or altitude
              is in [−90, 90].
        Dependencies:
            - No external dependencies at construction time.
        Structural invariants:
            - All five numeric fields are set at construction time and never
              mutated after __init__ returns.
        Behavioral invariants:
            - All fields are read-only after construction.
        Failure behavior:
            - Raises TypeError if any field receives a value of the wrong type.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planets.SkyPosition",
      "risk": "high",
      "api": {
        "frozen": ["name", "right_ascension", "declination", "azimuth",
                   "altitude", "distance"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["SkyPosition"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    name: str
    right_ascension: float   # degrees
    declination: float       # degrees
    azimuth: float           # degrees, north=0 east=90
    altitude: float          # degrees
    distance: float          # km

    def __repr__(self) -> str:
        return (
            f"SkyPosition({self.name!r}, RA={self.right_ascension:.5f}°, "
            f"Dec={self.declination:.5f}°, Az={self.azimuth:.5f}°, "
            f"Alt={self.altitude:.5f}°)"
        )


# ---------------------------------------------------------------------------
# Heliocentric result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class HeliocentricData:
    """
    RITE: The Heliocentric Data Vessel

    THEOREM: HeliocentricData serves as the read-only result vessel for a
        single heliocentric ecliptic position computation, carrying longitude,
        latitude, distance, speed, and derived sign data for one body
        measured from the Sun.

    RITE OF PURPOSE:
        HeliocentricData is the canonical output type of
        heliocentric_planet_at() and all_heliocentric_at(). It exists to
        give callers a self-contained object encoding the Sun-centred
        position of a body in the true-of-date ecliptic frame, mirroring
        the structure of PlanetData for the heliocentric case. Without it,
        callers would need to interpret raw ICRF vectors themselves.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the heliocentric ecliptic longitude, latitude, distance,
              and daily speed for one body at one instant.
            - Derive and store the zodiacal sign, sign symbol, and degree
              within sign via __post_init__.
            - Expose distance_au as a convenience property.
        Non-responsibilities:
            - Does not compute positions; it only stores them.
            - Does not perform coordinate transforms or time conversions.
            - Does not validate that longitude is in [0, 360).
        Dependencies:
            - sign_of() from constants must be importable at construction time.
        Structural invariants:
            - sign, sign_symbol, and sign_degree are always consistent with
              longitude after __post_init__ completes.
            - retrograde is always True iff speed < 0.
        Behavioral invariants:
            - All fields are set at construction time and never mutated
              after __post_init__ returns.
        Failure behavior:
            - Raises whatever sign_of() raises if longitude is out of range.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planets.HeliocentricData",
      "risk": "high",
      "api": {
        "frozen": ["longitude", "latitude", "distance", "speed", "retrograde",
                   "sign", "sign_symbol", "sign_degree", "distance_au"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["HeliocentricData"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    longitude:   float   # heliocentric ecliptic longitude [0, 360)
    latitude:    float   # heliocentric ecliptic latitude
    distance:    float   # distance from Sun, km
    speed:       float   # daily motion in longitude, °/day
    retrograde:  bool    # True when speed < 0
    sign:        str     = field(init=False)
    sign_symbol: str     = field(init=False)
    sign_degree: float   = field(init=False)

    def __post_init__(self) -> None:
        sign, sign_symbol, sign_degree = sign_of(self.longitude)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "sign_symbol", sign_symbol)
        object.__setattr__(self, "sign_degree", sign_degree)

    @property
    def distance_au(self) -> float:
        return self.distance / KM_PER_AU

    def __repr__(self) -> str:
        r = "℞" if self.retrograde else ""
        return (f"[helio] {self.name}: {self.longitude:.4f}°  "
                f"{self.sign} {self.sign_degree:.2f}  "
                f"r={self.distance_au:.4f} AU  {r}")


@dataclass(slots=True, frozen=True)
class CartesianPosition:
    """
    RITE: The Cartesian Position Vessel

    THEOREM: CartesianPosition is the read-only result vessel for a planetary
        position expressed as rectangular coordinates (km) rather than
        ecliptic longitude/latitude.  The coordinate orientation depends on
        the requested correction path: true equatorial of date when
        ``apparent=True`` and geometric ICRF when ``apparent=False``.

    RITE OF PURPOSE:
        CartesianPosition is returned by planet_at(..., frame='cartesian').
        It exists so callers who need raw rectangular vectors for orbital
        mechanics, numerical integration, or migration from integer flag
        APIs can
        receive a typed, self-describing result instead of a bare tuple.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the rectangular X/Y/Z position in the true equatorial frame
              of date (after the full apparent pipeline when apparent=True, or
              in geometric ICRF when apparent=False).
            - Carry the center and frame labels so callers know the reference.
        Non-responsibilities:
            - Does not compute positions; it only stores them.
            - Does not validate that coordinates are finite or non-zero.
        Dependencies:
            - No external dependencies at construction time.
        Structural invariants:
            - x, y, z are in kilometres.
            - center is 'geocentric' or 'barycentric'.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planets.CartesianPosition",
      "risk": "low",
      "api": {"frozen": ["name", "x", "y", "z", "center"], "internal": []},
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "none"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    name:   str
    x:      float   # km, true equatorial frame of date (apparent) or ICRF/J2000 (astrometric)
    y:      float   # km
    z:      float   # km
    center: str     # 'geocentric' or 'barycentric'

    def __repr__(self) -> str:
        return (
            f"CartesianPosition({self.name!r}, "
            f"x={self.x:.3f} km, y={self.y:.3f} km, z={self.z:.3f} km, "
            f"center={self.center!r})"
        )


# ---------------------------------------------------------------------------
# Internal: chain SPK segments to get barycentric position
# ---------------------------------------------------------------------------

_VectorCache = dict[tuple[str, str, float], object]
_NPE_ADMITTED_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)
_NPE_PUBLIC_ROUTE_PAIRS = (
    (0, 10),
    (0, 3),
    (3, 399),
    (3, 301),
    (0, 1),
    (1, 199),
    (0, 2),
    (2, 299),
    (0, 4),
    (0, 5),
    (0, 6),
    (0, 7),
    (0, 8),
    (0, 9),
)
_NPE_BODY_ROUTE_PAIRS = {
    Body.SUN: ((0, 10),),
    Body.MOON: ((0, 3), (3, 301)),
    Body.MERCURY: ((0, 1), (1, 199)),
    Body.VENUS: ((0, 2), (2, 299)),
    Body.EARTH: ((0, 3), (3, 399)),
    Body.MARS: ((0, 4),),
    Body.JUPITER: ((0, 5),),
    Body.SATURN: ((0, 6),),
    Body.URANUS: ((0, 7),),
    Body.NEPTUNE: ((0, 8),),
    Body.PLUTO: ((0, 9),),
}


@dataclass(slots=True)
class _ApparentContext:
    """Internal one-JD cache for shared apparent-path state."""

    jd_tt: float
    dpsi_deg: float
    deps_deg: float
    obliquity: float
    rot_mat: object | None
    vector_cache: _VectorCache
    earth_ssb: Vec3 | None = None
    earth_vel: Vec3 | None = None
    sun_geocentric: Vec3 | None = None
    jupiter_geocentric: Vec3 | None = None
    saturn_geocentric: Vec3 | None = None


_HAS_NATIVE_ROTATION = (
    _moira_native is not None
    and hasattr(_moira_native, "rotation_matrix_multiply")
    and hasattr(_moira_native, "rotation_matrix_apply")
)
# Keep enough one-JD contexts to cover ordinary chart/batch slices without
# evicting them before adjacent same-reader lookups can reuse the work.
_APPARENT_CONTEXT_CACHE_LIMIT = 32


def _reader_apparent_context_cache(reader: KernelReader):
    """Return the per-reader apparent-context cache when the reader can own one."""
    cache = getattr(reader, "_planetary_apparent_context_cache", None)
    if cache is not None:
        return cache
    try:
        cache = OrderedDict()
        setattr(reader, "_planetary_apparent_context_cache", cache)
        return cache
    except Exception:
        return None


def _reader_planet_call_cache(reader: KernelReader):
    """Return the per-reader same-JD single-body cache when the reader can own one."""
    cache = getattr(reader, "_planetary_planet_at_call_cache", None)
    if cache is not None:
        return cache
    try:
        cache = OrderedDict()
        setattr(reader, "_planetary_planet_at_call_cache", cache)
        return cache
    except Exception:
        return None


def _cached_planet_call_context(
    reader: KernelReader,
    *,
    jd_ut: float,
    apparent: bool,
    nutation: bool,
    delta_t_policy: 'DeltaTPolicy | None',
) -> tuple[float, _ApparentContext] | None:
    """
    Return cached TT/context state for repeated same-reader same-JD lookups.

    This is intentionally narrow: it only admits the default Delta-T path so
    that the cache key stays exact without introducing policy ambiguity.
    """
    if not apparent or delta_t_policy is not None:
        return None
    cache = _reader_planet_call_cache(reader)
    if cache is None:
        return None
    key = (jd_ut, apparent, nutation)
    state = cache.get(key)
    if state is not None:
        cache.move_to_end(key)
    return state


def _store_planet_call_context(
    reader: KernelReader,
    *,
    jd_ut: float,
    jd_tt: float,
    apparent: bool,
    nutation: bool,
    context: _ApparentContext,
) -> None:
    """Store repeated same-JD single-body setup on the live reader with a tiny LRU law."""
    if not apparent:
        return
    cache = _reader_planet_call_cache(reader)
    if cache is None:
        return
    key = (jd_ut, apparent, nutation)
    cache[key] = (jd_tt, context)
    cache.move_to_end(key)
    while len(cache) > _APPARENT_CONTEXT_CACHE_LIMIT:
        cache.popitem(last=False)


def _cached_apparent_context(
    reader: KernelReader,
    *,
    jd_tt: float,
    apparent: bool,
    nutation: bool,
) -> _ApparentContext | None:
    """Return a cached one-JD apparent context for repeated single-body lookups."""
    if not apparent:
        return None
    cache = _reader_apparent_context_cache(reader)
    if cache is None:
        return None
    key = (jd_tt, apparent, nutation)
    context = cache.get(key)
    if context is not None:
        cache.move_to_end(key)
    return context


def _store_apparent_context(
    reader: KernelReader,
    *,
    jd_tt: float,
    apparent: bool,
    nutation: bool,
    context: _ApparentContext,
) -> None:
    """Store a one-JD apparent context on the live reader with a tiny LRU law."""
    if not apparent:
        return
    cache = _reader_apparent_context_cache(reader)
    if cache is None:
        return
    key = (jd_tt, apparent, nutation)
    cache[key] = context
    cache.move_to_end(key)
    while len(cache) > _APPARENT_CONTEXT_CACHE_LIMIT:
        cache.popitem(last=False)


def _npe_all_planets_mode_is_admitted(
    *,
    bodies: list[str],
    reader: KernelReader,
    apparent: bool,
    aberration: bool,
    grav_deflection: bool,
    nutation: bool,
    center: str,
    observer_lat: float | None,
    observer_lon: float | None,
    observer_elev_m: float,
    lst_deg: float | None,
    delta_t_policy: 'DeltaTPolicy | None',
) -> bool:
    """Return True only for the first admitted native public planetary surface."""
    if not bodies or any(body not in _NPE_ADMITTED_BODIES for body in bodies):
        return False
    if not apparent or not aberration or not grav_deflection or not nutation:
        return False
    if center != 'geocentric':
        return False
    if observer_lat is not None or observer_lon is not None or lst_deg is not None:
        return False
    if observer_elev_m != 0.0:
        return False
    if delta_t_policy is not None:
        return False
    if type(reader) is not SpkReader:
        return False
    kernel = getattr(reader, "_kernel", None)
    handle = getattr(kernel, "_handle", None)
    return handle is not None and hasattr(handle, "batch_segment_position_and_velocity")


def _npe_public_route_segment_specs(reader: SpkReader, jd_tt: float):
    """Return native route specs for the admitted planetary segment set, or None."""
    kernel = getattr(reader, "_kernel", None)
    handle = getattr(kernel, "_handle", None)
    if handle is None or not hasattr(handle, "batch_segment_position_and_velocity"):
        return None

    specs: list[tuple[int, int, int]] = []
    for center, target in _NPE_PUBLIC_ROUTE_PAIRS:
        segment = reader._segment_for(center, target, jd_tt)
        if getattr(segment, "_handle", None) is not handle:
            return None
        if not all(hasattr(segment, attr) for attr in ("start_i", "end_i", "data_type")):
            return None
        specs.append((int(segment.start_i), int(segment.end_i), int(segment.data_type)))
    return specs


def _npe_body_route_segment_specs(reader: SpkReader, jd_tt: float):
    """Return admitted per-body route segment specs keyed by body, or None."""
    kernel = getattr(reader, "_kernel", None)
    handle = getattr(kernel, "_handle", None)
    if handle is None or not hasattr(handle, "batch_segment_position_requests"):
        return None

    body_specs: dict[str, tuple[tuple[int, int, int], ...]] = {}
    for body, route in _NPE_BODY_ROUTE_PAIRS.items():
        specs: list[tuple[int, int, int]] = []
        for center, target in route:
            segment = reader._segment_for(center, target, jd_tt)
            if getattr(segment, "_handle", None) is not handle:
                return None
            if not all(hasattr(segment, attr) for attr in ("start_i", "end_i", "data_type")):
                return None
            specs.append((int(segment.start_i), int(segment.end_i), int(segment.data_type)))
        body_specs[body] = tuple(specs)
    return body_specs


def _prefill_npe_public_vector_cache(
    jd_tt: float,
    vector_cache: _VectorCache,
    pair_states: dict[tuple[int, int], tuple[Vec3, Vec3]],
) -> None:
    """Prime the existing planetary cache law from one native batch segment read."""
    ssb_sun = pair_states[(0, 10)]
    ssb_emb = pair_states[(0, 3)]
    emb_earth = pair_states[(3, 399)]
    emb_moon = pair_states[(3, 301)]

    earth_pos = vec_add(ssb_emb[0], emb_earth[0])
    earth_vel = vec_add(ssb_emb[1], emb_earth[1])
    vector_cache[("earth_bary_pos", Body.EARTH, jd_tt)] = earth_pos
    vector_cache[("earth_bary_state", Body.EARTH, jd_tt)] = (earth_pos, earth_vel)
    vector_cache[("body_bary_pos", Body.SUN, jd_tt)] = ssb_sun[0]
    vector_cache[("body_bary_state", Body.SUN, jd_tt)] = ssb_sun

    for body in _NPE_ADMITTED_BODIES:
        if body == Body.SUN:
            bary_pos, bary_vel = ssb_sun
        elif body == Body.MOON:
            bary_pos = vec_add(ssb_emb[0], emb_moon[0])
            bary_vel = vec_add(ssb_emb[1], emb_moon[1])
        else:
            route = NAIF_ROUTES[body]
            bary_pos = (0.0, 0.0, 0.0)
            bary_vel = (0.0, 0.0, 0.0)
            for pair in route:
                pair_pos, pair_vel = pair_states[pair]
                bary_pos = vec_add(bary_pos, pair_pos)
                bary_vel = vec_add(bary_vel, pair_vel)

        geo_pos = vec_sub(bary_pos, earth_pos)
        geo_vel = vec_sub(bary_vel, earth_vel)
        vector_cache[("bary_pos", body, jd_tt)] = bary_pos
        vector_cache[("bary_state", body, jd_tt)] = (bary_pos, bary_vel)
        vector_cache[("geo_pos", body, jd_tt)] = geo_pos
        vector_cache[("geo_state", body, jd_tt)] = (geo_pos, geo_vel)


def _npe_batch_barycentric_positions(
    handle,
    body_segment_specs: dict[str, tuple[tuple[int, int, int], ...]],
    body_jds: dict[str, float],
) -> dict[str, Vec3]:
    """Evaluate admitted per-body barycentric positions for varying JDs in one native batch."""
    requests: list[tuple[int, int, int, float]] = []
    counts: dict[str, int] = {}
    for body, specs in body_segment_specs.items():
        jd = body_jds[body]
        counts[body] = len(specs)
        for start_i, end_i, data_type in specs:
            requests.append((start_i, end_i, data_type, jd))

    raw = handle.batch_segment_position_requests(requests)
    cursor = 0
    results: dict[str, Vec3] = {}
    for body in _NPE_ADMITTED_BODIES:
        count = counts[body]
        x = y = z = 0.0
        for _ in range(count):
            pos = raw[cursor]
            cursor += 1
            x += float(pos[0])
            y += float(pos[1])
            z += float(pos[2])
        results[body] = (x, y, z)
    return results


def _native_all_planets_admitted(
    jd_ut: float,
    bodies: list[str],
    *,
    reader: KernelReader,
    jd_tt: float,
    apparent: bool,
    aberration: bool,
    grav_deflection: bool,
    nutation: bool,
    center: str,
    observer_lat: float | None,
    observer_lon: float | None,
    observer_elev_m: float,
    lst_deg: float | None,
    delta_t_policy: 'DeltaTPolicy | None',
) -> dict[str, PlanetData] | None:
    """Execute the first admitted native public substrate when the exact mode matches."""
    if not _npe_all_planets_mode_is_admitted(
        bodies=bodies,
        reader=reader,
        apparent=apparent,
        aberration=aberration,
        grav_deflection=grav_deflection,
        nutation=nutation,
        center=center,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
        delta_t_policy=delta_t_policy,
    ):
        return None

    specs = _npe_public_route_segment_specs(reader, jd_tt)
    if specs is None:
        return None
    body_segment_specs = _npe_body_route_segment_specs(reader, jd_tt)
    if body_segment_specs is None:
        return None

    handle = reader._kernel._handle
    batch = handle.batch_segment_position_and_velocity(specs, jd_tt)
    pair_states: dict[tuple[int, int], tuple[Vec3, Vec3]] = {}
    for pair, (position, velocity) in zip(_NPE_PUBLIC_ROUTE_PAIRS, batch):
        pos = (float(position[0]), float(position[1]), float(position[2]))
        vel = (float(velocity[0]), float(velocity[1]), float(velocity[2]))
        pair_states[pair] = (pos, vel)

    vector_cache: _VectorCache = {}
    _prefill_npe_public_vector_cache(jd_tt, vector_cache, pair_states)
    context = _build_apparent_context(
        jd_tt,
        reader,
        apparent=apparent,
        nutation=nutation,
        vector_cache=vector_cache,
    )

    earth_ssb = context.earth_ssb
    earth_vel = context.earth_vel
    if earth_ssb is None or earth_vel is None:
        return None

    initial_bary = {
        body: vector_cache[("bary_pos", body, jd_tt)]  # type: ignore[index]
        for body in bodies
    }
    light_times = {
        body: vec_norm(vec_sub(initial_bary[body], earth_ssb)) / C_KM_PER_DAY
        for body in bodies
    }
    geocentric_lt: dict[str, Vec3] = {
        body: vec_sub(initial_bary[body], earth_ssb)
        for body in bodies
    }

    for _ in range(3):
        retarded_jds = {body: jd_tt - light_times[body] for body in bodies}
        body_bary_lt = _npe_batch_barycentric_positions(handle, body_segment_specs, retarded_jds)
        converged = True
        for body in bodies:
            xyz_lt = vec_sub(body_bary_lt[body], earth_ssb)
            lt_new = vec_norm(xyz_lt) / C_KM_PER_DAY
            if abs(lt_new - light_times[body]) >= 1e-14:
                converged = False
            light_times[body] = lt_new
            geocentric_lt[body] = xyz_lt
        if converged:
            break

    results: dict[str, PlanetData] = {}
    for body in bodies:
        xyz0 = geocentric_lt[body]
        if grav_deflection and body not in (Body.SUN, Body.MOON):
            xyz0 = apply_deflection(xyz0, _deflectors_for_body(body, jd_tt, reader, context))
        if aberration:
            xyz0 = apply_aberration(xyz0, earth_vel)

        xyz0 = apply_frame_bias(xyz0)
        if context.rot_mat is not None:
            xyz0 = _apply_rotation_matrix(context.rot_mat, xyz0)
        else:
            xyz0 = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz0)
            xyz0 = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz0)

        lon, lat, dist = icrf_to_ecliptic(xyz0, context.obliquity)
        xyz_rate, vel_rate = vector_cache[("geo_state", body, jd_tt)]  # type: ignore[index]
        speed = _longitude_rate(xyz_rate, vel_rate, context.obliquity)
        results[body] = PlanetData(
            name=body,
            longitude=lon,
            latitude=lat,
            distance=dist,
            speed=speed,
            retrograde=(speed < 0.0),
            is_topocentric=False,
        )
    return results


def _build_apparent_context(
    jd_tt: float,
    reader: KernelReader,
    *,
    apparent: bool,
    nutation: bool,
    vector_cache: _VectorCache | None = None,
) -> _ApparentContext:
    """Build one shared apparent-path context for a single JD."""
    mean_eps = mean_obliquity(jd_tt)
    dpsi_deg = deps_deg = 0.0
    if apparent and nutation:
        dpsi_deg, deps_deg = _nutation(jd_tt)

    obliquity = mean_eps + (deps_deg if (apparent and nutation) else 0.0)
    rot_mat = _compose_rotation_matrix(
        jd_tt,
        with_nutation=(apparent and nutation),
        mean_obliquity_deg=mean_eps,
        dpsi_deg=dpsi_deg,
        deps_deg=deps_deg,
    ) \
        if apparent else None

    cache = vector_cache if vector_cache is not None else {}
    earth_ssb = earth_vel = None
    if apparent:
        earth_ssb, earth_vel = _earth_barycentric_state(jd_tt, reader, cache)

    return _ApparentContext(
        jd_tt=jd_tt,
        dpsi_deg=dpsi_deg,
        deps_deg=deps_deg,
        obliquity=obliquity,
        rot_mat=rot_mat,
        vector_cache=cache,
        earth_ssb=earth_ssb,
        earth_vel=earth_vel,
    )


def _deflectors_for_body(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    context: _ApparentContext,
) -> list[tuple[Vec3, float]]:
    """Return lazily materialized deflector vectors for one target body."""
    if context.sun_geocentric is None:
        context.sun_geocentric = _geocentric(Body.SUN, jd_tt, reader, context.vector_cache)

    deflectors = [(context.sun_geocentric, SCHWARZSCHILD_RADII["Sun"])]

    if body != Body.JUPITER:
        if context.jupiter_geocentric is None:
            context.jupiter_geocentric = _geocentric(Body.JUPITER, jd_tt, reader, context.vector_cache)
        deflectors.append((context.jupiter_geocentric, SCHWARZSCHILD_RADII["Jupiter"]))

    if body != Body.SATURN:
        if context.saturn_geocentric is None:
            context.saturn_geocentric = _geocentric(Body.SATURN, jd_tt, reader, context.vector_cache)
        deflectors.append((context.saturn_geocentric, SCHWARZSCHILD_RADII["Saturn"]))

    return deflectors

def _barycentric(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> Vec3:
    """
    Return the Solar System Barycentric (SSB) position of a body (km, ICRF).
    """
    cache_key = ("bary_pos", body, jd_tt)
    if _vector_cache is not None and cache_key in _vector_cache:
        return _vector_cache[cache_key]  # type: ignore[return-value]

    if body == Body.MOON:
        # Moon relative to EMB + EMB relative to SSB
        emb_moon = reader.position(3, 301, jd_tt)
        ssb_emb  = reader.position(0, 3, jd_tt)
        result = vec_add(ssb_emb, emb_moon)
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result

    # All other bodies: chain from SSB
    route = NAIF_ROUTES[body]
    x = y = z = 0.0
    for center, target in route:
        px, py, pz = reader.position(center, target, jd_tt)
        x += px; y += py; z += pz
    result = (x, y, z)
    if _vector_cache is not None:
        _vector_cache[cache_key] = result
    return result


def _barycentric_state(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> tuple[Vec3, Vec3]:
    """
    Return Solar System Barycentric position and velocity of a body (km, km/day).
    """
    cache_key = ("bary_state", body, jd_tt)
    if _vector_cache is not None and cache_key in _vector_cache:
        return _vector_cache[cache_key]  # type: ignore[return-value]

    route = NAIF_ROUTES[body]

    if body == Body.MOON:
        ssb_emb_pos, ssb_emb_vel = reader.position_and_velocity(0, 3, jd_tt)
        emb_moon_pos, emb_moon_vel = reader.position_and_velocity(3, 301, jd_tt)
        result = (
            vec_add(ssb_emb_pos, emb_moon_pos),
            vec_add(ssb_emb_vel, emb_moon_vel),
        )
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result

    x = y = z = 0.0
    vx = vy = vz = 0.0
    for center, target in route:
        pos, vel = reader.position_and_velocity(center, target, jd_tt)
        x += pos[0]; y += pos[1]; z += pos[2]
        vx += vel[0]; vy += vel[1]; vz += vel[2]
    result = (x, y, z), (vx, vy, vz)
    if _vector_cache is not None:
        _vector_cache[cache_key] = result
    return result


def _earth_barycentric(
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> Vec3:
    """Return Earth's barycentric position (km, ICRF)."""
    cache_key = ("earth_bary_pos", Body.EARTH, jd_tt)
    if _vector_cache is not None and cache_key in _vector_cache:
        return _vector_cache[cache_key]  # type: ignore[return-value]
    ssb_emb = reader.position(0, 3, jd_tt)
    emb_earth = reader.position(3, 399, jd_tt)
    result = vec_add(ssb_emb, emb_earth)
    if _vector_cache is not None:
        _vector_cache[cache_key] = result
    return result


def _earth_barycentric_state(
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> tuple[Vec3, Vec3]:
    """Return Earth's barycentric position and velocity (km, km/day, ICRF)."""
    cache_key = ("earth_bary_state", Body.EARTH, jd_tt)
    if _vector_cache is not None and cache_key in _vector_cache:
        return _vector_cache[cache_key]  # type: ignore[return-value]
    ssb_emb_pos, ssb_emb_vel = reader.position_and_velocity(0, 3, jd_tt)
    emb_earth_pos, emb_earth_vel = reader.position_and_velocity(3, 399, jd_tt)
    result = (
        vec_add(ssb_emb_pos, emb_earth_pos),
        vec_add(ssb_emb_vel, emb_earth_vel),
    )
    if _vector_cache is not None:
        _vector_cache[cache_key] = result
    return result


def _geocentric(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> Vec3:
    """
    Return geocentric ICRF rectangular position of a body (km).
    """
    cache_key = ("geo_pos", body, jd_tt)
    if _vector_cache is not None and cache_key in _vector_cache:
        return _vector_cache[cache_key]  # type: ignore[return-value]

    earth = _earth_barycentric(jd_tt, reader, _vector_cache)

    if body == Body.MOON:
        # Moon position from EMB; Earth position from EMB
        emb_moon  = reader.position(3, 301, jd_tt)
        emb_earth = reader.position(3, 399, jd_tt)
        # Geocentric Moon = EMB→Moon − EMB→Earth
        result = vec_sub(emb_moon, emb_earth)
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result

    if body == Body.SUN:
        ssb_sun = reader.position(0, 10, jd_tt)
        result = vec_sub(ssb_sun, earth)
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result

    # Planets: chain from SSB, then subtract Earth
    bary = _barycentric(body, jd_tt, reader, _vector_cache)
    result = vec_sub(bary, earth)
    if _vector_cache is not None:
        _vector_cache[cache_key] = result
    return result


def _geocentric_state(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> tuple[Vec3, Vec3]:
    """
    Return geocentric ICRF rectangular position and velocity of a body.
    """
    cache_key = ("geo_state", body, jd_tt)
    if _vector_cache is not None and cache_key in _vector_cache:
        return _vector_cache[cache_key]  # type: ignore[return-value]

    earth_pos, earth_vel = _earth_barycentric_state(jd_tt, reader, _vector_cache)

    if body == Body.MOON:
        emb_moon_pos, emb_moon_vel = reader.position_and_velocity(3, 301, jd_tt)
        emb_earth_pos, emb_earth_vel = reader.position_and_velocity(3, 399, jd_tt)
        result = (
            vec_sub(emb_moon_pos, emb_earth_pos),
            vec_sub(emb_moon_vel, emb_earth_vel),
        )
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result

    if body == Body.SUN:
        sun_pos, sun_vel = reader.position_and_velocity(0, 10, jd_tt)
        result = (
            vec_sub(sun_pos, earth_pos),
            vec_sub(sun_vel, earth_vel),
        )
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result

    bary_pos, bary_vel = _barycentric_state(body, jd_tt, reader, _vector_cache)
    result = (
        vec_sub(bary_pos, earth_pos),
        vec_sub(bary_vel, earth_vel),
    )
    if _vector_cache is not None:
        _vector_cache[cache_key] = result
    return result


def _earth_velocity(
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> Vec3:
    """
    Earth's barycentric velocity in km/day (ICRF).
    """
    _, earth_vel = _earth_barycentric_state(jd_tt, reader, _vector_cache)
    return earth_vel


def _longitude_rate(xyz: Vec3, vel_xyz: Vec3, obliquity_deg: float) -> float:
    """
    Instantaneous longitude rate in degrees/day from an equatorial state vector.
    """
    eps = obliquity_deg * DEG2RAD
    cos_eps = math.cos(eps)
    sin_eps = math.sin(eps)

    xe = xyz[0]
    ye = xyz[1] * cos_eps + xyz[2] * sin_eps
    vxe = vel_xyz[0]
    vye = vel_xyz[1] * cos_eps + vel_xyz[2] * sin_eps

    denom = xe * xe + ye * ye
    if denom <= 1e-18:
        return 0.0
    return ((xe * vye - ye * vxe) / denom) * RAD2DEG


# ---------------------------------------------------------------------------
# Internal: pre-composed rotation matrix
# ---------------------------------------------------------------------------

def _compose_rotation_matrix(
    jd_tt: float,
    *,
    with_nutation: bool = True,
    mean_obliquity_deg: float | None = None,
    dpsi_deg: float | None = None,
    deps_deg: float | None = None,
):
    """
    Return the combined equatorial rotation matrix M = M_nut @ M_prec.

    Parameters
    ----------
    jd_tt        : Julian Day (TT)
    with_nutation: If False, returns only M_prec (mean-of-date frame).

    Returns
    -------
    Mat3 tuple-of-tuples, composed natively when available.
    """
    prec_mat = precession_matrix_equatorial(jd_tt)
    if not with_nutation:
        return prec_mat
    if mean_obliquity_deg is not None and dpsi_deg is not None and deps_deg is not None:
        nut_mat = nutation_matrix_from_terms(mean_obliquity_deg, dpsi_deg, deps_deg)
    else:
        nut_mat = nutation_matrix_equatorial(jd_tt)
    if _HAS_NATIVE_ROTATION:
        return _moira_native.rotation_matrix_multiply(nut_mat, prec_mat)
    return mat_mul(nut_mat, prec_mat)


def _apply_rotation_matrix(rot_mat, xyz: Vec3) -> Vec3:
    """Apply a pre-composed equatorial rotation matrix to one vector."""
    if _HAS_NATIVE_ROTATION:
        return _moira_native.rotation_matrix_apply(rot_mat, xyz)
    return mat_vec_mul(rot_mat, xyz)


def _chiron_planet_data(jd_ut: float, reader: KernelReader) -> PlanetData:
    """Bridge explicit Chiron requests to the centaur kernel path."""
    from .asteroids import asteroid_at

    chiron = asteroid_at(Body.CHIRON, jd_ut, reader=reader)
    return PlanetData(
        name=chiron.name,
        longitude=chiron.longitude,
        latitude=chiron.latitude,
        distance=chiron.distance,
        speed=chiron.speed,
        retrograde=chiron.retrograde,
    )


def _planet_at_default_apparent_geocentric_ecliptic(
    body: str,
    *,
    jd_tt: float,
    reader: KernelReader,
    context: _ApparentContext,
) -> PlanetData:
    """
    Fast route for the canonical public single-body chart surface.

    This preserves the same mathematical order as _planet_at_core(), but avoids
    re-checking every generic mode branch on the dominant default path.
    """
    earth_ssb = context.earth_ssb
    earth_vel = context.earth_vel
    rot_mat = context.rot_mat
    if earth_ssb is None or earth_vel is None or rot_mat is None:
        raise RuntimeError("default apparent context is incomplete")

    xyz0, _lt = apply_light_time(
        body,
        jd_tt,
        reader,
        earth_ssb,
        lambda body_, jd_tt_, reader_: _barycentric(body_, jd_tt_, reader_, context.vector_cache),
    )

    if body not in (Body.SUN, Body.MOON):
        xyz0 = apply_deflection(xyz0, _deflectors_for_body(body, jd_tt, reader, context))

    xyz0 = apply_aberration(xyz0, earth_vel)
    xyz0 = apply_frame_bias(xyz0)
    xyz0 = _apply_rotation_matrix(rot_mat, xyz0)

    lon, lat, dist = icrf_to_ecliptic(xyz0, context.obliquity)
    xyz_rate, vel_rate = _geocentric_state(body, jd_tt, reader, context.vector_cache)
    speed = _longitude_rate(xyz_rate, vel_rate, context.obliquity)

    return PlanetData(
        name=body,
        longitude=lon,
        latitude=lat,
        distance=dist,
        speed=speed,
        retrograde=(speed < 0.0),
        is_topocentric=False,
    )


def _planet_at_core(
    body: str,
    jd_ut: float,
    *,
    reader: KernelReader,
    obliquity: float | None,
    apparent: bool,
    aberration: bool,
    grav_deflection: bool,
    nutation: bool,
    center: str,
    frame: str,
    observer_lat: float | None,
    observer_lon: float | None,
    observer_elev_m: float,
    lst_deg: float | None,
    jd_tt: float,
    _dpsi_deg: float | None = None,
    _deps_deg: float | None = None,
    _rot_mat=None,
    _vector_cache: _VectorCache | None = None,
    _context: _ApparentContext | None = None,
) -> 'PlanetData | CartesianPosition':
    """Canonical internal planetary pipeline shared by single- and multi-body routes."""
    context = _context
    if context is not None:
        _vector_cache = context.vector_cache

    dpsi_deg = deps_deg = 0.0
    if apparent and nutation:
        if context is not None:
            dpsi_deg, deps_deg = context.dpsi_deg, context.deps_deg
        elif _dpsi_deg is not None and _deps_deg is not None:
            dpsi_deg, deps_deg = _dpsi_deg, _deps_deg
        else:
            dpsi_deg, deps_deg = _nutation(jd_tt)

    if obliquity is None:
        obliquity = context.obliquity if context is not None else (
            mean_obliquity(jd_tt) + (deps_deg if (apparent and nutation) else 0.0)
        )

    if apparent:
        if context is not None and context.earth_ssb is not None and context.earth_vel is not None:
            earth_ssb, earth_vel = context.earth_ssb, context.earth_vel
        else:
            earth_ssb, earth_vel = _earth_barycentric_state(jd_tt, reader, _vector_cache)

        xyz_geo, _lt = apply_light_time(
            body,
            jd_tt,
            reader,
            earth_ssb,
            lambda body_, jd_tt_, reader_: _barycentric(body_, jd_tt_, reader_, _vector_cache),
        )

        if center == 'barycentric':
            xyz0 = vec_add(xyz_geo, earth_ssb)
        else:
            xyz0 = xyz_geo
            if grav_deflection and body not in (Body.SUN, Body.MOON):
                if context is not None:
                    xyz0 = apply_deflection(xyz0, _deflectors_for_body(body, jd_tt, reader, context))
                else:
                    sun_geocentric = _geocentric(Body.SUN, jd_tt, reader, _vector_cache)
                    deflectors = [(sun_geocentric, SCHWARZSCHILD_RADII["Sun"])]
                    if body != Body.JUPITER:
                        deflectors.append((_geocentric(Body.JUPITER, jd_tt, reader, _vector_cache), SCHWARZSCHILD_RADII["Jupiter"]))
                    if body != Body.SATURN:
                        deflectors.append((_geocentric(Body.SATURN, jd_tt, reader, _vector_cache), SCHWARZSCHILD_RADII["Saturn"]))
                    xyz0 = apply_deflection(xyz0, deflectors)

            if aberration:
                xyz0 = apply_aberration(xyz0, earth_vel)

        xyz0 = apply_frame_bias(xyz0)

        rot_mat = context.rot_mat if context is not None else _rot_mat
        if rot_mat is not None:
            xyz0 = _apply_rotation_matrix(rot_mat, xyz0)
        else:
            xyz0 = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz0)
            if nutation:
                xyz0 = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz0)

    else:
        if center == 'barycentric':
            xyz0 = _barycentric(body, jd_tt, reader, _vector_cache)
        else:
            xyz0 = _geocentric(body, jd_tt, reader, _vector_cache)

    if (
        center == 'geocentric'
        and observer_lat is not None
        and observer_lon is not None
        and lst_deg is not None
    ):
        xyz0 = topocentric_correction(
            xyz0, observer_lat, observer_lon, lst_deg, observer_elev_m, jd_ut=jd_ut
        )
        xyz0 = apply_diurnal_aberration(
            xyz0, observer_lat, observer_lon, lst_deg, observer_elev_m, jd_ut=jd_ut
        )

    if frame == 'cartesian':
        return CartesianPosition(name=body, x=xyz0[0], y=xyz0[1], z=xyz0[2], center=center)

    lon, lat, dist = icrf_to_ecliptic(xyz0, obliquity)
    xyz_rate, vel_rate = _geocentric_state(body, jd_tt, reader, _vector_cache)
    speed = _longitude_rate(xyz_rate, vel_rate, obliquity)

    _topocentric = (center == 'geocentric' and observer_lat is not None and observer_lon is not None)
    return PlanetData(
        name=body,
        longitude=lon,
        latitude=lat,
        distance=dist,
        speed=speed,
        retrograde=(speed < 0.0),
        is_topocentric=_topocentric,
    )


# ---------------------------------------------------------------------------
# Public API: single body
# ---------------------------------------------------------------------------

def planet_at(
    body: str,
    jd_ut: float,
    reader: KernelReader | None = None,
    obliquity: float | None = None,
    apparent: bool = True,
    aberration: bool = True,
    grav_deflection: bool = True,
    nutation: bool = True,
    center: str = 'geocentric',
    frame: str = 'ecliptic',
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    lst_deg: float | None = None,
    jd_tt: float | None = None,
    delta_t_policy: 'DeltaTPolicy | None' = None,
    _dpsi_deg: float | None = None,    # pre-computed nutation params (internal)
    _deps_deg: float | None = None,
    _rot_mat=None,                     # pre-composed numpy rotation matrix (internal)
    _vector_cache: _VectorCache | None = None,
    _context: _ApparentContext | None = None,
) -> 'PlanetData | CartesianPosition':
    """
    Compute the geocentric (or topocentric) ecliptic position of one body.

    Executes the full apparent-position pipeline when ``apparent=True``:
    light-time correction → gravitational deflection → annual aberration →
    frame bias → precession → nutation → optional topocentric correction →
    ecliptic projection. When ``apparent=False``, returns the astrometric
    (geometric) position without any of those corrections.

    Individual correction stages can be disabled independently via the
    ``aberration``, ``grav_deflection``, and ``nutation`` switches. These
    switches only affect the pipeline when ``apparent=True``; they are ignored
    when ``apparent=False``.

    Args:
        body: One of the ``Body.*`` string constants identifying the target
            body (e.g. ``Body.MARS``).
        jd_ut: Julian Day Number in Universal Time (UT1).
        reader: An open ``SpkReader`` instance. If ``None``, the module-level
            singleton returned by ``get_reader()`` is used.
        obliquity: Obliquity of the ecliptic in degrees. If ``None``, it is
            computed automatically: true obliquity (mean + nutation) when
            ``nutation=True``, mean obliquity when ``nutation=False``.
        apparent: If ``True`` (default), apply light-time, aberration, and
            frame bias to produce apparent positions. If ``False``, return
            astrometric (geometric) positions.
        aberration: If ``True`` (default), apply annual aberration correction.
            Ignored when ``apparent=False``. Has no effect when
            ``center='barycentric'`` (aberration is an observer-centric term).
        grav_deflection: If ``True`` (default), apply gravitational deflection.
            Ignored when ``apparent=False`` or ``center='barycentric'``.
        nutation: If ``True`` (default), apply the nutation matrix and use true
            obliquity for the ecliptic projection. When ``False``, the nutation
            step is skipped and mean obliquity is used. Ignored when
            ``apparent=False``.
        center: Reference centre for the position vector. ``'geocentric'``
            (default) returns the position relative to Earth's centre.
            ``'barycentric'`` returns the position relative to the Solar System
            Barycentre; in this mode aberration and deflection are not applied
            (they are observer-centric corrections), but frame rotations
            (frame bias, precession, nutation) still apply when
            ``apparent=True``.
        frame: Output coordinate frame. ``'ecliptic'`` (default) returns a
            ``PlanetData`` with ecliptic longitude/latitude/distance.
            ``'cartesian'`` returns a ``CartesianPosition`` with rectangular
            coordinates (km): raw ICRF when ``apparent=False`` and
            equatorial-of-date when ``apparent=True``.
        observer_lat: Geographic latitude of the observer in degrees. Required
            together with ``observer_lon`` and ``lst_deg`` to apply
            topocentric parallax correction. Has no effect when
            ``center='barycentric'``.
        observer_lon: Geographic longitude of the observer in degrees.
        observer_elev_m: Observer elevation above sea level in metres.
            Defaults to 0.0.
        lst_deg: Local Sidereal Time in degrees. Required when topocentric
            correction is requested.
        jd_tt: Julian Day in Terrestrial Time (TT). Computed from ``jd_ut``
            if ``None``.

    Returns:
        A ``PlanetData`` vessel (default) or a ``CartesianPosition`` vessel
        when ``frame='cartesian'``. Note: ``PlanetData.speed`` is always the
        astrometric geocentric longitude rate regardless of ``center``.

    Raises:
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for the requested body.
        ValueError: If ``center`` or ``frame`` is not a recognised string.
        ValueError: If ``observer_lat`` or ``observer_lon`` is provided without
            ``lst_deg`` — topocentric correction requires all three.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if center not in ('geocentric', 'barycentric'):
        raise ValueError(f"center must be 'geocentric' or 'barycentric', got {center!r}")
    if frame not in ('ecliptic', 'cartesian'):
        raise ValueError(f"frame must be 'ecliptic' or 'cartesian', got {frame!r}")
    if (observer_lat is not None or observer_lon is not None) and lst_deg is None:
        raise ValueError(
            "planet_at: lst_deg is required when observer_lat/observer_lon are provided."
        )

    if reader is None:
        reader = get_active_reader()
        if reader is None:
            raise MissingKernelError(
                "No planetary kernel is provided and no active reader context was found. "
                "Pass a reader explicitly or use the Moira facade."
            )

    if body == Body.CHIRON:
        if center != 'geocentric':
            raise ValueError("planet_at: Chiron currently supports only center='geocentric'.")
        if frame != 'ecliptic':
            raise ValueError("planet_at: Chiron currently supports only frame='ecliptic'.")
        if not apparent:
            raise ValueError("planet_at: Chiron currently supports only apparent=True.")
        if observer_lat is not None or observer_lon is not None or lst_deg is not None:
            raise ValueError("planet_at: Chiron topocentric output is not supported by this API path.")
        if not aberration or not grav_deflection or not nutation:
            raise ValueError(
                "planet_at: Chiron currently supports only the default apparent correction path."
            )
        return _chiron_planet_data(jd_ut, reader)

    context = _context
    if jd_tt is None and context is None and apparent:
        cached_state = _cached_planet_call_context(
            reader,
            jd_ut=jd_ut,
            apparent=apparent,
            nutation=nutation,
            delta_t_policy=delta_t_policy,
        )
        if cached_state is not None:
            jd_tt, context = cached_state

    if jd_tt is None:
        year, month, *_ = _approx_year(jd_ut)
        jd_tt = ut_to_tt(jd_ut, decimal_year(year, month), delta_t_policy=delta_t_policy)

    built_context = False
    if context is None and apparent:
        context = _cached_apparent_context(
            reader,
            jd_tt=jd_tt,
            apparent=apparent,
            nutation=nutation,
        )
    if context is None and apparent:
        context = _build_apparent_context(
            jd_tt,
            reader,
            apparent=apparent,
            nutation=nutation,
            vector_cache=_vector_cache,
        )
        built_context = True
        _vector_cache = context.vector_cache
        _store_apparent_context(
            reader,
            jd_tt=jd_tt,
            apparent=apparent,
            nutation=nutation,
            context=context,
        )
    elif context is not None:
        _vector_cache = context.vector_cache

    if built_context and context is not None and delta_t_policy is None:
        _store_planet_call_context(
            reader,
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            apparent=apparent,
            nutation=nutation,
            context=context,
        )

    if (
        context is not None
        and obliquity is None
        and apparent
        and aberration
        and grav_deflection
        and nutation
        and center == 'geocentric'
        and frame == 'ecliptic'
        and observer_lat is None
        and observer_lon is None
        and lst_deg is None
        and observer_elev_m == 0.0
    ):
        return _planet_at_default_apparent_geocentric_ecliptic(
            body,
            jd_tt=jd_tt,
            reader=reader,
            context=context,
        )

    return _planet_at_core(
        body,
        jd_ut,
        reader=reader,
        obliquity=obliquity,
        apparent=apparent,
        aberration=aberration,
        grav_deflection=grav_deflection,
        nutation=nutation,
        center=center,
        frame=frame,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
        jd_tt=jd_tt,
        _dpsi_deg=_dpsi_deg,
        _deps_deg=_deps_deg,
        _rot_mat=_rot_mat,
        _vector_cache=_vector_cache,
        _context=context,
    )


def sky_position_at(
    body: str,
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float = 0.0,
    reader: KernelReader | None = None,
    aberration: bool = True,
    grav_deflection: bool = True,
    nutation: bool = True,
    refraction: bool = True,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
    relative_humidity: float = 0.0,
    delta_t_policy: 'DeltaTPolicy | None' = None,
    _vector_cache: _VectorCache | None = None,
    _context: _ApparentContext | None = None,
) -> SkyPosition:
    """
    Compute the apparent topocentric equatorial and horizontal position of a body.

    Executes the full 8-step apparent-position pipeline: light-time correction
    → gravitational deflection → annual aberration → frame bias → precession
    → nutation → topocentric correction → atmospheric refraction, then
    projects to RA/Dec and Az/Alt.

    Individual correction stages can be disabled via the ``aberration``,
    ``grav_deflection``, ``nutation``, and ``refraction`` switches. The first
    three correspond to conventional "no aberration", "no gravitational
    deflection", and "no nutation" flag families respectively.

    Args:
        body: One of the ``Body.*`` string constants identifying the target body.
        jd_ut: Julian Day Number in Universal Time (UT1).
        observer_lat: Geographic latitude of the observer in degrees.
        observer_lon: Geographic longitude of the observer in degrees.
        observer_elev_m: Observer elevation above sea level in metres.
            Defaults to 0.0.
        reader: An open ``SpkReader`` instance. If ``None``, the module-level
            singleton returned by ``get_reader()`` is used.
        aberration: If ``True`` (default), apply annual aberration correction.
        grav_deflection: If ``True`` (default), apply gravitational deflection.
        nutation: If ``True`` (default), apply the nutation matrix. When
            ``False``, mean obliquity is used for the equatorial projection.
        refraction: If ``True`` (default), apply atmospheric refraction to
            convert the geometric altitude to the apparent observed altitude.
            Set to ``False`` for geometric/astrometric altitude output.
        pressure_mbar: Atmospheric pressure in millibars. Used only when
            ``refraction=True``. Defaults to 1013.25 mbar.
        temperature_c: Air temperature in degrees Celsius. Used only when
            ``refraction=True``. Defaults to 10.0 °C.
        relative_humidity: Relative humidity 0–1. Used only when
            ``refraction=True``. When non-zero, incorporates water-vapour
            partial pressure into the refractivity correction (Magnus
            approximation). Defaults to 0.0 (dry air).

    Returns:
        A ``SkyPosition`` vessel containing right ascension, declination,
        azimuth, altitude (all in degrees), and distance in kilometres.
        When ``refraction=True``, altitude is the apparent (observed) altitude.

    Raises:
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for the requested body.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if reader is None:
        reader = get_active_reader()
        if reader is None:
            raise MissingKernelError(
                "No planetary kernel is provided and no active reader context was found. "
                "Pass a reader explicitly or use the Moira facade."
            )

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month), delta_t_policy=delta_t_policy)
    context = _context or _build_apparent_context(
        jd_tt,
        reader,
        apparent=True,
        nutation=nutation,
        vector_cache=_vector_cache,
    )
    _vector_cache = context.vector_cache
    dpsi_deg, deps_deg = context.dpsi_deg, context.deps_deg
    obliquity = context.obliquity
    earth_ssb = context.earth_ssb
    earth_vel = context.earth_vel
    rot_mat = context.rot_mat

    # Step 1: Light-time correction
    xyz, _lt = apply_light_time(
        body,
        jd_tt,
        reader,
        earth_ssb,
        lambda body_, jd_tt_, reader_: _barycentric(body_, jd_tt_, reader_, _vector_cache),
    )

    # Step 2: Gravitational deflection (skip for Sun/Moon, or if disabled)
    # IAU SOFA LDBODY: Sun (~1.75" at limb) + Jupiter (~16 µas) + Saturn (~6 µas).
    # A body is never deflected by its own gravity.
    if grav_deflection and body not in (Body.SUN, Body.MOON):
        xyz = apply_deflection(xyz, _deflectors_for_body(body, jd_tt, reader, context))

    # Step 3: Annual aberration
    if aberration:
        xyz = apply_aberration(xyz, earth_vel)

    # Step 4: Frame bias
    xyz = apply_frame_bias(xyz)

    # Step 5+6: Precession + optional Nutation
    if rot_mat is not None:
        xyz = _apply_rotation_matrix(rot_mat, xyz)
    else:
        xyz = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz)
        if nutation:
            xyz = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz)

    # Step 7: Topocentric correction
    lst_deg = local_sidereal_time(jd_ut, observer_lon, dpsi_deg, obliquity)
    xyz = topocentric_correction(
        xyz, observer_lat, observer_lon, lst_deg, observer_elev_m, jd_ut=jd_ut
    )
    
    # Step 7b: Topocentric diurnal aberration (after parallax)
    xyz = apply_diurnal_aberration(
        xyz, observer_lat, observer_lon, lst_deg, observer_elev_m, jd_ut=jd_ut
    )

    ra_deg, dec_deg, dist = icrf_to_equatorial(xyz)
    az_deg, alt_deg = equatorial_to_horizontal(ra_deg, dec_deg, lst_deg, observer_lat)

    # Step 8: Atmospheric refraction (geometric → apparent altitude)
    if refraction:
        alt_deg = apply_refraction(
            alt_deg,
            pressure_mbar=pressure_mbar,
            temperature_c=temperature_c,
            relative_humidity=relative_humidity,
        )

    return SkyPosition(
        name=body,
        right_ascension=ra_deg,
        declination=dec_deg,
        azimuth=az_deg,
        altitude=alt_deg,
        distance=dist,
    )


# ---------------------------------------------------------------------------
# Public API: all bodies at once
# ---------------------------------------------------------------------------

def all_planets_at(
    jd_ut: float,
    bodies: list[str] | None = None,
    reader: KernelReader | None = None,
    apparent: bool = True,
    aberration: bool = True,
    grav_deflection: bool = True,
    nutation: bool = True,
    center: str = 'geocentric',
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    lst_deg: float | None = None,
    delta_t_policy: 'DeltaTPolicy | None' = None,
) -> dict[str, PlanetData]:
    """
    Compute geocentric (or topocentric) positions for multiple bodies at once.

    Obliquity is computed once and shared across all body computations, making
    this more efficient than calling ``planet_at()`` in a loop when many bodies
    are needed.

    All position-switch kwargs (``apparent``, ``aberration``, ``grav_deflection``,
    ``nutation``, ``center``) are forwarded to each ``planet_at()`` call and
    have the same semantics as documented there. ``frame='ecliptic'`` is always
    used; call ``planet_at()`` directly for ``frame='cartesian'`` output.

    Args:
        jd_ut: Julian Day Number in Universal Time (UT1).
        bodies: List of ``Body.*`` string constants to compute. Defaults to
            ``Body.ALL_PLANETS`` when ``None``.
        reader: An open ``SpkReader`` instance. If ``None``, the module-level
            singleton returned by ``get_reader()`` is used.
        apparent: If ``True`` (default), apply the full apparent-position pipeline.
        aberration: If ``True`` (default), apply annual aberration. Ignored when
            ``apparent=False``.
        grav_deflection: If ``True`` (default), apply gravitational deflection.
            Ignored when ``apparent=False``.
        nutation: If ``True`` (default), apply nutation matrix. Ignored when
            ``apparent=False``.
        center: ``'geocentric'`` (default) or ``'barycentric'``.
        observer_lat: Geographic latitude for topocentric correction.
        observer_lon: Geographic longitude for topocentric correction.
        observer_elev_m: Observer elevation in metres. Defaults to 0.0.
        lst_deg: Local Sidereal Time in degrees for topocentric correction.

    Returns:
        A ``dict`` mapping each body name (``str``) to its ``PlanetData``
        vessel. Keys match the entries in ``bodies``.

    Raises:
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for a requested body.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if bodies is None:
        bodies = Body.ALL_PLANETS
    if reader is None:
        reader = get_active_reader()
        if reader is None:
            raise MissingKernelError(
                "No planetary kernel is provided and no active reader context was found. "
                "Pass a reader explicitly or use the Moira facade."
            )

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month), delta_t_policy=delta_t_policy)

    native_results = _native_all_planets_admitted(
        jd_ut,
        list(bodies),
        reader=reader,
        jd_tt=jd_tt,
        apparent=apparent,
        aberration=aberration,
        grav_deflection=grav_deflection,
        nutation=nutation,
        center=center,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
        delta_t_policy=delta_t_policy,
    )
    if native_results is not None:
        return native_results

    vector_cache: _VectorCache = {}
    context = _build_apparent_context(
        jd_tt,
        reader,
        apparent=apparent,
        nutation=nutation,
        vector_cache=vector_cache,
    )
    results: dict[str, PlanetData] = {}
    for body in bodies:
        if body == Body.CHIRON:
            results[body] = _chiron_planet_data(jd_ut, reader)
            continue
        results[body] = _planet_at_core(  # type: ignore[assignment]
            body, jd_ut, reader=reader, obliquity=context.obliquity,
            apparent=apparent, aberration=aberration,
            grav_deflection=grav_deflection, nutation=nutation,
            center=center, frame='ecliptic',
            observer_lat=observer_lat, observer_lon=observer_lon,
            observer_elev_m=observer_elev_m, lst_deg=lst_deg,
            jd_tt=jd_tt,
            _dpsi_deg=context.dpsi_deg, _deps_deg=context.deps_deg, _rot_mat=context.rot_mat,
            _vector_cache=context.vector_cache, _context=context,
        )
    return results


# ---------------------------------------------------------------------------
# Public API: heliocentric positions
# ---------------------------------------------------------------------------

def heliocentric_planet_at(
    body: str,
    jd_ut: float,
    reader: KernelReader | None = None,
    _vector_cache: _VectorCache | None = None,
) -> HeliocentricData:
    """
    Compute the heliocentric ecliptic position of a body.

    Returns the position in the true-of-date ecliptic frame (precession and
    nutation applied), consistent with the geocentric frame used by
    ``planet_at()``. Speed is derived analytically from the JPL kernel
    velocity vector, not from a finite difference.

    Args:
        body: One of the ``Body.*`` string constants. Must not be ``Body.SUN``,
            which has no meaningful heliocentric position.
        jd_ut: Julian Day Number in Universal Time (UT1).
        reader: An open ``SpkReader`` instance. If ``None``, the module-level
            singleton returned by ``get_reader()`` is used.

    Returns:
        A ``HeliocentricData`` vessel containing heliocentric ecliptic
        longitude, latitude, distance, daily speed, retrograde flag, and
        derived sign data.

    Raises:
        ValueError: If ``body`` is ``Body.SUN`` or ``Body.MOON`` (neither has
            a meaningful heliocentric ecliptic position in this frame).
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for the requested body.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if body in (Body.SUN, Body.MOON):
        raise ValueError(
            f"heliocentric_planet_at: {body!r} does not have a meaningful "
            "heliocentric ecliptic position in this frame."
        )
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))

    # Fetch heliocentric position AND velocity from kernel state vectors —
    # no finite difference needed.
    body_bary_pos, body_bary_vel = _body_barycentric_state(body, jd_tt, reader, _vector_cache)
    sun_bary_pos, sun_bary_vel = _body_barycentric_state(Body.SUN, jd_tt, reader, _vector_cache)
    xyz_h = vec_sub(body_bary_pos, sun_bary_pos)
    vel_h = vec_sub(body_bary_vel, sun_bary_vel)

    # Rotate both vectors to true equatorial of date (precession + nutation).
    # Applying the same R to vel_h neglects dR/dt·xyz_h — the precession-rate
    # contribution is ~50″/century, negligible against orbital velocity.
    prec_mat = precession_matrix_equatorial(jd_tt)
    nut_mat  = nutation_matrix_equatorial(jd_tt)
    xyz_tod  = mat_vec_mul(nut_mat, mat_vec_mul(prec_mat, xyz_h))
    vel_tod  = mat_vec_mul(nut_mat, mat_vec_mul(prec_mat, vel_h))

    obliquity = true_obliquity(jd_tt)
    lon, lat, dist = icrf_to_ecliptic(xyz_tod, obliquity)
    speed = _longitude_rate(xyz_tod, vel_tod, obliquity)

    return HeliocentricData(
        name=body,
        longitude=lon,
        latitude=lat,
        distance=dist,
        speed=speed,
        retrograde=(speed < 0.0),
    )


def all_heliocentric_at(
    jd_ut: float,
    bodies: list[str] | None = None,
    reader: KernelReader | None = None,
) -> dict[str, HeliocentricData]:
    """
    Compute heliocentric positions for multiple bodies at once.

    Excludes ``Body.SUN`` and ``Body.MOON`` from the default body list, as
    neither has a meaningful heliocentric position in the DE441 frame.

    Args:
        jd_ut: Julian Day Number in Universal Time (UT1).
        bodies: List of ``Body.*`` string constants to compute. Defaults to
            all planets in ``Body.ALL_PLANETS`` except ``Body.SUN`` and
            ``Body.MOON``.
        reader: An open ``SpkReader`` instance. If ``None``, the module-level
            singleton returned by ``get_reader()`` is used.

    Returns:
        A ``dict`` mapping each body name (``str``) to its
        ``HeliocentricData`` vessel.

    Raises:
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for a requested body.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if bodies is None:
        bodies = [b for b in Body.ALL_PLANETS if b != Body.SUN and b != Body.MOON]
    if reader is None:
        reader = get_reader()

    vector_cache: _VectorCache = {}
    results: dict[str, HeliocentricData] = {}
    for body in bodies:
        results[body] = heliocentric_planet_at(
            body,
            jd_ut,
            reader=reader,
            _vector_cache=vector_cache,
        )
    return results


# ---------------------------------------------------------------------------
# Sun longitude (used by houses and nodes modules)
# ---------------------------------------------------------------------------

def sun_longitude(jd_ut: float, reader: KernelReader | None = None) -> float:
    """Return geocentric ecliptic longitude of the Sun (degrees, tropical)."""
    return planet_at(Body.SUN, jd_ut, reader=reader).longitude


# ---------------------------------------------------------------------------
# Utility: approximate year from JD (avoids importing julian for a circular dep)
# ---------------------------------------------------------------------------

def _body_barycentric(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> Vec3:
    """Return SSB position of any supported body (km, ICRF)."""
    if body == Body.SUN:
        cache_key = ("body_bary_pos", Body.SUN, jd_tt)
        if _vector_cache is not None and cache_key in _vector_cache:
            return _vector_cache[cache_key]  # type: ignore[return-value]
        result = reader.position(0, 10, jd_tt)
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result
    if body == Body.EARTH:
        return _earth_barycentric(jd_tt, reader, _vector_cache)
    return _barycentric(body, jd_tt, reader, _vector_cache)


def _body_barycentric_state(
    body: str,
    jd_tt: float,
    reader: KernelReader,
    _vector_cache: _VectorCache | None = None,
) -> tuple[Vec3, Vec3]:
    """Return SSB position and velocity of any supported body (km, km/day, ICRF)."""
    if body == Body.SUN:
        cache_key = ("body_bary_state", Body.SUN, jd_tt)
        if _vector_cache is not None and cache_key in _vector_cache:
            return _vector_cache[cache_key]  # type: ignore[return-value]
        result = reader.position_and_velocity(0, 10, jd_tt)
        if _vector_cache is not None:
            _vector_cache[cache_key] = result
        return result
    if body == Body.EARTH:
        return _earth_barycentric_state(jd_tt, reader, _vector_cache)
    return _barycentric_state(body, jd_tt, reader, _vector_cache)


def _bisect(func, t0: float, t1: float, iterations: int = 52) -> float:
    """Bisect a bracketed root of func over [t0, t1].  f(t0) and f(t1) must differ in sign."""
    f0 = func(t0)
    for _ in range(iterations):
        tm = (t0 + t1) / 2.0
        fm = func(tm)
        if f0 * fm <= 0.0:
            t1 = tm
        else:
            t0 = tm
            f0 = fm
    return (t0 + t1) / 2.0


# ---------------------------------------------------------------------------
# Phase 2: planet_relative_to
# ---------------------------------------------------------------------------

def planet_relative_to(
    body: str,
    center_body: str,
    jd_ut: float,
    reader: KernelReader | None = None,
    _vector_cache: _VectorCache | None = None,
) -> PlanetData:
    """
    Compute the position of ``body`` as seen from ``center_body``.

    Methodology (independently derived):
        The relative ICRF position vector is the difference of the two bodies'
        DE441 SPK barycentric position vectors:

            r_rel = r_body(SSB) − r_center(SSB)

        This is the standard reduction described in Seidelmann (ed.),
        *Explanatory Supplement to the Astronomical Almanac* (1992), §3.26.
        The ICRF vector is then transformed to the true-of-date ecliptic frame
        via the IAU 2000A/2006 precession–nutation matrix stack
        (implemented in ``icrf_to_true_ecliptic``).  Longitude rate (speed)
        is estimated with a centred ±0.5-day finite difference
        (Meeus, *Astronomical Algorithms* 2nd ed., §33).

    Use this when you need the ecliptic position of a body relative to a
    centre other than Earth
    (e.g. Mars as seen from Jupiter, or any body as seen heliocentrically by
    passing ``Body.SUN`` as ``center_body``).

    For heliocentric positions of a single body, prefer
    :func:`heliocentric_planet_at`, which produces a :class:`HeliocentricData`
    vessel.  This function returns a :class:`PlanetData` vessel with the same
    fields as :func:`planet_at` but measured from ``center_body``.

    The position is geometric (no light-time or aberration corrections).  The
    ecliptic frame is the true-of-date frame (precession and nutation applied).

    Args:
        body: The body whose position is requested.  Any ``Body.*`` constant
            except ``Body.SUN`` when ``center_body`` is also ``Body.SUN``.
        center_body: The centre of the reference frame.  Any ``Body.*``
            constant, including ``Body.SUN`` for heliocentric positions.
        jd_ut: Julian Day in Universal Time (UT1).
        reader: Open :class:`SpkReader`.  Uses the module-level singleton if
            ``None``.

    Returns:
        A :class:`PlanetData` vessel.  ``distance`` is the separation between
        ``body`` and ``center_body`` in km.  ``speed`` is the instantaneous
        rate of change of relative longitude (degrees/day), computed via a
        ±0.5-day finite difference.

    Raises:
        ValueError: If ``body == center_body``.
        FileNotFoundError: If the DE441 kernel is not found.
    """
    if body == center_body:
        raise ValueError(
            f"planet_relative_to: body and center_body must be different ({body!r})"
        )
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))

    def _rel_vec(jd_tt_: float) -> Vec3:
        b_bary = _body_barycentric(body, jd_tt_, reader, _vector_cache)
        c_bary = _body_barycentric(center_body, jd_tt_, reader, _vector_cache)
        return vec_sub(b_bary, c_bary)

    xyz = _rel_vec(jd_tt)
    lon, lat, dist = icrf_to_true_ecliptic(jd_tt, xyz)

    year_p, month_p, *_ = _approx_year(jd_ut + 0.5)
    year_m, month_m, *_ = _approx_year(jd_ut - 0.5)
    jd_tt_p = ut_to_tt(jd_ut + 0.5, decimal_year(year_p, month_p))
    jd_tt_m = ut_to_tt(jd_ut - 0.5, decimal_year(year_m, month_m))
    lon_p, _, _ = icrf_to_true_ecliptic(jd_tt_p, _rel_vec(jd_tt_p))
    lon_m, _, _ = icrf_to_true_ecliptic(jd_tt_m, _rel_vec(jd_tt_m))
    raw_speed = (lon_p - lon_m) % 360.0
    if raw_speed > 180.0:
        raw_speed -= 360.0

    return PlanetData(
        name=body,
        longitude=lon,
        latitude=lat,
        distance=dist,
        speed=raw_speed,
        retrograde=(raw_speed < 0.0),
    )


# ---------------------------------------------------------------------------
# Phase 2: next_heliocentric_transit
# ---------------------------------------------------------------------------

def next_heliocentric_transit(
    body: str,
    target_lon: float,
    jd_start: float,
    reader: KernelReader | None = None,
    max_days: float = 400.0,
) -> float:
    """
    Find the next time ``body``'s heliocentric ecliptic longitude equals
    ``target_lon``.

    Methodology (independently derived):
        The heliocentric longitude at each epoch is computed from the body–Sun
        ICRF barycentric position difference rotated via ``icrf_to_true_ecliptic``
        (IAU 2000A/2006 precession–nutation).  The search strategy follows the
        longitude-crossing scan approach described in Meeus,
        *Astronomical Algorithms* 2nd ed., §33:

            1. Estimate the orbital angular speed from consecutive epochs to
               select an adaptive step advancing ~1.5° per iteration.
            2. Scan forward detecting sign changes in the phase function:
               ``φ(t) = (lon(t) − target + 180) mod 360 − 180``.
            3. Refine the crossing with 52-iteration deterministic bisection.

        The signed-angle formulation handles the 0°/360° wraparound without
        special cases.

    This is a heliocentric longitude crossing search over UT input epochs.

    The search scans forward from ``jd_start`` in steps proportional to the
    body's current orbital speed, then refines the crossing with 52-iteration
    bisection.  ``max_days`` limits the scan to avoid infinite loops for very
    slow bodies; increase it for Uranus/Neptune/Pluto.

    Args:
        body: A ``Body.*`` constant (not ``Body.SUN`` or ``Body.MOON``).
        target_lon: Heliocentric ecliptic longitude to find (degrees; need
            not be in [0, 360)).
        jd_start: Julian Day (UT1) to begin searching from.
        reader: Open :class:`SpkReader`.  Uses the module-level singleton if
            ``None``.
        max_days: Maximum days to search forward.  Default 400 covers all
            inner planets and Mars comfortably; set higher for outer planets
            (e.g. 20000 for Neptune).

    Returns:
        Julian Day (UT1) of the next crossing.

    Raises:
        ValueError: If ``body`` is ``Body.SUN``.
        ValueError: If no crossing is found within ``max_days``.
        FileNotFoundError: If the DE441 kernel is not found.
    """
    if body == Body.SUN:
        raise ValueError("next_heliocentric_transit: Body.SUN has no heliocentric longitude.")
    if reader is None:
        reader = get_reader()

    target = target_lon % 360.0

    def _helio_lon(jd_ut: float) -> float:
        yr, mo, *_ = _approx_year(jd_ut)
        jd_tt = ut_to_tt(jd_ut, decimal_year(yr, mo))
        body_bary = _barycentric(body, jd_tt, reader)
        sun_bary  = reader.position(0, 10, jd_tt)
        rel = vec_sub(body_bary, sun_bary)
        lon, _, _ = icrf_to_true_ecliptic(jd_tt, rel)
        return lon

    def _phase(jd_ut: float) -> float:
        """Signed angle in (-180, 180]: negative = approaching, positive = past."""
        lon = _helio_lon(jd_ut)
        d = (lon - target + 180.0) % 360.0 - 180.0
        return d

    # Estimate orbital speed to choose a safe step
    lon0 = _helio_lon(jd_start)
    lon1 = _helio_lon(jd_start + 1.0)
    speed_deg_per_day = (lon1 - lon0 + 360.0) % 360.0  # always positive (direct)
    if speed_deg_per_day < 1e-6:
        speed_deg_per_day = 1e-6
    step = max(0.25, 1.5 / speed_deg_per_day)  # cover 1.5° per step

    f_prev = _phase(jd_start)
    t = jd_start

    while t < jd_start + max_days:
        t_next = min(t + step, jd_start + max_days)
        f_next = _phase(t_next)
        if f_prev < 0.0 and f_next >= 0.0:
            return _bisect(_phase, t, t_next)
        f_prev = f_next
        t = t_next

    raise ValueError(
        f"next_heliocentric_transit: {body!r} did not reach {target_lon:.2f}° "
        f"within {max_days} days of JD {jd_start:.1f}."
    )


def _approx_year(jd: float) -> tuple[int, int, int, float]:
    """Fast approximate calendar date from JD — used only for ΔT lookup.

    .. deprecated::
        Import ``approx_year`` (the public alias) instead of this
        underscore-prefixed name.  The two are identical; ``_approx_year``
        is retained for internal call sites and will not be removed.
    """
    jd = jd + 0.5
    z = int(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day   = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year  = c - 4716 if month > 2 else c - 4715
    return year, month, day, f * 24.0


#: Public alias for :func:`_approx_year`.  External modules should import
#: this name rather than the underscore-prefixed internal name.
approx_year = _approx_year
