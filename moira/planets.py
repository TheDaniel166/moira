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

import math
from dataclasses import dataclass, field

from .constants import (
    Body, NAIF, NAIF_ROUTES, EARTH_ROUTE,
    DEG2RAD, RAD2DEG, sign_of,
)
from .coordinates import (
    Vec3, vec_add, vec_sub, vec_norm, mat_vec_mul, mat_mul,
    icrf_to_ecliptic, icrf_to_equatorial, equatorial_to_horizontal,
    normalize_degrees, precession_matrix_equatorial, nutation_matrix_equatorial,
    icrf_to_true_ecliptic,
)
from .obliquity import mean_obliquity, true_obliquity, nutation as _nutation
from .julian import ut_to_tt, centuries_from_j2000, local_sidereal_time, decimal_year, DeltaTPolicy
from .spk_reader import get_reader, SpkReader
from .corrections import (
    apply_light_time, apply_aberration, apply_deflection, apply_frame_bias,
    topocentric_correction, C_KM_PER_DAY,
)
from .precession import general_precession_in_longitude

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanetData:
    """
    RITE: The Planetary Data Vessel

    THEOREM: PlanetData serves as the immutable result vessel for a single
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
    speed:          float          # daily motion in longitude, degrees/day
    retrograde:     bool           # True when speed < 0
    is_topocentric: bool = False   # True when topocentric parallax has been applied
    sign:           str  = field(init=False)
    sign_symbol:    str  = field(init=False)
    sign_degree:    float= field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

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
        return self.distance / 149597870.7

    def __repr__(self) -> str:
        r = "℞" if self.retrograde else ""
        deg, m, s = self.longitude_dms
        return (f"{self.name}: {deg}°{m:02d}′{s:04.1f}″ {self.sign} {self.sign_symbol}"
                f"  ({self.longitude:.4f}°) {r}  Δ={self.speed:+.4f}°/d")


@dataclass(slots=True)
class SkyPosition:
    """
    RITE: The Sky Position Vessel

    THEOREM: SkyPosition serves as the immutable result vessel for a
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

@dataclass(slots=True)
class HeliocentricData:
    """
    RITE: The Heliocentric Data Vessel

    THEOREM: HeliocentricData serves as the immutable result vessel for a
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
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    @property
    def distance_au(self) -> float:
        return self.distance / 149597870.7

    def __repr__(self) -> str:
        r = "℞" if self.retrograde else ""
        return (f"[helio] {self.name}: {self.longitude:.4f}°  "
                f"{self.sign} {self.sign_degree:.2f}  "
                f"r={self.distance_au:.4f} AU  {r}")


@dataclass(slots=True)
class CartesianPosition:
    """
    RITE: The Cartesian Position Vessel

    THEOREM: CartesianPosition is the immutable result vessel for a planetary
        position expressed as rectangular ICRF-of-date coordinates (km) rather
        than ecliptic longitude/latitude.

    RITE OF PURPOSE:
        CartesianPosition is returned by planet_at(..., frame='cartesian').
        It exists so callers who need raw rectangular vectors for orbital
        mechanics, numerical integration, or Swiss FLG_XYZ migration can
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

def _barycentric(
    body: str,
    jd_tt: float,
    reader: SpkReader,
) -> Vec3:
    """
    Return the Solar System Barycentric (SSB) position of a body (km, ICRF).
    """
    if body == Body.MOON:
        # Moon relative to EMB + EMB relative to SSB
        emb_moon = reader.position(3, 301, jd_tt)
        ssb_emb  = reader.position(0, 3, jd_tt)
        return vec_add(ssb_emb, emb_moon)

    # All other bodies: chain from SSB
    route = NAIF_ROUTES[body]
    x = y = z = 0.0
    for center, target in route:
        px, py, pz = reader.position(center, target, jd_tt)
        x += px; y += py; z += pz
    return (x, y, z)


