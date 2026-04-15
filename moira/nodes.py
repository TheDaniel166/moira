"""
Moira — nodes.py
The Oracle of Lunar Nodes: governs computation of the Moon's true and mean
ascending node, and Black Moon Lilith (mean and true apogee).

Boundary: owns the full pipeline from Julian Day to NodeData result vessels
for the lunar nodes and Lilith points. Delegates kernel I/O to spk_reader,
coordinate transforms to coordinates, and time conversion to julian. Does
not own house calculations, aspect detection, or any display formatting.

Public surface:
    NodeData, mean_node(), true_node(), mean_lilith(), true_lilith(),
    next_moon_node_crossing()

Import-time side effects: None

External dependency assumptions:
    - jplephem must be importable (via spk_reader) for true_node() and true_lilith().
    - DE441 kernel must exist at kernels/de441.bsp (accessed lazily on first call).
"""

import math

__all__ = [
    "NodeData",
    "mean_node",
    "true_node",
    "mean_lilith",
    "true_lilith",
    "next_moon_node_crossing",
    "NodesAndApsides",
    "nodes_and_apsides_at",
]
from dataclasses import dataclass, field

from .constants import DEG2RAD, RAD2DEG, sign_of
from .julian import centuries_from_j2000, ut_to_tt, decimal_year
from .coordinates import Vec3, vec_sub, icrf_to_ecliptic, normalize_degrees, mat_vec_mul, precession_matrix_equatorial, nutation_matrix_equatorial
from .obliquity import mean_obliquity, nutation
from .planets import _earth_barycentric, approx_year as _approx_year
from .spk_reader import get_reader, SpkReader