def _barycentric_state(
    body: str,
    jd_tt: float,
    reader: SpkReader,
) -> tuple[Vec3, Vec3]:
    """
    Return Solar System Barycentric position and velocity of a body (km, km/day).
    """
    route = NAIF_ROUTES[body]

    if body == Body.MOON:
        return reader.position_and_velocity(3, 301, jd_tt)

    x = y = z = 0.0
    vx = vy = vz = 0.0
    for center, target in route:
        pos, vel = reader.position_and_velocity(center, target, jd_tt)
        x += pos[0]; y += pos[1]; z += pos[2]
        vx += vel[0]; vy += vel[1]; vz += vel[2]
    return (x, y, z), (vx, vy, vz)


def _earth_barycentric(jd_tt: float, reader: SpkReader) -> Vec3:
    """Return Earth's barycentric position (km, ICRF)."""
    ssb_emb = reader.position(0, 3, jd_tt)
    emb_earth = reader.position(3, 399, jd_tt)
    return vec_add(ssb_emb, emb_earth)


def _earth_barycentric_state(jd_tt: float, reader: SpkReader) -> tuple[Vec3, Vec3]:
    """Return Earth's barycentric position and velocity (km, km/day, ICRF)."""
    ssb_emb_pos, ssb_emb_vel = reader.position_and_velocity(0, 3, jd_tt)
    emb_earth_pos, emb_earth_vel = reader.position_and_velocity(3, 399, jd_tt)
    return (
        vec_add(ssb_emb_pos, emb_earth_pos),
        vec_add(ssb_emb_vel, emb_earth_vel),
    )


def _geocentric(
    body: str,
    jd_tt: float,
    reader: SpkReader,
) -> Vec3:
    """
    Return geocentric ICRF rectangular position of a body (km).
    """
    earth = _earth_barycentric(jd_tt, reader)

    if body == Body.MOON:
        # Moon position from EMB; Earth position from EMB
        emb_moon  = reader.position(3, 301, jd_tt)
        emb_earth = reader.position(3, 399, jd_tt)
        # Geocentric Moon = EMB→Moon − EMB→Earth
        return vec_sub(emb_moon, emb_earth)

    if body == Body.SUN:
        ssb_sun = reader.position(0, 10, jd_tt)
        return vec_sub(ssb_sun, earth)

    # Planets: chain from SSB, then subtract Earth
    bary = _barycentric(body, jd_tt, reader)
    return vec_sub(bary, earth)


def _geocentric_state(
    body: str,
    jd_tt: float,
    reader: SpkReader,
) -> tuple[Vec3, Vec3]:
    """
    Return geocentric ICRF rectangular position and velocity of a body.
    """
    earth_pos, earth_vel = _earth_barycentric_state(jd_tt, reader)

    if body == Body.MOON:
        emb_moon_pos, emb_moon_vel = reader.position_and_velocity(3, 301, jd_tt)
        emb_earth_pos, emb_earth_vel = reader.position_and_velocity(3, 399, jd_tt)
        return (
            vec_sub(emb_moon_pos, emb_earth_pos),
            vec_sub(emb_moon_vel, emb_earth_vel),
        )

    if body == Body.SUN:
        sun_pos, sun_vel = reader.position_and_velocity(0, 10, jd_tt)
        return (
            vec_sub(sun_pos, earth_pos),
            vec_sub(sun_vel, earth_vel),
        )

    bary_pos, bary_vel = _barycentric_state(body, jd_tt, reader)
    return (
        vec_sub(bary_pos, earth_pos),
        vec_sub(bary_vel, earth_vel),
    )


def _earth_velocity(jd_tt: float, reader: SpkReader) -> Vec3:
    """
    Earth's barycentric velocity in km/day (ICRF).
    """
    _, earth_vel = _earth_barycentric_state(jd_tt, reader)
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
# Public API: single body
# ---------------------------------------------------------------------------