@dataclass(slots=True)
class NodeData:
    """
    RITE: The Node Data Vessel — immutable result container for a lunar node or Lilith point.

    THEOREM: Serves as the terminal result vessel carrying the tropical longitude, zodiac
    sign decomposition, and daily motion speed for a single lunar node or Lilith computation.

    RITE OF PURPOSE:
        NodeData is the canonical output type for every function in this module. It
        decouples the computation pipeline from any downstream consumer by providing a
        stable, self-describing result vessel. Without it, callers would receive raw
        floats with no sign context and no speed information.

    LAW OF OPERATION:
        Responsibilities:
            - Store the computed tropical longitude of a node or Lilith point.
            - Derive and expose the zodiac sign, sign symbol, and within-sign degree
              via __post_init__ on construction.
            - Carry the daily motion speed (degrees/day) of the point.
        Non-responsibilities:
            - Does not perform any astronomical computation.
            - Does not validate that longitude is within [0, 360).
            - Does not own or cache any kernel state.
        Dependencies:
            - sign_of() from moira.constants must be importable at construction time.
        Structural invariants:
            - sign, sign_symbol, and sign_degree are always set after __post_init__.
            - longitude is stored as provided; callers are responsible for normalisation.
        Behavioral invariants:
            - __repr__ always returns a human-readable DMS string with sign symbol.
        Failure behavior:
            - If sign_of() raises, __post_init__ propagates the exception; no partial
              state is left on the object.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.nodes.NodeData",
      "risk": "high",
      "api": {
        "frozen": ["name", "longitude", "sign", "sign_symbol", "sign_degree", "speed"],
        "internal": ["__post_init__", "__repr__"]
      },
      "state": {"mutable": false, "owners": ["NodeData"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    longitude:   float
    sign:        str  = field(init=False)
    sign_symbol: str  = field(init=False)
    sign_degree: float= field(init=False)
    speed:       float = 0.0

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    def __repr__(self) -> str:
        d = int(self.sign_degree)
        m = int((self.sign_degree - d) * 60)
        return f"{self.name}: {d}°{m:02d}′ {self.sign} {self.sign_symbol}  ({self.longitude:.4f}°)"


# ---------------------------------------------------------------------------
# Mean Node — Meeus analytical formula (Ch.25)
# ---------------------------------------------------------------------------

def mean_node(jd_ut: float) -> NodeData:
    """
    Governs computation of the mean ascending node of the Moon using the
    Meeus analytical formula (Astronomical Algorithms, Ch. 25).

    Converts UT to TT internally; no external kernel is required. The result
    is accurate to approximately 10 arcminutes over several centuries.

    Args:
        jd_ut: Julian Day in Universal Time (UT1).

    Returns:
        NodeData vessel with name="Mean Node", tropical longitude in degrees
        [0, 360), and speed ≈ −0.05295°/day (retrograde).

    Raises:
        No exceptions under normal operation; propagates any exception raised
        by ut_to_tt() or centuries_from_j2000() on invalid input.

    Side effects:
        None.
    """
    year, month, *_ = _approx_year(jd_ut)
    jd_tt    = ut_to_tt(jd_ut, decimal_year(year, month))
    T = centuries_from_j2000(jd_tt)

    lon = (125.04452
           - 1934.136261 * T
           + 0.0020708   * T**2
           + T**3 / 450000.0) % 360.0

    # Speed: derivative ≈ −1934.136261 / 36525 ≈ −0.05295°/day
    speed = -1934.136261 / 36525.0

    return NodeData(name="Mean Node", longitude=lon % 360.0, speed=speed)


# ---------------------------------------------------------------------------
# True Node — computed geometrically from DE441
# ---------------------------------------------------------------------------

_TRUE_NODE_STEP = 0.01   # days; ~14 minutes, enough to track node direction


def true_node(
    jd_ut: float,
    reader: SpkReader | None = None,
    jd_tt: float | None = None,
) -> NodeData:
    """
    Governs computation of the true (geometric) ascending node of the Moon's
    orbit using DE441 barycentric state vectors.

    Method: samples the Moon's geocentric ICRF position at t − step and
    t + step (step = 0.01 days ≈ 14 minutes), forms the orbital plane normal
    via the cross product, then intersects that plane with the ecliptic to
    obtain the ascending node direction. The result is rotated through the
    precession and nutation matrices to yield a tropical ecliptic longitude.

    Args:
        jd_ut: Julian Day in Universal Time (UT1).
        reader: Optional pre-opened SpkReader. If None, the module-level
            singleton from get_reader() is used (lazy kernel open on first
            call).
        jd_tt: Optional pre-computed Julian Day in Terrestrial Time. If None,
            it is derived from jd_ut internally.

    Returns:
        NodeData vessel with name="True Node", tropical longitude in degrees
        [0, 360), and speed set to the mean node constant −1934.136261/36525
        ≈ −0.05295°/day.  This is a fixed approximation — the true node speed
        is not derived from the geometric computation.  Callers consuming
        ``speed`` for dynamic modelling (transit timing, direction rates) should
        compute it independently via finite difference of successive
        ``true_node()`` calls.

    Raises:
        FileNotFoundError: if the DE441 kernel cannot be found and reader is
            None (raised inside get_reader()).
        ValueError: propagated from SpkReader if the requested body or epoch
            is outside the kernel's coverage.

    Side effects:
        None. The SpkReader kernel file is opened lazily on first call if
        reader is None, but that side effect belongs to get_reader().
    """
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    if jd_tt is None:
        jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))
    dpsi_deg, deps_deg = nutation(jd_tt)
    obliquity = mean_obliquity(jd_tt) + deps_deg
    eps = obliquity * DEG2RAD

    def moon_geo(jd: float) -> Vec3:
        earth = _earth_barycentric(jd, reader)
        emb_moon  = reader.position(3, 301, jd)
        emb_earth = reader.position(3, 399, jd)
        return vec_sub(emb_moon, emb_earth)

    r1 = moon_geo(jd_tt - _TRUE_NODE_STEP)
    r2 = moon_geo(jd_tt + _TRUE_NODE_STEP)

    # Orbital plane normal = r1 × r2
    nx = r1[1]*r2[2] - r1[2]*r2[1]
    ny = r1[2]*r2[0] - r1[0]*r2[2]
    nz = r1[0]*r2[1] - r1[1]*r2[0]

    # Ecliptic plane normal in ICRF: (0, −sin ε, cos ε)
    # Ascending node = ecliptic_normal × n_orbit  (e × n gives ascending direction)
    ex = 0.0;  ey = -math.sin(eps);  ez = math.cos(eps)

    # intersection direction (ascending node)
    ix = ey*nz - ez*ny
    iy = ez*nx - ex*nz
    iz = ex*ny - ey*nx

    # Rotate intersection vector through P then N (J2000 ICRF → true equator of date)
    P = precession_matrix_equatorial(jd_tt)
    N = nutation_matrix_equatorial(jd_tt)
    i_vec = (ix, iy, iz)
    i_prec = mat_vec_mul(P, i_vec)
    i_true = mat_vec_mul(N, i_prec)

    # Extract ecliptic longitude from true-equator-of-date vector
    eps = (mean_obliquity(jd_tt) + deps_deg) * DEG2RAD
    iye_true = i_true[1] * math.cos(eps) + i_true[2] * math.sin(eps)
    ixe_true = i_true[0]
    node_lon = math.atan2(iye_true, ixe_true) * RAD2DEG % 360.0

    # Speed via mean node as proxy (true node oscillates around mean)
    speed = -1934.136261 / 36525.0

    return NodeData(name="True Node", longitude=node_lon, speed=speed)


# ---------------------------------------------------------------------------
# Mean Black Moon Lilith (Mean Apogee)
# ---------------------------------------------------------------------------

def mean_lilith(jd_ut: float) -> NodeData:
    """
    Governs computation of Mean Black Moon Lilith — the mean longitude of the
    Moon's apogee — using the Meeus analytical formula (Ch. 25, perigee
    formula §22.3 offset by 180°).

    Converts UT to TT internally; no external kernel is required. The result
    tracks the smoothed apogee and is accurate to within a few degrees
    compared to the osculating (true) apogee.

    Args:
        jd_ut: Julian Day in Universal Time (UT1).

    Returns:
        NodeData vessel with name="Lilith", tropical longitude in degrees
        [0, 360), and speed ≈ +0.1114°/day (direct motion).

    Raises:
        No exceptions under normal operation; propagates any exception raised
        by ut_to_tt() or centuries_from_j2000() on invalid input.

    Side effects:
        None.
    """
    year, month, *_ = _approx_year(jd_ut)
    jd_tt    = ut_to_tt(jd_ut, decimal_year(year, month))
    T = centuries_from_j2000(jd_tt)

    # Mean longitude of Moon's perigee (Meeus 22.3)
    perigee = (83.3532465
               + 4069.0137287 * T
               - 0.0103200   * T**2
               - T**3 / 80053.0
               + T**4 / 18999000.0) % 360.0

    # Apogee = perigee + 180°
    apogee = (perigee + 180.0) % 360.0

    # Speed ≈ derivative of perigee formula / Julian century * century/day
    speed = 4069.0137287 / 36525.0   # degrees/day

    return NodeData(name="Lilith", longitude=apogee, speed=speed)


# ---------------------------------------------------------------------------
# True Osculating Lilith (True Apogee)
# ---------------------------------------------------------------------------

def true_lilith(
    jd_ut: float,
    reader: SpkReader | None = None,
) -> NodeData:
    """
    Governs computation of True (osculating) Black Moon Lilith — the Moon's
    actual instantaneous apogee — via the eccentricity vector of the
    geocentric orbit derived from DE441 state vectors.

    Method: retrieves the Moon's geocentric position and velocity from the
    DE441 kernel, computes the specific angular momentum vector h = r × v,
    then derives the eccentricity vector e = (v × h)/μ − r̂. The apogee
    direction is exactly opposite to e. The apogee vector is rotated through
    precession and nutation matrices to yield a tropical ecliptic longitude.
    μ = GM_Earth + GM_Moon = 403503.236 km³/s² (DE441 values).

    Args:
        jd_ut: Julian Day in Universal Time (UT1).
        reader: Optional pre-opened SpkReader. If None, the module-level
            singleton from get_reader() is used (lazy kernel open on first
            call).

    Returns:
        NodeData vessel with name="True Lilith", tropical longitude in degrees
        [0, 360), and speed approximated from the mean apogee formula
        (≈ +0.1114°/day). The true apogee oscillates significantly around
        the mean; the speed field is an approximation only.

    Raises:
        FileNotFoundError: if the DE441 kernel cannot be found and reader is
            None (raised inside get_reader()).
        ValueError: propagated from SpkReader if the requested body or epoch
            is outside the kernel's coverage.

    Side effects:
        None. The SpkReader kernel file is opened lazily on first call if
        reader is None, but that side effect belongs to get_reader().
    """
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt    = ut_to_tt(jd_ut, decimal_year(year, month))
    
    # Nutation and Obliquity for tropical conversion
    dpsi_deg, deps_deg = nutation(jd_tt)
    obliquity = mean_obliquity(jd_tt) + deps_deg
    eps = obliquity * DEG2RAD

    # Earth-Moon mass ratio and GMs for DE441
    # GMe = 398600.435, GMm = 4902.801
    mu = 403503.236 # km^3 / s^2

    # Get state vector (pos, vel) of Moon relative to Earth (km, km/day)
    # Convert velocity to km/s for mu (km^3/s^2)
    # EMB = 3, Moon = 301, Earth = 399
    # Pos(Moon) - Pos(Earth)
    m_pos, m_vel_d = reader.position_and_velocity(3, 301, jd_tt)
    e_pos, e_vel_d = reader.position_and_velocity(3, 399, jd_tt)
    
    r = vec_sub(m_pos, e_pos)
    v_d = vec_sub(m_vel_d, e_vel_d)
    v = tuple(v_i / 86400.0 for v_i in v_d)
    
    # Specific angular momentum h = r x v
    hx = r[1]*v[2] - r[2]*v[1]
    hy = r[2]*v[0] - r[0]*v[2]
    hz = r[0]*v[1] - r[1]*v[0]
    
    # Eccentricity vector e = (v x h)/mu - r/|r|
    # v x h
    vhx = v[1]*hz - v[2]*hy
    vhy = v[2]*hx - v[0]*hz
    vhz = v[0]*hy - v[1]*hx
    
    r_mag = math.sqrt(r[0]*r[0] + r[1]*r[1] + r[2]*r[2])
    
    ex = vhx/mu - r[0]/r_mag
    ey = vhy/mu - r[1]/r_mag
    ez = vhz/mu - r[2]/r_mag
    
    # The eccentricity vector points to PERIGEE.
    # True Lilith is the APOGEE, which is exactly opposite.
    ax, ay, az = -ex, -ey, -ez
    
    # Rotate apogee vector through P then N (J2000 ICRF → true equator of date)
    P = precession_matrix_equatorial(jd_tt)
    N = nutation_matrix_equatorial(jd_tt)
    a_vec = (ax, ay, az)
    a_prec = mat_vec_mul(P, a_vec)
    a_true = mat_vec_mul(N, a_prec)

    # Extract ecliptic longitude from true-equator-of-date vector
    eps = (mean_obliquity(jd_tt) + deps_deg) * DEG2RAD
    aye_true = a_true[1] * math.cos(eps) + a_true[2] * math.sin(eps)
    axe_true = a_true[0]
    lon_tropical = math.atan2(aye_true, axe_true) * RAD2DEG % 360.0
    
    # Speed (estimated via mean apogee speed as it oscillates wildly)
    speed = 4069.0137287 / 36525.0

    return NodeData(name="True Lilith", longitude=lon_tropical, speed=speed)


# ---------------------------------------------------------------------------
# Phase 2: next_moon_node_crossing
# ---------------------------------------------------------------------------

def next_moon_node_crossing(
    jd_start: float,
    reader: SpkReader | None = None,
    ascending: bool = True,
) -> float:
    """
    Find the next time the Moon crosses its orbital node.

    Detection method: the Moon's geocentric ecliptic latitude passes through
    zero at each node crossing.  At the ascending node the latitude changes
    from south (negative) to north (positive); at the descending node it
    changes from north to south.  The function scans forward in 0.5-day steps
    (covering ~6.5° of latitude change per step) then refines with 52-iteration
    bisection.

    Args:
        jd_start: Julian Day (UT1) to begin searching from.
        reader: Open :class:`SpkReader` from :mod:`moira.spk_reader`.  Uses
            the module-level singleton if ``None``.
        ascending: If ``True`` (default), find the next ascending-node
            crossing (latitude − → +).  If ``False``, find the next
            descending-node crossing (latitude + → −).

    Returns:
        Julian Day (UT1) of the next node crossing.

    Raises:
        FileNotFoundError: If the DE441 kernel is not found.
        ValueError: If no crossing is found within 30 days (should never
            happen for a Moon search).
    """
    if reader is None:
        reader = get_reader()

    def _moon_lat(jd_ut: float) -> float:
        """Geocentric ecliptic latitude of the Moon (degrees)."""
        yr, mo, *_ = _approx_year(jd_ut)
        jd_tt = ut_to_tt(jd_ut, decimal_year(yr, mo))
        emb_moon  = reader.position(3, 301, jd_tt)
        emb_earth = reader.position(3, 399, jd_tt)
        moon_geo = vec_sub(emb_moon, emb_earth)
        # Rotate ICRF → true equatorial of date (precession + nutation)
        dpsi_deg, deps_deg = nutation(jd_tt)
        P = precession_matrix_equatorial(jd_tt)
        N = nutation_matrix_equatorial(jd_tt)
        v1 = mat_vec_mul(P, moon_geo)
        v_eq = mat_vec_mul(N, v1)
        # Rotate true equatorial → ecliptic to extract latitude
        obliquity = (mean_obliquity(jd_tt) + deps_deg) * DEG2RAD
        cos_eps = math.cos(obliquity)
        sin_eps = math.sin(obliquity)
        z_ecl = -v_eq[1] * sin_eps + v_eq[2] * cos_eps
        dist = math.sqrt(v_eq[0]**2 + v_eq[1]**2 + v_eq[2]**2)
        if dist < 1e-30:
            return 0.0
        return math.asin(max(-1.0, min(1.0, z_ecl / dist))) * RAD2DEG

    step = 0.5   # days
    max_days = 30.0

    f_prev = _moon_lat(jd_start)
    t = jd_start

    while t < jd_start + max_days:
        t_next = t + step
        f_next = _moon_lat(t_next)
        if ascending and f_prev < 0.0 and f_next >= 0.0:
            return _bisect_lat(_moon_lat, t, t_next)
        if not ascending and f_prev >= 0.0 and f_next < 0.0:
            return _bisect_lat(lambda jd: -_moon_lat(jd), t, t_next)
        f_prev = f_next
        t = t_next

    raise ValueError(
        f"next_moon_node_crossing: no {'ascending' if ascending else 'descending'} "
        f"node crossing found within {max_days} days of JD {jd_start:.1f}."
    )


def _bisect_lat(func, t0: float, t1: float, iterations: int = 52) -> float:
    """Bisect a bracketed sign-change of func over [t0, t1]."""
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
# NodesAndApsides
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class NodesAndApsides:
    """Nodes and apsides for a body at a given Julian Day.

    For the Moon: ascending/descending nodes and perigee/apogee are
    computed from the lunar node engine (``true_node``, ``mean_node``).
    For planets: ascending/descending nodes and perihelion/aphelion are
    taken from the planetary-node and phenomena engines.

    Fields
    ------
    body : str
        Body name.
    jd_ut : float
        Julian Day (UT) of the computation.
    ascending_node_lon : float
        Ecliptic longitude of the ascending node, in degrees.
    descending_node_lon : float
        Ecliptic longitude of the descending node (ascending + 180°), in degrees.
    periapsis_lon : float | None
        Ecliptic longitude of perihelion / perigee, in degrees; None if not available.
    apoapsis_lon : float | None
        Ecliptic longitude of aphelion / apogee, in degrees; None if not available.
    """

    body: str
    jd_ut: float
    ascending_node_lon: float
    descending_node_lon: float
    periapsis_lon: float | None
    apoapsis_lon: float | None


_MOON_NAMES = {"moon", "luna"}
_BODY_MOON = "Moon"


def nodes_and_apsides_at(body: str, jd_ut: float) -> NodesAndApsides:
    """Return nodes and apsides for *body* at *jd_ut*.

    For the Moon the true node and true Lilith (apogee) are used.
    For planets the ascending node longitude is taken from
    ``moira.planetary_nodes.planetary_node``; perihelion and aphelion are
    searched forward from *jd_ut* via ``moira.phenomena``.

    Parameters
    ----------
    body : str
        Body name (e.g. ``Body.MOON``, ``'Mars'``).
    jd_ut : float
        Julian Day in Universal Time.

    Returns
    -------
    NodesAndApsides
    """
    from .spk_reader import get_reader

    if body.lower() in _MOON_NAMES:
        nd = true_node(jd_ut)
        lil = true_lilith(jd_ut, reader=get_reader())
        apogee_lon = lil.longitude
        return NodesAndApsides(
            body=body,
            jd_ut=jd_ut,
            ascending_node_lon=nd.longitude,
            descending_node_lon=normalize_degrees(nd.longitude + 180.0),
            periapsis_lon=normalize_degrees(apogee_lon + 180.0),
            apoapsis_lon=apogee_lon,
        )

    from .planetary_nodes import planetary_node

    pn = planetary_node(body, jd_ut)
    asc = pn.ascending_node
    return NodesAndApsides(
        body=body,
        jd_ut=jd_ut,
        ascending_node_lon=asc,
        descending_node_lon=normalize_degrees(asc + 180.0),
        periapsis_lon=pn.perihelion,
        apoapsis_lon=pn.aphelion,
    )