def planet_at(
    body: str,
    jd_ut: float,
    reader: SpkReader | None = None,
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
            ICRF-of-date coordinates (km).
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
        when ``frame='cartesian'``.

    Raises:
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for the requested body.
        ValueError: If ``center`` or ``frame`` is not a recognised string.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if center not in ('geocentric', 'barycentric'):
        raise ValueError(f"center must be 'geocentric' or 'barycentric', got {center!r}")
    if frame not in ('ecliptic', 'cartesian'):
        raise ValueError(f"frame must be 'ecliptic' or 'cartesian', got {frame!r}")

    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    if jd_tt is None:
        jd_tt = ut_to_tt(jd_ut, decimal_year(year, month), delta_t_policy=delta_t_policy)

    dpsi_deg, deps_deg = _nutation(jd_tt)
    if obliquity is None:
        obliquity = mean_obliquity(jd_tt) + (deps_deg if nutation else 0.0)

    if apparent:
        earth_ssb = _earth_barycentric(jd_tt, reader)

        # 1. Light-time: Body(t-lt) − Earth(t) → geocentric vector [ICRF]
        xyz_geo, _lt = apply_light_time(body, jd_tt, reader, earth_ssb, _barycentric)

        if center == 'barycentric':
            # Un-subtract Earth to recover body_bary(t-lt).
            # Aberration and deflection are observer-centric terms and are not
            # applied for barycentric output.
            xyz0 = vec_add(xyz_geo, earth_ssb)
        else:
            xyz0 = xyz_geo
            # 2. Gravitational deflection (near Sun) [ICRF]
            if grav_deflection and body not in (Body.SUN, Body.MOON):
                sun_geocentric = _geocentric(Body.SUN, jd_tt, reader)
                xyz0 = apply_deflection(xyz0, sun_geocentric, earth_ssb)

            # 3. Annual aberration [ICRF]
            if aberration:
                xyz0 = apply_aberration(xyz0, _earth_velocity(jd_tt, reader))

        # 4. Frame bias [ICRF → Mean Equator/Equinox J2000]
        xyz0 = apply_frame_bias(xyz0)

        # 5. Precession [J2000 Mean → Mean Equator of date]
        xyz0 = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz0)

        # 6. Nutation [Mean → True Equator of date]
        if nutation:
            xyz0 = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz0)

    else:
        if center == 'barycentric':
            xyz0 = _barycentric(body, jd_tt, reader)
        else:
            xyz0 = _geocentric(body, jd_tt, reader)

    # 7. Topocentric correction (geocentric only)
    if (
        center == 'geocentric'
        and observer_lat is not None
        and observer_lon is not None
        and lst_deg is not None
    ):
        xyz0 = topocentric_correction(
            xyz0, observer_lat, observer_lon, lst_deg, observer_elev_m
        )

    if frame == 'cartesian':
        return CartesianPosition(name=body, x=xyz0[0], y=xyz0[1], z=xyz0[2], center=center)

    # 8. Convert to Ecliptic [True Equator of date → True Ecliptic of date]
    lon, lat, dist = icrf_to_ecliptic(xyz0, obliquity)

    # 9. Speed calculation (astrometric geocentric rate)
    xyz_rate, vel_rate = _geocentric_state(body, jd_tt, reader)
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


def sky_position_at(
    body: str,
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    aberration: bool = True,
    grav_deflection: bool = True,
    nutation: bool = True,
    delta_t_policy: 'DeltaTPolicy | None' = None,
) -> SkyPosition:
    """
    Compute the apparent topocentric equatorial and horizontal position of a body.

    Executes the full 7-step apparent-position pipeline: light-time correction
    → gravitational deflection → annual aberration → frame bias → precession
    → nutation → topocentric correction, then projects to RA/Dec and Az/Alt.

    Individual correction stages can be disabled via the ``aberration``,
    ``grav_deflection``, and ``nutation`` switches. These correspond to the
    Swiss Ephemeris ``FLG_NOABERR``, ``FLG_NOGDEFL``, and ``FLG_NONUT``
    flags respectively.

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

    Returns:
        A ``SkyPosition`` vessel containing right ascension, declination,
        azimuth, altitude (all in degrees), and distance in kilometres.

    Raises:
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for the requested body.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month), delta_t_policy=delta_t_policy)
    dpsi_deg, deps_deg = _nutation(jd_tt)
    obliquity = mean_obliquity(jd_tt) + (deps_deg if nutation else 0.0)
    earth_ssb = _earth_barycentric(jd_tt, reader)

    # Step 1: Light-time correction
    xyz, _lt = apply_light_time(body, jd_tt, reader, earth_ssb, _barycentric)

    # Step 2: Gravitational deflection (skip for Sun/Moon, or if disabled)
    if grav_deflection and body not in (Body.SUN, Body.MOON):
        sun_geo = _geocentric(Body.SUN, jd_tt, reader)
        xyz = apply_deflection(xyz, sun_geo, earth_ssb)

    # Step 3: Annual aberration
    if aberration:
        xyz = apply_aberration(xyz, _earth_velocity(jd_tt, reader))

    # Step 4: Frame bias
    xyz = apply_frame_bias(xyz)

    # Step 5: Precession (J2000 mean → mean equator of date)
    xyz = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz)

    # Step 6: Nutation (mean equator of date → true equator of date)
    if nutation:
        xyz = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz)

    # Step 7: Topocentric correction
    lst_deg = local_sidereal_time(jd_ut, observer_lon, dpsi_deg, obliquity)
    xyz = topocentric_correction(xyz, observer_lat, observer_lon, lst_deg, observer_elev_m)

    ra_deg, dec_deg, dist = icrf_to_equatorial(xyz)
    az_deg, alt_deg = equatorial_to_horizontal(ra_deg, dec_deg, lst_deg, observer_lat)
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
    reader: SpkReader | None = None,
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
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month), delta_t_policy=delta_t_policy)
    _, deps_deg = _nutation(jd_tt)
    obliquity = mean_obliquity(jd_tt) + (deps_deg if nutation else 0.0)

    results: dict[str, PlanetData] = {}
    for body in bodies:
        results[body] = planet_at(  # type: ignore[assignment]
            body, jd_ut, reader=reader, obliquity=obliquity,
            apparent=apparent, aberration=aberration,
            grav_deflection=grav_deflection, nutation=nutation,
            center=center, frame='ecliptic',
            observer_lat=observer_lat, observer_lon=observer_lon,
            observer_elev_m=observer_elev_m, lst_deg=lst_deg,
            delta_t_policy=delta_t_policy,
        )
    return results


# ---------------------------------------------------------------------------
# Public API: heliocentric positions
# ---------------------------------------------------------------------------

def heliocentric_planet_at(
    body: str,
    jd_ut: float,
    reader: SpkReader | None = None,
) -> HeliocentricData:
    """
    Compute the heliocentric ecliptic position of a body.

    Returns the position in the true-of-date ecliptic frame (precession and
    nutation applied), consistent with the geocentric frame used by
    ``planet_at()``. Speed is derived via a ±0.5-day finite difference with
    360° wraparound handling.

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
        ValueError: If ``body`` is ``Body.SUN``.
        FileNotFoundError: If the DE441 kernel has not been initialised and
            the default kernel path does not exist.
        KeyError: If the SPK kernel contains no segment for the requested body.

    Side effects:
        None. May initialise the module-level ``SpkReader`` singleton on first
        call if ``reader`` is ``None`` and no singleton exists yet.
    """
    if body == Body.SUN:
        raise ValueError("The Sun cannot have a heliocentric position.")
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))

    def _helio_vec(jd_tt_: float) -> Vec3:
        """Heliocentric ICRF vector of body at jd_tt_ (km)."""
        body_bary = _barycentric(body, jd_tt_, reader)
        sun_bary  = reader.position(0, 10, jd_tt_)
        return vec_sub(body_bary, sun_bary)

    # Primary position
    xyz = _helio_vec(jd_tt)
    lon, lat, dist = icrf_to_true_ecliptic(jd_tt, xyz)

    # Speed: finite difference over ±0.5 day
    year_p, *_ = _approx_year(jd_ut + 0.5)
    year_m, *_ = _approx_year(jd_ut - 0.5)
    jd_tt_p = ut_to_tt(jd_ut + 0.5, year_p)
    jd_tt_m = ut_to_tt(jd_ut - 0.5, year_m)
    lon_p, _, _ = icrf_to_true_ecliptic(jd_tt_p, _helio_vec(jd_tt_p))
    lon_m, _, _ = icrf_to_true_ecliptic(jd_tt_m, _helio_vec(jd_tt_m))
    # Handle wraparound
    raw_speed = (lon_p - lon_m) % 360.0
    if raw_speed > 180.0:
        raw_speed -= 360.0
    speed = raw_speed / 1.0

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
    reader: SpkReader | None = None,
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

    results: dict[str, HeliocentricData] = {}
    for body in bodies:
        results[body] = heliocentric_planet_at(body, jd_ut, reader=reader)
    return results


# ---------------------------------------------------------------------------
# Sun longitude (used by houses and nodes modules)
# ---------------------------------------------------------------------------

def sun_longitude(jd_ut: float, reader: SpkReader | None = None) -> float:
    """Return geocentric ecliptic longitude of the Sun (degrees, tropical)."""
    return planet_at(Body.SUN, jd_ut, reader=reader).longitude


# ---------------------------------------------------------------------------
# Utility: approximate year from JD (avoids importing julian for a circular dep)
# ---------------------------------------------------------------------------

def _body_barycentric(body: str, jd_tt: float, reader: SpkReader) -> Vec3:
    """Return SSB position of any supported body (km, ICRF)."""
    if body == Body.SUN:
        return reader.position(0, 10, jd_tt)
    if body == Body.EARTH:
        return _earth_barycentric(jd_tt, reader)
    return _barycentric(body, jd_tt, reader)


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
# Phase 2: planet_relative_to — calc_pctr analogue
# ---------------------------------------------------------------------------

def planet_relative_to(
    body: str,
    center_body: str,
    jd_ut: float,
    reader: SpkReader | None = None,
) -> PlanetData:
    """
    Compute the position of ``body`` as seen from ``center_body``.

    Equivalent to Swiss Ephemeris ``swe_calc_pctr``.  Use this when you need
    the ecliptic position of a body relative to a centre other than Earth
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
        b_bary = _body_barycentric(body, jd_tt_, reader)
        c_bary = _body_barycentric(center_body, jd_tt_, reader)
        return vec_sub(b_bary, c_bary)

    xyz = _rel_vec(jd_tt)
    lon, lat, dist = icrf_to_true_ecliptic(jd_tt, xyz)

    year_p, *_ = _approx_year(jd_ut + 0.5)
    year_m, *_ = _approx_year(jd_ut - 0.5)
    jd_tt_p = ut_to_tt(jd_ut + 0.5, year_p)
    jd_tt_m = ut_to_tt(jd_ut - 0.5, year_m)
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
# Phase 2: next_heliocentric_transit — helio_cross analogue
# ---------------------------------------------------------------------------

def next_heliocentric_transit(
    body: str,
    target_lon: float,
    jd_start: float,
    reader: SpkReader | None = None,
    max_days: float = 400.0,
) -> float:
    """
    Find the next time ``body``'s heliocentric ecliptic longitude equals
    ``target_lon``.

    Equivalent to Swiss Ephemeris ``swe_helio_cross`` / ``swe_helio_cross_ut``.

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
    """Fast approximate calendar date from JD — used only for ΔT lookup."""
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
